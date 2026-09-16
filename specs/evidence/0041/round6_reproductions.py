#!/usr/bin/env python3
"""0041 round 6 — the verdict's executed claims, reproduced at the pin BEFORE any fix.

Pin `ead0bcc93301b42f7e2ae19f684c49bae8e9882e` (0041 v11). Finding 2 is a defect
in a NEGATIVE CONTROL this seat wrote one round after writing the rule that
negative controls are what make a check real. It is reproduced here first, with
the reviewer's own mutant, because a fix whose reproduction never failed is a
description of a fix.
"""
import ast
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PIN = "ead0bcc93301b42f7e2ae19f684c49bae8e9882e"
FAILURES = []


def claim(n, sentence):
    print(f"\n=== R{n} — {sentence}")


def result(ok, detail):
    print(("    REPRODUCED: " if ok else "    DID NOT REPRODUCE: ") + detail)
    if not ok:
        FAILURES.append(detail)


# ---------------------------------------------------------------- R1
claim(1, "the fixture-checker test runs the checker ONCE, on the original bytes, "
         "and never on the altered copy — so its 'negative control' controls nothing")
src = (ROOT / "tests" / "test_0041_transition_table.py").read_text()
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef)
          and n.name == "test_the_frozen_pre_restriction_store_matches_its_manifest")
runs = [n for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and getattr(n.func, "attr", "") == "run"
        and getattr(getattr(n.func, "value", None), "id", "") == "subprocess"]
result(len(runs) == 1,
       f"subprocess.run call sites in the test body: {len(runs)} — the checker is "
       f"invoked on the frozen bytes only; the altered copy is never given to it")

# ---------------------------------------------------------------- R2
claim(2, "and no assertion ABOUT THE ALTERED COPY reads a checker result — what "
         "that half asserts is a property of sha256, that a flipped byte changes a digest")
# The first version of this probe asked whether ANY assertion after the single
# subprocess call reads the result, and answered no-it-does-not-reproduce —
# because `ok.returncode == 0` does read it, for the ORIGINAL bytes. The verdict's
# claim is narrower and exact: it is the ALTERED-COPY half that reads nothing. A
# probe wider than the claim it is testing reports a false negative.
asserts = [a for a in ast.walk(fn) if isinstance(a, ast.Assert)]
altered = [ast.unparse(a.test) for a in asserts
           if "mutated" in ast.unparse(a.test) or "raw" in ast.unparse(a.test)]
reads_checker = [t for t in altered
                 if any(k in t for k in ("returncode", "stdout", "stderr"))]
result(altered and not reads_checker,
       f"{len(altered)} assertion(s) concern the altered bytes and {len(reads_checker)} "
       f"of them read a checker result: {altered}")

# ---------------------------------------------------------------- R3
claim(3, "the reviewer's mutant: force the subprocess result to unconditional "
         "success and the test still passes")
spec = importlib.util.spec_from_file_location(
    "tt6", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tt)


class _AlwaysOK:
    returncode = 0
    stdout = ""
    stderr = ""


real_run = subprocess.run
import tempfile
try:
    subprocess.run = lambda *a, **k: _AlwaysOK()
    with tempfile.TemporaryDirectory() as d:
        tt.test_the_frozen_pre_restriction_store_matches_its_manifest(pathlib.Path(d))
    survived, why = True, "the test PASSED with subprocess.run stubbed to always succeed"
except BaseException as e:                                   # noqa: BLE001
    survived, why = False, f"the test failed: {type(e).__name__}"
finally:
    subprocess.run = real_run
result(survived, why)

# ---------------------------------------------------------------- R4
claim(4, "the checker ITSELF is sound — the defect is the test, not the tool: "
         "exit 0 on the frozen bytes, exit 1 on altered bytes")
script = ROOT / "specs" / "evidence" / "0041" / "pre_restriction_fixture.py"
good = real_run([sys.executable, str(script), "--check"], capture_output=True, text=True)
with tempfile.TemporaryDirectory() as d:
    copy = pathlib.Path(d)
    for name in ("pre_restriction_fixture.py", "pre_restriction.sqlite",
                 "pre_restriction_manifest.json"):
        (copy / name).write_bytes((script.parent / name).read_bytes())
    b = bytearray((copy / "pre_restriction.sqlite").read_bytes())
    b[-1] ^= 0xFF
    (copy / "pre_restriction.sqlite").write_bytes(bytes(b))
    bad = real_run([sys.executable, str(copy / "pre_restriction_fixture.py"), "--check"],
                   capture_output=True, text=True)
result(good.returncode == 0 and bad.returncode == 1,
       f"frozen bytes -> exit {good.returncode}; one flipped byte -> exit "
       f"{bad.returncode} ({bad.stdout.strip().splitlines()[0] if bad.stdout.strip() else ''})")

print("\n" + "=" * 72)
if FAILURES:
    print(f"{len(FAILURES)} claim(s) DID NOT reproduce:")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print("finding 2 reproduced in full: the checker is sound and its test is not. "
      "No fix has been applied.")
