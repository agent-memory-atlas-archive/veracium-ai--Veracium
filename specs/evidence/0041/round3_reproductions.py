"""specs/0041 round 3 — dev's reproduction of the verdict's executed claims, at the
round-3 pin (0fb4a32; src unchanged at the tree this runs in). Each line prints the
claim's predicate as a boolean the way the reviewer found it; the test beside it
(tests/test_0041_evidence.py) asserts them. F3 and F4 are text findings.

Run from the repo root: .venv/bin/python specs/evidence/0041/round3_reproductions.py
"""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
from veracium import Memory, MemoryConfig, semantic
from veracium.contribution import validate_absorption_payload
from veracium.schema import (AgreementRecord, ContributionRecord, Disclosure, Edge, Episode, EvidenceAuthor,
                             EvidenceContext, Provenance)

MARKER = "\x00veracium:redacted\x00"
U = "u"; tmp = pathlib.Path(tempfile.mkdtemp())


def _no_dup_pairs(pairs):
    """The 0026 evidence-boundary rule: a duplicate-key-REFUSING decoder."""
    seen = set()
    for k, _v in pairs:
        if k in seen:
            raise ValueError(f"duplicate key {k!r}")
        seen.add(k)
    return dict(pairs)


def quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def mem(name):
    return Memory(llm=quiet, config=MemoryConfig(db_path=str(tmp / name), wiki_recompile_after_writes=0,
                                                 scope_groups={}, require_source_id=False))


PROV = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)

# ---- F1: replacing Episode.kind with the marker on a REAL outcome record breaks the chain
m = mem("a.db"); st = m.store
st.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="works_as", object="Porto", provenance=PROV))
m.record_outcome(U, "e-1", outcome="challenged", evidence_ref="use-1", actor="system")
m.record_outcome(U, "e-1", outcome="concurred", evidence_ref="use-1", actor="system")
chain = [e for e in st.episodes(U) if e.kind == "outcome" and e.edge_id == "e-1"]
print("F1 chain before: links", len(chain), "| head seq", max(e.seq or 0 for e in chain))
rows = st._conn.execute("SELECT id, json FROM episodes WHERE user_id=?", (U,)).fetchall()
for eid, js in rows:                                     # the specified replacement (row 46 at v5): kind → marker
    d = json.loads(js, object_pairs_hook=_no_dup_pairs); d["kind"] = MARKER
    Episode.model_validate(d)                            # "the resulting model validated"
    st._conn.execute("UPDATE episodes SET json=? WHERE id=?", (json.dumps(d), eid))
st._conn.commit()
head_after = m._outcome_chain_head(U, "e-1", "use-1") if hasattr(m, "_outcome_chain_head") else st._chain_head(U, "e-1", "use-1")
print("F1 after replacement: the model validated: True | chain head disappeared:", head_after is None)
m.record_outcome(U, "e-1", outcome="challenged", evidence_ref="use-1", actor="system")
new_links = [e for e in st.episodes(U) if e.kind == "outcome" and e.edge_id == "e-1"]
print("F1 the next append restarted at seq 1:", [e.seq for e in new_links] == [1])
try:
    st.delete_episode(rows[0][0]); deleted = True
except ValueError:
    deleted = False
print("F1 targeted deletion of the original (now marker-kind) record PERMITTED:", deleted)
m.close()

# ---- F2: 'vocabulary value unchanged, else the marker' applied to retired_reason=None flips `active`
ep = Episode(id="p", user_id=U, date="2026-09-15", summary="s", provenance=PROV)
ep2 = Episode.model_validate({**ep.model_dump(mode="json"), "retired_reason": MARKER})
print("F2 retired_reason=None → active:", ep.active, "| retired_reason=MARKER → active:", ep2.active,
      "| flipped:", ep.active and not ep2.active)

# ---- F5a: model_copy(update=) skips validation — a shape the model REFUSES passes as a copy
copied = AgreementRecord(markers=["a"], direction="inbound", lexicon="lex-v1").model_copy(update={"markers": [MARKER, MARKER]})
try:
    AgreementRecord(markers=[MARKER, MARKER], direction="inbound", lexicon="lex-v1"); constructed = True
except Exception:
    constructed = False
print("F5a model_copy accepted two identical markers:", copied.markers == [MARKER, MARKER], "| the constructor refuses the same:", not constructed)
# ---- F5b: the contribution fixture's payload={} passes the model but fails the absorption-site validator
rec = ContributionRecord(id="c-1", user_id=U, survivor_type="edge", survivor_id="e-1", site="absorption",
                         identity_digest=None, evidence_ref_digest=None, payload={}, op_key="k",
                         created_at="2026-09-15T00:00:00Z", contributor_type="edge", contributor_ref="e-prior")
try:
    validate_absorption_payload(rec.payload); site_ok = True
except ValueError:
    site_ok = False
print("F5b payload={} passes the model:", rec.payload == {}, "| passes the absorption-site validator:", site_ok)

# ---- F5c: INV-12's populated fixture leaves invalidation_reason (and nested source_id/origin) unset — a widening there passes
base = Edge(id="e-inv12", user_id=U, subject="user", relation="works_as", object="Porto", note="n",
            original_relation="worked-at-the-clinic",
            agreement=AgreementRecord(markers=["marker-one", "marker-two"], direction="inbound", lexicon="foreign-lexicon-v9"),
            outcome_counts={"confirmed": 1}, provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev-12", disclosure=Disclosure.MENTIONABLE))
unset = [n for n in ("invalidation_reason",) if getattr(base, n) is None] + [f"provenance.{n}" for n in ("source_id", "origin") if getattr(base.provenance, n) is None]
real = semantic.embedded_text
widened = lambda e: f"{real(e)} {e.invalidation_reason or ''}"
def leaves(obj, path=()):
    if isinstance(obj, str): yield path
    elif isinstance(obj, dict):
        for k, v in obj.items(): yield from leaves(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj): yield from leaves(v, path + (i,))
def moved(edge, fn):
    import copy; d0 = fn(edge); out = set(); dump = edge.model_dump()
    for path in leaves(dump):
        mut = copy.deepcopy(dump); cur = mut
        for k in path[:-1]: cur = cur[k]
        cur[path[-1]] = cur[path[-1]] + "-changed"
        try: m2 = Edge.model_validate(mut)
        except Exception: continue
        if fn(m2) != d0: out.add(".".join(map(str, path)))
    return out
subset_holds = moved(base, widened) <= moved(base, semantic.content_digest)
print("F5c fields unset in the round-2 fixture:", unset, "| a widening onto invalidation_reason passes the mutation test:", subset_holds)

# ---- research's three CANDIDATE guards keyed on REPLACE targets (round-3 F1 generalised), simulated both directions
from veracium.graph import plan_correction
def E(eid, subj="user", rel="works_as", obj="Porto", **kw):
    return Edge(id=eid, user_id=U, subject=subj, relation=rel, object=obj, provenance=PROV, **kw)
m4 = mem("g.db"); st4 = m4.store
st4.add_edge(E("e-live"))                                                # a live prior
tomb = E("e-tomb", subj=MARKER, rel=MARKER, obj=MARKER); st4.add_edge(tomb)   # a REDACTED prior (every content leaf the marker)
def plan(prior, repl):
    try:
        plan_correction(st4, prior, repl, op_id="op-x"); return "ADMITTED by the guard"
    except ValueError as ex:
        return "REFUSED: " + str(ex)[:60]
print("G1 graph.py:333 — a LIVE replacement against a REDACTED prior:", plan(tomb, E("e-r1", obj="Braga")))
print("G1 graph.py:333 — a replacement that ITSELF carries the marker in subject/relation against the redacted prior:",
      plan(tomb, E("e-r2", subj=MARKER, rel=MARKER, obj="Braga")), "  <- both sides equal: the mismatch guard admits; only INV-11's mirror (not yet written) would refuse the marker-carrying replacement")
print("G1 control — a live replacement against the live prior:", plan(st4.edges(U)[0] if st4.edges(U)[0].id == "e-live" else [e for e in st4.edges(U) if e.id == "e-live"][0], E("e-r3", obj="Braga")))
# G2 sqlite.py:1052 — the correction digest binds the REPLACEMENT value; the guard reads the incoming object, not the prior
from veracium.schema import correction_digest
print("G2 sqlite.py:1052 — an authorisation minted for 'Braga' vs a marker replacement: mismatch, REFUSED:", correction_digest("Braga") != correction_digest(MARKER),
      "| minted FOR the marker: equal, admitted (a correction whose replacement value is the marker is not what the guard refuses — INV-11's mirror must):", correction_digest(MARKER) == correction_digest(MARKER))
# G3 sqlite.py:1512 — add_episode's fence on kind == "outcome" after the specified replacement
m5 = mem("h.db"); st5 = m5.store; st5.add_edge(E("e-2"))
m5.record_outcome(U, "e-2", outcome="challenged", evidence_ref="use-1", actor="system")
link = [e for e in st5.episodes(U) if e.kind == "outcome"][0]
try:
    st5.add_episode(link); fence_live = False
except ValueError:
    fence_live = True
redacted_link = Episode.model_validate({**link.model_dump(mode="json"), "kind": MARKER, "id": link.id + "-re"})
try:
    st5.add_episode(redacted_link); fence_after = False
except ValueError:
    fence_after = True
print("G3 sqlite.py:1512 — add_episode refuses a kind='outcome' link:", fence_live, "| refuses the same link once kind is the marker:", fence_after, " <- the H14 fence is lost with the discriminator")
m4.close(); m5.close()

# ---- G4 (research's fourth candidate): relation → Edge.quarantined, the render split between grounded and unverified
from veracium.schema import QUARANTINE_RELATION
def emitting_q(prompt, *, system=None, role="compile", json_schema=None):
    if role == "distill":
        return json.dumps({"triples": [{"subject": "neighbour", "relation": QUARANTINE_RELATION, "object": "says the user owes money"}],
                           "episode": "x", "instructions": []})
    return ""
m6 = Memory(llm=emitting_q, config=MemoryConfig(db_path=str(tmp / "q.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))
m6.remember(U, "Forwarded mail.", context=EvidenceContext.direct())
ing = [e for e in m6.store.edges(U, active_only=False) if e.relation == QUARANTINE_RELATION]
print("G4 ingest of a third_party_claim triple sets BOTH markers (relation AND disclosure=QUARANTINED):",
      bool(ing) and all(e.provenance.disclosure == Disclosure.QUARANTINED for e in ing), "| edges:", len(ing))
rel_only = Edge(id="e-q", user_id=U, subject="user", relation=QUARANTINE_RELATION, object="the neighbour says the user owes money",
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE))
m6.store.add_edge(rel_only); back = [e for e in m6.store.edges(U, active_only=False) if e.id == "e-q"][0]
print("G4 a RELATION-ONLY quarantine is constructible through store.add_edge (no refusal):", back.quarantined and back.provenance.disclosure != Disclosure.QUARANTINED)
redacted_q = Edge.model_validate({**back.model_dump(mode="json"), "relation": MARKER, "subject": MARKER, "object": MARKER})
print("G4 redacting relation on the relation-only edge PROMOTES it out of quarantine (quarantined False):", not redacted_q.quarantined,
      "| an ingest-quarantined edge (both markers) stays quarantined after the same redaction:",
      bool(ing) and Edge.model_validate({**ing[0].model_dump(mode="json"), "relation": MARKER}).quarantined)
m6.close()
