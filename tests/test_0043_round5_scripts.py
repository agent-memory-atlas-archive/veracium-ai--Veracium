"""specs/0043 — the two round-5 reproduction scripts are HISTORICAL evidence of the round-5 pin's instrument, and they
must stay runnable on it.

`round5_reproductions.py` and `round5_sweeps.py` reproduce the round-5 findings at the round-5 pin (c05b709), reading
that pin's code and committed ledger. Found at the round-6 stage (2026-10-08): a carrier sweep for the round-6
`reverify` changed their `v["verdict"]` to `v["downstream"]`, a key only the NEW reverify returns, so both scripts
broke on the one instrument they exist to measure, and nothing ran them. Two guards, both run everywhere and fast:
- beside any other instrument each script REFUSES by name (exit 2, with the recipe), never a crash on a changed name;
- each script's bytes are PINNED here. Their content is a measurement of fixed code; an edit is a re-measurement, so it
  re-runs the script against the round-5 tree (the recipe in the refusal) and moves the pin in the same commit.
Execution on the round-5 tree itself (about three minutes) runs at every package stage, where the package's claim that
the shipped evidence runs is made.
"""
import hashlib
import os
import re
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"
PINNED = {  # sha256 of each script, measured on the round-5 tree (round5_reproductions: 9 REPRODUCED, 6 of 6 controls; sweeps: 18 rows)
    "round5_reproductions.py": "79b9f382cc0afd9e499edcaa4a4451ce9cb6d772eb79e68ec570c89064514cd1",
    "round5_sweeps.py": "6cf7589df3e8bc5632726ea7325155936c3a361466aeb272f6515d3d16564aab",
}


@pytest.mark.parametrize("name", sorted(PINNED))
def test_a_round5_script_beside_another_instrument_refuses_by_name_with_the_recipe(name):
    r = subprocess.run([sys.executable, str(EVIDENCE / name)], capture_output=True, text=True, cwd=ROOT,
                       env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, timeout=300)
    assert r.returncode == 2, (r.returncode, r.stdout[-400:], r.stderr[-400:])
    assert r.stdout.startswith("REFUSED: this script reproduces the round-5 pin's instrument (c05b709b80a6)"), r.stdout[:300]
    assert "copy this file into its specs/evidence/0043/" in r.stdout and not r.stderr

MEASURED = {  # sha256 of each script as measured at 84cfecc, before the guard existed (research's ask: "restored" is byte-checked)
    "round5_reproductions.py": "62b28008f98e36443a22b9c0b58025679b0a2785a48d7c09950467ed5e17b543",
    "round5_sweeps.py": "1511c6fb6e81db09a7aa028e47243742cdce26df56981b127dad4de2302e20aa",
}
GUARD = re.compile(r"\n\n# THE TARGET GUARD .*?\n    sys\.exit\(2\)\n", re.S)


@pytest.mark.parametrize("name", sorted(PINNED))
def test_a_round5_script_minus_its_guard_is_the_84cfecc_measurement_byte_for_byte(name):
    text = (EVIDENCE / name).read_text(encoding="utf-8")
    assert len(GUARD.findall(text)) == 1, "exactly one guard block"
    assert hashlib.sha256(GUARD.sub("", text, count=1).encode("utf-8")).hexdigest() == MEASURED[name]


@pytest.mark.parametrize("name", sorted(PINNED))
def test_a_round5_script_is_the_measured_bytes(name):
    got = hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
    assert got == PINNED[name], (
        f"{name} changed. It is a measurement of the round-5 pin's instrument: re-run it there (extract the round-5 "
        f"package's tree/ or `git archive c05b709`, copy this file into its specs/evidence/0043/, run it with "
        f"PYTHONPATH=src), confirm its summary, then move this pin to {got} in the same commit.")
