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
import os
import pathlib
import re
import sys

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


# FROZEN at round 5 (2026-09-18): the reviewer ACCEPTED 0042 v7 AT THE DESIGN LEVEL on this surface —
# in the verdict's words, "both specifications are accepted at the design level and may proceed to implementation." Frozen scope: "INV-1, INV-2, INV-2b–2d, INV-7, INV-8". The state table below is PARSED from
# Part A-1 (the single authority); its six statuses and their precedence are part of that surface.
# THE GOVERNING RULE FORWARD, quoted from the banked verdict, never paraphrased: "require runtime checks at real product sites once implemented, alongside the three-arm decision-trace comparison."
# Editing the parser, the CONDITIONS map or the status set is reopening design review, not a constant edit.
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

def validate_report(report: dict, declaration: set[str], site_modules: dict | None = None, loaded_modules=None) -> list[str]:
    """Refusals, or [] — a refused report is still RETURNED (its rows are the evidence for the refusal); the caller
    must not compute anything from a refused report.

    THIS FUNCTION ANSWERS ONE QUESTION: is anything WRONG with this report? Its companion `insufficiency` answers
    the other: is there anything this report CANNOT SPEAK FOR (a row whose measurement failed, a declared site
    whose module the reporting process never loaded)? The two are separate because the answers call for different
    actions — a refusal means the report is not evidence, an insufficiency means it is evidence about less than the
    whole declaration. AN EVIDENCE RUN ASSERTS BOTH EMPTY; that pair, and only that pair, is the complete claim.
    The one exception routed here is VALIDATION INCOMPLETE, which is a refusal about THIS CALL rather than about
    the report: without the scan's map this function cannot look for a missing registration at all."""
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
            if t["fired"] > t["consulted"] and not t["errors"]:
                # round 6, R6-1(iii): on a row whose measurement FAILED (errors > 0, UNMEASURED by the table's
                # precedence) the counts are not a census outcome, so their arithmetic is not refused here —
                # INV-2's isolation: one failed measurement never invalidates the report's other rows. A report
                # carrying such rows is still refused as EVIDENCE by `insufficiency()` below.
                problems.append(f"row {i}: fired > consulted")
        expected = status_of(t)
        if r.get("status") != expected:
            problems.append(f"row {i}: status {r.get('status')!r} but the table says {expected}")
        for k in r:
            if k not in ("id", "status", "consulted", "fired", "errors"):
                problems.append(f"row {i}: field {k!r} is not an id or an integer (INV-8)")
    for d in sorted(declaration - seen):
        problems.append(f"declared id {d!r} absent from the report — a census FAILURE, not a zero (INV-1)")
    # round 6, R6-3: a declared id that never REGISTERED must not read as a valid UNREACHED zero. The report
    # carries what registered (names only) and the caller supplies which product modules were loaded (observed
    # by `loaded_product_modules` below — specs/0031 keeps the module registry out of src); given the scan's id
    # -> module map, a declared id whose module is LOADED but which is not registered is a MISSING REGISTRATION (refused,
    # named); a declared id whose module is NOT loaded is OUT OF REACH (listed by name, never silently a zero);
    # and a REGISTERED id whose scan module is not loaded contradicts the scan itself (refused: the scan is wrong).
    # ROUND 7, F1: a check whose SCOPE depends on an argument must report that scope IN ITS RESULT, and the
    # narrowed case must surface in THE CHANNEL THE CALLER ALREADY READS (research's sentence; the class's third
    # appearance in this spec). The reconciliation stays OPTIONAL — the module map is an observation of a RUNNING
    # interpreter, and a reviewer validating the shipped report in a throwaway, without importing the product,
    # CANNOT supply one; mandatory would make the shipped artifact unvalidatable by the person the package exists
    # for, which is how the reviewer found F1 in the first place. So the omission is a REFUSAL rather than a
    # silence: `[]` continues to mean "validated, completely", `if problems:` is already correct at every call
    # site, and no caller has to be updated to stop reading an incomplete validation as a clean one.
    registered = snap.get("registered")
    if site_modules is None or loaded_modules is None:
        missing = " and ".join(n for n, v in (("site_modules", site_modules), ("loaded_modules", loaded_modules)) if v is None)
        problems.append(
            f"VALIDATION INCOMPLETE: registry reconciliation not performed (no {missing} supplied) — a declared, "
            f"loaded, unregistered site cannot be refused from this call, and no site can be reported out of reach. "
            f"Supply the scan's id -> module map and this process's loaded product modules "
            f"(`installed_sites.scan` and `census_table.loaded_product_modules`) for a COMPLETE validation.")
    if site_modules is not None:
        if not isinstance(registered, list):
            problems.append("snapshot: `registered` is required to reconcile the registry against the scan (R6-3)")
        elif loaded_modules is None:
            pass                      # already reported as INCOMPLETE above, in the caller's own channel
        else:
            reg, ld = set(registered), set(loaded_modules)
            for d in sorted(declaration):
                mod = site_modules.get(d)
                if mod is None:
                    problems.append(f"declared id {d!r} is not in the scan — INSTALLED does not cover the declaration")
                elif d in reg and mod not in ld:
                    problems.append(f"registered id {d!r} is scanned in {mod!r}, which is not loaded — the scan is wrong (R6-3/R6-4)")
                elif d not in reg and mod in ld:
                    problems.append(f"declared id {d!r}: its module {mod!r} is LOADED and it never registered — a missing registration, not an unused site (R6-3)")
            # ROUND 7, F1's second half, placed by research's STAGE 1 read: the out-of-reach sites are named — but
            # in `insufficiency`, NOT here. "The report cannot speak for this id" is exactly what an UNMEASURED row
            # means, this file already routes that to `insufficiency`, and routing the identical category to the
            # REFUSAL channel would have made one channel carry two kinds (the tell: every consumer had to filter
            # the prefix out before asserting, and one of them computed from a report this docstring says must not
            # be computed from). A reviewer with a partial import keeps the rows that WERE reached, which are sound.
    return problems


def out_of_reach(declaration: set[str], site_modules: dict, loaded_modules) -> list[str]:
    """The declared ids whose scan module was NOT loaded in the reporting process — identified by name (R6-3)
    rather than counted as UNREACHED zeros. The packaged evidence run asserts this list EMPTY after importing
    every product module; a non-empty list in any run names exactly what the run could not see."""
    loaded = set(loaded_modules)
    return sorted(d for d in declaration if site_modules.get(d) is not None and site_modules[d] not in loaded)


def loaded_product_modules() -> tuple[str, ...]:
    """The product modules loaded in THIS process, as paths relative to the package (`store/sqlite.py`): the
    observation R6-3 needs beside the registry (a declared id whose module is loaded but never registered is a
    missing registration; one whose module was never imported is out of reach, named). It lives in the
    evidence layer, not in `veracium.census`: specs/0031's connection census refuses `sys.modules` in any form
    and `vars()` with an argument inside src (the capability-escape analysis, rounds 11 and 13), and the
    product has no other view of the interpreter's module registry. Names only."""
    import sys as _sys, veracium as _pkg
    root = os.path.dirname(os.path.abspath(_pkg.__file__))
    out = []
    for name, mod in list(_sys.modules.items()):       # every key: the FILE decides (research's mutant 3, round 7 —
        f = getattr(mod, "__file__", None)             # a name test could only produce a false "not loaded", which
        if not f:                                      # downgrades an R6-3 refusal to a benign out-of-reach listing)
            continue
        f = os.path.abspath(f)
        if f.startswith(root + os.sep):
            out.append(os.path.relpath(f, root).replace(os.sep, "/"))
    return tuple(sorted(set(out)))


def insufficiency(report: dict, declaration: set[str] | None = None,
                  site_modules: dict | None = None, loaded_modules=None) -> list[str]:
    """Everything this report CANNOT SPEAK FOR, one entry per id. A report can be structurally VALID and
    evidentially INSUFFICIENT (research, round 6), and there are two ways:

      UNMEASURED  — the row's own measurement failed, so the census did not fully run for it (round 6).
      OUT OF REACH — the declared site's module was never loaded in the reporting process, so nothing could have
                     been observed for it (round 7, F1's second half; needs the scan's map and the loaded modules,
                     which the EVIDENCE layer observes — specs/0031 keeps the module registry out of src).

    Both mean the same thing about the claim "every declared site was exercised": it is not established for these
    ids. `validate_report` tolerates both (INV-2's isolation) and answers the other question — is anything WRONG.
    An evidence run asserts BOTH functions empty before it claims anything; that pair is the complete claim.

    ONE ENTRY PER ID, never a joined sentence with a count in it: a caller that must parse prose to learn which
    ids are affected cannot act on them, and a changed set with an unchanged count is invisible (the shape that
    let 143-for-157 decay for four rounds)."""
    out = []
    rows = report.get("rows") or []
    kinds = report.get("snapshot", {}).get("measurement_failures") or {}
    for r in rows:
        if isinstance(r, dict) and r.get("status") == "UNMEASURED":
            out.append(f"UNMEASURED: {r['id']} — its own measurement failed ({kinds.get(r['id'], {})}); the census "
                       f"did not fully run for it")
    absent = [n for n, v in (("declaration", declaration), ("site_modules", site_modules),
                             ("loaded_modules", loaded_modules)) if v is None]
    if absent:
        # ROUND 7, research's stage-1 BLOCKING 3, and it is F1's own shape TWO FUNCTIONS OVER, in the code written
        # to fix F1: a check whose scope depends on an argument, returning a CLEAN result when the argument is
        # absent, in the channel the caller already reads. Moving reach into this function made `[]` mean "this
        # report can speak for everything" — a stronger claim than it carried before — so the one-argument form
        # would have made that claim without assessing reach at all. The arguments stay optional for F1's reason
        # (a reviewer holding a shipped report has no live interpreter), so the absence is REPORTED, as there.
        out.append(f"INSUFFICIENCY INCOMPLETE: reach not assessed (no {' and '.join(absent)} supplied) — a declared "
                   f"site whose module was never loaded in the reporting process cannot be reported from this call. "
                   f"Supply the declaration, the scan's id -> module map and `loaded_product_modules()`.")
    else:
        for d in out_of_reach(declaration, site_modules, loaded_modules):
            out.append(f"OUT OF REACH: {d} — scanned in {site_modules[d]!r}, which was NOT loaded in the reporting "
                       f"process, so nothing could have been observed for it (not a defect in the site)")
    return out


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
