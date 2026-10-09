"""specs/evidence carries no dead private helpers (process adjustment 5, approved by the owner 2026-10-09).

0043's round-9 verdict named, as advisory, a superseded helper (`_pre_question_structure`) left beside the live check
after a fix replaced it; CLAUDE.md's found-in-fix item 5 asks every fix to sweep the code it replaced. Measured on
2026-10-09: nine such helpers across the evidence tree, eight of them older than this arc.

A helper is a module-level, undecorated function under specs/evidence whose name starts with one underscore. It is
ALIVE when some TRACKED non-test .py (specs/, src/, anywhere but tests/) refers to it as CODE, outside its own body:
  - an Attribute `mod._x`;
  - a bare Name `_x` in its own module, or in a module that imports `_x` (`from m import _x [as y]` counts as a use);
  - a string constant, not a docstring, equal to `_x` (getattr, a dispatch table) or containing `_x(` (generated code
    executed later — how `_realized_site` is reached).
Not uses: a docstring that mentions it (a superseding fix's "replaces _x(…)" is exactly the dead case), a reference in
its own body (recursion), a same-named local in another module, and any reference from tests/ (a helper only a test
calls belongs in the test).

Exempt BY PROPERTY, each probed, never by name:
  - decorated functions: a decorator registers them (`@check(...)` in the 0022 store-concurrency harness);
  - a module whose own sha256 — full, or its first 16 hex — appears in any OTHER tracked file of any type: it is a
    pinned copy (`0042/reference_census.py` by REFERENCE_CENSUS_SHA256; the 0024 baseline scripts in DIGESTS.sha256;
    `0043/interpreter.py` by the 16-hex prefix in the committed run's ledger and report).
"Tracked" is `git ls-files`; outside a checkout (a packaged, git-less copy) every file under the root except dot-paths
(.venv*, .git, caches), __pycache__, site-packages and node_modules.

Stated limits: an Attribute `._x` and an import `from m import _x` are MODULE-BLIND (neither `m` nor the attribute's
object is resolved), so an unrelated `_x` reached that way keeps an evidence `_x` alive. That errs toward missing a dead
helper, never toward refusing a live one.
Rule and probe sharpened by research's stage-1 read (2026-10-09), each hole now a control cell below.
"""
import ast
import hashlib
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _tracked(root: pathlib.Path) -> list[pathlib.Path]:
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
        if pathlib.Path(top).resolve() == root.resolve():
            out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout
            return [root / p for p in out.decode().split("\0") if p and (root / p).is_file()]
    except (OSError, subprocess.CalledProcessError):
        pass
    # a git-less copy: the copy's OWN files, never what a launcher put beside them — the packaged launcher builds its
    # venv inside the tree (`$ROOT/.venv-offline`), and one attribute in third-party code would keep a dead helper alive.
    # This also skips TRACKED dot-paths (.github, .gitignore) that a checkout's ls-files includes: the two modes agree
    # only while no evidence module's digest is pinned in one (none is, 2026-10-09 — research's check)
    skip = lambda part: part.startswith(".") or part in ("__pycache__", "site-packages", "node_modules")
    return [p for p in root.rglob("*") if p.is_file() and not any(skip(x) for x in p.relative_to(root).parts)]


def _docstrings(tree) -> set:
    ids = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) \
                and isinstance(n.body[0].value.value, str):
            ids.add(id(n.body[0].value))
    return ids


def _uses(tree):
    """Yield (kind, name, top-level def it sits in or None) for every code reference in a module."""
    docs = _docstrings(tree)
    for top in tree.body:
        owner = top.name if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else None
        for n in ast.walk(top):
            if isinstance(n, ast.Attribute):
                yield "attr", n.attr, owner
            elif isinstance(n, ast.Name):
                yield "name", n.id, owner
            elif isinstance(n, ast.ImportFrom):
                for a in n.names:
                    yield "import", a.name, owner
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
                yield "string", n.value, owner


def _pinned(files: list, path: pathlib.Path, texts: dict) -> bool:
    full = hashlib.sha256(path.read_bytes()).hexdigest()
    return any(f != path and (full in t or full[:16] in t) for f, t in texts.items())


def dead_helpers(root: pathlib.Path) -> list[str]:
    files = _tracked(root)
    code = {}
    for p in files:
        if p.suffix == ".py" and "tests" not in p.relative_to(root).parts[:1]:
            try:
                code[p] = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue                       # a deliberately unparseable fixture is not a module of helpers
    uses = {p: list(_uses(t)) for p, t in code.items()}
    evidence = root / "specs" / "evidence"
    texts = None
    dead = []
    for p, t in code.items():
        if evidence not in p.parents:
            continue
        for n in t.body:
            if not (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("_")
                    and not n.name.startswith("__") and not n.decorator_list):
                continue
            x = n.name

            def alive_in(q, us):
                imports_x = any(k == "import" and v == x for k, v, _ in us)
                for k, v, owner in us:
                    if q == p and owner == x:
                        continue                                  # its own body: recursion is not a use
                    if (k == "attr" and v == x) or (k == "import" and v == x):
                        return True
                    if k == "name" and v == x and (q == p or imports_x):
                        return True
                    if k == "string" and (v == x or x + "(" in v):
                        return True
                return False

            if any(alive_in(q, us) for q, us in uses.items()):
                continue
            if texts is None:
                texts = {}
                for f in files:
                    try:
                        texts[f] = f.read_text(encoding="utf-8", errors="ignore").lower()
                    except OSError:
                        continue
            if _pinned(files, p, texts):
                continue
            dead.append(f"{p.relative_to(root)}:{n.lineno} {x}")
    return dead


def test_no_evidence_module_carries_a_dead_private_helper():
    assert dead_helpers(ROOT) == []


def _tree(tmp_path, files: dict) -> pathlib.Path:
    for rel, text in files.items():
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    return tmp_path


SYNTHETIC = {
    "specs/evidence/x/a.py": (
        "import functools\n"
        "def _dead():\n    return 1\n\n"
        "def _called():\n    return 2\n\n"
        "def _by_attr():\n    return 3\n\n"
        "def _by_template():\n    return 4\n\n"
        "def _by_getattr():\n    return 5\n\n"
        "@functools.lru_cache\ndef _decorated():\n    return 6\n\n"
        "def _test_only():\n    return 7\n\n"
        "def _doc_only():\n    return 8\n\n"
        "def _recursive(n):\n    return _recursive(n - 1) if n else 0\n\n"
        "def _shadowed():\n    return 9\n\n"
        "def _aliased():\n    return 10\n\n"
        "def _from_specs():\n    return 11\n\n"
        "def public():\n    \"\"\"replaces _doc_only(...) — a docstring is not a use\"\"\"\n    return _called()\n\n"
        "CODE = 'x = mod._by_template(1)'\n"
        "F = getattr(__import__('sys'), '_by_getattr', None)\n"),
    "specs/evidence/x/b.py": "import a\nY = a._by_attr()\n\ndef _shadowed():\n    return 0\n\nZ = _shadowed()\n",
    "specs/evidence/x/frozen.py": "def _kept_in_a_copy():\n    return 12\n",
    "specs/evidence/x/frozen16.py": "def _kept_by_prefix():\n    return 13\n",
    "specs/render.py": "from evidence.x.a import _aliased as h\nimport evidence.x.a as a\nh(); a._from_specs()\n",
    "tests/test_x.py": "from a import _test_only\n_test_only()\n",
}
EXPECTED_DEAD = {"_dead", "_test_only", "_doc_only", "_recursive", "_shadowed"}


def _pin(root):
    full = hashlib.sha256((root / "specs/evidence/x/frozen.py").read_bytes()).hexdigest()
    sha16 = hashlib.sha256((root / "specs/evidence/x/frozen16.py").read_bytes()).hexdigest()[:16]
    (root / "specs" / "PINS.json").write_text('{"frozen": "%s"}' % full.upper())          # case-insensitive
    (root / "specs" / "BASE.sha256").write_text(f"{sha16}  frozen16.py\n")               # any suffix; a 16-hex prefix


def test_controls_each_refusal_and_each_exemption_fires(tmp_path):
    root = _tree(tmp_path, SYNTHETIC)
    _pin(root)
    assert {d.split()[-1] for d in dead_helpers(root)} == EXPECTED_DEAD
    (root / "specs" / "PINS.json").write_text("{}")
    (root / "specs" / "BASE.sha256").write_text("")                                       # the pins removed
    assert {d.split()[-1] for d in dead_helpers(root)} == EXPECTED_DEAD | {"_kept_in_a_copy", "_kept_by_prefix"}


def test_control_a_git_less_copy_ignores_what_a_launcher_put_inside_it(tmp_path):
    """Research's stage-1 (2026-10-09): the reviewer's tree/ has no .git and run_offline.sh builds its venv at
    `$ROOT/.venv-offline`; one `obj._dead` in a site-packages module must not keep `_dead` alive."""
    root = _tree(tmp_path, SYNTHETIC)
    _pin(root)
    for venv in (".venv-offline/lib/python3.14/site-packages/x.py", "build/lib/site-packages/y.py"):
        f = root / venv
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("def g(obj):\n    return obj._dead\n")
    assert {d.split()[-1] for d in dead_helpers(root)} == EXPECTED_DEAD


def test_control_in_a_checkout_only_tracked_files_count(tmp_path):
    """An untracked scratch module counts neither as a holder of dead helpers nor as a caller, so a local tree and a
    clean CI checkout give one answer."""
    root = _tree(tmp_path, SYNTHETIC)
    _pin(root)
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, check=True)
    run("init", "-q"); run("add", "-A")
    (root / "specs/evidence/x/scratch.py").write_text("def _untracked_dead():\n    return 0\n")
    (root / "specs/evidence/x/scratch_caller.py").write_text("import a\na._dead()\n")
    assert {d.split()[-1] for d in dead_helpers(root)} == EXPECTED_DEAD
