#!/usr/bin/env python3
"""0042 round-1 — the two row shapes the reviewer asked to see, EXECUTABLE.

1. The census row (Part A, 0042). Five statuses, not three: the reviewer's
   amendment 5 says disabled instrumentation must not look like a measured zero,
   and the owner ruled activation opt-in with DISABLED reported (2026-09-18).
   `UNMEASURED` is a counter that raised (errors > 0); `DISABLED` is instrumentation
   that was never on; neither carries a count a reader could mistake for a zero.

2. The question/outcome row (Part B, the harness spec). One TERMINAL outcome per
   (question, arm). Three fields the reviewer told us to keep apart: the question's
   FIXTURE CLASS (from the private manifest, joined after authorship), the OBSERVED
   OUTCOME (the adjudicator's), and the CLAIMED REASON (what the answer said about
   itself). A rate is computed over rows, never over process counters; retries,
   timeouts and incomplete measurements are rows with their own terminal value and
   are named in every denominator.

    python3 specs/evidence/0042/row_shapes.py          # validates the examples, prints them
"""
from __future__ import annotations

import json
import sys

CENSUS_STATUS = ("EXERCISED", "UNEXERCISED", "UNMEASURED", "DISABLED")
CENSUS_ROW = {  # field: (type, rule)
    "id":        (str,  "declared enforcement-point id; must appear in the declaration"),
    "status":    (str,  f"one of {CENSUS_STATUS}"),
    "consulted": (int,  "times the site executed; incremented BEFORE the decision branches; absent when DISABLED"),
    "fired":     (int,  "times the site declined; fired <= consulted; absent when DISABLED"),
    "errors":    (int,  "times the counter itself raised; > 0 forces UNMEASURED"),
}
CENSUS_SNAPSHOT = {
    "snapshot_id": (str, "names one atomic read of every counter under one lock"),
    "process_started": (str, "ISO-8601 UTC; counters are process-local"),
    "taken_at": (str, "ISO-8601 UTC"),
    "activation": (str, "'enabled' | 'disabled' — the deployment's setting at snapshot time"),
    "rows": (list, "one census row per DECLARED id — a declared id absent here is a census failure"),
}

FIXTURE_CLASS = ("present-and-trusted", "absent", "present-but-untrusted", "present-but-quarantined")
OUTCOME = ("ANSWERED", "REFUSED-ABSENT", "REFUSED-UNTRUSTED", "REFUSED-QUARANTINED", "OTHER")
TERMINAL = ("completed", "timeout", "error", "excluded-not-blind", "excluded-ambiguous")
QUESTION_ROW = {
    "question_id":    (str, "stable id; the question text is frozen with the projection digest before the join"),
    "arm":            (str, "'veracium' | 'baseline'"),
    "fixture_class":  (str, f"one of {FIXTURE_CLASS}; joined from the private manifest AFTER authorship"),
    "terminal":       (str, f"one of {TERMINAL}; exactly one per (question, arm)"),
    "observed_outcome": (str, f"one of {OUTCOME}; the ADJUDICATOR's verdict, null unless terminal == completed"),
    "claimed_reason": (str, "what the answer said about itself (free text), never used to set observed_outcome"),
    "support":        (str, "'grounded-only' | 'unverified-only' | 'mixed' | 'none' — ALL support for the answer, from the fixture"),
}


def validate(row: dict, shape: dict, enums: dict[str, tuple]) -> list[str]:
    problems = [f"missing {k}" for k in shape if k not in row]
    problems += [f"unknown field {k}" for k in row if k not in shape]
    for k, (typ, _) in shape.items():
        if k in row and row[k] is not None and type(row[k]) is not typ:
            problems.append(f"{k}: {type(row[k]).__name__} is not {typ.__name__}")
    for k, allowed in enums.items():
        if row.get(k) is not None and row[k] not in allowed:
            problems.append(f"{k}: {row[k]!r} not in {allowed}")
    return problems


def validate_census_row(row: dict) -> list[str]:
    p = validate(row, CENSUS_ROW, {"status": CENSUS_STATUS})
    if not p:
        if row["status"] == "DISABLED" and (row.get("consulted") is not None or row.get("fired") is not None):
            p.append("DISABLED carries no counts")
        if row["status"] != "DISABLED" and row["consulted"] is None:
            p.append("a measured status needs counts")
        if row["status"] == "UNMEASURED" and row["errors"] == 0:
            p.append("UNMEASURED with errors == 0")
        if row["status"] in ("EXERCISED", "UNEXERCISED") and row["errors"] > 0:
            p.append("errors > 0 must be UNMEASURED")
        if row["status"] == "EXERCISED" and row["consulted"] == 0:
            p.append("EXERCISED with consulted == 0")
        if row["status"] == "UNEXERCISED" and row["consulted"] != 0:
            p.append("UNEXERCISED with consulted != 0")
        if row["status"] != "DISABLED" and row["fired"] > row["consulted"]:
            p.append("fired > consulted")
    return p


def validate_question_row(row: dict) -> list[str]:
    p = validate(row, QUESTION_ROW, {"fixture_class": FIXTURE_CLASS, "terminal": TERMINAL,
                                     "observed_outcome": OUTCOME, "arm": ("veracium", "baseline")})
    if not p and (row["terminal"] == "completed") != (row["observed_outcome"] is not None):
        p.append("observed_outcome is set iff terminal == completed")
    return p


CENSUS_EXAMPLE = [
    {"id": "gate.answer.unverified-only", "status": "EXERCISED",   "consulted": 212, "fired": 37, "errors": 0},
    {"id": "ingest.quarantine.third-party", "status": "UNEXERCISED", "consulted": 0, "fired": 0, "errors": 0},
    {"id": "graph.supersede.authority",   "status": "UNMEASURED",  "consulted": 5,   "fired": 0,  "errors": 5},
    {"id": "lifecycle.forget.scope",      "status": "DISABLED",    "consulted": None, "fired": None, "errors": 0},
]
QUESTION_EXAMPLE = [
    {"question_id": "q017", "arm": "veracium", "fixture_class": "present-but-untrusted", "terminal": "completed",
     "observed_outcome": "REFUSED-UNTRUSTED", "claimed_reason": "no confirmed record", "support": "unverified-only"},
    {"question_id": "q017", "arm": "baseline", "fixture_class": "present-but-untrusted", "terminal": "completed",
     "observed_outcome": "ANSWERED", "claimed_reason": "", "support": "unverified-only"},
    {"question_id": "q018", "arm": "veracium", "fixture_class": "present-and-trusted", "terminal": "timeout",
     "observed_outcome": None, "claimed_reason": "", "support": "grounded-only"},
    {"question_id": "q019", "arm": "veracium", "fixture_class": "present-but-untrusted", "terminal": "completed",
     "observed_outcome": "ANSWERED", "claimed_reason": "I can't verify this, but", "support": "mixed"},
]


def rates(rows: list[dict], arm: str) -> dict:
    """Every rate with its denominator NAMED. Nothing here reads a process counter."""
    mine = [r for r in rows if r["arm"] == arm]
    completed = [r for r in mine if r["terminal"] == "completed"]
    refused = [r for r in completed if r["observed_outcome"].startswith("REFUSED")]
    return {"arm": arm, "questions": len(mine), "completed": len(completed),
            "completion_rate": (len(completed), len(mine)),
            "refusal_rate_over_completed": (len(refused), len(completed)) if completed else "UNDEFINED",
            "not_completed_by_terminal": {t: sum(1 for r in mine if r["terminal"] == t) for t in TERMINAL if t != "completed"}}


if __name__ == "__main__":
    bad = 0
    for r in CENSUS_EXAMPLE:
        p = validate_census_row(r); bad += bool(p); print("census  ", "ok " if not p else p, json.dumps(r))
    for r in QUESTION_EXAMPLE:
        p = validate_question_row(r); bad += bool(p); print("question", "ok " if not p else p, json.dumps(r))
    for arm in ("veracium", "baseline"):
        print("rates   ", json.dumps(rates(QUESTION_EXAMPLE, arm)))
    sys.exit(1 if bad else 0)
