"""0048 §2c-ii rows 5, 7, 8, 11 and 12: the four evidence scripts the draft cites, run on this tree in every suite run.

The rows state what the SHIPPED code does today (the defects 0048 v3 answers), so these tests pin present behaviour:
rows 11 and 12 assert that the race and the round-1 reproductions still REPRODUCE, and they are inverted by the
implementation of 0048 §4 (its N4g/N4h tests replace them). The census (row 8) is a checker, so its refusals are
driven one by one on planted copies of src/ (P1's mutation matrix); `pin_repro.py` exits 1 when a reproduction stops
reproducing, so its matrix plants the fix and watches it say so. Every script runs as a subprocess with `veracium`
imported from the tree under test and its temporary files under the test's own directory.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EV = ROOT / "specs" / "evidence" / "0048"
SPEC = ROOT / "specs" / "0048-decay-never-raises-confidence.md"


def _run(tmp_path, script, *args, tree=ROOT):
    env = {**os.environ, "PYTHONPATH": str(tree / "src"), "TMPDIR": str(tmp_path)}
    return subprocess.run([sys.executable, str(EV / script), *map(str, args)], cwd=tree, env=env,
                          capture_output=True, text=True, timeout=300)


def _row(n):
    """The §2c-ii table row numbered `n`, as text."""
    (line,) = [ln for ln in SPEC.read_text().splitlines() if re.match(rf"\| {n} \|", ln)]
    return line


# --- row 8: the census -----------------------------------------------------------------------------------------------

def _census_sites(out):
    conf = re.search(r"of them write `confidence`: (\d+)\n((?:  \S+:\d+ .*\n)*)", out)
    edges = re.search(r"edge json writers in store/sqlite\.py: (\d+)", out)
    unresolved = re.search(r"UNRESOLVED: (\d+)", out)
    files = sorted(re.sub(r"^src/veracium/", "", ln.split()[0].rsplit(":", 1)[0]) for ln in conf.group(2).splitlines())
    return int(conf.group(1)), files, int(edges.group(1)), int(unresolved.group(1))


def test_the_census_states_what_row_8_says(tmp_path):
    """Row 8's counts against the census run on this tree: five confidence writers in the files the row names, seven
    edge json writers, nothing unresolved. Files and counts, not line numbers, so an unrelated src/ edit that moves a
    line does not fail a draft's evidence; a sixth writer, or one moving file, does."""
    r = _run(tmp_path, "census_0048.py", ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    n_conf, files, n_edge, n_unres = _census_sites(r.stdout)
    row = _row(8)
    named = sorted(m.rsplit(":", 1)[0] for m in re.findall(r"`((?:store/)?[a-z_]+\.py:\d+)`", row)
                   if not m.startswith("scope_read.py"))
    assert (n_conf, n_edge, n_unres) == (5, 7, 0), r.stdout
    assert "**five**" in row and "Edge `json` writers at L" in row
    assert files == named, (files, named)
    assert len(re.search(r"Edge `json` writers at (L[\d, ]+)", row).group(1).split(",")) == n_edge


_MUTANTS = {
    # name: (file under src/veracium, code appended, what the census must then report)
    "an update built by dict()": ("_mut.py", "def f(p):\n    return p.model_copy(update=dict(confidence=1.0))\n",
                                  "unresolved"),
    "a local dict writing confidence": ("_mut.py", "def f(p):\n    u = {'confidence': 1.0}\n"
                                        "    return p.model_copy(update=u)\n", "unresolved"),
    "a local dict mutated by .update()": ("_mut.py", "def f(p):\n    u = {'disclosure': 1}\n"
                                          "    u.update(confidence=1.0)\n"
                                          "    return p.model_copy(update=u)\n", "unresolved"),
    "model_construct": ("_mut.py", "def f(P):\n    return P.model_construct(confidence=2.0)\n", "unresolved"),
    "a key three lines below its call": ("_mut.py", "def f(p):\n    return p.model_copy(update={\n        'a': 1,\n"
                                         "        'b': 2,\n        'confidence': 0.5})\n", "six writers"),
    "a new edge json writer": ("store/sqlite.py", "_MUT_SQL = 'UPDATE edges SET json=? WHERE user_id=?'\n",
                               "eight edge writers"),
}


def test_census_0048_refuses_each_planted_defect(tmp_path):
    """census_0048's mutation matrix (research demonstrated these six at research 1f6ba672; here they run in every
    suite): each unresolvable confidence write exits 1 as UNRESOLVED, a key on a later line of the call is still found,
    and a new edge writer moves the count. The unmutated copy reproduces the honest result first, so a planted case
    cannot pass by the copy being broken."""
    def copy():
        tree = tmp_path / f"t{len(list(tmp_path.iterdir()))}"
        shutil.copytree(ROOT / "src" / "veracium", tree / "src" / "veracium")
        return tree
    honest = _run(tmp_path, "census_0048.py", copy())
    assert honest.returncode == 0 and _census_sites(honest.stdout)[0::2] == (5, 7), honest.stdout
    for name, (rel, code, expect) in _MUTANTS.items():
        tree = copy()
        target = tree / "src" / "veracium" / rel
        target.write_text((target.read_text() if target.exists() else "") + "\n" + code)
        r = _run(tmp_path, "census_0048.py", tree)
        n_conf, _, n_edge, n_unres = _census_sites(r.stdout)
        if expect == "unresolved":
            assert r.returncode == 1 and n_unres >= 1, (name, r.stdout)
        elif expect == "six writers":
            assert r.returncode == 0 and n_conf == 6, (name, r.stdout)
        else:
            assert r.returncode == 0 and n_edge == 8, (name, r.stdout)


# --- rows 5 and 7: reach_rows ----------------------------------------------------------------------------------------

def test_reach_row_5_the_out_of_range_write_breaks_the_users_read(tmp_path):
    r = _run(tmp_path, "reach_rows.py", ROOT, 5)
    assert r.returncode == 0, r.stdout + r.stderr
    for phrase in ("Input should be less than or equal to 1", "Input should be a valid number", "0.45"):
        assert phrase in r.stdout and phrase in _row(5), (phrase, r.stdout)


def test_reach_row_7_one_bounded_field_frozen_without_assignment_validation(tmp_path):
    r = _run(tmp_path, "reach_rows.py", ROOT, 7)
    assert r.returncode == 0, r.stdout + r.stderr
    for span in re.findall(r"`([^`]+)`", _row(7).split("|")[4]):
        assert span in r.stdout, (span, r.stdout)


# --- row 11: the lost update -----------------------------------------------------------------------------------------

def test_row_11_the_shipped_expire_loses_an_overlapping_update(tmp_path):
    """Present behaviour, inverted by 0048 §4D: all four overlapping cases lose B's committed state, and the serial
    controls (B, then A) keep it, so the overlap is the defect."""
    r = _run(tmp_path, "probe_expire_lost_update.py", tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    verdicts = dict(re.findall(r"^(\w+)\s+B committed .*\n.*\s(LOST-UPDATE|kept)$", r.stdout, re.M))
    assert verdicts == {"confirm": "LOST-UPDATE", "confirm95": "LOST-UPDATE", "lapse": "LOST-UPDATE",
                        "decay": "LOST-UPDATE"}, r.stdout
    serial = dict(re.findall(r"^(\w+)\s+SERIAL B .*\n.*\s(kept|CHANGED)$", r.stdout, re.M))
    assert serial == {"confirm": "kept", "lapse": "kept"}, r.stdout


# --- row 12: the round-1 reproductions -------------------------------------------------------------------------------

def test_row_12_the_round_1_reproductions_hold_and_their_controls_hold(tmp_path):
    r = _run(tmp_path, "pin_repro.py", ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    labels = [ln[:14].strip() for ln in r.stdout.splitlines()]
    assert labels.count("REPRODUCED") == 9 and labels.count("CONTROL HOLDS") == 3, r.stdout
    assert not (tmp_path / "leftover").exists() and not any(p.name.startswith("tmp") for p in tmp_path.iterdir())


def test_pin_repro_reports_a_planted_fix_as_not_reproduced(tmp_path):
    """pin_repro's mutation matrix: an instrument that reports REPRODUCED whatever the code does proves nothing. On a
    copy of src/ with the decay factor clamped to 1, the factor case must say NOT REPRODUCED and the run exit 1, while
    every other line is unchanged (the clamp does not touch the floor, the race, the loop or the census) and the
    controls still hold. A first form of this mutant also clamped the floor into [0, 1] and expected the floor case to
    flip; it cannot, since a floor of 1.0 still invalidates a decayed 0.45, so that expectation was wrong, not the
    instrument."""
    tree = tmp_path / "fixed"
    shutil.copytree(ROOT / "src" / "veracium", tree / "src" / "veracium")
    lc = tree / "src" / "veracium" / "lifecycle.py"
    t = lc.read_text()
    a = 'e.provenance.confidence * config.decay_factor})'
    assert t.count(a) == 1, "the mutant's anchor moved: re-anchor this test"
    lc.write_text(t.replace(a, 'e.provenance.confidence * min(float(config.decay_factor), 1.0)})'))
    honest = _run(tmp_path, "pin_repro.py", ROOT)
    r = _run(tmp_path, "pin_repro.py", tree, tree=tree)
    assert r.returncode == 1, r.stdout + r.stderr
    pairs = zip(honest.stdout.splitlines(), r.stdout.splitlines())
    flipped = [(h[:14].strip(), m[:14].strip(), h[15:50]) for h, m in pairs if h[:14] != m[:14]]
    assert flipped == [("REPRODUCED", "NOT REPRODUCED", "R1-01 factor 2.0 on 0.3: persisted ")], flipped
