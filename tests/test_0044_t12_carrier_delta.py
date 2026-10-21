"""T12, the generated v16 carrier delta (V44 L102 "actual migration DDL and carrier delta"; V45 L116 "a generated
carrier delta"): the committed `specs/generated/v16-carrier-delta.md` is what a fresh derivation produces — the declared
steps from v14 (the released schema) and the ACTUAL `sqlite_master` of three real stores, each digest accepted — and the
generator refuses each defect it exists to catch (P1's matrix for `specs/evidence/0044/carrier_delta.py`). Build note
b2870871 D4/D5 with addendum 1's M3.
"""
from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "specs" / "evidence" / "0044" / "carrier_delta.py"


def _gen():
    name = "carrier_delta_0044"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, GEN)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


@pytest.fixture(scope="module")
def delta():
    return _gen().derive()


def test_the_committed_delta_is_what_a_fresh_derivation_produces(delta):
    """Data to data: the committed artifact equals a fresh derivation's rendering, and the derivation raises none of
    the generator's refusals (every actual digest accepted; every new TEXT/BLOB column placed by 0041's account)."""
    g = _gen()
    assert g.problems(delta) == []
    assert g.render(delta) == g.OUT.read_text(), "regenerate with --write"


def test_the_v16_step_is_exactly_the_programmes_objects_and_t11b_added_none(delta):
    """D5 ("T11b changed no DDL"): the v15 -> v16 step adds exactly the programme's seventeen objects and changes the
    two ALTERed tables — the registry and counter (T3), the arity tables (T5-2), `replies` (T10a) — and nothing the
    act-portability tranche introduced; v14 -> v15 is 0041's four. The three actual stores manifest the three accepted
    shapes research measured at T12's stage-1 read (d2669f67, bbaa3a27, 4c268285)."""
    s = delta["steps"]["v15 -> v16"]
    assert s["added"] == sorted(["act_counter", "arity_era", "arity_inventory", "ix_arity_inventory_user",
                                 "ix_migration_outcome_edge", "ix_refusal_inventory_user", "ix_replies_edge",
                                 "ix_request_registry_target", "migration_op", "migration_outcome", "migration_run",
                                 "plan_header", "reclassification_plan", "refusal_inventory", "replies",
                                 "request_registry", "ux_replies_resolve"])
    assert (s["changed"], s["removed"]) == (["confirmations", "redactions"], [])
    assert delta["steps"]["v14 -> v15"]["added"] == ["episode_event", "ix_episode_event_lookup", "ix_redactions_target",
                                                      "redactions"]
    assert [(a["label"], a["digest"][:8], a["accepted"], sorted(a["differs"])) for a in delta["actual"]] == [
        ("created at v16", "d2669f67", True, []), ("migrated from v14", "bbaa3a27", True, ["confirmations"]),
        ("migrated from v15", "4c268285", True, ["confirmations", "redactions"])]
    assert len(delta["manifests"]) == 11


def test_the_delta_refuses_each_planted_defect(delta):
    """P1's matrix for carrier_delta.py: an actual store whose digest is outside accepted_digests(16); a new TEXT/BLOB
    column no account places; a step that removes an object; and the column parser does not read a table constraint
    (`UNIQUE(…)`, `CHECK (…)`) as a column. Each control is the unplanted delta."""
    g = _gen()
    assert g.problems(delta) == []
    d = copy.deepcopy(delta)
    d["actual"][1]["accepted"] = False
    assert any("outside accepted_digests(16)" in x for x in g.problems(d))
    d = copy.deepcopy(delta)
    d["tables"][0]["columns"][0]["class"] = None
    assert any("is neither a treated side path nor in DDL_ACCOUNT" in x for x in g.problems(d))
    d = copy.deepcopy(delta)
    d["steps"]["v15 -> v16"]["removed"] = ["edges"]
    assert any("removes ['edges']" in x for x in g.problems(d))
    cols = g._columns("CREATE TABLE t (a TEXT NOT NULL, b INTEGER, UNIQUE(a, b), CHECK ((a = 'x') = (b IS NULL)))")
    assert cols == [("a", "TEXT"), ("b", "INTEGER")]
    side = {"t.a": "REPLACE"}
    assert g._carrier_class("t", "a", "TEXT", {}, side) == "treated side path (REPLACE)"
    assert g._carrier_class("t", "c", "TEXT", {}, side) is None
    assert g._carrier_class("t", "b", "INTEGER", {}, side).startswith("non-text")
