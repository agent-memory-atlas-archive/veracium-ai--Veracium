#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0007_attestation_jobs.py::test_the_attestation_constraints_mutation_matrix
"""0007 §4d (I5, research's stage-1 read): ONE dependency set for every attestation row. pyproject's requirements are
lower bounds, so two jobs of one key could otherwise test different pydantic versions, and the record (whose provenance
fields are closed) would say nothing about it.

    $PY specs/attestation_constraints.py --write          # resolve [dev,mcp] for 3.14 on every platform (uv; network)
    $PY specs/attestation_constraints.py --check-current  # re-resolve and compare (network): run when regenerating,
                                                          # NEVER by pytest (it goes red on any upstream release)
    $PY specs/attestation_constraints.py --check          # offline: what the suite cell asserts

The offline rule: every direct requirement of the project, `[dev]` and `[mcp]` is pinned `==` in constraints.txt; each
pin satisfies pyproject's bound for it; every marker parses; and no name is pinned twice under one marker.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "specs" / "evidence" / "attestation" / "constraints.txt"
EXTRAS = ("dev", "mcp")
_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)\s*(?:;\s*(.+))?$")


def _canon(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def direct_requirements(pyproject=ROOT / "pyproject.toml") -> list:
    proj = tomllib.loads(pathlib.Path(pyproject).read_text())["project"]
    out = list(proj.get("dependencies", []))
    for extra in EXTRAS:
        out += proj.get("optional-dependencies", {}).get(extra, [])
    return out


def pins(text: str) -> list:
    """[(canonical name, version, marker or None)] from a constraints file; comments and blank lines skipped."""
    out = []
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].strip() if not raw.lstrip().startswith("#") else ""
        if not line:
            continue
        m = _PIN.match(line)
        if not m:
            raise ValueError(f"not an exact pin: {raw!r}")
        out.append((_canon(m.group(1)), m.group(2), m.group(3)))
    return out


def offline_problems(text=None, pyproject=ROOT / "pyproject.toml") -> list:
    from packaging.markers import InvalidMarker, Marker
    from packaging.requirements import Requirement
    from packaging.version import Version
    text = CONSTRAINTS.read_text() if text is None else text
    try:
        pinned = pins(text)
    except ValueError as exc:
        return [str(exc)]
    problems, seen = [], set()
    for name, version, marker in pinned:
        if marker is not None:
            try:
                Marker(marker)
            except InvalidMarker as exc:
                problems.append(f"{name}: the marker {marker!r} does not parse ({exc})")
        if (name, marker) in seen:
            problems.append(f"{name} is pinned twice under one marker ({marker!r})")
        seen.add((name, marker))
    by_name = {}
    for name, version, _ in pinned:
        by_name.setdefault(name, []).append(version)
    for spec in direct_requirements(pyproject):
        req = Requirement(spec)
        got = by_name.get(_canon(req.name))
        if not got:
            problems.append(f"{req.name} (a direct requirement: {spec!r}) is not pinned")
            continue
        for v in got:
            if not req.specifier.contains(Version(v), prereleases=True):
                problems.append(f"{req.name}=={v} does not satisfy pyproject's {spec!r}")
    return problems


def _compile(out_path) -> None:
    subprocess.run(["uv", "pip", "compile", str(ROOT / "pyproject.toml"), *[f"--extra={e}" for e in EXTRAS],
                    "--universal", "--python-version=3.14", "--no-header", "-q", "-o", str(out_path)],
                   cwd=str(ROOT), check=True)


def main(argv) -> int:
    if argv[1:] == ["--write"]:
        _compile(CONSTRAINTS)
        problems = offline_problems()
    elif argv[1:] == ["--check-current"]:
        with tempfile.TemporaryDirectory() as td:
            fresh = pathlib.Path(td) / "c.txt"
            _compile(fresh)
            problems = [] if fresh.read_text() == CONSTRAINTS.read_text() else [
                "constraints.txt differs from a fresh resolution: upstream moved, or pyproject changed; regenerate "
                "deliberately (--write) and re-attest"]
    elif argv[1:] == ["--check"]:
        problems = offline_problems()
    else:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
