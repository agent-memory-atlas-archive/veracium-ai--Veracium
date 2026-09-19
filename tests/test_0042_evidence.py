"""specs/0042 (exercised guarantees, draft) — the census evidence, bound. Round 2 found the
previous evidence written to DEMONSTRATE clauses rather than attack them (a validator that
refused only the mutants its author imagined; an inventory over the kinds it could parse). These
checks are the reviewer's: the state table is PARSED from the spec so the code cannot drift from
it; every refusal is demonstrated on the input it refuses; the three-sets check is shown REFUSING
on the real tree's DISCOVERED/REVIEWED half, which is the honest state until the review file lands
with the last implementation tranche; the DECLARED/INSTALLED half reconciles per tranche.
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


def test_a5_an_undeclared_reporter_is_refused_even_when_measurement_is_off():
    """Round-3 A5 reproduction, kept as the control: enabled=False + an undeclared reporter."""
    ct = _load("census_table")
    snap = {"snapshot_id": "s", "process_started": "t0", "window_start": "t1", "window_end": "t2", "enabled": False}
    rows = ct.report_rows({"ghost": dict(consulted=3, fired=1, errors=0)}, {"a"}, enabled=False)
    p = ct.validate_report({"snapshot": snap, "rows": rows}, {"a"})
    assert any("UNDECLARED id 'ghost'" in x for x in p) and any(r["id"] == "ghost" and r["status"] == "DISABLED" for r in rows)


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


# ---- Part A-0-quater: the site BINDS the decision (round 4) ----------------------------------

def test_a0quater_scan_finds_the_binding_and_the_registry_checks_it_and_the_unloaded_site_is_named():
    inst = _load("installed_sites")
    fx = inst.scan(inst.FIXTURE); reg, loaded = inst.load_fixture()
    assert {s["id"] for s in fx} == inst.FIX_DISCOVERED
    assert all(set(s) == {"id", "module", "qualname", "line", "name", "consult", "fire", "bound"} for s in fx)
    assert all(s["bound"] and s["consult"] and s["fire"] for s in fx), "the fixture's three sites must all be BOUND (consult AND fire)"
    ref, oor = inst.check_registry_against_scan(fx, reg, loaded)
    assert ref == [] and len(oor) == 1 and "lifecycle.forget.scope" in oor[0] and "NAMED" in oor[0]
    assert inst.reconcile(inst.FIX_DISCOVERED, inst.FIX_REVIEWED, inst.FIX_DECLARED, inst.installed(fx), set()) == []


def test_a0quater_the_reviewers_round4_test_executing_both_decisions_moves_both_counters_and_reads_exercised():
    """Round 4: both fixture decisions executed, every counter stayed at zero, the report read UNREACHED.
    Now the decision is expressed THROUGH the site: after one declining decision per loaded site,
    consulted >= 1 AND fired >= 1, and the report reads EXERCISED — never UNREACHED for a site that ran."""
    inst = _load("installed_sites"); ct = _load("census_table")
    snaps = inst.execute_decisions()
    executed = {"gate.answer.unverified-only", "ingest.quarantine.third-party"}
    assert inst.assert_counters_moved(snaps, executed) == []
    counters = inst.counters_after(snaps)
    assert all(counters[i]["consulted"] >= 1 and counters[i]["fired"] >= 1 for i in executed)
    rows = {r["id"]: r["status"] for r in ct.report_rows(counters, inst.FIX_DECLARED, enabled=True)}
    assert rows == {"gate.answer.unverified-only": "EXERCISED", "ingest.quarantine.third-party": "EXERCISED", "lifecycle.forget.scope": "UNREACHED"}
    # the assertion is over DELTAS (round 5): an already-positive counter that does not move around THIS
    # decision is refused, exactly like a zero one
    zero = {"consulted": 0, "fired": 0, "errors": 0}; five = {"consulted": 5, "fired": 5, "errors": 0}
    frozen = {i: (zero, zero) for i in executed}
    p = inst.assert_counters_moved(frozen, executed)
    assert len(p) == 4 and all("consult()" in x or "fire()" in x for x in p)
    already_positive = {i: (five, five) for i in executed}
    p = inst.assert_counters_moved(already_positive, executed)
    assert len(p) == 4 and all("moved by 0" in x for x in p), p
    assert inst.level_assertion(already_positive, executed) == []          # the superseded LEVEL check passes here: it is the mutant
    half = {**frozen, "gate.answer.unverified-only": (five, {"consulted": 6, "fired": 5, "errors": 0})}
    assert any("declined once but fired moved by 0" in x for x in inst.assert_counters_moved(half, executed))
    double = {**frozen, "gate.answer.unverified-only": (zero, {"consulted": 2, "fired": 2, "errors": 0})}   # v8.1: exactly one
    assert sum("double-counted" in x for x in inst.assert_counters_moved(double, executed)) == 2
    pp = inst.preloaded_positive_control()
    assert pp["delta_refuses"] and pp["level_passes"], pp


def test_a0quater_strip_the_binding_keep_the_declaration_refuses_and_consult_without_fire_refuses():
    """A-0-quater's first control under its honest name: v6's "delete a counter" deleted the declare_site
    LINE on a fixture with no counters. Now: keep declare_site + the raise, strip consult/fire -> REFUSE."""
    inst = _load("installed_sites")
    c1 = inst.strip_binding_control()
    assert any("DECLARED but NOT INSTALLED" in x and "gate.answer.unverified-only" in x for x in c1)
    c2 = inst.consult_without_fire_control()                       # the next mutant: consult kept, fire stripped
    assert any("DECLARED but NOT INSTALLED" in x and "gate.answer.unverified-only" in x for x in c2)
    c3 = inst.delete_declaration_control()                         # the structural case, kept and named for what it is
    assert any("DECLARED but NOT INSTALLED" in x for x in c3)


def test_a0quater_round5_the_binding_is_function_local_and_scope_aware():
    """Round 5's reproduction: consult() in one function and fire() in another read as bound under a
    module-wide scan by variable name. Same-function-body, nested functions are their own scope, and a
    shadowed name is not the site — every one REFUSES; the diagnostic fields still show the uses."""
    inst = _load("installed_sites")
    assert any("gate.answer.unverified-only" in x for x in inst.split_function_control())
    both = inst.nested_and_shadowed_control(); assert len(both) == 2 and all("gate.answer.unverified-only" in x for x in both)
    import shutil, tempfile
    with tempfile.TemporaryDirectory() as d:
        copy = pathlib.Path(d) / "fixture_sites"; shutil.copytree(inst.FIXTURE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        (copy / "gate_like.py").write_text('from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
                                           'def a(x):\n    with SITE_ANSWER.consult():\n        pass\n\n\ndef b(x):\n    raise SITE_ANSWER.fire(ValueError("x"))\n')
        g = [s for s in inst.scan(copy) if s["id"] == "gate.answer.unverified-only"][0]
        assert g["consult"] and g["fire"] and not g["bound"], g          # both used somewhere; bound nowhere
        assert "gate.answer.unverified-only" not in inst.installed(inst.scan(copy))


def test_a0quater_registered_but_unbound_is_refused_by_the_registry_check_as_registered_not_installed(tmp_path):
    """The exact round-4 state: declared, registered at import, and no counter bound — the registry check
    names it 'registered, not installed' rather than passing."""
    import shutil
    inst = _load("installed_sites")
    copy = tmp_path / "fixture_sites"; shutil.copytree(inst.FIXTURE, copy, ignore=shutil.ignore_patterns("__pycache__"))
    g = copy / "gate_like.py"
    g.write_text(g.read_text().replace("    with SITE_ANSWER.consult():\n        if not grounded and unverified:\n            raise SITE_ANSWER.fire(ValueError(\"refuse: unverified-only support\"))\n",
                                       "    if not grounded and unverified:\n        raise ValueError(\"refuse: unverified-only support\")\n"))
    fx = inst.scan(copy)
    unbound = [s for s in fx if s["id"] == "gate.answer.unverified-only"][0]
    assert not unbound["bound"] and not unbound["consult"] and not unbound["fire"]
    reg = {s["id"]: {"module": s["module"], "line": s["line"]} for s in fx}               # every site registered, as at import
    ref, _ = inst.check_registry_against_scan(fx, reg, {"gate_like.py", "ingest_like.py", "__init__.py"})
    assert any("registered, not installed" in x and "gate.answer.unverified-only" in x for x in ref)
    assert "gate.answer.unverified-only" not in inst.installed(fx)


def test_a0quater_full_binding_and_no_traffic_reads_unreached():
    inst = _load("installed_sites"); ct = _load("census_table")
    assert inst.installed(inst.scan(inst.FIXTURE)) == inst.FIX_DECLARED
    rows = ct.report_rows({}, inst.FIX_DECLARED, enabled=True)
    assert {r["status"] for r in rows} == {"UNREACHED"}


def test_a0quater_registry_refuses_a_registration_the_scan_does_not_show_and_a_scanned_site_that_did_not_register():
    inst = _load("installed_sites")
    fx = inst.scan(inst.FIXTURE); reg, loaded = inst.load_fixture()
    ref, _ = inst.check_registry_against_scan(fx, {**reg, "phantom.site": {"module": "x.py", "line": 1}}, loaded)
    assert any("registered site 'phantom.site' is not in the scan" in x for x in ref)
    silent = {k: v for k, v in reg.items() if k != "gate.answer.unverified-only"}
    ref, _ = inst.check_registry_against_scan(fx, silent, loaded)
    assert any("did not register" in x and "gate.answer.unverified-only" in x for x in ref)


def test_a0quater_on_the_real_tree_installed_equals_what_the_package_declares():
    """The spec is ACCEPTED (v9.2) and the implementation is landing in tranches (2026-09-19):
    INSTALLED on the real tree is exactly the set of ids the package declares at import — every
    declared site is bound (consult AND fire in one body) and no bound site is undeclared. The
    DISCOVERED/REVIEWED half of the reconciliation still bites until the review file lands with
    the last tranche (`test_a0bis_…`)."""
    inst = _load("installed_sites")
    scanned = inst.scan(inst.SRC)
    declared = {r["id"] for r in scanned}                   # DECLARED, read from the SOURCE (order-free:
    real = inst.installed(scanned)                          # the census tests clear the live registry)
    assert real == declared, (sorted(declared - real), sorted(real - declared))
    assert len(real) >= 28                                  # tranche 1 (module) + tranche 2 (28 sites)
    from veracium import census
    live = set(census.registry())                           # the live registry, when a fixture has not
    assert not live or live <= declared, sorted(live - declared)   # cleared it, names only declared ids
    probs = inst.reconcile(set(), {}, declared, real, set())
    assert not any("NOT INSTALLED" in x or "not DECLARED" in x for x in probs), probs
    assert any("DECLARED but NOT INSTALLED" in x for x in inst.reconcile(set(), {}, declared | {"gate.answer.unverified-only"}, real, set()))


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


@pytest.mark.parametrize("script,args", [("census_table.py", []), ("decision_site_inventory.py", []), ("reviewed_points.py", []), ("installed_sites.py", [])])
def test_every_evidence_script_runs_and_exits_zero(script, args):
    import subprocess, sys
    r = subprocess.run([sys.executable, str(EVIDENCE / script), *args], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]
