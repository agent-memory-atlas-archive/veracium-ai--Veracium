"""specs/0044 §4f / §4f-ii — an edge row's LIFETIME, derived from its persisted bytes, in ONE place.

The v16 schema step's arity inventory (§4f), the lifetime hook at 0029's emission choke point (§4f-ii) and `doctor`'s
pre-plan phase (0018 amendment §4e) all ask the same two questions of an edge row, so each asks them HERE (research's
T5 read, F2: one predicate, or the step and the hook classify one row differently):

  retirement(d)  the row's current retirement, `(invalidated_at, invalidation_reason)` as stored, or None when it is
                 active. `Edge.active` is DERIVED from `invalidated_at` (the `active` column mirrors it); the step
                 asserts that mirror for every row it inventories, so a row where they disagree refuses the step.
  redacted(d)    the row's own carriers hold the marker (`redaction.edge_carries_marker`). The marker is not self-
                 authenticating (0041 §4b): it equals an attested redaction HERE only because no write path may
                 INTRODUCE it — `_upsert_edge_row` refuses that (INV-11's mirror, `store.upsert.marker-introduced`) and
                 an import's differing same-id row refuses the whole import (0009). Relax either and this test reads a
                 forged marker as a redaction: it would clear `applicable` (fail-closed, but a silent change).

A transition is NEVER inferred from which method ran or from the journal kind (a changed same-id upsert journals
`mutated`): `transition(prior, new)` is §4f-ii's table over the persisted prior row and the new row.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import NamedTuple, Optional

from ..redaction import edge_carries_marker

# specs/0044 §4b: the three DEFAULT relation names reclassified single -> multi. The inventory selects by these NAMES
# (0018 amendment §4a, "under the three default relation names"); eligibility is the plan's (§4e), never this set's.
RECLASSIFIED_RELATIONS = ("measures", "prefers", "health_state")
SUPERSEDED = "superseded"


class Lifetime(NamedTuple):
    retirement: Optional[tuple]
    redacted: bool


def retirement(d: dict) -> Optional[tuple]:
    """The retirement AS STORED (the inventory keeps these bytes: they are what an undo writes back, §4i)."""
    at = d.get("invalidated_at")
    return None if at is None else (at, d.get("invalidation_reason"))


def _instant(at):
    """A stored `invalidated_at` as an instant, so ONE instant written two ways (`+00:00` by a legacy writer, `Z` by
    the model's serializer, which every rewrite of the row uses) is one value. An unparseable value stays as stored."""
    if not isinstance(at, str):
        return at
    try:
        dt = datetime.fromisoformat(at[:-1] + "+00:00" if at.endswith("Z") else at)
    except ValueError:
        return at
    return dt.astimezone(timezone.utc) if dt.tzinfo is not None else dt


def same_retirement(a: Optional[tuple], b: Optional[tuple]) -> bool:
    """§4f's equality test, "the current retirement EQUALS the inventoried one": the same instant and the same reason —
    never a byte comparison of the timestamp, which would read a re-serialization as a re-retirement."""
    if a is None or b is None:
        return a is b
    return _instant(a[0]) == _instant(b[0]) and a[1] == b[1]


def lifetime(row_json: str) -> Lifetime:
    d = json.loads(row_json)
    return Lifetime(retirement(d), edge_carries_marker(d))


def transition(prior_json: Optional[str], new_json: str) -> Optional[str]:
    """§4f-ii's table. None for an insert (no persisted prior), even one arriving retired or redacted, and for an
    unchanged lifetime (ordinary mutations: counters, confirmation, reinforcement)."""
    if prior_json is None:
        return None
    p, n = lifetime(prior_json), lifetime(new_json)
    if n.redacted and not p.redacted:
        return "redaction"
    if p.retirement is not None and n.retirement is None:
        return "reinstatement"
    if p.retirement is None and n.retirement is not None:
        return "retirement"
    if p.retirement is not None and not same_retirement(n.retirement, p.retirement):
        return "re-retirement"
    return None


# the effects, in the writer's transaction: a reinstatement ENDS the row's inventory membership (terminally — a later
# identical re-retirement never matches again); a retirement, re-retirement or redaction CLEARS `applicable` on its
# outcome (terminally — a later reinstatement never sets it back)
ENDS_MEMBERSHIP = frozenset({"reinstatement"})
CLEARS_APPLICABLE = frozenset({"retirement", "re-retirement", "redaction"})
