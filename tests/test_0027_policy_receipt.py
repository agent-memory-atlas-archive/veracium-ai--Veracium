"""specs/0027 v13 §4c — the POLICY RECEIPT (research T1; the owner's word,
2026-09-13: "Do the A1 receipt").

A policy lane may reorder what is returned; the receipt is what makes that
admissible: it records the COUNTERFACTUAL — the selection the same inputs give
with the policy term removed — so `displaced` (baseline[:n] − adjusted[:n]) is
the event `recalled_edges` structurally cannot hold (it is filtered to
survivors, and on the non-semantic path it is empty). Two properties learned
from correction C1 are asserted here rather than assumed: the receipt is
written on the NON-SEMANTIC path too, and it exists only when the lane FIRED.
"""

import importlib.util
import os
import pathlib
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig, PolicyLane, PolicyReceipt
from veracium.graph import RRF_K, fused_subgraph, fused_subgraph_with_receipt


def _module(name):
    path = pathlib.Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name[:-3] + "_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = _module("test_0027_semantic_recall.py")
lane_tests = _module("test_0027_policy_lane.py")
U = base.U
_edge = base._edge
LANE = PolicyLane(policy_id="demo-language-relevant", policy_version="2026-09-13.1",
                  ranks={"p": 1}, tags_matched=("language-relevant",))


# ------------------------------------------------------------- at the seam ----
def test_the_receipt_records_the_counterfactual_displacement_and_admission():
    """R4-1's coverage fixture (test_0027_policy_lane): the promotion of `p`
    evicts the head's marginal record `r5` and nothing else. The receipt says
    exactly that — baseline and adjusted selections, displaced, admitted — and
    asserts the reserve was the same set either way (V-RESERVE-UNADJUSTED per
    call), the score delta the lane contributed, and that the budget truncated."""
    scored, relevant, by_id, max_edges = lane_tests._coverage_fixture()
    out, meta, r = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"p": 1})
    assert r is not None
    assert r["baseline_order"] == ["x00", "x01", "r1", "r2", "r3", "r4", "r5", "t"]
    assert r["adjusted_order"] == [e.id for e in out]
    assert r["displaced"] == ["r5"] and r["admitted"] == ["p"]
    assert r["reserve_unchanged"] is True
    assert r["reserved_baseline"] == r["reserved_adjusted"] == ["x00", "x01"]     # the evidence for the boolean, derivable
    assert r["budget_state"] == {"candidates": 10, "max_edges": 8, "truncated": True, "coverage_share": 0.25}
    assert set(r["delta_fused"]) == {"p"} and 0 < r["delta_fused"]["p"] <= 1.0 / (RRF_K + 1) + 1e-12   # the per-lane bound, to the ulp
    assert r["ranks_applied"] == {"p": 1}
    # the baseline IS the no-policy selection: the same construction, no second instrument
    base_out, _ = fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)
    assert r["baseline_order"] == [e.id for e in base_out]


def test_no_receipt_when_no_policy_and_none_when_the_lane_did_not_fire():
    """The receipt exists only for a recall in which a policy lane FIRED: a rank
    on an id the membership lanes do not hold contributes nothing (v11) and
    leaves no receipt — an inert policy is not an event."""
    scored, relevant, by_id, max_edges = lane_tests._coverage_fixture()
    _, _, r0 = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=max_edges)
    _, _, r1 = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=max_edges, policy_rank={"ghost": 1})
    assert r0 is None and r1 is None
    # and the plain entry point's shape is unchanged for every existing caller
    assert len(fused_subgraph(scored, relevant, by_id, [], max_edges=max_edges)) == 2


def test_below_the_budget_the_lane_fires_and_the_receipt_proves_nothing_could_move():
    """T5's structural fact, carried by the receipt: with fewer candidates than
    `max_edges` there is no truncation, so a firing lane reorders and displaces
    nothing — `budget_state.truncated` is False and both lists are empty."""
    scored, relevant, by_id, _ = lane_tests._coverage_fixture()
    out, _, r = fused_subgraph_with_receipt(scored, relevant, by_id, [], max_edges=40, policy_rank={"p": 1})
    assert r is not None and r["displaced"] == [] and r["admitted"] == []
    assert r["budget_state"] == {"candidates": 10, "max_edges": 40, "truncated": False, "coverage_share": 0.25}
    assert r["reserved_baseline"] == r["reserved_adjusted"] == []                 # no truncation, no reserve
    assert set(r["baseline_order"]) == set(r["adjusted_order"]) == {e.id for e in out}


# ------------------------------------------------------- through Memory.recall ----
def _memory(tmp_path, name, max_edges=8):
    mem = Memory(llm=lambda *a, **k: "",
                 config=MemoryConfig(db_path=str(tmp_path / name), max_subgraph_edges=max_edges,
                                     require_source_id=False))
    for i in range(12):
        mem.store.add_edge(_edge(f"x{i:02d}", "user", "likes", f"boat topic{i}", days=i))
    mem.store.add_edge(_edge("p", "user", "enjoys", "harbor walks", days=30))   # no query overlap: outside the reserve's set
    return mem


def test_the_receipt_is_written_on_the_non_semantic_path_and_carries_ids_only(tmp_path):
    """Correction C1: `recalled_edges` was written only on the semantic path and
    filtered to survivors, so the displaced record — the whole event — left
    nothing. With `semantic=False` and a policy, the fused construction runs
    (its degenerate identity IS the legacy projection, V10) and the receipt
    exists; the displaced id has no `recalled_edges` entry and is not among the
    returned edges, yet the receipt names it. Ids only: no field carries content."""
    mem = _memory(tmp_path, "r.db")
    r = mem.recall(U, "boat topic", semantic=False, policy=LANE)
    rc = r.policy_receipt
    assert isinstance(rc, PolicyReceipt)
    assert r.semantic_status == "disabled" and rc.semantic_status == "disabled"
    assert rc.policy_id == LANE.policy_id and rc.policy_version == LANE.policy_version
    assert rc.tags_matched == ("language-relevant",)
    assert rc.admitted == ["p"] and len(rc.displaced) == 1
    displaced = rc.displaced[0]
    assert displaced not in {e.id for e in r.edges}
    assert r.recalled_edges.get(displaced) is None            # the event recalled_edges cannot hold
    assert rc.adjusted_order == [e.id for e in r.edges]
    assert rc.reserve_unchanged is True and rc.budget_state["truncated"] is True
    assert rc.reserve_unchanged == (rc.reserved_baseline == rc.reserved_adjusted)   # declared == derived
    assert rc.budget_state["coverage_share"] == mem.config.subgraph_coverage_share
    assert rc.recorded_at and datetime.fromisoformat(rc.recorded_at.replace("Z", "+00:00")).tzinfo is not None
    assert isinstance(rc.recall_id, str) and len(rc.recall_id) == 32                # minted, opaque
    assert rc.recall_id != mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt.recall_id
    for field in (rc.baseline_order, rc.adjusted_order, rc.displaced, rc.admitted, rc.reserved_baseline, rc.reserved_adjusted,
                  list(rc.delta_fused), list(rc.ranks_applied)):
        for v in field:
            assert v in mem.store._conn.execute("SELECT id FROM edges").fetchall().__repr__()   # ids
            assert "boat" not in v and "harbor" not in v                                        # never content
    mem.close()


def test_no_policy_no_receipt_and_an_inert_policy_returns_the_legacy_selection(tmp_path):
    """Without a policy the legacy path runs and `policy_receipt` is None
    (V-COMPAT: a defaulted field). With an INERT policy (no rank on a held id)
    the fused construction runs with the semantic lane empty and returns the
    legacy selection edge for edge (V10's identity, now exercised through
    `recall`), and still no receipt — the lane did not fire."""
    mem = _memory(tmp_path, "r.db")
    plain = mem.recall(U, "boat topic", semantic=False)
    inert = mem.recall(U, "boat topic", semantic=False,
                       policy=PolicyLane(policy_id="demo", policy_version="1", ranks={"ghost": 1}))
    assert plain.policy_receipt is None and inert.policy_receipt is None
    assert [e.id for e in inert.edges] == [e.id for e in plain.edges]
    assert inert.context == plain.context
    mem.close()


def test_the_receipt_baseline_is_the_selection_the_same_call_gives_without_the_policy(tmp_path):
    """The counterfactual is not modelled, it is computed: the receipt's
    `baseline_order` equals what `recall` returns for the same query with no
    policy (the same construction, so the instrument and the mechanism cannot
    disagree — research's replay uses this field as its baseline)."""
    mem = _memory(tmp_path, "r.db")
    plain = mem.recall(U, "boat topic", semantic=False)
    with_policy = mem.recall(U, "boat topic", semantic=False, policy=LANE)
    assert with_policy.policy_receipt.baseline_order == [e.id for e in plain.edges]
    assert "p" in [e.id for e in with_policy.edges] and "p" not in [e.id for e in plain.edges]
    mem.close()


@pytest.mark.parametrize("bad, exc", [
    ("not-a-lane", TypeError),
    ({"p": 1}, TypeError),
])
def test_a_policy_that_is_not_a_policy_lane_is_refused(tmp_path, bad, exc):
    mem = _memory(tmp_path, "r.db")
    with pytest.raises(exc):
        mem.recall(U, "boat topic", policy=bad)
    mem.close()


def test_a_policy_is_not_combinable_with_as_of(tmp_path):
    """The as-of path (0028) has no receipt; a policy there would be the
    untraceable ranking change the receipt exists to prevent — refused."""
    mem = _memory(tmp_path, "r.db")
    with pytest.raises(ValueError, match="not combinable with as_of"):
        mem.recall(U, "boat topic", policy=LANE, as_of=datetime(2026, 1, 1, tzinfo=timezone.utc))
    mem.close()


@pytest.mark.parametrize("kwargs", [
    dict(policy_id="", policy_version="1", ranks={}),
    dict(policy_id="demo", policy_version=" ", ranks={}),
    dict(policy_id="demo", policy_version="1", ranks=[("p", 1)]),
])
def test_a_malformed_policy_lane_is_refused_at_construction(kwargs):
    with pytest.raises((ValueError, TypeError)):
        PolicyLane(**kwargs)


def test_a_malformed_rank_is_refused_before_anything_is_computed(tmp_path):
    """v11's rule, reached through recall: a rank that is not an int ≥ 1 is a
    programming error, refused rather than skipped."""
    mem = _memory(tmp_path, "r.db")
    with pytest.raises(ValueError, match="policy_rank"):
        mem.recall(U, "boat topic", semantic=False, policy=PolicyLane(policy_id="demo", policy_version="1", ranks={"p": 0}))
    mem.close()


# ------------------------------------------------------- v14: durability ----
# specs/0027 v14 §4g — the receipt is DURABLE: written to the `policy_receipt`
# table before `recall` returns, read back field-equal, erased with the user,
# absent from the export, and a failed write is LOUD (raises out of recall)
# rather than a silent gap — correction C1's class, now closed at the store.
import json
import sqlite3

from veracium import receipt_from_row, receipt_row
from veracium.store import schema_version as sv
from veracium.store.base import Store
from veracium.store.migration import migrate_store
from veracium.store.sqlite import SqliteStore


def test_the_receipt_is_durable_and_reads_back_field_equal(tmp_path):
    """V-RECEIPT-DURABLE: the receipt `recall` returned is the receipt the store
    reads back by `recall_id` — every field equal (dataclass equality), the
    row's text is the sorted-key JSON of the receipt and carries ids only."""
    mem = _memory(tmp_path, "d.db")
    rc = mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt
    assert isinstance(rc, PolicyReceipt)
    back = mem.policy_receipt(U, rc.recall_id)
    assert back == rc and back is not rc
    assert mem.policy_receipts(U) == [rc]
    row = mem.store.policy_receipt(U, rc.recall_id)
    assert row["receipt"] == json.dumps(json.loads(row["receipt"]), sort_keys=True, separators=(",", ":"))
    assert json.loads(row["receipt"])["tags_matched"] == ["language-relevant"]     # a JSON list, back as a tuple
    assert "boat" not in row["receipt"] and "harbor" not in row["receipt"]        # ids only, at rest
    assert row["policy_id"] == LANE.policy_id and row["recorded_at"] == rc.recorded_at
    assert mem.policy_receipt(U, "no-such-id") is None
    mem.close()


def test_receipts_list_newest_first_with_a_limit_and_survive_reopening(tmp_path):
    mem = _memory(tmp_path, "l.db")
    ids = [mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt.recall_id
           for _ in range(3)]
    listed = mem.policy_receipts(U)
    assert [r.recall_id for r in listed] == sorted(ids, key=lambda i: (next(r.recorded_at for r in listed if r.recall_id == i), i), reverse=True)
    assert len(mem.policy_receipts(U, limit=2)) == 2 and mem.policy_receipts(U, limit=2) == listed[:2]
    with pytest.raises(ValueError):
        mem.store.policy_receipts(U, limit=0)
    assert mem.policy_receipts("someone-else") == []
    mem.close()
    again = Memory(llm=lambda *a, **k: "",
                   config=MemoryConfig(db_path=str(tmp_path / "l.db"), require_source_id=False))
    assert [r.recall_id for r in again.policy_receipts(U)] == [r.recall_id for r in listed]   # durable across open/close
    again.close()


def test_no_firing_writes_no_row(tmp_path):
    """An inert policy or no policy is not an event: no receipt, no row (V-RECEIPT-ON-FIRING at the store)."""
    mem = _memory(tmp_path, "n.db")
    inert = PolicyLane(policy_id="inert", policy_version="1", ranks={"absent-id": 1}, tags_matched=())
    assert mem.recall(U, "boat topic", semantic=False).policy_receipt is None
    assert mem.recall(U, "boat topic", semantic=False, policy=inert).policy_receipt is None
    assert mem.policy_receipts(U) == []
    assert mem.store._conn.execute("SELECT COUNT(*) FROM policy_receipt").fetchone()[0] == 0
    mem.close()


def test_a_failed_receipt_write_raises_out_of_recall(tmp_path, monkeypatch):
    """V-RECEIPT-DURABLE-OR-LOUD: a recall whose receipt could not be written does
    not return as if it had been recorded; a recall without a policy is untouched."""
    mem = _memory(tmp_path, "f.db")

    def boom(user_id, row):
        raise sqlite3.OperationalError("database is locked (injected)")
    monkeypatch.setattr(mem.store, "write_policy_receipt", boom)
    with pytest.raises(sqlite3.OperationalError, match="injected"):
        mem.recall(U, "boat topic", semantic=False, policy=LANE)
    assert mem.recall(U, "boat topic", semantic=False).policy_receipt is None       # no policy: no write, no raise
    assert mem.policy_receipts(U) == []
    mem.close()


def test_a_store_without_receipt_support_refuses_the_first_firing_recall(tmp_path):
    """A host store that predates v14: the base class REFUSES rather than drops,
    so the first recall on which a lane fires raises, and a non-firing recall works."""
    class _NoReceipts(SqliteStore):
        write_policy_receipt = Store.write_policy_receipt
        policy_receipts = Store.policy_receipts
        policy_receipt = Store.policy_receipt

    store = _NoReceipts(str(tmp_path / "h.db"))
    mem = Memory(llm=lambda *a, **k: "", store=store,
                 config=MemoryConfig(db_path=str(tmp_path / "h.db"), max_subgraph_edges=8,
                                     require_source_id=False))
    for i in range(12):
        mem.store.add_edge(_edge(f"x{i:02d}", "user", "likes", f"boat topic{i}", days=i))
    mem.store.add_edge(_edge("p", "user", "enjoys", "harbor walks", days=30))
    assert mem.recall(U, "boat topic", semantic=False).policy_receipt is None
    with pytest.raises(NotImplementedError, match="write_policy_receipt"):
        mem.recall(U, "boat topic", semantic=False, policy=LANE)
    with pytest.raises(NotImplementedError):
        mem.policy_receipts(U)
    mem.close()


def test_a_receipt_row_is_written_once_and_a_foreign_row_is_refused(tmp_path):
    mem = _memory(tmp_path, "o.db")
    rc = mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt
    with pytest.raises(sqlite3.IntegrityError):                               # written once, never replaced
        mem.store.write_policy_receipt(U, receipt_row(rc))
    with pytest.raises(ValueError, match="lacks"):
        mem.store.write_policy_receipt(U, {"recall_id": "x"})
    row = receipt_row(rc)
    with pytest.raises(ValueError, match="fields"):
        receipt_from_row({**row, "receipt": json.dumps({"recall_id": rc.recall_id})})
    with pytest.raises(ValueError, match="disagrees"):
        receipt_from_row({**row, "policy_id": "another"})
    assert receipt_from_row(row) == rc
    mem.close()


def test_forget_user_erases_the_users_receipts_and_no_others(tmp_path):
    """V-RECEIPT-ERASE: the receipt is per-user erasable data, gone with the
    user's rows in the same statement set; another user's receipts stay."""
    mem = _memory(tmp_path, "e.db")
    mine = mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt
    other = "other-user"
    for i in range(12):
        mem.store.add_edge(_edge(f"o{i:02d}", "user", "likes", f"boat topic{i}", days=i).model_copy(update={"user_id": other}))
    mem.store.add_edge(_edge("p", "user", "enjoys", "harbor walks", days=30).model_copy(update={"id": "op", "user_id": other}))
    theirs = mem.recall(other, "boat topic", semantic=False,
                        policy=PolicyLane(policy_id=LANE.policy_id, policy_version=LANE.policy_version,
                                          ranks={"op": 1}, tags_matched=LANE.tags_matched)).policy_receipt
    assert theirs is not None and mine is not None
    mem.forget(U)
    assert mem.policy_receipts(U) == [] and mem.policy_receipt(U, mine.recall_id) is None
    assert [r.recall_id for r in mem.policy_receipts(other)] == [theirs.recall_id]
    assert mem.store._conn.execute("SELECT COUNT(*) FROM policy_receipt WHERE user_id=?", (U,)).fetchone()[0] == 0
    assert "policy_receipt" in __import__("veracium.store.sqlite", fromlist=["_ERASE_TABLES"])._ERASE_TABLES
    mem.close()


def test_receipts_are_not_exported_and_an_import_carries_none(tmp_path):
    """The receipt is deployment audit, not memory: `export_memory` writes no
    receipt (no field of it appears in the file) and a store built from the
    export holds none."""
    mem = _memory(tmp_path, "x.db")
    rc = mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt
    out = tmp_path / "export.jsonl"
    mem.export_memory(U, out)
    text = out.read_text()
    assert rc.recall_id not in text and "policy_receipt" not in text and "baseline_order" not in text
    dest = Memory(llm=lambda *a, **k: "",
                  config=MemoryConfig(db_path=str(tmp_path / "y.db"), require_source_id=False))
    dest.import_memory(out, user_id=U)
    assert dest.policy_receipts(U) == []
    assert dest.store._conn.execute("SELECT COUNT(*) FROM policy_receipt").fetchone()[0] == 0
    dest.close()
    mem.close()


def test_schema_14_declares_the_receipt_table_required_and_its_index_rebuildable(tmp_path):
    objs = {o.name: o for o in sv.SCHEMAS[14]}
    assert objs["policy_receipt"].policy == sv.REQUIRED
    assert objs["ix_policy_receipt_time"].policy == sv.REBUILDABLE
    assert {o.key for o in sv.SCHEMAS[14]} - {o.key for o in sv.SCHEMAS[13]} == {
        ("table", "policy_receipt"), ("index", "ix_policy_receipt_time")}
    assert sv.SCHEMA_VERSION == 14
    mem = _memory(tmp_path, "s.db")
    assert mem.store._conn.execute("PRAGMA user_version").fetchone()[0] == 14
    cols = [r[1] for r in mem.store._conn.execute("PRAGMA table_info(policy_receipt)")]
    assert cols == ["user_id", "recall_id", "policy_id", "policy_version", "recorded_at", "receipt"]
    mem.close()


def test_a_v13_store_migrates_to_v14_with_its_rows_intact(tmp_path):
    """The v13→v14 cross is DDL only: the table and index appear, the edges and
    the journal are untouched (no second baseline), the stamp moves to 14."""
    src = _memory(tmp_path, "src.db")                       # a v14 store with real rows
    n_edges = len(src.store.edges(U, active_only=False, include_quarantined=True))
    src.close()
    old = str(tmp_path / "old13.db")
    c = sqlite3.connect(old)
    c.execute("BEGIN")
    sv.create(c, 13)
    c.execute(f"ATTACH DATABASE '{tmp_path / 'src.db'}' AS v14")
    c.execute("INSERT INTO edges SELECT * FROM v14.edges")
    c.execute("INSERT INTO edge_event SELECT * FROM v14.edge_event")
    c.execute("PRAGMA user_version = 13")
    c.commit()
    n_events = c.execute("SELECT COUNT(*) FROM edge_event").fetchone()[0]
    assert c.execute("PRAGMA user_version").fetchone()[0] == 13
    assert not c.execute("SELECT name FROM sqlite_master WHERE name='policy_receipt'").fetchall()
    c.close()
    result = migrate_store(old)
    assert result == "migrated" and result.resulting_version == 14 and result.transaction_committed, result
    c = sqlite3.connect(old)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 14
    assert c.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == n_edges
    assert c.execute("SELECT COUNT(*) FROM edge_event").fetchone()[0] == n_events    # no re-baseline
    assert c.execute("SELECT COUNT(*) FROM policy_receipt").fetchone()[0] == 0
    c.close()
    reopened = Memory(llm=lambda *a, **k: "",
                      config=MemoryConfig(db_path=old, max_subgraph_edges=8, require_source_id=False))
    rc = reopened.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt
    assert rc is not None and reopened.policy_receipt(U, rc.recall_id) == rc
    reopened.close()


def test_a_removed_receipt_table_refuses_to_open_the_store(tmp_path):
    """Research's round of behavioural verification (2026-09-14), a result
    stronger than the write's loudness: the table is REQUIRED in the shape
    manifest, so a store whose `policy_receipt` table was dropped to silence
    receipts does not reach `recall` at all — it refuses to OPEN as a
    stamped-shape mismatch naming the missing objects. The write's raise is
    the propagation path for a failure INSIDE an intact store; this is the
    guarantee for a store made incomplete."""
    from veracium.store.schema_version import StoreVersionError
    path = str(tmp_path / "dropped.db")
    mem = _memory(tmp_path, "dropped.db")
    assert mem.recall(U, "boat topic", semantic=False, policy=LANE).policy_receipt is not None
    mem.close()
    c = sqlite3.connect(path)
    c.execute("DROP TABLE policy_receipt")                                      # the index goes with it
    c.commit(); c.close()
    with pytest.raises(StoreVersionError) as e:
        SqliteStore(path)
    assert e.value.reason == "stamped-shape-mismatch"
    assert "table:policy_receipt" in str(e.value) and "ix_policy_receipt_time" in str(e.value)
    with pytest.raises(StoreVersionError):                                        # through Memory too
        Memory(llm=lambda *a, **k: "", config=MemoryConfig(db_path=path, require_source_id=False))


# ---------------------------------------------- v14.1: bounded identifiers ----
@pytest.mark.parametrize("field, value, why", [
    ("policy_id", "a whole sentence, with spaces and punctuation.", "spaces and punctuation"),
    ("policy_id", "x" * 65, "65 characters"),
    ("policy_id", "", "empty"),
    ("policy_id", True, "a bool"),
    ("policy_version", "diagnosis: hiv-positive, disclosed here", "spaces"),
    ("policy_version", 3, "not a string"),
    ("tags_matched", ("ok", "x" * 400), "a 400-character tag"),
    ("tags_matched", ("ok", ""), "an empty tag"),
    ("tags_matched", ("ok", "has space"), "whitespace in a tag"),
    ("tags_matched", ("ok", 7), "a non-string tag"),
    ("tags_matched", ("ok", True), "a bool tag"),
    ("tags_matched", tuple(f"t{i}" for i in range(65)), "65 tags"),
    ("tags_matched", "not-a-tuple", "a bare string"),
])
def test_policy_identity_strings_are_bounded_to_identifier_shape_and_the_limit_is_stated(field, value, why):
    """specs/0027 v14.1 (research's pre-adoption read of 0040): the policy's
    identity strings are persisted VERBATIM in the receipt row, so they are
    bounded to identifier shape at construction — before any recall — and a
    sentence, whitespace, an over-long or empty value, a bool, a non-string or
    too many tags are refused. The stated LIMIT is asserted below, not hidden:
    an identifier-shaped disclosure passes every rule and is persisted."""
    from veracium import PolicyLane
    kwargs = dict(policy_id="demo", policy_version="1", ranks={"p": 1}, tags_matched=("ok",))
    kwargs[field] = value
    with pytest.raises((ValueError, TypeError)):
        PolicyLane(**kwargs)


def test_an_identifier_shaped_disclosure_is_accepted_and_persisted_the_stated_limit(tmp_path):
    from veracium import PolicyLane
    lane = PolicyLane(policy_id="diagnosis:hiv-positive", policy_version="2026-09-14.1",
                      ranks={"p": 1}, tags_matched=["diagnosis:hiv-positive", "a" * 64])  # a list is taken as a tuple
    assert lane.tags_matched == ("diagnosis:hiv-positive", "a" * 64)
    mem = _memory(tmp_path, "lim.db")
    rc = mem.recall(U, "boat topic", semantic=False, policy=lane).policy_receipt
    row = mem.store.policy_receipt(U, rc.recall_id)
    assert "diagnosis:hiv-positive" in row["receipt"] and row["policy_id"] == "diagnosis:hiv-positive"   # bounded, not content-free
    mem.close()
