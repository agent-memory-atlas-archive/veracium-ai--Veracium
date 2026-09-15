"""specs/0041 — the EXECUTABLE TRANSITION TABLE (the round-4 verdict's artifact ask):
existing records → new writes → redaction → import → repeated calls.

Every fixture here is a record stored BEFORE the restrictions the spec adds —
through today's store, under today's model — because a transition claim proved on
a record built under the new model proves nothing (§4h's fixture rule). Each row
applies the ruled treatment through the store's own write paths and asks the
product's readers and predicates whether the record's OPERATIONAL disposition
survived. Rows the shipped code cannot yet honour are STRICT xfails, red first.
"""
import json

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
    st = _mem(tmp_path).store
    st.add_episode(Episode(id="ep-p", user_id=U, date="2026-09-01", summary="s", kind="told me in confidence", provenance=_prov()))
    ep = [e for e in st.episodes(U) if e.id == "ep-p"][0]
    assert ep.kind == "told me in confidence"                        # readable, retained
    _rewrite(st, "episodes", "ep-p", summary=MARKER, kind=MARKER)    # redaction: prose kind → marker
    ep2 = [e for e in st.episodes(U) if e.id == "ep-p"][0]
    assert ep2.kind == MARKER and ep2.summary == MARKER              # the marker-valued record reads back today


@pytest.mark.xfail(strict=True, reason="0041 §4h / §11.4-bis: the recognised-kind closure binds the WRITE path; "
                                       "an ordinary write of a NEW prose kind is not yet refused")
def test_B_an_ordinary_write_of_a_new_prose_kind_is_refused_while_the_stored_one_stays(tmp_path):
    st = _mem(tmp_path).store
    st.add_episode(Episode(id="ep-old", user_id=U, date="2026-09-01", summary="s", kind="told me in confidence", provenance=_prov()))
    with pytest.raises(Exception):
        st.add_episode(Episode(id="ep-new", user_id=U, date="2026-09-02", summary="s", kind="another prose kind", provenance=_prov()))
    assert [e for e in st.episodes(U) if e.id == "ep-old"][0].kind == "told me in confidence"


@pytest.mark.xfail(strict=True, reason="0041 §4h / §11.4-bis: the recognised-kind closure binds the IMPORT boundary; "
                                       "an import carrying a prose kind is not yet refused")
def test_B_an_import_carrying_a_prose_kind_is_refused(tmp_path):
    from veracium.portability import export_memory, import_memory
    src = _mem(tmp_path, "s.db").store
    src.add_episode(Episode(id="ep-p", user_id=U, date="2026-09-01", summary="s", kind="told me in confidence", provenance=_prov()))
    out = tmp_path / "x.jsonl"; export_memory(src, U, out)
    with pytest.raises(Exception):
        import_memory(_mem(tmp_path, "d.db").store, out)


@pytest.mark.xfail(strict=True, reason="0041 §4b attestation: a marker-valued kind validates only when a redaction "
                                       "record attests it; no attestation exists in the shipped code")
def test_B_a_marker_valued_kind_without_a_redaction_record_is_refused():
    with pytest.raises(Exception):
        Episode(id="ep-x", user_id=U, date="2026-09-01", summary="s", kind=MARKER, provenance=_prov())


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


@pytest.mark.xfail(strict=True, reason="0041 §4b: the migration REPORT enumerates unattested marker rows; no such report exists")
def test_C_the_migration_report_enumerates_unattested_marker_rows(tmp_path):
    from veracium.store import migration
    assert hasattr(migration, "unattested_marker_report")


@pytest.mark.xfail(strict=True, reason="0041 §4b / INV-11 keyed on ATTESTED redaction: after a redaction record attests the field, "
                                       "the same ordinary write is refused; no `redact` API or redaction record exists in the shipped code")
def test_C_after_attestation_the_same_write_is_refused(tmp_path):
    st = _mem(tmp_path).store
    st.add_edge(Edge(id="e-m", user_id=U, subject="user", relation="works_as", object="secret", provenance=_prov()))
    Memory.redact                                                       # the API, then the attested refusal
    with pytest.raises(Exception):
        st.add_edge(Edge(id="e-m", user_id=U, subject="user", relation="works_as", object="Porto", provenance=_prov()))


@pytest.mark.xfail(strict=True, reason="0041 §4b repeat calls: repeated=True with the original receipt, or reconstructed=True "
                                       "with explicit None where no receipt exists; an unattested marker is a FIRST redaction; no `redact` API exists")
def test_F_a_repeated_call_returns_the_original_or_a_reconstructed_receipt():
    assert hasattr(Memory, "redact")


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
    from veracium.source_identity import resolve_origin, source_identity_digest
    from veracium.store import revocation as rv
    st = _mem(tmp_path).store
    st.add_edge(Edge(id="e-s", user_id=U, subject="user", relation="works_as", object="Porto", provenance=_prov(source_id="mb-x")))
    digest = source_identity_digest(resolve_origin(None, st.local_origin()), "mb-x")
    rv.revoke_source(st, U, digest, "revoke", "the mailbox was compromised on 3 March", "2026-09-15T00:00:00Z")
    st._conn.execute("UPDATE source_revocations SET reason=? WHERE user_id=?", (MARKER, U)); st._conn.commit()
    assert st._conn.execute("SELECT reason FROM source_revocations WHERE user_id=?", (U,)).fetchone()[0] == MARKER
    assert _edge(st, "e-s").invalidation_reason == "revoked_source"


def test_D_a_registry_reason_is_preserved(tmp_path):
    st = _mem(tmp_path).store
    st.add_episode(Episode(id="ep-s", user_id=U, date="2026-09-01", summary="s", retired_reason="superseded", provenance=_prov()))
    _rewrite(st, "episodes", "ep-s", summary=MARKER)
    assert [e for e in st.episodes(U, include_retired=True) if e.id == "ep-s"][0].retired_reason == "superseded"


@pytest.mark.xfail(strict=True, reason="0041 rows 30/49: `redacted` is a NEW registry value — DISPOSITIONED_REASONS and the "
                                       "as-of RESOLUTION (an import-time equality gate) must carry it together; implementation follows acceptance")
def test_the_redacted_reason_is_dispositioned_twice():
    from veracium.asof.resolve import NOT_RETURNABLE, RESOLUTION
    assert "redacted" in DISPOSITIONED_REASONS and RESOLUTION["redacted"][0] == NOT_RETURNABLE
