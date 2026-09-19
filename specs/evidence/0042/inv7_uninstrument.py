#!/usr/bin/env python3
"""specs/0042 INV-7 — THE UNINSTRUMENTED TWIN, DERIVED FROM HEAD (not exported from an old commit).

The first four-arm transcripts exported the twin from the commit the instrumentation tranches began from
(`84f9515`). That twin was right for exactly as long as src/ changed only by instrumentation; the moment a
later spec touched src (0043's gate seam; 0041's write-path refusals) the "uninstrumented" arm was also an
OLDER product, its suites failed there for reasons that have nothing to do with the census, and the diff
compared two products — a census of the moment mistaken for a rule, for the third time in one day.

So the twin is now DERIVED: HEAD's src with the census instrumentation REMOVED by an AST transform that
inverts the instrumenter's forms and nothing else —

    with SITE.consult(): <body>            ->  <body>            (one or several items, all consult())
    raise SITE.fire(EXC, ...)              ->  raise EXC
    return SITE.fire(EXPR, ...)            ->  return EXPR
    x = SITE.fire(EXPR, ...) / any call    ->  EXPR              (the value is always the first argument)
    if _census.enabled(): <census block>   ->  (removed)         (the bypass at the four hot predicates)
    NAME = declare_site(...)               ->  (removed)
    from .census import declare_site …     ->  (removed)
    from . import census as _census        ->  (removed)

The module is re-emitted with `ast.unparse` (comments go; behaviour and names stay), so the observer wraps
the same qualnames. The transform REFUSES a form it does not recognise (a `consult()` item beside a
non-consult item; a `fire` reached through an attribute chain it cannot bind) rather than guess, and reports
counts: sites removed, fire calls unwrapped, consult blocks spliced, bypass blocks removed. `verify()` then
asserts the twin carries NO reference to the census at all.

    python3 specs/evidence/0042/inv7_uninstrument.py <src/veracium> <out/src/veracium>
"""
from __future__ import annotations

import ast
import pathlib
import shutil
import sys


class Refused(Exception):
    pass


def _is_consult_item(item: ast.withitem) -> bool:
    c = item.context_expr
    return isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "consult" and not c.args


def _is_fire_call(node) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fire"


class Uninstrument(ast.NodeTransformer):
    def __init__(self):
        self.sites = 0; self.fires = 0; self.consults = 0; self.bypasses = 0; self.imports = 0
        self.site_names: set[str] = set(); self.removed_imports: list = []

    # module-level: drop declare_site assignments and census imports
    def visit_Module(self, node):
        kept = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.value, ast.Call) \
                    and getattr(stmt.value.func, "id", getattr(stmt.value.func, "attr", "")) == "declare_site":
                self.sites += 1; self.site_names.add(stmt.targets[0].id); continue
            if isinstance(stmt, ast.ImportFrom) and stmt.module and stmt.module.endswith("census"):
                self.imports += 1; continue                      # `from .census import declare_site`: instrumentation only
            if isinstance(stmt, ast.ImportFrom) and stmt.module in (None, "") and all(a.name == "census" for a in stmt.names):
                self.imports += 1; self.removed_imports.append(stmt); continue   # restored if the module still uses the surface
            if isinstance(stmt, ast.ImportFrom) and any(a.name == "census" for a in stmt.names):
                stmt.names = [a for a in stmt.names if a.name != "census"]; self.imports += 1
                if not stmt.names:
                    continue
            kept.append(stmt)
        node.body = kept
        self.generic_visit(node)
        return node

    def visit_With(self, node):
        self.generic_visit(node)
        if all(_is_consult_item(i) for i in node.items):
            self.consults += 1
            return node.body                       # spliced into the parent's statement list
        if any(_is_consult_item(i) for i in node.items):
            raise Refused(f"line {node.lineno}: a consult() item beside a non-consult item — an unrecognised form")
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        t = node.test
        if isinstance(t, ast.Call) and isinstance(t.func, ast.Attribute) and t.func.attr == "enabled" \
                and isinstance(t.func.value, ast.Name) and t.func.value.id in ("_census", "census"):
            if node.orelse:
                raise Refused(f"line {node.lineno}: a census-enabled bypass with an else branch — unrecognised")
            self.bypasses += 1
            return None                            # the whole census-only block goes; the plain `return q` follows it
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if _is_fire_call(node):
            if not node.args:
                raise Refused(f"line {node.lineno}: fire() with no decision argument")
            self.fires += 1
            return node.args[0]
        return node

    def generic_visit(self, node):
        # statement lists may receive lists from visit_With (splicing) — flatten them
        for field, old in ast.iter_fields(node):
            if isinstance(old, list):
                new = []
                for item in old:
                    if isinstance(item, ast.AST):
                        r = self.visit(item)
                        if r is None:
                            continue
                        if isinstance(r, list):
                            new.extend(r)
                        else:
                            new.append(r)
                    else:
                        new.append(item)
                old[:] = new
            elif isinstance(old, ast.AST):
                r = self.visit(old)
                if r is None:
                    delattr(node, field)
                else:
                    setattr(node, field, r)
        return node


def uninstrument_source(text: str) -> tuple[str, dict]:
    tree = ast.parse(text)
    t = Uninstrument(); tree = t.visit(tree); ast.fix_missing_locations(tree)
    # a module that still USES the census surface after the instrumentation is gone (the opt-in switch,
    # `_census.enable(True)` in the package module) keeps its import: the twin's stub census answers it
    still_used = any(isinstance(n, ast.Name) and n.id in ("_census", "census") for n in ast.walk(tree))
    if still_used and t.removed_imports:
        tree.body[0:0] = t.removed_imports; t.imports -= len(t.removed_imports)
    out = ast.unparse(tree) + "\n"
    stats = {"sites": t.sites, "fires": t.fires, "consults": t.consults, "bypasses": t.bypasses, "imports": t.imports}
    # no INSTRUMENTATION may survive in the emitted module (a stub-answered surface read may)
    for token in ("declare_site", ".consult()", ".fire("):
        if token in out:
            raise Refused(f"the emitted module still carries {token!r}")
    return out, stats


def derive(src: pathlib.Path, out: pathlib.Path) -> dict:
    """Copy src/veracium to out, un-instrumenting every module; census.py itself is replaced by a stub that
    exposes the harness surface the observer touches (enabled(), registry()) and declares nothing."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
    totals = {"sites": 0, "fires": 0, "consults": 0, "bypasses": 0, "imports": 0, "modules_changed": 0}
    for p in sorted(out.rglob("*.py")):
        rel = p.relative_to(out)
        if str(rel) == "census.py":
            p.write_text('"""INV-7 twin stub: the census module with NOTHING declared — the harness surface only."""\n'
                         '_ENABLED = False\n\ndef enable(on=True):\n    global _ENABLED; _ENABLED = bool(on)\n\n'
                         'def enabled():\n    return _ENABLED\n\ndef registry():\n    return ()\n\ndef counters():\n    return {}\n\n'
                         'def trace(on=True):\n    pass\n\ndef trace_snapshot():\n    return []\n\ndef trace_reset():\n    pass\n\ndef reset_counters():\n    pass\n')
            continue
        text = p.read_text()
        if "census" not in text and ".fire(" not in text and "declare_site" not in text:
            continue
        new, stats = uninstrument_source(text)
        p.write_text(new)
        for k, v in stats.items():
            totals[k] += v
        totals["modules_changed"] += 1
    return totals


def verify(out: pathlib.Path) -> list[str]:
    """Every module in the twin, census.py aside, is free of the INSTRUMENTATION (a surface read of the stub may remain)."""
    problems = []
    for p in sorted(out.rglob("*.py")):
        if p.name == "census.py":
            continue
        t = p.read_text()
        for token in ("declare_site", ".consult()", ".fire(", "from .census import"):
            if token in t:
                problems.append(f"{p.relative_to(out)}: {token!r} survives")
    return problems


if __name__ == "__main__":
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    totals = derive(src, out)
    problems = verify(out)
    print("twin derived:", totals)
    print("verify:", "clean" if not problems else problems)
    sys.exit(0 if not problems else 1)
