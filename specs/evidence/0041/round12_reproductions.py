#!/usr/bin/env python3
"""0041 round 12's finding and two observations, REPRODUCED at the round-12 pin before any fix — through the supported
writers only (a real consolidation, `Memory.redact`, `export_memory` / `import_memory`; SQL read-only), each paired
with the verdict's controls, which must HOLD. A finding that does not reproduce prints NOT REPRODUCED; exit 1.

  R12-01  a genuine notice cannot reach a consolidation OUTPUT the destination already holds: the indexed-output
          collision check (0014 §2c) refuses the differing projection before the notice is applied
  N12-01  a repeated remapped import of a redacted consolidation export: the arriving copy is discarded as the
          existing indexed output, and its notice is written STANDING for the discarded id
  N12-02  an empty episode linked to a revocation row ALREADY holding the marker is refused "nothing to redact"

    PYTHONPATH=src python specs/evidence/0041/round12_reproductions.py
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


_spec = importlib.util.spec_from_file_location("tt41_r12repro", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r12repro"] = tt
_spec.loader.exec_module(tt)

from veracium.lifecycle import consolidate                     # noqa: E402
from veracium.portability import export_memory, import_memory  # noqa: E402
from veracium import redaction as R                            # noqa: E402
from veracium.schema import Episode                            # noqa: E402

U = "u"
SECRET = "SECRET-R12-OUTPUT"
RESULTS: list[tuple[str, bool]] = []
CONTROLS: list[bool] = []


def finding(fid, ok, what):
    RESULTS.append((fid, ok))
    print(f"    {'REPRODUCED' if ok else 'NOT REPRODUCED'}: {what}")


def control(ok, what):
    CONTROLS.append(ok)
    print(f"    control {'holds' if ok else 'FAILS'}: {what}")


def consolidated(m, n=8):
    for i in range(n):
        m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                    provenance=tt._prov(source_id="src-one", evidence_ref=f"ev-{i}")))
    consolidate(m.store, lambda p, system=None, role=None: json.dumps(
        {"records": [{"date": "2026-01-01", "summary": "the week " + SECRET}]}), U, m.config,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    (out,) = [e for e in m.store.episodes(U) if e.lineage]
    return out.id


def snapshot(st):
    return {t: st._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("episodes", "episode_event", "redactions")}


def attempt(fn):
    try:
        return fn(), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"          # whole: the phrase a check looks for can sit past any cut


# ---- R12-01 --------------------------------------------------------------------------------------------------
print("\n=== R12-01 — a genuine notice cannot reach a consolidation output the destination already holds")
for restore in (False, True):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        src = tt._mem(d, "src.db"); oid = consolidated(src)
        export_memory(src.store, U, d / "first.jsonl")
        dst = tt._mem(d, "dst.db"); import_memory(dst.store, d / "first.jsonl", restore=restore)
        held_before = [e.summary for e in dst.store.episodes(U) if e.lineage]
        src.redact(U, episode_id=oid, reason="subject_request")
        export_memory(src.store, U, d / "second.jsonl")
        before = snapshot(dst.store)
        _r, err = attempt(lambda: import_memory(dst.store, d / "second.jsonl", restore=restore))
        held = [e.summary for e in dst.store.episodes(U) if e.lineage]
        finding("R12-01", err is not None and "DIFFERENT source-identity projection" in err and snapshot(dst.store) == before
                and held == held_before and any(SECRET in s for s in held),
                f"restore={restore}: the redacted re-export into the destination holding the output → {(err or '')[-140:]!r}; the held "
                f"output keeps {held[0][:40]!r}, nothing written")
        # controls: the unchanged first export re-imports idempotently; the redacted export applies to a FRESH destination
        r1, e1 = attempt(lambda: import_memory(dst.store, d / "first.jsonl", restore=restore))
        control(e1 is None and len([e for e in dst.store.episodes(U) if e.lineage]) == 1,
                f"restore={restore}: re-importing the unchanged first export keeps one indexed output ({e1 or 'ok'})")
        fresh = tt._mem(d, "fresh.db")
        r2, e2 = attempt(lambda: import_memory(fresh.store, d / "second.jsonl", restore=restore))
        fresh_out = [e.summary for e in fresh.store.episodes(U) if e.lineage]
        control(bool(e2 is None and fresh_out and SECRET not in fresh_out[0] and fresh.store._attested_fields(
                    U, "episode", [e.id for e in fresh.store.episodes(U) if e.lineage][0])),
                f"restore={restore}: the redacted export into a FRESH destination applies and attests ({e2 or 'ok'})")
        recs = [json.loads(x, object_pairs_hook=_strict_pairs) for x in (d / "second.jsonl").read_text().splitlines() if x.strip()]
        (d / "nonotice.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs if r.get("record") != "redaction"))
        before = snapshot(dst.store)
        _r3, e3 = attempt(lambda: import_memory(dst.store, d / "nonotice.jsonl", restore=restore))
        control(e3 is not None and "DIFFERENT source-identity projection" in e3 and snapshot(dst.store) == before,
                f"restore={restore}: the same export WITHOUT its notice still refuses the identity conflict, nothing written")

# ---- N12-01 --------------------------------------------------------------------------------------------------
print("\n=== N12-01 — a repeated remapped import of a redacted consolidation output: the notice binds a discarded id")
for where in ("separate destination", "the native store under another user"):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        src = tt._mem(d, "src.db"); oid = consolidated(src)
        src.redact(U, episode_id=oid, reason="subject_request")
        export_memory(src.store, U, d / "x.jsonl")
        dst = src if where.startswith("the native") else tt._mem(d, "dst.db")
        r1 = import_memory(dst.store, d / "x.jsonl", user_id="v")
        r2 = import_memory(dst.store, d / "x.jsonl", user_id="v")
        outs = [e.id for e in dst.store.episodes("v") if e.lineage]
        rows = dst.store._conn.execute("SELECT target_id, event_ref FROM redactions WHERE user_id='v' ORDER BY target_id").fetchall()
        dangling = [t for t, ev in rows if t not in outs]
        finding("N12-01", len(outs) == 1 and r2.get("notices_standing") == 1 and r2.get("notices_existing") == 0 and dangling,
                f"{where}: after two imports one indexed output {outs}; the second import reports standing "
                f"{r2.get('notices_standing')}, existing {r2.get('notices_existing')}; redaction rows {len(rows)}, naming "
                f"{len(dangling)} id(s) that are no record: {dangling}")

# ---- N12-02 --------------------------------------------------------------------------------------------------
print("\n=== N12-02 — an empty episode linked to a side row already holding the marker is 'nothing to redact'")
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    m = tt._frozen_memory(d)
    rows = tt._frozen_rows()
    eid = rows["source_linked_edge"]
    m.redact(U, edge_id=eid, reason="subject_request")            # the linked revocation prose becomes the marker
    (ej,) = m.store._conn.execute("SELECT json FROM edges WHERE id=?", (eid,)).fetchone()
    prov = json.loads(ej, object_pairs_hook=_strict_pairs)["provenance"]
    m.store.add_episode(Episode(id="ep-empty", user_id=U, date="2026-10-01", summary="", kind="interaction",
                                provenance=tt._prov(source_id=prov.get("source_id"), evidence_ref="ev-empty")))
    before = {t: m.store._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("episodes", "redactions", "source_revocations")}
    _r, err = attempt(lambda: m.redact(U, episode_id="ep-empty", reason="subject_request"))
    after = {t: m.store._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in before}
    marker_rows = m.store._conn.execute("SELECT COUNT(*) FROM source_revocations WHERE reason=?", (R.MARKER,)).fetchone()[0]
    finding("N12-02", err is not None and "nothing to redact" in err and after == before and marker_rows >= 1,
            f"the empty interaction with the redacted edge's source (its revocation row holds the marker: {marker_rows}) → "
            f"{(err or '')[:120]!r}; nothing written")

print("\n" + "-" * 100)
for fid, ok in RESULTS:
    print(f"  {fid}: {'REPRODUCED' if ok else 'NOT REPRODUCED'}")
print(f"  controls: {sum(CONTROLS)} of {len(CONTROLS)} hold")
sys.exit(0 if all(ok for _f, ok in RESULTS) and all(CONTROLS) else 1)
