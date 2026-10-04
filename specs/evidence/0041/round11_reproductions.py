#!/usr/bin/env python3
"""0041 round 11 — the verdict's three implementation findings, reproduced at the pin BEFORE any fix.

Pin `04581ec4c9dc65bf09cfa53a796d48d9ec307fc9` (0041 v15.1). The reviewer's regressions (in their evidence archive)
were not supplied to this seat, so each scenario is built from the verdict's description through the REAL paths
(`Memory`, `SqliteStore`, `export_memory`/`import_memory`, `confirm`, `add_edge`); the frozen pre-restriction store is
used for the legacy relation-only quarantine record, as the verdict did. A file is edited only where the verdict's own
reproduction edits one (R11-03 changes one notice's reason). Each finding prints the claim and the outcome here, and
runs the verdict's controls; a control that misbehaves makes the run exit non-zero.
Run from the repository root (or an export): python specs/evidence/0041/round11_reproductions.py
"""
import importlib.util
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from veracium import redaction as R                                           # noqa: E402
from veracium.portability import export_memory, import_memory                 # noqa: E402
from veracium.schema import Disclosure, Edge, Episode, QUARANTINE_RELATION     # noqa: E402

_spec = importlib.util.spec_from_file_location("tt41_r11r", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r11r"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "REVIEW-CONTENT-ALPHA"
RESULTS, CONTROLS = [], []


def claim(n, sentence):
    print(f"\n=== R11-0{n} — {sentence}")


def result(n, ok, detail):
    print(("    REPRODUCED: " if ok else "    DID NOT REPRODUCE: ") + detail)
    RESULTS.append((n, ok))


def control(n, ok, detail):
    print(("    control holds: " if ok else "    CONTROL FAILED: ") + detail)
    CONTROLS.append((n, ok))


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
        return "refused", f"{type(e).__name__}: {str(e)[:400]}"


def edge_json(st, eid):
    r = st._conn.execute("SELECT json FROM edges WHERE id=?", (eid,)).fetchone()
    return None if r is None else r[0]


def attested(st, user, kind, tid):
    return sorted(st._attested_fields(user, kind, tid))


# ---------------------------------------------------------------- R11-01
claim(1, "redacting an edge whose relation is the quarantine relation emits a notice naming `provenance.disclosure`, "
         "which the importer's carrier domain rejects; a destination holding the earlier edge keeps its content")


def q_edge(eid="e-q", relation=QUARANTINE_RELATION):
    return Edge(id=eid, user_id=U, subject="user", relation=relation, object=SECRET,
                provenance=tt._prov(disclosure=Disclosure.QUARANTINED))


for restore in (False, True):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        src, dst = tt._mem(d, "src.db"), tt._mem(d, "dst.db")
        src.store.add_edge(q_edge()); dst.store.add_edge(q_edge())
        rec = src.redact(U, edge_id="e-q", reason="subject_request")
        p = d / "x.jsonl"
        export_memory(src.store, U, p)
        (n,) = notices(lines(p))
        k, got = attempt(lambda: import_memory(dst.store, p, restore=restore))
        result(1, k == "refused" and "provenance.disclosure" in got and SECRET in edge_json(dst.store, "e-q")
               and not attested(dst.store, U, "edge", "e-q"),
               f"restore={restore}: source receipt fields {sorted(rec.fields_cleared)}, quarantined after: "
               f"{src.store._conn.execute('SELECT quarantined FROM edges WHERE id=?', ('e-q',)).fetchone()[0]}; the "
               f"notice names {n['fields']}; import → {k}: {got if k == 'refused' else ''}; the destination keeps the "
               f"content: {SECRET in edge_json(dst.store, 'e-q')}, attested: {attested(dst.store, U, 'edge', 'e-q')}")
for restore in (False, True):                               # the frozen pre-closure relation-only quarantine record
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        m = tt._frozen_memory(d)
        eid = tt._frozen_rows()["relation_only_quarantine"]
        m.redact(U, edge_id=eid, reason="subject_request")
        p = d / "f.jsonl"
        export_memory(m.store, U, p)
        recs = lines(p)
        (n,) = [x for x in notices(recs) if x["target_id"] == eid]
        target = [x for x in recs if x.get("record") == "edge" and x.get("id") == eid]
        dst = tt._mem(d, "dst-frozen.db")
        k, got = attempt(lambda: import_memory(dst.store, write_lines(d / "iso.jsonl", head(recs) + target + [n]), restore=restore))
        result(1, k == "refused" and "provenance.disclosure" in got,
               f"restore={restore}: frozen relation-only record {eid!r}: the notice names {n['fields']}; the isolated record + notice → {k}: "
               f"{got if k == 'refused' else ''}")

for restore in (False, True):                               # control: an ordinary relation, quarantined disclosure
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        src, dst = tt._mem(d, "src.db"), tt._mem(d, "dst.db")
        src.store.add_edge(q_edge(relation="lives_at")); dst.store.add_edge(q_edge(relation="lives_at"))
        src.redact(U, edge_id="e-q", reason="subject_request")
        p = d / "x.jsonl"
        export_memory(src.store, U, p)
        k, got = attempt(lambda: import_memory(dst.store, p, restore=restore))
        control(1, k == "ok" and SECRET not in edge_json(dst.store, "e-q"),
                f"restore={restore}: ordinary relation with a quarantined disclosure → {k}; treated: "
                f"{SECRET not in edge_json(dst.store, 'e-q')}")

# ---------------------------------------------------------------- R11-02
claim(2, "the 'nothing to redact' decision reads the LIVE record only: an edge emptied by add_edge, whose journal (and "
         "confirmation digest) still carry content, is refused and those carriers stay untreated")


def journal_states(st, eid):
    return [s for (s,) in st._conn.execute("SELECT state FROM edge_event WHERE edge_id=? ORDER BY seq", (eid,))]


for with_confirm in (False, True):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        m = tt._mem(d, "m.db")
        m.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
        if with_confirm:
            m.confirm(U, "e-1")
        k0, _ = attempt(lambda: m.store.add_edge(Edge(id="e-1", user_id=U, subject="", relation="", object="",
                                                      provenance=tt._prov())))
        digest = m.store._conn.execute("SELECT request_digest FROM confirmations WHERE edge_id='e-1'").fetchone()
        k, got = attempt(lambda: m.redact(U, edge_id="e-1", reason="subject_request"))
        js = journal_states(m.store, "e-1")
        result(2, k0 == "ok" and k == "refused" and "nothing to redact" in got and any(SECRET in (s or "") for s in js)
               and (not with_confirm or (digest and m.store._conn.execute(
                   "SELECT request_digest FROM confirmations WHERE edge_id='e-1'").fetchone() == digest)),
               f"confirm first: {with_confirm}; the empty update → {k0}; redact → {k}: {got if k == 'refused' else ''}; "
               f"journal events still carrying the content: {sum(SECRET in (s or '') for s in js)} of {len(js)}"
               + (f"; confirmation digest intact: {bool(digest)} ({len(digest[0]) if digest else 0} chars)" if with_confirm else ""))
with tempfile.TemporaryDirectory() as d:                    # control: a genuinely empty episode refuses, nothing written
    d = pathlib.Path(d)
    m = tt._mem(d, "m.db")
    m.store.add_episode(Episode(id="ep-e", user_id=U, date="2026-10-01", summary="", provenance=tt._prov()))
    n0 = m.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0]
    k, _ = attempt(lambda: m.redact(U, episode_id="ep-e", reason="subject_request"))
    control(2, k == "refused" and m.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == n0,
            f"genuinely empty episode → {k}, nothing written")
with tempfile.TemporaryDirectory() as d:                    # control: a non-empty edge treats journal and digest
    d = pathlib.Path(d)
    m = tt._mem(d, "m.db")
    m.store.add_edge(Edge(id="e-2", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    m.confirm(U, "e-2")
    m.redact(U, edge_id="e-2", reason="subject_request")
    dg = m.store._conn.execute("SELECT request_digest FROM confirmations WHERE edge_id='e-2'").fetchone()[0]
    control(2, not any(SECRET in (s or "") for s in journal_states(m.store, "e-2")) and dg == R.MARKER,
            f"non-empty edge: journal treated {not any(SECRET in (s or '') for s in journal_states(m.store, 'e-2'))}, "
            f"digest replaced {dg == R.MARKER}")

# ---------------------------------------------------------------- R11-03
claim(3, "the source-body comparison selects WITNESSED rows only: a contradictory notice of the store's OWN redaction "
         "is accepted, and its next export carries two bodies under one source identity, which a fresh import refuses")


def native_case(d, kind, remap):
    m = tt._mem(d, "m.db")
    if kind == "edge":
        m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
        m.redact(U, edge_id="t", reason="subject_request")
    else:
        m.store.add_episode(Episode(id="t", user_id=U, date="2026-10-01", summary=SECRET, provenance=tt._prov()))
        m.redact(U, episode_id="t", reason="subject_request")
    p = d / "own.jsonl"
    export_memory(m.store, U, p)
    recs = lines(p)
    (n,) = notices(recs)
    changed = dict(n, reason="operator_policy")
    k, got = attempt(lambda: import_memory(m.store, write_lines(d / "chg.jsonl", head(recs) + [changed]),
                                           **({"user_id": "v"} if remap else {})))
    out = d / "after.jsonl"
    export_memory(m.store, "v" if remap else U, out)
    fresh = tt._mem(d, "fresh.db")
    k2, got2 = attempt(lambda: import_memory(fresh.store, out))
    return k, got, k2, got2, notices(lines(out))


for kind in ("edge", "episode"):
    for remap in (False, True):
        with tempfile.TemporaryDirectory() as d:
            k, got, k2, got2, outn = native_case(pathlib.Path(d), kind, remap)
            result(3, k == "ok" and (remap or (k2 == "refused" and "different bodies" in got2)),
                   f"{kind}, remap={remap}: the contradictory notice of the store's own event → {k}"
                   f"{'' if k == 'refused' else ' (applied ' + str(got.get('notices_applied')) + ')'}; "
                   + ("" if remap else f"the next export carries {len(outn)} notices; a fresh import of it → {k2}: "
                      f"{got2 if k2 == 'refused' else ''}"))
with tempfile.TemporaryDirectory() as d:                    # control: an EQUAL native body stays importable
    d = pathlib.Path(d)
    m = tt._mem(d, "m.db")
    m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    m.redact(U, edge_id="t", reason="subject_request")
    p = d / "own.jsonl"
    export_memory(m.store, U, p)
    k, _ = attempt(lambda: import_memory(m.store, p))
    control(3, k == "ok", f"the store's own export re-imported (equal body) → {k}")
with tempfile.TemporaryDirectory() as d:                    # control: a WITNESSED contradiction refuses
    d = pathlib.Path(d)
    src = tt._mem(d, "src.db")
    src.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    src.redact(U, edge_id="t", reason="subject_request")
    p = d / "x.jsonl"
    export_memory(src.store, U, p)
    recs = lines(p)
    dst = tt._mem(d, "dst.db")
    import_memory(dst.store, write_lines(d / "n.jsonl", head(recs) + notices(recs)))
    k, got = attempt(lambda: import_memory(dst.store, write_lines(d / "c.jsonl", head(recs) + [dict(notices(recs)[0], reason="operator_policy")])))
    control(3, k == "refused" and "different body" in got, f"a witnessed contradiction → {k}")

# ---------------------------------------------------------------- summary
print("\n" + "-" * 100)
for n, ok in RESULTS:
    print(f"  R11-0{n}: {'REPRODUCED' if ok else 'DID NOT REPRODUCE'}")
bad = [n for n, ok in CONTROLS if not ok]
print(f"  controls: {len(CONTROLS) - len(bad)} of {len(CONTROLS)} hold" + (f"; FAILED for {sorted(set(bad))}" if bad else ""))
sys.exit(0 if all(ok for _, ok in RESULTS) and not bad else 1)
