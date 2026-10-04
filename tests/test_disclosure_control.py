# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""PRIVATE_REVIEW_CONTENT_PUBLICATION_REQUIRES_EXPLICIT_CLEARANCE (WO-COMMONS-MEMBRANE-EVALUATION-01B §13).

Private review details (verdicts, round counts, finding ids, internal commercial labels and
reviewer reasoning) may not appear on a private-origin release surface without an explicit
clearance entry. The markers live in docs/private-review-markers.v0.1.json.
"""

import json
import re

import pytest

from conftest import ROOT

REGISTRY = json.loads((ROOT / "docs/private-review-markers.v0.1.json").read_text())


def release_surfaces(root=ROOT) -> list:
    """Every file that carries a private-origin release."""
    index = json.loads((root / "releases/package-index-v0.1.json").read_text())
    origins = json.loads((root / "provenance/ORIGIN_DISCLOSURE_LOCATIONS_V0_1.json").read_text())
    paths = set()
    for entry in index["packages"]:
        if entry["source_disclosure_level"] != "PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN":
            continue
        for base in (root / entry["bundle_root"], root / "releases" / entry["package_id"]):
            paths |= {p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        paths |= {root / r["path"] for r in origins["approved_records"] if r["package_id"] == entry["package_id"]}
    return sorted(paths)


def findings(rel: str, text: str, registry=REGISTRY) -> list:
    cleared = {(c["path"], c["marker_id"], c["text"]) for c in registry["clearances"]}
    out = []
    for marker in registry["markers"]:
        for m in re.finditer(marker["pattern"], text):
            if (rel, marker["id"], m.group(0)) not in cleared:
                out.append((rel, marker["id"], m.group(0)))
    return out


def test_release_surfaces_carry_no_uncleared_private_review_content():
    out = []
    for path in release_surfaces():
        out += findings(path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8", errors="replace"))
    assert out == []


def test_surfaces_include_bundle_releases_and_approved_records():
    rels = {p.relative_to(ROOT).as_posix() for p in release_surfaces()}
    assert "libraries/algorithm-trace-core/PROVENANCE.json" in rels
    assert "releases/algorithm-trace-core/0.1.0/manifest.json" in rels
    assert "reports/COMMONS_FIRST_EXPORT_01A_V0_1.md" in rels


# Synthetic variants of the categories that crossed the membrane in commit fe2f49e6.
HOSTILE = [
    "The clearance passed after two REVISE rounds.",
    "The related family was labelled UNCERTAIN.",
    "Recorded with export_authorized: false.",
    "Review round 2 asked for a narrower allowlist.",
    "R1 verdict: ACCEPT_WITH_LIMITATIONS.",
    "Fixed NB6 and R1-NB3.",
    "The reviewer found a leaking assertion in a draft test.",
    "Held as REPAIR_REQUIRED until the receipt was repaired.",
]

ORDINARY = [
    "The source clearance was independently reviewed and merged in the origin.",
    "Review accepted at the exact head.",
    "Commercial impact is COMPLEMENTARY, by explicit adjudication of the repository owner.",
    "The commercial review inputs and the decision are recorded in the private clearance receipt.",
    "Private review content is not disclosed.",
    "Each round of the replay rebuilds state from the trace bytes.",
]


@pytest.mark.parametrize("text", HOSTILE)
def test_private_review_detail_is_detected(text):
    assert findings("reports/X.md", text)


@pytest.mark.parametrize("text", ORDINARY)
def test_ordinary_public_statements_pass(text):
    assert findings("reports/X.md", text) == []


def test_explicit_clearance_is_exact():
    text = "one REVISE round"
    reg = dict(REGISTRY, clearances=[{"path": "reports/X.md", "marker_id": "REVIEW_VERDICT", "text": "REVISE",
                                      "basis": "test"}])
    remaining = findings("reports/X.md", text, reg)
    assert ("reports/X.md", "REVIEW_VERDICT", "REVISE") not in remaining
    assert remaining  # the round count is a separate marker and is not cleared
    assert findings("reports/Y.md", "REVISE", reg)  # clearance is per path


def test_clearance_entries_are_complete():
    for c in REGISTRY["clearances"]:
        assert {"path", "marker_id", "text", "basis"} <= set(c) and c["basis"].strip()
