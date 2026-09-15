"""0041 §4g row 3 — the standing-notice precondition, executed at the tree (dev, 2026-09-15).
Q (research, 2026-09-15): can the store TODAY hold a journal event whose edge_id names NO edges row
(the §4g 'standing notice' precondition)? What do the readers, doctor and export do with it?"""
import tempfile, pathlib, json, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
from veracium import Memory, MemoryConfig
from veracium.store.edge_events import append_event, next_seq, next_txn, mint_recorded_at
from datetime import datetime, timezone


def _no_dup_pairs(pairs):
    """The 0026 evidence-boundary rule: JSON at a boundary is parsed with a
    duplicate-key-REFUSING decoder, never a last-wins one."""
    seen = set()
    for k, _v in pairs:
        if k in seen:
            raise ValueError(f"duplicate key {k!r}")
        seen.add(k)
    return dict(pairs)


def _load(text):
    return json.loads(text, object_pairs_hook=_no_dup_pairs)
d = pathlib.Path(tempfile.mkdtemp())
def _quiet(prompt, *, system=None, role="compile", json_schema=None): return "{}"
m = Memory(llm=_quiet, config=MemoryConfig(db_path=str(d / "s.db")))
m.remember("u", "user likes tea", date="2026-09-15")
st = m.store; conn = st._conn
print("fk pragma:", conn.execute("PRAGMA foreign_keys").fetchone()[0])
try:
    seq = next_seq(conn, "u"); txn = next_txn(conn, "u")
    append_event(conn, user_id="u", seq=seq, txn=txn, edge_id="ghost-1", kind="redacted",
                 reason="subject_request", state=json.dumps({"id": "ghost-1"}),
                 recorded_at=mint_recorded_at(conn, "u", datetime.now(timezone.utc)))
    conn.commit(); print("Q1 orphan event: ACCEPTED by append_event (no FK, no CHECK refuses it)")
except Exception as e:
    print("Q1 orphan event: REFUSED:", type(e).__name__, e)
print("   rows for ghost-1:", conn.execute("SELECT kind, reason FROM edge_event WHERE edge_id='ghost-1'").fetchall())
r = st.edge_events("u", edge_id="ghost-1"); print("Q2 store.edge_events(u, ghost-1) returns:", len(r), "row(s)")
from veracium.doctor import diagnose
rep = diagnose(str(d / "s.db"), user="u")
fs = [(f.check, f.level, f.message[:90]) for f in rep.findings] if hasattr(rep, "findings") else rep
print("Q3 doctor findings:", fs)
from veracium.portability import export_memory
p = d / "x.jsonl"; c = export_memory(st, "u", p)
kinds = sorted({(_load(l).get("record") or _load(l).get("kind")) for l in p.read_text().splitlines()})
print("Q4 export counts:", c, "| record kinds in the file:", kinds, "| ghost-1 in file:", "ghost-1" in p.read_text())
