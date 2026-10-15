"""specs/0041 round 11 — R10-01: the outcome-chain import branch applies a notice to a HELD outcome, by the same
held-differs rule as edges and episodes; the chain's STRUCTURE still refuses, notice or not.

Round 10's outcome branch refused any held link whose record differed — so a source's full export after it redacted
an outcome could never reach a destination holding the earlier outcome, which kept the content. The rule is now the
edge/interaction rule, shared by one helper (research's stage-1, Option 1): with a notice, the held version is
redacted in the commit and flagged; without one, refused. A difference in `portability.OUTCOME_LINK_STRUCTURE` (the
chain's topology) refuses first, whatever the notice says — outcome history is never overwritten.

Every cell goes through `record_outcome`, `Memory.redact`, `export_memory` and `import_memory`; a file is edited only
to build a reviewer's input (a moved `seq`, an edited summary).
"""
import importlib.util
import json
import pathlib
import sys

import pytest

from veracium.portability import OUTCOME_LINK_STRUCTURE, export_memory, import_memory
from veracium.schema import Edge, Episode

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r11o", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r11o"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-OUTCOME-R11"


# the 2026-10-13 notice-binding hotfix's report and its two direct checks: a default-path notice that is not applied
# is listed in `notices_not_applied` as [kind, id] (never in `inconsistent_notices`, which keeps "the held version was
# redacted anyway", a restore-only outcome now); the held bytes are compared on the WHOLE json; rows are counted directly
def _not_applied(r, kind, tid):
    return [kind, tid] in [list(x)[:2] for x in r["notices_not_applied"]] and tid not in r["inconsistent_notices"]


def _held_json(st, kind, tid):
    row = st._conn.execute(f"SELECT json FROM {'edges' if kind == 'edge' else 'episodes'} WHERE id=?", (tid,)).fetchone()
    return row[0] if row else None


def _redaction_rows(st, tid=None):
    if tid is None:
        return st._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0]
    return st._conn.execute("SELECT COUNT(*) FROM redactions WHERE target_id=?", (tid,)).fetchone()[0]


def _applied_rows(st, tid=None):
    """T4 (specs/0041 §11.6.6): APPLIED redaction rows only — an attestation. A default import over a held target now
    records the notice PENDING (and an absent one STANDING), so "nothing applied" is no APPLIED row, not no row."""
    q = "SELECT COUNT(*) FROM redactions WHERE state='applied'"
    return st._conn.execute(q + ("" if tid is None else " AND target_id=?"), (() if tid is None else (tid,))).fetchone()[0]


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


def _head(recs):
    return [r for r in recs if r.get("kind") == "veracium-export"]


def _notices(recs):
    return [r for r in recs if r.get("record") == "redaction"]


def _source(tmp_path, kind):
    """A source holding one record of `kind` ('outcome' or 'interaction'); its export BEFORE the redaction (p1) and
    AFTER (p2). Returns (target id, p1, p2)."""
    src = tt._mem(tmp_path, f"src-{kind}.db")
    if kind == "outcome":
        src.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="prefers", object=SECRET,
                                provenance=tt._prov()))
        src.record_outcome(U, "e-1", outcome="confirmed", actor="user", evidence_ref="ev-outcome")
        tid = [e.id for e in src.store.episodes(U) if e.kind == "outcome"][0]
    else:
        src.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-10-01", summary=f"we discussed {SECRET}",
                                      provenance=tt._prov()))
        tid = "ep-1"
    p1 = tmp_path / f"{kind}-1.jsonl"
    export_memory(src.store, U, p1)
    src.redact(U, episode_id=tid, reason="subject_request")
    p2 = tmp_path / f"{kind}-2.jsonl"
    export_memory(src.store, U, p2)
    return tid, p1, p2


def _summary(st, tid):
    row = st._conn.execute("SELECT json FROM episodes WHERE id=?", (tid,)).fetchone()
    return json.loads(row[0])["summary"]


def _events(st):
    return st._conn.execute("SELECT COUNT(*) FROM episode_event").fetchone()[0]


def _outcome_of(r):
    return {"inconsistent": bool(r["inconsistent_notices"]), "applied": r["notices_applied"],
            "existing": r["notices_existing"], "skipped_ge_1": r["skipped"] >= 1}


@pytest.mark.parametrize("restore", [False, True])
def test_R10_01_full_export_applies_notice_to_held_outcome(tmp_path, restore):
    """The verdict's named regression: held = the earlier outcome; the source's full export after redacting it."""
    tid, p1, p2 = _source(tmp_path, "outcome")
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p1, restore=restore)
    assert SECRET in _summary(dst.store, tid)
    held = _held_json(dst.store, "episode", tid)
    r = import_memory(dst.store, p2, restore=restore)
    if not restore:
        # (A) attack-shaped on the default path: a notice reaching a HELD record is what the 2026-10-13 notice-binding
        # hotfix closes — not applied, the held bytes unchanged, nothing attested, no applied row (T4: the notice PENDING), reported as not applied
        assert _held_json(dst.store, "episode", tid) == held and _applied_rows(dst.store, tid) == 0
        assert not dst.store._attested_fields(U, "episode", tid) and r["notices_applied"] == 0
        assert _not_applied(r, "episode", tid)
        return
    assert SECRET not in _summary(dst.store, tid)
    assert dst.store._attested_fields(U, "episode", tid) and r["notices_applied"] == 1 and tid in r["inconsistent_notices"]


@pytest.mark.parametrize("restore", [False, True])
def test_the_treated_held_outcome_keeps_its_chain(tmp_path, restore):
    tid, p1, p2 = _source(tmp_path, "outcome")
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p1, restore=restore)
    before = [e for e in dst.store.episodes(U) if e.kind == "outcome"]
    import_memory(dst.store, p2, restore=restore)
    after = [e for e in dst.store.episodes(U) if e.kind == "outcome"]
    struct = lambda eps: sorted(tuple(e.model_dump(mode="json")["provenance"]["evidence_ref"] if f == "provenance.evidence_ref"
                                      else e.model_dump(mode="json").get(f) for f in OUTCOME_LINK_STRUCTURE) for e in eps)
    assert struct(after) == struct(before)                       # INV-1: the chain's structure is unchanged


def test_A2_an_already_treated_held_outcome_meeting_its_old_record_ends_existing_with_no_new_event(tmp_path):
    tid, p1, p2 = _source(tmp_path, "outcome")
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p2)                                 # held = treated
    n0 = _events(dst.store)
    old = [r for r in _lines(p1) if r.get("record") in ("edge", "episode")]
    r = import_memory(dst.store, _write(tmp_path / "old.jsonl", _head(_lines(p2)) + old + _notices(_lines(p2))))
    assert r["notices_existing"] == 1 and r["notices_applied"] == 0 and _events(dst.store) == n0
    assert SECRET not in _summary(dst.store, tid)


@pytest.mark.parametrize("shape", ["A1", "A2"])
def test_outcome_and_interaction_give_the_same_result_for_the_same_difference(tmp_path, shape):
    """ONE rule: the outcome branch reports exactly what the interaction branch reports in the same state — the
    same applied/existing counts and the same inconsistent flag."""
    got = {}
    for kind in ("outcome", "interaction"):
        d = tmp_path / kind
        d.mkdir()
        _tid, p1, p2 = _source(d, kind)
        dst = tt._mem(d, "dst.db")
        if shape == "A1":
            import_memory(dst.store, p1)
            f = p2
        else:
            import_memory(dst.store, p2)
            old = [r for r in _lines(p1) if r.get("record") in ("edge", "episode")]
            f = _write(d / "old.jsonl", _head(_lines(p2)) + old + _notices(_lines(p2)))
        got[kind] = _outcome_of(import_memory(dst.store, f))
    assert got["outcome"] == got["interaction"], got


def test_control_a_changed_outcome_with_no_notice_still_refuses(tmp_path):
    tid, p1, _p2 = _source(tmp_path, "outcome")
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p1)
    chg = [dict(r, summary=r["summary"] + " (edited)") if r.get("id") == tid else r for r in _lines(p1)]
    with pytest.raises(ValueError, match="outcome link"):
        import_memory(dst.store, _write(tmp_path / "chg.jsonl", chg))
    assert SECRET in _summary(dst.store, tid)


@pytest.mark.parametrize("with_notice", [True, False])
def test_control_a_topology_conflict_refuses_notice_or_not(tmp_path, with_notice):
    tid, p1, p2 = _source(tmp_path, "outcome")
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p1)
    src = _lines(p2) if with_notice else _lines(p1)
    moved = [dict(r, seq=(r.get("seq") or 0) + 5) if r.get("id") == tid and r.get("record") == "episode" else r for r in src]
    # the chain-shape validation (specs/0009 H5) refuses a moved seq BEFORE the per-link check, so the named
    # structural set is defence in depth behind it; the claim is the OUTCOME: refused, content kept, nothing attested
    with pytest.raises(ValueError, match="outcome (chain|link)"):
        import_memory(dst.store, _write(tmp_path / "moved.jsonl", moved))
    assert SECRET in _summary(dst.store, tid) and not dst.store._attested_fields(U, "episode", tid)


def test_the_structural_projection_separates_topology_from_content(tmp_path):
    """The named set, exercised directly (H5 shields it from the import path): a moved seq, a different supersedes
    or evidence_ref changes the structure; a treated summary does not."""
    from veracium.portability import _outcome_structure
    tid, p1, p2 = _source(tmp_path, "outcome")
    rec = lambda p: Episode.model_validate({k: v for k, v in
                                            [r for r in _lines(p) if r.get("id") == tid][0].items() if k != "record"})
    held, treated = rec(p1), rec(p2)
    assert _outcome_structure(held) == _outcome_structure(treated) and held.summary != treated.summary
    for upd in ({"seq": 9}, {"supersedes_episode": "ep-other"},
                {"provenance": held.provenance.model_copy(update={"evidence_ref": "ev-other"})}):
        assert _outcome_structure(held.model_copy(update=upd)) != _outcome_structure(held), upd


def test_the_structural_set_is_named_and_covers_the_chain_key():
    assert {"edge_id", "seq", "supersedes_episode", "provenance.evidence_ref"} <= set(OUTCOME_LINK_STRUCTURE)
    assert "summary" not in OUTCOME_LINK_STRUCTURE              # content is never structure
