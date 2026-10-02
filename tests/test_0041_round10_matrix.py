"""specs/0041 round 10 — the GENERATED treatment-coverage matrix (the round-9 verdict's requested artifact, R9-03).

THREE ROUTES, so the matrix can see a carrier that one of them omits (research's stage-1 condition: a matrix generated
from `redaction.py` alone proves only that the code agrees with itself):

  ENUM   specs/evidence/0041/carrier_enumeration.py's triage — the DDL of every table plus every `BaseModel` in
         `veracium.schema`, recursed. It reads neither `redaction.py` nor the spec.
  SPEC   §2d-iii-bis, the per-candidate map — 64 rows, one ruling each.
  TABLE  `redaction.py`'s treatment tables — what the code does.

ENUM == SPEC as SETS of carriers (the spec rules every carrier, and only carriers); SPEC == TABLE per target KIND
as {path: treatment class} (the code treats exactly what the spec rules, in the class it rules). Every TEXT/BLOB
column of every table is accounted for by name. A planted omission in the tables is NAMED by the comparison.

The kind a side table reaches is DERIVED from its DDL (an `*edge_id` column reaches edges; a `survivor_type`
column reaches both kinds), never listed.
"""
import contextlib
import importlib.util
import io
import pathlib
import re

import pytest

from veracium import redaction as R
from veracium.store import schema_version as sv

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "0041-targeted-redaction.md"


def _enumeration():
    spec = importlib.util.spec_from_file_location("ce41_r10", ROOT / "specs" / "evidence" / "0041" / "carrier_enumeration.py")
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
        carriers, _non, unres = mod.triage()
    assert unres == [], f"the enumeration holds UNRESOLVED carriers {unres} — rule them before comparing"
    return mod, {f"{m}.{f}": (paths, where) for m, f, _w, paths, where in carriers}


def _spec_rows():
    text = SPEC.read_text()
    s = text.index("### 2d-iii-bis."); e = text.index("\n### ", s + 10)
    rows = {}
    for line in text[s:e].splitlines():
        if not re.match(r"\| \d+ \|", line):
            continue
        cells = [c.strip() for c in line.split("|")]
        cand = cells[2].strip("`")
        rows[cand] = re.sub(r"\*", "", cells[4])
    return rows


def _spec_class(ruling):
    if ruling.startswith("PRESERVE"):
        return None
    if ruling.startswith("REPLACE (per entry)"):
        return "MARKERS"
    if ruling.startswith("REPLACE"):
        return "REPLACE"
    if ruling.startswith("CLEAR"):
        return "CLEAR"
    if "PRESERVE `None`" in ruling:
        return "REASON3"
    if "RECOGNISED" in ruling:
        return "KIND2"
    raise AssertionError(f"a ruling this matrix cannot classify: {ruling[:80]!r} — teach it, never default it")


def _tables():
    return {t.name: t for t in sv.latest_schema()[1] if t.kind == "table"} if hasattr(sv, "latest_schema") else None


def _ddl(mod):
    _ver, objs = mod.latest_schema()
    return {o.name: [(n, t) for n, t in mod.ddl_columns(o)] for o in objs if o.kind == "table"}


def _kinds_of_table(cols):
    names = {n for n, _t in cols}
    if "survivor_type" in names:
        return {"edge", "episode"}
    if any(n == "edge_id" or n.endswith("_edge_id") for n in names):
        return {"edge"}
    if "episode_id" in names:
        return {"episode"}
    return set()


def spec_route():
    """{kind: {path: class}} from the SPEC rulings, each candidate placed by ENUM's own location for it."""
    mod, carriers = _enumeration()
    ddl = _ddl(mod)
    out = {"edge": {}, "episode": {}}
    for cand, ruling in _spec_rows().items():
        cls = _spec_class(ruling)
        if cls is None:
            continue
        paths, where = carriers[cand]
        m = re.search(r"-> (\w+)", where)
        if m:                                                    # a carrier that IS (a column of) a side table
            table, field = m.group(1), cand.split(".", 1)[1]
            assert field in {n for n, _t in ddl[table]}, f"{cand} is ruled onto {table} but the DDL has no {field}"
            for kind in _kinds_of_table(ddl[table]):
                out[kind][f"{table}.{field}"] = cls
            continue
        homes = [p for p in paths if p.split(".", 1)[0] in ("Edge", "Episode")]
        assert homes, f"{cand} reaches disk in a json blob but no path from Edge/Episode reaches it: {paths}"
        for p in homes:
            top, rel = p.split(".", 1)
            out[top.lower()][rel] = cls
    return out


def table_route(tables=None):
    """{kind: {path: class}} from `redaction.py` — the model carriers only (the DDL-only derived oracle, the embedding
    row, is accounted by the DDL test below)."""
    t = tables or R
    out = {"edge": {}, "episode": {}}
    for p in t.EDGE_REPLACE: out["edge"][p] = "REPLACE"
    for p in t.EDGE_CLEAR: out["edge"][p] = "CLEAR"
    for p in t.EDGE_REASON_THREE_CASE: out["edge"][p] = "REASON3"
    for p in t.EDGE_MARKERS_PER_ENTRY: out["edge"][p] = "MARKERS"
    for p in t.EPISODE_REPLACE: out["episode"][p] = "REPLACE"
    for p in t.EPISODE_KIND_TWO_BRANCH: out["episode"][p] = "KIND2"
    for p in t.EPISODE_REASON_THREE_CASE: out["episode"][p] = "REASON3"
    for kind, entries in t.SIDE_TABLE_TREATMENTS.items():
        for p, how in entries:
            if how == t.DELETE:
                continue
            out[kind][p] = how
    return out


def _diff(a, b):
    return {k: (sorted(set(a[k].items()) - set(b[k].items())), sorted(set(b[k].items()) - set(a[k].items())))
            for k in a if a[k] != b[k]}


# ------------------------------------------------------------------------------------------------ the comparisons
def test_the_enumeration_and_the_spec_rule_exactly_the_same_carriers():
    _mod, carriers = _enumeration()
    spec = set(_spec_rows())
    assert set(carriers) == spec, (sorted(set(carriers) - spec), sorted(spec - set(carriers)))
    assert len(spec) == 64


def test_the_spec_and_the_code_agree_per_kind_on_every_treated_path_and_its_class():
    assert _diff(spec_route(), table_route()) == {}


class _Tables:
    def __init__(self, **over):
        for k in ("EDGE_REPLACE", "EDGE_CLEAR", "EDGE_REASON_THREE_CASE", "EDGE_MARKERS_PER_ENTRY", "EPISODE_REPLACE",
                  "EPISODE_KIND_TWO_BRANCH", "EPISODE_REASON_THREE_CASE", "SIDE_TABLE_TREATMENTS", "DELETE"):
            setattr(self, k, over.get(k, getattr(R, k)))


@pytest.mark.parametrize("planted, kind, named", [
    (dict(EDGE_REPLACE=tuple(p for p in R.EDGE_REPLACE if p != "note")), "edge", "note"),
    (dict(SIDE_TABLE_TREATMENTS={**R.SIDE_TABLE_TREATMENTS, "episode": ()}), "episode",
     "contribution_ledger.identity_digest"),                       # the round-9 state: the reviewer's instance
    (dict(EPISODE_REASON_THREE_CASE=()), "episode", "retired_reason"),
])
def test_a_planted_omission_in_the_tables_is_named_by_the_comparison(planted, kind, named):
    d = _diff(spec_route(), table_route(_Tables(**planted)))
    assert kind in d and any(p == named for p, _c in d[kind][0]), d


def test_a_planted_extra_treatment_is_named_too():
    extra = _Tables(EPISODE_REPLACE=R.EPISODE_REPLACE + ("date",))
    d = _diff(spec_route(), table_route(extra))
    assert "episode" in d and ("date", "REPLACE") in d["episode"][1], d


# ------------------------------------------------------------------------------------------------ the DDL, by name
# Every TEXT/BLOB column of every table, accounted for. A carrier column is placed by ENUM/SPEC above; everything
# else needs a reason HERE. A new column fails until it is classified.
DDL_ACCOUNT = {
    "json-blob (the model carriers above)": {"edges.json", "episodes.json"},
    "INV-2: duplicates a json field, treated with it": {"edges.subject", "edges.relation", "edges.object"},
    "§4c journal state, tombstoned by every redaction": {"edge_event.state", "episode_event.state"},
    "INV-7 derived oracle, DELETED with the edge": {"edge_embedding.vec", "edge_embedding.content_digest"},
    "identifier / reference / clock / closed set": {
        "confirmations.id", "confirmations.user_id", "confirmations.edge_id", "confirmations.confirmed_at",
        "confirmations.actor", "confirmations.call_path", "confirmations.correlation_id",
        "consolidation_ops.operation_id", "consolidation_ops.user_id", "consolidation_ops.state",
        "consolidation_ops.owner", "consolidation_ops.lease_expires_at", "consolidation_ops.claimed_ids",
        "contribution_ledger.id", "contribution_ledger.user_id", "contribution_ledger.survivor_type",
        "contribution_ledger.survivor_id", "contribution_ledger.site", "contribution_ledger.op_key",
        "contribution_ledger.created_at", "contribution_ledger.contributor_type", "contribution_ledger.contributor_ref",
        "edge_embedding.edge_id", "edge_embedding.user_id", "edge_embedding.embedder_id", "edge_embedding.built_at",
        "edge_event.user_id", "edge_event.edge_id", "edge_event.kind", "edge_event.recorded_at",
        "edges.id", "edges.user_id", "episode_event.user_id", "episode_event.episode_id", "episode_event.kind",
        "episode_event.recorded_at", "episodes.id", "episodes.user_id", "episodes.date",
        "policy_receipt.user_id", "policy_receipt.recall_id", "policy_receipt.policy_id",
        "policy_receipt.policy_version", "policy_receipt.recorded_at",
        "redactions.id", "redactions.user_id", "redactions.target_kind", "redactions.target_id",
        "redactions.event_ref", "redactions.recorded_at",
        "source_revocations.user_id", "source_revocations.identity_digest", "source_revocations.action",
        "source_revocations.at", "store_epoch.started_at", "store_identity.origin",
        "supersession_operations.user_id", "supersession_operations.operation_id", "supersession_operations.status",
        "supersession_operations.request_digest_domain",
        "supersession_refusals.refusal_id", "supersession_refusals.user_id", "supersession_refusals.prior_edge_id",
        "supersession_refusals.incoming_edge_id", "supersession_refusals.rule_version",
        "supersession_refusals.created_at", "wiki.user_id", "write_counter.user_id",
    },
    "D1 reason vocabulary (closed per field; §11.2)": {"edge_event.reason", "episode_event.reason", "redactions.reason"},
    "§11.2 carrier, prose replaced at redaction — R9-02(d), OWED in this batch": {"source_revocations.reason"},
    "attestation field names — the kind's carrier paths, refused otherwise at the parser AND the commit (R9-08)":
        {"redactions.fields"},
    "a witnessed notice's foreign body: carrier-path NAMES, D1 vocabulary, versions, a time (R9-04/R9-05)":
        {"redactions.source_body"},
    "§4f domains: no exact tier, named in every receipt": {
        "supersession_operations.logical_request_digest", "supersession_operations.request_digest",
        "supersession_operations.response", "policy_receipt.receipt"},
    "a derivation of content, DROPPED by every redaction": {"wiki.text"},
    "content-free by a CLOSED key schema of scalars (0014 §4a A5: `validate_payload` refuses unknown keys and "
    "non-scalars at every writer)": {"contribution_ledger.payload"},
}


def test_every_text_or_blob_column_of_every_table_is_accounted_for_by_name():
    mod, _c = _enumeration()
    ddl = _ddl(mod)
    columns = {f"{t}.{n}" for t, cols in ddl.items() for n, ty in cols if ty.upper().startswith(("TEXT", "BLOB"))}
    side_paths = {p for entries in R.SIDE_TABLE_TREATMENTS.values() for p, _h in entries if "." in p}
    placed = side_paths | set().union(*DDL_ACCOUNT.values())
    seen = [c for group in DDL_ACCOUNT.values() for c in group]
    assert len(seen) == len(set(seen)), "a column is accounted twice"
    assert columns - placed == set(), f"UNACCOUNTED columns (classify each, with its reason): {sorted(columns - placed)}"
    assert placed - columns == set(), f"accounted columns the DDL no longer has: {sorted(placed - columns)}"


def test_the_ddl_derives_which_kinds_each_treated_side_table_reaches():
    mod, _c = _enumeration()
    ddl = _ddl(mod)
    reach = {t: _kinds_of_table(ddl[t]) for t in ("confirmations", "contribution_ledger", "supersession_refusals",
                                                    "edge_embedding")}
    assert reach == {"confirmations": {"edge"}, "contribution_ledger": {"edge", "episode"},
                     "supersession_refusals": {"edge"}, "edge_embedding": {"edge"}}


# ------------------------------------------------------------------------------------------------ the execution half
# One cell per treated (kind, path) — the TABLE route's paths plus its DELETE entries — each built through the REAL
# path that populates that carrier, redacted through the real `Memory.redact`, and checked against the class the
# spec rules. The builder set must equal the table's path set: a treated path with no cell refuses.
import json as _json                                                         # noqa: E402
import sys                                                                   # noqa: E402
from datetime import datetime, timedelta, timezone                           # noqa: E402

from veracium import Memory, agreement as _agreement, graph as _graph        # noqa: E402
from veracium.config import MemoryConfig                                     # noqa: E402
from veracium.lifecycle import consolidate                                   # noqa: E402
from veracium.schema import (DEFAULT_RELATIONS, Disclosure, Edge, Episode,   # noqa: E402
                             EvidenceAuthor, Provenance)

_tt_spec = importlib.util.spec_from_file_location("tt41_r10m", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_tt_spec)
sys.modules["tt41_r10m"] = tt
_tt_spec.loader.exec_module(tt)

U = "u"
SECRET = "SECRET-MATRIX-4471"


def _prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw)
    return Provenance(**base)


def _ej(st, eid):
    return _json.loads(st._conn.execute("SELECT json FROM edges WHERE id=?", (eid,)).fetchone()[0])


def _pj(st, eid):
    return _json.loads(st._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()[0])


class _Emb:
    def id(self):
        return "rec@1"

    def dim(self):
        return 3

    def __call__(self, texts):
        return [[1.0, float(len(x)), 0.5] for x in texts]


def _mem(tmp_path, embed=None):
    return Memory(llm=tt._quiet, embed=embed, config=MemoryConfig(
        db_path=str(tmp_path / "mx.db"), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))


def _rich_edge(st, eid="e-1"):
    st.add_edge(Edge(id=eid, user_id=U, subject="user " + SECRET, relation="lives_in", object="Berlin " + SECRET,
                     note="my sister said " + SECRET, original_relation="resides " + SECRET,
                     outcome_counts={"confirmed": 2},
                     agreement=_agreement.derive_record("my sister said he moved", "Berlin", Disclosure.USE_ONLY,
                                                        relation="lives_in"),
                     provenance=_prov(disclosure=Disclosure.USE_ONLY)))


# each builder: (tmp_path) -> (memory, target kind, target id, before(st) , after(st, receipt) -> None)
def _edge_json_field(field, expect):
    def build(tmp_path):
        m = _mem(tmp_path); _rich_edge(m.store)
        def check(st, r):
            got = _ej(st, "e-1")[field.split(".")[0]]
            if "." in field:
                got = got[field.split(".", 1)[1]]
            expect(got)
            assert field in r.fields_cleared
        return m, "edge", "e-1", check
    return build


def _is_marker(v):
    assert v == R.MARKER, v


def _dup_column_too(col):
    def build(tmp_path):
        m, kind, tid, check = _edge_json_field(col, _is_marker)(tmp_path)
        def both(st, r):
            check(st, r)
            assert st._conn.execute(f"SELECT {col} FROM edges WHERE id='e-1'").fetchone()[0] == R.MARKER  # INV-2
        return m, kind, tid, both
    return build


def _edge_reason_three_cases(tmp_path):
    m = _mem(tmp_path)
    m.store.add_edge(Edge(id="e-none", user_id=U, subject="user", relation="pet", object="a cat", provenance=_prov()))
    m.store.add_edge(Edge(id="e-reg", user_id=U, subject="user", relation="pet", object="a dog", provenance=_prov()))
    m.dispute(U, "e-reg")                                         # a REGISTERED reason, by the real writer
    m.store.add_edge(Edge(id="e-prose", user_id=U, subject="user", relation="pet", object="a rat", provenance=_prov()))
    # the PROSE case is a legacy row's bytes (no writer can produce it once §11.2 closes the field): the stored
    # json is planted as the pre-closure state; the operation under test, `redact`, is the real one
    row = _ej(m.store, "e-prose"); row["invalidated_at"] = "2026-09-01T00:00:00Z"; row["invalidation_reason"] = SECRET
    m.store._conn.execute("UPDATE edges SET json=? WHERE id='e-prose'", (_json.dumps(row),)); m.store._conn.commit()
    def check(st, _r):
        for eid in ("e-none", "e-reg"):
            m.redact(U, edge_id=eid, reason="subject_request")
        assert _ej(st, "e-none").get("invalidation_reason") is None             # absence stays absence
        assert _ej(st, "e-reg")["invalidation_reason"] == "disputed"            # a registered value is preserved
        assert _ej(st, "e-prose")["invalidation_reason"] == R.REDACTED_REASON_VALUE  # prose is replaced
    return m, "edge", "e-prose", check


def _markers(tmp_path):
    m = _mem(tmp_path); _rich_edge(m.store)
    n = len(_ej(m.store, "e-1")["agreement"]["markers"])
    def check(st, r):
        assert _ej(st, "e-1")["agreement"]["markers"] == [R.MARKER] * n and n >= 1
        assert "agreement.markers" in r.fields_cleared
    return m, "edge", "e-1", check


def _outcome_counts(tmp_path):
    def expect(v):
        assert v == {}, v
    return _edge_json_field("outcome_counts", expect)(tmp_path)


def _confirmation(tmp_path):
    m = _mem(tmp_path)
    m.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="lives_in", object="Berlin " + SECRET,
                          provenance=_prov()))
    m.confirm(U, "e-1")                                           # the real writer of the confirmations row
    assert m.store._conn.execute("SELECT COUNT(*) FROM confirmations WHERE edge_id='e-1'").fetchone()[0] == 1
    def check(st, r):
        assert st._conn.execute("SELECT request_digest FROM confirmations WHERE edge_id='e-1'").fetchone()[0] == R.MARKER
        assert "confirmations.request_digest" in r.fields_cleared
    return m, "edge", "e-1", check


def _refusal(tmp_path):
    m = _mem(tmp_path)
    m.store.add_edge(Edge(id="e-1", user_id=U, subject="user's sister", relation="lives_in", object="Berlin",
                          provenance=_prov()))
    with pytest.raises(_graph.CorrectionRefused):
        m.correct(U, "e-1", "Paris")                              # the real path that records a refusal row
    assert m.store._conn.execute("SELECT COUNT(*) FROM supersession_refusals WHERE prior_edge_id='e-1'").fetchone()[0] == 1
    def check(st, r):
        assert st._conn.execute("SELECT relation FROM supersession_refusals WHERE prior_edge_id='e-1'").fetchone()[0] == R.MARKER
        assert "supersession_refusals.relation" in r.fields_cleared
    return m, "edge", "e-1", check


def _absorption_ledger(tmp_path):
    """A NATIVE absorption (an equal restatement absorbs its prior): the ledger row's survivor is the incoming edge,
    its contributor the prior. Redacting the SURVIVOR clears the row's digests; the mirror cell below proves a
    same-id episode's row is untouched."""
    m = _mem(tmp_path)
    # absorption needs a MORE SPECIFIC restatement in the SAME scope (graph.py, T1 + 0021 §4c): one source
    m.store.add_edge(Edge(id="e-prior", user_id=U, subject="user", relation="lives_in", object="Berlin",
                          provenance=_prov(source_id="src-a", evidence_ref="ev-a")))
    _graph.apply_supersession(m.store, Edge(id="e-1", user_id=U, subject="user", relation="lives_in",
                                            object="Berlin Mitte", provenance=_prov(source_id="src-a", evidence_ref="ev-b")),
                              DEFAULT_RELATIONS)
    rows = m.store._conn.execute("SELECT identity_digest, evidence_ref_digest FROM contribution_ledger "
                                 "WHERE survivor_type='edge' AND survivor_id='e-1'").fetchall()
    assert rows and all(a and b for a, b in rows), rows
    def check(st, r):
        after = st._conn.execute("SELECT identity_digest, evidence_ref_digest FROM contribution_ledger "
                                 "WHERE survivor_type='edge' AND survivor_id='e-1'").fetchall()
        assert after and all(x == (None, None) for x in after)
        assert {"contribution_ledger.identity_digest", "contribution_ledger.evidence_ref_digest"} <= set(r.fields_cleared)
    return m, "edge", "e-1", check


def _embedding(tmp_path):
    m = _mem(tmp_path, embed=_Emb())
    m.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="lives_in", object="Berlin", provenance=_prov()))
    assert m.embed_backfill(U) == 1
    def check(st, r):
        assert st._conn.execute("SELECT COUNT(*) FROM edge_embedding WHERE edge_id='e-1'").fetchone()[0] == 0
        assert "edge_embedding" in r.fields_cleared
    return m, "edge", "e-1", check


def _consolidated(m, n=8):
    for i in range(n):
        m.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                    provenance=_prov(source_id="src-one", evidence_ref=f"ev-{i}")))   # ONE source: one scope pool
    consolidate(m.store, lambda p, system=None, role=None: _json.dumps(
        {"records": [{"date": "2026-01-01", "summary": "the week " + SECRET}]}), U, m.config,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    (out,) = [e for e in m.store.episodes(U) if e.lineage]
    return out.id


def _episode_ledger(tmp_path):
    m = _mem(tmp_path)
    oid = _consolidated(m)
    q = "SELECT identity_digest, evidence_ref_digest FROM contribution_ledger WHERE survivor_type='episode' AND survivor_id=?"
    before = m.store._conn.execute(q, (oid,)).fetchall()
    assert len(before) == 8 and all(a and b for a, b in before), before
    def check(st, r):
        assert all(x == (None, None) for x in st._conn.execute(q, (oid,)).fetchall())
        assert {"contribution_ledger.identity_digest", "contribution_ledger.evidence_ref_digest"} <= set(r.fields_cleared)
    return m, "episode", oid, check


def _episode_summary(tmp_path):
    m = _mem(tmp_path)
    m.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-09-01", summary=SECRET, provenance=_prov()))
    def check(st, r):
        assert _pj(st, "ep-1")["summary"] == R.MARKER and "summary" in r.fields_cleared
    return m, "episode", "ep-1", check


def _frozen(tmp_path, shape):
    m = tt._frozen_memory(tmp_path)
    return m, tt._frozen_rows()[shape]


def _episode_kind(tmp_path):
    m, prose = _frozen(tmp_path, "prose_kind")
    active = tt._frozen_rows()["active_episode_absent_reason"]
    recognised = _pj(m.store, active)["kind"]
    def check(st, _r):
        m.redact(U, episode_id=active, reason="subject_request")
        assert _pj(st, active)["kind"] == recognised                          # a recognised kind is preserved
        assert _pj(st, prose)["kind"] == R.MARKER                             # a prose kind is replaced
    return m, "episode", prose, check


def _episode_reason(tmp_path):
    m, prose = _frozen(tmp_path, "prose_retired_reason")
    rows = tt._frozen_rows(); reg, none = rows["registry_retired_reason"], rows["active_episode_absent_reason"]
    registered = _pj(m.store, reg)["retired_reason"]
    def check(st, _r):
        for eid in (reg, none):
            m.redact(U, episode_id=eid, reason="subject_request")
        assert _pj(st, none).get("retired_reason") is None                    # absence stays absence (active)
        assert _pj(st, reg)["retired_reason"] == registered                   # a registered value is preserved
        assert _pj(st, prose)["retired_reason"] == R.REDACTED_REASON_VALUE    # prose is replaced
    return m, "episode", prose, check


CELLS = {
    ("edge", "subject"): _dup_column_too("subject"),
    ("edge", "relation"): _dup_column_too("relation"),
    ("edge", "object"): _dup_column_too("object"),
    ("edge", "note"): _edge_json_field("note", _is_marker),
    ("edge", "original_relation"): _edge_json_field("original_relation", _is_marker),
    ("edge", "outcome_counts"): _outcome_counts,
    ("edge", "invalidation_reason"): _edge_reason_three_cases,
    ("edge", "agreement.markers"): _markers,
    ("edge", "confirmations.request_digest"): _confirmation,
    ("edge", "supersession_refusals.relation"): _refusal,
    ("edge", "contribution_ledger.identity_digest"): _absorption_ledger,
    ("edge", "contribution_ledger.evidence_ref_digest"): _absorption_ledger,
    ("edge", "edge_embedding"): _embedding,
    ("episode", "summary"): _episode_summary,
    ("episode", "kind"): _episode_kind,
    ("episode", "retired_reason"): _episode_reason,
    ("episode", "contribution_ledger.identity_digest"): _episode_ledger,
    ("episode", "contribution_ledger.evidence_ref_digest"): _episode_ledger,
}


def test_every_treated_path_has_exactly_one_execution_cell():
    paths = {(k, p) for k, d in table_route().items() for p in d}
    paths |= {(k, p) for k, entries in R.SIDE_TABLE_TREATMENTS.items() for p, h in entries if h == R.DELETE}
    assert set(CELLS) == paths, (sorted(paths - set(CELLS)), sorted(set(CELLS) - paths))


@pytest.mark.parametrize("cell", sorted(CELLS), ids=lambda c: f"{c[0]}:{c[1]}")
def test_the_real_redaction_treats_the_carrier_as_the_map_rules(cell, tmp_path):
    m, kind, tid, check = CELLS[cell](tmp_path)
    r = m.redact(U, **{f"{kind}_id": tid}, reason="subject_request")
    check(m.store, r)


def test_the_mirror_redacting_an_edge_leaves_a_same_id_episode_ledger_intact(tmp_path):
    m = _mem(tmp_path)
    oid = _consolidated(m)
    m.store.add_edge(Edge(id=oid, user_id=U, subject="user", relation="pet", object="an unrelated cat",
                          provenance=_prov()))                   # an EDGE sharing the episode's raw id
    q = "SELECT identity_digest, evidence_ref_digest FROM contribution_ledger WHERE survivor_type='episode' AND survivor_id=?"
    before = m.store._conn.execute(q, (oid,)).fetchall()
    m.redact(U, edge_id=oid, reason="subject_request")
    assert m.store._conn.execute(q, (oid,)).fetchall() == before and all(a and b for a, b in before)
    assert not m.store._attested_fields(U, "episode", oid)


def test_the_contributor_column_domain_is_edge_or_null_so_an_episode_is_never_a_recorded_contributor(tmp_path):
    m = _mem(tmp_path)
    _consolidated(m)
    m.store.add_edge(Edge(id="e-prior", user_id=U, subject="user", relation="lives_in", object="Berlin",
                          provenance=_prov(source_id="src-a")))
    _graph.apply_supersession(m.store, Edge(id="e-1", user_id=U, subject="user", relation="lives_in",
                                            object="Berlin Mitte", provenance=_prov(source_id="src-a")), DEFAULT_RELATIONS)
    kinds = {r[0] for r in m.store._conn.execute("SELECT DISTINCT contributor_type FROM contribution_ledger")}
    assert kinds == {"edge", None}, kinds                        # both native writers ran; neither names an episode


def test_a_consumed_consolidation_input_cannot_be_redacted(tmp_path):
    m = _mem(tmp_path)
    _consolidated(m)
    with pytest.raises(ValueError, match="no episode"):
        m.redact(U, episode_id="ep-3", reason="subject_request")


def test_the_receipt_names_a_restored_output_whose_lineage_consumed_the_redacted_episode(tmp_path):
    """Found in the R9-03 fix: `_surviving_derived` compared the RAW id against lineage, which carries the HISTORICAL
    form (X19), so it never matched. Reachable when a store holds an input live beside an output that consumed it
    elsewhere — restore an export taken before a consolidation, then one taken after."""
    from veracium.portability import export_memory, import_memory
    src = Memory(llm=tt._quiet, config=MemoryConfig(db_path=str(tmp_path / "src.db"), wiki_recompile_after_writes=0,
                                                   scope_groups={}, require_source_id=False))
    for i in range(8):
        src.store.add_episode(Episode(id=f"ep-{i}", user_id=U, date=f"2026-01-{i + 1:02d}", summary=f"day {i}",
                                      provenance=_prov()))
    export_memory(src.store, U, tmp_path / "before.jsonl")
    consolidate(src.store, lambda p, system=None, role=None: _json.dumps(
        {"records": [{"date": "2026-01-01", "summary": "week"}]}), U, src.config,
        now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    export_memory(src.store, U, tmp_path / "after.jsonl")
    dst = _mem(tmp_path)
    import_memory(dst.store, tmp_path / "before.jsonl", restore=True)
    import_memory(dst.store, tmp_path / "after.jsonl", restore=True)
    (out,) = [e for e in dst.store.episodes(U) if e.lineage]
    r = dst.redact(U, episode_id="ep-3", reason="subject_request")
    assert [d["id"] for d in r.surviving_derived] == [out.id] and r.surviving_derived[0]["via"] == "lineage"


def test_an_imported_absorption_ledger_is_treated_under_its_minted_id(tmp_path):
    """Research's note: a cross-user import MINTS ids (imp-…); the cell must read the minted survivor, not the source's."""
    from veracium.portability import export_memory, import_memory
    src = _mem(tmp_path)
    src.store.add_edge(Edge(id="e-prior", user_id=U, subject="user", relation="lives_in", object="Berlin",
                            provenance=_prov(source_id="src-a", evidence_ref="ev-a")))
    _graph.apply_supersession(src.store, Edge(id="e-1", user_id=U, subject="user", relation="lives_in",
                                              object="Berlin Mitte", provenance=_prov(source_id="src-a", evidence_ref="ev-b")),
                              DEFAULT_RELATIONS)
    export_memory(src.store, U, tmp_path / "x.jsonl")
    dst = Memory(llm=tt._quiet, config=MemoryConfig(db_path=str(tmp_path / "dst.db"), wiki_recompile_after_writes=0,
                                                   scope_groups={}, require_source_id=False))
    import_memory(dst.store, tmp_path / "x.jsonl", user_id="v")
    rows = dst.store._conn.execute("SELECT survivor_id, identity_digest, evidence_ref_digest FROM contribution_ledger "
                                   "WHERE user_id='v' AND survivor_type='edge'").fetchall()
    assert rows and all(sid.startswith("imp-") for sid, _a, _b in rows), rows
    assert all(a and b for _sid, a, b in rows), "the imported rows must carry digests, or clearing them proves nothing"
    sid = rows[0][0]
    dst.redact("v", edge_id=sid, reason="subject_request")
    after = dst.store._conn.execute("SELECT identity_digest, evidence_ref_digest FROM contribution_ledger "
                                    "WHERE user_id='v' AND survivor_type='edge' AND survivor_id=?", (sid,)).fetchall()
    assert after and all(x == (None, None) for x in after)
