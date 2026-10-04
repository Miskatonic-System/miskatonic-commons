#!/usr/bin/env python3
# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Read-only audit of the Commons publication fence against its custodied expected state.

Compares the provider's ruleset and the CI workflow on main with
provenance/COMMONS_FENCE_EXPECTED_STATE_V0_1.json and prints one verdict:

  COMMONS_FENCE_MATCHES_EXPECTED   exit 0
  COMMONS_FENCE_DRIFT              exit 1   (each difference is listed)
  COMMONS_FENCE_UNOBSERVABLE       exit 3   (the provider state could not be read)

This detects drift. It cannot prevent an administrator from changing provider configuration.

Usage:
  python scripts/audit_commons_fence.py                      # live, read-only, via the gh CLI
  python scripts/audit_commons_fence.py --ruleset-file R.json --workflow-file ci.yml
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = ROOT / "provenance" / "COMMONS_FENCE_EXPECTED_STATE_V0_1.json"


def canonical(value) -> bytes:
    """RFC 8785 bytes for this document's value domain (ASCII strings, small integers, booleans)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def project(ruleset: dict) -> dict:
    """The fence-relevant fields of a ruleset API document, in a fixed shape."""
    rules = {}
    for rule in ruleset.get("rules", []):
        params = rule.get("parameters", {})
        if rule["type"] == "required_status_checks":
            params = {"strict_required_status_checks_policy": params.get("strict_required_status_checks_policy"),
                      "do_not_enforce_on_create": params.get("do_not_enforce_on_create"),
                      "required_status_checks": sorted(
                          ({"context": c["context"], "integration_id": c.get("integration_id")}
                           for c in params.get("required_status_checks", [])), key=lambda c: c["context"])}
        elif rule["type"] == "pull_request":
            params = {k: params.get(k) for k in ("allowed_merge_methods", "required_approving_review_count",
                                                 "require_code_owner_review", "required_reviewers")}
        rules[rule["type"]] = params
    return {
        "ruleset_id": ruleset.get("id"),
        "enforcement": ruleset.get("enforcement"),
        "target": ruleset.get("target"),
        "ref_name_include": sorted(ruleset.get("conditions", {}).get("ref_name", {}).get("include", [])),
        "ref_name_exclude": sorted(ruleset.get("conditions", {}).get("ref_name", {}).get("exclude", [])),
        "bypass_actors": ruleset.get("bypass_actors"),
        "current_user_can_bypass": ruleset.get("current_user_can_bypass"),
        "rules": rules,
    }


def differences(expected, observed, path="$") -> list:
    if isinstance(expected, dict) and isinstance(observed, dict):
        out = []
        for key in sorted(set(expected) | set(observed)):
            if key not in observed:
                out.append(f"{path}.{key}: missing")
            elif key not in expected:
                out.append(f"{path}.{key}: unexpected {json.dumps(observed[key], sort_keys=True)}")
            else:
                out += differences(expected[key], observed[key], f"{path}.{key}")
        return out
    if expected != observed:
        return [f"{path}: expected {json.dumps(expected, sort_keys=True)}, observed {json.dumps(observed, sort_keys=True)}"]
    return []


def audit(expected_doc: dict, ruleset: dict | None, workflow: bytes | None) -> tuple[str, list]:
    if isinstance(ruleset, dict) and str(ruleset.get("status")) == "404":
        return "COMMONS_FENCE_DRIFT", ["ruleset: the provider reports it does not exist (404)"]
    if not isinstance(ruleset, dict) or "rules" not in ruleset or workflow is None:
        return "COMMONS_FENCE_UNOBSERVABLE", ["ruleset or workflow could not be read"]
    observed = {"ruleset": project(ruleset),
                "workflow": {"path": expected_doc["expected_state"]["workflow"]["path"],
                             "sha256": hashlib.sha256(workflow).hexdigest()}}
    diffs = differences(expected_doc["expected_state"], observed)
    return ("COMMONS_FENCE_DRIFT" if diffs else "COMMONS_FENCE_MATCHES_EXPECTED"), diffs


def _gh(path: str) -> dict | None:
    """The JSON document at ``path``; {"status": "404"} when the provider says it does not exist; None otherwise."""
    try:
        proc = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return {"status": "404"} if "HTTP 404" in proc.stderr else None
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ruleset-file", type=Path)
    ap.add_argument("--workflow-file", type=Path)
    args = ap.parse_args(argv)
    expected_doc = json.loads(EXPECTED.read_text())
    if hashlib.sha256(canonical(expected_doc["expected_state"])).hexdigest() != expected_doc["expected_state_sha256"]:
        print("COMMONS_FENCE_DRIFT\nexpected-state record does not match its own digest")
        return 1
    repo, ruleset_id = expected_doc["repository"], expected_doc["expected_state"]["ruleset"]["ruleset_id"]
    if args.ruleset_file:
        try:
            ruleset = json.loads(args.ruleset_file.read_text())
        except (OSError, ValueError):
            ruleset = None
    else:
        ruleset = _gh(f"repos/{repo}/rulesets/{ruleset_id}")
    if args.workflow_file:
        workflow = args.workflow_file.read_bytes() if args.workflow_file.is_file() else None
    else:
        doc = _gh(f"repos/{repo}/contents/{expected_doc['expected_state']['workflow']['path']}?ref=main")
        workflow = base64.b64decode(doc["content"]) if doc and "content" in doc else None
    verdict, diffs = audit(expected_doc, ruleset, workflow)
    print(verdict)
    for d in diffs:
        print("  " + d)
    return {"COMMONS_FENCE_MATCHES_EXPECTED": 0, "COMMONS_FENCE_DRIFT": 1}.get(verdict, 3)


if __name__ == "__main__":
    sys.exit(main())
