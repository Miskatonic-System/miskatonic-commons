#!/usr/bin/env python3
# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Regenerate release metadata for the packages listed in RELEASES.

Writes, for each package listed in RELEASES, the release manifest and public
clearance receipt under releases/<package>/<version>/, then the package index.
File hashes and the bundle digest are computed from the bundle on disk; every
other field is declared here and reviewed like any other change.

This script only assembles metadata. It does not decide clearance, publish
anything, or contact any service.

Usage: python scripts/build_release_metadata.py [--check]
  --check   exit 1 if any generated file differs from the committed bytes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location(
    "commons_export_lint", ROOT / "tools" / "commons-export-lint" / "commons_export_lint.py")
lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lint)

RELEASES = [
    {
        "package_id": "commons-export-lint",
        "display_name": "commons-export-lint",
        "version": "0.1.1",
        "bundle_root": "tools/commons-export-lint",
        "summary": ("A standard-library Python command-line tool that checks Commons release "
                    "manifests, clearance receipts, release bundles and the package index for "
                    "completeness and consistency."),
        "release_class": "P3_PUBLIC_RELEASE_APPROVED",
        "commercial_impact": "NONE",
        "source_disclosure_level": "COMMONS_NATIVE",
        "claim_statement": ("Cleared for public distribution under its recorded scope: a metadata "
                            "consistency lint for Commons release records, written directly in Commons."),
        "does_not_establish": [
            "that any artifact checked by this tool is correct, safe, secure or fit for any purpose",
            "that any review recorded in a clearance receipt actually took place",
            "any scientific, safety, security, compliance, clinical or performance result",
            "that any private Miskatonic software has been cleared or released",
            "commercial demand, profitability, product status or paid support",
            "that absence of findings means absence of secrets or private information",
        ],
        "license": "Apache-2.0",
        "notices": ["LICENSE", "NOTICE"],
        "support_class": "COMMUNITY_BEST_EFFORT",
        "clearance_receipt_id": "ccr-commons-native-commons-export-lint-0-1-1",
        "approved_at": "2026-10-04T15:47:57Z",
        "scope_statement": ("Release 0.1.1 of commons-export-lint: exactly the files listed in the "
                            "manifest, bound by bundle_sha256. Maintenance of 0.1.0 (the claim scan judges the "
                            "term `SLA` in context). Written in Commons; it has no private ancestry and "
                            "exports no private technology."),
        "dimensions": {
            "originating_technical": "Commons-native; behavior defined by its README and exercised by the "
                                     "repository test suite and synthetic fixtures.",
            "provenance": "Authored directly in this repository on a history descending only from the "
                          "recorded clean root commit; no imported files.",
            "security": "Repository sensitive-data check and pinned gitleaks scan in CI; the tool imports "
                        "only allow-listed standard-library modules and opens no network connections.",
            "dependency_license": "No runtime dependencies beyond the Python standard library. Apache-2.0 "
                                  "LICENSE and NOTICE included in the bundle; patent grant acknowledged.",
            "commercial_impact": "Not applicable: Commons-native with commercial impact NONE; no private "
                                 "technology is exported.",
            "public_packaging": "Standalone README, bundled schemas, tests, fixtures and best-effort "
                                "support class reviewed by Commons maintainers.",
        },
    },
    {
        "package_id": "algorithm-trace-core",
        "display_name": "AlgorithmTrace v0.4 Public Core",
        "version": "0.1.1",
        "bundle_root": "libraries/algorithm-trace-core",
        "summary": ("A Python library for typed execution traces over declared storage: canonical JSONL, "
                    "content-addressed trace profiles, a generic recorder, a deterministic replay and reference "
                    "validator with stable error codes, and logical metrics (protocol 0.4)."),
        "release_class": "P3_PUBLIC_RELEASE_APPROVED",
        "commercial_impact": "COMPLEMENTARY",
        "source_disclosure_level": "PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN",
        "source_attribution": {
            "public_origin_name": "Miskatonic-System/msk-algorithms",
            "statement": ("Extracted from the generic AlgorithmTrace v0.4 core of the private repository "
                          "Miskatonic-System/msk-algorithms at commit 449bfdb2e823993c699a033d8a75e3c8171f9176, "
                          "under a source clearance merged there as 391e5171a4188aeb19fdfdeec37370017649def6. "
                          "PROVENANCE.json in the bundle maps every public file to its source or marks it Commons-native."),
        },
        "claim_statement": ("Cleared for public distribution under its recorded scope: a generic trace, recording, "
                            "profile-binding, replay and logical-metrics substrate with a synthetic example profile."),
        "does_not_establish": [
            "correctness or optimality of any implementation or algorithm",
            "coverage of arbitrary algorithm domains; each profile is a separate claim",
            "source provenance or producer identity from digests alone",
            "any scientific result, or the research authority of the private origin",
            "reproduction of any private qualification",
            "production security or suitability for safety-critical use",
            "commercial value, product status or paid support",
        ],
        "license": "Apache-2.0",
        "notices": ["LICENSE", "NOTICE"],
        "support_class": "COMMUNITY_BEST_EFFORT",
        "clearance_receipt_id": "ccr-algorithm-trace-core-0-1-1",
        "approved_at": "2026-10-04T15:47:57Z",
        "dependencies": {"inventory_complete": True, "runtime": [
            {"name": "rfc8785", "version": "0.1.4", "license": "Apache-2.0", "purpose": "RFC 8785 canonical JSON (supported range >=0.1.4,<0.2)"},
            {"name": "jsonschema", "version": "4.26.0", "license": "MIT", "purpose": "Schema self-checks and run-record validation (supported range >=4.18,<5)"},
            {"name": "fastjsonschema", "version": "2.22.2", "license": "BSD-3-Clause", "purpose": "Compiled event and profile validation (supported range >=2.19,<3)"}],
            "development": [{"name": "pytest", "version": "9.1.1", "license": "MIT", "purpose": "Test runner"}]},
        "scope_statement": ("Release 0.1.1 of algorithm-trace-core: exactly the files listed in the manifest, bound by "
                            "bundle_sha256. Maintenance of the already-cleared 0.1.0 artifact under "
                            "WO-COMMONS-MEMBRANE-EVALUATION-01B: no new private source, no source membrane expansion, "
                            "not a second private-origin export. Generic AlgorithmTrace v0.4 substrate only; no domain "
                            "profile, algorithm implementation, experiment or research record of the origin is included."),
        "dimension_owners": {"originating_technical": "msk-algorithms-maintainers", "provenance": "commons-maintainers",
                             "security": "commons-maintainers", "dependency_license": "commons-maintainers",
                             "commercial_impact": "repository-owner", "public_packaging": "commons-maintainers"},
        "dimensions": {
            "originating_technical": "Source clearance by the originating repository: 11 allowlisted files at the frozen source, 6 extracted symbols, closed import set, approved transformation classes.",
            "provenance": "Clean extraction onto Commons main with no private history; every public file mapped in PROVENANCE.json; private-to-public parity and transformation checks recorded there.",
            "security": "gitleaks and the Commons sensitive-data check over the source allowlist and the public bundle; 0 findings. Absence of findings is not proof.",
            "dependency_license": "Runtime dependencies rfc8785 (Apache-2.0), jsonschema (MIT), fastjsonschema (BSD-3-Clause); no private dependency; owner authorized Apache-2.0; patent grant acknowledged.",
            "commercial_impact": "Human commercial adjudication by the repository owner: COMPLEMENTARY. The commercial review inputs are recorded in the private clearance receipt.",
            "public_packaging": "Standalone package with README, synthetic example profile, hostile-control tests, provenance record and best-effort support class.",
        },
        "private_clearance_receipt": {"status": "HELD_PRIVATELY", "opaque_reference": "SRC-CLEARANCE-WO-COMMONS-FIRST-EXPORT-01A"},
        "minimum_viable_moat": {
            "question": "AFTER THIS ARTIFACT IS AVAILABLE FOR FREE, WHAT ECONOMICALLY VALUABLE FUNCTION REMAINS?",
            "retained_surfaces": ["MANAGED_PROVENANCE", "ORGANIZATION_WIDE_GOVERNANCE", "POLICY_MANAGEMENT", "IDENTITY_INTEGRATION",
                                  "ENTERPRISE_INTEGRATIONS", "MANAGED_HOSTING", "PRIVATE_DEPLOYMENT", "ASSURANCE_SERVICES",
                                  "SUPPORT", "SLA", "PROPRIETARY_ADAPTERS", "OTHER"],
            "analysis": ("Domain-specific profiles and their semantics, the research and evaluation infrastructure, "
                         "organization-wide evidence custody and cross-repository provenance, managed verification, "
                         "policy and identity governance, integrations, hosting, private deployment, audit reporting, "
                         "assurance, support and SLAs all remain outside this primitive. Nothing was withheld to "
                         "create scarcity."),
        },
    },
]


def build(rel: dict) -> tuple[dict, dict, dict]:
    described = lint.describe_bundle(ROOT / rel["bundle_root"])
    release_id = f"cpr-{rel['package_id']}-{rel['version']}"
    manifest = {
        "schema_version": "commons.public-release-manifest.v0.1",
        "provenance_format_version": "commons.provenance.v0.1",
        "public_release_id": release_id,
        "package_id": rel["package_id"],
        "display_name": rel["display_name"],
        "version": rel["version"],
        "summary": rel["summary"],
        "release_class": rel["release_class"],
        "commercial_impact": rel["commercial_impact"],
        "source_disclosure_level": rel["source_disclosure_level"],
        "public_claim_boundary": {"statement": rel["claim_statement"],
                                  "does_not_establish": rel["does_not_establish"]},
        "license": rel["license"],
        "notices": rel["notices"],
        "files": described["files"],
        "bundle_digest_algorithm": described["bundle_digest_algorithm"],
        "bundle_sha256": described["bundle_sha256"],
        "dependencies": rel.get("dependencies", {"inventory_complete": True, "runtime": [], "development": []}),
        "support_class": rel["support_class"],
        "clearance_receipt_id": rel["clearance_receipt_id"],
        "clearance_status": "CLEARED",
        "approved_at": rel["approved_at"],
        "imported_at": rel.get("imported_at", rel["approved_at"]),
    }
    if "source_attribution" in rel:
        manifest["source_attribution"] = rel["source_attribution"]
    dims = {}
    native = rel["source_disclosure_level"] == "COMMONS_NATIVE"
    for name, basis in rel["dimensions"].items():
        status = "NOT_APPLICABLE" if (name == "commercial_impact" and native) else "PASS"
        owner = rel.get("dimension_owners", {}).get(name, "commons-maintainers")
        dims[name] = {"status": status, "owner": owner, "basis": basis}
    receipt = {
        "schema_version": "commons.public-clearance-receipt.v0.1",
        "clearance_receipt_id": rel["clearance_receipt_id"],
        "public_release_id": release_id,
        "package_id": rel["package_id"],
        "version": rel["version"],
        "release_class": rel["release_class"],
        "commercial_impact": rel["commercial_impact"],
        "source_disclosure_level": rel["source_disclosure_level"],
        "bundle_sha256": described["bundle_sha256"],
        "clearance_status": "CLEARED",
        "scope_statement": rel["scope_statement"],
        "dimensions": dims,
        "private_clearance_receipt": rel.get("private_clearance_receipt", {"status": "NOT_APPLICABLE_COMMONS_NATIVE"}),
        "apache_patent_grant_acknowledged": True,
        "completed_at": rel["approved_at"],
    }
    if "minimum_viable_moat" in rel:
        receipt["minimum_viable_moat"] = rel["minimum_viable_moat"]
    base = f"releases/{rel['package_id']}/{rel['version']}"
    entry = {key: manifest[key] for key in lint.INDEX_MIRRORED_FIELDS} | {
        "manifest_path": f"{base}/manifest.json",
        "clearance_receipt_path": f"{base}/clearance-receipt.json",
        "bundle_root": rel["bundle_root"],
        "status": "ACTIVE",
    }
    return manifest, receipt, entry


def main(argv) -> int:
    check = "--check" in argv
    outputs = {}
    entries = []
    for rel in RELEASES:
        manifest, receipt, entry = build(rel)
        base = ROOT / "releases" / rel["package_id"] / rel["version"]
        outputs[base / "manifest.json"] = lint.canonical_json_bytes(manifest)
        outputs[base / "clearance-receipt.json"] = lint.canonical_json_bytes(receipt)
        entries.append(entry)
    entries.sort(key=lambda e: (e["package_id"], e["version"]))
    outputs[ROOT / "releases" / "package-index-v0.1.json"] = lint.canonical_json_bytes(
        {"schema_version": "commons.package-index.v0.1", "packages": entries})
    stale = []
    for path, data in outputs.items():
        current = path.read_bytes() if path.exists() else None
        if current != data:
            stale.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    for p in stale:
        print(("STALE\t" if check else "wrote\t") + p)
    return 1 if (check and stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
