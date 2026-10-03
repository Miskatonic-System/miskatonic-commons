#!/usr/bin/env python3
# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""commons-export-lint: validate Miskatonic Commons public release metadata.

This tool checks public release manifests, public clearance receipts, release
bundles and the public package index against the Commons v0.1 schemas and
export rules. It is deliberately small and conservative:

* it uses only the Python standard library;
* it never opens network connections;
* it never contacts, resolves or authenticates against any private system;
* it never publishes, authorizes or modifies anything except when explicitly
  asked to rewrite a JSON file into canonical form (``canonicalize --write``);
* it collects no telemetry.

Passing this lint means only that the metadata is internally consistent and
complete under the recorded rules. It does not establish that an artifact is
correct, safe, secure, scientifically valid or commercially useful, and it
cannot verify that a human review recorded in a receipt actually took place.

Exit status: 0 = no findings, 1 = findings reported, 2 = usage or I/O error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

TOOL_NAME = "commons-export-lint"
TOOL_VERSION = "0.1.0"

SCHEMA_FILES = {
    "manifest": "public-release-manifest-v0.1.schema.json",
    "receipt": "public-clearance-receipt-v0.1.schema.json",
    "index": "commons-package-index-v0.1.schema.json",
}

RELEASE_CLASSES = (
    "P0_INTERNAL_ONLY",
    "P1_REFERENCE_ONLY",
    "P2_PUBLIC_UTILITY_CANDIDATE",
    "P3_PUBLIC_RELEASE_APPROVED",
    "P4_PUBLIC_STRATEGIC_OPEN_SOURCE",
)
RELEASABLE_CLASSES = ("P3_PUBLIC_RELEASE_APPROVED", "P4_PUBLIC_STRATEGIC_OPEN_SOURCE")

COMMERCIAL_IMPACTS = (
    "NONE",
    "COMPLEMENTARY",
    "LEAD_GENERATING",
    "UNCERTAIN",
    "CANNIBALIZATION_RISK",
    "CORE_DIFFERENTIATOR",
)
# Commercially adjacent classes require a minimum-viable-moat review.
MOAT_REVIEW_REQUIRED = (
    "COMPLEMENTARY",
    "LEAD_GENERATING",
    "CANNIBALIZATION_RISK",
    "CORE_DIFFERENTIATOR",
)
# These classes additionally require a recorded explicit human authorization.
HUMAN_AUTHORIZATION_REQUIRED = ("CANNIBALIZATION_RISK", "CORE_DIFFERENTIATOR")

DISCLOSURE_LEVELS = (
    "PUBLIC_SOURCE",
    "PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN",
    "PRIVATE_ORIGIN_OPAQUE",
    "COMMONS_NATIVE",
)
ATTRIBUTION_ALLOWED = ("PUBLIC_SOURCE", "PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN")
# For these levels no source locator of any kind may appear in public metadata.
LOCATOR_FORBIDDEN = ("PRIVATE_ORIGIN_OPAQUE", "COMMONS_NATIVE")

CLEARANCE_STATES = ("NOT_REVIEWED", "REVIEW_IN_PROGRESS", "CLEARED", "REJECTED", "SUPERSEDED")

CLEARANCE_DIMENSIONS = (
    "originating_technical",
    "provenance",
    "security",
    "dependency_license",
    "commercial_impact",
    "public_packaging",
)

BUNDLE_DIGEST_ALGORITHM = "commons.bundle-digest.v0.1"

# Text that would upgrade a public release into a scientific, safety, security,
# compliance, clinical, performance or commercial claim. Checked only in
# affirmative fields; negations belong in public_claim_boundary.does_not_establish.
PROHIBITED_CLAIM_PATTERNS = (
    ("scientific", r"\bscientific(ally)?\s+(valid|validated|proven|established|authority|authoritative|truth)"),
    ("scientific", r"\bpeer[- ]reviewed\b"),
    ("scientific", r"\bproven\b"),
    ("scientific", r"\bcanonical\s+(scientific|evidence|truth|result)"),
    ("clinical", r"\bclinical(ly)?\b|\bdiagnos(is|tic|e)\b|\bFDA\b"),
    ("safety_security", r"\b(safety|security)[- ](certified|guaranteed|approved|proven)\b"),
    ("compliance", r"\bcertified\b|\bcertification\b|\bcompliant\b|\bcompliance\b"),
    ("assurance", r"\bguarantee(s|d)?\b|\bwarrant(y|ies|ed)\b|\bSLA\b|\bproduction[- ]ready\b"),
    ("performance", r"\bfastest\b|\bbest[- ]in[- ]class\b|\bstate[- ]of[- ]the[- ]art\b"),
    ("commercial", r"\bprofit(s|able|ability)?\b|\bproduct[- ]market[- ]fit\b|\brevenue\b"),
    ("commercial", r"\bwillingness[- ]to[- ]pay\b|\bcommercial(ly)?\s+(viable|viability|validated)\b"),
)

# Source locators that must never appear in opaque or Commons-native metadata.
LOCATOR_PATTERNS = (
    ("url", r"\b(https?|ssh|git|file|svn|hg)://"),
    ("scp_remote", r"\b[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[A-Za-z0-9._~/-]+"),
    ("commit_id", r"(?<![0-9A-Fa-f])[0-9a-f]{40}(?![0-9A-Fa-f])"),
    ("absolute_path", r"(^|[\s\"'(=])/(home|Users|root|srv|opt|var|mnt|private|workspace)/"),
    ("windows_path", r"\b[A-Za-z]:\\"),
)

SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

class Finding:
    __slots__ = ("code", "where", "detail")

    def __init__(self, code: str, where: str, detail: str):
        self.code = code
        self.where = where
        self.detail = detail

    def as_dict(self) -> dict:
        return {"code": self.code, "where": self.where, "detail": self.detail}

    def sort_key(self):
        return (self.code, self.where, self.detail)


class LintError(Exception):
    """Usage or I/O problem that prevents a lint from running (exit 2)."""


# --------------------------------------------------------------------------
# Canonical JSON
# --------------------------------------------------------------------------

def canonical_json_bytes(obj) -> bytes:
    """The one canonical serialization for Commons JSON documents."""
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


class _DuplicateKey(ValueError):
    pass


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise _DuplicateKey(key)
        seen[key] = value
    return seen


def load_json(path: Path, where: str, findings: list):
    """Load JSON strictly. Returns (obj, raw_bytes) or (None, None) on failure."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        raise LintError(f"cannot read {path}: {exc}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        findings.append(Finding("NONCANONICAL_SERIALIZATION", where, "UTF-8 byte-order mark present"))
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates,
                         parse_constant=_reject_constant)
    except _DuplicateKey as exc:
        findings.append(Finding("DUPLICATE_JSON_KEY", where, f"duplicate key {exc.args[0]!r}"))
        return None, raw
    except (UnicodeDecodeError, ValueError) as exc:
        findings.append(Finding("INVALID_JSON", where, str(exc)))
        return None, raw
    if canonical_json_bytes(obj) != raw:
        findings.append(Finding("NONCANONICAL_SERIALIZATION", where,
                                "bytes differ from canonical form (run: canonicalize --write)"))
    return obj, raw


def _reject_constant(name):
    raise ValueError(f"non-standard JSON constant {name}")


# --------------------------------------------------------------------------
# Minimal fail-closed JSON Schema (draft 2020-12 subset) validator
# --------------------------------------------------------------------------

SUPPORTED_SCHEMA_KEYWORDS = frozenset({
    "$schema", "$id", "$defs", "$ref", "$comment", "title", "description",
    "type", "properties", "required", "additionalProperties", "enum", "const",
    "pattern", "minLength", "maxLength", "items", "minItems", "maxItems",
    "uniqueItems", "minimum",
})


class SchemaError(LintError):
    """The schema itself uses something this validator does not implement."""


def _type_ok(value, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    raise SchemaError(f"unsupported type {expected!r}")


def schema_errors(instance, schema: dict, root: dict | None = None, path: str = "$") -> list:
    """Return a list of (path, message) violations. Unknown keywords raise."""
    root = schema if root is None else root
    if not isinstance(schema, dict):
        raise SchemaError(f"schema at {path} is not an object")
    unknown = set(schema) - SUPPORTED_SCHEMA_KEYWORDS
    if unknown:
        raise SchemaError(f"unsupported schema keyword(s) {sorted(unknown)} at {path}")
    errors = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise SchemaError(f"only local #/$defs/ references are supported, got {ref!r}")
        target = root.get("$defs", {}).get(ref[len("#/$defs/"):])
        if target is None:
            raise SchemaError(f"unresolved reference {ref!r}")
        errors += schema_errors(instance, target, root, path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(instance, t) for t in types):
            return errors + [(path, f"expected type {'/'.join(types)}")]
    if "const" in schema and not _json_equal(instance, schema["const"]):
        errors.append((path, f"must equal {schema['const']!r}"))
    if "enum" in schema and not any(_json_equal(instance, e) for e in schema["enum"]):
        errors.append((path, f"{instance!r} is not one of {schema['enum']}"))
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append((path, f"shorter than {schema['minLength']}"))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append((path, f"longer than {schema['maxLength']}"))
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append((path, f"does not match pattern {schema['pattern']!r}"))
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append((path, f"less than {schema['minimum']}"))
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append((path, f"fewer than {schema['minItems']} items"))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append((path, f"more than {schema['maxItems']} items"))
        if schema.get("uniqueItems"):
            seen = []
            for item in instance:
                if any(_json_equal(item, s) for s in seen):
                    errors.append((path, "items are not unique"))
                    break
                seen.append(item)
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += schema_errors(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append((path, f"missing required property {key!r}"))
        for key, value in instance.items():
            if key in props:
                errors += schema_errors(value, props[key], root, f"{path}.{key}")
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append((path, f"unknown property {key!r}"))
                elif isinstance(extra, dict):
                    errors += schema_errors(value, extra, root, f"{path}.{key}")
    return errors


def _json_equal(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def default_schema_dir() -> Path:
    return Path(__file__).resolve().parent / "schemas"


def load_schema(kind: str, schema_dir: Path | None) -> dict:
    path = (schema_dir or default_schema_dir()) / SCHEMA_FILES[kind]
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LintError(f"cannot load schema {path}: {exc}") from exc


def check_schema(instance, kind: str, where: str, schema_dir, findings: list) -> bool:
    errors = schema_errors(instance, load_schema(kind, schema_dir))
    for path, message in errors:
        findings.append(Finding("SCHEMA_VIOLATION", where, f"{path}: {message}"))
    return not errors


# --------------------------------------------------------------------------
# Bundle digests
# --------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def bundle_digest(files: list) -> str:
    """commons.bundle-digest.v0.1: SHA-256 over sorted '<sha256>  <path>\\n' lines."""
    lines = sorted(f"{f['sha256']}  {f['path']}\n" for f in files)
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def safe_relative_path(p: str) -> str | None:
    """Return a reason the path is unsafe, or None if it is acceptable."""
    if not p or p != p.strip():
        return "empty or padded path"
    if "\\" in p or "\x00" in p:
        return "backslash or NUL in path"
    if p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        return "absolute path"
    if any(part in ("..", ".", "") for part in p.split("/")):
        return "non-normalized path"
    return None


def scan_bundle(bundle_root: Path) -> tuple[dict, list]:
    """Return ({relpath: Path} of regular files, [problem relpaths that are not regular files])."""
    found, irregular = {}, []
    for dirpath, dirnames, filenames in os.walk(bundle_root, followlinks=False):
        dirnames.sort()
        base = Path(dirpath)
        for name in sorted(dirnames):
            full = base / name
            if full.is_symlink():
                irregular.append(full.relative_to(bundle_root).as_posix())
        for name in sorted(filenames):
            full = base / name
            rel = full.relative_to(bundle_root).as_posix()
            mode = os.lstat(full).st_mode
            if stat.S_ISREG(mode):
                found[rel] = full
            else:
                irregular.append(rel)
    return found, irregular


def describe_bundle(bundle_root: Path) -> dict:
    """Produce the files list and bundle digest for a bundle directory."""
    found, irregular = scan_bundle(bundle_root)
    if irregular:
        raise LintError(f"bundle contains non-regular entries: {irregular}")
    files = []
    for rel in sorted(found):
        reason = safe_relative_path(rel)
        if reason:
            raise LintError(f"unsafe bundle path {rel!r}: {reason}")
        full = found[rel]
        files.append({"path": rel, "sha256": sha256_file(full), "bytes": full.stat().st_size})
    return {"bundle_digest_algorithm": BUNDLE_DIGEST_ALGORITHM,
            "bundle_sha256": bundle_digest(files), "files": files}


# --------------------------------------------------------------------------
# Text scans
# --------------------------------------------------------------------------

def iter_strings(obj, path="$"):
    """Yield (path, text) for every key and string value in a JSON document."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield f"{path}.<key>", key
            yield from iter_strings(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from iter_strings(value, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def scan_locators(doc, where: str, findings: list) -> None:
    for path, text in iter_strings(doc):
        for kind, pattern in LOCATOR_PATTERNS:
            if re.search(pattern, text):
                findings.append(Finding("PRIVATE_LOCATOR_LEAK", where, f"{path}: {kind} pattern present"))


def scan_claims(text: str, where: str, findings: list) -> None:
    for kind, pattern in PROHIBITED_CLAIM_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            findings.append(Finding("PROHIBITED_CLAIM", where,
                                    f"{kind} claim language {match.group(0)!r}"))


# --------------------------------------------------------------------------
# Release check
# --------------------------------------------------------------------------

def check_release(manifest_path: Path, receipt_path: Path | None, bundle_root: Path | None,
                  schema_dir: Path | None = None) -> list:
    """Lint one release. Every rule fails closed; returns a sorted findings list."""
    findings: list = []
    manifest, _ = load_json(manifest_path, "manifest", findings)
    if manifest is None:
        if not manifest_path.exists():
            findings.append(Finding("MISSING_MANIFEST", "manifest", str(manifest_path.name)))
        return _sorted(findings)
    if not isinstance(manifest, dict):
        findings.append(Finding("SCHEMA_VIOLATION", "manifest", "$: expected type object"))
        return _sorted(findings)
    check_schema(manifest, "manifest", "manifest", schema_dir, findings)
    m = manifest

    # Clearance state and release class.
    if m.get("clearance_status") != "CLEARED":
        findings.append(Finding("CLEARANCE_NOT_CLEARED", "manifest.clearance_status",
                                f"{m.get('clearance_status')!r} is not CLEARED"))
    rc = m.get("release_class")
    if rc not in RELEASABLE_CLASSES:
        findings.append(Finding("RELEASE_CLASS_NOT_RELEASABLE", "manifest.release_class",
                                f"{rc!r} may not be distributed as an implementation release"))

    # Commercial impact.
    ci = m.get("commercial_impact")
    if ci == "UNCERTAIN" or ci not in COMMERCIAL_IMPACTS:
        findings.append(Finding("COMMERCIAL_IMPACT_UNRESOLVED", "manifest.commercial_impact",
                                f"{ci!r} fails closed pending explicit commercial review"))

    # Source disclosure.
    sdl = m.get("source_disclosure_level")
    has_attr = "source_attribution" in m
    if sdl in ATTRIBUTION_ALLOWED and not has_attr:
        findings.append(Finding("DISCLOSURE_INCOMPATIBLE", "manifest.source_attribution",
                                f"{sdl} requires an approved public source_attribution"))
    if sdl not in ATTRIBUTION_ALLOWED and has_attr:
        findings.append(Finding("DISCLOSURE_INCOMPATIBLE", "manifest.source_attribution",
                                f"source_attribution is not permitted for {sdl!r}"))
    if sdl in LOCATOR_FORBIDDEN or sdl not in DISCLOSURE_LEVELS:
        scan_locators(m, "manifest", findings)

    # Claim boundary and affirmative text.
    boundary = m.get("public_claim_boundary")
    if not isinstance(boundary, dict) or not str(boundary.get("statement", "")).strip() \
            or not boundary.get("does_not_establish"):
        findings.append(Finding("CLAIM_BOUNDARY_MISSING", "manifest.public_claim_boundary",
                                "a statement and a non-empty does_not_establish list are required"))
    for field in ("display_name", "summary"):
        if isinstance(m.get(field), str):
            scan_claims(m[field], f"manifest.{field}", findings)
    if isinstance(boundary, dict) and isinstance(boundary.get("statement"), str):
        scan_claims(boundary["statement"], "manifest.public_claim_boundary.statement", findings)
    attr = m.get("source_attribution")
    if isinstance(attr, dict) and isinstance(attr.get("statement"), str):
        scan_claims(attr["statement"], "manifest.source_attribution.statement", findings)

    # License, notices, dependencies.
    lic = m.get("license")
    if not isinstance(lic, str) or not lic.strip() or lic.upper() in ("NOASSERTION", "NONE", "UNKNOWN"):
        findings.append(Finding("LICENSE_MISSING", "manifest.license", f"{lic!r}"))
    deps = m.get("dependencies")
    if not isinstance(deps, dict) or deps.get("inventory_complete") is not True:
        findings.append(Finding("DEPENDENCY_INVENTORY_INCOMPLETE", "manifest.dependencies",
                                "inventory_complete must be true"))
    if isinstance(deps, dict):
        for scope in ("runtime", "development"):
            entries = deps.get(scope)
            if not isinstance(entries, list):
                findings.append(Finding("DEPENDENCY_INVENTORY_INCOMPLETE", f"manifest.dependencies.{scope}",
                                        "list required (may be empty)"))
                continue
            for i, dep in enumerate(entries):
                dlic = dep.get("license") if isinstance(dep, dict) else None
                if not isinstance(dlic, str) or not dlic.strip() \
                        or dlic.upper() in ("NOASSERTION", "NONE", "UNKNOWN"):
                    findings.append(Finding("DEPENDENCY_LICENSE_MISSING",
                                            f"manifest.dependencies.{scope}[{i}]", f"{dlic!r}"))

    # File list.
    files = m.get("files") if isinstance(m.get("files"), list) else []
    declared = {}
    for i, f in enumerate(files):
        if not isinstance(f, dict) or not isinstance(f.get("path"), str):
            continue
        reason = safe_relative_path(f["path"])
        if reason:
            findings.append(Finding("UNSAFE_PATH", f"manifest.files[{i}]", f"{f['path']!r}: {reason}"))
            continue
        if f["path"] in declared:
            findings.append(Finding("DUPLICATE_PATH", f"manifest.files[{i}]", f["path"]))
        declared[f["path"]] = f
    paths = [f.get("path") for f in files if isinstance(f, dict)]
    if paths != sorted(paths, key=lambda p: str(p)):
        findings.append(Finding("FILES_NOT_SORTED", "manifest.files", "entries must be sorted by path"))
    notices = m.get("notices") if isinstance(m.get("notices"), list) else []
    if not notices:
        findings.append(Finding("NOTICE_MISSING", "manifest.notices", "at least one notice file required"))
    for n in notices:
        if n not in declared:
            findings.append(Finding("NOTICE_NOT_IN_BUNDLE", "manifest.notices", f"{n!r}"))
    hashable = [f for f in declared.values()
                if isinstance(f.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", f["sha256"])]
    if len(hashable) == len(declared) and declared:
        if m.get("bundle_sha256") != bundle_digest(list(declared.values())):
            findings.append(Finding("BUNDLE_DIGEST_MISMATCH", "manifest.bundle_sha256",
                                    "does not match the digest of the declared file list"))

    # Bundle bytes.
    if bundle_root is None:
        findings.append(Finding("BUNDLE_NOT_PROVIDED", "bundle", "a bundle root is required"))
    elif not bundle_root.is_dir():
        findings.append(Finding("BUNDLE_NOT_PROVIDED", "bundle", f"{bundle_root.name!r} is not a directory"))
    else:
        found, irregular = scan_bundle(bundle_root)
        for rel in irregular:
            findings.append(Finding("IRREGULAR_FILE", "bundle", f"{rel!r} is not a regular file"))
        for rel in sorted(set(found) - set(declared)):
            findings.append(Finding("UNEXPECTED_FILE", "bundle", f"{rel!r} is not declared"))
        for rel, f in sorted(declared.items()):
            full = found.get(rel)
            if full is None:
                if rel not in irregular:
                    findings.append(Finding("MISSING_FILE", "bundle", f"{rel!r} is declared but absent"))
                continue
            if sha256_file(full) != f.get("sha256") or full.stat().st_size != f.get("bytes"):
                findings.append(Finding("HASH_MISMATCH", "bundle", f"{rel!r}"))

    # Clearance receipt.
    _check_receipt(m, receipt_path, schema_dir, findings)
    return _sorted(findings)


def _check_receipt(m: dict, receipt_path: Path | None, schema_dir, findings: list) -> None:
    if receipt_path is None or not receipt_path.exists():
        findings.append(Finding("MISSING_CLEARANCE_RECEIPT", "receipt",
                                f"no public clearance receipt for {m.get('clearance_receipt_id')!r}"))
        return
    r, _ = load_json(receipt_path, "receipt", findings)
    if not isinstance(r, dict):
        findings.append(Finding("MISSING_CLEARANCE_RECEIPT", "receipt", "receipt is unreadable"))
        return
    check_schema(r, "receipt", "receipt", schema_dir, findings)

    for field in ("clearance_receipt_id", "public_release_id", "package_id", "version",
                  "release_class", "commercial_impact", "source_disclosure_level", "bundle_sha256"):
        if r.get(field) != m.get(field):
            findings.append(Finding("RECEIPT_MISMATCH", f"receipt.{field}",
                                    f"receipt {r.get(field)!r} != manifest {m.get(field)!r}"))
    if r.get("clearance_status") != "CLEARED":
        findings.append(Finding("CLEARANCE_NOT_CLEARED", "receipt.clearance_status",
                                f"{r.get('clearance_status')!r} is not CLEARED"))
    if r.get("clearance_status") != m.get("clearance_status"):
        findings.append(Finding("RECEIPT_MISMATCH", "receipt.clearance_status",
                                "receipt and manifest disagree"))

    native = m.get("source_disclosure_level") == "COMMONS_NATIVE"
    ci = m.get("commercial_impact")
    dims = r.get("dimensions") if isinstance(r.get("dimensions"), dict) else {}
    for name in CLEARANCE_DIMENSIONS:
        status = (dims.get(name) or {}).get("status") if isinstance(dims.get(name), dict) else None
        if status == "PASS":
            continue
        if status == "NOT_APPLICABLE" and name == "commercial_impact" and native and ci == "NONE":
            continue
        findings.append(Finding("CLEARANCE_DIMENSION_NOT_PASSED", f"receipt.dimensions.{name}",
                                f"status {status!r}"))

    private = r.get("private_clearance_receipt") if isinstance(r.get("private_clearance_receipt"), dict) else {}
    if native and private.get("status") != "NOT_APPLICABLE_COMMONS_NATIVE":
        findings.append(Finding("DISCLOSURE_INCOMPATIBLE", "receipt.private_clearance_receipt",
                                "Commons-native releases have no private clearance receipt"))
    if not native and (private.get("status") != "HELD_PRIVATELY" or not private.get("opaque_reference")):
        findings.append(Finding("DISCLOSURE_INCOMPATIBLE", "receipt.private_clearance_receipt",
                                "non-native releases require an opaque reference to a privately held receipt"))

    if ci in MOAT_REVIEW_REQUIRED:
        moat = r.get("minimum_viable_moat")
        if not isinstance(moat, dict) or not str(moat.get("analysis", "")).strip():
            findings.append(Finding("MOAT_REVIEW_MISSING", "receipt.minimum_viable_moat",
                                    f"{ci} requires a minimum-viable-moat review"))
        elif not moat.get("retained_surfaces") and not moat.get("strategic_review"):
            findings.append(Finding("MOAT_REVIEW_MISSING", "receipt.minimum_viable_moat.strategic_review",
                                    "no retained paid surface: an explicit strategic review must be recorded"))
    if ci in HUMAN_AUTHORIZATION_REQUIRED:
        auth = r.get("human_authorization")
        if not isinstance(auth, dict) or auth.get("authorized") is not True:
            findings.append(Finding("HUMAN_AUTHORIZATION_MISSING", "receipt.human_authorization",
                                    f"{ci} requires recorded explicit human authorization"))

    lic = m.get("license")
    if isinstance(lic, str) and "Apache-2.0" in lic and r.get("apache_patent_grant_acknowledged") is not True:
        findings.append(Finding("PATENT_GRANT_NOT_ACKNOWLEDGED", "receipt.apache_patent_grant_acknowledged",
                                "Apache-2.0 releases must acknowledge the patent grant during clearance"))

    if m.get("source_disclosure_level") in LOCATOR_FORBIDDEN:
        scan_locators(r, "receipt", findings)


def _sorted(findings: list) -> list:
    unique = {}
    for f in findings:
        unique[f.sort_key()] = f
    return [unique[k] for k in sorted(unique)]


# --------------------------------------------------------------------------
# Package index check
# --------------------------------------------------------------------------

INDEX_MIRRORED_FIELDS = ("package_id", "display_name", "version", "release_class",
                         "commercial_impact", "source_disclosure_level", "license",
                         "support_class", "clearance_status")


def check_index(index_path: Path, repo_root: Path, schema_dir: Path | None = None) -> list:
    findings: list = []
    index, _ = load_json(index_path, "index", findings)
    if index is None:
        if not index_path.exists():
            findings.append(Finding("MISSING_INDEX", "index", index_path.name))
        return _sorted(findings)
    check_schema(index, "index", "index", schema_dir, findings)
    entries = index.get("packages") if isinstance(index, dict) else None
    if not isinstance(entries, list):
        return _sorted(findings)
    keys = [(e.get("package_id"), e.get("version")) for e in entries if isinstance(e, dict)]
    if keys != sorted(keys, key=lambda k: (str(k[0]), str(k[1]))):
        findings.append(Finding("INDEX_NOT_SORTED", "index.packages", "sort by package_id, version"))
    if len(set(keys)) != len(keys):
        findings.append(Finding("INDEX_DUPLICATE_ENTRY", "index.packages", "duplicate package_id/version"))
    root = repo_root.resolve()
    for i, e in enumerate(entries):
        where = f"index.packages[{i}]"
        if not isinstance(e, dict):
            continue
        if e.get("clearance_status") != "CLEARED":
            findings.append(Finding("CLEARANCE_NOT_CLEARED", where, "only CLEARED releases may be indexed"))
        if e.get("release_class") not in RELEASABLE_CLASSES:
            findings.append(Finding("RELEASE_CLASS_NOT_RELEASABLE", where,
                                    f"{e.get('release_class')!r} may not be indexed"))
        paths = {}
        for field in ("manifest_path", "clearance_receipt_path", "bundle_root"):
            value = e.get(field)
            reason = safe_relative_path(value) if isinstance(value, str) else "missing"
            if reason:
                findings.append(Finding("UNSAFE_PATH", f"{where}.{field}", f"{value!r}: {reason}"))
                continue
            resolved = (root / value).resolve()
            if root not in resolved.parents and resolved != root:
                findings.append(Finding("UNSAFE_PATH", f"{where}.{field}", f"{value!r} escapes repository"))
                continue
            paths[field] = resolved
        if len(paths) != 3:
            continue
        for f in check_release(paths["manifest_path"], paths["clearance_receipt_path"],
                               paths["bundle_root"], schema_dir):
            findings.append(Finding(f.code, f"{where} -> {f.where}", f.detail))
        manifest = _quiet_load(paths["manifest_path"])
        if isinstance(manifest, dict):
            for field in INDEX_MIRRORED_FIELDS:
                if e.get(field) != manifest.get(field):
                    findings.append(Finding("INDEX_MISMATCH", f"{where}.{field}",
                                            f"index {e.get(field)!r} != manifest {manifest.get(field)!r}"))
    return _sorted(findings)


def _quiet_load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------
# Fixture replay
# --------------------------------------------------------------------------

def replay_fixtures(fixtures_root: Path, schema_dir: Path | None = None) -> dict:
    """Run every release fixture and return a deterministic result document.

    Each fixture directory holds manifest.json, an optional clearance-receipt.json
    and a bundle/ directory. Index fixtures hold package-index.json and are
    checked with the fixture directory as repository root.
    """
    results = {}
    for group in ("valid", "invalid"):
        base = fixtures_root / group
        if not base.is_dir():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            if (d / "package-index.json").exists():
                findings = check_index(d / "package-index.json", d, schema_dir)
            else:
                findings = check_release(d / "manifest.json", d / "clearance-receipt.json",
                                         d / "bundle", schema_dir)
            results[f"{group}/{d.name}"] = sorted({f.code for f in findings})
    return {"fixture_results": results, "format": "commons.fixture-replay.v0.1",
            "tool": TOOL_NAME, "tool_version": TOOL_VERSION}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _report(findings: list, as_json: bool, out) -> int:
    if as_json:
        out.write(canonical_json_bytes({"findings": [f.as_dict() for f in findings],
                                        "ok": not findings}).decode("utf-8"))
    else:
        for f in findings:
            out.write(f"{f.code}\t{f.where}\t{f.detail}\n")
        out.write(("OK: no findings\n" if not findings else f"FAIL: {len(findings)} finding(s)\n"))
    return 0 if not findings else 1


def main(argv=None, out=None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog=TOOL_NAME, description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    parser.add_argument("--schema-dir", type=Path, default=None,
                        help="directory holding the v0.1 schemas (default: bundled copies)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check-release", help="lint one release manifest, receipt and bundle")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--receipt", type=Path, default=None)
    p.add_argument("--bundle-root", type=Path, default=None)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("check-index", help="lint the public package index and every release it lists")
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("describe-bundle", help="print the files list and bundle digest for a directory")
    p.add_argument("bundle_root", type=Path)

    p = sub.add_parser("replay-fixtures", help="replay fixtures and print a deterministic result")
    p.add_argument("fixtures_root", type=Path)
    p.add_argument("--expected", type=Path, default=None,
                   help="compare against this expected-results file (exit 1 on difference)")

    p = sub.add_parser("canonicalize", help="check or rewrite JSON files in canonical form")
    p.add_argument("files", type=Path, nargs="+")
    p.add_argument("--write", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "check-release":
            return _report(check_release(args.manifest, args.receipt, args.bundle_root, args.schema_dir),
                           args.json, out)
        if args.command == "check-index":
            return _report(check_index(args.index, args.repo_root, args.schema_dir), args.json, out)
        if args.command == "describe-bundle":
            out.write(canonical_json_bytes(describe_bundle(args.bundle_root)).decode("utf-8"))
            return 0
        if args.command == "replay-fixtures":
            result = canonical_json_bytes(replay_fixtures(args.fixtures_root, args.schema_dir))
            out.write(result.decode("utf-8"))
            if args.expected is not None:
                if args.expected.read_bytes() != result:
                    sys.stderr.write("fixture replay differs from expected results\n")
                    return 1
            return 0
        if args.command == "canonicalize":
            status = 0
            for path in args.files:
                raw = path.read_bytes()
                canon = canonical_json_bytes(json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates))
                if raw != canon:
                    if args.write:
                        path.write_bytes(canon)
                        out.write(f"rewrote {path}\n")
                    else:
                        out.write(f"NONCANONICAL\t{path}\n")
                        status = 1
            return status
    except (LintError, OSError, ValueError) as exc:
        sys.stderr.write(f"{TOOL_NAME}: error: {exc}\n")
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
