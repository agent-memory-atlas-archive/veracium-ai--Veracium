"""specs/0042 — ONE definition of "the digest of a derived twin", so two seats cannot compute two numbers.

Round 8g. The INV-7 transcript's claim that a tree's twin is byte-identical to the twin a committed run used
is what earns skipping an eighteen-minute harness re-run — and research found it was verifiable by ONE SEAT:
the run's twin lived in dev's scratch directory, its manifest is untracked, and the transcript's eight sha256s
are all per-arm RECORD digests, none of the twin. A check can RUN, FIRE and carry a negative control and still
be unusable in a two-seat protocol, because the second seat's agreement would be assent rather than
measurement. That is a property of the artifact's LOCATION, not of the check's logic.

The first remedy repeated the defect one turn tighter: the definition was written as a shell script under
`.claude/skills/`, which is in `.git/info/exclude` AND in pyproject's packaging exclusions — the one directory
a sealed package is guaranteed NOT to carry. A definition the reviewer must run cannot live where the seal
refuses to ship it. So it lives here, tracked, and travels with the package.

THE DEFINITION. sha256 over every file under the root, in sorted RELATIVE path order, hashing the path bytes,
then a NUL, then the file's bytes. The path is part of the hash, so a rename is a difference; the root is not,
so the same twin derived into two directories digests the same. Symlinks and empty directories are not part of
a derived twin and are not represented.

THE ROOT-INDEPENDENCE IS THE LOAD-BEARING HALF, and it is the half a matrix of refusal controls cannot reach
(research's reading, 2026-09-21). The reviewer proposed two controls and both were refusal-side — a byte
changed, a file renamed, each of which must MOVE the digest. **A definition that hashed ABSOLUTE paths passes
every refusal control there is** and still makes cross-seat agreement structurally impossible, because two
seats' twins are never in the same directory. The refusal half tests whether the instrument is SENSITIVE; only
the acceptance half tests whether it is USABLE BY TWO SEATS, which is the entire reason it exists. Third
instance of that asymmetry in one day, after the 27-versus-17 and 24-versus-15 splits in the rebinding matrix.

THE ROOT MUST BE THE DERIVATION'S OUTPUT DIRECTORY, AND GETTING THAT WRONG IS REFUSED RATHER THAN DIGESTED.
`derive(src, out)` writes `twin_manifest.json` to `out.parent`, so a root containing one is one level too high.
Research hit this on the first cross-seat run: the recipe's `<dir>/twin` gave 60 files and the digest above,
while calling the module API with `twin/src/veracium` as the output put the manifest inside the root they then
digested — 61 files, a completely different and perfectly plausible sha256. The file count printed beside the
digest is what made it visible, and a guard made of a careful reader noticing `61` is not a guard, so the
mis-scoped root is now a refusal.

REPRODUCING A TRANSCRIPT'S TWIN DIGEST FROM GIT ALONE, with no seat's scratch directory in the chain:

    git archive <the transcript's pin> | tar -x -C <dir>
    python <dir>/specs/evidence/0042/inv7_uninstrument.py <dir>/src/veracium <dir>/twin
    python <dir>/specs/evidence/0042/twin_digest.py <dir>/twin

What that establishes is that the twin DERIVABLE FROM THE PIN has that digest. That it equals the twin the
arms actually ran against rests on the derivation being deterministic from its source — which is tested by
deriving twice and diffing, not by reading a message.
"""
# Mutation-Matrix: tests/test_0042_twin_digest.py::test_the_digest_moves_for_every_kind_of_difference
from __future__ import annotations

import hashlib
import pathlib
import sys

# `inv7_uninstrument.derive(src, out)` writes its manifest to `out.parent`, BY CONSTRUCTION — never inside the
# twin. So a root containing one is not a derivation's output: the caller pointed at the parent, or passed a
# different `out` than the recipe's. That is a PROPERTY of the derivation, enforceable and probed below, not a
# convention about a filename.
MANIFEST_NAME = "twin_manifest.json"


class MisScopedTwinRoot(Exception):
    """The root handed in is not a twin: it contains the derivation's manifest, which is written beside one."""


def digest(root) -> str:
    """The tree digest of a derived twin. See the module docstring for the definition."""
    root = pathlib.Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory, so it is not a twin to digest")
    stray = [p.relative_to(root).as_posix() for p in root.rglob(MANIFEST_NAME) if p.is_file()]
    if stray:
        raise MisScopedTwinRoot(
            f"{root} contains {', '.join(stray)} — the derivation writes its manifest BESIDE the twin, never "
            f"inside it, so this root is one level too high or was produced by a different `out` than the "
            f"recipe's. Digesting it would answer a different question with a plausible-looking number. Pass "
            f"the directory given to `inv7_uninstrument.py` as its OUTPUT argument.")
    h = hashlib.sha256()
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    for rel in files:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update((root / rel).read_bytes())
    return h.hexdigest()


def file_count(root) -> int:
    """How many files the digest covered — printed beside it, because a digest of an EMPTY tree is a valid
    sha256 that says nothing, and an empty or half-derived twin is exactly the accident worth catching."""
    return sum(1 for p in pathlib.Path(root).rglob("*") if p.is_file())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: twin_digest.py <twin-root>", file=sys.stderr)
        raise SystemExit(2)
    target = pathlib.Path(sys.argv[1])
    try:
        n = file_count(target)
        value = digest(target)
    except (MisScopedTwinRoot, NotADirectoryError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if n == 0:
        print(f"REFUSED: {target} contains no files — a digest of an empty tree is a valid sha256 that says "
              f"nothing about a twin", file=sys.stderr)
        raise SystemExit(1)
    print(f"{value}  {n} files  {target}")
