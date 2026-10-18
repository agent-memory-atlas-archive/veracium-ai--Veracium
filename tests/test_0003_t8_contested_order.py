"""specs/0003 §4c-iii (v16, the folded amendment `0044/0003-contested-order`): the contested block's GROUP ORDER.

One cell per INV-O row (§4c-iii.8), each through the actual build and render path (`Memory.recall` on a real
SqliteStore, refusals made by the ordinary supersession path) unless it says "pure", and each named for the mutant it
must fail on (§4c-iii.8's column; the scratch campaign is t8_mutant_defs.py). Model I's `order_key` (INV-M9) is the
reference; the last cell compares the product's key with it over the whole small domain.

The kinds, as §4a names them: R = what the renderer EMITS (an assertable exposed member); V = every member VISIBLE to
the principal (every exposed member and every FENCED linkage entry); a policy-hidden (0020 withheld) or UNRESOLVED
member is in neither.
"""
from __future__ import annotations

import importlib.util
import itertools
import math
import pathlib
import random
import re
import sys

from veracium import Memory
from veracium.budgets import floor_for
from veracium.config import MemoryConfig
from veracium.contention import contested_group_key
from veracium.graph import apply_supersession
from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance
from veracium.scope import Identity

ROOT = pathlib.Path(__file__).resolve().parents[1]
U = "u1"
A1 = Identity(None, "agent-1")                     # the principal (0020)
TEAM = {"team-a": [A1]}                            # agent-2's records are cross-scope for A1
USER, SYSTEM, ASSISTANT, THIRD = (EvidenceAuthor.USER, EvidenceAuthor.SYSTEM, EvidenceAuthor.ASSISTANT,
                                  EvidenceAuthor.THIRD_PARTY)
MENTION, QUAR = Disclosure.MENTIONABLE, Disclosure.QUARANTINED
_HEAD = "## CONTESTED FUNCTIONAL FACTS"


def _load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


class _Fake:
    def __call__(self, *a, **k):
        return ""


def _mem(tmp_path, name="m.db", **cfg):
    return Memory(llm=_Fake(), config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                                                   **cfg))


def _e(eid, subject, obj, author=USER, disc=MENTION, source=None):
    return Edge(id=eid, user_id=U, subject=subject, relation="works_as", object=obj,
                provenance=Provenance(author_of_evidence=author, evidence_ref=f"ev-{eid}", disclosure=disc,
                                      source_id=source))


def _group(mem, subject, prior, *challengers):
    """`prior` and each challenger: (author, disclosure, source). The prior is stored; each challenger goes through
    the ordinary supersession path and MUST be refused (asserted: at least one refusal names it as the incoming
    edge — a later challenger is also refused against the earlier ones), so the group is the contention the product
    makes."""
    tag = subject.split(":")[-1]
    a, d, s = prior
    mem.store.add_edge(_e(f"{tag}-p", subject, f"{tag} prior value", a, d, s))
    for k, (a, d, s) in enumerate(challengers):
        apply_supersession(mem.store, _e(f"{tag}-c{k}", subject, f"{tag} challenger value {k}", a, d, s),
                           mem.config.relations)
        assert any(x.incoming_edge_id == f"{tag}-c{k}" for x in mem.store.refusals(U)), (subject, k, "not refused")


def _recall(mem, query="unrelated query", budget=None, principal=None):
    try:
        return mem.recall(U, query, token_budget=budget or floor_for("recall") + 4000, principal=principal)
    except Exception as exc:                                  # noqa: BLE001 — a raise is the property failing
        raise AssertionError(f"recall raised {type(exc).__name__}: {exc}") from exc


def _order(r):
    return [g.subject for g in r.contested]


def _block(r):
    """The block's own lines (the separator before the next section belongs to that section)."""
    return r.context.split(_HEAD, 1)[1].split("\n## ", 1)[0].rstrip("\n") if _HEAD in r.context else ""


def _rendered_subjects(r):
    return re.findall(r"^- (\S+) works_as", _block(r), re.M)


# the block's share of the budget below any line: only the best-effort first line renders (INV-O5)
_ONE_LINE = {"contested_render_share": 0.001}


# ======================================================================================== INV-O1 / O2
def test_inv_o1_a_slot_later_group_with_a_higher_tier_renders_first(tmp_path):
    """INV-O1. Mutant: the key replaced by the slot (today's `sorted(groups.items())`). And what the order does NOT
    move (research's T8 stage-2 S2): `Recall.edges` carries the contested members in the build loop's SLOT order,
    unchanged by T8 (Q4). Mutant: `exposed_all` rebuilt in the group order."""
    mem = _mem(tmp_path)
    _group(mem, "person:aa", (SYSTEM, MENTION, None), (ASSISTANT, MENTION, None))      # tier 2
    _group(mem, "person:zz", (USER, MENTION, None), (SYSTEM, MENTION, None))           # tier 3
    r = _recall(mem)
    assert _order(r) == ["person:zz", "person:aa"]
    assert _rendered_subjects(r) == ["person:zz", "person:aa"]
    assert [e.id for e in r.edges] == ["aa-p", "aa-c0", "zz-p", "zz-c0"]


def test_inv_o2_equal_keys_order_by_slot_and_two_recalls_are_identical(tmp_path):
    """INV-O2. Equal-key groups, made in REVERSE slot order, list by slot ascending; two recalls of one store are
    byte-identical on the context and on `Recall.contested`. Mutant: the slot reversed in the key. (Dropping the slot
    alone is EQUIVALENT here: the build loop walks the groups in slot order and the sort is stable — stated, not
    claimed as a kill.)"""
    mem = _mem(tmp_path)
    for subj in ("person:cc", "person:bb", "person:aa"):
        _group(mem, subj, (USER, MENTION, None), (THIRD, QUAR, None))
    r1, r2 = _recall(mem), _recall(mem)
    assert _order(r1) == ["person:aa", "person:bb", "person:cc"]
    assert r1.context == r2.context and r1.contested == r2.contested


# ======================================================================================== INV-O3
def test_inv_o3_the_report_figures_are_truthful_for_the_order_used(tmp_path):
    """INV-O3. Over a seeded grid of mixed-tier stores (1–3 challengers per group, mixed authorities and
    disclosures, several budgets), the report line's contested figures equal an INDEPENDENT derivation from
    `Recall.contested` and the rendered block (test_0012's `_independent_contested_figures`: renderable groups minus
    rendered lines, the sum of the withheld-value suffixes) — never from `ContestedLoss`. Mutant: the loss counted
    over the slot-ordered list (the pre-reorder counters)."""
    T = _load("budgets_render_0012", ROOT / "tests" / "test_0012_budgets_render.py")
    rng = random.Random(8031)
    challengers = [(SYSTEM, MENTION, None), (ASSISTANT, MENTION, None), (THIRD, QUAR, None), (ASSISTANT, QUAR, None)]
    truncated_runs = 0
    for store_n in range(6):
        mem = _mem(tmp_path, f"g{store_n}.db", contested_members_per_line=2)
        for g in range(8):
            prior = rng.choice([(USER, MENTION, None), (SYSTEM, MENTION, None), (USER, QUAR, None)])
            pa = {USER: 3, SYSTEM: 2}[prior[0]]
            pool = [c for c in challengers if {SYSTEM: 2, ASSISTANT: 1, THIRD: 0}[c[0]] < pa]
            _group(mem, f"person:{rng.choice('mpqx')}{g}", prior, *rng.sample(pool, rng.randint(1, len(pool))))
        for extra in (40, 120, 400):
            r = _recall(mem, budget=floor_for("recall") + extra)
            if T._REPORT.search(r.context):
                T._assert_report_states_the_contested_loss(r)
                truncated_runs += 1
    assert truncated_runs >= 6, truncated_runs            # the grid must actually cut (stated in the cell)


# ======================================================================================== INV-O4
def test_inv_o4_the_query_does_not_reach_the_block(tmp_path):
    """INV-O4, as research's T8 F3 narrowed it. Two queries, one of which SELECTS a fenced member (a query-selected
    non-assertable member moves from linkage to `exposed` on the structured carrier): the block's bytes and the order
    of the RENDERABLE groups are the same. Across tiers (the first store) and within ONE tier (the second, research's
    T8 stage-2 S1 probe: there selection could move only the gap). Mutants: a relevance term in the key (a selected
    member counted as renderable); V dropping a query-selected non-assertable member (research's RT8-1)."""
    mem = _mem(tmp_path)
    _group(mem, "person:aa", (USER, QUAR, None), (SYSTEM, MENTION, None))       # fenced user top: tier 2
    _group(mem, "person:zz", (USER, MENTION, None), (THIRD, QUAR, None))        # tier 3
    plain, selecting = _recall(mem), _recall(mem, "aa prior value")
    assert any(e.id == "aa-p" for g in selecting.contested for e in g.exposed), "the query must select the member"
    assert _block(plain) == _block(selecting)
    renderable = lambda r: [g.subject for g in r.contested if any(e.assertable for e in g.exposed)]  # noqa: E731
    assert renderable(plain) == renderable(selecting) == ["person:zz", "person:aa"]
    same = _mem(tmp_path, "same-tier.db")
    _group(same, "person:zz", (USER, QUAR, None), (SYSTEM, MENTION, None))            # tier 2, gap -1 (a fenced 3)
    _group(same, "person:aa", (SYSTEM, MENTION, None), (ASSISTANT, MENTION, None))    # tier 2, gap 1
    plain, selecting = _recall(same), _recall(same, "zz prior value")
    assert any(e.id == "zz-p" for g in selecting.contested for e in g.exposed), "the query must select the member"
    assert renderable(plain) == renderable(selecting) == ["person:zz", "person:aa"]
    assert _block(plain) == _block(selecting)


# ======================================================================================== INV-O5 / O6 / O8
def test_inv_o5_the_first_line_is_best_effort_unconditional_and_the_highest_tier(tmp_path):
    """INV-O5. A block budget below any line: the first line still renders, and it is the highest-tier group's.
    Mutant: the cut applied to the first line too (`if cost > remaining and sel:` without `and sel`; the line
    builder's `max(remaining, 1)` is NOT what keeps it: dropping that survives, since a line packs at any budget)."""
    mem = _mem(tmp_path, **_ONE_LINE)
    _group(mem, "person:aa", (ASSISTANT, MENTION, None), (THIRD, QUAR, None))
    _group(mem, "person:zz", (USER, MENTION, None), (THIRD, QUAR, None))
    assert _rendered_subjects(_recall(mem)) == ["person:zz"]


def test_inv_o6_a_challenge_never_displaces_a_higher_authority_top(tmp_path):
    """INV-O6. Three assistant-topped groups and one user-topped group, each challenged by third-party content; a
    budget for one line: the user-topped group renders. Mutant: v1.1's key (gap first, tier second)."""
    mem = _mem(tmp_path, **_ONE_LINE)
    for subj in ("person:aa", "person:bb", "person:cc"):
        _group(mem, subj, (ASSISTANT, MENTION, None), (THIRD, MENTION, None))      # tier 1, gap 1
    _group(mem, "person:zz", (USER, MENTION, None), (THIRD, MENTION, None))        # tier 3, gap 3
    assert _rendered_subjects(_recall(mem)) == ["person:zz"]


def test_inv_o8_the_tier_ranks_by_the_renderable_top(tmp_path):
    """INV-O8. A group whose higher-authority member is FENCED (tier 2) against a group with a visible user fact
    (tier 3); one line: the visible user fact renders. Mutant: the tier over exposed ∪ linkage."""
    mem = _mem(tmp_path, **_ONE_LINE)
    _group(mem, "person:aa", (USER, QUAR, None), (SYSTEM, MENTION, None))
    _group(mem, "person:zz", (USER, MENTION, None), (THIRD, QUAR, None))
    r = _recall(mem)
    assert _rendered_subjects(r) == ["person:zz"] and "zz prior value" in _block(r)


# ======================================================================================== INV-O7
def test_inv_o7_groups_follow_0044s_arity(tmp_path):
    """INV-O7, through recall on T5's store: a refusal in the v16 step's refusal inventory keeps its group, and one
    recorded after the step (backdated to 1990, before the era) forms none; a lower-authority differing value under
    the `multi` relation creates no refusal at all. Mutants: group `multi` refusals; drop the retained group."""
    T5 = _load("t5_era_helpers_0044", ROOT / "tests" / "test_0044_t5_era.py")
    p = T5._contention_store(tmp_path)
    mem = T5._mem(p)
    try:
        r = mem.recall(T5.U, "unrelated query")
        ids = {e.id for g in r.contested for e in g.exposed} | {x.edge_id for g in r.contested for x in g.linkage}
        assert ids == {"pre-a", "pre-b"}
        before = len(mem.store.refusals(T5.U))
        apply_supersession(mem.store, T5._edge("new-c", "weight 90 kg", author=EvidenceAuthor.ASSISTANT),
                           mem.config.relations)
        assert len(mem.store.refusals(T5.U)) == before
        ids2 = {e.id for g in mem.recall(T5.U, "unrelated query").contested for e in g.exposed}
        assert "new-c" not in ids2
    finally:
        mem.close()


# ======================================================================================== INV-O9
def test_inv_o9_every_reachable_group_has_a_position(tmp_path):
    """INV-O9, through build and render under a 0020 view: a renderable SINGLETON (its challenger policy-hidden), an
    equal-authority pair (0011's OTHER-subject refusal: user against user, gap 0), a higher-INCOMING refusal (the same
    rule with an assistant prior and a user challenger: the challenger is the top), and a group with nothing
    renderable (both fenced; it survives N-1 because the query selects its fenced member) — each has a position, and
    the no-renderable group is last. Mutants: the gap without its absence case (a singleton raises); a visible
    singleton dropped from the groups."""
    mem = _mem(tmp_path, scope_groups=TEAM)
    _group(mem, "person:aa", (USER, QUAR, "agent-1"), (THIRD, QUAR, "agent-1"))               # nothing renderable
    _group(mem, "person:bb", (USER, MENTION, "agent-1"), (USER, MENTION, "agent-1"))          # tier 3, gap 0
    _group(mem, "person:cc", (ASSISTANT, MENTION, "agent-1"), (USER, MENTION, "agent-1"))     # tier 3, gap 2
    _group(mem, "person:dd", (USER, MENTION, "agent-1"), (SYSTEM, MENTION, "agent-2"))        # singleton: tier 3, +inf
    r = _recall(mem, "aa prior value", principal=A1)
    assert _order(r) == ["person:bb", "person:cc", "person:dd", "person:aa"]
    assert _rendered_subjects(r) == ["person:bb", "person:cc", "person:dd"]


# ======================================================================================== INV-O10 (+ research's F2)
def test_inv_o10_a_policy_hidden_member_is_outside_v(tmp_path):
    """INV-O10, research's T8 F2. The hidden member is ASSERTABLE and of HIGHER authority (a user fact from
    agent-2), so a key that classified members by `assertable` and ignored the view would lift the tier. With it
    hidden: tier 2, gap +inf, so the visible tier-2 neighbour (gap 1) ranks first; with the same member FENCED
    instead (quarantined, own scope): tier 2, gap −1, so it ranks first. The tier never moves. Mutants: every
    `ContestedLinkage` entry counted in V; R/V classified from the members by `assertable`, ignoring `withheld`."""
    hidden = _mem(tmp_path, "h.db", scope_groups=TEAM)
    _group(hidden, "person:aa", (USER, MENTION, "agent-2"), (SYSTEM, MENTION, "agent-1"))
    _group(hidden, "person:zz", (SYSTEM, MENTION, "agent-1"), (ASSISTANT, MENTION, "agent-1"))
    fenced = _mem(tmp_path, "f.db", scope_groups=TEAM)
    _group(fenced, "person:aa", (USER, QUAR, "agent-1"), (SYSTEM, MENTION, "agent-1"))
    _group(fenced, "person:zz", (SYSTEM, MENTION, "agent-1"), (ASSISTANT, MENTION, "agent-1"))
    rh, rf = _recall(hidden, principal=A1), _recall(fenced, principal=A1)
    assert _order(rh) == ["person:zz", "person:aa"]
    assert _order(rf) == ["person:aa", "person:zz"]
    # the published groups the order was computed from: the hidden member is a content-free linkage entry
    gh = next(g for g in rh.contested if g.subject == "person:aa")
    assert [e.id for e in gh.exposed] == ["aa-c0"] and [x.edge_id for x in gh.linkage] == ["aa-p"]


def test_the_key_reads_the_shaped_authority_of_a_cross_visible_member(tmp_path):
    """Research's T8 F2: under `cross_scope_visible`, the view SHAPES a cross-scope member, which is published as
    FENCED linkage at its shaped authority 0 (stored: a user fact, 3). The key must read the published 0: the cross
    group is then tier 2 (its own system fact) with gap 2, and ranks AFTER a tier-2 neighbour with gap 1. Read
    unshaped, its gap would be −1 and it would rank first. Mutant: the key read from the unshaped stored edges."""
    mem = _mem(tmp_path, scope_groups=TEAM, cross_scope_visible=True)
    _group(mem, "person:aa", (USER, MENTION, "agent-2"), (SYSTEM, MENTION, "agent-1"))
    _group(mem, "person:zz", (SYSTEM, MENTION, "agent-1"), (ASSISTANT, MENTION, "agent-1"))
    r = _recall(mem, principal=A1)
    shaped = next(g for g in r.contested if g.subject == "person:aa")
    assert [(x.edge_id, x.authority) for x in shaped.linkage] == [("aa-p", 0)], "the fixture must shape"
    assert _order(r) == ["person:zz", "person:aa"]


# ======================================================================================== §4a's other components
def test_a_negative_gap_ranks_first_within_its_tier(tmp_path):
    """§4a (QO4): a fenced higher-authority member makes the gap negative, and the group ranks FIRST in its tier.
    Mutant: a negative gap ranked last."""
    mem = _mem(tmp_path)
    _group(mem, "person:aa", (SYSTEM, MENTION, None), (ASSISTANT, MENTION, None))      # tier 2, gap 1
    _group(mem, "person:zz", (USER, QUAR, None), (SYSTEM, MENTION, None))              # tier 2, gap -1
    assert _order(_recall(mem)) == ["person:zz", "person:aa"]


def test_more_visible_members_rank_first_at_equal_tier_and_gap(tmp_path):
    """§4a: at equal tier and gap, the group with more visible members ranks first. Mutant: `|V|` ascending."""
    mem = _mem(tmp_path)
    _group(mem, "person:aa", (USER, MENTION, None), (SYSTEM, MENTION, None))                            # |V| 2
    _group(mem, "person:zz", (USER, MENTION, None), (SYSTEM, MENTION, None), (ASSISTANT, MENTION, None))  # |V| 3
    assert _order(_recall(mem)) == ["person:zz", "person:aa"]


# ======================================================================================== the differential (pure)
def test_the_key_agrees_with_model_i_over_the_whole_small_domain():
    """Pure. Every group of 1–4 members, each member an (authority 0–3, kind R/O/U) — 22,620 ordered groups — keyed
    by the product's `contested_group_key` and by model I's `order_key` (R = renderable, O = visible not emitted,
    U = never in V). The domain sorted under each key gives the SAME sequence of tie classes (research's T8 F4: the
    every-pair comparison in n log n), with the slot left out of both keys so every class is compared whole."""
    rm = _load("arity_run_model_0044", ROOT / "specs" / "evidence" / "0044" / "run_model.py")
    kinds = [(a, k) for a in range(4) for k in "ROU"]
    domain = [g for n in range(1, 5) for g in itertools.product(kinds, repeat=n)]
    assert len(domain) == 22620

    def product(g):
        try:
            return contested_group_key("s", "r", [a for a, k in g if k == "R"], [a for a, k in g if k in "RO"])[:4]
        except Exception as exc:                          # noqa: BLE001 — a raise is the key not being total
            raise AssertionError(f"the key raised on {g}: {type(exc).__name__}: {exc}") from exc

    def model(g):
        return rm.M.order_key(list(g))[:4]

    def classes(key):
        ranked = sorted(domain, key=key)
        return [frozenset(c) for _k, c in itertools.groupby(ranked, key=key)]

    assert classes(product) == classes(model)
    assert math.inf in {product(g)[2] for g in domain}
