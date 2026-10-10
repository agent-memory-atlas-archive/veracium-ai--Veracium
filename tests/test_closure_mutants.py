"""Every CODE finding closed from the rule's adoption on is killed by its own cited closure cells — the owner's standing
check.

The owner, 2026-10-10: "make it a standard check", then, on its scope, "Code fixes only". Its evidence: 0043's
mechanism mutation table (specs/evidence/0043/mutation-table.json) found that 4 of that spec's 10 implementation-round
closure rows cited cells that PASSED but did not kill the finding's defect as its verdict described it; other existing
tests did. A closure row whose evidence cannot fail when the defect returns is a claim, not evidence.

THE RULE. A closure row in specs/closure_findings.py is SUBJECT when
  (1) its finding was RAISED by a verdict dated on or after RULE_DATE — the raising verdict's date in specs/reviews.py,
      keyed by (spec, finding id), because ids such as F1 recur across specs; and
  (2) it is a CODE fix — decided by the FIX, never by the evidence (citing a grep instead of a test must not escape the
      rule): a commit the row cites, in its fix text or its evidence, touches a non-test .py (src/, specs/evidence/,
      or a specs/*.py gate). A subject-by-date row that cites no resolvable commit REFUSES: it cannot be classified.
      STATED LIMIT: the classifier sees only the commits a row CITES, so a code fix whose row cites only a non-code
      commit (the spec fold, say) is classed non-code. The report LISTS it; it does not make it impossible.
A subject row needs a row in a mutation table that DECLARES its spec (header "spec"; the directory is location only),
for (spec, id), GOOD and KILLED, by EXACTLY the cells the closure row cites now, in a table that is CURRENT: every
digest its header records equals the bytes on disk.

Outside the rule BY PROPERTY, computed, never listed: findings raised before RULE_DATE, and non-code fixes. Non-code
rows under the date, and any non-node evidence a subject row also cites (a script, a grep — not proven by the table),
are REPORTED as a warning in the suite's summary, never silently dropped.

What a spec needs when its first subject finding closes: a campaign writing a table in this schema (header "spec",
"cells", "digests"; rows with "finding", "outcome", "good") with a `--check` — specs/evidence/0043/mutation_campaign.py is
the worked example. See the /pre-seal runbook.
"""
import hashlib
import importlib.util
import json
import pathlib
import re
import shlex
import subprocess
import warnings

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULE_DATE = "2026-10-10"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def tables(root: pathlib.Path) -> list:
    """(path, parsed table) for every mutation table under specs/evidence."""
    return [(p, json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs))
            for p in sorted((root / "specs" / "evidence").rglob("mutation-table.json"))]


def stale_digests(root: pathlib.Path, table: dict) -> list:
    out = []
    for rel, want in sorted(table.get("header", {}).get("digests", {}).items()):
        f = root / rel
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != want:
            out.append(rel)
    return out


def _tokens(cmd):
    """The command as the SHELL reads it: comments dropped (research, stage-1: an apostrophe inside a `# …` comment
    made plain shlex refuse 20 rows, and a node named only in a comment counted as cited though nothing runs it).
    With comments=True every row of specs/closure_findings.py parses (618 of 618, 2026-10-10), so there is no
    fallback: a command that does not parse is an error, not a guess."""
    return shlex.split(cmd, comments=True)


def git_classifier(root: pathlib.Path):
    """A callable: the set of files the commits cited in `text` touch, or None for a token git cannot resolve."""
    cache = {}

    def files(text):
        out = set()
        for tok in set(re.findall(r"\b[0-9a-f]{7,40}\b", text)):
            if tok not in cache:
                r = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", tok + "^{commit}"],
                                   capture_output=True, text=True)
                sha = r.stdout.strip() if r.returncode == 0 else None
                cache[tok] = set(subprocess.run(["git", "-C", str(root), "show", "--name-only", "--format=", sha],
                                                capture_output=True, text=True).stdout.split()) if sha else None
            if cache[tok] is not None:
                out |= cache[tok]
        return out
    return files


def _is_code(path):
    """Any non-test .py: src/, specs/evidence/, AND the top-level specs/*.py gates (a gate's own code is code)."""
    return path.endswith(".py") and not path.startswith("tests/")


def closure_mutant_problems(closures, reviews, mutation_tables, touched, root=ROOT, rule_date=RULE_DATE):
    """(problems, report). `touched(text)` returns the files the commits cited in `text` touch."""
    raised = {}
    for r in reviews:
        for fid in r.get("raised", []):
            raised.setdefault((r["spec"], fid), set()).add(r["date"])
    problems, report = [], []
    for row in closures:
        spec, fid, fix, evidence = row[0], row[3], row[5], row[-1]
        dates = raised.get((spec, fid))
        if not dates or len(dates) != 1:
            problems.append(f"{spec} {fid}: raised by {sorted(dates) if dates else 'no verdict'} in reviews.py — "
                            f"cannot be placed relative to the {rule_date} rule")
            continue
        if next(iter(dates)) < rule_date:
            continue
        files = touched(fix + " " + evidence)
        if not files:
            problems.append(f"{spec} {fid}: closed under the {rule_date} rule but cites no resolvable fix commit — "
                            f"cite it (fix text or `git show <sha>` evidence) so the rule can tell a code fix")
            continue
        if not any(_is_code(p) for p in files):
            report.append(f"{spec} {fid}: EXEMPT, a non-code fix (the commits it cites touch no non-test .py)")
            continue
        toks = _tokens(evidence)
        cited = [t for t in toks if "::" in t]
        dropped = [t for t in toks if (t.endswith(".py") or t.endswith(".sh")) and "::" not in t
                   and not t.startswith("tests/")] + (["grep"] if "grep" in toks else [])
        if dropped:
            report.append(f"{spec} {fid}: its evidence also cites {dropped}, which no mutation table proves")
        mine = [(p, t, r) for p, t in mutation_tables if t.get("header", {}).get("spec") == spec
                for r in t.get("rows", []) if r.get("finding") == fid]
        if not mine:
            problems.append(f"{spec} {fid}: a CODE fix closed under the {rule_date} rule with NO mechanism mutant in a "
                            f"mutation table declaring spec {spec}")
            continue
        ok = []
        for p, t, r in mine:
            stale = stale_digests(root, t)
            if stale:
                problems.append(f"{spec} {fid}: its mutation table {p.relative_to(root) if p.is_absolute() else p} is "
                                f"STALE (changed since --write: {stale})")
            elif r.get("good") is True and r.get("outcome") == "KILLED" and t.get("header", {}).get("cells", {}).get(fid) == cited:
                ok.append(r)
        if not ok and not any("STALE" in x and x.startswith(f"{spec} {fid}:") for x in problems):
            problems.append(f"{spec} {fid}: its mutant row(s) {[r.get('id') for _, _, r in mine]} are not GOOD, KILLED "
                            f"by exactly the cells the closure row cites now ({len(cited)} cited)")
    return problems, report


def _is_checkout():
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.returncode == 0 and pathlib.Path(r.stdout.strip()).resolve() == ROOT.resolve()


def _real():
    return (_load(ROOT / "specs" / "closure_findings.py", "cm_cf").CLOSURES,
            _load(ROOT / "specs" / "reviews.py", "cm_rv").REVIEWS)


def test_every_code_finding_closed_under_the_rule_is_killed_by_its_own_cited_cells():
    closures, reviews = _real()
    dated = {(r["spec"], f): r["date"] for r in reviews for f in r.get("raised", [])}
    subject_by_date = [r for r in closures if dated.get((r[0], r[3]), "") >= RULE_DATE]
    if subject_by_date and not _is_checkout():
        pytest.skip("rows are subject by date, and telling a code fix needs the git history of their fix commits")
    problems, report = closure_mutant_problems(closures, reviews, tables(ROOT), git_classifier(ROOT))
    for line in report:
        warnings.warn(f"closure-mutant rule: {line}", UserWarning)
    assert problems == []


def test_every_mutation_table_declares_its_spec_and_is_current():
    found = tables(ROOT)
    assert found, "no mutation table under specs/evidence (0043's is the worked example)"
    for p, t in found:
        assert isinstance(t.get("header", {}).get("spec"), str), f"{p} declares no spec"
        assert stale_digests(ROOT, t) == [], f"{p} is stale"


def test_the_rule_is_placeable_every_closure_row_traces_to_one_raising_verdict_date():
    """The date half of the exemption is a computed property, so every row must have one (618 of 618, 2026-10-10)."""
    closures, reviews = _real()
    problems, _ = closure_mutant_problems(closures, reviews, [], lambda text: set(), rule_date="9999-12-31")
    assert problems == []


# ---- controls: each refusal and each pass, on synthetic records ------------------------------------------------------

A = ["tests/test_x.py::test_a"]
CODE, PROSE = (lambda text: {"src/veracium/x.py"}), (lambda text: {"specs/0099-x.md"})


def _row(spec, fid, nodes, fix="round 2 (abc1234): the fix", extra=""):
    return (spec, "external", 1, fid, "the defect", fix, ("$PY -m pytest " + " ".join(nodes) + extra).strip())


def _review(spec, date, raised):
    return {"spec": spec, "round": 1, "kind": "external", "date": date, "verdict": "x", "raised": raised}


def _table(spec, fid, cells, outcome="KILLED", good=True, digests=None):
    return {"header": {"spec": spec, "cells": {fid: cells}, "digests": digests or {}},
            "rows": [{"id": "m1", "finding": fid, "outcome": outcome, "good": good}]}


def test_controls_the_rule_refuses_and_passes_where_it_should(tmp_path):
    after, before = "2026-10-11", "2026-10-09"
    f = tmp_path / "src.py"; f.write_text("x = 1\n")
    digest = {"src.py": hashlib.sha256(b"x = 1\n").hexdigest()}
    P = pathlib.Path("specs/evidence/x/mutation-table.json")
    cases = {
        "pre-rule, no table: outside the rule": (
            [_row("0099", "R1", A)], [_review("0099", before, ["R1"])], [], CODE, None),
        "post-rule NON-code fix, no table: exempt, and reported": (
            [_row("0099", "R1", A)], [_review("0099", after, ["R1"])], [], PROSE, None),
        "post-rule code fix citing no resolvable commit": (
            [_row("0099", "R1", A)], [_review("0099", after, ["R1"])], [], lambda text: set(), "no resolvable fix commit"),
        "post-rule code fix, no table": (
            [_row("0099", "R1", A)], [_review("0099", after, ["R1"])], [], CODE, "NO mechanism mutant"),
        "post-rule code fix, GOOD and killed by the cited cells, current": (
            [_row("0099", "R1", A)], [_review("0099", after, ["R1"])], [(P, _table("0099", "R1", A, digests=digest))], CODE, None),
        "...a code fix citing a GREP instead of a test cannot escape": (
            [("0099", "external", 1, "R1", "d", "round 2 (abc1234)", "grep -q x specs/0099-x.md")],
            [_review("0099", after, ["R1"])], [], CODE, "NO mechanism mutant"),
        "the mutant SURVIVED": (
            [_row("0099", "R1", A)], [_review("0099", after, ["R1"])],
            [(P, _table("0099", "R1", A, outcome="SURVIVED", good=False, digests=digest))], CODE, "not GOOD"),
        "killed by cells the row no longer cites": (
            [_row("0099", "R1", A + ["tests/test_x.py::test_b"])], [_review("0099", after, ["R1"])],
            [(P, _table("0099", "R1", A, digests=digest))], CODE, "not GOOD"),
        "a table declaring ANOTHER spec, same bare id (research's shared-directory case)": (
            [_row("0099", "R1", A)], [_review("0099", after, ["R1"])],
            [(P, _table("0098", "R1", A, digests=digest))], CODE, "NO mechanism mutant"),
        "a STALE table (a digested file changed since --write)": (
            [_row("0099", "R1", A)], [_review("0099", after, ["R1"])],
            [(P, _table("0099", "R1", A, digests={"src.py": "0" * 64}))], CODE, "STALE"),
        "a row no verdict raised": ([_row("0099", "R7", A)], [_review("0099", after, ["R1"])], [], CODE, "cannot be placed"),
    }
    for name, (closures, reviews, tbls, touched, want) in cases.items():
        problems, report = closure_mutant_problems(closures, reviews, tbls, touched, root=tmp_path)
        if want is None:
            assert problems == [], (name, problems)
        else:
            assert problems and all(want in p for p in problems), (name, problems)
    gate_code = lambda text: {"specs/check_x.py"}                       # a top-level specs/*.py gate is code
    problems, _ = closure_mutant_problems([_row("0099", "R1", A)], [_review("0099", after, ["R1"])], [], gate_code, root=tmp_path)
    assert problems and "NO mechanism mutant" in problems[0]
    commented = ("0099", "external", 1, "R1", "d", "round 2 (abc1234)", "$PY -m pytest tests/test_x.py  # tests/test_x.py::test_a")
    problems, _ = closure_mutant_problems([commented], [_review("0099", after, ["R1"])],
                                          [(P, _table("0099", "R1", A, digests=digest))], CODE, root=tmp_path)
    assert problems and "(0 cited)" in problems[0]                      # a node named only in a comment is not cited
    _, report = closure_mutant_problems([_row("0099", "R1", A)], [_review("0099", after, ["R1"])], [], PROSE, root=tmp_path)
    assert report and "EXEMPT, a non-code fix" in report[0]
    _, report = closure_mutant_problems([_row("0099", "R1", A, extra=" && $PY specs/check_x.py")], [_review("0099", after, ["R1"])],
                                        [(P, _table("0099", "R1", A, digests=digest))], CODE, root=tmp_path)
    assert report and "specs/check_x.py" in report[0]                     # non-node evidence is SAID, not dropped


def test_control_the_rule_date_moved_back_makes_0043s_rows_subject_and_its_table_satisfies_them():
    """0043's ten implementation-round findings predate the rule and are code fixes. Moved back to cover them, the rule
    must PASS on the committed table (the worked example meets its own standard), and REFUSE 0043's earlier findings,
    which have no mutants — on real rows and the real git history."""
    if not _is_checkout():
        pytest.skip("telling a code fix needs the git history of the fix commits")
    closures, reviews = _real()
    rows = [r for r in closures if r[0] == "0043" and r[2] >= 5]
    assert len(rows) == 10
    problems, report = closure_mutant_problems(rows, reviews, tables(ROOT), git_classifier(ROOT), rule_date="2026-10-01")
    assert problems == [] and not [x for x in report if "EXEMPT" in x], (problems, report)
    older = [r for r in closures if r[0] == "0043" and r[2] < 5]
    problems, _ = closure_mutant_problems(older, reviews, tables(ROOT), git_classifier(ROOT), rule_date="2026-09-01")
    assert problems
