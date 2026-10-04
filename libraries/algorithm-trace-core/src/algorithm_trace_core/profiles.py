# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Profile catalog: discovers content-addressed profile documents; resolves (profile_id, digest) to semantics.

The catalog is a lookup, not an authority. A run's authority is the exact
(profile_id, profile_schema_digest) it binds; resolution succeeds only if a discovered
document has that id *and* that digest, and only if the semantics module it names has
exactly the SHA-256 the document pins. Adding a profile means adding files: this module
is not edited.

Public adaptation: the catalog is a list of directories (default: this package's ``profiles``
directory), and a semantics module is located through Python's import system and checked
against its pinned SHA-256 before it is imported.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

import fastjsonschema
import jsonschema

from .canonical import canonical_digest, strict_loads
from .framing import ReplayError, load_schema

PROFILE_DIR = Path(__file__).resolve().parent / "profiles"
ProfileDirs = Iterable[str | Path] | None


@dataclass(frozen=True)
class Profile:
    doc: dict[str, Any]
    digest: str
    semantics: ModuleType
    problem: Any
    precondition: Any
    result: Any
    contract_policy: Any


def profile_digest(doc: dict[str, Any]) -> str:
    return canonical_digest(doc)


@lru_cache(maxsize=None)
def _document_validator() -> Any:
    schema = load_schema("trace-profile.v0.4.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    return fastjsonschema.compile(schema)


def catalog(profile_dirs: ProfileDirs = None) -> dict[tuple[str, str], Path]:
    """(profile_id, digest) -> document path, for every discovered profile document (read fresh)."""
    out = {}
    for directory in (PROFILE_DIR,) if profile_dirs is None else tuple(Path(d) for d in profile_dirs):
        for path in sorted(Path(directory).glob("*.profile.v0.4.json")):
            doc = strict_loads(path.read_bytes())
            out[(doc["profile_id"], profile_digest(doc))] = path
    return out


def _module_file(module_name: str) -> Path | None:
    """The source file Python would import for ``module_name``, located without executing it."""
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ValueError):
        return None
    if spec is None or spec.origin is None or not spec.origin.endswith(".py"):
        return None
    return Path(spec.origin)


def resolve(profile_id: str, digest: str, profile_dirs: ProfileDirs = None) -> Profile:
    """Resolve an exact profile or raise ReplayError. Documents and module bytes are observed on every call."""
    found = catalog(profile_dirs)
    path = found.get((profile_id, digest))
    if path is None:
        known = sorted(d for (pid, d) in found if pid == profile_id)
        code = "PROFILE_DIGEST_MISMATCH" if known else "PROFILE_UNKNOWN"
        raise ReplayError(code, f"{profile_id} @ {digest} is not a catalogued profile document")
    doc = strict_loads(path.read_bytes())
    try:
        _document_validator()(doc)
    except fastjsonschema.JsonSchemaException as exc:
        raise ReplayError("PROFILE_DOCUMENT_INVALID", exc.message) from None
    module_file = _module_file(doc["semantics_module"])
    if module_file is None or not module_file.is_file() or \
            hashlib.sha256(module_file.read_bytes()).hexdigest() != doc["semantics_module_sha256"]:
        raise ReplayError("PROFILE_SEMANTICS_MISMATCH", f"{doc['semantics_module']} does not have the pinned SHA-256")
    for part in ("problem_schema", "precondition_schema", "result_schema", "contract_policy_schema"):
        jsonschema.Draft202012Validator.check_schema(doc[part])
    return Profile(doc, digest, importlib.import_module(doc["semantics_module"]),
                   _compile(canonical_digest(doc["problem_schema"]), doc["problem_schema"]),
                   _compile(canonical_digest(doc["precondition_schema"]), doc["precondition_schema"]),
                   _compile(canonical_digest(doc["result_schema"]), doc["result_schema"]),
                   _compile(canonical_digest(doc["contract_policy_schema"]), doc["contract_policy_schema"]))


_COMPILED: dict[str, Any] = {}


def _compile(key: str, schema: dict[str, Any]) -> Any:
    """Compiled validators are cached by the schema's own content digest (immutable facts only)."""
    if key not in _COMPILED:
        _COMPILED[key] = fastjsonschema.compile(schema)
    return _COMPILED[key]


def validate_part(validator: Any, value: Any, code: str) -> None:
    try:
        validator(value)
    except fastjsonschema.JsonSchemaException as exc:
        raise ReplayError(code, exc.message) from None


def profile_for(profile_id: str, profile_dirs: ProfileDirs = None) -> tuple[dict[str, Any], str]:
    """The single catalogued document for a profile id (used by recorders); ambiguity is an error."""
    found = catalog(profile_dirs)
    matches = [(pid, d) for (pid, d) in found if pid == profile_id]
    if len(matches) != 1:
        raise LookupError(f"{profile_id}: {len(matches)} catalogued documents")
    path = found[matches[0]]
    return strict_loads(path.read_bytes()), matches[0][1]
