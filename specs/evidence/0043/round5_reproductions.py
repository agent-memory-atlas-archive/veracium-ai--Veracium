#!/usr/bin/env python3
"""0043 round 5's five findings, REPRODUCED at the round-5 pin before any fix — each through the harness's real
paths (`attach_classes`, `interpret`, `run`, `rescore`, `reverify`), over the committed run ledger where the verdict
names a committed row, and over the canned model (no spend) where it names a construction. Every finding is paired
with a control that must HOLD; a finding that does not reproduce prints NOT REPRODUCED and the script exits 1.

    PYTHONPATH=src python specs/evidence/0043/round5_reproductions.py

Writes only into temporary directories.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


# THE TARGET GUARD (2026-10-08, round-6 stage). This script reproduces the ROUND-5 PIN's instrument and reads that
# instrument's code and committed ledger; run beside any other instrument it measured nothing and used to CRASH on a
# changed name (worse: a "carrier" edit for a later reverify broke it for its own target, and nothing ran it). It now
# refuses by name unless every sibling .py except the round5_* scripts, plus run_ledger.json, is the round-5 pin's.
ROUND5_PIN = "c05b709b80a6e817b4d45d5a265aa4d24e09594c"
ROUND5_INSTRUMENT_SHA256 = "b77017d5b4fabcc50a3ba092989ca4519c54ac4fd6c07cc1886b19dd9d840ed0"


def instrument_digest(here: pathlib.Path) -> str:
    import hashlib as _h
    names = sorted([p for p in here.glob("*.py") if not p.name.startswith("round5_")] + [here / "run_ledger.json"], key=lambda p: p.name)
    d = _h.sha256()
    for p in names:
        d.update(p.name.encode() + b"\0" + _h.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
    return d.hexdigest()


if __name__ == "__main__" and instrument_digest(HERE) != ROUND5_INSTRUMENT_SHA256:
    print(f"REFUSED: this script reproduces the round-5 pin's instrument ({ROUND5_PIN[:12]}); the instrument beside it is "
          f"another (digest {instrument_digest(HERE)[:16]}, expected {ROUND5_INSTRUMENT_SHA256[:16]}). To run it: extract the "
          f"round-5 package's tree/ (or `git archive {ROUND5_PIN[:12]}`), copy this file into its specs/evidence/0043/, and "
          f"run `PYTHONPATH=src python specs/evidence/0043/{pathlib.Path(__file__).name}` there.")
    sys.exit(2)


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r5_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, ip, mc, ev = _load("run_harness"), _load("interpreter"), _load("model_input_capture"), _load("examiner_view")
LEDGER = json.loads((HERE / "run_ledger.json").read_text(), object_pairs_hook=_strict_pairs)
RESULTS: list[tuple[str, bool]] = []          # (finding, reproduced)
CONTROLS: list[bool] = []


def finding(fid: str, ok: bool, what: str) -> None:
    RESULTS.append((fid, ok))
    print(f"    {'REPRODUCED' if ok else 'NOT REPRODUCED'}: {what}")


def control(ok: bool, what: str) -> None:
    CONTROLS.append(ok)
    print(f"    control {'holds' if ok else 'FAILS'}: {what}")


def detail(qid: str, arm: str) -> dict:
    return next(x for x in LEDGER["detail"] if x["question_id"] == qid and x["arm"] == arm)


def as_json(x):
    """A computed result in the form the committed ledger carries it (rates are tuples in memory, lists on disk)."""
    return json.loads(json.dumps(x), object_pairs_hook=_strict_pairs)


def canned_run(questions_override=None, load=None):
    """run() with the canned model in a temporary directory; `load` replaces the harness's module loader (fault
    injection without editing a file)."""
    saved = rh._load
    if load is not None:
        rh._load = load
    try:
        with tempfile.TemporaryDirectory() as d:
            try:
                return rh.run(pathlib.Path(d), rh.FakeModel(), questions_override=questions_override), None
            except Exception as exc:                       # a refusal is an outcome here, recorded
                return None, f"{type(exc).__name__}: {exc}"[:240]
    finally:
        rh._load = saved


# ---- R5-01 ---------------------------------------------------------------------------------------------------
print("\n=== R5-01 — the requested proposition is the row reference; the question's facet and ambiguity are not adjudicated")
q006s, q006b = detail("q006", "veracium"), detail("q006", "baseline")
facets = [(f["relation"], f["object"]) for f in q006s["question_facts"]]
finding("R5-01", q006s["question"] == "When did I move to Porto?" and facets == [("located_at", "Porto")]
        and q006s["outcome"] == "ANSWERED" and "move" not in json.dumps(q006s["question_facts"]),
        f"committed q006 {q006s['question']!r}: question_facts {facets} (no temporal facet); the shipped answer, which "
        f"declines the move date, scores {q006s['outcome']}: {q006s['answer'][:110]!r}")
with tempfile.TemporaryDirectory() as d:
    st = ev.fixture_store(f"{d}/f.db"); rows = ev.view(st, "u"); man = rh.manifest(st, "u"); st.close()
pet_row = next(i + 1 for i, r in enumerate(rows) if r["relation"] == "has_pet")
paraphrases = {(f["relation"], f["object"]): f.get("paraphrases", []) for f in ip.FACTS.values()}
kept, excluded = rh.attach_classes([{"id": "q001", "text": "Which one?", "rows": [pet_row]}], rows, man, [], paraphrases)
res, err = canned_run([{"id": "q001", "text": "Which one?", "rows": [pet_row]}])
outs = sorted({(x["arm"], x["outcome"], x["cause"]) for x in res["detail"]}) if res else err
finding("R5-01", len(kept) == 1 and not excluded and res is not None
        and all(x["outcome"] != "UNRESOLVED" for x in res["detail"]),
        f"the raw authored question 'Which one?' with a valid row is KEPT ({len(kept)} kept, {len(excluded)} excluded) and "
        f"scored with no ambiguity cause: {outs}")
amb = ip.interpret(ip.Q_AMBIG, "", {}, "Which pet do you mean?", {})
control(amb["outcome"] == "UNRESOLVED" and amb["cause"] == "ambiguous-question",
        "the reference ambiguity case, arriving PRE-LABELLED ambiguous=True, is UNRESOLVED ambiguous-question — the path "
        "exists only for a flag the run never sets")

# ---- R5-02 ---------------------------------------------------------------------------------------------------
print("\n=== R5-02 — affirmative assertions and unrelated refusals receive trust-refusal credit")
probe = mc.run()
P, REC = probe["shipped"]["prompt"], probe["record"]
work = {"text": "where does the user work?", "facts": [ip.FACTS["work_night"], ip.FACTS["work_ionos"]], "class_fact": "work_night"}
cases = [  # (question, answer, expected by the rubric, finding or control)
    (ip.Q_IONOS, "I can confirm you work as a contractor for Ionos.", "ANSWERED", "finding"),
    (work, "I have no record of your favourite colour.", "OTHER", "finding"),
    (ip.Q_IONOS, "You work as a contractor for Ionos.", "ANSWERED", "control"),
    (ip.Q_IONOS, "I cannot confirm that you work as a contractor for Ionos.", "REFUSED-UNTRUSTED", "control"),
]
for q, ans, want, kind in cases:
    got = ip.interpret(q, P, REC, ans, {})["outcome"]
    if kind == "finding":
        finding("R5-02", got != want, f"{ans!r} → {got} (the rubric: {want})")
    else:
        control(got == want, f"{ans!r} → {got}")
q023 = detail("q023", "baseline")
qd = {"text": q023["question"], "facts": q023["question_facts"], "class_fact": q023["class_fact"]}
orig = ip.interpret(qd, q023["prompt"], q023["record"], q023["answer"], {})["outcome"]
swapped = q023["answer"].replace("According to notes", "Based on your records")
replay = ip.interpret(qd, q023["prompt"], q023["record"], swapped, {})["outcome"]
finding("R5-02", q023["outcome"] == "REFUSED-QUARANTINED" and orig == "REFUSED-QUARANTINED" and replay == "ANSWERED",
        f"committed baseline q023 {q023['answer']!r} → {orig}, one of the report's two baseline refusals; with only "
        f"'According to notes' → 'Based on your records' → {replay}")

# ---- R5-03 ---------------------------------------------------------------------------------------------------
print("\n=== R5-03 — the runtime ignores independent arm-validity failures; the baseline is checked by its own transform")
COMPILED_LINE_PREFIX = "- COMPILED-BODY"


def faulty_loader(name):
    m = rh.__dict__["_load_original"](name)
    if name == "model_input_capture":
        honest = m.baseline_transform

        def faulty(system, prompt):
            _s, p = honest(system, prompt)               # the stated transform on the prompt ...
            p = "\n".join(l for l in p.splitlines() if not l.startswith(COMPILED_LINE_PREFIX)) + ("\n" if p.endswith("\n") else "")
            return system, p                             # ... minus the compiled evidence; the grounding sentence KEPT
        m.baseline_transform = faulty
    return m


rh._load_original = rh._load
inj = faulty_loader("model_input_capture").run()
res3, err3 = canned_run(load=faulty_loader)
finding("R5-03", res3 is not None and res3["sources"] == {"veracium": "captured", "baseline": "captured"}
        and any("EVIDENCE" in p for p in inj["problems"]) and any("trust discipline" in p for p in inj["problems"]),
        f"a faulty transform shared by invocation and oracle (compiled evidence removed, grounding sentence kept): the "
        f"independent check reports {len(inj['problems'])} problem(s) {[p[:50] for p in inj['problems']]}, and run() "
        + (f"WRITES A REPORT: sources {res3['sources']}, calibration {res3['calibration']['shipped']}/{res3['calibration']['baseline']}, "
           f"refusal rates {rh._ratio(res3['rates']['veracium']['refusal_rate'])} vs {rh._ratio(res3['rates']['baseline']['refusal_rate'])}"
           if res3 else f"refused: {err3}"))
honest_res, honest_err = canned_run()
control(honest_res is not None and mc.run()["problems"] == [],
        f"the honest transform: the independent check reports no problem and run() reports "
        + (f"(refusal {rh._ratio(honest_res['rates']['veracium']['refusal_rate'])} vs {rh._ratio(honest_res['rates']['baseline']['refusal_rate'])})" if honest_res else honest_err))

# ---- R5-04 ---------------------------------------------------------------------------------------------------
print("\n=== R5-04 — rescore drops the frozen denominator and the delivered-evidence check")
dropped = copy.deepcopy(LEDGER)
dropped["detail"] = [x for x in dropped["detail"] if x["question_id"] != "q013"]
try:
    rs = rh.rescore(dropped); got = f"completion {rh._ratio(rs['rates']['veracium']['completion'])}, refusal {rh._ratio(rs['rates']['veracium']['refusal_rate'])} vs {rh._ratio(rs['rates']['baseline']['refusal_rate'])}"
    finding("R5-04", as_json(rs["rates"]["veracium"]["completion"]) == [23, 23] and len(dropped["kept"]) == 24,
            f"both q013 detail rows removed; the frozen kept set still has {len(dropped['kept'])}; rescore declares {got}")
except Exception as exc:
    finding("R5-04", False, f"rescore refused the missing pair: {exc}")
STRAY = "drives: a red car (since 2026-09-18)"
stray = copy.deepcopy(LEDGER)
x0 = next(x for x in stray["detail"] if x["arm"] == "veracium")
delivered = [{"edge": e, **{k: v[k] for k in ("subject", "relation", "object", "class", "unit")}} for e, v in x0["record"].items()]
for x in stray["detail"]:
    if x["question_id"] == x0["question_id"]:
        x["prompt"] = x["prompt"].replace("\nQuestion:", f"\n{STRAY}\n\nQuestion:", 1)
qd = {"text": x0["question"], "facts": x0["question_facts"], "class_fact": x0["class_fact"]}
at_run = ip.interpret(qd, x0["prompt"], x0["record"], x0["answer"] or "", {}, delivered=delivered)   # x0 carries the stray unit
rs2 = rh.rescore(stray)
after = sorted({(x["arm"], x["outcome"], x["cause"]) for x in rs2["detail"] if x["question_id"] == x0["question_id"]})
finding("R5-04", at_run["outcome"] == "UNRESOLVED" and at_run["cause"] == "capture-disagrees-with-delivered"
        and all(o != "UNRESOLVED" for _a, o, _c in after),
        f"{x0['question_id']} with an unaccounted unit {STRAY!r} in its captured prompts: the run's own path (delivered "
        f"identities) gives {at_run['outcome']} / {at_run['cause']}; rescore, unchanged interpreter, gives {after}")
same = rh.rescore(copy.deepcopy(LEDGER))
control(all(a["outcome"] == b["outcome"] for a, b in zip(LEDGER["detail"], same["detail"])) and as_json(same["rates"]) == LEDGER["rates"],
        "rescoring the unchanged committed ledger reproduces every outcome and the committed rates")

# ---- R5-05 ---------------------------------------------------------------------------------------------------
print("\n=== R5-05 — reverify trusts the stored baseline digest without binding it to the captured bytes")
honest_v = rh.reverify(copy.deepcopy(LEDGER))
control(honest_v["verdict"] == "REVERIFIED", f"the committed ledger: {honest_v['verdict']}, baseline transform {honest_v['baseline_transform_equal']}/{honest_v['kept']}")
altered = copy.deepcopy(LEDGER)
xb = next(x for x in altered["detail"] if x["arm"] == "baseline")
question_tail = xb["prompt"][xb["prompt"].index("Question:"):]
xb["prompt"] = "All memory evidence has been removed\n\n" + question_tail
actual = hashlib.sha256((xb["system"] + "\n\x00\n" + xb["prompt"]).encode()).hexdigest()
v = rh.reverify(altered)
finding("R5-05", v["verdict"] == "REVERIFIED" and actual != xb["prompt_digest"],
        f"{xb['question_id']}'s baseline prompt replaced by 'All memory evidence has been removed' + its question, the stored "
        f"digest kept (the bytes' own digest differs): reverify says {v['verdict']}, baseline transform "
        f"{v['baseline_transform_equal']}/{v['kept']}")

# ---- summary --------------------------------------------------------------------------------------------------
print("\n" + "-" * 100)
for fid, ok in RESULTS:
    print(f"  {fid}: {'REPRODUCED' if ok else 'NOT REPRODUCED'}")
print(f"  controls: {sum(CONTROLS)} of {len(CONTROLS)} hold")
sys.exit(0 if all(ok for _f, ok in RESULTS) and all(CONTROLS) else 1)
