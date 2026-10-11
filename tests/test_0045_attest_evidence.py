"""0045 §4a: the ATTEST evidence set (`specs/evidence/0045/attest/`, research's, landed with the spec) re-run in every
suite run, and its figures compared to the ones 0045 states — a restated measurement is a carrier the evidence can
outrun. It is evidence for a spec under review, not product code; nothing here imports `veracium`.
"""
from __future__ import annotations

import ast
import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ATTEST = ROOT / "specs" / "evidence" / "0045" / "attest"
SPEC = ROOT / "specs" / "0045-declarative-grounding.md"
# frozen BEFORE the holdout existed (the evidence README, step 2); 0045 §4a cites its first eight hex digits
FROZEN_ATTEST_2 = "e1e1e3d3f3eea956e6c3b78780db20c2e744534ebfd5d4f52bf6e3ba7f928c7a"


def _run(*args):
    r = subprocess.run([sys.executable, "-B", *args], cwd=ATTEST, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_attest_2_is_the_frozen_predicate_0045_cites():
    digest = hashlib.sha256((ATTEST / "attest_v2.py").read_bytes()).hexdigest()
    assert digest == FROZEN_ATTEST_2
    assert f"`{digest[:8]}…`" in SPEC.read_text(encoding="utf-8")


def test_the_holdout_figures_0045_states_are_the_ones_the_scorer_prints():
    """Both golds (the H1 author's and the second blind labelling) give the same counts, and 0045 §4a states exactly
    those: false attestations FP/(FP+TN), genuine statements recognised TP/(TP+FN)."""
    spec = SPEC.read_text(encoding="utf-8")
    seen = []
    for gold in ((), ("labels_h1_b.json",)):
        out = _run("score_h1.py", "attest_v2", *gold)
        c = ast.literal_eval(re.search(r"(\{'TP'.*?\})", out).group(1))
        seen.append(c)
        assert f"**{c['FP']} / {c['FP'] + c['TN']} false attestations**" in spec, (c, "0045's false-attestation figure")
        assert f"**{c['TP']} / {c['TP'] + c['FN']} genuine statements recognised" in spec, (c, "0045's recall figure")
    assert seen[0] == seen[1], seen


def test_r1_01s_three_mutants_are_killed_and_attest_2_falsely_attests_nothing():
    out = _run("mutants_r1_01.py")
    assert re.search(r"^ATTEST-2 false attestations over \d+ labelled items: 0$", out, re.M), out
    killed = re.findall(r"^  mutant '([^']+)': (\d+) new false attestations -> KILLED", out, re.M)
    assert [k for k, _ in killed] == ["drop polarity", "swap subject", "relation without a supporting assertion"], out
    assert all(int(n) > 0 for _, n in killed)
    assert "SURVIVED" not in out


def test_the_evidence_run_leaves_its_directory_untouched():
    before = sorted(p.name for p in ATTEST.iterdir())
    _run("score_h1.py", "attest_v2")
    assert sorted(p.name for p in ATTEST.iterdir()) == before
