#!/usr/bin/env python3
"""Reconcile rulings recorded in COORDINATION.md against the spec tables.

A ruling lands in COORDINATION, the spec's open-question table is updated
separately, and the two drift. `0001` Q5 read "blocking / research" for 16 hours
after it was answered; `0006` Q1 for 12. Anyone auditing "what is blocked" reads
the stale copy -- and with specs going to external review, that reader is
increasingly the reviewer.

Research's suggestion, and it is the same "derive from a definition rather than
recall" move that fixed the consumer inventory, the store mutators and the guard
list: every ruling names `<spec>-Q<n>` in a fixed form, so a grep can reconcile
the two and print the drift.

    RULED 0006-Q1

A spec question marked resolved must carry the token. A question still marked
blocking must NOT have one -- that is the direction that has actually bitten.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"
COORD = pathlib.Path.home() / "Documents" / "veracium" / "COORDINATION.md"

RULED = re.compile(r"\bRULED\s+(\d{4})-([A-Z]{0,2}-?Q\d+[a-z]?)\b", re.I)
# Which rows are questions is render_index's rule, imported, never restated: this file carried its own copy of the
# row grammar (bold ids only) and a looser section split, and so read 8 spec questions while STATUS.md read 57 and
# the specs held 104 (2026-10-12).
sys.path.insert(0, str(SPECS))
from render_index import question_rows  # noqa: E402


def _spec_questions() -> dict:
    out = {}
    for f in sorted(SPECS.glob("[0-9][0-9][0-9][0-9]-*.md")):
        num = f.name[:4]
        for row in question_rows(f.read_text()):
            out[(num, row.qid)] = dict(
                blocking="blocking" in row.rest.lower(),
                ruled=bool(RULED.search(row.rest)),
                struck=row.rest.strip().startswith("**RULED") or bool(row.strike),
                text=row.rest.strip()[:90])
    return out


def main() -> int:
    problems = []
    qs = _spec_questions()
    coord = COORD.read_text() if COORD.exists() else ""
    coord_ruled = {(m.group(1), m.group(2).upper()) for m in RULED.finditer(coord)}

    for (num, qid), q in sorted(qs.items()):
        if q["blocking"] and q["ruled"]:
            problems.append(f"{num} {qid}: carries a RULED token and is still "
                            f"marked blocking — {q['text']}")
        if (num, qid.upper()) in coord_ruled and q["blocking"]:
            problems.append(f"{num} {qid}: ruled in COORDINATION and still "
                            f"marked blocking in the spec — {q['text']}")
    for num, qid in sorted(coord_ruled):
        if (num, qid) not in qs and (num, qid.capitalize()) not in qs:
            problems.append(f"COORDINATION rules {num}-{qid}, which is not a "
                            f"question in specs/{num}-*.md")

    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"\n{len(problems)} ruling/spec disagreement(s). A ruling is not "
              f"applied until the spec says so — the answer living in "
              f"COORDINATION is what made two tables stale for half a day.",
              file=sys.stderr)
        return 1
    print(f"rulings reconciled: {len(qs)} spec questions, "
          f"{len(coord_ruled)} tokens in COORDINATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
