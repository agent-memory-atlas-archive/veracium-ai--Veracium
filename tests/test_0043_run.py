"""specs/0043 tranche 2 — THE RUN, bound: the pipeline end to end on a canned model (no spend), and the
committed real-model report re-derived from its own ledger.

The pipeline test drives `run_harness.run` with `FakeModel`: the blind examiner authors from the view
alone, the classes attach after authorship, a non-blind question is EXCLUDED AND COUNTED, both arms are
captured (the baseline equal to the oracle), every row lands in one of the six outcomes, the ledger's
six checks pass with both sources `captured`, and the rates carry their denominators with `absent` NOT
PRESENTED. The report test reads `run_ledger.json` (the committed real run), re-runs the ledger gate
and recomputes every rate from the rows, and asserts the report's figures are those — a measured
artifact re-derived, never quoted — with the pin an ancestor of HEAD and src/ unchanged since.
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
    assert re.search(r"^# generated \S+ against veracium @ [0-9a-f]{40}$", text, re.M)
    assert "fixture store digest (as built): " in text and "temperature" in text and "EXCLUDED (INV-6, counted)" in text


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


def test_the_committed_run_report_is_this_tree_and_its_rates_re_derive_from_its_ledger():
    lg = _load("ledger")
    path = EVIDENCE / "run_ledger.json"
    res = json.loads(path.read_text(), object_pairs_hook=_strict_pairs)
    text = (EVIDENCE / "run_report.txt").read_text()
    pin = re.search(r"^# generated \S+ against veracium @ ([0-9a-f]{40})$", text, re.M).group(1)
    assert pin == res["head"]
    if _git("rev-parse", "--is-inside-work-tree").returncode == 0:
        anc = _git("merge-base", "--is-ancestor", pin, "HEAD")
        if anc.returncode == 128:
            pytest.skip("shallow repository: the run's pin cannot be checked against history")
        assert anc.returncode == 0, f"pin {pin[:7]} is not an ancestor of HEAD"
        moved = _git("diff", "--name-only", pin, "HEAD", "--", "src/").stdout.split()
        assert moved == [], f"src/ changed since the run's pin: {moved} — re-run the harness and re-pin"
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
