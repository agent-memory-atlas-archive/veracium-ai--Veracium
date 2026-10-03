#!/usr/bin/env python3
"""A compact per-run TESTCASE MANIFEST from pytest's JUnit XML: one line per testcase — its identity, its outcome, and
for a skip its reason — sorted by identity, so two runs (two capture profiles, or a reviewer's run beside a supplied
one) reconcile by `diff` rather than by re-deriving from aggregated `-rs` lines (the 0041 round-10 reviewer's ask).

    python specs/evidence/offline/testcase_manifest.py <junit.xml> [<out.tsv>]

Columns, tab-separated: identity (classname::name, as JUnit records it) · outcome (passed / failed / error / skipped /
xfailed) · the skip or xfail reason (empty otherwise). A footer line counts each outcome, and the script REFUSES — exit
1 — if those counts disagree with the testsuite element's own totals, so a manifest never silently drops a case.
"""
import collections
import sys
import xml.etree.ElementTree as ET


def manifest(junit_path: str) -> tuple[list[str], collections.Counter]:
    root = ET.parse(junit_path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    rows, counts = [], collections.Counter()
    for suite in suites:
        for tc in suite.iter("testcase"):
            ident = f"{tc.get('classname', '')}::{tc.get('name', '')}"
            kids = {c.tag: c for c in tc}
            if "failure" in kids:
                outcome, reason = "failed", ""
            elif "error" in kids:
                outcome, reason = "error", ""
            elif "skipped" in kids:
                sk = kids["skipped"]
                outcome = "xfailed" if (sk.get("type") or "").endswith("xfail") else "skipped"
                reason = " ".join((sk.get("message") or "").split())
            else:
                outcome, reason = "passed", ""
            rows.append(f"{ident}\t{outcome}\t{reason}")
            counts[outcome] += 1
    expected = {"tests": sum(int(s.get("tests", 0)) for s in suites),
                "failures": sum(int(s.get("failures", 0)) for s in suites),
                "errors": sum(int(s.get("errors", 0)) for s in suites),
                "skipped": sum(int(s.get("skipped", 0)) for s in suites)}
    got = {"tests": sum(counts.values()), "failures": counts["failed"], "errors": counts["error"],
           "skipped": counts["skipped"] + counts["xfailed"]}
    if got != expected:
        raise SystemExit(f"REFUSED: the testcases ({got}) do not reconcile with the testsuite totals ({expected})")
    return sorted(rows), counts


def main(argv) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    rows, counts = manifest(argv[1])
    text = "\n".join(rows) + "\n" + "# " + " ".join(f"{k}={counts[k]}" for k in sorted(counts)) + "\n"
    if len(argv) == 3:
        with open(argv[2], "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
