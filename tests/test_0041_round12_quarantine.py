"""specs/0041 round 12 — R11-01: the field set a real redaction emits is one its own importer accepts.

Round 11 listed `provenance.disclosure` in the attestation of every quarantine-relation edge — even a current-writer
record already QUARANTINED, where nothing moved — while a notice's domain was carrier_paths alone; the store exported a
notice its own importer refused, and a destination holding the earlier edge kept its content. Now the attestation's
domain is carrier_paths(kind) ∪ a CLOSED, NAMED bookkeeping set (`redaction.attestation_paths`), read by the writer,
the parser and the commit primitive; `provenance.disclosure` is listed only when §4h's re-establishment MOVED it; and
the repair lives in the pure `treat_edge`. Every cell runs the real `Memory.redact`, export and import; the matrix
cells are GENERATED from writer-reachable carrier states, as the round-11 sweep generated them.
"""
import datetime as dt
import importlib.util
import itertools
import json
import pathlib
import sys

import pytest

from veracium import redaction as R
from veracium.portability import export_memory, import_memory
from veracium.schema import Disclosure, Edge, QUARANTINE_RELATION

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r12q", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r12q"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-QUARANTINE-R12"


def _strict(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _lines(p):
    return [json.loads(x, object_pairs_hook=_strict) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def _write(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def _head(recs):
    return [r for r in recs if r.get("kind") == "veracium-export"]


def _notices(recs):
    return [r for r in recs if r.get("record") == "redaction"]


# the 2026-10-13 notice-binding hotfix's report and its two direct checks: a default-path notice that is not applied
# is listed in `notices_not_applied` as [kind, id] (never in `inconsistent_notices`, which keeps "the held version was
# redacted anyway", a restore-only outcome now); the held bytes are compared on the WHOLE json; rows are counted directly
def _not_applied(r, kind, tid):
    return [kind, tid] in [list(x)[:2] for x in r["notices_not_applied"]] and tid not in r["inconsistent_notices"]


def _held_json(st, kind, tid):
    row = st._conn.execute(f"SELECT json FROM {'edges' if kind == 'edge' else 'episodes'} WHERE id=?", (tid,)).fetchone()
    return row[0] if row else None


def _redaction_rows(st, tid=None):
    if tid is None:
        return st._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0]
    return st._conn.execute("SELECT COUNT(*) FROM redactions WHERE target_id=?", (tid,)).fetchone()[0]


def _applied_rows(st, tid=None):
    """T4 (specs/0041 §11.6.6): APPLIED redaction rows only — an attestation. A default import over a held target now
    records the notice PENDING (and an absent one STANDING), so "nothing applied" is no APPLIED row, not no row."""
    q = "SELECT COUNT(*) FROM redactions WHERE state='applied'"
    return st._conn.execute(q + ("" if tid is None else " AND target_id=?"), (() if tid is None else (tid,))).fetchone()[0]


def _edge_json(st, eid):
    r = st._conn.execute("SELECT json, quarantined FROM edges WHERE id=?", (eid,)).fetchone()
    return (r[0], r[1]) if r else (None, None)


def _q_edge(eid="e-q", relation=QUARANTINE_RELATION, **kw):
    return Edge(id=eid, user_id=U, subject="user", relation=relation, object=SECRET,
                provenance=tt._prov(disclosure=Disclosure.QUARANTINED), **kw)


def _round_trip(tmp_path, src_store, tid, restore, recs_filter=None):
    """export → a destination → its re-export → a third store; asserts each hop applies and is attested."""
    p = tmp_path / "src.jsonl"
    export_memory(src_store, U, p)
    if recs_filter:
        p = _write(tmp_path / "iso.jsonl", recs_filter(_lines(p)))
    (n,) = [x for x in _notices(_lines(p)) if x["target_id"] == tid]
    assert set(n["fields"]) <= R.attestation_paths("edge")
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p, restore=restore)
    js, quarantined = _edge_json(dst.store, tid)
    assert SECRET not in js and dst.store._attested_fields(U, "edge", tid)
    relay = tmp_path / "relay.jsonl"
    export_memory(dst.store, U, relay)
    third = tt._mem(tmp_path, "third.db")
    import_memory(third.store, relay, restore=restore)
    assert third.store._attested_fields(U, "edge", tid)
    return n, quarantined


# ------------------------------------------------------------------ the domain

def test_the_attestation_domain_is_the_carriers_plus_a_closed_named_bookkeeping_set():
    for kind in ("edge", "episode"):
        assert R.attestation_paths(kind) == R.carrier_paths(kind) | frozenset(R.BOOKKEEPING_PATHS[kind])
    assert R.BOOKKEEPING_PATHS["edge"] == ("provenance.disclosure", "journal.state")   # the journal: R11-02
    assert "provenance.disclosure" not in R.carrier_paths("edge")          # bookkeeping, never a carrier


@pytest.mark.parametrize("kind,field", [("edge", "provenance.origin"), ("edge", "provenance.source_id"),
                                        ("episode", "provenance.disclosure"), ("edge", "a field in prose")])
def test_the_notice_domain_stays_closed(tmp_path, kind, field):
    """Admitting ONE named bookkeeping path opens nothing else: other provenance paths, the bookkeeping path on the
    wrong kind, and prose are refused at the import boundary, with nothing written."""
    from veracium.schema import Episode
    src = tt._mem(tmp_path, "src.db")
    if kind == "edge":
        src.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
        src.redact(U, edge_id="t", reason="subject_request")
    else:
        src.store.add_episode(Episode(id="t", user_id=U, date="2026-10-01", summary=SECRET, provenance=tt._prov()))
        src.redact(U, episode_id="t", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = _lines(p)
    (n,) = _notices(recs)
    dst = tt._mem(tmp_path, "dst.db")
    with pytest.raises(ValueError):
        import_memory(dst.store, _write(tmp_path / "bad.jsonl", _head(recs) + [dict(n, fields=n["fields"] + [field])]))
    assert dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0


# ------------------------------------------------------------------ the verdict's cases

@pytest.mark.parametrize("restore", [False, True])
def test_R11_01_quarantine_redaction_export_applies_to_held_target(tmp_path, restore):
    """The current writer's quarantine edge: the disclosure was already QUARANTINED, nothing moved, nothing listed —
    and the destination holding the earlier edge applies the notice and stays quarantined; the relay applies too."""
    src = tt._mem(tmp_path, "src.db")
    src.store.add_edge(_q_edge())
    rec = src.redact(U, edge_id="e-q", reason="subject_request")
    assert "provenance.disclosure" not in rec.fields_cleared
    dst = tt._mem(tmp_path, "held.db")
    dst.store.add_edge(_q_edge())
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    held = _edge_json(dst.store, "e-q")
    r = import_memory(dst.store, p, restore=restore)
    js, quarantined = _edge_json(dst.store, "e-q")
    if restore:
        assert SECRET not in js and quarantined == 1 and dst.store._attested_fields(U, "edge", "e-q")
    else:
        # (A) attack-shaped on the default path: the notice reaching the destination's own HELD edge is what the
        # 2026-10-13 notice-binding hotfix closes — not applied, the held bytes unchanged, nothing attested, no applied row (T4: the notice PENDING)
        assert (js, quarantined) == held and _applied_rows(dst.store, "e-q") == 0
        assert not dst.store._attested_fields(U, "edge", "e-q") and r["notices_applied"] == 0
        assert _not_applied(r, "edge", "e-q")
    (tmp_path / "rt").mkdir()
    _round_trip(tmp_path / "rt", src.store, "e-q", restore)


@pytest.mark.parametrize("restore", [False, True])
def test_the_frozen_relation_only_quarantine_lists_the_moved_disclosure_and_round_trips(tmp_path, restore):
    m = tt._frozen_memory(tmp_path)
    eid = tt._frozen_rows()["relation_only_quarantine"]
    rec = m.redact(U, edge_id=eid, reason="subject_request")
    assert "provenance.disclosure" in rec.fields_cleared                  # it MOVED here, so it is listed
    keep = lambda recs: _head(recs) + [x for x in recs if x.get("id") == eid and x.get("record") == "edge"] + \
        [x for x in _notices(recs) if x["target_id"] == eid]
    (tmp_path / "rt").mkdir()
    n, quarantined = _round_trip(tmp_path / "rt", m.store, eid, restore, keep)
    assert "provenance.disclosure" in n["fields"] and quarantined == 1


def test_a_destination_holding_the_relation_only_shape_moves_and_attests_its_own_disclosure(tmp_path):
    """Research's cell (a): the SOURCE's notice does not list the disclosure (its record was already QUARANTINED); the
    DESTINATION holds the pre-closure shape — the destination's own treatment moves its disclosure and attests it:
    the attestation is the notice's fields ∪ the destination's own treatment, across the hop."""
    eid = tt._frozen_rows()["relation_only_quarantine"]
    dst = tt._frozen_memory(tmp_path)
    src = tt._mem(tmp_path, "src.db")
    src.store.add_edge(_q_edge(eid))
    src.redact(U, edge_id=eid, reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = _lines(p)
    (n,) = _notices(recs)
    assert "provenance.disclosure" not in n["fields"]
    # (A) the treatment-union property needs the notice APPLIED to the HELD pre-closure record: since the 2026-10-13
    # notice-binding hotfix that is a trusted restore whose file SHOWS the redaction (the source's treated record beside
    # the notice; the fixed-point rule, both modes) ...
    notice_file = _write(tmp_path / "n.jsonl", _head(recs) + [n])
    (treated,) = [x for x in recs if x.get("record") == "edge" and x.get("id") == eid]
    assert treated["object"] == R.MARKER
    ra = import_memory(dst.store, _write(tmp_path / "nt.jsonl", _head(recs) + [treated, n]), restore=True)
    assert ra["notices_applied"] == 1
    js, quarantined = _edge_json(dst.store, eid)
    assert quarantined == 1 and json.loads(js)["provenance"]["disclosure"] == Disclosure.QUARANTINED.value
    assert "provenance.disclosure" in dst.store._attested_fields(U, "edge", eid)
    # ... and the default path, on a second copy of the same frozen store, applies nothing to the held record
    (tmp_path / "dflt").mkdir()
    dflt = tt._frozen_memory(tmp_path / "dflt")
    before = _edge_json(dflt.store, eid)
    r = import_memory(dflt.store, notice_file)
    assert _edge_json(dflt.store, eid) == before and not dflt.store._attested_fields(U, "edge", eid)
    assert r["notices_applied"] == 0 and _applied_rows(dflt.store, eid) == 0 and _not_applied(r, "edge", eid)
    # ... and the notice-only file on restore no longer applies to the UNTREATED held record either: reported
    (tmp_path / "rst").mkdir()
    rst = tt._frozen_memory(tmp_path / "rst")
    before_r = _edge_json(rst.store, eid)
    rr = import_memory(rst.store, notice_file, restore=True)
    assert _edge_json(rst.store, eid) == before_r and _applied_rows(rst.store, eid) == 0 and rr["notices_applied"] == 0
    assert ["edge", eid, "record-not-in-file"] in [list(x) for x in rr["notices_not_applied"]]


def test_control_an_ordinary_relation_with_a_quarantined_disclosure_round_trips(tmp_path):
    src = tt._mem(tmp_path, "src.db")
    src.store.add_edge(_q_edge(relation="lives_at"))
    src.redact(U, edge_id="e-q", reason="subject_request")
    n, quarantined = _round_trip(tmp_path, src.store, "e-q", False)
    assert "provenance.disclosure" not in n["fields"] and quarantined == 1


# ------------------------------------------------------------------ the generated matrix (the round-11 sweep's)

_DIMS = {"relation": ("lives_at", QUARANTINE_RELATION), "note": (None, "a note " + SECRET),
         "original_relation": (None, "lived_at"), "invalidation_reason": (None, "superseded"), "confirm": (False, True)}
_CELLS = [dict(zip(_DIMS, c)) for c in itertools.product(*_DIMS.values())]


def _cell_store(tmp_path, cell, name="m.db"):
    """One generated edge state, written through the real writers, NOT yet redacted."""
    m = tt._mem(tmp_path, name)
    disc = Disclosure.QUARANTINED if cell["relation"] == QUARANTINE_RELATION else Disclosure.MENTIONABLE
    kw = {k: cell[k] for k in ("note", "original_relation") if cell[k] is not None}
    # every generated state is writer-reachable (the round-11 sweep measured 32 of 32); one that is not FAILS here
    m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation=cell["relation"], object=SECRET,
                          provenance=tt._prov(disclosure=disc), **kw))
    if cell["invalidation_reason"]:
        m.store.invalidate_edge("t", dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc), cell["invalidation_reason"])
    if cell["confirm"] and not cell["invalidation_reason"] and cell["relation"] != QUARANTINE_RELATION:
        m.confirm(U, "t")
    return m


_IDS = ["-".join(str(v)[:10] for v in c.values()) for c in _CELLS]


@pytest.mark.parametrize("cell", _CELLS, ids=_IDS)
def test_every_writer_reachable_edge_state_round_trips_through_destination_and_relay(tmp_path, cell):
    """A FRESH destination and its relay (what `_round_trip` builds); the held-earlier destination is the next test."""
    m = _cell_store(tmp_path, cell)
    m.redact(U, edge_id="t", reason="subject_request")
    for restore in (False, True):
        d = tmp_path / f"rt{int(restore)}"
        d.mkdir()
        _round_trip(d, m.store, "t", restore)


@pytest.mark.parametrize("restore", [False, True])
@pytest.mark.parametrize("cell", _CELLS, ids=_IDS)
def test_every_writer_reachable_edge_state_reaches_a_destination_holding_it_earlier(tmp_path, cell, restore):
    """Round 13 (the round-12 verdict's evidence-scope note): the SAME generated states, into a destination that HOLDS
    the earlier edge — exported before the redaction and imported first — then the redacted export: the held edge is
    treated in place and attested, a quarantined edge stays quarantined, the journal holds no prior content."""
    m = _cell_store(tmp_path, cell)
    export_memory(m.store, U, tmp_path / "before.jsonl")
    m.redact(U, edge_id="t", reason="subject_request")
    export_memory(m.store, U, tmp_path / "after.jsonl")
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "before.jsonl", restore=restore)
    assert SECRET in _edge_json(dst.store, "t")[0]                     # the destination HOLDS the earlier edge
    held = _edge_json(dst.store, "t")
    r = import_memory(dst.store, tmp_path / "after.jsonl", restore=restore)
    js, quarantined = _edge_json(dst.store, "t")
    if not restore:
        # (A) attack-shaped on the default path: the notice reaching a HELD edge is what the 2026-10-13 notice-binding
        # hotfix closes — not applied (a genuine propagation to a held record waits for round 4's origin binding)
        assert (js, quarantined) == held and _applied_rows(dst.store, "t") == 0
        assert not dst.store._attested_fields(U, "edge", "t") and r["notices_applied"] == 0
        assert _not_applied(r, "edge", "t")
        return
    assert SECRET not in js and dst.store._attested_fields(U, "edge", "t")
    assert quarantined == (cell["relation"] == QUARANTINE_RELATION)
    assert not any(SECRET in (st or "") for (st,) in dst.store._conn.execute("SELECT state FROM edge_event WHERE edge_id='t'"))
