#!/usr/bin/env python3
"""0042 Part A-0-quater — THE SITE BINDS THE DECISION: INSTALLED is derived from the code by two
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


def scan(root: pathlib.Path) -> list[dict]:
    """Every `NAME = declare_site("<literal>")` under root, with the BINDING found for NAME in the
    same module's function bodies: {id, module, qualname, line, name, consult, fire, bound}."""
    out = []
    for p in sorted(root.rglob("*.py")):
        tree = ast.parse(p.read_text()); declared = []
        # 1. declarations (any depth, so a declaration hidden in a body is still seen and still needs binding)
        stack = []
        def walk(node):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name); walk(child); stack.pop(); continue
                if isinstance(child, ast.Call) and _call_name(child) == "declare_site" and child.args \
                        and isinstance(child.args[0], ast.Constant) and isinstance(child.args[0].value, str):
                    declared.append({"id": child.args[0].value, "module": str(p.relative_to(root)), "qualname": ".".join(stack) or "<module>",
                                     "line": child.lineno, "name": None})
                walk(child)
        walk(tree)
        # the bound NAME: `NAME = declare_site(...)` (a call not assigned to a name can never be used)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and _call_name(node.value) == "declare_site" \
                    and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                for d in declared:
                    if d["line"] == node.value.lineno and d["name"] is None:
                        d["name"] = node.targets[0].id
        # 2. binding: uses of NAME.consult( / NAME.fire( INSIDE a function body of this module
        uses = {}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for node in ast.walk(fn):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                            and node.func.attr in BINDING_METHODS:
                        uses.setdefault(node.func.value.id, set()).add(node.func.attr)
        for d in declared:
            u = uses.get(d["name"], set()) if d["name"] else set()
            d["consult"], d["fire"] = "consult" in u, "fire" in u
            d["bound"] = d["consult"] and d["fire"]
            out.append(d)
    return out


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
    enforcement = {cid for cid, d in reviewed.items() if d.get("decision") == "enforcement"}
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
    """Run one DECLINING decision at each loaded fixture site and return the counters afterwards."""
    load_fixture(); pkg = importlib.import_module("fixture_sites"); pkg.reset_counters()
    g = importlib.import_module("fixture_sites.gate_like"); i = importlib.import_module("fixture_sites.ingest_like")
    try:
        g.answer([], ["an unverified claim"]); raise AssertionError("the fixture gate did not decline")
    except ValueError:
        pass
    assert i.admit({"author": "third_party"}) is False, "the fixture ingest did not quarantine"
    return pkg.counters()


def assert_counters_moved(counters: dict, executed_ids: set[str]) -> list[str]:
    """After a declining decision at each executed site: consulted ≥ 1 AND fired ≥ 1, or the binding
    does not work whatever the scan says."""
    p = []
    for sid in sorted(executed_ids):
        c = counters.get(sid)
        if c is None: p.append(f"{sid}: executed but has NO counters — never registered"); continue
        if c["consulted"] < 1: p.append(f"{sid}: executed but consulted == {c['consulted']} — the decision is not bracketed by consult()")
        if c["fired"] < 1: p.append(f"{sid}: declined but fired == {c['fired']} — the decision is not expressed through fire()")
    return p


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
    counters = execute_decisions(); moved = assert_counters_moved(counters, {"gate.answer.unverified-only", "ingest.quarantine.third-party"})
    print("RUNTIME — one declining decision per loaded site, counters:", counters)
    print("RUNTIME — counters moved:", "ASSERTED" if not moved else moved)
    print("report after the decisions:", [(r["id"], r["status"]) for r in ct.report_rows(counters, FIX_DECLARED, True)])
    c1 = strip_binding_control(); print("STRIP-THE-BINDING CONTROL (keep declare_site + raise):", "REFUSES (correct): " + c1[0] if c1 else "WRONG: passed")
    c2 = consult_without_fire_control(); print("CONSULT-WITHOUT-FIRE CONTROL:", "REFUSES (correct): " + c2[0] if c2 else "WRONG: passed")
    c3 = delete_declaration_control(); print("DELETE-THE-DECLARATION (structural):", "REFUSES (correct): " + c3[0] if c3 else "WRONG: passed")
    real = scan(SRC); print(f"REAL TREE: declare_site calls in src/veracium: {len(real)} → INSTALLED = {'∅' if not real else len(installed(real))}; a non-empty DECLARED would refuse")
    sys.exit(0 if not ref and not moved and c1 and c2 and c3 else 1)
