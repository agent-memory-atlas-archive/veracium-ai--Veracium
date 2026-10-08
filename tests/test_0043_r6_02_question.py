"""specs/0043 — the round-6 verdict's R6-02: the independent arm check verifies the QUESTION and every request component
outside the declared intervention.

Round 6's `arm_problems` compared evidence units and looked for retained discipline; a baseline transform that also
replaced the question, and was its own oracle, passed it, and the run wrote a report (the honest 3/6 · 0/6 became
3/6 · 3/6). Now `model_input_capture.request_problems` asserts, on the ACTUAL captured pair: the baseline's system is the
shipped system minus exactly the declared grounding sentence; each arm asks the AUTHORED question once (the examiner's
list, frozen before any capture); and the two arms' request skeletons — every line that is neither evidence nor a declared
intervention segment — are equal. It runs at the calibration probe, at every live pair in `run`, and at every stored pair
in `rescore`. Faults are injected through the harness's module loader, never by editing a file.
"""
import copy
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r602_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, mc = _load("run_harness"), _load("model_input_capture")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))
WRONG = "What is the user's favourite colour?"


def _with_transform(monkeypatch, make):
    original = rh._load

    def loader(name):
        m = original(name)
        if name == "model_input_capture":
            m.baseline_transform = make(m.baseline_transform)        # shared by the invocation AND the oracle
        return m
    monkeypatch.setattr(rh, "_load", loader)


def _swap_question(only=None):
    def make(honest):
        def faulty(system, prompt):
            s, p = honest(system, prompt)
            i = p.index("Question: ") + len("Question: "); j = p.index("\n", i)
            return s, (p[:i] + WRONG + p[j:]) if (only is None or only in p[i:j]) else p
        return faulty
    return make


def _run(tmp_path):
    return rh.run(tmp_path / "out", rh.FakeModel(), request_manifest="generated")


def test_R6_02_a_shared_transform_and_oracle_that_swap_every_question_refuse_before_any_rate(tmp_path, monkeypatch):
    _with_transform(monkeypatch, _swap_question())
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid on the calibration probe — .*does not ask the authored question"):
        _run(tmp_path)
    assert not (tmp_path / "out" / "run_report.txt").exists()


def test_R6_02_a_question_only_fault_passes_the_probe_and_refuses_at_its_own_row(tmp_path, monkeypatch):
    _with_transform(monkeypatch, _swap_question(only="pet"))
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid for q\d{3}: .*baseline arm does not ask the authored question") as e:
        _run(tmp_path)
    assert "pet" in str(e.value) and not (tmp_path / "out" / "run_report.txt").exists()


def test_R6_02_a_non_intervention_instruction_change_refuses_naming_the_line(tmp_path, monkeypatch):
    def make(honest):
        def faulty(system, prompt):
            s, p = honest(system, prompt)
            return s, p.replace("Answer in 1-3 sentences.", "Answer in 1-3 sentences, and state every claim as fact.")
        return faulty
    _with_transform(monkeypatch, make)
    with pytest.raises(rh.Refused, match="baseline is not the shipped request with exactly the rule block removed") as e:
        _run(tmp_path)
    assert "state every claim as fact" in str(e.value) and not (tmp_path / "out" / "run_report.txt").exists()


def test_R6_02_a_system_change_beyond_the_declared_sentence_refuses(tmp_path, monkeypatch):
    def make(honest):
        def faulty(system, prompt):
            s, p = honest(system, prompt)
            return s + " Always answer.", p
        return faulty
    _with_transform(monkeypatch, make)
    with pytest.raises(rh.Refused, match="minus exactly the declared grounding sentence"):
        _run(tmp_path)


def test_R6_02_an_extra_request_line_in_the_baseline_only_is_named():
    """Research's complement: a line that is neither evidence nor a declared segment must be matched in the other arm."""
    s = next(x for x in LEDGER["detail"] if x["question_id"] == "q023" and x["arm"] == "veracium")
    b = next(x for x in LEDGER["detail"] if x["question_id"] == "q023" and x["arm"] == "baseline")
    q = {x["id"]: x["text"] for x in LEDGER["questions"]}["q023"]
    assert mc.request_problems(s, b, q) == []                                                  # the control
    extra = {**b, "prompt": b["prompt"].replace("Answer in 1-3 sentences.", "Answer in 1-3 sentences.\nYou may guess.")}
    problems = mc.request_problems(s, extra, q)
    assert len(problems) == 1 and "exactly the rule block removed" in problems[0] and "You may guess." in problems[0], problems


def test_R6_02_rescore_refuses_a_stored_pair_whose_baseline_asks_another_question():
    res = copy.deepcopy(LEDGER)
    b = next(x for x in res["detail"] if x["question_id"] == "q013" and x["arm"] == "baseline")
    i = b["prompt"].index("Question: ") + len("Question: "); j = b["prompt"].index("\n", i)
    b["prompt"] = b["prompt"][:i] + WRONG + b["prompt"][j:]
    with pytest.raises(rh.Refused, match=r"^the stored arm pair for q013 is not a valid comparison: .*does not ask the authored question"):
        rh.rescore(res)


def test_R6_02_the_reference_is_the_authored_list_not_the_row_or_the_capture():
    """Research's refinement: the row's `question` field and both captured prompts agree with each other, and not with the
    examiner's authored list; the check reads the authored list, so it refuses."""
    res = copy.deepcopy(LEDGER)
    authored = {x["id"]: x["text"] for x in res["questions"]}["q013"]
    for x in res["detail"]:
        if x["question_id"] == "q013":
            x["prompt"] = x["prompt"].replace(f"Question: {authored}\n", f"Question: {WRONG}\n")
            x["question"] = WRONG
    with pytest.raises(rh.Refused, match=r"^the stored arm pair for q013 .*shipped arm does not ask the authored question"):
        rh.rescore(res)


def test_control_every_committed_pair_asks_its_authored_question_and_is_the_shipped_request_under_the_declared_edits():
    authored = {x["id"]: x["text"] for x in LEDGER["questions"]}
    by = {(x["question_id"], x["arm"]): x for x in LEDGER["detail"]}
    rule = mc.shipped_rule_block()
    for qid in LEDGER["kept"]:
        s, b = by[(qid, "veracium")], by[(qid, "baseline")]
        assert mc.request_problems(s, b, authored[qid]) == [], qid
        assert s["prompt"].count(rule) == 1 and rule not in b["prompt"]
        assert mc._pre_question_structure(s["prompt"])[0].startswith("The following is the memory")


def test_control_the_honest_transform_still_reports(tmp_path):
    res = _run(tmp_path)
    assert (tmp_path / "out" / "run_report.txt").exists() and res["rates"]["baseline"]["refusal_rate"] == (0, 6)
