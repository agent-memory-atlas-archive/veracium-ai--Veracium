"""specs/0014 Slice D — consolidation_output_index + FORMAT v5 portability.

The named tests from §2c/§4c/§7a: store assignment + generic-path refusal +
contiguity; the exclude-none serializer exception with round-trips (older
importer refuses v5; v4 stays accepted; explicit null rejects; v4→v5→v5 is
lossless); duplicate present indices reject within one import AND against
destination state over the tenant-scoped origin-namespaced key; a
source-identical indexed output re-imports idempotently; the two-set projection
with its sets-are-exact, totality, and two-sided mutation oracles; and the
FROZEN repeated-import fixture (1 edge + 1 ordinary episode + 1 indexed output
per file → 2 edges, 2 ordinary + 1 indexed = 3 EPISODES TOTAL).
"""
import json
import uuid
from datetime import datetime, timezone

import pytest

from veracium import portability as P
from veracium.schema import to_historical_id as _thi
from veracium.schema import (ConsolidationOutputDraft, ConsolidationState, Edge, Episode, EvidenceAuthor, Provenance)
from veracium.store.sqlite import SqliteStore

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _prov(ref="ev-1", source_id=None):
    return Provenance(author_of_evidence=EvidenceAuthor.USER,
                      evidence_ref=ref, observed_at=NOW, confidence=0.9,
                      source_id=source_id)


def _store(tmp_path, name="s.db"):
    return SqliteStore(str(tmp_path / name))


def _seed_with_indexed_output(store, uid="u1"):
    """1 edge + 1 ordinary episode + 1 indexed consolidation output — the
    FROZEN fixture file shape (R12-2)."""
    store.add_edge(Edge(id="e-1", user_id=uid, subject="user", relation="pet",
                           object="Miso", valid_from=NOW, provenance=_prov()))
    store.add_episode(Episode(id="ep-plain", user_id=uid, date="2026-07-01",
                              summary="an ordinary day", provenance=_prov()))
    for i in range(2):
        store.add_episode(Episode(id=f"ep-in-{i}", user_id=uid,
                                  date=f"2026-06-0{i+1}",
                                  summary=f"input {i}", provenance=_prov()))
    op = store.create_or_takeover_consolidation(uid, ["ep-in-0", "ep-in-1"],
                                                "w1", 60)
    assert store.transition_consolidation_if_current(
        op.operation_id, op.fence, "w1", ConsolidationState.GENERATING)
    assert store.write_consolidation_output_if_current(
        op.operation_id, op.fence, "w1",
        ConsolidationOutputDraft(summary="june, consolidated",
                                 date_start="2026-06-01", date_end="2026-06-02"))
    assert store.transition_consolidation_if_current(
        op.operation_id, op.fence, "w1", ConsolidationState.OUTPUTS_DURABLE)
    assert store.delete_claimed_inputs_if_current(op.operation_id, op.fence)
    assert store.transition_consolidation_if_current(
        op.operation_id, op.fence, "w1", ConsolidationState.FINALIZED)
    outs = [ep for ep in store.episodes(uid) if ep.lineage]
    assert len(outs) == 1 and outs[0].consolidation_output_index == 0
    return outs[0]


# -- assignment + refusal + contiguity ---------------------------------------

def test_the_primitive_assigns_sequential_indices(tmp_path):
    store = _store(tmp_path)
    out = _seed_with_indexed_output(store)
    assert out.consolidation_output_index == 0


def test_generic_add_episode_refuses_a_caller_supplied_index(tmp_path):
    """§2c: a host submitting a plain episode with index 0 → refused at the
    generic path (the fabrication case, named)."""
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.add_episode(Episode(id="ep-forged", user_id="u1",
                                  date="2026-07-01", summary="forged",
                                  consolidation_output_index=0,
                                  provenance=_prov()))


# -- serialization + round-trips ----------------------------------------------

def test_export_omits_none_and_carries_present_indices(tmp_path):
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    lines = [json.loads(l) for l in path.read_text().splitlines()]
    assert lines[0]["version"] == 9           # specs/0001 bumped 8->9 (0025: 7->8; 0016 D2: 6->7)
    eps = [l for l in lines if l.get("record") == "episode"]
    plain = [l for l in eps if not l.get("lineage")]
    outs = [l for l in eps if l.get("lineage")]
    assert all("consolidation_output_index" not in l for l in plain)  # omitted
    assert all(l.get("consolidation_output_index") == 0 for l in outs)


def test_an_older_importer_refuses_a_v5_export(tmp_path):
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    lines = path.read_text().splitlines()
    header = json.loads(lines[0])
    assert header["version"] == 9 > 4          # an importer with FORMAT<=5 refuses
    dest = _store(tmp_path, "d.db")
    bad = tmp_path / "newer.jsonl"
    # DERIVED, not pinned: this number's job is to be one greater than
    # whatever head is, and as a literal it silently became EQUAL to head
    # when 0001 bumped FORMAT to 9 — the test would then have asserted
    # that importing a current-version file is refused as "newer".
    header["version"] = P.FORMAT_VERSION + 1     # simulate a NEWER-than-us file
    bad.write_text("\n".join([json.dumps(header)] + lines[1:]) + "\n")
    with pytest.raises(ValueError, match="newer"):
        P.import_memory(dest, bad)


def test_v5_round_trip_is_lossless_and_v4_stays_accepted(tmp_path):
    """R7-3: absent stays absent, present stays present; a v4 file (no field)
    imports as the legacy shape."""
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    dest = _store(tmp_path, "d.db")
    P.import_memory(dest, path)
    outs = [ep for ep in dest.episodes("u1") if ep.lineage]
    assert outs[0].consolidation_output_index == 0            # present → present
    plains = [ep for ep in dest.episodes("u1") if not ep.lineage]
    assert all(ep.consolidation_output_index is None for ep in plains)
    # second hop: d -> d2 (v5→v5)
    path2 = tmp_path / "y.jsonl"
    P.export_memory(dest, "u1", path2)
    dest2 = _store(tmp_path, "d2.db")
    P.import_memory(dest2, path2)
    outs2 = [ep for ep in dest2.episodes("u1") if ep.lineage]
    assert outs2[0].consolidation_output_index == 0


def test_a_v5_output_without_an_index_is_the_legacy_shape(tmp_path):
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    lines = [json.loads(l) for l in path.read_text().splitlines()]
    for l in lines:
        l.pop("consolidation_output_index", None)             # strip the index
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    dest = _store(tmp_path, "d.db")
    P.import_memory(dest, legacy)                             # accepted
    outs = [ep for ep in dest.episodes("u1") if ep.lineage]
    assert outs[0].consolidation_output_index is None         # less identity


def test_an_explicit_null_index_is_malformed(tmp_path):
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    lines = [json.loads(l) for l in path.read_text().splitlines()]
    for l in lines:
        if l.get("lineage"):
            l["consolidation_output_index"] = None            # explicit null
    bad = tmp_path / "null.jsonl"
    bad.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    with pytest.raises(ValueError, match="explicit null"):
        P.import_memory(_store(tmp_path, "d.db"), bad)


def test_type_gates_reject_bool_string_negative(tmp_path):
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    for value in (True, "0", -1):
        lines = [json.loads(l) for l in path.read_text().splitlines()]
        for l in lines:
            if l.get("lineage"):
                l["consolidation_output_index"] = value
        bad = tmp_path / "typed.jsonl"
        bad.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
        with pytest.raises(ValueError, match="non-negative integer"):
            P.import_memory(_store(tmp_path, f"d-{value}.db"), bad)


def test_an_index_on_a_plain_episode_is_fabricated_identity(tmp_path):
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    lines = [json.loads(l) for l in path.read_text().splitlines()]
    for l in lines:
        if l.get("record") == "episode" and not l.get("lineage"):
            l["consolidation_output_index"] = 0
    bad = tmp_path / "fab.jsonl"
    bad.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    with pytest.raises(ValueError, match="no lineage"):
        P.import_memory(_store(tmp_path, "d.db"), bad)


# -- uniqueness: within-file, destination-state, idempotent re-import ---------

def test_duplicate_output_index_within_an_imported_operation_is_rejected(tmp_path):
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    lines = path.read_text().splitlines()
    out_line = next(l for l in lines if json.loads(l).get("lineage"))
    dup = json.loads(out_line)
    dup["id"] = "ep-duplicate-claim"                          # different record,
    bad = tmp_path / "dup.jsonl"                              # same (op, index)
    bad.write_text("\n".join(lines + [json.dumps(dup)]) + "\n")
    with pytest.raises(ValueError, match="never duplicates"):
        P.import_memory(_store(tmp_path, "d.db"), bad)


def test_duplicate_output_index_across_sequential_imports_is_rejected(tmp_path):
    """R9-5/R12-3: import A at (op,0); then a DIFFERENT output B claiming the
    same key from a second file → the second import rejects."""
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    dest = _store(tmp_path, "d.db")
    P.import_memory(dest, path)                               # A lands
    lines = [json.loads(l) for l in path.read_text().splitlines()]
    for l in lines:
        if l.get("lineage"):
            l["summary"] = "a DIFFERENT consolidation entirely"
    b = tmp_path / "b.jsonl"
    b.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    with pytest.raises(ValueError, match="DIFFERENT source-identity"):
        P.import_memory(dest, b)


def test_repeated_remapped_import_resolves_the_indexed_output_idempotently(tmp_path):
    """R11-2/R12-2, the FROZEN fixture: the SAME file imported twice with
    user_id= — ordinary records follow the shipped remap-copy semantics while
    the indexed output claims no second identity. After TWO imports: 2 edges,
    2 ordinary episodes, 1 indexed output = 3 EPISODES TOTAL (total AND split
    asserted)."""
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    dest = _store(tmp_path, "d.db")
    P.import_memory(dest, path, user_id="target")
    P.import_memory(dest, path, user_id="target")             # the re-import
    edges = dest.edges("target", active_only=False, include_quarantined=True)
    eps = dest.episodes("target")
    ordinary = [e for e in eps if not e.lineage]
    indexed = [e for e in eps if e.lineage]
    assert len(edges) == 2                                    # remap-copy
    assert len(ordinary) == 2                                 # remap-copy
    assert len(indexed) == 1                                  # ONE identity
    assert len(eps) == 3                                      # the total
    assert indexed[0].consolidation_output_index == 0


# -- the projection's oracles -------------------------------------------------

def test_source_identity_projection_sets_are_exact():
    """R12-3: independent membership assertions for both sets."""
    assert P.PROJECTION_EXCLUDED_FIELDS == ("id", "user_id")
    assert set(P.PROJECTION_VERBATIM_FIELDS) == (
        set(Episode.model_fields) - {"id", "user_id"})


def test_source_identity_projection_is_total():
    """R11-3: the two sets partition Episode.model_fields — a future field
    breaks this until classified."""
    both = set(P.PROJECTION_EXCLUDED_FIELDS) | set(P.PROJECTION_VERBATIM_FIELDS)
    assert both == set(Episode.model_fields)
    assert not (set(P.PROJECTION_EXCLUDED_FIELDS)
                & set(P.PROJECTION_VERBATIM_FIELDS))


def test_every_projection_field_binds_source_identity(tmp_path):
    """R11-3/R13-2, two-sided: mutate any VERBATIM field in the second file →
    REJECT (including a lineage member id — a different historical episode);
    mutate an EXCLUDED field → idempotent (the destination-minted identity has
    no source meaning)."""
    store = _store(tmp_path)
    _seed_with_indexed_output(store)
    path = tmp_path / "x.jsonl"
    P.export_memory(store, "u1", path)
    dest = _store(tmp_path, "d.db")
    P.import_memory(dest, path)

    def _mutated_file(mutate):
        lines = [json.loads(l) for l in path.read_text().splitlines()]
        for l in lines:
            if l.get("lineage"):
                mutate(l)
        f = tmp_path / f"m-{uuid.uuid4().hex[:6]}.jsonl"
        f.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
        return f

    # VERBATIM mutations → reject
    for mutate in (
        lambda l: l.__setitem__("summary", "tampered"),
        lambda l: l.__setitem__("date", "1999-01-01"),
        lambda l: l["lineage"].__setitem__(0, _thi("DIFFERENT-EPISODE")),
        lambda l: l["provenance"].__setitem__("confidence", 0.01),
    ):
        with pytest.raises(ValueError, match="DIFFERENT source-identity"):
            P.import_memory(dest, _mutated_file(mutate))
    # EXCLUDED mutation → idempotent (skipped, not duplicated, not rejected)
    before = len(dest.episodes("u1"))
    P.import_memory(dest, _mutated_file(lambda l: l.__setitem__("id", "ep-renamed")))
    assert len(dest.episodes("u1")) == before


# -- the 0041 rider's paired oracle cells (0041 round 13; 0014 §2c as amended) -------------------------------------
# The rider admits EXACTLY ONE class of verbatim difference on a colliding indexed output: a redaction of the HELD
# output. Each cell starts from a REAL redaction (a consolidation through the lifecycle, `Memory.redact`, export) and
# mutates the redacted file once; `test_every_projection_field_binds_source_identity` above stays the general oracle.

def _rider_memory(tmp_path, name):
    from veracium import Memory
    from veracium.config import MemoryConfig
    return Memory(llm=lambda *a, **k: "{}", config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                                                              scope_groups={}, require_source_id=False))


def _rider_files(tmp_path):
    """(before, after) exports of one consolidation output: `after` carries its redaction and the notice."""
    from veracium.lifecycle import consolidate
    src = _rider_memory(tmp_path, "rider-src.db")
    for i in range(8):
        src.store.add_episode(Episode(id=f"ep-{i}", user_id="u", date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                      provenance=_prov(ref=f"ev-{i}", source_id="src-one")))
    consolidate(src.store, lambda p, system=None, role=None: json.dumps(
        {"records": [{"date": "2026-01-01", "summary": "the week RIDER-SECRET"}]}), "u", src.config,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    (out,) = [e for e in src.store.episodes("u") if e.lineage]
    before, after = tmp_path / "rider-before.jsonl", tmp_path / "rider-after.jsonl"
    P.export_memory(src.store, "u", before)
    src.redact("u", episode_id=out.id, reason="subject_request")
    P.export_memory(src.store, "u", after)
    return before, after


def _rider_held(tmp_path, before):
    dst = _rider_memory(tmp_path, f"rider-dst-{uuid.uuid4().hex[:6]}.db")
    P.import_memory(dst.store, before)
    return dst


def _rider_edit(path, tmp_path, *, output=None, drop_notice=False):
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    if drop_notice:
        recs = [r for r in recs if r.get("record") != "redaction"]
    for r in recs:
        if r.get("lineage") and output:
            output(r)
    f = tmp_path / f"rider-{uuid.uuid4().hex[:6]}.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return f


def test_rider_a_named_field_at_the_marker_WITH_the_notice_resolves_and_treats_the_held_output(tmp_path):
    before, after = _rider_files(tmp_path)
    dst = _rider_held(tmp_path, before)
    (held,) = [e for e in dst.store.episodes("u") if e.lineage]
    P.import_memory(dst.store, after)
    (now,) = [e for e in dst.store.episodes("u") if e.lineage]
    assert now.id == held.id and "RIDER-SECRET" not in now.summary


def test_rider_the_same_difference_WITHOUT_the_notice_rejects(tmp_path):
    before, after = _rider_files(tmp_path)
    dst = _rider_held(tmp_path, before)
    with pytest.raises(ValueError, match="DIFFERENT source-identity"):
        P.import_memory(dst.store, _rider_edit(after, tmp_path, drop_notice=True))


def test_rider_a_field_the_notice_does_NOT_name_rejects(tmp_path):
    before, after = _rider_files(tmp_path)
    dst = _rider_held(tmp_path, before)
    with pytest.raises(ValueError, match="DIFFERENT source-identity"):
        P.import_memory(dst.store, _rider_edit(after, tmp_path, output=lambda r: r.__setitem__("date", "1999-01-01")))


def test_rider_a_named_field_at_a_NON_marker_value_rejects(tmp_path):
    before, after = _rider_files(tmp_path)
    dst = _rider_held(tmp_path, before)
    with pytest.raises(ValueError, match="DIFFERENT source-identity"):
        P.import_memory(dst.store, _rider_edit(after, tmp_path, output=lambda r: r.__setitem__("summary", "tampered")))


def test_rider_a_lineage_difference_rejects_notice_or_not(tmp_path):
    before, after = _rider_files(tmp_path)
    for drop in (False, True):
        dst = _rider_held(tmp_path, before)
        with pytest.raises(ValueError, match="DIFFERENT source-identity"):
            P.import_memory(dst.store, _rider_edit(after, tmp_path, drop_notice=drop,
                                                   output=lambda r: r["lineage"].__setitem__(0, _thi("DIFFERENT-EPISODE"))))


def test_rider_a_treated_held_output_meeting_its_untreated_arrival_with_the_notice_is_existing(tmp_path):
    before, after = _rider_files(tmp_path)
    dst = _rider_memory(tmp_path, "rider-treated.db")
    P.import_memory(dst.store, after)                             # the destination holds the TREATED output, attested
    held = [json.loads(e.model_dump_json()) for e in dst.store.episodes("u") if e.lineage]
    rows = dst.store._conn.execute("SELECT * FROM redactions").fetchall()
    # the REDACTED export (format 13, its notice) with the output record swapped for the UNTREATED one — the "before"
    # file alone declares the pre-redaction format and could not carry a notice
    untreated = next(l for l in before.read_text().splitlines() if l.strip() and json.loads(l).get("lineage"))
    lines = [untreated if (l.strip() and json.loads(l).get("lineage")) else l for l in after.read_text().splitlines()]
    f = tmp_path / "rider-untreated-with-notice.jsonl"
    f.write_text("\n".join(lines) + "\n")
    P.import_memory(dst.store, f)                                 # the UNTREATED arrival, with the notice
    assert [json.loads(e.model_dump_json()) for e in dst.store.episodes("u") if e.lineage] == held
    assert dst.store._conn.execute("SELECT * FROM redactions").fetchall() == rows
