"""specs/0037 v19–v21 §4a-iii — the gates a procedural CAPTURE must pass, as pure
functions over strings (no store, no model, no I/O), so the spec's order of
operations is the code's: NORMALISE → SUBSTRING → GRAMMAR (over the span plus
its left context) → DERIVE (the stored gloss from the span, v21: one cut) → the
summary contract on the derived text. Every gate is
RESTRICT-ONLY: it can refuse a capture, never admit one the previous gate
refused, and a refusal is counted by the caller (`procedural_refused`).

Why each gate exists is the round-1 and round-2 returns and research's red
teams of their closures (2026-09-13): the quote gate proved that words
APPEARED in a user-authored event and nothing more — not who the routine
belongs to (V-ACTOR-PRESENT), not whether the span was lifted from inside a
quoted third party speaking in the first person (the left-context frame
check); and a model's summary of the span could not be trusted to describe it
(V-GLOSS-GROUNDED, v19, RETIRED at v21 — the summary is now DERIVED from the
span, V-GLOSS-DERIVED, so there is nothing to ground). The residual of each
gate is named in the spec with the measured rate; a false REFUSAL is the safe
direction and the feature's cost.

v20 (the owner's word, 2026-09-13, on research's reading of the held-out failure):
the grammar is POSITIVE-FORM. A marker list enumerates surface forms of a
semantic property and lags a criterion permanently (the held-out draw's three
"I'm thinking of" intentions were not in any list, including the rater's own
rubric); so the gate now REQUIRES an explicit assertion of current repeated
performance — an enumerated head shape with an ACTION verb at the head of the
SPAN — and every form nobody enumerated fails CLOSED. The negative markers are
kept as defence in depth; removing working code to make a point is not an
improvement.
"""
from __future__ import annotations

import re
from typing import Optional

# --------------------------------------------------------------- normalisation
def norm_ws(text: str) -> str:
    """Inner-whitespace collapse ONLY (no casefold, no punctuation strip) — the
    one normaliser every gate and the substring check run over. v22
    (research): a non-string is REFUSED, never coerced — `str(None)` is the
    plausible span "None", and a missing event once refused a capture under
    the content verdict `quote_not_in_event` instead of the truth."""
    if not isinstance(text, str):
        raise TypeError(f"norm_ws expects a str, got {type(text).__name__}")
    return " ".join(text.split())


# ------------------------------------------------------- V-ACTOR-PRESENT (grammar)
# The span must OPEN with the user as the actor, in the present or habitual:
# an optional leading temporal/conditional clause, then a first-person
# SINGULAR pronoun (research §5: "we" is a team policy, not the user), an
# optional auxiliary ("I've", "I have", "I am", "I'm"), optional "been", an
# optional frequency adverb, then a word.
# v22 (round-3 F2's class in the lead clause): a SUBORDINATE lead clause must
# END AT A COMMA — "If I review invoices daily, the queue stays short." used
# to match with the lead consuming only "If " and the head reading the
# conditional's own "I review…" as the assertion. A frequency lead ("Every
# Friday I review the invoices") needs no comma. Measured before choosing: no
# clean positive in 400 sessions opens with a subordinate lead; three
# must-refuse spans open with "if".
_LEAD = r"(?:(?:every|each)\s+\w+,?\s+|(?:before|after|when|whenever|once|on|at|during|while|if)\b[^,]{0,80},\s+)?"
_HEAD = re.compile(
    _LEAD + r"I(?:'ve|'m| have| am)?\s+(?:been\s+)?"
    r"(?:always|usually|typically|often|regularly|routinely|generally|normally|habitually|never|rarely|every \w+|each \w+)?\s*"
    r"[A-Za-z]",
    re.I)
# Markers anywhere in the span that make the words something other than the
# user asserting a current routine of their own. Classes, each with the case
# that put it here: REPORT (Marcus told me), REJECTION (I refuse), ASPECT
# (used to / keep meaning to), NORM (the team standard is / required me to),
# REQUEST (please — the reviewer's one-time instruction), ASPIRATION (I try
# to / I mean to — research §5's sixth class), QUESTION.
_MARKERS = re.compile(
    r"\b(?:told me|tells me|telling me|asked me|asks me|says?|said|according to|wrote|writes|read[s]?:|"
    r"refuse[sd]?|declin\w*|won't|don't want|do not want|stopped|quit|no longer|not anymore|"
    r"used to|keep meaning|kept meaning|mean to|meant to|want to|wanted to|plan to|planning to|going to|"
    r"should|ought to|supposed to|required to|require[sd]? me|the (?:team |company |house |shop )?(?:standard|rule|policy|norm) is|"
    r"please|kindly|"
    r"try to|tried to|trying to|aim to|hope to|hoping to|intend to|wish|would like to|"
    r"just|did|was|were|had to|have had to|have to|once)\b|\?",
    re.I)
# PAST TENSE after the head is not a current routine (research's labelled set,
# #5 "I just used…" and #18 "I did have to…", both one-time actions): the first
# verb after the pronoun group must not be a simple-past form unless the head
# carried "been" (present perfect progressive is habitual).
_PAST_VERB = re.compile(
    r"^" + _LEAD + r"I(?:'ve| have)?\s+(?!been\b)(?:always|usually|typically|often|regularly|routinely|generally|normally|habitually|never|rarely)?\s*"
    r"(?:[a-z]+ed|went|made|took|got|gave|came|ran|saw|did|had|was|were|wrote|read|said|told|bought|built|sent|spent|kept|left|put|set|cut|hit|let|found|thought|brought|began|started)\b",
    re.I)
# A preceding QUOTATION or ATTRIBUTION frame in the event text (research §2):
# the span was lifted from inside someone else's words. The left context is
# bounded; an opening quote mark with no closing mark before the span, a
# colon, or a report verb immediately before the span refuses.
_FRAME_TAIL = re.compile(
    r"(?:[\"'“‘«]|:|\b(?:said|says|wrote|writes|reads?|read|told me|tells me|asked me|according to|from the \w+|quote[sd]?|"
    r"message|email|mail|text|note|memo|post|letter)\b[^.]{0,30})\s*$",
    re.I)
_QUOTE_CHARS = "\"'“‘«"


def _inside_open_quote(left: str) -> bool:
    """True when the left context opened a quotation it never closed."""
    opens = sum(left.count(c) for c in _QUOTE_CHARS)
    closes = sum(left.count(c) for c in "\"'”’»")
    # straight quotes count on both sides; an odd total means one is open
    straight = left.count('"') + left.count("'")
    curly_open = left.count("“") + left.count("‘") + left.count("«")
    curly_close = left.count("”") + left.count("’") + left.count("»")
    return (straight % 2 == 1) or (curly_open > curly_close)


# ------------------------------------------- V-ACTOR-PRESENT, v20: the POSITIVE form
# The span must OPEN (after the optional lead clause) with one of THREE enumerated
# head shapes, each ending in a lexical verb whose STEM is an ACTION head:
#   PS   present simple            I [don't|do not|never|ADV] V        "I use it to…"
#   PPC  present perfect continuous I've|I have been [ADV] V-ing         "I've been using…"
#   PROG present progressive        I'm|I am [ADV] V-ing  + a FREQUENCY marker anywhere
#                                                                      "I'm walking the dog every morning"
# Anything else — a modal or auxiliary head ("I can", "I will", "I have a…", "I do
# the dishes"), a bare progressive ("I'm building a deck": one ongoing activity),
# a present perfect without "been" ("I've always run…"), a cognitive or
# volitional head ("I'm thinking of…", "I've been trying to…", "I want to…") —
# is NOT an explicit assertion of current repeated performance and FAILS CLOSED.
# The head verb is the SPAN's head, never a later clause's (research: clause-any
# reopens the complement construction "I'm thinking of dedicating a day each
# week…", the form that defeated v19). The excluded verb class is matched by
# CLASS through the symmetric light stem `_stem`, so every inflection
# of "think" meets "think".
_ADV = r"(?:always|usually|typically|often|regularly|routinely|generally|normally|habitually|never|rarely|sometimes|mostly|frequently|occasionally)"
_PS = re.compile(r"^" + _LEAD + r"I\s+(?:(?:don't|do not|never|" + _ADV + r")\s+)?([A-Za-z]+)\b", re.I)
_PPC = re.compile(r"^" + _LEAD + r"I(?:'ve|\s+have)\s+been\s+(?:" + _ADV + r"\s+)?([A-Za-z]+ing)\b", re.I)
_PROG = re.compile(r"^" + _LEAD + r"I(?:'m|\s+am)\s+(?:" + _ADV + r"\s+)?([A-Za-z]+ing)\b", re.I)
_FREQ = re.compile(r"\b(?:every \w+|each \w+|daily|weekly|monthly|nightly|hourly|twice a|once a|three times a|always|usually|regularly|routinely|often|whenever|"
                   r"on (?:mon|tues|wednes|thurs|fri|satur|sun)days|(?:most |all |some )?(?:mornings|afternoons|evenings|nights|weekends|weekdays))\b", re.I)
# Modals and auxiliaries can head a sentence but never assert a performed action.
_AUX = {"am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "can", "could", "will", "would", "shall", "should", "may", "might", "must", "ought", "ll", "d"}
# Cognitive / volitional heads: the class, excluded by class (each entry stemmed
# at import so the comparison is stem-to-stem).
_COGNITIVE_WORDS = ("think", "mean", "hope", "plan", "consider", "want", "intend", "wish", "try", "aim",
                    "like", "love", "prefer", "need", "feel", "believe", "guess", "suppose", "wonder",
                    "decide", "figure", "imagine", "dream", "expect", "assume", "reckon", "contemplate",
                    "toy", "debate", "ponder", "muse",
                    # v24 (round-4 finding 3: "I doubt I review invoices daily." was a CLAIMED
                    # refusal with no code behind it): the epistemic heads that qualify rather
                    # than assert — doubt, deny, suspect, presume — join the class. NOT added,
                    # on research's constructed controls: "question" ("I question every invoice
                    # over $500."), "bet" ("I bet on horses every Saturday.") — ordinary routine
                    # senses; "figure"/"guess"/"reckon" were already here (a stated cost:
                    # "I figure out the totals every morning." refuses).
                    "doubt", "deny", "suspect", "presume",
                    "thought", "felt", "meant", "dreamt")   # irregular pasts of the class, which no stem reaches


def _head_verb(span: str):
    """The span-head lexical verb under one of the three enumerated shapes, or
    None. PROG requires a frequency marker somewhere in the span."""
    m = _PPC.match(span)
    if m:
        return m.group(1)
    m = _PROG.match(span)
    if m:
        return m.group(1) if _FREQ.search(span) else None
    m = _PS.match(span)
    if m:
        v = m.group(1)
        if v.lower().endswith("ing"):            # "I running" is no shape; "I'm" was PROG
            return None
        return v
    return None


def positive_form(span: str) -> bool:
    """v20: True only when the span opens with an enumerated head shape whose
    head verb is a lexical ACTION verb — not an auxiliary or modal, not in the
    cognitive/volitional class."""
    v = _head_verb(norm_ws(span))
    if v is None:
        return False
    low = v.lower()
    if low in _AUX:
        return False
    if _stem(low) in _DIRECTIVE:              # v21 (round-2 F2): "I request that you…" is a request
        return False
    if any(tok in _SECOND_PERSON for tok in tokens(span)):   # v21: a span addressed to someone is not the user's own routine
        return False
    return _stem(low) not in _COGNITIVE


def actor_present(span: str, event_text: Optional[str] = None, left_window: int = 120) -> bool:
    """The grammar. `span` is the (normalised) quoted span; when `event_text`
    is given the span's LEFT CONTEXT in the event is checked for a quotation
    or attribution frame (research §2: containment is not position)."""
    s = norm_ws(span)
    if not s or not _HEAD.match(s) or _MARKERS.search(s) or _PAST_VERB.match(s):
        return False
    if has_internal_boundary(s):              # v21/v24: a span is ONE plain sentence — a second sentence, an ambiguous
        return False                          # join or a question is not the same assertion (the kinds, gate-only)
    if not positive_form(s):                  # v20: fail CLOSED on every unenumerated form
        return False
    if event_text is not None:
        ev = norm_ws(event_text)
        i = ev.find(s)
        if i < 0:
            return False
        if not whole_sentence(s, ev, i):          # v22 (round-3 F2/F3): the span is ONE WHOLE SENTENCE of the event
            return False
        left = ev[max(0, i - left_window):i]
        if _FRAME_TAIL.search(left) or _inside_open_quote(left):
            return False
    return True


def whole_sentence(span: str, event: str, at: int) -> bool:
    """v22 (round-3 finding 2, "validate the selected passage's boundaries
    against the source"): the span at offset `at` of the normalised event must
    be exactly one whole sentence of it — it begins at the start of the event
    or immediately after sentence-final punctuation, and it ends at the end of
    the event, or at sentence-final punctuation it carries itself, or
    immediately before a plain `.`/`!` it omitted. v24 (round-4 findings 1a/1b/2):
    the boundaries are the KINDS of `boundary_kind`, read from the complete
    event — a decimal point is inside a sentence, `daily.archive` is an
    ambiguous join, an omitted `?` is never allowed and a sentence ending in
    `?` is a question and refuses whatever the span carries; the rule is
    per SENTENCE, never per event (a user turn that ends in a question to the
    assistant still yields its routine sentence). A fragment inside a framing
    sentence ("Imagine I always review invoices." → "I always review
    invoices") is not a sentence, whatever the frame says; two sentences are
    not one. Case decides nothing about admission; it only tells a boundary
    from an ambiguous join, and the ambiguous side refuses."""
    end = at + len(span)
    for s, run_start, run_end, kind, start_kind in sentence_segments(event):
        if s <= at < run_end or (kind == "eot" and s <= at):
            if at != s:                                   # a fragment, or a start mid-token ("$100.|50 daily")
                return False
            if start_kind not in ("sot", "boundary", "question"):   # v24.1 (round-5 F1): the START must follow an
                return False                              # ESTABLISHED boundary — a `?`/`!` run or the text's start,
                                                          # never an ambiguous run ("e.g. I…", "that... I…", "daily. I…")
            if kind in ("question", "ambiguous"):          # a question is not an assertion; a join the rule
                return False                              # cannot resolve is refused, never guessed
            if kind == "eot":
                return end == run_end                     # the sentence has no terminator: the span is all of it
            if end == run_end:                            # the span carries its own terminal run
                return True
            run = event[run_start:run_end]
            return end == run_start and run in (".", "!")  # the span may omit a plain `.`/`!` — never `?`, never a closer
    return False


# ------------------------------------------------ the tokenizer and its literal sets
# v21 (the owner's word, 2026-09-13: "I agree with the derivation recommendation"):
# there is NO grounding gate any more. v19 checked the model's gloss as an ordered
# subsequence of the span; the round-2 reviewer showed order is not meaning
# (a negation dropped by a curly apostrophe; "Reviews receipts" from "I review
# invoices and archive receipts"); v21's predicate-level grounding was built,
# measured and DELETED before landing, because each of substring → markers →
# positive form → predicates was a better syntactic approximation of a semantic
# property and none would be the last. The product now DERIVES the gloss from the
# span (`derive_gloss`), so there is nothing to ground. The tokenizer below is
# the one normaliser the grammar's literal sets AND the deriver read through.
_STOP = {"a", "an", "the", "my", "our", "your", "his", "her", "their", "its", "i", "we", "me", "us", "it", "them",
         "to", "of", "in", "on", "at", "by", "for", "with", "from", "into", "onto", "and", "or", "then",
         "is", "are", "am", "be", "been", "being", "do", "does", "did", "have", "has", "had", "ve", "m",
         "that", "this", "these", "those", "so", "as", "up", "out", "off", "over"}
_NEG = {"not", "never", "no", "nor", "n't", "dont", "doesnt", "didnt", "wont", "cant", "stopped", "quit", "longer", "anymore", "rarely", "seldom"}
_SUBORD = {"when", "whenever", "if", "unless", "before", "after", "while", "during", "until", "once", "only", "except"}


def _stem(tok: str) -> str:
    """A SYMMETRIC light stem (v19 served the grounding; v21 serves the grammar's
    verb classes): both sides of a comparison pass through it, so what matters is that inflections of one word meet, not that the
    result is a dictionary form (deletes/delete -> delet; merging/merges ->
    merg; committing/commit -> commit; invoices/invoice -> invoic)."""
    t = tok
    if t.endswith("ies") and len(t) > 4:
        t = t[:-3] + "y"
    else:
        for suf in ("ing", "ed", "s"):
            if t.endswith(suf) and len(t) - len(suf) >= 3 and not t.endswith("ss"):
                t = t[: -len(suf)]
                break
    if len(t) >= 4 and t[-1] == t[-2] and t[-1] not in "aeiou":   # committ -> commit
        t = t[:-1]
    if len(t) >= 4 and t.endswith("e"):                             # delete/merge -> delet/merg
        t = t[:-1]
    return t


_COGNITIVE = frozenset(_stem(w) for w in _COGNITIVE_WORDS)
# v21 (round-2 F2): DIRECTIVE heads — a first-person present-simple verb of
# requesting or directing is a speech act aimed at the addressee, not a routine
# of the speaker's; refused by class. And SECOND PERSON anywhere in the span:
# measured across the 121 labelled spans of three draws, you/your occurs in 0
# of 13 clean positives and 27 of 101 must-refuse spans, so the refusal costs
# nothing observed and closes the whole "I <verb> that you …" family.
_DIRECTIVE_WORDS = ("request", "ask", "suggest", "recommend", "tell", "remind", "urge", "order", "insist",
                    "propose", "advise", "instruct", "demand", "require", "invite", "encourage", "beg",
                    "command", "direct", "forbid", "permit", "allow", "authorise", "authorize")
_DIRECTIVE = frozenset(_stem(w) for w in _DIRECTIVE_WORDS)
_SECOND_PERSON = frozenset({"you", "your", "yours", "yourself", "yourselves", "u"})


_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "`": "'"})


def tokens(text: str) -> list:
    """Lowercased word tokens with a light suffix strip; contractions split.
    v21 (round-2 F1): curly and typographic apostrophes are normalised to the
    straight one FIRST — "don’t" tokenised as `don` + `t` lost the negation the
    grammar is matched against (the normaliser class: a haystack transform
    that rewrites a literal a pattern names makes the pattern unfirable)."""
    raw = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(text).lower().translate(_APOSTROPHES))
    out = []
    for r in raw:
        if "'" in r:
            base, tail = r.split("'", 1)
            if tail == "t":
                out.append(_CONTRACTED_AUX.get(base, base))    # doesn't -> does + n't
                out.append("n't")
            else:
                out.append(base)
                out.append(tail)
        else:
            out.append(r)
    return out


_CONTRACTED_AUX = {"don": "do", "doesn": "does", "didn": "did", "won": "will", "can": "can", "isn": "is",
                   "aren": "are", "wasn": "was", "weren": "were", "haven": "have", "hasn": "has", "hadn": "had",
                   "wouldn": "would", "couldn": "could", "shouldn": "should", "mustn": "must", "needn": "need",
                   "ain": "is", "shan": "shall", "mightn": "might"}


_COORD = {"and", "or", "but", "then", "plus", "also"}
# v21 (research's attack, first on the retired predicate grounding, then on the
# derived gloss itself): a RELATIVE or commentary clause
# ("…, which has been a great way to … and make progress on my book") is a
# predicate too, and a gloss built from it ("Makes progress on my book") is a
# fabrication with perfect provenance. Relative pronouns key their predicate
# like a subordinator, so a gloss's main-clause predicate can never match one.
_RELATIVE = {"which", "who", "whom", "whose", "where", "that"}
_FREQ_ADV = {"always", "usually", "typically", "often", "regularly", "routinely", "generally", "normally",
             "habitually", "sometimes", "mostly", "frequently", "occasionally", "daily", "weekly", "monthly",
             "nightly", "hourly", "everyday"}


# ----------------------------------------------------------- the DERIVED gloss (v21)
# The stored gloss is the user's sentence, whitespace-normalised, with ONE
# transformation: a comma-introduced RELATIVE clause is cut from its comma to
# the end ("…, which has been a great way to get some exercise and make
# progress on my book"), because printing the sixteen observed positives showed
# the commentary a paraphrase used to drop is otherwise ALWAYS stored. Nothing
# else: no contraction expanded, no subject dropped, no inflection. Two
# rejected designs, measured before choosing: dropping the subject "I" turns
# "I always run the linter before merging" into an IMPERATIVE-shaped fragment
# that describe's frozen executable-detail floor WITHHOLDS (the reviewer's
# cases and the present-simple positives all vanished from describe), and
# expanding contractions was only ever needed to repair that dropping. describe
# prefixes "recorded from something you said:", so the first-person sentence
# reads as the quotation it is.
# v22 (round-3 F3): a sentence terminator followed by whitespace and ANY
# character is a boundary — the v21 pattern required an uppercase letter or an
# opening quote after it, so "daily. archive receipts" read as one sentence.
_TERMINAL = ".!?"
# v24 (round-4 findings 1a, 1b, 2 — one root cause: the v22 rule tested CHARACTERS,
# `[.!?]`, not sentence boundaries; a decimal point counted as sentence-final, a
# terminator with no following space did not, and a span could stop one character
# short of its own `?`). A boundary is a KIND read from the complete event, and the
# kinds are TOTAL over what can follow a terminator run — anything unrecognised is
# AMBIGUOUS and refuses (fail closed), never a boundary by default.
# v24.1 (round-5 finding 2; the owner's word, 2026-09-14: "Fail closed"): a boundary
# is ESTABLISHED only where the language leaves no doubt — the start or end of the
# text, or a `?`/`!` run followed by a sentence start. A MID-TEXT PERIOD ESTABLISHES
# NOTHING in either direction: it may be a sentence end or an abbreviation ("in env.
# Prod only after approval"), and the abbreviation list v24 carried could not
# establish which (the reviewer: no list can; research: no list-free rule can
# either). The list is gone. The cost is structural and stated in 0037 §8: a routine
# sentence followed by a period-terminated neighbour is not capturable.
_CLOSERS = "\"')]\u201d\u2019"
_OPENERS = "\"'([\u201c\u2018"
def _run_end(text: str, i: int) -> int:
    """`text[i]` is a terminator: the index just past the terminal run — the
    terminators, then any closing quotes/brackets that belong to the sentence."""
    j = i
    while j < len(text) and text[j] in _TERMINAL:
        j += 1
    while j < len(text) and text[j] in _CLOSERS:
        j += 1
    return j



def boundary_kind(text: str, i: int) -> str:
    """The KIND of the terminal run starting at `text[i]` (a terminator):
      question  — the run carries `?`: the sentence it ends is a question (refused
                  as an assertion); the run still ESTABLISHES the start of what follows
      inside    — a `.` between two digits (a decimal point), no run at all
      boundary  — ESTABLISHED: the run ends the text (any terminator; a closing quote
                  or bracket may follow), or it is a `!` run followed by whitespace and
                  then an uppercase letter, a digit or an opening quote/bracket
      ambiguous — everything else, refused rather than guessed: EVERY mid-text period
                  (a sentence end or an abbreviation — `in env. Prod`, `9 a.m. every`,
                  `daily. archive`, `daily.archive` — the rule cannot tell and no list
                  can, v24.1), an ellipsis, a `!` followed by anything but a sentence
                  start."""
    j = _run_end(text, i)
    run_terms = text[i:j].rstrip(_CLOSERS)
    if run_terms.count(".") >= 2:
        return "ambiguous"
    if (text[i] == "." and len(run_terms) == 1 and i + 1 < len(text) and text[i + 1].isdigit()
            and i > 0 and text[i - 1].isdigit()):
        return "inside"
    # v24.2 (round-6 finding 1): what FOLLOWS the run decides whether it establishes
    # the next start, whatever the run's marks — the question branch used to return
    # before looking ("Any tips?I review…" admitted; the `!` form refused)
    if j >= len(text):
        established = True
    elif "." in run_terms or not text[j].isspace():
        established = False                       # a mid-text period establishes nothing; no separator, no start
    else:
        k = j
        while k < len(text) and text[k].isspace():
            k += 1
        c = text[k] if k < len(text) else ""
        established = (k >= len(text)) or c.isupper() or c.isdigit() or c in _OPENERS
    if "?" in run_terms:
        return "question" if established else "ambiguous"
    return "boundary" if established else "ambiguous"


_PAIRS = {")": "(", "]": "[", "}": "{"}
_QUOTES = {'"': '"', "\u201c": "\u201d"}


def enclosure_structure(text: str):
    """v24.3 (round-7 finding 1): the enclosure structure of `text`, or None when it
    cannot be ESTABLISHED. Parentheses, brackets and braces must nest and match
    by type (a `]` closing a `(` is a mismatch); characters inside a quoted literal
    (`"…"` or curly quotes) are inert — a quoted `"]"` or `")"` closes nothing; an
    unclosed opener or an unbalanced double quote leaves the structure
    unestablished. Returns a list of booleans, one per character: True where the
    character sits inside an enclosure or a quoted literal (a terminator there ends
    nothing)."""
    inside = [False] * len(text)
    stack: list = []
    quote_close = None
    for i, ch in enumerate(text):
        if quote_close is not None:
            inside[i] = True
            if ch == quote_close:
                quote_close = None
            continue
        if ch in _QUOTES:
            quote_close = _QUOTES[ch]
            inside[i] = True
            continue
        if ch in "([{":
            stack.append(ch)
            inside[i] = True
            continue
        if ch in _PAIRS:
            if not stack or stack[-1] != _PAIRS[ch]:
                return None                                   # a mismatch or a stray closer
            stack.pop()
            inside[i] = True
            continue
        inside[i] = bool(stack)
    if stack or quote_close is not None:
        return None                                           # an unclosed opener or quote
    return inside


def sentence_segments(text: str):
    """The text cut at every terminal run that is not `inside`: a list of
    (start, run_start, run_end, kind, start_kind) — `kind` is the run's kind,
    or "eot" for a final segment with no terminator; `start_kind` is the kind
    of the run the segment FOLLOWS ("sot" for the start of the text). v24.1
    (round-5 finding 1): a segment that follows an ambiguous run ("e.g. I
    review…", "imagining that... I review…") is cut off from its qualifying
    context and is not a valid start — `whole_sentence` reads `start_kind`.
    v24.2/v24.3: a terminator inside an enclosure or a quoted literal ends
    nothing; when the enclosure structure cannot be established (a mismatch,
    a stray closer, an unclosed opener or quote) EVERY segment is returned
    ambiguous with an ambiguous start — the passage is declined, never
    guessed. `start` skips leading whitespace."""
    segs, start, start_kind, i, n = [], 0, "sot", 0, len(text)
    inside = enclosure_structure(text)
    established = inside is not None
    if not established:
        inside = [False] * n
    while i < n:
        ch = text[i]
        if ch in _TERMINAL and inside[i]:         # inside "(…)" or "…": the run is inert
            i += 1
            continue
        if text[i] in _TERMINAL and (i == 0 or text[i - 1] not in _TERMINAL):
            kind = boundary_kind(text, i)
            if kind == "inside":
                i += 1
                continue
            end = _run_end(text, i)
            s = start
            while s < i and text[s].isspace():
                s += 1
            segs.append((s, i, end, kind, start_kind))
            start, start_kind, i = end, kind, end
            continue
        i += 1
    s = start
    while s < n and text[s].isspace():
        s += 1
    if s < n:
        segs.append((s, n, n, "eot", start_kind))
    if not established:                           # v24.3: unestablished structure declines every segment
        segs = [(a, b, c, "ambiguous", "ambiguous") for (a, b, c, _k, _sk) in segs]
    return segs


def has_internal_boundary(span: str) -> bool:
    """v24: the gate-only reading of the same kinds — any terminal run before
    the span's own last one, or an ambiguous/question last run, means the span
    is not one plain sentence."""
    segs = sentence_segments(span)
    if len(segs) > 1:
        return True
    return bool(segs) and segs[0][3] in ("ambiguous", "question")


def derive_gloss(span: str) -> str:
    """specs/0037 v22 §4a-iii Gate 4 — the stored gloss IS the verified span,
    whitespace-normalised, and nothing else. v21 cut a comma-introduced
    relative clause to the end of the span; the round-3 reviewer showed that a
    relative clause can sit MID-sentence ("I review invoices, which arrive
    daily, only after approval" lost its condition), so the one transformation
    is withdrawn: the user's sentence is stored as the user wrote it, and
    trailing commentary is a stated cost rather than a meaning change."""
    return norm_ws(span)


# ------------------------------------------------ the normaliser preserves its literals
def literals_survive_normalisation() -> list:
    """v21 (research, round-2 F1 generalised): every literal the grammar or the
    grammar matches against must come back from `tokens()` as itself — a
    tokenizer that rewrites a literal makes the pattern naming it unfirable
    (the curly apostrophe made "don’t" unfirable as a negation). Returns the
    literals that do NOT survive; the test asserts it is empty."""
    bad = []
    sets = [_NEG, _STOP, _SUBORD, _COORD, _FREQ_ADV, _RELATIVE, _SECOND_PERSON,
            set(_COGNITIVE_WORDS), set(_DIRECTIVE_WORDS), set(_ADV.strip("(?:)").split("|"))]
    for s in sets:
        for lit in s:
            if lit == "n't":
                if tokens("don't")[-1] != "n't" or tokens("don’t")[-1] != "n't":
                    bad.append(lit)
                continue
            if not lit.isalpha():
                continue
            if tokens(lit) != [lit]:
                bad.append(lit)
    return bad


# --------------------------------------------------------- the gate, in spec order
def check_capture(span, event_text: str, *, max_summary_chars: int) -> tuple:
    """Runs the gates in the spec's order and returns (accepted, reason,
    derived_gloss, normalised_span). `reason` names the first failing gate:
    no_quote | no_event | quote_not_in_event | actor_absent | summary_contract;
    None when accepted — total over the inputs (v22). The model's own gloss is not an input: v21 derives the stored
    gloss from the span."""
    if not isinstance(span, str):
        return (False, "no_quote", None, None)
    s = norm_ws(span)
    if not s:
        return (False, "no_quote", None, None)
    if not isinstance(event_text, str) or not event_text.strip():
        return (False, "no_event", None, s)       # v22: the vocabulary is TOTAL over the inputs — a missing event is its own outcome
    ev = norm_ws(event_text)
    if s not in ev:
        return (False, "quote_not_in_event", None, s)
    if not actor_present(s, ev):
        return (False, "actor_absent", None, s)
    g = derive_gloss(s)
    if not g or len(g) > max_summary_chars:          # the summary contract, applied to the DERIVED gloss
        return (False, "summary_contract", g, s)
    return (True, None, g, s)
