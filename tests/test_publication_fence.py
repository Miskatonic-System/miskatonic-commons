# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Recorded provider publication fence is complete and matches the CI workflow (WO-COMMONS-PUBLICATION-FENCE-00C)."""

import json
import re

from conftest import ROOT

RECEIPT = json.loads((ROOT / "provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json").read_text())
RULESET = RECEIPT["ruleset"]["readback"]
RULES = {r["type"]: r.get("parameters", {}) for r in RULESET["rules"]}


def workflow_check_names() -> set:
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    versions = re.search(r"python-version:\s*\[([^\]]+)\]", text).group(1)
    pythons = [v.strip().strip('"') for v in versions.split(",")]
    names = set()
    for name in re.findall(r"^    name:\s*(.+)$", text, flags=re.M):
        name = name.strip()
        if "${{ matrix.python-version }}" in name:
            names |= {name.replace("${{ matrix.python-version }}", v) for v in pythons}
        else:
            names.add(name)
    return names


def test_required_checks_match_workflow_jobs():
    required = {c["context"] for c in RULES["required_status_checks"]["required_status_checks"]}
    assert required == set(RECEIPT["required_check_identities"]["contexts"])
    assert required == workflow_check_names()


def test_required_checks_bound_to_github_actions_app():
    for check in RULES["required_status_checks"]["required_status_checks"]:
        assert check["integration_id"] == RECEIPT["required_check_identities"]["app"]["integration_id"] == 15368
    assert RULES["required_status_checks"]["strict_required_status_checks_policy"] is True


def test_fence_targets_main_without_bypass():
    assert RULESET["enforcement"] == "active"
    assert RULESET["target"] == "branch"
    assert RULESET["conditions"]["ref_name"]["include"] == ["refs/heads/main"]
    assert RULESET["bypass_actors"] == []
    assert RULESET["current_user_can_bypass"] == "never"
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"} <= set(RULES)
    assert RULES["pull_request"]["allowed_merge_methods"] == ["rebase"]
    effective = {(r["type"], r["ruleset_id"]) for r in RECEIPT["effective_rules_for_main"]["rules"]}
    assert effective == {(t, RULESET["id"]) for t in ("deletion", "non_fast_forward", "pull_request", "required_status_checks")}
    assert RECEIPT["bypass_classification"]["value"] == "PROVIDER_PUBLICATION_FENCE_ENFORCED"


def test_adversarial_controls_all_blocked():
    controls = {c["id"]: c for c in RECEIPT["adversarial_controls"]["controls"]}
    assert set(controls) == {"B1", "B2", "B3", "B4", "B5"}
    expected = {"B1": "MERGE_BLOCKED_REQUIRED_CHECK_FAILED", "B2": "MERGE_BLOCKED_REQUIRED_CHECK_PENDING",
                "B3": "STALE_HEAD_SUCCESS_NOT_ACCEPTED", "B4": "MERGE_BLOCKED_REQUIRED_CHECK_MISSING",
                "B5": "PROVIDER_RULE_READBACK"}
    for cid, control in controls.items():
        assert control["expected"] == expected[cid] and control["result"] == "PASS"
        if cid != "B5":
            assert control["merged"] is False
    assert "dependency review" not in controls["B4"]["observed_checks"]


def test_no_private_export_and_identity_mechanism_recorded():
    assert RECEIPT["private_origin_export_count"] == 0
    assert RECEIPT["merge_identity"]["ACCOUNT_EMAIL_PRIVACY_STATE"] == "HUMAN_ATTESTATION_REQUIRED"
