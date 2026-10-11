"""Runs package II's reference model on rules draft 3.4 (research 12142443, sha16 b697bda6) + the owner's 2026-10-11 rulings:
invariants, mutants (each must be killed by the invariant that names it, and every invariant owns one), probes. Exit 0
iff all hold. With `--out <path>` it writes the machine-readable results there."""
from __future__ import annotations

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
    """MODEL-G3 (R1-05): no cell promotes an edge an existing gate refused."""
    e = E("e"); s = store(e)
    return M.gate(s, e, existing_ok=False) == "not_assertable"


def inv_g4_unit(rules=R):
    """MODEL-G4 (R1-05): a challenged attested fact renders WITH its unit or not at all; the count is all open, whatever
    the budget."""
    e = E("e"); s = store(e)
    for i in range(3):
        M.add_reply(s, e, "challenge", f"no {i}")
    full = M.render(s, e, 10_000)
    tight = M.render(s, e, len(f"{e.relation}: {e.obj}") + 2)
    # 0047 INV-R6: at a budget the unit EXACTLY fits, the count is still every open challenge — the budget decides
    # whether the unit fits, never how many challenges exist
    exact = M.render(s, e, len(full)) if full is not None else None
    return full is not None and "3 open" in full and tight is None and exact == full


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
        M.import_rows(s2, [], [], [M.Reply(id="f", edge="loc", kind="challenge", text="forged", t=1)], "default"); attack = False
    except M.Refused:
        attack = True
    s3 = store(); M.import_rows(s3, [E("y")], [], [M.Reply(id="r", edge="y", kind="challenge", text="mine", t=1)], "default")
    try:
        M.import_rows(store(), [], [], [M.Reply(id="o", edge="nowhere", kind="context", text="", t=1)], "default"); orphan = False
    except M.Refused:
        orphan = True
    # the 0041 amendment's reply rows (INV-RR3): a REDACTED export round-trips through its notice; a marker reply with no
    # notice is a fabricated tombstone and refuses the unit; an ordinary reply under a notice is written treated
    red = E("z", obj=M.MARKER); s4 = store()
    try:
        M.import_rows(s4, [red], [], [M.Reply(id="m", edge="z", kind="challenge", text=M.MARKER, t=1)], "default",
                      notices={"z"})
        round_trip = [r.text for r in s4.replies] == [M.MARKER]
    except M.Refused:
        round_trip = False                              # the redacted round trip R1-07 found refused
    try:
        M.import_rows(store(), [E("w")], [], [M.Reply(id="f2", edge="w", kind="challenge", text=M.MARKER, t=1)], "default")
        fabricated = False
    except M.Refused:
        fabricated = True
    s5 = store()
    M.import_rows(s5, [E("v")], [], [M.Reply(id="o2", edge="v", kind="context", text="I never said that", t=1)], "default",
                  notices={"v"})
    treated = [r.text for r in s5.replies] == [M.MARKER]
    # the 0008 amendment's origin rule (INV-Q5; 0047 INV-R21): local → export → DEFAULT import (imported, testimony,
    # not counted) → export → TRUSTED restore — still imported; a local act restored by its own history is `restored`
    # and counts; and a file's correlation id never occupies the destination's id space (INV-Q4)
    src = store(E("h", "not_attested")); M.confirm(src, src.edges["h"], rules, correlation_id="X1")
    b1 = store(); M.import_rows(b1, *M.export(src, "u"), "default")
    testimony = [c.origin for c in b1.confirmations] == ["imported"] and M.grounding(b1, b1.edges["h"]) == "not_attested"
    b2 = store(); M.import_rows(b2, *M.export(b1, "u"), "trusted")
    chain = [c.origin for c in b2.confirmations] == ["imported"] and M.grounding(b2, b2.edges["h"]) == "not_attested"
    b3 = store(); M.import_rows(b3, *M.export(src, "u"), "trusted")
    own = [c.origin for c in b3.confirmations] == ["restored"] and M.grounding(b3, b3.edges["h"]) == "confirmed"
    lying = M.Confirmation(id="kf", edge="g2", t=1, origin="local", correlation_id="X2")
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
    s3.confirmations.append(M.Confirmation(id="k-old", edge="f", t=1, correlation_id="old1"))
    M.migrate_registry(s3)
    try:
        M.add_reply(s3, f_, "context", "z", correlation_id="old1"); backfilled = False
    except M.Refused:
        backfilled = True
    return replayed and refused == 3 and r1 is r2 and diff and no_id and before_live and backfilled


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


def inv_g13_historical(rules=R):
    """MODEL-G13 (0047 INV-R20; rules draft 3.4): two clocks. T is VALID time and selects facts; acts carry COMMIT time
    and are never filtered by T. A fact valid from 10, challenged at commit time >100, queried as of T=20: an attested
    fact renders WITH the unit, an unattested one is withheld — never the plain line. A fact not held at T is not
    rendered at all (the control)."""
    att = E("ha", "attested"); att.valid_from = 10
    na = E("hn", "not_attested"); na.valid_from = 10
    later = E("hl", "attested"); later.valid_from = 50
    s = store(att, na, later)
    for e in (att, na):
        M.add_reply(s, e, "challenge", "that is wrong")
    a = M.render(s, att, 10_000, at=20); n = M.render(s, na, 10_000, at=20)
    return (a is not None and "[challenged by the subject: 1 open" in a and n is None
            and M.render(s, later, 10_000, at=20) is None)


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


INVARIANTS = {"MODEL-G1": inv_g1_legacy, "MODEL-G2": inv_g2_resolution, "MODEL-G3": inv_g3_restriction, "MODEL-G4": inv_g4_unit,
              "MODEL-G5": inv_g5_acts_stay, "MODEL-G6": inv_g6_survivor_axis, "MODEL-G7": inv_g7_marker_follows_flag,
              "MODEL-G8": inv_g8_write_path, "MODEL-G9": inv_g9_source_redacted, "MODEL-G10": inv_g10_import,
              "MODEL-G11": inv_g11_replay, "MODEL-G12": inv_g12_procedural,
              "MODEL-G13": inv_g13_historical, "MODEL-G14": inv_g14_erasure}


def run_invariants(rules=R) -> dict:
    out = {}
    for k, f in INVARIANTS.items():
        try:
            out[k] = bool(f(rules))
        except Exception as x:
            out[k] = f"ERROR {type(x).__name__}: {x}"
    return out


# ----------------------------------------------------------------------------------------------- mutants
_O = {k: getattr(M, k) for k in ("grounding", "active_challenges", "gate", "render", "absorb", "write", "confirm",
                                   "import_rows", "_replay", "add_reply", "forget_user", "migrate_registry")}


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
        s.confirmations.append(M.Confirmation(id=c.id + "'", edge=incoming.id, t=c.t))
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


def _render_drops_unit(s, e, budget, at=None):
    line = _O["render"](s, e, 10_000, at)
    if line is None:
        return None
    return line if len(line) <= budget else line.split(" [challenged")[0]


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
    """0047 INV-R20's mutant: acts filtered by the VALID-time T, as if their commit time were valid time."""
    if at is None:
        return _O["render"](s, e, budget, at)
    saved = M.active_challenges
    M.active_challenges = lambda s_, e_, at_=None: [r for r in saved(s_, e_) if r.t <= at]
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
    s.confirmations.append(M.Confirmation(id=f"k{len(s.confirmations) + 1}", edge=e.id, t=s.tick()))


def _import_keeps_file_axis(s, edges, confirmations, replies, mode, notices=()):
    keep = {e.id: (e.att, e.source_episode) for e in edges}
    _O["import_rows"](s, edges, confirmations, replies, mode, notices)
    for i, (a, ep) in keep.items():
        s.edges[i].att, s.edges[i].source_episode = a, ep


def _render_counts_selected(s, e, budget, at=None):
    """0047 INV-R6's mutant: the open count derived from the challenges whose text fits the budget, not from all."""
    line = _O["render"](s, e, 10_000, at)
    if line is None or " [challenged" not in line:
        return line if line is None or len(line) <= budget else None
    base = line.split(" [challenged")[0]
    ch = M.active_challenges(s, e, at)
    room, kept = budget - len(base) - len(" [challenged by the subject:  open; latest: ]") - 1, 0
    for c in ch:
        if room - len(c.text[:20]) < 0:
            break
        room -= len(c.text[:20]); kept += 1
    out = f"{base} [challenged by the subject: {kept} open; latest: {ch[-1].text[:20]}]"
    return out if len(out) <= budget else None


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


def _import_admits_unattested_marker(s, edges, confirmations, replies, mode, notices=()):
    """0041 amendment INV-RR3's second mutant: a marker reply admitted with no notice (a fabricated tombstone)."""
    marked = {r.edge for r in replies if r.text == M.MARKER}
    return _O["import_rows"](s, edges, confirmations, replies, mode, set(notices) | marked)


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


# name -> (owning model invariant, installer, the spec rows whose named mutant this is). The third element is what
# model_citations.py checks against each document's §6: a row that cites "model Gn" must have a mutant answering it,
# owned by MODEL-Gn, and a mutant may answer only a row that cites its owner.
MUTANTS = {
    "a legacy row read as attested (R1-02)": ("MODEL-G1", _set("grounding", lambda s, e, at=None: e.att or "attested"), ("0045 INV-G7",)),
    "a context reply mentioning withdrawal clears every challenge (R1-06)": ("MODEL-G2", _set("active_challenges", _challenges_context_clears), ()),
    "any context reply clears all challenges (R1-06, the reviewer's)": ("MODEL-G2", _set("active_challenges", _challenges_any_context_clears), ("0047 INV-R14",)),
    "confirm() drops the active-challenge refusal": ("MODEL-G2", _set("confirm", _confirm_drops_challenge_refusal), ("0047 INV-R13",)),
    "a grid cell promotes an ineligible edge (R1-05)": ("MODEL-G3", _set("gate", lambda s, e, existing_ok=True, at=None: "assertable"), ("0047 INV-R12",)),
    "budget selection drops the unit to fit (R1-05)": ("MODEL-G4", _set("render", _render_drops_unit), ()),
    "the open count derived from the budget-selected challenges": ("MODEL-G4", _set("render", _render_counts_selected), ("0047 INV-R6",)),
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
    "a marker reply admitted with no notice": ("MODEL-G10", _set("import_rows", _import_admits_unattested_marker), ("0041am INV-RR3",)),
    "an ordinary reply under a notice written as-is": ("MODEL-G10", _set("import_rows", _import_untreated_under_notice), ("0041am INV-RR3",)),
    "no replay: a retried confirm/reply writes again (0008)": ("MODEL-G11", _set("_replay", _replay_none), ()),
    "same id + a different request returns the first result": ("MODEL-G11", _set("_replay", _replay_first_on_different), ("0047 INV-R15",)),
    "each verb checks only its own table (ids scoped per verb)": ("MODEL-G11", _set("_replay", _replay_per_verb), ("0047 INV-R15", "0008am INV-Q1")),
    "only the new verb's direction is checked": ("MODEL-G11", _set("_replay", _replay_one_direction), ("0008am INV-Q1",)),
    "live edge state read before the registry": ("MODEL-G11", _set("confirm", _confirm_reads_edge_first), ("0008am INV-Q2",)),
    "the migration without the backfill": ("MODEL-G11", _set("migrate_registry", _migrate_without_backfill), ("0008am INV-Q3",)),
    "an imported act occupies the id space": ("MODEL-G10", _set("import_rows", _import_occupies_ids), ("0008am INV-Q4",)),
    "an imported row keeps the file's id as its correlation_id": ("MODEL-G10", _set("import_rows", _import_keeps_file_id), ("0008am INV-Q4",)),
    "count imported confirmations toward g(e)": ("MODEL-G10", _set("grounding", _grounding_counts_imported), ("0047 INV-R21",)),
    "trusted restore writes recorded acts as local": ("MODEL-G10", _set("import_rows", _restore_writes_local), ("0047 INV-R21", "0008am INV-Q5")),
    "default import keeps the file's origin": ("MODEL-G10", _set("import_rows", _default_keeps_file_origin), ("0047 INV-R21", "0008am INV-Q5")),
    "filter acts by the valid-time T": ("MODEL-G13", _set("render", _render_filters_acts_by_valid_t), ("0047 INV-R20",)),
    "keep replies after forget_user": ("MODEL-G14", _set("forget_user", _forget_keeps_replies), ("0047 INV-R22",)),
    "keep registry rows after erasure": ("MODEL-G14", _set("forget_user", _forget_keeps_registry), ("0047 INV-R22", "0008am INV-Q6")),
    "draft 3.2's rule: an att-less insert is refused, procedural included": ("MODEL-G12", _set("write", _write_refuses_procedural), ("0045 INV-G12",)),
    "a reply attaches to a procedural edge (0047 R19)": ("MODEL-G12", lambda: _install_reply_on_procedural(), ("0047 INV-R19",)),
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
