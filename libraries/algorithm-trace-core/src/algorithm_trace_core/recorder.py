# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Generic AlgorithmTrace v0.4 recorder: typed ARRAY/SCALAR storage, locations, compound SWAP, frames.

Accounting: read -> one READ; write -> one WRITE; swap(a, b) -> SWAP followed by exactly
READ a, READ b, WRITE a <- old(b), WRITE b <- old(a) (the SWAP is counted once as a swap;
its reads and writes are counted once each as reads and writes); compare -> one COMPARE
over held operands (no storage access). Initial storage is declared, never traced.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import INSTRUMENTATION_VERSION, RUN_SCHEMA_VERSION, TRACE_SCHEMA_VERSION
from .canonical import canonical_digest, sha256_hex
from .framing import serialize_jsonl

EMPTY = {"type": "EMPTY"}


def integer(v: int) -> dict[str, Any]:
    return {"type": "INTEGER", "value": v}


def tagged(key: int, tag: str) -> dict[str, Any]:
    return {"type": "TAGGED_ITEM", "key": key, "tag": tag}


def cell(storage: str, index: int) -> dict[str, Any]:
    return {"kind": "ARRAY_CELL", "storage": storage, "index": index}


def scalar(storage: str) -> dict[str, Any]:
    return {"kind": "SCALAR", "storage": storage}


def executed_path(module_file: str, root: str | Path | None = None) -> str:
    """Path of an executed module, relative to ``root`` (default: the current directory) when inside it."""
    base = Path(root if root is not None else Path.cwd()).resolve()
    path = Path(module_file).resolve()
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def derive_run_id_v04(algorithm_id: str, implementation_id: str, begin: dict[str, Any]) -> str:
    return "run-" + canonical_digest({
        "schema_version": TRACE_SCHEMA_VERSION, "algorithm_id": algorithm_id, "implementation_id": implementation_id,
        "profile_id": begin["profile_id"], "profile_schema_digest": begin["profile_schema_digest"],
        "problem": begin["problem"], "storage": begin["storage"], "config": begin["config"], "seed": begin["seed"],
        "instrumentation_version": begin["instrumentation_version"]})


class RecorderV04:
    def __init__(self, algorithm_id: str, implementation_id: str, profile_id: str, profile_digest: str,
                 problem: dict[str, Any], precondition: dict[str, Any], storage: list[dict[str, Any]],
                 initial: dict[str, Any]) -> None:
        self.algorithm_id, self.implementation_id = algorithm_id, implementation_id
        self.begin = {"profile_id": profile_id, "profile_schema_digest": profile_digest, "problem": problem,
                      "precondition": precondition, "storage": storage, "config": {}, "seed": None,
                      "instrumentation_version": INSTRUMENTATION_VERSION}
        self.run_id = derive_run_id_v04(algorithm_id, implementation_id, self.begin)
        self._state = {k: (list(v) if isinstance(v, list) else v) for k, v in initial.items()}
        self._decl = {d["name"]: d for d in storage}
        self.events: list[dict[str, Any]] = []
        self._frames: list[int] = []
        self._next_frame = 0
        self._emit("RUN_BEGIN", self.begin)

    def _emit(self, op: str, payload: dict[str, Any]) -> None:
        self.events.append({"schema_version": TRACE_SCHEMA_VERSION, "run_id": self.run_id, "seq": len(self.events),
                            "op": op, "algorithm_id": self.algorithm_id, "implementation_id": self.implementation_id,
                            "payload": payload})

    def _get(self, loc: dict[str, Any]) -> Any:
        if loc["kind"] == "SCALAR":
            return self._state[loc["storage"]]
        cells = self._state[loc["storage"]]
        if not 0 <= loc["index"] < len(cells):
            raise IndexError(f"{loc} out of range")
        return cells[loc["index"]]

    def _put(self, loc: dict[str, Any], value: dict[str, Any]) -> None:
        if not self._decl[loc["storage"]]["mutable"]:
            raise PermissionError(f"{loc['storage']} is immutable")
        if value["type"] not in self._decl[loc["storage"]]["element_types"]:
            raise TypeError(f"{value['type']} not admissible in {loc['storage']}")
        if loc["kind"] == "SCALAR":
            self._state[loc["storage"]] = value
        else:
            cells = self._state[loc["storage"]]
            if not 0 <= loc["index"] < len(cells):
                raise IndexError(f"{loc} out of range")
            cells[loc["index"]] = value

    def read(self, loc: dict[str, Any]) -> dict[str, Any]:
        value = self._get(loc)
        self._emit("READ", {"location": loc, "value": value})
        return value

    def write(self, loc: dict[str, Any], value: dict[str, Any]) -> None:
        self._get(loc)  # bounds
        self._emit("WRITE", {"location": loc, "value": value})
        self._put(loc, value)

    def swap(self, a: dict[str, Any], b: dict[str, Any]) -> None:
        if a == b:
            raise ValueError("a swap needs two distinct locations")
        self._get(a), self._get(b)
        self._emit("SWAP", {"a": a, "b": b})
        va, vb = self.read(a), self.read(b)
        self.write(a, vb)
        self.write(b, va)

    def compare(self, lhs: dict[str, Any], rhs: dict[str, Any], result: int) -> int:
        self._emit("COMPARE", {"lhs": lhs, "rhs": rhs, "result": result})
        return result

    def frame_enter(self, name: str, scope: dict[str, Any] | None) -> int:
        frame_id, self._next_frame = self._next_frame, self._next_frame + 1
        self._frames.append(frame_id)
        self._emit("FRAME_ENTER", {"frame_id": frame_id, "name": name, "scope": scope})
        return frame_id

    def frame_exit(self, frame_id: int) -> None:
        if not self._frames or self._frames.pop() != frame_id:
            raise RuntimeError("frame exit does not match innermost frame")
        self._emit("FRAME_EXIT", {"frame_id": frame_id})

    def finish(self, result: dict[str, Any]) -> None:
        if self._frames:
            raise RuntimeError("RUN_END with open frames")
        self._emit("RUN_END", {"result": result})

    def seal(self, input_id: str | None, source_sha256: str, executed_source_path: str,
             result: dict[str, Any]) -> tuple[bytes, str, dict[str, Any]]:
        trace_bytes = serialize_jsonl(self.events)
        digest = sha256_hex(trace_bytes)
        b = self.begin
        record = {"schema_version": RUN_SCHEMA_VERSION, "run_id": self.run_id, "profile_id": b["profile_id"],
                  "profile_schema_digest": b["profile_schema_digest"], "algorithm_id": self.algorithm_id,
                  "implementation_id": self.implementation_id, "implementation_source_sha256": source_sha256,
                  "executed_source_path": executed_source_path, "instrumentation_version": INSTRUMENTATION_VERSION,
                  "input_id": input_id, "problem_digest": canonical_digest(b["problem"]),
                  "precondition": b["precondition"], "result": result, "config": {}, "seed": None,
                  "trace_digest": digest, "event_count": len(self.events)}
        return trace_bytes, digest, record


class Frame:
    def __init__(self, rec: RecorderV04, name: str, scope: dict[str, Any] | None = None) -> None:
        self._rec, self._name, self._scope, self._id = rec, name, scope, -1

    def __enter__(self) -> None:
        self._id = self._rec.frame_enter(self._name, self._scope)

    def __exit__(self, *exc: object) -> None:
        if exc[0] is None:
            self._rec.frame_exit(self._id)
