"""0048 round 2 (R1-04): the two inventories 0048 cites, GENERATED from the AST of a source tree, never hand-counted.

    python census_0048.py <tree-root> [--json]

1. CONFIDENCE WRITERS: every call `<x>.model_copy(update=...)` and `<x>.model_construct(...)` under src/veracium.
   A `model_copy` whose `update` is a dict LITERAL, or a local dict built only with literal keys, is classified by
   its keys. The key may sit on any line of the call: v2's row 8 used a LINE grep and missed sqlite.py's
   consolidation site, whose "confidence" key is 18 lines below the call. An `update` that is not resolvable this
   way, a `**` spread, a local dict writing confidence, or any `model_construct`, is listed as UNRESOLVED and needs
   a reader's ruling, so the tool exits 1 while one exists. A copy replacing the whole `provenance` is listed
   separately: confidence travels inside the new value.
2. EDGE JSON WRITERS: every string constant (f-string parts and implicit concatenations joined) in
   src/veracium/store/sqlite.py that INSERTs into `edges` or UPDATEs `edges` setting `json`.

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

def _local_literal_keys(fn, name):
    """The keys of a dict variable `name` in function `fn`, when it is built ONLY as `name = {<literal keys>}` and
    `name[<literal>] = ...`; else None (any other binding, mutation or alias makes it unresolvable)."""
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
for f in sorted(src.rglob("*.py")):
    rel = f.relative_to(root).as_posix()
    tree = ast.parse(f.read_text(), filename=rel)
    parent = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for m in ast.walk(fn):
                parent.setdefault(id(m), fn)
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        if n.func.attr == "model_construct":
            unresolved.append({"site": f"{rel}:{n.lineno}", "why": "model_construct skips validation"})
            continue
        if n.func.attr != "model_copy":
            continue
        upd = next((k.value for k in n.keywords if k.arg == "update"), None)
        if upd is None:
            continue                                          # a plain copy writes no field
        if isinstance(upd, ast.Name) and id(n) in parent:
            lk = _local_literal_keys(parent[id(n)], upd.id)
            if lk is not None:
                row = {"site": f"{rel}:{n.lineno}", "keys": sorted(set(lk)), "resolved": f"local dict `{upd.id}`"}
                if "confidence" in lk:
                    unresolved.append({"site": row["site"], "why": "writes confidence through a local dict"})
                copies.append(row)
                continue
        if not isinstance(upd, ast.Dict) or any(k is None for k in upd.keys):
            unresolved.append({"site": f"{rel}:{n.lineno}", "why": "update is not a dict literal (or spreads **)"})
            continue
        keys = [k.value if isinstance(k, ast.Constant) else ast.unparse(k) for k in upd.keys]
        row = {"site": f"{rel}:{n.lineno}", "keys": keys}
        if "provenance" in keys:                     # replaces the WHOLE stamp: confidence travels in the new value
            provenance_replaced.append({"site": row["site"],
                                        "value": ast.unparse(upd.values[keys.index("provenance")])[:90]})
        if "confidence" in keys:
            i = keys.index("confidence")
            row["confidence_line"] = upd.keys[i].lineno
            row["confidence_expr"] = ast.unparse(upd.values[i])
        copies.append(row)

edge_sql = []
sq = src / "store" / "sqlite.py"
pat = re.compile(r"INSERT (OR [A-Z]+ )?INTO edges\b|UPDATE edges SET[^\"']*\bjson\b")
for n in ast.walk(ast.parse(sq.read_text())):
    s = None
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        s = n.value
    elif isinstance(n, ast.JoinedStr):
        s = "".join(v.value for v in n.values if isinstance(v, ast.Constant))
    if s and pat.search(s):
        edge_sql.append({"line": n.lineno, "sql": " ".join(s.split())[:90]})
edge_sql = sorted({d["line"]: d for d in edge_sql}.values(), key=lambda d: d["line"])

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
