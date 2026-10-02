"""specs/0041 round 10 — P-TXN: a decision about the STORED state is made under BEGIN IMMEDIATE on the writing
connection, in the same transaction as the write (round-9 finding R9-01, its X21 sibling, and sweep A's
consolidation instance).

Two real connections (two `Memory` instances on one database file) and deterministic hooks — no sleeps decide an
outcome. Each interleaving cell OBSERVES which ordering it ran:

* SEQUENTIAL — the other connection commits before this one's transaction begins (the hook sits at the entry of
  `_write_txn`). The fixed code sees the commit and refuses; the pre-fix code had already decided.
* BLOCKED — this connection holds BEGIN IMMEDIATE and is paused at its in-transaction read; the other
  connection's write runs on its own thread and is observed NOT to have committed while the lock is held (an
  event marks it at its own BEGIN; a bounded join can only report "still blocked"). Then this connection commits
  and the other proceeds. The pre-fix code read outside any transaction, so the other write completed inside the
  pause and the end state differs.
"""
import contextlib
import importlib.util
import json
import pathlib
import sys
import threading
from datetime import datetime, timezone

import pytest

from veracium import redaction as R
from veracium.lifecycle import consolidate
from veracium.schema import Disclosure, Episode, EvidenceAuthor, Provenance

_spec = importlib.util.spec_from_file_location(
    "tt41_r10txn", pathlib.Path(__file__).resolve().parent / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r10txn"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-R10-4471"
NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)


def _pair(tmp_path):
    return tt._mem(tmp_path, "r10.db"), tt._mem(tmp_path, "r10.db")


def _summary(st, eid):
    row = st._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    return None if row is None else json.loads(row[0])["summary"]


def _claimed_by(st, eid):
    row = st._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    return None if row is None else json.loads(row[0]).get("claimed_by")


def _on_write_txn_entry(store, action):
    """Run `action` once, at the ENTRY of `store._write_txn` — before its BEGIN IMMEDIATE."""
    real, fired = store._write_txn, []

    @contextlib.contextmanager
    def hooked():
        if not fired:
            fired.append(action())
        with real():
            yield
    store._write_txn = hooked
    return fired


class _Blocked:
    """Runs `fn` on its own thread; `.at_begin` is set when that thread enters its store's `_write_txn` (just
    before BEGIN IMMEDIATE). `.observe()` waits for that point, then reports whether the thread is still running."""

    def __init__(self, store, fn):
        self.at_begin, self.result, self.error = threading.Event(), None, None
        real = store._write_txn

        @contextlib.contextmanager
        def marked():
            self.at_begin.set()
            with real():
                yield
        store._write_txn = marked
        self.thread = threading.Thread(target=self._run, args=(fn,), daemon=True)

    def _run(self, fn):
        try:
            self.result = fn()
        except Exception as e:                       # noqa: BLE001 — the outcome is asserted by the caller
            self.error = e

    def start_and_observe(self):
        self.thread.start()
        assert self.at_begin.wait(5), "the other connection never reached its BEGIN IMMEDIATE"
        self.thread.join(0.3)                        # it cannot finish while we hold the lock
        return self.thread.is_alive()

    def finish(self):
        self.thread.join(10)
        assert not self.thread.is_alive()
        if self.error is not None:
            raise self.error
        return self.result


def _pause_inside(store, attr, on_pause):
    """Wrap `store.<attr>` so its FIRST call runs the real read, then `on_pause()`, then returns the read."""
    real, seen = getattr(store, attr), []

    def hooked(*a, **kw):
        got = real(*a, **kw)
        if not seen:
            seen.append(store._conn.in_transaction)
            on_pause()
        return got
    setattr(store, attr, hooked)
    return seen


# ------------------------------------------------------------------------------------------------ R9-01
def _ep(summary):
    return Episode(id="ep-1", user_id=U, date="2026-09-01", summary=summary, provenance=_prov())


def test_R9_01_sequential_a_redaction_committed_before_the_write_begins_is_seen_and_refuses(tmp_path):
    a, b = _pair(tmp_path)
    a.store.add_episode(_ep(SECRET))
    fired = _on_write_txn_entry(a.store, lambda: b.store.redact(U, episode_id="ep-1", reason="subject_request"))
    with pytest.raises(ValueError, match="is redacted"):
        a.store.add_episode(_ep(SECRET))
    assert fired and fired[0].repeated is False                       # the ordering this cell ran: B first
    assert _summary(b.store, "ep-1") == R.MARKER
    again = b.store.redact(U, episode_id="ep-1", reason="subject_request")
    assert again.repeated is True and _summary(b.store, "ep-1") == R.MARKER


def test_R9_01_blocked_the_redaction_waits_for_the_write_then_treats_what_it_wrote(tmp_path):
    a, b = _pair(tmp_path)
    a.store.add_episode(_ep("first version"))
    other = _Blocked(b.store, lambda: b.store.redact(U, episode_id="ep-1", reason="subject_request"))
    blocked = []
    in_txn = _pause_inside(a.store, "_attested_fields", lambda: blocked.append(other.start_and_observe()))
    a.store.add_episode(_ep(SECRET))                                  # A's ordinary write commits
    receipt = other.finish()
    assert in_txn == [True], "A's attestation read must run inside its write transaction"
    assert blocked == [True], "B's redaction must not complete while A holds BEGIN IMMEDIATE"
    assert receipt.repeated is False
    assert _summary(a.store, "ep-1") == R.MARKER                      # B's treatment over A's row
    assert SECRET not in json.dumps(a.store._conn.execute("SELECT json FROM episodes").fetchall())


def test_R9_01_control_ordinary_episode_writes_still_work(tmp_path):
    a, _ = _pair(tmp_path)
    a.store.add_episode(_ep("one"))
    a.store.add_episode(_ep("two"))                                   # an ordinary overwrite of an unattested row
    assert _summary(a.store, "ep-1") == "two"


# ------------------------------------------------------------------------------------------------ X21 sibling
def test_X21_blocked_a_claim_waits_for_the_write_and_is_not_overwritten_by_it(tmp_path):
    a, b = _pair(tmp_path)
    a.store.add_episode(_ep("v1"))
    holder = {}
    other = _Blocked(b.store, lambda: holder.setdefault(
        "op", b.store.create_or_takeover_consolidation(U, ["ep-1"], "w-b", 60)))
    blocked = []
    in_txn = _pause_inside(a.store, "_reserved_ids", lambda: blocked.append(other.start_and_observe()))
    a.store.add_episode(_ep("v2"))
    other.finish()
    op = holder["op"]
    assert in_txn == [True] and blocked == [True]
    assert op is not None and _claimed_by(a.store, "ep-1") == op.operation_id   # the claim survives A's write
    assert _summary(a.store, "ep-1") == "v2"


def test_X21_sequential_a_claim_committed_before_the_write_begins_refuses_it(tmp_path):
    a, b = _pair(tmp_path)
    a.store.add_episode(_ep("v1"))
    _on_write_txn_entry(a.store, lambda: b.store.create_or_takeover_consolidation(U, ["ep-1"], "w-b", 60))
    with pytest.raises(ValueError, match="reserved id"):
        a.store.add_episode(_ep("v2"))
    assert _summary(a.store, "ep-1") == "v1"


# ------------------------------------------------------------------------------------------------ A1 consolidation
def _cold(st, n=8, secret_at=3):
    for i in range(n):
        st.add_episode(Episode(id=f"ep-old-{i}", user_id=U, date=f"2026-01-{i + 1:02d}",
                               summary=f"day {i} " + (SECRET if i == secret_at else "ordinary"), provenance=_prov()))


def _echo_llm(on_call=None):
    calls = []

    def llm(prompt, system=None, role=None):
        calls.append(prompt)
        if on_call is not None and len(calls) == 1:
            on_call()
        return json.dumps({"records": [{"date": "2026-01-01", "summary": "echo: " + prompt}]})
    llm.calls = calls
    return llm


def _outputs(st):
    return [e for e in st.episodes(U) if e.lineage]


def test_A1_a_redaction_between_listing_and_claim_refuses_the_pool_and_claims_nothing(tmp_path):
    a, b = _pair(tmp_path)
    _cold(a.store, n=9)                      # nine, so the eight that remain still meet min_batch
    llm = _echo_llm(lambda: b.store.redact(U, episode_id="ep-old-3", reason="subject_request"))
    res = consolidate(a.store, llm, U, a.config, now=NOW)
    (pool,) = res["pools"].values()
    assert (pool["status"], pool.get("error")) == ("contended", "claim-contention")
    assert res["into"] == 0 and _outputs(a.store) == []
    assert all(_claimed_by(a.store, f"ep-old-{i}") is None for i in range(9))   # no leaked claim
    assert _summary(a.store, "ep-old-3") == R.MARKER
    blob = json.dumps(a.store._conn.execute("SELECT json FROM episodes").fetchall())
    assert SECRET not in blob
    # the acceptance half: the next run consolidates the remaining eight, never the redacted one
    llm2 = _echo_llm()
    res2 = consolidate(a.store, llm2, U, a.config, now=NOW)
    assert (res2["consolidated"], res2["into"]) == (8, 1)
    assert R.MARKER not in llm2.calls[0] and _summary(a.store, "ep-old-3") == R.MARKER


def test_A1_a_redaction_after_the_claim_is_refused_by_the_existing_guard(tmp_path):
    a, b = _pair(tmp_path)
    _cold(a.store)
    real, out = a.store.transition_consolidation_if_current, {}

    def after_claim(*args, **kw):
        if not out:
            try:
                out["r"] = b.store.redact(U, episode_id="ep-old-3", reason="subject_request")
            except ValueError as e:
                out["e"] = str(e)
        return real(*args, **kw)
    a.store.transition_consolidation_if_current = after_claim
    res = consolidate(a.store, _echo_llm(), U, a.config, now=NOW)
    assert "claimed by an in-flight consolidation" in out.get("e", "")
    assert (res["consolidated"], res["into"]) == (8, 1)               # the user's own content, consolidated
    assert not a.store.redacted_targets(U, "episode")


def test_A1_blocked_a_redaction_racing_the_claim_waits_and_then_refuses(tmp_path):
    a, b = _pair(tmp_path)
    _cold(a.store)
    other = _Blocked(b.store, lambda: b.store.redact(U, episode_id="ep-old-3", reason="subject_request"))
    blocked = []
    in_txn = _pause_inside(a.store, "redacted_targets", lambda: blocked.append(other.start_and_observe()))
    op = a.store.create_or_takeover_consolidation(U, [f"ep-old-{i}" for i in range(8)], "w-a", 60)
    assert in_txn == [True] and blocked == [True] and op is not None
    with pytest.raises(ValueError, match="claimed by an in-flight consolidation"):
        other.finish()
    assert not a.store.redacted_targets(U, "episode")


def test_A1_an_episode_redacted_before_the_run_is_never_a_candidate(tmp_path):
    a, _ = _pair(tmp_path)
    _cold(a.store, n=9)
    a.store.redact(U, episode_id="ep-old-3", reason="subject_request")
    llm = _echo_llm()
    res = consolidate(a.store, llm, U, a.config, now=NOW)
    assert (res["consolidated"], res["into"]) == (8, 1)
    assert R.MARKER not in llm.calls[0]
    assert _summary(a.store, "ep-old-3") == R.MARKER                 # it stays as its marker
    assert a.store.redacted_targets(U, "episode") == frozenset({"ep-old-3"})


def test_A1_control_no_redaction_is_an_ordinary_consolidation(tmp_path):
    a, _ = _pair(tmp_path)
    _cold(a.store)
    res = consolidate(a.store, _echo_llm(), U, a.config, now=NOW)
    assert (res["consolidated"], res["into"]) == (8, 1)
