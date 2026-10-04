# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Permissive semantics for the test-only CORE_PROBE profile.

Every hook accepts, so a hostile control replayed under CORE_PROBE can only be rejected by the
generic core. Problem: {"<storage name>": [value, ...]} for each FROM_PROBLEM storage.
"""

from __future__ import annotations

from typing import Any


def check_begin(ctx: Any) -> None:
    return None


def from_problem(decl: dict[str, Any], ctx: Any) -> Any:
    values = ctx.problem[decl["name"]]
    return values if decl["kind"] == "ARRAY" else values[0]


def check_read(ctx: Any, loc: dict[str, Any], seq: int) -> None:
    return None


def check_write(ctx: Any, loc: dict[str, Any], value: dict[str, Any], seq: int) -> None:
    return None


def parameter(ctx: Any, name: str) -> Any:
    return None


def check_integer(ctx: Any, value: int, seq: int) -> None:
    return None


def check_argument(ctx: Any, operation: int, value: dict[str, Any], seq: int) -> None:
    return None


def on_frame_enter(ctx: Any, name: str, seq: int) -> None:
    return None


def on_frame_exit(ctx: Any, name: str, seq: int) -> None:
    return None


def check_result(ctx: Any, result: dict[str, Any]) -> None:
    return None
