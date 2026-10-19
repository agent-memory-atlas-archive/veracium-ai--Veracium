"""specs/0047 (v1.16, ACCEPTED, design) — T10a, the subject's reply: the store, the verb, and what it changes now.

One cell per §6 row T10a makes product-true (INV-R1, R2, R5, R7, R8, R9, R10, R13, R14, R15 with 0008 INV-Q1 for all
three verbs, R17, R19, R22, R24), the 0041 amendment's INV-RR1, RR2, RR4 and RR5, IO-II-3's reply carriers, and
research's T10a stage-1 items (Q7's union, Q9's stated reading, Q12's exact skip set, F1–F6). The read half (withholding,
the unit, the wiki, as-of) is T10b's; the portable half is T11b's. A differential replays short sequences against
reference model II. Every product mutant is in the scratch campaign
`.claude/skills/pre-seal/impl-review/0044/t10a_mutant_defs.py` (classified by specs/evidence/mutation_kinds.py).
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import random
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import pytest

from veracium import EvidenceAuthor, EvidenceContext, Memory, MemoryConfig, doctor
from veracium import portability as port
from veracium import redaction as R
from veracium.audit import AuditLog
from veracium.graph import apply_supersession
from veracium.schema import (DEFAULT_RELATIONS, ConfirmationActor, ConfirmationCallPath, Disclosure, Edge,
                             EvidenceAuthor as EA, Provenance, Relation, ReplyActor, Volatility, reply_request_digest)
from veracium.store.base import REPLY_REFUSAL_REASONS, ReplyRefused, RequestRedacted
from veracium.store.sqlite import SqliteStore

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "veracium"
U, U2 = "u1", "u2"
DIRECT = EvidenceContext.direct()


def _load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


class _Fake:
    """A scripted distiller; every other role answers nothing."""

    def __init__(self, scripts):
        self._s = list(scripts)

    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        if role != "distill":
            return ""
        return json.dumps(self._s.pop(0) if self._s else {"triples": [], "episode": "x"})


def _script(relation, obj):
    return {"triples": [{"subject": "user", "relation": relation, "object": obj, "volatility": "durable"}],
            "episode": "the user said something"}


def _mem(tmp_path, scripts=(), name="m.db", **cfg):
    return Memory(llm=_Fake(scripts), config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                                                          **cfg))


def _fact(mem, relation="lives_in", obj="Paris", user=U):
    """Remember one fact from a declared-direct USER event, through the real ingest path; its edge id."""
    mem.llm._s.append(_script(relation, obj))
    before = {e.id for e in mem.store.edges(user, active_only=False, include_quarantined=True)}
    _ok(mem.remember, user, f"I {relation} {obj}", author=EvidenceAuthor.USER, context=DIRECT)
    new = [e for e in mem.store.edges(user, active_only=False, include_quarantined=True) if e.id not in before]
    assert len(new) == 1, [(e.id, e.object) for e in new]
    return new[0].id


def _ok(fn, *a, **k):
    """A call the cell expects to SUCCEED: any raise is the property failing, read as an assertion (so a mutant's kill
    is classified, never an escaping exception)."""
    try:
        return fn(*a, **k)
    except Exception as exc:                                       # noqa: BLE001 — the cell's subject
        raise AssertionError(f"expected success; raised {type(exc).__name__}: {exc}") from exc


def _refuses(exc_type, fn, *a, **k):
    """A call the cell expects to raise EXACTLY `exc_type` (or a subclass): anything else is an assertion."""
    try:
        fn(*a, **k)
    except exc_type as exc:
        return exc
    except Exception as exc:                                       # noqa: BLE001 — the cell's subject
        raise AssertionError(f"expected {exc_type.__name__}; raised {type(exc).__name__}: {exc}") from exc
    raise AssertionError(f"expected {exc_type.__name__}; nothing was raised")


def _reason(fn, *a, **k):
    return _refuses(ReplyRefused, fn, *a, **k).reason


def _q(mem, sql, args=()):
    return mem.store._conn.execute(sql, args).fetchall()


def _rows(mem, user=U):
    return _q(mem, "SELECT id, edge_id, kind, target, text, actor, request_digest, act_seq FROM replies "
                   "WHERE user_id=? ORDER BY act_seq", (user,))


def _registry(mem, user=U):
    return _q(mem, "SELECT correlation_id, verb, target_edge_id FROM request_registry WHERE user_id=? "
                   "ORDER BY correlation_id", (user,))


def _edge_bytes(mem, eid):
    return (_q(mem, "SELECT json, subject, relation, object, active, quarantined FROM edges WHERE id=?", (eid,)),
            _q(mem, "SELECT seq, kind, reason, state FROM edge_event WHERE edge_id=? ORDER BY seq", (eid,)))


def _open(mem, eid, user=U):
    return [r.id for r in mem.store.active_challenges(user, eid)]


# ============================================================================================ INV-R1, INV-R2
def test_r1_a_reply_of_every_kind_mutates_nothing_about_its_edge(tmp_path):
    """INV-R1: a reply — every kind, a resolve included — leaves the edge's json, its columns and its journal
    byte-identical, writes no episode (§1c: a reply never feeds ingest) and no confirmation. Mutant: a reply that sets
    `invalidated_at`."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    before, eps = _edge_bytes(mem, e), _q(mem, "SELECT id, json FROM episodes ORDER BY id")
    c = _ok(mem.reply, U, e, kind="challenge", text="I never lived there")
    _ok(mem.reply, U, e, kind="context", text="only for one summer")
    _ok(mem.reply, U, e, kind="withdrawn-consent", text="please stop using this")
    _ok(mem.reply, U, e, kind="resolve", target=c["reply_id"])
    assert _edge_bytes(mem, e) == before
    assert _q(mem, "SELECT id, json FROM episodes ORDER BY id") == eps
    assert _q(mem, "SELECT COUNT(*) FROM confirmations") == [(0,)]
    assert [r[2] for r in _rows(mem)] == ["challenge", "context", "withdrawn-consent", "resolve"]


_WRITE = re.compile(r"\b(INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|DELETE\s+FROM)\s+replies\b", re.I)


def _sql_writers_of_replies():
    """Every SQL string literal in src/ that WRITES `replies`, with its enclosing function: (module, qualname, verb)."""
    out = []
    for f in sorted(SRC.rglob("*.py")):
        tree = ast.parse(f.read_text())
        stack = []

        def visit(node):
            named = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            if named:
                stack.append(node.name)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for m in _WRITE.finditer(node.value):
                    out.append((str(f.relative_to(SRC)), ".".join(stack), m.group(1).split()[0].upper()))
            for ch in ast.iter_child_nodes(node):
                visit(ch)
            if named:
                stack.pop()
        visit(tree)
    return sorted(out)


def test_r2_replies_are_append_only_by_construction(tmp_path):
    """INV-R2: the SQL census over src/ — `replies` is INSERTed only by `add_reply`, UPDATEd only by the redaction's
    treatment (text and digest, §11.6.2), and DELETEd only by the erasure loop (`_ERASE_TABLES`); and a resolve is a
    NEW row: its challenge's row is byte-identical after it. Mutant: a resolve that UPDATEs its challenge in place."""
    assert _sql_writers_of_replies() == [
        ("store/sqlite.py", "SqliteStore._redact_in_txn", "UPDATE"),
        ("store/sqlite.py", "SqliteStore._redact_in_txn", "UPDATE"),
        ("store/sqlite.py", "SqliteStore.add_reply", "INSERT")]
    from veracium.store import sqlite as S
    assert "replies" in S._ERASE_TABLES
    mem = _mem(tmp_path)
    e = _fact(mem)
    c = _ok(mem.reply, U, e, kind="challenge", text="wrong")
    row = _q(mem, "SELECT * FROM replies WHERE id=?", (c["reply_id"],))
    _ok(mem.reply, U, e, kind="resolve", target=c["reply_id"])
    assert _q(mem, "SELECT * FROM replies WHERE id=?", (c["reply_id"],)) == row


# ============================================================================================ INV-R5
def test_r5_doctor_reports_an_orphan_reply_and_a_resolve_naming_no_challenge(tmp_path):
    """INV-R5: a reply whose edge does not exist FOR ITS USER is an error row — a dangling id, and (research's F5) an
    id that exists only for another user, as the confirmations row joins; a resolve naming no challenge of its own
    edge is a second row (Q14). Control: a clean store with replies has neither. Mutant: silence the row."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    other = _fact(mem, "works_at", "Acme", user=U2)
    c = _ok(mem.reply, U, e, kind="challenge", text="wrong")
    _ok(mem.reply, U, e, kind="resolve", target=c["reply_id"])
    path = str(tmp_path / "m.db")
    clean = [f for f in doctor.diagnose(path).findings if f.check == "refs" and "repl" in f.message]
    assert clean == []
    ins = ("INSERT INTO replies(id, user_id, edge_id, kind, target, text, actor, correlation_id, request_digest, "
           "origin, written_at) VALUES(?,?,?,?,?,?,'user',?,'d','local','2026-10-19T00:00:00+00:00')")
    mem.store._conn.execute(ins, ("r-dangling", U, "e-nowhere", "context", None, "x", "k1"))
    mem.store._conn.execute(ins, ("r-cross", U, other, "context", None, "x", "k2"))
    mem.store._conn.execute(ins, ("r-badres", U, e, "resolve", "r-cross", None, "k3"))
    mem.store._conn.commit()
    found = {f.message.split(" ", 1)[1]: f.ids for f in doctor.diagnose(path).findings if f.check == "refs"
             and f.level == "error" and "repl" in f.message}
    assert found == {"reply(ies) naming an edge that does not exist (specs/0047 INV-R5)": ["r-cross", "r-dangling"],
                     "resolve reply(ies) naming no challenge of their own edge (specs/0047 §4b)": ["r-badres"]}, found


# ============================================================================================ the request's shape
@pytest.mark.parametrize("text", [R.MARKER, R.MARKER + " and more", "I said " + R.MARKER + " nothing"])
def test_r7_rr1_a_marker_carrying_reply_is_refused_and_writes_nothing(tmp_path, text):
    """INV-R7 / 0041 INV-RR1: an ordinary reply may not introduce the marker — whole, a prefix, embedded. Refused as
    `marker`, nothing written (no row, no registry row). Control: text QUOTING the fact's words is admitted. Mutant:
    accept it."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    assert _reason(mem.reply, U, e, kind="challenge", text=text, correlation_id="k1") == "marker"
    assert _rows(mem) == [] and _registry(mem) == []
    _ok(mem.reply, U, e, kind="challenge", text="I never lived in Paris")


@pytest.mark.parametrize("kind", ["disputed", "", "Challenge", "CHALLENGE", "challenge ", None, 1])
def test_r8_the_kind_is_closed_at_the_write_path(tmp_path, kind):
    """INV-R8: every kind outside {challenge, context, withdrawn-consent, resolve} is refused as `kind`, before
    anything is read or written. Mutant: widen the set."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    assert _reason(mem.reply, U, e, kind=kind, text="x") == "kind"
    assert _rows(mem) == [] and _registry(mem) == []


@pytest.mark.parametrize("actor", ["assistant", "system", "third_party", "extractor", "USER", None])
def test_the_actor_is_closed_to_the_subject_and_the_host(tmp_path, actor):
    """§2c's "who wrote it": a reply labelled anything but `user` or `host` is refused as `actor` (Q4: `ReplyActor`,
    its own closed type). Controls: both labels are admitted. Mutant: admit any label."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    assert _reason(mem.reply, U, e, kind="challenge", text="x", actor=actor) == "actor"
    for a in (ReplyActor.USER, "host"):
        _ok(mem.reply, U, e, kind="context", text=f"from {a}", actor=a)


@pytest.mark.parametrize("kind,text,target,why", [
    ("challenge", None, None, "empty"), ("challenge", "", None, "empty"), ("context", "   \n", None, "empty"),
    ("challenge", "x", "r-1", "target"), ("resolve", None, None, "target"), ("resolve", "", "r-1", "text"),
    ("resolve", "text too", "r-1", "text"), ("challenge", "I never said \ud800 that", None, "high surrogate"),
    ("context", "lone low \udc00", None, "low surrogate")])
def test_the_request_shape_is_closed_before_the_registry(tmp_path, kind, text, target, why):
    """§4b's closed request (a target iff `resolve`, non-empty text iff not) and research's F1 (text must encode as
    strict UTF-8: a lone surrogate would raise UnicodeEncodeError at the INSERT, a ValueError with no reason). Refused as
    `shape`, nothing written, and BEFORE the registry (Q5): a malformed request under a HELD id is a shape refusal, not
    a conflict. Mutants: drop the shape check; drop the encoding check."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    _ok(mem.reply, U, e, kind="challenge", text="held", correlation_id="k1")
    rows = _rows(mem)
    assert _reason(mem.reply, U, e, kind=kind, text=text, target=target, correlation_id="k1") == "shape", why
    assert _reason(mem.reply, U, e, kind=kind, text=text, target=target, correlation_id="k2") == "shape", why
    assert _rows(mem) == rows


def test_an_astral_character_is_valid_text(tmp_path):
    """F1's control: a valid astral character (a surrogate PAIR in UTF-16, one code point here) is admitted and stored
    unchanged."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    r = _ok(mem.reply, U, e, kind="context", text="moved \U0001F3E0 in May")
    assert [x.text for x in mem.store.replies_for(U, e)] == ["moved \U0001F3E0 in May"] and r["replayed"] is False


# ============================================================================================ INV-R9, Q7, INV-R19
def test_r9_an_absent_or_another_users_edge_is_refused_and_nothing_written(tmp_path):
    """INV-R9: an edge id that does not exist, and one that exists only for another user, refuse `unknown-edge` with
    no row and no registry row. Mutant: drop the check."""
    mem = _mem(tmp_path)
    other = _fact(mem, user=U2)
    for eid in ("e-nowhere", other):
        assert _reason(mem.reply, U, eid, kind="challenge", text="x", correlation_id="k1") == "unknown-edge"
    assert _rows(mem) == [] and _registry(mem) == [] and _rows(mem, U2) == []


def test_r9_q7_a_redacted_edge_is_refused_by_its_bytes_or_its_attestation(tmp_path):
    """§0 / INV-R9 with research's Q7 union: a new reply to a redacted edge is refused `redacted-edge` when the edge's
    own carriers show the marker OR an applied attestation names it.
      - a real `Memory.redact`: both halves hold, refused;
      - the BYTES alone (a record that arrived treated under a notice not yet applied — planted): refused;
      - an applied ATTESTATION alone (planted over untreated bytes): refused;
      - the control: a PENDING notice over untreated bytes is no redaction of what this store holds: admitted.
    Mutants: drop the bytes half; drop the attestation half."""
    mem = _mem(tmp_path)
    real, by_bytes, by_att, pending = (_fact(mem, "lives_in", "Paris"), _fact(mem, "works_at", "Acme"),
                                       _fact(mem, "likes", "tea"), _fact(mem, "has_pet", "Rex"))
    _ok(mem.redact, U, edge_id=real, reason="subject_request")
    d = json.loads(_q(mem, "SELECT json FROM edges WHERE id=?", (by_bytes,))[0][0])
    d["object"] = R.MARKER
    mem.store._conn.execute("UPDATE edges SET json=?, object=? WHERE id=?", (json.dumps(d), R.MARKER, by_bytes))
    ins = ("INSERT INTO redactions(id, user_id, target_kind, target_id, fields, marker_version, reason, "
           "store_version_before, store_version_after, recorded_at, state, pending_reason) "
           "VALUES(?,?,'edge',?,'[\"object\"]',1,'subject_request',1,1,'2026-10-19T00:00:00+00:00',?,?)")
    mem.store._conn.execute(ins, ("n-att", U, by_att, "applied", None))
    mem.store._conn.execute(ins, ("n-pend", U, pending, "pending", "held-target"))
    mem.store._conn.commit()
    for eid in (real, by_bytes, by_att):
        assert _reason(mem.reply, U, eid, kind="challenge", text="x") == "redacted-edge", eid
    _ok(mem.reply, U, pending, kind="challenge", text="that is not my dog")


def test_r19_a_reply_to_a_procedural_record_is_refused_for_every_kind(tmp_path):
    """INV-R19 (§4d's ruling): a reply cannot attach to a procedural record — refused `procedural-edge` for every
    kind, nothing written. Control: a declarative fact from the same user takes a reply. Mutant: accept it."""
    mem = _mem(tmp_path)
    pid = _ok(mem.record_procedure, U, "I review invoices every Friday", author=EvidenceAuthor.USER,
              context=EvidenceContext.direct(basis="stated"))
    for kind, text in (("challenge", "no"), ("context", "c"), ("withdrawn-consent", "w")):
        assert _reason(mem.reply, U, pid, kind=kind, text=text) == "procedural-edge"
    assert _reason(mem.reply, U, pid, kind="resolve", target="r-x") == "procedural-edge"
    assert _rows(mem) == [] and _registry(mem) == []
    _ok(mem.reply, U, _fact(mem), kind="challenge", text="no")


def test_q8_an_inactive_or_quarantined_edge_takes_a_reply(tmp_path):
    """Q8 (research agreed): §2c refuses only absent, redacted and procedural edges, and §4e keeps acts on retired
    records; §3 stores a reply on a quarantined edge. A disputed (retired) fact and a quarantined one each take a
    challenge."""
    mem = _mem(tmp_path)
    gone = _fact(mem)
    _ok(mem.dispute, U, gone)
    _ok(mem.reply, U, gone, kind="challenge", text="still wrong")
    q = Edge(id="e-q", user_id=U, subject="user", relation="likes", object="jazz",
             provenance=Provenance(author_of_evidence=EA.USER, evidence_ref="ev", disclosure=Disclosure.QUARANTINED))
    mem.store.add_edge(q)
    _ok(mem.reply, U, "e-q", kind="context", text="only some")


# ============================================================================================ INV-R13, R14
def test_r13_confirm_is_refused_under_an_open_challenge_and_admitted_after_its_resolve(tmp_path):
    """INV-R13: `confirm()` refuses an edge with an active challenge, writing nothing; with two challenges and one
    resolved it still refuses; after the second resolve it confirms. Mutants: drop the guard; a guard that ignores
    resolves; a guard that reads only the latest challenge."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    c1 = _ok(mem.reply, U, e, kind="challenge", text="first")["reply_id"]
    c2 = _ok(mem.reply, U, e, kind="challenge", text="second")["reply_id"]
    before = _edge_bytes(mem, e)
    msg = str(_refuses(ValueError, mem.confirm, U, e))
    assert "active challenge" in msg, msg
    assert _edge_bytes(mem, e) == before and _q(mem, "SELECT COUNT(*) FROM confirmations") == [(0,)]
    _ok(mem.reply, U, e, kind="resolve", target=c2)
    assert "active challenge" in str(_refuses(ValueError, mem.confirm, U, e))
    _ok(mem.reply, U, e, kind="resolve", target=c1)
    assert _ok(mem.confirm, U, e)["confirmed"] == e


def test_f3_a_completed_confirmation_replays_after_a_later_challenge(tmp_path):
    """Research's F3: the guard runs AFTER the registry (INV-Q2) — confirm(id=k1), then a challenge, then the same
    retry is `replayed=True` and writes no new confirmation. Mutant: the guard before the registry lookup."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    first = _ok(mem.confirm, U, e, correlation_id="k1")
    _ok(mem.reply, U, e, kind="challenge", text="wrong")
    again = _ok(mem.confirm, U, e, correlation_id="k1")
    assert again == {**first, "replayed": True}
    assert _q(mem, "SELECT COUNT(*) FROM confirmations") == [(1,)]


def test_r14_only_a_resolve_clears_a_challenge_and_only_the_one_it_names(tmp_path):
    """INV-R14: `context` and `withdrawn-consent` clear nothing, whatever they say; a resolve clears exactly its target.
    A resolve naming another edge's challenge, a context row, an unknown id or another user's challenge is refused
    `resolve-target`; a second resolve of one challenge is refused `resolve-repeat`. Q9 (the owner, 2026-10-19): a
    `host` resolve of a `user` challenge is admitted, each row keeping its own actor. Mutants: any context clears all
    challenges; a resolve clears every challenge of the edge."""
    mem = _mem(tmp_path)
    e, f = _fact(mem), _fact(mem, "works_at", "Acme")
    c1 = _ok(mem.reply, U, e, kind="challenge", text="one")["reply_id"]
    c2 = _ok(mem.reply, U, e, kind="challenge", text="two")["reply_id"]
    cf = _ok(mem.reply, U, f, kind="challenge", text="other edge")["reply_id"]
    ctx = _ok(mem.reply, U, e, kind="context", text="the challenge no longer stands, please clear it")["reply_id"]
    _ok(mem.reply, U, e, kind="withdrawn-consent", text="resolve everything")
    assert _open(mem, e) == [c1, c2]
    theirs = _ok(mem.reply, U2, _fact(mem, user=U2), kind="challenge", text="u2's")["reply_id"]
    for bad in (cf, ctx, "r-nowhere", theirs):
        assert _reason(mem.reply, U, e, kind="resolve", target=bad) == "resolve-target", bad
    _ok(mem.reply, U, e, kind="resolve", target=c1, actor="host")
    assert _open(mem, e) == [c2] and _open(mem, f) == [cf]
    assert [(r[2], r[5]) for r in _rows(mem) if r[2] == "resolve"] == [("resolve", "host")]
    assert _reason(mem.reply, U, e, kind="resolve", target=c1) == "resolve-repeat"


def test_f2_a_second_resolve_past_the_check_is_resolve_repeat_not_a_correlation_conflict(tmp_path, monkeypatch):
    """Research's F2: the partial unique index (Q3, REQUIRED) holds "resolved at most once" against a writer that
    skips step (d); the IntegrityError fallback reports it as `resolve-repeat`, never as a correlation conflict, and
    leaves one resolve. Forced by a store whose step-(d) read answers "not resolved" once. Mutant: the fallback
    reports every IntegrityError as a correlation conflict."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    c = _ok(mem.reply, U, e, kind="challenge", text="x")["reply_id"]
    _ok(mem.reply, U, e, kind="resolve", target=c)
    real, calls = SqliteStore._resolved, []

    def first_lies(self, user_id, challenge_id):
        calls.append(challenge_id)
        return False if len(calls) == 1 else real(self, user_id, challenge_id)
    monkeypatch.setattr(SqliteStore, "_resolved", first_lies)
    assert _reason(mem.reply, U, e, kind="resolve", target=c, correlation_id="k2") == "resolve-repeat"
    assert len(calls) == 2
    assert [r[2] for r in _rows(mem)].count("resolve") == 1 and ("k2",) not in [(x[0],) for x in _registry(mem)]


# ============================================================================================ INV-R15 / Q1, R24
T7 = None


def _t7():
    global T7
    T7 = T7 or _load("t7_undo_helpers_0047", pathlib.Path(__file__).with_name("test_0044_t7_undo.py"))
    return T7


@pytest.mark.parametrize("first,second", [("reply", "confirm"), ("confirm", "reply"), ("reply", "undo"),
                                          ("undo", "reply"), ("confirm", "undo"), ("undo", "confirm")])
def test_r15_q1_one_id_space_across_confirm_reply_and_undo(tmp_path, first, second):
    """INV-R15 / 0008 INV-Q1 for all three verbs, in both orders: an id held by one verb is refused to the other,
    naming the holder, and writes nothing. On a real store the data migration restored (T7's fixture), so `undo` runs
    for real. Mutant: each verb checks only its own table."""
    t7 = _t7()
    p = t7._restored(tmp_path)
    mem = t7._mem(p)
    calls = {"reply": lambda: mem.reply(t7.U, t7.N, kind="challenge", text="no", correlation_id="x"),
             "confirm": lambda: mem.confirm(t7.U, t7.N, correlation_id="x"),
             "undo": lambda: mem.undo_restoration(t7.U, t7.P, correlation_id="x")}
    _ok(calls[first])
    before = (_q(mem, "SELECT COUNT(*) FROM replies"), _q(mem, "SELECT COUNT(*) FROM confirmations"),
              _q(mem, "SELECT verb FROM request_registry WHERE correlation_id='x'"))
    msg = str(_refuses(ValueError, calls[second]))
    assert f"held by a '{first}' request" in msg, msg
    assert (_q(mem, "SELECT COUNT(*) FROM replies"), _q(mem, "SELECT COUNT(*) FROM confirmations"),
            _q(mem, "SELECT verb FROM request_registry WHERE correlation_id='x'")) == before


def test_r15_the_same_reply_request_replays_and_a_different_one_conflicts(tmp_path):
    """INV-R15/R24: the same request under one id replays the recorded reply (same id, same time, `replayed=True`,
    one row); the id with a different text, kind or edge is an integrity conflict; a different actor label is the
    SAME request (§4b's closed identity leaves the actor out, Q6). Mutant: same id + different request returns the
    first result."""
    mem = _mem(tmp_path)
    e, f = _fact(mem), _fact(mem, "works_at", "Acme")
    a = _ok(mem.reply, U, e, kind="challenge", text="wrong", correlation_id="k1")
    assert _ok(mem.reply, U, e, kind="challenge", text="wrong", correlation_id="k1") == {**a, "replayed": True}
    assert _ok(mem.reply, U, e, kind="challenge", text="wrong", actor="host", correlation_id="k1")["replayed"] is True
    for other in ({"kind": "challenge", "text": "WRONG"}, {"kind": "context", "text": "wrong"}):
        assert "DIFFERENT reply request" in str(_refuses(ValueError, mem.reply, U, e, correlation_id="k1", **other))
    assert "DIFFERENT reply request" in str(_refuses(ValueError, mem.reply, U, f, kind="challenge", text="wrong",
                                                     correlation_id="k1"))
    assert len(_rows(mem)) == 1


@pytest.mark.parametrize("order", ["reply-first", "confirm-first", "reply-reply"])
def test_r15_two_connections_racing_on_one_id_admit_exactly_one(tmp_path, order):
    """INV-R15 under concurrency (T7's race shape): two SqliteStores on one file; the first is paused inside its write
    transaction at the registry lookup, the second waits for the lock; exactly one commits, and the other replays
    (same reply request) or is refused naming the holder."""
    t7 = _t7()
    p = t7._restored(tmp_path)
    reply = lambda s: Memory(llm=lambda *a, **k: "", store=s).reply(t7.U, t7.N, kind="challenge", text="no",
                                                                     correlation_id="x")
    confirm = lambda s: Memory(llm=lambda *a, **k: "", store=s).confirm(t7.U, t7.N, correlation_id="x")
    first, second = {"reply-first": (reply, confirm), "confirm-first": (confirm, reply),
                     "reply-reply": (reply, reply)}[order]
    a, b, waited = t7._race(p, first, second)
    assert waited and not isinstance(a, Exception), a
    if order == "reply-reply":
        assert b == {**a, "replayed": True}
    else:
        winner = "reply" if order == "reply-first" else "confirm"
        assert isinstance(b, ValueError) and f"held by a '{winner}' request" in str(b), b
    s = SqliteStore(p)
    try:
        assert s._conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0] == (0 if order == "confirm-first" else 1)
    finally:
        s.close()


def test_r24_a_reply_retry_replays_its_own_result_whatever_the_edge_became(tmp_path):
    """INV-R24: after the edge is retired (disputed) a reply retry under its id replays its own reply without reading
    the edge; a confirm under the reply's id never returns the reply's result (it is refused naming `reply`). Mutants:
    replay by edge state; return a confirm result under a reply id."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    a = _ok(mem.reply, U, e, kind="context", text="only in 2020", correlation_id="k1")
    _ok(mem.dispute, U, e)
    assert _ok(mem.reply, U, e, kind="context", text="only in 2020", correlation_id="k1") == {**a, "replayed": True}
    assert "held by a 'reply' request" in str(_refuses(ValueError, mem.confirm, U, e, correlation_id="k1"))


def test_q8_the_digest_is_a_canonical_array_with_a_golden_vector():
    """Research's F4 with INV-Q8's probes, at the digest function itself: the bytes are pinned by a golden vector (one
    request with non-ASCII text and a NULL target), and a separator inside a field, a NUL, None against "None" and ""
    against NULL each give distinct digests. Mutant: a separator join."""
    assert reply_request_digest("u1", "e-1", "challenge", None, "Ich wohne nicht in München") == hashlib.sha256(
        '["reply","u1","e-1","challenge",null,"Ich wohne nicht in München"]'.encode("utf-8")).hexdigest()
    assert reply_request_digest("u1", "e-1", "challenge", None, "Ich wohne nicht in München") == \
        "672adc149befb40f4f14e9c3a3c7c4f12c088cc4fd74537e33b3b3c62549cb1f"
    pairs = [(("u1", "e-1", "context", None, "a\x1fb"), ("u1", "e-1\x1fcontext", "a", None, "b")),
             (("u1", "e-1", "context", None, "a\x00"), ("u1", "e-1", "context", None, "a")),
             (("u1", "e-1", "resolve", None, None), ("u1", "e-1", "resolve", "None", None)),
             (("u1", "e-1", "context", None, ""), ("u1", "e-1", "context", None, None))]
    for x, y in pairs:
        assert reply_request_digest(*x) != reply_request_digest(*y), (x, y)


# ============================================================================================ INV-R17, Q12
_NOW = datetime.now(timezone.utc)


def _E(eid, obj, rel="has_pet", days=1):
    t = _NOW - timedelta(days=days)
    return Edge(id=eid, user_id=U, subject="user", relation=rel, object=obj, volatility=Volatility.DURABLE, valid_from=t,
                provenance=Provenance(author_of_evidence=EA.USER, evidence_ref=f"ev-{eid}",
                                      disclosure=Disclosure.MENTIONABLE, confidence=0.7, observed_at=t))


def _state(s):
    return sorted((e.id, e.object, e.active, e.invalidation_reason) for e in s.edges(U, active_only=False))


def _confirm_raw(s, eid, cid):
    return s.confirm_edge(U, eid, actor=ConfirmationActor.USER, call_path=ConfirmationCallPath.HOST_API,
                          correlation_id=cid, request_digest=f"d-{cid}", confirmed_at=_NOW - timedelta(days=2))


def _rels(functional):
    rels = dict(DEFAULT_RELATIONS)
    rels["has_pet"] = Relation(name="has_pet", functional=functional)
    return rels


@pytest.mark.parametrize("functional", [False, True])
def test_r17_a_confirmed_prior_is_not_absorbed_by_a_more_specific_restatement(functional):
    """INV-R17 / §4e — research's P1, RED at 1150667 (a confirmed "Miso" was absorbed by "cat Miso", its confirmation
    stranded on a retired record): the confirmed prior stays ACTIVE with its confirmation, the restatement is its own
    active record carrying none, and no `absorbed_duplicate` is written. Under a FUNCTIONAL relation too (Q12 (a)): no
    `superseded`, no refusal row. Uses only `confirm_edge`, so it runs at the pin. Mutant: absorb an acted prior."""
    s = SqliteStore(":memory:")
    _ok(apply_supersession, s, _E("e-miso", "Miso", days=3), _rels(functional))
    _ok(_confirm_raw, s, "e-miso", "c1")
    _ok(apply_supersession, s, _E("e-cat", "cat Miso", days=1), _rels(functional))
    assert _state(s) == [("e-cat", "cat Miso", True, None), ("e-miso", "Miso", True, None)]
    assert [c.id for c in s.confirmations_for(U, "e-miso")] and s.confirmations_for(U, "e-cat") == []
    assert s._conn.execute("SELECT COUNT(*) FROM supersession_refusals").fetchone()[0] == 0
    assert s._conn.execute("SELECT COUNT(*) FROM contribution_ledger WHERE site='absorption'").fetchone()[0] == 0


@pytest.mark.parametrize("kind", ["challenge", "context", "withdrawn-consent"])
def test_r17_a_replied_prior_is_not_absorbed_and_an_unacted_one_still_is(kind):
    """INV-R17 for the reply act, every kind: the replied prior stays active with its reply. Control: an unacted prior
    of the same shape IS absorbed (`absorbed_duplicate`), so the rule is the act, not the shape. Mutant: count only
    confirmations as acts."""
    s = SqliteStore(":memory:")
    _ok(apply_supersession, s, _E("e-miso", "Miso", days=3), _rels(False))
    _ok(s.add_reply, U, "e-miso", kind=kind, text="about Miso", target=None, actor=ReplyActor.USER,
        correlation_id="k1")
    _ok(apply_supersession, s, _E("e-cat", "cat Miso", days=1), _rels(False))
    assert _state(s) == [("e-cat", "cat Miso", True, None), ("e-miso", "Miso", True, None)]
    assert [r.id for r in s.replies_for(U, "e-miso")] and s.replies_for(U, "e-cat") == []
    t = SqliteStore(":memory:")
    _ok(apply_supersession, t, _E("e-miso", "Miso", days=3), _rels(False))
    _ok(apply_supersession, t, _E("e-cat", "cat Miso", days=1), _rels(False))
    assert _state(t) == [("e-cat", "cat Miso", True, None), ("e-miso", "Miso", False, "absorbed_duplicate")]


def test_r17_q12b_a_new_value_still_supersedes_an_acted_prior_and_its_acts_stay(tmp_path):
    """Q12 (b), research's exact skip set: under a functional relation a confirmed "Miso" is SUPERSEDED by a genuinely
    new value "Rex" and keeps its confirmation; "Rex" carries none (§4e row 4: the acts stay on the prior). A
    reinforcement (the same value again) writes a new id and moves no act. Mutant: skip every acted prior in the
    functional branch."""
    s = SqliteStore(":memory:")
    _ok(apply_supersession, s, _E("e-miso", "Miso", days=3), _rels(True))
    _ok(_confirm_raw, s, "e-miso", "c1")
    _ok(apply_supersession, s, _E("e-rex", "Rex", days=1), _rels(True))
    assert _state(s) == [("e-miso", "Miso", False, "superseded"), ("e-rex", "Rex", True, None)]
    assert len(s.confirmations_for(U, "e-miso")) == 1 and s.confirmations_for(U, "e-rex") == []
    t = SqliteStore(":memory:")
    _ok(apply_supersession, t, _E("e-miso", "Miso", days=3), _rels(False))
    _ok(_confirm_raw, t, "e-miso", "c1")
    _ok(apply_supersession, t, _E("e-miso2", "Miso", days=1), _rels(False))
    assert _state(t) == [("e-miso", "Miso", True, None), ("e-miso2", "Miso", True, None)]
    assert len(t.confirmations_for(U, "e-miso")) == 1 and t.confirmations_for(U, "e-miso2") == []


def test_r17_q13_an_act_written_between_plan_and_commit_makes_the_plan_stale():
    """Q13 (research agreed): the CAS fingerprint does not see acts, so the store's verifier reads them in the plan's
    own transaction. A reply written AFTER the plan absorbed its prior makes the plan stale; the re-plan declines to
    absorb, and the prior keeps its reply. Mutant: drop the verifier check (the stale plan commits the absorption)."""
    s = SqliteStore(":memory:")
    _ok(apply_supersession, s, _E("e-miso", "Miso", days=3), _rels(False))
    real, fired = SqliteStore.apply_supersession_plan, []

    def late_act(self, *a, **k):
        if not fired:
            fired.append(1)
            self.add_reply(U, "e-miso", kind="challenge", text="not my cat", target=None, actor=ReplyActor.USER,
                           correlation_id="late")
        return real(self, *a, **k)
    s.apply_supersession_plan = late_act.__get__(s)
    _ok(apply_supersession, s, _E("e-cat", "cat Miso", days=1), _rels(False))
    assert fired
    assert _state(s) == [("e-cat", "cat Miso", True, None), ("e-miso", "Miso", True, None)]
    assert [r.id for r in s.replies_for(U, "e-miso")]


# ============================================================================================ INV-R22
def test_r22_erasure_removes_the_users_replies_and_registry_rows_and_never_reuses_a_position(tmp_path):
    """INV-R22 / 0008 §6g: `forget_user` removes the user's replies and registry rows, counts the replies (Q15), and
    leaves another user's; a retry under the old id after erasure is a NEW request; the store-wide counter is not
    reset, so the next position is higher than any before. Mutants: keep replies; keep registry rows."""
    mem = _mem(tmp_path)
    e, o = _fact(mem), _fact(mem, user=U2)
    _ok(mem.reply, U, e, kind="challenge", text="x", correlation_id="k1")
    _ok(mem.reply, U2, o, kind="challenge", text="y", correlation_id="k1")
    top = _q(mem, "SELECT MAX(act_seq) FROM replies")[0][0]
    assert isinstance(top, int), top
    assert _ok(mem.store.forget_user, U)["replies"] == 1
    assert _rows(mem) == [] and _registry(mem) == [] and len(_rows(mem, U2)) == 1 and len(_registry(mem, U2)) == 1
    e2 = _fact(mem)
    again = _ok(mem.reply, U, e2, kind="challenge", text="x", correlation_id="k1")
    assert again["replayed"] is False
    assert _q(mem, "SELECT act_seq FROM replies WHERE user_id=?", (U,))[0][0] > top


# ============================================================================================ 0041 INV-RR2, RR4, RR5
def test_rr4_the_reply_carriers_are_edge_carrier_paths_by_derivation():
    """INV-RR4: `replies.text` and `replies.request_digest` are in `carrier_paths("edge")`, derived from the treatment
    map — never listed a second time; both REPLACE."""
    assert {"replies.text", "replies.request_digest"} <= set(R.carrier_paths("edge"))
    assert ("replies.text", R.REPLACE) in R.SIDE_TABLE_TREATMENTS["edge"]
    assert ("replies.request_digest", R.REPLACE) in R.SIDE_TABLE_TREATMENTS["edge"]
    assert not {"replies.text", "replies.request_digest"} & set(R.carrier_paths("episode"))


def test_rr2_redacting_an_edge_replaces_every_replys_text_and_keeps_the_rows(tmp_path):
    """INV-RR2: after `Memory.redact` every reply's text is the marker and a resolve's NULL stays NULL; ids, kinds,
    targets, actors and positions are unchanged; the attestation names `replies.text` and `replies.request_digest`.
    Control: redacting an edge with no reply names neither. Mutants: delete the rows; keep the text; omit the field
    from the attestation."""
    mem = _mem(tmp_path)
    e, bare = _fact(mem), _fact(mem, "works_at", "Acme")
    c = _ok(mem.reply, U, e, kind="challenge", text="I never lived in Paris")["reply_id"]
    _ok(mem.reply, U, e, kind="context", text="Paris was a visit", actor="host")
    _ok(mem.reply, U, e, kind="resolve", target=c)
    before = _rows(mem)
    rec = _ok(mem.redact, U, edge_id=e, reason="subject_request")
    after = _rows(mem)
    assert [(r[0], r[1], r[2], r[3], r[5], r[7]) for r in after] == [(r[0], r[1], r[2], r[3], r[5], r[7])
                                                                     for r in before]
    assert [r[4] for r in after] == [R.MARKER, R.MARKER, None]
    assert {"replies.text", "replies.request_digest"} <= set(rec.fields_cleared)
    fields = json.loads(_q(mem, "SELECT fields FROM redactions WHERE target_id=?", (e,))[0][0])
    assert {"replies.text", "replies.request_digest"} <= set(fields)
    rec2 = _ok(mem.redact, U, edge_id=bare, reason="subject_request")
    assert not {"replies.text", "replies.request_digest"} & set(rec2.fields_cleared)


def test_rr5_after_redaction_no_digest_survives_and_every_retry_is_terminal(tmp_path):
    """INV-RR5 / 0008 INV-Q7: an edge with a local confirmation and a text reply, redacted — no request digest on it
    survives in `confirmations`, `replies` or the registry; a retry under either id, with the SAME and with a
    DIFFERENT payload, is `RequestRedacted`, for `reply` and for `confirm`. Mutants: treat `replies.text` only (the
    verdict's countermodel); replay "same payload" against a treated digest."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    _ok(mem.confirm, U, e, correlation_id="k-conf")
    _ok(mem.reply, U, e, kind="context", text="I moved in 2019", correlation_id="k-rep")
    _ok(mem.redact, U, edge_id=e, reason="subject_request")
    assert {d for (d,) in _q(mem, "SELECT request_digest FROM confirmations")} == {R.MARKER}
    assert {d for (d,) in _q(mem, "SELECT request_digest FROM replies")} == {R.MARKER}
    assert {d for (d,) in _q(mem, "SELECT request_digest FROM request_registry WHERE target_edge_id=?", (e,))} == \
        {R.MARKER}
    for cid in ("k-conf", "k-rep"):
        for text in ("I moved in 2019", "something else"):
            _refuses(RequestRedacted, mem.reply, U, e, kind="context", text=text, correlation_id=cid)
        _refuses(RequestRedacted, mem.confirm, U, e, correlation_id=cid)


# ============================================================================================ IO-II-3
def test_io_ii_3_a_reply_under_a_pending_notice_is_admitted_and_its_confirmation_treats_it(tmp_path):
    """IO-II-3's reply carriers with 0041 INV-RR11: a PENDING notice (a default import over a held fact, T4's real
    path) is no redaction of what this store holds, so the subject's reply to the fact is admitted; the user's
    `confirm_notice` then applies this store's TOTAL treatment, and the reply's text and digest are treated although
    the notice's own fields predate replies. Mutant: confirm with the notice's fields only (a held reply survives)."""
    t4 = _load("t4_notice_helpers_0047", pathlib.Path(__file__).with_name("test_0041_notice_state.py"))
    _full, notices, _poisoned = t4._source(tmp_path, "src")
    v = t4._holder(tmp_path, "v.db")
    _ok(v.import_memory, notices)
    assert t4._rows(v) == [("e-x", "pending", "held-target")]
    assert not {"replies.text", "replies.request_digest"} & set(json.loads(
        v.store._conn.execute("SELECT fields FROM redactions").fetchone()[0]))
    _ok(v.reply, t4.U, "e-x", kind="challenge", text="Lisbon is still right")
    nid = v.store.pending_notices(t4.U)[0]["notice_id"]
    _ok(v.store.confirm_notice, t4.U, nid)
    assert v.store._conn.execute("SELECT text, request_digest FROM replies").fetchall() == [(R.MARKER, R.MARKER)]
    assert _reason(v.reply, t4.U, "e-x", kind="context", text="x") == "redacted-edge"


def test_io_ii_3_a_failed_redaction_leaves_the_replies_untouched(tmp_path, monkeypatch):
    """IO-II-3's rollback, for the reply carriers: a redaction that fails after the replies were treated rolls them back
    with everything else — text and digest unchanged, no attestation row."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    _ok(mem.reply, U, e, kind="challenge", text="wrong")
    before = _rows(mem)

    def boom(*a, **k):
        raise RuntimeError("injected after the side tables")
    monkeypatch.setattr(SqliteStore, "_journal_edge_write", boom)
    _refuses(RuntimeError, mem.redact, U, edge_id=e, reason="subject_request")
    monkeypatch.undo()
    assert _rows(mem) == before and _q(mem, "SELECT COUNT(*) FROM redactions") == [(0,)]


# ============================================================================================ INV-R10, F6
def test_r10_the_reply_verb_is_not_reachable_over_mcp():
    """INV-R10: no MCP tool reaches the reply verb. Read from mcp_server.py's AST, so it runs on the floor lane, which
    has no `mcp` extra (test_mcp's exact tool list covers the installed lane). Mutant: register it."""
    tree = ast.parse((SRC / "mcp_server.py").read_text())
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert not {"reply", "add_reply", "replies_for", "active_challenges"} & names


def test_f6_a_reply_writes_one_content_free_audit_line_and_none_on_replay(tmp_path):
    """Research's F6: a new reply appends ONE audit line naming its closed kind — never its text, target or the fact —
    and a replay appends none; telemetry's closed schema has no `reply` event, so nothing reaches it."""
    audit = AuditLog(tmp_path / "audit.jsonl")
    mem = Memory(llm=_Fake([]), audit=audit, config=MemoryConfig(db_path=str(tmp_path / "m.db"),
                                                                  wiki_recompile_after_writes=0))
    e = _fact(mem)
    secret = "SECRET-WORDS-ABOUT-PARIS"
    c = _ok(mem.reply, U, e, kind="challenge", text=secret, correlation_id="k1")
    _ok(mem.reply, U, e, kind="challenge", text=secret, correlation_id="k1")
    _ok(mem.reply, U, e, kind="resolve", target=c["reply_id"])
    lines = audit.entries(op="reply")
    assert [(x["user_id"], x["kind"], sorted(x)) for x in lines] == [
        (U, "challenge", ["kind", "op", "ts", "user_id"]), (U, "resolve", ["kind", "op", "ts", "user_id"])]
    raw = (tmp_path / "audit.jsonl").read_text()
    assert secret not in raw and c["reply_id"] not in raw and "Paris" not in raw
    if mem.telemetry is not None:
        assert "reply" not in json.dumps(mem.telemetry.snapshot())


def test_the_refusal_reasons_are_closed():
    """`ReplyRefused` carries a closed reason, as `UndoRefused` does: one outside the set refuses at construction."""
    assert set(REPLY_REFUSAL_REASONS) == {"kind", "actor", "shape", "marker", "unknown-edge", "redacted-edge",
                                          "procedural-edge", "resolve-target", "resolve-repeat"}
    with pytest.raises(ValueError, match="outside"):
        ReplyRefused("nope", U, "e", "x")


# ============================================================================================ the model II differential
_MODEL = None


def _model():
    global _MODEL
    _MODEL = _MODEL or _load("grounding_model_t10a", ROOT / "specs" / "evidence" / "0045" / "grounding_model.py")
    return _MODEL


def _verb(op):
    return "confirm" if op[0] == "confirm" else "reply"


def _run_model(M, s, edges, op, ids):
    """One op against model II: ('ok', result id) / ('refused',) / ('terminal',)."""
    kind, eid, arg, cid = op
    e = edges[eid]
    try:
        if kind == "confirm":
            r = M.confirm(s, e, M.Rules(), correlation_id=cid)
            return ("terminal",) if r == M.REQUEST_REDACTED else ("ok", r.id)
        if kind == "redact":
            M.redact_edge(s, e.id)
            return ("ok", None)
        text, target = (None, ids[arg][0] if arg is not None else "r-missing") if kind == "resolve" else (arg, None)
        r = M.add_reply(s, e, kind, text, target, correlation_id=cid)
        return ("terminal",) if r == M.REQUEST_REDACTED else ("ok", r.id)
    except M.Refused:
        return ("refused",)
    except Exception as exc:                                       # noqa: BLE001 — a crash is an outcome to compare
        return ("raised", type(exc).__name__)


def _run_product(mem, op, ids):
    kind, eid, arg, cid = op
    try:
        if kind == "confirm":
            r = mem.confirm(U, eid, correlation_id=cid)
            return ("ok", None)
        if kind == "redact":
            mem.redact(U, edge_id=eid, reason="subject_request")
            return ("ok", None)
        text, target = (None, ids[arg][1] if arg is not None else "r-missing") if kind == "resolve" else (arg, None)
        r = mem.reply(U, eid, kind=kind, text=text, target=target, correlation_id=cid)
        return ("ok", r["reply_id"])
    except RequestRedacted:
        # model II answers a redacted id with the terminal for its OWN verb and a conflict for another (0008 v8 raises
        # RequestRedacted for both, naming the holder): the same decision, read by the holder
        return ("terminal",) if _held_verb(mem, cid) == _verb(op) else ("refused",)
    except ValueError:
        return ("refused",)
    except Exception as exc:                                       # noqa: BLE001 — a crash is an outcome to compare
        return ("raised", type(exc).__name__)


def _held_verb(mem, cid):
    row = mem.store._conn.execute("SELECT verb FROM request_registry WHERE user_id=? AND correlation_id=?",
                                  (U, cid)).fetchone()
    return row[0] if row else None


@pytest.mark.parametrize("seed", range(40))
def test_differential_against_reference_model_ii(tmp_path, seed):
    """Short random sequences of challenge / context / resolve / confirm / redact over two facts, on a real store and
    on model II (`add_reply`, `confirm`, `redact_edge`): after every step the same outcome class (admitted, replayed,
    refused, terminal), the same open challenges per fact, and the same registry verbs per id. Model II's own scope is
    respected: its `confirm` has no assertability check, so the generator never confirms a redacted fact."""
    M = _model()
    rnd = random.Random(seed)
    mem = _mem(tmp_path)
    pa, pb = _fact(mem), _fact(mem, "works_at", "Acme")
    s = M.Store()
    ea = M.Edge(id="A", user=U, relation="lives_in", obj="Paris", att="attested")
    eb = M.Edge(id="B", user=U, relation="works_at", obj="Acme", att="attested")
    s.edges = {"A": ea, "B": eb}
    medges, map_e = {pa: ea, pb: eb}, {pa: "A", pb: "B"}
    ids: list = []                                   # (model reply id, product reply id), in creation order
    redacted: set = set()
    for _step in range(16):
        eid = rnd.choice([pa, pb])
        cid = rnd.choice([None, "k1", "k2", "k3"])
        roll = rnd.random()
        mine = [i for i, x in enumerate(ids) if x[2] == "challenge" and x[3] == eid]
        if roll < 0.3 or (0.72 <= roll < 0.95 and eid in redacted):
            op = ("challenge", eid, rnd.choice(["wrong", "no"]), cid)
        elif roll < 0.42:
            op = ("context", eid, "some context", cid)
        elif roll < 0.72:          # mostly a challenge of this fact; sometimes any reply, or one that does not exist
            pick = rnd.random()
            op = ("resolve", eid, rnd.choice(mine) if mine and pick < 0.7 else
                  rnd.randrange(len(ids)) if ids and pick < 0.9 else None, cid)
        elif roll < 0.95:
            op = ("confirm", eid, None, cid)
        else:
            op = ("redact", eid, None, None)
            redacted.add(eid)
        m = _run_model(M, s, medges, op, ids)
        p = _run_product(mem, op, ids)
        acts = op[0] not in ("confirm", "redact")
        m_cls = m[0] if not (acts and m[0] == "ok") else ("replayed" if m[1] in [i[0] for i in ids] else "new")
        p_cls = p[0] if not (acts and p[0] == "ok") else ("replayed" if p[1] in [i[1] for i in ids] else "new")
        assert m_cls == p_cls, (op, m, p)
        if m_cls == "new":
            ids.append((m[1], p[1], op[0], op[1]))
        back = {x[1]: x[0] for x in ids}
        for pe, me in medges.items():
            assert sorted(back[x] for x in _open(mem, pe)) == sorted(r.id for r in M.active_challenges(s, me)), op
        for c in ("k1", "k2", "k3"):
            held = s.registry.get((U, c))
            assert _held_verb(mem, c) == (held[0] if held else None), (op, c)


# ============================================================================================ research's T10a stage 2
# Ready cells (research, T10a stage 2 at ea42346), written to be appended to tests/test_0047_t10a_reply.py: they use
# its helpers. Each kills a research mutant that survived the 35 cells, and passes at ea42346.
def test_rs2_1_doctor_reports_each_broken_conjunct_of_a_resolve_alone(tmp_path):
    """Q14, one conjunct at a time: a resolve naming a CHALLENGE of another edge, and a resolve naming a CONTEXT reply of
    its own edge, are each reported. The R5 cell's `r-badres` names a context reply of another edge, which breaks both
    conjuncts at once, so dropping either one alone survived. Mutants: drop the same-edge conjunct; drop the kind
    conjunct."""
    mem = _mem(tmp_path)
    e, f = _fact(mem), _fact(mem, "works_at", "Acme")
    cf = _ok(mem.reply, U, f, kind="challenge", text="not Acme")["reply_id"]
    ctx = _ok(mem.reply, U, e, kind="context", text="a visit")["reply_id"]
    ins = ("INSERT INTO replies(id, user_id, edge_id, kind, target, text, actor, correlation_id, request_digest, "
           "origin, written_at) VALUES(?,?,?,?,?,?,'user',?,'d','local','2026-10-19T00:00:00+00:00')")
    mem.store._conn.execute(ins, ("r-res-other-edge", U, e, "resolve", cf, None, "k-a"))
    mem.store._conn.execute(ins, ("r-res-context", U, e, "resolve", ctx, None, "k-b"))
    mem.store._conn.commit()
    found = {f_.message.split(" ", 1)[1]: f_.ids for f_ in doctor.diagnose(str(tmp_path / "m.db")).findings
             if f_.check == "refs" and f_.level == "error" and "resolve" in f_.message}
    assert found == {"resolve reply(ies) naming no challenge of their own edge (specs/0047 §4b)":
                     ["r-res-context", "r-res-other-edge"]}, found


@pytest.mark.parametrize("cid", ["#act:s1|u1|r-1", "has space", "x" * 65, "", "k\x00"])
def test_rs2_2_memory_reply_refuses_a_correlation_id_outside_the_caller_grammar(tmp_path, cid):
    """The caller grammar (`[A-Za-z0-9._:-]{1,64}`) is what keeps a caller's id out of the internal `#act:` key space an
    imported act uses (0047 R2-02, T11b); the store takes any string, so `Memory.reply` is the only check. Refused with
    ValueError before anything is written. Mutant: Memory.reply skips the grammar."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    _refuses(ValueError, mem.reply, U, e, kind="challenge", text="wrong", correlation_id=cid)
    assert _rows(mem) == [] and _registry(mem) == []


def test_rs2_3_a_new_reply_bumps_the_store_version_once_and_a_replay_or_refusal_does_not(tmp_path):
    """A reply is a write the read half must see (T10b's wiki eviction keys on the store version): a new reply moves
    `store_version` by exactly one; its replay and a refusal move it by none. Mutant: drop the bump."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    v0 = mem.store.store_version(U)
    _ok(mem.reply, U, e, kind="challenge", text="wrong", correlation_id="k1")
    v1 = mem.store.store_version(U)
    _ok(mem.reply, U, e, kind="challenge", text="wrong", correlation_id="k1")
    _reason(mem.reply, U, e, kind="resolve", target="r-nowhere")
    assert (v1 - v0, mem.store.store_version(U) - v1) == (1, 0)


def test_rs2_4_every_local_reply_has_an_integer_position_strictly_increasing(tmp_path):
    """0008 §6f: a local act's position is allocated from the never-reset counter. The R22 cell compares positions with
    `>`, so a NULL position killed it by TypeError, not by assertion. Every kind gets an int, in write order. Mutant:
    allocate no position."""
    mem = _mem(tmp_path)
    e = _fact(mem)
    c = _ok(mem.reply, U, e, kind="challenge", text="wrong")["reply_id"]
    _ok(mem.reply, U, e, kind="context", text="a visit")
    _ok(mem.reply, U, e, kind="withdrawn-consent", text="stop")
    _ok(mem.reply, U, e, kind="resolve", target=c)
    seqs = [r[7] for r in _rows(mem)]
    assert len(seqs) == 4 and all(isinstance(s, int) for s in seqs), seqs
    assert seqs == sorted(set(seqs)), seqs
