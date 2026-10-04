# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Implementation-agnostic trace builders and hostile cases.

An ``Impl`` bundles the functions of one AlgorithmTrace v0.4 implementation, so the same cases
can drive this package's tests and an external parity harness. Every hostile case changes one
thing and names the single ReplayError code it must produce.
"""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

PROFILE_ID = "INTEGER_SEQUENCE_EXAMPLE"
SEMANTICS_MODULE = "algorithm_trace_core.examples.integer_sequence"


@dataclass
class Impl:
    name: str
    canonical_bytes: Callable[[Any], bytes]
    canonical_digest: Callable[[Any], str]
    strict_loads: Callable[[Any], Any]
    serialize_jsonl: Callable[[list], bytes]
    recorder_cls: Any
    frame_cls: Any
    derive_run_id: Callable[..., str]
    profile_digest: Callable[[dict], str]
    derive_metrics: Callable[[list], dict]
    replay: Callable[..., Any]            # replay(trace_bytes, profile_dir, **kw)
    error_cls: type
    profile_dir: Path                     # directory holding the example profile document
    trace_schema_version: str


def example_doc(impl: Impl) -> dict[str, Any]:
    return json.loads((impl.profile_dir / "integer_sequence_example.profile.v0.4.json").read_text())


def storage(n: int) -> list[dict[str, Any]]:
    return [{"name": "seq", "kind": "ARRAY", "element_types": ["INTEGER"], "length": n,
             "initial": "FROM_PROBLEM", "mutable": True},
            {"name": "best", "kind": "SCALAR", "element_types": ["INTEGER"], "initial": "ZERO", "mutable": True}]


def integer(v: int) -> dict[str, Any]:
    return {"type": "INTEGER", "value": v}


def cell(i: int) -> dict[str, Any]:
    return {"kind": "ARRAY_CELL", "storage": "seq", "index": i}


BEST = {"kind": "SCALAR", "storage": "best"}


def record_workload(impl: Impl, values: list[int], floor: int = 0, digest: str | None = None) -> Any:
    """The synthetic running-maximum workload, driven only through the recorder API."""
    digest = digest or impl.profile_digest(example_doc(impl))
    rec = impl.recorder_cls("running_maximum_v1.0", "commons.running-maximum.v1", PROFILE_ID, digest,
                            {"values": list(values), "floor": floor}, {"status": "SATISFIED"}, storage(len(values)),
                            {"seq": [integer(v) for v in values], "best": integer(0)})
    with impl.frame_cls(rec, "scan", {"storage": "seq", "lo": 0, "hi": len(values)}):
        for i in range(len(values)):
            v = rec.read(cell(i))
            cur = rec.read(BEST)
            res = (v["value"] > cur["value"]) - (v["value"] < cur["value"])
            if rec.compare({"kind": "VALUE", "value": v, "at": cell(i)}, {"kind": "VALUE", "value": cur, "at": BEST}, res) > 0:
                rec.compare({"kind": "VALUE", "value": v, "at": cell(i)}, {"kind": "PARAMETER", "name": "floor", "value": floor},
                            (v["value"] > floor) - (v["value"] < floor))
                rec.write(BEST, v)
    if len(values) >= 2:
        with impl.frame_cls(rec, "swap_ends", {"storage": "seq", "lo": 0, "hi": len(values)}):
            rec.compare({"kind": "INTEGER", "value": len(values)}, {"kind": "INTEGER", "value": 2},
                        (len(values) > 2) - (len(values) < 2))
            rec.swap(cell(0), cell(len(values) - 1))
    final = list(values)
    if len(values) >= 2:
        final[0], final[-1] = final[-1], final[0]
    best = 0
    for v in values:
        best = max(best, v)
    rec.finish({"final": final, "best": best})
    return rec


def sealed(impl: Impl, values: list[int] = (3, -1, 7, 2), floor: int = 1) -> tuple[bytes, str, dict, list]:
    rec = record_workload(impl, list(values), floor)
    result = rec.events[-1]["payload"]["result"]
    trace, digest, run = rec.seal(None, "0" * 64, "example", result)
    return trace, digest, run, rec.events


def reserialize(impl: Impl, events: list[dict[str, Any]], *, rederive: bool = False) -> bytes:
    """Canonical bytes for mutated events; optionally re-derive run_id so only the intended defect remains."""
    events = copy.deepcopy(events)
    if rederive:
        first = events[0]
        rid = impl.derive_run_id(first["algorithm_id"], first["implementation_id"], first["payload"])
        for e in events:
            e["run_id"] = rid
    return impl.serialize_jsonl(events)


def _swap_seq(events, i, j):
    events = copy.deepcopy(events)
    events[i]["seq"], events[j]["seq"] = events[j]["seq"], events[i]["seq"]
    return events


def _first(events, op):
    return next(i for i, e in enumerate(events) if e["op"] == op)


def hostile_cases(impl: Impl, tmp: Path) -> list[tuple[str, str, Callable[[], Any]]]:
    """(name, expected ReplayError code, thunk) for every hostile control."""
    trace, digest, run, events = sealed(impl)
    rp = impl.replay
    pd = impl.profile_dir

    def mutate(fn, rederive=False):
        ev = copy.deepcopy(events)
        fn(ev)
        return reserialize(impl, ev, rederive=rederive)

    def other_dir(name, edit_doc=None, edit_module=None):
        d = tmp / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        doc = example_doc(impl)
        if edit_doc:
            edit_doc(doc)
        (d / "integer_sequence_example.profile.v0.4.json").write_text(json.dumps(doc))
        return d, impl.profile_digest(doc)

    def rebind(ev, new_digest):
        ev[0]["payload"]["profile_schema_digest"] = new_digest

    cases = [
        ("noncanonical_jsonl", "NONCANONICAL_LINE",
         lambda: rp(trace.replace(b"\n", b" \n", 1), pd)),
        ("missing_terminal_lf", "FRAMING_INVALID", lambda: rp(trace[:-1], pd)),
        ("duplicate_json_keys", "FRAMING_INVALID",
         lambda: rp(trace.replace(b'{"algorithm_id"', b'{"algorithm_id":"x","algorithm_id"', 1), pd)),
        ("nan_input", "FRAMING_INVALID",
         lambda: rp(trace.replace(b'"seq":0', b'"seq":NaN', 1), pd)),
        ("sequence_gap", "SEQ_GAP", lambda: rp(mutate(lambda ev: ev[3].__setitem__("seq", 99)), pd)),
        ("duplicate_sequence", "SEQ_DUPLICATE", lambda: rp(mutate(lambda ev: ev[3].__setitem__("seq", 2)), pd)),
        ("out_of_order_sequence", "SEQ_OUT_OF_ORDER", lambda: rp(reserialize(impl, _swap_seq(events, 2, 3)), pd)),
        ("undeclared_storage", "STORAGE_NOT_DECLARED",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "READ")]["payload"]["location"].__setitem__("storage", "ghost")), pd)),
        ("wrong_location_kind", "LOCATION_KIND_MISMATCH",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "READ")]["payload"].__setitem__(
             "location", {"kind": "SCALAR", "storage": "seq"})), pd)),
        ("out_of_range_access", "INDEX_OUT_OF_RANGE",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "READ")]["payload"]["location"].__setitem__("index", 40)), pd)),
        ("read_value_mismatch", "READ_VALUE_MISMATCH",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "READ")]["payload"].__setitem__("value", integer(999))), pd)),
        ("invalid_write_type", "WRITE_TYPE_INVALID",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "WRITE")]["payload"].__setitem__("value", {"type": "EMPTY"})), pd)),
        ("unknown_profile", "PROFILE_UNKNOWN",
         lambda: rp(mutate(lambda ev: ev[0]["payload"].__setitem__("profile_id", "NO_SUCH_PROFILE"), rederive=True), pd)),
        ("profile_digest_mismatch", "PROFILE_DIGEST_MISMATCH",
         lambda: rp(mutate(lambda ev: rebind(ev, "0" * 64), rederive=True), pd)),
        ("profile_document_schema_violation", "PROFILE_DOCUMENT_INVALID",
         lambda: (lambda d_dg: rp(mutate(lambda ev: rebind(ev, d_dg[1]), rederive=True), d_dg[0]))(
             other_dir("doc_invalid", edit_doc=lambda doc: doc.__setitem__("comparison", "LEXICAL")))),
        ("semantics_module_digest_mismatch", "PROFILE_SEMANTICS_MISMATCH",
         lambda: (lambda d_dg: rp(mutate(lambda ev: rebind(ev, d_dg[1]), rederive=True), d_dg[0]))(
             other_dir("module_mismatch", edit_doc=lambda doc: doc.__setitem__("semantics_module_sha256", "1" * 64)))),
        ("run_id_derivation_mismatch", "RUN_ID_NOT_DERIVED",
         lambda: rp(mutate(lambda ev: [e.__setitem__("run_id", "run-" + "a" * 64) for e in ev]), pd)),
        ("malformed_frame_nesting", "FRAME_EXIT_INVALID",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "FRAME_EXIT")]["payload"].__setitem__("frame_id", 7)), pd)),
        ("compare_unread_operand", "COMPARE_UNREAD_OPERAND",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "COMPARE")]["payload"]["lhs"].__setitem__("value", integer(555))), pd)),
        ("compare_wrong_result", "COMPARE_RESULT_WRONG",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "COMPARE")]["payload"].__setitem__(
             "result", -ev[_first(ev, "COMPARE")]["payload"]["result"] or 1)), pd)),
        ("compare_operand_kind_not_permitted", "OPERAND_KIND_NOT_PERMITTED",
         lambda: rp(mutate(lambda ev: ev[_first(ev, "COMPARE")]["payload"].__setitem__(
             "rhs", {"kind": "ARGUMENT", "operation": 0, "value": integer(1)})), pd)),
        ("result_schema_violation", "PROFILE_SCHEMA_INVALID",
         lambda: rp(mutate(lambda ev: ev[-1]["payload"]["result"].__setitem__("best", "seven")), pd)),
        ("trace_digest_mismatch", "TRACE_DIGEST_MISMATCH", lambda: rp(trace, pd, expected_digest="f" * 64)),
    ]
    return cases
