"""INV-SA10's mutation table (0013 §5f.1; 0007 I2): specs/evidence/0013/sa10_mutants.py.

The table is current and every row good, and its `--check` refuses each way a table can be wrong: edited after
writing, a row not killed, a named cell that passed, a declared reason not seen, an unrelated failure counted as a kill,
a missing row, a stale digest, a changed definition, a red clean run, a classifier control that killed, another spec,
and a duplicate key.
"""
from __future__ import annotations

import collections
import copy
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
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


def test_the_table_check_refuses_each_tampered_table(tmp_path, monkeypatch):
    check = _load("sa10_mutants").problems                  # the artifact this matrix binds (P1)
    (tmp_path / "control").mkdir()
    control = _write(tmp_path / "control", _base())
    assert check(control) == []                                         # the untampered copy passes
    # the phrase complement is part of the check: an untampered table with a phrase uncarried refuses, by name
    k = ("N2", "a row-count postcondition in place of the list")
    monkeypatch.setattr(sm, "CARRIERS", {x: v for x, v in sm.CARRIERS.items() if x != k})
    assert "N2 phrase 'a row-count postcondition in place of the list' has no carrier" in check(control)
    monkeypatch.undo()
    assert check(control) == []
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


# ---- the phrase complement: §5f.1's "gate mutant it kills" column EQUALS the carriers --------------------------------
def test_every_section_phrase_has_exactly_one_carrier():
    """Read from the spec's bytes at run time: every row of §5f.1's table, split by mutant, and each phrase carried."""
    rows = [r for r, _cell in sm.section_rows()]
    assert rows == [f"N{i}" for i in range(1, 16)] + ["W1", "W2", "W3", "C1", "C2", "C3"], rows
    ph = sm.phrases()
    per_row = collections.Counter(k[0] for k in ph)
    assert "C1" not in per_row                                   # "—": the control names no mutant
    assert {r: per_row[r] for r in ("N2", "N4", "N7", "N8", "N11", "N12", "W2", "W3", "C2", "C3")} == {
        "N2": 2, "N4": 1, "N7": 2, "N8": 1, "N11": 2, "N12": 2, "W2": 2, "W3": 2, "C2": 1, "C3": 1}, per_row
    n6 = ("N6", "classify by the leading keyword")
    n13 = ("N13", "forward every name the proxy does not list to the real connection")
    assert {k: v for k, v in ph.items() if v is not None} == {
        ("N7", "the same"): n6, ("N14", "the same"): n13, ("N15", "the same"): n13}
    assert sm.carrier_problems() == []
    assert set(ph) == set(sm.CARRIERS)


def test_the_split_is_by_mutant_at_parenthesis_depth_zero():
    s = sm._split_depth0
    assert s("") == [""]                                                                       # n = 0 (refused later)
    assert s("drop the assertion") == ["drop the assertion"]                                     # n = 1
    assert s("a; b") == ["a", "b"]                                                             # n = 2
    assert s("a; b, or c or d") == ["a", "b", "c", "d"]                                        # each separator
    assert s("x (y; z or w, or v) or u") == ["x (y; z or w, or v)", "u"]                       # nothing inside (...)
    assert s("allow a and classify b") == ["allow a and classify b"]                           # never on " and "
    for bad in ("a (b", "a) b"):
        with pytest.raises(ValueError):
            s(bad)


def _spec_root(tmp_path, old, new):
    """A root holding the cells file and a copy of the spec with `old` (which must occur exactly once) made `new`."""
    text = (ROOT / sm.SPEC).read_text(encoding="utf-8")
    assert text.count(old) == 1, old                             # the mutator asserts its anchor
    (tmp_path / sm.SPEC).parent.mkdir(parents=True)
    (tmp_path / sm.SPEC).write_text(text.replace(old, new), encoding="utf-8")
    (tmp_path / "tests").mkdir()
    shutil.copy(ROOT / sm.CELLS_FILE, tmp_path / sm.CELLS_FILE)
    return tmp_path


def test_a_phrase_without_a_carrier_or_a_carrier_without_a_phrase_fails_by_name(monkeypatch, capsys):
    k = ("N11", "attribute actions by trace sequence")
    monkeypatch.setattr(sm, "CARRIERS", {x: v for x, v in sm.CARRIERS.items() if x != k})
    want = "N11 phrase 'attribute actions by trace sequence' has no carrier"
    assert want in sm.carrier_problems()
    assert want in sm.problems()                                 # --check's own list
    assert sm.main(["sa10_mutants.py", "--check"]) == 1 and want in capsys.readouterr().out
    assert sm.main(["sa10_mutants.py", "--phrases"]) == 1 and want in capsys.readouterr().out
    monkeypatch.setattr(sm.SUBJECT_P, "main", lambda argv: pytest.fail("the campaign ran with a phrase uncarried"))
    assert sm.main(["sa10_mutants.py", "--write"]) == 1 and want in capsys.readouterr().out
    monkeypatch.setattr(sm, "CARRIERS", {**sm.CARRIERS, k: ("mutant", "N11-attribute-by-trace-sequence"),
                                         ("N11", "a phrase nobody wrote"): ("mutant", "N11-orphans-skipped")})
    assert sm.carrier_problems() == ["N11 carrier 'a phrase nobody wrote' has no phrase in the spec"]


def test_a_phrase_removed_from_or_added_to_the_spec_fails_by_name(tmp_path):
    gone = _spec_root(tmp_path / "gone", "| attribute actions by trace sequence, or skip the orphan check |",
                      "| skip the orphan check |")
    assert sm.carrier_problems(gone) == ["N11 carrier 'attribute actions by trace sequence' has no phrase in the spec"]
    added = _spec_root(tmp_path / "added", "| widen (b2) to every index |", "| widen (b2) to every index; a new one |")
    assert sm.carrier_problems(added) == ["N3 phrase 'a new one' has no carrier"]
    reworded = _spec_root(tmp_path / "reworded", ", or skip the orphan check |", ", or skip the orphan checks |")
    assert sorted(sm.carrier_problems(reworded)) == ["N11 carrier 'skip the orphan check' has no phrase in the spec",
                                                     "N11 phrase 'skip the orphan checks' has no carrier"]
    unread = _spec_root(tmp_path / "unread", sm.TABLE_HEADER, "| # | cell | expected | mutant |")
    assert [p for p in sm.carrier_problems(unread) if "cannot be read" in p and "occurs 0 time(s)" in p]


def test_the_same_takes_its_referents_carrier_and_refuses_when_ambiguous(tmp_path, monkeypatch):
    ambiguous = _spec_root(tmp_path / "amb", "| widen (b2) to every index |", "| the same |")    # N2 has two phrases
    assert [p for p in sm.carrier_problems(ambiguous) if "'the same' needs a previous row with exactly one phrase" in p]
    monkeypatch.setattr(sm, "CARRIERS", {**sm.CARRIERS, ("N14", "the same"): ("mutant", "N11-orphans-skipped")})
    probs = sm.carrier_problems()
    assert ("N14 phrase 'the same' is the same mutant as N13's 'forward every name the proxy does not list to the "
            "real connection' but has another carrier") in probs, probs
    assert "N14 phrase 'the same': its carrier 'N11-orphans-skipped' names no N14 cell" in probs, probs


def test_a_carrier_that_does_not_resolve_fails(monkeypatch):
    k = ("N1", "admit every statement at a declared class-(b) site")
    monkeypatch.setattr(sm, "CARRIERS", {**sm.CARRIERS, k: ("mutant", "a row nobody wrote")})
    assert sm.carrier_problems() == [f"N1 phrase {k[1]!r}: no mutant 'a row nobody wrote' in this table"]
    monkeypatch.setattr(sm, "CARRIERS", {**sm.CARRIERS, k: ("absent", "why", f"{sm.CELLS_FILE}::test_nobody_wrote")})
    assert sm.carrier_problems() == [f"N1 phrase {k[1]!r}: the ABSENT cell {sm.CELLS_FILE}::test_nobody_wrote is not a "
                                     f"test in {sm.CELLS_FILE}"]
    cell = f"{sm.CELLS_FILE}::test_n1_the_reviewers_drop_and_recreate_at_a_declared_site_is_refused"
    monkeypatch.setattr(sm, "CARRIERS", {**sm.CARRIERS, k: ("absent", "why", cell)})
    assert sm.carrier_problems() == []                           # the control: an ABSENT carrier whose cell exists
    monkeypatch.setattr(sm, "CARRIERS", {**sm.CARRIERS, k: ("cite", "x")})
    assert sm.carrier_problems() == [f"N1 phrase {k[1]!r}: carrier ('cite', 'x') is not ('mutant', id) or "
                                     f"('absent', reason, cell)"]
