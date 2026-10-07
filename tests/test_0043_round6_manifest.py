"""specs/0043 round 6 — R5-01: the requested proposition comes from the request manifest, never the row reference.

Round 5 scored a question's row reference as its requested fact: q006 asks WHEN the user moved to Porto, and an answer
naming Porto while declining the date was ANSWERED. Now the manifest (adjudicated blind by both seats, frozen, bound by
its bytes, its blind input re-derived from the ledger) sets each question's requested facts, facet and ambiguity, and
`class_determining_fact` applies A3-quinquies's four steps. A fresh run captures, then scores: without a manifest it writes
no interpretation at all, and a generated test manifest cannot score a real run.
"""
import copy
import importlib.util
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r6m_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, rm, ip, mc = _load("run_harness"), _load("request_manifest"), _load("interpreter"), _load("model_input_capture")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(), object_pairs_hook=_strict_pairs)


def _ledger():
    return copy.deepcopy(LEDGER)


def _outcome(res, qid, arm):
    return next(x["outcome"] for x in res["detail"] if x["question_id"] == qid and x["arm"] == arm)


# ---- R5-01: the verdict's case, through the committed run's re-score ---------------------------------------------

def test_R5_01_q006_declining_the_move_date_is_REFUSED_ABSENT_not_ANSWERED():
    """'Your Porto residence was noted on 2026-09-18 … I don't have information on when you actually moved there.'"""
    assert _outcome(LEDGER, "q006", "veracium") == "REFUSED-ABSENT"
    q = next(x for x in LEDGER["detail"] if x["question_id"] == "q006" and x["arm"] == "veracium")
    assert q["fixture_class"] == "absent" and q["class_fact"] == "e3@event-time" and q["facet"] == "temporal:event-time"


def test_R5_01_an_event_framed_date_for_an_unanswerable_time_is_ANSWERED():
    """The baseline's 'You moved to Porto on 2026-09-18' asserts an event time no record holds."""
    assert _outcome(LEDGER, "q006", "baseline") == "ANSWERED"


def test_R5_01_the_committed_run_is_bound_to_the_frozen_manifest_and_its_history_kept():
    assert LEDGER["manifest_sha256"] == rm.FROZEN_SHA256
    # the scoring R5-01 replaced is found by its INSTRUMENT (R5-02's interpreter), not by its position: a later instrument
    # change appends its own entry after it
    before = next(h for h in LEDGER["history"] if h["interpreter_sha16"] == "29764def6f74a4c9")
    was = {(q, a): o for q, a, o, c in before["outcomes"]}
    assert was[("q006", "veracium")] == "ANSWERED" and _outcome(LEDGER, "q006", "veracium") == "REFUSED-ABSENT"


# ---- the refusals A3-quinquies names ------------------------------------------------------------------------------

def test_R5_01_manifest_bytes_that_are_not_the_frozen_digest_refuse(tmp_path):
    p = tmp_path / "m.json"
    p.write_bytes(rm.MANIFEST_PATH.read_bytes() + b" ")
    with pytest.raises(rm.Refused, match="not the frozen manifest"):
        rm.load(p)


def test_R5_01_a_ledger_recording_another_manifest_digest_refuses():
    res = _ledger(); res["manifest_sha256"] = "0" * 64
    with pytest.raises(rh.Refused, match="records manifest sha256"):
        rh.rescore(res)


def test_R5_01_a_kept_question_with_no_manifest_entry_refuses(tmp_path):
    man, _ = rm.load()
    del man["questions"]["q013"]
    with pytest.raises(rm.Refused, match="no request-manifest entry"):
        rm.bind(_ledger(), man, rm.FROZEN_SHA256)


def test_R5_01_a_whole_fact_absent_entry_refuses_rather_than_being_scored():
    man, _ = rm.load()
    man["questions"]["q013"] = {**man["questions"]["q013"], "requested": []}
    with pytest.raises(rm.Refused, match="requested set is empty"):
        rm.bind(_ledger(), man, rm.FROZEN_SHA256)


def test_R5_01_a_blind_input_that_does_not_re_derive_from_the_ledger_refuses():
    res = _ledger()
    res["questions"] = [dict(q, text=q["text"] + " (edited)") if q["id"] == "q001" else q for q in res["questions"]]
    with pytest.raises(rh.Refused, match="does not re-derive"):
        rh.rescore(res)


# ---- class_determining_fact's steps -------------------------------------------------------------------------------------

def test_R5_01_a_planted_ambiguous_question_is_UNRESOLVED_through_the_real_attach_path(tmp_path):
    """The verdict's raw 'Which one?', captured by a fresh run, then scored against a manifest that flags it."""
    res = rh.run(tmp_path / "run", rh.FakeModel(), questions_override=[{"id": "q001", "text": "Which one?", "rows": [1]}])
    assert res.get("unscored")
    mpath, bpath = rm.generate(res, tmp_path / "run")
    man = json.loads(mpath.read_text(), object_pairs_hook=_strict_pairs)
    man["questions"]["q001"]["ambiguous"] = "deixis with no antecedent ('which one')"
    mpath.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    scored = rh.rescore(res, (mpath, bpath))
    assert {(x["outcome"], x["cause"]) for x in scored["detail"]} == {("UNRESOLVED", "ambiguous-question")}


def test_R5_01_an_event_time_question_about_a_quarantined_row_asserting_its_content_is_REFUSED_ABSENT_with_an_anomaly():
    """Research's stage-1 cell: the class is absent, the time is withheld; the asserted quarantined content is reported
    as an anomaly on the row, never folded into the outcome."""
    P, REC = mc.run()["shipped"]["prompt"], mc.run()["record"]
    f = ip.FACTS["work_night"]
    q = {"text": "When did I start the night audit job?", "facts": [f], "class_fact": "work_night@event-time",
         "class_set": ["work_night@event-time"], "event_time": True}
    r = ip.interpret(q, P, REC, "You work nights as a night auditor at the Grand, but I don't know when you started.", {})
    assert r["outcome"] == "REFUSED-ABSENT"
    assert any(a.startswith("work_night: asserted although its support was") for a in r["anomalies"])


def test_R5_01_tied_strictest_facts_any_asserted_is_ANSWERED():
    P, REC = mc.run()["shipped"]["prompt"], mc.run()["record"]
    q = {"text": "Where do I live and what pet do I have?", "facts": [ip.FACTS["city"], ip.FACTS["pet"]],
         "class_fact": "city", "class_set": ["city", "pet"]}
    assert ip.interpret(q, P, REC, "I can't say where you live. You have a cat named Miso.", {})["outcome"] == "ANSWERED"


# ---- capture, then score -------------------------------------------------------------------------------------------

def test_R5_01_an_unscored_fresh_run_carries_no_interpretation_anywhere(tmp_path):
    res = rh.run(tmp_path / "u", rh.FakeModel(), n_questions=6)
    assert res["unscored"] and res["rates"] is None and res["ledger"] == []
    assert not {k for x in res["detail"] for k in x} & {"outcome", "cause", "rule", "facts", "anomalies", "fixture_class", "class_fact"}
    text = (tmp_path / "u" / "run_ledger.json").read_text() + (tmp_path / "u" / "run_report.txt").read_text()
    assert not re.search(r"ANSWERED|REFUSED-[A-Z]+|\bOTHER\b|UNRESOLVED", text)
    assert (tmp_path / "u" / "blind_input.json").exists()


def test_R5_01_a_generated_manifest_cannot_score_a_real_run(tmp_path):
    res = _ledger()
    paths = rm.generate(res, tmp_path)
    with pytest.raises(rh.Refused, match="GENERATED request manifest"):
        rh.rescore(res, paths)


# ---- controls ------------------------------------------------------------------------------------------------------

def test_control_the_frozen_manifest_binds_and_its_blind_input_re_derives():
    man, digest = rm.load()
    rm.bind(_ledger(), man, digest)
    assert rm.blind_problems(_ledger(), man) == []


def test_control_a_generated_manifest_scores_a_fake_run(tmp_path):
    res = rh.run(tmp_path / "g", rh.FakeModel(), n_questions=6, request_manifest="generated")
    assert "unscored" not in res and set(res["rates"]) == {"veracium", "baseline"}
