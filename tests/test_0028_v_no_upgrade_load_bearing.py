"""specs/0028 §6 V-NO-UPGRADE — the cap is LOAD-BEARING (post-acceptance evidence
maintenance, 2026-09-15, on the owner's word).

Research's A-5 mutation run found the cap at `asof/resolve.py` ("the verdict caps
the row": a grounded-outcome reason under a non-GROUNDED 0030 verdict returns
FENCED_SELF) fires in the existing suite and yet the FULL suite stays green with
the condition replaced by `if False:`. The existing per-reason test constructs
only rows whose verdict is GROUNDED, so the cap is never the deciding line. This
file constructs the case the cap exists for — a row whose §4b outcome would be
grounded but whose 0030 verdict is FENCED_AS_OF — and asserts the outcome the
mutant would upgrade. Verified red under the mutant before it was committed.
"""
import pathlib
import runpy

import pytest

_h = runpy.run_path(str(pathlib.Path(__file__).with_name("test_0028_resolution.py")), run_name="_helpers_0028")
_store, _edge, _mem, _facts = _h["_store"], _h["_edge"], _h["_mem"], _h["_facts"]
T0, D, U = _h["T0"], _h["D"], _h["U"]
Identity, validate_policy = _h["Identity"], _h["validate_policy"]

from veracium.asof.classify import FENCED_AS_OF, GROUNDED_AS_OF
from veracium.asof.resolve import FENCED_SELF, GROUNDED_OUTCOMES, RESOLUTION


@pytest.mark.parametrize("reason", sorted(r for r, (o, _t) in RESOLUTION.items() if o in GROUNDED_OUTCOMES))
def test_v_no_upgrade_a_fenced_verdict_caps_a_grounded_reason_to_fenced_self(tmp_path, reason):
    """The precondition is asserted, not assumed: a row from ANOTHER source read
    through a principal's cross-scope view classifies FENCED_AS_OF at T inside
    its interval (the construction `test_two_principals_one_store_one_record`
    uses, where the cap fires four times without any assertion reading the
    outcome). With the cap: FENCED_SELF. With the cap disabled: the §4b table's
    grounded outcome — RETURN_SELF / RETURN_SELF_FLAGGED — an UPGRADE of the
    verdict, which is exactly what V-NO-UPGRADE forbids."""
    store = _store(tmp_path)
    vf, ia = T0, T0 + 10 * D
    e = _edge("Porto", source="other-mailbox", valid_from=vf); store.add_edge(e)
    store.invalidate_edge(e.id, ia, reason)
    mem = _mem(tmp_path, store)
    principal = Identity(origin=None, source_id="mb-a")
    policy = validate_policy({}, cross_scope_visible=True, local_origin=store.local_origin())
    T = vf + 5 * D
    facts = mem.facts_valid_at(U, "user", "located_at", T, principal=principal, policy=policy)
    assert [f.edge.id for f in facts] == [e.id]
    r = facts[0].resolution
    assert r.status == FENCED_AS_OF, r                       # the precondition: 0030 fenced it
    assert RESOLUTION[reason][0] in GROUNDED_OUTCOMES        # the table alone would ground it
    assert r.outcome == FENCED_SELF, r                       # the cap: the verdict wins
    assert r.outcome not in GROUNDED_OUTCOMES


def test_v_no_upgrade_the_grounded_verdict_is_not_capped(tmp_path):
    """The other half of the same line: under a GROUNDED verdict the table's
    grounded outcome stands. Together with the test above this pins the
    condition on both sides, so an inverted cap (`==` for `!=`) is red too."""
    store = _store(tmp_path)
    e = _edge("Porto", valid_from=T0); store.add_edge(e)
    store.invalidate_edge(e.id, T0 + 10 * D, "superseded")
    r = _facts(store, T0 + 5 * D)[e.id]
    assert r.status == GROUNDED_AS_OF and r.outcome == RESOLUTION["superseded"][0]
