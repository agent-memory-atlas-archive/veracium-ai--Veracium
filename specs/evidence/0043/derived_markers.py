#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0043_derived_markers.py::test_derived_markers_check_refuses_each_tampered_snapshot
"""0043 — a generated, digest-bound SNAPSHOT of the derived marker set (the round-9 verdict's optional ask).

The round-9 verdict accepted the arm check's independence line — the marker DATA is derived from the renderer and
shared, the APPLICATION is separate — and named its limit: "an incorrect or incomplete shared marker derivation can
still affect both sides". It suggested "a generated, digest-bound snapshot of the derived marker set … would make
changes easier to inspect without making the snapshot a second authority". This writes that snapshot:

  sources         sha256 of the three files the derivation reads (examiner_projection.py, src/veracium/graph.py,
                  src/veracium/introspect.py) — the same key `_declared_edit_data` memoises on;
  prose           `examiner_projection.derive_forbidden_markers()["prose"]`, by render source;
  applied         the CHECK side's data exactly as `model_input_capture._declared_edit_data()` returns it (fragments,
                  origins, in their application order), and the TRANSFORM side's `_marker_patterns()` — both
                  applications of the one vocabulary, side by side, so a change to either is a visible diff;
  body_sha256     sha256 of the CANONICAL JSON (sort_keys, separators (",", ":"), ensure_ascii) of everything above,
                  i.e. of the object without this field. The file itself is that object plus this field, written
                  with indent=1 and sort_keys for reading.

NOT AN AUTHORITY: no code reads this file; it only records. tests/test_0043_derived_markers.py proves it by behaviour
(the snapshot replaced with garbage, and deleted, changes nothing the check or the transform decides on any committed
pair), not only by a name search.

    $PY specs/evidence/0043/derived_markers.py --check    # the snapshot equals a fresh derivation (default)
    $PY specs/evidence/0043/derived_markers.py --write    # regenerate
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAPSHOT = HERE / "derived-markers.json"
SOURCES = (HERE / "examiner_projection.py", ROOT / "src" / "veracium" / "graph.py", ROOT / "src" / "veracium" / "introspect.py")


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"dm_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def derive() -> dict:
    ep, mc = _load("examiner_projection"), _load("model_input_capture")
    frags, origins = mc._declared_edit_data()
    body = {
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},
        "prose": {k: sorted(v) for k, v in ep.derive_forbidden_markers()["prose"].items()},
        "applied": {"check_side": {"fragments": list(frags), "origins": list(origins)},
                    "transform_side": {"marker_patterns": list(mc._marker_patterns())}},
    }
    return {**body, "body_sha256": hashlib.sha256(canonical(body)).hexdigest()}


def render(snapshot: dict) -> str:
    return json.dumps(snapshot, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def problems(path: pathlib.Path = SNAPSHOT) -> list[str]:
    if not path.exists():
        return [f"{path.name} does not exist — run --write"]
    text = path.read_text(encoding="utf-8")
    try:
        shipped = json.loads(text, object_pairs_hook=_strict_pairs)
    except ValueError as e:
        return [f"{path.name} is not JSON: {e}"]
    out = []
    body = {k: v for k, v in shipped.items() if k != "body_sha256"} if isinstance(shipped, dict) else None
    if body is None or hashlib.sha256(canonical(body)).hexdigest() != shipped.get("body_sha256"):
        out.append(f"{path.name}: body_sha256 does not match its own body (edited by hand, or a partial write)")
    fresh = render(derive())
    if text != fresh:
        out.append(f"{path.name} is stale: it differs from a fresh derivation of this tree — regenerate with --write")
    return out


def main() -> int:
    if "--write" in sys.argv:
        SNAPSHOT.write_text(render(derive()), encoding="utf-8")
        print(f"wrote {SNAPSHOT.relative_to(ROOT)} (body_sha256 {json.loads(SNAPSHOT.read_text(), object_pairs_hook=_strict_pairs)['body_sha256']})")
        return 0
    bad = problems()
    for b in bad:
        print(f"STALE: {b}")
    if not bad:
        print(f"derived-markers.json current (body_sha256 {json.loads(SNAPSHOT.read_text(), object_pairs_hook=_strict_pairs)['body_sha256']})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
