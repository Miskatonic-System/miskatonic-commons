# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""PUBLIC_HISTORY_REWRITE_AUTHORITY = NONE, checked structurally (WO-COMMONS-PUBLICATION-FENCE-00C §9).

Normative documents (root *.md, docs/*.md, .github/*.md) are split into units:
headings, list items together with their lead-in, table rows, code lines and
sentences. Each unit is NFKC-folded. Then:

1. Any unit naming a history-changing action must match a registered
   PROHIBITED clause exactly.
2. Any unit combining a history-scope word with permissive or exception
   wording must match a registered clause exactly: a PROHIBITED clause or a
   reviewed ACKNOWLEDGED_NON_HISTORY statement.
3. Registered PROHIBITED clauses carry exactly one negation and no permissive
   or exception wording. ACKNOWLEDGED_NON_HISTORY statements may never name a
   history-changing action.
4. Normative documents contain no non-ASCII letters (homoglyph defence).
"""

import copy
import json
import re
import unicodedata
from pathlib import Path

import pytest

from conftest import ROOT

REGISTRY = json.loads((ROOT / "docs/history-norms.v0.1.json").read_text())
NEGATION = re.compile(r"(?i)\b(no|not|never|nor|none|without|cannot|prohibited|forbidden)\b")


def rx(key, registry=None):
    return re.compile(r"(?i)(" + "|".join((registry or REGISTRY)[key]) + r")")


def normative_documents(root: Path = ROOT) -> dict:
    paths = list(root.glob("*.md")) + list((root / "docs").glob("*.md")) + list((root / ".github").glob("*.md"))
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in sorted(paths)}


def units(text: str) -> list:
    """Return [(unit, lead_in)] where lead_in is set for list items."""
    out, para, item, last_sentence, in_code = [], [], None, None, False

    def norm(s):
        return " ".join(unicodedata.normalize("NFKC", s).split())

    def flush_para():
        nonlocal para, last_sentence
        if para:
            for sentence in re.split(r"(?<=[.!?:;])\s+", norm(" ".join(para))):
                if sentence:
                    out.append((sentence, None))
                    last_sentence = sentence
            para = []

    def flush_item():
        nonlocal item
        if item is not None:
            out.append((norm(item[0]), item[1]))
            item = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            flush_para(); flush_item(); in_code = not in_code
            continue
        stripped = line.strip()
        if in_code:
            if stripped:
                out.append((norm(stripped), None))
            continue
        if not stripped:
            flush_para(); flush_item()
            continue
        if stripped.startswith(("#", "|", ">")):
            flush_para(); flush_item()
            out.append((norm(stripped), None))
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
    action, scope, grant = (rx(k, registry) for k in ("action_terms", "scope_terms", "grant_terms"))
    problems = []
    for clause in registry["clauses"]:
        text = clause["text"].replace("**", "")
        kind = clause.get("kind")
        if kind == "PROHIBITED":
            lead = clause.get("list_lead_in")
            if grant.search(text) or (lead and grant.search(lead)):
                problems.append(f"{clause['id']}: permissive or exception wording in a prohibition")
            negs = len(NEGATION.findall(text)) + (len(NEGATION.findall(lead)) if lead else 0)
            if negs != 1:
                problems.append(f"{clause['id']}: needs exactly one negation, found {negs}")
        elif kind == "ACKNOWLEDGED_NON_HISTORY":
            if action.search(text):
                problems.append(f"{clause['id']}: an acknowledged statement may not name a history-changing action")
        else:
            problems.append(f"{clause['id']}: unknown clause kind {kind!r}")
    registered = {(c["document"], c["text"], c.get("list_lead_in")): c for c in registry["clauses"]}
    seen = set()
    for doc, text in documents.items():
        for ch in text:
            if ord(ch) > 127 and unicodedata.category(ch).startswith("L"):
                problems.append(f"{doc}: non-ASCII letter {ch!r} (U+{ord(ch):04X}) in a normative document")
                break
        for unit, lead_in in units(text):
            names_action = bool(action.search(unit))
            scoped_grant = bool(scope.search(unit) and grant.search(unit))
            if not (names_action or scoped_grant):
                continue
            key = next((k for k in ((doc, unit, lead_in), (doc, unit, None)) if k in registered), None)
            if key is None:
                problems.append(f"{doc}: unregistered history-relevant wording: {unit[:140]!r}")
                continue
            if names_action and registered[key]["kind"] != "PROHIBITED":
                problems.append(f"{doc}: history-changing action outside a prohibition: {unit[:140]!r}")
            seen.add(key)
    for key in set(registered) - seen:
        problems.append(f"registered clause not found verbatim in {key[0]}: {key[1][:80]!r}")
    return problems


def test_public_history_rewrite_authority_is_none():
    assert REGISTRY["property"] == "PUBLIC_HISTORY_REWRITE_AUTHORITY = NONE"
    assert violations(normative_documents(), REGISTRY) == []


# Hostile controls (WO §9 and 00C review round 0) ---------------------------------

POLICY = "docs/PUBLIC_COMMIT_IDENTITY_POLICY.md"
MAINT = "docs/MAINTENANCE_POLICY.md"


def _with(doc, addition, after=None):
    docs = normative_documents()
    if after:
        assert after in docs[doc]
        docs[doc] = docs[doc].replace(after, after + " " + addition, 1)
    else:
        docs[doc] = docs[doc] + "\n" + addition + "\n"
    return docs


HOSTILE = [
    (POLICY, "Maintainers may force-push to main to remove old metadata.", None),
    (POLICY, "It is not prohibited to rewrite public history.", None),
    (MAINT, "## Exceptions\n\nThe bootstrap history can be rewritten once to remove author metadata.", None),
    ("docs/SUPPORT.md", "- Maintainers rewrite history when asked.", None),
    ("CONTRIBUTING.md", "| Rewrite | allowed for maintainers |", None),
    (POLICY, "```\ngit push --force origin main  # rewrite allowed\n```", None),
    # 00C review round 0 bypass inputs
    (MAINT, "Maintainers may run `git push --force` on main when needed.", None),
    (MAINT, "Maintainers may push --force-with-lease to main.", None),
    (MAINT, "Re-writing public history is permitted for maintainers.", None),
    (MAINT, "Maintainers may re-base main.", None),
    (MAINT, "Maintainers may purge leaked commits from public history with BFG.", None),
    (MAINT, "Published commits may be replaced or dropped by the owner.", None),
    (MAINT, "The bootstrap commits are exempt from the history rule above.", None),
    (MAINT, "The owner may waive the preceding rule.", None),
    (MAINT, "The rule above does not apply to the bootstrap commits.", "Public history is never rewritten."),
    (MAINT, "Maintainers may reіwrite main.", None),  # Cyrillic i homoglyph
    (".github/pull_request_template.md", "Maintainers may squash public history.", None),
    # 00C review round 1 residual paraphrases
    (MAINT, "The bootstrap commits are out of scope for this section.", None),
    (MAINT, "The prohibition above is suspended during incident response.", None),
    (MAINT, "Owners are free to overwrite the default branch to remove leaked data.", None),
    (MAINT, "Old revisions may be edited by the owner.", None),
    ("SECURITY.md", "Maintainers may delete and re-create the repository to remove a leak.", None),
]


@pytest.mark.parametrize("doc,addition,after", HOSTILE)
def test_hostile_rewrite_wording_is_rejected(doc, addition, after):
    assert violations(_with(doc, addition, after), REGISTRY)


@pytest.mark.parametrize("clause", [
    {"id": "X1", "document": POLICY, "kind": "PROHIBITED", "text": "It is not prohibited to rewrite public history."},
    {"id": "X2", "document": POLICY, "kind": "PROHIBITED", "text": "History may be rewritten except for the bootstrap commits."},
    {"id": "X3", "document": POLICY, "kind": "PERMITTED", "text": "Maintainers may rewrite public history."},
    {"id": "X4", "document": POLICY, "kind": "ACKNOWLEDGED_NON_HISTORY", "text": "Maintainers may force-push to main."},
    {"id": "X5", "document": MAINT, "kind": "ACKNOWLEDGED_NON_HISTORY", "text": "Maintainers may purge commits from main."},
])
def test_registering_permissive_or_contradictory_clauses_is_rejected(clause):
    registry = copy.deepcopy(REGISTRY)
    registry["clauses"].append(clause)
    docs = normative_documents()
    docs[clause["document"]] += "\n" + clause["text"] + "\n"
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
