"""specs/0041 — the EXECUTABLE TRANSITION TABLE (the round-4 verdict's artifact ask):
existing records → new writes → redaction → import → repeated calls.

Every fixture here is a record stored BEFORE the restrictions the spec adds —
through today's store, under today's model — because a transition claim proved on
a record built under the new model proves nothing (§4h's fixture rule). Each row
applies the ruled treatment through the store's own write paths and asks the
product's readers and predicates whether the record's OPERATIONAL disposition
survived. Rows the shipped code cannot yet honour are STRICT xfails, red first.
"""
import hashlib
import json
import pathlib
import shutil

import pytest

from veracium import Memory, MemoryConfig
from veracium.schema import (DISPOSITIONED_REASONS, Disclosure, Edge, Episode, EvidenceAuthor, Provenance,
                             QUARANTINE_RELATION)

MARKER = "\x00veracium:redacted\x00"
U = "u"


def _quiet(prompt, *, system=None, role="compile", json_schema=None):
    return json.dumps({"triples": [], "episode": "x", "instructions": []}) if role == "distill" else ""


def _mem(tmp_path, name="m.db"):
    return Memory(llm=_quiet, config=MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                                                  scope_groups={}, require_source_id=False))


def _prov(**kw):
    base = dict(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev", disclosure=Disclosure.MENTIONABLE)
    base.update(kw)
    return Provenance(**base)


def _rewrite(store, table, rid, **changes):
    """The simulated treatment on a STORED record: full re-validation of the new dump, then the row."""
    model = Edge if table == "edges" else Episode
    row = store._conn.execute(f"SELECT json FROM {table} WHERE id=?", (rid,)).fetchone()
    d = json.loads(row[0])
    for k, v in changes.items():
        if "." in k:
            a, b = k.split(".", 1); d[a][b] = v
        else:
            d[k] = v
    model.model_validate(d)
    if table == "edges":
        store._conn.execute("UPDATE edges SET json=?, subject=?, relation=?, object=? WHERE id=?",
                            (json.dumps(d), d["subject"], d["relation"], d["object"], rid))
    else:
        store._conn.execute("UPDATE episodes SET json=? WHERE id=?", (json.dumps(d), rid))
    store._conn.commit()


def _redact(memory, *, user_id=U, edge_id=None, episode_id=None, reason):
    """THE OPERATION AS §4a SPECIFIES IT, not as this seat guessed it.

    §4a, at the reviewed pin and since v1:

        redact(user_id, *, edge_id | episode_id, reason) -> RedactionReceipt

    ROUND-7 CORRECTION 3. This adapter passed `kind`, `target_id` and `fields`,
    and its docstring said *"0041 … does not fix a signature"*. **It does, and it
    did when that sentence was written, in the same tree.** A callable with the
    documented signature fails immediately on an unexpected `kind` argument, so
    the repeat test would have gone green against an implementation that ignored
    §4a and red against one that followed it — the identical defect the round-6
    reviewer found in the event-count helper, which counted a `redaction_events`
    table this spec never proposes.

    The lesson is the same both times and it is not about carelessness: **when a
    test needs a surface that does not exist yet, the temptation is to invent one
    and note the assumption. The spec is the place to look first, and both times
    the answer was already there.** What an adapter is for is the spelling the
    spec leaves open — here, only the receipt's field names are open, and those
    are read through `_field`.

    `edge_id` and `episode_id` are exclusive, as the `|` in §4a requires, and
    that exclusivity is asserted rather than assumed: passing both, or neither,
    is a caller error and fails here rather than reaching the product."""
    assert (edge_id is None) != (episode_id is None), (
        "§4a takes `edge_id | episode_id` — exactly one, never both and never neither")
    target = {"edge_id": edge_id} if edge_id is not None else {"episode_id": episode_id}
    return memory.redact(user_id, reason=reason, **target)


def _field(receipt, name):
    """Read one receipt field, whether the receipt is a model or a mapping.

    Deliberately NOT `getattr(receipt, name, None)`: a default would turn a
    missing field into a `None` that compares equal to another missing field,
    and two absent values agreeing is exactly how the old bodies passed."""
    if isinstance(receipt, dict):
        assert name in receipt, f"the receipt carries no {name!r}"
        return receipt[name]
    assert hasattr(receipt, name), f"the receipt carries no {name!r}"
    return getattr(receipt, name)


def _redaction_event_count(store, target_id):
    """How many REDACTION events the journal holds for one target.

    ROUND-6 FINDING 1, aligned with the journal contract the spec already carries.
    The first version queried a `redaction_events` table — a table this spec never
    proposes. §11.2 and §2d-ii say the redaction event is a NEW KIND in the
    EXISTING `edge_event` journal (one branch added at the writer that already
    refuses, no new mechanism), carrying the redaction vocabulary in `reason`
    where every other kind carries `None`. Counting a table of my own invention
    would have gone green against an implementation that followed the spec, and
    red against one that did not — the wrong way round.

    No `redacted` kind is written yet, so this returns 0 today and its caller is a
    strict xfail. It reads the SHIPPED journal, so when the kind lands the count
    becomes real without this helper changing."""
    rows = store._conn.execute(
        "SELECT COUNT(*) FROM edge_event WHERE edge_id=? AND kind=?",
        (target_id, "redacted")).fetchone()
    return rows[0]


def _edge(store, eid):
    return [e for e in store.edges(U, active_only=False, include_quarantined=True) if e.id == eid][0]


# ---------------------------------------------------------------- row A: a relation-only quarantine stored BEFORE the closure
def test_A_existing_relation_only_quarantine_keeps_its_quarantine_under_the_ruled_treatment(tmp_path):
    """§4h: a redaction may not change a derived disposition; redacting `relation`
    on a quarantined edge RE-ESTABLISHES the disposition through
    provenance.disclosure in the same write. The fixture is the pre-closure
    shape: relation carries the quarantine, the disclosure does not."""
    st = _mem(tmp_path).store
    st.add_edge(Edge(id="e-q", user_id=U, subject="neighbour", relation=QUARANTINE_RELATION,
                     object="says the user owes money", provenance=_prov()))
    before = _edge(st, "e-q")
    assert before.quarantined and before.provenance.disclosure != Disclosure.QUARANTINED   # the pre-closure shape, stored
    _rewrite(st, "edges", "e-q", relation=MARKER, **{"provenance.disclosure": "quarantined"})   # the ruling's own shape: redact `relation`, re-establish through the disclosure
    after = _edge(st, "e-q")
    assert after.relation == MARKER and after.quarantined                                   # the disposition survived
    # the PROPERTY, not the proxy: the record renders under the unverified section, never the grounded one
    text = _mem(tmp_path).recall(U, "neighbour owes money").context
    assert "## UNVERIFIED THIRD-PARTY CLAIMS" in text and text.index(MARKER) > text.index("## UNVERIFIED THIRD-PARTY CLAIMS")
    assert "## RELEVANT DETAIL" not in text.split("## UNVERIFIED THIRD-PARTY CLAIMS")[0] or MARKER not in text.split("## UNVERIFIED THIRD-PARTY CLAIMS")[0]


def test_A_control_the_naive_treatment_promotes_the_claim(tmp_path):
    """The negative control research executed: relation replaced, disclosure
    untouched — the unverified claim is PROMOTED out of quarantine. Asserted as
    the wrong shape so the table shows what §4h refuses."""
    st = _mem(tmp_path).store
    st.add_edge(Edge(id="e-q", user_id=U, subject="neighbour", relation=QUARANTINE_RELATION,
                     object="says the user owes money", provenance=_prov()))
    _rewrite(st, "edges", "e-q", relation=MARKER)                     # relation replaced, disclosure untouched
    assert not _edge(st, "e-q").quarantined
    text = _mem(tmp_path).recall(U, "neighbour owes money").context                      # and it RENDERS as grounded — the manufactured assertion
    assert MARKER in text and "## UNVERIFIED THIRD-PARTY CLAIMS" not in text


def test_A_the_ruled_shape_survives_export_and_import(tmp_path):
    st = _mem(tmp_path).store
    st.add_edge(Edge(id="e-q", user_id=U, subject="neighbour", relation=QUARANTINE_RELATION,
                     object="says the user owes money", provenance=_prov()))
    _rewrite(st, "edges", "e-q", subject=MARKER, relation=MARKER, object=MARKER, **{"provenance.disclosure": "quarantined"})
    out = tmp_path / "x.jsonl"; st.export_memory(U, out) if hasattr(st, "export_memory") else None
    m2 = _mem(tmp_path, "n.db")
    from veracium.portability import export_memory, import_memory
    export_memory(st, U, out); import_memory(m2.store, out)
    imported = _edge(m2.store, "e-q")
    assert imported.quarantined and imported.relation == MARKER     # today's import carries the bytes and the disposition


# ---------------------------------------------------------------- row B: a prose-kind episode stored BEFORE the closure
def test_B_existing_prose_kind_is_retained_at_migration_and_readable(tmp_path):
    """§4h: the closure binds the WRITE path and the IMPORT boundary, never the
    read path; an existing prose kind is retained and stays readable."""
    # ROUND-6 FINDING 1: the prose kind was written here, which the recognised-kind
    # closure refuses at the write path. It is a frozen record now.
    st = _frozen_store(tmp_path)
    ep_id = _frozen_rows()["prose_kind"]
    ep = [e for e in st.episodes(U) if e.id == ep_id][0]
    assert ep.kind == "told me in confidence"                        # readable, retained
    _rewrite(st, "episodes", ep_id, summary=MARKER, kind=MARKER)    # redaction: prose kind → marker
    ep2 = [e for e in st.episodes(U) if e.id == ep_id][0]
    assert ep2.kind == MARKER and ep2.summary == MARKER              # the marker-valued record reads back today


@pytest.mark.xfail(strict=True, reason="0041 §4h / §11.4-bis: the recognised-kind closure binds the WRITE path; "
                                       "an ordinary write of a NEW prose kind is not yet refused")
def test_B_an_ordinary_write_of_a_new_prose_kind_is_refused_while_the_stored_one_stays(tmp_path):
    # ROUND-7 CORRECTION 1: the historical record was WRITTEN here through the
    # ordinary writer, so the closure fires at SETUP and `ep-new` is never
    # attempted — the refusal this test exists to assert is never reached. Its
    # neighbour was converted to the frozen fixture at round 6 and this one was
    # missed, which is the same sibling-left-behind defect as `test_row46`'s.
    st = _frozen_store(tmp_path)
    stored = _frozen_rows()["prose_kind"]
    with pytest.raises(Exception):
        st.add_episode(Episode(id="ep-new", user_id=U, date="2026-09-02", summary="s",
                               kind="another prose kind", provenance=_prov()))
    assert [e for e in st.episodes(U, include_retired=True) if e.id == stored][0].kind == "told me in confidence"


@pytest.mark.xfail(strict=True, reason="0041 §4h / §11.4-bis: the recognised-kind closure binds the IMPORT boundary; "
                                       "an import carrying a prose kind is not yet refused")
def test_B_an_import_carrying_a_prose_kind_is_refused(tmp_path):
    from veracium.portability import export_memory, import_memory
    # ROUND-6 FINDING 1, EXTENDED. The reviewer named three tests that built their
    # historical records through ordinary writers; this is a FOURTH of the same
    # shape, found by the class sweep rather than by the verdict. It wrote a prose
    # kind into its own source store to have something to export — the exact write
    # the closure refuses — so it too would have failed while preparing data. The
    # export source is the frozen store, which already carries a prose-kind
    # episode written before the restrictions.
    # ROUND-7 CORRECTION 2. This exported the WHOLE frozen store, which carries two
    # unattested marker rows — so the reviewer installed an import check that
    # rejects markers and does NO kind validation, and this test passed. Its
    # `pytest.raises` was satisfiable by a restriction that has nothing to do with
    # kinds. My round-6 fix caused it: pointing the export at the frozen store
    # wholesale made the setup legal and the assertion ambiguous in one move.
    #
    # The export is now ISOLATED to the prose-kind episode alone, so nothing in the
    # exported file can trigger a different rule. The marker rows stay frozen and
    # unexported; the control below proves the isolation rather than assuming it.
    src = _frozen_store(tmp_path)
    ep_id = _frozen_rows()["prose_kind"]
    out = tmp_path / "x.jsonl"
    export_memory(src, U, out)
    _isolate_jsonl(out, keep_id=ep_id)

    assert _exported_kinds(out) == {"told me in confidence"}, (
        f"the prose kind must survive the isolation and nothing else may; the "
        f"export carries {_exported_kinds(out)}")
    assert not _exported_markers(out), (
        f"ISOLATION CONTROL: no marker may remain in the exported file, or a marker "
        f"rule could satisfy the refusal below and this test would prove nothing "
        f"about kinds. Found: {_exported_markers(out)}")

    with pytest.raises(Exception):
        import_memory(_mem(tmp_path, "d.db").store, out)


@pytest.mark.xfail(strict=True, reason="0041 §4b attestation: a marker-valued kind validates only when a redaction "
                                       "record attests it; no attestation exists in the shipped code")
def test_B_a_marker_valued_kind_without_a_redaction_record_is_refused(tmp_path):
    """ROUND-5 FINDING 3, aligned with §4h's WRITE/READ distinction.

    The previous body asserted that the CONSTRUCTOR refuses. That is the wrong
    boundary and it contradicts the clause it was written to defend: §4h binds
    the recognised-kind closure to the WRITE path and the IMPORT boundary and
    NEVER to the read path, because a row already on disk has to load. A refusal
    in `Episode.__init__` is a refusal on every read, since loading a stored row
    goes through the same validator — it would make an existing record
    unreadable, which is the one outcome §4h forbids outright.

    So the closure is asserted where the spec puts it. The model ADMITS the value
    (the read path stays open, proved by reading a stored row back), and the
    write path refuses it while it is unattested."""
    # READ PATH: the model admits it, so a row already on disk still loads
    ep = Episode(id="ep-x", user_id=U, date="2026-09-01", summary="s", kind=MARKER, provenance=_prov())
    assert ep.kind == MARKER
    assert Episode.model_validate(json.loads(ep.model_dump_json())).kind == MARKER

    # WRITE PATH: the closure binds here, and only here
    st = _mem(tmp_path).store
    with pytest.raises(Exception):
        st.add_episode(ep)


# ---------------------------------------------------------------- row C: a pre-existing UNATTESTED marker row
def test_C_a_pre_existing_marker_row_is_admitted_and_is_not_a_redaction(tmp_path):
    """§4b's attestation rule: the marker is not self-authenticating; a stored
    row holding the marker bytes with no redaction record is an UNATTESTED
    marker — admitted at migration, conferring no redacted status. Today's
    store admits it (asserted); the status half is the xfail below."""
    st = _mem(tmp_path).store
    st.add_edge(Edge(id="e-m", user_id=U, subject="user", relation="works_as", object=MARKER, provenance=_prov()))
    e = _edge(st, "e-m")
    assert e.object == MARKER and e.active                             # admitted, live, untouched
    # an ORDINARY write to the marker-holding field SUCCEEDS: INV-11 is keyed on attested redaction, not on the bytes
    st.add_edge(Edge(id="e-m", user_id=U, subject="user", relation="works_as", object="Porto", provenance=_prov()))
    assert _edge(st, "e-m").object == "Porto"


@pytest.mark.xfail(strict=True, reason="0041 §4b: the migration REPORT enumerates unattested marker rows; "
                                       "`veracium.store.migration` has no such report, so the call below raises")
def test_C_the_migration_report_enumerates_unattested_marker_rows(tmp_path):
    """ROUND-5 FINDING 3, rewritten. The previous body was `assert hasattr(...)`,
    which the reviewer satisfied with a helper that always returns an empty list:
    a store FULL of unattested marker rows would have reported none and the check
    would have been green. What is asserted now is the report's CONTENTS against a
    store whose answer is known — two unattested rows and one ordinary row — so a
    report that returns [] fails, and so does one that returns everything."""
    from veracium.store import migration
    # ROUND-6 FINDING 1: this body WROTE its two marker rows through the ordinary
    # writer, which the write-path closure refuses — so the test failed while
    # PREPARING its data, in the one place a frozen fixture exists to serve.
    st = _frozen_store(tmp_path)
    man = _frozen_rows()

    rows = migration.unattested_marker_report(st)

    named = {r["target_id"] if isinstance(r, dict) else r.target_id for r in rows}
    assert named == {man["unattested_marker"], man["unattested_marker_2"]}, (
        "the report must name every row holding the marker bytes with no redaction "
        "record attesting them, and no others")
    # and it must say WHICH field carries the marker — a report that names the row
    # without the carrier cannot be acted on
    fields = {r["field"] if isinstance(r, dict) else r.field for r in rows}
    assert fields == {"object"}


@pytest.mark.xfail(strict=True, reason="0041 §4b / INV-11 keyed on ATTESTED redaction: after a redaction record attests the field, "
                                       "the same ordinary write is refused; no `redact` API exists, so the call below raises")
def test_C_after_attestation_the_same_write_is_refused(tmp_path):
    """ROUND-5 FINDING 3, rewritten. The previous body never called redaction and
    never created an attestation: its `Memory.redact` was a BARE EXPRESSION
    STATEMENT, a no-op the moment the attribute exists, and the refusal it then
    asserted would have had to come from somewhere else entirely.

    Worse, and beyond the verdict's wording: the write it expected to be refused
    SUCCEEDS today (an ordinary re-write of the same edge id is an upsert, proved
    in `test_C_a_pre_existing_marker_row_is_admitted_and_is_not_a_redaction`
    above). So the old body could never have passed, whatever landed — it would
    have gone on xfailing for a third unrelated reason and could never announce
    the implementation it was written to announce.

    This body performs the redaction, then asserts the refusal, and carries its
    own CONTROL: an unattested marker row stays writable. Without that control a
    blanket refusal of every write to a marker-holding field would satisfy the
    test while contradicting §4b."""
    # ROUND-6 FINDING 1: both the target and the control were WRITTEN here, and
    # the control wrote the marker through the ordinary writer — the exact write
    # the closure refuses. Both are frozen records now.
    m = _frozen_memory(tmp_path)
    st = m.store
    man = _frozen_rows()
    target = man["ordinary_edge"]

    _redact(m, edge_id=target, reason="subject_request")                # the attestation is CREATED here

    with pytest.raises(Exception):                                      # ... and only then refused
        st.add_edge(Edge(id=target, user_id=U, subject="user", relation="likes",
                         object="Porto", provenance=_prov()))

    # THE CONTROL, and it is the half that keeps the refusal honest: an UNATTESTED
    # marker confers nothing, so a write over one must still succeed (§4b). The
    # marker row is frozen; only the ordinary write over it happens here.
    un = man["unattested_marker"]
    st.add_edge(Edge(id=un, user_id=U, subject="user", relation="works_as",
                     object="Porto", provenance=_prov()))
    assert _edge(st, un).object == "Porto"


@pytest.mark.xfail(strict=True, reason="0041 §4b repeat calls: repeated=True with the original receipt, or reconstructed=True "
                                       "with explicit None where no receipt exists; no `redact` API exists, so the call below raises")
def test_F_a_repeated_call_returns_the_original_or_a_reconstructed_receipt(tmp_path):
    """ROUND-5 FINDING 3, rewritten. The previous body was `assert hasattr(Memory,
    "redact")`, which the reviewer satisfied with a no-op method — no receipt, no
    repeated flag, no event count. What is asserted now is §1041's contract:
    idempotent BY CONTENT, not by attempt. A second call writes NO new event and
    returns the ORIGINAL receipt with `repeated=True`.

    A stub that returns None fails at the first attribute read; a stub that
    returns a fresh receipt each time fails on the identity assertion; a stub that
    writes a second event fails on the count. That is the property the old body
    lacked: every way of being wrong is caught by something."""
    m = _mem(tmp_path)
    st = m.store
    st.add_edge(Edge(id="e-rep", user_id=U, subject="user", relation="works_as", object="a secret", provenance=_prov()))

    first = _redact(m, edge_id="e-rep", reason="subject_request")
    second = _redact(m, edge_id="e-rep", reason="subject_request")

    assert _field(first, "repeated") is False                          # the first call is not a repeat
    assert _field(second, "repeated") is True
    assert _field(second, "reconstructed") is False                    # a stored receipt exists, so nothing is reconstructed
    # the SAME receipt, not an equal-looking new one
    for name in ("redacted_kind", "target_id", "fields_cleared", "recorded_at"):
        assert _field(second, name) == _field(first, name), name
    # §4a's receipt, read by the names §1040 gives it. `fields_cleared` is the
    # CARRIERS the operation cleared — determined by the treatment map, not passed
    # in by the caller, which is why the call no longer names them.
    assert _field(first, "redacted_kind") == "edge"
    assert _field(first, "target_id") == "e-rep"
    assert list(_field(first, "fields_cleared")), (
        "the receipt must name the carriers actually cleared; §1040 lists them as a "
        "receipt field and the treatment map decides their content")
    # ... and the repeat wrote NO second event: a log of repeats is itself a signal
    assert _redaction_event_count(st, "e-rep") == 1


# ---------------------------------------------------------------- row D: a legacy prose reason stored BEFORE the closure
def test_D_a_legacy_prose_retired_reason_is_retained_at_migration_and_replaced_by_the_registry_value_at_redaction(tmp_path):
    """Rows 30/49 at v7: PRESERVE if in DISPOSITIONED_REASONS, else the registry
    value `redacted` — never the marker (the journal refuses it), never NULL
    (NULL un-retires the episode). Episode.retired_reason is a bare str today,
    so the value writes and `active` is unchanged."""
    st = _mem(tmp_path).store
    st.add_episode(Episode(id="ep-r", user_id=U, date="2026-09-01", summary="s", retired_reason="told me in confidence: hiv-positive",
                           provenance=_prov()))
    before = [e for e in st.episodes(U, include_retired=True) if e.id == "ep-r"][0]
    assert not before.active                                            # retained at migration, still retired
    _rewrite(st, "episodes", "ep-r", summary=MARKER, retired_reason="redacted")
    after = [e for e in st.episodes(U, include_retired=True) if e.id == "ep-r"][0]
    assert after.retired_reason == "redacted" and after.active == before.active


def test_D_a_legacy_prose_invalidation_reason_on_an_edge_is_retained_and_becomes_the_registry_value(tmp_path):
    """The edge side of rows 30/49. A pre-journal store could hold prose here;
    today's journal refuses writing prose OR `redacted` through the writer, so
    the fixture and the treatment are written to the row directly (the
    simulation), and the write-path half is the registry xfail below."""
    st = _mem(tmp_path).store
    st.add_edge(Edge(id="e-l", user_id=U, subject="user", relation="works_as", object="Porto", provenance=_prov()))
    _rewrite(st, "edges", "e-l", invalidated_at="2026-09-10T00:00:00Z", invalidation_reason="told me in confidence: hiv-positive")
    before = _edge(st, "e-l")
    assert not before.active and before.invalidation_reason.startswith("told me")     # retained verbatim
    _rewrite(st, "edges", "e-l", subject=MARKER, relation=MARKER, object=MARKER, invalidation_reason="redacted")
    after = _edge(st, "e-l")
    assert after.invalidation_reason == "redacted" and after.active == before.active


def test_D_a_source_revocation_reason_holding_the_callers_sentence_is_replaced(tmp_path):
    """source_revocations.reason has no vocabulary to preserve (round-4 F3,
    executed): it is REPLACED as ordinary prose; the effect's registry value on
    the affected records is preserved."""
    # ROUND-7 CORRECTION 1: this created a NEW prose reason with `revoke_source`,
    # which the finalised vocabulary refuses — the setup fails before the claim is
    # reached. The frozen fixture has carried a historical prose revocation since
    # round 6 and this test did not read it. It now does, WITH the source-linked
    # edge the round-7 reviewer asked for: a revocation with nothing attached
    # cannot exercise the second half of the claim, which is about the affected
    # record rather than about the reason.
    st = _frozen_store(tmp_path)
    man = _frozen_rows()
    digest, linked = man["prose_source_revocation"], man["source_linked_edge"]

    stored = st._conn.execute(
        "SELECT reason FROM source_revocations WHERE identity_digest=?", (digest,)).fetchone()[0]
    assert stored == "she asked me to drop everything from that address", (
        "the frozen revocation must still carry the caller's PROSE — it is the last "
        "such row creatable, since the vocabulary now closes the field at the writer")
    assert _edge(st, linked).invalidation_reason == "revoked_source", (
        "and the affected record must already carry the REGISTRY value, which is what "
        "the redaction must preserve while the prose is replaced")

    # the treatment: prose replaced, the effect's registry value untouched
    st._conn.execute("UPDATE source_revocations SET reason=? WHERE identity_digest=?",
                     (MARKER, digest))
    st._conn.commit()
    assert st._conn.execute(
        "SELECT reason FROM source_revocations WHERE identity_digest=?", (digest,)).fetchone()[0] == MARKER
    assert _edge(st, linked).invalidation_reason == "revoked_source"


def test_D_a_registry_reason_is_preserved(tmp_path):
    st = _mem(tmp_path).store
    st.add_episode(Episode(id="ep-s", user_id=U, date="2026-09-01", summary="s", retired_reason="superseded", provenance=_prov()))
    _rewrite(st, "episodes", "ep-s", summary=MARKER)
    assert [e for e in st.episodes(U, include_retired=True) if e.id == "ep-s"][0].retired_reason == "superseded"


@pytest.mark.xfail(strict=True, reason="0041 rows 30/49: `redacted` is a NEW registry value — DISPOSITIONED_REASONS and the "
                                       "as-of RESOLUTION (an import-time equality gate) must carry it together; implementation follows acceptance")
def test_the_redacted_reason_is_dispositioned_twice():
    """ROUND-5 FINDING 3: assert the COMPLETE disposition, not its first element.

    The previous body read `RESOLUTION["redacted"][0] == NOT_RETURNABLE` and
    stopped. Every entry in that table is a PAIR — an outcome and the tag the
    as-of reader surfaces — and the spec promises both:
    `(NOT_RETURNABLE, TAG_REDACTED_EXCLUDED)`, following `revoked_source`'s
    precedent, since both are rights-driven removals. Asserting only the outcome
    would accept an entry whose tag was `in-interval`, which would report a
    redacted answer as an ordinary historical one.

    The tag is bound to the module's own symbol rather than to a guessed literal,
    for the reason the `_redact` adapter gives: this test binds the contract, not
    the spelling."""
    from veracium.asof import resolve
    from veracium.asof.resolve import NOT_RETURNABLE, RESOLUTION

    assert "redacted" in DISPOSITIONED_REASONS
    assert RESOLUTION["redacted"] == (NOT_RETURNABLE, resolve.TAG_REDACTED_EXCLUDED)
    # the tag is the redaction's OWN, not another disposition's borrowed
    assert resolve.TAG_REDACTED_EXCLUDED not in {
        v[1] for k, v in RESOLUTION.items() if k != "redacted"}
    # and the import-time coupling the two registries live under still holds
    assert set(RESOLUTION) == set(DISPOSITIONED_REASONS)


# ---------------------------------------------------------------- the FROZEN pre-restriction store
#
# Round 5's standing artifact ask. Every row above is built by WRITING it through
# today's store, and the moment 0041's write-path closure lands those setup writes
# are refused — the evidence that existing records survive would be destroyed by
# the change it exists to check. `specs/evidence/0041/pre_restriction_fixture.py`
# freezes a store written before the closure; these tests copy the bytes.

_FROZEN = pathlib.Path(__file__).resolve().parents[1] / "specs" / "evidence" / "0041"


def _strict_json(text):
    """Duplicate JSON members REFUSE at parse (0026-EVIDENCE-R8-1). The manifest
    read here decides whether the frozen fixture is intact, so a second `sha256`
    member silently winning would authenticate the wrong bytes."""
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError(f"duplicate JSON member {k!r}")
            out[k] = v
        return out
    return json.loads(text, object_pairs_hook=pairs)


def _decoded_values(path):
    """Every string VALUE in an exported jsonl, DECODED — never the raw text.

    ROUND-8 FOLLOW-UP 1, found by the reviewer. The isolation control asserted
    `MARKER not in path.read_text()` against the file's raw bytes, and **JSON
    escapes the marker's NUL characters**:

        raw          '\x00veracium:redacted\x00'
        in the file  '\\u0000veracium:redacted\\u0000'

    so that assertion is TRUE for every JSON export whatever it contains. **The
    control could never have failed**; a file full of markers passed it. The
    unfailable-check class, in the control written to prove isolation — one round
    after the same seat's fixture-checker control was found comparing digests
    instead of running the checker. Twice the control was written and the control
    was not tested. `test_the_isolation_control_detects_a_marker_bearing_export`
    is the demonstration the reviewer asked for."""
    import json as _json
    out = []

    def walk(obj):
        if isinstance(obj, str):
            out.append(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                out.append(k)
                walk(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                walk(v)

    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            walk(_json.loads(line))
        except ValueError:
            out.append(line)
    return out


def _exported_markers(path):
    """The decoded values carrying the marker — the LIST, so a failure names what
    it found rather than only that it found something."""
    return [v for v in _decoded_values(path) if MARKER in v]


def _exported_kinds(path):
    """The `kind` values the export's RECORDS carry, decoded.

    Record lines only: the export's metadata header carries its own `kind`
    ("veracium-export"), which the round-8 reviewer's description accounts for —
    *"exactly the metadata header and the intended prose-kind episode"*. A header
    is not a record, and counting it fails a correct export."""
    import json as _json
    kinds = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            obj = _json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and "id" in obj and isinstance(obj.get("kind"), str):
            kinds.add(obj["kind"])
    return kinds


def _isolate_jsonl(path, *, keep_id):
    """Keep only the record named, plus any line that is not a record.

    ROUND-7 CORRECTION 2. An export of the whole frozen store carries every shape
    it holds, so a refusal asserted over it can be caused by ANY of them. A test
    that expects rejection for ONE reason must not hand the importer a file with
    three other reasons in it. Lines without an `id` (headers, manifests) are kept
    so the file stays well-formed; the caller asserts what survived."""
    import json as _json
    kept = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            obj = _json.loads(line)
        except ValueError:
            kept.append(line)
            continue
        if not isinstance(obj, dict) or "id" not in obj or obj.get("id") == keep_id:
            kept.append(line)
    path.write_text("\n".join(kept) + "\n")


def _frozen_memory(tmp_path):
    """A `Memory` over a writable copy of the frozen pre-restriction store — the
    sibling of `_frozen_store`, for tests that need the API and not the store."""
    dst = tmp_path / "frozen.db"
    shutil.copy2(_FROZEN / "pre_restriction.sqlite", dst)
    return _mem(tmp_path, name="frozen.db")


def _frozen_rows():
    """The frozen store's named shapes, from its manifest. A test names a shape
    and the manifest says which row carries it, so a rebuild cannot silently
    leave a test pointing at an id that no longer exists."""
    return _strict_json((_FROZEN / "pre_restriction_manifest.json").read_text())["rows"]


def _frozen_store(tmp_path):
    """A writable copy of the frozen pre-restriction store.

    Copied, never opened in place: an observer must not share a directory with
    the thing it observes, and sqlite would leave -wal and -shm beside a fixture
    whose digest is asserted."""
    dst = tmp_path / "frozen.db"
    shutil.copy2(_FROZEN / "pre_restriction.sqlite", dst)
    return _mem(tmp_path, name="frozen.db").store


def test_the_frozen_pre_restriction_store_matches_its_manifest(tmp_path):
    """THE MUTATION MATRIX for `specs/evidence/0041/pre_restriction_fixture.py`.

    The fixture is only evidence while its bytes are the frozen ones: a silent
    regeneration AFTER 0041's write-path closure lands would produce a store the
    closure ALLOWED, which is the opposite of what a pre-restriction fixture is
    for, and nothing else in the tree would notice.

    So the checker is run, both ways. `--check` must pass on the real bytes, and
    it must refuse a single flipped byte — a digest check that cannot be made to
    fail is the unfailable-check class, and this one guards an artifact whose
    whole value is that it has not changed."""
    import subprocess
    import sys

    script = _FROZEN / "pre_restriction_fixture.py"

    ok = subprocess.run([sys.executable, str(script), "--check"],
                        capture_output=True, text=True)
    assert ok.returncode == 0, f"pre_restriction_fixture.py --check refused the frozen bytes: {ok.stdout}{ok.stderr}"

    # NEGATIVE CONTROL: one byte, and the checker must say so
    man = _strict_json((_FROZEN / "pre_restriction_manifest.json").read_text())
    raw = bytearray((_FROZEN / "pre_restriction.sqlite").read_bytes())
    assert hashlib.sha256(bytes(raw)).hexdigest() == man["sha256"]
    assert len(raw) == man["bytes"]
    # ROUND-6 FINDING 2. This half used to flip a byte and compare two sha256
    # digests, which is a property of sha256 and not of the checker: the reviewer
    # replaced the subprocess result with unconditional success and the test still
    # passed. It was written in the same commit as the rule that a check without a
    # working negative control certifies nothing. The checker is now RUN on the
    # altered bytes, in a throwaway copy of its own directory, and the rejection is
    # read from ITS exit code and ITS message.
    copy = tmp_path / "evidence"
    copy.mkdir()
    for name in ("pre_restriction_fixture.py", "pre_restriction.sqlite",
                 "pre_restriction_manifest.json"):
        (copy / name).write_bytes((_FROZEN / name).read_bytes())
    b = bytearray((copy / "pre_restriction.sqlite").read_bytes())
    b[-1] ^= 0xFF
    (copy / "pre_restriction.sqlite").write_bytes(bytes(b))

    bad = subprocess.run([sys.executable, str(copy / "pre_restriction_fixture.py"), "--check"],
                         capture_output=True, text=True)
    assert bad.returncode == 1, (
        f"the checker ACCEPTED a store with a flipped byte (exit {bad.returncode}); a "
        f"digest check that cannot be made to fail is the unfailable-check class, and "
        f"this one guards an artifact whose whole value is that it has not changed")
    assert "CHANGED" in bad.stdout.upper(), (
        f"the checker refused the altered bytes but did not SAY what was wrong; its "
        f"output was {bad.stdout.strip()!r}")


def test_the_frozen_store_carries_every_pre_restriction_shape_the_table_needs(tmp_path):
    """Named shapes, read back through the product's own readers — a fixture whose
    rows cannot be loaded is not a fixture."""
    st = _frozen_store(tmp_path)
    man = _strict_json((_FROZEN / "pre_restriction_manifest.json").read_text())
    edges = {e.id: e for e in st.edges(U, active_only=False, include_quarantined=True)}
    eps = {e.id: e for e in st.episodes(U, include_retired=True)}
    assert man["rows"]["relation_only_quarantine"] in edges
    assert edges[man["rows"]["unattested_marker"]].object == MARKER
    assert eps[man["rows"]["prose_kind"]].kind == "told me in confidence"
    assert eps[man["rows"]["prose_retired_reason"]].retired_reason == "she asked me not to repeat it"
    assert eps[man["rows"]["registry_retired_reason"]].retired_reason == "superseded"


def test_rows30_49_on_a_frozen_record_absence_survives_and_prose_does_not(tmp_path):
    """ROUND-5 FINDING 1, on a record stored before the restrictions.

    v7 fixed "NULL un-retires the episode" and broke the opposite direction: row
    49's two-case rule put ABSENCE on the replace side, so an active episode's
    `retired_reason=None` became `"redacted"` and `active` went True to False —
    a derived disposition changed by a redaction, which is exactly what §4h
    forbids. The reviewer reproduced it on the packaged model; this asserts the
    corrected three-case rule on a FROZEN pre-restriction record, which is the
    only place the claim means anything.

    Absent stays absent. Registered stays registered. Only prose is replaced."""
    st = _frozen_store(tmp_path)
    man = _strict_json((_FROZEN / "pre_restriction_manifest.json").read_text())
    eps = {e.id: e for e in st.episodes(U, include_retired=True)}

    active = eps[man["rows"]["active_episode_absent_reason"]]
    assert active.retired_reason is None and active.active is True and active.assertable

    # ABSENT -> ABSENT: the treatment touches content, and absence is not content
    _rewrite(st, "episodes", active.id, summary=MARKER)
    after = {e.id: e for e in st.episodes(U, include_retired=True)}[active.id]
    assert after.retired_reason is None, "row 49 must not write into an absent reason"
    assert after.active is True and after.assertable, "a redaction may not retire an episode"

    # REGISTERED -> unchanged
    reg = eps[man["rows"]["registry_retired_reason"]]
    _rewrite(st, "episodes", reg.id, summary=MARKER)
    assert {e.id: e for e in st.episodes(U, include_retired=True)}[reg.id].retired_reason == "superseded"

    # PROSE -> the registry value, and the disposition it already had is unchanged
    prose = eps[man["rows"]["prose_retired_reason"]]
    assert prose.active is False
    _rewrite(st, "episodes", prose.id, summary=MARKER, retired_reason="redacted")
    replaced = {e.id: e for e in st.episodes(U, include_retired=True)}[prose.id]
    assert replaced.retired_reason == "redacted" and replaced.active is False


def test_the_isolation_control_detects_a_marker_bearing_export(tmp_path):
    """ROUND-8 FOLLOW-UP 1's DEMONSTRATION, asked for in those words: *"strengthen
    the check and demonstrate that it detects a marker-bearing export."*

    The old control could not. `MARKER not in path.read_text()` is true of every
    JSON export ever written, because JSON escapes the marker's NUL bytes, so the
    assertion held whether or not markers were present and the isolation it
    claimed to prove rested on nothing.

    This is the control for the control: it exports the FULL frozen store, which
    carries two unattested marker rows, and requires the check to FIND them. If it
    ever passes vacuously the isolation assertion beside it is worthless again, and
    the failure surfaces here rather than in a reviewer's message three rounds on."""
    from veracium.portability import export_memory

    src = _frozen_store(tmp_path)
    full = tmp_path / "full.jsonl"
    export_memory(src, U, full)

    assert MARKER not in full.read_text(), (
        "THE OLD CHECK, SHOWN NOT FIRING: markers ARE present in this export and a "
        "raw-text search does not see them, because JSON escapes NUL. This "
        "assertion passing is the defect being demonstrated, not a property")

    found = _exported_markers(full)
    assert len(found) >= 2, (
        f"the decoded check must FIND the frozen store's unattested markers; it "
        f"found {len(found)}. A control that cannot detect what it excludes is not "
        f"a control")

    isolated = tmp_path / "isolated.jsonl"
    export_memory(src, U, isolated)
    _isolate_jsonl(isolated, keep_id=_frozen_rows()["prose_kind"])
    assert not _exported_markers(isolated), (
        "and it must find NOTHING once the export is isolated, or it would refuse "
        "the correct case too")
