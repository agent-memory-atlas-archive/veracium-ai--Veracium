"""The shared kill classifier (specs/evidence/mutation_kinds.py), and its mutation matrix: each rule the module states
is load-bearing — a mutant of the module that drops one rule is caught by the case that rule exists for."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULE = ROOT / "specs" / "evidence" / "mutation_kinds.py"


def _load(source: str | None = None, name: str = "mutation_kinds_under_test"):
    if source is None:
        spec = importlib.util.spec_from_file_location(name, MODULE)
        m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
        return m
    m = type(sys)(name); exec(compile(source, str(MODULE), "exec"), m.__dict__)
    return m


ADMITS = ("Refused", frozenset({"t.py::test_control_a"}))


def _cases(mk) -> list[str]:
    """Every case the module's rules decide; returns the names of the cases it gets WRONG."""
    k, c = mk.failure_kind, mk.classify
    wrong = []
    def want(name, got, expected):
        if got != expected:
            wrong.append(name)
    want("assert form", k("assert (1 == 0)"), "assertion")
    want("AssertionError form", k("AssertionError: the hotfix must permit x; it was refused: refused: y"), "assertion")
    want("DID NOT RAISE", k("Failed: DID NOT RAISE <class 'ValueError'>"), "expected-refusal-missing")
    want("pytest.fail is not a kill kind", k("Failed: an explicit pytest.fail"), "other: Failed")
    want("escaping domain refusal", k("ValueError: refused: imported edge 'e'"), "other: ValueError")
    want("unrelated TypeError", k("TypeError: unsupported operand"), "other: TypeError")
    want("KeyError (0043 R5-04a's form)", k("KeyError: ('q013', 'veracium')"), "other: KeyError")
    want("empty message", k(""), "other: <no message>")
    want("one qualifying cell kills", c({"a": "assertion"}, ["a"], [])["outcome"], "KILLED")
    want("an other beside a qualifying cell is UNCLASSIFIED",
         c({"a": "assertion", "b": "other: TypeError"}, ["a", "b"], [])["outcome"], "UNCLASSIFIED")
    want("a failing cell with no recorded kind is UNCLASSIFIED", c({"a": "assertion"}, ["a", "b"], [])["outcome"], "UNCLASSIFIED")
    want("an error beats everything", c({"a": "assertion"}, ["a"], ["e"])["outcome"], "ERROR")
    want("no failure survives", c({}, [], [])["outcome"], "SURVIVED")
    want("kill kinds joined", c({"a": "assertion", "b": "expected-refusal-missing"}, ["a", "b"], [])["kill_kind"],
         "assertion+expected-refusal-missing")
    refused = {"t.py::test_control_a": "other: r701_run_harness.Refused"}
    want("a declared refusal on a declared cell kills a fail-closed row",
         c(refused, list(refused), [], admits=ADMITS)["outcome"], "KILLED")
    want("the same refusal without a declaration is UNCLASSIFIED", c(refused, list(refused), [])["outcome"], "UNCLASSIFIED")
    elsewhere = {"t.py::test_other": "other: r701_run_harness.Refused"}
    want("a declared refusal on an UNDECLARED cell is UNCLASSIFIED",
         c(elsewhere, list(elsewhere), [], admits=ADMITS)["outcome"], "UNCLASSIFIED")
    wrongtype = {"t.py::test_control_a": "other: KeyError"}
    want("an undeclared type on a declared cell is UNCLASSIFIED",
         c(wrongtype, list(wrongtype), [], admits=ADMITS)["outcome"], "UNCLASSIFIED")
    lookalike = {"t.py::test_control_a": "other: NotRefused"}
    want("a name merely ending in the suffix is not the declared type",
         c(lookalike, list(lookalike), [], admits=ADMITS)["outcome"], "UNCLASSIFIED")
    want("the recorded kinds are the RAW observation",
         c(refused, list(refused), [], admits=ADMITS)["cell_kinds"], refused)
    return wrong


def test_the_classifier_decides_every_case_its_rules_state():
    assert _cases(_load()) == []


# (name, the exact text replaced, the replacement, a case that must now be decided wrongly)
MUTANTS = [
    ("pytest.fail counted as a refusal check", 'if m.startswith("Failed: DID NOT RAISE"):', 'if m.startswith("Failed"):',
     "pytest.fail is not a kill kind"),
    ("every JUnit failure an assertion (the IO-II-7 runner)", '    if m.startswith("AssertionError") or m.startswith("assert "):\n        return "assertion"',
     '    if True:\n        return "assertion"', "escaping domain refusal"),
    ("an other beside a qualifying cell tolerated", "elif other or not qual or set(kinds) != set(failed):",
     "elif not qual or set(kinds) != set(failed):", "an other beside a qualifying cell is UNCLASSIFIED"),
    ("unrecorded failing cells tolerated", "elif other or not qual or set(kinds) != set(failed):",
     "elif other or not qual:", "a failing cell with no recorded kind is UNCLASSIFIED"),
    ("admission on any cell", "    if node in cells and (name == suffix or name.endswith(\".\" + suffix)):",
     "    if (name == suffix or name.endswith(\".\" + suffix)):", "a declared refusal on an UNDECLARED cell is UNCLASSIFIED"),
    ("admission by bare suffix", 'name.endswith("." + suffix)', "name.endswith(suffix)",
     "a name merely ending in the suffix is not the declared type"),
    ("admission without a declaration", '    ok = set(QUALIFYING) | ({DECLARED} if admits else set())',
     '    ok = set(QUALIFYING) | {DECLARED, "other: r701_run_harness.Refused"}', "the same refusal without a declaration is UNCLASSIFIED"),
    ("the admitted kind recorded instead of the observed one", '"cell_kinds": dict(sorted(kinds.items())),',
     '"cell_kinds": dict(sorted(eff.items())),', "the recorded kinds are the RAW observation"),
]


def test_each_rule_of_the_classifier_is_load_bearing():
    """The module's mutation matrix: each mutant reintroduces one weakening, and the case that rule exists for catches
    it. A mutant whose anchor is not found exactly once fails loudly (the matrix cannot silently go stale)."""
    text = MODULE.read_text(encoding="utf-8")
    assert _cases(_load()) == []                                           # control: the module itself is right
    for name, anchor, repl, case in MUTANTS:
        assert text.count(anchor) == 1, f"{name}: its anchor occurs {text.count(anchor)} times"
        wrong = _cases(_load(text.replace(anchor, repl), name="mk_mutant"))
        assert case in wrong, f"mutant '{name}' was not caught by '{case}' (wrong: {wrong})"
    assert _cases(_load()) == []                                           # control after: nothing leaked
