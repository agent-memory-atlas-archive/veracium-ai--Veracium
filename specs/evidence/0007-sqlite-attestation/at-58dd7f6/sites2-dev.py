"""QUESTION: over every 0013-PA1 campaign path (the census INV-S10's gate would run over), is every write-issuing
`execute` call site in the functions the ladder enters observed at least once? A site never observed is a write the
gate's census cannot see on any fixture (the arity-INSERT shape of the step table). argv: <tree> <scratch>.
Static side: every Call to .execute/.executemany/.executescript inside each function that issued at least one recorded
write (by the recorder's issuing frame, file:func:line), matched to observations by the call's line span."""
import ast, collections, importlib.util, os, sys, tempfile
T = os.path.realpath(sys.argv[1])
spec = importlib.util.spec_from_file_location("pa1", f"{T}/specs/evidence/0013/pa1_campaign.py")
m = importlib.util.module_from_spec(spec); sys.modules["pa1"] = m; spec.loader.exec_module(m)
import veracium; assert os.path.realpath(veracium.__file__).startswith(T), veracium.__file__
path = os.path.join(tempfile.mkdtemp(dir=sys.argv[2]), "a.db")
kinds = collections.Counter(); L = m.lib(); seen = collections.Counter(); paths = 0
for label, _b, _a, _st in L["paths"]():
    m.fresh_fixture(path, label); paths += 1
    import veracium.store.migration as mig
    rec = []
    class Shim(L["_Shim"]):
        def connect(self, *a, **kw):
            return L["Proxy"](m.sqlite3.connect(*a, **kw), self.rec, self.plan)
    mig.sqlite3 = Shim(None, rec)
    try:
        mig.migrate_store(path)
    finally:
        mig.sqlite3 = m.sqlite3
    kinds.update(w["kind"] for w in rec)
    for w in rec:
        f, fn, ln = w["by"].rsplit(":", 2)
        seen[(f, fn, int(ln))] += 1
funcs = {(f, fn) for f, fn, _ in seen}
print("record kinds", dict(kinds)); print(f"campaign paths {paths}; observed write sites {len(seen)} in {len(funcs)} functions")
unobserved = []
for f in sorted({f for f, _ in funcs}):
    src = open(os.path.join(T, "src", f), encoding="utf-8").read()
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (f, node.name) in funcs):
            continue
        for c in ast.walk(node):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in (
                    "execute", "executemany", "executescript"):
                hit = sum(n for (sf, sfn, ln), n in seen.items()
                          if sf == f and sfn == node.name and c.lineno <= ln <= c.end_lineno)
                text = ast.get_source_segment(src, c) or ""
                first = text.split("(", 1)[1][:90].replace("\n", " ") if "(" in text else text[:90]
                row = (f, node.name, c.lineno, hit, first)
                print(f"  {'OBSERVED' if hit else 'NEVER   '} {f}:{node.name}:{c.lineno} x{hit}  {first}")
                if not hit:
                    unobserved.append(row)
print(f"execute sites in those functions never observed issuing a write: {len(unobserved)}")
