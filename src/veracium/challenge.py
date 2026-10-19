"""specs/0047 §4c–§4e and 0045 §4c on the READ side: what a surface may assert, and what an inspection carries.

ONE object per call. Every surface a call renders or returns reads the challenge state from the SAME
`ChallengeSnapshot` (0047 §4d's one-snapshot row, IO-II-5): its withholding, its report-line count and its structured
returns' inspection records. The snapshot is read before the call's own edge reads, so an edge the call later reads is
judged against acts at least as old as the call; a challenge committed during a call is reflected from the next one.

THE GATE (§4c, v1.8): an edge with an active challenge is NOT ASSERTABLE, whatever `g(e)`; it is WITHHELD on every
assertion surface and counted. The owner's F7 ruling (2026-10-19, option (ii)): a same-value TWIN of a challenged record
is withheld too, read-side, no act copied; and (the T10b rulings) the subject's own later correction is a twin like any
other until a `resolve`, a historical twin is withheld on as-of, and a challenger outside a principal's view still
withholds an in-view twin without being named there. Restriction only: nothing here can make an otherwise ineligible
edge assertable (INV-R12).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Mapping, Optional

from .attestation import declarative_grounding
from .census import declare_site

_SITE_WITHHELD = declare_site("read.challenge.withheld", declines=True)   # specs/0047 INV-R3, F7
_SITE_TWIN = declare_site("read.challenge.twin", declines=True)           # F7's "same value", (a)–(b)


@dataclass(frozen=True)
class OpenChallenge:
    id: str
    text: str
    written_at: datetime


@dataclass(frozen=True)
class ChallengedRecord:
    """A record with at least one open challenge. `edge` is held for twin matching and the scope check only, never
    handed to a caller; `redacted` is the attestation record's answer (0041 §4b-iii), never the marker bytes."""
    edge: object
    value_key: tuple
    challenges: tuple            # OpenChallenge, ordered by (written_at, id); the LAST is the latest
    redacted: bool


@dataclass(frozen=True)
class EdgeInspection:
    """0047 §4d's inspection record for one edge: g(e) and its version (0045 §4c, INV-G13: read from `attv`), the
    open count over ALL active challenges (never budget-selected, INV-R6), the latest open challenge's text, the
    mandatory unit, and §4c's half of assertability.

    `challenge_clear` is False when the edge has an open challenge or twins a challenged record (F7); a caller must not
    assert an edge whose entry is not clear (the consumer duty). Restriction only: True never promotes an edge another
    gate refuses. `withheld_by` names the challenged records withholding it, and `waiting_on` their open challenges —
    only those the reader may see (0020 N-2: a challenger out of view withholds without being named)."""
    edge_id: str
    grounding: Optional[str]
    attestation_version: Optional[str]
    open_challenges: int
    latest_challenge: Optional[str]
    unit: Optional[str]
    challenge_clear: bool = True
    withheld_by: tuple = ()
    waiting_on: tuple = ()


def unit_text(n_open: int, latest: str, cap_tokens: int) -> str:
    """The mandatory unit (§4d). The latest open challenge's text is clamped to the per-item cap with the elision
    marker; the count is never clamped."""
    from .budgets import clamp_item
    return f"[challenged by the subject: {n_open} open; latest: {clamp_item(latest, cap_tokens)}]"


def _is_twin(edge, rec: ChallengedRecord) -> bool:
    """F7's "same value" (ruled (a)): same subject and relation, and the value keys equal or one subsuming the other
    within the absorption bound — reinforcement's and absorption's predicate, both directions — across disclosure
    classes, whatever the challenged record's own state ((b)). A REDACTED challenged record twins nothing: its object
    is the marker, and no value of it survives to match on ((g)). Decided by the attestation record (`rec.redacted`),
    never the bytes. Today that guard is defence in depth: local redaction and every applied notice replace the
    subject and relation as well (`redaction.EDGE_REPLACE`), so a redacted record's triple matches no fact; a narrower
    edge treatment would leave the guard the only defence (pinned by the T10b cells)."""
    from .graph import _subsumes, _value_key
    with _SITE_TWIN.consult():
        if rec.redacted or edge.id == rec.edge.id or edge.subject != rec.edge.subject \
                or edge.relation != rec.edge.relation:
            return _SITE_TWIN.fire(False, "not-a-twin")
        vk = _value_key(edge.object)
        return _SITE_TWIN.fire(vk == rec.value_key or _subsumes(vk, rec.value_key) or _subsumes(rec.value_key, vk),
                               "twin")


@dataclass(frozen=True)
class ChallengeSnapshot:
    challenged: Mapping[str, ChallengedRecord] = field(default_factory=dict)
    confirmation_origins: Mapping[str, tuple] = field(default_factory=dict)
    acted: frozenset = frozenset()

    def _withholders(self, edge) -> tuple:
        if edge.provenance.procedural:          # INV-R19: a procedural edge carries no reply and no grounding
            return ()
        own = self.challenged.get(edge.id)
        if own is not None:
            return (own,)
        return tuple(sorted((r for r in self.challenged.values() if _is_twin(edge, r)), key=lambda r: r.edge.id))

    def withheld(self, edge) -> bool:
        """The ONE predicate every assertion surface asks (INV-R3, F7)."""
        with _SITE_WITHHELD.consult():
            return _SITE_WITHHELD.fire(len(self._withholders(edge)) > 0, "withheld")

    def inspect(self, edge, *, visible: Optional[Callable] = None, cap_tokens: int = 512) -> EdgeInspection:
        """The inspection record. `visible` is the reader's scope predicate (None: the operator, who sees all)."""
        ws = self._withholders(edge)
        named = [r for r in ws if visible is None or r.edge.id == edge.id or visible(r.edge)]
        g = declarative_grounding(edge, self.confirmation_origins.get(edge.id, ()))
        version = None if g is None else (edge.attv if edge.attv is not None else "version unknown")
        own = self.challenged.get(edge.id)
        latest = own.challenges[-1].text if own is not None else None
        return EdgeInspection(
            edge_id=edge.id, grounding=g, attestation_version=version,
            open_challenges=len(own.challenges) if own is not None else 0, latest_challenge=latest,
            unit=unit_text(len(own.challenges), latest, cap_tokens) if own is not None else None,
            challenge_clear=not ws,
            withheld_by=tuple(r.edge.id for r in named),
            waiting_on=tuple(c.id for r in named for c in r.challenges))


def withheld_line(n: int) -> str:
    """The report line's withheld count (§4d: "the silence is not silent"): this answer's candidates, counted before any
    budget selection and, under a principal, inside the view (0020 N-1)."""
    from .budgets import bounded_count
    return f"[withheld: {bounded_count(n)} fact(s) the subject disputes; see the host's why()]"
