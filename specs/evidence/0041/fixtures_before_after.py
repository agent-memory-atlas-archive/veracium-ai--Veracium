"""0041 round 3 — VALIDATED before/after record fixtures (the round-2 verdict's first
artifact ask, corrected for round-3 F5). Every "after" record is built by FULL
model validation of a complete dump (`Model.model_validate(...)`) — never
`model_copy(update=)`, which validates nothing — and where an operation-specific
validator exists for the record (the ledger's absorption-site payload), it is run
too and its verdict printed. A shape the model or the validator refuses is printed
as REFUSED, never assumed. Nothing here redacts anything.

Run from the repo root: .venv/bin/python specs/evidence/0041/fixtures_before_after.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
from veracium.contribution import validate_absorption_payload
from veracium.schema import (AgreementRecord, Confirmation, ContributionRecord, Disclosure, Edge, Episode, EvidenceAuthor,
                             Provenance)

MARKER = "\x00veracium:redacted\x00"
PROV = dict(author_of_evidence="user", evidence_ref="ev-12", disclosure="mentionable")


def validated(label, model, data, *, also=None):
    """Full validation through the model, then the operation-specific validator if given."""
    try:
        obj = model.model_validate(data)
    except Exception as e:
        print(f"  REFUSED  {label}: {type(e).__name__}: {str(e).splitlines()[0][:80]}")
        return None
    if also is not None:
        try:
            also(obj)
        except Exception as e:
            print(f"  REFUSED  {label}: model VALID but the operation validator refuses: {str(e)[:80]}")
            return None
    print(f"  VALID    {label}" + ("  (model + operation validator)" if also else "  (model)"))
    return obj


def after(obj, **changes):
    """A complete dump with the changes applied, re-validated from scratch."""
    d = obj.model_dump(mode="json")
    for k, v in changes.items():
        if "." in k:
            a, b = k.split(".", 1); d[a][b] = v
        else:
            d[k] = v
    return d


print("A. edge — before")
before = validated("before: a one-marker agreement, a prose original_relation, one outcome key", Edge, dict(
    id="e-7c1a", user_id="u", subject="user", relation="has_condition", object="hiv-positive since 2019",
    note="told me in confidence", original_relation="told me in confidence about the diagnosis",
    agreement=dict(markers=["clinic-letter"], direction="inbound", lexicon="lex-v1"),
    outcome_counts={"confirmed": 1}, provenance=PROV))
print("B. edge — after, per the treatment map (REPLACE content leaves; CLEAR outcome_counts; PRESERVE ids, timestamps,")
print("   provenance.evidence_ref and the agreement's direction/lexicon; markers REPLACED per entry)")
a1 = validated("after (arity-1 markers)", Edge, after(before, subject=MARKER, relation=MARKER, object=MARKER, note=MARKER,
                                                     original_relation=MARKER, outcome_counts={},
                                                     agreement=dict(markers=[MARKER], direction="inbound", lexicon="lex-v1")))
if a1 is not None:
    print("   identity preserved:", a1.id == before.id, "| evidence_ref preserved:", a1.provenance.evidence_ref == "ev-12",
          "| every content leaf is the marker:", all(getattr(a1, f) == MARKER for f in ("subject", "relation", "object", "note", "original_relation")),
          "| outcome_counts cleared:", a1.outcome_counts == {})
print("C. the BLOCKED row — a two-marker agreement redacted per entry (§2d-iii-bis: INVALID until the uniqueness validator admits repeats)")
validated("after (arity-2 markers) — REFUSED until 0041 tranche 3 (2026-09-19), when the uniqueness validator began admitting repeated REDACTION markers (row 3)", AgreementRecord, dict(markers=[MARKER, MARKER], direction="inbound", lexicon="lex-v1"))
validated("after (arity-2 markers) — a repeated NON-marker, still REFUSED (the amendment admits the marker and nothing else)", AgreementRecord, dict(markers=["clinic-letter", "clinic-letter"], direction="inbound", lexicon="lex-v1"))
print("D. episode — before / after (summary REPLACED; kind PRESERVED when it is a recognised operational kind and REPLACED when prose —")
print("   round-3 F1; retired_reason=None stays None — round-3 F2: absence is absence; a legacy PROSE retired_reason → marker)")
ep = validated("before", Episode, dict(id="ep-31", user_id="u", date="2026-09-01", summary="User disclosed a diagnosis and asked that it not be shared.", kind="interaction", provenance=PROV))
e1 = validated("after (summary → marker; kind 'interaction' PRESERVED; retired_reason None PRESERVED)", Episode, after(ep, summary=MARKER))
if e1 is not None:
    print("   kind preserved:", e1.kind == "interaction", "| still active (retired_reason None):", e1.active)
validated("after (a PROSE kind → marker)", Episode, after(ep, summary=MARKER, kind=MARKER))
eo = validated("an OUTCOME link before", Episode, dict(id="ep-o", user_id="u", date="2026-09-01", summary="used", kind="outcome", edge_id="e-7c1a", outcome="challenged", seq=2, provenance=PROV))
e2 = validated("after (summary → marker; kind 'outcome' PRESERVED — the chain discriminator survives)", Episode, after(eo, summary=MARKER))
if e2 is not None:
    print("   kind preserved:", e2.kind == "outcome", "| seq preserved:", e2.seq == 2)
legacy = validated("a retired episode with a legacy PROSE reason, before", Episode, after(ep, retired_reason="told me in confidence: hiv-positive"))
e3 = validated("after (legacy prose retired_reason → marker; active stays False as it was)", Episode, after(legacy, summary=MARKER, retired_reason=MARKER))
if e3 is not None:
    print("   active unchanged by the redaction:", legacy.active == e3.active == False)
print("E. the receipt carries no content digest (round-2 F5): the redaction receipt names cleared CARRIERS by field path, never the removed digest")
receipt = {"redacted_kind": "edge", "target_id": "e-7c1a", "reason": "subject_request",
           "carriers_cleared": ["edges.subject", "edges.relation", "edges.object", "json.subject", "json.relation", "json.object",
                                "json.note", "json.original_relation", "json.agreement.markers[0]", "json.outcome_counts",
                                "edge_event.state[seq=4]", "edge_event.state[seq=9]", "edge_embedding[row deleted]"],
           "receipts_complete": False, "domains_not_recomputed": ["veracium.supersession-request.v2"], "receipts_cleared": []}
print("   receipt mentions no 64-hex digest:", not any(len(tok) == 64 and all(c in "0123456789abcdef" for c in tok)
                                                       for tok in json.dumps(receipt).replace('"', ' ').replace(",", " ").split()))
print("F. the digest rows (ruled v5): the ORACLE goes, the RECORD stays — CLEAR where the field is Optional, REPLACE where CLEAR has no")
print("   valid shape (Confirmation.request_digest is a required bare str). The ledger record is validated by the model AND the absorption-site validator (round-3 F5).")
SIDE = {"observed_at": "2026-09-01T00:00:00Z", "confidence": 1.0, "valid_from": "2026-09-01T00:00:00Z", "disclosure": "mentionable"}
led = validated("ContributionRecord before (a REAL absorption payload)", ContributionRecord, dict(
    id="c-1", user_id="u", survivor_type="edge", survivor_id="e-7c1a", site="absorption",
    identity_digest="a" * 64, evidence_ref_digest="b" * 64, payload={"base": dict(SIDE), "contributor": dict(SIDE)}, op_key="k",
    created_at="2026-09-15T00:00:00Z", contributor_type="edge", contributor_ref="e-prior"), also=lambda r: validate_absorption_payload(r.payload))
if led is not None:
    validated("ContributionRecord after (identity_digest / evidence_ref_digest → None; payload untouched)", ContributionRecord,
              after(led, identity_digest=None, evidence_ref_digest=None), also=lambda r: validate_absorption_payload(r.payload))
validated("ContributionRecord with payload={} — the round-2 fixture (expected REFUSED by the operation validator)", ContributionRecord, dict(
    id="c-2", user_id="u", survivor_type="edge", survivor_id="e-7c1a", site="absorption", identity_digest=None, evidence_ref_digest=None,
    payload={}, op_key="k", created_at="2026-09-15T00:00:00Z", contributor_type="edge", contributor_ref="e-prior"),
    also=lambda r: validate_absorption_payload(r.payload))
conf = dict(id="c-1", user_id="u", edge_id="e-7c1a", confirmed_at="2026-09-15T00:00:00Z", actor="user", call_path="host_api", correlation_id="corr-1")
validated("Confirmation.request_digest → None  (expected REFUSED: required bare str)", Confirmation, {**conf, "request_digest": None})
validated("Confirmation.request_digest → MARKER (the ruling)", Confirmation, {**conf, "request_digest": MARKER})
