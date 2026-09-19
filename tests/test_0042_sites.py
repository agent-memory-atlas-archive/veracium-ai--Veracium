"""specs/0042 (accepted v9.2) — the RUNTIME leg over the product's declared sites, per tranche.

The static scan says a binding exists; this executes ONE declining decision at every declared
site and asserts the id's counters MOVED BY EXACTLY ONE — Δconsulted == 1 and Δfired == 1 —
between a before and an after (a LEVEL is the proxy round 4 refused). Every declared id must
have an entry here (completeness), and every entry must name a declared id; the disabled
census (the shipped default) moves nothing.

Tranche 2 (2026-09-19): gate, schema, compile, grounding, authority, asof — 28 sites.
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
    dc, df, de = _delta(site_id, lambda: DECLINES[site_id](monkeypatch))
    assert (dc, df, de) == (1, 1, 0), f"{site_id}: consulted moved {dc}, fired moved {df}, errors {de}"


@pytest.mark.parametrize("site_id", sorted(SURFACE_DRIVEN))
def test_the_surface_driven_sites_decline_once_per_candidate(site_id, enabled):
    dc, df, de = _delta(site_id, SURFACE_DRIVEN[site_id])
    assert df >= 1 and dc >= df and de == 0, f"{site_id}: consulted {dc}, fired {df}, errors {de}"


def test_the_disabled_census_moves_nothing(monkeypatch):
    assert not census.enabled()
    for site_id, run in DECLINES.items():
        assert _delta(site_id, lambda: run(monkeypatch)) == (0, 0, 0), site_id


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
