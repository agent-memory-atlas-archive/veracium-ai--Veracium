"""specs/0045 (v1.13, ACCEPTED, design) — T9, the declarative grounding axis's WRITE half.

One cell per §6 row T9 makes product-true (INV-G1, G2 wired, G6, G7, G9 write, G10, G11, G12, G13 write), plus the
owner's D6 binding (ATTEST-3 vendored byte-identical), the source-redacted guard's consolidation case (the owner's
F1(a)), research's T9 stage-1 cells (F2, F3, F5, F7, F8) and the import window (Q6). Each goes through `Memory` on a
real SqliteStore with a scripted extractor unless it says "pure". The scratch campaign is t9_mutant_defs.py.
"""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import pathlib
import sqlite3
import sys
from datetime import datetime, timezone

import pytest

from veracium import EvidenceAuthor, EvidenceContext, Memory, MemoryConfig
from veracium import attest_v3, attestation
from veracium.attestation import (DEFAULT_IMPORT, NON_USER_EFFECTIVE, PREDICATE_VERSION, declarative_grounding,
                                  valid_attv)
from veracium.lifecycle import consolidate
from veracium.schema import Edge, Episode, Provenance
from veracium.store.sqlite import SqliteStore

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATTEST = ROOT / "specs" / "evidence" / "0045" / "attest"
U = "u1"
DIRECT = EvidenceContext.direct()
NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)


class _Fake:
    """A scripted distiller; every other role answers nothing."""

    def __init__(self, scripts):
        self._s = list(scripts)

    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        return json.dumps(self._s.pop(0)) if role == "distill" else ""


def _script(relation, obj, *, subject="user", episode="the user said something", **extra):
    return {"triples": [{"subject": subject, "relation": relation, "object": obj, "volatility": "durable", **extra}],
            "episode": episode}


def _mem(tmp_path, scripts, name="m.db"):
    return Memory(llm=_Fake(scripts), config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0))


def _edges(mem, user=U):
    return [e for e in mem.store.edges(user, active_only=False, include_quarantined=True) if not e.provenance.procedural]


def _one(mem, user=U):
    es = _edges(mem, user)
    assert len(es) == 1, [(e.id, e.object) for e in es]
    return es[0]


def _ok(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as exc:                                       # noqa: BLE001 — a raise is the property failing
        raise AssertionError(f"expected success; raised {type(exc).__name__}: {exc}") from exc


def _refuses(fn, *a, match, **k):
    try:
        fn(*a, **k)
    except ValueError as exc:
        assert match in str(exc), str(exc)
        return exc
    except Exception as exc:                                       # noqa: BLE001
        raise AssertionError(f"expected ValueError({match!r}); raised {type(exc).__name__}: {exc}") from exc
    raise AssertionError(f"expected ValueError({match!r}); nothing was raised")


def _q(mem, sql, args=()):
    c = sqlite3.connect(mem.config.db_path)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def _plant(mem, eid, *, att, src, attv=PREDICATE_VERSION, obj="dentist"):
    """A declarative edge with a chosen axis, written through the store (the fixture for the guard cells)."""
    e = Edge(id=eid, user_id=U, subject="user", relation="works_as", object=obj,
             provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref=f"ev-{eid}"),
             att=att, src=src, attv=attv if att is not None else None)
    mem.store.add_edge(e)
    return e


def _episode(mem, eid, *, date="2026-10-01", summary="s"):
    mem.store.add_episode(Episode(id=eid, user_id=U, date=date, summary=summary,
                                  provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref=eid)))


# ======================================================================================== D6
def test_d6_the_vendored_predicate_is_the_frozen_file_byte_for_byte():
    """The owner's D6 (2026-10-18): ATTEST-3 enters src VENDORED BYTE-IDENTICAL. `attv` names the frozen file's
    digest, so the module ingest runs must BE that file; the version literal is bound to it here, never computed
    (research's T9 F9). Mutant: the vendored copy edited (one table entry)."""
    vendored = (ROOT / "src" / "veracium" / "attest_v3.py").read_bytes()
    assert vendored == (ATTEST / "attest_v3.py").read_bytes()
    digest = hashlib.sha256(vendored).hexdigest()
    assert f"{attest_v3.VERSION}@{digest[:8]}" == "ATTEST-3@b1329a81"
    # specs/0051 §4a: the write path's version is ATTEST-6, whose verdict is a function of this file AND attest_turns.py;
    # its literal is bound to both digests by test_0051_speaker_turns.py::test_inv_s5_the_version_names_both_frozen_files
    assert PREDICATE_VERSION == "ATTEST-6@ccabb664"
    assert attest_v3.__file__.endswith(str(pathlib.Path("src", "veracium", "attest_v3.py")))


# ======================================================================================== INV-G1 / G9 / G13 (write)
def test_inv_g1_a_grounding_claim_in_the_extractor_output_is_ignored(tmp_path):
    """INV-G1: `att` comes only from ATTEST over the raw text. A triple claiming its own grounding, on a statement
    ATTEST does not attest, is stored `not_attested`. Mutant: honour the extractor's field."""
    mem = _mem(tmp_path, [_script("works_as", "chef", att="attested", attv="ATTEST-9@00000000", grounded=True,
                                  src="ep-forged")])
    _ok(mem.remember, U, "we talked about restaurants for an hour", date="2026-10-01", context=DIRECT)
    e = _one(mem)
    assert (e.att, e.attv) == ("not_attested", PREDICATE_VERSION) and e.src != "ep-forged"


def test_inv_g9_label_dont_block_and_inv_g13_the_version_from_the_evaluation(tmp_path, monkeypatch):
    """INV-G9 (write half): a USER-effective statement is ALWAYS stored — attested if ATTEST recognises it, else
    `not_attested`, never refused or demoted; a non-user unflagged triple is stored `not_attested`; a non-user flagged
    one is refused and counted (0019 v7, T2). INV-G13 (write half): `attv` is the predicate version for a USER-effective
    write and `non-user-effective` for every other, where the predicate is NOT called. `src` is the event's episode.
    Mutants: an unrecognised user statement not stored; the predicate version recorded for a non-user write."""
    mem = _mem(tmp_path, [_script("works_as", "dentist"), _script("works_as", "chef"),
                          _script("works_as", "pilot"), _script("deadline", "fabricated deadline 2026-08-10")])
    _ok(mem.remember, "a", "I work as a dentist.", date="2026-10-01", context=DIRECT)
    _ok(mem.remember, "b", "we talked about restaurants", date="2026-10-01", context=DIRECT)
    calls = []
    real = attest_v3.attests
    monkeypatch.setattr(attest_v3, "attests", lambda *a: calls.append(a) or real(*a))
    _ok(mem.remember, "c", "I work as a pilot.", date="2026-10-01")             # no context: the 0011 floor, non-user
    out = _ok(mem.remember, "d", "the deadline is not decided", date="2026-10-01", author=EvidenceAuthor.THIRD_PARTY, source_id="feed-1")
    a, b, c = _one(mem, "a"), _one(mem, "b"), _one(mem, "c")
    assert (a.att, a.attv) == ("attested", PREDICATE_VERSION)
    assert (b.att, b.attv) == ("not_attested", PREDICATE_VERSION) and b.assertable      # stored, not demoted
    assert (c.att, c.attv) == ("not_attested", NON_USER_EFFECTIVE) and calls == []     # no predicate ran
    assert out["nonuser_ungrounded_refused"] == 1 and _edges(mem, "d") == []
    for e, user in ((a, "a"), (b, "b"), (c, "c")):
        assert e.src is not None and e.src in {ep.id for ep in mem.store.episodes(user)}


def test_inv_g13_the_axis_is_immutable_and_two_versions_coexist(tmp_path):
    """INV-G13: `attv` (and `att`, `src`) is never rewritten — a same-id replace changing any of the three refuses,
    nothing written; a row written by another predicate version (planted `ATTEST-2@e1e1e3d3`) coexists with
    ATTEST-3's and neither is relabelled by recall, maintain or confirm; an `attv` outside the grammar refuses at
    construction. Mutants: the replace guard dropped; the grammar check dropped."""
    mem = _mem(tmp_path, [_script("works_as", "dentist")])
    _ok(mem.remember, U, "I work as a dentist.", date="2026-10-01", context=DIRECT)
    e = _one(mem)
    old = _plant(mem, "old-v2", att="attested", src=None, attv="ATTEST-2@e1e1e3d3", obj="baker")
    for field, value in (("att", "not_attested"), ("src", "ep-other"), ("attv", "ATTEST-4@00000000")):
        _refuses(mem.store.add_edge, e.model_copy(update={field: value}), match=f"cannot change {field}")
    _ok(mem.recall, U, "dentist baker")
    mem.maintain(U)
    _ok(mem.confirm, U, old.id, correlation_id="k-old")
    by_id = {x.id: x for x in mem.store.edges(U, active_only=False, include_quarantined=True)}
    assert (by_id[e.id].att, by_id[e.id].attv) == ("attested", PREDICATE_VERSION)
    assert (by_id[old.id].att, by_id[old.id].attv) == ("attested", "ATTEST-2@e1e1e3d3")
    for bad in ("ATTEST-３@b1329a81", "ATTEST-03@b1329a81", "ATTEST-3@b1329a81x", "ATTEST-3@B1329A81", "nonsense"):
        assert not valid_attv(bad)
        with pytest.raises(ValueError):
            Edge(id="x", user_id=U, subject="user", relation="works_as", object="o",
                 provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r"), att="attested",
                 attv=bad)


def test_f7_the_model_admits_only_the_axis_states_0045_allows():
    """Research's T9 F7: `att` with `attv` NULL is admitted (a trusted restore's version-less row); `attv` or `src`
    without `att` refuses; any of the three on a procedural row refuses. Mutant: `src` admitted without `att`."""
    P = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r")
    base = dict(id="x", user_id=U, subject="user", relation="works_as", object="o", provenance=P)
    assert Edge(**base, att="attested").attv is None
    for kw in ({"attv": DEFAULT_IMPORT}, {"src": "ep-1"}):
        with pytest.raises(ValueError):
            Edge(**base, **kw)
    proc = dict(base, provenance=P.model_copy(update={"record_kind": "procedural"}))
    for kw in ({"att": "not_attested"}, {"att": "not_attested", "attv": NON_USER_EFFECTIVE}):
        with pytest.raises(ValueError):
            Edge(**proc, **kw)


# ======================================================================================== INV-G2 (wired)
def _h2():
    return json.loads((ATTEST / "holdout_h2.json").read_text())


def test_inv_g2_h2_reproduced_through_remember_item_for_item(tmp_path, monkeypatch):
    """INV-G2, wired (research's T9 F5): every H2 item through REAL ingest — its gold triple scripted, a declared-direct
    USER event with the item's text — is stored `attested` exactly where ATTEST-3 attests it directly: 12 / 53 recall,
    1 / 67 false attestations, item for item. A non-user control over the same items attests none, and the predicate
    is never called. Mutants: the write path calling ATTEST-2; the subject or relation passed wrongly."""
    items = _h2()
    mem = _mem(tmp_path, [_script(i["relation"], i["object"], episode=f"item {i['id']}") for i in items])
    for i in items:
        _ok(mem.remember, f"h2-{i['id']}", i["text"], date="2026-10-01", context=DIRECT)
    got = {i["id"]: _one(mem, f"h2-{i['id']}").att == "attested" for i in items}
    direct = {i["id"]: attest_v3.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED" for i in items}
    assert got == direct
    tp = sum(1 for i in items if got[i["id"]] and i["gold"])
    fp = sum(1 for i in items if got[i["id"]] and not i["gold"])
    assert (tp, sum(i["gold"] for i in items), fp, sum(not i["gold"] for i in items)) == (12, 53, 1, 67)
    monkeypatch.setattr(attest_v3, "attests", lambda *a: (_ for _ in ()).throw(AssertionError("predicate called")))
    ctrl = _mem(tmp_path, [_script(i["relation"], i["object"]) for i in items], name="ctrl.db")
    for i in items:
        _ok(ctrl.remember, f"n-{i['id']}", i["text"], date="2026-10-01")        # undeclared: non-user-effective
    assert all(_one(ctrl, f"n-{i['id']}").att == "not_attested" for i in items)


def test_inv_g2_r2_01_negatives_through_real_ingest_stay_not_attested(tmp_path):
    """Three R2-01 constructions (a supposition, a prefix of the complement, a quotation spanning sentences) through
    real ingest, declared-direct: `not_attested`. Mutant: a prefix of the complement accepted."""
    cases = [("works_as", "dentist", "Suppose I work as a dentist."),
             ("works_as", "dentist", "I work as a dentist assistant."),
             ("works_as", "dentist", 'He wrote: "I work as a. dentist." Funny.')]
    mem = _mem(tmp_path, [_script(r, o) for r, o, _t in cases])
    for n, (_r, _o, text) in enumerate(cases):
        _ok(mem.remember, f"n{n}", text, date="2026-10-01", context=DIRECT)
        assert _one(mem, f"n{n}").att == "not_attested", text


# ======================================================================================== INV-G6 / G7
def test_inv_g6_the_label_never_reaches_query_time(tmp_path):
    """INV-G6: the write labels, it never filters — a `not_attested` fact is recalled and rendered exactly like an
    `attested` one. Mutant: the ingest rule applied at recall (`not_attested` dropped from the context)."""
    mem = _mem(tmp_path, [_script("works_as", "dentist"), _script("located_at", "Porto")])
    _ok(mem.remember, U, "I work as a dentist.", date="2026-10-01", context=DIRECT)
    _ok(mem.remember, U, "we discussed the coast near Porto", date="2026-10-01", context=DIRECT)
    atts = {e.object: e.att for e in _edges(mem)}
    assert atts == {"dentist": "attested", "Porto": "not_attested"}
    r = _ok(mem.recall, U, "where does the user live and work")
    assert "dentist" in r.context and "Porto" in r.context
    assert {e.object for e in r.edges} >= {"dentist", "Porto"}


def test_inv_g7_a_legacy_row_reads_unknown_and_is_never_rewritten(tmp_path):
    """INV-G7: a row written before this spec (`att` NULL) reads `unknown`, never `attested`, and nothing — recall,
    maintain, confirm — writes an `att` onto it. Mutant: NULL read as `attested`."""
    mem = _mem(tmp_path, [])
    legacy = _plant(mem, "legacy", att=None, src=None)
    assert declarative_grounding(legacy, []) == "unknown"
    _ok(mem.recall, U, "dentist")
    mem.maintain(U)
    _ok(mem.confirm, U, "legacy", correlation_id="k-legacy")
    row = json.loads(_q(mem, "SELECT json FROM edges WHERE id='legacy'")[0][0])
    assert "att" not in row and "attv" not in row and "src" not in row


# ======================================================================================== INV-G10 and the guard's cases
def _redact_episode(mem, eid):
    _ok(mem.redact, U, episode_id=eid, reason="subject_request")


def test_inv_g10_confirm_refuses_a_not_attested_edge_whose_source_is_redacted(tmp_path):
    """INV-G10 through real ingest: after `Memory.redact(episode_id=src)`, `confirm()` on the `not_attested` edge
    refuses — state it anew — and writes nothing. Mutant: the guard dropped."""
    mem = _mem(tmp_path, [_script("works_as", "chef")])
    _ok(mem.remember, U, "we talked about restaurants", date="2026-10-01", context=DIRECT)
    e = _one(mem)
    assert e.att == "not_attested" and e.src
    _redact_episode(mem, e.src)
    v0 = mem.store.store_version(U)
    _refuses(mem.confirm, U, e.id, correlation_id="k1", match="source episode was redacted")
    assert _q(mem, "SELECT COUNT(*) FROM confirmations")[0][0] == 0 and mem.store.store_version(U) == v0


def test_inv_g10_controls_attested_standing_legacy_and_sourceless_confirm(tmp_path):
    """INV-G10's controls (0045 §4d's boundary): an `attested` edge whose source is redacted confirms; a
    `not_attested` edge whose source stands confirms; a legacy row and a `src`-less row confirm. Mutant: the guard
    on `attested` too (the uniform rule §4d declines)."""
    mem = _mem(tmp_path, [])
    for ep in ("ep-r", "ep-s"):
        _episode(mem, ep)
    _plant(mem, "att-r", att="attested", src="ep-r")
    _plant(mem, "not-s", att="not_attested", src="ep-s", obj="chef")
    _plant(mem, "leg", att=None, src=None, obj="pilot")
    _plant(mem, "nosrc", att="not_attested", src=None, obj="nurse")
    _redact_episode(mem, "ep-r")
    for eid in ("att-r", "not-s", "leg", "nosrc"):
        _ok(mem.confirm, U, eid, correlation_id=f"k-{eid}")


def test_inv_g10_a_completed_confirmation_replays_and_a_confirmed_edge_reconfirms(tmp_path):
    """The registry is read first (0008 v8): a completed confirmation replays after its source's redaction. And the
    guard is scoped by g(e), not by `att` (research's T9 F2): a `not_attested` edge already confirmed LOCALLY is
    `confirmed`, so a NEW confirmation after the redaction is admitted. Mutant: the guard reading `att`."""
    mem = _mem(tmp_path, [])
    _episode(mem, "ep-1")
    _plant(mem, "e1", att="not_attested", src="ep-1")
    first = _ok(mem.confirm, U, "e1", correlation_id="k1")
    _redact_episode(mem, "ep-1")
    assert _ok(mem.confirm, U, "e1", correlation_id="k1")["replayed"]
    assert not _ok(mem.confirm, U, "e1", correlation_id="k2")["replayed"]
    assert first


def test_f2_an_imported_confirmation_is_testimony_and_does_not_lift_the_guard(tmp_path):
    """Research's T9 F2 (0047 INV-R21: only `local` and `restored` confirmations count): an edge whose only confirmation is IMPORTED (testimony, 0047 §4f) is still `not_attested`,
    so the guard refuses. Mutant: `imported` counted as confirming."""
    mem = _mem(tmp_path, [])
    _episode(mem, "ep-1")
    _plant(mem, "e1", att="not_attested", src="ep-1")
    c = sqlite3.connect(mem.config.db_path)
    c.execute("INSERT INTO confirmations(id, user_id, edge_id, confirmed_at, actor, call_path, correlation_id, "
              "request_digest, origin, act_seq) VALUES('ci', ?, 'e1', '2026-10-01T00:00:00+00:00', 'user', 'host_api', "
              "'imp-1', 'd', 'imported', NULL)", (U,))
    c.commit()
    c.close()
    _redact_episode(mem, "ep-1")
    _refuses(mem.confirm, U, "e1", correlation_id="k2", match="source episode was redacted")


def test_q3_a_pending_notice_does_not_refuse(tmp_path):
    """Q3 (research agreed): the guard reads APPLIED notices only (0041 §11.6.6: a pending notice redacts nothing this
    store holds). The same notice held PENDING confirms; applied, refuses. Mutant: the guard reading every notice."""
    mem = _mem(tmp_path, [])
    _episode(mem, "ep-1")
    _plant(mem, "e1", att="not_attested", src="ep-1")
    _redact_episode(mem, "ep-1")
    c = sqlite3.connect(mem.config.db_path)
    c.execute("UPDATE redactions SET state='pending' WHERE target_id='ep-1'")
    c.commit()
    c.close()
    _ok(mem.confirm, U, "e1", correlation_id="k1")


def test_f1a_the_guard_follows_consolidation_lineage(tmp_path):
    """The owner's F1(a) (2026-10-18; research's T9 probe): past consolidation the source episode is deleted and its
    content lives in an OUTPUT whose lineage names it in historical form; redacting the output must still refuse the
    confirmation. Mutant: the guard reading `src` alone."""
    mem = _mem(tmp_path, [])
    for i in range(1, 9):
        mem.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i:02d}", summary=f"day {i}",
                                      provenance=Provenance(author_of_evidence=EvidenceAuthor.USER,
                                                            evidence_ref=f"r{i}",
                                                            observed_at=datetime(2026, 1, i, tzinfo=timezone.utc))))
    _plant(mem, "e1", att="not_attested", src="ep-1")
    llm = lambda *a, **k: json.dumps({"records": [{"date": "2026-01-01", "summary": "merged"}]})  # noqa: E731
    consolidate(mem.store, llm, U, MemoryConfig(consolidate_after_days=30, consolidate_min_batch=8), now=NOW)
    live = {ep.id: ep for ep in mem.store.episodes(U)}
    assert "ep-1" not in live
    out = next(ep for ep in live.values() if ep.lineage)
    _redact_episode(mem, out.id)
    _refuses(mem.confirm, U, "e1", correlation_id="k1", match="source episode was redacted")


def test_f1b_a_deleted_source_names_nothing_and_confirm_is_allowed(tmp_path):
    """The owner's F1(b), STATED: a source deleted outright (`delete_episode`) leaves `src` naming no episode and no
    lineage, so nothing shows an erasure and confirm is allowed."""
    mem = _mem(tmp_path, [])
    _episode(mem, "ep-1")
    _plant(mem, "e1", att="not_attested", src="ep-1")
    mem.store.delete_episode("ep-1")
    _ok(mem.confirm, U, "e1", correlation_id="k1")


# ======================================================================================== INV-G11 / G12 / F8
def test_inv_g11_an_absorbed_survivor_carries_the_incomings_axis(tmp_path):
    """INV-G11 (0045 §4e): absorption's survivor IS the incoming row, so its `att`, `src` and `attv` are its own,
    never the prior's — in both directions (an attested prior under a not_attested incoming, and the reverse). The
    fixture ABSORBS (one extra token, within graph's bound; the prior retires `absorbed_duplicate`, asserted), so the
    cell reaches the absorption branch, not supersession. Mutant: copy the prior's `att` onto the survivor."""
    for prior_text, inc_text, want in (("I work as a dentist.", "Started at the clinic in an orthodontic dentist role",
                                        "not_attested"),
                                       ("we chatted about teeth today", "I work as an orthodontic dentist.",
                                        "attested")):
        d = tmp_path / want
        d.mkdir()
        mem = _mem(d, [_script("works_as", "dentist", episode="first"),
                       _script("works_as", "orthodontic dentist", episode="second")])
        _ok(mem.remember, U, prior_text, date="2026-10-01", context=DIRECT)
        prior = _one(mem)
        _ok(mem.remember, U, inc_text, date="2026-10-02", context=DIRECT)
        by_obj = {e.object: e for e in _edges(mem)}
        assert by_obj["dentist"].invalidation_reason == "absorbed_duplicate", by_obj["dentist"].invalidation_reason
        survivor = by_obj["orthodontic dentist"]
        assert survivor.invalidated_at is None and prior.att != want      # the fixture: the two axes differ
        assert (survivor.att, survivor.attv) == (want, PREDICATE_VERSION) and survivor.src != prior.src


def test_inv_g12_a_procedural_row_carries_no_axis(tmp_path):
    """INV-G12: a procedural record — `record_procedure` and the quote-gated capture alike — carries no `att`, `src`
    or `attv`, and `g(e)` is None for it; an att-less procedural insert is admitted; a declarative control from a
    declared-direct event carries all three. Mutant: the ingest exemption for procedural rows dropped."""
    mem = _mem(tmp_path, [_script("works_as", "dentist")])
    pid = _ok(mem.record_procedure, U, "I review invoices every Friday", author=EvidenceAuthor.USER,
                    context=EvidenceContext.direct(basis="stated"))
    proc = next(e for e in mem.store.edges(U, active_only=False, include_quarantined=True) if e.id == pid)
    assert (proc.att, proc.src, proc.attv) == (None, None, None) and declarative_grounding(proc, []) is None
    _ok(mem.remember, U, "I work as a dentist.", date="2026-10-01", context=DIRECT)
    d = _one(mem)
    assert d.att == "attested" and d.attv and d.src


def test_f8_correct_writes_a_label_less_successor(tmp_path):
    """The owner's F8 (2026-10-18), STATED: `correct()` writes its successor with `att` NULL, which reads `unknown`;
    labelling corrections is NEXT-ROUND. It is no way round the guard: the guard reads only `not_attested` rows."""
    mem = _mem(tmp_path, [_script("works_as", "dentist")])
    _ok(mem.remember, U, "I work as a dentist.", date="2026-10-01", context=DIRECT)
    e = _one(mem)
    _ok(mem.correct, U, e.id, "orthodontist")
    succ = next(x for x in mem.store.edges(U, active_only=True) if x.object == "orthodontist")
    assert succ.att is None and declarative_grounding(succ, []) == "unknown"


# ======================================================================================== Q6, F3: the import window
def test_q6_export_carries_the_axis_and_default_import_stamps_it(tmp_path):
    """Q6, as T11b opens the axis's era (format 14, 0045 §4f; this cell's T9 form pinned the strip): an export carries
    each declarative edge's `att`/`src`/`attv` as held and a procedural record's none; a DEFAULT import discards the
    file's values and stamps every declarative row `not_attested`, `src` NULL, `default-import` (0045 §4e: whatever the
    file says); a forged `attested` in the file is never written. A procedural record never reaches the stamp in
    default mode (0037 refuses it, asserted), so F3(a)'s exemption is defence in depth and its mutant is EQUIVALENT at
    T9 (stated in t9_mutant_defs.py). Mutants: export dropping the axis; the file's `att` honoured."""
    src_mem = _mem(tmp_path, [_script("works_as", "dentist")], name="src.db")
    _ok(src_mem.remember, U, "I work as a dentist.", date="2026-10-01", context=DIRECT)
    _ok(src_mem.record_procedure, U, "I review invoices every Friday", author=EvidenceAuthor.USER,
                    context=EvidenceContext.direct(basis="stated"))
    path = tmp_path / "out.jsonl"
    src_mem.export_memory(U, path)
    lines = [json.loads(l) for l in path.read_text().splitlines()[1:]]
    held = {e.id: e for e in src_mem.store.edges(U, active_only=False, include_quarantined=True)}
    for r in (r for r in lines if r.get("record") == "edge"):
        if held[r["id"]].provenance.procedural:
            assert all(k not in r for k in ("att", "src", "attv"))
        else:
            assert (r["att"], r["src"], r["attv"]) == (held[r["id"]].att, held[r["id"]].src, held[r["id"]].attv)
    for r in lines:
        if r.get("record") == "edge" and not (r.get("provenance") or {}).get("record_kind"):
            r.update(att="attested", attv="ATTEST-3@b1329a81", src="ep-forged")     # a forged label in the file
    path.write_text(path.read_text().splitlines()[0] + "\n" + "\n".join(json.dumps(r) for r in lines) + "\n")
    dst = _mem(tmp_path, [], name="dst.db")
    r = _ok(dst.import_memory, path)
    # a DEFAULT import refuses procedural records outright (0037), so F3(a)'s exemption is defence in depth there
    assert r["procedural_refused"] == 1, r
    for e in dst.store.edges(U, active_only=False, include_quarantined=True):
        if e.provenance.procedural:
            assert (e.att, e.src, e.attv) == (None, None, None)
        else:
            assert (e.att, e.src, e.attv) == ("not_attested", None, DEFAULT_IMPORT)


def test_f3c_a_stores_own_export_reimports_idempotently_in_both_modes(tmp_path):
    """Research's T9 F3(c) and its addendum (1): the stamp is a write rule, so record equality excludes the axis in
    BOTH modes. A DEFAULT re-import of a store's own export of a third-party edge is a skip (as at 56f3d95; a USER
    edge's default re-import was already refused before T9, by the provenance cap, and stays so), and a TRUSTED
    restore of a store's own export into itself is a skip for a USER-effective and a third-party edge alike.
    Mutant: the held comparison includes the three fields."""
    def store_with(d, scripts, calls):
        d.mkdir()
        mem = _mem(d, scripts)
        for text, kw in calls:
            _ok(mem.remember, U, text, date="2026-10-01", **kw)
        path = d / "self.jsonl"
        mem.export_memory(U, path)
        return mem, path

    def records(path):                       # every record of the file is skipped (edges AND episodes)
        return sum(1 for l in path.read_text().splitlines()[1:] if json.loads(l).get("record") in ("edge", "episode"))

    def edges(mem):
        return sorted(e.model_dump_json() for e in mem.store.edges(U, active_only=False, include_quarantined=True))

    tp = ("they live in Porto", {"author": EvidenceAuthor.THIRD_PARTY, "source_id": "feed-1"})
    mem, path = store_with(tmp_path / "default", [_script("located_at", "Porto")], [tp])
    before = edges(mem)
    assert _ok(mem.import_memory, path)["skipped"] == records(path) and edges(mem) == before
    mem, path = store_with(tmp_path / "restore", [_script("works_as", "dentist"), _script("located_at", "Porto")],
                           [("I work as a dentist.", {"context": DIRECT}), tp])
    before = edges(mem)
    assert _ok(mem.import_memory, path, restore=True)["skipped"] == records(path) and edges(mem) == before


# ======================================================================================== g(e) (pure)
def test_declarative_grounding_agrees_with_model_ii_over_the_whole_small_domain():
    """Pure. `declarative_grounding` against model II's `grounding` over every (att, procedural, confirmation-origin
    set) — att in {attested, not_attested, NULL}, origins any subset of {local, restored, imported}. Mutant: `imported`
    counted as confirming."""
    spec = importlib.util.spec_from_file_location("grounding_model_0045_t9", ROOT / "specs" / "evidence" / "0045" /
                                                  "grounding_model.py")
    G = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = G
    spec.loader.exec_module(G)
    P = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r")
    n = 0
    for att, proc in itertools.product(("attested", "not_attested", None), (False, True)):
        for k in range(4):
            for origins in itertools.combinations(("local", "restored", "imported"), k):
                prov = P.model_copy(update={"record_kind": "procedural"}) if proc else P
                e = Edge(id="e", user_id=U, subject="user", relation="works_as", object="o", provenance=prov,
                         att=None if proc else att, attv=None if (proc or att is None) else PREDICATE_VERSION)
                s = G.Store()
                s.confirmations = [G.Confirmation(id=f"k{i}", edge="e", pos=(0, i), user=U, request_digest="d",
                                                  confirmed_at=0, origin=o) for i, o in enumerate(origins)]
                me = G.Edge(id="e", user=U, relation="works_as", obj="o", att=None if proc else att, procedural=proc)
                assert declarative_grounding(e, list(origins)) == G.grounding(s, me), (att, proc, origins)
                n += 1
    assert n == 48


# ======================================================================================== research's T9 stage-2 cells
# Appended to tests/test_0045_t9_write.py (its helpers: _mem, _script, _one, _edges, _plant, _episode, _ok, _refuses, _q).
# Each kills a research mutant that survived the T9 cells at d8f16bf (READ-T9-stage2.md): S1 RT9-3, S2 RT9-5/RT9-6,
# S3 RT9-9/RT9-10, S4 RT9-4.
def test_inv_g2_an_unsupported_triple_from_a_user_effective_event_is_not_attested(tmp_path):
    """0045 §3: ATTEST-3 covers first-person USER statements in its trigger table; UNSUPPORTED is not attested (the
    safe direction). Through real ingest, declared-direct: another subject, and a relation outside the table, are
    stored `not_attested` with the predicate's version. Mutant: UNSUPPORTED read as attested."""
    cases = [("sister", "works_as", "nurse", "My sister works as a nurse."),
             ("user", "favourite_colour", "green", "My favourite colour is green.")]
    mem = _mem(tmp_path, [_script(r, o, subject=s) for s, r, o, _t in cases])
    for n, (_s, _r, _o, text) in enumerate(cases):
        _ok(mem.remember, f"n{n}", text, date="2026-10-01", context=DIRECT)
        e = _one(mem, f"n{n}")
        assert attest_v3.attests(e.subject, e.relation, e.object, text) == "UNSUPPORTED", (e.subject, e.relation)
        assert (e.att, e.attv) == ("not_attested", PREDICATE_VERSION), text


def test_inv_g13_the_same_id_guard_refuses_null_to_value_and_value_to_null(tmp_path):
    """INV-G13, both directions (367f761: "refuses a same-id change of any of the three, both directions"): a legacy
    row (NULL) is never labelled by a same-id replace, and a labelled row's three fields are never erased by one;
    nothing is written. Mutants: NULL -> value admitted; value -> NULL admitted."""
    mem = _mem(tmp_path, [])
    _episode(mem, "ep-1")
    legacy = _plant(mem, "legacy", att=None, src=None)
    lab = _plant(mem, "lab", att="not_attested", src="ep-1", obj="chef")
    _refuses(mem.store.add_edge, legacy.model_copy(update={"att": "attested", "attv": PREDICATE_VERSION}),
             match="cannot change att")
    for field in ("att", "src", "attv"):
        _refuses(mem.store.add_edge, lab.model_copy(update={field: None}), match=f"cannot change {field}")
    rows = {i: json.loads(j) for i, j in _q(mem, "SELECT id, json FROM edges")}
    assert not {"att", "src", "attv"} & set(rows["legacy"])
    assert (rows["lab"]["att"], rows["lab"]["src"], rows["lab"]["attv"]) == ("not_attested", "ep-1", PREDICATE_VERSION)


def test_q6_a_trusted_restore_keeps_the_files_axis_as_recorded_and_stamps_nothing(tmp_path):
    """Q6 in RESTORE mode, as T11b opens the axis's era (0045 §4e "trusted restore: as recorded"; this cell's T9 form,
    367f761, pinned the strip): a trusted restore into a store without the edge writes the file's `att`, `src` and
    `attv` exactly — the store's own export, and a file that says `attested`, which a restore trusts as the operator's
    own history (0005), its `src` naming no episode admitted (research's T11b M4). Nothing is stamped. Mutants: the
    strip in restore; the default stamp in restore too."""
    src_mem = _mem(tmp_path, [_script("works_as", "dentist")], name="src.db")
    _ok(src_mem.remember, U, "I work as a dentist.", date="2026-10-01", context=DIRECT)
    path = tmp_path / "own.jsonl"
    src_mem.export_memory(U, path)
    head, *rest = path.read_text().splitlines()
    recs = [json.loads(l) for l in rest]
    for r in recs:
        if r.get("record") == "edge":
            r.update(att="attested", attv=PREDICATE_VERSION, src="ep-forged")
    forged = tmp_path / "forged.jsonl"
    forged.write_text(head + "\n" + "\n".join(json.dumps(r) for r in recs) + "\n")
    for f in (path, forged):
        dst = _mem(tmp_path, [], name=f"dst-{f.stem}.db")
        _ok(dst.import_memory, f, restore=True)
        es = _edges(dst)
        want = {e.id: (e.att, e.src, e.attv) for e in _edges(src_mem)} if f is path else None
        assert es and all((e.att, e.src, e.attv) == (want[e.id] if want else ("attested", "ep-forged", PREDICATE_VERSION))
                          for e in es), (f.stem, [(e.att, e.attv) for e in es])


def test_f4_the_attv_hex_part_is_exactly_eight():
    """0045 §2c's grammar, `ATTEST-<n>@<8 hex>`: ten hex digits refuse. Mutant: the hex part unbounded."""
    assert valid_attv(PREDICATE_VERSION)
    assert not valid_attv("ATTEST-3@b1329a81ab")
