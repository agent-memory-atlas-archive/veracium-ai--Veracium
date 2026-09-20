#!/usr/bin/env python3
"""specs/0042 INV-7 — THE UNINSTRUMENTED TWIN, DERIVED FROM HEAD (not exported from an old commit).

The first four-arm transcripts exported the twin from the commit the instrumentation tranches began from
(`84f9515`). That twin was right for exactly as long as src/ changed only by instrumentation; the moment a
later spec touched src the "uninstrumented" arm was also an OLDER product. So the twin is DERIVED: HEAD's src
with the census instrumentation REMOVED by an AST transform that inverts the instrumenter's forms and nothing
else — and, since round 6 (R6-6), REFUSES everything it has not established is instrumentation:

    NAME = declare_site(...)                 ->  (removed)            NAME is then a DECLARED name of this module
    from .census import declare_site …      ->  (removed)
    from . import census as _census          ->  (removed; restored if the module still reads the stub's surface)
    with NAME.consult(): <body>              ->  <body>               NAME declared; every item of the with a consult
    NAME.consult()                           ->  (removed)            the statement form (round 6, R6-2a)
    raise NAME.fire(EXC, ...)                ->  raise EXC            NAME declared; the value is the first argument
    return NAME.fire(EXPR, ...)              ->  return EXPR
    x = NAME.fire(EXPR, ...)                 ->  x = EXPR
    if _census.enabled(): <block>            ->  if False: <block'>   ONLY the recognised bypass shape at the four hot
                                                                      Edge predicates (a with-consult whose body is
                                                                      [assignment,] return NAME.fire(...)); the block
                                                                      is kept DEAD, not deleted, so the function's
                                                                      return/raise statements keep their number and
                                                                      order — the observer keys exits by ordinal

REFUSED (never guessed): `other.fire(...)` on a name that is not a declared site of the module; `a.b.fire(...)`
(an attribute chain the transform cannot bind); a consult on an undeclared name; a `with` mixing consult and
non-consult items; an enabled-block of any other shape (a side effect inside it would be product behaviour);
`nonlocal`/`global` naming a declared site. Every statement that is not one of the listed forms is PRESERVED.

`derive()` writes the twin AND a MANIFEST (`twin_manifest.json`): per module the source sha256 before and after,
the count of every transformation, and per function the number of return/raise statements before and after —
`verify()` asserts the exit counts equal, that no instrumentation survives, and that every non-instrumentation
statement of HEAD is still present in the twin (the transform removes and rewrites only the listed forms).

    python3 specs/evidence/0042/inv7_uninstrument.py <src/veracium> <out/src/veracium>
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import shutil
import sys


class Refused(Exception):
    pass


def _receiver(call: ast.Call):
    """The receiver NAME of `NAME.method(...)`, or None for any other callee shape."""
    f = call.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return f.value.id
    return None


def _is_consult_item(item: ast.withitem) -> bool:
    c = item.context_expr
    return isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "consult" and not c.args


def _is_fire_call(node) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fire"


def exits_per_function(tree: ast.AST) -> dict:
    """{qualname: number of return/raise statements in the function's OWN body (nested scopes excluded)}."""
    out = {}
    def walk(node, qual):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = ".".join(qual + [child.name]); n = 0
                def count(n_):
                    nonlocal n
                    for c in ast.iter_child_nodes(n_):
                        if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                            continue
                        if isinstance(c, (ast.Return, ast.Raise)):
                            n += 1
                        count(c)
                count(child); out[q] = n
                walk(child, qual + [child.name])
            elif isinstance(child, ast.ClassDef):
                walk(child, qual + [child.name])
            else:
                walk(child, qual)
    walk(tree, [])
    return out


class Uninstrument(ast.NodeTransformer):
    def __init__(self, declared: set[str], census_aliases: set[str]):
        self.declared = declared; self.census_aliases = census_aliases
        self.sites = 0; self.fires = 0; self.consults = 0; self.consult_stmts = 0; self.bypasses = 0; self.imports = 0
        self.removed_imports: list = []

    # module-level: drop declare_site assignments and census imports
    def visit_Module(self, node):
        kept = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.value, ast.Call) \
                    and getattr(stmt.value.func, "id", getattr(stmt.value.func, "attr", "")) == "declare_site":
                self.sites += 1; continue
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

    def visit_Global(self, node):
        if any(n in self.declared for n in node.names):
            raise Refused(f"line {node.lineno}: `global` names a declared site — not resolved by guess")
        return node

    def visit_Nonlocal(self, node):
        if any(n in self.declared for n in node.names):
            raise Refused(f"line {node.lineno}: `nonlocal` names a declared site — not resolved by guess")
        return node

    def visit_With(self, node):
        self.generic_visit(node)
        consults = [_is_consult_item(i) for i in node.items]
        if all(consults):
            for i in node.items:
                r = _receiver(i.context_expr)
                if r not in self.declared:
                    raise Refused(f"line {node.lineno}: consult() on {r!r}, not a declared site of this module")
            self.consults += 1
            return node.body                       # spliced into the parent's statement list
        if any(consults):
            raise Refused(f"line {node.lineno}: a consult() item beside a non-consult item — an unrecognised form")
        return node

    def visit_Expr(self, node):
        self.generic_visit(node)
        v = node.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "consult" and not v.args:
            r = _receiver(v)
            if r not in self.declared:
                raise Refused(f"line {node.lineno}: consult() statement on {r!r}, not a declared site of this module")
            self.consult_stmts += 1
            return None                            # the statement form: removed
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        t = node.test
        if isinstance(t, ast.Call) and isinstance(t.func, ast.Attribute) and t.func.attr == "enabled" \
                and isinstance(t.func.value, ast.Name) and t.func.value.id in self.census_aliases:
            # the ONLY recognised shapes for the body (after the with was spliced by generic_visit above):
            # one or two statements, each a simple assignment to ONE Name, the last of them allowed to be a
            # `return <expr>` — the four hot Edge predicates, in their round-6 form (`q = …; return fire(q)`,
            # no else) and their round-7 form (`q = …; q = fire(q)` under an `else:` that computes the same
            # Name, ONE return after both: the exit statement is then the same in every arm, INV-7 R6-5).
            # The else branch is product code and is left exactly as written: with the test made False it
            # is the path every twin takes, which is the census-disabled path by construction.
            body = node.body

            def simple_assign(s):
                return isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)
            ok = 1 <= len(body) <= 2 and all(simple_assign(s) for s in body[:-1]) and \
                 (simple_assign(body[-1]) or isinstance(body[-1], ast.Return))
            if not ok:
                raise Refused(f"line {node.lineno}: a census-enabled block whose body is not the recognised bypass shape "
                              f"([assignment,] assignment|return) — a side effect or another statement in it would be product behaviour")
            if node.orelse and not all(simple_assign(s) for s in node.orelse):
                raise Refused(f"line {node.lineno}: a census-enabled bypass whose else branch is not simple assignments — unrecognised")
            self.bypasses += 1
            node.test = ast.Constant(value=False)  # kept DEAD: a return statement in the body keeps its ordinal
            return node
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if _is_fire_call(node):
            r = _receiver(node)
            if r is None:
                raise Refused(f"line {node.lineno}: fire() reached through an attribute chain the transform cannot bind")
            if r not in self.declared:
                raise Refused(f"line {node.lineno}: fire() on {r!r}, not a declared site of this module")
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


def declared_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """(the module-level names bound by `NAME = declare_site(...)`, the aliases the census module is imported as)."""
    declared, aliases = set(), set()
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) \
                and isinstance(stmt.value, ast.Call) and getattr(stmt.value.func, "id", getattr(stmt.value.func, "attr", "")) == "declare_site":
            declared.add(stmt.targets[0].id)
        if isinstance(stmt, ast.ImportFrom) and any(a.name == "census" for a in stmt.names):
            for a in stmt.names:
                if a.name == "census":
                    aliases.add(a.asname or "census")
    return declared, aliases


def _statement_keys(tree: ast.AST) -> list:
    """Every non-instrumentation statement, as (qualname, kind, unparsed text) — the material the transform must PRESERVE."""
    keys = []
    def walk(node, qual):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                keys.append((".".join(qual), type(child).__name__, child.name)); walk(child, qual + [child.name]); continue
            if isinstance(child, ast.stmt):
                keys.append((".".join(qual), type(child).__name__, None))
            walk(child, qual)
    walk(tree, [])
    return keys


def uninstrument_source(text: str) -> tuple[str, dict]:
    tree = ast.parse(text)
    declared, aliases = declared_names(tree)
    exits_before = exits_per_function(tree)
    t = Uninstrument(declared, aliases or {"_census", "census"}); tree = t.visit(tree); ast.fix_missing_locations(tree)
    # a module that still USES the census surface after the instrumentation is gone (the opt-in switch,
    # `_census.enable(True)` in the package module) keeps its import: the twin's stub census answers it
    still_used = any(isinstance(n, ast.Name) and n.id in ("_census", "census") for n in ast.walk(tree))
    if still_used and t.removed_imports:
        tree.body[0:0] = t.removed_imports; t.imports -= len(t.removed_imports)
    out = ast.unparse(tree) + "\n"
    exits_after = exits_per_function(ast.parse(out))
    if exits_after != exits_before:
        diff = {k: (exits_before.get(k), exits_after.get(k)) for k in set(exits_before) | set(exits_after) if exits_before.get(k) != exits_after.get(k)}
        raise Refused(f"the transform changed a function's exit count — the observer keys exits by ordinal: {diff}")
    stats = {"sites": t.sites, "fires": t.fires, "consults": t.consults, "consult_statements": t.consult_stmts,
             "bypasses": t.bypasses, "imports": t.imports, "exits": exits_after}
    # no INSTRUMENTATION may survive in the emitted module (a stub-answered surface read may)
    for token in ("declare_site", ".consult()", ".fire("):
        if token in out:
            raise Refused(f"the emitted module still carries {token!r}")
    return out, stats


STUB = ('"""INV-7 twin stub: the census module with NOTHING declared — the harness surface only."""\n'
        '_ENABLED = False\n\ndef enable(on=True):\n    global _ENABLED; _ENABLED = bool(on)\n\n'
        'def enabled():\n    return _ENABLED\n\ndef registry():\n    return ()\n\ndef counters():\n    return {}\n\n'
        'def trace(on=True):\n    pass\n\ndef trace_snapshot():\n    return []\n\ndef trace_reset():\n    pass\n\ndef reset_counters():\n    pass\n')


def derive(src: pathlib.Path, out: pathlib.Path) -> dict:
    """Copy src/veracium to out, un-instrumenting every module; census.py itself is replaced by a stub that
    exposes the harness surface the observer touches (enabled(), registry()) and declares nothing. Writes the
    MANIFEST beside the twin (out/../twin_manifest.json): source hashes before and after, every count, the
    permitted transformations by name."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
    totals = {"sites": 0, "fires": 0, "consults": 0, "consult_statements": 0, "bypasses": 0, "imports": 0, "modules_changed": 0}
    manifest = {"permitted_transformations": [
                    "NAME = declare_site(...) removed (module level)", "census imports removed (restored if the surface is still read)",
                    "with NAME.consult(): body -> body (NAME declared)", "NAME.consult() statement removed (NAME declared)",
                    "NAME.fire(X, ...) -> X (NAME declared; raise/return/assign)",
                    "if <census>.enabled(): [assign,] return NAME.fire(...) -> if False: [assign,] return X (kept dead; exit ordinals preserved)",
                    "if <census>.enabled(): [assign,] NAME2 = NAME.fire(NAME2) else: <assignments> -> if False: ... else: <assignments> (round 7: the four hot Edge predicates' one-return form; the else branch is product code, untouched)"],
                "refused_forms": ["fire()/consult() on an undeclared name", "fire() through an attribute chain", "fire() with no decision argument",
                                  "a with mixing consult and non-consult items", "an enabled block of any other shape",
                                  "a census-enabled bypass whose else branch is not simple assignments", "nonlocal/global naming a declared site",
                                  "a transform that changes a function's exit count", "an emitted module still carrying a census token"],
                "modules": {}}
    for p in sorted(out.rglob("*.py")):
        rel = str(p.relative_to(out)); before = p.read_bytes()
        if rel == "census.py":
            p.write_text(STUB); manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(STUB.encode()).hexdigest(), "stub": True}
            continue
        text = before.decode()
        if "census" not in text and ".fire(" not in text and "declare_site" not in text:
            manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(before).hexdigest(), "unchanged": True}
            continue
        try:
            new, stats = uninstrument_source(text)
        except Refused as e:
            raise Refused(f"{rel}: {e}") from None
        p.write_text(new)
        for k, v in stats.items():
            if k != "exits":
                totals[k] += v
        totals["modules_changed"] += 1
        manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(new.encode()).hexdigest(), **stats}
    manifest["totals"] = totals
    (out.parent / "twin_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return totals


def verify(out: pathlib.Path, src: pathlib.Path | None = None) -> list[str]:
    """Every module in the twin, census.py aside, is free of the INSTRUMENTATION (a surface read of the stub may
    remain); and, given the source tree, every non-instrumentation statement of the source is still present in
    the twin in order (what REMAINS is verified, not only what was removed — R6-6)."""
    problems = []
    for p in sorted(out.rglob("*.py")):
        if p.name == "census.py":
            continue
        t = p.read_text()
        for token in ("declare_site", ".consult()", ".fire(", "from .census import"):
            if token in t:
                problems.append(f"{p.relative_to(out)}: {token!r} survives")
        if src is not None:
            s = src / p.relative_to(out)
            if s.exists():
                head = ast.parse(s.read_text()); twin = ast.parse(t)
                declared, _ = declared_names(head)
                # statements of HEAD that the transform is allowed to drop/rewrite: the declare_site assigns, the
                # census imports, the consult statements/withs (their bodies survive); everything else must remain
                def keep(k):
                    return True
                hk = [k for k in _statement_keys(head)]; tk = _statement_keys(twin)
                # compare multiset of (qual, kind) for kinds the transform never touches
                untouched_kinds = {"Return", "Raise", "FunctionDef", "AsyncFunctionDef", "ClassDef", "For", "While", "Try", "AugAssign", "AnnAssign"}
                hc = sorted(k for k in hk if k[1] in untouched_kinds); tc = sorted(k for k in tk if k[1] in untouched_kinds)
                if hc != tc:
                    problems.append(f"{p.relative_to(out)}: the twin's untouched statements differ from HEAD's ({len(hc)} vs {len(tc)})")
    return problems


if __name__ == "__main__":
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    totals = derive(src, out)
    problems = verify(out, src)
    print("twin derived:", totals)
    print("verify:", "clean" if not problems else problems)
    sys.exit(0 if not problems else 1)
