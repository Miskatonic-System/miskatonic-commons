# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Custody of the publication-fence configuration (WO-COMMONS-MEMBRANE-EVALUATION-01B §14-§15).

The expected state of ruleset 24431688 and the digest of the CI workflow are recorded in
provenance/COMMONS_FENCE_EXPECTED_STATE_V0_1.json. scripts/audit_commons_fence.py compares a
provider observation with that record. These tests run offline: every observation is synthetic.
"""

import copy
import hashlib
import importlib.util
import json

import pytest
import rfc8785

from conftest import ROOT

_spec = importlib.util.spec_from_file_location("audit_commons_fence", ROOT / "scripts" / "audit_commons_fence.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

RECORD = json.loads((ROOT / "provenance/COMMONS_FENCE_EXPECTED_STATE_V0_1.json").read_text())
STATE = RECORD["expected_state"]
WORKFLOW = (ROOT / STATE["workflow"]["path"]).read_bytes()


def provider_view(state=STATE) -> dict:
    """A ruleset API document that projects exactly onto ``state``."""
    rs = state["ruleset"]
    rules = []
    for rtype, params in rs["rules"].items():
        rule = {"type": rtype}
        if params:
            rule["parameters"] = copy.deepcopy(params)
        rules.append(rule)
    return {"id": rs["ruleset_id"], "enforcement": rs["enforcement"], "target": rs["target"],
            "conditions": {"ref_name": {"include": rs["ref_name_include"], "exclude": rs["ref_name_exclude"]}},
            "bypass_actors": copy.deepcopy(rs["bypass_actors"]),
            "current_user_can_bypass": rs["current_user_can_bypass"], "rules": rules, "_links": {}}


def test_record_digest_is_rfc8785():
    assert hashlib.sha256(rfc8785.dumps(STATE)).hexdigest() == RECORD["expected_state_sha256"]
    assert audit.canonical(STATE) == rfc8785.dumps(STATE)


def test_record_states_the_fence():
    rs = STATE["ruleset"]
    assert rs["ruleset_id"] == 24431688 and rs["enforcement"] == "active" and rs["target"] == "branch"
    assert rs["ref_name_include"] == ["refs/heads/main"] and rs["bypass_actors"] == []
    assert rs["current_user_can_bypass"] == "never"
    assert set(rs["rules"]) == {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}
    assert rs["rules"]["pull_request"]["allowed_merge_methods"] == ["merge"]
    checks = rs["rules"]["required_status_checks"]
    assert checks["strict_required_status_checks_policy"] is True
    assert {c["integration_id"] for c in checks["required_status_checks"]} == {15368}
    assert sorted(c["context"] for c in checks["required_status_checks"]) == sorted([
        "tests (python 3.12)", "tests (python 3.13)", "tests (python 3.14)",
        "secret scan (gitleaks, full history)", "dependency review"])


def test_workflow_in_tree_matches_custodied_digest():
    """A change to the CI workflow must update the custody record in the same reviewed change."""
    assert hashlib.sha256(WORKFLOW).hexdigest() == STATE["workflow"]["sha256"]


def test_matching_observation():
    assert audit.audit(RECORD, provider_view(), WORKFLOW) == ("COMMONS_FENCE_MATCHES_EXPECTED", [])


def _drift(edit):
    view = provider_view()
    edit(view)
    verdict, diffs = audit.audit(RECORD, view, WORKFLOW)
    assert verdict == "COMMONS_FENCE_DRIFT" and diffs
    return diffs


def _rule(view, rtype):
    return next(r for r in view["rules"] if r["type"] == rtype)


@pytest.mark.parametrize("name,edit", [
    ("disabled", lambda v: v.__setitem__("enforcement", "disabled")),
    ("evaluate_only", lambda v: v.__setitem__("enforcement", "evaluate")),
    ("other_ref", lambda v: v["conditions"]["ref_name"].__setitem__("include", ["refs/heads/release"])),
    ("ref_excluded", lambda v: v["conditions"]["ref_name"].__setitem__("exclude", ["refs/heads/main"])),
    ("bypass_actor", lambda v: v["bypass_actors"].append({"actor_id": 5, "actor_type": "RepositoryRole",
                                                         "bypass_mode": "always"})),
    ("viewer_can_bypass", lambda v: v.__setitem__("current_user_can_bypass", "always")),
    ("squash_allowed", lambda v: _rule(v, "pull_request")["parameters"]["allowed_merge_methods"].append("squash")),
    ("check_removed", lambda v: _rule(v, "required_status_checks")["parameters"]["required_status_checks"].pop()),
    ("check_integration_changed", lambda v: _rule(v, "required_status_checks")["parameters"]
     ["required_status_checks"][0].__setitem__("integration_id", None)),
    ("checks_not_strict", lambda v: _rule(v, "required_status_checks")["parameters"]
     .__setitem__("strict_required_status_checks_policy", False)),
    ("deletion_rule_removed", lambda v: v["rules"].remove(_rule(v, "deletion"))),
    ("force_push_rule_removed", lambda v: v["rules"].remove(_rule(v, "non_fast_forward"))),
    ("unknown_rule_added", lambda v: v["rules"].append({"type": "update"})),
])
def test_drift_is_detected(name, edit):
    _drift(edit)


def test_workflow_change_is_drift():
    verdict, diffs = audit.audit(RECORD, provider_view(), WORKFLOW + b"\n# changed\n")
    assert verdict == "COMMONS_FENCE_DRIFT" and any("workflow" in d for d in diffs)


@pytest.mark.parametrize("ruleset,workflow", [(None, WORKFLOW), ({"message": "Not Found"}, WORKFLOW),
                                              (provider_view(), None)])
def test_unobservable(ruleset, workflow):
    assert audit.audit(RECORD, ruleset, workflow)[0] == "COMMONS_FENCE_UNOBSERVABLE"


def test_command_line_offline(tmp_path):
    (tmp_path / "r.json").write_text(json.dumps(provider_view()))
    (tmp_path / "ci.yml").write_bytes(WORKFLOW)
    assert audit.main(["--ruleset-file", str(tmp_path / "r.json"), "--workflow-file", str(tmp_path / "ci.yml")]) == 0
    (tmp_path / "r.json").write_text(json.dumps(dict(provider_view(), enforcement="disabled")))
    assert audit.main(["--ruleset-file", str(tmp_path / "r.json"), "--workflow-file", str(tmp_path / "ci.yml")]) == 1
    assert audit.main(["--ruleset-file", str(tmp_path / "absent.json"), "--workflow-file", str(tmp_path / "ci.yml")]) == 3
