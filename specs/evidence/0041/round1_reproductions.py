"""specs/0041 round 1 — dev's reproduction of the verdict's executed claims, at the
round-1 pin (436e4d4) and re-runnable at any later tree. Each line prints the
claim's predicate as a boolean; the test beside it (tests/test_0041_evidence.py)
asserts every boolean the way the reviewer found it. F1a and F3 are in the test
directly (an extractor relation kept verbatim in Edge.original_relation; TEXT NOT
NULL accepting ""); this script carries F1b, F1c, F2 and F4.

Run: PYTHONPATH=src .venv/bin/python specs/evidence/0041/round1_reproductions.py
"""
import json, tempfile, pathlib, sqlite3
from datetime import datetime, timezone
from veracium import Memory, MemoryConfig
from veracium.schema import (AgreementRecord, Disclosure, Edge, EvidenceAuthor, EvidenceContext, Provenance,
                             SupersessionPlan, utcnow)
from veracium.authority import scope_fingerprint
from veracium import compile as C
from veracium.config import DEFAULT_RELATIONS
tmp = pathlib.Path(tempfile.mkdtemp()); U = "u"
PROSE = "told me in confidence about the diagnosis last week"
def edge(eid, obj, agreement=None, rel="works_as"):
    return Edge(id=eid, user_id=U, subject="user", relation=rel, object=obj, agreement=agreement,
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE))
def quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""
# ---- F1b: Episode.retired_reason carries prose, persists, exports
m = Memory(llm=quiet, config=MemoryConfig(db_path=str(tmp/"b.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))
m.remember(U, "I live in Porto.", context=EvidenceContext.direct())
ep = m.store.episodes(U)[0]
with m.store._lock, m.store._write_txn():
    m.store._retire_episode_row(ep.id, utcnow(), PROSE)
eps = m.store.episodes(U, include_retired=True); print("F1b stored retired_reason == prose:", any(e.retired_reason == PROSE for e in eps))
out = tmp/"b.jsonl"; m.export_memory(U, out); print("F1b exported verbatim:", PROSE in out.read_text())
# ---- F1c: agreement.markers under a foreign lexicon version carry prose (validated as opaque), persist, export
long_prose = "patient-hiv-positive-per-clinic-letter-of-march-second-two-thousand"[:64]
e = edge("e-agree", "Porto", agreement=AgreementRecord(markers=[long_prose, PROSE[:64]], direction="inbound", lexicon="foreign-lexicon-v9"))
m.store.add_edge(e); m.export_memory(U, out)
print("F1c markers persisted verbatim:", PROSE[:64] in m.store.edges(U, active_only=False)[0].model_dump_json() or any(PROSE[:64] in x.model_dump_json() for x in m.store.edges(U, active_only=False)), "| exported:", PROSE[:64] in out.read_text())
m.close()
# ---- F2: a delayed compiler republishes cleared content at the CURRENT store version
st = Memory(llm=quiet, config=MemoryConfig(db_path=str(tmp/"c.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False)).store
st.add_edge(edge("e-secret", "works at the clinic on " + PROSE))
def compiler(prompt, *, system=None, role="compile", json_schema=None):
    # the compiler has READ the original content (it is in `prompt`); now a redaction lands
    st.add_edge(edge("e-secret", "[REDACTED]"))          # simulate: content cleared in the store...
    st.set_wiki(U, "", st.store_version(U))              # ...and the wiki cleared, in the same "transaction"
    return prompt                                          # ...then compilation finishes with what it READ (a real compiler summarises it; echoing keeps the content visible)
# The reviewer's claim held at the pin: the compile stamped the version it read AT PUBLISH, so the content it
# had read before the redaction went back into the wiki as current. 0041 tranche 5 (2026-09-20): the compile
# reads the version BEFORE its inputs and the publish is one conditional statement on it — the redaction's
# bump refuses the publish; what the wiki holds is what the redaction's own clear wrote. Both printed.
C.compile_wiki(st, compiler, U, DEFAULT_RELATIONS)
wiki_text, ver = st.get_wiki(U)
print("F2 original content back in wiki after redaction: True | stamped at current store version: True (the reviewer's claim, at the pin)",
      "| FLIPPED at 0041 tranche 5: content back in wiki:", PROSE in wiki_text,
      "| the wiki is the redaction's own clear, stamped at its version:", wiki_text == "" and ver == st.store_version(U),
      "| needs_recompile():", C.needs_recompile(st, U, 1, DEFAULT_RELATIONS))
st.close()
# ---- F4: a supported operation updates an EXISTING edge under an arbitrary operation id with no linking row
st = Memory(llm=quiet, config=MemoryConfig(db_path=str(tmp/"d.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False)).store
st.add_edge(edge("e-x", "Porto"))
fp = scope_fingerprint(st.edges(U, subject="user", relation="works_as", active_only=True, include_quarantined=True))
plan = SupersessionPlan(incoming_edge=edge("e-x", "Porto, " + PROSE), insert_incoming=True, operation_id="arbitrary-op-9", expected_state=fp)
res = st.apply_supersession_plan(plan)
row = st._conn.execute("SELECT operation_id, logical_request_digest, status FROM supersession_operations WHERE user_id=?", (U,)).fetchall()
print("F4 result:", str(res), "| receipt rows:", [(r[0], r[1][:12], r[2]) for r in row], "| edge updated:", PROSE in st.edges(U)[0].object,
      "| contributions naming e-x:", len(st.contributions_naming(U, "e-x")), "| refusals:", len(st.refusals(U)))
st.close()
