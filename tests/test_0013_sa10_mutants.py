"""INV-SA10's mutation table (0013 §5f.1; 0007 I2): specs/evidence/0013/sa10_mutants.py.

The table is current and every row good, and its `--check` refuses each way a table can be wrong: edited after
writing, a row not killed, a named cell that passed, a declared reason not seen, an unrelated failure counted as a kill,
a missing row, a stale digest, a changed definition, a red clean run, a classifier control that killed, another spec,
and a duplicate key.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(stem):
    name = f"veracium_{stem}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "specs" / "evidence" / "0013" / f"{stem}.py")
        m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return sys.modules[name]


sm = _load("sa10_mutants")


def test_the_mutation_table_is_current_and_every_row_good():
    assert sm.problems() == []


def _base():
    """The committed table with its digests set to the live bytes, so the tamper cells below read one change each
    whether or not the table is stale (the test above is the staleness check)."""
    t = json.loads(sm.TABLE.read_text(encoding="utf-8"))
    t["header"]["digests"] = sm._digests(ROOT)
    return t


def _write(tmp_path, t, redigest=True):
    if redigest:
        t["body_sha256"] = hashlib.sha256(sm.canonical({k: v for k, v in t.items() if k != "body_sha256"})).hexdigest()
    p = tmp_path / "mutation-table.json"
    p.write_text(sm.render(t), encoding="utf-8")
    return p


def _reasoned(t):
    return next(r for r in t["rows"] if r["reason"] is not None)


def _unname(t):
    r = t["rows"][0]
    n = r["named_cells"][0]
    r["cells_failed"].remove(n)
    r["cell_kinds"].pop(n)


TAMPERS = {
    "edited after writing": (lambda t: t["rows"][0].__setitem__("what", "edited"), False,
                             "does not match its own body digest"),
    "a row not killed": (lambda t: t["rows"][0].update(outcome="SURVIVED"), True, "not a good row"),
    "a named cell that passed": (_unname, True, "every named cell failed False"),
    "a declared reason not seen": (lambda t: _reasoned(t).update(reason_seen=False), True, "not a good row"),
    "an unrelated failure counted as a kill": (
        lambda t: (t["rows"][0]["cells_failed"].append("x::y"), t["rows"][0]["cell_kinds"].__setitem__(
            "x::y", "other: TypeError")), True, "recounted UNCLASSIFIED"),
    "a missing row": (lambda t: t["rows"].pop(), True, "the rows are not one per mutant"),
    "a stale digest": (lambda t: t["header"]["digests"].__setitem__(sm.GATE, "0" * 64), True, "stale: "),
    "a changed definition": (lambda t: t["header"]["definitions"].__setitem__(sm.MUTANTS[0][0], "0" * 64), True,
                             "the mutant definitions differ"),
    "a red clean run": (lambda t: t["header"]["clean"]["last"].__setitem__("ok", False), True,
                        "the clean runs are not both green"),
    "a classifier control that killed": (lambda t: t["controls"][0].update(outcome="KILLED"), True,
                                         "negative control is not good"),
    "another spec": (lambda t: t["header"].__setitem__("spec", "0007"), True, "not 0013/INV-SA10"),
}


def test_the_table_check_refuses_each_tampered_table(tmp_path):
    check = _load("sa10_mutants").problems                  # the artifact this matrix binds (P1)
    (tmp_path / "control").mkdir()
    assert check(_write(tmp_path / "control", _base())) == []           # the untampered copy passes
    for name, (tamper, redigest, want) in TAMPERS.items():
        t = copy.deepcopy(_base())
        tamper(t)
        d = tmp_path / name.replace(" ", "-")
        d.mkdir()
        probs = check(_write(d, t, redigest))
        assert any(want in p for p in probs), (name, probs)
    dup = tmp_path / "dup.json"
    text = sm.render(_base())
    dup.write_text(text.replace('{\n "body_sha256"', '{\n "body_sha256": "x",\n "body_sha256"', 1), encoding="utf-8")
    assert any("duplicate key" in p for p in check(dup)), check(dup)


def test_every_n_cell_of_the_section_table_has_a_mutant_that_names_it():
    """§5f.1's N1–N12 and stage-1's N13–N15: each cell is named by at least one mutant's row, so a cell with no
    demonstration cannot be added silently."""
    tests = sm.defined_tests()
    n_tests = sorted(t for t in tests if t.startswith("test_n") and t[6:7].isdigit())
    named = {n.split("::")[1].split("[")[0] for m in sm.MUTANTS for n in m[4]}
    assert n_tests and set(n_tests) <= named, sorted(set(n_tests) - named)
    covered = {int(x) for m in sm.MUTANTS for n in m[4] for x in re.findall(r"(?:_n|\[N)(\d+)", n.split("::")[1])}
    assert covered == set(range(1, 16)), sorted(set(range(1, 16)) ^ covered)


@pytest.mark.parametrize("kind", ["gate", "tree"])
def test_each_kind_of_mutant_is_present(kind):
    assert any(m[1] == kind for m in sm.MUTANTS)
