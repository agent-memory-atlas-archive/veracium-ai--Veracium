"""specs/0041 tranche 5 — §4e's DELAYED WRITERS, bound: a read-compute-publish path makes its read and its publish
one transaction under the DATABASE lock (the embedding upsert: BEGIN IMMEDIATE before the read) or one statement
(the wiki publish: written only if the version read before the inputs is still the store's). The controls: the
same paths, uninterleaved, publish.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from veracium import Memory, MemoryConfig, compile as C
from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance

U = "u"


def _quiet(prompt, *, system=None, role="compile", json_schema=None):
    if role == "distill":
        return json.dumps({"triples": [], "episode": "x", "instructions": []})
    return "## USER MODEL\n- (compiled)\n" if role == "compile" else ""


def _cfg(tmp_path, name="s.db"):
    return dict(db_path=str(tmp_path / name), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False)


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)


def test_the_wiki_publish_is_one_conditional_statement_on_the_version_read_before_the_inputs(tmp_path):
    """Connection B redacts BETWEEN A's input read and A's publish: A's compile must not publish (the store moved),
    and the wiki row stays absent — the next read recompiles from the store of record. The control below: no
    interleaving, the row is written under the version the compile read."""
    A = Memory(llm=_quiet, config=MemoryConfig(**_cfg(tmp_path)))
    B = Memory(llm=_quiet, config=MemoryConfig(**_cfg(tmp_path)))
    A.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="works_as", object="night auditor at the Grand", provenance=_prov()))
    real = C._grounded_inputs
    seen = {}
    def interleaved(store, user_id, relations):
        out = real(store, user_id, relations)
        seen["inputs"] = out
        B.redact(U, edge_id="e-1", reason="subject_request")        # the store moves after the read
        return out
    C._grounded_inputs = interleaved
    try:
        wiki = C.compile_wiki(A.store, _quiet, U, A.config.relations)
    finally:
        C._grounded_inputs = real
    assert wiki                                                      # this call's own text, compiled from a consistent read
    assert A.store._conn.execute("SELECT COUNT(*) FROM wiki WHERE user_id=?", (U,)).fetchone()[0] == 0   # NOT published
    assert seen["inputs"][0] and any(e.id == "e-1" for e in seen["inputs"][0])                            # the read did see the content
    # the control: uninterleaved, the publish lands under the version the compile read
    before = A.store.store_version(U)
    C.compile_wiki(A.store, _quiet, U, A.config.relations)
    row = A.store._conn.execute("SELECT store_version FROM wiki WHERE user_id=?", (U,)).fetchone()
    assert row is not None and row[0] == before


def test_set_wiki_writes_only_when_the_counter_still_matches_and_says_so(tmp_path):
    m = Memory(llm=_quiet, config=MemoryConfig(**_cfg(tmp_path))); st = m.store
    st.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="lives_in", object="Porto", provenance=_prov()))
    v = st.store_version(U)
    assert st.set_wiki(U, "compiled at v", v) is True
    st.add_edge(Edge(id="e-2", user_id=U, subject="user", relation="has_pet", object="Miso", provenance=_prov()))   # the counter moves
    assert st.set_wiki(U, "compiled at v, published late", v) is False                                              # refused by the statement
    assert st._conn.execute("SELECT text FROM wiki WHERE user_id=?", (U,)).fetchone()[0] == "compiled at v"
    assert st.set_wiki(U, "compiled at v+1", st.store_version(U)) is True


def test_the_embedding_upsert_holds_the_database_lock_across_its_read_and_its_write(tmp_path):
    """Inside A's window a second connection's write WAITS behind its busy timeout (specs/0028 §5: never refused
    for the window as such) and, the window outlasting the timeout here, is refused loudly and writes nothing;
    uninterleaved, the upsert stores the vector and returns True (the control)."""
    from veracium import semantic
    A = Memory(llm=_quiet, config=MemoryConfig(**_cfg(tmp_path))).store
    B = Memory(llm=_quiet, config=MemoryConfig(**_cfg(tmp_path))).store
    e = Edge(id="e-1", user_id=U, subject="user", relation="works_as", object="x", provenance=_prov())
    A.add_edge(e)
    d = semantic.content_digest(e)
    assert A.upsert_embedding(edge_id="e-1", user_id=U, embedder_id="emb@1", content_digest=d, dim=2, vec=b"\x00" * 8,
                              built_at="2026-09-20T00:00:00Z") is True                                          # the control
    assert not A._conn.in_transaction
    # inside A's window, B's ordinary write cannot take the lock: the lock refusal is loud on B's side
    real = semantic.content_digest
    refused = {}
    def probe(live):
        try:
            B.add_edge(Edge(id="e-2", user_id=U, subject="user", relation="has_pet", object="Miso", provenance=_prov()))
        except sqlite3.OperationalError as exc:
            refused["B"] = str(exc)
        return real(live)
    semantic.content_digest = probe
    try:
        A.upsert_embedding(edge_id="e-1", user_id=U, embedder_id="emb@2", content_digest=d, dim=2, vec=b"\x00" * 8,
                           built_at="2026-09-20T00:00:00Z")
    finally:
        semantic.content_digest = real
    assert "write lock" in refused.get("B", ""), refused
    assert B._conn.execute("SELECT COUNT(*) FROM edges WHERE id='e-2'").fetchone()[0] == 0
