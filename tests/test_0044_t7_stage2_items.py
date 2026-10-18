"""T7-1 — research's T6 stage-2 items N1–N4 (ceb520fe; ruled into T7's first commit by the owner, 2026-10-16).

  N1  a store path that does not encode (a lone surrogate) or encodes to more than 4096 bytes is refused with each
      public entry's OWN closed refusal, never a `UnicodeEncodeError`: `run_release_migration` → `invalid-request`
      (0018 I13's totality, broken since v0.11.0 for Python callers who build the path string themselves),
      `run_data_migration` → `preflight-refused`, `data_migration_status` and `data_migration_receipt` → `ValueError`.
      ONE predicate (`release_migration._usable_store_path`), whose encodability half `_store_path_problems` composes.
  N2  a `plan_only` that is not exactly a bool raises at entry, before anything is read (stated, not a §4c row).
  N3  `doctor --user` scopes the incomplete-users warning to that user.
  N4  the plan header's `effective_at` is the schema step's `arity_era.effective_at`, never the call's clock.
"""
import pathlib
import sqlite3
from datetime import datetime, timezone

import pytest

from veracium import doctor
from veracium.store import data_migration as DM
from veracium.store import release_migration as RM
from veracium.store.release_migration import MigrationAttestation
from veracium.store.sqlite import SqliteStore



def _t6():
    """T6's store builders, loaded by path (tests/ is not a package, and the import mode is not assumed)."""
    import importlib.util
    import sys
    name = "t6_operation_helpers_0044"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name("test_0044_t6_operation.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


T6 = _t6()

ATT = MigrationAttestation(quiesced=True, backup_ref="bk-t7")


def _fit(prefix: str, ch: str, n_bytes: int) -> str:
    """`prefix` padded with `ch` to EXACTLY `n_bytes` encoded bytes (`ch` is one byte or a whole multibyte char)."""
    w = len(ch.encode())
    gap = n_bytes - len(prefix.encode())
    assert gap >= 0 and gap % w == 0, (gap, w)
    s = prefix + ch * (gap // w)
    assert len(s.encode()) == n_bytes
    return s


def _paths(tmp):
    root = str(tmp) + "/"
    return {
        "lone-surrogate": root + "\ud800.db",
        "4097-bytes": _fit(root, "a", 4097),
        # ≤4096 CHARACTERS but 4097 bytes: a mutant counting `len(path)` instead of the encoded length passes it
        "multibyte-4097-bytes": _fit(root + "a", "é", 4097) if (4097 - len((root + "a").encode())) % 2 == 0
        else _fit(root, "é", 4097),
    }


def _entries(tmp):
    """The four public entries that take a store path, each with its own closed refusal."""
    return {
        "run_release_migration": lambda p: RM.run_release_migration(p, host_attestation=ATT),
        "run_data_migration": lambda p: DM.run_data_migration(p, host_attestation=ATT, registry=T6._reg(),
                                                              op_id="op-n1"),
        "data_migration_status": lambda p: DM.data_migration_status(p, "op-n1"),
        "data_migration_receipt": lambda p: DM.data_migration_receipt(p, "plan-n1", "u"),
    }


def _closed(call, p):
    """The call's return, or an AssertionError naming any raise: an entry whose refusal is a RESULT must never
    raise (N1's defect was a `UnicodeEncodeError` escaping it)."""
    try:
        return call(p)
    except Exception as exc:                                   # noqa: BLE001 — the cell's subject (an interrupt is not)
        raise AssertionError(f"raised {type(exc).__name__}: {exc!r} instead of returning a refusal") from exc


def _assert_refused(name, call, p):
    if name == "run_release_migration":
        r = _closed(call, p)
        assert r.outcome == "invalid-request" and "not a usable store path" in r.diagnostic, r
    elif name == "run_data_migration":
        r = _closed(call, p)
        assert r.outcome == "preflight-refused" and "not a usable store path" in r.diagnostic, r
    else:
        with pytest.raises(ValueError, match="not a usable store path"):
            call(p)


@pytest.mark.parametrize("entry", ["run_release_migration", "run_data_migration", "data_migration_status",
                                   "data_migration_receipt"])
@pytest.mark.parametrize("kind", ["lone-surrogate", "4097-bytes", "multibyte-4097-bytes"])
def test_n1_an_unencodable_or_oversized_path_is_each_entrys_own_refusal(tmp_path, entry, kind):
    p = _paths(tmp_path)[kind]
    if kind == "multibyte-4097-bytes":
        assert len(p) <= 4096 < len(p.encode())
    before = sorted(x.name for x in tmp_path.iterdir())
    _assert_refused(entry, _entries(tmp_path)[entry], p)       # never UnicodeEncodeError (N1's defect)
    assert sorted(x.name for x in tmp_path.iterdir()) == before


@pytest.mark.parametrize("entry", ["run_release_migration", "run_data_migration", "data_migration_status",
                                   "data_migration_receipt"])
def test_n1_a_4096_byte_path_passes_the_entry_check(tmp_path, entry):
    """The boundary's other side: exactly 4096 bytes is not refused by the PATH check (it fails later, as an absent
    store, with that store refusal's own words). The two TOTAL entries must RETURN here too: the path is one
    component of more than 255 bytes, so the filesystem's ENAMETOOLONG is in reach, and a raise is their defect
    (research's T7-1 read). Only the two reads may raise, and not the path check's refusal."""
    p = _fit(str(tmp_path) + "/", "a", 4096)
    call = _entries(tmp_path)[entry]
    if entry in ("run_release_migration", "run_data_migration"):
        r = _closed(call, p)
        assert "not a usable store path" not in (r.diagnostic or ""), r
    else:
        with pytest.raises((ValueError, OSError)) as ei:       # the reads refuse an absent store loudly
            call(p)
        assert "not a usable store path" not in str(ei.value)


def test_n1_one_predicate_two_consumers():
    """`_store_path_problems` (the authority path) composes `_path_encoding_problem`, so the two cannot disagree on
    encodability: over the probe set, the entry predicate and the authority path's encodability problem agree."""
    probes = ["/x.db", "/\ud800.db", "/" + "a" * 4095, "/" + "a" * 4096, "/" + "é" * 2048, "/a" + "é" * 2048,
              "/\udcff.db"]
    for sp in probes:
        try:
            enc = RM._path_encoding_problem(sp)
        except Exception as exc:                               # noqa: BLE001 — a predicate never raises
            raise AssertionError(f"{sp!r}: raised {type(exc).__name__}") from exc
        assert RM._usable_store_path(sp) is (enc is None), sp
        assert (enc in RM._store_path_problems(sp)) if enc else not any(
            pr.startswith(("is not filesystem-encodable", "exceeds 4096")) for pr in RM._store_path_problems(sp))


# ---------------------------------------------------------------------------------------------------------- N2
@pytest.mark.parametrize("bad", [1, 0, "yes", None, 1.0])
def test_n2_a_non_bool_plan_only_raises_before_anything_is_read(tmp_path, bad, monkeypatch):
    p = T6._store(tmp_path, T6._pair(T6.U))
    pre = T6._durable(p)
    def _read(*a, **k):
        raise AssertionError("the store was read before plan_only was checked")
    monkeypatch.setattr(DM, "_preflight", _read)
    with pytest.raises(ValueError, match="plan_only must be a bool"):
        DM.run_data_migration(p, host_attestation=ATT, registry=T6._reg(), op_id="op-n2", plan_only=bad)
    assert T6._durable(p) == pre


# ---------------------------------------------------------------------------------------------------------- N3
def _dm(p, user=None):
    return [(f.level, f.message) for f in doctor.diagnose(p, user=user).findings if f.check == "data-migration"]


def test_n3_doctor_scopes_the_incomplete_users_warning_to_the_named_user(tmp_path, monkeypatch):
    """Research's doctor_scope.py: U committed, V did not. Scoped to U → nothing; scoped to V → the warn for one
    user; unscoped → the warn for exactly one. A mutant dropping `AND i.user_id=?` warns for U."""
    p = T6._store(tmp_path, T6._pair(T6.U) + T6._pair(T6.V))
    monkeypatch.setattr(DM, "_restore_user", lambda store, user, *a: (_ for _ in ()).throw(RuntimeError("x"))
                        if user == T6.V else None)
    assert T6._run(p).outcome == "partial"
    monkeypatch.undo()
    assert _dm(p, user=T6.U) == []
    for scope in (T6.V, None):
        f = _dm(p, user=scope)
        assert len(f) == 1 and f[0][0] == "warn" and "1 user(s)" in f[0][1], (scope, f)


# ---------------------------------------------------------------------------------------------------------- N4
def test_n4_the_plan_header_carries_the_steps_effective_at_not_the_calls_clock(tmp_path, monkeypatch):
    p = T6._store(tmp_path, T6._pair(T6.U))
    era = T6._q(p, "SELECT effective_at FROM arity_era WHERE id=1")[0][0]
    later = datetime(2099, 6, 1, tzinfo=timezone.utc)          # the call's clock, forced to differ from the step's
    assert later.isoformat() != era
    monkeypatch.setattr(SqliteStore, "_now", lambda self: later)
    assert T6._run(p).outcome == "migrated"
    header = T6._q(p, "SELECT effective_at FROM plan_header WHERE id=1")[0][0]
    assert header == era
    # the control: the call's clock DID reach the store (its admission row carries it), so equal bytes above are
    # not the clocks coinciding
    assert T6._q(p, "SELECT admitted_at FROM migration_op WHERE op_id='op-1'")[0][0] == later.isoformat()
