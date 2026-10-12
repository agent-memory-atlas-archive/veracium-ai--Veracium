"""0048 §2c-ii rows 5, 7, 8, 11 and 12: the four evidence scripts the draft cites, run on this tree in every suite run.

The rows state what the SHIPPED code does today (the defects 0048 v3 answers), so these tests pin present behaviour:
rows 11 and 12 assert that the race and the round-1 reproductions still REPRODUCE, and they are inverted by the
implementation of 0048 §4 (its N4g/N4h tests replace them). The census (row 8) is a checker, so its refusals are
driven one by one on planted copies of src/ (P1's mutation matrix); `pin_repro.py` exits 1 when a reproduction stops
reproducing, so its matrix plants the fix and watches it say so. Every script runs as a subprocess with `veracium`
imported from the tree under test and its temporary files under the test's own directory.

What holds a NEW writer is two instruments, and neither alone. The census resolves the forms it is written for and
misses others (round 2's stage 2: twenty, then eleven more against its widened form), so it pins row 8's counts on this
tree and is no regression pin by itself. The token tripwire (`tripwire_0048.py`) resolves nothing: it counts every
token an unvalidated confidence write or an edge json write must contain, and a hand-classified snapshot of its hits
fails on any new one. Together they hold every planted attack. The residual is a write with none of the tripwire's
tokens: a field name built from parts that reaches the store through none of its names (a memory-level route such as
ctypes, a C extension), a SQL write verb built from parts, or SQL read from outside src/veracium/*.py; the residual
control is planted and silent in both. Durable protection is 0048 §4C's validating serialiser at the store, which does not care how a value was made.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

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
    line does not fail a draft's evidence. A sixth writer of a form the census resolves, or one moving file, does; a
    writer of another form is the tripwire's to catch (test_every_tripwire_hit_on_this_tree_is_classified)."""
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


# The planted forms, one table for both instruments: research's stage-2 matrix (its two controls and twenty forms the
# census was not written for, research 22685e22), dev's six (the forms the census WAS written for), dev's eleven from
# the next-mutant campaign against the widened census, research's pickle round trip, the residual the tripwire names,
# research's write through a table selector the tree already binds (planted inside its function), and seven harmless
# forms. Generated from research's two scripts by `ast.literal_eval`, not retyped (both at research 71c9ed9d). name: (file under src/veracium, code appended, a snippet that runs the form on a
# real Provenance `p` and leaves the result in `q`, or None).
_FORMS = {
    'CONTROL model_copy literal': ('_mut.py', "def f(p):\n    return p.model_copy(update={'confidence': 2.0})\n",
        "q = p.model_copy(update={'confidence': 2.0})"),
    'CONTROL edge UPDATE': ('store/sqlite.py', "_M = 'UPDATE edges SET json=? WHERE id=?'\n",
        None),
    'pydantic .copy(update=)': ('_mut.py', "def f(p):\n    return p.copy(update={'confidence': 2.0})\n",
        "q = p.copy(update={'confidence': 2.0})"),
    'copy.replace': ('_mut.py', 'import copy\ndef f(p):\n    return copy.replace(p, confidence=2.0)\n',
        'import copy; q = copy.replace(p, confidence=2.0)'),
    'model_copy(**kw)': ('_mut.py', "def f(p):\n    kw = {'update': {'confidence': 2.0}}\n    return p.model_copy(**kw)\n",
        "kw = {'update': {'confidence': 2.0}}; q = p.model_copy(**kw)"),
    'parameter rebound in a branch': ('_mut.py', "def f(p, u=None):\n    if u is None:\n        u = {'disclosure': p.disclosure}\n    return p.model_copy(update=u)\n",
        "def f(p, u=None):\n    if u is None:\n        u = {'disclosure': p.disclosure}\n    return p.model_copy(update=u)\nq = f(p, {'confidence': 2.0})"),
    'alias mutated': ('_mut.py', "def f(p):\n    u = {'disclosure': p.disclosure}\n    v = u\n    v['confidence'] = 2.0\n    return p.model_copy(update=u)\n",
        "u = {'disclosure': p.disclosure}; v = u; v['confidence'] = 2.0; q = p.model_copy(update=u)"),
    'dict.update(u, ...)': ('_mut.py', "def f(p):\n    u = {'disclosure': p.disclosure}\n    dict.update(u, confidence=2.0)\n    return p.model_copy(update=u)\n",
        "u = {'disclosure': p.disclosure}; dict.update(u, confidence=2.0); q = p.model_copy(update=u)"),
    'module-constant key': ('_mut.py', "K = 'confidence'\ndef f(p):\n    return p.model_copy(update={K: 2.0})\n",
        "K = 'confidence'; q = p.model_copy(update={K: 2.0})"),
    "getattr(p, 'model_copy')": ('_mut.py', "def f(p):\n    return getattr(p, 'model_copy')(update={'confidence': 2.0})\n",
        "q = getattr(p, 'model_copy')(update={'confidence': 2.0})"),
    'object.__setattr__': ('_mut.py', "def f(p):\n    object.__setattr__(p, 'confidence', 2.0)\n    return p\n",
        "object.__setattr__(p, 'confidence', 2.0); q = p"),
    '__dict__ write': ('_mut.py', "def f(p):\n    p.__dict__['confidence'] = 2.0\n    return p\n",
        "p.__dict__['confidence'] = 2.0; q = p"),
    'edge UPDATE over two lines': ('store/sqlite.py', "_M = '''UPDATE edges\n   SET json=? WHERE id=?'''\n",
        None),
    'edge update in lower case': ('store/sqlite.py', "_M = 'update edges set json=? where id=?'\n",
        None),
    'edge REPLACE INTO': ('store/sqlite.py', "_M = 'REPLACE INTO edges(id,user_id,json) VALUES(?,?,?)'\n",
        None),
    'edge UPDATE OR IGNORE': ('store/sqlite.py', "_M = 'UPDATE OR IGNORE edges SET json=? WHERE id=?'\n",
        None),
    'edge quoted table': ('store/sqlite.py', '_M = \'UPDATE "edges" SET json=? WHERE id=?\'\n',
        None),
    'edge SQL joined by +': ('store/sqlite.py', "_M = 'UPDATE edges ' + 'SET json=? WHERE id=?'\n",
        None),
    'edge writer in another module': ('store/_mut.py', "_M = 'UPDATE edges SET json=? WHERE id=?'\n",
        None),
    'edge schema-qualified': ('store/sqlite.py', "_M = 'UPDATE main.edges SET json=? WHERE id=?'\n",
        None),
    'from copy import replace': ('_mut.py', 'from copy import replace as r\ndef f(p):\n    return r(p, confidence=2.0)\n',
        'from copy import replace as r; q = r(p, confidence=2.0)'),
    'dynamic setattr': ('_mut.py', 'def f(p, k):\n    object.__setattr__(p, k, 2.0)\n    return p\n',
        "k = 'confidence'; object.__setattr__(p, k, 2.0); q = p"),
    'DEV update built by dict()': ('_mut.py', 'def f(p):\n    return p.model_copy(update=dict(confidence=1.0))\n',
        None),
    'DEV local dict writing confidence': ('_mut.py', "def f(p):\n    u = {'confidence': 1.0}\n    return p.model_copy(update=u)\n",
        None),
    'DEV local dict .update()': ('_mut.py', "def f(p):\n    u = {'disclosure': 1}\n    u.update(confidence=1.0)\n    return p.model_copy(update=u)\n",
        None),
    'DEV model_construct': ('_mut.py', 'def f(P):\n    return P.model_construct(confidence=2.0)\n',
        None),
    'DEV key three lines below': ('_mut.py', "def f(p):\n    return p.model_copy(update={\n        'a': 1,\n        'b': 2,\n        'confidence': 0.5})\n",
        None),
    'DEV new edge json writer': ('store/sqlite.py', "_MUT_SQL = 'UPDATE edges SET json=? WHERE user_id=?'\n",
        None),
    'HARMLESS other-field setattr': ('_mut.py', "def f(p):\n    object.__setattr__(p, 'kind', 1)\n    return p\n",
        None),
    'HARMLESS literal getattr': ('_mut.py', "def f(p):\n    return getattr(p, 'model_dump')()\n",
        None),
    'HARMLESS str/datetime replace': ('_mut.py', "def f(s, d):\n    return s.replace('a', 'b'), d.replace(year=2000)\n",
        None),
    'HARMLESS dict tested then used': ('_mut.py', "def f(p):\n    u = {}\n    if p:\n        u['disclosure'] = 1\n    if not u or len(u) == 0:\n        return p\n    return p.model_copy(update=u)\n",
        None),
    'HARMLESS edges read': ('store/sqlite.py', "_M = 'SELECT json FROM edges WHERE id=?'\n",
        None),
    'HARMLESS episodes write': ('store/sqlite.py', "_M = 'UPDATE episodes SET json=? WHERE id=?'\n",
        None),
    'HARMLESS edges_fts write': ('store/sqlite.py', "_M = 'INSERT INTO edges_fts(rowid, json) VALUES(?,?)'\n",
        None),
    'DEV2 vars(p)[...] store': ('_mut.py', "def f(p):\n    vars(p)['confidence'] = 2.0\n    return p\n",
        "vars(p)['confidence'] = 2.0; q = p"),
    'DEV2 __dict__.update': ('_mut.py', 'def f(p):\n    p.__dict__.update(confidence=2.0)\n    return p\n',
        'p.__dict__.update(confidence=2.0); q = p'),
    'DEV2 __dict__ alias |=': ('_mut.py', "def f(p):\n    d = p.__dict__\n    d |= {'confidence': 2.0}\n    return p\n",
        "d = p.__dict__; d |= {'confidence': 2.0}; q = p"),
    'DEV2 deprecated construct': ('_mut.py', 'def f(P):\n    return P.construct(confidence=2.0)\n',
        "q = type(p).construct(author_of_evidence=p.author_of_evidence, evidence_ref='r', confidence=2.0)"),
    'DEV2 bound-method alias': ('_mut.py', "def f(p):\n    m = p.model_copy\n    return m(update={'confidence': 2.0})\n",
        "m = p.model_copy; q = m(update={'confidence': 2.0})"),
    'DEV2 functools.partial': ('_mut.py', "import functools\ndef f(p):\n    return functools.partial(p.model_copy, update={'confidence': 2.0})()\n",
        "import functools; q = functools.partial(p.model_copy, update={'confidence': 2.0})()"),
    'DEV2 SQL %-formatted table': ('store/sqlite.py', "_M = 'UPDATE %s SET json=? WHERE id=?' % 'edges'\n",
        None),
    'DEV2 SQL f-string table name': ('store/sqlite.py', "_T = 'edges'\n_M = f'UPDATE {_T} SET json=? WHERE id=?'\n",
        None),
    "DEV2 SQL ' '.join": ('store/sqlite.py', "_M = ' '.join(['UPDATE edges', 'SET json=? WHERE id=?'])\n",
        None),
    'DEV2 SQL comment in statement': ('store/sqlite.py', "_M = 'UPDATE /* x */ edges SET json=? WHERE id=?'\n",
        None),
    'DEV2 SQL table alias': ('store/sqlite.py', "_M = 'UPDATE edges AS e SET json=? WHERE e.id=?'\n",
        None),
    'R2b pickle round trip': ('_mut.py', "import pickle, struct\ndef f(p):\n    b = pickle.dumps(p)\n    return pickle.loads(b.replace(struct.pack('>d', 0.5), struct.pack('>d', 2.0)))\n",
        "import pickle, struct; b = pickle.dumps(p); q = pickle.loads(b.replace(struct.pack('>d', 0.5), struct.pack('>d', 2.0)))"),
    'RESIDUAL verb built from parts': ('store/sqlite.py', "_M = 'UP' + 'DATE ed' + 'ges SET json=? WHERE id=?'\n",
        None),
}
# planted INSIDE an existing function: name: (file, anchor line that must occur exactly once, code put before it)
_INSERTS = {
    'R2b UPDATE through an existing selector': ('store/sqlite.py',
        '        row = self._conn.execute(f"SELECT json FROM {table} WHERE id=? AND user_id=?", (target_id, user_id)).fetchone()\n',
        '        self._conn.execute(f"UPDATE {table} SET json=? WHERE id=?", ("{}", target_id))\n'),
}

_CENSUS_IS_NOT_WRITTEN_FOR = ("DEV2 ", "R2b ", "RESIDUAL ", "HARMLESS ")
_TRIPWIRE_SILENT = {"RESIDUAL verb built from parts", "HARMLESS str/datetime replace"}
_DEV_SIX = {  # dev's six, with the exact census result each must give
    "DEV update built by dict()": "unresolved", "DEV local dict writing confidence": "unresolved",
    "DEV local dict .update()": "unresolved", "DEV model_construct": "unresolved",
    "DEV key three lines below": "six writers", "DEV new edge json writer": "eight edge writers"}
_REACH = """
import sys
from veracium.schema import Provenance, EvidenceAuthor
p = Provenance(author_of_evidence=list(EvidenceAuthor)[0], evidence_ref="r", confidence=0.5)
try:
{body}
except Exception as ex:
    print("REFUSED", type(ex).__name__); sys.exit(0)
print("WROTE", q.confidence)
"""


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    """Every form planted on its own copy of src/, both instruments run on it, and every Python form executed on a
    real Provenance. The unmutated copy is run first and must give the honest results, so a planted case cannot pass by
    the copy being broken."""
    td = tmp_path_factory.mktemp("planted")

    def instruments(tree):
        c = _run(td, "census_0048.py", tree)
        t = _run(td, "tripwire_0048.py", tree)
        assert t.returncode == 0, t.stderr
        return c, json.loads(t.stdout)
    base = td / "base"
    shutil.copytree(ROOT / "src" / "veracium", base / "src" / "veracium", ignore=shutil.ignore_patterns("__pycache__"))
    c0, t0 = instruments(base)
    assert c0.returncode == 0 and _census_sites(c0.stdout)[0::2] == (5, 7), c0.stdout
    out = {}
    plants = [(n, rel, code, reach, None) for n, (rel, code, reach) in _FORMS.items()] + \
             [(n, rel, code, None, anchor) for n, (rel, anchor, code) in _INSERTS.items()]
    for i, (name, rel, code, reach, anchor) in enumerate(plants):
        tree = td / f"m{i}"
        shutil.copytree(base, tree)
        target = tree / "src" / "veracium" / rel
        if anchor is None:
            target.write_text((target.read_text() if target.exists() else "") + "\n" + code)
        else:
            old = target.read_text()
            assert old.count(anchor) == 1, f"{name}: the anchor occurs {old.count(anchor)} times -- re-anchor it"
            target.write_text(old.replace(anchor, code + anchor))
        c, tw = instruments(tree)
        cells = {(f, h) for f in set(tw) | set(t0) for h in set(tw.get(f, {})) | set(t0.get(f, {}))}
        fires = sorted(f"{f}:{h}" for f, h in cells if tw.get(f, {}).get(h, 0) != t0.get(f, {}).get(h, 0))
        wrote = None
        if reach is not None:
            body = "\n".join("    " + ln for ln in (reach.splitlines() if "\n" in reach else reach.split("; ")))
            r = subprocess.run([sys.executable, "-c", _REACH.format(body=body)], capture_output=True, text=True,
                               env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, timeout=120)
            wrote = r.stdout.strip() or r.stderr.strip()
        out[name] = (c, _census_sites(c.stdout) if c.returncode in (0, 1) else None, fires, wrote)
    return c0, out


def test_census_0048_refuses_each_planted_defect(planted):
    """census_0048.py's mutation matrix, over the forms it is written to resolve: research's two controls and twenty
    stage-2 forms (each exits 1 as UNRESOLVED or moves a count), and dev's six with the exact result each gives. The
    census's boundary is pinned too, so it cannot move unseen: it stays silent on the seven harmless forms (no
    over-refusal) and on the forms it was not written for, which tripwire_0048.py holds (the next test)."""
    c0, out = planted
    honest = _census_sites(c0.stdout)
    for name, (c, sites, _, _) in out.items():
        n_conf, _, n_edge, n_unres = sites
        noticed = c.returncode == 1 or (n_conf, n_edge, n_unres) != (honest[0], honest[2], honest[3])
        if name.startswith(_CENSUS_IS_NOT_WRITTEN_FOR):
            assert c.returncode == 0 and not noticed, (name, c.stdout)
        elif name in _DEV_SIX:
            assert {"unresolved": c.returncode == 1 and n_unres >= 1,
                    "six writers": c.returncode == 0 and n_conf == 6,
                    "eight edge writers": c.returncode == 0 and n_edge == 8}[_DEV_SIX[name]], (name, c.stdout)
        else:
            assert noticed, (name, c.stdout)


def test_tripwire_0048_fires_on_every_planted_attack(planted):
    """tripwire_0048.py's mutation matrix. Every attack form (41: the census's own, the twenty it was not written for,
    dev's eleven, the pickle round trip, a write through a table selector the tree already binds) moves a (file,
    trigger) count, and every one that is Python really stores 2.0 when run, so none is a straw man. The residual the
    tripwire's docstring names (a SQL write verb built from parts) is silent in BOTH instruments: the residual is
    stated, and it is accurate. The harmless split is pinned (six fire, the tripwire's cost by design; one is
    silent)."""
    _, out = planted
    for name, (c, _, fires, wrote) in out.items():
        if name in _TRIPWIRE_SILENT:
            assert not fires, (name, fires)
        else:
            assert fires, (name, "tripwire_0048.py is silent")
        if name.startswith("RESIDUAL"):
            assert c.returncode == 0, (name, c.stdout)
        if wrote is not None:
            assert wrote == "WROTE 2.0", (name, wrote)
    attacks = [n for n in out if not n.startswith(("HARMLESS", "RESIDUAL"))]
    assert len(attacks) == 41 and sum(out[n][3] is not None for n in attacks) == 20, (len(attacks),)
    assert sum(n.startswith("HARMLESS") for n in out) == 7 and sum(n.startswith("RESIDUAL") for n in out) == 1


# --- the tripwire's snapshot -------------------------------------------------------------------------------------------

def test_every_tripwire_hit_on_this_tree_is_classified(tmp_path):
    """tripwire_0048.py's hits on this tree equal, as a multiset of (file, trigger, line text), the rows of
    tripwire_0048_classified.tsv, and every row carries a class from its header's closed list. A line that moves still
    matches; a new hit, or an edit to a hit's line, fails here until someone classifies it."""
    r = _run(tmp_path, "tripwire_0048.py", ROOT, "--sites")
    assert r.returncode == 0, r.stderr
    live = collections.Counter()
    for ln in r.stdout.splitlines():
        loc, trig, *text = ln.split(" ", 2)
        live[(loc.rsplit(":", 1)[0], trig, text[0] if text else "")] += 1
    table = (EV / "tripwire_0048_classified.tsv").read_text().splitlines()
    classes = set(re.findall(r"^#   ([a-z-]+) ", "\n".join(table), re.M))
    assert len(classes) == 13, classes
    rows = [ln.split("\t") for ln in table if ln and not ln.startswith("#")]
    assert all(len(row) == 4 and row[0] in classes for row in rows), [row for row in rows if row[0] not in classes]
    snap = collections.Counter((f, t, x) for _, f, t, x in rows)
    assert snap == live, {"unclassified": live - snap, "classified but gone": snap - live}


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
