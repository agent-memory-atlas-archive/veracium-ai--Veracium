"""0042's measurement trust boundary, EXECUTED (round 19): census code running in an arm can rewrite that arm's own INV-7
trace. One healthy arm through the REAL harness.run_arm, twice, over tests/test_0011_entitlement.py: HEAD's census.py as
is, and with four lines appended that replace the observer's `_record` with a no-op. The observer's wrappers look
`_record` up in the observer module's globals at call time, and census code runs in the arm's process after the plugin
has loaded, so it holds write access to the recording.

WHAT THIS SHOWS, AND WHAT IT DOES NOT (kept apart, as the disclosure requires): it RAN a census rewriting its own arm's
trace — here to zero records, which the four-arm comparison would read as DIVERGENT, i.e. LOUD. A SILENT forge — a
census that changes a decision and records the reference's value for it — needs only the same write access, and is
INFERRED, not built. The accepted design has always assumed census code changes behaviour and does not attack the
measurement; 0042 v11.3 proposes stating that as a trust boundary.

Usage: python specs/evidence/0042/trust_boundary_probe.py <scratch dir>   (writes nothing into the tree)"""
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"
FORGE = "\nimport sys as _s\n_o = _s.modules.get('inv7_observer')\nif _o is not None:\n    _o._record = lambda *a, **k: None\n"


def main(scratch: pathlib.Path) -> int:
    spec = importlib.util.spec_from_file_location("inv7_harness_probe", EVIDENCE / "inv7_harness.py")
    harness = importlib.util.module_from_spec(spec); spec.loader.exec_module(harness)
    repo = scratch / "repo"; (repo / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
    shim = repo / ".venv" / "bin" / "python"; shim.write_text(f"#!/bin/sh\nexec {sys.executable} \"$@\"\n"); shim.chmod(0o755)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "(no git)"
    print(f"trust boundary probe — veracium @ {head}, python {sys.version.split()[0]}")
    print(f"suite: tests/test_0011_entitlement.py, arm: healthy, through inv7_harness.run_arm")
    print(f"appended to census.py in the forging run:{FORGE.rstrip()}")
    got = {}
    for tag, extra in (("clean", ""), ("forging", FORGE)):
        src = scratch / f"src-{tag}" / "veracium"
        shutil.rmtree(src.parent, ignore_errors=True)
        shutil.copytree(ROOT / "src" / "veracium", src, ignore=shutil.ignore_patterns("__pycache__"))
        (src / "census.py").write_text((src / "census.py").read_text() + extra)
        os.environ["PYTHONPATH"] = str(src.parent)
        s = harness.run_arm(repo, "healthy", [str(ROOT / "tests" / "test_0011_entitlement.py")], scratch / f"out-{tag}",
                            EVIDENCE / "declaration.py")
        got[tag] = s
        print(f"  {tag:8s} records={s.get('records')}  pytest: {s.get('pytest_result_line')}")
    rewrote = got["clean"].get("records", 0) > 0 and got["forging"].get("records") == 0
    same_tests = got["clean"].get("pytest_exit") == got["forging"].get("pytest_exit") == 0
    print(f"RESULT: the census rewrote its own arm's trace: {rewrote}; the arm's tests still passed: {same_tests}")
    return 0 if rewrote and same_tests else 1


if __name__ == "__main__":
    sys.exit(main(pathlib.Path(sys.argv[1])))
