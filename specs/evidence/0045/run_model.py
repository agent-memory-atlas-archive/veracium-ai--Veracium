"""Runs package II's reference model on rules draft 3.3 (research b06368d5, sha16 5cefe166) + the owner's 2026-10-11 rulings:
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
    """INV-G1 (R1-02): a legacy row (axis NULL) reads `unknown`, never attested, flagged or not."""
    s = store(E("old", None), E("oldf", None, flag=True))
    return M.grounding(s, s.edges["old"]) == "unknown" and M.grounding(s, s.edges["oldf"]) == "unknown"


def inv_g2_resolution(rules=R):
    """INV-G2 (R1-06): context never clears a challenge; resolve clears exactly the one it names; with one open, confirm
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
    """INV-G3 (R1-05): no cell promotes an edge an existing gate refused."""
    e = E("e"); s = store(e)
    return M.gate(s, e, existing_ok=False) == "not_assertable"


def inv_g4_unit(rules=R):
    """INV-G4 (R1-05): a challenged attested fact renders WITH its unit or not at all; the count is all open."""
    e = E("e"); s = store(e)
    for i in range(3):
        M.add_reply(s, e, "challenge", f"no {i}")
    full = M.render(s, e, 10_000)
    tight = M.render(s, e, len(f"{e.relation}: {e.obj}") + 2)
    return full is not None and "3 open" in full and tight is None


def inv_g5_acts_stay(rules=R):
    """INV-G5 (R1-03): absorption never moves a person's act: a prior with a confirmation is NOT absorbed and keeps it;
    nothing is copied to the incoming."""
    p = E("p", obj="Miso"); i = E("i", obj="big cat Miso"); s = store(p)
    M.confirm(s, p, rules)
    return (M.absorb(s, p, i, rules) == "not_absorbed" and s.edges["p"].active
            and not any(c.edge == "i" for c in s.confirmations))


def inv_g6_survivor_axis(rules=R):
    """INV-G6 (§7): an absorption survivor's axis is the INCOMING's own — an attested prior cannot launder a not_attested
    incoming into attested."""
    p = E("p", "attested", obj="Miso"); i = E("i", "not_attested", obj="big cat Miso"); s = store(p)
    M.absorb(s, p, i, rules)
    return M.grounding(s, s.edges["i"]) == "not_attested"


def inv_g7_marker_follows_flag(rules=R):
    """INV-G7 (0019 U5): the marker follows the FLAG on every axis value, legacy `unknown` included; an unflagged row
    has none."""
    out = []
    for att in ("attested", "not_attested", None):
        f = E(f"f{att}", att, flag=True); n = E(f"n{att}", att, flag=False); s = store(f, n)
        out.append("[possible extraction error]" in (M.render(s, f, 10_000) or "")
                   and "[possible extraction error]" not in (M.render(s, n, 10_000) or ""))
    return all(out)


def inv_g8_write_path(rules=R):
    """INV-G8 ("Label, don't block"): every USER statement is stored — attested iff the predicate recognised it, else
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
    """INV-G9 ("Add the link", R1-04 kept): confirm() REFUSES a not_attested edge whose recorded source episode is
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
    """INV-G10 (R1-07, R1-08): default import writes not_attested and a NULL link whatever the file says, and refuses an
    act aimed at a pre-existing local edge; a fresh round trip is admitted; an orphan is refused."""
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
    return capped and attack and "y" in s3.edges and orphan


def inv_g11_replay(rules=R):
    """INV-G11 (R1-09 / 0047 INV-R15, 0008's rule): one user-scoped id space for confirm() and add_reply(): same id +
    same request replays the FIRST result and writes nothing; same id + a different request — another edge, other
    text, or the OTHER verb — is refused; an omitted id has no replay protection (a retry writes again)."""
    a, b = E("a"), E("b"); s = store(a, b)
    k1 = M.confirm(s, a, rules, correlation_id="c1"); k2 = M.confirm(s, a, rules, correlation_id="c1")
    replayed = k1 is k2 and len(s.confirmations) == 1
    refused = 0
    for f in (lambda: M.confirm(s, b, rules, correlation_id="c1"),                 # another edge
              lambda: M.add_reply(s, a, "context", "x", correlation_id="c1")):    # the other verb
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
    return replayed and refused == 2 and r1 is r2 and diff and no_id


def inv_g12_procedural(rules=R):
    """INV-G12 (rules draft 3.3; 0047 INV-R19): a post-version PROCEDURAL insert with no att is ADMITTED (ATTEST never
    runs there), carries no grounding (never read as legacy `unknown`), and no reply attaches to it; a declarative row
    keeps its axis (the control)."""
    s = M.Store()
    pr = M.Edge(id="pr", user="u", relation="procedure", obj="step", att=None, procedural=True)
    got = M.write(s, pr, author="user", attested_by_predicate=False, context="direct")
    admitted = got is not None and "pr" in s.edges and got.att is None and M.grounding(s, got) is None
    try:
        M.add_reply(s, got, "challenge", "no"); refused = False
    except M.Refused as x:
        refused = "procedural-edge" in str(x)
    d = M.write(s, E("d", None), author="user", attested_by_predicate=True, context="direct")
    return admitted and refused and M.grounding(s, d) == "attested"


INVARIANTS = {"INV-G1": inv_g1_legacy, "INV-G2": inv_g2_resolution, "INV-G3": inv_g3_restriction, "INV-G4": inv_g4_unit,
              "INV-G5": inv_g5_acts_stay, "INV-G6": inv_g6_survivor_axis, "INV-G7": inv_g7_marker_follows_flag,
              "INV-G8": inv_g8_write_path, "INV-G9": inv_g9_source_redacted, "INV-G10": inv_g10_import,
              "INV-G11": inv_g11_replay, "INV-G12": inv_g12_procedural}


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
                                   "import_rows", "_replay", "add_reply")}


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


def _replay_none(s, user, correlation_id, digest):
    return None                                                     # no replay: a retry writes again


def _replay_per_verb(s, user, correlation_id, digest):
    """Ids scoped per VERB: a confirm id reused by a reply (or vice versa) is taken as fresh."""
    rec = s.corr.get((user, correlation_id))
    if rec is None or rec[0].split("|")[0] != digest.split("|")[0]:
        return None
    if rec[0] == digest:
        return rec
    raise M.Refused("integrity conflict")


def _confirm_ignores_source(s, e, rules, correlation_id=None):
    if M.active_challenges(s, e):
        raise M.Refused("store.confirm.active-challenge")
    s.confirmations.append(M.Confirmation(id=f"k{len(s.confirmations) + 1}", edge=e.id, t=s.tick()))


def _import_keeps_file_axis(s, edges, confirmations, replies, mode):
    keep = {e.id: (e.att, e.source_episode) for e in edges}
    _O["import_rows"](s, edges, confirmations, replies, mode)
    for i, (a, ep) in keep.items():
        s.edges[i].att, s.edges[i].source_episode = a, ep


MUTANTS = {
    "a legacy row read as attested (R1-02)": ("INV-G1", _set("grounding", lambda s, e, at=None: e.att or "attested")),
    "a context reply mentioning withdrawal clears every challenge (R1-06)": ("INV-G2", _set("active_challenges", _challenges_context_clears)),
    "a grid cell promotes an ineligible edge (R1-05)": ("INV-G3", _set("gate", lambda s, e, existing_ok=True, at=None: "assertable")),
    "budget selection drops the unit to fit (R1-05)": ("INV-G4", _set("render", _render_drops_unit)),
    "absorption copies confirmations to the survivor (R1-03)": ("INV-G5", _set("absorb", _absorb_copies)),
    "an attested prior launders the survivor's axis (§7)": ("INV-G6", _set("absorb", _absorb_launders)),
    "the marker read from the axis, not the flag (0019 U5)": ("INV-G7", _set("render", _render_axis_marker)),
    "the rejected design: an unrecognised user statement is not stored": ("INV-G8", _set("write", _write_blocks)),
    "a non-user FLAGGED triple stored (§2a)": ("INV-G8", _set("write", _write_stores_flagged_nonuser)),
    "the rejected reading: an undeclared USER call counts as the user (user-effective scope)": ("INV-G8", _set("write", _write_absence_is_user)),
    "confirm() ignores a redacted source ('Add the link')": ("INV-G9", _set("confirm", _confirm_ignores_source)),
    "default import keeps the file's axis and link (R1-08)": ("INV-G10", _set("import_rows", _import_keeps_file_axis)),
    "no replay: a retried confirm/reply writes again (0008)": ("INV-G11", _set("_replay", _replay_none)),
    "draft 3.2's rule: an att-less insert is refused, procedural included": ("INV-G12", _set("write", _write_refuses_procedural)),
    "a reply attaches to a procedural edge (0047 R19)": ("INV-G12", lambda: _install_reply_on_procedural()),
    "ids scoped per verb, not shared across confirm and replies (0008)": ("INV-G11", _set("_replay", _replay_per_verb)),
}


def run_mutants() -> dict:
    out = {}
    for name, (owner, install) in MUTANTS.items():
        install()
        try:
            res = run_invariants()
        finally:
            for k, v in _O.items():
                setattr(M, k, v)
        killed = sorted(k for k, v in res.items() if v is not True)
        out[name] = {"owner": owner, "killed_by": killed, "killed_by_owner": owner in killed}
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
    res = {"model": "package II reference model", "rules_draft": "research draft 3.3 (sha16 5cefe166) + the owner's rulings",
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
