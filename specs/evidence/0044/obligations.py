"""Package I's obligation map — every §6 row of the four documents, mapped to the model check that exercises it or to
the stated reason it is a PRODUCT obligation (the 0044 round-2 verdict, R2-08: "ship an obligation-to-model/check/
mutant map"; the review manifest the archive feedback asked for is the same artifact).

Three checks run over it, each DERIVED rather than listed (the "hand list for a derivable set" class):
  rows      every invariant row of each document's §6 is mapped, by parsing the document; every mapped model invariant
            exists and is killed by a mutant it owns; every model invariant is claimed by at least one row.
  domains   THE MODEL KNOWS MORE THAN THE WIRE (I R2-01, II R2-03; research's typed-carrier refinement): every field of the
            model's state maps to exactly one carrier with a time DOMAIN, and every comparison in the model's source
            compares two operands of one domain. A single clock standing in for valid time and transaction time fails.
  guards    THE MODEL REMEMBERS WHAT THE STORE FORGOT (I R2-04 ¶3, I R2-07): the replay and receipt paths never
            subscript live edge state (`s.edges[...]`); they read it through `.get` and render what is absent.
  shared    the 0008 amendment travels in both packages: every row this map hands to model II ("MODEL-II") must be
            cited there by a model II invariant that owns a killed mutant answering it (research's refusal).
Run: `python obligations.py [<doc>=<path> ...]` — prints problems and exits non-zero if any.
"""
# Mutation-Matrix: tests/test_reference_models.py::test_the_obligation_map_refuses_each_broken_carrier
from __future__ import annotations

import ast
import dataclasses
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arity_model as M  # noqa: E402


def _load(name: str, path: pathlib.Path):
    """A module BY FILE under a unique name: both package models name their runner `run_model.py`, so a bare import
    returns whichever the process loaded first (the round-3 suite's KeyError)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RUN = _load("arity_run_model_0044", HERE / "run_model.py")

# --------------------------------------------------------------------------------------------- the typed carriers
# model field -> (the persisted/exported carrier it stands for, its time DOMAIN). Domains: valid (when a fact held:
# valid_from, invalidated_at), transaction (0029's txn), act_ordinal (the 0008 amendment's store-wide act_seq),
# none (not a time). Every dataclass field of the model's state must appear (checked).
CARRIERS = {
    "Edge.id": ("edges.id", "none"), "Edge.user": ("edges.user_id", "none"), "Edge.relation": ("edges.relation", "none"),
    "Edge.obj": ("edges.object", "none"), "Edge.source": ("edges.provenance.source_id", "none"),
    "Edge.active": ("edges.active (derived from invalidated_at IS NULL)", "none"),
    "Edge.valid_from": ("edges.valid_from", "valid"), "Edge.invalidated_at": ("edges.invalidated_at", "valid"),
    "Edge.reason": ("edges.invalidation_reason", "none"), "Edge.supersedes": ("edges.supersedes", "none"),
    "Edge.counters": ("edges.reinforcement counters", "none"), "Edge.basis": ("contribution_ledger (0022 basis)", "none"),
    "Edge.redacted": ("redactions (0041 attestation)", "none"),
    "Store.origin": ("store_identity.origin (0006)", "none"), "Store.edges": ("edges", "none"),
    "Store.txn": ("edge_event.txn (0029)", "transaction"),
    "Store.act_counter": ("the 0008 amendment's act counter row", "act_ordinal"),
    "Store.schema_v16": ("schema version (0013)", "none"), "Store.revoked": ("source_revocations (0022)", "none"),
    "Store.refusals": ("supersession_refusals", "none"), "Store.inventory": ("arity_inventory (retirements)", "none"),
    "Store.refusal_inventory": ("arity_inventory (refusals)", "none"), "Store.header": ("plan_header", "none"),
    "Store.plan": ("reclassification_plan rows", "none"), "Store.runs": ("migration_run", "none"),
    "Store.outcomes": ("migration_outcome", "none"), "Store.registry": ("request_registry (0008am)", "none"),
    "Store.confirmations": ("confirmations (0008)", "none"), "Store.journal": ("edge_event (0029, never exported)", "none"),
}
# names that carry a domain wherever they appear in the model's source (attributes, dict keys, tuple slots)
NAME_DOMAINS = {"invalidated_at": "valid", "valid_from": "valid", "pre_invalidated_at": "valid", "at_valid": "valid",
                "txn": "transaction", "written_txn": "transaction", "act_counter": "act_ordinal"}

# --------------------------------------------------------------------------------------------- the rows
# (document, row id) -> model invariants that exercise it, or ("PRODUCT", why)
ROWS = {
    ("0044", "INV-A1"): ["INV-M21"], ("0044", "INV-A2"): ["INV-M21"], ("0044", "INV-A3"): ["INV-M21"],
    ("0044", "INV-A4"): ["INV-M21"], ("0044", "INV-A5"): ["INV-M5"], ("0044", "INV-A6"): ["INV-M12"],
    ("0044", "INV-A7"): ["INV-M8"], ("0044", "INV-A8"): ["INV-M3"], ("0044", "INV-A9"): ["INV-M2"],
    ("0044", "INV-A10"): ["INV-M21"], ("0044", "INV-A11"): ["INV-M1"], ("0044", "INV-A12"): ["INV-M16", "INV-M4"],
    ("0044", "INV-A13"): ["INV-M4", "INV-M10", "INV-M11", "INV-M17"], ("0044", "INV-A14"): ["INV-M12"],
    ("0044", "INV-A15"): ["INV-M14"], ("0044", "INV-A16"): ["INV-M7", "INV-M20"],
    ("0044", "INV-A17"): ["INV-M6", "INV-M7", "INV-M19"], ("0044", "INV-A18"): ["INV-J1", "INV-J2", "INV-J3"],
    ("0044", "INV-A19"): ["INV-M13"],
    ("0044", "INV-A20"): {"model": ["INV-M18"], "product": "the census: any `DELETE FROM edges` outside the per-user "
                                                           "erasure loop fails (research, construction §3)"},
    ("0044", "INV-A21"): ["INV-M14"],
    ("0018am", "I24"): ("PRODUCT", "a byte comparison of a real v15 store through the real step; the model's step "
                                   "writes only its inventory tables, which is the design claim — the byte check is "
                                   "the implementation's"),
    ("0018am", "I25"): ["INV-M14"], ("0018am", "I26"): ["INV-M2"], ("0018am", "I27"): ["INV-M14", "INV-M15"],
    ("0018am", "I28"): ["INV-M2"], ("0018am", "I29"): ["INV-M15"], ("0018am", "I30"): ["INV-M14"],
    ("0018am", "I31"): ("PRODUCT", "0018's existing I13–I23 tests, run unmodified"),
    ("0003am", "INV-O1"): ("PRODUCT", "narrowed (owner, 2026-10-12): the renderer ships unchanged; bound to the shipped "
                                      "build and render path at implementation"),
    ("0003am", "INV-O2"): ("PRODUCT", "narrowed: determinism of the shipped render path"),
    ("0003am", "INV-O3"): ("PRODUCT", "narrowed: R2-09's closure binds the SHIPPED renderer with independently derived "
                                      "totals (a test against the renderer, not the model)"),
    ("0003am", "INV-O4"): ("PRODUCT", "narrowed: query-independence of the shipped block"),
    ("0003am", "INV-O5"): ("PRODUCT", "narrowed: the renderer's first-line rule, unchanged"),
    ("0003am", "INV-O6"): ["INV-M9"], ("0003am", "INV-O7"): ["INV-M21"], ("0003am", "INV-O8"): ["INV-M9"],
    ("0003am", "INV-O9"): ["INV-M9"], ("0003am", "INV-O10"): ["INV-M9"],
    # the 0008 amendment travels in BOTH packages (the owner's hosting ruling): model I carries undo's side of it; the
    # acts' side is model II's, named here and checked by model II's map at package II's stage
    ("0008am", "INV-Q1"): ["INV-M17"], ("0008am", "INV-Q2"): ["INV-M17"],
    ("0008am", "INV-Q3"): ("MODEL-II", "the confirmations backfill"),
    ("0008am", "INV-Q4′"): ("MODEL-II", "internal act keys"),
    ("0008am", "INV-Q5"): ["INV-M19"], ("0008am", "INV-Q6"): ["INV-M18"],
    ("0008am", "INV-Q7"): ("MODEL-II", "digest treatment of acts"), ("0008am", "INV-Q8"): ["INV-M22"],
    ("0008am", "INV-Q9"): ("MODEL-II", "the act ordinal and the origin check"),
    ("0008am", "INV-I1"): ("MODEL-II", "repeat import of acts"), ("0008am", "INV-I2"): ("MODEL-II", "changed act"),
    ("0008am", "INV-I3"): ("MODEL-II", "exact replay and the held target"),
}

# paths that must never subscript live edge state (the store may have erased or never held the edge)
GUARDED_PATHS = ("receipt", "undo", "_replay")

_ROW = re.compile(r"^\| \*\*((?:INV-[A-Z]+|I)\d+[a-z]?′?)\*\* \|", re.M)


def section6_rows(text: str) -> list:
    m = re.search(r"^## 6\..*?(?=^## 7\.)", text, re.M | re.S)
    if not m:
        raise ValueError("no §6 section")
    return _ROW.findall(m.group(0))


def check_rows(docs: dict, mutants: dict) -> list:
    problems = []
    invariants = set(RUN.INVARIANTS)
    owned = {m["owner"] for m in mutants.values() if m["killed_by_owner"]}
    claimed = set()
    for doc, text in docs.items():
        for row in section6_rows(text):
            target = ROWS.get((doc, row))
            if target is None:
                problems.append(f"ROWS {doc} {row}: unmapped — map it to a model invariant or state its PRODUCT reason")
                continue
            if isinstance(target, tuple):
                if target[0] not in ("PRODUCT", "MODEL-II") or not target[1].strip():
                    problems.append(f"ROWS {doc} {row}: a non-model mapping must be ('PRODUCT' or 'MODEL-II', reason)")
                continue
            if isinstance(target, dict):                # a row with a model part AND a product part
                if not target.get("product", "").strip() or not target.get("model"):
                    problems.append(f"ROWS {doc} {row}: a two-part mapping needs both `model` and a `product` reason")
                    continue
                target = target["model"]
            for inv in target:
                if inv not in invariants:
                    problems.append(f"ROWS {doc} {row}: maps to {inv}, which the model does not define")
                elif inv not in owned:
                    problems.append(f"ROWS {doc} {row}: {inv} owns no killed mutant — it is not shown able to fail")
                claimed.add(inv)
        stale = sorted(r for d, r in ROWS if d == doc and r not in section6_rows(text))
        problems += [f"ROWS {doc} {r}: mapped but not in the document's §6" for r in stale]
    if docs and set(docs) >= {d for d, _ in ROWS}:
        problems += [f"ROWS: model invariant {i} is claimed by no row" for i in sorted(invariants - claimed)]
    return problems


def check_domains(sources: dict) -> list:
    """Every model state field is typed; every comparison compares ONE domain. A local bound by a simple assignment
    from a typed expression takes its domain (so `t = s.txn; e.invalidated_at < t` is the cross-domain comparison it
    is), and a comparison of a typed operand with a non-constant operand whose domain is unknown FAILS CLOSED
    (research's note: one alias otherwise hid the R2-01 mutant)."""
    problems = []
    for cls in (M.Edge, M.Store):
        for f in dataclasses.fields(cls):
            key = f"{cls.__name__}.{f.name}"
            if key not in CARRIERS:
                problems.append(f"DOMAIN {key}: a model field with no declared carrier and domain")
    for label, src in sources.items():
        tree = ast.parse(src)
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Lambda))] or [tree]:
            local = {}
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    d = _domain(node.value, local)
                    if d is not None:
                        local[node.targets[0].id] = d
            for node in ast.walk(fn):
                if not isinstance(node, ast.Compare):
                    continue
                operands = [node.left, *node.comparators]
                doms = [_domain(o, local) for o in operands]
                typed = {d for d in doms if d is not None}
                where = f"DOMAIN {label}:{node.lineno}: `{ast.unparse(node)[:80]}`"
                if len(typed) > 1:
                    problems.append(f"{where} compares {sorted(typed)}")
                elif typed and any(d is None and not _inert(o) for d, o in zip(doms, operands)):
                    problems.append(f"{where} compares {sorted(typed)} with an operand of unknown domain")
    return sorted(set(problems))


def _inert(node) -> bool:
    """An operand that carries no time: a constant (None, a literal), a tuple/list/set/dict display, or a call whose
    value is not a time (len, a membership collection)."""
    return isinstance(node, (ast.Constant, ast.Tuple, ast.List, ast.Set, ast.Dict))


def _domain(node, local=None):
    local = local or {}
    if isinstance(node, ast.Attribute):
        return NAME_DOMAINS.get(node.attr)
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
        return NAME_DOMAINS.get(node.slice.value)
    if isinstance(node, ast.Name):
        return local.get(node.id, NAME_DOMAINS.get(node.id))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "begin":
        return "transaction"                         # Store.begin() returns the new txn
    if isinstance(node, ast.BinOp):
        doms = {_domain(node.left, local), _domain(node.right, local)} - {None}
        return doms.pop() if len(doms) == 1 else None
    return None


def check_guards(sources: dict) -> list:
    """The replay and receipt paths read edge state through `.get` only — including every module function they call,
    transitively (research's note: a name-matched check let a helper do the read)."""
    problems = []
    for label, src in sources.items():
        tree = ast.parse(src)
        fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        reach, todo = set(), [n for n in GUARDED_PATHS if n in fns]
        while todo:
            name = todo.pop()
            if name in reach:
                continue
            reach.add(name)
            for node in ast.walk(fns[name]):
                if isinstance(node, ast.Call):
                    callee = (node.func.id if isinstance(node.func, ast.Name)
                              else node.func.attr if isinstance(node.func, ast.Attribute) else None)
                    if callee in fns and callee not in reach:
                        todo.append(callee)
        for name in sorted(reach):
            for node in ast.walk(fns[name]):
                if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                        and node.value.attr == "edges" and isinstance(node.ctx, ast.Load)):
                    problems.append(f"GUARD {label}:{node.lineno}: `{name}` (reached from {GUARDED_PATHS}) subscripts "
                                    f"live edge state (`{ast.unparse(node)}`) — read it with .get and render what is absent")
    return problems


def check_shared(doc_0008am: str, mutants_ii: dict) -> list:
    """Every 0008am row this map hands to model II is cited there by a model II invariant that owns a killed mutant
    answering it (research: the hand-off is a refusal, not a sentence)."""
    model_citations = _load("model_citations_0045", HERE.parent / "0045" / "model_citations.py")
    rows, doc_level = model_citations.parse(doc_0008am)[:2]
    problems = []
    for (doc, row), target in ROWS.items():
        if doc != "0008am" or not (isinstance(target, tuple) and target[0] == "MODEL-II"):
            continue
        # an amendment cites its model at document level ("*MODEL: … (its G11)*") or per row ("(model G11)")
        cites = {f"MODEL-{g}" for g in rows.get(row, set()) | doc_level}
        answering = [n for n, m in mutants_ii.items() if f"0008am {row}" in m.get("answers", ())
                     and m["killed_by_owner"] and m["owner"] in cites]
        if not cites:
            problems.append(f"SHARED 0008am {row}: handed to model II, but the row cites no model II invariant")
        elif not answering:
            problems.append(f"SHARED 0008am {row}: no killed model II mutant owned by {sorted(cites)} answers it")
    return problems


def check(docs: dict) -> list:
    src = {"arity_model.py": (HERE / "arity_model.py").read_text()}
    out = check_rows(docs, RUN.run_mutants()) + check_domains(src) + check_guards(src)
    if "0008am" in docs:
        out += check_shared(docs["0008am"], _load("grounding_run_model_0045", HERE.parent / "0045" / "run_model.py").run_mutants())
    return out


if __name__ == "__main__":
    docs = {}
    for arg in sys.argv[1:]:
        k, v = arg.split("=", 1)
        docs[k] = pathlib.Path(v).read_text(encoding="utf-8")
    probs = check(docs)
    print("\n".join(probs) if probs else f"obligation map: 0 problems over {sorted(docs)}")
    sys.exit(1 if probs else 0)
