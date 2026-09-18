#!/usr/bin/env python3
"""0042 round-1 amendment 4 — the domain of "enforcement point", MEASURED over all of src.

v3.1 bounded the domain with a lexical line count over five hand-chosen files
(162). The reviewer showed it is not a bound: it misses ordinary `return False`
decisions and excludes modules such as scope.py. This inventory replaces a chosen
domain with a measured one, and states its COUNTING UNIT so two seats get one
number:

  unit      one AST node of a listed DECISION KIND
  identity  (module, enclosing qualname, line)
  kinds     RAISE          a `raise` statement (bare re-raise included, flagged)
            RETURN_FALSE   `return False`
            RETURN_NONE    `return None` / bare `return` inside a function that
                           also has a non-None return (a decision to give nothing)
  domain    every src/veracium/**/*.py — nothing excluded, exclusions are for
            the spec to argue in words

It is an inventory of CANDIDATES by syntactic kind, not a census of confirmed
enforcement points: the spec's declaration must be compared against an inspected
subset of this, and a row here is where an inspector starts, not a verdict.

    python3 specs/evidence/0042/decision_site_inventory.py            # summary table
    python3 specs/evidence/0042/decision_site_inventory.py --write    # + JSON inventory beside this file
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "veracium"
OUT = pathlib.Path(__file__).with_name("decision_site_inventory_OUTPUT.json")
KINDS = ("RAISE", "RETURN_FALSE", "RETURN_NONE")


class _Walker(ast.NodeVisitor):
    def __init__(self, module: str):
        self.module, self.stack, self.rows = module, [], []

    def _qual(self):
        return ".".join(self.stack) or "<module>"

    def visit_ClassDef(self, node):
        self.stack.append(node.name); self.generic_visit(node); self.stack.pop()

    def _visit_fn(self, node):
        self.stack.append(node.name)
        returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
        has_value = any(r.value is not None and not (isinstance(r.value, ast.Constant) and r.value.value is None)
                        for r in returns)
        self._fn_has_value = getattr(self, "_fn_has_value", [])
        self._fn_has_value.append(has_value)
        self.generic_visit(node)
        self._fn_has_value.pop(); self.stack.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = _visit_fn

    def visit_Raise(self, node):
        self.rows.append({"module": self.module, "qualname": self._qual(), "line": node.lineno,
                          "kind": "RAISE", "bare": node.exc is None})
        self.generic_visit(node)

    def visit_Return(self, node):
        v = node.value
        if isinstance(v, ast.Constant) and v.value is False:
            self.rows.append({"module": self.module, "qualname": self._qual(), "line": node.lineno,
                              "kind": "RETURN_FALSE"})
        elif (v is None or (isinstance(v, ast.Constant) and v.value is None)) and \
                getattr(self, "_fn_has_value", [False])[-1:] == [True]:
            self.rows.append({"module": self.module, "qualname": self._qual(), "line": node.lineno,
                              "kind": "RETURN_NONE"})
        self.generic_visit(node)


def inventory() -> list[dict]:
    rows = []
    for p in sorted(SRC.rglob("*.py")):
        mod = str(p.relative_to(SRC))
        w = _Walker(mod); w.visit(ast.parse(p.read_text())); rows += w.rows
    return rows


def summary(rows: list[dict]) -> dict:
    per: dict[str, dict] = {}
    for r in rows:
        per.setdefault(r["module"], {k: 0 for k in KINDS})[r["kind"]] += 1
    return {"unit": "one AST node of a listed decision kind; identity (module, qualname, line)",
            "kinds": KINDS, "modules_scanned": len(list(SRC.rglob("*.py"))),
            "modules_with_sites": len(per), "total": len(rows),
            "by_kind": {k: sum(1 for r in rows if r["kind"] == k) for k in KINDS},
            "per_module": dict(sorted(per.items()))}


if __name__ == "__main__":
    rows = inventory(); s = summary(rows)
    print(f"modules scanned {s['modules_scanned']}, with sites {s['modules_with_sites']}, "
          f"sites {s['total']}  by kind {s['by_kind']}")
    print(f"{'module':34s} {'RAISE':>6} {'RET_F':>6} {'RET_N':>6}")
    for m, c in s["per_module"].items():
        print(f"{m:34s} {c['RAISE']:6d} {c['RETURN_FALSE']:6d} {c['RETURN_NONE']:6d}")
    if "--write" in sys.argv:
        OUT.write_text(json.dumps({"summary": s, "sites": rows}, indent=1, sort_keys=True) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
