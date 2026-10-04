# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""A synthetic workload recorded under INTEGER_SEQUENCE_EXAMPLE: a running maximum with one swap.

It exists to exercise the public core (reads, writes, compares on VALUE / PARAMETER / INTEGER
operands, a compound SWAP, nested frames, result validation and metrics). It is not a
benchmark and says nothing about any algorithm's correctness or cost.
"""

from __future__ import annotations

from typing import Any

from ..profiles import ProfileDirs, profile_for
from ..recorder import Frame, RecorderV04, cell, integer, scalar

PROFILE_ID = "INTEGER_SEQUENCE_EXAMPLE"


def record(values: list[int], floor: int = 0, profile_dirs: ProfileDirs = None) -> RecorderV04:
    _, digest = profile_for(PROFILE_ID, profile_dirs)
    storage = [
        {"name": "seq", "kind": "ARRAY", "element_types": ["INTEGER"], "length": len(values),
         "initial": "FROM_PROBLEM", "mutable": True},
        {"name": "best", "kind": "SCALAR", "element_types": ["INTEGER"], "initial": "ZERO", "mutable": True},
    ]
    rec = RecorderV04("running_maximum_v1.0", "commons.running-maximum.v1", PROFILE_ID, digest,
                      {"values": list(values), "floor": floor}, {"status": "SATISFIED"}, storage,
                      {"seq": [integer(v) for v in values], "best": integer(0)})
    best = scalar("best")
    with Frame(rec, "scan", {"storage": "seq", "lo": 0, "hi": len(values)}):
        for i in range(len(values)):
            v = rec.read(cell("seq", i))
            current = rec.read(best)
            if rec.compare({"kind": "VALUE", "value": v, "at": cell("seq", i)},
                           {"kind": "VALUE", "value": current, "at": best},
                           (v["value"] > current["value"]) - (v["value"] < current["value"])) > 0:
                rec.compare({"kind": "VALUE", "value": v, "at": cell("seq", i)},
                            {"kind": "PARAMETER", "name": "floor", "value": floor},
                            (v["value"] > floor) - (v["value"] < floor))
                rec.write(best, v)
    if len(values) >= 2:
        with Frame(rec, "swap_ends", {"storage": "seq", "lo": 0, "hi": len(values)}):
            rec.compare({"kind": "INTEGER", "value": len(values)}, {"kind": "INTEGER", "value": 2},
                        (len(values) > 2) - (len(values) < 2))
            rec.swap(cell("seq", 0), cell("seq", len(values) - 1))
    return rec


def result_of(rec: RecorderV04) -> dict[str, Any]:
    final = [v["value"] for v in rec._state["seq"]]
    return {"final": final, "best": rec._state["best"]["value"]}
