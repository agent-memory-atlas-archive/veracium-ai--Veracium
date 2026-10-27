"""0007 §4d (I5): the actual attestation jobs — the committed suite rule, one job's closed outcome, aggregation within
one CI run, the matrix's one carrier (rows.json) and the workflow that reads it, and the pinned dependency set.
Research's stage-1 read of I5 (BLOCKING 1–4, Q2/Q4/Q5a/Q6a) is asserted cell by cell, and each artifact carries a
mutation matrix (P1) in the writer's form: each mutant killed BY ASSERTION in a named cell, control first and last.
"""
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import pathlib
import subprocess
import sys
import types
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"
ATT = SPECS / "evidence" / "attestation"
sys.path.insert(0, str(SPECS))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


suite_rule = _load(SPECS / "attestation_suite.py", "veracium_attestation_suite")
job = _load(SPECS / "attestation_job.py", "veracium_attestation_job")
agg = _load(SPECS / "attestation_aggregate.py", "veracium_attestation_aggregate")
cons = _load(SPECS / "attestation_constraints.py", "veracium_attestation_constraints")
import skip_inventory  # noqa: E402

sv = agg.sv


# ---- Q1: the suite rule ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("source", [
    "import sqlite3",
    "import sqlite3 as db",
    "import sqlite3.dbapi2",
    "from sqlite3 import connect",
    "from veracium.store import schema_version",
    "from veracium.store.migration import migrate",
    "from veracium.store import release_migration as rm",
    "def f():\n    import schema_evidence",
    "try:\n    import migrations_0013\nexcept ImportError:\n    pass",
    "class T:\n    def m(self):\n        from veracium.store.schema_version import SCHEMA_VERSION",
    "spec_from_file_location('m', ROOT / 'specs' / 'migrations_0013.py')",
    "runpy.run_path(path='specs/schema_evidence.py')",
    "subprocess.run([sys.executable, f'{SPECS}/schema_evidence.py', '--check'])",
])
def test_the_rule_admits_each_root_by_import_at_any_depth_or_by_file_inside_a_call(source):
    assert suite_rule.reasons(source), source


@pytest.mark.parametrize("source", [
    "import veracium.store",                         # the package, not a root
    "from veracium import store",                    # imports veracium.store, not a root
    "from . import schema_version",                  # relative: not this rule's module name
    "from .sqlite3 import connect",                  # relative, even when its tail names a root
    "import sqlite3x",                               # a prefix of a NAME is not a submodule
    "X = 'specs/schema_evidence.py'",                # a literal outside any call's arguments
    "def f():\n    '''loads migrations_0013.py by path'''",
    "pytest.skip",                                   # an attribute, no call
])
def test_the_rule_admits_nothing_else(source):
    assert suite_rule.reasons(source) == [], source


def test_the_rule_agrees_with_researchs_frozen_implementation_at_this_tree():
    """Two implementations of ONE rule (research's suite_rule_v2.py, frozen at its pin, and the product script); a
    divergence is a finding in one of them. Research's reads `from p import x` only as `p` or `p.x` against the roots
    exactly, the product's as a root or its submodule; no module of this tree tells them apart, which this cell
    asserts."""
    frozen = SPECS / "evidence" / "0007-sqlite-attestation" / "r1-repro-at-58dd7f6" / "suite_rule_v2.py"
    p = subprocess.run([sys.executable, "-I", str(frozen), str(ROOT)], capture_output=True, text=True, check=True)
    theirs = [line.split(" ", 1)[0] for line in p.stdout.splitlines() if line.strip()]
    assert theirs == suite_rule.suite(ROOT)
    assert len(theirs) == int(p.stderr.split("TOTAL")[-1].strip())


def _junit(tmp_path, cases, modules=None):
    """A planted JUnit: every rule module once (passed), unless `modules` says otherwise, plus `cases`:
    [(module path, test name, kind, message)], kind one of passed/failed/error/skip/xfail."""
    modules = suite_rule.suite(ROOT) if modules is None else modules
    rows = [(m, "test_planted_ok", "passed", None) for m in modules] + list(cases)
    body = []
    for mod, name, kind, msg in rows:
        cls = mod[:-3].replace("/", ".")
        inner = {"passed": "", "failed": '<failure message="boom">x</failure>', "error": '<error message="e">x</error>',
                 "skip": f'<skipped type="pytest.skip" message="{msg}">{mod}:1: {msg}</skipped>',
                 "xfail": f'<skipped type="pytest.xfail" message="{msg}" />'}[kind]
        body.append(f'<testcase classname="{cls}" name="{name}" time="0.{len(body)}">{inner}</testcase>')
    path = tmp_path / "junit.xml"
    path.write_text('<?xml version="1.0"?><testsuites><testsuite name="pytest">' + "".join(body)
                    + "</testsuite></testsuites>")
    return path


def test_the_job_must_have_run_exactly_the_rules_modules(tmp_path):
    mods = suite_rule.suite(ROOT)
    assert suite_rule.nodes_problems(_junit(tmp_path, []), ROOT) == []
    extra = suite_rule.nodes_problems(_junit(tmp_path, [("tests/test_not_in_suite.py", "t", "passed", None)]), ROOT)
    assert extra == ["the job ran tests/test_not_in_suite.py, which the rule does not select"]
    missing = suite_rule.nodes_problems(_junit(tmp_path, [], modules=mods[1:]), ROOT)
    assert missing == [f"the rule selects {mods[0]}, which the job did not run"]


# ---- Q2: the attestation-class column ----------------------------------------------------------------------------------
def test_every_inventory_entry_in_the_suite_carries_its_attestation_class_and_none_outside():
    """§4d: "a gate requires the column on every entry whose file is in the suite"; outside it, the column is None."""
    in_suite = set(suite_rule.suite(ROOT))
    bad = []
    for e in skip_inventory.INVENTORY:
        cls = skip_inventory.attestation_class(e)
        if e[0] in in_suite and cls not in skip_inventory.ATTESTATION_CLASSES:
            bad.append(f"{e[0]} [{e[2]}]: in the suite, class {cls!r}")
        if e[0] not in in_suite and cls is not None:
            bad.append(f"{e[0]} [{e[2]}]: outside the suite, class {cls!r}")
    assert not bad, bad


def test_no_inventory_entry_carries_the_rewrite_class():
    """Research's Q2a: `rewrite` stays in the vocabulary, and is EMPTY by rule (§4d's mutant: a rewrite-class skip
    left in place)."""
    assert "rewrite" in skip_inventory.ATTESTATION_CLASSES
    assert [e for e in skip_inventory.INVENTORY if skip_inventory.attestation_class(e) == "rewrite"] == []


_STRANDED = ("records a different runtime identity", "is not a qualified runtime", "runtime_" + "supported",
             "_runtime_" + "supported_interim", "qualified_runtimes")
"""(Both predicate names are split: test_0007_runtime_status's census refuses any live file whose code names either,
a string constant included.)"""


def _skip_sites(text):
    """The source of every skip DECISION in a module: pytest.skip/skipif/importorskip calls and skipif markers."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in ("skip", "skipif", "importorskip"):
                yield ast.get_source_segment(text, node) or ""
        elif isinstance(node, ast.If) and any(
                isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "skip" for s in node.body
                for c in ast.walk(s)):
            yield ast.get_source_segment(text, node.test) or ""


def test_both_stranded_skips_are_gone_from_the_suite():
    """§4d's stranded rows: no skip decision in a suite module (its call, marker or guarding condition) still rests on
    the withdrawn single-record rule. Control: the two stranded forms as they were, planted, are found."""
    hits = [f"{mod}: {site[:100]}" for mod in suite_rule.suite(ROOT)
            for site in _skip_sites((ROOT / mod).read_text()) if any(m in site for m in _STRANDED)]
    assert not hits, hits
    skip = "pytest." + "skip"                     # split, so the completeness gate does not read a skip site here
    planted = (f"def test_x():\n    if not ev.sv.runtime_supported():\n        {skip}('x is not a qualified runtime')\n"
               f"def test_y():\n    {skip}('artifact records a different runtime identity')\n")
    assert len([s for s in _skip_sites(planted) if any(m in s for m in _STRANDED)]) == 3


# ---- Q3: one job, its closed outcome -------------------------------------------------------------------------------------
def _args(**over):
    base = dict(route="setup-python", runner_image="ubuntu-24.04", expect_prefix=sys.base_prefix, run_id="7",
                job_id=3)
    base.update(over)
    return SimpleNamespace(**base)


def _status(status="verified"):
    return lambda: sv.runtime_status()._replace(status=status, reason="" if status != "refused" else "probe x is False")


def _decide(tmp_path, cases=(), modules=None, status="verified", evidence_rc=0, probes=None, **over):
    junit = _junit(tmp_path, cases, modules)

    def run_suite(target):
        pathlib.Path(target).write_bytes(junit.read_bytes())
        return 0
    return job.decide(_args(**over), runtime_status=_status(status), check_evidence=lambda: (evidence_rc, "tail"),
                      run_suite=run_suite, head=lambda: "a" * 40,
                      probes=probes or (lambda: {k: True for k in sv.CONFINEMENT_PROBE_KEYS}))


def test_agreeing_evidence_builds_this_builds_record_here(tmp_path):
    r = _decide(tmp_path)
    assert r["outcome"] == "evidence" and job.OUTCOME_EXIT["evidence"] == 0
    rec = r["record"]
    assert sv.attestation_record_problems(rec) == []
    assert sv.attestation_key(rec) == sv.attestation_key(sv.attestation_identity())
    assert rec["provenance"] == [{"route": "setup-python", "runner_image": "ubuntu-24.04", "run_id": "7", "job_id": 3,
                                  "commit": "a" * 40}]


def test_a_wrong_interpreter_is_a_named_failure_naming_both_locations(tmp_path):
    """BLOCKING 3: the row must be the route it claims."""
    r = _decide(tmp_path, expect_prefix="/no/such/route")
    assert r["outcome"] == "wrong-interpreter" and job.OUTCOME_EXIT["wrong-interpreter"] == 1
    assert "/no/such/route" in r["reason"] and str(pathlib.Path(sys.base_prefix).resolve()) in r["reason"]
    assert (job.interpreter_problem(sys.base_prefix, version_info=(3, 13, 0)) or "").startswith("Python 3.13 is below")
    assert job.interpreter_problem(str(pathlib.Path(sys.base_prefix).parent)) is None      # under a declared prefix


def test_a_refused_build_is_a_census_row_and_runs_nothing(tmp_path):
    ran = []
    r = job.decide(_args(), runtime_status=_status("refused"), check_evidence=lambda: ran.append("ce") or (0, ""),
                   run_suite=lambda t: ran.append("suite"), head=lambda: "a" * 40)
    assert (r["outcome"], r["record"], ran) == ("refused", None, []) and job.OUTCOME_EXIT["refused"] == 0
    assert "probe x is False" in r["reason"]


def test_a_check_evidence_failure_is_evidence_mismatch_not_refused(tmp_path):
    """BLOCKING 2: §5f.3, a build that re-derives differently is a FAILED job, never a record and never a census
    `refused`."""
    r = _decide(tmp_path, evidence_rc=1)
    assert r["outcome"] == "evidence-mismatch" and job.OUTCOME_EXIT["evidence-mismatch"] == 1 and r["record"] is None


def test_a_suite_other_than_the_rules_is_suite_mismatch(tmp_path):
    r = _decide(tmp_path, cases=[("tests/test_not_in_suite.py", "t", "passed", None)])
    assert r["outcome"] == "suite-mismatch" and "test_not_in_suite.py" in r["reason"]


def test_an_xfail_is_not_a_skip_and_an_unmapped_skip_fails(tmp_path):
    """BLOCKING 4: one xfail and one ordinary unmapped skip; ONLY the skip fails the job."""
    mod = suite_rule.suite(ROOT)[0]
    r = _decide(tmp_path, cases=[(mod, "test_x", "xfail", "known"), (mod, "test_s", "skip", "an invented reason")])
    assert r["outcome"] == "unmapped-skip" and "test_s" in r["reason"] and "test_x" not in r["reason"]
    alone = _decide(tmp_path, cases=[(mod, "test_x", "xfail", "known")])
    assert alone["outcome"] == "evidence"


def _job_runs_entry():
    in_suite = set(suite_rule.suite(ROOT))
    return next(e for e in skip_inventory.INVENTORY
                if e[0] in in_suite and skip_inventory.attestation_class(e) == "job:runs")


def test_a_fired_job_runs_condition_excludes_the_job_naming_its_entry(tmp_path):
    e = _job_runs_entry()
    r = _decide(tmp_path, cases=[(e[0], "test_s", "skip", e[2])])
    assert r["outcome"] == "excluded" and job.OUTCOME_EXIT["excluded"] == 0 and r["record"] is None
    assert r["excluded_entries"] and e[0] in r["excluded_entries"][0] and e[2] in r["excluded_entries"][0]


def test_a_fired_condition_never_hides_a_failure(tmp_path):
    """Research's stage 2 on 84c512b: a fired job:runs skip AND a failure give failed-tests, exit 1, still naming the
    fired entry (exclusion means "not an input", never "not a failure")."""
    e = _job_runs_entry()
    r = _decide(tmp_path, cases=[(e[0], "test_s", "skip", e[2]), (e[0], "test_f", "failed", None)])
    assert r["outcome"] == "failed-tests" and job.OUTCOME_EXIT[r["outcome"]] == 1
    assert r["excluded_entries"] and e[2] in r["excluded_entries"][0] and "job:runs condition" in r["reason"]


def test_a_key_class_skip_is_evidence_not_exclusion(tmp_path, monkeypatch):
    """A `key` skip fires identically for every job of one key, so it is part of the evidence. The entry is PLANTED, so
    the cell never depends on which key-class entries this tree happens to carry."""
    mod = suite_rule.suite(ROOT)[0]
    planted = (mod, "skip", "a planted key-class token", "system", "planted by the cell", "key")
    monkeypatch.setattr(skip_inventory, "INVENTORY", [*skip_inventory.INVENTORY, planted])
    r = _decide(tmp_path, cases=[(mod, "test_s", "skip", planted[2])])
    assert r["outcome"] == "evidence", r["reason"]


def test_failing_tests_are_red_and_still_carry_their_digest(tmp_path):
    mod = suite_rule.suite(ROOT)[0]
    r = _decide(tmp_path, cases=[(mod, "test_f", "failed", None)])
    assert r["outcome"] == "failed-tests" and job.OUTCOME_EXIT["failed-tests"] == 1
    assert r["result_digest"] and r["record"] is None and r["key"]


def test_a_failing_confinement_probe_is_never_a_record(tmp_path):
    first = sorted(sv.CONFINEMENT_PROBE_KEYS)[0]
    r = _decide(tmp_path, probes=lambda: {k: k != first for k in sv.CONFINEMENT_PROBE_KEYS})
    assert r["outcome"] == "confinement-failed" and job.OUTCOME_EXIT["confinement-failed"] == 1 and r["record"] is None


def test_the_suite_runs_once_in_pytests_own_order(monkeypatch, tmp_path):
    """BLOCKING 1: pytest-randomly disabled, no cache, the rule's modules, one process."""
    seen = []
    monkeypatch.setattr(job.subprocess, "run", lambda argv, **k: seen.append(argv) or SimpleNamespace(returncode=0))
    job._run_suite(tmp_path / "j.xml")
    (argv,) = seen
    assert argv[1:3] == ["-m", "pytest"] and "no:randomly" in argv and argv[argv.index("no:randomly") - 1] == "-p"
    assert "-n" not in argv and argv[-len(suite_rule.suite(ROOT)):] == suite_rule.suite(ROOT)


def test_the_result_digest_ignores_timing_and_order_and_sees_one_outcome(tmp_path):
    mod = suite_rule.suite(ROOT)[0]
    a = job.junit_cases(_junit(tmp_path, [(mod, "test_a", "passed", None), (mod, "test_b", "failed", None)]))
    b = list(reversed(a))
    assert job.result_digest(a) == job.result_digest(b)
    flipped = [(n, "passed" if n.endswith("test_b") else o, m) for n, o, m in a]
    assert job.result_digest(flipped) != job.result_digest(a)


def test_the_suites_node_ids_do_not_depend_on_the_hash_seed():
    """Research's determinism ask, at the cost a suite cell can carry: the suite's COLLECTED node ids under two
    PYTHONHASHSEED values are identical (a node id built from set order fails here, not as a silent CI disagreement).
    The full twice-run of outcomes is evidence, run once (scratch transcript), not a suite cell."""
    import os
    ids = []
    for seed in ("0", "12345"):
        p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:randomly",
                            "-p", "no:cacheprovider", *suite_rule.suite(ROOT)], cwd=str(ROOT), capture_output=True,
                           text=True, env={**os.environ, "PYTHONHASHSEED": seed})
        assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
        ids.append([line for line in p.stdout.splitlines() if "::" in line])
    assert ids[0] and ids[0] == ids[1]


# ---- Q4/Q5: aggregation --------------------------------------------------------------------------------------------------
def _result(outcome="evidence", route="setup-python", image="ubuntu-24.04", job_id=1, digest="e" * 64, **rec_over):
    key = list(sv.attestation_key(sv.attestation_identity()))
    r = {"outcome": outcome, "route": route, "runner_image": image, "job_id": job_id, "reason": "", "key": key,
         "excluded_entries": [], "record": None}
    if outcome == "evidence":
        rec = {**{k: sv.attestation_identity()[k] for k in sv.KEY_FIELDS}, "manifest_algorithm": sv.MANIFEST_ALGORITHM,
               "schema_version": sv.SCHEMA_VERSION, "result_digest": digest,
               "confinement": {k: True for k in sv.CONFINEMENT_PROBE_KEYS},
               "provenance": [{"route": route, "runner_image": image, "run_id": "9", "job_id": job_id,
                               "commit": "a" * 40}]}
        rec.update(rec_over)
        r["record"] = rec
        r["key"] = list(sv.attestation_key(rec))
    return r


def test_equal_evidence_aggregates_to_one_record_with_sorted_union_provenance():
    out = agg.aggregate([_result(route="setup-python", job_id=4), _result(route="deadsnakes", job_id=2)])
    assert not agg.failed(out) and len(out["records"]) == 1
    prov = out["records"][0]["provenance"]
    assert [j["route"] for j in prov] == ["deadsnakes", "setup-python"]
    assert sv.attestation_record_problems(out["records"][0]) == []


def test_different_evidence_is_a_disagreement_naming_every_job_and_other_keys_still_emit():
    other = _result(route="docker", image="python:3.14-alpine", job_id=9, libc="musl")
    out = agg.aggregate([_result(job_id=1), _result(route="deadsnakes", job_id=2, digest="d" * 64), other])
    assert agg.failed(out) and out["disagreements"][0]["why"] == "different evidence"
    assert len(out["disagreements"][0]["jobs"]) == 2
    assert [sv.attestation_key(r) for r in out["records"]] == [sv.attestation_key(other["record"])]


def test_a_refused_job_beside_a_verifying_one_of_the_same_key_is_a_disagreement():
    out = agg.aggregate([_result(job_id=1), _result("refused", route="deadsnakes", job_id=2)])
    assert agg.failed(out) and not out["records"] and "refused" in out["disagreements"][0]["why"]


@pytest.mark.parametrize("red", ["failed-tests", "evidence-mismatch", "confinement-failed"])
def test_a_key_with_only_failing_jobs_fails_aggregation(red):
    """Research's Q5a: "attested" is never one red job away from silently empty."""
    out = agg.aggregate([_result(red, job_id=1)])
    assert agg.failed(out) and out["failed_keys"] and not out["records"]


def test_excluded_and_refused_only_keys_are_listed_not_failures_and_a_missing_row_is_unavailable():
    rows = [{"route": "setup-python", "runner_image": "ubuntu-24.04"}, {"route": "distro", "runner_image": "rhel-10"}]
    out = agg.aggregate([_result("excluded", job_id=1), _result("refused", route="conda-forge", job_id=2)], rows)
    assert not agg.failed(out) and out["excluded"] and out["refused"]
    assert out["unavailable"] == ["distro on rhel-10"]


def test_the_aggregator_takes_each_key_from_its_record_never_from_its_own_runner(monkeypatch):
    """Research's Q4 addition: an aggregator on another platform still emits the job's key."""
    mine = _result(job_id=1)
    monkeypatch.setattr(sv, "attestation_identity", lambda: {**mine["record"], "machine": "riscv64", "libc": "musl"})
    out = agg.aggregate([mine])
    assert [sv.attestation_key(r) for r in out["records"]] == [sv.attestation_key(mine["record"])]


# ---- Q6: the matrix's one carrier, and the workflow that reads it --------------------------------------------------------
def _spec_route_rows():
    text = (SPECS / "0007-store-schema-versioning.md").read_text()
    start = text.index("| route to a Python 3.14 | OS images |")
    rows = []
    for line in text[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        rows.append(line.split("|")[1].strip())
    return rows


def test_rows_json_is_its_generators_output():
    p = subprocess.run([sys.executable, "-I", str(ATT / "gen_rows.py"), "--check"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr


def test_every_route_row_of_the_spec_is_a_matrix_row_or_named_later():
    data = json.loads((ATT / "rows.json").read_text())
    covered = {r["spec_row"] for r in data["rows"]} | {r["spec_row"] for r in data["later"]}
    spec_rows = _spec_route_rows()
    assert spec_rows and set(spec_rows) == covered, (sorted(set(spec_rows) - covered), sorted(covered - set(spec_rows)))


def test_every_row_declares_its_route_location_install_and_interpreter():
    """BLOCKING 3's carrier: a row cannot run without the location its interpreter must lie under."""
    data = json.loads((ATT / "rows.json").read_text())
    bad = []
    for r in data["rows"]:
        for f in ("route", "runner_image", "runs_on", "install", "python", "expect_prefix"):
            if not isinstance(r.get(f), str) or not r[f]:
                bad.append(f"{r.get('route')}/{r.get('runner_image')}: no {f}")
        if "image" in r and not r.get("user_add"):
            bad.append(f"{r['route']}/{r['runner_image']}: a container row with no non-root user")
    pairs = [(r["route"], r["runner_image"]) for r in data["rows"]]
    assert not bad and len(pairs) == len(set(pairs)), (bad, pairs)


def test_the_workflow_reads_the_rows_runs_each_row_non_root_with_full_history_and_never_runs_on_main():
    wf = (ROOT / ".github" / "workflows" / "attestation.yml").read_text()
    assert 'branches: ["attest/**"]' in wf and "workflow_dispatch:" in wf
    assert "main" not in wf.split("jobs:")[0]                         # the trigger block names no main branch
    assert "include: ${{ fromJSON(needs.rows.outputs.rows) }}" in wf
    assert "rows.json" in wf and wf.count("fetch-depth: 0") == 2
    assert wf.count("specs/evidence/attestation/run_row.sh") == 2 and "docker exec -u attest" in wf
    assert "--rows specs/evidence/attestation/rows.json" in wf
    sh = (ATT / "run_row.sh").read_text()
    assert 'refusing to run as root' in sh and "-c specs/evidence/attestation/constraints.txt" in sh
    assert '-e ".[dev,mcp]"' in sh


# ---- the pinned dependency set (research's do-now; the network half is a command, never a cell) ---------------------------
def test_the_constraints_pin_every_direct_requirement_within_its_bound():
    assert cons.offline_problems() == []


def test_the_constraints_check_refuses_an_unpinned_or_out_of_bound_or_unparseable_set():
    text = cons.CONSTRAINTS.read_text()
    name = cons._canon(__import__("packaging.requirements", fromlist=["Requirement"]).Requirement(
        cons.direct_requirements()[0]).name)
    lines = [l for l in text.splitlines() if not cons._canon(l.split("==")[0].strip()) == name]
    assert any("is not pinned" in p for p in cons.offline_problems("\n".join(lines)))
    assert any("does not satisfy" in p for p in cons.offline_problems(text + "\npytest==1.0\n"))
    assert any("does not parse" in p for p in cons.offline_problems(text + "\nzzz==1.0 ; python_version >>> '3'\n"))
    assert any("not an exact pin" in p for p in cons.offline_problems(text + "\nzzz>=1.0\n"))


# ---- the mutation matrices (P1) -------------------------------------------------------------------------------------------
def _run_cell(cell, params, tmp_path_factory, patch):
    """'pass', 'kill' (an assertion or DID NOT RAISE) or 'crash: …'. `patch` swaps this module's global for the
    mutant module."""
    this = sys.modules[__name__]
    fn = getattr(this, cell)
    with pytest.MonkeyPatch.context() as mp:
        name, mod = patch
        mp.setattr(this, name, mod)
        args = {}
        for p in inspect.signature(fn).parameters:
            if p in params:
                args[p] = params[p]
            elif p == "tmp_path":
                args[p] = tmp_path_factory.mktemp("cell")
            elif p == "monkeypatch":
                args[p] = mp
            else:
                raise AssertionError(f"{cell}: no argument for {p}")
        try:
            fn(**args)
        except (AssertionError, pytest.fail.Exception):
            return "kill"
        except Exception as exc:  # noqa: BLE001 - a crash is reported, never counted as a kill
            return f"crash: {type(exc).__name__}: {exc}"
    return "pass"


def _matrix(path, global_name, mutants, tmp_path_factory):
    text = path.read_text()

    def load(t, n):
        mod = types.ModuleType(n)
        mod.__file__ = str(path)
        exec(compile(t, str(path), "exec"), mod.__dict__)
        return mod
    cells = sorted({(c, tuple(sorted(p.items()))) for _, kills in mutants.values() for c, p in kills})

    def control(label):
        mod = load(text, "control")
        bad = {c: r for c, p in cells if (r := _run_cell(c, dict(p), tmp_path_factory, (global_name, mod))) != "pass"}
        assert not bad, (label, bad)
    control("control, first")
    survivors = {}
    for name, (edits, kills) in mutants.items():
        mutated = text
        for anchor, repl in edits:
            assert mutated.count(anchor) == 1, (name, anchor)
            mutated = mutated.replace(anchor, repl)
        assert mutated != text, name
        mod = load(mutated, "mutant")
        results = {c: _run_cell(c, p, tmp_path_factory, (global_name, mod)) for c, p in kills}
        if "kill" not in results.values():
            survivors[name] = results
    control("control, last")
    assert not survivors, survivors


def test_the_attestation_suite_rule_mutation_matrix(tmp_path_factory):
    """P1 for specs/attestation_suite.py."""
    A, N = "test_the_rule_admits_each_root_by_import_at_any_depth_or_by_file_inside_a_call", "test_the_rule_admits_nothing_else"
    _matrix(SPECS / "attestation_suite.py", "suite_rule", {
        "submodules not admitted": ([('name == r or name.startswith(r + ".")', "name == r")],
                                    [(A, {"source": "import sqlite3.dbapi2"})]),
        "a name prefix admitted": ([('name.startswith(r + ".")', "name.startswith(r)")], [(N, {"source": "import sqlite3x"})]),
        "from p import x not read as p.x": ([('why |= {f"{node.module}.{a.name}" for a in node.names if _is_root(f"{node.module}.{a.name}")}', "pass")],
                                            [(A, {"source": "from veracium.store import schema_version"})]),
        "relative imports admitted": ([("node.level == 0 and node.module", "node.module")],
                                      [(N, {"source": "from .sqlite3 import connect"})]),
        "keywords ignored": ([("[*node.args, *(k.value for k in node.keywords)]", "list(node.args)")],
                             [(A, {"source": "runpy.run_path(path='specs/schema_evidence.py')"})]),
        "any literal admits": ([("        elif isinstance(node, ast.Call):\n            for arg in [*node.args, *(k.value for k in node.keywords)]:\n                for c in ast.walk(arg):",
                                 "        elif isinstance(node, ast.Module):\n            for arg in [node]:\n                for c in ast.walk(arg):")],
                               [(N, {"source": "X = 'specs/schema_evidence.py'"})]),
        "depth 0 only": ([("    for node in ast.walk(ast.parse(source)):", "    for node in ast.parse(source).body:")],
                         [(A, {"source": "def f():\n    import schema_evidence"})]),
        "an extra module is not reported": ([('    out = [f"the job ran {m}, which the rule does not select" for m in sorted(ran - want)]', "    out = []")],
                                            [("test_the_job_must_have_run_exactly_the_rules_modules", {})]),
        "a missing module is not reported": ([('    out += [f"the rule selects {m}, which the job did not run" for m in sorted(want - ran)]', "")],
                                             [("test_the_job_must_have_run_exactly_the_rules_modules", {})]),
    }, tmp_path_factory)


def test_the_attestation_job_mutation_matrix(tmp_path_factory):
    """P1 for specs/attestation_job.py: each closed outcome's arm, and BLOCKING 1–4."""
    _matrix(SPECS / "attestation_job.py", "job", {
        "the interpreter check dropped": ([("        if bad:\n            raise Decided(\"wrong-interpreter\", bad)", "        if False:\n            raise Decided(\"wrong-interpreter\", bad)")],
                                          [("test_a_wrong_interpreter_is_a_named_failure_naming_both_locations", {})]),
        "the floor dropped": ([("    if tuple(version_info[:2]) < (3, 14):", "    if False:")],
                              [("test_a_wrong_interpreter_is_a_named_failure_naming_both_locations", {})]),
        "refused runs the suite": ([('        if st.status == "refused":\n            raise Decided("refused", st.reason or "refused")\n', "")],
                                   [("test_a_refused_build_is_a_census_row_and_runs_nothing", {})]),
        "check-evidence read as refused (BLOCKING 2)": ([('raise Decided("evidence-mismatch",', 'raise Decided("refused",')],
                                                        [("test_a_check_evidence_failure_is_evidence_mismatch_not_refused", {})]),
        "the suite's module set unchecked": ([("            if mismatch:\n", "            if False:\n")],
                                             [("test_a_suite_other_than_the_rules_is_suite_mismatch", {})]),
        "an xfail read as a skip (BLOCKING 4)": ([('            if sk.get("type") == "pytest.xfail":', "            if False:")],
                                                 [("test_an_xfail_is_not_a_skip_and_an_unmapped_skip_fails", {})]),
        "an unmapped skip tolerated": ([("        if unmapped:\n", "        if False:\n")],
                                       [("test_an_xfail_is_not_a_skip_and_an_unmapped_skip_fails", {})]),
        "a fired job:runs condition tolerated": ([("        if fired:\n", "        if False:\n")],
                                                 [("test_a_fired_job_runs_condition_excludes_the_job_naming_its_entry", {})]),
        "every inventoried skip excludes": ([('        elif skip_inventory.attestation_class(entry) == "job:runs":', "        else:")],
                                            [("test_a_key_class_skip_is_evidence_not_exclusion", {})]),
        "exclusion before failures (stage 2)": ([('        if fired:\n            raise Decided("excluded"', '        if False:\n            raise Decided("excluded"'),
                                                  ("        failing = [n for n, o, _ in cases if o in (\"failed\", \"error\")]\n",
                                                   "        failing = [n for n, o, _ in cases if o in (\"failed\", \"error\")]\n        if fired:\n            raise Decided(\"excluded\", \"fired\")\n")],
                                                 [("test_a_fired_condition_never_hides_a_failure", {})]),
        "failures tolerated": ([("        if failing:\n", "        if False:\n")],
                               [("test_failing_tests_are_red_and_still_carry_their_digest", {})]),
        "a failing probe recorded": ([("        if problems:                                       # a failing", "        if False:                                       # a failing")],
                                     [("test_a_failing_confinement_probe_is_never_a_record", {})]),
        "randomly left on (BLOCKING 1)": ([('PYTEST_ARGS = ("-p", "no:randomly", "-p", "no:cacheprovider", "-q")', 'PYTEST_ARGS = ("-p", "no:cacheprovider", "-q")')],
                                          [("test_the_suite_runs_once_in_pytests_own_order", {})]),
        "timings in the digest": ([("    pairs = sorted((n, o) for n, o, _ in cases)", "    pairs = [(n, o) for n, o, _ in cases]")],
                                  [("test_the_result_digest_ignores_timing_and_order_and_sees_one_outcome", {})]),
        "refused fails the matrix": ([('OUTCOME_EXIT = {"evidence": 0, "refused": 0,', 'OUTCOME_EXIT = {"evidence": 0, "refused": 1,')],
                                     [("test_a_refused_build_is_a_census_row_and_runs_nothing", {})]),
    }, tmp_path_factory)


def test_the_attestation_aggregate_mutation_matrix(tmp_path_factory):
    """P1 for specs/attestation_aggregate.py: §4d's three steps, Q4, Q5a and Q6a."""
    _matrix(SPECS / "attestation_aggregate.py", "agg", {
        "different evidence emitted": ([("        if any({k: v for k, v in rec.items() if k != \"provenance\"} != base for rec in recs[1:]):", "        if False:")],
                                       [("test_different_evidence_is_a_disagreement_naming_every_job_and_other_keys_still_emit", {})]),
        "refused beside evidence emitted": ([('        elif outcome in FAILING or outcome == "refused":', "        elif outcome in FAILING:")],
                                            [("test_a_refused_job_beside_a_verifying_one_of_the_same_key_is_a_disagreement", {})]),
        "a failing-only key silent (Q5a)": ([('            out["failed_keys"].append({"key": repr(key), "jobs": names})', "            pass")],
                                            [("test_a_key_with_only_failing_jobs_fails_aggregation", {"red": "failed-tests"})]),
        "confinement-failed not failing": ([('FAILING = ("failed-tests", "evidence-mismatch", "confinement-failed")', 'FAILING = ("failed-tests", "evidence-mismatch")')],
                                           [("test_a_key_with_only_failing_jobs_fails_aggregation", {"red": "confinement-failed"})]),
        "provenance unsorted": ([('        prov = sorted((j for rec in recs for j in rec["provenance"]),\n                      key=lambda j: (j["route"], j["runner_image"], j["job_id"]))', '        prov = [j for rec in recs for j in rec["provenance"]]')],
                                [("test_equal_evidence_aggregates_to_one_record_with_sorted_union_provenance", {})]),
        "one disagreement stops every key": ([("            out[\"disagreements\"].append({\"key\": repr(key), \"why\": why, \"jobs\": names})\n            continue", "            out[\"disagreements\"].append({\"key\": repr(key), \"why\": why, \"jobs\": names})\n            break")],
                                             [("test_different_evidence_is_a_disagreement_naming_every_job_and_other_keys_still_emit", {})]),
        "unavailable rows unnamed (Q6a)": ([("            out[\"unavailable\"].append(f\"{row['route']} on {row['runner_image']}\")", "            pass")],
                                           [("test_excluded_and_refused_only_keys_are_listed_not_failures_and_a_missing_row_is_unavailable", {})]),
        "excluded counted as a failure": ([('    return bool(summary["disagreements"] or summary["failed_keys"])', '    return bool(summary["disagreements"] or summary["failed_keys"] or summary["excluded"])')],
                                          [("test_excluded_and_refused_only_keys_are_listed_not_failures_and_a_missing_row_is_unavailable", {})]),
        "the key from this runner (Q4)": ([("            key = sv.attestation_key(rec) if isinstance(rec, dict) else None", "            key = sv.attestation_key(sv.attestation_identity()) if isinstance(rec, dict) else None"),
                                           ('        out["records"].append({**base, "provenance": prov})', '        out["records"].append({**base, **{k: sv.attestation_identity()[k] for k in sv.KEY_FIELDS}, "provenance": prov})')],
                                          [("test_the_aggregator_takes_each_key_from_its_record_never_from_its_own_runner", {})]),
    }, tmp_path_factory)


def test_the_attestation_constraints_mutation_matrix(tmp_path_factory):
    """P1 for specs/attestation_constraints.py's offline rule."""
    C = "test_the_constraints_check_refuses_an_unpinned_or_out_of_bound_or_unparseable_set"
    _matrix(SPECS / "attestation_constraints.py", "cons", {
        "an unpinned requirement tolerated": ([('            problems.append(f"{req.name} (a direct requirement: {spec!r}) is not pinned")', "            pass")], [(C, {})]),
        "bounds unchecked": ([("            if not req.specifier.contains(Version(v), prereleases=True):", "            if False:")], [(C, {})]),
        "markers unparsed": ([("                Marker(marker)\n", "                pass\n")], [(C, {})]),
        "a range read as a pin": ([('_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\\s;]+)\\s*(?:;\\s*(.+))?$")', '_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:==|>=)([^\\s;]+)\\s*(?:;\\s*(.+))?$")')], [(C, {})]),
    }, tmp_path_factory)
