"""specs/0041 (targeted redaction, draft) — the round-1 verdict's executed claims,
reproduced as the reviewer found them and kept runnable, so v3's carrier
inventory and contracts are written against behaviour that is asserted here
rather than recalled. Every check below FAILS the day the behaviour changes —
which is the point: when 0041 is implemented, these become the negative
controls the redaction contract must turn around, one by one.
"""

import json
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
