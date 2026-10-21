"""T12's product fixes (the closing gates' one guarded commit): the carried rows research measured open at a26a8e7 —
T5 S2 N3 (the v16 step's arity inventory selects by the relation COLUMN only), T6 S2 F5 (an inventory row naming
another user's edge is dropped silently) — research's T11b landing nit (the act noun) and its T12 side finding
(`IDENTIFIER_RE` admits a trailing newline). Build note b2870871 with addendum 1 (9d872f85; research's stage-1 read
39899dfe). Each cell names its mutant; the campaign is `t12_mutant_defs.py`.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from veracium import PolicyLane, doctor
from veracium import portability as P
from veracium.schema import DEFAULT_RELATIONS, Disclosure, Edge, EvidenceAuthor, Provenance
from veracium.store import data_migration as DM
from veracium.store.migration import MigrationPostconditionError, migrate_store
from veracium.store.release_migration import MigrationAttestation
from veracium.store.sqlite import SqliteStore

import test_0044_t5_era as T5

AT = datetime(2026, 2, 1, tzinfo=timezone.utc)
ATT = MigrationAttestation(quiesced=True, backup_ref="bk-t12")


def _ok(fn, *a, **k):
    """A call the cell expects to SUCCEED: any raise is the property failing, read as an assertion."""
    try:
        return fn(*a, **k)
    except Exception as exc:                                       # noqa: BLE001 — the cell's subject
        raise AssertionError(f"expected success; raised {type(exc).__name__}: {exc}") from exc


# ======================================================================= T5 S2 N3: column OR json selects the row
def _v15_with_column(tmp_path, name, column):
    """A v15 store holding one edge retired `superseded` whose json names `measures`, its relation COLUMN `column`."""
    p = str(tmp_path / f"{name}.db")
    e = T5._edge("e-" + name, "weight 78", at=AT, reason="superseded")
    T5._v15(p)
    c = sqlite3.connect(p)
    c.execute("INSERT INTO edges(id,user_id,subject,relation,object,active,quarantined,json) VALUES(?,?,?,?,?,0,0,?)",
              (e.id, e.user_id, e.subject, column, e.object, e.model_dump_json()))
    c.commit()
    c.close()
    return p, e.id


def test_n3_a_row_whose_column_and_json_disagree_refuses_the_v16_step(tmp_path):
    """Research's T5 S2 N3: the step-8 selection reads the relation column OR the json's relation, so a row whose json
    names a reclassified relation under another column value is SEEN, and F2's column = json check refuses the step
    (before, it migrated with nothing inventoried and nothing refused). Control: column = json is inventoried. Mutant:
    select by the column alone."""
    p, eid = _v15_with_column(tmp_path, "control", "measures")
    _ok(migrate_store, p)
    assert T5._members(p) == {eid}
    q, _ = _v15_with_column(tmp_path, "disagree", "likes")
    with pytest.raises(MigrationPostconditionError, match="the relation column 'likes' is not its json relation"):
        migrate_store(q)


# ====================================================================== T6 S2 F5: another user's edge in the inventory
def _f5_store(tmp_path, *, user="U"):
    """V's edge, retired `superseded`, with an inventory row naming `user` (U: the damage; V: the control)."""
    e = Edge(id="v-p", user_id="V", subject="user", relation="measures", object="weight 78", valid_from=AT,
             invalidated_at=AT + timedelta(days=30), invalidation_reason="superseded",
             provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r",
                                   disclosure=Disclosure.MENTIONABLE, observed_at=AT))
    p = str(tmp_path / f"f5-{user}.db")
    s = SqliteStore(p)
    s.add_edge(e)
    d = json.loads(s._conn.execute("SELECT json FROM edges WHERE id='v-p'").fetchone()[0])
    s._conn.execute("INSERT INTO arity_inventory VALUES('v-p', ?, ?, 'superseded')", (user, d["invalidated_at"]))
    s._conn.commit()
    s.close()
    return p


def test_f5_an_inventory_row_naming_another_users_edge_fails_that_user_and_doctor_warns(tmp_path):
    """Research's T6 S2 F5: U's inventory row names V's edge. Before, U read `migrated` with no outcome row, the row
    still inventoried and doctor quiet. Now U is a named `failed` (0018 §4i's carrier: the existing outcome, a
    class-only diagnostic), nothing is written for it, and doctor warns in every phase. Control: the row naming its own
    user (V) migrates. Mutants: the integrity read removed; doctor's row removed."""
    p = _f5_store(tmp_path)
    assert [f.message[:40] for f in doctor.diagnose(p).findings if f.check == "data-migration" and "damaged" in f.message]
    r = DM.run_data_migration(p, host_attestation=ATT, registry=dict(DEFAULT_RELATIONS), op_id="op-f5")
    assert (r.outcome, r.committed, r.failed) == ("failed", (), ("U",)), (r.outcome, r.committed, r.failed)
    assert "ValueError" in r.diagnostic and "v-p" not in r.diagnostic
    s = SqliteStore(p)
    try:
        assert s._conn.execute("SELECT COUNT(*) FROM migration_outcome").fetchone()[0] == 0
        assert s._conn.execute("SELECT COUNT(*) FROM migration_run").fetchone()[0] == 0
    finally:
        s.close()
    damaged = [f for f in doctor.diagnose(p).findings if f.check == "data-migration" and "damaged" in f.message]
    assert len(damaged) == 1 and damaged[0].level == "warn"
    c = _f5_store(tmp_path, user="V")
    rc = DM.run_data_migration(c, host_attestation=ATT, registry=dict(DEFAULT_RELATIONS), op_id="op-f5c")
    assert rc.outcome == "migrated" and rc.committed == ("V",)
    assert not [f for f in doctor.diagnose(c).findings if f.check == "data-migration" and "damaged" in f.message]


def _damaged(p, **k):
    return [f for f in doctor.diagnose(p, **k).findings if f.check == "data-migration" and "damaged" in f.message]


def test_f5_an_inventory_row_naming_no_edge_at_all_fails_that_user_beside_a_sound_one(tmp_path):
    """F5's other half (the integrity read's `e.id IS NULL`): U's inventory row names an edge the store does not hold.
    U is a named `failed`, V (whose row names its own edge) commits in the same call — the closed carrier's `partial`
    — and doctor warns naming the row. Mutant: only another user's edge counted (a missing edge admitted)."""
    p = _f5_store(tmp_path, user="V")
    c = sqlite3.connect(p)
    c.execute("INSERT INTO arity_inventory VALUES('gone', 'U', ?, 'superseded')", (AT.isoformat(),))
    c.commit()
    c.close()
    assert [f.ids for f in _damaged(p)] == [["gone"]]
    r = DM.run_data_migration(p, host_attestation=ATT, registry=dict(DEFAULT_RELATIONS), op_id="op-f5g")
    assert (r.outcome, r.committed, r.failed) == ("partial", ("V",), ("U",)), (r.outcome, r.committed, r.failed)


def test_f5_doctors_damaged_row_is_scoped_by_user(tmp_path):
    """doctor --user reports only that user's damaged inventory rows (the scope every data-migration row keeps, T7-1
    N3): U's row naming V's edge is U's damage — reported under U and unscoped, never under V. Mutant: the damaged
    query unscoped by --user."""
    p = _f5_store(tmp_path)
    assert len(_damaged(p)) == 1 and len(_damaged(p, user="U")) == 1
    assert _damaged(p, user="V") == []


# ================================================================== research's landing nit and side finding
def test_the_orphan_refusal_names_a_reply_as_a_reply(tmp_path):
    """Research's T11b landing nit: the orphan refusal built its noun as the table name minus one letter, so a reply
    read "replie". The noun comes from the closed marker map. Mutant: the slice back."""
    assert P._ACT_NOUN == {"confirmations": "confirmation", "replies": "reply"}
    act = {"table": "replies", "act_uid": ("o", "u", "r-1"), "act_seq": 1, "edge_id": "e-nowhere", "kind": "context",
           "target_uid": None, "text": "x", "actor": "user", "call_path": None, "confirmed_at": None,
           "written_at": "2026-10-01T00:00:00+00:00", "recorded_correlation_id": "k", "request_digest": "a" * 64,
           "origin": "local"}
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        with pytest.raises(ValueError, match=r"p: reply \('o', 'u', 'r-1'\) names edge"):
            P._act_preflight(s, "p", "u", [act], [], {}, restore=True, notices=[], now=datetime.now(timezone.utc))
    finally:
        s.close()


@pytest.mark.parametrize("ident,ok", [("abc", True), ("a.b:c-d_e", True), ("abc\n", False), ("abc def", False),
                                      ("", False), ("x" * 65, False), ("\nabc", False)])
def test_a_policy_identifier_is_matched_whole_so_a_trailing_newline_refuses(ident, ok):
    """Research's T12 side finding: `IDENTIFIER_RE` was `^…$` read with `.match`, and `$` admits a trailing newline, so
    "abc\\n" passed where "abc def" refused, against the docstring's "no whitespace". Matched whole now. Mutant: `.match`
    back."""
    if ok:
        assert _ok(PolicyLane, policy_id=ident, policy_version="1", ranks={"e-1": 1}).policy_id == ident
    else:
        with pytest.raises(ValueError):
            PolicyLane(policy_id=ident, policy_version="1", ranks={"e-1": 1})


# ========================================================= T5 S2 N2: 0025 F4's closure command no longer matches itself
def test_n2_the_f4_closure_command_reads_above_the_ledger_and_fails_when_the_annotation_drifts(tmp_path):
    """Research's T5 S2 N2: 0025 F4's closure command searched the WHOLE spec for "from 0044", and the ledger row that
    carries the command contains that phrase, so the command could never fail. It reads the text ABOVE the closure
    ledger now. Shipped: exit 0. With the annotation's "from 0044" reworded (research's probe): exit 1. Mutant: read the
    whole file again."""
    import importlib.util
    import os
    import pathlib
    import shutil
    import subprocess
    import sys
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("closure_findings_t12", root / "specs" / "closure_findings.py")
    cf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cf)
    (cmd,) = [row[6] for row in cf.CLOSURES if row[0] == "0025" and row[3] == "F4"]
    rel = "specs/0025-relation-vocabulary-enforcement.md"

    def run(text):
        d = tmp_path / f"t{len(list(tmp_path.iterdir()))}"
        (d / "specs").mkdir(parents=True)
        (d / rel).write_text(text)
        env = dict(os.environ, PY=sys.executable)
        env["PYTHONPATH"] = str(root / "src")
        return subprocess.run(["bash", "-c", cmd.replace("PYTHONPATH=src ", "")], cwd=d, env=env).returncode
    shipped = (root / rel).read_text()
    assert run(shipped) == 0
    lines = shipped.splitlines(keepends=True)
    i = next(n for n, ln in enumerate(lines) if ln.startswith("> *Annotation (research, 2026-10-15") and "from 0044" in ln)
    lines[i] = lines[i].replace("from 0044's", "per the arity spec's")
    drifted = "".join(lines)
    assert "from 0044" in drifted.split("**Per-finding closure ledger", 1)[1]    # the ledger row still carries it
    assert run(drifted) == 1


# ================================================================ the release text's wording (build note D6, P3)
def test_the_owners_release_wording_replaced_now_keep_every_value_in_every_tracked_use():
    """0044 §8 (the owner's release text, v1.6: "no longer supersede incomparable values" IN PLACE OF "now keep every
    value"; 0044 L9, L652): no tracked file USES the replaced phrase — the one remaining occurrence is 0044's own Version
    cell, which QUOTES it (a mention). The CHANGELOG carries the release text. Mutant: api.md's line reverted."""
    import pathlib
    import subprocess
    root = pathlib.Path(__file__).resolve().parents[1]
    try:
        files = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("no git checkout: the sweep reads the tracked tree")
    hits = []
    for f in files:
        p = root / f
        if p.suffix not in (".md", ".py", ".txt", ".json") or not p.is_file():
            continue
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if "keep every value" in line:
                hits.append((f, n))
    this = pathlib.Path(__file__).relative_to(root).as_posix()
    assert [h for h in hits if h[0] != this] == [("specs/0044-relation-arity.md", 9)], hits
    assert "“now keep every value”" in (root / "specs/0044-relation-arity.md").read_text().splitlines()[8]
    assert "no longer supersede incomparable values: a second preference" in (root / "CHANGELOG.md").read_text()
