# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Hostile controls that isolate the generic replay core (added in 0.1.1).

The 0.1.0 controls in ``cases.py`` reach the core through the example profile, whose own hooks
can reject first and so mask a core check. Each control here changes one thing and names the
single ReplayError code it must produce. Controls marked CORE_PROBE replay under a test-only
profile whose semantics hooks all accept (``core_probe/semantics.py``), so only the core can
reject them. Each control has a positive twin: the same construction without the defect must be
accepted (see ``core_positive_cases``).
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from cases import _first, example_doc, integer, reserialize, sealed

HERE = Path(__file__).resolve().parent
PROBE_MODULE = "core_probe.semantics"
PROBE_ID = "CORE_PROBE"


def _renumber(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, e in enumerate(events):
        e["seq"] = i
    return events


def _write_dir(impl: Any, tmp: Path, name: str, doc: dict[str, Any]) -> tuple[Path, str]:
    d = tmp / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "profile.profile.v0.4.json").write_text(json.dumps(doc))
    return d, impl.profile_digest(doc)


def _example_variant(impl: Any, tmp: Path, name: str, edit: Callable[[dict], None]) -> tuple[Path, str]:
    doc = example_doc(impl)
    edit(doc)
    return _write_dir(impl, tmp, name, doc)


# CORE_PROBE storage: a mixed-type mutable array, an immutable INTEGER array and a scalar.
PROBE_STORAGE = [
    {"name": "a", "kind": "ARRAY", "element_types": ["EMPTY", "INTEGER", "TAGGED_ITEM"], "length": 2,
     "initial": "FROM_PROBLEM", "mutable": True},
    {"name": "k", "kind": "ARRAY", "element_types": ["INTEGER"], "length": 1, "initial": "FROM_PROBLEM", "mutable": False},
    {"name": "s", "kind": "SCALAR", "element_types": ["INTEGER"], "initial": "ZERO", "mutable": True},
]
PROBE_PROBLEM = {"a": [{"type": "TAGGED_ITEM", "key": 5, "tag": "x"}, {"type": "EMPTY"}], "k": [integer(4)]}


def probe_doc(**overrides: Any) -> dict[str, Any]:
    module = HERE / "core_probe" / "semantics.py"
    doc = {
        "profile_document_version": "algorithm-trace-core.trace-profile.v0.4", "profile_id": PROBE_ID,
        "profile_version": "0.1.0", "semantics_module": PROBE_MODULE,
        "semantics_module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "comparison": "TOTAL_KEY_TAG", "operand_kinds": ["VALUE", "PARAMETER", "INTEGER", "ARGUMENT"],
        "permitted_ops": ["RUN_BEGIN", "RUN_END", "READ", "WRITE", "COMPARE", "SWAP", "FRAME_ENTER", "FRAME_EXIT"],
        "problem_schema": {"type": "object"}, "precondition_schema": {"type": "object"},
        "result_schema": {"type": "object"}, "contract_policy_schema": {"type": "object"},
        "storage_sets": [[{k: d[k] for k in ("name", "kind", "element_types", "initial", "mutable")} for d in PROBE_STORAGE]],
    }
    doc.update(overrides)
    return doc


def probe_trace(impl: Any, digest: str, body: list[tuple[str, dict]], *, storage=None, problem=None,
                begin_edit: Callable[[dict], None] | None = None) -> bytes:
    """A hand-built CORE_PROBE trace: RUN_BEGIN, the body, RUN_END with an empty result."""
    begin = {"profile_id": PROBE_ID, "profile_schema_digest": digest,
             "problem": copy.deepcopy(PROBE_PROBLEM if problem is None else problem),
             "precondition": {}, "storage": copy.deepcopy(PROBE_STORAGE if storage is None else storage),
             "config": {}, "seed": None, "instrumentation_version": "algorithm-trace-core.instrumented-storage.v0.4"}
    if begin_edit:
        begin_edit(begin)
    env = {"schema_version": impl.trace_schema_version, "run_id": "", "algorithm_id": "core_probe_v1.0",
           "implementation_id": "core-probe"}
    events = [dict(env, op="RUN_BEGIN", payload=begin)] + [dict(env, op=op, payload=p) for op, p in body] \
        + [dict(env, op="RUN_END", payload={"result": {}})]
    return reserialize(impl, _renumber(events), rederive=True)


def A(i: int) -> dict[str, Any]:
    return {"kind": "ARRAY_CELL", "storage": "a", "index": i}


K0 = {"kind": "ARRAY_CELL", "storage": "k", "index": 0}
TAG5 = {"type": "TAGGED_ITEM", "key": 5, "tag": "x"}


def _cases(impl: Any, tmp: Path, defective: bool) -> list[tuple[str, str, Callable[[], Any]]]:
    """(name, code, thunk). With defective=False each thunk builds the positive twin (must be accepted)."""
    trace, digest, run, events = sealed(impl)
    rp, pd = impl.replay, impl.profile_dir
    probe_dir, probe_digest = _write_dir(impl, tmp, "core_probe", probe_doc())

    def mutate(fn, rederive=False):
        ev = copy.deepcopy(events)
        if defective:
            fn(ev)
        return reserialize(impl, ev, rederive=rederive)

    def probe(body_bad, body_good, **kw):
        return lambda: rp(probe_trace(impl, probe_digest, body_bad if defective else body_good, **kw), probe_dir)

    def probe_variant(name, doc_bad, doc_good, body, **kw):
        def run():
            d, dg = _write_dir(impl, tmp, name, doc_bad if defective else doc_good)
            return rp(probe_trace(impl, dg, body, **kw), d)
        return run

    def example_under(name, edit, ev_edit=None):
        def run():
            d, dg = _example_variant(impl, tmp, name, edit if defective else (lambda doc: None))
            ev = copy.deepcopy(events)
            ev[0]["payload"]["profile_schema_digest"] = dg
            if ev_edit and defective:
                ev_edit(ev)
            return rp(reserialize(impl, ev, rederive=True), d)
        return run

    swap = _first(events, "SWAP")
    final_unswapped = list(events[0]["payload"]["problem"]["values"])

    def swap_same_cell(ev):
        a = ev[swap]["payload"]["a"]
        va = ev[swap + 1]["payload"]["value"]
        ev[swap]["payload"]["b"] = copy.deepcopy(a)
        ev[swap + 2]["payload"].update(location=copy.deepcopy(a), value=copy.deepcopy(va))
        ev[swap + 3]["payload"].update(location=copy.deepcopy(a), value=copy.deepcopy(va))
        ev[swap + 4]["payload"].update(location=copy.deepcopy(a), value=copy.deepcopy(va))
        ev[-1]["payload"]["result"]["final"] = list(final_unswapped)

    def swap_reads_reordered(ev):
        # Read b before a; the writes then restore each cell, so every value is consistent.
        a, b = ev[swap]["payload"]["a"], ev[swap]["payload"]["b"]
        va, vb = ev[swap + 1]["payload"]["value"], ev[swap + 2]["payload"]["value"]
        ev[swap + 1]["payload"].update(location=copy.deepcopy(b), value=copy.deepcopy(vb))
        ev[swap + 2]["payload"].update(location=copy.deepcopy(a), value=copy.deepcopy(va))
        ev[swap + 3]["payload"]["value"] = copy.deepcopy(va)
        ev[swap + 4]["payload"]["value"] = copy.deepcopy(vb)
        ev[-1]["payload"]["result"]["final"] = list(final_unswapped)

    def swap_not_exchanged(ev):
        va = ev[swap + 1]["payload"]["value"]
        ev[swap + 3]["payload"]["value"] = copy.deepcopy(va)  # writes a := va (should be vb)
        final = list(ev[-1]["payload"]["result"]["final"])
        final[0] = va["value"]
        ev[-1]["payload"]["result"]["final"] = final

    exits = [i for i, e in enumerate(events) if e["op"] == "FRAME_EXIT"]
    enters = [i for i, e in enumerate(events) if e["op"] == "FRAME_ENTER"]
    n = len(final_unswapped)

    def nest_wider_child(ev):
        # Move the first frame's exit to just before RUN_END, so the second frame nests inside it,
        # and narrow the parent scope so the child's scope exceeds it.
        moved = ev.pop(exits[0])
        ev.insert(len(ev) - 1, moved)
        ev[enters[0]]["payload"]["scope"]["hi"] = n - 1
        _renumber(ev)

    def drop_last_exit(ev):
        del ev[exits[-1]]
        _renumber(ev)

    def event_after_end(ev):
        # A READ of the scalar with its true final value: consistent in every respect except its position.
        extra = copy.deepcopy(ev[_first(ev, "READ")])
        extra["payload"] = {"location": {"kind": "SCALAR", "storage": "best"},
                            "value": integer(ev[-1]["payload"]["result"]["best"])}
        ev.append(extra)
        _renumber(ev)

    def second_begin(ev):
        ev.insert(1, copy.deepcopy(ev[0]))
        _renumber(ev)

    def drop_begin(ev):
        del ev[0]
        _renumber(ev)

    def drop_end(ev):
        del ev[-1]

    cmp_param = next(i for i, e in enumerate(events) if e["op"] == "COMPARE" and e["payload"]["rhs"]["kind"] == "PARAMETER")
    cmp_value = _first(events, "COMPARE")

    def param_lie(ev):
        p = ev[cmp_param]["payload"]
        p["rhs"]["value"] = 1000
        lhs = p["lhs"]["value"]["value"]
        p["result"] = (lhs > 1000) - (lhs < 1000)

    def at_elsewhere(ev):
        p = ev[cmp_value]["payload"]
        cur = p["lhs"]["at"]["index"]
        values = events[0]["payload"]["problem"]["values"]
        other = next(j for j in range(n) if values[j] != values[cur])
        p["lhs"]["at"]["index"] = other

    def run_record(edit):
        r = copy.deepcopy(run)
        if defective:
            edit(r)
        return lambda: rp(trace, pd, expected_digest=digest, run_record=r)

    big = b'"seq":' + str(2 ** 60).encode()
    cases = [
        # Framing
        ("framing_non_bytes_input", "TRACE_EMPTY", lambda: rp(trace.decode() if defective else trace, pd)),
        ("framing_final_lf_replaced", "FRAMING_INVALID", lambda: rp(trace[:-1] + b"X" if defective else trace, pd)),
        ("framing_interior_empty_line", "FRAMING_INVALID",
         lambda: rp(trace.replace(b"\n", b"\n\n", 1) if defective else trace, pd)),
        ("framing_integer_outside_rfc8785_domain", "NONCANONICAL_LINE",
         lambda: rp(trace.replace(b'"seq":0', big, 1) if defective else trace, pd)),
        ("framing_malformed_json_line", "FRAMING_INVALID",
         lambda: rp(b"[" + trace[1:] if defective else trace, pd)),
        # Event schema and run identity
        ("event_schema_extra_field", "SCHEMA_INVALID",
         lambda: rp(mutate(lambda ev: ev[1].__setitem__("note", "x")), pd)),
        ("run_begin_missing", "RUN_BEGIN_MISSING", lambda: rp(mutate(drop_begin), pd)),
        ("run_begin_duplicate", "RUN_BEGIN_DUPLICATE", lambda: rp(mutate(second_begin), pd)),
        ("algorithm_id_differs", "ALGORITHM_ID_MISMATCH",
         lambda: rp(mutate(lambda ev: ev[2].__setitem__("algorithm_id", "other_v1.0")), pd)),
        ("implementation_id_differs", "IMPLEMENTATION_ID_MISMATCH",
         lambda: rp(mutate(lambda ev: ev[2].__setitem__("implementation_id", "other")), pd)),
        ("run_id_differs_in_one_event", "RUN_ID_MISMATCH",
         lambda: rp(mutate(lambda ev: ev[2].__setitem__("run_id", "run-" + "b" * 64)), pd)),
        ("config_not_empty", "PROFILE_INPUT_INVALID",
         lambda: rp(mutate(lambda ev: ev[0]["payload"].__setitem__("config", {"x": 1}), rederive=True), pd)),
        ("problem_schema_violation", "PROFILE_SCHEMA_INVALID",
         lambda: rp(mutate(lambda ev: ev[0]["payload"]["problem"].__setitem__("floor", 5000), rederive=True), pd)),
        ("precondition_schema_violation", "PROFILE_SCHEMA_INVALID",
         lambda: rp(mutate(lambda ev: ev[0]["payload"]["precondition"].__setitem__("status", "UNKNOWN"), rederive=True), pd)),
        ("storage_set_not_admissible", "STORAGE_INVALID",
         lambda: rp(mutate(lambda ev: ev[0]["payload"]["storage"][1].__setitem__("element_types", ["INTEGER", "EMPTY"]), rederive=True), pd)),
        # Event order and termination
        ("event_after_run_end", "EVENT_AFTER_RUN_END", lambda: rp(mutate(event_after_end), pd)),
        ("run_end_missing", "RUN_END_MISSING", lambda: rp(mutate(drop_end), pd)),
        ("run_end_with_open_frame", "RUN_END_OPEN_FRAMES", lambda: rp(mutate(drop_last_exit), pd)),
        # Profile permissions (example-profile variants: same semantics module, edited document)
        ("op_not_permitted", "MUTATION_FORBIDDEN",
         example_under("no_swap", lambda doc: doc.__setitem__("permitted_ops", [o for o in doc["permitted_ops"] if o != "SWAP"]))),
        ("op_not_permitted_non_mutating", "OP_NOT_PERMITTED",
         example_under("no_frames", lambda doc: doc.__setitem__(
             "permitted_ops", [o for o in doc["permitted_ops"] if o not in ("FRAME_ENTER", "FRAME_EXIT")]))),
        ("core_operand_kind_not_permitted", "OPERAND_KIND_NOT_PERMITTED",
         example_under("no_integer_operand", lambda doc: doc.__setitem__("operand_kinds", ["VALUE", "PARAMETER"]))),
        ("execution_after_precondition_violation", "EXECUTION_AFTER_PRECONDITION_VIOLATION",
         example_under("open_precondition", lambda doc: doc.__setitem__("precondition_schema", {"type": "object"}),
                       lambda ev: ev[0]["payload"].__setitem__("precondition", {"status": "VIOLATED"}))),
        # SWAP
        ("swap_endpoints_equal", "SWAP_MALFORMED", lambda: rp(mutate(swap_same_cell), pd)),
        ("swap_wrong_constituent", "SWAP_CONSTITUENTS_MISMATCH",
         lambda: rp(mutate(swap_reads_reordered), pd)),
        ("swap_writes_not_exchanged", "SWAP_CONSTITUENTS_MISMATCH", lambda: rp(mutate(swap_not_exchanged), pd)),
        # COMPARE operands
        ("compare_operand_not_at_location", "COMPARE_OPERAND_MISMATCH", lambda: rp(mutate(at_elsewhere), pd)),
        ("compare_parameter_misreported", "COMPARE_PARAMETER_MISMATCH", lambda: rp(mutate(param_lie), pd)),
        # FRAME
        ("frame_id_not_sequential", "FRAME_ID_INVALID",
         lambda: rp(mutate(lambda ev: [ev[enters[0]]["payload"].__setitem__("frame_id", 5),
                                       ev[exits[0]]["payload"].__setitem__("frame_id", 5)]), pd)),
        ("frame_scope_outside_storage", "FRAME_RANGE_INVALID",
         lambda: rp(mutate(lambda ev: ev[enters[0]]["payload"]["scope"].__setitem__("hi", 99)), pd)),
        ("frame_scope_exceeds_parent", "FRAME_RANGE_INVALID", lambda: rp(mutate(nest_wider_child), pd)),
        # Run record
        ("run_record_schema_invalid", "RUN_RECORD_INVALID", run_record(lambda r: r.pop("result"))),
        ("run_record_digest_differs", "TRACE_DIGEST_MISMATCH", run_record(lambda r: r.__setitem__("trace_digest", "e" * 64))),
        ("run_record_field_differs", "RUN_RECORD_MISMATCH", run_record(lambda r: r.__setitem__("event_count", r["event_count"] + 1))),
        # CORE_PROBE: only the core can reject
        ("probe_compare_empty_operand", "COMPARE_EMPTY_OPERAND",
         probe([("READ", {"location": A(1), "value": {"type": "EMPTY"}}),
                ("COMPARE", {"lhs": {"kind": "VALUE", "value": {"type": "EMPTY"}, "at": A(1)},
                             "rhs": {"kind": "INTEGER", "value": 1}, "result": 1})],
               [("READ", {"location": A(1), "value": {"type": "EMPTY"}})])),
        ("probe_compare_type_mismatch", "COMPARE_TYPE_MISMATCH",
         probe([("READ", {"location": A(0), "value": TAG5}),
                ("COMPARE", {"lhs": {"kind": "VALUE", "value": TAG5, "at": A(0)},
                             "rhs": {"kind": "INTEGER", "value": 1}, "result": 1})],
               [("READ", {"location": A(0), "value": TAG5}),
                ("COMPARE", {"lhs": {"kind": "VALUE", "value": TAG5, "at": A(0)},
                             "rhs": {"kind": "VALUE", "value": TAG5, "at": A(0)}, "result": 0})])),
        ("probe_write_immutable", "MUTATION_FORBIDDEN",
         probe([("WRITE", {"location": K0, "value": integer(9)})],
               [("WRITE", {"location": A(1), "value": integer(9)})])),
        ("probe_swap_immutable", "MUTATION_FORBIDDEN",
         probe([("SWAP", {"a": A(0), "b": K0}), ("READ", {"location": A(0), "value": TAG5}),
                ("READ", {"location": K0, "value": integer(4)}), ("WRITE", {"location": A(0), "value": integer(4)}),
                ("WRITE", {"location": K0, "value": TAG5})],
               [("SWAP", {"a": A(0), "b": A(1)}), ("READ", {"location": A(0), "value": TAG5}),
                ("READ", {"location": A(1), "value": {"type": "EMPTY"}}), ("WRITE", {"location": A(0), "value": {"type": "EMPTY"}}),
                ("WRITE", {"location": A(1), "value": TAG5})])),
        ("probe_duplicate_storage_name", "STORAGE_INVALID",
         probe_variant("dup_names", probe_doc(storage_sets=[[{k: d[k] for k in ("name", "kind", "element_types", "initial", "mutable")}
                                                            for d in PROBE_STORAGE + [PROBE_STORAGE[2]]]]),
                       probe_doc(), [],
                       storage=PROBE_STORAGE + [PROBE_STORAGE[2]] if defective else None)),
        ("probe_initial_length_differs", "STORAGE_INVALID",
         probe([], [], problem=dict(PROBE_PROBLEM, k=[integer(4), integer(5)]) if defective else None)),
        ("probe_initial_values_outside_types", "STORAGE_INVALID",
         probe([], [], problem=dict(PROBE_PROBLEM, k=[TAG5]) if defective else None)),
    ]
    return cases


def core_hostile_cases(impl: Any, tmp: Path) -> list[tuple[str, str, Callable[[], Any]]]:
    return _cases(impl, tmp, defective=True)


def core_positive_cases(impl: Any, tmp: Path) -> list[tuple[str, str, Callable[[], Any]]]:
    return _cases(impl, tmp, defective=False)
