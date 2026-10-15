"""specs/0008 v7 §2a/§6c/§6f/§6g (amendment `0047/0008-request-registry`): the request registry, the act counter and
the confirmations act columns — schema v16, the programme's one bump.

PRODUCT tests through the real writer (`Store.confirm_edge`, `Memory.confirm`) and the real migration (`migrate_store`
from every base). The step's mutants are injected as TEMP triggers: they live in SQLite's temp schema, so they alter
what the step writes without altering the store's manifest, and each must refuse AT THE STEP IT NAMES (0013 §4f; the
B1 cells are research's stage-1 read of T3).
"""
from __future__ import annotations

import hashlib
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig
from veracium import redaction as _redaction
from veracium.schema import (CONFIRMATION_RULE_VERSION, ConfirmationActor, ConfirmationCallPath, Disclosure, Edge,
                             EvidenceAuthor, Provenance)
from veracium.store import migration as M
from veracium.store import schema_version as sv
from veracium.store.base import RequestRedacted
from veracium.store.migration import MigrationPostconditionError, migrate_store
from veracium.store.sqlite import SqliteStore

U = "u"
NOW = datetime(2026, 3, 1, tzinfo=timezone.utc)
CLOCK = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _mktemp_under_tmp_path(tmp_path):
    previous = tempfile.tempdir
    tempfile.tempdir = str(tmp_path)
    try:
        yield
    finally:
        tempfile.tempdir = previous


def _edge(eid="e1", *, obj="dark mode"):
    return Edge(id=eid, user_id=U, subject="user", relation="prefers", object=obj,
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc), active=True, needs_confirmation=True,
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref=eid,
                                      disclosure=Disclosure.MENTIONABLE,
                                      observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))


def _store(tmp_path, name="s"):
    return SqliteStore(str(tmp_path / f"{name}.db"))


def _confirm(store, eid="e1", **over):
    kw = dict(actor=ConfirmationActor.USER, call_path=ConfirmationCallPath.HOST_API,
              correlation_id="k1", request_digest="d1", confirmed_at=NOW)
    kw.update(over)
    return store.confirm_edge(U, eid, **kw)


# IO-II-7's form, applied to this file's own cells: an operation a cell EXPECTS TO SUCCEED is asserted as a
# permission (a store refusal — ValueError, KeyError, RuntimeError, MigrationPostconditionError among them — fails as an
# ASSERTION naming it), and an expected refusal is asserted by its class (another refusal, or none, is an assertion).
# Anything else (a TypeError, an unrelated failure) propagates as itself, so a mutation campaign never reads it as a kill.
_REFUSALS = (ValueError, KeyError, RuntimeError)


def _permitted(what, fn, *a, **k):
    try:
        return fn(*a, **k)
    except _REFUSALS as x:
        raise AssertionError(f"{what} was refused: {type(x).__name__}: {x}") from x


def _refuses(cls, fn, *a, match=None, **k):
    try:
        fn(*a, **k)
    except cls as x:
        assert match is None or match in str(x), f"refused, but not as {match!r}: {x}"
        return
    except _REFUSALS as x:
        raise AssertionError(f"expected {cls.__name__}, refused instead with {type(x).__name__}: {x}") from x
    raise AssertionError(f"DID NOT RAISE {cls.__name__}")


def _rows(path, sql):
    c = sqlite3.connect(path)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def _mem(tmp_path, name="m"):
    return Memory(llm=None, config=MemoryConfig(db_path=str(tmp_path / f"{name}.db"), wiki_recompile_after_writes=0))


# ---- the migration ----------------------------------------------------------------------------------------------

def _legacy_store(path, base, confirmations=(("c-1", "e1", "corr-1", "d1"),)):
    c = sqlite3.connect(path)
    sv.create(c, base)
    if base >= 2:
        for cid, eid, corr, digest in confirmations:
            c.execute("INSERT INTO confirmations VALUES (?,?,?,?,?,?,?,?)",
                      (cid, U, eid, "2026-01-02T00:00:00+00:00", "user", "host_api", corr, digest))
    c.execute(f"PRAGMA user_version = {base}")
    c.commit()
    c.close()


@pytest.mark.parametrize("base", range(1, 16))
def test_every_base_migrates_and_the_step_writes_exactly_its_inventory(tmp_path, monkeypatch, base):
    """§2a's inventory from every base: base 1 lands on the constructor shape, 2..15 on the frozen ALTER literal; one
    `confirm` registry row per confirmation (digest byte-copied, written_at the migration's ONE clock read); every
    legacy act `local` and position-less; the counter (1, 1). Mutants: the cells below, each at its step."""
    monkeypatch.setattr(M, "_clock", lambda: CLOCK)
    p = str(tmp_path / f"b{base}.db")
    _legacy_store(p, base)
    _permitted("the migration", migrate_store, p)
    assert _rows(p, "PRAGMA user_version") == [(16,)]
    ddl = _rows(p, "SELECT sql FROM sqlite_master WHERE name='confirmations'")[0][0]
    ctor = next(o.ddl for o in sv.SCHEMA_V16 if o.name == "confirmations")
    assert ddl == (ctor if base == 1 else sv.ALTER_PATH_V16_CONFIRMATIONS_SQL)
    reg = _rows(p, "SELECT user_id, correlation_id, verb, target_edge_id, request_digest, result_ref, written_at "
                   "FROM request_registry")
    assert reg == ([] if base == 1 else [(U, "corr-1", "confirm", "e1", "d1", "c-1", CLOCK.isoformat())])
    assert _rows(p, "SELECT origin, recorded_correlation_id, origin_store, origin_user, origin_act_id, act_seq "
                    "FROM confirmations") == ([] if base == 1 else [("local", None, None, None, None, None)])
    assert _rows(p, "SELECT id, next_seq FROM act_counter") == [(1, 1)]


def test_the_two_confirmations_variants_mean_the_same_columns(tmp_path):
    """Research's cell: the digests prove each shape ACCEPTED; only this proves they MEAN the same — name, type,
    NOT NULL, default and order, on a base-1 migration (constructor form) and a base-2 one (ALTER form)."""
    info = {}
    for base in (1, 2):
        p = str(tmp_path / f"v{base}.db")
        _legacy_store(p, base)
        _permitted("the migration", migrate_store, p)
        info[base] = _rows(p, "PRAGMA table_info(confirmations)")
    assert info[1] == info[2]
    assert [r[1:5] for r in info[1] if r[1] == "origin"] == [("origin", "TEXT", 1, "'local'")]


def _mutant_trigger(sql):
    """A TEMP trigger installed by a wrapped `mint_act_counter` — inside the migration's own transaction, before the
    backfill, invisible to the manifest."""
    real = sv.mint_act_counter

    def mint(conn):
        conn.execute(sql)
        real(conn)
    return mint


@pytest.mark.parametrize("label,sql,step", [
    ("M1: a legacy act gets a synthesized position",
     "CREATE TEMP TRIGGER m AFTER INSERT ON request_registry BEGIN "
     "UPDATE confirmations SET act_seq = rowid WHERE id = NEW.result_ref; END", M.STEP_ACT_COLUMNS),
    ("M1': a legacy act gets this store's origin",
     "CREATE TEMP TRIGGER m AFTER INSERT ON request_registry BEGIN "
     "UPDATE confirmations SET origin_store = 'me' WHERE id = NEW.result_ref; END", M.STEP_ACT_COLUMNS),
    ("M2: the backfill advances the counter once per row",
     "CREATE TEMP TRIGGER m AFTER INSERT ON request_registry BEGIN "
     "UPDATE act_counter SET next_seq = next_seq + 1; END", M.STEP_ACT_COUNTER),
    ("the backfill rewrites a digest",
     "CREATE TEMP TRIGGER m AFTER INSERT ON request_registry BEGIN "
     "UPDATE request_registry SET request_digest = 'other' WHERE rowid = NEW.rowid; END", M.STEP_REGISTRY),
    ("written_at is the confirmation's date",
     "CREATE TEMP TRIGGER m AFTER INSERT ON request_registry BEGIN "
     "UPDATE request_registry SET written_at = '2026-01-02T00:00:00+00:00' WHERE rowid = NEW.rowid; END",
     M.STEP_REGISTRY),
    ("a confirmation's own column changes",
     "CREATE TEMP TRIGGER m AFTER INSERT ON request_registry BEGIN "
     "UPDATE confirmations SET actor = 'system' WHERE id = NEW.result_ref; END", M.STEP_ACT_COLUMNS),
])
def test_each_step_mutant_refuses_at_its_step_and_nothing_lands(tmp_path, monkeypatch, label, sql, step):
    monkeypatch.setattr(M, "_clock", lambda: CLOCK)
    monkeypatch.setattr(sv, "mint_act_counter", _mutant_trigger(sql))
    p = str(tmp_path / "m.db")
    _legacy_store(p, 7)
    with pytest.raises(MigrationPostconditionError) as ei:
        migrate_store(p)
    assert ei.value.step == step, (label, ei.value.step, ei.value.problems)
    assert _rows(p, "PRAGMA user_version") == [(7,)], f"{label}: the refused migration landed"


def test_a_backfilled_redacted_confirmation_is_terminal_not_a_replay(tmp_path, monkeypatch):
    """§6g / INV-Q7: a confirmation 0041 already redacted (its digest IS the marker) backfills the marker, so a retry
    under its id is `request_redacted` — never the original. Mutant: backfill a fresh digest."""
    p = str(tmp_path / "r.db")
    _legacy_store(p, 15, confirmations=(("c-1", "e1", "k1", _redaction.MARKER),))
    _permitted("the migration", migrate_store, p)
    assert _rows(p, "SELECT request_digest FROM request_registry") == [(_redaction.MARKER,)]
    s = SqliteStore(p)
    _refuses(RequestRedacted, _confirm, s, correlation_id="k1", request_digest="d1")


def _v15_store_with_a_confirmation(path, corr="k-pre"):
    """A real pre-upgrade store: v15 DDL, the edge, and a confirmation whose digest is exactly what `Memory.confirm`
    computes for (u, e1, host_api, user, rule 0008, OMITTED)."""
    digest = hashlib.sha256("\x1f".join([U, "e1", "host_api", "user", CONFIRMATION_RULE_VERSION,
                                         "OMITTED"]).encode()).hexdigest()
    c = sqlite3.connect(path)
    sv.create(c, 15)
    e = _edge().model_copy(update={"needs_confirmation": False})
    c.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) VALUES(?,?,?,?,?,1,0,?)",
              ("e1", U, e.subject, e.relation, e.object, e.model_dump_json()))
    c.execute("INSERT INTO confirmations VALUES (?,?,?,?,?,?,?,?)",
              ("c-pre", U, "e1", "2026-01-02T00:00:00+00:00", "user", "host_api", corr, digest))
    c.execute("PRAGMA user_version = 15")
    c.commit()
    c.close()


def test_a_pre_upgrade_confirmation_replays_after_the_migration(tmp_path):
    """§6g's first regime row: every existing replay still replays — through the public verb, from the BACKFILLED
    row. Mutant: no backfill (the retry would be a second confirmation)."""
    p = str(tmp_path / "pre.db")
    _v15_store_with_a_confirmation(p)
    _permitted("the migration", migrate_store, p)
    mem = Memory(llm=None, config=MemoryConfig(db_path=p, wiki_recompile_after_writes=0))
    out = _permitted("a retry of a pre-upgrade confirmation", mem.confirm, U, "e1", correlation_id="k-pre")
    assert out["replayed"] is True and out["confirmed_at"] == "2026-01-02"
    assert len(mem.store.confirmations_for(U, "e1")) == 1


# ---- the writer ---------------------------------------------------------------------------------------------------

def test_a_fresh_store_mints_the_counter_and_acts_take_successive_positions(tmp_path):
    """§6f: creation mints (1, 1); each act takes the next position inside its own transaction; the registry row
    is written with it, written_at the store's clock. Mutants: no mint at create; a position from MAX(act_seq)."""
    p = str(tmp_path / "f.db")
    s = SqliteStore(p, clock=lambda: CLOCK)
    assert _rows(p, "SELECT id, next_seq FROM act_counter") == [(1, 1)]
    s.add_edge(_edge("e1"))
    s.add_edge(_edge("e2", obj="tea"))
    _permitted("a confirm", _confirm, s, "e1", correlation_id="k1")
    _permitted("a confirm", _confirm, s, "e2", correlation_id="k2", request_digest="d2")
    assert _rows(p, "SELECT correlation_id, origin, act_seq FROM confirmations ORDER BY act_seq") == [
        ("k1", "local", 1), ("k2", "local", 2)]
    assert _rows(p, "SELECT next_seq FROM act_counter") == [(3,)]
    assert _rows(p, "SELECT correlation_id, verb, target_edge_id, written_at FROM request_registry "
                    "ORDER BY correlation_id") == [("k1", "confirm", "e1", CLOCK.isoformat()),
                                                    ("k2", "confirm", "e2", CLOCK.isoformat())]


def test_a_retry_after_invalidation_replays_at_the_store_and_through_the_public_verb(tmp_path):
    """INV-Q2: the registry is read BEFORE any read of live edge state, so a retry replays after the edge was
    retired. FAILS ON THE v15 CODE, which checked assertability first and raised "not assertable". Driven through
    `Store.confirm_edge` and `Memory.confirm` both (research's N1). Mutant: read the edge first."""
    s = _store(tmp_path)
    s.add_edge(_edge())
    first = _permitted("a confirm", _confirm, s)
    s.invalidate_edge("e1", NOW, "superseded")
    again = _permitted("a retry after invalidation", _confirm, s)
    assert again.replayed is True and again.id == first.id

    mem = _mem(tmp_path)
    mem.store.add_edge(_edge())
    out = _permitted("a confirm", mem.confirm, U, "e1", correlation_id="kq")
    mem.store.invalidate_edge("e1", NOW, "superseded")
    replay = _permitted("a retry after invalidation", mem.confirm, U, "e1", correlation_id="kq")
    assert replay["replayed"] is True and replay["confirmed_at"] == out["confirmed_at"]


def test_an_id_held_by_another_verb_or_request_is_a_conflict_naming_it(tmp_path):
    """§6c: the same id under a different verb names the verb that holds it; under a different request, an
    integrity conflict. Mutants: replay across verbs; accept a different digest."""
    p = str(tmp_path / "v.db")
    s = SqliteStore(p)
    s.add_edge(_edge())
    _permitted("a confirm", _confirm, s, correlation_id="k1", request_digest="d1")
    _refuses(ValueError, _confirm, s, correlation_id="k1", request_digest="d2", match="DIFFERENT request")
    c = sqlite3.connect(p)
    c.execute("INSERT INTO request_registry VALUES (?,?,?,?,?,?,?)", (U, "kr", "reply", "e1", "dr", "r-1", "x"))
    c.commit()
    c.close()
    _refuses(ValueError, _confirm, s, correlation_id="kr", request_digest="dr", match="held by a 'reply' request")
    assert len(s.confirmations_for(U, "e1")) == 1


@pytest.mark.parametrize("index", ["present", "dropped"])
@pytest.mark.parametrize("payload", ["the same", "a different"])
def test_a_retry_after_redaction_is_terminal_whatever_its_payload(tmp_path, index, payload):
    """§6g / INV-Q7: a redaction REPLACEs the registry digest of every row targeting the edge; a retry is then
    `request_redacted` — not a replay (the verifier is gone), not a new act (the id stays held). Holds with the
    REBUILDABLE index dropped. Mutants: leave the registry digest; replay from result_ref."""
    p = str(tmp_path / "x.db")
    mem = Memory(llm=None, config=MemoryConfig(db_path=p, wiki_recompile_after_writes=0))
    mem.store.add_edge(_edge())
    _permitted("a confirm", mem.confirm, U, "e1", correlation_id="kx")
    if index == "dropped":
        mem.store._conn.execute("DROP INDEX ix_request_registry_target")
        mem.store._conn.commit()
    mem.redact(U, edge_id="e1", reason="subject_request")
    assert _rows(p, "SELECT request_digest FROM request_registry") == [(_redaction.MARKER,)]
    if payload == "the same":
        _refuses(RequestRedacted, mem.confirm, U, "e1", correlation_id="kx")
    else:
        _refuses(RequestRedacted, mem.confirm, U, "e1", correlation_id="kx", date="2026-05-05")
    assert len(mem.store.confirmations_for(U, "e1")) == 1


def test_erasure_frees_the_ids_but_never_resets_the_counter(tmp_path):
    """§6g / INV-Q6, Q9: `forget_user` erases the registry rows, so a retry after erasure is a NEW request; the
    counter is NOT erased, so a recreated user's act never reuses a position. Mutants: erase the counter; keep the
    registry rows."""
    p = str(tmp_path / "e.db")
    s = SqliteStore(p)
    s.add_edge(_edge())
    _permitted("a confirm", _confirm, s, correlation_id="k1")
    s.forget_user(U)
    assert _rows(p, "SELECT COUNT(*) FROM request_registry") == [(0,)]
    s.add_edge(_edge())
    again = _permitted("a confirm after erasure", _confirm, s, correlation_id="k1")
    assert again.replayed is False
    assert _rows(p, "SELECT act_seq FROM confirmations") == [(2,)]


def test_an_absent_counter_row_refuses_and_writes_nothing(tmp_path):
    """Research's N3: a writer never re-mints the counter — a lost row would restart positions. Mutant: INSERT OR
    IGNORE at write time."""
    p = str(tmp_path / "c.db")
    s = SqliteStore(p)
    s.add_edge(_edge())
    s._conn.execute("DELETE FROM act_counter")
    s._conn.commit()
    _refuses(RuntimeError, _confirm, s, match="act_counter")
    assert s.edges(U, active_only=False)[0].needs_confirmation is True
    assert _rows(p, "SELECT COUNT(*) FROM confirmations") == [(0,)]
    assert _rows(p, "SELECT COUNT(*) FROM request_registry") == [(0,)]
    assert _rows(p, "SELECT COUNT(*) FROM act_counter") == [(0,)]


def test_a_generated_id_takes_a_registry_row(tmp_path):
    """§6c: "a generated id takes a registry row like a supplied one". Mutant: register supplied ids only."""
    mem = _mem(tmp_path)
    mem.store.add_edge(_edge())
    out = _permitted("a confirm with a generated id", mem.confirm, U, "e1")
    assert out["correlation_id"].startswith("auto-")
    assert _rows(str(tmp_path / "m.db"), "SELECT correlation_id, verb FROM request_registry") == [
        (out["correlation_id"], "confirm")]
