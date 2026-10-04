"""specs/0041 round 12 — R11-03: one source identity has one body, whether this store ORIGINATED the event or witnessed it.

Round 11's comparison read only WITNESSED rows (their source columns and stored body); a store's own NATIVE redaction
has neither, so a contradictory notice of the store's own event was accepted — and its next export carried two bodies
under one identity, which a fresh import refuses. The class sweep found a second instance: the store's own event
relayed back HONESTLY wrote a second attestation row for one source event. Now ONE canonical projection
(`SqliteStore._canonical_source`) gives every row its identity and body — native rows from this store's origin, their
user, their event and their own facts; witnessed rows from their columns — and both the export and the comparison use
it. The three-way rule (research's stage 1): equal body and the SAME bound target as a native row → existing, no
second row; equal body and ANOTHER target → applied there, as a WITNESSED row; a different body → refused, native or
witnessed. No foreign columns are ever written onto a native row.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

from veracium.portability import export_memory, import_memory
from veracium.schema import Edge, Episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r12n", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r12n"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-NATIVE-R12"


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _lines(p):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def _write(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def _head(recs):
    return [r for r in recs if r.get("kind") == "veracium-export"]


def _notices(recs):
    return [r for r in recs if r.get("record") == "redaction"]


def _own(tmp_path, kind="edge"):
    m = tt._mem(tmp_path, "m.db")
    if kind == "edge":
        m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
        m.redact(U, edge_id="t", reason="subject_request")
    else:
        m.store.add_episode(Episode(id="t", user_id=U, date="2026-10-01", summary=SECRET, provenance=tt._prov()))
        m.redact(U, episode_id="t", reason="subject_request")
    p = tmp_path / "own.jsonl"
    export_memory(m.store, U, p)
    return m, _lines(p)


def _rows(st):
    return st._conn.execute("SELECT * FROM redactions ORDER BY id").fetchall()


@pytest.mark.parametrize("kind", ["edge", "episode"])
@pytest.mark.parametrize("remap", [False, True])
def test_R11_03_contradiction_with_native_source_event_refuses_atomically(tmp_path, kind, remap):
    m, recs = _own(tmp_path, kind)
    before = _rows(m.store)
    changed = dict(_notices(recs)[0], reason="operator_policy")
    with pytest.raises(ValueError, match="different body"):
        import_memory(m.store, _write(tmp_path / "c.jsonl", _head(recs) + [changed]), **({"user_id": "v"} if remap else {}))
    assert _rows(m.store) == before


def test_the_stores_own_event_relayed_back_honestly_is_existing_not_a_second_row(tmp_path):
    """The class sweep's C2: the same body, the same bound target as the native row — one row stays one."""
    m, recs = _own(tmp_path)
    other = tt._mem(tmp_path, "other.db")
    import_memory(other.store, _write(tmp_path / "n.jsonl", _head(recs) + _notices(recs)))
    relay = tmp_path / "relay.jsonl"
    export_memory(other.store, U, relay)
    before = _rows(m.store)
    r = import_memory(m.store, relay)
    assert _rows(m.store) == before and r["notices_existing"] == 1


def test_a_self_import_under_a_remap_attests_the_copy_as_a_witnessed_row(tmp_path):
    """Equal body, ANOTHER bound target: applied there. The copy's row is WITNESSED — its source columns hold the native
    identity — the native row is untouched, the copy refuses an ordinary write, and a later contradiction against
    EITHER row refuses."""
    m, recs = _own(tmp_path)
    native_before = m.store._conn.execute("SELECT * FROM redactions WHERE user_id=?", (U,)).fetchall()
    r = import_memory(m.store, _write(tmp_path / "all.jsonl", recs), user_id="v")
    assert r["notices_applied"] == 1
    (row,) = m.store._conn.execute("SELECT target_id, source_origin, source_user, source_event_ref FROM redactions "
                                   "WHERE user_id='v'").fetchall()
    n = _notices(recs)[0]
    assert row[1:] == (n["origin"], n["source_user"], n["source_event_ref"])
    assert m.store._conn.execute("SELECT * FROM redactions WHERE user_id=?", (U,)).fetchall() == native_before
    copy = row[0]
    with pytest.raises(ValueError, match="redacted"):
        m.store.add_edge(Edge(id=copy, user_id="v", subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    with pytest.raises(ValueError, match="different body"):
        import_memory(m.store, _write(tmp_path / "c.jsonl", _head(recs) + [dict(n, reason="operator_policy")]),
                      user_id="w")


def test_control_the_stores_own_export_re_imported_is_existing(tmp_path):
    m, recs = _own(tmp_path)
    before = _rows(m.store)
    r = import_memory(m.store, _write(tmp_path / "all.jsonl", recs))
    assert _rows(m.store) == before and r["notices_existing"] == 1


def test_control_a_witnessed_contradiction_still_refuses(tmp_path):
    _m, recs = _own(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, _write(tmp_path / "n.jsonl", _head(recs) + _notices(recs)))
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, _write(tmp_path / "c.jsonl", _head(recs) + [dict(_notices(recs)[0], reason="operator_policy")]))


def test_the_export_and_the_comparison_share_one_projection(tmp_path):
    """The export's (origin, source_user, source_event_ref) and body for a NATIVE row are exactly what the comparison
    projects — so a re-import of the store's own export can never read as a contradiction."""
    m, recs = _own(tmp_path)
    (n,) = _notices(recs)
    row = m.store._conn.execute(f"SELECT {m.store.RECORD_COLS} FROM redactions").fetchone()
    ident, body = m.store._canonical_source(U, *row[1:])
    assert ident == (n["origin"], n["source_user"], n["source_event_ref"])
    assert m.store.notice_body(body) == m.store.notice_body(n)


def test_two_native_events_of_one_user_are_compared_each_against_its_own(tmp_path):
    """The comparison keeps a row only when its PROJECTED identity equals the notice's: a second native redaction of
    the same user is another event, never a contradiction of the first."""
    m = tt._mem(tmp_path, "m.db")
    for eid, obj in (("t1", SECRET), ("t2", SECRET + "-2")):
        m.store.add_edge(Edge(id=eid, user_id=U, subject="user", relation="lives_at", object=obj, provenance=tt._prov()))
        m.redact(U, edge_id=eid, reason="subject_request")
    p = tmp_path / "own.jsonl"
    export_memory(m.store, U, p)
    before = _rows(m.store)
    r = import_memory(m.store, p)
    assert _rows(m.store) == before and r["notices_existing"] == 2


def test_a_foreign_origin_never_compares_against_a_native_row(tmp_path):
    """Native rows are this store's identity only: a notice from ANOTHER origin that happens to share the user and the
    event ref is another source event, never a contradiction of the native one."""
    m, recs = _own(tmp_path)
    (n,) = _notices(recs)
    foreign = dict(n, origin=n["origin"] + "-elsewhere", reason="operator_policy")
    import_memory(m.store, _write(tmp_path / "f.jsonl", _head(recs) + [foreign]))


def _plant_witnessed(st, n, body):
    """PLANTED by SQL (the one write in this file): a witnessed row under the notice's source identity, on another
    target. With `body=None` it is the pre-81c68d4 shape — a witnessed row written before `source_body` existed, which
    no supported writer produces (v15.1 declares those stores unsupported)."""
    st._conn.execute(
        "INSERT INTO redactions(id, user_id, target_kind, target_id, fields, marker_version, reason, store_version_before, "
        "store_version_after, event_ref, recorded_at, source_body, source_origin, source_user, source_event_ref) "
        "VALUES('planted', ?, 'edge', 't-planted', ?, 1, 'imported_notice', 0, 0, NULL, '2026-10-04T00:00:00+00:00', "
        "?, ?, ?, ?)", (U, json.dumps(n["fields"]), body, n["origin"], n["source_user"], n["source_event_ref"]))
    st._conn.commit()


@pytest.mark.parametrize("planted_body", ["none", "different"])
def test_a_witnessed_row_holding_no_body_is_a_stated_limit_not_a_contradiction(tmp_path, planted_body):
    """The LIMIT, executed: a witnessed row with NO stored body is not compared (its body is unknown, and unknown never
    contradicts) — so a different body under its identity is NOT detected. The control plants the same row WITH a
    different body, and the import refuses."""
    _m, recs = _own(tmp_path)
    (n,) = _notices(recs)
    dst = tt._mem(tmp_path, "dst.db")
    other = dict(n, reason="operator_policy")
    _plant_witnessed(dst.store, n, None if planted_body == "none" else dst.store.notice_body(other))
    if planted_body == "none":
        import_memory(dst.store, _write(tmp_path / "n.jsonl", _head(recs) + [n]))
    else:
        with pytest.raises(ValueError, match="different body"):
            import_memory(dst.store, _write(tmp_path / "n.jsonl", _head(recs) + [n]))
