"""T12, the real-store cross-package registry scenario (V44 L102 "a real-store cross-package registry scenario"; V45
L116): obligation I-4 in full ("Confirm, reply and undo must share one namespace, including concurrency,
migration/backfill, redaction's terminal precedence and user erasure", V44 L61) and IO-II-6's registry half ("Exercise
the request grammar and cross-verb races on a real store", V45 L72).

The store is REAL and MIGRATED: built at v14 (the released schema, v0.26.1) — or v15, main's, as the second base — with
a pre-upgrade confirmation, taken through the real v16 step by `migrate_store` (so its id is a BACKFILLED registry row),
then `run_data_migration` restores a value, so `undo_restoration` runs for real. Confirm and reply go through `Memory`.
Build note b2870871 D2/D3/D8 with addendum 1 (9d872f85: M2, P1, P2). Each cell names the clause it closes and its
mutant; the campaign is `t12_mutant_defs.py`. The model half of "both implementations must meet the shared contract" is
the two differentials (model I `test_0044_t7_undo.py`, model II `test_0047_t10a_reply.py`; V45 L40: "Both models now
exercise the third verb's terminal rule"); model II's token undo is not 0044's operation (V44 L61), so the PRODUCT
contract is checked here, on all three verbs together.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sqlite3
import sys
import threading
import time

import pytest

from veracium import Memory, MemoryConfig
from veracium.store import schema_version as sv
from veracium.store.base import RequestRedacted, UndoRefused
from veracium.store.migration import migrate_store
from veracium.store.sqlite import SqliteStore


def _load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


T6 = _load("t6_operation_helpers_0044", pathlib.Path(__file__).with_name("test_0044_t6_operation.py"))
U, V = T6.U, T6.V
P, N, F = f"p-{U}", f"n-{U}", f"f-{U}"
PRE = "pre-1"                                     # the pre-upgrade confirmation's id: a BACKFILLED registry row
PRE_DIGEST = "d" * 64


def _ok(fn, *a, **k):
    """A call the cell expects to SUCCEED: any raise is the property failing, read as an assertion."""
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


def _scenario(tmp_path, base=14, name="s.db"):
    """A store at `base` holding user U's retired `p` and its successor `n` (the old single rule's retirement), an
    assertable fact `f` with a pre-upgrade confirmation under `pre-1`, and a control user V; migrated to v16 by the real
    step, then the data migration restores `p`."""
    p = str(tmp_path / name)
    edges = [T6._edge(P, "weight 78", at=T6.PRE_2050, reason="superseded"), T6._edge(N, "weight 80", day=2, supersedes=P),
             T6._edge(F, "Paris", rel="lives_in")] + T6._pair(V)
    c = sqlite3.connect(p)
    sv.create(c, base)
    for e in edges:
        c.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) VALUES(?,?,?,?,?,?,0,?)",
                  (e.id, e.user_id, e.subject, e.relation, e.object, int(e.invalidated_at is None), e.model_dump_json()))
    c.execute("INSERT INTO confirmations VALUES('c-pre', ?, ?, '2026-01-02T00:00:00+00:00', 'user', 'host_api', ?, ?)",
              (U, F, PRE, PRE_DIGEST))
    c.execute(f"PRAGMA user_version = {base}")
    c.commit()
    c.close()
    _ok(migrate_store, p)
    assert T6._q(p, "SELECT correlation_id, verb, target_edge_id, result_ref FROM request_registry") == \
        [(PRE, "confirm", F, "c-pre")]                     # the backfill, as the v16 step writes it
    assert T6._run(p).outcome == "migrated"
    assert T6._q(p, "SELECT outcome FROM migration_outcome WHERE edge_id=?", (P,)) == [("restored",)]
    return p


def _mem(store):
    return Memory(llm=lambda *a, **k: "", store=store, config=MemoryConfig(db_path=store._path))


# the three verbs, each through the HOST entry (`Memory`, where §6c's id grammar is checked) on the store it is given,
# under one id, on the restored value `p` (one edge for all three, so a redaction of it reaches every verb's registry row)
VERBS = {
    "confirm": lambda s, cid: _mem(s).confirm(U, P, correlation_id=cid),
    "reply": lambda s, cid: _mem(s).reply(U, P, kind="context", text="noted", correlation_id=cid),
    "undo": lambda s, cid: _mem(s).undo_restoration(U, P, correlation_id=cid),
}


def _do(p, verb, cid):
    s = SqliteStore(p)
    try:
        return VERBS[verb](s, cid)
    finally:
        s.close()


def _registry(p, user=U):
    return T6._q(p, "SELECT correlation_id, verb FROM request_registry WHERE user_id=? ORDER BY correlation_id", (user,))


# ============================================================================== I-4: one namespace, the contract
@pytest.mark.parametrize("holder", sorted(VERBS))
def test_i4_one_namespace_on_the_migrated_store_every_holder_refuses_both_other_verbs(tmp_path, holder):
    """I-4 (V44 L61), the shared contract's core on the migrated store: an id held by ANY verb is an integrity conflict
    for each of the other two, naming the holder, and admits nothing (0008 INV-Q1, 0047 INV-R15). The verdict's other
    clauses are this module's other cells: concurrency (the races), migration/backfill (INV-Q3), redaction's terminal
    precedence (the 3×3 table) and user erasure. Mutant: each verb checks only its own table."""
    p = _scenario(tmp_path)
    _ok(_do, p, holder, "h1")
    before = _registry(p)
    for other in sorted(set(VERBS) - {holder}):
        exc = _refuses(ValueError, _do, p, other, "h1")
        assert not isinstance(exc, RequestRedacted) and f"held by a '{holder}' request" in str(exc), (other, exc)
    assert _registry(p) == before


# ============================================================================= migration/backfill (0008 INV-Q3)
@pytest.mark.parametrize("base", [14, 15])
def test_q3_a_pre_upgrade_confirm_id_conflicts_on_reply_and_on_undo_and_still_replays(tmp_path, base):
    """0008 INV-Q3 ("the migration backfills every existing confirmation, so a pre-upgrade confirm id conflicts on
    `reply`") and §6g's regime row ("a reply cannot reuse a pre-upgrade confirm id"), for reply AND undo, from v14 (the
    released schema) and v15: the backfilled id is refused naming `confirm`, and its own retry — the original request —
    replays the original confirmation. Control: a fresh id. Mutant: migrate without the backfill."""
    p = _scenario(tmp_path, base)
    for verb in ("reply", "undo"):
        assert "held by a 'confirm' request" in str(_refuses(ValueError, _do, p, verb, PRE)), verb
    s = SqliteStore(p)
    try:
        c = s.confirm_edge(U, F, actor=__import__("veracium.schema", fromlist=["x"]).ConfirmationActor.USER,
                           call_path=__import__("veracium.schema", fromlist=["x"]).ConfirmationCallPath.HOST_API,
                           correlation_id=PRE, request_digest=PRE_DIGEST, confirmed_at=__import__(
                               "datetime").datetime(2026, 1, 2, tzinfo=__import__("datetime").timezone.utc))
        assert c.id == "c-pre" and c.replayed is True
    finally:
        s.close()
    _ok(_do, p, "reply", "fresh-1")


# =========================================================================================== concurrency
def _race(p, first, second):
    """T7's construction (`test_0044_t7_undo.py` `_race`): `first` runs on its own SqliteStore, PAUSED inside its write
    transaction at the registry lookup (under BEGIN IMMEDIATE); `second` starts on another and must WAIT for the lock.
    Returns (first's result, second's result, second-was-waiting)."""
    gate, entered = threading.Event(), threading.Event()
    out = {}
    s1, s2 = SqliteStore(p), SqliteStore(p)
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


@pytest.mark.parametrize("first,second", [("reply", "undo"), ("undo", "reply"), ("confirm", "confirm")])
def test_races_on_two_connections_admit_exactly_one(tmp_path, first, second):
    """IO-II-6 ("cross-verb races on a real store") and I-4's concurrency: two connections racing one id. reply↔undo,
    both orders — the second waits for the lock and is refused naming the winner; confirm↔confirm (C8 on TWO
    connections; its existing cells force the race on one store) — the second replays the first. Mutant: the registry
    read outside the write transaction."""
    p = _scenario(tmp_path)
    a, b, waited = _race(p, lambda s: VERBS[first](s, "x"), lambda s: VERBS[second](s, "x"))
    assert waited
    assert not isinstance(a, Exception), a
    if first == second:
        assert not isinstance(b, Exception), b
        assert (b["replayed"], b["confirmed"]) == (True, a["confirmed"])
    else:
        assert isinstance(b, ValueError) and f"held by a '{first}' request" in str(b), b
    assert [v for c, v in _registry(p) if c == "x"] == [first]


def test_an_erasure_racing_a_reply_leaves_nothing_of_the_user_and_the_counter_unmoved_back(tmp_path):
    """I-4's erasure under concurrency: a reply paused inside its transaction, `forget_user` on another connection
    waiting for the lock. The reply commits first; the erasure then removes it with everything of the user (0008 §6g's
    one rule), and the act counter keeps the reply's position (never reset). Mutant: keep reply rows after erasure."""
    p = _scenario(tmp_path)
    seq0 = T6._q(p, "SELECT next_seq FROM act_counter")[0][0]
    a, b, waited = _race(p, lambda s: VERBS["reply"](s, "r1"), lambda s: s.forget_user(U))
    assert waited and not isinstance(a, Exception) and not isinstance(b, Exception), (a, b)
    for table in ("replies", "confirmations", "request_registry", "migration_outcome", "arity_inventory"):
        assert T6._q(p, f"SELECT COUNT(*) FROM {table} WHERE user_id=?", (U,))[0][0] == 0, table
    assert T6._q(p, "SELECT next_seq FROM act_counter")[0][0] == seq0 + 1
    assert T6._q(p, "SELECT COUNT(*) FROM edges WHERE user_id=?", (V,))[0][0] == 2          # the control untouched


# ============================================================================ redaction's terminal precedence
@pytest.mark.parametrize("connections", ["one", "two"])
@pytest.mark.parametrize("retrier", sorted(VERBS))
@pytest.mark.parametrize("holder", sorted(VERBS))
def test_terminal_after_redaction_for_every_holder_and_retrier(tmp_path, holder, retrier, connections):
    """0008 INV-Q7 ("for every verb, `confirm`, `reply` and `undo`"), §6g v8 (the terminal precedes the verb check),
    the whole 3×3 table in one place: after the edge's redaction, a retry under the holder's id by ANY verb raises
    `RequestRedacted` naming the HOLDER, whatever the payload — on the redacting connection and on a SECOND one opened
    before the redaction. Mutants: the terminal after the verb check; an undo's digest kept after redaction."""
    p = _scenario(tmp_path)
    _ok(_do, p, holder, "h1")
    s2 = SqliteStore(p) if connections == "two" else None
    s1 = SqliteStore(p)
    try:
        s1.redact(U, edge_id=P, reason="subject_request")
        store = s2 if s2 is not None else s1
        exc = _refuses(RequestRedacted, VERBS[retrier], store, "h1")
        assert exc.verb == holder, (exc.verb, holder)
    finally:
        s1.close()
        if s2 is not None:
            s2.close()


# ================================================================================================ erasure
def test_a_user_holding_all_three_verbs_is_erased_at_once_and_every_id_is_free_again(tmp_path):
    """I-4's erasure and 0008 §6g's one rule (INV-Q6, 0047 INV-R22, 0044 INV-A20): a user holding a confirmation, a reply and an
    undo is erased atomically — registry rows of every verb, act rows, outcome/run/inventory rows — the act counter is
    NOT reset, and after the user is recreated each erased id is a NEW request (never a replay, never a conflict),
    a recreated act taking a position past every erased one. Mutants: keep the registry after erasure; reset the
    counter; replay an erased undo id."""
    p = _scenario(tmp_path)
    _ok(_do, p, "confirm", "a")
    _ok(_do, p, "reply", "b")
    _ok(_do, p, "undo", "c")
    top = T6._q(p, "SELECT MAX(act_seq) FROM (SELECT act_seq FROM confirmations UNION ALL SELECT act_seq FROM replies)")[0][0]
    seq = T6._q(p, "SELECT next_seq FROM act_counter")[0][0]
    s = SqliteStore(p)
    try:
        s.forget_user(U)
    finally:
        s.close()
    for table in ("request_registry", "confirmations", "replies", "migration_outcome", "migration_run", "arity_inventory"):
        assert T6._q(p, f"SELECT COUNT(*) FROM {table} WHERE user_id=?", (U,))[0][0] == 0, table
    assert T6._q(p, "SELECT next_seq FROM act_counter")[0][0] == seq
    s = SqliteStore(p)
    try:
        s.add_edge(T6._edge(P, "weight 78"))                       # the user recreated, the same edge id
        c = _ok(VERBS["confirm"], s, "a")
        assert c["replayed"] is False
        r = _ok(VERBS["reply"], s, "b")
        assert r["replayed"] is False
        assert _refuses(UndoRefused, VERBS["undo"], s, "c").reason == "no-outcome"      # a new request: no outcome
    finally:
        s.close()
    new = T6._q(p, "SELECT act_seq FROM confirmations WHERE user_id=? UNION ALL SELECT act_seq FROM replies WHERE "
                   "user_id=?", (U, U))
    assert new and all(x[0] > top for x in new)


# ========================================================================================= the request grammar
GOOD = ["a", "A.b_c:d-9", "x" * 64]
BAD = ["", "x" * 65, "has space", "tab\there", "line\n", "#act:0123", "café", "semi;colon"]


@pytest.mark.parametrize("verb", sorted(VERBS))
def test_the_request_grammar_is_one_for_all_three_verbs_on_the_migrated_store(tmp_path, verb):
    """IO-II-6 ("Exercise the request grammar … on a real store") and 0008 §6c / C9: the union of the id cases the
    three verbs' cells had used separately, for EVERY verb, on the migrated store — each bad id refused with
    `ValueError` before any write (the registry and the act tables unchanged), each good one admitted (an undo of an
    already-undone value answers without taking the id). Mutant: one verb's grammar check removed."""
    p = _scenario(tmp_path)
    for cid in BAD:
        before = (_registry(p), T6._q(p, "SELECT COUNT(*) FROM confirmations"), T6._q(p, "SELECT COUNT(*) FROM replies"))
        exc = _refuses(ValueError, _do, p, verb, cid)
        assert not isinstance(exc, (RequestRedacted, UndoRefused)), (cid, exc)
        assert (_registry(p), T6._q(p, "SELECT COUNT(*) FROM confirmations"),
                T6._q(p, "SELECT COUNT(*) FROM replies")) == before, cid
    for cid in GOOD:
        _ok(_do, p, verb, cid)
