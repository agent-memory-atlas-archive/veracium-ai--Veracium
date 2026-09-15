"""specs/0041 (targeted redaction, draft) — the round-1 verdict's executed claims,
reproduced as the reviewer found them and kept runnable, so v3's carrier
inventory and contracts are written against behaviour that is asserted here
rather than recalled. Every check below FAILS the day the behaviour changes —
which is the point: when 0041 is implemented, these become the negative
controls the redaction contract must turn around, one by one.
"""

import json

import pytest
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

from veracium import Memory, MemoryConfig
from veracium.schema import EvidenceContext

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0041"
PROSE = "told me in confidence about the diagnosis last week"


def _llm_with_relation(relation):
    def llm(prompt, *, system=None, role="compile", json_schema=None):
        if role == "distill":
            return json.dumps({"triples": [{"subject": "user", "relation": relation, "object": "Porto",
                                            "quote": "I live in Porto"}], "episode": "x", "instructions": []})
        return json.dumps({"triples": [], "episode": "x", "instructions": []})
    return llm


def test_f1a_an_unrecognised_extractor_relation_is_kept_verbatim_in_original_relation(tmp_path):
    """Round-1 F1: §2 classified `Edge.original_relation` as non-content; ingestion
    keeps an unrecognised extractor relation there verbatim (the relation itself
    becomes `unclassified`), and it exports."""
    mem = Memory(llm=_llm_with_relation(PROSE),
                 config=MemoryConfig(db_path=str(tmp_path / "a.db"), wiki_recompile_after_writes=0,
                                     scope_groups={}, require_source_id=False))
    mem.remember("u", "I live in Porto. " + PROSE + ".", context=EvidenceContext.direct())
    edges = mem.store.edges("u", active_only=False, include_quarantined=True)
    assert [(e.relation, e.original_relation) for e in edges] == [("unclassified", PROSE)]
    out = tmp_path / "a.jsonl"
    mem.export_memory("u", out)
    assert PROSE in out.read_text()
    mem.close()


def test_f3_a_text_not_null_column_accepts_the_empty_string():
    """Round-1 F3: §4b's supporting claim was that `TEXT NOT NULL` excludes the
    empty string; it does not — the reserved marker needs its own definition."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE t(x TEXT NOT NULL)")
    c.execute("INSERT INTO t VALUES('')")
    assert c.execute("SELECT count(*) FROM t WHERE x = ''").fetchone()[0] == 1


def test_the_round1_reproduction_script_reports_every_claim_as_the_reviewer_found_it():
    """F1b, F1c, F2 and F4 through the packaged script itself (P4: evidence that
    RUNS behaviour). Each expected token is the predicate the reviewer stated."""
    r = subprocess.run([sys.executable, str(EVIDENCE / "round1_reproductions.py")],
                       cwd=ROOT, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    out = r.stdout
    assert "F1b stored retired_reason == prose: True" in out and "F1b exported verbatim: True" in out
    assert "F1c markers persisted verbatim: True | exported: True" in out
    assert ("F2 original content back in wiki after redaction: True | stamped at current store version: True "
            "| needs_recompile(): False") in out
    assert "| edge updated: True | contributions naming e-x: 0 | refusals: 0" in out and "'applied'" in out


def test_the_carrier_enumeration_reproduces_its_committed_output_byte_for_byte():
    """Research's carrier enumeration (their original sha16 50531999b8caf5f0 at
    research commit 2dfdf3ab; the packaged copy resolves the repository from its
    own location) regenerates `carrier_enumeration_OUTPUT.txt` exactly: 15
    tables, 84 terminal (model, field) identities, 64 carriers + 20 non-carriers.
    v3's §2 quotes those counts; this is the node that keeps them honest."""
    r = subprocess.run([sys.executable, str(EVIDENCE / "carrier_enumeration.py")],
                       cwd=EVIDENCE, env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout == (EVIDENCE / "carrier_enumeration_OUTPUT.txt").read_text()
    assert "-> 64 CARRIERS" in r.stdout and "-> 20 NON-CARRIERS" in r.stdout


def _inv12_sets(base, content_digest, embedded_text):
    """The fields, top-level AND nested, whose mutation moves each projection —
    derived by mutation over every string-valued leaf of a POPULATED edge."""
    import copy
    d0, t0 = content_digest(base), embedded_text(base)
    moves_digest, moves_text = set(), set()
    dump = base.model_dump()

    def leaves(obj, path=()):
        if isinstance(obj, str) and not isinstance(obj, bool):
            yield path
        elif isinstance(obj, dict):
            for k, v in obj.items():
                yield from leaves(v, path + (k,))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                yield from leaves(v, path + (i,))

    for path in leaves(dump):
        mutated = copy.deepcopy(dump)
        cur = mutated
        for k in path[:-1]:
            cur = cur[k]
        cur[path[-1]] = cur[path[-1]] + "-changed"
        try:
            m = type(base).model_validate(mutated)
        except Exception:
            continue                    # a leaf whose mutation the model refuses (an enum, a closed set)
        name = ".".join(str(k) for k in path)
        if content_digest(m) != d0:
            moves_digest.add(name)
        if embedded_text(m) != t0:
            moves_text.add(name)
    return moves_digest, moves_text


def _string_leaves(model, prefix=()):
    """Every (path, optional?) leaf of `model` whose type admits a str — walked
    from the model's own fields, recursively through nested models, so the
    fixture is COMPLETE by construction and not by a hand list (round-3 F5: the
    hand list left invalidation_reason and the nested source_id/origin unset)."""
    import typing
    for name, f in model.model_fields.items():
        ann = f.annotation; origin = typing.get_origin(ann); args = typing.get_args(ann)
        optional = origin is typing.Union and type(None) in args
        inner = [a for a in args if a is not type(None)] if origin is typing.Union else [ann]
        nested = [a for a in inner if isinstance(a, type) and hasattr(a, "model_fields")]
        if nested:
            yield from _string_leaves(nested[0], prefix + (name,))
        elif any(a is str for a in inner):
            yield prefix + (name,), optional
        elif any(typing.get_origin(a) is list and typing.get_args(a) == (str,) for a in inner):
            yield prefix + (name,), optional
        elif any(typing.get_origin(a) is dict and typing.get_args(a)[:1] == (str,) for a in inner):
            yield prefix + (name,), optional


_LEAF_VALUES = {                      # every str-admitting leaf of Edge, by path, with a VALID populated value
    ("id",): "e-inv12", ("user_id",): "u", ("subject",): "user", ("relation",): "works_as", ("object",): "Porto",
    ("note",): "n", ("invalidation_reason",): "superseded", ("supersedes",): "e-prior",
    ("original_relation",): "worked-at-the-clinic", ("outcome_counts",): {"confirmed": 1},
    ("provenance", "evidence_ref"): "ev-12", ("provenance", "source_id"): "mb-a", ("provenance", "origin"): "origin-1",
    ("agreement", "markers"): ["marker-one", "marker-two"], ("agreement", "direction"): "inbound",
    ("agreement", "lexicon"): "foreign-lexicon-v9",
}


def _complete_edge(unset=()):
    """An Edge with EVERY str-admitting leaf populated (or all but `unset`); the
    completeness is asserted against the model's own field walk."""
    from veracium.schema import Edge
    leaves = list(_string_leaves(Edge))
    missing = [p for p, _opt in leaves if p not in _LEAF_VALUES]
    assert not missing, f"the fixture table lacks a value for {missing} — a str leaf the model grew"
    d = {"invalidated_at": "2026-09-10T00:00:00Z",
         "provenance": {"author_of_evidence": "user", "disclosure": "mentionable"},
         "agreement": {}}
    for path, val in _LEAF_VALUES.items():
        if path in unset:
            continue
        cur = d
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = val
    if unset and ("invalidation_reason",) in unset:
        d.pop("invalidated_at", None)                      # coherence: no reason without a retirement
    if not d["agreement"]:
        d.pop("agreement")
    e = Edge.model_validate(d)
    for path, opt in leaves:
        if path in unset:
            continue
        cur = e
        for k in path:
            cur = getattr(cur, k) if cur is not None else None
        assert cur not in (None, "", [], {}), f"leaf {path} is unset in the complete fixture"
    return e


def _populated_edge():
    return _complete_edge()


def test_inv12_every_string_leaf_of_edge_is_populated_in_the_fixture():
    """Completeness by the model's own field walk: the fixture's leaf table
    covers every str-admitting leaf (a leaf the model grows fails here first)."""
    from veracium.schema import Edge
    leaves = {p for p, _ in _string_leaves(Edge)}
    assert leaves == set(_LEAF_VALUES), leaves ^ set(_LEAF_VALUES)
    _complete_edge()


@pytest.mark.parametrize("leaf", sorted(p for p, opt in _string_leaves(__import__("veracium.schema", fromlist=["Edge"]).Edge) if opt))
def test_inv12_each_optional_leaf_is_load_bearing_a_widening_onto_it_is_missed_when_it_is_unset(leaf):
    """The per-leaf NEGATIVE CONTROL: for every optional leaf, a fixture with that
    leaf UNSET lets a widening of the embedder onto it pass the mutation test,
    and the complete fixture refuses it. So each populated leaf is doing work,
    and the control shares the failure mode it guards (round-3 F5)."""
    from veracium import semantic
    real = semantic.embedded_text

    def read(e):
        cur = e
        for k in leaf:
            cur = getattr(cur, k) if cur is not None else None
        return cur

    def widened(e):
        v = read(e)
        return f"{real(e)} {v if isinstance(v, str) else (' '.join(v) if isinstance(v, list) else ' '.join(sorted(v)) if isinstance(v, dict) else '')}"
    md, mt = _inv12_sets(_complete_edge(unset=(leaf,)), semantic.content_digest, widened)
    assert mt <= md, f"the UNSET fixture was expected to MISS a widening onto {leaf}"
    md, mt = _inv12_sets(_complete_edge(), semantic.content_digest, widened)
    assert not (mt <= md), f"the complete fixture must CATCH a widening onto {leaf}"


def test_inv12_catches_a_widened_embedder_the_packaged_fixture_missed():
    """The negative control the reviewer ran: widen `embedded_text` with
    `original_relation` and leave the digest alone. The packaged (unset) fixture
    lets it through; the populated fixture refuses it."""
    from veracium import semantic
    from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance
    real = semantic.embedded_text
    widened = lambda e: f"{real(e)} {e.original_relation or ''}"
    packaged = Edge(id="e-inv12", user_id="u", subject="user", relation="works_as", object="Porto", note="n",
                    provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                          disclosure=Disclosure.MENTIONABLE))
    md, mt = _inv12_sets(packaged, semantic.content_digest, widened)
    assert mt <= md, "the packaged fixture was expected to MISS the widening"
    md, mt = _inv12_sets(_populated_edge(), semantic.content_digest, widened)
    assert not (mt <= md) and (mt - md) == {"original_relation"}


def test_the_round2_reproduction_script_reports_every_claim_as_the_reviewer_found_it():
    """Round-2 F1a, F1b, F2, F3, F5, F6 through the packaged script itself (P4:
    evidence that RUNS behaviour). Each token is the predicate the reviewer stated."""
    r = subprocess.run([sys.executable, str(EVIDENCE / "round2_reproductions.py")],
                       cwd=ROOT, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    out = r.stdout
    assert "F1a upsert reported success after B's redaction committed: True" in out
    assert "F1a stale vector STORED under the original digest: True" in out
    assert "F1b widened embedder still passes on the PACKAGED fixture (subset holds): True" in out
    assert "F1b the same widening is caught once original_relation is POPULATED: True" in out
    assert "F2 sanitize_llm_body leaves the marker intact: True" in out
    assert "F2 an edge whose object IS the marker was stored by remember() (no redaction happened): True" in out
    assert "F3 existing disposition reasons: 7 " in out and "F3 ALL of them are outside the proposed vocabulary: True" in out
    assert "F5 response is counts only (no ids): True | response names the prior id: False" in out
    assert "contribution_ledger has operation_id: False | supersession_refusals has operation_id: False | ledger rows: 1" in out
    assert "F6 prose key persisted in outcome_counts: True | exported verbatim: True" in out


@pytest.mark.xfail(strict=True, reason="0041 §4e (round-2 F1): the embedding upsert's read and insert "
                                       "are not one database transaction; implementation follows acceptance")
def test_two_connection_publication_the_embedding_upsert_refuses_a_vector_for_content_another_connection_replaced(tmp_path):
    """The reviewer's two-connection regression, red first: connection A reads the
    edge inside upsert_embedding; connection B commits a redaction (the tombstone)
    and deletes the embedding; A must NOT store a vector under the original digest.
    Today it does (instance-local lock, no transaction before the read)."""
    from veracium import semantic
    from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance
    MARKER = "\x00veracium:redacted\x00"

    def quiet(prompt, *, system=None, role="compile", json_schema=None):
        return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""
    cfg = dict(db_path=str(tmp_path / "s.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False)
    A = Memory(llm=quiet, config=MemoryConfig(**cfg)).store
    B = Memory(llm=quiet, config=MemoryConfig(**cfg)).store
    orig = Edge(id="e-1", user_id="u", subject="user", relation="works_as", object="hiv-positive since 2019",
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                      disclosure=Disclosure.MENTIONABLE))
    A.add_edge(orig)
    d_orig = semantic.content_digest(orig)
    real = semantic.content_digest

    def interleave(live):
        semantic.content_digest = real
        B.add_edge(orig.model_copy(update={"subject": MARKER, "relation": MARKER, "object": MARKER, "note": MARKER}))
        B._conn.execute("DELETE FROM edge_embedding WHERE edge_id='e-1'")
        B._conn.commit()
        return real(live)
    semantic.content_digest = interleave
    try:
        A.upsert_embedding(edge_id="e-1", user_id="u", embedder_id="emb@1", content_digest=d_orig, dim=2,
                           vec=b"\x00" * 8, built_at="2026-09-15T00:00:00Z")
    finally:
        semantic.content_digest = real
    stored = B._conn.execute("SELECT content_digest FROM edge_embedding WHERE edge_id='e-1'").fetchall()
    assert stored == [], "a vector for content another connection already replaced was stored"


def test_the_before_after_fixtures_validate_as_the_treatment_map_rules_them():
    """Round-2 artifact ask, corrected for round-3 F5: every after-shape is built by
    FULL model validation of a complete dump (never model_copy), the ledger record
    also through the absorption-site validator; the refusals are printed as results
    and asserted here as the reviewer would find them today."""
    r = subprocess.run([sys.executable, str(EVIDENCE / "fixtures_before_after.py")],
                       cwd=ROOT, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    out = r.stdout
    assert "model_copy" not in (EVIDENCE / "fixtures_before_after.py").read_text().split('"""', 2)[2]   # never used outside the docstring
    assert "VALID    after (arity-1 markers)  (model)" in out
    assert "identity preserved: True | evidence_ref preserved: True | every content leaf is the marker: True | outcome_counts cleared: True" in out
    assert "REFUSED  after (arity-2 markers) — expected REFUSED today" in out
    assert "kind preserved: True | still active (retired_reason None): True" in out
    assert "kind preserved: True | seq preserved: True" in out
    assert "active unchanged by the redaction: True" in out
    assert "receipt mentions no 64-hex digest: True" in out
    assert "VALID    ContributionRecord before (a REAL absorption payload)  (model + operation validator)" in out
    assert "VALID    ContributionRecord after (identity_digest / evidence_ref_digest → None; payload untouched)  (model + operation validator)" in out
    assert "REFUSED  ContributionRecord with payload={} — the round-2 fixture (expected REFUSED by the operation validator): model VALID but the operation validator refuses" in out
    assert "REFUSED  Confirmation.request_digest → None" in out and "VALID    Confirmation.request_digest → MARKER (the ruling)  (model)" in out


def test_the_round3_reproduction_script_reports_every_claim_as_the_reviewer_found_it():
    """Round-3 F1, F2 and F5 through the packaged script, plus the four guard
    simulations research named as candidates (P4: evidence that RUNS behaviour).
    Each token is the predicate the reviewer stated or the simulation printed."""
    r = subprocess.run([sys.executable, str(EVIDENCE / "round3_reproductions.py")],
                       cwd=ROOT, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    out = r.stdout
    assert "F1 after replacement: the model validated: True | chain head disappeared: True" in out
    assert "F1 the next append restarted at seq 1: True" in out
    assert "F1 targeted deletion of the original (now marker-kind) record PERMITTED: True" in out
    assert "F2 retired_reason=None → active: True | retired_reason=MARKER → active: False | flipped: True" in out
    assert "F5a model_copy accepted two identical markers: True | the constructor refuses the same: True" in out
    assert "F5b payload={} passes the model: True | passes the absorption-site validator: False" in out
    assert "a widening onto invalidation_reason passes the mutation test: True" in out
    assert "G1 graph.py:333 — a LIVE replacement against a REDACTED prior: REFUSED" in out
    assert "against the redacted prior: ADMITTED by the guard" in out
    assert "G3 sqlite.py:1512 — add_episode refuses a kind='outcome' link: True | refuses the same link once kind is the marker: False" in out
    assert "G4 ingest of a third_party_claim triple sets BOTH markers (relation AND disclosure=QUARANTINED): True" in out
    assert "G4 a RELATION-ONLY quarantine is constructible through store.add_edge (no refusal): True" in out
    assert "G4 redacting relation on the relation-only edge PROMOTES it out of quarantine (quarantined False): True" in out

