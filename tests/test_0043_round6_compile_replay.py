"""specs/0043 round 6 — the round-5 verdict's Q3: "capture and compare the full compiler invocation/configuration, then
replay its stored output through the current downstream seam".

reverify used to compare the gate prompt OUTSIDE the compiled-wiki block and only CARRY the block (a compile-role model
output). Now (research's G1 decision, dev's injection point) it also replays the run's STORED compile output at the
compile-role call (ReplayCompile) and compares the COMPLETE gate prompt byte for byte, and its verdict is SPLIT:
`downstream` (that replay, plus every earlier cell) and `compiler_stage` (the recorded compile invocation compared with this
tree's, or HISTORICAL by name for a run that recorded none). Never one undivided REVERIFIED.

The shipped wrapping (strip, sanitize, normalise, the marker with RECOMPUTED counts) is a FIXED POINT on the stored body,
which is what makes the comparison exact; the controls below prove the replay is what feeds the prompt.
"""
import copy
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"cr_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, ev = _load("run_harness"), _load("examiner_view")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))


def _rebind(row):
    row["prompt_digest"] = rh.capture_digest(row["system"], row["prompt"])


def test_the_committed_run_downstream_reverifies_with_no_carve_out_and_its_compiler_stage_is_historical():
    v = rh.reverify(copy.deepcopy(LEDGER))
    n = len(LEDGER["kept"])
    assert v["prompt_complete_equal"] == n and v["downstream"] == "REVERIFIED", rh.reverify_lines(v)
    assert v["compiler_stage"] == "HISTORICAL" and "not recorded at the run's pin" in v["compiler_stage_reason"]
    assert v["distinct_stored_bodies"] == 1 and v["compile_calls"] == 1      # one compile per store, as in the run
    assert "REVERIFIED;" not in v["verdict"].split("downstream")[0]          # the verdict names both halves, never one
    assert v["verdict"].startswith("downstream REVERIFIED; compiler stage HISTORICAL")


def test_the_replay_is_what_feeds_the_prompt_one_byte_in_the_stored_body_shows_in_the_gate_prompt(tmp_path):
    """Research's negative: a regenerated canned body would make the edit invisible."""
    old = next(x for x in LEDGER["detail"] if x["arm"] == "veracium")
    body = rh.stored_compile_body(old["prompt"])
    i = body.index("Porto")
    edited = body[:i] + "Q" + body[i + 1:]
    db = tmp_path / "f.db"; st = ev.fixture_store(str(db)); st.close()
    cap = rh.capture_shipped(str(db), old["question"], rh.ReplayCompile(rh.FakeModel(), edited))
    assert edited.split("\n")[0] in cap["prompt"] and cap["prompt"] != old["prompt"]
    assert "Qorto" in cap["prompt"] and "Qorto" not in old["prompt"]


def test_a_changed_drop_count_in_the_stored_block_is_caught_by_the_recomputed_marker():
    """The marker's counts are RECOMPUTED by the current code from the compile's inputs; a stored block whose marker
    claims other counts (bytes re-bound to its digest, so only the replay can see it) reads NOT REVERIFIED."""
    res = copy.deepcopy(LEDGER)
    row = next(x for x in res["detail"] if x["arm"] == "veracium")
    j = row["prompt"].index(rh.COMPILED_WIKI_MARKER)
    line_end = row["prompt"].index("\n", j)
    marker = row["prompt"][j:line_end]
    assert "+0 facts" in marker, marker
    row["prompt"] = row["prompt"][:j] + marker.replace("+0 facts", "+7 facts") + row["prompt"][line_end:]
    _rebind(row)
    v = rh.reverify(res)
    assert v["downstream"] == "NOT REVERIFIED" and v["prompt_complete_equal"] == len(res["kept"]) - 1, rh.reverify_lines(v)
    assert v["prompt_outside_compiled_equal"] == len(res["kept"])        # the old carve-out could not see it


def test_an_altered_downstream_render_is_caught(monkeypatch):
    """A change to the shipped wrapping after the model call (here: the marker appender) breaks the fixed point."""
    from veracium import budgets
    real = budgets.append_compile_marker
    monkeypatch.setattr(budgets, "append_compile_marker", lambda body, f, e: real(body, f, e) + " ")
    v = rh.reverify(copy.deepcopy(LEDGER))
    assert v["downstream"] == "NOT REVERIFIED" and v["prompt_complete_equal"] < len(LEDGER["kept"]), rh.reverify_lines(v)


def test_a_new_run_records_its_compile_invocation_and_its_compiler_stage_reverifies(tmp_path):
    res = rh.run(tmp_path / "run", rh.FakeModel(), request_manifest="generated")
    ci = res["compile_invocation"]
    assert ci and ci["system"] and ci["prompt"] and ci["digest"] == rh.capture_digest(ci["system"], ci["prompt"])
    v = rh.reverify(copy.deepcopy(res))
    assert v["compiler_stage"] == "REVERIFIED" and v["downstream"] == "REVERIFIED", rh.reverify_lines(v)
    bad = copy.deepcopy(res); bad["compile_invocation"]["digest"] = "0" * 64
    assert rh.reverify(bad)["compiler_stage"] == "NOT REVERIFIED"
    none = copy.deepcopy(res); none["compile_invocation"] = None
    assert rh.reverify(none)["compiler_stage"] == "HISTORICAL"


def test_the_cli_exit_follows_both_halves(tmp_path, monkeypatch):
    """0 when downstream is REVERIFIED and the compiler stage is not NOT REVERIFIED (HISTORICAL passes, by name)."""
    import subprocess, sys
    p = tmp_path / "ledger.json"; p.write_text(json.dumps(LEDGER))
    r = subprocess.run([sys.executable, str(EVIDENCE / "run_harness.py"), "--reverify", str(p)], capture_output=True, text=True,
                       cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")})
    assert r.returncode == 0 and "compiler stage HISTORICAL" in r.stdout, (r.returncode, r.stdout[-400:], r.stderr[-400:])


def test_rows_carrying_different_compile_outputs_read_not_reverified_with_the_cause_stated():
    """Research's cell: two rows with DIFFERENT bodies, each consistently rebound to its digest. One compile per store
    cannot have produced both, so downstream refuses with that cause, not with unexplained row mismatches."""
    res = copy.deepcopy(LEDGER)
    row = [x for x in res["detail"] if x["arm"] == "veracium"][3]
    rest, block = rh.strip_compiled_wiki(row["prompt"])
    row["prompt"] = row["prompt"].replace(block, block.replace("Miso", "Mochi") if "Miso" in block else block.replace("\n", "\n- x\n", 1), 1)
    _rebind(row)
    v = rh.reverify(res)
    assert v["distinct_stored_bodies"] == 2 and v["downstream"] == "NOT REVERIFIED", rh.reverify_lines(v)
    assert "the run's rows carry 2 compile outputs; the replay models one compile per store" in v["verdict"]
