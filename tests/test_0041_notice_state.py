"""specs/0041 §11.6.6 (T4; amendment `0047/0041-replies`, INV-RR10–RR12, RR14): the NOTICE STATE machine that replaces
the 2026-10-13 notice-binding hotfix. A redaction row is `applied` (an attestation), `pending` (a witnessed notice over a
record this store holds, awaiting the user's `confirm_notice`) or `standing` (a witnessed notice whose record this
store does not hold). Only `applied` attests. An import weighs every notice by its TARGET's state, the file's copy and
the mode — never by its origin (the owner's ruling) — and a default import never changes a held byte through a notice.

PRODUCT tests through the real `Memory.import_memory` / `export_memory` / `redact` / `confirm_notice`, and the real
migration. Research's stage-1 read of T4: B1 (export carries no pending notice, and a standing one only when its target
is not in the file), B2 (attestation readers count applied only; coverage readers every state), B3 (a standing notice
over a record since written locally is weighed like any held target), and the Q3 additions.
"""
from __future__ import annotations

import contextlib
import json
import pathlib
import sqlite3

import pytest

from veracium import Memory, MemoryConfig, portability as port
from veracium import redaction as R
from veracium.schema import Confirmation, Disclosure, Edge, Episode, EvidenceAuthor, Provenance  # noqa: F401
from veracium.store import migration as M
from veracium.store import schema_version as sv
from veracium.store.migration import MigrationPostconditionError, migrate_store

U = "u"


def _quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def _mem(tmp_path, name):
    return Memory(llm=_quiet, config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                                                  scope_groups={}, require_source_id=False))


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)


def _edge(eid, obj):
    return Edge(id=eid, user_id=U, subject="user", relation="likes", object=obj, provenance=_prov())


def _lines(p):
    return [json.loads(x) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def _write(p, lines):
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return p


def _source(tmp_path, name, eid="e-x", obj="Berlin SECRET"):
    """A source store that holds `eid`, redacts its OWN row and exports: (the full file, its notice-only cut, the
    source's export of the record UNREDACTED beside the notice — the poisoned pair)."""
    a = _mem(tmp_path, f"{name}.db")
    a.store.add_edge(_edge(eid, obj))
    plain = tmp_path / f"{name}-plain.jsonl"
    port.export_memory(a.store, U, plain)
    a.redact(U, edge_id=eid, reason="subject_request")
    full = tmp_path / f"{name}.jsonl"
    port.export_memory(a.store, U, full)
    a.close()
    lines = _lines(full)
    notice = [x for x in lines[1:] if x.get("record") == "redaction"]
    notices = _write(tmp_path / f"{name}-notices.jsonl", [lines[0], *notice])
    pl = _lines(plain)
    poisoned = _write(tmp_path / f"{name}-poisoned.jsonl", [lines[0], *[x for x in pl[1:]], *notice])
    return full, notices, poisoned


def _rows(m):
    return m.store._conn.execute("SELECT target_id, state, pending_reason FROM redactions ORDER BY target_id").fetchall()


def _json(m, eid):
    r = m.store._conn.execute("SELECT json FROM edges WHERE id=?", (eid,)).fetchone()
    return None if r is None else r[0]


@contextlib.contextmanager
def _permitted(what):
    """A permission asserted as such: a DOMAIN refusal (`refused: …`) of it fails as an assertion naming it."""
    try:
        yield
    except ValueError as x:
        if not str(x).startswith("refused:"):
            raise
        raise AssertionError(f"T4 must permit {what}; it was refused: {x}") from x


def _holder(tmp_path, name, eid="e-x", obj="Lisbon (my own fact)"):
    v = _mem(tmp_path, name)
    v.store.add_edge(_edge(eid, obj))
    return v


# ---- the binding table: a HELD target ------------------------------------------------------------------------------

@pytest.mark.parametrize("cut", ["full", "notices", "poisoned"])
def test_a_default_import_never_changes_a_held_record_through_a_notice(tmp_path, cut):
    """INV-RR10: whatever copy the unit carries (treated, none, or unredacted), a default import over a HELD target
    records the notice PENDING `held-target` and every held byte is unchanged. Mutant: apply it (the shipped defect at
    1fd3e52); apply the authorized transition in default mode."""
    full, notices, poisoned = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    before = _json(v, "e-x")
    with _permitted("a default import of a notice over a held fact"):
        r = v.import_memory({"full": full, "notices": notices, "poisoned": poisoned}[cut])
    assert _json(v, "e-x") == before, "a held record changed through a notice in a default import"
    assert _rows(v) == [("e-x", "pending", "held-target")]
    assert ["edge", "e-x", "held-target"] in r["notices_not_applied"]
    assert "e-x" not in v.store.redacted_targets(U, "edge")


def test_a_pending_notice_is_no_attestation_and_refuses_no_local_write(tmp_path):
    """INV-RR11: pending is absent from redacted_targets() and refuses no local write. Mutants: count a pending notice
    in redacted_targets(); refuse a local write under it."""
    full, _n, _p = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    v.import_memory(full)
    assert v.store.redacted_targets(U, "edge") == frozenset()
    with _permitted("the user's own write under a pending notice"):
        v.store.add_edge(_edge("e-x", "Lisbon, updated"))
    assert json.loads(_json(v, "e-x"))["object"] == "Lisbon, updated"


def test_a_repeat_default_import_of_a_pending_notice_is_existing_and_keeps_its_reason(tmp_path):
    """IO-II-1: the repeat is `existing`; the row and its reason unchanged. Mutant: re-weigh it."""
    full, _n, _p = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    v.import_memory(full)
    before = v.store._conn.execute("SELECT * FROM redactions").fetchall()
    r = v.import_memory(full)
    assert r["notices_existing"] == 1 and ["edge", "e-x", "held-target"] in r["notices_not_applied"]
    assert v.store._conn.execute("SELECT * FROM redactions").fetchall() == before


def test_io_ii_1_a_record_not_in_file_pending_notice_keeps_its_reason_on_a_default_replay(tmp_path):
    """IO-II-1, the verdict's first sequence, as stated: a notice pending as `record-not-in-file` after a restore
    without its target's copy, then a default import of that notice — `existing`, and the reason stays
    `record-not-in-file` (the round-4 model rewrote it to `held-target`). Mutant: rewrite a pending row's reason."""
    _f, notices, _p = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    v.import_memory(notices, restore=True)
    assert _rows(v) == [("e-x", "pending", "record-not-in-file")]
    before = v.store._conn.execute("SELECT * FROM redactions").fetchall()
    r = v.import_memory(notices)
    assert r["notices_existing"] == 1 and ["edge", "e-x", "record-not-in-file"] in r["notices_not_applied"]
    assert v.store._conn.execute("SELECT * FROM redactions").fetchall() == before


def test_r11_a_pending_notice_keeps_its_reason_through_a_restore_that_leaves_it_pending(tmp_path):
    """Research's R11 (0041 v16.1): a pending notice keeps its STORED reason through every import that leaves it
    pending — the RESTORE leg: pending `held-target` from a default import, then a restore of the notice with no copy
    over a held record that does not show it (the table leaves it pending), and the reason stays `held-target`, never
    rewritten to `record-not-in-file`. Mutant: rewrite a pending row's reason on a restore."""
    _f, notices, _p = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    v.import_memory(notices)
    assert _rows(v) == [("e-x", "pending", "held-target")]
    before = v.store._conn.execute("SELECT * FROM redactions").fetchall()
    r = v.import_memory(notices, restore=True)
    assert ["edge", "e-x", "held-target"] in r["notices_not_applied"]
    assert v.store._conn.execute("SELECT * FROM redactions").fetchall() == before


def test_io_ii_1_a_standing_arrival_pending_notice_keeps_its_reason_on_a_repeat_of_the_notice(tmp_path):
    """IO-II-1, the verdict's second sequence, as stated, default-only: the notice first (standing), a treated arrival
    of its target (pending `standing-arrival`), then the original notice-only file again — `existing`, the reason
    unchanged. Mutant: rewrite a pending row's reason to `held-target`."""
    full, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices)
    v.import_memory(_write(tmp_path / "records.jsonl", [x for x in _lines(full) if x.get("record") != "redaction"]))
    assert _rows(v) == [("e-x", "pending", "standing-arrival")]
    before = v.store._conn.execute("SELECT * FROM redactions").fetchall()
    r = v.import_memory(notices)
    assert r["notices_existing"] == 1 and ["edge", "e-x", "standing-arrival"] in r["notices_not_applied"]
    assert v.store._conn.execute("SELECT * FROM redactions").fetchall() == before


@pytest.mark.parametrize("cut,outcome", [
    ("full", "applied"),                      # the file's copy shows it
    ("poisoned", "refused"),                  # the file's copy is unredacted
    ("notices", "pending"),                   # no copy, and the held record does not show it
])
def test_a_trusted_restore_over_a_held_target_follows_the_files_copy(tmp_path, cut, outcome):
    """§11.6.6's restore column over a HELD target. Mutants: apply on an unredacted copy (the same-store restore);
    apply with no copy over a held record that does not show it."""
    full, notices, poisoned = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    before = _json(v, "e-x")
    f = {"full": full, "notices": notices, "poisoned": poisoned}[cut]
    if outcome == "refused":
        with pytest.raises(ValueError, match="UNREDACTED"):
            v.import_memory(f, restore=True)
        assert _json(v, "e-x") == before and _rows(v) == []
        return
    r = v.import_memory(f, restore=True)
    if outcome == "applied":
        assert json.loads(_json(v, "e-x"))["object"] == R.MARKER
        assert _rows(v) == [("e-x", "applied", None)] and "e-x" in v.store.redacted_targets(U, "edge")
    else:
        assert _json(v, "e-x") == before
        assert _rows(v) == [("e-x", "pending", "record-not-in-file")]
        assert ["edge", "e-x", "record-not-in-file"] in r["notices_not_applied"]


def test_a_restore_with_no_copy_applies_over_a_held_record_that_already_shows_it(tmp_path):
    """§11.6.6: no copy in the unit, and the HELD record already shows the redaction — applied (it attests; held acts
    still carrying content are treated). Mutant: leave it pending."""
    full, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    v.import_memory(full)                                   # holds the treated copy (created + applied)
    v.store._conn.execute("DELETE FROM redactions")            # as if the notice had never travelled with it
    v.store._conn.commit()
    r = v.import_memory(notices, restore=True)
    assert _rows(v) == [("e-x", "applied", None)], r


# ---- the binding table: a CREATED target, and ABSENT targets ------------------------------------------------------

@pytest.mark.parametrize("restore", [False, True])
def test_a_created_record_must_show_its_notice_in_both_modes(tmp_path, restore):
    """INV-RR14: a record this import CREATES beside its notice is applied if it shows the redaction, and refuses the
    whole import if it does not — both modes. Mutants: apply regardless (redacts a poisoned pair's fact); admit the
    record and skip or pend the notice (content its source redacted lands)."""
    full, _n, poisoned = _source(tmp_path, "src")
    fresh = _mem(tmp_path, "fresh.db")
    fresh.import_memory(full, restore=restore)
    assert _rows(fresh) == [("e-x", "applied", None)]
    assert json.loads(_json(fresh, "e-x"))["object"] == R.MARKER
    other = _mem(tmp_path, "other.db")
    with pytest.raises(ValueError, match="UNREDACTED"):
        other.import_memory(poisoned, restore=restore)
    assert _json(other, "e-x") is None and _rows(other) == []


@pytest.mark.parametrize("restore", [False, True])
def test_an_absent_target_leaves_an_inert_standing_notice(tmp_path, restore):
    """§11.6.6: absent and not in the unit → STANDING, in both modes; it is absent from redacted_targets() and refuses
    no local write. Mutants: write no row (the hotfix's default path); count it in redacted_targets(); refuse the
    write."""
    _f, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    r = v.import_memory(notices, restore=restore)
    assert r["notices_standing"] == 1 and _rows(v) == [("e-x", "standing", None)]
    assert v.store.redacted_targets(U, "edge") == frozenset()
    with _permitted("the user's own write of a standing notice's id"):
        v.store.add_edge(_edge("e-x", "Paris (local)"))


@pytest.mark.parametrize("restore,outcome", [(False, "pending"), (True, "applied")])
def test_a_standing_notice_on_a_created_arrival_that_shows_it(tmp_path, restore, outcome):
    """INV-RR12: a standing notice, then a LATER import creating its record treated (the notice not in that unit):
    PENDING `standing-arrival` in a default import, applied in a restore. Mutant: attest a treated arrival
    automatically in a default import; leave a pending standing arrival out of notices_not_applied."""
    full, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices, restore=restore)
    records = _write(tmp_path / "records.jsonl", [x for x in _lines(full) if x.get("record") != "redaction"])
    r = v.import_memory(records, restore=restore)
    if outcome == "pending":
        assert _rows(v) == [("e-x", "pending", "standing-arrival")]
        assert ["edge", "e-x", "standing-arrival"] in r["notices_not_applied"]
    else:
        assert _rows(v) == [("e-x", "applied", None)]


@pytest.mark.parametrize("restore", [False, True])
def test_a_standing_notice_refuses_an_unredacted_arrival_in_both_modes(tmp_path, restore):
    """INV-RR12: content would land under the notice — the whole import refused. Mutants: admit it; complete it on the
    untreated arrival (content removed)."""
    _f, notices, _p = _source(tmp_path, "src")
    plain = _source(tmp_path, "src2")[2]
    plain_records = _write(tmp_path / "plain-records.jsonl", [x for x in _lines(plain) if x.get("record") != "redaction"])
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices, restore=restore)
    with pytest.raises(ValueError, match="UNREDACTED"):
        v.import_memory(plain_records, restore=restore)
    assert _json(v, "e-x") is None


def test_origin_decides_nothing(tmp_path):
    """INV-RR12 / RR14: a notice whose origin claims this store's own origin is weighed like any other — PENDING over a
    held target in a default import. Mutant: compare origins (the hotfix's site; a legitimate B-over-A notice
    misfires)."""
    full, _n, _p = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    forged = [dict(x, origin=v.store.local_origin()) if x.get("record") == "redaction" else x for x in _lines(full)]
    v.import_memory(_write(tmp_path / "forged.jsonl", forged))
    assert _rows(v) == [("e-x", "pending", "held-target")]
    # the B-over-A case the origin check misfired on: store B redacts a record it holds FROM store A
    a = _mem(tmp_path, "a.db")
    a.store.add_edge(_edge("e-ab", "from A"))
    fa = tmp_path / "a.jsonl"
    port.export_memory(a.store, U, fa)
    b = _mem(tmp_path, "b.db")
    b.import_memory(fa)
    b.redact(U, edge_id="e-ab", reason="subject_request")
    fb = tmp_path / "b.jsonl"
    port.export_memory(b.store, U, fb)
    c = _mem(tmp_path, "c.db")
    with _permitted("a fresh store importing B's redaction of A's record"):
        c.import_memory(fb)
    assert c.store._conn.execute("SELECT state FROM redactions WHERE target_id='e-ab'").fetchone() == ("applied",)


# ---- research's B3: a standing notice whose target was since written LOCALLY ---------------------------------------

@pytest.mark.parametrize("restore,cut,want", [
    (False, "notices", ("e-x", "pending", "held-target")),
    (True, "notices", ("e-x", "pending", "record-not-in-file")),
    (True, "full", ("e-x", "applied", None)),
])
def test_a_standing_notice_over_a_local_write_is_weighed_as_a_held_target(tmp_path, restore, cut, want):
    """B3: standing, then the user writes the id locally, then the notice re-arrives — weighed by the table like any
    held target, the SAME row moving standing → pending (default) or the held-target restore row. Mutant: complete it
    on the local record (the arrival loop before the v15.6 hotfix); count it `existing` and leave it standing."""
    full, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices, restore=True)
    row = v.store._conn.execute("SELECT id FROM redactions").fetchone()
    assert row is not None, "the notice-only restore left no standing row"
    rid = row[0]
    with _permitted("the user's own write of a standing notice's id"):
        v.store.add_edge(_edge("e-x", "Paris (local)"))
    before = _json(v, "e-x")
    v.import_memory({"notices": notices, "full": full}[cut], restore=restore)
    assert _rows(v) == [want]
    assert v.store._conn.execute("SELECT id FROM redactions").fetchone()[0] == rid, "the row was duplicated"
    if want[1] != "applied":
        assert _json(v, "e-x") == before


def test_the_users_own_redact_of_a_record_a_standing_notice_names_redacts_it(tmp_path):
    """Found while writing T4 (main-only, never released): `redact()`'s repeat check read ANY redaction row, so after a
    standing notice and a local write of its id the user's own redact() returned `repeated=True` and treated NOTHING.
    It reads APPLIED rows only. Mutant: the unfiltered repeat check."""
    _f, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices, restore=True)
    with _permitted("the user's own write of a standing notice's id"):
        v.store.add_edge(_edge("e-x", "Paris (local)"))
    r = v.redact(U, edge_id="e-x", reason="subject_request")
    assert r.repeated is False and json.loads(_json(v, "e-x"))["object"] == R.MARKER


# ---- research's B1: what an export carries -------------------------------------------------------------------------

def _store_holding(tmp_path, state):
    full, notices, _p = _source(tmp_path, f"src-{state}")
    v = _mem(tmp_path, f"held-{state}.db")
    if state == "applied":
        v.store.add_edge(_edge("e-x", "Lisbon"))
        v.redact(U, edge_id="e-x", reason="subject_request")
    elif state == "pending":
        v.store.add_edge(_edge("e-x", "Lisbon"))
        v.import_memory(full)
    elif state == "standing-absent":
        v.import_memory(notices, restore=True)
    else:                                                       # standing, then a local write of its id
        v.import_memory(notices, restore=True)
        with _permitted("the user's own write of a standing notice's id"):
            v.store.add_edge(_edge("e-x", "Paris (local)"))
    return v


@pytest.mark.parametrize("state", ["applied", "pending", "standing-absent", "standing-local"])
def test_a_stores_own_export_round_trips_whatever_its_notices_hold(tmp_path, state):
    """B1: export carries APPLIED rows, and STANDING rows only when the file does not carry their target; a PENDING
    notice never travels. So a store's own export restores into a fresh store, default-imports into one, and restores
    into ITSELF. FAILED at a2dc7b0 for `standing-local` (measured three ways). Mutants: export every row; export a
    pending notice beside its record."""
    v = _store_holding(tmp_path, state)
    f = tmp_path / f"own-{state}.jsonl"
    port.export_memory(v.store, U, f)
    kinds = [x.get("record") for x in _lines(f)]
    if state in ("pending", "standing-local"):
        assert "redaction" not in kinds, "an export carried a non-applied notice beside its record"
    with _permitted("a store's own export, restored into a fresh store"):
        _mem(tmp_path, f"fresh-r-{state}.db").import_memory(f, restore=True)
    with _permitted("a store's own export, default-imported into a fresh store"):
        _mem(tmp_path, f"fresh-d-{state}.db").import_memory(f)
    with _permitted("a store's own export, restored into itself"):
        v.import_memory(f, restore=True)


# ---- confirm_notice ------------------------------------------------------------------------------------------------

def _pending(tmp_path, name="v.db"):
    full, _n, _p = _source(tmp_path, "src")
    v = _holder(tmp_path, name)
    v.store.confirm_edge(U, "e-x", actor="user", call_path="host_api", correlation_id="k1", request_digest="d1",
                         confirmed_at=__import__("datetime").datetime(2026, 3, 1, tzinfo=__import__("datetime").timezone.utc))
    v.import_memory(full)
    (nid,) = [p["notice_id"] for p in v.pending_notices(U)]
    return v, nid


def test_confirm_notice_is_this_stores_total_treatment_and_keeps_the_foreign_body(tmp_path):
    """INV-RR11: the confirmation treats EVERY held carrier of the target under this store's own map — the held
    confirmation's request digest and its registry row included, which the source's notice (made before any act
    existed here) does not attest — and the foreign body is unchanged. Mutant: confirm with the notice's fields only
    (a held act keeps its verifier)."""
    v, nid = _pending(tmp_path)
    body = v.store._conn.execute("SELECT source_body FROM redactions WHERE id=?", (nid,)).fetchone()
    r = _permitted_call("confirm_notice of a pending notice", v.confirm_notice, U, nid)
    assert r.repeated is False
    assert json.loads(_json(v, "e-x"))["object"] == R.MARKER
    assert v.store._conn.execute("SELECT request_digest FROM confirmations").fetchone()[0] == R.MARKER
    assert v.store._conn.execute("SELECT request_digest FROM request_registry").fetchone()[0] == R.MARKER
    assert v.store._conn.execute("SELECT state, pending_reason, source_body FROM redactions WHERE id=?",
                                 (nid,)).fetchone() == ("applied", None, body[0])
    assert v.pending_notices(U) == [] and "e-x" in v.store.redacted_targets(U, "edge")
    again = _permitted_call("a repeated confirm_notice", v.confirm_notice, U, nid)
    assert again.repeated is True


def test_confirm_notice_refuses_an_unknown_id_and_another_users_identically(tmp_path):
    """Q3: no existence leak — another user's notice id refuses exactly as an unknown id does."""
    v, nid = _pending(tmp_path)
    with pytest.raises(ValueError) as unknown:
        v.confirm_notice(U, "notice-does-not-exist")
    with pytest.raises(ValueError) as other:
        v.confirm_notice("someone-else", nid)
    norm = lambda e, i, u: str(e.value).replace(repr(i), "<id>").replace(repr(u), "<user>")   # noqa: E731
    assert norm(unknown, "notice-does-not-exist", U) == norm(other, nid, "someone-else")


def test_confirm_notice_refuses_a_standing_row_as_standing(tmp_path):
    """Q3: a STANDING row is refused AS standing (under B3's case its target can be held)."""
    _f, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices, restore=True)
    with _permitted("the user's own write of a standing notice's id"):
        v.store.add_edge(_edge("e-x", "Paris (local)"))
    row = v.store._conn.execute("SELECT id FROM redactions").fetchone()
    assert row is not None, "the notice-only restore left no standing row"
    rid = row[0]
    with pytest.raises(ValueError, match="STANDING"):
        v.confirm_notice(U, rid)
    assert json.loads(_json(v, "e-x"))["object"] == "Paris (local)"


def test_an_episode_notice_pending_deleted_inert_recreated_then_confirmed(tmp_path):
    """Q3: an EPISODE target — pending; the episode deleted → confirm refused as inert; an import re-creates it → still
    pending (an import never re-weighs a held pending notice); confirm then applies it. Mutants: re-weigh a pending
    notice when an import re-creates its target; confirm onto an absent target."""
    a = _mem(tmp_path, "a.db")
    a.store.add_episode(Episode(id="ep-x", user_id=U, date="2026-09-01", summary="the secret", provenance=_prov()))
    plain = tmp_path / "ep-plain.jsonl"
    port.export_memory(a.store, U, plain)
    a.redact(U, episode_id="ep-x", reason="subject_request")
    full = tmp_path / "ep.jsonl"
    port.export_memory(a.store, U, full)
    v = _mem(tmp_path, "v.db")
    v.import_memory(plain)
    v.import_memory(full)
    (nid,) = [p["notice_id"] for p in v.pending_notices(U)]
    v.store.delete_episode("ep-x")
    with pytest.raises(ValueError, match="inert"):
        v.confirm_notice(U, nid)
    with _permitted("an import re-creating a pending notice's target"):
        v.import_memory(plain)
    assert [p["notice_id"] for p in v.pending_notices(U)] == [nid]
    _permitted_call("confirm_notice once its target is re-created", v.confirm_notice, U, nid)
    ep = json.loads(v.store._conn.execute("SELECT json FROM episodes WHERE id='ep-x'").fetchone()[0])
    assert ep["summary"] == R.MARKER


def test_forget_user_erases_pending_and_standing_rows(tmp_path):
    """Q3: user erasure removes every notice row, whatever its state."""
    v, _nid = _pending(tmp_path)
    _f, notices, _p = _source(tmp_path, "src-b", eid="e-absent")
    v.import_memory(notices)
    assert {s for _t, s, _r in _rows(v)} == {"pending", "standing"}
    v.store.forget_user(U)
    assert _rows(v) == []


def test_the_doctor_lists_pending_notices_and_flags_a_state_outside_its_domain(tmp_path):
    """§11.6.2's doctor row and Q3: every PENDING notice listed with its claimed source; a state or pending reason
    outside the closed sets — or a reason on a row that is not pending — is an error (the DDL holds no CHECK)."""
    from veracium import doctor as doc
    v, nid = _pending(tmp_path)
    path = str(tmp_path / "v.db")
    rep = doc.diagnose(path)
    assert any("PENDING" in f.message and any(nid in i for i in f.ids) for f in rep.findings), rep
    for bad in ("UPDATE redactions SET state='half'", "UPDATE redactions SET pending_reason='whim'",
                "UPDATE redactions SET state='applied'"):        # a reason left on an applied row
        c = sqlite3.connect(path)
        c.execute(bad)
        c.commit()
        c.close()
        assert any(f.level == "error" and "notice state" in f.message for f in doc.diagnose(path).findings), bad
        c = sqlite3.connect(path)
        c.execute("UPDATE redactions SET state='pending', pending_reason='held-target'")
        c.commit()
        c.close()


# ---- research's B2: the coverage readers count every state ---------------------------------------------------------

def test_coverage_counts_a_standing_notice_for_a_treated_arrivals_reason(tmp_path):
    """B2: a standing-arrival that SHOWS the redaction can carry `invalidation_reason='redacted'` (the three-case rule);
    its notice is held standing, not in the unit, and the import's reason closure must count it (coverage, every
    state) — the arrival goes PENDING in a default import. Mutant: the coverage reader reads applied only (the arrival
    is refused under _refuse_redacted_reason)."""
    a = _mem(tmp_path, "a.db")
    e = _edge("e-r", "Berlin SECRET").model_copy(update={"active": False, "invalidation_reason": "the user said so"})
    a.store._conn.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) "
                          "VALUES(?,?,?,?,?,0,0,?)", (e.id, U, e.subject, e.relation, e.object, e.model_dump_json()))
    a.store._conn.commit()
    a.redact(U, edge_id="e-r", reason="subject_request")
    assert json.loads(_json(a, "e-r"))["invalidation_reason"] == "redacted"
    full = tmp_path / "r.jsonl"
    port.export_memory(a.store, U, full)
    lines = _lines(full)
    notices = _write(tmp_path / "r-notices.jsonl", [lines[0], *[x for x in lines[1:] if x.get("record") == "redaction"]])
    records = _write(tmp_path / "r-records.jsonl", [x for x in lines if x.get("record") != "redaction"])
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices)
    with _permitted("a treated arrival under a held standing notice"):
        v.import_memory(records)
    assert _rows(v) == [("e-r", "pending", "standing-arrival")]


# ---- the v16 step ----------------------------------------------------------------------------------------------------

def _v15_with_rows(path):
    c = sqlite3.connect(path)
    sv.create(c, 15)
    for rid, ev, so in (("r-app", "u:1", None), ("r-std", None, "origin-x"), ("r-native-noevent", None, None)):
        c.execute("INSERT INTO redactions(id,user_id,target_kind,target_id,fields,marker_version,reason,"
                  "store_version_before,store_version_after,event_ref,recorded_at,source_origin) "
                  "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (rid, U, "edge", "e-" + rid, '["object"]', 1, "imported_notice", 1, 1, ev,
                   "2026-10-01T00:00:00+00:00", so))
    c.execute("PRAGMA user_version = 15")
    c.commit()
    c.close()


def test_the_v16_step_derives_each_rows_state_by_the_pre_v16_rule(tmp_path):
    """The step preserves today's semantics: no event and a source → standing; else applied (a native row with no
    event counted as attested before v16, and still does); no row pending."""
    p = str(tmp_path / "s.db")
    _v15_with_rows(p)
    migrate_store(p)
    c = sqlite3.connect(p)
    assert c.execute("SELECT id, state, pending_reason FROM redactions ORDER BY id").fetchall() == [
        ("r-app", "applied", None), ("r-native-noevent", "applied", None), ("r-std", "standing", None)]
    assert c.execute("SELECT sql FROM sqlite_master WHERE name='redactions'").fetchone()[0] == \
        sv.ALTER_PATH_V16_REDACTIONS_SQL


@pytest.mark.parametrize("label,sql", [
    ("a row read as pending", "UPDATE redactions SET state='pending', pending_reason='held-target' WHERE id='r-app'"),
    ("a standing row read as applied", "UPDATE redactions SET state='applied' WHERE id='r-std'"),
    ("a v15 column changed", "UPDATE redactions SET fields='[]' WHERE id='r-app'"),
    ("a row lost", "DELETE FROM redactions WHERE id='r-native-noevent'"),
])
def test_each_notice_state_mutant_refuses_at_its_step(tmp_path, monkeypatch, label, sql):
    """PA1 cells (research's N3 rule): each injected at the step, after its own UPDATE, by a TEMP trigger on the
    stamp's read — refuses AT `v16-notice-state`, and nothing lands."""
    real = sv.mint_act_counter

    def mint(conn):
        conn.execute("CREATE TEMP TRIGGER m AFTER UPDATE OF state ON redactions WHEN NEW.id='r-std' BEGIN "
                     + sql + "; END")
        real(conn)
    monkeypatch.setattr(sv, "mint_act_counter", mint)
    p = str(tmp_path / "m.db")
    _v15_with_rows(p)
    with pytest.raises(MigrationPostconditionError) as ei:
        migrate_store(p)
    assert ei.value.step == M.STEP_NOTICE_STATE, (label, ei.value.step, ei.value.problems)
    assert sqlite3.connect(p).execute("PRAGMA user_version").fetchone()[0] == 15


# ---- research's T4 stage 2 (2026-10-15): T4-1 and the seven gaps, each the property its mutant broke ---------------

def _episode_source(tmp_path, name="eps", eid="ep-x"):
    """A source holding an episode, exported plain, then redacted and exported: (plain, full, poisoned = the plain
    record beside the notice, the pair a poisoned export carries)."""
    a = _mem(tmp_path, f"{name}.db")
    a.store.add_episode(Episode(id=eid, user_id=U, date="2026-09-01", summary="the SECRET", provenance=_prov()))
    plain = tmp_path / f"{name}-plain.jsonl"
    port.export_memory(a.store, U, plain)
    a.redact(U, episode_id=eid, reason="subject_request")
    full = tmp_path / f"{name}.jsonl"
    port.export_memory(a.store, U, full)
    a.close()
    notice = [x for x in _lines(full)[1:] if x.get("record") == "redaction"]
    poisoned = _write(tmp_path / f"{name}-poisoned.jsonl", [_lines(full)[0], *_lines(plain)[1:], *notice])
    return plain, full, poisoned


def _summary(m, eid):
    r = m.store._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    return None if r is None else json.loads(r[0])["summary"]


def test_t4_1_a_pending_notice_beside_its_unredacted_re_created_record_refuses_the_unit(tmp_path):
    """T4-1 (BLOCKING, research): pending (held-target) → the episode deleted → a DEFAULT unit carrying the plain
    record beside the notice. §11.6.6 row 1 refuses it whole; the pending shortcut admitted it and the content landed.
    Then the SHOWN variant (dev's call): the same unit with the record treated is APPLIED — the unit attests itself
    and nothing the user holds changes. Mutant: weigh the pending shortcut before the created row."""
    plain, full, poisoned = _episode_source(tmp_path)
    v = _mem(tmp_path, "v.db")
    v.import_memory(plain)
    v.import_memory(full)
    assert _rows(v) == [("ep-x", "pending", "held-target")]
    v.store.delete_episode("ep-x")
    with pytest.raises(ValueError, match="UNREDACTED"):
        v.import_memory(poisoned)
    assert _summary(v, "ep-x") is None and _rows(v) == [("ep-x", "pending", "held-target")]
    v.import_memory(full)
    assert _summary(v, "ep-x") == R.MARKER and _rows(v) == [("ep-x", "applied", None)]


def test_r18_confirm_notice_never_treats_another_users_record_under_the_same_id(tmp_path):
    """R18 (cross-user WRITE): u's pending notice, u's episode deleted, w writes an episode under the same id (ids are
    a global key); u's confirm_notice is refused as inert and w's record is untouched. Mutant: drop the target-owner
    check."""
    plain, full, _p = _episode_source(tmp_path)
    v = _mem(tmp_path, "v.db")
    v.import_memory(plain)
    v.import_memory(full)
    (nid,) = [p["notice_id"] for p in v.pending_notices(U)]
    v.store.delete_episode("ep-x")
    v.store.add_episode(Episode(id="ep-x", user_id="w", date="2026-09-02", summary="w's own words", provenance=_prov()))
    with pytest.raises(ValueError, match="inert"):
        v.confirm_notice(U, nid)
    assert _summary(v, "ep-x") == "w's own words"


def test_r15_pending_notices_reads_one_users_rows(tmp_path):
    """R15 (cross-user READ): another user's pending notices are never listed. Mutant: drop the user filter."""
    v, _nid = _pending(tmp_path)
    assert len(v.pending_notices(U)) == 1 and v.pending_notices("someone-else") == []


def test_r9_a_standing_episode_notice_over_a_local_episode_write_round_trips_the_own_export(tmp_path):
    """R9: B1's round trip for the EPISODE kind — the export's carried set holds episodes too, so a standing episode
    notice whose id the user wrote locally does not travel beside it. Mutant: build the carried set from edges only."""
    _plain, full, _p = _episode_source(tmp_path)
    notices = _write(tmp_path / "ep-notices.jsonl", [_lines(full)[0], *[x for x in _lines(full)[1:] if x.get("record") == "redaction"]])
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices, restore=True)
    with _permitted("the user's own episode write of a standing notice's id"):
        v.store.add_episode(Episode(id="ep-x", user_id=U, date="2026-09-03", summary="mine", provenance=_prov()))
    f = tmp_path / "own-ep.jsonl"
    port.export_memory(v.store, U, f)
    assert "redaction" not in [x.get("record") for x in _lines(f)]
    with _permitted("a store's own export, restored into a fresh store"):
        _mem(tmp_path, "fresh-ep.db").import_memory(f, restore=True)
    with _permitted("a store's own export, restored into itself"):
        v.import_memory(f, restore=True)


def test_r10_a_restore_weighs_a_held_pending_notice(tmp_path):
    """R10: a held PENDING notice re-arriving in a trusted restore whose file shows the redaction is APPLIED — the same
    row, its body unchanged (§11.6.6: "in a trusted restore the table weighs it"). Mutant: count it `existing`."""
    full, _n, _p = _source(tmp_path, "src")
    v = _holder(tmp_path, "v.db")
    v.import_memory(full)
    rid, body = v.store._conn.execute("SELECT id, source_body FROM redactions").fetchone()
    v.import_memory(full, restore=True)
    assert _rows(v) == [("e-x", "applied", None)] and json.loads(_json(v, "e-x"))["object"] == R.MARKER
    assert v.store._conn.execute("SELECT id, source_body FROM redactions").fetchone() == (rid, body)


def test_r5_coverage_counts_a_standing_notice_for_a_treated_episodes_reason(tmp_path):
    """R5: B2's EPISODE twin — an episode whose retired reason the redaction made `redacted` arrives treated under a
    standing notice held from an earlier file; the episode reason closure counts it (coverage), and the notice goes
    PENDING `standing-arrival`. Mutant: the episode coverage reader reads applied only."""
    a = _mem(tmp_path, "a.db")
    ep = Episode(id="ep-r", user_id=U, date="2026-09-01", summary="the SECRET", provenance=_prov())
    ep = ep.model_copy(update={"retired_at": __import__("datetime").datetime(2026, 9, 2, tzinfo=__import__("datetime").timezone.utc),
                               "retired_reason": "the user said so"})
    a.store._conn.execute("INSERT INTO episodes(id,user_id,date,json) VALUES(?,?,?,?)", (ep.id, U, ep.date, ep.model_dump_json()))
    a.store._conn.commit()
    a.redact(U, episode_id="ep-r", reason="subject_request")
    assert json.loads(a.store._conn.execute("SELECT json FROM episodes WHERE id='ep-r'").fetchone()[0])["retired_reason"] == "redacted"
    full = tmp_path / "er.jsonl"
    port.export_memory(a.store, U, full)
    lines = _lines(full)
    notices = _write(tmp_path / "er-notices.jsonl", [lines[0], *[x for x in lines[1:] if x.get("record") == "redaction"]])
    records = _write(tmp_path / "er-records.jsonl", [x for x in lines if x.get("record") != "redaction"])
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices)
    with _permitted("a treated episode arrival under a held standing notice"):
        v.import_memory(records)
    assert _rows(v) == [("ep-r", "pending", "standing-arrival")]


def test_r25_the_doctor_flags_a_state_outside_its_domain_with_no_reason(tmp_path):
    """R25: ('half', NULL) — a state outside the closed set whose pending reason is NULL, so only the DOMAIN clause can
    see it (the earlier cell's planted row still carried a reason). Mutant: drop the domain clause."""
    from veracium import doctor as doc
    v, _nid = _pending(tmp_path)
    path = str(tmp_path / "v.db")
    c = sqlite3.connect(path)
    c.execute("UPDATE redactions SET state='half', pending_reason=NULL")
    c.commit()
    c.close()
    assert any(f.level == "error" and "notice state" in f.message for f in doc.diagnose(path).findings)


@pytest.mark.parametrize("restore", [False, True])
def test_r27_a_standing_notices_own_copy_with_its_created_record_takes_the_created_row(tmp_path, restore):
    """R27 (research's ratification of (b)): a STANDING notice held from an earlier file, then a unit carrying the
    notice AND its record treated — the created row: APPLIED in both modes, the outcome a fresh store reaches. Mutant:
    weigh it by the standing-arrival rule (pending on a default import)."""
    full, notices, _p = _source(tmp_path, "src")
    v = _mem(tmp_path, "v.db")
    v.import_memory(notices, restore=restore)
    assert _rows(v) == [("e-x", "standing", None)]
    v.import_memory(full, restore=restore)
    assert _rows(v) == [("e-x", "applied", None)]


def test_every_src_call_of_the_attested_fields_reader_names_it():
    """Research's ratification of (c): every call in src/ names its reader (`coverage=`) — the claim held by a gate,
    found by the AST, never by a hand list. The census is not vacuous: a planted unnamed call is found."""
    import ast as _ast
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "veracium"

    def unnamed(text):
        out = []
        for n in _ast.walk(_ast.parse(text)):
            if (isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute) and n.func.attr == "_attested_fields"
                    and "coverage" not in {k.arg for k in n.keywords}):
                out.append(n.lineno)
        return out
    calls = {str(p.relative_to(root)): unnamed(p.read_text()) for p in sorted(root.rglob("*.py"))}
    assert {f: ls for f, ls in calls.items() if ls} == {}
    assert sum(1 for p in root.rglob("*.py") for n in _ast.walk(_ast.parse(p.read_text()))
               if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute) and n.func.attr == "_attested_fields") >= 7
    assert unnamed("store._attested_fields(u, 'edge', e)\n") == [1]


# ---- IO-II-3: competing import, confirmation and redaction across connections (round 4's list, product half) ------

def test_io_ii_3_a_redaction_on_one_connection_then_confirm_notice_on_another(tmp_path):
    """IO-II-3: the user redacts the target on connection B while the notice is pending on A; A's confirm_notice then
    adds its attestation and treats nothing new (§11.6.6: "Confirming one whose target this store has since redacted").
    Mutants: confirm refuses a target already redacted; confirm re-treats it into a second, different state."""
    from veracium.store.sqlite import SqliteStore
    v, nid = _pending(tmp_path)
    b = SqliteStore(str(tmp_path / "v.db"))
    try:
        rb = _permitted_call("the user's own redaction on a second connection", b.redact, U, edge_id="e-x",
                             reason="subject_request")
        after_b = _json(v, "e-x")
        assert rb.repeated is False and json.loads(after_b)["object"] == R.MARKER
        r = _permitted_call("confirm_notice after another connection redacted the target", v.confirm_notice, U, nid)
        assert r.repeated is False and _json(v, "e-x") == after_b, "the confirmation re-treated a redacted record"
        assert v.store._conn.execute("SELECT COUNT(*) FROM redactions WHERE state='applied'").fetchone()[0] == 2
        assert v.pending_notices(U) == []
    finally:
        b.close()


def test_io_ii_3_a_held_write_lock_refuses_confirm_notice_cleanly_then_it_proceeds(tmp_path):
    """IO-II-3: a confirmation competing with another connection's open write transaction refuses in the store's
    lock-refusal form (0029 §4a) and writes NOTHING — the notice still pending, the record untouched; once the holder
    releases, the same confirmation applies. Mutant: a confirmation that writes outside its BEGIN IMMEDIATE."""
    import contextlib as _cl
    from veracium.store.sqlite import SqliteStore
    v, nid = _pending(tmp_path)
    path = str(tmp_path / "v.db")
    before = _json(v, "e-x")
    holder, writer = SqliteStore(path), SqliteStore(path, busy_timeout_ms=200)
    try:
        holder._conn.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError, match="could not take the write lock"):
            writer.confirm_notice(U, nid)
        holder._conn.execute("ROLLBACK")
        assert _json(v, "e-x") == before and [p["notice_id"] for p in v.pending_notices(U)] == [nid]
        _permitted_call("confirm_notice once the lock is released", writer.confirm_notice, U, nid)
        assert json.loads(_json(v, "e-x"))["object"] == R.MARKER and v.pending_notices(U) == []
    finally:
        with _cl.suppress(sqlite3.OperationalError):
            holder._conn.execute("ROLLBACK")
        holder.close()
        writer.close()


def test_io_ii_3_a_confirmation_on_one_connection_then_an_import_on_another(tmp_path):
    """IO-II-3: confirm_notice on A; a default re-import of the same file on connection B finds the notice APPLIED —
    `existing`, nothing re-treated, nothing pending again. Mutant: an import re-weighs an applied notice."""
    from veracium.store.sqlite import SqliteStore
    full, _n, _p = _source(tmp_path, "src2")
    v = _holder(tmp_path, "v.db")
    v.import_memory(full)
    (nid,) = [p["notice_id"] for p in v.pending_notices(U)]
    _permitted_call("confirm_notice", v.confirm_notice, U, nid)
    settled = v.store._conn.execute("SELECT * FROM redactions").fetchall(), _json(v, "e-x")
    b = Memory(llm=_quiet, config=MemoryConfig(db_path=str(tmp_path / "v.db"), wiki_recompile_after_writes=0,
                                               scope_groups={}, require_source_id=False))
    try:
        with _permitted("a re-import on a second connection"):
            r = b.import_memory(full)
        assert r["notices_existing"] == 1 and r["notices_not_applied"] == []
        assert (v.store._conn.execute("SELECT * FROM redactions").fetchall(), _json(v, "e-x")) == settled
    finally:
        b.close()


def _permitted_call(what, fn, *a, **k):
    """IO-II-7's form for a call a cell expects to succeed: a store refusal fails as an assertion naming it."""
    try:
        return fn(*a, **k)
    except (ValueError, KeyError, RuntimeError) as x:
        raise AssertionError(f"{what} was refused: {type(x).__name__}: {x}") from x
