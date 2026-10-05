"""specs/0041 round 13 — R12-01 and N12-01 (a redaction notice reaches a consolidation OUTPUT the destination already
holds, under 0014 §2c's rider). N12-02 is tests/test_0041_round13_side.py.

R12-01: the indexed-output collision check refused ANY projected difference before the notice could apply, so a genuine
redaction of an output never reached a destination holding it. The 0014 §2c rider (owner-approved 2026-10-05) admits
exactly one class — a redaction of THAT held output: a notice for it in the unit or already held, every differing field
named by it and an episode record carrier path, the marker on one side. The arrival is not installed; the held output
IS the identity. N12-01: the notice of a discarded arrival named the importer's minted id, so a repeated remapped import
wrote a second, dangling redaction row; every notice for a resolved arrival is now REBOUND to the held id before the
commit, and R11-03's body comparison runs on it like any other. Every cell uses the supported writers (a real
consolidation, `Memory.redact`, export / import); SQL is read-only.
"""
import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

from veracium.lifecycle import consolidate
from veracium.portability import export_memory, import_memory
from veracium.schema import Episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r13o", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r13o"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-R13-OUTPUT"


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


def _consolidated(m, n=8):
    for i in range(n):
        m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                    provenance=tt._prov(source_id="src-one", evidence_ref=f"ev-{i}")))
    consolidate(m.store, lambda p, system=None, role=None: json.dumps(
        {"records": [{"date": "2026-01-01", "summary": "the week " + SECRET}]}), U, m.config,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    (out,) = [e for e in m.store.episodes(U) if e.lineage]
    return out.id


def _source(tmp_path):
    """A source holding one consolidation output; its export BEFORE the redaction and AFTER (with the notice)."""
    src = tt._mem(tmp_path, "src.db")
    oid = _consolidated(src)
    export_memory(src.store, U, tmp_path / "before.jsonl")
    src.redact(U, episode_id=oid, reason="subject_request")
    export_memory(src.store, U, tmp_path / "after.jsonl")
    return src, oid


def _outputs(st, uid=U):
    return [e for e in st.episodes(uid) if e.lineage]


def _rows(st, uid=U):
    return st._conn.execute("SELECT target_id FROM redactions WHERE user_id=? ORDER BY target_id", (uid,)).fetchall()


def _snapshot(st):
    return {t: st._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("episodes", "episode_event", "redactions")}


@pytest.mark.parametrize("restore", [False, True])
def test_R12_01_indexed_output_redaction_reaches_held_output(tmp_path, restore):
    _src, oid = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "before.jsonl", restore=restore)
    (held,) = _outputs(dst.store)
    r = import_memory(dst.store, tmp_path / "after.jsonl", restore=restore)
    (after,) = _outputs(dst.store)
    assert after.id == held.id and SECRET not in after.summary                 # the HELD output, treated in place
    assert after.lineage == held.lineage and after.consolidation_output_index == held.consolidation_output_index
    assert after.operation_id == held.operation_id and after.date == held.date   # structure preserved
    assert dst.store._attested_fields(U, "episode", held.id) and held.id in r["inconsistent_notices"]


def test_the_held_output_keeps_every_field_the_notice_does_not_name(tmp_path):
    """REPRESENTATION of 'every other field preserved': the treated held output equals the held one on every field
    but the notice's carriers."""
    _src, oid = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "before.jsonl")
    held = json.loads(_outputs(dst.store)[0].model_dump_json())
    import_memory(dst.store, tmp_path / "after.jsonl")
    after = json.loads(_outputs(dst.store)[0].model_dump_json())
    (n,) = [x for x in _lines(tmp_path / "after.jsonl") if x.get("record") == "redaction"]
    assert {k for k in held if held[k] != after[k]} <= set(n["fields"])


@pytest.mark.parametrize("native", [False, True])
def test_N12_01_a_repeated_remapped_import_binds_the_notice_to_the_existing_copy(tmp_path, native):
    src, _oid = _source(tmp_path)
    dst = src if native else tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "after.jsonl", user_id="v")
    r2 = import_memory(dst.store, tmp_path / "after.jsonl", user_id="v")
    (out,) = _outputs(dst.store, "v")
    assert _rows(dst.store, "v") == [(out.id,)]                                  # ONE row, naming the record that exists
    assert r2["notices_standing"] == 0 and r2["notices_existing"] == 1


@pytest.mark.parametrize("restore", [False, True])
def test_every_redaction_row_names_a_record_after_held_earlier_and_repeat(tmp_path, restore):
    """Research's (c): both modes, a held-earlier destination and a repeat — every row names a record."""
    _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    for f in ("before.jsonl", "after.jsonl", "after.jsonl"):
        import_memory(dst.store, tmp_path / f, restore=restore)
    ids = {e.id for e in dst.store.episodes(U)}
    assert _rows(dst.store) and all(t in ids for (t,) in _rows(dst.store))


def test_a_notice_for_a_DIFFERENT_record_does_not_admit_the_output_difference(tmp_path):
    """Research's (a): a valid notice in the unit, but for ANOTHER record; the output's own notice removed — the
    collision still REJECTS, nothing written."""
    src, oid = _source(tmp_path)
    src.store.add_episode(Episode(id="other", user_id=U, date="2026-10-01", summary="other " + SECRET, provenance=tt._prov()))
    src.redact(U, episode_id="other", reason="subject_request")
    export_memory(src.store, U, tmp_path / "both.jsonl")
    recs = [r for r in _lines(tmp_path / "both.jsonl") if not (r.get("record") == "redaction" and r.get("target_id") == oid)]
    assert any(r.get("record") == "redaction" for r in recs)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "before.jsonl")
    before = _snapshot(dst.store)
    with pytest.raises(ValueError, match="DIFFERENT source-identity projection"):
        import_memory(dst.store, _write(tmp_path / "x.jsonl", recs))
    assert _snapshot(dst.store) == before


def test_a_contradictory_body_on_the_rebound_notice_still_refuses_whole_import(tmp_path):
    """Research's (b): after the rebind, R11-03's body comparison runs on the rebound notice like any other."""
    _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "before.jsonl")
    import_memory(dst.store, tmp_path / "after.jsonl")                         # the held output attested, body B
    recs = _lines(tmp_path / "after.jsonl")
    recs = [dict(r, reason="operator_policy") if r.get("record") == "redaction" else r for r in recs]
    before = _snapshot(dst.store)
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, _write(tmp_path / "c.jsonl", recs))
    assert _snapshot(dst.store) == before


def test_control_the_unchanged_first_export_still_reimports_idempotently(tmp_path):
    _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "before.jsonl")
    import_memory(dst.store, tmp_path / "before.jsonl")
    assert len(_outputs(dst.store)) == 1


def test_control_the_redacted_export_without_its_notice_still_refuses(tmp_path):
    _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, tmp_path / "before.jsonl")
    recs = [r for r in _lines(tmp_path / "after.jsonl") if r.get("record") != "redaction"]
    before = _snapshot(dst.store)
    with pytest.raises(ValueError, match="DIFFERENT source-identity projection"):
        import_memory(dst.store, _write(tmp_path / "n.jsonl", recs))
    assert _snapshot(dst.store) == before
