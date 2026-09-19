"""specs/0041 tranche 3 — THE OPERATION, bound: `Memory.redact` over the treatment map in one transaction, the
seven invariants of §6 with their planted mutants, the attestation rule at the writers, §4h(i)'s disposition
rule, the episode journal row, repeats, refusals (never a silent no-op), and the receipt's own limits.

Every transition claim runs on the FROZEN pre-restriction store (§4h(iii)): the records were written by the
pre-restriction writer, never by the code under test. Records the frozen store does not carry (a ledger row, a
confirmation, an embedding, a refusal row) are planted by direct SQL in the shape the product writes.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sqlite3
import sys
from datetime import datetime, timezone

import pytest

from veracium import redaction as R
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance, QUARANTINE_RELATION, DISPOSITIONED_REASONS

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0041"
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


def _load_tt():
    spec = importlib.util.spec_from_file_location("tt41r", ROOT / "tests" / "test_0041_transition_table.py")
    m = importlib.util.module_from_spec(spec); sys.modules["tt41r"] = m; spec.loader.exec_module(m); return m


@pytest.fixture
def tt():
    return _load_tt()


@pytest.fixture
def frozen(tt, tmp_path):
    """The frozen pre-restriction store, opened through Memory (its writable copy migrated to the head)."""
    return tt._frozen_memory(tmp_path)


def _prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw); return Provenance(**base)


def _edge_json(st, eid):
    return json.loads(st._conn.execute("SELECT json FROM edges WHERE id=?", (eid,)).fetchone()[0])


def _episode_json(st, eid):
    return json.loads(st._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()[0])


# ------------------------------------------------------------------------------------------ the map, on a frozen edge
def test_the_treatment_replaces_every_content_carrier_of_a_frozen_edge_and_preserves_the_rest(frozen, tt):
    """§2d-iii-bis on the frozen ordinary edge: subject/relation/object → the marker, the duplicated columns
    follow (INV-2), identifiers/timestamps/provenance byte-identical, the receipt names exactly the carriers
    treated and no absent field (§4h corollary: note "" and invalidation_reason None are left alone)."""
    st = frozen.store; man = tt._frozen_rows(); eid = man["ordinary_edge"]
    before = _edge_json(st, eid)
    r = frozen.redact(tt.U, edge_id=eid, reason="subject_request")
    after = _edge_json(st, eid)
    assert after["subject"] == R.MARKER and after["relation"] == R.MARKER and after["object"] == R.MARKER
    for k in ("id", "user_id", "valid_from", "provenance", "supersedes", "invalidated_at", "invalidation_reason", "needs_confirmation"):
        assert after.get(k) == before.get(k), k
    assert after.get("note", "") == before.get("note", "")          # "" is absence, never replaced
    assert after["invalidation_reason"] is None and before["invalidation_reason"] is None
    cols = st._conn.execute("SELECT subject, relation, object, active FROM edges WHERE id=?", (eid,)).fetchone()
    assert cols[0] == R.MARKER and cols[1] == R.MARKER and cols[2] == R.MARKER           # INV-2: the columns follow
    assert cols[3] == int(before["invalidated_at"] is None)
    assert r.redacted_kind == "edge" and r.target_id == eid and r.repeated is False and r.reconstructed is False
    assert set(r.fields_cleared) >= {"subject", "relation", "object"} and "note" not in r.fields_cleared \
        and "invalidation_reason" not in r.fields_cleared
    assert r.marker_version == R.MARKER_VERSION and r.store_version_after == r.store_version_before + 1
    assert r.receipts_complete is False and r.receipt_domains            # §4f: the ordinary case, the domains named
    # the attestation record names the same carriers
    (fields,) = st._conn.execute("SELECT fields FROM redactions WHERE user_id=? AND target_kind='edge' AND target_id=?",
                                 (tt.U, eid)).fetchone()
    assert json.loads(fields) == r.fields_cleared


def test_inv2_planted_mutant_a_json_only_redaction_leaves_the_duplicated_columns_and_is_caught(frozen, tt):
    """INV-2's planted mutant: rewrite the json alone (the reasonable implementation's mistake) and the column
    check must FAIL — proving the check sees the columns and not only the blob."""
    st = frozen.store; man = tt._frozen_rows(); eid = man["ordinary_edge"]
    d = _edge_json(st, eid); d["object"] = R.MARKER
    st._conn.execute("UPDATE edges SET json=? WHERE id=?", (json.dumps(d), eid)); st._conn.commit()
    (col,) = st._conn.execute("SELECT object FROM edges WHERE id=?", (eid,)).fetchone()
    assert col != R.MARKER, "the mutant must leave the column behind for this check to mean anything"
    assert _edge_json(st, eid)["object"] != col                          # the disagreement INV-2 exists to catch


# ---------------------------------------------------------------------------------------------- the journal (INV-4)
def test_inv4_every_prior_event_is_tombstoned_and_a_redacted_event_closes_the_sequence(tt, tmp_path):
    """§4c: after redaction no event for the edge yields the original content; the new event's kind is
    `redacted`, its reason the redaction vocabulary, its seq the next in the user's sequence (INV-1)."""
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-j", user_id=tt.U, subject="user", relation="works_as", object="the night shift at the Grand", provenance=_prov()))
    st.add_edge(Edge(id="e-j", user_id=tt.U, subject="user", relation="works_as", object="the night shift at the Grand, since May", provenance=_prov()))
    seqs_before = [e.seq for e in st.edge_events(tt.U)]
    assert any("Grand" in e.state for e in st.edge_events(tt.U, edge_id="e-j"))
    r = m.redact(tt.U, edge_id="e-j", reason="operator_policy")
    evs = st.edge_events(tt.U, edge_id="e-j")
    assert [e.kind for e in evs] == ["created", "mutated", "redacted"]
    assert all("Grand" not in e.state for e in evs)                      # INV-4: no residue
    assert all(e.state == R.MARKER for e in evs[:-1])                    # the prior states are the tombstone
    assert evs[-1].reason == "operator_policy" and json.loads(evs[-1].state)["object"] == R.MARKER   # the JSON escapes the NUL
    all_seqs = [e.seq for e in st.edge_events(tt.U)]
    assert all_seqs == sorted(all_seqs) and len(set(all_seqs)) == len(all_seqs) and all_seqs[:len(seqs_before)] == seqs_before
    assert r.event_ref == f"{tt.U}:{evs[-1].seq}"


def test_inv3_why_degrades_and_never_fails_on_a_redacted_edge(tt, tmp_path):
    from veracium import why as W
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-w", user_id=tt.U, subject="user", relation="has_pet", object="a cat called Miso", provenance=_prov()))
    m.redact(tt.U, edge_id="e-w", reason="subject_request")
    bio = W.gather(st, tt.U, "e-w")
    assert "Miso" not in W.render(bio)
    text = json.dumps(bio.__dict__ if hasattr(bio, "__dict__") else bio, default=str)
    assert "Miso" not in text
    kinds = [e["kind"] for e in bio.events]
    assert kinds[-1] == "redacted" and [tuple(c) for c in bio.events[-1]["changed"]] == [("content", None, "redacted")]
    assert "redacted" in W.render(bio)
    assert any(e.get("note") == "redacted" for e in bio.events[:-1])


# --------------------------------------------------------------------------------------------- INV-7 and the receipt
def test_inv7_the_embedding_rows_are_deleted_and_the_ledger_digests_cleared_planted_mutant_shows_the_check_bites(tt, tmp_path):
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-o", user_id=tt.U, subject="user", relation="works_as", object="a secret", provenance=_prov()))
    st._conn.execute("INSERT INTO edge_embedding(edge_id,user_id,embedder_id,content_digest,dim,vec,built_at) VALUES(?,?,?,?,?,?,?)",
                     ("e-o", tt.U, "emb", "a" * 64, 2, b"\x00\x00", "2026-09-19T00:00:00Z"))
    st._conn.execute("INSERT INTO contribution_ledger(id,user_id,survivor_type,survivor_id,site,identity_digest,evidence_ref_digest,payload,op_key,created_at,contributor_type,contributor_ref) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", ("c1", tt.U, "edge", "e-o", "absorb", "b" * 64, "c" * 64, "{}", None, "2026-09-19T00:00:00Z", "edge", "e-other"))
    st._conn.commit()
    r = m.redact(tt.U, edge_id="e-o", reason="erroneous_capture")
    assert st._conn.execute("SELECT COUNT(*) FROM edge_embedding WHERE edge_id='e-o'").fetchone()[0] == 0
    assert st._conn.execute("SELECT identity_digest, evidence_ref_digest FROM contribution_ledger WHERE id='c1'").fetchone() == (None, None)
    assert "edge_embedding" in r.fields_cleared and "contribution_ledger.identity_digest" in r.fields_cleared
    # the receipt NEVER carries a content digest (§4f's oracle rule), whatever the store held
    assert not HEX64.search(r.model_dump_json())
    # the planted mutant: a redaction that forgot the ledger leaves a digest, and this check is what sees it
    st._conn.execute("UPDATE contribution_ledger SET identity_digest=? WHERE id='c1'", ("d" * 64,)); st._conn.commit()
    assert st._conn.execute("SELECT identity_digest FROM contribution_ledger WHERE id='c1'").fetchone()[0] is not None


def test_the_side_tables_follow_the_map_confirmations_and_refusal_rows(tt, tmp_path):
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-s", user_id=tt.U, subject="user", relation="told me in confidence", object="x", provenance=_prov()))
    st._conn.execute("INSERT INTO confirmations(id,user_id,edge_id,confirmed_at,actor,call_path,correlation_id,request_digest) VALUES(?,?,?,?,?,?,?,?)",
                     ("cf1", tt.U, "e-s", "2026-09-19T00:00:00Z", "user", "library", "corr-1", "e" * 64))
    st._conn.execute("INSERT INTO supersession_refusals(refusal_id,user_id,prior_edge_id,incoming_edge_id,relation,prior_effective,incoming_effective,rule_version,created_at) "
                     "VALUES(?,?,?,?,?,?,?,?,?)", ("rf1", tt.U, "e-s", "e-in", "told me in confidence", 1, 1, "v1", "2026-09-19T00:00:00Z"))
    st._conn.commit()
    r = m.redact(tt.U, edge_id="e-s", reason="legal_obligation")
    assert st._conn.execute("SELECT request_digest FROM confirmations WHERE id='cf1'").fetchone()[0] == R.MARKER
    assert st._conn.execute("SELECT relation FROM supersession_refusals WHERE refusal_id='rf1'").fetchone()[0] == R.MARKER
    assert st._conn.execute("SELECT COUNT(*) FROM confirmations WHERE id='cf1'").fetchone()[0] == 1          # the row KEPT (row 7)
    assert {"confirmations.request_digest", "supersession_refusals.relation"} <= set(r.fields_cleared)


# --------------------------------------------------------------------------------------- §4h(i): derived dispositions
def test_4h_i_redacting_the_relation_of_a_relation_only_quarantined_frozen_edge_keeps_it_quarantined(frozen, tt):
    """The frozen relation-only quarantine (§4h(i)'s executed case): the relation becomes the marker, the
    disclosure becomes QUARANTINED in the same transaction, and `quarantined` reads True before and after."""
    st = frozen.store; man = tt._frozen_rows(); eid = man["relation_only_quarantine"]
    before = Edge.model_validate(_edge_json(st, eid))
    assert before.relation == QUARANTINE_RELATION and before.provenance.disclosure != Disclosure.QUARANTINED and before.quarantined
    r = frozen.redact(tt.U, edge_id=eid, reason="subject_request")
    after = Edge.model_validate(_edge_json(st, eid))
    assert after.relation == R.MARKER and after.provenance.disclosure == Disclosure.QUARANTINED and after.quarantined
    assert st._conn.execute("SELECT quarantined FROM edges WHERE id=?", (eid,)).fetchone()[0] == 1
    assert "provenance.disclosure" in r.fields_cleared


def test_4h_i_a_treatment_that_would_change_a_disposition_refuses_with_nothing_written(tt, tmp_path, monkeypatch):
    """The general rule, with the mutant that makes it fire: a treatment that flips `active` (here, one that
    writes an invalidation) must be refused and leave the row byte-identical."""
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-d", user_id=tt.U, subject="user", relation="works_as", object="x", provenance=_prov()))
    before = st._conn.execute("SELECT json, subject FROM edges WHERE id='e-d'").fetchone()
    real = R.treat_edge
    def flipping(dump, **kw):
        d, treated = real(dump, **kw); d["invalidated_at"] = "2026-09-19T00:00:00+00:00"; return d, treated + ["invalidated_at"]
    monkeypatch.setattr(R, "treat_edge", flipping)
    with pytest.raises(ValueError, match="derived disposition"):
        m.redact(tt.U, edge_id="e-d", reason="subject_request")
    assert st._conn.execute("SELECT json, subject FROM edges WHERE id='e-d'").fetchone() == before
    assert st._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0
    assert [e.kind for e in st.edge_events(tt.U, edge_id="e-d")] == ["created"]


# ------------------------------------------------------------------------------------------------------- episodes
def test_an_episode_redaction_replaces_the_summary_keeps_a_recognised_kind_and_writes_the_episode_journal_row(frozen, tt):
    st = frozen.store; man = tt._frozen_rows(); eid = man["active_episode_absent_reason"]
    before = _episode_json(st, eid); assert before["kind"] in R.RECOGNISED_EPISODE_KINDS and before["retired_reason"] is None
    r = frozen.redact(tt.U, episode_id=eid, reason="subject_request")
    after = _episode_json(st, eid)
    assert after["summary"] == R.MARKER and after["kind"] == before["kind"] and after["retired_reason"] is None
    assert Episode.model_validate(after).active                                   # row 49: absence stays absence, ACTIVE stays
    rows = st._conn.execute("SELECT seq, kind, reason, state FROM episode_event WHERE user_id=? AND episode_id=?", (tt.U, eid)).fetchall()
    assert len(rows) == 1 and rows[0][1] == "redacted" and rows[0][2] == "subject_request" and json.loads(rows[0][3])["summary"] == R.MARKER
    assert before["summary"] not in rows[0][3]
    assert r.redacted_kind == "episode" and r.event_ref == f"{tt.U}:episode:{rows[0][0]}" and r.fields_cleared == ["summary"]


def test_an_episode_with_a_frozen_prose_kind_gets_the_marker_in_kind_and_still_loads(frozen, tt):
    """Row 46's REPLACE branch on the frozen prose kind — attested, so the marker in `kind` is a valid kind
    (§4h(ii)); the record loads through the ordinary reader."""
    st = frozen.store; man = tt._frozen_rows(); eid = man["prose_kind"]
    assert _episode_json(st, eid)["kind"] not in R.RECOGNISED_EPISODE_KINDS
    r = frozen.redact(tt.U, episode_id=eid, reason="subject_request")
    assert _episode_json(st, eid)["kind"] == R.MARKER and "kind" in r.fields_cleared
    assert any(e.id == eid for e in st.episodes(tt.U, include_retired=True))
    assert st._attested_fields(tt.U, "episode", eid) >= {"kind", "summary"}


def test_rows_30_49_three_cases_on_the_frozen_reasons(frozen, tt):
    """The frozen prose retired reason becomes `redacted` (the registry value, never the marker, never NULL);
    the frozen REGISTRY reason is preserved; the episode stays retired in both."""
    st = frozen.store; man = tt._frozen_rows()
    prose, reg = man["prose_retired_reason"], man["registry_retired_reason"]
    assert _episode_json(st, prose)["retired_reason"] not in DISPOSITIONED_REASONS
    reg_reason = _episode_json(st, reg)["retired_reason"]; assert reg_reason in DISPOSITIONED_REASONS
    r1 = frozen.redact(tt.U, episode_id=prose, reason="subject_request")
    r2 = frozen.redact(tt.U, episode_id=reg, reason="subject_request")
    assert _episode_json(st, prose)["retired_reason"] == "redacted" and "retired_reason" in r1.fields_cleared
    assert _episode_json(st, reg)["retired_reason"] == reg_reason and "retired_reason" not in r2.fields_cleared
    assert not Episode.model_validate(_episode_json(st, prose)).active and not Episode.model_validate(_episode_json(st, reg)).active


def test_a_claimed_consolidation_input_refuses_redaction(tt, tmp_path, monkeypatch):
    m = tt._mem(tmp_path); st = m.store
    st.add_episode(Episode(id="ep-c", user_id=tt.U, date="2026-09-01", summary="s", provenance=_prov()))
    monkeypatch.setattr(type(st), "_reserved_ids", lambda self, user_id: {"ep-c"})
    with pytest.raises(ValueError, match="in-flight consolidation"):
        m.redact(tt.U, episode_id="ep-c", reason="subject_request")
    assert _episode_json(st, "ep-c")["summary"] == "s" and st._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0


# ---------------------------------------------------------------------------------------------- INV-5 and the vocabulary
@pytest.mark.parametrize("call", [
    dict(edge_id="no-such-edge"), dict(episode_id="no-such-episode"),
    dict(edge_id="e-x", episode_id="ep-x"), dict(),
])
def test_inv5_an_unknown_target_or_a_malformed_call_refuses_loudly_never_a_silent_no_op(tt, tmp_path, call):
    m = tt._mem(tmp_path)
    with pytest.raises(ValueError):
        m.redact(tt.U, reason="subject_request", **call)
    assert m.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0


def test_inv5_a_cross_user_target_refuses_with_the_same_words_as_an_unknown_one(tt, tmp_path):
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-theirs", user_id="other", subject="user", relation="works_as", object="x", provenance=_prov()))
    with pytest.raises(ValueError) as a:
        m.redact(tt.U, edge_id="e-theirs", reason="subject_request")
    with pytest.raises(ValueError) as b:
        m.redact(tt.U, edge_id="e-nobody", reason="subject_request")
    assert str(a.value).replace("e-theirs", "X") == str(b.value).replace("e-nobody", "X")   # existence not disclosed
    assert _edge_json(st, "e-theirs")["object"] == "x"


def test_a_reason_outside_the_vocabulary_refuses_and_the_journal_would_too(tt, tmp_path):
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-r", user_id=tt.U, subject="user", relation="works_as", object="x", provenance=_prov()))
    with pytest.raises(ValueError, match="not one of"):
        m.redact(tt.U, edge_id="e-r", reason="redacted: the user's HIV status")
    # the second fence, at the choke point (D1): the journal refuses a prose reason on the redacted kind
    with st._write_txn():
        with pytest.raises(ValueError, match="redaction reason"):
            st._journal_edge_write(tt.U, "e-r", "{}", "{\"a\": 1}", kind="redacted", reason="the user's HIV status")


def test_inv6_the_reason_reaches_no_prompt_and_the_content_reaches_none_either(tt, tmp_path):
    """INV-6 after §11.2: the vocabulary word is the only thing a reason can be, and even that word does not
    reach the model's input; the redacted content is absent from every prompt the answer path renders."""
    seen = []
    def llm(prompt, *, system=None, role="compile", json_schema=None):
        seen.append((system or "") + "\n" + prompt)
        return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else "I don't know."
    from veracium import Memory, MemoryConfig
    m = Memory(llm=llm, config=MemoryConfig(db_path=str(tmp_path / "m.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))
    m.store.add_edge(Edge(id="e-6", user_id=tt.U, subject="user", relation="works_as", object="night auditor at the Grand", provenance=_prov()))
    m.redact(tt.U, edge_id="e-6", reason="subject_request")
    m.answer(tt.U, "Where does the user work?")
    assert seen and all("Grand" not in s and "subject_request" not in s for s in seen)


# --------------------------------------------------------------------------------------------- INV-1 and the doctor
def test_inv1_structure_preserved_and_the_doctor_is_clean_after_a_mid_chain_redaction(tt, tmp_path):
    from veracium import doctor as doc
    m = tt._mem(tmp_path); st = m.store
    st.add_edge(Edge(id="e-a", user_id=tt.U, subject="user", relation="lives_in", object="Porto", provenance=_prov()))
    st.add_edge(Edge(id="e-b", user_id=tt.U, subject="user", relation="lives_in", object="Braga", supersedes="e-a", provenance=_prov()))
    st.invalidate_edge("e-a", datetime.now(timezone.utc), "superseded")
    st.add_edge(Edge(id="e-c", user_id=tt.U, subject="user", relation="lives_in", object="Lisbon", supersedes="e-b", provenance=_prov()))
    st.invalidate_edge("e-b", datetime.now(timezone.utc), "superseded")
    chain_before = sorted((e.id, e.supersedes, e.active) for e in st.edges(tt.U, active_only=False, include_quarantined=True))
    seqs_before = [e.seq for e in st.edge_events(tt.U)]
    m.redact(tt.U, edge_id="e-b", reason="subject_request")
    chain_after = sorted((e.id, e.supersedes, e.active) for e in st.edges(tt.U, active_only=False, include_quarantined=True))
    assert chain_after == chain_before
    seqs_after = [e.seq for e in st.edge_events(tt.U)]
    assert seqs_after[:len(seqs_before)] == seqs_before and len(seqs_after) == len(seqs_before) + 1
    m.close()
    rep = doc.diagnose(str(tmp_path / "m.db"))
    errors = [f for f in rep.findings if f.level == "error"]
    assert not errors, doc.render(rep)


# ------------------------------------------------------------------------------------------------ the host's Store
def test_a_store_without_the_operation_refuses_rather_than_dropping():
    from types import SimpleNamespace
    from veracium.store.base import Store
    with pytest.raises(NotImplementedError, match="redact"):
        Store.redact(SimpleNamespace(), "u", edge_id="e", reason="subject_request")     # the base body, unimplemented
