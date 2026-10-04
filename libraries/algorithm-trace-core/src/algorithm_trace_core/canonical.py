# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Canonical JSON (RFC 8785) and digest helpers shared by every layer."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import rfc8785


def canonical_bytes(value: Any) -> bytes:
    """RFC 8785 canonical JSON bytes (no trailing newline)."""
    return rfc8785.dumps(value)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        out[key] = val
    return out


def _reject_constant(token: str) -> Any:
    raise ValueError(f"non-finite JSON number: {token}")


def strict_loads(text: str | bytes) -> Any:
    """Parse JSON rejecting duplicate keys and NaN/Infinity."""
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)
