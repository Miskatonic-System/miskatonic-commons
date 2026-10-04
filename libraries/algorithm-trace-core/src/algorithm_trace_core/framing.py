# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Canonical JSONL framing, schema loading, sequence validation and the stable ReplayError.

Each symbol below is extracted unchanged from a frozen private source, except where noted;
see the package's PROVENANCE.json for the exact source lines and their SHA-256.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

import rfc8785

from .canonical import canonical_bytes, strict_loads


class ReplayError(Exception):
    def __init__(self, code: str, message: str, seq: int | None = None) -> None:
        super().__init__(f"{code}: {message}" + ("" if seq is None else f" (event {seq})"))
        self.code = code
        self.seq = seq


# Adapted: the package-resource name is this public package.
@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    return json.loads(resources.files("algorithm_trace_core").joinpath("schemas", name).read_text("utf-8"))


def _canon(value: Any) -> bytes:
    return rfc8785.dumps(value)


def parse_jsonl(trace_bytes: bytes) -> list[dict[str, Any]]:
    """Parse canonical JSONL framing; every line must already be RFC 8785 canonical."""
    if not isinstance(trace_bytes, (bytes, bytearray)) or not trace_bytes:
        raise ReplayError("TRACE_EMPTY", "trace has no bytes")
    if not trace_bytes.endswith(b"\n"):
        raise ReplayError("FRAMING_INVALID", "trace must end with a final LF")
    events = []
    for lineno, line in enumerate(bytes(trace_bytes)[:-1].split(b"\n")):
        if not line:
            raise ReplayError("FRAMING_INVALID", f"empty line {lineno}")
        try:
            event = strict_loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ReplayError("FRAMING_INVALID", f"line {lineno} is not strict JSON: {exc}") from None
        try:
            canonical = _canon(event)
        except Exception as exc:  # rfc8785 rejects values outside its domain
            raise ReplayError("NONCANONICAL_LINE", f"line {lineno}: {exc}") from None
        if canonical != line:
            raise ReplayError("NONCANONICAL_LINE", f"line {lineno} is not RFC 8785 canonical")
        events.append(event)
    return events


def _check_sequence(events: list[dict[str, Any]]) -> None:
    all_seqs = {e["seq"] for e in events}
    seen: set[int] = set()
    for expected, event in enumerate(events):
        seq = event["seq"]
        if seq in seen:
            raise ReplayError("SEQ_DUPLICATE", f"seq {seq} repeated", seq)
        if seq != expected:
            code = "SEQ_OUT_OF_ORDER" if expected in all_seqs else "SEQ_GAP"
            raise ReplayError(code, f"expected seq {expected}, found {seq}", seq)
        seen.add(seq)


def serialize_jsonl(events: list[dict[str, Any]]) -> bytes:
    """RFC8785(event_0) + LF + ... + RFC8785(event_n) + LF."""
    return b"".join(canonical_bytes(e) + b"\n" for e in events)
