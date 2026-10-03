"""specs/0041 round 11 — what a redaction record ATTESTS (an instance of R10-04's class, found by dev's own probe).

A successful `Memory.redact` could attest NOTHING and still succeed: on a record whose only carrier was already the
marker (an UNATTESTED marker row — admitted by an import with no notice, v7 §4b), or on a record with no content at
all (an episode whose summary is ""), the treatment changed no carrier, the attestation named no field — so an
unattested marker stayed writable (INV-11 keyed on nothing) — and the export carried a notice with an empty field
list that the store's own importer refuses (R9-08). The verdict's R10-04 sentence, reached by a content state:
"do not accept the operation and emit an unusable export".

Research's closure, and the owner's ruling (2026-10-03, dev session: "Refuse: nothing to redact"):
  the attestation names every carrier holding its TREATED value after the operation — what the call treated plus
  what already held it (`redaction.already_treated`, the exact complement of `treat_edge` / `treat_episode`);
  only when that is EMPTY does `redact` refuse, before any write.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

from veracium import redaction as R
from veracium.portability import export_memory, import_memory
from veracium.schema import Edge, Episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r11t", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r11t"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-ATTEST-R11"


def _strict(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _lines(p):
    return [json.loads(x, object_pairs_hook=_strict) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def _write(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def _unattested_marker_episode(tmp_path):
    """An UNATTESTED marker row, made the way a store gets one: a redacted episode's export, its notice stripped,
    imported — admitted as an unattested marker (§4b, v7) and listed as such."""
    src = tt._mem(tmp_path, "src.db")
    src.store.add_episode(Episode(id="ep-m", user_id=U, date="2026-10-01", summary=SECRET, provenance=tt._prov()))
    src.redact(U, episode_id="ep-m", reason="subject_request")
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    stripped = _write(tmp_path / "stripped.jsonl", [r for r in _lines(p) if r.get("record") != "redaction"])
    dst = tt._mem(tmp_path, "dst.db")
    r = import_memory(dst.store, stripped)
    assert "ep-m" in r["unattested_markers"] and not dst.store._attested_fields(U, "episode", "ep-m")
    return dst


def test_redacting_an_unattested_marker_attests_its_marker_carriers(tmp_path):
    dst = _unattested_marker_episode(tmp_path)
    rec = dst.redact(U, episode_id="ep-m", reason="subject_request")
    assert "summary" in rec.fields_cleared and "summary" in dst.store._attested_fields(U, "episode", "ep-m")


def test_once_attested_the_marker_row_refuses_an_ordinary_write(tmp_path):
    dst = _unattested_marker_episode(tmp_path)
    dst.redact(U, episode_id="ep-m", reason="subject_request")
    with pytest.raises(ValueError, match="redacted"):
        dst.store.add_episode(Episode(id="ep-m", user_id=U, date="2026-10-01", summary="restored", provenance=tt._prov()))


def test_its_export_round_trips(tmp_path):
    dst = _unattested_marker_episode(tmp_path)
    dst.redact(U, episode_id="ep-m", reason="subject_request")
    out = tmp_path / "out.jsonl"
    export_memory(dst.store, U, out)
    (n,) = [r for r in _lines(out) if r.get("record") == "redaction"]
    assert n["fields"] and "summary" in n["fields"]
    third = tt._mem(tmp_path, "third.db")
    r = import_memory(third.store, out, restore=True)
    assert r["notices_applied"] == 1 and "summary" in third.store._attested_fields(U, "episode", "ep-m")


def test_a_record_with_nothing_to_redact_is_refused_with_nothing_written(tmp_path):
    m = tt._mem(tmp_path, "m.db")
    m.store.add_episode(Episode(id="ep-e", user_id=U, date="2026-10-01", summary="", provenance=tt._prov()))
    st = m.store
    snap = {t: st._conn.execute(f"SELECT * FROM {t}").fetchall() for t in ("episodes", "episode_event", "redactions")}
    with pytest.raises(ValueError, match="nothing to redact"):
        m.redact(U, episode_id="ep-e", reason="subject_request")
    assert {t: st._conn.execute(f"SELECT * FROM {t}").fetchall() for t in snap} == snap


def test_control_an_ordinary_record_attests_exactly_what_it_treated(tmp_path):
    m = tt._mem(tmp_path, "m.db")
    m.store.add_edge(Edge(id="e-x", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    rec = m.redact(U, edge_id="e-x", reason="subject_request")
    assert {"subject", "relation", "object"} <= set(rec.fields_cleared)
    assert set(m.store._attested_fields(U, "edge", "e-x")) == set(rec.fields_cleared)


def test_a_mixed_record_attests_both_the_treated_and_the_already_marker_carriers(tmp_path):
    """One carrier already the marker (an unattested marker edge, imported without its notice), the others holding
    content: the redaction attests BOTH."""
    src = tt._mem(tmp_path, "src.db")
    src.store.add_edge(Edge(id="e-m", user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=tt._prov()))
    p = tmp_path / "x.jsonl"
    export_memory(src.store, U, p)
    recs = [dict(r, subject=R.MARKER) if r.get("id") == "e-m" else r for r in _lines(p)]
    dst = tt._mem(tmp_path, "dst.db")
    r = import_memory(dst.store, _write(tmp_path / "m.jsonl", recs))
    assert "e-m" in r["unattested_markers"]
    rec = dst.redact(U, edge_id="e-m", reason="subject_request")
    att = set(dst.store._attested_fields(U, "edge", "e-m"))
    assert "subject" in att and {"relation", "object"} <= att      # the already-marker carrier AND the treated ones


def test_already_treated_is_the_exact_complement_of_the_treatment():
    """Whatever `treat_*` writes, `already_treated` reads back on the result — for both kinds, from a populated record."""
    e = Edge(id="e", user_id=U, subject="s", relation="r", object="o", provenance=tt._prov()).model_dump(mode="json")
    new, treated = R.treat_edge(e, reason_registry=())
    assert set(treated) <= set(R.already_treated("edge", new)) | set(R.EDGE_CLEAR)
    ep = Episode(id="p", user_id=U, date="2026-10-01", summary="x", provenance=tt._prov()).model_dump(mode="json")
    new, treated = R.treat_episode(ep, reason_registry=(), recognised_kinds=R.RECOGNISED_EPISODE_KINDS)
    assert set(treated) == set(R.already_treated("episode", new))
