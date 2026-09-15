"""0041 round 3 — VALIDATED before/after record fixtures (the round-2 verdict's first
artifact ask). Each fixture is built from the ruled treatment map (§2d-ii at v5), then
VALIDATED under the model: a resulting shape the model refuses is printed as REFUSED,
never assumed. Nothing here redacts anything — it constructs the shapes the contract
names and asks the model whether they exist.

Run from the repo root: .venv/bin/python specs/evidence/0041/fixtures_before_after.py
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
from veracium.schema import (AgreementRecord, Confirmation, ContributionRecord, Disclosure, Edge, Episode, EvidenceAuthor,
                             Provenance)

MARKER = "\x00veracium:redacted\x00"
PROV = Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev-12", disclosure=Disclosure.MENTIONABLE)


def show(label, fn):
    try:
        obj = fn()
        print(f"  VALID    {label}")
        return obj
    except Exception as e:                       # the model's refusal IS the result
        print(f"  REFUSED  {label}: {type(e).__name__}: {str(e).splitlines()[0][:80]}")
        return None


print("A. edge — before")
before = show("before: a one-marker agreement, a prose original_relation, one outcome key",
              lambda: Edge(id="e-7c1a", user_id="u", subject="user", relation="has_condition",
                           object="hiv-positive since 2019", note="told me in confidence",
                           original_relation="told me in confidence about the diagnosis",
                           agreement=AgreementRecord(markers=["clinic-letter"], direction="inbound", lexicon="lex-v1"),
                           outcome_counts={"confirmed": 1}, provenance=PROV))
print("B. edge — after, per the treatment map (REPLACE content leaves; CLEAR outcome_counts; PRESERVE ids, timestamps,")
print("   provenance.evidence_ref and the agreement's direction/lexicon; markers REPLACED per entry)")
after = show("after (arity-1 markers)",
             lambda: before.model_copy(update={"subject": MARKER, "relation": MARKER, "object": MARKER, "note": MARKER,
                                               "original_relation": MARKER, "outcome_counts": {},
                                               "agreement": AgreementRecord(markers=[MARKER], direction="inbound", lexicon="lex-v1")}))
if after is not None:
    print("   identity preserved:", after.id == before.id, "| evidence_ref preserved:", after.provenance.evidence_ref == "ev-12",
          "| every content leaf is the marker:", all(getattr(after, f) == MARKER for f in ("subject", "relation", "object", "note", "original_relation")),
          "| outcome_counts cleared:", after.outcome_counts == {})
print("C. the BLOCKED row — a two-marker agreement redacted per entry (§2d-ii: INVALID until the uniqueness validator admits repeats)")
show("after (arity-2 markers) — expected REFUSED today", lambda: AgreementRecord(markers=[MARKER, MARKER], direction="inbound", lexicon="lex-v1"))
print("D. episode — before / after (summary REPLACED; kind REPLACED when it is prose, PRESERVED when it is the product's literal;")
print("   retired_reason PRESERVED if vocabulary, REPLACED if legacy prose)")
ep = show("before", lambda: Episode(id="ep-31", user_id="u", date="2026-09-01", summary="User disclosed a diagnosis and asked that it not be shared.",
                                     kind="interaction", provenance=PROV))
show("after (summary → marker; kind 'interaction' preserved)", lambda: ep.model_copy(update={"summary": MARKER}))
show("after (a PROSE kind → marker)", lambda: ep.model_copy(update={"summary": MARKER, "kind": MARKER}))
show("after (a legacy prose retired_reason → marker)", lambda: ep.model_copy(update={"summary": MARKER, "retired_reason": MARKER}))
print("E. the receipt carries no content digest (round-2 F5): the redaction receipt names cleared CARRIERS by field path, never the removed digest")
receipt = {"redacted_kind": "edge", "target_id": "e-7c1a", "reason": "subject_request",
           "carriers_cleared": ["edges.subject", "edges.relation", "edges.object", "json.subject", "json.relation", "json.object",
                                "json.note", "json.original_relation", "json.agreement.markers[0]", "json.outcome_counts",
                                "edge_event.state[seq=4]", "edge_event.state[seq=9]", "edge_embedding[row deleted]"],
           "receipts_complete": False, "domains_not_recomputed": ["veracium.supersession-request.v2"], "receipts_cleared": []}
print("   receipt mentions no 64-hex digest:", not any(len(tok) == 64 and all(c in "0123456789abcdef" for c in tok)
                                                       for tok in json.dumps(receipt).replace('"', ' ').replace(",", " ").split()))

print("F. the digest rows (round-2 F5/F6, ruled v5): the ORACLE goes, the RECORD stays — CLEAR where the field is Optional,")
print("   REPLACE where CLEAR has no valid shape (Confirmation.request_digest is a required bare str)")
show("ContributionRecord.identity_digest / evidence_ref_digest → None",
     lambda: ContributionRecord(id="c-1", user_id="u", survivor_type="edge", survivor_id="e-7c1a", site="absorption",
                                identity_digest=None, evidence_ref_digest=None, payload={}, op_key="k", created_at="2026-09-15T00:00:00Z",
                                contributor_type="edge", contributor_ref="e-prior"))
conf = dict(id="c-1", user_id="u", edge_id="e-7c1a", confirmed_at="2026-09-15T00:00:00Z", actor="user", call_path="host_api", correlation_id="corr-1")
show("Confirmation.request_digest → None  (expected REFUSED: required bare str)", lambda: Confirmation(**conf, request_digest=None))
show("Confirmation.request_digest → MARKER (the ruling)", lambda: Confirmation(**conf, request_digest=MARKER))

