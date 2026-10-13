"""Reference model for 0044 stage 1 (accumulation) — v2, for package I's round 3.

Encodes 0044 v1.4, the 0018 amendment v3 and the 0003 amendment v1.4 as research drafts them, plus the two shared
constructions of the 0008 amendment (dev-handoff/round3-I-II/CONSTRUCTIONS.md v2): import identity and the act ordinal.
Every rule is one function here, named by its section, so a reader can hold the two side by side.

A MODEL, not product code: it imports nothing from `veracium`. Product tests bind the same properties to shipped code at
the implementation gate (R1-10's split, kept). What it adds over v1, each answering a round-2 finding:
  * TWO TIME DOMAINS, never one clock (R2-01): `Edge.invalidated_at` and `valid_from` are VALID time (any value, future or
    past); `Store.txn` is TRANSACTION time (the model of 0029's per-user txn); `Store.act_counter` is the store-wide act
    ordinal (the 0008 amendment's `act_seq`). The obligation map (obligations.py) types every field and refuses a
    comparison across domains.
  * the schema step writes an INVENTORY of retirements and refusals (R2-01, research C-4/C-5): eligibility is membership,
    never a time comparison;
  * a plan HEADER persisted even when empty, admission by registry digest, a plan-only mode (R2-02, Q9);
  * a TOTAL result carrier over an enumerated schedule domain, with operation discovery after an unknown return (R2-03);
  * the phased `data-migration` diagnostic (I30);
  * arity admission, `multi` (no supersession; reinforcement/absorption only), the dual carrier `functional` (R2-08);
  * the restoration's `applicable` marker, cleared terminally by retirement, redaction and erasure (R2-04, C-6);
  * the 0008 amendment's request registry: confirm and undo share one id space, read before live state (R2-04);
  * user erasure over every new carrier (R2-07);
  * portable outcomes under the act origin matrix — proof vs testimony, never upgraded (R2-05);
  * 0009's collision rule kept: record-equal skips, differing refuses the whole import (R2-06).
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field

MARKER = "\x00redacted\x00"
PLAN_RELATIONS = ("measures", "prefers", "health_state")
OTHER_DEFAULTS = ("works_as", "located_at", "deadline", "scope")
# the v16 defaults, canonical: (arity, functional) — the dual carrier agrees in every default
DEFAULT_REGISTRY = {**{r: {"arity": "multi", "functional": False} for r in PLAN_RELATIONS},
                    **{r: {"arity": "single", "functional": True} for r in OTHER_DEFAULTS}}
ARITIES = ("single", "multi")
RESERVED_ARITIES = ("keyed",)
ORIGINS = ("local", "restored", "imported")
PROOF = ("local", "restored")


class Refused(Exception):
    pass


class Crash(Exception):
    pass


# ----------------------------------------------------------------------------------------------- the state
@dataclass
class Edge:
    id: str
    user: str
    relation: str
    obj: str
    source: str = "src-a"
    active: bool = True
    valid_from: int = 0                 # VALID time
    invalidated_at: int | None = None   # VALID time — shipped supersession writes the incoming's valid_from here
    reason: str | None = None
    supersedes: str | None = None
    counters: int = 0
    basis: tuple = ()                   # contribution-derived sources (0022)
    redacted: bool = False              # 0041: content replaced and attested


@dataclass
class Store:
    origin: str = "store-A"             # 0006 local_origin(): durable, minted once
    edges: dict = field(default_factory=dict)
    txn: int = 0                        # TRANSACTION time: 0029's txn (one clock per write transaction)
    act_counter: int = 0                # the 0008 amendment's store-wide act ordinal (research C-2: never reset)
    schema_v16: bool = False
    revoked: set = field(default_factory=set)
    refusals: list = field(default_factory=list)          # (prior, incoming, relation, written_txn)
    inventory: dict = field(default_factory=dict)         # edge_id -> (user, pre_invalidated_at, pre_reason)
    refusal_inventory: set = field(default_factory=set)   # (prior, incoming) rows existing at the step
    header: dict | None = None                            # {plan_id, registry_digest, op_id, written_txn}
    plan: dict = field(default_factory=dict)              # relation -> plan_id (the header's relation rows)
    runs: dict = field(default_factory=dict)              # (plan_id, user) -> {op_id, txn}
    outcomes: dict = field(default_factory=dict)          # (plan_id, edge_id) -> row (see restore_row)
    registry: dict = field(default_factory=dict)          # (user, cid) -> {verb, digest, result_ref, target}
    confirmations: list = field(default_factory=list)     # (user, edge_id, cid) — 0008's verb, for the shared id space
    journal: list = field(default_factory=list)           # (kind, edge_id, txn, reason) — store-local, never exported

    def begin(self) -> int:
        self.txn += 1
        return self.txn


@dataclass
class Rules:
    """Kept for the probes: the alternatives the round-2 model executed. Defaults = the v1.4 rules."""
    undo_without_id_duplicate: str = "replay_state"


# ----------------------------------------------------------------------------------------------- canonical identity
def canonical_uid(*parts) -> str:
    """research C-3: a JSON array of strings, never a separator join — so ("a","b:c") and ("a:b","c") differ."""
    return hashlib.sha256(json.dumps([str(p) for p in parts], ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def registry_digest(reg: dict) -> str:
    return hashlib.sha256(json.dumps(reg, sort_keys=True).encode()).hexdigest()[:16]


# ----------------------------------------------------------------------------------------------- §4a arity admission
def admit_registry(reg: dict) -> dict:
    """0044 §4a + the dual carrier: `keyed` is reserved and refused; `functional` alone maps (True ≡ single, False ≡
    multi); both present must agree; an unknown arity is refused. Returns the canonical registry."""
    out = {}
    for rel, d in reg.items():
        a, f = d.get("arity"), d.get("functional")
        if a in RESERVED_ARITIES:
            raise Refused(f"{rel}: arity {a!r} is reserved (stage 1)")
        if a is not None and a not in ARITIES:
            raise Refused(f"{rel}: unknown arity {a!r}")
        if a is None and f is None:
            raise Refused(f"{rel}: no arity carrier")
        mapped = None if f is None else ("single" if f else "multi")
        if a is not None and mapped is not None and a != mapped:
            raise Refused(f"{rel}: arity {a!r} disagrees with functional={f!r}")
        arity = a or mapped
        out[rel] = {"arity": arity, "functional": arity == "single"}
    return out


def _key(obj: str) -> str:
    return " ".join(obj.lower().split())


def write_value(s: Store, incoming: Edge, reg: dict) -> str:
    """§3a/§4b: one write. `single` — a differing value supersedes the active prior (the shipped graph path: the prior's
    invalidated_at = the INCOMING's valid_from, a valid-time value). `multi` — a differing value never supersedes; a value
    whose key contains, or is contained in, an active value's key is absorbed (today's behaviour, residual stated)."""
    arity = admit_registry(reg)[incoming.relation]["arity"]
    t = s.begin()
    priors = [e for e in s.edges.values() if e.active and e.user == incoming.user
              and e.relation == incoming.relation and e.id != incoming.id]
    for p in priors:
        if _key(p.obj) == _key(incoming.obj) or _key(p.obj) in _key(incoming.obj) or _key(incoming.obj) in _key(p.obj):
            return "absorbed_duplicate"
    if arity == "single":
        for p in priors:
            p.active, p.invalidated_at, p.reason = False, incoming.valid_from, "superseded"
            s.journal.append(("invalidated", p.id, t, "superseded"))
            if incoming.supersedes is None:
                incoming.supersedes = p.id
    s.edges[incoming.id] = incoming
    s.journal.append(("created", incoming.id, t, None))
    return "superseded" if arity == "single" and priors else "added"


def supersede_single(s: Store, prior: Edge, incoming: Edge):
    """The pre-upgrade `single` path, explicitly (the stored rows the restoration acts on)."""
    t = s.begin()
    prior.active, prior.invalidated_at, prior.reason = False, incoming.valid_from, "superseded"
    if incoming.supersedes is None:
        incoming.supersedes = prior.id
    s.edges[incoming.id] = incoming
    s.journal.append(("invalidated", prior.id, t, "superseded"))


def retire(s: Store, edge_id: str, reason: str, at_valid: int = 0):
    """THE retirement choke point (F4b: `_invalidate_edge_row`): every retirement passes here, and it clears every
    applicable restoration of the edge in the same transaction (§4i, construction §2c)."""
    t = s.begin()
    e = s.edges[edge_id]
    e.active, e.invalidated_at, e.reason = False, at_valid, reason
    _clear_applicable(s, edge_id)
    s.journal.append(("invalidated", edge_id, t, reason))


def _clear_applicable(s: Store, edge_id: str):
    for (pid, eid), o in s.outcomes.items():
        if eid == edge_id:
            o["applicable"] = False


def redact(s: Store, edge_id: str):
    """0041: content REPLACED and attested; a journaled `redacted` write that does NOT retire (research C-6): it clears
    `applicable` itself — redaction is a terminal event for the restoration."""
    t = s.begin()
    e = s.edges[edge_id]
    e.relation, e.obj, e.redacted = MARKER, MARKER, True
    _clear_applicable(s, edge_id)
    s.journal.append(("redacted", edge_id, t, None))


def would_be_revoked(s: Store, e: Edge) -> bool:
    """§4f(3): 0022's sweep predicate — the edge's source or any contribution-basis source is in the standing set."""
    return e.source in s.revoked or any(b in s.revoked for b in e.basis)


def revoke_source(s: Store, source: str):
    s.revoked.add(source)
    for e in list(s.edges.values()):
        if e.active and would_be_revoked(s, e):
            retire(s, e.id, "revoked_source")


def lift_source(s: Store, source: str):
    """0022's reinstate verb: reactivates ONLY rows it retired. It does not restore `applicable` (construction §2c)."""
    s.revoked.discard(source)
    for e in s.edges.values():
        if not e.active and e.reason == "revoked_source" and not would_be_revoked(s, e):
            t = s.begin()
            e.active, e.invalidated_at, e.reason = True, None, None
            journal_reinstated(s, e.id, "source_restored", t)


# ----------------------------------------------------------------------------------------------- the v16 schema step
def schema_step(s: Store):
    """0018am's v16 step, ONE transaction: the inventory of the old-policy population (research C-4: the retirement,
    not only the edge) and of the refusals existing now (C-5). No clock is compared, now or later."""
    s.begin()
    for e in s.edges.values():
        if e.relation in PLAN_RELATIONS and not e.active and e.reason == "superseded":
            s.inventory[e.id] = (e.user, e.invalidated_at, e.reason)
    for prior, incoming, rel, _t in s.refusals:
        if rel in PLAN_RELATIONS:
            s.refusal_inventory.add((prior, incoming))
    s.schema_v16 = True


# ----------------------------------------------------------------------------------------------- §4e the plan
def write_plan(s: Store, registry: dict, op_id: str) -> str:
    """§4e: ONE write transaction. The header is written even for an empty relation set; exactly one header exists;
    a caller that finds one compares digests (equal → continue, nothing written; different → registry-changed)."""
    canon = admit_registry(registry)
    dig = registry_digest(canon)
    if s.header is not None:
        if s.header["registry_digest"] != dig:
            raise Refused("registry-changed")
        return "existing"
    t = s.begin()
    s.header = {"plan_id": "plan-1", "registry_digest": dig, "op_id": op_id, "written_txn": t}
    for rel in PLAN_RELATIONS:
        if canon.get(rel) == DEFAULT_REGISTRY[rel]:
            s.plan[rel] = "plan-1"
    return "written"


def plan_state(s: Store) -> str:
    if s.header is None:
        return "uninitialized"
    return "initialized-nonempty" if s.plan else "initialized-empty"


# ----------------------------------------------------------------------------------------------- §4f eligibility
def consider(s: Store, e: Edge, imported: bool = False) -> str | None:
    """§4f. LOCAL rows: eligible iff INVENTORIED and the current retirement EQUALS the inventoried one (C-4) — never a
    time comparison (R2-01). Imported pre-format rows: retired under `single` by construction (F5), no inventory read."""
    pid = s.plan.get(e.relation)
    if not pid or e.active or e.reason != "superseded":
        return None
    if not imported:
        inv = s.inventory.get(e.id)
        if inv is None or inv != (e.user, e.invalidated_at, e.reason):
            return None
    if (pid, e.id) in s.outcomes:
        return None                                       # (4) once per plan, ever
    if e.redacted or MARKER in (e.relation, e.obj):
        return None                                       # (2) tombstones are never considered
    if would_be_revoked(s, e):
        return "withheld_revoked"                         # (3)
    return "restored"


def restore_row(s: Store, e: Edge, out: str, op_id: str, origin: str = "local") -> dict:
    pid = s.plan[e.relation]
    succ = sorted(x.id for x in s.edges.values() if x.supersedes == e.id)
    return {"user": e.user, "outcome": out, "pre_invalidated_at": e.invalidated_at, "pre_reason": e.reason,
            "successor_evidence": ("pointer", succ) if succ else ("none", []), "undone": False, "op_id": op_id,
            "origin": origin, "applicable": out == "restored",
            "outcome_uid": canonical_uid(s.origin, e.user, pid, e.id)}


# ----------------------------------------------------------------------------------------------- §4h the operation
def migrate_user(s: Store, user: str, op_id: str, fail: bool = False, crash_at: str | None = None):
    """The per-user phase, ONE transaction: work on a copy, swap it in at commit."""
    tx = copy.deepcopy(s)
    pid = tx.header["plan_id"]
    if (pid, user) in tx.runs:
        return "skipped"
    t = tx.begin()
    for e in sorted(tx.edges.values(), key=lambda x: x.id):
        if e.user != user:
            continue
        out = consider(tx, e)
        if out is None:
            continue
        tx.outcomes[(pid, e.id)] = restore_row(tx, e, out, op_id)
        if out == "restored":
            e.active, e.invalidated_at, e.reason = True, None, None
            journal_reinstated(tx, e.id, "arity_reclassified", t)
        if crash_at == "mid_user":
            raise Crash("before commit")
    if fail:
        raise Refused(f"user {user}: transaction failed")
    tx.runs[(pid, user)] = {"op_id": op_id, "txn": t}
    s.__dict__.update(tx.__dict__)                        # COMMIT
    if crash_at == "after_commit":
        raise Crash("after commit, before delivery")
    return "committed"


RESULT_ROWS = {
    # outcome: store_changed — the closed table (0018am v3 §4c as dev's enumeration defines it; research checks the prose)
    "requires-schema-step": False,
    "preflight-refused": False,
    "registry-changed": False,
    "planned": True,            # this call wrote the header and restored nothing (plan-only, or a full call with no users)
    "already-planned": False,   # plan-only, an equal header existed
    "complete": False,          # full call: every user already had a run row; nothing written
    "migrated": True,           # ≥1 user committed, none failed
    "partial": True,            # ≥1 committed and ≥1 failed
    "failed": None,             # 0 committed, ≥1 failed: store_changed = whether THIS call wrote the header
}


def run_data_migration(s: Store, registry: dict, *, op_id: str = "op-1", plan_only: bool = False,
                       attested: bool = True, fail_users=(), crash_user=None, crash_at=None) -> dict:
    """0018am v3 §4b. Returns the total result carrier: outcome, store_changed, plan_written, committed, failed,
    op_id. Each user phase is its own transaction; a failing user is named and the call continues."""
    if not attested:
        return _result("preflight-refused", False, [], [], op_id)
    if not s.schema_v16:
        return _result("requires-schema-step", False, [], [], op_id)
    try:
        w = write_plan(s, registry, op_id)
    except Refused as x:
        if "registry-changed" in str(x):
            return _result("registry-changed", False, [], [], op_id)
        return _result("preflight-refused", False, [], [], op_id)
    plan_written = w == "written"
    if plan_only:
        return _result("planned" if plan_written else "already-planned", plan_written, [], [], op_id)
    committed, failed = [], []
    for u in sorted({e.user for e in s.edges.values()}):
        try:
            r = migrate_user(s, u, op_id, fail=u in fail_users, crash_at=crash_at if u == crash_user else None)
        except Refused:
            failed.append(u)
            continue
        if r == "committed":
            committed.append(u)
    if failed and not committed:
        return _result("failed", plan_written, committed, failed, op_id)
    if failed:
        return _result("partial", True, committed, failed, op_id)
    if committed:
        return _result("migrated", True, committed, failed, op_id)
    return _result("planned" if plan_written else "complete", plan_written, committed, failed, op_id)


def _result(outcome, changed, committed, failed, op_id):
    return {"outcome": outcome, "store_changed": changed, "committed": list(committed), "failed": list(failed),
            "op_id": op_id}


def operation_status(s: Store, op_id: str) -> dict:
    """Discovery after an unknown return (R2-03): rebuilt from DURABLE facts only — the header's op_id and the run rows
    this operation wrote. A user it did not commit reads as not run (a failure is not durable; a re-call retries it)."""
    wrote_header = s.header is not None and s.header["op_id"] == op_id
    committed = sorted(u for (pid, u), r in s.runs.items() if r["op_id"] == op_id)
    return {"plan_written_by_op": wrote_header, "committed": committed}


# ----------------------------------------------------------------------------------------------- receipt
def receipt(s: Store, user: str) -> list:
    """§4g: a view over the outcome rows. Object text from the live edge when held; `no longer held` rendered from the
    outcome row ALONE when the edge is absent (construction §3: unreachable at the pin; defensive)."""
    rows = []
    for (pid, eid), o in sorted(s.outcomes.items()):
        if o["user"] != user:
            continue
        kind, succ = o["successor_evidence"]
        e = s.edges.get(eid)
        rows.append({"edge": eid, "outcome": o["outcome"], "object": e.obj if e is not None else "no longer held",
                     "replaced_by": succ if kind == "pointer" else "unknown", "undone": o["undone"]})
    return rows


# ----------------------------------------------------------------------------------------------- the request registry
def _replay(s: Store, user, cid, verb, digest):
    """The 0008 amendment §6c, read FIRST, before any live edge state: same verb + same request → the original result;
    any other holder → integrity conflict naming it."""
    if cid is None:
        return None
    rec = s.registry.get((user, cid))
    if rec is None:
        return None
    if rec["verb"] == verb and rec["digest"] == digest:
        return {"replayed": rec["result_ref"]}
    raise Refused(f"integrity conflict: correlation id held by {rec['verb']}")


def _register(s: Store, user, cid, verb, digest, result_ref, target):
    if cid is not None:
        s.registry[(user, cid)] = {"verb": verb, "digest": digest, "result_ref": result_ref, "target": target}
    s.act_counter += 1                                    # the store-wide act ordinal: every act write, never reset
    return s.act_counter


def confirm(s: Store, user: str, edge_id: str, cid=None):
    """0008's confirm(), only as far as the shared id space needs it."""
    digest = canonical_uid("confirm", user, edge_id)
    rep = _replay(s, user, cid, "confirm", digest)
    if rep is not None:
        return rep
    s.begin()
    s.confirmations.append((user, edge_id, cid))
    _register(s, user, cid, "confirm", digest, f"conf:{edge_id}", edge_id)
    return {"confirmed": edge_id}


# ----------------------------------------------------------------------------------------------- §4i undo
def undo(s: Store, user: str, edge_id: str, rules: Rules | None = None, correlation_id: str | None = None):
    """§4i. The registry first (replay never reads the edge); then the outcome must be PROOF (local/restored — no undo
    from testimony), APPLICABLE (no later retirement, redaction or erasure), and the edge not redacted. Restores the
    retirement fields only, per field, and clears `applicable`, under the write lock."""
    rules = rules or Rules()
    key = next(((pid, eid) for (pid, eid) in s.outcomes if eid == edge_id and s.outcomes[(pid, eid)]["user"] == user),
               None)
    digest = canonical_uid("undo", user, edge_id, key[0] if key else "")
    rep = _replay(s, user, correlation_id, "undo", digest)
    if rep is not None:
        return rep
    if key is None:
        raise Refused("no migration outcome for this edge")
    o = s.outcomes[key]
    if o["outcome"] != "restored":
        raise Refused(f"not restored ({o['outcome']})")
    if o["undone"]:
        if rules.undo_without_id_duplicate == "replay_state":
            return {"undone": edge_id, "already_undone": True}
        raise Refused("already undone")
    if o["origin"] not in PROOF:
        raise Refused("testimony: an imported outcome is not undone (§4l)")
    if not o["applicable"]:
        raise Refused("not applicable: the restoration ended (a later retirement, redaction or erasure)")
    e = s.edges.get(edge_id)
    if e is None or e.redacted:
        raise Refused("edge redacted or no longer held")
    t = s.begin()
    e.active, e.invalidated_at, e.reason = False, o["pre_invalidated_at"], o["pre_reason"]
    o["undone"], o["applicable"] = True, False
    s.journal.append(("invalidated", edge_id, t, o["pre_reason"]))
    _register(s, user, correlation_id, "undo", digest, f"outcome:{edge_id}", edge_id)
    return {"undone": edge_id, "already_undone": False}


# ----------------------------------------------------------------------------------------------- §4k doctor
def doctor_refs(s: Store) -> list:
    """`refs`: an active edge whose `supersedes` predecessor is ALSO active warns, unless an APPLICABLE PROOF outcome
    exempts it (info); testimony stays a warning."""
    out = []
    for e in s.edges.values():
        pred = s.edges.get(e.supersedes) if e.supersedes else None
        if e.active and pred is not None and pred.active:
            ex = any(eid == pred.id and o["outcome"] == "restored" and not o["undone"] and o["applicable"]
                     and o["origin"] in PROOF for (pid, eid), o in s.outcomes.items())
            out.append(("info" if ex else "warn", e.id, pred.id))
    return out


def doctor_data_migration(s: Store) -> tuple:
    """I30, the phased diagnostic, read from the HEADER's state (not from relation rows)."""
    st = plan_state(s)
    if not s.schema_v16:
        return ("none", "below v16")
    if st == "uninitialized":
        n = len(s.inventory)
        return ("warn", f"may have values to restore (judged by relation name): {n}") if n else ("none", "nothing")
    if st == "initialized-empty":
        return ("info", "planned: no relation reclassified")
    users = {e.user for e in s.edges.values()}
    missing = sorted(u for u in users if (s.header["plan_id"], u) not in s.runs)
    return ("warn", f"{len(missing)} users incomplete") if missing else ("none", "complete")


# ----------------------------------------------------------------------------------------------- erasure
def forget_user(s: Store, user: str):
    """0008am INV-Q6 + 0044/0018am's tables (construction §3): one atomic erasure over every user-linked carrier."""
    s.edges = {k: v for k, v in s.edges.items() if v.user != user}
    s.outcomes = {k: v for k, v in s.outcomes.items() if v["user"] != user}
    s.runs = {k: v for k, v in s.runs.items() if k[1] != user}
    s.registry = {k: v for k, v in s.registry.items() if k[0] != user}
    s.inventory = {k: v for k, v in s.inventory.items() if v[0] != user}
    s.confirmations = [c for c in s.confirmations if c[0] != user]


# ----------------------------------------------------------------------------------------------- §4l portability
def export(s: Store, user: str, fmt: str = "post") -> dict:
    """Edges + outcome rows with their ORIGIN, applicability and outcome_uid (never the journal, never the registry)."""
    edges = [copy.deepcopy(e) for e in s.edges.values() if e.user == user]
    outs = {k: copy.deepcopy(v) for k, v in s.outcomes.items() if v["user"] == user} if fmt == "post" else {}
    return {"format": fmt, "origin": s.origin, "edges": edges, "outcomes": outs}


def _same_record(a: Edge, b: Edge) -> bool:
    return vars(a) == vars(b)


def import_file(s: Store, f: dict, mode: str, op_id: str = "op-import") -> dict:
    """§4l. 0009's collision rule KEPT (R2-06): a record-equal edge is skipped, a differing one refuses the WHOLE import.
    A pre-format file into an unplanned store is refused (Q9). Outcome rows: the origin matrix (default → imported;
    trusted maps local → restored and never upgrades imported), validated as a whole unit before any write (R2-05)."""
    if f["format"] == "pre" and s.header is None:
        raise Refused("requires-data-migration-plan: run run_data_migration(..., plan_only=True) first")
    tx = copy.deepcopy(s)
    rec = {"converted": [], "unknown_linkage": [], "skipped_equal": []}
    incoming = {e.id: e for e in f["edges"]}
    # whole-unit validation of outcome rows BEFORE any write
    seen = {}
    for (pid, eid), o in f["outcomes"].items():
        if eid not in incoming and eid not in tx.edges:
            raise Refused(f"outcome for {eid}: no such edge in the unit or the store")
        if o.get("origin") not in ORIGINS:
            raise Refused(f"outcome for {eid}: origin {o.get('origin')!r}")
        uid = o.get("outcome_uid")
        if uid in seen and seen[uid] != o:
            raise Refused(f"outcome {uid}: conflicting duplicate")
        seen[uid] = o
        e = incoming.get(eid) or tx.edges[eid]
        if o["outcome"] == "restored" and o["applicable"] and not e.active:
            raise Refused(f"outcome for {eid}: applicable, but the edge is not active")
    for e in f["edges"]:
        held = tx.edges.get(e.id)
        if held is not None:
            if _same_record(held, e):
                rec["skipped_equal"].append(e.id)
                continue
            raise Refused(f"edge {e.id!r} already exists with different content — refuse (0009 §4c)")
        tx.edges[e.id] = copy.deepcopy(e)
    for (pid, eid), o in f["outcomes"].items():
        row = copy.deepcopy(o)
        row["origin"] = "imported" if mode == "default" else ("restored" if o["origin"] == "local" else o["origin"])
        prior = tx.outcomes.get((pid, eid))
        if prior is not None and prior["outcome_uid"] == row["outcome_uid"]:
            continue                                         # an exact replay of an outcome already held
        tx.outcomes[(pid, eid)] = row
    new = [tx.edges[e.id] for e in f["edges"] if e.id not in rec["skipped_equal"]]
    if f["format"] == "pre":
        for e in new:                                        # conversion: INCOMING rows only, never a held local row
            out = consider(tx, e, imported=True)
            if out is None:
                continue
            tx.outcomes[(tx.plan[e.relation], e.id)] = restore_row(tx, e, out, op_id)
            if out == "restored":
                e.active, e.invalidated_at, e.reason = True, None, None
            rec["converted"].append((e.id, out))
    else:
        for e in new:
            pid = tx.plan.get(e.relation)
            if pid and e.reason == "superseded" and (pid, e.id) not in tx.outcomes:
                rec["unknown_linkage"].append(e.id)
    s.__dict__.update(tx.__dict__)
    return rec


# ----------------------------------------------------------------------------------------------- §4d retained refusals
def contested_pairs(s: Store) -> list:
    """§4d (Q8 adopted; research C-5): a refusal in the STEP's inventory keeps its contested rendering while both members
    are live, no expiry; after the step, the ordinary path creates no refusals under `multi`. No timestamp is read."""
    return [(p, i) for p, i in sorted(s.refusal_inventory)
            if p in s.edges and i in s.edges and s.edges[p].active and s.edges[i].active]


# ----------------------------------------------------------------------------------------------- the 0003 ordering key
def order_key(group: list, o_reading: str = "other_than_top", negative: str = "as_is", slot: str = "s") -> tuple:
    """The 0003 amendment §4a (unchanged from v1; QO4 adopted: a negative ambiguity ranks first within its tier).
    `group`: (authority, kind), kind ∈ {"R" rendered, "O" visible not emitted (fenced linkage), "U" UNRESOLVED or
    policy-hidden — never in V}."""
    R = sorted((a for a, k in group if k == "R"), reverse=True)
    V = sorted((a for a, k in group if k in ("R", "O")), reverse=True)
    if not R:
        return (1, 0, 0, 0, slot)
    top1 = R[0]
    if o_reading == "other_than_top":
        rest = list(V); rest.remove(top1)
    else:
        rest = [a for a, k in group if k == "O"]
    amb = (top1 - max(rest)) if rest else float("inf")
    if amb < 0 and negative == "last":
        amb = float("inf")
    return (0, -top1, amb, -len(V), slot)


# ----------------------------------------------------------------------------------------------- the 0029 amendment
REINSTATEMENT_REASONS = ("source_restored", "arity_reclassified")


def journal_reinstated(s: Store, edge_id: str, reason, t: int | None = None):
    """0029am INV-J1: a `reinstated` event's reason must be in the closed set; NULL or outside is refused."""
    if reason not in REINSTATEMENT_REASONS:
        raise Refused(f"reinstated with reason {reason!r} — outside {REINSTATEMENT_REASONS}")
    s.inventory.pop(edge_id, None)      # research's C-4 residual: ANY reinstatement ends inventory membership, terminally,
    #                                     at the one reinstate choke point (sqlite.py:847), so a later re-retirement cannot
    #                                     match the inventoried tuple even with an identical (invalidated_at, reason)
    s.journal.append(("reinstated", edge_id, t if t is not None else s.begin(), reason))


def reinstated_reason(event) -> str:
    """0029am INV-J2: an old NULL-reason event reads `source_restored`; the stored event is never rewritten."""
    return event[3] if len(event) > 3 and event[3] is not None else "source_restored"


def restore_source(s: Store, edge_id: str):
    """0022's reinstate verb on one edge (0029am INV-J3: it writes `source_restored`)."""
    e = s.edges[edge_id]
    t = s.begin()
    e.active, e.invalidated_at, e.reason = True, None, None
    journal_reinstated(s, edge_id, "source_restored", t)
