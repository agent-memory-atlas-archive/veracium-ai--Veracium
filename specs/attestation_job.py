#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0007_attestation_jobs.py::test_the_attestation_job_mutation_matrix
"""0007 §4d (I5): ONE attestation job, run in the matrix row's own interpreter. It decides a CLOSED outcome and writes
it, with this build's record when there is one, to `--out`.

    $PY specs/attestation_job.py --route R --runner-image I --expect-prefix P --run-id N --job-id K --out F

In order, stopping at the first step that decides (research's stage-1 read of I5, BLOCKING 1–4):
  0. the job is non-root (else **wrong-job-state**, red: INV-SA6's job-state assertion), and the row is the route it
     claims: Python >= 3.14, and realpath(sys.base_prefix) lies under the row's declared
     `--expect-prefix`; else **wrong-interpreter** (red);
  1. §4b verification, `sv.runtime_status()`: `refused` is **refused**, with the failing step. That is a census row, not a
     record, and the job exits 0 ("a job whose build fails verification records that result, it does not fail
     the matrix");
  2. `migrations_0013.py --check-evidence`: nonzero is **evidence-mismatch** (red; 0013 §5f.3, "a FAILED attestation
     job, named, never a record");
  3. the suite, by the one committed rule (`attestation_suite.py`), run ONCE in pytest's own order with
     pytest-randomly disabled, into a JUnit file; the JUnit must have run exactly the rule's modules, else
     **suite-mismatch** (red);
  4. skips, FROM THE SAME JUNIT: an xfail is never a skip; one mapping to no inventory entry is **unmapped-skip**
     (red);
  5. any failure or error is **failed-tests** (red), whether or not a job:runs condition also fired (exclusion means
     "not an input", never "not a failure"). Its digest is still written, as a member of its key's group;
  5b. a skip mapping to a `job:runs` entry is **excluded**, naming the entry: not an input and not a disagreement, so
     exit 0;
  6. otherwise **evidence**, unless the record would be malformed (a confinement probe failing on this build is
     **confinement-failed**, red, and never a record): the result digest over the sorted (node id, outcome) pairs, the sixteen confinement
     probes run live, and the record built HERE, in this process, by `attestation_writer.build_record` (the key is
     this build's own, W3).

Provenance `job_id` is the row's MATRIX INDEX within its run (`strategy.job-index`), not GitHub's numeric job id: unique
within one run, which is all §4d's ordering needs. Look a job up by run id and matrix index, never as a GitHub job id.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SPECS))

import attestation_suite  # noqa: E402
import skip_inventory  # noqa: E402

OUTCOME_EXIT = {"evidence": 0, "refused": 0, "excluded": 0,
                "wrong-interpreter": 1, "wrong-job-state": 1, "evidence-mismatch": 1, "suite-mismatch": 1, "unmapped-skip": 1,
                "failed-tests": 1, "confinement-failed": 1}
"""The CLOSED outcome set, and each one's exit code. (`unavailable`, an interpreter that could not be installed, is
the workflow's: no job script ran, so the aggregator names the row from the workflow's matrix.)"""

PYTEST_ARGS = ("-p", "no:randomly", "-p", "no:cacheprovider", "-q")
"""BLOCKING 1: ONE ordering source. pytest-randomly is in the dev extra and reorders and reseeds per test, so two jobs
of one key could disagree on an order-dependent outcome."""


class Decided(Exception):
    def __init__(self, outcome, reason, **extra):
        assert outcome in OUTCOME_EXIT, outcome
        super().__init__(f"{outcome}: {reason}")
        self.outcome, self.reason, self.extra = outcome, reason, extra


def interpreter_problem(expect_prefix, base_prefix=None, version_info=None) -> str | None:
    """Step 0, BLOCKING 3: None, or why this interpreter is not the row's. The job runs in a venv, so the BASE install
    is what is compared: `sys.base_prefix`, resolved. (realpath(sys.executable) sees through a POSIX venv's symlink but
    not a Windows venv's copied python.exe.)"""
    version_info = sys.version_info if version_info is None else version_info
    if tuple(version_info[:2]) < (3, 14):
        return f"Python {version_info[0]}.{version_info[1]} is below the floor 3.14"
    real = os.path.realpath(sys.base_prefix if base_prefix is None else base_prefix)
    prefix = os.path.realpath(expect_prefix)
    try:
        under = os.path.commonpath([real, prefix]) == prefix
    except ValueError:                                     # different drives (Windows): not under
        under = False
    if not under:
        return f"the interpreter's base install {real} is not under the row's declared location {prefix}"
    return None


def junit_cases(junit_path) -> list:
    """[(node id, outcome, skip message or None)], outcome one of passed/failed/error/skipped/xfailed."""
    out = []
    for case in ET.parse(junit_path).getroot().iter("testcase"):
        parts = (case.get("classname") or "").split(".")
        mod = next(i for i, p in enumerate(parts) if p.startswith("test_"))
        nodeid = "::".join(["/".join(parts[:mod + 1]) + ".py", *parts[mod + 1:], case.get("name") or ""])
        kids = {c.tag: c for c in case}
        if "error" in kids:
            out.append((nodeid, "error", None))
        elif "failure" in kids:
            out.append((nodeid, "failed", None))
        elif "skipped" in kids:
            sk = kids["skipped"]
            if sk.get("type") == "pytest.xfail":
                out.append((nodeid, "xfailed", None))          # BLOCKING 4: an xfail is not a skip
            else:
                out.append((nodeid, "skipped", " ".join(filter(None, (sk.get("message"), sk.text)))))
        else:
            out.append((nodeid, "passed", None))
    return out


def result_digest(cases) -> str:
    """sha256 over the sorted (node id, outcome) pairs, without timings (§4d)."""
    pairs = sorted((n, o) for n, o, _ in cases)
    return hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode()).hexdigest()


def classify_skips(cases):
    """(job:runs entries that fired, skips that match no entry), from the JUnit's own skip messages."""
    fired, unmapped = [], []
    for nodeid, outcome, message in cases:
        if outcome != "skipped":
            continue
        entry = skip_inventory.entry_for(nodeid.split("::")[0], message or "")
        if entry is None:
            unmapped.append(f"{nodeid}: {(message or '')[:120]}")
        elif skip_inventory.attestation_class(entry) == "job:runs":
            fired.append(f"{entry[0]} [{entry[2]}] at {nodeid}")
    return sorted(set(fired)), unmapped


def _check_evidence() -> tuple:
    p = subprocess.run([sys.executable, str(SPECS / "migrations_0013.py"), "--check-evidence"], cwd=str(ROOT),
                       env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)[-2000:]


def _run_suite(junit) -> int:
    modules = attestation_suite.suite(ROOT)
    return subprocess.run([sys.executable, "-m", "pytest", *PYTEST_ARGS, f"--junitxml={junit}", *modules],
                          cwd=str(ROOT)).returncode


def _head() -> str:
    import attestation_writer as aw
    return aw.run_git(["rev-parse", "HEAD"], ROOT)[1]


def job_state_problem(euid=None) -> str | None:
    """INV-SA6's job-state assertion (§4d job:runs): the attestation job runs NON-root, so the geteuid entries cannot
    fire. A root job would skip the read-only-store tests and attest a suite it did not run, and two jobs of one key
    (one root, one not) would read as "the key does not identify the build". run_row.sh refuses root too; this is
    the check a matrix can mutate."""
    euid = (os.geteuid() if hasattr(os, "geteuid") else None) if euid is None else euid
    return "the attestation job is running as root (uid 0): it must run as a non-root user" if euid == 0 else None


def decide(args, *, runtime_status=None, check_evidence=_check_evidence, run_suite=_run_suite, probes=None,
           head=_head, euid=None) -> dict:
    """The job's closed result. Every seam is injectable, so each outcome is a cell."""
    from veracium.store import schema_version as sv
    import attestation_writer as aw
    st = (sv.runtime_status if runtime_status is None else runtime_status)()
    result = {"outcome": None, "reason": "", "route": args.route, "runner_image": args.runner_image,
              "sqlite_version": st.sqlite_version, "source_id": st.source_id, "status": st.status,
              "key": None, "result_digest": None, "excluded_entries": [], "record": None}
    try:
        bad = interpreter_problem(args.expect_prefix)
        if bad:
            raise Decided("wrong-interpreter", bad)
        bad = job_state_problem(euid)
        if bad:
            raise Decided("wrong-job-state", bad)
        result["key"] = list(sv.attestation_key(sv.attestation_identity()) or []) or None
        if st.status == "refused":
            raise Decided("refused", st.reason or "refused")
        rc, tail = check_evidence()
        if rc != 0:
            raise Decided("evidence-mismatch", f"--check-evidence exited {rc}: {tail.strip()[-400:]}")
        with tempfile.TemporaryDirectory() as td:
            junit = pathlib.Path(td) / "junit.xml"
            run_suite(junit)
            if not junit.exists():
                raise Decided("suite-mismatch", "the suite wrote no JUnit file")
            mismatch = attestation_suite.nodes_problems(junit, ROOT)
            if mismatch:
                raise Decided("suite-mismatch", "; ".join(mismatch))
            cases = junit_cases(junit)
        result["result_digest"] = result_digest(cases)
        fired, unmapped = classify_skips(cases)
        if unmapped:
            raise Decided("unmapped-skip", f"{len(unmapped)} skip(s) match no inventory entry: " + "; ".join(unmapped))
        result["excluded_entries"] = fired
        # Failures FIRST (research's stage 2 on 84c512b): exclusion means "not an input", never "not a failure". A
        # job whose job:runs condition fired AND whose suite fails is red, and still names the fired entries.
        failing = [n for n, o, _ in cases if o in ("failed", "error")]
        if failing:
            raise Decided("failed-tests", f"{len(failing)} failing: " + ", ".join(failing[:20])
                          + (f" (and {len(fired)} job:runs condition(s) fired)" if fired else ""))
        if fired:
            raise Decided("excluded", f"{len(fired)} job:runs condition(s) fired: " + "; ".join(fired))
        live = (_live_probes if probes is None else probes)()
        commit = head()
        record = aw.build_record(result["result_digest"], live,
                                 [{"route": args.route, "runner_image": args.runner_image, "run_id": str(args.run_id),
                                   "job_id": int(args.job_id), "commit": commit}])
        problems = sv.attestation_record_problems(record)
        if problems:                                       # a failing confinement probe: never a record, and not a
            raise Decided("confinement-failed", f"the record would be malformed: {problems[0]}")   # failed TEST
        result.update(outcome="evidence", reason="", record=record)
    except Decided as d:
        result.update(outcome=d.outcome, reason=d.reason)
    return result


def _live_probes() -> dict:
    import migrations_0013
    return migrations_0013.authorizer_probes()


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    for a in ("--route", "--runner-image", "--expect-prefix", "--run-id", "--out"):
        ap.add_argument(a, required=True)
    ap.add_argument("--job-id", required=True, type=int)
    args = ap.parse_args(argv[1:])
    result = decide(args)
    pathlib.Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(f"{result['outcome']}: {result['reason']}" if result["reason"] else result["outcome"])
    return OUTCOME_EXIT[result["outcome"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
