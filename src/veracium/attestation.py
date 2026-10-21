"""specs/0045 — the declarative grounding axis: what ingest records about how a fact is known, and the value read from it.

`attest_v3` is ATTEST-3, VENDORED BYTE-IDENTICAL from the evidence set that measured it (`specs/evidence/0045/attest/`,
sha256 b1329a81…; the owner's D6, 2026-10-18), so the predicate holdout H2 scored is the one the write path runs.
specs/0051: the write path runs ATTEST-6 (`attest_turns`, FROZEN, sha256 ccabb664…): ATTEST-3 over the raw text AND,
when the event labels a non-user turn, over the event's user text. ATTEST-5 (0bb7779f, the predicate research's
holdout H4 scored) differed in one rule (R-II round 2's RII-02: a counted `h`/`q` did not make a weak name a non-user
speaker); ATTEST-6's holdout is H5.
Nothing here reads the extractor's output or 0019's flag: `att` comes only from ATTEST over the event text (0051: the raw text and its user turns)
(INV-G1), and the axis is orthogonal to the flag (INV-G8).

THE VERSION CARRIER (0045 v1.9 §4a): every `att` is written with `attv`, WHAT produced it, from the same evaluation:
`PREDICATE_VERSION` when the predicate judged the statement, `NON_USER_EFFECTIVE` when the write path decided by the
author rule and no predicate ran. `PREDICATE_VERSION` is a LITERAL, bound to the vendored file's digest by a test
(research's T9 F9), never computed from the bytes at run time.
"""
from __future__ import annotations

import re
from typing import Optional

from . import attest_turns

PREDICATE_VERSION = "ATTEST-6@ccabb664"   # specs/0051 §4a; ATTEST-3@b1329a81 and ATTEST-5@0bb7779f rows keep theirs (INV-G7, G13)
NON_USER_EFFECTIVE = "non-user-effective"
DEFAULT_IMPORT = "default-import"
ATTESTED, NOT_ATTESTED = "attested", "not_attested"

# 0045 §2c: `attv`'s closed grammar, matched WHOLE (research's T9 F4: ASCII digits only, no leading zero, no trailing
# text; `\d` would admit other scripts' digits and an unanchored pattern a suffix)
_ATTV = re.compile(r"ATTEST-[1-9][0-9]*@[0-9a-f]{8}|non-user-effective|default-import")


def valid_attv(value: str) -> bool:
    return isinstance(value, str) and _ATTV.fullmatch(value) is not None


def attestation(user_effective: bool, subject: str, relation: str, obj: str, event_text: str) -> tuple[str, str]:
    """0045 §3/§4a: `(att, attv)` for one DECLARATIVE edge of an event. USER-effective (0019 v7: the effective author
    is USER and the resolved content source is direct): ATTEST-3 over the RAW event text, with the edge's own
    subject, relation and object as stored (an UNSUPPORTED answer is not attested: the safe direction) — through ATTEST-6
    (specs/0051 §4a), which conjoins ATTEST-3 over the event's user text when the event labels a non-user turn. Any
    other event: `not_attested`, and the predicate is NOT called (§3: ATTEST-3 covers first-person USER statements
    only)."""
    if not user_effective:
        return NOT_ATTESTED, NON_USER_EFFECTIVE
    verdict = attest_turns.attests(subject, relation, obj, event_text)
    return (ATTESTED if verdict == "ATTESTED" else NOT_ATTESTED), PREDICATE_VERSION


def declarative_grounding(edge, confirmation_origins) -> Optional[str]:
    """0045 §4c, `g(e)`, derived and never stored: None for a procedural edge (0037's basis grounds it); `confirmed`
    if any confirmation of origin `local` or `restored` exists (an `imported` one is testimony, 0047 §4f); else the
    stored `att`, NULL reading `unknown` (INV-G7: never re-derived)."""
    if edge.provenance.procedural:
        return None
    if any(o in ("local", "restored") for o in confirmation_origins):
        return "confirmed"
    return edge.att if edge.att is not None else "unknown"
