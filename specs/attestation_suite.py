#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0007_attestation_jobs.py::test_the_attestation_suite_rule_mutation_matrix
"""0007 §4d: the attestation suite, by the ONE committed rule (I5, "bind collection to the one committed
suite-selection rule").

A module is in the suite when it is a `test_*.py` under `tests/` whose AST, at any depth:
  * imports a ROOT, or a submodule of one, by `import x` or `from x import y` (`from p import x` imports `p.x`);
  * or passes `schema_evidence.py` or `migrations_0013.py` inside a string constant somewhere in a CALL's arguments
    (loading the file by path). A literal anywhere else (a fixture string, a docstring, a message) admits nothing.
The node set is pytest's collection of those modules.

    $PY specs/attestation_suite.py --list                 # the suite's modules at this tree, one per line
    $PY specs/attestation_suite.py --nodes <junit.xml>    # exit 1 unless the JUnit ran exactly those modules
"""
from __future__ import annotations

import ast
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOTS = ("sqlite3", "veracium.store.schema_version", "veracium.store.migration", "veracium.store.release_migration",
         "schema_evidence", "migrations_0013")
FILES = ("schema_evidence.py", "migrations_0013.py")
GROUPS_DOC = ROOT / "specs" / "evidence" / "offline" / "JOINT-TEST-GROUPS.md"
"""0007 v22 §4d: the ONE carrier of the joint test groups (written after 0041 round 9). The selection is CLOSED under
them: a selected member brings every other member of its group, since the group's gate reads state the other members
record in the same process."""


def _is_root(name) -> bool:
    return isinstance(name, str) and any(name == r or name.startswith(r + ".") for r in ROOTS)


def reasons(source: str) -> list:
    """Why a module's source admits it (empty: it is not in the suite)."""
    why = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            why |= {a.name for a in node.names if _is_root(a.name)}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            # `from m import a` imports m and m.a; `m.a` is root-or-submodule exactly when m is or a root is m.a
            why |= {f"{node.module}.{a.name}" for a in node.names if _is_root(f"{node.module}.{a.name}")}
        elif isinstance(node, ast.Call):
            for arg in [*node.args, *(k.value for k in node.keywords)]:
                for c in ast.walk(arg):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str):
                        why |= {"call:" + f for f in FILES if f in c.value}
    return sorted(why)


def joint_groups(doc=None, tree=None) -> list:
    """[[member, ...]] from the groups document's `| members |` rows: each backticked `tests/…py` in the row. A row
    with none, a member that is not a file of `tree`, or a document with no group is refused (each would silently
    close over nothing)."""
    import re
    doc = GROUPS_DOC if doc is None else pathlib.Path(doc)
    tree = doc.parents[3] if tree is None else pathlib.Path(tree)
    groups = []
    for line in doc.read_text(encoding="utf-8").splitlines():
        if line.startswith("| members |"):
            members = re.findall(r"`(tests/[\w/]+\.py)`", line)
            if not members:
                raise ValueError(f"a members row names no test module: {line[:120]!r}")
            missing = [m for m in members if not (tree / m).is_file()]
            if missing:
                raise ValueError(f"a joint test group names a module this tree does not have: {missing}")
            groups.append(members)
    if not groups:
        raise ValueError(f"{doc} declares no joint test group")
    return groups


def suite(tree=ROOT) -> list:
    """The suite's modules, as tree-relative paths, sorted: the rule's selection, closed under the joint test groups."""
    tree = pathlib.Path(tree)
    picked = {str(p.relative_to(tree)) for p in sorted((tree / "tests").rglob("test_*.py"))
              if reasons(p.read_text(encoding="utf-8"))}
    for members in joint_groups(tree / GROUPS_DOC.relative_to(ROOT), tree):
        if picked & set(members):
            picked |= set(members)
    return sorted(picked)


def junit_modules(junit_path) -> set:
    """The test modules a JUnit file ran, from each testcase's `classname` (pytest: `tests.test_x[.Class]`)."""
    out = set()
    for case in ET.parse(junit_path).getroot().iter("testcase"):
        parts = (case.get("classname") or "").split(".")
        mod = next((i for i, p in enumerate(parts) if p.startswith("test_")), None)
        if mod is None:
            raise ValueError(f"a testcase with no test module in its classname: {case.get('classname')!r}")
        out.add("/".join(parts[:mod + 1]) + ".py")
    return out


def nodes_problems(junit_path, tree=ROOT) -> list:
    want, ran = set(suite(tree)), junit_modules(junit_path)
    out = [f"the job ran {m}, which the rule does not select" for m in sorted(ran - want)]
    out += [f"the rule selects {m}, which the job did not run" for m in sorted(want - ran)]
    return out


def main(argv) -> int:
    if argv[1:] == ["--list"]:
        print("\n".join(suite()))
        return 0
    if len(argv) == 3 and argv[1] == "--nodes":
        problems = nodes_problems(argv[2])
        for p in problems:
            print(p, file=sys.stderr)
        return 1 if problems else 0
    print(__doc__.strip().splitlines()[-2:], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
