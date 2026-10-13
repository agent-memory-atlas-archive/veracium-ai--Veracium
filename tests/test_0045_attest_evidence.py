"""0045 §4a: the ATTEST evidence set (`specs/evidence/0045/attest/`, research's, landed with the spec) re-run in every
suite run, and its figures compared to the ones 0045 states — a restated measurement is a carrier the evidence can
outrun. It is evidence for a spec under review, not product code; nothing here imports `veracium`.

0045 v1.8 (round 3): ATTEST-3 is the predicate, frozen before holdout H2 existed and scored on it ONCE; ATTEST-2 and
H1 stay as history (H1 is regression only for ATTEST-3). Every figure 0045 states is re-derived here from the run.
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
# frozen BEFORE their holdouts existed (the evidence README); 0045 §4a cites ATTEST-3's first eight hex digits
FROZEN_ATTEST_2 = "e1e1e3d3f3eea956e6c3b78780db20c2e744534ebfd5d4f52bf6e3ba7f928c7a"
FROZEN_ATTEST_3_PREFIX = "b1329a81"


def _run(*args):
    r = subprocess.run([sys.executable, "-B", *args], cwd=ATTEST, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def _counts(out):
    return ast.literal_eval(re.search(r"(\{'TP'.*?\})", out).group(1))


def test_the_frozen_predicates_are_the_ones_0045_cites():
    assert hashlib.sha256((ATTEST / "attest_v2.py").read_bytes()).hexdigest() == FROZEN_ATTEST_2   # history, unchanged
    digest = hashlib.sha256((ATTEST / "attest_v3.py").read_bytes()).hexdigest()
    assert digest.startswith(FROZEN_ATTEST_3_PREFIX), digest
    assert f"`{digest[:8]}…`" in SPEC.read_text(encoding="utf-8")


def test_the_h2_figures_0045_states_are_the_ones_the_scorer_prints():
    """Both H2 golds (the author's and the second blind labelling) give the same counts, and 0045 §4a states exactly
    those for ATTEST-3: false attestations FP/(FP+TN), recall TP/(TP+FN); and ATTEST-2's on the same H2."""
    spec = SPEC.read_text(encoding="utf-8")
    seen = [_counts(_run("score_holdout.py", "attest_v3", "holdout_h2.json", *gold)) for gold in ((), ("labels_h2_b.json",))]
    assert seen[0] == seen[1], seen
    c = seen[0]
    assert f"**ATTEST-3: {c['FP']} / {c['FP'] + c['TN']} false attestations**" in spec, (c, "ATTEST-3's H2 false attestations")
    assert f"**{c['TP']} / {c['TP'] + c['FN']} recall" in spec, (c, "ATTEST-3's H2 recall")
    a2 = _counts(_run("score_holdout.py", "attest_v2", "holdout_h2.json"))
    assert (f"ATTEST-2 on the same H2: {a2['FP']} / {a2['FP'] + a2['TN']} and {a2['TP']} / {a2['TP'] + a2['FN']}"
            in spec), (a2, "ATTEST-2 on H2")


def test_the_h1_figures_0045_states_are_the_ones_the_scorer_prints():
    """H1: ATTEST-2's measurement (history) and ATTEST-3 as regression only, under both golds."""
    spec = SPEC.read_text(encoding="utf-8")
    for gold in ((), ("labels_h1_b.json",)):
        c2 = _counts(_run("score_h1.py", "attest_v2", *gold))
        assert f"**{c2['FP']} / {c2['FP'] + c2['TN']} false attestations, {c2['TP']} / {c2['TP'] + c2['FN']} recall**" in spec, c2
        c3 = _counts(_run("score_holdout.py", "attest_v3", "holdout_h1.json", *gold))
        assert f"ATTEST-3: {c3['FP']} / {c3['FP'] + c3['TN']}, {c3['TP']} / {c3['TP'] + c3['FN']}" in spec, c3


def test_attest_3s_mechanism_mutants_are_all_killed_with_clean_controls():
    out = _run("mutants_v3.py")
    assert re.search(r"^control \(first\): 0 false attestations$", out, re.M), out
    assert re.search(r"^control \(last\): 0 false attestations$", out, re.M), out
    killed = re.findall(r"^KILLED\s+(.+?): (\d+) new false attestations", out, re.M)
    assert len(killed) == 8 and all(int(n) > 0 for _, n in killed), out
    assert "SURVIVED" not in out


def test_attest_3s_regression_gate_holds():
    out = _run("regressions_v3.py")
    assert out.rstrip().endswith("every gate holds"), out


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
    _run("score_holdout.py", "attest_v3", "holdout_h2.json")
    _run("mutants_v3.py")
    _run("regressions_v3.py")
    assert sorted(p.name for p in ATTEST.iterdir()) == before
