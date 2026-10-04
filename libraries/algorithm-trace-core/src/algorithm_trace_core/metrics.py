# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Logical metrics from canonical v0.4 events. A SWAP counts once as a swap; its constituent
READs and WRITEs count once each as reads and writes (COMPOUND_OPERATION != DOUBLE_COUNTED_PRIMITIVES)."""

from __future__ import annotations

from collections import Counter
from typing import Any


def derive_metrics_v04(events: list[dict[str, Any]]) -> dict[str, int]:
    ops = Counter(e["op"] for e in events)
    depth = max_depth = 0
    for e in events:
        if e["op"] == "FRAME_ENTER":
            depth += 1
            max_depth = max(max_depth, depth)
        elif e["op"] == "FRAME_EXIT":
            depth -= 1
    return {"reads": ops["READ"], "writes": ops["WRITE"], "comparisons": ops["COMPARE"], "swaps": ops["SWAP"],
            "event_count": len(events), "frame_entries": ops["FRAME_ENTER"], "max_frame_depth": max_depth}
