"""specs/0041 §4g — the notice-binding HOTFIX (internal finding 2026-10-13, the owner's rulings: fail closed, all three
arms, including the standing notices the earlier code already wrote). 0041 as implemented on main since 8ea59e7 (never
in a release) bound an imported redaction notice
to a bare target id, so an UNTRUSTED (default-mode) file carrying nothing but a notice could (1) permanently redact the
destination user's OWN held fact, (2) leave a STANDING notice for an absent id that refused the user's own later write
of it and listed it as redacted, and (3) redact a later record of that id on arrival. Found by the 0045–0047 round-4
reference model; reproduced on the shipped code (dev-handoff/round4-I-II/repro_notice_default.py; research's
probe_standing_notice.py).

RE-POINTED AT T4 (specs/0041 §11.6.6, the notice state machine, which REPLACES the hotfix's rule). Every ATTACK below
is still the attacker's move and still fails; what the store records changed. A default import never changes a held
byte through a notice, and now records the notice PENDING (`held-target`), awaiting the user's `confirm_notice`,
instead of writing nothing. A notice for an ABSENT id is a STANDING row, inert (it refuses no local write and is not in
`redacted_targets()`), instead of no row. A later arrival of that id must SHOW the redaction in both modes, or the
import is refused; a treated arrival is PENDING `standing-arrival` on a default import and applied on a restore —
and origin decides nothing (the hotfix's origin check is removed; RR12's "compare origins" mutant is the cell below).
A store's own export no longer carries a non-applied notice beside its record (research's B1), so the poisoned pair
is built by hand here, as a pre-T4 export carried it. The controls are unchanged.
"""
from __future__ import annotations

import contextlib
import json
import pathlib

import pytest

from veracium import Memory, MemoryConfig, portability as port
from veracium import redaction as R
from veracium.cli import main
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance

U = "u"


def _quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def _mem(tmp_path, name):
    return Memory(llm=_quiet, config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                                                  scope_groups={}, require_source_id=False))


def _prov():
    return Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)


def _lines(p):
    return [json.loads(l) for l in pathlib.Path(p).read_text().splitlines() if l.strip()]


def _write(p, lines):
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return p


def _export_cuts(tmp_path, name, *, edge_id=None, episode_id=None, obj="anything"):
    """A store that holds `edge_id`/`episode_id`, redacts its OWN row and exports: the full file, its notice-only cut
    (header + redaction lines — a file shape the shipped tests already use) and its records-only cut. Returns
    (full, notices, records, that store's origin)."""
    a = _mem(tmp_path, f"{name}.db")
    if edge_id:
        a.store.add_edge(Edge(id=edge_id, user_id=U, subject="user", relation="likes", object=obj, provenance=_prov()))
        a.redact(U, edge_id=edge_id, reason="subject_request")
    if episode_id:
        a.store.add_episode(Episode(id=episode_id, user_id=U, date="2026-09-01", summary="whatever", provenance=_prov()))
        a.redact(U, episode_id=episode_id, reason="subject_request")
    full = tmp_path / f"{name}.jsonl"
    port.export_memory(a.store, U, full)
    origin = a.store.local_origin()
    a.close()
    lines = _lines(full)
    notices = _write(tmp_path / f"{name}-notices.jsonl",
                     [lines[0], *[l for l in lines[1:] if l.get("record") == "redaction"]])
    hb = dict(lines[0]); hb["version"] = 12
    records = _write(tmp_path / f"{name}-records.jsonl", [hb, *[l for l in lines[1:] if l.get("record") != "redaction"]])
    return full, notices, records, origin


def _plain_export(tmp_path, name, edge_id, obj):
    s = _mem(tmp_path, f"{name}.db")
    s.store.add_edge(Edge(id=edge_id, user_id=U, subject="user", relation="likes", object=obj, provenance=_prov()))
    f = tmp_path / f"{name}.jsonl"
    port.export_memory(s.store, U, f)
    s.close()
    return f


def _row(store, kind, rid):
    tbl = "edges" if kind == "edge" else "episodes"
    r = store._conn.execute(f"SELECT json FROM {tbl} WHERE id=?", (rid,)).fetchone()
    return None if r is None else r[0]


def _obj(store, edge_id):
    j = _row(store, "edge", edge_id)
    return None if j is None else json.loads(j)["object"]


def _redaction_rows(store, target_id):
    return store._conn.execute("SELECT COUNT(*) FROM redactions WHERE target_id=?", (target_id,)).fetchone()[0]


def _states(store, target_id):
    """T4: the notice rows for a target as (state, pending_reason)."""
    return store._conn.execute("SELECT state, pending_reason FROM redactions WHERE target_id=? ORDER BY id",
                               (target_id,)).fetchall()


def _applied(store, target_id):
    """T4: the APPLIED rows (attestations) for a target — what "redacted here" means; a pending notice is not one."""
    return store._conn.execute("SELECT COUNT(*) FROM redactions WHERE target_id=? AND state='applied'",
                               (target_id,)).fetchone()[0]


@contextlib.contextmanager
def _permitted(what):
    """An operation the hotfix must PERMIT, asserted as such: a refusal of it fails as an ASSERTION naming the
    permission, never as an escaping domain ValueError (round-4 IO-II-7: the mutation campaign counts only assertion
    and expected-refusal failures as kills, so a permission a mutant takes away must be asserted, not merely run).
    Only a DOMAIN refusal (`refused: …`) is that observation; any other exception propagates as itself. A context
    manager, not a wrapper taking the function: the call stays a direct `import_memory(...)` / `add_edge(...)` call,
    which the call-site censuses (0005's import dispositions among them) find by its name."""
    try:
        yield
    except ValueError as x:
        if not str(x).startswith("refused:"):
            raise
        raise AssertionError(f"the hotfix must permit {what}; it was refused: {x}") from x


def _own_fact(tmp_path, name="victim.db", edge_id="e-own", obj="Lisbon"):
    v = _mem(tmp_path, name)
    v.store.add_edge(Edge(id=edge_id, user_id=U, subject="user", relation="lives_in", object=obj, provenance=_prov()))
    return v


# ------------------------------------------------------------------------------------------- arm 1: a held record
def test_an_untrusted_notice_never_redacts_the_users_own_held_fact(tmp_path):
    victim = _own_fact(tmp_path)
    before = _row(victim.store, "edge", "e-own")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-own")
    r = port.import_memory(victim.store, notices)                      # DEFAULT mode
    assert _row(victim.store, "edge", "e-own") == before               # the whole held row, byte for byte
    assert _states(victim.store, "e-own") == [("pending", "held-target")]
    assert r["notices_applied"] == 0 and r["notices_standing"] == 0
    assert r["notices_not_applied"] == [["edge", "e-own", "held-target"]] and r["inconsistent_notices"] == []
    victim.close()


def test_an_untrusted_notice_never_redacts_a_held_episode(tmp_path):
    victim = _mem(tmp_path, "victim.db")
    victim.store.add_episode(Episode(id="ep-own", user_id=U, date="2026-09-02", summary="my own day", provenance=_prov()))
    before = _row(victim.store, "episode", "ep-own")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", episode_id="ep-own")
    r = port.import_memory(victim.store, notices)
    assert _row(victim.store, "episode", "ep-own") == before
    assert _states(victim.store, "ep-own") == [("pending", "held-target")]
    assert r["notices_not_applied"] == [["episode", "ep-own", "held-target"]]
    victim.close()


def test_the_victims_exact_record_in_the_file_does_not_unlock_the_notice(tmp_path):
    """The attacker who holds the victim's export puts the victim's EXACT record beside the notice: the record is
    skipped as equal to the held one, so it is in the file but not inserted — the notice must still not apply."""
    victim = _own_fact(tmp_path)
    before = _row(victim.store, "edge", "e-own")
    leaked = tmp_path / "victim-export.jsonl"
    port.export_memory(victim.store, U, leaked)
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-own")
    vl, nl = _lines(leaked), _lines(notices)
    crafted = _write(tmp_path / "crafted.jsonl", [nl[0], *[l for l in vl[1:] if l.get("id") == "e-own"], *nl[1:]])
    try:
        r = port.import_memory(victim.store, crafted)
    except ValueError:
        r = None                                                       # refusing the whole file is also fail-closed
    assert _row(victim.store, "edge", "e-own") == before and _applied(victim.store, "e-own") == 0
    if r is not None:
        assert r["notices_applied"] == 0 and ["edge", "e-own", "held-target"] in r["notices_not_applied"]
    victim.close()


def test_a_held_different_version_under_an_untrusted_notice_is_kept_and_reported(tmp_path):
    """Accepted 0041 redacted a held DIFFERENT version 'anyway' under a file's notice; on the default path the held
    version is now kept, the incoming copy is still not written, and the target is reported as NOT applied — never as
    `inconsistent` (that key says the held version was redacted)."""
    victim = _own_fact(tmp_path)
    before = _row(victim.store, "edge", "e-own")
    full, _notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-own")
    r = port.import_memory(victim.store, full)
    assert _row(victim.store, "edge", "e-own") == before and _applied(victim.store, "e-own") == 0
    assert r["notices_applied"] == 0 and r["notices_not_applied"] == [["edge", "e-own", "held-target"]]
    assert r["inconsistent_notices"] == []
    victim.close()


# --------------------------------------------------------------------------- arms 2 and 3: an absent id (standing)
def test_an_untrusted_notice_for_an_absent_id_leaves_an_inert_standing_row(tmp_path):
    """T4: an absent target's notice is STANDING (the hotfix wrote no row) — and inert: not in redacted_targets(), and
    the user's own write of the id is admitted."""
    victim = _mem(tmp_path, "victim.db")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-later")
    r = port.import_memory(victim.store, notices)
    assert r["notices_standing"] == 1 and r["notices_applied"] == 0 and r["notices_not_applied"] == []
    assert _states(victim.store, "e-later") == [("standing", None)]
    assert "e-later" not in victim.store.redacted_targets(U, "edge")
    with _permitted("the user's own write of a standing notice's id"):
        victim.store.add_edge(Edge(id="e-later", user_id=U, subject="user", relation="lives_in", object="Porto",
                                   provenance=_prov()))
    assert _obj(victim.store, "e-later") == "Porto"
    victim.close()


def test_a_later_unredacted_record_of_that_id_is_refused_whole_and_nothing_is_redacted(tmp_path):
    """T4 (§11.6.7: "a standing notice, then an arrival of its id carrying content: the import refused"): the hotfix
    admitted the later record because it wrote no standing row; the standing notice now refuses an arrival that does
    not show the redaction — content never lands under a notice, and nothing is redacted."""
    victim = _mem(tmp_path, "victim.db")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-x")
    with _permitted("a notice-only default import"):
        port.import_memory(victim.store, notices)
    with pytest.raises(ValueError, match="arrives UNREDACTED under a standing redaction notice"):
        port.import_memory(victim.store, _plain_export(tmp_path, "third", "e-x", "tea"))
    assert _row(victim.store, "edge", "e-x") is None and _states(victim.store, "e-x") == [("standing", None)]
    victim.close()


# --------------------------------------------- (i) and (ii): a standing notice the earlier code already wrote
def _legacy_standing(tmp_path, store, edge_id):
    """A standing notice exactly as the earlier code's default import wrote it (main since 8ea59e7, never released; its
    commit had no scope narrowing): through the
    primitive's restore scope, which is still the path that writes one. Returns that notice's origin."""
    _full, notices, _recs, origin = _export_cuts(tmp_path, f"legacy-{edge_id}", edge_id=edge_id)
    r = port.import_memory(store, notices, restore=True)
    assert r["notices_standing"] == 1 and _redaction_rows(store, edge_id) == 1
    return origin


def test_i_a_legacy_standing_notice_never_refuses_the_users_own_write(tmp_path):
    victim = _mem(tmp_path, "victim.db")
    _legacy_standing(tmp_path, victim.store, "e-held-later")
    assert "e-held-later" not in victim.store.redacted_targets(U, "edge")
    with _permitted("the user's own edge write under a standing notice"):
        victim.store.add_edge(Edge(id="e-held-later", user_id=U, subject="user", relation="lives_in", object="Porto",
                                   provenance=_prov()))
    before = _row(victim.store, "edge", "e-held-later")
    assert json.loads(before)["object"] == "Porto"
    # the NEXT unrelated default import leaves that local record alone: it is not a record that import inserts
    with _permitted("an unrelated default import beside a local record under a standing notice"):
        port.import_memory(victim.store, _plain_export(tmp_path, "unrelated", "e-other", "tea"))
    assert _row(victim.store, "edge", "e-held-later") == before
    victim.close()


def test_i_a_legacy_standing_notice_never_refuses_the_users_own_episode_write(tmp_path):
    victim = _mem(tmp_path, "victim.db")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "legacy-ep", episode_id="ep-later")
    assert port.import_memory(victim.store, notices, restore=True)["notices_standing"] == 1
    with _permitted("the user's own episode write under a standing notice"):
        victim.store.add_episode(Episode(id="ep-later", user_id=U, date="2026-09-03", summary="mine", provenance=_prov()))
    assert json.loads(_row(victim.store, "episode", "ep-later"))["summary"] == "mine"
    assert "ep-later" not in victim.store.redacted_targets(U, "episode")
    victim.close()


def test_ii_an_unredacted_default_arrival_under_a_standing_notice_is_refused_whole(tmp_path):
    """Refused by the fixed point (the record does not show the redaction) — never by origin, which T4 removed."""
    victim = _mem(tmp_path, "victim.db")
    _legacy_standing(tmp_path, victim.store, "e-x")
    with pytest.raises(ValueError, match="arrives UNREDACTED under a standing redaction notice"):
        port.import_memory(victim.store, _plain_export(tmp_path, "third", "e-x", "tea"))
    assert _row(victim.store, "edge", "e-x") is None                  # nothing written
    assert _states(victim.store, "e-x") == [("standing", None)]       # still standing
    victim.close()


def test_ii_a_default_REDACTED_arrival_from_another_origin_is_pending_origin_decides_nothing(tmp_path):
    """INV-RR12's "compare origins" mutant cell (T4 removed the hotfix's origin check): store B's arrival of that id
    already SHOWS the redaction, so the fixed point is satisfied and ONLY an origin rule could refuse it. It is
    admitted, and the standing notice from A is PENDING `standing-arrival` on it — never applied on a default import,
    never refused by origin (a legitimate B-over-A notice must not misfire)."""
    victim = _mem(tmp_path, "victim.db")
    _legacy_standing(tmp_path, victim.store, "e-x")
    _full, _n, b_records, _ob = _export_cuts(tmp_path, "b", edge_id="e-x", obj="B's own value")
    with _permitted("a treated default arrival from another origin under a standing notice"):
        r = port.import_memory(victim.store, b_records)                # DEFAULT
    assert r["notices_applied"] == 0 and ["edge", "e-x", "standing-arrival"] in r["notices_not_applied"]
    assert _states(victim.store, "e-x") == [("pending", "standing-arrival")]
    assert _obj(victim.store, "e-x") == R.MARKER                      # B's own treated copy, as it arrived
    victim.close()


def test_ii_a_default_arrival_from_the_notices_own_origin_is_pending_not_applied(tmp_path):
    """T4: on a default import even the notice's own source's treated record leaves the notice PENDING — an
    attestation of data this store then holds, on an untrusted file's word, is the user's to confirm. The record
    arrives treated; nothing held changes."""
    victim = _mem(tmp_path, "victim.db")
    _full, notices, records, _origin = _export_cuts(tmp_path, "src", edge_id="e-red", obj="night shifts at the Grand")
    assert port.import_memory(victim.store, notices, restore=True)["notices_standing"] == 1
    r = port.import_memory(victim.store, records)                      # DEFAULT: the source's own record arrives
    assert r["notices_applied"] == 0 and _states(victim.store, "e-red") == [("pending", "standing-arrival")]
    assert _obj(victim.store, "e-red") == R.MARKER and "Grand" not in _row(victim.store, "edge", "e-red")
    victim.close()


def test_ii_a_treated_default_arrival_under_a_standing_notice_is_admitted(tmp_path):
    """An HONEST flow for the mutation campaign (T4): a record that SHOWS its standing notice's redaction, arriving by a
    default import, is admitted and stored treated — whatever the notice's state then reads (pending on the default
    path, applied under a restore scope), so this asserts only the admission, which no protection may take away."""
    victim = _mem(tmp_path, "victim.db")
    _full, notices, records, _origin = _export_cuts(tmp_path, "src", edge_id="e-red", obj="night shifts at the Grand")
    assert port.import_memory(victim.store, notices, restore=True)["notices_standing"] == 1
    with _permitted("a treated default arrival under a standing notice"):
        port.import_memory(victim.store, records)
    assert _obj(victim.store, "e-red") == R.MARKER and "Grand" not in _row(victim.store, "edge", "e-red")
    victim.close()


def test_ii_on_restore_completion_needs_an_inserted_shown_record_and_not_its_origin(tmp_path):
    """A standing notice from A; B's OWN redacted copy of that id arrives on a restore (origin B, the record treated):
    completed — restore asks for an inserted record that shows the redaction, never for the notice's origin."""
    victim = _mem(tmp_path, "victim.db")
    _legacy_standing(tmp_path, victim.store, "e-x")
    _full, _n, b_records, _ob = _export_cuts(tmp_path, "b", edge_id="e-x", obj="B's own value")
    r = port.import_memory(victim.store, b_records, restore=True)
    assert r["notices_applied"] == 1 and _obj(victim.store, "e-x") == R.MARKER
    victim.close()


def test_ii_an_unredacted_arrival_under_a_standing_notice_refuses_even_on_restore(tmp_path):
    """The fixed-point rule at the arrival loop, the owner's ruling: an inserted record that does NOT show the
    redaction refuses the import whole, in both modes — completing it could destroy it, admitting it would land
    content the notice says was redacted. Nothing written; the notice stays standing."""
    victim = _mem(tmp_path, "victim.db")
    _legacy_standing(tmp_path, victim.store, "e-x")
    with pytest.raises(ValueError, match="arrives UNREDACTED under a standing redaction notice"):
        port.import_memory(victim.store, _plain_export(tmp_path, "third", "e-x", "tea"), restore=True)
    assert _row(victim.store, "edge", "e-x") is None
    assert _states(victim.store, "e-x") == [("standing", None)]
    victim.close()


# ------------------------------------- case 7 (research's probe of candidate 1): the hostile notice rides an export
def _poisoned_export(tmp_path):
    """A store the earlier code poisoned (a legacy standing notice for e-mine), whose user — admitted by (i) — writes
    their own e-mine. T4 (research's B1): its OWN export no longer carries the standing notice, whose target it carries,
    so the poisoned pair is built here as a pre-T4 export carried it — the hostile notice beside the user's UNTREATED
    fact — and every case below is the attacker's (or the old export's) file."""
    v = _mem(tmp_path, "poisoned.db")
    _legacy_standing(tmp_path, v.store, "e-mine")
    with _permitted("the user's own edge write under a legacy standing notice"):
        v.store.add_edge(Edge(id="e-mine", user_id=U, subject="user", relation="lives_in", object="Lisbon",
                              provenance=_prov()))
    own = tmp_path / "own.jsonl"
    port.export_memory(v.store, U, own)
    assert not [l for l in _lines(own)[1:] if l.get("record") == "redaction"], "B1: the own export carried the notice"
    _full, legacy_notices, _r, _o = _export_cuts(tmp_path, "legacy-e-mine-again", edge_id="e-mine")
    notice = [l for l in _lines(legacy_notices)[1:] if l.get("record") == "redaction"]
    head = dict(_lines(legacy_notices)[0])
    f = _write(tmp_path / "poisoned.jsonl", [head, *_lines(own)[1:], *notice])
    return v, f


def test_7a_a_poisoned_export_default_imported_refuses_and_redacts_nothing(tmp_path):
    """The file pairs the notice with the user's UNREDACTED fact: refused whole (the owner's ruling) — never applied."""
    v, f = _poisoned_export(tmp_path); v.close()
    second = _mem(tmp_path, "second.db")
    with pytest.raises(ValueError, match="UNREDACTED beside a redaction notice"):
        port.import_memory(second.store, f)
    assert _row(second.store, "edge", "e-mine") is None and _redaction_rows(second.store, "e-mine") == 0
    second.close()


def test_7b_a_poisoned_export_restored_into_a_fresh_store_refuses_and_redacts_nothing(tmp_path):
    v, f = _poisoned_export(tmp_path); v.close()
    fresh = _mem(tmp_path, "fresh.db")
    with pytest.raises(ValueError, match="UNREDACTED beside a redaction notice"):
        port.import_memory(fresh.store, f, restore=True)
    assert _row(fresh.store, "edge", "e-mine") is None and _redaction_rows(fresh.store, "e-mine") == 0
    fresh.close()


def test_7c_a_poisoned_store_restoring_its_own_export_refuses_and_keeps_the_fact(tmp_path):
    v, f = _poisoned_export(tmp_path)
    before = _row(v.store, "edge", "e-mine")
    with pytest.raises(ValueError, match="UNREDACTED beside a redaction notice"):
        port.import_memory(v.store, f, restore=True)
    assert _row(v.store, "edge", "e-mine") == before
    v.close()


def test_7_the_default_path_reports_a_held_target_before_it_would_refuse(tmp_path):
    """On the default path a HELD target beside its own unredacted copy (the victim's exact record under a hostile
    notice) is PENDING held-target and never refused — nothing lands, nothing is destroyed, and an ordinary import of
    the victim's own data is not blocked."""
    v, f = _poisoned_export(tmp_path)
    before = _row(v.store, "edge", "e-mine")
    with _permitted("a default import of the victim's own export"):
        r = port.import_memory(v.store, f)
    assert _row(v.store, "edge", "e-mine") == before and ["edge", "e-mine", "held-target"] in r["notices_not_applied"]
    v.close()


# ------------------------------------------------------------------------------------------- the controls
def test_a_redacted_record_arriving_new_is_still_redacted_in_the_same_transaction(tmp_path):
    """The propagation 0041 §4g exists for, on the default path: a record this import INSERTS arrives with its notice
    and is written in its treated shape, attested here."""
    full, _notices, _recs, _o = _export_cuts(tmp_path, "src", edge_id="e-red", obj="night shifts at the Grand")
    dst = _mem(tmp_path, "dst.db")
    r = port.import_memory(dst.store, full)
    assert r["notices_applied"] == 1 and r["notices_not_applied"] == [] and r["inconsistent_notices"] == []
    assert _obj(dst.store, "e-red") == R.MARKER and "Grand" not in _row(dst.store, "edge", "e-red")
    assert _redaction_rows(dst.store, "e-red") == 1
    dst.close()


def test_a_trusted_restore_of_a_newer_backup_still_redacts_the_held_older_record(tmp_path):
    """Restore is the operator's own history: a newer backup whose record is redacted, restored over an older store
    holding it unredacted, applies the notice (the file SHOWS it), exactly as before."""
    held = _own_fact(tmp_path, "held.db")
    full, _notices, _recs, _o = _export_cuts(tmp_path, "own", edge_id="e-own")
    r = port.import_memory(held.store, full, restore=True)
    assert r["notices_applied"] == 1 and _obj(held.store, "e-own") == R.MARKER and r["notices_not_applied"] == []
    held.close()


def test_a_notice_only_restore_onto_a_held_record_is_not_applied(tmp_path):
    """The fixed-point rule narrows restore for exactly one shape: a notice with no record beside it — which a genuine
    export never produces — names a held record and is reported, never applied."""
    held = _own_fact(tmp_path, "held.db")
    before = _row(held.store, "edge", "e-own")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "own", edge_id="e-own")
    r = port.import_memory(held.store, notices, restore=True)
    assert _row(held.store, "edge", "e-own") == before
    assert r["notices_not_applied"] == [["edge", "e-own", "record-not-in-file"]]
    held.close()


def test_a_repeat_untrusted_import_stays_inert(tmp_path):
    victim = _own_fact(tmp_path)
    before = _row(victim.store, "edge", "e-own")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-own")
    for _ in range(2):
        r = port.import_memory(victim.store, notices)
        assert r["notices_applied"] == 0 and r["notices_standing"] == 0
    assert _row(victim.store, "edge", "e-own") == before
    assert _states(victim.store, "e-own") == [("pending", "held-target")]     # one row, its reason kept (IO-II-1)
    victim.close()


def test_the_cli_prints_the_notices_it_did_not_apply(tmp_path, capsys):
    victim = _own_fact(tmp_path)
    victim.close()
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-own")
    assert main(["import", str(notices), "--db", str(tmp_path / "victim.db")]) == 0
    out = capsys.readouterr().out
    assert "1 redaction notice(s) PENDING your confirmation, NOT applied" in out and "edge e-own" in out
    assert main(["import", str(notices), "--restore", "--db", str(tmp_path / "other.db")]) == 0
    assert "NOT applied" not in capsys.readouterr().out


def test_the_attest_only_branch_is_restore_only_on_a_default_import(tmp_path):
    """With no copy in the file, a notice ATTESTS a held record that already shows the redaction — on a RESTORE. On the
    default path the created-only gate decides first, so a held record that merely looks redacted (an unattested
    marker) is never attested on an untrusted file's word: that would make it write-refused and hide it."""
    held = _mem(tmp_path, "held.db")
    held.store.add_edge(Edge(id="e-own", user_id=U, subject="user", relation="lives_in", object="Lisbon", provenance=_prov()))
    held.store._conn.execute("UPDATE edges SET json=json_set(json, '$.object', ?) WHERE id='e-own'", (R.MARKER,))
    held.store._conn.commit()                                          # an unattested marker row, held here
    assert "e-own" not in held.store.redacted_targets(U, "edge")
    _full, notices, _recs, _o = _export_cuts(tmp_path, "att", edge_id="e-own")
    r = port.import_memory(held.store, notices)                        # DEFAULT
    assert r["notices_not_applied"] == [["edge", "e-own", "held-target"]] and _applied(held.store, "e-own") == 0
    with _permitted("the user's own write under a pending notice"):
        held.store.add_edge(Edge(id="e-own", user_id=U, subject="user", relation="lives_in", object="Porto",
                                 provenance=_prov()))
    assert _obj(held.store, "e-own") == "Porto"                        # still writable: nothing attested it
    held.close()


def test_the_primitive_defaults_to_the_narrow_scope(tmp_path):
    """A plan that names no `notice_scope` reaches the commit primitive by another route than the import: it gets the
    NARROW scope (fail closed) — a notice for a record the commit did not insert is not applied and writes nothing."""
    victim = _own_fact(tmp_path)
    before = _row(victim.store, "edge", "e-own")
    notice = {"origin": "o", "source_user": U, "source_event_ref": "u:1", "target_kind": "edge", "target_id": "e-own",
              "fields": ["object"], "marker_version": 1, "reason": "subject_request", "_shown": True}
    r = victim.store.commit_outcome_import_plan(U, {"edges": [], "episodes": [], "contributions": [], "redactions": [notice]},
                                                {"edge_ids": {}, "episode_records": {}, "chain_heads": {},
                                                 "contribution_state": {}})
    assert r["notices_applied"] == 0 and r["notices_not_applied"] == [["edge", "e-own", "held-target"]]
    assert _row(victim.store, "edge", "e-own") == before and _applied(victim.store, "e-own") == 0
    victim.close()
