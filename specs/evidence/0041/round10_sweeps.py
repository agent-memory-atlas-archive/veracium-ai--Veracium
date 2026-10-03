#!/usr/bin/env python3
"""0041 round 10 — the SWEEPS: each round-10 verdict finding treated as a sample of its class, measured at the pin.

Pin `de9f9659855069118fcdaa74650e5bbb030c463a`, before any fix (the companion of `round10_reproductions.py`). The four
criteria were agreed with research BEFORE anything was measured (coordination ledger, 2026-10-03):
  A  (R10-01) every import branch that meets a HELD record differing from the incoming one, and what it does when a
     valid notice accompanies it; the branches are the importer's labelled held-differs refusals, DERIVED from
     portability.py, not listed by hand
  B  (R10-02) target state (present · standing · completed-but-absent · re-arriving) × every REMOVER that deletes a
     row while its attestation could stay × every RE-ARRIVAL path, including notice-only imports and the next
     repeated receipt
  C  (R10-03) every identity or key built by JOINING caller-reachable values, or compared by a prefix: two distinct
     inputs that encode equal, or an encoding that fails to decode. The candidates are DERIVED by an AST pass over
     src/ (an f-string joining >=2 interpolations around a short separator, or `sep.join(...)` over non-constants,
     outside messages), plus the long-separator `event_ref` form the pass's length bound would miss
  D  (R10-04) every branch where a stored VALUE decides provenance: the fact it keys on, and every writer of that
     fact. A branch is accused only when a PUBLIC caller can set the fact independently of the operation (research's
     refinement; a hand-built export file counts as a public input)
Each row states the class it EXPECTS at this tree and what was MEASURED:
  FOUND     the defect is present here        HOLDS    the surface is safe, measured with the same instrument
  OBSERVED  measured and reported; no defect claimed (the reason is printed)
The exit status is 0 when every row measured the class it states. After the fixes the FOUND rows are expected to
move; this file is the pin-time record, and the fixes carry their own cells.
Run from the repository root (or an export): python specs/evidence/0041/round10_sweeps.py
"""
import ast
import hashlib
import importlib.util
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from veracium import redaction as R                                                  # noqa: E402
from veracium import graph as _graph                                                 # noqa: E402
from veracium.compile import DEFAULT_RELATIONS                                       # noqa: E402
from veracium.contribution import consolidation_op_key                              # noqa: E402
from veracium.portability import export_memory, import_memory                       # noqa: E402
from veracium.schema import Edge, Episode                                            # noqa: E402
from veracium.scope_linkage import row_op_key                                        # noqa: E402
from veracium.store.sqlite import SqliteStore                                        # noqa: E402

_spec = importlib.util.spec_from_file_location("tt41_r10s", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r10s"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-SWEEP-R10"
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


def mem(d, name):
    return tt._mem(pathlib.Path(d), name)


def lines(path):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in path.read_text().splitlines() if x.strip()]


def write_lines(path, recs):
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return path


def head(recs):
    return [r for r in recs if r.get("kind") == "veracium-export"]


def notices(recs):
    return [r for r in recs if r.get("record") == "redaction"]


def attempt(fn):
    try:
        return "ok", fn()
    except Exception as e:
        return "refused", f"{type(e).__name__}: {str(e)[:110]}"


def carries(st, kind, tid, text=SECRET):
    tbl = "edges" if kind == "edge" else "episodes"
    r = st._conn.execute(f"SELECT json FROM {tbl} WHERE id=?", (tid,)).fetchone()
    return None if r is None else (text in r[0])


def attested(st, user, kind, tid):
    return bool(st._attested_fields(user, kind, tid))


def ledger_digests(st, user, sid):
    return st._conn.execute("SELECT identity_digest, evidence_ref_digest FROM contribution_ledger WHERE user_id=? "
                            "AND survivor_type='edge' AND survivor_id=?", (user, sid)).fetchall()


# ===================================================================================================== SWEEP A
section("A — a HELD record differing from the incoming one, with and without a valid notice (R10-01)",
        "the held-differs branches are the importer's labelled `*-conflict` refusals in portability.py (derived "
        "below). FOUND = a branch that refuses (or keeps the content) when a valid notice for the record is present")
src_text = (ROOT / "src" / "veracium" / "portability.py").read_text()
labels = sorted(set(re.findall(r'"([a-z-]+-conflict)"\)', src_text)))
print(f"    held-differs branches, derived: {labels}")


def kind_source(d, kind):
    """A source holding one record of `kind`, its pre-redaction export p1, then the redaction and its export p2.
    Returns (src, target_kind, target_id, p1, p2, probe) where probe(st) says whether the held content survives."""
    src = mem(d, f"a-{kind}.db")
    if kind == "edge":
        src.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
        tk, tid = "edge", "e-1"
    elif kind == "interaction":
        src.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-10-01", summary=f"we discussed {SECRET}",
                                      provenance=tt._prov()))
        tk, tid = "episode", "ep-1"
    elif kind == "outcome":
        src.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="prefers", object=SECRET, provenance=tt._prov()))
        src.record_outcome(U, "e-1", outcome="confirmed", actor="user", evidence_ref="ev-outcome")
        tk, tid = "episode", [e.id for e in src.store.episodes(U) if e.kind == "outcome"][0]
    else:                                                     # ledger: a native absorption; the SURVIVOR is redacted
        src.store.add_edge(Edge(id="e-prior", user_id=U, subject="user", relation="lives_in", object="Berlin",
                                provenance=tt._prov(source_id="src-a", evidence_ref="ev-a")))
        _graph.apply_supersession(src.store, Edge(id="e-1", user_id=U, subject="user", relation="lives_in",
                                                  object="Berlin Mitte",
                                                  provenance=tt._prov(source_id="src-a", evidence_ref="ev-b")),
                                  DEFAULT_RELATIONS)
        tk, tid = "edge", "e-1"
        held = ledger_digests(src.store, U, tid)
        # the fixture OWNS its input: a source with no digest-bearing ledger row measures nothing — refuse instead
        assert held and all(a and b for a, b in held), f"the absorption built no digest-bearing ledger row: {held}"
    p1 = pathlib.Path(d) / f"a-{kind}-1.jsonl"
    export_memory(src.store, U, p1)
    src.redact(U, edge_id=tid, reason="subject_request") if tk == "edge" else \
        src.redact(U, episode_id=tid, reason="subject_request")
    p2 = pathlib.Path(d) / f"a-{kind}-2.jsonl"
    export_memory(src.store, U, p2)
    return src, tk, tid, p1, p2


# "ledger" was PREDICTED FOUND before this ran (research's sweep note asked whether ledger rows were a held-differs
# branch); MEASURED HOLDS: the notice's application clears the held rows' digests and scope-rows-conflict never fires.
for kind, expect in (("edge", "HOLDS"), ("interaction", "HOLDS"), ("outcome", "FOUND"), ("ledger", "HOLDS")):
    with tempfile.TemporaryDirectory() as d:
        _s, tk, tid, p1, p2 = kind_source(d, kind)
        dst = mem(d, "dst.db")
        import_memory(dst.store, p1)
        before = ledger_digests(dst.store, U, tid) if kind == "ledger" else None
        k, got = attempt(lambda: import_memory(dst.store, p2))
        text = "Mitte" if kind == "ledger" else SECRET
        treated = carries(dst.store, tk, tid, text) is False and attested(dst.store, U, tk, tid)
        extra = ""
        if kind == "ledger":
            assert before and all(a and b for a, b in before), f"the destination holds no digest-bearing row: {before}"
            after = ledger_digests(dst.store, U, tid)
            treated = treated and after and all(x == (None, None) for x in after)
            extra = f"; ledger digests held before {bool(before and all(a and b for a, b in before))}, after {after}"
        row(f"A1 {kind}", expect, "HOLDS" if (k == "ok" and treated) else "FOUND",
            f"held = the pre-redaction record; the source's full export (record treated + its notice) → {k}"
            f"{'' if k == 'ok' else ': ' + got}; held now treated and attested: {treated}{extra}")

for kind, expect in (("edge", "HOLDS"), ("interaction", "HOLDS"), ("outcome", "FOUND")):
    with tempfile.TemporaryDirectory() as d:          # held is ALREADY treated; the OLD record arrives with the notice
        _s, tk, tid, p1, p2 = kind_source(d, kind)
        dst = mem(d, "dst.db")
        import_memory(dst.store, p2)
        old = [r for r in lines(p1) if r.get("record") in ("edge", "episode")]
        f = write_lines(pathlib.Path(d) / "old+notice.jsonl", head(lines(p2)) + old + notices(lines(p2)))
        k, got = attempt(lambda: import_memory(dst.store, f))
        row(f"A2 {kind}", expect, "HOLDS" if (k == "ok" and carries(dst.store, tk, tid) is False) else "FOUND",
            f"held = treated; the OLD record + its notice → {k}{'' if k == 'ok' else ': ' + got}; still treated: "
            f"{carries(dst.store, tk, tid) is False}")

for kind in ("edge", "interaction", "outcome"):                # control: a changed record and NO notice still refuses
    with tempfile.TemporaryDirectory() as d:
        _s, tk, tid, p1, _p2 = kind_source(d, kind)
        dst = mem(d, "dst.db")
        import_memory(dst.store, p1)
        recs = lines(p1)
        field = "object" if tk == "edge" else "summary"
        chg = [dict(r, **{field: r[field] + " (edited)"}) if r.get("id") == tid and r.get("record") in ("edge", "episode")
               else r for r in recs]
        k, got = attempt(lambda: import_memory(dst.store, write_lines(pathlib.Path(d) / "chg.jsonl", chg)))
        row(f"A3 {kind} control", "HOLDS", "HOLDS" if k == "refused" and carries(dst.store, tk, tid) else "FOUND",
            f"a changed record with no notice → {k}; the held content is unchanged: {carries(dst.store, tk, tid)}")

with tempfile.TemporaryDirectory() as d:                       # a TOPOLOGY conflict refuses, notice or not
    _s, tk, tid, p1, p2 = kind_source(d, "outcome")
    dst = mem(d, "dst.db")
    import_memory(dst.store, p1)
    recs = lines(p2)
    topo = [dict(r, seq=(r.get("seq") or 0) + 5) if r.get("id") == tid and r.get("record") == "episode" else r for r in recs]
    k, got = attempt(lambda: import_memory(dst.store, write_lines(pathlib.Path(d) / "topo.jsonl", topo)))
    row("A4 outcome topology control", "HOLDS", "HOLDS" if k == "refused" else "FOUND",
        f"the outcome's seq moved, with its valid notice → {k} (a structural conflict must still refuse)")

with tempfile.TemporaryDirectory() as d:                       # STANDING notice, then the outcome arrives
    _s, tk, tid, p1, p2 = kind_source(d, "outcome")
    dst = mem(d, "dst.db")
    r1 = import_memory(dst.store, write_lines(pathlib.Path(d) / "n.jsonl", head(lines(p2)) + notices(lines(p2))))
    k, got = attempt(lambda: import_memory(dst.store, p1))
    row("A5 outcome standing arrival", "HOLDS", "HOLDS" if (k == "ok" and carries(dst.store, tk, tid) is False) else "FOUND",
        f"the notice first (standing {r1.get('notices_standing')}), then the untreated outcome → {k}"
        f"{'' if k == 'ok' else ': ' + got}; treated on arrival: {carries(dst.store, tk, tid) is False}")

# ===================================================================================================== SWEEP B
section("B — target state × removers × re-arrival (R10-02)",
        "FOUND = after any reachable sequence, the record's content is present while `redactions` attests it, or a "
        "repeated redact reports done over that content")


def ep_files(d):
    src = mem(d, "b-src.db")
    src.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-10-01", summary=f"we discussed {SECRET}",
                                  provenance=tt._prov()))
    po = pathlib.Path(d) / "old.jsonl"
    export_memory(src.store, U, po)
    src.redact(U, episode_id="ep-1", reason="subject_request")
    pn = pathlib.Path(d) / "new.jsonl"
    export_memory(src.store, U, pn)
    old, new = lines(po), lines(pn)
    rec = [r for r in old if r.get("id") == "ep-1"]
    return (write_lines(pathlib.Path(d) / "rec+notice.jsonl", head(new) + rec + notices(new)),
            write_lines(pathlib.Path(d) / "rec.jsonl", head(new) + rec),
            write_lines(pathlib.Path(d) / "notice.jsonl", head(new) + notices(new)), rec[0])


def restored(st):
    return carries(st, "episode", "ep-1") is True and attested(st, U, "episode", "ep-1")


# the removers: every DELETE of an edge/episode row in store/, derived, plus the per-user erasure
store_src = (ROOT / "src" / "veracium" / "store" / "sqlite.py").read_text()
tree = ast.parse(store_src)
funcs = [(n.lineno, n.end_lineno, n.name) for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
deleters = sorted({min((f for f in funcs if f[0] <= n.lineno <= f[1]), key=lambda f: f[1] - f[0])[2]
                   for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and re.search(r"DELETE FROM (edges|episodes)\b", n.value)})
print(f"    removers that DELETE an edge/episode row by statement, derived: {deleters}; plus forget_user's "
      f"table loop (_ERASE_TABLES)")

for restore in (False, True):
    with tempfile.TemporaryDirectory() as d:
        both, rec_only, notice_only, _r = ep_files(d)
        dst = mem(d, "dst.db")
        import_memory(dst.store, both, restore=restore)
        dst.store.delete_episode("ep-1")
        k, got = attempt(lambda: import_memory(dst.store, both, restore=restore))
        row(f"B1 completed-but-absent × record+notice (restore={restore})", "FOUND", "FOUND" if restored(dst.store) else "HOLDS",
            f"delete_episode, then the identical file → {k}; content present while attested: {restored(dst.store)}")
        rk, rep = attempt(lambda: dst.redact(U, episode_id="ep-1", reason="subject_request"))
        row(f"B2 the next repeated receipt (restore={restore})", "FOUND",
            "FOUND" if (rk == "ok" and rep.repeated and carries(dst.store, "episode", "ep-1")) else "HOLDS",
            f"redact after the repopulation → {rk}; repeated={getattr(rep, 'repeated', rep)}; content still present: "
            f"{carries(dst.store, 'episode', 'ep-1')}")

with tempfile.TemporaryDirectory() as d:
    both, rec_only, notice_only, rec = ep_files(d)
    dst = mem(d, "dst.db")
    import_memory(dst.store, both)
    dst.store.delete_episode("ep-1")
    k, _ = attempt(lambda: import_memory(dst.store, rec_only))
    row("B3 completed-but-absent × record, no notice", "HOLDS", "HOLDS" if k == "refused" and carries(dst.store, "episode", "ep-1") is None else "FOUND",
        f"→ {k}; absent afterwards: {carries(dst.store, 'episode', 'ep-1') is None}")
    k, got = attempt(lambda: import_memory(dst.store, notice_only))
    row("B4 completed-but-absent × notice only", "HOLDS", "HOLDS" if carries(dst.store, "episode", "ep-1") is None else "FOUND",
        f"→ {k} ({ {x: got.get(x) for x in ('notices_existing', 'notices_applied')} if k == 'ok' else got}); nothing "
        f"inserted: {carries(dst.store, 'episode', 'ep-1') is None}")
    ep = Episode.model_validate(dict((x, y) for x, y in rec.items() if x != "record"))
    k, got = attempt(lambda: dst.store.add_episode(ep))
    row("B5 completed-but-absent × ordinary add_episode", "HOLDS", "HOLDS" if k == "refused" else "FOUND",
        f"the original episode written directly → {k}{': ' + got if k == 'refused' else ''}")

with tempfile.TemporaryDirectory() as d:
    both, rec_only, notice_only, _r = ep_files(d)
    dst = mem(d, "dst.db")
    import_memory(dst.store, notice_only)
    k, _ = attempt(lambda: import_memory(dst.store, rec_only))
    row("B6 standing × record arrives", "HOLDS", "HOLDS" if k == "ok" and carries(dst.store, "episode", "ep-1") is False else "FOUND",
        f"→ {k}; treated on arrival: {carries(dst.store, 'episode', 'ep-1') is False}")
    k, _ = attempt(lambda: import_memory(dst.store, both))
    row("B7 present (treated) × record+notice again", "HOLDS", "HOLDS" if carries(dst.store, "episode", "ep-1") is False else "FOUND",
        f"→ {k}; still treated: {carries(dst.store, 'episode', 'ep-1') is False}")

with tempfile.TemporaryDirectory() as d:                       # the per-user erasure removes the attestation WITH the data
    both, rec_only, notice_only, _r = ep_files(d)
    dst = mem(d, "dst.db")
    import_memory(dst.store, both)
    dst.store.forget_user(U)
    left = dst.store._conn.execute("SELECT COUNT(*) FROM redactions WHERE user_id=?", (U,)).fetchone()[0]
    k, _ = attempt(lambda: import_memory(dst.store, both))
    row("B8 forget_user × record+notice", "HOLDS", "HOLDS" if left == 0 and carries(dst.store, "episode", "ep-1") is False else "FOUND",
        f"erasure leaves {left} redaction rows (attestation erased with the data, so nothing is attested-but-restored); "
        f"re-import with the notice → {k}, treated: {carries(dst.store, 'episode', 'ep-1') is False}")

with tempfile.TemporaryDirectory() as d:                       # consolidation's removers never meet an attested row
    m = mem(d, "b9.db")
    for i in range(8):
        m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                    provenance=tt._prov()))
    m.redact(U, episode_id="ep-3", reason="subject_request")
    cands = m.store._conn.execute("SELECT id FROM episodes WHERE user_id=?", (U,)).fetchall()
    excluded = "ep-3" in m.store.redacted_targets(U, "episode")
    row("B9 consolidation removers (_abandon, delete_claimed_inputs_if_current)", "HOLDS", "HOLDS" if excluded else "FOUND",
        f"an attested episode is never a consolidation candidate (round 10, A1) and `redact` refuses a claimed input, so "
        f"neither remover deletes an attested row: ep-3 in the attested set {excluded}; the A1 cells "
        f"(tests/test_0041_round10_txn.py) execute both directions")
row("B10 edges", "OBSERVED", "OBSERVED",
    "no remover deletes a single EDGE row (the derived list above has none for edges; forget_user erases "
    "the attestation with it), so completed-but-absent is unreachable for an edge at this tree")

# ===================================================================================================== SWEEP C
section("C — identities built by JOINING caller-reachable values, or compared by prefix (R10-03)",
        "two distinct inputs that encode equal, or an encoding that fails to decode; inputs U+001F, NUL, ':', '%', "
        "'_', '|', empty. Candidates: the AST pass (header), classified by use")
nid = SqliteStore.notice_id
pid = SqliteStore.parse_notice_id
a = nid("origin\u001fpart", "owner", "event", "u", "edge", "e")
b = nid("origin", "part\u001fowner", "event", "u", "edge", "e")
row("C1 notice_id over U+001F", "FOUND", "FOUND" if a == b else "HOLDS",
    f"('origin\\x1fpart','owner',…) and ('origin','part\\x1fowner',…) encode equal: {a == b}")
row("C2 parse_notice_id over U+001F", "FOUND", "FOUND" if pid(nid("o", "owner\u001fpart", "u:1", "d", "edge", "e")) is None else "HOLDS",
    f"a source user carrying the separator decodes to {pid(nid('o', 'owner' + chr(31) + 'part', 'u:1', 'd', 'edge', 'e'))!r} "
    f"(None: the relay then treats the row as LOCAL)")
row("C3 parse_notice_id, empty source event", "OBSERVED", "OBSERVED",
    f"('o','u','') decodes to {pid(nid('o', 'u', '', 'd', 'edge', 'e'))!r}: an EMPTY component decodes, so the "
    f"encoding cannot tell an empty event from one a relay emits after decoding fails (the verdict's probe note)")
with tempfile.TemporaryDirectory() as d:
    st = SqliteStore(str(pathlib.Path(d) / "c.db"))
    for name, user in (("NUL", "owner\u0000part"), ("%", "own%r"), ("_", "own_r"), (":", "own:r"), ("|", "own|r")):
        prefix = SqliteStore.NOTICE_SEP.join(("notice", "o", user, "ev", ""))
        rid = nid("o", user, "ev", "d", "edge", "e")
        hit = st._conn.execute("SELECT substr(?, 1, ?) = ?", (rid, len(prefix), prefix)).fetchone()[0]
        row(f"C4 the body comparison's substr prefix over {name}", "FOUND" if name == "NUL" else "HOLDS",
            "HOLDS" if hit == 1 else "FOUND", f"the row id's prefix matches its own source identity: {bool(hit)}")
    st.close() if hasattr(st, "close") else None
e1 = f"{'u:episode'}:{1}"                                      # sqlite.py: an EDGE event ref, f"{user_id}:{seq}"
e2 = f"{'u'}:episode:{1}"                                      # sqlite.py: an EPISODE event ref, f"{user_id}:episode:{seq}"
consumers = re.findall(r"WHERE[^\"']*\bevent_ref\s*=", store_src)
row("C5 event_ref across users and kinds", "OBSERVED", "OBSERVED",
    f"user 'u:episode' edge seq 1 → {e1!r}; user 'u' episode seq 1 → {e2!r}; equal: {e1 == e2}. No statement looks "
    f"a row up BY event_ref ({len(consumers)} lookups); it travels as a notice's source_event_ref beside source_user, "
    f"so the collision reaches identity only through the notice_id encoding (C1's fix closes it there)")
ids = ("a", "a:b", ":", "a\u001fb", "", "op-x:1")
dec = all(consolidation_op_key("op-0123456789ab", i, t, c).split(":", 3) == ["op-0123456789ab", str(i), t, c]
          for i in (0, 7) for t in ("edge", "episode") for c in ids)
row("C6 consolidation_op_key", "HOLDS", "HOLDS" if dec else "FOUND",
    "op id op-<12hex>, an int index and a CLOSED contributor type before ONE unrestricted id: over the reachable "
    f"domain (types edge/episode; ids {ids!r}) every key decodes back to its inputs by split(':', 3): {dec}")
rk1 = row_op_key("op-0123456789ab", "imported-absorption", "a\u001fb", "c")
rk2 = row_op_key("op-0123456789ab", "imported-absorption", "a", "b\u001fc")
row("C7 row_op_key / plan_row_id (0021's framed form)", "HOLDS", "HOLDS" if rk1 != rk2 else "FOUND",
    f"the unrestricted pair is FRAMED into a digest (scope_linkage._framed): separator-shifted pairs distinct: {rk1 != rk2}")
d1 = hashlib.sha256("\x1f".join(["u", "a\x1fuser\x1fconfirm", "user", "confirm", "v", "OMITTED"]).encode()).hexdigest()
row("C8 the confirmation request digest", "OBSERVED", "OBSERVED",
    "READ, not executed: looked up under (user_id, correlation_id), so a collision needs the SAME user; after the user the components are "
    "the edge id (which must exist), two closed enums, a constant and a date that must PARSE (_event_dt), so a "
    "separator inside the edge id cannot be re-balanced by a later component — the tail is fixed-shape (digest "
    f"computed for a crafted id: {d1[:12]}…, distinct from the plain id's by construction)")

# ===================================================================================================== SWEEP D
section("D — a stored VALUE deciding provenance (R10-04)",
        "per branch: (1) the fact it keys on; (2) every writer of that fact and whether a PUBLIC caller can set it "
        "independently of the operation (a hand-built export file is a public input). Accused only when (2) is yes")
branches = [(m.start(), m.group(0)) for m in re.finditer(r"reason\s*[!=]=\s*\"imported_notice\"|reason='imported_notice'|"
                                                           r"source_body is (not )?None|source_body IS (NOT )?NULL|"
                                                           r"event_ref IS NULL", store_src)]
lines_of = sorted({store_src.count("\n", 0, p) + 1 for p, _ in branches})
print(f"    provenance-keyed expressions in store/sqlite.py, derived: {len(branches)} at lines {lines_of}")
with tempfile.TemporaryDirectory() as d:
    m = mem(d, "d.db")
    m.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    k, got = attempt(lambda: m.redact(U, edge_id="e-1", reason="imported_notice"))
    row("D1 `reason` (receipt and export branch on reason == 'imported_notice')", "FOUND", "FOUND" if k == "ok" else "HOLDS",
        f"writer: Memory.redact(reason=caller) — public; reason 'imported_notice' → {k}. A caller sets the fact "
        f"independently of any notice: ACCUSED")
    st = m.store
    rid_local = st._conn.execute("SELECT id, source_body FROM redactions").fetchone()
    row("D2 `source_body` (receipt/export: a foreign body when NOT NULL)", "HOLDS",
        "HOLDS" if rid_local[1] is None else "FOUND",
        "writers: the import commit only (`_redact_in_txn(source_body=n['_body'])`, the standing insert), each from "
        "the importer's canonical body of a notice; Memory.redact passes none — a local row holds NULL here: "
        f"{rid_local[1] is None}. A hand-built file sets it only AS a foreign notice, which is what it is: not accused")
    row("D3 the row id's notice form (parse_notice_id)", "HOLDS", "HOLDS" if rid_local[0].startswith("rd-") else "FOUND",
        f"writers: a local redaction mints 'rd-<hex>' ({rid_local[0][:8]}…); only the importer writes the notice form. "
        "Not caller-settable; its DECODING over the identifier domain is sweep C's (C2)")
with tempfile.TemporaryDirectory() as d:
    both, rec_only, notice_only, _r = ep_files(d)
    dst = mem(d, "dst.db")
    import_memory(dst.store, notice_only)
    import_memory(dst.store, rec_only)
    sb = dst.store._conn.execute("SELECT source_body, event_ref FROM redactions").fetchone()
    row("D4 `event_ref IS NULL` (a STANDING notice) and its completion", "HOLDS",
        "HOLDS" if sb[0] is not None and sb[1] is not None else "FOUND",
        "writers of a NULL event_ref: the standing insert only (a local redaction always writes its event); the "
        f"arrival's UPDATE completes the row and leaves source_body: kept {sb[0] is not None}, event written {sb[1] is not None}")

# ---------------------------------------------------------------- summary
print("\n" + "-" * 100)
bad = [r for r, ok in ROWS if not ok]
print(f"  {len(ROWS)} rows; {len(ROWS) - len(bad)} measured the class they state; mismatches: {bad or 'none'}")
sys.exit(0 if not bad else 1)
