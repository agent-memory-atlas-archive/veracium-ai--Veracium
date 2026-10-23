"""R-II round 3, RII-R3-01: an episode's owner never changes through `add_episode`, and the stored state the write
consults is keyed by the episode's ID, never by the incoming `user_id`.

The finding: `add_episode` replaced a same-ID row under another `user_id`, and its eviction and version bump addressed
only the newcomer, so the former owner's cached wiki still asserted an input it no longer held. Two siblings of the same
key (dev's, then research's stage-1 B1): the INV-11 attestation and the X21 reservation were read under the INCOMING
owner, so another user could repopulate a redacted episode and take an id an in-flight consolidation reserves. The
closure is the Store protocol's add_episode obligation (store/base.py), the 0008 §6d guard shape the edge writer has.

1. THE REVIEWER'S MATRIX: content unchanged/changed × cached/compiled × the replacement before recall / before the
   cached body's challenge snapshot / after it — now with the refusal REQUIRED (the reviewer's test accepted either a
   refusal or a withdrawn claim; the closure chose refusal), and ownership unchanged.
2. ATOMIC: a refused owner change writes nothing — the stored row, both users' versions and the cached wiki row.
3. THE CONTROL: an ordinary same-owner replacement is still allowed, and still evicts when it moves the view.
4. X21 BY ID: a deleted-but-reserved id is refused to every owner until the op finalizes.
5. INV-11 BY ID (N1, RULED 2026-10-23: "the redaction holds the ID"): a redacted-then-deleted id is refused to every
   owner; the READERS stay per user, so another user's own records are untouched by it.
6. CONFORMANCE: the protocol states the obligation the backend enforces.
"""
import inspect
import sys

import pytest

from veracium import Memory, MemoryConfig
from veracium.schema import ASSERTION_VIEW_KEEPS, ConsolidationOutputDraft, ConsolidationState as CS
from veracium.schema import Episode, EvidenceAuthor, Provenance
from veracium.store.base import Store
from veracium.store.sqlite import SqliteStore

A, B = "r3-owner-a", "r3-owner-b"
LINE = "User lives in Lisbon."


def _provider(prompt, *, role="compile", **kw):
    return LINE if role == "compile" and "Lisbon" in prompt else "No current location."


def _ep(eid="r3-ep", uid=A, summary="The user lives in Lisbon."):
    return Episode(id=eid, user_id=uid, date="2026-01-02", summary=summary,
                   provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r3-event"))


def _cfg(tmp_path):
    return MemoryConfig(db_path=str(tmp_path / "m.db"), require_source_id=False, scope_groups={})


def _row(s, eid):
    return s._conn.execute("SELECT user_id, json FROM episodes WHERE id=?", (eid,)).fetchone()


# ---- 1. the reviewer's matrix, with the refusal required -------------------------------------------------------

@pytest.mark.parametrize("change_content", [False, True], ids=["same-view", "different-view"])
@pytest.mark.parametrize("cached", [True, False], ids=["cached", "compiled"])
@pytest.mark.parametrize("timing", ["before_recall", "before_snapshot", "after_snapshot"])
def test_an_owner_change_is_refused_and_the_former_owner_asserts_nothing_it_lost(tmp_path, monkeypatch, timing,
                                                                                cached, change_content):
    cfg = _cfg(tmp_path)
    assert cfg.wiki_recompile_after_writes == 8
    reader, writer = Memory(llm=_provider, config=cfg), Memory(llm=_provider, config=cfg)
    try:
        original = _ep()
        reader.store.add_episode(original)
        if cached:
            assert LINE in reader.recall(A, "Lisbon", semantic=False).grounded
        refused = []

        def replace():
            moved = Episode.model_validate({**original.model_dump(), "user_id": B,
                                            "summary": "The user lives in Porto." if change_content
                                            else original.summary})
            with pytest.raises(ValueError, match="ownership is not transferable"):
                writer.store.add_episode(moved)
            refused.append(True)
            assert [e.id for e in writer.store.episodes(A)] == [original.id]
            assert writer.store.episodes(B) == []

        if timing == "before_recall":
            replace()
        real = reader.store.challenge_snapshot

        def snapshot(uid):
            bind = sys._getframe(1).f_code.co_name == "bound_wiki"
            if bind and timing == "before_snapshot" and not refused:
                replace()
            snap = real(uid)
            if bind and timing == "after_snapshot" and not refused:
                replace()
            return snap
        monkeypatch.setattr(reader.store, "challenge_snapshot", snapshot)
        result = reader.recall(A, "Lisbon", semantic=False)
        if timing == "before_recall" or cached:
            assert refused, "the replacement never ran: the cell measured nothing"
        # A still holds the episode (the write was refused), so A's claim is current, not stale
        assert LINE in result.grounded
        assert [e.id for e in reader.store.episodes(A)] == [original.id]
    finally:
        reader.close()
        writer.close()


# ---- 2. atomic: nothing written ----------------------------------------------------------------------------------

@pytest.mark.parametrize("change_content", [False, True], ids=["same-view", "different-view"])
def test_a_refused_owner_change_writes_nothing(tmp_path, change_content):
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        s.add_episode(_ep())
        assert s.set_wiki(A, "cached body", s.store_version(A))
        before = (_row(s, "r3-ep"), s.store_version(A), s.store_version(B), s.get_wiki(A))
        moved = _ep(uid=B, summary="The user lives in Porto." if change_content else "The user lives in Lisbon.")
        with pytest.raises(ValueError, match="user_id"):
            s.add_episode(moved)
        assert (_row(s, "r3-ep"), s.store_version(A), s.store_version(B), s.get_wiki(A)) == before
        assert s.episodes(B) == [] and s.get_wiki(B) is None
    finally:
        s.close()


def test_the_refusal_holds_against_another_connections_persisted_row(tmp_path):
    """The guard reads the PERSISTED row inside the write's transaction: a second connection's committed row is
    what is compared, not anything this connection cached."""
    a, b = SqliteStore(str(tmp_path / "s.db")), SqliteStore(str(tmp_path / "s.db"))
    try:
        a.add_episode(_ep())
        with pytest.raises(ValueError, match="user_id"):
            b.add_episode(_ep(uid=B))
        assert _row(a, "r3-ep")[0] == A
    finally:
        a.close()
        b.close()


# ---- 3. the control: same-owner replacement ----------------------------------------------------------------------

def test_a_same_owner_replacement_is_still_allowed_and_still_evicts(tmp_path):
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        s.add_episode(_ep())
        assert s.set_wiki(A, "cached body", s.store_version(A))
        v = s.store_version(A)
        s.add_episode(_ep(summary="The user lives in Porto."))
        assert Episode.model_validate_json(_row(s, "r3-ep")[1]).summary == "The user lives in Porto."
        assert s.store_version(A) > v and s.get_wiki(A) is None
        s.add_episode(_ep(summary="The user lives in Porto."))       # an identical replacement: allowed, view unmoved
    finally:
        s.close()


# ---- 4. X21 by id ------------------------------------------------------------------------------------------------

def _deleted_but_reserved(s):
    s.add_episode(_ep("r3-y", A, "input y"))
    s.add_episode(_ep("r3-z", A, "input z"))
    op = s.create_or_takeover_consolidation(A, ["r3-y", "r3-z"], "w1", 60)
    assert s.transition_consolidation_if_current(op.operation_id, op.fence, "w1", CS.GENERATING)
    assert s.write_consolidation_output_if_current(op.operation_id, op.fence, "w1", ConsolidationOutputDraft(
        summary="y and z", date_start="2026-01-02", date_end="2026-01-02"))
    assert s.transition_consolidation_if_current(op.operation_id, op.fence, "w1", CS.OUTPUTS_DURABLE)
    assert s.delete_claimed_inputs_if_current(op.operation_id, op.fence)
    assert _row(s, "r3-y") is None and "r3-y" in s._reserved_ids(A)
    return op


@pytest.mark.parametrize("owner", [A, B], ids=["the-reserving-owner", "another-owner"])
def test_a_deleted_but_reserved_id_is_refused_to_every_owner(tmp_path, owner):
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        _deleted_but_reserved(s)
        with pytest.raises(ValueError, match="reserved id"):
            s.add_episode(_ep("r3-y", owner, "a new y"))
        assert _row(s, "r3-y") is None
    finally:
        s.close()


def test_the_reservation_ends_when_the_op_finalizes(tmp_path):
    """The control on the other side: X21's reservation is the interval to FINALIZED, not a permanent ban."""
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        op = _deleted_but_reserved(s)
        assert s.transition_consolidation_if_current(op.operation_id, op.fence, "w1", CS.FINALIZED)
        s.add_episode(_ep("r3-y", B, "B's own y"))
        assert _row(s, "r3-y")[0] == B
    finally:
        s.close()


# ---- 5. INV-11 by id; the readers per user -----------------------------------------------------------------------

def _redacted_then_deleted(s):
    s.add_episode(_ep("r3-x", A, "The user lives in Lisbon."))
    s.redact(A, episode_id="r3-x", reason="subject_request")
    s.delete_episode("r3-x")
    assert _row(s, "r3-x") is None and "r3-x" in s.redacted_targets(A, "episode")


@pytest.mark.parametrize("owner", [A, B], ids=["the-redacting-owner", "another-owner"])
def test_a_redacted_then_deleted_id_is_refused_to_every_owner(tmp_path, owner):
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        _redacted_then_deleted(s)
        with pytest.raises(ValueError, match="is redacted"):
            s.add_episode(_ep("r3-x", owner, "The user lives in Lisbon."))
        assert _row(s, "r3-x") is None
    finally:
        s.close()


def test_a_present_redacted_episode_is_refused_to_another_owner(tmp_path):
    """Dev's sibling as found at 6cdb9aa: the row present, its owner's redaction applied; another owner's same-ID
    write once repopulated the erased summary. Refused now — by the ownership guard, before the attestation."""
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        s.add_episode(_ep("r3-x", A, "The user lives in Lisbon."))
        s.redact(A, episode_id="r3-x", reason="subject_request")
        held = _row(s, "r3-x")
        with pytest.raises(ValueError, match="user_id"):
            s.add_episode(_ep("r3-x", B, "The user lives in Lisbon."))
        assert _row(s, "r3-x") == held and s.episodes(B) == []
    finally:
        s.close()


def test_another_users_records_are_untouched_by_a_redaction_of_an_id_it_cannot_use(tmp_path):
    """Research's caution on N1: the id is held by the WRITE refusal only. B's own records — and B's view of
    redaction — are unaffected by A's redaction."""
    s = SqliteStore(str(tmp_path / "s.db"))
    try:
        _redacted_then_deleted(s)
        s.add_episode(_ep("r3-b-own", B, "The user lives in Lisbon."))
        assert s.redacted_targets(B, "episode") == frozenset()
        assert [e.id for e in s.episodes(B)] == ["r3-b-own"]
        assert s.redaction_records(B) == []
    finally:
        s.close()


# ---- 5b. the import's episode admission: the same two refusals, by the id ----------------------------------------

def _archive(tmp_path, eid, uid, name):
    src = Memory(llm=lambda q, **k: "x", config=MemoryConfig(db_path=str(tmp_path / f"{name}.db"),
                                                            require_source_id=False, scope_groups={}))
    try:
        src.store.add_episode(_ep(eid, uid, "The user lives in Lisbon."))
        out = str(tmp_path / f"{name}.jsonl")
        src.export_memory(uid, out)
        return out
    finally:
        src.close()


def _import(dst, path, uid, restore):
    return dst.import_memory(path, restore=True) if restore else dst.import_memory(path, user_id=uid)


@pytest.mark.parametrize("restore", [False, True], ids=["import", "restore"])
def test_an_import_of_another_owners_redacted_id_is_refused(tmp_path, restore):
    f = _archive(tmp_path, "r3-x", B, "b")
    dst = Memory(llm=lambda q, **k: "x", config=_cfg(tmp_path))
    try:
        _redacted_then_deleted(dst.store)
        with pytest.raises(ValueError, match="under another owner"):
            _import(dst, f, B, restore)
        assert _row(dst.store, "r3-x") is None and dst.store.episodes(B) == []
    finally:
        dst.close()


@pytest.mark.parametrize("restore", [False, True], ids=["import", "restore"])
@pytest.mark.parametrize("owner", [A, B], ids=["the-reserving-owner", "another-owner"])
def test_an_import_of_a_deleted_but_reserved_id_is_refused(tmp_path, owner, restore):
    """X21 was not consulted on the import path at all: even the reserving owner's own import was admitted, and its
    op's finalize would then delete the imported row by id."""
    f = _archive(tmp_path, "r3-y", owner, "o")
    dst = Memory(llm=lambda q, **k: "x", config=_cfg(tmp_path))
    try:
        _deleted_but_reserved(dst.store)
        with pytest.raises(ValueError, match="reserved by an in-flight consolidation"):
            _import(dst, f, owner, restore)
        assert _row(dst.store, "r3-y") is None
    finally:
        dst.close()


def test_an_import_of_a_fresh_id_is_still_admitted(tmp_path):
    """The control: another owner's redaction of a DIFFERENT id, and a finalized op, leave an ordinary import alone."""
    f = _archive(tmp_path, "r3-fresh", B, "b")
    dst = Memory(llm=lambda q, **k: "x", config=_cfg(tmp_path))
    try:
        _redacted_then_deleted(dst.store)
        _import(dst, f, B, False)
        assert [e.id for e in dst.store.episodes(B)] == ["r3-fresh"]
    finally:
        dst.close()


def test_a_restore_replaying_finalized_outputs_is_admitted_beside_an_in_flight_op(tmp_path):
    """Research's check on the import's (ii): it refuses only an id an op CLAIMS. A restore carrying a finalized op's
    outputs (store-minted `epc-` ids) is admitted while another op is in flight in the destination."""
    src = SqliteStore(str(tmp_path / "src.db"))
    try:
        op = _deleted_but_reserved(src)
        assert src.transition_consolidation_if_current(op.operation_id, op.fence, "w1", CS.FINALIZED)
        outputs = [e.id for e in src.episodes(A)]
        assert outputs and all(i.startswith("epc-") for i in outputs)
    finally:
        src.close()
    m = Memory(llm=lambda q, **k: "x", config=MemoryConfig(db_path=str(tmp_path / "src.db"), require_source_id=False,
                                                          scope_groups={}))
    f = str(tmp_path / "a.jsonl")
    try:
        m.export_memory(A, f)
    finally:
        m.close()
    dst = Memory(llm=lambda q, **k: "x", config=_cfg(tmp_path))
    try:
        dst.store.add_episode(_ep("r3-other-in", A, "input other"))
        dst.store.create_or_takeover_consolidation(A, ["r3-other-in"], "w2", 60)
        dst.import_memory(f, restore=True)
        assert {e.id for e in dst.store.episodes(A, include_retired=True)} >= set(outputs)
    finally:
        dst.close()


# ---- 6. conformance ---------------------------------------------------------------------------------------------

def test_the_protocol_states_the_obligation_the_backend_enforces():
    """The KEEP reason for `episode.user_id` names the protocol obligation, and the protocol states it: the
    premise the cached wiki relies on is a contract every backend is held to, not one backend's behaviour."""
    doc = inspect.getdoc(Store.add_episode) or ""
    assert "`user_id` never changes" in doc and "PERSISTED prior row" in doc
    assert "X21" in doc and "INV-11" in doc and "never" in doc and "incoming `user_id`" in doc
    assert "add_episode obligation" in ASSERTION_VIEW_KEEPS["episode"]["user_id"]
    assert getattr(SqliteStore.add_episode, "__isabstractmethod__", False) is False


# ---- 7. the census: every episode writer refuses by the id, or mints the id ---------------------------------------

def _episode_writer_census(text):
    """Generated from the AST: every function whose SQL inserts into `episodes` (INSERT, INSERT OR REPLACE), as
    (function, refuses-by-id, mints-the-id). Refuses by id: it calls `_id_reserved` AND an id-keyed attestation
    (`_attested_fields(_ANY_OWNER, ...)` or `_attested_by_another_owner`). Mints: it calls `uuid.uuid4()`, so the id
    it writes is fresh and no stored state can name it."""
    import ast
    import re
    out = []
    for fn in ast.walk(ast.parse(text)):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        sql = " ".join(" ".join(n.value.split()) for n in ast.walk(fn)
                       if isinstance(n, ast.Constant) and isinstance(n.value, str))
        if not re.search(r"INSERT (?:OR REPLACE )?INTO episodes\b", sql, re.I):
            continue
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        names = {n.func.attr for n in calls}
        by_id_attest = ("_attested_by_another_owner" in names or any(
            n.func.attr == "_attested_fields" and n.args and ast.unparse(n.args[0]) == "_ANY_OWNER" for n in calls))
        mints = any(n.func.attr == "uuid4" for n in calls)
        out.append((fn.name, "_id_reserved" in names and by_id_attest, mints))
    return sorted(out)


def test_every_episode_writer_refuses_by_the_id_or_mints_it():
    """0004 v3.5 §2c (ii)/(iii): a writer that admits a CALLER-CHOSEN episode id decides X21 and INV-11 by the id,
    whoever owns the stored state; a writer that mints the id needs neither. Generated over src/, never listed."""
    import pathlib
    import veracium
    root = pathlib.Path(veracium.__file__).resolve().parent
    census = [(str(p.relative_to(root)),) + row for p in sorted(root.rglob("*.py"))
              for row in _episode_writer_census(p.read_text())]
    assert ("store/sqlite.py", "add_episode", True, False) in census
    assert ("store/sqlite.py", "commit_outcome_import_plan", True, False) in census
    assert [c for c in census if not (c[2] or c[3])] == [], census


def test_the_census_finds_a_writer_keyed_by_the_incoming_owner():
    """The census is not vacuous: add_episode as shipped at 6cdb9aa is flagged, and so is the import with no X21."""
    shipped = ("def add_episode(self, episode):\n"
               "    self._attested_fields(episode.user_id, 'episode', episode.id, coverage=False)\n"
               "    if episode.id in self._reserved_ids(episode.user_id): pass\n"
               "    self._conn.execute('INSERT OR REPLACE INTO episodes(id) VALUES(?)', (episode.id,))\n")
    no_x21 = ("def commit_outcome_import_plan(self, user_id, plan):\n"
              "    self._attested_by_another_owner('episode', ep.id, user_id)\n"
              "    self._conn.execute('INSERT INTO episodes(id) VALUES(?)', (ep.id,))\n")
    minted = ("def append(self, u):\n"
              "    i = f'ep-{uuid.uuid4().hex}'\n"
              "    self._conn.execute('INSERT INTO episodes(id) VALUES(?)', (i,))\n")
    assert _episode_writer_census(shipped) == [("add_episode", False, False)]
    assert _episode_writer_census(no_x21) == [("commit_outcome_import_plan", False, False)]
    assert _episode_writer_census(minted) == [("append", False, True)]


def _edge_deleters(text):
    """Generated from the AST: every function that can DELETE edge rows — a literal `DELETE FROM edges`, or an f-string
    `DELETE FROM {name}` inside a loop whose iterable is a module-level tuple holding "edges"."""
    import ast
    tree = ast.parse(text)
    tuples = {t.id: {e.value for e in n.value.elts if isinstance(e, ast.Constant)}
              for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, (ast.Tuple, ast.List))
              for t in n.targets if isinstance(t, ast.Name)}
    out = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in ast.walk(fn):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and \
                    " ".join(n.value.split()).upper().startswith("DELETE FROM EDGES"):
                out.add(fn.name)
            if isinstance(n, ast.For) and isinstance(n.iter, ast.Name) and "edges" in tuples.get(n.iter.id, ()):
                for m in ast.walk(n):
                    if isinstance(m, ast.JoinedStr) and m.values and isinstance(m.values[0], ast.Constant) and \
                            m.values[0].value.upper().startswith("DELETE FROM"):
                        out.add(fn.name)
    return out


def test_edges_are_deleted_only_with_their_redactions():
    """Why an EDGE's INV-11 refusal may stay keyed by its owner (0004 v3.5 §2c (iii) names add_episode and the import
    only): no applied edge redaction outlives its row, because the only edge deletion is forget_user's erasure, which
    erases the user's redactions in the same statement loop. The day another edge deletion lands, this is red and (iii)
    must extend to add_edge."""
    import pathlib
    import veracium
    import veracium.store.sqlite as sq
    root = pathlib.Path(veracium.__file__).resolve().parent
    deleters = {(str(p.relative_to(root)), f) for p in sorted(root.rglob("*.py")) for f in _edge_deleters(p.read_text())}
    assert deleters == {("store/sqlite.py", "forget_user")}, sorted(deleters)
    assert {"edges", "redactions"} <= set(sq._ERASE_TABLES)


def test_the_edge_deleter_census_finds_both_forms():
    planted = ("_T = ('edges', 'wiki')\n"
               "def purge(self, i):\n    self._conn.execute('DELETE FROM edges WHERE id=?', (i,))\n"
               "def erase(self, u):\n    for t in _T:\n        self._conn.execute(f'DELETE FROM {t} WHERE user_id=?', (u,))\n"
               "def other(self, u):\n    for t in ('wiki',):\n        self._conn.execute(f'DELETE FROM {t}', ())\n")
    assert _edge_deleters(planted) == {"purge", "erase"}


def test_one_users_standing_notice_does_not_reach_another_users_import_of_the_id(tmp_path):
    """Research's caution on N1, at the readers: the id-keyed attestation is add_episode's and the import's WRITE
    refusal only. A notice is the one redaction state that names an id its user does not hold: A's standing notice for
    `r3-n` must not refuse B's own import of a record `r3-n`. (A by-id `_attested_fields` alone does not reach this
    path — the notice refusal reads the notice tables — so this cell holds the behaviour, not that mutant.)"""
    import json as _j
    from veracium import portability as port
    from veracium.schema import Edge
    prov = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r3-n-ev")

    def mem(name):
        return Memory(llm=lambda q, **k: "x", config=MemoryConfig(db_path=str(tmp_path / name), require_source_id=False,
                                                                 scope_groups={}))
    src = mem("a-src.db")
    src.store.add_edge(Edge(id="r3-n", user_id=A, subject="user", relation="likes", object="tea", provenance=prov))
    src.redact(A, edge_id="r3-n", reason="subject_request")
    full = tmp_path / "a.jsonl"
    port.export_memory(src.store, A, full)
    src.close()
    lines = [_j.loads(x) for x in full.read_text().splitlines()]
    notices = tmp_path / "a-notices.jsonl"
    notices.write_text("".join(_j.dumps(x) + "\n" for x in [lines[0], *[x for x in lines[1:]
                                                                        if x.get("record") == "redaction"]]))
    b = mem("b-src.db")
    b.store.add_edge(Edge(id="r3-n", user_id=B, subject="user", relation="likes", object="coffee", provenance=prov))
    plain = tmp_path / "b.jsonl"
    port.export_memory(b.store, B, plain)
    b.close()
    victim = mem("victim.db")
    try:
        r = port.import_memory(victim.store, notices)
        assert r["notices_standing"] == 1
        port.import_memory(victim.store, plain, user_id=B)
        got = victim.store._conn.execute("SELECT user_id, json FROM edges WHERE id='r3-n'").fetchone()
        assert got is not None and got[0] == B and _j.loads(got[1])["object"] == "coffee"
    finally:
        victim.close()


@pytest.mark.parametrize("kind", ["episode", "edge"])
@pytest.mark.parametrize("a_notice", [False, True], ids=["control-no-notice", "A-holds-a-standing-notice"])
def test_another_users_standing_notice_never_covers_a_forged_redacted_reason(tmp_path, kind, a_notice):
    """Research's pushback on dropping "every _attested_fields reader keys by id" (research c31b3190): the import's
    coverage reader (coverage=True) decides whether an arrival's `redacted` reason is the treated shape of a notice it
    holds, and it is the DESTINATION user's: A's STANDING notice for `r3-f` must not cover B's hand-built arrival whose
    `r3-f` carries the reason `redacted` and no notice (0041 §11.2: only a redaction writes it). Refused either way."""
    import json as _j
    from veracium import portability as port
    from veracium.schema import Edge
    prov = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="r3-f-ev")

    def mem(name):
        return Memory(llm=lambda q, **k: "x", config=MemoryConfig(db_path=str(tmp_path / name), require_source_id=False,
                                                                 scope_groups={}))

    def rec(uid, content):
        if kind == "episode":
            return lambda s: s.add_episode(_ep("r3-f", uid, content))
        return lambda s: s.add_edge(Edge(id="r3-f", user_id=uid, subject="user", relation="likes", object=content,
                                         provenance=prov))

    def lines(p):
        return [_j.loads(x) for x in p.read_text().splitlines() if x.strip()]

    def write(p, ls):
        p.write_text("".join(_j.dumps(x) + "\n" for x in ls))
        return p
    dst = mem("dst.db")
    try:
        if a_notice:
            src = mem("a-src.db")
            rec(A, "tea")(src.store)
            src.redact(A, **{f"{kind}_id": "r3-f"}, reason="subject_request")
            full = tmp_path / "a.jsonl"
            port.export_memory(src.store, A, full)
            src.close()
            ls = lines(full)
            r = port.import_memory(dst.store, write(tmp_path / "a-notices.jsonl",
                                                    [ls[0], *[x for x in ls[1:] if x.get("record") == "redaction"]]),
                                   restore=True)
            assert r["notices_standing"] == 1
        b = mem("b-src.db")
        rec(B, "coffee")(b.store)
        plain = tmp_path / "b.jsonl"
        port.export_memory(b.store, B, plain)
        b.close()
        ls, n = lines(plain), 0
        for x in ls[1:]:
            if x.get("record") == kind and x.get("id") == "r3-f":
                if kind == "episode":
                    x["retired_reason"] = "redacted"
                else:
                    x["invalidation_reason"] = "redacted"
                    x["invalidated_at"] = x.get("valid_from") or "2026-01-03T00:00:00+00:00"
                n += 1
        assert n == 1, "the forged field must land on exactly one record"
        with pytest.raises(ValueError, match="only a redaction writes"):
            port.import_memory(dst.store, write(tmp_path / "b-forged.jsonl", ls), user_id=B)
        table = "episodes" if kind == "episode" else "edges"
        assert dst.store._conn.execute(f"SELECT 1 FROM {table} WHERE id='r3-f'").fetchone() is None
    finally:
        dst.close()
