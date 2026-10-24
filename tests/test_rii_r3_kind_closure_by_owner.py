"""Research's third reader (R-II round 3, NEXT-ROUND; research c31b3190): the import's KIND closure (0041 §2d-iv, §4h(ii))
admits a MARKER-valued episode kind only when the DESTINATION user's own attestation covers `kind`. Another user's
standing notice naming `kind` for the same id must not admit it.

The episode-reason and edge-reason cells (tests/test_rii_r3_01_episode_owner.py) kill the class mutant "every
_attested_fields reader keys by id"; this cell holds the kind closure's reader on its own, so a per-site mutant there
(`_attested_fields(_ANY_OWNER, ...)` at the kind check alone) is killed too. A's notice must name `kind`, which only a
redaction of a PROSE kind does, and the write closure refuses a prose kind: the fixture plants a pre-closure row, as
older stores hold it, and asserts the anchor (the standing notice names `kind`) before it asserts the refusal.
"""
import json

import pytest

from veracium import Memory, MemoryConfig
from veracium import portability as port
from veracium.redaction import MARKER
from veracium.schema import Disclosure, Episode, EvidenceAuthor, Provenance

A, B = "kind-owner-a", "kind-owner-b"
EID = "r3-k"


def _mem(tmp_path, name):
    return Memory(llm=lambda q, **k: "x", config=MemoryConfig(db_path=str(tmp_path / name), require_source_id=False,
                                                             scope_groups={}))


def _ep(uid, kind=None):
    extra = {"kind": kind} if kind is not None else {}
    return Episode(id=EID, user_id=uid, date="2026-01-02", summary=f"{uid}'s fact",
                   provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r3-k-ev",
                                         disclosure=Disclosure.MENTIONABLE), **extra)


def _lines(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def _write(p, ls):
    p.write_text("".join(json.dumps(x) + "\n" for x in ls))
    return p


def _a_holds_a_standing_notice_naming_kind(tmp_path, dst):
    src = _mem(tmp_path, "a-src.db")
    ep = _ep(A, kind="told me in confidence")                       # a pre-closure prose kind, planted as older stores hold it
    src.store._conn.execute("INSERT INTO episodes(id,user_id,date,json) VALUES(?,?,?,?)",
                            (ep.id, ep.user_id, ep.date, ep.model_dump_json()))
    src.store._conn.commit()
    src.redact(A, episode_id=EID, reason="subject_request")
    full = tmp_path / "a.jsonl"
    port.export_memory(src.store, A, str(full))
    src.close()
    ls = _lines(full)
    notices = [x for x in ls[1:] if x.get("record") == "redaction"]
    assert len(notices) == 1 and "kind" in notices[0]["fields"], notices   # the anchor: A's notice attests `kind`
    r = port.import_memory(dst.store, str(_write(tmp_path / "a-notices.jsonl", [ls[0], *notices])), restore=True)
    assert r["notices_standing"] == 1, r
    assert "kind" in dst.store._attested_fields(A, "episode", EID, coverage=True)


def _b_forged_marker_kind(tmp_path):
    b = _mem(tmp_path, "b-src.db")
    b.store.add_episode(_ep(B))
    plain = tmp_path / "b.jsonl"
    port.export_memory(b.store, B, str(plain))
    b.close()
    ls, n = _lines(plain), 0
    for x in ls[1:]:
        if x.get("record") == "episode" and x.get("id") == EID:
            x["kind"] = MARKER
            n += 1
    assert n == 1, "the forged field must land on exactly one record"
    return _write(tmp_path / "b-forged.jsonl", ls)


@pytest.mark.parametrize("a_notice", [False, True], ids=["control-no-notice", "A-holds-a-standing-notice"])
def test_another_users_standing_notice_never_admits_a_marker_kind(tmp_path, a_notice):
    dst = _mem(tmp_path, "dst.db")
    try:
        if a_notice:
            _a_holds_a_standing_notice_naming_kind(tmp_path, dst)
        assert "kind" not in dst.store._attested_fields(B, "episode", EID, coverage=True)
        with pytest.raises(ValueError, match="is not a recognised operational kind"):
            port.import_memory(dst.store, str(_b_forged_marker_kind(tmp_path)), user_id=B)
        assert dst.store._conn.execute("SELECT 1 FROM episodes WHERE id=?", (EID,)).fetchone() is None
    finally:
        dst.close()
