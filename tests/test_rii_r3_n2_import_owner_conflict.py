"""Research's N2 (R-II round 3, NEXT-ROUND): an import carrying an id ANOTHER user holds at the destination refuses at
once, naming the owner conflict, and never as a lost race.

The import's preflight reads the destination per user, so another user's row is invisible to it: the plan expects the id
absent, the commit's revalidation (store-wide, by id) finds it present, and the store answered DESTINATION_CHANGED. The
retry loop re-planned the same invisible collision until it gave up with "kept losing a race against concurrent writes
after 8 attempts", though nothing raced. The outcome was already fail-closed (nothing imported); the defect was the
reason given and seven futile re-plans. The owner of a record never changes on any persistence path (edges 0008 §6d,
episodes 0004 v3.5 §2c (i)), so a retry can never succeed: the commit now refuses it as an owner conflict.

1. THE MATRIX: edge only / episode only / both × default import / trusted restore — refused naming the conflict, ONE
   commit attempt, nothing of B's written, A's rows unchanged, and the message does not name the other user.
2. ATOMIC: a file whose edge is new and whose episode collides writes nothing, the new edge included.
3. THE CONTROL: the same-owner re-import is still an idempotent skip.
"""
import pytest

from datetime import datetime, timezone

from veracium import Memory, MemoryConfig
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance

A, B = "n2-owner-a", "n2-owner-b"
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _mem(path):
    return Memory(llm=lambda q, **k: "x", config=MemoryConfig(db_path=str(path), require_source_id=False, scope_groups={}))


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev-n2", disclosure=Disclosure.MENTIONABLE)


def _edge(uid, obj, eid="n2-e"):
    return Edge(id=eid, user_id=uid, subject="user", relation="located_at", object=obj, provenance=_prov(), valid_from=T0)


def _ep(uid, summary, eid="n2-p"):
    return Episode(id=eid, user_id=uid, date="2026-01-02", summary=summary, provenance=_prov())


def _rows(store):
    edges = store._conn.execute("SELECT id, user_id, json FROM edges ORDER BY id").fetchall()
    eps = store._conn.execute("SELECT id, user_id, json FROM episodes ORDER BY id").fetchall()
    return edges, eps


def _export_b(tmp_path, kinds, extra_edge=False):
    src = _mem(tmp_path / "src.db")
    if "edge" in kinds:
        src.store.add_edge(_edge(B, "Porto"))
    if "episode" in kinds:
        src.store.add_episode(_ep(B, "B lives in Porto."))
    if extra_edge:
        src.store.add_edge(_edge(B, "Braga", eid="n2-e-new"))
    f = tmp_path / "b.jsonl"
    src.export_memory(B, str(f))
    src.close()
    return f


def _import(dst, f, restore):
    return dst.import_memory(str(f), restore=True) if restore else dst.import_memory(str(f), user_id=B)


def _count_commits(monkeypatch, store):
    calls = []
    real = store.commit_outcome_import_plan

    def counting(*a, **k):
        calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(store, "commit_outcome_import_plan", counting)
    return calls


# ---- 1. the matrix ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("restore", [False, True], ids=["default", "restore"])
@pytest.mark.parametrize("kinds", [("edge",), ("episode",), ("edge", "episode")], ids=["edge", "episode", "both"])
def test_another_users_id_is_refused_as_an_owner_conflict_at_the_first_attempt(tmp_path, monkeypatch, kinds, restore):
    f = _export_b(tmp_path, kinds)
    dst = _mem(tmp_path / "dst.db")
    if "edge" in kinds:
        dst.store.add_edge(_edge(A, "Lisbon"))
    if "episode" in kinds:
        dst.store.add_episode(_ep(A, "A lives in Lisbon."))
    before = _rows(dst.store)
    calls = _count_commits(monkeypatch, dst.store)
    with pytest.raises(ValueError, match=r"is held by another user in this store") as ei:
        _import(dst, f, restore)
    msg = str(ei.value)
    assert "race" not in msg, msg
    assert A not in msg, f"the refusal names the other user: {msg}"
    assert len(calls) == 1, f"{len(calls)} commit attempts; an owner conflict is not retried"
    assert _rows(dst.store) == before, "the refused import wrote something"
    assert dst.store.edges(B) == [] and dst.store.episodes(B, include_retired=True) == []
    dst.close()


# ---- 2. atomic --------------------------------------------------------------------------------------------------

def test_a_colliding_episode_refuses_the_files_new_edge_too(tmp_path):
    f = _export_b(tmp_path, ("episode",), extra_edge=True)
    dst = _mem(tmp_path / "dst.db")
    dst.store.add_episode(_ep(A, "A lives in Lisbon."))
    before = _rows(dst.store)
    with pytest.raises(ValueError, match=r"episode 'n2-p' is held by another user"):
        _import(dst, f, restore=False)
    assert _rows(dst.store) == before
    assert dst.store.edges(B) == []
    dst.close()


# ---- 3. the control ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("restore", [False, True], ids=["default", "restore"])
def test_the_same_owners_reimport_is_still_an_idempotent_skip(tmp_path, monkeypatch, restore):
    f = _export_b(tmp_path, ("edge", "episode"))
    dst = _mem(tmp_path / "dst.db")
    _import(dst, f, restore)
    before = _rows(dst.store)
    calls = _count_commits(monkeypatch, dst.store)
    r = _import(dst, f, restore)
    assert r["edges"] == 0 and r["episodes"] == 0 and r["skipped"] == 2, r
    assert len(calls) == 1
    assert _rows(dst.store) == before
    dst.close()
