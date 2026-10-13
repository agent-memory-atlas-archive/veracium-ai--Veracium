"""Reference model for package II (0045 grounding × 0047 replies × confirmations): research's
GROUNDING-REPLY-TRANSITIONS-DRAFT draft 3.4 (research 12142443, sha16 b697bda6), the 0008 amendment
`0047/0008-request-registry` (the request registry, act origin, user erasure), with the owner's 2026-10-11 rulings
"Label, don't block" and "Add the link" (an edge records its source episode), executed.

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
    recorded_origin: str | None = None           # the origin the file recorded (projection; the stored one is mapped)


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
    recorded_origin: str | None = None


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
    notices: set = field(default_factory=set)      # edge ids whose `replies.text` a HELD redaction notice attests (the 0041
                                                   # amendment `0047/0041-replies`: 0041's standing-notice rule)

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
    if e.procedural:
        e.att = None                                   # rules draft 3.3: ATTEST never runs on the procedural path;
        e.author = author                              # an att-less PROCEDURAL insert is admitted, never refused
        s.edges[e.id] = e
        return e
    if user_effective(author, context):
        e.att = "attested" if attested_by_predicate else "not_attested"
    elif e.ungrounded:
        s.counts["nonuser_ungrounded_refused"] += 1
        return None
    else:
        e.att = "not_attested"
    e.author = author
    s.edges[e.id] = e
    return e


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


def redact_edge(s: Store, edge_id: str, *, covers_replies: bool = True):
    """0041 + the 0041 amendment v1.3: the edge's content, every reply's text, and EVERY request digest on it — in
    `confirmations`, `replies` and the registry (found by target_edge_id) — are REPLACED with the marker, in one
    transaction. `covers_replies=False` models an OLDER notice whose fields predate replies (it attests the edge only)."""
    e = s.edges[edge_id]
    e.relation, e.obj = MARKER, MARKER
    for r in s.replies:
        if r.edge == edge_id:
            if r.text is not None:
                r.text = MARKER
            r.request_digest = MARKER
    for c in s.confirmations:
        if c.edge == edge_id:
            c.request_digest = MARKER
    for k, v in list(s.registry.items()):
        if len(v) > 3 and v[3] == edge_id:
            s.registry[k] = (v[0], MARKER, v[2], v[3])
    if covers_replies:
        s.notices.add(edge_id)


def export(s: Store, user: str) -> tuple:
    """Edges and acts WITH their origin; never the registry (a request's replay belongs to its store)."""
    import copy
    return (copy.deepcopy([e for e in s.edges.values() if e.user == user]),
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
    r.correlation_id = _register(s, e.user, correlation_id, "reply", digest, r, e.id)
    s.replies.append(r)
    return r


# ----------------------------------------------------------------------------------------------- §5 the gate
def gate(s: Store, e: Edge, existing_ok: bool = True, at: int | None = None) -> str:
    """Additional restriction only. Unchallenged: assertable (every grounding value; not_attested is today's line).
    Challenged: assertable ONLY if attested, and then only with the unit."""
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
def _proj(row) -> tuple:
    """§6e's canonical comparison projection: the act's portable fields, never a destination-internal one (row id,
    internal key, the stored origin mapping)."""
    return (row.act_uid, row.edge, getattr(row, "kind", "confirm"), getattr(row, "target", None),
            getattr(row, "text", None), row.request_digest, _original_id(row), row.recorded_origin or row.origin,
            row.pos, getattr(row, "confirmed_at", None))


def _original_id(row):
    """§6e: `recorded_correlation_id` is the ORIGINAL request's id — the file's recorded one when the row was already
    imported once, else the file's own id when the file row is `local`."""
    return row.recorded_correlation_id if row.recorded_correlation_id is not None else row.correlation_id


def import_rows(s: Store, edges: list, confirmations: list, replies: list, mode: str, notices=()):
    """§8 + the 0008 amendment §6e–§6f + the 0041 amendment v1.3, as one atomic unit (any refusal writes nothing):
    rule 0 (C-1): a DEFAULT file may not claim this store's origin; rule 1: an act whose act_uid is held here with an
    equal projection is an exact replay — a no-op that grants nothing; rule 2: held with a differing projection →
    refuse; rule 3: a NEW act over an edge held before this import, in default mode → refuse; rule 4: admit, origin per
    the matrix, an internal key derived from act_uid, no registry row. The restore chronology (INV-R23): an incoming
    confirmation onto an edge with an OPEN destination challenge is admitted only when ordered before it within one
    origin. Notice coverage (INV-RR6): an ordinary reply onto a target held redacted under a notice that does not cover
    `replies.text` refuses the unit."""
    import copy
    tx = copy.deepcopy(s)
    local, incoming = set(tx.edges), {e.id for e in edges}
    attested = set(notices) | tx.notices
    held_uids = {a.act_uid: a for a in tx.confirmations + tx.replies if a.act_uid is not None}
    for e in edges:                                   # 0009 §4c kept: record-equal skip, differing refuse
        e2 = copy.deepcopy(e)
        if mode == "default":
            e2.att, e2.source_episode = "not_attested", None
            e2.author, e2.disclosure, e2.origin = "third_party", "use_only", "imported"
        held = tx.edges.get(e2.id)
        if held is not None and vars(held) != vars(e2):
            raise Refused(f"edge {e2.id!r} already held with different content (0009 §4c)")
        tx.edges[e2.id] = e2
    tx.notices |= set(notices)
    replayed_targets = set()
    for row in confirmations + replies:
        if row.edge not in local | incoming:
            raise Refused(f"orphan act {row.id}")
        if mode == "default" and ((row.act_uid and row.act_uid[0] == tx.origin) or (row.pos and row.pos[0] == tx.origin)):
            raise Refused(f"a default file claims this store's origin ({row.id})")           # rule 0 (C-1)
        held = held_uids.get(row.act_uid) if row.act_uid is not None else None
        if held is not None:
            if _proj(held) == _proj(row):
                replayed_targets.add(row.edge)
                continue                                                                  # rule 1: exact replay
            raise Refused(f"act {row.id}: a held act_uid with a different projection")      # rule 2
        if row.edge in local and mode == "default":
            raise Refused(f"an untrusted file acting on a local edge ({row.id})")          # rule 3
        if isinstance(row, Reply):
            target = tx.edges[row.edge]
            held_redacted = MARKER in (target.relation, target.obj)
            if row.text == MARKER and row.edge not in attested:
                raise Refused(f"a marker reply with no notice attesting replies.text ({row.id})")
            if held_redacted and row.text not in (None, MARKER) and row.edge not in attested:
                raise Refused(f"a reply onto a target redacted under a notice that does not cover replies.text ({row.id})")
        if isinstance(row, Confirmation):
            for ch in active_challenges(tx, tx.edges[row.edge]):
                if ordered_before(row.pos, ch.pos) is not True:
                    raise Refused(f"confirmation {row.id}: not ordered before open challenge {ch.id}")   # INV-R23
        r2 = copy.deepcopy(row)
        r2.recorded_origin = row.recorded_origin or row.origin
        r2.origin = "imported" if mode == "default" else ("restored" if row.origin == "local" else row.origin)
        r2.recorded_correlation_id = _original_id(row)
        if r2.act_uid is None:
            r2.act_uid = (row.pos[0] if row.pos else "unknown", row.user, row.id)
        r2.correlation_id = internal_key(r2.act_uid)
        if isinstance(r2, Reply) and r2.edge in attested and r2.text:
            r2.text = MARKER                                  # written in its treated shape (0041 L1400, extended)
        (tx.confirmations if isinstance(r2, Confirmation) else tx.replies).append(r2)
    s.__dict__.update(tx.__dict__)
