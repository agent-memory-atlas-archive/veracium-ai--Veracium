"""specs/0044 (accepted v1.6) — T5-2: the reclassification, the era boundary, the lifetime hook and the retention.

  INV-A1 / A2   `measures`, `prefers`, `health_state` are `multi`: a differing value never supersedes; reinforcement and
                absorption are unchanged (§4b).
  INV-A4        every other default keeps the meaning it had (its old functional bit, frozen below).
  INV-A6 / A14  a refusal recorded while its relation was `single` keeps its contested rendering and its compiler
                exclusion (§4d), decided by the v16 step's refusal INVENTORY, never by a timestamp, with no expiry.
  INV-A19       the arity inventory is the operation-era boundary (§4f): what was retired `superseded` under the three
                default names when the v16 step committed; a reinstatement ends membership terminally, at WHICHEVER
                write makes the row active again.
  INV-A22       lifetime transitions are derived at the emission choke point from the persisted prior and new row
                (§4f-ii), so the invalidate/reinstate methods and a same-id upsert are bound alike.
  INV-I24       the v16 step changes no edge and no journal event.
  INV-I30       `doctor`'s pre-plan phase (the 0018 amendment §4e): name-only, and stated as such.
  erasure       `forget_user` ends everything 0044 records for the user (§4g-ii).

`migration_outcome` rows are SEEDED through v16's real DDL (research's R5): T6 writes them, and the hook must already
be correct here. A12 is not product-true at T5.
"""
import json
import pathlib
import re
import sqlite3
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig
from veracium import compile as _compile
from veracium import doctor
from veracium import redaction as R
from veracium.contention import is_live_refusal
from veracium.graph import apply_supersession
from veracium.registry import declared_arity
from veracium.schema import (DEFAULT_RELATIONS, RESERVED_RELATIONS, Disclosure, Edge, EvidenceAuthor,
                             Provenance, SupersessionRefusal)
from veracium.store import lifetime as L
from veracium.store import migration as M
from veracium.store import schema_version as sv
from veracium.store.migration import MigrationPostconditionError, migrate_store
from veracium.store.sqlite import SqliteStore

U, V = "t5-user", "t5-other"
SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "veracium"
PRE_2050 = datetime(2050, 1, 1, tzinfo=timezone.utc)      # a pre-step retirement dated AFTER the step (§4f)
POST_1990 = datetime(1990, 1, 1, tzinfo=timezone.utc)     # a post-step retirement dated BEFORE it


def _edge(eid, obj, *, rel="measures", user=U, at=None, reason=None, author=EvidenceAuthor.USER, day=1):
    return Edge(id=eid, user_id=user, subject="user", relation=rel, object=obj,
                valid_from=datetime(2026, 1, day, tzinfo=timezone.utc),
                invalidated_at=at, invalidation_reason=reason,
                provenance=Provenance(author_of_evidence=author, evidence_ref=f"t5-{eid}",
                                      disclosure=Disclosure.MENTIONABLE,
                                      observed_at=datetime(2026, 1, day, tzinfo=timezone.utc)))


def _v15(path, edges=(), refusals=()):
    """A real pre-upgrade store: v15 DDL, edge rows (the `active` column mirroring the json, as every writer leaves
    it) and `supersession_refusals` rows `(refusal_id, user, prior, incoming, relation, created_at)`."""
    c = sqlite3.connect(path)
    sv.create(c, 15)
    for e in edges:
        c.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) "
                  "VALUES(?,?,?,?,?,?,0,?)",
                  (e.id, e.user_id, e.subject, e.relation, e.object, int(e.invalidated_at is None),
                   e.model_dump_json()))
    for rid, user, prior, inc, rel, created in refusals:
        c.execute("INSERT INTO supersession_refusals VALUES(?,?,?,?,?,3,2,'0003-v1',?)",
                  (rid, user, prior, inc, rel, created))
    c.execute("PRAGMA user_version = 15")
    c.commit()
    c.close()


def _migrated(tmp_path, name="s.db", **kw):
    p = str(tmp_path / name)
    _v15(p, **kw)
    _permitted("the v16 migration", migrate_store, p)
    return p


def _permitted(what, fn, *a, **k):
    """An expected acceptance asserted as a permission (IO-II-7's form): a refusal fails as an ASSERTION."""
    try:
        return fn(*a, **k)
    except (ValueError, KeyError, RuntimeError) as x:
        raise AssertionError(f"{what} was refused: {type(x).__name__}: {x}") from x


def _rows(p, sql, args=()):
    c = sqlite3.connect(p)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def _members(p):
    return {r[0] for r in _rows(p, "SELECT edge_id FROM arity_inventory")}


def _seed_outcome(store, eid, *, user=U, applicable=1, plan="plan-t5"):
    """research's R5: a `migration_outcome` row written through v16's real DDL (its CHECKs and UNIQUEs apply)."""
    store._conn.execute(
        "INSERT INTO migration_outcome(plan_id,user_id,edge_id,outcome,pre_invalidated_at,pre_reason,"
        "successor_evidence,applicable,origin,outcome_uid) VALUES(?,?,?,'restored','2026-01-01T00:00:00Z',"
        "'superseded','none',?,'local',?)", (plan, user, eid, applicable, f"uid-{plan}-{eid}"))
    store._conn.commit()


def _applicable(store, eid, plan="plan-t5"):
    r = store._conn.execute("SELECT applicable FROM migration_outcome WHERE plan_id=? AND edge_id=?",
                            (plan, eid)).fetchone()
    return None if r is None else r[0]


def _mem(p):
    return Memory(llm=lambda *a, **k: "", config=MemoryConfig(
        db_path=p, wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))


# ---- INV-A1 / A2: the three are multi; reinforcement and absorption unchanged ------------------------------------

@pytest.mark.parametrize("rel,a,b", [("measures", "weight 78 kg", "weight 80 kg"),
                                     ("prefers", "concise answers", "detailed answers"),
                                     ("health_state", "a cold", "a sprained ankle")])
def test_a_differing_value_under_a_reclassified_relation_leaves_both_active(tmp_path, rel, a, b):
    """A1 through the planner: neither value retires the other. Mutant: supersede under `multi`."""
    s = SqliteStore(str(tmp_path / "a1.db"))
    apply_supersession(s, _edge("x1", a, rel=rel), DEFAULT_RELATIONS)
    apply_supersession(s, _edge("x2", b, rel=rel, day=5), DEFAULT_RELATIONS)
    got = {e.id: e.invalidated_at for e in s.edges(U, active_only=False)}
    assert got == {"x1": None, "x2": None}, got


def test_a_differing_measures_value_leaves_both_active_through_remember(tmp_path):
    """A1 through `Memory.remember`, the extractor's path."""
    scripts = iter([{"triples": [{"subject": "user", "relation": "measures", "object": "weight 78 kg"}],
                     "episode": "weight"},
                    {"triples": [{"subject": "user", "relation": "measures", "object": "savings 4200"}],
                     "episode": "savings"}])
    mem = Memory(llm=lambda *a, **k: json.dumps(next(scripts)), config=MemoryConfig(
        db_path=str(tmp_path / "r.db"), wiki_recompile_after_writes=0, require_source_id=False))
    mem.remember(U, "I weigh 78 kg", date="2026-01-01")
    mem.remember(U, "my savings are 4200", date="2026-01-05")
    active = sorted(e.object for e in mem.store.edges(U, relation="measures"))
    assert active == ["savings 4200", "weight 78 kg"], active
    mem.close()


def test_absorption_under_measures_is_unchanged_and_unrelated_quantities_never_merge(tmp_path):
    """A2 (INV-A2 narrowed): `80` then `weight 80` absorbs, as for every `multi` relation; `weight 78 kg` and
    `savings 4200` both stay active. Mutant: absorb a non-subsuming value."""
    s = SqliteStore(str(tmp_path / "a2.db"))
    apply_supersession(s, _edge("n1", "80"), DEFAULT_RELATIONS)
    apply_supersession(s, _edge("n2", "weight 80", day=3), DEFAULT_RELATIONS)
    reasons = {e.id: e.invalidation_reason for e in s.edges(U, active_only=False)}
    assert reasons == {"n1": "absorbed_duplicate", "n2": None}, reasons
    apply_supersession(s, _edge("q1", "savings 4200", day=4), DEFAULT_RELATIONS)
    apply_supersession(s, _edge("q2", "weight 78 kg", day=6), DEFAULT_RELATIONS)    # one token longer, not a superset
    active = {e.id for e in s.edges(U)}
    assert {"q1", "q2"} <= active, active


# ---- INV-A4: every other default keeps its meaning ----------------------------------------------------------------

# the functional bit of every default and reserved relation at 7168070, the commit before the flip — FROZEN here, never
# derived from the registry the cell checks
FUNCTIONAL_BEFORE_0044 = frozenset({"works_as", "measures", "prefers", "located_at", "health_state", "deadline", "scope"})


def test_only_the_three_relations_change_arity():
    """A4: every default and reserved relation reads `single` iff it was functional before 0044, except the three,
    which read `multi`. Mutants: map `True -> multi`; reclassify a fourth relation; leave one of the three `single`."""
    for name, r in {**DEFAULT_RELATIONS, **RESERVED_RELATIONS}.items():
        want = "multi" if name in L.RECLASSIFIED_RELATIONS else (
            "single" if name in FUNCTIONAL_BEFORE_0044 else "multi")
        assert declared_arity(r) == want, (name, declared_arity(r), want)
    assert set(L.RECLASSIFIED_RELATIONS) == {"measures", "prefers", "health_state"}


def test_the_reclassified_glosses_lose_only_the_one_value_clauses():
    """R1 (research; the owner's ruling, option 3): the two false clauses are gone and every other gloss byte stays.
    The prompt-byte change is keyed into the benchmark's extraction identity (tests/test_longmemeval.py)."""
    assert DEFAULT_RELATIONS["measures"].desc == ("a changing quantity — weight, reading progress, savings balance, "
                                                  "score; history is kept")
    assert DEFAULT_RELATIONS["prefers"].desc == "a standing preference"
    assert DEFAULT_RELATIONS["health_state"].desc == "a current health condition or state"
    assert not any("one current value" in r.desc or "number updates" in r.desc for r in DEFAULT_RELATIONS.values())


# ---- the v16 step: the era and the two inventories (INV-A19, INV-I24) ---------------------------------------------

def _population():
    return [
        _edge("m-2050", "weight 81", at=PRE_2050, reason="superseded"),        # pre-step retirement dated 2050
        _edge("m-live", "weight 80"),
        _edge("p-old", "tea", rel="prefers", at=PRE_2050, reason="superseded"),
        _edge("h-disp", "a cold", rel="health_state", at=PRE_2050, reason="disputed"),   # not `superseded`
        _edge("w-old", "engineer at Acme", rel="works_as", at=PRE_2050, reason="superseded"),   # not a reclassified name
        _edge("m-other", "weight 90", user=V, at=PRE_2050, reason="superseded"),
    ]


def test_the_step_inventories_exactly_the_superseded_retirements_under_the_three_names(tmp_path):
    """§4f: the 2050-dated retirement IS inventoried (a clock test would exclude it); a `disputed` retirement, a
    `works_as` one and an active row are not; each row is its edge's own retirement. Mutants: select by
    `invalidated_at < effective_at`; select every superseded row; drop the user."""
    p = _migrated(tmp_path, edges=_population())
    got = _rows(p, "SELECT edge_id, user_id, pre_invalidated_at, pre_reason FROM arity_inventory ORDER BY edge_id")
    js = {e.id: json.loads(e.model_dump_json()) for e in _population()}
    assert got == [("m-2050", U, js["m-2050"]["invalidated_at"], "superseded"),
                   ("m-other", V, js["m-other"]["invalidated_at"], "superseded"),
                   ("p-old", U, js["p-old"]["invalidated_at"], "superseded")], got
    (era,) = _rows(p, "SELECT id, effective_at FROM arity_era")
    assert era[0] == 1 and era[1]


def test_a_retirement_after_the_step_is_never_inventoried_whatever_its_date(tmp_path):
    """§4f: the inventory is written ONCE, by the step; a later retirement dated 1990 is not old-policy. Mutant:
    inventory on every retirement under the three names."""
    p = _migrated(tmp_path, edges=_population())
    s = SqliteStore(p)
    s.invalidate_edge("m-live", POST_1990, "superseded")
    assert "m-live" not in _members(p)
    s.close()


def test_the_step_inventories_every_refusal_and_a_fresh_store_has_empty_inventories(tmp_path):
    """§4f / 0018 §4a (research's R3): EVERY refusal that exists, whatever its relation; a store CREATED at v16 holds
    an era row and two empty inventories. Mutant: filter the refusal inventory by the three names."""
    p = _migrated(tmp_path, edges=_population(), refusals=[
        ("r-m", U, "m-live", "m-2050", "measures", "2026-01-01T00:00:00+00:00"),
        ("r-w", U, "w-old", "m-live", "works_as", "2026-01-01T00:00:00+00:00")])
    assert sorted(_rows(p, "SELECT refusal_id, user_id FROM refusal_inventory")) == [("r-m", U), ("r-w", U)]
    f = str(tmp_path / "fresh.db")
    SqliteStore(f).close()
    assert len(_rows(f, "SELECT * FROM arity_era")) == 1
    assert _rows(f, "SELECT * FROM arity_inventory") == [] and _rows(f, "SELECT * FROM refusal_inventory") == []


def test_the_step_changes_no_edge_and_no_journal_event(tmp_path):
    """INV-I24: every edge row and every journal event byte-identical across the whole migration. Mutant: restore
    (clear a retirement) inside the step."""
    p = str(tmp_path / "i24.db")
    _v15(p, edges=_population())
    c = sqlite3.connect(p)
    c.execute("INSERT INTO edge_event(user_id,seq,txn,edge_id,kind,reason,state,recorded_at) "
              "VALUES(?,1,1,'m-live','created',NULL,?,'2026-01-01T00:00:00+00:00')",
              (U, c.execute("SELECT json FROM edges WHERE id='m-live'").fetchone()[0]))
    c.commit()
    before = (c.execute("SELECT * FROM edges ORDER BY id").fetchall(),
              c.execute("SELECT rowid, * FROM edge_event ORDER BY rowid").fetchall())
    c.close()
    _permitted("the v16 migration", migrate_store, p)
    after = (_rows(p, "SELECT * FROM edges ORDER BY id"), _rows(p, "SELECT rowid, * FROM edge_event ORDER BY rowid"))
    assert after == before


def test_a_row_whose_active_column_disagrees_with_its_json_refuses_the_step(tmp_path):
    """research's T5 F2: one predicate for "retired", and the step asserts the `active` column mirrors the json for
    every row under the three names — a disagreeing row refuses, never mis-inventoried. Mutant: skip the mirror."""
    p = str(tmp_path / "f2.db")
    _v15(p, edges=_population())
    c = sqlite3.connect(p)
    c.execute("UPDATE edges SET active=1 WHERE id='m-2050'")
    c.commit()
    c.close()
    with pytest.raises(MigrationPostconditionError) as ei:
        migrate_store(p)
    assert ei.value.step == M.STEP_ARITY_INVENTORY, (ei.value.step, ei.value.problems)
    assert _rows(p, "PRAGMA user_version") == [(15,)]


def _step_mutant(monkeypatch, sql_on, sql):
    """A PA1 cell (research's N3 rule): a TEMP trigger installed by the era mint, so it is in place when the
    inventory blocks write, perturbs the block after its own write."""
    real = sv.mint_arity_era

    def mint(conn, at):
        if sql_on:
            conn.execute(f"CREATE TEMP TRIGGER t5m AFTER INSERT ON {sql_on} BEGIN {sql}; END")
        real(conn, at)
    monkeypatch.setattr(sv, "mint_arity_era", mint)


@pytest.mark.parametrize("label,table,sql,step", [
    ("an extra inventory row", "arity_inventory",
     "INSERT OR IGNORE INTO arity_inventory VALUES('m-live', 't5-user', 'x', 'superseded')", M.STEP_ARITY_INVENTORY),
    ("a member lost", "arity_inventory", "DELETE FROM arity_inventory WHERE edge_id='p-old'", M.STEP_ARITY_INVENTORY),
    ("a member's retirement rewritten", "arity_inventory",
     "UPDATE arity_inventory SET pre_invalidated_at='1990-01-01T00:00:00Z' WHERE edge_id='m-2050'",
     M.STEP_ARITY_INVENTORY),
    ("an edge rewritten by the step", "arity_inventory",
     "UPDATE edges SET object='changed' WHERE id='m-live'", M.STEP_ARITY_EDGES),
    ("a refusal not inventoried", "refusal_inventory",
     "DELETE FROM refusal_inventory WHERE refusal_id='r-w'", M.STEP_REFUSAL_INVENTORY),
    ("an extra refusal inventoried", "refusal_inventory",
     "INSERT OR IGNORE INTO refusal_inventory VALUES('r-ghost', 't5-user')", M.STEP_REFUSAL_INVENTORY),
])
def test_each_step_mutant_refuses_at_its_block(tmp_path, monkeypatch, label, table, sql, step):
    _step_mutant(monkeypatch, table, sql)
    p = str(tmp_path / "pa1.db")
    _v15(p, edges=_population(), refusals=[
        ("r-m", U, "m-live", "m-2050", "measures", "2026-01-01T00:00:00+00:00"),
        ("r-w", U, "w-old", "m-live", "works_as", "2026-01-01T00:00:00+00:00")])
    with pytest.raises(MigrationPostconditionError) as ei:
        migrate_store(p)
    assert ei.value.step == step, (label, ei.value.step, ei.value.problems)
    assert _rows(p, "PRAGMA user_version") == [(15,)]


def test_an_era_not_the_migrations_clock_read_refuses_at_the_era_block(tmp_path, monkeypatch):
    """D5: the era is the migration's ONE clock read. Mutant: a second clock read."""
    real = sv.mint_arity_era
    monkeypatch.setattr(sv, "mint_arity_era", lambda conn, at: real(conn, "2001-01-01T00:00:00+00:00"))
    p = str(tmp_path / "era.db")
    _v15(p, edges=_population())
    with pytest.raises(MigrationPostconditionError) as ei:
        migrate_store(p)
    assert ei.value.step == M.STEP_ARITY_ERA, (ei.value.step, ei.value.problems)


# ---- §4f-ii: the lifetime transition, derived from persisted state (INV-A19, INV-A22) ------------------------------

def _j(**kw):
    return json.dumps({"invalidated_at": None, "invalidation_reason": None, "object": "v", **kw})


@pytest.mark.parametrize("prior,new,want", [
    (None, _j(), None),                                                              # an insert
    (None, _j(invalidated_at="2050", invalidation_reason="superseded"), None),        # …arriving retired
    (None, _j(object=R.MARKER), None),                                                # …arriving redacted
    (_j(invalidated_at="2050", invalidation_reason="superseded"), _j(), "reinstatement"),
    (_j(), _j(invalidated_at="1990", invalidation_reason="superseded"), "retirement"),
    (_j(invalidated_at="2050", invalidation_reason="superseded"),
     _j(invalidated_at="1990", invalidation_reason="superseded"), "re-retirement"),
    (_j(invalidated_at="2050", invalidation_reason="superseded"),
     _j(invalidated_at="2050", invalidation_reason="disputed"), "re-retirement"),
    (_j(invalidated_at="2050", invalidation_reason="superseded"),
     _j(invalidated_at="2050", invalidation_reason="superseded", object="w"), None),
    (_j(invalidated_at="2050-01-01T00:00:00+00:00", invalidation_reason="superseded"),
     _j(invalidated_at="2050-01-01T00:00:00Z", invalidation_reason="superseded"), None),      # one instant, two spellings
    (_j(), _j(object=R.MARKER), "redaction"),
    (_j(), _j(object="w"), None),                                                     # an ordinary mutation
])
def test_the_transition_table_row_by_row(prior, new, want):
    """§4f-ii's table, every row, plus the boundary cases: the same retirement with other fields changed is no
    transition; a redaction is read from the carriers' bytes."""
    assert L.transition(prior, new) == want


def test_an_upsert_reinstatement_ends_membership_and_an_identical_re_retirement_never_matches_again(tmp_path):
    """INV-A19 / R3-01: the same-id `add_edge` upsert reinstates WITHOUT the reinstate method; membership ends there,
    terminally, and the identical retirement written next does not restore it — so doctor stops counting it.
    Mutants: hook only the two methods; end membership only in `_reinstate_edge_row`; keep membership across a
    reinstatement; match by id only."""
    p = _migrated(tmp_path, edges=_population())
    s = SqliteStore(p)
    held = s.edges(U, active_only=False)
    m = next(e for e in held if e.id == "m-2050")
    assert "m-2050" in _members(p)
    s.add_edge(m.model_copy(update={"invalidated_at": None, "invalidation_reason": None}))
    assert "m-2050" not in _members(p)
    s.add_edge(m)                                                    # the identical retirement, re-written
    assert "m-2050" not in _members(p)
    s.close()
    found = [f for f in doctor.diagnose(p).findings if f.check == "data-migration"]
    assert all("m-2050" not in f.ids for f in found), found


def test_a_re_retired_member_stays_a_member_but_its_retirement_no_longer_matches(tmp_path):
    """§4f's equality test: a re-retirement (a different date) is not a reinstatement, so membership stays — but the
    current retirement no longer equals the inventoried one, so doctor's pre-plan phase does not count it. Mutant:
    match by id only."""
    p = _migrated(tmp_path, edges=_population())
    s = SqliteStore(p)
    m = next(e for e in s.edges(U, active_only=False) if e.id == "m-2050")
    s.add_edge(m.model_copy(update={"invalidated_at": POST_1990}))
    s.close()
    assert "m-2050" in _members(p)
    found = [f for f in doctor.diagnose(p).findings if f.check == "data-migration"]
    assert [sorted(f.ids) for f in found] == [["m-other", "p-old"]], found


def test_a_legacy_spelled_retirement_rewritten_by_a_writer_still_matches_its_inventory_row(tmp_path):
    """§4f's equality is of the retirement, not its bytes: a row a legacy writer stored as `+00:00` and the model's
    serializer rewrites as `Z` (any write of the row) keeps `applicable` and stays a counted member, and the inventory
    keeps the bytes the step read (what an undo writes back). Mutant: compare the stored strings."""
    e = _edge("m-legacy", "weight 82", at=PRE_2050, reason="superseded")
    p = str(tmp_path / "legacy.db")
    _v15(p, edges=[e])
    c = sqlite3.connect(p)
    d = json.loads(c.execute("SELECT json FROM edges WHERE id='m-legacy'").fetchone()[0])
    d["invalidated_at"] = "2050-01-01T00:00:00+00:00"
    c.execute("UPDATE edges SET json=? WHERE id='m-legacy'", (json.dumps(d),))
    c.commit()
    c.close()
    _permitted("the v16 migration", migrate_store, p)
    s = SqliteStore(p)
    _seed_outcome(s, "m-legacy")
    held = next(x for x in s.edges(U, active_only=False) if x.id == "m-legacy")
    s.add_edge(held.model_copy(update={"note": "rewritten by an ordinary write"}))
    assert json.loads(s._conn.execute("SELECT json FROM edges WHERE id='m-legacy'").fetchone()[0])[
        "invalidated_at"].endswith("Z"), "fixture: the rewrite did not re-spell the instant"
    assert _applicable(s, "m-legacy") == 1
    s.close()
    assert _rows(p, "SELECT pre_invalidated_at FROM arity_inventory") == [("2050-01-01T00:00:00+00:00",)]
    found = [f for f in doctor.diagnose(p).findings if f.check == "data-migration"]
    assert [f.ids for f in found] == [["m-legacy"]], found


def test_a_reinstatement_through_the_method_ends_membership_too(tmp_path):
    """The reinstate METHOD's write (a source lift) passes the same choke point."""
    p = _migrated(tmp_path, edges=_population())
    s = SqliteStore(p)
    with s._lock, s._write_txn():
        s._reinstate_edge_row("p-old")
    assert "p-old" not in _members(p)
    s.close()


def test_round_3s_upsert_sequence_ends_membership_at_the_reinstatement_and_clears_applicable_at_the_re_retirement(
        tmp_path):
    """INV-A22, round 3's sequence through `add_edge` alone: create; upsert retired; upsert active; upsert the
    identical retirement. The reinstatement ends membership and leaves `applicable`; the re-retirement clears it.
    Mutants: infer the transition from the journal kind (`mutated` throughout); hook only the two methods."""
    s = SqliteStore(str(tmp_path / "seq.db"))
    e = _edge("q", "weight 70")
    s.add_edge(e)
    retired = e.model_copy(update={"invalidated_at": PRE_2050, "invalidation_reason": "superseded"})
    s.add_edge(retired)
    at = json.loads(s._conn.execute("SELECT json FROM edges WHERE id='q'").fetchone()[0])["invalidated_at"]
    s._conn.execute("INSERT INTO arity_inventory VALUES('q', ?, ?, 'superseded')", (U, at))
    s._conn.commit()
    _seed_outcome(s, "q")
    s.add_edge(e)                                                     # reinstatement (an upsert)
    assert s._conn.execute("SELECT COUNT(*) FROM arity_inventory WHERE edge_id='q'").fetchone()[0] == 0
    assert _applicable(s, "q") == 1, "a reinstatement does not clear applicable"
    s.add_edge(retired)                                               # the identical retirement (an upsert)
    assert _applicable(s, "q") == 0
    s.add_edge(e)                                                     # a later reinstatement never sets it back
    assert _applicable(s, "q") == 0
    s.close()


def test_an_insert_arriving_retired_is_no_transition(tmp_path):
    """§4f-ii row 1: a NEW row, even one arriving retired, is not a held row changing. Mutant: treat an inactive
    insert as a retirement."""
    s = SqliteStore(str(tmp_path / "ins.db"))
    _seed_outcome(s, "z")
    s.add_edge(_edge("z", "weight 71", at=PRE_2050, reason="superseded"))
    assert _applicable(s, "z") == 1
    s.close()


def test_ordinary_mutations_keep_applicable_and_a_retirement_by_the_method_clears_it(tmp_path):
    """Counters, a note, a confirmation leave the flag; the invalidate method's retirement clears it, and the lift
    that follows does not set it back (restoration -> revocation -> lift)."""
    s = SqliteStore(str(tmp_path / "mut.db"))
    e = _edge("h", "weight 72")
    s.add_edge(e)
    _seed_outcome(s, "h")
    s.add_edge(e.model_copy(update={"note": "a harmless note", "times_used": 3}))
    s.confirm_edge(U, "h", actor="user", call_path="host_api", correlation_id="t5-k", request_digest="d",
                   confirmed_at=datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert _applicable(s, "h") == 1
    s.invalidate_edge("h", datetime.now(timezone.utc), "revoked_source")
    assert _applicable(s, "h") == 0
    with s._lock, s._write_txn():
        s._reinstate_edge_row("h")
    assert _applicable(s, "h") == 0
    s.close()


def test_a_redaction_clears_applicable(tmp_path):
    """§4i: a redaction's `redacted` write passes the choke point and clears the flag."""
    p = str(tmp_path / "red.db")
    mem = _mem(p)
    mem.store.add_edge(_edge("r", "weight 73"))
    _seed_outcome(mem.store, "r")
    mem.redact(U, edge_id="r", reason="subject_request")
    assert _applicable(mem.store, "r") == 0
    mem.close()


def test_an_upsert_introducing_the_marker_refuses_before_any_transition(tmp_path):
    """research's F1(c): INV-11's mirror refuses BEFORE the choke point, so no transition is derived and nothing
    changes. The dependency the bytes test rests on, pinned."""
    s = SqliteStore(str(tmp_path / "f1.db"))
    e = _edge("f", "weight 74")
    s.add_edge(e)
    _seed_outcome(s, "f")
    with pytest.raises(ValueError):
        s.add_edge(e.model_copy(update={"object": R.MARKER}))
    assert _applicable(s, "f") == 1
    s.close()


def test_an_imported_new_row_carrying_an_unattested_marker_is_an_insert(tmp_path):
    """research's F1(c), the import half: a record that ARRIVES holding the marker (admitted unattested, 0041 §4g)
    is a new row, so no transition — the seeded outcome under its id keeps `applicable`."""
    src = str(tmp_path / "src.db")
    a = SqliteStore(src)
    a.add_edge(_edge("g", "weight 75"))
    a.close()
    c = sqlite3.connect(src)
    d = json.loads(c.execute("SELECT json FROM edges WHERE id='g'").fetchone()[0])
    d["object"] = R.MARKER
    c.execute("UPDATE edges SET object=?, json=? WHERE id='g'", (R.MARKER, json.dumps(d)))
    c.commit()
    c.close()
    a = _mem(src)
    out = tmp_path / "g.jsonl"
    a.export_memory(U, out)
    a.close()
    b = _mem(str(tmp_path / "dst.db"))
    _seed_outcome(b.store, "g")
    _permitted("the import of an unattested-marker record", b.import_memory, out)
    assert b.store._conn.execute("SELECT COUNT(*) FROM edges WHERE id='g'").fetchone()[0] == 1
    assert _applicable(b.store, "g") == 1
    b.close()


# ---- §4d: historical refusal protection is retained (INV-A6, INV-A14; research's F3) -------------------------------

def _contention_store(tmp_path):
    """A pre-step refusal under `measures` (recorded 2000-01-01 — long before the step, and long before now) between
    a USER and a SYSTEM reading, both active; migrated; then a refusal recorded AFTER the step under `measures` and
    BACKDATED to 1990, before the era, between two other active readings."""
    p = _migrated(tmp_path, edges=[
        _edge("pre-a", "weight 78 kg"), _edge("pre-b", "weight 80 kg", author=EvidenceAuthor.SYSTEM),
        _edge("post-a", "savings 4200"), _edge("post-b", "savings 5000", author=EvidenceAuthor.SYSTEM)],
        refusals=[("r-pre", U, "pre-a", "pre-b", "measures", "2000-01-01T00:00:00+00:00")])
    c = sqlite3.connect(p)
    c.execute("INSERT INTO supersession_refusals VALUES('r-post', ?, 'post-a', 'post-b', 'measures', 3, 2, "
              "'0003-v1', '1990-01-01T00:00:00+00:00')", (U,))
    c.commit()
    c.close()
    return p


def _contested_ids(mem):
    groups, _ = mem._build_contested(U, query_edges=[])
    return {e.id for g in groups for e in g.exposed} | {l.edge_id for g in groups for l in g.linkage}


def test_a_pre_step_refusal_keeps_its_contested_group_and_its_wiki_exclusion(tmp_path):
    """INV-A6, both readers: recall's contested surface and the compiler's exclusion. The post-step refusal,
    backdated before the era, is NOT retained in either — a timestamp never decides. Mutants: declassify (drop the
    inventory clause); decide by `created_at`; retain every refusal under the three names."""
    p = _contention_store(tmp_path)
    mem = _mem(p)
    assert _contested_ids(mem) == {"pre-a", "pre-b"}
    assert _compile._live_refusal_contention_edge_ids(mem.store, U, mem.config.relations) == {"pre-a", "pre-b"}
    mem.close()


def test_retention_does_not_lapse_with_time(tmp_path):
    """INV-A14: no expiry — the retained refusal is 26 years old at the pin and stays contested under a store clock
    far in the future. Mutant: expire a retained refusal after a period."""
    p = _contention_store(tmp_path)
    mem = _mem(p)
    mem.store._clock = lambda: datetime(2099, 1, 1, tzinfo=timezone.utc)
    assert {"pre-a", "pre-b"} <= _contested_ids(mem)
    mem.close()


def test_a_retained_pair_ends_when_a_lifecycle_transition_retires_a_member(tmp_path):
    """§4d: the existing resolution path — a retirement of a member ends the live pair, and its protection with it."""
    p = _contention_store(tmp_path)
    mem = _mem(p)
    mem.store.invalidate_edge("pre-b", datetime.now(timezone.utc), "disputed")
    assert _contested_ids(mem) == set()
    assert _compile._live_refusal_contention_edge_ids(mem.store, U, mem.config.relations) == set()
    mem.close()


def test_one_live_contention_predicate_decides_for_both_readers(tmp_path, monkeypatch):
    """research's F3: recall and the compiler call ONE function, so the retention rule cannot drift between the
    contested surface and the wiki exclusion. Patched to refuse everything, both readers go empty."""
    p = _contention_store(tmp_path)
    mem = _mem(p)
    import veracium as _v
    monkeypatch.setattr(_v, "is_live_refusal", lambda *a, **k: False)
    monkeypatch.setattr(_compile, "is_live_refusal", lambda *a, **k: False)
    assert _contested_ids(mem) == set()
    assert _compile._live_refusal_contention_edge_ids(mem.store, U, mem.config.relations) == set()
    mem.close()
    # the predicate's own unit: a `single` relation needs no inventory; a reclassified one needs its refusal in it
    ref = SupersessionRefusal(refusal_id="x", user_id=U, prior_edge_id="a", incoming_edge_id="b",
                              relation="works_as", prior_effective=3, incoming_effective=2, rule_version="0003-v1",
                              created_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
    a, b = _edge("a", "CFO at Acme", rel="works_as"), _edge("b", "unemployed", rel="works_as")
    assert is_live_refusal(ref, a, b, DEFAULT_RELATIONS, frozenset())
    ref.relation = "measures"
    assert not is_live_refusal(ref, a, b, DEFAULT_RELATIONS, frozenset())
    assert is_live_refusal(ref, a, b, DEFAULT_RELATIONS, frozenset({"x"}))


# ---- INV-I30: doctor's pre-plan phase -----------------------------------------------------------------------------

def test_doctor_warns_before_any_plan_and_names_the_operation_by_relation_name(tmp_path):
    """The 0018 amendment §4e uninitialized row, its text verbatim: members whose retirement still equals the
    inventoried one. No warning on a fresh store, none once a plan header exists. Mutants: silent; a claim of
    eligibility."""
    p = _migrated(tmp_path, edges=_population())
    found = [f for f in doctor.diagnose(p).findings if f.check == "data-migration"]
    assert [(f.level, sorted(f.ids)) for f in found] == [("warn", ["m-2050", "m-other", "p-old"])], found
    assert doctor.PRE_PLAN_WARNING in found[0].message and "judged by relation name" in found[0].message
    assert "eligible" not in found[0].message.replace("will find none eligible", "")
    f = str(tmp_path / "fresh.db")
    SqliteStore(f).close()
    assert [x for x in doctor.diagnose(f).findings if x.check == "data-migration"] == []
    c = sqlite3.connect(p)
    c.execute("INSERT INTO plan_header VALUES(1, 'plan-t5', '2026-10-15T00:00:00+00:00', 'd', 'op-1')")
    c.commit()
    c.close()
    assert [x for x in doctor.diagnose(p).findings if x.check == "data-migration"] == []


# ---- §4g-ii: erasure ----------------------------------------------------------------------------------------------

def test_forget_user_erases_the_users_inventory_outcome_and_run_rows_and_no_one_elses(tmp_path):
    """0008 §6g's one erasure rule. Mutant: omit a table from `_ERASE_TABLES`."""
    p = _migrated(tmp_path, edges=_population(), refusals=[
        ("r-u", U, "m-live", "m-2050", "measures", "2026-01-01T00:00:00+00:00"),
        ("r-v", V, "m-other", "m-other", "measures", "2026-01-01T00:00:00+00:00")])
    s = SqliteStore(p)
    for user, eid in ((U, "m-2050"), (V, "m-other")):
        _seed_outcome(s, eid, user=user)
        s._conn.execute("INSERT INTO migration_run VALUES('plan-t5', ?, 'op-1', '2026-10-15T00:00:00+00:00')", (user,))
    s._conn.commit()
    s.forget_user(U)
    for table in ("arity_inventory", "refusal_inventory", "migration_outcome", "migration_run"):
        assert {r[0] for r in s._conn.execute(f"SELECT user_id FROM {table}")} == {V}, table
    assert len(s._conn.execute("SELECT * FROM arity_era").fetchall()) == 1     # store-level: never erased
    s.close()


# ---- §4g-ii: the census that keeps the absent-edge case unreachable -----------------------------------------------

def test_no_statement_deletes_from_edges_except_the_per_user_erasure():
    """The only edge-row delete is `forget_user`'s loop over `_ERASE_TABLES`; any other `DELETE FROM edges` would
    reopen 0044 §4g's absent-edge case. Interpolated table names are found too, and must sit in `forget_user`."""
    literal, interpolated = [], []
    for f in sorted(SRC.rglob("*.py")):
        text = f.read_text()
        for m in re.finditer(r"DELETE\s+FROM\s+(\w+|\{\w+\})", text, re.I):
            if m.group(1).lower() == "edges":
                literal.append(f"{f.relative_to(SRC)}:{text.count(chr(10), 0, m.start()) + 1}")
            elif m.group(1).startswith("{"):
                fn = max(text.rfind("\n    def ", 0, m.start()), text.rfind("\ndef ", 0, m.start()))
                interpolated.append((f.name, re.match(r"\n\s*def\s+(\w+)", text[fn:]).group(1)))
    assert literal == [], literal
    assert interpolated == [("sqlite.py", "forget_user")], interpolated
