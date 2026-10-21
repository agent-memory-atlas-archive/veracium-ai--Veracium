"""specs/0051 §4b — the speaker-turn backstop, PRODUCT code (not the frozen predicate: research's 0051 v0.2 H4 read).
A triple restricted here has no value in any user text, so ATTEST-6 over the user text cannot attest it; this module's
only independent effect is the triple's disclosure. Turns come from the frozen grammar (`attest_turns.turns`).

A triple is restricted when EVERY non-`user` side of it occurs in some non-user turn and in no user text, each side
matched as a token sequence on word boundaries after these normalisations, and only these: case-fold; a `kind:`
prefix dropped from the side; `_` and `-` read as spaces; ATTEST-3's own object normalisation; tokens are runs of
letters and digits, so an apostrophe splits ("Daniel's" holds "daniel"); and each token compared by a plural stem
("seats" ~ "seat", "boxes" ~ "box", never "glass" ~ "glas")."""
from __future__ import annotations

import re

from . import attest_v3
from .attest_turns import turns

_KIND = re.compile(r"^[a-z][a-z_]*:")
_TOKEN = re.compile(r"[a-z0-9]+")


def _stem(tok: str) -> str:
    if len(tok) > 4 and tok.endswith("es") and tok[-3] in "sxz":
        return tok[:-2]
    if len(tok) > 5 and tok.endswith(("ches", "shes")):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def _tokens(s: str) -> list:
    return [_stem(t) for t in _TOKEN.findall(attest_v3._norm_object(s.lower().replace("_", " ").replace("-", " ")))]


def _side(s: str) -> list:
    return _tokens(_KIND.sub("", s.strip().lower()))


def _occurs(value: list, toks: list) -> bool:
    n = len(value)
    return n > 0 and any(toks[i:i + n] == value for i in range(len(toks) - n + 1))


def speaker_restricts(subject: str, obj: str, event_text: str) -> bool:
    ts = [(sp, _tokens(b)) for sp, b in turns(event_text)]
    if not any(sp == "non-user" for sp, _t in ts):
        return False
    sides = [obj] if subject == "user" else [subject] if obj == "user" else [subject, obj]
    values = [_side(s) for s in sides]
    if any(not v for v in values):
        return False
    return all(any(_occurs(v, t) for sp, t in ts if sp == "non-user")
               and not any(_occurs(v, t) for sp, t in ts if sp == "user") for v in values)
