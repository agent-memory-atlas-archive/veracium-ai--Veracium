"""specs/0042 (accepted at the design level, external round 5) — the census module's own contract:
the state table carried verbatim and equal to the spec's parsed table; precedence; opt-in default OFF
with DISABLED omitting counts; UNDECLARED emitted AND refused; UNMEASURED from a counter that raised;
fire() returns the decision unchanged (INV-7); the trace carries exactly (seq, site_id, decision)
(Part A-2); duplicate ids refuse at declaration; per-id increments are atomic under threads."""
from __future__ import annotations

import importlib.util
import pathlib
import threading

import pytest

from veracium import census

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _evidence(name):
    p = ROOT / "specs" / "evidence" / "0042" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


@pytest.fixture(autouse=True)
def _census_off():
    """An empty registry for each test, the PRODUCTION registrations put back after it: a bare
    `_clear_registry()` left every later test in the process with an empty registry, and the live-registry
    reconciliation (R6-3) then read 127 production ids as 'loaded and never registered' under one shuffle
    order and reconciled under another (round 7, found repairing it). The affordance is the harness's own
    (the registry dict the evidence tests already read), not a new product surface."""
    census.enable(False); census.trace(False); census.trace_reset()
    saved = dict(census._REGISTRY); census._clear_registry()
    try:
        yield
    finally:
        census.enable(False); census.trace(False); census.trace_reset()
        census._clear_registry(); census._REGISTRY.update(saved)


def _row(report, cid):
    return next(r for r in report["rows"] if r["id"] == cid)


def test_the_state_table_equals_the_specs_parsed_table_row_for_row():
    ct = _evidence("census_table")
    parsed = [(r["status"], r["condition"]) for r in ct.STATE_TABLE]
    assert list(census.STATE_TABLE) == parsed, "the product's table and the spec's table diverged (Part A-1 is the single authority)"
    assert census.STATUSES == ct.STATUSES
    for enabled in (False, True):
        for declared in (False, True):
            for errors in (0, 1):
                for consulted, fired in ((0, 0), (1, 0), (3, 2)):
                    t = {"enabled": enabled, "declared": declared, "errors": errors, "consulted": consulted, "fired": fired}
                    assert census.status_of(t) == ct.status_of(t)


def test_default_off_every_site_is_a_no_op_and_the_report_reads_disabled_without_counts():
    S = census.declare_site("t.off")
    assert not census.enabled()
    with S.consult():
        assert S.fire(False) is False
    assert S.counters() == {"consulted": 0, "fired": 0, "errors": 0}
    r = _row(census.census({"t.off"}), "t.off")
    assert r == {"id": "t.off", "status": "DISABLED"} and "consulted" not in r


def test_on_consult_then_fire_reads_exercised_consult_alone_unexercised_and_never_unreached():
    S = census.declare_site("t.on"); census.enable(True)
    with S.consult():
        pass
    assert _row(census.census({"t.on"}), "t.on")["status"] == "UNEXERCISED"
    with S.consult():
        try:
            raise S.fire(ValueError("refuse"))
        except ValueError:
            pass
    r = _row(census.census({"t.on"}), "t.on")
    assert r == {"id": "t.on", "status": "EXERCISED", "consulted": 2, "fired": 1, "errors": 0}
    assert _row(census.census({"t.on", "t.never"}), "t.never") == {"id": "t.never", "status": "UNREACHED", "consulted": 0, "fired": 0, "errors": 0}


def test_fire_returns_the_decision_unchanged_on_and_off():
    S = census.declare_site("t.identity"); exc = ValueError("x")
    for on in (False, True):
        census.enable(on)
        assert S.fire(exc) is exc and S.fire(None) is None and S.fire(False) is False


def test_an_undeclared_reporter_is_emitted_and_the_evidence_gate_refuses_measurement_on_or_off():
    ct = _evidence("census_table"); S = census.declare_site("t.undeclared"); census.enable(True)
    with S.consult():
        S.fire(None)
    rep = census.census(set())
    assert _row(rep, "t.undeclared")["status"] == "UNDECLARED"
    assert any("UNDECLARED" in p for p in ct.validate_report(rep, set()))
    census.enable(False)
    rep = census.census(set())
    assert _row(rep, "t.undeclared")["status"] == "DISABLED" and any("UNDECLARED" in p for p in ct.validate_report(rep, set()))


def test_a_counter_that_raises_reads_unmeasured_and_the_decision_still_proceeds(monkeypatch):
    S = census.declare_site("t.broken"); census.enable(True)
    def boom(self, field):
        raise RuntimeError("the counter broke")
    monkeypatch.setattr(census.Site, "_bump", boom)
    with S.consult():
        try:
            raise S.fire(ValueError("refuse"))
        except ValueError:
            pass                                                  # the decision proceeded
    r = _row(census.census({"t.broken"}), "t.broken")
    assert r["status"] == "UNMEASURED" and r["errors"] >= 1
    assert census.census({"t.broken"})["snapshot"]["unmeasured"] == 1


def test_the_trace_carries_exactly_seq_site_and_decision_and_only_when_tracing():
    S = census.declare_site("t.trace"); census.enable(True)
    with S.consult():
        S.fire(False, label="withhold")
    assert census.trace_snapshot() == []
    census.trace(True)
    with S.consult():
        S.fire(False, label="withhold")
        try:
            raise S.fire(PermissionError("no"))
        except PermissionError:
            pass
    t = census.trace_snapshot()
    assert t == [(1, "t.trace", "withhold"), (2, "t.trace", "PermissionError")]
    assert all(len(x) == 3 for x in t)


def test_a_duplicate_site_id_refuses_at_declaration():
    census.declare_site("t.dup")
    with pytest.raises(census.CensusError, match="duplicate"):
        census.declare_site("t.dup")                                     # any second declaration refuses
    with pytest.raises(census.CensusError):
        census.declare_site("bad id")


def test_increments_are_atomic_per_id_under_threads():
    S = census.declare_site("t.atomic"); census.enable(True)
    def work():
        for _ in range(2000):
            with S.consult():
                S.fire(None)
    ts = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert S.counters() == {"consulted": 16000, "fired": 16000, "errors": 0}


def test_the_report_carries_no_content_only_ids_and_integers():
    S = census.declare_site("t.content"); census.enable(True)
    with S.consult():
        S.fire(ValueError("the user's secret"))
    for r in census.census({"t.content"})["rows"]:
        assert set(r) <= {"id", "status", "consulted", "fired", "errors"}
        assert all(isinstance(r[k], int) for k in r if k not in ("id", "status"))


def test_memory_config_census_enabled_is_the_opt_in_switch_default_off(tmp_path):
    from veracium import Memory, MemoryConfig
    m = Memory(llm=lambda *a, **k: "", config=MemoryConfig(db_path=str(tmp_path / "a.db"))); m.close()
    assert not census.enabled(), "default OFF (Part A-2, the owner's ruling)"
    m = Memory(llm=lambda *a, **k: "", config=MemoryConfig(db_path=str(tmp_path / "b.db"), census_enabled=True)); m.close()
    assert census.enabled()


# ---- round 6 (2026-09-20), cell A: every failure OF THE MEASUREMENT is contained and counted -------------------

def test_r6_1_a_failed_trace_recorder_is_contained_counted_and_the_decision_is_returned_as_made(monkeypatch):
    """R6-1(i): with tracing on, a recorder that raises turned a returned False into a RuntimeError and left
    `errors` at 0. Now: the decision is returned exactly as made, `errors` moves, the failure KIND is in the
    snapshot (type name only), and the row reads UNMEASURED."""
    S = census.declare_site("t.recorder", declines=False); census.enable(True); census.trace(True)
    def boom(site_id, label):
        raise RuntimeError("recorder failed")
    monkeypatch.setattr(census, "_record_trace", boom)
    with S.consult():
        out = S.fire(False, "withhold")
    assert out is False                                      # the decision made, returned as made — INV-7
    c = S.counters(); assert (c["consulted"], c["fired"], c["errors"]) == (1, 1, 1)
    rep = census.census({"t.recorder"}); r = _row(rep, "t.recorder")
    assert r["status"] == "UNMEASURED" and rep["snapshot"]["measurement_failures"] == {"t.recorder": {"RuntimeError": 1}}
    census.trace(False)


def test_r6_1_a_failed_decline_classifier_reads_unmeasured_not_unexercised(monkeypatch):
    """R6-1(ii): a classifier that raises preserved the product result but reported UNEXERCISED (1,0,0)."""
    def bad(decision):
        raise RuntimeError("classifier failed")
    S = census.declare_site("t.classifier", declines=bad); census.enable(True)
    with S.consult():
        out = S.fire(False, "withhold")
    assert out is False
    c = S.counters(); assert (c["consulted"], c["fired"], c["errors"]) == (1, 0, 1)
    assert _row(census.census({"t.classifier"}), "t.classifier")["status"] == "UNMEASURED"


def test_r6_1_a_failed_consult_increment_reads_unmeasured_the_report_stays_valid_and_is_insufficient(monkeypatch):
    """R6-1(iii): (0,1,1) — the row is UNMEASURED; the validator no longer refuses the WHOLE report for the
    arithmetic of a row whose measurement failed (INV-2's isolation), but the report is refused as EVIDENCE
    by `insufficiency()`, naming the id and the failure kind. Detection existed (the validator's fired >
    consulted); the deliverable is a row and a report that are not misleading."""
    ct = _evidence("census_table")
    S = census.declare_site("t.consult-fails"); N = census.declare_site("t.neighbour"); census.enable(True)
    orig = census.Site._bump
    def bump(self, field):
        if field == "consulted" and self.site_id == "t.consult-fails":
            raise RuntimeError("consult increment failed")
        return orig(self, field)
    monkeypatch.setattr(census.Site, "_bump", bump)
    with S.consult():
        try: raise S.fire(ValueError("refuse"))
        except ValueError: pass
    with N.consult():
        try: raise N.fire(ValueError("refuse"))
        except ValueError: pass
    c = S.counters(); assert (c["consulted"], c["fired"], c["errors"]) == (0, 1, 1)
    rep = census.census({"t.consult-fails", "t.neighbour"})
    assert _row(rep, "t.consult-fails")["status"] == "UNMEASURED" and _row(rep, "t.neighbour")["status"] == "EXERCISED"
    assert ct.validate_report(rep, {"t.consult-fails", "t.neighbour"}) == []          # valid: the neighbour is not invalidated
    bad = ct.insufficiency(rep); assert len(bad) == 1 and "t.consult-fails" in bad[0] and "RuntimeError" in bad[0]
    # the control: a fired > consulted row with NO error is still refused by the validator
    rep2 = census.census({"t.neighbour"}); _row(rep2, "t.neighbour").update(fired=5, consulted=1, errors=0)
    assert any("fired > consulted" in p for p in ct.validate_report(rep2, {"t.neighbour"}))


# ---- round 6, cell E: a missing registration is not a valid zero ----------------------------------------------

def test_r6_3_a_declared_id_whose_module_is_loaded_but_never_registered_is_refused_and_an_unloaded_one_is_named():
    ct = _evidence("census_table")
    A = census.declare_site("t.registered"); census.enable(True)
    with A.consult():
        A.fire(None)
    decl = {"t.registered", "t.never-registered", "t.not-loaded"}
    rep = census.census(decl)
    assert _row(rep, "t.never-registered")["status"] == "UNREACHED"          # the row alone cannot tell (the finding)
    assert ct.validate_report(rep, decl) == []                              # without the scan's map: as before
    # the loaded-module observation is the EVIDENCE layer's (specs/0031 keeps sys.modules out of src) and the
    # snapshot does not pretend to carry it; the validator refuses a scan map without it
    assert "loaded_modules" not in rep["snapshot"] and rep["snapshot"]["registered"] == ["t.registered"]
    loaded = ct.loaded_product_modules(); assert "census.py" in loaded
    site_modules = {"t.registered": "census.py", "t.never-registered": "census.py", "t.not-loaded": "never/imported.py"}
    assert any("`loaded_modules`" in p for p in ct.validate_report(rep, decl, site_modules))
    probs = ct.validate_report(rep, decl, site_modules, loaded)
    assert any("t.never-registered" in p and "missing registration" in p for p in probs)     # loaded, unregistered: REFUSED
    assert not any("t.not-loaded" in p for p in probs)                                       # not loaded: not a refusal …
    assert ct.out_of_reach(decl, site_modules, loaded) == ["t.not-loaded"]                   # … but NAMED, never a silent zero
    # a WRONG scan (D feeds E): a registered id mapped to an unloaded module is a refusal about the scan
    wrong = dict(site_modules, **{"t.registered": "never/imported.py"})
    assert any("t.registered" in p and "the scan is wrong" in p for p in ct.validate_report(rep, decl, wrong, loaded))
    # a declared id the scan does not carry at all is a refusal too
    assert any("not in the scan" in p for p in ct.validate_report(rep, decl, {"t.registered": "census.py"}, loaded))


def test_the_snapshot_carries_only_ids_module_paths_and_type_names():
    """INV-8 at the snapshot: the round-6 fields are names, never content."""
    S = census.declare_site("t.inv8"); census.enable(True)
    with S.consult():
        S.fire(None)
    snap = census.census({"t.inv8"})["snapshot"]
    assert all(isinstance(x, str) and x == x.strip() and " " not in x for x in snap["registered"])
    assert "loaded_modules" not in snap            # not the product's observation (specs/0031); see census_table
    assert all(isinstance(v, dict) and all(k.isidentifier() and isinstance(n, int) for k, n in v.items()) for v in snap["measurement_failures"].values())
