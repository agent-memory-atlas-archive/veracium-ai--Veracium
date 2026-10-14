"""Runs package II's reference model on rules draft 3.4 (research 12142443, sha16 b697bda6) + the owner's 2026-10-11 rulings,
with round 4's candidates (research 5ad5eb1c: 0008am v1.3, 0041am v1.4, 0047 v1.9, 0045 v1.9): invariants, mutants
(each must be killed by the invariant that names it, and every invariant owns one), probes. Exit 0 iff all hold. With
`--out <path>` it writes the machine-readable results there."""
from __future__ import annotations

import copy as _copy

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import grounding_model as M  # noqa: E402

R = M.Rules()


def E(i, att="attested", flag=False, ep=None, obj=None, rel="works_as"):
    return M.Edge(id=i, user="u", relation=rel, obj=obj or f"obj-{i}", att=att, ungrounded=flag, source_episode=ep)


def store(*edges):
    s = M.Store()
    for e in edges:
        s.edges[e.id] = e
    return s


# ----------------------------------------------------------------------------------------------- invariants
def inv_g1_legacy(rules=R):
    """MODEL-G1 (R1-02): a legacy row (axis NULL) reads `unknown`, never attested, flagged or not."""
    s = store(E("old", None), E("oldf", None, flag=True))
    return M.grounding(s, s.edges["old"]) == "unknown" and M.grounding(s, s.edges["oldf"]) == "unknown"


def inv_g2_resolution(rules=R):
    """MODEL-G2 (R1-06): context never clears a challenge; resolve clears exactly the one it names; with one open, confirm
    is refused; with all resolved, it is admitted."""
    e = E("e"); s = store(e)
    c1 = M.add_reply(s, e, "challenge", "wrong"); c2 = M.add_reply(s, e, "challenge", "also wrong")
    M.add_reply(s, e, "context", "I withdraw my dispute")
    still = len(M.active_challenges(s, e)) == 2
    M.add_reply(s, e, "resolve", "", target=c1.id)
    one = [r.id for r in M.active_challenges(s, e)] == [c2.id]
    try:
        M.confirm(s, e, rules); blocked = False
    except M.Refused:
        blocked = True
    M.add_reply(s, e, "resolve", "", target=c2.id); M.confirm(s, e, rules)
    return still and one and blocked


def inv_g3_restriction(rules=R):
    """MODEL-G3 (R1-05; 0047 v1.8 INV-R12): no cell promotes an edge an existing gate refused, and under an active
    challenge NO value is assertable — `attested` included (the owner's option 3)."""
    e = E("e"); s = store(e)
    restriction = M.gate(s, e, existing_ok=False) == "not_assertable"
    challenged = []
    for att in ("attested", "not_attested", None):
        c = E(f"c{att}", att); s.edges[c.id] = c
        M.add_reply(s, c, "challenge", "no")
        challenged.append(M.gate(s, c) == "not_assertable")
    return restriction and all(challenged)


def inv_g4_unit(rules=R):
    """MODEL-G4 (0047 v1.8 INV-R3/R6): a challenged fact is WITHHELD on every assertion surface at every budget, whatever
    its value; where it is inspected the unit is present and counts EVERY open challenge, whatever budget trims the
    excerpts shown."""
    e = E("e"); s = store(e)
    for i in range(3):
        M.add_reply(s, e, "challenge", f"no {i}")
    withheld = all(M.render(s, e, b) is None for b in (5, 40, 10_000))
    full, tight = M.inspect(s, e), M.inspect(s, e, budget=5)
    return (withheld and full["open"] == 3 and full["unit"] is not None and "3 open" in full["unit"]
            and tight["open"] == 3 and "3 open" in (tight["unit"] or "") and len(tight["excerpts"]) < 3)


def inv_g5_acts_stay(rules=R):
    """MODEL-G5 (R1-03): absorption never moves a person's act: a prior with a confirmation OR a reply is NOT absorbed
    and keeps it; nothing is copied to the incoming."""
    p = E("p", obj="Miso"); i = E("i", obj="big cat Miso"); s = store(p)
    M.confirm(s, p, rules)
    by_confirmation = (M.absorb(s, p, i, rules) == "not_absorbed" and s.edges["p"].active
                       and not any(c.edge == "i" for c in s.confirmations))
    # the OTHER act (0047 INV-R17): a prior carrying only a REPLY is not absorbed either, and its reply stays on it
    q = E("q", obj="Miso"); j = E("j", obj="big cat Miso"); s2 = store(q)
    M.add_reply(s2, q, "context", "it was my sister's cat")
    by_reply = (M.absorb(s2, q, j, rules) == "not_absorbed" and s2.edges["q"].active
                and [r.edge for r in s2.replies] == ["q"])
    return by_confirmation and by_reply


def inv_g6_survivor_axis(rules=R):
    """MODEL-G6 (§7): an absorption survivor's axis is the INCOMING's own — an attested prior cannot launder a not_attested
    incoming into attested."""
    p = E("p", "attested", obj="Miso"); i = E("i", "not_attested", obj="big cat Miso"); s = store(p)
    M.absorb(s, p, i, rules)
    return M.grounding(s, s.edges["i"]) == "not_attested"


def inv_g7_marker_follows_flag(rules=R):
    """MODEL-G7 (0019 U5): the marker follows the FLAG on every axis value, legacy `unknown` included; an unflagged row
    has none."""
    out = []
    for att in ("attested", "not_attested", None):
        f = E(f"f{att}", att, flag=True); n = E(f"n{att}", att, flag=False); s = store(f, n)
        out.append("[possible extraction error]" in (M.render(s, f, 10_000) or "")
                   and "[possible extraction error]" not in (M.render(s, n, 10_000) or ""))
    return all(out)


def inv_g8_write_path(rules=R):
    """MODEL-G8 ("Label, don't block"): every USER statement is stored — attested iff the predicate recognised it, else
    not_attested; a non-user FLAGGED triple is refused and counted; a non-user unflagged one is stored not_attested."""
    s = M.Store()
    a = M.write(s, E("ua", None), author="user", attested_by_predicate=True)
    b = M.write(s, E("ub", None, flag=True), author="user", attested_by_predicate=False)
    c = M.write(s, E("nf", None, flag=True), author="assistant", attested_by_predicate=False)
    d = M.write(s, E("nu", None), author="third_party", attested_by_predicate=False)
    # the owner's scope ruling: USER with NO declared-direct context is NOT user-effective — it cannot earn attested,
    # its unflagged triple is stored not_attested, its flagged triple is refused
    e1 = M.write(s, E("und", None), author="user", attested_by_predicate=True, context=None)
    e2 = M.write(s, E("undf", None, flag=True), author="user", attested_by_predicate=False, context=None)
    return (a is not None and a.att == "attested" and b is not None and b.att == "not_attested"
            and c is None and d is not None and d.att == "not_attested"
            and e1 is not None and e1.att == "not_attested" and e2 is None
            and s.counts["nonuser_ungrounded_refused"] == 2)


def inv_g9_source_redacted(rules=R):
    """MODEL-G9 ("Add the link", R1-04 kept): confirm() REFUSES a not_attested edge whose recorded source episode is
    redacted; control: the same edge with its source standing is confirmed; a legacy edge (no link) keeps today's
    behaviour."""
    e = E("e", "not_attested", ep="ep1"); s = store(e); s.redacted_episodes.add("ep1")
    try:
        M.confirm(s, e, rules); refused = False
    except M.Refused as x:
        refused = "source-redacted" in str(x)
    c = E("c", "not_attested", ep="ep2"); s2 = store(c); M.confirm(s2, c, rules)
    leg = E("l", None, ep=None); s3 = store(leg); s3.redacted_episodes.add("ep1"); M.confirm(s3, leg, rules)
    return refused and M.grounding(s2, c) == "confirmed" and M.grounding(s3, leg) == "confirmed"


def inv_g10_import(rules=R):
    """MODEL-G10 (R1-07, R1-08): default import writes not_attested and a NULL link whatever the file says, and refuses an
    act aimed at a pre-existing local edge; a fresh round trip is admitted; an orphan is refused; and the 0041
    amendment's reply rows (INV-RR3): a marker reply is admitted iff its unit attests `replies.text`, an ordinary reply
    under such a notice is written treated."""
    s = store(); forged = E("x", "attested", ep="ep9")
    M.import_rows(s, [forged], [], [], "default")
    capped = s.edges["x"].att == "not_attested" and s.edges["x"].source_episode is None
    local = E("loc"); s2 = store(local)
    try:
        M.import_rows(s2, [], [], [M.Reply(id="f", edge="loc", kind="challenge", text="forged")], "default"); attack = False
    except M.Refused:
        attack = True
    s3 = store(); M.import_rows(s3, [E("y")], [], [M.Reply(id="r", edge="y", kind="challenge", text="mine")], "default")
    try:
        M.import_rows(store(), [], [], [M.Reply(id="o", edge="nowhere", kind="context", text="")], "default"); orphan = False
    except M.Refused:
        orphan = True
    # the 0041 amendment's reply rows (INV-RR3): a REDACTED export round-trips through its notice; a marker reply with no
    # notice is a fabricated tombstone and refuses the unit; an ordinary reply under a notice is written treated
    red = E("z", obj=M.MARKER, rel=M.MARKER); s4 = store()           # a redacted record, as an export writes it
    try:
        M.import_rows(s4, [red], [], [M.Reply(id="m", edge="z", kind="challenge", text=M.MARKER)], "default",
                      notices={"z"})
        round_trip = [r.text for r in s4.replies] == [M.MARKER]
    except M.Refused:
        round_trip = False                              # the redacted round trip R1-07 found refused
    try:
        M.import_rows(store(), [E("w")], [], [M.Reply(id="f2", edge="w", kind="challenge", text=M.MARKER)], "default")
        fabricated = False
    except M.Refused:
        fabricated = True
    s5 = store()                                   # the honest same-file pair: the record arrives showing the redaction
    M.import_rows(s5, [E("v", obj=M.MARKER, rel=M.MARKER)], [],
                  [M.Reply(id="o2", edge="v", kind="context", text="I never said that")], "default", notices={"v"})
    treated = [r.text for r in s5.replies] == [M.MARKER]
    # the 0008 amendment's origin rule (INV-Q5; 0047 INV-R21): local → export → DEFAULT import (imported, testimony,
    # not counted) → export → TRUSTED restore — still imported; a local act restored by its own history is `restored`
    # and counts; and a file's correlation id never occupies the destination's id space (INV-Q4)
    src = store(E("h", "not_attested")); src.origin = "store-S"     # a FOREIGN source (rule 0 refuses an own-origin claim)
    M.confirm(src, src.edges["h"], rules, correlation_id="X1")
    b1 = store(); M.import_rows(b1, *M.export(src, "u"), "default")
    testimony = [c.origin for c in b1.confirmations] == ["imported"] and M.grounding(b1, b1.edges["h"]) == "not_attested"
    b2 = store(); M.import_rows(b2, *M.export(b1, "u"), "trusted")
    chain = [c.origin for c in b2.confirmations] == ["imported"] and M.grounding(b2, b2.edges["h"]) == "not_attested"
    b3 = store(); M.import_rows(b3, *M.export(src, "u"), "trusted")
    own = [c.origin for c in b3.confirmations] == ["restored"] and M.grounding(b3, b3.edges["h"]) == "confirmed"
    lying = M.Confirmation(id="kf", edge="g2", origin="local", correlation_id="X2")
    b4 = store(); M.import_rows(b4, [E("g2", "not_attested")], [lying], [], "default")
    no_lie = [c.origin for c in b4.confirmations] == ["imported"]
    try:
        M.confirm(b4, b4.edges["g2"], rules, correlation_id="X2"); ids_free = not any(k[1] == "X2" and v[0] != "confirm"
                                                                                       for k, v in b4.registry.items())
    except M.Refused:
        ids_free = False
    return (capped and attack and "y" in s3.edges and orphan and round_trip and fabricated and treated
            and testimony and chain and own and no_lie and ids_free)


def inv_g11_replay(rules=R):
    """MODEL-G11 (0047 INV-R15; the 0008 amendment's INV-Q1..Q3): ONE request registry for confirm() and add_reply().
    Same id + same verb + same request replays the FIRST result and writes nothing; the id under another request or
    ANOTHER VERB is refused, in BOTH orders; an omitted id has no replay protection. Replay is decided from the registry
    BEFORE live edge state (a confirm retried after the edge was challenged replays, not refuses). The migration backfills
    a pre-upgrade confirmation's id, so a reply cannot reuse it."""
    a, b, c = E("a"), E("b"), E("c"); s = store(a, b, c)
    k1 = M.confirm(s, a, rules, correlation_id="c1")
    try:
        replayed = M.confirm(s, a, rules, correlation_id="c1") is k1 and len(s.confirmations) == 1
    except M.Refused:
        replayed = False                                # a retry must REPLAY, not be refused
    refused = 0
    for f in (lambda: M.confirm(s, b, rules, correlation_id="c1"),                 # another request
              lambda: M.add_reply(s, a, "context", "x", correlation_id="c1"),     # confirm's id, on reply
              lambda: (M.add_reply(s, c, "context", "y", correlation_id="r9"),    # reply's id, on confirm
                       M.confirm(s, c, rules, correlation_id="r9"))):
        try:
            f()
        except M.Refused:
            refused += 1
    r1 = M.add_reply(s, b, "context", "note", correlation_id="r1"); r2 = M.add_reply(s, b, "context", "note", correlation_id="r1")
    try:
        M.add_reply(s, b, "context", "different", correlation_id="r1"); diff = False
    except M.Refused:
        diff = True
    M.add_reply(s, b, "context", "again"); M.add_reply(s, b, "context", "again")
    no_id = sum(1 for r in s.replies if r.text == "again") == 2
    # INV-Q2: the registry before live state — a confirm retried after its edge was challenged returns the original
    d = E("d"); s2 = store(d); k3 = M.confirm(s2, d, rules, correlation_id="c3")
    M.add_reply(s2, d, "challenge", "no")
    try:
        before_live = M.confirm(s2, d, rules, correlation_id="c3") is k3
    except M.Refused:
        before_live = False
    # INV-Q3: a store whose confirmation predates the registry; after the migration its id conflicts on a reply
    f_ = E("f"); s3 = store(f_)
    s3.confirmations.append(M.Confirmation(id="k-old", edge="f", correlation_id="old1"))
    M.migrate_registry(s3)
    try:
        M.add_reply(s3, f_, "context", "z", correlation_id="old1"); backfilled = False
    except M.Refused:
        backfilled = True
    # 0047 INV-R15 / 0008am §6g: `undo` is the registry's third verb; its id conflicts with confirm's, both ways
    u = E("uu"); s4 = store(u)
    M.undo(s4, u, "outcome:p", correlation_id="u1")
    cross_undo = 0
    for f in (lambda: M.confirm(s4, u, rules, correlation_id="u1"),
              lambda: (M.confirm(s4, u, rules, correlation_id="c9"), M.undo(s4, u, "outcome:q", correlation_id="c9"))):
        try:
            f()
        except M.Refused:
            cross_undo += 1
    return (replayed and refused == 3 and r1 is r2 and diff and no_id and before_live and backfilled
            and cross_undo == 2)


def inv_g12_procedural(rules=R):
    """MODEL-G12 (rules draft 3.3; 0047 INV-R19): a post-version PROCEDURAL insert with no att is ADMITTED (ATTEST never
    runs there), carries no grounding (never read as legacy `unknown`), and no reply attaches to it; a declarative row
    keeps its axis (the control)."""
    s = M.Store()
    pr = M.Edge(id="pr", user="u", relation="procedure", obj="step", att=None, procedural=True)
    got = M.write(s, pr, author="user", attested_by_predicate=False, context="direct")
    admitted = got is not None and "pr" in s.edges and got.att is None and M.grounding(s, got) is None
    if not admitted:
        return False
    try:
        M.add_reply(s, got, "challenge", "no"); refused = False
    except M.Refused as x:
        refused = "procedural-edge" in str(x)
    d = M.write(s, E("d", None), author="user", attested_by_predicate=True, context="direct")
    return admitted and refused and M.grounding(s, d) == "attested"


def inv_g13_historical(rules=R):  # 0047 v1.8 INV-R20
    """MODEL-G13 (0047 v1.8 INV-R20): two clocks. T is VALID time and selects facts; acts carry a POSITION (the 0008
    amendment's act ordinal) and are never filtered by T. A fact valid from 10 and challenged NOW (late in act order) is
    WITHHELD as of T=20, attested or not; an unchallenged fact held at T renders (the control); a fact not held at T
    does not."""
    att = E("ha", "attested"); att.valid_from = 10
    na = E("hn", "not_attested"); na.valid_from = 10
    ok = E("ho", "attested"); ok.valid_from = 10
    later = E("hl", "attested"); later.valid_from = 50
    s = store(att, na, ok, later)
    s.act_counter = 100                    # the challenges are written LATE in the store's act order (positions >100)
    for e in (att, na):
        M.add_reply(s, e, "challenge", "that is wrong")
    return (M.render(s, att, 10_000, at=20) is None and M.render(s, na, 10_000, at=20) is None
            and M.render(s, ok, 10_000, at=20) is not None and M.render(s, later, 10_000, at=20) is None)


def inv_g14_erasure(rules=R):
    """MODEL-G14 (0047 INV-R22; the 0008 amendment's INV-Q6): forget_user removes the user's replies, confirmations and
    REGISTRY rows together; a retry after erasure is a new request, not a replay of erased evidence."""
    e = E("e"); s = store(e)
    M.confirm(s, e, rules, correlation_id="z1"); M.add_reply(s, e, "context", "mine", correlation_id="z2")
    M.forget_user(s, "u")
    gone = not s.replies and not s.confirmations and not any(k[0] == "u" for k in s.registry)
    e2 = E("e2"); s.edges["e2"] = e2
    try:
        fresh = M.confirm(s, e2, rules, correlation_id="z1").edge == "e2"
    except M.Refused:
        fresh = False
    return gone and fresh



# ================================================================================ round 3 (package II round-2 verdict)
def _admitted(s, *rows, mode="trusted"):
    """An import the invariant asserts is ADMITTED: a domain refusal is that property failing, returned as False; any
    other exception propagates (a harness defect is never read as a kill)."""
    try:
        M.import_rows(s, *rows, mode)
        return True
    except M.Refused:
        return False


def _foreign(*edges, origin="store-S"):
    s = store(*edges); s.origin = origin
    return s


def inv_g15_key_domains(rules=R):
    """MODEL-G15 (II R2-02; 0008am INV-Q4′): internal act keys fail the caller grammar and caller keys pass it; the
    verdict's sequence — restore a confirmation, then a LOCAL confirm on another edge with a caller id equal to anything
    a prior model generated — is admitted; the reverse order (a local id, then an import whose ORIGINAL id is the same)
    is admitted; repeated imports and both verbs never occupy the caller namespace."""
    src = _foreign(E("e1"), E("e2")); M.confirm(src, src.edges["e1"], rules, correlation_id="c-src")
    M.add_reply(src, src.edges["e2"], "context", "note", correlation_id="r-src")
    dst = store(E("e9"))
    M.import_rows(dst, *M.export(src, "u"), "trusted")
    M.import_rows(dst, *M.export(src, "u"), "trusted")                 # repeated
    keys = [a.correlation_id for a in dst.confirmations + dst.replies]
    grammar = all(not M.CALLER_ID.fullmatch(k) for k in keys) and all(k.startswith("#act:") for k in keys)
    ok = []
    for cid in ("imp-1", "c-src", "r-src", "gen-1"):
        try:
            M.confirm(dst, dst.edges["e9"], rules, correlation_id=cid); ok.append(True)
            dst.confirmations = [c for c in dst.confirmations if c.correlation_id != cid]
            dst.registry.pop(("u", cid), None)
        except M.Refused:
            ok.append(False)
    rev = store(E("e7")); M.confirm(rev, rev.edges["e7"], rules, correlation_id="c-src")
    try:
        M.import_rows(rev, *M.export(src, "u"), "trusted"); reverse = True
    except M.Refused:
        reverse = False
    try:
        M.confirm(dst, dst.edges["e9"], rules, correlation_id=keys[0]); forged = False
    except M.Refused:
        forged = True                                                   # a caller cannot present an internal key
    return grammar and all(ok) and reverse and forged and not any(k[1].startswith("#") for k in dst.registry)


def inv_g16_chronology(rules=R):
    """MODEL-G16 (II R2-03; 0047 INV-R23; 0008am INV-Q9): the restore rule reads POSITION, never the caller's date. A
    same-origin confirmation ordered before an open destination challenge is admitted, one after it refused; an
    incomparable one (another origin, or a legacy unknown position) is refused against an OPEN challenge and admitted
    against a RESOLVED one; a confirmation dated 2025 (`confirmed_at`) made after a 2026 challenge is refused; a default
    file cannot claim the destination's origin; the store-wide counter is never reset by erasure."""
    a = store(E("f")); a.origin = "store-S"
    early = M.confirm(a, a.edges["f"], rules, correlation_id="k1", date=2025)
    M.add_reply(a, a.edges["f"], "challenge", "wrong")
    edges, confs, reps = M.export(a, "u")
    d1 = store(); d1.origin = "store-D"
    M.import_rows(d1, edges, [], reps, "trusted")                     # the challenge arrives first, open
    try:
        M.import_rows(d1, [], confs, [], "trusted"); before = True
    except M.Refused:
        before = False
    b = store(E("g")); b.origin = "store-S"
    M.add_reply(b, b.edges["g"], "challenge", "wrong")
    late = M.Confirmation(id="kl", edge="g", pos=M.next_pos(b), confirmed_at=2025, act_uid=("store-S", "u", "kl"),
                          request_digest="d")                         # made AFTER the challenge, dated BEFORE it
    edges_b, _c, reps_b = M.export(b, "u")
    d2 = store(); d2.origin = "store-D"; M.import_rows(d2, edges_b, [], reps_b, "trusted")
    try:
        M.import_rows(d2, [], [late], [], "trusted"); after_refused = False
    except M.Refused:
        after_refused = True
    d3 = store(E("h")); d3.origin = "store-D"; M.add_reply(d3, d3.edges["h"], "challenge", "mine")
    other = M.Confirmation(id="ko", edge="h", pos=("store-X", 1), act_uid=("store-X", "u", "ko"), request_digest="d")
    legacy = M.Confirmation(id="kg", edge="h", pos=None, act_uid=("store-X", "u", "kg"), request_digest="d")
    refused = []
    for c in (other, legacy):
        try:
            M.import_rows(d3, [], [c], [], "trusted"); refused.append(False)
        except M.Refused:
            refused.append(True)
    ch = d3.replies[0]; M.add_reply(d3, d3.edges["h"], "resolve", None, target=ch.id)
    resolved_ok = _admitted(d3, [], [other], []) and any(c.id == "ko" for c in d3.confirmations)
    d4 = store(); d4.origin = "store-D"
    forged = M.Confirmation(id="kz", edge="z", pos=("store-D", 0), act_uid=("store-D", "u", "kz"), request_digest="d")
    try:
        M.import_rows(d4, [E("z")], [forged], [], "default"); rule0 = False
    except M.Refused:
        rule0 = True
    c5 = store(E("m")); M.confirm(c5, c5.edges["m"], rules, correlation_id="q1")
    exported = c5.confirmations[0].pos
    M.forget_user(c5, "u"); c5.edges["m"] = E("m")
    again = M.confirm(c5, c5.edges["m"], rules, correlation_id="q1")
    never_reset = again.pos[1] > exported[1]
    return (before and after_refused and all(refused) and resolved_ok and rule0 and never_reset
            and _merged_history_checks(rules))


def _late_history():
    """A challenge, then a confirmation made under it (same origin), dated BEFORE it."""
    a = _foreign(E("lh"))
    ch = M.add_reply(a, a.edges["lh"], "challenge", "wrong")
    late = M.Confirmation(id="kl", edge="lh", pos=M.next_pos(a), confirmed_at=2025, act_uid=("store-S", "u", "kl"),
                          request_digest="d")
    return a.edges["lh"], ch, late


def _merged_history_checks(rules) -> bool:
    """0008am v1.3 INV-Q10 / 0047 v1.9 INV-R23 (R3-02): the restore rule over the MERGED history H. The reviewer's two
    witnesses, then the verdict's controls: confirmation before the challenge, resolution before the confirmation,
    ties, unknown and incomparable positions, remapping, and an incoming challenge judged against a HELD confirmation."""
    e, ch, late = _late_history()
    one_file = not _admitted(store(), [e], [late], [ch])                          # the reviewer's one-file witness
    split = store(); M.import_rows(split, [e], [], [ch], "trusted")
    challenge_first = not _admitted(split, [], [late], [])
    src = _foreign(E("vr"))                                                      # the valid resolved-history restore
    c0 = M.add_reply(src, src.edges["vr"], "challenge", "wrong", correlation_id="ch")
    dst = store(); M.import_rows(dst, *M.export(src, "u"), "trusted")
    M.add_reply(src, src.edges["vr"], "resolve", None, target=c0.id, correlation_id="rs")
    M.confirm(src, src.edges["vr"], rules, correlation_id="cf")
    valid = _admitted(dst, *M.export(src, "u")) and len(dst.confirmations) == 1
    held_k = store(); M.import_rows(held_k, [e], [late], [], "trusted")         # an incoming challenge vs a HELD k
    incoming_challenge = not _admitted(held_k, [], [], [ch])
    k1 = M.Confirmation("t1", "lh", pos=("store-S", 7), act_uid=("store-S", "u", "t1"), request_digest="d1")
    k2 = M.Confirmation("t2", "lh", pos=("store-S", 7), act_uid=("store-S", "u", "t2"), request_digest="d2")
    tie = not _admitted(store(), [e], [k1, k2], [])
    unknown = []                                                                 # unknown, and another origin
    for pos in (None, ("store-X", 1)):
        kx = M.Confirmation("kx", "lh", pos=pos, act_uid=("store-X", "u", "kx"), request_digest="d")
        rs = M.Reply("rx", "lh", "resolve", None, pos=("store-S", 5), target=ch.id, act_uid=("store-S", "u", "rx"))
        unknown.append(not _admitted(store(), [e], [kx], [ch]) and _admitted(store(), [e], [kx], [ch, rs]))
    r1 = M.Reply("rv1", "lh", "resolve", None, pos=("store-S", 3), target=ch.id, act_uid=("store-S", "u", "rv1"))
    r2 = M.Reply("rv2", "lh", "resolve", None, pos=("store-S", 4), target=ch.id, act_uid=("store-S", "u", "rv2"))
    r0 = M.Reply("rv0", "lh", "resolve", None, pos=("store-S", 0), target=ch.id, act_uid=("store-S", "u", "rv0"))
    resolves = (not _admitted(store(), [e], [], [ch, r1, r2]) and not _admitted(store(), [e], [], [ch, r0])
                and _admitted(store(), [e], [], [ch, r1]))
    before_ch = _foreign(E("kb")); M.confirm(before_ch, before_ch.edges["kb"], rules)       # k < c: consistent
    M.add_reply(before_ch, before_ch.edges["kb"], "challenge", "no")
    kb = store(); consistent = _admitted(kb, *M.export(before_ch, "u")) and len(kb.confirmations) == 1
    rm_src = _foreign(E("rm")); rc = M.add_reply(rm_src, rm_src.edges["rm"], "challenge", "no")   # remapping: the
    M.add_reply(rm_src, rm_src.edges["rm"], "resolve", None, target=rc.id)                     # destination's own r1
    rm = store(); rm.edges["rm"] = _copy.deepcopy(rm_src.edges["rm"])
    mine = M.add_reply(rm, rm.edges["rm"], "challenge", "mine")
    M.import_rows(rm, *M.export(rm_src, "u"), "trusted")
    remap = mine.id == rc.id and [c.act_uid for c in M.active_challenges(rm, rm.edges["rm"])] == [mine.act_uid]
    return (one_file and challenge_first and valid and incoming_challenge and tie and all(unknown) and resolves
            and consistent and remap)


def inv_g17_repeat_import(rules=R):
    """MODEL-G17 (II R2-04; 0008am INV-I1–I3): importing one file twice, in either mode, leaves the destination
    byte-identical after the first; a changed row under a held act_uid refuses the whole unit; a NEW default act over a
    held fact refuses even when an exact replay on that fact was a no-op; a second hop keeps act_uid and the ORIGINAL
    request id."""
    src = _foreign(E("x"), E("y")); M.confirm(src, src.edges["x"], rules, correlation_id="orig-1")
    M.add_reply(src, src.edges["y"], "challenge", "no", correlation_id="orig-2")
    f = M.export(src, "u")
    import copy as _c
    same = []
    for mode in ("default", "trusted"):
        d = store()
        first = _admitted(d, *f, mode=mode)
        snap = _c.deepcopy(vars(d))
        same.append(first and _admitted(d, *f, mode=mode) and vars(d) == snap)
    d = store(); M.import_rows(d, *f, "trusted")
    changed = _c.deepcopy(f); changed[1][0].confirmed_at = 1999
    try:
        M.import_rows(d, *changed, "trusted"); conflict = False
    except M.Refused:
        conflict = True
    dd = store(); M.import_rows(dd, *f, "default")
    newact = M.Reply(id="r-new", edge="x", kind="challenge", text="new", pos=("store-S", 99), act_uid=("store-S", "u", "r-new"))
    try:
        M.import_rows(dd, [], f[1], [newact], "default"); grant = False
    except M.Refused:
        grant = True
    hop1 = store(); hop1.origin = "store-B"; M.import_rows(hop1, *f, "default")
    hop2 = store(); hop2.origin = "store-C"; M.import_rows(hop2, *M.export(hop1, "u"), "trusted")
    k2 = hop2.confirmations[0]
    second_hop = k2.act_uid == ("store-S", "u", "k1") and k2.recorded_correlation_id == "orig-1"
    return all(same) and conflict and grant and second_hop and _staged_union_checks(rules)


def _acts(s):
    return sorted((tuple(a.act_uid or ()), getattr(a, "kind", "confirm"), a.origin, getattr(a, "text", None),
                   a.request_digest, a.pos) for a in s.confirmations + s.replies)


def _staged_union_checks(rules) -> bool:
    """0008am v1.3 INV-I6 and INV-I3 (R3-01): HELD is the staged union — two differing copies of one act in ONE unit
    refuse it (the reviewer's same-unit witness), two equal copies are one act; the outcome is the same under every row
    order; and an exact replay never exempts a new act in the unit from chronology."""
    src = _foreign(E("su")); k = M.confirm(src, src.edges["su"], rules, correlation_id="c")
    other = _copy.deepcopy(k); other.confirmed_at = 1999
    conflicting = not _admitted(store(), [src.edges["su"]], [k, other], [])
    eq = store(); M.import_rows(eq, [src.edges["su"]], [k, _copy.deepcopy(k)], [], "trusted")
    equal = len(eq.confirmations) == 1
    h = _foreign(E("ho")); hc = M.add_reply(h, h.edges["ho"], "challenge", "no")      # challenge, resolve, confirm,
    M.add_reply(h, h.edges["ho"], "resolve", None, target=hc.id); M.confirm(h, h.edges["ho"], rules)   # export order
    edges, confs, reps = M.export(h, "u")
    outcomes = set()
    import itertools
    for perm in itertools.permutations(reps):
        d = store()
        ok = _admitted(d, _copy.deepcopy(edges), _copy.deepcopy(confs), list(_copy.deepcopy(perm)))
        outcomes.add((ok, tuple(_acts(d))))
    order_free = len(outcomes) == 1 and next(iter(outcomes))[0]
    e, ch, late = _late_history()
    dst = store(); M.import_rows(dst, [e], [], [ch], "trusted")
    no_exemption = not _admitted(dst, [], [late], [ch])                    # the unit replays ch AND brings late
    a = M.Confirmation("k9", "su", pos=("store-S", 40), act_uid=("store-S", "u", "k9"), request_digest="d")
    b = M.Confirmation("k9", "su", pos=("store-S", 41), act_uid=("store-S", "u", "k9b"), request_digest="d")
    dup_equal = store()
    one_row_twice = (_admitted(dup_equal, [src.edges["su"]], [a, _copy.deepcopy(a)], [])
                     and len(dup_equal.confirmations) == 1)
    two_rows_one_id = not _admitted(store(), [src.edges["su"]], [a, b], [])
    idless = store(); M.import_rows(idless, [src.edges["su"]], [a], [], "trusted")      # INV-I1 for an act sent with
    snap = _copy.deepcopy(vars(idless))                                                 # no request id: a repeat is
    idless_repeat = _admitted(idless, [src.edges["su"]], [a], []) and vars(idless) == snap   # a no-op
    return (conflicting and equal and order_free and no_exemption and one_row_twice and two_rows_one_id
            and idless_repeat)


def inv_g18_redacted_requests(rules=R):
    """MODEL-G18 (II R2-05; 0008am INV-Q7; 0041am INV-RR5/RR7; 0047 INV-R24): after an edge's redaction no request
    digest on it survives in confirmations, replies or the registry; a retry under either id returns request_redacted
    for the SAME and for a DIFFERENT payload; a different verb under that id still conflicts; the registry step backfills
    an already-redacted confirmation with the marker; before redaction a reply retry replays its own result after the
    edge changed."""
    s = store(E("e"))
    M.confirm(s, s.edges["e"], rules, correlation_id="kc")
    r1 = M.add_reply(s, s.edges["e"], "context", "my words", correlation_id="kr")
    s.edges["e"].obj = "changed"

    def retry(text, cid):
        try:
            return M.add_reply(s, s.edges["e"], "context", text, correlation_id=cid)
        except M.Refused as x:                                          # a refusal is this property failing
            return f"refused: {x}"
    replay = retry("my words", "kr") is r1
    M.redact_edge(s, "e")
    digests = ([c.request_digest for c in s.confirmations] + [r.request_digest for r in s.replies]
               + [v[1] for v in s.registry.values()])
    clean = all(d == M.MARKER for d in digests)
    same = retry("my words", "kr") == M.REQUEST_REDACTED
    diff = retry("other", "kr") == M.REQUEST_REDACTED
    cross = str(retry("x", "kc")).startswith("refused: integrity conflict")
    old = store(E("o")); M.confirm(old, old.edges["o"], rules, correlation_id="ko")
    old.registry.clear(); M.redact_edge(old, "o"); M.migrate_registry(old)
    backfill = old.registry[("u", "ko")][1] == M.MARKER
    # 0008am v1.3 INV-Q7: the terminal rule precedes replay for EVERY verb — confirm and undo as well as reply
    t = store(E("t")); M.confirm(t, t.edges["t"], rules, correlation_id="tc")
    first_undo = M.undo(t, t.edges["t"], "outcome:p", correlation_id="tu")
    undo_replays = M.undo(t, t.edges["t"], "outcome:p", correlation_id="tu") == first_undo
    M.redact_edge(t, "t")
    try:                                                                # a refusal is this property failing
        terminal = (M.confirm(t, t.edges["t"], rules, correlation_id="tc") == M.REQUEST_REDACTED
                    and M.undo(t, t.edges["t"], "outcome:p", correlation_id="tu") == M.REQUEST_REDACTED)
    except M.Refused:
        terminal = False
    return replay and clean and same and diff and cross and backfill and undo_replays and terminal


def inv_g19_notice_coverage(rules=R):
    """MODEL-G19 (II R2-06; 0041am INV-RR6): an ordinary reply onto a target held redacted under a notice that does NOT
    cover replies.text refuses the unit, and the foreign notice is not rewritten; under a covering notice it is written
    treated; an unredacted target admits it (the positive control)."""
    src = _foreign(E("h")); r = M.add_reply(src, src.edges["h"], "context", "my real employer is Acme")
    old = store(E("h")); M.redact_edge(old, "h", covers_replies=False)
    try:
        M.import_rows(old, [], [], [r], "trusted"); refused = False
    except M.Refused:
        refused = True
    untouched = [n.fields for n in old.notices.values() if n.target == "h"] == [M.OLD_NOTICE] and not old.replies
    cov = store(E("h")); M.redact_edge(cov, "h", covers_replies=True)
    M.import_rows(cov, [], [], [r], "trusted")
    treated = [x.text for x in cov.replies] == [M.MARKER]
    plain = store(E("h")); M.import_rows(plain, [], [], [r], "trusted")
    control = [x.text for x in plain.replies] == ["my real employer is Acme"]
    return refused and untouched and treated and control and _treatment_checks(rules)


def _treatment_checks(rules) -> bool:
    """0008am v1.3 INV-I4/I5 and 0041am v1.4 INV-RR8/RR9 (R3-01): treatment before equality. Notice-first (the
    reviewer's witness 1): both carriers treated and the same file a no-op. Record-first (witness 2): the held copy
    receives the treatment and nothing else. Partial coverage refuses and the held notice is not enlarged; a structural
    change under a held act_uid refuses even when the arrival is treated; a second hop replays the treated act."""
    src = _foreign(E("w1")); r = M.add_reply(src, src.edges["w1"], "context", "review text", correlation_id="rq")
    nf = store(); nf.edges["w1"] = _copy.deepcopy(src.edges["w1"]); M.redact_edge(nf, "w1")
    M.import_rows(nf, [], [], [r], "trusted")
    both = nf.replies[0].text == M.MARKER and nf.replies[0].request_digest == M.MARKER
    snap = _copy.deepcopy(vars(nf))
    notice_first = both and _admitted(nf, [], [], [r]) and vars(nf) == snap
    s2 = _foreign(E("w2")); M.add_reply(s2, s2.edges["w2"], "context", "review text", correlation_id="rq")
    rf = store(); M.import_rows(rf, *M.export(s2, "u"), "trusted")
    held0 = _copy.deepcopy(rf.replies[0])
    M.redact_edge(s2, "w2"); f = M.export(s2, "u")
    try:                                             # a trusted restore whose unit shows the redaction (INV-I4)
        M.import_rows(rf, f[0], f[1], f[2], "trusted", notices=["w2"]); got = True
    except M.Refused:
        got = False
    h1 = rf.replies[0] if rf.replies else None
    record_first = (got and h1 is not None and h1.text == M.MARKER and h1.request_digest == M.MARKER
                    and all(getattr(h1, k) == getattr(held0, k) for k in
                            ("id", "edge", "kind", "target", "pos", "act_uid", "origin", "correlation_id",
                             "recorded_correlation_id")))
    s3 = _foreign(E("w3")); M.add_reply(s3, s3.edges["w3"], "context", "my words")
    part = store(); part.edges["w3"] = _copy.deepcopy(s3.edges["w3"])
    M.redact_edge(part, "w3", fields={"edges", "replies.text"})
    f3 = M.export(s3, "u")
    partial = (not _admitted(part, [], f3[1], f3[2])
               and [n.fields for n in part.notices.values() if n.target == "w3"] == [frozenset({"edges", "replies.text"})]
               and not part.replies)
    s4 = _foreign(E("w4")); M.add_reply(s4, s4.edges["w4"], "context", "review text")
    st = store(); M.import_rows(st, *M.export(s4, "u"), "trusted")
    M.redact_edge(s4, "w4"); f4 = M.export(s4, "u"); f4[2][0].kind = "withdrawn-consent"
    try:
        M.import_rows(st, [], f4[1], f4[2], "trusted", notices=["w4"]); structural = False
    except M.Refused:
        structural = st.replies[0].text == "review text"
    s5 = _foreign(E("w5")); M.add_reply(s5, s5.edges["w5"], "context", "review text")
    b = store(); b.origin = "store-B"; M.import_rows(b, *M.export(s5, "u"), "trusted")
    M.redact_edge(s5, "w5"); f5 = M.export(s5, "u")
    try:
        M.import_rows(b, *f5, "trusted", notices=["w5"])
        c = store(); c.origin = "store-C"; M.import_rows(c, *M.export(b, "u"), "trusted", notices=["w5"])
        snap_c = _copy.deepcopy(vars(c))
        M.import_rows(c, *f5, "trusted", notices=["w5"])
        second_hop = vars(c) == snap_c and c.replies[0].text == M.MARKER
    except M.Refused:
        second_hop = False
    return (notice_first and record_first and partial and structural and second_hop and _held_notice_checks(rules)
            and _binding_checks(rules))


def _held_notice_checks(rules) -> bool:
    """0041am v1.10 §4 / 0008am v1.7 INV-I7 and INV-RR10/RR11: a DEFAULT import never changes a held byte through a
    notice — over a held target it is PENDING (held-target), the held record, its acts and the registry byte-equal, the
    treated arriving copy of a held act an exact replay; a pending notice is no attestation (absent from
    redacted_targets(), refusing no local write); confirm_notice applies it as this store's TOTAL treatment, even an
    edges-only one, the foreign body unchanged; a unit refused for an uncovered arriving row applies nothing; and an
    older notice refuses an arriving confirmation."""
    so = _foreign(E("hn")); M.add_reply(so, so.edges["hn"], "context", "restates the fact")
    M.confirm(so, so.edges["hn"], rules)
    d = store(); M.import_rows(d, *M.export(so, "u"), "default")
    M.redact_edge(so, "hn"); f = M.export(so, "u")
    snap = _copy.deepcopy((d.edges, d.replies, d.confirmations, d.registry))
    try:                                             # the honest pair, by an untrusted file: an exact replay (INV-I7)
        M.import_rows(d, *f, "default", notices=["hn"])
    except M.Refused:
        return False
    pending = (_copy.deepcopy((d.edges, d.replies, d.confirmations, d.registry)) == snap
               and [r for _i, r in M.notices_not_applied(d)] == ["held-target"] and "hn" not in M.redacted_targets(d))
    try:                                             # a local write of the PENDING target's own id is admitted
        local_write = M.write(_copy.deepcopy(d), E("hn"), author="user", attested_by_predicate=True) is not None
    except M.Refused:
        local_write = False
    pend = M.notices_not_applied(d)
    if len(pend) != 1:
        return False
    M.confirm_notice(d, "u", pend[0][0])
    confirmed = (all(x.text == M.MARKER and x.request_digest == M.MARKER for x in d.replies if x.edge == "hn")
                 and all(c.request_digest == M.MARKER for c in d.confirmations) and "hn" in M.redacted_targets(d))
    eo = store(); M.import_rows(eo, *M.export(_hn_source(rules), "u"), "default")       # an EDGES-ONLY notice,
    M.import_rows(eo, [], [], [], "default", notices={"eo": M.OLD_NOTICE})          # confirmed: total all the same
    pend_eo = M.notices_not_applied(eo)
    if len(pend_eo) != 1:
        return False
    eid = pend_eo[0][0]
    M.confirm_notice(eo, "u", eid)
    total = (all(x.text == M.MARKER and x.request_digest == M.MARKER for x in eo.replies)
             and all(c.request_digest == M.MARKER for c in eo.confirmations) and eo.notices[eid].fields == M.OLD_NOTICE)
    rf = store(); M.import_rows(rf, *M.export(_hn_source(rules), "u"), "trusted")
    red = _copy.deepcopy(rf.edges["eo"]); red.relation = red.obj = M.MARKER
    fresh = M.Reply("rn", "eo", "context", "a new reply", pos=("store-S", 50), act_uid=("store-S", "u", "rn"),
                    request_digest="dn")
    snap_rf = _copy.deepcopy(vars(rf))
    refused_unit = not _admitted_with(rf, [red], [fresh], {"eo": M.OLD_NOTICE}) and vars(rf) == snap_rf
    ks = _foreign(E("on")); k = M.confirm(ks, ks.edges["on"], rules)
    old = store(E("on")); M.redact_edge(old, "on", covers_replies=False)
    older_refuses = not _admitted(old, [], [k], []) and not old.confirmations
    return pending and local_write and confirmed and total and refused_unit and older_refuses


def _imp(s, recs, reps, mode, notices) -> bool:
    try:
        M.import_rows(s, recs, [], reps, mode, notices=notices)
        return True
    except M.Refused:
        return False


def _red(i, user="u"):
    e = E(i, obj=M.MARKER, rel=M.MARKER); e.user = user
    return e


def _binding_checks(rules) -> bool:
    """0041am v1.10 §4's one table, row by row (INV-RR12, RR14; 0008am INV-I7's restore half): a notice takes effect
    only where a record SHOWS the redaction, and an import that would land content under it is refused.
    - created by this import, unredacted: REFUSED in both modes (never applied to it, never admitted with the notice
      skipped); showing: APPLIED;
    - held, trusted restore: the unit's copy showing → applied by this store (total); its copy unredacted → REFUSED; no
      copy: the held record showing → applied, removing nothing; not showing → PENDING (record-not-in-file);
    - `existing`: an applied notice arriving again with an unredacted copy → the arrival written treated;
    - absent → STANDING: no attestation, no local-write refusal; a later created arrival unredacted → REFUSED in both
      modes; showing → PENDING (default) / APPLIED (restore); a locally written id is never completed;
    - no rule reads origin (a B-over-A notice completes); an episode is a record like an edge."""
    created = all(not _imp(store(), [E("c1")], [], mode, ["c1"]) and _imp(store(), [_red("c1")], [], mode, ["c1"])
                  for mode in ("default", "trusted"))
    sa = store(); created = created and _imp(sa, [_red("c1")], [], "default", ["c1"]) and "c1" in M.redacted_targets(sa)
    so = _foreign(E("hb")); M.add_reply(so, so.edges["hb"], "context", "restates the fact")
    d = store(); M.import_rows(d, *M.export(so, "u"), "trusted")
    clean_copy = _copy.deepcopy(so.edges["hb"])
    M.redact_edge(so, "hb"); f = M.export(so, "u")
    shows = _copy.deepcopy(d)
    restore_shows = (_imp(shows, f[0], [], "trusted", ["hb"]) and "hb" in M.redacted_targets(shows)
                     and all(x.text == M.MARKER and x.request_digest == M.MARKER for x in shows.replies))
    restore_unredacted = not _imp(_copy.deepcopy(d), [clean_copy], [], "trusted", ["hb"])
    nocopy = _copy.deepcopy(d); snap = _copy.deepcopy((nocopy.edges, nocopy.replies))
    restore_nocopy = (_imp(nocopy, [], [], "trusted", ["hb"])
                      and _copy.deepcopy((nocopy.edges, nocopy.replies)) == snap
                      and [r for _i, r in M.notices_not_applied(nocopy)] == ["record-not-in-file"])
    hs = store(); M.import_rows(hs, [_red("hs")], [], [], "trusted", notices=["hs"])      # held, already showing
    snap_hs = _copy.deepcopy((hs.edges, hs.replies, hs.confirmations, hs.registry))
    attest_only = (_imp(hs, [], [], "trusted", {"hs": M.OLD_NOTICE})
                   and _copy.deepcopy((hs.edges, hs.replies, hs.confirmations, hs.registry)) == snap_hs
                   and not M.notices_not_applied(hs) and all(n.state == "applied" for n in hs.notices.values()))
    ex = store(); M.import_rows(ex, [_red("ex")], [], [], "trusted", notices=["ex"])
    del ex.edges["ex"]                                # the record gone; its applied notice kept
    existing = _imp(ex, [E("ex")], [], "default", ["ex"]) and ex.edges["ex"].obj == M.MARKER
    st = store(); M.import_rows(st, [], [], [], "default", notices=["s1"])
    standing = "s1" not in M.redacted_targets(st) and [n.state for n in st.notices.values()] == ["standing"]
    for mode, want in (("default", "pending"), ("trusted", "applied")):
        x = _copy.deepcopy(st)
        standing = (standing and not _imp(x, [E("s1")], [], mode, ()) and _imp(x, [_red("s1")], [], mode, ())
                    and [n.state for n in x.notices.values()] == [want])
    loc = _copy.deepcopy(st)
    try:
        mine = M.write(loc, E("s1", None), author="user", attested_by_predicate=True)
    except M.Refused:
        mine = None
    never = False
    if mine is not None:                              # admitted or refused by 0009, it is never COMPLETED
        arrival = _copy.deepcopy(mine); arrival.relation = arrival.obj = M.MARKER
        _imp(loc, [arrival], [], "trusted", ())
        admitted_other = _imp(loc, [E("unrelated")], [], "trusted", ())     # an ADMITTED import meets the standing
        never = (admitted_other and loc.edges["s1"].obj != M.MARKER and "s1" not in M.redacted_targets(loc)
                 and [n.state for n in loc.notices.values()] == ["standing"])
    a = _foreign(); a.origin = "store-A"; M.write(a, E("og", None), author="user", attested_by_predicate=True)
    b = store(); b.origin = "store-B"; M.import_rows(b, *M.export(a, "u"), "trusted"); M.redact_edge(b, "og")
    nb = next(iter(b.notices.values()))
    c = store(); c.origin = "store-C"; M.import_rows(c, [], [], [], "trusted", notices=[nb])
    origin_free = _imp(c, M.export(b, "u")[0], [], "trusted", ()) and "og" in M.redacted_targets(c)
    epi = (not _imp(store(), [M.Episode("ep1", "u", "what I said")], [], "trusted", {"ep1": frozenset({"episodes"})})
           and _imp(store(), [M.Episode("ep1", "u", M.MARKER)], [], "trusted", {"ep1": frozenset({"episodes"})}))
    return (created and restore_shows and restore_unredacted and restore_nocopy and attest_only and existing
            and standing and never and origin_free and epi and _v111_checks(rules))


def _v111_checks(rules) -> bool:
    """0041am v1.11 / 0008am v1.8 (research 14b6fdf6), the eight rulings that are rows' named mutants:
    (1) a restore with NO copy over a held record already showing the redaction is TOTAL — a held reply still carrying
        content is treated (this store's own OLDER redaction treated the edge only);
    (5) `existing` needs a notice for the target IN THE UNIT: with none, an arrival under a completed attestation is
        refused (accepted 0041 INV-11); with it, written treated;
    (7) a held copy from a RESTORE, a default import's capped copy differing, a notice for it in the unit: skipped,
        never written, the notice PENDING (held-target), every held byte equal; with no notice, 0009 refuses;
    (2) a pending standing arrival is listed with reason `standing-arrival`;
    (3) a pending notice re-arriving: `existing` in a default import, APPLIED in a restore whose unit shows it (its body
        unchanged);
    (4) an import that re-creates a pending notice's target leaves it PENDING."""
    so = _foreign(E("t1")); M.add_reply(so, so.edges["t1"], "context", "restates the fact")
    d1 = store(); M.import_rows(d1, *M.export(so, "u"), "trusted")
    M.redact_edge(d1, "t1", covers_replies=False)                 # the edge only: a held reply keeps its content
    total = (d1.replies[0].text != M.MARKER and _imp(d1, [], [], "trusted", ["t1"])
             and d1.replies[0].text == M.MARKER and d1.replies[0].request_digest == M.MARKER)
    ex = store(); M.import_rows(ex, [_red("x5")], [], [], "trusted", notices=["x5"]); del ex.edges["x5"]
    needs_notice = (not _imp(_copy.deepcopy(ex), [E("x5")], [], "default", ())
                    and _imp(ex, [E("x5")], [], "default", ["x5"]) and ex.edges["x5"].obj == M.MARKER)
    s7 = _foreign(E("t7")); M.add_reply(s7, s7.edges["t7"], "context", "restates the fact")
    d7 = store(); M.import_rows(d7, *M.export(s7, "u"), "trusted")            # held from a RESTORE
    M.redact_edge(s7, "t7"); f7 = M.export(s7, "u")
    snap7 = _copy.deepcopy((d7.edges, d7.replies, d7.confirmations, d7.registry))
    skipped = (_imp(d7, f7[0], [], "default", ["t7"])
               and _copy.deepcopy((d7.edges, d7.replies, d7.confirmations, d7.registry)) == snap7
               and [r for _i, r in M.notices_not_applied(d7)] == ["held-target"]
               and not _imp(_copy.deepcopy(d7), f7[0], [], "default", ()))
    st = store(); M.import_rows(st, [], [], [], "default", notices=["s2"])
    listed = (_imp(st, [_red("s2")], [], "default", ())
              and [r for _i, r in M.notices_not_applied(st)] == ["standing-arrival"])
    s3 = _foreign(E("t3")); M.add_reply(s3, s3.edges["t3"], "context", "restates the fact")
    d3 = store(); M.import_rows(d3, *M.export(s3, "u"), "default")
    M.redact_edge(s3, "t3"); f3 = M.export(s3, "u")
    M.import_rows(d3, [], [], [], "default", notices={"t3": M.OLD_NOTICE})
    body = [n.fields for n in d3.notices.values()]
    again = _copy.deepcopy(d3)
    default_existing = (_imp(again, [], [], "default", {"t3": M.OLD_NOTICE})
                        and [n.state for n in again.notices.values()] == ["pending"])
    red3 = _copy.deepcopy(d3.edges["t3"]); red3.relation = red3.obj = M.MARKER
    restore_applies = (_imp(d3, [red3], [], "trusted", {"t3": M.OLD_NOTICE})
                       and [n.state for n in d3.notices.values()] == ["applied"]
                       and [n.fields for n in d3.notices.values()] == body and d3.replies[0].text == M.MARKER)
    s4 = _foreign(E("t4"))
    d4 = store(); M.import_rows(d4, *M.export(s4, "u"), "trusted")
    M.import_rows(d4, [], [], [], "default", notices=["t4"])                  # pending (held-target)
    del d4.edges["t4"]                                                         # its target deleted: inert
    recreated = (_imp(d4, [E("t4")], [], "trusted", ()) and [n.state for n in d4.notices.values()] == ["pending"])
    own, f_own = _own_redacted(rules)                # 0041am v1.12: INV-11 by `attested-redaction`
    default_inv11 = "attested-redaction" in (_refused_with(_copy.deepcopy(own), *f_own, mode="default") or "")
    snap_own = _copy.deepcopy(vars(own)); r_own = _copy.deepcopy(own)
    restore_noop = _refused_with(r_own, *f_own, mode="trusted") is None and vars(r_own) == snap_own
    changed = _copy.deepcopy(f_own); changed[0][0].obj = "a different employer"
    changed_inv11 = "attested-redaction" in (_refused_with(_copy.deepcopy(own), *changed, mode="trusted") or "")
    return (total and needs_notice and skipped and listed and default_existing and restore_applies and recreated
            and default_inv11 and restore_noop and changed_inv11 and _pending_repeat_is_existing())


def _pending_repeat_is_existing() -> bool:
    """Round-4 IO-II-1 (the reviewer's two sequences, pending_repeat_probe.py): a notice held PENDING with a reason other
    than `held-target`, met again by a default import of the same notice alone, is `existing` — the WHOLE store equal
    before and after, its pending row and reason included (a state-only comparison let the reason be rewritten)."""
    ok = True
    for case in ("restore-pending-then-default", "default-standing-arrival-then-repeat"):
        s = M.Store(origin="D"); n = M.Notice("n", "e", M.FULL_NOTICE, origin="S")
        if case == "restore-pending-then-default":            # restore without the target's copy: record-not-in-file
            s.edges["e"] = M.Edge("e", "u", "works_as", "dentist", "not_attested")
            M.import_rows(s, [], [], [], "trusted", notices=[n])
            want = "record-not-in-file"
        else:                                                  # notice first, then a treated arrival: standing-arrival
            M.import_rows(s, [], [], [], "default", notices=[n])
            M.import_rows(s, [M.Edge("e", "u", M.MARKER, M.MARKER, "not_attested")], [], [], "default")
            want = "standing-arrival"
        before = _copy.deepcopy(s)
        ok = ok and (before.notices["n"].state, before.notices["n"].reason) == ("pending", want)   # the precondition
        ok = ok and _imp(s, [], [], "default", [n]) and s == before
    return ok


def _own_redacted(rules):
    s = store(); s.origin = "store-O"
    M.write(s, E("e-1", None), author="user", attested_by_predicate=True)
    M.redact_edge(s, "e-1")
    return s, M.export(s, "u")                        # the record, WITHOUT the notice


def _refused_with(s, *rows, mode):
    try:
        M.import_rows(s, *rows, mode)
        return None
    except M.Refused as x:
        return str(x)


def _hn_source(rules):
    so = _foreign(E("eo")); M.add_reply(so, so.edges["eo"], "context", "restates the fact")
    M.confirm(so, so.edges["eo"], rules)
    return so


def _admitted_with(s, recs, reps, notices) -> bool:
    try:
        M.import_rows(s, recs, [], reps, "trusted", notices=notices)
        return True
    except M.Refused:
        return False


def inv_g20_canonical(rules=R):
    """MODEL-G20 (0008am INV-Q8): act identity is hashed over a canonical JSON array — a separator inside a field, a NUL
    and an empty field each give distinct internal keys."""
    pairs = [(("a", "b:c", "d"), ("a:b", "c", "d")), (("a", "b\x00c"), ("a\x00b", "c")), (("a", "", "b"), ("a", "b", ""))]
    return all(M.internal_key(x) != M.internal_key(y) for x, y in pairs)


def inv_g21_attv(rules=R):
    """MODEL-G21 (0045 v1.9 INV-G13, the owner's ruling): `attv` is written WITH `att` from the same evaluation; `why`
    reads the version FROM `attv`; a legacy or version-less row reads "version unknown"; two predicate versions coexist
    in one store; default import writes `default-import`; trusted restore and a second hop carry it; a file `att` without
    `attv` restores as version unknown, never the current version; an `attv` outside its grammar refuses the unit;
    redaction preserves it; a procedural row has none; an absorption survivor keeps the incoming's."""
    s = _foreign()
    w = M.write(s, E("w", None), author="user", attested_by_predicate=True)
    written = w.attv == M.PREDICATE_VERSION and M.why(s, w) == {"label": "attested", "version": M.PREDICATE_VERSION}
    old = E("o", "attested"); old.attv = "ATTEST-2@0a1b2c3d"; s.edges["o"] = old
    coexist = M.why(s, old)["version"] == "ATTEST-2@0a1b2c3d" and M.why(s, w)["version"] == M.PREDICATE_VERSION
    leg = E("l", None); s.edges["l"] = leg
    vless = E("v", "attested"); s.edges["v"] = vless
    unknown = M.why(s, leg)["version"] == "version unknown" and M.why(s, vless)["version"] == "version unknown"
    d = store(); M.import_rows(d, *M.export(s, "u"), "default")
    default = {x.attv for x in d.edges.values()} == {M.DEFAULT_IMPORT}
    t = store(); t.origin = "store-T"; M.import_rows(t, *M.export(s, "u"), "trusted")
    t2 = store(); t2.origin = "store-T2"; M.import_rows(t2, *M.export(t, "u"), "trusted")
    carried = (t2.edges["o"].attv == "ATTEST-2@0a1b2c3d" and t2.edges["w"].attv == M.PREDICATE_VERSION
               and t2.edges["v"].attv is None and M.why(t2, t2.edges["v"])["version"] == "version unknown")
    bad = E("x", "attested"); bad.attv = "v3"
    grammar = not _admitted(store(), [bad], [], [])
    r = store(E("rd")); M.write(r, r.edges["rd"], author="user", attested_by_predicate=True); M.redact_edge(r, "rd")
    preserved = r.edges["rd"].attv == M.PREDICATE_VERSION
    pr = M.write(M.Store(), M.Edge(id="pr", user="u", relation="procedure", obj="s", att=None, procedural=True),
                 author="user", attested_by_predicate=False)
    procedural = pr.attv is None and M.why(M.Store(), pr) is None
    prior = E("p", "attested"); prior.attv = "ATTEST-2@0a1b2c3d"; inc = E("i", "not_attested")
    inc.attv = M.PREDICATE_VERSION; ab = store(prior); M.absorb(ab, prior, inc, rules)
    survivor = ab.edges["i"].attv == M.PREDICATE_VERSION
    # WHAT produced `att` (0045 v1.9): a write the author rule decides — a non-USER author, or USER with no declared
    # context — records `non-user-effective`, never a predicate version it did not run; the grammar admits it on import
    nu = M.Store(); third = M.write(nu, E("nu", None), author="third_party", attested_by_predicate=False)
    undeclared = M.write(nu, E("ud", None), author="user", attested_by_predicate=True, context=None)
    nonuser = (third.attv == M.NON_USER and undeclared.attv == M.NON_USER and M.why(nu, third)["version"] == M.NON_USER)
    nr = store(); nr.origin = "store-N"; M.import_rows(nr, *M.export(nu, "u"), "trusted")
    nonuser_travels = nr.edges["nu"].attv == M.NON_USER
    null_iff = leg.attv is None and leg.att is None and t2.edges["v"].att == "attested" and t2.edges["v"].attv is None
    return (written and coexist and unknown and default and carried and grammar and preserved and procedural
            and survivor and nonuser and nonuser_travels and null_iff)


# FROZEN at round 4 (2026-10-13): the reviewer ACCEPTED 0045 and 0047 jointly AT THE DESIGN LEVEL — "Accept 0045 and 0047
# jointly at design level, with their 0008 and 0041 constructions." Frozen scope, quoted: "Freeze the active invariant rows in
# **0045 §6** (including new **INV-G13**), **0047 §6** through **INV-R24** (R4 remains moved to the amendment), **0008 INV-Q1–Q10
# including Q4′ and INV-I1–I7**, **0041 amendment INV-RR1–RR12 and RR14** (RR13 remains withdrawn), and **0019 INV-N1–N4**.
# Preserve each row's MODEL/PREDICATE/PRODUCT allocation and the stated limits." This table is model II's MODEL allocation.
# THE GOVERNING RULE FORWARD, quoted from the banked verdict (outbox/0045-0047-round4-verdict-verbatim.md, body sha16
# 12576a39a0c51cb8), never paraphrased: "These obligations preserve the frozen design. Product findings should be repaired against
# it rather than restarting debate over label-versus-block, unrestricted query derivation, procedures, authenticated principals,
# cross-store replay or operational keys."
# Removing an invariant, weakening an owner's check, or moving a frozen row's allocation is reopening design review, not an edit.
INVARIANTS = {"MODEL-G1": inv_g1_legacy, "MODEL-G2": inv_g2_resolution, "MODEL-G3": inv_g3_restriction, "MODEL-G4": inv_g4_unit,
              "MODEL-G5": inv_g5_acts_stay, "MODEL-G6": inv_g6_survivor_axis, "MODEL-G7": inv_g7_marker_follows_flag,
              "MODEL-G8": inv_g8_write_path, "MODEL-G9": inv_g9_source_redacted, "MODEL-G10": inv_g10_import,
              "MODEL-G11": inv_g11_replay, "MODEL-G12": inv_g12_procedural,
              "MODEL-G13": inv_g13_historical, "MODEL-G14": inv_g14_erasure,
              "MODEL-G15": inv_g15_key_domains, "MODEL-G16": inv_g16_chronology, "MODEL-G17": inv_g17_repeat_import,
              "MODEL-G18": inv_g18_redacted_requests, "MODEL-G19": inv_g19_notice_coverage,
              "MODEL-G20": inv_g20_canonical, "MODEL-G21": inv_g21_attv}


def _refusal_is_failure(f):
    """An invariant asserts that the histories it builds are admitted; a DOMAIN refusal it did not catch is that
    property failing, so it returns False. Only `Refused` is caught: any other exception stays a harness failure, which
    the runner never counts as a kill (R2-08)."""
    def run(rules=R):
        try:
            return f(rules)
        except M.Refused:
            return False
    run.__doc__, run.__name__ = f.__doc__, f.__name__
    return run


INVARIANTS = {k: _refusal_is_failure(f) for k, f in INVARIANTS.items()}


def run_invariants(rules=R) -> dict:
    out = {}
    for k, f in INVARIANTS.items():
        try:
            out[k] = bool(f(rules))
        except Exception as x:
            out[k] = f"ERROR {type(x).__name__}: {x}"
    return out


# ----------------------------------------------------------------------------------------------- mutants
# every function the model module defines — DERIVED, never listed: a hand list went stale when round 3 added
# ordered_before, next_pos, _proj, redact_edge and internal_key (mutants of them found no original, and their calls
# were never counted as reaching the mutated path)
_O = {k: v for k, v in vars(M).items()
      if callable(v) and not isinstance(v, type) and getattr(v, "__module__", None) == M.__name__}


def _set(name, fn):
    return lambda: setattr(M, name, fn)


def _absorb_launders(s, prior, incoming, rules):
    r = _O["absorb"](s, prior, incoming, rules)
    if r == "absorbed" and prior.att == "attested":
        incoming.att = "attested"
    return r


def _absorb_copies(s, prior, incoming, rules):
    s.edges[incoming.id] = incoming; prior.active = False
    for c in [c for c in s.confirmations if c.edge == prior.id]:
        s.confirmations.append(M.Confirmation(id=c.id + "'", edge=incoming.id, pos=c.pos))
    return "absorbed"


def _render_axis_marker(s, e, budget, at=None):
    """The marker read from the AXIS, not the flag (draft 2's G3 shape)."""
    line = _O["render"](s, e, budget, at)
    if line is None:
        return None
    line = line.replace(" [possible extraction error]", "")
    if M.grounding(s, e, at) == "not_attested":
        line = line.replace(f"{e.obj}", f"{e.obj} [possible extraction error]", 1)
    return line


def _inspect_drops_unit(s, e, budget=None):
    """0047 v1.8 INV-R3's inspection mutant: the unit omitted from an inspection carrier."""
    out = _O["inspect"](s, e, budget)
    return dict(out, unit=None)


def _gate_v17_attested(s, e, existing_ok=True, at=None):
    """v1.7's cell: a challenged `attested` fact stays assertable (with its unit) — the privilege option 3 removed."""
    r = _O["gate"](s, e, existing_ok, at)
    if r == "not_assertable" and existing_ok and M.active_challenges(s, e, at) and M.grounding(s, e, at) == "attested":
        return "assertable_with_unit"
    return r


def _challenges_context_clears(s, e, at=None):
    if any(r.edge == e.id and r.kind == "context" and "withdraw" in r.text for r in s.replies):
        return []
    return _O["active_challenges"](s, e, at)


def _write_blocks(s, e, *, author, attested_by_predicate, context="direct"):
    """The REJECTED design ("keep blocking"): an unrecognised user statement is not stored."""
    if M.user_effective(author, context) and not attested_by_predicate:
        return None
    return _O["write"](s, e, author=author, attested_by_predicate=attested_by_predicate, context=context)


def _write_stores_flagged_nonuser(s, e, *, author, attested_by_predicate, context="direct"):
    if not M.user_effective(author, context):
        e.att = "not_attested"; s.edges[e.id] = e
        return e
    return _O["write"](s, e, author=author, attested_by_predicate=attested_by_predicate, context=context)


def _write_absence_is_user(s, e, *, author, attested_by_predicate, context="direct"):
    """The REJECTED reading: an undeclared USER call counts as the user."""
    return _O["write"](s, e, author=author, attested_by_predicate=attested_by_predicate,
                       context="direct" if (author == "user" and context is None) else context)


def _write_refuses_procedural(s, e, *, author, attested_by_predicate, context="direct"):
    if e.procedural:
        return None                                                 # draft 3.2: "an insert without att is refused"
    return _O["write"](s, e, author=author, attested_by_predicate=attested_by_predicate, context=context)


def _install_reply_on_procedural():
    orig = M.add_reply

    def add_reply(s, e, kind, text, target=None, correlation_id=None):
        was = e.procedural; e.procedural = False
        try:
            return orig(s, e, kind, text, target, correlation_id)
        finally:
            e.procedural = was
    M.add_reply = add_reply


def _replay_none(s, user, correlation_id, verb, digest):
    return None                                                     # no replay: a retry writes again


def _replay_per_verb(s, user, correlation_id, verb, digest):
    """Each verb checks only its own table: an id held by the OTHER verb is invisible, taken as fresh."""
    rec = s.registry.get((user, correlation_id)) if correlation_id is not None else None
    if rec is None or rec[0] != verb:
        return None
    if rec[1] == digest:
        return rec[2]
    raise M.Refused("integrity conflict")


def _replay_one_direction(s, user, correlation_id, verb, digest):
    """Only the NEW verb's direction is checked: a reply refuses a confirm's id, but confirm ignores a reply's."""
    rec = s.registry.get((user, correlation_id)) if correlation_id is not None else None
    if rec is not None and verb == "confirm" and rec[0] == "reply":
        return None
    return _O["_replay"](s, user, correlation_id, verb, digest)


def _confirm_reads_edge_first(s, e, rules, correlation_id=None):
    """INV-Q2's mutant: live edge state (an open challenge) is read BEFORE the registry, so a retry is refused."""
    if M.active_challenges(s, e):
        raise M.Refused("store.confirm.active-challenge")
    return _O["confirm"](s, e, rules, correlation_id)


def _render_filters_acts_by_valid_t(s, e, budget, at=None):
    """0047 INV-R20's mutant: acts filtered by the VALID-time T, as if their position were valid time."""
    if at is None:
        return _O["render"](s, e, budget, at)
    saved = M.active_challenges
    M.active_challenges = lambda s_, e_, at_=None: [r for r in saved(s_, e_) if (r.pos or ("", 0))[1] <= at]
    try:
        return _O["render"](s, e, budget, at)
    finally:
        M.active_challenges = saved


def _forget_keeps_replies(s, user):
    keep = [r for r in s.replies if r.user == user]
    _O["forget_user"](s, user)
    s.replies.extend(keep)


def _forget_keeps_registry(s, user):
    keep = {k: v for k, v in s.registry.items() if k[0] == user}
    _O["forget_user"](s, user)
    s.registry.update(keep)


def _grounding_counts_imported(s, e, at=None):
    if not e.procedural and any(c.edge == e.id for c in s.confirmations):
        return "confirmed"
    return _O["grounding"](s, e, at)


def _restore_writes_local(s, edges, confirmations, replies, mode, notices=()):
    _O["import_rows"](s, edges, confirmations, replies, mode, notices)
    if mode != "default":
        for r in s.confirmations + s.replies:
            r.origin = "local"


def _default_keeps_file_origin(s, edges, confirmations, replies, mode, notices=()):
    recorded = {r.id: r.origin for r in confirmations + replies}
    _O["import_rows"](s, edges, confirmations, replies, mode, notices)
    for r in s.confirmations + s.replies:
        if r.id in recorded:
            r.origin = recorded[r.id]


def _import_occupies_ids(s, edges, confirmations, replies, mode, notices=()):
    _O["import_rows"](s, edges, confirmations, replies, mode, notices)
    for r in confirmations:
        if r.correlation_id is not None:
            s.registry[(r.user, r.correlation_id)] = ("confirm", "imported|" + r.id, r)


def _import_keeps_file_id(s, edges, confirmations, replies, mode, notices=()):
    """The 0008 amendment INV-Q4's mutant: an imported row keeps the file's id as its correlation_id, so it occupies the
    confirmations UNIQUE the host's own requests need."""
    _O["import_rows"](s, edges, confirmations, replies, mode, notices)
    for r in s.confirmations + s.replies:
        if r.recorded_correlation_id is not None:
            r.correlation_id = r.recorded_correlation_id


def _migrate_without_backfill(s):
    return None


def _confirm_ignores_source(s, e, rules, correlation_id=None):
    if M.active_challenges(s, e):
        raise M.Refused("store.confirm.active-challenge")
    s.confirmations.append(M.Confirmation(id=f"k{len(s.confirmations) + 1}", edge=e.id, pos=M.next_pos(s)))


def _import_keeps_file_axis(s, edges, confirmations, replies, mode, notices=()):
    keep = {e.id: (e.att, e.source_episode) for e in edges}
    _O["import_rows"](s, edges, confirmations, replies, mode, notices)
    for i, (a, ep) in keep.items():
        s.edges[i].att, s.edges[i].source_episode = a, ep


def _inspect_counts_selected(s, e, budget=None):
    """0047 INV-R6's mutant: the open count derived from the excerpts the budget selected, not from all."""
    out = _O["inspect"](s, e, budget)
    n = len(out["excerpts"])
    return dict(out, open=n, unit=(out["unit"] or "").replace(f"{out['open']} open", f"{n} open") or None)


def _absorb_ignores_replies(s, prior, incoming, rules):
    """0047 INV-R17's second mutant: survivor selection reads confirmations only, so a reply-carrying prior is absorbed."""
    s.edges[incoming.id] = incoming
    if any(c.edge == prior.id for c in s.confirmations):
        return "not_absorbed"
    prior.active = False
    return "absorbed"


def _challenges_any_context_clears(s, e, at=None):
    """0047 INV-R14's mutant, in the reviewer's words: ANY context reply clears all challenges."""
    if any(r.edge == e.id and r.kind == "context" for r in s.replies):
        return []
    return _O["active_challenges"](s, e, at)


def _confirm_drops_challenge_refusal(s, e, rules, correlation_id=None):
    """0047 INV-R13's mutant: confirm() without the active-challenge refusal (the source-redacted refusal kept)."""
    saved = M.active_challenges
    M.active_challenges = lambda s_, e_, at=None: []
    try:
        return _O["confirm"](s, e, rules, correlation_id)
    finally:
        M.active_challenges = saved


def _replay_first_on_different(s, user, correlation_id, verb, digest):
    """0047 INV-R15's mutant: same id + a DIFFERENT request returns the first result instead of refusing."""
    rec = s.registry.get((user, correlation_id)) if correlation_id is not None else None
    return None if rec is None else rec[2]


def _import_trusts_acts(s, edges, confirmations, replies, mode, notices=()):
    """0047 INV-R16's mutant (the reviewer's): the edge cap applied, every incoming side-row act trusted."""
    local = set(s.edges)
    tagged = [r for r in confirmations + replies if r.edge in local]
    rest_c = [c for c in confirmations if c not in tagged]; rest_r = [r for r in replies if r not in tagged]
    _O["import_rows"](s, edges, rest_c, rest_r, mode, notices)
    for r in tagged:
        (s.confirmations if isinstance(r, M.Confirmation) else s.replies).append(r)


def _import_refuses_every_marker_reply(s, edges, confirmations, replies, mode, notices=()):
    """0041 amendment INV-RR3's first mutant: v1.3's rule — every marker-carrying reply refused, the round trip too."""
    if any(r.text == M.MARKER for r in replies):
        raise M.Refused("a marker reply (v1.3)")
    return _O["import_rows"](s, edges, confirmations, replies, mode, notices)


def _coverage_marker_free(row, target, cov):
    """0041 amendment INV-RR3's second mutant: a marker reply admitted with no notice (a fabricated tombstone) — a
    carrier holding the marker is taken as attested by itself."""
    marked = {p for p, v in M._carriers(row).items() if v == M.MARKER}
    return _O["_coverage_ok"](row, target, frozenset(cov) | marked)


def _import_untreated_under_notice(s, edges, confirmations, replies, mode, notices=()):
    """0041 amendment INV-RR3's third mutant: an ordinary reply arriving under a notice is written as-is."""
    texts = {r.id: r.text for r in replies}
    _O["import_rows"](s, edges, confirmations, replies, mode, notices)
    for r in s.replies:
        if r.id in texts and texts[r.id] != M.MARKER:
            r.text = texts[r.id]


def _write_refuses_unflagged_nonuser(s, e, *, author, attested_by_predicate, context="direct"):
    """0019 amendment INV-N1's second mutant: unflagged non-user triples refused too."""
    if not M.user_effective(author, context) and not e.procedural:
        return None
    return _O["write"](s, e, author=author, attested_by_predicate=attested_by_predicate, context=context)


def _write_refuses_flagged_user(s, e, *, author, attested_by_predicate, context="direct"):
    """0019 amendment INV-N2's mutant: v1's rule — a USER-effective flagged triple refused."""
    if M.user_effective(author, context) and e.ungrounded and not attested_by_predicate:
        return None
    return _O["write"](s, e, author=author, attested_by_predicate=attested_by_predicate, context=context)


# ---------------------------------------------------------------------------------------------- round-3 mutants
def _add_reply_digest_of_edge_state(s, e, kind, text, target=None, correlation_id=None):
    """0047 INV-R24's first mutant, "replay by edge state": the request digest folds in the edge's current content, so a
    retry after the edge changed is a DIFFERENT request and conflicts instead of replaying."""
    saved = M.canonical_uid
    M.canonical_uid = lambda *parts: saved(*parts, e.obj) if parts and parts[0] == "add_reply" else saved(*parts)
    try:
        return _O["add_reply"](s, e, kind, text, target, correlation_id)
    finally:
        M.canonical_uid = saved


def _import_imp_keys(s, edges, confs, reps, mode, notices=()):
    """The round-2 model: an imported act keyed `imp-N`, an admissible caller id (II R2-02)."""
    _O["import_rows"](s, edges, confs, reps, mode, notices)
    for n, a in enumerate(s.confirmations + s.replies, 1):
        if a.origin != "local":
            a.correlation_id = f"imp-{n}"


def _import_orders_by_date(s, edges, confs, reps, mode, notices=()):
    """Order by the caller's `confirmed_at` (II R2-03, the verdict's countermodel)."""
    import copy as _c
    confs = [_c.copy(c) for c in confs]
    for c in confs:
        c.pos = (c.pos[0] if c.pos else "?", c.confirmed_at)
    return _O["import_rows"](s, edges, confs, reps, mode, notices)


def _ordered_unknown_earliest(a, b):
    r = _O["ordered_before"](a, b)
    return True if r is None else r


def _import_no_origin_check(s, edges, confs, reps, mode, notices=()):
    import copy as _c
    if mode == "default":
        confs, reps = [_c.copy(x) for x in confs], [_c.copy(x) for x in reps]
        for x in confs + reps:
            if x.pos and x.pos[0] == s.origin:
                x.pos = ("elsewhere", x.pos[1])
            if x.act_uid and x.act_uid[0] == s.origin:
                x.act_uid = ("elsewhere",) + tuple(x.act_uid[1:])
    return _O["import_rows"](s, edges, confs, reps, mode, notices)


def _next_pos_max_live(s):
    live = [a.pos[1] for a in s.confirmations + s.replies if a.pos and a.pos[0] == s.origin]
    s.act_counter = 1 + max(live, default=0)
    return (s.origin, s.act_counter)


def _proj_full_rows(row):
    return tuple(sorted((k, repr(v)) for k, v in vars(row).items()))


def _import_drops_act_uid(s, edges, confs, reps, mode, notices=()):
    import copy as _c
    confs, reps = [_c.copy(x) for x in confs], [_c.copy(x) for x in reps]
    for x in confs + reps:
        x.act_uid = None
    return _O["import_rows"](s, edges, confs, reps, mode, notices)


def _proj_uid_only(row):
    return (row.act_uid,)


def _import_replay_grants(s, edges, confs, reps, mode, notices=()):
    """An exact replay on a held fact read as permission for the file's other acts on it (INV-I3's mutant)."""
    held = {a.act_uid: a for a in s.confirmations + s.replies}
    rows = confs + reps
    replays = [r for r in rows if r.act_uid in held and M._proj(held[r.act_uid]) == M._proj(r)]
    if mode == "default" and replays:
        _O["import_rows"](s, edges, [r for r in confs if r in replays], [r for r in reps if r in replays], mode, notices)
        return _O["import_rows"](s, [], [r for r in confs if r not in replays], [r for r in reps if r not in replays],
                                 "trusted", notices)
    return _O["import_rows"](s, edges, confs, reps, mode, notices)


def _redact_text_only(s, edge_id, *, covers_replies=True, fields=None):
    e = s.edges[edge_id]; e.relation, e.obj = M.MARKER, M.MARKER
    for r in s.replies:
        if r.edge == edge_id and r.text is not None:
            r.text = M.MARKER
    f = M.FULL_NOTICE if covers_replies else M.OLD_NOTICE
    s.notices[f"own:{edge_id}"] = M.Notice(f"own:{edge_id}", edge_id, f, state="applied", treated=f)


def _replay_compares_treated(s, user, cid, verb, digest):
    if cid is None:
        return None
    rec = s.registry.get((user, cid))
    if rec is None:
        return None
    if rec[0] == verb and rec[1] == digest:
        return rec[2]
    raise M.Refused(f"integrity conflict: correlation id held by {rec[0]}")


def _replay_ignores_verb(s, user, cid, verb, digest):
    rec = s.registry.get((user, cid)) if cid is not None else None
    if rec is not None and rec[1] == M.MARKER:
        return M.REQUEST_REDACTED
    return _O["_replay"](s, user, cid, verb, digest)


def _backfill_live_digest(s):
    for c in s.confirmations:
        if c.origin == "local" and c.correlation_id is not None:
            s.registry.setdefault((c.user, c.correlation_id),
                                  ("confirm", M.canonical_uid("confirm", c.user, c.edge), c, c.edge))


def _coverage_absent_permits(row, target, cov):
    """0041am INV-RR6's mutant (II R2-06): a notice that names NONE of a row's carriers read as permission — the row
    is admitted, and written untreated (the verdict's held-notice probe keeps the content)."""
    if not (set(cov) & M.CONTENT):
        return None
    return _O["_coverage_ok"](row, target, cov)


def _import_rewrites_notice(s, edges, confs, reps, mode, notices=()):
    """0041am INV-RR6's and 0008am INV-I5's mutant: the HELD (foreign, immutable) notice enlarged to cover the row."""
    for r in reps:
        t = s.edges.get(r.edge)
        if t is not None and M.MARKER in (t.relation, t.obj):
            for n in s.notices.values():
                if n.target == r.edge:
                    n.fields = n.fields | M.CONTENT
    return _O["import_rows"](s, edges, confs, reps, mode, notices)


# ---------------------------------------------------------------------------------------------- round-4 mutants
def _view(tx, *, drop):
    """A shallow view of a staged store without the acts `drop` selects (a mutant's narrower H)."""
    v = _copy.copy(tx)
    v.replies = [r for r in tx.replies if not drop(r)]
    v.confirmations = [c for c in tx.confirmations if not drop(c)]
    return v


def _chronology_before_challenges(tx, new, replayed):
    """0047 INV-R23 / 0008am INV-Q10: confirmations checked before the unit's challenges are installed (round 3)."""
    fresh = {id(a) for a in new}
    drop = lambda a: id(a) in fresh and getattr(a, "kind", None) == "challenge"
    return _O["_chronology"](_view(tx, drop=drop), [a for a in new if not drop(a)], replayed)


def _chronology_held_resolves(tx, new, replayed):
    """0047 INV-R23 / 0008am INV-Q10: held challenges judged before the unit's resolves are applied (round 3)."""
    fresh = {id(a) for a in new}
    drop = lambda a: id(a) in fresh and getattr(a, "kind", None) == "resolve"
    return _O["_chronology"](_view(tx, drop=drop), [a for a in new if not drop(a)], replayed)


def _chronology_incoming_confirmations(tx, new, replayed):
    """0008am INV-Q10: only INCOMING confirmations judged — an incoming challenge never meets a HELD confirmation."""
    fresh = {id(a) for a in new}
    return _O["_chronology"](_view(tx, drop=lambda a: isinstance(a, M.Confirmation) and id(a) not in fresh),
                             new, replayed)


def _ties_ordered(acts, fresh):
    """0008am INV-Q10: a tie treated as ordered — two acts at one position admitted."""
    return None


def _chronology_skips_replay_units(tx, new, replayed):
    """0008am INV-I3: §6f's chronology skipped for a unit that contains an exact replay."""
    if replayed:
        return None
    return _O["_chronology"](tx, new, replayed)


def _identity_pre_import(held_map, staged, uid):
    """0008am INV-I6 (the reviewer's same-unit witness): the identity map built from pre-import rows only."""
    return held_map.get(uid) if uid is not None else None


def _import_in_file_order(s, edges, confs, reps, mode, notices=()):
    """0008am INV-I6: rows processed one at a time in file order (confirmations, then replies), each against what was
    staged before it — atomic, but no longer a set."""
    tx = _copy.deepcopy(s)
    rows = [(c, True) for c in confs] + [(r, False) for r in reps]
    _O["import_rows"](tx, edges, [], [], mode, notices)
    for row, is_conf in rows:
        _O["import_rows"](tx, [], [row] if is_conf else [], [] if is_conf else [row], mode, notices)
    s.__dict__.update(tx.__dict__)


def _redact_keeps_undo(s, edge_id, *, covers_replies=True, fields=None):
    """0008am INV-Q7 (the 0044 review's witness): an undo's registry digest kept after redaction, so its retry replays."""
    keep = {k: v for k, v in s.registry.items() if v[0] == "undo" and len(v) > 3 and v[3] == edge_id}
    _O["redact_edge"](s, edge_id, covers_replies=covers_replies, fields=fields)
    s.registry.update(keep)


def _same_act_untreated_incoming(held, row, cov):
    """0008am INV-I4 / 0041am INV-RR8: the untreated arrival compared with the treated held row (witness 1's second
    import refuses)."""
    return M._treated(held, cov) == M._proj(row)


def _write_treated_text_only(row, cov):
    """0008am INV-I4 / 0041am INV-RR8: `text` treated and `request_digest` kept (witness 1's first admission)."""
    if "replies.text" in cov and getattr(row, "text", None) is not None:
        row.text = M.MARKER


def _same_act_raw(held, row, cov):
    """0008am INV-I4 / 0041am INV-RR9: equality on the RAW projection — a treated arrival over a held untreated copy
    refuses (witness 2 keeps the content)."""
    return M._proj(held) == M._proj(row)


def _same_act_treated_any_structure(held, row, cov):
    if any(v == M.MARKER for v in M._carriers(row).values()):
        return True
    return _O["_same_act"](held, row, cov)


def _transition_copies_row(held, row, cov):
    for k, v in vars(row).items():
        if k not in ("id", "origin", "correlation_id", "recorded_correlation_id"):
            setattr(held, k, v)


def _install_structural_transition():
    """0008am INV-I5 / 0041am INV-RR9: the transition changes a structural field — a treated arrival is taken as the
    held act whatever its structure, and its fields are written over the held copy's."""
    M._same_act = _same_act_treated_any_structure
    M._transition = _transition_copies_row


def _coverage_partial_permits(row, target, cov):
    """0008am INV-I5 / 0041am INV-RR9: a notice attesting SOME of a row's carriers admits it."""
    if set(cov) & M.CONTENT:
        return None
    return _O["_coverage_ok"](row, target, cov)


def _why_current_for_unknown(s, e):
    """0045 INV-G13: a legacy or version-less row labelled with the current predicate's version."""
    r = _O["why"](s, e)
    return dict(r, version=M.PREDICATE_VERSION) if r and r["version"] == "version unknown" else r


def _why_running_build(s, e):
    """0045 INV-G13: `why`'s version read from the running build instead of `attv`."""
    r = _O["why"](s, e)
    return None if r is None else dict(r, version=M.PREDICATE_VERSION)


def _export_drops_attv(s, user):
    """0045 INV-G13: `attv` dropped on export — a second hop cannot carry the version."""
    edges, confs, reps = _O["export"](s, user)
    for e in edges:
        e.attv = None
    return edges, confs, reps


def _write_predicate_on_nonuser(s, e, *, author, attested_by_predicate, context="direct"):
    """0045 INV-G13: a non-USER-effective write records the predicate version, which never ran on it."""
    got = _O["write"](s, e, author=author, attested_by_predicate=attested_by_predicate, context=context)
    if got is not None and got.attv == M.NON_USER:
        got.attv = M.PREDICATE_VERSION
    return got


def _effect_on(test, make):
    """A mutant of _notice_effect: where `test(n, prev, rec, held_rec, mode)` holds, `make(...)`'s effect replaces the
    text's; elsewhere the text's own effect."""
    def eff(n, prev, rec, held_rec, mode):
        if test(n, prev, rec, held_rec, mode):
            return make(n, prev, rec, held_rec, mode)
        return _O["_notice_effect"](n, prev, rec, held_rec, mode)
    return eff


def _unshown(n, rec):
    return rec is not None and not M.shows_redaction(rec, n.fields)


def _standing(prev):
    return prev is not None and prev.state == "standing"


# INV-RR10: the default-mode defect
_mut_default_applies = _effect_on(lambda n, p, r, h, m: m == "default" and h is not None and not _standing(p),
                                  lambda *a: M.Effect(state="applied", by_store=True))


def _mut_pending_reason_rewritten(n, prev, rec, held_rec, mode):
    """INV-RR11 ("a pending notice re-arriving is `existing`"), round-4 IO-II-1: the SUPERSEDED implementation — the table alone, so a repeated default pending
    notice's held reason (`record-not-in-file`, `standing-arrival`) is rewritten to `held-target`."""
    return M._notice_table(n, prev, rec, held_rec, mode)


def _record_pending_and_apply(tx, n, reason):
    """INV-RR10: listed in notices_not_applied, and applied anyway."""
    _O["_record_pending"](tx, n, reason)
    M._apply_notice(tx, n.target, M.FULL_NOTICE)


# INV-I7 / RR14: a restore carrying the held record UNREDACTED, applied instead of refused
_mut_restore_unredacted = _effect_on(lambda n, p, r, h, m: m != "default" and h is not None and _unshown(n, r),
                                     lambda *a: M.Effect(state="applied", by_store=True))
# INV-RR14: the created record, unredacted, with its notice
_mut_apply_created = _effect_on(lambda n, p, r, h, m: h is None and _unshown(n, r) and not _standing(p),
                                lambda *a: M.Effect(state="applied", treated=a[0].fields, write_treated=True))
_mut_pend_created = _effect_on(lambda n, p, r, h, m: h is None and _unshown(n, r) and not _standing(p),
                               lambda *a: M.Effect(state="pending", reason="held-target"))
_mut_skip_created = _effect_on(lambda n, p, r, h, m: h is None and _unshown(n, r) and not _standing(p),
                               lambda *a: M.Effect())             # the record admitted, its notice dropped
# INV-RR12: standing notices
_mut_standing_every_present = _effect_on(lambda n, p, r, h, m: _standing(p) and h is not None,
                                         lambda *a: M.Effect(state="applied", by_store=True))
_mut_standing_untreated_completes = _effect_on(lambda n, p, r, h, m: _standing(p) and h is None and _unshown(n, r),
                                               lambda *a: M.Effect(state="applied", treated=a[0].fields,
                                                                   write_treated=True))
_mut_standing_untreated_admitted = _effect_on(lambda n, p, r, h, m: _standing(p) and h is None and _unshown(n, r),
                                              lambda *a: M.Effect())
_mut_standing_default_attests = _effect_on(lambda n, p, r, h, m: _standing(p) and h is None and m == "default"
                                           and r is not None and not _unshown(n, r),
                                           lambda *a: M.Effect(state="applied", treated=a[0].fields))
_mut_compare_origins = _effect_on(lambda n, p, r, h, m: r is not None and getattr(r, "origin_store", None) is not None
                                  and n.origin != r.origin_store,
                                  lambda *a: M.Effect(state="pending", reason="origin"))


def _apply_by_store_fields_only(s, n):
    """0008am INV-I5 / 0041am INV-RR11: the held treatment (restore, or confirm_notice) limited to the notice's fields —
    an older notice leaves a held reply's text published."""
    M._apply_notice(s, n.target, n.fields)
    n.state, n.reason, n.treated = "applied", None, n.fields
    s.notices[n.id] = n


def _redacted_targets_with_pending(s):
    return {n.target for n in s.notices.values() if n.state in ("applied", "pending")}


def _write_refused_pending(s, rid):
    return any(n.target == rid and n.state in ("applied", "pending") for n in s.notices.values())


def _write_refused_standing(s, rid):
    return any(n.target == rid and n.state in ("applied", "standing") for n in s.notices.values())


def _shows_skips_episode(record, fields):
    """INV-RR14: the record test reads only an edge's own fields; an episode always 'shows'."""
    if isinstance(record, M.Episode):
        return True
    return _O["shows_redaction"](record, fields)


def _original_id_falls_back_to_key(row):
    """Round 3's `_original_id`: with no recorded id, a row's own internal `#act:` key read as its original request id —
    an admitted copy then differs from its own repeat (found at round 4; INV-I1 for an act sent with no request id)."""
    return row.recorded_correlation_id if row.recorded_correlation_id is not None else row.correlation_id


def _unit_ids_unchecked(rows):
    """0008am v1.3 §6e: a file row id naming two different rows of one unit admitted."""
    return None


# ---------------------------------------------------------------------------------------------- 0041am v1.11 mutants
_mut_attest_only = _effect_on(lambda n, p, r, h, m: m != "default" and r is None and h is not None
                              and M.shows_redaction(h, n.fields) and not (p is not None and p.state == "applied"),
                              lambda *a: M.Effect(state="applied"))
_mut_restore_rearrival_existing = _effect_on(lambda n, p, r, h, m: m != "default" and p is not None
                                             and p.state == "pending",
                                             lambda *a: M.Effect())


def _arrival_under_attestation_treats(rec, applied):
    """INV-RR14: an arrival under a completed attestation, with no notice for it in the unit, written treated."""
    M._treat_record(rec, frozenset().union(*(x.fields | x.treated for x in applied)))


def _notices_not_applied_without_standing(s):
    """INV-RR12: a pending standing arrival left out of notices_not_applied."""
    return [x for x in _O["notices_not_applied"](s) if x[1] != "standing-arrival"]


def _held_differs_skips_attested(noticed, attested):
    """INV-RR14 (0041am v1.12): a store's own redacted record arriving without its notice skipped — INV-11 not run."""
    return "skip" if (noticed or attested) else "refuse"


def _coverage_foreign_only(s, target):
    """INV-RR6: only FOREIGN notices count as coverage — this store's own attestations do not."""
    out = frozenset()
    for n in s.notices.values():
        if n.target == target and n.origin != s.origin:
            out |= n.fields
    return out


# name -> (owning model invariant, installer, the spec rows whose named mutant this is). The third element is what
# model_citations.py checks against each document's §6: a row that cites "model Gn" must have a mutant answering it,
# owned by MODEL-Gn, and a mutant may answer only a row that cites its owner.
MUTANTS = {
    "a legacy row read as attested (R1-02)": ("MODEL-G1", _set("grounding", lambda s, e, at=None: e.att or "attested"), ("0045 INV-G7",)),
    "a context reply mentioning withdrawal clears every challenge (R1-06)": ("MODEL-G2", _set("active_challenges", _challenges_context_clears), ()),
    "any context reply clears all challenges (R1-06, the reviewer's)": ("MODEL-G2", _set("active_challenges", _challenges_any_context_clears), ("0047 INV-R14",)),
    "confirm() drops the active-challenge refusal": ("MODEL-G2", _set("confirm", _confirm_drops_challenge_refusal), ("0047 INV-R13",)),
    "a grid cell promotes an ineligible edge (R1-05)": ("MODEL-G3", _set("gate", lambda s, e, existing_ok=True, at=None: "assertable"), ("0047 INV-R12",)),
    "an inspection carrier omits the unit (R1-05, v1.8 INV-R3)": ("MODEL-G4", _set("inspect", _inspect_drops_unit), ()),
    "keep `attested` assertable under a challenge (v1.7's cell)": ("MODEL-G3", _set("gate", _gate_v17_attested), ("0047 INV-R12",)),
    "the open count derived from the budget-selected challenges": ("MODEL-G4", _set("inspect", _inspect_counts_selected), ("0047 INV-R6",)),
    "absorption copies confirmations to the survivor (R1-03)": ("MODEL-G5", _set("absorb", _absorb_copies), ("0047 INV-R17",)),
    "survivor selection ignores a contributor's reply": ("MODEL-G5", _set("absorb", _absorb_ignores_replies), ("0047 INV-R17",)),
    "an attested prior launders the survivor's axis (§7)": ("MODEL-G6", _set("absorb", _absorb_launders), ("0045 INV-G11",)),
    "the marker read from the axis, not the flag (0019 U5)": ("MODEL-G7", _set("render", _render_axis_marker), ("0045 INV-G8",)),
    "the rejected design: an unrecognised user statement is not stored": ("MODEL-G8", _set("write", _write_blocks), ("0045 INV-G9",)),
    "a non-user FLAGGED triple stored (§2a)": ("MODEL-G8", _set("write", _write_stores_flagged_nonuser), ("0019am INV-N1",)),
    "unflagged non-user triples refused too": ("MODEL-G8", _set("write", _write_refuses_unflagged_nonuser), ("0019am INV-N1",)),
    "v1's rule: a USER-effective flagged triple refused": ("MODEL-G8", _set("write", _write_refuses_flagged_user), ("0019am INV-N2",)),
    "the rejected reading: an undeclared USER call counts as the user (user-effective scope)": ("MODEL-G8", _set("write", _write_absence_is_user), ("0019am INV-N3",)),
    "confirm() ignores a redacted source ('Add the link')": ("MODEL-G9", _set("confirm", _confirm_ignores_source), ("0045 INV-G10",)),
    "default import keeps the file's axis and link (R1-08)": ("MODEL-G10", _set("import_rows", _import_keeps_file_axis), ("0045 INV-G9",)),
    "the edge cap applied, every incoming side-row act trusted (R1-08, the reviewer's)": ("MODEL-G10", _set("import_rows", _import_trusts_acts), ("0047 INV-R16",)),
    "v1.3's rule: every marker reply refused at import": ("MODEL-G10", _set("import_rows", _import_refuses_every_marker_reply), ("0041am INV-RR3",)),
    "a marker reply admitted with no notice": ("MODEL-G10", _set("_coverage_ok", _coverage_marker_free), ("0041am INV-RR3",)),
    "an ordinary reply under a notice written as-is": ("MODEL-G10", _set("import_rows", _import_untreated_under_notice), ("0041am INV-RR3",)),
    "no replay: a retried confirm/reply writes again (0008)": ("MODEL-G11", _set("_replay", _replay_none), ()),
    "same id + a different request returns the first result": ("MODEL-G11", _set("_replay", _replay_first_on_different), ("0047 INV-R15",)),
    "each verb checks only its own table (ids scoped per verb)": ("MODEL-G11", _set("_replay", _replay_per_verb), ("0047 INV-R15", "0008am INV-Q1")),
    "only the new verb's direction is checked": ("MODEL-G11", _set("_replay", _replay_one_direction), ("0008am INV-Q1",)),
    "live edge state read before the registry": ("MODEL-G11", _set("confirm", _confirm_reads_edge_first), ("0008am INV-Q2",)),
    "the migration without the backfill": ("MODEL-G11", _set("migrate_registry", _migrate_without_backfill), ("0008am INV-Q3",)),
    "an imported act occupies the id space": ("MODEL-G10", _set("import_rows", _import_occupies_ids), ("0008am INV-Q4′",)),
    "an imported row keeps the file's id as its correlation_id": ("MODEL-G10", _set("import_rows", _import_keeps_file_id), ("0008am INV-Q4′",)),
    "count imported confirmations toward g(e)": ("MODEL-G10", _set("grounding", _grounding_counts_imported), ("0047 INV-R21",)),
    "trusted restore writes recorded acts as local": ("MODEL-G10", _set("import_rows", _restore_writes_local), ("0047 INV-R21", "0008am INV-Q5")),
    "default import keeps the file's origin": ("MODEL-G10", _set("import_rows", _default_keeps_file_origin), ("0047 INV-R21", "0008am INV-Q5")),
    "filter acts by the valid-time T": ("MODEL-G13", _set("render", _render_filters_acts_by_valid_t), ("0047 INV-R20",)),
    "keep replies after forget_user": ("MODEL-G14", _set("forget_user", _forget_keeps_replies), ("0047 INV-R22",)),
    "keep registry rows after erasure": ("MODEL-G14", _set("forget_user", _forget_keeps_registry), ("0047 INV-R22", "0008am INV-Q6")),
    "draft 3.2's rule: an att-less insert is refused, procedural included": ("MODEL-G12", _set("write", _write_refuses_procedural), ("0045 INV-G12",)),
    "a reply attaches to a procedural edge (0047 R19)": ("MODEL-G12", lambda: _install_reply_on_procedural(), ("0047 INV-R19",)),
    "imported acts keyed imp-N, an admissible caller id (II R2-02)": ("MODEL-G15", _set("import_rows", _import_imp_keys), ("0008am INV-Q4′",)),
    "order by the caller's confirmed_at (II R2-03)": ("MODEL-G16", _set("import_rows", _import_orders_by_date), ("0047 INV-R23",)),
    "an incomparable or unknown position read as earliest": ("MODEL-G16", _set("ordered_before", _ordered_unknown_earliest), ("0047 INV-R23", "0008am INV-Q10")),
    "compare positions without the origin check (C-1)": ("MODEL-G16", _set("import_rows", _import_no_origin_check), ("0008am INV-Q9",)),
    "the act ordinal as MAX over live rows (C-2)": ("MODEL-G16", _set("next_pos", _next_pos_max_live), ("0008am INV-Q9",)),
    "compare full rows, not the projection (II R2-04)": ("MODEL-G17", _set("_proj", _proj_full_rows), ("0008am INV-I1",)),
    "no exact-replay rule: identity dropped": ("MODEL-G17", _set("import_rows", _import_drops_act_uid), ("0008am INV-I1",)),
    "a changed row under a held act_uid admitted": ("MODEL-G17", _set("_proj", _proj_uid_only), ("0008am INV-I2",)),
    "an exact replay grants a new act on its target": ("MODEL-G17", _set("import_rows", _import_replay_grants), ("0008am INV-I3",)),
    "redaction treats replies.text only (II R2-05)": ("MODEL-G18", _set("redact_edge", _redact_text_only), ("0008am INV-Q7", "0041am INV-RR5")),
    "replay 'same payload' against a treated digest": ("MODEL-G18", _set("_replay", _replay_compares_treated), ("0008am INV-Q7", "0041am INV-RR5")),
    "a reply retry returns another verb's result": ("MODEL-G18", _set("_replay", _replay_ignores_verb), ("0047 INV-R24",)),
    "a reply replays by edge state (its digest folds in the edge)": ("MODEL-G18", _set("add_reply", _add_reply_digest_of_edge_state), ("0047 INV-R24",)),
    "the backfill copies the live digest": ("MODEL-G18", _set("migrate_registry", _backfill_live_digest), ("0041am INV-RR7",)),
    "an absent notice field read as permission (II R2-06)": ("MODEL-G19", _set("_coverage_ok", _coverage_absent_permits), ("0041am INV-RR6",)),
    "the foreign notice rewritten to cover the reply": ("MODEL-G19", _set("import_rows", _import_rewrites_notice), ("0041am INV-RR6", "0008am INV-I5")),
    "act identity by separator join (C-3)": ("MODEL-G20", _set("internal_key", lambda uid: "#act:" + ":".join(map(str, uid))), ("0008am INV-Q8",)),
    # round 4 (the round-3 verdict; research 5ad5eb1c)
    "confirmations checked before the unit's challenges are installed (R3-02)": ("MODEL-G16", _set("_chronology", _chronology_before_challenges), ("0047 INV-R23", "0008am INV-Q10")),
    "held challenges judged before the unit's resolves are applied (R3-02)": ("MODEL-G16", _set("_chronology", _chronology_held_resolves), ("0047 INV-R23", "0008am INV-Q10")),
    "only incoming confirmations judged": ("MODEL-G16", _set("_chronology", _chronology_incoming_confirmations), ("0008am INV-Q10",)),
    "a tie treated as ordered": ("MODEL-G16", _set("_ties", _ties_ordered), ("0008am INV-Q10",)),
    "chronology skipped for a unit that contains a replay": ("MODEL-G17", _set("_chronology", _chronology_skips_replay_units), ("0008am INV-I3",)),
    "the identity map built from pre-import rows only (R3-01)": ("MODEL-G17", _set("_identity", _identity_pre_import), ("0008am INV-I6",)),
    "rows processed in file order": ("MODEL-G17", _set("import_rows", _import_in_file_order), ("0008am INV-I6",)),
    "an undo's digest kept after redaction (its retry replays)": ("MODEL-G18", _set("redact_edge", _redact_keeps_undo), ("0008am INV-Q7",)),
    "the untreated arrival compared with the treated held row (R3-01 witness 1)": ("MODEL-G19", _set("_same_act", _same_act_untreated_incoming), ("0008am INV-I4", "0041am INV-RR8")),
    "text treated, request_digest kept (R3-01 witness 1)": ("MODEL-G19", _set("_write_treated", _write_treated_text_only), ("0008am INV-I4", "0041am INV-RR8")),
    "a treated arrival over a held untreated copy refused (R3-01 witness 2)": ("MODEL-G19", _set("_same_act", _same_act_raw), ("0008am INV-I4", "0041am INV-RR9", "0008am INV-I7")),
    "the transition changes a structural field": ("MODEL-G19", _install_structural_transition, ("0008am INV-I5", "0041am INV-RR9")),
    "partial coverage admitted": ("MODEL-G19", _set("_coverage_ok", _coverage_partial_permits), ("0008am INV-I5", "0041am INV-RR9")),
    "a legacy or version-less row labelled with the current version": ("MODEL-G21", _set("why", _why_current_for_unknown), ("0045 INV-G13",)),
    "why's version read from the running build": ("MODEL-G21", _set("why", _why_running_build), ("0045 INV-G13",)),
    "attv dropped on export (a second hop cannot carry it)": ("MODEL-G21", _set("export", _export_drops_attv), ("0045 INV-G13",)),
    "a non-user-effective write records the predicate version": ("MODEL-G21", _set("write", _write_predicate_on_nonuser), ("0045 INV-G13",)),
    "held treatment limited to the notice's fields (confirm_notice or restore)": ("MODEL-G19", _set("_apply_by_this_store", _apply_by_store_fields_only), ("0008am INV-I5", "0041am INV-RR11")),
    "the authorized transition applied in default mode": ("MODEL-G19", _set("_transition_allowed", lambda mode, t, tx: True), ("0008am INV-I7", "0041am INV-RR10")),
    "a default import's notice over a held target applied (the defect at 1fd3e52)": ("MODEL-G19", _set("_notice_effect", _mut_default_applies), ("0041am INV-RR10",)),
    "a pending notice listed and applied anyway": ("MODEL-G19", _set("_record_pending", _record_pending_and_apply), ("0041am INV-RR10",)),
    "a pending notice counted in redacted_targets()": ("MODEL-G19", _set("redacted_targets", _redacted_targets_with_pending), ("0041am INV-RR11",)),
    "a local write refused under a pending notice": ("MODEL-G19", _set("_write_refused", _write_refused_pending), ("0041am INV-RR11",)),
    "a standing notice completed on every present target (the pin's arrival loop)": ("MODEL-G19", _set("_notice_effect", _mut_standing_every_present), ("0041am INV-RR12",)),
    "a standing notice completed on an untreated arrival (content removed)": ("MODEL-G19", _set("_notice_effect", _mut_standing_untreated_completes), ("0041am INV-RR12",)),
    "an untreated arrival admitted under a standing notice (content lands)": ("MODEL-G19", _set("_notice_effect", _mut_standing_untreated_admitted), ("0041am INV-RR12",)),
    "a treated arrival attested automatically in a default import": ("MODEL-G19", _set("_notice_effect", _mut_standing_default_attests), ("0041am INV-RR12",)),
    "a local write refused under a standing notice (the pin)": ("MODEL-G19", _set("_write_refused", _write_refused_standing), ("0041am INV-RR12",)),
    "a notice's origin compared with its record's (v1.5's binding)": ("MODEL-G19", _set("_notice_effect", _mut_compare_origins), ("0041am INV-RR12",)),
    "a repeated default pending notice's reason rewritten to held-target (round-4 IO-II-1)": ("MODEL-G19", _set("_notice_effect", _mut_pending_reason_rewritten), ("0041am INV-RR11",)),
    "a notice applied to the created record regardless (hotfix candidate 1)": ("MODEL-G19", _set("_notice_effect", _mut_apply_created), ("0041am INV-RR14",)),
    "the created record admitted, its notice pended (content lands)": ("MODEL-G19", _set("_notice_effect", _mut_pend_created), ("0041am INV-RR14",)),
    "the created record admitted, its notice skipped (content lands)": ("MODEL-G19", _set("_notice_effect", _mut_skip_created), ("0041am INV-RR14",)),
    "a restore applies a notice over its held record's unredacted copy": ("MODEL-G19", _set("_notice_effect", _mut_restore_unredacted), ("0008am INV-I7", "0041am INV-RR14")),
    "the record test skips an episode": ("MODEL-G19", _set("shows_redaction", _shows_skips_episode), ("0041am INV-RR14",)),
    "attest only, with no copy, over a held record already showing (a held act keeps its content)": ("MODEL-G19", _set("_notice_effect", _mut_attest_only), ("0041am INV-RR11", "0008am INV-I7")),
    "a restore re-arrival of a pending notice counted existing": ("MODEL-G19", _set("_notice_effect", _mut_restore_rearrival_existing), ("0041am INV-RR11",)),
    "a held pending notice re-weighed when an import re-creates its target": ("MODEL-G19", _set("_meets_on_arrival", lambda n: n.state in ("standing", "pending")), ("0041am INV-RR11",)),
    "an arrival under a completed attestation written treated with no notice in the unit": ("MODEL-G19", _set("_arrival_under_attestation", _arrival_under_attestation_treats), ("0041am INV-RR14",)),
    "a noticed held record refused by 0009 (its capped copy differs)": ("MODEL-G19", _set("_held_differs", lambda noticed, attested: "refuse"), ("0041am INV-RR10",)),
    "a default import skips a store's own redacted record arriving without its notice (INV-11 refuses it)": ("MODEL-G19", _set("_held_differs", _held_differs_skips_attested), ("0041am INV-RR14",)),
    "a pending standing arrival left out of notices_not_applied": ("MODEL-G19", _set("notices_not_applied", _notices_not_applied_without_standing), ("0041am INV-RR12",)),
    "count only foreign notices as coverage (the coverage check misreads this store's own redaction)": ("MODEL-G19", _set("coverage", _coverage_foreign_only), ("0041am INV-RR6",)),
    "a file row id naming two rows of one unit admitted": ("MODEL-G17", _set("_unit_ids_ok", _unit_ids_unchecked), ("0008am INV-I6",)),
    "an internal key read as the original request id": ("MODEL-G17", _set("_original_id", _original_id_falls_back_to_key), ("0008am INV-I1",)),
}


def run_mutants() -> dict:
    """Each mutant is installed, then judged. A KILL is semantic: the owning invariant RETURNS False, and the mutated
    function was CALLED while it ran. An owner that RAISES is a harness failure, not a kill (the 0044 round-2 verdict,
    R2-08: a mutant with the wrong signature raised TypeError, which a runner counting any exception reported as a kill
    that never reached the assertion it claimed). `killed_by` still lists every invariant the mutant moved."""
    out = {}
    for name, (owner, install, answers) in MUTANTS.items():
        install()
        calls = {"n": 0}
        for k in [k for k in _O if getattr(M, k) is not _O[k]]:
            f = getattr(M, k)

            def counted(*a, _f=f, **kw):
                calls["n"] += 1
                return _f(*a, **kw)
            setattr(M, k, counted)
        try:
            try:
                ov = INVARIANTS[owner](R)
                owner_outcome = "failed" if ov is False else ("held" if ov is True else f"returned {ov!r}")
            except Exception as x:
                owner_outcome = f"raised {type(x).__name__}: {x}"
            reached = calls["n"] > 0
            res = run_invariants()
        finally:
            for k, v in _O.items():
                setattr(M, k, v)
        killed = sorted(k for k, v in res.items() if v is not True)
        out[name] = {"owner": owner, "owner_outcome": owner_outcome, "mutated_path_reached": reached,
                     "killed_by": killed, "killed_by_owner": owner_outcome == "failed" and reached,
                     "answers": list(answers)}
    return out


# ----------------------------------------------------------------------------------------------- probes (draft 3.1 §10)
def probes() -> dict:
    p = {}
    for v in (True, False):                     # §10.2: no invariant needs G2's verifier amendment
        res = run_invariants(M.Rules(absorption_or=v))
        p[f"§10.2 all invariants hold with absorption OR={v}"] = all(x is True for x in res.values())
    for scope in ("not_attested", "all"):       # §10.1 (i): the refusal's scope, both ways
        e = E("a", "attested", ep="ep1"); s = store(e); s.redacted_episodes.add("ep1")
        try:
            M.confirm(s, e, M.Rules(source_redacted_scope=scope)); r = "ADMITTED"
        except M.Refused:
            r = "REFUSED"
        p[f"§10.1(i) scope[{scope}]: confirm() of an ATTESTED edge whose source is redacted"] = r
    # §10.1 (ii): a post-version edge with NO episode carrier (att set, link NULL) — is a redaction ever unseen?
    e = E("noep", "not_attested", ep=None); s = store(e); s.redacted_episodes.add("any-episode")
    try:
        M.confirm(s, e, R); r = "ADMITTED (no source to be redacted: nothing erased goes unseen, because nothing was linked)"
    except M.Refused:
        r = "REFUSED"
    p["§10.1(ii) post-version edge, no episode carrier"] = r
    p["§10.1(ii) is a NULL link ever read as legacy?"] = M.grounding(s, e) != "unknown"   # att decides legacy, not the link
    # §10.1 (iii): the source redacted AFTER a confirmation — the confirmation stands (the rule gates confirm(), it does
    # not revoke)
    e = E("late", "not_attested", ep="ep3"); s = store(e); M.confirm(s, e, R); s.redacted_episodes.add("ep3")
    p["§10.1(iii) source redacted AFTER confirmation: grounding"] = M.grounding(s, e)
    p["§10.3 readers of the not_attested reason in this model"] = 0
    return p


def main() -> int:
    inv = run_invariants(); mut = run_mutants(); pr = probes()
    owners = {m["owner"] for m in mut.values()}
    ok = (all(v is True for v in inv.values()) and all(m["killed_by_owner"] for m in mut.values())
          and set(inv) <= owners)
    res = {"model": "package II reference model", "rules_draft": "research draft 3.4 (sha16 b697bda6) + the 0008 amendment 0047/0008-request-registry + the owner's rulings",
           "invariants": inv, "mutants": mut, "probes": pr, "verdict": "PASS" if ok else "FAIL"}
    if "--out" in sys.argv:
        pathlib.Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(res, indent=2, default=str) + "\n")
    for k, v in inv.items():
        print(f"{'ok  ' if v is True else 'FAIL'} {k}: {'' if v is True else v}")
    for k, v in mut.items():
        print(f"{'KILLED  ' if v['killed_by_owner'] else 'SURVIVED'} {k} -> by {v['killed_by']} (owner {v['owner']})")
    for k, v in pr.items():
        print(f"probe {k}: {v!r}")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
