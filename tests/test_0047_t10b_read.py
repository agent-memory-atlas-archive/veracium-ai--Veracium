"""specs/0047 T10b — the read half: a challenged fact reaches no assertion surface, and wherever it is inspected it
carries the challenge (0047 v1.16 §4c–§4e; 0045 v1.13 §4c, INV-G8, INV-G13; IO-II-5).

Every surface reads ONE `ChallengeSnapshot` per call (`veracium.challenge`). The owner's rulings (2026-10-19): F7 — a
same-value twin of a challenged record is withheld too ((a) both directions, (b) across disclosure classes, whatever the
challenged record's state, (c) counted as its own fact); (g) a REDACTED challenged record twins nothing; (h) the
subject's own later correction is a twin until a `resolve`; (i) a challenger outside a principal's view withholds an
in-view twin and is never named there; Q9 as-of withholds historical twins; Q10 collapse never suppresses an acted
member. F7's expected sets are stated as LITERALS (research's rule: model II predates F7, so these cells are its only
oracle).
"""
from __future__ import annotations

import importlib.util
import json
import random
import sys
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig, budgets, challenge as C, why as W
from veracium.compile import compile_wiki
from veracium.graph import apply_supersession
from veracium.schema import (DEFAULT_RELATIONS, Disclosure, Edge, EvidenceAuthor as EA, Provenance)
from veracium.scope import Identity
from veracium.store.base import ReplyRefused
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
U = "u1"
A1, A2 = Identity(None, "agent-1"), Identity(None, "agent-2")
ONE_GROUP = {"team-a": [A1]}
WITHHELD_1 = "[withheld: 1 fact(s) the subject disputes; see the host's why()]"


class _Cap:
    """Records every prompt by role; the compiler answers with its own prompt (so the body shows its inputs)."""

    def __init__(self):
        self.prompts: dict = {}

    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        self.prompts.setdefault(role, []).append(prompt)
        if role == "compile":
            return "WIKI " + prompt
        if role == "gate":
            return "ok"
        return json.dumps({"triples": [], "episode": "x"})


def _mem(tmp_path, name="m.db", *, wiki=0, groups=None, llm=None):
    return Memory(llm=llm or _Cap(), config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=wiki,
                                                         scope_groups=groups, require_source_id=False))


def _edge(eid, obj, *, relation="works_as", subject="user", author=EA.USER, disc=Disclosure.MENTIONABLE, att=None,
          attv=None, src=None, ungrounded=False, valid_from=None, source_id=None, needs_confirmation=False):
    kw = {} if valid_from is None else {"valid_from": valid_from}
    if needs_confirmation:
        kw["needs_confirmation"] = True
    return Edge(id=eid, user_id=U, subject=subject, relation=relation, object=obj,
                provenance=Provenance(author_of_evidence=author, evidence_ref=f"ev-{eid}", disclosure=disc,
                                      source_id=source_id),
                att=att, src=src if att is not None else None, attv=attv if att is not None else None,
                ungrounded=ungrounded, **kw)


def _plant(mem, *edges):
    for e in edges:
        mem.store.add_edge(e)


def _ok(fn, *a, **k):
    """A call the cell expects to SUCCEED: any raise is the property failing, read as an assertion."""
    try:
        return fn(*a, **k)
    except Exception as exc:                                       # noqa: BLE001 — the cell's subject
        raise AssertionError(f"expected success; raised {type(exc).__name__}: {exc}") from exc


def _challenge(mem, eid, text="that is wrong"):
    return _ok(mem.reply, U, eid, kind="challenge", text=text)["reply_id"]


def _resolve(mem, eid, cid):
    return _ok(mem.reply, U, eid, kind="resolve", target=cid)["reply_id"]


def _insp(r, eid):
    """The inspection entry for `eid`, asserted present (a missing carrier is the property failing, never a KeyError)."""
    assert eid in r.inspection, (eid, sorted(r.inspection))
    return r.inspection[eid]


def _asof_insp(fact):
    assert fact.inspection is not None, fact.edge.id
    return fact.inspection


def _withheld_ids(r) -> set:
    return {k for k, v in r.inspection.items() if not v.challenge_clear}


def _asserted(r, obj: str) -> bool:
    """`obj` on a FACT line of the grounded block. Bracketed lines are not fact assertions: `[date] …` is an episode
    (an act episode — `confirm()`'s "(user) confirmed '…' still holds" — names a value as its act's object, 0047 §8
    NOT claimed), `[withheld: …]` the report line."""
    return any(obj in ln for ln in r.grounded.splitlines() if not ln.lstrip().startswith("["))


def _withheld_line(text: str):
    return [ln for ln in text.splitlines() if ln.startswith("[withheld:")]


# ================================================================================ INV-R3: every assertion surface
def test_r3_query_recall_withholds_counts_and_keeps_the_record_in_the_structured_carrier(tmp_path):
    """Query recall: the challenged object is in no rendered part; the withheld line counts it; `Recall.edges` keeps the
    record with its inspection entry (RAW). Mutant: skip the detail withholding."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme"), _edge("e-b", "Porto", relation="lives_in"))
    _challenge(mem, "e-a", "I never worked at Acme")
    r = _ok(mem.recall, U, "where does the user work and live")
    assert "CFO at Acme" not in r.context and "Porto" in r.context
    assert _withheld_line(r.grounded) == [WITHHELD_1]
    assert {e.id for e in r.edges} >= {"e-a", "e-b"}
    assert _insp(r, "e-a").unit == "[challenged by the subject: 1 open; latest: I never worked at Acme]"
    assert (_insp(r, "e-a").challenge_clear, _insp(r, "e-b").challenge_clear) == (False, True)


def test_r3_the_contested_block_withholds_a_challenged_member(tmp_path):
    """The CONTESTED line renders only unchallenged members; `Recall.contested` keeps both. Mutant: render the
    contested groups unfiltered."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("p", "CFO at Acme"))
    apply_supersession(mem.store, _edge("i", "unemployed", author=EA.SYSTEM), mem.config.relations)
    _challenge(mem, "p")
    r = _ok(mem.recall, U, "CFO Acme unemployed")
    assert "CFO at Acme" not in r.context and "unemployed" in r.context
    assert [e.id for e in r.contested[0].exposed] == ["p", "i"]
    assert _withheld_line(r.grounded) == [WITHHELD_1]


def test_r3_proactive_withholds_and_counts(tmp_path):
    """Proactive (recall without a query) is an assertion surface: two facts it would surface (both need
    confirmation), one challenged. Mutant: skip proactive's withholding."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme", needs_confirmation=True),
           _edge("e-b", "Porto", relation="lives_in", needs_confirmation=True))
    _challenge(mem, "e-a")
    r = _ok(mem.recall, U, None)
    assert "CFO at Acme" not in r.context and "Porto" in r.context
    assert _withheld_line(r.context) == [WITHHELD_1]
    assert r.inspection.get("e-a") is None or not _insp(r, "e-a").challenge_clear


def test_r3_answer_never_hands_a_challenged_fact_to_the_gate(tmp_path):
    """`answer()` reads recall's rendered text (Q14): the gate's prompt never holds the challenged object."""
    llm = _Cap()
    mem = _mem(tmp_path, llm=llm)
    _plant(mem, _edge("e-a", "CFO at Acme"), _edge("e-b", "Porto", relation="lives_in"))
    _challenge(mem, "e-a")
    _ok(mem.answer, U, "where does the user work")
    assert llm.prompts["gate"] and all("CFO at Acme" not in p for p in llm.prompts["gate"])


def test_r20_as_of_withholds_a_fact_challenged_now_whatever_T(tmp_path):
    """INV-R20: the challenge is written now about a fact valid in 2024; as of 2025 it is withheld, and
    `facts_valid_at` carries the unit from the CURRENT acts. Mutant: read acts written before T only."""
    mem = _mem(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-a", "CFO at Acme", valid_from=t0), _edge("e-b", "Porto", relation="lives_in", valid_from=t0))
    _challenge(mem, "e-a", "never")
    T = datetime(2025, 1, 1, tzinfo=timezone.utc)
    r = _ok(mem.recall, U, "where does the user work and live", as_of=T)
    assert "CFO at Acme" not in r.context and "Porto" in r.context
    assert _withheld_line(r.grounded) == [WITHHELD_1]
    facts = {f.edge.id: f for f in _ok(mem.facts_valid_at, U, "user", "works_as", T)}
    assert _asof_insp(facts["e-a"]).unit == "[challenged by the subject: 1 open; latest: never]"


# ================================================================================ INV-R18: the wiki
def test_r18_the_compiler_input_never_holds_a_challenged_fact(tmp_path):
    """INV-R18, and INV-R3 at the wiki compiler's input (an assertion surface): a challenged fact never reaches it."""
    llm = _Cap()
    mem = _mem(tmp_path, wiki=1, llm=llm)
    _plant(mem, _edge("e-a", "CFO at Acme"), _edge("e-b", "Porto", relation="lives_in"))
    _challenge(mem, "e-a")
    _ok(mem.recall, U, "anything")
    assert llm.prompts["compile"] and all("CFO at Acme" not in p for p in llm.prompts["compile"])
    assert any("Porto" in p for p in llm.prompts["compile"])


@pytest.mark.parametrize("kind", ["challenge", "context", "withdrawn-consent", "resolve"])
def test_r18_every_reply_kind_evicts_the_wiki_and_bumps_once(tmp_path, kind):
    """Q7 (research: a resolve too — it restores a fact the cache excluded). Mutant: drop the eviction."""
    mem = _mem(tmp_path, wiki=1)
    _plant(mem, _edge("e-a", "CFO at Acme"))
    cid = _challenge(mem, "e-a") if kind == "resolve" else None
    _ok(mem.recall, U, "anything")
    assert mem.store.get_wiki(U) is not None
    v = mem.store.store_version(U)
    if kind == "resolve":
        _resolve(mem, "e-a", cid)
    else:
        _ok(mem.reply, U, "e-a", kind=kind, text="x")
    assert mem.store.get_wiki(U) is None and mem.store.store_version(U) == v + 1


def _compile(tmp_path, on_calls):
    a, b = _mem(tmp_path, "w.db"), _mem(tmp_path, "w.db")
    _plant(a, _edge("e-1", "CFO at Acme"), _edge("e-2", "green tea", relation="likes"))
    calls = []

    def llm(prompt, system=None, role=None):
        calls.append(prompt)
        act = on_calls.get(len(calls))
        if act:
            act(b)
        return "WIKI " + prompt
    body = compile_wiki(a.store, llm, U, DEFAULT_RELATIONS)
    cached = a.store._conn.execute("SELECT text FROM wiki WHERE user_id=?", (U,)).fetchone()
    return body, cached, calls


def test_r18_a_challenge_during_the_compile_is_recompiled_once(tmp_path):
    """The in-flight fence's challenge branch. Mutant: drop it (the stale body is returned)."""
    body, cached, calls = _compile(tmp_path, {1: lambda b: b.reply(U, "e-1", kind="challenge", text="no")})
    assert len(calls) == 2 and "CFO at Acme" in calls[0] and "CFO at Acme" not in calls[1]
    assert "CFO at Acme" not in body and "green tea" in body
    assert cached is not None and "CFO at Acme" not in cached[0]


def test_r18_a_second_challenge_in_the_recompile_returns_the_closed_notice(tmp_path):
    body, cached, calls = _compile(tmp_path, {1: lambda b: b.reply(U, "e-1", kind="challenge", text="no"),
                                              2: lambda b: b.reply(U, "e-2", kind="challenge", text="no")})
    assert len(calls) == 2 and body == budgets.DISPUTED_DURING_COMPILE_NOTICE and cached is None


def test_r18_control_a_context_reply_during_the_compile_keeps_the_returned_body(tmp_path):
    """A context reply bumps (so nothing publishes) but withholds nothing (Q8): today's plain-write behaviour."""
    body, cached, calls = _compile(tmp_path, {1: lambda b: b.reply(U, "e-1", kind="context", text="a visit")})
    assert len(calls) == 1 and cached is None and "CFO at Acme" in body


# ================================================================================ INV-R12: the grid, restriction only
def _grid_edge(mem, g):
    if g == "attested":
        e = _edge("e-g", "CFO at Acme", att="attested", attv="ATTEST-3@b1329a81", src="ep-x")
    elif g == "unknown":
        e = _edge("e-g", "CFO at Acme")
    else:
        e = _edge("e-g", "CFO at Acme", att="not_attested", attv="ATTEST-3@b1329a81", src="ep-x")
    _plant(mem, e)
    if g == "confirmed":
        _ok(mem.confirm, U, "e-g", correlation_id="k-g")


@pytest.mark.parametrize("g", ["attested", "confirmed", "not_attested", "unknown"])
def test_r12_every_grounding_value_is_asserted_unchallenged_and_withheld_challenged(tmp_path, g):
    """§4c's eight cells. Mutant: keep `attested` assertable under a challenge (v1.7's cell)."""
    mem = _mem(tmp_path)
    _grid_edge(mem, g)
    r0 = _ok(mem.recall, U, "CFO Acme")
    assert _asserted(r0, "CFO at Acme") and _insp(r0, "e-g").grounding == g
    _challenge(mem, "e-g")
    r1 = _ok(mem.recall, U, "CFO Acme")
    assert not _asserted(r1, "CFO at Acme") and _insp(r1, "e-g").grounding == g
    assert not _insp(r1, "e-g").challenge_clear


def test_r12_a_clear_challenge_state_never_promotes_an_ineligible_edge(tmp_path):
    """A resolved challenge on a third-party claim leaves it fenced (UNVERIFIED), never grounded. Mutant: route by
    `challenge_clear` instead of the existing gates."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-q", "owes 400 EUR", relation="third_party_claim", subject="person:landlord",
                      author=EA.THIRD_PARTY, disc=Disclosure.QUARANTINED))
    _resolve(mem, "e-q", _challenge(mem, "e-q"))
    r = _ok(mem.recall, U, "landlord owes")
    assert _insp(r, "e-q").challenge_clear
    assert "owes 400 EUR" not in r.grounded and "owes 400 EUR" in r.unverified


def test_r12_as_of_a_clear_challenge_state_never_promotes_a_fenced_fact(tmp_path):
    """As of T, a third-party claim resolves FENCED: with its challenge resolved it is still never grounded. Mutant:
    let `challenge_clear` stand in for the resolution's grounded outcome."""
    mem = _mem(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-q", "owes 400 EUR", relation="third_party_claim", subject="person:landlord",
                      author=EA.THIRD_PARTY, disc=Disclosure.QUARANTINED, valid_from=t0))
    _resolve(mem, "e-q", _challenge(mem, "e-q"))
    r = _ok(mem.recall, U, "landlord owes", as_of=datetime(2025, 1, 1, tzinfo=timezone.utc))
    assert _insp(r, "e-q").challenge_clear and "owes 400 EUR" not in r.grounded


# ================================================================================ INV-R6: never budget-selected
@pytest.mark.parametrize("budget", [400, 1200, 4000])
def test_r6_the_open_count_and_the_withheld_count_do_not_depend_on_the_budget(tmp_path, budget):
    """30 challenges on one fact; 25 challenged facts. Mutant: count from the budget-selected lines."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-many", "CFO at Acme"))
    for n in range(30):
        _challenge(mem, "e-many", f"no {n}")
    for n in range(25):
        _plant(mem, _edge(f"e-{n:02d}", f"thing{n:02d}", relation="likes"))
        _challenge(mem, f"e-{n:02d}")
    r = _ok(mem.recall, U, "CFO Acme likes " + " ".join(f"thing{n:02d}" for n in range(25)), token_budget=budget)
    assert _insp(r, "e-many").open_challenges == 30
    assert _insp(r, "e-many").unit == "[challenged by the subject: 30 open; latest: no 29]"
    assert _withheld_line(r.grounded) == ["[withheld: 26 fact(s) the subject disputes; see the host's why()]"]


def test_r6_the_latest_challenge_is_by_written_at_then_id(tmp_path):
    """The display contract (§4d): three challenges at one instant with permuted ids, then a later one. The unit names
    the latest by `(written_at, id)`; `why` lists replies in that order. Mutant: order by id alone."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme"))
    ins = ("INSERT INTO replies(id, user_id, edge_id, kind, target, text, actor, correlation_id, request_digest, "
           "origin, act_seq, written_at) VALUES(?,?,?,'challenge',NULL,?,'user',?,'d','local',?,?)")
    rows = [("r-c", "c", "2026-10-19T10:00:00+00:00"), ("r-a", "a", "2026-10-19T10:00:00+00:00"),
            ("r-b", "b", "2026-10-19T10:00:00+00:00"), ("r-0", "later", "2026-10-19T11:00:00+00:00")]
    for i, (rid, text, at) in enumerate(rows):
        mem.store._conn.execute(ins, (rid, U, "e-a", text, f"k-{rid}", 900 + i, at))
    mem.store._conn.commit()
    r = _ok(mem.recall, U, "CFO Acme")
    assert _insp(r, "e-a").latest_challenge == "later"
    bio = W.gather(mem.store, U, "e-a")
    assert [x["id"] for x in bio.replies] == ["r-a", "r-b", "r-c", "r-0"]


# ================================================================================ one snapshot (§4d, IO-II-5)
@pytest.mark.parametrize("surface", ["query", "proactive", "as-of", "why", "introspect"])
def test_one_snapshot_per_call(tmp_path, monkeypatch, surface):
    """Each surface call reads the challenge state exactly once. Mutant: a second read for the inspection map."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme"))
    reads = []
    real = mem.store.challenge_snapshot
    monkeypatch.setattr(mem.store, "challenge_snapshot", lambda user_id: (reads.append(user_id), real(user_id))[1])
    T = datetime(2030, 1, 1, tzinfo=timezone.utc) if surface == "as-of" else None
    {"query": lambda: mem.recall(U, "CFO Acme"), "proactive": lambda: mem.recall(U, None),
     "as-of": lambda: mem.recall(U, "CFO Acme", as_of=datetime.now(timezone.utc)),
     "why": lambda: W.gather(mem.store, U, "e-a"),
     "introspect": lambda: mem.introspect(U, mode="categories")}[surface]()
    assert reads == [U], (surface, reads, T)


def test_a_challenge_landing_inside_a_call_is_seen_whole_by_the_next_call(tmp_path, monkeypatch):
    """A challenge committed by another connection right after this call's snapshot: within the call, withholding,
    the count and the inspection entry agree (nothing withheld); the next call withholds all three ways."""
    mem, other = _mem(tmp_path, "s.db"), _mem(tmp_path, "s.db")
    _plant(mem, _edge("e-a", "CFO at Acme"))
    real = mem.store.challenge_snapshot
    fired = []

    def snap(user_id):
        s = real(user_id)
        if not fired:
            fired.append(1)
            other.reply(U, "e-a", kind="challenge", text="no")
        return s
    monkeypatch.setattr(mem.store, "challenge_snapshot", snap)
    r1 = _ok(mem.recall, U, "CFO Acme")
    assert ("CFO at Acme" in r1.context, _withheld_line(r1.grounded), _insp(r1, "e-a").challenge_clear) \
        == (True, [], True)
    r2 = _ok(mem.recall, U, "CFO Acme")
    assert ("CFO at Acme" in r2.context, _withheld_line(r2.grounded), _insp(r2, "e-a").challenge_clear) \
        == (False, [WITHHELD_1], False)


# ================================================================================ inspection carriers
def test_inspection_why_carries_grounding_replies_and_the_unit(tmp_path):
    """`why` JSON and text: g(e) and its version, every reply (all kinds), the unit (RT9-12: att and src printed)."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme", att="not_attested", attv="ATTEST-3@b1329a81", src="ep-1"))
    cid = _challenge(mem, "e-a", "never")
    _ok(mem.reply, U, "e-a", kind="context", text="I visited once")
    bio = W.gather(mem.store, U, "e-a")
    assert bio.grounding == {"label": "not_attested", "version": "ATTEST-3@b1329a81"}
    assert [x["kind"] for x in bio.replies] == ["challenge", "context"]
    assert bio.challenge["unit"] == "[challenged by the subject: 1 open; latest: never]" and bio.challenge["open"] == 1
    text = W.render(bio)
    assert "grounding     not_attested (attestation version ATTEST-3@b1329a81)  att=not_attested src=ep-1" in text
    assert "[challenged by the subject: 1 open; latest: never]" in text and f"reply challenge {cid}" in text
    assert W.to_json(bio)["challenge"]["open"] == 1


def test_inspection_introspect_categories_carry_the_unit(tmp_path):
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme"))
    _challenge(mem, "e-a", "never")
    lines = _ok(mem.introspect, U, mode="categories")["categories"]["works_as"]
    assert len(lines) == 1 and lines[0].endswith("[challenged by the subject: 1 open; latest: never]")


def test_q6_a_long_challenge_on_a_flagged_fact_keeps_the_marker_the_count_and_the_elision(tmp_path):
    """§4d: the marker is never clamped away; the count is never clamped; the text elides."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme", ungrounded=True))
    _challenge(mem, "e-a", "x" * 5000)
    line = _ok(mem.introspect, U, mode="categories")["categories"]["works_as"][0]
    assert "[possible extraction error]" in line and "1 open; latest: " in line and budgets.ELISION_MARKER in line


@pytest.mark.parametrize("grounding", ["attested", "not_attested", "legacy"])
@pytest.mark.parametrize("ungrounded", [False, True])
def test_g8_the_marker_follows_the_flag_unchallenged_and_a_challenged_flagged_fact_is_withheld(tmp_path, ungrounded,
                                                                                               grounding):
    """INV-G8: 0019's marker follows the FLAG on every grounding value — `attested`, `not_attested` and a legacy row
    with no axis (T12 widened the cell from `attested` alone: the row says "every grounding value, legacy included");
    a challenged flagged fact is withheld either way. Mutant: suppress the marker on `attested` or `unknown`."""
    mem = _mem(tmp_path)
    att = {"attested": dict(att="attested", attv="ATTEST-3@b1329a81", src="ep-1"),
           "not_attested": dict(att="not_attested", attv="ATTEST-3@b1329a81", src="ep-1"), "legacy": {}}[grounding]
    _plant(mem, _edge("e-a", "CFO at Acme", ungrounded=ungrounded, **att),
           _edge("e-b", "chef", relation="likes", ungrounded=ungrounded))
    _challenge(mem, "e-b")
    r = _ok(mem.recall, U, "CFO Acme chef likes")
    assert ("[possible extraction error]" in r.context) == ungrounded
    assert "chef" not in r.context


def test_g13_why_reads_the_version_from_attv_and_a_legacy_row_reads_version_unknown(tmp_path):
    """INV-G13's `why` half: two coexisting versions, each its own; legacy reads "version unknown". Mutant: read the
    running build's version."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-2", "baker", att="attested", attv="ATTEST-2@e1e1e3d3", src="ep-1"),
           _edge("e-3", "CFO at Acme", att="attested", attv="ATTEST-3@b1329a81", src="ep-2", relation="role"),
           _edge("e-l", "Porto", relation="lives_in"))
    got = {eid: W.gather(mem.store, U, eid).grounding for eid in ("e-2", "e-3", "e-l")}
    assert got == {"e-2": {"label": "attested", "version": "ATTEST-2@e1e1e3d3"},
                   "e-3": {"label": "attested", "version": "ATTEST-3@b1329a81"},
                   "e-l": {"label": "unknown", "version": "version unknown"}}


def test_rt9_11_a_scoped_views_shaped_edge_keeps_src_and_attv(tmp_path):
    mem = _mem(tmp_path, groups=ONE_GROUP)
    _plant(mem, _edge("e-a", "CFO at Acme", att="not_attested", attv="ATTEST-3@b1329a81", src="ep-9",
                      source_id="agent-1"))
    r = _ok(mem.recall, U, "CFO Acme", principal=A1)
    e = next(x for x in r.edges if x.id == "e-a")
    assert (e.att, e.src, e.attv) == ("not_attested", "ep-9", "ATTEST-3@b1329a81")


# ================================================================================ §4e collapse (Q10, ruled)
def test_collapse_never_suppresses_a_member_carrying_an_act(tmp_path):
    """Two strictly-redundant restatements: without acts one surfaces; once the NON-survivor is confirmed both do.
    Mutant: ignore acts in collapse."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-old", "chef", valid_from=datetime(2025, 1, 1, tzinfo=timezone.utc)),
           _edge("e-new", "chef", valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    before = {e.id for e in _ok(mem.recall, U, "chef").edges}
    assert len(before & {"e-old", "e-new"}) == 1
    hidden = ({"e-old", "e-new"} - before).pop()
    _ok(mem.confirm, U, hidden, correlation_id="k-1")
    assert {"e-old", "e-new"} <= {e.id for e in _ok(mem.recall, U, "chef").edges}


# ================================================================================ F7 (literal expected sets)
def _miso(mem, first, second, *, author2=EA.USER, disc2=Disclosure.MENTIONABLE):
    _plant(mem, _edge("e-1", first, relation="has_pet"))
    cid = _challenge(mem, "e-1")
    _plant(mem, _edge("e-2", second, relation="has_pet", author=author2, disc=disc2))
    _plant(mem, _edge("e-x", "Porto", relation="lives_in"))
    return cid


@pytest.mark.parametrize("first,second", [("Miso", "cat Miso"), ("cat Miso", "Miso"), ("Miso", "Miso")])
def test_f7_a_twin_in_either_direction_is_withheld_and_counted(tmp_path, first, second):
    """(a) both directions; (c) counted as its own fact. Mutants: exact keys only; per-edge only."""
    mem = _mem(tmp_path)
    _miso(mem, first, second)
    r = _ok(mem.recall, U, "pet Miso Porto")
    assert _withheld_ids(r) == {"e-1", "e-2"}
    assert "Miso" not in r.context and "Porto" in r.context
    assert _withheld_line(r.grounded) == ["[withheld: 2 fact(s) the subject disputes; see the host's why()]"]
    assert _insp(r, "e-2").withheld_by == ("e-1",) and _insp(r, "e-2").unit is None


def test_f7_a_different_value_is_not_a_twin(tmp_path):
    mem = _mem(tmp_path)
    _miso(mem, "Miso", "Mochi")
    assert _withheld_ids(_ok(mem.recall, U, "pet Miso Mochi")) == {"e-1"}


def test_f7_a_twin_across_disclosure_classes_is_withheld(tmp_path):
    """(b): a quarantined third-party restatement is withheld too, from the unverified section. Mutant: one class."""
    mem = _mem(tmp_path)
    _miso(mem, "Miso", "Miso", author2=EA.THIRD_PARTY, disc2=Disclosure.QUARANTINED)
    r = _ok(mem.recall, U, "pet Miso")
    assert _withheld_ids(r) == {"e-1", "e-2"} and "Miso" not in r.context


def test_f7_resolving_the_challenge_releases_the_twin(tmp_path):
    """(e). Mutant: withhold a twin of a RESOLVED challenge."""
    mem = _mem(tmp_path)
    cid = _miso(mem, "Miso", "cat Miso")
    _resolve(mem, "e-1", cid)
    r = _ok(mem.recall, U, "pet Miso")
    assert _withheld_ids(r) == set() and "cat Miso" in r.context and _withheld_line(r.grounded) == []


def test_f7_a_retired_challenged_record_still_withholds_its_twin(tmp_path):
    """(b): the challenge stands on the retired record. Mutant: only active challenged records withhold."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-1", "Miso", relation="has_pet"))
    _challenge(mem, "e-1")
    mem.store.invalidate_edge("e-1", datetime.now(timezone.utc), "superseded")
    _plant(mem, _edge("e-2", "Miso", relation="has_pet"))
    r = _ok(mem.recall, U, "pet Miso")
    assert "e-2" in _withheld_ids(r) and "Miso" not in r.context


def test_h_the_subjects_own_correction_waits_on_a_resolve(tmp_path):
    """The owner's ruling (h): "Acme" challenged ("wrong, it is Acme Labs"), then "Acme Labs" arrives: both withheld;
    `why` on the correction names the challenge it waits on; a resolve asserts the correction."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-1", "Acme", relation="works_at"))
    cid = _challenge(mem, "e-1", "wrong, it is Acme Labs")
    _plant(mem, _edge("e-2", "Acme Labs", relation="works_at"))
    r = _ok(mem.recall, U, "works at Acme Labs")
    assert _withheld_ids(r) == {"e-1", "e-2"} and "Acme" not in r.context
    bio = W.gather(mem.store, U, "e-2")
    assert bio.challenge["waiting_on"] == [cid] and f"not asserted until the subject resolves {cid}" in W.render(bio)
    _resolve(mem, "e-1", cid)
    assert "Acme Labs" in _ok(mem.recall, U, "works at Acme Labs").context


# ------------------------------------------------------------------------------ (g) a redacted challenged record
def test_g1_redacting_a_challenged_record_releases_its_twin(tmp_path):
    """The stated consequence: the record stays off every surface; its twin is asserted again. Mutant: keep
    withholding by any stored proxy."""
    mem = _mem(tmp_path)
    _miso(mem, "Miso", "cat Miso")
    _ok(mem.redact, U, edge_id="e-1", reason="subject_request")
    r = _ok(mem.recall, U, "pet Miso")
    assert "cat Miso" in r.context and _insp(r, "e-2").withheld_by == () and "e-1" not in {e.id for e in r.edges}


def test_g2_the_redaction_treatment_replaces_the_whole_triple():
    """The dependency (g)'s guard rests on today (research's T10b read): every edge treatment replaces the subject,
    relation and object, so a redacted challenged record's triple matches no fact. A narrowing fails HERE, rather than
    quietly leaving `rec.redacted` the only defence."""
    from veracium import redaction as R
    assert {"subject", "relation", "object"} <= set(R.EDGE_REPLACE), R.EDGE_REPLACE


def test_g2_a_redacted_challenged_record_never_withholds_by_its_marker_bytes(tmp_path, monkeypatch):
    """`_value_key(MARKER)` is ('veracium', 'redacted'). Today's local redaction also replaces the subject and relation,
    so the record matches nothing; under a NARROWER treatment that keeps them (simulated as 0041's round-10 cells do,
    by narrowing EDGE_REPLACE), a same-relation fact of value "veracium redacted" would match the marker bytes. It is
    NOT withheld: the snapshot decides by the attestation record. Mutant: match twins on current bytes."""
    from veracium import redaction as R
    monkeypatch.setattr(R, "EDGE_REPLACE", ("object", "note"))
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-1", "Miso", relation="has_pet"))
    _challenge(mem, "e-1")
    _ok(mem.redact, U, edge_id="e-1", reason="subject_request")
    row = json.loads(mem.store._conn.execute("SELECT json FROM edges WHERE id='e-1'").fetchone()[0])
    assert (row["subject"], row["relation"]) == ("user", "has_pet")          # the narrower treatment took hold
    _plant(mem, _edge("e-2", "veracium redacted", relation="has_pet"))
    r = _ok(mem.recall, U, "pet veracium redacted")
    assert _withheld_ids(r) == set() and "veracium redacted" in r.context


# ------------------------------------------------------------------------------ (i) across 0020's principal boundary
def test_i_an_all_out_of_scope_store_with_a_challenged_pair_still_looks_empty(tmp_path):
    """N-1 re-run: the full `Recall` (inspection included) equals the empty store's; no withheld line."""
    empty = _mem(tmp_path, "empty.db", groups=ONE_GROUP)
    held = _mem(tmp_path, "held.db", groups=ONE_GROUP)
    _plant(held, _edge("w1", "Miso", relation="has_pet", source_id="agent-2"))
    _challenge(held, "w1")
    _plant(held, _edge("w2", "cat Miso", relation="has_pet", source_id="agent-2"))
    for q in ("pet Miso", "anything"):
        a, b = empty.recall(U, q, principal=A1), held.recall(U, q, principal=A1)
        assert a == b and b.inspection == {} and _withheld_line(b.context) == []


def test_i_an_out_of_view_challenger_withholds_an_in_view_twin_and_is_never_named(tmp_path):
    """N-2's precedent: the in-view twin is withheld; the scoped inspection names no out-of-view record and holds none
    of its content. Mutant: name the out-of-view challenger in the scoped carrier."""
    mem = _mem(tmp_path, groups=ONE_GROUP)
    _plant(mem, _edge("w1", "Miso", relation="has_pet", source_id="agent-2"))
    _challenge(mem, "w1", "secret dispute text")
    _plant(mem, _edge("v2", "Miso", relation="has_pet", source_id="agent-1"))
    r = _ok(mem.recall, U, "pet Miso", principal=A1)
    i = _insp(r, "v2")
    assert (i.challenge_clear, i.withheld_by, i.waiting_on) == (False, (), ())
    assert "Miso" not in r.context and "secret dispute text" not in repr(r) and "w1" not in repr(r)
    assert _withheld_line(r.grounded) == [WITHHELD_1]


def test_q9_as_of_withholds_a_historical_twin(tmp_path):
    """Q9 (ruled): a 2024 "Miso", superseded since, while today's "Miso" record is challenged: withheld as of 2024."""
    mem = _mem(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-old", "Miso", relation="has_pet", valid_from=t0))
    mem.store.invalidate_edge("e-old", datetime(2025, 1, 1, tzinfo=timezone.utc), "superseded")
    _plant(mem, _edge("e-now", "Miso", relation="has_pet", valid_from=datetime(2025, 1, 1, tzinfo=timezone.utc)))
    _challenge(mem, "e-now")
    r = _ok(mem.recall, U, "pet Miso", as_of=datetime(2024, 6, 1, tzinfo=timezone.utc))
    assert "Miso" not in r.context and "e-old" in _withheld_ids(r)


# ================================================================================ S2-3 (research's T10a stage 2)
def test_s2_3_a_lone_surrogate_in_a_resolves_target_refuses_as_shape(tmp_path):
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "CFO at Acme"))
    try:
        mem.reply(U, "e-a", kind="resolve", target="r-\ud800")
    except Exception as exc:                                       # noqa: BLE001 — the cell's subject
        assert isinstance(exc, ReplyRefused) and exc.reason == "shape", repr(exc)
    else:
        raise AssertionError("nothing was raised")
    assert mem.store._conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0] == 0


# ================================================================================ the model II differential
def _model():
    name = "grounding_model_t10b"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "specs/evidence/0045/grounding_model.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


@pytest.mark.parametrize("seed", range(40))
def test_differential_against_reference_model_ii(tmp_path, seed):
    """Random challenge / context / resolve / confirm over three distinct-value edges (so F7 is outside the model's
    scope): per edge, the product's withholding equals model II's `gate`, and its open count and g(e) equal model II's
    `inspect`."""
    M = _model()
    rnd = random.Random(seed)
    mem = _mem(tmp_path)
    s, rules = M.Store(), M.Rules()
    objs = {"e-0": "alpha", "e-1": "bravo", "e-2": "charlie"}
    medges = {}
    for eid, obj in objs.items():
        att = rnd.choice(["attested", "not_attested", None])
        _plant(mem, _edge(eid, obj, relation=f"rel{eid[-1]}", att=att, attv="ATTEST-3@b1329a81", src="ep-1"))
        medges[eid] = s.edges[eid] = M.Edge(id=eid, user=U, relation=f"rel{eid[-1]}", obj=obj, att=att)
    ids: dict = {}                       # model reply id -> product reply id
    for step in range(12):
        eid = rnd.choice(list(objs))
        op = rnd.choice(["challenge", "context", "resolve", "confirm"])
        if op == "resolve":
            open_ = M.active_challenges(s, medges[eid])
            if not open_:
                continue
            c = rnd.choice(open_)
            M.add_reply(s, medges[eid], "resolve", None, target=c.id)
            _resolve(mem, eid, ids[c.id])
        elif op == "confirm":
            try:
                M.confirm(s, medges[eid], rules)
            except M.Refused:
                with pytest.raises(ValueError):            # store.confirm.active-challenge
                    mem.confirm(U, eid)
                continue
            _ok(mem.confirm, U, eid)
        else:
            mr = M.add_reply(s, medges[eid], op, f"t{step}")
            ids[mr.id] = _ok(mem.reply, U, eid, kind=op, text=f"t{step}")["reply_id"]
    r = _ok(mem.recall, U, " ".join(objs.values()))
    for eid in objs:
        want = M.inspect(s, medges[eid])
        got = _insp(r, eid)
        assert (got.challenge_clear, got.open_challenges, got.grounding) == \
            (M.gate(s, medges[eid]) == "assertable", want["open"], want["g"]), (seed, eid)
        assert _asserted(r, objs[eid]) == (M.gate(s, medges[eid]) == "assertable"), (seed, eid)


# ============================================================================================ research's T10b stage 2
# Ready cells (research, T10b stage 2 at 3914f73), written to be appended to tests/test_0047_t10b_read.py: they use its
# helpers. Each FAILS at 3914f73 by assertion and states the expected sets as literals.
def test_rs2_1_as_of_collapse_never_hides_a_twin_behind_a_withheld_survivor(tmp_path):
    """F7 (c) and Q9 on as-of recall: a challenged "cat Miso" and its act-less "Miso" twin are withheld and counted as
    two facts, each with an inspection entry, as query recall does. At 3914f73 as-of's collapse runs without the call's
    snapshot, so "Miso" is suppressed behind its withheld survivor: uncounted and uninspectable."""
    mem = _mem(tmp_path)
    t0, t1 = datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 6, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-1", "cat Miso", relation="has_pet", valid_from=t0),
           _edge("e-2", "Miso", relation="has_pet", valid_from=t1))
    _challenge(mem, "e-1")
    q = _ok(mem.recall, U, "pet Miso")
    r = _ok(mem.recall, U, "pet Miso", as_of=datetime(2025, 1, 1, tzinfo=timezone.utc))
    two = ["[withheld: 2 fact(s) the subject disputes; see the host's why()]"]
    assert (_withheld_ids(q), _withheld_line(q.grounded)) == ({"e-1", "e-2"}, two)
    assert (_withheld_ids(r), _withheld_line(r.grounded)) == ({"e-1", "e-2"}, two)


def test_rs2_2_as_of_collapse_never_suppresses_a_member_carrying_an_act(tmp_path):
    """Q10 on as-of recall: two strictly-redundant "chef" restatements, the hidden one ("e-old") confirmed: both
    surface, as on query recall. At 3914f73 as-of's collapse ignores acts and hides the confirmed one."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-old", "chef", valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc)),
           _edge("e-new", "chef", valid_from=datetime(2024, 6, 1, tzinfo=timezone.utc)))
    T = datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert {e.id for e in _ok(mem.recall, U, "chef", as_of=T).edges} == {"e-new"}       # the collapse, before the act
    _ok(mem.confirm, U, "e-old", correlation_id="k-1")
    assert {e.id for e in _ok(mem.recall, U, "chef").edges} == {"e-old", "e-new"}
    assert {e.id for e in _ok(mem.recall, U, "chef", as_of=T).edges} == {"e-old", "e-new"}


def test_rs2_3_collapse_never_hides_a_withheld_member_behind_a_clear_survivor(tmp_path):
    """F7 (c), the anchor case: "grey tabby cat" twins the challenged "grey tabby" (it adds one word); "tabby cat",
    note-bearing, is the group's survivor and twins nothing (neither subsumes the other). The twin is withheld and
    counted. At 3914f73 it is suppressed behind the clear survivor: uncounted, uninspectable, and its group's
    collapse is presented on the survivor."""
    mem = _mem(tmp_path)
    t0, t1 = datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 6, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-A", "grey tabby cat", relation="has_pet", valid_from=t0),
           _edge("e-m1", "grey tabby", relation="has_pet", valid_from=t1),
           _edge("e-m2", "tabby cat", relation="has_pet", valid_from=t1).model_copy(update={"note": "adopted"}))
    _challenge(mem, "e-m1")
    r = _ok(mem.recall, U, "pet grey tabby cat")
    assert _withheld_ids(r) == {"e-A", "e-m1"}, sorted(r.inspection)
    assert _withheld_line(r.grounded) == ["[withheld: 2 fact(s) the subject disputes; see the host's why()]"]


# ---------------------------------------------------------------- research's surviving mutants (each pinned at 3914f73)
def test_rs2_4_a_quarantined_twin_is_counted(tmp_path):
    """F7 (b) and (c): the cross-class twin is withheld AND counted. Mutant: the count drops the quarantined term."""
    mem = _mem(tmp_path)
    _miso(mem, "Miso", "Miso", author2=EA.THIRD_PARTY, disc2=Disclosure.QUARANTINED)
    r = _ok(mem.recall, U, "pet Miso")
    assert _withheld_line(r.grounded) == ["[withheld: 2 fact(s) the subject disputes; see the host's why()]"]


def test_rs2_5_a_challenged_use_only_fact_is_counted(tmp_path):
    """A use-only fact renders on query recall when unchallenged, so withholding it is counted. Mutant: the count
    drops the use-only term."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-a", "Lisbon harbour pilot", disc=Disclosure.USE_ONLY), _edge("e-b", "Porto", relation="lives_in"))
    assert "Lisbon harbour pilot" in _ok(mem.recall, U, "Lisbon harbour pilot Porto").context
    _challenge(mem, "e-a")
    r = _ok(mem.recall, U, "Lisbon harbour pilot Porto")
    assert "Lisbon harbour pilot" not in r.context and _withheld_line(r.grounded) == [WITHHELD_1]


def test_rs2_6_a_retired_challenged_record_is_not_counted_only_its_live_twin(tmp_path):
    """The retired challenged record is in `Recall.edges` and withheld, but it never rendered, so N counts only the
    live twin. Mutant: count every withheld edge."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-1", "Miso", relation="has_pet"))
    _challenge(mem, "e-1")
    mem.store.invalidate_edge("e-1", datetime.now(timezone.utc), "superseded")
    _plant(mem, _edge("e-2", "Miso", relation="has_pet"))
    r = _ok(mem.recall, U, "pet Miso")
    assert _withheld_ids(r) == {"e-1", "e-2"} and _withheld_line(r.grounded) == [WITHHELD_1]


def test_rs2_7_the_withheld_count_is_bounded_width():
    """The report line's count is `bounded_count`'s: exact to 999, then '999+'. Mutant: print N unbounded."""
    assert C.withheld_line(999) == "[withheld: 999 fact(s) the subject disputes; see the host's why()]"
    assert C.withheld_line(1000) == "[withheld: 999+ fact(s) the subject disputes; see the host's why()]"


def test_rs2_8_collapse_never_suppresses_a_member_carrying_a_reply(tmp_path):
    """Q10's act is a confirmation OR a reply: a `context` reply on the hidden restatement keeps it. Mutant: the
    snapshot's acted set reads confirmations only."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-old", "chef", valid_from=datetime(2025, 1, 1, tzinfo=timezone.utc)),
           _edge("e-new", "chef", valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    assert {e.id for e in _ok(mem.recall, U, "chef").edges} == {"e-new"}
    _ok(mem.reply, U, "e-old", kind="context", text="at the harbour restaurant")
    assert {e.id for e in _ok(mem.recall, U, "chef").edges} == {"e-old", "e-new"}


@pytest.mark.parametrize("subject,relation", [("sister", "has_pet"), ("user", "relative_of")])
def test_rs2_9_the_same_value_under_another_subject_or_relation_is_not_a_twin(tmp_path, subject, relation):
    """F7's "same value" is same subject AND relation. Mutants: the twin predicate ignores the subject; the relation."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-1", "Miso", relation="has_pet"))
    _challenge(mem, "e-1")
    _plant(mem, _edge("e-2", "Miso", relation=relation, subject=subject))
    r = _ok(mem.recall, U, "pet Miso sister relative")
    assert _withheld_ids(r) == {"e-1"} and _insp(r, "e-2").challenge_clear and _withheld_line(r.grounded) == [WITHHELD_1]


def test_rs2_10_a_procedural_record_is_never_a_twin(tmp_path):
    """INV-R19: a procedural record carries no reply and no grounding, so `why` reports it clear even when its value
    equals a challenged record's. Mutant: drop the procedural guard."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-1", "Miso", relation="has_pet"))
    _challenge(mem, "e-1")
    e2 = _edge("e-2", "Miso", relation="has_pet")
    _plant(mem, e2.model_copy(update={"provenance": e2.provenance.model_copy(update={"record_kind": "procedural"})}))
    ch = W.gather(mem.store, U, "e-2").challenge
    assert (ch["clear"], ch["withheld_by"], ch["waiting_on"]) == (True, [], [])


def test_rs2_11_as_of_an_out_of_view_challenger_withholds_an_in_view_twin_and_is_never_named(tmp_path):
    """(i) on the as-of carriers: the scoped `Recall.inspection` and `facts_valid_at`'s `AsOfFact.inspection` name no
    out-of-view record. Mutant: the as-of inspection ignores the reader's scope."""
    mem = _mem(tmp_path, groups=ONE_GROUP)
    t0, T = datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2025, 1, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("w1", "Miso", relation="has_pet", source_id="agent-2", valid_from=t0))
    _challenge(mem, "w1", "secret dispute text")
    _plant(mem, _edge("v2", "Miso", relation="has_pet", source_id="agent-1", valid_from=t0))
    r = _ok(mem.recall, U, "pet Miso", principal=A1, as_of=T)
    i = _insp(r, "v2")
    assert (i.challenge_clear, i.withheld_by, i.waiting_on) == (False, (), ())
    assert "w1" not in repr(r) and "secret dispute text" not in repr(r) and _withheld_line(r.grounded) == [WITHHELD_1]
    facts = {f.edge.id: f for f in _ok(mem.facts_valid_at, U, "user", "has_pet", T, principal=A1)}
    j = _asof_insp(facts["v2"])
    assert set(facts) == {"v2"} and (j.challenge_clear, j.withheld_by, j.waiting_on) == (False, (), ())


def test_rs2_12_proactive_recall_carries_an_inspection_entry_for_every_edge(tmp_path):
    """`Recall.inspection` on proactive recall: an entry per returned edge, with g(e) and its version. Mutant: omit it."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-b", "Porto", relation="lives_in", needs_confirmation=True, att="attested",
                      attv="ATTEST-3@b1329a81", src="ep-1"))
    r = _ok(mem.recall, U, None)
    assert {e.id for e in r.edges} == set(r.inspection) == {"e-b"}
    i = _insp(r, "e-b")
    assert (i.grounding, i.attestation_version, i.challenge_clear) == ("attested", "ATTEST-3@b1329a81", True)


_RS2_VARIANTS = {"plain": {}, "flagged": {"needs_confirmation": True}, "ungrounded": {"ungrounded": True},
                 "third-party-quarantined": {"author": EA.THIRD_PARTY, "disc": Disclosure.QUARANTINED},
                 "use-only": {"disc": Disclosure.USE_ONLY}, "system-authored": {"author": EA.SYSTEM},
                 "flagged-third-party-quarantined": {"needs_confirmation": True, "author": EA.THIRD_PARTY,
                                                     "disc": Disclosure.QUARANTINED}}


@pytest.mark.parametrize("variant", sorted(_RS2_VARIANTS))
@pytest.mark.parametrize("surface", ["query", "proactive", "as-of"])
def test_rs2_13_the_withheld_count_is_exactly_what_the_challenge_stopped_rendering(tmp_path, surface, variant):
    """"The silence is not silent", read both ways: on every assertion surface, a challenge withholds a fact the surface
    rendered (counted 1), and a fact the surface would never have shown is not counted (counted 0). FAILS at 3914f73 on
    proactive for the plain, ungrounded and system-authored facts: proactive counts every assertable challenged fact
    in view, including those it never volunteers (api.md: N counts this answer's candidates)."""
    mem = _mem(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-a", "Lisbon harbour pilot", valid_from=t0, **_RS2_VARIANTS[variant]),
           _edge("e-b", "Porto", relation="lives_in", valid_from=t0))
    call = {"query": lambda: mem.recall(U, "Lisbon harbour pilot Porto"),
            "proactive": lambda: mem.recall(U, None),
            "as-of": lambda: mem.recall(U, "Lisbon harbour pilot Porto",
                                        as_of=datetime(2025, 1, 1, tzinfo=timezone.utc))}[surface]
    before = "Lisbon harbour pilot" in _ok(call).context
    _challenge(mem, "e-a")
    r = _ok(call)
    assert "Lisbon harbour pilot" not in r.context
    assert _withheld_line(r.context) == ([WITHHELD_1] if before else []), (before, _withheld_line(r.context))


def test_t10b_s2_1_a_scoped_as_of_answer_carries_its_three_fields_and_no_snapshot(tmp_path):
    """Research's T10b S2-1, the design call: as-of recall's collapse reads the call's ONE challenge snapshot, which
    travels BESIDE the public `AsOfAnswer` (`_resolve_as_of` returns the pair), never on it. The snapshot holds every
    challenged record of the user, out-of-view ones included, so a field would hand a principal-scoped caller what
    0020 N-2 hides; equality and repr cannot see a `compare=False, repr=False` field, so this asserts the fields.
    Mutant: the candidate's `snapshot` field on `AsOfAnswer`."""
    import dataclasses
    from veracium.asof import resolve_as_of
    mem = _mem(tmp_path, groups=ONE_GROUP)
    t0, T = datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2025, 1, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("w1", "Miso", relation="has_pet", source_id="agent-2", valid_from=t0))
    _challenge(mem, "w1", "secret dispute text")
    _plant(mem, _edge("v2", "Miso", relation="has_pet", source_id="agent-1", valid_from=t0))
    a = resolve_as_of(mem.store, U, T, principal=A1, policy=mem.scope_policy)
    assert [f.name for f in dataclasses.fields(a)] == ["T", "now", "facts"] and set(vars(a)) == {"T", "now", "facts"}
    assert {f.edge.id for f in a.facts} == {"v2"}
    assert "w1" not in repr(vars(a)) and "secret dispute text" not in repr(vars(a))


def test_t10b_s2_5_introspect_marks_a_withheld_restatement(tmp_path):
    """Research's T10b S2-5: `introspect(mode="categories")` carries the unit on the challenged fact's line AND why()'s
    phrase on its same-value restatement's (operator-side, like why: it names the record). Mutant: the twin line
    printed plain."""
    mem = _mem(tmp_path)
    _plant(mem, _edge("e-1", "Miso", relation="has_pet"), _edge("e-2", "cat Miso", relation="has_pet"))
    _challenge(mem, "e-1")
    lines = mem.introspect(U, mode="categories")["categories"]["has_pet"]
    assert [l for l in lines if "[withheld: same value as challenged e-1]" in l] == [
        l for l in lines if "cat Miso" in l] and len(lines) == 2
    assert [l for l in lines if "[challenged by the subject: 1 open;" in l and "cat Miso" not in l] != []


def test_t10b_s2_2_a_clear_member_behind_a_withheld_survivor_renders(tmp_path):
    """F7 (c)'s other side, after S2-2: the survivor "grey tabby cat" (note-bearing) twins the challenged "grey tabby"
    and is withheld; "tabby cat" in its group twins nothing (neither subsumes "grey tabby"), so it is CLEAR and must
    render, not vanish behind a survivor that is itself withheld. Mutant: drop `snap.withheld(survivor)` from the keep
    test (`snap.withheld(m)` alone does not keep a clear member)."""
    mem = _mem(tmp_path)
    t0, t1 = datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 6, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-S", "grey tabby cat", relation="has_pet", valid_from=t0).model_copy(update={"note": "adopted"}),
           _edge("e-X", "grey tabby", relation="has_pet", valid_from=t1),
           _edge("e-m", "tabby cat", relation="has_pet", valid_from=t1))
    assert {e.id for e in _ok(mem.recall, U, "pet grey tabby cat").edges} == {"e-S"}      # the collapse, before the act
    _challenge(mem, "e-X")
    r = _ok(mem.recall, U, "pet grey tabby cat")
    assert _withheld_ids(r) == {"e-S", "e-X"} and _insp(r, "e-m").challenge_clear
    assert "has_pet: tabby cat (since 2024-06-01)" in r.context
    assert _withheld_line(r.grounded) == ["[withheld: 2 fact(s) the subject disputes; see the host's why()]"]


def test_t10b_s2_3_proactive_never_counts_a_flagged_ungrounded_fact_it_never_volunteers(tmp_path):
    """S2-3's ungrounded term: a FLAGGED fact is eligible for proactive, but an ungrounded one is never volunteered, so
    withholding it is not counted. (rs2_13's ungrounded variant is settled, so eligibility alone already excludes it.)
    Mutant: drop `not e.ungrounded` from proactive's count."""
    mem = _mem(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _plant(mem, _edge("e-a", "Lisbon harbour pilot", valid_from=t0, needs_confirmation=True, ungrounded=True),
           _edge("e-b", "Porto", relation="lives_in", valid_from=t0))
    assert "Lisbon harbour pilot" not in _ok(mem.recall, U, None).context
    _challenge(mem, "e-a")
    assert _withheld_line(_ok(mem.recall, U, None).context) == []
