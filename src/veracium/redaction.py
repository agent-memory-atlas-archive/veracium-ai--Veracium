"""specs/0041 — targeted redaction: the marker and the rules every write path shares (tranche 1).

THE MARKER IS NOT SELF-AUTHENTICATING (§4b, v7): a field is REDACTED iff a redaction record names that record
and that field; the byte string alone confers nothing. Two rules follow and both are refusals, not descriptions
(the spec's own lesson, five times over: "a comment, a docstring, a type alias and a naming convention are not
closures — only a refusal is"):

  INV-11's MIRROR   a NON-REDACTION write may not INTRODUCE the marker. Enforced at the store's ordinary write
                    paths (`_upsert_edge_row`, `add_episode`); a record that ALREADY holds the marker and arrives
                    through import is CARRYING it, not introducing it — admitted as an UNATTESTED marker (§4g).
  §2d-iv CLOSURE    `Episode.kind` is closed to the recognised operational kinds at the WRITE path and the
                    IMPORT boundary — never at the read path, so a stored prose kind still loads.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field

MARKER = "\x00veracium:redacted\x00"
MARKER_VERSION = 1
RECOGNISED_EPISODE_KINDS = ("interaction", "outcome")


def carries_marker(value) -> bool:
    """True when a text value IS or CONTAINS the marker, or a list/tuple has such an entry, or a dict has such a
    value (nested one level: the shapes the treatment map names — a string field, `markers` per entry,
    `outcome_counts` keys)."""
    if isinstance(value, str):
        return MARKER in value
    if isinstance(value, (list, tuple)):
        return any(carries_marker(v) for v in value)
    if isinstance(value, dict):
        return any(carries_marker(k) or carries_marker(v) for k, v in value.items())
    return False


def marker_fields(dumped: dict, prefix: str = "") -> list[str]:
    """The dotted names of every field in a model dump that carries the marker."""
    out = []
    for k, v in dumped.items():
        name = f"{prefix}{k}"
        if isinstance(v, dict) and not carries_marker_keys_only(v):
            out.extend(marker_fields(v, name + "."))
        elif carries_marker(v):
            out.append(name)
    return out


def carries_marker_keys_only(d: dict) -> bool:
    """A dict whose KEYS carry the marker is reported as one field (outcome_counts' shape), not descended."""
    return any(isinstance(k, str) and MARKER in k for k in d)


# --------------------------------------------------------------------------------------------------- tranche 3
# specs/0041 §4a — the operation's vocabulary and the treatment map, as PURE functions over a model dump. The
# store applies them inside its one transaction; the tests apply them to the frozen pre-restriction records.

# §11.2: redaction's own reasons (D1's closed vocabulary for the `redacted` journal event and the attestation
# record). `imported_notice` is the import contract's (tranche 4); it is registered here so the vocabulary is
# closed once, in one place. A column CHECK cannot distinguish operations, so the closure is a refusal at the
# redaction write path.
REDACTION_REASONS = ("subject_request", "operator_policy", "erroneous_capture", "legal_obligation", "imported_notice")

REPLACE, CLEAR, DELETE, PRESERVE = "REPLACE", "CLEAR", "DELETE", "PRESERVE"

# §2d-iii-bis, the per-candidate map, restricted to what a treatment CHANGES. Every field not named is
# PRESERVED (identifiers, timestamps, closed sets, provenance) — the map's 44 PRESERVE rows. Nested carriers are
# dotted. A REPLACE writes the marker as the whole value; a CLEAR writes the empty shape the model validates
# (`{}` for `outcome_counts`); the reason fields are the THREE-CASE rule (§4h(i) corollary, v11): absence stays
# absent, a registered vocabulary value is preserved, existing prose becomes `redacted`.
EDGE_REPLACE = ("subject", "relation", "object", "note", "original_relation")       # rows 31-33, 35-36
EDGE_CLEAR = ("outcome_counts",)                                                       # row 34
EDGE_REASON_THREE_CASE = ("invalidation_reason",)                                      # row 30
EDGE_MARKERS_PER_ENTRY = ("agreement.markers",)                                        # row 3
EPISODE_REPLACE = ("summary",)                                                         # row 50
EPISODE_KIND_TWO_BRANCH = ("kind",)                                                    # row 46
EPISODE_REASON_THREE_CASE = ("retired_reason",)                                        # row 49
# the side tables (rows 7, 21, 23, 59/64) and the derived oracle (INV-7), named by table so the receipt can
# carry them beside the record's own carriers
SIDE_TABLE_TREATMENTS = {
    "edge": (("confirmations.request_digest", REPLACE), ("contribution_ledger.identity_digest", CLEAR),
             ("contribution_ledger.evidence_ref_digest", CLEAR), ("supersession_refusals.relation", REPLACE),
             ("edge_embedding", DELETE)),
    "episode": (),
}
REDACTED_REASON_VALUE = "redacted"       # the registry value rows 30/49 write over prose (schema.DISPOSITIONED_REASONS)


def _is_absent(v) -> bool:
    """§4h's corollary: REDACTION ACTS ON CONTENT — a field holding nothing has nothing to remove."""
    return v is None or v == "" or v == [] or v == {}


def treat_reason(value, registry) -> tuple:
    """Rows 30/49, the THREE cases: (new value, treated?)."""
    if _is_absent(value):
        return value, False
    if value in registry:
        return value, False
    return REDACTED_REASON_VALUE, True


def treat_edge(dump: dict, *, reason_registry, recognised_kinds=None) -> tuple:
    """The edge's own carriers (rows 1-3, 29-38, 53-55): returns (the new dump, the dotted fields treated).
    Pure; validated by the caller under the model. The marker never lands on an absent value (§4h corollary),
    and `agreement.markers` keeps its arity (row 3 — the validator admits repeated markers, and only markers)."""
    d = json.loads(json.dumps(dump))
    treated = []
    for f in EDGE_REPLACE:
        if f in d and not _is_absent(d[f]) and d[f] != MARKER:
            d[f] = MARKER; treated.append(f)
    for f in EDGE_CLEAR:
        if not _is_absent(d.get(f)):
            d[f] = {}; treated.append(f)
    for f in EDGE_REASON_THREE_CASE:
        new, hit = treat_reason(d.get(f), reason_registry)
        if hit:
            d[f] = new; treated.append(f)
    ag = d.get("agreement")
    if isinstance(ag, dict) and isinstance(ag.get("markers"), list) and ag["markers"]:
        if any(m != MARKER for m in ag["markers"]):
            ag["markers"] = [MARKER] * len(ag["markers"]); treated.append("agreement.markers")
    return d, treated


def treat_episode(dump: dict, *, reason_registry, recognised_kinds) -> tuple:
    """The episode's carriers (rows 39-52): summary REPLACE; kind PRESERVE-if-recognised else REPLACE (row 46,
    v6); retired_reason THREE-CASE (row 49, v11 — `None` stays `None` and the episode stays ACTIVE)."""
    d = json.loads(json.dumps(dump))
    treated = []
    for f in EPISODE_REPLACE:
        if f in d and not _is_absent(d[f]) and d[f] != MARKER:
            d[f] = MARKER; treated.append(f)
    k = d.get("kind")
    if not _is_absent(k) and k not in recognised_kinds and k != MARKER:
        d["kind"] = MARKER; treated.append("kind")
    for f in EPISODE_REASON_THREE_CASE:
        new, hit = treat_reason(d.get(f), reason_registry)
        if hit:
            d[f] = new; treated.append(f)
    return d, treated


class RedactionReceipt(BaseModel):
    """§4a / §4b-ii: what the caller is told. NEVER a content digest (§4f: a receipt naming what was removed by
    its digest is an oracle for the removed content) — asserted by a test over the serialized receipt.
    `receipts_complete` is False in the ordinary case and the domains are named (§4f, v4); the surviving derived
    records (F6) are named so the caller can act on them."""
    model_config = {"frozen": True, "extra": "forbid"}

    redacted_kind: str                       # "edge" | "episode"
    target_id: str
    user_id: str
    reason: str                              # REDACTION_REASONS
    fields_cleared: list[str]                # the carriers treated (dotted; side tables by table)
    marker_version: int
    store_version_before: int
    store_version_after: int
    recorded_at: str
    event_ref: Optional[str] = None          # "user_id:seq" of the journal event the redaction wrote
    repeated: bool = False                   # §4b-ii: idempotent by content — a second call returns the ORIGINAL
    reconstructed: bool = False              # the receipt rebuilt from the attestation record alone (no original held)
    receipts_complete: bool = False          # §4f: no exact tier exists; the domains that may retain a digest
    receipt_domains: list[str] = Field(default_factory=list)
    surviving_derived: list[dict] = Field(default_factory=list)   # F6: derived records that may still carry the content
