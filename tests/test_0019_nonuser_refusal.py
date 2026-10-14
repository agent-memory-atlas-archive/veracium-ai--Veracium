"""specs/0019 v7 §4c (the fold of amendment 0045/0019-nonuser-refusal; INV-N1–N4): a FLAGGED triple from a
NON-user-effective event is refused and counted, nothing written; a USER-effective event's flagged triple is stored
with the flag exactly as before. USER-effective is the product's own resolved trust: the effective author is `user` AND
the resolved content source is direct; the absent-context floor derived(THIRD_PARTY) is non-user-effective.

PRODUCT tests through the real `ingest_event` with a scripted provider (the spec's implementation gate; dev's reference
model II encodes the write path as its G8). A triple is FLAGGED when a specifics token of its object (here the number
42) is absent from the event text, measured with the shipped predicate.
"""
from __future__ import annotations

import json

import pytest

from veracium import SqliteStore
from veracium.grounding import ungrounded
from veracium.ingest import ingest_event
from veracium.schema import EvidenceAuthor, EvidenceContext

U = "u"
DATE = "2026-10-14"
TEXT = "I moved flats this week"
FLAGGED = {"subject": "user", "relation": "located_at", "object": "flat 42", "note": "", "volatility": "durable"}
CLEAN_TEXT = "I moved to flat 42 this week"


def _llm(answer: str):
    def complete(prompt, *, system=None, role="compile", json_schema=None):
        return answer
    return complete


def _answer(*triples):
    return json.dumps({"episode": "the user moved", "triples": list(triples)})


def _ingest(tmp_path, *, text, author, context=None, answer=None, name="s"):
    store = SqliteStore(str(tmp_path / f"{name}.db"))
    res = ingest_event(store, _llm(answer or _answer(FLAGGED)), U, event_text=text, author=author, date=DATE,
                       context=context)
    edges = store.edges(U, active_only=False)
    store.close()
    return res, edges


def test_the_fixture_triple_is_flagged_and_its_control_is_not():
    """The premise, measured with the shipped predicate rather than assumed."""
    assert ungrounded(FLAGGED["object"], TEXT, DATE) is True
    assert ungrounded(FLAGGED["object"], CLEAN_TEXT, DATE) is False


@pytest.mark.parametrize("author,context,label", [
    (EvidenceAuthor.THIRD_PARTY, EvidenceContext.direct(), "a third-party author"),
    (EvidenceAuthor.SYSTEM, EvidenceContext.direct(), "a system author"),
    (EvidenceAuthor.USER, EvidenceContext.derived(EvidenceAuthor.THIRD_PARTY), "a user author, derived content"),
])
def test_a_flagged_triple_from_a_non_user_effective_event_is_refused_and_counted(tmp_path, author, context, label):
    """INV-N1: nothing written, the counter moves by one. Mutant: store it with the marker (0019's old rule)."""
    res, edges = _ingest(tmp_path, text=TEXT, author=author, context=context, name=label.replace(" ", "_"))
    assert edges == [], f"{label}: a flagged non-user triple was written"
    assert res["nonuser_ungrounded_refused"] == 1 and res["facts"] == 0, (label, res)


def test_an_unflagged_triple_from_a_non_user_effective_event_is_stored(tmp_path):
    """INV-N1's other half. Mutant: refuse unflagged non-user triples too."""
    res, edges = _ingest(tmp_path, text=CLEAN_TEXT, author=EvidenceAuthor.THIRD_PARTY, context=EvidenceContext.direct())
    assert len(edges) == 1 and edges[0].ungrounded is False
    assert res["nonuser_ungrounded_refused"] == 0


def test_a_flagged_triple_from_a_user_effective_event_is_stored_with_the_flag(tmp_path):
    """INV-N2: exactly 0019's rule — stored, ungrounded=True, never refused. Mutant: refuse it (v1's rule)."""
    res, edges = _ingest(tmp_path, text=TEXT, author=EvidenceAuthor.USER, context=EvidenceContext.direct())
    assert len(edges) == 1 and edges[0].ungrounded is True
    assert res["nonuser_ungrounded_refused"] == 0 and res["facts"] == 1


def test_the_absent_context_floor_is_non_user_effective(tmp_path):
    """INV-N3: a USER author with NO declared context resolves to the floor derived(THIRD_PARTY) — non-user-effective,
    so its flagged triple is refused. Mutant: treat an undeclared context as direct."""
    res, edges = _ingest(tmp_path, text=TEXT, author=EvidenceAuthor.USER, context=None)
    assert edges == [] and res["nonuser_ungrounded_refused"] == 1


@pytest.mark.parametrize("answer,label", [
    (_answer(), "an empty extraction"),
    (_answer({"subject": "user", "relation": "located_at", "object": "flat 42", "note": "", "volatility": "durable"}),
     "a user-effective flagged triple"),
    ("I refuse.", "the unparseable path"),
])
def test_the_counter_is_present_and_zero_on_every_path(tmp_path, answer, label):
    """INV-N4: present, and zero, wherever nothing was refused — the unparseable path included. Mutant: omit the key when
    zero."""
    res, _edges = _ingest(tmp_path, text=TEXT, author=EvidenceAuthor.USER, context=EvidenceContext.direct(),
                          answer=answer, name=label.replace(" ", "_"))
    assert "nonuser_ungrounded_refused" in res, label
    assert res["nonuser_ungrounded_refused"] == 0, (label, res["nonuser_ungrounded_refused"])


def test_the_counter_never_reaches_the_model_over_mcp():
    """0019 v7 §2's carrier row: the MCP tool result strips the counter with its refusal siblings (0031 §4d)."""
    from veracium import mcp_server
    assert "nonuser_ungrounded_refused" in mcp_server._OPERATOR_ONLY
