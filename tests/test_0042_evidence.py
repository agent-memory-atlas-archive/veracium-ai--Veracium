"""specs/0042 (exercised guarantees, draft) — the census evidence, bound. Round 2 found the
previous evidence written to DEMONSTRATE clauses rather than attack them (a validator that
refused only the mutants its author imagined; an inventory over the kinds it could parse). These
checks are the reviewer's: the state table is PARSED from the spec so the code cannot drift from
it; every refusal is demonstrated on the input it refuses; the three-sets check is shown REFUSING
on the real tree, which is the honest state until 738 decisions exist.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


# ---- Part A-1: the state table, parsed from the spec ------------------------------------

def test_a1_state_table_is_parsed_from_the_spec_and_the_code_conditions_match_it_one_to_one():
    ct = _load("census_table")
    assert ct.STATUSES == ("DISABLED", "UNDECLARED", "UNMEASURED", "UNREACHED", "UNEXERCISED", "EXERCISED")
    assert [r["precedence"] for r in ct.STATE_TABLE] == [1, 2, 3, 4, 5, 6]
    assert set(ct.CONDITIONS) == {r["condition"] for r in ct.STATE_TABLE}   # no orphan condition either way


def test_a1_parser_refuses_a_missing_table_and_a_count_that_disagrees_with_the_prose():
    ct = _load("census_table")
    text = ct.SPEC.read_text()
    with pytest.raises(RuntimeError, match="not found"):
        ct.parse_state_table(text.replace("### Part A-1", "### Part A-one"))
    with pytest.raises(RuntimeError, match="disagree"):
        ct.parse_state_table(text.replace("SIX statuses, not five", "FIVE statuses, not five", 1))


@pytest.mark.parametrize("tup,expected", [
    (dict(enabled=False, declared=True, errors=0, consulted=5, fired=2), "DISABLED"),
    (dict(enabled=True, declared=False, errors=0, consulted=5, fired=2), "UNDECLARED"),
    (dict(enabled=True, declared=True, errors=1, consulted=5, fired=2), "UNMEASURED"),
    (dict(enabled=True, declared=True, errors=0, consulted=0, fired=0), "UNREACHED"),
    (dict(enabled=True, declared=True, errors=0, consulted=10, fired=0), "UNEXERCISED"),   # the central case
    (dict(enabled=True, declared=True, errors=0, consulted=10, fired=3), "EXERCISED"),
    (dict(enabled=False, declared=False, errors=9, consulted=0, fired=0), "DISABLED"),       # precedence: first match wins
])
def test_a1_every_tuple_maps_to_exactly_one_status_in_precedence_order(tup, expected):
    assert _load("census_table").status_of(tup) == expected


def test_a1_report_gate_refuses_every_named_defect_and_emits_the_undeclared_row():
    ct = _load("census_table")
    decl = {"a", "b"}
    snap = {"snapshot_id": "s", "process_started": "t0", "window_start": "t1", "window_end": "t2", "enabled": True}
    good = {"snapshot": snap, "rows": ct.report_rows({"a": dict(consulted=10, fired=0, errors=0), "b": dict(consulted=0, fired=0, errors=0)}, decl, True)}
    assert ct.validate_report(good, decl) == []
    assert [r["status"] for r in good["rows"]] == ["UNEXERCISED", "UNREACHED"]
    rows = ct.report_rows({"a": dict(consulted=1, fired=1, errors=0), "b": dict(consulted=0, fired=0, errors=0), "zzz": dict(consulted=1, fired=0, errors=0)}, decl, True)
    p = ct.validate_report({"snapshot": snap, "rows": rows}, decl)
    assert any("UNDECLARED id 'zzz'" in x for x in p) and any(r["id"] == "zzz" and r["status"] == "UNDECLARED" for r in rows)   # emitted AND refused
    neg = {"snapshot": snap, "rows": [{"id": "a", "status": "EXERCISED", "consulted": -3, "fired": 1, "errors": 0}, {"id": "b", "status": "UNREACHED", "consulted": 0, "fired": 0, "errors": 0}]}
    assert any("negative" in x for x in ct.validate_report(neg, decl))
    missing = {"snapshot": snap, "rows": [{"id": "a", "status": "UNREACHED", "consulted": 0, "fired": 0, "errors": 0}]}
    assert any("declared id 'b' absent" in x for x in ct.validate_report(missing, decl))
    dup = {"snapshot": snap, "rows": good["rows"] + [good["rows"][0]]}
    assert any("duplicate id" in x for x in ct.validate_report(dup, decl))
    wrong = {"snapshot": snap, "rows": [{"id": "a", "status": "EXERCISED", "consulted": 10, "fired": 0, "errors": 0}, good["rows"][1]]}
    assert any("table says UNEXERCISED" in x for x in ct.validate_report(wrong, decl))
    disabled_counts = {"snapshot": {**snap, "enabled": False}, "rows": [{"id": "a", "status": "DISABLED", "consulted": 3, "fired": 0, "errors": 0}, {"id": "b", "status": "DISABLED"}]}
    assert any("DISABLED carries counts" in x for x in ct.validate_report(disabled_counts, decl))
    content = {"snapshot": snap, "rows": [{**good["rows"][0], "text": "user lives in Porto"}, good["rows"][1]]}
    assert any("INV-8" in x for x in ct.validate_report(content, decl))
    nowin = {"snapshot": {k: v for k, v in snap.items() if k != "window_end"}, "rows": good["rows"]}
    assert any("window_end" in x for x in ct.validate_report(nowin, decl))


# ---- Part A-2: the trace diff over exactly the named fields --------------------------------

def test_a2_three_arm_trace_diff_compares_only_the_named_fields_and_refuses_extra_ones():
    ct = _load("census_table")
    t = [{"seq": 0, "site_id": "gate.answer", "decision": "refuse"}, {"seq": 1, "site_id": "ingest.q", "decision": "request"}]
    assert ct.three_arm_diff(t, t, t)["identical"]
    reordered = [t[1] | {"seq": 0}, t[0] | {"seq": 1}]
    d = ct.three_arm_diff(t, t, reordered); assert not d["identical"] and d["first_divergence"] == ("healthy", 0)
    with pytest.raises(ValueError, match="fields"):
        ct.trace_key([{**t[0], "duration_ms": 3}])          # wall-clock cannot leak into the comparison
    with pytest.raises(ValueError, match="fields"):
        ct.trace_key([{"seq": 0, "site_id": "x"}])           # a missing named field refuses too


# ---- Part A-0-bis: the three sets -----------------------------------------------------------

def test_a0bis_the_three_sets_check_refuses_each_wrong_pair_and_passes_the_complete_fixture():
    rp = _load("reviewed_points")
    assert rp.check_three_sets(rp.FIXTURE_DISCOVERED, rp.FIXTURE_REVIEWED, rp.FIXTURE_DECLARED, rp.FIXTURE_DECLARED) == []
    no_decision = {k: v for k, v in rp.FIXTURE_REVIEWED.items() if "ingest" not in k}
    assert any("NO DECISION" in x for x in rp.check_three_sets(rp.FIXTURE_DISCOVERED, no_decision, rp.FIXTURE_DECLARED, rp.FIXTURE_DECLARED))
    undeclared = rp.FIXTURE_DECLARED - {"gate.py:answer:10:RAISE"}
    assert any("REVIEWED-as-enforcement but NOT DECLARED" in x for x in rp.check_three_sets(rp.FIXTURE_DISCOVERED, rp.FIXTURE_REVIEWED, undeclared, undeclared))
    overdeclared = rp.FIXTURE_DECLARED | {"ingest.py:_check_arg:30:RAISE"}
    assert any("DECLARED but not REVIEWED-as-enforcement" in x for x in rp.check_three_sets(rp.FIXTURE_DISCOVERED, rp.FIXTURE_REVIEWED, overdeclared, overdeclared))
    assert any("UNDECLARED" in x for x in rp.check_three_sets(rp.FIXTURE_DISCOVERED, rp.FIXTURE_REVIEWED, rp.FIXTURE_DECLARED, rp.FIXTURE_DECLARED | {"ghost"}))
    malformed = {**rp.FIXTURE_REVIEWED, "ingest.py:_check_arg:30:RAISE": {"decision": "maybe", "reason": "", "reviewer": ""}}
    assert any("malformed" in x for x in rp.check_three_sets(rp.FIXTURE_DISCOVERED, malformed, rp.FIXTURE_DECLARED, rp.FIXTURE_DECLARED))


def test_a0bis_on_the_real_tree_the_third_source_bites_because_no_decisions_exist_yet():
    rp = _load("reviewed_points")
    real = rp.load_discovered()
    reviewed = rp.load_reviewed(rp.REVIEWED_PATH) if rp.REVIEWED_PATH.exists() else {}
    probs = rp.check_three_sets(real, reviewed, set(), set())
    undecided = sum(1 for x in probs if "NO DECISION" in x)
    assert undecided == len(real) - len([c for c in reviewed if c in {rp.candidate_id(s) for s in real}])
    assert undecided > 0, "every discovered candidate has a decision — update this test to assert the pass"


# ---- A4: discovery kinds -----------------------------------------------------------------

def test_a4_discovery_finds_the_four_symbols_round_2_named_and_states_its_unit():
    inv = _load("decision_site_inventory")
    rows = inv.inventory(); s = inv.summary(rows)
    q = {r["qualname"] for r in rows}
    assert {"Edge.assertable", "Edge.quarantined", "partition_parts", "exclude_procedural"} <= q
    assert set(s["by_kind"]) == {"RAISE", "RETURN_FALSE", "RETURN_NONE", "BOOL_RETURN", "FILTER_RETURN"}
    assert s["modules_scanned"] == len(list((ROOT / "src/veracium").rglob("*.py")))
    assert "scope.py" in s["per_module"]
    saved = json.loads((EVIDENCE / "decision_site_inventory_OUTPUT.json").read_text())
    assert saved["summary"]["total"] == s["total"] == len(rows), "the saved inventory is stale — regenerate with --write"


@pytest.mark.parametrize("script,args", [("census_table.py", []), ("decision_site_inventory.py", []), ("reviewed_points.py", [])])
def test_every_evidence_script_runs_and_exits_zero(script, args):
    import subprocess, sys
    r = subprocess.run([sys.executable, str(EVIDENCE / script), *args], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]
