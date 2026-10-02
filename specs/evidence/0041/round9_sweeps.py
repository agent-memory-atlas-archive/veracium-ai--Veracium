#!/usr/bin/env python3
"""0041 round 9 — the SWEEPS: each verdict finding treated as a sample of its class, measured at the pin.

Pin `c05b709b80a6e817b4d45d5a265aa4d24e09594c`, before any fix (the companion of `round9_reproductions.py`, which
reproduces the eight named findings). Every row states its CRITERION, the CLASS it expects at this tree, and what
was MEASURED, and every FOUND or HOLDS row is paired with a control that shows the instrument can see the other
outcome:

  FOUND     the defect is present here (a found-in-sweep instance, or the reviewer's own instance as the control)
  HOLDS     a surface the criterion reaches and which is already safe, executed with the same instrument
  OBSERVED  measured and reported, no fix proposed in this round (named owner beside it)

The interleavings are deterministic: a hook in the first connection's read path makes a SECOND `Memory` on the same
database file redact the record in the gap. No sleeps, no threads. Everything goes through the real entry points
(`Memory`, `SqliteStore`, `lifecycle`, `compile_wiki`, `export_memory`/`import_memory`); no row is written by hand.

The exit status is 0 when EVERY row measured the class it states — at this pin. After the fixes the FOUND rows are
expected to move; this file is the pin-time record, and the fixes carry their own cells.
Run from the repository root (or an export): python specs/evidence/0041/round9_sweeps.py
"""
import ast
import datetime as dt
import importlib.util
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from veracium import Memory, redaction as R, why                                    # noqa: E402
from veracium.compile import DEFAULT_RELATIONS, compile_wiki                        # noqa: E402
from veracium.config import MemoryConfig                                             # noqa: E402
from veracium.lifecycle import consolidate                                           # noqa: E402
from veracium.portability import export_memory, import_memory                       # noqa: E402
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance, Volatility  # noqa: E402
from veracium.scope_linkage import plan_row_id                                       # noqa: E402
from veracium.store.sqlite import SqliteStore                                        # noqa: E402

_spec = importlib.util.spec_from_file_location("tt41_r9s", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r9s"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-SWEEP-4471"
ROWS = []


def section(name, criterion):
    print(f"\n=== SWEEP {name}\n    criterion: {criterion}")


def row(rid, expect, measured_class, detail):
    ok = expect == measured_class
    print(f"  [{rid}] expect {expect:8s} measured {measured_class:8s} {'ok' if ok else 'MISMATCH'} — {detail}")
    ROWS.append((rid, ok))


def prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw)
    return Provenance(**base)


def pair(d, name="s.db"):
    """Two Memory instances (two connections) on ONE database file."""
    return tt._mem(pathlib.Path(d), name), tt._mem(pathlib.Path(d), name)


def carriers(st):
    """Every place the secret survives: the json of edges/episodes, and every text column of every other table."""
    hits = []
    for tbl, in st._conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [c[1] for c in st._conn.execute(f"PRAGMA table_info('{tbl}')")]
        for r in st._conn.execute(f"SELECT * FROM '{tbl}'"):
            for c, v in zip(cols, r):
                if isinstance(v, str) and SECRET in v:
                    hits.append(f"{tbl}.{c}")
    return sorted(set(hits))


def secret_edge(st, eid="e-1", **kw):
    st.add_edge(Edge(id=eid, user_id=U, subject="user", relation=kw.pop("relation", "lives_at"), object=SECRET,
                     note=kw.pop("note", "note " + SECRET), provenance=kw.pop("provenance", prov()), **kw))


def find_edge_gap(a, b, eid="e-1"):
    """A's `_find_edge` returns its read, then B redacts the edge: the read precedes the redaction's commit."""
    real, done = a._find_edge, []

    def hooked(user_id, edge_id):
        got = real(user_id, edge_id)
        if not done:
            done.append(b.redact(U, edge_id=eid, reason="subject_request"))
        return got
    a._find_edge = hooked


def attempt(fn):
    try:
        return "returned", fn()
    except Exception as e:                              # noqa: BLE001 — the class of the outcome is the measurement
        return "refused", f"{type(e).__name__}: {str(e)[:80]}"


# ===================================================================================================== SWEEP A
section("A — a writer whose output DERIVES from records read before its write transaction",
        "every writer whose output derives from records read BEFORE its write txn (across an LLM call, an embed call "
        "or a plan/commit split), and whether it re-validates those records' attestation under the write txn. "
        "Instrument: B redacts in the gap; the secret is then searched in every carrier. (Widened from round-9 "
        "sweep A's 'attestation reads that gate a write' on research's measured consolidation instance.)")


def consolidation(redact_in_gap):
    with tempfile.TemporaryDirectory() as d:
        a, b = pair(d)
        for i in range(8):
            a.store.add_episode(Episode(id=f"ep-old-{i}", user_id=U, date=f"2026-01-0{i + 1}",
                                        summary=f"day {i} " + (SECRET if i == 3 else "ordinary"), provenance=prov()))
        seen = {}

        def llm(prompt, system=None, role=None):
            if redact_in_gap:
                seen["repeated"] = b.store.redact(U, episode_id="ep-old-3", reason="subject_request").repeated
                seen["claimed"] = "ep-old-3" in b.store._reserved_ids(U)
            return json.dumps({"records": [{"date": "2026-01-01", "summary": "echo: " + prompt}]})
        res = consolidate(a.store, llm, U, a.config, now=dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc))
        outs = [e for e in a.store.episodes(U) if e.lineage]
        return res, seen, outs, carriers(a.store)


res, seen, outs, hits = consolidation(True)
row("A1", "FOUND", "FOUND" if res["into"] == 1 and any(SECRET in o.summary for o in outs) else "HOLDS",
    f"consolidation (`_consolidate_pool` calls the LLM BEFORE the claim): redaction during the call succeeded "
    f"(repeated={seen.get('repeated')}, input claimed at that moment: {seen.get('claimed')}); then {res['consolidated']} "
    f"into {res['into']}, the output carrying the redacted text; carriers {hits}. The gap is LISTING to CLAIM — redact "
    f"already refuses a claimed input")
res, _, outs, hits = consolidation(False)
row("A1-control", "HOLDS", "HOLDS" if res["into"] == 1 else "FOUND",
    f"no redaction: {res['consolidated']} into {res['into']} — the ordinary consolidation (the content is the user's)")

for name, call in (("A2 dispute", lambda a: a.dispute(U, "e-1", reason="wrong")),
                   ("A3 record_outcome", lambda a: a.record_outcome(U, "e-1", outcome="challenged",
                                                                    evidence_ref="ctx", actor="system"))):
    with tempfile.TemporaryDirectory() as d:
        a, b = pair(d)
        secret_edge(a.store)
        find_edge_gap(a, b)
        kind, out = attempt(lambda: call(a))
        hits = carriers(a.store)
        eps = [h for h in hits if h.startswith("episodes.")]
        row(name.split()[0], "FOUND", "FOUND" if eps else "HOLDS",
            f"{name.split()[1]}: read the edge, B redacted it, then the call {kind} ({str(out)[:60]}); the episode it "
            f"wrote quotes the stale `edge.object` — carriers after the committed redaction: {hits}")

with tempfile.TemporaryDirectory() as d:
    a, _ = pair(d)
    secret_edge(a.store)
    a.redact(U, edge_id="e-1", reason="subject_request")
    n0 = a.store._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    kind, out = attempt(lambda: a.record_outcome(U, "e-1", outcome="challenged", evidence_ref="ctx", actor="system"))
    n1 = a.store._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    row("A3-norace", "FOUND", "FOUND" if kind == "refused" and n1 > n0 else "HOLDS",
        f"record_outcome on an ALREADY-redacted edge, no race: {kind} ({str(out)[:50]}) yet episodes {n0} -> {n1} — the "
        f"outcome append committed before the edge write refused (a partial write; the episode quotes the marker)")

for a_ctl in (True,):
    with tempfile.TemporaryDirectory() as d:
        a, _ = pair(d)
        secret_edge(a.store)
        kind, _out = attempt(lambda: a.dispute(U, "e-1", reason="wrong"))
        row("A2/A3-control", "HOLDS", "HOLDS" if kind == "returned" else "FOUND",
            "no redaction: dispute returns and its episode quotes the user's own fact (the hook is what makes A2/A3)")

orig_replace = R.EDGE_REPLACE
for mutant in (False, True):
    if mutant:                                          # the treatment leaves subject/relation: the incidental closure
        R.EDGE_REPLACE = tuple(f for f in orig_replace if f not in ("subject", "relation"))
    try:
        with tempfile.TemporaryDirectory() as d:
            a, b = pair(d)
            secret_edge(a.store)
            find_edge_gap(a, b)
            kind, out = attempt(lambda: a.correct(U, "e-1", "somewhere else"))
            hits = carriers(a.store)
    finally:
        R.EDGE_REPLACE = orig_replace
    if not mutant:
        row("A4 correct", "HOLDS", "HOLDS" if kind == "refused" and not hits else "FOUND",
            f"correct: {kind} ({str(out)[:60]}); carriers {hits} — closed only because the redaction markers `subject`, "
            f"so plan_correction's fresh scope read no longer holds the prior (an UNNAMED dependency)")
    else:
        row("A4-mutant", "FOUND", "FOUND" if kind == "returned" and hits else "HOLDS",
            f"the same interleaving with a treatment that leaves subject/relation: correct {kind}; carriers {hits} — "
            f"the closure is incidental, not designed")

for gap in (True, False):
    with tempfile.TemporaryDirectory() as d:
        a, b = pair(d)
        secret_edge(a.store)

        def llm(prompt, system=None, role=None, _gap=gap, _b=b):
            if _gap:
                _b.redact(U, edge_id="e-1", reason="subject_request")
            return "WIKI " + prompt
        body = compile_wiki(a.store, llm, U, DEFAULT_RELATIONS)
        cached = a.store._conn.execute("SELECT text FROM wiki WHERE user_id=?", (U,)).fetchone()
    if gap:
        row("A5 compile", "HOLDS", "HOLDS" if cached is None else "FOUND",
            f"compile_wiki under the gap: cache {'NOT published' if cached is None else 'published'} (the "
            f"version-conditional set_wiki, one statement)")
        row("A5-residual", "FOUND", "FOUND" if SECRET in body else "HOLDS",
            f"…but the body compiled from the pre-redaction read is RETURNED to the caller "
            f"(secret in the returned body: {SECRET in body}) — a served read after the redaction committed")
    else:
        row("A5-control", "HOLDS", "HOLDS" if cached is not None and SECRET in cached[0] else "FOUND",
            "no redaction: the page is cached and carries the user's content (the instrument can see a publish)")


class _Emb:
    def __init__(self, cb):
        self.cb = cb

    def id(self):
        return "rec@1"

    def dim(self):
        return 3

    def __call__(self, texts):
        self.cb()
        return [[1.0, float(len(x)), 0.5] for x in texts]


for gap in (True, False):
    with tempfile.TemporaryDirectory() as d:
        cfg = MemoryConfig(db_path=str(pathlib.Path(d) / "e.db"), wiki_recompile_after_writes=0, scope_groups={},
                           require_source_id=False)
        b = Memory(llm=tt._quiet, config=cfg)
        fired = []
        a = Memory(llm=tt._quiet, config=cfg, embed=_Emb(
            lambda _g=gap, _b=b, _f=fired: (_g and not _f and _f.append(_b.redact(U, edge_id="e-1",
                                                                                    reason="subject_request")))))
        secret_edge(a.store)
        n = a.embed_backfill(U)
        v = a.store._conn.execute("SELECT COUNT(*) FROM edge_embedding WHERE edge_id='e-1'").fetchone()[0]
    row("A6 backfill" if gap else "A6-control", "HOLDS", "HOLDS" if (v == 0) == gap else "FOUND",
        f"embed_backfill, redaction {'during' if gap else 'absent from'} the embed call: wrote {n}, vectors {v} "
        f"(digest-conditional upsert under BEGIN IMMEDIATE)")

for gap in (True, False):
    with tempfile.TemporaryDirectory() as d:
        a, b = pair(d, "dst.db")
        secret_edge(a.store)
        p = pathlib.Path(d) / "self.jsonl"
        export_memory(a.store, U, p)
        real, fired = a.store.commit_outcome_import_plan, []

        def hooked(uid, plan, expected, _g=gap, _b=b, _real=real, _f=fired):
            _f.append(1)
            if _g:
                _b.redact(U, edge_id="e-1", reason="subject_request")
            return _real(uid, plan, expected)
        a.store.commit_outcome_import_plan = hooked
        kind, out = attempt(lambda: import_memory(a.store, p, restore=True))
        hits = carriers(a.store)
    row("A7 import-skip" if gap else "A7-skip-control", "HOLDS",
        "HOLDS" if fired and kind == "returned" and (not hits) == gap else "FOUND",
        f"restore of the store's own export, redaction between plan and commit {'present' if gap else 'absent'}: "
        f"{kind} (skipped={out.get('skipped') if isinstance(out, dict) else '-'}); carriers {hits}")

for restore in (False, True):
    for gap in (True, False):
        with tempfile.TemporaryDirectory() as d:
            s = tt._mem(pathlib.Path(d), "src.db")
            secret_edge(s.store)
            p = pathlib.Path(d) / "x.jsonl"
            export_memory(s.store, U, p)
            a, b = pair(d, "dst.db")
            real, fired = a.store.commit_outcome_import_plan, []

            def hooked(uid, plan, expected, _g=gap, _b=b, _real=real, _f=fired):
                _f.append(1)
                if _g and len(_f) == 1:                 # the id is ABSENT at plan; B creates then redacts it
                    secret_edge(_b.store)
                    _b.redact(U, edge_id="e-1", reason="subject_request")
                return _real(uid, plan, expected)
            a.store.commit_outcome_import_plan = hooked
            kind, out = attempt(lambda: import_memory(a.store, p, restore=restore))
            hits = carriers(a.store)
        want = ("refused", []) if gap else ("returned", hits)
        row(f"A7 import-write r={int(restore)}" if gap else f"A7-write-control r={int(restore)}", "HOLDS",
            "HOLDS" if fired and (kind, hits) == want and (gap or hits) else "FOUND",
            f"the WRITE branch (the planner never writes ONTO an existing record: differing refuses at preflight, "
            f"equal skips), id absent at plan and created+redacted in the gap {'yes' if gap else 'no'}: {kind} "
            f"({str(out)[:50]}); carriers {hits}")

# ===================================================================================================== SWEEP B
section("B — a contribution-ledger id matched without its kind",
        "MECHANICAL: every SQL string literal in store/sqlite.py naming contribution_ledger whose text matches "
        "`survivor_id` without `survivor_type`, or `contributor_ref` without `contributor_type`, in the same statement")
src = (ROOT / "src" / "veracium" / "store" / "sqlite.py").read_text()
tree = ast.parse(src)
funcs = [(n.lineno, n.end_lineno, n.name) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
hits = []
for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and "contribution_ledger" in node.value:
        sql = node.value
        bad = [c for c, t in (("survivor_id", "survivor_type"), ("contributor_ref", "contributor_type"))
               if c in sql and t not in sql]
        if bad:
            fn = min((f for f in funcs if f[0] <= node.lineno <= f[1]), key=lambda f: f[1] - f[0])[2]
            hits.append((fn, tuple(bad)))
names = sorted({h[0] for h in hits})
row("B-control", "FOUND", "FOUND" if "_redact_in_txn" in names else "HOLDS",
    f"the reviewer's instance is among the hits (`_redact_in_txn`, R9-03): {'_redact_in_txn' in names}")
for fn in [n for n in names if n != "_redact_in_txn"]:
    row(f"B {fn}", "FOUND", "FOUND",
        f"sibling: {fn} matches {sorted({c for f, b in hits if f == fn for c in b})} without the type "
        f"({'0021 export reverse join, pre-0041; in scope by research' if fn == 'contributions_naming' else 'NEW'})")
print(f"    total hits: {len(hits)} literal(s) in {names}")

# ===================================================================================================== SWEEP C
section("C — an identity carried across the import boundary without its destination",
        "every identity minted or carried by import — record ids, ledger row ids (plan_row_id), event refs, the "
        "notice id — and whether it binds the DESTINATION user")
with tempfile.TemporaryDirectory() as d:
    src = tt._mem(pathlib.Path(d), "src.db")
    secret_edge(src.store)
    src.redact(U, edge_id="e-1", reason="subject_request")
    p = pathlib.Path(d) / "x.jsonl"
    export_memory(src.store, U, p)
    dst = SqliteStore(str(pathlib.Path(d) / "dst.db"))
    import_memory(dst, p, user_id="u-a")
    second = import_memory(dst, p, user_id="u-b")
    held = dst._conn.execute("SELECT user_id, target_id FROM redactions").fetchall()
    b_attested = sorted(dst._attested_fields("u-b", "edge", "e-1"))
lost = second.get("notices_existing") == 1 and second.get("notices_applied") == 0 and not b_attested
row("C notice_id", "FOUND", "FOUND" if lost else "HOLDS",
    f"one export imported for two destination users of one store: the second import reports existing="
    f"{second.get('notices_existing')} applied={second.get('notices_applied')}, u-b's target attested {b_attested}, "
    f"rows held {held} — `notice_id(origin, source_user, source_event_ref)` takes no destination (R9-04(a) is the "
    f"reviewer's instance; the sweep's question is whether any OTHER minted identity shares the gap)")
edges_by_user = {u: dst._conn.execute("SELECT COUNT(*) FROM edges WHERE user_id=?", (u,)).fetchone()[0]
                 for u in ("u-a", "u-b")}
row("C-control records", "HOLDS", "HOLDS" if edges_by_user == {"u-a": 1, "u-b": 1} else "FOUND",
    f"the same two imports, a destination-bound identity: the record rows exist per destination {edges_by_user} "
    f"(the instrument can see an identity that holds). plan_row_id hashes user_id and survivor_type into the ledger "
    f"row id (read; its validator refuses a synthetic row, so not executed here); event refs are minted locally")

# ===================================================================================================== SWEEP D
section("D — a D1 vocabulary column that accepts prose",
        "each column D1 names (edge_event.reason, Edge.invalidation_reason, source_revocations.reason, "
        "Episode.retired_reason), written with a prose value through every public writer")
PROSE = "told me in confidence about the divorce"
with tempfile.TemporaryDirectory() as d:
    a, _ = pair(d)
    a.store.add_edge(Edge(id="e-0", user_id=U, subject="user", relation="lives_at", object="x", provenance=prov()))
    kind, out = attempt(lambda: a.store.invalidate_edge("e-0", dt.datetime.now(dt.timezone.utc), PROSE))
    row("D-control edge_event.reason", "HOLDS", "HOLDS" if kind == "refused" else "FOUND",
        f"invalidate_edge (the only writer of edge_event.reason) with prose: {kind}")
    now = dt.datetime.now(dt.timezone.utc)
    kind1, _ = attempt(lambda: a.store.add_edge(Edge(id="e-2", user_id=U, subject="user", relation="lives_at",
                                                     object="y", provenance=prov(), invalidated_at=now,
                                                     invalidation_reason=PROSE)))
    a.store.add_edge(Edge(id="e-3", user_id=U, subject="user", relation="lives_at", object="z", provenance=prov()))
    e3 = next(x for x in a.store.edges(U, active_only=False) if x.id == "e-3")
    e3.invalidated_at, e3.invalidation_reason = now, PROSE
    kind2, _ = attempt(lambda: a.store.add_edge(e3))
    stored = [r[0] for r in a.store._conn.execute(
        "SELECT json_extract(json,'$.invalidation_reason') FROM edges WHERE id IN ('e-2','e-3') ORDER BY id")]
    journal = [r for r in a.store._conn.execute("SELECT kind, reason FROM edge_event WHERE edge_id='e-3' ORDER BY seq")]
row("D Edge.invalidation_reason", "FOUND", "FOUND" if kind1 == kind2 == "returned" and stored == [PROSE] * 2
    else "HOLDS",
    f"add_edge on create: {kind1}; on re-upsert active->invalidated: {kind2}; stored {len(stored)} prose reasons. "
    f"(Residual, named: that invalidation is journaled as {journal[-1] if journal else None}, never `invalidated`)")
print("    source_revocations.reason and Episode.retired_reason: R9-02's own (round9_reproductions.py)")

# ===================================================================================================== SWEEP E
section("E — a derived surface or reader that ignores attestation",
        "every product-module enumeration of store.edges(/episodes( (selfcheck's own temp stores aside), executed on "
        "an attested record beside an unredacted control; the contract is §4b-iii's reader table plus D3")
TODAY = dt.date.today().isoformat()
for red in (False, True):
    with tempfile.TemporaryDirectory() as d:
        a, _ = pair(d)
        secret_edge(a.store, "e-cur", relation="mood", volatility=Volatility.TRANSIENT)          # CURRENT CONTEXT
        secret_edge(a.store, "e-conf", relation="works_as", needs_confirmation=True)             # CONFIRM WHEN NATURAL
        a.store.add_edge(Edge(id="e-due", user_id=U, subject="user", relation="plans", provenance=prov(),
                              object=f"submit the form by {TODAY} " + SECRET))                   # DATED COMMITMENTS
        a.store.add_episode(Episode(id="ep-1", user_id=U, date=TODAY, summary="ep " + SECRET,     # RECENT HISTORY
                                    provenance=prov()))
        if red:
            for e in ("e-cur", "e-conf", "e-due"):
                a.redact(U, edge_id=e, reason="subject_request")
            a.redact(U, episode_id="ep-1", reason="subject_request")
        r = a.recall(U)
        got = sorted([e.id for e in r.edges] + [e.id for e in r.episodes])
    want = ["e-conf", "e-cur", "e-due", "ep-1"]
    if red:
        three = ["e-conf", "e-cur", "ep-1"]
        row("E proactive", "FOUND", "FOUND" if all(x in got for x in three) and R.MARKER in r.context else "HOLDS",
            f"recall() with no query, one redacted record per section: RETURNS {got}, rendered as marker lines "
            f"(secret in context: {SECRET in r.context}) — the CONFIRM, CURRENT and RECENT HISTORY sections; §4b-iii's "
            f"recall row says 'not returned'; not a content disclosure")
        row("E proactive-dated", "HOLDS", "HOLDS" if "e-due" not in got else "FOUND",
            "the DATED COMMITMENTS section drops its redacted record — INCIDENTALLY: it selects on an ISO date read "
            "from the object, which the redaction markered (the fix's read-time exclusion makes this designed)")
    else:
        row("E-control proactive", "HOLDS", "HOLDS" if got == want and SECRET in r.context else "FOUND",
            f"unredacted: all four sections surface {got} with content (the instrument sees every branch)")

old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3000)
for mode in ("control", "pre-redacted"):
    with tempfile.TemporaryDirectory() as d:
        a, _ = pair(d)
        secret_edge(a.store, "e-1", relation="works_as", volatility=Volatility.SLOW, provenance=prov(observed_at=old))
        a.store.add_edge(Edge(id="e-2", user_id=U, subject="user", relation="likes", object="tea",
                              volatility=Volatility.SLOW, provenance=prov(observed_at=old)))
        if mode == "pre-redacted":
            a.redact(U, edge_id="e-1", reason="subject_request")
        kind, out = attempt(lambda: a.maintain(U, consolidate=False))
        flags = {x.id: x.needs_confirmation for x in a.store.edges(U, active_only=False)}
    if mode == "control":
        row("E-control expire", "HOLDS", "HOLDS" if kind == "returned" and all(flags.values()) else "FOUND",
            f"aged SLOW edges, none redacted: maintain {kind}, flags {flags}")
    else:
        row("E expire", "FOUND", "FOUND" if kind == "refused" and not flags.get("e-2") else "HOLDS",
            f"one aged SLOW edge redacted, NO race: maintain {kind} ({str(out)[:60]}); the other edge is never "
            f"processed (flags {flags}) — on every run, permanently")

for red in (False, True):
    with tempfile.TemporaryDirectory() as d:
        a, _ = pair(d)
        for i in range(8):
            a.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-0{i + 1}", summary=f"day {i}",
                                        provenance=prov()))
        if red:
            a.redact(U, episode_id="ep-3", reason="subject_request")
        listed = []

        def llm(prompt, system=None, role=None, _l=listed):
            _l.append(prompt)
            return json.dumps({"records": [{"date": "2026-01-01", "summary": "week"}]})
        consolidate(a.store, llm, U, a.config, now=dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc))
        marker_listed = bool(listed) and R.MARKER in listed[0]
        consumed = a.store._conn.execute("SELECT COUNT(*) FROM episodes WHERE id='ep-3'").fetchone()[0] == 0
        dangling = sorted(a.store.redacted_targets(U, "episode"))
    if red:
        row("E consolidation-selection", "FOUND", "FOUND" if marker_listed and consumed else "HOLDS",
            f"an attested episode is a cold candidate: the marker reached the LLM listing ({marker_listed}), the "
            f"episode was consumed ({consumed}), the attestation now names an absent id {dangling}")
    else:
        row("E-control consolidation", "HOLDS", "HOLDS" if listed and consumed else "FOUND",
            "no redaction: the eight episodes are listed and consumed")

for red in (False, True):
    with tempfile.TemporaryDirectory() as d:
        a, _ = pair(d)
        secret_edge(a.store, "e-1", relation="works_as")
        t = dt.datetime.now(dt.timezone.utc)
        if red:
            a.redact(U, edge_id="e-1", reason="subject_request")
        q = a.recall(U, "works")
        aso = a.recall(U, "works", as_of=t)
        wtxt = why.render(why.gather(a.store, U, "e-1"))
        intro = str(a.introspect(U, mode="categories"))
        since = a.edges_since(U, t - dt.timedelta(days=1))
    tag = "" if red else "-control"
    if red:
        row("E query-recall", "HOLDS", "HOLDS" if "e-1" not in [e.id for e in q.edges] else "FOUND",
            "query recall: not returned")
        row("E as-of", "HOLDS", "HOLDS" if "e-1" not in [e.id for e in aso.edges] else "FOUND",
            "as-of recall: not returned")
        row("E why", "HOLDS", "HOLDS" if SECRET not in wtxt and "redacted" in wtxt else "FOUND",
            "why renders 'redacted' and no content")
        row("E introspect", "HOLDS", "HOLDS" if SECRET not in intro and R.MARKER not in intro else "FOUND",
            "introspect categories: neither content nor marker")
        row("E edges_since", "OBSERVED", "OBSERVED",
            f"edges_since returns the redacted edge carrying the marker: "
            f"{[(e.id, R.MARKER in e.object) for e in since]} — HELD BY THE OWNER; reported, nothing proposed")
    else:
        row("E-control readers", "HOLDS",
            "HOLDS" if "e-1" in [e.id for e in q.edges] and "e-1" in [e.id for e in aso.edges] and SECRET in wtxt
            and SECRET in intro else "FOUND",
            "unredacted: query recall, as-of, why and introspect all show the record (each instrument can see it)")
from veracium.schema import EvidenceContext                                         # noqa: E402
for red in (False, True):
    with tempfile.TemporaryDirectory() as d:
        a, _ = pair(d)
        pid = a.record_procedure(U, "SECRETWORD reviews go to the team lead", author=EvidenceAuthor.USER,
                                 context=EvidenceContext.direct(basis="stated"))
        if red:
            a.redact(U, edge_id=pid, reason="subject_request")
        dr = a.describe_procedures(U)
        txt = repr(dr)
        outcomes = [w.outcome for w in dr.withheld]
    if red:
        row("E describe_procedures", "HOLDS",
            "HOLDS" if "SECRETWORD" not in txt and R.MARKER not in txt and outcomes == ["redacted"] else "FOUND",
            f"reported as redacted, not omitted (§4b-iii's row): withheld outcomes {outcomes}, no content, no marker")
    else:
        row("E-control describe_procedures", "HOLDS", "HOLDS" if "SECRETWORD" in txt else "FOUND",
            "unredacted: the procedure is described with its content")
print("    internal, no output surface: compile's contention-id list (ids only), dryrun snapshot, _lexical_scored "
      "(feeds query recall, which filters)")

# ---------------------------------------------------------------- summary
print("\n" + "-" * 100)
bad = [r for r, ok in ROWS if not ok]
print(f"  {len(ROWS)} rows; {len(ROWS) - len(bad)} measured the class they state; mismatches: {bad or 'none'}")
sys.exit(0 if not bad else 1)
