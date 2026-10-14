"""Reference model for package II (0045 grounding × 0047 replies × confirmations): research's
GROUNDING-REPLY-TRANSITIONS-DRAFT draft 3.4 (research 12142443, sha16 b697bda6), the 0008 amendment
`0047/0008-request-registry` (the request registry, act origin, user erasure), with the owner's 2026-10-11 rulings
"Label, don't block" and "Add the link" (an edge records its source episode), executed.

Round 4 final (research 82fcdb7b: 0008am v1.7, 0041am v1.10, 0047 v1.13, 0045 v1.10): a notice takes effect only
where a RECORD SHOWS the redaction, an import that would land content under a notice is refused, and a notice's effect
is decided by its target's state and the mode (0041am §4's one table); a PENDING or STANDING notice is not an
attestation; no rule reads a notice's origin. Round 4's earlier rules, kept: HELD is the STAGED UNION
(destination ∪ every row of the unit, after id remapping); act equality is decided on the canonical TREATED projection
under the union's notice coverage, with ONE authorized notice transition; coverage is all or nothing per row; the trust
label is excluded from the projection (no `recorded_origin` carrier); chronology is validated over the merged history H;
`undo` is a third verb of the registry; `attv` carries the predicate version. Display ORDER of the inspection unit is a
PRODUCT contract (0047 §4d v1.9): this model sorts by position only to pick a deterministic excerpt, never as a claim.

A MODEL, not product code: no `veracium` import. One function per rule section. Ambiguities and the alternatives the
owner rejected are named switches (`Rules`); the run executes them as mutants or probes, never silently.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

MARKER = "\x00redacted\x00"
REQUEST_REDACTED = "request_redacted"                 # the terminal replay after a redaction (0041am INV-RR5)
CALLER_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")      # 0008 §6c's grammar, enforced at the host entry only
PREDICATE_VERSION = "ATTEST-3@b1329a81"              # 0045 v1.9 §4a: the frozen predicate this model's write path runs
DEFAULT_IMPORT = "default-import"                    # 0045 v1.9 §4e: no predicate judged a default-imported row here
NON_USER = "non-user-effective"                      # 0045 v1.9 §4a: the author rule set `not_attested`; no predicate ran
ATTV = re.compile(r"ATTEST-\d+@[0-9a-f]{8}|non-user-effective|default-import")   # 0045 v1.9 §2c: else the unit refuses
# 0041's notice `fields` this model distinguishes: a record's content (an edge's, an episode's), and the act content
# carriers (0041am v1.4)
CONTENT = {"replies.text", "replies.request_digest", "confirmations.request_digest"}
FULL_NOTICE = frozenset({"edges", "episodes", "request_registry.request_digest"} | CONTENT)   # this store's own map
OLD_NOTICE = frozenset({"edges"})                                                  # a notice older than replies


def canonical_uid(*parts) -> str:
    """The 0008 amendment §6e (research C-3): a JSON array of strings, never a separator join."""
    return hashlib.sha256(json.dumps([str(p) for p in parts], ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def internal_key(act_uid: tuple) -> str:
    """§6e INV-Q4′: `#` is outside the caller grammar, so an internal key can never be presented by a caller; it is a
    function of the act's portable identity, so it is the same on every hop."""
    return "#act:" + canonical_uid(*act_uid)[:32]


@dataclass
class Edge:
    id: str
    user: str
    relation: str
    obj: str
    att: str | None                    # §1–2: attested | not_attested | None (legacy) — written ONCE at insert
    ungrounded: bool = False           # 0019's flag: the MARKER, orthogonal to the axis
    source_episode: str | None = None  # "Add the link": written once at insert; NULL for legacy and default import
    active: bool = True
    author: str = "user"
    disclosure: str = "mentionable"
    origin: str = "local"
    procedural: bool = False           # 0037's floor (record_kind == "procedural" or basis set): no att, no g(e)
    valid_from: int = 0                # VALID time (0028), a clock of its own: when the fact held, never when it was written
    valid_to: int | None = None
    attv: str | None = None            # 0045 v1.9: the predicate version that produced `att`, written WITH it, immutable
    origin_store: str | None = None    # the store that first wrote the record (0041 I2b: records carry their origin);
                                       # RECORDED and compared by no rule (0041am v1.8: origin binding dropped)


@dataclass
class Episode:
    """A 0041 record a notice can target besides an edge (its content: the episode's text). Only what INV-RR14's
    record test needs: an episode is a record with a content carrier, admitted by 0009's collision rule."""
    id: str
    user: str
    text: str | None


@dataclass
class Notice:
    """A redaction notice as this store holds it (0041; 0041am v1.10 §4). Its BODY — id, target, fields, origin — is
    immutable (0041's discipline); `state` and `treated` are this store's judgement of it. `applied`: an attestation
    of what this store treated (`treated`); `pending`: held target, listed in notices_not_applied with `reason`;
    `standing`: names no record this store holds. A local redaction's notice has this store's origin (an OWN
    attestation); `treated` is what this store attests it treated, on any notice it applied."""
    id: str
    target: str
    fields: frozenset
    origin: str = "unknown"            # its source identity, recorded; compared by no rule
    state: str = "standing"
    reason: str | None = None
    treated: frozenset = frozenset()


@dataclass
class Reply:
    id: str
    edge: str
    kind: str                          # challenge | context | withdrawn-consent | resolve
    text: str
    pos: tuple | None = None           # (origin_store, act_seq) — the 0008 amendment §6f; None = legacy/unknown
    target: str | None = None
    origin: str = "local"              # the 0008 amendment: local | imported | restored — never upgraded
    user: str = "u"
    correlation_id: str | None = None
    recorded_correlation_id: str | None = None   # the ORIGINAL request's id (§6e), kept as evidence only
    act_uid: tuple | None = None                 # (origin_store, origin_user, origin_act_id), set once, carried
    request_digest: str | None = None
    target_uid: tuple | None = None              # a resolve's challenge as a PORTABLE reference (its act_uid), so a
                                                 # target is remapped by identity, never by a row id (0008am §6e)


@dataclass
class Confirmation:
    id: str
    edge: str
    pos: tuple | None = None           # (origin_store, act_seq) — what the wire carries (II R2-03); None = legacy
    confirmed_at: int = 0              # the CALLER's admitted date — never an order (II R2-03)
    origin: str = "local"
    user: str = "u"
    correlation_id: str | None = None
    recorded_correlation_id: str | None = None
    act_uid: tuple | None = None
    request_digest: str | None = None


@dataclass
class Store:
    origin: str = "store-A"                         # 0006 local_origin()
    act_counter: int = 0                            # §6f: store-wide, never reset — not even by erasure (C-2)
    edges: dict = field(default_factory=dict)
    replies: list = field(default_factory=list)
    confirmations: list = field(default_factory=list)
    redacted_episodes: set = field(default_factory=set)
    clock: int = 100
    counts: dict = field(default_factory=lambda: {"nonuser_ungrounded_refused": 0})
    registry: dict = field(default_factory=dict)   # THE REQUEST REGISTRY (the 0008 amendment): (user, correlation_id) ->
                                                   # (verb, request digest, result, target_edge_id) — one id space
    notices: dict = field(default_factory=dict)    # notice id -> Notice: every notice this store holds, any state
    episodes: dict = field(default_factory=dict)   # episode id -> Episode

    def tick(self):
        self.clock += 1
        return self.clock


@dataclass
class Rules:
    source_redacted_scope: str = "not_attested"   # the confirm() refusal: "not_attested" (drafted) | "all" (the uniform alternative)
    absorption_or: bool = True                    # draft 3 §7: the 0019/0014 OR rule kept (G2's verifier amendment withdrawn)


class Refused(Exception):
    pass


# ----------------------------------------------------------------------------------------------- §1–2 the axis
def grounding(s: Store, e: Edge, at: int | None = None) -> str | None:
    """g(e) = confirmed if any LOCAL or RESTORED confirmation exists (an imported one is testimony), else the STORED axis;
    NULL reads unknown. The axis never reads the 0019 flag (G3 by construction). `at` is VALID time and selects facts,
    never acts: a historical query reads the CURRENT acts (rules draft 3.4; 0047 INV-R20)."""
    if e.procedural:
        return None                                    # rules draft 3.3: declarative-only; 0037's basis grounds it
    if any(c.edge == e.id and c.origin in ("local", "restored") for c in s.confirmations):
        return "confirmed"
    return e.att or "unknown"


# ----------------------------------------------------------------------------------------------- §2a the write path
def user_effective(author: str, context: str | None) -> bool:
    """The owner's ruling (2026-10-11, "Only declared-direct calls"): USER-effective iff the effective author is USER AND
    the context is DECLARED direct — the product's own _resolve_context/_disclosure_for. Absence is never the trusted
    cell: `remember(author=USER)` with no context, and MCP at capability NONE, are NOT user-effective."""
    return author == "user" and context == "direct"


def write(s: Store, e: Edge, *, author: str, attested_by_predicate: bool, context: str | None = "direct"):
    """§2a ("Label, don't block"): a USER-effective statement is ALWAYS stored — attested only if the strict predicate
    recognised it, else not_attested. Anything else (non-user, or USER without a declared-direct context): flag UNSET →
    stored not_attested; flag SET → REFUSED, counted."""
    if _write_refused(s, e.id):
        raise Refused(f"local write of {e.id!r}: redacted here")       # 0041's local-writer refusal (applied only)
    if e.origin_store is None:
        e.origin_store = s.origin
    if e.procedural:
        e.att = e.attv = None                          # rules draft 3.3: ATTEST never runs on the procedural path;
        e.author = author                              # an att-less PROCEDURAL insert is admitted, never refused
        s.edges[e.id] = e
        return e
    if user_effective(author, context):
        e.att = "attested" if attested_by_predicate else "not_attested"
        e.attv = PREDICATE_VERSION                     # 0045 v1.9: WHAT produced `att` — the predicate that judged it
    elif e.ungrounded:
        s.counts["nonuser_ungrounded_refused"] += 1
        return None
    else:
        e.att = "not_attested"
        e.attv = NON_USER                              # the author rule decided; no predicate ran, so none is named
    e.author = author
    s.edges[e.id] = e
    return e


def add_episode(s: Store, ep: Episode) -> Episode:
    """0041's other local writer: refused on an id this store has REDACTED (an applied attestation) only."""
    if _write_refused(s, ep.id):
        raise Refused(f"local write of {ep.id!r}: redacted here")
    s.episodes[ep.id] = ep
    return ep


def _write_refused(s: Store, record_id: str) -> bool:
    """0041am v1.5: the two local-writer refusals count APPLIED attestations only; a pending or standing notice is not a
    redaction of anything this store holds."""
    return record_id in redacted_targets(s)


def redacted_targets(s: Store) -> set:
    """0041's redacted_targets(): the targets of APPLIED notices — never pending, never standing (INV-RR11/RR12)."""
    return {n.target for n in s.notices.values() if n.state == "applied"}


def notices_not_applied(s: Store) -> list:
    """0041am v1.5: every PENDING notice with its reason (`held-target`, `record-not-in-file`), as `doctor` lists them."""
    return sorted((n.id, n.reason) for n in s.notices.values() if n.state == "pending")


def coverage(s: Store, target: str) -> frozenset:
    """0008am v1.4 §6e: coverage counts EVERY notice for the target, whatever its state, and what this store attests it
    treated — its OWN attestations covering exactly the paths they attest (0041am v1.11, INV-RR6); it decides admission
    and equality only, and writes nothing."""
    out = frozenset()
    for n in s.notices.values():
        if n.target == target:
            out |= n.fields | n.treated
    return out


def why(s: Store, e: Edge) -> dict | None:
    """0045 v1.9 §4a: `why` names the label and the version that produced it, read FROM `attv`, never from the
    predicate this build runs; a row with no `attv` (legacy, or a file `att` restored without one) reads "version
    unknown"."""
    if e.procedural:
        return None
    return {"label": grounding(s, e), "version": e.attv if e.attv is not None else "version unknown"}


# ----------------------------------------------------------------------------------------------- §4 challenges
def active_challenges(s: Store, e: Edge, at: int | None = None) -> list:
    """The CURRENT open challenges. `at` (valid time) is accepted and IGNORED: acts are never filtered by T. Ordered by
    position within an origin; incomparable positions (another origin, legacy) fall back to the id — a display order
    only, never a decision (the restore rule reads `ordered_before`)."""
    rs = [r for r in s.replies if r.edge == e.id]
    resolved = {r.target for r in rs if r.kind == "resolve"}
    return sorted((r for r in rs if r.kind == "challenge" and r.id not in resolved),
                  key=lambda r: (r.pos or ("", 0), r.id))


def next_pos(s: Store) -> tuple:
    """§6f: every act write takes the next value of the store-wide counter, under the verb's write lock."""
    s.act_counter += 1
    return (s.origin, s.act_counter)


def ordered_before(a: tuple | None, b: tuple | None) -> bool | None:
    """§6f: True/False when both positions exist and share an origin_store; None (INCOMPARABLE) otherwise."""
    if a is None or b is None or a[0] != b[0]:
        return None
    return a[1] < b[1]


def held_at(e: Edge, T: int) -> bool:
    """0028's valid-time predicate: valid_from ≤ T < valid_to."""
    return e.valid_from <= T and (e.valid_to is None or T < e.valid_to)


def _replay(s: Store, user: str, correlation_id, verb: str, digest: str):
    """The request registry, read FIRST: same id + same verb + same request → the original result; the id held by ANY
    other verb or request → integrity conflict naming the holder (the 0008 amendment, INV-Q1/Q2)."""
    if correlation_id is None:
        return None
    rec = s.registry.get((user, correlation_id))
    if rec is None:
        return None
    if rec[1] == MARKER:                               # the request was redacted (0041am INV-RR5): terminal for its
        if rec[0] == verb:                             # own verb whatever the payload; the id stays held for others
            return REQUEST_REDACTED
        raise Refused(f"integrity conflict: correlation id held by {rec[0]}")
    if rec[0] == verb and rec[1] == digest:
        return rec[2]
    raise Refused(f"integrity conflict: correlation id held by {rec[0]}")


def _register(s: Store, user: str, correlation_id, verb: str, digest: str, result, target: str | None = None):
    """Every verb writes its registry row (with the edge it acted on: §6g, so a redaction can find it) in its own
    transaction; an omitted id is generated and takes a row too."""
    cid = correlation_id if correlation_id is not None else f"gen-{len(s.registry) + 1}"
    s.registry[(user, cid)] = (verb, digest, result, target)
    return cid


def _caller_id(cid):
    """§6c's format check at the host entry (C9): a caller id must match the grammar; `#act:` keys cannot."""
    if cid is not None and not CALLER_ID.fullmatch(cid):
        raise Refused(f"correlation_id {cid!r} outside the caller grammar")


def migrate_registry(s: Store):
    """The schema step: backfill one `confirm` row per existing LOCAL confirmation, so a pre-upgrade id conflicts on a
    reply (INV-Q3)."""
    for c in s.confirmations:
        if c.origin == "local" and c.correlation_id is not None:
            # 0041am INV-RR7: an already-redacted confirmation's row carries the marker, never a live digest
            dig = c.request_digest if c.request_digest is not None else f"confirm|{c.user}|{c.edge}"
            s.registry.setdefault((c.user, c.correlation_id), ("confirm", dig, c, c.edge))


def forget_user(s: Store, user: str):
    """User erasure (0008 §6d, amended; 0047 INV-R22): the user's edges, acts AND registry rows, atomically. Replay ends."""
    gone = {i for i, e in s.edges.items() if e.user == user}
    s.edges = {i: e for i, e in s.edges.items() if i not in gone}
    s.replies = [r for r in s.replies if r.user != user]
    s.confirmations = [c for c in s.confirmations if c.user != user]
    s.registry = {k: v for k, v in s.registry.items() if k[0] != user}
    # the store-wide act counter is NOT erased (§6f): a recreated user can never reissue an exported position


def redact_edge(s: Store, edge_id: str, *, covers_replies: bool = True, fields=None):
    """0041 + the 0041 amendment: a LOCAL redaction — this store's own notice, APPLIED, attesting what it treated. The
    edge's content, every reply's text, and EVERY request digest on it — in `confirmations`, `replies` and the registry
    (found by target_edge_id) — are REPLACED with the marker, in one transaction. A redaction treats exactly what its
    notice attests: `covers_replies=False` models an OLDER notice whose fields predate replies (the edge only); `fields`
    names any other (a partial one, for the coverage rule)."""
    f = frozenset(fields) if fields is not None else (FULL_NOTICE if covers_replies else OLD_NOTICE)
    _apply_notice(s, edge_id, f)
    nid = f"own:{s.origin}:{edge_id}:{sum(1 for n in s.notices.values() if n.target == edge_id) + 1}"
    s.notices[nid] = Notice(nid, edge_id, f, origin=s.origin, state="applied", treated=f)


def _apply_notice(s: Store, target: str, f: frozenset):
    """The TREATMENT of a redaction under fields `f`: every HELD carrier of the target that `f` names is replaced, the
    target's acts and registry rows included. It records no notice (the caller says whose redaction it is)."""
    e = s.edges.get(target)
    if e is not None and "edges" in f:
        e.relation, e.obj = MARKER, MARKER
    ep = s.episodes.get(target)
    if ep is not None and "episodes" in f and ep.text is not None:
        ep.text = MARKER
    for r in s.replies:
        if r.edge == target:
            if r.text is not None and "replies.text" in f:
                r.text = MARKER
            if "replies.request_digest" in f:
                r.request_digest = MARKER
    for c in s.confirmations:
        if c.edge == target and "confirmations.request_digest" in f:
            c.request_digest = MARKER
    if "request_registry.request_digest" in f:
        for k, v in list(s.registry.items()):
            if len(v) > 3 and v[3] == target:
                s.registry[k] = (v[0], MARKER, v[2], v[3])


def shows_redaction(record, fields: frozenset) -> bool:
    """0041am v1.10 §4 (`redaction.shows_redaction` is the shipped form): the record SHOWS the redaction when treating it
    under the notice's fields would change none of its record carriers — an edge's content under `edges`, an episode's
    text under `episodes`."""
    if isinstance(record, Episode):
        return "episodes" not in fields or record.text in (None, MARKER)
    return "edges" not in fields or (record.relation == MARKER and record.obj == MARKER)


def _apply_by_this_store(s: Store, n: Notice):
    """Applying a notice to a HELD target is a redaction BY THIS STORE (0041am v1.10 §4, 0008am v1.7 §6e): total over the
    target's carriers under this store's own treatment map, held acts not in any unit included, EVEN WHEN the notice is
    older or partial. This store attests what it treated; the notice's body is unchanged."""
    _apply_notice(s, n.target, FULL_NOTICE)
    n.state, n.reason, n.treated = "applied", None, FULL_NOTICE
    s.notices[n.id] = n


def confirm_notice(s: Store, user: str, notice_id: str) -> str:
    """0041am v1.5: the user's confirmation of a PENDING notice applies it as this store's total treatment. A pending
    notice whose target has since been deleted is inert; confirming one whose target this store has since redacted adds
    its attestation and treats nothing new (the treatment is idempotent)."""
    n = s.notices[notice_id]
    if n.state != "pending":
        raise Refused(f"notice {notice_id}: {n.state}, not pending")
    rec = s.edges.get(n.target) or s.episodes.get(n.target)
    if rec is None:
        return "inert"
    if rec.user != user:
        raise Refused(f"notice {notice_id}: not this user's record")
    _apply_by_this_store(s, n)
    return "applied"


def export(s: Store, user: str) -> tuple:
    """Edges and acts WITH their origin; never the registry (a request's replay belongs to its store)."""
    import copy
    return (copy.deepcopy([e for e in s.edges.values() if e.user == user]
                          + [ep for ep in s.episodes.values() if ep.user == user]),
            copy.deepcopy([c for c in s.confirmations if c.user == user]),
            copy.deepcopy([r for r in s.replies if r.user == user]))


def add_reply(s: Store, e: Edge, kind: str, text: str, target: str | None = None, correlation_id=None) -> Reply:
    _caller_id(correlation_id)
    digest = canonical_uid("add_reply", e.user, e.id, kind, text, target)   # the closed canonical request (corr. #5)
    rec = _replay(s, e.user, correlation_id, "reply", digest)
    if rec is not None:
        return rec
    if kind not in ("challenge", "context", "withdrawn-consent", "resolve"):
        raise Refused("kind outside the closed set")
    if text is not None and MARKER in text:
        raise Refused("a marker in an ordinary reply")
    if MARKER in (e.relation, e.obj):
        raise Refused("reply to a redacted edge")
    if e.procedural:
        raise Refused("store.reply.procedural-edge")   # 0047 v1.4 ruling (1); a procedural right of reply deferred (R6)
    if kind == "resolve":
        c = next((r for r in s.replies if r.id == target), None)
        if c is None or c.edge != e.id or c.kind != "challenge":
            raise Refused("resolve must name a challenge of the same edge")
        if any(r.kind == "resolve" and r.target == target for r in s.replies):
            raise Refused("challenge already resolved")
    s.tick()
    r = Reply(id=f"r{len(s.replies) + 1}", edge=e.id, kind=kind, text=text, pos=next_pos(s), target=target, user=e.user,
              request_digest=digest)
    r.act_uid = (s.origin, e.user, r.id)
    if target is not None:
        r.target_uid = next(x.act_uid for x in s.replies if x.id == target)
    r.correlation_id = _register(s, e.user, correlation_id, "reply", digest, r, e.id)
    s.replies.append(r)
    return r


def undo(s: Store, e: Edge, outcome_ref: str, correlation_id=None):
    """0044's `undo` as a verb of THIS registry only (0008am v1.3 §6g; INV-Q7 for the third verb): its request takes a
    registry row naming the edge it acted on, replays from the registry, and is TERMINAL after that edge's redaction.
    What it undoes (0044's outcome and episode) is model I's, not represented here: the result is a token."""
    _caller_id(correlation_id)
    digest = canonical_uid("undo", e.user, e.id, outcome_ref)
    rec = _replay(s, e.user, correlation_id, "undo", digest)
    if rec is not None:
        return rec
    s.tick()
    result = ("undone", outcome_ref, next_pos(s))          # an undo write is an act write: it takes a position (§6f)
    _register(s, e.user, correlation_id, "undo", digest, result, e.id)
    return result


# ----------------------------------------------------------------------------------------------- §5 the gate
def gate(s: Store, e: Edge, existing_ok: bool = True, at: int | None = None) -> str:
    """Additional restriction only. Unchallenged: assertable (every grounding value; not_attested is today's line).
    Challenged: not_assertable for every grounding value (0047 v1.8 §4c, the owner's option 3)."""
    if not existing_ok or (at is not None and not held_at(e, at)):
        return "not_assertable"
    if active_challenges(s, e, at):
        return "not_assertable"            # 0047 v1.8 §4c (the owner, 2026-10-12, option 3): no value survives a challenge
    return "assertable"


def render(s: Store, e: Edge, budget: int, at: int | None = None) -> str | None:
    """An ASSERTION surface (recall detail, contested, proactive, as-of — 0047 v1.8 §4d): a fact the gate refuses is
    WITHHELD at every budget; the 0019 marker follows the FLAG, whatever the axis. Under an active challenge no value
    reaches this surface (§4c, the owner's option 3), so the unit is never rendered here."""
    if gate(s, e, at=at) == "not_assertable":
        return None
    line = f"{e.relation}: {e.obj}" + (" [possible extraction error]" if e.ungrounded else "")
    return line if len(line) <= budget else None


def inspect(s: Store, e: Edge, budget: int | None = None) -> dict:
    """Where the record is INSPECTED (why, introspect, structured returns — §4d): g(e), the open count over ALL active
    challenges (computed before any budget selection, INV-R6), and the unit. A budget trims only the reply EXCERPTS
    shown, never the count."""
    ch = active_challenges(s, e)
    shown, room = [], budget
    for c in reversed(ch):
        t = (c.text or "")[:20]
        if room is not None and len(t) > room:
            break
        shown.append(t)
        room = None if room is None else room - len(t)
    unit = f"[challenged by the subject: {len(ch)} open; latest: {shown[0] if shown else ''}]" if ch else None
    return {"g": grounding(s, e), "open": len(ch), "unit": unit, "excerpts": shown}


# ----------------------------------------------------------------------------------------------- confirmation (0008)
def confirm(s: Store, e: Edge, rules: Rules, correlation_id=None, date: int = 0):
    """0008's confirm(), as rules draft 3.4 and the 0008 amendment leave it: the request registry is read FIRST (a retry
    replays even after the edge changed); then refused while a challenge is open; refused for a
    not_attested edge (scope per Rules) whose RECORDED source episode is redacted — "state it anew"."""
    _caller_id(correlation_id)
    digest = canonical_uid("confirm", e.user, e.id)
    rec = _replay(s, e.user, correlation_id, "confirm", digest)
    if rec is not None:
        return rec
    if active_challenges(s, e):
        raise Refused("store.confirm.active-challenge")
    scoped = rules.source_redacted_scope == "all" or grounding(s, e) == "not_attested"
    if scoped and e.source_episode is not None and e.source_episode in s.redacted_episodes:
        raise Refused("store.confirm.source-redacted: state it anew")
    if correlation_id is not None and any(k.user == e.user and k.correlation_id == correlation_id for k in s.confirmations):
        raise Refused("UNIQUE(user_id, correlation_id) on confirmations")   # the second belt, kept exactly as it is
    s.tick()
    c = Confirmation(id=f"k{len(s.confirmations) + 1}", edge=e.id, pos=next_pos(s), user=e.user, request_digest=digest,
                     confirmed_at=date)
    c.act_uid = (s.origin, e.user, c.id)
    c.correlation_id = _register(s, e.user, correlation_id, "confirm", digest, c, e.id)
    s.confirmations.append(c)
    return c


# ----------------------------------------------------------------------------------------------- §7 identity transitions
def absorb(s: Store, prior: Edge, incoming: Edge, rules: Rules) -> str:
    """§7: refused when the prior carries a confirmation or a reply; otherwise the survivor's AXIS is the incoming's own
    (never laundered from the prior), and its 0019 flag is the OR (kept: it only adds a marker)."""
    acts = any(c.edge == prior.id for c in s.confirmations) or any(r.edge == prior.id for r in s.replies)
    s.edges[incoming.id] = incoming
    if acts:
        return "not_absorbed"
    prior.active = False
    if rules.absorption_or and prior.ungrounded:
        incoming.ungrounded = True
    return "absorbed"


# ----------------------------------------------------------------------------------------------- §8 import
_TEXT, _DIGEST = 4, 5                                  # the content carriers' places in the projection


def _proj(row) -> tuple:
    """§6e's canonical comparison projection: act_uid, the portable edge, kind, the portable target, the content
    carriers (text, request_digest), the ORIGINAL request id, the position and `confirmed_at` as stored. It EXCLUDES
    every destination-internal field (row id, internal key, registry state) and the TRUST LABEL: `origin` is the
    destination's own judgement at first admission and legitimately differs hop to hop (v1.3, the reviewer's
    recorded-origin carrier closed by normalization, not by a column)."""
    return (row.act_uid, row.edge, getattr(row, "kind", "confirm"), _target_ref(row), getattr(row, "text", None),
            row.request_digest, _original_id(row), row.pos, getattr(row, "confirmed_at", None))


def _target_ref(row):
    """A target as a PORTABLE reference: the challenge's act_uid where known, else the row id the act was made with."""
    t = getattr(row, "target_uid", None)
    return t if t is not None else getattr(row, "target", None)


def _original_id(row):
    """§6e: `recorded_correlation_id` is the ORIGINAL request's id — the file's recorded one when the row was already
    imported once, else the file's own id when the file row is `local`. An internal `#act:` key is never an original
    request id: an act sent with none has none on every hop (round 4: falling back to the key made an admitted copy
    differ from its own repeat, so a repeat import of such a row refused as a conflicting replay)."""
    if row.recorded_correlation_id is not None:
        return row.recorded_correlation_id
    cid = row.correlation_id
    return None if cid is not None and cid.startswith("#act:") else cid


def _carriers(row) -> dict:
    """A row's non-NULL CONTENT carriers, by 0041 carrier path (0008am v1.3 §6e)."""
    out = ({"replies.text": row.text, "replies.request_digest": row.request_digest} if isinstance(row, Reply)
           else {"confirmations.request_digest": row.request_digest})
    return {k: v for k, v in out.items() if v is not None}


_ATTR = {"replies.text": "text", "replies.request_digest": "request_digest",
         "confirmations.request_digest": "request_digest"}
_PLACE = {"replies.text": _TEXT, "replies.request_digest": _DIGEST, "confirmations.request_digest": _DIGEST}


def _treated(row, cov) -> tuple:
    """The canonical TREATED projection under a coverage: every content carrier the coverage attests compares as the
    marker; every other field as it is."""
    p = list(_proj(row))
    for path in _carriers(row):
        if path in cov:
            p[_PLACE[path]] = MARKER
    return tuple(p)


def _same_act(held, row, cov) -> bool:
    """Rule 1 against rule 2 (v1.3, R3-01): one act_uid is an EXACT REPLAY iff the canonical treated projections are
    equal — so a treated held row and an untreated arriving copy of the same act are one act."""
    return _treated(held, cov) == _treated(row, cov)


def _transition(held, row, cov):
    """The ONE authorized transition: an arriving copy whose covered content carriers are the marker gives the held
    copy the treatment its notice attests. Content carriers only: a structural difference never reaches here (it is a
    conflicting replay, rule 2)."""
    for path, v in _carriers(row).items():
        if v == MARKER and path in cov:
            setattr(held, _ATTR[path], MARKER)


def _write_treated(row, cov):
    """Rule 4: an admitted act is written treated wherever the coverage attests its carriers."""
    for path in _carriers(row):
        if path in cov:
            setattr(row, _ATTR[path], MARKER)


def _coverage_ok(row, target: Edge, cov):
    """Coverage is all or nothing per row (v1.3; 0041am INV-RR6/RR9): a carrier holding the marker must be attested
    (else it is a fabricated tombstone), and onto a REDACTED target every non-NULL content carrier must be attested — a
    carrier the notice does not attest is never treated in its name, and the notice is never enlarged."""
    car = _carriers(row)
    if any(v == MARKER and path not in cov for path, v in car.items()):
        raise Refused(f"a marker carrier with no notice attesting it ({row.id})")
    redacted = bool(cov) or MARKER in (target.relation, target.obj)
    if redacted and not set(car) <= set(cov):
        raise Refused(f"act {row.id}: its target's notices attest {sorted(set(cov) & CONTENT)}, not all of {sorted(car)}")


def _identity(held_map: dict, staged: dict, uid):
    """HELD is the STAGED UNION (v1.3): the destination's acts AND every earlier row of this unit."""
    if uid is None:
        return None
    return staged.get(uid) or held_map.get(uid)


def _norm_notices(notices) -> list:
    """An arriving unit's notices, as fresh Notice bodies: a Notice; {target: fields}; or a bare target id (a notice
    made by this version, every field). A body's id is a function of its target and fields, so a repeat is `existing`."""
    import copy
    out = []
    items = notices.items() if isinstance(notices, dict) else [(x, None) for x in notices]
    for k, v in items:
        if isinstance(k, Notice):
            n = copy.deepcopy(k)
            out.append(Notice(n.id, n.target, frozenset(n.fields), origin=n.origin))      # this store's view: fresh
            continue
        f = frozenset(v) if v is not None else FULL_NOTICE
        out.append(Notice("n:" + canonical_uid(k, *sorted(f))[:16], k, f))
    return out


@dataclass
class Effect:
    """What one notice does at one import (0041am v1.10 §4's one table), as data the executor applies."""
    refuse: str | None = None          # the whole import refused, and why
    state: str | None = None           # applied | pending | standing | None (keep what is held)
    reason: str | None = None          # a pending notice's reason in notices_not_applied
    treated: frozenset = frozenset()   # what this store attests it treated, for an applied notice
    write_treated: bool = False        # a record this import creates is written in the attestation's treated shape
    by_store: bool = False             # a redaction BY THIS STORE: total over the held target's carriers


def _notice_effect(n: Notice, prev: Notice | None, rec, held_rec, mode: str) -> Effect:
    """0041am v1.10 §4: a notice takes effect only where a record SHOWS the redaction, an import that would land content
    under it is refused, and the rest is decided by the target's state and the mode. `rec` is the unit's copy of the
    target's record (None: no copy); `held_rec` the record held BEFORE this import (None: the import creates it, or it
    is absent); `prev` the notice as this store already holds it (a repeat; or a held STANDING notice meeting an
    arrival). No rule reads the notice's origin.
    A notice this store already holds PENDING, met again by a default import that would leave it pending, is
    `existing`: the held row and its reason are kept (0041am v1.13 §4; round-4 IO-II-1 — the table alone rewrote
    `record-not-in-file` / `standing-arrival` to `held-target`). Refusals and applications are the table's, unchanged."""
    e = _notice_table(n, prev, rec, held_rec, mode)
    if mode == "default" and prev is not None and prev.state == "pending" and e.state == "pending":
        return Effect()                                # `existing`: the held pending row, reason included
    return e


def _notice_table(n: Notice, prev: Notice | None, rec, held_rec, mode: str) -> Effect:
    """The one table of 0041am v1.10 §4, before the repeated-pending rule `_notice_effect` applies over it."""
    if prev is not None and prev.state == "applied":
        if rec is not None and not shows_redaction(rec, n.fields):
            return Effect(write_treated=True)          # `existing`: the arrival written in the attestation's shape
        return Effect()                                # `existing`
    if prev is not None and prev.state == "standing" and held_rec is not None:
        return Effect()                                # a locally written id is never completed by a later import
    if rec is not None and not shows_redaction(rec, n.fields):
        if held_rec is None:                           # created: content would land under the notice, both modes
            return Effect(refuse=f"notice {n.id}: the unit carries its target {n.target!r} unredacted")
        if mode == "default":
            return Effect(state="pending", reason="held-target")
        return Effect(refuse=f"notice {n.id}: a restore carrying its held target {n.target!r} unredacted")
    if rec is not None:                                # the unit's record SHOWS the redaction
        if held_rec is None:
            if prev is not None and prev.state == "standing" and mode == "default":
                return Effect(state="pending", reason="standing-arrival")   # an untrusted file's word: the user decides
            return Effect(state="applied", treated=n.fields)   # created: it attests what arrived treated
        if mode == "default":
            return Effect(state="pending", reason="held-target")
        return Effect(state="applied", by_store=True)
    if held_rec is not None:                           # no copy in the unit, the target held
        if mode == "default":
            return Effect(state="pending", reason="held-target")
        if shows_redaction(held_rec, n.fields):        # (v1.11) TOTAL: the record changes nothing, held acts still
            return Effect(state="applied", by_store=True)   # carrying content are treated (INV-RR5)
        return Effect(state="pending", reason="record-not-in-file")
    return Effect(state="standing") if prev is None else Effect()


def _held_differs(noticed: bool, attested: bool) -> str:
    """0041am v1.11–v1.12 (measured, §2c-ii row 12; research 91b87bde): 0009 compares the CAPPED incoming form. Where it
    differs from the held record: a notice for it in the unit → 0041 §4g's held-differs rule runs FIRST, the copy is
    skipped (never written) and the notice weighed by the table; no notice, and the record is under this store's
    COMPLETED attestation → INV-11 refuses, reason `attested-redaction` (a default import's capped form of a store's own
    record always differs; a restore's content-changed copy too); otherwise 0009 refuses. An EQUAL form is a no-op."""
    if noticed:
        return "skip"
    return "attested-redaction" if attested else "refuse"


def _arrival_under_attestation(rec, applied: list):
    """Accepted 0041 §4b-ii / INV-11: an arrival under this store's COMPLETED attestation with no notice for it in the
    unit is refused — `existing` (the R10-02 treated write) needs the notice in the unit."""
    raise Refused(f"record {rec.id!r} is redacted here and the unit carries no notice for it (0041 INV-11)")


def _meets_on_arrival(n: Notice) -> bool:
    """Which held notices an arrival of their target re-weighs: STANDING ones only. An import that re-creates a PENDING
    notice's target leaves it pending (0041am v1.11); only confirm_notice or its own re-arrival in a restore applies it."""
    return n.state == "standing"


def _record_pending(tx: Store, n: Notice, reason: str):
    """A PENDING notice: its body kept, listed in notices_not_applied; it writes no held content."""
    n.state, n.reason = "pending", reason
    tx.notices[n.id] = n


def _transition_allowed(mode: str, target: str, tx: Store) -> bool:
    """0008am v1.4 §6e: the authorized transition happens only where the notice is APPLIED — a trusted restore (or the
    user's confirm_notice); in a default import a treated arrival over a held untreated copy is an exact replay."""
    return mode != "default" and target in redacted_targets(tx)


def _treat_record(rec, f: frozenset):
    if isinstance(rec, Episode):
        if "episodes" in f and rec.text is not None:
            rec.text = MARKER
    elif "edges" in f:
        rec.relation, rec.obj = MARKER, MARKER


def _unit_ids_ok(rows: list):
    """0008am v1.3 §6e: a file row id that names two rows of one unit refuses it, unless the two are byte-identical (one
    row twice) — every reference in the unit is remapped through those ids, so a repeated one would be ambiguous."""
    seen = {}
    for row in rows:
        prev = seen.get(row.id)
        if prev is not None and not (type(prev) is type(row) and vars(prev) == vars(row)):
            raise Refused(f"file row id {row.id!r} names two different rows of one unit")
        seen[row.id] = row


def _file_uid(row) -> tuple:
    """A row's identity: its act_uid, or for a row the file sent without one, the uid it is admitted under."""
    return row.act_uid if row.act_uid is not None else (row.pos[0] if row.pos else "unknown", row.user, row.id)


def import_rows(s: Store, edges: list, confirmations: list, replies: list, mode: str, notices=()):
    """§8 + the 0008 amendment v1.3 §6e–§6f + the 0041 amendment v1.4, as one atomic unit (any refusal writes nothing),
    preflighted over the STAGED UNION. Per arriving act: rule 0 (C-1) a DEFAULT file may not claim this store's
    origin; then coverage (all or nothing per row); rule 1 an act_uid held in the union with an equal canonical
    TREATED projection is an exact replay (a no-op, or the one authorized transition); rule 2 held, differing →
    refuse; rule 3 a NEW act over an edge held BEFORE this import, in default mode → refuse (the one rule that reads the
    destination alone); rule 4 admit, origin per the matrix, an internal key from act_uid, no registry row, written
    treated where the coverage attests it, its row id remapped where the destination already uses it. A file row id that
    names two different rows refuses the unit. Notices (0041am v1.10 §4): each arriving notice, and each held STANDING
    one an arrival meets, is decided by _notice_effect BEFORE anything is written; records are compared under the
    coverage of every notice and never treated in place by an unapplied one. Then resolve references are remapped by
    identity inside H, and chronology is validated over the merged history (§6f)."""
    import copy
    tx = copy.deepcopy(s)
    before = set(tx.edges)                                      # rule 3 reads the destination BEFORE the import
    held_records = {**tx.edges, **tx.episodes}
    arriving = _norm_notices(notices)
    afields = {}
    for n in arriving:
        afields[n.target] = afields.get(n.target, frozenset()) | n.fields

    def cov(eid):                     # coverage: every notice held before this unit, whatever its state, and the
        return coverage(s, eid) | afields.get(eid, frozenset())          # arriving bodies; it writes nothing

    recs = {}
    for e in edges:                                   # the unit's records, as the destination would admit them
        if isinstance(e, Edge) and e.attv is not None and not ATTV.fullmatch(e.attv):
            raise Refused(f"edge {e.id!r}: attv {e.attv!r} outside its grammar")
        e2 = copy.deepcopy(e)
        if mode == "default" and isinstance(e2, Edge):
            e2.att, e2.source_episode, e2.attv = "not_attested", None, DEFAULT_IMPORT
            e2.author, e2.disclosure, e2.origin = "third_party", "use_only", "imported"
        recs[e2.id] = e2
    effects = []                                      # decide every notice BEFORE any write (one transaction)
    for n in arriving:
        effects.append((n, tx.notices.get(n.id), _notice_effect(n, tx.notices.get(n.id), recs.get(n.target),
                                                                 held_records.get(n.target), mode)))
    met = {n.id for n in arriving}
    for n in list(tx.notices.values()):               # a held STANDING notice meets a record now present
        if _meets_on_arrival(n) and n.id not in met and (n.target in recs or n.target in held_records):
            effects.append((n, n, _notice_effect(n, n, recs.get(n.target), held_records.get(n.target), mode)))
    for n, prev, eff in effects:
        if eff.refuse:
            raise Refused(eff.refuse)
    for e2 in recs.values():                          # 0009 §4c kept, under the coverage; a held record never changes
        c = cov(e2.id)
        store_of = tx.episodes if isinstance(e2, Episode) else tx.edges
        held = store_of.get(e2.id)
        if held is not None:                          # 0009 compares the CAPPED incoming form, as is (0041am v1.11)
            if vars(held) != vars(e2):
                attested = any(x.target == e2.id and x.state == "applied" for x in tx.notices.values())
                verdict = _held_differs(e2.id in afields, attested)
                if verdict == "attested-redaction":
                    raise Refused(f"record {e2.id!r}: attested-redaction — redacted here, and the unit carries no notice "
                                  f"for it (0041 §4b-ii, INV-11; §4g's held-differs verdict)")
                if verdict == "refuse":
                    raise Refused(f"record {e2.id!r} already held with different content (0009 §4c)")
            continue                                  # equal, or noticed: skipped, never written (0041 §4g)
        applied = [x for x in tx.notices.values() if x.target == e2.id and x.state == "applied"]
        if applied and e2.id not in afields:          # accepted 0041 §4b-ii / INV-11: no notice for it in the unit
            _arrival_under_attestation(e2, applied)
        if any(eff.write_treated for n, _p, eff in effects if n.target == e2.id):
            _treat_record(e2, frozenset().union(*(x.fields | x.treated for x in applied)) if applied else FULL_NOTICE)
        store_of[e2.id] = e2
    for n, prev, eff in effects:                      # the notices' own effects, in the same transaction
        held_n = prev if prev is not None else n
        if eff.by_store:
            _apply_by_this_store(tx, held_n)
        elif eff.state == "pending":
            _record_pending(tx, held_n, eff.reason)
        elif eff.state is not None:
            held_n.state, held_n.reason = eff.state, None
            if eff.state == "applied":
                held_n.treated = eff.treated
            tx.notices[held_n.id] = held_n
    _unit_ids_ok(confirmations + replies)
    held_map = {a.act_uid: a for a in tx.confirmations + tx.replies if a.act_uid is not None}
    used = {a.id for a in tx.confirmations + tx.replies}
    staged, new, replayed, by_file_id = {}, [], [], {}
    for row in confirmations + replies:
        if row.edge not in tx.edges:
            raise Refused(f"orphan act {row.id}")
        if mode == "default" and ((row.act_uid and row.act_uid[0] == tx.origin) or (row.pos and row.pos[0] == tx.origin)):
            raise Refused(f"a default file claims this store's origin ({row.id})")           # rule 0 (C-1)
        c = cov(row.edge)
        _coverage_ok(row, tx.edges[row.edge], c)
        held = _identity(held_map, staged, _file_uid(row))
        if held is not None:
            if _same_act(held, row, c):
                if _transition_allowed(mode, row.edge, tx):
                    _transition(held, row, c)
                replayed.append(held); by_file_id[row.id] = held
                continue                                                                  # rule 1: exact replay
            raise Refused(f"act {row.id}: a held act_uid with a different projection")      # rule 2
        if row.edge in before and mode == "default":
            raise Refused(f"an untrusted file acting on a local edge ({row.id})")          # rule 3
        r2 = copy.deepcopy(row)
        r2.origin = "imported" if mode == "default" else ("restored" if row.origin == "local" else row.origin)
        r2.recorded_correlation_id = _original_id(row)
        r2.act_uid = _file_uid(row)
        r2.correlation_id = internal_key(r2.act_uid)
        _write_treated(r2, c)
        if r2.id in used:                                    # id remapping: the destination's own row keeps its id
            n = 1
            while f"{row.id}~{n}" in used:
                n += 1
            r2.id = f"{row.id}~{n}"
        used.add(r2.id)
        staged[r2.act_uid] = r2; new.append(r2); by_file_id[row.id] = r2
    for r2 in new:                                   # resolve references remapped and resolved inside H BEFORE deciding
        if isinstance(r2, Reply) and r2.kind == "resolve":
            tuid = r2.target_uid if r2.target_uid is not None else getattr(by_file_id.get(r2.target), "act_uid", None)
            ch = _identity(held_map, staged, tuid)
            if not isinstance(ch, Reply) or ch.kind != "challenge" or ch.edge != r2.edge:
                raise Refused(f"resolve {r2.id}: names no challenge of its edge in the merged history")
            r2.target, r2.target_uid = ch.id, ch.act_uid
    tx.confirmations += [r for r in new if isinstance(r, Confirmation)]
    tx.replies += [r for r in new if isinstance(r, Reply)]
    _chronology(tx, new, replayed)
    s.__dict__.update(tx.__dict__)


# ----------------------------------------------------------------------------------------------- §6f chronology over H
def _chronology(tx: Store, new: list, replayed: list):
    """0008am v1.3 §6f over the merged history H (the staged union's acts, references already remapped): ties, resolve
    validity, and every challenge/confirmation pair of one edge of which at least one member is NEW (admitted by rule 4)
    — an incoming challenge is judged against a HELD confirmation as much as the reverse. A replay exempts only itself."""
    fresh = {id(a) for a in new}
    resolves = {}
    for r in tx.replies:
        if r.kind == "resolve" and r.target is not None:
            resolves.setdefault(r.target, []).append(r)
    _ties(tx.confirmations + tx.replies, fresh)
    _resolves_valid(tx, resolves, fresh)
    _pairs(tx, resolves, fresh)


def _ties(acts: list, fresh: set):
    """Two different acts at one position refuse the unit: the counter never issues a position twice."""
    seen = {}
    for a in acts:
        if a.pos is None:
            continue
        for b in seen.get(a.pos, []):
            if (id(a) in fresh or id(b) in fresh) and a.act_uid != b.act_uid:
                raise Refused(f"two acts at one position {a.pos} ({b.id}, {a.id})")
        seen.setdefault(a.pos, []).append(a)


def _resolves_valid(tx: Store, resolves: dict, fresh: set):
    """A challenge is resolved at most once in H, and a resolve ordered before its own challenge refuses the unit."""
    by_id = {r.id: r for r in tx.replies}
    for cid, rs in resolves.items():
        c = by_id.get(cid)
        if not (any(id(r) in fresh for r in rs) or (c is not None and id(c) in fresh)):
            continue
        if len(rs) > 1:
            raise Refused(f"challenge {cid} resolved more than once in the merged history")
        if c is not None and ordered_before(rs[0].pos, c.pos) is True:
            raise Refused(f"resolve {rs[0].id} ordered before its challenge {cid}")


def _pairs(tx: Store, resolves: dict, fresh: set):
    """§6f's table, read over H. Ordered k < c: consistent. Ordered c < k: refused unless a resolve of c precedes k.
    Not ordered (another origin, an unknown position): refused unless c is resolved in H."""
    challenges = [r for r in tx.replies if r.kind == "challenge"]
    for k in tx.confirmations:
        for c in challenges:
            if c.edge != k.edge or (id(k) not in fresh and id(c) not in fresh):
                continue
            o = ordered_before(k.pos, c.pos)
            if o is True:
                continue
            rs = resolves.get(c.id, [])
            if o is False:
                if not any(ordered_before(r.pos, k.pos) is True for r in rs):
                    raise Refused(f"confirmation {k.id}: made under challenge {c.id}, unresolved in the merged history")
            elif not rs:
                raise Refused(f"confirmation {k.id}: its order against open challenge {c.id} cannot be established")
