"""specs/0043 — the round-6 verdict's reproductions (R6-01..03), measured at the round-6 pin be35c9b before any fix, are
HISTORICAL evidence of that instrument: beside any other instrument the script refuses by name with its recipe, and its
bytes are pinned (the round-5 scripts' lesson: an edit to a measurement is a re-measurement). Its execution on the
round-6 pin's tree runs at every package stage."""
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "specs" / "evidence" / "0043" / "round6_reproductions.py"
MEASURED = "d3dfd6e65a00f305c783dc861c1fa933a8bf62e8c0d1e5014f910f5228dcb470"     # measured on an archive of be35c9b: 10 of 10 REPRODUCED, 5 of 5 controls


def test_the_round6_reproductions_beside_another_instrument_refuse_by_name_with_the_recipe():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=ROOT,
                       env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, timeout=300)
    assert r.returncode == 2 and r.stdout.startswith("REFUSED: this script reproduces the round-6 pin's instrument (be35c9b55cbb)"), r.stdout[:300]
    assert "copy this file into its specs/evidence/0043/" in r.stdout and not r.stderr


def test_the_round6_reproductions_are_the_measured_bytes():
    got = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert got == MEASURED, (f"round6_reproductions.py changed. It is a measurement of the round-6 pin's instrument: re-run it "
                             f"there (an archive of be35c9b, this file copied into specs/evidence/0043/, PYTHONPATH=src), confirm "
                             f"10 of 10 and 5 of 5, then move this pin to {got} in the same commit.")
