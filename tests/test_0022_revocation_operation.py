"""specs/0022 — the R19 operation and standing state against the PRODUCT store.

The spec-side harness proves the construction on a toy table (18 checks); these
prove the same frozen properties against the real `source_revocations` table
SCHEMA v9 ships: F2 (a far-future revoke stays liftable — seq alone orders),
R1 (append-only standing state), R19 (row + effects land together or not at
all; failure outcomes total; the classifier reports the RIGHT invariant).
"""

import sqlite3
import uuid

import pytest

from veracium import SqliteStore
from veracium.store import revocation as rv

U = "u"


def _store(tmp_path):
    return SqliteStore(str(tmp_path / "r.db"))


def _op(conn, digest, action, *, at="2026-08-21T00:00:00Z", reason="operator",
        plan=lambda st: [], apply_effect=lambda c, e: None, **kw):
    return rv.revocation_operation(conn, U, digest, action, reason, at,
                                   plan=plan, apply_effect=apply_effect, **kw)


# --- F2: a planted far-future timestamp cannot make a revocation permanent ---

def test_a_far_future_revoke_is_still_liftable(tmp_path):
    s = _store(tmp_path)
    _op(s._conn, "d1", "revoke", at="2099-01-01T00:00:00Z")   # planted future
    assert rv.standing_revocations(s._conn, U) == {"d1"}
    _op(s._conn, "d1", "lift", at="2026-01-01T00:00:00Z")     # earlier clock
    assert rv.standing_revocations(s._conn, U) == frozenset(), (
        "the lift was appended LATER by the store's own committed order; a "
        "host-supplied clock must not out-rank the append ordinal (F2)")


def test_standing_is_latest_per_digest_by_seq_alone(tmp_path):
    s = _store(tmp_path)
    for digest, action in [("d1", "revoke"), ("d2", "revoke"), ("d1", "lift"),
                           ("d2", "lift"), ("d2", "revoke")]:
        _op(s._conn, digest, action)
    assert rv.standing_revocations(s._conn, U) == {"d2"}


# --- R19: the row and its effects land together or not at all ----------------

def test_effects_land_with_the_row(tmp_path):
    s = _store(tmp_path)
    applied = []
    seq, standing, effects = _op(
        s._conn, "d1", "revoke",
        plan=lambda st: [("probe", sorted(st))],
        apply_effect=lambda c, e: applied.append(e))
    assert applied == [("probe", [])] and seq == 0
    assert rv.standing_revocations(s._conn, U) == {"d1"}


def test_a_failing_effect_rolls_back_the_row_too(tmp_path):
    s = _store(tmp_path)

    def bad_apply(conn, e):
        raise rv.RevocationEffectError("effect refused")

    with pytest.raises(rv.RevocationEffectError):
        _op(s._conn, "d1", "revoke", plan=lambda st: [("x",)],
            apply_effect=bad_apply)
    assert rv.standing_revocations(s._conn, U) == frozenset()
    assert s._conn.execute("SELECT COUNT(*) FROM source_revocations")\
        .fetchone()[0] == 0, "the row must not survive its failed effects (R19)"
    assert not s._conn.in_transaction, "the transaction must be closed"


def test_a_fault_between_row_and_effects_loses_both(tmp_path):
    s = _store(tmp_path)

    def fault():
        raise RuntimeError("injected at the R19 seam")

    with pytest.raises(RuntimeError):
        _op(s._conn, "d1", "revoke", plan=lambda st: [("x",)],
            _fault=fault)
    assert s._conn.execute("SELECT COUNT(*) FROM source_revocations")\
        .fetchone()[0] == 0


# --- R5-1: the classifier reports the RIGHT invariant ------------------------

def test_an_ordinal_collision_is_classified_as_one(tmp_path):
    s = _store(tmp_path)
    _op(s._conn, "d1", "revoke")

    # force the UNIQUE(user_id, seq) violation through the operation by
    # pre-inserting the seq it will allocate, inside the plan callback — same
    # transaction, so the operation's own INSERT hits the constraint at append
    def plan_preinsert(st):
        s._conn.execute(
            "INSERT INTO source_revocations(user_id, seq, identity_digest,"
            " action, at, reason) VALUES(?,?,?,?,?,?)",
            (U, 1, "other", "revoke", "2026-01-01T00:00:00Z", "r"))
        return []

    with pytest.raises(rv.OrdinalCollision):
        _op(s._conn, "d2", "revoke", plan=plan_preinsert)


def test_a_non_ordinal_integrity_fault_is_NOT_a_collision(tmp_path):
    s = _store(tmp_path)
    # the CHECK(action IN ('revoke','lift')) constraint — an integrity fault
    # that is NOT the ordinal; converting it to OrdinalCollision would send
    # the operator to the wrong invariant (R5-1)
    with pytest.raises(rv.RevocationIntegrityError):
        _op(s._conn, "d1", "resurrect")
    assert not s._conn.in_transaction


def test_a_failing_rollback_reports_unknown_state_and_closes(tmp_path):
    s = _store(tmp_path)

    real_execute = s._conn.execute

    class Wrapped:
        def __init__(self, conn): self._c = conn
        def __getattr__(self, n): return getattr(self._c, n)
        def execute(self, sql, *a):
            if sql == "ROLLBACK":
                raise sqlite3.OperationalError("disk gone")
            return real_execute(sql, *a)

    w = Wrapped(s._conn)
    with pytest.raises(rv.RevocationUnknownState):
        rv.revocation_operation(
            w, U, "d1", "revoke", "r", "2026-01-01T00:00:00Z",
            plan=lambda st: [("x",)],
            apply_effect=lambda c, e: (_ for _ in ()).throw(RuntimeError("boom")))


# --- append-only: no UPDATE path exists on the product surface ---------------

def _updater_support():
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "support_0022_updater", pathlib.Path(__file__).resolve().parent / "support_0022_updater.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_the_table_is_append_only_by_construction():
    """0022 §4a, AS AMENDED by 0041 §11.4 (round 10): append-only, with EXACTLY ONE admitted updater — the redaction
    treatment `redact_revocation_reasons`, bound by NAME and by PROPERTY (the shared definition in
    tests/support_0022_updater.py, the same one the R19 gate reads). No other UPDATE, and no DELETE, anywhere in src."""
    import pathlib
    sup = _updater_support()
    files = {str(f): f.read_text() for f in sorted(pathlib.Path("src/veracium").rglob("*.py"))}
    _writers, updater_ok, violations = sup.classify(files)
    assert not violations, violations
    assert {name for _p, name in updater_ok} == {"redact_revocation_reasons"}, updater_ok


@pytest.mark.parametrize("body, why", [
    ("    if not conn.in_transaction:\n        raise RuntimeError('x')\n    conn.execute(\"UPDATE source_revocations SET action=? WHERE user_id=?\", ())\n", "SET assigns"),
    ("    if not conn.in_transaction:\n        raise RuntimeError('x')\n    conn.execute(\"UPDATE source_revocations SET reason=?, seq=? WHERE user_id=?\", ())\n", "SET assigns"),
    ("    if not conn.in_transaction:\n        raise RuntimeError('x')\n    conn.execute(\"UPDATE source_revocations SET reason=? WHERE user_id=?\", ())\n    conn.execute(\"INSERT INTO source_revocations(user_id) VALUES(?)\", ())\n", "not UPDATE alone"),
    ("    conn.execute(\"UPDATE source_revocations SET reason=? WHERE user_id=?\", ())\n", "refuse outside a transaction"),
])
def test_the_updater_property_refuses_each_wrong_shape(body, why):
    """The NEGATIVE controls: the named updater with a wrong SET, an extra INSERT, or no transaction guard is refused;
    the same statement under ANY other name is refused as an updater that is not the one admitted."""
    sup = _updater_support()
    src = "def redact_revocation_reasons(conn, user_id, digest):\n" + body
    _w, ok, violations = sup.classify({"src/veracium/store/revocation.py": src})
    assert not ok and any(why in v for v in violations), violations
    _w, ok2, v2 = sup.classify({"src/veracium/store/revocation.py": src.replace("redact_revocation_reasons", "other_writer")})
    assert not ok2 and any("not the one admitted updater" in v for v in v2), v2


def test_the_updater_property_accepts_the_shape_it_names():
    """The POSITIVE control: a guarded UPDATE that sets `reason` alone, under the admitted name, is accepted."""
    sup = _updater_support()
    src = ("def redact_revocation_reasons(conn, user_id, digest):\n    \"\"\"doc\"\"\"\n"
           "    if not conn.in_transaction:\n        raise RuntimeError('x')\n"
           "    return conn.execute(\"UPDATE source_revocations SET reason=? WHERE user_id=?\", ()).rowcount\n")
    _w, ok, violations = sup.classify({"src/veracium/store/revocation.py": src})
    assert ok and not violations


def test_the_one_updater_refuses_to_run_outside_a_transaction(tmp_path):
    """The executed probe of the guard the property names."""
    from veracium.store.revocation import redact_revocation_reasons
    st = SqliteStore(str(tmp_path / "s.db"))
    assert not st._conn.in_transaction
    with pytest.raises(RuntimeError, match="open write transaction"):
        redact_revocation_reasons(st._conn, "u", "a" * 64)
