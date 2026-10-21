"""R-I / R-II round 2, V1 — the shared full-suite hold. The reviewer's complete run failed
tests/eval/test_semantic_recall_gate.py::test_fixture_topology_is_tie_free_and_insertion_invariant during fixture
construction: `attempt to write a readonly database` while `embed_backfill` inserted an embedding, after every
`add_edge` to that store had succeeded. The test passed alone there and here, and the whole suite through the
package's own launcher passed here (6598 passed, 0 failed).

What this file shows, and its limit:
(a) the MECHANISM is sufficient: removing an open DELETE-journal store's directory, or replacing its file, between
    writes gives exactly that message at that site, with the extended code SQLITE_READONLY_DBMOVED (1032). The
    message alone cannot say it was that: a read-only file (SQLITE_READONLY, 8) prints the same message (the third
    cell), and the reviewer's trace kept only the message. So this is sufficiency, not the cause of their failure;
    the cause is not identified.
(c) the one concrete deleter named (research's stage-1 read): pytest removes an explicit `--basetemp` when a session
    starts, and the reviewer gave one path to an interrupted suite and then the full one. The conftest's
    `hold_basetemp` makes a second live session on a held path refuse by name.
(d) the conftest records each sqlite3 error's extended name on a failing test's report, so the next one says which.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import textwrap
import types

import pytest

from veracium import Memory, MemoryConfig
from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance

U = "v1-user"
READONLY = "attempt to write a readonly database"


class _Embed:
    def id(self):
        return "v1-stub"

    def dim(self):
        return 3

    def __call__(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def _edge(i):
    return Edge(id=f"e{i}", user_id=U, subject="user", relation="likes", object=f"thing {i}", provenance=Provenance(
        author_of_evidence=EvidenceAuthor.USER, evidence_ref="v1", disclosure=Disclosure.MENTIONABLE))


def _store(tmp_path):
    d = tmp_path / "t0"
    d.mkdir()
    m = Memory(llm=lambda p, **k: "", embed=_Embed(),
               config=MemoryConfig(db_path=str(d / "m.db"), wiki_recompile_after_writes=0))
    for i in range(3):
        m.store.add_edge(_edge(i))                       # every add_edge succeeds, as in the reviewer's run
    return m, d


def _chain(exc):
    out = []
    while exc is not None:
        out.append(exc)
        exc = exc.__cause__ or exc.__context__
    return out


@pytest.mark.parametrize("change", ["none", "remove-directory", "replace-file"])
def test_a_store_moved_between_writes_refuses_the_next_write_as_dbmoved(tmp_path, change):
    m, d = _store(tmp_path)
    try:
        if change == "remove-directory":
            shutil.rmtree(d)
        elif change == "replace-file":
            os.unlink(d / "m.db")
            sqlite3.connect(d / "m.db").close()
        if change == "none":
            assert m.embed_backfill(U) == 3                # the control: the same build completes
            return
        with pytest.raises(sqlite3.OperationalError) as ei:
            m.embed_backfill(U)
        errs = [e for e in _chain(ei.value) if isinstance(e, sqlite3.Error)]
        assert any(READONLY in str(e) for e in errs), [str(e) for e in errs]
        assert any("_upsert_embedding_in_txn" == f.name for f in ei.traceback), "not the reviewer's site"
        if sys.version_info < (3, 11):
            pytest.skip("sqlite_errorname exists from Python 3.11: the message is asserted, the code is not")
        assert {getattr(e, "sqlite_errorname", None) for e in errs} & {"SQLITE_READONLY_DBMOVED"}, \
            [(type(e).__name__, getattr(e, "sqlite_errorname", None)) for e in errs]
    finally:
        try:
            m.close()
        except sqlite3.Error:
            pass


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root writes a read-only file")
def test_a_read_only_file_prints_the_same_message_under_another_code(tmp_path):
    """The limit of (a): the message is shared. A file opened read-only (a chmod before the open; one already open
    keeps its descriptor's mode) refuses a write with the same message under SQLITE_READONLY, so only the extended code
    tells it from DBMOVED. Plain sqlite3: the code is SQLite's, whatever opens the file."""
    db = tmp_path / "ro.db"
    c = sqlite3.connect(db)
    c.execute("PRAGMA journal_mode=DELETE")
    c.execute("CREATE TABLE t(x)")
    c.commit()
    c.close()
    os.chmod(db, 0o444)
    try:
        c = sqlite3.connect(db)
        with pytest.raises(sqlite3.OperationalError, match=READONLY) as ei:
            c.execute("INSERT INTO t VALUES (1)")
        c.close()
        if sys.version_info >= (3, 11):
            assert ei.value.sqlite_errorname == "SQLITE_READONLY", ei.value.sqlite_errorname
    finally:
        os.chmod(db, 0o644)


def _conftest(request):
    path = pathlib.Path(__file__).with_name("conftest.py").resolve()
    mods = [p for p in request.config.pluginmanager.get_plugins()
            if isinstance(p, types.ModuleType) and getattr(p, "__file__", None)
            and pathlib.Path(p.__file__).resolve() == path]
    assert len(mods) == 1, "the suite's conftest is not loaded as a plugin"
    return mods[0]


def test_the_error_names_are_read_from_the_whole_chain(request):
    cf = _conftest(request)
    try:
        try:
            sqlite3.connect(":memory:").execute("SELECT * FROM no_such_table")
        except sqlite3.OperationalError as e:
            raise RuntimeError("a wrapper, as the store's journaled-write refusal is") from e
    except RuntimeError as outer:
        names = cf.sqlite_error_names(outer)
    assert [n[0] for n in names] == ["OperationalError"] and "no such table" in names[0][2]
    assert names[0][1] == ("SQLITE_ERROR" if sys.version_info >= (3, 11) else None)


def test_a_held_basetemp_refuses_a_second_session_by_name(request, tmp_path):
    cf = _conftest(request)
    cfg = lambda bt, **kw: types.SimpleNamespace(option=types.SimpleNamespace(basetemp=bt), **kw)
    bt = str(tmp_path / "suite-tmp")
    first = cfg(bt)
    if importlib.util.find_spec("fcntl") is None:
        pytest.skip("no fcntl on this platform: nothing is held, and nothing is claimed")
    lock = cf.hold_basetemp(first)
    assert lock is not None, "an explicit basetemp with fcntl available was not held"
    try:
        assert lock == tmp_path / ".suite-tmp.lock" and lock.read_text() == str(os.getpid())
        with pytest.raises(pytest.UsageError, match=rf"held by a live pytest session \(pid {os.getpid()}\)"):
            cf.hold_basetemp(cfg(bt))
        assert cf.hold_basetemp(cfg(None)) is None                        # no explicit basetemp: nothing to hold
        assert cf.hold_basetemp(cfg(bt, workerinput={})) is None          # an xdist worker runs under its controller
    finally:
        os.close(first.veracium_basetemp_lock)
    second = cfg(bt)
    assert cf.hold_basetemp(second) == lock                               # released: the next session takes it
    os.close(second.veracium_basetemp_lock)


def test_a_second_live_pytest_session_on_one_basetemp_refuses_and_deletes_nothing(tmp_path):
    """The mechanism, run: a first pytest session (the suite's conftest loaded as a plugin) waits inside a test that
    has written a file under its basetemp; a second session given the same --basetemp exits 4 naming the first one's
    pid, and the first session's file is still there. Control: once the first ends, the same path is taken."""
    tests_dir = pathlib.Path(__file__).resolve().parent
    work = tmp_path / "work"
    work.mkdir()
    gate, ready = work / "go", work / "ready"
    (work / "test_hold.py").write_text(textwrap.dedent(f"""
        import pathlib, time
        def test_hold(tmp_path):
            (tmp_path / "store.db").write_text("x")
            pathlib.Path({str(ready)!r}).write_text(str(tmp_path / "store.db"))
            for _ in range(600):
                if pathlib.Path({str(gate)!r}).exists():
                    return
                time.sleep(0.05)
            raise AssertionError("never released")
    """))
    (work / "test_quick.py").write_text("def test_quick():\n    pass\n")
    bt = tmp_path / "shared-tmp"
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tests_dir), os.environ.get("PYTHONPATH", "")]))
    base = [sys.executable, "-m", "pytest", "-q", "-p", "conftest", "-p", "no:randomly", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-c", os.devnull, "--rootdir", str(work), f"--basetemp={bt}"]
    first = subprocess.Popen(base + [str(work / "test_hold.py")], cwd=work, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(600):
            if ready.exists() or first.poll() is not None:
                break
            __import__("time").sleep(0.05)
        assert ready.exists(), first.communicate(timeout=30)[0]
        held_file = pathlib.Path(ready.read_text())
        second = subprocess.run(base + [str(work / "test_quick.py")], cwd=work, env=env, capture_output=True,
                                text=True, timeout=120)
        assert second.returncode == 4, (second.returncode, second.stdout, second.stderr)
        assert f"held by a live pytest session (pid {first.pid})" in second.stdout + second.stderr
        assert held_file.exists()                                        # nothing of the first session was removed
    finally:
        gate.write_text("go")
        out = first.communicate(timeout=60)[0]
    assert first.returncode == 0, out
    again = subprocess.run(base + [str(work / "test_quick.py")], cwd=work, env=env, capture_output=True, text=True,
                           timeout=120)
    assert again.returncode == 0, (again.stdout, again.stderr)
