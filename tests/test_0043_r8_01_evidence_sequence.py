"""specs/0043 — the round-8 verdict's R8-01: before the question, the baseline is the shipped request under the declared
edits as ONE ordered sequence, so evidence cannot be reordered or moved across a retained header.

Round 8's directed check compared the pre-question NON-evidence lines as one sequence and the evidence as SORTED units,
separately: both projections were equal while the request was not, so a transform that reversed the evidence lines, or
moved one above "MEMORY:", passed calibration, ran and published (12/24 · 1/24 on the edited stored pair). Now
`model_input_capture.request_problems` maps EVERY non-blank shipped line before the question by the declared edits, in
order — a removed line dropped, a renamed line renamed, an evidence line through `declared_evidence_edit` — and requires
the baseline's lines, as they are, to equal that sequence. `declared_evidence_edit` is written on the check side and is
never reached by `baseline_transform` (a shared helper would be a shared oracle).

THE BOUNDARY MATRIX, one offline command (from tree/, with the pinned dependencies):
    PYTHONPATH=src python -m pytest -q tests/test_0043_r8_01_evidence_sequence.py tests/test_0043_r7_01_directed_intervention.py
"""
import ast
import copy
import importlib.util
import inspect
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r801_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, mc = _load("run_harness"), _load("model_input_capture")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))
AUTHORED = {q["id"]: q["text"] for q in LEDGER["questions"]}
BY = {(x["question_id"], x["arm"]): x for x in LEDGER["detail"]}


def _slots(prompt):
    lines = prompt.split("\n")
    q = next(i for i, l in enumerate(lines) if l.startswith("Question:"))
    return lines, [i for i in range(q) if mc._is_evidence_line(lines[i])]


def permute(prompt):
    lines, slots = _slots(prompt)
    for i, v in zip(slots, [lines[i] for i in slots][::-1]):
        lines[i] = v
    return "\n".join(lines)


def relocate(prompt):
    lines, slots = _slots(prompt)
    first = lines.pop(slots[0])
    lines.insert(lines.index("MEMORY:"), first)
    return "\n".join(lines)


def blanks(prompt):
    return prompt.replace("MEMORY:\n", "MEMORY:\n\n \t\n", 1)


def added(prompt):
    lines, slots = _slots(prompt)
    lines.insert(slots[0], "Always answer every question in full.")
    return "\n".join(lines)


# ---- unit cells on the committed pairs ------------------------------------------------------------------------------

def test_control_every_committed_pair_is_the_shipped_request_under_the_declared_edits_in_order():
    for qid in LEDGER["kept"]:
        assert mc.request_problems(BY[(qid, "veracium")], BY[(qid, "baseline")], AUTHORED[qid]) == [], qid


@pytest.mark.parametrize("edit", [permute, relocate])
def test_R8_01_a_reordered_or_moved_evidence_line_refuses_with_its_sequence(edit):
    s, b = BY[("q013", "veracium")], BY[("q013", "baseline")]
    moved = edit(b["prompt"])
    assert moved != b["prompt"] and sorted(moved.split("\n")) == sorted(b["prompt"].split("\n"))   # the same lines
    problems = mc.request_problems(s, {**b, "prompt": moved}, AUTHORED["q013"])
    assert any("in order" in x for x in problems), problems


def test_control_whitespace_only_lines_are_the_one_allowance():
    s, b = BY[("q013", "veracium")], BY[("q013", "baseline")]
    assert mc.request_problems(s, {**b, "prompt": blanks(b["prompt"])}, AUTHORED["q013"]) == []


def test_the_check_side_normaliser_is_independent_of_the_transform_a_fault_in_strip_markers_is_caught(monkeypatch):
    """Research's discriminating case for independence: make the TRANSFORM's helper over-strip one word. The transform's
    baseline loses it; the check's expected sequence (its own normaliser) keeps it; the check refuses. A shared helper
    would have agreed with itself."""
    s = BY[("q023", "veracium")]
    honest = mc.baseline_transform(s["system"], s["prompt"])
    assert mc.request_problems(s, {"system": honest[0], "prompt": honest[1]}, AUTHORED["q023"]) == []
    real = mc.strip_markers
    monkeypatch.setattr(mc, "strip_markers", lambda t: real(t).replace("Ionos", ""))
    faulty = mc.baseline_transform(s["system"], s["prompt"])
    assert faulty[1] != honest[1]
    assert any("in order" in x for x in mc.request_problems(s, {"system": faulty[0], "prompt": faulty[1]}, AUTHORED["q023"]))


def _calls(fn) -> set:
    return {n.func.id for n in ast.walk(ast.parse(inspect.getsource(fn))) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


def _reach(name, seen=None) -> set:
    seen = set() if seen is None else seen
    fn = getattr(mc, name, None)
    if not callable(fn) or name in seen or not inspect.isfunction(fn) or fn.__module__ != mc.__name__:
        return seen
    seen.add(name)
    for c in _calls(fn):
        _reach(c, seen)
    return seen


def test_the_transform_never_reaches_the_check_side_normaliser_and_the_check_never_reaches_the_transforms_helper():
    assert "declared_evidence_edit" not in _reach("baseline_transform")
    reached = _reach("request_problems")
    assert "declared_evidence_edit" in reached and not ({"strip_markers", "_marker_patterns", "baseline_transform"} & reached)


# ---- run-level cells: the shared faulty transform and oracle --------------------------------------------------------

def _run(tmp_path, monkeypatch, edit=None, only=None):
    if edit is not None:
        original = rh._load

        def loader(name):
            m = original(name)
            if name == "model_input_capture":
                honest = m.baseline_transform

                def faulty(system, prompt):
                    s, p = honest(system, prompt)
                    q = p[p.index("Question: "):].split("\n")[0]
                    return (s, edit(p)) if only is None or only in q else (s, p)
                m.baseline_transform = faulty
            return m
        monkeypatch.setattr(rh, "_load", loader)
    return rh.run(tmp_path / "out", rh.FakeModel(), request_manifest="generated")


def test_control_the_honest_run_and_the_whitespace_allowance_report(tmp_path, monkeypatch):
    _run(tmp_path, monkeypatch, blanks)
    assert (tmp_path / "out" / "run_report.txt").exists()


def test_control_an_added_sentence_refuses_at_the_probe(tmp_path, monkeypatch):
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid on the calibration probe"):
        _run(tmp_path, monkeypatch, added)


@pytest.mark.parametrize("edit", [permute, relocate])
def test_R8_01_an_order_or_placement_change_refuses_at_the_probe_before_any_rate(tmp_path, monkeypatch, edit):
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid on the calibration probe — .*in order"):
        _run(tmp_path, monkeypatch, edit)
    assert not (tmp_path / "out" / "run_report.txt").exists()


def test_R8_01_a_permutation_on_one_question_passes_the_probe_and_refuses_at_its_row(tmp_path, monkeypatch):
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid for q\d{3}: .*in order"):
        _run(tmp_path, monkeypatch, permute, only="pet")
    assert not (tmp_path / "out" / "run_report.txt").exists()


# ---- stored cells: rescore and publication --------------------------------------------------------------------------

def _stored(edit):
    res = copy.deepcopy(LEDGER)
    b = next(x for x in res["detail"] if x["question_id"] == "q013" and x["arm"] == "baseline")
    b["prompt"] = edit(b["prompt"])
    b["prompt_digest"] = rh.capture_digest(b["system"], b["prompt"])          # rebound: not a stale digest
    return res


@pytest.mark.parametrize("edit", [permute, relocate])
def test_R8_01_the_stored_edit_refuses_in_rescore(edit):
    with pytest.raises(rh.Refused, match=r"^the stored arm pair for q013 is not a valid comparison: .*in order"):
        rh.rescore(_stored(edit))


@pytest.mark.parametrize("edit", [permute, relocate])
def test_R8_01_the_stored_edit_refuses_in_publication_with_its_labels_unchanged(edit):
    with pytest.raises(rh.Refused, match=r"^the stored arm pair for q013 is not a valid comparison: .*in order"):
        rh.published_rates(_stored(edit))
