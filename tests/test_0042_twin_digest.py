"""specs/0042 — the twin digest's own controls.

The digest exists so a SECOND SEAT can check "this tree's twin is the twin the committed run used" — the claim
that earns skipping an eighteen-minute harness re-run. An instrument whose job is to make a claim checkable is
worth nothing if it cannot tell two trees apart, so every kind of difference a twin can carry is injected here
and the digest must move. Two of these are the reviewer's own proposed controls, written before they ran them.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m; spec.loader.exec_module(m); return m


td = _load("twin_digest_under_test", EVIDENCE / "twin_digest.py")


def _tree(base, files):
    for rel, body in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
    return base


BASE = {"a.py": b"print(1)\n", "pkg/b.py": b"x = 2\n", "pkg/sub/c.py": b"", "d.txt": b"hello"}


def test_the_digest_moves_for_every_kind_of_difference(tmp_path):
    """The instrument's own matrix. A digest that does not move is a digest that certifies a difference."""
    reference = td.digest(_tree(tmp_path / "ref", dict(BASE)))
    cases = {}

    one_byte = dict(BASE); one_byte["pkg/b.py"] = b"x = 3\n"
    cases["one byte changed"] = one_byte

    renamed = {("pkg/renamed.py" if k == "pkg/b.py" else k): v for k, v in BASE.items()}
    cases["one file renamed, same bytes"] = renamed

    moved = {("other/b.py" if k == "pkg/b.py" else k): v for k, v in BASE.items()}
    cases["one file moved to another directory"] = moved

    added = dict(BASE); added["pkg/extra.py"] = b""
    cases["an EMPTY file added"] = added

    removed = {k: v for k, v in BASE.items() if k != "d.txt"}
    cases["one file removed"] = removed

    swapped = dict(BASE); swapped["a.py"], swapped["d.txt"] = BASE["d.txt"], BASE["a.py"]
    cases["two files' contents swapped"] = swapped

    for label, files in cases.items():
        got = td.digest(_tree(tmp_path / label.replace(" ", "_").replace(",", ""), files))
        assert got != reference, f"{label}: the digest did not move, so it cannot certify a difference"
    assert len({td.digest(tmp_path / l.replace(" ", "_").replace(",", "")) for l in cases}) == len(cases), \
        "two different trees share a digest — the instrument collides on cases it is meant to separate"


def test_the_root_is_not_part_of_the_digest(tmp_path):
    """The other half, and the one an over-eager definition breaks: the SAME twin derived into two directories
    must digest the same, or no two seats could ever agree. The path INSIDE the root is part of the hash; the
    path TO the root is not."""
    a = td.digest(_tree(tmp_path / "somewhere", dict(BASE)))
    b = td.digest(_tree(tmp_path / "somewhere_else_entirely" / "nested" / "deeper", dict(BASE)))
    assert a == b


def test_an_empty_tree_is_refused_rather_than_digested(tmp_path):
    """A digest of an empty directory is a perfectly valid sha256 that says nothing about a twin, and an empty
    or half-written twin is exactly the accident this is used to catch. The library call still answers, because
    a caller may legitimately ask; the COMMAND refuses, because its output would be read as evidence."""
    empty = tmp_path / "empty"; empty.mkdir()
    assert td.file_count(empty) == 0
    assert isinstance(td.digest(empty), str)
    run = subprocess.run([sys.executable, str(EVIDENCE / "twin_digest.py"), str(empty)],
                         capture_output=True, text=True)
    assert run.returncode == 1, run
    assert "REFUSED" in run.stderr and "empty tree" in run.stderr, run.stderr


def test_the_command_prints_the_file_count_beside_the_digest(tmp_path):
    """A digest alone cannot distinguish 'the twin' from 'four files of it'. The count travels with it."""
    base = _tree(tmp_path / "t", dict(BASE))
    run = subprocess.run([sys.executable, str(EVIDENCE / "twin_digest.py"), str(base)],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert td.digest(base) in run.stdout and f"{len(BASE)} files" in run.stdout, run.stdout


def test_a_missing_root_is_refused_not_silently_empty(tmp_path):
    """The failure that would read as 'no difference': digesting a path that is not there."""
    with pytest.raises(NotADirectoryError):
        td.digest(tmp_path / "does-not-exist")
