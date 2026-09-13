"""specs/0027 §4a Stage 2 — the I6 reserve's relevance set, pinned; and the policy
lane's invariant (a policy contributes to `fused_score` only, never to `rel_ext`).

The ordered implementation (research, 2026-09-12, on the owner's word "add a
distinct policy lane parameter that feeds fused_score but not rel_ext"): PIN what
exists first — `rel_ext = relevant_ids | sm_rank` had no test at all — then the
negative control, SEEN TO FAIL against the `sm`-overloading route before the
parameter that satisfies it exists. The two tests are the deliverable as a PAIR:
the control alone could pass by breaking the semantic lane.

The fixture is the unit seam the existing 0027 tests use: `scored` /
`relevant_ids` / `by_id` built directly, so the reserve is exercised with
`max_edges` smaller than the candidate set. The reserve is OBSERVED from the
output: with every candidate assertable and lexically relevant, the first
⌈max_edges/4⌉ positions are the reserve in fused order (V1's own assertion in
test_0027_semantic_recall.py); a candidate that is NOT in `rel_ext` can never
occupy one of them, whatever its fused rank."""

import importlib.util
import pathlib

import pytest

from veracium.graph import RRF_K, fused_subgraph


def _base_module():
    """The 0027 test module's fixture helpers (`_edge`, `U`), loaded by PATH: the
    tests directory is not a package, and `import tests.…` resolved only when
    the invocation happened to put the repo root on sys.path — CI's did not
    (five red jobs at ca4674d, ModuleNotFoundError: No module named 'tests')."""
    path = pathlib.Path(__file__).with_name("test_0027_semantic_recall.py")
    spec = importlib.util.spec_from_file_location("test_0027_semantic_recall_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = _base_module()
U = base.U
_edge = base._edge


def _lexical_fixture(n=12, max_edges=8):
    """n lexically relevant, assertable edges, in a fixed lexical order; the
    reserve holds ⌈max_edges/4⌉ = 2 of them."""
    edges = [_edge(f"x{i:02d}", "user", "likes", f"boat topic{i}", days=i) for i in range(n)]
    scored = [(10 - i * 0.1, 1, e) for i, e in enumerate(edges)]      # (score, overlap>0, edge)
    relevant = {e.id for e in edges}
    by_id = {e.id: e for e in edges}
    return edges, scored, relevant, by_id, max_edges


def _reserve_size(max_edges):
    return -(-max_edges // 4)


# ------------------------------------------------ step 1: pin what exists ----
def test_the_reserve_reads_the_extended_relevance_set_semantic_yes_non_entry_no():
    """CHARACTERISATION (0027 §4a Stage 2, the R2-3 ruling): a semantic-lane entry
    that is not lexically relevant IS reserve-eligible — `rel_ext` extends
    `relevant_ids` by `sm_rank` — and a candidate in neither set is not, however
    high its fused rank. Both halves observed from the output, not the internals."""
    edges, scored, relevant, by_id, max_edges = _lexical_fixture()
    # a semantic-only arrival: assertable, NOT in scored/relevant, in `sm` at rank 1
    sem = _edge("sem", "user", "enjoys", "harbor walks", days=30)
    by_id["sem"] = sem
    out, meta = fused_subgraph(scored, relevant, by_id, [("sem", 0.9)], max_edges=max_edges)
    got = [e.id for e in out]
    assert meta["sem"]["route"] == "semantic" and meta["sem"]["fused_rank"] == 1
    # rank 1 in the semantic lane alone ties lexical rank 1 (both 1/61); the
    # tiebreak is recency and `sem` (day 30) is the newest, so it leads — and
    # it holds a RESERVE slot, which is the claim
    assert got[: _reserve_size(max_edges)] == ["sem", "x00"], got
    # the SAME candidate NOT in the semantic lane but with the SAME fused rank is
    # not eligible: give it lexical rank 1 with overlap 0 (the eligibility floor —
    # a user-subject edge present only via the floor, route "lexical", overlap 0)
    floor = _edge("flr", "user", "enjoys", "hill walks", days=30)
    scored2 = [(99.0, 0, floor)] + scored          # top lexical rank, but overlap 0
    by_id2 = {**by_id, "flr": floor}
    del by_id2["sem"]
    out2, meta2 = fused_subgraph(scored2, relevant, by_id2, [], max_edges=max_edges)
    got2 = [e.id for e in out2]
    assert meta2["flr"]["fused_rank"] == 1 and meta2["flr"]["route"] == "lexical"
    assert "flr" not in got2[: _reserve_size(max_edges)], (
        "a candidate outside rel_ext took a reserve slot: " + str(got2))
    assert got2[: _reserve_size(max_edges)] == ["x00", "x01"], got2


# ------------------------------------------- step 2: the negative control ----
def _apply_policy_via_sm(scored, relevant, by_id, policy, *, max_edges):
    """THE ROUTE ANYONE WOULD REACH FOR — and the hazard: express the policy as a
    semantic-lane list. It ranks the target exactly as the policy lane would
    (research measured it), and it ALSO puts the target in `rel_ext`."""
    sm = sorted(policy, key=policy.get)
    return fused_subgraph(scored, relevant, by_id, [(eid, 0.0) for eid in sm], max_edges=max_edges)


def _apply_policy_via_parameter(scored, relevant, by_id, policy, *, max_edges):
    """The approved design: a distinct parameter that feeds fused_score only."""
    return fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges, policy_rank=policy)


def _policy_target_is_not_reserve_eligible(apply):
    """The invariant, as a function of the route, asserted as the PROPERTY the
    mechanism exists to produce rather than as membership of an internal set
    (research's re-measurement, 2026-09-12): a policy-ranked candidate that is
    neither lexically relevant nor a semantic entry cannot occupy any of the
    ⌈max_edges/4⌉ reserve slots, so at policy rank 1 it lands at EXACTLY the
    first position after the reserve — reserve_n + 1. Through the `sm` route it
    lands at position 1, inside protected evidence. A position assertion
    survives any refactor of how `rel_ext` is computed."""
    edges, scored, relevant, by_id, max_edges = _lexical_fixture()
    target = _edge("pol", "user", "enjoys", "harbor walks", days=30)
    # present via the floor at the BOTTOM of the lexical lane (overlap 0, not
    # relevant, lexical rank 13): without a policy it is outside the budget, so
    # everything observed below is the policy's doing — research's census found
    # the other exception class, a target already returned, and this rules it out
    scored = scored + [(0.0, 0, target)]
    by_id["pol"] = target
    base, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)
    assert "pol" not in [e.id for e in base], "fixture drift: the target must not be returned without a policy"
    out, meta = apply(scored, relevant, by_id, {"pol": 1}, max_edges=max_edges)
    got = [e.id for e in out]
    # PRECONDITION, asserted rather than assumed (research's census, 2026-09-12:
    # 51 of 57 exceptions to the position rule were recalls that did not
    # truncate — when stage3 fits the budget the reserve is never computed and a
    # promoted record correctly sits at position 1; the rule is conditional on
    # truncation, and a fixture that shrinks below the budget would pass here
    # for the wrong reason)
    assert len(scored) > max_edges and len(got) == max_edges, (
        f"fixture no longer truncates ({len(scored)} candidates, budget {max_edges}): the reserve is not exercised")
    assert "pol" in meta, "the policy must rank the target into the selection"
    position = got.index("pol") + 1
    assert position > _reserve_size(max_edges), (
        f"a POLICY-ranked candidate took a protected-reserve slot (position {position}): {got}")
    assert position == _reserve_size(max_edges) + 1, (
        f"the policy target should land at the first slot after the reserve, not {position}: {got}")
    return got, meta


def test_the_sm_route_grants_reserve_eligibility_the_hazard_is_real():
    """STEP 2, SEEN TO FAIL: the control run against the `sm`-overloading route
    must FAIL — the policy target takes a reserve slot. Pinned as the executed
    evidence that the hazard is real; a control never seen to fail is an
    assertion. (This test asserts the FAILURE of the invariant on the wrong
    route, so it stays green after the parameter lands.)"""
    with pytest.raises(AssertionError, match=r"took a protected-reserve slot \(position 1\)"):
        _policy_target_is_not_reserve_eligible(_apply_policy_via_sm)


def test_a_policy_lane_entry_does_not_gain_reserve_eligibility():
    """THE NEGATIVE CONTROL for the approved parameter: `policy_rank` feeds
    `fused_score` only — never `rel_ext`, never Stage 3 membership. Fails until
    step 4 lands (TypeError: no such parameter), then passes; the pair with the
    characterisation test above is the deliverable."""
    got, meta = _policy_target_is_not_reserve_eligible(_apply_policy_via_parameter)
    # the policy DID rank it: lexical rank 13 (1/73) plus policy rank 1 (1/61)
    # outscores every single-lane candidate, so it is FIRST in fused order — yet
    # it sits at reserve_n + 1 in the OUTPUT, because the reserve is taken from
    # rel_ext and it is not in it
    assert meta["pol"]["fused_rank"] == 1, meta["pol"]


# ---------------------------------------- the invariant's other two edges ----
def test_a_policy_id_outside_both_lanes_gets_no_membership_and_a_bad_rank_is_refused():
    """Bullets 1 and 3 of the Stage 2 amendment: a policy id that is neither a
    lexical candidate nor a semantic entry gets no term and NO membership — it
    does not appear in the output or in `meta`, whatever its rank — and a
    malformed rank (0, negative, non-int, bool) is a programming error, refused
    rather than skipped."""
    edges, scored, relevant, by_id, max_edges = _lexical_fixture()
    ghost = _edge("ghost", "user", "enjoys", "harbor walks", days=30)
    by_id["ghost"] = ghost                     # known to the store, in neither lane
    out, meta = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"ghost": 1})
    assert "ghost" not in meta and "ghost" not in [e.id for e in out]
    # and with the policy naming nothing real, the output equals the no-policy output (V10's shape)
    out0, meta0 = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)
    assert [e.id for e in out] == [e.id for e in out0] and meta == meta0
    for bad in (0, -1, 1.5, True, "1"):
        with pytest.raises(ValueError, match="must be an int >= 1"):
            fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"x00": bad})


def test_the_policy_lane_is_inert_when_absent_and_bounded_per_lane():
    """Bullets 4 and 5: `policy_rank=None` and `{}` are byte-identical to the
    two-lane construction (V10's guard, here on the unit seam), and a lane's
    contribution is at most 1/(RRF_K + 1) — three lanes at rank 1 give
    exactly 3/61, the per-lane bound the spec states."""
    edges, scored, relevant, by_id, max_edges = _lexical_fixture()
    base_out, base_meta = fused_subgraph(scored, relevant, by_id, [("x03", 0.9)], max_edges=max_edges)
    for absent in (None, {}):
        out, meta = fused_subgraph(scored, relevant, by_id, [("x03", 0.9)], max_edges=max_edges, policy_rank=absent)
        assert [e.id for e in out] == [e.id for e in base_out] and meta == base_meta
    # x00 is lexical rank 1; make it semantic rank 1 and policy rank 1: three lanes
    out, meta = fused_subgraph(scored, relevant, by_id, [("x00", 0.9)], max_edges=max_edges, policy_rank={"x00": 1})
    assert abs(meta["x00"]["fused_score"] - 3.0 / (RRF_K + 1)) < 1e-12
    assert meta["x00"]["route"] == "both"      # route names the two membership lanes only


def test_a_policy_promotion_displaces_only_the_record_at_the_budget_boundary():
    """The marginal-record property, as v12 states it (v11's version said "the
    previous LAST record", from a census whose fixture had one distinct
    valid_from, so the coverage tail never ran — research's R4-1 instrument
    finding): under truncation, promoting one record that was not already
    returned removes exactly ONE record — the pure-rank HEAD's marginal record —
    and nothing else; the coverage tail's pick survives because novelty is
    judged against the BASELINE head's days (v12), and every other member keeps
    its relative order. Here: reserve x00,x01; head x02..x06; tail x07 (day 7,
    novel). The promotion evicts x06 and leaves x07 in place."""
    edges, scored, relevant, by_id, max_edges = _lexical_fixture()
    target = _edge("pol", "user", "enjoys", "harbor walks", days=30)
    scored = scored + [(0.0, 0, target)]             # bottom of the lexical lane, not returned today
    by_id["pol"] = target
    base, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)
    base_ids = [e.id for e in base]
    assert base_ids == ["x00", "x01", "x02", "x03", "x04", "x05", "x06", "x07"], base_ids
    assert "pol" not in base_ids
    out, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"pol": 1})
    got = [e.id for e in out]
    displaced = [i for i in base_ids if i not in got]
    assert displaced == ["x06"], f"displaced {displaced}, expected only the head's marginal record 'x06'"
    kept = [i for i in got if i != "pol"]
    assert kept == [i for i in base_ids if i != "x06"], "a surviving record moved relative to the others"


# ------------------------------------------------ v12: the owner's R4-2 / R4-1 rulings ----
# "Confirm R4-2; R4-1 too" (the dev session, 2026-09-13; R4-2 first relayed as
# "Option 1 is my decision"). Written RED against v11's code before the change
# that satisfies them, research's order: the property must be seen to fail.

def _eligible_promotion_fixture():
    """The reviewer's R4-2 case: the promoted record is ELIGIBLE for the reserve
    (assertable, lexically relevant — it carries query overlap) and ranked
    beneath every distractor, so a policy promotion can only reach the reserve
    by reordering. Research's first fixture gave the target rank 1 already and
    produced a null in 256/256 configurations; here it is last."""
    edges, scored, relevant, by_id, max_edges = _lexical_fixture()
    target = _edge("tgt", "user", "likes", "boat topic tgt", days=40)
    scored = scored + [(0.1, 1, target)]              # relevant (overlap 1), lowest lexical score
    relevant = relevant | {"tgt"}
    by_id["tgt"] = target
    return scored, relevant, by_id, max_edges


def test_the_reserve_is_identical_with_the_policy_lane_present_and_absent():
    """R4-2 (v12): the I6 reserve is computed on the UNADJUSTED fused order. The
    v11 ruling kept the policy out of the reserve's MEMBERSHIP set (rel_ext) but
    the reserved SLICE was a prefix of the policy-adjusted order, so an eligible
    record promoted to rank 1 took a protected slot. The property the owner
    bought: with the policy lane active, the reserved set is IDENTICAL to the
    reserved set with policy_rank absent — the policy may reorder what is
    returned and may not decide which records are protected from the budget."""
    scored, relevant, by_id, max_edges = _eligible_promotion_fixture()
    n = _reserve_size(max_edges)
    base, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)
    out, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"tgt": 1})
    base_reserve = [e.id for e in base[:n]]
    pol_reserve = [e.id for e in out[:n]]
    assert "tgt" not in base_reserve
    assert pol_reserve == base_reserve, f"the protected slice moved under the policy: {pol_reserve} != {base_reserve}"
    assert "tgt" in [e.id for e in out]              # the promotion still admits the record — through the remainder


def _coverage_fixture():
    """R4-1's mechanism, at the unit seam: two reserved records (days 0, 1), a
    five-record relevance head (days 2, 3, 4, 5, 5 — the boundary record shares
    its day with its neighbour), a coverage tail of one (day 6 novel), one more
    candidate (day 7), and a promoted record OUTSIDE the relevance set whose day
    equals the tail pick's (6). max_edges=8, share=0.25: reserve 2, then
    _cover(rest, 6, 0.25) = head 5 + tail 1. Under v11 the promotion evicts the
    boundary record AND makes day 6 look covered, so the tail re-picks day 7:
    TWO departures from one promotion (the reviewer's finding, reproduced by
    research in 46 of 3,402 configurations)."""
    days = {"x00": 0, "x01": 1, "r1": 2, "r2": 3, "r3": 4, "r4": 5, "r5": 5, "t": 6, "u": 7}
    edges = [_edge(k, "user", "likes", f"boat topic {k}", days=d) for k, d in days.items()]
    scored = [(10 - i * 0.1, 1, e) for i, e in enumerate(edges)]
    relevant = {e.id for e in edges}
    by_id = {e.id: e for e in edges}
    p = _edge("p", "user", "enjoys", "harbor walks", days=6)      # not relevant: overlap 0, outside rel_ext
    scored.append((0.0, 0, p)); by_id["p"] = p
    return scored, relevant, by_id, 8


def test_a_policy_promotion_displaces_at_most_one_record_even_across_the_coverage_tail():
    """R4-1 (v12, research's construction B): `_cover` judges day-novelty against
    the days the BASELINE head covered, never the adjusted head's, so a promotion
    can enter through the pure-rank head and evict its marginal record, and
    cannot redefine which periods look uncovered. Bound: ONE departure per
    promotion; the promoted record is still admitted (research measured B at
    0 of 2,560 configurations displacing more than one, 2,092 of 2,092
    admissions kept)."""
    scored, relevant, by_id, max_edges = _coverage_fixture()
    base, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)
    base_ids = [e.id for e in base]
    assert base_ids == ["x00", "x01", "r1", "r2", "r3", "r4", "r5", "t"], base_ids   # head 5 + the day-6 tail pick
    out, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"p": 1})
    got = [e.id for e in out]
    assert "p" in got, got
    displaced = [i for i in base_ids if i not in got]
    assert len(displaced) <= 1, f"one promotion displaced {displaced}"
    assert displaced == ["r5"], displaced                       # the head's marginal record, and only it


def test_stage_3_membership_never_depends_on_the_policy_order():
    """A probe, not a ruling: Stage 3 adds semantic-only candidates in fused
    order and suppresses a pure duplicate of an already-kept edge, so two
    mutually-duplicate semantic-only records are decided by ORDER. If the policy
    order decided which of the pair survives, membership would be the policy's,
    against v11's own sentence. Asserted so the answer is measured."""
    edges, scored, relevant, by_id, max_edges = _lexical_fixture(n=4, max_edges=8)
    d1 = _edge("d1", "user", "visits", "the harbor cafe", days=20)
    d2 = _edge("d2", "user", "visits", "the harbor cafe", days=21)
    by_id.update({"d1": d1, "d2": d2})
    sm = [("d1", 0.9), ("d2", 0.8)]
    base, _ = fused_subgraph(scored, relevant, by_id, sm, max_edges=max_edges)
    out, _ = fused_subgraph(scored, relevant, by_id, sm, max_edges=max_edges, policy_rank={"d2": 1})
    assert {e.id for e in out} == {e.id for e in base}, (sorted(e.id for e in out), sorted(e.id for e in base))
