"""ATTEST-2 — a bounded, relation-specific attestation predicate (0045 round 2, answering R1-01).

Pure Python, no veracium import. Decides whether a declarative triple about the USER is ATTESTED by the raw event
text: the speaker stated it, about themself, affirmatively, as a current fact. Anything the grammar does not cover
returns UNSUPPORTED, which the caller treats as NOT attested (the proposal/refusal branch) — the safe direction.

Version: ATTEST-2 (2026-10-11, research). ONE change from ATTEST-1: the object must be the IMMEDIATE complement of
the trigger (after an optional article), not merely occur later in the sentence. ATTEST-1 falsely attested 6 of 7
unseen negatives (probes_after_v1.py) because trigger and object could sit in different clauses. Frozen before
any holdout existed. Changing any table below is a new version; results are reported per
version.

Scope (stated, not implied):
  * subject 'user' only — first-person statements by the speaker. Any other subject → UNSUPPORTED.
  * declarative relations only; the procedural path is 0037's and is exempt (never passed here).
  * the raw event text as received by ingest (not an extractor-written episode summary).
"""
import re

VERSION = "ATTEST-2"

# Relation -> first-person trigger phrases (lower case). A trigger is matched at a word boundary; the object must
# follow it within the same sentence. Relations absent here are UNSUPPORTED in this version.
TRIGGERS = {
    "works_as": ["i work as", "i'm a", "i am a", "i'm an", "i am an", "i work at", "i work for", "my job is",
                 "i'm employed as", "i am employed as", "i'm employed at", "i am employed at"],
    "measures": ["i weigh", "my weight is", "i've saved", "i have saved", "my savings are", "i'm on page",
                 "i am on page", "my score is", "i scored"],
    "prefers": ["i prefer", "i'd rather", "i like", "i love", "my favorite", "my favourite"],
    "located_at": ["i live in", "i'm based in", "i am based in", "i live at", "i moved to"],
    "health_state": ["i have", "i've got", "i was diagnosed with", "i've been diagnosed with", "i suffer from",
                     "i'm recovering from", "i am recovering from"],
    "has_pet": ["i have a", "i've got a", "my dog", "my cat", "my pet"],
    "has_diet": ["i'm", "i am", "i follow", "i eat", "i keep"],
    "partner_of": ["my partner", "my wife", "my husband", "my girlfriend", "my boyfriend", "my fiancé",
                   "my fiance", "i'm married to", "i am married to"],
    "relative_of": ["my mother", "my mom", "my father", "my dad", "my sister", "my brother", "my son",
                    "my daughter", "my aunt", "my uncle", "my cousin", "my grandmother", "my grandfather"],
    "works_on": ["i'm working on", "i am working on", "i work on", "my project is"],
    "client_of": ["my client is", "i'm a client of", "i am a client of"],
    "uses_tool": ["i use", "i'm using", "i am using", "i rely on"],
    "avoids_tool": ["i avoid", "i don't use", "i do not use", "i stopped using", "i never use"],
}

# Disqualifiers: if any occurs in the sentence OUTSIDE the matched trigger, the sentence does not attest.
NEGATION = [r"\bnot\b", r"n't\b", r"\bnever\b", r"\bno longer\b", r"\bnobody\b", r"\bnone\b"]
MODALITY = [r"\bif\b", r"\bwould\b", r"\bcould\b", r"\bmight\b", r"\bmay\b", r"\bmaybe\b", r"\bperhaps\b",
            r"\bwant to\b", r"\bwants to\b", r"\bhope to\b", r"\bplan to\b", r"\bplanning to\b",
            r"\bthinking about\b", r"\bconsidering\b", r"\bshould\b", r"\bused to\b", r"\bwill\b", r"\bgoing to\b"]
REPORTED = [r"\bsaid\b", r"\bsays\b", r"\btold me\b", r"\baccording to\b", r"\bthinks\b", r"\bbelieves\b",
            r"\bclaims\b"]

_ARTICLE = re.compile(r"^(?:a|an|the)\s+")
_QUOTED = re.compile(r"[\"“”][^\"“”]*[\"“”]")


def _norm(s: str) -> str:
    """The enumerated normalizations, and only these: case-fold; curly apostrophes to straight; whitespace
    collapsed; digit-unit spacing removed (78 kg == 78kg); trailing sentence punctuation stripped."""
    s = s.replace("’", "'").replace("‘", "'").lower()
    s = re.sub(r"(\d)\s+([a-z%])", r"\1\2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(".!?;,: ")


def _norm_object(o: str) -> str:
    return _ARTICLE.sub("", _norm(o))


def sentences(text: str):
    """Deterministic segmentation: split on . ! ? ; and newlines followed by space or end. A question keeps its
    '?' so it can be recognised."""
    parts = re.split(r"(?<=[.!;])\s+|(?<=\?)\s+|\n+", text.strip())
    return [p for p in (x.strip() for x in parts) if p]


def attests(subject: str, relation: str, obj: str, event_text: str) -> str:
    """Returns 'ATTESTED', 'NOT_ATTESTED' or 'UNSUPPORTED'. The caller treats UNSUPPORTED as not attested."""
    if subject != "user" or relation not in TRIGGERS:
        return "UNSUPPORTED"
    if not event_text or not event_text.strip() or not obj or not obj.strip():
        return "NOT_ATTESTED"
    want = _norm_object(obj)
    for raw in sentences(event_text):
        if raw.rstrip().endswith("?"):
            continue                                        # a question asserts nothing
        s = _norm(_QUOTED.sub(" ", raw))                    # quoted/reported text never attests
        for trig in TRIGGERS[relation]:
            for m in re.finditer(r"(?<![a-z'])" + re.escape(trig) + r"(?![a-z])", s):
                after = _ARTICLE.sub("", s[m.end():].lstrip(" ,:"))
                if not re.match(re.escape(want) + r"(?![a-z0-9])", after):
                    continue
                outside = s[:m.start()] + " " + s[m.end():]
                if any(re.search(p, outside) for p in NEGATION + MODALITY + REPORTED):
                    continue
                return "ATTESTED"
    return "NOT_ATTESTED"
