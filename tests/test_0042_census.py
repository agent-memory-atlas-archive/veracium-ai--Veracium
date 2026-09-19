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
    census.enable(False); census.trace(False); census.trace_reset(); census._clear_registry()
    yield
    census.enable(False); census.trace(False); census.trace_reset(); census._clear_registry()


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
