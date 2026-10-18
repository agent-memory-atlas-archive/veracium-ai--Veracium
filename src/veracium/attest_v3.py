"""ATTEST-3 — a clause-scoped, relation-bound attestation predicate (0045 v1.8, answering package II round 2's R2-01).

Pure Python, no veracium import. Decides whether a declarative triple about the USER is ATTESTED by the raw event
text: the speaker stated it, about themself, affirmatively, as a current fact. Anything outside the SUPPORTED
CONSTRUCTION below returns NOT_ATTESTED or UNSUPPORTED, which the caller treats as not attested — the safe direction.

Version: ATTEST-3 (2026-10-12, research). ATTEST-2 matched a trigger ANYWHERE in a sentence and then excluded bad
contexts with a finite blacklist; the round-2 reviewer showed six strings it attested that state nothing of the kind
(a quotation spanning sentences, a supposition, an outer negation, a prefix of the real occupation, and two generic
triggers that do not bind the relation). ATTEST-3 inverts the design: it accepts ONE positive construction and
nothing else. Frozen before its holdout (H2) existed. Changing any table below is a new version.

THE SUPPORTED CONSTRUCTION (all must hold, in one sentence of the text):
  1. QUOTATION is removed from the WHOLE text before it is split into sentences, so a quote that spans sentences is
     removed whole. An unbalanced double quote removes everything after it (fail closed).
  2. The sentence BEGINS with the trigger. Before it, only a closed set of discourse fillers may appear ("yes,",
     "honestly,", "these days", ...). Any other material before the trigger — "Suppose", "It is false that",
     "He wrote:", "Example sentence:", "I deny that" — puts the trigger inside another frame, and the sentence is
     not supported.
  3. The object is the trigger's COMPLETE complement: it follows the trigger (after an optional article) and is
     followed by the end of the sentence, by clause punctuation, or by a word from a closed list of function words
     (prepositions, conjunctions, time adverbs). A following content word ("dentist assistant"), a possessive
     ("dentist's receptionist") or a hyphen ("dentist-in-training") means the object named only part of what the
     speaker said.
  4. The trigger BINDS the relation. Specific triggers do so by themselves ("I work as", "I weigh", "I live in").
     Generic triggers ("I'm a", "I am", "I have") bind it only when the object is in that relation's closed lexicon
     (an occupation for works_as, a diet for has_diet, a condition for health_state, an animal for has_pet); for a
     relation with no lexicon, a generic trigger attests nothing.
  5. No negation, modality or reported-speech marker occurs in the sentence outside the trigger (ATTEST-2's lists,
     kept as defence in depth), the sentence is not a question, and NO sentence of the event retracts it ("just
     kidding", "not really", ...).

Scope (stated, not implied):
  * subject 'user' only — first-person statements by the speaker. Any other subject → UNSUPPORTED.
  * declarative relations only; the procedural path is 0037's and is exempt (never passed here).
  * the raw event text as received by ingest (not an extractor-written episode summary).
  * double quotes only: single quotes cannot be told from apostrophes, so a single-quoted passage is NOT removed.
"""
import re

VERSION = "ATTEST-3"

# Relation -> (specific triggers, generic triggers). A specific trigger binds the relation by itself; a generic one
# binds it only through LEXICON[relation]. Relations absent here are UNSUPPORTED in this version.
TRIGGERS = {
    "works_as": (["i work as", "i'm employed as", "i am employed as", "my job is", "i work at", "i work for",
                  "i'm employed at", "i am employed at", "i'm employed by", "i am employed by"],
                 ["i'm a", "i am a", "i'm an", "i am an"]),
    "measures": (["i weigh", "my weight is", "i've saved", "i have saved", "my savings are", "i'm on page",
                  "i am on page", "my score is", "i scored"], []),
    "prefers": (["i prefer", "i'd rather", "my favorite", "my favourite"], ["i like", "i love"]),
    "located_at": (["i live in", "i'm based in", "i am based in", "i live at", "i moved to"], []),
    "health_state": (["i was diagnosed with", "i've been diagnosed with", "i have been diagnosed with",
                      "i suffer from", "i'm recovering from", "i am recovering from"],
                     ["i have", "i've got"]),
    "has_pet": (["my dog", "my cat", "my pet"], ["i have a", "i've got a", "i have an", "i've got an"]),
    "has_diet": (["i follow", "i'm on a", "i am on a"], ["i'm", "i am", "i eat", "i keep"]),
    "partner_of": (["my partner", "my wife", "my husband", "my girlfriend", "my boyfriend", "my fiancé",
                    "my fiance", "my fiancée", "my fiancee", "i'm married to", "i am married to"], []),
    "relative_of": (["my mother", "my mom", "my mum", "my father", "my dad", "my sister", "my brother", "my son",
                     "my daughter", "my aunt", "my uncle", "my cousin", "my grandmother", "my grandfather"], []),
    "works_on": (["i'm working on", "i am working on", "i work on", "my project is"], []),
    "client_of": (["my client is", "i'm a client of", "i am a client of"], []),
    "uses_tool": (["i use", "i'm using", "i am using", "i rely on"], []),
    "avoids_tool": (["i avoid", "i don't use", "i do not use", "i stopped using", "i never use"], []),
}

# Closed lexicons through which a GENERIC trigger binds its relation. Membership is by the normalized object. A
# relation whose generic triggers have no lexicon here gets nothing from them ("prefers" via "I like": liking is not
# preferring a named thing over others — kept generic-with-no-lexicon deliberately, so it never attests).
LEXICON = {
    "works_as": {
        "accountant", "actor", "actress", "administrator", "analyst", "architect", "artist", "assistant",
        "attorney", "auditor", "baker", "banker", "barber", "barista", "bartender", "bookkeeper", "builder",
        "bus driver", "butcher", "carpenter", "cashier", "chef", "chemist", "cleaner", "clerk", "coach", "consultant",
        "cook", "counselor", "counsellor", "courier", "data analyst", "data scientist", "dental hygienist",
        "dental technician", "dentist", "designer", "developer", "dietitian", "doctor", "driver", "economist",
        "editor", "electrician", "engineer", "farmer", "firefighter", "flight attendant", "gardener",
        "graphic designer", "hairdresser", "historian", "illustrator", "interpreter", "janitor", "journalist",
        "judge", "landscaper", "lawyer", "lecturer", "librarian", "lifeguard", "machinist", "manager", "marketer",
        "mechanic", "midwife", "musician", "nanny", "night auditor", "nurse", "nutritionist", "optometrist",
        "painter", "paralegal", "paramedic", "pharmacist", "photographer", "physician", "physicist",
        "physiotherapist", "physical therapist", "pilot", "plumber", "police officer", "postman", "producer",
        "product manager", "professor", "programmer", "project manager", "psychiatrist", "psychologist",
        "radiographer", "real estate agent", "receptionist", "recruiter", "researcher", "sales rep", "salesperson",
        "scientist", "secretary", "security guard", "social worker", "software developer", "software engineer",
        "solicitor", "surgeon", "surveyor", "tailor", "teacher", "technician", "therapist", "translator",
        "truck driver", "tutor", "veterinarian", "vet", "waiter", "waitress", "web developer", "welder", "writer",
    },
    "has_diet": {
        "vegan", "vegetarian", "pescatarian", "pescetarian", "keto", "ketogenic", "paleo", "gluten-free",
        "dairy-free", "lactose-free", "halal", "kosher", "plant-based", "low-carb", "low carb", "carnivore",
        "flexitarian", "raw vegan", "whole30", "fodmap", "low-fodmap", "intermittent fasting",
    },
    "health_state": {
        "asthma", "diabetes", "type 1 diabetes", "type 2 diabetes", "celiac", "coeliac", "celiac disease",
        "coeliac disease", "adhd", "autism", "anxiety", "depression", "migraines", "migraine", "epilepsy",
        "arthritis", "eczema", "psoriasis", "hypertension", "high blood pressure", "ibs", "crohn's",
        "crohn's disease", "lupus", "ms", "multiple sclerosis", "copd", "long covid", "covid", "a cold", "the flu",
        "flu", "insomnia", "sleep apnea", "sleep apnoea", "tinnitus", "fibromyalgia", "endometriosis", "pcos",
        "gout", "anemia", "anaemia", "hypothyroidism", "hyperthyroidism", "a peanut allergy", "allergies",
        "hay fever", "back pain", "chronic pain", "a broken arm", "a broken leg", "ptsd", "ocd", "bipolar disorder",
        "dyslexia", "cancer", "osteoporosis", "scoliosis", "a concussion", "covid-19",
    },
    "has_pet": {
        "dog", "cat", "puppy", "kitten", "rabbit", "bunny", "hamster", "guinea pig", "parrot", "budgie", "bird",
        "fish", "goldfish", "turtle", "tortoise", "snake", "lizard", "gecko", "ferret", "horse", "pony", "rat",
        "mouse", "chinchilla", "hedgehog", "cockatiel", "bearded dragon",
    },
}

# Before the trigger, only these may appear (after normalization, as whole words, optionally followed by commas).
FILLERS = {"yes", "yeah", "yep", "honestly", "well", "so", "oh", "ok", "okay", "actually", "btw", "fyi", "fwiw",
           "also", "and", "but", "currently", "now", "right now", "these days", "nowadays", "today", "hi", "hey",
           "hello", "ah", "um", "uh", "anyway", "anyways", "basically", "in fact", "for the record"}

# After the object, the complement is complete only if the next word is one of these (or punctuation, or the end).
FOLLOWERS = {"at", "in", "for", "with", "since", "and", "but", "so", "because", "from", "on", "near", "by", "here",
             "now", "today", "currently", "these", "this", "nowadays", "full", "part", "too", "as", "until",
             "though", "then", "which", "who", "lol", "haha", "btw", "fyi", "i", "it", "my", "a", "an", "the",
             "every", "most", "all", "per", "named", "called", "last", "whenever", "daily", "weekly", "often",
             "mostly", "regularly", "always", "nearby", "is", "lives", "has", "works", "so"}
# relation-specific head nouns that may follow the object ("a keto DIET")
REL_FOLLOWERS = {"has_diet": {"diet"}}

NEGATION = [r"\bnot\b", r"n't\b", r"\bnever\b", r"\bno longer\b", r"\bnobody\b", r"\bnone\b"]
MODALITY = [r"\bif\b", r"\bwould\b", r"\bcould\b", r"\bmight\b", r"\bmay\b", r"\bmaybe\b", r"\bperhaps\b",
            r"\bwant to\b", r"\bwants to\b", r"\bhope to\b", r"\bplan to\b", r"\bplanning to\b",
            r"\bthinking about\b", r"\bconsidering\b", r"\bshould\b", r"\bused to\b", r"\bwill\b", r"\bgoing to\b"]
REPORTED = [r"\bsaid\b", r"\bsays\b", r"\btold me\b", r"\baccording to\b", r"\bthinks\b", r"\bbelieves\b",
            r"\bclaims\b"]
# a sentence anywhere in the event that takes the statement back
RETRACTIONS = [r"\bjust kidding\b", r"\bjk\b", r"\bkidding\b", r"\bnot really\b", r"\bi lied\b",
               r"\bthat's not true\b", r"\bthat is not true\b", r"\bnot true\b", r"/s\b", r"\bjoking\b"]

_ARTICLE = re.compile(r"^(?:a|an|the)\s+")
_QUOTE_CHARS = "\"“”"


def _norm(s: str) -> str:
    """The enumerated normalizations, and only these: case-fold; curly apostrophes to straight; whitespace
    collapsed; spacing between a number and a UNIT from a closed list removed (78 kg == 78kg; ATTEST-2 joined any
    following letters, so "4200 so far" became "4200so far"); trailing sentence punctuation stripped."""
    s = s.replace("’", "'").replace("‘", "'").lower()
    s = re.sub(r"(\d)\s+(kg|kgs|lb|lbs|g|mg|cm|mm|m|km|mi|ft|in|k|%|usd|eur|gbp|aud)\b", r"\1\2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(".!?;,: ")


def _norm_object(o: str) -> str:
    return _ARTICLE.sub("", _norm(o))


def strip_quotes(text: str) -> str:
    """Remove every double-quoted span from the WHOLE text, before sentence splitting. Curly and straight quotes are
    one class. An unbalanced quote removes everything after it (fail closed)."""
    out, inside = [], False
    for ch in text:
        if ch in _QUOTE_CHARS:
            inside = not inside
            out.append(" ")
            continue
        if not inside:
            out.append(ch)
    return "".join(out)


def sentences(text: str):
    """Deterministic segmentation: split on . ! ? ; and newlines. A question keeps its '?' so it can be recognised."""
    parts = re.split(r"(?<=[.!;])\s+|(?<=\?)\s+|\n+", text.strip())
    return [p for p in (x.strip() for x in parts) if p]


def _prefix_ok(prefix: str) -> bool:
    """Only closed-set fillers may precede the trigger."""
    rest = prefix.strip(" ,:-")
    while rest:
        for f in sorted(FILLERS, key=len, reverse=True):
            if rest == f or rest.startswith(f + " ") or rest.startswith(f + ","):
                rest = rest[len(f):].strip(" ,")
                break
        else:
            return False
    return True


def _complement_complete(after_obj: str, relation: str) -> bool:
    """The object is the WHOLE complement: what follows it is the end, clause punctuation, or a closed function word."""
    if after_obj == "":
        return True
    if after_obj[0] in "'-" or after_obj.startswith("’"):
        return False                                        # possessive or hyphenated: the object was a prefix
    if after_obj[0] in ",;:.!?)":
        return True
    if not after_obj[0].isspace():
        return False
    nxt = re.match(r"\s+([a-z0-9][a-z0-9']*)", after_obj)
    if not nxt:
        return True
    word = nxt.group(1)
    return word in FOLLOWERS or word in REL_FOLLOWERS.get(relation, set())


def attests(subject: str, relation: str, obj: str, event_text: str) -> str:
    """Returns 'ATTESTED', 'NOT_ATTESTED' or 'UNSUPPORTED'. The caller treats UNSUPPORTED as not attested."""
    if subject != "user" or relation not in TRIGGERS:
        return "UNSUPPORTED"
    if not event_text or not event_text.strip() or not obj or not obj.strip():
        return "NOT_ATTESTED"
    want = _norm_object(obj)
    specific, generic = TRIGGERS[relation]
    if want not in LEXICON.get(relation, set()):
        generic = []                                        # a generic trigger binds the relation only via its lexicon
    unquoted = strip_quotes(event_text)
    sents = sentences(unquoted)
    if any(re.search(p, _norm(x)) for x in sents for p in RETRACTIONS):
        return "NOT_ATTESTED"                               # the event takes something back: attest nothing from it
    for raw in sents:
        if raw.rstrip().endswith("?"):
            continue                                        # a question asserts nothing
        s = _norm(raw)
        for trig in sorted(specific + generic, key=len, reverse=True):
            for m in re.finditer(r"(?<![a-z'])" + re.escape(trig) + r"(?![a-z])", s):
                if not _prefix_ok(s[:m.start()]):
                    continue                                # the trigger sits inside another frame
                rest = s[m.end():].lstrip(" ,:")
                rest = _ARTICLE.sub("", rest)
                if not rest.startswith(want):
                    continue
                if not _complement_complete(rest[len(want):], relation):
                    continue
                outside = s[:m.start()] + " " + s[m.end():]
                if any(re.search(p, outside) for p in NEGATION + MODALITY + REPORTED):
                    continue
                return "ATTESTED"
    return "NOT_ATTESTED"
