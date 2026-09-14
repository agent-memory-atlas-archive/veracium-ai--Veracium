"""specs/0036 — the journal-witness LIMIT is PUBLISHED, not left silent (the
owner's ruling of 2026-09-12 took journal witnessing off the critical path on
that condition; research's roadmap review of 2026-09-14 found the limit absent
from the concepts page — it stood under `veracium why` in the API reference and
in the release notes that introduced it — and the owner's word "add it to the
docs" put it where a host reads limits).

A carrier check, the same shape as the store-boundary sentence's: the limit's
sentence must stand where a host reads limits (the concepts page's "What
Veracium does *not* do"), beside the store-boundary statement ("Providing a
store" in the API reference), and under `veracium why` where it began. The
words that carry the claim are pinned so a rewrite that softens them fails
here rather than in a review.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIMIT = "not changes made by the party who operates the store"
WITNESS = "Independent witnessing is not part of v1"


def _section(text: str, heading: str) -> str:
    """The section's text with its line wrapping collapsed, so a clause the
    docs wrap across lines is matched as the clause it is."""
    i = text.index(heading)
    j = text.find("\n## ", i + 1)
    return " ".join((text[i:] if j < 0 else text[i:j]).split())


def test_the_journal_limit_stands_in_the_three_places_a_host_reads():
    concepts = (ROOT / "docs" / "concepts.md").read_text(encoding="utf-8")
    api = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    not_do = _section(concepts, "## What Veracium does *not* do")
    assert LIMIT in not_do and WITNESS in not_do and "edge_event" in not_do
    providing = _section(api, "## Providing a store")
    assert LIMIT in providing and WITNESS in providing
    # the original carrier, under `veracium why`, still stands (it spells the clause in
    # lower case mid-sentence, so the count is case-insensitive)
    flat = " ".join(api.split())
    assert LIMIT in flat and flat.lower().count(WITNESS.lower()) >= 2
    # the mechanism is named, not just the outcome: same file, no chain, no signature, erased by forget_user
    for phrase in ("same SQLite file", "no hash chain", "signature", "forget_user"):
        assert phrase in not_do, phrase
    # the control: the sentence is about the operator, never softened to "an attacker"
    assert "party who operates the store" in not_do and "cannot be tampered" not in not_do
