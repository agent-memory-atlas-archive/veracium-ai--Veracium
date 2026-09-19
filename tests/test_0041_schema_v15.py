"""specs/0041 tranche 2 — the schema bump 14 -> 15 (`episode_event`, `redactions`), the unattested-marker report, erasure
and the doctor's sweep — every transition claim shown on the FROZEN pre-restriction store (§4h(iii)), never on a
record the new code wrote."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0041"


def _load_tt():
    spec = importlib.util.spec_from_file_location("tt41", ROOT / "tests" / "test_0041_transition_table.py")
    m = importlib.util.module_from_spec(spec); sys.modules["tt41"] = m; spec.loader.exec_module(m); return m


def test_v15_adds_exactly_the_two_tables_and_their_indexes_and_the_head_is_15():
    from veracium.store import schema_version as sv
    assert sv.SCHEMA_VERSION == 15 and 15 in sv.SCHEMAS
    added = {o.key for o in sv.SCHEMAS[15]} - {o.key for o in sv.SCHEMAS[14]}
    assert added == {("table", "episode_event"), ("index", "ix_episode_event_lookup"), ("table", "redactions"), ("index", "ix_redactions_target")}, added
    policies = {o.key: o.policy for o in sv.SCHEMAS[15] if o.key in added}
    assert policies[("table", "episode_event")] == sv.REQUIRED and policies[("table", "redactions")] == sv.REQUIRED
    assert policies[("index", "ix_episode_event_lookup")] == sv.REBUILDABLE and policies[("index", "ix_redactions_target")] == sv.REBUILDABLE


def test_the_frozen_v14_store_migrates_to_15_with_its_rows_intact_and_no_data_step(tmp_path):
    """The crossing is DDL only: the pre-restriction store's rows (its prose kind, its two unattested marker rows,
    its relation-only quarantine) arrive at v15 byte-identical; the two tables exist and are empty. On a RAW copy
    of the frozen bytes — the helper that opens the fixture migrates first, so it cannot show this."""
    from veracium.store.migration import migrate_store
    frozen = tmp_path / "raw.sqlite"; shutil.copy2(EVIDENCE / "pre_restriction.sqlite", frozen)
    c = sqlite3.connect(str(frozen))
    assert c.execute("PRAGMA user_version").fetchone()[0] == 14
    before = {r[0]: r[1] for r in c.execute("SELECT id, json FROM edges")}
    before_eps = {r[0]: r[1] for r in c.execute("SELECT id, json FROM episodes")}
    c.close()
    r = migrate_store(str(frozen))
    assert r == "migrated" and r.resulting_version == 15, r
    c = sqlite3.connect(str(frozen))
    assert c.execute("PRAGMA user_version").fetchone()[0] == 15
    assert {r[0]: r[1] for r in c.execute("SELECT id, json FROM edges")} == before
    assert {r[0]: r[1] for r in c.execute("SELECT id, json FROM episodes")} == before_eps
    assert c.execute("SELECT COUNT(*) FROM episode_event").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0
    c.close()


def test_the_unattested_marker_report_names_the_frozen_rows_and_their_field_and_nothing_else(tmp_path):
    tt = _load_tt()
    from veracium.store import migration
    st = tt._frozen_store(tmp_path); man = tt._frozen_rows()
    rows = migration.unattested_marker_report(st)
    assert {r["target_id"] for r in rows} == {man["unattested_marker"], man["unattested_marker_2"]}
    assert {r["field"] for r in rows} == {"object"} and {r["target_kind"] for r in rows} == {"edge"}
    # the control: attest one of them (a redaction record naming the row and the field) and it leaves the report
    st._conn.execute("INSERT INTO redactions(id,user_id,target_kind,target_id,fields,marker_version,reason,store_version_before,store_version_after,event_ref,recorded_at) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("r1", tt.U, "edge", man["unattested_marker"], json.dumps(["object"]), 1, "subject_request", 15, 15, None, "2026-09-19T00:00:00Z"))
    st._conn.commit()
    assert {r["target_id"] for r in migration.unattested_marker_report(st)} == {man["unattested_marker_2"]}
    st.close()


def test_forget_user_erases_the_two_new_tables_and_the_doctor_flags_a_redaction_naming_a_missing_target(tmp_path):
    tt = _load_tt()
    from veracium import doctor as doc
    st = tt._frozen_store(tmp_path)
    st._conn.execute("INSERT INTO redactions(id,user_id,target_kind,target_id,fields,marker_version,reason,store_version_before,store_version_after,event_ref,recorded_at) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("r-orphan", tt.U, "edge", "no-such-edge", json.dumps(["object"]), 1, "subject_request", 15, 15, None, "2026-09-19T00:00:00Z"))
    st._conn.execute("INSERT INTO episode_event(user_id,seq,txn,episode_id,kind,reason,state,recorded_at) VALUES(?,?,?,?,?,?,?,?)",
                     (tt.U, 999999, 999999, "no-such-episode", "redacted", "subject_request", "{}", "2026-09-19T00:00:00Z"))
    st._conn.commit()
    st.close()
    # the doctor diagnoses a CLOSED store by path (it snapshots the file); the two orphans are `refs` errors
    rep = doc.diagnose(str(tmp_path / "frozen.db"))
    refs = [f for f in rep.findings if f.check == "refs" and f.level == "error"]
    msgs = " | ".join(f.message for f in refs)
    assert "1 redaction record(s) naming a target that does not exist" in msgs, doc.render(rep)
    assert "1 episode event(s) naming an episode that does not exist" in msgs, doc.render(rep)
    assert {"r-orphan"} <= set(sum((f.ids for f in refs), [])) and {"no-such-episode"} <= set(sum((f.ids for f in refs), []))
    assert "redaction" in json.dumps(doc.to_json(rep))
    # the control: the doctor on the frozen copy WITHOUT the orphans raises no refs error about them
    (tmp_path / "clean").mkdir(); clean = tt._frozen_store(tmp_path / "clean"); clean.close()
    rep0 = doc.diagnose(str(tmp_path / "clean" / "frozen.db"))
    assert not any("redaction record" in f.message or "episode event" in f.message for f in rep0.findings), doc.render(rep0)
    # erasure: forget_user clears both tables for the user (0017's per-user erasure reaches the two new carriers)
    st = tt._mem(tmp_path, name="frozen.db").store
    assert st._conn.execute("SELECT COUNT(*) FROM redactions WHERE user_id=?", (tt.U,)).fetchone()[0] == 1
    st.forget_user(tt.U)
    assert st._conn.execute("SELECT COUNT(*) FROM redactions WHERE user_id=?", (tt.U,)).fetchone()[0] == 0
    assert st._conn.execute("SELECT COUNT(*) FROM episode_event WHERE user_id=?", (tt.U,)).fetchone()[0] == 0
    st.close()
