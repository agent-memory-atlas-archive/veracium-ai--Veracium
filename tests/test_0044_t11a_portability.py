"""specs/0044 §4l (T11a, format era 14): outcome portability — the outcome rows and the exporting store's plan state
travel; import validates the unit whole, decides replay by comparing canonical projections over the staged union,
keeps one outcome per destination edge, maps trust by the origin matrix, and applies the owner's D3 ruling (plan state +
narrow): an undecided source's retired rows under a reclassified relation are refused into an uninitialized store,
converted under an initialized one's plan, and a decided source's are reported `unknown-linkage`.

PRODUCT tests through the real `export_memory` / `import_memory` on real upgraded stores (T6's construction: v15 rows
through the real v16 step), and `run_data_migration` for the plans. Build note b38eb499 + addendum 1 (research's
stage-1 read 8fbdf283): T1, Q1–Q5, T2–T4 are named where they bind.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
from datetime import datetime, timezone

import pytest

from veracium import portability as P
from veracium.schema import DEFAULT_RELATIONS, Disclosure, Edge, EvidenceAuthor, Provenance, Relation
from veracium.store import data_migration as DM
from veracium.store import schema_version as sv
from veracium.store.migration import migrate_store
from veracium.store.release_migration import MigrationAttestation
from veracium.store.sqlite import SqliteStore

U = "t11a-user"
ATT = MigrationAttestation(quiesced=True, backup_ref="bk-t11a")
PRE = datetime(2025, 6, 1, tzinfo=timezone.utc)          # a retirement under the old single rule


def _edge(eid, obj, *, rel="measures", user=U, at=None, reason=None, day=1, supersedes=None):
    return Edge(id=eid, user_id=user, subject="user", relation=rel, object=obj,
                valid_from=datetime(2025, 1, day, tzinfo=timezone.utc), invalidated_at=at,
                invalidation_reason=reason, supersedes=supersedes,
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref=f"t11a-{eid}",
                                      disclosure=Disclosure.MENTIONABLE,
                                      observed_at=datetime(2025, 1, day, tzinfo=timezone.utc)))


def _pair(tag="", rel="measures", user=U):
    """p, retired `superseded` under the old single rule, and its successor n."""
    return [_edge(f"p{tag}", "weight 78", rel=rel, user=user, at=PRE, reason="superseded"),
            _edge(f"n{tag}", "weight 80", rel=rel, user=user, day=2, supersedes=f"p{tag}")]


def _store(tmp_path, name, edges=()):
    """A real upgraded store: v15 rows through the real v16 step (which inventories them)."""
    p = str(tmp_path / name)
    c = sqlite3.connect(p)
    sv.create(c, 15)
    for e in edges:
        c.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) VALUES(?,?,?,?,?,?,0,?)",
                  (e.id, e.user_id, e.subject, e.relation, e.object, int(e.invalidated_at is None), e.model_dump_json()))
    c.execute("PRAGMA user_version = 15")
    c.commit()
    c.close()
    migrate_store(p)
    return p


def _run(p, *, op_id="op-1", plan_only=False, registry=None):
    r = DM.run_data_migration(p, host_attestation=ATT, registry=dict(DEFAULT_RELATIONS) if registry is None else registry,
                              op_id=op_id, plan_only=plan_only)
    assert r.outcome in ("planned", "migrated", "complete", "already-planned"), (r.outcome, r.diagnostic)
    return r


def _export(p, tmp_path, name, user=U):
    s = SqliteStore(p)
    try:
        f = tmp_path / name
        P.export_memory(s, user, f)
        return f
    finally:
        s.close()


def _import(p, f, **kw):
    """An import the cell expects to be ADMITTED: a refusal is the cell's failure, stated as an assertion."""
    s = SqliteStore(p)
    try:
        return P.import_memory(s, f, **kw)
    except Exception as x:                          # noqa: BLE001 — any refusal fails the cell by assertion
        raise AssertionError(f"the import was refused: {type(x).__name__}: {x}") from x
    finally:
        s.close()


def _refuses(p, f, match=".", **kw):
    """An import the cell expects REFUSED with a ValueError matching `match`; anything else fails by assertion."""
    import re
    s = SqliteStore(p)
    try:
        P.import_memory(s, f, **kw)
    except Exception as x:                          # noqa: BLE001
        assert isinstance(x, ValueError) and re.search(match, str(x)), f"{type(x).__name__}: {x}"
        return str(x)
    finally:
        s.close()
    raise AssertionError("the import was admitted")


def _q(p, sql, args=()):
    c = sqlite3.connect(p)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def _lines(f):
    return [json.loads(x) for x in pathlib.Path(f).read_text().splitlines() if x.strip()]


def _active(p, eid):
    return bool(_q(p, "SELECT active FROM edges WHERE id=?", (eid,))[0][0])


def _outcomes(p):
    return _q(p, "SELECT edge_id, outcome, origin, applicable, undone_at IS NOT NULL, op_id FROM migration_outcome "
                 "ORDER BY edge_id")


def _rewrite(f, out, fn):
    """Write `out` from `f`'s lines through `fn(list of dicts) -> list of dicts`."""
    pathlib.Path(out).write_text("".join(json.dumps(x) + "\n" for x in fn(_lines(f))))
    return out


# ========================================================================================== the export (era 14)
def test_an_uninitialized_feature_free_export_stamps_below_the_arity_era(tmp_path):
    """Research's D2: absence of the plan-state record IS "uninitialized", so a store with no header and no outcome
    exports exactly as before (0026 V7's byte-identity class). Mutant: write an explicit uninitialized record."""
    p = _store(tmp_path, "a.db", [_edge("x", "weight 70")])
    lines = _lines(_export(p, tmp_path, "a.jsonl"))
    assert lines[0]["version"] < P._ARITY_VERSION
    assert [x.get("record") for x in lines[1:]] == ["edge"]


def test_a_migrated_store_exports_its_plan_state_and_its_outcomes(tmp_path):
    p = _store(tmp_path, "s.db", _pair())
    _run(p)
    lines = _lines(_export(p, tmp_path, "s.jsonl"))
    assert lines[0]["version"] == P._ARITY_VERSION == P.FORMAT_VERSION == 14
    plan = [x for x in lines if x.get("record") == "arity_plan"]
    outs = [x for x in lines if x.get("record") == "arity_outcome"]
    assert plan == [{"record": "arity_plan", "state": "initialized"}]
    assert len(outs) == 1 and outs[0]["edge_id"] == "p" and (outs[0]["outcome"], outs[0]["stage"], outs[0]["origin"]) \
        == ("restored", "live", "local")
    assert set(outs[0]) - {"record"} == set(P._OUTCOME_KEYS)                # never undo_request_ref, never op_id


def test_an_initialized_empty_plan_exports_its_state(tmp_path):
    p = _store(tmp_path, "e.db", [_edge("x", "weight 70")])
    _run(p, plan_only=True, registry={k: v for k, v in DEFAULT_RELATIONS.items()
                                      if k not in ("measures", "prefers", "health_state")})
    assert [x for x in _lines(_export(p, tmp_path, "e.jsonl")) if x.get("record") == "arity_plan"] == \
        [{"record": "arity_plan", "state": "initialized-empty"}]


# =========================================================== INV-A17: the testimony chain, through the real import
def test_inv_a17_migrate_export_default_import_export_restore_still_reads_imported(tmp_path):
    """0044 §4l: migrate -> export -> default import -> export -> trusted restore reads `imported` at its end; a trusted
    restore of the store's OWN export maps local -> restored (proof). Mutant: the trust bit set from the import mode."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f1 = _export(src, tmp_path, "f1.jsonl")
    hop = _store(tmp_path, "hop.db")
    r = _import(hop, f1)
    assert r["outcomes"] == 1 and _outcomes(hop) == [("p", "restored", "imported", 1, False, None)]
    f2 = _export(hop, tmp_path, "f2.jsonl")
    end = _store(tmp_path, "end.db")
    _import(end, f2, restore=True)
    assert _outcomes(end) == [("p", "restored", "imported", 1, False, None)]          # testimony, never upgraded
    own = _store(tmp_path, "own.db")
    r = _import(own, f1, restore=True)
    rows = _outcomes(own)
    assert [(e, o, origin) for e, o, origin, *_ in rows] == [("p", "restored", "restored")] and rows[0][5]
    with pytest.raises(DM.UndoRefused):                                          # no undo from testimony
        s = SqliteStore(hop)
        try:
            s.undo_restoration(U, "p", correlation_id="undo-1")
        finally:
            s.close()


# ===================================================== INV-A23: replay by comparison over the staged union
def test_inv_a23_an_unchanged_replay_is_a_no_op_in_both_modes(tmp_path):
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    dst = _store(tmp_path, "d.db")
    assert _import(dst, f)["outcomes"] == 1
    r = _import(dst, f)
    assert (r["outcomes"], r["outcomes_existing"]) == (0, 1) and len(_outcomes(dst)) == 1
    own = _store(tmp_path, "o.db")
    _import(own, f, restore=True)
    r = _import(own, f, restore=True)
    assert (r["outcomes"], r["outcomes_existing"]) == (0, 1)


def test_inv_a23_a_changed_field_under_the_same_uid_refuses_beside_an_unrelated_new_edge(tmp_path):
    """The round-3 negative probe: one field changed under the same uid, plus an unrelated new edge in the same import,
    refuses the WHOLE unit — the new edge is not written. Mutant: equal uid alone admits."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    dst = _store(tmp_path, "d.db")
    _import(dst, f)

    def change(lines):
        for x in lines:
            if x.get("record") == "arity_outcome":
                x["successor_evidence"] = ["none", []]
        new = dict(next(x for x in lines if x.get("record") == "edge" and x.get("id") == "n"))
        new.update(id="brand-new", relation="works_on", object="chess", supersedes=None)
        return lines + [new]
    g = _rewrite(f, tmp_path / "g.jsonl", change)
    _refuses(dst, g, match="different projection")
    assert not _q(dst, "SELECT 1 FROM edges WHERE id='brand-new'")


def test_inv_a23_an_ended_held_episode_is_never_revived_by_a_live_arrival(tmp_path):
    """A held row ended by a later retirement, and the same outcome arriving `live`: older evidence of the same
    episode — a no-op, and `applicable` stays 0. Mutant: let the arrival set applicable again."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    dst = _store(tmp_path, "d.db")
    _import(dst, f)
    s = SqliteStore(dst)
    try:
        s.invalidate_edge("p", datetime(2026, 10, 1, tzinfo=timezone.utc), "superseded")
    finally:
        s.close()
    assert _outcomes(dst)[0][3] == 0
    _refuses(dst, f)
    assert _outcomes(dst)[0][3] == 0


def test_inv_a23_a_z_suffix_and_an_offset_are_one_instant(tmp_path):
    """Build note D15: the projection compares canonical UTC text, so a file rewriting `+00:00` as `Z` replays."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    dst = _store(tmp_path, "d.db")
    _import(dst, f)

    def zulu(lines):
        for x in lines:
            if x.get("record") == "arity_outcome":
                x["pre_invalidated_at"] = x["pre_invalidated_at"].replace("+00:00", "Z")
        return lines
    r = _import(dst, _rewrite(f, tmp_path / "z.jsonl", zulu))
    assert r["outcomes_existing"] == 1


@pytest.mark.parametrize("field,value,reason", [
    ("pre_invalidated_at", "2025-06-01T00:00:00", "outcome-time"),          # research T2: NAIVE refuses, never compared
    ("stage", "half-done", "outcome-shape"), ("origin", "proof", "outcome-shape"),
    ("successor_evidence", ["pointer", []], "outcome-shape"), ("undone_at", "2026-01-01T00:00:00+00:00", "outcome-shape")])
def test_an_outcome_outside_its_closed_shape_refuses_the_import(tmp_path, field, value, reason):
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")

    def bad(lines):
        for x in lines:
            if x.get("record") == "arity_outcome":
                x[field] = value
        return lines
    dst = _store(tmp_path, "d.db")
    _refuses(dst, _rewrite(f, tmp_path / "b.jsonl", bad), match="arity outcome")
    assert _outcomes(dst) == []


@pytest.mark.parametrize("mutate", ["below-era", "two-plan-records", "unknown-state", "edge-not-in-unit"])
def test_the_arity_records_own_refusals(tmp_path, mutate):
    """Build note D14 and §4l's admission rule: an arity record below the era, a second or unknown plan-state record,
    an outcome whose edge the file does not carry."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")

    def bad(lines):
        if mutate == "below-era":
            lines[0]["version"] = 13
        elif mutate == "two-plan-records":
            lines.append({"record": "arity_plan", "state": "initialized-empty"})
        elif mutate == "unknown-state":
            for x in lines:
                if x.get("record") == "arity_plan":
                    x["state"] = "uninitialized"
        else:
            lines = [x for x in lines if not (x.get("record") == "edge" and x.get("id") == "p")]
        return lines
    _refuses(_store(tmp_path, "d.db"), _rewrite(f, tmp_path / "b.jsonl", bad), match="arity|outcome")


def test_d6c_one_outcome_per_destination_edge(tmp_path):
    """Two plans' outcomes for one destination edge refuse at import (build note D6c), so undo's ambiguous-outcome is
    unreachable from an import. Control: a trusted restore of a store's own export never meets it (research's Q2)."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    own = _store(tmp_path, "own.db")
    _import(own, f, restore=True)                                    # the control
    dst = _store(tmp_path, "d.db")
    _import(dst, f)

    def other_uid(lines):
        for x in lines:
            if x.get("record") == "arity_outcome":
                x["outcome_uid"] = "f" * 64
                x["plan_id"] = "another-plan"
        return lines
    _refuses(dst, _rewrite(f, tmp_path / "o.jsonl", other_uid), match="another uid")


def test_d11_a_remapped_import_twice_and_into_two_users_admits_as_edges_do(tmp_path):
    """Research's Q3: under a cross-user remap the uid is re-minted with its edge, so outcomes duplicate exactly when
    their edges do; the store-wide UNIQUE never fires. Mutant: keep the file's uid under a remap."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    dst = _store(tmp_path, "d.db")
    assert _import(dst, f, user_id="alice")["outcomes"] == 1
    assert _import(dst, f, user_id="alice")["outcomes"] == 1
    assert _import(dst, f, user_id="bob")["outcomes"] == 1
    assert len(_q(dst, "SELECT 1 FROM migration_outcome")) == 3


# ========================================================================= the owner's D3 ruling (§4l, Q9 narrowed)
def _pre_arity_file(tmp_path, *, name="pre.jsonl", rel="measures"):
    """An undecided source: an upgraded store with no plan, its old-rule retirement exported (≤13, no plan record)."""
    src = _store(tmp_path, f"src-{name}.db", _pair(rel=rel))
    f = _export(src, tmp_path, name)
    assert _lines(f)[0]["version"] < P._ARITY_VERSION
    return f


def test_d3_an_undecided_sources_candidate_is_refused_into_an_uninitialized_store(tmp_path):
    """Q9 narrowed: refused, naming the plan-only mode; nothing written. Mutant: convert silently with no plan."""
    f = _pre_arity_file(tmp_path)
    dst = _store(tmp_path, "d.db")
    _refuses(dst, f, match=r"plan_only=True")
    assert not _q(dst, "SELECT 1 FROM edges")


def test_d3_a_file_with_nothing_to_convert_is_admitted_into_an_uninitialized_store(tmp_path):
    """The narrowing: refusing a file with nothing to convert protects nothing (dev and research, ruled). Mutant: the
    literal reading — refuse every pre-arity file."""
    src = _store(tmp_path, "src.db", [_edge("x", "weight 70"), _edge("w", "chess", rel="works_on", at=PRE, reason="superseded")])
    r = _import(_store(tmp_path, "d.db"), _export(src, tmp_path, "f.jsonl"))
    assert r["edges"] == 2 and r["arity_conversion"] is None


def test_d3_an_undecided_sources_candidate_converts_under_an_initialized_plan(tmp_path):
    """Plan-only first, then the import converts: the row reinstated, one `local` outcome carrying the import's op id,
    one `import-convert` op row whose inputs digest names the file's bytes (research's Q1)."""
    import hashlib
    f = _pre_arity_file(tmp_path)
    dst = _store(tmp_path, "d.db")
    _run(dst, plan_only=True)
    r = _import(dst, f)
    assert (r["arity_conversion"], r["arity_restored"]) == ("converted", ["p"]) and _active(dst, "p")
    (eid, outcome, origin, applicable, undone, op), = _outcomes(dst)
    assert (eid, outcome, origin, applicable, undone) == ("p", "restored", "local", 1, False)
    assert _q(dst, "SELECT mode, inputs_digest FROM migration_op WHERE op_id=?", (op,)) == \
        [("import-convert", hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest())]


def test_d3_an_initialized_empty_plan_converts_nothing_and_says_so(tmp_path):
    f = _pre_arity_file(tmp_path)
    dst = _store(tmp_path, "d.db")
    _run(dst, plan_only=True, registry={k: v for k, v in DEFAULT_RELATIONS.items()
                                        if k not in ("measures", "prefers", "health_state")})
    r = _import(dst, f)
    assert r["arity_conversion"] == "nothing-to-convert" and not _active(dst, "p") and _outcomes(dst) == []


@pytest.mark.parametrize("dest_plan", [False, True])
def test_d3_a_decided_sources_unexplained_retirement_is_unknown_linkage(tmp_path, dest_plan):
    """A source that planned but did not restore exports its retirement with an `initialized` record: kept retired,
    reported, never reinstated by guess — into an initialized destination, and into an uninitialized one by the default
    names (build note D13). Mutant: unknown-linkage silent without a plan."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src, plan_only=True)
    f = _export(src, tmp_path, "f.jsonl")
    dst = _store(tmp_path, "d.db")
    if dest_plan:
        _run(dst, plan_only=True)
    r = _import(dst, f)
    assert r["arity_unknown_linkage"] == ["p"] and r["arity_conversion"] is None and not _active(dst, "p")


def test_t1_a_local_retired_row_beside_a_converting_import_stays_retired(tmp_path):
    """Research's T1: a candidate is a UNIT record not already held — conversion never rescans local rows (0044 L517,
    INV-A16). Mutant: rescan the staged union."""
    dst = _store(tmp_path, "d.db", [_edge("local-p", "weight 60", at=PRE, reason="superseded")])
    _run(dst, plan_only=True)
    r = _import(dst, _pre_arity_file(tmp_path))
    assert r["arity_restored"] == ["p"] and not _active(dst, "local-p")


def test_t4_a_registry_that_keeps_the_relation_single_has_no_candidate(tmp_path):
    """Research's T4: the candidate relation is a default-reclassified name the RECEIVING registry declares multi; a
    host whose registry keeps `measures` single is never forced to plan."""
    f = _pre_arity_file(tmp_path)
    single = dict(DEFAULT_RELATIONS)
    single["measures"] = Relation(name="measures", functional=True, desc=DEFAULT_RELATIONS["measures"].desc,
                                  arity="single")
    r = _import(_store(tmp_path, "d.db"), f, relations=single)
    assert r["arity_conversion"] is None and r["edges"] == 2


def test_d9_a_plan_written_between_preflight_and_commit_is_a_lost_race(tmp_path, monkeypatch):
    """Build note D9: the plan header is part of the expected state; a plan-only call landing between this import's
    preflight and its commit makes the first pass DESTINATION_CHANGED, and the retry decides again (now: convert)."""
    f = _pre_arity_file(tmp_path)
    dst = _store(tmp_path, "d.db")
    _run(dst, plan_only=True, op_id="op-early")       # the first pass sees an initialized plan ...
    real = SqliteStore.commit_outcome_import_plan
    calls = []

    def racing(self, user_id, plan, expected):
        if not calls:                                  # ... and the plan moves before its commit
            self._conn.execute("UPDATE plan_header SET plan_id='moved' WHERE id=1")
            self._conn.execute("UPDATE reclassification_plan SET plan_id='moved'")
            self._conn.commit()
        calls.append(expected.get("arity", {}).get("plan_id"))
        return real(self, user_id, plan, expected)
    monkeypatch.setattr(SqliteStore, "commit_outcome_import_plan", racing)
    r = _import(dst, f)
    assert len(calls) == 2 and calls[1] == "moved" and r["arity_conversion"] == "converted"
    assert _q(dst, "SELECT plan_id FROM migration_outcome") == [("moved",)]       # decided again, on the moved plan


# ============================================================== I-3: identities, endings, erased users (the verdict)
def test_i3_duplicate_identities_in_one_file(tmp_path):
    """An outcome repeated in the file with equal contents is one outcome; repeated with different contents, or a
    second outcome for the same edge under another uid, refuses the whole import (§4l's whole-unit validation)."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    out = next(x for x in _lines(f) if x.get("record") == "arity_outcome")
    twice = _rewrite(f, tmp_path / "twice.jsonl", lambda ls: ls + [dict(out)])
    assert _import(_store(tmp_path, "a.db"), twice)["outcomes"] == 1
    differ = _rewrite(f, tmp_path / "differ.jsonl", lambda ls: ls + [{**out, "successor_evidence": ["none", []]}])
    _refuses(_store(tmp_path, "b.db"), differ, match="appears twice")
    other = _rewrite(f, tmp_path / "other.jsonl", lambda ls: ls + [{**out, "outcome_uid": "e" * 64}])
    _refuses(_store(tmp_path, "c.db"), other, match="two arity outcomes")


def test_i3_an_erased_then_recreated_user_reimports_cleanly(tmp_path):
    """Erasure removes every outcome row (0044 §4g-ii), so the same file into the recreated user writes them afresh —
    no replay against an erased incarnation, no slot conflict."""
    src = _store(tmp_path, "src.db", _pair())
    _run(src)
    f = _export(src, tmp_path, "f.jsonl")
    dst = _store(tmp_path, "d.db")
    assert _import(dst, f)["outcomes"] == 1
    s = SqliteStore(dst)
    try:
        s.forget_user(U)
    finally:
        s.close()
    assert _outcomes(dst) == []
    assert _import(dst, f)["outcomes"] == 1


def test_i3_two_different_endings_refuse(tmp_path):
    """A held UNDONE row and an arriving ENDED one for the same uid are two histories, not stages of one (v1.5):
    refused. The file's edge equals the held one, so 0009 admits it and the outcome rule decides. Mutant: treat an
    ended arrival over an undone held row as an earlier stage."""
    own = _store(tmp_path, "own.db", _pair())
    _run(own)
    s = SqliteStore(own)
    try:
        s.undo_restoration(U, "p", correlation_id="undo-1")
    finally:
        s.close()
    f = _export(own, tmp_path, "f.jsonl")
    assert [x["stage"] for x in _lines(f) if x.get("record") == "arity_outcome"] == ["undone"]
    assert _import(own, f, restore=True)["outcomes_existing"] == 1                 # the undone replay itself: a no-op

    def ended(lines):
        for x in lines:
            if x.get("record") == "arity_outcome":
                x.update(stage="ended", undone_at=None)
        return lines
    _refuses(own, _rewrite(f, tmp_path / "e.jsonl", ended), restore=True, match="different projection")


# ============================================== the staged-union rules a real file cannot reach, driven directly
class _Held:
    """A store stub for `_arity_preflight`: the held outcome rows it answers, and a plan state."""
    def __init__(self, rows=(), state="uninitialized"):
        self.rows, self.state = list(rows), state

    def migration_outcomes(self, user_id):
        return [r for r in self.rows if r["user_id"] == user_id]

    def migration_outcomes_by_uid(self, uids):
        return {r["outcome_uid"]: r for r in self.rows if r["outcome_uid"] in set(uids)}

    def arity_plan_state(self):
        return {"state": self.state, "plan_id": None, "relations": frozenset()}


_O = {"outcome_uid": "u-1", "plan_id": "pl-1", "edge_id": "p", "outcome": "restored",
      "pre_invalidated_at": "2025-06-01T00:00:00+00:00", "pre_reason": "superseded",
      "successor_evidence": ["pointer", ["n"]], "stage": "live", "origin": "local", "undone_at": None}


def _held_row(**over):
    r = {"plan_id": "pl-1", "user_id": U, "edge_id": "p", "outcome": "restored",
         "pre_invalidated_at": "2025-06-01T00:00:00+00:00", "pre_reason": "superseded",
         "successor_evidence": '["pointer",["n"]]', "applicable": 1, "origin": "imported", "outcome_uid": "u-1",
         "undone_at": None, "undo_request_ref": None, "op_id": None}
    r.update(over)
    return r


def _pf(store, outcomes, edges=(), state="uninitialized"):
    return P._arity_preflight(store, "f", U, list(outcomes), state, list(edges), {}, restore=False, registry=None,
                              import_op="op-x", inputs_digest="d", notice_targets=set())


def _pf_ok(*a, **k):
    """A preflight the cell expects to ADMIT: a refusal fails the cell by assertion."""
    try:
        return _pf(*a, **k)
    except Exception as x:                          # noqa: BLE001
        raise AssertionError(f"the preflight refused: {type(x).__name__}: {x}") from x


def test_inv_a23_an_ended_held_row_and_a_live_arrival_is_older_evidence_a_no_op():
    """§4l: held `ended`, arriving differing ONLY by being live → a no-op, the held stage kept (no row written). A real
    file rarely reaches it (0009 refuses the differing edge first), so it is driven on the preflight directly. Mutant:
    let the arriving live copy count as a new history (refuse) or revive the row."""
    rows, existing, *_ = _pf_ok(_Held([_held_row(applicable=0)]), [_O])
    assert (rows, existing) == ([], 1)
    with pytest.raises(ValueError, match="different projection"):           # the reverse is NOT older evidence
        _pf(_Held([_held_row(applicable=1)]), [{**_O, "stage": "ended"}])


def test_d6b_an_edge_with_an_outcome_in_the_unit_is_never_a_candidate():
    """Build note D6b / research's T1: an undecided relay can carry imported outcomes; an edge someone already decided
    about is not converted (a remote undo is never reversed) and does not trigger the refusal. Mutant: the candidate
    test ignores the unit's outcomes."""
    p = _edge("p", "weight 78", at=PRE, reason="superseded")
    undone = {**_O, "stage": "undone", "undone_at": "2026-01-01T00:00:00+00:00"}
    rows, existing, conversion, report, _ = _pf_ok(_Held(), [undone], edges=[p])
    assert len(rows) == 1 and conversion is None and report["arity_conversion"] is None


def test_d10_a_v13_file_carrying_a_notice_is_not_refused_by_the_era_gate(tmp_path):
    """Build note D10: the notice-below-era gate keys on the redaction era (13), never on the reader's head, so a v13
    file with a notice still imports once era 14 opens. Mutant: the gate left on FORMAT_VERSION."""
    f = tmp_path / "v13.jsonl"
    f.write_text("".join(json.dumps(x) + "\n" for x in [
        {"kind": "veracium-export", "version": 13, "user_id": U, "exported_at": "2026-10-01T00:00:00+00:00"},
        {"record": "redaction", "origin": "store-elsewhere", "source_user": U, "source_event_ref": "ev-1",
         "target_kind": "edge", "target_id": "gone", "fields": ["invalidation_reason"], "marker_version": 1,
         "reason": "subject_request", "recorded_at": "2026-10-01T00:00:00+00:00"}]))
    try:
        _import(_store(tmp_path, "d.db"), f)
        refused = None
    except ValueError as x:
        refused = str(x)
    assert refused is None or "notice-below-era" not in refused and "carries redaction notices" not in refused, refused
