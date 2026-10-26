"""No module-level name in src/ is bound twice (0007 I1–I7, stage-1 read item 9).

schema_version.py carried three functions defined twice, with identical bodies
(`active_records`, `artifact_problems`, `manifestation_problems`) and a doubled
`_RUNTIME_OVERRIDE`. Python binds the LATER copy, so an edit made in the first
copy, the one a reader reaches first, is dead code: the suite runs the unedited
live copy, a red test stays red for no visible reason, and a mutant planted in
the first copy survives every test and reads as a weak test. The 0042 decision
inventory counted the dead copies' sites as well (1005 → 1002 when they went).

Scope: a module's own body only (def, async def, class, plain and annotated
assignment to a bare name). A name bound inside `if`/`try` at module level is a
conditional binding and is not counted; AugAssign extends a binding and is not
a second one.
"""
import ast
import collections
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "veracium"


def bound_twice(text: str) -> dict:
    """{name: [line, ...]} for every name the module body binds more than once."""
    seen = collections.defaultdict(list)
    for n in ast.parse(text).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            seen[n.name].append(n.lineno)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    seen[t.id].append(n.lineno)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            seen[n.target.id].append(n.lineno)
    return {k: v for k, v in seen.items() if len(v) > 1}


def test_the_checker_sees_each_binding_form():
    # every form it counts, doubled once; the conditional and augmented forms are not second bindings
    text = ("def f(): pass\ndef f(): pass\nclass C: pass\nclass C: pass\nasync def g(): pass\nasync def g(): pass\n"
            "x = 1\nx = 2\ny: list = []\ny: list = []\nz = 0\nz += 1\nif True:\n    z = 2\n")
    assert bound_twice(text) == {"f": [1, 2], "C": [3, 4], "g": [5, 6], "x": [7, 8], "y": [9, 10]}


def test_no_module_level_name_in_src_is_bound_twice():
    files = sorted(SRC.rglob("*.py"))
    assert len(files) > 50, f"found {len(files)} files under {SRC}: the walk is not reading the package"
    found = {str(f.relative_to(SRC)): d for f in files if (d := bound_twice(f.read_text(encoding="utf-8")))}
    assert not found, f"names bound twice at module level (the later binding is the live one): {found}"
