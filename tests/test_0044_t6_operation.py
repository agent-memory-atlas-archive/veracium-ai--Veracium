"""specs/0018 §4i (the folded amendment `0044/0018-data-migration`) and specs/0044 §4e–§4g-ii — T6: the per-user
data-migration operation, `run_data_migration`, against REAL stores.

  I29 / INV-M15  DataMigrationResult is total and closed: the constructor's rejection matrix row by row with every
                 outcome row constructing, AND a differential enumeration of reference model I's own domain (the
                 900 schedules of `run_model.enumerate_results`) on real stores, field by field.
  I25 / A15      the plan is written once, from the registry; only the three reclassified declarations count.
  A21            three durable header states; two concurrent first callers produce one header.
  I26            a user's restorations, outcomes, run row and journal commit together or not at all.
  I27            a completed user's re-call is `complete`, and `doctor` is quiet for it.
  I28            after a crash after commit, the receipt and the status recover the commit.
  I32            an op_id is bound to its inputs digest and mode; status is cumulative.
  I30            `doctor`'s four phases.
  A5 A7 A8 A9 A11 A20, and the inventory as the era boundary in BOTH directions (research's T6 read, F4).

Every mutant §4i.8 and 0044 §6 name for these rows is run by the scratch campaign
`.claude/skills/pre-seal/impl-review/0044/t6_mutant_defs.py` (classified by specs/evidence/mutation_kinds.py).
"""
import collections
import importlib.util
import json
import os
import random
import pathlib
import shutil
import sqlite3
import sys
import threading
from datetime import datetime, timezone

import pytest

from veracium import doctor
from veracium import redaction as R
from veracium.schema import DEFAULT_RELATIONS, Disclosure, Edge, EvidenceAuthor, Provenance, Relation
from veracium.store import data_migration as DM
from veracium.store import revocation as rv
from veracium.store import schema_version as sv
from veracium.store.migration import migrate_store
from veracium.store.release_migration import MigrationAttestation
from veracium.store.revocation_sweep import digest_of
from veracium.store.sqlite import SqliteStore

ROOT = pathlib.Path(__file__).resolve().parents[1]
U, V = "t6-user", "t6-other"
ATT = MigrationAttestation(quiesced=True, backup_ref="bk-t6")
PRE_2050 = datetime(2050, 1, 1, tzinfo=timezone.utc)      # a pre-step retirement dated AFTER the step
POST_1990 = datetime(1990, 1, 1, tzinfo=timezone.utc)     # a post-step retirement dated BEFORE it
AT = "2026-10-16T00:00:00Z"


def _model():
    name = "arity_run_model_0044"                          # the name obligations.py and the model tests use
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "specs" / "evidence" / "0044" / "run_model.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def _rel(name, arity):
    base = DEFAULT_RELATIONS[name]
    return Relation(name=name, functional=arity == "single", desc=base.desc, arity=arity)


def _reg(**arities):
    reg = dict(DEFAULT_RELATIONS)
    for name, a in arities.items():
        if a is None:
            reg.pop(name)
        else:
            reg[name] = _rel(name, a)
    return reg


def _edge(eid, obj, *, rel="measures", user=U, at=None, reason=None, day=1, source=None, supersedes=None):
    return Edge(id=eid, user_id=user, subject="user", relation=rel, object=obj,
                valid_from=datetime(2026, 1, day, tzinfo=timezone.utc), invalidated_at=at,
                invalidation_reason=reason, supersedes=supersedes,
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref=f"t6-{eid}",
                                      disclosure=Disclosure.MENTIONABLE, source_id=source,
                                      observed_at=datetime(2026, 1, day, tzinfo=timezone.utc)))


def _pair(user, *, rel="measures", at=PRE_2050, source=None, tag=""):
    """p (retired `superseded` under the old single rule) and its successor n, which names it in `supersedes`."""
    return [_edge(f"p{tag}-{user}", "weight 78", rel=rel, user=user, at=at, reason="superseded", source=source),
            _edge(f"n{tag}-{user}", "weight 80", rel=rel, user=user, day=2, supersedes=f"p{tag}-{user}",
                  source=source)]


def _v15(path, edges=()):
    c = sqlite3.connect(path)
    sv.create(c, 15)
    for e in edges:
        c.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) "
                  "VALUES(?,?,?,?,?,?,0,?)",
                  (e.id, e.user_id, e.subject, e.relation, e.object, int(e.invalidated_at is None),
                   e.model_dump_json()))
    c.execute("PRAGMA user_version = 15")
    c.commit()
    c.close()


def _store(tmp_path, edges=(), name="s.db"):
    """A real upgraded store: the v15 rows through the real v16 step (which inventories them)."""
    p = str(tmp_path / name)
    _v15(p, edges)
    migrate_store(p)
    return p


def _run(p, *, registry=None, op_id="op-1", plan_only=False, att=ATT):
    return DM.run_data_migration(p, host_attestation=att, registry=_reg() if registry is None else registry,
                                 op_id=op_id, plan_only=plan_only)


def _q(p, sql, args=()):
    c = sqlite3.connect(p)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def _json(p, eid):
    return json.loads(_q(p, "SELECT json FROM edges WHERE id=?", (eid,))[0][0])


def _durable(p) -> str:
    c = sqlite3.connect(p)
    try:
        return "\n".join(c.iterdump())
    finally:
        c.close()


def _dm_findings(p):
    return [(f.level, f.message) for f in doctor.diagnose(p).findings if f.check == "data-migration"]


def _assert_permitted(r, *outcomes):
    assert r.outcome in outcomes, f"{r.outcome}: {r.diagnostic}"


# ===================================================================================== I29: the carrier, row by row
_GOOD = {
    "requires-schema-step": dict(store_changed=False, plan_written=False, committed=(), failed=(), plan_id=None),
    "preflight-refused": dict(store_changed=False, plan_written=False, committed=(), failed=(), plan_id=None),
    "registry-changed": dict(store_changed=False, plan_written=False, committed=(), failed=(), plan_id="pl"),
    "op-id-conflict": dict(store_changed=False, plan_written=False, committed=(), failed=(), plan_id=None),
    "planned": dict(store_changed=True, plan_written=True, committed=(), failed=(), plan_id="pl"),
    "already-planned": dict(store_changed=False, plan_written=False, committed=(), failed=(), plan_id="pl"),
    "complete": dict(store_changed=False, plan_written=False, committed=(), failed=(), plan_id="pl"),
    "migrated": dict(store_changed=True, plan_written=False, committed=("a",), failed=(), plan_id="pl"),
    "partial": dict(store_changed=True, plan_written=False, committed=("a",), failed=("b",), plan_id="pl"),
    "failed": dict(store_changed=False, plan_written=False, committed=(), failed=("b",), plan_id="pl"),
}


def _carrier(outcome, **over):
    f = dict(_GOOD.get(outcome, _GOOD["complete"]), op_id="op-1", diagnostic="")
    f.update(over)
    return DM.DataMigrationResult(outcome, f["store_changed"], f["plan_written"], f["committed"], f["failed"],
                                  f["op_id"], f["plan_id"], f["diagnostic"])


@pytest.mark.parametrize("outcome", sorted(_GOOD))
def test_every_outcome_row_constructs(outcome):
    """§4c's positive control: each of the ten rows, with its own consistent fields, constructs."""
    assert _carrier(outcome).outcome == outcome
    if outcome == "failed":                                  # failed's store_changed IS plan_written
        assert _carrier("failed", store_changed=True, plan_written=True).store_changed is True


REJECTED = [
    ("row 1", "unlisted", {}),                                                    # round 3's `_result('unlisted', …)`
    ("row 2", "complete", {"plan_written": None}),                                # the carrier omits plan_written
    ("row 2", "complete", {"committed": ["a"]}),
    ("row 2", "migrated", {"committed": ("a", "a")}),
    ("row 3", "planned", {"store_changed": False}),                               # store_changed only on a commit
    ("row 3", "failed", {"store_changed": True}),
    ("row 4", "complete", {"failed": ("b",)}),
    ("row 4", "failed", {"failed": ()}),                                          # an all-failed call reads complete
    ("row 5", "complete", {"committed": ("a",), "store_changed": True}),
    ("row 5", "migrated", {"committed": (), "store_changed": False}),
    ("row 6", "partial", {"committed": ("a",), "failed": ("a",)}),
    ("row 7", "already-planned", {"plan_written": True, "store_changed": True}),
    ("row 7", "planned", {"plan_written": False, "store_changed": False}),
    ("row 8", "complete", {"op_id": "has space"}),
    ("row 9", "complete", {"plan_id": None}),                                     # research's row-9 mutants
    ("row 9", "preflight-refused", {"plan_id": "pl"}),
    ("row 9", "op-id-conflict", {"plan_id": "pl"}),
    ("row 9", "registry-changed", {"plan_id": None}),
]


@pytest.mark.parametrize("row,outcome,over", REJECTED, ids=[f"{r}-{o}-{i}" for i, (r, o, _) in enumerate(REJECTED)])
def test_the_constructor_rejects_each_matrix_row(row, outcome, over):
    with pytest.raises(ValueError, match=row):
        _carrier(outcome, **over)


# ===================================================================================== I29: the differential domain
def _templates(tmp_path):
    """One v15 and one v16 template store per user count (0–3), copied per schedule."""
    out = {}
    for n in range(4):
        edges = [e for i in range(n) for e in _pair(f"u{i}", tag="")]
        for v16 in (False, True):
            p = str(tmp_path / f"tpl-{n}-{int(v16)}.db")
            _v15(p, edges)
            if v16:
                migrate_store(p)
            out[(n, v16)] = p
    return out


def _status(p, op_id):
    s = DM.data_migration_status(p, op_id)
    return ({"outcome": "unknown-op"} if s.outcome == "unknown-op"
            else {"plan_written_by_op": s.plan_written_by_op, "committed": list(s.committed)})


def _model_status(m, s, op_id):
    st = m.M.data_migration_status(s, op_id)
    return st if st.get("outcome") == "unknown-op" else {"plan_written_by_op": st["plan_written_by_op"],
                                                         "committed": list(st["committed"])}


FULL_DOMAIN = os.environ.get("VERACIUM_T6_FULL_DOMAIN") == "1"
PER_OUTCOME = 6


def _domain(m) -> list:
    """The model's whole enumerated domain under VERACIUM_T6_FULL_DOMAIN=1 (900 schedules, ~4 minutes on real
    stores); otherwise a SEEDED sample STRATIFIED by the model's outcome, PER_OUTCOME schedules of each of the ten
    (research's T6 read, Q7), so every row of §4c is reached on every run."""
    cases = m.enumerate_results()
    if FULL_DOMAIN:
        return cases
    by = collections.defaultdict(list)
    for c in cases:
        by[c["result"]["outcome"]].append(c)
    rng = random.Random(20261016)
    return [c for o in sorted(by) for c in rng.sample(by[o], min(PER_OUTCOME, len(by[o])))]


def test_the_product_agrees_with_model_i_over_its_whole_domain(tmp_path, monkeypatch):
    """I29 / INV-M15 executed against the PRODUCT: reference model I's own §4c domain (schema version × attestation
    × the header before × an earlier call under the op_id × plan-only × 0–3 users × every failing subset), each
    schedule built as a real store — the whole domain with VERACIUM_T6_FULL_DOMAIN=1, a stratified seeded sample
    otherwise (`_domain`). Failure is injected AFTER the user's writes, inside its transaction (research's note), so
    a rollback that kept a write would show. Each carrier is compared field by field with the model's, the status
    read with the model's, and `store_changed` with whether the database's bytes changed (iterdump)."""
    m = _model()
    fails = set()
    real = DM._restore_user

    def injected(store, user, plan_id, relations, op_id):
        real(store, user, plan_id, relations, op_id)
        if user in fails:
            raise RuntimeError("injected after the user's writes")
    monkeypatch.setattr(DM, "_restore_user", injected)
    tpl = _templates(tmp_path)
    measures_single = _reg(measures="single")
    case_dir = tmp_path / "cases"
    case_dir.mkdir()
    seen, n_cases = set(), 0
    for c in _domain(m):
        v16, attested, before, prior, _pf, plan_only, n, want_fails = c["case"]
        p = str(case_dir / f"c{n_cases}.db")
        shutil.copyfile(tpl[(n, v16)], p)
        if v16 and before == "equal":
            _assert_permitted(_run(p, op_id="op-0", plan_only=True), "planned")
        elif v16 and before == "different":
            _assert_permitted(_run(p, registry=measures_single, op_id="op-0", plan_only=True), "planned")
        fails.clear()
        first = None
        if prior != "none":
            reg = measures_single if prior == "other-registry" else _reg()
            mode = (not plan_only) if prior == "other-mode" else plan_only
            first = _run(p, registry=reg, op_id="op-1", plan_only=mode)
            want_first = c["first"]
            assert (first.outcome, sorted(first.committed)) == (want_first["outcome"],
                                                                sorted(want_first["committed"])), c["case"]
        pre = _durable(p)
        fails.update(want_fails)
        r = _run(p, op_id="op-1", plan_only=plan_only, att=ATT if attested else None)
        fails.clear()
        want = c["result"]
        got = {"outcome": r.outcome, "store_changed": r.store_changed, "plan_written": r.plan_written,
               "committed": sorted(r.committed), "failed": sorted(r.failed), "op_id": r.op_id}
        assert got == {**want, "committed": sorted(want["committed"]), "failed": sorted(want["failed"])}, \
            (c["case"], r.diagnostic)
        assert r.store_changed == (_durable(p) != pre), c["case"]
        if v16:
            assert _status(p, "op-1") == c["status"], c["case"]
        seen.add(r.outcome)
        n_cases += 1
    assert n_cases == (900 if FULL_DOMAIN else PER_OUTCOME * len(DM.OUTCOMES))
    assert seen == set(DM.OUTCOMES)                           # all ten outcomes reached


# ===================================================================================== the restoration itself
def test_an_upgraded_store_restores_its_pre_step_retirements_on_both_dates(tmp_path):
    """0044 §4f: an inventoried retirement is restored whatever its valid-time endpoint (2050 and 1990 alike), with
    `reinstated`/`arity_reclassified` journaled, its inventory membership ended, and an outcome row naming its
    successor. The receipt reads the live object."""
    p = _store(tmp_path, _pair(U) + _pair(U, at=POST_1990, tag="b"))
    r = _run(p)
    _assert_permitted(r, "migrated")
    assert r.committed == (U,) and r.plan_written and r.store_changed
    for eid in (f"p-{U}", f"pb-{U}"):
        d = _json(p, eid)
        assert d["invalidated_at"] is None and d["invalidation_reason"] is None
        assert _q(p, "SELECT kind, reason FROM edge_event WHERE edge_id=? ORDER BY seq DESC LIMIT 1", (eid,)) == \
            [("reinstated", "arity_reclassified")]
    assert _q(p, "SELECT COUNT(*) FROM arity_inventory") == [(0,)]
    rows = DM.data_migration_receipt(p, r.plan_id, U)
    assert [(x.edge_id, x.outcome, x.replaced_by, x.object, x.applicable, x.origin) for x in rows] == [
        (f"p-{U}", "restored", (f"n-{U}",), "weight 78", True, "local"),
        (f"pb-{U}", "restored", (f"nb-{U}",), "weight 78", True, "local")]
    assert rows[0].pre_invalidated_at == _q(p, "SELECT pre_invalidated_at FROM migration_outcome WHERE edge_id=?",
                                            (f"p-{U}",))[0][0]


def test_a_fresh_store_has_nothing_to_restore(tmp_path):
    """§5: a store created at v16 has an empty inventory — the full call plans and finds no user (`planned`), and a
    second call is `complete`."""
    p = str(tmp_path / "fresh.db")
    s = SqliteStore(p)
    s.add_edge(_edge("x", "weight 70", day=3))
    s.close()
    r = _run(p)
    assert (r.outcome, r.committed, r.plan_written) == ("planned", (), True)
    assert _run(p).outcome == "complete"
    assert _q(p, "SELECT COUNT(*) FROM migration_run") == [(0,)]


def test_successor_evidence_is_zero_one_or_many_never_guessed(tmp_path):
    """INV-A8: `pointer` lists EVERY row whose `supersedes` names r, and `none` when nothing does — never matched by
    quantity or time."""
    lone = _edge("lone", "weight 60", at=PRE_2050, reason="superseded")
    two = [_edge("tw", "weight 61", at=PRE_2050, reason="superseded"),
           _edge("s1", "weight 62", day=2, supersedes="tw"), _edge("s2", "weight 63", day=3, supersedes="tw")]
    p = _store(tmp_path, [lone] + two + _pair(U))
    r = _run(p)
    got = {x.edge_id: x.replaced_by for x in DM.data_migration_receipt(p, r.plan_id, U)}
    assert got == {"lone": None, "tw": ("s1", "s2"), f"p-{U}": (f"n-{U}",)}
    assert json.loads(_q(p, "SELECT successor_evidence FROM migration_outcome WHERE edge_id='lone'")[0][0]) == \
        ["none", []]


def test_the_inventory_decides_in_both_directions(tmp_path):
    """research's T6 read, F4 — the negative half. A `superseded` retirement written AFTER the step (under a host
    `single` declaration for `prefers`, dated 1990) is never inventoried and never restored; an inventoried row
    reinstated by a same-id upsert and re-superseded is no longer a member and is not restored. The positive half is
    the 2050/1990 cell above."""
    p = _store(tmp_path, _pair(U))
    s = SqliteStore(p)
    s.add_edge(_edge("late", "tea", rel="prefers", at=POST_1990, reason="superseded"))
    re_ = _edge(f"p-{U}", "weight 78")                       # the same id upserted ACTIVE: membership ends
    s.add_edge(re_)
    re_.invalidated_at, re_.invalidation_reason = PRE_2050, "superseded"
    s.add_edge(re_)                                          # re-superseded with the inventoried bytes
    s.close()
    assert _q(p, "SELECT COUNT(*) FROM arity_inventory") == [(0,)]
    r = _run(p)
    assert r.outcome == "planned"                            # nothing inventoried: no user to process
    assert _json(p, "late")["invalidation_reason"] == "superseded"
    assert _json(p, f"p-{U}")["invalidation_reason"] == "superseded"


def test_a_re_retired_member_no_longer_matches(tmp_path):
    """0044 §4f's equality test: a member re-retired with a different retirement (a same-id upsert, still
    `superseded`) stays inventoried, but its current retirement no longer equals the inventoried one, so it is not
    considered; an untouched member of the same user is restored."""
    p = _store(tmp_path, _pair(U) + _pair(U, tag="b"))
    s = SqliteStore(p)
    moved = _edge(f"p-{U}", "weight 78", at=POST_1990, reason="superseded")
    s.add_edge(moved)
    s.close()
    assert _q(p, "SELECT COUNT(*) FROM arity_inventory WHERE edge_id=?", (f"p-{U}",)) == [(1,)]
    r = _run(p)
    assert r.committed == (U,)
    assert _q(p, "SELECT edge_id FROM migration_outcome") == [(f"pb-{U}",)]
    assert _json(p, f"p-{U}")["invalidation_reason"] == "superseded"


def test_a_redacted_row_is_never_restored_both_arms(tmp_path):
    """INV-A7 / §4f step 1: never considered when its carriers hold the marker, or when an applied attestation names
    it — each arm ALONE (a real redaction does both and also replaces `relation`, which the relation test catches
    first; the two arms are the defence in depth)."""
    p = _store(tmp_path, _pair(U) + _pair(U, tag="b"))
    plan_id = _run(p, plan_only=True).plan_id
    s = SqliteStore(p)
    try:
        s._conn.execute("UPDATE edges SET json=? WHERE id=?",
                        (json.dumps({**_json(p, f"p-{U}"), "object": R.MARKER}), f"p-{U}"))
        cols = [r[1] for r in s._conn.execute("PRAGMA table_info(redactions)")]
        row = {"id": "att-1", "user_id": U, "target_kind": "edge", "target_id": f"pb-{U}", "fields": "[]",
               "marker_version": 1, "reason": "subject_request", "store_version_before": 0,
               "store_version_after": 1, "recorded_at": AT, "state": "applied"}
        s._conn.execute(f"INSERT INTO redactions({','.join(row)}) VALUES({','.join('?' * len(row))})",
                        tuple(row.values()))
        s._conn.commit()
        assert "state" in cols
        relations = frozenset({"measures"})
        with s._lock, s._write_txn():
            got = DM._considered(s, U, plan_id, relations)
    finally:
        s.close()
    assert got == []
    r = _run(p, op_id="op-2")                                # op-1 is held by the plan-only call (another mode)
    assert (r.outcome, r.committed) == ("migrated", (U,)), r.diagnostic
    assert _q(p, "SELECT COUNT(*) FROM migration_outcome") == [(0,)]
    assert _json(p, f"pb-{U}")["invalidation_reason"] == "superseded"


def _revoked_store(tmp_path, *, basis=False):
    """A user whose `p` came from `feed-1`, then `feed-1` revoked (after the step: the retired row is untouched by
    the sweep, which only retires active rows). With `basis`, `p` is user-authored and only its CONTRIBUTION basis
    names the source (a 0014 absorption row), the contribution-derived arm."""
    src = None if basis else "feed-1"
    edges = _pair(U, source=src) + _pair(V)
    p = _store(tmp_path, edges)
    s = SqliteStore(p)
    d = digest_of(None, "feed-1", s.local_origin())
    if basis:
        s._conn.execute(
            "INSERT INTO contribution_ledger(id, user_id, survivor_type, survivor_id, site, identity_digest, "
            "evidence_ref_digest, payload, op_key, created_at, contributor_type, contributor_ref) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            ("contrib-t6", U, "edge", f"p-{U}", "consolidation", d, None, "{}", None, AT, None, None))
        s._conn.commit()
    rv.revoke_source(s, U, d, "revoke", "policy", AT)
    s.close()
    return p, d


@pytest.mark.parametrize("basis", [False, True], ids=["direct-source", "contribution-basis"])
def test_a_row_under_standing_revocation_is_withheld(tmp_path, basis):
    """INV-A11 / §4f step 2: the sweep's OWN predicate, as if active → `withheld_revoked`, the row stays retired;
    the unrevoked control user is restored. After the commit, `doctor`'s revocation check has nothing to report for
    the user (research's Q6 cell: retire and recompute together, 0044 §4k's claim)."""
    p, _d = _revoked_store(tmp_path, basis=basis)
    r = _run(p)
    assert r.outcome == "migrated" and set(r.committed) == {U, V}
    assert _q(p, "SELECT outcome, applicable FROM migration_outcome WHERE edge_id=?", (f"p-{U}",)) == \
        [("withheld_revoked", 0)]
    assert _json(p, f"p-{U}")["invalidation_reason"] == "superseded"
    assert _q(p, "SELECT outcome FROM migration_outcome WHERE edge_id=?", (f"p-{V}",)) == [("restored",)]
    assert not [f for f in doctor.diagnose(p, user=U).findings if f.check == "revocation" and f.level == "error"]


def test_the_outcome_row_alone_stops_a_reconsideration(tmp_path):
    """INV-A9 / §4f step 3, isolated (research's F2): withheld → the source lifted → the row is still inventoried and
    still retired with the inventoried retirement, so only the outcome row keeps it from being considered again."""
    p, d = _revoked_store(tmp_path)
    r = _run(p)
    s = SqliteStore(p)
    try:
        rv.revoke_source(s, U, d, "lift", "policy", AT)
        assert s._conn.execute("SELECT 1 FROM arity_inventory WHERE edge_id=?", (f"p-{U}",)).fetchone()
        with s._lock, s._write_txn():
            assert DM._considered(s, U, r.plan_id, frozenset({"measures"})) == []
    finally:
        s.close()
    assert _run(p).outcome == "complete"
    assert _json(p, f"p-{U}")["invalidation_reason"] == "superseded"


def test_a_completed_user_is_complete_on_re_call_and_doctor_is_quiet(tmp_path):
    """I27, with a user who KEEPS an inventory row (a withheld one), so the user stays in the universe and only the
    run row makes the re-call `complete` (research's F2: a user with only restored rows leaves the universe and would
    make the cell vacuous)."""
    p, _d = _revoked_store(tmp_path)
    assert _run(p).outcome == "migrated"
    assert _q(p, "SELECT user_id FROM arity_inventory") == [(U,)]
    pre = _durable(p)
    r = _run(p, op_id="op-x")                                 # a new id whose call finds every user complete
    assert (r.outcome, r.committed, r.store_changed) == ("complete", (), False)
    assert _durable(p) == pre and DM.data_migration_status(p, "op-x").outcome == "unknown-op"
    assert _dm_findings(p) == []


def test_a_users_transaction_is_atomic(tmp_path, monkeypatch):
    """I26: a failure after the user's restoration writes rolls back its edges, journal, inventory, outcomes and run
    row together; the failing user is named and the next user still commits (D1)."""
    p = _store(tmp_path, _pair(U) + _pair(V))
    _assert_permitted(_run(p, plan_only=True), "planned")
    real = DM._restore_user

    def boom(store, user, plan_id, relations, op_id):
        real(store, user, plan_id, relations, op_id)
        if user == V:
            raise RuntimeError("after the writes")
    monkeypatch.setattr(DM, "_restore_user", boom)
    before = {t: _q(p, f"SELECT * FROM {t} WHERE user_id=? ORDER BY 1, 2", (V,))
              for t in ("edges", "edge_event", "arity_inventory", "migration_outcome", "migration_run")}
    r = _run(p, op_id="op-2")
    assert (r.outcome, r.committed, r.failed) == ("partial", (U,), (V,))
    assert "t6-other: RuntimeError" in r.diagnostic and "after the writes" not in r.diagnostic
    assert {t: _q(p, f"SELECT * FROM {t} WHERE user_id=? ORDER BY 1, 2", (V,)) for t in before} == before
    monkeypatch.setattr(DM, "_restore_user", real)
    r2 = _run(p, op_id="op-2")                                 # the equal-digest resume retries exactly V
    assert (r2.outcome, r2.committed) == ("migrated", (V,))
    assert DM.data_migration_status(p, "op-2") == DM.DataMigrationStatus("known", False, tuple(sorted((U, V))))


def test_a_crash_after_a_users_commit_loses_nothing(tmp_path, monkeypatch):
    """I28: a crash after the user's commit, before the caller reads the result — the receipt and the status recover
    it from durable facts alone (no delivery state); a re-call is `complete` for that user."""
    p = _store(tmp_path, _pair(U))
    real = DM._migrate_user

    def crash(*a, **k):
        done = real(*a, **k)
        raise KeyboardInterrupt("after commit, before delivery")
    monkeypatch.setattr(DM, "_migrate_user", crash)
    with pytest.raises(KeyboardInterrupt):
        _run(p)
    monkeypatch.setattr(DM, "_migrate_user", real)
    st = DM.data_migration_status(p, "op-1")
    assert st == DM.DataMigrationStatus("known", True, (U,))
    plan_id = _q(p, "SELECT plan_id FROM plan_header")[0][0]
    assert [x.outcome for x in DM.data_migration_receipt(p, plan_id, U)] == ["restored"]
    assert _run(p).outcome == "complete"


# ===================================================================================== the plan (I25, A5, A15, A21)
def test_only_the_three_declarations_count(tmp_path):
    """I25 / A15: the plan is fixed at its first write. `works_as` single → multi leaves the digest equal and is
    admitted (the round-3 witness); a change to one of the three returns `registry-changed` naming both digests and
    changes nothing. Hashing the whole registry is the mutant."""
    p = _store(tmp_path, _pair(U))
    first = _run(p, plan_only=True)
    assert first.outcome == "planned"
    assert _run(p, registry=_reg(works_as="multi"), op_id="op-2", plan_only=True).outcome == "already-planned"
    pre = _durable(p)
    r = _run(p, registry=_reg(prefers="single"), op_id="op-3")
    assert r.outcome == "registry-changed" and r.plan_id == first.plan_id
    held = _q(p, "SELECT registry_digest FROM plan_header")[0][0]
    assert held in r.diagnostic and DM.plan_input_digest(_reg(prefers="single")) in r.diagnostic
    assert _durable(p) == pre
    assert DM.data_migration_status(p, "op-3").outcome == "unknown-op"


def test_the_plan_admits_only_canonically_default_declarations(tmp_path):
    """INV-A5 / §4e: a host `single` declaration keeps its relation out of the plan and its supersessions stay; a
    registry LACKING `prefers` gets no `prefers` row; a gloss edit keeps the name (arity only, research's Q4)."""
    p = _store(tmp_path, _pair(U) + _pair(U, rel="prefers", tag="f"))
    glossed = _reg()
    glossed["measures"] = Relation(name="measures", functional=False, desc="a host's own gloss", arity="multi")
    r = _run(p, registry={k: v for k, v in _reg(prefers="single").items()})
    assert _q(p, "SELECT relation FROM reclassification_plan ORDER BY relation") == [("health_state",),
                                                                                      ("measures",)]
    assert _json(p, f"pf-{U}")["invalidation_reason"] == "superseded"
    assert _json(p, f"p-{U}")["invalidation_reason"] is None and r.committed == (U,)
    assert DM.plan_relations(_reg(prefers=None)) == ("health_state", "measures")
    assert DM.plan_input_digest(_reg(prefers=None)) != DM.plan_input_digest(_reg())
    assert DM.plan_relations(glossed) == DM.PLAN_RELATIONS
    assert DM.plan_input_digest(glossed) == DM.plan_input_digest(_reg())


def test_three_header_states_and_an_empty_plan_is_recorded(tmp_path):
    """A21's store clauses: uninitialized → initialized-empty (a host whose declarations keep all three single gets
    a header with no relation rows, `doctor` info) → a later call with the defaults is REFUSED by digest, never
    re-planned."""
    p = _store(tmp_path, _pair(U))
    assert _dm_findings(p)[0][0] == "warn"                   # uninitialized: the pre-plan phase
    singles = _reg(measures="single", prefers="single", health_state="single")
    r = _run(p, registry=singles)
    assert (r.outcome, r.committed) == ("migrated", (U,))     # the user had an inventory row; nothing qualified
    assert _q(p, "SELECT COUNT(*) FROM reclassification_plan") == [(0,)]
    assert _q(p, "SELECT COUNT(*) FROM migration_outcome") == [(0,)]
    assert _dm_findings(p) == [("info", doctor.PLAN_EMPTY_INFO)]
    assert _run(p, op_id="op-2").outcome == "registry-changed"


def test_two_concurrent_first_callers_produce_one_header(tmp_path):
    """A21 / §4e admission: two first calls on two connections serialize on the write lock; exactly one header, one
    `planned` and one `already-planned`."""
    p = _store(tmp_path, _pair(U))
    gate, out = threading.Barrier(2), {}

    def call(op):
        gate.wait()
        out[op] = _run(p, op_id=op, plan_only=True)
    ts = [threading.Thread(target=call, args=(op,)) for op in ("op-a", "op-b")]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(r.outcome for r in out.values()) == ["already-planned", "planned"]
    assert _q(p, "SELECT COUNT(*) FROM plan_header") == [(1,)]
    assert len({r.plan_id for r in out.values()}) == 1


# ===================================================================================== admission (I32)
def test_the_op_id_is_bound_to_its_inputs(tmp_path):
    """I32: plan-only then restoration under one id conflicts; a changed request under a reused id never runs; the
    grammar is checked at entry, before any read, with no result constructed."""
    p = _store(tmp_path, _pair(U))
    assert _run(p, plan_only=True).outcome == "planned"
    pre = _durable(p)
    r = _run(p)                                               # the same id, the other mode
    assert (r.outcome, r.store_changed) == ("op-id-conflict", False)
    assert _durable(p) == pre
    with pytest.raises(ValueError, match="correlation_id"):
        _run(p, op_id="not a key")
    with pytest.raises(ValueError, match="correlation_id"):
        DM.data_migration_status(p, "x" * 65)
    assert _durable(p) == pre
    assert _q(p, "SELECT mode FROM migration_op WHERE op_id='op-1'") == [("plan_only",)]


def test_a_call_that_writes_nothing_holds_no_id(tmp_path, monkeypatch):
    """§4b.1b: an all-failed call over an existing header writes no admission record (`unknown-op`); its id stays
    free, and the failure is the user's entry, never an op-id-conflict (research's Q5 cell)."""
    p = _store(tmp_path, _pair(U))
    _run(p, op_id="op-0", plan_only=True)
    monkeypatch.setattr(DM, "_restore_user", lambda *a: (_ for _ in ()).throw(RuntimeError("no")))
    r = _run(p, op_id="op-9")
    assert (r.outcome, r.failed, r.store_changed, r.plan_written) == ("failed", (U,), False, False)
    assert DM.data_migration_status(p, "op-9").outcome == "unknown-op"


def test_a_conflict_found_in_a_users_transaction_is_not_a_users_failure(tmp_path, monkeypatch):
    """§4b.1b under the lock: when the header already exists, the call's first durable write is its first user's
    transaction, which re-checks the admission; a different-digest holder that appeared there refuses the CALL as
    `op-id-conflict` with nothing written — no `failed` entry (research's Q5)."""
    p = _store(tmp_path, _pair(U))
    _run(p, op_id="op-0", plan_only=True)
    real = DM._migrate_user

    def race(store, user, plan_id, admission, relations):
        store._conn.execute("INSERT INTO migration_op VALUES('op-1','plan_only','other-digest','2026-10-16')")
        store._conn.commit()
        return real(store, user, plan_id, admission, relations)
    monkeypatch.setattr(DM, "_migrate_user", race)
    r = _run(p)
    assert (r.outcome, r.failed, r.committed) == ("op-id-conflict", (), ())
    assert _q(p, "SELECT COUNT(*) FROM migration_run") == [(0,)]


# ===================================================================================== preflight cells
def test_preflight_cells(tmp_path):
    """§4b.1: below v16 → `requires-schema-step`; a refused attestation, a missing store and a registry 0025 refuses
    → `preflight-refused`; v16 with rebuildable drift → `preflight-refused`, never a silent repair (research's Q1)."""
    v15 = str(tmp_path / "old.db")
    _v15(v15, _pair(U))
    assert _run(v15).outcome == "requires-schema-step"
    p = _store(tmp_path, _pair(U))
    assert _run(p, att=None).outcome == "preflight-refused"
    assert _run(str(tmp_path / "absent.db")).outcome == "preflight-refused"
    assert not (tmp_path / "absent.db").exists()
    assert _run(p, registry={}).outcome == "preflight-refused"
    bad = _reg()
    bad["measures"] = _rel("measures", "multi").model_copy(update={"functional": True})
    assert _run(p, registry=bad).outcome == "preflight-refused"
    c = sqlite3.connect(p)
    c.execute("DROP INDEX ix_arity_inventory_user")           # a REBUILDABLE object: drift, not a foreign shape
    c.commit()
    c.close()
    pre = _durable(p)
    r = _run(p)
    assert r.outcome == "preflight-refused" and "rebuildable drift" in r.diagnostic
    assert _durable(p) == pre


# ===================================================================================== doctor (I30) and erasure (A20)
def test_doctor_names_incomplete_users_and_only_those_with_inventory(tmp_path, monkeypatch):
    """I30's initialized-nonempty phase: the users of the universe without a run row → warn naming the count and
    the operation; a user created AFTER the run (no inventory row) never warns (0018 §4i's annotation, Q2)."""
    p = _store(tmp_path, _pair(U) + _pair(V))
    monkeypatch.setattr(DM, "_restore_user", lambda store, user, *a: (_ for _ in ()).throw(RuntimeError("x"))
                        if user == V else None)
    r = _run(p)
    assert r.outcome == "partial"
    f = _dm_findings(p)
    assert len(f) == 1 and f[0][0] == "warn" and "1 user(s)" in f[0][1] and "run_data_migration" in f[0][1]
    monkeypatch.undo()
    _run(p)
    s = SqliteStore(p)
    s.add_edge(_edge("newcomer", "weight 90", user="t6-new", day=4))
    s.close()
    assert _dm_findings(p) == []


def test_erasure_ends_the_receipt_and_a_recreated_user_restores_nothing(tmp_path):
    """INV-A20 / §4g-ii: forget_user deletes the user's outcomes, run and inventory rows atomically; the receipt is
    empty, and a recreated user has no inventory row, so the next call commits nothing for it."""
    p = _store(tmp_path, _pair(U) + _pair(U, tag="b"))
    s = SqliteStore(p)
    s._conn.execute("DELETE FROM arity_inventory WHERE edge_id=?", (f"pb-{U}",))   # keep one member pending
    s._conn.commit()
    s.close()
    r = _run(p)
    s = SqliteStore(p)
    s.forget_user(U)
    s.add_edge(_edge(f"p-{U}", "weight 78", at=PRE_2050, reason="superseded"))
    s.close()
    assert DM.data_migration_receipt(p, r.plan_id, U) == ()
    for t in ("migration_outcome", "migration_run", "arity_inventory"):
        assert _q(p, f"SELECT COUNT(*) FROM {t} WHERE user_id=?", (U,)) == [(0,)]
    assert _run(p).outcome == "complete"
    assert _json(p, f"p-{U}")["invalidation_reason"] == "superseded"


def test_a_user_erased_between_the_universe_read_and_its_transaction_gets_no_run_row(tmp_path, monkeypatch):
    """research's F3: the universe is re-checked inside the user's transaction, so an erasure landing between the
    two reads writes no `migration_run` row after the erasure."""
    p = _store(tmp_path, _pair(U) + _pair(V))
    real = DM._inventory_users

    def then_erase(conn):
        users = real(conn)
        s = SqliteStore(p)
        s.forget_user(V)
        s.close()
        return users
    monkeypatch.setattr(DM, "_inventory_users", then_erase)
    r = _run(p)
    assert (r.outcome, r.committed) == ("migrated", (U,))
    assert _q(p, "SELECT user_id FROM migration_run") == [(U,)]


def test_the_receipt_reads_the_live_edge(tmp_path):
    """INV-A8 / §4d: object text from the LIVE edge at read time (a redacted edge shows the marker); an absent edge
    renders "no longer held" from the outcome row alone."""
    p = _store(tmp_path, _pair(U) + _pair(U, tag="b"))
    r = _run(p)
    s = SqliteStore(p)
    s.redact(U, edge_id=f"p-{U}", reason="subject_request")
    s._conn.execute("DELETE FROM edges WHERE id=?", (f"pb-{U}",))     # unreachable by any public path (§4g-ii)
    s._conn.commit()
    s.close()
    pre = _durable(p)
    got = {x.edge_id: x.object for x in DM.data_migration_receipt(p, r.plan_id, U)}
    assert got == {f"p-{U}": R.MARKER, f"pb-{U}": DM.NO_LONGER_HELD}
    DM.data_migration_status(p, "op-1")
    assert _durable(p) == pre                                 # the reads go through the shared opener and write nothing
    with pytest.raises(ValueError, match="not a current"):
        DM.data_migration_receipt(str(tmp_path / "absent.db"), r.plan_id, U)
    assert not (tmp_path / "absent.db").exists()


def test_portable_uid_is_0008s_canonical_encoding():
    """research's F6: 0008 §6e's encoding (UTF-8 JSON array, no whitespace), equal to model I's canonical_uid on a
    non-ASCII user id and on INV-Q8's separator, NUL and empty probes."""
    m = _model().M
    for parts in (("store", "Zoë", "plan", "e1"), ("a", "b:c", "", "d"), ("a:b", "c", "", "d"), ("a\x00", "", "x", "y"),
                  ("", "", "", "")):
        assert DM.portable_uid(*parts) == m.canonical_uid(*parts)
    assert DM.portable_uid("a", "b:c") != DM.portable_uid("a:b", "c")


def test_a_registry_without_prefers_moves_the_wiki_cache_key():
    """research's T5-3 read (the optional cell): `_policy_digest` binds the whole arity map, so a registry that DROPS
    a reclassified name changes the key."""
    from veracium import compile as _compile
    from veracium.registry import effective_registry
    full = effective_registry(_reg())
    dropped = effective_registry(_reg(prefers=None))
    assert _compile._policy_digest(full) != _compile._policy_digest(dropped)
