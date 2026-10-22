"""ATTEST-5 (specs/0051): ATTEST-3 restricted to the USER's turns of a speaker-labelled event, and the speaker-turn
backstop. FROZEN BYTES: `attestation.PREDICATE_VERSION` names this file's sha256 prefix, and a test binds that literal
to this file AND to ATTEST-3's (`attest_v3.py`, b1329a81), since ATTEST-5's verdict is a function of both. Any edit is a
new version, measured on a fresh holdout before it ships (0045 §4a, Versioning). ATTEST-4 (ba09a2a1) never shipped:
its rule "every label ends the turn before it" let a heading inside an assistant reply ("Pros:", "Note:") end the
assistant's turn (research's 0051 B3; 24.5% of LongMemEval's assistant turns).

THE TURN GRAMMAR (closed). A LABEL is found at the start of the event or of a line, after optional spaces, `>` quote
markers and a markdown heading (`#`..`######`), inside optional `**`/`__` emphasis:
    NAME [ (parenthetical) ] :          e.g. "Assistant:", "**User:**", "> AI:", "Assistant (GPT-4o):"
    NAME said:                          e.g. "You said:", "ChatGPT said:"
    a heading that is only NAME         e.g. "### Assistant" (the turn starts on the next line)
NAME is one to three words of letters (and `'` `.` `-`), at most 32 characters, beginning with a letter, none of
them `said`; a colon followed by `//` (a URL) is not a label. Each label is CLASSED over the whole event:
    USER        user · human · me · customer · `you` in the `said:` form only · `h`/`q` when COUNTED (below)
    NON-USER    assistant · ai · chatbot · claude · chatgpt · gpt · gemini · copilot · `a` when COUNTED ·
                system · model · agent · bot · any one word ending in `bot` (WEAK) when in a TWO-SPEAKER SHAPE: the
                event also carries a USER label, or the same weak name labels two turns with another label between
    UNLISTED    every other name, an uncounted weak name, an uncounted letter
    (the letters are COUNTED only when both an `h`/`q` label and an `a` label occur)
THE TURNS, one left-to-right pass over the labels. Text before the first label is a USER turn.
    - A USER or NON-USER label always ends the turn before it and opens a turn of its class.
    - Outside a non-user turn, an UNLISTED label ends the turn before it and opens a USER turn (a person's own notes:
      "Model: Corolla", "Tips: …"). If the label's NEXT label is NON-USER, its name becomes ESTABLISHED (it handed the
      floor to a non-user speaker).
    - Inside a non-user turn, an UNLISTED label ends that turn and opens a USER turn ONLY when its name is already
      ESTABLISHED, or its NEXT label is NON-USER (it hands the floor back; its name then becomes established).
      Otherwise it is part of the non-user turn's text: a heading, a key, a list title ("Pros:", "Note:").
The USER TEXT is every user turn (label removed) in order; it exists only when at least one NON-USER turn does.
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
    """'user', 'non-user' or 'unlisted' per label, by the closed classes above (whole-event properties)."""
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
            out.append("non-user" if has_user or alternates else "unlisted")
        elif n == "a":
            out.append("non-user" if letters else "unlisted")
        elif n in USER_NAMES or (n == "you" and said) or (n in ("h", "q") and letters):
            out.append("user")
        else:
            out.append("unlisted")
    return out


def turns(text: str) -> list:
    """[(speaker, body)] over the whole event: 'user' or 'non-user', each body with its label removed."""
    labels = _labels(text)
    if not labels:
        return [("user", text)]
    classes = _classify(labels)
    bounds, cur, established = [], "user", set()      # bounds: (label index, the speaker of the turn it opens)
    for i, (_s, _e, n, _said) in enumerate(labels):
        hands_off = i + 1 < len(labels) and classes[i + 1] == "non-user"
        if classes[i] != "unlisted":
            bounds.append((i, classes[i]))
            cur = classes[i]
        elif cur != "non-user" or n in established or hands_off:
            bounds.append((i, "user"))
            cur = "user"
            if hands_off:
                established.add(n)
    out = [("user", text[:labels[bounds[0][0]][0]] if bounds else text)]
    for k, (i, speaker) in enumerate(bounds):
        stop = labels[bounds[k + 1][0]][0] if k + 1 < len(bounds) else len(text)
        out.append((speaker, text[labels[i][1]:stop]))
    return [(sp, b) for sp, b in out if b or sp != "user" or len(out) == 1]


def user_text(text: str):
    """The event's user text, or None when the event has no non-user turn (then ATTEST-5 is ATTEST-3)."""
    ts = turns(text)
    if not any(sp == "non-user" for sp, _b in ts):
        return None
    return "\n".join(b for sp, b in ts if sp == "user")


def attests(subject: str, relation: str, obj: str, event_text: str) -> str:
    """ATTEST-5: ATTEST-3 over the raw text AND, when the event has a non-user turn, over its user text. Its attested
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
