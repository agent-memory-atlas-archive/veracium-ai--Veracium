"""specs/0043 — the PUBLISHED figures come from two-seat blind labels (held-out-4's and held-out-5's pre-committed fallbacks).

Both readers failed their pre-committed held-out lines (event time: coordination def44a2; the mention reader: c61e913), so
the reader is an AID and a run's published rates are derived from two-seat BLIND per-fact labels by the spec's rubric. A
spec sentence saying so beside a generated report that prints the reader's rates as plain RATES would let the wrong figure
be quoted (research's point, carrier-checked): the report now names the reader's block an aid and prints the published
block, derived here from the labels, beside it.
"""
import copy
import hashlib
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"pr_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh = _load("run_harness")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))


def test_the_labels_carried_are_the_frozen_merge_byte_for_byte():
    # coordination 0048103: the merge both seats froze (76 of 76 identical), sha256 recorded there
    assert hashlib.sha256(rh.LABELS_PATH.read_bytes()).hexdigest() == \
        "3125054ecb6a7947422da478136a2e218ba9ae9ba719f483245613a597c136cc"


def test_the_published_rates_are_the_labels_rates():
    """The figures the committed-run RESULT (coordination 3355fc4) derived by hand from the same labels."""
    pub = rh.published_rates(copy.deepcopy(LEDGER))
    want = {"veracium": (12, 24), "baseline": (1, 24)}
    for arm, (n, d) in want.items():
        r = pub["rates"][arm]
        assert tuple(r["refusal_rate"]) == (n, d) and tuple(r["completion"]) == (24, 24) and r["unresolved"] == 0, (arm, r)
        assert tuple(r["answered_on_trusted"]) == (11, 11)
    assert pub["key_sha256"] == "b2ec6953190e59829c38d5d0301383922380037f0693f6a48370ad0d6d8d3aa0"


def test_the_labelled_input_carried_is_the_one_labelled():
    labels = json.loads(rh.LABELS_PATH.read_text(encoding="utf-8"))
    assert hashlib.sha256(rh.LABELS_INPUT_PATH.read_bytes()).hexdigest() == labels["input_sha256"]


def test_the_items_re_derive_from_this_ledger_exactly():
    """The acceptance control for the answer binding: the extractor's items, rebuilt from today's ledger."""
    labelled = json.loads(rh.LABELS_INPUT_PATH.read_text(encoding="utf-8"))["items"]
    assert rh.label_items(copy.deepcopy(LEDGER), rh.LABELS_SEED) == labelled


def _answers(res):
    return {(x["question_id"], x["arm"]): x for x in res["detail"]}


def test_one_answer_changed_refuses_on_the_answers():
    res = copy.deepcopy(LEDGER); res["detail"][0]["answer"] = (res["detail"][0]["answer"] or "") + " "
    with pytest.raises(rh.Refused, match="do not re-derive the labelled input: item a\\d+ differs in its answer"):
        rh.published_rates(res)


def test_every_answer_changed_refuses_on_the_answers():
    res = copy.deepcopy(LEDGER)
    for x in res["detail"]:
        x["answer"] = "I don't know."
    with pytest.raises(rh.Refused, match="differs in its answer"):
        rh.published_rates(res)


def test_the_arms_answers_swapped_on_one_question_refuses_on_the_answers():
    res = copy.deepcopy(LEDGER); by = _answers(res)
    # a question whose two arms answered DIFFERENTLY (a swap of identical answers changes nothing, and is no control)
    q = next(q for q in res["kept"] if by[(q, "veracium")]["answer"] != by[(q, "baseline")]["answer"])
    a, b = by[(q, "veracium")], by[(q, "baseline")]
    a["answer"], b["answer"] = b["answer"], a["answer"]
    with pytest.raises(rh.Refused, match="differs in its answer"):
        rh.published_rates(res)


def test_missing_labels_for_the_committed_run_refuse(tmp_path):
    with pytest.raises(rh.Refused, match="labels are missing"):
        rh.published_rates(copy.deepcopy(LEDGER), labels_path=tmp_path / "absent.json")


def test_edited_labels_refuse_before_anything_is_published(tmp_path):
    """Research's probe: one label changed published baseline 2/24. The pin lives in the function, not only in a test."""
    bad = json.loads(rh.LABELS_PATH.read_text(encoding="utf-8"))
    item = next(k for k, v in bad["labels"].items() if "withheld" in v.values())
    fact = next(f for f, v in bad["labels"][item].items() if v == "withheld")
    bad["labels"][item][fact] = "asserted"
    p = tmp_path / "MERGED-LABELS.json"; p.write_text(json.dumps(bad, indent=1, sort_keys=True) + "\n")
    with pytest.raises(rh.Refused, match="not the frozen two-seat merge"):
        rh.published_rates(copy.deepcopy(LEDGER), labels_path=p)
    assert rh.LABELS_SHA256 == hashlib.sha256(rh.LABELS_PATH.read_bytes()).hexdigest()


def test_a_reordered_ledger_refuses_on_the_key():
    res = copy.deepcopy(LEDGER); res["detail"] = res["detail"][1:] + res["detail"][:1]
    with pytest.raises(rh.Refused, match="does not regenerate"):
        rh.published_rates(res)


def test_a_reordered_ledger_cannot_be_joined_to_the_labels():
    """The control the key exists for: the same answers in another order would map labels onto the wrong rows."""
    res = copy.deepcopy(LEDGER)
    res["detail"] = list(reversed(res["detail"]))
    with pytest.raises(rh.Refused, match="does not regenerate"):
        rh.published_rates(res)


def test_the_report_names_the_reader_an_aid_and_prints_the_published_rates():
    text = rh.report(copy.deepcopy(LEDGER))
    assert "READER RATES — an AID, NOT the published figure" in text
    assert "\n  veracium   PUBLISHED refusal rate 12/24 " in text and "\n  baseline   PUBLISHED refusal rate 1/24 " in text
    assert "\nRATES (" not in text                     # no unlabelled rates block survives
    assert (EVIDENCE / "run_report.txt").read_text(encoding="utf-8") == text   # the committed report is this tree's


def test_a_run_without_labels_says_it_has_no_published_figure():
    res = copy.deepcopy(LEDGER)
    res["manifest_sha256"] = "f" * 64                 # not the frozen manifest: a run nobody has labelled
    assert rh.published_rates(res) is None
    assert "PUBLISHED RATES — none" in rh.report(res)
