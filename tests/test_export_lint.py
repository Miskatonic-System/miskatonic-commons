# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Behavior of commons-export-lint (work-order tests T1-T11 and supporting cases)."""

import json

import pytest

from conftest import ROOT, lint

FIXTURES = ROOT / "fixtures"
# The current release of the tool, as listed in the package index.
_LINT_ENTRY = next(p for p in json.loads((ROOT / "releases/package-index-v0.1.json").read_text())["packages"]
                   if p["package_id"] == "commons-export-lint")
REAL_MANIFEST = ROOT / _LINT_ENTRY["manifest_path"]
REAL_RECEIPT = ROOT / _LINT_ENTRY["clearance_receipt_path"]
REAL_BUNDLE = ROOT / "tools/commons-export-lint"
INDEX = ROOT / "releases/package-index-v0.1.json"


# T1 -------------------------------------------------------------------------

def test_t1_valid_commons_native_manifest_passes(release_copy):
    assert release_copy().codes() == []


def test_t1_real_bootstrap_release_passes():
    assert lint.check_release(REAL_MANIFEST, REAL_RECEIPT, REAL_BUNDLE) == []
    manifest = json.loads(REAL_MANIFEST.read_text())
    assert manifest["source_disclosure_level"] == "COMMONS_NATIVE"
    assert manifest["commercial_impact"] == "NONE"
    assert manifest["release_class"] == "P3_PUBLIC_RELEASE_APPROVED"


def test_t1_valid_commercially_adjacent_public_source_passes(release_copy):
    assert release_copy("valid/VALID-02-public-source-complementary-p4").codes() == []


# T2 -------------------------------------------------------------------------

@pytest.mark.parametrize("state", ["NOT_REVIEWED", "REVIEW_IN_PROGRESS", "REJECTED", "SUPERSEDED"])
def test_t2_non_cleared_fails(release_copy, state):
    rel = release_copy()
    rel.both("clearance_status", state)
    assert "CLEARANCE_NOT_CLEARED" in rel.codes()


def test_t2_missing_receipt_fails(release_copy):
    rel = release_copy()
    rel.receipt_path.unlink()
    assert rel.codes() == ["MISSING_CLEARANCE_RECEIPT"]


def test_t2_receipt_and_manifest_must_agree(release_copy):
    rel = release_copy()
    rel.edit(lambda r: r.__setitem__("clearance_status", "REVIEW_IN_PROGRESS"), "receipt")
    assert {"CLEARANCE_NOT_CLEARED", "RECEIPT_MISMATCH"} <= set(rel.codes())


@pytest.mark.parametrize("status", ["FAIL", "PENDING", "NOT_APPLICABLE"])
def test_t2_every_dimension_must_pass(release_copy, status):
    rel = release_copy()
    rel.edit(lambda r: r["dimensions"]["provenance"].__setitem__("status", status), "receipt")
    assert "CLEARANCE_DIMENSION_NOT_PASSED" in rel.codes()


def test_t2_commercial_dimension_not_applicable_only_for_native_none(release_copy):
    rel = release_copy()
    rel.edit(lambda r: r["dimensions"]["commercial_impact"].__setitem__("status", "NOT_APPLICABLE"), "receipt")
    assert rel.codes() == []
    rel = release_copy("valid/VALID-02-public-source-complementary-p4")
    rel.edit(lambda r: r["dimensions"]["commercial_impact"].__setitem__("status", "NOT_APPLICABLE"), "receipt")
    assert "CLEARANCE_DIMENSION_NOT_PASSED" in rel.codes()


# T3 / T4 ---------------------------------------------------------------------

def test_t3_bundle_hash_mismatch_fails(release_copy):
    rel = release_copy()
    (rel.bundle / "README.txt").write_text("tampered\n")
    assert rel.codes() == ["HASH_MISMATCH"]


def test_t3_declared_digest_mismatch_fails(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("bundle_sha256", "0" * 64))
    assert "BUNDLE_DIGEST_MISMATCH" in rel.codes()


def test_t4_unknown_file_fails(release_copy):
    rel = release_copy()
    (rel.bundle / "stowaway.txt").write_text("not declared\n")
    assert rel.codes() == ["UNEXPECTED_FILE"]


def test_t4_missing_declared_file_fails(release_copy):
    rel = release_copy()
    (rel.bundle / "README.txt").unlink()
    assert rel.codes() == ["MISSING_FILE"]


def test_t4_symlink_in_bundle_fails(release_copy):
    rel = release_copy()
    try:
        (rel.bundle / "link").symlink_to(rel.bundle / "README.txt")
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    assert "IRREGULAR_FILE" in rel.codes()


@pytest.mark.parametrize("bad", ["../escape.txt", "/abs.txt", "a/./b.txt", "a//b.txt", "dir/"])
def test_t4_unsafe_paths_fail(release_copy, bad):
    rel = release_copy()
    rel.edit(lambda m: m["files"].append({"path": bad, "sha256": "0" * 64, "bytes": 0}))
    assert "UNSAFE_PATH" in rel.codes() or "SCHEMA_VIOLATION" in rel.codes()


# T5 -------------------------------------------------------------------------

def test_t5_uncertain_commercial_impact_fails_closed(release_copy):
    rel = release_copy()
    rel.both("commercial_impact", "UNCERTAIN")
    assert rel.codes() == ["COMMERCIAL_IMPACT_UNRESOLVED"]


@pytest.mark.parametrize("impact", ["CANNIBALIZATION_RISK", "CORE_DIFFERENTIATOR"])
def test_t5_high_risk_impact_requires_moat_and_human_authorization(release_copy, impact):
    rel = release_copy("valid/VALID-02-public-source-complementary-p4")
    rel.both("commercial_impact", impact)
    assert "HUMAN_AUTHORIZATION_MISSING" in rel.codes()
    rel.edit(lambda r: r.__setitem__("human_authorization", {
        "authorized": True, "authority_role": "commercial-review", "authorized_at": "2026-10-03T00:00:00Z"}),
        "receipt")
    assert rel.codes() == []
    rel.edit(lambda r: r.pop("minimum_viable_moat"), "receipt")
    assert rel.codes() == ["MOAT_REVIEW_MISSING"]


def test_t5_no_retained_surface_requires_strategic_review(release_copy):
    rel = release_copy("valid/VALID-02-public-source-complementary-p4")
    rel.edit(lambda r: r["minimum_viable_moat"].__setitem__("retained_surfaces", []), "receipt")
    assert rel.codes() == ["MOAT_REVIEW_MISSING"]
    rel.edit(lambda r: r["minimum_viable_moat"].__setitem__("strategic_review", {
        "decision": "Intentionally released in full.", "recorded_at": "2026-10-03T00:00:00Z"}), "receipt")
    assert rel.codes() == []


# T6 -------------------------------------------------------------------------

@pytest.mark.parametrize("cls", ["P0_INTERNAL_ONLY", "P1_REFERENCE_ONLY", "P2_PUBLIC_UTILITY_CANDIDATE"])
def test_t6_non_releasable_class_fails(release_copy, cls):
    rel = release_copy()
    rel.both("release_class", cls)
    assert rel.codes() == ["RELEASE_CLASS_NOT_RELEASABLE"]


# T7 -------------------------------------------------------------------------

LOCATORS = [
    "see https://example.invalid/origin",
    "see HTTPS://example.invalid/origin",
    "from git@example.invalid:org/origin.git",
    "from example.invalid/org/origin",
    "from www.example.invalid/x",
    "from Miskatonic-System" + "/some-private-repo",
    "at " + "a1b2c3d4e5" * 4,
    "at " + "A1B2C3D4E5" * 4,
    "at revision 3f2a9c1",
    "built in /home/someone/work/origin",
    "built in /tmp/build",
    "config in /etc/thing",
    "path:/data/x",
    "built from `/home/someone/origin/src`",
    "piped |/srv/origin",
    "redirected >/data/origin",
    "quoted '~build/origin'",
    "from example.invalid\uff0forg\uff0forigin",
    "built in ~/work/origin",
    "copied from C:\\work\\origin",
    "copied from \\\\fileserver\\share",
    "mirrored from build-host." + "internal",
    "served on localhost",
    "endpoint 10." + "1.2.3",
]


@pytest.mark.parametrize("level", ["PRIVATE_ORIGIN_OPAQUE", "COMMONS_NATIVE", "PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN"])
@pytest.mark.parametrize("text", LOCATORS)
def test_t7_opaque_or_native_metadata_rejects_locators(release_copy, level, text):
    rel = release_copy()
    if level != "COMMONS_NATIVE":
        rel.both("source_disclosure_level", level)
        rel.edit(lambda r: r.__setitem__("private_clearance_receipt",
                                         {"status": "HELD_PRIVATELY", "opaque_reference": "opaque-1234"}), "receipt")
    if level == "PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN":
        rel.edit(lambda m: m.__setitem__("source_attribution", {
            "public_origin_name": "Approved origin", "statement": "Name approved for disclosure."}))
    rel.edit(lambda m: m.__setitem__("summary", "Synthetic utility " + text))
    assert rel.codes() == ["PRIVATE_LOCATOR_LEAK"]


def test_t7_locator_in_receipt_rejected(release_copy):
    rel = release_copy()
    rel.edit(lambda r: r.__setitem__("scope_statement", "Cleared from git@example.invalid:org/x.git"), "receipt")
    assert rel.codes() == ["PRIVATE_LOCATOR_LEAK"]


@pytest.mark.parametrize("field", ["source_repository", "source_commit", "source_paths", "private_origin"])
def test_t7_locator_fields_are_not_part_of_the_schema(release_copy, field):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__(field, "anything"))
    assert "SCHEMA_VIOLATION" in rel.codes()


def test_t7_opaque_origin_cannot_carry_attribution(release_copy):
    rel = release_copy("invalid/INVALID-13-opaque-origin-with-attribution")
    assert rel.codes() == ["DISCLOSURE_INCOMPATIBLE"]


def test_t7_opaque_origin_needs_opaque_private_receipt_reference(release_copy):
    rel = release_copy()
    rel.both("source_disclosure_level", "PRIVATE_ORIGIN_OPAQUE")
    assert rel.codes() == ["DISCLOSURE_INCOMPATIBLE"]


def test_t7_sha256_hashes_are_not_mistaken_for_commit_ids(release_copy):
    # 64-hex file hashes appear in every manifest and must not trip the 40-hex rule.
    assert release_copy().codes() == []


# T8 / T9 ---------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Scientifically validated estimator.",
    "Peer-reviewed reference implementation.",
    "Proven method for evidence custody.",
    "Carries scientific authority for downstream results.",
    "Provides canonical evidence for experiments.",
    "Clinically useful screening helper.",
    "Security-certified validator.",
    "Compliant with every regulation.",
    "Production-ready with guaranteed uptime.",
    "The fastest validator available.",
])
def test_t8_scientific_and_assurance_claims_rejected(release_copy, text):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("summary", text))
    assert rel.codes() == ["PROHIBITED_CLAIM"]


@pytest.mark.parametrize("text", [
    "Clearance shows product-market fit.",
    "A profitable open primitive.",
    "Demonstrates willingness to pay among adopters.",
    "Commercially viable utility.",
    "Generates revenue for maintainers.",
])
def test_t9_commercial_claims_rejected(release_copy, text):
    rel = release_copy()
    rel.edit(lambda m: m["public_claim_boundary"].__setitem__("statement", text))
    assert rel.codes() == ["PROHIBITED_CLAIM"]


# SLA context handling (commons-export-lint 0.1.1, WO-COMMONS-MEMBRANE-EVALUATION-01B §12) ---------

SLA_AFFIRMATIVE = [
    "Backed by an SLA.",
    "Includes a 99.9% uptime SLA.",
    "SLA-backed support included.",
    "We offer an SLA to all users.",
    "Enterprise SLAs available on request.",
    "A service-level agreement is included.",
    # Wording built to slip past a negation or context rule:
    "Not only free but SLA-backed.",
    "It is not only SLA-backed but hosted.",
    "No question: it has an SLA.",
    "There is no doubt SLA coverage applies.",
    "We do not hesitate to offer an SLA.",
    "Without delay, an SLA applies.",
    "No SLA? Not here: every user gets an SLA.",
    "No SLA violations since launch.",
    "This release is never shipped without an SLA.",
    "This release is not SLA-free.",
    "Support means an SLA of 99.9% uptime.",
    "Includes an enterprise 'SLA'.",
    "This package may include an SLA for enterprise users.",
    "There is no better SLA in the industry.",
    "Backed by a 99.9% SLA, which stays valid outside business hours.",
    "Under the term SLA agreed with each customer, uptime is assured.",
    "This package does not provide an SLA, except for enterprise users.",
    "No SLA is offered to free users.",
    "SLAs remain outside this package for now, but are coming.",
]

SLA_NOT_A_CLAIM = [
    "This package does not provide an SLA.",
    "No SLA is offered.",
    "Provided without any SLA.",
    "It is not an SLA-backed service.",
    "Maintainers do not offer an SLA.",
    "Commercial operationalization may someday include SLA-backed service.",
    "The term `SLA` refers to a service-level agreement.",
    "SLAs remain outside this primitive.",
]


@pytest.mark.parametrize("text", SLA_AFFIRMATIVE)
def test_sla_affirmative_claim_rejected(release_copy, text):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("summary", text))
    assert rel.codes() == ["PROHIBITED_CLAIM"]


@pytest.mark.parametrize("text", SLA_NOT_A_CLAIM)
def test_sla_negation_prospect_or_term_is_not_a_claim(release_copy, text):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("summary", text))
    assert rel.codes() == []


@pytest.mark.parametrize("text", SLA_AFFIRMATIVE)
def test_sla_affirmative_claim_rejected_in_receipt(release_copy, text):
    rel = release_copy()
    rel.edit(lambda r: r.__setitem__("scope_statement", text), "receipt")
    assert rel.codes() == ["PROHIBITED_CLAIM"]


def test_sla_moat_enum_value_is_structural_not_a_claim():
    """The schema-fixed moat value "SLA" is exempt; the same word in free text is not."""
    findings = []
    lint.scan_claims("SLA", "receipt.minimum_viable_moat.retained_surfaces[0]", findings,
                     "$.minimum_viable_moat.retained_surfaces[0]")
    assert findings == []
    lint.scan_claims("SLA", "receipt.minimum_viable_moat.analysis", findings, "$.minimum_viable_moat.analysis")
    assert [f.code for f in findings] == ["PROHIBITED_CLAIM"]


def test_t8_t9_negations_belong_in_does_not_establish(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m["public_claim_boundary"]["does_not_establish"].extend(
        ["scientific authority", "profitability or product-market fit"]))
    assert rel.codes() == []


# T10 ------------------------------------------------------------------------

@pytest.mark.parametrize("which", ["manifest", "receipt"])
def test_t10_unknown_top_level_fields_rejected(release_copy, which):
    rel = release_copy()
    rel.edit(lambda d: d.__setitem__("unexpected", True), which)
    assert rel.codes() == ["SCHEMA_VIOLATION"]


def test_t10_unknown_nested_fields_rejected(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m["files"][0].__setitem__("mode", "0644"))
    assert "SCHEMA_VIOLATION" in rel.codes()
    rel = release_copy()
    rel.edit(lambda r: r["dimensions"].__setitem__("vibes", {"status": "PASS", "owner": "x", "basis": "y"}),
             "receipt")
    assert "SCHEMA_VIOLATION" in rel.codes()


def test_t10_index_rejects_unknown_fields(tmp_path):
    index = json.loads(INDEX.read_text())
    index["packages"][0]["download_url"] = "https://example.invalid"
    path = tmp_path / "index.json"
    path.write_bytes(lint.canonical_json_bytes(index))
    codes = {f.code for f in lint.check_index(path, ROOT)}
    assert "SCHEMA_VIOLATION" in codes


def test_t10_every_schema_object_forbids_undeclared_properties():
    def walk(node, path):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, path
            for key, value in node.items():
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}/{i}")
    for schema in (ROOT / "schemas").glob("*.json"):
        walk(json.loads(schema.read_text()), schema.name)


def test_t10_internal_validator_agrees_with_reference_jsonschema():
    jsonschema = pytest.importorskip("jsonschema")
    docs = []
    for path in sorted(FIXTURES.rglob("*.json")):
        if path.name == "manifest.json":
            docs.append(("manifest", path))
        elif path.name == "clearance-receipt.json":
            docs.append(("receipt", path))
        elif path.name == "package-index.json":
            docs.append(("index", path))
    docs += [("manifest", REAL_MANIFEST), ("receipt", REAL_RECEIPT), ("index", INDEX)]
    assert len(docs) > 30
    for kind, path in docs:
        schema = json.loads((ROOT / "schemas" / lint.SCHEMA_FILES[kind]).read_text())
        instance = json.loads(path.read_text())
        reference_ok = jsonschema.Draft202012Validator(schema).is_valid(instance)
        internal_ok = not lint.schema_errors(instance, schema)
        assert reference_ok == internal_ok, path.relative_to(ROOT)


def test_t10_validator_fails_closed_on_unsupported_keywords():
    with pytest.raises(lint.SchemaError):
        lint.schema_errors({}, {"type": "object", "oneOf": []})
    with pytest.raises(lint.SchemaError):
        lint.schema_errors({}, {"$ref": "https://example.invalid/schema.json"})


# T11 ------------------------------------------------------------------------

def test_t11_real_index_passes():
    assert lint.check_index(INDEX, ROOT) == []


def test_t11_index_contains_only_cleared_p3_p4():
    index = json.loads(INDEX.read_text())
    assert index["packages"], "the bootstrap index lists the Commons-native utility"
    for entry in index["packages"]:
        assert entry["clearance_status"] == "CLEARED"
        assert entry["release_class"] in lint.RELEASABLE_CLASSES
        assert entry["source_disclosure_level"] in ("COMMONS_NATIVE", "PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN")
        if entry["source_disclosure_level"] != "COMMONS_NATIVE":
            manifest = json.loads((ROOT / entry["manifest_path"]).read_text())
            receipt = json.loads((ROOT / entry["clearance_receipt_path"]).read_text())
            assert manifest["source_attribution"]["public_origin_name"]
            assert receipt["private_clearance_receipt"]["status"] == "HELD_PRIVATELY"


@pytest.mark.parametrize("field,value,code", [
    ("release_class", "P2_PUBLIC_UTILITY_CANDIDATE", "RELEASE_CLASS_NOT_RELEASABLE"),
    ("release_class", "P1_REFERENCE_ONLY", "RELEASE_CLASS_NOT_RELEASABLE"),
    ("clearance_status", "REVIEW_IN_PROGRESS", "CLEARANCE_NOT_CLEARED"),
    ("version", "0.2.0", "INDEX_MISMATCH"),
    ("manifest_path", "../outside.json", "UNSAFE_PATH"),
])
def test_t11_index_rejects_bad_entries(tmp_path, field, value, code):
    index = json.loads(INDEX.read_text())
    index["packages"][0][field] = value
    path = tmp_path / "index.json"
    path.write_bytes(lint.canonical_json_bytes(index))
    assert code in {f.code for f in lint.check_index(path, ROOT)}


def test_t11_index_rejects_duplicates(tmp_path):
    index = json.loads(INDEX.read_text())
    index["packages"].append(dict(index["packages"][0]))
    path = tmp_path / "index.json"
    path.write_bytes(lint.canonical_json_bytes(index))
    assert "INDEX_DUPLICATE_ENTRY" in {f.code for f in lint.check_index(path, ROOT)}


# Supporting cases --------------------------------------------------------------

def test_license_and_notice_rules(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("license", "NOASSERTION"))
    assert "LICENSE_MISSING" in rel.codes()
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("notices", ["NOT-IN-BUNDLE"]))
    assert "NOTICE_NOT_IN_BUNDLE" in rel.codes()


def test_apache_patent_grant_must_be_acknowledged(release_copy):
    rel = release_copy()
    rel.edit(lambda r: r.__setitem__("apache_patent_grant_acknowledged", False), "receipt")
    assert rel.codes() == ["PATENT_GRANT_NOT_ACKNOWLEDGED"]


def test_noncanonical_and_duplicate_key_json_rejected(release_copy):
    rel = release_copy()
    rel.manifest_path.write_text(json.dumps(rel.load(), indent=4))
    assert "NONCANONICAL_SERIALIZATION" in rel.codes()
    rel.manifest_path.write_text('{"a": 1, "a": 2}\n')
    assert "DUPLICATE_JSON_KEY" in rel.codes()


def test_unsorted_file_list_rejected(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("files", list(reversed(m["files"]))))
    assert "FILES_NOT_SORTED" in rel.codes()


def test_missing_bundle_fails(release_copy):
    rel = release_copy()
    codes = {f.code for f in lint.check_release(rel.manifest_path, rel.receipt_path, None)}
    assert "BUNDLE_NOT_PROVIDED" in codes


def test_cli_exit_codes(release_copy, capsys):
    rel = release_copy()
    args = ["check-release", "--manifest", str(rel.manifest_path), "--receipt", str(rel.receipt_path),
            "--bundle-root", str(rel.bundle)]
    assert lint.main(args) == 0
    (rel.bundle / "extra.txt").write_text("x\n")
    assert lint.main(args + ["--json"]) == 1
    out = capsys.readouterr().out
    assert '"UNEXPECTED_FILE"' in out
    assert lint.main(["canonicalize", str(rel.dir / "missing.json")]) == 2


def test_describe_bundle_matches_real_manifest():
    described = lint.describe_bundle(REAL_BUNDLE)
    manifest = json.loads(REAL_MANIFEST.read_text())
    assert described["files"] == manifest["files"]
    assert described["bundle_sha256"] == manifest["bundle_sha256"]


# Review round 1 repairs ---------------------------------------------------------

def test_locators_allowed_inside_approved_attribution_only(release_copy):
    rel = release_copy("valid/VALID-02-public-source-complementary-p4")
    assert rel.codes() == []  # its source_attribution carries a public URL
    rel.edit(lambda m: m.__setitem__("summary", "See https://example.org/fixture-origin"))
    assert rel.codes() == ["PRIVATE_LOCATOR_LEAK"]


def test_locator_in_receipt_basis_rejected(release_copy):
    rel = release_copy()
    rel.edit(lambda r: r["dimensions"]["provenance"].__setitem__("basis", "See example.invalid/org/repo"), "receipt")
    assert rel.codes() == ["PRIVATE_LOCATOR_LEAK"]


@pytest.mark.parametrize("value", ["Jane Doe", "jane.doe@example.com", "+1 555 010 0199", "Commons Maintainers"])
def test_receipt_owner_must_be_role_token(release_copy, value):
    rel = release_copy()
    rel.edit(lambda r: r["dimensions"]["security"].__setitem__("owner", value), "receipt")
    assert "SCHEMA_VIOLATION" in rel.codes()


@pytest.mark.parametrize("text", ["Contact jane.doe@example.com", "Call (555) 010-0199",
                                  "jane.doe@example.com: reviewer", "jane\uff20example.com"])
def test_personal_data_rejected_anywhere(release_copy, text):
    rel = release_copy()
    rel.edit(lambda r: r.__setitem__("scope_statement", text), "receipt")
    assert rel.codes() == ["PERSONAL_DATA"]


@pytest.mark.parametrize("field,where", [("scope_statement", "receipt"), ("summary", "manifest")])
def test_claims_scanned_beyond_summary(release_copy, field, where):
    rel = release_copy()
    rel.edit(lambda d: d.__setitem__(field, "This proves customer demand."), where)
    assert rel.codes() == ["PROHIBITED_CLAIM"]


def test_claims_in_dependency_purpose_rejected(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m["dependencies"]["runtime"].append(
        {"name": "x", "version": "1.0.0", "license": "MIT", "purpose": "Peer-reviewed parser."}))
    assert rel.codes() == ["PROHIBITED_CLAIM"]


def test_release_id_bound_to_package_and_version(release_copy):
    rel = release_copy()
    rel.both("public_release_id", "cpr-other-9.9.9")
    assert rel.codes() == ["RELEASE_ID_MISMATCH"]


def test_control_characters_rejected(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("approved_at", m["approved_at"] + "\n"))
    assert "CONTROL_CHARACTER" in rel.codes()


def test_bundle_must_ship_license_text(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("notices", ["NOTICE"]))
    assert rel.codes() == ["LICENSE_TEXT_MISSING"]


def test_private_deny_pattern_file(release_copy, tmp_path):
    rel = release_copy()
    rel.edit(lambda r: r.__setitem__("clearance_receipt_id", "ccr-secret-lab-export"), "receipt")
    rel.edit(lambda m: m.__setitem__("clearance_receipt_id", "ccr-secret-lab-export"))
    assert rel.codes() == []
    deny = tmp_path / "deny.txt"
    deny.write_text("# private names\nsecret-lab\n")
    args = ["--deny-pattern-file", str(deny), "check-release", "--manifest", str(rel.manifest_path),
            "--receipt", str(rel.receipt_path), "--bundle-root", str(rel.bundle), "--json"]
    assert lint.main(args, out=open(tmp_path / "out.json", "w")) == 1
    assert "denied pattern #1" in (tmp_path / "out.json").read_text()


def test_manifest_clearance_state_checked_independently(release_copy):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("clearance_status", "REJECTED"))
    findings = lint.check_release(rel.manifest_path, rel.receipt_path, rel.bundle)
    assert ("CLEARANCE_NOT_CLEARED", "manifest.clearance_status") in {(f.code, f.where) for f in findings}


def test_native_release_cannot_claim_private_receipt(release_copy):
    rel = release_copy()
    rel.edit(lambda r: r.__setitem__("private_clearance_receipt",
                                     {"status": "HELD_PRIVATELY", "opaque_reference": "opaque-1234"}), "receipt")
    assert rel.codes() == ["DISCLOSURE_INCOMPATIBLE"]


@pytest.mark.parametrize("text", ["and/or", "N/A", "Python 3.12/3.13", "input / output"])
def test_ordinary_slashes_are_not_paths(release_copy, text):
    rel = release_copy()
    rel.edit(lambda m: m.__setitem__("summary", "A synthetic tool for " + text + " checks."))
    assert rel.codes() == []
