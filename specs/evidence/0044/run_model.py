"""Runs the 0044 stage-1 reference model (v3, package I round 4): every invariant on the drafted rules, every declared
mutant, the exhaustive result-domain enumeration (R2-03; v4's admission dimension added), and the probes. Writes
results only where `--out` says.

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


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


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
    bumped = copy.deepcopy(s.edges["p"]); bumped.counters += 3
    M.add_edge(s, bumped)                                  # a harmless mutation through the store's own upsert
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
def _upsert_lifetime(s, edge_id, active, at, reason):
    """A same-id `add_edge` upsert carrying the given lifetime fields (round 3's R3-01 path)."""
    e = copy.deepcopy(s.edges[edge_id])
    e.active, e.invalidated_at, e.reason = active, at, reason
    M.add_edge(s, e)


def inv_era_boundary(rules=R):
    """INV-M13 (R2-01; research C-4 and its residual; v3: R3-01): eligibility is INVENTORY membership, never a clock
    comparison. A pre-upgrade retirement dated 2050 IS eligible; a post-upgrade retirement dated 1990 is NOT; an
    inventoried edge reinstated and then re-retired with an IDENTICAL (invalidated_at, reason) is NOT — whether the
    reinstatement was the reinstate method's or a same-id `add_edge` upsert's (membership ends at WHICHEVER write makes
    the row active again)."""
    s = M.Store()
    fut = E("fut", obj="weight 78"); s.edges["fut"] = fut
    M.supersede_single(s, fut, E("fn", obj="weight 80", vf=2050))                 # pre-upgrade, valid-time 2050
    re = E("re", obj="weight 60"); s.edges["re"] = re
    M.supersede_single(s, re, E("rn", obj="weight 61", vf=5))                     # pre-upgrade, then reinstated ...
    up = E("up", obj="weight 50"); s.edges["up"] = up
    M.supersede_single(s, up, E("un", obj="weight 51", vf=7))                     # pre-upgrade, then UPSERTED active ...
    M.schema_step(s)
    late = E("late", rel="measures", obj="weight 70"); s.edges["late"] = late
    M.supersede_single(s, late, E("ln", obj="weight 71", vf=1990))                # post-upgrade, valid-time 1990
    M.restore_source(s, "re")                                                     # ... reinstated (any reason) ...
    _upsert_lifetime(s, "re", False, 5, "superseded")                            # ... re-retired, the same tuple
    _upsert_lifetime(s, "up", True, None, None)                                  # the upsert reinstatement ...
    _upsert_lifetime(s, "up", False, 7, "superseded")                            # ... re-retired, the same tuple
    run(s)
    return (s.edges["fut"].active and not s.edges["late"].active and not s.edges["re"].active
            and not s.edges["up"].active)


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
    run(s2, op_id="op-r")                     # a restoration is its own operation (v4: op-1 was admitted plan-only)
    complete = M.doctor_data_migration(s2)[0] == "none"
    # 0018am v4 §4b.2 (I25): the digest covers the THREE reclassified declarations only — an unrelated change
    # (`works_as` single → multi, round 3's witness) is admitted; a change to one of the three is refused
    s3 = base(); run(s3, plan_only=True, op_id="plan")
    unrelated = run(s3, custom(works_as={"arity": "multi", "functional": False}), op_id="next")
    related = run(s3, custom(prefers=SINGLE), op_id="other")
    narrow = unrelated["outcome"] == "migrated" and s3.edges["p"].active and related["outcome"] == "registry-changed"
    return (pre_phase and empty and empty_info and refused and same_continues and pre_refused and plan_only
            and incomplete and complete and narrow)


def _freeze(v):
    """A hashable, order-insensitive value of a durable state (dicts and sets compare by content, not insertion
    order). Generic over every field, so a new Store field cannot be left out of `_durable`."""
    if isinstance(v, dict):
        return frozenset((k, _freeze(x)) for k, x in v.items())
    if isinstance(v, (set, frozenset)):
        return frozenset(_freeze(x) for x in v)
    if isinstance(v, (list, tuple)):
        return tuple(_freeze(x) for x in v)
    if isinstance(v, M.Edge):
        return tuple(vars(v).items())                    # every Edge field is immutable
    return v


def _durable(s):
    """The store's durable state: every field but the two counters (0029's txn, the 0008 amendment's act ordinal),
    which a no-op never advances in the model but which are not what `store_changed` reports."""
    return _freeze({k: v for k, v in vars(s).items() if k not in ("txn", "act_counter")})


PRIOR_CALLS = ("none", "same", "other-registry", "other-mode")


def enumerate_results() -> list:
    """R2-03, re-enumerated for 0018am v4: the WHOLE small domain — schema version × attestation × header before
    (none / equal / different) × an EARLIER call under the same op_id (none; the same inputs; another registry; the
    other mode — v4's admission dimension) × plan-only × 0–3 users × every failing subset. Each call's result must be a
    valid carrier (the validating constructor) and a row of the closed table, its `store_changed` must equal whether
    the store's durable state changed, its named failures must be exactly the failing users, and the status read must
    return the operation's CUMULATIVE commits, or `unknown-op` exactly when no call under the id wrote durably.
    Bounded, with the reason: the earlier call runs only on a v16 store (below v16 every call refuses before writing,
    so it cannot change state), and it fails no user (a resume after a FAILED user, the invocation-vs-cumulative split,
    is INV-M25's own check); each mutant re-runs this domain, so its size is the runner's cost."""
    cases = []
    for v16, attested, before, prior, plan_only, n in itertools.product((True, False), (True, False),
                                                                        ("none", "equal", "different"), PRIOR_CALLS,
                                                                        (False, True), range(4)):
        if not v16 and prior != "none":
            continue
        users = [f"u{i}" for i in range(n)]
        prior_fails = [()]
        for pf in prior_fails:
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
                    first = None
                    if prior != "none":
                        reg = custom(measures=SINGLE) if prior == "other-registry" else dict(M.DEFAULT_REGISTRY)
                        mode = (not plan_only) if prior == "other-mode" else plan_only
                        first = M.run_data_migration(s, reg, op_id="op-1", plan_only=mode, fail_users=pf)
                    pre = _durable(s)
                    res = M.run_data_migration(s, dict(M.DEFAULT_REGISTRY), op_id="op-1", plan_only=plan_only,
                                               attested=attested, fail_users=fails)
                    st = M.data_migration_status(s, "op-1")
                    cases.append({"case": (v16, attested, before, prior, list(pf), plan_only, n, list(fails)),
                                  "first": first, "result": res, "changed": _durable(s) != pre, "status": st})
    return cases


def inv_result_totality(rules=R):
    """INV-M15 (R2-03; 0018am v4 I29/I32): over the enumerated domain, every result is a VALID carrier (it passes the
    validating constructor, `plan_written` included) and a row of the closed table; `store_changed` is honest (equal
    to whether durable state changed, including a plan-only commit and an all-failed call that wrote the header);
    named failures equal the failing users; the status read returns the operation's cumulative commits over both calls,
    and `unknown-op` exactly when neither call under the id wrote; and all ten outcomes are reached (a domain that
    never reaches one proves nothing about it)."""
    seen = set()
    for c in enumerate_results():
        r = c["result"]
        try:
            if M.make_result(**r) != r:
                return False
        except M.Refused:
            return False
        want = M.RESULT_ROWS[r["outcome"]]
        if want is not None and r["store_changed"] is not want:
            return False
        if r["store_changed"] != c["changed"]:
            return False
        first = c["first"] or {"store_changed": False, "committed": []}
        if first["store_changed"] or r["store_changed"]:
            if c["status"].get("committed") != sorted(set(first["committed"]) | set(r["committed"])):
                return False
        elif c["status"] != {"outcome": "unknown-op"}:
            return False
        fails = [u for u in c["case"][-1] if u not in first["committed"]]     # a user with a run row is not re-run
        if r["outcome"] in ("migrated", "partial", "failed") and sorted(r["failed"]) != sorted(fails):
            return False
        seen.add(r["outcome"])
    return set(M.RESULT_ROWS) <= seen


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
    bumped = copy.deepcopy(s2.edges["p"]); bumped.counters += 1
    M.add_edge(s2, bumped); M.confirm(s2, "u", "p", cid="k")
    kept = s2.outcomes[("plan-1", "p")]["applicable"]
    s3 = base(); run(s3); M.redact(s3, "p")
    try:
        M.undo(s3, "u", "p", rules); red_refused = False
    except M.Refused:
        red_refused = True
    # v3 (R3-01): a retirement by a same-id upsert ends the episode as the invalidate method's does
    s4 = base(); run(s4)
    _upsert_lifetime(s4, "p", False, 2050, "superseded")
    _upsert_lifetime(s4, "p", True, None, None)
    upsert_ended = s4.outcomes[("plan-1", "p")]["applicable"] is False and "refused" in attempt(M.undo, s4, "u", "p", rules)
    # v3 (§4i v1.5, defensive): the edge row's removal while its outcome is kept ends the episode, so a later insert
    # under the same id — active, as restored — finds `applicable` already cleared: no undo, no doctor exemption
    s5 = base(); run(s5)
    again = copy.deepcopy(s5.edges["p"])
    M.remove_edge(s5, "p"); M.add_edge(s5, again)
    removal_ended = (s5.outcomes[("plan-1", "p")]["applicable"] is False and s5.edges["p"].active
                     and "refused" in attempt(M.undo, s5, "u", "p", rules) and ("info", "n", "p") not in M.doctor_refs(s5))
    return active_again and no_exempt and undo_refused and kept and red_refused and upsert_ended and removal_ended


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
    s2 = base(); run(s2); M.remove_edge(s2, "p")          # the defensive removal (§4g; unreachable at the pin)
    try:
        rows = M.receipt(s2, "u")
        rendered = rows and rows[0]["object"] == "no longer held"
    except KeyError:
        rendered = False
    # v3 (R3-03): the refusal inventory and refusals on the erased user's edges go too, so a recreated user with the
    # same edge ids has no protected historical pair; another user's retained refusal is the control
    s3 = M.Store()
    for i, u in (("rp", "u"), ("ri", "u"), ("wp", "w"), ("wi", "w")):
        s3.edges[i] = E(i, user=u, obj=f"weight {i}")
    s3.refusals += [("rp", "ri", "measures", 1), ("wp", "wi", "measures", 1)]
    M.schema_step(s3)
    M.forget_user(s3, "u")
    for i in ("rp", "ri"):
        s3.edges[i] = E(i, user="u", obj=f"new {i}")
    refusals_gone = M.contested_pairs(s3) == [("wp", "wi")] and s3.refusal_inventory == {(("wp", "wi"), "w")}
    return gone and not_replayed and recreated and bool(rendered) and refusals_gone


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


# ================================================================================ round 4: the round-3 findings
# the lifetime domain of one row: (active, invalidated_at, reason, redacted); None = no persisted row
_LIFE_DOMAIN = [None] + [(a, at, r, d) for a in (True, False) for at in (None, 0, 5)
                         for r in (None, "superseded", "disputed") for d in (False, True)]


def _transition_oracle(prior, new):
    """0044 v1.5 §4f-ii's table and §4i's defensive removal, written from the TEXT, independently of the model's
    `derive_transition`."""
    if prior is None:
        return None                                       # row 1: an insert, a row arriving retired included
    if new is None:
        return "removal"                                  # §4i: the row removed while its outcome is retained
    if new[3] and not prior[3]:
        return "redaction"                                # row 5
    flip = {(False, True): "reinstatement", (True, False): "retirement"}.get((prior[0], new[0]))
    if flip:
        return flip                                       # rows 2 and 3
    if not prior[0] and not new[0] and (prior[1], prior[2]) != (new[1], new[2]):
        return "re-retirement"                            # row 4
    return None                                           # row 6, and an unchanged row


def inv_lifetime_transitions(rules=R):
    """INV-M23 (0044 v1.5 INV-A22, R3-01): every lifetime transition is derived from the persisted prior and the new row
    at the emission choke point, by every writer. The derivation equals §4f-ii's table over the whole lifetime domain
    (a row ARRIVING retired is no transition); round 3's sequence through the same-id `add_edge` upsert — on an
    inventoried row, the upsert reinstatement ends membership and a re-retirement with the identical tuple is not
    restored; on a restored row, the upsert retirement clears `applicable`, a later upsert reinstatement never sets it
    back, and undo and the doctor exemption end — and a NEW row inserted retired changes no outcome or inventory row."""
    table = all(M.derive_transition(p, n) == _transition_oracle(p, n) for p in _LIFE_DOMAIN for n in _LIFE_DOMAIN)
    s = base()
    _upsert_lifetime(s, "p", True, None, None)
    membership_ended = "p" not in s.inventory
    _upsert_lifetime(s, "p", False, 0, "superseded")      # base's exact retirement tuple, re-written
    run(s)
    not_restored = not s.edges["p"].active
    s2 = base(); run(s2)
    _upsert_lifetime(s2, "p", False, 2050, "superseded")
    cleared = s2.outcomes[("plan-1", "p")]["applicable"] is False
    _upsert_lifetime(s2, "p", True, None, None)
    _upsert_lifetime(s2, "p", False, 2050, "superseded")
    ended = (s2.outcomes[("plan-1", "p")]["applicable"] is False and "refused" in attempt(M.undo, s2, "u", "p", rules))
    s3 = base(); run(s3)
    before = (copy.deepcopy(s3.outcomes), dict(s3.inventory))
    fresh = E("fresh", obj="weight 99"); fresh.active, fresh.invalidated_at, fresh.reason = False, 3, "superseded"
    M.add_edge(s3, fresh)
    arriving = (s3.outcomes, s3.inventory) == before
    return table and membership_ended and not_restored and cleared and ended and arriving


def _migrated(origin="store-A"):
    s = M.Store(origin=origin)
    p = E("p", obj="weight 78"); s.edges["p"] = p
    M.supersede_single(s, p, E("n", obj="weight 80", vf=2050))
    M.schema_step(s); run(s)
    return s


def _planned(origin):
    d = M.Store(origin=origin); M.schema_step(d); run(d, plan_only=True, op_id="plan")
    return d


def _refuses(f, *a, **kw):
    """True iff the verb REFUSES (a domain refusal); any other exception propagates (a harness failure, never a kill)."""
    try:
        f(*a, **kw)
        return False
    except M.Refused:
        return True


def inv_outcome_replay(rules=R):
    """INV-M24 (0044 v1.5 INV-A23, R3-02): an outcome's replay is decided by COMPARING canonical projections over the
    staged union. Round 3's negative probe (one field changed under the same uid, beside an unrelated new edge) refuses
    the WHOLE unit; an unchanged file imports again as a no-op in both modes; under user and id remapping too; an ended
    local episode is never revived (held not applicable, arriving applicable: a no-op, the flag stays down, no undo);
    a second hop back into the origin is a no-op although the origin's row holds a store-local `undo_request_ref`; one
    outcome per slot — a second uid on a held slot refuses, and so do two uids for one slot in one unit; two EQUAL
    copies of one uid in a unit are one outcome."""
    a = _migrated(); f = M.export(a, "u")
    uid = f["outcomes"][("plan-1", "p")]["outcome_uid"]
    dst = _planned("store-B"); M.import_file(dst, f, "trusted")
    changed = copy.deepcopy(f)
    changed["outcomes"][("plan-1", "p")]["pre_invalidated_at"] = 1990
    changed["edges"].append(M.Edge("new", "u", "uses_tool", "tool"))
    negative = (_refuses(M.import_file, dst, changed, "trusted") and "new" not in dst.edges
                and dst.outcomes[("plan-1", "p")]["pre_invalidated_at"] == 2050)
    replay = True
    for mode in ("default", "trusted"):
        d = _planned("store-B"); M.import_file(d, f, mode)
        snap = _durable(d)
        rec = M.import_file(d, f, mode)
        replay = replay and _durable(d) == snap and rec["outcomes_replayed"] == [uid]
    rm = {"users": {"u": "v"}, "ids": {"p": "p2", "n": "n2"}}
    d = _planned("store-B"); M.import_file(d, f, "trusted", remap=rm)
    row = d.outcomes.get(("plan-1", "p2"))
    snap = _durable(d)
    M.import_file(d, f, "trusted", remap=rm)
    remapped = (row is not None and row["user"] == "v" and row["successor_evidence"] == ["pointer", ["n2"]]
                and _durable(d) == snap)
    d = _planned("store-B"); M.import_file(d, f, "trusted")
    M.revoke_source(d, "src-a"); M.lift_source(d, "src-a")         # the episode ends; the edges are as exported again
    M.import_file(d, f, "trusted")
    ended = d.outcomes[("plan-1", "p")]["applicable"] is False and "refused" in attempt(M.undo, d, "u", "p", rules)
    a2 = _migrated(); M.undo(a2, "u", "p", rules, correlation_id="c1")
    b = _planned("store-B"); M.import_file(b, M.export(a2, "u"), "default")
    second_hop = not _refuses(M.import_file, a2, M.export(b, "u"), "trusted")
    other = copy.deepcopy(f); other["outcomes"][("plan-1", "p")]["outcome_uid"] = M.canonical_uid("store-Z", "u", "plan-1", "p")
    held_slot = _refuses(M.import_file, dst, other, "trusted")
    twin = copy.deepcopy(f); twin["outcomes"][("plan-1", "p", "dup")] = copy.deepcopy(other["outcomes"][("plan-1", "p")])
    unit_slot = _refuses(M.import_file, _planned("store-C"), twin, "trusted")
    copies = copy.deepcopy(f); copies["outcomes"][("plan-1", "p", "copy")] = copy.deepcopy(f["outcomes"][("plan-1", "p")])
    d = _planned("store-C")
    equal_copies = not _refuses(M.import_file, d, copies, "trusted") and len(d.outcomes) == 1
    return (negative and replay and remapped and ended and second_hop and held_slot and unit_slot and equal_copies
            and _stage_cells(f["outcomes"][("plan-1", "p")]) and _stage_imports(rules))


def _at_stage(row, st, undone_at):
    return dict(row, applicable=(st == "live"), undone_at=(undone_at if st == "undone" else None))


def _stage_oracle(held, arr):
    """§4l v1.5, from the TEXT: equal stages replay; a `live` arrival over a held ending is older evidence (a no-op);
    every other stage difference — an ending over `live`, `ended` over `undone` and the reverse — refuses."""
    return held == arr or (arr == "live" and held in ("ended", "undone"))


def _stage_cells(row):
    """All nine (held × arriving) stage cells through the import's own decision, with DIFFERENT `undone_at` values on
    the two sides (each store's own clock: the value never decides)."""
    return all(M.replay_decision(_at_stage(row, h, 7), _at_stage(row, a, 99)) == _stage_oracle(h, a)
               for h in M.STAGES for a in M.STAGES)


def _stage_imports(rules):
    """The cells an import can reach with record-equal edges (0009 decides the rest first): two stores that each undid
    the episode, at different times, replay; an `ended` arrival over an `undone` held row, the reverse, and an ending
    over a held `live` row each refuse the whole unit."""
    a = _migrated(); b = _planned("store-B"); M.import_file(b, M.export(a, "u"), "trusted")
    M.undo(a, "u", "p", rules)
    for _ in range(10):
        b.begin()                                                # b's clock is elsewhere: the values must differ
    M.undo(b, "u", "p", rules)
    times = a.outcomes[("plan-1", "p")]["undone_at"] != b.outcomes[("plan-1", "p")]["undone_at"]
    both_undone = times and not _refuses(M.import_file, b, M.export(a, "u"), "trusted")
    src = _migrated(); dst = _planned("store-B"); M.import_file(dst, M.export(src, "u"), "trusted")
    M.retire(src, "p", "superseded", at_valid=2050)              # src: ENDED, the edge retired as the pre-state
    M.undo(dst, "u", "p", rules)                                 # dst: UNDONE, the same edge record
    ended_over_undone = _refuses(M.import_file, dst, M.export(src, "u"), "trusted")
    undone_over_ended = _refuses(M.import_file, src, M.export(dst, "u"), "trusted")
    s1 = _migrated(); live = _planned("store-B"); M.import_file(live, M.export(s1, "u"), "trusted")
    M.revoke_source(s1, "src-a"); M.lift_source(s1, "src-a")     # s1: ENDED, its edges as exported
    ending_over_live = _refuses(M.import_file, live, M.export(s1, "u"), "trusted")
    return both_undone and ended_over_undone and undone_over_ended and ending_over_live


def inv_op_admission(rules=R):
    """INV-M25 (0018am v4 I32): an op_id is bound to its inputs digest and mode by a durable admission record holding no
    user content. Equal inputs RESUME (exactly the users with no run row); the status read returns the operation's
    CUMULATIVE commits while a result's `committed` names the invocation's; a changed request under the reused id
    returns `op-id-conflict` and writes nothing; plan-only and restoration never share an id; a call refused before
    any durable write leaves no record (`unknown-op`)."""
    s = M.Store()
    for u in ("u0", "u1"):
        p = E(f"p-{u}", user=u, obj="weight 78"); s.edges[p.id] = p
        M.supersede_single(s, p, E(f"n-{u}", user=u, obj="weight 80"))
    M.schema_step(s)
    r1 = run(s, op_id="op-A", fail_users=("u1",))
    rec = s.migration_ops.get("op-A") or {}
    no_content = set(rec) == {"op_id", "mode", "inputs_digest", "admitted_at"} and rec.get("mode") == "restore"
    r2 = run(s, op_id="op-A")
    st = M.data_migration_status(s, "op-A")
    resumed = (r1["outcome"] == "partial" and r2["outcome"] == "migrated" and r2["committed"] == ["u1"]
               and st.get("committed") == ["u0", "u1"])
    pre = _durable(s)
    r3 = run(s, custom(prefers=SINGLE), op_id="op-A")
    conflict = r3["outcome"] == "op-id-conflict" and _durable(s) == pre
    s2 = base(); run(s2, plan_only=True, op_id="op-P")
    r4 = run(s2, op_id="op-P")
    modes = r4["outcome"] == "op-id-conflict" and not s2.edges["p"].active
    s3 = base(); run(s3, custom(measures=SINGLE), plan_only=True, op_id="x")
    r5 = run(s3, op_id="fresh")
    no_record = r5["outcome"] == "registry-changed" and M.data_migration_status(s3, "fresh") == {"outcome": "unknown-op"}
    # a call that writes nothing writes no record: `complete`, `already-planned`, and all-failed over an existing header
    s4 = base(); run(s4, op_id="first")
    quiet = [run(s4, op_id="c")["outcome"], run(s4, plan_only=True, op_id="ap")["outcome"]]
    s5 = base(); run(s5, plan_only=True, op_id="plan")
    quiet.append(run(s5, op_id="af", fail_users=("u",))["outcome"])
    nothing_written = (quiet == ["complete", "already-planned", "failed"]
                       and all(M.data_migration_status(x, op) == {"outcome": "unknown-op"}
                               for x, op in ((s4, "c"), (s4, "ap"), (s5, "af"))))
    # the record is not per-user: user erasure keeps it, so the id still conflicts afterwards
    M.forget_user(s, "u0"); M.forget_user(s, "u1")
    kept = "op-A" in s.migration_ops and run(s, custom(prefers=SINGLE), op_id="op-A")["outcome"] == "op-id-conflict"
    # an op_id outside the caller grammar is refused at entry: before any read or write, no result constructed
    s6 = base(); pre6 = _durable(s6)
    entry = _refuses(M.run_data_migration, s6, dict(M.DEFAULT_REGISTRY), op_id="bad id!") and _durable(s6) == pre6
    return no_content and resumed and conflict and modes and no_record and nothing_written and kept and entry


def _carrier(outcome, pw=False, c=(), fl=(), op="op-1", sc=None):
    return {"outcome": outcome, "store_changed": (pw or bool(c)) if sc is None else sc, "plan_written": pw,
            "committed": list(c), "failed": list(fl), "op_id": op}


def inv_result_constructor(rules=R):
    """INV-M26 (0018am v4 I29, §4c's rejection matrix): the validating constructor builds every row of the outcome
    table with consistent fields (the positive control), and refuses each row of the matrix: an unlisted outcome
    (round 3's `_result('unlisted', …)`), a missing field (`plan_written`), a dishonest `store_changed`, `failed` and
    `committed` on the wrong rows, a user both committed and failed, `plan_written` on the wrong rows, and an op_id
    outside the caller grammar."""
    good = [_carrier(o) for o in ("requires-schema-step", "preflight-refused", "registry-changed", "op-id-conflict",
                                  "already-planned", "complete")]
    good += [_carrier("planned", pw=True), _carrier("migrated", c=["u"]), _carrier("migrated", pw=True, c=["u"]),
             _carrier("partial", c=["u"], fl=["v"]), _carrier("failed", fl=["v"]), _carrier("failed", pw=True, fl=["v"])]
    builds = all(not _refuses(M.make_result, **g) for g in good) and {g["outcome"] for g in good} == set(M.RESULT_ROWS)
    missing = _carrier("complete"); del missing["plan_written"]
    bad = [_carrier("unlisted"), missing, _carrier("complete", sc=True), _carrier("migrated", c=["u"], fl=["v"]),
           _carrier("partial", c=["u"]), _carrier("complete", c=["u"], sc=True), _carrier("migrated"),
           _carrier("partial", c=["u"], fl=["u"]), _carrier("complete", pw=True), _carrier("planned"),
           _carrier("complete", op="bad id!")]
    refuses = all(_refuses(M.make_result, **b) for b in bad)
    witness = _refuses(M._result, "unlisted", False, ["u"], ["u"], "bad")
    return builds and refuses and witness


def inv_redacted_requests_terminal(rules=R):
    """INV-M27 (0008am v1.3 INV-Q7, the `undo` verb's side, which model II does not represent; brought to 0008 v8 §6g
    at T7, research's stage-1 F1): an edge's redaction replaces the digest of every registry row on it — `undo`
    included — and a retry under such an id returns the terminal `request_redacted`, naming the verb that holds the
    id, which takes precedence over replay AND over the verb check: a request of ANOTHER verb under it gets the same
    terminal and is never admitted (v1.3 had it conflict); a request on an unredacted edge still replays, and the
    same rule holds for `confirm`."""
    s = base(); run(s)
    M.undo(s, "u", "p", rules, correlation_id="undo-request")
    M.confirm(s, "u", "n", cid="conf-request")
    M.redact(s, "p")
    digest_gone = s.registry[("u", "undo-request")]["digest"] == M.MARKER
    held_term = {"terminal": "request_redacted", "held_by": "undo"}
    terminal = attempt(M.undo, s, "u", "p", rules, correlation_id="undo-request") == held_term
    n_conf = len(s.confirmations)
    held = (attempt(M.confirm, s, "u", "p", cid="undo-request") == held_term and len(s.confirmations) == n_conf
            and s.registry[("u", "undo-request")]["verb"] == "undo")
    replays = attempt(M.confirm, s, "u", "n", cid="conf-request") == {"replayed": "conf:n"}
    M.redact(s, "n")
    conf_terminal = (attempt(M.confirm, s, "u", "n", cid="conf-request")
                     == {"terminal": "request_redacted", "held_by": "confirm"})
    return digest_gone and terminal and held and replays and conf_terminal


def inv_undo_is_not_an_act(rules=R):
    """INV-M28 (0008 v7 §6f, the owner's ruling D4 "Undo is not an act row"; added at T7, research's stage-1 Q7): an
    undo takes NO act position (the store-wide counter does not move) while a confirmation takes exactly one."""
    s = base(); run(s)
    a0 = s.act_counter
    M.undo(s, "u", "p", rules, correlation_id="c1")
    undo_kept = s.act_counter == a0
    M.confirm(s, "u", "n", cid="k1")
    return undo_kept and s.act_counter == a0 + 1


def inv_generated_ids(rules=R):
    """INV-M29 (0008 §2c's v6 row and §6c; 0044 §4g; added at T7, research's stage-1 F2): a request without an id
    GENERATES one, which takes a registry row like a supplied one, for both verbs; an id-less undo's outcome row names
    that row in `undo_request_ref`; an already-undone call generates nothing durable (no registry row, no
    transaction: a call that writes nothing holds no id); and a generated id is IN the one shared id space (0008am
    INV-Q1): another verb under it is an integrity conflict naming its holder, and nothing is admitted (research's
    T7 stage-2 S2)."""
    s = base(); run(s)
    n0 = len(s.registry)
    M.undo(s, "u", "p", rules)
    ref = s.outcomes[("plan-1", "p")]["undo_request_ref"]
    undo_row = ref in s.registry and s.registry[ref]["verb"] == "undo" and s.registry[ref]["target"] == "p"
    t, n1 = s.txn, len(s.registry)
    again = attempt(M.undo, s, "u", "p", rules) == {"undone": "p", "already_undone": True}
    quiet = s.txn == t and len(s.registry) == n1
    M.confirm(s, "u", "n")
    conf_row = sum(1 for r in s.registry.values() if r["verb"] == "confirm" and r["target"] == "n") == 1
    n_conf = len(s.confirmations)
    shared = (attempt(M.confirm, s, "u", "n", cid=ref[1]) == {"refused": "integrity conflict: correlation id held by undo"}
              and len(s.confirmations) == n_conf)
    return n1 == n0 + 1 and undo_row and again and quiet and conf_row and shared


# FROZEN at round 4 (2026-10-13): the reviewer ACCEPTED 0044 v1.5 AT THE DESIGN LEVEL — in the verdict's words, "Accept the
# design on the frozen invariant surface below." Frozen scope, quoted: "Freeze **0044 INV-A1–A23**, **0018 amendment I24–I32**
# with accepted I13–I23 preserved, and **0003 INV-O1–O10**. The shared 0008 fold freezes its active **INV-Q1–Q10, including Q4′,
# and INV-I1–I7** as enumerated in v1.9. These names refer to the actual rows and their MODEL/PRODUCT ownership, not a claim that
# all proposed product behavior exists at this pin." This table is model I's half of that ownership (obligations.py maps it).
# THE GOVERNING RULE FORWARD, quoted from the banked verdict (outbox/0044-round4-verdict-verbatim.md, body sha16
# f2dd2dbbd0041425), never paraphrased: "Do not reopen operational keys, the owner's accumulation choice, optional superset
# restoration, plan-only admission, a user-tier floor or expiration of retained refusals. Ordinary implementation defects should
# be fixed against the frozen rules."
# Removing an invariant, weakening an owner's check, or moving a frozen row's ownership is reopening design review, not an edit.
INVARIANTS = {"INV-M1": inv_revocation, "INV-M2": inv_once_per_plan, "INV-M3": inv_successor_evidence,
              "INV-M4": inv_undo_identity, "INV-M5": inv_custom_registry, "INV-M6": inv_doctor,
              "INV-M7": inv_portability, "INV-M8": inv_redaction, "INV-M9": inv_order_key,
              "INV-M10": inv_undo_id_scope, "INV-M11": inv_idless_duplicate, "INV-M12": inv_retained_refusals,
              "INV-M13": inv_era_boundary, "INV-M14": inv_plan_states, "INV-M15": inv_result_totality,
              "INV-M16": inv_applicability, "INV-M17": inv_shared_id_space, "INV-M18": inv_erasure,
              "INV-M19": inv_testimony, "INV-M20": inv_collision, "INV-M21": inv_arity, "INV-M22": inv_canonical_uid,
              "INV-M23": inv_lifetime_transitions, "INV-M24": inv_outcome_replay, "INV-M25": inv_op_admission,
              "INV-M26": inv_result_constructor, "INV-M27": inv_redacted_requests_terminal,
              "INV-M28": inv_undo_is_not_an_act, "INV-M29": inv_generated_ids,   # added at T7 (disclosed)
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
    """C-4's residual: the reinstatement transition is derived but no longer ends inventory membership."""
    def apply_transition(s, edge_id, transition):
        if transition == "reinstatement":
            return
        return orig(s, edge_id, transition)
    return apply_transition


def _kind_gated(effect, kind_needed):
    """Round 3's binding: the transition's EFFECT applied only when the writer is the named method (its site kind), so
    a same-id upsert, which journals `mutated`, passes unseen. `effect` is the transition the gate restricts."""
    def make(orig):
        def journal_edge_write(s, edge_id, prior, *, kind=None, reason=None, t=None):
            saved = M.apply_transition

            def gated(s2, eid, transition):
                if transition in effect and kind != kind_needed:
                    return None
                return saved(s2, eid, transition)
            M.apply_transition = gated
            try:
                return orig(s, edge_id, prior, kind=kind, reason=reason, t=t)
            finally:
                M.apply_transition = saved
        return journal_edge_write
    return make


def _transition_from_kind(orig):
    """Infer the transition from the journal kind (`invalidated` → retirement, `reinstated` → reinstatement,
    `redacted` → redaction): a changed same-id upsert journals `mutated`, so its transition is hidden."""
    def journal_edge_write(s, edge_id, prior, *, kind=None, reason=None, t=None):
        new = M._snap(s.edges.get(edge_id))
        M.apply_transition(s, edge_id, {"invalidated": "retirement", "reinstated": "reinstatement",
                                        "redacted": "redaction"}.get(kind))
        if prior is not None and prior == new and kind != "redacted":
            return None
        t = t if t is not None else s.txn
        kind = "created" if prior is None else (kind or "mutated")
        if kind == "reinstated":
            M.journal_reinstated(s, edge_id, reason, t)
        else:
            s.journal.append((kind, edge_id, t, reason))
        return kind
    return journal_edge_write


def _upsert_bypasses_choke_point(orig):
    """Hook only the invalidate and reinstate methods: `add_edge` writes the row and journals, but derives no
    transition (round 3's shipped shape)."""
    def add_edge(s, edge):
        t = s.begin()
        prior = s.edges.get(edge.id)
        s.edges[edge.id] = copy.deepcopy(edge)
        s.journal.append(("created" if prior is None else "mutated", edge.id, t, None))
        return "mutated"
    return add_edge


def _inactive_insert_is_retirement(orig):
    def derive_transition(prior, new):
        if prior is None and new is not None and not new[0]:
            return "retirement"
        return orig(prior, new)
    return derive_transition


def _uid_alone_replays(orig):
    return lambda o: json.dumps(o.get("outcome_uid"))          # equal uid ⇒ "equal projection" (round 3's witness)


def _projection_with_request_ref(orig):
    def outcome_projection(o):
        return json.dumps({**json.loads(orig(o), object_pairs_hook=_strict_pairs), "undo_request_ref": o.get("undo_request_ref")}, sort_keys=True,
                          default=list)
    return outcome_projection


def _arrival_revives(orig):
    def episode_replay(held, arr):
        r = orig(held, arr)
        if r:
            held["applicable"], held["undone_at"] = arr["applicable"], arr["undone_at"]
        return r
    return episode_replay


def _projection_with_undone_value(orig):
    def outcome_projection(o):
        return json.dumps({**json.loads(orig(o), object_pairs_hook=_strict_pairs), "undone_at": o.get("undone_at")}, sort_keys=True, default=list)
    return outcome_projection


def _endings_as_one(orig):
    """v1.4's wording: `ended` read as an earlier stage of `undone`, so an ended arrival over an undone held row
    replays."""
    def episode_replay(held, arr):
        if M.stage(held) == "undone" and M.stage(arr) == "ended":
            return M.outcome_projection({**arr, "applicable": held["applicable"], "undone_at": held["undone_at"]}) \
                == M.outcome_projection(held)
        return orig(held, arr)
    return episode_replay


def _removal_keeps_applicable(orig):
    def apply_transition(s, edge_id, transition):
        if transition == "removal":
            return None
        return orig(s, edge_id, transition)
    return apply_transition


def _install_last_invocation_status():
    """Status returns only the LAST invocation's commits (the mutant tracks invocations itself; the model does not)."""
    last = {}
    orig_run, orig_st = _O["run_data_migration"], _O["data_migration_status"]

    def run_data_migration(s, registry, **kw):
        r = orig_run(s, registry, **kw)
        last[(id(s), r["op_id"])] = list(r["committed"])
        return r

    def data_migration_status(s, op_id):
        st = orig_st(s, op_id)
        if "committed" in st and (id(s), op_id) in last:
            st = dict(st, committed=sorted(last[(id(s), op_id)]))
        return st
    M.run_data_migration, M.data_migration_status = run_data_migration, data_migration_status


def _carrier_without_plan_written(orig):
    def run_data_migration(s, registry, **kw):
        r = orig(s, registry, **kw)
        r.pop("plan_written", None)
        return r
    return run_data_migration


def _undo_digest_kept(orig):
    """The 0044 review's witness: a redaction replaces the digests of `confirm` requests only; an undo's survives, and
    its retained result reference replays."""
    def redact_request_digests(s, edge_id):
        for rec in s.registry.values():
            if rec["target"] == edge_id and rec["verb"] == "confirm":
                rec["digest"] = M.MARKER
    return redact_request_digests


def _no_terminal_rule(orig):
    def _replay(s, user, cid, verb, digest):
        if cid is None:
            return None
        rec = s.registry.get((user, cid))
        if rec is None:
            return None
        if rec["verb"] == verb and rec["digest"] == digest:
            return {"replayed": rec["result_ref"]}
        raise M.Refused(f"integrity conflict: correlation id held by {rec['verb']}")
    return _replay


def _terminal_own_verb_only(orig):
    """The SUPERSEDED rule (0008am v1.3, model I before T7): the terminal only for the caller's own verb, so a
    request of another verb under a redacted id reads as a conflict instead of `request_redacted`."""
    def _replay(s, user, cid, verb, digest):
        if cid is None:
            return None
        rec = s.registry.get((user, cid))
        if rec is None:
            return None
        if rec["verb"] == verb and rec["digest"] == M.MARKER:
            return {"terminal": "request_redacted", "held_by": rec["verb"]}
        if rec["verb"] == verb and rec["digest"] == digest:
            return {"replayed": rec["result_ref"]}
        raise M.Refused(f"integrity conflict: correlation id held by {rec['verb']}")
    return _replay


def _undo_takes_an_act_position(orig):
    """The SUPERSEDED rule (model I before T7, pre-D4): every registry write advanced the act counter, undo's too."""
    def _register(s, user, cid, verb, digest, result_ref, target):
        r = orig(s, user, cid, verb, digest, result_ref, target)
        if verb == "undo":
            s.act_counter += 1
        return s.act_counter
    return _register


def _install_no_generated_ids():
    """The SUPERSEDED rule (model I before T7, pre-F2): an omitted id stays omitted and takes no registry row."""
    orig_reg = _O["_register"]

    def _register(s, user, cid, verb, digest, result_ref, target):
        if cid is None:
            if verb in M.ACT_VERBS:
                s.act_counter += 1
            return s.act_counter
        return orig_reg(s, user, cid, verb, digest, result_ref, target)
    M._generated_id = lambda verb, t: None
    M._register = _register


def _generated_ids_per_verb(orig):
    """A generated id checked by its own verb only, outside the shared id space (0008am INV-Q1): another verb under it
    is admitted as if the id were free."""
    def _replay(s, user, cid, verb, digest):
        rec = s.registry.get((user, cid)) if cid is not None else None
        if rec is not None and cid.startswith("auto-") and rec["verb"] != verb:
            return None
        return orig(s, user, cid, verb, digest)
    return _replay


def _header_only_when_nonempty(orig):
    """Round 2's design, well-formed: the call runs, but an EMPTY plan leaves no durable trace afterwards."""
    def run_data_migration(s, registry, **kw):
        r = orig(s, registry, **kw)
        if s.header is not None and not s.plan:
            s.header = None
        return r
    return run_data_migration


def _no_digest_check(orig):
    def write_plan(s, registry, op_id, admission=None):
        if s.header is not None:
            s.header = None; s.plan.clear()                  # re-plan whatever the stored digest
        return orig(s, registry, op_id, admission)
    return write_plan


def _import_before_plan_silent(orig):
    def import_file(s, f, mode, op_id="op-import", remap=None):
        if f["format"] == "pre" and s.header is None:
            s.header = {"plan_id": "plan-0", "registry_digest": "", "op_id": op_id, "written_txn": s.txn}
            try:
                return orig(s, f, mode, op_id, remap)
            finally:
                s.header = None
        return orig(s, f, mode, op_id, remap)
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
                 "replaced_by": "unknown", "undone": o["undone_at"] is not None}
                for (pid, eid), o in sorted(s.outcomes.items()) if o["user"] == user]
    return receipt


def _trust_from_mode(orig):
    def import_file(s, f, mode, op_id="op-import", remap=None):
        rec = orig(s, f, mode, op_id, remap)
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
    def import_file(s, f, mode, op_id="op-import", remap=None):
        f2 = copy.deepcopy(f)
        for e in f2["edges"]:
            e.active = True                                   # the validation's inputs neutralised: nothing reads as bad
        f2["outcomes"] = {k: v for k, v in f2["outcomes"].items()
                          if k[1] in {e.id for e in f2["edges"]} and k[0] == "plan-1"}
        return orig(s, f2, mode, op_id, remap)
    return import_file


def _skip_every_collision(orig):
    def import_file(s, f, mode, op_id="op-import", remap=None):
        f2 = copy.deepcopy(f)
        f2["edges"] = [e for e in f2["edges"] if e.id not in s.edges]
        return orig(s, f2, mode, op_id, remap)
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
    def import_file(s, f, mode, op_id="op-import", remap=None):
        rec = orig(s, f, mode, op_id, remap)
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
    "a reinstatement keeps inventory membership (C-4 residual)": ("INV-M13", _wrap("apply_transition", _reinstate_keeps_membership)),
    "end membership only in the reinstate method (round 3's upsert reinstatement keeps it)": ("INV-M13", _wrap("journal_edge_write", _kind_gated(("reinstatement",), "reinstated"))),
    "an empty plan writes no header (R2-02)": ("INV-M14", _wrap("run_data_migration", _header_only_when_nonempty)),
    "a later registry re-plans, no digest check (R2-02)": ("INV-M14", _wrap("write_plan", _no_digest_check)),
    "a pre-format import before any plan converts silently (Q9)": ("INV-M14", _wrap("import_file", _import_before_plan_silent)),
    "doctor's phase from relation rows, not the header (I30)": ("INV-M14", _wrap("doctor_data_migration", _doctor_from_rows)),
    "store_changed only when a user committed (R2-03)": ("INV-M15", _wrap("run_data_migration", _changed_only_on_commit)),
    "no row for all-failed: reported complete (R2-03)": ("INV-M15", _wrap("run_data_migration", _no_failed_row)),
    "applicability = the current active bit (R2-04)": ("INV-M16", _wrap("undo", _applicable_is_active_bit)),
    "applicability cleared only by `superseded` retirements (R2-04)": ("INV-M16", _wrap("retire", _clear_only_on_superseded)),
    "redaction keeps applicability (C-6)": ("INV-M16", _wrap("redact", _redaction_keeps_applicable)),
    "clear the flag only in the invalidate method (round 3's upsert re-retirement keeps it)": ("INV-M16", _wrap("journal_edge_write", _kind_gated(("retirement", "re-retirement"), "invalidated"))),
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
    "hook only the invalidate and reinstate methods: the upsert derives nothing (R3-01)": ("INV-M23", _wrap("add_edge", _upsert_bypasses_choke_point)),
    "infer the transition from the journal kind: `mutated` hides it (R3-01)": ("INV-M23", _wrap("journal_edge_write", _transition_from_kind)),
    "treat an inactive insert as a retirement (R3-01)": ("INV-M23", _wrap("derive_transition", _inactive_insert_is_retirement)),
    "equal outcome_uid alone admits (round 3's changed-outcome witness)": ("INV-M24", _wrap("outcome_projection", _uid_alone_replays)),
    "replace the slot's row on a different uid (R3-02)": ("INV-M24", _set("slot_taken", lambda staged, row: False)),
    "an arriving applicable copy sets applicable again (R3-02)": ("INV-M24", _wrap("episode_replay", _arrival_revives)),
    "compare undone_at by value: two stores that each undid the episode refuse (§4l v1.5)": ("INV-M24", _wrap("outcome_projection", _projection_with_undone_value)),
    "an ended arrival over an undone held row as an earlier stage: two endings read as one (§4l v1.5)": ("INV-M24", _wrap("episode_replay", _endings_as_one)),
    "the edge row's removal keeps applicable (§4i v1.5)": ("INV-M16", _wrap("apply_transition", _removal_keeps_applicable)),
    "compare undo_request_ref: a second hop conflicts (R3-02)": ("INV-M24", _wrap("outcome_projection", _projection_with_request_ref)),
    "grammar-only idempotency: a changed request under a reused id runs (I32)": ("INV-M25", _set("same_operation", lambda held, adm: True)),
    "one id admitted for plan-only then for restoration: the digest ignores the mode (I32)": ("INV-M25", _set("inputs_digest", lambda canon, mode: M.canonical_uid(M.plan_input_digest(canon)))),
    "status returns only the last invocation's commits (I32)": ("INV-M25", _install_last_invocation_status),
    "an unlisted carrier constructs (round 3's `_result('unlisted', …)`, I29)": ("INV-M26", _set("make_result", lambda **f: dict(f))),
    "the carrier omits plan_written (I29)": ("INV-M15", _wrap("run_data_migration", _carrier_without_plan_written)),
    "hash the whole registry: an unrelated declaration trips registry-changed (I25)": ("INV-M14", _set("plan_input_digest", lambda canon: M.registry_digest(canon))),
    "keep an undo's digest after redaction and replay its result_ref (0008am INV-Q7)": ("INV-M27", _wrap("redact_request_digests", _undo_digest_kept)),
    "the terminal rule omitted: a redacted retry reads as a conflict (0008am INV-Q7)": ("INV-M27", _wrap("_replay", _no_terminal_rule)),
    # added at T7 (disclosed): each is the rule model I itself carried before research's T7 stage-1 read
    "the terminal for the caller's own verb only: another verb under a redacted id conflicts (0008am v1.3; 0008 v8 §6g)": ("INV-M27", _wrap("_replay", _terminal_own_verb_only)),
    "undo takes an act position (pre-D4; 0008 v7 §6f)": ("INV-M28", _wrap("_register", _undo_takes_an_act_position)),
    "an omitted id is not generated and takes no registry row (pre-F2; 0008 §6c)": ("INV-M29", _install_no_generated_ids),
    "a generated id is checked by its own verb only, outside the shared id space (0008am INV-Q1; stage-2 S2)": ("INV-M29", _wrap("_replay", _generated_ids_per_verb)),
    "erasure keeps the refusal inventory (R3-03)": ("INV-M18", _wrap("forget_user", lambda o: (lambda s, user: (lambda keep, keep2: (o(s, user), setattr(s, "refusal_inventory", keep), setattr(s, "refusals", keep2)))(set(s.refusal_inventory), list(s.refusals))))),
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


def run_mutant(name: str, others: bool = True) -> dict:
    """One mutant installed, then judged. A KILL is semantic: the owner RETURNS False and the mutated function was
    CALLED while it ran (model II's rule; R2-08). `others`: also run every invariant under it (`killed_by`)."""
    owner, install = MUTANTS[name]
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
        res = run_invariants() if others else {}
    finally:
        for k, v in _O.items():
            setattr(M, k, v)
    killed = sorted(k for k, v in res.items() if v is not True)
    return {"owner": owner, "owner_outcome": owner_outcome, "mutated_path_reached": reached,
            "killed_by": killed, "killed_by_owner": owner_outcome == "failed" and reached}


def run_mutants() -> dict:
    return {name: run_mutant(name) for name in MUTANTS}


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
    # v1.5 as first issued named "derive after the unchanged-bytes return" under INV-A22; it is EQUIVALENT (an unchanged
    # row has no transition: derive(x, x) is None over the whole domain) and the re-issue dropped it. Kept as a probe
    # that claims nothing, with the invariants run under it.
    p["equivalent: derive after the unchanged-bytes return"] = {
        "derive(x, x) is None over the lifetime domain": all(M.derive_transition(x, x) is None
                                                             for x in _LIFE_DOMAIN if x is not None),
        "invariants failing under it": _under(_wrap("journal_edge_write", _derive_after_return))}
    # INV-A22's "treat an inactive insert as a retirement" is killed at the derivation's table (INV-M23); this records
    # which OTHER invariants see an effect of it (an outcome can only exist for a held row, so none is expected)
    p["inactive insert as retirement: invariants failing besides INV-M23"] = [
        k for k in _under(_wrap("derive_transition", _inactive_insert_is_retirement)) if k != "INV-M23"]
    # §4l v1.5 compares the STAGE, never `undone_at`'s value (each store's own clock): two stores that each undid the
    # same episode, at different times, compare equal, and the later import of one into the other is a replay.
    a = _migrated(); b = _planned("store-B"); M.import_file(b, M.export(a, "u"), "trusted")
    M.undo(a, "u", "p")
    for _ in range(10):
        b.begin()
    M.undo(b, "u", "p")
    p["undone_at values in the two stores"] = [a.outcomes[("plan-1", "p")]["undone_at"], b.outcomes[("plan-1", "p")]["undone_at"]]
    p["undone_at compared across stores: both undo, then import a into b"] = (
        "refused" if _refuses(M.import_file, b, M.export(a, "u"), "trusted") else "admitted")
    return p


def _derive_after_return(orig):
    def journal_edge_write(s, edge_id, prior, *, kind=None, reason=None, t=None):
        new = M._snap(s.edges.get(edge_id))
        if prior is not None and prior == new and kind != "redacted":
            return None                                   # the return FIRST ...
        M.apply_transition(s, edge_id, M.derive_transition(M._life(prior), M._life(new)))   # ... then the derivation
        t = t if t is not None else s.txn
        kind = "created" if prior is None else (kind or "mutated")
        if kind == "reinstated":
            M.journal_reinstated(s, edge_id, reason, t)
        else:
            s.journal.append((kind, edge_id, t, reason))
        return kind
    return journal_edge_write


def _under(install) -> list:
    """The invariants that fail with `install` in place (a probe; nothing here is a claimed kill)."""
    install()
    try:
        return sorted(k for k, v in run_invariants().items() if v is not True)
    finally:
        for k, v in _O.items():
            setattr(M, k, v)


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
