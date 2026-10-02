"""specs/0041 round 10 — P-CLOSED: the D1 reason fields close for future writes at every writer and at import
(round-9 R9-02 (a), (b), (c); sweep D's Edge.invalidation_reason).

Each field: a PERMITTED value, PROSE and NONE, tested separately, through the real writer and through the import
boundary; stored legacy prose still LOADS (the closure binds writers and import, never the read path).
`source_revocations.reason` closes for a REVOKE only — the LIFT half is held for the owner's ruling, and the lift cell
pins today's state so that a ruling which changes it is visible as a change here.
"""
import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

from veracium import redaction as R
from veracium.portability import export_memory, import_memory
from veracium.schema import DISPOSITIONED_REASONS, Disclosure, Edge, Episode, EvidenceAuthor, Provenance
from veracium.scope_linkage import identity_digest_of
from veracium.store.revocation import revoke_source

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r10r", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r10r"] = tt
_spec.loader.exec_module(tt)

U = "u"
PROSE = "she asked me to drop everything from that address"
AT = "2026-09-01T00:00:00Z"


def _prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw)
    return Provenance(**base)


def _count(st, table):
    return st._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _strict(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


# ------------------------------------------------------------------------------------------------ (a) revocation
def _digest(m):
    m.store.add_edge(Edge(id="e-s", user_id=U, subject="user", relation="lives_at", object="x",
                          provenance=_prov(source_id="mailbox-1")))
    return identity_digest_of(None, "mailbox-1", m.store.local_origin())


@pytest.mark.parametrize("reason", R.SOURCE_REVOCATION_REASONS)
def test_a_revoke_with_each_of_the_owners_four_reasons_commits(tmp_path, reason):
    m = tt._mem(tmp_path)
    revoke_source(m.store, U, _digest(m), "revoke", reason, AT)
    assert m.store._conn.execute("SELECT reason FROM source_revocations").fetchall() == [(reason,)]


@pytest.mark.parametrize("dry_run", [True, False])
def test_a_revoke_with_prose_refuses_in_preview_and_in_commit_and_writes_nothing(tmp_path, dry_run):
    m = tt._mem(tmp_path)
    with pytest.raises(ValueError, match="not one of"):
        revoke_source(m.store, U, _digest(m), "revoke", PROSE, AT, dry_run=dry_run)
    assert _count(m.store, "source_revocations") == 0


def test_a_the_redaction_vocabulary_is_not_the_revocation_vocabulary(tmp_path):
    """Two fields, two closures: `operator_policy` is a REDACTION reason and is refused for a revoke."""
    m = tt._mem(tmp_path)
    assert "operator_policy" in R.REDACTION_REASONS and "operator_policy" not in R.SOURCE_REVOCATION_REASONS
    with pytest.raises(ValueError, match="not one of"):
        revoke_source(m.store, U, _digest(m), "revoke", "operator_policy", AT)


def test_a_the_lift_half_is_held_a_lift_reason_is_neither_refused_nor_closed_today(tmp_path):
    """HELD for the owner's ruling (research put the lift vocabulary to the owner): this pins TODAY's state — a lift
    with a prose reason commits — so the ruling's implementation changes this cell visibly, never silently."""
    m = tt._mem(tmp_path)
    d = _digest(m)
    revoke_source(m.store, U, d, "revoke", "policy", AT)
    revoke_source(m.store, U, d, "lift", "revoked in error, the owner says", "2026-09-02T00:00:00Z")
    assert _count(m.store, "source_revocations") == 2


# ------------------------------------------------------------------------------------------------ (b) retired_reason
def _ep(**kw):
    return Episode(id="ep-1", user_id=U, date="2026-09-01", summary="day", provenance=_prov(), **kw)


@pytest.mark.parametrize("value, ok", [(None, True), ("revoked_source", True), (PROSE, False)])
def test_b_a_present_retired_reason_must_be_registered_none_stays_valid(tmp_path, value, ok):
    m = tt._mem(tmp_path)
    ep = _ep(retired_reason=value, retired_at=(datetime(2026, 9, 1, tzinfo=timezone.utc) if value else None))
    if ok:
        m.store.add_episode(ep)
        assert _count(m.store, "episodes") == 1
    else:
        with pytest.raises(ValueError, match="retired reason"):
            m.store.add_episode(ep)
        assert _count(m.store, "episodes") == 0


# ------------------------------------------------------------------------------------------------ (c) invalidation_reason
def _edge(eid="e-1", **kw):
    return Edge(id=eid, user_id=U, subject="user", relation="pet", object="a cat", provenance=_prov(), **kw)


@pytest.mark.parametrize("value, ok", [(None, True), ("disputed", True), (PROSE, False)])
def test_c_an_invalidation_reason_on_create_must_be_registered(tmp_path, value, ok):
    m = tt._mem(tmp_path)
    e = _edge(invalidated_at=(datetime(2026, 9, 1, tzinfo=timezone.utc) if value else None), invalidation_reason=value)
    if ok:
        m.store.add_edge(e)
        assert _count(m.store, "edges") == 1
    else:
        with pytest.raises(ValueError, match="invalidation reason"):
            m.store.add_edge(e)
        assert _count(m.store, "edges") == 0


def test_c_the_re_upsert_to_invalidated_with_prose_refuses_and_the_stored_row_is_unchanged(tmp_path):
    m = tt._mem(tmp_path)
    m.store.add_edge(_edge())
    before = m.store._conn.execute("SELECT json FROM edges").fetchone()[0]
    e = next(x for x in m.store.edges(U, active_only=False) if x.id == "e-1")
    e.invalidated_at, e.invalidation_reason = datetime(2026, 9, 1, tzinfo=timezone.utc), PROSE
    with pytest.raises(ValueError, match="invalidation reason"):
        m.store.add_edge(e)
    assert m.store._conn.execute("SELECT json FROM edges").fetchone()[0] == before


def test_c_every_registered_reason_is_accepted_the_closure_is_the_registry_not_a_list():
    assert set(DISPOSITIONED_REASONS) >= {"disputed", "corrected", "superseded", "revoked_source", "redacted"}


# ------------------------------------------------------------------------------------------------ the import boundary
def _file_with(tmp_path, kind, field, value):
    src = tt._mem(tmp_path, "src.db")
    if kind == "edge":
        src.store.add_edge(_edge())
    else:
        src.store.add_episode(_ep())
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = [json.loads(x, object_pairs_hook=_strict) for x in p.read_text().splitlines() if x.strip()]
    for r in recs:
        if r.get("record") == kind:
            r[field] = value
            r["invalidated_at" if kind == "edge" else "retired_at"] = "2026-09-01T00:00:00+00:00"
    out = tmp_path / "edited.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return out


@pytest.mark.parametrize("kind, field", [("edge", "invalidation_reason"), ("episode", "retired_reason")])
@pytest.mark.parametrize("value, ok", [("revoked_source", True), (PROSE, False)])
def test_the_closure_binds_the_import_boundary(tmp_path, kind, field, value, ok):
    path = _file_with(tmp_path, kind, field, value)
    dst = tt._mem(tmp_path, "dst.db")
    table = "edges" if kind == "edge" else "episodes"
    if ok:
        import_memory(dst.store, path, restore=True)
        assert _count(dst.store, table) == 1
    else:
        with pytest.raises(ValueError, match="registered reason"):
            import_memory(dst.store, path, restore=True)
        assert _count(dst.store, table) == 0


# ------------------------------------------------------------------------------------------------ legacy rows still load
def test_stored_legacy_prose_still_loads_the_closure_never_binds_the_read_path(tmp_path):
    m = tt._frozen_memory(tmp_path)
    eid = tt._frozen_rows()["prose_retired_reason"]
    eps = {e.id: e for e in m.store.episodes(U, include_retired=True)}
    assert eid in eps and eps[eid].retired_reason not in DISPOSITIONED_REASONS     # loaded, prose intact
