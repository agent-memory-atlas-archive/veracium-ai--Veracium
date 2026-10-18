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

import math

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


def contested_group_key(subject: str, relation: str, renderable: list, visible: list) -> tuple:
    """specs/0003 §4c-iii.6 4a — where a contested group sorts in the CONTESTED block and `Recall.contested`: by the
    authority of the fact it preserves, then by ambiguity, then by visible size, then by slot (determinism only).

    `renderable`: the effective authorities of the members the renderer can EMIT (the assertable exposed members).
    `visible`: those of every member VISIBLE to this principal: every exposed member and every FENCED linkage entry,
    never a policy-hidden (withheld, 0020 N-2) or UNRESOLVED member. Both are the PUBLISHED authorities, after the
    view's shaping. The key reads no query, so the order cannot depend on one (§4c-iii INV-O4).

    A group with nothing renderable sorts after every other group, by slot. Otherwise, with `t` the highest renderable
    authority: `(−t, t − max(visible without one t) or +∞, −|visible|, slot)`. A tie on `t` between members changes no
    component, so no edge-id tie is computed.

    Residual, stated (research's T8 stage-1 F1): `Recall.contested` publishes a fenced and a policy-hidden member as
    the same content-free `ContestedLinkage`, but only the fenced one is in `visible`. Two groups that read the same
    on the structured API can therefore sort differently, so the order discloses which kind a linkage entry is. §4a
    mandates this (INV-O10)."""
    if not renderable:
        return (1, 0, 0, 0, subject, relation)
    top = max(renderable)
    rest = list(visible)
    rest.remove(top)
    gap = (top - max(rest)) if rest else math.inf
    return (0, -top, gap, -len(visible), subject, relation)
