# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Cross-repository closure and public-identity invariants (WO-COMMONS-INTEGRATION-HARDENING-00B)."""

import json
import re
import subprocess

import pytest

from conftest import ROOT, lint
from test_bootstrap_contract import RECORDED_ROOT, git, in_git_checkout, tracked_text_files

RECEIPT_PATH = ROOT / "provenance/COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.json"
RECEIPT = json.loads(RECEIPT_PATH.read_text())
INDEX = json.loads((ROOT / "releases/package-index-v0.1.json").read_text())
POLICY = (ROOT / "docs/PUBLIC_COMMIT_IDENTITY_POLICY.md").read_text()

# Historical commits whose public metadata carries a personal address. They are
# recorded, never rewritten, and are the only permitted exceptions.
# Hard-coded on purpose: extending the receipt must not widen the exception list.
HISTORICAL_IDENTITY_EXCEPTIONS = frozenset({
    "9e27f1a5e8076d7985d95e9c7e5bcca2f551b9de",  # GitHub-generated root commit
    "3d27deba20427ef10bdf46bbb3b95d087dd38db3",  # 00A bootstrap merge via GitHub merge API
})
SAFE_EMAIL = re.compile(r"(?i)^(?:[^@\s]+@users\.noreply\.github\.com|noreply@github\.com|noreply@anthropic\.com)$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def receipt_problems(doc) -> list:
    """Locator and personal-data shapes that must never appear in the public closure receipt.

    Commit identities are bound deliberately, so only the commit-ID rule is not applied.
    """
    problems = []
    for path, text in lint.iter_strings(doc):
        for kind, pattern in lint.LOCATOR_PATTERNS:
            if kind != "commit_id" and re.search(pattern, text):
                problems.append(f"{path}: {kind}")
        for kind, pattern in lint.PERSONAL_DATA_PATTERNS:
            if re.search(pattern, text):
                problems.append(f"{path}: {kind}")
    return problems


# NC6 / WO §12-13 -----------------------------------------------------------------

def test_nc6_private_origin_export_count_is_zero_and_consistent():
    assert RECEIPT["PRIVATE_ORIGIN_EXPORT_COUNT"] == 0
    non_native = [p for p in INDEX["packages"] if p["source_disclosure_level"] != "COMMONS_NATIVE"]
    assert len(non_native) == RECEIPT["PRIVATE_ORIGIN_EXPORT_COUNT"]
    for release_dir in (ROOT / "releases").iterdir():
        for manifest in release_dir.glob("*/manifest.json"):
            assert json.loads(manifest.read_text())["source_disclosure_level"] == "COMMONS_NATIVE", manifest


def test_commons_native_package_preserved():
    (entry,) = INDEX["packages"]
    manifest = json.loads((ROOT / entry["manifest_path"]).read_text())
    for doc in (entry, manifest, RECEIPT["released_packages"][0]):
        assert doc["package_id"] == "commons-export-lint" and doc["version"] == "0.1.0"
        assert doc["release_class"] == "P3_PUBLIC_RELEASE_APPROVED"
        assert doc["commercial_impact"] == "NONE"
        assert doc["source_disclosure_level"] == "COMMONS_NATIVE"
        assert doc["clearance_status"] == "CLEARED"
    assert lint.check_index(ROOT / "releases/package-index-v0.1.json", ROOT) == []


# NC7 ---------------------------------------------------------------------------

def test_nc7_closure_receipt_exposes_no_private_locator_or_personal_data():
    assert receipt_problems(RECEIPT) == []


@pytest.mark.parametrize("injected", [
    "Miskatonic-System" + "/private-registry",
    "/home/someone/registry",
    "registry." + "corp/x",
    "someone" + "@" + "example.com",
])
def test_nc7_check_detects_injected_leaks(injected):
    doc = json.loads(RECEIPT_PATH.read_text())
    doc["organization_registry"]["identity_disclosure"] = injected
    assert receipt_problems(doc)


def test_no_personal_address_reproduced_in_tracked_files():
    offenders = []
    for path, text in tracked_text_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(("fixtures/", "tests/")) or rel == "scripts/generate_fixtures.py":
            continue  # synthetic example.invalid / example.com samples only
        for match in EMAIL.finditer(text):
            if not SAFE_EMAIL.match(match.group(0)):
                offenders.append(f"{rel}: {match.group(0)}")
    assert offenders == []


# NC8 / WO §7-8, §21 --------------------------------------------------------------

def test_receipt_identity_exceptions_match_hard_coded_set():
    assert set(RECEIPT["public_identity_exposure"]["affected_commits"]) == HISTORICAL_IDENTITY_EXCEPTIONS


def test_nc8_policy_sentences_about_history_are_all_negative():
    """Every policy sentence that mentions rewriting history must be a prohibition."""
    text = re.sub(r"\s+", " ", POLICY)
    risky = re.compile(r"(?i)\b(rewrit\w*|force[- ]push\w*|filter\w*|rebas\w*|scrub\w*|graft\w*)\b")
    negation = re.compile(r"(?i)\b(no|not|never|without|unchanged)\b|\*\*no\*\*")
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if risky.search(sentence):
            assert negation.search(sentence), sentence


def test_nc2_recorded_at_does_not_postdate_its_commit():
    if not in_git_checkout():
        pytest.skip("not running inside a Git checkout of this repository")
    rel = RECEIPT_PATH.relative_to(ROOT).as_posix()
    if git("status", "--porcelain", "--", rel):
        pytest.skip("receipt has uncommitted changes")
    committed = git("log", "-1", "--format=%cI", "--", rel)
    if not committed:
        pytest.skip("receipt not yet committed")
    import datetime
    when = datetime.datetime.fromisoformat(committed).astimezone(datetime.timezone.utc)
    assert RECEIPT["recorded_at"] <= when.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_nc8_identity_policy_grants_no_history_rewrite():
    assert RECEIPT["public_identity_exposure"]["PUBLIC_HISTORY_REWRITE_AUTHORITY"] == "NONE"
    assert RECEIPT["public_identity_exposure"]["ROOT_COMMIT_PERSONAL_EMAIL_EXPOSURE"] == "YES"
    assert RECEIPT["public_identity_exposure"]["address_reproduced_here"] is False
    assert "grants **no** authority to rewrite" in POLICY
    assert "does **not** require anyone to hide an identity" in POLICY
    assert RECEIPT["commons"]["root_commit"] == RECORDED_ROOT


def test_maintainer_merges_and_automation_commits_use_safe_identity():
    if not in_git_checkout():
        pytest.skip("not running inside a Git checkout of this repository")
    if git("rev-parse", "--is-shallow-repository") == "true":
        pytest.skip("shallow clone")
    head = git("rev-parse", "HEAD")
    log = git("log", "--format=%H%x1f%P%x1f%ae%x1f%ce%x1f%s%x1f%(trailers:key=Co-Authored-By,valueonly)%x1e", "HEAD")
    offenders = []
    for record in filter(None, (r.strip() for r in log.split("\x1e"))):
        sha, parents, author, committer, subject, coauthors = (record.split("\x1f") + [""] * 6)[:6]
        if sha in HISTORICAL_IDENTITY_EXCEPTIONS:
            continue
        if sha == head and re.match(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$", subject):
            continue  # only the checked-out HEAD may be CI's synthetic pull-request merge
        is_merge = len(parents.split()) > 1
        is_automation = bool(coauthors.strip())
        if (is_merge or is_automation) and not (SAFE_EMAIL.match(author) and SAFE_EMAIL.match(committer)):
            offenders.append(f"{sha[:12]} {subject}")
    assert offenders == []


# NC1 / NC2 / NC10 (Commons-side record) -----------------------------------------

def test_nc1_nc2_historical_gates_recorded_as_not_passing():
    ppc = RECEIPT["publication_path_conformance"]
    assert ppc["classification"] == "COMMONS_SYSTEMS_PUBLICATION_PATH_NONCONFORMITY"
    assert ppc["historical_status_rewritten"] is False
    for pr in ("pointer_pr_317", "closure_pr_318"):
        assert ppc[pr]["pre_merge_gate"] in ("FAILED", "NOT_EVALUATED_BEFORE_MERGE")
        assert ppc[pr]["pr_context_run_conclusion"] == "failure"
        assert ppc[pr]["anomaly"] == "AUTHORITATIVE_BLOCK_MISSING"
    reg = RECEIPT["organization_registry"]
    assert RECEIPT["recorded_at"] > max(reg["pointer"]["merged_at"], reg["closure"]["merged_at"])


def test_nc10_technical_result_distinct_from_publication_conformance():
    tr = RECEIPT["technical_result"]
    assert tr["disposition"] == "MISKATONIC_COMMONS_PUBLIC_EXPORT_SURFACE_V0_1_BOOTSTRAPPED"
    assert tr["preserved"] is True and tr["independent_of_publication_path_conformance"] is True
    assert RECEIPT["authority_delta"] == "NONE"


def test_receipt_is_canonical_json():
    assert lint.canonical_json_bytes(RECEIPT) == RECEIPT_PATH.read_bytes()
