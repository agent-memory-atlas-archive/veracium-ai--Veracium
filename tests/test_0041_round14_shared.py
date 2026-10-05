"""specs/0041 round 14 — N13-01: a supersession-refusal row shared by its two edges is attested for the SECOND edge's
redaction too.

The row links two edges (prior_edge_id, incoming_edge_id) and the treatment matches either end, but it reported only
rows its UPDATE changed: the first edge's redaction marked the shared row and named it; the second's found it already
at the marker and omitted it. A row linked to the edge at either end and already at the marker is now attested, as the
shared revocation row is (N12-02). The refusal row is recorded by the real path (`Memory.correct` refused), the incoming
edge persisted through the ordinary writer; SQL is read-only.
"""
import importlib.util
import pathlib
import sys

import pytest

from veracium import graph as _graph
from veracium import redaction as R
from veracium.schema import Edge

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r14s", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r14s"] = tt
_spec.loader.exec_module(tt)

U = "u"
PATH = "supersession_refusals.relation"


def _refusal_pair(tmp_path):
    m = tt._mem(tmp_path, "m.db")
    m.store.add_edge(Edge(id="e-1", user_id=U, subject="user's sister", relation="lives_in", object="Berlin", provenance=tt._prov()))
    with pytest.raises(_graph.CorrectionRefused):
        m.correct(U, "e-1", "Paris")                          # the real path that records a refusal row
    prior, incoming = m.store._conn.execute("SELECT prior_edge_id, incoming_edge_id FROM supersession_refusals").fetchone()
    if not m.store._conn.execute("SELECT 1 FROM edges WHERE id=?", (incoming,)).fetchone():
        m.store.add_edge(Edge(id=incoming, user_id=U, subject="user's sister", relation="lives_in", object="Paris",
                              provenance=tt._prov()))
    return m, prior, incoming


@pytest.mark.parametrize("order", ["prior first", "incoming first"])
def test_N13_01_the_second_edge_attests_the_shared_row_already_at_the_marker(tmp_path, order):
    m, prior, incoming = _refusal_pair(tmp_path)
    first, second = (prior, incoming) if order == "prior first" else (incoming, prior)
    m.redact(U, edge_id=first, reason="subject_request")
    r2 = m.redact(U, edge_id=second, reason="subject_request")
    assert PATH in r2.fields_cleared
    assert m.store._conn.execute("SELECT relation FROM supersession_refusals").fetchone()[0] == R.MARKER


@pytest.mark.parametrize("which", ["prior", "incoming"])
def test_control_a_never_treated_shared_row_is_treated_and_attested_by_this_call(tmp_path, which):
    m, prior, incoming = _refusal_pair(tmp_path)
    r = m.redact(U, edge_id=prior if which == "prior" else incoming, reason="subject_request")
    assert PATH in r.fields_cleared
    assert m.store._conn.execute("SELECT relation FROM supersession_refusals").fetchone()[0] == R.MARKER


def test_control_an_edge_with_no_refusal_row_does_not_name_the_path(tmp_path):
    m = tt._mem(tmp_path, "m.db")
    m.store.add_edge(Edge(id="lone", user_id=U, subject="user", relation="lives_in", object="Berlin", provenance=tt._prov()))
    assert PATH not in m.redact(U, edge_id="lone", reason="subject_request").fields_cleared
