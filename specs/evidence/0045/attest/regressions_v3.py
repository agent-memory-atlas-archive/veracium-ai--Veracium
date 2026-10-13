"""ATTEST-3's development regressions (research, 2026-10-12) — a GATE, not a rate. Usage: python regressions_v3.py

R2-01's closure: every negative the round-2 reviewer listed (6) and every same-class negative research's stage-1
probes added (17; research 9ead5e9f) must stay NOT attested, the direct positive must attest, and the direct
negation must not. These strings were written knowing the predicate's failures, so they may never be quoted as a
rate: a rate comes only from a fresh holdout (H2). Every earlier development set is re-run too (corpus_v1,
probes_after_v1, polarity_pairs): its NEGATIVES are gates (0 false attestations), its positives are reported, since a
safe-direction miss is a cost, not a defect. H1 is NOT run here: score_h1.py runs it, as regression only.
Exit 0 only if every gate holds.
"""
import sys

import attest_v3 as A
from corpus_v1 import ITEMS
from polarity_pairs import PAIRS
from probes_after_v1 import PROBES

D = ("works_as", "dentist")
# (relation, object, text, source)
R2_NEGATIVES = [
    (*D, 'A sample passage reads: "I work as a dentist. I live in Rome."', "verdict: quote spans sentences"),
    (*D, "Suppose I work as a dentist.", "verdict: supposition"),
    (*D, "It is false that I work as a dentist.", "verdict: outer negation"),
    (*D, "I work as a dentist's receptionist.", "verdict: prefix object"),
    ("works_as", "diabetic", "I am a diabetic.", "verdict: generic trigger, relation unbound"),
    ("has_diet", "tired", "I am tired.", "verdict: generic trigger, relation unbound"),
    (*D, "Imagine I work as a dentist.", "research: supposition, lexicon gap"),
    (*D, "Pretend I work as a dentist.", "research: supposition, lexicon gap"),
    (*D, "Let's say I work as a dentist.", "research: supposition, lexicon gap"),
    (*D, "It's untrue that I work as a dentist.", "research: outer negation, lexicon gap"),
    (*D, "I deny that I work as a dentist.", "research: outer negation, lexicon gap"),
    (*D, "I work as a dentist assistant.", "research: compound object"),
    (*D, "I work as a dentist-in-training.", "research: hyphenated object"),
    (*D, "He wrote: I work as a dentist.", "research: reported speech, verb not listed"),
    (*D, "I work as a dentist. Just kidding.", "research: retraction in a LATER sentence"),
    (*D, "Translate: I work as a dentist.", "research: metalinguistic frame"),
    (*D, "Example sentence: I work as a dentist.", "research: metalinguistic frame"),
]
# the same classes, one step further from the listed strings (written with the predicate, so gates only)
CLASS_NEGATIVES = [
    ("located_at", "Rome", "“Picture this. I live in Rome.” That was the prompt.", "quote spans sentences, curly"),
    ("located_at", "Rome", 'She typed "I live in Rome', "unbalanced quote: the rest is quoted"),
    ("works_as", "nurse", "Assume I'm a nurse.", "supposition, generic trigger"),
    ("has_diet", "vegan", "Say I'm vegan, what then?", "supposition inside a question"),
    ("works_as", "pilot", "I am a pilot's daughter.", "possessive after a lexicon object"),
    ("works_as", "teacher", "I'm a teacher trainee.", "content word after a lexicon object"),
    ("has_pet", "dog", "I have a dog allergy.", "content word after a lexicon object"),
    ("health_state", "asthma", "I have asthma medication for my son.", "content word after the object"),
    ("works_as", "happy", "I'm a happy person.", "generic trigger, object outside the lexicon"),
    ("prefers", "tea", "I like tea.", "generic trigger, relation with no lexicon"),
    ("uses_tool", "Notion", "My manager says I use Notion.", "reported: frame before the trigger"),
    ("located_at", "Berlin", "I live in Berlin. Not really, I live in Hamburg.", "retraction"),
]
POSITIVES = [
    (*D, "I work as a dentist.", "verdict: direct positive control"),
    ("works_as", "nurse", "Yes, I'm a nurse.", "filler, generic trigger, lexicon object"),
    ("works_as", "paralegal", "I work as a paralegal at a small firm downtown.", "a following prepositional phrase"),
    ("has_diet", "keto", "I'm on a keto diet these days.", "relation-specific head noun after the object"),
    ("has_diet", "vegan", "Honestly, I'm vegan.", "filler, generic trigger, lexicon object"),
    ("located_at", "Brisbane", "These days I live in Brisbane, near the river.", "filler, clause punctuation"),
    ("has_pet", "cat", "I have a cat named Miso.", "generic trigger, lexicon object, 'named'"),
    ("health_state", "asthma", "I was diagnosed with asthma in 2019.", "specific trigger"),
    ("uses_tool", "Obsidian", "I use Obsidian for everything.", "specific trigger"),
]
CONTROLS = [(*D, "I don't work as a dentist.", "verdict: direct negation control")]


def run():
    bad = []
    for rows, want, label in ((R2_NEGATIVES, False, "R2 negative"), (CLASS_NEGATIVES, False, "class negative"),
                              (POSITIVES, True, "positive"), (CONTROLS, False, "control")):
        for rel, obj, text, src in rows:
            got = A.attests("user", rel, obj, text) == "ATTESTED"
            if got != want:
                bad.append(f"{label}: {rel} {obj!r} | {text} | {src} -> {'ATTESTED' if got else 'not attested'}")
    dev = [(i[1], i[2], i[3], i[4], "corpus_v1 " + i[0]) for i in ITEMS]
    dev += [(r, o, t, g, "probes_after_v1") for r, o, t, g in PROBES]
    dev += [(r, o, t, g, "polarity_pairs") for r, o, t, g in PAIRS]
    fp = [d for d in dev if not d[3] and A.attests("user", d[0], d[1], d[2]) == "ATTESTED"]
    pos = [d for d in dev if d[3]]
    tp = [d for d in pos if A.attests("user", d[0], d[1], d[2]) == "ATTESTED"]
    bad += [f"earlier development NEGATIVE attested: {d[0]} {d[1]!r} | {d[2]} | {d[4]}" for d in fp]
    n = len(R2_NEGATIVES) + len(CLASS_NEGATIVES) + len(POSITIVES) + len(CONTROLS)
    print(f"{A.VERSION}: {n} regression rows; earlier development sets: {len(dev) - len(pos)} negatives, "
          f"{len(fp)} falsely attested; {len(tp)}/{len(pos)} positives attested (reported, not gated)")
    for d in pos:
        if d not in tp:
            print(f"  safe-direction miss: {d[0]} {d[1]!r} | {d[2]} | {d[4]}")
    print("\n".join(bad) if bad else "every gate holds")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(run())
