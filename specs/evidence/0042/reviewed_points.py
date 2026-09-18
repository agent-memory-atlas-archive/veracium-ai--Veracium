#!/usr/bin/env python3
"""0042 Part A-0-bis — THE THREE SETS and their refusals.

  DISCOVERED  the AST inventory (decision_site_inventory.py) — nobody chose its members
  REVIEWED    one inclusion-or-exclusion DECISION per discovered candidate — AUTHORED:
              {candidate_id: {"decision": "enforcement" | "not", "reason": str, "reviewer": str}}
  INSTALLED   the declaration (authored) + the ids that report at runtime (observed)

The inventory never forces a DECLARATION; it forces a DECISION. The refusals compare the right pairs:
a discovered candidate with no decision; reviewed-as-enforcement but undeclared; declared but not
reviewed-as-enforcement; reporting but undeclared (UNDECLARED, Part A-1).

Run against the real tree TODAY this REFUSES — nobody has recorded a decision for the 727 discovered
candidates — and that is the honest state: a third source that passed on our own tree would be one that
is not biting. It passes only on a fixture whose every candidate has a decision.

    python3 specs/evidence/0042/reviewed_points.py            # the real tree (expect REFUSED) and the fixture (expect PASS)
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REVIEWED_PATH = HERE / "reviewed_points.json"     # the authored artifact, when it exists
DECISIONS = ("enforcement", "not")


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key in an authored artifact is a REFUSAL, never
    last-wins — two decisions for one candidate would otherwise silently become one."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r} in the reviewed-points artifact")
        out[k] = v
    return out


def load_reviewed(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(), object_pairs_hook=_strict_pairs)


def candidate_id(site: dict) -> str:
    return f"{site['module']}:{site['qualname']}:{site['line']}:{site['kind']}"


def check_three_sets(discovered: list[dict], reviewed: dict, declared: set[str], reporting: set[str]) -> list[str]:
    p = []
    ids = {candidate_id(s) for s in discovered}
    for cid in sorted(ids):
        d = reviewed.get(cid)
        if d is None:
            p.append(f"DISCOVERED candidate with NO DECISION: {cid}")
        elif d.get("decision") not in DECISIONS or not d.get("reason") or not d.get("reviewer"):
            p.append(f"malformed decision for {cid}: {d}")
    for cid in sorted(set(reviewed) - ids):
        p.append(f"REVIEWED entry for a candidate the inventory does not discover: {cid}")
    enforcement = {cid for cid, d in reviewed.items() if d.get("decision") == "enforcement" and cid in ids}
    for cid in sorted(enforcement - declared):
        p.append(f"REVIEWED-as-enforcement but NOT DECLARED: {cid}")
    for cid in sorted(declared - enforcement):
        p.append(f"DECLARED but not REVIEWED-as-enforcement: {cid}")
    for cid in sorted(reporting - declared):
        p.append(f"reporting but not DECLARED (UNDECLARED): {cid}")
    return p


def load_discovered() -> list[dict]:
    spec = importlib.util.spec_from_file_location("inv", HERE / "decision_site_inventory.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.inventory()


FIXTURE_DISCOVERED = [
    {"module": "gate.py", "qualname": "answer", "line": 10, "kind": "RAISE"},
    {"module": "schema.py", "qualname": "Edge.assertable", "line": 20, "kind": "BOOL_RETURN"},
    {"module": "ingest.py", "qualname": "_check_arg", "line": 30, "kind": "RAISE"},
]
FIXTURE_REVIEWED = {
    "gate.py:answer:10:RAISE": {"decision": "enforcement", "reason": "refuses to answer from unverified-only support", "reviewer": "dev"},
    "schema.py:Edge.assertable:20:BOOL_RETURN": {"decision": "enforcement", "reason": "the assertable predicate gates the grounded bucket", "reviewer": "dev"},
    "ingest.py:_check_arg:30:RAISE": {"decision": "not", "reason": "argument type check, not a policy decision", "reviewer": "dev"},
}
FIXTURE_DECLARED = {"gate.py:answer:10:RAISE", "schema.py:Edge.assertable:20:BOOL_RETURN"}

if __name__ == "__main__":
    real = load_discovered()
    reviewed = load_reviewed(REVIEWED_PATH) if REVIEWED_PATH.exists() else {}
    probs = check_three_sets(real, reviewed, set(), set())
    print(f"REAL TREE: {len(real)} discovered, {len(reviewed)} decisions recorded -> {'PASS' if not probs else 'REFUSED'} ({len(probs)} refusal(s); first: {probs[0] if probs else '-'})")
    fp = check_three_sets(FIXTURE_DISCOVERED, FIXTURE_REVIEWED, FIXTURE_DECLARED, FIXTURE_DECLARED)
    print(f"FIXTURE: {'PASS' if not fp else fp}")
    sys.exit(0 if not fp else 1)
