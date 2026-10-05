"""specs/0041 round 13 — N12-02: a SHARED side carrier already at the marker is attested.

The revocation rows are shared by every record of a source, and their one updater reports only the rows IT changed; an
empty record of a source whose row another record's redaction had already marked read "nothing to redact" — v15.2's
"judged over the whole covered surface" was untrue for that carrier. A row already at the marker now enters the union,
as a record carrier already holding the marker does (`already_treated`). Supported writers only; SQL read-only.
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
_spec = importlib.util.spec_from_file_location("tt41_r13s", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r13s"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-R13-SIDE"


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


def _frozen_with_marked_revocation(tmp_path):
    m = tt._frozen_memory(tmp_path)
    eid = tt._frozen_rows()["source_linked_edge"]
    m.redact(U, edge_id=eid, reason="subject_request")
    (ej,) = m.store._conn.execute("SELECT json FROM edges WHERE id=?", (eid,)).fetchone()
    return m, json.loads(ej, object_pairs_hook=_strict_pairs)["provenance"]


def test_N12_02_an_empty_episode_of_a_source_whose_revocation_row_is_marked_is_redacted(tmp_path):
    m, prov = _frozen_with_marked_revocation(tmp_path)
    m.store.add_episode(Episode(id="ep-empty", user_id=U, date="2026-10-01", summary="", kind="interaction",
                                provenance=tt._prov(source_id=prov.get("source_id"), evidence_ref="ev-empty")))
    rec = m.redact(U, episode_id="ep-empty", reason="subject_request")
    assert "source_revocations.reason" in rec.fields_cleared
    export_memory(m.store, U, tmp_path / "x.jsonl")
    keep = [r for r in _lines(tmp_path / "x.jsonl") if "id" not in r or r.get("id") == "ep-empty" or r.get("target_id") == "ep-empty"]
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, _write(tmp_path / "k.jsonl", keep))
    assert dst.store._attested_fields(U, "episode", "ep-empty")


def test_control_an_empty_episode_with_no_linked_source_is_still_nothing_to_redact(tmp_path):
    m, _prov = _frozen_with_marked_revocation(tmp_path)
    m.store.add_episode(Episode(id="ep-bare", user_id=U, date="2026-10-01", summary="", kind="interaction",
                                provenance=tt._prov(source_id="src-unrelated", evidence_ref="ev-bare")))
    with pytest.raises(ValueError, match="nothing to redact"):
        m.redact(U, episode_id="ep-bare", reason="subject_request")


def test_control_the_record_that_changes_the_revocation_row_attests_it(tmp_path):
    """The carrier this call CHANGES: the linked edge's own redaction treats the prose and attests the path."""
    m = tt._frozen_memory(tmp_path)
    rec = m.redact(U, edge_id=tt._frozen_rows()["source_linked_edge"], reason="subject_request")
    assert "source_revocations.reason" in rec.fields_cleared
