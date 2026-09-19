"""specs/0042 (accepted v9.2) — the RUNTIME leg over the product's declared sites, per tranche.

The static scan says a binding exists; this executes ONE declining decision at every declared
site and asserts the id's counters MOVED BY EXACTLY ONE — Δconsulted == 1 and Δfired == 1 —
between a before and an after (a LEVEL is the proxy round 4 refused). Every declared id must
have an entry here (completeness), and every entry must name a declared id; the disabled
census (the shipped default) moves nothing.

Tranche 2 (2026-09-19): gate, schema, compile, grounding, authority, asof — 28 sites.
Tranche 3 (2026-09-19): graph, proactive, ingest, procedures, the procedural gate, the registry,
the MCP closed set, the Memory surface, diagnostics, telemetry — 40 more ids.
Tranche 4 (2026-09-19): scope, scope_linkage, scope_read, portability — 33 more ids.
Tranche 5 (2026-09-19): the store — migration, revocation, the sweep's validators, schema
version, sqlite — 46 more ids; 147 in all, every id the semantic review named.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import pytest

import veracium
import veracium.asof.recall  # noqa: F401 — lazily imported by the package; declares two sites
from veracium import authority, census, gate, grounding
from veracium import compile as compile_mod
from veracium.asof import adapter, classify, resolve
from veracium.asof.carrier import Envelope
from veracium.config import MemoryConfig
from veracium.schema import (DEFAULT_RELATIONS, Disclosure, Edge, Episode, EvidenceAuthor,
                             Provenance, Volatility)
from veracium.store.base import RawEdgeState
from veracium.store.sqlite import SqliteStore

U = "u"
NOW = datetime.now(timezone.utc)

# The product's Site objects, captured at THIS module's import: the census tests clear the registry
# for their own fixtures (an autouse `_clear_registry()`), so under a shuffled order the registry
# may be empty by the time these run — the module-level sites keep counting regardless, and
# they are what this leg measures (the registry is the report's carrier, not the counters').
SITES = {sid: census._REGISTRY[sid] for sid in census.registry()}


def _edge(eid="e1", obj="a value", *, disc=Disclosure.MENTIONABLE, author=EvidenceAuthor.USER,
          rel="works_as", valid_from=None, procedural=False):
    t = valid_from or (NOW - timedelta(days=1))
    prov = Provenance(author_of_evidence=author, evidence_ref=f"ev-{eid}", disclosure=disc,
                      observed_at=NOW - timedelta(days=1))
    if procedural:
        prov = prov.model_copy(update={"record_kind": "procedural"})
    return Edge(id=eid, user_id=U, subject="user", relation=rel, object=obj, note="",
                volatility=Volatility.SLOW, valid_from=t, provenance=prov)


def _episode(eid="ep1", *, disc=Disclosure.MENTIONABLE, date=None, retired=None,
             third_party=False):
    prov = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref=eid, disclosure=disc,
                      observed_at=NOW, third_party_influenced=third_party)
    return Episode(id=eid, user_id=U, date=(date or NOW.date().isoformat()), summary="s",
                   provenance=prov, retired_reason=retired)


# ---- one declining execution per site: {site_id: callable} ---------------------------------
# Each callable executes the decision ONCE at its site on an input the site declines. Sites whose
# bracket is shared (scoped_assertable's three, _resolve_edge's two) are asserted on their OWN id.

def _grounded_inputs_withholding():
    s = SqliteStore(":memory:")
    s.add_edge(_edge("uo", disc=Disclosure.USE_ONLY, author=EvidenceAuthor.THIRD_PARTY))
    compile_mod._grounded_inputs(s, U, DEFAULT_RELATIONS)
    s.close()


def _resolve_edge_with(monkeypatched, res):
    """Drive `_resolve_edge` with `_classify_live` returning `res` — the decision at the site on a
    controlled classification (the runtime leg executes the site, not the classifier)."""
    monkeypatched.setattr(resolve, "_classify_live", lambda *a, **k: (res, {} if res else None))
    s = SqliteStore(":memory:")
    resolve._resolve_edge(s, U, _edge(), {}, NOW, NOW, None, None, None, True)
    s.close()


DECLINES = {
    "schema.edge.quarantined": lambda mp: _edge(disc=Disclosure.QUARANTINED).quarantined,
    "schema.edge.use-only": lambda mp: _edge(disc=Disclosure.USE_ONLY).use_only,
    "schema.edge.valid-now": lambda mp: _edge(valid_from=NOW + timedelta(days=1)).valid_now,
    "schema.edge.assertable": lambda mp: _edge(disc=Disclosure.QUARANTINED).assertable,
    "schema.episode.quarantined": lambda mp: _episode(disc=Disclosure.QUARANTINED).quarantined,
    "schema.episode.use-only": lambda mp: _episode(disc=Disclosure.USE_ONLY).use_only,
    "schema.episode.active": lambda mp: _episode(retired="superseded").active,
    "schema.episode.assertable": lambda mp: _episode(disc=Disclosure.QUARANTINED).assertable,
    "schema.episode.valid-now": lambda mp: _episode(
        date=(NOW + timedelta(days=2)).date().isoformat()).valid_now,
    "gate.exclude-procedural": lambda mp: gate.exclude_procedural([_edge(procedural=True)]),
    "gate.scoped-assertable.invisible": lambda mp: gate.scoped_assertable(True, (False, "own")),
    "gate.scoped-assertable.third-party-shaped": lambda mp: gate.scoped_assertable(
        True, (True, "third-party-shaped")),
    "gate.scoped-assertable.entitlement": lambda mp: gate.scoped_assertable(
        True, (True, "own"), subject_entitlement=False),
    "gate.partition-parts": lambda mp: gate.partition_parts(
        [_edge(disc=Disclosure.QUARANTINED, author=EvidenceAuthor.THIRD_PARTY)], []),
    "compile.grounded-inputs": lambda mp: _grounded_inputs_withholding(),
    "grounding.ungrounded": lambda mp: grounding.ungrounded("42 units", "we ordered some", "2026-01-01"),
    "authority.permitted": lambda mp: authority.permitted(
        EvidenceAuthor.USER, None, EvidenceAuthor.THIRD_PARTY, None),
    "authority.self-assertion": lambda mp: authority.self_assertion(EvidenceAuthor.USER, None),
    "asof.adapter.derive-quarantined": lambda mp: adapter.derive_quarantined("works_as", "quarantined"),
    "asof.adapter.derive-use-only": lambda mp: adapter.derive_use_only("use_only"),
    "asof.adapter.adapt.refuse": lambda mp: adapter.adapt("not json", expect_id="a", expect_user=U),
    "asof.classify.assertable-as-of": lambda mp: classify.assertable_as_of(
        Envelope(U, "e1"),
        RawEdgeState(edge_id="e2", user_id=U, state={}, txn=0, seq=0, kind="live", recorded_at=""),
        NS(edge_id="e2", user_id=U, scope_cell=None), NOW, NOW),
    "asof.resolve.held-at": lambda mp: resolve.held_at(_edge(valid_from=NOW + timedelta(days=1)), NOW),
    "asof.resolve.future-T": lambda mp: _raises(
        resolve.FutureAsOfRefused, resolve.resolve_as_of, SqliteStore(":memory:"), U,
        NOW + timedelta(days=1)),
    "asof.resolve.edge-unclassified": lambda mp: _resolve_edge_with(mp, None),
    "asof.resolve.edge-hidden-or-invalid": lambda mp: _resolve_edge_with(
        mp, NS(status=resolve.SCOPE_HIDDEN, flags=frozenset())),
}


def _raises(exc, fn, *a, **k):
    with pytest.raises(exc):
        fn(*a, **k)


# the two as-of recall sites are inner functions of `recall_at` and execute once per candidate
# under a recall — driven through the surface, asserted as one decline per candidate
def _asof_recall_one_candidate():
    mem = veracium.Memory(llm=lambda p, **k: "", config=MemoryConfig(db_path=":memory:"))
    mem.store.add_edge(_edge("q", disc=Disclosure.QUARANTINED, author=EvidenceAuthor.THIRD_PARTY))
    mem.recall(U, "a value", as_of=NOW - timedelta(seconds=1))
    mem.close()


SURFACE_DRIVEN = {
    "asof.recall.grounded": _asof_recall_one_candidate,   # one candidate: grounded False once
    "asof.recall.claim": _asof_recall_one_candidate,      # … and claim True once
}


# ---- tranche 3 (2026-09-19): graph, proactive, ingest, procedures, procedural_gate, registry, mcp,
# the package module, diagnostics, telemetry — 40 ids ------------------------------------------
from veracium import graph, procedural_gate, registry as registry_mod, mcp_server, telemetry as T
from veracium import diagnostics as D
import veracium.procedures  # noqa: F401 — lazily imported by the package; declares its site
from veracium.ingest import EvidenceContext, SourceIdRequired, ingest_event
from veracium.proactive import assemble
from veracium.schema import Outcome, RESERVED_RELATIONS, Relation, UNCLASSIFIED_RELATION
from veracium.store.base import ReceiptSchemaBoundaryError, SupersessionIntegrityError
import json as _json


def _store():
    return SqliteStore(":memory:")


def _mem(**cfg):
    return veracium.Memory(llm=lambda p, **k: "", config=MemoryConfig(db_path=":memory:", **cfg))


def _llm_emitting(payload):
    text = _json.dumps(payload)
    return lambda prompt, *, system=None, role="distill", json_schema=None: text


def _receipt_boundary():
    s = _store(); e = _edge("legacy")
    s._conn.execute("INSERT INTO supersession_operations(user_id,operation_id,logical_request_digest,"
                    "status,request_digest,response,outcome_digest_version) VALUES(?,?,?,?,NULL,?,?)",
                    (U, f"sup-{e.id}", "pre-split", "applied", None, 1))
    s._conn.commit()
    with pytest.raises(ReceiptSchemaBoundaryError):
        graph.apply_supersession(s, e, DEFAULT_RELATIONS)
    s.close()


def _replay_mismatch():
    s = _store()
    graph.apply_supersession(s, _edge("same", "Miso"), DEFAULT_RELATIONS)
    with pytest.raises(SupersessionIntegrityError):
        graph.apply_supersession(s, _edge("same", "COMPLETELY different"), DEFAULT_RELATIONS)
    s.close()


def _sourced(eid, obj="v", source="mb-a"):
    e = _edge(eid, obj)
    return e.model_copy(update={"provenance": e.provenance.model_copy(update={"source_id": source})})


def _absorption(mp, case):
    s = _store()
    if case == "unresolved":                          # the incoming's own evidence UNRESOLVED (controlled)
        from veracium import scope_read
        from veracium.scope import UNRESOLVED
        mp.setattr(scope_read.MembershipResolver, "evidence_of_unwritten", lambda self, record: UNRESOLVED)
        gate = graph._absorption_scope_gate(s, _sourced("inc")); prior = _sourced("prior")
        s.add_edge(prior); gate(prior)
    elif case == "cross-scope":                        # two identities: the prior's evidence differs
        prior = _sourced("prior", source="mb-b"); s.add_edge(prior)
        gate = graph._absorption_scope_gate(s, _sourced("inc", source="mb-a")); gate(prior)
    else:                                              # same scope, the prior's closure is None
        from veracium import scope_read
        mp.setattr(scope_read.MembershipResolver, "flattening_plan", lambda self, kind, rid: None)
        prior = _sourced("prior"); s.add_edge(prior)
        gate = graph._absorption_scope_gate(s, _sourced("inc")); gate(prior)
    s.close()


def _src_revoked(mp):
    from veracium import scope_linkage
    mp.setattr(SqliteStore, "standing_revocations", lambda self, uid: {"d"})
    mp.setattr(scope_linkage, "identity_digest_of", lambda *a, **k: "d")
    s = _store(); graph.apply_supersession(s, _sourced("inc"), DEFAULT_RELATIONS); s.close()


def _inactive(e):
    return e.model_copy(update={"invalidated_at": NOW, "invalidation_reason": "superseded"})


def _collapse():
    a = _edge("a", "same value"); b = _edge("b", "same value")
    graph.collapse_for_render([a, b])


def _assemble_with(*edges):
    s = _store()
    for e in edges: s.add_edge(e)
    assemble(s, U, MemoryConfig(db_path=":memory:"), now=NOW); s.close()


def _ingest(**kw):
    s = _store()
    try:
        ingest_event(s, _llm_emitting({"triples": [], "episode": "ep"}), U, event_text="t",
                     author=kw.pop("author", EvidenceAuthor.USER), date="2026-09-19",
                     relations=DEFAULT_RELATIONS, **kw)
    finally:
        s.close()


def _procedure_source_id():
    mem = _mem(require_source_id=True)
    with pytest.raises(SourceIdRequired):
        mem.record_procedure(U, "Rotate service credentials every quarter.", author=EvidenceAuthor.THIRD_PARTY,
                             context=EvidenceContext.direct(basis="stated"))
    mem.close()


def _memory_raises(exc, fn):
    mem = _mem()
    try:
        with pytest.raises(exc):
            fn(mem)
    finally:
        mem.close()


def _local_origin_missing(mp):
    mp.delattr(SqliteStore, "local_origin")
    from veracium.scope import ScopeError
    with pytest.raises(ScopeError):
        veracium.Memory(llm=lambda p, **k: "", config=MemoryConfig(db_path=":memory:", scope_groups={}))


class TwoPhase:
    """A site whose SETUP would consult the same site (disputing an edge to make it inactive consults
    the dispute site): `setup` runs OUTSIDE the counting window, `run` inside it."""
    def __init__(self, setup, run): self.setup, self.run = setup, run


def _with_inactive_edge():
    mem = _mem(); e = _edge("d1"); mem.store.add_edge(e); mem.dispute(U, e.id); return (mem, e.id)


def _inactive_edge_in(mem):
    e = _edge("d1"); mem.store.add_edge(e); mem.dispute(U, e.id); return e.id


def _procedural_edge_in(mem):
    return mem.record_procedure(U, "Rotate service credentials every quarter.", author=EvidenceAuthor.USER,
                                context=EvidenceContext.direct(basis="stated"))


def _other_subject_prior_in(mem):
    e = _edge("p9", "nurse").model_copy(update={"subject": "user's sister", "provenance": _edge("p9").provenance.model_copy(
        update={"author_of_evidence": EvidenceAuthor.SYSTEM, "derived_from": EvidenceAuthor.THIRD_PARTY})})
    mem.store.add_edge(e); return e.id


def _reporter_not_consented():
    r = D.Reporter(); r.config.endpoint = "https://example.invalid/collect"
    assert r.send(interactive=False) is False


def _telemetry(mp, fn, enabled=None):
    mp.setenv("XDG_CONFIG_HOME", str(__import__("tempfile").mkdtemp()))
    if enabled is not None:
        T.set_enabled(enabled)
    cfg = T.TelemetryConfig.load(); c = T.Collector(); c.record("recall", {"subgraph_edges": 1})
    return fn(cfg, c)


DECLINES.update({
    "graph.supersession.receipt-boundary": lambda mp: _receipt_boundary(),
    "graph.supersession.replay-mismatch": lambda mp: _replay_mismatch(),
    "graph.absorption.scope-unresolved": lambda mp: _absorption(mp, "unresolved"),
    "graph.absorption.cross-scope": lambda mp: _absorption(mp, "cross-scope"),
    "graph.absorption.no-flattening-plan": lambda mp: _absorption(mp, "no-plan"),
    "graph.correction.identity-mismatch": lambda mp: _raises(
        ValueError, graph.plan_correction, _store(), _edge("p"), _edge("r").model_copy(update={"subject": "other"}), op_id="op-x"),
    "graph.correction.prior-not-active": lambda mp: _raises(ValueError, graph.plan_correction, _store(), _edge("p"), _edge("r"), op_id="op-x"),
    "graph.src-revoked": lambda mp: _src_revoked(mp),
    "graph.semantic-duplicate.keep": lambda mp: graph.semantic_duplicate_of(_inactive(_edge("m")), _edge("s")),
    "graph.strictly-redundant": lambda mp: graph._strictly_redundant(
        _edge("m").model_copy(update={"note": "extra"}), _edge("s")),
    "graph.collapse-for-render": lambda mp: _collapse(),
    "ingest.source-id-required": lambda mp: _raises(SourceIdRequired, _ingest_third_party_unsourced),
    "ingest.basis-via-remember": lambda mp: _raises(ValueError, lambda: _ingest(context=EvidenceContext.direct(basis="stated"))),
    "ingest.instructions-not-a-list": lambda mp: _ingest_instructions_not_a_list(),
    "procedures.source-id-required": lambda mp: _procedure_source_id(),
    "procedural-gate.positive-form": lambda mp: procedural_gate.positive_form(""),
    "procedural-gate.actor-present": lambda mp: procedural_gate.actor_present(""),
    "registry.empty-refused": lambda mp: _raises(registry_mod.RegistryError, registry_mod.effective_registry, {}),
    "registry.reserved-shadowed": lambda mp: _raises(
        registry_mod.RegistryError, registry_mod.effective_registry,
        {UNCLASSIFIED_RELATION: Relation(name=UNCLASSIFIED_RELATION, functional=True, desc="shadowed")}),
    "mcp.closed-set.author": lambda mp: _raises(ValueError, mcp_server._closed_set, "author", "system"),
    "mcp.closed-set.trust-field": lambda mp: _raises(ValueError, mcp_server._closed_set, "derived_from", "bogus"),
    "memory.scope.local-origin-missing": lambda mp: _local_origin_missing(mp),
    "memory.recall.as-of-on-proactive": lambda mp: _memory_raises(ValueError, lambda m: m.recall(U, None, as_of=NOW)),
    "memory.recall.policy-with-as-of": lambda mp: _memory_raises(ValueError, lambda m: m.recall(
        U, "q", policy=veracium.PolicyLane(policy_id="p", policy_version="1", tags_matched=("t",), ranks={}), as_of=NOW)),
    "memory.edge.unknown-target": lambda mp: _memory_raises(ValueError, lambda m: m.dispute(U, "nope")),
    "memory.dispute.inactive-edge": TwoPhase(lambda mp: _with_inactive_edge(), lambda st: _raises(ValueError, st[0].dispute, U, st[1])),
    "memory.record-outcome.actor-vocabulary": lambda mp: _memory_raises(ValueError, lambda m: m.record_outcome(
        U, "x", outcome=Outcome.CONFIRMED, evidence_ref="r", actor="bogus")),
    "memory.record-outcome.human-judgment": lambda mp: _memory_raises(ValueError, lambda m: m.record_outcome(
        U, "x", outcome=Outcome.CONFIRMED, evidence_ref="r", actor="system")),
    "memory.record-outcome.system-judgment": lambda mp: _memory_raises(ValueError, lambda m: m.record_outcome(
        U, "x", outcome=Outcome.CHALLENGED, evidence_ref="r", actor="user")),
    "memory.correct.inactive-edge": lambda mp: _memory_raises(ValueError, lambda m: m.correct(U, _inactive_edge_in(m), "new")),
    "memory.correct.procedural": lambda mp: _memory_raises(
        __import__("veracium.procedures", fromlist=["ProcedureValueError"]).ProcedureValueError,
        lambda m: m.correct(U, _procedural_edge_in(m), "new")),
    "memory.correct.refused": lambda mp: _memory_raises(graph.CorrectionRefused, lambda m: m.correct(U, _other_subject_prior_in(m), "surgeon")),
    "diagnostics.send.not-consented": lambda mp: _reporter_not_consented(),
    "telemetry.preview.invalid-consent": lambda mp: _telemetry(mp, T.preview),
    "telemetry.preview.not-enabled": lambda mp: _telemetry(mp, T.preview, enabled=False),
    "telemetry.flush.invalid-consent": lambda mp: _telemetry(mp, lambda cfg, c: T.flush_if_due(cfg, c, poster=lambda u, p: None)),
    "telemetry.flush.not-enabled": lambda mp: _telemetry(mp, lambda cfg, c: T.flush_if_due(cfg, c, poster=lambda u, p: None), enabled=False),
    "telemetry.collector.not-enabled": lambda mp: _telemetry(mp, lambda cfg, c: T.load_collector_if_enabled()),
})


def _ingest_third_party_unsourced():
    _ingest(author=EvidenceAuthor.THIRD_PARTY, require_source_id=True)


def _ingest_instructions_not_a_list():
    s = _store()
    ingest_event(s, _llm_emitting({"triples": [], "episode": "ep", "instructions": "x"}), U, event_text="t",
                 author=EvidenceAuthor.USER, date="2026-09-19", relations=DEFAULT_RELATIONS)
    s.close()


SURFACE_DRIVEN.update({
    # a variant needs an ELIGIBLE group (a survivor is chosen among class rank < 9): transient
    # members, one value, two distinct notes (neither strictly redundant) → one survivor, one variant
    "proactive.variant": lambda: _assemble_with(
        _edge("a", "same value").model_copy(update={"note": "one note", "volatility": Volatility.TRANSIENT}),
        _edge("b", "same value").model_copy(update={"note": "another note", "volatility": Volatility.TRANSIENT})),
    "proactive.eligible": lambda: _assemble_with(_edge("durable", "a plain durable fact")),
})


# the lazily imported modules declared their sites only now: refresh the snapshot the leg measures
SITES.update({sid: census._REGISTRY[sid] for sid in census.registry()})


# ---- tranche 4 (2026-09-19): scope, scope_linkage, scope_read, portability — 33 ids ----------------
from veracium import portability, scope, scope_linkage, scope_read
from veracium.scope import Identity, ScopeError, validate_policy
import veracium.portability  # noqa: F401 — lazily imported by the package; declares its sites

_LOCAL = "org-local-1234"
_A1 = Identity("org-a", "agent-1")
_B1 = Identity("org-b", "agent-9")


def _pol(local=_LOCAL):
    return validate_policy({"team-a": [Identity("org-a", "agent-1"), Identity("org-a", "agent-2")],
                            "team-b": [Identity("org-b", "agent-9")]}, False, local_origin=local)


def _ungroupable():
    return Identity("org-a", None)


def _row(ref, **payload):
    return {"site": "absorption", "identity_digest": "d", "op_key": None, "evidence_ref_digest": None,
            "contributor_ref": ref, "payload": payload}


def _export_lines(records, version=12, uid=U):
    head = {"kind": "veracium-export", "version": version, "user_id": uid, "exported_at": "2026-01-01T00:00:00+00:00"}
    return [_json.dumps(head)] + [_json.dumps(r) for r in records]


def _edge_rec(eid="e1", origin="org-x", **over):
    rec = _json.loads(_edge(eid).model_dump_json()); rec["provenance"]["origin"] = origin
    rec.update(over); return {"record": "edge", **rec}


def _episode_rec(eid="ep1", origin="org-x", **over):
    rec = _json.loads(_episode(eid).model_dump_json()); rec["provenance"]["origin"] = origin
    rec.pop("consolidation_output_index", None); rec.update(over); return {"record": "episode", **rec}


def _import(lines, **kw):
    import tempfile, os
    d = tempfile.mkdtemp(); p = os.path.join(d, "e.jsonl")
    with open(p, "w") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    s = _store()
    try:
        return portability.import_memory(s, p, **kw)
    finally:
        s.close()


def _import_raises(lines, exc=ValueError, **kw):
    with pytest.raises(exc):
        _import(lines, **kw)


def _export_non_quiescent(mp):
    mp.setattr(SqliteStore, "quiescent_episode_snapshot", lambda self, *a, **k: portability.NON_QUIESCENT)
    s = _store()
    with pytest.raises(ValueError):
        portability.export_memory(s, U, "/dev/null")
    s.close()


def _preflight_conflict():
    s = _store(); s.add_edge(_edge("e1", "stored value"))
    import tempfile, os
    p = os.path.join(tempfile.mkdtemp(), "e.jsonl")
    with open(p, "w") as f:
        f.write("\n".join(_export_lines([_edge_rec("e1", object="a different value")])) + "\n")
    with pytest.raises(ValueError):
        portability.import_memory(s, p, restore=True)
    s.close()


def _race_exhausted(mp):
    mp.setattr(portability, "_IMPORT_RETRIES", 0)
    _import_raises(_export_lines([_edge_rec("e1")]))


def _scoped_view_hides():
    s = _store(); pol = _pol(s.local_origin())
    v = scope_read.ScopeView(s, U, _A1, pol)
    e = _edge("x"); e = e.model_copy(update={"provenance": e.provenance.model_copy(update={"source_id": "agent-9", "origin": "org-b"})})
    v.scoped([e])
    s.close()


DECLINES.update({
    "scope.identity.groupable": lambda mp: _ungroupable().groupable,
    "scope.policy.non-groupable-member": lambda mp: _raises(ScopeError, validate_policy, {"g": [_ungroupable()]}, local_origin=_LOCAL),
    "scope.policy.digest-overlap": lambda mp: _raises(
        ScopeError, validate_policy, {"g1": [Identity("org-a", "agent-1")], "g2": [Identity("org-a", "agent-1")]}, local_origin=_LOCAL),
    "scope.revalidate": lambda mp: _raises(ScopeError, scope._revalidate, "not a policy", _LOCAL),
    "scope.closure.walk": lambda mp: scope.close_absorption_rows("S", {"S": [_row(None)]}),
    "scope.prune.cycle": lambda mp: _raises(
        scope.ExportLinkageError, scope.prune_absorbed_record, "B",
        {"B": [_row("C")], "C": [_row("B")]}, prune_op="op-000000000001"),
    "scope.membership.unknown-state": lambda mp: _raises(
        ScopeError, scope.membership, {"author": "user", "origin": "o", "source_id": "s", "evidence_ref": "r", "lineage": False}, [], "bogus", _LOCAL),
    "scope.membership.abandoned": lambda mp: _raises(
        ScopeError, scope.membership, {"author": "user", "origin": "o", "source_id": "s", "evidence_ref": "r", "lineage": False}, [], "abandoned", _LOCAL),
    "scope.classify.no-policy": lambda mp: _raises(ScopeError, scope.classify, scope.digest_of(_A1, _LOCAL), _A1, None, _LOCAL),
    "scope.classify.principal-ungroupable": lambda mp: _raises(ScopeError, scope.classify, scope.digest_of(_A1, _LOCAL), _ungroupable(), _pol(), _LOCAL),
    "scope.classify.evidence-not-digest": lambda mp: _raises(ScopeError, scope.classify, "not-a-digest", _A1, _pol(), _LOCAL),
    "scope.filters.not-mapping": lambda mp: _raises(ScopeError, scope.validate_filters, 5),
    "scope.filters.unknown-field": lambda mp: _raises(ScopeError, scope.validate_filters, {"bogus": "x"}),
    "scope.filters.bad-value": lambda mp: _raises(ScopeError, scope.validate_filters, {"subject": ""}),
    "scope.filters.apply": lambda mp: scope.apply_filters([{"subject": "a"}], {"subject": "b"}),
    "scope-linkage.import.winner": lambda mp: _raises(
        scope_linkage.ImportLinkageError, scope_linkage._resolve_winner, {"id": "r", "absorbed_by_id": "gone"}, {"r"}),
    "scope-linkage.import.rows": lambda mp: _raises(
        scope_linkage.ImportLinkageError, scope_linkage.reconstruct_absorption_rows,
        [{"id": "r", "invalidation_reason": "superseded", "absorbed_by_id": "w"}, {"id": "w"}], "org-dest-1", import_op="op-feedbeef0042"),
    "scope-linkage.export.ambiguous-absorber": lambda mp: _raises(
        scope.ExportLinkageError, scope.derive_absorbed_by, "A", {"B": [_row("A")], "C": [_row("A")]}),
    "scope-read.view.principal-not-identity": lambda mp: _raises(ScopeError, scope_read.ScopeView, _store(), U, "not-an-identity", _pol()),
    "scope-read.view.no-policy": lambda mp: _raises(ScopeError, scope_read.ScopeView, _store(), U, _A1, None),
    "scope-read.view.principal-ungroupable": lambda mp: _raises(ScopeError, scope_read.ScopeView, _store(), U, _ungroupable(), _pol()),
    "scope-read.scoped": lambda mp: _scoped_view_hides(),
    "scope-read.narrow-edges": lambda mp: scope_read.narrow_edges([_edge("n")], {"subject": "nobody"}),
    "portability.export.non-quiescent": lambda mp: _export_non_quiescent(mp),
    "portability.import.chain": lambda mp: _raises(ValueError, portability._validate_incoming_chain, [], "k", "p"),
    "portability.import.restore-not-bool": lambda mp: _import_raises(_export_lines([]), TypeError, restore="yes"),
    "portability.import.restore-with-user": lambda mp: _import_raises(_export_lines([]), restore=True, user_id="v"),
    "portability.import.file": lambda mp: _import_raises([]),
    "portability.import.agreement-invalid": lambda mp: _import_raises(
        _export_lines([_edge_rec("e1", agreement={"malformed": True})]), restore=True),
    "portability.import.origin-missing": lambda mp: _import_raises(_export_lines([_edge_rec("e1", origin=None)])),
    "portability.import.record": lambda mp: _import_raises(_export_lines([_episode_rec("ep1", claimed_by="op-x")])),
    "portability.import.race-exhausted": lambda mp: _race_exhausted(mp),
    "portability.import.preflight": lambda mp: _preflight_conflict(),
})

SITES.update({sid: census._REGISTRY[sid] for sid in census.registry()})


# ---- tranche 5 (2026-09-19): the store — migration, revocation, the sweep's validators, schema
# version, sqlite — 46 ids ---------------------------------------------------------------------
import contextlib as _contextlib
import sqlite3 as _sqlite3
import tempfile as _tempfile

from veracium import contribution as _C
from veracium.graph import _build_supersession_plan, apply_supersession, plan_correction
from veracium.schema import (ConfirmationActor, ConfirmationCallPath, ConsolidationOutputDraft,
                             ConsolidationState, ContributionDraft)
from veracium.store import migration as _migration, revocation as _rv, revocation_sweep as _rvs
from veracium.store import schema_version as _sv
from veracium.store.base import (NON_QUIESCENT, CorrectionAuthorisationError, PreEpochQuery,
                                 ReceiptSchemaBoundaryError, SupersessionIntegrityError)
from veracium.store.schema_version import StoreVersionError


def _dbpath():
    return _tempfile.mktemp(suffix=".db")


def _sourced5(eid, obj="v", source="src-A", days=1):
    e = _edge(eid, obj, valid_from=NOW - timedelta(days=days))
    return e.model_copy(update={"provenance": e.provenance.model_copy(update={"source_id": source})})


def _seeded(n=3):
    s = _store()
    for i in range(1, n + 1):
        s.add_episode(_episode(f"e{i}", date=f"2026-01-0{i}"))
    return s


def _claimed(ids=("e1", "e2")):
    s = _seeded(); op = s.create_or_takeover_consolidation(U, list(ids), "w1", 60); assert op is not None
    return s, op


def _v2_conn_with_duplicate_legacy_outcome():
    p = _dbpath(); conn = _sqlite3.connect(p)
    for o in _sv.SCHEMA_V2:
        conn.execute(o.ddl)
    legacy = {"id": "leg-1", "user_id": U, "date": "2026-05-05", "summary": "legacy use", "kind": "outcome",
              "edge_id": "e1", "outcome": "concurred", "provenance": {"author_of_evidence": "system", "evidence_ref": "run-1"}}
    for eid in ("leg-1", "leg-2"):
        conn.execute("INSERT INTO episodes(id,user_id,date,json) VALUES(?,?,?,?)", (eid, U, "2026-05-05", _json.dumps(dict(legacy, id=eid))))
    conn.execute("PRAGMA user_version = 2"); conn.commit(); return conn


class _RollbackFails:
    def __init__(self, conn): self._c = conn
    def __getattr__(self, n): return getattr(self._c, n)
    def execute(self, sql, *a):
        if sql == "ROLLBACK":
            raise _sqlite3.OperationalError("disk gone")
        return self._c.execute(sql, *a)


class _CommitFails:
    def __init__(self, conn): self._c = conn
    def __getattr__(self, n): return getattr(self._c, n)
    def commit(self):
        raise _sqlite3.OperationalError("database is locked")


def _stamped_foreign_file():
    p = _dbpath(); c = _sqlite3.connect(p); c.execute("CREATE TABLE not_ours (x)")
    c.execute(f"PRAGMA user_version = {_sv.SCHEMA_VERSION}"); c.commit(); c.close(); return p


def _stamped(version):
    p = _dbpath(); SqliteStore(p).close(); c = _sqlite3.connect(p); c.execute(f"PRAGMA user_version = {version}"); c.commit(); c.close(); return p


def _legacy_v1_file():
    p = _dbpath(); c = _sqlite3.connect(p); c.executescript(";\n".join(o.ddl for o in _sv.SCHEMA_V1) + ";\n"); c.commit(); c.close(); return p


def _open_locked():
    p = _dbpath(); holder = SqliteStore(p)
    try:
        holder._conn.execute("BEGIN IMMEDIATE")
        with pytest.raises(StoreVersionError) as ei:
            SqliteStore(p, busy_timeout_ms=100)
        assert ei.value.reason == "locked"
    finally:
        with _contextlib.suppress(_sqlite3.OperationalError):
            holder._conn.execute("ROLLBACK")
        holder.close()


def _txn_locked():
    p = _dbpath(); holder = SqliteStore(p); writer = SqliteStore(p, busy_timeout_ms=100)
    try:
        holder._conn.execute("BEGIN IMMEDIATE")
        with pytest.raises(_sqlite3.OperationalError, match="could not take the write lock"):
            writer.add_edge(_edge("x"))
    finally:
        with _contextlib.suppress(_sqlite3.OperationalError):
            holder._conn.execute("ROLLBACK")
        holder.close(); writer.close()


def _txn_commit_lost():
    s = _store(); s._conn = _CommitFails(s._conn)
    with pytest.raises(_sqlite3.OperationalError, match="could not COMMIT"):
        s.add_edge(_edge("x"))


def _journal_bad_reason():
    s = _store(); s.add_edge(_edge("j"))
    with pytest.raises(ValueError):
        with s._write_txn():
            s._journal_edge_write(U, "j", '{"changed": 1}', "{}", kind="invalidated", reason="bogus")   # a changed row reaches the reason check
    s.close()


def _upsert_changes_user():
    s = _store(); e = _edge("u1"); s.add_edge(e)
    with pytest.raises(ValueError):
        with s._write_txn():
            s._upsert_edge_row(e.model_copy(update={"user_id": "someone-else"}))
    s.close()


def _flattening_unresolved(mp):
    from veracium import scope_read
    from veracium.scope import UNRESOLVED
    mp.setattr(scope_read.MembershipResolver, "evidence_of_unwritten", lambda self, record: UNRESOLVED)
    s = _store(); inc = _sourced5("inc")
    plan = NS(incoming_edge=inc, contribution_drafts=[ContributionDraft(
        site="absorption", survivor_type="edge", survivor_id=inc.id, contributor_type="edge", contributor_id="prior")])
    with pytest.raises(SupersessionIntegrityError):
        s._write_absorption_flattening(U, plan)
    s.close()


def _consolidation_output_without_index(mp):
    s = _store()
    out = _episode("out1").model_copy(update={"lineage": ["e1"], "consolidation_output_index": None, "operation_id": "op-x"})
    mp.setattr(SqliteStore, "_episodes_for_operation", lambda self, uid, op: [(None, out)])
    with pytest.raises(SupersessionIntegrityError):
        s._write_consolidation_contributions(NS(user_id=U, operation_id="op-x", claimed_ids=["e1"]))
    s.close()


def _receipt_boundary_in_store():
    s = _store(); e = _sourced5("eb")
    plan, _ = _build_supersession_plan(s, e, DEFAULT_RELATIONS, "op-boundary")
    plan.raw_request = _C.raw_request_snapshot(e)
    s._conn.execute("INSERT INTO supersession_operations(user_id,operation_id,logical_request_digest,status,"
                    "request_digest,response,outcome_digest_version) VALUES(?,?,?,?,?,?,?)",
                    (U, "op-boundary", "stored-pre-d2", "applied", None, None, 1))
    s._conn.commit()
    with pytest.raises(ReceiptSchemaBoundaryError):
        s.apply_supersession_plan(plan)
    s.close()


def _correction_without_authorisation():
    s = _store(); prior = _sourced5("p1", "nurse"); s.add_edge(prior)
    plan = plan_correction(s, prior, _sourced5("r1", "surgeon"), op_id="op-c")[0]
    with pytest.raises(CorrectionAuthorisationError):
        s.apply_supersession_plan(plan)
    s.close()


def _absorption_drafts_mismatch():
    s = _store()
    prior = _sourced5("e-prior", "Miso", days=3); apply_supersession(s, prior, DEFAULT_RELATIONS)
    winner = _sourced5("e-winner", "cat Miso", days=0)
    plan, _ = _build_supersession_plan(s, winner, DEFAULT_RELATIONS, "op-abs")
    assert plan.contribution_drafts, "the fixture must absorb (same source, more specific value)"
    plan.contribution_drafts.append(plan.contribution_drafts[0])
    with pytest.raises(SupersessionIntegrityError):
        s.apply_supersession_plan(plan)
    s.close()


def _confirm(s, **over):
    kw = dict(actor=ConfirmationActor.USER, call_path=ConfirmationCallPath.HOST_API,
              correlation_id="k1", request_digest="d1", confirmed_at=NOW)
    kw.update(over); return s.confirm_edge(U, "c1", **kw)


def _confirm_correlation_race():
    """The concurrent-duplicate branch: the UNIQUE(user_id, correlation_id) row appears between the
    replay check and the INSERT, with a DIFFERENT request digest."""
    s = _store(); s.add_edge(_edge("c1")); real = s._conn
    class Racing:
        done = False
        def __getattr__(self, n): return getattr(real, n)
        def execute(self, sql, *a):
            if sql.lstrip().upper().startswith("INSERT INTO CONFIRMATIONS") and not Racing.done:
                Racing.done = True
                params = list(a[0]); params[params.index("d1")] = "OTHER"     # same id, other digest, first
                real.execute(sql, tuple(params))
            return real.execute(sql, *a)
    s._conn = Racing()
    with pytest.raises(ValueError, match="conflict"):
        _confirm(s)
    s.close()


def _outcome_episode_id(mem):
    e = _edge("o1"); mem.store.add_edge(e)
    mem.record_outcome(U, e.id, outcome=Outcome.CONCURRED, evidence_ref="run-1", actor="system")
    return next(ep.id for ep in mem.store.episodes(U) if ep.kind == "outcome")


def _delete_outcome_episode():
    mem = _mem(); eid = _outcome_episode_id(mem)
    with pytest.raises(ValueError):
        mem.store.delete_episode(eid)
    mem.close()


def _delete_reserved_episode():
    s, op = _claimed(("e1",))
    with pytest.raises(ValueError):
        s.delete_episode("e1")
    s.close()


def _pre_epoch(mp):
    mp.setattr(SqliteStore, "epoch_txn", lambda self, uid: 5)
    s = _store()
    with pytest.raises(PreEpochQuery):
        s.edge_state_at(U, "e", 1)
    s.close()


def _non_quiescent_snapshot():
    s, op = _claimed(); assert s.quiescent_episode_snapshot(U) is NON_QUIESCENT; s.close()


def _contended_claim():
    s = _seeded(); a = s.create_or_takeover_consolidation(U, ["e1", "e2"], "w1", 60)
    assert a is not None and s.create_or_takeover_consolidation(U, ["e2", "e3"], "w2", 60) is None; s.close()


def _delete_not_current():
    s, op = _claimed(); assert s.delete_claimed_inputs_if_current(op.operation_id, op.fence) is False; s.close()


def _abandon_live():
    s, op = _claimed(); assert s.abandon_consolidation_if_current(op.operation_id, op.fence) is False; s.close()


def _embedding(edge_exists, digest):
    s = _store()
    if edge_exists:
        s.add_edge(_edge("emb"))
    assert s.upsert_embedding(edge_id="emb", user_id=U, embedder_id="x", content_digest=digest,
                              dim=2, vec=[0.0, 0.0], built_at=NOW) is False
    s.close()


def _import_plan_missing_fields():
    s = _store()
    with pytest.raises(ValueError):
        s.commit_outcome_import_plan(U, {"edges": [], "episodes": [], "contributions": [{"id": "x"}]}, {})
    s.close()


def _visible(**over):
    return _episode("v1").model_copy(update=over)


DECLINES.update({
    "store.migration.version": lambda mp: _raises(StoreVersionError, _migration._apply_forward, _sqlite3.connect(":memory:"), 99),
    "store.migration.duplicate-outcome-chain": lambda mp: _raises(
        _migration.DuplicateOutcomeChainError, _migration._migrate_outcome_chains, _v2_conn_with_duplicate_legacy_outcome()),
    "store.revocation.unknown-state": lambda mp: _raises(
        _rv.RevocationUnknownState, _rv._rollback_or_poison, _RollbackFails(_store()._conn), RuntimeError("boom")),
    "store.revocation.ordinal-collision": lambda mp: _ordinal_collision(),
    "store.revocation.integrity": lambda mp: _raises(
        _rv.RevocationIntegrityError, _rv.revocation_operation, _store()._conn, U, "d1", "resurrect", "r",
        "2026-01-01T00:00:00Z", plan=lambda st: [], apply_effect=lambda c, e: None),
    "store.revocation.self-linkage": lambda mp: _raises(
        _rvs.RevocationLinkageError, _rvs.validate_contribution_row,
        {"user_id": U, "survivor_type": "edge", "survivor_id": "a", "site": "absorption", "identity_digest": "0" * 64,
         "evidence_ref_digest": None, "payload": {}, "op_key": None, "contributor_type": "edge", "contributor_ref": "a"}),
    "store.revocation.source-not-revocable": lambda mp: _raises(
        _rvs.RevocationError, _rvs.validate_revocation_row,
        {"user_id": U, "identity_digest": "not-a-digest", "action": "revoke", "at": "2026-01-01T00:00:00Z", "seq": 1, "reason": "r"}),
    "store.open.unaccepted-shape": lambda mp: _raises(StoreVersionError, SqliteStore, _stamped_foreign_file()),
    "store.open.runtime-unsupported": lambda mp: (mp.setattr(_sv, "runtime_supported", lambda: False),
                                                  _raises(StoreVersionError, SqliteStore, _dbpath())),
    "store.open.locked": TwoPhase(lambda mp: _lock_holder(), lambda st: _open_while_held(st)),
    "store.open.invalid-version": TwoPhase(lambda mp: _stamped(-1), lambda p: _raises(StoreVersionError, SqliteStore, p)),
    "store.open.newer": TwoPhase(lambda mp: _stamped(_sv.SCHEMA_VERSION + 1), lambda p: _raises(StoreVersionError, SqliteStore, p)),
    "store.open.legacy": lambda mp: _raises(StoreVersionError, SqliteStore, _legacy_v1_file()),
    "store.runtime-supported": lambda mp: (mp.setattr(_sv, "artifact_problems", lambda records: ["bad"]), _sv.runtime_supported()),
    "store.journal.reason-not-dispositioned": lambda mp: _journal_bad_reason(),
    "store.read.output-not-visible": lambda mp: SqliteStore._ordinary_read_visible(
        _visible(lineage=["e1"], operation_id="op"), {"op": ConsolidationState.CLAIMED}),
    "store.read.input-claimed": lambda mp: SqliteStore._ordinary_read_visible(
        _visible(operation_id="op"), {"op": ConsolidationState.OUTPUTS_DURABLE}),
    "store.upsert.immutable": TwoPhase(lambda mp: _stored_edge(), lambda st: _upsert_other_user(*st)),
    "store.flattening": lambda mp: _flattening_unresolved(mp),
    "store.consolidation-contribution": lambda mp: _consolidation_output_without_index(mp),
    "store.contribution": lambda mp: _raises(
        SupersessionIntegrityError, _store()._write_contribution, U,
        ContributionDraft(site="consolidation", survivor_type="edge", survivor_id="a", contributor_type="edge", contributor_id="b"), None),
    "store.txn.locked": lambda mp: _txn_locked(),
    "store.txn.locked-retry": lambda mp: _txn_commit_lost(),
    "store.consolidation.abandon-live-lease": lambda mp: _abandon_live(),
    "store.add-episode": lambda mp: _raises(ValueError, _store().add_episode, _episode("bad").model_copy(update={"consolidation_output_index": 1})),
    "store.outcome.context-ref": TwoPhase(lambda mp: _outcome_chain_state(), lambda st: _raises(ValueError, st[0].store.append_outcome_if_head, *st[1])),
    "store.supersession.integrity": lambda mp: _receipt_boundary_in_store(),
    "store.correction.authorisation": lambda mp: _correction_without_authorisation(),
    "store.supersession.plan": TwoPhase(lambda mp: _absorption_plan_with_duplicate_draft(), lambda st: _raises(SupersessionIntegrityError, st[0].apply_supersession_plan, st[1])),
    "store.import-plan": lambda mp: _import_plan_missing_fields(),
    "store.confirm.unknown-edge": lambda mp: _raises(KeyError, _confirm, _store()),
    "store.confirm.not-assertable": TwoPhase(lambda mp: _quarantined_store(), lambda s: _raises(ValueError, _confirm, s)),
    "store.confirm.request-digest": TwoPhase(lambda mp: _confirmed_once(), lambda s: _raises(ValueError, _confirm, s, request_digest="DIFFERENT")),
    "store.confirm.correlation": lambda mp: _confirm_correlation_race(),
    "store.consolidation.contended": TwoPhase(lambda mp: _first_claim(), lambda s: s.create_or_takeover_consolidation(U, ["e2", "e3"], "w2", 60)),
    "store.consolidation.delete-not-current": lambda mp: _delete_not_current(),
    "store.delete-episode.outcome": lambda mp: _delete_outcome_episode(),
    "store.delete-episode.reserved": lambda mp: _delete_reserved_episode(),
    "store.journal.pre-epoch": lambda mp: _pre_epoch(mp),
    "store.edges.read-fence": lambda mp: _store().edges(U, include_quarantined=False),
    "store.export.non-quiescent": lambda mp: _non_quiescent_snapshot(),
    "store.consolidation.renew-refused": lambda mp: _store().renew_consolidation_lease("nope", "f", "w"),
    "store.consolidation.transition": lambda mp: _store().transition_consolidation_if_current("nope", "f", "w", "generating"),
    "store.embedding.delayed-writer": lambda mp: _embedding(False, "d"),
    "store.embedding.stale-content": lambda mp: _embedding(True, "not-the-digest"),
    "store.consolidation.write-not-current": lambda mp: _store().write_consolidation_output_if_current(
        "nope", "f", "w", ConsolidationOutputDraft(summary="m", date_start="2026-01-01", date_end="2026-01-02")),
})


def _ordinal_collision():
    s = _store()
    _rv.revocation_operation(s._conn, U, "d1", "revoke", "r", "2026-08-21T00:00:00Z", plan=lambda st: [], apply_effect=lambda c, e: None)
    def plan_preinsert(st):
        s._conn.execute("INSERT INTO source_revocations(user_id, seq, identity_digest, action, at, reason) VALUES(?,?,?,?,?,?)",
                        (U, 1, "other", "revoke", "2026-01-01T00:00:00Z", "r"))
        return []
    with pytest.raises(_rv.OrdinalCollision):
        _rv.revocation_operation(s._conn, U, "d2", "revoke", "r", "2026-08-21T00:00:00Z", plan=plan_preinsert, apply_effect=lambda c, e: None)
    s.close()


def _quarantined_store():
    s = _store(); s.add_edge(_edge("c1", disc=Disclosure.QUARANTINED, author=EvidenceAuthor.THIRD_PARTY)); return s


def _confirmed_once():
    s = _store(); s.add_edge(_edge("c1")); _confirm(s); return s


def _outcome_chain_state():
    """A head whose context_ref is X; the run then appends a draft with context_ref Y."""
    from veracium.schema import OutcomeJudgmentDraft
    mem = _mem(); e = _edge("o2"); mem.store.add_edge(e)
    ts = "2026-01-01T00:00:00+00:00"
    first = OutcomeJudgmentDraft(outcome=Outcome.CONCURRED, author=EvidenceAuthor.SYSTEM, context_ref="ctx-a",
                                 summary="s", event_timestamp=ts)
    mem.store.append_outcome_if_head(U, e.id, "run-1", None, first)
    head = mem.store._chain_head(U, e.id, "run-1")
    second = OutcomeJudgmentDraft(outcome=Outcome.CONCURRED, author=EvidenceAuthor.SYSTEM, context_ref="ctx-b",
                                  summary="s", event_timestamp=ts)
    return (mem, (U, e.id, "run-1", head.id, second))


SITES.update({sid: census._REGISTRY[sid] for sid in census.registry()})


def _first_claim():
    s = _seeded(); assert s.create_or_takeover_consolidation(U, ["e1", "e2"], "w1", 60) is not None; return s


def _lock_holder():
    p = _dbpath(); holder = SqliteStore(p); holder._conn.execute("BEGIN IMMEDIATE"); return (p, holder)


def _open_while_held(st):
    p, holder = st
    try:
        with pytest.raises(StoreVersionError) as ei:
            SqliteStore(p, busy_timeout_ms=100)
        assert ei.value.reason == "locked"
    finally:
        with _contextlib.suppress(_sqlite3.OperationalError):
            holder._conn.execute("ROLLBACK")
        holder.close()


def _absorption_plan_with_duplicate_draft():
    s = _store()
    prior = _sourced5("e-prior", "Miso", days=3); apply_supersession(s, prior, DEFAULT_RELATIONS)
    winner = _sourced5("e-winner", "cat Miso", days=0)
    plan, _ = _build_supersession_plan(s, winner, DEFAULT_RELATIONS, "op-abs")
    assert plan.contribution_drafts, "the fixture must absorb (same source, more specific value)"
    plan.contribution_drafts.append(plan.contribution_drafts[0])
    return (s, plan)


def _stored_edge():
    s = _store(); e = _edge("u1"); s.add_edge(e); return (s, e)


def _upsert_other_user(s, e):
    with pytest.raises(ValueError):
        with s._write_txn():
            s._upsert_edge_row(e.model_copy(update={"user_id": "someone-else"}))
    s.close()


SITES.update({sid: census._REGISTRY[sid] for sid in census.registry()})


@pytest.fixture
def enabled():
    census.enable(True)
    try:
        yield
    finally:
        census.enable(False)


def _delta(site_id, run):
    before = SITES[site_id].counters()
    run()
    after = SITES[site_id].counters()
    return (after["consulted"] - before["consulted"], after["fired"] - before["fired"],
            after["errors"] - before["errors"])


def test_every_declared_site_has_one_declining_execution_here_and_vice_versa():
    declared = set(SITES)
    covered = set(DECLINES) | set(SURFACE_DRIVEN)
    assert declared == covered, (sorted(declared - covered), sorted(covered - declared))


@pytest.mark.parametrize("site_id", sorted(DECLINES))
def test_one_declining_decision_moves_the_counters_by_exactly_one(site_id, enabled, monkeypatch):
    entry = DECLINES[site_id]
    if isinstance(entry, TwoPhase):
        state = entry.setup(monkeypatch)
        dc, df, de = _delta(site_id, lambda: entry.run(state))
    else:
        dc, df, de = _delta(site_id, lambda: entry(monkeypatch))
    assert (dc, df, de) == (1, 1, 0), f"{site_id}: consulted moved {dc}, fired moved {df}, errors {de}"


@pytest.mark.parametrize("site_id", sorted(SURFACE_DRIVEN))
def test_the_surface_driven_sites_decline_once_per_candidate(site_id, enabled):
    dc, df, de = _delta(site_id, SURFACE_DRIVEN[site_id])
    assert df >= 1 and dc >= df and de == 0, f"{site_id}: consulted {dc}, fired {df}, errors {de}"


def test_the_disabled_census_moves_nothing(monkeypatch):
    assert not census.enabled()
    for site_id, entry in DECLINES.items():
        with monkeypatch.context() as mp:          # one entry's patches never reach the next
            if isinstance(entry, TwoPhase):
                state = entry.setup(mp); run = lambda st=state, e=entry: e.run(st)
            else:
                run = lambda e=entry, m=mp: e(m)
            assert _delta(site_id, run) == (0, 0, 0), site_id


def test_the_trace_names_the_branch_not_the_content(enabled, monkeypatch):
    census.trace(True)
    try:
        census.trace_reset()
        DECLINES["asof.adapter.adapt.refuse"](monkeypatch)
        DECLINES["gate.scoped-assertable.entitlement"](monkeypatch)
        rows = census.trace_snapshot()
    finally:
        census.trace(False)
    labels = {(r[1], r[2]) for r in rows}
    assert ("asof.adapter.adapt.refuse", "unparseable") in labels
    assert ("gate.scoped-assertable.entitlement", "entitlement") in labels
    assert all(len(r) == 3 for r in rows)


# ---- the bypass at the four hot Edge predicates (Quentin, 2026-09-19): both paths, and the raise --
# The decision is computed ONCE (`q = <expr>`) and the census machinery runs only when enabled, so
# §4A-2's "consulted before the decision branches" is honoured in purpose (counted at the site) and
# not in letter: a predicate that RAISES is invisible to the census at these four sites. Research's
# sharpest case for the fourth arm: the bypassed path and the enabled path must raise the SAME
# exception, and `Site.__exit__` must never swallow it.

def test_a_raising_predicate_raises_identically_on_both_paths_and_is_invisible_to_the_census(monkeypatch):
    from veracium import schema as schema_mod

    def boom(_dt):
        raise RuntimeError("the predicate itself raised")
    monkeypatch.setattr(schema_mod, "as_utc", boom)
    e = _edge()
    census.enable(False)
    with pytest.raises(RuntimeError, match="the predicate itself raised"):
        e.valid_now                                             # the bypassed (shipped) path
    census.enable(True)
    try:
        dc, df, de = _delta("schema.edge.valid-now", lambda: pytest.raises(RuntimeError, e.__class__.valid_now.fget, e))
    finally:
        census.enable(False)
    assert (dc, df, de) == (0, 0, 0), "a raising predicate is not counted at a bypassed site (the trade, stated)"


def test_the_enabled_and_bypassed_paths_agree_on_every_verdict(monkeypatch):
    """The fourth arm in miniature: for each of the four hot predicates, the value the property
    returns is identical with the census off and on, on a declining and a passing edge."""
    cases = [(_edge(disc=Disclosure.QUARANTINED), _edge()), (_edge(disc=Disclosure.USE_ONLY), _edge()),
             (_edge(valid_from=NOW + timedelta(days=1)), _edge()), (_edge(disc=Disclosure.QUARANTINED), _edge())]
    props = ["quarantined", "use_only", "valid_now", "assertable"]
    for prop, (declining, passing) in zip(props, cases):
        for e in (declining, passing):
            census.enable(False); off = getattr(e, prop)
            census.enable(True)
            try:
                on = getattr(e, prop)
            finally:
                census.enable(False)
            assert off == on, (prop, e.id, off, on)
