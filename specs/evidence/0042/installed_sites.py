#!/usr/bin/env python3
"""0042 Part A-0-quater — THE SITE BINDS THE DECISION (round 5: the binding is FUNCTION-LOCAL and scope-aware; the runtime assertion is over DELTAS): INSTALLED is derived from the code by two
derivations that check each other, and the second is the reviewer's own round-4 test made an assertion.

  SCAN      a static AST pass: for every `NAME = declare_site("<id>")` at module level, the function
            bodies of the SAME module that use `NAME.consult(` AND `NAME.fire(`. An id is BOUND when
            some body carries both. (Round 4: a `declare_site` CALL is a proxy for a counter bound to
            the decision — the scan was honest about what it scanned; what it scanned was the wrong
            thing. Consult-without-fire is the next mutant: traffic moves `consulted`, the decline never
            moves `fired`, and a site that fired reads UNEXERCISED — so the binding is BOTH.)
  REGISTRY  the import-time record: each declare_site(id) registers when its module loads.
  INSTALLED = the ids the SCAN shows BOUND. A declared id whose module registered it but whose bodies
            never bind it is "registered, not installed" → REFUSE — precisely what round 4 found and
            A-0-ter called installed. A loaded module whose scanned site did not register → REFUSE;
            a module that did not load has its sites NAMED as out of reach; registered-but-unscanned → REFUSE.
  RUNTIME   execute a decision and ASSERT the id's counters MOVED (consulted ≥ 1 and, for a decline,
            fired ≥ 1). The scan says the binding exists; the execution says it works. Round 4 is what
            happens when only the first is checked.

Reconciliation over FOUR sets (A-0-ter): every DISCOVERED candidate has a DECISION; REVIEWED-as-
enforcement == DECLARED; DECLARED == INSTALLED; reporting ⊆ DECLARED.

Controls (A-0-quater's table, the naming defect fixed — v6's "delete a counter" deleted the
`declare_site` LINE on a fixture with no counters, so its name promised missing instrumentation and
its body tested missing registration):
  strip the `.consult`/`.fire` wrappers, KEEP the `declare_site` line and the raise → REFUSE
  full binding, no traffic                                                            → UNREACHED
  execute a decision                                                                   → counters move, asserted
  (kept as a structural case: delete the `declare_site` line, keep the body → REFUSE, the id is unscanned)

On the real tree today the scan finds NO `declare_site` calls in src/veracium (a draft spec authorises
no implementation), so INSTALLED = ∅ and a non-empty DECLARED would refuse — the honest state.

    python3 specs/evidence/0042/installed_sites.py     # scans the fixture package and src/, runs every control
"""
from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / "src" / "veracium"
FIXTURE = HERE / "fixture_sites"
BINDING_METHODS = ("consult", "fire")


def _call_name(node: ast.Call):
    f = node.func
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)


# ONE resolver, two instruments — loaded BY PATH, never `from scope_resolution import …`: a sibling import by
# package path is green wherever the directory happens to be on sys.path and red where it is not (the tests/ class,
# 2026-09-08). `HERE` is this file's own directory, so the load works from any cwd and inside a git-less archive.
def _sibling(name):
    import importlib.util as _u
    s = _u.spec_from_file_location(f"_0042_{name}", pathlib.Path(__file__).resolve().parent / f"{name}.py")
    m = _u.module_from_spec(s); s.loader.exec_module(m); return m


_scope = _sibling("scope_resolution")
Resolver, UnresolvableScope = _scope.Resolver, _scope.UnresolvableScope


def _binding_bodies(src: str, filename: str = "<scan>") -> dict:
    """{NAME: the (consult|fire) methods used on the MODULE-LEVEL site NAME inside ONE function body, unioned over
    bodies carrying BOTH}. Round 5 made the scan per-body; round 6 made it resolve through enclosing scopes; ROUND 7
    (F2) stops enumerating the forms that bind a name at all. The previous version hand-listed assignments, loop
    targets, imports, with-as, except-as and parameters, and the reviewer found the two rungs it had not reached —
    an assignment expression (`S := …`) and a `match` capture — each reading `bound=True` while the declared site's
    counters never moved. The set of forms that bind a name is defined by the LANGUAGE, so the question now goes to
    CPython's own scope analysis (`scope_resolution.Resolver`, symtable): a use counts only where the name resolves
    to the MODULE binding, which is false for a local, a parameter, or a name bound by an enclosing function."""
    r = Resolver(src, filename)
    sites = r.site_names()
    r.refuse_site_rebindings(sites)
    per_body: dict = {}
    for fn in ast.walk(r.tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        uses: dict = {}

        def visit(n_):
            for c in ast.iter_child_nodes(n_):
                if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    continue                                   # a nested scope is NOT this body
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) \
                        and c.func.attr in BINDING_METHODS and c.func.value.id in sites \
                        and r.refers_to_declared_site(c, c.func.value.id):
                    uses.setdefault(c.func.value.id, set()).add(c.func.attr)
                visit(c)
        visit(fn)
        for name, methods in uses.items():
            if set(BINDING_METHODS) <= methods:
                per_body.setdefault(name, set()).update(methods)
    return per_body


def scan(root: pathlib.Path) -> list[dict]:
    """Every `NAME = declare_site("<literal>")` under root, with the BINDING found for NAME inside ONE
    function body of the same module: {id, module, qualname, line, name, consult, fire, bound, sha256} — `sha256` is the
    digest of the bytes read (round 13: `scan_is_the_program_that_ran` binds them to the running code).
    `consult`/`fire` report whether ANY body uses the method (diagnostic); `bound` is true only when
    ONE body carries both on the unshadowed module-level name."""
    out = []
    for p in sorted(root.rglob("*.py")):
        raw = p.read_bytes(); src = raw.decode(); tree = ast.parse(src); declared = []
        digest = hashlib.sha256(raw).hexdigest()
        stack = []
        def walk(node):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name); walk(child); stack.pop(); continue
                if isinstance(child, ast.Call) and _call_name(child) == "declare_site" and child.args \
                        and isinstance(child.args[0], ast.Constant) and isinstance(child.args[0].value, str):
                    declared.append({"id": child.args[0].value, "module": str(p.relative_to(root)), "qualname": ".".join(stack) or "<module>",
                                     "line": child.lineno, "name": None, "sha256": digest})
                walk(child)
        walk(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and _call_name(node.value) == "declare_site" \
                    and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                for d in declared:
                    if d["line"] == node.value.lineno and d["name"] is None:
                        d["name"] = node.targets[0].id
        # diagnostic: any use anywhere in a function body (module-wide, the round-4 reading)
        anywhere = {}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for node in ast.walk(fn):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                            and node.func.attr in BINDING_METHODS:
                        anywhere.setdefault(node.func.value.id, set()).add(node.func.attr)
        bound_names = _binding_bodies(src, str(p))      # symtable reads SOURCE: the same text the runtime executes
        for d in declared:
            u = anywhere.get(d["name"], set()) if d["name"] else set()
            d["consult"], d["fire"] = "consult" in u, "fire" in u
            d["bound"] = bool(d["name"]) and d["name"] in bound_names      # ONE body, both methods, unshadowed
            out.append(d)
    return out


def _code_objects(code, out=None) -> dict:
    """Every code object a compiled module holds, keyed (name, first line) — the function bodies as compiled."""
    out = {} if out is None else out
    for c in code.co_consts:
        if hasattr(c, "co_code"):
            out[(c.co_name, c.co_firstlineno)] = c
            _code_objects(c, out)
    return out


def _running_code(mod) -> dict:
    """The code objects of the functions a RUNNING module defines at top level and in its classes, unwrapped."""
    import inspect
    out = {}
    def add(obj):
        obj = inspect.unwrap(obj) if callable(obj) else obj
        code = getattr(obj, "__code__", None)
        # compiled FROM THIS FILE: a dataclass's or namedtuple's generated `__init__`/`__repr__`/`__eq__` belong to the
        # running module and are compiled by `exec` from text that is not in the source (measured: 48 of them on
        # 3.12, 88 on 3.13, every one refused before this filter) — they are not what the scan read.
        if code is not None and getattr(obj, "__module__", None) == mod.__name__ \
                and pathlib.Path(code.co_filename).resolve() == pathlib.Path(mod.__file__).resolve():
            out[(code.co_name, code.co_firstlineno)] = code
    for obj in list(vars(mod).values()):
        if isinstance(obj, type) and obj.__module__ == mod.__name__:
            for member in list(vars(obj).values()):      # a snapshot: a class dict can change under iteration
                for fn in (member, getattr(member, "__func__", None), getattr(member, "fget", None)):
                    if fn is not None:
                        add(fn)
        elif callable(obj):
            add(obj)
    return out


def _defined_functions(tree: ast.Module) -> int:
    """How many functions a module ENDS UP holding where `_running_code` looks — top level, and directly in top-level
    classes — counted as DISTINCT NAMES per scope, because a later `def` of the same name replaces the earlier one
    (measured: store/schema_version.py defines three functions twice, store/sqlite.py one method twice; a property's
    getter and setter share one name and one `fget`). Counting statements refused both modules."""
    n = len({s.name for s in tree.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))})
    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            n += len({x.name for x in stmt.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))})
    return n


def scan_is_the_program_that_ran(root: pathlib.Path, scanned: list[dict], registry: dict) -> list[str]:
    """ROUND 13 — THE SCAN'S TWO INPUTS ARE THE PROGRAM THAT RAN (the ledger's row 321, research's stage-2 finding of
    2026-09-21, taken into round 13 on the owner's word as a SILENT limit the round-12 package never disclosed).
    `scan()` reads each module from disk and its `bound` is a JOIN between two things: the MODULE-LEVEL table
    `NAME = declare_site(id)` and the FUNCTION BODIES that consult and fire NAME. The reconciliation compared module
    names and site ids, never content, so an edit the process never saw could flip `bound` with nothing to refuse.

    Per scanned module the process has loaded — found by its MODULE NAME, so a module that ran from another copy is
    refused rather than skipped as "not loaded" (research's stage-1 attack on round 13's first form):
      0. the module RAN FROM the scanned file (`__file__` resolves to it);
      1. the file's bytes NOW equal the bytes the scan read (their sha256);
      2. THE TABLE, BY IDENTITY: for every scanned `NAME = declare_site(id)`, the running module's NAME IS the object
         the census registry holds for id, and every id the registry holds for that module is scanned. Research's
         case: `S = declare_site('a'); T = object()` ran, `S = object(); T = declare_site('a')` was scanned — every
         function's code object equal, the scan saying bound where the site was not;
      3. THE BODIES: every function the running module defines at top level and in its classes has a code object
         EQUAL to the one compiled from the scanned bytes, and the number compared equals the number of definitions
         in the scanned source — so a module whose functions were all filtered out cannot pass by comparing none.
    NOT `__loader__.get_source`, the first proposed remedy: it re-reads the file at call time and shows the edit
    (measured by both seats). SCOPE, named: the scan's two inputs, not the whole program — a default value or a
    decorator argument evaluated at module level is not what `bound` reads. Returns refusals; [] is the claim."""
    import sys as _sys
    root = pathlib.Path(root).resolve(); pkg = root.name
    by_module: dict[str, list] = {}
    for s in scanned:
        by_module.setdefault(s["module"], []).append(s)
    problems = []
    for rel, rows in sorted(by_module.items()):
        parts = pathlib.PurePosixPath(rel).with_suffix("").parts
        name = ".".join([pkg, *(parts[:-1] if parts[-1] == "__init__" else parts)])
        mod = _sys.modules.get(name)
        if mod is None:
            continue                                     # out of reach: named by the reconciliation, never silent
        path = root / rel
        ran_from = pathlib.Path(getattr(mod, "__file__", "") or "").resolve()
        if ran_from != path.resolve():
            problems.append(f"{rel}: the running module {name} was loaded from {ran_from}, not the scanned file")
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != rows[0]["sha256"]:
            problems.append(f"{rel}: the file changed after the scan read it — the scan does not describe these bytes")
            continue
        for r in rows:
            if r["name"] is None:
                problems.append(f"{rel}:{r['line']}: site {r['id']!r} is declared without a module-level name, so its "
                                f"identity with the registered site cannot be established")
            elif getattr(mod, r["name"], None) is not registry.get(r["id"]):
                problems.append(f"{rel}:{r['line']}: the running module's {r['name']} is NOT the site the registry holds "
                                f"for {r['id']!r} — the scan's declaration table describes a different program")
        scanned_ids = {r["id"] for r in rows}
        for rid, site in registry.items():
            if rid not in scanned_ids and any(site is getattr(mod, n, None) for n in list(vars(mod))):
                problems.append(f"{rel}: the running module holds the registered site {rid!r}, which the scan does not show")
        tree = ast.parse(raw.decode())
        compiled = _code_objects(compile(raw.decode(), str(path), "exec", dont_inherit=True))
        ran = _running_code(mod)
        if len(ran) != _defined_functions(tree):
            problems.append(f"{rel}: {len(ran)} running functions compared against {_defined_functions(tree)} defined in the "
                            f"scanned source — the comparison does not cover the module")
        for key, code in sorted(ran.items(), key=lambda kv: kv[0][1]):
            if compiled.get(key) != code:
                problems.append(f"{rel}: {key[0]} (line {key[1]}) as it RAN differs from the source the scan read — the "
                                f"scan's `bound` describes a different program")
    return problems


def installed(scanned: list[dict]) -> set[str]:
    """INSTALLED = the BOUND ids. A declaration without its binding is not installed."""
    return {s["id"] for s in scanned if s["bound"]}


def load_fixture(modules=("gate_like", "ingest_like")) -> tuple[dict, set[str]]:
    """Import the named fixture modules (NOT unloaded_like) and return the registry + loaded module files."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    pkg = importlib.import_module("fixture_sites"); pkg._REGISTRY.clear()
    for m in modules:
        importlib.reload(importlib.import_module(f"fixture_sites.{m}"))
    return pkg.registry(), {f"{m}.py" for m in modules} | {"__init__.py"}


def check_registry_against_scan(scanned: list[dict], registry: dict, loaded_modules: set[str]) -> tuple[list[str], list[str]]:
    """-> (refusals, out_of_reach). The registry checks the scan; it is not a second opinion — and a
    registration whose scan shows NO binding is refused as 'registered, not installed'."""
    refusals, out_of_reach = [], []
    for s in scanned:
        if s["module"] in loaded_modules:
            if s["id"] not in registry:
                refusals.append(f"scanned site {s['id']!r} in a LOADED module ({s['module']}:{s['line']}) did not register — dead branch, guarded import, or the scan misread")
            elif not s["bound"]:
                missing = [m for m in BINDING_METHODS if not s[m]]
                refusals.append(f"registered, not installed: {s['id']!r} ({s['module']}:{s['line']}) is declared and registered but no function body binds it — missing {missing}")
        else:
            out_of_reach.append(f"site {s['id']!r} in {s['module']} — module not loaded in this process; NAMED, never silently absent"
                                + ("" if s["bound"] else f" (and UNBOUND in the source: missing {[m for m in BINDING_METHODS if not s[m]]})"))
    scanned_ids = {s["id"] for s in scanned}
    for rid in sorted(set(registry) - scanned_ids):
        refusals.append(f"registered site {rid!r} is not in the scan — something registered that the source does not show")
    return refusals, out_of_reach


def reconcile(discovered_ids: set[str], reviewed: dict, declared: set[str], installed_ids: set[str], reporting: set[str]) -> list[str]:
    p = []
    for cid in sorted(discovered_ids):
        if cid not in reviewed:
            p.append(f"DISCOVERED candidate with NO DECISION: {cid}")
    # a reviewed row names its SITE id (the generated review file, tranche 6); the fixture's rows
    # carry none and their candidate id IS their site id
    enforcement = {d.get("site", cid) for cid, d in reviewed.items() if d.get("decision") == "enforcement"}
    for x in sorted(enforcement - declared): p.append(f"REVIEWED-as-enforcement but NOT DECLARED: {x}")
    for x in sorted(declared - enforcement): p.append(f"DECLARED but not REVIEWED-as-enforcement: {x}")
    for x in sorted(declared - installed_ids): p.append(f"DECLARED but NOT INSTALLED (the scan shows no binding for it): {x}")
    for x in sorted(installed_ids - declared): p.append(f"INSTALLED but not DECLARED: {x}")
    for x in sorted(reporting - declared): p.append(f"reporting but not DECLARED (UNDECLARED): {x}")
    return p


# the fixture's authored sets (the three sites; the unloaded one is declared and reviewed too — it is
# INSTALLED by the scan, merely out of reach at runtime)
FIX_DISCOVERED = {"gate.answer.unverified-only", "ingest.quarantine.third-party", "lifecycle.forget.scope"}
FIX_REVIEWED = {k: {"decision": "enforcement", "reason": "fixture", "reviewer": "dev"} for k in FIX_DISCOVERED}
FIX_DECLARED = set(FIX_DISCOVERED)


# ---- the RUNTIME derivation: the reviewer's round-4 test, as an assertion -----------------------

def execute_decisions() -> dict:
    """Run one DECLINING decision at each loaded fixture site and return {site: (before, after)} —
    round 5: the assertion is over the DELTA around the particular decision; an already-positive
    counter must not establish that a later decision was measured."""
    load_fixture(); pkg = importlib.import_module("fixture_sites"); pkg.reset_counters()
    g = importlib.import_module("fixture_sites.gate_like"); i = importlib.import_module("fixture_sites.ingest_like")
    snaps = {}
    before = pkg.counters().get("gate.answer.unverified-only")
    try:
        g.answer([], ["an unverified claim"]); raise AssertionError("the fixture gate did not decline")
    except ValueError:
        pass
    snaps["gate.answer.unverified-only"] = (before, pkg.counters().get("gate.answer.unverified-only"))
    before = pkg.counters().get("ingest.quarantine.third-party")
    assert i.admit({"author": "third_party"}) is False, "the fixture ingest did not quarantine"
    snaps["ingest.quarantine.third-party"] = (before, pkg.counters().get("ingest.quarantine.third-party"))
    return snaps


def assert_counters_moved(snapshots: dict, executed_ids: set[str]) -> list[str]:
    """After ONE declining decision at each executed site: Δconsulted == 1 AND Δfired == 1 BETWEEN the
    snapshot before that decision and the one after it (v8.1: exactly one, so a double-count refuses
    too). A LEVEL (consulted >= 1) is the proxy the reviewer refused: an already-positive counter
    proves nothing about this decision."""
    p = []
    for sid in sorted(executed_ids):
        snap = snapshots.get(sid)
        if snap is None or snap[1] is None: p.append(f"{sid}: executed but has NO counters — never registered"); continue
        before, after = snap
        b = before or {"consulted": 0, "fired": 0, "errors": 0}
        dc, df = after["consulted"] - b["consulted"], after["fired"] - b["fired"]
        if dc != 1: p.append(f"{sid}: executed once but consulted moved by {dc} — " + ("the decision is not bracketed by consult()" if dc < 1 else "double-counted"))
        if df != 1: p.append(f"{sid}: declined once but fired moved by {df} — " + ("the decision is not expressed through fire()" if df < 1 else "double-counted"))
    return p


def level_assertion(snapshots: dict, executed_ids: set[str]) -> list[str]:
    """THE SUPERSEDED v8 RUNTIME LEG, kept as the mutant: a LEVEL check (consulted >= 1 and fired >= 1
    after the decision). It passes on pre-loaded counters that never moved."""
    p = []
    for sid in sorted(executed_ids):
        after = (snapshots.get(sid) or (None, None))[1]
        if after is None or after["consulted"] < 1 or after["fired"] < 1:
            p.append(f"{sid}: counters not positive")
    return p


def preloaded_positive_control() -> dict:
    """v8.1's second control: counters PRE-LOADED positive, then a decision that never reaches the site
    (the declaration kept, the raise unwrapped). The delta assertion REFUSES; the level assertion PASSES —
    which is why the level assertion is the mutant, not the check."""
    load_fixture(); pkg = importlib.import_module("fixture_sites"); pkg.reset_counters()
    site = pkg._REGISTRY["gate.answer.unverified-only"]; site.consulted = site.fired = 5
    before = pkg.counters()["gate.answer.unverified-only"]
    def answer_unwrapped(grounded, unverified):          # the mutant decision: declares nothing, touches no counter
        if not grounded and unverified:
            raise ValueError("refuse: unverified-only support")
        return "answer"
    try:
        answer_unwrapped([], ["claim"]); raise AssertionError("the mutant did not decline")
    except ValueError:
        pass
    snaps = {"gate.answer.unverified-only": (before, pkg.counters()["gate.answer.unverified-only"])}
    return {"delta_refuses": bool(assert_counters_moved(snaps, {"gate.answer.unverified-only"})),
            "level_passes": not level_assertion(snaps, {"gate.answer.unverified-only"}), "snapshots": snaps}


def counters_after(snapshots: dict) -> dict:
    """The live counters after the decisions, in report_rows' shape."""
    return {sid: after for sid, (_, after) in snapshots.items() if after is not None}


# ---- controls ------------------------------------------------------------------------------------

def _mutated_copy(edit) -> set[str]:
    with tempfile.TemporaryDirectory() as d:
        copy = pathlib.Path(d) / "fixture_sites"; shutil.copytree(FIXTURE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        edit(copy)
        return installed(scan(copy))


def strip_binding_control() -> list[str]:
    """A-0-quater's first control: strip the `.consult`/`.fire` wrappers from gate_like, KEEP the
    `declare_site` line and the raise → the scan shows registration without binding → REFUSE."""
    def edit(copy):
        g = copy / "gate_like.py"; src = g.read_text()
        new = src.replace("    with SITE_ANSWER.consult():\n        if not grounded and unverified:\n            raise SITE_ANSWER.fire(ValueError(\"refuse: unverified-only support\"))\n",
                          "    if not grounded and unverified:\n        raise ValueError(\"refuse: unverified-only support\")\n")
        assert new != src and 'declare_site("gate.answer.unverified-only")' in new, "the control's edit did not apply"
        g.write_text(new)
    return reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, _mutated_copy(edit), set())


def consult_without_fire_control() -> list[str]:
    """The next mutant: keep consult(), express the raise WITHOUT fire() → not bound → REFUSE."""
    def edit(copy):
        g = copy / "gate_like.py"; src = g.read_text()
        new = src.replace("raise SITE_ANSWER.fire(ValueError(\"refuse: unverified-only support\"))", "raise ValueError(\"refuse: unverified-only support\")")
        assert new != src; g.write_text(new)
    return reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, _mutated_copy(edit), set())


def split_function_control() -> list[str]:
    """Round 5's reproduction: consult() in ONE function and fire() in ANOTHER — a module-wide scan by
    variable name read it as bound. Same-function-body → not bound → REFUSE."""
    def edit(copy):
        g = copy / "gate_like.py"
        g.write_text('from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
                     'def consult_only(grounded, unverified):\n    with SITE_ANSWER.consult():\n        pass\n    return "answer"\n\n\n'
                     'def answer(grounded, unverified):\n    if not grounded and unverified:\n        raise SITE_ANSWER.fire(ValueError("refuse: unverified-only support"))\n    return "answer"\n')
    return reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, _mutated_copy(edit), set())


def nested_and_shadowed_control() -> list[str]:
    """Two more scope mutants: (a) consult() in the body and fire() only inside a NESTED function;
    (b) both methods on a LOCAL name that shadows the module-level site. Both → not bound → REFUSE."""
    def nested(copy):
        g = copy / "gate_like.py"
        g.write_text('from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
                     'def answer(grounded, unverified):\n    with SITE_ANSWER.consult():\n        def inner():\n            raise SITE_ANSWER.fire(ValueError("refuse"))\n        if not grounded and unverified:\n            inner()\n    return "answer"\n')
    def shadowed(copy):
        g = copy / "gate_like.py"
        g.write_text('from . import declare_site\n\nSITE_ANSWER = declare_site("gate.answer.unverified-only")\n\n\n'
                     'def answer(grounded, unverified, SITE_ANSWER=None):\n    with SITE_ANSWER.consult():\n        if not grounded and unverified:\n            raise SITE_ANSWER.fire(ValueError("refuse"))\n    return "answer"\n')
    return reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, _mutated_copy(nested), set()) + \
           reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, _mutated_copy(shadowed), set())


def delete_declaration_control() -> list[str]:
    """v6's control under its honest name: delete the `declare_site` line, keep the body → the id is
    unscanned → REFUSE. (Structural; it is not the instrumentation control.)"""
    def edit(copy):
        g = copy / "gate_like.py"; src = g.read_text()
        new = src.replace('SITE_ANSWER = declare_site("gate.answer.unverified-only")\n', "SITE_ANSWER = None\n"); assert new != src; g.write_text(new)
    return reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, _mutated_copy(edit), set())


if __name__ == "__main__":
    fx = scan(FIXTURE); reg, loaded = load_fixture()
    print("fixture scan:", [(s["id"], s["module"], s["line"], "BOUND" if s["bound"] else "UNBOUND") for s in fx])
    ref, oor = check_registry_against_scan(fx, reg, loaded)
    print("registry vs scan — refusals:", ref or "none", "| out of reach:", oor)
    inst = installed(fx)
    print("four-set reconciliation (fixture, no traffic):", reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, inst, set()) or "PASS")
    ct_spec = importlib.util.spec_from_file_location("census_table", HERE / "census_table.py"); ct = importlib.util.module_from_spec(ct_spec); ct_spec.loader.exec_module(ct)
    print("report, no traffic:", [(r["id"], r["status"]) for r in ct.report_rows({}, FIX_DECLARED, True)])
    snaps = execute_decisions(); moved = assert_counters_moved(snaps, {"gate.answer.unverified-only", "ingest.quarantine.third-party"})
    print("RUNTIME — one declining decision per loaded site, (before, after):", snaps)
    print("RUNTIME — counters moved BY DELTA around each decision:", "ASSERTED" if not moved else moved)
    print("report after the decisions:", [(r["id"], r["status"]) for r in ct.report_rows(counters_after(snaps), FIX_DECLARED, True)])
    c1 = strip_binding_control(); print("STRIP-THE-BINDING CONTROL (keep declare_site + raise):", "REFUSES (correct): " + c1[0] if c1 else "WRONG: passed")
    c2 = consult_without_fire_control(); print("CONSULT-WITHOUT-FIRE CONTROL:", "REFUSES (correct): " + c2[0] if c2 else "WRONG: passed")
    c4 = split_function_control(); print("SPLIT-FUNCTION CONTROL (round 5):", "REFUSES (correct): " + c4[0] if c4 else "WRONG: passed")
    c5 = nested_and_shadowed_control(); print("NESTED / SHADOWED CONTROLS:", f"REFUSE (correct): {len(c5)} refusal(s)" if len(c5) == 2 else f"WRONG: {c5}")
    c3 = delete_declaration_control(); print("DELETE-THE-DECLARATION (structural):", "REFUSES (correct): " + c3[0] if c3 else "WRONG: passed")
    pp = preloaded_positive_control(); print("PRE-LOADED-POSITIVE CONTROL (v8.1):", "delta REFUSES, level PASSES (the level check is the mutant)" if pp["delta_refuses"] and pp["level_passes"] else f"WRONG: {pp}")
    real = scan(SRC); print(f"REAL TREE: declare_site calls in src/veracium: {len(real)} → INSTALLED = {'∅' if not real else len(installed(real))}; a non-empty DECLARED would refuse")
    sys.exit(0 if not ref and not moved and c1 and c2 and c4 and len(c5) == 2 and c3 and pp["delta_refuses"] and pp["level_passes"] else 1)
