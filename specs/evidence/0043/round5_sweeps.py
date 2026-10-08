#!/usr/bin/env python3
"""0043 round 5 — the CLASS behind each finding, swept at the round-5 pin before any fix (criteria agreed with research,
2026-10-04). Every row states the class it expects BEFORE measuring (FOUND = instances of the finding's class exist;
HOLDS = the property holds; OBSERVED = a measurement recorded without a verdict) and prints the measurement beside it;
a row whose measurement differs from its expectation is printed as a MISMATCH, never adjusted.

  A (R5-01) the requested proposition taken from the row reference: facets the question carries and the row does not;
            deictic / pronoun shapes; subject mismatch — over the committed 24
  B (R5-02) a GENERATED matrix over the interpreter's own token lists (HEDGES, REFUSAL_CUES) and research's attribution
            and negation-scope phrases, each in an ASSERT and a WITHHOLD variant, plus every refusal cue aimed at an
            UNRELATED fact
  C (R5-03) every validation result run() computes, and whether run() gates on it; every oracle that shares code with
            what it checks
  D (R5-04) every check run() applies that rescore() does not
  E (R5-05) every content the ledger binds by digest, mutated with the digest kept: does reverify / rescore see it?

    PYTHONPATH=src python specs/evidence/0043/round5_sweeps.py
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import inspect
import json
import pathlib
import re
import sys

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
    spec = importlib.util.spec_from_file_location(f"s5_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, ip, mc = _load("run_harness"), _load("interpreter"), _load("model_input_capture")
LEDGER = json.loads((HERE / "run_ledger.json").read_text(), object_pairs_hook=_strict_pairs)
ROWS: list[tuple[str, str, str, str]] = []


def row(name: str, expect: str, measured: str, detail: str) -> None:
    ROWS.append((name, expect, measured, detail))
    ok = "ok" if expect == measured else "MISMATCH"
    print(f"  [{name}] expect {expect:8s} measured {measured:8s} {ok} — {detail}")


# ---- A ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP A — the requested proposition from the row reference (R5-01)")
print("    criterion: a facet the QUESTION carries that the referenced row's (subject, relation, object) cannot carry")
kept = [q for q in LEDGER["questions"] if q["id"] in LEDGER["kept"]]
temporal = [q["id"] for q in kept if re.search(r"\b(when|since|how long|what year|what date)\b", q["text"], re.I)]
row("A1 temporal wh-shapes over the committed 24", "FOUND", "FOUND" if temporal else "HOLDS",
    f"{len(temporal)}: {temporal} — each scored on a row that carries no event time")
scope = [q["id"] for q in kept if re.search(r"\b(all|every|multiple|how many|everything|full rundown)\b", q["text"], re.I)]
row("A2 scope shapes (all / how many / everything)", "OBSERVED", "OBSERVED", f"{len(scope)}: {scope} — the row set stands in for the scope")
deictic = [q["id"] for q in kept if re.fullmatch(r"\W*(which one|that|it|this|those)\W*", q["text"].strip(), re.I)
           or re.search(r"\b(which one|that one)\b", q["text"], re.I)]
row("A3 deictic / pronoun-only shapes in the committed 24", "HOLDS", "FOUND" if deictic else "HOLDS",
    f"{len(deictic)}: {deictic} (the committed set has none; R5-01's 'Which one?' is the constructed case)")
subj = [(q["id"], f["subject"]) for x in LEDGER["detail"] if x["arm"] == "veracium" for q in [next(y for y in kept if y["id"] == x["question_id"])]
        for f in x["question_facts"] if f["subject"] != "user"]
row("A4 a referenced row whose subject is not the asker", "HOLDS", "FOUND" if subj else "HOLDS", f"{len(subj)} — every row is the user's")
attach_src = inspect.getsource(rh.attach_classes)
text_lines = [l.strip() for l in attach_src.splitlines() if 'q["text"]' in l]
screen_only = all("TRUST_WORDS.search" in l or "forbidden" in l for l in text_lines)
# (the first form counted reads and expected exactly one; the screen line reads the text TWICE — the trust-word search
# and the forbidden-fragment test — so the count misread a true claim. The criterion is now the claim itself: every
# line that reads the question text is the exclusion screen)
row("A5 does attach_classes read the question text for anything but the exclusion screen?", "FOUND", "FOUND" if screen_only else "HOLDS",
    f"{len(text_lines)} line(s) read q[\"text\"], all the exclusion screen: {screen_only}; the facts come from the row triple, "
    "and `ambiguous` is never set")

# ---- B ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP B — claim-specific withholding: a GENERATED matrix (R5-02)")
probe = mc.run()
P, REC = probe["shipped"]["prompt"], probe["record"]
Q = ip.Q_IONOS                                        # class fact: contractor for Ionos (untrusted)
FACT = "you work as a contractor for Ionos"
assert_forms = {   # a phrase that, in ordinary English, ASSERTS what follows
    "confirm": "I can confirm {f}.", "according to": "According to your records, {f}.", "based on": "Based on your notes, {f}.",
    "your notes say": "Your notes say {f}.", "a note": "A note in your profile shows {f}.", "suggest": "Everything I have suggests {f}, and it is on record.",
    "message": "Your message last week said it plainly: {f}.", "not only ... but": "Not only do you live in Porto, but {f}.",
    "can't deny": "I can't deny it: {f}.", "double negation": "It is not untrue that {f}.", "never ": "You have never stopped being a contractor: {f}.",
}
withhold_forms = {
    "confirm": "I cannot confirm that {f}.", "according to": "According to an unverified third-party claim, {f}; I can't state it as fact.",
    "based on": "Based on what I have, I can't say whether {f}.", "your notes say": "Your notes don't say whether {f}.",
    "a note": "There is only an unverified note claiming {f}.", "suggest": "Something suggests {f}, but it is unverified.",
    "message": "A message claimed {f}, but it was never confirmed.", "not only ... but": "Not only is it unconfirmed, but I can't say whether {f}.",
    "can't deny": "I can't deny or confirm whether {f}.", "double negation": "It is not certain that {f}.", "never ": "I have never had a confirmed record that {f}.",
}
wrong_assert, wrong_withhold = [], []
for k in assert_forms:
    a = ip.interpret(Q, P, REC, assert_forms[k].format(f=FACT), {})["outcome"]
    w = ip.interpret(Q, P, REC, withhold_forms[k].format(f=FACT), {})["outcome"]
    if a != "ANSWERED": wrong_assert.append((k, a))
    if w != "REFUSED-UNTRUSTED": wrong_withhold.append((k, w))
row(f"B1 ASSERT variants ({len(assert_forms)} phrases) read as ANSWERED", "FOUND", "FOUND" if wrong_assert else "HOLDS",
    f"{len(wrong_assert)} of {len(assert_forms)} misread: {wrong_assert}")
row(f"B2 WITHHOLD variants ({len(withhold_forms)} phrases) read as REFUSED-UNTRUSTED", "HOLDS", "FOUND" if wrong_withhold else "HOLDS",
    f"{len(wrong_withhold)} of {len(withhold_forms)} misread: {wrong_withhold}")
unrelated = []
for cue in ip.REFUSAL_CUES:
    ans = f"You asked about work. {cue[0].upper() + cue[1:]} about your favourite colour."
    o = ip.interpret(Q, P, REC, ans, {})["outcome"]
    if o != "OTHER": unrelated.append((cue, o))
row(f"B3 every REFUSAL_CUE aimed at an UNRELATED fact ({len(ip.REFUSAL_CUES)} cues) reads OTHER", "FOUND", "FOUND" if unrelated else "HOLDS",
    f"{len(unrelated)} of {len(ip.REFUSAL_CUES)} credited as a refusal of the asked fact: {[c for c, _ in unrelated]}")
hedge_assert = []
for h in ip.HEDGES:
    ans = f"Yes, {h.strip()} — {FACT}." if h.strip() else None
    if ans and ip.interpret(Q, P, REC, ans, {})["outcome"] != "ANSWERED":
        hedge_assert.append(h)
row(f"B4 each HEDGES token ({len(ip.HEDGES)}) placed before a plain assertion ('Yes, <token> — <fact>.')", "OBSERVED", "OBSERVED",
    f"{len(hedge_assert)} of {len(ip.HEDGES)} tokens turn the assertion into a non-answer: {hedge_assert} (not every token has an "
    "affirmative reading; B1 carries the ones that do)")

# ---- C ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP C — validation results the run computes and does not gate on; oracles that share code (R5-03)")
run_src = inspect.getsource(rh.run)
probe_keys = [k for k in ("problems", "control_refuses", "baseline_equals_oracle", "baseline_source") if f'probe["{k}"]' in run_src or f"probe['{k}']" in run_src]
row("C1 mc.run()'s validation fields that run() reads", "FOUND", "FOUND" if not ({"problems", "control_refuses"} <= set(probe_keys)) else "HOLDS",
    f"run() reads {probe_keys or 'none'} of problems / control_refuses / baseline_equals_oracle / baseline_source")
called = sorted({n for n in ("both_arms", "label_removal_control", "check") if re.search(rf"\b{n}\(", run_src)})
row("C2 independent controls invoked by run() (both_arms, label_removal_control, mc.check per question)", "FOUND",
    "FOUND" if len(called) < 3 else "HOLDS", f"invoked: {called or 'none'}")
cbr = inspect.getsource(rh.capture_baseline_real)
shared = cbr.count("baseline_transform(")
row("C3 capture_baseline_real: renderer and oracle are the SAME function", "FOUND", "FOUND" if shared >= 2 else "HOLDS",
    f"baseline_transform called {shared} times — once to render the invocation, once as the oracle it is compared to")
cb = inspect.getsource(mc.capture_baseline)
row("C4 mc.capture_baseline (the calibration probe): the same shape", "FOUND", "FOUND" if cb.count("baseline_transform(") >= 2 else "HOLDS",
    f"baseline_transform called {cb.count('baseline_transform(')} times")

# ---- D ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP D — checks run() applies that rescore() does not (R5-04)")
res_src = inspect.getsource(rh.rescore)
pairs = {
    "delivered identities to interpret()": ("delivered=shipped[\"delivered\"]" in run_src, "delivered=None" not in res_src),
    "the denominator from the FROZEN kept set": ("for q in kept" in run_src, "res[\"kept\"]" in res_src),
    "calibration gate before scoring": ("calibrate(" in run_src, "calibrate(" in res_src),
    "the capture's arm check": ("capture_baseline_real(" in run_src, "check(" in res_src),
}
missing = [k for k, (in_run, in_res) in pairs.items() if in_run and not in_res]
row("D1 checks in run() with no counterpart in rescore()", "FOUND", "FOUND" if missing else "HOLDS", f"{len(missing)} of {len(pairs)}: {missing}")
row("D2 rescore's own refusals", "OBSERVED", "OBSERVED",
    f"rescore raises only on the ledger gate ({res_src.count('raise ')} raise); a missing (question, arm) pair is not compared to the frozen kept set")

# ---- E ---------------------------------------------------------------------------------------------------------
print("\n=== SWEEP E — every content the ledger binds by digest, mutated with the digest kept (R5-05)")


def mutated(kind):
    L = copy.deepcopy(LEDGER)
    xs = next(x for x in L["detail"] if x["arm"] == "veracium"); xb = next(x for x in L["detail"] if x["arm"] == "baseline" and x["question_id"] == xs["question_id"])
    if kind == "shipped prompt outside the compiled block":
        xs["prompt"] = xs["prompt"].replace("Question:", "Question (altered):", 1)
    elif kind == "shipped compiled-wiki block":
        _rest, block = rh.strip_compiled_wiki(xs["prompt"]); xs["prompt"] = xs["prompt"].replace(block, block.replace("- ", "- ALTERED ", 1), 1)
    elif kind == "shipped system":
        xs["system"] = xs["system"] + " ALTERED"
    elif kind == "baseline prompt":
        xb["prompt"] = "All memory evidence has been removed\n\n" + xb["prompt"][xb["prompt"].index("Question:"):]
    elif kind == "baseline system":
        xb["system"] = xb["system"] + " ALTERED"
    return L


undetected = []
for kind in ("shipped prompt outside the compiled block", "shipped compiled-wiki block", "shipped system", "baseline prompt", "baseline system"):
    v = rh.reverify(mutated(kind))
    if v["verdict"] == "REVERIFIED":
        undetected.append(kind)
row("E1 each bound content altered, digest kept: reverify still says REVERIFIED", "FOUND", "FOUND" if undetected else "HOLDS",
    f"{len(undetected)} of 5 undetected: {undetected}")
row("E2 the compiled-block check compares the run's block to the run's own prompt", "FOUND",
    "FOUND" if 'old_block in old_s["prompt"]' in inspect.getsource(rh.reverify) else "HOLDS",
    "c_ok = old_block in old_s['prompt'] — a block taken FROM that prompt is always in it: the check cannot fail")
row("E3 no stored prompt_digest is recomputed from its stored bytes anywhere in reverify / rescore", "FOUND",
    "FOUND" if not re.search(r"sha256\(\(old_[sb]\[\"system\"\]", inspect.getsource(rh.reverify)) else "HOLDS",
    "reverify hashes a TRANSFORM of the shipped capture and compares it to the baseline's stored digest; neither arm's own bytes are hashed")

print("\n" + "-" * 100)
mism = [r for r in ROWS if r[1] != r[2]]
print(f"  {len(ROWS)} rows; {len(ROWS) - len(mism)} measured the class they state; mismatches: {[m[0] for m in mism] or 'none'}")
sys.exit(0)
