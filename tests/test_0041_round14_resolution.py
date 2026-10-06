"""specs/0041 round 14 — R13-01: a notice authorises the 0014 §2c rider's exception only for its own RESOLVED subject.

Round 13 matched a notice's RAW target against "the arriving id OR the held id" before the arrivals were resolved, so
with two outputs' ids permuted, B's notice (naming arriving `a`) read as A's (held `a`) and excused A's difference. Now
a notice whose raw target is an arriving record's id is for THAT arrival's subject and authorises the exception only
when that arrival IS the colliding one; a notice naming no arriving record is for the held or standing record of that
id directly (research's stage-1 wording; the ordinary-arrival ruling is (i), refuse). Every cell builds two REAL
consolidation outputs (A, index 0; B, index 1), redacts them with `Memory.redact`, and imports through `import_memory`;
a file is edited only to build the reviewer's input (ids permuted, a notice removed). SQL is read-only.
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
_spec = importlib.util.spec_from_file_location("tt41_r14r", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r14r"] = tt
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


def _state(st):
    """Every row of the three tables an import writes here, `recorded_at` (the wall clock) alone excepted."""
    out = {}
    for t in ("episodes", "episode_event", "redactions"):
        cols = [c[1] for c in st._conn.execute(f"PRAGMA table_info({t})") if c[1] != "recorded_at"]
        out[t] = st._conn.execute(f"SELECT {', '.join(cols)} FROM {t} ORDER BY {', '.join(cols)}").fetchall()
    return out


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


# ---- R13-01 -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("restore", [False, True])
def test_R13_01_permuted_ids_with_ONE_notice_refuse_the_whole_import(tmp_path, restore):
    dst, a, b = _setup(tmp_path, restore)
    before = _snapshot(dst.store)
    f = _write(tmp_path / "p.jsonl", _permute(_lines(tmp_path / "after.jsonl"), a, b, keep_a_notice=False))
    with pytest.raises(ValueError, match="DIFFERENT source-identity projection"):
        import_memory(dst.store, f, restore=restore)
    assert _snapshot(dst.store) == before and SECRET in _summary(dst, a) and SECRET in _summary(dst, b)


@pytest.mark.parametrize("restore", [False, True])
def test_R13_01_an_ordinary_arrival_reusing_a_held_id_does_not_lend_its_notice(tmp_path, restore):
    """Research's ruling (i): A's indexed arrival relabelled `zz`, A's own notice removed; an ORDINARY episode arrives
    under A's held id with a notice naming it. The notice is for the ordinary arrival's subject, not A's arrival: refuse."""
    dst, a, b = _setup(tmp_path, restore)
    recs = []
    for r in _lines(tmp_path / "after.jsonl"):
        if r.get("record") == "redaction" and r["target_id"] == a:
            recs.append(r)                                     # this notice now names the ORDINARY arrival "a"
            continue
        if r.get("lineage") and r.get("id") == a:
            recs.append(dict(r, id="zz"))
            recs.append({k: v for k, v in r.items() if k not in ("lineage", "consolidation_output_index", "operation_id")}
                        | {"id": a, "summary": R.MARKER})       # an ordinary episode reusing the held id spelling
            continue
        recs.append(r)
    before = _snapshot(dst.store)
    with pytest.raises(ValueError, match="DIFFERENT source-identity projection"):   # refused at the collision, for THIS reason
        import_memory(dst.store, _write(tmp_path / "o.jsonl", recs), restore=restore)
    assert _snapshot(dst.store) == before


@pytest.mark.parametrize("restore", [False, True])
def test_control_permuted_ids_with_BOTH_notices_treat_both_held_outputs(tmp_path, restore):
    """The relabelled unit with both notices leaves the destination EXACTLY as the unrelabelled unit leaves a twin
    destination holding the same outputs: the same import result, and every episode, event and notice row (the
    notices' source identities included) equal, `recorded_at` alone excepted. A relabelled copy is resolved, never
    refused merely for being relabelled."""
    dst, a, b = _setup(tmp_path, restore)
    twin = tt._mem(tmp_path, "twin.db"); import_memory(twin.store, tmp_path / "before.jsonl", restore=restore)
    want = import_memory(twin.store, tmp_path / "after.jsonl", restore=restore)
    got = import_memory(dst.store, _write(tmp_path / "p.jsonl", _permute(_lines(tmp_path / "after.jsonl"), a, b, keep_a_notice=True)),
                        restore=restore)
    assert got == want and got["notices_applied"] == 2 and got["unattested_markers"] == []
    assert _state(dst.store) == _state(twin.store)
    assert _summary(dst, a) == R.MARKER and _summary(dst, b) == R.MARKER
    fa, fb = dst.store._attested_fields(U, "episode", a), dst.store._attested_fields(U, "episode", b)
    assert "summary" in fa and fa == fb
    rows = sorted(t for (t,) in dst.store._conn.execute("SELECT target_id FROM redactions WHERE user_id=?", (U,)))
    assert rows == sorted([a, b])


@pytest.mark.parametrize("restore", [False, True])
def test_control_a_notice_naming_a_held_target_with_no_arrival_applies_to_it(tmp_path, restore):
    """A's arrival is absent from the unit; A's notice names held `a` directly; B arrives with its own notice."""
    dst, a, b = _setup(tmp_path, restore)
    recs = [r for r in _lines(tmp_path / "after.jsonl") if not (r.get("lineage") and r.get("id") == a)]
    r = import_memory(dst.store, _write(tmp_path / "h.jsonl", recs), restore=restore)
    assert _summary(dst, a) == R.MARKER and _summary(dst, b) == R.MARKER
    assert r["notices_applied"] == 2 and r["unattested_markers"] == []
    assert all("summary" in dst.store._attested_fields(U, "episode", x) for x in (a, b))


def test_control_a_repeated_user_remap_binds_both_notices_to_the_surviving_copies(tmp_path):
    dst, a, b = _setup(tmp_path, False)
    import_memory(dst.store, tmp_path / "after.jsonl", user_id="v")
    r2 = import_memory(dst.store, tmp_path / "after.jsonl", user_id="v")
    outs = {e.id for e in dst.store.episodes("v") if e.lineage}
    rows = [t for (t,) in dst.store._conn.execute("SELECT target_id FROM redactions WHERE user_id='v'")]
    assert len(outs) == 2 and sorted(rows) == sorted(outs) and r2["notices_existing"] == 2
