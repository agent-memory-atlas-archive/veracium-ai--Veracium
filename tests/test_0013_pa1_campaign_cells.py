"""The 0013-PA1 mutation campaign's CELLS (specs/evidence/0013/pa1_campaign.py, part B).

`test_cell_*` are the kill cells (derived by the campaign from this file, never a hand list); `test_honest_*` are the
legitimate flows a mutant must not break, declared per mutant. Every observation is ASSERTED: a migration that must
succeed and refuses fails as an AssertionError naming the refusal, and a refusal that must happen is checked for its
step, its position and an unchanged store. Only the store's own refusal type is converted (StoreVersionError, which
MigrationPostconditionError subclasses); any OTHER exception propagates as itself, so the campaign's classifier never
counts an unrelated failure as a kill.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _campaign():
    name = "veracium_pa1_campaign"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "specs" / "evidence" / "0013" / "pa1_campaign.py")
        m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return sys.modules[name]


def _mig():
    import veracium.store.migration as mig
    return mig


def _fixture(tmp_path, *, observed_at=None, extra=None, second=False) -> str:
    """The v2#0 accepted shape, populated by the step-table instrument (every table, one legacy outcome row lacking
    observed_at), its legacy row optionally edited; `second` adds a second legacy outcome of a different chain."""
    p = str(tmp_path / "v2.db")
    _campaign().fresh_fixture(p, "v2#0")
    c = sqlite3.connect(p)
    eid, blob = c.execute("SELECT id, json FROM episodes").fetchone()
    row = json.loads(blob)
    if observed_at is not None:
        row["provenance"]["observed_at"] = observed_at
    row.update(extra or {})
    c.execute("UPDATE episodes SET json=? WHERE id=?", (json.dumps(row), eid))
    if second:
        r2 = dict(row, id="leg-2", summary="legacy use 2")
        r2["provenance"] = dict(row["provenance"], evidence_ref="run-2")
        c.execute("INSERT INTO episodes(id,user_id,date,json) VALUES(?,?,?,?)",
                  ("leg-2", r2["user_id"], r2["date"], json.dumps(r2)))
    c.commit(); c.close()
    return p


def _must_migrate(path, plan=None) -> dict:
    from veracium.store.schema_version import StoreVersionError
    res = _campaign().run_case(path, plan)
    e = res["exc"]
    if e is not None and not isinstance(e, StoreVersionError):
        raise e                                                   # unrelated: never converted into a kill
    assert e is None, f"a correct migration was refused: {e}"
    assert res["result"] == "migrated", res["result"]
    return res


def _must_refuse_at(build, step, perturb=None) -> None:
    """`build()` makes the fixture and returns its path (called again for the perturbed run, so the run sees the same
    edited row). A perturbation (`perturb` = (mode, payload) on the step's FIRST write, or None for a fixture that
    must refuse) refuses AT `step`: the postcondition error naming it exactly, before any later step's write, the store
    unchanged."""
    from veracium.store.schema_version import StoreVersionError
    camp, L = _campaign(), _campaign().lib()
    base = None
    plan = None
    path = build()
    if perturb is not None:
        base = camp.run_case(path)
        if base["exc"] is not None and not isinstance(base["exc"], StoreVersionError):
            raise base["exc"]                                     # unrelated: never converted into a kill
        assert base["exc"] is None, f"the unperturbed ladder must migrate: {base['exc']}"
        k = camp.step_ranges(base["writes"])[step][0]
        path = build()
        plan = L["Plan"](k=k, mode=perturb[0], expect=base["writes"][k]["sql"])
        plan.payload = perturb[1]
    res = camp.run_case(path, plan)
    e = res["exc"]
    if e is not None and not isinstance(e, StoreVersionError):
        raise e
    mig = _mig()
    assert isinstance(e, mig.MigrationPostconditionError), f"expected a refusal at {step!r}, got {e!r}"
    assert e.step == step, f"refused at {e.step!r}, not at {step!r}"
    assert res["pre"] == res["post"], "the refusal left the store changed"
    if base is not None:
        v = camp.judge(res, step, base["writes"])
        assert v["position"], (f"refused at {step!r} only after later steps wrote: {v['issued']} write(s) issued, the "
                               f"step's last is #{v['step_last_write']}")


# ---- the per-step cells: one perturbation of each step, refused AT the step (M117–M123) ----------------------------
def test_cell_a_perturbed_outcome_chain_refuses_at_its_step(tmp_path):
    _must_refuse_at(lambda: _fixture(tmp_path), _mig().STEP_CHAINS, ("alter", None))


def test_cell_a_skipped_wiki_drop_refuses_at_its_step(tmp_path):
    _must_refuse_at(lambda: _fixture(tmp_path), _mig().STEP_WIKI, ("skip", None))


def test_cell_a_perturbed_store_identity_refuses_at_its_step(tmp_path):
    _must_refuse_at(lambda: _fixture(tmp_path), _mig().STEP_IDENTITY, ("alter", None))


def test_cell_a_perturbed_baseline_event_refuses_at_its_step(tmp_path):
    _must_refuse_at(lambda: _fixture(tmp_path), _mig().STEP_BASELINE, ("alter", None))


def test_cell_a_skipped_store_epoch_refuses_at_its_step(tmp_path):
    _must_refuse_at(lambda: _fixture(tmp_path), _mig().STEP_EPOCH, ("skip", None))


def test_cell_a_perturbed_stamp_refuses_at_the_stamp(tmp_path):
    _must_refuse_at(lambda: _fixture(tmp_path), _mig().STEP_STAMP, ("alter", None))


# ---- M121: the v2→v3 conversion against the RAW legacy row ---------------------------------------------------------
def test_cell_a_legacy_row_in_isoformat_plus0000_form_migrates(tmp_path):
    """datetime.isoformat()'s '+00:00' comes back as 'Z' through the dump: equal as the declared type, not as text."""
    p = _fixture(tmp_path, observed_at="2026-09-03T10:00:00+00:00")
    _must_migrate(p)
    c = sqlite3.connect(p)
    got = json.loads(c.execute("SELECT json FROM episodes").fetchone()[0])["provenance"]["observed_at"]
    c.close()
    assert datetime.fromisoformat(got.replace("Z", "+00:00")) == datetime(2026, 9, 3, 10, tzinfo=timezone.utc)


def test_cell_a_present_observed_at_is_kept(tmp_path):
    p = _fixture(tmp_path, observed_at="2026-01-01T00:00:00Z")
    _must_migrate(p)
    c = sqlite3.connect(p)
    got = json.loads(c.execute("SELECT json FROM episodes").fetchone()[0])["provenance"]["observed_at"]
    c.close()
    assert got == "2026-01-01T00:00:00Z", f"a present observed_at was rewritten to {got!r}"


def test_cell_a_missing_observed_at_is_filled_from_the_one_clock_read(tmp_path, monkeypatch):
    """B1/M121: two legacy rows lacking observed_at, under a clock that ADVANCES on every call: the migration reads
    it once, and every fill equals store_epoch.started_at."""
    mig = _mig()
    t0 = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    calls = []

    def advancing():
        calls.append(1)
        return t0 + timedelta(seconds=len(calls))

    monkeypatch.setattr(mig, "_clock", advancing)
    p = _fixture(tmp_path, second=True)
    _must_migrate(p)
    assert len(calls) == 1, f"the migration read its clock {len(calls)} times"
    c = sqlite3.connect(p)
    fills = [json.loads(b)["provenance"]["observed_at"] for (b,) in c.execute("SELECT json FROM episodes")]
    started = c.execute("SELECT started_at FROM store_epoch").fetchone()[0]
    c.close()
    assert len(fills) == 2
    assert all(datetime.fromisoformat(f.replace("Z", "+00:00")) == datetime.fromisoformat(started) for f in fills)


def test_cell_an_added_key_with_a_non_default_value_refuses_at_the_chain_step(tmp_path):
    _must_refuse_at(lambda: _fixture(tmp_path, observed_at="2026-01-01T00:00:00Z"), _mig().STEP_CHAINS,
                    ("jsonset", {"context_ref": "not-the-default"}))


def test_cell_an_undeclared_raw_key_refuses_at_the_chain_step(tmp_path):
    """A raw key no model declares, outside the retired set (0016 D2), refuses — with a PRESENT observed_at, so a
    model load of the raw row has nothing to refill and only the dropped key distinguishes it."""
    _must_refuse_at(lambda: _fixture(tmp_path, observed_at="2026-01-01T00:00:00Z", extra={"not_a_field": 1}),
                    _mig().STEP_CHAINS)


# ---- the honest flows ----------------------------------------------------------------------------------------------
def test_honest_a_legacy_row_with_a_present_observed_at_migrates(tmp_path):
    _must_migrate(_fixture(tmp_path, observed_at="2026-01-01T00:00:00Z"))


def test_honest_a_legacy_row_lacking_observed_at_migrates(tmp_path):
    _must_migrate(_fixture(tmp_path))
