"""specs/0043 — the round-7 verdict's reproduction (R7-01), measured at the round-7 pin f9975b9 before any fix, is
HISTORICAL evidence of that instrument: beside any other instrument the script refuses by name with its recipe, and its
bytes are pinned (an edit to a measurement is a re-measurement). Its execution on the round-7 pin's tree runs at every
package stage."""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "specs" / "evidence" / "0043" / "round7_reproductions.py"
MEASURED = "ce7f80a5e416511bd23609252735e00f446414a29a090d97519cd044c1051b33"     # measured on an archive of f9975b9: 4 of 4 REPRODUCED, 2 of 2 controls


def test_the_round7_reproductions_beside_another_instrument_refuse_by_name_with_the_recipe():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=ROOT,
                       env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, timeout=300)
    assert r.returncode == 2 and r.stdout.startswith("REFUSED: this script reproduces the round-7 pin's instrument (f9975b95a677)"), r.stdout[:300]
    assert "copy this file into its specs/evidence/0043/" in r.stdout and not r.stderr


def test_the_round7_reproductions_are_the_measured_bytes():
    got = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert got == MEASURED, (f"round7_reproductions.py changed. It is a measurement of the round-7 pin's instrument: re-run it "
                             f"there (an archive of f9975b9, this file copied into specs/evidence/0043/, PYTHONPATH=src), confirm "
                             f"4 of 4 and 2 of 2, then move this pin to {got} in the same commit.")
