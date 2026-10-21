"""specs/0047 §4d, INV-R18 — R-II round 2's RII-01: the wiki body a recall serves and the call's challenge snapshot
come from ONE state (compile.bound_wiki), so a body never asserts a fact the same call reports as challenged.

The reviewer's counterexample was the cached path; research's stage-1 read (READ-RII-phase0-stage1.md B1) showed the
window open on all three ensure_wiki paths, and answering its question showed a fourth, sequential instance: an
IMPORTED challenge left the cached wiki in place. Each cell interleaves at bound_wiki's own snapshot read and asserts
that it did (research's trap: compile_wiki reads the snapshot itself, and a probe that interleaves there measures the
compile's fence, not this window), and asserts the path the call took.

The census below holds the bind's precondition: every write of a reply evicts the user's wiki in its own function.
Confirmations are out of its scope by the withheld rule itself: ChallengeSnapshot.withheld reads only the open
challenges (`challenged`), never `confirmation_origins`, so a confirmation cannot make a cached body assert anything
the snapshot withholds.
"""
import ast
import pathlib
import re
import sys

import pytest

from veracium import Memory, MemoryConfig, budgets
from veracium import compile as compile_mod
from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance

U = "bind-user"
FACT = "Toronto"
WIKI_LINE = "User has a fact about Toronto."   # the provider's body: the wiki, not an edge line, asserts it
SRC = pathlib.Path(compile_mod.__file__).resolve().parent


def _edge(eid, obj, rel="located_at"):
    return Edge(id=eid, user_id=U, subject="user", relation=rel, object=obj, provenance=Provenance(
        author_of_evidence=EvidenceAuthor.USER, evidence_ref="bind", disclosure=Disclosure.MENTIONABLE))


def _cfg(path, after=1):
    return MemoryConfig(db_path=str(path), wiki_recompile_after_writes=after, require_source_id=False, scope_groups={})


def _bind_site_hook(monkeypatch, store, before=None, after=None):
    """Wrap the store's snapshot read; run `before`/`after` around it ONLY when bound_wiki is the caller. Returns the
    list of callers seen, so a cell can assert the interleave happened at the window under test."""
    real, callers = store.challenge_snapshot, []

    def hooked(user_id):
        f = sys._getframe(1).f_code
        site = f"{pathlib.Path(f.co_filename).name}:{f.co_name}"
        callers.append(site)
        bind = site == "compile.py:bound_wiki"
        if bind and before is not None:
            before(len([c for c in callers if c == site]))
        snap = real(user_id)
        if bind and after is not None:
            after(len([c for c in callers if c == site]))
        return snap
    monkeypatch.setattr(store, "challenge_snapshot", hooked)
    return callers


def _record_publishes(monkeypatch, store):
    real, published = store.set_wiki, []

    def rec(*a, **k):
        ok = real(*a, **k)
        published.append(bool(ok))
        return ok
    monkeypatch.setattr(store, "set_wiki", rec)
    return published


def _provider(state):
    def provider(prompt, *, role="compile", **kw):
        if role != "compile":
            return "ok"
        state["compiles"] = state.get("compiles", 0) + 1
        if state.get("during_compile") and not state.get("done"):
            state["done"] = True
            state["during_compile"]()
        facts = [f for f in ("Toronto", "Lisbon") if f in prompt]
        return " ".join(f"User has a fact about {f}." for f in facts) or "No current location fact."
    return provider


# ================================================================================ the window, on every path
@pytest.mark.parametrize("path", ["cached", "compiled_published", "compiled_unpublished"])
def test_a_challenge_before_the_bound_snapshot_is_never_asserted_by_the_body(tmp_path, monkeypatch, path):
    """A challenge committed after the body is read and before the call's snapshot: the inspection reports it and the
    body does not assert it, on the cached, the published-compile and the unpublished-compile paths.
    Mutant (07df8f8's recall): the body read before the snapshot is served as is — all three fail."""
    state = {}
    reader, writer = (Memory(llm=_provider(state), config=_cfg(tmp_path / "m.db")) for _ in range(2))
    try:
        reader.store.add_edge(_edge("location", FACT))
        if path == "cached":
            assert WIKI_LINE in reader.recall(U, FACT, semantic=False).grounded and reader.store.get_wiki(U) is not None
        if path == "compiled_unpublished":                 # a plain concurrent write during the compile
            state["during_compile"] = lambda: writer.store.add_edge(_edge("other", "tea", rel="prefers"))
        compiles = state.get("compiles", 0)
        published = _record_publishes(monkeypatch, reader.store)
        challenged, first = [], []

        def challenge(n):
            if not challenged:
                # the path the call's FIRST ensure_wiki took, read at the bound snapshot it precedes
                first.append((state.get("compiles", 0) - compiles, list(published)))
                challenged.append(writer.reply(U, "location", kind="challenge", text="Please withhold this."))
        callers = _bind_site_hook(monkeypatch, reader.store, before=challenge)
        r = reader.recall(U, FACT, semantic=False)
        assert challenged and "compile.py:bound_wiki" in callers, callers
        # the path really is the one named: the first ensure_wiki served the cache, published, or could not publish
        assert first == [{"cached": (0, []), "compiled_published": (1, [True]),
                          "compiled_unpublished": (1, [False])}[path]], first
        assert not r.inspection["location"].challenge_clear
        assert FACT not in r.grounded, r.grounded
    finally:
        reader.close()
        writer.close()


@pytest.mark.parametrize("path", ["cached", "compiled_published"])
def test_a_challenge_after_the_bound_snapshot_leaves_the_call_coherent(tmp_path, monkeypatch, path):
    """The control: a challenge committed right after the call's snapshot (same thread: no read window is held, so the
    writer never waits on this call). A compiled body is bound by its inputs against the call's snapshot, which
    predates the challenge: this call is clear and the body asserts the fact. A cached body's row is evicted before
    the bind re-reads it: the call recomputes, and its fresh snapshot withholds the fact both ways. Either way the
    body and the inspection agree, and the next call withholds."""
    state = {}
    reader, writer = (Memory(llm=_provider(state), config=_cfg(tmp_path / "m.db")) for _ in range(2))
    try:
        reader.store.add_edge(_edge("location", FACT))
        if path == "cached":
            reader.recall(U, FACT, semantic=False)
            assert reader.store.get_wiki(U) is not None
        done = []

        def challenge(n):
            if not done:
                done.append(writer.reply(U, "location", kind="challenge", text="Please withhold this."))
        callers = _bind_site_hook(monkeypatch, reader.store, after=challenge)
        r1 = reader.recall(U, FACT, semantic=False)
        assert done and "compile.py:bound_wiki" in callers
        clear = r1.inspection["location"].challenge_clear
        assert clear == (WIKI_LINE in r1.grounded), r1.grounded            # coherent, whichever state it read
        assert clear == {"compiled_published": True, "cached": False}[path]
        assert callers.count("compile.py:bound_wiki") == {"compiled_published": 1, "cached": 2}[path], callers
        monkeypatch.undo()
        r2 = reader.recall(U, FACT, semantic=False)
        assert not r2.inspection["location"].challenge_clear and FACT not in r2.grounded, r2.grounded
    finally:
        reader.close()
        writer.close()


def test_a_resolve_before_the_bound_snapshot_is_served_from_a_fresh_body(tmp_path, monkeypatch):
    """The resolve direction: a body compiled while the fact was challenged OMITS it (it asserts nothing false); a
    resolve committed before the call's snapshot evicts that body, so the call serves one that carries the fact, and
    the inspection agrees (clear)."""
    state = {}
    reader, writer = (Memory(llm=_provider(state), config=_cfg(tmp_path / "m.db", after=10**6)) for _ in range(2))
    try:
        reader.store.add_edge(_edge("location", FACT))
        cid = reader.reply(U, "location", kind="challenge", text="Please withhold this.")["reply_id"]
        omitted = reader.recall(U, FACT, semantic=False)
        assert WIKI_LINE not in omitted.grounded and reader.store.get_wiki(U) is not None
        done = []

        def resolve(n):
            if not done:
                done.append(writer.reply(U, "location", kind="resolve", target=cid))
        callers = _bind_site_hook(monkeypatch, reader.store, before=resolve)
        r = reader.recall(U, FACT, semantic=False)
        assert done and "compile.py:bound_wiki" in callers
        assert r.inspection["location"].challenge_clear and WIKI_LINE in r.grounded, r.grounded
    finally:
        reader.close()
        writer.close()


def test_a_body_that_fails_its_bind_twice_is_the_disputed_notice(tmp_path, monkeypatch):
    """The retry is bounded: a challenge before each of the call's two bound snapshots (Toronto, then Lisbon, each a fact
    the body then drew on) leaves the disputed notice, never a body asserting either fact, and never a third compile."""
    state = {}
    reader, writer = (Memory(llm=_provider(state), config=_cfg(tmp_path / "m.db")) for _ in range(2))
    try:
        reader.store.add_edge(_edge("location", FACT))
        reader.store.add_edge(_edge("trip", "Lisbon", rel="visited"))
        targets = {1: "location", 2: "trip"}

        def challenge(n):
            if n in targets:
                writer.reply(U, targets.pop(n), kind="challenge", text="Please withhold this.")
        callers = _bind_site_hook(monkeypatch, reader.store, before=challenge)
        r = reader.recall(U, "Toronto Lisbon", semantic=False)
        assert callers.count("compile.py:bound_wiki") == 2 and not targets
        assert budgets.DISPUTED_DURING_COMPILE_NOTICE in r.grounded
        assert FACT not in r.grounded and "Lisbon" not in r.grounded, r.grounded
    finally:
        reader.close()
        writer.close()


# ================================================================================ the imported challenge (sequential)
@pytest.mark.parametrize("route", ["import", "local_reply"])
def test_a_challenge_admitted_after_a_cached_wiki_is_never_asserted_by_it(tmp_path, route):
    """No concurrency: a wiki cached on a fact, then a challenge of it admitted by an IMPORT (the file's record is
    skipped, its challenge act admitted) or written locally, under the default recompile threshold. Mutant (07df8f8's
    import): one bump and no eviction, so the cached body grounds the fact beside the withheld notice."""
    src = Memory(llm=_provider({}), config=_cfg(tmp_path / "a.db", after=8))
    src.store.add_edge(_edge("location", FACT))
    src.export_memory(U, tmp_path / "f0.jsonl")
    src.reply(U, "location", kind="challenge", text="Please withhold this.")
    src.export_memory(U, tmp_path / "f1.jsonl")
    src.close()
    dst = Memory(llm=_provider({}), config=_cfg(tmp_path / "b.db", after=8))
    try:
        dst.import_memory(tmp_path / "f0.jsonl", restore=True)
        assert WIKI_LINE in dst.recall(U, FACT, semantic=False).grounded and dst.store.get_wiki(U) is not None
        if route == "import":
            r1 = dst.import_memory(tmp_path / "f1.jsonl", restore=True)
            assert (r1["edges"], r1["skipped"], r1["replies"]) == (0, 1, 1), r1
        else:
            dst.reply(U, "location", kind="challenge", text="Please withhold this.")
        assert dst.store.get_wiki(U) is None              # evicted in the writer's own transaction
        r = dst.recall(U, FACT, semantic=False)
        assert not r.inspection["location"].challenge_clear and FACT not in r.grounded, r.grounded
    finally:
        dst.close()


# ================================================================================ the precondition, as a census
_WRITE = re.compile(r"\b(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|REPLACE\s+INTO|UPDATE|DELETE\s+FROM)\s+(\w+|\{\w*\})", re.I)
_EVICT = re.compile(r"DELETE\s+FROM\s+(?:wiki|\{wiki\})\s+WHERE\s+user_id\s*=\s*\?", re.I)


def _module_tuples(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, ast.Tuple) and all(isinstance(e, ast.Constant) for e in n.value.elts):
            out[n.targets[0].id] = [e.value for e in n.value.elts]
    return out


def _sql_texts(fn, arg, loops, tuples):
    """Every SQL text `arg` can be, or None when the function's own source cannot resolve it. A placeholder bound by a
    `for` over a module-level tuple of names expands to each name (forget_user's erasure loop); any other placeholder
    stays `{}`, which the census treats as ANY table — the import's act loop writes `INSERT INTO {a['table']}`, and
    research's trap is that a literal match never sees it."""
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return [arg.value]
    if isinstance(arg, ast.JoinedStr):
        outs = [""]
        for v in arg.values:
            if isinstance(v, ast.Constant):
                outs = [o + v.value for o in outs]
            elif isinstance(v.value, ast.Name) and v.value.id in loops and loops[v.value.id] in tuples:
                outs = [o + "{" + t + "}" for o in outs for t in tuples[loops[v.value.id]]]
            else:
                outs = [o + "{}" for o in outs]
        return outs
    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
        a, b = _sql_texts(fn, arg.left, loops, tuples), _sql_texts(fn, arg.right, loops, tuples)
        return None if a is None or b is None else [x + y for x in a for y in b]
    if isinstance(arg, ast.IfExp):
        a, b = _sql_texts(fn, arg.body, loops, tuples), _sql_texts(fn, arg.orelse, loops, tuples)
        return None if a is None or b is None else a + b
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "format":
        base = _sql_texts(fn, arg.func.value, loops, tuples)
        return None if base is None else [re.sub(r"\{[^}]*\}", "{}", b) for b in base]
    if isinstance(arg, ast.Name):
        parts = []
        for n in ast.walk(fn):
            tgt = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(n, ast.AugAssign) else []
            if any(isinstance(t, ast.Name) and t.id == arg.id for t in tgt):
                v = _sql_texts(fn, n.value, loops, tuples)
                if v is None:
                    return None
                parts += v
        return [" ".join(parts)] if parts else None
    return None


def reply_writer_census(source: str):
    """{function: (evicts, [(line, write)])} for every function whose SQL can write `replies`, and the (function,
    line) of every execute whose SQL the census cannot resolve (each refuses). Scope: one function is the unit; the
    shipped writers run their statements in one transaction per function, which the behaviour cells above exercise."""
    tree = ast.parse(source)
    tuples = _module_tuples(tree)
    writers, unresolved = {}, []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        loops = {f.target.id: f.iter.id for f in ast.walk(fn) if isinstance(f, ast.For)
                 and isinstance(f.target, ast.Name) and isinstance(f.iter, ast.Name)}
        evicts, writes = False, []
        for c in ast.walk(fn):
            if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    and c.func.attr in ("execute", "executemany") and c.args):
                continue
            texts = _sql_texts(fn, c.args[0], loops, tuples)
            if texts is None:
                unresolved.append((fn.name, c.lineno))
                continue
            for t in texts:
                evicts = evicts or bool(_EVICT.search(t))
                writes += [(c.lineno, m.group(0)) for m in _WRITE.finditer(t)
                           if m.group(1).lower() in ("replies", "{replies}", "{}")]
        if writes:
            writers[fn.name] = (evicts, writes)
    return writers, unresolved


def _sqlite_source():
    return (SRC / "store" / "sqlite.py").read_text(encoding="utf-8")


def test_every_reply_writer_evicts_the_wiki_in_its_own_function():
    writers, unresolved = reply_writer_census(_sqlite_source())
    assert not unresolved, unresolved
    # anchor: the census sees the literal writers, the redaction's updates, the import's NON-literal act loop and the
    # erasure loop (a census blind to the import would pass at 07df8f8)
    assert {"add_reply", "_redact_in_txn", "commit_outcome_import_plan", "forget_user"} <= set(writers), writers
    assert [k for k, (ev, _w) in writers.items() if not ev] == [], writers


def _span(source, fn_name):
    tree = ast.parse(source)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name)
    lines = source.splitlines(keepends=True)
    return sum(map(len, lines[:fn.lineno - 1])), sum(map(len, lines[:fn.end_lineno]))


def _without_eviction(source, fn_name):
    a, b = _span(source, fn_name)
    body = source[a:b]
    stmt = 'self._conn.execute("DELETE FROM wiki WHERE user_id=?", '
    assert body.count(stmt) >= 1, (fn_name, "anchor absent")
    return source[:a] + body.replace(stmt, 'self._conn.execute("SELECT 1 FROM wiki WHERE user_id=?", ') + source[b:]


@pytest.mark.parametrize("fn_name", ["add_reply", "_redact_in_txn", "commit_outcome_import_plan"])
def test_the_census_flags_a_reply_writer_without_its_eviction(fn_name):
    """The census's mutants: each writer's eviction removed in turn is FLAGGED (the import's is 07df8f8's state)."""
    writers, unresolved = reply_writer_census(_without_eviction(_sqlite_source(), fn_name))
    assert not unresolved and writers[fn_name][0] is False, writers.get(fn_name)


def test_the_census_flags_an_erasure_loop_without_the_wiki_and_refuses_unresolved_sql():
    src = _sqlite_source()
    anchor = '"edges", "episodes", "wiki", "write_counter",'
    assert src.count(anchor) == 1
    writers, _u = reply_writer_census(src.replace(anchor, '"edges", "episodes", "write_counter",'))
    assert writers["forget_user"][0] is False
    probe = "def probe(self, q):\n    self._conn.execute(q)\n"
    assert reply_writer_census(probe)[1] == [("probe", 2)]


def test_no_other_module_writes_replies():
    """The census reads store/sqlite.py; no other module of the package carries SQL that writes `replies`."""
    hits = []
    for p in sorted(SRC.rglob("*.py")):
        if p.name == "sqlite.py" and p.parent.name == "store":
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                hits += [(p.name, n.lineno) for m in _WRITE.finditer(n.value) if m.group(1).lower() == "replies"]
    assert hits == [], hits


def test_a_row_evicted_between_the_staleness_check_and_the_read_recompiles(tmp_path, monkeypatch):
    """ensure_wiki reads the row twice (needs_recompile, then the body): a reply between the two leaves None. The body
    read recompiles, as a stale cache does, rather than index None. Mutant (07df8f8): `get_wiki(user_id)[0]` raises
    TypeError."""
    state = {}
    reader, writer = (Memory(llm=_provider(state), config=_cfg(tmp_path / "m.db", after=10**6)) for _ in range(2))
    try:
        reader.store.add_edge(_edge("location", FACT))
        reader.recall(U, FACT, semantic=False)
        real, reads = reader.store.get_wiki, []

        def evict_after_first(user_id):
            reads.append(1)
            row = real(user_id)
            if len(reads) == 1:
                writer.reply(U, "location", kind="challenge", text="Please withhold this.")
            return row
        monkeypatch.setattr(reader.store, "get_wiki", evict_after_first)
        compiles = state["compiles"]
        try:
            r = reader.recall(U, FACT, semantic=False)
        except TypeError as e:                       # the defect's own shape, reported as the cell's failure
            raise AssertionError(f"the evicted row was indexed: {e}") from e
        assert len(reads) >= 2 and state["compiles"] > compiles
        assert not r.inspection["location"].challenge_clear and FACT not in r.grounded, r.grounded
    finally:
        reader.close()
        writer.close()
