"""specs/0041 round 12 — R11-02: "nothing to redact" is decided over the WHOLE treatment surface.

Round 11 decided it from the LIVE record alone, before the journal and the side tables were read: an edge emptied by
an ordinary write — whose journal, confirmation digest or ledger digests still carry its content — was refused, and
those carriers were left. Now the decision is taken at the END of the treatment, over everything it reached, inside the
transaction (a refusal rolls every statement back, so nothing is written); and the journal tombstone is recorded as the
bookkeeping path `journal.state` (the journal named, not its table — V-INERT) when it changed a prior state, so a
history-only edge attests a NON-empty field set its export carries and another store imports. The owner's ruling stands as given: a record with no covered content or
marker ANYWHERE is refused. Every cell runs the real writers (`add_edge`, `confirm`, the native absorption) and
`Memory.redact`; SQL is read-only.
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
_spec = importlib.util.spec_from_file_location("tt41_r12s", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r12s"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-SURFACE-R12"


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


def _journal(st, eid="t"):
    return [s for (s,) in st._conn.execute("SELECT state FROM edge_event WHERE edge_id=? ORDER BY seq", (eid,))]


def _content_in_journal(st, eid="t"):
    return sum(SECRET in (s or "") for s in _journal(st, eid))


def _emptied(tmp_path, prep=lambda m: None, name="m.db"):
    m = tt._mem(tmp_path, name)
    m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    prep(m)
    m.store.add_edge(Edge(id="t", user_id=U, subject="", relation="", object="", provenance=tt._prov()))
    assert _content_in_journal(m.store) >= 1                    # the journal still carries it: the precondition
    return m


def test_R11_02_empty_live_record_with_retained_carriers_can_be_redacted(tmp_path):
    m = _emptied(tmp_path)
    rec = m.redact(U, edge_id="t", reason="subject_request")
    assert _content_in_journal(m.store) == 0
    assert "journal.state" in rec.fields_cleared and rec.fields_cleared
    assert set(rec.fields_cleared) <= R.attestation_paths("edge")


def test_R11_02_the_confirmation_digest_of_an_emptied_edge_is_treated(tmp_path):
    m = _emptied(tmp_path, lambda m: m.confirm(U, "t"))
    rec = m.redact(U, edge_id="t", reason="subject_request")
    dg = m.store._conn.execute("SELECT request_digest FROM confirmations WHERE edge_id='t'").fetchone()[0]
    assert dg == R.MARKER and "confirmations.request_digest" in rec.fields_cleared and _content_in_journal(m.store) == 0


def test_the_ledger_digests_of_an_emptied_survivor_are_treated(tmp_path):
    from veracium import graph as _graph
    from veracium.compile import DEFAULT_RELATIONS
    m = tt._mem(tmp_path, "m.db")
    m.store.add_edge(Edge(id="e-prior", user_id=U, subject="user", relation="lives_in", object="Berlin",
                          provenance=tt._prov(source_id="src-a", evidence_ref="ev-a")))
    _graph.apply_supersession(m.store, Edge(id="t", user_id=U, subject="user", relation="lives_in", object="Berlin Mitte",
                                            provenance=tt._prov(source_id="src-a", evidence_ref="ev-b")), DEFAULT_RELATIONS)
    q = "SELECT COUNT(*) FROM contribution_ledger WHERE survivor_id='t' AND identity_digest IS NOT NULL"
    assert m.store._conn.execute(q).fetchone()[0], "no digest-bearing ledger row: the cell would measure nothing"
    m.store.add_edge(Edge(id="t", user_id=U, subject="", relation="", object="",
                          provenance=tt._prov(source_id="src-a", evidence_ref="ev-b")))
    rec = m.redact(U, edge_id="t", reason="subject_request")
    assert m.store._conn.execute(q).fetchone()[0] == 0 and "contribution_ledger.identity_digest" in rec.fields_cleared


@pytest.mark.parametrize("restore", [False, True])
def test_a_history_only_redaction_exports_a_notice_another_store_applies(tmp_path, restore):
    m = _emptied(tmp_path)
    m.redact(U, edge_id="t", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(m.store, U, p)
    (n,) = [r for r in _lines(p) if r.get("record") == "redaction"]
    assert n["fields"] and "journal.state" in n["fields"]
    dst = _emptied(tmp_path, name="dst.db")                     # the destination holds the same history
    import_memory(dst.store, p, restore=restore)
    assert dst.store._attested_fields(U, "edge", "t") and _content_in_journal(dst.store) == 0


def test_a_notice_WITHOUT_the_journal_path_still_treats_the_destinations_journal(tmp_path):
    """Research's cell (b): the new path is an ADDITION, never a requirement — an older notice naming only the
    record's carriers still makes the destination tombstone its journal (its own treatment does)."""
    src = tt._mem(tmp_path, "src.db")
    src.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    src.redact(U, edge_id="t", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = _lines(p)
    (n,) = [r for r in recs if r.get("record") == "redaction"]
    dst = tt._mem(tmp_path, "dst.db")
    dst.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    head = [r for r in recs if r.get("kind") == "veracium-export"]
    # the OLDER form, built explicitly: the record's carriers only, as every round-11 notice was
    import_memory(dst.store, _write(tmp_path / "n.jsonl", head + [dict(n, fields=["object", "relation", "subject"])]))
    assert _content_in_journal(dst.store) == 0


def test_a_record_with_nothing_anywhere_is_still_refused_with_nothing_written(tmp_path):
    m = tt._mem(tmp_path, "m.db")
    m.store.add_episode(Episode(id="ep-e", user_id=U, date="2026-10-01", summary="", provenance=tt._prov()))
    snap = {t: m.store._conn.execute(f"SELECT * FROM {t}").fetchall() for t in ("episodes", "episode_event", "redactions")}
    with pytest.raises(ValueError, match="nothing to redact"):
        m.redact(U, episode_id="ep-e", reason="subject_request")
    assert {t: m.store._conn.execute(f"SELECT * FROM {t}").fetchall() for t in snap} == snap


def test_control_a_populated_edge_treats_its_journal_and_its_digest(tmp_path):
    """BEHAVIOUR, which held before this round too: a populated edge's redaction tombstones the journal and replaces
    the confirmation digest."""
    m = tt._mem(tmp_path, "m.db")
    m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    m.confirm(U, "t")
    m.redact(U, edge_id="t", reason="subject_request")
    dg = m.store._conn.execute("SELECT request_digest FROM confirmations WHERE edge_id='t'").fetchone()[0]
    assert _content_in_journal(m.store) == 0 and dg == R.MARKER


def test_a_populated_edge_attests_the_journal_it_tombstoned(tmp_path):
    """REPRESENTATION (new this round): the tombstone is recorded as the bookkeeping path `journal.state`."""
    m = tt._mem(tmp_path, "m.db")
    m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    m.confirm(U, "t")
    rec = m.redact(U, edge_id="t", reason="subject_request")
    assert {"subject", "relation", "object", "confirmations.request_digest", "journal.state"} <= set(rec.fields_cleared)
