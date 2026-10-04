# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Generic AlgorithmTrace v0.4 replay core.

Owns: canonical framing, core-schema validation, sequence and identity, derived run_id
(binding profile_id and profile_schema_digest), exact profile resolution, profile-schema
validation of problem / precondition / result, storage admission against the profile's
storage sets, typed ARRAY/SCALAR state, READ/WRITE state transitions, compound SWAP,
read provenance, COMPARE validity under the profile's declared comparison mode, and frame
structure. A profile's semantics module is called only through fixed hooks and owns
abstract meaning (precondition re-derivation, ranges, per-operation abstract checks, result).

Procedure-specific control flow is never here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import fastjsonschema
import jsonschema

from . import TRACE_SCHEMA_VERSION
from .canonical import canonical_digest
from .framing import ReplayError, _check_sequence, load_schema, parse_jsonl
from .profiles import Profile, ProfileDirs, resolve, validate_part

CORE_SCHEMA = "algorithm-trace-core.v0.4.schema.json"
RUN_SCHEMA = "algorithm-run.v0.4.schema.json"


@lru_cache(maxsize=None)
def _core() -> Any:
    jsonschema.Draft202012Validator.check_schema(load_schema(CORE_SCHEMA))
    return fastjsonschema.compile(load_schema(CORE_SCHEMA))


@dataclass
class ReplayContext:
    """State and history visible to profile hooks (read-only by convention)."""
    first: dict[str, Any]
    problem: dict[str, Any]
    precondition: dict[str, Any]
    decl: dict[str, dict[str, Any]]
    arrays: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    scalars: dict[str, dict[str, Any]] = field(default_factory=dict)
    frames: list[tuple[int, str, dict[str, Any] | None]] = field(default_factory=list)
    reads: list[dict[str, Any]] = field(default_factory=list)
    scratch: dict[str, Any] = field(default_factory=dict)

    def get(self, loc: dict[str, Any]) -> dict[str, Any]:
        return self.scalars[loc["storage"]] if loc["kind"] == "SCALAR" else self.arrays[loc["storage"]][loc["index"]]


@dataclass(frozen=True)
class ReplayResultV04:
    run_id: str
    algorithm_id: str
    implementation_id: str
    profile_id: str
    profile_schema_digest: str
    problem: dict[str, Any]
    result: dict[str, Any]
    final_arrays: dict[str, list[dict[str, Any]]]
    final_scalars: dict[str, dict[str, Any]]
    trace_digest: str
    event_count: int
    events: list[dict[str, Any]]


def _check_location(ctx: ReplayContext, loc: dict[str, Any], seq: int) -> None:
    decl = ctx.decl.get(loc["storage"])
    if decl is None:
        raise ReplayError("STORAGE_NOT_DECLARED", f"{loc['storage']} is not declared storage", seq)
    if (loc["kind"] == "SCALAR") != (decl["kind"] == "SCALAR"):
        raise ReplayError("LOCATION_KIND_MISMATCH", f"{loc['kind']} location on {decl['kind']} storage", seq)
    if loc["kind"] == "ARRAY_CELL" and not 0 <= loc["index"] < decl["length"]:
        raise ReplayError("INDEX_OUT_OF_RANGE", f"{loc['storage']}[{loc['index']}] outside {decl['length']}", seq)


def _order_key(profile: Profile, operand: dict[str, Any], seq: int) -> tuple:
    value = operand["value"] if operand["kind"] in ("VALUE", "ARGUMENT") else {"type": "INTEGER", "value": operand["value"]}
    if value["type"] == "EMPTY":
        raise ReplayError("COMPARE_EMPTY_OPERAND", "EMPTY is not comparable", seq)
    if profile.doc["comparison"] == "NUMERIC_KEY":
        return ("N", value["key"] if value["type"] == "TAGGED_ITEM" else value["value"])
    if value["type"] == "TAGGED_ITEM":  # TOTAL_KEY_TAG
        return ("T", value["key"], value["tag"])
    return ("I", value["value"])


def replay_v04(trace_bytes: bytes, *, expected_digest: str | None = None,
               run_record: dict[str, Any] | None = None, profile_dirs: ProfileDirs = None) -> ReplayResultV04:
    events = parse_jsonl(trace_bytes)
    validate = _core()
    for pos, event in enumerate(events):
        try:
            validate(event)
        except fastjsonschema.JsonSchemaException as exc:
            raise ReplayError("SCHEMA_INVALID", f"line {pos}: {exc.message}") from None
    _check_sequence(events)
    first = events[0]
    if first["op"] != "RUN_BEGIN":
        raise ReplayError("RUN_BEGIN_MISSING", "first event must be RUN_BEGIN", first["seq"])
    for fld, code in (("run_id", "RUN_ID_MISMATCH"), ("algorithm_id", "ALGORITHM_ID_MISMATCH"),
                      ("implementation_id", "IMPLEMENTATION_ID_MISMATCH")):
        for event in events:
            if event[fld] != first[fld]:
                raise ReplayError(code, f"{fld} differs from RUN_BEGIN", event["seq"])
    b = first["payload"]
    derived = "run-" + canonical_digest({
        "schema_version": TRACE_SCHEMA_VERSION, "algorithm_id": first["algorithm_id"],
        "implementation_id": first["implementation_id"], "profile_id": b["profile_id"],
        "profile_schema_digest": b["profile_schema_digest"], "problem": b["problem"], "storage": b["storage"],
        "config": b["config"], "seed": b["seed"], "instrumentation_version": b["instrumentation_version"]})
    if first["run_id"] != derived:
        raise ReplayError("RUN_ID_NOT_DERIVED", "run_id does not bind profile, digest, problem, storage and identity", 0)

    profile = resolve(b["profile_id"], b["profile_schema_digest"], profile_dirs)
    sem = profile.semantics
    validate_part(profile.problem, b["problem"], "PROFILE_SCHEMA_INVALID")
    validate_part(profile.precondition, b["precondition"], "PROFILE_SCHEMA_INVALID")
    if b["config"] != {} or b["seed"] is not None:
        raise ReplayError("PROFILE_INPUT_INVALID", "v0.4 runs take empty config and no seed", 0)
    names = [d["name"] for d in b["storage"]]
    if len(names) != len(set(names)):
        raise ReplayError("STORAGE_INVALID", "duplicate storage name", 0)
    shape = [{k: d[k] for k in ("name", "kind", "element_types", "initial", "mutable")} for d in b["storage"]]
    if shape not in profile.doc["storage_sets"]:
        raise ReplayError("STORAGE_INVALID", f"storage {names} is not an admissible set for {b['profile_id']}", 0)

    ctx = ReplayContext(first, b["problem"], b["precondition"], {d["name"]: d for d in b["storage"]})
    sem.check_begin(ctx)
    for d in b["storage"]:
        if d["kind"] == "ARRAY":
            init = {"IDENTITY": lambda i: {"type": "INTEGER", "value": i}, "ONES": lambda i: {"type": "INTEGER", "value": 1},
                    "EMPTY": lambda i: {"type": "EMPTY"}}.get(d["initial"])
            values = [init(i) for i in range(d["length"])] if init else sem.from_problem(d, ctx)
            if len(values) != d["length"]:
                raise ReplayError("STORAGE_INVALID", f"{d['name']} initial length differs from declared length", 0)
            ctx.arrays[d["name"]] = values
        else:
            ctx.scalars[d["name"]] = {"type": "INTEGER", "value": 0} if d["initial"] == "ZERO" else sem.from_problem(d, ctx)
        initial = ctx.arrays.get(d["name"], [ctx.scalars.get(d["name"])])
        if any(v["type"] not in d["element_types"] for v in initial):
            raise ReplayError("STORAGE_INVALID", f"{d['name']} initial values outside its element types", 0)

    permitted = set(profile.doc["permitted_ops"])
    operand_kinds = set(profile.doc["operand_kinds"])
    read_values: set[str] = set()
    swap: dict[str, Any] | None = None
    next_frame, ended, end_payload = 0, False, None
    for event in events[1:]:
        op, p, seq = event["op"], event["payload"], event["seq"]
        if ended:
            raise ReplayError("EVENT_AFTER_RUN_END", f"{op} after RUN_END", seq)
        if op == "RUN_BEGIN":
            raise ReplayError("RUN_BEGIN_DUPLICATE", "second RUN_BEGIN", seq)
        if swap is not None:
            stage = swap["stage"]
            want_op = "READ" if stage < 2 else "WRITE"
            want_loc = swap["a"] if stage in (0, 2) else swap["b"]
            if op != want_op or p.get("location") != want_loc:
                raise ReplayError("SWAP_CONSTITUENTS_MISMATCH", f"SWAP step {stage} expected {want_op} {want_loc}", seq)
            if stage == 2 and p["value"] != swap["vb"] or stage == 3 and p["value"] != swap["va"]:
                raise ReplayError("SWAP_CONSTITUENTS_MISMATCH", "SWAP writes must exchange the values read", seq)
        if op == "RUN_END":
            if ctx.frames:
                raise ReplayError("RUN_END_OPEN_FRAMES", f"{len(ctx.frames)} frames still open", seq)
            ended, end_payload = True, p
            continue
        if op not in permitted:
            code = "MUTATION_FORBIDDEN" if op in ("WRITE", "SWAP") else "OP_NOT_PERMITTED"
            raise ReplayError(code, f"{op} is not permitted by profile {b['profile_id']}", seq)
        if b["precondition"].get("status") == "VIOLATED":
            raise ReplayError("EXECUTION_AFTER_PRECONDITION_VIOLATION", f"{op} on a rejected input", seq)
        if op == "READ":
            _check_location(ctx, p["location"], seq)
            if ctx.get(p["location"]) != p["value"]:
                raise ReplayError("READ_VALUE_MISMATCH", f"{p['location']} holds {ctx.get(p['location'])}", seq)
            sem.check_read(ctx, p["location"], seq)
            read_values.add(canonical_digest(p["value"]))
            ctx.reads.append(p)
            if swap is not None:
                swap["va" if swap["stage"] == 0 else "vb"] = p["value"]
        elif op == "WRITE":
            loc, value = p["location"], p["value"]
            _check_location(ctx, loc, seq)
            decl = ctx.decl[loc["storage"]]
            if not decl["mutable"]:
                raise ReplayError("MUTATION_FORBIDDEN", f"{loc['storage']} is immutable", seq)
            if value["type"] not in decl["element_types"]:
                raise ReplayError("WRITE_TYPE_INVALID", f"{value['type']} not admissible in {loc['storage']}", seq)
            sem.check_write(ctx, loc, value, seq)
            if loc["kind"] == "SCALAR":
                ctx.scalars[loc["storage"]] = value
            else:
                ctx.arrays[loc["storage"]][loc["index"]] = value
        elif op == "SWAP":
            if p["a"] == p["b"]:
                raise ReplayError("SWAP_MALFORMED", "swap endpoints must differ", seq)
            for loc in (p["a"], p["b"]):
                _check_location(ctx, loc, seq)
                if not ctx.decl[loc["storage"]]["mutable"]:
                    raise ReplayError("MUTATION_FORBIDDEN", f"{loc['storage']} is immutable", seq)
        elif op == "COMPARE":
            keys = []
            for side in ("lhs", "rhs"):
                operand = p[side]
                if operand["kind"] not in operand_kinds:
                    raise ReplayError("OPERAND_KIND_NOT_PERMITTED", f"{operand['kind']} in {b['profile_id']}", seq)
                if operand["kind"] == "VALUE":
                    if canonical_digest(operand["value"]) not in read_values:
                        raise ReplayError("COMPARE_UNREAD_OPERAND", f"{side} value was never READ", seq)
                    if operand["at"] is not None:
                        _check_location(ctx, operand["at"], seq)
                        if ctx.get(operand["at"]) != operand["value"]:
                            raise ReplayError("COMPARE_OPERAND_MISMATCH", f"{side} not at its declared location", seq)
                elif operand["kind"] == "PARAMETER":
                    if sem.parameter(ctx, operand["name"]) != operand["value"]:
                        raise ReplayError("COMPARE_PARAMETER_MISMATCH", f"{side} is not the declared parameter", seq)
                elif operand["kind"] == "INTEGER":
                    sem.check_integer(ctx, operand["value"], seq)
                else:
                    sem.check_argument(ctx, operand["operation"], operand["value"], seq)
                keys.append(_order_key(profile, operand, seq))
            if keys[0][0] != keys[1][0]:
                raise ReplayError("COMPARE_TYPE_MISMATCH", "operands are not comparable under the profile's comparison", seq)
            if p["result"] != (keys[0] > keys[1]) - (keys[0] < keys[1]):
                raise ReplayError("COMPARE_RESULT_WRONG", f"compare{tuple(keys)} != {p['result']}", seq)
        elif op == "FRAME_ENTER":
            if p["frame_id"] != next_frame:
                raise ReplayError("FRAME_ID_INVALID", f"expected frame_id {next_frame}", seq)
            scope = p["scope"]
            if scope is not None:
                d = ctx.decl.get(scope["storage"])
                if d is None or d["kind"] != "ARRAY" or not scope["lo"] <= scope["hi"] <= d["length"]:
                    raise ReplayError("FRAME_RANGE_INVALID", "scope outside declared array storage", seq)
                parent = next((s for _, _, s in reversed(ctx.frames) if s is not None), None)
                if parent is not None and parent["storage"] == scope["storage"] and \
                        not parent["lo"] <= scope["lo"] <= scope["hi"] <= parent["hi"]:
                    raise ReplayError("FRAME_RANGE_INVALID", "nested scope exceeds its parent", seq)
            next_frame += 1
            ctx.frames.append((p["frame_id"], p["name"], scope))
            sem.on_frame_enter(ctx, p["name"], seq)
        elif op == "FRAME_EXIT":
            if not ctx.frames or ctx.frames[-1][0] != p["frame_id"]:
                raise ReplayError("FRAME_EXIT_INVALID", f"frame {p['frame_id']} is not innermost", seq)
            _, name, _ = ctx.frames.pop()
            sem.on_frame_exit(ctx, name, seq)
        if op == "SWAP":
            swap = {"a": p["a"], "b": p["b"], "stage": 0}
        elif swap is not None:
            swap["stage"] += 1
            if swap["stage"] == 4:
                swap = None
    if not ended:
        raise ReplayError("RUN_END_MISSING", "trace does not terminate with RUN_END", events[-1]["seq"])
    if swap is not None:
        raise ReplayError("SWAP_CONSTITUENTS_MISMATCH", "trace ends inside a SWAP", events[-1]["seq"])
    result = end_payload["result"]
    validate_part(profile.result, result, "PROFILE_SCHEMA_INVALID")
    sem.check_result(ctx, result)

    digest = hashlib.sha256(trace_bytes).hexdigest()
    if expected_digest is not None and digest != expected_digest:
        raise ReplayError("TRACE_DIGEST_MISMATCH", f"computed {digest}, expected {expected_digest}")
    if run_record is not None:
        error = jsonschema.exceptions.best_match(
            jsonschema.Draft202012Validator(load_schema(RUN_SCHEMA)).iter_errors(run_record))
        if error is not None:
            raise ReplayError("RUN_RECORD_INVALID", error.message)
        if run_record["trace_digest"] != digest:
            raise ReplayError("TRACE_DIGEST_MISMATCH", "run record digest differs")
        expected = {"run_id": first["run_id"], "algorithm_id": first["algorithm_id"],
                    "implementation_id": first["implementation_id"], "profile_id": b["profile_id"],
                    "profile_schema_digest": b["profile_schema_digest"],
                    "instrumentation_version": b["instrumentation_version"], "precondition": b["precondition"],
                    "result": result, "config": b["config"], "seed": b["seed"], "event_count": len(events),
                    "problem_digest": canonical_digest(b["problem"])}
        for fld, value in expected.items():
            if run_record[fld] != value:
                raise ReplayError("RUN_RECORD_MISMATCH", f"run record {fld} disagrees with the trace")
    return ReplayResultV04(first["run_id"], first["algorithm_id"], first["implementation_id"], b["profile_id"],
                           b["profile_schema_digest"], b["problem"], result, ctx.arrays, ctx.scalars, digest,
                           len(events), events)
