"""specs/0043 — the round-6 verdict's R6-01: a PUBLISHED figure is scored by the run's own path, the two-seat label in
place of the reader's judgement of the answer and of nothing else.

Round 6's `published_rates` was a parallel path: it read a CACHED `support` from the row and called `per_fact_outcome`
directly, so (a) an unaccounted unit that the run's own path makes UNRESOLVED (`capture-disagrees-with-delivered`)
published as a resolved outcome with the totals unchanged, and (b) an edit to the cached support moved the published rate
(12/24 -> 11/24) with no evidence or label changed. Now `published_rates` and `rescore` share `_score`, and `interpret`
takes the labels through `mention_source`: the delivered accounting, support from the captured prompt and record, the
tie and the anomalies run unchanged, a STRUCTURAL cause survives into the published row, and only a READER cause is what
a label resolves. The report carries a published per-row table.
"""
import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r601_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, ip = _load("run_harness"), _load("interpreter")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))
STRAY = "drives: a red car (since 2026-09-18)"          # the verdict's unit: fact-shaped, delivered by no edge


def _with_stray(qid, arms=("veracium", "baseline")):
    res = copy.deepcopy(LEDGER)
    for x in res["detail"]:
        if x["question_id"] == qid and x["arm"] in arms:
            i = x["prompt"].index("\n\nQuestion:")
            x["prompt"] = x["prompt"][:i] + "\n" + STRAY + x["prompt"][i:]
            x["prompt_digest"] = rh.capture_digest(x["system"], x["prompt"])     # rebound: not a stale digest
    return res


def _pub(res):
    p = rh.published_rates(res)
    return {(r["question_id"], r["arm"]): r for r in p["rows"]}, {a: p["rates"][a] for a in ("veracium", "baseline")}


def test_control_the_unchanged_committed_run_publishes_12_of_24_and_1_of_24_with_every_row_resolved():
    rows, rates = _pub(copy.deepcopy(LEDGER))
    assert tuple(rates["veracium"]["refusal_rate"]) == (12, 24)
    assert tuple(rates["baseline"]["refusal_rate"]) == (1, 24) and rates["veracium"]["unresolved"] == rates["baseline"]["unresolved"] == 0
    assert len(rows) == 48 and all(r["cause"] is None and r["outcome"] != "UNRESOLVED" for r in rows.values())


def test_control_an_event_time_question_the_reader_leaves_to_the_labels_is_resolved_by_them():
    reader = {x["arm"]: (x["outcome"], x["cause"]) for x in LEDGER["detail"] if x["question_id"] == "q006"}
    assert reader == {"veracium": ("UNRESOLVED", "event-time-human-scored"), "baseline": ("UNRESOLVED", "event-time-human-scored")}
    rows, _ = _pub(copy.deepcopy(LEDGER))
    assert (rows[("q006", "veracium")]["outcome"], rows[("q006", "baseline")]["outcome"]) == ("REFUSED-ABSENT", "ANSWERED")


@pytest.mark.parametrize("qid, temporal", [("q006", True), ("q013", False)])
def test_R6_01_an_unaccounted_unit_stays_UNRESOLVED_in_the_published_row(qid, temporal):
    assert any(q["id"] == qid for q in LEDGER["questions"])
    rows, rates = _pub(_with_stray(qid))
    for arm in ("veracium", "baseline"):
        r = rows[(qid, arm)]
        assert (r["outcome"], r["cause"]) == ("UNRESOLVED", "capture-disagrees-with-delivered"), (qid, arm, r)
        assert rates[arm]["unresolved"] == 1, rates[arm]


@pytest.mark.parametrize("arm", ["veracium", "baseline"])
def test_R6_01_inconsistent_delivered_identities_refuse_publication_in_either_arm(arm):
    res = copy.deepcopy(LEDGER)
    x = next(d for d in res["detail"] if d["question_id"] == "q013" and d["arm"] == arm)
    x["delivered"] = x["delivered"][:-1]
    with pytest.raises(rh.Refused, match=rf"^q013/{arm}: the adjudication record's edges .* are not the delivered ids"):
        rh.published_rates(res)


def test_R6_01_an_edit_to_the_cached_support_cannot_move_the_published_rate():
    res = copy.deepcopy(LEDGER)
    x = next(d for d in res["detail"] if d["question_id"] == "q013" and d["arm"] == "veracium")
    assert x["facts"]["e4"]["support"] == "quarantined"
    x["facts"]["e4"]["support"] = "grounded"
    rows, rates = _pub(res)
    assert tuple(rates["veracium"]["refusal_rate"]) == (12, 24)
    assert rows[("q013", "veracium")]["support"] == "quarantined"      # derived from the captured prompt and record


def test_R6_01_the_report_publishes_the_unresolved_row_and_names_its_cause():
    text = rh.report(rh.rescore(_with_stray("q006")))
    pub = [l for l in text.splitlines() if "PUBLISHED refusal rate" in l]
    assert len(pub) == 2 and all("unresolved 1" in l for l in pub), pub
    rows = [l for l in text.splitlines() if l.startswith("  q006 ") and "capture-disagrees-with-delivered" in l]
    assert len(rows) == 2, rows


def test_R6_01_the_cli_rescore_publishes_the_unresolved_row(tmp_path):
    src = tmp_path / "ledger.json"; src.write_text(json.dumps(_with_stray("q013")))
    r = subprocess.run([sys.executable, str(EVIDENCE / "run_harness.py"), "--rescore", str(src), "--out", str(tmp_path / "out")],
                       capture_output=True, text=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert r.returncode == 0, r.stderr[-400:]
    text = (tmp_path / "out" / "run_report.txt").read_text(encoding="utf-8")
    assert sum("PUBLISHED refusal rate" in l and "unresolved 1" in l for l in text.splitlines()) == 2
    assert sum(l.startswith("  q013 ") and "UNRESOLVED" in l and "capture-disagrees-with-delivered" in l for l in text.splitlines()) == 2


def test_the_unresolved_causes_are_partitioned_closed_into_structural_and_reader():
    """A new cause fails here until it is placed; it never defaults to READER (which a label would silently resolve)."""
    s, r = set(ip.STRUCTURAL_CAUSES), set(ip.READER_CAUSES)
    assert not (s & r) and s | r == set(ip.UNRESOLVED_CAUSES) and len(ip.UNRESOLVED_CAUSES) == len(set(ip.UNRESOLVED_CAUSES))


def test_a_label_replaces_only_the_mention_and_a_class_fact_without_one_refuses():
    probe = _load("model_input_capture").run()
    P, REC = probe["shipped"]["prompt"], probe["record"]
    q = {"text": "Where do I live?", "facts": [ip.FACTS["city"]], "class_fact": "city", "class_set": ["city"]}
    answer = "I can't say where you live."                                  # the reader reads a withholding
    assert ip.interpret(q, P, REC, answer, {})["facts"]["city"]["mention"] == "withheld"
    r = ip.interpret(q, P, REC, answer, {}, mention_source={"city": "asserted"})
    assert r["outcome"] == "ANSWERED" and r["facts"]["city"]["support"] == ip.interpret(q, P, REC, answer, {})["facts"]["city"]["support"]
    for bad in ({}, {"city": "unrecognised"}):
        with pytest.raises(ValueError, match="needs a two-seat label"):
            ip.interpret(q, P, REC, answer, {}, mention_source=bad)


@pytest.mark.parametrize("reading", ["asserted", "withheld"])
def test_R6_01_nothing_published_rests_on_the_reader(monkeypatch, reading):
    """The reader and the labels agree on every non-event-time row of the committed run, so no row there can show whether
    a label was applied. Sabotage the reader inside the publication path (every mention read as `reading`, every event
    time as `reading`) in the SCORING: the published figures must not move, because the labels replace it for every
    requested fact. The calibration gate keeps an UNSABOTAGED reader (a fresh load, its own globals): the publication path
    keeps the run's calibration gate, so a reader broken on its reference cases would refuse publication, failing closed."""
    original = rh._load

    def loader(name):
        m = original(name)
        if name == "interpreter":
            honest = original("interpreter")
            m.calibrate, m.garble_control = honest.calibrate, honest.garble_control
            m.mention_from_answer = lambda *a, **k: reading
            m.event_time_reading = lambda *a, **k: (reading, "sabotaged")
        return m
    monkeypatch.setattr(rh, "_load", loader)
    rows, rates = _pub(copy.deepcopy(LEDGER))
    assert tuple(rates["veracium"]["refusal_rate"]) == (12, 24) and tuple(rates["baseline"]["refusal_rate"]) == (1, 24)
    assert rates["veracium"]["unresolved"] == rates["baseline"]["unresolved"] == 0
