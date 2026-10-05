"""specs/0043 round 6 — R5-03: the independent arm check gates the run.

Round 5's `run` called `model_input_capture.run()` and gated only on calibration: its `problems` were computed and never
read, and each question's baseline was checked only against the same `baseline_transform` that produced it. A faulty
transform shared by invocation and oracle (the compiled evidence removed, the grounding instruction kept) therefore
agreed with itself and the run wrote a report with rates, while the independent check reported both defects (the
verdict's `bad_transform_and_own_oracle_agree`). Now the probe's arm problems and its control gate the run, and every
question's ACTUAL captured pair is checked by `arm_problems` — what the two captured prompts carry, independent of the
transform, with no fixture sentinel — before any rate. Every cell runs `run()` end to end on the canned model; the
faults are injected through the harness's module loader, never by editing a file.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r6a_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh = _load("run_harness")


def _with_transform(make):
    """A module loader whose `model_input_capture` carries `make(honest)` as its baseline_transform — shared by the
    invocation AND the oracle, exactly as a faulty transform would be."""
    original = rh._load

    def loader(name):
        m = original(name)
        if name == "model_input_capture":
            m.baseline_transform = make(m.baseline_transform)
        return m
    return loader


def _run(tmp_path, monkeypatch, make=None, questions=None):
    if make is not None:
        monkeypatch.setattr(rh, "_load", _with_transform(make))
    return rh.run(tmp_path / "out", rh.FakeModel(), questions_override=questions)


def _drop_compiled_keep_grounding(honest):
    def faulty(system, prompt):
        _s, p = honest(system, prompt)
        return system, "\n".join(l for l in p.splitlines() if not l.startswith("- COMPILED-BODY")) + ("\n" if p.endswith("\n") else "")
    return faulty


def test_R5_03_a_faulty_transform_that_is_its_own_oracle_does_not_produce_a_report(tmp_path, monkeypatch):
    with pytest.raises(rh.Refused, match="arm comparison is not valid"):
        _run(tmp_path, monkeypatch, _drop_compiled_keep_grounding)
    assert not (tmp_path / "out" / "run_report.txt").exists()


def test_R5_03_a_fault_only_a_QUESTION_s_pair_shows_is_caught_per_question(tmp_path, monkeypatch):
    """A transform that is honest on the calibration probe's question and drops a fact line on another question's
    prompt: the probe passes, and the per-question gate refuses before any rate."""
    def make(honest):
        def faulty(system, prompt):
            s, p = honest(system, prompt)
            if "pet" in prompt.split("Question:")[-1].lower():
                p = "\n".join(l for l in p.splitlines() if not l.startswith("has_pet:")) + ("\n" if p.endswith("\n") else "")
            return s, p
        return faulty
    with pytest.raises(rh.Refused, match="arm comparison is not valid for q"):
        _run(tmp_path, monkeypatch, make)


def test_control_the_honest_transform_reports(tmp_path, monkeypatch):
    res = _run(tmp_path, monkeypatch)
    assert res["sources"] == {"veracium": "captured", "baseline": "captured"}
    assert (tmp_path / "out" / "run_report.txt").exists()


def test_control_the_honest_probe_pair_has_no_arm_problem():
    mc = _load("model_input_capture")
    probe = mc.run()
    assert probe["problems"] == [] and probe["control_refuses"]
