#!/usr/bin/env python3
"""0042 round-1 amendment 2 — the blind examiner's input, as a HARNESS-ONLY projection.

The reviewer reproduced that `introspect(mode="categories")` hands the examiner
`by_author`, `by_disclosure`, "[UNVERIFIED third-party claim, never assert as fact]"
and "[third-party-derived; unconfirmed]" — every trust label the examiner must not
see. So the examiner does not read `introspect`. It reads THIS projection: one row
per ACTIVE record, (subject, relation, object, since) and nothing else, the same
shape for a fact, a quarantined claim and a third-party inference — presence alone.

The FORBIDDEN set is DERIVED, never hand-listed (CLAUDE.md: a hand list for a
derivable set). It is every string constant of >= 4 letters inside the render
functions that PUT trust labels into prose — `render_edges`, `_origin_label`,
`_outcome_note` and the `_ORIGIN_LABELS` table in graph.py — plus every
`EvidenceAuthor` value and every disclosure bucket `introspect.py` counts. When a
render string changes, the set changes with it; nothing here needs editing.

    python3 specs/evidence/0042/examiner_projection.py            # prints the derived set
    python3 specs/evidence/0042/examiner_projection.py --demo     # fixture: render vs projection
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "veracium"

_RENDER_FUNCTIONS = ("render_edges", "_origin_label", "_outcome_note")
_RENDER_TABLES = ("_ORIGIN_LABELS",)
_MIN_LETTERS = 4


def _strings_in(node: ast.AST) -> list[str]:
    """Every string constant under `node`, EXCEPT a docstring (prose about the
    render, not prose the render emits)."""
    doc = None
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            doc = body[0].value
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n is not doc:
            out.append(n.value)
    return out


def derive_forbidden_markers() -> dict[str, list[str]]:
    """What the examiner must not see, by source and by KIND.

    prose     the render layer's trust markers: every string constant in the render
              functions that the layer attaches INSIDE BRACKETS (its own convention,
              specs/0019 §4c) or as a shouted status word (an all-caps word of >= 4
              letters), plus the origin labels that fill the brackets. Checked as
              SUBSTRINGS of the examiner's text.
    metadata  the vocabularies a metadata FIELD would carry: every `EvidenceAuthor`
              value, every disclosure bucket `introspect.py` counts, and introspect's
              own grouping keys. Checked as JSON KEYS — the way `introspect` leaks them
              (`"by_author": {"third_party": 1}`) — never as substrings, because a
              stored subject may legitimately BE the word "user" and a stored relation
              may contain "third_party"; content is presence, a field is a label.
    """
    tree = ast.parse((SRC / "graph.py").read_text())
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in _RENDER_FUNCTIONS:
            found[f"graph.py:{node.name}"] = _strings_in(node)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name) and t.id in _RENDER_TABLES:
                    found[f"graph.py:{t.id}"] = _strings_in(node.value)
    missing = [f for f in _RENDER_FUNCTIONS if f"graph.py:{f}" not in found] + \
              [t for t in _RENDER_TABLES if f"graph.py:{t}" not in found]
    if missing:  # the derivation must REFUSE when its source moved, never derive from less
        raise RuntimeError(f"render source not found in graph.py: {missing}")

    def _marker(s: str) -> bool:
        return ("[" in s or "]" in s or re.search(r"\b[A-Z]{4,}\b", s) is not None) \
            and len(re.sub(r"[^A-Za-z]", "", s)) >= _MIN_LETTERS

    def _clean(s: str) -> str:
        return s.strip(" []();:—-")

    def _fragments(s: str) -> set[str]:
        groups = re.findall(r"\[([^\[\]]+)\]", s)      # each complete [group] is its own marker
        if groups:
            return {_clean(g) for g in groups if len(re.sub(r"[^A-Za-z]", "", g)) >= _MIN_LETTERS}
        return {_clean(s)} if _marker(s) else set()   # an f-string piece or a shouted word

    prose: dict[str, list[str]] = {}
    for src, strings in found.items():
        if src.endswith(("_ORIGIN_LABELS", "_origin_label")):   # the values that fill the brackets
            frags = {_clean(s) for s in strings if len(re.sub(r"[^A-Za-z]", "", s)) >= _MIN_LETTERS}
        else:
            frags = set().union(*(_fragments(s) for s in strings)) if strings else set()
        prose[src] = sorted(f for f in frags if f)
    from veracium import EvidenceAuthor  # noqa: E402
    itree = ast.parse((SRC / "introspect.py").read_text())
    disc = []
    for n in ast.walk(itree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_count":
            if n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == "by_disclosure":
                disc += _strings_in(n.args[1])
    metadata = {"schema.EvidenceAuthor": sorted(m.value for m in EvidenceAuthor),
                "introspect.by_disclosure": sorted(set(disc)),
                "introspect.keys": ["by_author", "by_disclosure"]}
    return {"prose": prose, "metadata": metadata}


def forbidden_fragments() -> list[str]:
    d = derive_forbidden_markers()
    return sorted({f for frags in d["prose"].values() for f in frags} |
                  {f for frags in d["metadata"].values() for f in frags})


def hits(text: str, derived: dict | None = None) -> list[str]:
    """Prose markers as substrings; metadata vocabularies as JSON keys."""
    d = derived or derive_forbidden_markers()
    prose = {f for frags in d["prose"].values() for f in frags}
    meta = {f for frags in d["metadata"].values() for f in frags}
    return sorted({f for f in prose if f in text} | {f for f in meta if f'"{f}":' in text})


def project(store, user_id: str) -> list[dict]:
    """The examiner's whole view: presence alone. Same shape for every record."""
    rows = []
    for e in store.edges(user_id, active_only=False, include_quarantined=True):
        if not e.active:
            continue                         # history is not presence
        rows.append({"subject": e.subject, "relation": e.relation,
                     "object": e.object, "since": e.valid_from.date().isoformat()})
    rows.sort(key=lambda r: (r["relation"], r["since"], r["subject"], r["object"]))
    return rows


def freeze(rows: list[dict]) -> tuple[str, str]:
    """The frozen input: canonical JSON and its digest, fixed BEFORE questions are
    authored and before any join to the private manifest."""
    text = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text, hashlib.sha256(text.encode()).hexdigest()


def _demo() -> int:
    import importlib.util, tempfile
    spec = importlib.util.spec_from_file_location("t", ROOT / "tests" / "test_introspect_cli.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    from veracium.graph import render_edges
    derived = derive_forbidden_markers(); frags = forbidden_fragments()
    with tempfile.TemporaryDirectory() as d:
        mem = m._seeded_mem(f"{d}/t.db")
        edges = mem.store.edges("ida", active_only=False, include_quarantined=True)
        rendered = render_edges([e for e in edges if e.active])
        rows = project(mem.store, "ida"); text, digest = freeze(rows)
        cats = json.dumps(mem.introspect("ida", mode="categories"))
        mem.close()
    print(f"forbidden fragments derived: {len(frags)}")
    print(f"render_edges output hits:     {hits(rendered, derived)}")
    print(f"introspect categories hits:   {hits(cats, derived)}")
    print(f"projection hits:              {hits(text, derived)}")
    print(f"projection rows: {len(rows)}; frozen digest sha16 {digest[:16]}")
    for r in rows:
        print("  ", r)
    return 0 if not hits(text, derived) and hits(rendered, derived) and hits(cats, derived) else 1


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    d = derive_forbidden_markers()
    for kind in ("prose", "metadata"):
        for src, frags in d[kind].items():
            print(f"{kind:8s} {src}:")
            for f in frags:
                print(f"             {f!r}")
