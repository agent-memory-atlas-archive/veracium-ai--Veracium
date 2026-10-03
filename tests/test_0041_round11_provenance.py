"""specs/0041 round 11 — R10-04: provenance is a fact of the RECORD, never the reason text.

Round 10 read `reason == "imported_notice"` as "this redaction was witnessed, not performed here". The public
`Memory.redact` admitted that reason, so a LOCAL redaction read as witnessed: its receipt reported
`reconstructed=True` and lost its known facts, and its export wrote `marker_version=null, reason=null`, which the
importer refused. The owner ruled (2026-10-03, dev session: "Refuse it"): the public redact refuses the witness label
before any write. And provenance is now read from the record: a witnessed row is the one whose source identity
columns are set, which only the import path writes. A hand-built file can set those columns only AS a foreign
notice, so it can never make a witnessed record read as local.

Every cell goes through the real `Memory.redact` / `export_memory` / `import_memory` / `doctor.diagnose` paths.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

from veracium import redaction as R
from veracium.portability import export_memory, import_memory
from veracium.schema import Edge, Episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r11p", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r11p"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-PROVENANCE-R11"


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


def _edge_store(tmp_path, name="src.db"):
    m = tt._mem(tmp_path, name)
    m.store.add_edge(Edge(id="e-x", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    return m


# ------------------------------------------------------------------ the public operation

def test_the_witness_label_is_not_an_originating_reason():
    assert R.WITNESS_REASON == "imported_notice" and R.WITNESS_REASON in R.REDACTION_REASONS
    assert R.WITNESS_REASON not in R.ORIGINATING_REASONS
    assert set(R.ORIGINATING_REASONS) | {R.WITNESS_REASON} == set(R.REDACTION_REASONS)


def test_R10_04_memory_redact_refuses_imported_notice_before_any_write(tmp_path):
    m = _edge_store(tmp_path)
    st = m.store
    snap = {t: st._conn.execute(f"SELECT * FROM {t}").fetchall() for t in ("edges", "edge_event", "redactions")}
    with pytest.raises(ValueError, match="imported_notice"):
        m.redact(U, edge_id="e-x", reason="imported_notice")
    assert {t: st._conn.execute(f"SELECT * FROM {t}").fetchall() for t in snap} == snap


@pytest.mark.parametrize("reason", R.ORIGINATING_REASONS)
def test_R10_04_every_admitted_local_reason_round_trips(tmp_path, reason):
    """The reviewer's sweep, over the COMPLETE admitted set: a local redaction keeps its known facts in its receipt
    and its export, and a restore of that export into an empty store succeeds."""
    m = _edge_store(tmp_path)
    first = m.redact(U, edge_id="e-x", reason=reason)
    again = m.redact(U, edge_id="e-x", reason=reason)
    for r in (first, again):
        assert r.reconstructed is False and r.reason == reason and r.marker_version == R.MARKER_VERSION
        assert r.event_ref is not None and r.store_version_before is not None and r.recorded_at is not None
    p = tmp_path / "x.jsonl"
    export_memory(m.store, U, p)
    (n,) = _notices(_lines(p))
    assert n["reason"] == reason and n["marker_version"] == R.MARKER_VERSION and n["origin"] == m.store.local_origin()
    dst = tt._mem(tmp_path, "dst.db")
    r = import_memory(dst.store, p, restore=True)
    assert r["notices_applied"] == 1


def test_R10_04_a_LOCAL_row_holding_the_witness_label_still_reads_local(tmp_path):
    """The discriminator itself. Round 10's public redact wrote local rows whose reason IS the witness label; the label
    is now refused at the operation, so such a row exists only as an earlier build left it — modelled here by setting
    that one column on a genuine local redaction. Provenance is read from the RECORD (no source identity), so the
    receipt keeps every known local fact and the export carries them, never the null body round 10 emitted."""
    m = _edge_store(tmp_path)
    m.redact(U, edge_id="e-x", reason="subject_request")
    m.store._conn.execute("UPDATE redactions SET reason='imported_notice'")     # the row round 10's build wrote
    m.store._conn.commit()
    rec = m.redact(U, edge_id="e-x", reason="subject_request")
    assert rec.repeated and rec.reconstructed is False
    assert rec.marker_version == R.MARKER_VERSION and rec.event_ref is not None and rec.recorded_at is not None
    p = tmp_path / "x.jsonl"
    export_memory(m.store, U, p)
    (n,) = _notices(_lines(p))
    assert n["marker_version"] == R.MARKER_VERSION and n["recorded_at"] is not None and n["origin"] == m.store.local_origin()


def test_control_a_genuine_imported_notice_keeps_the_sources_facts(tmp_path):
    m = _edge_store(tmp_path)
    m.redact(U, edge_id="e-x", reason="legal_obligation")
    p = tmp_path / "x.jsonl"
    export_memory(m.store, U, p)
    (n,) = _notices(_lines(p))
    dst = _edge_store(tmp_path, "dst.db")
    import_memory(dst.store, p)
    rec = dst.redact(U, edge_id="e-x", reason="subject_request")        # the repeat returns the attestation's receipt
    assert rec.repeated and rec.reconstructed is True and rec.reason == "legal_obligation"
    assert rec.event_ref == n["source_event_ref"] and rec.recorded_at == n["recorded_at"]
    assert rec.applied_event_ref is not None


# ------------------------------------------------------------------ a hand-built file cannot make a witnessed record read local

def test_R10_04_a_hand_built_notice_claiming_this_stores_own_identity_still_reads_as_witnessed(tmp_path):
    """The file names the DESTINATION's own origin, user and an event-ref shape of its own: it is still a notice this
    store was TOLD about — the record's source columns are set, the receipt is reconstructed, the export relays the
    file's claim unchanged rather than re-stating it as this store's act."""
    src = _edge_store(tmp_path)
    src.redact(U, edge_id="e-x", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = _lines(p)
    dst = _edge_store(tmp_path, "dst.db")
    (n0,) = _notices(recs)
    forged = dict(n0, origin=dst.store.local_origin(), source_user=U, source_event_ref=f"{U}:1")
    import_memory(dst.store, _write(tmp_path / "f.jsonl", _head(recs) + [forged]))
    held = dst.store._conn.execute("SELECT source_origin, source_user, source_event_ref FROM redactions").fetchone()
    assert held == (dst.store.local_origin(), U, f"{U}:1")
    rec = dst.redact(U, edge_id="e-x", reason="subject_request")
    assert rec.repeated and rec.reconstructed is True
    out = tmp_path / "relay.jsonl"
    export_memory(dst.store, U, out)
    (rel,) = _notices(_lines(out))
    assert (rel["origin"], rel["source_user"], rel["source_event_ref"]) == (forged["origin"], U, f"{U}:1")
    assert rel["reason"] == forged["reason"] and rel["recorded_at"] == forged["recorded_at"]


@pytest.mark.parametrize("extra", [{"source_body": None}, {"source_origin": None}, {"id": "rd-0"}, {"event_ref": None}])
def test_R10_04_a_hand_built_notice_cannot_clear_its_own_provenance(tmp_path, extra):
    """Keys naming the representation itself, set to the LOCAL shape: either refused before any write, or ignored —
    never a record that reads as this store's own redaction."""
    src = _edge_store(tmp_path)
    src.redact(U, edge_id="e-x", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = _lines(p)
    (n0,) = _notices(recs)
    dst = _edge_store(tmp_path, "dst.db")
    try:
        import_memory(dst.store, _write(tmp_path / "f.jsonl", _head(recs) + [dict(n0, **extra)]))
    except ValueError:
        assert dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0
        return
    (src_origin,) = dst.store._conn.execute("SELECT source_origin FROM redactions").fetchone()
    assert src_origin == n0["origin"]
    assert dst.redact(U, edge_id="e-x", reason="subject_request").reconstructed is True


def test_R10_04_a_notice_whose_own_reason_is_the_witness_label_is_refused(tmp_path):
    """A notice's reason is the SOURCE's, and a source originates a redaction with an originating reason; a body
    claiming `imported_notice` is refused with nothing written."""
    src = _edge_store(tmp_path)
    src.redact(U, edge_id="e-x", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = _lines(p)
    (n0,) = _notices(recs)
    dst = tt._mem(tmp_path, "dst.db")
    with pytest.raises(ValueError):
        import_memory(dst.store, _write(tmp_path / "f.jsonl", _head(recs) + [dict(n0, reason="imported_notice")]))
    assert dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0


# ------------------------------------------------------------------ the doctor reads the same fact

def test_the_doctor_calls_a_notice_standing_by_its_missing_event_and_never_a_local_row(tmp_path):
    from veracium import doctor as doc
    src = tt._mem(tmp_path, "src.db")
    src.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-10-01", summary=SECRET, provenance=tt._prov()))
    src.redact(U, episode_id="ep-1", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = _lines(p)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, _write(tmp_path / "n.jsonl", _head(recs) + _notices(recs)))     # standing
    dst.close()
    rep = doc.diagnose(str(tmp_path / "dst.db"))
    assert not [f for f in rep.findings if f.level == "error"] and \
        any("standing redaction notice" in f.message for f in rep.findings)
    src.store.delete_episode("ep-1")                            # a LOCAL attestation whose target is gone
    src.close()
    rep = doc.diagnose(str(tmp_path / "src.db"))
    # a LOCAL row is never called standing, whatever its reason (its event exists); how the doctor grades a deleted
    # attested target is not this cell's claim
    assert not any("standing redaction notice" in f.message for f in rep.findings)
