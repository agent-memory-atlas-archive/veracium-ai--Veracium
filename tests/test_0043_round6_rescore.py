"""specs/0043 round 6 — R5-04: rescore replays the run's validation path.

Round 5's `rescore` derived its denominator from the rows that survived and passed `delivered=None` to the interpreter:
removing both detail rows of q013 left the frozen kept set at 24 and the re-score declared completion 23/23; and an
unaccounted unit that the run's own path made UNRESOLVED (`capture-disagrees-with-delivered`) was re-scored as an
answer. Now rescore refuses unless the detail is EXACTLY the frozen (kept question, arm) set, rebuilds each row's
delivered identities from its adjudication record (bound to the ids the row recorded) and passes them as the run did,
and applies the run's calibration gate and R5-03's arm check. Every cell mutates a deep copy of the committed run
ledger; the file is untouched.
"""
import copy
import importlib.util
import json
import pathlib

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
    spec = importlib.util.spec_from_file_location(f"r6r_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, ip = _load("run_harness"), _load("interpreter")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(), object_pairs_hook=_strict_pairs)
STRAY = "drives: a red car (since 2026-09-18)"


def _ledger():
    return copy.deepcopy(LEDGER)


def test_R5_04_a_missing_pair_refuses_against_the_frozen_set(tmp_path):
    res = _ledger()
    res["detail"] = [x for x in res["detail"] if x["question_id"] != "q013"]
    with pytest.raises(rh.Refused, match="frozen"):
        rh.rescore(res)


def test_R5_04_a_single_missing_arm_refuses(tmp_path):
    res = _ledger()
    res["detail"] = [x for x in res["detail"] if not (x["question_id"] == "q013" and x["arm"] == "baseline")]
    with pytest.raises(rh.Refused, match="frozen"):
        rh.rescore(res)


def test_R5_04_an_unaccounted_unit_stays_UNRESOLVED_on_rescore(tmp_path):
    """The run's own path (delivered identities) and the re-score now agree: UNRESOLVED, the cause kept."""
    res = _ledger()
    q0 = res["kept"][0]
    for x in res["detail"]:
        if x["question_id"] == q0:
            x["prompt"] = x["prompt"].replace("\nQuestion:", f"\n{STRAY}\n\nQuestion:", 1)
    out = rh.rescore(res)
    got = {(x["arm"], x["outcome"], x["cause"]) for x in out["detail"] if x["question_id"] == q0}
    assert got == {("veracium", "UNRESOLVED", "capture-disagrees-with-delivered"),
                   ("baseline", "UNRESOLVED", "capture-disagrees-with-delivered")}


def test_a_record_that_is_not_the_recorded_delivered_set_refuses(tmp_path):
    res = _ledger()
    x = res["detail"][0]
    x["delivered"] = x["delivered"][:-1]
    with pytest.raises(rh.Refused, match="delivered ids"):
        rh.rescore(res)


def test_a_stored_pair_that_fails_the_arm_check_refuses(tmp_path):
    """R5-03's check, replayed on the stored captures: a baseline prompt that lost an evidence line."""
    res = _ledger()
    b = next(x for x in res["detail"] if x["arm"] == "baseline")
    line = next(l for l in b["prompt"].splitlines() if l.startswith("has_pet:") or l.startswith("located_at:") or l.startswith("prefers:"))
    b["prompt"] = b["prompt"].replace(line + "\n", "", 1)
    with pytest.raises(rh.Refused, match="not a valid comparison"):
        rh.rescore(res)


def test_control_the_unchanged_committed_run_rescores_to_its_outcomes_and_rates():
    out = rh.rescore(_ledger())
    assert [(x["question_id"], x["arm"], x["outcome"]) for x in out["detail"]] == \
           [(x["question_id"], x["arm"], x["outcome"]) for x in LEDGER["detail"]]
    assert json.loads(json.dumps(out["rates"]), object_pairs_hook=_strict_pairs) == LEDGER["rates"]
