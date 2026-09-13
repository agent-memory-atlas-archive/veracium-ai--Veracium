"""Shared AST sweep for 0037's producer invariant (V-TWO-PRODUCERS, v19 form)."""
import ast, pathlib


def stamp_forms(path: pathlib.Path) -> dict:
    """Returns {"literal": bool, "suspicious": [descriptions]} for one file:
    literal = a call passes record_kind="procedural" as a constant keyword;
    suspicious = a record_kind keyword whose value is NOT a constant, a
    Provenance(**...) call, or a dict literal with a "record_kind" key."""
    tree = ast.parse(path.read_text())
    literal, suspicious = False, []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            for k in n.keywords:
                if k.arg == "record_kind":
                    if isinstance(k.value, ast.Constant) and k.value.value == "procedural":
                        literal = True
                    elif not isinstance(k.value, ast.Constant):
                        suspicious.append(f"line {n.lineno}: record_kind=<non-literal>")
                if k.arg is None and getattr(n.func, "id", getattr(n.func, "attr", "")) == "Provenance":
                    suspicious.append(f"line {n.lineno}: Provenance(**...)")
        if isinstance(n, ast.Dict):
            for key in n.keys:
                if isinstance(key, ast.Constant) and key.value == "record_kind":
                    suspicious.append(f"line {n.lineno}: dict literal with a 'record_kind' key")
    return {"literal": literal, "suspicious": suspicious}
