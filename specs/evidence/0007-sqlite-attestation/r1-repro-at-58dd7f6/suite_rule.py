"""Candidate attestation-suite rule: every tests/**/test_*.py whose AST imports a root module
(at any depth, Import or ImportFrom), or names a root's specs file in a string literal."""
import ast, pathlib, sys
ROOTS = ("sqlite3", "veracium.store.schema_version", "veracium.store.migration",
         "veracium.store.release_migration", "schema_evidence", "migrations_0013")
FILES = ("schema_evidence.py", "migrations_0013.py")
tree = pathlib.Path(sys.argv[1])
hits = []
for p in sorted((tree / "tests").rglob("test_*.py")):
    m = ast.parse(p.read_bytes())
    why = set()
    for n in ast.walk(m):
        if isinstance(n, ast.Import):
            why |= {a.name for a in n.names if a.name in ROOTS or any(a.name.startswith(r + ".") for r in ROOTS)}
        elif isinstance(n, ast.ImportFrom) and n.module:
            full = {n.module} | {f"{n.module}.{a.name}" for a in n.names}
            why |= {f for f in full if f in ROOTS}
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and any(f in n.value for f in FILES):
            why.add("str:" + next(f for f in FILES if f in n.value))
    if why:
        hits.append((str(p.relative_to(tree)), sorted(why)))
for h in hits: print(h[0], ",".join(h[1]))
print("TOTAL", len(hits), file=sys.stderr)
