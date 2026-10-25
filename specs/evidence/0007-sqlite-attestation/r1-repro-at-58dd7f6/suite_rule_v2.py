"""Attestation-suite rule v2: every tests/**/test_*.py whose AST imports a root module (any depth,
Import or ImportFrom), or passes a root's specs file NAME inside the arguments of a call (loading the
file by path: spec_from_file_location, runpy, subprocess). A literal elsewhere (a fixture string, a
docstring, a message) does not admit a module."""
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
        elif isinstance(n, ast.Call):
            for a in list(n.args) + [k.value for k in n.keywords]:
                for c in ast.walk(a):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str):
                        why |= {"call:" + f for f in FILES if f in c.value}
    if why:
        hits.append((str(p.relative_to(tree)), sorted(why)))
for h in hits: print(h[0], ",".join(h[1]))
print("TOTAL", len(hits), file=sys.stderr)
