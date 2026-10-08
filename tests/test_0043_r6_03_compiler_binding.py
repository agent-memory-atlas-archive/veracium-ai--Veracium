"""specs/0043 — the round-6 verdict's R6-03: the compiler stage binds the RECORDED invocation, then compares each field.

Round 6's compiler stage compared this tree's compile digest with the recorded DIGEST only: an edit to the recorded system
or prompt with its digest kept, or to the recorded model or token limit, read REVERIFIED (R5-05's defect, at the new
carrier). The shipped negative zeroed the digest itself, which cannot test whether the bytes are bound to it. Now
`run_harness.compiler_stage_status` binds the recorded system and prompt to their digest FIRST, then compares system,
prompt, model and max_tokens with this tree's, naming each mismatch; a field this tree cannot observe yields PARTIAL,
never REVERIFIED. Every negative here edits the RECORD (or the live configuration), not only the digest.
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
    spec = importlib.util.spec_from_file_location(f"r603_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh = _load("run_harness")


@pytest.fixture(scope="module")
def fresh(tmp_path_factory):
    res = rh.run(tmp_path_factory.mktemp("r603") / "out", rh.FakeModel(), request_manifest="generated")
    assert res["compile_invocation"] and res["compile_invocation"]["model"] == "fake" and res["compile_invocation"]["max_tokens"] == 0
    return res


def _stage(res, inner=None):
    v = rh.reverify(copy.deepcopy(res), inner)
    return v["compiler_stage"], v["compiler_stage_reason"], v["downstream"]


def test_control_an_unchanged_recorded_invocation_reverifies(fresh):
    stage, why, downstream = _stage(fresh)
    assert (stage, downstream) == ("REVERIFIED", "REVERIFIED") and "system, prompt, model and max_tokens" in why


@pytest.mark.parametrize("field", ["system", "prompt"])
def test_R6_03_recorded_bytes_edited_with_the_digest_kept_are_not_bound(fresh, field):
    res = copy.deepcopy(fresh)
    res["compile_invocation"][field] = (res["compile_invocation"][field] or "") + " EDITED"
    stage, why, downstream = _stage(res)
    assert stage == "NOT REVERIFIED" and "do not hash to its recorded digest" in why, why
    assert downstream == "REVERIFIED"                       # the stored output still replays: the two halves stay split


def test_R6_03_the_recorded_digest_edited_alone_is_not_bound(fresh):
    res = copy.deepcopy(fresh); res["compile_invocation"]["digest"] = "0" * 64
    stage, why, _ = _stage(res)
    assert stage == "NOT REVERIFIED" and "do not hash to its recorded digest" in why


def test_R6_03_recorded_bytes_edited_and_consistently_rebound_differ_from_this_tree(fresh):
    """Past the binding: a recorded system edited AND its digest recomputed is bound, and is not what this tree sends."""
    res = copy.deepcopy(fresh); ci = res["compile_invocation"]
    ci["system"] = (ci["system"] or "") + " EDITED"; ci["digest"] = rh.capture_digest(ci["system"], ci["prompt"])
    stage, why, _ = _stage(res)
    assert stage == "NOT REVERIFIED" and why.endswith("differs from the recorded one in: system"), why


@pytest.mark.parametrize("field, value", [("model", "another-model"), ("max_tokens", 1)])
def test_R6_03_a_recorded_configuration_field_edited_is_named(fresh, field, value):
    res = copy.deepcopy(fresh); res["compile_invocation"][field] = value
    stage, why, _ = _stage(res)
    assert stage == "NOT REVERIFIED" and why.endswith(f"differs from the recorded one in: {field}"), why


def test_R6_03_a_changed_live_configuration_is_named(fresh):
    class Other(rh.FakeModel):
        _models = {"compile": "another-model", "gate": "fake", "distill": "fake"}; _max_tokens = 4096
    stage, why, _ = _stage(fresh, Other())
    assert stage == "NOT REVERIFIED" and why.endswith("in: model, max_tokens"), why


def test_R6_03_a_live_token_limit_alone_changed_from_0_is_named(fresh):
    """0 is a value (research's point: `_max_tokens = 0` is falsy): recorded 0 against live 1 is a mismatch."""
    class OneMore(rh.FakeModel):
        _max_tokens = 1
    stage, why, _ = _stage(fresh, OneMore())
    assert stage == "NOT REVERIFIED" and why.endswith("in: max_tokens"), why


def test_R6_03_a_field_this_tree_cannot_observe_is_PARTIAL_never_REVERIFIED_and_names_its_side(fresh):
    class Silent(rh.FakeModel):
        _models = None; _max_tokens = None
    stage, why, _ = _stage(fresh, Silent())
    assert stage == "PARTIAL" and why.endswith("model (not observable in this tree), max_tokens (not observable in this tree)"), why
    res = copy.deepcopy(fresh); res["compile_invocation"]["model"] = None
    stage, why, _ = _stage(res)
    assert stage == "PARTIAL" and why.endswith("model (not recorded)"), why


def test_R6_03_a_mismatch_outranks_PARTIAL(fresh):
    class SilentModelOtherLimit(rh.FakeModel):
        _models = None; _max_tokens = 7
    stage, why, _ = _stage(fresh, SilentModelOtherLimit())
    assert stage == "NOT REVERIFIED" and why.endswith("in: max_tokens"), why


def test_R6_03_PARTIAL_exits_0_on_the_cli_like_HISTORICAL(fresh, tmp_path):
    res = copy.deepcopy(fresh); res["compile_invocation"]["max_tokens"] = None
    p = tmp_path / "ledger.json"; p.write_text(json.dumps(res))
    r = subprocess.run([sys.executable, str(EVIDENCE / "run_harness.py"), "--reverify", str(p)], capture_output=True, text=True,
                       cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert r.returncode == 0 and "compiler stage PARTIAL" in r.stdout and "max_tokens (not recorded)" in r.stdout, r.stdout[-300:]


def test_control_a_run_that_recorded_no_invocation_is_HISTORICAL(fresh):
    res = copy.deepcopy(fresh); res["compile_invocation"] = None
    assert _stage(res)[0] == "HISTORICAL"


@pytest.mark.parametrize("edit, code", [(None, 0), ("model", 1), ("system", 1)])
def test_R6_03_the_cli_exit_follows_the_compiler_stage(fresh, tmp_path, edit, code):
    res = copy.deepcopy(fresh)
    if edit == "model":
        res["compile_invocation"]["model"] = "another-model"
    elif edit == "system":
        res["compile_invocation"]["system"] = (res["compile_invocation"]["system"] or "") + " EDITED"
    p = tmp_path / "ledger.json"; p.write_text(json.dumps(res))
    r = subprocess.run([sys.executable, str(EVIDENCE / "run_harness.py"), "--reverify", str(p)], capture_output=True, text=True,
                       cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert r.returncode == code, (r.returncode, r.stdout[-300:], r.stderr[-300:])
