#!/usr/bin/env python3
"""0041 round 6 — the verdict's executed claim, FROZEN as it stood at the pin.

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


PIN_FILE_SHA16 = '16d31ae15d347ead'   # tests/test_0041_transition_table.py at the pin

# THE BODY AS IT STOOD AT THE PIN, frozen rather than re-read.
#
# The first version of this script read the test from the tree. The moment the
# test was fixed it stopped claiming "here is the defect" and began claiming
# "here is the absence of the defect" — and FAILED, because the claims are
# written as reproductions. The round-7 throwaway verification caught it in the
# sealed bytes, before the package reached the outbox.
#
# This is the SECOND time this exact inversion has happened, in consecutive
# rounds, in scripts written by the same seat. Round 5's reproduction was frozen
# for precisely this reason and round 6's was then written to re-read the tree.
# A reproduction that reads live state is not a reproduction; it is a claim
# about whatever the tree happens to say today.
#
# Frozen rather than fetched with `git show` for the second reason round 5 gives:
# that would make the round's own reproduction one more artifact a packaged tree
# cannot run.
PIN_BODY = 'def f(tmp_path):\n    """THE MUTATION MATRIX for `specs/evidence/0041/pre_restriction_fixture.py`.\n\n    The fixture is only evidence while its bytes are the frozen ones: a silent\n    regeneration AFTER 0041\'s write-path closure lands would produce a store the\n    closure ALLOWED, which is the opposite of what a pre-restriction fixture is\n    for, and nothing else in the tree would notice.\n\n    So the checker is run, both ways. `--check` must pass on the real bytes, and\n    it must refuse a single flipped byte — a digest check that cannot be made to\n    fail is the unfailable-check class, and this one guards an artifact whose\n    whole value is that it has not changed."""\n    import subprocess\n    import sys\n\n    script = _FROZEN / "pre_restriction_fixture.py"\n\n    ok = subprocess.run([sys.executable, str(script), "--check"],\n                        capture_output=True, text=True)\n    assert ok.returncode == 0, f"pre_restriction_fixture.py --check refused the frozen bytes: {ok.stdout}{ok.stderr}"\n\n    # NEGATIVE CONTROL: one byte, and the checker must say so\n    man = _strict_json((_FROZEN / "pre_restriction_manifest.json").read_text())\n    raw = bytearray((_FROZEN / "pre_restriction.sqlite").read_bytes())\n    assert hashlib.sha256(bytes(raw)).hexdigest() == man["sha256"]\n    assert len(raw) == man["bytes"]\n    raw[-1] ^= 0xFF\n    mutated = tmp_path / "mutated.sqlite"\n    mutated.write_bytes(bytes(raw))\n    assert hashlib.sha256(mutated.read_bytes()).hexdigest() != man["sha256"], (\n        "a flipped byte must move the digest the checker compares")\n'

EXISTENCE = ("hasattr", "getattr", "callable")


def _calls(src, attr):
    tree = ast.parse(src)
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and getattr(n.func, "attr", "") == attr]


# ---------------------------------------------------------------- R1
claim(1, "at the pin the fixture-checker test ran the checker ONCE, on the "
         "original bytes, and never on the altered copy")
runs = _calls(PIN_BODY, "run")
result(len(runs) == 1,
       f"subprocess.run call sites in the pin-era body: {len(runs)} — the checker is "
       f"invoked on the frozen bytes only; the altered copy is never given to it")

# ---------------------------------------------------------------- R2
claim(2, "and no assertion about the altered copy read a checker result — that "
         "half asserted a property of sha256, that a flipped byte changes a digest")
_fn = ast.parse(PIN_BODY).body[0]
_alt = [ast.unparse(a.test) for a in ast.walk(_fn) if isinstance(a, ast.Assert)
        and ("mutated" in ast.unparse(a.test) or "raw" in ast.unparse(a.test))]
_reads = [x for x in _alt if any(k in x for k in ("returncode", "stdout", "stderr"))]
result(bool(_alt) and not _reads,
       f"{len(_alt)} assertion(s) concerned the altered bytes and {len(_reads)} read a "
       f"checker result: {_alt}")

# ---------------------------------------------------------------- R3
claim(3, "so the reviewer's mutant survived it: forcing the subprocess result to "
         "unconditional success left the pin-era body passing")
result("returncode == 0" in PIN_BODY and not _reads,
       "the only assertion reading the checker's result is `ok.returncode == 0`, "
       "on the ORIGINAL bytes — an always-succeeding checker satisfies it and "
       "nothing else in the body can refuse")

# ---------------------------------------------------------------- R4
claim(4, "and the FIX is in the tree: the checker is now run on altered bytes "
         "and its refusal read from its own exit code")
live = (ROOT / "tests" / "test_0041_transition_table.py").read_text()
now = live[live.index("def test_the_frozen_pre_restriction_store_matches_its_manifest"):
           live.index("def test_the_frozen_store_carries_every_pre_restriction_shape")]
calls = now.count("subprocess.run(")
reads_altered = "bad.returncode == 1" in now
result(calls == 2 and reads_altered,
       f"the tree's body makes {calls} checker call(s) and asserts the altered "
       f"copy's exit code: {reads_altered}")

print("\n" + "=" * 72)
if FAILURES:
    print(f"{len(FAILURES)} claim(s) DID NOT reproduce:")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print("finding 2 reproduced in full from the FROZEN pin-era body: the checker was "
      "sound and its test was theatre. R4 confirms the repair is in the tree — "
      "which is why R1-R3 are quotations and not a re-read: a reproduction that "
      "reads live state inverts the moment the defect is fixed, and this script's "
      "first version did exactly that, in the round after round 5's did.")
