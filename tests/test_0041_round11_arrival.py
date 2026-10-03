"""specs/0041 round 11 — R10-02: a record ARRIVING for a target this store already redacted is written in the
attestation's TREATED shape, or refused; never as its content.

Round 10's import primitive admitted an episode whenever the plan carried a notice for it, then counted that notice
`existing` (it had already been applied) and skipped it — so after the supported `delete_episode`, re-importing the
same file restored the content under an attestation that still said "redacted", and the next `redact` reported
`repeated=True` over it. Now (research and dev, agreed at stage 1 — treat-on-arrival over fail-closed, because a
store's own backups must stay restorable):
  WITH the notice for it, the arrival is written as the PURE treatment of the incoming record — no new redaction
  event, no new attestation row; the next receipt is the ORIGINAL, repeated. The predicate: run the same pure
  treatment on the arriving record; refuse iff the carriers it would treat are not all attested.
  WITHOUT a notice, the arrival is refused, unchanged (v15 tranche 4b; the verdict's own control).
The doctor reads that completed-but-absent episode state as information, not damage (an absent edge stays an error).

Every cell goes through `Memory.redact`, `export_memory`, `import_memory`, `delete_episode` and `doctor.diagnose`.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

from veracium import redaction as R
from veracium.portability import export_memory, import_memory
from veracium.schema import Episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r11a", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r11a"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-ARRIVAL-R11"


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


def _ep(st, eid):
    row = st._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    return None if row is None else json.loads(row[0])


def _attestation(st):
    return st._conn.execute("SELECT * FROM redactions ORDER BY id").fetchall()


def _redaction_events(st):
    return st._conn.execute("SELECT COUNT(*) FROM episode_event WHERE kind='redacted'").fetchone()[0]


def _files(tmp_path, eid="ep-1"):
    """The reviewer's R10-02 inputs: an ordinary interaction episode's export BEFORE its redaction, the export AFTER,
    and the older record put beside the later genuine notice under the notice-capable envelope."""
    src = tt._mem(tmp_path, "src.db")
    src.store.add_episode(Episode(id=eid, user_id=U, date="2026-10-01", summary=f"we discussed {SECRET}",
                                  provenance=tt._prov()))
    old = tmp_path / "old.jsonl"
    export_memory(src.store, U, old)
    src.redact(U, episode_id=eid, reason="subject_request")
    new = tmp_path / "new.jsonl"
    export_memory(src.store, U, new)
    rec = [r for r in _lines(old) if r.get("id") == eid]
    combined = _write(tmp_path / "combined.jsonl", _head(_lines(new)) + rec + _notices(_lines(new)))
    record_only = _write(tmp_path / "record.jsonl", _head(_lines(new)) + rec)
    return combined, new, record_only


def _assert_treated(st, eid):
    d = _ep(st, eid)
    assert d is not None and d["summary"] == R.MARKER and SECRET not in json.dumps(d)
    assert d["kind"] == "interaction" and d["retired_reason"] is None        # absence is not content (§4h)


# ------------------------------------------------------------------ ACCEPTANCE: a store's own files stay importable

@pytest.mark.parametrize("restore", [False, True])
def test_R10_02_public_import_cannot_repopulate_a_deleted_attested_episode(tmp_path, restore):
    """The verdict's named regression, as ACCEPTANCE: the pre-redaction record plus its genuine notice, re-imported
    after delete_episode, SUCCEEDS — written treated, the attestation untouched, no new redaction event, and the next
    receipt is the ORIGINAL, repeated."""
    combined, _new, _r = _files(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, combined, restore=restore)
    first = dst.redact(U, episode_id="ep-1", reason="subject_request")
    att0, ev0 = _attestation(dst.store), _redaction_events(dst.store)
    dst.store.delete_episode("ep-1")
    r = import_memory(dst.store, combined, restore=restore)
    assert r["episodes"] == 1
    _assert_treated(dst.store, "ep-1")
    assert _attestation(dst.store) == att0 and _redaction_events(dst.store) == ev0
    again = dst.redact(U, episode_id="ep-1", reason="subject_request")
    assert again.repeated and again.event_ref == first.event_ref and again.recorded_at == first.recorded_at
    _assert_treated(dst.store, "ep-1")


@pytest.mark.parametrize("restore", [False, True])
def test_a_backup_taken_after_the_redaction_restores_after_a_delete(tmp_path, restore):
    """The commonest backup: the record already treated, with its notice. Its pure treatment changes NOTHING (markers
    are skipped), the empty edge of the predicate — it must pass."""
    _c, new, _r = _files(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, new, restore=restore)
    att0 = _attestation(dst.store)
    dst.store.delete_episode("ep-1")
    import_memory(dst.store, new, restore=restore)
    _assert_treated(dst.store, "ep-1")
    assert _attestation(dst.store) == att0


def test_an_honest_full_backup_of_several_redacted_episodes_restores_after_one_is_deleted(tmp_path):
    m = tt._mem(tmp_path, "m.db")
    for i in range(4):
        m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-10-0{i + 1}", summary=f"day {i} {SECRET}",
                                    provenance=tt._prov()))
    for i in (0, 1, 2):
        m.redact(U, episode_id=f"ep-{i}", reason="subject_request")
    backup = tmp_path / "backup.jsonl"
    export_memory(m.store, U, backup)
    m.store.delete_episode("ep-1")
    r = import_memory(m.store, backup, restore=True)
    assert r["episodes"] == 1                                             # the deleted one written; the rest held-equal
    for i in (0, 1, 2):
        _assert_treated(m.store, f"ep-{i}")
    assert SECRET in _ep(m.store, "ep-3")["summary"]                      # the unredacted one is untouched


# ------------------------------------------------------------------ the refusals

@pytest.mark.parametrize("restore", [False, True])
def test_control_re_arrival_without_a_notice_still_refuses(tmp_path, restore):
    combined, _new, record_only = _files(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, combined, restore=restore)
    dst.store.delete_episode("ep-1")
    with pytest.raises(ValueError, match="redacted here"):
        import_memory(dst.store, record_only, restore=restore)
    assert _ep(dst.store, "ep-1") is None


def test_control_an_ordinary_write_of_the_deleted_attested_episode_is_refused(tmp_path):
    combined, _new, _r = _files(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, combined)
    dst.store.delete_episode("ep-1")
    with pytest.raises(ValueError, match="redacted"):
        dst.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-10-01", summary=SECRET, provenance=tt._prov()))
    assert _ep(dst.store, "ep-1") is None


def test_notice_only_after_the_delete_inserts_nothing(tmp_path):
    combined, new, _r = _files(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, combined)
    dst.store.delete_episode("ep-1")
    r = import_memory(dst.store, _write(tmp_path / "n.jsonl", _head(_lines(new)) + _notices(_lines(new))))
    assert r["notices_existing"] == 1 and _ep(dst.store, "ep-1") is None


# ------------------------------------------------------------------ the doctor

def test_the_doctor_reads_a_deleted_attested_episode_as_information(tmp_path):
    from veracium import doctor as doc
    combined, _new, _r = _files(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, combined)
    dst.store.delete_episode("ep-1")
    dst.close()
    rep = doc.diagnose(str(tmp_path / "dst.db"))
    assert not [f for f in rep.findings if f.level == "error"], doc.render(rep)
    assert any(f.level == "info" and "episode since deleted" in f.message for f in rep.findings)


def test_the_doctor_still_reads_an_attestation_for_an_absent_EDGE_as_an_error(tmp_path):
    """No supported remover deletes a single edge, so an absent edge under a completed attestation is damage. The
    edge row is removed by SQL here because no public path can do it — that is the point of the control."""
    from veracium import doctor as doc
    from veracium.schema import Edge
    m = tt._mem(tmp_path, "m.db")
    m.store.add_edge(Edge(id="e-x", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    m.redact(U, edge_id="e-x", reason="subject_request")
    m.store._conn.execute("DELETE FROM edges WHERE id='e-x'")
    m.store._conn.commit()
    m.close()
    rep = doc.diagnose(str(tmp_path / "m.db"))
    assert any(f.level == "error" and "redaction record" in f.message for f in rep.findings), doc.render(rep)


def test_the_doctor_still_reads_events_of_an_UNATTESTED_absent_episode_as_an_error(tmp_path):
    """The journal exemption is specific: it covers only an episode this store ATTESTS. An episode event naming any
    other absent episode stays an error (planted by SQL: no public path writes one)."""
    from veracium import doctor as doc
    m = tt._mem(tmp_path, "m.db")
    m.store._conn.execute("INSERT INTO episode_event(user_id,seq,txn,episode_id,kind,reason,state,recorded_at) "
                          "VALUES(?,?,?,?,?,?,?,?)", (U, 999, 999, "ep-never", "mutated", None, "{}", "2026-10-03T00:00:00Z"))
    m.store._conn.commit()
    m.close()
    rep = doc.diagnose(str(tmp_path / "m.db"))
    assert any(f.level == "error" and "episode event(s) naming an episode" in f.message for f in rep.findings), doc.render(rep)


def test_an_arrival_needing_treatment_in_a_carrier_the_attestation_never_named_is_refused(tmp_path):
    """The predicate's REFUSAL, reached natively. An episode whose summary was EMPTY is redacted (the attestation names
    no field); after `delete_episode`, a file carries that id with summary content and a notice naming `summary`. The
    pure treatment of the arrival would treat `summary`, which the attestation does not cover: refused, fail-closed,
    with nothing written (the attestation is the authority, and it does not attest that field)."""
    m = tt._mem(tmp_path, "m.db")
    m.store.add_episode(Episode(id="ep-e", user_id=U, date="2026-10-01", summary="", provenance=tt._prov()))
    m.redact(U, episode_id="ep-e", reason="subject_request")
    assert not m.store._attested_fields(U, "episode", "ep-e")              # the attestation names no field
    full = tmp_path / "full.jsonl"
    m.store.add_episode(Episode(id="ep-c", user_id=U, date="2026-10-01", summary="x", provenance=tt._prov()))
    m.redact(U, episode_id="ep-c", reason="subject_request")
    export_memory(m.store, U, full)
    (n_c,) = [n for n in _notices(_lines(full)) if n["target_id"] == "ep-c"]
    rec = dict([r for r in _lines(full) if r.get("id") == "ep-c"][0], id="ep-e", summary=f"now carrying {SECRET}")
    notice = dict(n_c, target_id="ep-e", source_event_ref="u:elsewhere")      # a valid notice naming `summary`
    m.store.delete_episode("ep-e")
    before = {t: m.store._conn.execute(f"SELECT * FROM {t}").fetchall() for t in ("episodes", "redactions", "episode_event")}
    with pytest.raises(ValueError, match="does not attest"):
        import_memory(m.store, _write(tmp_path / "f.jsonl", _head(_lines(full)) + [rec, notice]))
    assert {t: m.store._conn.execute(f"SELECT * FROM {t}").fetchall() for t in before} == before
