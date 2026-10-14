"""specs/0013 §4f / M-Q6 (ruled by accepted 0016 D2): the v2→v3 postcondition admits a raw key no current model
declares ONLY if it is in `RETIRED_EPISODE_KEYS`. That constant is bound here to its derivation: over every release tag,
the fields `Episode` and `Provenance` declared in that release's `src/veracium/schema.py`, minus the fields HEAD
declares. A field added to a release and later deleted must appear in the constant, and nothing else may.

Needs the repository's history (its tags). With no `.git` at all (a packaged tree) it skips, the cause named; with a
`.git` whose tags are missing it FAILS — a shallow or tagless clone would otherwise read as "nothing was ever retired"."""
from __future__ import annotations

import ast
import pathlib
import subprocess

import pytest

from veracium.schema import Episode, Provenance
from veracium.store.migration import RETIRED_EPISODE_KEYS

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def _fields(source: str) -> dict:
    """{class name: set of annotated field names} for Episode and Provenance in one release's schema.py."""
    out = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and node.name in ("Episode", "Provenance"):
            out[node.name] = {s.target.id for s in node.body
                              if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)}
    return out


def test_the_retired_keys_are_exactly_the_fields_releases_declared_and_head_does_not():
    if not (ROOT / ".git").exists():
        pytest.skip("no repository here (a packaged tree): the derivation reads every release tag's schema.py")
    tags = [t for t in _git("tag", "--list", "v*").split() if t]
    assert tags, ".git is present but carries no v* tag: a shallow or tagless clone cannot derive the retired keys"
    head = {"Episode": set(Episode.model_fields), "Provenance": set(Provenance.model_fields)}
    seen = {"Episode": set(), "Provenance": set()}
    for t in tags:
        got = _fields(_git("show", f"{t}:src/veracium/schema.py"))
        assert set(got) == {"Episode", "Provenance"}, f"{t}: schema.py does not define both classes ({sorted(got)})"
        for cls in seen:
            seen[cls] |= got[cls]
    derived = {(n,) for n in seen["Episode"] - head["Episode"]} | {("provenance", n)
                                                                  for n in seen["Provenance"] - head["Provenance"]}
    assert derived == set(RETIRED_EPISODE_KEYS), (len(tags), sorted(derived))
