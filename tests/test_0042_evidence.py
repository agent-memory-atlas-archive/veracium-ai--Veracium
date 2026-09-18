"""specs/0042 (exercised guarantees, draft) — the round-1 verdict's executed claims,
reproduced as the reviewer found them and kept runnable, and the evidence the next
package carries in answer: the decision-site inventory over all of src and the two row shapes (the
question row is the harness spec's; the shape is kept beside the census row it was
designed with). The examiner projection and the abstention counter-cases moved to
the harness spec's evidence directory with the split. Every "shipped behaviour" check here FAILS the day the behaviour changes —
when the harness spec's adjudicator exists, these are its first controls.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _fixture_mem(db):
    spec = importlib.util.spec_from_file_location("t_introspect", ROOT / "tests" / "test_introspect_cli.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m._seeded_mem(db)


# ---- amendment 4: the domain ---------------------------------------------------------

def test_a4_inventory_covers_all_of_src_and_states_its_unit():
    inv = _load("decision_site_inventory")
    rows = inv.inventory(); s = inv.summary(rows)
    assert s["modules_scanned"] == len(list((ROOT / "src/veracium").rglob("*.py")))
    assert "scope.py" in s["per_module"] and s["per_module"]["scope.py"]["RETURN_FALSE"] >= 10
    assert s["per_module"]["graph.py"]["RETURN_FALSE"] >= 10 and s["per_module"]["gate.py"]["RETURN_FALSE"] >= 3
    assert s["total"] == len(rows) == sum(s["by_kind"].values())
    assert "identity (module, qualname, line)" in s["unit"]
    ids = {(r["module"], r["qualname"], r["line"], r["kind"]) for r in rows}
    assert len(ids) == len(rows)                       # identity is unique per row


def test_a4_the_five_file_lexical_count_is_not_a_bound_on_the_inventory():
    inv = _load("decision_site_inventory")
    s = inv.summary(inv.inventory())
    five = ("graph.py", "ingest.py", "schema.py", "gate.py", "lifecycle.py")
    outside = sum(c["RAISE"] + c["RETURN_FALSE"] for m, c in s["per_module"].items() if m not in five)
    assert outside > 0, "the domain the spec chose excluded decision sites"


# ---- the row shapes -------------------------------------------------------------------

def test_rows_examples_validate_and_every_mutant_is_refused():
    rs = _load("row_shapes")
    assert all(rs.validate_census_row(r) == [] for r in rs.CENSUS_EXAMPLE)
    assert all(rs.validate_question_row(r) == [] for r in rs.QUESTION_EXAMPLE)
    assert "DISABLED" in rs.CENSUS_STATUS and len(rs.CENSUS_STATUS) == 4
    mutants = [
        ({"id": "x", "status": "UNEXERCISED", "consulted": 3, "fired": 0, "errors": 0}, "UNEXERCISED with consulted != 0"),
        ({"id": "x", "status": "EXERCISED", "consulted": 3, "fired": 0, "errors": 1}, "errors > 0 must be UNMEASURED"),
        ({"id": "x", "status": "DISABLED", "consulted": 0, "fired": 0, "errors": 0}, "DISABLED carries no counts"),
        ({"id": "x", "status": "EXERCISED", "consulted": 3, "fired": 4, "errors": 0}, "fired > consulted"),
        ({"id": "x", "status": "MEASURED", "consulted": 3, "fired": 0, "errors": 0}, "not in"),
    ]
    for row, expected in mutants:
        p = rs.validate_census_row(row); assert any(expected in x for x in p), (row, p)
    q = dict(rs.QUESTION_EXAMPLE[2]); q["observed_outcome"] = "ANSWERED"    # a timeout with a verdict
    assert any("iff" in x for x in rs.validate_question_row(q))
    q = dict(rs.QUESTION_EXAMPLE[0]); q["fixture_class"] = "present"       # outside the closed set
    assert any("not in" in x for x in rs.validate_question_row(q))


def test_rows_rates_name_their_denominators_and_a_timeout_changes_no_completed_rate():
    rs = _load("row_shapes")
    v = rs.rates(rs.QUESTION_EXAMPLE, "veracium")
    assert v["questions"] == 3 and v["completed"] == 2 and v["completion_rate"] == (2, 3)
    assert v["refusal_rate_over_completed"] == (1, 2) and v["not_completed_by_terminal"]["timeout"] == 1
    # INV-4 as it must read: a timeout is its own terminal row; the rate OVER COMPLETED is unchanged
    more = rs.QUESTION_EXAMPLE + [{"question_id": "q020", "arm": "veracium", "fixture_class": "absent",
                                   "terminal": "timeout", "observed_outcome": None, "claimed_reason": "", "support": "none"}]
    assert rs.rates(more, "veracium")["refusal_rate_over_completed"] == (1, 2)
    assert rs.rates(more, "veracium")["completion_rate"] == (2, 4)
    assert rs.rates([], "baseline")["refusal_rate_over_completed"] == "UNDEFINED"


# ---- the scripts run as the package will run them ------------------------------------

@pytest.mark.parametrize("script,args", [("decision_site_inventory.py", []),
                                         ("row_shapes.py", [])])
def test_every_evidence_script_runs_and_exits_zero(script, args):
    r = subprocess.run([sys.executable, str(EVIDENCE / script), *args], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
