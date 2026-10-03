"""specs/0041 round 10 — the redaction notice across the import boundary (round-9 R9-04, R9-05, R9-06, R9-08).

Every cell goes through the real `export_memory` / `import_memory` / `Memory.redact` paths; a file is edited only to
construct the INPUT a reviewer would (a later contradictory body, a prose field name), never a destination's state.

R9-04  the notice row binds the destination user and the typed target; a repeat is idempotent only for the SAME
       foreign body, and a contradictory body refuses atomically across imports.
R9-05  the foreign body is immutable and travels unchanged: a witnessed receipt reports the SOURCE's facts (None
       where unknown) with this store's application facts beside them; an honest relay is the same notice.
R9-06  a marker-valued episode kind is admitted only under an attestation of `kind` in the same unit.
R9-08  notice field names are the declared kind's carrier paths, at the parser AND at the commit primitive.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

from veracium import redaction as R
from veracium.portability import export_memory, import_memory
from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r10n", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r10n"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-NOTICE-4471"


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)


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


def _notice(p):
    (n,) = [r for r in _lines(p) if r.get("record") == "redaction"]
    return n


def _source(tmp_path, name="src", eid="e-x", reason="legal_obligation"):
    src = tt._mem(tmp_path, f"{name}.db")
    src.store.add_edge(Edge(id=eid, user_id=U, subject="user", relation="lives_at", object=SECRET, provenance=_prov()))
    receipt = src.redact(U, edge_id=eid, reason=reason)
    path = tmp_path / f"{name}.jsonl"
    export_memory(src.store, U, path)
    return src, receipt, path


def _rows(st, table, where="1=1", args=()):
    return st._conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args).fetchone()[0]


# ------------------------------------------------------------------------------------------------ R9-04
def test_R9_04_one_notice_imported_for_two_destination_users_attests_each_users_own_record(tmp_path):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    r1 = import_memory(dst.store, path, user_id="v1")
    r2 = import_memory(dst.store, path, user_id="v2")
    assert (r1["notices_applied"], r2["notices_applied"], r2["notices_existing"]) == (1, 1, 0)
    for v in ("v1", "v2"):
        (eid,) = [e.id for e in dst.store.edges(v, active_only=False)]
        assert eid.startswith("imp-e-")                                # the remapped target
        assert dst.store._attested_fields(v, "edge", eid)               # each user's OWN record is attested
    # control: the two imports did write two destinations' records (the instrument sees a per-destination identity)
    assert {_rows(dst.store, "edges", "user_id=?", (v,)) for v in ("v1", "v2")} == {1}
    assert _rows(dst.store, "redactions") == 2


def test_R9_04_an_honest_repeat_is_idempotent_and_writes_nothing(tmp_path):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path)
    before = dst.store._conn.execute("SELECT * FROM redactions").fetchall()
    again = import_memory(dst.store, path)
    assert (again["notices_existing"], again["notices_applied"]) == (1, 0)
    assert dst.store._conn.execute("SELECT * FROM redactions").fetchall() == before


def test_R9_04_a_later_contradictory_body_under_the_same_identity_refuses_atomically(tmp_path):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path)
    recs = _lines(path)
    other = tt._mem(tmp_path, "other.db")                            # a record the second file would add
    other.store.add_edge(Edge(id="e-new", user_id=U, subject="user", relation="likes", object="tea", provenance=_prov()))
    extra = [r for r in _lines(export_memory(other.store, U, tmp_path / "o.jsonl")["path"]) if r.get("record") == "edge"]
    later = [dict(r, fields=["object", "subject"]) if r.get("record") == "redaction" else r for r in recs] + extra
    snapshot = [dst.store._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("edges", "redactions")]
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, _write(tmp_path / "later.jsonl", later))
    assert [dst.store._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("edges", "redactions")] == snapshot


def test_R9_04_two_bodies_under_one_identity_in_one_file_still_refuse(tmp_path):
    _s, _r, path = _source(tmp_path)
    recs = _lines(path)
    n = _notice(path)
    with pytest.raises(ValueError, match="different bodies"):
        import_memory(tt._mem(tmp_path, "d.db").store, _write(tmp_path / "two.jsonl", recs + [dict(n, reason="subject_request")]))


# ------------------------------------------------------------------------------------------------ R9-05
def test_R9_05_a_witnessed_receipt_reports_the_sources_facts_and_this_stores_application_beside_them(tmp_path):
    _s, rs, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    for i in range(2):                                                # the destination has history of its own
        dst.store.add_edge(Edge(id=f"e-pre-{i}", user_id=U, subject="user", relation="likes", object=f"t{i}",
                                provenance=_prov()))
    import_memory(dst.store, path)
    rd = dst.redact(U, edge_id="e-x", reason="subject_request")      # a repeat: the receipt read back
    assert rd.reconstructed and rd.repeated
    assert (rd.reason, rd.recorded_at, rd.store_version_before, rd.store_version_after, rd.marker_version) == \
        (rs.reason, rs.recorded_at, rs.store_version_before, rs.store_version_after, rs.marker_version)
    assert rd.event_ref == rs.event_ref                                # the SOURCE's event
    assert rd.applied_at is not None and rd.applied_event_ref is not None
    assert (rd.applied_store_version_before, rd.applied_store_version_after) != \
        (rs.store_version_before, rs.store_version_after)               # this store's own counters, named as such


def test_R9_05_the_relay_re_exports_the_source_body_unchanged(tmp_path):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path)
    export_memory(dst.store, U, tmp_path / "relay.jsonl")
    src_n, relay_n = _notice(path), _notice(tmp_path / "relay.jsonl")
    assert relay_n == src_n                                            # every key, including reason and time


def test_R9_05_the_original_and_its_honest_relay_are_one_notice_together_or_in_sequence(tmp_path):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path)
    export_memory(dst.store, U, tmp_path / "relay.jsonl")
    both = _write(tmp_path / "both.jsonl", _lines(path) + [_notice(tmp_path / "relay.jsonl")])
    third = tt._mem(tmp_path, "third.db")
    r = import_memory(third.store, both)
    assert r["notices_applied"] == 1 and _rows(third.store, "redactions") == 1
    fourth = tt._mem(tmp_path, "fourth.db")
    import_memory(fourth.store, path)
    assert import_memory(fourth.store, tmp_path / "relay.jsonl")["notices_existing"] == 1


def test_R9_05_a_relay_that_alters_the_body_is_refused(tmp_path):
    _s, _r, path = _source(tmp_path)
    # round 11 (R10-04): the alteration was the witness label, which the parser now refuses on its own (before any
    # body comparison); a genuinely different ORIGINATING reason keeps this cell on the body comparison it tests
    altered = dict(_notice(path), reason="subject_request", recorded_at="2099-01-01T00:00:00+00:00")
    assert altered["reason"] != _notice(path)["reason"]
    with pytest.raises(ValueError, match="different bodies"):
        import_memory(tt._mem(tmp_path, "d.db").store, _write(tmp_path / "a.jsonl", _lines(path) + [altered]))


def test_R9_05_facts_the_notice_does_not_carry_are_None_and_serialise_as_null(tmp_path):
    _s, _r, path = _source(tmp_path)
    recs = [{k: v for k, v in r.items() if k not in ("store_version_before", "store_version_after", "recorded_at")}
            if r.get("record") == "redaction" else r for r in _lines(path)]
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, _write(tmp_path / "bare.jsonl", recs))
    rd = dst.redact(U, edge_id="e-x", reason="subject_request")
    assert (rd.store_version_before, rd.store_version_after, rd.recorded_at) == (None, None, None)
    dumped = json.loads(rd.model_dump_json(), object_pairs_hook=_strict)
    assert dumped["store_version_before"] is None and dumped["store_version_after"] is None
    assert rd.applied_store_version_after is not None                 # what this store did know, it says


# ------------------------------------------------------------------------------------------------ R9-06
def _redacted_prose_kind_export(tmp_path):
    """The treated frozen ep-prose-kind and its notice ONLY: the frozen store also holds other legacy shapes (a prose
    retired_reason, which the D1 closure now refuses at import), and a cell about the kind must not be decided by them."""
    m = tt._frozen_memory(tmp_path)
    eid = tt._frozen_rows()["prose_kind"]
    m.redact(U, episode_id=eid, reason="subject_request")
    full = tmp_path / "full.jsonl"
    export_memory(m.store, U, full)
    keep = [r for r in _lines(full) if r.get("record") not in ("edge", "episode", "redaction")
            or (r.get("record") == "episode" and r["id"] == eid)
            or (r.get("record") == "redaction" and r["target_id"] == eid)]
    return eid, _write(tmp_path / "pk.jsonl", keep)


def test_R9_06_the_treated_historical_prose_kind_episode_round_trips_with_its_notice(tmp_path):
    eid, path = _redacted_prose_kind_export(tmp_path)
    n = [r for r in _lines(path) if r.get("record") == "redaction" and r["target_id"] == eid]
    assert n and "kind" in n[0]["fields"]
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path, restore=True)
    row = json.loads(dst.store._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()[0])
    assert row["kind"] == R.MARKER and "kind" in dst.store._attested_fields(U, "episode", eid)


def test_R9_06_a_standing_notice_admits_the_marker_kind_when_the_record_arrives_later(tmp_path):
    eid, path = _redacted_prose_kind_export(tmp_path)
    recs = _lines(path)
    head = [r for r in recs if r.get("record") not in ("episode", "edge", "redaction")]
    notice_only = head + [r for r in recs if r.get("record") == "redaction" and r["target_id"] == eid]
    record_only = head + [r for r in recs if r.get("record") == "episode" and r["id"] == eid]
    dst = tt._mem(tmp_path, "dst.db")
    assert import_memory(dst.store, _write(tmp_path / "n.jsonl", notice_only), restore=True)["notices_standing"] == 1
    import_memory(dst.store, _write(tmp_path / "r.jsonl", record_only), restore=True)
    assert "kind" in dst.store._attested_fields(U, "episode", eid)


@pytest.mark.parametrize("variant", ["no-notice", "notice-without-kind", "prose-kind"])
def test_R9_06_the_closure_still_refuses_what_no_attestation_accounts_for(tmp_path, variant):
    eid, path = _redacted_prose_kind_export(tmp_path)
    recs = _lines(path)
    if variant == "no-notice":
        recs = [r for r in recs if not (r.get("record") == "redaction" and r["target_id"] == eid)]
    elif variant == "notice-without-kind":
        recs = [dict(r, fields=[f for f in r["fields"] if f != "kind"])
                if r.get("record") == "redaction" and r["target_id"] == eid else r for r in recs]
    else:
        recs = [dict(r, kind="a private diary entry") if r.get("record") == "episode" and r["id"] == eid else r
                for r in recs]
    dst = tt._mem(tmp_path, "dst.db")
    with pytest.raises(ValueError):
        import_memory(dst.store, _write(tmp_path / "v.jsonl", recs), restore=True)
    assert _rows(dst.store, "episodes") == 0                             # nothing imported


# ------------------------------------------------------------------------------------------------ R9-08
@pytest.mark.parametrize("fields, ok", [
    (["private prose disguised as a field name"], False),
    (["summary"], False),                                              # an EPISODE path on an edge notice
    (["object", "object"], False),                                     # repeated
    ([], False),
    (["object", "confirmations.request_digest", "contribution_ledger.identity_digest"], True),   # side-table paths
])
def test_R9_08_notice_field_names_are_the_kinds_carrier_paths(tmp_path, fields, ok):
    _s, _r, path = _source(tmp_path)
    recs = [dict(r, fields=fields) if r.get("record") == "redaction" else r for r in _lines(path)]
    dst = tt._mem(tmp_path, "dst.db")
    if ok:
        import_memory(dst.store, _write(tmp_path / "f.jsonl", recs))
        assert set(fields) <= dst.store._attested_fields(U, "edge", "e-x")
    else:
        with pytest.raises(ValueError, match="carrier paths|invalid"):
            import_memory(dst.store, _write(tmp_path / "f.jsonl", recs))
        assert _rows(dst.store, "edges") == 0 and _rows(dst.store, "redactions") == 0   # the unit, atomically


def test_R9_08_the_commit_primitive_refuses_prose_field_names_on_its_own(tmp_path):
    """The second boundary: a plan that reaches the primitive by another route than the parser."""
    dst = tt._mem(tmp_path, "dst.db")
    bad = {"origin": "o", "source_user": U, "source_event_ref": "u:1", "target_kind": "edge", "target_id": "e-z",
           "fields": ["private prose"], "marker_version": 1, "reason": "subject_request"}
    with pytest.raises(ValueError, match="carrier paths"):
        dst.store.commit_outcome_import_plan(U, {"edges": [], "episodes": [], "contributions": [], "redactions": [bad]},
                                             {"edge_ids": {}, "episode_records": {}, "chain_heads": {},
                                              "contribution_state": {}})
    assert _rows(dst.store, "redactions") == 0


def test_R9_08_the_allowed_set_is_derived_from_the_treatment_tables():
    for kind in ("edge", "episode"):
        own = {p for p, _h in R.SIDE_TABLE_TREATMENTS[kind]}
        assert own <= R.carrier_paths(kind)
    assert "summary" in R.carrier_paths("episode") and "summary" not in R.carrier_paths("edge")


# ------------------------------------------------------------------------------------------------ stage 2, S2-1
def _contradicting_copy(tmp_path, path, **change):
    """The source file with its notice changed (a REASON, which R9-08's field check does not catch first) and a NEW
    record added, so "nothing written" is an atomicity claim about a real write, not an empty file."""
    other = tt._mem(tmp_path, "other-s2.db")
    other.store.add_edge(Edge(id="e-new-s2", user_id=U, subject="user", relation="likes", object="tea", provenance=_prov()))
    extra = [r for r in _lines(export_memory(other.store, U, tmp_path / "o-s2.jsonl")["path"]) if r.get("record") == "edge"]
    orig = [r for r in _lines(path) if r.get("record") == "redaction"]
    assert orig and all(orig[0].get(k) != v for k, v in change.items()), "the change must actually differ from the source"
    recs = [dict(r, **change) if r.get("record") == "redaction" else r for r in _lines(path)] + extra
    return _write(tmp_path / "contradicting-s2.jsonl", recs)


def _snap(st):
    return [st._conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("edges", "redactions")]


def test_S2_1_a_remapping_import_with_a_contradictory_body_is_refused_atomically(tmp_path):
    """Research's stage-2 finding: the bound id carries the post-remap target, which a remapping import mints afresh, so
    the body comparison found no held row. It now compares on the SOURCE identity."""
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path, user_id="v1")
    bad = _contradicting_copy(tmp_path, path, reason="subject_request")
    before = _snap(dst.store)
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, bad, user_id="v1")
    assert _snap(dst.store) == before                                   # the new record in that file stays absent


def test_S2_1_the_same_contradiction_across_two_destination_users_is_refused(tmp_path):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path, user_id="v1")
    bad = _contradicting_copy(tmp_path, path, reason="subject_request")
    before = _snap(dst.store)
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, bad, user_id="v2")
    assert _snap(dst.store) == before


def test_S2_1_control_remapping_twice_with_an_equal_body_is_not_refused(tmp_path):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path, user_id="v1")
    second = import_memory(dst.store, path, user_id="v1")              # a fresh minted target, the SAME body
    assert second["notices_applied"] == 1
    import_memory(dst.store, path, user_id="v2")                        # and another destination user, same body


@pytest.mark.parametrize("restore", [False, True])
def test_S2_1_control_the_non_remapping_paths_still_refuse(tmp_path, restore):
    _s, _r, path = _source(tmp_path)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, path, restore=restore)
    bad = _contradicting_copy(tmp_path, path, reason="subject_request")
    before = _snap(dst.store)
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, bad, restore=restore)
    assert _snap(dst.store) == before
