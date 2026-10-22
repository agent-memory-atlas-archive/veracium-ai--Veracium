"""ATTEST-4 (specs/0051): ATTEST-3 restricted to the USER's turns of a speaker-labelled event, and the speaker-turn
backstop. FROZEN BYTES: `attestation.PREDICATE_VERSION` names this file's sha256 prefix, and a test binds that literal
to this file AND to ATTEST-3's (`attest_v3.py`, b1329a81), since ATTEST-4's verdict is a function of both. Any edit is a
new version, measured on a fresh holdout before it ships (0045 §4a, Versioning).

THE TURN GRAMMAR (closed). A LABEL is found at the start of the event or of a line, after optional spaces, `>` quote
markers and a markdown heading (`#`..`######`), inside optional `**`/`__` emphasis:
    NAME [ (parenthetical) ] :          e.g. "Assistant:", "**User:**", "> AI:", "Assistant (GPT-4o):"
    NAME said:                          e.g. "You said:", "ChatGPT said:"
    a heading that is only NAME         e.g. "### Assistant" (the turn starts on the next line)
NAME is one to three words of letters (and `'` `.` `-`), at most 32 characters, beginning with a letter, none of
them `said`; a colon followed by `//` (a URL) is not a label. EVERY label
ends the turn before it. A NAME is classed:
    USER        user · human · me · customer · and `you` in the `said:` form only
    NON-USER    assistant · ai · chatbot · claude · chatgpt · gpt · gemini · copilot
    WEAK        system · model · agent · bot · any one word ending in `bot` — NON-USER only in a TWO-SPEAKER SHAPE:
                the event also carries a USER label, or the same weak name labels two turns with another label between
    LETTERS     `h` and `q` (user) and `a` (non-user) — counted only when both an `h`/`q` and an `a` label occur
    anything else — USER: an unlisted name opens a user turn (a person's own notes: "Model: Corolla")
Text before the first label is USER text. The USER TEXT is every user turn (label removed) in order; it exists only
when at least one NON-USER turn does.
"""
from __future__ import annotations

import re

from . import attest_v3

USER_NAMES = frozenset(("user", "human", "me", "customer"))
NON_USER_NAMES = frozenset(("assistant", "ai", "chatbot", "claude", "chatgpt", "gpt", "gemini", "copilot"))
WEAK_NAMES = frozenset(("system", "model", "agent", "bot"))
_WEAK_BOT = re.compile(r"[a-z]+bot")
_WORD = r"(?![Ss]aid\b)[A-Za-z][A-Za-z'.\-]*"                 # `said` is the said-form's word, never a name's
_NAME = _WORD + r"(?: " + _WORD + r"){0,2}"
_LEAD = r"[ \t]*(?:>[ \t]*)*(?:#{1,6}[ \t]+)?(?:\*\*|__)?"
_LABEL = re.compile(
    r"(?m)^" + _LEAD + r"(?P<name>" + _NAME + r")(?:\*\*|__)?[ \t]*"
    r"(?:(?P<paren>\([^()\n]{1,40}\))[ \t]*)?(?P<said>said[ \t]*)?:(?!//)(?:\*\*|__)?[ \t]?")         # `https://…` is not a label
_HEADING = re.compile(r"(?m)^[ \t]*(?:>[ \t]*)*#{1,6}[ \t]+(?:\*\*|__)?(?P<name>" + _NAME + r")(?:\*\*|__)?[ \t]*$\n?")


def _labels(text: str) -> list:
    """Every label, in order: (start, end, name lower-cased, said-form). A heading label and a colon label cannot
    overlap (a heading line holds no colon)."""
    found = []
    for m in _LABEL.finditer(text):
        if len(m.group("name")) <= 32:
            found.append((m.start(), m.end(), m.group("name").lower(), m.group("said") is not None))
    for m in _HEADING.finditer(text):
        if len(m.group("name")) <= 32:
            found.append((m.start(), m.end(), m.group("name").lower(), False))
    found.sort()
    return found


def _classify(labels: list) -> list:
    """'user' or 'non-user' per label, by the closed classes above."""
    names = [n for _s, _e, n, _said in labels]
    has_user = any(n in USER_NAMES or (n == "you" and said) for _s, _e, n, said in labels)
    letters = {"h", "q"} & set(names) and "a" in names
    out = []
    for i, (_s, _e, n, said) in enumerate(labels):
        if n in NON_USER_NAMES:
            out.append("non-user")
        elif n in WEAK_NAMES or _WEAK_BOT.fullmatch(n):
            alternates = any(names[j] == n and any(names[k] != n for k in range(min(i, j) + 1, max(i, j)))
                             for j in range(len(names)) if j != i)
            out.append("non-user" if has_user or alternates else "user")
        elif n == "a":
            out.append("non-user" if letters else "user")
        else:
            out.append("user")
    return out


def turns(text: str) -> list:
    """[(speaker, body)] over the whole event: 'user' or 'non-user', each body with its label removed."""
    labels = _labels(text)
    if not labels:
        return [("user", text)]
    classes = _classify(labels)
    out = [("user", text[:labels[0][0]])] if labels[0][0] > 0 else []
    for i, (_s, end, _n, _said) in enumerate(labels):
        stop = labels[i + 1][0] if i + 1 < len(labels) else len(text)
        out.append((classes[i], text[end:stop]))
    return out


def user_text(text: str):
    """The event's user text, or None when the event has no non-user turn (then ATTEST-4 is ATTEST-3)."""
    ts = turns(text)
    if not any(sp == "non-user" for sp, _b in ts):
        return None
    return "\n".join(b for sp, b in ts if sp == "user")


def attests(subject: str, relation: str, obj: str, event_text: str) -> str:
    """ATTEST-4: ATTEST-3 over the raw text AND, when the event has a non-user turn, over its user text. Its attested
    set is a subset of ATTEST-3's on every input (restriction only)."""
    verdict = attest_v3.attests(subject, relation, obj, event_text)
    if verdict != "ATTESTED":
        return verdict
    u = user_text(event_text)
    if u is None:
        return verdict
    return "ATTESTED" if attest_v3.attests(subject, relation, obj, u) == "ATTESTED" else "NOT_ATTESTED"


_KIND = re.compile(r"^[a-z][a-z_]*:")
_TOKEN = re.compile(r"[a-z0-9']+")


def _tokens(s: str) -> list:
    return _TOKEN.findall(attest_v3._norm_object(s.lower().replace("_", " ").replace("-", " ")))


def _side_tokens(s: str) -> list:
    """A triple side's value: its `kind:` prefix (`person:`, `org:`) dropped first."""
    return _tokens(_KIND.sub("", s.strip().lower()))


def _occurs(value: list, body: str) -> bool:
    toks = _tokens(body)
    n = len(value)
    return n > 0 and any(toks[i:i + n] == value for i in range(len(toks) - n + 1))


def only_in_non_user_turns(subject: str, obj: str, event_text: str) -> bool:
    """The backstop's test (0051 §4b): True when the event has a non-user turn and EVERY non-`user` side of the triple
    — the object when the subject is `user`, the subject when the object is `user`, both otherwise — occurs, as a
    token sequence on word boundaries (a `kind:` prefix dropped, `_`/`-` read as spaces, ATTEST-3's normalisation),
    in some non-user turn and in no user text. A value found in neither (a paraphrase) is False."""
    ts = turns(event_text)
    if not any(sp == "non-user" for sp, _b in ts):
        return False
    sides = [obj] if subject == "user" else [subject] if obj == "user" else [subject, obj]
    values = [_side_tokens(s) for s in sides]
    if any(not v for v in values):
        return False
    return all(any(_occurs(v, b) for sp, b in ts if sp == "non-user")
               and not any(_occurs(v, b) for sp, b in ts if sp == "user") for v in values)
