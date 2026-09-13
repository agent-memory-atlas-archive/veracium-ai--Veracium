"""specs/0027 v13 §4c — the POLICY RECEIPT (research T1; the owner's word,
2026-09-13: "Do the A1 receipt").

A policy lane may reorder what is returned; the receipt is what makes that
admissible: it records the COUNTERFACTUAL — the selection the same inputs give
with the policy term removed — so `displaced` (baseline[:n] − adjusted[:n]) is
the event `recalled_edges` structurally cannot hold (it is filtered to
survivors, and on the non-semantic path it is empty). Two properties learned
from correction C1 are asserted here rather than assumed: the receipt is
written on the NON-SEMANTIC path too, and it exists only when the lane FIRED.
"""

import importlib.util
import os
import pathlib
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig, PolicyLane, PolicyReceipt
from veracium.graph import RRF_K, fused_subgraph, fused_subgraph_with_receipt


def _module(name):
    path = pathlib.Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name[:-3] + "_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = _module("test_0027_semantic_recall.py")
lane_tests = _module("test_0027_policy_lane.py")
U = base.U
_edge = base._edge
LANE = PolicyLane(policy_id="demo-language-relevant", policy_version="2026-09-13.1",
                  ranks={"p": 1}, tags_matched=("language-relevant",))


# ------------------------------------------------------------- at the seam ----
def test_the_receipt_records_the_counterfactual_displacement_and_admission():
    """R4-1's coverage fixture (test_0027_policy_lane): the promotion of `p`
    evicts the head's marginal record `r5` and nothing else. The receipt says
    exactly that — baseline and adjusted selections, displaced, admitted — and
    asserts the reserve was the same set either way (V-RESERVE-UNADJUSTED per
    call), the score delta the lane contributed, and that the budget truncated."""
    scored, relevant, by_id, max_edges = lane_tests._coverage_fixture()
    out, meta, r = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"p": 1})
    assert r is not None
    assert r["baseline_order"] == ["x00", "x01", "r1", "r2", "r3", "r4", "r5", "t"]
    assert r["adjusted_order"] == [e.id for e in out]
    assert r["displaced"] == ["r5"] and r["admitted"] == ["p"]
    assert r["reserve_unchanged"] is True
    assert r["reserved_baseline"] == r["reserved_adjusted"] == ["x00", "x01"]     # the evidence for the boolean, derivable
    assert r["budget_state"] == {"candidates": 10, "max_edges": 8, "truncated": True, "coverage_share": 0.25}
    assert set(r["delta_fused"]) == {"p"} and 0 < r["delta_fused"]["p"] <= 1.0 / (RRF_K + 1) + 1e-12   # the per-lane bound, to the ulp
    assert r["ranks_applied"] == {"p": 1}
    # the baseline IS the no-policy selection: the same construction, no second instrument
    base_out, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)
    assert r["baseline_order"] == [e.id for e in base_out]


def test_no_receipt_when_no_policy_and_none_when_the_lane_did_not_fire():
    """The receipt exists only for a recall in which a policy lane FIRED: a rank
    on an id the membership lanes do not hold contributes nothing (v11) and
    leaves no receipt — an inert policy is not an event."""
    scored, relevant, by_id, max_edges = lane_tests._coverage_fixture()
    _, _, r0 = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=max_edges)
    _, _, r1 = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"ghost": 1})
    assert r0 is None and r1 is None
    # and the plain entry point's shape is unchanged for every existing caller
    assert len(fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)) == 2


def test_below_the_budget_the_lane_fires_and_the_receipt_proves_nothing_could_move():
    """T5's structural fact, carried by the receipt: with fewer candidates than
    `max_edges` there is no truncation, so a firing lane reorders and displaces
    nothing — `budget_state.truncated` is False and both lists are empty."""
    scored, relevant, by_id, _ = lane_tests._coverage_fixture()
    out, _, r = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=40, policy_rank={"p": 1})
    assert r is not None and r["displaced"] == [] and r["admitted"] == []
    assert r["budget_state"] == {"candidates": 10, "max_edges": 40, "truncated": False, "coverage_share": 0.25}
    assert r["reserved_baseline"] == r["reserved_adjusted"] == []                 # no truncation, no reserve
    assert set(r["baseline_order"]) == set(r["adjusted_order"]) == {e.id for e in out}


# ------------------------------------------------------- through Memory.recall ----
def _memory(tmp_path, name, max_edges=8):
    mem = Memory(llm=lambda *a, **k: "",
                 config=MemoryConfig(db_path=str(tmp_path / name), max_subgraph_edges=max_edges,
                                     require_source_id=False))
    for i in range(12):
        mem.store.add_edge(_edge(f"x{i:02d}", "user", "likes", f"boat topic{i}", days=i))
    mem.store.add_edge(_edge("p", "user", "enjoys", "harbor walks", days=30))   # no query overlap: outside the reserve's set
    return mem


def test_the_receipt_is_written_on_the_non_semantic_path_and_carries_ids_only(tmp_path):
    """Correction C1: `recalled_edges` was written only on the semantic path and
    filtered to survivors, so the displaced record — the whole event — left
    nothing. With `semantic=False` and a policy, the fused construction runs
    (its degenerate identity IS the legacy projection, V10) and the receipt
    exists; the displaced id has no `recalled_edges` entry and is not among the
    returned edges, yet the receipt names it. Ids only: no field carries content."""
    mem = _memory(tmp_path, "r.db")
    r = mem.recall(U, "boat topic", semantic=False, policy=LANE)
    rc = r.policy_receipt
    assert isinstance(rc, PolicyReceipt)
    assert r.semantic_status == "disabled" and rc.semantic_status == "disabled"
    assert rc.policy_id == LANE.policy_id and rc.policy_version == LANE.policy_version
    assert rc.tags_matched == ("language-relevant",)
    assert rc.admitted == ["p"] and len(rc.displaced) == 1
    displaced = rc.displaced[0]
    assert displaced not in {e.id for e in r.edges}
    assert r.recalled_edges.get(displaced) is None            # the event recalled_edges cannot hold
    assert rc.adjusted_order == [e.id for e in r.edges]
    assert rc.reserve_unchanged is True and rc.budget_state["truncated"] is True
    assert rc.reserve_unchanged == (rc.reserved_baseline == rc.reserved_adjusted)   # declared == derived
    assert rc.budget_state["coverage_share"] == mem.config.subgraph_coverage_share
    assert rc.recorded_at and datetime.fromisoformat(rc.recorded_at.replace("Z", "+00:00")).tzinfo is not None
    assert isinstance(rc.recall_id, str) and len(rc.recall_id) == 32                # minted, opaque
    assert rc.recall_id != mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt.recall_id
    for field in (rc.baseline_order, rc.adjusted_order, rc.displaced, rc.admitted, rc.reserved_baseline, rc.reserved_adjusted,
                  list(rc.delta_fused), list(rc.ranks_applied)):
        for v in field:
            assert v in mem.store._conn.execute("SELECT id FROM edges").fetchall().__repr__()   # ids
            assert "boat" not in v and "harbor" not in v                                        # never content
    mem.close()


def test_no_policy_no_receipt_and_an_inert_policy_returns_the_legacy_selection(tmp_path):
    """Without a policy the legacy path runs and `policy_receipt` is None
    (V-COMPAT: a defaulted field). With an INERT policy (no rank on a held id)
    the fused construction runs with the semantic lane empty and returns the
    legacy selection edge for edge (V10's identity, now exercised through
    `recall`), and still no receipt — the lane did not fire."""
    mem = _memory(tmp_path, "r.db")
    plain = mem.recall(U, "boat topic", semantic=False)
    inert = mem.recall(U, "boat topic", semantic=False,
                       policy=PolicyLane(policy_id="demo", policy_version="1", ranks={"ghost": 1}))
    assert plain.policy_receipt is None and inert.policy_receipt is None
    assert [e.id for e in inert.edges] == [e.id for e in plain.edges]
    assert inert.context == plain.context
    mem.close()


def test_the_receipt_baseline_is_the_selection_the_same_call_gives_without_the_policy(tmp_path):
    """The counterfactual is not modelled, it is computed: the receipt's
    `baseline_order` equals what `recall` returns for the same query with no
    policy (the same construction, so the instrument and the mechanism cannot
    disagree — research's replay uses this field as its baseline)."""
    mem = _memory(tmp_path, "r.db")
    plain = mem.recall(U, "boat topic", semantic=False)
    with_policy = mem.recall(U, "boat topic", semantic=False, policy=LANE)
    assert with_policy.policy_receipt.baseline_order == [e.id for e in plain.edges]
    assert "p" in [e.id for e in with_policy.edges] and "p" not in [e.id for e in plain.edges]
    mem.close()


@pytest.mark.parametrize("bad, exc", [
    ("not-a-lane", TypeError),
    ({"p": 1}, TypeError),
])
def test_a_policy_that_is_not_a_policy_lane_is_refused(tmp_path, bad, exc):
    mem = _memory(tmp_path, "r.db")
    with pytest.raises(exc):
        mem.recall(U, "boat topic", policy=bad)
    mem.close()


def test_a_policy_is_not_combinable_with_as_of(tmp_path):
    """The as-of path (0028) has no receipt; a policy there would be the
    untraceable ranking change the receipt exists to prevent — refused."""
    mem = _memory(tmp_path, "r.db")
    with pytest.raises(ValueError, match="not combinable with as_of"):
        mem.recall(U, "boat topic", policy=LANE, as_of=datetime(2026, 1, 1, tzinfo=timezone.utc))
    mem.close()


@pytest.mark.parametrize("kwargs", [
    dict(policy_id="", policy_version="1", ranks={}),
    dict(policy_id="demo", policy_version=" ", ranks={}),
    dict(policy_id="demo", policy_version="1", ranks=[("p", 1)]),
])
def test_a_malformed_policy_lane_is_refused_at_construction(kwargs):
    with pytest.raises((ValueError, TypeError)):
        PolicyLane(**kwargs)


def test_a_malformed_rank_is_refused_before_anything_is_computed(tmp_path):
    """v11's rule, reached through recall: a rank that is not an int ≥ 1 is a
    programming error, refused rather than skipped."""
    mem = _memory(tmp_path, "r.db")
    with pytest.raises(ValueError, match="policy_rank"):
        mem.recall(U, "boat topic", semantic=False, policy=PolicyLane(policy_id="demo", policy_version="1", ranks={"p": 0}))
    mem.close()
