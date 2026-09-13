"""specs/0037 v19 §4a-iii — the gates a procedural CAPTURE must pass, as pure
functions over strings (no store, no model, no I/O), so the spec's order of
operations is the code's: NORMALISE → SUBSTRING → GRAMMAR (over the span plus
its left context) → GROUNDING (the gloss against the span). Every gate is
RESTRICT-ONLY: it can refuse a capture, never admit one the previous gate
refused, and a refusal is counted by the caller (`procedural_refused`).

Why each gate exists is the round-1 return and research's red team of its
closure (2026-09-13): the quote gate proved that words APPEARED in a
user-authored event and nothing more — not who the routine belongs to
(V-ACTOR-PRESENT), not whether the gloss describes the quoted words
(V-GLOSS-GROUNDED), not whether the span was lifted from inside a quoted
third party speaking in the first person (the left-context frame check).
The residual of each gate is named in the spec with the measured rate; a
false REFUSAL is the safe direction and the feature's cost.
"""
from __future__ import annotations

import re
from typing import Optional

# --------------------------------------------------------------- normalisation
def norm_ws(text) -> str:
    """Inner-whitespace collapse ONLY (no casefold, no punctuation strip) — the
    one normaliser every gate and the substring check run over."""
    return " ".join(str(text).split())


# ------------------------------------------------------- V-ACTOR-PRESENT (grammar)
# The span must OPEN with the user as the actor, in the present or habitual:
# an optional leading temporal/conditional clause, then a first-person
# SINGULAR pronoun (research §5: "we" is a team policy, not the user), an
# optional auxiliary ("I've", "I have", "I am", "I'm"), optional "been", an
# optional frequency adverb, then a word.
_LEAD = r"(?:(?:before|after|when|whenever|once|every|each|on|at|during|while|if)\b[^,]{0,80},?\s+)?"
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


def actor_present(span: str, event_text: Optional[str] = None, left_window: int = 120) -> bool:
    """The grammar. `span` is the (normalised) quoted span; when `event_text`
    is given the span's LEFT CONTEXT in the event is checked for a quotation
    or attribution frame (research §2: containment is not position)."""
    s = norm_ws(span)
    if not s or not _HEAD.match(s) or _MARKERS.search(s) or _PAST_VERB.match(s):
        return False
    if event_text is not None:
        ev = norm_ws(event_text)
        i = ev.find(s)
        if i < 0:
            return False
        left = ev[max(0, i - left_window):i]
        if _FRAME_TAIL.search(left) or _inside_open_quote(left):
            return False
    return True


# ------------------------------------------------------ V-GLOSS-GROUNDED (grounding)
_STOP = {"a", "an", "the", "my", "our", "your", "his", "her", "their", "its", "i", "we", "me", "us", "it", "them",
         "to", "of", "in", "on", "at", "by", "for", "with", "from", "into", "onto", "and", "or", "then",
         "is", "are", "am", "be", "been", "being", "do", "does", "did", "have", "has", "had", "ve", "m",
         "that", "this", "these", "those", "so", "as", "up", "out", "off", "over"}
_NEG = {"not", "never", "no", "nor", "n't", "dont", "doesnt", "didnt", "wont", "cant", "stopped", "quit", "longer", "anymore", "rarely", "seldom"}
_SUBORD = {"when", "whenever", "if", "unless", "before", "after", "while", "during", "until", "once", "only", "except"}


def _stem(tok: str) -> str:
    """A SYMMETRIC light stem: both sides of the grounding check pass through
    it, so what matters is that inflections of one word meet, not that the
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


def tokens(text: str) -> list:
    """Lowercased word tokens with a light suffix strip; contractions split."""
    raw = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(text).lower())
    out = []
    for r in raw:
        if "'" in r:
            base, tail = r.split("'", 1)
            out.append(base)
            out.append("n't" if tail == "t" else tail)
        else:
            out.append(r)
    return out


def _content(toks: list) -> list:
    return [_stem(t) for t in toks if t not in _STOP and t != "n't"]


def gloss_grounded(gloss: str, span: str) -> bool:
    """The gloss must DESCRIBE the quoted span: every content token of the
    gloss occurs in the span (containment), in the SAME ORDER (a subsequence,
    research §3), the gloss carries every negation the span carries and every
    subordinator the span carries (research §3/§4: a gloss may not drop a
    'never', nor a 'when …' that made the practice conditional), and the gloss
    is not empty of content."""
    g_toks, s_toks = tokens(gloss), tokens(span)
    g, s = _content(g_toks), _content(s_toks)
    if not g:
        return False
    # FREQUENCY PHRASES ("every Friday", "each morning") are position-free
    # adverbials: checked by CONTAINMENT only, then removed before the order
    # check, so "Every Friday I review the invoices" grounds "Reviews the invoices
    # every Friday".
    def split_freq(toks):
        bag, rest, i = [], [], 0
        while i < len(toks):
            if toks[i] in ("every", "each") and i + 1 < len(toks):
                bag += [toks[i], toks[i + 1]]; i += 2
            else:
                rest.append(toks[i]); i += 1
        return bag, rest
    g_freq, g = split_freq(g); s_freq, s = split_freq(s)
    if not all(tok in s_freq for tok in g_freq):
        return False
    # containment + ORDER, CLAUSE-WISE: both texts are split into segments at
    # punctuation (a comma returns to the main clause, so a FRONTED clause is
    # not swallowed) and at subordinators, keyed by the subordinator (the main
    # clause keyed None); each gloss clause must be a subsequence of the span
    # clause with the same key. "Before committing, I run the formatter" and
    # "Runs the formatter before committing" are the same clauses in another
    # order and pass; a reversal INSIDE a clause ("merges before the linter
    # runs") fails.
    def clauses(text):
        out = {}
        for seg in re.split(r"[,;:.!?]", str(text).lower()):
            key, cur = None, []
            raw = [x for x in tokens(seg) if x not in _STOP and x != "n't"]
            for tok in raw:                      # subordinators are matched RAW, before the stem
                if tok in ("every", "each"):
                    continue                     # the frequency bag, handled above
                if tok in _SUBORD:
                    out.setdefault(key, []).extend(cur); key, cur = tok, []
                else:
                    cur.append(_stem(tok))
            out.setdefault(key, []).extend(cur)
        return out
    gc, sc = clauses(gloss), clauses(span)
    for key, g_seq in gc.items():
        g_seq = [x for x in g_seq if x not in {y for y in g_freq}]
        if not g_seq:
            continue
        s_seq = sc.get(key)
        if s_seq is None:
            return False
        j = 0
        for tok in g_seq:
            while j < len(s_seq) and s_seq[j] != tok:
                j += 1
            if j == len(s_seq):
                return False
            j += 1
    # negation coverage (on raw tokens, before stemming/stopword removal)
    if any(t in _NEG for t in s_toks) and not any(t in _NEG for t in g_toks):
        return False
    # subordinator coverage: the clause that scoped the practice survives in the gloss
    s_sub = {t for t in s_toks if t in _SUBORD}
    g_sub = {t for t in g_toks if t in _SUBORD}
    if not s_sub <= g_sub:
        return False
    return True


# --------------------------------------------------------- the gate, in spec order
def check_capture(gloss: str, span, event_text: str, *, max_summary_chars: int) -> tuple:
    """Runs the gates in the spec's order and returns (accepted, reason,
    normalised_gloss, normalised_span). `reason` names the first failing gate:
    no_quote | quote_not_in_event | summary_contract | actor_absent |
    gloss_ungrounded; None when accepted."""
    if not isinstance(span, str):
        return (False, "no_quote", None, None)
    s = norm_ws(span)
    if not s:
        return (False, "no_quote", None, None)
    ev = norm_ws(event_text)
    if s not in ev:
        return (False, "quote_not_in_event", None, s)
    g = norm_ws(gloss)
    if not g or len(g) > max_summary_chars:
        return (False, "summary_contract", g, s)
    if not actor_present(s, ev):
        return (False, "actor_absent", g, s)
    if not gloss_grounded(g, s):
        return (False, "gloss_ungrounded", g, s)
    return (True, None, g, s)
