# Classify cov.py's never-executed lines in one source file: EXEMPT if inside an if/else/except block whose last
# statement is `raise` (dev's proposed property), else FLAGGED. argv: <cov output> <src root> <relative file>
import ast, re, sys
out, root, rel = sys.argv[1:4]
src = open(f"{root}/{rel}").read(); tree = ast.parse(src)
blocks = []
for n in ast.walk(tree):
    for field in ("body", "orelse", "handlers", "finalbody"):
        b = getattr(n, field, None)
        if isinstance(n, (ast.If, ast.ExceptHandler, ast.Try, ast.For, ast.While, ast.With)) and isinstance(b, list) and b and isinstance(b[0], ast.stmt):
            blocks.append((b[0].lineno, b[-1].end_lineno, isinstance(b[-1], ast.Raise)))
        if isinstance(n, ast.Try) and field == "handlers":
            for h in n.handlers:
                blocks.append((h.body[0].lineno, h.body[-1].end_lineno, isinstance(h.body[-1], ast.Raise)))
ex = fl = 0; flagged = []
for line in open(out):
    m = re.match(rf"\s+{re.escape(rel.split('veracium/',1)[-1])}:(\S+)@\d+\s+\d+/\d+ missed: \[(.*)\]", line)
    if not m: continue
    fn = m.group(1)
    for l in map(int, m.group(2).split(", ")):
        inner = [b for b in blocks if b[0] <= l <= b[1]]
        inner = min(inner, key=lambda b: b[1] - b[0]) if inner else None
        if inner and inner[2]: ex += 1
        else: fl += 1; flagged.append((fn, l))
print(f"{rel}: never-executed {ex + fl}; exempt (raise-ending block) {ex}; FLAGGED {fl}")
by = {}
for fn, l in flagged: by.setdefault(fn, []).append(l)
for fn, ls in by.items(): print(f"  {fn}: {ls}")
