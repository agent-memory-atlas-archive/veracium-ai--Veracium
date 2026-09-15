"""0041 treatment matrix — writer trace for `Episode.kind` (round-2 F6, dev 2026-09-15):
the model declares `kind: str = "interaction"` with no validator, and an export file is
an EXTERNAL writer of it. Executed: a prose `kind` in an export record is accepted by
import and stored verbatim.  Run from the repo root: .venv/bin/python specs/evidence/0041/kind_import_probe.py
"""
import json, pathlib, tempfile, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))


def _no_dup_pairs(pairs):
    """The 0026 evidence-boundary rule: a duplicate-key-REFUSING decoder."""
    seen = set()
    for k, _v in pairs:
        if k in seen:
            raise ValueError(f"duplicate key {k!r}")
        seen.add(k)
    return dict(pairs)


def _load(text):
    return json.loads(text, object_pairs_hook=_no_dup_pairs)
from veracium import Memory, MemoryConfig
from veracium.schema import EvidenceContext
tmp = pathlib.Path(tempfile.mkdtemp()); U = "u"
def quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""
m = Memory(llm=quiet, config=MemoryConfig(db_path=str(tmp/"a.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))
m.remember(U, "I live in Porto.", context=EvidenceContext.direct())
out = tmp/"x.jsonl"; m.export_memory(U, out)
lines = out.read_text().splitlines(); rec = _load(lines[1])
print("exported record kind field present:", "kind" in rec, "| marker:", rec.get("record"))
rec["kind"] = "told me in confidence: hiv-positive"          # a PROSE Episode.kind in the file
(tmp/"y.jsonl").write_text(lines[0] + "\n" + json.dumps(rec) + "\n")
m2 = Memory(llm=quiet, config=MemoryConfig(db_path=str(tmp/"b.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))
try:
    r = m2.import_memory(tmp/"y.jsonl"); eps = m2.store.episodes(U, include_retired=True)
    print("import accepted:", r, "| stored Episode.kind:", [e.kind for e in eps])
except Exception as e:
    print("import REFUSED:", type(e).__name__, str(e)[:120])
