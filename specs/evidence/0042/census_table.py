#!/usr/bin/env python3
"""0042 Part A-1/A-2 — the census STATE TABLE, the report gate, the snapshot header and the
trace diff, all GENERATED FROM the spec rather than written beside it.

Round 2 (A5) found the spec naming five statuses, the validator supporting four and its test
requiring four — three carriers of one value. So this module does not carry its own copy of the
table: `STATE_TABLE` is parsed from `specs/0042-exercised-guarantees.md`'s Part A-1 table at
import, and the status function below is a literal reading of its rows in precedence order
(first match wins). If the spec's table changes — a row, its condition text, its order — the
parse changes with it and `test_0042_evidence.py` asserts the code's condition functions still
match the parsed condition strings one to one.

    python3 specs/evidence/0042/census_table.py          # prints the parsed table and the example report
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import os

ROOT = pathlib.Path(__file__).resolve().parents[3]
# The ADOPTED text is the authority; VERACIUM_0042_SPEC exists only so the evidence can be built
# against a candidate BEFORE adoption (the adoption commit lands spec and evidence together).
SPEC = pathlib.Path(os.environ.get("VERACIUM_0042_SPEC", ROOT / "specs" / "0042-exercised-guarantees.md"))


def parse_state_table(text: str | None = None) -> list[dict]:
    """The Part A-1 table: [{status, condition, precedence}] in the spec's own order."""
    text = text if text is not None else SPEC.read_text()
    sect = re.search(r"^### Part A-1 .*?(?=^### Part A-2 )", text, re.S | re.M)
    if not sect:
        raise RuntimeError("Part A-1 not found in the spec — the state table has moved or vanished")
    rows = []
    for line in sect.group(0).splitlines():
        m = re.match(r"^\| (?:🔴 )?\*\*`([A-Z]+)`\*\* \| `([^`]+)` \| \*\*(\d+)\*\*", line)
        if m:
            rows.append({"status": m.group(1), "condition": m.group(2), "precedence": int(m.group(3))})
    if not rows:
        raise RuntimeError("Part A-1 carries no status rows in the expected form")
    stated = re.search(r"#### .*?\b(SIX|FIVE|FOUR|SEVEN)\b statuses", sect.group(0))
    words = {"FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7}
    if not stated or words[stated.group(1)] != len(rows):
        raise RuntimeError(f"the prose says {stated.group(1) if stated else '?'} statuses and the table has {len(rows)} rows — "
                           "two carriers of one count disagree, or the parser missed rows")
    precs = [r["precedence"] for r in rows]
    if precs != sorted(precs) or precs != list(range(1, len(rows) + 1)):
        raise RuntimeError(f"precedence is not 1..n in table order: {precs}")
    return rows


STATE_TABLE = parse_state_table()
STATUSES = tuple(r["status"] for r in STATE_TABLE)

# The conditions, as CODE, keyed by the exact condition string the spec carries. The test
# asserts every parsed row's condition string is a key here and every key is a parsed row —
# so a reworded or added condition in the spec fails until this dict follows it.
CONDITIONS = {
    "enabled == false":                  lambda t: t["enabled"] is False,
    "declared == false":                 lambda t: t["declared"] is False,
    "errors > 0":                        lambda t: t["errors"] > 0,
    "consulted == 0":                    lambda t: t["consulted"] == 0,
    "consulted > 0 and fired == 0":      lambda t: t["consulted"] > 0 and t["fired"] == 0,
    "fired > 0":                         lambda t: t["fired"] > 0,
}

TUPLE_FIELDS = ("enabled", "declared", "errors", "consulted", "fired")


def status_of(t: dict) -> str:
    """First matching row in precedence order; every tuple maps to exactly one status."""
    for row in STATE_TABLE:
        if CONDITIONS[row["condition"]](t):
            return row["status"]
    raise ValueError(f"no status row matches {t} — the table has a gap")


# ---- the report gate (Part A-1's three resolutions + INV-1/INV-8) ------------------------

def validate_report(report: dict, declaration: set[str]) -> list[str]:
    """Refusals, or [] — a refused report is still RETURNED (its rows are the evidence for the
    refusal); the caller must not compute anything from a refused report."""
    problems = []
    snap = report.get("snapshot") or {}
    for k in ("snapshot_id", "process_started", "window_start", "window_end", "enabled"):
        if k not in snap:
            problems.append(f"snapshot: missing {k}")
    rows = report.get("rows")
    if not isinstance(rows, list):
        return problems + ["rows: not a list"]
    seen = set()
    for i, r in enumerate(rows):
        if type(r.get("id")) is not str or not r["id"]:
            problems.append(f"row {i}: id missing"); continue
        if r["id"] in seen:
            problems.append(f"row {i}: duplicate id {r['id']!r}")
        seen.add(r["id"])
        # STRUCTURAL refusals come BEFORE status and do not depend on `enabled` (round-3 A5): an
        # undeclared reporter is refused whether or not measurement was on — the state table orders
        # STATUSES, it does not switch reconciliation off.
        if r["id"] not in declaration:
            problems.append(f"row {i}: UNDECLARED id {r['id']!r} — the row is emitted AND the report refuses (INV-1), measurement on or off")
        t = {"enabled": snap.get("enabled"), "declared": r["id"] in declaration,
             "errors": r.get("errors"), "consulted": r.get("consulted"), "fired": r.get("fired")}
        if t["enabled"] is False:
            # DISABLED: counts are OMITTED rather than reported as zero
            if r.get("consulted") is not None or r.get("fired") is not None:
                problems.append(f"row {i}: DISABLED carries counts")
            t.update(errors=r.get("errors", 0) or 0, consulted=0, fired=0)
        else:
            for k in ("errors", "consulted", "fired"):
                v = r.get(k)
                if type(v) is not int:
                    problems.append(f"row {i}: {k} is not an int"); t[k] = 0
                elif v < 0:
                    problems.append(f"row {i}: negative {k} — a broken counter, not a census outcome"); t[k] = 0
            if t["fired"] > t["consulted"]:
                problems.append(f"row {i}: fired > consulted")
        expected = status_of(t)
        if r.get("status") != expected:
            problems.append(f"row {i}: status {r.get('status')!r} but the table says {expected}")
        for k in r:
            if k not in ("id", "status", "consulted", "fired", "errors"):
                problems.append(f"row {i}: field {k!r} is not an id or an integer (INV-8)")
    for d in sorted(declaration - seen):
        problems.append(f"declared id {d!r} absent from the report — a census FAILURE, not a zero (INV-1)")
    return problems


def report_rows(counters: dict[str, dict], declaration: set[str], enabled: bool) -> list[dict]:
    """Rows for every declared id AND every reporting id (an undeclared reporter is emitted so the
    refusal has its evidence)."""
    rows = []
    for cid in sorted(set(counters) | declaration):
        c = counters.get(cid, {"consulted": 0, "fired": 0, "errors": 0})
        t = {"enabled": enabled, "declared": cid in declaration, **c}
        st = status_of(t)
        rows.append({"id": cid, "status": st} if st == "DISABLED"
                    else {"id": cid, "status": st, "consulted": c["consulted"], "fired": c["fired"], "errors": c["errors"]})
    return rows


# ---- the trace diff (Part A-2: the compared fields, and no others) ------------------------

TRACE_FIELDS = ("seq", "site_id", "decision")


def trace_key(trace: list[dict]) -> list[tuple]:
    """Project a trace onto exactly the compared fields; a record carrying anything else refuses,
    so wall-clock, counter values and content cannot leak into the comparison.

    THE BOUND (round-3): equal keys establish BRANCH-SEQUENCE EQUIVALENCE under frozen replay inputs
    and execution conditions — not that behaviour is unchanged. Returned results and state changes
    are checked separately before any broader claim."""
    out = []
    for rec in trace:
        extra = set(rec) - set(TRACE_FIELDS)
        if extra or set(TRACE_FIELDS) - set(rec):
            raise ValueError(f"trace record fields {sorted(rec)} != {TRACE_FIELDS}")
        out.append(tuple(rec[f] for f in TRACE_FIELDS))
    return out


def three_arm_diff(healthy: list[dict], failing: list[dict], uninstrumented: list[dict]) -> dict:
    keys = {"healthy": trace_key(healthy), "failing": trace_key(failing), "uninstrumented": trace_key(uninstrumented)}
    ref = keys["uninstrumented"]
    return {"identical": all(k == ref for k in keys.values()),
            "first_divergence": next(((arm, i) for arm, k in keys.items() for i, (a, b) in enumerate(zip(k, ref)) if a != b), None),
            "lengths": {a: len(k) for a, k in keys.items()}}


if __name__ == "__main__":
    print("STATE TABLE (parsed from the spec):")
    for r in STATE_TABLE:
        print(f"  {r['precedence']}  {r['status']:12s} {r['condition']}")
    decl = {"gate.answer.unverified-only", "ingest.quarantine.third-party", "graph.supersede.authority", "lifecycle.forget.scope"}
    counters = {"gate.answer.unverified-only": {"consulted": 212, "fired": 37, "errors": 0},
                "ingest.quarantine.third-party": {"consulted": 0, "fired": 0, "errors": 0},
                "graph.supersede.authority": {"consulted": 3744, "fired": 0, "errors": 0},
                "lifecycle.forget.scope": {"consulted": 5, "fired": 0, "errors": 5}}
    rows = report_rows(counters, decl, enabled=True)
    report = {"snapshot": {"snapshot_id": "s1", "process_started": "2026-09-18T00:00:00Z", "window_start": "2026-09-18T01:00:00Z",
                           "window_end": "2026-09-18T01:00:00.004Z", "enabled": True}, "rows": rows}
    print(json.dumps(report, indent=1)); print("refusals:", validate_report(report, decl))
