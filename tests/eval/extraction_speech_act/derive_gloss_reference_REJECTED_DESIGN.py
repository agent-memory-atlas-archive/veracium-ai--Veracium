#!/usr/bin/env python3
"""THE RECORD OF THE REJECTED DERIVATION DESIGN — 0037 v21. NOT the live rule.

⛔ DO NOT READ THIS AS THE SPEC. The rule implemented below was MEASURED AND
REJECTED on 2026-09-13, the same day it was written. It is kept, and pinned
beside `test_the_derived_gloss_is_not_withheld_by_describes_frozen_floor`,
because it is what makes "both designs were measured before the choice"
CHECKABLE rather than asserted.

WHAT IT IMPLEMENTS, and why both halves were asked for:
  * CONTRACTION EXPANSION — added because research measured dev's first stated
    rule ("subject dropped, no inflection") against all sixteen observed
    positives and 13 of 16 derived to a stranded clitic: "'ve been misting my
    fern every other day". Expansion repaired that, 0 of 16 broken.
  * CLAUSE-OPENING SUBJECT DROPPING — dev's refinement after printing the line
    "have been keeping track of the birds I have seen", which dropping every
    "I" destroyed.

WHY THE WHOLE DESIGN WAS THEN REJECTED, and it is the useful part: with the
subject dropped, a present-simple routine becomes an IMPERATIVE-SHAPED FRAGMENT
("always run the linter before merging"), and `describe`'s own FROZEN
executable-detail floor WITHHOLDS it. The transform made its output invisible
at the surface it exists to feed. Neither seat saw it in the sixteen printed
lines, because all sixteen are present-perfect-continuous and survive either
way; dev found it by RUNNING THE FLOOR rather than reasoning about it.

THE LIVE RULE (0037 v21 Gate 4, V-GLOSS-DERIVED) DOES LESS: the user's sentence,
whitespace-normalised, with ONE cut — a comma-introduced relative clause from
its comma to the end — and nothing else. No expansion, no subject drop, no
inflection. Expansion only ever existed to repair the dropping; with the
dropping gone it had nothing to repair.

Original header, kept because it records why the file was written before the
rejection: "Research's REFERENCE derivation of the procedural gloss — a
cross-check, not a spec."

WHY THIS IS NOT THE DESIGNED-FROM PROBLEM, while authoring expected GLOSSES for a
model's paraphrase would have been. A paraphrase is a JUDGEMENT: if research
writes the target and dev's rule is tuned to hit it, the measurement is of the
agreement between two authors. A derivation is a MECHANICAL TRANSFORM: the output
is a function of the span, so two independent implementations either agree or one
is wrong. Disagreement is a finding in both directions.

So this exists to be DIFFED against dev's implementation, not copied by it.

THE RULE, as ruled 2026-09-13 and amended by research's contraction finding:
  1. normalise (the SAME normaliser the grammar's token stream uses)
  2. EXPAND CONTRACTIONS — before the subject is dropped, or 13 of 16 observed
     positives derive to a stranded clitic ("'ve been misting my fern")
  3. drop the leading first-person subject
  4. no inflection attempted; `describe` supplies the frame
"""
import json, re, sys

EXPANSIONS = [
    (r"\bI['’]ve\b", "I have"), (r"\bI['’]m\b", "I am"),
    (r"\bI['’]ll\b", "I will"), (r"\bI['’]d\b", "I would"),
    (r"\bdon['’]t\b", "do not"), (r"\bdoesn['’]t\b", "does not"),
    (r"\bdidn['’]t\b", "did not"), (r"\bcan['’]t\b", "cannot"),
    (r"\bwon['’]t\b", "will not"), (r"\bisn['’]t\b", "is not"),
    (r"\baren['’]t\b", "are not"), (r"\bwasn['’]t\b", "was not"),
    (r"\bhaven['’]t\b", "have not"), (r"\bhasn['’]t\b", "has not"),
]


def derive(span: str) -> str:
    s = " ".join(span.split())
    s = s.replace("’", "'")                      # the F1 literal, normalised FIRST
    for pat, rep in EXPANSIONS:
        s = re.sub(pat, rep, s, flags=re.I)
    s = re.sub(r"^\s*I\b", "", s).strip()
    return s


if __name__ == "__main__":
    files = ("ablation_31_labelled.jsonl", "heldout_51_labelled.jsonl",
             "draw3_39_labelled.jsonl", "draw4_120_labelled.jsonl")
    rows, seen, out = [], set(), []
    for f in files:
        for line in open(f):
            r = json.loads(line)
            if r["expected"] == "pass" and r["quote"] not in seen:
                seen.add(r["quote"])
                out.append({"src": f.split("_")[1], "n": r["n"],
                            "span": " ".join(r["quote"].split()),
                            "derived": derive(r["quote"])})
    print(f"# {len(out)} derived glosses — every clean positive observed across "
          f"400 LongMemEval sessions\n")
    for i, r in enumerate(out, 1):
        print(f"{i:2d}. recorded from something you said: {r['derived']}")
    bad = [r for r in out if not r["derived"][:1].isalpha()]
    print(f"\n# malformed (not starting with a letter): {len(bad)}")
    with open("derived_glosses_16.jsonl", "w") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
