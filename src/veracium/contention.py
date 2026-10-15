"""specs/0003 §4c-ii + specs/0044 §4d — when a refusal record is a LIVE CONTENTION, in ONE place.

Recall's contested groups (`Memory._contested_groups`) and the wiki compiler's refusal exclusion
(`compile._live_refusal_contention_edge_ids`, which `introspect` reuses) both ask this question of every refusal, so
each asks it HERE (research's T5 read, F3: two copies of the predicate would let the retention rule drift between
the contested surface and the wiki exclusion).

A refusal is live iff both referenced edges are active and still distinct in value AND either
  - its relation is `single` (functional) — the existing rule (0003 §4c-ii); or
  - its relation is one of the three DEFAULT names 0044 reclassified to `multi`, and the refusal is in the v16 schema
    step's refusal inventory: recorded while the relation was `single`, so its protection is RETAINED (0044 §4d). Never
    decided from a timestamp, and with no expiry (INV-A14): the pair stays contested until a lifecycle transition
    retires a member.
A `multi` relation's ordinary path creates no refusal, so a refusal under a `multi` relation outside the inventory
forms no group. Ranking (`graph._permute_contention_groups`) is unchanged: a retained pair is ordered by relevance
there, and by authority on the contested surface (research's R4, option (i)).
"""
from __future__ import annotations

from .graph import _value_key
from .store.lifetime import RECLASSIFIED_RELATIONS


def retained_refusal_ids(store, user_id: str) -> frozenset:
    """The user's refusal-inventory ids; a Store without the 0044 primitive reads as having none (like `refusals`)."""
    try:
        return frozenset(store.refusal_inventory_ids(user_id))
    except NotImplementedError:
        return frozenset()


def is_live_refusal(refusal, prior, incoming, relations: dict, retained: frozenset) -> bool:
    """`prior` / `incoming`: the referenced edges if ACTIVE, else None."""
    if prior is None or incoming is None:
        return False
    if _value_key(prior.object) == _value_key(incoming.object):
        return False
    rel = relations.get(refusal.relation)
    if rel is None:
        return False
    if rel.functional:
        return True
    return refusal.relation in RECLASSIFIED_RELATIONS and refusal.refusal_id in retained
