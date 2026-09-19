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
