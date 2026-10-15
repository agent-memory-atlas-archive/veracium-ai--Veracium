"""R-A round 2 (0045/0047 package II, T2–T4): the notice boundaries the external reviewer's RA-01 and RA-02 found.

RA-01 (0010 X21 at the treatment): an episode CLAIMED by an in-flight consolidation is changed by no treatment
caller. `redact` carried that check alone; T4's `confirm_notice`, and the import's notice treatments, reached the
shared body without it. The guard now lives in the body, `_redact_in_txn`.

RA-02 (0041 §11.6.6, INV-RR12): every `shows_redaction` decision of an import's notice phase is staged over ONE
snapshot taken before any notice treatment: the arriving copy for a record the unit carries, the held row otherwise.
One notice's treatment no longer satisfies another's predicate, and no decision depends on the order of the
notices in the file. The reviewer found the standing-arrival instance; dev found the held-restore one
(`test_held_restore_decisions_are_the_same_in_every_order`).

The reviewer's own regressions (their test_review_boundaries.py) are adapted here with their fixtures' shape. Each
operation a cell EXPECTS to succeed is an asserted permission (IO-II-7's form): a refusal there fails as an
assertion, never as an escaping exception.
"""
import itertools
import json
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig, portability
from veracium.lifecycle import consolidate
from veracium.redaction import MARKER
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance

U = "ra2-user"
_REFUSALS = (ValueError, KeyError, RuntimeError)


def _permitted(what, fn, *a, **k):
    try:
        return fn(*a, **k)
    except _REFUSALS as x:
        raise AssertionError(f"{what} was refused: {type(x).__name__}: {x}") from x


def _memory(path):
    return Memory(llm=lambda *a, **k: "", config=MemoryConfig(
        db_path=str(path), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ra2-evidence",
                      disclosure=Disclosure.MENTIONABLE)


def _add(m, kind, ident, *, note=None):
    if kind == "edge":
        m.store.add_edge(Edge(id=ident, user_id=U, subject="user", relation="likes", object="ra2-content",
                              note=note, provenance=_prov()))
    else:
        m.store.add_episode(Episode(id=ident, user_id=U, date="2026-10-15", summary="ra2-content", provenance=_prov()))


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def _records(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def _source(tmp, kind):
    """A genuine source store's export of one record, plain and then redacted: (header, the plain record, a notice)."""
    m = _memory(tmp / f"source-{kind}.db")
    try:
        _add(m, kind, "record-1", note="ra2-note" if kind == "edge" else None)
        plain = tmp / f"plain-{kind}.jsonl"
        portability.export_memory(m.store, U, plain)
        m.redact(U, **{kind + "_id": "record-1"}, reason="subject_request")
        treated = tmp / f"treated-{kind}.jsonl"
        portability.export_memory(m.store, U, treated)
    finally:
        m.close()
    p, t = _records(plain), _records(treated)
    return t[0], next(r for r in p if r.get("record") == kind), next(r for r in t if r.get("record") == "redaction")


def _state(m, table, ident):
    c = m.store._conn
    return {"record": c.execute(f"SELECT json FROM {table} WHERE id=?", (ident,)).fetchone(),
            "notices": c.execute("SELECT * FROM redactions ORDER BY id").fetchall(),
            "edge_journal": c.execute("SELECT COUNT(*) FROM edge_event").fetchone()[0],
            "episode_journal": c.execute("SELECT COUNT(*) FROM episode_event").fetchone()[0],
            "version": m.store.store_version(U)}


# ---- RA-01 ----------------------------------------------------------------------------------------------------------

def _pending_episode_notice(tmp, m):
    header, _row, n = _source(tmp, "episode")
    _permitted("importing the pending notice", m.import_memory, _write(tmp / "pending.jsonl", [header, n]))
    return m.pending_notices(U)[0]["notice_id"]


def test_confirm_notice_refuses_a_claimed_episode_across_connections_and_changes_nothing(tmp_path):
    """The reviewer's RA-01 cell, on two connections: one holds the consolidation's reservation, the other confirms.
    The refusal leaves the episode, every notice row, both journals and the store version exactly as they were."""
    db = tmp_path / "destination.db"
    a, b = _memory(db), _memory(db)
    try:
        _add(a, "episode", "record-1")
        nid = _pending_episode_notice(tmp_path, a)
        op = a.store.create_or_takeover_consolidation(U, ["record-1"], "ra2-worker", 60)
        assert op is not None and "record-1" in b.store._reserved_ids(U)
        before = _state(b, "episodes", "record-1")
        with pytest.raises(ValueError, match="in-flight consolidation"):
            b.confirm_notice(U, nid)
        assert _state(b, "episodes", "record-1") == before
        assert [p["notice_id"] for p in b.pending_notices(U)] == [nid]
        # the ordinary redaction is refused by the SAME guard (the body's), with the same words
        with pytest.raises(ValueError, match="in-flight consolidation"):
            b.redact(U, episode_id="record-1", reason="subject_request")
        assert _state(b, "episodes", "record-1") == before
    finally:
        a.close(); b.close()


def test_an_unclaimed_target_is_confirmed_and_a_repeat_is_the_original_receipt(tmp_path):
    """The controls: with no reservation the confirmation applies the notice; repeating it is the recorded receipt
    (`repeated=True`), which writes nothing."""
    m = _memory(tmp_path / "destination.db")
    try:
        _add(m, "episode", "record-1")
        nid = _pending_episode_notice(tmp_path, m)
        first = _permitted("confirming an unclaimed target", m.confirm_notice, U, nid)
        assert not first.repeated
        assert json.loads(m.store._conn.execute("SELECT json FROM episodes WHERE id='record-1'").fetchone()[0])[
            "summary"] == MARKER
        before = _state(m, "episodes", "record-1")
        again = _permitted("repeating the confirmation", m.confirm_notice, U, nid)
        assert again.repeated and _state(m, "episodes", "record-1") == before
    finally:
        m.close()


def test_no_confirmation_succeeds_while_a_running_consolidation_holds_its_input(tmp_path):
    """The reviewer's real-run interleaving (their probe_notice_consolidation.py), as a cell: the real consolidate,
    two connections, the confirmation attempted after the input claim and before the first transition. It is
    refused, the notice stays pending, and the consolidation completes. Before the fix the confirmation succeeded and
    the run then published the input's content into its output."""
    db = tmp_path / "destination.db"
    a, b = _memory(db), _memory(db)
    try:
        for i in range(8):
            ident = "record-1" if i == 3 else f"episode-{i}"
            a.store.add_episode(Episode(id=ident, user_id=U, date=f"2026-01-{i + 1:02d}",
                                        summary="RA2-SYNTHETIC-TOKEN" if i == 3 else "ordinary", provenance=_prov()))
        nid = _pending_episode_notice(tmp_path, a)
        original, observed = a.store.transition_consolidation_if_current, {}

        def interleave(*args, **kwargs):
            if not observed:
                observed["reserved"] = "record-1" in b.store._reserved_ids(U)
                try:
                    b.confirm_notice(U, nid)
                    observed["confirmed"] = True
                except ValueError as e:
                    observed["confirmed"], observed["refusal"] = False, str(e)
            return original(*args, **kwargs)

        a.store.transition_consolidation_if_current = interleave

        def echo(prompt, **kwargs):
            return json.dumps({"records": [{"date": "2026-01-01", "summary": "echo: " + prompt}]})

        consolidate(a.store, echo, U, a.config, now=datetime(2026, 10, 15, tzinfo=timezone.utc))
        assert observed["reserved"] is True
        assert observed["confirmed"] is False, "a confirmation succeeded while the consolidation held its input"
        assert "in-flight consolidation" in observed["refusal"]
        assert [p["notice_id"] for p in a.pending_notices(U)] == [nid]
    finally:
        a.close(); b.close()


def test_a_restore_that_would_treat_a_claimed_episode_refuses_the_whole_unit(tmp_path):
    """The import's notice treatments pass the same guard (research's Q1 ruling: refuse the unit, naming X21; no new
    pending reason). A trusted restore whose notice would apply to a HELD, CLAIMED episode is refused, and the unit
    writes nothing — neither the notice nor the unrelated edge beside it."""
    header, _row, n = _source(tmp_path, "episode")
    shown = {**n, "fields": ["source_revocations.reason"], "source_event_ref": "ra2-restore-event"}
    m = _memory(tmp_path / "destination.db")
    try:
        _add(m, "episode", "record-1")
        op = m.store.create_or_takeover_consolidation(U, ["record-1"], "ra2-worker", 60)
        assert op is not None
        hdr, plain_edge, _n = _source(tmp_path, "edge")
        plain_edge = {**plain_edge, "id": "unrelated-edge"}
        before = _state(m, "episodes", "record-1")
        with pytest.raises(ValueError, match="in-flight consolidation"):
            m.import_memory(_write(tmp_path / "restore.jsonl", [header, plain_edge, shown]), restore=True)
        assert _state(m, "episodes", "record-1") == before
        assert m.store._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 0
    finally:
        m.close()


# ---- RA-02 ----------------------------------------------------------------------------------------------------------

_BLOCKED = {"edge": "note", "episode": "summary"}
_SHOWN = {"edge": "object", "episode": "source_revocations.reason"}


@pytest.mark.parametrize("kind", ["edge", "episode"])
@pytest.mark.parametrize("restore", [False, True])
@pytest.mark.parametrize("with_unit_notice", [False, True])
def test_a_prior_standing_notice_is_judged_on_the_arriving_copy(tmp_path, kind, restore, with_unit_notice):
    """The reviewer's RA-02 cell (INV-RR12), both kinds × both modes, each with its single-notice control
    (`with_unit_notice=False`). A prior STANDING notice B names a carrier the arriving copy does NOT show; the unit's
    own notice A names one it does, and A's total treatment would clear B's carrier before B was judged. The whole
    unit refuses either way, and nothing is written: B stays standing, no target, the version unchanged."""
    header, row, n = _source(tmp_path, kind)
    standing = {**n, "fields": [_BLOCKED[kind]], "source_event_ref": "ra2-standing-event"}
    unit_notice = {**n, "fields": [_SHOWN[kind]], "source_event_ref": "ra2-unit-event"}
    row = {**row, _BLOCKED[kind]: "ra2-content"}
    if kind == "edge":
        row["object"] = MARKER                    # the arriving copy SHOWS A's field (object), not B's (note)
    m = _memory(tmp_path / "destination.db")
    try:
        _permitted("importing the standing notice", m.import_memory, _write(tmp_path / "standing.jsonl", [header, standing]))
        before = _state(m, "edges" if kind == "edge" else "episodes", "record-1")
        assert before["record"] is None
        unit = [header, row] + ([unit_notice] if with_unit_notice else [])
        with pytest.raises(ValueError, match="UNREDACTED"):
            m.import_memory(_write(tmp_path / "arrival.jsonl", unit), restore=restore)
        assert _state(m, "edges" if kind == "edge" else "episodes", "record-1") == before
    finally:
        m.close()


@pytest.mark.parametrize("restore", [False, True])
def test_the_standing_arrival_refusal_does_not_depend_on_the_order_of_the_units_notices(tmp_path, restore):
    """Two notices in the unit that the arriving copy shows, and a prior standing notice it does not: refused in
    BOTH orders of the unit's notices (research's permutation requirement, 2! here)."""
    header, row, n = _source(tmp_path, "edge")
    standing = {**n, "fields": ["note"], "source_event_ref": "ra2-standing-event"}
    a1 = {**n, "fields": ["object"], "source_event_ref": "ra2-unit-a1"}
    a2 = {**n, "fields": ["subject"], "source_event_ref": "ra2-unit-a2"}
    row = {**row, "note": "ra2-content", "object": MARKER, "subject": MARKER}
    for order in itertools.permutations([a1, a2]):
        m = _memory(tmp_path / f"destination-{order[0]['source_event_ref']}.db")
        try:
            _permitted("importing the standing notice", m.import_memory,
                       _write(tmp_path / "standing.jsonl", [header, standing]))
            before = _state(m, "edges", "record-1")
            with pytest.raises(ValueError, match="UNREDACTED"):
                m.import_memory(_write(tmp_path / "arrival.jsonl", [header, row, *order]), restore=restore)
            assert _state(m, "edges", "record-1") == before
        finally:
            m.close()


_HELD_RESTORE = {
    # kind: (the three notices' fields, the decision staged from the PRE-treatment held record)
    "edge": ((["source_revocations.reason"], ["note"], ["object"]), ("applied", "pending", "pending")),
    "episode": ((["source_revocations.reason"], ["summary"], ["contribution_ledger.identity_digest"]),
                ("applied", "pending", "applied")),
}


@pytest.mark.parametrize("kind", ["edge", "episode"])
def test_held_restore_decisions_are_the_same_in_every_order(tmp_path, kind):
    """dev's widening of RA-02 (demonstrated at c31bd9f before the fix): a trusted restore carrying three notices
    for ONE held record and no copy of it. Each decision reads the held record as it stood before any treatment, so
    every one of the 3! orderings yields the same states and the same report. Before the fix, a side-carrier notice
    processed first applied total treatment and turned the later notices' `pending` into `applied`."""
    header, _row, n = _source(tmp_path, kind)
    fields, expected = _HELD_RESTORE[kind]
    notices = [{**n, "fields": f, "source_event_ref": f"ra2-held-{i}"} for i, f in enumerate(fields)]
    want = {f"ra2-held-{i}": s for i, s in enumerate(expected)}
    outcomes = set()
    for order in itertools.permutations(notices):
        tag = "-".join(x["source_event_ref"][-1] for x in order)
        m = _memory(tmp_path / f"destination-{tag}.db")
        try:
            _add(m, kind, "record-1", note="ra2-note" if kind == "edge" else None)
            report = _permitted(f"the restore in order {tag}", m.import_memory,
                                _write(tmp_path / f"restore-{tag}.jsonl", [header, *order]), restore=True)
            states = dict(m.store._conn.execute("SELECT source_event_ref, state FROM redactions").fetchall())
            assert states == want, (tag, states)
            outcomes.add((report["notices_applied"], len(report["notices_not_applied"])))
        finally:
            m.close()
    assert len(outcomes) == 1, outcomes


@pytest.mark.parametrize("restore", [False, True])
def test_a_store_caller_without_the_staged_answer_is_judged_on_the_arriving_copy_too(tmp_path, restore):
    """The created branch's FALLBACK predicate, reached only by a store caller that does not stage `_shown` (the
    public import always stages it from the file's copy). The unit carries the record (object marked, note NOT) and
    two notices, A naming object and then B naming note. A's total treatment would clear the note before B is
    judged; judged on the arriving copy, B is unshown and the whole unit refuses."""
    header, row, n = _source(tmp_path, "edge")
    row = {**row, "note": "ra2-content", "object": MARKER}
    a = {**n, "fields": ["object"], "source_event_ref": "ra2-fallback-a"}
    b = {**n, "fields": ["note"], "source_event_ref": "ra2-fallback-b"}
    m = _memory(tmp_path / "destination.db")
    commit = m.store.commit_outcome_import_plan

    def unstaged(user_id, plan, *args, **kwargs):
        for x in plan.get("redactions", []):
            x.pop("_shown", None); x.pop("_unshown", None)
        return commit(user_id, plan, *args, **kwargs)

    m.store.commit_outcome_import_plan = unstaged
    try:
        before = _state(m, "edges", "record-1")
        with pytest.raises(ValueError, match="UNREDACTED"):
            m.import_memory(_write(tmp_path / "unstaged.jsonl", [header, row, a, b]), restore=restore)
        assert _state(m, "edges", "record-1") == before
    finally:
        m.close()


@pytest.mark.parametrize("restore", [False, True])
def test_an_arrival_under_a_completed_attestation_is_judged_on_the_copy_that_arrived(tmp_path, restore):
    """research's Q2 ruling, as a cell (it reproduced at c31bd9f: ADMITTED in both modes). This store COMPLETED a
    redaction of an episode it then deleted, and holds a STANDING notice B naming its summary. The unit carries the
    episode's plain copy beside a side-carrier notice it shows. `_treated_on_arrival` writes the attestation's treated
    shape at insert, BEFORE the notice phase; B must be judged on the copy that ARRIVED (summary unredacted), never on
    that shape, so the whole unit refuses."""
    header, row, n = _source(tmp_path, "episode")
    m = _memory(tmp_path / "destination.db")
    try:
        _add(m, "episode", "record-1")
        _permitted("the local redaction", m.redact, U, episode_id="record-1", reason="subject_request")
        _permitted("deleting the redacted episode", m.store.delete_episode, "record-1")
        standing = {**n, "fields": ["summary"], "source_event_ref": "ra2-q2-standing"}
        _permitted("importing the standing notice", m.import_memory, _write(tmp_path / "standing.jsonl", [header, standing]))
        before = _state(m, "episodes", "record-1")
        unit_notice = {**n, "fields": ["source_revocations.reason"], "source_event_ref": "ra2-q2-unit"}
        with pytest.raises(ValueError, match="UNREDACTED"):
            m.import_memory(_write(tmp_path / "arrival.jsonl", [header, row, unit_notice]), restore=restore)
        assert _state(m, "episodes", "record-1") == before
    finally:
        m.close()
