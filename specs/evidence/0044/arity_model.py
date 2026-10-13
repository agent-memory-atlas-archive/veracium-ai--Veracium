"""Reference model for 0044 stage 1 (accumulation) — v3, for package I's round 4.

Encodes 0044 v1.5, the 0018 amendment v4 and the 0003 amendment v1.5 as research drafts them, plus the shared
constructions of the 0008 amendment v1.3 that this package uses: the request registry (undo is a verb), import
identity and projection, the act ordinal, the terminal `request_redacted` and the one erasure rule.
Every rule is one function here, named by its section, so a reader can hold the two side by side.

A MODEL, not product code: it imports nothing from `veracium`. Product tests bind the same properties to shipped code at
the implementation gate (R1-10's split, kept). What v2 added, each answering a round-2 finding:
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
What v3 adds, each answering a round-3 finding:
  * every edge writer passes ONE emission choke point, `journal_edge_write`, which derives the lifetime transition from
    the persisted prior row and the new row, before its unchanged-bytes return (0044 §4f-ii, R3-01); `add_edge` is the
    same-id upsert round 3 found, and passes it like every other writer;
  * an outcome's replay is decided by COMPARING its canonical projection over the staged union; one outcome per
    `(plan_id, edge_id)` slot; an ended episode is never revived; `undo_request_ref` is store-local (0044 §4l, R3-02);
  * the result carrier gains `plan_written` and a validating constructor with the §4c rejection matrix; the plan's
    digest covers only the three reclassified declarations; an `op_id` is bound by a durable admission record
    (0018am v4 §4b.1b, §4b.2, §4c; R3-03);
  * a redaction replaces every registry digest on the edge, `undo` included, and a retry returns the terminal
    `request_redacted` (0008am v1.3 §6g; R3-03);
  * erasure removes the user's refusal inventory and refusals (R3-03).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
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
CALLER_KEY = re.compile(r"[A-Za-z0-9._:-]{1,64}")      # 0008 §6c's caller grammar (the 0008 amendment §6e)


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

    def __deepcopy__(self, memo):
        """Every field is immutable (str, int, bool, None, a tuple of str), so a field-for-field copy IS a deep copy;
        the enumeration copies stores thousands of times per run, and this is its cost."""
        return Edge(**vars(self))


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
    refusal_inventory: set = field(default_factory=set)   # (refusal_id, user_id) at the step; refusal_id = (prior, incoming)
    header: dict | None = None                            # {plan_id, registry_digest, op_id, written_txn}
    plan: dict = field(default_factory=dict)              # relation -> plan_id (the header's relation rows)
    runs: dict = field(default_factory=dict)              # (plan_id, user) -> {op_id, txn}
    outcomes: dict = field(default_factory=dict)          # (plan_id, edge_id) -> row (see restore_row): ONE per slot
    registry: dict = field(default_factory=dict)          # (user, cid) -> {verb, digest, result_ref, target}
    confirmations: list = field(default_factory=list)     # (user, edge_id, cid) — 0008's verb, for the shared id space
    journal: list = field(default_factory=list)           # (kind, edge_id, txn, reason) — store-local, never exported
    migration_ops: dict = field(default_factory=dict)     # op_id -> {op_id, mode, inputs_digest, admitted_at} (0018am)

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


def plan_input_digest(canon: dict) -> str:
    """0018am v4 §4b.2: a digest of the plan's INPUTS only — the canonical declarations of the three reclassified
    relations — so an unrelated registry edit never trips `registry-changed`."""
    return registry_digest({r: canon[r] for r in PLAN_RELATIONS if r in canon})


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


# ----------------------------------------------------------------------------------------------- §4f-ii the choke point
REINSTATEMENT_REASONS = ("source_restored", "arity_reclassified")


def _snap(e: Edge | None) -> dict | None:
    """The persisted row, as the writer hands it to the choke point (a copy: the write must not alias it)."""
    return None if e is None else copy.deepcopy(vars(e))


def _life(row: dict | None) -> tuple | None:
    return None if row is None else (row["active"], row["invalidated_at"], row["reason"], row["redacted"])


def derive_transition(prior: tuple | None, new: tuple | None) -> str | None:
    """0044 v1.5 §4f-ii's table, over the persisted prior and the new row's lifetime (active, invalidated_at, reason,
    redacted); None = no persisted row (before: an insert; after: a removal). Never which method wrote, never the
    journal kind."""
    if prior is None:
        return None                                   # an insert (a row ARRIVING retired included) is not a transition
    if new is None:
        return "removal"                              # §4i v1.5, defensive: the row removed while its outcome is kept
    p_active, p_at, p_reason, p_red = prior
    n_active, n_at, n_reason, n_red = new
    if n_red and not p_red:
        return "redaction"
    if not p_active and n_active:
        return "reinstatement"
    if p_active and not n_active:
        return "retirement"
    if not p_active and not n_active and (p_at, p_reason) != (n_at, n_reason):
        return "re-retirement"
    return None                                       # active → active (an ordinary mutation), or unchanged


def apply_transition(s: Store, edge_id: str, transition: str | None):
    """The table's effects, in the writer's own transaction: a reinstatement ends `arity_inventory` membership,
    terminally; a retirement, re-retirement, redaction or (§4i v1.5, defensively) the row's removal clears
    `applicable` on the row's outcome, terminally — so a later insert under the id finds it already cleared."""
    if transition == "reinstatement":
        s.inventory.pop(edge_id, None)
    elif transition in ("retirement", "re-retirement", "redaction", "removal"):
        _clear_applicable(s, edge_id)


def journal_reinstated(s: Store, edge_id: str, reason, t: int | None = None):
    """0029am INV-J1: a `reinstated` event's reason must be in the closed set; NULL or outside is refused."""
    if reason not in REINSTATEMENT_REASONS:
        raise Refused(f"reinstated with reason {reason!r} — outside {REINSTATEMENT_REASONS}")
    s.journal.append(("reinstated", edge_id, t if t is not None else s.begin(), reason))


def journal_edge_write(s: Store, edge_id: str, prior: dict | None, *, kind: str | None = None, reason=None,
                       t: int | None = None) -> str | None:
    """0029's emission choke point (`_journal_edge_write`), called by every `edges` writer AFTER its row write with the
    persisted prior. 0044 v1.5 §4f-ii: the lifetime transition is DERIVED HERE, from the prior and the new row, BEFORE
    the unchanged-bytes return. The journal kind follows 0029 (prior absent → created; changed → mutated or the site's
    flip hint; unchanged → no event, except a `redacted` write)."""
    new = _snap(s.edges.get(edge_id))
    apply_transition(s, edge_id, derive_transition(_life(prior), _life(new)))
    if new is None:
        return None                                   # a removal journals no event (0029 journals row writes)
    if prior is not None and prior == new and kind != "redacted":
        return None
    t = t if t is not None else s.txn
    if prior is None:
        kind = "created"
    elif kind is None:
        kind = "mutated"
    if kind == "reinstated":
        journal_reinstated(s, edge_id, reason, t)
    else:
        s.journal.append((kind, edge_id, t, reason))
    return kind


def _write(s: Store, edge_id: str, apply, *, kind: str | None = None, reason=None, t: int | None = None):
    """Every `edges` writer: the persisted prior, the row write, then the choke point. A `reinstated` write with a
    reason outside the closed set is refused BEFORE the row changes (0029's refusal unwinds the transaction)."""
    if kind == "reinstated" and reason not in REINSTATEMENT_REASONS:
        raise Refused(f"reinstated with reason {reason!r} — outside {REINSTATEMENT_REASONS}")
    prior = _snap(s.edges.get(edge_id))
    apply()
    return journal_edge_write(s, edge_id, prior, kind=kind, reason=reason, t=t)


def add_edge(s: Store, edge: Edge) -> str | None:
    """The store API's same-id UPSERT (`SqliteStore.add_edge` → `_upsert_edge_row`): writes the given row whole,
    whatever its lifetime fields, and passes the choke point like every writer. Round 3's R3-01 path; the owner kept
    `add_edge` unchanged (no lifetime-changing write is refused — its transitions are bound)."""
    t = s.begin()
    new = copy.deepcopy(edge)
    return _write(s, edge.id, lambda: s.edges.__setitem__(edge.id, new), t=t)


def remove_edge(s: Store, edge_id: str):
    """The DEFENSIVE removal of one edge row while its user (and so its outcome row) is retained — 0044 §4g's
    absent-edge case, unreachable at the pin (§4g-ii: the only `DELETE FROM edges` is the per-user erasure loop). It
    passes the choke point, whose removal row ends the episode (§4i v1.5)."""
    t = s.begin()
    _write(s, edge_id, lambda: s.edges.pop(edge_id, None), t=t)


def _set_lifetime(s: Store, edge_id: str, active: bool, at, reason):
    e = s.edges.get(edge_id)
    e.active, e.invalidated_at, e.reason = active, at, reason


# ----------------------------------------------------------------------------------------------- writers
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
            _write(s, p.id, lambda p=p: _set_lifetime(s, p.id, False, incoming.valid_from, "superseded"),
                   kind="invalidated", reason="superseded", t=t)
            if incoming.supersedes is None:
                incoming.supersedes = p.id
    _write(s, incoming.id, lambda: s.edges.__setitem__(incoming.id, incoming), t=t)
    return "superseded" if arity == "single" and priors else "added"


def supersede_single(s: Store, prior: Edge, incoming: Edge):
    """The pre-upgrade `single` path, explicitly (the stored rows the restoration acts on)."""
    t = s.begin()
    if prior.id not in s.edges:
        _write(s, prior.id, lambda: s.edges.__setitem__(prior.id, prior), t=t)
    _write(s, prior.id, lambda: _set_lifetime(s, prior.id, False, incoming.valid_from, "superseded"),
           kind="invalidated", reason="superseded", t=t)
    if incoming.supersedes is None:
        incoming.supersedes = prior.id
    _write(s, incoming.id, lambda: s.edges.__setitem__(incoming.id, incoming), t=t)


def retire(s: Store, edge_id: str, reason: str, at_valid: int = 0):
    """The invalidate method (F4b: `_invalidate_edge_row`). v1.5: NOT the sole retirement writer; its effect on
    `applicable` is the choke point's, as for every writer (§4f-ii)."""
    t = s.begin()
    _write(s, edge_id, lambda: _set_lifetime(s, edge_id, False, at_valid, reason), kind="invalidated", reason=reason,
           t=t)


def _clear_applicable(s: Store, edge_id: str):
    for (pid, eid), o in s.outcomes.items():
        if eid == edge_id:
            o["applicable"] = False


def redact(s: Store, edge_id: str):
    """0041: content REPLACED and attested; a journaled `redacted` write that does NOT retire (research C-6). It passes
    the choke point (v1.5: v1.4 said it did not), whose redaction row clears `applicable`. The 0008 amendment §6g: the
    redaction REPLACES the request digest of every registry row on the edge, every verb (`confirm`, `undo`)."""
    t = s.begin()

    def w():
        e = s.edges.get(edge_id)
        e.relation, e.obj, e.redacted = MARKER, MARKER, True
    _write(s, edge_id, w, kind="redacted", t=t)
    redact_request_digests(s, edge_id)


def redact_request_digests(s: Store, edge_id: str):
    """The 0008 amendment §6g: `target_edge_id` finds the edge's requests, and their digests are replaced, whatever the
    verb. The id stays held."""
    for rec in s.registry.values():
        if rec["target"] == edge_id:
            rec["digest"] = MARKER


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
    for e in list(s.edges.values()):
        if not e.active and e.reason == "revoked_source" and not would_be_revoked(s, e):
            t = s.begin()
            _write(s, e.id, lambda e=e: _set_lifetime(s, e.id, True, None, None), kind="reinstated",
                   reason="source_restored", t=t)


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
            member = s.edges.get(prior) or s.edges.get(incoming)
            s.refusal_inventory.add(((prior, incoming), member.user if member else None))   # §4f: (refusal_id, user_id)
    s.schema_v16 = True


# ----------------------------------------------------------------------------------------------- §4e the plan
def write_plan(s: Store, registry: dict, op_id: str, admission: dict | None = None) -> str:
    """§4e: ONE write transaction. The header is written even for an empty relation set; exactly one header exists;
    a caller that finds one compares digests (equal → continue, nothing written; different → registry-changed). The
    digest is the plan's INPUT digest (0018am v4 §4b.2). `admission`: the 0018am admission record, written in this
    transaction when it writes the header (the call's first durable write)."""
    canon = admit_registry(registry)
    dig = plan_input_digest(canon)
    if s.header is not None:
        if s.header["registry_digest"] != dig:
            raise Refused("registry-changed")
        return "existing"
    t = s.begin()
    s.header = {"plan_id": "plan-1", "registry_digest": dig, "op_id": op_id, "written_txn": t}
    for rel in PLAN_RELATIONS:
        if canon.get(rel) == DEFAULT_REGISTRY[rel]:
            s.plan[rel] = "plan-1"
    if admission is not None and op_id not in s.migration_ops:
        s.migration_ops[op_id] = dict(admission, admitted_at=t)
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


def restore_row(s: Store, e: Edge, out: str, origin: str = "local") -> dict:
    """§4g's `migration_outcome` row (v1.4's digest and op-id columns gone): `undo_request_ref` is store-local."""
    pid = s.plan[e.relation]
    succ = sorted(x.id for x in s.edges.values() if x.supersedes == e.id)
    return {"plan_id": pid, "edge_id": e.id, "user": e.user, "outcome": out, "pre_invalidated_at": e.invalidated_at,
            "pre_reason": e.reason, "successor_evidence": ["pointer", succ] if succ else ["none", []],
            "undone_at": None, "applicable": out == "restored", "origin": origin,
            "outcome_uid": canonical_uid(s.origin, e.user, pid, e.id), "undo_request_ref": None}


# ----------------------------------------------------------------------------------------------- §4h the operation
def migrate_user(s: Store, user: str, op_id: str, fail: bool = False, crash_at: str | None = None,
                 admission: dict | None = None):
    """The per-user phase, ONE transaction: work on a copy, swap it in at commit. The admission record, when not yet
    held, commits with the first user (0018am v4 §4b.1b)."""
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
        tx.outcomes[(pid, e.id)] = restore_row(tx, e, out)
        if out == "restored":
            _write(tx, e.id, lambda e=e: _set_lifetime(tx, e.id, True, None, None), kind="reinstated",
                   reason="arity_reclassified", t=t)
        if crash_at == "mid_user":
            raise Crash("before commit")
    if fail:
        raise Refused(f"user {user}: transaction failed")
    tx.runs[(pid, user)] = {"op_id": op_id, "txn": t}
    if admission is not None and op_id not in tx.migration_ops:
        tx.migration_ops[op_id] = dict(admission, admitted_at=t)
    s.__dict__.update(tx.__dict__)                        # COMMIT
    if crash_at == "after_commit":
        raise Crash("after commit, before delivery")
    return "committed"


RESULT_ROWS = {
    # outcome: store_changed — 0018am v4 §4c's closed table (research's prose; this is its executable form)
    "requires-schema-step": False,
    "preflight-refused": False,
    "registry-changed": False,
    "op-id-conflict": False,    # v4: the op_id is held with a different inputs digest or mode; nothing written
    "planned": True,            # this call wrote the header and restored nothing (plan-only, or a full call with no users)
    "already-planned": False,   # plan-only, an equal header existed
    "complete": False,          # full call: every user already had a run row; nothing written
    "migrated": True,           # ≥1 user committed, none failed
    "partial": True,            # ≥1 committed and ≥1 failed
    "failed": None,             # 0 committed, ≥1 failed: store_changed = plan_written
}
RESULT_FIELDS = ("outcome", "store_changed", "plan_written", "committed", "failed", "op_id")
_NO_PLAN_WRITE = ("requires-schema-step", "preflight-refused", "registry-changed", "op-id-conflict",
                  "already-planned", "complete")
_MISSING = object()


def make_result(**f) -> dict:
    """0018am v4 §4c: the VALIDATING constructor (the I15 discipline). It rejects every carrier of the rejection matrix,
    one refusal per row, and constructs every row of the outcome table with consistent fields."""
    missing = [k for k in RESULT_FIELDS if k not in f or f[k] is _MISSING]
    extra = sorted(set(f) - set(RESULT_FIELDS))
    if missing or extra:
        raise Refused(f"result row 2: missing {missing} / unknown {extra}")
    o, sc, pw, c, fl, op = (f[k] for k in RESULT_FIELDS)
    if o not in RESULT_ROWS:
        raise Refused(f"result row 1: outcome {o!r} is not a row of §4c")
    if not (isinstance(sc, bool) and isinstance(pw, bool) and isinstance(c, list) and isinstance(fl, list)):
        raise Refused("result row 2: a field of the wrong type")
    if sc != (pw or bool(c)):
        raise Refused("result row 3: store_changed ≠ (plan_written ∨ committed ≠ ∅)")
    if (o in ("partial", "failed")) != bool(fl):
        raise Refused(f"result row 4: `failed` on {o!r}")
    if (o in ("migrated", "partial")) != bool(c):
        raise Refused(f"result row 5: `committed` on {o!r}")
    if set(c) & set(fl):
        raise Refused("result row 6: a user both committed and failed")
    if (pw and o in _NO_PLAN_WRITE) or (not pw and o == "planned"):
        raise Refused(f"result row 7: plan_written={pw} on {o!r}")
    if not isinstance(op, str) or not CALLER_KEY.fullmatch(op):
        raise Refused("result row 8: op_id outside §6c's caller grammar")
    return {k: (list(f[k]) if k in ("committed", "failed") else f[k]) for k in RESULT_FIELDS}


def _result(outcome, changed, committed, failed, op_id, plan_written=_MISSING):
    return make_result(outcome=outcome, store_changed=changed, plan_written=plan_written, committed=list(committed),
                       failed=list(failed), op_id=op_id)


def inputs_digest(canon: dict, mode: str) -> str:
    """0018am v4 §4b.1b: the canonical digest of the operation's inputs — §4b.2's plan-input digest and the mode. The
    attestation is NOT an input (a resume legitimately carries a fresh one)."""
    return canonical_uid(plan_input_digest(canon), mode)


def run_data_migration(s: Store, registry: dict, *, op_id: str = "op-1", plan_only: bool = False,
                       attested: bool = True, fail_users=(), crash_user=None, crash_at=None) -> dict:
    """0018am v4 §4b. Returns the total result carrier: outcome, store_changed, plan_written, committed, failed,
    op_id. Each user phase is its own transaction; a failing user is named and the call continues."""
    if not isinstance(op_id, str) or not CALLER_KEY.fullmatch(op_id):
        raise Refused("op_id outside §6c's caller grammar")
    if not attested:
        return _result("preflight-refused", False, [], [], op_id, plan_written=False)
    if not s.schema_v16:
        return _result("requires-schema-step", False, [], [], op_id, plan_written=False)
    try:
        canon = admit_registry(registry)
    except Refused:
        return _result("preflight-refused", False, [], [], op_id, plan_written=False)
    mode = "plan_only" if plan_only else "restore"
    admission = {"op_id": op_id, "mode": mode, "inputs_digest": inputs_digest(canon, mode)}
    held = s.migration_ops.get(op_id)
    if held is not None and not same_operation(held, admission):
        return _result("op-id-conflict", False, [], [], op_id, plan_written=False)
    try:
        w = write_plan(s, registry, op_id, admission)
    except Refused as x:
        if "registry-changed" in str(x):
            return _result("registry-changed", False, [], [], op_id, plan_written=False)
        return _result("preflight-refused", False, [], [], op_id, plan_written=False)
    plan_written = w == "written"
    if plan_only:
        return _result("planned" if plan_written else "already-planned", plan_written, [], [], op_id,
                       plan_written=plan_written)
    committed, failed = [], []
    for u in sorted({e.user for e in s.edges.values()}):
        try:
            r = migrate_user(s, u, op_id, fail=u in fail_users, crash_at=crash_at if u == crash_user else None,
                             admission=admission)
        except Refused:
            failed.append(u)
            continue
        if r == "committed":
            committed.append(u)
    if failed and not committed:
        return _result("failed", plan_written, committed, failed, op_id, plan_written=plan_written)
    if failed:
        return _result("partial", True, committed, failed, op_id, plan_written=plan_written)
    if committed:
        return _result("migrated", True, committed, failed, op_id, plan_written=plan_written)
    return _result("planned" if plan_written else "complete", plan_written, committed, failed, op_id,
                   plan_written=plan_written)


def same_operation(held: dict, admission: dict) -> bool:
    """0018am v4 §4b.1b: a held op_id is the same operation iff its inputs digest (which includes the mode) is equal."""
    return held["inputs_digest"] == admission["inputs_digest"]


def data_migration_status(s: Store, op_id: str) -> dict:
    """Discovery after an unknown return (R2-03; v4): the operation's CUMULATIVE durable commits, over every invocation
    under the op_id — the header's op_id and the run rows it wrote — or `unknown-op` when no admission record holds the
    id. A user it did not commit reads as not run (a failure is not durable; a re-call retries it)."""
    if op_id not in s.migration_ops:
        return {"outcome": "unknown-op"}
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
                     "replaced_by": succ if kind == "pointer" else "unknown", "undone": o["undone_at"] is not None})
    return rows


# ----------------------------------------------------------------------------------------------- the request registry
def _replay(s: Store, user, cid, verb, digest):
    """The 0008 amendment §6c/§6g, read FIRST, before any live edge state. v1.3: a request whose digest a redaction
    replaced is TERMINAL for its own verb — `request_redacted`, whatever the payload, before any replay; another verb
    under the id still conflicts (the id stays held). Otherwise same verb + same request → the original result; any
    other holder → integrity conflict naming it."""
    if cid is None:
        return None
    rec = s.registry.get((user, cid))
    if rec is None:
        return None
    if rec["verb"] == verb and rec["digest"] == MARKER:
        return {"terminal": "request_redacted"}
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
    """§4i. The registry first (replay never reads the edge; a redacted request is terminal first); then the outcome
    must be PROOF (local/restored — no undo from testimony), APPLICABLE (no later retirement, redaction or erasure),
    and the edge not redacted. Restores the retirement fields only, per field, under the write lock."""
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
    if o["undone_at"] is not None:
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
    _write(s, edge_id, lambda: _set_lifetime(s, edge_id, False, o["pre_invalidated_at"], o["pre_reason"]),
           kind="invalidated", reason=o["pre_reason"], t=t)
    o["undone_at"], o["applicable"] = t, False
    _register(s, user, correlation_id, "undo", digest, f"outcome:{edge_id}", edge_id)
    if correlation_id is not None:
        o["undo_request_ref"] = (user, correlation_id)    # store-local: never exported, never compared (§4g)
    return {"undone": edge_id, "already_undone": False}


# ----------------------------------------------------------------------------------------------- §4k doctor
def doctor_refs(s: Store) -> list:
    """`refs`: an active edge whose `supersedes` predecessor is ALSO active warns, unless an APPLICABLE PROOF outcome
    exempts it (info); testimony stays a warning."""
    out = []
    for e in s.edges.values():
        pred = s.edges.get(e.supersedes) if e.supersedes else None
        if e.active and pred is not None and pred.active:
            ex = any(eid == pred.id and o["outcome"] == "restored" and o["undone_at"] is None and o["applicable"]
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
    """The 0008 amendment's ONE erasure rule (§6g) + 0044 §4g-ii: one atomic erasure over every user-linked carrier,
    the refusal inventory and refusals on the user's edges included (R3-03). The disposition of `edges` is `erasure`,
    not the choke point. The admission record is NOT erased: it holds no user content and lives as long as the store
    (0018am v4 §4b.1b); its per-user part is the run rows, which go."""
    mine = {k for k, v in s.edges.items() if v.user == user}
    s.edges = {k: v for k, v in s.edges.items() if v.user != user}
    s.outcomes = {k: v for k, v in s.outcomes.items() if v["user"] != user}
    s.runs = {k: v for k, v in s.runs.items() if k[1] != user}
    s.registry = {k: v for k, v in s.registry.items() if k[0] != user}
    s.inventory = {k: v for k, v in s.inventory.items() if v[0] != user}
    s.confirmations = [c for c in s.confirmations if c[0] != user]
    s.refusals = [r for r in s.refusals if r[0] not in mine and r[1] not in mine]
    s.refusal_inventory = {r for r in s.refusal_inventory if r[1] != user}


# ----------------------------------------------------------------------------------------------- §4l portability
def export(s: Store, user: str, fmt: str = "post") -> dict:
    """Edges + outcome rows with their ORIGIN, applicability and outcome_uid (never the journal, never the registry,
    and never `undo_request_ref`, which is store-local, §4g)."""
    edges = [copy.deepcopy(e) for e in s.edges.values() if e.user == user]
    outs = {}
    if fmt == "post":
        for k, v in s.outcomes.items():
            if v["user"] == user:
                row = copy.deepcopy(v)
                row.pop("undo_request_ref", None)
                outs[k] = row
    return {"format": fmt, "origin": s.origin, "edges": edges, "outcomes": outs}


def _same_record(a: Edge, b: Edge) -> bool:
    return vars(a) == vars(b)


# §4l v1.5: the outcome's canonical comparison projection — the lifecycle as its STAGE. EXCLUDED: the trust label
# (`origin`), `undo_request_ref`, and the VALUE of `undone_at` (the undoing store's own clock).
OUTCOME_PROJECTION = ("outcome_uid", "plan_id", "edge_id", "user", "outcome", "pre_invalidated_at", "pre_reason",
                      "successor_evidence")
STAGES = ("live", "ended", "undone")


def stage(o: dict) -> str:
    """§4l v1.5: `live` (applicable, not undone), `ended` (not applicable, not undone: a retirement, a redaction or the
    edge's removal ended it) or `undone`."""
    if o.get("undone_at") is not None:
        return "undone"
    return "live" if o.get("applicable") else "ended"


def outcome_projection(o: dict) -> str:
    return json.dumps({**{k: o.get(k) for k in OUTCOME_PROJECTION}, "stage": stage(o)}, sort_keys=True, default=list)


def episode_replay(held: dict, arr: dict) -> bool:
    """§4l v1.5: an ended local episode is never revived. The stage moves only from `live` to ONE of two endings, and
    the endings are different histories. True iff the HELD row is `ended` or `undone` and the arrival differs from it
    ONLY by being `live`: older evidence of the same episode, an exact replay, the held stage kept. Every other stage
    difference is a conflicting replay."""
    if stage(held) == "live" or stage(arr) != "live":
        return False
    return outcome_projection({**arr, "applicable": held["applicable"], "undone_at": held["undone_at"]}) \
        == outcome_projection(held)


def replay_decision(held: dict, arr: dict) -> bool:
    """§4l: an arrival under a held outcome_uid is an EXACT REPLAY (a no-op) iff the canonical projections are equal,
    or the held episode has ended and the arrival is the same episode still `live`; otherwise a conflicting replay."""
    return outcome_projection(held) == outcome_projection(arr) or episode_replay(held, arr)


def slot_taken(staged: dict, row: dict) -> bool:
    """§4l: one outcome per `(plan_id, destination edge_id)` slot over the staged union — a slot held, or claimed by an
    earlier row of this unit, under a DIFFERENT outcome_uid."""
    other = staged.get((row["plan_id"], row["edge_id"]))
    return other is not None and other["outcome_uid"] != row["outcome_uid"]


def _remap(f: dict, remap: dict | None):
    """User and id remapping (§4l; the 0008 amendment §6e): every edge id, `supersedes`, outcome edge reference and
    successor reference is mapped; outcome_uid is portable and never remapped."""
    users = (remap or {}).get("users", {})
    ids = (remap or {}).get("ids", {})
    edges = []
    for e in f["edges"]:
        e2 = copy.deepcopy(e)
        e2.id, e2.user = ids.get(e.id, e.id), users.get(e.user, e.user)
        e2.supersedes = ids.get(e.supersedes, e.supersedes) if e.supersedes else None
        edges.append(e2)
    rows = []
    for o in f["outcomes"].values():
        o2 = copy.deepcopy(o)
        o2["edge_id"], o2["user"] = ids.get(o["edge_id"], o["edge_id"]), users.get(o["user"], o["user"])
        kind, succ = o["successor_evidence"]
        o2["successor_evidence"] = [kind, [ids.get(x, x) for x in succ]]
        rows.append(o2)
    return edges, rows


def import_file(s: Store, f: dict, mode: str, op_id: str = "op-import", remap: dict | None = None) -> dict:
    """§4l. 0009's collision rule KEPT (R2-06): a record-equal edge is skipped, a differing one refuses the WHOLE import.
    A pre-format file into an unplanned store is refused (Q9). Outcome rows (v1.5, R3-02): ONE admission rule — every
    outcome's edge IN THE UNIT — then replay decided by comparing canonical projections over the staged union, one
    outcome per slot, an ended episode never revived; the whole unit validated before any write; then the origin
    matrix (default → imported; trusted maps local → restored and never upgrades imported)."""
    if f["format"] == "pre" and s.header is None:
        raise Refused("requires-data-migration-plan: run run_data_migration(..., plan_only=True) first")
    tx = copy.deepcopy(s)
    rec = {"converted": [], "unknown_linkage": [], "skipped_equal": [], "outcomes_replayed": []}
    edges, rows = _remap(f, remap)
    incoming = {e.id: e for e in edges}
    # ---- whole-unit validation of the outcome rows, BEFORE any write
    staged = {k: v for k, v in tx.outcomes.items()}                 # the staged union, slot -> row
    held_by_uid = {v["outcome_uid"]: v for v in tx.outcomes.values()}
    unit_by_uid, admit = {}, []
    for o in rows:
        eid, uid = o["edge_id"], o.get("outcome_uid")
        if eid not in incoming:
            raise Refused(f"outcome for {eid}: its edge is not in the unit (one admission rule)")
        if o.get("origin") not in ORIGINS:
            raise Refused(f"outcome for {eid}: origin {o.get('origin')!r}")
        kind, succ = o["successor_evidence"]
        if any(x not in incoming for x in succ):
            raise Refused(f"outcome for {eid}: a successor reference does not resolve in the unit")
        e = incoming[eid]
        if o["outcome"] == "restored" and o["applicable"] and not e.active:
            raise Refused(f"outcome for {eid}: applicable, but the edge is not active")
        if o["undone_at"] is not None and (e.active or (e.invalidated_at, e.reason)
                                           != (o["pre_invalidated_at"], o["pre_reason"])):
            raise Refused(f"outcome for {eid}: undone, but the edge is not retired with the recorded pre-state")
        if uid in unit_by_uid:
            if outcome_projection(unit_by_uid[uid]) != outcome_projection(o):
                raise Refused(f"outcome {uid}: two differing copies in one unit")
            continue                                                # a copy of itself: one outcome
        unit_by_uid[uid] = o
        h = held_by_uid.get(uid)
        if h is not None:
            if replay_decision(h, o):
                rec["outcomes_replayed"].append(uid)
                continue                                            # exact replay: a no-op, the held row kept
            raise Refused(f"outcome {uid}: a held outcome_uid with a different projection (conflicting replay)")
        if slot_taken(staged, o):
            raise Refused(f"outcome slot {(o['plan_id'], eid)}: held or claimed under a different outcome_uid")
        staged[(o["plan_id"], eid)] = o
        admit.append(o)
    # ---- edges: 0009 (record-equal → skipped; differing → the whole import refused)
    for e in edges:
        held = tx.edges.get(e.id)
        if held is not None:
            if _same_record(held, e):
                rec["skipped_equal"].append(e.id)
                continue
            raise Refused(f"edge {e.id!r} already exists with different content — refuse (0009 §4c)")
    writes = [e for e in edges if e.id not in rec["skipped_equal"]]
    t = tx.begin() if writes or admit else tx.txn          # a pure replay spends no transaction
    for e in edges:
        if e.id not in rec["skipped_equal"]:
            _write(tx, e.id, lambda e=e: tx.edges.__setitem__(e.id, copy.deepcopy(e)), t=t)
    for o in admit:
        row = copy.deepcopy(o)
        row["origin"] = "imported" if mode == "default" else ("restored" if o["origin"] == "local" else o["origin"])
        row["undo_request_ref"] = None                              # store-local: an import writes NULL (§4g)
        tx.outcomes[(row["plan_id"], row["edge_id"])] = row
    new = [tx.edges[e.id] for e in edges if e.id not in rec["skipped_equal"]]
    if f["format"] == "pre":
        for e in new:                                        # conversion: INCOMING rows only, never a held local row
            out = consider(tx, e, imported=True)
            if out is None:
                continue
            tx.outcomes[(tx.plan[e.relation], e.id)] = restore_row(tx, e, out)
            if out == "restored":
                _write(tx, e.id, lambda e=e: _set_lifetime(tx, e.id, True, None, None), kind="reinstated",
                       reason="arity_reclassified", t=t)
            rec["converted"].append((e.id, out))
    else:
        for e in new:
            pid = tx.plan.get(e.relation)
            if pid and e.reason == "superseded" and (pid, e.id) not in tx.outcomes:
                rec["unknown_linkage"].append(e.id)
    s.__dict__.update(tx.__dict__)                           # COMMIT (a replay commits an unchanged staged state)
    return rec


# ----------------------------------------------------------------------------------------------- §4d retained refusals
def contested_pairs(s: Store) -> list:
    """§4d (Q8 adopted; research C-5): a refusal in the STEP's inventory keeps its contested rendering while both members
    are live, no expiry; after the step, the ordinary path creates no refusals under `multi`. No timestamp is read."""
    return [(p, i) for (p, i), _user in sorted(s.refusal_inventory, key=lambda r: r[0])
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
def reinstated_reason(event) -> str:
    """0029am INV-J2: an old NULL-reason event reads `source_restored`; the stored event is never rewritten."""
    return event[3] if len(event) > 3 and event[3] is not None else "source_restored"


def restore_source(s: Store, edge_id: str):
    """0022's reinstate verb on one edge (0029am INV-J3: it writes `source_restored`)."""
    t = s.begin()
    _write(s, edge_id, lambda: _set_lifetime(s, edge_id, True, None, None), kind="reinstated",
           reason="source_restored", t=t)
