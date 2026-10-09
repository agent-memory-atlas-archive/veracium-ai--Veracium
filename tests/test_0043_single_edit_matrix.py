"""specs/0043 — the arm check under the generated single-edit matrix (process adjustment 1, 2026-10-09).

For the committed pairs, every undeclared single edit of the BASELINE (tests/single_edit_matrix.py, plus the edits
only the 0043 declaration can name) must refuse in `model_input_capture.arm_problems` — THE per-pair check the run,
rescoring and publication call, never one of its parts (at the round-8 pin `request_problems` alone accepted an added
sentence that `arm_problems`' evidence comparison refused) — and every declared whitespace edit before the question
must pass. Three mutants prove the matrix can fail: the round-8 defect, an order-blind comparison, and a
whitespace-blind one. A gate that cannot catch the defect it was built after is not a gate.

Representatives: one per distinct pre-question block, derived from the ledger. The text from the Question line on is
the same in every kept pair apart from the question itself (asserted below), so the shapes cover that region too.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sem = _load(ROOT / "tests" / "single_edit_matrix.py", "sem_0043")
mc = _load(EVIDENCE / "model_input_capture.py", "sem_0043_mc")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))
AUTHORED = {q["id"]: q["text"] for q in LEDGER["questions"]}
BY = {(x["question_id"], x["arm"]): x for x in LEDGER["detail"]}
STOP = "Question:"


def _halves(prompt):
    """(the text before the Question line, the lines from it on), split by the check's own rule: the first line
    STARTING WITH "Question:"."""
    lines = prompt.split("\n")
    q = sem.split_at(lines, STOP)
    return "\n".join(lines[:q]), lines[q:]


def _key(q):
    return tuple(_halves(BY[(q, arm)]["prompt"])[0] for arm in ("veracium", "baseline"))


def _accepts(qid, field="prompt"):
    s, b = BY[(qid, "veracium")], BY[(qid, "baseline")]
    return lambda t: mc.arm_problems(s, {**b, field: t}, AUTHORED[qid]) == []


def _shapes():
    """One representative per DISTINCT pre-question block (the pair of them, shipped and baseline), derived from the
    ledger, never listed: retrieval order differs by question, and order is what this check must hold. A hand-picked
    q013 would have covered one of the six shapes the committed run has."""
    reps = {}
    for q in LEDGER["kept"]:
        reps.setdefault(_key(q), q)
    return sorted(reps.values())


SHAPES = _shapes()


def test_the_representatives_cover_every_kept_pairs_shape_and_there_is_more_than_one():
    every = {_key(q) for q in LEDGER["kept"]}
    assert {_key(q) for q in SHAPES} == every and len(SHAPES) == len(every)
    assert len(SHAPES) > 1                       # a property of the FROZEN committed ledger, not of the check


def test_the_text_from_the_question_on_differs_between_kept_pairs_only_in_the_question():
    """Why the shapes also cover the post-question region: there, every kept pair is q013's text with its own question
    line. If a future ledger breaks this, the matrix must widen to every distinct post-question block."""
    for arm in ("veracium", "baseline"):
        ref = _halves(BY[("q013", arm)]["prompt"])[1][1:]
        for q in LEDGER["kept"]:
            post = _halves(BY[(q, arm)]["prompt"])[1]
            assert post[0] == f"Question: {AUTHORED[q]}" and post[1:] == ref, (q, arm)


def _view(text):
    """What the DECLARATION says an allowed edit preserves, written from it and NOT from the generator (so the two cannot
    agree with themselves): the non-blank lines before the Question line, in order, and every line from it on. Research's
    stage-1 self-check: an undeclared edit must change this view; a declared one must not."""
    lines = text.split("\n")
    q = sem.split_at(lines, STOP)
    return [l for l in lines[:q] if l.strip()], lines[q:]


SYNTHETIC = "\n\nA line\nB line\n\nQuestion: x\n\nrule"     # leading blanks: the to-top mirror research found


@pytest.mark.parametrize("text", [pytest.param(SYNTHETIC, id="synthetic")] +
                         [pytest.param(BY[(q, "baseline")]["prompt"], id=q) for q in SHAPES])
def test_the_generators_agree_with_the_declaration_every_undeclared_edit_changes_the_view_and_no_declared_one_does(text):
    """Catches a generator that labels a whitespace-only edit as undeclared (to-above-stop's first form, the to-top
    mirror) AT GENERATION, before the check has to rightly accept it."""
    v = _view(text)
    covered = [l for l, t in sem.single_line_edits(text, stop=STOP) if _view(t) == v]
    uncovered = [l for l, t in sem.declared_whitespace_edits(text, stop=STOP) if _view(t) != v]
    assert covered == [] and uncovered == [], (covered, uncovered)


def test_control_the_generators_change_every_input_and_cover_every_kind():
    b = BY[("q013", "baseline")]["prompt"]
    undeclared = list(sem.single_line_edits(b, stop=STOP))
    declared = list(sem.declared_whitespace_edits(b, stop=STOP))
    for edits in (undeclared, declared):
        assert edits and all(t != b for _, t in edits) and len({t for _, t in edits}) == len(edits)
    assert {l.split()[0] for l, _ in undeclared} == {"delete", "duplicate", "indent", "trailing-space", "zero-width",
                                                    "alter", "added-sentence", "to-top", "to-above-stop", "swap", "join",
                                                    "whitespace", "delete-blank"}
    assert all("after-stop" in l for l, _ in undeclared if l.split()[0] in ("whitespace", "delete-blank"))
    assert {l.split()[0] for l, _ in declared} == {"whitespace", "blank", "delete-blank"}
    assert any("before L0" in l for l, _ in declared)


@pytest.mark.parametrize("qid", SHAPES)
def test_every_undeclared_single_edit_refuses_and_every_declared_whitespace_edit_passes(qid):
    accepts, b = _accepts(qid), BY[(qid, "baseline")]["prompt"]
    assert accepts(b), "the honest committed pair must pass"
    found = sem.disagreements(accepts, sem.single_line_edits(b, stop=STOP), sem.declared_whitespace_edits(b, stop=STOP))
    assert found == []


@pytest.mark.parametrize("qid", SHAPES)
def test_a_shipped_only_line_re_added_anywhere_before_the_question_refuses(qid):
    """The R7-01 class: every SHIPPED-ONLY pre-question line (derived as the complement: a declared removal, a rename's
    original, a marked evidence line's shipped form) put back into the baseline at every pre-question position — a
    look-alike the declaration itself produces, which a symmetric normaliser would erase."""
    s, b = BY[(qid, "veracium")]["prompt"], BY[(qid, "baseline")]["prompt"]
    pre_s, pre_b = _halves(s)[0].split("\n"), _halves(b)[0].split("\n")
    shipped_only = [l for l in pre_s if l.strip() and l not in pre_b]       # the COMPLEMENT, derived (research, stage-1)
    named = [l for l in pre_s if l.strip() in mc.INTERVENTION_REMOVED_LINES or l in mc.INTERVENTION_RENAMED_LINES]
    assert named and set(named) <= set(shipped_only), "every line the declaration names is among the shipped-only lines"
    assert len(shipped_only) > len(named)   # here also the MARKED evidence lines: the originals of declared_evidence_edit
    lines = b.split("\n")
    q = sem.split_at(lines, STOP)
    edits = [(f"re-add {l[:30]!r} at L{i}", "\n".join(lines[:i] + [l] + lines[i:]))
             for l in shipped_only for i in range(q + 1)]
    assert sem.disagreements(_accepts(qid), edits, []) == []


def test_every_single_edit_of_the_baseline_system_refuses():
    b = BY[("q013", "baseline")]["system"]
    edits = list(sem.single_line_edits(b))
    assert edits
    assert sem.disagreements(_accepts("q013", field="system"), edits, []) == []


def _found_on_q013(accepts):
    b = BY[("q013", "baseline")]["prompt"]
    return sem.disagreements(accepts, sem.single_line_edits(b, stop=STOP), sem.declared_whitespace_edits(b, stop=STOP))


def test_mutant_the_round8_defect_evidence_dropped_from_the_sequence_is_caught(monkeypatch):
    real = mc._pre_question_lines
    monkeypatch.setattr(mc, "_pre_question_lines", lambda p: [l for l in real(p) if not mc._is_evidence_line(l)])
    found = _found_on_q013(_accepts("q013"))
    assert any(f.startswith("ACCEPTED undeclared: swap") for f in found), found


def test_mutant_a_whitespace_blind_comparison_is_caught(monkeypatch):
    """Research's mutant (stage-1, 2026-10-09): lines compared after .strip(). The honest pair and the allowance still
    pass; only the indent and trailing-space kinds can catch it, which is what makes them load-bearing."""
    real = mc._pre_question_lines
    monkeypatch.setattr(mc, "_pre_question_lines", lambda p: [l.strip() for l in real(p)])
    accepts = _accepts("q013")
    assert accepts(BY[("q013", "baseline")]["prompt"])
    found = _found_on_q013(accepts)
    assert not any(f.startswith("REFUSED declared") for f in found), found
    assert {"indent", "trailing-space"} <= {f.split(": ", 1)[1].split()[0] for f in found}, found


def test_mutant_an_order_blind_comparison_is_caught():
    """The R8-01 class from the other side: a check that compares the pre-question lines as a MULTISET. Emulated by
    handing the real check the honest order whenever an edited prompt's non-blank pre-question lines are a permutation
    of the honest ones — so the honest pair and the declared whitespace still pass, and the mutant must be caught by
    ACCEPTING an undeclared edit, never by refusing everything (this cell's first form sorted one side only and refused
    the honest pair: vacuous)."""
    real = _accepts("q013")
    honest_pre = _halves(BY[("q013", "baseline")]["prompt"])[0]
    honest_set = sorted(l for l in honest_pre.split("\n") if l.strip())

    def order_blind(p):
        lines = p.split("\n")
        q = sem.split_at(lines, STOP)
        if q < len(lines) and sorted(l for l in lines[:q] if l.strip()) == honest_set:
            p = "\n".join([honest_pre] + lines[q:])
        return real(p)

    found = _found_on_q013(order_blind)
    assert order_blind(BY[("q013", "baseline")]["prompt"]) and not any(f.startswith("REFUSED declared") for f in found), found
    assert any(f.startswith("ACCEPTED undeclared: swap") for f in found), found
