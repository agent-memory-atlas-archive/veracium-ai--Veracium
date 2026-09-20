"""specs/0043 tranche 2 — THE RUN, bound: the pipeline end to end on a canned model (no spend), and the
committed real-model report re-derived from its own ledger.

The pipeline test drives `run_harness.run` with `FakeModel`: the blind examiner authors from the view
alone, the classes attach after authorship, a non-blind question is EXCLUDED AND COUNTED, both arms are
captured (the baseline equal to the oracle), every row lands in one of the six outcomes, the ledger's
six checks pass with both sources `captured`, and the rates carry their denominators with `absent` NOT
PRESENTED. The report test reads `run_ledger.json` (the committed real run), re-runs the ledger gate
and recomputes every rate from the rows, and asserts the report's figures are those — a measured
artifact re-derived, never quoted — with the pin an ancestor of HEAD and the run's INPUTS re-derived at
HEAD without the model (`run_harness.reverify`): the fixture's view digest, the gate system, the prompt
outside the compiled-wiki block and the baseline transform, per kept question; the compiled-wiki block is
the run's own compile-role output and is carried, not re-derived — the one named exclusion.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


@pytest.fixture(scope="module")
def fake_run(tmp_path_factory):
    rh = _load("run_harness")
    out = tmp_path_factory.mktemp("run")
    return rh, rh.run(out, rh.FakeModel(), n_questions=6), out


def test_the_pipeline_runs_end_to_end_on_the_canned_model_and_the_ledger_passes_its_gate(fake_run):
    rh, res, out = fake_run
    lg = _load("ledger")
    assert res["sources"] == {"veracium": "captured", "baseline": "captured"} and res["arms"] == ["veracium", "baseline"]
    assert res["calibration"]["shipped"] == res["calibration"]["baseline"] and res["calibration"]["shipped"][0] == res["calibration"]["shipped"][1]
    assert res["calibration"]["garble_collapsed"]
    # the calibration gate, NAMED (research's point 1): the UNRESOLVED count on the reference cases is split into the
    # ambiguity control (expected) and known answers the judge could not resolve (unexpected — must be zero, or no run)
    assert res["calibration"]["unresolved_unexpected"] == 0 and res["calibration"]["unresolved_expected"] >= 1
    assert res["calibration"]["unresolved_on_reference"] == res["calibration"]["unresolved_expected"]
    assert res["calibration"]["interpreter_sha16"] == rh.interpreter_sha16() and "learned from runs 1 and 2" in res["calibration"]["independence"]
    expected = {q: c for q, c in [(x["question_id"], x["fixture_class"]) for x in res["ledger"]]}
    assert lg.gate(res["ledger"], expected, tuple(res["arms"]), exclusions=res["excluded"], sources=res["sources"]) == []
    assert all(r["outcome"] in lg.OUTCOMES for r in res["ledger"])
    # the non-blind question the canned examiner slipped in is EXCLUDED AND COUNTED, with its reason, and rides in the ledger
    assert len(res["excluded"]) == 1 and "trust marker" in next(iter(res["excluded"].values()))
    qid = next(iter(res["excluded"]))
    assert {r["arm"] for r in res["ledger"] if r["question_id"] == qid} == set(res["arms"])
    assert res["rates"]["veracium"]["excluded"] == 1
    # every kept question's class came from the manifest, never from the examiner
    assert set(res["manifest_classes"].values()) == {"grounded", "untrusted", "quarantined"}
    assert all(x["fixture_class"] in ("present-and-trusted", "present-but-untrusted", "present-but-quarantined") for x in res["detail"])
    assert res["rates"]["veracium"]["per_class"]["absent"] == "NOT PRESENTED"
    # the report exists and quotes the frozen inputs
    text = (out / "run_report.txt").read_text()
    head_line = re.search(r"^# generated \S+ against veracium @ (.+)$", text, re.M); assert head_line, text[:120]
    if (ROOT / ".git").exists():                       # a checkout pins the commit
        assert re.fullmatch(r"[0-9a-f]{40}", head_line.group(1)), head_line.group(0)
    else:                                              # an extracted archive DECLARES it is unpinned, never an empty pin
        assert head_line.group(1) == rh.UNPINNED, head_line.group(0)
    assert "fixture store digest (as built): " in text and "temperature" in text and "EXCLUDED (INV-6, counted)" in text


def test_a_tree_that_is_not_a_git_checkout_declares_itself_unpinned_and_a_checkout_pins_the_commit(monkeypatch):
    """The header's pin has two honest values and no third: the 40-hex of a checkout, or the declared marker of a
    git-less tree (an extracted review package). An EMPTY pin — what `git rev-parse` yields outside a checkout — is
    the outcome this test exists to refuse (2026-09-20, found by research's offline leg on the sealed package).
    DEPENDENCY, named: the git-less branch of the pipeline test above runs in NO checkout and NO CI lane — only in
    a git-less tree, which today means the review package's stage smoke and research's offline leg; narrow either
    and that branch goes dark. This test drives both answers in every environment so the mechanism is asserted
    wherever the suite runs."""
    rh = _load("run_harness")
    import subprocess as sp
    real = sp.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)   # the control, read BEFORE any patch
    class R:
        def __init__(self, rc, out): self.returncode, self.stdout = rc, out
    monkeypatch.setattr(rh.subprocess, "run", lambda *a, **k: R(128, ""))            # not a git checkout
    assert rh.tree_head() == rh.UNPINNED
    monkeypatch.setattr(rh.subprocess, "run", lambda *a, **k: R(0, "a" * 40 + "\n"))  # a checkout
    assert rh.tree_head() == "a" * 40
    monkeypatch.setattr(rh.subprocess, "run", lambda *a, **k: R(0, "\n"))             # git ran and answered nothing: still declared, never empty
    assert rh.tree_head() == rh.UNPINNED
    monkeypatch.undo()                                                                  # the control: this tree, un-patched
    assert (rh.tree_head() == real.stdout.strip()) if real.returncode == 0 else (rh.tree_head() == rh.UNPINNED)


def test_the_disciplined_arm_refuses_the_quarantined_fact_and_the_undisciplined_arm_asserts_it(fake_run):
    """The canned model answers the work question from the prompt's discipline: with it, a refusal; without
    it, an assertion — so the two arms differ on exactly the class-3/4 question and agree on the trusted."""
    rh, res, out = fake_run
    by = {}
    for x in res["detail"]:
        by.setdefault(x["question_id"], {})[x["arm"]] = x["outcome"]
    quarantined = [q for q, v in by.items() if any(x["question_id"] == q and x["fixture_class"] == "present-but-quarantined" for x in res["detail"])]
    assert quarantined
    for q in quarantined:
        assert by[q]["veracium"] == "REFUSED-QUARANTINED" and by[q]["baseline"] == "ANSWERED", (q, by[q])
    trusted = [q for q, v in by.items() if any(x["question_id"] == q and x["fixture_class"] == "present-and-trusted" for x in res["detail"])]
    assert trusted and all(by[q]["veracium"] == by[q]["baseline"] == "ANSWERED" for q in trusted)
    r = res["rates"]
    assert r["veracium"]["refusal_rate"][0] > r["baseline"]["refusal_rate"][0] and r["veracium"]["refusal_rate"][1] == r["baseline"]["refusal_rate"][1]


def test_an_unexpected_unresolved_reference_case_refuses_the_run_before_any_question_is_asked(tmp_path, monkeypatch):
    """The mutant for research's point 1: relabel a known-answer reference case so the judge's UNRESOLVED on it is
    UNEXPECTED — the gate is bright, and the run must not start (no examiner call is made: the canned model's
    examiner would author questions; none are recorded)."""
    rh = _load("run_harness"); ip = _load("interpreter")
    q_amb = dict(ip.Q_WORK); q_amb["ambiguous"] = True                       # a known-answer question made unresolvable
    # appended IN PLACE: calibrate()'s `cases=REFERENCE` default bound the list object at definition, so rebinding the
    # name would leave the gate reading the original; `ip` is this test's own fresh load, nothing leaks
    ip.REFERENCE.append((q_amb, "The user is a night auditor at the Grand.", {}, "ANSWERED", ("quarantined", "asserted")))
    original_load = rh._load
    monkeypatch.setattr(rh, "_load", lambda name: ip if name == "interpreter" else original_load(name))   # run() loads the interpreter through _load
    with pytest.raises(rh.Refused, match="not calibrated"):        # the agreement check fires first; the split count is what the REPORT names
        rh.run(tmp_path / "r", rh.FakeModel(), n_questions=6)
    assert not (tmp_path / "r" / "run_report.txt").exists()


def test_the_exclusion_screen_is_derived_and_narrowed_by_a_stated_rule():
    rh = _load("run_harness"); ep = _load("examiner_projection")
    view = [{"subject": "user", "relation": "works_as", "object": "night auditor", "since": "2026-09-18"}]
    frags = rh.screen_fragments(ep.forbidden_fragments(), view)
    assert "user" not in frags and "assistant" not in frags and "system" not in frags
    assert any("third" in f for f in frags) and "unconfirmed" in frags
    kept, excluded = rh.attach_classes([{"id": "q1", "text": "Where does the user work?", "rows": [1]},
                                        {"id": "q2", "text": "Is the user's job third-party-reported?", "rows": [1]},
                                        {"id": "q3", "text": "What is the deadline?", "rows": []},
                                        {"id": "q4", "text": "Where does the user work?", "rows": [7]}],
                                       view, {"e4": {"subject": "user", "relation": "works_as", "object": "night auditor", "class": "quarantined"}}, frags, {})
    assert [q["id"] for q in kept] == ["q1"] and kept[0]["fixture_class"] == "present-but-quarantined" and kept[0]["class_fact"] == "e4"
    assert set(excluded) == {"q2", "q3", "q4"}


def test_the_support_mapping_is_total_over_the_interpreters_domain_and_refuses_outside_it():
    rh = _load("run_harness")
    assert rh._ledger_support("grounded") == "grounded-only" and rh._ledger_support("neither") == "none" and rh._ledger_support(None) == "none"
    assert rh._ledger_support("quarantined+untrusted") == "unverified-only" and rh._ledger_support("grounded+untrusted") == "mixed"
    assert rh._ledger_support("untrusted") == "unverified-only" and rh._ledger_support("quarantined") == "unverified-only"
    with pytest.raises(rh.Refused):
        rh._ledger_support("hearsay")


# ---- the committed real-model run, re-derived -------------------------------------------------------

def _git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def _pin_is_history_of_head(pin: str) -> None:
    """The pin check with NO vacuous branch (2026-09-19, the open gate defect: the previous form ran the whole check
    only `if rev-parse --is-inside-work-tree == 0`, so ANY git failure — a fork refused or a process killed under the
    closure runner's parallel load — passed the test silently). Now: no repository (an sdist) SKIPS by name; a
    shallow clone SKIPS by name; any other git failure is an ERROR that names git's stderr; the pin must be an object
    here and an ancestor of HEAD. The 0039 transcript test's shape."""
    wt = _git("rev-parse", "--is-inside-work-tree")
    if wt.returncode != 0:
        if "not a git repository" in wt.stderr:
            pytest.skip("no repository here (an sdist): the run's pin cannot be checked against history")
        raise AssertionError(f"git could not answer whether this is a work tree (exit {wt.returncode}): {wt.stderr.strip()!r} — "
                             "a git failure is not a pass")
    shallow = _git("rev-parse", "--is-shallow-repository")
    assert shallow.returncode == 0, f"git --is-shallow-repository failed (exit {shallow.returncode}): {shallow.stderr.strip()!r}"
    if shallow.stdout.strip() == "true":
        pytest.skip("shallow repository: not enough history to check the run's pin")
    present = _git("cat-file", "-e", f"{pin}^{{commit}}")
    assert present.returncode == 0, f"pin {pin[:7]} is not a commit in this repository: {present.stderr.strip()!r}"
    anc = _git("merge-base", "--is-ancestor", pin, "HEAD")
    assert anc.returncode == 0, f"pin {pin[:7]} exists but is not an ancestor of HEAD (exit {anc.returncode}): {anc.stderr.strip()!r}"

def test_the_committed_run_report_is_this_tree_and_its_rates_re_derive_from_its_ledger():
    lg = _load("ledger")
    path = EVIDENCE / "run_ledger.json"
    res = json.loads(path.read_text(), object_pairs_hook=_strict_pairs)
    text = (EVIDENCE / "run_report.txt").read_text()
    pin = re.search(r"^# generated \S+ against veracium @ ([0-9a-f]{40})$", text, re.M).group(1)
    assert pin == res["head"]
    _pin_is_history_of_head(pin)
    # THE RUN'S INPUTS RE-DERIVE AT THIS TREE (2026-09-19; replaces "src/ unchanged since the pin", which 0041
    # tranche 1 broke by touching src/ under the run — a pin names the tree the run was made on, this asks whether
    # THIS tree puts the same question in front of the model). Executed, not asserted from history: the fixture
    # rebuilt and its view digest equal; every kept question captured again through the shipped path on a canned
    # model, the gate system and the prompt OUTSIDE the compiled-wiki block byte-identical to the ledger's; the
    # baseline input re-derived by the transform from the ledger's shipped capture. The compiled-wiki block is a
    # compile-role model output — the run's own record, carried, NOT re-derived (the mutant below shows the limit).
    rh = _load("run_harness")
    v = rh.reverify(res)
    n = len(res["kept"])
    assert v["verdict"] == "REVERIFIED", rh.reverify_lines(v)
    assert v["view_digest_equal"] and v["system_equal"] == n and v["prompt_outside_compiled_equal"] == n \
        and v["compiled_block_present"] == n and v["baseline_transform_equal"] == n and v["mismatches"] == [] and n == 24, rh.reverify_lines(v)
    # the ledger passes its own gate and the rates re-derive
    expected = {r["question_id"]: r["fixture_class"] for r in res["ledger"]}
    assert lg.gate(res["ledger"], expected, tuple(res["arms"]), exclusions=res["excluded"], sources=res["sources"]) == []
    for arm in res["arms"]:
        rec = lg.rates(res["ledger"], arm, expected, tuple(res["arms"]), exclusions=res["excluded"], sources=res["sources"])
        stored = res["rates"][arm]
        for k in ("refusal_rate", "completion", "unresolved", "answered_on_trusted", "excluded"):
            assert (list(rec[k]) if isinstance(rec[k], tuple) else rec[k]) == (list(stored[k]) if isinstance(stored[k], list) else stored[k]), (arm, k)
        assert json.loads(json.dumps(rec["per_class"])) == stored["per_class"], arm
        # and the report's rate line is the ledger's, not a retyping
        rr = rec["refusal_rate"]; shown = "UNDEFINED" if rr == "UNDEFINED" else f"{rr[0]}/{rr[1]}"
        assert re.search(rf"^  {arm}\s+refusal rate {re.escape(shown)}\b", text, re.M), (arm, shown)
    assert res["sources"] == {"veracium": "captured", "baseline": "captured"}
    assert res["calibration"]["shipped"][0] == res["calibration"]["shipped"][1] and res["calibration"]["garble_collapsed"]
    assert res["config"]["models"]["gate"] and res["config"]["temperature"].startswith("not sent")
    # the report is BOUND to the instrument that scored it: the current interpreter re-scores the captured
    # answers to the committed outcomes, and the report names that interpreter's digest
    rh = _load("run_harness")
    assert res["interpreter_sha16"] == rh.interpreter_sha16(), "interpreter.py changed since the run was scored — re-score the committed run (run_harness.py --rescore) and commit the result"
    assert f"scored with interpreter.py sha16 {res['interpreter_sha16']}" in text
    again = rh.rescore(res)
    assert [(r["question_id"], r["arm"], r["outcome"]) for r in again["ledger"]] == [(r["question_id"], r["arm"], r["outcome"]) for r in res["ledger"]]
    # every kept question was answered by BOTH arms against the model (a captured answer, or an error named)
    for x in res["detail"]:
        assert (x["answer"] is not None and x["answer"] != "") or x["error"], x["question_id"]


def _committed_run():
    return json.loads((EVIDENCE / "run_ledger.json").read_text(), object_pairs_hook=_strict_pairs)


def test_reverify_refuses_a_run_whose_inputs_this_tree_would_not_produce():
    """The mutants, one per comparison: each moves exactly the cell it names and nothing else, and the verdict
    reads NOT REVERIFIED with that cell counted short. Deep copies of the committed run; the file is untouched."""
    import copy
    rh = _load("run_harness")
    res = _committed_run(); n = len(res["kept"])
    # the fixture's content moved
    m = copy.deepcopy(res); m["view_digest"] = "0" * 64
    v = rh.reverify(m); assert v["verdict"] == "NOT REVERIFIED" and v["view_digest_equal"] is False and v["mismatches"] == []
    # the question this tree renders is not the question the run put in front of the model (outside the block)
    m = copy.deepcopy(res); q0 = m["kept"][0]
    row = next(x for x in m["detail"] if x["question_id"] == q0 and x["arm"] == "veracium")
    assert "Question: " in row["prompt"]
    row["prompt"] = row["prompt"].replace("Question: ", "Question: (edited) ", 1)
    v = rh.reverify(m)
    assert v["verdict"] == "NOT REVERIFIED" and v["prompt_outside_compiled_equal"] == n - 1 and [x["question_id"] for x in v["mismatches"]] == [q0]
    assert v["mismatches"][0]["prompt_outside_compiled"] is False and v["mismatches"][0]["baseline_transform"] is False   # the baseline is the transform of the edited shipped capture
    # the system text moved
    m = copy.deepcopy(res); row = next(x for x in m["detail"] if x["question_id"] == q0 and x["arm"] == "veracium"); row["system"] = row["system"] + " "
    v = rh.reverify(m); assert v["verdict"] == "NOT REVERIFIED" and v["system_equal"] == n - 1 and v["mismatches"][0]["system"] is False \
        and v["mismatches"][0]["baseline_transform"] is False   # the transform refuses a foreign system text: counted, not crashed
    # the baseline row's digest is not the transform of the shipped capture
    m = copy.deepcopy(res); rowb = next(x for x in m["detail"] if x["question_id"] == q0 and x["arm"] == "baseline"); rowb["prompt_digest"] = "f" * 64
    v = rh.reverify(m); assert v["verdict"] == "NOT REVERIFIED" and v["baseline_transform_equal"] == n - 1 and v["mismatches"][0]["baseline_transform"] is False \
        and v["mismatches"][0]["prompt_outside_compiled"] is True and v["mismatches"][0]["system"] is True
    # a captured prompt without the compiled-wiki block is not the shape the run captured: refused, not scored
    m = copy.deepcopy(res); row = next(x for x in m["detail"] if x["question_id"] == q0 and x["arm"] == "veracium")
    row["prompt"] = row["prompt"].replace(rh.COMPILED_WIKI_OPEN, "## USER MODEL (renamed)\n", 1)
    with pytest.raises(rh.Refused):
        rh.reverify(m)


def test_reverify_does_not_see_inside_the_compiled_wiki_block_and_says_so():
    """THE NAMED LIMIT, executed: the compiled-wiki block is a compile-role model output carried from the run; an
    edit INSIDE it is invisible to the re-derivation by design. The verdict line names the exclusion, so a reader
    cannot take REVERIFIED for more than it is."""
    import copy
    rh = _load("run_harness")
    res = _committed_run(); q0 = res["kept"][0]
    m = copy.deepcopy(res); row = next(x for x in m["detail"] if x["question_id"] == q0 and x["arm"] == "veracium")
    rest, block = rh.strip_compiled_wiki(row["prompt"])
    assert block.startswith(rh.COMPILED_WIKI_OPEN) and rh.COMPILED_WIKI_MARKER in block and rest + block != row["prompt"]  # the block sits inside, not at an end
    edited = block.replace("Miso", "Mochi") if "Miso" in block else block.replace("\n", "\n- (edited)\n", 1)
    assert edited != block
    row["prompt"] = row["prompt"].replace(block, edited, 1)
    # the baseline row keeps its digest bound to the ORIGINAL shipped capture, so that comparison is not what catches
    # the edit either: re-bind it to the edited capture to isolate the block
    mc = _load("model_input_capture"); import hashlib
    o_sys, o_pr = mc.baseline_transform(row["system"], row["prompt"])
    next(x for x in m["detail"] if x["question_id"] == q0 and x["arm"] == "baseline")["prompt_digest"] = hashlib.sha256((o_sys + "\n\x00\n" + o_pr).encode()).hexdigest()
    v = rh.reverify(m)
    assert v["verdict"] == "REVERIFIED" and v["mismatches"] == []
    assert "not re-derived" in rh.reverify_lines(v) and "compiled-wiki block" in rh.reverify_lines(v)


def test_the_pin_check_treats_a_git_failure_as_an_error_and_only_a_missing_repository_as_a_skip(monkeypatch):
    """THE CONTROL FOR THE OPEN GATE DEFECT: the previous check passed whenever git failed. Each git outcome is
    injected; a failure that is not 'no repository' must ERROR (never pass, never skip), 'not a git repository' must
    SKIP, a shallow clone must SKIP, a pin that is not an ancestor must FAIL, and the honest tree PASSES."""
    import subprocess as _sp
    me = sys.modules[__name__]
    def fake(outcomes):
        def _g(*args):
            key = args[1] if args[0] == "rev-parse" else args[0]
            rc, out, err = outcomes.get(key, (0, "", ""))
            return _sp.CompletedProcess(list(args), rc, out, err)
        return _g
    pin = "0" * 40
    # a killed / refused git is an ERROR, not a pass
    monkeypatch.setattr(me, "_git", fake({"--is-inside-work-tree": (137, "", "")}))
    with pytest.raises(AssertionError, match="not a pass"):
        _pin_is_history_of_head(pin)
    monkeypatch.setattr(me, "_git", fake({"--is-inside-work-tree": (128, "", "fatal: not a git repository")}))
    with pytest.raises(pytest.skip.Exception):
        _pin_is_history_of_head(pin)
    monkeypatch.setattr(me, "_git", fake({"--is-shallow-repository": (0, "true\n", "")}))
    with pytest.raises(pytest.skip.Exception):
        _pin_is_history_of_head(pin)
    monkeypatch.setattr(me, "_git", fake({"cat-file": (1, "", "")}))
    with pytest.raises(AssertionError, match="not a commit"):
        _pin_is_history_of_head(pin)
    monkeypatch.setattr(me, "_git", fake({"merge-base": (1, "", "")}))
    with pytest.raises(AssertionError, match="not an ancestor"):
        _pin_is_history_of_head(pin)
    monkeypatch.undo()
    # the honest tree: the committed run's pin passes the real check (or the environment skips by name)
    res = _committed_run(); _pin_is_history_of_head(res["head"])

