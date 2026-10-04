# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Regenerate the INTEGER_SEQUENCE_EXAMPLE profile document (pins its semantics module by SHA-256).

Usage: python scripts/build_example_profile.py [--check]
"""

import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "src" / "algorithm_trace_core"
DOC = PKG / "profiles" / "integer_sequence_example.profile.v0.4.json"


def document() -> dict:
    module = PKG / "examples" / "integer_sequence.py"
    integer = {"type": "integer", "minimum": -1000, "maximum": 1000}
    return {
        "profile_document_version": "algorithm-trace-core.trace-profile.v0.4",
        "profile_id": "INTEGER_SEQUENCE_EXAMPLE",
        "profile_version": "0.1.0",
        "semantics_module": "algorithm_trace_core.examples.integer_sequence",
        "semantics_module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "problem_schema": {"type": "object", "additionalProperties": False, "required": ["values", "floor"],
                           "properties": {"values": {"type": "array", "maxItems": 64, "items": integer},
                                          "floor": integer}},
        "precondition_schema": {"type": "object", "additionalProperties": False, "required": ["status"],
                                "properties": {"status": {"const": "SATISFIED"}}},
        "result_schema": {"type": "object", "additionalProperties": False, "required": ["final", "best"],
                          "properties": {"final": {"type": "array", "items": integer}, "best": integer}},
        "storage_sets": [[
            {"name": "seq", "kind": "ARRAY", "element_types": ["INTEGER"], "initial": "FROM_PROBLEM", "mutable": True},
            {"name": "best", "kind": "SCALAR", "element_types": ["INTEGER"], "initial": "ZERO", "mutable": True}]],
        "permitted_ops": ["RUN_BEGIN", "RUN_END", "READ", "WRITE", "COMPARE", "SWAP", "FRAME_ENTER", "FRAME_EXIT"],
        "operand_kinds": ["VALUE", "PARAMETER", "INTEGER"],
        "comparison": "NUMERIC_KEY",
        "contract_policy_schema": {"type": "object"},
    }


def render() -> bytes:
    return (json.dumps(document(), indent=2, sort_keys=True) + "\n").encode()


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if DOC.read_bytes() == render() else 1)
    DOC.write_bytes(render())
