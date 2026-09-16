#!/usr/bin/env python3
"""0041 — a FROZEN store written BEFORE the restrictions the spec adds.

Round 5's standing artifact ask, made twice: "freeze pre-restriction fixtures so
future write restrictions do not prevent test setup."

THE PROBLEM THIS SOLVES. Every transition test proves a claim about a record that
EXISTS ALREADY — a prose `kind`, a prose `retired_reason`, a relation-only
quarantine, an unattested marker. Today those records are built by writing them
through the store in the test's own setup. The moment 0041's write-path closure
lands, those setup writes are refused, and the tests that prove existing records
survive can no longer create an existing record. The evidence would be destroyed
by the very change it exists to check.

So the bytes are frozen NOW, under today's model and today's store, and the tests
copy the file instead of writing the rows. A frozen store is the only fixture a
write restriction cannot reach.

    --write   build the store and the manifest (run once, before the closure)
    --check   re-verify the frozen bytes against the manifest

The manifest records the digest, the store's schema version, and the tree's HEAD
at freeze time, so a silent regeneration after the closure lands is visible as a
digest change and a reader can tell which code wrote it.
"""
# Mutation-Matrix: tests/test_0041_transition_table.py::test_the_frozen_pre_restriction_store_matches_its_manifest
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DB = HERE / "pre_restriction.sqlite"
MANIFEST = HERE / "pre_restriction_manifest.json"
U = "u"
MARKER = "\x00veracium:redacted\x00"
sys.path.insert(0, str(ROOT / "src"))


def _strict_pairs(pairs):
    """0026-EVIDENCE-R8-1: `json.loads` keeps the LAST duplicate key, so a
    manifest carrying `"sha256"` twice would authenticate under whichever value
    came second. Duplicate names REFUSE at parse, at every evidence boundary —
    and this file's manifest is exactly such a boundary, since its digest is what
    says the frozen fixture has not been regenerated."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate JSON member {k!r}")
        out[k] = v
    return out


def _strict_json(text: str):
    """json.loads with duplicate-member refusal (0026-EVIDENCE-R8-1)."""
    return json.loads(text, object_pairs_hook=_strict_pairs)


def _quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def build(path: pathlib.Path):
    """Write one of every shape the transition table needs, through the ordinary
    write paths, with nothing that 0041 has not yet closed."""
    from veracium import Memory, MemoryConfig
    from veracium.schema import Disclosure, Edge, Episode, EvidenceAuthor, Provenance, QUARANTINE_RELATION

    def prov(**kw):
        base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                    disclosure=Disclosure.MENTIONABLE)
        base.update(kw)
        return Provenance(**base)

    m = Memory(llm=_quiet, config=MemoryConfig(db_path=str(path), wiki_recompile_after_writes=0,
                                               scope_groups={}, require_source_id=False))
    st = m.store
    rows = {}

    # A — a relation-only quarantine: quarantined by its RELATION, not its disclosure
    st.add_edge(Edge(id="e-quarantine-relation", user_id=U, subject="user",
                     relation=QUARANTINE_RELATION, object="a claim", provenance=prov()))
    rows["relation_only_quarantine"] = "e-quarantine-relation"

    # B — an episode carrying PROSE in `kind`, stored before the recognised-kind closure
    st.add_episode(Episode(id="ep-prose-kind", user_id=U, date="2026-09-01", summary="a summary",
                           kind="told me in confidence", provenance=prov()))
    rows["prose_kind"] = "ep-prose-kind"

    # C — an UNATTESTED marker: the bytes, with no redaction record anywhere
    st.add_edge(Edge(id="e-unattested-marker", user_id=U, subject="user", relation="works_as",
                     object=MARKER, provenance=prov()))
    rows["unattested_marker"] = "e-unattested-marker"

    # D — legacy prose in each of the reason carriers
    st.add_episode(Episode(id="ep-prose-retired", user_id=U, date="2026-09-01", summary="a summary",
                           retired_reason="she asked me not to repeat it", provenance=prov()))
    rows["prose_retired_reason"] = "ep-prose-retired"

    # D-control — an ACTIVE episode: retired_reason absent, which is the case round 5
    # found row 49 destroying. Frozen so the absence can be proved to survive.
    st.add_episode(Episode(id="ep-active", user_id=U, date="2026-09-02", summary="a summary",
                           provenance=prov()))
    rows["active_episode_absent_reason"] = "ep-active"

    # D-registry — a REGISTERED reason, which must be preserved unchanged
    st.add_episode(Episode(id="ep-registry-reason", user_id=U, date="2026-09-03", summary="a summary",
                           retired_reason="superseded", provenance=prov()))
    rows["registry_retired_reason"] = "ep-registry-reason"

    # C-bis — a SECOND unattested marker row and an ordinary row beside it, so the
    # migration-report test can assert the report's CONTENTS against a store whose
    # answer is known WITHOUT writing marker rows itself. Round 6, finding 1: three
    # transition tests still built their historical records through ordinary
    # writers and failed while PREPARING data once the write restrictions were
    # added — which is the trap this fixture exists to avoid, sprung in the tests
    # that did not use it.
    st.add_edge(Edge(id="e-unattested-marker-2", user_id=U, subject="user", relation="lives_in",
                     object=MARKER, provenance=prov()))
    rows["unattested_marker_2"] = "e-unattested-marker-2"
    st.add_edge(Edge(id="e-ordinary", user_id=U, subject="user", relation="likes",
                     object="tea", provenance=prov()))
    rows["ordinary_edge"] = "e-ordinary"

    # E — a historical SOURCE REVOCATION carrying the caller's PROSE, written
    # through the sole writer before D1's vocabulary closes the field. Round 6,
    # finding 1: the six-shape fixture lacked this case, and after v12 it can no
    # longer be created, because `revoke_source` will refuse a reason outside the
    # four values. This row is the only pre-closure instance that will exist.
    # ROUND 7: the revocation now has a SOURCE-LINKED EDGE, because the round-7
    # reviewer found the frozen revocation carried no linked record and the
    # transition test asserts about the AFFECTED record as well as the reason. A
    # revocation with nothing attached cannot exercise "the prose is replaced and
    # the effect's registry value on the affected record is preserved" — only half
    # the claim has a subject.
    from veracium.source_identity import resolve_origin, source_identity_digest
    from veracium.store.revocation import revoke_source
    st.add_edge(Edge(id="e-source-linked", user_id=U, subject="user", relation="works_as",
                     object="Porto", provenance=prov(source_id="mb-frozen")))
    digest = source_identity_digest(resolve_origin(None, st.local_origin()), "mb-frozen")
    revoke_source(st, U, digest, "revoke",
                  "she asked me to drop everything from that address", "2026-09-01T00:00:00Z")
    rows["prose_source_revocation"] = digest
    rows["source_linked_edge"] = "e-source-linked"

    st._conn.commit()
    st.close() if hasattr(st, "close") else None
    return rows


def digest(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--map", action="store_true",
                    help="print the fixture-to-test mapping, DERIVED from the tests")
    a = ap.parse_args()

    if a.write:
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d) / "pre_restriction.sqlite"
            rows = build(tmp)
            shutil.copy2(tmp, DB)
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        from veracium.store import schema_version as sv
        MANIFEST.write_text(json.dumps({
            "what": "a store written BEFORE 0041's write-path closure; the transition "
                    "tests copy it instead of writing rows a landed closure would refuse",
            "sha256": digest(DB),
            "bytes": DB.stat().st_size,
            "store_schema_version": sv.SCHEMA_VERSION,
            "frozen_at_head": head,
            "frozen_on": "2026-09-16",
            "rows": rows,
        }, indent=2, sort_keys=True) + "\n")
        print(f"wrote {DB.name} ({DB.stat().st_size} bytes) and its manifest")
        print(f"  sha256 {digest(DB)}")
        return 0

    if a.check:
        man = _strict_json(MANIFEST.read_text())
        actual = digest(DB)
        if actual != man["sha256"]:
            print(f"FROZEN FIXTURE CHANGED\n  manifest {man['sha256']}\n  on disk  {actual}")
            return 1
        print(f"frozen fixture matches its manifest: {actual[:16]}… "
              f"({man['bytes']} bytes, store schema {man['store_schema_version']}, "
              f"frozen at {man['frozen_at_head'][:8]})")
        return 0

    if a.map:
        # THE FIXTURE-TO-TEST MAPPING, asked for by the round-7 reviewer so the
        # remaining amendment is verifiable at a glance. DERIVED by scanning the
        # tests for `_frozen_rows()["<shape>"]` and for the manifest's own row ids,
        # never hand-written: a hand list would be one more carrier to drift, and
        # this whole arc has been a catalogue of those.
        import ast
        import re
        man = _strict_json(MANIFEST.read_text())
        tests = sorted((ROOT / "tests").glob("test_0041_*.py"))
        used = {k: [] for k in man["rows"]}
        for f in tests:
            src = f.read_text()
            tree = ast.parse(src)
            for fn in [n for n in ast.walk(tree)
                       if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]:
                seg = ast.get_source_segment(src, fn) or ""
                for shape, rid in man["rows"].items():
                    if f'"{shape}"' in seg or f"'{shape}'" in seg or rid in seg:
                        used[shape].append(f"{f.name}::{fn.name}")
        width = max(len(k) for k in used)
        print(f"fixture: {DB.name}  sha256 {digest(DB)[:16]}…  {len(man['rows'])} shapes")
        print(f"derived from {len(tests)} test module(s); a shape with no test is a shape "
              f"nobody is using\n")
        for shape in sorted(used):
            nodes = used[shape]
            print(f"  {shape:<{width}}  {man['rows'][shape][:28]:<30} {len(nodes)} test(s)")
            for n in nodes:
                print(f"  {'':<{width}}    {n}")
        orphans = [s for s, n in used.items() if not n]
        print(f"\n{len(used) - len(orphans)} of {len(used)} shapes are used by at least one test")
        if orphans:
            print(f"ORPHANED SHAPES (frozen, referenced by nothing): {orphans}")
            return 1
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
