"""specs/0041 round 4 — dev's reproduction of the verdict's executed claims, at the
round-4 pin (ef46d4a; src unchanged at the tree this runs in). F3's two executed
claims; F4's is reproduced inside tests/test_0041_evidence.py (the key-widening
control). F1 and F2 are text findings.

Run from the repo root: .venv/bin/python specs/evidence/0041/round4_reproductions.py
"""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
from datetime import datetime, timezone
from veracium import Memory, MemoryConfig
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, EvidenceContext, Provenance, DISPOSITIONED_REASONS
from veracium.source_identity import resolve_origin, source_identity_digest
from veracium.store import revocation as rv

U = "u"; tmp = pathlib.Path(tempfile.mkdtemp())


def quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def mem(name):
    return Memory(llm=quiet, config=MemoryConfig(db_path=str(tmp / name), wiki_recompile_after_writes=0,
                                                 scope_groups={}, require_source_id=False))


# ---- F3a: the journal ALREADY enforces DISPOSITIONED_REASONS on invalidation events; other kinds carry reason=None
m = mem("a.db"); st = m.store
st.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="works_as", object="Porto",
                 provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)))
try:
    st.invalidate_edge("e-1", datetime(2026, 9, 15, tzinfo=timezone.utc), "told me in confidence"); refused = False
except ValueError as e:
    refused = "DISPOSITIONED_REASONS" in str(e)
print("F3a an invalidation with a reason outside DISPOSITIONED_REASONS is REFUSED by the journal writer:", refused)
st.invalidate_edge("e-1", datetime(2026, 9, 15, tzinfo=timezone.utc), "superseded")
rows = st._conn.execute("SELECT kind, reason FROM edge_event WHERE edge_id='e-1' ORDER BY seq").fetchall()
print("F3a journal rows (kind, reason):", rows, "| non-invalidation kinds carry None:", all(r is None for k, r in rows if k != "invalidated"),
      "| the invalidation carries the registry value:", any(k == "invalidated" and r == "superseded" for k, r in rows))
m.close()

# ---- F3b: `source_revocations.reason` keeps the caller's explanatory sentence; the affected edge and episode get `revoked_source`
m2 = mem("b.db"); st2 = m2.store
prov = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE, source_id="mb-x")
st2.add_edge(Edge(id="e-2", user_id=U, subject="user", relation="works_as", object="Porto", provenance=prov))
st2.add_episode(Episode(id="ep-2", user_id=U, date="2026-09-01", summary="s", provenance=prov))
digest = source_identity_digest(resolve_origin(None, st2.local_origin()), "mb-x")
SENTENCE = "the mailbox was compromised on 3 March; every record from it is untrusted"
rv.revoke_source(st2, U, digest, "revoke", SENTENCE, "2026-09-15T00:00:00Z")
row = st2._conn.execute("SELECT action, reason FROM source_revocations WHERE user_id=?", (U,)).fetchone()
e = [x for x in st2.store_edges(U) if x.id == "e-2"][0] if hasattr(st2, "store_edges") else [x for x in st2.edges(U, active_only=False) if x.id == "e-2"][0]
ep = [x for x in st2.episodes(U, include_retired=True) if x.id == "ep-2"][0]
print("F3b source_revocations.reason == the caller's sentence:", row == ("revoke", SENTENCE),
      "| the affected edge's invalidation_reason:", e.invalidation_reason, "| the episode's retired_reason:", ep.retired_reason)
print("F3b 'revoked_source' names the EFFECT's reason, not the revocation row's vocabulary:", e.invalidation_reason == "revoked_source" and row[1] != "revoked_source")
m2.close()
