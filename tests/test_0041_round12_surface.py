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
    held, journal = _held_json(dst.store, "edge", "t"), _journal(dst.store, "t")
    r = import_memory(dst.store, p, restore=restore)
    if not restore:
        # (A) attack-shaped on the default path: a notice reaching the destination's HELD record is what the
        # 2026-10-13 notice-binding hotfix closes — not applied, the row and its journal byte-identical, no applied row (T4: the notice PENDING)
        assert _held_json(dst.store, "edge", "t") == held and _journal(dst.store, "t") == journal
        assert not dst.store._attested_fields(U, "edge", "t") and _applied_rows(dst.store, "t") == 0
        assert r["notices_applied"] == 0 and _not_applied(r, "edge", "t")
        return
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
    head = [r for r in recs if r.get("kind") == "veracium-export"]
    # the OLDER form, built explicitly: the record's carriers only, as every round-11 notice was
    older = _write(tmp_path / "n.jsonl", head + [dict(n, fields=["object", "relation", "subject"])])
    # (A) the property — an older notice naming only the record's carriers still makes the destination tombstone its
    # journal — needs the notice APPLIED: since the 2026-10-13 notice-binding hotfix that is a trusted restore whose
    # file SHOWS the redaction (the record beside the notice, treated; the fixed-point rule, both modes) ...
    (treated,) = [r for r in recs if r.get("record") == "edge" and r.get("id") == "t"]
    assert treated["object"] == R.MARKER
    dst = tt._mem(tmp_path, "dst.db")
    dst.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    ra = import_memory(dst.store, _write(tmp_path / "nt.jsonl", head + [treated, dict(n, fields=["object", "relation", "subject"])]),
                       restore=True)
    assert ra["notices_applied"] == 1 and _content_in_journal(dst.store) == 0
    # ... the notice-only file on restore no longer applies to the UNTREATED held record: reported, nothing changed ...
    rst = tt._mem(tmp_path, "rst.db")
    rst.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    held_r, journal_r = _held_json(rst.store, "edge", "t"), _journal(rst.store, "t")
    rr = import_memory(rst.store, older, restore=True)
    assert _held_json(rst.store, "edge", "t") == held_r and _journal(rst.store, "t") == journal_r
    assert rr["notices_applied"] == 0 and _applied_rows(rst.store, "t") == 0
    assert ["edge", "t", "record-not-in-file"] in [list(x) for x in rr["notices_not_applied"]]
    # ... and the default path applies nothing to the held record: its journal keeps the content, the target reported
    dflt = tt._mem(tmp_path, "dflt.db")
    dflt.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    held, journal = _held_json(dflt.store, "edge", "t"), _journal(dflt.store, "t")
    r = import_memory(dflt.store, older)
    assert _held_json(dflt.store, "edge", "t") == held and _journal(dflt.store, "t") == journal
    assert _content_in_journal(dflt.store) >= 1 and not dflt.store._attested_fields(U, "edge", "t")
    assert r["notices_applied"] == 0 and _applied_rows(dflt.store, "t") == 0 and _not_applied(r, "edge", "t")


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


def test_an_applied_notice_attests_each_path_once(tmp_path):
    """Found in the round-12 parent split: the notice's fields arrive as the hint, and the side-table and journal paths
    were appended AFTER the hint's set — so the destination's attestation listed `confirmations.request_digest` (since
    round 10) and `journal.state` (round 12) twice. Every path once, at the destination and through its relay."""
    def held(name):
        m = tt._mem(tmp_path, name)
        m.store.add_edge(Edge(id="t", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
        m.confirm(U, "t")
        return m
    src = held("src.db")
    src.redact(U, edge_id="t", reason="subject_request")
    export_memory(src.store, U, tmp_path / "x.jsonl")
    dst = held("dst.db")
    # (B) attest-once is a property of an APPLIED notice, independent of trust: the default path no longer applies a
    # notice to a held record (the 2026-10-13 notice-binding hotfix), so the property is exercised under restore
    import_memory(dst.store, tmp_path / "x.jsonl", restore=True)
    (fields,) = dst.store._conn.execute("SELECT fields FROM redactions").fetchone()
    fields = json.loads(fields)
    assert {"confirmations.request_digest", "journal.state"} <= set(fields)
    assert fields == sorted(set(fields))
