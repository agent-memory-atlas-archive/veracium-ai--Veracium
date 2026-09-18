#!/usr/bin/env python3
"""0042 Part A-0-ter — INSTALLED IS DERIVED FROM THE CODE, by two derivations that check each other.

  SCAN      a static AST pass for `declare_site("<id>")` calls → (id, module, qualname, line). Nobody
            authored it: the source either carries the instrumentation or it does not.
  REGISTRY  the import-time record: each declare_site(id) registers when its module loads.
  INSTALLED = the SCAN. The REGISTRY is the CHECK ON the scan: a loaded module whose scanned site did
            not register REFUSES; a module that did not load has its sites NAMED as out of reach;
            anything registered but unscanned REFUSES.

Reconciliation over FOUR sets (A-0-ter): every DISCOVERED candidate has a DECISION; REVIEWED-as-
enforcement == DECLARED; DECLARED == INSTALLED; reporting ⊆ DECLARED. The standing control is the
reviewer's demonstration: delete a counter keeping its decision and declaration → the scan loses it →
REFUSE; keep it and send no traffic → UNREACHED.

On the real tree today the scan finds NO `declare_site` calls in src/veracium (a draft spec authorises
no implementation), so INSTALLED = ∅ and a non-empty DECLARED would refuse — which is the honest state.

    python3 specs/evidence/0042/installed_sites.py     # scans the fixture package and src/, runs the control
"""
from __future__ import annotations

import ast
import importlib
import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / "src" / "veracium"
FIXTURE = HERE / "fixture_sites"


def scan(root: pathlib.Path) -> list[dict]:
    """Every `declare_site("<literal>")` call under root, with (id, module, qualname, line)."""
    out = []
    for p in sorted(root.rglob("*.py")):
        tree = ast.parse(p.read_text()); stack = []
        def walk(node):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name); walk(child); stack.pop(); continue
                if isinstance(child, ast.Call):
                    f = child.func
                    name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                    if name == "declare_site" and child.args and isinstance(child.args[0], ast.Constant) and isinstance(child.args[0].value, str):
                        out.append({"id": child.args[0].value, "module": str(p.relative_to(root)), "qualname": ".".join(stack) or "<module>", "line": child.lineno})
                walk(child)
        walk(tree)
    return out


def load_fixture(modules=("gate_like", "ingest_like")) -> tuple[dict, set[str]]:
    """Import the named fixture modules (NOT unloaded_like) and return the registry + loaded module files."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    pkg = importlib.import_module("fixture_sites"); pkg._REGISTRY.clear()
    for m in modules:
        importlib.reload(importlib.import_module(f"fixture_sites.{m}"))
    return pkg.registry(), {f"{m}.py" for m in modules} | {"__init__.py"}


def check_registry_against_scan(scanned: list[dict], registry: dict, loaded_modules: set[str]) -> tuple[list[str], list[str]]:
    """-> (refusals, out_of_reach). The registry checks the scan; it is not a second opinion."""
    refusals, out_of_reach = [], []
    for s in scanned:
        if s["module"] in loaded_modules:
            if s["id"] not in registry:
                refusals.append(f"scanned site {s['id']!r} in a LOADED module ({s['module']}:{s['line']}) did not register — dead branch, guarded import, or the scan misread")
        else:
            out_of_reach.append(f"site {s['id']!r} in {s['module']} — module not loaded in this process; NAMED, never silently absent")
    scanned_ids = {s["id"] for s in scanned}
    for rid in sorted(set(registry) - scanned_ids):
        refusals.append(f"registered site {rid!r} is not in the scan — something registered that the source does not show")
    return refusals, out_of_reach


def reconcile(discovered_ids: set[str], reviewed: dict, declared: set[str], installed: set[str], reporting: set[str]) -> list[str]:
    p = []
    for cid in sorted(discovered_ids):
        if cid not in reviewed:
            p.append(f"DISCOVERED candidate with NO DECISION: {cid}")
    enforcement = {cid for cid, d in reviewed.items() if d.get("decision") == "enforcement"}
    for x in sorted(enforcement - declared): p.append(f"REVIEWED-as-enforcement but NOT DECLARED: {x}")
    for x in sorted(declared - enforcement): p.append(f"DECLARED but not REVIEWED-as-enforcement: {x}")
    for x in sorted(declared - installed): p.append(f"DECLARED but NOT INSTALLED (the scan does not carry it): {x}")
    for x in sorted(installed - declared): p.append(f"INSTALLED but not DECLARED: {x}")
    for x in sorted(reporting - declared): p.append(f"reporting but not DECLARED (UNDECLARED): {x}")
    return p


# the fixture's authored sets (the three sites; the unloaded one is declared and reviewed too — it is
# INSTALLED by the scan, merely out of reach at runtime)
FIX_DISCOVERED = {"gate.answer.unverified-only", "ingest.quarantine.third-party", "lifecycle.forget.scope"}
FIX_REVIEWED = {k: {"decision": "enforcement", "reason": "fixture", "reviewer": "dev"} for k in FIX_DISCOVERED}
FIX_DECLARED = set(FIX_DISCOVERED)


def delete_counter_control() -> list[str]:
    """The reviewer's demonstration: remove ONE declare_site call from a copy of the source, keep its
    decision and declaration → the scan loses it → INSTALLED != DECLARED → REFUSE."""
    with tempfile.TemporaryDirectory() as d:
        copy = pathlib.Path(d) / "fixture_sites"; shutil.copytree(FIXTURE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        g = copy / "gate_like.py"; g.write_text(g.read_text().replace('SITE_ANSWER = declare_site("gate.answer.unverified-only")\n', ""))
        installed = {s["id"] for s in scan(copy)}
    return reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, installed, set())


if __name__ == "__main__":
    fx = scan(FIXTURE); reg, loaded = load_fixture()
    print("fixture scan:", [(s["id"], s["module"], s["line"]) for s in fx])
    ref, oor = check_registry_against_scan(fx, reg, loaded)
    print("registry vs scan — refusals:", ref or "none", "| out of reach:", oor)
    print("four-set reconciliation (fixture, no traffic):", reconcile(FIX_DISCOVERED, FIX_REVIEWED, FIX_DECLARED, {s["id"] for s in fx}, set()) or "PASS")
    ctl = delete_counter_control(); print("DELETE-A-COUNTER CONTROL:", "REFUSES (correct): " + ctl[0] if ctl else "WRONG: passed")
    real = scan(SRC); print(f"REAL TREE: declare_site calls in src/veracium: {len(real)} → INSTALLED = {'∅' if not real else len(real)}; a non-empty DECLARED would refuse")
    sys.exit(0 if not ref and ctl else 1)
