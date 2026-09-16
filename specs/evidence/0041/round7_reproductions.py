#!/usr/bin/env python3
"""0041 round 7 — the verdict's three corrections, reproduced at the pin BEFORE any fix.

Pin `6b8d757530865194c5ad4ffc50783994b7eb8f0c` (0041 v13). All three are in this
seat's evidence; amendments 2 and 3 of round 6 are recorded CLOSED by the
reviewer and amendment 1 is partially closed.

The pin-era bodies are FROZEN QUOTATIONS, not a re-read of the tree — the rule
`tests/test_spec_gate.py::test_a_reproduction_that_quotes_test_source_freezes_it_at_the_pin`
now enforces, after this seat wrote two reproductions in consecutive rounds that
inverted the moment their defects were fixed.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PIN_FILE_SHA16 = '3c00b357c8a5bfc8'   # tests/test_0041_transition_table.py at the pin
PIN_BODIES = {
    "test_B_an_ordinary_write_of_a_new_prose_kind_is_refused_while_the_stored_one_stays": "def f(tmp_path):\n    st = _mem(tmp_path).store\n    st.add_episode(Episode(id=\"ep-old\", user_id=U, date=\"2026-09-01\", summary=\"s\", kind=\"told me in confidence\", provenance=_prov()))\n    with pytest.raises(Exception):\n        st.add_episode(Episode(id=\"ep-new\", user_id=U, date=\"2026-09-02\", summary=\"s\", kind=\"another prose kind\", provenance=_prov()))\n    assert [e for e in st.episodes(U) if e.id == \"ep-old\"][0].kind == \"told me in confidence\"\n",
    "test_D_a_source_revocation_reason_holding_the_callers_sentence_is_replaced": "def f(tmp_path):\n    \"\"\"source_revocations.reason has no vocabulary to preserve (round-4 F3,\n    executed): it is REPLACED as ordinary prose; the effect's registry value on\n    the affected records is preserved.\"\"\"\n    from veracium.source_identity import resolve_origin, source_identity_digest\n    from veracium.store import revocation as rv\n    st = _mem(tmp_path).store\n    st.add_edge(Edge(id=\"e-s\", user_id=U, subject=\"user\", relation=\"works_as\", object=\"Porto\", provenance=_prov(source_id=\"mb-x\")))\n    digest = source_identity_digest(resolve_origin(None, st.local_origin()), \"mb-x\")\n    rv.revoke_source(st, U, digest, \"revoke\", \"the mailbox was compromised on 3 March\", \"2026-09-15T00:00:00Z\")\n    st._conn.execute(\"UPDATE source_revocations SET reason=? WHERE user_id=?\", (MARKER, U)); st._conn.commit()\n    assert st._conn.execute(\"SELECT reason FROM source_revocations WHERE user_id=?\", (U,)).fetchone()[0] == MARKER\n    assert _edge(st, \"e-s\").invalidation_reason == \"revoked_source\"\n",
    "test_B_an_import_carrying_a_prose_kind_is_refused": "def f(tmp_path):\n    from veracium.portability import export_memory, import_memory\n    # ROUND-6 FINDING 1, EXTENDED. The reviewer named three tests that built their\n    # historical records through ordinary writers; this is a FOURTH of the same\n    # shape, found by the class sweep rather than by the verdict. It wrote a prose\n    # kind into its own source store to have something to export \u2014 the exact write\n    # the closure refuses \u2014 so it too would have failed while preparing data. The\n    # export source is the frozen store, which already carries a prose-kind\n    # episode written before the restrictions.\n    src = _frozen_store(tmp_path)\n    assert any(e.kind == \"told me in confidence\" for e in src.episodes(U)), (\n        \"the frozen store must carry the prose-kind episode this export needs\")\n    out = tmp_path / \"x.jsonl\"\n    export_memory(src, U, out)\n    with pytest.raises(Exception):\n        import_memory(_mem(tmp_path, \"d.db\").store, out)\n",
    "_redact": "def f(memory, *, kind, target_id, fields):\n    \"\"\"THE ONE PLACE THE ASSUMED API SPELLING LIVES.\n\n    0041 defines the redaction CONTRACT (\u00a74b, the receipt-fields row, the\n    repeat-calls row) and does not fix a signature. These tests bind the\n    contract, not the spelling, so every call goes through this adapter: when\n    the API lands under different argument names, ONE function is reconciled and\n    no assertion moves. That is deliberate \u2014 a test that hard-codes an invented\n    signature in six places turns an ordinary naming choice into six false reds.\n\n    Today `Memory` has no `redact`, so this raises `AttributeError` and the\n    callers are strict xfails. It is a genuine call, not a reference: a no-op\n    method added to `Memory` satisfies the attribute lookup and then fails every\n    assertion that follows, which is the property the round-5 verdict found\n    missing.\"\"\"\n    return memory.redact(kind=kind, target_id=target_id, fields=fields)\n"
}

FAILURES = []


def claim(n, sentence):
    print(f"\n=== R{n} — {sentence}")


def result(ok, detail):
    print(("    REPRODUCED: " if ok else "    DID NOT REPRODUCE: ") + detail)
    if not ok:
        FAILURES.append(detail)


def calls_in(body, attr):
    tree = ast.parse(body)
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and getattr(n.func, "attr", "") == attr]


# ---------------------------------------------------------------- R1
claim(1, "the prose-kind write test still builds its historical record through "
         "an ordinary writer, so the restriction stops it at SETUP")
body = PIN_BODIES["test_B_an_ordinary_write_of_a_new_prose_kind_is_refused_while_the_stored_one_stays"]
writes = calls_in(body, "add_episode")
frozen = "_frozen_store" in body or "_frozen_rows" in body
result(len(writes) >= 1 and not frozen,
       f"{len(writes)} add_episode call(s) in the body and no frozen-fixture helper; the "
       f"FIRST is the historical record `ep-old`, so the restriction fires before "
       f"`ep-new` is ever attempted — the assertion the test exists for is never reached")

# ---------------------------------------------------------------- R2
claim(2, "and the source-reason test creates a NEW prose reason rather than using "
         "the frozen historical revocation that now exists")
body = PIN_BODIES["test_D_a_source_revocation_reason_holding_the_callers_sentence_is_replaced"]
revokes = calls_in(body, "revoke_source")
result(bool(revokes) and "_frozen" not in body,
       f"{len(revokes)} revoke_source call(s) and no frozen-fixture helper — the "
       f"fixture carries `prose_source_revocation` and this test does not read it")

# ---------------------------------------------------------------- R3
claim(3, "the import test exports the WHOLE mixed fixture, so a restriction that "
         "rejects markers satisfies its expected rejection without any kind check")
body = PIN_BODIES["test_B_an_import_carrying_a_prose_kind_is_refused"]
result("_frozen_store" in body and "export_memory" in body,
       "the body exports the frozen store wholesale — which carries "
       "`unattested_marker` and `unattested_marker_2` — so the `pytest.raises` it "
       "asserts can be satisfied by a marker rule alone, proving nothing about kinds")

# ---------------------------------------------------------------- R4
claim(4, "the redaction adapter's signature disagrees with §4a, which FIXES one")
body = PIN_BODIES["_redact"]
spec = (ROOT / "specs" / "0041-targeted-redaction.md").read_text()
signature = "redact(user_id, *, edge_id | episode_id, reason)" in spec
adapter_kwargs = sorted({k.arg for c in calls_in(body, "redact") for k in c.keywords})
result(signature and adapter_kwargs == ["fields", "kind", "target_id"],
       f"§4a specifies `redact(user_id, *, edge_id | episode_id, reason)`; the adapter "
       f"passes {adapter_kwargs}. A callable with the documented signature fails on an "
       f"unexpected `kind` argument. The adapter's own docstring claimed the spec 'does "
       f"not fix a signature' — §4a does, and has since v1")

# ---------------------------------------------------------------- R5
claim(5, "and the coverage accounting in the round-7 README was wrong: four "
         "positive controls, but only three cover STRICT xfails")
camp = (ROOT / "specs" / "evidence" / "0041" / "xfail_mutant_campaign.py").read_text()
positives = camp.count('check("POSITIVE CONTROL')
strict = sum((ROOT / "tests" / f).read_text().count("xfail(strict=True")
             for f in ("test_0041_transition_table.py", "test_0041_treatment_matrix.py",
                       "test_0041_evidence.py"))
result(positives == 4 and strict == 11,
       f"{positives} positive controls, {strict} strict xfails; one positive control covers "
       f"the ordinary fixture-checker test, so {strict - 3} strict xfails await one — not the "
       f"seven the README claimed")

print("\n" + "=" * 72)
if FAILURES:
    print(f"{len(FAILURES)} claim(s) DID NOT reproduce:")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print("every correction in the round-7 verdict reproduced at the pin; no fix applied")
