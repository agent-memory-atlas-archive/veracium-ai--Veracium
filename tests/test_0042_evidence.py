"""specs/0042 (exercised guarantees, draft) — the census evidence, bound. Round 2 found the
previous evidence written to DEMONSTRATE clauses rather than attack them (a validator that
refused only the mutants its author imagined; an inventory over the kinds it could parse). These
checks are the reviewer's: the state table is PARSED from the spec so the code cannot drift from
it; every refusal is demonstrated on the input it refuses; the four-set reconciliation over the real
tree is tests/test_0042_reconciliation.py's (tranche 6, 2026-09-19), and the refusals stay LIVE here
against emptied inputs.
"""
import importlib
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
    # round 7, F1: a two-argument call is STRUCTURALLY clean and INCOMPLETELY validated, and says so in the
    # channel the caller already reads — the only refusal is the incompleteness marker, never []
    assert [x for x in ct.validate_report(good, decl) if not x.startswith("VALIDATION INCOMPLETE")] == []
    assert sum(x.startswith("VALIDATION INCOMPLETE") for x in ct.validate_report(good, decl)) == 1
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


def test_a0bis_on_the_real_tree_every_discovered_candidate_has_a_decision():
    """Flipped 2026-09-19 (tranche 6): the review file exists, generated from the authored review —
    the third source no longer bites on the real tree, and the full four-set reconciliation is
    tests/test_0042_reconciliation.py's. This keeps the DISCOVERED/REVIEWED half's refusal LIVE:
    with the review file emptied it must still bite."""
    rp = _load("reviewed_points")
    real = rp.load_discovered()
    reviewed = rp.load_reviewed(rp.REVIEWED_PATH)
    undecided = [x for x in rp.check_three_sets(real, reviewed, set(), set()) if "NO DECISION" in x]
    assert undecided == [], undecided[:3]
    assert len(reviewed) == len(real)
    bites = [x for x in rp.check_three_sets(real, {}, set(), set()) if "NO DECISION" in x]
    assert len(bites) == len(real), "the refusal must still bite on an empty review"


# ---- Part A-0-quater: the site BINDS the decision (round 4) ----------------------------------

def test_a0quater_scan_finds_the_binding_and_the_registry_checks_it_and_the_unloaded_site_is_named():
    inst = _load("installed_sites")
    fx = inst.scan(inst.FIXTURE); reg, loaded = inst.load_fixture()
    assert {s["id"] for s in fx} == inst.FIX_DISCOVERED
    assert all(set(s) == {"id", "module", "qualname", "line", "name", "consult", "fire", "bound", "sha256"} for s in fx)
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


def test_r7_f2_the_reviewers_two_rebinding_forms_no_longer_read_as_bound():
    """F2, THE REVIEWER'S OWN CASE, driven through `installed_sites.scan()` — the regression the round-7
    verdict asked for, and the only one for F2 that can RUN at the round-7 pin.

    The reviewer reproduced two forms rebinding a declared site's name to another object inside the function
    that uses it: an assignment expression and a `match` capture. Both read `bound=True`, with no
    reconciliation refusal, while the declared site's counters never moved. An ordinary assignment correctly
    read `bound=False` — so the enumeration of binding forms had reached `ast.Assign` and not these two.

    Measured at pin 12d06a5ba58d, both forms: `bound=True`. Here: `bound=False`, because the name resolves
    through `symtable` and both forms make it a function LOCAL, which is a shadow and not the site. Note this
    is resolution and not refusal: the reviewer offered either ("resolve these forms using Python's scope
    information, or explicitly refuse unsupported binding syntax") and a form the language can answer is
    answered. Refusal is reserved for what cannot be resolved — a MODULE-level rebinding, which is
    `test_0042_scope_resolution.py`'s 44-row matrix.

    The scope resolver's own tests cannot serve as this regression: the module under test does not exist at
    the round-7 pin, so they collection-error there rather than demonstrating the defect."""
    import shutil, tempfile
    inst = _load("installed_sites")
    forms = {
        "an assignment expression": (
            'from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
            'def a(x):\n'
            '    if (SITE_ANSWER := x):\n'
            '        with SITE_ANSWER.consult():\n'
            '            return SITE_ANSWER.fire(x)\n'
            '    return None\n'),
        "a match capture": (
            'from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
            'def a(x):\n'
            '    match x:\n'
            '        case SITE_ANSWER:\n'
            '            with SITE_ANSWER.consult():\n'
            '                return SITE_ANSWER.fire(x)\n'
            '    return None\n'),
    }
    # the CONTROL the reviewer also ran: an ordinary assignment was already correct, and must stay correct
    forms["an ordinary assignment (the reviewer's control)"] = (
        'from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
        'def a(x):\n'
        '    SITE_ANSWER = x\n'
        '    with SITE_ANSWER.consult():\n'
        '        return SITE_ANSWER.fire(x)\n')
    # and the POSITIVE control: an unshadowed use must still read bound, or "False everywhere" would pass this
    forms["no rebinding at all (must read BOUND)"] = (
        'from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
        'def a(x):\n'
        '    with SITE_ANSWER.consult():\n'
        '        return SITE_ANSWER.fire(x)\n')
    for label, body in forms.items():
        with tempfile.TemporaryDirectory() as d:
            copy = pathlib.Path(d) / "fixture_sites"
            shutil.copytree(inst.FIXTURE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / "gate_like.py").write_text(body)
            rows = [r for r in inst.scan(copy) if r["id"] == "gate.answer.unverified-only"]
            assert len(rows) == 1, (label, rows)
            expected = label.startswith("no rebinding")
            assert rows[0]["bound"] is expected, (
                f"{label}: scan reports bound={rows[0]['bound']}, expected {expected} — a name rebound in the "
                f"function that uses it is a SHADOW, and an unshadowed one must still read bound")


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


# ---- tranche 2 (2026-09-19): instrumenting a site never removes it from DISCOVERED --------------
# Research's read of INV-2d: if wrapping a decision in `fire()` dropped its statement from the
# inventory, the set that requires a decision would shrink exactly as sites are instrumented and
# the third source would stop being one. The first form of tranche 2 did that to 14 of 28 sites;
# discovery now looks THROUGH the wrapper, and this is the assertion that keeps it so.

def _fire_wrapped_statements():
    """Every `return`/`raise` in src whose value is `NAME.fire(...)`: (module, line, unwrapped kind)."""
    import ast
    inv = _load("decision_site_inventory")
    out = []
    for path in sorted((ROOT / "src/veracium").rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            v = node.value if isinstance(node, ast.Return) else node.exc if isinstance(node, ast.Raise) else None
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "fire" \
                    and isinstance(v.func.value, ast.Name):
                out.append((str(path.relative_to(ROOT / "src/veracium")), node.lineno, isinstance(node, ast.Raise)))
    return out


def test_instrumenting_a_site_never_removes_its_statement_from_discovered():
    inv = _load("decision_site_inventory")
    rows = {(r["module"], r["line"]): r["kind"] for r in inv.inventory()}
    wrapped = _fire_wrapped_statements()
    assert len(wrapped) >= 28, "tranche 2 wrapped at least 28 statements"
    missing = [(m, ln) for m, ln, _ in wrapped if (m, ln) not in rows
               and not _returns_true_through_fire(m, ln)]
    assert missing == [], f"fire-wrapped statements discovery no longer lists: {missing}"
    # a wrapped raise is a RAISE; a wrapped `None`/`False`/Boolean/filter is its own kind
    for m, ln, is_raise in wrapped:
        if (m, ln) in rows:
            assert (rows[(m, ln)] == "RAISE") == is_raise, (m, ln, rows[(m, ln)])


def _returns_true_through_fire(module, line):
    """A fire-wrapped statement whose UNWRAPPED value is not a discovery kind is not a removal:
    `return NAME.fire(True, …)` (the non-declining branch of a predicate split across statements,
    grounding.ungrounded's final `return`) and `return NAME.fire(<bare Name>, …)` where the Name
    is a module constant, not a filter- or Boolean-bound local (the store's NON_QUIESCENT
    sentinel, tranche 5). Everything else must be listed."""
    import ast
    src = (ROOT / "src/veracium" / module).read_text().split("\n")[line - 1]
    try:
        v = ast.parse(src.strip()).body[0].value
    except SyntaxError:
        return False
    if not (isinstance(v, ast.Call) and v.args):
        return False
    a = v.args[0]
    if isinstance(a, ast.Constant) and a.value is True:
        return True
    return isinstance(a, ast.Name) and a.id.isupper()          # a module-level sentinel constant


# ---- round 6 (2026-09-20) ----------------------------------------------------------------------------------------

def test_a0quater_round6_a_site_name_resolves_through_enclosing_function_scopes_and_class_bodies_do_not_shadow(tmp_path):
    """R6-4 (cell D): the round-5 scan checked local shadowing and stopped one scope short — a nested function
    whose SITE name is an ENCLOSING function's parameter read the module-level site as bound. Names now resolve
    through the lexical scope: a binding in any enclosing FUNCTION shadows for everything nested; a CLASS body
    is not a closure scope (Python's rule), so a class attribute of the same name shadows nothing for the
    methods below it. ROUND 7 (F2): the forms are no longer enumerated by hand — the scan asks CPython's own
    scope analysis, so `nonlocal` RESOLVES as a shadow and only a `global` REBINDING is refused."""
    import textwrap
    inst = _load("installed_sites")
    def scan_of(src):
        d = tmp_path / f"m{abs(hash(src))}"; d.mkdir(); (d / "mod.py").write_text(textwrap.dedent(src))
        return {r["id"]: r["bound"] for r in inst.scan(d)}
    closure = '''
        from veracium.census import declare_site
        SITE = declare_site("t.enclosing-parameter")
        def outer(SITE):
            def inner(x):
                with SITE.consult():
                    if x: raise SITE.fire(ValueError("no"))
                return x
            return inner
    '''
    assert scan_of(closure) == {"t.enclosing-parameter": False}           # the reviewer's case: NOT bound
    assigned = closure.replace("def outer(SITE):", "def outer():\n            SITE = object()")
    assert scan_of(assigned) == {"t.enclosing-parameter": False}          # an enclosing assignment shadows too
    class_body = '''
        from veracium.census import declare_site
        SITE = declare_site("t.class-body")
        class K:
            SITE = None
            def m(self, x):
                with SITE.consult():
                    if x: raise SITE.fire(ValueError("no"))
                return x
    '''
    assert scan_of(class_body) == {"t.class-body": True}                  # the control: a class body does not shadow
    plain = closure.replace("def outer(SITE):", "def outer(other):")
    assert scan_of(plain) == {"t.enclosing-parameter": True}              # the control: the same shape, unshadowed, IS bound
    # ROUND 7 (F2) narrows what is refused, because CPython's own scope analysis now answers what the scan used to
    # guess at. `nonlocal SITE` is no longer a refusal: it RESOLVES — the name is the enclosing function's binding,
    # so it is a shadow and the site is simply not bound there. What stays refused is the one form no static
    # reading can account for: `global SITE` WITH an assignment, which replaces the module binding for every reader.
    nonlocal_shadow = closure.replace("def inner(x):\n", "def inner(x):\n                nonlocal SITE\n").replace("def outer(SITE):", "def outer():\n            SITE = 1")
    assert scan_of(nonlocal_shadow) == {"t.enclosing-parameter": False}
    with pytest.raises(inst.UnresolvableScope, match="replaces the declared site"):
        scan_of(closure.replace("def outer(SITE):", "def outer():\n            global SITE\n            SITE = 1"))


def test_r7_f1_the_reviewers_case_a_two_argument_validation_no_longer_reads_clean(monkeypatch):
    """Round 7, F1, the reviewer's own reproduction: delete the registration of an ALREADY-LOADED declared site and
    the row reads UNREACHED with zero counts — a report that looks fine. Before this round the ordinary two-argument
    `validate_report(report, declaration)` returned NO refusals, so a caller who could not observe an interpreter
    (the reviewer, validating the shipped report in a throwaway) received an apparently validated report. The
    reconciliation stays OPTIONAL — that caller cannot supply a module map — but its ABSENCE is now a refusal in the
    list every caller already reads, so `[]` means "validated, completely" and nothing else."""
    from veracium import census
    import veracium.gate  # noqa: F401 — the victim's module must be loaded for the case to be the reviewer's
    inst, decl_m, ct = _load("installed_sites"), _load("declaration"), _load("census_table")
    victim = "gate.scoped-assertable.invisible"
    declared = set(decl_m.DECLARED_IDS); assert victim in declared
    monkeypatch.setattr(census, "_ENABLED", True)
    saved = census._REGISTRY.pop(victim)
    try:
        rep = census.census(declared)
        row = next(r for r in rep["rows"] if r["id"] == victim)
        assert row["status"] == "UNREACHED" and row["consulted"] == row["fired"] == row["errors"] == 0
        two_arg = ct.validate_report(rep, declared)
        assert any(x.startswith("VALIDATION INCOMPLETE") for x in two_arg), two_arg
        site_modules = {s["id"]: s["module"] for s in inst.scan(pathlib.Path(__file__).resolve().parents[1] / "src" / "veracium")}
        four_arg = ct.validate_report(rep, declared, site_modules, ct.loaded_product_modules())
        assert any(victim in x and "missing registration" in x for x in four_arg), four_arg
        assert not any(x.startswith("VALIDATION INCOMPLETE") for x in four_arg)
    finally:
        census._REGISTRY[victim] = saved
    # The control, and it is the contract working rather than a nuisance: with the registration restored there is
    # no REFUSAL left, but this process imported one product module, so the complete validation names the sites it
    # cannot speak for instead of returning []. (Written as `== []` first and red at 35 entries — the second control
    # with a wrong expected outcome in this round; both were mine, and both were corrected rather than concluded
    # from. `test_a0quater_round6_the_live_registry_reconciles…` is the case where [] IS the right expectation,
    # because it imports every product module first.)
    rep = census.census(declared)
    site_modules = {s["id"]: s["module"] for s in inst.scan(pathlib.Path(__file__).resolve().parents[1] / "src" / "veracium")}
    # with the registration restored there is no REFUSAL left, and nothing has to be filtered out of the refusal
    # channel to see that (research's stage-1 BLOCKING 1: a channel whose consumers must filter it before use is
    # carrying two kinds). What this partial process cannot speak for is `insufficiency`'s answer, separately.
    loaded_now = ct.loaded_product_modules()
    complete = ct.validate_report(rep, declared, site_modules, loaded_now)
    assert complete == [], complete
    # the claim is about REACH, so the assertion is about reach: the victim's module is loaded, so it is never
    # named OUT OF REACH. (The broader form — the victim absent from insufficiency entirely — was wrong: an
    # earlier file's in-process replay can leave a site with errors, which is an UNMEASURED row and a true
    # statement about this process. Asserting more than the claim is how a test becomes order-dependent.)
    assert not any(victim in x for x in ct.insufficiency(rep, declared, site_modules, loaded_now)
                   if x.startswith("OUT OF REACH"))
    assert [x for x in ct.validate_report(rep, declared) if not x.startswith("VALIDATION INCOMPLETE")] == []


def test_a0quater_round6_the_live_registry_reconciles_against_the_scan_and_nothing_is_out_of_reach():
    """R6-3 on the real tree (cell E, D feeding it): with every product module imported, the census's own
    snapshot of what registered and what was loaded, validated against the scan's id -> module map, refuses
    nothing and leaves NO declared id out of reach — the claim 'every declared site' is over the whole
    declaration, not over the modules a run happened to import."""
    import importlib
    import veracium
    # every .py under the package, by FILE — `pkgutil.walk_packages` does not descend into `store/`,
    # a namespace package (no __init__.py), and the round-6 draft of this test imported 51 modules and
    # reported seven store ids out of reach while calling the tree reconciled (found repairing it)
    root = pathlib.Path(veracium.__file__).resolve().parent
    failed = []
    for f in sorted(root.rglob("*.py")):
        rel = f.relative_to(root).with_suffix("")
        parts = [p for p in rel.parts if p != "__init__"]
        try:
            importlib.import_module(".".join(["veracium", *parts]) if parts else "veracium")
        except Exception as exc:      # an unimportable product module would leave its ids out of reach: say which
            failed.append((str(rel), type(exc).__name__))
    assert failed == []
    from veracium import census
    inst, decl, ct = _load("installed_sites"), _load("declaration"), _load("census_table")
    loaded = ct.loaded_product_modules()          # the evidence layer's observation (specs/0031 keeps sys.modules out of src)
    assert len(loaded) == sum(1 for _ in root.rglob("*.py"))
    scanned = inst.scan(pathlib.Path(__file__).resolve().parents[1] / "src" / "veracium")
    site_modules = {s["id"]: s["module"] for s in scanned}
    declared = set(decl.DECLARED_IDS)
    rep = census.census(declared)
    # THE PAIR IS THE COMPLETE CLAIM (round 7, research's stage-1 read): `validate_report` answers "is anything
    # WRONG" and `insufficiency` answers "is there anything this report cannot SPEAK FOR". An evidence run asserts
    # both empty; either alone leaves the other question unasked, which is how an out-of-reach set went unnoticed.
    # ROUND 13 (row 321): and BOTH rest on the scan's site map, so the scan must describe the program this process
    # RAN — otherwise the pair is complete about a different program. Asserted before either is read.
    from veracium import census
    assert inst.scan_is_the_program_that_ran(root, scanned, census._REGISTRY) == []
    assert ct.validate_report(rep, declared, site_modules, loaded) == []
    assert ct.insufficiency(rep, declared, site_modules, loaded) == []
    assert ct.out_of_reach(declared, site_modules, loaded) == []
    assert set(rep["snapshot"]["registered"]) >= declared
    # the mutant: forget one registration of a loaded module → refused by name, not a valid zero
    victim = sorted(declared)[0]; saved = census._REGISTRY.pop(victim)
    try:
        probs = ct.validate_report(census.census(declared), declared, site_modules, loaded)
    finally:
        census._REGISTRY[victim] = saved
    assert any(victim in p and "missing registration" in p for p in probs), probs


# ROUND 13 — THE SCAN IS BOUND TO THE PROGRAM THAT RAN (the ledger's row 321; taken into round 13 on the owner's word
# as a SILENT limit the round-12 package never disclosed). `scan()` read each module from disk and nothing bound those
# bytes to what the process executed, so an edit the process never saw could flip `bound` with nothing to refuse.
_R13_STUB = ("REGISTRY = {}\n\n\nclass _S:\n    def consult(self):\n        return self\n    def __enter__(self):\n"
             "        return self\n    def __exit__(self, *a):\n        return False\n    def fire(self, v):\n        return v\n\n\n"
             "def declare_site(i):\n    REGISTRY[i] = _S()\n    return REGISTRY[i]\n")
_R13_BIND_SRC = ("from .census_stub import declare_site\nS = declare_site('r13.bind')\nT = object()\n\n\n"
                 "def decide(x):\n    with S.consult():\n        return S.fire(x)\n\n\ndef extra():\n    return 1\n")


def _r13_bind_pkg(tmp_path, tag, text=_R13_BIND_SRC):
    import sys, uuid
    name = f"r13bind_{tag}_{uuid.uuid4().hex[:8]}"
    pkg = tmp_path / name; pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "census_stub.py").write_text(_R13_STUB)
    (pkg / "m.py").write_text(text)
    sys.path.insert(0, str(tmp_path))
    try:
        mod = importlib.import_module(f"{name}.m")
        stub = importlib.import_module(f"{name}.census_stub")
    finally:
        sys.path.remove(str(tmp_path))
    return pkg, mod, stub.REGISTRY


def test_r13_the_scan_describes_the_program_that_ran_and_refuses_otherwise(tmp_path):
    """Each way the scan can describe a program other than the one that ran, and the clean control.
      EDITED BODY after import, then scanned — refused by comparing code objects (NOT `__loader__.get_source`, which
        re-reads the file and shows the edit);
      the TABLE swapped — research's case: `S = declare_site(..); T = object()` ran, `S = object(); T = declare_site(..)`
        was scanned, every function body identical, the scan saying bound where it was not — refused by IDENTITY;
      SCANNED, THEN EDITED — refused, the file is no longer the bytes the scan read;
      a function REMOVED from the running module — refused by the count, so filtering cannot leave nothing compared;
      RAN FROM ANOTHER FILE — refused, found by module name rather than skipped as not loaded."""
    inst = _load("installed_sites")
    clean, _, reg = _r13_bind_pkg(tmp_path, "clean")
    assert inst.scan_is_the_program_that_ran(clean, inst.scan(clean), reg) == []

    body, _, reg = _r13_bind_pkg(tmp_path, "body")
    (body / "m.py").write_text(_R13_BIND_SRC.replace("return S.fire(x)", "return S.fire(not x)"))
    got = inst.scan_is_the_program_that_ran(body, inst.scan(body), reg)
    assert any("decide" in p and "as it RAN differs" in p for p in got), got

    table, _, reg = _r13_bind_pkg(tmp_path, "table")
    (table / "m.py").write_text(_R13_BIND_SRC.replace("S = declare_site('r13.bind')\nT = object()",
                                                      "S = object()\nT = declare_site('r13.bind')")
                                                .replace("S.consult()", "T.consult()").replace("S.fire(x)", "T.fire(x)"))
    got = inst.scan_is_the_program_that_ran(table, inst.scan(table), reg)
    assert any("is NOT the site the registry holds" in p for p in got), got

    late, _, reg = _r13_bind_pkg(tmp_path, "late")
    scanned = inst.scan(late)
    (late / "m.py").write_text(_R13_BIND_SRC + "\n\ndef more():\n    return 2\n")
    assert any("changed after the scan" in p for p in inst.scan_is_the_program_that_ran(late, scanned, reg))

    gone, mod, reg = _r13_bind_pkg(tmp_path, "gone")
    del mod.extra
    got = inst.scan_is_the_program_that_ran(gone, inst.scan(gone), reg)
    assert any("does not cover the module" in p for p in got), got

    moved, mod, reg = _r13_bind_pkg(tmp_path, "moved")
    other = tmp_path / "elsewhere_m.py"; other.write_text(_R13_BIND_SRC)
    mod.__file__ = str(other)
    got = inst.scan_is_the_program_that_ran(moved, inst.scan(moved), reg)
    assert any("was loaded from" in p for p in got), got


def test_r13_the_real_tree_s_scan_is_the_program_this_process_ran():
    """The acceptance half on the product: every site-declaring module imported, scanned, and every function it
    defines compared with the code compiled from the scanned bytes. Measured at round 13: 509 functions in 28
    modules, 0 refusals, on 3.10–3.13 (dataclass-generated methods excluded — `exec`'d text is not the source)."""
    inst = _load("installed_sites")
    root = ROOT / "src" / "veracium"
    scanned = inst.scan(root)
    import veracium  # noqa: F401
    for rel in sorted({r["module"] for r in scanned}):
        parts = rel[:-3].split("/")
        importlib.import_module(".".join(["veracium", *(parts[:-1] if parts[-1] == "__init__" else parts)]))
    from veracium import census
    assert inst.scan_is_the_program_that_ran(root, scanned, census._REGISTRY) == []
