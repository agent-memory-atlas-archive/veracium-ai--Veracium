"""specs/0042 (exercised guarantees, draft) — the round-1 verdict's executed claims,
reproduced as the reviewer found them and kept runnable, and the evidence the next
package carries in answer: the examiner projection with a DERIVED forbidden set, the
decision-site inventory over all of src, the abstention counter-cases, the two row
shapes. Every "shipped behaviour" check here FAILS the day the behaviour changes —
when the harness spec's adjudicator exists, these are its first controls.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _fixture_mem(db):
    spec = importlib.util.spec_from_file_location("t_introspect", ROOT / "tests" / "test_introspect_cli.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m._seeded_mem(db)


# ---- amendment 2: the examiner input ------------------------------------------------

def test_a2_forbidden_set_is_derived_and_carries_the_reviewers_three_quotes():
    ep = _load("examiner_projection")
    d = ep.derive_forbidden_markers()
    assert set(d["prose"]) >= {"graph.py:render_edges", "graph.py:_origin_label", "graph.py:_ORIGIN_LABELS"}
    assert set(d["metadata"]) == {"schema.EvidenceAuthor", "introspect.by_disclosure", "introspect.keys"}
    # content words are NOT prose markers: the render says "user" and "claims:" without labelling anything
    assert "user" not in {f for fr in d["prose"].values() for f in fr}
    frags = ep.forbidden_fragments()
    assert len(frags) >= 10
    # the three strings the reviewer quoted are fragments of the derived set, not a hand list
    joined = "\n".join(frags)
    assert "never assert as fact" in joined and "unconfirmed" in joined and "third-party-derived" in joined
    assert "by_author" in frags and "by_disclosure" in frags


def test_a2_derivation_refuses_when_a_render_source_is_missing(monkeypatch):
    ep = _load("examiner_projection")
    monkeypatch.setattr(ep, "_RENDER_FUNCTIONS", ("render_edges", "_no_such_function"))
    with pytest.raises(RuntimeError, match="_no_such_function"):
        ep.derive_forbidden_markers()


def test_a2_introspect_categories_exposes_the_labels_and_the_projection_does_not():
    ep = _load("examiner_projection")
    from veracium.graph import render_edges
    derived = ep.derive_forbidden_markers()
    with tempfile.TemporaryDirectory() as d:
        mem = _fixture_mem(f"{d}/t.db")
        cats = json.dumps(mem.introspect("ida", mode="categories"))
        edges = [e for e in mem.store.edges("ida", active_only=False, include_quarantined=True) if e.active]
        rendered = render_edges(edges)
        rows = ep.project(mem.store, "ida"); text, digest = ep.freeze(rows)
        mem.close()
    # the reviewer's reproduction, kept runnable: introspect hands the examiner the labels
    assert {"UNVERIFIED third-party claim, never assert as fact", "unconfirmed", "third-party-derived",
            "by_author", "by_disclosure", "third_party", "quarantined"} <= set(ep.hits(cats, derived))
    # negative control on the forbidden set: the render carries it
    assert "UNVERIFIED third-party claim, never assert as fact" in ep.hits(rendered, derived)
    # the projection carries NONE of it, and every active record is present in one shape
    assert ep.hits(text, derived) == []
    assert len(rows) == len(edges) == 3
    assert set(rows[0]) == {"subject", "relation", "object", "since"}
    assert {r["relation"] for r in rows} == {"has_pet", "prefers", "third_party_claim"}
    assert len(digest) == 64 and ep.freeze(rows)[1] == digest  # frozen input is deterministic


def test_a2_projection_hides_a_label_that_appears_in_a_new_render_string(monkeypatch):
    """Mutant: a new render label appears in graph.py — the derived set must grow to
    include it without anyone editing the evidence (the derivation reads the source)."""
    ep = _load("examiner_projection")
    src = (ROOT / "src/veracium/graph.py").read_text()
    mutated = src.replace('ug = " [possible extraction error]"', 'ug = " [possible extraction error] [FRESHLY-LABELLED-MUTANT]"')
    assert mutated != src
    with tempfile.TemporaryDirectory() as d:
        fake_src = pathlib.Path(d) / "veracium"; fake_src.mkdir()
        (fake_src / "graph.py").write_text(mutated)
        (fake_src / "introspect.py").write_text((ROOT / "src/veracium/introspect.py").read_text())
        monkeypatch.setattr(ep, "SRC", fake_src)
        frags = ep.forbidden_fragments()
        assert "FRESHLY-LABELLED-MUTANT" in frags            # the new label is its own fragment
        assert "possible extraction error" in frags         # and did not swallow its neighbour


# ---- amendment 3: the abstention heuristic --------------------------------------------

def test_a3_disclaimer_then_assertion_counts_as_abstention_in_the_shipped_regex():
    ac = _load("abstention_counter_cases")
    rows = ac.table()
    wrong = [(c, frag) for g, c, hit, frag in rows if g == "disclaimer→assertion" and hit]
    assert len(wrong) == len(ac.DISCLAIMER_THEN_ASSERTION), wrong   # every one, today
    assert all(hit for g, _, hit, _ in rows if g == "genuine abstention")
    assert not any(hit for g, _, hit, _ in rows if g == "plain answer")


def test_a3_the_consumers_are_the_products_own_telemetry():
    ac = _load("abstention_counter_cases")
    c = ac.consumers()
    assert any(x.startswith("selfcheck.py:") for x in c) and any(x.startswith("__init__.py:") for x in c), c


# ---- amendment 4: the domain ---------------------------------------------------------

def test_a4_inventory_covers_all_of_src_and_states_its_unit():
    inv = _load("decision_site_inventory")
    rows = inv.inventory(); s = inv.summary(rows)
    assert s["modules_scanned"] == len(list((ROOT / "src/veracium").rglob("*.py")))
    assert "scope.py" in s["per_module"] and s["per_module"]["scope.py"]["RETURN_FALSE"] >= 10
    assert s["per_module"]["graph.py"]["RETURN_FALSE"] >= 10 and s["per_module"]["gate.py"]["RETURN_FALSE"] >= 3
    assert s["total"] == len(rows) == sum(s["by_kind"].values())
    assert "identity (module, qualname, line)" in s["unit"]
    ids = {(r["module"], r["qualname"], r["line"], r["kind"]) for r in rows}
    assert len(ids) == len(rows)                       # identity is unique per row


def test_a4_the_five_file_lexical_count_is_not_a_bound_on_the_inventory():
    inv = _load("decision_site_inventory")
    s = inv.summary(inv.inventory())
    five = ("graph.py", "ingest.py", "schema.py", "gate.py", "lifecycle.py")
    outside = sum(c["RAISE"] + c["RETURN_FALSE"] for m, c in s["per_module"].items() if m not in five)
    assert outside > 0, "the domain the spec chose excluded decision sites"


# ---- the row shapes -------------------------------------------------------------------

def test_rows_examples_validate_and_every_mutant_is_refused():
    rs = _load("row_shapes")
    assert all(rs.validate_census_row(r) == [] for r in rs.CENSUS_EXAMPLE)
    assert all(rs.validate_question_row(r) == [] for r in rs.QUESTION_EXAMPLE)
    assert "DISABLED" in rs.CENSUS_STATUS and len(rs.CENSUS_STATUS) == 4
    mutants = [
        ({"id": "x", "status": "UNEXERCISED", "consulted": 3, "fired": 0, "errors": 0}, "UNEXERCISED with consulted != 0"),
        ({"id": "x", "status": "EXERCISED", "consulted": 3, "fired": 0, "errors": 1}, "errors > 0 must be UNMEASURED"),
        ({"id": "x", "status": "DISABLED", "consulted": 0, "fired": 0, "errors": 0}, "DISABLED carries no counts"),
        ({"id": "x", "status": "EXERCISED", "consulted": 3, "fired": 4, "errors": 0}, "fired > consulted"),
        ({"id": "x", "status": "MEASURED", "consulted": 3, "fired": 0, "errors": 0}, "not in"),
    ]
    for row, expected in mutants:
        p = rs.validate_census_row(row); assert any(expected in x for x in p), (row, p)
    q = dict(rs.QUESTION_EXAMPLE[2]); q["observed_outcome"] = "ANSWERED"    # a timeout with a verdict
    assert any("iff" in x for x in rs.validate_question_row(q))
    q = dict(rs.QUESTION_EXAMPLE[0]); q["fixture_class"] = "present"       # outside the closed set
    assert any("not in" in x for x in rs.validate_question_row(q))


def test_rows_rates_name_their_denominators_and_a_timeout_changes_no_completed_rate():
    rs = _load("row_shapes")
    v = rs.rates(rs.QUESTION_EXAMPLE, "veracium")
    assert v["questions"] == 3 and v["completed"] == 2 and v["completion_rate"] == (2, 3)
    assert v["refusal_rate_over_completed"] == (1, 2) and v["not_completed_by_terminal"]["timeout"] == 1
    # INV-4 as it must read: a timeout is its own terminal row; the rate OVER COMPLETED is unchanged
    more = rs.QUESTION_EXAMPLE + [{"question_id": "q020", "arm": "veracium", "fixture_class": "absent",
                                   "terminal": "timeout", "observed_outcome": None, "claimed_reason": "", "support": "none"}]
    assert rs.rates(more, "veracium")["refusal_rate_over_completed"] == (1, 2)
    assert rs.rates(more, "veracium")["completion_rate"] == (2, 4)
    assert rs.rates([], "baseline")["refusal_rate_over_completed"] == "UNDEFINED"


# ---- the scripts run as the package will run them ------------------------------------

@pytest.mark.parametrize("script,args", [("examiner_projection.py", ["--demo"]), ("decision_site_inventory.py", []),
                                         ("abstention_counter_cases.py", []), ("row_shapes.py", [])])
def test_every_evidence_script_runs_and_exits_zero(script, args):
    r = subprocess.run([sys.executable, str(EVIDENCE / script), *args], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
