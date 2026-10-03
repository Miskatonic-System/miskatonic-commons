# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Cross-repository closure and public-identity invariants (WO-COMMONS-INTEGRATION-HARDENING-00B)."""

import json
import re
import subprocess
from pathlib import Path

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


def test_nc2_recorded_at_does_not_postdate_its_commit():
    if not in_git_checkout():
        pytest.skip("not running inside a Git checkout of this repository")
    rel = RECEIPT_PATH.relative_to(ROOT).as_posix()
    if git("status", "--porcelain", "--", rel):
        pytest.skip("receipt has uncommitted changes")
    # The commit that introduced the recorded value (pickaxe), not merely the last commit touching the file.
    value = f'"recorded_at": "{RECEIPT["recorded_at"]}"'
    introducing = git("log", "--reverse", "--format=%cI", "-S", value, "--", rel).splitlines()
    if not introducing:
        pytest.skip("recorded value not found in this checkout's history")
    committed = introducing[0]
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


def synthetic_merge_context() -> dict:
    """Structural evidence of CI's synthetic pull-request merge, taken from the provider event payload.

    Returns {} unless running in a GitHub Actions pull_request event, in which case it returns the
    synthetic merge SHA (GITHUB_SHA) and the pull request's head SHA.
    """
    import os
    if os.environ.get("GITHUB_EVENT_NAME") not in ("pull_request", "pull_request_target"):
        return {}
    try:
        payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        return {"merge_sha": os.environ["GITHUB_SHA"].lower(),
                "pr_head_sha": payload["pull_request"]["head"]["sha"].lower()}
    except (KeyError, OSError, ValueError):
        return {}


def identity_offenders(records, context: dict) -> list:
    """records: iterable of (sha, parents, author_email, committer_email, subject, coauthors).

    A commit is exempt as CI's synthetic merge only if it is the provider-declared merge SHA and its
    second parent is the provider-declared PR head. Commit subjects are never consulted.
    """
    offenders = []
    for sha, parents, author, committer, subject, coauthors in records:
        parent_list = parents.split()
        if sha in HISTORICAL_IDENTITY_EXCEPTIONS:
            continue
        if (context and sha.lower() == context.get("merge_sha") and len(parent_list) == 2
                and parent_list[1].lower() == context.get("pr_head_sha")):
            continue
        is_merge = len(parent_list) > 1
        is_automation = bool(coauthors.strip())
        if (is_merge or is_automation) and not (SAFE_EMAIL.match(author) and SAFE_EMAIL.match(committer)):
            offenders.append(f"{sha[:12]} {subject}")
    return offenders


def git_records(cwd=ROOT, rev="HEAD"):
    log = subprocess.run(
        ["git", "log", "--format=%H%x1f%P%x1f%ae%x1f%ce%x1f%s%x1f%(trailers:key=Co-Authored-By,valueonly)%x1e", rev],
        cwd=cwd, capture_output=True, text=True, check=True).stdout
    for record in filter(None, (r.strip() for r in log.split("\x1e"))):
        yield tuple((record.split("\x1f") + [""] * 6)[:6])


def canonical_committer_offenders(records) -> list:
    """Every committer on canonical history must be a safe identity.

    Provider merges stamp the merging account as committer (author on merge commits), so this is
    what catches a maintainer account whose email privacy is off. Contributors' own pull-request
    commits are not canonical until merged, and are not checked here.
    """
    return [f"{sha[:12]} committer" for sha, parents, author, committer, subject, coauthors in records
            if sha not in HISTORICAL_IDENTITY_EXCEPTIONS and not SAFE_EMAIL.match(committer)]


def canonical_rev():
    for rev in ("origin/main", "refs/remotes/origin/main"):
        if subprocess.run(["git", "rev-parse", "--verify", "--quiet", rev], cwd=ROOT, capture_output=True).returncode == 0:
            return rev
    return "HEAD" if git("rev-parse", "--abbrev-ref", "HEAD") == "main" else None


def test_maintainer_merges_and_automation_commits_use_safe_identity():
    if not in_git_checkout():
        pytest.skip("not running inside a Git checkout of this repository")
    if git("rev-parse", "--is-shallow-repository") == "true":
        pytest.skip("shallow clone")
    assert identity_offenders(git_records(), synthetic_merge_context()) == []
    rev = canonical_rev()
    if rev is None:
        pytest.skip("canonical main not available in this checkout")
    assert canonical_committer_offenders(git_records(rev=rev)) == []


def test_canonical_committer_check_catches_personal_committer():
    records = [("a" * 40, "b" * 40, "1+x@users.noreply.github.com", "someone@personal.invalid", "rebased", "")]
    assert canonical_committer_offenders(records) == [f"{'a' * 12} committer"]


def _spoof_repo(tmp_path):
    """A repository whose HEAD is a real merge by a personal identity whose subject mimics CI's synthetic merge."""
    def g(*args, env=None):
        import os
        e = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", **(env or {}))
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True, check=True, env=e).stdout.strip()
    safe = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "1+a@users.noreply.github.com",
            "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "1+a@users.noreply.github.com"}
    personal = {"GIT_AUTHOR_NAME": "p", "GIT_AUTHOR_EMAIL": "someone@personal.invalid",
                "GIT_COMMITTER_NAME": "p", "GIT_COMMITTER_EMAIL": "someone@personal.invalid"}
    g("init", "-q", "-b", "main")
    g("commit", "-q", "--allow-empty", "-m", "base", env=safe)
    base = g("rev-parse", "HEAD")
    g("checkout", "-q", "-b", "topic")
    g("commit", "-q", "--allow-empty", "-m", "topic", env=safe)
    topic = g("rev-parse", "HEAD")
    g("checkout", "-q", "main")
    g("merge", "-q", "--no-ff", "topic", "-m", f"Merge {topic} into {base}", env=personal)
    return g("rev-parse", "HEAD"), base, topic


def test_synthetic_merge_subject_spoof_rejected(tmp_path):
    """SYNTHETIC_MERGE_SUBJECT_SPOOF_REJECTED: a mimicking subject earns no exemption."""
    head, base, topic = _spoof_repo(tmp_path)
    records = list(git_records(tmp_path))
    # push context, or no provider context at all
    assert identity_offenders(records, {}) == [f"{head[:12]} Merge {topic} into {base}"]
    # pull_request context, but the spoof is not the provider-declared merge SHA
    assert identity_offenders(records, {"merge_sha": "0" * 40, "pr_head_sha": topic}) != []
    # provider-declared merge SHA, but the declared PR head is not its second parent
    assert identity_offenders(records, {"merge_sha": head, "pr_head_sha": "1" * 40}) != []


def test_true_synthetic_merge_structure_is_exempt(tmp_path):
    head, base, topic = _spoof_repo(tmp_path)
    assert identity_offenders(list(git_records(tmp_path)), {"merge_sha": head, "pr_head_sha": topic}) == []


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


def test_erratum_00c_binds_unmodified_receipt():
    import hashlib
    erratum = json.loads((ROOT / "provenance/COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.ERRATUM_00C.json").read_text())
    assert erratum["affected_file"] == RECEIPT_PATH.relative_to(ROOT).as_posix()
    assert hashlib.sha256(RECEIPT_PATH.read_bytes()).hexdigest() == erratum["affected_file_sha256"]
    assert erratum["affected_statement"] in RECEIPT["temporal_note"]
    assert erratum["affected_file_modified"] is False and erratum["chronology_changed"] is False
