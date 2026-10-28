"""0013 §5f.3's finite acceptance matrix, A1–A16 and P1–P3: its mutation table, specs/evidence/0013/a_matrix_mutants.py.

The table is current and every row good; the spec's mutant PHRASES equal the table's carriers in both directions (a
phrase the spec gains or loses fails by name, not by review), each mutant names its own row's case cells, and the table
check refuses each tampered table.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(name="veracium_a_matrix_mutants"):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "specs" / "evidence" / "0013" / "a_matrix_mutants.py")
        m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return sys.modules[name]


am = _load()


def test_the_mutation_table_is_current_and_every_row_good():
    assert am.problems() == []


def test_every_spec_mutant_phrase_has_exactly_one_carrier():
    """The complement check: the phrases §5f.3's table names EQUAL the carriers' keys, and each carrier resolves.
    Read from the spec's bytes, never from a list typed beside them: 22 phrases over the 19 rows A1–A16, P1–P3."""
    ph = am.phrases()
    rows = {f"A{i}" for i in range(1, 17)} | {"P1", "P2", "P3"}
    assert {k[0] for k in ph} == rows, sorted({k[0] for k in ph})
    assert len(ph) == 22, sorted(ph)
    assert ph[("A2", 0)] == "— (control)" and am.CARRIERS[("A2", 0)][0] == "control"
    assert ph[("A12", 1)] == "as a pass" and ph[("P3", 1)] == "pass `require_stamp=False` on one"
    assert am.carrier_problems() == []


def test_a_phrase_without_a_carrier_or_a_carrier_without_a_phrase_fails_by_name(monkeypatch):
    first = sorted(am.CARRIERS)[0]
    monkeypatch.setattr(am, "CARRIERS", {k: v for k, v in am.CARRIERS.items() if k != first})
    assert any(f"{first[0]} phrase {first[1]} has no carrier" in p for p in am.carrier_problems())
    monkeypatch.setattr(am, "CARRIERS", {**am.CARRIERS, ("A1", 9): ("mutant", am.MUTANTS[0][0])})
    assert any("A1 carrier 9 has no phrase" in p for p in am.carrier_problems())


def test_a_spec_that_gains_or_loses_a_phrase_fails_by_name(tmp_path):
    """The same check over an edited copy of the spec: a phrase added to a row (A7 split by "; ") names the new
    phrase; a row deleted names its orphaned carrier."""
    text = (ROOT / am.SPEC).read_text(encoding="utf-8")
    for label, edit, want in (
            ("gained", lambda t: t.replace("| deduplicate silently |", "| deduplicate silently; keep the last |"),
             "A7 phrase 1 has no carrier: 'keep the last'"),
            ("lost", lambda t: "\n".join(ln for ln in t.splitlines() if not ln.startswith("| A15 |")) + "\n",
             "A15 carrier 0 has no phrase in the spec")):
        root = tmp_path / label
        (root / am.SPEC).parent.mkdir(parents=True)
        edited = edit(text)
        assert edited != text, label
        (root / am.SPEC).write_text(edited, encoding="utf-8")
        assert want in am.carrier_problems(root), (label, am.carrier_problems(root))


def test_a_mutant_that_names_only_a_sibling_cell_fails(monkeypatch):
    """Each row's mutant must name its OWN case's cells: A7's mutant re-pointed at A8's cell refuses, naming A7."""
    sibling = am.CASE_CELLS["A8"]
    monkeypatch.setattr(am, "MUTANTS", [m[:4] + (sibling,) + m[5:] if m[0] == "a7-deduplicate-silently" else m
                                        for m in am.MUTANTS])
    assert any(p.startswith("A7 phrase 0: its mutants do not name the row's own case cells") for p in
               am.carrier_problems())


def test_the_control_is_an_honest_probe_and_a_cite_is_refused(monkeypatch):
    """A2's control must be an honest probe of THIS table; and every carrier is a row of this table, so another
    table's citation is not a carrier kind here."""
    monkeypatch.setattr(am, "CARRIERS", {**am.CARRIERS, ("A2", 0): ("control", am.CASE_CELLS["A1"][0])})
    probs = am.carrier_problems()
    assert any("A2 phrase 0: the control cell" in p and "not an honest probe" in p for p in probs), probs
    monkeypatch.setattr(am, "CARRIERS", {**am.CARRIERS, ("A2", 0): ("cite", "specs/evidence/x.py::MUTANTS::y")})
    assert any("carrier kind 'cite' is not mutant/control/absent" in p for p in am.carrier_problems())


def _base():
    t = json.loads(am.TABLE.read_text(encoding="utf-8"))
    t["header"]["digests"] = am._digests(ROOT)
    return t


def _write(tmp_path, t, redigest=True):
    if redigest:
        t["body_sha256"] = hashlib.sha256(am.canonical({k: v for k, v in t.items() if k != "body_sha256"})).hexdigest()
    p = tmp_path / "mutation-table.json"
    p.write_text(am.render(t), encoding="utf-8")
    return p


TAMPERS = {
    "edited after writing": (lambda t: t["rows"][0].__setitem__("what", "edited"), False,
                             "does not match its own body digest"),
    "a row not killed": (lambda t: t["rows"][0].update(outcome="SURVIVED"), True, "not a good row"),
    "a named cell that passed": (lambda t: t["rows"][0].update(cells_failed=[]), True, "not a good row"),
    "an honest probe that failed": (lambda t: t["rows"][0].update(honest="fail: 1 failed, 0 errored of 1"), True,
                                    "not a good row"),
    "a missing row": (lambda t: t["rows"].pop(), True, "the rows are not one per mutant"),
    "a stale digest": (lambda t: t["header"]["digests"].__setitem__(am.MODEL, "0" * 64), True, "stale: "),
    "a changed definition": (lambda t: t["header"]["definitions"].__setitem__(am.MUTANTS[0][0], "0" * 64), True,
                             "the mutant definitions differ"),
    "a red clean run": (lambda t: t["header"]["clean"]["first"].__setitem__("ok", False), True,
                        "the clean runs are not both green"),
    "a classifier control that killed": (lambda t: t["controls"][0].update(outcome="KILLED"), True,
                                         "negative control is not good"),
    "another spec": (lambda t: t["header"].__setitem__("spec", "0007"), True, "not 0013/A1-A16-P1-P3"),
}


def test_the_table_check_refuses_each_tampered_table(tmp_path):
    check = _load().problems                                  # the artifact this matrix binds (P1): a_matrix_mutants.py
    (tmp_path / "control").mkdir()
    assert check(_write(tmp_path / "control", _base())) == []           # the untampered copy passes
    for name, (tamper, redigest, want) in TAMPERS.items():
        t = copy.deepcopy(_base())
        tamper(t)
        d = tmp_path / name.replace(" ", "-")
        d.mkdir()
        probs = check(_write(d, t, redigest))
        assert any(want in p for p in probs), (name, probs)
