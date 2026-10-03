#!/usr/bin/env python3
# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Regenerate release metadata for Commons-native packages.

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
        "version": "0.1.0",
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
        "clearance_receipt_id": "ccr-commons-native-commons-export-lint-0-1-0",
        "approved_at": "2026-10-03T00:00:00Z",
        "scope_statement": ("Release 0.1.0 of commons-export-lint: exactly the files listed in the "
                            "manifest, bound by bundle_sha256. Written in Commons for the Commons "
                            "bootstrap; it has no private ancestry and exports no private technology."),
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
        "dependencies": {"inventory_complete": True, "runtime": [], "development": []},
        "support_class": rel["support_class"],
        "clearance_receipt_id": rel["clearance_receipt_id"],
        "clearance_status": "CLEARED",
        "approved_at": rel["approved_at"],
    }
    dims = {}
    for name, basis in rel["dimensions"].items():
        status = "NOT_APPLICABLE" if name == "commercial_impact" else "PASS"
        dims[name] = {"status": status, "owner": "commons-maintainers", "basis": basis}
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
        "private_clearance_receipt": {"status": "NOT_APPLICABLE_COMMONS_NATIVE"},
        "apache_patent_grant_acknowledged": True,
        "completed_at": rel["approved_at"],
    }
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
