"""T12, the generated PRODUCT obligation map (V44 L20, L58–L62; build note b2870871 D10 as replaced by addendum 1's
M1, P7, P8): the committed map is what a fresh derivation produces from the tree and the consolidated campaign's
committed result, every frozen row is CLOSED (or withdrawn), and the generator refuses each defect it exists to catch
(P1's matrix for `specs/evidence/0044/obligation_map.py`).
"""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "specs" / "evidence" / "0044" / "obligation_map.py"


def _gen():
    name = "obligation_map_0044"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, GEN)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


@pytest.fixture(scope="module")
def committed():
    g = _gen()
    defs = g._load(g.CAMPAIGN / "defs.py", "obligation_campaign_defs_t")
    return defs, json.loads((g.CAMPAIGN / "result.json").read_text())


def test_the_committed_map_is_what_a_fresh_derivation_produces_and_every_row_is_closed(committed):
    """Data to data: obligation_map.json and .md equal a fresh derivation over the tree and the committed campaign,
    the derivation raises none of the generator's refusals — the campaign ran at THIS tree's pin digest, every defined
    mutant has a result, every control was green — and every frozen row is CLOSED or withdrawn (M1)."""
    g = _gen()
    m = g.derive(*committed)
    assert g.problems(m) == []
    assert json.dumps(g._public(m), indent=1, sort_keys=True, ensure_ascii=False) + "\n" == g.OUT_JSON.read_text(), \
        "regenerate with --write"
    assert g.render(m) == g.OUT_MD.read_text(), "regenerate with --write"
    assert {r["state"] for r in m["rows"].values()} <= {"closed", "withdrawn"}
    assert [k for k, r in m["rows"].items() if r["state"] == "withdrawn"] == ["0041 INV-RR13"]


def test_the_row_set_is_every_documents_table():
    """The rows are parsed from each document's own table, never listed: the seven documents' counts, 0018's two
    tables (I13–I23 and the amendment's I24–I32), and 0003's own I-rows NOT taken (the programme's rows there are the
    amendment's INV-O1–O10)."""
    from collections import Counter
    R = _gen().rows()
    assert Counter(r["doc"] for r in R.values()) == {"0044": 23, "0047": 23, "0018": 20, "0008": 19, "0041": 14,
                                                    "0003": 10, "0045": 10}
    assert {r["id"] for r in R.values() if r["doc"] == "0018"} == {f"I{n}" for n in range(13, 33)}
    assert {r["id"] for r in R.values() if r["doc"] == "0003"} == {f"INV-O{n}" for n in range(1, 11)}
    # 0008: the amendment's INV-Q/INV-I and the two C-rows it amended (C8, C11: research's P9), no other C-row
    assert {r["id"] for r in R.values() if r["doc"] == "0008" and not r["id"].startswith("INV-")} == {"C8", "C11"}


def _fake(defs_groups, answers=None, rows=None, controls=True, pin="x", retired=None):
    """A synthetic campaign: each result row carries the digest of the definition it names (as a real run's do)."""
    defs = types.SimpleNamespace(GROUPS=defs_groups, ANSWERS=answers or {}, RETIRED=retired or [])
    dg = {(g, m[0]): _gen().def_digest(g, m) for g, _c, ms in defs_groups for m in ms}
    rows = [dict(r, def_digest=r.get("def_digest", dg.get((r["group"], r["mutant"])))) for r in rows or []]
    result = {"rows": rows or [], "summary": {"mutants": len(rows or []), "killed": 0, "controls_green": controls},
              "pin_digest": pin}
    return defs, result


_NODE = "tests/test_0044_t12_fixes.py::test_n3_a_row_whose_column_and_json_disagree_refuses_the_v16_step"


def test_the_map_refuses_each_planted_defect(monkeypatch):
    """P1's matrix for obligation_map.py, each with its control, over SYNTHETIC campaigns only (the campaign that
    writes the committed result runs this cell as a control, so it never reads that result): a row's cited test renamed (the row loses its node and
    is listed open); a docstring citation alone (a bound node, no killing answering mutant: open); a kill by a node
    NOT bound to the row (open); a campaign at another pin digest; a mutant with no result; a red control; an ANSWERS
    entry naming no mutant or no row; a gate quote that no longer occurs; I31's DERIVED quote gone; a withdrawn row
    owes nothing; a bare id (`A1`) is not read as INV-A1; an ANSWERS entry without a why or whose clause is not
    the row's text; a bold id row outside every row and NON_ROW family (the complement); a withdrawal no longer
    quoted; a binding edit that is gone; a retired mutant whose inverse is not KILLED or whose commit is unnamed."""
    g = _gen()
    grp = [("G (INV-A1)", ["t"], [("INV-A1: planted", "src/veracium/__init__.py", "x", "y")])]
    killed = {"group": "G (INV-A1)", "mutant": "INV-A1: planted", "outcome": "KILLED", "cell_kinds": {}}
    # control: INV-A1 closes when a node bound to it kills the answering mutant
    bound_a1 = sorted(g.derive(*_fake(grp, rows=[dict(killed, cell_kinds={})]))["rows"]["0044 INV-A1"]["bound"])
    assert bound_a1, "INV-A1 has a bound node"
    ok = dict(killed, cell_kinds={bound_a1[0] + "[p]": "assertion"})
    m = g.derive(*_fake(grp, rows=[ok]))
    assert m["rows"]["0044 INV-A1"]["state"] == "closed"
    # a citation alone: the mutant survives → open
    m = g.derive(*_fake(grp, rows=[dict(killed, outcome="SURVIVED")]))
    assert m["rows"]["0044 INV-A1"]["state"] == "open: no answering mutant killed by a bound node"
    # a kill by a node bound to another row only → open, and a FINDING the map refuses (P10)
    m = g.derive(*_fake(grp, rows=[dict(killed, cell_kinds={"tests/test_x.py::test_unbound": "assertion"})]))
    assert m["rows"]["0044 INV-A1"]["state"].startswith("open")
    assert [f["row"] for f in m["findings_unbound_kills"]] == ["0044 INV-A1"]
    assert any(x.startswith("FINDING 0044 INV-A1") for x in g.problems(m))
    assert not g.derive(*_fake(grp, rows=[ok]))["findings_unbound_kills"]
    # NOT_ANSWERS excludes a pair (and it is listed); one naming no mutant refuses
    na = types.SimpleNamespace(GROUPS=grp, ANSWERS={}, RETIRED=[],
                               NOT_ANSWERS={("G (INV-A1) :: INV-A1: planted", "0044 INV-A1"): "judged not to"})
    m = g.derive(na, _fake(grp, rows=[ok])[1])
    assert m["rows"]["0044 INV-A1"]["state"] == "open: no answering mutant" and m["not_answers"]
    na.NOT_ANSWERS = {("nope :: nope", "0044 INV-A1"): "x"}
    assert any("NOT_ANSWERS names an unknown" in x for x in g.problems(g.derive(na, _fake(grp, rows=[ok])[1])))
    # a GROUP label answers nothing, bare or INV- (labels name a tranche's theme or list several rows); the NAME does
    lab = [("G (C11, D2)", ["t"], [("D2: planted", "src/veracium/__init__.py", "x", "y")])]
    assert not g.derive(*_fake(lab))["rows"]["0008 C11"]["answering"]
    lab = [("G (INV-A1: the rule)", ["t"], [("D2: planted", "src/veracium/__init__.py", "x", "y")])]
    assert not g.derive(*_fake(lab))["rows"]["0044 INV-A1"]["answering"]
    assert g.derive(*_fake(grp))["rows"]["0044 INV-A1"]["answering"]
    # a bare native id binds outside its document's own modules only when qualified by the document ("0008 C11")
    c11 = g.derive(*_fake(grp))["rows"]["0008 C11"]["bound"]
    assert "tests/test_0047_t11b_portability.py::test_c11_export_carries_confirmations_with_origin_and_derived_identity" in c11
    assert not [n for n in c11 if not (n.startswith("tests/test_0008_") or n.startswith("tests/test_confirm_contract_0008")
                                       or "0008 C11" in g.nodes()[n])]
    # a bare id is not read: the same mutant named "A1: planted" answers nothing
    bare = [("G", ["t"], [("A1: planted", "src/veracium/__init__.py", "x", "y")])]
    m = g.derive(*_fake(bare, rows=[dict(ok, group="G", mutant="A1: planted")]))
    assert m["rows"]["0044 INV-A1"]["state"] == "open: no answering mutant"
    # the cited test renamed: a row bound only by naming its test loses it (I13's three named nodes are declared
    # renames; drop the declarations and the row binds nothing by name)
    monkeypatch.setattr(g, "renames", lambda: {})
    m = g.derive(*_fake(grp, rows=[ok]))
    assert not [n for n, how in m["rows"]["0018 I13"]["bound"].items() if "declared rename" in how]
    monkeypatch.undo()
    m = g.derive(*_fake(grp, rows=[ok]))
    assert [n for n, how in m["rows"]["0018 I13"]["bound"].items() if "declared rename" in how]
    # the campaign's own refusals; control: a campaign at this tree's digest, one result per mutant, controls green
    base = g.derive(*_fake(grp, rows=[ok]))
    base["campaign"]["pin_digest"] = base["campaign"]["tree_digest"]
    camp = ("re-run the consolidated campaign", "result(s) for", "control was not green", "ANSWERS names an unknown",
            "gate's quote no longer occurs", "DERIVED binding is stale")
    assert not [x for x in g.problems(base) if any(c in x for c in camp)]
    m = copy.deepcopy(base)
    m["campaign"]["pin_digest"] = "0" * 64
    assert any("re-run the consolidated campaign" in x for x in g.problems(m))
    m = copy.deepcopy(base)
    m["campaign"]["results"] -= 1
    assert any("result(s) for" in x for x in g.problems(m))
    # a result row that ran another definition (or none recorded): refused until re-run
    assert not [x for x in g.problems(base) if "ran a definition other than" in x]
    m = g.derive(*_fake(grp, rows=[dict(ok, def_digest="0" * 64)]))
    assert any("ran a definition other than" in x for x in g.problems(m))
    m = copy.deepcopy(base)
    m["campaign"]["summary"]["controls_green"] = False
    assert any("control was not green" in x for x in g.problems(m))
    e = lambda row, clause="a `multi` relation never supersedes on a differing value", why="w": \
        {"row": row, "clause": clause, "why": why}
    m = g.derive(*_fake(grp, answers={"G (INV-A1) :: INV-A1: planted": [e("0044 INV-A1")]}, rows=[ok]))
    assert not [x for x in g.problems(m) if "ANSWERS" in x]
    m = g.derive(*_fake(grp, answers={"nope :: nope": [e("0044 INV-A1")],
                                      "G (INV-A1) :: INV-A1: planted": [e("0044 INV-A99")]}, rows=[ok]))
    assert len([x for x in g.problems(m) if "ANSWERS names an unknown" in x]) == 2
    m = g.derive(*_fake(grp, answers={"G (INV-A1) :: INV-A1: planted": [e("0044 INV-A1", clause="not in the row")]},
                        rows=[ok]))
    assert any("clause is not quoted from the row" in x for x in g.problems(m))
    m = g.derive(*_fake(grp, answers={"G (INV-A1) :: INV-A1: planted": [e("0044 INV-A1", why="")]}, rows=[ok]))
    assert any("lacks a why" in x for x in g.problems(m))
    # the complement: drop 0008's C-family declaration and its C rows surface
    assert g.complement() == []
    monkeypatch.setattr(g, "NON_ROWS", {k: v for k, v in g.NON_ROWS.items() if k[0] != "0008"})
    assert "0008 C9" in g.complement() and "0008 C8" not in g.complement()
    monkeypatch.undo()
    # S2-P2: a pair both in ANSWERS and NOT_ANSWERS refuses (one judgement contradicts the other); control: exclusive
    both = types.SimpleNamespace(GROUPS=grp, RETIRED=[], ANSWERS={"G (INV-A1) :: INV-A1: planted": [e("0044 INV-A1")]},
                                 NOT_ANSWERS={("G (INV-A1) :: INV-A1: planted", "0044 INV-A1"): "judged not to"})
    assert any("both hold" in x for x in g.problems(g.derive(both, _fake(grp, rows=[ok])[1])))
    assert not [x for x in g.problems(base) if "both hold" in x]
    # S2-P1: the cell a clause quotes is derived from the row's columns — invariant, mutant, or (where the id shares
    # its cell with the invariant, 0018's I13–I23 and 0008's C-rows) check
    R = g.rows()
    assert g.clause_cell(R["0044 INV-A15"], "the plan is fixed at its first write") == "invariant"
    assert g.clause_cell(R["0044 INV-A15"], "re-plan on each call") == "mutant"
    assert g.clause_cell(R["0018 I15"], "test_migration_result_truth_table") == "check"
    assert g.clause_cell(R["0044 INV-A15"], "words in no cell") is None
    # a NON_ROW family whose quoted reason the spec no longer holds
    monkeypatch.setitem(g.NON_ROWS, ("0008", r"C(?:[1-79]|10|12|2a)"), ("r", ("0008-staleness-clearing", "words not in 0008")))
    assert any("NON_ROW family" in x for x in g.problems(base))
    monkeypatch.undo()
    assert not [x for x in g.problems(base) if "NON_ROW family" in x]
    # a withdrawal no longer quoted
    monkeypatch.setitem(g.WITHDRAWN, "0041 INV-RR13", "**Withdrawn for another reason.**")
    assert any("withdrawal no longer reads" in x for x in g.problems(base))
    monkeypatch.undo()
    # a binding edit: its citation gone; its clause not the row's; its asserting line not in the test; its node not
    # bound to the row (research's T12 D10 ask: "does this line assert this clause"). Control: every committed entry.
    assert not [x for x in g.problems(base) if x.startswith("binding edit")]
    assert all(e["line"] and e["bound"] for e in base["binding_edits"])
    node, cited, row, clause, line = g.BINDING_EDITS[0]
    for planted, msg in (((node, "a citation the node does not carry", row, clause, line), "binding edit gone"),
                         ((node, cited, row, "words the row does not hold", line), "is not the row's text"),
                         ((node, cited, row, clause, "assert a line the test does not hold"), "is not in the test"),
                         ((node, cited, "0044 INV-A1", "a `multi` relation never supersedes on a differing value", line),
                          "the node is not bound to the row")):
        monkeypatch.setattr(g, "BINDING_EDITS", (planted,))
        assert any(msg in x for x in g.problems(g.derive(*_fake(grp, rows=[ok])))), msg
        monkeypatch.undo()
    # a retired mutant: its inverse must read KILLED and its commit be named
    ret = [{"mutant": "R :: old", "reason": "r", "commit": "abc1234", "inverse": "G (INV-A1) :: INV-A1: planted"}]
    assert not [x for x in g.problems(g.derive(*_fake(grp, rows=[ok], retired=ret))) if x.startswith("retired")]
    assert any(x.startswith("retired") for x in g.problems(g.derive(*_fake(grp, rows=[dict(ok, outcome="SURVIVED")],
                                                                          retired=ret))))
    assert any(x.startswith("retired") for x in g.problems(g.derive(*_fake(grp, rows=[ok],
                                                                          retired=[dict(ret[0], commit="")]))))
    m = copy.deepcopy(base)
    m["gates"]["0044"]["quote"] = "a sentence the spec does not hold"
    assert any("gate's quote no longer occurs" in x for x in g.problems(m))
    monkeypatch.setitem(g.DERIVED, "0018 I31", ("a phrase I31 does not read", g.DERIVED["0018 I31"][1]))
    assert any("DERIVED binding is stale" in x for x in g.problems(base))
    monkeypatch.undo()
    # a withdrawn row owes nothing and is never listed open
    assert base["rows"]["0041 INV-RR13"]["state"] == "withdrawn"
    assert not [x for x in g.problems(base) if x.startswith("0041 INV-RR13")]
