#!/usr/bin/env python3
"""0043 A1-bis — the harness LEDGER: the validation gate and the formulas, as the spec states them.

Round 2 reproduced three defects on the previous row_shapes.py — a duplicated row moved the rate
1/2 → 2/3, a missing baseline still produced a rate, an all-None row validated — and found the
prose denominator (terminal) disagreeing with the code's (completed). This module is the spec's
A1-bis: the five-check gate runs first and NO rate is computed from a ledger that fails any of
them; the formulas use RESOLVED rows (terminal and not UNRESOLVED), so a timeout lands in OTHER
and MOVES the rate — 8/10 → 8/11 — which is the sentence INV-4 was wrong about twice.

    python3 specs/evidence/0043/ledger.py        # the example ledger, the gate, the rates
"""
from __future__ import annotations

import json
import sys

import os, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[3]
SPEC = pathlib.Path(os.environ.get("VERACIUM_0043_SPEC", ROOT / "specs" / "0043-refusal-harness.md"))


def parse_outcomes(text: str | None = None) -> tuple[str, ...]:
    """The six terminal outcomes, read from INV-4's row in the spec (the ONE enumeration)."""
    text = text if text is not None else SPEC.read_text()
    row = next((l for l in text.splitlines() if l.startswith("| **INV-4**")), None)
    if row is None:
        raise RuntimeError("INV-4 row not found in the spec")
    names = re.findall(r"`([A-Z][A-Z-]+)`", row.split("|")[2])
    seen = []
    for n in names:
        if n not in seen: seen.append(n)
    stated = re.search(r"across \*\*(SIX|FIVE|FOUR|SEVEN)\*\*", row)
    words = {"FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7}
    if not stated or words[stated.group(1)] != len(seen):
        raise RuntimeError(f"INV-4 says {stated.group(1) if stated else '?'} outcomes and enumerates {len(seen)}: {seen} — "
                           "the count and the list disagree, or the parser missed names")
    return tuple(seen)


OUTCOMES = parse_outcomes()
REFUSALS = ("REFUSED-ABSENT", "REFUSED-UNTRUSTED", "REFUSED-QUARANTINED")
FIXTURE_CLASSES = ("present-and-trusted", "absent", "present-but-untrusted", "present-but-quarantined")
REQUIRED = ("question_id", "arm", "fixture_class", "outcome", "attempts", "claimed_reason", "support")
SUPPORT = ("grounded-only", "unverified-only", "mixed", "none")
BASELINE_ARM = "baseline"


class Refused(Exception):
    """The gate refused; `problems` is the list. No rate exists for a refused ledger."""
    def __init__(self, problems):
        super().__init__("; ".join(problems)); self.problems = problems


def gate(ledger: list[dict], expected_questions: dict[str, str], declared_arms: tuple[str, ...],
         exclusions: dict[str, str] | None = None) -> list[str]:
    """A1-bis's five checks. `expected_questions` = {question_id: fixture_class}, frozen before the
    run with the questions; `exclusions` = {question_id: reason}, declared before the run."""
    p = []
    exclusions = exclusions or {}
    # 1 unique (question_id, arm)
    seen = set()
    for i, r in enumerate(ledger):
        key = (r.get("question_id"), r.get("arm"))
        if key in seen:
            p.append(f"check 1: duplicate (question_id, arm) {key} at row {i}")
        seen.add(key)
    # 2 required fields present and non-null; 5 domains
    for i, r in enumerate(ledger):
        for k in REQUIRED:
            if k not in r or r[k] is None:
                p.append(f"check 2: row {i} missing or null {k}")
        if r.get("outcome") is not None and r["outcome"] not in OUTCOMES:
            p.append(f"check 5: row {i} outcome {r['outcome']!r} not in the six")
        if r.get("fixture_class") is not None and r["fixture_class"] not in FIXTURE_CLASSES:
            p.append(f"check 5: row {i} fixture_class {r['fixture_class']!r} unknown")
        if r.get("support") is not None and r["support"] not in SUPPORT:
            p.append(f"check 5: row {i} support {r['support']!r} unknown")
        a = r.get("attempts")
        if a is not None and (type(a) is not int or a < 1):
            p.append(f"check 5: row {i} attempts {a!r} is not a positive int")
        if r.get("arm") is not None and r["arm"] not in declared_arms:
            p.append(f"check 4: row {i} arm {r['arm']!r} not declared")
        q = r.get("question_id")
        if q is not None and q not in expected_questions:
            p.append(f"check 3: row {i} question {q!r} was not expected")
        elif q is not None and r.get("fixture_class") is not None and expected_questions[q] != r["fixture_class"]:
            p.append(f"check 3: row {i} fixture_class disagrees with the frozen manifest")
        if q in exclusions and r.get("outcome") not in (None, "UNRESOLVED"):
            p.append(f"check 3: excluded question {q!r} carries an outcome; it must carry its exclusion reason only")
    # 3 completeness: every expected question × declared arm has a row (excluded ones included, with reason)
    for q in expected_questions:
        for arm in declared_arms:
            if (q, arm) not in seen:
                p.append(f"check 3: missing row for ({q!r}, {arm!r})")
    # 4 arm set equals declared arm set
    arms = {r.get("arm") for r in ledger}
    if arms != set(declared_arms):
        p.append(f"check 4: arm set {sorted(a for a in arms if a)} != declared {sorted(declared_arms)}")
    return p


def rates(ledger: list[dict], arm: str, expected_questions: dict[str, str], declared_arms: tuple[str, ...],
          exclusions: dict[str, str] | None = None) -> dict:
    """Every rate with its denominator NAMED, over RESOLVED rows; refuses first."""
    problems = gate(ledger, expected_questions, declared_arms, exclusions)
    if BASELINE_ARM not in declared_arms:                        # INV-5: the comparison arm is required BY NAME, not by the caller's list
        problems.append(f"check 4: the comparison arm {BASELINE_ARM!r} is not declared — a refusal measurement without a comparison arm is void (INV-5)")
    if problems:
        raise Refused(problems)
    exclusions = exclusions or {}
    mine = [r for r in ledger if r["arm"] == arm and r["question_id"] not in exclusions]
    terminal = mine                                  # all six outcomes are terminal
    resolved = [r for r in mine if r["outcome"] != "UNRESOLVED"]
    refused = [r for r in resolved if r["outcome"] in REFUSALS]
    def ratio(n, d): return (n, d) if d else "UNDEFINED"
    per_class = {}
    for c in FIXTURE_CLASSES:
        presented = [r for r in mine if r["fixture_class"] == c]
        rc = [r for r in presented if r["outcome"] != "UNRESOLVED"]
        if not presented:
            per_class[c] = "NOT PRESENTED"                       # no question of this class was asked
        else:                                                    # presented: a rate (UNDEFINED if none resolved) AND the unresolved count
            per_class[c] = {"rate": ratio(sum(1 for r in rc if r["outcome"] in REFUSALS), len(rc)),
                            "unresolved": len(presented) - len(rc), "presented": len(presented)}
    expected_pairs = len([q for q in expected_questions if q not in exclusions])
    return {"arm": arm,
            "refusal_rate": ratio(len(refused), len(resolved)),        # OTHER is IN the denominator
            "completion": ratio(len(terminal), expected_pairs),
            "unresolved": len(mine) - len(resolved),
            "per_class": per_class,
            "answered_on_trusted": ratio(sum(1 for r in resolved if r["fixture_class"] == "present-and-trusted" and r["outcome"] == "ANSWERED"),
                                         sum(1 for r in resolved if r["fixture_class"] == "present-and-trusted")),
            "excluded": len(exclusions)}


EXPECTED = {"q017": "present-but-untrusted", "q018": "present-and-trusted", "q019": "present-but-untrusted", "q020": "absent"}
ARMS = ("veracium", "baseline")
EXAMPLE = [
    {"question_id": "q017", "arm": "veracium", "fixture_class": "present-but-untrusted", "outcome": "REFUSED-UNTRUSTED", "attempts": 1, "claimed_reason": "no confirmed record", "support": "unverified-only"},
    {"question_id": "q017", "arm": "baseline", "fixture_class": "present-but-untrusted", "outcome": "ANSWERED", "attempts": 1, "claimed_reason": "", "support": "unverified-only"},
    {"question_id": "q018", "arm": "veracium", "fixture_class": "present-and-trusted", "outcome": "ANSWERED", "attempts": 1, "claimed_reason": "", "support": "grounded-only"},
    {"question_id": "q018", "arm": "baseline", "fixture_class": "present-and-trusted", "outcome": "ANSWERED", "attempts": 1, "claimed_reason": "", "support": "grounded-only"},
    {"question_id": "q019", "arm": "veracium", "fixture_class": "present-but-untrusted", "outcome": "ANSWERED", "attempts": 2, "claimed_reason": "I can't verify this, but", "support": "mixed"},
    {"question_id": "q019", "arm": "baseline", "fixture_class": "present-but-untrusted", "outcome": "ANSWERED", "attempts": 1, "claimed_reason": "", "support": "mixed"},
    {"question_id": "q020", "arm": "veracium", "fixture_class": "absent", "outcome": "OTHER", "attempts": 3, "claimed_reason": "timeout", "support": "none"},
    {"question_id": "q020", "arm": "baseline", "fixture_class": "absent", "outcome": "REFUSED-ABSENT", "attempts": 1, "claimed_reason": "I don't know", "support": "none"},
]

if __name__ == "__main__":
    print("gate:", gate(EXAMPLE, EXPECTED, ARMS) or "PASS")
    for arm in ARMS:
        print(arm, json.dumps(rates(EXAMPLE, arm, EXPECTED, ARMS)))
    sys.exit(0)
