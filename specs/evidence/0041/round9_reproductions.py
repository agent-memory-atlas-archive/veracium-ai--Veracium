#!/usr/bin/env python3
"""0041 round 9 — the verdict's eight implementation findings, reproduced at the pin BEFORE any fix.

Pin `c05b709b80a6e817b4d45d5a265aa4d24e09594c` (0041 v14). The reviewer's own probes (`reviewer_probes.py`) are not
available to this seat, so each scenario here is built from the verdict's description, through the REAL persistence
paths (`Memory`, `SqliteStore`, `revoke_source`, `export_memory`/`import_memory`), never by writing rows by hand —
the verdict's R9-02 note found a transition test that performed its own replacement SQL and so tested nothing.

Each finding prints the reviewer's claim and the outcome at this tree beside it: REPRODUCED means the defect is
present here. Run from the repository root (or an export): python specs/evidence/0041/round9_reproductions.py
"""
import importlib.util
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from veracium import redaction as R                                  # noqa: E402
from veracium.schema import Disclosure, Episode, EvidenceAuthor, Provenance  # noqa: E402

_spec = importlib.util.spec_from_file_location("tt41_r9", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r9"] = tt
_spec.loader.exec_module(tt)

U = "u"
RESULTS = []


def claim(n, sentence):
    print(f"\n=== R9-0{n} — {sentence}")


def result(n, ok, detail):
    print(("    REPRODUCED: " if ok else "    DID NOT REPRODUCE: ") + detail)
    RESULTS.append((n, ok))


def prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw)
    return Provenance(**base)


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def episode_json(st, eid):
    return json.loads(st._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()[0],
                      object_pairs_hook=_strict_pairs)


# ---------------------------------------------------------------- R9-01
claim(1, "an ordinary episode write checks the attestation BEFORE its transaction, so a redaction committed in "
         "between is overwritten: the original summary comes back, the attestation stays, a repeat redact is a no-op")
with tempfile.TemporaryDirectory() as d:
    a = tt._mem(pathlib.Path(d), "r1.db")           # connection A
    b = tt._mem(pathlib.Path(d), "r1.db")           # connection B, the same database file
    secret = "the user's private diagnosis"
    a.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-09-01", summary=secret, provenance=prov()))
    real = a.store._attested_fields
    interleaved = {}

    def hooked(user_id, kind, target_id):
        got = real(user_id, kind, target_id)          # A's REAL attestation read: no record yet
        if not interleaved:
            interleaved["a_saw"] = sorted(got)
            interleaved["a_in_txn"] = a.store._conn.in_transaction
            interleaved["receipt"] = b.store.redact(U, episode_id="ep-1", reason="subject_request")   # B commits
        return got
    a.store._attested_fields = hooked
    try:
        a.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-09-01", summary=secret, provenance=prov()))
        wrote = "A's ordinary write completed"
    except ValueError as e:
        wrote = f"A's write refused: {e}"
    finally:
        a.store._attested_fields = real
    after = episode_json(b.store, "ep-1")["summary"]
    attested = sorted(b.store._attested_fields(U, "episode", "ep-1"))
    again = b.store.redact(U, episode_id="ep-1", reason="subject_request")
    after_repeat = episode_json(b.store, "ep-1")["summary"]
    result(1, after == secret and attested and again.repeated and after_repeat == secret,
           f"A read attestation {interleaved.get('a_saw')} with in_transaction={interleaved.get('a_in_txn')}; B redacted "
           f"and committed; {wrote}. Stored summary afterwards: {'the ORIGINAL' if after == secret else repr(after)}; "
           f"the attestation still names {attested}; a repeat redact returned repeated={again.repeated} and left the "
           f"summary {'the ORIGINAL' if after_repeat == secret else 'treated'}")

# ---------------------------------------------------------------- R9-03
claim(3, "the contribution-ledger treatment exists only in the EDGE branch and joins by raw id without the target "
         "kind: redacting a consolidated episode leaves its ledger digests; redacting an unrelated edge that shares "
         "the episode's raw id clears the EPISODE's ledger digests")
from veracium.schema import ConsolidationOutputDraft, ConsolidationState, Edge   # noqa: E402
from veracium.store.sqlite import SqliteStore                                     # noqa: E402


def consolidated(st, uid="u1", n=2):
    """Native consolidation (test_0014_ledger.py's `_run_consolidation` path): n inputs with a source_id, so each
    ledger row carries an identity digest; returns the output episode."""
    for i in range(n):
        st.add_episode(Episode(id=f"ep-{i}", user_id=uid, date=f"2026-07-0{i+1}", summary=f"day {i} detail",
                               provenance=prov(evidence_ref=f"ev-{i}", source_id=f"src-{i}")))
    op = st.create_or_takeover_consolidation(uid, [f"ep-{i}" for i in range(n)], "w1", 60)
    assert st.transition_consolidation_if_current(op.operation_id, op.fence, "w1", ConsolidationState.GENERATING)
    assert st.write_consolidation_output_if_current(op.operation_id, op.fence, "w1",
           ConsolidationOutputDraft(summary="the week, in detail", date_start="2026-07-01", date_end="2026-07-02"))
    assert st.transition_consolidation_if_current(op.operation_id, op.fence, "w1", ConsolidationState.OUTPUTS_DURABLE)
    return [ep for _, ep in st._episodes_for_operation(uid, op.operation_id) if ep.lineage][0]


def ledger(st, survivor_type, survivor_id):
    return st._conn.execute("SELECT identity_digest, evidence_ref_digest FROM contribution_ledger WHERE user_id='u1' "
                            "AND survivor_type=? AND survivor_id=? ORDER BY id", (survivor_type, survivor_id)).fetchall()


with tempfile.TemporaryDirectory() as d:
    st = SqliteStore(str(pathlib.Path(d) / "r3a.db"))
    out = consolidated(st)
    before = ledger(st, "episode", out.id)
    st.redact("u1", episode_id=out.id, reason="subject_request")
    after = ledger(st, "episode", out.id)
    kept = [r for r in after if r[0] is not None or r[1] is not None]
    result(3, len(before) == 2 and all(r[0] for r in before) and len(kept) == len(after) == 2,
           f"(a) episode branch: {len(before)} native ledger rows for the consolidated episode, identity digests "
           f"present before; after redacting the EPISODE, {len(kept)} of {len(after)} rows still carry their digests")
with tempfile.TemporaryDirectory() as d:
    st = SqliteStore(str(pathlib.Path(d) / "r3b.db"))
    out = consolidated(st)
    st.add_edge(Edge(id=out.id, user_id="u1", subject="user", relation="pet", object="an unrelated cat",
                     provenance=prov()))                         # an EDGE with the episode's raw id: a typed namespace
    before = ledger(st, "episode", out.id)
    st.redact("u1", edge_id=out.id, reason="subject_request")    # redact the EDGE, not the episode
    after = ledger(st, "episode", out.id)
    ep_attested = st._attested_fields("u1", "episode", out.id)
    result(3, all(r[0] for r in before) and all(r == (None, None) for r in after) and not ep_attested,
           f"(b) the mirror: an edge sharing raw id {out.id!r} with an UNREDACTED episode (episode attested: "
           f"{sorted(ep_attested)}); redacting the edge turned the episode's {len(after)} ledger rows from digests "
           f"present to {after}")

# ---------------------------------------------------------------- R9-07
claim(7, "semantic backfill enumerates edges without consulting attestation, so a redacted edge (its vector deleted "
         "by the redaction) is embedded again — the tombstone, not the original content (D3 selects SKIP)")
from veracium import Memory                                   # noqa: E402
from veracium.config import MemoryConfig                      # noqa: E402


class RecordingEmbed:
    def __init__(self):
        self.seen = []

    def id(self):
        return "rec@1"

    def dim(self):
        return 3

    def __call__(self, texts):
        self.seen.extend(texts)
        return [[1.0, float(len(x)), 0.5] for x in texts]


with tempfile.TemporaryDirectory() as d:
    emb = RecordingEmbed()
    m = Memory(llm=tt._quiet, embed=emb, config=MemoryConfig(db_path=str(pathlib.Path(d) / "r7.db"),
               wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))
    m.store.add_edge(Edge(id="e-7", user_id=U, subject="user", relation="works_as", object="a covert role",
                          provenance=prov()))
    n0 = m.embed_backfill(U)
    vec = lambda: m.store._conn.execute("SELECT COUNT(*) FROM edge_embedding WHERE edge_id='e-7'").fetchone()[0]
    v0 = vec()
    m.redact(U, edge_id="e-7", reason="subject_request")
    v1 = vec()
    emb.seen.clear()
    n2 = m.embed_backfill(U)
    v2 = vec()
    marker_embedded = any(R.MARKER in s for s in emb.seen)
    original_embedded = any("covert" in s for s in emb.seen)
    result(7, v0 == 1 and v1 == 0 and n2 == 1 and v2 == 1 and marker_embedded and not original_embedded,
           f"backfill wrote {n0}, vectors {v0}; after redaction {v1}; backfill again wrote {n2}, vectors {v2}; the "
           f"embedded text {'carried the marker' if marker_embedded else 'did not carry the marker'} and "
           f"{'the ORIGINAL content' if original_embedded else 'not the original content'} — the tombstone was "
           f"re-embedded (the verdict: not an oracle leak, the missing D3 skip)")

# ---------------------------------------------------------------- shared: a source export carrying one redaction
from veracium.portability import export_memory, import_memory   # noqa: E402


def mem(d, name):
    return tt._mem(pathlib.Path(d), name)


def redacted_export(d, name="src", eid="e-x", obj="the user's home address"):
    src = mem(d, f"{name}.db")
    src.store.add_edge(Edge(id=eid, user_id=U, subject="user", relation="lives_at", object=obj, provenance=prov()))
    src.redact(U, edge_id=eid, reason="subject_request")
    path = pathlib.Path(d) / f"{name}.jsonl"
    export_memory(src.store, U, path)
    return src, path


def lines(path):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in path.read_text().splitlines() if x.strip()]


def write_lines(path, recs):
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))


# ---------------------------------------------------------------- R9-04
claim(4, "the durable notice identity binds origin, source user and source event only — not the destination user "
         "or the typed target — and the body is not compared across imports")
with tempfile.TemporaryDirectory() as d:
    _src, path = redacted_export(d)
    dst = mem(d, "dst4.db")
    r1 = import_memory(dst.store, path, user_id="v1")
    try:
        r2 = import_memory(dst.store, path, user_id="v2")
        second = {k: r2.get(k) for k in ("notices_applied", "notices_standing", "notices_existing")}
    except Exception as e:
        r2, second = None, f"refused: {type(e).__name__}: {str(e)[:120]}"
    v2_attested = sorted(dst.store._attested_fields("v2", "edge", "e-x"))
    rows = dst.store._conn.execute("SELECT user_id, target_id FROM redactions").fetchall()
    result(4, isinstance(second, dict) and second.get("notices_existing") == 1 and second.get("notices_applied") == 0
           and not v2_attested,
           f"(a) user remaps: first import into v1 → applied {r1.get('notices_applied')}, standing "
           f"{r1.get('notices_standing')}; the same file into v2 → {second}; v2's target attested: {v2_attested}; "
           f"redaction rows held: {rows}")
with tempfile.TemporaryDirectory() as d:
    _src, path = redacted_export(d)
    dst = mem(d, "dst4b.db")
    import_memory(dst.store, path)
    recs = lines(path)
    later = [dict(r, fields=["object", "subject"]) if r.get("record") == "redaction" else r for r in recs]
    p2 = pathlib.Path(d) / "later.jsonl"
    write_lines(p2, later)
    try:
        r2 = import_memory(dst.store, p2)
        outcome = f"ACCEPTED: existing {r2.get('notices_existing')}, applied {r2.get('notices_applied')}"
        accepted = True
    except Exception as e:
        outcome, accepted = f"refused: {str(e)[:140]}", False
    result(4, accepted,
           f"(b) a later file with the same source identity and target, fields "
           f"{[r for r in later if r.get('record') == 'redaction'][0]['fields']} where the first said "
           f"{[r for r in recs if r.get('record') == 'redaction'][0]['fields']}: {outcome}")

# ---------------------------------------------------------------- R9-08
claim(8, "a notice's `fields` admit any non-empty string: prose disguised as a field name is accepted as a standing "
         "notice and stored verbatim in a column the implementation treats as non-content")
with tempfile.TemporaryDirectory() as d:
    _src, path = redacted_export(d)
    prose = "private prose disguised as a field name"
    recs = [dict(r, fields=[prose]) for r in lines(path) if r.get("record") == "redaction"]   # the notice only:
    p8 = pathlib.Path(d) / "n8.jsonl"                                                          # a STANDING notice
    head = [r for r in lines(path) if r.get("record") not in ("edge", "episode", "redaction")]
    write_lines(p8, head + recs)
    dst = mem(d, "dst8.db")
    try:
        r = import_memory(dst.store, p8)
        stored = dst.store._conn.execute("SELECT fields FROM redactions").fetchall()
        result(8, any(prose in s[0] for s in stored),
               f"imported: standing {r.get('notices_standing')}; the redactions table now holds fields {stored}")
    except Exception as e:
        result(8, False, f"refused: {str(e)[:160]}")

# ---------------------------------------------------------------- R9-02
claim(2, "§11.2's D1 closures are not enforced: revoke_source persists an arbitrary prose reason; add_episode and "
         "export/restore-import accept an arbitrary retirement reason; and a real redaction leaves the linked "
         "historical source-revocation prose in place (the transition test does its own UPDATE)")
from veracium.store import revocation as rv                     # noqa: E402
from veracium.store.revocation_sweep import digest_of            # noqa: E402

with tempfile.TemporaryDirectory() as d:
    s = SqliteStore(str(pathlib.Path(d) / "r2a.db"))
    s.add_edge(Edge(id="e1", user_id=U, subject="user", relation="located_at", object="Lisbon",
                    provenance=Provenance(author_of_evidence=EvidenceAuthor.THIRD_PARTY, evidence_ref="ev-a",
                                          source_id="feed-1")))
    dg = digest_of(None, "feed-1", s.local_origin())
    prose = "because she told me in confidence that the feed is her ex"
    try:
        rv.revoke_source(s, U, dg, "revoke", prose, "2026-09-01T00:00:00Z")
        held = s._conn.execute("SELECT reason FROM source_revocations WHERE identity_digest=?", (dg,)).fetchone()
        result(2, held is not None and held[0] == prose, f"(a) revoke_source accepted and persisted the reason {held[0]!r}")
    except Exception as e:
        result(2, False, f"(a) revoke_source refused: {str(e)[:140]}")
with tempfile.TemporaryDirectory() as d:
    m = mem(d, "r2b.db")
    prose = "retired because the user regretted saying it"
    try:
        m.store.add_episode(Episode(id="ep-r", user_id=U, date="2026-09-01", summary="s", provenance=prov(),
                                    retired_reason=prose))
        stored = episode_json(m.store, "ep-r").get("retired_reason")
        out = pathlib.Path(d) / "r2b.jsonl"
        export_memory(m.store, U, out)
        dst = mem(d, "r2b-dst.db")
        import_memory(dst.store, out, restore=True)
        restored = episode_json(dst.store, "ep-r").get("retired_reason")
        result(2, stored == prose and restored == prose,
               f"(b) add_episode stored retired_reason {stored!r}; export and restore-import carried it: {restored!r}")
    except Exception as e:
        result(2, False, f"(b) refused: {str(e)[:160]}")
with tempfile.TemporaryDirectory() as d:
    fm = tt._frozen_memory(pathlib.Path(d))
    man = tt._frozen_rows()
    dg, linked = man["prose_source_revocation"], man["source_linked_edge"]
    q = lambda: fm.store._conn.execute("SELECT reason FROM source_revocations WHERE identity_digest=?", (dg,)).fetchone()[0]
    before = q()
    owner = fm.store._conn.execute("SELECT user_id FROM edges WHERE id=?", (linked,)).fetchone()[0]
    fm.redact(owner, edge_id=linked, reason="subject_request")
    after = q()
    result(2, before == after and R.MARKER not in after,
           f"(c) the frozen store's linked edge {linked!r} redacted through the REAL operation; its source-revocation "
           f"reason before {before!r}, after {after!r}")

# ---------------------------------------------------------------- R9-05
claim(5, "a witnessed receipt reports the DESTINATION's version counters and time, not the source's (its version "
         "fields cannot be unknown); a re-export replaces the source's reason and time; and the original notice plus "
         "its honest relay are refused together as a corrupted source")
with tempfile.TemporaryDirectory() as d:
    src = mem(d, "src5.db")
    src.store.add_edge(Edge(id="e-5", user_id=U, subject="user", relation="lives_at", object="a private address",
                            provenance=prov()))
    rs = src.redact(U, edge_id="e-5", reason="legal_obligation")
    p_src = pathlib.Path(d) / "src5.jsonl"
    export_memory(src.store, U, p_src)
    dst = mem(d, "dst5.db")
    for i in range(2):                                      # the destination has history of its own
        dst.store.add_edge(Edge(id=f"e-pre-{i}", user_id=U, subject="user", relation="likes", object=f"thing {i}",
                                provenance=prov()))
    import_memory(dst.store, p_src)
    rd = dst.redact(U, edge_id="e-5", reason="subject_request")      # a repeat: the reconstructed receipt
    p_relay = pathlib.Path(d) / "relay5.jsonl"
    export_memory(dst.store, U, p_relay)
    src_note = [r for r in lines(p_src) if r.get("record") == "redaction"][0]
    relay_note = [r for r in lines(p_relay) if r.get("record") == "redaction"][0]
    result(5, rd.reconstructed and (rd.store_version_before, rd.store_version_after) != (rs.store_version_before, rs.store_version_after),
           f"(a) source receipt versions {rs.store_version_before}->{rs.store_version_after} at {rs.recorded_at}; the "
           f"destination's reconstructed receipt (reconstructed={rd.reconstructed}) reports "
           f"{rd.store_version_before}->{rd.store_version_after} at {rd.recorded_at}, event {rd.event_ref!r} — local "
           f"counters standing in for unknown source facts")
    result(5, relay_note["reason"] != src_note["reason"] and relay_note["recorded_at"] != src_note["recorded_at"]
           and (relay_note["origin"], relay_note["source_event_ref"]) == (src_note["origin"], src_note["source_event_ref"]),
           f"(b) the relay keeps the source identity ({relay_note['origin'][:12]}…, {relay_note['source_event_ref']}) "
           f"but says reason {relay_note['reason']!r} where the source said {src_note['reason']!r}, and recorded_at "
           f"{relay_note['recorded_at']} where the source said {src_note['recorded_at']}")
    # (c) as the verdict built it: the original notice and its honest relay CO-IMPORTED, in one file
    combined = pathlib.Path(d) / "both5.jsonl"
    write_lines(combined, lines(p_src) + [relay_note])
    third = mem(d, "third5.db")
    try:
        import_memory(third.store, combined)
        result(5, False, "(c) the original notice and its honest relay, co-imported in one file, were accepted")
    except Exception as e:
        result(5, True, f"(c) the original notice and its honest relay co-imported in one file: refused — {str(e)[:150]}")
    # (c') and imported one after the other they are ACCEPTED as "existing" — not a refusal, the R9-04(b) symptom
    fourth = mem(d, "fourth5.db")
    import_memory(fourth.store, p_src)
    r4 = import_memory(fourth.store, p_relay)
    print(f"    (note, not counted) sequentially, the relay after the original is accepted: existing "
          f"{r4.get('notices_existing')} — the cross-import body comparison R9-04(b) found missing")

# ---------------------------------------------------------------- R9-06
claim(6, "a redacted historical prose-kind episode carries the marker as its kind, and its own valid export is "
         "refused at import because the marker kind is not a recognised operational kind")
with tempfile.TemporaryDirectory() as d:
    fm = tt._frozen_memory(pathlib.Path(d))
    owner = fm.store._conn.execute("SELECT user_id FROM episodes WHERE id='ep-prose-kind'").fetchone()[0]
    fm.redact(owner, episode_id="ep-prose-kind", reason="subject_request")
    kind = episode_json(fm.store, "ep-prose-kind")["kind"]
    p6 = pathlib.Path(d) / "r6.jsonl"
    export_memory(fm.store, owner, p6)
    note = [r for r in lines(p6) if r.get("record") == "redaction" and r.get("target_id") == "ep-prose-kind"]
    dst = mem(d, "dst6.db")
    try:
        import_memory(dst.store, p6)
        result(6, False, f"the export imported (kind {kind!r})")
    except Exception as e:
        result(6, kind == R.MARKER and bool(note),
               f"kind after redaction is the marker: {kind == R.MARKER}; the export carries its notice naming "
               f"{note[0]['fields'] if note else None}; import refused: {str(e)[:150]}")

# ---------------------------------------------------------------- summary
print("\n" + "-" * 100)
for n, ok in RESULTS:
    print(f"  R9-0{n}: {'REPRODUCED' if ok else 'DID NOT REPRODUCE'}")
sys.exit(0 if all(ok for _, ok in RESULTS) else 1)
