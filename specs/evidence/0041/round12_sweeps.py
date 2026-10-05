#!/usr/bin/env python3
"""0041 round 12 — the CLASS behind the finding and the observations, swept at the round-12 pin before any fix.
Every row states the class it expects BEFORE measuring (FOUND / HOLDS / OBSERVED) and prints the measurement beside
it; a row measuring otherwise is printed as a MISMATCH, never adjusted.

  A (R12-01, N12-01) THE IMPORT-STAGE MATRIX the verdict asks for: which importer stages can refuse or discard an
    arriving record BEFORE notice application and depend on the DESTINATION (derived from the importer's source), then
    a GENERATED matrix — record kind × destination state × mode — each cell a real redaction exported and imported,
    checked for: import succeeds, the held target treated and attested under its ACTUAL id, no redaction row naming an
    id that is no record
  B (N12-02) side carriers SHARED between records, whose updater reports only rows IT changed: an already-treated
    shared carrier never enters the attestation union
  C (the evidence-scope note) every round-12 claim that a cell's destination HELD an earlier record, checked against
    the cell's own code

    PYTHONPATH=src python specs/evidence/0041/round12_sweeps.py
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import pathlib
import re
import sys
import tempfile
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


_spec = importlib.util.spec_from_file_location("tt41_r12sw", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r12sw"] = tt
_spec.loader.exec_module(tt)

from veracium import portability as P                          # noqa: E402
from veracium.lifecycle import consolidate                     # noqa: E402
from veracium.portability import export_memory, import_memory  # noqa: E402
from veracium.schema import Edge, Episode                      # noqa: E402
from veracium.store import sqlite as SQ                        # noqa: E402

U = "u"
SECRET = "SECRET-R12-SWEEP"
ROWS: list[tuple[str, str, str, str]] = []


def row(name, expect, measured, detail):
    ROWS.append((name, expect, measured, detail))
    print(f"  [{name}] expect {expect:8s} measured {measured:8s} {'ok' if expect == measured else 'MISMATCH'} — {detail}")


def lines(p):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def write(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


# ---- A ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP A — importer stages before notice application, and the travelling-notice matrix (R12-01, N12-01)")
src_text = inspect.getsource(P.import_memory)
dest_reads = [n for n in ("store.episodes(", "store.edges(") if n in src_text.split("_preflight_and_commit(")[0]]
refusals_before = len(re.findall(r"_SITE_IMPORT_RECORD\.fire", src_text.split("_preflight_and_commit(")[0]))
discards = len(re.findall(r"skip_ids\.add\(", src_text))
row("A1 importer stages BEFORE the commit that read the DESTINATION", "FOUND", "FOUND" if dest_reads else "HOLDS",
    f"{dest_reads} read before _preflight_and_commit; {refusals_before} record refusals and {discards} discard site(s) precede "
    "it — of those, the indexed-output collision check is the one keyed on what the destination holds")


def build(kind, m):
    """One record of `kind` in source `m`, through the real writers; returns its id."""
    if kind == "edge":
        m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
        return "t"
    if kind == "interaction":
        m.store.add_episode(Episode(id="t", user_id=U, date="2026-10-01", summary=f"we discussed {SECRET}", provenance=tt._prov()))
        return "t"
    if kind == "outcome":
        m.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="prefers", object=SECRET, provenance=tt._prov()))
        m.record_outcome(U, "e-1", outcome="confirmed", actor="user", evidence_ref="ev-outcome")
        return [e.id for e in m.store.episodes(U) if e.kind == "outcome"][0]
    if kind == "consolidation-output":
        for i in range(8):
            m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                        provenance=tt._prov(source_id="src-one", evidence_ref=f"ev-{i}")))
        consolidate(m.store, lambda p, system=None, role=None: json.dumps(
            {"records": [{"date": "2026-01-01", "summary": "the week " + SECRET}]}), U, m.config,
            now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        return [e.id for e in m.store.episodes(U) if e.lineage][0]
    raise ValueError(kind)


def redact(m, kind, tid):
    if kind == "edge":
        m.redact(U, edge_id=tid, reason="subject_request")
    else:
        m.redact(U, episode_id=tid, reason="subject_request")


def holds_secret(st, uid, kind):
    """The REDACTED KIND's records only. (The first form scanned every edge and episode, and an outcome is built FROM
    an edge carrying the secret — a separate record its redaction correctly leaves — so every outcome cell read
    'content survives' on the instrument, not the product.)"""
    tbl = "edges" if kind == "edge" else "episodes"
    q = f"SELECT json FROM {tbl} WHERE user_id=?" + (" AND json_extract(json, '$.kind')='outcome'" if kind == "outcome" else "")
    return any(SECRET in (r[0] or "") for r in st._conn.execute(q, (uid,)))


def cell(kind, state, restore, d):
    src = tt._mem(d, "src.db"); tid = build(kind, src)
    export_memory(src.store, U, d / "before.jsonl")
    redact(src, kind, tid)
    export_memory(src.store, U, d / "after.jsonl")
    dst = tt._mem(d, "dst.db"); uid = U; kw = {"restore": restore}
    if state == "held-earlier":
        import_memory(dst.store, d / "before.jsonl", **kw)
    elif state == "already-attested":
        import_memory(dst.store, d / "after.jsonl", **kw)
    elif state == "repeated-remap":
        uid = "v"; kw["user_id"] = "v"
        import_memory(dst.store, d / "after.jsonl", **kw)
    try:
        import_memory(dst.store, d / "after.jsonl", **kw)
    except Exception as exc:
        return f"refused: {str(exc)[-90:]}"
    ids = {r[0] for r in dst.store._conn.execute("SELECT id FROM episodes WHERE user_id=? UNION SELECT id FROM edges WHERE user_id=?", (uid, uid))}
    reds = [r[0] for r in dst.store._conn.execute("SELECT target_id FROM redactions WHERE user_id=?", (uid,))]
    dangling = [t for t in reds if t not in ids]
    if holds_secret(dst.store, uid, kind):
        return "content survives"
    if dangling:
        return f"{len(dangling)} redaction row(s) naming no record"
    return "ok"


KINDS = ("edge", "interaction", "outcome", "consolidation-output")
STATES = ("absent", "held-earlier", "already-attested", "repeated-remap")
bad = []
total = 0
for kind in KINDS:
    for state in STATES:
        for restore in (False, True):
            if state == "repeated-remap" and restore:
                continue                                   # a remapping import is the default path (restore keeps ids)
            total += 1
            with tempfile.TemporaryDirectory() as d:
                got = cell(kind, state, restore, pathlib.Path(d))
            if got != "ok":
                bad.append((kind, state, restore, got))
row(f"A2 the travelling-notice matrix ({len(KINDS)} kinds × {len(STATES)} destination states × modes = {total} cells)",
    "FOUND", "FOUND" if bad else "HOLDS", f"{len(bad)} of {total} cells fail: " + "; ".join(f"{k}/{s}/restore={r}: {g}" for k, s, r, g in bad))
outside = [b for b in bad if b[0] != "consolidation-output"]
row("A3 a failing cell OUTSIDE the consolidation output", "HOLDS", "FOUND" if outside else "HOLDS",
    f"{len(outside)}: {outside}")

# the historical prose-kind episode of the frozen store, isolated with its notice (the frozen export carries other
# shapes). Its UNREDACTED form is refused at the import boundary by design — the disclosed D1 limit ("legacy-prose
# restore refuses until the records are redacted") — so a destination cannot HOLD it earlier; the row measures the
# redacted record into an ABSENT destination, and separately that the unredacted import is the named refusal.
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    m = tt._frozen_memory(d); pid = tt._frozen_rows()["prose_kind"]
    export_memory(m.store, U, d / "before.jsonl")
    m.redact(U, episode_id=pid, reason="subject_request")
    export_memory(m.store, U, d / "after.jsonl")
    keep = lambda recs: [r for r in recs if "id" not in r or r.get("id") == pid or r.get("target_id") == pid]
    write(d / "b.jsonl", keep(lines(d / "before.jsonl"))); write(d / "a.jsonl", keep(lines(d / "after.jsonl")))
    try:
        import_memory(tt._mem(d, "held.db").store, d / "b.jsonl"); d1 = "the unredacted form IMPORTED (the D1 limit did not fire)"
    except Exception as exc:
        d1 = "the unredacted form refused (D1)" if "§2d-iv" in str(exc) else f"refused otherwise: {str(exc)[-60:]}"
    dst = tt._mem(d, "dst.db")
    try:
        import_memory(dst.store, d / "a.jsonl")
        res = "ok" if dst.store._attested_fields(U, "episode", pid) else "not attested"
    except Exception as exc:
        res = f"refused: {str(exc)[-90:]}"
row("A4 the frozen store's historical prose-kind episode: redacted, into an ABSENT destination", "HOLDS",
    "HOLDS" if res == "ok" else "FOUND", f"{res}; {d1}")

# ---- B ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP B — shared side carriers whose updater reports only the rows IT changed (N12-02)")
body = inspect.getsource(SQ.SqliteStore._redact_in_txn)
appends = re.findall(r'fields\.append\("([^"]+)"\)', body)
row("B1 side-carrier paths the treatment appends", "OBSERVED", "OBSERVED", f"{len(appends)}: {appends}")
from veracium.store import revocation as RV                     # noqa: E402
rv = inspect.getsource(RV.redact_revocation_reasons)
# (the first form looked the helper up on the sqlite module, where it is only imported inside a function: it read an
# empty string and measured HOLDS. The source is the revocation module's.)
shared_and_changed_only = "identity_digest=?" in rv and "reason<>?" in rv and ".rowcount" in rv
row("B2 the revocation updater: keyed by SOURCE (shared between records), reports only rows it changed", "FOUND",
    "FOUND" if shared_and_changed_only else "HOLDS",
    "source_revocations rows are keyed by the source digest, so one row serves every record of that source; the updater "
    "returns whether IT changed a row, so a row another record's redaction already marked never enters this record's union")
others = [a for a in appends if a.split(".")[0] in ("confirmations", "supersession_refusals", "edge_embedding", "contribution_ledger")]
row("B3 the other side carriers: keyed by the record's own id (not shared)", "HOLDS",
    "HOLDS" if all(re.search(rf"{a.split('.')[0]}[^\n]*(edge_id|survivor_id|target_id|=\?)", body) for a in others) else "FOUND",
    f"{others}: each updated by the record's own id, so 'already treated' there means this record's own earlier redaction")

# ---- C ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP C — claims that a cell's destination HELD an earlier record, against the cell's code")
qsrc = (ROOT / "tests" / "test_0041_round12_quarantine.py").read_text()
tree = ast.parse(qsrc)
fns = {n.name: ast.get_source_segment(qsrc, n) for n in tree.body if isinstance(n, ast.FunctionDef)}
rt = fns.get("_round_trip", "")
fresh = "_mem(" in rt and "import_memory" in rt and not re.search(r"add_edge|import_memory\([^)]*before", rt.split("import_memory")[0].split("_mem(")[-1])
row("C1 the generated matrix's _round_trip: a FRESH destination, not one holding the earlier edge", "FOUND",
    "FOUND" if fresh else "HOLDS", "the round-12 README §1a said every matrix cell imported into a destination HOLDING the "
    "earlier edge; _round_trip builds a new store and imports the treated export into it")
named = [n for n in fns if n.startswith("test_R11_01_quarantine_redaction_export_applies_to_held_target")
         or n.startswith("test_a_destination_holding")]
held_ok = all("add_edge" in fns[n] or "before" in fns[n] or "_frozen" in fns[n] for n in named)
row("C2 the NAMED held-target cells populate the destination before the notice", "HOLDS", "HOLDS" if held_ok and named else "FOUND",
    f"{named}")

print("\n" + "-" * 100)
mism = [r for r in ROWS if r[1] != r[2]]
print(f"  {len(ROWS)} rows; {len(ROWS) - len(mism)} measured the class they state; mismatches: {[m[0] for m in mism] or 'none'}")
sys.exit(0)
