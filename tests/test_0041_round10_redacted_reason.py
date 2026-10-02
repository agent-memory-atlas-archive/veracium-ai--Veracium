"""specs/0041 §11.2 (round 10): `redacted` is written ONLY by a redaction. Every other writer — enumerated, not
recalled: the edge upsert (add_edge, the supersession plan, correction), add_episode, the two row retirers
(invalidate_edge's and the revocation sweep's) and the import commit — refuses it; import admits it only when the same
atomic unit attests the record (a notice in the plan, or one held). Each refusal's control: a registered non-redaction
reason is still admitted. And the real redaction still writes it.
"""
import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

from veracium.portability import export_memory, import_memory
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance
from veracium.store.sqlite import SqliteStore

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r10rr", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r10rr"] = tt
_spec.loader.exec_module(tt)

U = "u"
AT = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)


def _edge(eid="e-1", **kw):
    return Edge(**{"id": eid, "user_id": U, "subject": "user", "relation": "pet", "object": "a cat",
                   "provenance": _prov(), **kw})


def _ep(eid="ep-1", **kw):
    return Episode(**{"id": eid, "user_id": U, "date": "2026-09-01", "summary": "s", "provenance": _prov(), **kw})


@pytest.mark.parametrize("reason, ok", [("redacted", False), ("disputed", True)])
def test_add_edge(tmp_path, reason, ok):
    st = SqliteStore(str(tmp_path / "s.db"))
    call = lambda: st.add_edge(_edge(invalidated_at=AT, invalidation_reason=reason))
    if ok:
        call()
    else:
        with pytest.raises(ValueError, match="only a redaction writes"):
            call()
    assert st._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == int(ok)


@pytest.mark.parametrize("reason, ok", [("redacted", False), ("superseded", True)])
def test_add_episode(tmp_path, reason, ok):
    st = SqliteStore(str(tmp_path / "s.db"))
    call = lambda: st.add_episode(_ep(retired_at=AT, retired_reason=reason))
    if ok:
        call()
    else:
        with pytest.raises(ValueError, match="only a redaction writes"):
            call()
    assert st._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == int(ok)


@pytest.mark.parametrize("reason, ok", [("redacted", False), ("disputed", True)])
def test_invalidate_edge(tmp_path, reason, ok):
    st = SqliteStore(str(tmp_path / "s.db"))
    st.add_edge(_edge())
    call = lambda: st.invalidate_edge("e-1", AT, reason)
    if ok:
        call()
    else:
        with pytest.raises(ValueError, match="only a redaction writes"):
            call()
    assert (json.loads(st._conn.execute("SELECT json FROM edges").fetchone()[0])["invalidation_reason"]
            == ("disputed" if ok else None))


@pytest.mark.parametrize("reason, ok", [("redacted", False), ("revoked_source", True)])
def test_the_revocation_sweeps_episode_retirer(tmp_path, reason, ok):
    """The episode row retirer's one caller is the revocation sweep (always `revoked_source`); it is exercised
    directly, inside a transaction as its caller holds one, because no public path can pass it `redacted`."""
    st = SqliteStore(str(tmp_path / "s.db"))
    st.add_episode(_ep())
    with st.atomic():
        if ok:
            st._retire_episode_row("ep-1", AT, reason)
        else:
            with pytest.raises(ValueError, match="only a redaction writes"):
                st._retire_episode_row("ep-1", AT, reason)


def _export_with(tmp_path, kind, reason, with_notice):
    src = tt._mem(tmp_path, f"src-{with_notice}.db")                  # a fresh source per file
    if kind == "edge":
        src.store.add_edge(_edge(object="a secret"))
        src.redact(U, edge_id="e-1", reason="subject_request")
    else:
        src.store.add_episode(_ep(summary="a secret"))
        src.redact(U, episode_id="ep-1", reason="subject_request")
    p = tmp_path / f"x-{with_notice}.jsonl"
    export_memory(src.store, U, p)
    recs = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    for r in recs:
        if r.get("record") == kind:
            r["invalidation_reason" if kind == "edge" else "retired_reason"] = reason
            r["invalidated_at" if kind == "edge" else "retired_at"] = "2026-09-01T00:00:00+00:00"
    if not with_notice:
        recs = [r for r in recs if r.get("record") != "redaction"]
    out = tmp_path / f"edited-{with_notice}.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return out


@pytest.mark.parametrize("kind", ["edge", "episode"])
def test_import_admits_redacted_only_with_an_attesting_notice(tmp_path, kind):
    table = "edges" if kind == "edge" else "episodes"
    dst = tt._mem(tmp_path, "dst.db")
    with pytest.raises(ValueError):
        import_memory(dst.store, _export_with(tmp_path, kind, "redacted", with_notice=False), restore=True)
    assert dst.store._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0          # nothing written
    import_memory(dst.store, _export_with(tmp_path, kind, "redacted", with_notice=True), restore=True)
    assert dst.store._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1          # attested: admitted


def test_the_real_redaction_still_writes_it(tmp_path):
    m = tt._frozen_memory(tmp_path)
    eid = tt._frozen_rows()["prose_retired_reason"]
    m.redact(U, episode_id=eid, reason="subject_request")
    assert [e for e in m.store.episodes(U, include_retired=True) if e.id == eid][0].retired_reason == "redacted"
