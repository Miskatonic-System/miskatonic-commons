#!/usr/bin/env python3
# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Deterministically generate the synthetic export fixtures.

All fixtures are synthetic. They contain no real software, no secrets and no
copied private source. Expected outcomes are declared here by intent (the
finding codes each fixture is built to trigger); they are not computed by
running the linter, so replaying the fixtures is an independent check.

Usage: python scripts/generate_fixtures.py [OUTPUT_DIR]   (default: fixtures/)
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

STAMP = "2026-10-03T00:00:00Z"

BUNDLE = {
    "NOTICE": "Synthetic Commons fixture notice. This bundle contains no real software.\n",
    "README.txt": "Synthetic Commons fixture bundle used only to exercise release validation.\n",
    "data/example.json": '{"example": true}\n',
}

DOES_NOT_ESTABLISH = [
    "correctness or fitness for any purpose",
    "any scientific, safety, security, compliance or performance claim",
    "commercial demand, profitability or product support",
]


def canonical(obj) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def file_entries(bundle: dict) -> list:
    return [{"path": p, "sha256": hashlib.sha256(c.encode()).hexdigest(), "bytes": len(c.encode())}
            for p, c in sorted(bundle.items())]


def digest(files: list) -> str:
    lines = sorted(f"{f['sha256']}  {f['path']}\n" for f in files)
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def base_release(package_id: str):
    files = file_entries(BUNDLE)
    version = "0.1.0"
    manifest = {
        "schema_version": "commons.public-release-manifest.v0.1",
        "provenance_format_version": "commons.provenance.v0.1",
        "public_release_id": f"cpr-{package_id}-{version}",
        "package_id": package_id,
        "display_name": "Synthetic fixture package",
        "version": version,
        "summary": "A synthetic bundle that exists only to exercise Commons release validation.",
        "release_class": "P3_PUBLIC_RELEASE_APPROVED",
        "commercial_impact": "NONE",
        "source_disclosure_level": "COMMONS_NATIVE",
        "public_claim_boundary": {
            "statement": "This synthetic bundle was cleared for distribution under its recorded scope only.",
            "does_not_establish": list(DOES_NOT_ESTABLISH),
        },
        "license": "Apache-2.0",
        "notices": ["NOTICE"],
        "files": files,
        "bundle_digest_algorithm": "commons.bundle-digest.v0.1",
        "bundle_sha256": digest(files),
        "dependencies": {"inventory_complete": True, "runtime": [], "development": []},
        "support_class": "COMMUNITY_BEST_EFFORT",
        "clearance_receipt_id": f"ccr-fixture-{package_id}",
        "clearance_status": "CLEARED",
        "approved_at": STAMP,
    }
    receipt = {
        "schema_version": "commons.public-clearance-receipt.v0.1",
        "clearance_receipt_id": manifest["clearance_receipt_id"],
        "public_release_id": manifest["public_release_id"],
        "package_id": package_id,
        "version": version,
        "release_class": manifest["release_class"],
        "commercial_impact": manifest["commercial_impact"],
        "source_disclosure_level": manifest["source_disclosure_level"],
        "bundle_sha256": manifest["bundle_sha256"],
        "clearance_status": "CLEARED",
        "scope_statement": "Synthetic fixture bundle only.",
        "dimensions": {name: {"status": "PASS", "owner": "commons-maintainers", "basis": "Synthetic fixture."}
                       for name in ("originating_technical", "provenance", "security",
                                    "dependency_license", "commercial_impact", "public_packaging")},
        "private_clearance_receipt": {"status": "NOT_APPLICABLE_COMMONS_NATIVE"},
        "apache_patent_grant_acknowledged": True,
        "completed_at": STAMP,
    }
    return manifest, receipt, dict(BUNDLE)


def set_both(m, r, field, value):
    m[field] = value
    r[field] = value


def private_origin(m, r, level, ref):
    set_both(m, r, "source_disclosure_level", level)
    r["private_clearance_receipt"] = {"status": "HELD_PRIVATELY", "opaque_reference": ref}


def moat(r, surfaces, analysis="Fixture analysis of what remains valuable once the artifact is free."):
    r["minimum_viable_moat"] = {
        "question": "AFTER THIS ARTIFACT IS AVAILABLE FOR FREE, WHAT ECONOMICALLY VALUABLE FUNCTION REMAINS?",
        "retained_surfaces": surfaces,
        "analysis": analysis,
    }


def build():
    """Return {relative_dir: (manifest, receipt_or_None, bundle, expected_codes)} plus index fixtures."""
    out = {}

    m, r, b = base_release("fixture-valid-01")
    out["valid/VALID-01-commons-native-p3-none"] = (m, r, b, [])

    m, r, b = base_release("fixture-valid-02")
    private_origin(m, r, "PUBLIC_SOURCE", "fixture-opaque-0002")
    set_both(m, r, "commercial_impact", "COMPLEMENTARY")
    set_both(m, r, "release_class", "P4_PUBLIC_STRATEGIC_OPEN_SOURCE")
    m["source_attribution"] = {"public_origin_name": "Example public origin project",
                               "public_origin_url": "https://example.org/fixture-origin",
                               "statement": "Derived from an already public example project."}
    moat(r, ["MANAGED_HOSTING", "SUPPORT"])
    out["valid/VALID-02-public-source-complementary-p4"] = (m, r, b, [])

    m, r, b = base_release("fixture-invalid-01")
    out["invalid/INVALID-01-missing-clearance-receipt"] = (m, None, b, ["MISSING_CLEARANCE_RECEIPT"])

    m, r, b = base_release("fixture-invalid-02")
    set_both(m, r, "commercial_impact", "UNCERTAIN")
    out["invalid/INVALID-02-uncertain-commercial-impact"] = (m, r, b, ["COMMERCIAL_IMPACT_UNRESOLVED"])

    m, r, b = base_release("fixture-invalid-03")
    b["README.txt"] = "Synthetic Commons fixture bundle, modified after the manifest was written.\n"
    out["invalid/INVALID-03-hash-mismatch"] = (m, r, b, ["HASH_MISMATCH"])

    m, r, b = base_release("fixture-invalid-04")
    private_origin(m, r, "PRIVATE_ORIGIN_OPAQUE", "fixture-opaque-0004")
    m["summary"] = ("Synthetic utility extracted from git@example.invalid:example-private-org/internal-origin.git "
                    "at " + "0123456789abcdef" * 2 + "01234567.")
    out["invalid/INVALID-04-opaque-origin-locator-leak"] = (m, r, b, ["PRIVATE_LOCATOR_LEAK"])

    m, r, b = base_release("fixture-invalid-05")
    m["summary"] = "Scientifically validated reference implementation of the synthetic method."
    out["invalid/INVALID-05-unsupported-scientific-claim"] = (m, r, b, ["PROHIBITED_CLAIM"])

    m, r, b = base_release("fixture-invalid-06")
    set_both(m, r, "release_class", "P5_UNRESTRICTED")
    out["invalid/INVALID-06-unknown-release-class"] = (m, r, b,
                                                       ["RELEASE_CLASS_NOT_RELEASABLE", "SCHEMA_VIOLATION"])

    m, r, b = base_release("fixture-invalid-07")
    m["dependencies"] = {"inventory_complete": False,
                         "runtime": [{"name": "example-dependency", "version": "1.0.0",
                                      "purpose": "Synthetic dependency without a declared license."}],
                         "development": []}
    out["invalid/INVALID-07-incomplete-dependency-license"] = (
        m, r, b, ["DEPENDENCY_INVENTORY_INCOMPLETE", "DEPENDENCY_LICENSE_MISSING", "SCHEMA_VIOLATION"])

    m, r, b = base_release("fixture-invalid-08")
    b["extra/undeclared.txt"] = "This file is present in the bundle but absent from the manifest.\n"
    out["invalid/INVALID-08-undeclared-bundle-file"] = (m, r, b, ["UNEXPECTED_FILE"])

    m, r, b = base_release("fixture-invalid-09")
    set_both(m, r, "clearance_status", "REVIEW_IN_PROGRESS")
    out["invalid/INVALID-09-not-cleared"] = (m, r, b, ["CLEARANCE_NOT_CLEARED"])

    m, r, b = base_release("fixture-invalid-10")
    set_both(m, r, "release_class", "P1_REFERENCE_ONLY")
    out["invalid/INVALID-10-reference-only-release"] = (m, r, b, ["RELEASE_CLASS_NOT_RELEASABLE"])

    m, r, b = base_release("fixture-invalid-11")
    m["public_claim_boundary"]["statement"] = "Clearance demonstrates product-market fit for this utility."
    out["invalid/INVALID-11-commercial-claim"] = (m, r, b, ["PROHIBITED_CLAIM"])

    m, r, b = base_release("fixture-invalid-12")
    m["internal_notes"] = "An undeclared property."
    out["invalid/INVALID-12-unknown-manifest-field"] = (m, r, b, ["SCHEMA_VIOLATION"])

    m, r, b = base_release("fixture-invalid-13")
    private_origin(m, r, "PRIVATE_ORIGIN_OPAQUE", "fixture-opaque-0013")
    m["source_attribution"] = {"public_origin_name": "Example internal origin",
                               "statement": "Names an origin that was not approved for disclosure."}
    out["invalid/INVALID-13-opaque-origin-with-attribution"] = (m, r, b, ["DISCLOSURE_INCOMPATIBLE"])

    m, r, b = base_release("fixture-invalid-14")
    private_origin(m, r, "PRIVATE_ORIGIN_OPAQUE", "fixture-opaque-0014")
    set_both(m, r, "commercial_impact", "CANNIBALIZATION_RISK")
    moat(r, ["MANAGED_HOSTING"])
    out["invalid/INVALID-14-cannibalization-without-authorization"] = (m, r, b, ["HUMAN_AUTHORIZATION_MISSING"])

    m, r, b = base_release("fixture-invalid-15")
    private_origin(m, r, "PRIVATE_ORIGIN_OPAQUE", "fixture-opaque-0015")
    set_both(m, r, "commercial_impact", "COMPLEMENTARY")
    moat(r, [])
    out["invalid/INVALID-15-no-retained-surface-without-strategic-review"] = (m, r, b, ["MOAT_REVIEW_MISSING"])

    m, r, b = base_release("fixture-invalid-16")
    r["bundle_sha256"] = hashlib.sha256(b"a different bundle").hexdigest()
    out["invalid/INVALID-16-receipt-bundle-mismatch"] = (m, r, b, ["RECEIPT_MISMATCH"])

    m, r, b = base_release("fixture-invalid-17")
    r["dimensions"]["security"] = {"status": "PENDING", "owner": "security-review", "basis": "Not yet reviewed."}
    out["invalid/INVALID-17-security-dimension-pending"] = (m, r, b, ["CLEARANCE_DIMENSION_NOT_PASSED"])
    return out


def index_entry(m, prefix="release"):
    return {key: m[key] for key in ("package_id", "display_name", "version", "release_class",
                                    "commercial_impact", "source_disclosure_level", "license",
                                    "support_class", "clearance_status")} | {
        "manifest_path": f"{prefix}/manifest.json",
        "clearance_receipt_path": f"{prefix}/clearance-receipt.json",
        "bundle_root": f"{prefix}/bundle",
        "status": "ACTIVE",
    }


def build_index_fixtures():
    out = {}
    m, r, b = base_release("fixture-index-valid-01")
    out["valid/INDEX-VALID-01-cleared-entry"] = (
        {"schema_version": "commons.package-index.v0.1", "packages": [index_entry(m)]}, m, r, b, [])
    m, r, b = base_release("fixture-index-invalid-01")
    set_both(m, r, "release_class", "P2_PUBLIC_UTILITY_CANDIDATE")
    set_both(m, r, "clearance_status", "REVIEW_IN_PROGRESS")
    out["invalid/INDEX-INVALID-01-uncleared-candidate-entry"] = (
        {"schema_version": "commons.package-index.v0.1", "packages": [index_entry(m)]}, m, r, b,
        ["CLEARANCE_NOT_CLEARED", "RELEASE_CLASS_NOT_RELEASABLE", "SCHEMA_VIOLATION"])
    return out


def write_bundle(root: Path, bundle: dict):
    for rel, content in bundle.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content.encode("utf-8"))


def generate(dest: Path):
    for group in ("valid", "invalid"):
        if (dest / group).exists():
            shutil.rmtree(dest / group)
    expected = {}
    for rel, (m, r, b, codes) in build().items():
        d = dest / rel
        d.mkdir(parents=True)
        (d / "manifest.json").write_bytes(canonical(m))
        if r is not None:
            (d / "clearance-receipt.json").write_bytes(canonical(r))
        write_bundle(d / "bundle", b)
        expected[rel] = sorted(codes)
    for rel, (idx, m, r, b, codes) in build_index_fixtures().items():
        d = dest / rel
        (d / "release").mkdir(parents=True)
        (d / "package-index.json").write_bytes(canonical(idx))
        (d / "release" / "manifest.json").write_bytes(canonical(m))
        (d / "release" / "clearance-receipt.json").write_bytes(canonical(r))
        write_bundle(d / "release" / "bundle", b)
        expected[rel] = sorted(codes)
    (dest / "expected-results.json").write_bytes(canonical({
        "fixture_results": dict(sorted(expected.items())),
        "format": "commons.fixture-replay.v0.1",
        "tool": "commons-export-lint",
        "tool_version": "0.1.0",
    }))


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "fixtures"
    target.mkdir(parents=True, exist_ok=True)
    generate(copy.copy(target))
