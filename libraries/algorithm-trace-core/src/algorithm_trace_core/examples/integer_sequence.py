# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Semantics for the synthetic INTEGER_SEQUENCE_EXAMPLE profile (Commons-native).

Problem: {"values": [int, ...], "floor": int}. Storage: a mutable INTEGER array ``seq``
initialized from the problem and a mutable INTEGER scalar ``best`` starting at ZERO.
Result: {"final": [int, ...], "best": int}; ``final`` must equal the replayed array and
``best`` the replayed scalar. ``floor`` is the only PARAMETER. INTEGER operands must lie
within [-1000, 1000]. This module pins no algorithm; it only gives replay a meaning.
"""

from __future__ import annotations

from typing import Any

from ..framing import ReplayError

INTEGER_BOUND = 1000


def check_begin(ctx: Any) -> None:
    values = ctx.problem["values"]
    if ctx.decl["seq"]["length"] != len(values):
        raise ReplayError("PROFILE_INPUT_INVALID", "seq length must equal the number of problem values", 0)


def from_problem(decl: dict[str, Any], ctx: Any) -> list[dict[str, Any]]:
    return [{"type": "INTEGER", "value": v} for v in ctx.problem["values"]]


def check_read(ctx: Any, loc: dict[str, Any], seq: int) -> None:
    return None


def check_write(ctx: Any, loc: dict[str, Any], value: dict[str, Any], seq: int) -> None:
    return None


def parameter(ctx: Any, name: str) -> int | None:
    return ctx.problem["floor"] if name == "floor" else None


def check_integer(ctx: Any, value: int, seq: int) -> None:
    if not -INTEGER_BOUND <= value <= INTEGER_BOUND:
        raise ReplayError("PROFILE_OPERAND_INVALID", f"INTEGER operand {value} outside [-{INTEGER_BOUND}, {INTEGER_BOUND}]", seq)


def check_argument(ctx: Any, operation: int, value: dict[str, Any], seq: int) -> None:
    raise ReplayError("OPERAND_KIND_NOT_PERMITTED", "INTEGER_SEQUENCE_EXAMPLE has no operation arguments", seq)


def on_frame_enter(ctx: Any, name: str, seq: int) -> None:
    return None


def on_frame_exit(ctx: Any, name: str, seq: int) -> None:
    return None


def check_result(ctx: Any, result: dict[str, Any]) -> None:
    if result["final"] != [v["value"] for v in ctx.arrays["seq"]]:
        raise ReplayError("RESULT_MISMATCH", "result.final differs from the replayed array")
    if result["best"] != ctx.scalars["best"]["value"]:
        raise ReplayError("RESULT_MISMATCH", "result.best differs from the replayed scalar")
