"""specs/0041 tranche 4a — THE READERS, bound: the as-of classifier's REDACTED status (distinct from MALFORMED,
after visibility, keyed on the journal's own writes), the resolver's NOT_RETURNABLE / redacted-excluded, recall not
returning an attested-redacted record (edges, episodes, the compiled wiki), describe_procedures reporting `redacted`
under the existing visibility restrictions — and the CONTROL every row carries: a row merely holding the marker
bytes (the frozen unattested marker) is treated by each reader exactly as before.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

import pytest

from veracium import redaction as R
from veracium.asof import MALFORMED, REDACTED, STATUSES, classify_as_of
from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance

ROOT = pathlib.Path(__file__).resolve().parents[1]
U = "u"


def _load_tt():
    spec = importlib.util.spec_from_file_location("tt41rd", ROOT / "tests" / "test_0041_transition_table.py")
    m = importlib.util.module_from_spec(spec); sys.modules["tt41rd"] = m; spec.loader.exec_module(m); return m


@pytest.fixture
def tt():
    return _load_tt()


def _prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw); return Provenance(**base)


def _prompts_llm(seen):
    def llm(prompt, *, system=None, role="compile", json_schema=None):
        seen.append(((system or "") + "\n" + prompt, role))
        if role == "distill":
            return json.dumps({"triples": [], "episode": "x", "instructions": []})
        if role == "compile":
            return "## USER MODEL\n- (compiled)\n"
        return "I don't know."
    return llm


# ------------------------------------------------------------------------------------- the as-of classifier
def test_the_status_set_gained_redacted_and_the_resolver_is_total_over_it():
    assert REDACTED in STATUSES and len(STATUSES) == 8
    from veracium.asof import resolve as rs
    assert rs.RESOLUTION["redacted"] == (rs.NOT_RETURNABLE, rs.TAG_REDACTED_EXCLUDED)


def _classify(st, eid, k, T, view=None, cell=None):
    """The 0030 inputs from the store's own reads: the raw snapshot at txn k and the current state (one read
    window), the way `resolve_as_of` builds them; `cell` replaces the scope cell for the hidden case."""
    import dataclasses
    from veracium.asof import Envelope
    cs = st.current_state(U, eid, principal=None, policy=None)
    if cell is not None:
        cs = dataclasses.replace(cs, scope_cell=cell)
    return classify_as_of(Envelope(U, eid), st.edge_state_at(U, eid, k), cs, T, datetime.now(timezone.utc), view)


def test_an_as_of_read_of_a_redacted_snapshot_is_REDACTED_not_MALFORMED(tt, tmp_path):
    """Before the redaction the snapshot is the tombstone (the marker, not JSON): REDACTED, where the old
    classifier said MALFORMED. At the redaction event itself: REDACTED by kind. The status comes from the
    journal's own writes, not from bytes; the control below shows a well-formed snapshot still classifies."""
    from veracium.asof import GROUNDED_AS_OF
    m = tt._mem(tmp_path); st = m.store
    t0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    st.add_edge(Edge(id="e-as", user_id=U, subject="user", relation="lives_in", object="Porto", valid_from=t0, provenance=_prov()))
    st.add_edge(Edge(id="e-ok", user_id=U, subject="user", relation="has_pet", object="Miso", valid_from=t0, provenance=_prov()))
    txn_before = max(e.txn for e in st.edge_events(U, edge_id="e-as"))
    assert _classify(st, "e-as", txn_before, t0 + timedelta(days=1)).status == GROUNDED_AS_OF      # before: an answer
    m.redact(U, edge_id="e-as", reason="subject_request")
    txn_after = max(e.txn for e in st.edge_events(U, edge_id="e-as"))
    for k in (txn_before, txn_after):
        r = _classify(st, "e-as", k, t0 + timedelta(days=1))
        assert r.status == REDACTED and r.held_at_K is None, (k, r)
    assert st.edge_state_at(U, "e-as", txn_before).state == R.MARKER                     # the tombstone
    assert st.edge_state_at(U, "e-as", txn_after).kind == "redacted"
    assert _classify(st, "e-ok", txn_after, t0 + timedelta(days=1)).status == GROUNDED_AS_OF       # the neighbour: untouched


def test_a_hidden_redacted_record_stays_hidden_the_new_state_is_not_a_disclosure_channel(tt, tmp_path):
    """§4b-iii: 'a new state that is visible where the record was not is a disclosure channel'. With a scope cell
    that is not visible (and the view it was computed for), the classifier answers SCOPE_HIDDEN before REDACTED."""
    from veracium.asof import SCOPE_HIDDEN
    from veracium.asof.carrier import ScopeCell
    m = tt._mem(tmp_path); st = m.store
    t0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    st.add_edge(Edge(id="e-h", user_id=U, subject="user", relation="lives_in", object="Porto", valid_from=t0, provenance=_prov()))
    m.redact(U, edge_id="e-h", reason="subject_request")
    k = max(e.txn for e in st.edge_events(U, edge_id="e-h"))
    class _P:
        origin, source_id = "org-x", "src-x"
    class _View:                       # the classifier reads only user_id and the principal pair (never .visible)
        user_id = U; principal = _P()
    hidden = ScopeCell(visible=False, shape=None, fail_closed=False, principal=("org-x", "src-x"))
    assert _classify(st, "e-h", k, t0 + timedelta(days=1), view=_View(), cell=hidden).status == SCOPE_HIDDEN
    visible = ScopeCell(visible=True, shape=None, fail_closed=False, principal=("org-x", "src-x"))
    assert _classify(st, "e-h", k, t0 + timedelta(days=1), view=_View(), cell=visible).status == REDACTED   # the control


def test_the_control_an_unattested_marker_row_is_not_REDACTED_to_the_classifier(tt, tmp_path):
    """An UNATTESTED marker row — the marker bytes written into the row the pre-restriction way (direct SQL,
    no redaction record) over an edge whose journal holds its `created` event — is not REDACTED to the
    classifier: no attestation, so the leg does not fire and the snapshot classifies as before (§4b: bytes
    confer nothing). The same row is REDACTED the moment a record attests it."""
    m = tt._mem(tmp_path); st = m.store
    t0 = datetime(2026, 9, 1, tzinfo=timezone.utc)
    st.add_edge(Edge(id="e-un", user_id=U, subject="user", relation="lives_in", object="Porto", valid_from=t0, provenance=_prov()))
    d = json.loads(st._conn.execute("SELECT json FROM edges WHERE id='e-un'").fetchone()[0]); d["object"] = R.MARKER
    st._conn.execute("UPDATE edges SET json=?, object=? WHERE id='e-un'", (json.dumps(d), R.MARKER)); st._conn.commit()
    k = max(e.txn for e in st.edge_events(U, edge_id="e-un"))
    r = _classify(st, "e-un", k, t0 + timedelta(days=1))
    # the bytes confer nothing: the snapshot classifies by the ordinary legs (here FENCED_AS_OF — the current
    # row's marker content no longer projects the snapshot's identity), never as REDACTED
    assert r.status in STATUSES and r.status != REDACTED, r
    st._conn.execute("INSERT INTO redactions(id,user_id,target_kind,target_id,fields,marker_version,reason,store_version_before,store_version_after,event_ref,recorded_at) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("r-un", U, "edge", "e-un", json.dumps(["object"]), 1, "subject_request", 1, 2, None, "2026-09-19T00:00:00Z"))
    st._conn.commit()
    assert _classify(st, "e-un", k, t0 + timedelta(days=1)).status == REDACTED       # the record, not the bytes


# ------------------------------------------------------------------------------------------------- recall
def test_recall_does_not_return_an_attested_redacted_edge_or_episode_and_the_control_row_still_renders(tt, tmp_path):
    from veracium import Memory, MemoryConfig
    seen = []
    m = Memory(llm=_prompts_llm(seen), config=MemoryConfig(db_path=str(tmp_path / "m.db"), wiki_recompile_after_writes=1,
                                                          scope_groups={}, require_source_id=False))
    st = m.store
    st.add_edge(Edge(id="e-r1", user_id=U, subject="user", relation="has_pet", object="a cat called Miso", provenance=_prov()))
    st.add_edge(Edge(id="e-r2", user_id=U, subject="user", relation="lives_in", object="Porto", provenance=_prov()))
    st.add_episode(Episode(id="ep-r", user_id=U, date="2026-09-01", summary="the user adopted a cat called Miso", provenance=_prov()))
    tt._legacy_insert_edge(st, Edge(id="e-un", user_id=U, subject="user", relation="works_as", object=R.MARKER, provenance=_prov()))
    m.redact(U, edge_id="e-r1", reason="subject_request"); m.redact(U, episode_id="ep-r", reason="subject_request")
    rec = m.recall(U, "cat Miso Porto")
    ids = {e.id for e in rec.edges}
    assert "e-r1" not in ids and "e-r2" in ids
    assert "e-un" in ids                                               # the CONTROL: an unattested marker row is returned as before
    assert all("Miso" not in (e.object + e.subject + e.relation) for e in rec.edges)
    assert all(ep.id != "ep-r" for ep in getattr(rec, "episodes", []))
    text = rec.grounded + "\n" + rec.unverified
    assert "Miso" not in text
    m.answer(U, "What is the name of my cat?")
    assert seen and all("Miso" not in p for p, _ in seen)              # not in the compile input, not in the gate prompt


def test_the_compiled_wiki_excludes_the_redacted_record(tt, tmp_path):
    from veracium import Memory, MemoryConfig
    seen = []
    m = Memory(llm=_prompts_llm(seen), config=MemoryConfig(db_path=str(tmp_path / "m.db"), wiki_recompile_after_writes=1,
                                                          scope_groups={}, require_source_id=False))
    st = m.store
    st.add_edge(Edge(id="e-w1", user_id=U, subject="user", relation="has_pet", object="a cat called Miso", provenance=_prov()))
    st.add_edge(Edge(id="e-w2", user_id=U, subject="user", relation="lives_in", object="Porto", provenance=_prov()))
    m.redact(U, edge_id="e-w1", reason="subject_request")
    m.answer(U, "Where do I live?")
    compile_inputs = [p for p, role in seen if role == "compile"]
    assert compile_inputs and all("Miso" not in p and R.MARKER not in p for p in compile_inputs)
    assert any("Porto" in p for p in compile_inputs)


# -------------------------------------------------------------------------------------- describe_procedures
def test_describe_procedures_reports_a_redacted_procedure_as_withheld_redacted_and_a_hidden_one_stays_hidden(tt, tmp_path):
    from veracium.procedures import WITHHELD_OUTCOMES
    assert "redacted" in WITHHELD_OUTCOMES
    m = tt._mem(tmp_path); st = m.store
    proc = Edge(id="e-p", user_id=U, subject="user", relation="prefers", object="commit messages in the imperative",
                provenance=_prov(record_kind="procedural", basis="stated"))
    st.add_edge(proc)
    before = m.describe_procedures(U)
    assert any(d.edge_id == "e-p" for d in before.descriptions), before
    m.redact(U, edge_id="e-p", reason="subject_request")
    after = m.describe_procedures(U)
    assert not any(d.edge_id == "e-p" for d in after.descriptions)
    w = [x for x in after.withheld if x.edge_id == "e-p"]
    assert len(w) == 1 and w[0].outcome == "redacted"
    assert "imperative" not in json.dumps(after.to_dict() if hasattr(after, "to_dict") else after.__dict__, default=str)
