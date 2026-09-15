"""specs/0041 — the EXECUTABLE treatment matrix (the round-3 verdict's artifact ask).

0041 is unimplemented, so every row here SIMULATES the ruled treatment on real
records through the store's own write paths and then asks the product's own
readers, guards and predicates what survived — the reviewer's method in round 3.
A row is one operational property the treatment must preserve. Where today's
code cannot yet honour a ruling (the closure amendments in §11.4), the row is a
STRICT xfail: red first, it flips when the amendment lands.
"""
import json

import pytest

from veracium import Memory, MemoryConfig
from veracium.schema import (AgreementRecord, Disclosure, Edge, Episode, EvidenceAuthor, Provenance,
                             QUARANTINE_RELATION)
from veracium.graph import plan_correction

MARKER = "\x00veracium:redacted\x00"
U = "u"
RECOGNISED_KINDS = ("interaction", "outcome", "corrected")     # the product's own writers (writer_traces.md)


def _quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def _mem(tmp_path):
    return Memory(llm=_quiet, config=MemoryConfig(db_path=str(tmp_path / "m.db"), wiki_recompile_after_writes=0,
                                                  scope_groups={}, require_source_id=False))


def _edge(eid, **kw):
    base = dict(id=eid, user_id=U, subject="user", relation="works_as", object="Porto",
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                      disclosure=Disclosure.MENTIONABLE))
    base.update(kw)
    return Edge(**base)


def _rewrite_episode(store, eid, **changes):
    """The simulated treatment on a stored episode: full re-validation, then the row."""
    row = store._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    d = json.loads(row[0]); d.update(changes)
    Episode.model_validate(d)
    store._conn.execute("UPDATE episodes SET json=? WHERE id=?", (json.dumps(d), eid)); store._conn.commit()


def _treat_kind(kind):
    """Row 46 at v6: PRESERVE a recognised operational kind, REPLACE prose."""
    return kind if kind in RECOGNISED_KINDS else MARKER


# ---------------------------------------------------------------- outcome-chain continuity (round-3 F1)
def test_row46_the_two_branch_kind_treatment_keeps_the_outcome_chain_and_its_guards(tmp_path):
    m = _mem(tmp_path); st = m.store; st.add_edge(_edge("e-1"))
    m.record_outcome(U, "e-1", outcome="challenged", evidence_ref="use-1", actor="system")
    m.record_outcome(U, "e-1", outcome="concurred", evidence_ref="use-1", actor="system")
    links = [e for e in st.episodes(U) if e.kind == "outcome" and e.edge_id == "e-1"]
    for e in links:                                            # the treatment: summary REPLACED, kind by the two-branch rule
        _rewrite_episode(st, e.id, summary=MARKER, kind=_treat_kind(e.kind))
    head = st._chain_head(U, "e-1", "use-1")
    assert head is not None and head.seq == 2                 # the head survives
    m.record_outcome(U, "e-1", outcome="challenged", evidence_ref="use-1", actor="system")
    assert st._chain_head(U, "e-1", "use-1").seq == 3         # the append continues, never restarts
    with pytest.raises(ValueError):                            # H14's deletion refusal still keyed
        st.delete_episode(links[0].id)
    with pytest.raises(ValueError):                            # the add_episode fence still keyed
        st.add_episode(links[0])


def test_row46_the_replace_branch_applies_to_prose_only(tmp_path):
    m = _mem(tmp_path); st = m.store
    st.add_episode(Episode(id="ep-p", user_id=U, date="2026-09-01", summary="s", kind="told me in confidence",
                           provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                                 disclosure=Disclosure.MENTIONABLE)))
    _rewrite_episode(st, "ep-p", summary=MARKER, kind=_treat_kind("told me in confidence"))
    ep = [e for e in st.episodes(U) if e.id == "ep-p"][0]
    assert ep.kind == MARKER and ep.summary == MARKER
    assert _treat_kind("outcome") == "outcome" and _treat_kind("interaction") == "interaction"


@pytest.mark.xfail(strict=True, reason="0041 §11.4 / §2d-iv: the recognised-kind set is not yet closed by a refusal "
                                       "at the model or at import (Episode.kind is a bare str); implementation follows acceptance")
def test_row46_the_recognised_kind_set_is_closed_by_a_refusal(tmp_path):
    with pytest.raises(Exception):
        Episode(id="ep-x", user_id=U, date="2026-09-01", summary="s", kind="told me in confidence",
                provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                      disclosure=Disclosure.MENTIONABLE))


# ---------------------------------------------------------------- absent values (round-3 F2)
def test_rows30_49_absence_stays_absence_a_none_reason_is_not_replaced(tmp_path):
    m = _mem(tmp_path); st = m.store
    st.add_episode(Episode(id="ep-a", user_id=U, date="2026-09-01", summary="s",
                           provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                                 disclosure=Disclosure.MENTIONABLE)))
    before = [e for e in st.episodes(U, include_retired=True) if e.id == "ep-a"][0]
    assert before.retired_reason is None and before.active
    _rewrite_episode(st, "ep-a", summary=MARKER)              # the treatment touches content, never absence
    after = [e for e in st.episodes(U, include_retired=True) if e.id == "ep-a"][0]
    assert after.retired_reason is None and after.active == before.active
    # the literal round-2 wording, applied to None, is the state change the reviewer found — asserted as the wrong shape
    wrong = Episode.model_validate({**after.model_dump(mode="json"), "retired_reason": MARKER})
    assert not wrong.active


# ---------------------------------------------------------------- quarantine (research's G4)
def test_relation_replacement_keeps_an_ingest_quarantined_edge_quarantined():
    e = _edge("e-q", subject="neighbour", relation=QUARANTINE_RELATION, object="says the user owes money",
              provenance=Provenance(author_of_evidence=EvidenceAuthor.THIRD_PARTY, evidence_ref="ev",
                                    disclosure=Disclosure.QUARANTINED))
    after = Edge.model_validate({**e.model_dump(mode="json"), "subject": MARKER, "relation": MARKER, "object": MARKER})
    assert e.quarantined and after.quarantined                 # the disclosure is the durable discriminator


@pytest.mark.xfail(strict=True, reason="0041 §11.4: a quarantine relation without the QUARANTINED disclosure is not yet "
                                       "refused by add_edge/import (research's G4); implementation follows acceptance")
def test_a_relation_only_quarantine_is_refused_at_the_write_path(tmp_path):
    m = _mem(tmp_path); st = m.store
    with pytest.raises(Exception):
        st.add_edge(_edge("e-q2", relation=QUARANTINE_RELATION, object="says the user owes money"))


# ---------------------------------------------------------------- INV-11's mirror (research's G1/G2)
@pytest.mark.xfail(strict=True, reason="0041 §4b INV-11's MIRROR: a non-redaction write introducing the marker is not yet "
                                       "refused (a marker-carrying replacement is admitted by the correction guard); implementation follows acceptance")
def test_a_non_redaction_write_may_not_introduce_the_marker(tmp_path):
    m = _mem(tmp_path); st = m.store
    with pytest.raises(Exception):
        st.add_edge(_edge("e-m", object=MARKER))


def test_a_redacted_prior_cannot_be_corrected_the_caller_facing_consequence(tmp_path):
    """§8 at v6 (research, from dev's G1): the correction path requires the
    replacement to share the prior's (user, subject, relation); after redaction
    those are markers, so a live replacement is refused. Asserted so the sentence
    in §8 is a behaviour, not a reading."""
    m = _mem(tmp_path); st = m.store
    tomb = _edge("e-tomb", subject=MARKER, relation=MARKER, object=MARKER); st.add_edge(tomb)
    with pytest.raises(ValueError):
        plan_correction(st, tomb, _edge("e-r", object="Braga"), op_id="op-x")
