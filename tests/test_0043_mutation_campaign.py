"""specs/0043 — the mechanism mutation table (specs/evidence/0043/mutation_campaign.py): current, every row good, refused
when tampered, and one row REPRODUCED here every suite run, so CI re-executes part of the claim rather than only
reading it (research's stage-1, 2026-10-10)."""
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


camp = _load(ROOT / "specs" / "evidence" / "0043" / "mutation_campaign.py", "camp_test")


def _table():
    return json.loads(camp.TABLE.read_text(encoding="utf-8"))


def test_the_mutation_table_is_current_and_every_row_is_good():
    assert camp.problems() == []
    t = _table()
    assert t["summary"]["rows"] == len(camp.MUTANTS) == t["summary"]["good"] and t["summary"]["survived"] == 0
    assert {r["id"] for r in t["rows"] if r["kind"] == "fail-closed"} == camp.FAIL_CLOSED


def _rebound(t):
    body = {k: v for k, v in t.items() if k != "body_sha256"}
    return {**body, "body_sha256": hashlib.sha256(camp.canonical(body)).hexdigest()}


def test_mutation_table_check_refuses_each_tampered_table(tmp_path):
    """The Mutation-Matrix of specs/evidence/0043/mutation_campaign.py: each tampering of mutation-table.json is refused
    by its `problems` (what `--check` runs), with the reason that names it."""
    good = _table()
    first_disc = next(i for i, r in enumerate(good["rows"]) if r["kind"] == "discriminating")
    fc = next(i for i, r in enumerate(good["rows"]) if r["kind"] == "fail-closed")

    def edited(fn):
        t = copy.deepcopy(good); fn(t); return t

    cases = {
        "a row's outcome edited, digest kept": (edited(lambda t: t["rows"][0].update(outcome="SURVIVED")), "own body"),
        "a row SURVIVED, rebound": (_rebound(edited(lambda t: t["rows"][first_disc].update(outcome="SURVIVED", good=False))), "not a good row"),
        "a kill by error, rebound": (_rebound(edited(lambda t: t["rows"][first_disc].update(kill_kind="error"))), "not a good row"),
        "a discriminating row whose honest data refused, rebound": (_rebound(edited(lambda t: t["rows"][first_disc].update(honest="fail: 24 committed pair(s) refused"))), "not a good row"),
        "the fail-closed row passing honest data, rebound": (_rebound(edited(lambda t: t["rows"][fc].update(honest="pass"))), "not a good row"),
        "the fail-closed row's kind flipped, rebound": (_rebound(edited(lambda t: t["rows"][fc].update(kind="discriminating"))), "not the declared one"),
        "a row dropped, rebound": (_rebound(edited(lambda t: t["rows"].pop())), "one per mutant"),
        "a definition digest changed, rebound": (_rebound(edited(lambda t: t["header"]["definitions"].update({good["rows"][0]["id"]: "0" * 64}))), "definitions differ"),
        "a finding's cell list edited, rebound": (_rebound(edited(lambda t: t["header"]["cells"].update(
            {next(iter(good["header"]["cells"])): good["header"]["cells"][next(iter(good["header"]["cells"]))][1:]}))), "closure cells"),
        "a source digest changed, rebound":(_rebound(edited(lambda t: t["header"]["digests"].update({next(iter(good["header"]["digests"])): "0" * 64}))), "stale"),
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


def _is_checkout():
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.returncode == 0 and pathlib.Path(r.stdout.strip()).resolve() == ROOT.resolve()


@pytest.mark.skipif(not _is_checkout(), reason="the campaign snapshots the TRACKED tree (git ls-files); a git-less copy has none")
def test_the_first_row_reproduces_in_this_run():
    """A fixed rule picks the row (the first), so it cannot be chosen for passing: re-run here, its outcome, kill kind,
    import, honest probe and failing cells must equal the table's."""
    want = _table()["rows"][0]
    m = camp.MUTANTS[0]
    assert want["id"] == m[0]
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        camp._snapshot(root)
        if m[5] == "reader":
            assert camp._honest(root, "reader-reference") == "pass"
        got = camp.run_one(root, m, camp.cells()[m[1]])
    for k in ("outcome", "kill_kind", "import", "honest", "kind", "good", "cells_failed", "cells_errored"):
        assert got[k] == want[k], (k, got[k], want[k])
