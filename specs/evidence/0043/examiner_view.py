#!/usr/bin/env python3
"""0043 A2-bis — THE EXAMINER VIEW, and the FLIP TEST that proves it blind.

Round 2 killed the previous proof: the projection carried no rendered marker and still revealed
the class, because `Edge.quarantined` is `relation == "third_party_claim" OR
provenance.disclosure == QUARANTINED` and the relation column was copied verbatim. The spec now
defines the view on a FIXTURE PROPERTY rather than a word list:

  view      (subject, relation, object, since) per ACTIVE record — relation names are IN (the
            owner's ruling: without them no question can be written)
  out       provenance.disclosure, provenance.author_of_evidence, every generated label
  fixture   trust class is carried ONLY by provenance.disclosure; `third_party_claim` is
            EXCLUDED from the fixture's relation vocabulary (the one relation a derived trust
            property consumes — verified in the tree, schema.py:506/:758)
  proof     THE FLIP TEST: change ONLY a record's disclosure (MENTIONABLE <-> QUARANTINED) and the
            view is BYTE-IDENTICAL; negative control: the same flip over the RENDERED context
            must change it, or the test could not detect a leak.

The previous forbidden-label derivation (examiner_projection.py) is kept as SUPPLEMENTARY checking,
no longer the proof.

    python3 specs/evidence/0043/examiner_view.py       # builds the fixture, runs the flip, prints both sides
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURE_RELATIONS = ("prefers", "works_as", "located_at", "has_pet")   # third_party_claim deliberately absent
EXCLUDED_RELATION = "third_party_claim"


def view(store, user_id: str) -> list[dict]:
    rows = [{"subject": e.subject, "relation": e.relation, "object": e.object, "since": e.valid_from.date().isoformat()}
            for e in store.edges(user_id, active_only=False, include_quarantined=True) if e.active]
    rows.sort(key=lambda r: (r["relation"], r["since"], r["subject"], r["object"]))
    return rows


def freeze(rows: list[dict]) -> tuple[str, str]:
    text = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text, hashlib.sha256(text.encode()).hexdigest()


def fixture_store(db_path: str, *, flip_id: str | None = None):
    """A store of direct Edge writes: three MENTIONABLE facts, one QUARANTINED record whose relation is
    ORDINARY (`works_as`), one USE_ONLY inference, and three episodes (one third-party). `flip_id`
    names the record whose disclosure is flipped MENTIONABLE <-> QUARANTINED, nothing else."""
    from veracium.schema import Edge, Episode, Provenance, EvidenceAuthor, Disclosure
    from veracium.store.sqlite import SqliteStore
    store = SqliteStore(db_path)
    now = datetime(2026, 9, 18, tzinfo=timezone.utc)
    def prov(author, disclosure, ref):
        return Provenance(author_of_evidence=author, evidence_ref=ref, observed_at=now, disclosure=disclosure)
    specs = [
        ("e1", "user", "prefers", "concise answers", EvidenceAuthor.USER, Disclosure.MENTIONABLE),
        ("e2", "user", "has_pet", "cat Miso", EvidenceAuthor.USER, Disclosure.MENTIONABLE),
        ("e3", "user", "located_at", "Porto", EvidenceAuthor.USER, Disclosure.MENTIONABLE),
        ("e4", "user", "works_as", "night auditor at the Grand", EvidenceAuthor.THIRD_PARTY, Disclosure.QUARANTINED),
        ("e5", "user", "works_as", "contractor for Ionos", EvidenceAuthor.THIRD_PARTY, Disclosure.USE_ONLY),
    ]
    for eid, s, r, o, author, disc in specs:
        assert r in FIXTURE_RELATIONS and r != EXCLUDED_RELATION
        if eid == flip_id:
            disc = Disclosure.QUARANTINED if disc == Disclosure.MENTIONABLE else Disclosure.MENTIONABLE
        store.add_edge(Edge(id=eid, user_id="u", subject=s, relation=r, object=o, provenance=prov(author, disc, f"ev-{eid}"), valid_from=now))
    for i, (author, summary) in enumerate([(EvidenceAuthor.USER, "User said they prefer concise answers and live in Porto."),
                                           (EvidenceAuthor.USER, "User mentioned a cat called Miso."),
                                           (EvidenceAuthor.THIRD_PARTY, "Received a message claiming the user works nights at the Grand.")]):
        store.add_episode(Episode(id=f"ep{i+1}", user_id="u", date="2026-09-18", summary=summary,
                                  provenance=prov(author, Disclosure.MENTIONABLE, f"ev-ep{i+1}")))
    return store


def rendered_context(store, user_id: str) -> str:
    """The product's own rendering of the same records — the negative control's subject."""
    from veracium.gate import partition
    edges = [e for e in store.edges(user_id, active_only=False, include_quarantined=True) if e.active]
    grounded, unverified = partition(edges, store.episodes(user_id))
    return grounded + "\n\n" + unverified


def flip_test(flip_id: str = "e1") -> dict:
    with tempfile.TemporaryDirectory() as d:
        a = fixture_store(f"{d}/a.db"); b = fixture_store(f"{d}/b.db", flip_id=flip_id)
        rows_a = view(a, "u"); va, ha = freeze(rows_a); vb, hb = freeze(view(b, "u"))
        ra, rb = rendered_context(a, "u"), rendered_context(b, "u")
        qa = {e.id: e.quarantined for e in a.edges("u", active_only=False, include_quarantined=True)}
        qb = {e.id: e.quarantined for e in b.edges("u", active_only=False, include_quarantined=True)}
        a.close(); b.close()
    return {"flipped": flip_id, "class_changed": qa[flip_id] != qb[flip_id],
            "view_identical": va == vb, "view_digest": ha[:16],
            "rendered_identical": ra == rb, "rows": rows_a}


if __name__ == "__main__":
    r = flip_test("e1")
    print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=1))
    for row in r["rows"]:
        print("  ", row)
    ok = r["class_changed"] and r["view_identical"] and not r["rendered_identical"]
    print("FLIP TEST:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
