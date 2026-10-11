"""Reference model for package II (0045 grounding × 0047 replies × confirmations): research's
GROUNDING-REPLY-TRANSITIONS-DRAFT draft 3.3 (research b06368d5, sha16 5cefe166) with the owner's 2026-10-11 rulings
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


@dataclass
class Reply:
    id: str
    edge: str
    kind: str                          # challenge | context | withdrawn-consent | resolve
    text: str
    t: int
    target: str | None = None
    origin: str = "local"


@dataclass
class Confirmation:
    id: str
    edge: str
    t: int
    origin: str = "local"


@dataclass
class Store:
    edges: dict = field(default_factory=dict)
    replies: list = field(default_factory=list)
    confirmations: list = field(default_factory=list)
    redacted_episodes: set = field(default_factory=set)
    clock: int = 100
    counts: dict = field(default_factory=lambda: {"nonuser_ungrounded_refused": 0})
    corr: dict = field(default_factory=dict)       # (user, correlation_id) -> (request digest, result): 0008's rule, one
                                                   # user-scoped id space shared by confirm() and add_reply() (INV-R15)

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
    """g(e) = confirmed if any confirmation (written at or before `at`), else the STORED axis; NULL reads unknown.
    The axis never reads the 0019 flag (G3 by construction)."""
    if e.procedural:
        return None                                    # rules draft 3.3: declarative-only; 0037's basis grounds it
    if any(c.edge == e.id and (at is None or c.t <= at) for c in s.confirmations):
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
    rs = [r for r in s.replies if r.edge == e.id and (at is None or r.t <= at)]
    resolved = {r.target for r in rs if r.kind == "resolve"}
    return sorted((r for r in rs if r.kind == "challenge" and r.id not in resolved), key=lambda r: (r.t, r.id))


def _replay(s: Store, user: str, correlation_id, digest: str):
    """0008's rule: same id + same request → the first result; same id + a DIFFERENT request (any verb) → refused."""
    if correlation_id is None:
        return None
    rec = s.corr.get((user, correlation_id))
    if rec is None:
        return None
    if rec[0] == digest:
        return rec
    raise Refused("integrity conflict: same correlation id, different request")


def add_reply(s: Store, e: Edge, kind: str, text: str, target: str | None = None, correlation_id=None) -> Reply:
    digest = f"add_reply|{e.user}|{e.id}|{kind}|{text}|{target}"
    rec = _replay(s, e.user, correlation_id, digest)
    if rec is not None:
        return rec[1]
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
    r = Reply(id=f"r{len(s.replies) + 1}", edge=e.id, kind=kind, text=text, t=s.tick(), target=target)
    s.replies.append(r)
    if correlation_id is not None:
        s.corr[(e.user, correlation_id)] = (digest, r)
    return r


# ----------------------------------------------------------------------------------------------- §5 the gate
def gate(s: Store, e: Edge, existing_ok: bool = True, at: int | None = None) -> str:
    """Additional restriction only. Unchallenged: assertable (every grounding value; not_attested is today's line).
    Challenged: assertable ONLY if attested, and then only with the unit."""
    if not existing_ok:
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
    """0008's confirm(), as rules draft 3.3 leaves it (with "Add the link"): refused while a challenge is open; refused for a
    not_attested edge (scope per Rules) whose RECORDED source episode is redacted — "state it anew"."""
    digest = f"confirm|{e.user}|{e.id}"
    rec = _replay(s, e.user, correlation_id, digest)
    if rec is not None:
        return rec[1]
    if active_challenges(s, e):
        raise Refused("store.confirm.active-challenge")
    scoped = rules.source_redacted_scope == "all" or grounding(s, e) == "not_attested"
    if scoped and e.source_episode is not None and e.source_episode in s.redacted_episodes:
        raise Refused("store.confirm.source-redacted: state it anew")
    c = Confirmation(id=f"k{len(s.confirmations) + 1}", edge=e.id, t=s.tick())
    s.confirmations.append(c)
    if correlation_id is not None:
        s.corr[(e.user, correlation_id)] = (digest, c)
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
def import_rows(s: Store, edges: list, confirmations: list, replies: list, mode: str):
    """§8: default import writes att = not_attested and source_episode = NULL whatever the file says, and refuses acts
    aimed at PRE-EXISTING local edges; trusted restore writes as recorded. Preflighted against destination ∪ incoming."""
    import copy
    local, incoming = set(s.edges), {e.id for e in edges}
    for row in confirmations + replies:
        if row.edge not in local | incoming:
            raise Refused(f"orphan act {row.id}")
        if row.edge in local and mode == "default":
            raise Refused(f"an untrusted file acting on a local edge ({row.id})")
    for e in edges:
        e2 = copy.deepcopy(e)
        if mode == "default":
            e2.att, e2.source_episode = "not_attested", None
            e2.author, e2.disclosure, e2.origin = "third_party", "use_only", "imported"
        s.edges[e2.id] = e2
    for row in confirmations + replies:
        r2 = copy.deepcopy(row); r2.origin = "imported" if mode == "default" else "restored"
        (s.confirmations if isinstance(r2, Confirmation) else s.replies).append(r2)
