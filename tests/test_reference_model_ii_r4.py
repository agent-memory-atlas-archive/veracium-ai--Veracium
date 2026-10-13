"""Reference model II at round 4: the round-3 verdict's witnesses (0045-0047 R3-01, R3-02 and the bounded carrier
corrections) as the candidate text decides them (research 5ad5eb1c: 0008am v1.3 §6e/§6f, 0041am v1.4, 0047 v1.9,
0045 v1.9), with the verdict's own positive and negative controls.

Each witness test was written BEFORE the model changed and failed against round 3's model (the reviewer's
`focused_probes.py` observations, reproduced byte-identically at 1fd3e52); each passes on the round-4 model. The model
is loaded BY FILE under a unique name (rule A of tests/test_import_name_collisions.py: an evidence stem is never
imported bare). These are MODEL checks of the rules, not product tests: SQL enforcement, migrations and per-surface
rendering are implementation gates.
"""
from __future__ import annotations

import copy
import importlib.util
import itertools
import pathlib

import pytest

_PATH = pathlib.Path(__file__).resolve().parent.parent / "specs" / "evidence" / "0045" / "grounding_model.py"


def _load():
    import sys
    spec = importlib.util.spec_from_file_location("grounding_model_ii_r4", _PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod                 # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(mod)
    return mod


M = _load()
R = M.Rules()


def edge(i="e", att="not_attested"):
    return M.Edge(i, "u", "works_as", "dentist", att, source_episode="ep")


def admitted(fn) -> bool:
    try:
        fn()
        return True
    except M.Refused:
        return False


def acts(s):
    """A destination's acts, compared by what they ARE (identity, carriers, structure, label), never by row id."""
    return sorted((tuple(a.act_uid or ()), type(a).__name__, getattr(a, "kind", "confirm"), a.origin,
                   getattr(a, "text", None), a.request_digest, a.pos, getattr(a, "confirmed_at", None))
                  for a in s.confirmations + s.replies)


# ================================================================================ R3-01: notice treatment × replay
def test_witness_1_notice_first_arrival_treats_both_carriers_and_replays():
    """The reviewer's II_notice_arrival_and_replay: an ordinary reply restored onto its held redacted target under a
    covering notice is written with BOTH content carriers treated (0008am INV-I4, 0041am INV-RR8), and the same file
    imported again is a no-op."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    r = M.add_reply(src, e, "context", "review text", correlation_id="reply-request")
    dst = M.Store(origin="D"); dst.edges[e.id] = copy.deepcopy(e); M.redact_edge(dst, e.id)
    M.import_rows(dst, [], [], [r], "trusted")
    held = dst.replies[0]
    assert held.text == M.MARKER and held.request_digest == M.MARKER
    snap = copy.deepcopy(vars(dst))
    assert admitted(lambda: M.import_rows(dst, [], [], [r], "trusted"))
    assert vars(dst) == snap


def test_witness_2_record_first_held_act_receives_its_redaction_and_nothing_else():
    """The reviewer's II_noticed_act_update, as 0008am v1.7 INV-I4 decides it: in a TRUSTED RESTORE whose unit carries
    the record showing the redaction, the held ordinary reply receives the treatment and nothing structural changes; a
    repeat is a no-op. Without the record in the unit, the notice is PENDING (record-not-in-file) and nothing changes."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "review text", correlation_id="reply")
    dst = M.Store(origin="D"); M.import_rows(dst, *M.export(src, "u"), "trusted")
    before = copy.deepcopy(dst.replies[0])
    M.redact_edge(src, e.id)
    f = M.export(src, "u")
    nocopy = copy.deepcopy(dst)
    M.import_rows(nocopy, [], f[1], f[2], "trusted", notices=[e.id])
    assert nocopy.replies[0].text == "review text" and [r for _i, r in M.notices_not_applied(nocopy)] == ["record-not-in-file"]
    M.import_rows(dst, *f, "trusted", notices=[e.id])
    after = dst.replies[0]
    assert after.text == M.MARKER and after.request_digest == M.MARKER
    for k in ("id", "edge", "kind", "target", "pos", "act_uid", "origin", "correlation_id", "recorded_correlation_id"):
        assert getattr(after, k) == getattr(before, k), k
    snap = copy.deepcopy(vars(dst))
    M.import_rows(dst, *f, "trusted", notices=[e.id])
    assert vars(dst) == snap


def test_structural_change_under_a_held_uid_refuses_even_when_the_arrival_is_treated():
    """Negative control (0008am INV-I5): the transition changes content carriers only; a treated arrival whose kind
    differs from the held copy's is a conflicting replay."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "review text")
    dst = M.Store(origin="D"); M.import_rows(dst, *M.export(src, "u"), "trusted")
    M.redact_edge(src, e.id)
    f = M.export(src, "u"); f[2][0].kind = "withdrawn-consent"
    assert not admitted(lambda: M.import_rows(dst, [], f[1], f[2], "trusted", notices=[e.id]))
    assert dst.replies[0].text == "review text"


def test_partial_coverage_refuses_the_unit_and_never_enlarges_the_foreign_notice():
    """Negative control (0008am INV-I5, 0041am INV-RR9): a held notice attesting `replies.text` but not
    `replies.request_digest` refuses an ordinary reply onto its target, and the notice is left as it was."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    r = M.add_reply(src, e, "context", "my words")
    dst = M.Store(origin="D"); dst.edges[e.id] = copy.deepcopy(e)
    M.redact_edge(dst, e.id, fields={"edges", "replies.text"})
    bodies = [n.fields for n in dst.notices.values()]
    assert not admitted(lambda: M.import_rows(dst, [], [], [r], "trusted"))
    assert [n.fields for n in dst.notices.values()] == bodies and not dst.replies


def test_a_new_untrusted_act_over_a_held_target_still_refuses():
    """Negative control (rule 3): a NEW default-mode act on an edge held before the import."""
    dst = M.Store(origin="D"); dst.edges["e"] = edge()
    newact = M.Reply(id="x", edge="e", kind="challenge", text="new", pos=("S", 9), act_uid=("S", "u", "x"))
    assert not admitted(lambda: M.import_rows(dst, [], [], [newact], "default"))


def test_second_hop_replays_the_treated_act():
    """Positive control: S → B (trusted; then S's redaction restored with the record showing it) → C (trusted); C then
    receives S's treated file again: a no-op."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "review text")
    b = M.Store(origin="B"); M.import_rows(b, *M.export(src, "u"), "trusted")
    M.redact_edge(src, e.id)
    f = M.export(src, "u")
    M.import_rows(b, *f, "trusted", notices=[e.id])
    c = M.Store(origin="C"); M.import_rows(c, *M.export(b, "u"), "trusted", notices=[e.id])
    snap = copy.deepcopy(vars(c))
    M.import_rows(c, *f, "trusted", notices=[e.id])
    assert vars(c) == snap and c.replies[0].text == M.MARKER


# ================================================================================ R3-01: same-unit identity
def test_two_differing_copies_of_one_act_in_one_unit_refuse_it():
    """The reviewer's II_same_unit_conflicting_uid (0008am INV-I6): HELD is the staged union."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    c = M.confirm(src, e, R, correlation_id="c")
    other = copy.deepcopy(c); other.confirmed_at = 1999
    dst = M.Store(origin="D")
    assert not admitted(lambda: M.import_rows(dst, [e], [c, other], [], "trusted"))
    assert not dst.confirmations


def test_two_equal_copies_of_one_act_in_one_unit_are_one_act():
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    c = M.confirm(src, e, R, correlation_id="c")
    dst = M.Store(origin="D")
    M.import_rows(dst, [e], [c, copy.deepcopy(c)], [], "trusted")
    assert len(dst.confirmations) == 1


# ================================================================================ R3-02: chronology over H
def _late_confirmation_history():
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    ch = M.add_reply(src, e, "challenge", "review challenge")
    late = M.Confirmation("late", e.id, pos=("S", 2), confirmed_at=2025, act_uid=("S", "u", "late"),
                          request_digest="d")
    return e, ch, late


def test_witness_chronology_union_refuses_in_one_file_and_split():
    """The reviewer's II_chronology_union: a confirmation made under an unresolved challenge is refused whether the two
    arrive in one file or the challenge first (0008am INV-Q10, 0047 INV-R23)."""
    e, ch, late = _late_confirmation_history()
    assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [late], [ch], "trusted"))
    split = M.Store(origin="D"); M.import_rows(split, [e], [], [ch], "trusted")
    assert not admitted(lambda: M.import_rows(split, [], [late], [], "trusted"))


def test_witness_valid_resolved_history_restores():
    """The reviewer's II_valid_resolved_history_restore: challenge → resolve → confirm, with the challenge already held,
    is admitted from the later snapshot."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    ch = M.add_reply(src, e, "challenge", "review challenge", correlation_id="ch")
    dst = M.Store(origin="D"); M.import_rows(dst, *M.export(src, "u"), "trusted")
    M.add_reply(src, e, "resolve", None, target=ch.id, correlation_id="resolve")
    M.confirm(src, e, R, correlation_id="confirm")
    M.import_rows(dst, *M.export(src, "u"), "trusted")
    assert len(dst.confirmations) == 1 and M.active_challenges(dst, dst.edges[e.id]) == []


def test_an_incoming_unresolved_challenge_before_a_held_confirmation_refuses():
    e, ch, late = _late_confirmation_history()
    dst = M.Store(origin="D"); M.import_rows(dst, [e], [late], [], "trusted")   # no challenge yet: admitted
    assert not admitted(lambda: M.import_rows(dst, [], [], [ch], "trusted"))


def test_confirmation_before_the_challenge_is_consistent():
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.confirm(src, e, R); M.add_reply(src, e, "challenge", "no")
    dst = M.Store(origin="D"); M.import_rows(dst, *M.export(src, "u"), "trusted")
    assert len(dst.confirmations) == 1 and len(M.active_challenges(dst, dst.edges[e.id])) == 1


def test_ties_unknown_and_incomparable_positions():
    e = edge()
    k1 = M.Confirmation("k1", e.id, pos=("S", 5), act_uid=("S", "u", "k1"), request_digest="d1")
    k2 = M.Confirmation("k2", e.id, pos=("S", 5), act_uid=("S", "u", "k2"), request_digest="d2")
    assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [k1, k2], [], "trusted"))   # a tie
    for pos in (None, ("X", 1)):                                    # unknown, and another origin
        ch = M.Reply("c1", e.id, "challenge", "no", pos=("S", 1), act_uid=("S", "u", "c1"))
        k = M.Confirmation("k", e.id, pos=pos, act_uid=("X", "u", "k"), request_digest="d")
        assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [k], [ch], "trusted"))
        rs = M.Reply("r1", e.id, "resolve", None, pos=("S", 2), target="c1", act_uid=("S", "u", "r1"))
        assert admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [k], [ch, rs], "trusted"))


def test_a_second_resolve_and_a_resolve_before_its_challenge_refuse():
    e = edge()
    ch = M.Reply("c1", e.id, "challenge", "no", pos=("S", 2), act_uid=("S", "u", "c1"))
    r1 = M.Reply("r1", e.id, "resolve", None, pos=("S", 3), target="c1", act_uid=("S", "u", "r1"))
    r2 = M.Reply("r2", e.id, "resolve", None, pos=("S", 4), target="c1", act_uid=("S", "u", "r2"))
    early = M.Reply("r0", e.id, "resolve", None, pos=("S", 1), target="c1", act_uid=("S", "u", "r0"))
    assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [], [ch, r1, r2], "trusted"))
    assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [], [ch, early], "trusted"))
    assert admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [], [ch, r1], "trusted"))


def test_remapping_binds_a_resolve_to_the_imported_challenge_not_a_local_row_with_the_same_id():
    """Remapping control: the destination's own reply `r1`, an open challenge on the SAME edge, is not the file's `r1`;
    the file's resolve closes the file's challenge only."""
    src = M.Store(origin="S"); e = edge("e"); src.edges[e.id] = e
    ch = M.add_reply(src, e, "challenge", "no")
    M.add_reply(src, e, "resolve", None, target=ch.id)
    dst = M.Store(origin="D"); dst.edges["e"] = copy.deepcopy(e)
    mine = M.add_reply(dst, dst.edges["e"], "challenge", "my own")   # local id r1 on the same edge, open
    assert mine.id == ch.id
    M.import_rows(dst, *M.export(src, "u"), "trusted")
    assert [r.act_uid for r in M.active_challenges(dst, dst.edges["e"])] == [mine.act_uid]


def test_row_order_never_changes_the_outcome():
    """Input order (0008am INV-I6): every permutation of a unit's rows gives the same result and the same acts."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    ch = M.add_reply(src, e, "challenge", "no")
    M.add_reply(src, e, "resolve", None, target=ch.id)
    M.confirm(src, e, R)
    edges, confs, reps = M.export(src, "u")
    outcomes = set()
    for perm in itertools.permutations(reps):
        d = M.Store(origin="D")
        ok = admitted(lambda: M.import_rows(d, copy.deepcopy(edges), copy.deepcopy(confs), list(copy.deepcopy(perm)),
                                            "trusted"))
        outcomes.add((ok, tuple(acts(d))))
    assert len(outcomes) == 1 and next(iter(outcomes))[0]


def test_successive_snapshots_give_the_one_file_result():
    """Split control, narrowed to what the text can mean: successive SNAPSHOTS (each file the source's history up to a
    point) give the one-file result. An arbitrary split need not: see the next test."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    ch = M.add_reply(src, e, "challenge", "no")
    snap1 = M.export(src, "u")
    M.add_reply(src, e, "resolve", None, target=ch.id); M.confirm(src, e, R)
    snap2 = M.export(src, "u")
    one = M.Store(origin="D"); M.import_rows(one, *copy.deepcopy(snap2), "trusted")
    two = M.Store(origin="D"); M.import_rows(two, *snap1, "trusted"); M.import_rows(two, *snap2, "trusted")
    assert acts(one) == acts(two)


def test_an_arbitrary_split_is_not_a_snapshot_and_its_first_file_refuses():
    """The design point (0008am v1.3 §6f, research's ruling on dev's counterexample): equivalence holds for one file
    or SUCCESSIVE SNAPSHOTS of the source, and an arbitrary split is not equivalent, BY DESIGN. A file carrying the
    challenge and the confirmation without the resolve between them represents a confirmation under an unresolved
    challenge, and is refused, although the whole history in one file is admitted."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    ch = M.add_reply(src, e, "challenge", "no")
    rs = M.add_reply(src, e, "resolve", None, target=ch.id)
    k = M.confirm(src, e, R)
    assert admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [k], [ch, rs], "trusted"))
    assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [k], [ch], "trusted"))


def test_an_exact_replay_never_exempts_a_new_act_from_chronology():
    """0008am INV-I3: the unit holds a replayed challenge AND a new confirmation made under it."""
    e, ch, late = _late_confirmation_history()
    dst = M.Store(origin="D"); M.import_rows(dst, [e], [], [ch], "trusted")
    assert not admitted(lambda: M.import_rows(dst, [], [late], [ch], "trusted"))


# ================================================================================ bounded carrier corrections
def test_recorded_origin_is_a_normalization_not_a_carrier():
    """The reviewer's II_recorded_origin_carrier: with origin EXCLUDED from the projection there is no model-only
    carrier to delete, and repeated trusted import replays across local → restored and a second hop."""
    assert "recorded_origin" not in M.Confirmation.__dataclass_fields__   # (no model-only carrier to delete)
    assert "recorded_origin" not in M.Reply.__dataclass_fields__
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.confirm(src, e, R, correlation_id="c"); f = M.export(src, "u")
    dst = M.Store(origin="D"); M.import_rows(dst, *f, "trusted")
    assert dst.confirmations[0].origin == "restored"
    assert admitted(lambda: M.import_rows(dst, *f, "trusted"))
    hop = M.Store(origin="H"); M.import_rows(hop, *M.export(dst, "u"), "trusted")
    assert admitted(lambda: M.import_rows(hop, *f, "trusted")) and admitted(lambda: M.import_rows(src, *M.export(hop, "u"), "trusted"))
    assert [c.origin for c in src.confirmations] == ["local"]          # a replay never changes the label


def test_the_label_keeps_its_source_guard_privilege_only():
    """II_label_privilege_scope, unchanged by design: `attested` has no challenge-gate privilege (0047 §4c) but the
    owner's source-redacted confirmation guard still distinguishes it (0045: "no challenge-gate privilege")."""
    for label, want in (("attested", True), ("not_attested", False)):
        s = M.Store(); e = edge(att=label); s.edges[e.id] = e; s.redacted_episodes.add("ep")
        assert admitted(lambda: M.confirm(s, e, R, correlation_id="c")) is want
        s2 = M.Store(); e2 = edge(att=label); s2.edges[e2.id] = e2; M.add_reply(s2, e2, "challenge", "no")
        assert M.gate(s2, e2) == "not_assertable"


def test_undo_is_a_verb_of_the_registry_and_terminal_after_redaction():
    """0008am INV-Q7 for the third verb: after the edge's redaction an undo retry returns request_redacted; before it,
    it replays; its id conflicts with the other verbs both ways."""
    s = M.Store(); e = edge(att="attested"); s.edges[e.id] = e
    first = M.undo(s, e, "outcome:p", correlation_id="u1")
    assert M.undo(s, e, "outcome:p", correlation_id="u1") == first
    assert not admitted(lambda: M.confirm(s, e, R, correlation_id="u1"))
    M.redact_edge(s, e.id)
    assert M.undo(s, e, "outcome:p", correlation_id="u1") == M.REQUEST_REDACTED


def test_attv_is_the_version_of_the_evaluation_and_travels_with_att():
    """0045 INV-G13 and its controls: two coexisting versions; default import writes `default-import`; a file `att`
    with no `attv` restores as version unknown; a second hop keeps the version."""
    s = M.Store(origin="S")
    w = M.write(s, edge("w", att=None), author="user", attested_by_predicate=True)
    assert w.attv == M.PREDICATE_VERSION and M.why(s, w)["version"] == M.PREDICATE_VERSION
    old = edge("o", att="attested"); old.attv = "ATTEST-2@0a1b2c3d"; s.edges["o"] = old
    assert M.why(s, old)["version"] == "ATTEST-2@0a1b2c3d"
    leg = edge("l", att=None); s.edges["l"] = leg
    assert M.why(s, leg)["version"] == "version unknown"
    d = M.Store(origin="D"); M.import_rows(d, *M.export(s, "u"), "default")
    assert {x.attv for x in d.edges.values()} == {"default-import"}
    t = M.Store(origin="T"); M.import_rows(t, *M.export(s, "u"), "trusted")
    t2 = M.Store(origin="T2"); M.import_rows(t2, *M.export(t, "u"), "trusted")
    assert t2.edges["o"].attv == "ATTEST-2@0a1b2c3d" and t2.edges["w"].attv == M.PREDICATE_VERSION
    bare = edge("b", att="attested")                                    # a file att with no attv
    t3 = M.Store(origin="T3"); M.import_rows(t3, [bare], [], [], "trusted")
    assert t3.edges["b"].attv is None and M.why(t3, t3.edges["b"])["version"] == "version unknown"
    bad = edge("x", att="attested"); bad.attv = "v3"
    assert not admitted(lambda: M.import_rows(M.Store(origin="T4"), [bad], [], [], "trusted"))


@pytest.mark.parametrize("name", ["MODEL-G16", "MODEL-G17", "MODEL-G18", "MODEL-G19", "MODEL-G21"])
def test_the_round_4_invariants_exist_and_hold(name):
    spec = importlib.util.spec_from_file_location("grounding_run_model_ii_r4", _PATH.parent / "run_model.py")
    rm = importlib.util.module_from_spec(spec)
    import sys
    sys.path.insert(0, str(_PATH.parent))
    try:
        spec.loader.exec_module(rm)
    finally:
        sys.path.remove(str(_PATH.parent))
    assert rm.INVARIANTS[name](rm.R) is True


# ================================================================================ research's six rulings (round 4)
def test_attv_records_what_produced_att():
    """Ruling 3: `attv` is WHAT produced `att`. A write the author rule decides (a non-USER author, or USER with no
    declared context) records `non-user-effective`, never a predicate version that did not run; the import grammar
    admits it and a trusted restore carries it."""
    s = M.Store(origin="S")
    third = M.write(s, edge("n", att=None), author="third_party", attested_by_predicate=False)
    undeclared = M.write(s, edge("d", att=None), author="user", attested_by_predicate=True, context=None)
    direct = M.write(s, edge("u", att=None), author="user", attested_by_predicate=False)
    assert third.attv == undeclared.attv == M.NON_USER and direct.attv == M.PREDICATE_VERSION
    t = M.Store(origin="T"); M.import_rows(t, *M.export(s, "u"), "trusted")
    assert t.edges["n"].attv == M.NON_USER and M.why(t, t.edges["n"])["version"] == M.NON_USER


def test_attv_is_null_exactly_for_a_null_att_or_a_restore_without_one():
    """Ruling 2: NULL when `att` is NULL (legacy, procedural), or when a trusted restore's file carries `att` without
    `attv` — "version unknown" either way, never the current version."""
    leg = edge("l", att=None); s = M.Store(); s.edges["l"] = leg
    assert leg.attv is None and M.why(s, leg)["version"] == "version unknown"
    pr = M.write(M.Store(), M.Edge(id="p", user="u", relation="procedure", obj="s", att=None, procedural=True),
                 author="user", attested_by_predicate=False)
    assert pr.att is None and pr.attv is None
    t = M.Store(origin="T"); M.import_rows(t, [edge("b", att="attested")], [], [], "trusted")
    assert t.edges["b"].att == "attested" and t.edges["b"].attv is None
    assert M.why(t, t.edges["b"])["version"] == "version unknown"


def test_a_pending_notice_confirmed_treats_held_rows_that_never_arrived():
    """0041am v1.10 §4 (SUPERSEDES v1.4's "an arriving notice treats held carriers whenever it arrives"): a default
    import's notice over a held target treats NOTHING — it is PENDING; the user's confirm_notice then treats every held
    carrier of the target, held acts never in any unit, the destination's own registry rows and the record included."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "my words"); M.confirm(src, e, R)
    d = M.Store(origin="D"); M.import_rows(d, *M.export(src, "u"), "trusted")
    M.add_reply(d, d.edges[e.id], "context", "a local note", correlation_id="ln")
    snap = copy.deepcopy(vars(d))
    M.import_rows(d, [], [], [], "default", notices=[e.id])
    assert {k: v for k, v in vars(d).items() if k != "notices"} == {k: v for k, v in snap.items() if k != "notices"}
    (nid, reason), = M.notices_not_applied(d)
    assert reason == "held-target"
    M.confirm_notice(d, "u", nid)
    assert all(r.text == M.MARKER and r.request_digest == M.MARKER for r in d.replies)
    assert all(c.request_digest == M.MARKER for c in d.confirmations)
    assert all(v[1] == M.MARKER for v in d.registry.values() if v[3] == e.id)
    assert d.edges[e.id].obj == M.MARKER


def test_an_older_notice_refuses_an_arriving_confirmation():
    """Ruling 5: a notice older than the 0008 amendment attests the edge only; a confirmation's one content carrier,
    its request_digest, is not attested, so the unit refuses (intended: confirmations were not exportable then)."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    k = M.confirm(src, e, R)
    d = M.Store(origin="D"); d.edges[e.id] = copy.deepcopy(e); M.redact_edge(d, e.id, covers_replies=False)
    assert not admitted(lambda: M.import_rows(d, [], [k], [], "trusted")) and not d.confirmations


def test_a_file_row_id_naming_two_rows_refuses_unless_one_row_is_repeated():
    """Ruling 6 (0008am v1.3 §6e): one row twice is one act; two different rows under one file id refuse the unit."""
    e = edge()
    a = M.Confirmation("k9", e.id, pos=("S", 40), act_uid=("S", "u", "k9"), request_digest="d")
    b = M.Confirmation("k9", e.id, pos=("S", 41), act_uid=("S", "u", "k9b"), request_digest="d")
    d = M.Store(origin="D"); M.import_rows(d, [e], [a, copy.deepcopy(a)], [], "trusted")
    assert len(d.confirmations) == 1
    assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [e], [a, b], [], "trusted"))


def test_an_act_sent_with_no_request_id_imports_twice_as_a_no_op():
    """Found at round 4, red on round 3's model: with no recorded id, the admitted copy's original id fell back to its
    own internal key, so a repeat import of such an act refused as a conflicting replay (0008am INV-I1)."""
    e = edge()
    k = M.Confirmation("k1", e.id, pos=("S", 1), act_uid=("S", "u", "k1"), request_digest="d")
    d = M.Store(origin="D"); M.import_rows(d, [e], [k], [], "trusted")
    snap = copy.deepcopy(vars(d))
    assert admitted(lambda: M.import_rows(d, [e], [k], [], "trusted")) and vars(d) == snap


def test_an_edges_only_notice_over_held_rows_is_a_total_redaction_by_this_store():
    """Applying a notice to a HELD target is a redaction BY THIS STORE, total under its own treatment map, even when the
    notice is edges-only (INV-I5's held-treatment mutant): in a restore whose unit shows the redaction, and at
    confirm_notice. The foreign body is kept as received; this store attests what it treated."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "restates the fact"); M.confirm(src, e, R)
    held = M.Store(origin="D"); M.import_rows(held, *M.export(src, "u"), "trusted")
    red = copy.deepcopy(held.edges[e.id]); red.relation = red.obj = M.MARKER
    restore = copy.deepcopy(held); M.import_rows(restore, [red], [], [], "trusted", notices={e.id: M.OLD_NOTICE})
    confirm = copy.deepcopy(held); M.import_rows(confirm, [], [], [], "default", notices={e.id: M.OLD_NOTICE})
    (nid, _r), = M.notices_not_applied(confirm)
    M.confirm_notice(confirm, "u", nid)
    for d in (restore, confirm):
        assert all(r.text == M.MARKER and r.request_digest == M.MARKER for r in d.replies)
        assert all(c.request_digest == M.MARKER for c in d.confirmations)
        n, = d.notices.values()
        assert n.fields == M.OLD_NOTICE and M.FULL_NOTICE <= n.treated and n.state == "applied"


def test_a_unit_refused_for_an_uncovered_arriving_row_applies_no_redaction():
    """One transaction: the same edges-only notice, in a unit that also brings an ordinary reply it does not cover
    (the coverage that ADMITS an arriving row is the foreign notice's fields alone), refuses — and treats nothing."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "restates the fact"); M.confirm(src, e, R)
    d = M.Store(origin="D"); M.import_rows(d, *M.export(src, "u"), "trusted")
    fresh = M.Reply("rn", e.id, "context", "a new reply", pos=("S", 50), act_uid=("S", "u", "rn"), request_digest="dn")
    snap = copy.deepcopy(vars(d))
    assert not admitted(lambda: M.import_rows(d, [], [], [fresh], "trusted", notices={e.id: M.OLD_NOTICE}))
    assert vars(d) == snap


# ================================================================================ round 4 final text (research 82fcdb7b)
# 0041am v1.10 §4's one table: a notice takes effect only where a record shows the redaction; refuse where content
# would land; by target state and mode; pending is not an attestation; no rule reads origin. 0008am v1.7 INV-I4 split,
# INV-I7 new. Each test below was RED on the model as it stood before this encoding (dev's round-4 red-first list).
def _held_fact_with_acts(dst_origin="D"):
    """A destination holding S's fact with a reply and a confirmation (restored), and a local request on it."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "restates the fact"); M.confirm(src, e, R)
    d = M.Store(origin=dst_origin); M.import_rows(d, *M.export(src, "u"), "trusted")
    M.add_reply(d, d.edges[e.id], "context", "a local note", correlation_id="ln")
    return src, e, d


def test_default_import_never_changes_a_held_byte_through_a_notice():
    """INV-RR10 / INV-I7: a notice over a HELD target in a default import is PENDING (held-target); the honest treated
    copies of the record and its acts are an exact replay; every held row — the record, its acts, the registry — is
    byte-equal, and the notice is not an attestation."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "restates the fact"); M.confirm(src, e, R)
    d = M.Store(origin="D"); M.import_rows(d, *M.export(src, "u"), "default")
    M.redact_edge(src, e.id); f = M.export(src, "u")
    snap = copy.deepcopy((d.edges, d.replies, d.confirmations, d.registry))
    M.import_rows(d, *f, "default", notices=[e.id])
    assert copy.deepcopy((d.edges, d.replies, d.confirmations, d.registry)) == snap
    assert [r for _i, r in M.notices_not_applied(d)] == ["held-target"] and e.id not in M.redacted_targets(d)


def test_restore_applies_a_held_targets_notice_only_where_the_unit_shows_the_redaction():
    """0041am §4, trusted restore over a HELD target: the unit's record showing the redaction → applied, a redaction by
    THIS STORE (total); no copy and the held record unredacted → PENDING (record-not-in-file), nothing treated; the
    unit's copy UNREDACTED → the whole import refused."""
    src, e, d = _held_fact_with_acts()
    M.redact_edge(src, e.id); f = M.export(src, "u")
    nocopy = copy.deepcopy(d); snap = copy.deepcopy(vars(nocopy)["replies"])
    M.import_rows(nocopy, [], [], [], "trusted", notices=[e.id])
    assert nocopy.replies == snap and [r for _i, r in M.notices_not_applied(nocopy)] == ["record-not-in-file"]
    shows = copy.deepcopy(d); M.import_rows(shows, f[0], [], [], "trusted", notices=[e.id])
    assert all(r.text == M.MARKER and r.request_digest == M.MARKER for r in shows.replies)
    assert e.id in M.redacted_targets(shows)
    unredacted = copy.deepcopy(d)
    clean = M.export(M.Store(origin="S2"), "u")[0] + [copy.deepcopy(d.edges[e.id])]
    assert not admitted(lambda: M.import_rows(unredacted, clean, [], [], "trusted", notices=[e.id]))


def test_a_unit_carrying_a_created_record_unredacted_with_its_notice_refuses_in_either_mode():
    """INV-RR14: content would land under the notice — refused, never applied to the created record (the poisoned
    export), never admitted with the notice skipped or pended."""
    for mode in ("default", "trusted"):
        assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [edge()], [], [], mode, notices=["e"]))


def test_a_same_file_pair_whose_record_shows_the_redaction_is_applied_to_the_created_record():
    for mode in ("default", "trusted"):
        red = edge(); red.relation = red.obj = M.MARKER
        d = M.Store(origin="D"); M.import_rows(d, [red], [], [], mode, notices=["e"])
        assert "e" in M.redacted_targets(d)


def test_a_standing_notice_never_removes_content_and_never_refuses_a_local_write():
    """INV-RR12: absent target → STANDING; not in redacted_targets(); a local write of its id is admitted and never
    completed later; a later created arrival unredacted refuses (both modes); showing → PENDING (default) / applied
    (restore)."""
    d = M.Store(origin="D"); M.import_rows(d, [], [], [], "default", notices=["e"])
    assert "e" not in M.redacted_targets(d) and [n.state for n in d.notices.values()] == ["standing"]
    for mode, want in (("default", "pending"), ("trusted", "applied")):
        x = copy.deepcopy(d)
        assert not admitted(lambda: M.import_rows(x, [edge()], [], [], mode))
        red = edge(); red.relation = red.obj = M.MARKER
        M.import_rows(x, [red], [], [], mode)
        assert {n.state for n in x.notices.values() if n.target == "e"} == {want}
    local = copy.deepcopy(d)
    mine = M.write(local, edge(att=None), author="user", attested_by_predicate=True)
    assert mine is not None
    arrival = copy.deepcopy(mine); arrival.relation = arrival.obj = M.MARKER
    admitted(lambda: M.import_rows(local, [arrival], [], [], "trusted"))      # 0009 refuses it; never completed either way
    assert local.edges["e"].obj == "dentist" and "e" not in M.redacted_targets(local)
    assert [n.state for n in local.notices.values()] == ["standing"]


def test_confirm_notice_applies_a_pending_notice_as_this_stores_total_treatment():
    """INV-RR11: a pending notice refuses no local write; confirm_notice applies it totally, even when the notice is
    edges-only; the foreign body is unchanged."""
    src, e, d = _held_fact_with_acts()
    M.import_rows(d, [], [], [], "default", notices={e.id: M.OLD_NOTICE})
    (nid, _r), = M.notices_not_applied(d)
    M.confirm_notice(d, "u", nid)
    assert all(r.text == M.MARKER and r.request_digest == M.MARKER for r in d.replies)
    assert all(c.request_digest == M.MARKER for c in d.confirmations) and d.notices[nid].fields == M.OLD_NOTICE
    assert e.id in M.redacted_targets(d)


def test_no_rule_reads_a_notices_origin():
    """INV-RR12 (origin binding dropped): store B redacts a record it holds from store A; its notice (origin B) over the
    record (origin A) completes in a restore that shows the redaction, like any other."""
    a = M.Store(origin="A"); M.write(a, edge(att=None), author="user", attested_by_predicate=True)
    b = M.Store(origin="B"); M.import_rows(b, *M.export(a, "u"), "trusted"); M.redact_edge(b, "e")
    nb = next(iter(b.notices.values()))
    c = M.Store(origin="C"); M.import_rows(c, [], [], [], "trusted", notices=[nb])     # standing at C
    M.import_rows(c, M.export(b, "u")[0], [], [], "trusted")
    assert "e" in M.redacted_targets(c)


def test_an_episode_is_a_record_a_notice_can_target():
    """INV-RR14's fourth mutant: the record test covers an episode, not only an edge's own fields."""
    ep = M.Episode("ep1", "u", "what I said")
    assert not admitted(lambda: M.import_rows(M.Store(origin="D"), [ep], [], [], "trusted",
                                              notices={"ep1": frozenset({"episodes"})}))


# ================================================================================ research 14b6fdf6 (0041am v1.11, 0008am v1.8)
def test_a_restore_with_no_copy_over_a_held_record_already_showing_is_total():
    """Ruling (1), INV-RR11 / INV-I7: every application by this store is its TOTAL treatment. The held record already
    shows the redaction (this store's own OLDER redaction treated the edge only), a restore brings a notice and no
    copy: the record's carriers change nothing, and the held reply still carrying content IS treated."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "restates the fact")
    d = M.Store(origin="D"); M.import_rows(d, *M.export(src, "u"), "trusted")
    M.redact_edge(d, e.id, covers_replies=False)                     # an older local redaction: the edge only
    assert d.replies[0].text == "restates the fact"
    M.import_rows(d, [], [], [], "trusted", notices=[e.id])
    assert d.replies[0].text == M.MARKER and d.replies[0].request_digest == M.MARKER


def test_existing_needs_a_notice_for_the_target_in_the_unit():
    """Ruling (5), INV-RR14 / accepted 0041 INV-11: an arrival under this store's completed attestation with NO notice
    for it in the unit is refused; with the notice, it is written in the attestation's treated shape."""
    ex = M.Store(origin="D"); red = edge(); red.relation = red.obj = M.MARKER
    M.import_rows(ex, [red], [], [], "trusted", notices=["e"])
    del ex.edges["e"]                                               # the record gone; its attestation kept
    assert not admitted(lambda: M.import_rows(copy.deepcopy(ex), [edge()], [], [], "default"))
    M.import_rows(ex, [edge()], [], [], "default", notices=["e"])
    assert ex.edges["e"].obj == M.MARKER


def test_a_noticed_held_record_skips_0009_and_reaches_the_held_target_row():
    """Ruling (7), INV-RR10 (measured at the pin, §2c-ii row 12): the held copy came from a RESTORE, so a default
    import's capped copy differs; with a notice for it in the unit, 0041 §4g's held-differs rule skips the copy before
    0009 can refuse, and the notice is weighed: PENDING (held-target), every held byte equal."""
    src = M.Store(origin="S"); e = edge(); src.edges[e.id] = e
    M.add_reply(src, e, "context", "restates the fact")
    d = M.Store(origin="D"); M.import_rows(d, *M.export(src, "u"), "trusted")
    M.redact_edge(src, e.id); f = M.export(src, "u")
    snap = copy.deepcopy((d.edges, d.replies, d.confirmations, d.registry))
    M.import_rows(d, f[0], [], [], "default", notices=[e.id])
    assert copy.deepcopy((d.edges, d.replies, d.confirmations, d.registry)) == snap
    assert [r for _i, r in M.notices_not_applied(d)] == ["held-target"]
    assert not admitted(lambda: M.import_rows(d, f[0], [], [], "default"))      # no notice in the unit: 0009 refuses


# ================================================================================ research 230c868e (0041am v1.12)
def _own_redacted_export():
    s = M.Store(origin="D")
    M.write(s, M.Edge("e-1", "u", "works_as", "dentist", None), author="user", attested_by_predicate=True)
    M.redact_edge(s, "e-1")
    return s, M.export(s, "u")                                 # the record, WITHOUT the notice


def _refusal(fn):
    try:
        fn()
        return None
    except M.Refused as x:
        return str(x)


def test_inv11_refuses_a_stores_own_redacted_record_re_imported_without_its_notice_by_attested_redaction():
    """0041am v1.12 (measured, research 91b87bde): with no notice in the unit, an arrival under this store's completed
    attestation meets INV-11. A DEFAULT import's capped form differs from the store's own record, so its own redacted
    export re-imported without the notice is refused BY INV-11, reason `attested-redaction` (§4g's held-differs
    verdict), not by 0009; a RESTORE of the equal form is an exact no-op; a restore of a CONTENT-CHANGED copy is
    refused by the same INV-11 reason."""
    s, f = _own_redacted_export()
    assert "attested-redaction" in (_refusal(lambda: M.import_rows(copy.deepcopy(s), *f, "default")) or "")
    r = copy.deepcopy(s); snap = copy.deepcopy(vars(r))
    assert _refusal(lambda: M.import_rows(r, *f, "trusted")) is None and vars(r) == snap
    changed = copy.deepcopy(f); changed[0][0].obj = "a different employer"
    assert "attested-redaction" in (_refusal(lambda: M.import_rows(copy.deepcopy(s), *changed, "trusted")) or "")
