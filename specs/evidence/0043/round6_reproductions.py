#!/usr/bin/env python3
"""0043 round 6's three findings, REPRODUCED at the round-6 pin (be35c9b) before any fix, each through the harness's
real paths (`rescore`, `published_rates`, `report`, `run`, `reverify`, the CLI), over the committed run ledger where the
verdict names a committed row and over the canned model (no spend) where it names a construction. Every finding is
paired with a control that must HOLD; a finding that does not reproduce prints NOT REPRODUCED and the script exits 1.

    PYTHONPATH=src python specs/evidence/0043/round6_reproductions.py

Writes only into temporary directories.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
# THE TARGET GUARD (the round-5 scripts' lesson, 2026-10-08): this script reproduces the ROUND-6 PIN's instrument and
# reads its code and its committed ledger; beside any other instrument it refuses by name rather than measure nothing.
ROUND6_PIN = "be35c9b55cbba05ee6ff555da05e713a0f34f9c4"
ROUND6_INSTRUMENT_SHA256 = "006c1d0530e32ecdb9c7f3bf2d802c232b7f7145826b2b60cbf0e19825255f6b"


def instrument_digest(here: pathlib.Path) -> str:
    import hashlib as _h
    names = sorted([p for p in here.glob("*.py") if not p.name.startswith(("round5_", "round6_"))] + [here / "run_ledger.json"], key=lambda p: p.name)
    d = _h.sha256()
    for p in names:
        d.update(p.name.encode() + b"\0" + _h.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
    return d.hexdigest()


if __name__ == "__main__" and instrument_digest(HERE) != ROUND6_INSTRUMENT_SHA256:
    print(f"REFUSED: this script reproduces the round-6 pin's instrument ({ROUND6_PIN[:12]}); the instrument beside it is "
          f"another (digest {instrument_digest(HERE)[:16]}, expected {ROUND6_INSTRUMENT_SHA256[:16]}). To run it: extract the "
          f"round-6 package's tree/ (or `git archive {ROUND6_PIN[:12]}`), copy this file into its specs/evidence/0043/, and "
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
    spec = importlib.util.spec_from_file_location(f"r6_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh = _load("run_harness")
LEDGER = json.loads((HERE / "run_ledger.json").read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
RESULTS: list[tuple[str, bool]] = []
CONTROLS: list[bool] = []


def finding(name, reproduced, detail):
    RESULTS.append((name, reproduced))
    print(f"{'REPRODUCED    ' if reproduced else 'NOT REPRODUCED'} {name}: {detail}")


def control(holds, detail):
    CONTROLS.append(holds)
    print(f"{'control HOLDS ' if holds else 'control FAILS '} {detail}")


def published(res):
    p = rh.published_rates(res)
    rows = {(r["question_id"], r["arm"]): r["outcome"] for r in p["rows"]}
    rate = {a: p["rates"][a]["refusal_rate"] for a in ("veracium", "baseline")}
    return rows, rate, p


def rate_str(r):
    return " · ".join(f"{a} {r[a][0]}/{r[a][1]}" for a in ("veracium", "baseline"))


# ---- R6-01 (P1): the publication path bypasses capture integrity and reads cached support ---------------------------

rows0, rate0, _ = published(copy.deepcopy(LEDGER))
control(rate_str(rate0) == "veracium 12/24 · baseline 1/24", f"the unmodified committed ledger publishes {rate_str(rate0)}")

STRAY = "drives: a red car (since 2026-09-18)"
res = copy.deepcopy(LEDGER)
for x in res["detail"]:
    if x["question_id"] == "q006":
        i = x["prompt"].index("\n\nQuestion:")
        x["prompt"] = x["prompt"][:i] + "\n" + STRAY + x["prompt"][i:]
        x["prompt_digest"] = rh.capture_digest(x["system"], x["prompt"])          # rebound: not a stale digest
r = rh.rescore(res)
q006 = {x["arm"]: (x["outcome"], x.get("cause")) for x in r["detail"] if x["question_id"] == "q006"}
control(all(v == ("UNRESOLVED", "capture-disagrees-with-delivered") for v in q006.values()),
        f"rescore reads the stray unit in both q006 prompts: {q006}")
rows1, rate1, _ = published(r)
finding("R6-01a an unaccounted unit becomes a resolved published outcome",
        (rows1[("q006", "veracium")], rows1[("q006", "baseline")]) == ("REFUSED-ABSENT", "ANSWERED") and rate1 == rate0,
        f"published q006 veracium {rows1[('q006', 'veracium')]}, baseline {rows1[('q006', 'baseline')]}; rates {rate_str(rate1)}")
text = rh.report(r)
pub_line = next((l for l in text.splitlines() if "PUBLISHED refusal rate" in l and l.strip().startswith("veracium")), "")
finding("R6-01a' the report publishes it with no unresolved", "unresolved 0" in pub_line, pub_line.strip())

res = copy.deepcopy(LEDGER)
x = next(d for d in res["detail"] if d["question_id"] == "q013" and d["arm"] == "veracium")
before = x["facts"]["e4"]["support"]
x["facts"]["e4"]["support"] = "grounded"
rows2, rate2, _ = published(res)
finding("R6-01b an edit to the CACHED support moves the published rate",
        before == "quarantined" and rate2["veracium"] != rate0["veracium"],
        f"q013/veracium/e4 support {before} -> grounded: published {rate_str(rate2)}")

with tempfile.TemporaryDirectory() as d:
    src = pathlib.Path(d) / "ledger.json"
    res = copy.deepcopy(LEDGER)
    for x in res["detail"]:
        if x["question_id"] == "q006":
            i = x["prompt"].index("\n\nQuestion:")
            x["prompt"] = x["prompt"][:i] + "\n" + STRAY + x["prompt"][i:]
            x["prompt_digest"] = rh.capture_digest(x["system"], x["prompt"])
    src.write_text(json.dumps(res), encoding="utf-8")
    out = pathlib.Path(d) / "out"
    cp = subprocess.run([sys.executable, str(HERE / "run_harness.py"), "--rescore", str(src), "--out", str(out)],
                        capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(HERE.parents[2] / "src")})
    rep = (out / "run_report.txt").read_text(encoding="utf-8") if (out / "run_report.txt").exists() else ""
    line = next((l for l in rep.splitlines() if "PUBLISHED refusal rate" in l and l.strip().startswith("veracium")), "")
    finding("R6-01c the CLI rescore exits 0 and its report publishes the unaccounted row resolved",
            cp.returncode == 0 and "unresolved 0" in line, f"exit {cp.returncode}; {line.strip() or (cp.stderr or cp.stdout)[-200:]}")


# ---- R6-02 (P1): the independent arm check accepts a different question ---------------------------------------------

WRONG = "What is the user's favourite colour?"


def wrong_question(only=None):
    def make(honest):
        def faulty(system, prompt):
            s, p = honest(system, prompt)
            i = p.index("Question: ") + len("Question: "); j = p.index("\n", i)
            if only is None or only in p[i:j]:
                p = p[:i] + WRONG + p[j:]
            return s, p
        return faulty
    return make


def canned(tmp, make=None):
    original = rh._load
    if make is not None:
        def loader(name):
            m = original(name)
            if name == "model_input_capture":
                m.baseline_transform = make(m.baseline_transform)
            return m
        rh._load = loader
    try:
        return rh.run(pathlib.Path(tmp) / "out", rh.FakeModel(), request_manifest="generated")
    finally:
        rh._load = original


def asks(x):
    p = x["prompt"]; i = p.index("Question: ") + len("Question: ")
    return p[i:p.index("\n", i)]


with tempfile.TemporaryDirectory() as d:
    honest = canned(d)
    control(all(asks(a) == asks(b) for a, b in zip([x for x in honest["detail"] if x["arm"] == "veracium"],
                                                   [x for x in honest["detail"] if x["arm"] == "baseline"])),
            f"the honest transform: both arms ask the authored question; rates {rate_str({a: honest['rates'][a]['refusal_rate'] for a in ('veracium', 'baseline')})}")
for label, make in (("every question", wrong_question()), ("only the pet question", wrong_question("pet"))):
    with tempfile.TemporaryDirectory() as d:
        try:
            res = canned(d, make)
            base = [x for x in res["detail"] if x["arm"] == "baseline"]
            changed = sum(1 for x in base if asks(x) == WRONG)
            finding(f"R6-02 a transform that replaces {label} (and is its own oracle) writes a report",
                    (pathlib.Path(d) / "out" / "run_report.txt").exists() and changed >= 1,
                    f"{changed}/{len(base)} baseline prompts ask {WRONG!r}; rates {rate_str({a: res['rates'][a]['refusal_rate'] for a in ('veracium', 'baseline')})}")
        except rh.Refused as e:
            finding(f"R6-02 a transform that replaces {label} (and is its own oracle) writes a report", False, f"Refused: {str(e)[:160]}")


# ---- R6-03 (P2): the compiler stage binds neither the recorded bytes nor the configuration ---------------------------

with tempfile.TemporaryDirectory() as d:
    fresh = rh.run(pathlib.Path(d) / "out", rh.FakeModel(), request_manifest="generated")
ci = fresh["compile_invocation"]
control(rh.reverify(copy.deepcopy(fresh))["compiler_stage"] == "REVERIFIED", "a fresh run's unchanged compile invocation reverifies")
zero = copy.deepcopy(fresh); zero["compile_invocation"]["digest"] = "0" * 64
control(rh.reverify(zero)["compiler_stage"] == "NOT REVERIFIED", "the shipped negative (the digest itself zeroed) refuses")
for field, edit in (("system", lambda c: c.update(system=(c["system"] or "") + " EDITED")),
                    ("prompt", lambda c: c.update(prompt=c["prompt"] + " EDITED")),
                    ("model", lambda c: c.update(model="another-model")),
                    ("max_tokens", lambda c: c.update(max_tokens=(c.get("max_tokens") or 0) + 1))):
    res = copy.deepcopy(fresh); edit(res["compile_invocation"])
    v = rh.reverify(res)
    finding(f"R6-03 the recorded {field} edited (digest kept) still reads REVERIFIED", v["compiler_stage"] == "REVERIFIED",
            f"compiler stage {v['compiler_stage']}; downstream {v['downstream']}")


print(f"\nfindings: {sum(1 for _, r in RESULTS if r)} of {len(RESULTS)} REPRODUCED")
print(f"  controls: {sum(CONTROLS)} of {len(CONTROLS)} hold")
sys.exit(0 if all(r for _, r in RESULTS) and all(CONTROLS) else 1)
