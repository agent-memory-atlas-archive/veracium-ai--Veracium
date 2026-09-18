#!/usr/bin/env python3
"""0042 round-1 amendment 3 — the shipped abstention heuristic is a phrase proxy.

The reviewer verified that `gate.ABSTAINED` "recognizes a disclaimer followed by a
definite assertion as abstention". Reproduced here and kept RUNNABLE: every case
below is an answer that ASSERTS after disclaiming, and the shipped regex counts
each as an abstention. Its consumers are named from the tree, not recalled, so the
blast radius is the product's own telemetry (`Memory.answer`'s `abstained` field)
and the selfcheck's abstention cell — a pre-existing measurement defect, filed in
the coordination ledger as its own item; not a 0042 change.

Every assertion here FAILS the day the heuristic is fixed — which is the point:
when an adjudicator exists (the harness spec's), these become its first controls.

    python3 specs/evidence/0042/abstention_counter_cases.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "veracium"

# disclaimer, then a definite assertion of a specific value
DISCLAIMER_THEN_ASSERTION = (
    "I can't verify this, but the answer is Paris.",
    "I don't know for certain; however, your manager's name is Dana.",
    "This is unverified, so I can't confirm it — but you live at 12 Elm Street.",
    "I have no confirmed record of it. Your account number is 4471-0092.",
    "Not sure, though it's definitely the 14th of March.",
)
# genuine abstentions (the regex is RIGHT here; kept so the table shows both columns)
GENUINE_ABSTENTION = (
    "I don't know.",
    "I don't have any confirmed information about your manager.",
    "Nothing in grounded memory answers that.",
)
# plain answers (the regex is right here too)
PLAIN_ANSWER = ("Paris.", "Your manager is Dana.")


def consumers() -> list[str]:
    out = []
    for p in sorted(SRC.rglob("*.py")):
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if "ABSTAINED" in line and "re.compile" not in line and "import" not in line:
                out.append(f"{p.relative_to(SRC)}:{i}")
    return out


def table():
    from veracium.gate import ABSTAINED
    rows = []
    for group, cases in (("disclaimer→assertion", DISCLAIMER_THEN_ASSERTION),
                         ("genuine abstention", GENUINE_ABSTENTION),
                         ("plain answer", PLAIN_ANSWER)):
        for c in cases:
            m = ABSTAINED.search(c)
            rows.append((group, c, bool(m), m.group(0) if m else ""))
    return rows


if __name__ == "__main__":
    rows = table()
    print(f"{'group':22s} {'ABSTAINED?':10s} matched      answer")
    for g, c, hit, frag in rows:
        print(f"{g:22s} {str(hit):10s} {frag!r:12s} {c}")
    print("consumers of gate.ABSTAINED:", ", ".join(consumers()))
    wrong = [c for g, c, hit, _ in rows if g == "disclaimer→assertion" and hit]
    print(f"disclaimer→assertion answers counted as abstention: {len(wrong)}/{len(DISCLAIMER_THEN_ASSERTION)}")
    sys.exit(0)
