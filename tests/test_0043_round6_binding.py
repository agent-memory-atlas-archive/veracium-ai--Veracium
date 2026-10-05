"""specs/0043 round 6 — R5-05: `reverify` binds each arm's captured bytes to the digest the ledger declares for them.

Round 5 hashed the TRANSFORM of the shipped capture and compared it to the baseline row's stored digest field: the
baseline's own system and prompt were never hashed, so a baseline whose bytes were replaced and whose digest was kept
still read REVERIFIED (the verdict's `baseline_bytes_not_bound_to_digest`). And the compiled-wiki block check took the
block FROM the prompt and asked whether it was IN the prompt, which could not fail. Now each arm's (system, prompt) is
re-hashed and compared to its declared digest, the baseline comparison is between the ACTUAL captured pair and the
transform of the shipped one, and the block is carried in a capture its digest binds. Every cell mutates a deep copy
of the committed run ledger; the file is untouched. One kept question per cell keeps the canned re-capture short.
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
    spec = importlib.util.spec_from_file_location(f"r6b_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh = _load("run_harness")


def _one_question_run():
    """The committed run, narrowed to its first kept question (both arms' detail rows, its ledger rows)."""
    res = json.loads((EVIDENCE / "run_ledger.json").read_text(), object_pairs_hook=_strict_pairs)
    q0 = res["kept"][0]
    res["kept"] = [q0]
    res["detail"] = [x for x in res["detail"] if x["question_id"] == q0]
    return res, q0


def _row(res, arm):
    return next(x for x in res["detail"] if x["arm"] == arm)


def test_control_the_committed_capture_reverifies():
    """BEHAVIOUR, which held before this round too: the honest committed capture reads REVERIFIED."""
    res, _ = _one_question_run()
    v = rh.reverify(res)
    assert v["verdict"] == "REVERIFIED", rh.reverify_lines(v)


def test_the_verdict_counts_each_arms_binding():
    """REPRESENTATION (new this round): the verdict carries, and its line prints, how many captures of each arm were
    bound to their declared digest."""
    res, _ = _one_question_run()
    v = rh.reverify(res)
    assert v["shipped_bytes_bound"] == 1 and v["baseline_bytes_bound"] == 1
    assert "bound to its declared digest: shipped 1/1, baseline 1/1" in rh.reverify_lines(v)


@pytest.mark.parametrize("field", ["prompt", "system"])
def test_R5_05_a_baseline_whose_bytes_moved_and_digest_stayed_is_not_reverified(field):
    res, _ = _one_question_run()
    b = _row(res, "baseline")
    if field == "prompt":
        b["prompt"] = "All memory evidence has been removed\n\n" + b["prompt"][b["prompt"].index("Question:"):]
    else:
        b["system"] = b["system"] + " ALTERED"
    assert rh.capture_digest(b["system"], b["prompt"]) != b["prompt_digest"]   # the bytes no longer have their digest
    v = rh.reverify(res)
    assert v["verdict"] == "NOT REVERIFIED", rh.reverify_lines(v)


def test_R5_05_a_compiled_block_edited_consistently_but_with_its_shipped_digest_kept_is_not_reverified():
    """The round-5 compiled-block check could not fail. An edit inside the block, the baseline re-derived from the
    edited capture with its own digest (so the transform comparison agrees), and the SHIPPED digest kept: the shipped
    bytes no longer have their declared digest. Round 5 read this REVERIFIED."""
    mc = _load("model_input_capture")
    res, _ = _one_question_run()
    s = _row(res, "veracium")
    _rest, block = rh.strip_compiled_wiki(s["prompt"])
    s["prompt"] = s["prompt"].replace(block, block.replace("\n", "\n- (edited)\n", 1), 1)
    b = _row(res, "baseline")
    b["system"], b["prompt"] = mc.baseline_transform(s["system"], s["prompt"])
    b["prompt_digest"] = rh.capture_digest(b["system"], b["prompt"])
    v = rh.reverify(res)
    assert v["verdict"] == "NOT REVERIFIED", rh.reverify_lines(v)


def test_control_a_baseline_rebound_to_a_digest_that_is_not_the_transform_is_not_reverified():
    """CONTROL (held before this round): bytes and digest consistent with each other but NOT the transform of the
    shipped capture — refused, then by the digest comparison, now by the actual-pair comparison."""
    res, _ = _one_question_run()
    b = _row(res, "baseline")
    b["prompt"] = "All memory evidence has been removed\n\n" + b["prompt"][b["prompt"].index("Question:"):]
    b["prompt_digest"] = rh.capture_digest(b["system"], b["prompt"])
    v = rh.reverify(res)
    assert v["verdict"] == "NOT REVERIFIED", rh.reverify_lines(v)


def test_a_moved_baseline_is_reported_as_unbound():
    """REPRESENTATION: the mismatch names the binding that failed."""
    res, q0 = _one_question_run()
    b = _row(res, "baseline")
    b["prompt"] = "All memory evidence has been removed\n\n" + b["prompt"][b["prompt"].index("Question:"):]
    v = rh.reverify(res)
    assert v["baseline_bytes_bound"] == 0 and v["mismatches"][0]["question_id"] == q0 and v["mismatches"][0]["baseline_bytes_bound"] is False


def test_capture_digest_is_the_definition_the_capture_writers_use():
    """One definition: the digest the harness's capture writers record is capture_digest of the same bytes."""
    res, _ = _one_question_run()
    for x in res["detail"]:
        assert rh.capture_digest(x["system"], x["prompt"]) == x["prompt_digest"], x["arm"]
