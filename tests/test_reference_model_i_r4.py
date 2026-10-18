"""Model I's round-4 encoding (0044 v1.5, the 0018 amendment v4, the shared 0008 amendment v1.3), checked on its own.

`test_reference_models.py` runs the whole model (every invariant, every mutant). This file names what round 4 added, so
deleting or weakening one of them fails HERE, by name: each round-3 reviewer witness now behaves as the candidate
text says (each was red on the round-3 model first); each round-4 mutant is killed semantically by its owner (the owner
RETURNS False with the mutated path reached); the lifetime derivation equals §4f-ii's table; and the one equivalent
mutant INV-A22 names is recorded as such, never claimed as a kill. A model, not product code (no `veracium` import).
"""
from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys

import pytest

_DIR = pathlib.Path(__file__).resolve().parent.parent / "specs" / "evidence" / "0044"


def _runner():
    name = "arity_run_model_0044"                       # the name obligations.py loads it under: one module per file
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, _DIR / "run_model.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


RUN = _runner()
M = RUN.M

ROUND4_MUTANTS = {
    "end membership only in the reinstate method (round 3's upsert reinstatement keeps it)": "INV-M13",
    "clear the flag only in the invalidate method (round 3's upsert re-retirement keeps it)": "INV-M16",
    "hook only the invalidate and reinstate methods: the upsert derives nothing (R3-01)": "INV-M23",
    "infer the transition from the journal kind: `mutated` hides it (R3-01)": "INV-M23",
    "treat an inactive insert as a retirement (R3-01)": "INV-M23",
    "equal outcome_uid alone admits (round 3's changed-outcome witness)": "INV-M24",
    "replace the slot's row on a different uid (R3-02)": "INV-M24",
    "an arriving applicable copy sets applicable again (R3-02)": "INV-M24",
    "compare undo_request_ref: a second hop conflicts (R3-02)": "INV-M24",
    "grammar-only idempotency: a changed request under a reused id runs (I32)": "INV-M25",
    "one id admitted for plan-only then for restoration: the digest ignores the mode (I32)": "INV-M25",
    "status returns only the last invocation's commits (I32)": "INV-M25",
    "an unlisted carrier constructs (round 3's `_result('unlisted', …)`, I29)": "INV-M26",
    "the carrier omits plan_written (I29)": "INV-M15",
    "hash the whole registry: an unrelated declaration trips registry-changed (I25)": "INV-M14",
    "keep an undo's digest after redaction and replay its result_ref (0008am INV-Q7)": "INV-M27",
    "the terminal rule omitted: a redacted retry reads as a conflict (0008am INV-Q7)": "INV-M27",
    "erasure keeps the refusal inventory (R3-03)": "INV-M18",
    "compare undone_at by value: two stores that each undid the episode refuse (§4l v1.5)": "INV-M24",
    "an ended arrival over an undone held row as an earlier stage: two endings read as one (§4l v1.5)": "INV-M24",
    "the edge row's removal keeps applicable (§4i v1.5)": "INV-M16",
}


def _base_i():
    """The reviewer's `base_i()`: p superseded by n (valid from 2050) under the old `single` arity, then the v16 step."""
    s = M.Store()
    p = M.Edge("p", "u", "measures", "weight 78")
    s.edges[p.id] = p
    M.supersede_single(s, p, M.Edge("n", "u", "measures", "weight 80", valid_from=2050))
    M.schema_step(s)
    return s


def _refuses(f, *a, **kw):
    try:
        f(*a, **kw)
        return False
    except M.Refused:
        return True


# ---------------------------------------------------------------------------- the round-3 witnesses, as the text says
def test_an_unrelated_declaration_change_is_admitted():
    """0018am v4 §4b.2 (R3-03): the digest covers the three reclassified declarations only."""
    s = _base_i()
    M.run_data_migration(s, M.DEFAULT_REGISTRY, op_id="plan", plan_only=True)
    unrelated = copy.deepcopy(M.DEFAULT_REGISTRY)
    unrelated["works_as"] = {"arity": "multi", "functional": False}
    assert M.run_data_migration(s, unrelated, op_id="next")["outcome"] == "migrated"


def test_the_result_carrier_has_plan_written_and_refuses_the_unlisted_carrier():
    """0018am v4 §4c (R3-03): `plan_written` is required; round 3's `_result('unlisted', …)` no longer constructs."""
    r = M.run_data_migration(_base_i(), M.DEFAULT_REGISTRY, op_id="result")
    assert set(r) == set(M.RESULT_FIELDS) and r["plan_written"] is True
    assert _refuses(M._result, "unlisted", False, ["u"], ["u"], "bad")


def test_a_redacted_undo_request_is_terminal():
    """0008am v1.3 §6g (R3-03): the undo's digest is replaced and its retry returns `request_redacted`, before replay;
    0008 v8 §6g (T7): the terminal names the verb holding the id."""
    s = _base_i()
    M.run_data_migration(s, M.DEFAULT_REGISTRY, op_id="restore")
    M.undo(s, "u", "p", correlation_id="undo-request")
    M.redact(s, "p")
    assert s.registry[("u", "undo-request")]["digest"] == M.MARKER
    assert M.undo(s, "u", "p", correlation_id="undo-request") == {"terminal": "request_redacted", "held_by": "undo"}


def test_a_changed_outcome_under_a_held_uid_refuses_the_whole_unit():
    """0044 v1.5 §4l (R3-02): round 3's witness — one field changed under the same uid, beside an unrelated new edge."""
    src = _base_i()
    M.run_data_migration(src, M.DEFAULT_REGISTRY, op_id="restore")
    dst = M.Store(origin="B")
    M.schema_step(dst)
    M.run_data_migration(dst, M.DEFAULT_REGISTRY, op_id="plan", plan_only=True)
    f = M.export(src, "u")
    M.import_file(dst, f, "trusted")
    changed = copy.deepcopy(f)
    changed["outcomes"][("plan-1", "p")]["pre_invalidated_at"] = 1990
    changed["edges"].append(M.Edge("new", "u", "uses_tool", "tool"))
    assert _refuses(M.import_file, dst, changed, "trusted")
    assert "new" not in dst.edges and dst.outcomes[("plan-1", "p")]["pre_invalidated_at"] == 2050


def test_erasure_removes_the_refusal_inventory():
    """R3-03: a recreated user with the same edge ids has no protected historical pair."""
    s = M.Store()
    s.edges = {x: M.Edge(x, "u", "measures", x) for x in ("p", "n")}
    s.refusals.append(("p", "n", "measures", 1))
    M.schema_step(s)
    M.forget_user(s, "u")
    s.edges = {x: M.Edge(x, "u", "measures", "new " + x) for x in ("p", "n")}
    assert M.contested_pairs(s) == [] and not s.refusal_inventory and not s.refusals


def test_a_same_id_upsert_reinstatement_ends_membership_and_its_retirement_clears_applicable():
    """0044 v1.5 §4f-ii (R3-01): the upsert passes the one choke point like every writer."""
    s = _base_i()
    p = copy.deepcopy(s.edges["p"])
    p.active, p.invalidated_at, p.reason = True, None, None
    M.add_edge(s, p)
    assert "p" not in s.inventory
    s = _base_i()
    M.run_data_migration(s, M.DEFAULT_REGISTRY, op_id="restore")
    q = copy.deepcopy(s.edges["p"])
    q.active, q.invalidated_at, q.reason = False, 2050, "superseded"
    M.add_edge(s, q)
    assert s.outcomes[("plan-1", "p")]["applicable"] is False


# ---------------------------------------------------------------------------- the invariants and their mutants, by name
@pytest.mark.parametrize("inv", ["INV-M13", "INV-M14", "INV-M15", "INV-M16", "INV-M18", "INV-M23", "INV-M24", "INV-M25",
                                 "INV-M26", "INV-M27"])
def test_each_invariant_round_4_touched_holds(inv):
    assert RUN.INVARIANTS[inv](RUN.R) is True


@pytest.mark.parametrize("name", sorted(ROUND4_MUTANTS))
def test_each_round_4_mutant_is_killed_semantically_by_its_owner(name):
    """The owner RETURNS False with the mutated path reached; an owner that raises is a harness failure, not a kill."""
    rec = RUN.run_mutant(name, others=False)
    assert rec["owner"] == ROUND4_MUTANTS[name]
    assert rec["owner_outcome"] == "failed" and rec["mutated_path_reached"], rec
    assert all(getattr(M, k) is v for k, v in RUN._O.items()), "a mutant install leaked past its judgement"


def test_the_derivation_is_section_4f_ii_s_table_over_the_whole_lifetime_domain():
    domain = RUN._LIFE_DOMAIN
    diffs = [(p, n) for p in domain for n in domain if n is not None
             and M.derive_transition(p, n) != RUN._transition_oracle(p, n)]
    assert not diffs and len(domain) == 37          # None + 2 × 3 × 3 × 2; None as the NEW row is §4i's removal


def test_the_unchanged_bytes_mutant_is_recorded_as_equivalent_never_claimed():
    """v1.5 as first issued named "derive after the unchanged-bytes return" under INV-A22; the re-issue dropped it as
    EQUIVALENT (an unchanged row has no transition). The runner keeps it as a probe that claims nothing."""
    p = RUN.probes()["equivalent: derive after the unchanged-bytes return"]
    assert p == {"derive(x, x) is None over the lifetime domain": True, "invariants failing under it": []}
    assert not any("unchanged-bytes" in k for k in RUN.MUTANTS)


@pytest.mark.parametrize("held", ["live", "ended", "undone"])
@pytest.mark.parametrize("arriving", ["live", "ended", "undone"])
def test_each_stage_cell_decides_as_section_4l_says(held, arriving):
    """§4l v1.5: equal stages replay; a `live` arrival over a held ending is a no-op; every other difference refuses.
    The two sides carry different `undone_at` values: the value never decides."""
    f = M.export(RUN._migrated(), "u")
    row = f["outcomes"][("plan-1", "p")]
    want = held == arriving or (arriving == "live" and held in ("ended", "undone"))
    assert M.replay_decision(RUN._at_stage(row, held, 7), RUN._at_stage(row, arriving, 99)) is want


def test_the_refusal_inventory_is_keyed_by_refusal_and_user():
    """0044 v1.5 §4f: `refusal_inventory(refusal_id, user_id)`; the model's refusal_id is the (prior, incoming) pair."""
    s = M.Store()
    s.edges = {x: M.Edge(x, "u", "measures", x) for x in ("p", "n")}
    s.refusals.append(("p", "n", "measures", 1))
    M.schema_step(s)
    assert s.refusal_inventory == {(("p", "n"), "u")}
