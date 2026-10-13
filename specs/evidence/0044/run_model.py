"""Runs the 0044 stage-1 reference model (v2, package I round 3): every invariant on the drafted rules, every declared
mutant, the exhaustive result-domain enumeration (R2-03), and the probes. Writes results only where `--out` says.

A KILL IS SEMANTIC (the 0044 round-2 verdict, R2-08; model II's rule, now shared): the owning invariant RETURNS False
AND the mutated function was CALLED while it ran. An owner that RAISES is a harness failure, never a kill — v1 counted
any exception, and its `once` mutant (wrong signature, TypeError) was reported killed without reaching its assertion.
Other invariants may also fail under a mutant (`killed_by` lists them); that is a further detection, not a defect: the
claim is that the OWNER kills it, not that only the owner does (v1's "exactly" prose was wrong and is withdrawn).
Exit 0 iff every invariant holds and every mutant is killed by its owner."""
from __future__ import annotations

import copy
import itertools
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import arity_model as M  # noqa: E402

R = M.Rules()
_O = {k: getattr(M, k) for k in dir(M) if callable(getattr(M, k)) and not k.startswith("__")
      and getattr(getattr(M, k), "__module__", None) == M.__name__ and not isinstance(getattr(M, k), type)}


def E(i, rel="measures", obj="x", user="u", source="src-a", basis=(), vf=0):
    return M.Edge(id=i, user=user, relation=rel, obj=obj, source=source, basis=basis, valid_from=vf)


def base(vf=0):
    """p (weight 78) superseded by n (weight 80, valid from `vf`) under the old `single` arity; then the v16 step."""
    s = M.Store()
    p, n = E("p", obj="weight 78"), E("n", obj="weight 80", vf=vf)
    s.edges["p"] = p
    M.supersede_single(s, p, n)
    M.schema_step(s)
    return s


def run(s, reg=None, **kw):
    return M.run_data_migration(s, reg if reg is not None else dict(M.DEFAULT_REGISTRY), **kw)


def custom(**over):
    reg = copy.deepcopy(M.DEFAULT_REGISTRY)
    for k, v in over.items():
        reg[k] = v
    return reg


SINGLE = {"arity": "single", "functional": True}


def attempt(f, *a, **kw):
    """Run a verb whose success the invariant asserts. A DOMAIN refusal (M.Refused) is the property failing and is
    returned as data; any other exception propagates, so a harness defect is never read as a kill (R2-08)."""
    try:
        return f(*a, **kw)
    except M.Refused as x:
        return {"refused": str(x)}


# ================================================================================ invariants carried from v1 (adapted)
def inv_revocation(rules=R):
    """INV-M1 (R1-01): a row whose source or contribution-basis source is standing-revoked is WITHHELD, never active; a
    non-revoked control IS restored."""
    s = M.Store()
    for pid, nid, src, basis in (("p", "n", "src-a", ()), ("q", "m", "feed-A", ()), ("c", "d", "src-a", ("feed-B",))):
        pr = E(pid, obj=f"weight {pid}", source=src, basis=basis); s.edges[pid] = pr
        M.supersede_single(s, pr, E(nid, obj=f"weight {nid}9"))
    s.revoked |= {"feed-A", "feed-B"}
    M.schema_step(s); run(s)
    out = {r["edge"]: r["outcome"] for r in M.receipt(s, "u")}
    return (out.get("q") == "withheld_revoked" and not s.edges["q"].active and out.get("c") == "withheld_revoked"
            and not s.edges["c"].active and out.get("p") == "restored" and s.edges["p"].active)


def inv_once_per_plan(rules=R):
    """INV-M2 (R1-03): migrate → undo → rerun does NOT re-select; a crash before a user's commit leaves it untouched and
    a re-call completes; a crash after commit loses nothing; an undone row arriving again in an old pre-format export is
    not restored again (the once-per-plan check is the only guard there)."""
    s = base(); run(s); M.undo(s, "u", "p", rules, correlation_id="c1")
    run(s, op_id="op-2")
    rerun_ok = not s.edges["p"].active
    s2 = base()
    try:
        run(s2, crash_user="u", crash_at="mid_user")
    except M.Crash:
        pass
    untouched = not s2.edges["p"].active and not s2.outcomes and not s2.runs
    run(s2)
    resumed = s2.edges["p"].active
    s3 = base()
    try:
        run(s3, crash_user="u", crash_at="after_commit")
    except M.Crash:
        pass
    recovered = [r["outcome"] for r in M.receipt(s3, "u")] == ["restored"]
    old = M.export(base(), "u", fmt="pre")
    s4 = base(); run(s4); M.undo(s4, "u", "p", rules, correlation_id="c1")
    del s4.edges["p"]; del s4.edges["n"]
    M.import_file(s4, old, "default")
    once = not s4.edges["p"].active
    return rerun_ok and untouched and resumed and recovered and once


def inv_successor_evidence(rules=R):
    """INV-M3 (R1-04): two restatements then one replacement: the pointer names ONE prior; the other reads 'unknown'."""
    s = M.Store()
    p1, p2, n = E("p1", obj="weight 78"), E("p2", obj="weight 78 kg"), E("n", obj="weight 80")
    s.edges["p1"] = p1; s.edges["p2"] = p2
    for pr in (p1, p2):
        pr.active, pr.invalidated_at, pr.reason = False, 0, "superseded"
    n.supersedes = "p2"; s.edges["n"] = n
    M.schema_step(s); run(s)
    rb = {r["edge"]: r["replaced_by"] for r in M.receipt(s, "u")}
    return rb == {"p1": "unknown", "p2": ["n"]}


def inv_undo_identity(rules=R):
    """INV-M4 (R1-05, P-7): an ordinary mutation and a confirmation keep undo eligibility; undo restores the retirement
    fields ONLY; same id + same request replays; a later retirement by another operation ends eligibility."""
    s = base(); run(s)
    s.edges["p"].counters += 3; s.journal.append(("mutated", "p", s.begin(), None))   # a harmless, journaled mutation
    M.confirm(s, "u", "p", cid="k1")
    r1 = attempt(M.undo, s, "u", "p", rules, correlation_id="c1")
    kept = s.edges["p"].counters == 3 and s.edges["p"].reason == "superseded" and not s.edges["p"].active
    r2 = attempt(M.undo, s, "u", "p", rules, correlation_id="c1")
    s2 = base(); run(s2)
    M.retire(s2, "p", "disputed")
    try:
        M.undo(s2, "u", "p", rules); ended = False
    except M.Refused as x:
        ended = "not applicable" in str(x)
    return kept and r1 == {"undone": "p", "already_undone": False} and r2 == {"replayed": "outcome:p"} and ended


def inv_custom_registry(rules=R):
    """INV-M5 (R1-06): a host declaring its own `measures` as single gets no plan row and no restoration; the default
    declaration does."""
    s = base(); run(s, custom(measures=SINGLE))
    s2 = base(); run(s2)
    return not s.edges["p"].active and "measures" not in s.plan and s2.edges["p"].active


def inv_doctor(rules=R):
    """INV-M6 (§4k): an applicable PROOF restoration reads `info`; after undo nothing reports; an unrelated
    active-predecessor pair still warns."""
    s = base(); run(s)
    restored = M.doctor_refs(s) == [("info", "n", "p")]
    M.undo(s, "u", "p", rules, correlation_id="c1")
    after = M.doctor_refs(s) == []
    z, y = E("z", rel="prefers", obj="tea"), E("y", rel="prefers", obj="coffee"); y.supersedes = "z"
    s.edges["z"] = z; s.edges["y"] = y
    return restored and after and ("warn", "y", "z") in M.doctor_refs(s)


def inv_portability(rules=R):
    """INV-M7 (P-4, P-5): a pre-format file's retired rows convert on import (incoming rows only); a local undo is never
    reversed by an import (the record-equal row is skipped); a post-format superseded row with no outcome stays retired
    and is reported unknown-linkage; a trusted own-history restore keeps the exemption with no journal carried; a
    default import's testimony keeps the warning."""
    pre = M.export(base(), "u", fmt="pre")
    dst = M.Store(); M.schema_step(dst); run(dst, plan_only=True)
    rec = M.import_file(dst, pre, "default")
    converted = ("p", "restored") in rec["converted"] and dst.edges["p"].active
    loc = base(); run(loc); M.undo(loc, "u", "p", rules, correlation_id="c1")
    pre_l = M.export(loc, "u", fmt="pre")
    rec2 = M.import_file(loc, pre_l, "default")
    undo_kept = not loc.edges["p"].active and "p" in rec2["skipped_equal"]
    post = base(); post.outcomes.clear()
    dst2 = M.Store(); M.schema_step(dst2); run(dst2, plan_only=True)
    rec3 = M.import_file(dst2, M.export(post, "u"), "default")
    unknown = "p" in rec3["unknown_linkage"] and not dst2.edges["p"].active
    mig = base(); run(mig)
    dst3 = M.Store(origin="store-B"); M.schema_step(dst3); run(dst3, plan_only=True)
    M.import_file(dst3, M.export(mig, "u"), "trusted")
    exempt = M.doctor_refs(dst3) == [("info", "n", "p")] and not any(j[0] == "reinstated" for j in dst3.journal)
    dst4 = M.Store(origin="store-B"); M.schema_step(dst4); run(dst4, plan_only=True)
    M.import_file(dst4, M.export(mig, "u"), "default")
    return converted and undo_kept and unknown and exempt and M.doctor_refs(dst4) == [("warn", "n", "p")]


def inv_redaction(rules=R):
    """INV-M8 (INV-A7): a redacted superseded row is never restored."""
    s = M.Store(); p = E("p", obj="weight 78"); s.edges["p"] = p
    M.supersede_single(s, p, E("n", obj="weight 80"))
    M.redact(s, "p"); M.schema_step(s); run(s)
    s2 = base(); M.redact(s2, "p"); run(s2)               # redacted AFTER the step: inventoried, so arm (2) must hold
    return not s.edges["p"].active and not s2.edges["p"].active


def inv_order_key(rules=R):
    """INV-M9 (the 0003 amendment §4a; QO4 adopted): the key is TOTAL over the post-visibility representation, ranks by
    the RENDERABLE top, never uses an UNRESOLVED or policy-hidden member, and a closer contention ranks first; a
    negative ambiguity ranks first within its tier."""
    H, U = [(3, "U"), (2, "R")], [(3, "R"), (0, "U")]
    groups = {"H": H, "U": U, "none": [(3, "O"), (1, "U")], "single": [(3, "R")], "pair": [(3, "R"), (1, "R")],
              "equal": [(3, "R"), (3, "R")]}
    k = {n: M.order_key(g) for n, g in groups.items()}
    order = sorted(k, key=k.get)
    unresolved_unused = M.order_key([(3, "R"), (2, "U")]) == M.order_key([(3, "R")])
    closer_first = M.order_key([(3, "R"), (2, "R")]) < M.order_key([(3, "R"), (1, "R")])
    neg_first = M.order_key([(2, "R"), (3, "O")]) < M.order_key([(2, "R"), (1, "R")])
    return (order.index("U") < order.index("H") and order[-1] == "none"
            and order.index("equal") < order.index("pair") < order.index("single")
            and unresolved_unused and closer_first and neg_first)


def inv_undo_id_scope(rules=R):
    """INV-M10 (F2): an undo correlation id is USER-scoped: reused on a different edge it is REFUSED."""
    s = M.Store()
    for a, n in (("a", "n1"), ("b", "n2")):
        pr = E(a, obj=f"weight {a}"); s.edges[a] = pr; M.supersede_single(s, pr, E(n, obj=f"weight {n}9"))
    M.schema_step(s); run(s)
    M.undo(s, "u", "a", rules, correlation_id="same")
    try:
        M.undo(s, "u", "b", rules, correlation_id="same")
        return False
    except M.Refused as x:
        return "integrity conflict" in str(x) and s.edges["b"].active


def inv_idless_duplicate(rules=R):
    """INV-M11 (F3): a duplicate undo WITHOUT an id returns the recorded "already undone" — no refusal, no write."""
    s = base(); run(s)
    first = attempt(M.undo, s, "u", "p", rules)
    t = s.txn
    second = attempt(M.undo, s, "u", "p", rules)
    return first.get("already_undone") is False and second == {"undone": "p", "already_undone": True} and s.txn == t


def inv_retained_refusals(rules=R):
    """INV-M12 (§4d, Q8 adopted; research C-5): a refusal in the STEP's inventory stays contested while both members
    are live, with no expiry, until a verb retires a member; a refusal written after the step is not historical,
    however its timestamp reads."""
    s = M.Store()
    p, i = E("rp", obj="weight 78"), E("ri", obj="weight 80")
    s.edges["rp"] = p; s.edges["ri"] = i
    s.refusals.append(("rp", "ri", "measures", s.begin()))
    M.schema_step(s); run(s)
    for _ in range(50):
        s.begin()
    kept = M.contested_pairs(s) == [("rp", "ri")]
    M.retire(s, "ri", "corrected")
    ended = M.contested_pairs(s) == []
    s2 = M.Store(); s2.edges["a"] = E("a", obj="w 1"); s2.edges["b"] = E("b", obj="w 2")
    M.schema_step(s2)
    s2.refusals.append(("a", "b", "measures", -1000))            # written after the step, stamped far in the past
    return kept and ended and M.contested_pairs(s2) == []


# ================================================================================ round 3: the findings, one by one
def inv_era_boundary(rules=R):
    """INV-M13 (R2-01; research C-4 and its residual): eligibility is INVENTORY membership, never a clock comparison.
    A pre-upgrade retirement dated 2050 IS eligible; a post-upgrade retirement dated 1990 is NOT; an inventoried edge
    reinstated and then re-retired with an IDENTICAL (invalidated_at, reason) is NOT."""
    s = M.Store()
    fut = E("fut", obj="weight 78"); s.edges["fut"] = fut
    M.supersede_single(s, fut, E("fn", obj="weight 80", vf=2050))                 # pre-upgrade, valid-time 2050
    re = E("re", obj="weight 60"); s.edges["re"] = re
    M.supersede_single(s, re, E("rn", obj="weight 61", vf=5))                     # pre-upgrade, then reinstated ...
    M.schema_step(s)
    late = E("late", rel="measures", obj="weight 70"); s.edges["late"] = late
    M.supersede_single(s, late, E("ln", obj="weight 71", vf=1990))                # post-upgrade, valid-time 1990
    M.restore_source(s, "re")                                                     # ... reinstated (any reason) ...
    s.edges["re"].active, s.edges["re"].invalidated_at, s.edges["re"].reason = False, 5, "superseded"   # ... same tuple
    run(s)
    return s.edges["fut"].active and not s.edges["late"].active and not s.edges["re"].active


def inv_plan_states(rules=R):
    """INV-M14 (R2-02, Q9): a plan HEADER is written even when empty; a later different registry is refused
    (registry-changed) and restores nothing; the same registry continues; plan-only writes the header and restores
    nothing; a pre-format import before any header is refused naming the prerequisite; doctor's I30 phase is read from
    the header (initialized-empty is info, never the pre-plan warning)."""
    allc = custom(measures=SINGLE, prefers=SINGLE, health_state=SINGLE)
    s = base()
    pre_phase = M.doctor_data_migration(s)[0] == "warn"
    r1 = run(s, allc)
    empty = M.plan_state(s) == "initialized-empty" and r1["outcome"] in ("migrated", "planned")
    empty_info = M.doctor_data_migration(s)[0] == "info"
    r2 = run(s, op_id="op-2")
    refused = r2["outcome"] == "registry-changed" and not s.edges["p"].active
    r3 = run(s, allc, op_id="op-3")
    same_continues = r3["outcome"] in ("complete", "migrated")
    s2 = base()
    try:
        M.import_file(s2, M.export(base(), "u", fmt="pre"), "default"); pre_refused = False
    except M.Refused as x:
        pre_refused = "requires-data-migration-plan" in str(x)
    po = run(s2, plan_only=True)
    po2 = run(s2, plan_only=True, op_id="op-x")
    plan_only = (po["outcome"] == "planned" and po["store_changed"] and not s2.edges["p"].active
                 and po2["outcome"] == "already-planned" and not po2["store_changed"])
    incomplete = M.doctor_data_migration(s2)[0] == "warn"
    run(s2)
    complete = M.doctor_data_migration(s2)[0] == "none"
    return (pre_phase and empty and empty_info and refused and same_continues and pre_refused and plan_only
            and incomplete and complete)


def _durable(s):
    d = copy.deepcopy(vars(s))
    d.pop("txn"); d.pop("act_counter")
    return d


def enumerate_results() -> list:
    """R2-03: the WHOLE small domain — schema version × attestation × header before (none / equal / different) ×
    plan-only × 0–3 users × every failing subset. Each call's result must be a row of the closed table, its
    `store_changed` must equal whether the store's durable state changed, its named failures must be exactly the
    failing users, and operation_status must recover its commits from durable facts alone."""
    cases = []
    for v16, attested, before, plan_only, n in itertools.product((True, False), (True, False),
                                                                 ("none", "equal", "different"), (False, True),
                                                                 range(4)):
        users = [f"u{i}" for i in range(n)]
        for k in range(n + 1):
            for fails in itertools.combinations(users, k):
                s = M.Store()
                for u in users:
                    p = E(f"p-{u}", user=u, obj="weight 78"); s.edges[p.id] = p
                    M.supersede_single(s, p, E(f"n-{u}", user=u, obj="weight 80"))
                if v16:
                    M.schema_step(s)
                    if before == "equal":
                        M.write_plan(s, dict(M.DEFAULT_REGISTRY), "op-0")
                    elif before == "different":
                        M.write_plan(s, custom(measures=SINGLE), "op-0")
                pre = _durable(s)
                res = M.run_data_migration(s, dict(M.DEFAULT_REGISTRY), op_id="op-1", plan_only=plan_only,
                                           attested=attested, fail_users=fails)
                st = M.operation_status(s, "op-1")
                cases.append({"case": (v16, attested, before, plan_only, n, list(fails)), "result": res,
                              "changed": _durable(s) != pre, "status": st})
    return cases


def inv_result_totality(rules=R):
    """INV-M15 (R2-03): over the enumerated domain, every result is in the closed table; `store_changed` is honest
    (equal to whether durable state changed, including a plan-only commit and an all-failed call that wrote the
    header); named failures equal the failing users; operation discovery recovers exactly the committed users; and
    the all-failed and plan-only cases are reached (a domain that never reaches them proves nothing about them)."""
    seen = set()
    for c in enumerate_results():
        r = c["result"]
        if r["outcome"] not in M.RESULT_ROWS:
            return False
        want = M.RESULT_ROWS[r["outcome"]]
        if want is not None and r["store_changed"] is not want:
            return False
        if r["store_changed"] != c["changed"]:
            return False
        if c["status"]["committed"] != sorted(r["committed"]):
            return False
        v16, attested, before, plan_only, n, fails = c["case"]
        if r["outcome"] in ("migrated", "partial", "failed") and sorted(r["failed"]) != sorted(fails):
            return False
        seen.add(r["outcome"])
    return {"failed", "planned", "already-planned", "partial", "migrated", "complete", "registry-changed",
            "requires-schema-step", "preflight-refused"} <= seen


def inv_applicability(rules=R):
    """INV-M16 (R2-04 ¶1; research C-6): after restoration → source revocation → lift the edge is ACTIVE but the
    restoration is NOT applicable — no exemption, no undo; a harmless mutation and a confirmation keep it; a redaction
    ends it (redaction is not a retirement, and undo refuses a redacted edge)."""
    s = base(); run(s)
    M.revoke_source(s, "src-a"); M.lift_source(s, "src-a")
    active_again = s.edges["p"].active
    no_exempt = ("info", "n", "p") not in M.doctor_refs(s)
    try:
        M.undo(s, "u", "p", rules); undo_refused = False
    except M.Refused as x:
        undo_refused = "not applicable" in str(x)
    s2 = base(); run(s2)
    s2.edges["p"].counters += 1; M.confirm(s2, "u", "p", cid="k")
    kept = s2.outcomes[("plan-1", "p")]["applicable"]
    s3 = base(); run(s3); M.redact(s3, "p")
    try:
        M.undo(s3, "u", "p", rules); red_refused = False
    except M.Refused:
        red_refused = True
    return active_again and no_exempt and undo_refused and kept and red_refused


def inv_shared_id_space(rules=R):
    """INV-M17 (R2-04 ¶2–3; 0008am INV-Q1/Q2): one id space across verbs in BOTH directions — an undo id conflicts on
    confirm and a confirm id conflicts on undo; a completed undo REPLAYS from the registry after its edge was later
    retired and after it is absent, never reading live edge state first."""
    s = base(); run(s)
    M.undo(s, "u", "p", rules, correlation_id="X")
    try:
        M.confirm(s, "u", "n", cid="X"); a = False
    except M.Refused as x:
        a = "held by undo" in str(x)
    s2 = base(); run(s2)
    M.confirm(s2, "u", "n", cid="Y")
    try:
        M.undo(s2, "u", "p", rules, correlation_id="Y"); b = False
    except M.Refused as x:
        b = "held by confirm" in str(x)
    s3 = base(); run(s3)
    M.undo(s3, "u", "p", rules, correlation_id="Z")
    M.retire(s3, "p", "disputed")
    r_ret = attempt(M.undo, s3, "u", "p", rules, correlation_id="Z")
    del s3.edges["p"]
    r_abs = attempt(M.undo, s3, "u", "p", rules, correlation_id="Z")
    return a and b and r_ret == {"replayed": "outcome:p"} and r_abs == {"replayed": "outcome:p"}


def inv_erasure(rules=R):
    """INV-M18 (R2-07; 0008am INV-Q6): user erasure removes the user's outcomes, runs, registry rows and inventory
    atomically; a retry after erasure is not a replay; a recreated user has nothing restorable; a retained outcome whose
    edge is gone renders `no longer held` from the outcome row alone."""
    s = base(); run(s); M.undo(s, "u", "p", rules, correlation_id="c1")
    M.forget_user(s, "u")
    gone = not s.outcomes and not s.runs and not s.registry and not s.inventory
    try:
        M.undo(s, "u", "p", rules, correlation_id="c1"); not_replayed = False
    except M.Refused as x:
        not_replayed = "no migration outcome" in str(x)
    s.edges["p"] = E("p", obj="weight 78"); M.supersede_single(s, s.edges["p"], E("n", obj="weight 80"))
    run(s, op_id="op-2")
    recreated = not s.edges["p"].active
    s2 = base(); run(s2); del s2.edges["p"]
    try:
        rows = M.receipt(s2, "u")
        rendered = rows and rows[0]["object"] == "no longer held"
    except KeyError:
        rendered = False
    return gone and not_replayed and recreated and bool(rendered)


def inv_testimony(rules=R):
    """INV-M19 (R2-05; the 0008am origin matrix, one trust model): migrate → export → DEFAULT import → export → TRUSTED
    restore reads `imported` at the end and warns; no undo from testimony; the unit is validated before any write — an
    outcome with no edge, a conflicting duplicate, and an applicable outcome on a retired edge each refuse."""
    a = base(); run(a)
    b = M.Store(origin="store-B"); M.schema_step(b); run(b, plan_only=True)
    M.import_file(b, M.export(a, "u"), "default")
    c = M.Store(origin="store-C"); M.schema_step(c); run(c, plan_only=True)
    M.import_file(c, M.export(b, "u"), "trusted")
    chain = c.outcomes[("plan-1", "p")]["origin"] == "imported" and M.doctor_refs(c) == [("warn", "n", "p")]
    try:
        M.undo(b, "u", "p", rules); no_undo = False
    except M.Refused as x:
        no_undo = "testimony" in str(x)
    f = M.export(a, "u")
    bad = []
    g1 = copy.deepcopy(f); g1["edges"] = [e for e in g1["edges"] if e.id != "p"]
    g2 = copy.deepcopy(f); k = next(iter(g2["outcomes"])); g2["outcomes"][("plan-x", "p")] = dict(g2["outcomes"][k], outcome="withheld_revoked")
    g3 = copy.deepcopy(f); next(e for e in g3["edges"] if e.id == "p").active = False
    for g in (g1, g2, g3):
        d = M.Store(origin="store-D"); M.schema_step(d); run(d, plan_only=True)
        try:
            M.import_file(d, g, "trusted"); bad.append(False)
        except M.Refused:
            bad.append(not d.edges and not d.outcomes)
    return chain and no_undo and all(bad)


def inv_collision(rules=R):
    """INV-M20 (R2-06; 0009 §4c kept): a record-equal edge is skipped; a DIFFERING one under a held id refuses the WHOLE
    import and keeps the held row; a re-import after a local undo leaves the undone row as it is."""
    src = M.Store(); src.edges["x"] = E("x", obj="weight 80"); M.schema_step(src); run(src, plan_only=True)
    dst = M.Store(); dst.edges["x"] = E("x", obj="weight 78"); M.schema_step(dst); run(dst, plan_only=True)
    try:
        M.import_file(dst, M.export(src, "u"), "trusted"); refused = False
    except M.Refused as x:
        refused = "different content" in str(x)
    held = dst.edges["x"].obj == "weight 78"
    same = M.Store(); same.edges["x"] = E("x", obj="weight 80"); M.schema_step(same); run(same, plan_only=True)
    rec = M.import_file(same, M.export(src, "u"), "trusted")
    equal_skip = rec["skipped_equal"] == ["x"]
    return refused and held and equal_skip


def inv_arity(rules=R):
    """INV-M21 (R2-08's arity row; 0044 §4a/§4b): `keyed` refused; a dual declaration that disagrees refused;
    `functional` alone maps; under `multi` a differing value never supersedes, unrelated quantities never merge, and a
    contained value is absorbed; under `single` a differing value supersedes."""
    for bad in ({"measures": {"arity": "keyed", "functional": None}},
                {"measures": {"arity": "multi", "functional": True}},
                {"measures": {"arity": None, "functional": None}}):
        try:
            M.admit_registry(bad); return False
        except M.Refused:
            pass
    mapped = M.admit_registry({"x": {"arity": None, "functional": True}})["x"]["arity"] == "single"
    reg = dict(M.DEFAULT_REGISTRY)
    s = M.Store()
    M.write_value(s, E("a", obj="weight 78 kg"), reg)
    r1 = M.write_value(s, E("b", obj="weight 80 kg"), reg)
    r2 = M.write_value(s, E("c", obj="savings 4200"), reg)
    r3 = M.write_value(s, E("d", obj="80"), reg)
    multi_ok = (r1 == "added" and r2 == "added" and r3 == "absorbed_duplicate"
                and s.edges["a"].active and s.edges["b"].active and "d" not in s.edges)
    s2 = M.Store()
    M.write_value(s2, E("w", rel="works_as", obj="dentist"), reg)
    r4 = M.write_value(s2, E("w2", rel="works_as", obj="nurse"), reg)
    single_ok = r4 == "superseded" and not s2.edges["w"].active and s2.edges["w"].reason == "superseded"
    return mapped and multi_ok and single_ok


def inv_canonical_uid(rules=R):
    """INV-M22 (research C-3): the canonical identity encoding separates a separator inside a field, a NUL and an empty
    field."""
    pairs = [(("a", "b:c", "d"), ("a:b", "c", "d")), (("a", "b\x00c"), ("a\x00b", "c")), (("a", "", "b"), ("a", "b", ""))]
    return all(M.canonical_uid(*x) != M.canonical_uid(*y) for x, y in pairs)


def inv_j1_closed_reason(rules=R):
    """INV-J1 (0029 amendment): a `reinstated` write with NULL or an outside reason is refused and writes nothing."""
    s = base()
    n0 = len(s.journal)
    refused = 0
    for bad in (None, "other", ""):
        try:
            M.journal_reinstated(s, "p", bad)
        except M.Refused:
            refused += 1
    M.journal_reinstated(s, "p", "source_restored"); M.journal_reinstated(s, "p", "arity_reclassified")
    return refused == 3 and len(s.journal) == n0 + 2


def inv_j2_old_nulls(rules=R):
    """INV-J2: an old NULL-reason event reads as `source_restored` and is NOT rewritten."""
    ev = ("reinstated", "p", 1, None)
    s = M.Store(); s.journal.append(ev)
    return M.reinstated_reason(s.journal[0]) == "source_restored" and s.journal[0] == ev


def inv_j3_writers(rules=R):
    """INV-J3: each writer writes ITS reason."""
    s = base(); run(s)
    arity = [j for j in s.journal if j[0] == "reinstated" and j[1] == "p"]
    s2 = base()
    M.restore_source(s2, "p")
    src = [j for j in s2.journal if j[0] == "reinstated"]
    return ([M.reinstated_reason(j) for j in arity] == ["arity_reclassified"]
            and [M.reinstated_reason(j) for j in src] == ["source_restored"])


INVARIANTS = {"INV-M1": inv_revocation, "INV-M2": inv_once_per_plan, "INV-M3": inv_successor_evidence,
              "INV-M4": inv_undo_identity, "INV-M5": inv_custom_registry, "INV-M6": inv_doctor,
              "INV-M7": inv_portability, "INV-M8": inv_redaction, "INV-M9": inv_order_key,
              "INV-M10": inv_undo_id_scope, "INV-M11": inv_idless_duplicate, "INV-M12": inv_retained_refusals,
              "INV-M13": inv_era_boundary, "INV-M14": inv_plan_states, "INV-M15": inv_result_totality,
              "INV-M16": inv_applicability, "INV-M17": inv_shared_id_space, "INV-M18": inv_erasure,
              "INV-M19": inv_testimony, "INV-M20": inv_collision, "INV-M21": inv_arity, "INV-M22": inv_canonical_uid,
              "INV-J1": inv_j1_closed_reason, "INV-J2": inv_j2_old_nulls, "INV-J3": inv_j3_writers}


# ================================================================================ mutants
def _set(name, fn):
    return lambda: setattr(M, name, fn)


def _wrap(name, make):
    return lambda: setattr(M, name, make(_O[name]))


def _consider_without_once(orig):
    def consider(s, e, imported=False):                 # v1's mutant had the wrong signature (no `imported`): fixed
        saved = dict(s.outcomes); s.outcomes.clear()
        try:
            return orig(s, e, imported=imported)
        finally:
            s.outcomes.update(saved)
    return consider


def _consider_valid_time(orig):
    """R2-01's own mechanism: eligibility by `invalidated_at < the step's time` — a VALID-time value compared with a
    TRANSACTION-time one (the shipped cutoff's shape; the obligation map's typed-carrier check refuses it statically)."""
    def consider(s, e, imported=False):
        pid = s.plan.get(e.relation)
        if not pid or e.active or e.reason != "superseded" or (pid, e.id) in s.outcomes or e.redacted:
            return None
        if not imported and not (e.invalidated_at < s.header["written_txn"]):
            return None
        return "withheld_revoked" if M.would_be_revoked(s, e) else "restored"
    return consider


def _reinstate_keeps_membership(orig):
    def journal_reinstated(s, edge_id, reason, t=None):
        if reason not in M.REINSTATEMENT_REASONS:
            raise M.Refused("bad reason")
        s.journal.append(("reinstated", edge_id, t if t is not None else s.begin(), reason))
    return journal_reinstated


def _header_only_when_nonempty(orig):
    """Round 2's design, well-formed: the call runs, but an EMPTY plan leaves no durable trace afterwards."""
    def run_data_migration(s, registry, **kw):
        r = orig(s, registry, **kw)
        if s.header is not None and not s.plan:
            s.header = None
        return r
    return run_data_migration


def _no_digest_check(orig):
    def write_plan(s, registry, op_id):
        if s.header is not None:
            s.header = None; s.plan.clear()                  # re-plan whatever the stored digest
        return orig(s, registry, op_id)
    return write_plan


def _import_before_plan_silent(orig):
    def import_file(s, f, mode, op_id="op-import"):
        if f["format"] == "pre" and s.header is None:
            s.header = {"plan_id": "plan-0", "registry_digest": "", "op_id": op_id, "written_txn": s.txn}
            try:
                return orig(s, f, mode, op_id)
            finally:
                s.header = None
        return orig(s, f, mode, op_id)
    return import_file


def _doctor_from_rows(orig):
    def doctor_data_migration(s):
        if not s.schema_v16:
            return ("none", "below v16")
        if not s.plan:
            return ("warn", "may have values to restore") if s.inventory else ("none", "nothing")
        return orig(s)
    return doctor_data_migration


def _changed_only_on_commit(orig):
    def run_data_migration(s, registry, **kw):
        r = orig(s, registry, **kw)
        r["store_changed"] = bool(r["committed"])           # the round-2 table: a plan-only commit reads unchanged
        return r
    return run_data_migration


def _no_failed_row(orig):
    def run_data_migration(s, registry, **kw):
        r = orig(s, registry, **kw)
        if r["outcome"] == "failed":
            r["outcome"] = "complete"                        # v2's table had no row for all-failed
        return r
    return run_data_migration


def _applicable_is_active_bit(orig):
    def undo(s, user, edge_id, rules=None, correlation_id=None):
        for (pid, eid), o in s.outcomes.items():
            if eid == edge_id and s.edges.get(edge_id) is not None and s.edges[edge_id].active:
                o["applicable"] = True                       # "still active" read as the restoration's lifetime
        return orig(s, user, edge_id, rules, correlation_id)
    return undo


def _clear_only_on_superseded(orig):
    def retire(s, edge_id, reason, at_valid=0):
        t = s.begin()
        e = s.edges[edge_id]
        e.active, e.invalidated_at, e.reason = False, at_valid, reason
        if reason == "superseded":
            M._clear_applicable(s, edge_id)
        s.journal.append(("invalidated", edge_id, t, reason))
    return retire


def _redaction_keeps_applicable(orig):
    def redact(s, edge_id):
        e = s.edges[edge_id]
        e.relation, e.obj = M.MARKER, M.MARKER              # content replaced; the flag and the edge's redacted bit kept
    return redact


def _per_verb_ids(orig):
    def _replay(s, user, cid, verb, digest):
        if cid is None:
            return None
        rec = s.registry.get((user, cid))
        if rec is None or rec["verb"] != verb:
            return None                                      # each verb sees only its own ids
        if rec["digest"] == digest:
            return {"replayed": rec["result_ref"]}
        raise M.Refused("integrity conflict: correlation id held by " + rec["verb"])
    return _replay


def _per_target_ids(orig):
    """Round 1's draft-1 scope: an id is looked up per target, so the same id on ANOTHER edge reads as a fresh request."""
    def _replay(s, user, cid, verb, digest):
        rec = s.registry.get((user, cid)) if cid is not None else None
        if rec is not None and rec["verb"] == verb and rec["digest"] != digest:
            return None
        return orig(s, user, cid, verb, digest)
    return _replay


def _edge_before_registry(orig):
    """The model's v1 order (R2-04 ¶3): live edge state read FIRST — an absent or retired edge refuses before the
    registry could replay the completed request."""
    def undo(s, user, edge_id, rules=None, correlation_id=None):
        e = s.edges.get(edge_id)
        if e is None or not e.active:
            raise M.Refused("edge retired or absent")
        return orig(s, user, edge_id, rules, correlation_id)
    return undo


def _erasure_keeps_registry(orig):
    def forget_user(s, user):
        keep = dict(s.registry)
        orig(s, user)
        s.registry = keep
    return forget_user


def _receipt_reads_live(orig):
    def receipt(s, user):
        return [{"edge": eid, "outcome": o["outcome"], "object": s.edges[eid].obj,
                 "replaced_by": "unknown", "undone": o["undone"]}
                for (pid, eid), o in sorted(s.outcomes.items()) if o["user"] == user]
    return receipt


def _trust_from_mode(orig):
    def import_file(s, f, mode, op_id="op-import"):
        rec = orig(s, f, mode, op_id)
        if mode == "trusted":
            for o in s.outcomes.values():
                o["origin"] = "local" if o["origin"] == "imported" else o["origin"]
        return rec
    return import_file


def _undo_from_testimony(orig):
    def undo(s, user, edge_id, rules=None, correlation_id=None):
        for o in s.outcomes.values():
            if o["origin"] == "imported":
                o["origin"] = "restored"
        return orig(s, user, edge_id, rules, correlation_id)
    return undo


def _skip_unit_validation(orig):
    def import_file(s, f, mode, op_id="op-import"):
        f2 = copy.deepcopy(f)
        for e in f2["edges"]:
            e.active = True                                   # the validation's inputs neutralised: nothing reads as bad
        f2["outcomes"] = {k: v for k, v in f2["outcomes"].items()
                          if k[1] in {e.id for e in f2["edges"]} and k[0] == "plan-1"}
        return orig(s, f2, mode, op_id)
    return import_file


def _skip_every_collision(orig):
    def import_file(s, f, mode, op_id="op-import"):
        f2 = copy.deepcopy(f)
        f2["edges"] = [e for e in f2["edges"] if e.id not in s.edges]
        return orig(s, f2, mode, op_id)
    return import_file


def _multi_supersedes(orig):
    def write_value(s, incoming, reg):
        reg2 = {k: dict(v, arity="single", functional=True) if v.get("arity") == "multi" else v for k, v in reg.items()}
        return orig(s, incoming, reg2)
    return write_value


def _keyed_admitted(orig):
    def admit_registry(reg):
        reg2 = {k: (dict(v, arity="multi", functional=False) if v.get("arity") == "keyed" else v) for k, v in reg.items()}
        return orig(reg2)
    return admit_registry


def _functional_wins(orig):
    def admit_registry(reg):
        reg2 = {k: (dict(v, arity=None) if v.get("functional") is not None else v) for k, v in reg.items()}
        return orig(reg2)
    return admit_registry


def _separator_uid(orig):
    return lambda *parts: ":".join(str(p) for p in parts)          # the collision class C-3 names


def _refusals_by_timestamp(orig):
    def contested_pairs(s):
        step = min((t for *_x, t in s.refusals), default=0)
        return [(p, i) for p, i, rel, t in s.refusals if t <= step and p in s.edges and i in s.edges
                and s.edges[p].active and s.edges[i].active]
    return contested_pairs


def _successor_guess(orig):
    def receipt(s, user):
        rows = orig(s, user)
        for r in rows:
            if r["replaced_by"] == "unknown":
                cands = sorted(x.id for x in s.edges.values() if x.active and x.id != r["edge"])
                r["replaced_by"] = [cands[-1]] if cands else "unknown"
        return rows
    return receipt


def _latest_event_eligibility(orig):
    def undo(s, user, edge_id, rules=None, correlation_id=None):
        last = [j for j in s.journal if j[1] == edge_id]
        if not last or last[-1][0] != "reinstated":
            raise M.Refused("latest event is not reinstated")
        return orig(s, user, edge_id, rules, correlation_id)
    return undo


def _whole_snapshot(orig):
    def undo(s, user, edge_id, rules=None, correlation_id=None):
        r = orig(s, user, edge_id, rules, correlation_id)
        if edge_id in s.edges:
            s.edges[edge_id].counters = 0
        return r
    return undo


def _blanket_exemption(orig):
    return lambda s: [("info", e, p) for _lvl, e, p in orig(s)]


def _rescan_local(orig):
    def import_file(s, f, mode, op_id="op-import"):
        rec = orig(s, f, mode, op_id)
        if f["format"] == "pre":
            for e in s.edges.values():
                if e.reason == "superseded" and e.relation in s.plan:
                    e.active, e.invalidated_at, e.reason = True, None, None
        return rec
    return import_file


def _install_redaction_two_fault():
    """Two coordinated faults (INV-A7's two arms): a future redaction that KEEPS the relation (only the object marked,
    no attestation bit), AND eligibility that no longer looks for the marker or the attestation."""
    def redact(s, edge_id):
        s.edges[edge_id].obj = M.MARKER

    orig = _O["consider"]

    def consider(s, e, imported=False):
        obj = e.obj
        e.obj = "x" if obj == M.MARKER else obj
        try:
            return orig(s, e, imported=imported)
        finally:
            e.obj = obj
    M.redact, M.consider = redact, consider


def _idless_refuse(orig):
    def undo(s, user, edge_id, rules=None, correlation_id=None):
        return orig(s, user, edge_id, M.Rules(undo_without_id_duplicate="refuse"), correlation_id)
    return undo


def _order_key_global(orig):
    def order_key(group, o_reading="other_than_top", negative="as_is", slot="s"):
        allm = sorted((a for a, _k in group), reverse=True)
        if not any(k == "R" for _a, k in group):
            return (1, 0, 0, 0, slot)
        return (0, -allm[0], (allm[0] - allm[1]) if len(allm) > 1 else float("inf"), -len(allm), slot)
    return order_key


def _order_key_o_only(orig):
    return lambda group, o_reading="other_than_top", negative="as_is", slot="s": orig(group, "non_emitted", negative, slot)


def _negative_last(orig):
    return lambda group, o_reading="other_than_top", negative="as_is", slot="s": orig(group, o_reading, "last", slot)


MUTANTS = {
    # name: (owning invariant, installer)
    "omit the standing-revocation check (R1-01)": ("INV-M1", _set("would_be_revoked", lambda s, e: False)),
    "selector-only completion: no outcome-row check (R1-03)": ("INV-M2", _wrap("consider", _consider_without_once)),
    "guess the successor from the latest active row (R1-04)": ("INV-M3", _wrap("receipt", _successor_guess)),
    "undo eligibility = latest journal event is 'reinstated' (R1-05)": ("INV-M4", _wrap("undo", _latest_event_eligibility)),
    "undo restores the whole pre-snapshot, counters included (R1-05)": ("INV-M4", _wrap("undo", _whole_snapshot)),
    "name-only selector: the plan ignores the registry (R1-06)": ("INV-M5", _wrap("admit_registry", lambda o: (lambda reg: {k: dict(M.DEFAULT_REGISTRY.get(k, v)) for k, v in o(reg).items()}))),
    "doctor exemption as a blanket (§4k)": ("INV-M6", _wrap("doctor_refs", _blanket_exemption)),
    "import conversion rescans local rows (P-4)": ("INV-M7", _wrap("import_file", _rescan_local)),
    "redaction keeps the relation AND eligibility drops arm (2) (INV-A7)": ("INV-M8", _install_redaction_two_fault),
    "order key over ALL members (R1-08)": ("INV-M9", _wrap("order_key", _order_key_global)),
    "ambiguity over O only (the first wording)": ("INV-M9", _wrap("order_key", _order_key_o_only)),
    "a negative ambiguity ranks last (QO4's alternative)": ("INV-M9", _wrap("order_key", _negative_last)),
    "each verb checks only its own ids (0008am INV-Q1)": ("INV-M17", _wrap("_replay", _per_verb_ids)),
    "an undo id scoped per target edge (F2)": ("INV-M10", _wrap("_replay", _per_target_ids)),
    "a duplicate id-less undo is refused (F3)": ("INV-M11", _wrap("undo", _idless_refuse)),
    "historical refusals by timestamp, not the step's inventory (C-5)": ("INV-M12", _wrap("contested_pairs", _refusals_by_timestamp)),
    "eligibility by invalidated_at < the step's time (R2-01)": ("INV-M13", _wrap("consider", _consider_valid_time)),
    "a reinstatement keeps inventory membership (C-4 residual)": ("INV-M13", _wrap("journal_reinstated", _reinstate_keeps_membership)),
    "an empty plan writes no header (R2-02)": ("INV-M14", _wrap("run_data_migration", _header_only_when_nonempty)),
    "a later registry re-plans, no digest check (R2-02)": ("INV-M14", _wrap("write_plan", _no_digest_check)),
    "a pre-format import before any plan converts silently (Q9)": ("INV-M14", _wrap("import_file", _import_before_plan_silent)),
    "doctor's phase from relation rows, not the header (I30)": ("INV-M14", _wrap("doctor_data_migration", _doctor_from_rows)),
    "store_changed only when a user committed (R2-03)": ("INV-M15", _wrap("run_data_migration", _changed_only_on_commit)),
    "no row for all-failed: reported complete (R2-03)": ("INV-M15", _wrap("run_data_migration", _no_failed_row)),
    "applicability = the current active bit (R2-04)": ("INV-M16", _wrap("undo", _applicable_is_active_bit)),
    "applicability cleared only by `superseded` retirements (R2-04)": ("INV-M16", _wrap("retire", _clear_only_on_superseded)),
    "redaction keeps applicability (C-6)": ("INV-M16", _wrap("redact", _redaction_keeps_applicable)),
    "undo reads the edge before the registry (R2-04 ¶3)": ("INV-M17", _wrap("undo", _edge_before_registry)),
    "erasure keeps registry rows (R2-07, INV-Q6)": ("INV-M18", _wrap("forget_user", _erasure_keeps_registry)),
    "the receipt reads the live edge (R2-07)": ("INV-M18", _wrap("receipt", _receipt_reads_live)),
    "a trusted restore sets proof from the import mode (R2-05)": ("INV-M19", _wrap("import_file", _trust_from_mode)),
    "undo from testimony (R2-05)": ("INV-M19", _wrap("undo", _undo_from_testimony)),
    "the outcome unit is not validated before writing (R2-05)": ("INV-M19", _wrap("import_file", _skip_unit_validation)),
    "every collision skipped (R2-06, the v1 model)": ("INV-M20", _wrap("import_file", _skip_every_collision)),
    "`multi` supersedes a differing value (§4b)": ("INV-M21", _wrap("write_value", _multi_supersedes)),
    "`keyed` admitted (§4a)": ("INV-M21", _wrap("admit_registry", _keyed_admitted)),
    "the dual carrier: `functional` wins silently (§4a)": ("INV-M21", _wrap("admit_registry", _functional_wins)),
    "identity by separator join (C-3)": ("INV-M22", _wrap("canonical_uid", _separator_uid)),
    "the journal accepts any reason (0029 J1)": ("INV-J1", _set("journal_reinstated", lambda s, e, r, t=None: s.journal.append(("reinstated", e, s.begin(), r)))),
    "old NULL events read 'unknown' (0029 J2)": ("INV-J2", _set("reinstated_reason", lambda ev: ev[3] if len(ev) > 3 and ev[3] is not None else "unknown")),
    "the writers' reasons swapped (0029 J3)": ("INV-J3", _wrap("restore_source", lambda o: (lambda s, eid: (setattr(s.edges[eid], "active", True), M.journal_reinstated(s, eid, "arity_reclassified"))))),
}


def run_invariants(rules=R) -> dict:
    res = {}
    for name, f in INVARIANTS.items():
        try:
            res[name] = f(rules) is True
        except Exception as x:                                          # an exception is a failure, named
            res[name] = f"ERROR {type(x).__name__}: {x}"
    return res


def run_mutants() -> dict:
    """Each mutant is installed, then judged. A KILL is semantic: the owner RETURNS False and the mutated function was
    CALLED while it ran (model II's rule; R2-08)."""
    out = {}
    for name, (owner, install) in MUTANTS.items():
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
                     "killed_by": killed, "killed_by_owner": owner_outcome == "failed" and reached}
    return out


def probes() -> dict:
    """What the drafts leave to the reader, executed."""
    p = {}
    dom = enumerate_results()
    p["result_domain_size"] = len(dom)
    p["result_outcomes_reached"] = sorted({c["result"]["outcome"] for c in dom})
    p["failed_row_store_changed_values"] = sorted({c["result"]["store_changed"] for c in dom
                                                   if c["result"]["outcome"] == "failed"})
    for neg in ("as_is", "last"):
        ks = {n: M.order_key(g, negative=neg) for n, g in (("negative(2R,3O)", [(2, "R"), (3, "O")]),
                                                            ("pair(2,1)", [(2, "R"), (1, "R")]))}
        p[f"QO4_negative[{neg}]"] = sorted(ks, key=ks.get)
    return p


def main() -> int:
    inv = run_invariants()
    mut = run_mutants()
    pr = probes()
    ok = all(v is True for v in inv.values()) and all(m["killed_by_owner"] for m in mut.values())
    res = {"model": "0044 stage 1 reference model v2 (package I round 3)", "invariants": inv, "mutants": mut,
           "probes": pr, "verdict": "PASS" if ok else "FAIL"}
    if "--out" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
        out.write_text(json.dumps(res, indent=2, default=str) + "\n")
    for k, v in inv.items():
        print(f"{'ok  ' if v is True else 'FAIL'} {k}: {v if v is not True else ''}")
    for k, v in mut.items():
        print(f"{'KILLED  ' if v['killed_by_owner'] else 'SURVIVED'} {k} -> owner {v['owner']} {v['owner_outcome']}"
              f"{'' if v['mutated_path_reached'] else ' (mutated path NOT reached)'}; by {v['killed_by']}")
    for k, v in pr.items():
        print(f"probe {k}: {v}")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
