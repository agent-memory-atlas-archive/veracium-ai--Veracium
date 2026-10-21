"""T12, the generated writer/lifetime matrix (V44 L102; 0044 §4f-ii, INV-A22's product half): the committed matrix is
what a fresh RUN of the writers produces, and the generator refuses each defect it exists to catch (P1's matrix for
`specs/evidence/0044/writer_lifetime_matrix.py`). Build note b2870871 D1 with addendum 1's M4 and P5.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "specs" / "evidence" / "0044" / "writer_lifetime_matrix.py"


def _gen():
    name = "writer_lifetime_matrix_0044"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, GEN)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


@pytest.fixture(scope="module")
def matrix():
    return _gen().generate()


def test_the_committed_matrix_is_what_running_the_writers_produces(matrix):
    """Data to data (CLAUDE.md item 9): writer_lifetime_matrix.json and .md equal a fresh run's rendering, and the
    fresh run raises none of the generator's refusals. A new ruling key, a changed writer or a new input moves the run,
    and this cell names the regeneration."""
    import json
    g = _gen()
    assert g.problems(matrix) == []
    assert json.dumps(matrix, indent=1, sort_keys=True) + "\n" == g.OUT_JSON.read_text(), "regenerate with --write"
    assert g.render(matrix) == g.OUT_MD.read_text(), "regenerate with --write"


def test_every_ruling_key_is_in_the_matrix_and_every_cell_is_observed_or_reasoned(matrix):
    """INV-A22's product half, at the transition grain: every `EDGE_WRITE_SITE_RULINGS` key — the store's generated
    write-site census — has a row, with a `lifetime` disposition, and every (writer × transition) cell is OBSERVED by a
    run or carries a stated reason; the writers' characteristic transitions are observed (§4f-ii's table, by writer)."""
    from veracium.store.sqlite import EDGE_WRITE_SITE_RULINGS
    assert set(matrix["ruling_keys"]) == set(EDGE_WRITE_SITE_RULINGS)
    obs = {c for c, v in matrix["cells"].items() if v["state"] == "observed"}
    for cell in ("_upsert_edge_row|insert", "_upsert_edge_row|reinstatement", "_upsert_edge_row|retirement",
                 "_upsert_edge_row|re-retirement", "_upsert_edge_row|none", "_invalidate_edge_row|retirement",
                 "_reinstate_edge_row|reinstatement", "_redact_in_txn|redaction", "confirm_edge|none",
                 "_recompute_edge_row|none", "commit_outcome_import_plan|insert", "forget_user|erasure"):
        assert cell in obs, cell
    # M4(b): the imported attested redaction is recorded with its chain, outer → inner
    chains = {tuple(c["chain"]) for r in matrix["runs"] for c in r["calls"]}
    assert ("commit_outcome_import_plan", "_redact_in_txn") in chains
    # M4(a): every driven input ends in exactly one of the three endings
    assert {r["ending"].split(":")[0] for r in matrix["runs"]} <= {"accepted", "refused", "no-hook-call"}


def test_the_generator_refuses_each_planted_defect(matrix, monkeypatch):
    """P1's matrix for writer_lifetime_matrix.py: each refusal fires on a planted defect, and its control does not —
    a reason given for an OBSERVED cell (a stale reason); a not-observed cell with NO reason; a ruling key without a
    `lifetime` disposition; a missing cell; a run caller the AST list lacks; a lifetime hook call that passes through
    NO ruling key (M4(c), raised during the run)."""
    import copy
    g = _gen()
    assert g.problems(matrix) == []
    m = copy.deepcopy(matrix)
    monkeypatch.setitem(g.REASONS, ("_upsert_edge_row", "insert"), "planted")
    assert any("is observed, but REASONS says" in x for x in g.problems(m))
    monkeypatch.delitem(g.REASONS, ("_upsert_edge_row", "insert"))
    m = copy.deepcopy(matrix)
    m["cells"]["confirm_edge|retirement"]["reason"] = None
    assert any("neither observed nor given a reason" in x for x in g.problems(m))
    m = copy.deepcopy(matrix)
    m["ruling_keys"]["confirm_edge"] = None
    assert any("carries no lifetime disposition" in x for x in g.problems(m))
    m = copy.deepcopy(matrix)
    del m["cells"]["forget_user|erasure"]
    assert any("has no cell for 'erasure'" in x for x in g.problems(m))
    m = copy.deepcopy(matrix)
    m["callers"]["run"]["confirm_edge"] = ["planted.py:nowhere"]
    assert any("is not in the AST caller list" in x for x in g.problems(m))
    # M4(c): a hook call from outside every ruling key — the generator refuses the RUN
    from veracium.store.sqlite import SqliteStore

    def stray(p):
        s = SqliteStore(p)
        try:
            with s._write_txn():
                s._apply_lifetime_transition("u", "e", None, "{}")
        finally:
            s.close()
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = str(pathlib.Path(d) / "x.db")
        SqliteStore(p).close()
        with pytest.raises(g.GeneratorRefused, match="passed through no ruling key"):
            g._record_run(stray, p, g._ruling_keys())
