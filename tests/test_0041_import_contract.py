"""specs/0041 tranche 4b — D2 and the §4g IMPORT CONTRACT, bound: the export carries the redaction record (format
13, conditionally stamped); a notice is applied in the SAME transaction as its record; a notice for a record the
destination does not hold is a STANDING notice and the record is redacted on arrival (order independence); an
invalid notice refuses the record-and-notice unit with nothing written; two notices under one source identity with
different bodies are an integrity refusal; a held DIFFERENT version is redacted anyway and flagged; a tombstone
without a notice is admitted as an unattested marker and flagged; repeat imports are idempotent by identity; the
user remap moves the notice's subject; an older reader refuses the file; the doctor is quiet on a standing notice.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from veracium import Memory, MemoryConfig, portability as port
from veracium import redaction as R
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance
from veracium.store.sqlite import SqliteStore

U = "u"


def _quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def _mem(tmp_path, name):
    return Memory(llm=_quiet, config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                                                  scope_groups={}, require_source_id=False))


def _prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw); return Provenance(**base)


def _lines(p):
    return [json.loads(l) for l in pathlib.Path(p).read_text().splitlines() if l.strip()]


def _source(tmp_path):
    """A source store with one redacted edge, one redacted episode, one ordinary edge."""
    m = _mem(tmp_path, "src.db"); st = m.store
    st.add_edge(Edge(id="e-red", user_id=U, subject="user", relation="works_as", object="night auditor at the Grand", provenance=_prov()))
    st.add_edge(Edge(id="e-ok", user_id=U, subject="user", relation="lives_in", object="Porto", provenance=_prov()))
    st.add_episode(Episode(id="ep-red", user_id=U, date="2026-09-01", summary="the user works nights at the Grand", provenance=_prov()))
    m.redact(U, edge_id="e-red", reason="subject_request"); m.redact(U, episode_id="ep-red", reason="operator_policy")
    return m


# -------------------------------------------------------------------------------------------- D2: the export
def test_the_export_carries_one_redaction_line_per_record_stamped_13_and_no_digest(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"
    r = port.export_memory(m.store, U, p)
    lines = _lines(p)
    assert lines[0]["version"] == 13 and r["redactions"] == 2
    notices = [l for l in lines[1:] if l.get("record") == "redaction"]
    assert {(n["target_kind"], n["target_id"]) for n in notices} == {("edge", "e-red"), ("episode", "ep-red")}
    for n in notices:
        assert n["origin"] == m.store.local_origin() and n["source_user"] == U and n["source_event_ref"]
        assert n["reason"] in R.REDACTION_REASONS and n["marker_version"] == R.MARKER_VERSION and n["fields"]
        assert not any(len(v) == 64 and all(c in "0123456789abcdef" for c in v) for v in n.values() if isinstance(v, str))
    text = p.read_text()
    assert "Grand" not in text                                                # the content travels redacted
    # the conditional stamp: a store without a redaction record still exports the producer era
    m2 = _mem(tmp_path, "plain.db"); m2.store.add_edge(Edge(id="e1", user_id=U, subject="user", relation="lives_in", object="Porto", provenance=_prov()))
    port.export_memory(m2.store, U, tmp_path / "plain.jsonl")
    assert _lines(tmp_path / "plain.jsonl")[0]["version"] < 13


def test_an_older_reader_refuses_a_file_that_carries_a_notice(tmp_path, monkeypatch):
    """The refuse-don't-drop rule: a reader that dropped the notice would import the record un-redacted."""
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    monkeypatch.setattr(port, "FORMAT_VERSION", 12)
    dst = _mem(tmp_path, "dst.db")
    with pytest.raises(ValueError, match="newer"):
        port.import_memory(dst.store, p, restore=True)
    assert dst.store._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0


# ------------------------------------------------------------------------------------ §4g: held → the same transaction
def test_a_held_record_and_its_notice_commit_together_and_the_destination_attests_it(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    dst = _mem(tmp_path, "dst.db")
    r = port.import_memory(dst.store, p, restore=True)
    assert r["notices_applied"] == 2 and r["notices_standing"] == 0 and r["inconsistent_notices"] == [] and r["unattested_markers"] == []
    st = dst.store
    assert st._attested_fields(U, "edge", "e-red") >= {"subject", "relation", "object"}
    assert st._attested_fields(U, "episode", "ep-red") >= {"summary"}
    assert json.loads(st._conn.execute("SELECT json FROM edges WHERE id='e-red'").fetchone()[0])["object"] == R.MARKER
    # the destination's journal closes the record with its own redacted event; INV-11 holds at the destination
    assert [e.kind for e in st.edge_events(U, edge_id="e-red")][-1] == "redacted"
    with pytest.raises(ValueError, match="redacted"):
        st.add_edge(Edge(id="e-red", user_id=U, subject="user", relation="works_as", object="repopulated", provenance=_prov()))
    # the witnessed receipt: a repeat call returns it, reconstructed and repeated
    rec = dst.redact(U, edge_id="e-red", reason="subject_request")
    assert rec.repeated is True and rec.reconstructed is True and rec.reason == "imported_notice"
    # the row keeps the SOURCE identity, so a re-export names the original source
    port.export_memory(st, U, tmp_path / "re.jsonl")
    again = [l for l in _lines(tmp_path / "re.jsonl") if l.get("record") == "redaction" and l["target_id"] == "e-red"][0]
    assert again["origin"] == m.store.local_origin() and again["source_user"] == U


def test_repeat_imports_are_idempotent_by_source_identity(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    dst = _mem(tmp_path, "dst.db")
    port.import_memory(dst.store, p, restore=True)
    r2 = port.import_memory(dst.store, p, restore=True)
    assert r2["notices_existing"] == 2 and r2["notices_applied"] == 0
    assert dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 2
    assert dst.store._conn.execute("SELECT COUNT(*) FROM edge_event WHERE edge_id='e-red' AND kind='redacted'").fetchone()[0] == 1


# ------------------------------------------------------------------------------- §4g: absent → standing, then arrival
def _split(p, tmp_path):
    lines = _lines(p); header = lines[0]
    recs = [l for l in lines[1:] if l.get("record") != "redaction"]; nots = [l for l in lines[1:] if l.get("record") == "redaction"]
    a, b = tmp_path / "notices.jsonl", tmp_path / "records.jsonl"
    a.write_text("\n".join(json.dumps(x) for x in [header, *nots]) + "\n")
    hb = dict(header); hb["version"] = 12
    b.write_text("\n".join(json.dumps(x) for x in [hb, *recs]) + "\n")
    return a, b


def test_a_notice_before_its_record_is_a_standing_notice_and_the_record_is_redacted_on_arrival(tmp_path):
    from veracium import doctor as doc
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    notices_file, records_file = _split(p, tmp_path)
    dst = _mem(tmp_path, "dst.db")
    r1 = port.import_memory(dst.store, notices_file, restore=True)
    assert r1["notices_standing"] == 2 and r1["notices_applied"] == 0
    st = dst.store
    assert st._conn.execute("SELECT COUNT(*) FROM redactions WHERE event_ref IS NULL AND reason='imported_notice'").fetchone()[0] == 2
    dst.close()
    rep = doc.diagnose(str(tmp_path / "dst.db"))
    assert not [f for f in rep.findings if f.level == "error"], doc.render(rep)
    assert any("standing redaction notice" in f.message for f in rep.findings)
    # an ORDINARY write of a notice-covered id is refused (INV-11 keys on the attestation, standing or not)
    dst = _mem(tmp_path, "dst.db"); st = dst.store
    with pytest.raises(ValueError, match="redacted"):
        st.add_edge(Edge(id="e-red", user_id=U, subject="user", relation="works_as", object="the content again", provenance=_prov()))
    # the records arrive: redacted ON ARRIVAL, the standing rows completed in place, one row per notice
    r2 = port.import_memory(st, records_file, restore=True)
    assert r2["notices_applied"] == 2 and r2["notices_standing"] == 0
    assert st._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 2
    assert st._conn.execute("SELECT COUNT(*) FROM redactions WHERE event_ref IS NULL").fetchone()[0] == 0
    assert json.loads(st._conn.execute("SELECT json FROM edges WHERE id='e-red'").fetchone()[0])["object"] == R.MARKER
    assert json.loads(st._conn.execute("SELECT json FROM episodes WHERE id='ep-red'").fetchone()[0])["summary"] == R.MARKER
    assert "Grand" not in st._conn.execute("SELECT json FROM edges WHERE id='e-red'").fetchone()[0]


def test_the_two_orders_reach_the_same_destination_state(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    notices_file, records_file = _split(p, tmp_path)
    a = _mem(tmp_path, "a.db"); port.import_memory(a.store, notices_file, restore=True); port.import_memory(a.store, records_file, restore=True)
    b = _mem(tmp_path, "b.db"); port.import_memory(b.store, records_file, restore=True); port.import_memory(b.store, notices_file, restore=True)
    def state(st):
        return (sorted(st._conn.execute("SELECT id, json FROM edges").fetchall()),
                sorted(st._conn.execute("SELECT id, json FROM episodes").fetchall()),
                sorted(st._conn.execute("SELECT id, target_kind, target_id, fields, reason FROM redactions").fetchall()))
    assert state(a.store) == state(b.store)


# ----------------------------------------------------------------------------------- §4g: the refusals and the flags
def test_an_invalid_notice_refuses_the_record_and_notice_unit_with_nothing_written(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    lines = _lines(p)
    for mutate in (lambda n: n.update(reason="redacted: the user's HIV status"), lambda n: n.update(marker_version=99),
                   lambda n: n.update(fields="object"), lambda n: n.pop("origin")):
        ls = [dict(l) for l in lines]
        n = next(l for l in ls if l.get("record") == "redaction" and l["target_id"] == "e-red"); mutate(n)
        q = tmp_path / "bad.jsonl"; q.write_text("\n".join(json.dumps(x) for x in ls) + "\n")
        dst = _mem(tmp_path, f"dst-{abs(hash(str(mutate)))}.db")
        with pytest.raises(ValueError, match="notice"):
            port.import_memory(dst.store, q, restore=True)
        assert dst.store._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0        # the UNIT: nothing written
        assert dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0


def test_two_notices_under_one_source_identity_with_different_bodies_are_an_integrity_refusal(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    lines = _lines(p)
    n = next(l for l in lines if l.get("record") == "redaction" and l["target_id"] == "e-red")
    twin = dict(n); twin["fields"] = ["note"]
    q = tmp_path / "twin.jsonl"; q.write_text("\n".join(json.dumps(x) for x in [*lines, twin]) + "\n")
    dst = _mem(tmp_path, "dst.db")
    with pytest.raises(ValueError, match="corrupted source"):
        port.import_memory(dst.store, q, restore=True)
    assert dst.store._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0
    # the SAME notice twice is one notice
    q2 = tmp_path / "dup.jsonl"; q2.write_text("\n".join(json.dumps(x) for x in [*lines, dict(n)]) + "\n")
    r = port.import_memory(dst.store, q2, restore=True)
    assert r["notices_applied"] == 2 and dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 2


def test_a_held_different_version_is_redacted_anyway_and_flagged(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    dst = _mem(tmp_path, "dst.db"); st = dst.store
    st.add_edge(Edge(id="e-red", user_id=U, subject="user", relation="works_as", object="a DIFFERENT version of the secret", provenance=_prov()))
    r = port.import_memory(st, p, restore=True)
    assert r["inconsistent_notices"] == ["e-red"] and r["notices_applied"] == 2
    js = st._conn.execute("SELECT json FROM edges WHERE id='e-red'").fetchone()[0]
    assert "DIFFERENT" not in js and json.loads(js)["object"] == R.MARKER


def test_a_tombstone_without_a_notice_is_admitted_as_an_unattested_marker_and_flagged(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    lines = [l for l in _lines(p) if l.get("record") != "redaction"]; lines[0]["version"] = 12
    q = tmp_path / "bare.jsonl"; q.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    dst = _mem(tmp_path, "dst.db"); st = dst.store
    r = port.import_memory(st, q, restore=True)
    assert sorted(r["unattested_markers"]) == ["e-red", "ep-red"] and r["notices_applied"] == 0
    assert st._attested_fields(U, "edge", "e-red") == set()                                  # carried, not attested
    assert st.redacted_targets(U, "edge") == frozenset()                                     # no reader excludes it
    # an unattested marker row stays writable (§4b's rule holds at the destination too)
    st.add_edge(Edge(id="e-red", user_id=U, subject="user", relation="works_as", object="Porto", provenance=_prov()))


def test_an_import_may_not_repopulate_a_record_the_destination_already_redacted_without_a_notice(tmp_path):
    """INV-11 at the import boundary: the destination redacted e-red itself; a file carrying the ORIGINAL
    content for that id and no notice is refused whole."""
    src = _mem(tmp_path, "src.db"); s = src.store
    s.add_edge(Edge(id="e-red", user_id=U, subject="user", relation="works_as", object="night auditor at the Grand", provenance=_prov()))
    p = tmp_path / "plain.jsonl"; port.export_memory(s, U, p)          # exported BEFORE any redaction: plain content, no notice
    dst = _mem(tmp_path, "dst.db"); port.import_memory(dst.store, p, restore=True)
    dst.redact(U, edge_id="e-red", reason="subject_request")
    with pytest.raises(ValueError, match="repopulate"):
        port.import_memory(dst.store, p, restore=True)
    assert json.loads(dst.store._conn.execute("SELECT json FROM edges WHERE id='e-red'").fetchone()[0])["object"] == R.MARKER


def test_the_user_remap_moves_the_notice_with_the_record(tmp_path):
    m = _source(tmp_path); p = tmp_path / "u.jsonl"; port.export_memory(m.store, U, p)
    dst = _mem(tmp_path, "dst.db")
    r = port.import_memory(dst.store, p, user_id="v")
    assert r["notices_applied"] == 2
    # the remap mints fresh ids (a copy, not a move): the notice's target followed the record's new id
    st = dst.store
    new_ids = {e.id for e in st.edges("v", active_only=False, include_quarantined=True)}
    assert len(new_ids) == 2 and "e-red" not in new_ids and all(i.startswith("imp-e-") for i in new_ids)
    redacted = st.redacted_targets("v", "edge")
    assert len(redacted) == 1 and redacted <= new_ids
    (rid,) = redacted
    assert st._attested_fields("v", "edge", rid) >= {"subject", "relation", "object"}
    assert json.loads(st._conn.execute("SELECT json FROM edges WHERE id=?", (rid,)).fetchone()[0])["object"] == R.MARKER
    assert not st._attested_fields(U, "edge", "e-red") and st._conn.execute("SELECT COUNT(*) FROM redactions WHERE user_id=?", (U,)).fetchone()[0] == 0
    assert {r[0] for r in st._conn.execute("SELECT user_id FROM redactions")} == {"v"}
