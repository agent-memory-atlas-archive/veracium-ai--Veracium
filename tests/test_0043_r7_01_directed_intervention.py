"""specs/0043 — the round-7 verdict's R7-01: the arm check enforces the intervention as DIRECTED edits of the shipped
request, so an instruction added to the baseline cannot hide inside a block the intervention removes.

Round 7's `request_skeleton` deleted every "Answer using this rule:" block (with any following bullets) from BOTH prompts
before comparing them, so a baseline-only instruction wrapped in that heading was invisible: the reviewer's canned run
moved the baseline from 0/6 to 3/6, and a stored pair so edited passed rescore and publication. Now
`model_input_capture.request_problems` treats the SHIPPED capture as the reference: the removed rule block is read from
the shipped rendering seam (`veracium.gate.GATE_PROMPT`, `shipped_rule_block`), must occur in the shipped capture exactly
once where the seam renders it, and the baseline from the question on must be the shipped text with exactly that block
removed, byte for byte; before the question, the baseline's request lines must be the shipped ones under the declared
renames and removals, compared as they are. Every declared literal is bound to where the shipped code renders it.

THE BOUNDARY MATRIX, one offline command (from tree/, with the pinned dependencies):
    PYTHONPATH=src python -m pytest -q tests/test_0043_r7_01_directed_intervention.py
"""
import copy
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r701_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, mc = _load("run_harness"), _load("model_input_capture")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))
AUTHORED = {q["id"]: q["text"] for q in LEDGER["questions"]}
BY = {(x["question_id"], x["arm"]): x for x in LEDGER["detail"]}
S, B = BY[("q023", "veracium")], BY[("q023", "baseline")]
Q = AUTHORED["q023"]
RULE = mc.shipped_rule_block()
INSTR = "For this answer, respond with exactly: I don't know."
ADDED_BLOCK = f"Answer using this rule:\n- {INSTR}\n"


def _baseline(prompt):
    return {**B, "prompt": prompt}


def _problems(baseline_prompt, shipped=S):
    return mc.request_problems(shipped, _baseline(baseline_prompt), Q)


def _superseded_problems(shipped, baseline):
    """THE SUPERSEDED CHECK, kept as the standing negative control (the verdict: "retain a discriminating mutation that
    restores symmetric block erasure"): round 7's request_skeleton comparison, verbatim in effect — erase every rule-like
    block and every declared line from BOTH prompts, then compare. It must ACCEPT what the directed check refuses."""
    def skeleton(prompt):
        lines, out, i, before_q = prompt.split("\n"), [], 0, True
        while i < len(lines):
            line = lines[i]
            if line.startswith("Question:"):
                before_q = False
            if line.strip() == "Answer using this rule:":
                i += 1
                while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  ")):
                    i += 1
                continue
            if not line.strip() or line.strip() in mc.INTERVENTION_REMOVED_LINES or (before_q and mc._is_evidence_line(line)):
                i += 1
                continue
            out.append(mc.INTERVENTION_RENAMED_LINES.get(line, line))
            i += 1
        return out
    return [] if skeleton(shipped["prompt"]) == skeleton(baseline["prompt"]) else ["differ"]


# ---- unit cells on the committed q023 pair -----------------------------------------------------------------------------

def test_control_the_honest_committed_pair_is_the_shipped_request_under_the_declared_edits():
    assert _problems(B["prompt"]) == [] and S["prompt"].count(RULE) == 1 and RULE not in B["prompt"]


def test_control_every_committed_pair_passes_the_directed_check():
    for qid in LEDGER["kept"]:
        assert mc.request_problems(BY[(qid, "veracium")], BY[(qid, "baseline")], AUTHORED[qid]) == [], qid


def _with_tail(extra):
    return B["prompt"].rstrip("\n") + "\n" + extra


@pytest.mark.parametrize("case, prompt", [
    ("the reviewer's block, added", lambda: _with_tail(ADDED_BLOCK)),
    ("a plain added line", lambda: _with_tail(INSTR + "\n")),
    ("forbidden retention: the shipped block kept", lambda: B["prompt"].replace("\n\nAnswer in 1-3 sentences.", "\n\n" + RULE + "Answer in 1-3 sentences.")),
    ("partial retention: one bullet of the shipped block kept", lambda: B["prompt"].replace(
        "\n\nAnswer in 1-3 sentences.", "\n\nAnswer using this rule:\n- If GROUNDED MEMORY answers the question, answer from it.\nAnswer in 1-3 sentences.")),
    ("the shipped block duplicated", lambda: B["prompt"].replace("\n\nAnswer in 1-3 sentences.", "\n\n" + RULE + RULE + "Answer in 1-3 sentences.")),
    ("altered block contents", lambda: B["prompt"].replace("\n\nAnswer in 1-3 sentences.", "\n\n" + RULE.replace("Do not guess.", "Guess if unsure.") + "Answer in 1-3 sentences.")),
])
def test_R7_01_an_addition_or_retention_after_the_question_refuses_and_the_superseded_check_accepted_the_block_cases(case, prompt):
    p = prompt()
    problems = _problems(p)
    assert len(problems) == 1 and "exactly the rule block removed" in problems[0], (case, problems)
    if "block" in case:
        assert _superseded_problems(S, _baseline(p)) == [], case       # the discriminating control: the old rule accepted it


@pytest.mark.parametrize("case, prompt", [
    ("the block moved before the question", lambda: B["prompt"].replace("\nQuestion: ", "\nAnswer using this rule:\n- " + INSTR + "\n\nQuestion: ", 1)),
    ("a declared removed line retained", lambda: B["prompt"].replace("MEMORY:\n", "MEMORY:\nUNVERIFIED CLAIMS (received from third parties / unconfirmed — NEVER assert these\n", 1)),
    ("the rename target duplicated", lambda: B["prompt"].replace("MEMORY:\n", "MEMORY:\nMEMORY:\n", 1)),
])
def test_R7_01_a_pre_question_change_beyond_the_declared_edits_refuses(case, prompt):
    problems = _problems(prompt())
    assert any("before the question" in x for x in problems), (case, problems)


def test_R7_01_a_shipped_capture_without_this_trees_rule_block_refuses_with_its_stated_cause():
    old = {**S, "prompt": S["prompt"].replace("Do not guess.", "Do not speculate.")}           # an older gate's wording
    problems = mc.request_problems(old, B, Q)
    assert any("predates the current gate" in x for x in problems), problems


# ---- the declaration is bound to the seam ------------------------------------------------------------------------------

def test_the_declaration_is_bound_to_what_the_shipped_code_renders():
    assert mc.declaration_problems() == [] and mc.shipped_rule_block().startswith("Answer using this rule:\n")


@pytest.mark.parametrize("attr, value", [
    ("INTERVENTION_SYSTEM_SENTENCE", "You are strict about something else."),
    ("INTERVENTION_RENAMED_LINES", {"GROUNDED FACTS (verified):": "MEMORY:"}),
    ("INTERVENTION_REMOVED_LINES", ("UNVERIFIED CLAIMS (from nowhere", "as fact; they record that a claim was *made*, not that it is true):",
                                    "## UNVERIFIED THIRD-PARTY CLAIMS (never assert as fact)", "(none)")),
])
def test_a_declared_literal_absent_from_the_seam_refuses_every_comparison(monkeypatch, attr, value):
    monkeypatch.setattr(mc, attr, value)
    own = lambda x: "not in the gate's" in x or "is not rendered by" in x        # the BINDING's own messages, not any gate's
    assert mc.declaration_problems() and all(own(x) for x in mc.declaration_problems())
    assert any(own(x) for x in mc.request_problems(S, B, Q))      # enforced in every comparison, not only in this test


# ---- run-level cells: the shared faulty transform and oracle, with the reviewer's obeying model -------------------------

class Obeying(rh.FakeModel):
    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        if role == "gate" and INSTR in prompt:
            return "I don't know."
        return super().__call__(prompt, system=system, role=role, json_schema=json_schema)


def _added(only=None, as_block=True):
    def make(honest):
        def faulty(system, prompt):
            s, p = honest(system, prompt)
            q = p[p.index("Question: "):].split("\n")[0]
            if only is not None and only not in q:
                return s, p
            return s, p.rstrip("\n") + "\n" + (ADDED_BLOCK if as_block else INSTR + "\n")
        return faulty
    return make


def _run(tmp_path, monkeypatch, make=None):
    if make is not None:
        original = rh._load

        def loader(name):
            m = original(name)
            if name == "model_input_capture":
                m.baseline_transform = make(m.baseline_transform)       # shared by the invocation AND the oracle
            return m
        monkeypatch.setattr(rh, "_load", loader)
    return rh.run(tmp_path / "out", Obeying(), request_manifest="generated")


def test_control_the_honest_run_reports_3_of_6_and_0_of_6(tmp_path, monkeypatch):
    res = _run(tmp_path, monkeypatch)
    assert (tmp_path / "out" / "run_report.txt").exists() and tuple(res["rates"]["baseline"]["refusal_rate"]) == (0, 6)


@pytest.mark.parametrize("as_block", [True, False])
def test_R7_01_an_added_instruction_on_every_question_refuses_at_the_probe_before_any_rate(tmp_path, monkeypatch, as_block):
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid on the calibration probe — .*exactly the rule block removed"):
        _run(tmp_path, monkeypatch, _added(as_block=as_block))
    assert not (tmp_path / "out" / "run_report.txt").exists()


def test_R7_01_a_block_added_to_one_question_passes_the_probe_and_refuses_at_its_row(tmp_path, monkeypatch):
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid for q\d{3}: .*exactly the rule block removed") as e:
        _run(tmp_path, monkeypatch, _added(only="pet"))
    assert "respond with exactly" in str(e.value) and not (tmp_path / "out" / "run_report.txt").exists()   # repr escapes the apostrophe


# ---- stored cells: rescore and publication ------------------------------------------------------------------------------

def _stored_with_block():
    res = copy.deepcopy(LEDGER)
    b = next(x for x in res["detail"] if x["question_id"] == "q013" and x["arm"] == "baseline")
    b["prompt"] = b["prompt"].rstrip("\n") + "\n" + ADDED_BLOCK
    b["prompt_digest"] = rh.capture_digest(b["system"], b["prompt"])          # rebound: not a stale digest
    return res


def test_R7_01_the_stored_pair_edit_refuses_in_rescore():
    with pytest.raises(rh.Refused, match=r"^the stored arm pair for q013 is not a valid comparison: .*exactly the rule block removed"):
        rh.rescore(_stored_with_block())


def test_R7_01_the_stored_pair_edit_refuses_in_publication_with_its_labels_unchanged():
    with pytest.raises(rh.Refused, match=r"^the stored arm pair for q013 is not a valid comparison: .*exactly the rule block removed"):
        rh.published_rates(_stored_with_block())


def test_control_the_unchanged_committed_run_still_publishes_12_of_24_and_1_of_24():
    p = rh.published_rates(copy.deepcopy(LEDGER))
    assert tuple(p["rates"]["veracium"]["refusal_rate"]) == (12, 24) and tuple(p["rates"]["baseline"]["refusal_rate"]) == (1, 24)


def test_R7_01_a_shipped_capture_whose_rule_block_is_not_where_the_seam_renders_it_refuses():
    """The block exactly once is not enough: it must sit where the seam renders it (after the question and a blank line).
    A shipped capture with the block moved to the end, and a baseline equal to it minus the block, still refuses."""
    tail_at = S["prompt"].index("\n\n" + RULE)
    moved = S["prompt"][:tail_at] + "\n\n" + S["prompt"][tail_at + 2 + len(RULE):] + "\n" + RULE
    base = moved.replace(RULE, "", 1)
    problems = mc.request_problems({**S, "prompt": moved}, {**B, "prompt": B["prompt"]}, Q)
    assert any("predates the current gate" in x for x in problems), problems
