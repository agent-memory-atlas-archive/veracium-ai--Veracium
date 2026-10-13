"""Mechanism mutants for ATTEST-3 (research, 2026-10-12). Usage: python mutants_v3.py

Each mutant removes ONE rule of ATTEST-3's supported construction (attest_v3.py's docstring, rules 1-5), plus
R1-01's three required mutants carried from ATTEST-2. A mutant is KILLED when the development regressions
(regressions_v3.py: the R2 and class negatives) gain at least one false attestation under it, and the control (the
unmutated predicate) has none. Mutants patch a fresh import of the module, never the file. Exit 0 only if every
mutant is killed and the control is clean, run first and last.
"""
import importlib
import re
import sys

import regressions_v3 as R


def fresh():
    import attest_v3
    return importlib.reload(attest_v3)


def false_attestations(A):
    """Every development NEGATIVE: the regression rows and the earlier development sets' negatives (corpus_v1,
    probes_after_v1, polarity_pairs). None of these is a holdout; H1 and H2 are never used to kill a mutant."""
    rows = R.R2_NEGATIVES + R.CLASS_NEGATIVES + R.CONTROLS
    rows += [(i[1], i[2], i[3], "corpus_v1 " + i[0]) for i in R.ITEMS if not i[4]]
    rows += [(r, o, t, "probes_after_v1") for r, o, t, g in R.PROBES if not g]
    rows += [(r, o, t, "polarity_pairs") for r, o, t, g in R.PAIRS if not g]
    return [r for r in rows if A.attests("user", r[0], r[1], r[2]) == "ATTESTED"]


def m_split_before_quotes(A):            # rule 1: remove quotes per sentence, after splitting (ATTEST-2's order)
    orig = A.strip_quotes
    A.strip_quotes = lambda t: t
    old = A.sentences
    A.sentences = lambda t: [re.sub(r"[\"“”][^\"“”]*[\"“”]", " ", x) for x in old(t)]
    return orig


def m_any_prefix(A):                     # rule 2: the trigger may sit anywhere (no frame check)
    A._prefix_ok = lambda prefix: True


def m_prefix_object(A):                  # rule 3: the object need only be a prefix of the complement
    A._complement_complete = lambda after, rel: True


def m_generic_binds(A):                  # rule 4: generic triggers bind the relation without the lexicon
    A.LEXICON = {k: _Everything() for k in A.TRIGGERS}


class _Everything(set):
    def __contains__(self, x):
        return True


def m_no_retraction(A):                  # rule 5: ignore an event-level retraction
    A.RETRACTIONS = []


def m_drop_polarity(A):                  # R1-01: drop the negation list (outside-span negation)
    A.NEGATION = []


def m_swap_subject(A):                   # R1-01: the subject is not bound: a third-person statement counts
    third = {"works as": "works_as", "is a": "works_as", "is an": "works_as", "lives in": "located_at",
             "weighs": "measures", "has": "health_state", "uses": "uses_tool", "avoids": "avoids_tool",
             "prefers": "prefers"}
    for trig, rel in third.items():
        A.TRIGGERS[rel][0].append(trig)
    orig = A._prefix_ok
    A._prefix_ok = lambda prefix: orig(prefix) or bool(re.fullmatch(
        r"(?:he|she|they|dana|sam|maria|my (?:brother|sister|mum|mom|dad|wife|husband|partner|friend|manager))\s*",
        prefix.strip()))


def m_terms_presence(A):                 # R1-01: the relation's object merely appears in the text
    A.attests = lambda subject, relation, obj, text: ("ATTESTED" if obj.lower() in text.lower() else "NOT_ATTESTED")


MUTANTS = {"rule 1: quotes removed after splitting": m_split_before_quotes,
           "rule 2: any material before the trigger": m_any_prefix,
           "rule 3: a prefix of the complement suffices": m_prefix_object,
           "rule 4: generic triggers bind without the lexicon": m_generic_binds,
           "rule 5: retractions ignored": m_no_retraction,
           "R1-01: drop polarity": m_drop_polarity,
           "R1-01: swap subject": m_swap_subject,
           "R1-01: terms presence": m_terms_presence}


def main():
    ok = True
    ctl = false_attestations(fresh())
    print(f"control (first): {len(ctl)} false attestations")
    ok &= not ctl
    for name, mut in MUTANTS.items():
        A = fresh()
        mut(A)
        fa = false_attestations(A)
        killed = len(fa) > 0
        ok &= killed
        print(f"{'KILLED  ' if killed else 'SURVIVED'} {name}: {len(fa)} new false attestations"
              + (f", e.g. {fa[0][2]!r}" if fa else ""))
    ctl = false_attestations(fresh())
    print(f"control (last): {len(ctl)} false attestations")
    ok &= not ctl
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
