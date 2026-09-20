"""specs/0042 (accepted v9.2) — THE RECONCILIATION FLIP over the real tree (tranche 6, 2026-09-19).

Four sets, four sources: DISCOVERED (the AST inventory, derived), REVIEWED (the authored semantic
review, GENERATED into reviewed_points.json with the line and the statement text per decision),
DECLARED (the spec-side declaration, authored from the review — INV-1's other source), INSTALLED
(the static binding scan). Every check here REFUSES on the real tree rather than on a fixture, and
each carries a negative control that makes it fail.

The second reader's checks (research, 2026-09-19), mechanical here: every decision cites the
statement it decided about and that statement is still at its line; every decision's stable key
still resolves; every DISCOVERED candidate has exactly one decision; and the collapse shape (a
function carrying more than one id on non-raising exits) is re-swept against a frozen, hand-read
allow-list — a new member refuses until it has been read.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"
SRC = ROOT / "src" / "veracium"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _reporting_ids():
    """The ids the SITES report — read from the source (every `declare_site` the scan finds), not
    from the live registry, which the census tests' autouse fixture clears under a shuffled order.
    The live registry, when a fixture has not emptied it, names only these ids."""
    inst = _load("installed_sites")
    ids = {r["id"] for r in inst.scan(inst.SRC)}
    from veracium import census
    live = set(census.registry())
    assert not live or live <= ids, sorted(live - ids)
    return ids


def _generated(script, *args):
    out = subprocess.run([sys.executable, str(EVIDENCE / script), *map(str, args)], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stdout[-800:] + out.stderr[-800:]
    return out.stdout


# ---- the committed artifacts are the generated ones ----------------------------------------------

def test_the_review_file_is_exactly_what_the_generator_produces(tmp_path):
    inv = EVIDENCE / "decision_site_inventory_OUTPUT.json"
    _generated("reviewed_points_gen.py", SRC, inv, EVIDENCE / "semantic_review.py", tmp_path / "r.json")
    assert (tmp_path / "r.json").read_text() == (EVIDENCE / "reviewed_points.json").read_text(), \
        "reviewed_points.json is stale — regenerate it from the review and the inventory"


def test_the_declaration_is_exactly_what_the_generator_produces(tmp_path):
    inv = EVIDENCE / "decision_site_inventory_OUTPUT.json"
    _generated("declaration_gen.py", inv, EVIDENCE / "semantic_review.py", tmp_path / "d.py")
    assert (tmp_path / "d.py").read_text() == (EVIDENCE / "declaration.py").read_text(), \
        "declaration.py is stale — regenerate it from the review and the inventory"


# ---- the four sets reconcile on the REAL tree --------------------------------------------------------

def test_the_four_sets_reconcile_on_the_real_tree_and_a_dropped_decision_refuses():
    rp, inst, decl = _load("reviewed_points"), _load("installed_sites"), _load("declaration")
    discovered = rp.load_discovered()
    reviewed = rp.load_reviewed(rp.REVIEWED_PATH)
    declared = set(decl.DECLARED_IDS)
    reporting = _reporting_ids()
    # check_three_sets speaks in CANDIDATE ids: the declared/reporting candidates are the reviewed
    # enforcement candidates whose site id the declaration / the sites carry
    def cands(ids):
        return {cid for cid, r in reviewed.items() if r["decision"] == "enforcement" and r["site"] in ids}
    assert rp.check_three_sets(discovered, reviewed, cands(declared), cands(reporting)) == []
    installed = inst.installed(inst.scan(inst.SRC))
    assert inst.reconcile({rp.candidate_id(s) for s in discovered}, reviewed, declared, installed, reporting) == []
    # the negative control: one decision dropped → the third source bites
    cid = next(k for k, v in reviewed.items() if v["decision"] == "not")
    fewer = {k: v for k, v in reviewed.items() if k != cid}
    assert any("NO DECISION" in p for p in rp.check_three_sets(discovered, fewer, cands(declared), cands(reporting)))
    # and one enforcement candidate whose id the declaration lacks → REVIEWED-as-enforcement but NOT DECLARED
    some = next(r["site"] for r in reviewed.values() if r["decision"] == "enforcement")
    assert any("NOT DECLARED" in p for p in rp.check_three_sets(discovered, reviewed, cands(declared - {some}), cands(reporting)))
    # and one declared id nobody bound → DECLARED but NOT INSTALLED
    assert any("NOT INSTALLED" in p for p in inst.reconcile(set(), reviewed, declared | {"phantom.site"}, installed, reporting))


def test_the_declaration_and_the_sites_are_two_sources_that_agree_in_both_directions():
    """INV-1: EXPECTED (the declaration) and OBSERVED (the registry the sites build at import) — a
    declared id that never reports, and a reporting id never declared, both refuse."""
    decl, inst = _load("declaration"), _load("installed_sites")
    declared = set(decl.DECLARED_IDS); reporting = _reporting_ids()
    assert declared == reporting, (sorted(declared - reporting), sorted(reporting - declared))
    # the declaration's file:symbol names the function whose exits go through the id's site — read
    # from the source: the function enclosing every `VAR.fire(...)` where VAR was bound to that id
    where = _functions_by_site_id()
    wrong = [(row[0], row[3], sorted(where.get(row[0], ()))) for row in decl.DECLARATION if where.get(row[0]) != {row[3]}]
    assert wrong == [], wrong


def _functions_by_site_id():
    out = {}
    for path in sorted(SRC.rglob("*.py")):
        module = str(path.relative_to(SRC)); tree = ast.parse(path.read_text())
        var_id = {n.targets[0].id: n.value.args[0].value for n in tree.body
                  if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                  and isinstance(n.value, ast.Call) and getattr(n.value.func, "id", getattr(n.value.func, "attr", "")) == "declare_site"}
        if not var_id:
            continue
        stack = []

        def visit(node, qual):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    visit(child, qual + [child.name])
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit(child, qual + [child.name])
                else:
                    v = child.value if isinstance(child, ast.Return) else child.exc if isinstance(child, ast.Raise) else None
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "fire" \
                            and isinstance(v.func.value, ast.Name) and v.func.value.id in var_id:
                        out.setdefault(var_id[v.func.value.id], set()).add(f"{module}:{'.'.join(qual)}")
                    visit(child, qual)
        visit(tree, [])
    return out


# ---- the second reader's checks --------------------------------------------------------------------

def _rows():
    rp = _load("reviewed_points")
    return rp.load_reviewed(EVIDENCE / "reviewed_points.json")   # 0026: the strict loader


def test_every_decision_still_sits_on_the_statement_it_decided_about():
    rows = _rows(); srcs = {}
    moved = []
    for cid, r in rows.items():
        module = cid.split(":", 1)[0]
        lines = srcs.setdefault(module, (SRC / module).read_text().split("\n"))
        if lines[r["line"] - 1].strip() != r["statement"]:
            moved.append((cid, r["statement"][:60], lines[r["line"] - 1].strip()[:60]))
    assert moved == [], f"decisions whose statement is no longer at their line: {moved[:5]}"


def test_every_decision_key_resolves_and_every_candidate_has_exactly_one_decision():
    rp = _load("reviewed_points"); rows = _rows()
    discovered = rp.load_discovered()
    ids = [rp.candidate_id(s) for s in discovered]
    assert len(ids) == len(set(ids)), "the inventory holds two candidates with one id"
    assert set(rows) == set(ids), (sorted(set(rows) - set(ids))[:5], sorted(set(ids) - set(rows))[:5])
    # the stable key (module:qualname:kind:ordinal) re-derives from the inventory
    import collections
    ordinal = collections.Counter(); keys = {}
    for s in sorted(discovered, key=lambda s: (s["module"], s["line"])):
        g = (s["module"], s["qualname"], s["kind"]); ordinal[g] += 1
        keys[rp.candidate_id(s)] = f"{s['module']}:{s['qualname']}:{s['kind']}:{ordinal[g]}"
    assert all(rows[c]["key"] == keys[c] for c in rows), "a decision's stable key no longer matches the inventory"


# hand-read 2026-09-19 (research's sweep after the two collapse corrections): every function
# carrying more than one id on non-raising exits, each a set of DISTINCT declining reasons
# 0041 tranche 5 (2026-09-20): the embedding upsert's body moved into `_upsert_embedding_in_txn` under the lock-taking wrapper
COLLAPSE_SWEEP_READ = frozenset({
    "asof/resolve.py:_resolve_edge", "gate.py:scoped_assertable", "graph.py:_absorption_scope_gate.same_scope",
    "store/sqlite.py:SqliteStore._ordinary_read_visible", "store/sqlite.py:SqliteStore._upsert_embedding_in_txn",
    "telemetry.py:flush_if_due", "telemetry.py:preview",
})


def test_the_collapse_shape_is_reswept_against_the_hand_read_set():
    """A function carrying MORE THAN ONE id whose entries include a return False / return None /
    Boolean return is a candidate for the collapse the review got wrong twice (`_src_revoked`,
    `_is_variant`). The set is re-derived here; a new member refuses until it has been hand-read
    and added above with its reading."""
    import collections
    rows = _rows(); by_fn = collections.defaultdict(set); kinds = collections.defaultdict(set)
    for cid, r in rows.items():
        if r["decision"] != "enforcement": continue
        module, rest = cid.split(":", 1); qual, line, kind = rest.rsplit(":", 2)
        by_fn[f"{module}:{qual}"].add(r["site"]); kinds[f"{module}:{qual}"].add(kind)
    found = {fn for fn, ids in by_fn.items() if len(ids) > 1 and kinds[fn] & {"RETURN_FALSE", "RETURN_NONE", "BOOL_RETURN"}}
    assert found == COLLAPSE_SWEEP_READ, (sorted(found - COLLAPSE_SWEEP_READ), sorted(COLLAPSE_SWEEP_READ - found))


def test_not_decisions_are_grouped_by_class_with_their_reasons():
    """The reading that matters is the NOT half; the file keeps it contiguous by class."""
    rows = _rows(); seen = []; last = None
    for r in rows.values():
        if r["class"] != last:
            seen.append(r["class"]); last = r["class"]
    assert len(seen) == len(set(seen)), f"a class appears in more than one run: {seen}"
    assert seen[0] == "enforcement"
    review = _load("semantic_review")
    for r in rows.values():
        if r["decision"] != "not":
            continue
        if r["class"] == "predicate-helper":      # the class text, then the SUBJECT (who consumes the helper)
            assert r["reason"].startswith(review.REASON_TEXT[r["class"]] + "; "), r["reason"]
        else:
            assert r["reason"] == review.REASON_TEXT[r["class"]]


def test_every_predicate_helper_reason_names_its_consumer_and_an_unresolved_helper_refuses(tmp_path):
    """Research's finding on 6a: 43 rows shared one sentence that could not be wrong ("the consumer's site is
    the enforcement point where one exists"). Now each names its consumer: a consuming SITE by id, or the
    consumers that carry none, or a hand-stated outside consumer — and a helper with none of the three
    refuses generation (the control runs the generator with the stated readings removed)."""
    import re
    rows = _rows()
    ph = {cid: r for cid, r in rows.items() if r["class"] == "predicate-helper"}
    assert ph
    forms = {"site": 0, "no-site": 0, "outside": 0}
    for cid, r in ph.items():
        tail = r["reason"].split("; ", 1)[1]
        if tail.startswith("consumed (by name) by ") and "[site " in tail:
            forms["site"] += 1
        elif tail.startswith("no consuming site — consumed (by name) by "):
            forms["no-site"] += 1
        elif tail.startswith("no product consumer — "):
            forms["outside"] += 1
        else:
            raise AssertionError(f"{cid}: reason without a subject: {r['reason']}")
        # a named consuming site is a site the review declares
        for sid in re.findall(r"\[site ([^\]]+)\]", tail):
            for one in sid.split(", "):
                assert any(x["decision"] == "enforcement" and x["site"] == one for x in rows.values()), (cid, one)
    assert all(forms.values()), forms      # every form is REACHED, or the branch it names was never tested
    # the control: strip the stated readings → the generator refuses and names a helper
    review = (EVIDENCE / "semantic_review.py").read_text()
    assert "CONSUMED_OUTSIDE = {" in review
    stripped = review[:review.index("CONSUMED_OUTSIDE = {")] + "CONSUMED_OUTSIDE = {}\n"
    (tmp_path / "semantic_review.py").write_text(stripped)
    inv = EVIDENCE / "decision_site_inventory_OUTPUT.json"
    out = subprocess.run([sys.executable, str(EVIDENCE / "reviewed_points_gen.py"), str(SRC), str(inv), str(tmp_path / "semantic_review.py"), str(tmp_path / "r.json")],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode != 0 and "REFUSED: predicate-helper" in (out.stderr + out.stdout), (out.returncode, out.stderr[-300:])
    assert not (tmp_path / "r.json").exists()
