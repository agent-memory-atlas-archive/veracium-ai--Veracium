#!/usr/bin/env python3
"""0041 round 13's two findings and one observation, REPRODUCED at the round-13 pin before any fix — through the
supported writers only (a real consolidation, `Memory.redact`, `Memory.correct`, export / import; SQL read-only), each
paired with the verdict's controls, which must HOLD. A finding that does not reproduce prints NOT REPRODUCED; exit 1.

  R13-01  a notice for one consolidation output authorises ANOTHER output's difference: the collision check accepts a
          notice whose RAW target equals the arriving id OR the held id, before the arriving ids are resolved
  R13-02  the rider's marker condition is a SUBSTRING test: an arriving summary prefix+MARKER+suffix is admitted
  N13-01  a supersession-refusal row is shared by its two edges: redacting the second edge omits the already-treated row

    PYTHONPATH=src python specs/evidence/0041/round13_reproductions.py
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
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


_spec = importlib.util.spec_from_file_location("tt41_r13repro", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r13repro"] = tt
_spec.loader.exec_module(tt)

from veracium import graph as _graph                           # noqa: E402
from veracium import redaction as R                            # noqa: E402
from veracium.lifecycle import consolidate                     # noqa: E402
from veracium.portability import export_memory, import_memory  # noqa: E402
from veracium.schema import Edge, Episode                      # noqa: E402

U = "u"
SECRET = "SECRET-R13"
RESULTS: list[tuple[str, bool]] = []
CONTROLS: list[bool] = []


def finding(fid, ok, what):
    RESULTS.append((fid, ok))
    print(f"    {'REPRODUCED' if ok else 'NOT REPRODUCED'}: {what}")


def control(ok, what):
    CONTROLS.append(bool(ok))
    print(f"    control {'holds' if ok else 'FAILS'}: {what}")


def lines(p):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def write(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def attempt(fn):
    try:
        return fn(), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def two_outputs(m):
    """Two indexed outputs (index 0 = A, index 1 = B) from ONE real consolidation operation."""
    for i in range(8):
        m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                    provenance=tt._prov(source_id="src-one", evidence_ref=f"ev-{i}")))
    consolidate(m.store, lambda p, system=None, role=None: json.dumps(
        {"records": [{"date": "2026-01-01", "summary": "week one " + SECRET},
                     {"date": "2026-01-05", "summary": "week two " + SECRET}]}), U, m.config,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    outs = sorted((e for e in m.store.episodes(U) if e.lineage), key=lambda e: e.consolidation_output_index)
    assert [e.consolidation_output_index for e in outs] == [0, 1], outs
    return outs[0].id, outs[1].id


def setup(d, restore):
    """A source with outputs A and B; a destination holding both, imported in the SAME mode the cell then uses (the
    first form populated it on the default path and compared in restore mode, where the 0005 cap makes the held copy
    differ from the uncapped arrival regardless of any redaction — a refusal unrelated to the finding); the source's
    redacted export (both notices)."""
    src = tt._mem(d, "src.db"); a, b = two_outputs(src)
    export_memory(src.store, U, d / "before.jsonl")
    dst = tt._mem(d, "dst.db"); import_memory(dst.store, d / "before.jsonl", restore=restore)
    src.redact(U, episode_id=a, reason="subject_request"); src.redact(U, episode_id=b, reason="subject_request")
    export_memory(src.store, U, d / "after.jsonl")
    return dst, a, b


def held(dst, eid):
    (j,) = dst.store._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    return json.loads(j, object_pairs_hook=_strict_pairs)["summary"]


def snapshot(st):
    return {t: st._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("episodes", "episode_event", "redactions")}


def permute(recs, a, b, keep_a_notice):
    """Swap the two arriving output ids (and their notices' targets); optionally drop A's notice."""
    sw = {a: b, b: a}
    out = []
    for r in recs:
        if r.get("record") == "redaction":
            if r["target_id"] == a and not keep_a_notice:
                continue
            r = dict(r, target_id=sw.get(r["target_id"], r["target_id"]))
        elif r.get("lineage") and r.get("id") in sw:
            r = dict(r, id=sw[r["id"]])
        out.append(r)
    return out


# ---- R13-01 --------------------------------------------------------------------------------------------------
print("\n=== R13-01 — a notice for one output authorises another output's difference (ids permuted, A's notice removed)")
for restore in (False, True):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        dst, a, b = setup(d, restore)
        f = write(d / "perm.jsonl", permute(lines(d / "after.jsonl"), a, b, keep_a_notice=False))
        r, err = attempt(lambda: import_memory(dst.store, f, restore=restore))
        a_att, b_att = dst.store._attested_fields(U, "episode", a), dst.store._attested_fields(U, "episode", b)
        finding("R13-01", err is None and SECRET in held(dst, a) and not a_att and SECRET not in held(dst, b) and b_att,
                f"restore={restore}: the permuted unit with ONLY B's notice → {('accepted' if err is None else err[-80:])}; "
                f"A keeps {held(dst, a)[:24]!r} with attestation {sorted(a_att)}; B treated {SECRET not in held(dst, b)}")
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        dst, a, b = setup(d, restore)
        before = snapshot(dst.store)
        f = write(d / "noperm.jsonl", [r for r in lines(d / "after.jsonl") if not (r.get("record") == "redaction" and r["target_id"] == a)])
        _r, err = attempt(lambda: import_memory(dst.store, f, restore=restore))
        control(err is not None and "DIFFERENT source-identity" in err and snapshot(dst.store) == before,
                f"restore={restore}: WITHOUT the permutation, A's notice removed → the whole import refuses, nothing written")
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        dst, a, b = setup(d, restore)
        f = write(d / "both.jsonl", permute(lines(d / "after.jsonl"), a, b, keep_a_notice=True))
        r, err = attempt(lambda: import_memory(dst.store, f, restore=restore))
        control(err is None and SECRET not in held(dst, a) and SECRET not in held(dst, b)
                and dst.store._attested_fields(U, "episode", a) and dst.store._attested_fields(U, "episode", b),
                f"restore={restore}: the SAME permutation with BOTH notices → both held outputs treated and attested ({err or 'ok'})")

# ---- R13-02 --------------------------------------------------------------------------------------------------
print("\n=== R13-02 — the rider's marker condition is a substring test")
for restore in (False, True):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        dst, a, b = setup(d, restore)
        recs = [dict(r, summary="prefix " + R.MARKER + " suffix") if (r.get("lineage") and r.get("id") == a) else r
                for r in lines(d / "after.jsonl")]
        _r, err = attempt(lambda: import_memory(dst.store, write(d / "sub.jsonl", recs), restore=restore))
        finding("R13-02", err is None,
                f"restore={restore}: A arriving as prefix+MARKER+suffix (neither side IS the marker), both notices → "
                f"{'accepted' if err is None else 'refused: ' + err[-70:]}")

# ---- N13-01 --------------------------------------------------------------------------------------------------
print("\n=== N13-01 — a supersession-refusal row shared by its two edges; the second redaction omits it")
for order in ("prior first", "incoming first"):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        m = tt._mem(d, "m.db")
        m.store.add_edge(Edge(id="e-1", user_id=U, subject="user's sister", relation="lives_in", object="Berlin",
                              provenance=tt._prov()))
        try:
            m.correct(U, "e-1", "Paris")                       # the real path that records a refusal row
        except _graph.CorrectionRefused:
            pass
        (prior, incoming) = m.store._conn.execute("SELECT prior_edge_id, incoming_edge_id FROM supersession_refusals").fetchone()
        if not m.store._conn.execute("SELECT 1 FROM edges WHERE id=?", (incoming,)).fetchone():
            m.store.add_edge(Edge(id=incoming, user_id=U, subject="user's sister", relation="lives_in", object="Paris",
                                  provenance=tt._prov()))       # the incoming edge persisted through the ordinary writer
        first, second = (prior, incoming) if order == "prior first" else (incoming, prior)
        r1 = m.redact(U, edge_id=first, reason="subject_request")
        r2 = m.redact(U, edge_id=second, reason="subject_request")
        (rel,) = m.store._conn.execute("SELECT relation FROM supersession_refusals").fetchone()
        finding("N13-01", "supersession_refusals.relation" in r1.fields_cleared
                and "supersession_refusals.relation" not in r2.fields_cleared and rel == R.MARKER,
                f"{order}: the first receipt names the shared row {'supersession_refusals.relation' in r1.fields_cleared}; "
                f"the second's {sorted(r2.fields_cleared)} omits it while the row holds the marker {rel == R.MARKER}")

print("\n" + "-" * 100)
for fid, ok in RESULTS:
    print(f"  {fid}: {'REPRODUCED' if ok else 'NOT REPRODUCED'}")
print(f"  controls: {sum(CONTROLS)} of {len(CONTROLS)} hold")
sys.exit(0 if all(ok for _f, ok in RESULTS) and all(CONTROLS) else 1)
