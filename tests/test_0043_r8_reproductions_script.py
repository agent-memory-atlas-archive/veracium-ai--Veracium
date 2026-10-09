"""specs/0043 — the round-8 verdict's reproduction (R8-01), measured at the round-8 pin 7350daf before any fix, is
HISTORICAL evidence of that instrument: beside any other instrument the script refuses by name with its recipe, and its
bytes are pinned (an edit to a measurement is a re-measurement). Its execution on the round-8 pin's tree runs at every
package stage."""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "specs" / "evidence" / "0043" / "round8_reproductions.py"
MEASURED = "e7527a3f91ea3b5b9185649429ab1b2c049aa2a13847df57e3c333764d5b86b1"     # measured on an archive of 7350daf: 6 of 6 REPRODUCED, 3 of 3 controls


def test_the_round8_reproductions_beside_another_instrument_refuse_by_name_with_the_recipe():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=ROOT,
                       env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, timeout=300)
    assert r.returncode == 2 and r.stdout.startswith("REFUSED: this script reproduces the round-8 pin's instrument (7350daf8cc4d)"), r.stdout[:300]
    assert "copy this file into its specs/evidence/0043/" in r.stdout and not r.stderr


def test_the_round8_reproductions_are_the_measured_bytes():
    got = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert got == MEASURED, (f"round8_reproductions.py changed. It is a measurement of the round-8 pin's instrument: re-run it "
                             f"there (an archive of 7350daf, this file copied into specs/evidence/0043/, PYTHONPATH=src), confirm "
                             f"6 of 6 and 3 of 3, then move this pin to {got} in the same commit.")
