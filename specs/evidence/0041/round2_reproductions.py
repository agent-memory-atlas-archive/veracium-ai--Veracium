"""specs/0041 round 2 — dev's reproduction of the verdict's executed claims, at the
round-2 pin (dc695b9; src unchanged at the tree this runs in) and re-runnable at any
later tree. Each line prints the claim's predicate as a boolean the way the reviewer
found it; the tests beside it (tests/test_0041_evidence.py) assert them. F4, F6's
evidence_ref disagreement and F7 are text findings on the spec/examples and carry no
executable claim.

Run (from the repo root): .venv/bin/python specs/evidence/0041/round2_reproductions.py
"""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
from veracium import Memory, MemoryConfig, semantic
from veracium.schema import (AgreementRecord, Disclosure, Edge, EvidenceAuthor, EvidenceContext,
                             Provenance, DISPOSITIONED_REASONS)
from veracium.budgets import sanitize_llm_body
from veracium.store import sqlite as _sqlite

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


def edge(eid, obj, **kw):
    return Edge(id=eid, user_id=U, subject="user", relation="works_as", object=obj,
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                      disclosure=Disclosure.MENTIONABLE), **kw)


def quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def mem(name, llm=quiet):
    return Memory(llm=llm, config=MemoryConfig(db_path=str(tmp / name), wiki_recompile_after_writes=0,
                                               scope_groups={}, require_source_id=False))


# ---- F1a: the embedding upsert's check-then-insert is not atomic across CONNECTIONS
ma, mb = mem("a.db"), mem("a.db")            # two connections to one database
A, B = ma.store, mb.store
A.add_edge(edge("e-1", "works at the clinic; hiv-positive since 2019"))
orig = A.edges(U)[0]; d_orig = semantic.content_digest(orig)
real = semantic.content_digest

def legacy_insert_edge(store, edge):
    """The PRE-RESTRICTION writer's shape (direct SQL): 0041 tranche 1's mirror refuses a marker-carrying
    write, so a tombstone ROW is planted the way an older store holds one (§4h(iii))."""
    js = edge.model_dump_json()
    store._conn.execute("INSERT OR REPLACE INTO edges(id,user_id,subject,relation,object,active,quarantined,json) VALUES(?,?,?,?,?,?,?,?)",
                        (edge.id, edge.user_id, edge.subject, edge.relation, edge.object, int(edge.active), int(edge.quarantined), js))
    store._conn.commit()

def interleave(live):
    """Called by A's upsert_embedding BETWEEN its SELECT and its INSERT (no transaction
    is open on A). B commits a simulated redaction and removes the embedding here."""
    semantic.content_digest = real                 # one shot
    tomb = orig.model_copy(update={"subject": MARKER, "relation": MARKER, "object": MARKER, "note": MARKER})
    legacy_insert_edge(B, tomb)                   # the redaction, committed on B (a planted row: the mirror refuses the write path)
    B._conn.execute("DELETE FROM edge_embedding WHERE edge_id='e-1'"); B._conn.commit()
    return real(live)                             # A checks the digest of the row it ALREADY read
semantic.content_digest = interleave
ok = A.upsert_embedding(edge_id="e-1", user_id=U, embedder_id="emb@1", content_digest=d_orig, dim=2,
                        vec=semantic.pack_vec([1.0, 0.0]) if hasattr(semantic, "pack_vec") else b"\x00" * 8,
                        built_at="2026-09-15T00:00:00Z")
semantic.content_digest = real
rows = B._conn.execute("SELECT content_digest FROM edge_embedding WHERE edge_id='e-1'").fetchall()
live_now = B.edges(U, active_only=False)[0]
print("F1a upsert reported success after B's redaction committed:", ok)
print("F1a stale vector STORED under the original digest:", [r[0] for r in rows] == [d_orig])
print("F1a live edge is the tombstone (search would exclude the row by digest):",
      live_now.object == MARKER and semantic.content_digest(live_now) != d_orig)
ma.close(); mb.close()

# ---- F1b: the packaged INV-12 test passes when embedded_text is widened with original_relation
def inv12_sets(base):
    d0, t0 = semantic.content_digest(base), semantic.embedded_text(base)
    md, mt = set(), set()
    for name in type(base).model_fields:
        cur = getattr(base, name)
        if not isinstance(cur, str) or isinstance(cur, bool):
            continue
        try:
            m = base.model_copy(update={name: cur + "-changed"})
        except Exception:
            continue
        if semantic.content_digest(m) != d0: md.add(name)
        if semantic.embedded_text(m) != t0: mt.add(name)
    return md, mt
packaged_fixture = edge("e-inv12", "Porto", note="n")            # original_relation UNSET, as packaged
populated_fixture = edge("e-inv12b", "Porto", note="n", original_relation="worked-at-the-clinic")
real_text = semantic.embedded_text
semantic.embedded_text = lambda e: f"{real_text(e)} {e.original_relation or ''}"   # the widening
md1, mt1 = inv12_sets(packaged_fixture); md2, mt2 = inv12_sets(populated_fixture)
semantic.embedded_text = real_text
print("F1b widened embedder still passes on the PACKAGED fixture (subset holds):", mt1 <= md1)
print("F1b the same widening is caught once original_relation is POPULATED:", not (mt2 <= md2), sorted(mt2 - md2))

# ---- F2: the marker survives sanitize_llm_body, ordinary ingestion and storage with NO redaction
print("F2 sanitize_llm_body leaves the marker intact:", sanitize_llm_body(MARKER) == MARKER)
def emitting(prompt, *, system=None, role="compile", json_schema=None):
    if role == "distill":
        return json.dumps({"triples": [{"subject": "user", "relation": "works_as", "object": MARKER, "note": MARKER}],
                           "episode": "x", "instructions": []})
    return ""
m2 = mem("b.db", emitting)
try:
    m2.remember(U, "I work somewhere.", context=EvidenceContext.direct()); refused = False
except ValueError as exc:                                     # 0041 tranche 1: INV-11's mirror at the upsert
    refused = "redaction marker" in str(exc)
stored = [e for e in m2.store.edges(U, active_only=False) if e.object == MARKER]
print("F2 an edge whose object IS the marker was stored by remember() (no redaction happened):", len(stored) == 1,
      "| REFUSED by INV-11's mirror (0041 tranche 1):", refused)
m2.close()

# ---- F3: the proposed five-value vocabulary excludes every existing disposition reason
proposed = {"subject_request", "operator_policy", "erroneous_capture", "legal_obligation", "imported_notice"}
existing = set(DISPOSITIONED_REASONS)
print("F3 existing disposition reasons:", len(existing), sorted(existing))
print("F3 ALL of them are outside the proposed vocabulary:", not (existing & proposed))

# ---- F5: a current-format operation updates a prior through prior_upserts; no row links that prior to the OPERATION
OBJ = {"o": "Acme"}
def acme(prompt, *, system=None, role="compile", json_schema=None):
    if role == "distill":
        return json.dumps({"triples": [{"subject": "user", "relation": "works_as", "object": OBJ["o"]}],
                           "episode": "x", "instructions": []})
    return ""
m5 = mem("c.db", acme); st5 = m5.store
m5.remember(U, "I work at Acme.", context=EvidenceContext.direct())          # the prior: "Acme"
OBJ["o"] = "Acme Corp"
m5.remember(U, "I work at Acme Corp.", context=EvidenceContext.direct())     # subsumes the prior: ABSORBED through prior_upserts
ops = st5._conn.execute("SELECT operation_id, request_digest_domain, response FROM supersession_operations WHERE user_id=?", (U,)).fetchall()
absorbed = [e for e in st5.edges(U, active_only=False) if e.invalidation_reason == "absorbed_duplicate"]
prior_ids = [e.id for e in absorbed]
resp_names_prior = any(pid in (r[2] or "") for pid in prior_ids for r in ops)
ledger_cols = [c[1] for c in st5._conn.execute("PRAGMA table_info(contribution_ledger)").fetchall()]
refusal_cols = [c[1] for c in st5._conn.execute("PRAGMA table_info(supersession_refusals)").fetchall()]
ledger_rows = st5._conn.execute("SELECT COUNT(*) FROM contribution_ledger WHERE user_id=?", (U,)).fetchone()[0]
print("F5 operations recorded:", len(ops), "| domains:", sorted({r[1] for r in ops}), "| absorbed (upserted) priors:", prior_ids)
print("F5 response is counts only (no ids):", all(all(isinstance(v, (int, bool)) for v in json.loads(r[2], object_pairs_hook=_no_dup_pairs).values()) for r in ops if r[2]), "| response names the prior id:", resp_names_prior)
print("F5 no linking column: contribution_ledger has operation_id:", "operation_id" in ledger_cols, "| supersession_refusals has operation_id:", "operation_id" in refusal_cols, "| ledger rows:", ledger_rows)
m5.close()

# ---- F6: an Edge.outcome_counts prose KEY persists and exports through the existing APIs
m6 = mem("d.db"); PROSE = "told me in confidence: hiv-positive since 2019"
m6.store.add_edge(edge("e-oc", "Porto", outcome_counts={PROSE: 1}))
back = m6.store.edges(U, active_only=False)[0]; out = tmp / "d.jsonl"; m6.export_memory(U, out)
print("F6 prose key persisted in outcome_counts:", PROSE in back.outcome_counts, "| exported verbatim:", PROSE in out.read_text())
m6.close()
