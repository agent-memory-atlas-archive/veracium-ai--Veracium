#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0043_mutation_campaign.py::test_mutation_table_check_refuses_each_tampered_table
"""0043 — the mechanism mutation table (the round-9 verdict's optional ask: "a short machine-readable mutation result
table would make the declared independence easier to audit").

ONE mutant per closed finding that REINTRODUCES ITS DEFECT AS ITS VERDICT DESCRIBED IT, two or three where the verdict
named two halves, plus R8-01's five as the round-9 reviewer named them — each re-anchored at the current code (the
superseded code the old campaigns mutated is gone). Research's stage-1 read chose the set (2026-10-09). Not a generic
operator sweep: a sweep has equivalent survivors by nature, and this table asserts none survive.

The protocol is 0011's (mutant_registry.py): runner-observed, never claimed —
  CLEAN   on an unmutated copy of the tracked tree, every finding's closure cells pass and every honest probe passes;
  per mutant, in that copy: the anchor must occur EXACTLY ONCE; it is replaced; then
    IMPORT  every 0043 evidence module still imports (a mutant that breaks import "kills" everything, proving nothing);
    HONEST  the family's honest probe on the committed data (`--honest <family>`; below);
    CELLS   the finding's own closure cells (derived from specs/closure_findings.py, never a hand list) run under
            pytest with a JUnit record: KILLED iff >=1 cell FAILS by assertion and none ERRORS (collection or setup);
  and the file is restored byte-identically before the next.
A row is good when IMPORT ok, HONEST passes, and it is KILLED by assertion: a kill only because the honest data now
refuses is vacuous, and is recorded as such, never hidden.

mutation-table.json carries a header (the commit, whether the tree was clean, the interpreter and platform it was
produced on, sha256 of every mutated file and every cell file, each mutant definition's sha256) and one row per mutant.
`--check` is FAST and re-runs nothing: the definitions equal the table's, every anchor still occurs once, every
recorded digest equals the current bytes, every row is good, and body_sha256 binds the rest. A change to a mutated file
or a cell file makes the table STALE — correctly, since the kill may no longer hold — and the remedy is `--write`
(minutes). tests/test_0043_mutation_campaign.py re-runs the first row each suite run, so CI reproduces one row.

    $PY specs/evidence/0043/mutation_campaign.py --check     # the table is current and every row good (default)
    $PY specs/evidence/0043/mutation_campaign.py --write     # run the campaign and write the table
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TABLE = HERE / "mutation-table.json"
E = "specs/evidence/0043/"
ERASE = 'r"Answer using this rule:\\n(?:(?:- |  ).*\\n)*"'

# (id, finding, file under specs/evidence/0043/, anchor, replacement, honest family, what it reintroduces)
MUTANTS = [
    ("R5-01a", "0043-R5-01", "request_manifest.py",
     '    if entry["facet"] == "temporal:event-time" and not entry["answerable_from_fixture"]:\n',
     "    if False:\n", "score",
     "row references treated as the requested facts without adjudicating the question (the event-time step skipped: "
     "q006 classes on its located_at row)"),
    ("R5-01b", "0043-R5-01", "request_manifest.py",
     '"ambiguous": entry["ambiguous"] or False,', '"ambiguous": False,', "score",
     "no ambiguity path (an ambiguous question is scored as if it were not)"),
    ("R5-02a", "0043-R5-02", "interpreter.py",
     "            if not obj or any(_token_present(t, obj) for t in topic) or any(_token_present(t, list(topic)) for t in obj):\n",
     "            if True:\n", "reader",
     "an answer-wide refusal-cue fallback (a refusal cue anywhere withholds every fact)"),
    ("R5-02b", "0043-R5-02", "interpreter.py",
     '            polarity, frame_no = _frame_of(" " + clause[:pos], tail)\n',
     '            polarity, frame_no = _frame_of(" " + a[:a.find(clause) + pos], tail)\n',
     "reader", "keyword hedges anywhere before a fact (the frame read over the answer's whole text up to the fact, not "
     "its clause; research's form, stage-1)"),
    ("R5-03a", "0043-R5-03", "run_harness.py",
     "    # shared by invocation and oracle produced a report with rates while this check reported two problems.\n"
     '    if probe["problems"] or not probe["control_refuses"]:\n',
     "    # shared by invocation and oracle produced a report with rates while this check reported two problems.\n"
     "    if False:\n", "run",
     "run discards the calibration probe's independent arm problems"),
    ("R5-03b", "0043-R5-03", "run_harness.py",
     "        if bad:\n            raise Refused(f\"the arm comparison is not valid for {q['id']}",
     "        if False:\n            raise Refused(f\"the arm comparison is not valid for {q['id']}", "run",
     "run discards each question's captured-pair arm problems"),
    ("R5-04a", "0043-R5-04", "run_harness.py",
     "    if len(have) != len(set(have)) or set(have) != want:\n", "    if False:\n", "score",
     "rescoring takes the denominator from the surviving rows (the frozen (question, arm) set not enforced)"),
    ("R5-04b", "0043-R5-04", "run_harness.py",
     "delivered=delivered, mention_source=ms)", "delivered=None, mention_source=ms)", "score",
     "rescoring passes delivered=None (no delivered-evidence check)"),
    ("R5-05", "0043-R5-05", "run_harness.py",
     '            bb_ok = capture_digest(old_b["system"], old_b["prompt"]) == old_b["prompt_digest"]\n',
     "            bb_ok = True\n", "reverify",
     "reverify trusts the baseline's declared digest without binding it to the captured bytes"),
    ("R6-01a", "0043-R6-01", "interpreter.py",
     "    if delivered is not None:\n        mc = _load(\"model_input_capture\"); stray",
     "    if delivered is not None and mention_source is None:\n        mc = _load(\"model_input_capture\"); stray",
     "score", "published scoring bypasses capture integrity (the labelled path skips the capture accounting)"),
    ("R6-01b", "0043-R6-01", "run_harness.py",
     '        cf = x["facts"].get(x["class_fact"]) or {}\n',
     '        cf = next(y for y in res["detail"] if (y["question_id"], y["arm"]) == (x["question_id"], x["arm"]))["facts"]'
     '.get(x["class_fact"]) or {}\n', "score",
     "published scoring reads cached support: published_rates takes each row's support from the STORED ledger row, not "
     "the re-derived one (round 6's own mutant form; a first form in _score's ledger rows moved nothing published — "
     "an equivalent mutant, not a gap)"),
    ("R6-02", "0043-R6-02", "model_input_capture.py",
     '        if asked != [f"Question: {question}"]:\n', "        if False:\n", "arm",
     "the independent arm check accepts a different question"),
    ("R6-03a", "0043-R6-03", "run_harness.py",
     '    if capture_digest(recorded.get("system") or "", recorded.get("prompt") or "") != recorded.get("digest"):\n',
     "    if False:\n", "compiler", "compiler reverification does not bind the recorded bytes"),
    ("R6-03b", "0043-R6-03", "run_harness.py",
     '    differ += [f for f in ("model", "max_tokens") if f not in dict(unobserved) and live[f] != recorded[f]]\n',
     "    differ += []\n", "compiler", "compiler reverification does not compare the configuration"),
    ("R7-01", "0043-R7-01", "model_input_capture.py",
     '        elif bt != st.replace(rule, "", 1):\n',
     f'        elif re.sub({ERASE}, "", bt) != re.sub({ERASE}, "", st):\n', "arm",
     "added baseline instructions disappear: every 'Answer using this rule:' block erased from BOTH arms"),
    ("R8-01a", "0043-R8-01", "model_input_capture.py",
     "    if actual != expected:\n", "    if sorted(actual) != sorted(expected):\n", "arm",
     "the pre-question sequence compared SORTED (the reviewer's sorted-unit comparison)"),
    ("R8-01b", "0043-R8-01", "model_input_capture.py",
     "    if actual != expected:\n",
     "    if [l for l in actual if not _is_evidence_line(l)] != [l for l in expected if not _is_evidence_line(l)] or "
     "sorted(l for l in actual if _is_evidence_line(l)) != sorted(l for l in expected if _is_evidence_line(l)):\n",
     "arm", "non-evidence lines and sorted evidence compared as SEPARATE projections"),
    ("R8-01c", "0043-R8-01", "model_input_capture.py",
     "    frags, origins = _declared_edit_data()\n    for frag in frags:\n"
     '        line = line.replace("[" + frag + "] ", "").replace("[" + frag + "]", "")\n    for o in origins:\n'
     '        line = line.replace(" [" + o + "; unconfirmed]", "").replace("[" + o + "; unconfirmed]", "")\n',
     "    line = strip_markers(line)\n",
     "arm", "the check's marker removal is the transform's own strip_markers (a shared oracle); the claims rewrite kept, "
     "so honest data passes (equal on all 504 committed evidence lines) and only the independence cells can catch it"),
    ("R8-01d", "0043-R8-01", "model_input_capture.py",
     "(declared_evidence_edit(l) if _is_evidence_line(l) else l)", "l", "arm",
     "FAIL-CLOSED: evidence compared unnormalised (the declared marker removal not applied). On honest data the baseline "
     "carries no markers and the shipped side does, so its ONLY observable is that every honest pair refuses: a real "
     "kill by the honest controls, but no test of whether the comparison discriminates an undeclared change"),
    ("R8-01e", "0043-R8-01", "model_input_capture.py",
     "    if actual != expected:\n", "    if False:\n", "arm", "the pre-question sequence check removed"),
]


# research's stage-1 (2026-10-10): a mutant whose only observable is that every honest pair refuses is a real defect
# (the check fails closed) caught by the honest controls, not a discriminating one; its row is GOOD iff the honest
# probe REFUSES and an honest-control cell fails by assertion. Declared per mutant, asserted by --check — never inferred.
FAIL_CLOSED = {"R8-01d"}


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def definition_sha(m) -> str:
    return hashlib.sha256(json.dumps(list(m), ensure_ascii=True).encode()).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def cells() -> dict:
    """finding -> its closure cells, read from specs/closure_findings.py (the evidence each closure row runs)."""
    spec = importlib.util.spec_from_file_location("mc_cf", ROOT / "specs" / "closure_findings.py")
    cf = importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
    out = {}
    for r in cf.CLOSURES:
        if r[0] == "0043" and r[3] in {m[1] for m in MUTANTS}:
            out[r[3]] = [t for t in shlex.split(r[-1]) if "::" in t]
    return out


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _digests(root: pathlib.Path) -> dict:
    """The bytes the table's claims rest on: every mutated module, every cell file, AND this runner itself — a change
    to how a kill or an honest pass is judged must stale the table too (the first form bound only the first two)."""
    files = sorted({E + m[2] for m in MUTANTS} | {n.split("::")[0] for ns in cells().values() for n in ns}
                   | {E + "mutation_campaign.py"})
    return {f: _sha(root / f) for f in files}


# ---- the honest probes (run INSIDE the copy, as `--honest <family>`) ----------------------------------------------

def _ev(name):
    spec = importlib.util.spec_from_file_location(f"hp_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


READER_REFERENCE = ROOT / ".0043-reader-reference.json"       # written in the COPY at CLEAN, never in the real tree


def _readings() -> dict:
    """Every committed (answer, requested fact) reading by the reader: the reader family's honest data."""
    ip = _ev("interpreter")
    ledger = json.loads((HERE / "run_ledger.json").read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
    return {f"{x['question_id']}/{x['arm']}/{f['id']}": list(ip.mention_reading(x["answer"] or "", f, x["question"]))
            for x in ledger["detail"] for f in x["question_facts"]}


def honest(family: str) -> str:
    ledger = json.loads((HERE / "run_ledger.json").read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
    if family == "reader-reference":
        READER_REFERENCE.write_text(json.dumps(_readings(), sort_keys=True), encoding="utf-8")
        return "pass"
    if family == "reader":
        # research's definition (stage-1): for a reader mutant "honest" means the COMMITTED answers read the same; a
        # calibration refusal of a broken reader is a KILL by a real defence, not an honest failure
        ref, now = json.loads(READER_REFERENCE.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs), _readings()
        changed = sorted(k for k in ref if now.get(k) != ref[k])
        return "pass" if not changed and set(now) == set(ref) else f"fail: {len(changed)} of {len(ref)} committed readings changed"
    if family == "arm":
        mc = _ev("model_input_capture")
        by = {(x["question_id"], x["arm"]): x for x in ledger["detail"]}
        authored = {q["id"]: q["text"] for q in ledger["questions"]}
        bad = [q for q in ledger["kept"] if mc.arm_problems(by[(q, "veracium")], by[(q, "baseline")], authored[q])]
        return "pass" if not bad else f"fail: {len(bad)} committed pair(s) refused"
    rh = _ev("run_harness")
    if family == "score":
        rh.rescore(copy.deepcopy(ledger)); rh.published_rates(copy.deepcopy(ledger))
        return "pass"
    if family == "reverify":
        v = rh.reverify(copy.deepcopy(ledger))
        return "pass" if not v["mismatches"] else f"fail: {len(v['mismatches'])} mismatch(es)"
    if family == "run":
        with tempfile.TemporaryDirectory() as d:
            rh.run(pathlib.Path(d) / "out", rh.FakeModel(), request_manifest="generated")
            return "pass" if (pathlib.Path(d) / "out" / "run_report.txt").exists() else "fail: no report"
    if family == "compiler":
        node = "tests/test_0043_r6_03_compiler_binding.py::test_control_an_unchanged_recorded_invocation_reverifies"
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:randomly", "-p", "no:cacheprovider", node],
                           cwd=ROOT, capture_output=True, text=True)
        return "pass" if r.returncode == 0 else "fail: the unchanged recorded invocation does not reverify"
    raise SystemExit(f"unknown family {family}")


# ---- the campaign -------------------------------------------------------------------------------------------------

def _snapshot(dst: pathlib.Path):
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0")
    for f in filter(None, files):
        src = ROOT / f
        if src.is_file():
            (dst / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst / f)


def _env(root):
    return {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"}


def _imports(root, file) -> str:
    """The MUTATED module still imports (research's requirement). Only that module: the round-N reproduction scripts in
    the same folder execute when imported, and the first form of this probe loaded them all and read their refusals as
    import errors on every row."""
    code = ("import importlib.util, sys\n"
            "s = importlib.util.spec_from_file_location('i_mut', sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n")
    r = subprocess.run([sys.executable, "-B", "-c", code, E + file], cwd=root, env=_env(root), capture_output=True, text=True)
    return "ok" if r.returncode == 0 else "error: " + (r.stderr.strip().splitlines() or ["?"])[-1][:200]


def _honest(root, family) -> str:
    r = subprocess.run([sys.executable, "-B", E + "mutation_campaign.py", "--honest", family], cwd=root, env=_env(root),
                       capture_output=True, text=True)
    out = (r.stdout.strip().splitlines() or [""])[-1]
    return out if r.returncode == 0 and out else "fail: " + ((r.stderr.strip().splitlines() or ["no output"])[-1][:200])


def _cells(root, nodes) -> dict:
    with tempfile.TemporaryDirectory() as d:
        xml = pathlib.Path(d) / "j.xml"
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:randomly", "-p", "no:cacheprovider",
                            f"--junitxml={xml}", *nodes], cwd=root, env=_env(root), capture_output=True, text=True)
        failed, errored, passed = [], [], 0
        if xml.exists():
            for tc in ET.parse(xml).iter("testcase"):
                node = f"{tc.get('file') or tc.get('classname', '').replace('.', '/') + '.py'}::{tc.get('name')}"
                if tc.find("failure") is not None:
                    failed.append(node)
                elif tc.find("error") is not None:
                    errored.append(node)
                elif tc.find("skipped") is None:
                    passed += 1
        summary = (r.stdout.strip().splitlines() or [""])[-1][:160]
    return {"exit": r.returncode, "passed": passed, "failed": sorted(failed), "errored": sorted(errored), "summary": summary}


def run_one(root: pathlib.Path, m, nodes) -> dict:
    mid, finding, file, anchor, repl, family, what = m
    target = root / E / file
    original = target.read_bytes()
    text = original.decode()
    n = text.count(anchor)
    row = {"id": mid, "finding": finding, "file": E + file, "what": what, "family": family, "anchor_count": n,
           "definition_sha256": definition_sha(m)}
    if n != 1:
        return {**row, "outcome": "ANCHOR", "good": False}
    target.write_text(text.replace(anchor, repl))
    try:
        row["import"] = _imports(root, file)
        row["honest"] = _honest(root, family)
        c = _cells(root, nodes)
    finally:
        target.write_bytes(original)
    assert _sha(target) == hashlib.sha256(original).hexdigest()
    killed = bool(c["failed"]) and not c["errored"]
    row.update({"cells": len(nodes), "cells_failed": c["failed"], "cells_errored": c["errored"], "pytest": c["summary"],
                "outcome": "KILLED" if killed else ("ERROR" if c["errored"] else "SURVIVED"),
                "kill_kind": "assertion" if killed else None})
    row["kind"] = "fail-closed" if mid in FAIL_CLOSED else "discriminating"
    if row["kind"] == "fail-closed":
        row["good"] = (row["import"] == "ok" and row["honest"].startswith("fail") and killed
                       and any("::test_control" in n for n in c["failed"]))
    else:
        row["good"] = row["import"] == "ok" and row["honest"] == "pass" and killed
    return row


def campaign() -> dict:
    nodes = cells()
    missing = sorted({m[1] for m in MUTANTS} - set(nodes))
    if missing:
        raise SystemExit(f"no closure cells for {missing}")
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        _snapshot(root)
        clean_cells = _cells(root, sorted({n for ns in nodes.values() for n in ns}))
        if _honest(root, "reader-reference") != "pass":
            raise SystemExit("CLEAN failed — the reader reference could not be computed on the unmutated copy")
        clean_honest = {f: _honest(root, f) for f in sorted({m[5] for m in MUTANTS})}
        clean_imports = {f: _imports(root, f) for f in sorted({m[2] for m in MUTANTS})}
        if any(v != "ok" for v in clean_imports.values()):
            raise SystemExit(f"CLEAN failed — a module does not import unmutated: {clean_imports}")
        if clean_cells["failed"] or clean_cells["errored"] or any(v != "pass" for v in clean_honest.values()):
            raise SystemExit(f"CLEAN failed — no mutant is meaningful on a tree whose controls fail: {clean_cells} {clean_honest}")
        rows = [run_one(root, m, nodes[m[1]]) for m in MUTANTS]
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.split("\n")
    body = {
        "header": {"commit": head, "tracked_changes": sorted(l[3:] for l in dirty if l.strip()),
                   "python": platform.python_version(), "platform": platform.platform(),
                   "digests": _digests(ROOT), "definitions": {m[0]: definition_sha(m) for m in MUTANTS},
                   "cells": nodes,
                   "clean": {"cells_passed": clean_cells["passed"], "honest": clean_honest}},
        "rows": rows,
        "summary": {"rows": len(rows), "killed_by_assertion": sum(r.get("kill_kind") == "assertion" for r in rows),
                    "fail_closed": sum(r.get("kind") == "fail-closed" for r in rows),
                    "survived": sum(r["outcome"] == "SURVIVED" for r in rows), "good": sum(r["good"] for r in rows)},
    }
    return {**body, "body_sha256": hashlib.sha256(canonical(body)).hexdigest()}


def render(table: dict) -> str:
    return json.dumps(table, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def problems(path: pathlib.Path = TABLE) -> list[str]:
    if not path.exists():
        return [f"{path.name} does not exist — run --write"]
    try:
        t = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
    except ValueError as e:
        return [f"{path.name} is not JSON: {e}"]
    out = []
    body = {k: v for k, v in t.items() if k != "body_sha256"}
    if hashlib.sha256(canonical(body)).hexdigest() != t.get("body_sha256"):
        out.append("body_sha256 does not match the table's own body (edited by hand, or a partial write)")
    h = t.get("header", {})
    if h.get("definitions") != {m[0]: definition_sha(m) for m in MUTANTS}:
        out.append("the mutant definitions differ from the table's (a mutant added, removed or changed) — run --write")
    for m in MUTANTS:
        n = (ROOT / E / m[2]).read_text().count(m[3])
        if n != 1:
            out.append(f"{m[0]}: its anchor occurs {n} time(s) in {m[2]} at this tree")
    if h.get("cells") != cells():
        out.append("the closure cells each finding's row ran differ from what specs/closure_findings.py cites now "
                   "(a cited node added or dropped) — run --write")
    live = _digests(ROOT)
    stale = sorted(f for f in set(live) | set(h.get("digests", {})) if live.get(f) != h.get("digests", {}).get(f))
    if stale:
        out.append(f"stale: these mutated or cell files changed since the table was written: {stale} — run --write")
    rows = t.get("rows", [])
    if [r.get("id") for r in rows] != [m[0] for m in MUTANTS]:
        out.append("the rows are not one per mutant, in order")
    for r in rows:
        fc = r.get("id") in FAIL_CLOSED
        honest_ok = str(r.get("honest", "")).startswith("fail") if fc else r.get("honest") == "pass"
        if r.get("kind") != ("fail-closed" if fc else "discriminating"):
            out.append(f"{r.get('id')}: kind {r.get('kind')!r} is not the declared one")
        if not (r.get("outcome") == "KILLED" and r.get("kill_kind") == "assertion" and r.get("import") == "ok"
                and honest_ok and r.get("good") is True
                and (not fc or any("::test_control" in n for n in r.get("cells_failed", [])))):
            out.append(f"{r.get('id')}: not a good row (kind {r.get('kind')}, outcome {r.get('outcome')}, kill "
                       f"{r.get('kill_kind')}, import {r.get('import')}, honest {r.get('honest')})")
    return out


def main() -> int:
    if "--honest" in sys.argv:
        print(honest(sys.argv[sys.argv.index("--honest") + 1]))
        return 0
    if "--write" in sys.argv:
        t = campaign()
        TABLE.write_text(render(t), encoding="utf-8")
        print(f"wrote {TABLE.relative_to(ROOT)}: {json.dumps(t['summary'])} (body_sha256 {t['body_sha256']})")
        for r in t["rows"]:
            print(f"  {r['id']:7s} {r['outcome']:8s} import={r.get('import')} honest={r.get('honest')} "
                  f"failed={len(r.get('cells_failed', []))}/{r.get('cells')} errored={len(r.get('cells_errored', []))}")
        return 0 if t["summary"]["good"] == len(t["rows"]) else 1
    bad = problems()
    for b in bad:
        print(f"STALE: {b}")
    if not bad:
        t = json.loads(TABLE.read_text(), object_pairs_hook=_strict_pairs)
        print(f"mutation-table.json current: {json.dumps(t['summary'])} (body_sha256 {t['body_sha256']})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
