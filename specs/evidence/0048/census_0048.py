"""0048 round 2 (R1-04): the two inventories 0048 cites, GENERATED from the AST of a source tree, never hand-counted.

    python census_0048.py <tree-root> [--json]

1. CONFIDENCE WRITERS: every call `<x>.model_copy(update=...)` and `<x>.model_construct(...)` under src/veracium.
   A `model_copy` whose `update` is a dict LITERAL, or a local dict built only with literal keys, is classified by
   its keys. The key may sit on any line of the call: v2's row 8 used a LINE grep and missed sqlite.py's
   consolidation site, whose "confidence" key is 18 lines below the call. An `update` that is not resolvable this
   way, a `**` spread, a local dict writing confidence, or any `model_construct`, is listed as UNRESOLVED and needs
   a reader's ruling, so the tool exits 1 while one exists. A copy replacing the whole `provenance` is listed
   separately: confidence travels inside the new value.
   A local dict resolves only if the function binds it ONLY that way and uses it ONLY as the `update=` value or the
   base of a literal-key store: a parameter, an alias (`v = u`), a call that receives it (`dict.update(u, …)`), any
   other binding, or a non-literal key in a literal (`{K: 2.0}`) is UNRESOLVED.
   Every other route that writes a field without validation is UNRESOLVED too: `model_copy(**kw)`, pydantic's
   `.copy(update=…)`, `copy.replace` / `__replace__`, a called `getattr(x, <one of those, or a non-literal name>)`,
   `setattr` / `object.__setattr__` naming `confidence` or a non-literal name, and any store into `__dict__`.
   (Stage 2, research 2026-10-11: v1 missed all of these, each planted on 1e80d4c, each executed and writing 2.0.)
2. EDGE JSON WRITERS: every string in src/veracium (constants, f-string parts, implicit and `+` concatenations of
   constants), whitespace-normalised and case-insensitive, that INSERTs or REPLACEs INTO `edges` (any `OR` clause,
   quoted or schema-qualified) or UPDATEs `edges` with `json` after its SET. A writer outside store/sqlite.py is
   UNRESOLVED: it is a path round 2's §4C helper would not cover.

Exit 0 only when nothing is UNRESOLVED. The counts are printed with the tree's path; a count without its tree and
this tool's digest is not a citation (research's standing rule).
"""
# Mutation-Matrix: tests/test_0048_evidence.py::test_census_0048_refuses_each_planted_defect
import ast
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1]).resolve()
src = root / "src" / "veracium"
copies, unresolved = [], []

def _local_literal_keys(fn, name, call):
    """The keys of a dict variable `name` in function `fn`, when it is built ONLY as `name = {<literal keys>}` and
    `name[<literal>] = ...` and READ only as `call`'s `update=` value; else None (a parameter, any other binding,
    mutation, alias or use makes it unresolvable)."""
    a = fn.args
    if name in {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None}:
        return None
    upd = next(k.value for k in call.keywords if k.arg == "update")
    stores = {id(m.targets[0].value) for m in ast.walk(fn) if isinstance(m, ast.Assign) and len(m.targets) == 1
              and isinstance(m.targets[0], ast.Subscript)}
    up = {id(c): m for m in ast.walk(fn) for c in ast.iter_child_nodes(m)}

    def _only_tested(m):
        """A read that cannot change the dict: a truth test, a comparison, `len(u)` / `bool(u)` (scope_read.py's
        `if not update:` is one)."""
        p = up.get(id(m))
        return ((isinstance(p, ast.UnaryOp) and isinstance(p.op, ast.Not)) or isinstance(p, ast.Compare)
                or (isinstance(p, (ast.If, ast.While, ast.IfExp, ast.Assert)) and p.test is m)
                or (isinstance(p, ast.Call) and getattr(p.func, "id", None) in ("len", "bool") and p.args == [m]))
    for m in ast.walk(fn):
        if isinstance(m, ast.Name) and m.id == name and isinstance(m.ctx, ast.Load) and m is not upd \
                and id(m) not in stores and not _only_tested(m):
            return None                                  # aliased, passed to a call, returned, ...
        if isinstance(m, (ast.Global, ast.Nonlocal)) and name in m.names:
            return None
        bound = (m.target if isinstance(m, (ast.For, ast.AsyncFor, ast.comprehension, ast.NamedExpr)) else
                 m.optional_vars if isinstance(m, ast.withitem) else
                 ast.Tuple(elts=m.targets) if isinstance(m, ast.Delete) else None)
        if bound is not None and any(isinstance(t, ast.Name) and t.id == name for t in ast.walk(bound)):
            return None                                  # bound by a loop, `with`, walrus or `del`
        if isinstance(m, (ast.Import, ast.ImportFrom)) and any((x.asname or x.name) == name for x in m.names):
            return None
    keys, seen = [], False
    for m in ast.walk(fn):
        if isinstance(m, ast.Assign):
            for t in m.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    if not isinstance(m.value, ast.Dict) or not all(isinstance(k, ast.Constant) for k in m.value.keys):
                        return None
                    keys += [k.value for k in m.value.keys]; seen = True
                elif isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == name:
                    if not isinstance(t.slice, ast.Constant):
                        return None
                    keys.append(t.slice.value)
        elif isinstance(m, (ast.AugAssign, ast.AnnAssign)) and getattr(m.target, "id", None) == name:
            return None
        elif (isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute) and isinstance(m.func.value, ast.Name)
              and m.func.value.id == name and m.func.attr in ("update", "setdefault", "__setitem__", "pop")):
            return None
    return keys if seen else None


provenance_replaced = []
UNVALIDATED = ("model_copy", "copy", "model_construct", "__replace__")
for f in sorted(src.rglob("*.py")):
    rel = f.relative_to(root).as_posix()
    tree = ast.parse(f.read_text(), filename=rel)
    parent = {}
    for fn in ast.walk(tree):                           # breadth-first: an inner function overwrites its outer one
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for m in ast.walk(fn):
                parent[id(m)] = fn
    copy_replace = {x.asname or x.name for m in ast.walk(tree) if isinstance(m, ast.ImportFrom) and m.module == "copy"
                    for x in m.names if x.name == "replace"}
    for n in ast.walk(tree):
        site = f"{rel}:{getattr(n, 'lineno', 0)}"
        if isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Store) and isinstance(n.value, ast.Attribute) \
                and n.value.attr == "__dict__":
            unresolved.append({"site": site, "why": "a store into `__dict__` skips validation"})
            continue
        if not isinstance(n, ast.Call):
            continue
        fn_, name = n.func, getattr(n.func, "attr", getattr(n.func, "id", None))
        if name in ("setattr", "__setattr__"):
            a = n.args[1] if len(n.args) > 1 else None
            if not (isinstance(a, ast.Constant) and a.value != "confidence"):
                unresolved.append({"site": site, "why": f"`{name}` naming `confidence` or a non-literal field"})
            continue
        if isinstance(fn_, ast.Call) and getattr(fn_.func, "id", None) == "getattr":
            a = fn_.args[1] if len(fn_.args) > 1 else None
            if not isinstance(a, ast.Constant) or a.value in UNVALIDATED:
                unresolved.append({"site": site, "why": "a called `getattr` that may reach an unvalidated copy"})
            continue
        if name == "__replace__" or (name == "replace" and isinstance(fn_, ast.Attribute)
                                     and getattr(fn_.value, "id", None) == "copy") \
                or (name in copy_replace and isinstance(fn_, ast.Name)):
            unresolved.append({"site": site, "why": "`copy.replace` copies without validation"})
            continue
        if not isinstance(fn_, ast.Attribute):
            continue
        if name == "model_construct":
            unresolved.append({"site": site, "why": "model_construct skips validation"})
            continue
        if name not in ("model_copy", "copy"):
            continue
        if any(k.arg is None for k in n.keywords):
            unresolved.append({"site": site, "why": f"`{name}(**...)`: the update cannot be read"})
            continue
        upd = next((k.value for k in n.keywords if k.arg == "update"), None)
        if upd is None:
            continue                                          # a plain copy writes no field
        if name == "copy":
            unresolved.append({"site": site, "why": "pydantic `.copy(update=...)` skips validation"})
            continue
        if isinstance(upd, ast.Name) and id(n) in parent:
            lk = _local_literal_keys(parent[id(n)], upd.id, n)
            if lk is not None:
                row = {"site": site, "keys": sorted(set(lk)), "resolved": f"local dict `{upd.id}`"}
                if "confidence" in lk:
                    unresolved.append({"site": row["site"], "why": "writes confidence through a local dict"})
                copies.append(row)
                continue
        if not isinstance(upd, ast.Dict) or any(k is None for k in upd.keys):
            unresolved.append({"site": site, "why": "update is not a dict literal (or spreads **)"})
            continue
        if not all(isinstance(k, ast.Constant) for k in upd.keys):
            unresolved.append({"site": site, "why": "a key that is not a literal"})
            continue
        keys = [k.value for k in upd.keys]
        row = {"site": site, "keys": keys}
        if "provenance" in keys:                     # replaces the WHOLE stamp: confidence travels in the new value
            provenance_replaced.append({"site": row["site"],
                                        "value": ast.unparse(upd.values[keys.index("provenance")])[:90]})
        if "confidence" in keys:
            i = keys.index("confidence")
            row["confidence_line"] = upd.keys[i].lineno
            row["confidence_expr"] = ast.unparse(upd.values[i])
        copies.append(row)

edge_sql = []
_T = r"""(?:["`\[]?\w+["`\]]?\s*\.\s*)?["`\[]?edges["`\]]?(?=[\s(]|$)"""
pat = re.compile(rf"\b(?:(?:INSERT(?:\s+OR\s+\w+)?|REPLACE)\s+INTO\s+{_T}|UPDATE(?:\s+OR\s+\w+)?\s+{_T}\s+SET\b.*\bjson\b)",
                 re.I | re.S)

def _text(n):
    """The constant text of a string expression: a constant, an f-string's literal parts, or a `+` chain of them."""
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.JoinedStr):
        return "".join(v.value for v in n.values if isinstance(v, ast.Constant))
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        a, b = _text(n.left), _text(n.right)
        return None if a is None or b is None else a + " " + b
    return None

for f in sorted(src.rglob("*.py")):
    rel = f.relative_to(src).as_posix()
    for n in ast.walk(ast.parse(f.read_text())):
        s = _text(n)
        if s and pat.search(" ".join(s.split())):
            if rel != "store/sqlite.py":
                unresolved.append({"site": f"src/veracium/{rel}:{n.lineno}",
                                   "why": "an edge json writer outside store/sqlite.py"})
            else:
                edge_sql.append({"line": n.lineno, "sql": " ".join(s.split())[:90]})
edge_sql = sorted({d["line"]: d for d in edge_sql}.values(), key=lambda d: d["line"])
unresolved = list({u["site"]: u for u in unresolved}.values())

writers = [c for c in copies if "confidence_line" in c]
out = {"tree": str(root), "model_copy_with_update": len(copies), "confidence_writers": writers,
       "provenance_replaced": provenance_replaced,
       "edge_json_writers": edge_sql, "unresolved": unresolved}
if "--json" in sys.argv:
    print(json.dumps(out, indent=1))
else:
    print(f"tree: {root}")
    print(f"model_copy(update=...) sites: {len(copies)}; of them write `confidence`: {len(writers)}")
    for w in writers:
        print(f"  {w['site']:42} key at L{w['confidence_line']}: {w['confidence_expr']}")
    print(f"model_copy sites replacing the whole `provenance` (confidence carried in the new value): {len(provenance_replaced)}")
    for r in provenance_replaced:
        print(f"  {r['site']:42} <- {r['value']}")
    for c in copies:
        if "resolved" in c:
            print(f"  resolved: {c['site']} {c['resolved']} keys {c['keys']}")
    print(f"edge json writers in store/sqlite.py: {len(edge_sql)}")
    for d in edge_sql:
        print(f"  L{d['line']}: {d['sql']}")
    print(f"UNRESOLVED: {len(unresolved)}")
    for u in unresolved:
        print(f"  {u['site']}: {u['why']}")
sys.exit(1 if unresolved else 0)
