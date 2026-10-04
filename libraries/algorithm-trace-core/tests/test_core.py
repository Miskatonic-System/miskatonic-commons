# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Public behaviour of AlgorithmTrace v0.4 Public Core, using only the synthetic example profile."""

import ast
import hashlib
import json
import math
from pathlib import Path

import pytest

from algorithm_trace_core import framing, profiles
from cases import hostile_cases, record_workload, sealed

LIB = Path(__file__).resolve().parents[1]
PKG = LIB / "src" / "algorithm_trace_core"


# Synthetic demonstrator ------------------------------------------------------------

def test_demonstrator_records_and_replays(impl):
    trace, digest, run, events = sealed(impl)
    out = impl.replay(trace, impl.profile_dir, expected_digest=digest, run_record=run)
    assert out.result == {"final": [2, -1, 7, 3], "best": 7}
    assert out.trace_digest == digest == hashlib.sha256(trace).hexdigest()
    assert impl.derive_metrics(out.events) == {"reads": 10, "writes": 4, "comparisons": 7, "swaps": 1,
                                               "event_count": 28, "frame_entries": 2, "max_frame_depth": 1}


def test_trace_is_canonical_jsonl(impl):
    trace, _, _, events = sealed(impl)
    assert trace.endswith(b"\n")
    for line, event in zip(trace[:-1].split(b"\n"), events):
        assert line == impl.canonical_bytes(event)


def test_run_id_binds_profile_identity(impl):
    _, _, run, events = sealed(impl)
    begin = events[0]
    assert begin["run_id"] == impl.derive_run_id(begin["algorithm_id"], begin["implementation_id"], begin["payload"])
    other = dict(begin["payload"], profile_schema_digest="0" * 64)
    assert impl.derive_run_id(begin["algorithm_id"], begin["implementation_id"], other) != begin["run_id"]


def test_profile_digest_is_rfc8785_sha256(impl):
    doc = json.loads((impl.profile_dir / "integer_sequence_example.profile.v0.4.json").read_text())
    shuffled = dict(reversed(list(doc.items())))
    assert impl.profile_digest(doc) == impl.profile_digest(shuffled) == hashlib.sha256(impl.canonical_bytes(doc)).hexdigest()


def test_exact_profile_resolution(impl):
    doc, digest = profiles.profile_for("INTEGER_SEQUENCE_EXAMPLE")
    resolved = profiles.resolve("INTEGER_SEQUENCE_EXAMPLE", digest)
    assert resolved.digest == digest and resolved.doc == doc
    module_file = PKG / "examples" / "integer_sequence.py"
    assert doc["semantics_module_sha256"] == hashlib.sha256(module_file.read_bytes()).hexdigest()


def test_example_profile_document_is_reproducible():
    import subprocess, sys
    proc = subprocess.run([sys.executable, str(LIB / "scripts" / "build_example_profile.py"), "--check"])
    assert proc.returncode == 0


def test_recorder_rejects_illegal_api_use(impl):
    rec = impl.recorder_cls("running_maximum_v1.0", "x", "INTEGER_SEQUENCE_EXAMPLE", "0" * 64,
                            {"values": [1], "floor": 0}, {"status": "SATISFIED"},
                            [{"name": "seq", "kind": "ARRAY", "element_types": ["INTEGER"], "length": 1,
                              "initial": "FROM_PROBLEM", "mutable": True}],
                            {"seq": [{"type": "INTEGER", "value": 1}]})
    loc = {"kind": "ARRAY_CELL", "storage": "seq", "index": 0}
    with pytest.raises(IndexError):
        rec.read({"kind": "ARRAY_CELL", "storage": "seq", "index": 5})
    with pytest.raises(TypeError):
        rec.write(loc, {"type": "EMPTY"})
    with pytest.raises(ValueError):
        rec.swap(loc, loc)
    frame = rec.frame_enter("outer", None)
    with pytest.raises(RuntimeError):
        rec.frame_exit(frame + 1)   # a mismatched exit is refused (the frame is popped, as in the source)
    rec.frame_enter("still_open", None)
    with pytest.raises(RuntimeError):
        rec.finish({})              # RUN_END with an open frame is refused


# Hostile controls (WO §17) -----------------------------------------------------------

def _cases(impl, tmp_path):
    return {name: (code, thunk) for name, code, thunk in hostile_cases(impl, tmp_path)}


@pytest.mark.parametrize("name", [
    "noncanonical_jsonl", "missing_terminal_lf", "duplicate_json_keys", "nan_input", "sequence_gap",
    "duplicate_sequence", "out_of_order_sequence", "undeclared_storage", "wrong_location_kind",
    "out_of_range_access", "read_value_mismatch", "invalid_write_type", "unknown_profile",
    "profile_digest_mismatch", "profile_document_schema_violation", "semantics_module_digest_mismatch",
    "run_id_derivation_mismatch", "malformed_frame_nesting", "compare_unread_operand", "compare_wrong_result",
    "compare_operand_kind_not_permitted", "result_schema_violation", "trace_digest_mismatch",
])
def test_hostile_trace_rejected_with_stable_code(impl, tmp_path, name):
    code, thunk = _cases(impl, tmp_path)[name]
    with pytest.raises(impl.error_cls) as exc:
        thunk()
    assert exc.value.code == code


def test_strict_loads_rejects_duplicates_and_non_finite(impl):
    with pytest.raises(ValueError):
        impl.strict_loads('{"a": 1, "a": 2}')
    for token in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError):
            impl.strict_loads(f'{{"a": {token}}}')
    with pytest.raises(Exception):
        impl.canonical_bytes({"a": math.nan})


# Standalone / no network / no telemetry --------------------------------------------------

ALLOWED_IMPORTS = {"__future__", "collections", "dataclasses", "functools", "hashlib", "importlib", "json",
                   "pathlib", "types", "typing", "rfc8785", "jsonschema", "fastjsonschema"}


def test_package_imports_only_stdlib_and_declared_dependencies():
    for path in PKG.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = set() if node.level else {(node.module or "").split(".")[0]}
            else:
                continue
            assert names <= ALLOWED_IMPORTS, (path.name, names)


COMMONS_SCHEMA_BASE = ("https://github.com/Miskatonic-System/miskatonic-commons/tree/main/"
                      "libraries/algorithm-trace-core/src/algorithm_trace_core/schemas/")
PUBLIC_STANDARD_URLS = {"https://json-schema.org/draft/2020-12/schema"}


def test_package_urls_are_commons_or_public_standards_only():
    import re
    for path in list(PKG.rglob("*")) + [LIB / "README.md"]:
        if path.is_file():
            for url in re.findall(r"https?://[^\s\"'`)#]+", path.read_text(errors="replace")):
                assert url.startswith(COMMONS_SCHEMA_BASE) or url in PUBLIC_STANDARD_URLS, (path.name, url)


def test_protocol_identifiers_use_public_namespace_only():
    import re
    for path in PKG.rglob("*"):
        if path.is_file():
            text = path.read_text(errors="replace")
            for ident in re.findall(r"\b[a-z][a-z0-9-]*\.(?:algorithm-trace|algorithm-run|instrumented-storage|trace-profile|algorithm-trace-core)\.v0\.4\b", text):
                assert ident.startswith("algorithm-trace-core."), (path.name, ident)
