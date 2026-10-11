"""R1-01's required mutants (polarity_pairs.py added after 'drop polarity' SURVIVED on the first 200 items), run against frozen ATTEST-2 (research, 2026-10-11).

A mutant is KILLED when, on the labelled sets (H1 by its author's gold, corpus_v1, probes_after_v1), it produces at
least one false attestation that ATTEST-2 does not. The reviewer's fourth mutant, "trusting the extractor's
grounding field", has no subject in the predicate: attests() takes no such input (its signature is subject,
relation, object, event text). It is an ingest-layer property (0045 INV-G1, a product test at the implementation gate).
"""
import importlib, json, re

import attest_v2 as BASE
from corpus_v1 import ITEMS
from probes_after_v1 import PROBES
from polarity_pairs import PAIRS


def _strict_pairs(pairs):
    """object_pairs_hook: refuse a duplicate key rather than keep the last (the product repo's evidence-boundary rule)."""
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"duplicate JSON key {k!r}")
        d[k] = v
    return d


SETS = ([(i["relation"], i["object"], i["text"], i["gold"]) for i in json.load(open("holdout_h1.json"), object_pairs_hook=_strict_pairs)]
        + [(r, o, t, g) for _, r, o, t, g, _ in ITEMS] + list(PROBES) + list(PAIRS))


def fresh():
    m = importlib.import_module("attest_v2"); return importlib.reload(m)


def drop_polarity():
    m = fresh(); m.NEGATION = []; return m


def swap_subject():
    # accept a third-person or other-possessor statement as the user's: add 3rd-person forms of every trigger
    m = fresh(); T = {}
    for rel, trigs in m.TRIGGERS.items():
        extra = []
        for t in trigs:
            extra += [re.sub(r"^i'm\b|^i am\b", "she's", t), re.sub(r"^i\b", "he", t), re.sub(r"^my\b", "his", t),
                      re.sub(r"^my\b", "her", t)]
        T[rel] = trigs + [e for e in extra if e not in trigs] + [re.sub(r"^i (\w+)", r"\1s", t) for t in trigs if t.startswith("i ")]
    m.TRIGGERS = T; return m


def relation_without_assertion():
    # accept the declared relation when the object merely occurs in the text (the terms-presence test)
    m = fresh()
    def attests(subject, relation, obj, text):
        if subject != "user" or relation not in m.TRIGGERS: return "UNSUPPORTED"
        return "ATTESTED" if obj and m._norm_object(obj) in m._norm(text or "") else "NOT_ATTESTED"
    m.attests = attests; return m


def fp(mod):
    return {(r, t) for r, o, t, g in SETS if not g and mod.attests("user", r, o, t) == "ATTESTED"}


base = fp(fresh())
print("ATTEST-2 false attestations over", len(SETS), "labelled items:", len(base))
for name, mk in (("drop polarity", drop_polarity), ("swap subject", swap_subject),
                 ("relation without a supporting assertion", relation_without_assertion)):
    new = fp(mk()) - base
    print(f"  mutant '{name}': {len(new)} new false attestations -> {'KILLED' if new else 'SURVIVED'}"
          + (f"; e.g. {sorted(new)[0]}" if new else ""))
