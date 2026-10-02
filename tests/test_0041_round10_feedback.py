"""specs/0041 round 10 — dispute, record_outcome and correct read, judge and quote the record INSIDE one write
transaction (`store.atomic()`), and refuse an attested target before writing anything (sweep A's A2, A3, A4); and the
outcome chain's compare-and-set holds across connections (found while fixing A3).

The interleaving instruments are the ones tests/test_0041_round10_txn.py established: SEQUENTIAL (the other
connection commits before this one's transaction begins) and BLOCKED (this connection holds BEGIN IMMEDIATE, the other
connection's write is observed not to complete).
"""
import contextlib
import importlib.util
import json
import pathlib
import sys
import threading

import pytest

from veracium import graph, redaction as R
from veracium.schema import Disclosure, Edge, EvidenceAuthor, OutcomeJudgmentDraft, Outcome, Provenance
from veracium.store.base import HEAD_MOVED

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


tt = _load("tt41_r10fb", ROOT / "tests" / "test_0041_transition_table.py")
txn = _load("txn41_r10fb", ROOT / "tests" / "test_0041_round10_txn.py")

U = "u"
SECRET = "SECRET-FEEDBACK-4471"
OPS = {
    "dispute": lambda m: m.dispute(U, "e-1", reason="wrong"),
    "record_outcome": lambda m: m.record_outcome(U, "e-1", outcome="challenged", evidence_ref="ctx", actor="system"),
    "correct": lambda m: m.correct(U, "e-1", "somewhere else"),
}


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)


def _pair(tmp_path):
    a, b = tt._mem(tmp_path, "fb.db"), tt._mem(tmp_path, "fb.db")
    a.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="lives_at", object=SECRET,
                          note="note " + SECRET, provenance=_prov()))
    return a, b


def _snapshot(st):
    return [st._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("episodes", "edges")]


def _carriers(st):
    return [t for t in ("episodes", "edges") if any(SECRET in r[-1] for r in st._conn.execute(f"SELECT * FROM {t}"))]


@pytest.mark.parametrize("op", sorted(OPS))
def test_sequential_a_redaction_committed_before_the_operation_begins_refuses_it_and_writes_nothing(tmp_path, op):
    a, b = _pair(tmp_path)
    fired = txn._on_write_txn_entry(a.store, lambda: b.redact(U, edge_id="e-1", reason="subject_request"))
    episodes_before = a.store._conn.execute("SELECT * FROM episodes ORDER BY 1").fetchall()
    with pytest.raises(ValueError, match="is redacted"):
        OPS[op](a)
    # the operation wrote NOTHING (an edge redaction adds no episode), and no carrier holds the content
    assert fired and a.store._conn.execute("SELECT * FROM episodes ORDER BY 1").fetchall() == episodes_before
    assert _carriers(a.store) == []


@pytest.mark.parametrize("op", sorted(OPS))
def test_blocked_a_redaction_racing_the_operation_waits_for_it(tmp_path, op):
    """A holds BEGIN IMMEDIATE while it reads the record; B's redaction is observed NOT to complete until A commits,
    then treats the record. The record A quoted was unredacted when A read it — the ordering is serial."""
    a, b = _pair(tmp_path)
    other = txn._Blocked(b.store, lambda: b.redact(U, edge_id="e-1", reason="subject_request"))
    blocked = []
    real, in_txn = a._find_edge, []

    def paused(user_id, edge_id):                                  # the Memory reads; its STORE holds the transaction
        got = real(user_id, edge_id)
        if not in_txn:
            in_txn.append(a.store._conn.in_transaction)
            blocked.append(other.start_and_observe())
        return got
    a._find_edge = paused
    OPS[op](a)
    other.finish()
    assert in_txn == [True] and blocked == [True]
    assert json.loads(a.store._conn.execute("SELECT json FROM edges WHERE id='e-1'").fetchone()[0])["object"] == R.MARKER


@pytest.mark.parametrize("op", sorted(OPS))
def test_an_already_redacted_target_is_refused_with_nothing_written(tmp_path, op):
    """No race: record_outcome used to append its outcome episode and then have the edge write refused (a partial
    write). Every operation now refuses first."""
    a, _b = _pair(tmp_path)
    a.redact(U, edge_id="e-1", reason="subject_request")
    before = _snapshot(a.store)
    with pytest.raises(ValueError, match="is redacted"):
        OPS[op](a)
    assert _snapshot(a.store) == before


@pytest.mark.parametrize("op", sorted(OPS))
def test_control_an_unredacted_target_is_processed(tmp_path, op):
    a, _b = _pair(tmp_path)
    OPS[op](a)
    assert _carriers(a.store)                                     # the user's own content, quoted as before


def test_atomic_mid_dispute_another_connection_still_sees_the_record_active(tmp_path):
    """Atomicity by BEHAVIOUR: inside dispute, after the invalidation and before the episode, a second connection
    reads the record and sees it ACTIVE — the invalidation has not committed on its own."""
    a, b = _pair(tmp_path)
    real, seen = a.store.add_episode, []

    def peek(ep):
        seen.append(json.loads(b.store._conn.execute("SELECT json FROM edges WHERE id='e-1'").fetchone()[0])
                    .get("invalidated_at"))
        return real(ep)
    a.store.add_episode = peek
    a.dispute(U, "e-1", reason="wrong")
    assert seen == [None]                                          # B saw it active mid-operation
    assert json.loads(b.store._conn.execute("SELECT json FROM edges WHERE id='e-1'").fetchone()[0])["invalidated_at"]


def test_a_refused_correction_still_commits_its_durable_refusal_row(tmp_path):
    """specs/0011 §4b inside the atomic scope: the refusal is raised AFTER the scope, so the durable row commits."""
    a, _b = _pair(tmp_path)
    a.store.add_edge(Edge(id="e-o", user_id=U, subject="user's sister", relation="lives_in", object="Berlin",
                          provenance=_prov()))
    with pytest.raises(graph.CorrectionRefused):
        a.correct(U, "e-o", "Paris")
    assert a.store._conn.execute("SELECT COUNT(*) FROM supersession_refusals WHERE prior_edge_id='e-o'").fetchone()[0] == 1


def test_A4_correct_refuses_by_the_attestation_record_not_by_the_subject_marker(tmp_path, monkeypatch):
    """The sweep's mutant: a treatment that leaves subject/relation used to let correct() through (it was closed only
    because the marker broke the scope read). The refusal is now the attestation record's."""
    a, b = _pair(tmp_path)
    monkeypatch.setattr(R, "EDGE_REPLACE", tuple(f for f in R.EDGE_REPLACE if f not in ("subject", "relation")))
    b.redact(U, edge_id="e-1", reason="subject_request")
    before = _snapshot(a.store)
    with pytest.raises(ValueError, match="is redacted"):
        a.correct(U, "e-1", "somewhere else")
    assert _snapshot(a.store) == before and _carriers(a.store) == []


def test_the_outcome_chain_cas_holds_across_two_connections(tmp_path):
    """Found while fixing A3: the head read and the INSERT ran under the instance lock only, which serialises ONE
    connection. Two connections appending to the same empty chain: the second is now HEAD_MOVED, never a fork."""
    a, b = _pair(tmp_path)
    draft = OutcomeJudgmentDraft(author=EvidenceAuthor.SYSTEM, event_timestamp="2026-09-01", outcome=Outcome.CHALLENGED,
                                 summary="s", context_ref=None)
    holder = {}
    other = txn._Blocked(b.store, lambda: holder.setdefault("r", b.store.append_outcome_if_head(U, "e-1", "ctx", None, draft)))
    blocked = []
    in_txn = txn._pause_inside(a.store, "_chain_head", lambda: blocked.append(other.start_and_observe()))
    first = a.store.append_outcome_if_head(U, "e-1", "ctx", None, draft)
    other.finish()
    assert in_txn == [True] and blocked == [True]
    assert first is not HEAD_MOVED and holder["r"] is HEAD_MOVED
    heads = a.store._conn.execute("SELECT COUNT(*) FROM episodes WHERE json LIKE '%\"kind\":\"outcome\"%'").fetchone()[0]
    assert heads == 1                                              # one link, not two roots
