"""specs/0041 — the notice-binding hotfix's mutation table (specs/evidence/0041/mutation_campaign.py; internal finding
0041-PA1 under the 2026-10-10 closure-mutant rule): current, every row good, refused when tampered, and one row
REPRODUCED here every suite run, so CI re-executes part of the claim rather than only reading it (0043's pattern)."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


camp = _load(ROOT / "specs" / "evidence" / "0041" / "mutation_campaign.py", "camp41_test")


def _table():
    return json.loads(camp.TABLE.read_text(encoding="utf-8"))


def test_the_mutation_table_is_current_and_every_row_is_good():
    assert camp.problems() == []
    t = _table()
    assert t["summary"]["rows"] == len(camp.MUTANTS) == t["summary"]["good"] and t["summary"]["survived"] == 0


def _rebound(t):
    body = {k: v for k, v in t.items() if k != "body_sha256"}
    return {**body, "body_sha256": hashlib.sha256(camp.canonical(body)).hexdigest()}


def test_mutation_table_check_refuses_each_tampered_table(tmp_path):
    """The Mutation-Matrix of specs/evidence/0041/mutation_campaign.py: each tampering of mutation-table.json is refused
    by its `problems` (what `--check` runs), with the reason that names it."""
    good = _table()

    def edited(fn):
        t = copy.deepcopy(good); fn(t); return t

    first_cells_key = next(iter(good["header"]["cells"]))
    cases = {
        "a row's outcome edited, digest kept": (edited(lambda t: t["rows"][0].update(outcome="SURVIVED")), "own body digest"),
        "a row SURVIVED, rebound": (_rebound(edited(lambda t: t["rows"][0].update(outcome="SURVIVED", good=False))), "not a good row"),
        "a kill by error, rebound": (_rebound(edited(lambda t: t["rows"][0].update(kill_kind="error"))), "not a good row"),
        "a row whose honest flows broke, rebound": (_rebound(edited(lambda t: t["rows"][0].update(honest="fail: 1 failed, 0 errored of 4"))), "not a good row"),
        "a row whose cells errored, rebound": (_rebound(edited(lambda t: t["rows"][0].update(cells_errored=["x::y"]))), "not a good row"),
        "a KILLED row with no failing cell, rebound": (_rebound(edited(lambda t: t["rows"][0].update(cells_failed=[]))), "not a good row"),
        "a KILLED row failing a cell it does not cite, rebound": (_rebound(edited(lambda t: t["rows"][0].update(cells_failed=["tests/x.py::not_cited"]))), "not a good row"),
        "a row dropped, rebound": (_rebound(edited(lambda t: t["rows"].pop())), "one per mutant"),
        # round-4 IO-II-7: the kill is recounted from the recorded cell kinds, and the classifier's controls are checked
        "a cell's kind edited to an unrelated exception, rebound": (_rebound(edited(lambda t: t["rows"][0]["cell_kinds"].update(
            {next(iter(t["rows"][0]["cell_kinds"])): "other: TypeError"}))), "recounted from its cell kinds UNCLASSIFIED"),
        "a row's cell kinds dropped, rebound": (_rebound(edited(lambda t: t["rows"][0].update(cell_kinds={}))), "not a good row"),
        "a kill kind that disagrees with the cell kinds, rebound": (_rebound(edited(lambda t: t["rows"][0].update(
            kill_kind="expected-refusal-missing"))), "not a good row"),
        "a control read KILLED, rebound": (_rebound(edited(lambda t: t["controls"][0].update(outcome="KILLED"))), "negative control is not good"),
        "a control's unrelated failures reclassified as assertions, rebound": (_rebound(edited(lambda t: t["controls"][0].update(
            cell_kinds={k: "assertion" for k in t["controls"][0]["cell_kinds"]}))), "negative control is not good"),
        "a control dropped, rebound": (_rebound(edited(lambda t: t["controls"].pop())), "one per CONTROLS entry"),
        "a control definition changed, rebound": (_rebound(edited(lambda t: t["header"]["control_definitions"].update(
            {good["controls"][0]["id"]: "0" * 64}))), "control definitions differ"),
        "the spec changed, rebound": (_rebound(edited(lambda t: t["header"].update(spec="0043"))), "not 0041"),
        "a definition digest changed, rebound": (_rebound(edited(lambda t: t["header"]["definitions"].update({good["rows"][0]["id"]: "0" * 64}))), "definitions differ"),
        "the finding's cell list edited, rebound": (_rebound(edited(lambda t: t["header"]["cells"].update(
            {first_cells_key: good["header"]["cells"][first_cells_key][1:]}))), "closure cells"),
        "the honest nodes edited, rebound": (_rebound(edited(lambda t: t["header"].update(honest_nodes=good["header"]["honest_nodes"][1:]))), "honest nodes"),
        "a source digest changed, rebound": (_rebound(edited(lambda t: t["header"]["digests"].update({next(iter(good["header"]["digests"])): "0" * 64}))), "stale"),
    }
    f = tmp_path / "mutation-table.json"
    for name, (t, reason) in cases.items():
        text = camp.render(t)
        assert text != camp.TABLE.read_text(encoding="utf-8"), name             # the tampering changed the bytes
        f.write_text(text, encoding="utf-8")
        found = camp.problems(f)
        assert any(reason in p for p in found), (name, found)
    assert any("not JSON" in p for p in (f.write_text("{"), camp.problems(f))[1])
    dup = '{"body_sha256": "x", ' + camp.TABLE.read_text(encoding="utf-8")[1:]                 # strict decoder: refused
    assert any("duplicate key" in p for p in (f.write_text(dup), camp.problems(f))[1])
    assert any("does not exist" in p for p in camp.problems(tmp_path / "absent.json"))
    f.write_text(camp.TABLE.read_text(encoding="utf-8"), encoding="utf-8")
    assert camp.problems(f) == []                                                  # control: an untouched copy passes


def test_the_classifier_reads_each_failure_kind():
    """IO-II-7's classifier, on the JUnit message forms it must tell apart (a bare unit check; the table's controls run
    the injected failures for real)."""
    k = camp.failure_kind
    assert k("AssertionError: the hotfix must permit x; it was refused: refused: y") == "assertion"
    assert k("assert (1 == 0)") == "assertion"
    assert k("Failed: DID NOT RAISE <class 'ValueError'>") == "expected-refusal-missing"
    assert k("ValueError: refused: imported edge 'e' arrives") == "other: ValueError"
    assert k("TypeError: unsupported operand") == "other: TypeError"
    assert k("Failed: an explicit pytest.fail") == "other: Failed"
    assert k("") == "other: <no message>"
    kinds = {"a": "assertion", "b": "other: TypeError"}
    assert camp.classify({"kinds": kinds, "failed": ["a", "b"], "errored": []})["outcome"] == "UNCLASSIFIED"
    assert camp.classify({"kinds": {"a": "assertion"}, "failed": ["a"], "errored": []})["outcome"] == "KILLED"
    assert camp.classify({"kinds": {"a": "assertion"}, "failed": ["a", "b"], "errored": []})["outcome"] == "UNCLASSIFIED"
    assert camp.classify({"kinds": {}, "failed": [], "errored": ["e"]})["outcome"] == "ERROR"


def _is_checkout():
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.returncode == 0 and pathlib.Path(r.stdout.strip()).resolve() == ROOT.resolve()


@pytest.mark.skipif(not _is_checkout(), reason="the campaign snapshots the TRACKED tree (git ls-files); a git-less copy has none")
def test_the_first_row_reproduces_in_this_run():
    """A fixed rule picks the row (the first), so it cannot be chosen for passing: re-run here, its outcome, kill kind,
    import, honest flows and failing cells must equal the table's."""
    want = _table()["rows"][0]
    m = camp.MUTANTS[0]
    assert want["id"] == m[0]
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        camp._snapshot(root)
        got = camp.run_one(root, m, camp.cells()[m[1]])
    for k in ("outcome", "kill_kind", "import", "honest", "good", "cells_failed", "cells_errored", "cell_kinds"):
        assert got[k] == want[k], (k, got[k], want[k])
