#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0041_mutation_campaign.py::test_mutation_table_check_refuses_each_tampered_table
"""0041 — the notice-binding hotfix's mutation table (internal finding 0041-PA1, 2026-10-13; the closure-mutant rule of
2026-10-10: a CODE finding closes only with cells that KILL its defect as the finding describes it).

ONE mutant per protection the hotfix added, each REINTRODUCING the defect that protection closes, at the shipped code
(src/veracium). The protocol is 0043's (specs/evidence/0043/mutation_campaign.py), with the mutated files under src/:
  CLEAN   on an unmutated copy of the tracked tree, every closure cell passes and the honest controls pass;
  per mutant, in that copy: the anchor must occur EXACTLY ONCE; it is replaced; then
    IMPORT  the mutated module still imports (a mutant that breaks import "kills" everything, proving nothing);
    HONEST  the legitimate flows the hotfix must not break still pass under the mutant (HONEST_NODES: a redacted record
            arriving new is redacted; a newer backup restored over an older store redacts it; a standing notice
            completes on its own origin's redacted record and, on restore, on any inserted record that shows it);
    CELLS   0041-PA1's closure cells (read from specs/closure_findings.py, never a hand list) run under pytest with a
            JUnit record, and EACH failing cell is classified from its failure message (failure_kind): `assertion`
            (an AssertionError or a bare assert, the permission helper's included), `expected-refusal-missing`
            (pytest.raises: DID NOT RAISE), or `other: <type>` (anything else — a TypeError, an unrelated ValueError,
            a setup failure). KILLED iff >=1 cell fails with a QUALIFYING kind, NO cell fails with `other` and none
            ERRORS; failures that include an `other` read UNCLASSIFIED (round-4 IO-II-7: the runner had called every
            JUnit failure an assertion kill, and three detections were escaping domain refusals);
  and the file is restored byte-identically before the next.
A row is good when IMPORT ok, HONEST passes, and it is KILLED; it records every failing cell's kind, so its kill can be
recounted from the table without re-running. CONTROLS are the classifier's negatives: an UNRELATED failure injected at a
mutated call site must read UNCLASSIFIED, never KILLED.

`--check` is FAST and re-runs nothing: the definitions equal the table's, every anchor still occurs once, every recorded
digest (each mutated module, each cell file, the honest nodes' file, this runner) equals the current bytes, every row is
good, and body_sha256 binds the rest. A change to any of them makes the table STALE, and the remedy is `--write`.
tests/test_0041_mutation_campaign.py re-runs the first row each suite run, so CI reproduces one row.

    $PY specs/evidence/0041/mutation_campaign.py --check     # the table is current and every row good (default)
    $PY specs/evidence/0041/mutation_campaign.py --write     # run the campaign and write the table
"""
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TABLE = HERE / "mutation-table.json"
SRC = "src/veracium/"
SELF = "specs/evidence/0041/mutation_campaign.py"
KINDS = "specs/evidence/mutation_kinds.py"          # how a kill is judged: digested with the runner
FINDING = "0041-PA1"
HOTFIX_TESTS = "tests/test_0041_notice_binding_hotfix.py"
HONEST_NODES = [HOTFIX_TESTS + "::" + n for n in (
    "test_a_redacted_record_arriving_new_is_still_redacted_in_the_same_transaction",
    "test_a_trusted_restore_of_a_newer_backup_still_redacts_the_held_older_record",
    "test_ii_a_default_arrival_from_the_notices_own_origin_completes_it",
    "test_ii_on_restore_completion_needs_an_inserted_shown_record_and_not_its_origin",
)]

def _load_kinds():
    """The ONE definition of a kill, shared with 0043's campaign (specs/evidence/mutation_kinds.py)."""
    spec = importlib.util.spec_from_file_location("veracium_mutation_kinds", HERE.parent / "mutation_kinds.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


MK = _load_kinds()
QUALIFYING = MK.QUALIFYING
failure_kind = MK.failure_kind


# (id, finding, file under src/veracium/, anchor, replacement, what it reintroduces)
MUTANTS = [
    ("PA1-created", FINDING, "store/sqlite.py",
     '                        if not notice_any and (n["target_kind"], n["target_id"]) not in created:\n',
     '                        if False:\n',
     "the default path's created-only gate removed: an untrusted notice redacts a HELD record and writes a standing row"),
    ("PA1-scope", FINDING, "portability.py",
     '                "notice_scope": "created" if capped_path else "any"}',
     '                "notice_scope": "any"}',
     "the import passes the restore scope on the default path: the shipped bare-id binding, through the caller"),
    ("PA1-default", FINDING, "store/sqlite.py",
     '            notice_any = plan.get("notice_scope") == "any"\n',
     '            notice_any = plan.get("notice_scope") != "created"\n',
     "the primitive's default scope widened: a plan with no scope binds a notice to a bare id (fail-open)"),
    ("PA1-fixedpoint", FINDING, "redaction.py",
     "    return not ((set(would) & set(fields)) - _NOT_RECORD_CARRIERS)\n",
     "    return True\n",
     "every record 'shows' every redaction: a notice beside an unredacted record applies (case 7 destroys the fact)"),
    ("PA1-infile", FINDING, "portability.py",
     '            n["_shown"] = rec is not None and _redaction.shows_redaction(n["target_kind"], rec, n["fields"])\n',
     '            n["_shown"] = rec is None or _redaction.shows_redaction(n["target_kind"], rec, n["fields"])\n',
     "a notice with no record in the file counts as shown: a notice-only restore redacts an unredacted held record"),
    ("PA1-pair-refusal", FINDING, "store/sqlite.py",
     '                            if present and n.get("_unshown") == "record-untreated":\n',
     '                            if False:\n',
     "a file pairing a notice with its record UNREDACTED is not refused (the poisoned export imports)"),
    ("PA1-arrival-refusal", FINDING, "store/sqlite.py",
     '                                if not _redaction.shows_redaction(kind, json.loads(row[1]), json.loads(fields)):\n',
     '                                if False:\n',
     "a standing notice completes on an UNREDACTED arrival: it removes content from a record arriving in a restore"),
    ("PA1-arrival-created", FINDING, "store/sqlite.py",
     '                        if (kind, tid) not in created:\n                            continue\n',
     '',
     "a standing notice completes on ANY present record, not only one this import inserted (the user's own later write)"),
    ("PA1-origin", FINDING, "store/sqlite.py",
     '                                    if resolve_origin(stored, self.local_origin()) != s_origin:\n',
     '                                    if False:\n',
     "on the default path a standing notice completes on a record from ANY origin (a third store's record redacted)"),
    ("PA1-attest-held", FINDING, "store/sqlite.py",
     '                                and _redaction.shows_redaction(n["target_kind"], json.loads(row[1]), n["fields"])):\n',
     '                                and True):\n',
     "with no copy in the file, a notice applies to a HELD record that does not show the redaction (the primitive's own "
     "check, the only one a plan arriving by another route than the import has)"),
    ("PA1-writer-edge", FINDING, "store/sqlite.py",
     '            attested = self._attested_fields(edge.user_id, "edge", edge.id, standing=False)\n',
     '            attested = self._attested_fields(edge.user_id, "edge", edge.id)\n',
     "a standing notice refuses the user's own edge write of its id again"),
    ("PA1-writer-episode", FINDING, "store/sqlite.py",
     '                    attested = self._attested_fields(episode.user_id, "episode", episode.id, standing=False)\n',
     '                    attested = self._attested_fields(episode.user_id, "episode", episode.id)\n',
     "a standing notice refuses the user's own episode write of its id again"),
    ("PA1-readers", FINDING, "store/sqlite.py",
     '            f"SELECT DISTINCT target_id FROM redactions WHERE user_id=? AND target_kind=? AND NOT {_STANDING_SQL}",\n',
     '            f"SELECT DISTINCT target_id FROM redactions WHERE user_id=? AND target_kind=?",\n',
     "a standing notice's id is in redacted_targets() again: the readers hide a record no notice reached"),
]

_WRITER = '            attested = self._attested_fields(edge.user_id, "edge", edge.id, standing=False)\n'
# (id, file under src/veracium/, anchor, replacement, what it injects, the outcome the classifier must give it)
CONTROLS = [
    ("CTRL-unrelated-TypeError", "store/sqlite.py", _WRITER,
     _WRITER + '            raise TypeError("an unrelated execution failure (IO-II-7 negative control)")\n',
     "an UNRELATED TypeError at PA1-writer-edge's call site: every edge write fails, for no reason the hotfix names",
     "UNCLASSIFIED"),
    ("CTRL-unrelated-ValueError", "store/sqlite.py", _WRITER,
     _WRITER + '            raise ValueError("an unrelated ValueError, not a domain refusal (IO-II-7 negative control)")\n',
     "an UNRELATED ValueError (no `refused:` domain form) at the same site: the permission helper must not count it",
     "UNCLASSIFIED"),
]


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
    """finding -> its closure cells, read from specs/closure_findings.py (the evidence its closure row runs)."""
    spec = importlib.util.spec_from_file_location("mc41_cf", ROOT / "specs" / "closure_findings.py")
    cf = importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
    return {r[3]: [t for t in shlex.split(r[-1]) if "::" in t]
            for r in cf.CLOSURES if r[0] == "0041" and r[3] in {m[1] for m in MUTANTS}}


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _digests(root: pathlib.Path) -> dict:
    """The bytes the table's claims rest on: every mutated module, every cell file, the honest nodes' file, and this
    runner itself (a change to how a kill or an honest pass is judged stales the table too)."""
    files = sorted({SRC + m[2] for m in MUTANTS} | {n.split("::")[0] for ns in cells().values() for n in ns}
                   | {n.split("::")[0] for n in HONEST_NODES} | {SELF, KINDS})
    return {f: _sha(root / f) for f in files}


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
    """The MUTATED module still imports, as the package imports it (from the copy's src, asserted)."""
    mod = "veracium." + file[:-3].replace("/", ".")
    code = (f"import importlib, pathlib, sys\nm = importlib.import_module({mod!r})\n"
            f"assert pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[1]).resolve()), m.__file__\n")
    r = subprocess.run([sys.executable, "-B", "-c", code, str(root / "src")], cwd=root, env=_env(root),
                       capture_output=True, text=True)
    return "ok" if r.returncode == 0 else "error: " + (r.stderr.strip().splitlines() or ["?"])[-1][:200]


def _pytest(root, nodes) -> dict:
    with tempfile.TemporaryDirectory() as d:
        xml = pathlib.Path(d) / "j.xml"
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:randomly", "-p", "no:cacheprovider",
                            f"--junitxml={xml}", *nodes], cwd=root, env=_env(root), capture_output=True, text=True)
        failed, errored, passed, kinds = [], [], 0, {}
        if xml.exists():
            for tc in ET.parse(xml).iter("testcase"):
                node = f"{tc.get('file') or tc.get('classname', '').replace('.', '/') + '.py'}::{tc.get('name')}"
                f = tc.find("failure")
                if f is not None:
                    failed.append(node)
                    kinds[node] = failure_kind(f.get("message") or "")
                elif tc.find("error") is not None:
                    errored.append(node)
                elif tc.find("skipped") is None:
                    passed += 1
        summary = (r.stdout.strip().splitlines() or [""])[-1][:160]
    return {"exit": r.returncode, "passed": passed, "failed": sorted(failed), "errored": sorted(errored),
            "kinds": dict(sorted(kinds.items())), "summary": summary}


def _honest(root) -> str:
    h = _pytest(root, HONEST_NODES)
    ok = h["exit"] == 0 and h["passed"] == len(HONEST_NODES) and not h["failed"] and not h["errored"]
    return "pass" if ok else f"fail: {len(h['failed'])} failed, {len(h['errored'])} errored of {len(HONEST_NODES)}"


def run_one(root: pathlib.Path, m, nodes) -> dict:
    mid, finding, file, anchor, repl, what = m
    target = root / SRC / file
    original = target.read_bytes()
    text = original.decode()
    n = text.count(anchor)
    row = {"id": mid, "finding": finding, "file": SRC + file, "what": what, "anchor_count": n,
           "definition_sha256": definition_sha(m)}
    if n != 1:
        return {**row, "outcome": "ANCHOR", "good": False}
    target.write_text(text.replace(anchor, repl))
    try:
        row["import"] = _imports(root, file)
        row["honest"] = _honest(root)
        c = _pytest(root, nodes)
    finally:
        target.write_bytes(original)
    assert _sha(target) == hashlib.sha256(original).hexdigest()
    row.update(classify(c))
    row.update({"cells": len(nodes), "pytest": c["summary"]})
    row["good"] = row["import"] == "ok" and row["honest"] == "pass" and row["outcome"] == "KILLED"
    return row


def classify(c: dict) -> dict:
    """KILLED only by a qualifying kind with no `other` and no error (round-4 IO-II-7); the shared definition."""
    return MK.classify(c["kinds"], c["failed"], c["errored"])


def run_control(root: pathlib.Path, ctl, nodes) -> dict:
    cid, file, anchor, repl, what, expected = ctl
    target = root / SRC / file
    original = target.read_bytes()
    text = original.decode()
    row = {"id": cid, "file": SRC + file, "what": what, "anchor_count": text.count(anchor), "expected": expected}
    if row["anchor_count"] != 1:
        return {**row, "outcome": "ANCHOR", "good": False}
    target.write_text(text.replace(anchor, repl))
    try:
        row["import"] = _imports(root, file)
        c = _pytest(root, nodes)
    finally:
        target.write_bytes(original)
    assert _sha(target) == hashlib.sha256(original).hexdigest()
    row.update(classify(c))
    row["good"] = row["import"] == "ok" and row["outcome"] == expected and bool(row["cells_failed"])
    return row


def campaign() -> dict:
    nodes = cells()
    if FINDING not in nodes or not nodes[FINDING]:
        raise SystemExit(f"no closure cells for {FINDING} in specs/closure_findings.py")
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        _snapshot(root)
        clean_cells = _pytest(root, nodes[FINDING])
        clean_honest = _honest(root)
        clean_imports = {f: _imports(root, f) for f in sorted({m[2] for m in MUTANTS})}
        if any(v != "ok" for v in clean_imports.values()):
            raise SystemExit(f"CLEAN failed — a module does not import unmutated: {clean_imports}")
        if clean_cells["failed"] or clean_cells["errored"] or clean_cells["exit"] != 0 or clean_honest != "pass":
            raise SystemExit(f"CLEAN failed — no mutant is meaningful on a tree whose controls fail: {clean_cells} {clean_honest}")
        rows = [run_one(root, m, nodes[m[1]]) for m in MUTANTS]
        controls = [run_control(root, k, nodes[FINDING]) for k in CONTROLS]
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.split("\n")
    body = {
        "header": {"spec": "0041", "commit": head, "tracked_changes": sorted(l[3:] for l in dirty if l.strip()),
                   "python": platform.python_version(), "platform": platform.platform(),
                   "digests": _digests(ROOT), "definitions": {m[0]: definition_sha(m) for m in MUTANTS},
                   "control_definitions": {k[0]: definition_sha(k) for k in CONTROLS},
                   "cells": nodes, "honest_nodes": HONEST_NODES,
                   "clean": {"cells_passed": clean_cells["passed"], "honest": clean_honest}},
        "rows": rows,
        "controls": controls,
        "summary": {"rows": len(rows), "killed": sum(r["outcome"] == "KILLED" for r in rows),
                    "cell_kinds": dict(sorted(collections.Counter(
                        k for r in rows for k in r.get("cell_kinds", {}).values()).items())),
                    "survived": sum(r["outcome"] == "SURVIVED" for r in rows), "good": sum(r["good"] for r in rows),
                    "controls": len(controls), "controls_good": sum(k["good"] for k in controls)},
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
        return [f"{path.name} is not JSON, or carries a duplicate key: {e}"]
    out = []
    body = {k: v for k, v in t.items() if k != "body_sha256"}
    if hashlib.sha256(canonical(body)).hexdigest() != t.get("body_sha256"):
        out.append("the table does not match its own body digest (edited after writing)")
    h = t.get("header", {})
    if h.get("spec") != "0041":
        out.append(f"the table declares spec {h.get('spec')!r}, not 0041")
    if h.get("definitions") != {m[0]: definition_sha(m) for m in MUTANTS}:
        out.append("the mutant definitions differ from the runner's — run --write")
    if h.get("control_definitions") != {k[0]: definition_sha(k) for k in CONTROLS}:
        out.append("the control definitions differ from the runner's — run --write")
    if h.get("cells") != cells():
        out.append("the closure cells differ from specs/closure_findings.py's — run --write")
    if h.get("honest_nodes") != HONEST_NODES:
        out.append("the honest nodes differ from the runner's — run --write")
    stale = sorted(f for f, want in h.get("digests", {}).items()
                   if not (ROOT / f).is_file() or _sha(ROOT / f) != want)
    if stale or set(h.get("digests", {})) != set(_digests(ROOT)):
        out.append(f"stale: {stale or 'the digested file set changed'} — run --write")
    for m in MUTANTS:
        if (ROOT / SRC / m[2]).read_text().count(m[3]) != 1:
            out.append(f"{m[0]}: its anchor no longer occurs exactly once in {SRC + m[2]}")
    rows = t.get("rows", [])
    if [r.get("id") for r in rows] != [m[0] for m in MUTANTS]:
        out.append("the rows are not one per mutant, in order")
    cited = {n for ns in (h.get("cells") or {}).values() for n in ns}
    for r in rows:
        failed = r.get("cells_failed") or []
        recount = classify({"kinds": r.get("cell_kinds") or {}, "failed": failed, "errored": r.get("cells_errored") or []})
        if not (r.get("outcome") == "KILLED" == recount["outcome"] and r.get("kill_kind") == recount["kill_kind"]
                and r.get("import") == "ok" and r.get("honest") == "pass" and r.get("good") is True
                and not r.get("cells_errored") and failed and set(failed) <= cited):
            out.append(f"{r.get('id')}: not a good row (outcome {r.get('outcome')}, recounted from its cell kinds "
                       f"{recount['outcome']}, kill {r.get('kill_kind')}, import {r.get('import')}, honest "
                       f"{r.get('honest')}, {len(failed)} failing cell(s), "
                       f"{'all' if set(failed) <= cited else 'NOT all'} among the cited cells)")
    ctls = t.get("controls", [])
    if [k.get("id") for k in ctls] != [k[0] for k in CONTROLS]:
        out.append("the controls are not one per CONTROLS entry, in order")
    for k in ctls:
        recount = classify({"kinds": k.get("cell_kinds") or {}, "failed": k.get("cells_failed") or [],
                            "errored": k.get("cells_errored") or []})
        if not (k.get("good") is True and k.get("outcome") == k.get("expected") == recount["outcome"] != "KILLED"):
            out.append(f"{k.get('id')}: the classifier's negative control is not good (outcome {k.get('outcome')}, "
                       f"recounted {recount['outcome']}, expected {k.get('expected')})")
    return out


def main() -> int:
    if "--write" in sys.argv:
        t = campaign()
        TABLE.write_text(render(t), encoding="utf-8")
        print(f"wrote {TABLE.relative_to(ROOT)}: {json.dumps(t['summary'])} (body_sha256 {t['body_sha256']})")
        for r in t["rows"]:
            print(f"  {r['id']:20s} {r['outcome']:8s} import={r.get('import')} honest={r.get('honest')} "
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
