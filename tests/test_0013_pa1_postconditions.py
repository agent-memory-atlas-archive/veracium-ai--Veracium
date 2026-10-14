"""specs/0013 §4f (v33, internal finding 0013-PA1): every migration step's output is checked AT THE STEP.

The CONTROLS of the closure (the mutation table, specs/evidence/0013/pa1_campaign.py, carries the kills):
- correct legacy rows migrate, in every datetime form an older writer could have produced (isoformat's "+00:00", a
  fraction, pydantic's "Z", a space separator, a naive value) — a postcondition comparing strings would refuse them;
- a v0.3–v0.4-shaped outcome row carrying the retired `provenance.source_type` migrates (0016 D2), and any OTHER
  undeclared key refuses;
- the migration reads its clock ONCE (B1): every filled `observed_at`, `store_epoch.started_at` and every baseline
  `recorded_at` are the same instant, under a clock that advances on every call;
- the model-shape guards the postcondition's derivation rests on (N2, N3).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from veracium.schema import Edge, Episode, EvidenceAuthor, Provenance
from veracium.store import migration as M
from veracium.store.migration import MigrationPostconditionError, migrate_store
from veracium.store.schema_version import SCHEMA_V2, SCHEMA_VERSION


def _legacy(eid, *, observed_at=None, extra_prov=None, extra=None, kind="outcome"):
    prov = {"author_of_evidence": "system", "evidence_ref": f"run-{eid}"}
    if observed_at is not None:
        prov["observed_at"] = observed_at
    prov.update(extra_prov or {})
    row = {"id": eid, "user_id": "u", "date": "2026-05-05", "summary": f"legacy {eid}", "kind": kind,
           "edge_id": f"e-{eid}", "outcome": "concurred", "provenance": prov}
    row.update(extra or {})
    return row


def _edge_json(eid):
    return Edge(id=eid, user_id="u", subject="user", relation="lives_in", object="Porto",
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="m")).model_dump_json()


def _v2_store(path, episodes, edges=()):
    conn = sqlite3.connect(path)
    for o in SCHEMA_V2:
        conn.execute(o.ddl)
    for ep in episodes:
        conn.execute("INSERT INTO episodes(id,user_id,date,json) VALUES(?,?,?,?)",
                     (ep["id"], ep["user_id"], ep["date"], json.dumps(ep)))
    for eid in edges:
        conn.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) "
                     "VALUES(?,?,?,?,?,1,0,?)", (eid, "u", "user", "lives_in", "Porto", _edge_json(eid)))
    conn.execute("PRAGMA user_version = 2")
    conn.commit(); conn.close()


def _episodes(path):
    conn = sqlite3.connect(path)
    try:
        return {eid: json.loads(b) for eid, b in conn.execute("SELECT id, json FROM episodes")}
    finally:
        conn.close()


@pytest.mark.parametrize("form", [
    "2026-09-03T10:00:00+00:00",            # datetime.isoformat()'s default — reformatted to "Z" by the dump
    "2026-09-03T10:00:00.000000+00:00",
    "2026-09-03T10:00:00Z",
    "2026-09-03 10:00:00",                  # a space separator, naive — stays naive
    "2026-09-03T10:00:00",
])
def test_a_legacy_row_in_every_datetime_form_migrates(tmp_path, form):
    p = str(tmp_path / "v2.db")
    _v2_store(p, [_legacy("a", observed_at=form)])
    assert migrate_store(p) == "migrated"
    got = _episodes(p)["a"]["provenance"]["observed_at"]
    want = datetime.fromisoformat(form.replace("Z", "+00:00"))
    assert datetime.fromisoformat(got.replace("Z", "+00:00")) == want            # the same instant (or naive value)


def test_an_old_release_outcome_row_with_the_retired_source_type_migrates(tmp_path):
    """v0.3.0–v0.4.8 stamped schema 1 and REQUIRED `provenance.source_type`: every real legacy outcome row carries it.
    0016 D2 drops it on read; the step persists that, and the postcondition admits exactly that key."""
    p = str(tmp_path / "v2.db")
    _v2_store(p, [_legacy("a", observed_at="2026-09-03T10:00:00+00:00", extra_prov={"source_type": "conversation"})])
    assert migrate_store(p) == "migrated"
    assert "source_type" not in _episodes(p)["a"]["provenance"]


@pytest.mark.parametrize("where", ["top", "provenance"])
def test_any_other_undeclared_key_refuses_at_the_chain_step_and_changes_nothing(tmp_path, where):
    p = str(tmp_path / "v2.db")
    row = _legacy("a", observed_at="2026-09-03T10:00:00Z",
                  **({"extra": {"not_a_field": 1}} if where == "top" else {"extra_prov": {"not_a_field": 1}}))
    _v2_store(p, [row])
    before = open(p, "rb").read()
    with pytest.raises(MigrationPostconditionError) as e:
        migrate_store(p)
    assert e.value.step == M.STEP_CHAINS and e.value.reason == "unsupported-migration"
    assert any("not_a_field" in x for x in e.value.problems)
    conn = sqlite3.connect(p)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    conn.close()
    assert _episodes(p)["a"] == row                                               # nothing converted


def test_the_migration_reads_its_clock_once_and_records_the_fill(tmp_path, monkeypatch):
    """B1: every filled `observed_at`, `store_epoch.started_at` and every baseline `recorded_at` are ONE instant —
    under a clock that ADVANCES on every call, so a per-row or per-step re-read cannot pass by luck."""
    t0 = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    calls = []
    def advancing():
        calls.append(1)
        return t0 + timedelta(seconds=len(calls))
    monkeypatch.setattr(M, "_clock", advancing)
    p = str(tmp_path / "v2.db")
    _v2_store(p, [_legacy("a"), _legacy("b"), _legacy("c", observed_at="2026-01-01T00:00:00Z")],
              edges=["e-1", "e-2"])
    assert migrate_store(p) == "migrated"
    assert len(calls) == 1, f"the migration read its clock {len(calls)} times"
    the_read = t0 + timedelta(seconds=1)
    eps = _episodes(p)
    filled = [datetime.fromisoformat(eps[k]["provenance"]["observed_at"].replace("Z", "+00:00")) for k in ("a", "b")]
    conn = sqlite3.connect(p)
    started = conn.execute("SELECT started_at FROM store_epoch").fetchone()[0]
    recorded = [r[0] for r in conn.execute("SELECT recorded_at FROM edge_event WHERE kind='baseline'")]
    conn.close()
    assert filled == [the_read, the_read]
    assert datetime.fromisoformat(started) == the_read
    assert len(recorded) == 2 and all(datetime.fromisoformat(r) == the_read for r in recorded)
    assert eps["c"]["provenance"]["observed_at"] in ("2026-01-01T00:00:00Z",)    # a present value is never refilled


def test_the_migrated_store_stamps_head(tmp_path):
    p = str(tmp_path / "v2.db")
    _v2_store(p, [_legacy("a", observed_at="2026-09-03T10:00:00Z")], edges=["e-1"])
    migrate_store(p)
    conn = sqlite3.connect(p)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    conn.close()


def test_the_only_nested_model_in_an_episode_is_provenance():
    """N2: the postcondition recurses into fields DERIVED as model-typed; this pins what that derivation finds today,
    so a new nested model is a visible change, not a silent one."""
    assert set(M._nested_models(Episode)) == {"provenance"}
    assert M._nested_models(Provenance) == {}


def test_the_only_default_factory_field_is_provenance_observed_at():
    """N3: the step's contract covers exactly one clock-sourced default; a new factory field fails HERE, not on a live
    migration (where the postcondition would refuse it as uncovered)."""
    factory = {(n,) for n, f in Episode.model_fields.items() if f.default_factory is not None}
    factory |= {("provenance", n) for n, f in Provenance.model_fields.items() if f.default_factory is not None}
    assert factory == {("provenance", "observed_at")}
