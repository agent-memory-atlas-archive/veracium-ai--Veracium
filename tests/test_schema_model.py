"""Every adversarial counterexample the external reviews have constructed.

(Round counts are generated -- see `specs/STATUS.md`; none is stated here.)

**These were a hand-rolled harness inside the instrument until round 5.** It
printed 30 result rows and reported `28/28`, because its total was a
hand-maintained arithmetic expression — a tool whose whole purpose is truthful
evidence, miscounting its own evidence. Moving them into pytest removes that
class of defect entirely: the count comes from collection.

Each test names the round that built the case, so a regression says which
review would have caught it.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "specs"))

from schema_model import (REBUILDABLE, REQUIRED, SCHEMA_V1, SCHEMA_VERSION,  # noqa: E402
                          SCHEMAS, SchemaObject, create, declared_policies, digest,
                          drift, identity, manifest, registry_conformance,
                          reviewed_policies, resolve)
from veracium.store.sqlite import SqliteStore, _SCHEMA  # noqa: E402


@pytest.fixture(autouse=True)
def _mktemp_under_tmp_path(tmp_path):
    """Every `tempfile` name this module mints lands under the test's own
    `tmp_path`, which pytest removes.

    2026-09-16: `tempfile.mktemp(suffix=".db")` at 3 sites in this file wrote
    into the system temp directory and deleted nothing. Across the suite that was
    413 stray stores per run and 53,230 in /tmp over three days (4 GB), measured
    before the clean-up. The call sites sit inside module helpers as well as
    tests, so redirecting `tempfile` for the module fixes both without changing a
    single signature or assertion — the shape the doctor-CLI test already uses to
    own its own temp root.

    Set and restored DIRECTLY rather than through `monkeypatch`. A test that calls
    `monkeypatch.undo()` mid-body undoes every patch on that fixture, including one
    another fixture installed, so the `monkeypatch.setattr(tempfile, "tempdir", …)`
    version of this redirect was silently lifted for the rest of those tests and
    three stores per run still escaped. Measured across the seven files: 27+ before,
    3 with the monkeypatch form, 0 with this one. Two of the seven call `undo()`
    mid-body — `tests/test_0018_orchestrator.py` (three times inside one test) and
    `tests/test_migrations_0013.py` — so this is a live hazard here, not a
    precaution. Do not simplify it back to `monkeypatch`.
    """
    previous = tempfile.tempdir
    tempfile.tempdir = str(tmp_path)
    try:
        yield
    finally:
        tempfile.tempdir = previous


def _fresh() -> str:
    p = tempfile.mktemp(suffix=".db")
    SqliteStore(p)
    return p


def _objs(path: str) -> dict:
    c = sqlite3.connect(path)
    try:
        return manifest(c)
    finally:
        c.close()


def _mutate(sql, collation=False) -> str:
    p = _fresh()
    c = sqlite3.connect(p)
    if collation:
        c.create_collation("MYCOLL", lambda a, b: (a > b) - (a < b))
    for s in sql:
        c.execute(s)
    c.commit()
    c.close()
    return p


def _variant(old: str, new: str) -> str:
    """One change against the REAL schema text.

    Hand-writing a near-copy is how two of round 2's counterexamples first
    failed to reproduce: the reconstruction differed in some *other* way, so it
    was caught for the wrong reason."""
    text = _SCHEMA.replace(old, new)
    assert text != _SCHEMA, f"variant did not apply: {old!r}"
    p = tempfile.mktemp(suffix=".db")
    c = sqlite3.connect(p)
    c.executescript(text)
    c.commit()
    c.close()
    return p


@pytest.fixture
def clean():
    return digest(_objs(_fresh()))


# --- shapes that must be REFUSED -----------------------------------------

def _stripped() -> str:
    p = tempfile.mktemp(suffix=".db")
    c = sqlite3.connect(p)
    c.executescript(
        "CREATE TABLE edges (id TEXT, user_id TEXT, subject TEXT, relation TEXT,"
        " object TEXT, active INTEGER, quarantined INTEGER, json TEXT);"
        "CREATE TABLE episodes (id TEXT, user_id TEXT, date TEXT, json TEXT);"
        "CREATE TABLE wiki (user_id TEXT, text TEXT, store_version INTEGER);"
        "CREATE TABLE write_counter (user_id TEXT, n INTEGER);")
    c.commit()
    c.close()
    return p


REFUSED = {
    "r1_constraint_stripped_clone": _stripped,
    "r1_generated_column": lambda: _mutate(
        ["ALTER TABLE edges ADD COLUMN leak TEXT "
         "GENERATED ALWAYS AS (subject||object) VIRTUAL"]),
    "r1_unrelated_table": lambda: _mutate(["CREATE TABLE unrelated_application_data (x)"]),
    "r1_trigger_on_a_protected_table": lambda: _mutate(
        ["CREATE TRIGGER t AFTER INSERT ON edges BEGIN UPDATE edges SET active=0; END"]),
    "r2_check_constraint": lambda: _variant(
        "active INTEGER NOT NULL,", "active INTEGER NOT NULL CHECK(active = 0),"),
    "r2_collate_nocase_primary_key": lambda: _variant(
        "id TEXT PRIMARY KEY", "id TEXT COLLATE NOCASE PRIMARY KEY"),
    "r2_extra_view": lambda: _mutate(["CREATE VIEW v AS SELECT * FROM edges"]),
    "r2_host_collation_index": lambda: _mutate(
        ["CREATE INDEX ix_custom ON edges(subject COLLATE MYCOLL)"], collation=True),
    "r3_check_literal_whitespace": lambda: _variant(
        "object TEXT,", "object TEXT CHECK(object <> 'a  b'),"),
    "r3_trigger_named_like_an_index": lambda: _mutate(
        ["CREATE TRIGGER ix_edges_subj_rel AFTER INSERT ON edges "
         "BEGIN UPDATE edges SET active=0 WHERE id=NEW.id; END"]),
}


# --- shapes that must NOT be refused -------------------------------------
# These are the ones to read sceptically. A check that refuses stores which are
# genuinely fine gets bypassed, and a bypassed check is weaker than a narrower
# one that holds.

def test_analyze_does_not_change_the_digest(clean):
    assert digest(_objs(_mutate(["ANALYZE"]))) == clean


def test_a_missing_acceleration_index_is_drift_not_refusal(clean):
    objs = _objs(_mutate(["DROP INDEX ix_edges_subj_rel"]))
    assert digest(objs) == clean
    assert drift(objs) == [("index", "ix_edges_subj_rel")]


def test_a_wrong_same_named_index_is_drift_not_refusal(clean):
    objs = _objs(_mutate(["DROP INDEX ix_edges_subj_rel",
                          "CREATE UNIQUE INDEX ix_edges_subj_rel ON edges(user_id, subject)"]))
    assert digest(objs) == clean
    assert drift(objs) == [("index", "ix_edges_subj_rel")]


def test_a_trigger_named_like_an_index_is_not_mistaken_for_drift(clean):
    """Round 3: v4 reported it AS index drift, which would have sent an
    implementation off to repair an index that was never broken."""
    objs = _objs(REFUSED["r3_trigger_named_like_an_index"]())
    assert digest(objs) != clean
    assert drift(objs) == []


def test_an_in_memory_store_is_inspectable_through_its_own_connection(clean):
    """Round 2: reopening ':memory:' yields a different, empty database."""
    store = SqliteStore(":memory:")
    objs = manifest(store._conn)
    assert digest(objs) == clean and drift(objs) == []


def test_two_literal_variants_are_not_the_same_schema():
    """Round 3: collapsing whitespace rewrote quoted literals, so these two —
    which accept exactly opposite values — shared a digest."""
    two = digest(_objs(_variant("object TEXT,", "object TEXT CHECK(object <> 'a  b'),")))
    one = digest(_objs(_variant("object TEXT,", "object TEXT CHECK(object <> 'a b'),")))
    assert two != one


# --- the registry conforms to the product schema -------------------------

def test_the_registry_reproduces_the_product_schema():
    assert registry_conformance() == []


def test_a_wrong_rebuildable_ddl_fails_conformance(monkeypatch):
    """Round 4: v5 compared the acceptance digest, which excludes exactly these.
    Patched against the CURRENT registry version (`_SCHEMA` tracks it), so a wrong
    rebuildable DDL diverges from the product schema built at import."""
    bad = tuple(o._replace(ddl="CREATE UNIQUE INDEX ix_edges_subj_rel ON edges(user_id)")
                if o.name == "ix_edges_subj_rel" else o for o in SCHEMAS[SCHEMA_VERSION])
    monkeypatch.setitem(SCHEMAS, SCHEMA_VERSION, bad)
    assert len(registry_conformance()) == 1


def test_flipping_only_a_policy_fails_conformance(monkeypatch):
    """Round 5: v6's policy check compared the registry against itself, so this
    passed. A policy decides digest exclusion, drift repair and candidate
    matching — it cannot be self-certifying."""
    flipped = tuple(o._replace(policy=REQUIRED) if o.name == "ix_edges_subj_rel" else o
                    for o in SCHEMAS[SCHEMA_VERSION])
    monkeypatch.setitem(SCHEMAS, SCHEMA_VERSION, flipped)
    problems = registry_conformance()
    assert any("policy" in p for p in problems), problems


def test_the_reviewed_policy_artifact_matches_the_registry():
    assert reviewed_policies(1) == declared_policies(1)


@pytest.fixture
def simulated_v2(monkeypatch):
    """A version 2 with its own required table AND its own rebuildable index —
    the combination that exposed round 4's circular resolution."""
    import schema_evidence as ev
    v2 = SCHEMA_V1 + (
        SchemaObject("table", "sources",
                     "CREATE TABLE sources (id TEXT PRIMARY KEY, label TEXT)", REQUIRED),
        SchemaObject("index", "ix_sources",
                     "CREATE INDEX ix_sources ON sources(id)", REBUILDABLE))
    monkeypatch.setitem(SCHEMAS, 2, v2)
    monkeypatch.setattr(ev, "SCHEMA_VERSION", 2)
    monkeypatch.setattr("schema_model.SCHEMA_VERSION", 2)
    return ev.build_version_artifact(strict=False)["versions"]


def _built(version: int) -> dict:
    c = sqlite3.connect(":memory:")
    create(c, version)
    return manifest(c)


def test_a_v1_store_still_resolves_once_head_is_v2(simulated_v2):
    assert resolve(_built(1), simulated_v2) == 1
    assert resolve(_built(2), simulated_v2) == 2


def test_resolution_does_not_use_a_default_version_digest(simulated_v2):
    """Round 4: the digest excludes objects by the version's policy, so a
    default-version digest of a v2 store resolves to nothing."""
    v2 = _built(2)
    assert digest(v2, 1) != digest(v2, 2)
    assert not any(a["digest"] == digest(v2, 1) for a in simulated_v2["2"]["accepted"])
    assert resolve(v2, simulated_v2) == 2


def test_resolution_is_restricted_to_legacy_base_versions(simulated_v2):
    """Round 5: v6 tried every known version, so an unstamped version-2 shape
    resolved to 2 even though only version 1 was ever a legitimate base."""
    assert resolve(_built(2), simulated_v2, candidates=frozenset({1})) is None
    assert resolve(_built(1), simulated_v2, candidates=frozenset({1})) == 1


def test_an_unknown_shape_resolves_to_nothing(simulated_v2):
    assert resolve({("table", "nope"): {"type": "table", "table": "nope",
                                        "sql": "CREATE TABLE nope (x)",
                                        "columns": []}}, simulated_v2) is None


def test_deleting_a_historical_version_is_an_error(simulated_v2, tmp_path, monkeypatch):
    """Round 5: v6 iterated only the versions currently in SCHEMAS, so dropping
    one silently emitted an artifact without it."""
    import json

    import schema_evidence as ev
    art = tmp_path / "schema_versions.json"
    art.write_text(json.dumps({"manifest_algorithm": ev.sv.MANIFEST_ALGORITHM,
                               "schema_version": 2,
                               "versions": simulated_v2}))
    monkeypatch.setattr(ev.sv, "VERSIONS", art)
    monkeypatch.setitem(SCHEMAS, 2, SCHEMAS[2])
    del SCHEMAS[2]
    try:
        with pytest.raises(SystemExit, match="no longer declares it"):
            ev.build_version_artifact(strict=True)
    finally:
        pass


# --- runtime qualification ------------------------------------------------


def test_missing_legacy_evidence_authorizes_nothing(monkeypatch, tmp_path):
    """Round 6, finding 7: v7 returned {SCHEMA_VERSION}, authorising adoption
    using the very evidence that was missing."""
    import schema_evidence as ev
    monkeypatch.setattr(ev.sv, "RELEASES", tmp_path / "absent.json")
    assert ev.sv.legacy_base_versions() == frozenset()


def test_a_policy_typo_is_a_build_error():
    """Round 7, finding 6: `policy` was an open string, so a typo created a
    third, unchecked behaviour."""
    from schema_model import validate_schema_registry
    bad = SCHEMA_V1 + (SchemaObject("table", "sources",
                                    "CREATE TABLE sources (id TEXT)", "requried"),)
    SCHEMAS[99] = bad
    try:
        problems = validate_schema_registry()
        assert any("policy" in p for p in problems), problems
    finally:
        del SCHEMAS[99]


def test_a_rebuildable_non_index_is_a_build_error():
    from schema_model import validate_schema_registry
    SCHEMAS[99] = (SchemaObject("table", "t", "CREATE TABLE t (a)", REBUILDABLE),)
    try:
        assert any("rebuildable" in p for p in validate_schema_registry())
    finally:
        del SCHEMAS[99]


def test_the_release_result_is_rederived():
    """Round 7, finding 7: the gate inspected the stored value."""
    import schema_evidence as ev
    assert "result" in ev.AUTHORITATIVE


def test_the_strict_table_probe_reports_a_real_bool():
    """Round 7, finding 5: the probe was invalid SQL and recorded False on a
    runtime that supports strict tables.

    Round 12 correction: STRICT support is recorded as identity but NOT
    required, so the test must not assert True — on a runtime without strict
    tables the probe correctly reports False and nothing in `0007` breaks. What
    must hold is that the result is a real bool (`1 == True` in Python made a
    mistyped probe split the canonical identity from dict equality)."""
    import schema_evidence as ev
    assert isinstance(ev.sv.runtime_identity()["features"]["strict_tables"], bool)


def test_the_ddl_probe_asserts_body_preservation():
    """And this one only checked that a row existed."""
    import schema_evidence as ev
    f = ev.sv.runtime_identity()["features"]
    assert f["preserves_ddl_body"] is True and f["xinfo_exposes_generated"] is True


# --- round 8: runtime-record validation ----------------------------------


def test_a_fabricated_manifestation_is_rejected():
    """Round 8, finding 2 — a demonstrated bypass. An added trigger became an
    accepted version-1 shape while the validator returned no problems. (0007 §4g: the legacy runtime record that
    carried manifestations is retired; the rule lives on in manifestation_problems, which the 0013 model's evidence
    validator applies.)"""
    import copy

    import schema_evidence as ev
    objs = copy.deepcopy(ev.sv._constructor_objects(1))
    objs["trigger:evil"] = {
        "type": "trigger", "table": "edges",
        "sql": "CREATE TRIGGER evil AFTER INSERT ON edges BEGIN DELETE FROM edges; END"}
    assert ev.sv.manifestation_problems(objs, 1)


def test_the_capability_validator_is_not_in_the_0007_kernel():
    """Round 8, finding 4: it is a migration destination validator with no
    caller here. `specs/0013` owns it."""
    import schema_model
    assert not hasattr(schema_model, "capability_problems")


# --- round 10: publication and artifact-level checks ----------------------

def _isolate(monkeypatch, tmp_path):
    """Point the evidence artifacts at a scratch directory."""
    import schema_evidence as ev

    monkeypatch.setattr(ev.sv, "RUNTIMES", tmp_path / "sqlite_runtimes.json")
    monkeypatch.setattr(ev.sv, "VERSIONS", tmp_path / "schema_versions.json")
    return ev


def test_the_repository_has_no_stray_staged_artifacts():
    assert not list((ROOT / "specs" / "generated").glob("*.tmp"))


# --- round 11 ------------------------------------------------------------


def test_schema_version_must_match_the_registry():
    """Round 11, finding 3 — a regression from the scope cut. The guard lived in
    the deleted migrations module, and the round-6 disposition still claimed
    S53 enforced it."""
    from schema_model import validate_schema_registry
    # A registry whose max version exceeds the declared SCHEMA_VERSION. Uses a
    # fresh version above the head (SCHEMA_VERSION is now 2, with a real v2 in the
    # registry) and restores by deleting only what it added.
    extra = SCHEMA_VERSION + 1
    SCHEMAS[extra] = SCHEMA_V1
    try:
        problems = validate_schema_registry()
        assert any("SCHEMA_VERSION" in p for p in problems), problems
    finally:
        del SCHEMAS[extra]


def test_the_registry_versions_are_contiguous():
    from schema_model import validate_schema_registry
    # Add a version ABOVE head with a GAP (SCHEMA_VERSION+2 leaves +1 missing), so
    # the registry is non-contiguous and `validate` must object. Uses a
    # never-real version and restores it in `finally` — an earlier revision hard-set
    # `SCHEMAS[3]` when 3 did not exist, which now clobbers and then DELETES the real
    # head schema out of the shared dict, polluting every later test.
    gap = SCHEMA_VERSION + 2
    assert gap not in SCHEMAS
    SCHEMAS[gap] = SCHEMA_V1
    try:
        assert validate_schema_registry()
    finally:
        del SCHEMAS[gap]


def test_a_missing_versions_artifact_fails_the_gate(monkeypatch, tmp_path):
    """Round 11 correction: `--check` compared the file only when it existed.

    **Skips outside a git checkout.** `check()` returns 2 there — the documented
    "release probing needs git" status — before it can reach the missing-file
    condition. Asserting 1 unconditionally made this pass in the repo and fail
    in the extracted review package, which is the environment-dependence class
    round 10 objected to."""
    import subprocess

    import schema_evidence as ev
    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=ROOT,
                      capture_output=True).returncode:
        pytest.skip("no git checkout: check() returns 2 before reaching this")
    monkeypatch.setattr(ev.sv, "VERSIONS", tmp_path / "absent.json")
    monkeypatch.setattr(ev, "_tags", lambda: [])
    monkeypatch.setattr(ev, "_probe_at",
                        lambda ref, work: {"tag": ref, "commit": "x",
                                           "on_disk_user_version": 0,
                                           "store_schema_version": 1,
                                           "digest": None, "result": "ok",
                                           "_objects": {}})
    assert ev.check() == 1


# --- round 12 ------------------------------------------------------------


@pytest.mark.parametrize("victim", ["index:ix_edges_subj_rel", "table:wiki"])
def test_a_missing_declared_object_fails_the_record(victim):
    """Round 12, finding 2: "no extras" was only half of "exact" — a missing
    object with an updated digest passed the validator. (Now exercised on the manifestation itself, through
    sv.manifestation_problems: 0007 §4g withdrew the legacy runtime record that carried it; 0007 v20 re-states S73's
    citation.)"""
    import copy

    import schema_evidence as ev
    objs = copy.deepcopy(ev.sv._constructor_objects(1))
    del objs[victim]
    assert any("missing declared object" in p for p in ev.sv.manifestation_problems(objs, 1))


# --- round 13 ------------------------------------------------------------


def test_an_extra_manifestation_field_is_rejected():
    """Round 13 correction: "closed" had meant only "these fields present". (Now exercised on the manifestation
    itself, through sv.manifestation_problems: 0007 §4g withdrew the legacy runtime record that carried it; 0007 v20
    re-states S78's citation.)"""
    import copy

    import schema_evidence as ev
    objs = copy.deepcopy(ev.sv._constructor_objects(1))
    key = next(iter(objs))
    objs[key] = dict(objs[key], extra="field")
    assert any("not exactly" in p for p in ev.sv.manifestation_problems(objs, 1))


# --- round 14 (non-blocking corrections at acceptance) --------------------


def test_a_type_key_mismatch_is_reported():
    """Round 14: "structurally valid" now also means internally consistent."""
    import copy

    import schema_evidence as ev
    objs = copy.deepcopy(ev.sv._constructor_objects(1))
    key = "index:ix_edges_subj_rel"
    objs[key] = dict(objs[key], type="trigger")
    assert any("disagreeing with its key" in p for p in ev.sv.manifestation_problems(objs, 1))


def test_a_null_sql_declared_object_is_reported():
    import copy

    import schema_evidence as ev
    objs = copy.deepcopy(ev.sv._constructor_objects(1))
    objs["table:wiki"] = dict(objs["table:wiki"], sql=None)
    assert any("null SQL" in p for p in ev.sv.manifestation_problems(objs, 1))


def test_duplicate_column_names_are_reported():
    import copy

    import schema_evidence as ev
    objs = copy.deepcopy(ev.sv._constructor_objects(1))
    entry = copy.deepcopy(objs["table:wiki"])
    entry["columns"] = entry["columns"] + [entry["columns"][0]]
    objs["table:wiki"] = entry
    assert any("duplicate column names" in p for p in ev.sv.manifestation_problems(objs, 1))


_ACCEPTED_SOURCE = __import__("re").compile(
    r"constructor v\d+|migrated->v\d+ \(.+|v\d+:constructor(?:->v\d+)+ \(.+")
"""The closed set of sources an accepted manifestation may come from (0007 §4g.6 4d, INV-SA5): a version's own
constructor, a reviewed migration onto it, or a reviewed legacy ALTER chain. The withdrawn union's form, a runtime
record's manifestation (`<provenance> @ sqlite <version>`), is none of them."""


def test_every_accepted_manifestation_comes_from_a_closed_set_of_sources():
    """S58 / INV-SA5: no attestation record widens the accepted evidence. An attestation record carries no
    manifestation (its field set is closed: test_inv_sa5_a_forged_record_cannot_widen_the_accepted_evidence), and
    every entry the accepted-set generator PRODUCES comes from the closed set above. The control is the withdrawn
    union's own entry form, which the grammar refuses."""
    import schema_evidence as ev
    generated = ev.build_version_artifact(strict=False)["versions"]
    sources = [a["provenance"] for rec in generated.values() for a in rec["accepted"]]
    assert sources and all(_ACCEPTED_SOURCE.fullmatch(s) for s in sources), \
        [s for s in sources if not _ACCEPTED_SOURCE.fullmatch(s)]
    assert not _ACCEPTED_SOURCE.fullmatch("constructor v1 @ sqlite 3.45.1")     # the withdrawn union's form
