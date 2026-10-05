"""specs/0041 round 14 — R13-02: the 0014 §2c rider's marker condition is the WHOLE value.

Round 13's predicate asked `marker_fields`, whose `carries_marker` is a SUBSTRING test, so an arriving summary that only
CONTAINED the marker — neither side IS the marker — was admitted. Now `held or incoming == MARKER`, exactly; the general
helper keeps its ordinary-write reservation and unattested-marker diagnostic callers. Every cell builds two REAL
consolidation outputs, redacts them with `Memory.redact`, and imports through `import_memory`; a file is edited only to
build the reviewer's input. SQL is read-only.
"""
import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

from veracium import redaction as R
from veracium.lifecycle import consolidate
from veracium.portability import export_memory, import_memory
from veracium.schema import Episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r14m", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r14m"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-R14"


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _lines(p):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def _write(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def _two_outputs(m):
    for i in range(8):
        m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                    provenance=tt._prov(source_id="src-one", evidence_ref=f"ev-{i}")))
    consolidate(m.store, lambda p, system=None, role=None: json.dumps(
        {"records": [{"date": "2026-01-01", "summary": "week one " + SECRET},
                     {"date": "2026-01-05", "summary": "week two " + SECRET}]}), U, m.config,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    outs = sorted((e for e in m.store.episodes(U) if e.lineage), key=lambda e: e.consolidation_output_index)
    return outs[0].id, outs[1].id


def _setup(tmp_path, restore):
    """A destination holding outputs A and B (imported in the cell's own mode); the source's redacted export."""
    src = tt._mem(tmp_path, "src.db"); a, b = _two_outputs(src)
    export_memory(src.store, U, tmp_path / "before.jsonl")
    dst = tt._mem(tmp_path, "dst.db"); import_memory(dst.store, tmp_path / "before.jsonl", restore=restore)
    src.redact(U, episode_id=a, reason="subject_request"); src.redact(U, episode_id=b, reason="subject_request")
    export_memory(src.store, U, tmp_path / "after.jsonl")
    return dst, a, b


def _summary(dst, eid):
    (j,) = dst.store._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    return json.loads(j, object_pairs_hook=_strict_pairs)["summary"]


def _snapshot(st):
    return {t: st._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("episodes", "episode_event", "redactions")}


def _permute(recs, a, b, *, keep_a_notice):
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


# ---- R13-02 -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("restore", [False, True])
@pytest.mark.parametrize("shape", ["prefix+M", "M+suffix", "prefix+M+suffix"])
def test_R13_02_a_value_that_merely_CONTAINS_the_marker_refuses_whole_import(tmp_path, restore, shape):
    dst, a, b = _setup(tmp_path, restore)
    value = {"prefix+M": "prefix " + R.MARKER, "M+suffix": R.MARKER + " suffix", "prefix+M+suffix": "p " + R.MARKER + " s"}[shape]
    recs = [dict(r, summary=value) if (r.get("lineage") and r.get("id") == a) else r for r in _lines(tmp_path / "after.jsonl")]
    before = _snapshot(dst.store)
    with pytest.raises(ValueError, match="DIFFERENT source-identity projection"):
        import_memory(dst.store, _write(tmp_path / "x.jsonl", recs), restore=restore)
    assert _snapshot(dst.store) == before


@pytest.mark.parametrize("restore", [False, True])
def test_control_the_exact_marker_with_the_notices_is_admitted_and_treats_both(tmp_path, restore):
    dst, a, b = _setup(tmp_path, restore)
    import_memory(dst.store, tmp_path / "after.jsonl", restore=restore)
    assert _summary(dst, a) == R.MARKER and _summary(dst, b) == R.MARKER


@pytest.mark.parametrize("restore", [False, True])
def test_control_ordinary_text_in_a_named_field_refuses(tmp_path, restore):
    dst, a, b = _setup(tmp_path, restore)
    recs = [dict(r, summary="tampered") if (r.get("lineage") and r.get("id") == a) else r for r in _lines(tmp_path / "after.jsonl")]
    with pytest.raises(ValueError, match="DIFFERENT source-identity projection"):
        import_memory(dst.store, _write(tmp_path / "x.jsonl", recs), restore=restore)
