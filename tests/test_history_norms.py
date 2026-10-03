# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""PUBLIC_HISTORY_REWRITE_AUTHORITY = NONE, checked structurally (WO-COMMONS-PUBLICATION-FENCE-00C §9).

Normative documents are split into units (headings, list items with their
lead-in, table rows, code lines, sentences). Every unit that mentions a
history-changing action must exactly match a clause registered in
docs/history-norms.v0.1.json. Every registered clause must be a prohibition
with exactly one negation and no permissive or exception wording.
"""

import copy
import json
import re
from pathlib import Path

import pytest

from conftest import ROOT

REGISTRY = json.loads((ROOT / "docs/history-norms.v0.1.json").read_text())
NEGATION = re.compile(r"(?i)\b(no|not|never|nor|none|without|cannot|prohibited|forbidden)\b")
PERMISSIVE = re.compile(
    r"(?i)\b(may|can|could|might|allowed|allow|allows|permit\w*|authori[sz]\w*|except\w*|unless|however|but|"
    r"reserved|optional\w*|only if|provided that)\b")


def normative_documents(root: Path = ROOT) -> dict:
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(list(root.glob("*.md")) + list((root / "docs").glob("*.md")))}


def units(text: str) -> list:
    """Return [(unit, lead_in)] where lead_in is set for list items."""
    out, para, item, last_sentence, in_code = [], [], None, None, False

    def flush_para():
        nonlocal para, last_sentence
        if para:
            joined = " ".join(" ".join(para).split())
            for sentence in re.split(r"(?<=[.!?:])\s+", joined):
                if sentence:
                    out.append((sentence, None))
                    last_sentence = sentence
            para = []

    def flush_item():
        nonlocal item
        if item is not None:
            out.append((" ".join(item[0].split()), item[1]))
            item = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            flush_para(); flush_item(); in_code = not in_code
            continue
        if in_code:
            if line.strip():
                out.append((line.strip(), None))
            continue
        stripped = line.strip()
        if not stripped:
            flush_para(); flush_item()
            continue
        if stripped.startswith("#") or stripped.startswith("|") or stripped.startswith(">"):
            flush_para(); flush_item()
            out.append((" ".join(stripped.split()), None))
            continue
        if re.match(r"^([-*+]|\d+[.)])\s+", stripped):
            flush_para(); flush_item()
            item = [stripped, last_sentence]
            continue
        if item is not None and raw.startswith((" ", "\t")):
            item[0] += " " + stripped
            continue
        flush_item()
        para.append(stripped)
    flush_para(); flush_item()
    return out


def violations(documents: dict, registry: dict) -> list:
    terms = re.compile(r"(?i)\b(" + "|".join(registry["action_terms"]) + r")\b")
    problems = []
    clauses = registry["clauses"]
    for clause in clauses:
        text = clause["text"].replace("**", "")
        if clause.get("modality") != "PROHIBITED":
            problems.append(f"{clause['id']}: modality {clause.get('modality')!r} is not PROHIBITED")
        if PERMISSIVE.search(text):
            problems.append(f"{clause['id']}: permissive or exception wording")
        own = len(NEGATION.findall(text))
        lead = clause.get("list_lead_in")
        lead_neg = len(NEGATION.findall(lead)) if lead else 0
        if lead and PERMISSIVE.search(lead):
            problems.append(f"{clause['id']}: permissive lead-in")
        if own + lead_neg != 1:
            problems.append(f"{clause['id']}: needs exactly one negation, found {own + lead_neg}")
    registered = {(c["document"], c["text"], c.get("list_lead_in")) for c in clauses}
    seen = set()
    for doc, text in documents.items():
        for unit, lead_in in units(text):
            if not terms.search(unit):
                continue
            key = (doc, unit, lead_in if (doc, unit, lead_in) in registered else None)
            if (doc, unit, lead_in) in registered:
                seen.add((doc, unit, lead_in))
            elif (doc, unit, None) in registered and lead_in is None:
                seen.add(key)
            else:
                problems.append(f"{doc}: unregistered history-action wording: {unit[:120]!r}")
    for clause in registered - seen:
        problems.append(f"registered clause not found verbatim in {clause[0]}: {clause[1][:80]!r}")
    return problems


def test_public_history_rewrite_authority_is_none():
    assert REGISTRY["property"] == "PUBLIC_HISTORY_REWRITE_AUTHORITY = NONE"
    assert violations(normative_documents(), REGISTRY) == []


# Hostile controls (WO §9) -------------------------------------------------------

POLICY = "docs/PUBLIC_COMMIT_IDENTITY_POLICY.md"
MAINT = "docs/MAINTENANCE_POLICY.md"


def _with(doc, addition):
    docs = normative_documents()
    docs[doc] = docs[doc] + "\n" + addition + "\n"
    return docs


@pytest.mark.parametrize("doc,addition", [
    (POLICY, "Maintainers may force-push to main to remove old metadata."),            # explicit permission
    (POLICY, "It is not prohibited to rewrite public history."),                        # double negation
    (MAINT, "## Exceptions\n\nThe bootstrap history can be rewritten once to remove author metadata."),  # other section + exception
    ("docs/SUPPORT.md", "- Maintainers rewrite history when asked."),                     # different document, list item
    ("CONTRIBUTING.md", "| Rewrite | allowed for maintainers |"),                          # table row
    (POLICY, "```\ngit push --force origin main  # rewrite allowed\n```"),               # code block
])
def test_unregistered_rewrite_wording_is_rejected(doc, addition):
    assert violations(_with(doc, addition), REGISTRY)


@pytest.mark.parametrize("mutate", [
    lambda r: r["clauses"][0].__setitem__("modality", "PERMITTED"),
    lambda r: r["clauses"].append({"id": "X1", "document": POLICY, "modality": "PROHIBITED",
                                   "text": "It is not prohibited to rewrite public history."}),
    lambda r: r["clauses"].append({"id": "X2", "document": POLICY, "modality": "PROHIBITED",
                                   "text": "History may be rewritten except for the bootstrap commits."}),
    lambda r: r["clauses"].append({"id": "X3", "document": POLICY, "modality": "PERMITTED",
                                   "text": "Maintainers may rewrite public history."}),
])
def test_registering_permissive_or_contradictory_clauses_is_rejected(mutate):
    registry = copy.deepcopy(REGISTRY)
    mutate(registry)
    docs = normative_documents()
    extra = registry["clauses"][-1]
    if extra["id"].startswith("X"):
        docs[extra["document"]] += "\n" + extra["text"] + "\n"
    assert violations(docs, registry)


def test_removing_a_registered_prohibition_is_detected():
    docs = normative_documents()
    docs[MAINT] = docs[MAINT].replace("Public history is never rewritten.", "")
    assert violations(docs, REGISTRY)


def test_list_item_needs_its_prohibiting_lead_in():
    docs = normative_documents()
    docs["docs/EXPORT_POLICY.md"] = docs["docs/EXPORT_POLICY.md"].replace(
        "The following are prohibited:", "The following are recommended:")
    assert violations(docs, REGISTRY)
