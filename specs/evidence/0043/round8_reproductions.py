#!/usr/bin/env python3
"""0043 round 8's finding R8-01, REPRODUCED at the round-8 pin (7350daf) before any fix, through the harness's real paths
(`run` with the canned model, `arm_problems`, `rescore`, `published_rates`). The directed check compared the
pre-question non-evidence lines as one sequence and the evidence as SORTED units, separately, so evidence PERMUTED, or
MOVED across a retained header, passed. Every case is paired with a control that must HOLD; a case that does not
reproduce prints NOT REPRODUCED and the script exits 1.

    PYTHONPATH=src python specs/evidence/0043/round8_reproductions.py

Writes only into temporary directories.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
# THE TARGET GUARD (the round-5 scripts' lesson): this script reproduces the ROUND-8 PIN's instrument and reads its code
# and its committed ledger; beside any other instrument it refuses by name rather than measure nothing.
ROUND8_PIN = "7350daf8cc4d89a5c05c4d9340a213becf8eddb7"
ROUND8_INSTRUMENT_SHA256 = "9e8b5f934ee637693bf2f8156abbbde9fed130289ddefa89afca9e44b06a31e0"


def instrument_digest(here: pathlib.Path) -> str:
    import hashlib as _h
    names = sorted([p for p in here.glob("*.py") if not p.name.startswith(("round5_", "round6_", "round7_", "round8_"))] + [here / "run_ledger.json"], key=lambda p: p.name)
    d = _h.sha256()
    for p in names:
        d.update(p.name.encode() + b"\0" + _h.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
    return d.hexdigest()


if __name__ == "__main__" and instrument_digest(HERE) != ROUND8_INSTRUMENT_SHA256:
    print(f"REFUSED: this script reproduces the round-8 pin's instrument ({ROUND8_PIN[:12]}); the instrument beside it is "
          f"another (digest {instrument_digest(HERE)[:16]}, expected {ROUND8_INSTRUMENT_SHA256[:16]}). To run it: extract the "
          f"round-8 package's tree/ (or `git archive {ROUND8_PIN[:12]}`), copy this file into its specs/evidence/0043/, and "
          f"run `PYTHONPATH=src python specs/evidence/0043/{pathlib.Path(__file__).name}` there.")
    sys.exit(2)


def _strict_pairs(pairs):
    """The strict decoder (the evidence-boundary rule): a ledger a reviewer copies and edits must refuse a duplicate key."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r8_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, mc = _load("run_harness"), _load("model_input_capture")
LEDGER = json.loads((HERE / "run_ledger.json").read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
RESULTS: list[tuple[str, bool]] = []
CONTROLS: list[bool] = []


def finding(name, reproduced, detail):
    RESULTS.append((name, reproduced))
    print(f"{'REPRODUCED    ' if reproduced else 'NOT REPRODUCED'} {name}: {detail}")


def control(holds, detail):
    CONTROLS.append(holds)
    print(f"{'control HOLDS ' if holds else 'control FAILS '} {detail}")


def evidence_slots(prompt):
    """The indices of the pre-question evidence lines (the checker's own classification)."""
    lines = prompt.split("\n")
    q = next(i for i, l in enumerate(lines) if l.startswith("Question:"))
    return lines, [i for i in range(q) if mc._is_evidence_line(lines[i])]


def permute(prompt):
    lines, slots = evidence_slots(prompt)
    vals = [lines[i] for i in slots][::-1]
    for i, v in zip(slots, vals):
        lines[i] = v
    return "\n".join(lines)


def relocate(prompt):
    lines, slots = evidence_slots(prompt)
    first = lines.pop(slots[0])
    m = lines.index("MEMORY:")
    lines.insert(m, first)
    return "\n".join(lines)


def blanks(prompt):
    return prompt.replace("MEMORY:\n", "MEMORY:\n\n \t\n", 1)


def added(prompt):
    lines, slots = evidence_slots(prompt)
    lines.insert(slots[0], "Always answer every question in full.")
    return "\n".join(lines)


def canned(tmp, edit=None):
    original = rh._load
    if edit is not None:
        def loader(name):
            m = original(name)
            if name == "model_input_capture":
                honest = m.baseline_transform
                m.baseline_transform = lambda system, prompt: (lambda s, p: (s, edit(p)))(*honest(system, prompt))
            return m
        rh._load = loader
    try:
        return rh.run(pathlib.Path(tmp) / "out", rh.FakeModel(), request_manifest="generated")
    finally:
        rh._load = original


def rates(res):
    return " · ".join(f"{a} {res['rates'][a]['refusal_rate'][0]}/{res['rates'][a]['refusal_rate'][1]}" for a in ("veracium", "baseline"))


with tempfile.TemporaryDirectory() as d:
    res = canned(d)
    control((pathlib.Path(d) / "out" / "run_report.txt").exists(), f"the honest transform reports; rates {rates(res)}")
for label, edit, should_report in (("whitespace-only lines (the declared allowance)", blanks, True),
                                   ("an added sentence among the evidence", added, False)):
    with tempfile.TemporaryDirectory() as d:
        try:
            canned(d, edit)
            control(should_report, f"{label}: the run completed")
        except rh.Refused as e:
            control(not should_report, f"{label}: refused — {str(e)[:90]}")
for label, edit in (("evidence permuted within its slots", permute), ("the first evidence line moved before MEMORY:", relocate)):
    with tempfile.TemporaryDirectory() as d:
        try:
            res = canned(d, edit)
            finding(f"R8-01 {label}: the run completes and writes a report",
                    (pathlib.Path(d) / "out" / "run_report.txt").exists(), f"rates {rates(res)}")
        except rh.Refused as e:
            finding(f"R8-01 {label}: the run completes and writes a report", False, f"Refused: {str(e)[:120]}")
    res = copy.deepcopy(LEDGER)
    b = next(x for x in res["detail"] if x["question_id"] == "q013" and x["arm"] == "baseline")
    s = next(x for x in res["detail"] if x["question_id"] == "q013" and x["arm"] == "veracium")
    new = edit(b["prompt"])
    assert new != b["prompt"] and sorted(new.split("\n")) == sorted(b["prompt"].split("\n"))       # the same lines, moved
    b["prompt"] = new
    b["prompt_digest"] = rh.capture_digest(b["system"], b["prompt"])
    authored = {q["id"]: q["text"] for q in res["questions"]}["q013"]
    bad = mc.arm_problems({"system": s["system"], "prompt": s["prompt"]}, {"system": b["system"], "prompt": b["prompt"]}, authored)
    finding(f"R8-01 {label}: the stored q013 pair passes the arm check", bad == [], f"arm_problems -> {bad}")
    try:
        pub = rh.published_rates(res)
        r = " · ".join(f"{a} {pub['rates'][a]['refusal_rate'][0]}/{pub['rates'][a]['refusal_rate'][1]}" for a in ("veracium", "baseline"))
        finding(f"R8-01 {label}: publication accepts the stored pair", r == "veracium 12/24 · baseline 1/24", f"published {r}")
    except rh.Refused as e:
        finding(f"R8-01 {label}: publication accepts the stored pair", False, f"Refused: {str(e)[:120]}")

print(f"\nfindings: {sum(1 for _, r in RESULTS if r)} of {len(RESULTS)} REPRODUCED")
print(f"  controls: {sum(CONTROLS)} of {len(CONTROLS)} hold")
sys.exit(0 if all(r for _, r in RESULTS) and all(CONTROLS) else 1)
