"""specs/0044 §4i (with research's T7 annotation) and §4k — T7-2: `undo_restoration`, the registry verb `undo`, and
`doctor`'s refs exemption, against REAL stores.

  INV-A12  eligibility is the outcome row plus `applicable`, this restoration episode's flag, cleared terminally by
           any retirement (revoke → lift leaves the edge active and the episode ended), a redaction or erasure.
  INV-A13  per-field restore; the registry is read BEFORE the edge (a replay reads no edge row, after the edge was
           re-retired or removed); one id space with `confirm()` in both directions and under concurrency; idempotent
           without an id; a generated id takes a registry row; a call that writes nothing holds no id.
  INV-A17  (local half) an `imported` outcome is testimony: no undo, and `doctor` keeps the warning, naming it.
  INV-Q7   (for undo) after the edge's redaction a retry under the undo's id is the terminal `RequestRedacted`, for
           `undo` and for `confirm` alike, and no table keeps the undo's digest.
  §4k      `doctor`'s refs warning for an active predecessor is `info` iff a live PROOF outcome records it.
  D4       undo writes no act row and takes no act position.
  and a differential against reference model I over short sequences of undo / confirm / redact / revoke / lift.

Every mutant §6 names for these rows is run by the scratch campaign
`.claude/skills/pre-seal/impl-review/0044/t7_2_mutant_defs.py` (classified by specs/evidence/mutation_kinds.py).
"""
import importlib.util
import itertools
import json
import os
import pathlib
import random
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig, doctor
from veracium import redaction as R
from veracium.schema import as_utc_required
from veracium.store import data_migration as DM
from veracium.store import revocation as rv
from veracium.store.base import RequestRedacted, Store, UNDO_REFUSAL_REASONS, UndoRefused
from veracium.store.revocation_sweep import digest_of
from veracium.store.sqlite import SqliteStore

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


T6 = _load("t6_operation_helpers_0044", pathlib.Path(__file__).with_name("test_0044_t6_operation.py"))
U, V = T6.U, T6.V
P, N = f"p-{U}", f"n-{U}"
AT = T6.AT


def _restored(tmp_path, *, source=None, name="s.db"):
    """A real upgraded store whose `p` (retired `superseded` before the step; `source` its source, `n` sourceless)
    the data migration has RESTORED, plus a control user V."""
    edges = [T6._edge(P, "weight 78", at=T6.PRE_2050, reason="superseded", source=source),
             T6._edge(N, "weight 80", day=2, supersedes=P)] + T6._pair(V)
    p = T6._store(tmp_path, edges, name=name)
    assert T6._run(p).outcome == "migrated"
    assert T6._q(p, "SELECT outcome, applicable FROM migration_outcome WHERE edge_id=?", (P,)) == [("restored", 1)]
    return p


def _mem(p):
    return Memory(llm=lambda *a, **k: "", store=SqliteStore(p), config=MemoryConfig(db_path=p))


def _ok(fn, *a, **k):
    """A call the cell expects to SUCCEED: any raise is the property failing, read as an assertion (so a mutant's
    kill is classified, never an escaping exception — specs/evidence/mutation_kinds.py)."""
    try:
        return fn(*a, **k)
    except Exception as exc:                                       # noqa: BLE001 — the cell's subject
        raise AssertionError(f"expected success; raised {type(exc).__name__}: {exc}") from exc


def _refuses(exc_type, fn, *a, **k):
    """A call the cell expects to raise EXACTLY `exc_type` (or a subclass): anything else is an assertion."""
    try:
        fn(*a, **k)
    except exc_type as exc:
        return exc
    except Exception as exc:                                       # noqa: BLE001 — the cell's subject
        raise AssertionError(f"expected {exc_type.__name__}; raised {type(exc).__name__}: {exc}") from exc
    raise AssertionError(f"expected {exc_type.__name__}; nothing was raised")


def _undo_raw(p, edge=P, user=U, cid="c1"):
    s = SqliteStore(p)
    try:
        return s.undo_restoration(user, edge, correlation_id=cid)
    finally:
        s.close()


def _undo(p, edge=P, user=U, cid="c1"):
    return _ok(_undo_raw, p, edge, user, cid)


def _reason(p, edge=P, user=U, cid="c1"):
    return _refuses(UndoRefused, _undo_raw, p, edge, user, cid).reason


def _outcome(p, edge=P):
    return T6._q(p, "SELECT undone_at, applicable, undo_request_ref FROM migration_outcome WHERE edge_id=?", (edge,))


def _act_counter(p):
    return T6._q(p, "SELECT next_seq FROM act_counter WHERE id=1")[0][0]


def _events(p, edge=P):
    return T6._q(p, "SELECT kind, reason FROM edge_event WHERE edge_id=? ORDER BY seq", (edge,))


def _refs(p, user=None):
    return [(f.level, f.message, tuple(f.ids)) for f in doctor.diagnose(p, user=user).findings if f.check == "refs"]


# ============================================================================================ the restore itself
def test_undo_restores_the_retirement_per_field_and_nothing_else(tmp_path):
    """§4i.3 (INV-A13's per-field restore): `invalidated_at := pre_invalidated_at`, `invalidation_reason := pre_reason`, the row inactive; every
    other field as it was — including what a confirmation changed after the restoration (ordinary mutations keep
    the episode, INV-A12). One `invalidated`/`superseded` event; the outcome row records the undo; the registry row
    is `undo`, its result the outcome; no act position is taken (D4)."""
    p = _restored(tmp_path)
    m = _mem(p)
    _ok(m.confirm, U, P, correlation_id="k1")
    before = T6._json(p, P)
    a0, ev0 = _act_counter(p), len(_events(p))
    r = _undo(p)
    assert r == {"undone": P, "undone_at": r["undone_at"], "correlation_id": "c1", "replayed": False,
                 "already_undone": False}
    after = T6._json(p, P)
    assert {k for k in before if before[k] != after[k]} == {"invalidated_at", "invalidation_reason"}
    assert as_utc_required(after["invalidated_at"]) == T6.PRE_2050 and after["invalidation_reason"] == "superseded"
    assert T6._q(p, "SELECT active FROM edges WHERE id=?", (P,)) == [(0,)]
    assert _events(p)[ev0:] == [("invalidated", "superseded")]
    assert _outcome(p) == [(r["undone_at"], 0, "c1")]
    uid = T6._q(p, "SELECT outcome_uid FROM migration_outcome WHERE edge_id=?", (P,))[0][0]
    assert T6._q(p, "SELECT verb, target_edge_id, result_ref, request_digest FROM request_registry "
                    "WHERE user_id=? AND correlation_id='c1'", (U,)) == \
        [("undo", P, uid, DM.portable_uid("undo", U, P, T6._q(p, "SELECT plan_id FROM plan_header")[0][0]))]
    assert _act_counter(p) == a0                                   # D4: undo is not an act
    assert T6._q(p, "SELECT COUNT(*) FROM confirmations")[0][0] == 1


def test_undo_checks_applicable_and_refuses_when_the_hook_did_not_clear_it(tmp_path, monkeypatch):
    """Research's Q8: undo never WRITES `applicable` — the retirement's own lifetime hook clears it (§4f-ii, derived
    once) and undo writes `undone_at` only where it is cleared. With the hook broken (planted), undo refuses with
    nothing written, instead of masking the regression with a second writer of the rule."""
    p = _restored(tmp_path)
    pre = T6._durable(p)
    monkeypatch.setattr(SqliteStore, "_apply_lifetime_transition", lambda self, *a, **k: None)
    assert "was not cleared by the retirement" in str(_refuses(RuntimeError, _undo_raw, p))
    assert T6._durable(p) == pre


def test_a_naive_pre_retirement_is_restored_as_the_same_instant(tmp_path):
    """The outcome row's `pre_invalidated_at` read through the normalizer every retirement uses: a NAIVE stored
    text (a legacy representation) is restored as the same instant, in the normalized representation."""
    p = _restored(tmp_path)
    c = sqlite3.connect(p)
    c.execute("UPDATE migration_outcome SET pre_invalidated_at='2050-01-01T00:00:00' WHERE edge_id=?", (P,))
    c.commit()
    c.close()
    _undo(p)
    assert as_utc_required(T6._json(p, P)["invalidated_at"]) == datetime(2050, 1, 1, tzinfo=timezone.utc)


# ============================================================================================ replay (INV-A13)
def _deny_edge_reads(store):
    def auth(action, a1, a2, db, trig):
        return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ and a1 == "edges" else sqlite3.SQLITE_OK
    store._conn.set_authorizer(auth)


def test_a_completed_undo_replays_from_the_registry_without_reading_the_edge(tmp_path):
    p = _restored(tmp_path)
    first = _undo(p)
    s = SqliteStore(p)
    try:
        _deny_edge_reads(s)                                         # any read of `edges` now raises
        again = _ok(s.undo_restoration, U, P, correlation_id="c1")
    finally:
        s._conn.set_authorizer(None)
        s.close()
    assert again == {**first, "replayed": True}
    # the edge later re-retired by another writer, then REMOVED (planted): the replay still answers
    c = sqlite3.connect(p)
    c.execute("DELETE FROM edges WHERE id=?", (P,))
    c.commit()
    c.close()
    assert _undo(p) == {**first, "replayed": True}


def test_without_an_id_undo_is_idempotent_and_its_generated_id_takes_a_registry_row(tmp_path):
    """§4i.1 + the annotation: an id-less call generates `auto-<hex>`, which takes the registry row and is the
    outcome row's `undo_request_ref`; a second id-less call answers `already undone at T`, writes nothing and holds
    no id (its generated id is free afterwards)."""
    p = _restored(tmp_path)
    m = _mem(p)
    r1 = _ok(m.undo_restoration, U, P)
    assert r1["correlation_id"].startswith("auto-") and not r1["already_undone"]
    assert _outcome(p) == [(r1["undone_at"], 0, r1["correlation_id"])]
    pre, ev = T6._durable(p), len(_events(p))
    r2 = _ok(m.undo_restoration, U, P)
    assert r2["already_undone"] and not r2["replayed"] and r2["undone_at"] == r1["undone_at"]
    assert r2["correlation_id"] != r1["correlation_id"]
    assert T6._durable(p) == pre and len(_events(p)) == ev
    assert T6._q(p, "SELECT correlation_id FROM request_registry WHERE verb='undo'") == [(r1["correlation_id"],)]


def _versions(p):
    s = SqliteStore(p)
    try:
        return s.store_version(U), s.store_version(V)
    finally:
        s.close()


def test_undo_bumps_the_users_store_version_once_and_a_no_op_does_not(tmp_path):
    """The undo's own `_bump` is its ONLY one (`_invalidate_edge_row` runs without lock, bump or commit), and the
    counter guards 0041 §4e's wiki write: an undo moves this user's version by exactly one; a replay and an
    already-undone call move it by none; the control user's never moves (research's T7 stage-2 S3a)."""
    p = _restored(tmp_path)
    u0, v0 = _versions(p)
    _undo(p)
    assert _versions(p) == (u0 + 1, v0)
    assert _undo(p)["replayed"] and _versions(p) == (u0 + 1, v0)
    assert _undo(p, cid="c2")["already_undone"] and _versions(p) == (u0 + 1, v0)


def test_the_undo_registry_row_is_written_at_the_store_clock(tmp_path):
    """0008 v8: the registry row's `written_at` is the store clock at the write, the same instant as the outcome's
    `undone_at` — never the restored pre-state's retirement time (research's T7 stage-2 S3b). Both a supplied id and
    a generated one."""
    p = _restored(tmp_path)
    r = _undo(p)
    assert T6._q(p, "SELECT written_at FROM request_registry WHERE verb='undo' AND correlation_id='c1'") == [(r["undone_at"],)]
    assert _outcome(p)[0][0] == r["undone_at"]
    q = _restored(tmp_path, name="g.db")
    g = _ok(_mem(q).undo_restoration, U, P)
    assert T6._q(q, "SELECT written_at FROM request_registry WHERE verb='undo'") == [(g["undone_at"],)]


def test_a_fresh_id_on_an_undone_row_is_answered_and_left_free(tmp_path):
    p = _restored(tmp_path)
    _undo(p, cid="c1")
    r = _undo(p, cid="fresh")
    assert r["already_undone"] and r["correlation_id"] == "fresh"
    assert _ok(_mem(p).confirm, U, N, correlation_id="fresh")["replayed"] is False      # the id was never held


def test_the_public_verb_checks_the_id_grammar_before_any_read(tmp_path, monkeypatch):
    p = _restored(tmp_path)
    m = _mem(p)
    monkeypatch.setattr(SqliteStore, "undo_restoration", lambda *a, **k: pytest.fail("the store was reached"))
    with pytest.raises(ValueError, match="correlation_id must be"):
        m.undo_restoration(U, P, correlation_id="has space")


# ============================================================================================ eligibility (INV-A12)
def _plant(p, sql, args=()):
    c = sqlite3.connect(p)
    c.execute(sql, args)
    c.commit()
    c.close()


def test_revoke_then_lift_leaves_the_edge_active_and_the_episode_ended(tmp_path):
    """R2-04's witness: restoration → the source revoked (the sweep retires it: `applicable` cleared) → lifted (the
    edge is active again) → undo refuses `not-applicable`, and `doctor` gives no exemption."""
    p = _restored(tmp_path, source="feed-1")
    s = SqliteStore(p)
    d = digest_of(None, "feed-1", s.local_origin())
    rv.revoke_source(s, U, d, "revoke", "policy", AT)
    rv.revoke_source(s, U, d, "lift", "policy", AT)
    s.close()
    assert T6._q(p, "SELECT active FROM edges WHERE id=?", (P,)) == [(1,)]
    assert _outcome(p) == [(None, 0, None)]
    assert _reason(p) == "not-applicable"
    assert [(f[0], f[2]) for f in _refs(p, user=U)] == [("warn", (N,))]       # no exemption: the old warning


def test_an_upsert_re_retirement_ends_the_episode(tmp_path):
    """Round 3's sequence by the same-id upsert (no invalidate method): retired, then active again → refused."""
    p = _restored(tmp_path)
    s = SqliteStore(p)
    from veracium.schema import Edge
    e = Edge.model_validate_json(T6._q(p, "SELECT json FROM edges WHERE id=?", (P,))[0][0])
    s.add_edge(e.model_copy(update={"invalidated_at": T6.PRE_2050, "invalidation_reason": "superseded"}))
    s.add_edge(e)
    s.close()
    assert T6._q(p, "SELECT active FROM edges WHERE id=?", (P,)) == [(1,)]
    assert _reason(p) == "not-applicable"


def test_a_redaction_ends_the_episode(tmp_path):
    """The redaction passes the choke point and clears `applicable`, so the refusal is `not-applicable` (the
    edge-unavailable check is defensive behind it)."""
    p = _restored(tmp_path)
    s = SqliteStore(p)
    s.redact(U, edge_id=P, reason="subject_request")
    s.close()
    assert _reason(p) == "not-applicable"


def test_a_withheld_row_is_not_restored_and_erasure_leaves_no_outcome(tmp_path):
    p, d = T6._revoked_store(tmp_path)
    assert T6._run(p).outcome == "migrated"
    assert _reason(p, edge=f"p-{U}") == "not-restored"
    s = SqliteStore(p)
    s.forget_user(U)
    s.close()
    assert _reason(p, edge=f"p-{U}") == "no-outcome"


def test_an_imported_outcome_is_testimony_and_a_restored_one_is_proof(tmp_path):
    """INV-A17's local half (an imported row planted by SQL; it arrives by import at T11a): `testimony` and the
    warning naming it; the same row as `restored` (a trusted restore of this store's own outcome) is undoable, and
    before the undo `doctor` reads `info`."""
    p = _restored(tmp_path)
    _plant(p, "UPDATE migration_outcome SET origin='imported' WHERE edge_id=?", (P,))
    assert _reason(p) == "testimony"
    refs = _refs(p, user=U)
    assert [f[0] for f in refs] == ["warn"] and "IMPORTED testimony" in refs[0][1] and refs[0][2] == (N,)
    _plant(p, "UPDATE migration_outcome SET origin='restored' WHERE edge_id=?", (P,))
    assert [(f[0], f[2]) for f in _refs(p, user=U)] == [("info", (N,))]
    assert not _undo(p)["already_undone"]


def test_the_edge_unavailable_check_reads_the_users_own_row(tmp_path):
    """Defensive behind `applicable` (a removal or redaction clears it at the choke point), so both states are
    PLANTED with the flag still set: the row absent; the row carrying the marker; the row held by ANOTHER user."""
    for state in ("absent", "marker", "other-user"):
        (tmp_path / state).mkdir()
        p = _restored(tmp_path / state)
        if state == "absent":
            _plant(p, "DELETE FROM edges WHERE id=?", (P,))
        elif state == "marker":
            j = T6._json(p, P)
            j["object"] = R.MARKER
            _plant(p, "UPDATE edges SET json=? WHERE id=?", (json.dumps(j), P))
        else:
            _plant(p, "UPDATE edges SET user_id=? WHERE id=?", (V, P))
        assert _reason(p) == "edge-unavailable", state


def test_two_outcome_rows_refuse_before_the_registry(tmp_path):
    """The annotation: two rows for the user's edge (only an import can make them; planted) → `ambiguous-outcome`,
    even for an id that already completed — the digest needs the row's plan, so nothing replays."""
    p = _restored(tmp_path)
    _undo(p, cid="c1")
    _plant(p, "INSERT INTO migration_outcome(plan_id, user_id, edge_id, outcome, pre_invalidated_at, pre_reason, "
              "successor_evidence, applicable, origin, outcome_uid) VALUES('other-plan',?,?,'restored',?, "
              "'superseded','none',1,'imported','uid-other')", (U, P, AT))
    assert _reason(p, cid="c1") == "ambiguous-outcome"


def test_undo_refused_closes_its_reason_at_construction():
    for r in UNDO_REFUSAL_REASONS:
        assert UndoRefused(r, U, P, "x").reason == r
    with pytest.raises(ValueError, match="outside"):
        UndoRefused("not-a-reason", U, P, "x")


def test_a_backend_without_the_operation_refuses():
    import types
    with pytest.raises(NotImplementedError, match="does not implement undo_restoration"):
        Store.undo_restoration(types.SimpleNamespace(), U, P, correlation_id="c1")


def test_a_rerun_after_undo_restores_nothing(tmp_path):
    """INV-A9 after undo: the outcome row keeps the row from being considered again under the plan."""
    p = _restored(tmp_path)
    _undo(p)
    assert T6._run(p, op_id="op-2").outcome in ("complete", "migrated")
    assert T6._q(p, "SELECT active FROM edges WHERE id=?", (P,)) == [(0,)]


# ============================================================================================ one id space (Q1, R15)
def test_one_id_space_with_confirm_in_both_directions(tmp_path):
    """0008am INV-Q1: one id space across confirm and undo, in both directions."""
    p = _restored(tmp_path)
    m = _mem(p)
    _ok(m.confirm, U, N, correlation_id="held-by-confirm")
    assert "held by a 'confirm' request" in str(_refuses(ValueError, _undo_raw, p, cid="held-by-confirm"))
    _undo(p, cid="held-by-undo")
    with pytest.raises(ValueError, match="held by a 'undo' request"):
        m.confirm(U, N, correlation_id="held-by-undo")
    assert "DIFFERENT undo request" in str(_refuses(ValueError, _undo_raw, p, edge=f"p-{V}", user=U,
                                                    cid="held-by-undo"))


def test_a_confirm_under_an_undos_generated_id_is_refused(tmp_path):
    """0008am INV-Q1 for a GENERATED id (research's T7 re-check, 834ae72d: the cell above uses supplied ids only, and
    the differential never confirms under `auto-…`): an id-less undo's generated id is in the one shared id space, so
    a confirm under it is an integrity conflict naming `undo`, and no confirmation is admitted."""
    p = _restored(tmp_path)
    m = _mem(p)
    gen = _ok(m.undo_restoration, U, P)["correlation_id"]
    assert gen.startswith("auto-")
    n = T6._q(p, "SELECT COUNT(*) FROM confirmations")[0][0]
    assert "held by a 'undo' request" in str(_refuses(ValueError, m.confirm, U, N, correlation_id=gen))
    assert T6._q(p, "SELECT COUNT(*) FROM confirmations")[0][0] == n


def _race(p, first, second):
    """`first` runs in a thread on its own SqliteStore and is PAUSED inside its write transaction (at the registry
    lookup, which runs under BEGIN IMMEDIATE); `second` starts on another SqliteStore and must WAIT for the lock.
    Returns (first's result, second's result, second-was-still-waiting-while-first-held-the-lock)."""
    gate, entered = threading.Event(), threading.Event()
    out = {}
    s1, s2 = SqliteStore(p), SqliteStore(p)      # both OPEN before the first holds the lock (opening reads the store)
    orig = s1._registry_held

    def paused(*a, **k):
        entered.set()
        gate.wait(10)
        return orig(*a, **k)
    s1._registry_held = paused

    def run(key, fn, store):
        try:
            out[key] = fn(store)
        except Exception as exc:                                    # noqa: BLE001 — the race's result
            out[key] = exc
        finally:
            store.close()
    t1 = threading.Thread(target=run, args=("first", first, s1))
    t1.start()
    assert entered.wait(10)
    t2 = threading.Thread(target=run, args=("second", second, s2))
    t2.start()
    time.sleep(0.4)
    waited = t2.is_alive() and "second" not in out
    gate.set()
    t1.join(15)
    t2.join(15)
    return out["first"], out["second"], waited


def _undo_on(cid):
    return lambda s: s.undo_restoration(U, P, correlation_id=cid)


def _confirm_on(cid):
    return lambda s: Memory(llm=lambda *a, **k: "", store=s).confirm(U, N, correlation_id=cid)


def test_two_concurrent_undos_under_one_id_apply_once_and_the_second_replays(tmp_path):
    p = _restored(tmp_path)
    a, b, waited = _race(p, _undo_on("c1"), _undo_on("c1"))
    assert waited
    assert a["replayed"] is False and b == {**a, "replayed": True}
    assert _events(p) == [("reinstated", "arity_reclassified"), ("invalidated", "superseded")]   # ONE undo


@pytest.mark.parametrize("order", ["confirm-first", "undo-first"])
def test_confirm_and_undo_racing_on_one_id_admit_exactly_one(tmp_path, order):
    p = _restored(tmp_path)
    first, second = (_confirm_on("x"), _undo_on("x")) if order == "confirm-first" else (_undo_on("x"), _confirm_on("x"))
    a, b, waited = _race(p, first, second)
    assert waited
    assert not isinstance(a, Exception), a
    winner, loser = ("confirm", "undo") if order == "confirm-first" else ("undo", "confirm")
    assert isinstance(b, ValueError) and f"held by a '{winner}' request" in str(b), b
    assert T6._q(p, "SELECT verb FROM request_registry WHERE user_id=? AND correlation_id='x'", (U,)) == [(winner,)]


# ============================================================================================ redaction (INV-Q7)
def test_after_the_edges_redaction_the_undo_id_is_terminal_for_every_verb(tmp_path):
    p = _restored(tmp_path)
    _undo(p, cid="c1")
    plan = T6._q(p, "SELECT plan_id FROM plan_header")[0][0]
    digest = DM.portable_uid("undo", U, P, plan)
    s = SqliteStore(p)
    s.redact(U, edge_id=P, reason="subject_request")
    s.close()
    assert _refuses(RequestRedacted, _undo_raw, p, cid="c1").verb == "undo"
    # v8: the terminal precedes the verb check, so confirm() under the undo's id gets it too, naming `undo`
    assert _refuses(RequestRedacted, _mem(p).confirm, U, N, correlation_id="c1").verb == "undo"
    assert T6._q(p, "SELECT request_digest FROM request_registry WHERE correlation_id='c1'") == [(R.MARKER,)]
    assert digest not in T6._durable(p)


# ============================================================================================ doctor (§4k)
def test_doctor_reads_info_for_proof_and_the_old_warning_otherwise(tmp_path):
    p = _restored(tmp_path)
    assert [(f[0], f[2]) for f in _refs(p, user=U)] == [("info", (N,))]
    assert _refs(p, user=V) == [("info", f"1 active edge(s) whose predecessor is active because this store's data "
                                         "migration restored it (specs/0044 §4k: its own outcome row is the proof)",
                                 (f"n-{V}",))]
    _undo(p)
    assert _refs(p, user=U) == []                                   # undone: p is retired again, nothing to report
    _plant(p, "UPDATE edges SET active=1, json=json_set(json, '$.invalidated_at', NULL) WHERE id=?", (P,))
    assert [f[0] for f in _refs(p, user=U)] == ["warn"]             # an undone outcome is never proof


def test_doctor_joins_the_exemption_on_user_and_edge(tmp_path):
    """Unscoped too: U's own row not applicable, and a planted row for (V, U's edge) — the exemption must not be
    read from another user's row."""
    p = _restored(tmp_path)
    _plant(p, "UPDATE migration_outcome SET applicable=0 WHERE edge_id=?", (P,))
    _plant(p, "INSERT INTO migration_outcome(plan_id, user_id, edge_id, outcome, pre_invalidated_at, pre_reason, "
              "successor_evidence, applicable, origin, outcome_uid) VALUES('other-plan',?,?,'restored',?, "
              "'superseded','none',1,'local','uid-v')", (V, P, AT))
    for scope in (U, None):
        lv = [(f[0], f[2]) for f in _refs(p, user=scope) if N in f[2]]
        assert lv and all(level == "warn" for level, _ in lv), (scope, lv)


def test_doctor_without_outcome_rows_reads_as_before(tmp_path):
    """A v16 store whose data migration never ran (no outcome rows): an active predecessor is the old warning, in
    the old words. (Below v16 `doctor` runs no refs check at all: the version check refuses first.)"""
    p = T6._store(tmp_path, [T6._edge("a", "x"), T6._edge("b", "y", supersedes="a")])
    assert _refs(p) == [("warn", "1 active edge(s) whose predecessor is still active (a supersession that did not "
                                 "retire what it superseded)", ("b",))]


# ============================================================================================ the differential
_STEPS = ("undo:c1", "undo:c2", "undo:-", "confirm:c1", "redact", "revoke", "lift")
_MODEL_TEXT = {"no migration outcome": "no-outcome", "not restored": "not-restored", "testimony": "testimony",
               "not applicable": "not-applicable", "edge redacted or no longer held": "edge-unavailable"}


def _legal(seq):
    """revoke and lift at most once each, a lift only after the revoke (0022's own preconditions)."""
    return (seq.count("revoke") <= 1 and seq.count("lift") <= 1
            and ("lift" not in seq or ("revoke" in seq and seq.index("revoke") < seq.index("lift"))))


# the three length-3 sequences that reach the terminal pairs: undo's own terminal under each supplied id, and F1's
# (another verb under the undo's redacted id). Pinned, so the default run reaches them by construction, not by
# the seeded sample's draw (research's T7 stage-2 S1)
_PINNED = (("undo:c1", "redact", "undo:c1"), ("undo:c2", "redact", "undo:c2"), ("undo:c1", "redact", "confirm:c1"))


def _all_legal():
    return [s for n in (1, 2, 3) for s in itertools.product(_STEPS, repeat=n) if _legal(s)]


def _domain():
    out = _all_legal()
    assert set(_PINNED) <= set(out)
    if os.environ.get("VERACIUM_T6_FULL_DOMAIN") == "1":
        return out
    short = [s for s in out if len(s) <= 2]
    rest = [s for s in out if len(s) == 3 and s not in _PINNED]
    return short + list(_PINNED) + random.Random(4407).sample(rest, 40)


def _model_reached(seqs):
    """Every (step, result tag) model I returns over `seqs` — the coverage a run of them can claim."""
    reached = set()
    for seq in seqs:
        M, ms = _model_state()
        for step in seq:
            reached.add((step, _model_step(M, ms, step)))
    return reached


def _model_state():
    rm = _load("arity_run_model_0044", ROOT / "specs" / "evidence" / "0044" / "run_model.py")
    M = rm.M
    s = M.Store()
    p, n = rm.E("p", obj="weight 78", source="src-a"), rm.E("n", obj="weight 80", source="src-b")
    s.edges["p"] = p
    M.supersede_single(s, p, n)
    M.schema_step(s)
    rm.run(s)
    return M, s


def _model_step(M, s, step):
    verb, _, arg = step.partition(":")
    try:
        if verb == "undo":
            r = M.undo(s, "u", "p", correlation_id=None if arg == "-" else arg)
        elif verb == "confirm":
            r = M.confirm(s, "u", "n", cid=arg)
        elif verb == "redact":
            M.redact(s, "p"); return ("ok",)
        elif verb == "revoke":
            M.revoke_source(s, "src-a"); return ("ok",)
        else:
            M.lift_source(s, "src-a"); return ("ok",)
    except M.Refused as x:
        msg = str(x)
        if msg.startswith("integrity conflict: correlation id held by "):
            return ("conflict", msg.rsplit(" ", 1)[1])
        return ("refused", next(v for k, v in _MODEL_TEXT.items() if msg.startswith(k)))
    if "terminal" in r:
        return ("terminal", r["held_by"])
    if verb == "confirm":
        return ("confirm", "replayed" if "replayed" in r else "new")
    if "replayed" in r:
        return ("undo", False, True)
    return ("undo", r["already_undone"], False)


def _product_step(p, step, digest_of_src):
    verb, _, arg = step.partition(":")
    s = SqliteStore(p)
    try:
        if verb == "undo":
            m = Memory(llm=lambda *a, **k: "", store=s, config=MemoryConfig(db_path=p))
            r = m.undo_restoration(U, P, correlation_id=None if arg == "-" else arg)
            return ("undo", r["already_undone"], r["replayed"])
        if verb == "confirm":
            m = Memory(llm=lambda *a, **k: "", store=s, config=MemoryConfig(db_path=p))
            return ("confirm", "replayed" if m.confirm(U, N, correlation_id=arg)["replayed"] else "new")
        if verb == "redact":
            s.redact(U, edge_id=P, reason="subject_request"); return ("ok",)
        rv.revoke_source(s, U, digest_of_src(s), verb, "policy", AT)
        return ("ok",)
    except RequestRedacted as x:
        return ("terminal", x.verb)
    except UndoRefused as x:
        return ("refused", x.reason)
    except ValueError as x:
        if "held by a " in str(x):
            return ("conflict", str(x).split("held by a '")[1].split("'")[0])
        if "DIFFERENT undo request" in str(x):
            return ("conflict", "undo")
        raise
    finally:
        s.close()


def _model_projection(s):
    o = s.outcomes[("plan-1", "p")]
    return (o["undone_at"] is not None, bool(o["applicable"]), s.edges["p"].active,
            sorted((v["verb"], k[1] if not k[1].startswith("auto-") else "auto") for k, v in s.registry.items()))


def _product_projection(p):
    (undone, applicable, _ref), = _outcome(p)
    return (undone is not None, bool(applicable), T6._q(p, "SELECT active FROM edges WHERE id=?", (P,))[0][0] == 1,
            sorted((v, c if not c.startswith("auto-") else "auto") for v, c in
                   T6._q(p, "SELECT verb, correlation_id FROM request_registry WHERE user_id=?", (U,))))


def test_undo_agrees_with_model_i_over_short_sequences(tmp_path):
    """Model I's `undo`/`confirm`/`redact`/`revoke_source`/`lift_source` against the product, from one restored
    state, step by step. The PROJECTION (Q1, stated): each return maps to a tag — an undo to
    `(already_undone, replayed)` (the model's replay `{"replayed": ref}` is `(False, True)`); a refusal to its
    closed reason (the model's messages map by prefix); an integrity conflict to the holding verb; the terminal to
    the holding verb — and the state to (undone, applicable, edge active, the registry's (verb, id) pairs with
    every GENERATED id read as `auto`: the model draws `auto-<verb>-<txn>`, the product `auto-<hex>`). The act
    counter is not projected: neither side advances it on undo (D4; model I edited at T7). The default is every
    sequence of ≤2 steps, the three pinned terminal sequences and a seeded 40 of length 3;
    VERACIUM_T6_FULL_DOMAIN=1 runs every legal sequence. COVERAGE (stage-2 S1): the (step, result) pairs the run
    reached must equal those model I reaches over the WHOLE legal domain (derived here, never listed), so a default
    run that drops a pair fails instead of passing on a narrower claim."""
    tmpl = _restored(tmp_path, source="feed-1", name="template.db")
    blob = pathlib.Path(tmpl).read_bytes()
    src = lambda s: digest_of(None, "feed-1", s.local_origin())  # noqa: E731
    reached = set()
    for i, seq in enumerate(_domain()):
        p = str(tmp_path / f"d{i}.db")
        pathlib.Path(p).write_bytes(blob)
        M, ms = _model_state()
        for k, step in enumerate(seq):
            want, got = _model_step(M, ms, step), _product_step(p, step, src)
            assert got == want, (seq, k, step, want, got)
            assert _product_projection(p) == _model_projection(ms), (seq, k, step)
            reached.add((step, want))
    whole = _model_reached(_all_legal())
    assert reached == whole, ("coverage", sorted(whole - reached), sorted(reached - whole))
    assert {("undo:c1", ("terminal", "undo")), ("undo:c2", ("terminal", "undo")),
            ("confirm:c1", ("terminal", "undo"))} <= reached
