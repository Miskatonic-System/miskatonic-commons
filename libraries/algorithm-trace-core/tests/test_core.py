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
from core_cases import core_hostile_cases, core_positive_cases, probe_doc, probe_trace

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


# Core-isolating controls (0.1.1) ---------------------------------------------------------

CORE_NAMES = [
    "framing_non_bytes_input", "framing_final_lf_replaced", "framing_interior_empty_line",
    "framing_integer_outside_rfc8785_domain", "framing_malformed_json_line", "event_schema_extra_field",
    "run_begin_missing", "run_begin_duplicate", "algorithm_id_differs", "implementation_id_differs",
    "run_id_differs_in_one_event", "config_not_empty", "problem_schema_violation",
    "precondition_schema_violation", "storage_set_not_admissible", "event_after_run_end", "run_end_missing",
    "run_end_with_open_frame", "op_not_permitted", "op_not_permitted_non_mutating",
    "core_operand_kind_not_permitted", "execution_after_precondition_violation", "swap_endpoints_equal",
    "swap_wrong_constituent", "swap_writes_not_exchanged", "compare_operand_not_at_location",
    "compare_parameter_misreported", "frame_id_not_sequential", "frame_scope_outside_storage",
    "frame_scope_exceeds_parent", "run_record_schema_invalid", "run_record_digest_differs",
    "run_record_field_differs", "probe_compare_empty_operand", "probe_compare_type_mismatch",
    "probe_write_immutable", "probe_swap_immutable", "probe_duplicate_storage_name",
    "probe_initial_length_differs", "probe_initial_values_outside_types",
]


def test_core_case_list_is_complete(impl, tmp_path):
    assert [name for name, _, _ in core_hostile_cases(impl, tmp_path)] == CORE_NAMES


@pytest.mark.parametrize("name", CORE_NAMES)
def test_core_hostile_trace_rejected_with_stable_code(impl, tmp_path, name):
    code, thunk = {n: (c, f) for n, c, f in core_hostile_cases(impl, tmp_path)}[name]
    with pytest.raises(impl.error_cls) as exc:
        thunk()
    assert exc.value.code == code


@pytest.mark.parametrize("name", CORE_NAMES)
def test_core_positive_twin_accepted(impl, tmp_path, name):
    """The same construction without its one defect replays cleanly, so each control has power."""
    thunk = {n: f for n, _, f in core_positive_cases(impl, tmp_path)}[name]
    thunk()


def test_frame_scope_is_declarative_not_an_access_restriction(impl):
    """Documented boundary: a frame scope is checked against storage and its parent scope only."""
    import copy
    from cases import _first, reserialize
    _, _, _, events = sealed(impl)
    ev = copy.deepcopy(events)
    ev[_first(ev, "FRAME_ENTER")]["payload"]["scope"].update(lo=2, hi=2)
    impl.replay(reserialize(impl, ev), impl.profile_dir)


# Profile module discovery (0.1.1) ---------------------------------------------------------

def _discovery_case(impl, tmp_path, package, init_body, module_body):
    import sys
    pkg = tmp_path / "mods" / package
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(init_body)
    (pkg / "semantics.py").write_text(module_body)
    doc = probe_doc(semantics_module=f"{package}.semantics",
                    semantics_module_sha256=hashlib.sha256((pkg / "semantics.py").read_bytes()).hexdigest())
    d = tmp_path / "profiles"
    d.mkdir()
    (d / "p.profile.v0.4.json").write_text(json.dumps(doc))
    trace = probe_trace(impl, impl.profile_digest(doc), [])
    sys.path.insert(0, str(tmp_path / "mods"))  # restored by the clean_modules fixture
    return lambda: impl.replay(trace, d)


@pytest.fixture
def clean_modules():
    import sys
    before = (list(sys.path), set(sys.modules))
    yield
    sys.path[:] = before[0]
    for name in set(sys.modules) - before[1]:
        del sys.modules[name]


def test_parent_package_raising_is_a_stable_resolution_failure(impl, tmp_path, clean_modules):
    run = _discovery_case(impl, tmp_path, "raising_parent", "raise RuntimeError('parent failed')\n", "")
    with pytest.raises(impl.error_cls) as exc:
        run()
    assert exc.value.code == "PROFILE_MODULE_RESOLUTION_FAILED"


def test_parent_package_import_error_stays_a_semantics_mismatch(impl, tmp_path, clean_modules):
    run = _discovery_case(impl, tmp_path, "importerror_parent", "raise ImportError('absent')\n", "")
    with pytest.raises(impl.error_cls) as exc:
        run()
    assert exc.value.code == "PROFILE_SEMANTICS_MISMATCH"


def test_pinned_module_execution_failure_is_not_masked(impl, tmp_path, clean_modules):
    """Once the pinned module itself runs, its exceptions are not rewritten into the error envelope."""
    run = _discovery_case(impl, tmp_path, "raising_module", "", "raise RuntimeError('semantics failed')\n")
    with pytest.raises(RuntimeError, match="semantics failed"):
        run()


def test_healthy_external_semantics_package_resolves(impl, tmp_path, clean_modules):
    import inspect
    from core_probe import semantics
    run = _discovery_case(impl, tmp_path, "healthy_probe", "", inspect.getsource(semantics))
    run()


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
