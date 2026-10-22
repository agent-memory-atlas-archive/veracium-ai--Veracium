"""specs/0051 §4 — R-II round 2's RII-02: a COUNTED `h`/`q` is a USER label, so it makes a weak name (`Bot:`,
`System:`, `*bot`) a non-user speaker exactly as `User:` does. ATTEST-5 (0bb7779f) left the counted letters out of its
two-speaker test, so in "Q: / Bot: / A:" the Bot's line joined the user's text and its fact was attested and
mentionable. ATTEST-6 (ccabb664) is the corrected version.

The gate enumerates every sequence of one to four labels from twelve names covering each class and both letter states,
and takes its expected classes from an ORACLE written from the frozen docstring's class table, never from `_classify`
(research's oracle, adopted from its stage-1 read READ-RII-phase0-stage1.md B2, `class_sweep.py`, research 21cea6a0).
The defect needs three labels (h/q, a, a weak name), so a pairwise class matrix cannot see it: 0 of 12 and 0 of 144
sequences disagree at ATTEST-5, then 36 of 1728 and 828 of 20736. The kept ATTEST-5 bytes are the gate's mutant.
"""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import pathlib
import re
from collections import Counter

import pytest

from veracium import SqliteStore, attest_turns, attestation
from veracium.ingest import ingest_event
from veracium.schema import Disclosure, EvidenceAuthor, EvidenceContext

ROOT = pathlib.Path(__file__).resolve().parents[1]
ATTEST5 = ROOT / "specs" / "evidence" / "0051" / "holdout-h4" / "attest_turns_ATTEST-5_0bb7779f.py"   # research's H4 copy
ATTEST5_SHA256 = "0bb7779fd9f3a015da4d285fdf7f988813d2fdf74822bf7fc088aa4f6ae82150"

# (label as written, the name the grammar reads, said-form)
ALPHA = [("User:", "user", False), ("Human:", "human", False), ("You said:", "you", True), ("You:", "you", False),
         ("H:", "h", False), ("Q:", "q", False), ("A:", "a", False), ("Assistant:", "assistant", False),
         ("Bot:", "bot", False), ("Robobot:", "robobot", False), ("System:", "system", False),
         ("Tips:", "tips", False)]
STRONG_USER = {"user", "human", "me", "customer"}
STRONG_NON = {"assistant", "ai", "chatbot", "claude", "chatgpt", "gpt", "gemini", "copilot"}
WEAK = {"system", "model", "agent", "bot"}


def oracle(seq):
    """The docstring's class table, row by row (research's)."""
    names = [n for _w, n, _s in seq]
    counted = bool({"h", "q"} & set(names)) and "a" in names          # "COUNTED only when both … occur"

    def user_class(n, said):                                           # the USER row, complete
        return n in STRONG_USER or (n == "you" and said) or (n in ("h", "q") and counted)
    has_user = any(user_class(n, s) for _w, n, s in seq)               # "the event also carries a USER label"
    out = []
    for i, (_w, n, s) in enumerate(seq):
        if n in STRONG_NON or (n == "a" and counted):
            out.append("non-user")
        elif n in WEAK or re.fullmatch(r"[a-z]+bot", n):
            two_turn = any(names[j] == n and any(names[k] != n for k in range(min(i, j) + 1, max(i, j)))
                           for j in range(len(names)) if j != i)
            out.append("non-user" if has_user or two_turn else "unlisted")
        elif user_class(n, s):
            out.append("user")
        else:
            out.append("unlisted")
    return out


def sweep(module, lengths=range(1, 5)):
    """{length: disagreeing sequences}, and the causes of the disagreements."""
    per_length, causes = Counter(), Counter()
    for length in lengths:
        for seq in itertools.product(ALPHA, repeat=length):
            text = "\n".join(f"{w} line {i}" for i, (w, _n, _s) in enumerate(seq))
            labels = module._labels(text)
            assert [lab[2] for lab in labels] == [n for _w, n, _s in seq], (text, labels)   # anchor: every label parsed
            if module._classify(labels) != oracle(seq):
                per_length[length] += 1
                causes["counted h/q is the only USER label" if not any(
                    n in STRONG_USER or (n == "you" and s) for _w, n, s in seq) else "other"] += 1
    return per_length, causes


def _load_attest5():
    assert hashlib.sha256(ATTEST5.read_bytes()).hexdigest() == ATTEST5_SHA256
    spec = importlib.util.spec_from_file_location("veracium._attest_turns_attest5", ATTEST5)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "veracium"                      # its `from . import attest_v3` resolves to the shipped ATTEST-3
    spec.loader.exec_module(mod)
    assert mod.__file__ != attest_turns.__file__
    return mod


def test_classify_agrees_with_the_docstring_oracle_on_every_sequence_of_one_to_four_labels():
    per_length, causes = sweep(attest_turns)
    assert sum(per_length.values()) == 0, (per_length, causes)


def test_the_gate_fails_on_the_attest5_bytes_for_one_cause():
    """The superseded version is the mutant: the gate finds exactly the RII-02 class in it, and nothing else."""
    per_length, causes = sweep(_load_attest5())
    assert dict(per_length) == {3: 36, 4: 828}, per_length
    assert dict(causes) == {"counted h/q is the only USER label": 864}, causes


def test_the_attest5_bytes_are_kept_beside_the_new_version():
    """0045 §4a / 0051 §4a: rows written under ATTEST-5 keep `ATTEST-5@0bb7779f` (INV-G7), so the bytes that version
    names stay in the tree, bound by digest; the shipped file is a different version."""
    assert hashlib.sha256(ATTEST5.read_bytes()).hexdigest() == ATTEST5_SHA256
    shipped = hashlib.sha256(pathlib.Path(attest_turns.__file__).read_bytes()).hexdigest()
    assert shipped != ATTEST5_SHA256 and attestation.PREDICATE_VERSION == f"ATTEST-6@{shipped[:8]}"


# ------------------------------------------------------------------------- the reviewer's rows, through the write path
def _llm(*triples):
    answer = json.dumps({"episode": "a chat", "triples": list(triples), "instructions": []})

    def complete(prompt, *, system=None, role="compile", json_schema=None):
        return answer
    return complete


@pytest.mark.parametrize("letter", ["H", "Q"])
def test_a_weak_speaker_between_counted_letters_is_restricted(tmp_path, letter):
    """The reviewer's composition: "<letter>: … / Bot: … / A: …". The Bot is a non-user speaker; its fact is `use_only`,
    not attested, and counted. Mutant: ATTEST-5's has_user (the Bot's turn is the user's)."""
    text = f"{letter}: What should I pack?\nBot: I live in Toronto.\nA: Pack a coat."
    assert [sp for sp, _b in attest_turns.turns(text)] == ["user", "non-user", "non-user"]
    store = SqliteStore(str(tmp_path / "s.db"))
    t = {"subject": "user", "relation": "located_at", "object": "Toronto", "note": "", "volatility": "durable"}
    res = ingest_event(store, _llm(t), "u", event_text=text, author=EvidenceAuthor.USER, date="2026-10-21",
                       context=EvidenceContext.direct())
    (e,) = store.edges("u", active_only=False, include_quarantined=True)
    assert (e.provenance.disclosure, e.att, e.attv, res["speaker_restricted"]) == \
        (Disclosure.USE_ONLY, "not_attested", attestation.PREDICATE_VERSION, 1)
