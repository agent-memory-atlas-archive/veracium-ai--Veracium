#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0007_attestation_writer.py::test_the_attestation_writer_mutation_matrix
"""0007 §4g.6 4d (and v19): the attestation-record WRITER — the one way a record reaches `sqlite_runtimes.json`.

An attestation record states that the FULL attestation suite passed in this repository's CI on one build. The record's
KEY is never taken from the job's input: it is THIS process's `sv.attestation_identity()`, through production's one
canonicaliser (`sv.options_digest`, `sv.canonical_platform`). The job supplies only its evidence (the suite's result
digest and the sixteen confinement results) and its provenance (route, runner image, run, job, commit).

Writing, in order (research's stage-1 read of the writer, f5aaa289 §18, and W1–W7):
  1. the record is built and validated by PRODUCTION's own `attestation_record_problems` (one validator both
     directions, W2); a fixture mark (the all-zeros commit, a `fixture-` run id) is refused outright (W4);
  2. answerability, ALWAYS: git present, inside a repository, not shallow, the record's ONE commit (W1) full hex in the
     repository's object format, and that commit IS this checkout's HEAD (BLOCKING 1: never a claimed commit);
  3. per existing record of the SAME full key (`sv.attestation_key`, never a reconstruction, W7): a FUTURE revision
     refuses (S75); an OLDER revision is superseded (10(a)'s carve-out); a CURRENT one goes through v19's order —
     the same commit (equal evidence idempotent, else refused), then `merge-base --is-ancestor` (0 replaces; 1
     refuses "not an ancestor", the reverse call naming the direction; anything else "unanswerable");
  4. records of other keys are kept unchanged (merge, never replace, W6); the prospective artifact must pass
     `attestation_artifact_problems`, and must read back attested for the written key (W2's round trip);
  5. published atomically: a temporary in the same directory, then `os.replace`; the top level stays closed.
Git runs with its environment PINNED (BLOCKING 2): the variables that point git at another repository or object store
are scrubbed, and system and global configuration are off.

    $PY specs/attestation_writer.py <job-input.json>     # {"result_digest", "confinement", "provenance"}
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from veracium.store import schema_version as sv  # noqa: E402

GIT_SCRUBBED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                "GIT_INDEX_FILE", "GIT_CEILING_DIRECTORIES")
FIXTURE_COMMIT = "0" * 40
_HEX = {"sha1": re.compile(r"[0-9a-f]{40}"), "sha256": re.compile(r"[0-9a-f]{64}")}


class AttestationRefused(Exception):
    """The writer refuses; nothing was written. The message names why."""


def git_env(base=None) -> dict:
    """Git's environment, PINNED (BLOCKING 2): no inherited variable can answer "shallow?" or "ancestor?" for another
    repository or object store, and no developer's configuration changes an answer."""
    env = {k: v for k, v in (os.environ if base is None else base).items() if k not in GIT_SCRUBBED}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def run_git(args, repo) -> tuple:
    """(exit code, stripped stdout) of `git <args>` in `repo`; 127 when git itself cannot run."""
    try:
        p = subprocess.run(["git", *args], cwd=str(repo), env=git_env(), capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return 127, ""
    return p.returncode, p.stdout.strip()


def build_record(result_digest, confinement, provenance) -> dict:
    """The record for THIS build: its key from `sv.attestation_identity()` (W3), the job's evidence and provenance."""
    ident = sv.attestation_identity()
    if sv.attestation_key(ident) is None:
        raise AttestationRefused(f"this build's attestation key has an unreadable field "
                                 f"({[k for k in sv.KEY_FIELDS if ident[k] is None]}); it can never be attested")
    return {**{k: ident[k] for k in sv.KEY_FIELDS}, "manifest_algorithm": sv.MANIFEST_ALGORITHM,
            "schema_version": sv.SCHEMA_VERSION, "result_digest": result_digest, "confinement": confinement,
            "provenance": sorted(provenance, key=lambda j: (j.get("route"), j.get("runner_image"), j.get("job_id")))
            if isinstance(provenance, list) else provenance}


def _check_record(rec) -> str:
    problems = sv.attestation_record_problems(rec)
    if problems:
        raise AttestationRefused(f"the record is malformed: {problems[0]}")
    for j in rec["provenance"]:
        if j["commit"] == FIXTURE_COMMIT or j["run_id"].startswith("fixture-"):
            raise AttestationRefused("the record carries a fixture mark (the all-zeros commit or a fixture- run id): "
                                     "fixture records are tests-only and never written")
    return sv.record_commit(rec)


def _answerable(commit, repo, git) -> None:
    """v19 step 2, plus BLOCKING 1: the record's commit must be this checkout's HEAD."""
    rc, _ = git(["--version"], repo)
    if rc != 0:
        raise AttestationRefused("unanswerable: git is not available")
    rc, out = git(["rev-parse", "--is-inside-work-tree"], repo)
    if rc != 0 or out != "true":
        raise AttestationRefused("unanswerable: the writer is not inside a git repository")
    rc, out = git(["rev-parse", "--is-shallow-repository"], repo)
    if rc != 0 or out != "false":
        raise AttestationRefused("unanswerable: the repository is shallow (or its shallowness cannot be read), so "
                                 "--is-ancestor's exit 1 would be ambiguous")
    rc, fmt = git(["rev-parse", "--show-object-format"], repo)
    if rc != 0 or fmt not in _HEX:
        raise AttestationRefused(f"unanswerable: the repository's object format is unreadable ({fmt!r})")
    if not _HEX[fmt].fullmatch(commit):
        raise AttestationRefused(f"unanswerable: the record's commit {commit!r} is not a full {fmt} id")
    rc, head = git(["rev-parse", "HEAD"], repo)
    if rc != 0 or head != commit:
        raise AttestationRefused(f"the record's commit {commit} is not this checkout's HEAD {head or '(unreadable)'}: "
                                 f"a record attests the commit its suite ran at, never a claimed one")
    return fmt


def _ordered(existing, new, new_commit, repo, git, fmt) -> str:
    """v19's order for an existing CURRENT record of the same full key: "idempotent", "replace", or a refusal."""
    old_commit = sv.record_commit(existing)
    if old_commit is None or not _HEX[fmt].fullmatch(old_commit):
        raise AttestationRefused(f"unanswerable: the existing record's commit {old_commit!r} is not a full {fmt} id")
    evidence = lambda r: (r["result_digest"], json.dumps(r["confinement"], sort_keys=True))   # noqa: E731
    if old_commit == new_commit:                   # before --is-ancestor: a commit is its own ancestor
        if evidence(existing) == evidence(new):
            return "idempotent"
        raise AttestationRefused(f"the same commit {new_commit} recorded different evidence for one key: the key "
                                 f"does not identify the build")
    rc, _ = git(["merge-base", "--is-ancestor", old_commit, new_commit], repo)
    if rc == 0:
        return "replace"
    if rc == 1:
        rrc, _ = git(["merge-base", "--is-ancestor", new_commit, old_commit], repo)
        if rrc == 0:
            raise AttestationRefused(f"not an ancestor: the writing commit {new_commit} is OLDER than the recorded "
                                     f"{old_commit}")
        if rrc == 1:
            raise AttestationRefused(f"not an ancestor: {old_commit} and {new_commit} are on sibling branches or the "
                                     f"history was rewritten")
        raise AttestationRefused(f"unanswerable: the reverse --is-ancestor exited {rrc}")
    raise AttestationRefused(f"unanswerable: --is-ancestor exited {rc}")


def merged(records, new, *, repo=ROOT, git=run_git) -> tuple:
    """(the prospective record list, "written" | "replaced" | "idempotent"). Raises AttestationRefused."""
    commit = _check_record(new)
    fmt = _answerable(commit, repo, git)
    key = sv.attestation_key(new)
    out, outcome = [], "written"
    for r in records:
        if not isinstance(r, dict) or sv.attestation_key(r) != key:
            out.append(r)                             # another key: kept, byte for byte (W6)
            continue
        rev = sv.attestation_revision(r)
        if rev == "future":
            raise AttestationRefused("refusing to overwrite a NEWER revision's record of this key: this checkout is "
                                     "older than the artifact (S75)")
        if rev == "superseded":
            continue                                  # 10(a)'s carve-out, on the FULL key only (W7)
        if rev == "malformed":
            out.append(r)                             # left for the artifact check below to refuse
            continue
        decision = _ordered(r, new, commit, repo, git, fmt)
        if decision == "idempotent":
            return list(records), "idempotent"
        outcome = "replaced"                          # this current record is replaced by the new one
    out.append(new)
    problems = sv.attestation_artifact_problems(out)
    if problems:
        raise AttestationRefused(f"the prospective artifact would be poisoned: {problems[0]}")
    if not sv.attested_key(key, out):
        raise AttestationRefused("the written record would not read back attested (round trip)")
    return out, outcome


def write(new, *, path=None, repo=ROOT, git=run_git) -> str:
    """Merge `new` into the artifact at `path` (default: the package's) and publish it atomically."""
    path = pathlib.Path(sv.RUNTIMES if path is None else path)
    data = json.loads(path.read_text()) if path.exists() else {"attestations": []}
    if not isinstance(data, dict) or set(data) - sv.ARTIFACT_KEYS or not isinstance(data.get("attestations"), list):
        raise AttestationRefused(f"the existing artifact's top level is not within {sorted(sv.ARTIFACT_KEYS)}")
    records, outcome = merged(data["attestations"], new, repo=repo, git=git)
    if outcome == "idempotent":
        return outcome
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"attestations": records}, indent=2) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return outcome


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    job = json.loads(pathlib.Path(argv[1]).read_text())
    try:
        rec = build_record(job.get("result_digest"), job.get("confinement"), job.get("provenance"))
        print(write(rec))
    except AttestationRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
