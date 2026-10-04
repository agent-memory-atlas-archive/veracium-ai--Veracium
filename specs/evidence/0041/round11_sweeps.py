#!/usr/bin/env python3
"""0041 round 11 — the SWEEPS: each round-11 verdict finding treated as a sample of its class, measured at the pin.

Pin `04581ec4c9dc65bf09cfa53a796d48d9ec307fc9`, before any fix (the companion of `round11_reproductions.py`). The
criteria were agreed with research before anything was measured (coordination ledger, 2026-10-04):
  A  (R11-01) PRODUCER ⊄ VALIDATOR: for every field set the REAL writer emits, the exported notice must parse and APPLY
     at a destination, in both modes, and the destination's RE-EXPORT (a second producer) must apply at a third store.
     The cells are GENERATED: the product of writer-reachable carrier states for each kind, plus every redactable
     record of the frozen pre-restriction store. FOUND = emitted fields outside carrier_paths(kind), or not re-applied.
  B  (R11-02) a decision taken from the LIVE record before every carrier its outcome speaks for is read. FOUND = the
     record's live carriers are empty while one side carrier still holds content, and redaction refuses or leaves it.
     One cell per side carrier the treatment covers, and the import path's application.
  C  (R11-03) a predicate over `redactions` that treats NATIVE and WITNESSED rows of one canonical source identity
     differently where the contract covers both. The candidates are DERIVED: every SQL literal in store/ naming a
     source column or `source_body`; each is classified, and the comparison executed both ways.
Classes: FOUND (the defect is present) · HOLDS (safe, measured with the same instrument) · OBSERVED (no defect claimed).
The exit status is 0 when every row measured the class it states.
Run from the repository root (or an export): python specs/evidence/0041/round11_sweeps.py
"""
import ast
import importlib.util
import itertools
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from veracium import redaction as R                                            # noqa: E402
from veracium.portability import export_memory, import_memory                  # noqa: E402
from veracium.schema import Disclosure, Edge, Episode, QUARANTINE_RELATION      # noqa: E402

_spec = importlib.util.spec_from_file_location("tt41_r11s", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r11s"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-SWEEP-R11"
ROWS = []


def section(name, criterion):
    print(f"\n=== SWEEP {name}\n    criterion: {criterion}")


def row(rid, expect, measured_class, detail):
    ok = expect == measured_class
    print(f"  [{rid}] expect {expect:8s} measured {measured_class:8s} {'ok' if ok else 'MISMATCH'} — {detail}")
    ROWS.append((rid, ok))


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def lines(p):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def write_lines(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def head(recs):
    return [r for r in recs if r.get("kind") == "veracium-export"]


def notices(recs):
    return [r for r in recs if r.get("record") == "redaction"]


def attempt(fn):
    try:
        return "ok", fn()
    except Exception as e:
        return "refused", f"{type(e).__name__}: {str(e)[:300]}"


def carries(st, kind, tid, text=SECRET):
    tbl = "edges" if kind == "edge" else "episodes"
    r = st._conn.execute(f"SELECT json FROM {tbl} WHERE id=?", (tid,)).fetchone()
    return None if r is None else (text in r[0])


def round_trip(d, src_store, user, kind, tid, recs_filter=None):
    """source export → a destination holding nothing (both modes) → the destination's re-export → a third store.
    Returns (emitted fields, outcome string, ok)."""
    p = d / "src.jsonl"
    export_memory(src_store, user, p)
    recs = lines(p)
    if recs_filter:
        recs = recs_filter(recs)
        p = write_lines(d / "iso.jsonl", recs)
    (n,) = [x for x in notices(recs) if x["target_id"] == tid]
    outs = []
    for restore in (False, True):
        dst = tt._mem(d, f"dst-{int(restore)}.db")
        k, got = attempt(lambda: import_memory(dst.store, p, restore=restore))
        if k != "ok":
            return n["fields"], f"restore={restore} import refused: {got[:160]}", False
        if not dst.store._attested_fields(user, kind, tid):
            return n["fields"], f"restore={restore}: imported but NOT attested at the destination", False
        relay = d / f"relay-{int(restore)}.jsonl"
        export_memory(dst.store, user, relay)
        third = tt._mem(d, f"third-{int(restore)}.db")
        k, got = attempt(lambda: import_memory(third.store, relay, restore=restore))
        if k != "ok":
            return n["fields"], f"restore={restore} RELAY refused: {got[:160]}", False
        outs.append(restore)
    return n["fields"], "applied at the destination and at the relay's third store, both modes", True


# ===================================================================================================== SWEEP A
section("A — producer ⊄ validator, over a GENERATED field-set matrix (R11-01)",
        "for every writer-reachable carrier state, the notice the real redaction emits must parse and apply at a "
        "destination in both modes, and the destination's re-export must apply at a third store")
DOMAIN = {"edge": R.carrier_paths("edge"), "episode": R.carrier_paths("episode")}
EDGE_DIMS = {
    "relation": ("lives_at", QUARANTINE_RELATION),      # the writer pairs the quarantine relation with QUARANTINED
    "note": (None, "a note " + SECRET),
    "original_relation": (None, "lived_at"),
    "invalidation_reason": (None, "superseded"),
    "confirm": (False, True),
}
found_a, holds_a = [], []
for combo in itertools.product(*EDGE_DIMS.values()):
    cell = dict(zip(EDGE_DIMS, combo))
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        m = tt._mem(d, "m.db")
        disc = Disclosure.QUARANTINED if cell["relation"] == QUARANTINE_RELATION else Disclosure.MENTIONABLE
        kw = {k: v for k, v in (("note", cell["note"]), ("original_relation", cell["original_relation"])) if v is not None}
        e = Edge(id="t", user_id=U, subject="user", relation=cell["relation"], object=SECRET,
                 provenance=tt._prov(disclosure=disc), **kw)
        k, _ = attempt(lambda: m.store.add_edge(e))
        if k != "ok":
            continue                                         # not writer-reachable: not a cell
        if cell["invalidation_reason"]:
            import datetime as _dt
            m.store.invalidate_edge("t", _dt.datetime(2026, 10, 1, tzinfo=_dt.timezone.utc), cell["invalidation_reason"])
        if cell["confirm"] and not cell["invalidation_reason"] and cell["relation"] != QUARANTINE_RELATION:
            m.confirm(U, "t")
        m.redact(U, edge_id="t", reason="subject_request")
        fields, outcome, ok = round_trip(d, m.store, U, "edge", "t")
        bad = sorted(set(fields) - DOMAIN["edge"])
        (found_a if (bad or not ok) else holds_a).append((cell, fields, bad, outcome))
by_cause = {}
for cell, fields, bad, outcome in found_a:
    by_cause.setdefault((tuple(bad), outcome.split(":")[0]), []).append(cell)
print(f"    edge cells generated and writer-reachable: {len(found_a) + len(holds_a)}; FOUND {len(found_a)}, HOLDS {len(holds_a)}")
for (bad, cause), cells in sorted(by_cause.items()):
    rel = sorted({c["relation"] for c in cells})
    row(f"A1 edge {list(bad)} ({len(cells)} cells)", "FOUND", "FOUND",
        f"emitted outside the domain: {list(bad)}; {cause}; relation in every FOUND cell: {rel}")
row(f"A1 edge, the other cells ({len(holds_a)})", "HOLDS", "HOLDS" if holds_a and all(
    c["relation"] != QUARANTINE_RELATION for c, *_ in holds_a) else "FOUND",
    "every cell WITHOUT the quarantine relation round-trips through the destination AND the relay, both modes")

EP_DIMS = {"summary": ("we discussed " + SECRET,), "retired_reason": (None, "superseded")}
ep_found = []
for combo in itertools.product(*EP_DIMS.values()):
    cell = dict(zip(EP_DIMS, combo))
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        m = tt._mem(d, "m.db")
        m.store.add_episode(Episode(id="t", user_id=U, date="2026-10-01", summary=cell["summary"],
                                    retired_reason=cell["retired_reason"], provenance=tt._prov()))
        m.redact(U, episode_id="t", reason="subject_request")
        fields, outcome, ok = round_trip(d, m.store, U, "episode", "t")
        if set(fields) - DOMAIN["episode"] or not ok:
            ep_found.append((cell, fields, outcome))
row("A2 episode cells", "HOLDS", "HOLDS" if not ep_found else "FOUND",
    f"{len(list(itertools.product(*EP_DIMS.values())))} writer-reachable episode states; failures: {ep_found or 'none'}")

frozen_found, frozen_n = [], 0
rows = tt._frozen_rows()
for name, rid in sorted(rows.items()):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        m = tt._frozen_memory(d)
        kind = "edge" if rid in {e.id for e in m.store.edges(U, active_only=False, include_quarantined=True)} else "episode"
        k, _ = attempt(lambda: m.redact(U, **({"edge_id": rid} if kind == "edge" else {"episode_id": rid}),
                                        reason="subject_request"))
        if k != "ok":
            continue
        frozen_n += 1
        keep = lambda recs, rid=rid: head(recs) + [x for x in recs if x.get("id") == rid and x.get("record") in ("edge", "episode")] \
            + [x for x in notices(recs) if x["target_id"] == rid]
        fields, outcome, ok = round_trip(d, m.store, U, kind, rid, keep)
        if set(fields) - DOMAIN[kind] or not ok:
            frozen_found.append((name, fields, outcome))
row(f"A3 frozen records ({frozen_n} redactable)", "FOUND", "FOUND" if frozen_found else "HOLDS",
    f"the frozen shapes whose isolated record + notice do not round-trip: "
    f"{[(n, sorted(set(f) - DOMAIN['edge'] - DOMAIN['episode'])) for n, f, _ in frozen_found]}")

# ===================================================================================================== SWEEP B
section("B — a decision from the LIVE record before every carrier it speaks for (R11-02)",
        "the live record's own carriers empty, ONE side carrier still holding content: redaction must treat it")


def emptied_edge(d, prep):
    m = tt._mem(d, "m.db")
    m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    prep(m)
    m.store.add_edge(Edge(id="t", user_id=U, subject="", relation="", object="", provenance=tt._prov()))
    return m


CARRIERS = {
    "edge_event.state (the journal)": lambda m: None,
    "confirmations.request_digest": lambda m: m.confirm(U, "t"),
}
for name, prep in CARRIERS.items():
    with tempfile.TemporaryDirectory() as d:
        m = emptied_edge(pathlib.Path(d), prep)
        k, got = attempt(lambda: m.redact(U, edge_id="t", reason="subject_request"))
        js = [s for (s,) in m.store._conn.execute("SELECT state FROM edge_event WHERE edge_id='t'")]
        row(f"B1 {name}", "FOUND", "FOUND" if k == "refused" and "nothing to redact" in got else "HOLDS",
            f"redact → {k}; journal states still carrying content: {sum(SECRET in (s or '') for s in js)}")
with tempfile.TemporaryDirectory() as d:                    # the ledger: a native absorption, the survivor then emptied
    from veracium import graph as _graph
    from veracium.compile import DEFAULT_RELATIONS
    d = pathlib.Path(d)
    m = tt._mem(d, "m.db")
    m.store.add_edge(Edge(id="e-prior", user_id=U, subject="user", relation="lives_in", object="Berlin",
                          provenance=tt._prov(source_id="src-a", evidence_ref="ev-a")))
    _graph.apply_supersession(m.store, Edge(id="t", user_id=U, subject="user", relation="lives_in", object="Berlin Mitte",
                                            provenance=tt._prov(source_id="src-a", evidence_ref="ev-b")), DEFAULT_RELATIONS)
    led = m.store._conn.execute("SELECT COUNT(*) FROM contribution_ledger WHERE survivor_id='t' AND identity_digest IS NOT NULL").fetchone()[0]
    assert led, "the absorption built no digest-bearing ledger row — this cell would measure nothing"
    m.store.add_edge(Edge(id="t", user_id=U, subject="", relation="", object="",
                          provenance=tt._prov(source_id="src-a", evidence_ref="ev-b")))
    k, got = attempt(lambda: m.redact(U, edge_id="t", reason="subject_request"))
    led2 = m.store._conn.execute("SELECT COUNT(*) FROM contribution_ledger WHERE survivor_id='t' AND identity_digest IS NOT NULL").fetchone()[0]
    row("B2 contribution_ledger digests (a native absorption's survivor, then emptied)", "FOUND",
        "FOUND" if k == "refused" and "nothing to redact" in got and led2 else "HOLDS",
        f"redact → {k}; digest-bearing ledger rows {led} before, {led2} after")
row("B2b supersession_refusals.relation, edge_embedding, source_revocations.reason", "OBSERVED", "OBSERVED",
    "NOT MEASURED here (each needs its own producing path: a refused supersession, an embedder, a source revocation); "
    "the decision reads none of them, so the same refusal is expected — the fix's cells cover them")
with tempfile.TemporaryDirectory() as d:                    # the import path: an applied notice carries a hint
    d = pathlib.Path(d)
    src = tt._mem(d, "src.db")
    src.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    src.redact(U, edge_id="t", reason="subject_request")
    p = d / "x.jsonl"
    export_memory(src.store, U, p)
    (d / "dst").mkdir()
    dst = emptied_edge(d / "dst", lambda m: None)
    k, got = attempt(lambda: import_memory(dst.store, write_lines(d / "n.jsonl", head(lines(p)) + notices(lines(p)))))
    js = [s for (s,) in dst.store._conn.execute("SELECT state FROM edge_event WHERE edge_id='t'")]
    row("B3 the import path (an applied notice on an emptied record)", "HOLDS",
        "HOLDS" if k == "ok" and not any(SECRET in (s or "") for s in js) else "FOUND",
        f"the notice's fields keep the union non-empty, so the treatment runs: import → {k}; journal carrying "
        f"content after: {sum(SECRET in (s or '') for s in js)}")

# ===================================================================================================== SWEEP C
section("C — predicates over `redactions` that treat NATIVE and WITNESSED rows of one source identity differently (R11-03)",
        "candidates DERIVED: every SQL literal in store/sqlite.py naming source_body or a source_* column")
src_text = (ROOT / "src" / "veracium" / "store" / "sqlite.py").read_text()
tree = ast.parse(src_text)
funcs = [(n.lineno, n.end_lineno, n.name) for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
cands = sorted({min((f for f in funcs if f[0] <= n.lineno <= f[1]), key=lambda f: f[1] - f[0])[2]
                for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and re.search(r"source_body|source_origin|source_user|source_event_ref", n.value) and "SELECT" in n.value})
print(f"    functions holding a SELECT over a source column, derived: {cands}")


def own_store(d):
    m = tt._mem(d, "m.db")
    m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    m.redact(U, edge_id="t", reason="subject_request")
    p = d / "own.jsonl"
    export_memory(m.store, U, p)
    return m, lines(p)


with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    m, recs = own_store(d)
    k, got = attempt(lambda: import_memory(m.store, write_lines(d / "c.jsonl", head(recs) + [dict(notices(recs)[0], reason="operator_policy")])))
    row("C1 commit_outcome_import_plan: the body comparison vs a NATIVE row", "FOUND", "FOUND" if k == "ok" else "HOLDS",
        f"a contradictory notice of the store's own event → {k}")
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    m, recs = own_store(d)
    other = tt._mem(d, "other.db")
    import_memory(other.store, write_lines(d / "n.jsonl", head(recs) + notices(recs)))
    relay = d / "relay.jsonl"
    export_memory(other.store, U, relay)
    rows_before = m.store._conn.execute("SELECT COUNT(*) FROM redactions WHERE target_id='t'").fetchone()[0]
    k, got = attempt(lambda: import_memory(m.store, relay))
    rows_after = m.store._conn.execute("SELECT COUNT(*) FROM redactions WHERE target_id='t'").fetchone()[0]
    row("C2 the store's OWN event relayed back honestly (equal body)", "FOUND",
        "FOUND" if rows_after > rows_before else "HOLDS",
        f"→ {k}; attestation rows for the target {rows_before} → {rows_after} (a second row for one source event is the "
        f"native/witnessed split: the native row is not found under its own source identity)")
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    m, recs = own_store(d)
    dup = head(recs) + notices(recs) + [dict(notices(recs)[0], reason="operator_policy")]
    k, got = attempt(lambda: import_memory(tt._mem(d, "f.db").store, write_lines(d / "dup.jsonl", dup)))
    row("C3 the in-file dedupe (portability): two bodies under one identity in ONE file", "HOLDS",
        "HOLDS" if k == "refused" else "FOUND", f"→ {k} (the parser keys on the triple, native or not)")
row("C4 the arrival query and the doctor's standing test (source_origin IS NOT NULL AND event_ref IS NULL)", "OBSERVED",
    "OBSERVED", "witnessed-only BY DEFINITION: a native row always has its event, so it is never standing — the "
    "predicate's restriction is the contract's, not a split")
row("C5 the receipt and export (source_origin decides local vs witnessed)", "OBSERVED", "OBSERVED",
    "native vs witnessed DECIDES provenance here, as R10-04's fix requires; the export synthesises a native row's "
    "identity from local facts — which is the representation C1/C2's comparison does not consult")

# ---------------------------------------------------------------- summary
print("\n" + "-" * 100)
bad = [r for r, ok in ROWS if not ok]
print(f"  {len(ROWS)} rows; {len(ROWS) - len(bad)} measured the class they state; mismatches: {bad or 'none'}")
sys.exit(0 if not bad else 1)
