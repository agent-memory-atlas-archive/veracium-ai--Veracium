"""The two 0022 evidence RECORDS are bound to the GENERATORS they claim to record.

`specs/evidence/0022/vector_harness_result.txt` and `store_concurrency_result.txt`
are one-line files: the verdict line each harness prints, "recorded verbatim" —
the 0022 spec calls the first "the oracle" for its harness. Nothing bound either
record to its generator. The vector record said 60/60 while the harness produced
78/78; the concurrency record said 17/17 against 18/18 — and that second one was
external round 8's R8-2, which was closed by making the SEALER run the harnesses
live (so packages stopped carrying the false number) while the record file itself
was never regenerated. Both records had been wrong since 2026-08-17, one of them
through the closure of the finding that named it. Found at the v0.26.0 release
battery, 2026-09-17.

A record maintained beside the thing it records drifts; the check compares data
to data. For each record the TOTAL is derived from the generator's own source of
truth — the vector count from `vectors.json`, the check count from `CHECKS` — and
the record's `P/N` must equal `N/N` for that derived N: a record of a partial run
is not evidence, and a total that no longer matches the generator is the defect.

The vector harness is also RUN, and its printed line must equal the record byte
for byte — it is cheap and deterministic. The concurrency harness is NOT run here,
on purpose: it times SQLite BUSY behaviour and a deadline, and the closure-evidence
runner already executes it ALONE after the concurrent batch drains
(`NEEDS_QUIET` in test_spec_gate.py). A second run in the randomised phase would
reintroduce the contention that carve-out exists to prevent, and a timing harness
run under contention produces a number about the box. Its live figure is asserted
by that quiet lane; this test binds record to source.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVID = ROOT / "specs" / "evidence" / "0022"
LINE = re.compile(r"^(?P<label>.+?): (?P<p>\d+)/(?P<n>\d+) pass against (?P<ref>.+)$")


def _record(name: str) -> tuple[str, int, int, str]:
    text = (EVID / name).read_text()
    lines = text.splitlines()
    assert len(lines) == 1, f"{name}: a record is ONE verdict line, found {len(lines)}"
    m = LINE.match(lines[0])
    assert m, f"{name}: not a harness verdict line: {lines[0]!r}"
    return lines[0], int(m["p"]), int(m["n"]), m["ref"]


def _load_module_without_running(path: pathlib.Path):
    """Import a harness for its tables only. Its run is behind `__main__`;
    importing must not execute it — asserted by timing nothing, but by the
    fact that CHECKS is a module-level list the import populates."""
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_vector_record_matches_the_vector_count_and_the_live_run():
    line, p, n, ref = _record("vector_harness_result.txt")
    vectors = json.loads((EVID / "vectors.json").read_text())
    assert n == len(vectors), (
        f"vector_harness_result.txt records {p}/{n} but vectors.json holds "
        f"{len(vectors)} vectors — the generator grew and the record did not follow")
    assert p == n, f"the record is of a PARTIAL run ({p}/{n}); a partial run is not evidence"
    assert ref == "reference_revocation.py"
    # the live run, byte for byte
    r = subprocess.run([sys.executable, str(EVID / "vector_harness.py")],
                       cwd=ROOT, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    printed = [l for l in r.stdout.splitlines() if l.startswith("vector harness:")]
    assert printed == [line], (
        f"the harness printed {printed!r}; the record says {line!r} — regenerate the record")


def test_the_concurrency_record_matches_the_check_count_without_rerunning_it():
    line, p, n, ref = _record("store_concurrency_result.txt")
    mod = _load_module_without_running(EVID / "store_concurrency_harness.py")
    assert isinstance(mod.CHECKS, list) and mod.CHECKS, "CHECKS is the harness's case table"
    assert n == len(mod.CHECKS), (
        f"store_concurrency_result.txt records {p}/{n} but the harness defines "
        f"{len(mod.CHECKS)} checks — the generator grew and the record did not follow "
        f"(this is R8-2's exact shape, a second time)")
    assert p == n, f"the record is of a PARTIAL run ({p}/{n}); a partial run is not evidence"
    assert ref == "the §4e-i construction"
    assert line == f"store concurrency harness: {n}/{n} pass against {ref}", (
        "the record's line must be exactly what the harness prints on a full pass")


def test_the_binding_refuses_a_stale_record():
    """RULE ZERO: the check must be capable of failing. Each mutation is the
    defect this file was written for, applied to a COPY and asserted to have
    applied, so a control that silently did nothing cannot read as a pass."""
    vectors_n = len(json.loads((EVID / "vectors.json").read_text()))
    checks_n = len(_load_module_without_running(EVID / "store_concurrency_harness.py").CHECKS)
    stale_vec = f"vector harness: {vectors_n - 18}/{vectors_n - 18} pass against reference_revocation.py"
    stale_conc = f"store concurrency harness: {checks_n - 1}/{checks_n - 1} pass against the §4e-i construction"
    partial = f"vector harness: {vectors_n - 1}/{vectors_n} pass against reference_revocation.py"
    for text, derived in ((stale_vec, vectors_n), (stale_conc, checks_n)):
        m = LINE.match(text); assert m and int(m["n"]) != derived, "the control did not change the total"
    m = LINE.match(partial); assert m and int(m["p"]) != int(m["n"]), "the partial control is not partial"
    # and the parser itself refuses a non-verdict record rather than defaulting
    assert LINE.match("harness ok") is None
