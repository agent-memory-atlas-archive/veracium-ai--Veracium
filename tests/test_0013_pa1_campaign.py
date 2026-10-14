"""specs/evidence/0013/pa1_campaign.py — the 0013-PA1 mutation table is current and every row good; its `--check`
refuses each tampering (the runner's Mutation-Matrix); the first code mutant re-runs here."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    name = "veracium_pa1_campaign"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "specs" / "evidence" / "0013" / "pa1_campaign.py")
        m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return sys.modules[name]


camp = _load()


def _table():
    return json.loads(camp.TABLE.read_text(encoding="utf-8"))


def _rebound(t):
    body = {k: v for k, v in t.items() if k != "body_sha256"}
    return {**body, "body_sha256": hashlib.sha256(camp.canonical(body)).hexdigest()}


def test_the_pa1_table_is_current_and_every_row_good():
    assert camp.problems() == []
    t = _table()
    s = t["summary"]
    assert s["rows"] == len(camp.MUTANTS) == s["good"] == s["killed"]
    assert s["controls"] == len(camp.CONTROLS) == s["controls_good"]
    assert s["perturbations"] == s["perturbations_killed"] + s["perturbations_not_applicable"]
    # the only not-applicable cells are the v16 registry backfill on a BASE-1 store: no confirmation exists to copy,
    # so the write changes 0 rows and every perturbation of it is n/a (the step table's own "wrote no row") or
    # equivalent (a skip of a 0-row write). Anywhere else an n/a is a perturbation that did not land.
    na = [r for r in t["perturbations"] if r.get("killed") is None]
    assert len(na) == s["perturbations_not_applicable"]
    assert {(r["step"], r["path"].split("-")[0]) for r in na} <= {("v16-registry-backfill", "v1#0")}, na
    import veracium.store.migration as mig
    writing = {v for k, v in vars(mig).items() if k.startswith("STEP_") and isinstance(v, str)} - set(camp.WRITELESS_STEPS)
    assert set(s["per_step"]) == writing == {"stamp", "store-identity", "store-epoch", "v13-baseline",
                                             "v2-v3-outcome-chains", "v3-v4-wiki-drop", "v16-act-counter",
                                             "v16-registry-backfill"}


def test_pa1_table_check_refuses_each_tampered_table(tmp_path):
    """The Mutation-Matrix of specs/evidence/0013/pa1_campaign.py: each tampering of mutation-table.json is refused
    by its `problems` (what `--check` runs), with the reason that names it."""
    good = _table()

    def edited(fn):
        t = copy.deepcopy(good); fn(t); return t

    def p0(t, **kw):
        t["perturbations"][0].update(kw)

    cases = {
        "a row's outcome edited, digest kept": (edited(lambda t: t["rows"][0].update(outcome="SURVIVED")), "own body digest"),
        "a row SURVIVED, rebound": (_rebound(edited(lambda t: t["rows"][0].update(outcome="SURVIVED", good=False))), "not a good row"),
        "a row whose honest flows broke, rebound": (_rebound(edited(lambda t: t["rows"][0].update(honest="fail: 1 failed, 0 errored of 2"))), "not a good row"),
        "a row's cell kinds edited to an unrelated exception, rebound": (_rebound(edited(lambda t: t["rows"][0]["cell_kinds"].update(
            {next(iter(t["rows"][0]["cell_kinds"])): "other: TypeError"}))), "recounted from its cell kinds UNCLASSIFIED"),
        "a row killed by some cell but not its named one, rebound": (_rebound(edited(lambda t: t["rows"][0].update(killer_failed=False))), "not a good row"),
        "a row dropped, rebound": (_rebound(edited(lambda t: t["rows"].pop())), "one per mutant"),
        "a control read KILLED, rebound": (_rebound(edited(lambda t: t["controls"][0].update(outcome="KILLED"))), "negative control is not good"),
        "a control dropped, rebound": (_rebound(edited(lambda t: t["controls"].pop())), "one per CONTROLS entry"),
        "a definition digest changed, rebound": (_rebound(edited(lambda t: t["header"]["definitions"].update({good["rows"][0]["id"]: "0" * 64}))), "definitions differ"),
        "the closure cells edited, rebound": (_rebound(edited(lambda t: t["header"]["cells"].update(
            {camp.FINDING: good["header"]["cells"][camp.FINDING][1:]}))), "closure cells differ"),
        "a row's finding edited, rebound": (_rebound(edited(lambda t: t["rows"][0].update(finding="0013-X"))), "not 0013-PA1"),
        "a source digest changed, rebound": (_rebound(edited(lambda t: t["header"]["digests"].update({camp.MIGRATION: "0" * 64}))), "stale"),
        "a perturbation refused at the wrong step, rebound": (_rebound(edited(lambda t: p0(t, refused_at_step=False, killed=False))), "not killed"),
        "a perturbation refused after a later step wrote, rebound": (_rebound(edited(lambda t: p0(t, position=False, killed=False))), "not killed"),
        "a perturbation whose refusal changed the store, rebound": (_rebound(edited(lambda t: p0(t, unchanged=False, killed=False))), "not killed"),
        "a perturbation claimed killed with a failed condition, rebound": (_rebound(edited(lambda t: p0(t, position=False))), "not killed"),
        "a step's perturbations dropped, rebound": (_rebound(edited(lambda t: t.update(perturbations=[
            r for r in t["perturbations"] if r["step"] != "v3-v4-wiki-drop"]))), "not every writing step"),
    }
    f = tmp_path / "mutation-table.json"
    for name, (t, reason) in cases.items():
        text = camp.render(t)
        assert text != camp.TABLE.read_text(encoding="utf-8"), name
        f.write_text(text, encoding="utf-8")
        found = camp.problems(f)
        assert any(reason in p for p in found), (name, found)
    assert any("not JSON" in p for p in (f.write_text("{"), camp.problems(f))[1])
    dup = '{"body_sha256": "x", ' + camp.TABLE.read_text(encoding="utf-8")[1:]
    assert any("duplicate key" in p for p in (f.write_text(dup), camp.problems(f))[1])
    assert any("does not exist" in p for p in camp.problems(tmp_path / "absent.json"))
    f.write_text(camp.TABLE.read_text(encoding="utf-8"), encoding="utf-8")
    assert camp.problems(f) == []                                                  # control: an untouched copy passes


def _is_checkout():
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.returncode == 0 and pathlib.Path(r.stdout.strip()).resolve() == ROOT.resolve()


@pytest.mark.skipif(not _is_checkout(), reason="the campaign snapshots the tree through git ls-files; a git-less copy has none")
def test_the_first_code_mutant_reproduces_in_this_run():
    """A fixed rule picks the row (the first), so it cannot be chosen for passing: re-run here, its outcome, kill kind,
    import, honest flows and failing cells must equal the table's."""
    want = _table()["rows"][0]
    m = camp.MUTANTS[0]
    assert want["id"] == m[0]
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        camp._snapshot(root)
        got = camp.run_one(root, m, camp.kill_cells())
    for k in ("outcome", "kill_kind", "import", "honest", "good", "cells_failed", "cells_errored", "cell_kinds",
              "killer_failed"):
        assert got[k] == want[k], (k, got[k], want[k])
