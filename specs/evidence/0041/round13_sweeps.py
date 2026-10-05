#!/usr/bin/env python3
"""0041 round 13 — the CLASS behind each finding, swept at the round-13 pin before any fix (criteria agreed with
research, widened by research's stage-1). Every row states its class BEFORE measuring (FOUND / HOLDS / OBSERVED); a
row measuring otherwise prints MISMATCH, never adjusted.

  A (R13-01) id comparisons in the import whose two sides come from DIFFERENT namespaces (arriving / held-resolved /
    remapped user / target kind / historical form / a notice's source triple vs its bound target), or where one side
    is compared BEFORE the resolution that defines it — derived from the import's own comparison expressions; and the
    honest permutation WITH both notices as the positive control
  B (R13-02) EVERY use of the marker in src, classified by CONTRACT: "the value IS the marker" (treated-value decisions)
    vs "the text CARRIES the marker" (ordinary-write reservation, unattested-marker diagnostics). A substring test
    under an IS contract is FOUND
  C (N13-01) every side table's COMPLETE target relation — every column linking a row to a record — from the DDL of a
    freshly created store (sqlite_master / PRAGMA table_info), and, per shared table, newly treated / already treated
    and shared / absent, measured through the real writers

    PYTHONPATH=src python specs/evidence/0041/round13_sweeps.py
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import pathlib
import re
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / "src" / "veracium"

_spec = importlib.util.spec_from_file_location("tt41_r13sw", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r13sw"] = tt
_spec.loader.exec_module(tt)

from veracium import graph as _graph                           # noqa: E402
from veracium import portability as P                          # noqa: E402
from veracium import redaction as R                            # noqa: E402
from veracium.schema import Edge                               # noqa: E402

U = "u"
ROWS: list[tuple[str, str, str, str]] = []


def row(name, expect, measured, detail):
    ROWS.append((name, expect, measured, detail))
    print(f"  [{name}] expect {expect:8s} measured {measured:8s} {'ok' if expect == measured else 'MISMATCH'} — {detail}")


# ---- A ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP A — id comparisons across namespaces, or before the resolution that defines a side (R13-01)")
src = inspect.getsource(P.import_memory)
tree = ast.parse(src)
NOTICE_TARGET = re.compile(r'n\[\s*"target_id"\s*\]')
cmp_sites = []
for node in ast.walk(tree):
    if isinstance(node, ast.Compare):
        text = ast.get_source_segment(src, node) or ""
        if NOTICE_TARGET.search(text):
            cmp_sites.append((node.lineno, text))
row("A1 comparisons of a notice's RAW target id inside import_memory, derived from the AST", "OBSERVED", "OBSERVED",
    f"{len(cmp_sites)}: " + "; ".join(f"line+{ln}: {t[:70]}" for ln, t in cmp_sites))
both = [t for _ln, t in cmp_sites if re.search(r'in\s*\(\s*r\["id"\]\s*,\s*hit\["id"\]\s*\)', t)]
row("A2 one comparison accepts EITHER the arriving id OR the held id — two namespaces, before every arrival is resolved",
    "FOUND", "FOUND" if both else "HOLDS", f"{len(both)} site(s): {both}")
coll = src.index("incoming_indexed")
rebind_at = src.find("rebind[n[") if "rebind[n[" in src else src.find('n["target_id"] = rebind')
row("A3 the collision decision precedes the rebind that resolves notice subjects", "FOUND",
    "FOUND" if 0 <= coll < rebind_at else "HOLDS", "the collision loop reads notices before `n['target_id'] = rebind[...]` runs")

# ---- B ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP B — every use of the marker in src, by contract (R13-02)")
IS_CONTRACT = {"held_output_redaction", "already_treated", "_treated_on_arrival", "_redact_in_txn", "treat_edge",
               "treat_episode", "revocation_reason_marked", "redact_revocation_reasons"}
sites = []
for py in sorted(SRC.rglob("*.py")):
    text = py.read_text()
    t = ast.parse(text)
    for fn in [n for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        seg = ast.get_source_segment(text, fn) or ""
        own = seg
        for inner in [n for n in ast.walk(fn) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not fn]:
            own = own.replace(ast.get_source_segment(text, inner) or "", "")
        uses = []
        if re.search(r"\bcarries_marker\(", own): uses.append("carries_marker (substring)")
        if re.search(r"\bmarker_fields\(", own): uses.append("marker_fields (substring)")
        if re.search(r"MARKER\s+in\b|\bin\s+[\w.\[\]\"']*\s*#?.*MARKER|\.find\(\s*(_redaction\.)?MARKER", own): uses.append("`in` / find (substring)")
        if re.search(r"==\s*(_redaction\.|R\.)?MARKER\b|(_redaction\.|R\.)?MARKER\s*==|!=\s*(_redaction\.)?MARKER|reason=\?", own) or "<>?" in own:
            uses.append("== / <> (exact)")
        if uses:
            sites.append((py.relative_to(SRC).as_posix(), fn.name, uses))
under_is = [(f, n, u) for f, n, u in sites if n in IS_CONTRACT and any("substring" in x for x in u) and not any("exact" in x for x in u)]
row(f"B1 marker uses in src, by function ({len(sites)} functions)", "OBSERVED", "OBSERVED",
    "; ".join(f"{f}:{n} [{', '.join(u)}]" for f, n, u in sites))
row("B2 a SUBSTRING-only test inside a function whose contract is 'the value IS the marker'", "FOUND",
    "FOUND" if under_is else "HOLDS", f"{len(under_is)}: {[(f, n) for f, n, _u in under_is]}")
mf = inspect.getsource(R.marker_fields) + inspect.getsource(R.carries_marker)
row("B3 marker_fields reaches the substring helper carries_marker", "FOUND",
    "FOUND" if "carries_marker(" in inspect.getsource(R.marker_fields) else "HOLDS", "marker_fields → carries_marker → `MARKER in value`")

# ---- C ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP C — side tables' COMPLETE target relation, from the DDL; shared rows measured (N13-01)")
# every column that names a RECORD: an `*_id` naming an edge / episode / survivor / prior / incoming / target, and an
# `*_ref` naming a contributor (the first form matched `*_id` only and missed contribution_ledger.contributor_ref —
# the narrowness that hid the second shared table)
LINK = re.compile(r"(^|_)(edge|episode|survivor|incoming|prior|target)(_[a-z]+)?_id$|^contributor_ref$|^identity_digest$")
with tempfile.TemporaryDirectory() as d:
    m = tt._mem(pathlib.Path(d), "ddl.db")
    tables = [r[0] for r in m.store._conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    links = {t: [c[1] for c in m.store._conn.execute(f"PRAGMA table_info({t})") if LINK.search(c[1])] for t in tables}
links = {t: c for t, c in links.items() if c and t not in ("edges", "episodes")}
multi = {t: c for t, c in links.items() if len([x for x in c if x != "identity_digest"]) > 1}
row("C1 side tables with their record-linking columns, from the created store's DDL", "OBSERVED", "OBSERVED",
    "; ".join(f"{t}: {c}" for t, c in sorted(links.items())))
row("C2 a side table whose row links to MORE THAN ONE record by id (shared between records)", "FOUND",
    "FOUND" if multi else "HOLDS", f"{multi}")
treated = {p.split(".")[0] for p in R.attestation_paths("edge") | R.attestation_paths("episode") if "." in p}
shared_treated = sorted(set(multi) & treated)
row("C3 of those, the ones the treatment writes (a carrier path names them)", "FOUND",
    "FOUND" if shared_treated else "HOLDS", f"{shared_treated}")


def refusal_pair(d):
    m = tt._mem(d, "m.db")
    m.store.add_edge(Edge(id="e-1", user_id=U, subject="user's sister", relation="lives_in", object="Berlin", provenance=tt._prov()))
    try:
        m.correct(U, "e-1", "Paris")
    except _graph.CorrectionRefused:
        pass
    prior, incoming = m.store._conn.execute("SELECT prior_edge_id, incoming_edge_id FROM supersession_refusals").fetchone()
    if not m.store._conn.execute("SELECT 1 FROM edges WHERE id=?", (incoming,)).fetchone():
        m.store.add_edge(Edge(id=incoming, user_id=U, subject="user's sister", relation="lives_in", object="Paris", provenance=tt._prov()))
    return m, prior, incoming


states = {}
for order in ("prior", "incoming"):
    with tempfile.TemporaryDirectory() as d:
        m, prior, incoming = refusal_pair(pathlib.Path(d))
        first, second = (prior, incoming) if order == "prior" else (incoming, prior)
        r1 = m.redact(U, edge_id=first, reason="subject_request"); r2 = m.redact(U, edge_id=second, reason="subject_request")
        states[order] = ("newly treated" if "supersession_refusals.relation" in r1.fields_cleared else "?",
                         "already treated and shared: attested" if "supersession_refusals.relation" in r2.fields_cleared
                         else "already treated and shared: OMITTED")
with tempfile.TemporaryDirectory() as d:
    m = tt._mem(pathlib.Path(d), "a.db")
    m.store.add_edge(Edge(id="lone", user_id=U, subject="user", relation="lives_in", object="Berlin", provenance=tt._prov()))
    absent = "absent: not named" if "supersession_refusals.relation" not in m.redact(U, edge_id="lone", reason="subject_request").fields_cleared else "absent: NAMED"
row("C4 supersession_refusals, both orders: newly treated / already treated and shared / absent", "FOUND",
    "FOUND" if any("OMITTED" in v[1] for v in states.values()) else "HOLDS", f"{states}; {absent}")

from veracium.compile import DEFAULT_RELATIONS                 # noqa: E402
ledger_states = {}
for order in ("survivor", "contributor"):
    with tempfile.TemporaryDirectory() as d:
        m = tt._mem(pathlib.Path(d), "l.db")
        m.store.add_edge(Edge(id="e-prior", user_id=U, subject="user", relation="lives_in", object="Berlin",
                              provenance=tt._prov(source_id="src-a", evidence_ref="ev-a")))
        _graph.apply_supersession(m.store, Edge(id="t", user_id=U, subject="user", relation="lives_in", object="Berlin Mitte",
                                                provenance=tt._prov(source_id="src-a", evidence_ref="ev-b")), DEFAULT_RELATIONS)
        rows = m.store._conn.execute("SELECT survivor_id, contributor_ref FROM contribution_ledger WHERE survivor_type='edge' "
                                     "AND contributor_type='edge' AND identity_digest IS NOT NULL").fetchall()
        two = [(s_, c_) for s_, c_ in rows if s_ != c_ and m.store._conn.execute("SELECT 1 FROM edges WHERE id=?", (c_,)).fetchone()
               and m.store._conn.execute("SELECT 1 FROM edges WHERE id=?", (s_,)).fetchone()]
        if not two:
            ledger_states[order] = f"no ledger row linking two EXISTING edges by this writer (rows {rows})"
            continue
        surv, contrib = two[0]
        first, second = (surv, contrib) if order == "survivor" else (contrib, surv)
        r1 = m.redact(U, edge_id=first, reason="subject_request"); r2 = m.redact(U, edge_id=second, reason="subject_request")
        p_ = "contribution_ledger.identity_digest"
        ledger_states[order] = (("newly treated" if p_ in r1.fields_cleared else "first: not named"),
                                ("shared, already cleared: attested" if p_ in r2.fields_cleared else "shared, already cleared: OMITTED"))
row("C5 contribution_ledger rows linking two edges (survivor, contributor), both orders", "OBSERVED", "OBSERVED",
    f"{ledger_states} — the ledger digests are CLEAR carriers. MEASURED (stage 1, research's conditional ruling): an "
    "ordinary absorption whose edges carry no source_id and an empty evidence_ref writes a linking row with BOTH digests "
    "NULL (identity_digest_of: None without source_id, 0006 I13; evidence_ref_digest: NULL iff empty, 0014 §4a), so a NULL "
    "digest is not evidence of a prior treatment — round 11's accepted CLEAR reading stands; v15.4 names the limit")

print("\n" + "-" * 100)
mism = [r for r in ROWS if r[1] != r[2]]
print(f"  {len(ROWS)} rows; {len(ROWS) - len(mism)} measured the class they state; mismatches: {[m[0] for m in mism] or 'none'}")
sys.exit(0)
