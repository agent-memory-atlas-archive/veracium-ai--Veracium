"""Reference model for package II (0045 grounding × 0047 replies × confirmations): research's
GROUNDING-REPLY-TRANSITIONS-DRAFT draft 3.4 (research 12142443, sha16 b697bda6), the 0008 amendment
`0047/0008-request-registry` (the request registry, act origin, user erasure), with the owner's 2026-10-11 rulings
"Label, don't block" and "Add the link" (an edge records its source episode), executed.

A MODEL, not product code: no `veracium` import. One function per rule section. Ambiguities and the alternatives the
owner rejected are named switches (`Rules`); the run executes them as mutants or probes, never silently.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MARKER = "\x00redacted\x00"


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
    t: int
    target: str | None = None
    origin: str = "local"              # the 0008 amendment: local | imported | restored — never upgraded
    user: str = "u"
    correlation_id: str | None = None
    recorded_correlation_id: str | None = None   # an imported/restored act's id from the file, kept as evidence only


@dataclass
class Confirmation:
    id: str
    edge: str
    t: int                             # COMMIT time (the store's clock), never valid time
    origin: str = "local"
    user: str = "u"
    correlation_id: str | None = None
    recorded_correlation_id: str | None = None


@dataclass
class Store:
    edges: dict = field(default_factory=dict)
    replies: list = field(default_factory=list)
    confirmations: list = field(default_factory=list)
    redacted_episodes: set = field(default_factory=set)
    clock: int = 100
    counts: dict = field(default_factory=lambda: {"nonuser_ungrounded_refused": 0})
    registry: dict = field(default_factory=dict)   # THE REQUEST REGISTRY (the 0008 amendment): (user, correlation_id) ->
                                                   # (verb, request digest, result) — one id space for every verb
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
    """The CURRENT open challenges. `at` (valid time) is accepted and IGNORED: acts are never filtered by T."""
    rs = [r for r in s.replies if r.edge == e.id]
    resolved = {r.target for r in rs if r.kind == "resolve"}
    return sorted((r for r in rs if r.kind == "challenge" and r.id not in resolved), key=lambda r: (r.t, r.id))


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
    if rec[0] == verb and rec[1] == digest:
        return rec[2]
    raise Refused(f"integrity conflict: correlation id held by {rec[0]}")


def _register(s: Store, user: str, correlation_id, verb: str, digest: str, result):
    """Every verb writes its registry row in its own transaction; an omitted id is generated and takes a row too."""
    cid = correlation_id if correlation_id is not None else f"gen-{len(s.registry) + 1}"
    s.registry[(user, cid)] = (verb, digest, result)
    return cid


def migrate_registry(s: Store):
    """The schema step: backfill one `confirm` row per existing LOCAL confirmation, so a pre-upgrade id conflicts on a
    reply (INV-Q3)."""
    for c in s.confirmations:
        if c.origin == "local" and c.correlation_id is not None:
            s.registry.setdefault((c.user, c.correlation_id), ("confirm", f"confirm|{c.user}|{c.edge}", c))


def forget_user(s: Store, user: str):
    """User erasure (0008 §6d, amended; 0047 INV-R22): the user's edges, acts AND registry rows, atomically. Replay ends."""
    gone = {i for i, e in s.edges.items() if e.user == user}
    s.edges = {i: e for i, e in s.edges.items() if i not in gone}
    s.replies = [r for r in s.replies if r.user != user]
    s.confirmations = [c for c in s.confirmations if c.user != user]
    s.registry = {k: v for k, v in s.registry.items() if k[0] != user}


def export(s: Store, user: str) -> tuple:
    """Edges and acts WITH their origin; never the registry (a request's replay belongs to its store)."""
    import copy
    return (copy.deepcopy([e for e in s.edges.values() if e.user == user]),
            copy.deepcopy([c for c in s.confirmations if c.user == user]),
            copy.deepcopy([r for r in s.replies if r.user == user]))


def add_reply(s: Store, e: Edge, kind: str, text: str, target: str | None = None, correlation_id=None) -> Reply:
    digest = f"add_reply|{e.user}|{e.id}|{kind}|{text}|{target}"
    rec = _replay(s, e.user, correlation_id, "reply", digest)
    if rec is not None:
        return rec
    if kind not in ("challenge", "context", "withdrawn-consent", "resolve"):
        raise Refused("kind outside the closed set")
    if MARKER in text:
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
    r = Reply(id=f"r{len(s.replies) + 1}", edge=e.id, kind=kind, text=text, t=s.tick(), target=target, user=e.user)
    r.correlation_id = _register(s, e.user, correlation_id, "reply", digest, r)
    s.replies.append(r)
    return r


# ----------------------------------------------------------------------------------------------- §5 the gate
def gate(s: Store, e: Edge, existing_ok: bool = True, at: int | None = None) -> str:
    """Additional restriction only. Unchallenged: assertable (every grounding value; not_attested is today's line).
    Challenged: assertable ONLY if attested, and then only with the unit."""
    if not existing_ok or (at is not None and not held_at(e, at)):
        return "not_assertable"
    if active_challenges(s, e, at):
        return "assertable_with_unit" if grounding(s, e, at) == "attested" else "not_assertable"
    return "assertable"


def render(s: Store, e: Edge, budget: int, at: int | None = None) -> str | None:
    """§6: the mandatory unit or withheld; the 0019 marker follows the FLAG, whatever the axis; the count is all open
    challenges, computed before budget selection."""
    if gate(s, e, at=at) == "not_assertable":
        return None
    line = f"{e.relation}: {e.obj}" + (" [possible extraction error]" if e.ungrounded else "")
    ch = active_challenges(s, e, at)
    if ch:
        line += f" [challenged by the subject: {len(ch)} open; latest: {ch[-1].text[:20]}]"
    return line if len(line) <= budget else None


# ----------------------------------------------------------------------------------------------- confirmation (0008)
def confirm(s: Store, e: Edge, rules: Rules, correlation_id=None):
    """0008's confirm(), as rules draft 3.4 and the 0008 amendment leave it: the request registry is read FIRST (a retry
    replays even after the edge changed); then refused while a challenge is open; refused for a
    not_attested edge (scope per Rules) whose RECORDED source episode is redacted — "state it anew"."""
    digest = f"confirm|{e.user}|{e.id}"
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
    c = Confirmation(id=f"k{len(s.confirmations) + 1}", edge=e.id, t=s.tick(), user=e.user)
    c.correlation_id = _register(s, e.user, correlation_id, "confirm", digest, c)
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
def import_rows(s: Store, edges: list, confirmations: list, replies: list, mode: str, notices=()):
    """§8: default import writes att = not_attested and source_episode = NULL whatever the file says, and refuses acts
    aimed at PRE-EXISTING local edges; trusted restore writes as recorded. Preflighted against destination ∪ incoming.
    The 0041 amendment's reply rows (INV-RR3): a reply whose text is the marker is admitted only when its unit attests
    `replies.text` for its edge (a notice in the file, or one held); without one the unit is refused (a fabricated
    tombstone); an ordinary reply arriving under such a notice is written in its TREATED shape, the marker."""
    import copy
    local, incoming = set(s.edges), {e.id for e in edges}
    attested = set(notices) | s.notices
    for row in confirmations + replies:
        if row.edge not in local | incoming:
            raise Refused(f"orphan act {row.id}")
        if row.edge in local and mode == "default":
            raise Refused(f"an untrusted file acting on a local edge ({row.id})")
        if isinstance(row, Reply) and row.text == MARKER and row.edge not in attested:
            raise Refused(f"a marker reply with no notice attesting replies.text ({row.id})")
    for e in edges:
        e2 = copy.deepcopy(e)
        if mode == "default":
            e2.att, e2.source_episode = "not_attested", None
            e2.author, e2.disclosure, e2.origin = "third_party", "use_only", "imported"
        s.edges[e2.id] = e2
    s.notices |= set(notices)
    for n, row in enumerate(confirmations + replies):
        r2 = copy.deepcopy(row)
        # the 0008 amendment's origin rule (INV-Q5, 0047 INV-R21): default import writes `imported` whatever the file
        # says; trusted restore maps only local → restored and keeps `restored` and `imported` — never upgrades
        r2.origin = "imported" if mode == "default" else ("restored" if row.origin == "local" else row.origin)
        # INV-Q4: the file's id is evidence only; the act takes a store id and writes NO registry row
        r2.recorded_correlation_id, r2.correlation_id = row.correlation_id, f"imp-{len(s.confirmations) + len(s.replies) + n + 1}"
        if isinstance(r2, Reply) and r2.edge in attested and r2.text:
            r2.text = MARKER                                  # written in its treated shape (0041 L1400, extended)
        (s.confirmations if isinstance(r2, Confirmation) else s.replies).append(r2)
