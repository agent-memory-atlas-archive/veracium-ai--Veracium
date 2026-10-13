"""One module name, two files, one process: the race the round-3 suite found.

Both package models named their runner `run_model.py`; package I's obligation map imported model I's by bare name,
and on one shuffled worker model_citations then received model I's runner (its mutants carry no `answers`: two tests
failed, seed 3901382873). Python binds a bare module name ONCE per process (`sys.modules`), so whichever file is
imported first under a shared name wins for every later importer. The class is closed by two rules over DERIVED sets
(research's conditions, 2026-10-13):

  shared stems   every `.py` stem tracked under `specs/` and `tests/` that names two or more files.
  rule A         a stem shared by any EVIDENCE file (`specs/evidence/`) is never imported bare — by `import X`,
                 `from X import`, `__import__("X")` or `import_module("X")` — anywhere under `specs/` or `tests/`.
                 Evidence modules are loaded by file under a unique name (`spec_from_file_location`).
  rule B         for every OTHER shared stem, the collected test modules (`tests/**/test_*.py`) that import it bare all
                 resolve it to ONE directory: the importer's own directory if it holds that file, else the one
                 candidate directory whose name the importer's source spells (its `sys.path.insert`). Ambiguous or
                 unresolved fails closed.

THE NARROWING, stated (research asked that it never be silent): rule B judges only collected test modules, because a
standalone script (the longmemeval and robustness harness CLIs, 0019's phase scripts) runs in its own interpreter, where
one bare binding is all there is. A test that loads such a harness in-process loads it by path and restores the binding
(test_0021's `_robustness_accumulators` precedent). The opt-in robustness tier (`VERACIUM_ROBUSTNESS=1`) imports its
harness, which binds `adapter` bare to the robustness copy; it is outside the default suite, named here as the residual.
"""
from __future__ import annotations

import ast
import collections
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _tracked():
    out = subprocess.run(["git", "ls-files", "specs", "tests"], capture_output=True, text=True, cwd=ROOT)
    if out.returncode == 0 and out.stdout.strip():
        return sorted(f for f in out.stdout.split() if f.endswith(".py"))
    # a git-less export (the offline launcher's tree): every .py on disk under the two roots
    return sorted(str(p.relative_to(ROOT)) for d in ("specs", "tests") for p in (ROOT / d).rglob("*.py")
                  if "__pycache__" not in p.parts)


def bare_imports(src: str) -> list:
    """(top-level module name, line) for every import by NAME: `import X`, `from X import …` (absolute), and
    `__import__("X")` / `import_module("X")` with a literal. A load by file path names no module and is not one."""
    found = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            found += [(a.name.split(".")[0], node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module.split(".")[0], node.lineno))
        elif (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)
              and isinstance(node.args[0].value, str)):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
            if name in ("__import__", "import_module"):
                found.append((node.args[0].value.split(".")[0], node.lineno))
    return found


def check(files: dict) -> list:
    """`files`: {repo-relative path: source}. Returns the refusals."""
    by_stem = collections.defaultdict(list)
    for f in files:
        by_stem[pathlib.PurePosixPath(f).stem].append(f)
    shared = {s: sorted(fs) for s, fs in by_stem.items() if len(fs) > 1 and s != "__init__"}
    evidence = {s for s, fs in shared.items() if any(f.startswith("specs/evidence/") for f in fs)}
    problems, resolved = [], collections.defaultdict(set)
    for f, src in sorted(files.items()):
        p = pathlib.PurePosixPath(f)
        for name, line in bare_imports(src):
            if name in evidence:
                problems.append(f"A {f}:{line}: bare import of `{name}`, a stem two evidence-tree files share "
                                f"({', '.join(shared[name])}) — load it by file under a unique name")
            elif name in shared and p.name.startswith("test_") and f.startswith("tests/"):
                dirs = {str(pathlib.PurePosixPath(x).parent) for x in shared[name]}
                own = str(p.parent)
                if own in dirs:
                    resolved[name].add((own, f))
                    continue
                spelled = {d for d in dirs if f"'{pathlib.PurePosixPath(d).name}'" in src
                           or f'"{pathlib.PurePosixPath(d).name}"' in src}
                if len(spelled) != 1:
                    problems.append(f"B {f}:{line}: bare `{name}` resolves to {sorted(spelled) or 'no'} directory — "
                                    f"one of {sorted(dirs)} must be named, and only one")
                else:
                    resolved[name].add((spelled.pop(), f))
    for name, pairs in sorted(resolved.items()):
        if len({d for d, _f in pairs}) > 1:
            problems.append(f"B `{name}`: collected tests bind it to {sorted({d for d, _ in pairs})} — two files, "
                            f"one bare name ({sorted(f for _, f in pairs)})")
    return problems


def test_no_bare_module_name_is_bound_to_two_files_in_one_process():
    files = {f: (ROOT / f).read_text(encoding="utf-8") for f in _tracked()}
    assert not check(files), "\n".join(check(files))


def test_the_collision_check_refuses_each_planted_break():
    """Controls in both directions (research): a bare import of a shared evidence stem is refused; the same name loaded
    by file passes; a bare import of a UNIQUE stem passes (so the set is derived, not a blanket ban); and rule B
    refuses two collected tests binding one bare name to two directories."""
    ev = {"specs/evidence/a/run_model.py": "", "specs/evidence/b/run_model.py": "", "specs/evidence/a/only_here.py": ""}
    bare = {**ev, "specs/evidence/a/obligations.py": "import run_model\n"}
    by_file = {**ev, "specs/evidence/a/obligations.py":
               "import importlib.util\ns = importlib.util.spec_from_file_location('m0044', 'run_model.py')\n"}
    unique = {**ev, "specs/evidence/a/obligations.py": "import only_here\n"}
    dunder = {**ev, "specs/evidence/a/obligations.py": "x = __import__('run_model')\n"}
    assert any(p.startswith("A specs/evidence/a/obligations.py:1: bare import of `run_model`") for p in check(bare))
    assert any("bare import of `run_model`" in p for p in check(dunder))
    assert check(by_file) == [] and check(unique) == []
    helpers = {"tests/h1/adapter.py": "", "tests/h2/adapter.py": ""}
    one_dir = {**helpers, "tests/test_x.py": "import sys\nsys.path.insert(0, 'h1')\nimport adapter\n",
               "tests/h1/test_y.py": "import adapter\n"}
    two_dirs = {**helpers, "tests/test_x.py": "import sys\nsys.path.insert(0, 'h1')\nimport adapter\n",
                "tests/test_z.py": "import sys\nsys.path.insert(0, 'h2')\nimport adapter\n"}
    unresolved = {**helpers, "tests/test_x.py": "import adapter\n"}
    script = {**helpers, "tests/h2/run.py": "import adapter\n", "tests/test_x.py": "import sys\nsys.path.insert(0, 'h1')\nimport adapter\n"}
    assert check(one_dir) == [] and check(script) == []          # one binding; a standalone script is not judged
    assert any(p.startswith("B `adapter`: collected tests bind it to") for p in check(two_dirs))
    assert any("resolves to no directory" in p for p in check(unresolved))
