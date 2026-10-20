"""specs/0051 (speaker turns inside a user event; ACCEPTED on Quentin's word 2026-10-20, v0.3.1): ATTEST-5 — ATTEST-3
over the raw text AND over the event's USER text when the event labels a non-user turn — and the product backstop that
writes `use_only` a triple whose every non-`user` side the event shows only in a non-user turn. INV-S1..S8.

PRODUCT tests: the frozen predicate file and the backstop module directly (the grammar's domain, INV-S6), and the real
`ingest_event` with a scripted provider (the write path, INV-S1/S2/S7). The literal rows h4-073 and h4-083 are
research's holdout H4 items (research b3242a94) on which ATTEST-4's matcher restricted a USER fact; H4 is the
backstop's regression set since its normalisation was fixed after reading them (0051 §6).
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from veracium import SqliteStore, attest_turns, attest_v3, attestation, speaker_backstop
from veracium.ingest import ingest_event
from veracium.schema import Disclosure, EvidenceAuthor, EvidenceContext

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "veracium"
U = "u"
DATE = "2026-10-20"
A3, A5, B = attest_v3.attests, attest_turns.attests, speaker_backstop.speaker_restricts


# ------------------------------------------------------------------------------------------- INV-S5: the version
def test_inv_s5_the_version_names_both_frozen_files():
    """`attv` says what produced `att`: ATTEST-5's verdict is a function of attest_turns.py AND attest_v3.py, so the
    literal is bound to the first file's digest and the second's is pinned too. Mutants: keep ATTEST-3@b1329a81; edit
    either file without a new version."""
    turns = hashlib.sha256((SRC / "attest_turns.py").read_bytes()).hexdigest()
    v3 = hashlib.sha256((SRC / "attest_v3.py").read_bytes()).hexdigest()
    assert turns == "0bb7779fd9f3a015da4d285fdf7f988813d2fdf74822bf7fc088aa4f6ae82150"
    assert v3.startswith("b1329a81")
    assert attestation.PREDICATE_VERSION == f"ATTEST-5@{turns[:8]}" and attestation.valid_attv(attestation.PREDICATE_VERSION)


# --------------------------------------------------------------------------------- INV-S6: the grammar's domain
NOTES = [  # research's B1 rows: a user's own notes; nothing is a non-user turn, ATTEST-3's answer stands (INV-S3)
    "Model: Corolla\nI live in Porto.", "Agent: Jane Doe\nI live in Porto.", "System: Ubuntu 24.04\nI live in Porto.",
    "Talbot: see you at 5\nI live in Porto.", "Note: call mom\nI live in Porto.", "I live in Porto.",
    "A: the plan\nI live in Porto."]           # a lone `a` is no letter pair


@pytest.mark.parametrize("text", NOTES)
def test_inv_s3_a_users_notes_have_no_non_user_turn(text):
    assert attest_turns.user_text(text) is None
    assert A5("user", "located_at", "Porto", text) == A3("user", "located_at", "Porto", text) == "ATTESTED"
    assert B("user", "Porto", text) is False


ASSISTANT_FIRST_PERSON = {  # F1 formats and C3/B3: the assistant's "I'm based in Toronto" never attests, and restricts
    "said-form": "You said:\nAny tips?\nChatGPT said:\nSure! I'm based in Toronto.",
    "heading": "### User\nAny tips?\n### Assistant\nSure! I'm based in Toronto.",
    "quote": "> User: any tips?\n> Assistant: Sure! I'm based in Toronto.",
    "parenthetical": "User: any tips?\nAssistant (GPT-4o): Sure! I'm based in Toronto.",
    "letters": "H: any tips?\nA: Sure! I'm based in Toronto.",
    "emphasis": "**Human:** any tips?\n**AI:** Sure! I'm based in Toronto.",
    "human-ai": "Human: any tips?\nAI: Sure! I'm based in Toronto.",
    "weak-alternating": "System: hello\nUser: hi\nSystem: Sure! I'm based in Toronto.",
    "B3 note heading": "User: tips?\nAssistant: Sure.\nNote:\nI'm based in Toronto.",
    "B3 key line": "Human: where?\nAI: Here.\nlocation: Toronto\nI'm based in Toronto.",
    "URL line": "User: hi\nAssistant: see\nhttps://x.com\nNice. I'm based in Toronto.\nAssistant: ok",   # no hand-off at a URL
}


@pytest.mark.parametrize("name", sorted(ASSISTANT_FIRST_PERSON))
def test_inv_s1_s6_an_assistant_first_person_never_attests_and_is_restricted(name):
    text = ASSISTANT_FIRST_PERSON[name]
    assert A3("user", "located_at", "Toronto", text) == "ATTESTED"          # the leak this spec closes
    assert A5("user", "located_at", "Toronto", text) == "NOT_ATTESTED"
    assert B("user", "Toronto", text) is True


def test_inv_s6_a_heading_inside_a_reply_stays_in_the_reply():
    """B3: "**Pros:**" inside the assistant's reply is the reply's own text, not a user turn (ATTEST-4's every-label
    rule made it one). Mutant: ATTEST-4's rule."""
    text = "User: laptop?\nAssistant: Options.\n**Pros:**\nI prefer ThinkPads."
    assert [sp for sp, _b in attest_turns.turns(text)] == ["user", "non-user"]
    assert A5("user", "prefers", "ThinkPads", text) == "NOT_ATTESTED" and B("user", "ThinkPads", text) is True


@pytest.mark.parametrize("text,speakers", [
    # a hand-off: the unlisted name's NEXT label is non-user, so it ends Claude's turn and opens a USER turn
    ("Claude: Where do you live?\nQuentin: Hi. I live in Porto.\nClaude: Nice.", ["non-user", "user", "non-user"]),
    # established: Quentin handed the floor to Claude earlier, so its later label ends Claude's turn
    ("Quentin: hello\nClaude: Where do you live?\nQuentin: Hi. I live in Porto.", ["user", "non-user", "user"]),
    # the one-exchange LIMIT (§8 limit 6): unlisted, unestablished, hands off to nobody — it stays in Claude's turn
    ("Claude: Where do you live?\nQuentin: Hi. I live in Porto.", ["non-user"]),
    # a later recurrence never reaches back (C3): the first Quentin line hands off to nobody but Quentin
    ("Claude: Q?\nQuentin: A.\nQuentin: B.\nClaude: ok", ["non-user", "user", "non-user"]),
    # a user's own heading that hands off to no assistant establishes nothing (C2's shape needs the hand-off): the
    # assistant's same heading stays in its reply
    ("Tips: bring water\nUser: any tips?\nAssistant: Sure.\nTips:\nI'm based in Toronto.", ["user", "user", "non-user"]),
])
def test_inv_s6_c3_the_one_pass_hand_off_rule(text, speakers):
    """C3, the exact rule (0051 §4; the frozen file's docstring). Mutants: establishment without the hand-off
    condition; a whole-event alternation rule for unlisted names."""
    assert [sp for sp, _b in attest_turns.turns(text)] == speakers


def test_c1_sample_dialogue_inside_a_reply_is_a_stated_limit():
    """§8 limit 7: a listed USER label inside the assistant's reply reopens a USER turn — the lines fail open."""
    text = "User: write a script\nAssistant: Here:\nCustomer: Hi. I'm based in Toronto."
    assert A5("user", "located_at", "Toronto", text) == "ATTESTED" and B("user", "Toronto", text) is False


def test_the_users_own_later_sentence_in_a_labelled_turn_still_attests():
    text = "User: Hi. I live in Austin.\nAssistant: Nice. I live in Denver."
    assert A5("user", "located_at", "Austin", text) == "ATTESTED" and B("user", "Austin", text) is False
    assert A5("user", "located_at", "Denver", text) == "NOT_ATTESTED" and B("user", "Denver", text) is True


# ----------------------------------------------------------------------- INV-S2: the backstop's normalisations
H4_073 = ("You: Write a toast for my husband Daniel's 40th birthday, about 4 sentences, warm and a bit funny.\n\n"
          "Copilot: Here you go:\n\n🥂 *Toast*\n\nMy husband Daniel turns forty today, and somehow still thinks 'one "
          "more episode' means one. He is the steadiest person I know, the best cook in any kitchen, and the reason "
          "our home is full of laughter. Here's to forty, and to many more. Cheers, Daniel!\n\nWant a version for a "
          "larger crowd?")
H4_083 = ("Human: Help me write a note to my travel agent. I prefer window seats and I'd like to avoid anything "
          "departing before 8am. Flying Boston to Denver on Dec 4.\n\nAssistant: Here's a draft:\n\nHi Carol,\n\nI'm "
          "booking Boston to Denver on December 4. I prefer a window seat, and I'd like to avoid departures before "
          "8am. Could you share a few options?\n\nThanks,\n[Name]\n\n**Add if useful**\n- Max layovers\n- Preferred "
          "airline\n- Carry-on only?")


@pytest.mark.parametrize("subject,obj,text,want", [
    ("user", "person:Daniel", H4_073, False),     # an apostrophe splits: "Daniel's" holds "daniel" (h4-073)
    ("user", "window seat", H4_083, False),       # a plural stem: "window seats" ~ "window seat" (h4-083)
    ("user", "Go", "User: I'm going now.\nAssistant: I prefer Go.", True),         # word boundaries, not substrings
    ("user", "person:Anna", "User: hi\nAssistant: My wife is Anna.", True),         # the prefix dropped on the side
    ("person:anna_smith", "user", "User: hi\nAssistant: Anna Smith is my wife.", True),   # `_` read as a space
    ("person:Anna", "org:Acme", "User: hi\nAssistant: Anna works at Acme.", True),  # neither side `user`: both checked
    ("person:Anna", "org:Acme", "User: Anna is great\nAssistant: Anna works at Acme.", False),
    ("user", "box", "User: two boxes\nAssistant: a box", False),
    ("user", "glass", "User: I like glasses.\nAssistant: I prefer glass.", False),
])
def test_inv_s2_the_backstop_reads_each_side_through_its_normalisations(subject, obj, text, want):
    """Mutants: keep the apostrophe in tokens; drop the plural stem; substring matching; a one-sided prefix drop."""
    assert B(subject, obj, text) is want


# -------------------------------------------------------------------- INV-S4 and INV-S8 over every row above
ROWS = ([("user", "located_at", "Porto", t) for t in NOTES]
        + [("user", "located_at", "Toronto", t) for t in ASSISTANT_FIRST_PERSON.values()]
        + [("user", "partner_of", "person:Daniel", H4_073), ("user", "prefers", "window seat", H4_083),
           ("user", "prefers", "the Beatles", "User: Hi. I prefer Beatles.\nAssistant: I prefer the Beatles too.")])


def test_inv_s4_s8_restriction_only_and_never_both_restricted_and_attested():
    """INV-S4: ATTEST-5 attests a subset of what ATTEST-3 attests. INV-S8: no triple is both restricted by the backstop
    and attested by ATTEST-5 (the premise of §4b's normalisation changing without a new `attv`). Mutant for S8: a
    backstop normalisation stricter than ATTEST-3's (drop the leading-article strip) — the Beatles row then reads both."""
    for subject, relation, obj, text in ROWS:
        a5 = A5(subject, relation, obj, text)
        assert a5 != "ATTESTED" or A3(subject, relation, obj, text) == "ATTESTED", text
        assert not (a5 == "ATTESTED" and B(subject, obj, text)), text
    assert A5("user", "prefers", "the Beatles", ROWS[-1][3]) == "ATTESTED"


# -------------------------------------------------------------------------- the write path (INV-S1, S2, S7)
def _llm(*triples):
    answer = json.dumps({"episode": "a chat", "triples": list(triples), "instructions": []})

    def complete(prompt, *, system=None, role="compile", json_schema=None):
        return answer
    return complete


def _t(relation, obj, subject="user"):
    return {"subject": subject, "relation": relation, "object": obj, "note": "", "volatility": "durable"}


MIXED = "Human: I live in Austin. Any tips?\nAI: Sure! I'm based in Toronto."


def _ingest(tmp_path, text, *triples, author=EvidenceAuthor.USER, context="direct", name="s"):
    store = SqliteStore(str(tmp_path / f"{name}.db"))
    ctx = EvidenceContext.direct() if context == "direct" else None
    res = ingest_event(store, _llm(*triples), U, event_text=text, author=author, date=DATE, context=ctx)
    return res, {e.object: e for e in store.edges(U, active_only=False, include_quarantined=True)}


def test_the_write_path_restricts_the_assistants_value_and_keeps_the_users(tmp_path):
    """INV-S1/S2/S7 through the real ingest: the assistant's Toronto is `use_only`, not attested, and counted; the
    user's Austin is `mentionable` and attested; both carry ATTEST-5's version. Mutants: drop §4b in ingest; count
    nothing; count §4b only."""
    res, by = _ingest(tmp_path, "Human: Hi. I live in Austin. Any tips?\nAI: Sure! I'm based in Toronto.",
                      _t("located_at", "Austin"), _t("located_at", "Toronto"))
    t, a = by["Toronto"], by["Austin"]
    assert (t.provenance.disclosure, t.att, t.attv) == (Disclosure.USE_ONLY, "not_attested", "ATTEST-5@0bb7779f")
    assert (a.provenance.disclosure, a.att, a.attv) == (Disclosure.MENTIONABLE, "attested", "ATTEST-5@0bb7779f")
    assert res["speaker_restricted"] == 1


def test_s7_a_label_only_restriction_is_counted_once(tmp_path):
    """§4a without §4b: the value also occurs in the user's text, so the disclosure stands, but ATTEST-3 over the raw
    text attested the assistant's sentence and ATTEST-5 does not — counted once."""
    res, by = _ingest(tmp_path, "Human: Toronto tips?\nAI: Sure! I'm based in Toronto.", _t("located_at", "Toronto"))
    t = by["Toronto"]
    assert (t.provenance.disclosure, t.att, res["speaker_restricted"]) == (Disclosure.MENTIONABLE, "not_attested", 1)


def test_s7_the_counter_is_present_and_zero_on_every_other_path(tmp_path):
    """0025 §4c's every-path rule: no label (0), a non-user-effective event (0, the backstop not applied), and the
    unparseable path (0)."""
    res, by = _ingest(tmp_path, "I live in Austin.", _t("located_at", "Austin"), name="a")
    assert res.get("speaker_restricted") == 0 and by["Austin"].att == "attested"
    res, by = _ingest(tmp_path, MIXED, _t("located_at", "Toronto"), author=EvidenceAuthor.SYSTEM, name="b")
    assert res.get("speaker_restricted") == 0 and by["Toronto"].attv == "non-user-effective"
    store = SqliteStore(str(tmp_path / "c.db"))
    bad = ingest_event(store, lambda *a, **k: "not json", U, event_text=MIXED, author=EvidenceAuthor.USER, date=DATE,
                       context=EvidenceContext.direct())
    assert bad.get("speaker_restricted") == 0 and bad.get("unparseable") is True


def test_a_restricted_arrival_never_demotes_a_mentionable_prior(tmp_path):
    """Research's v0.2 read (unchecked there): a `use_only` same-value arrival from a mixed transcript meets the
    user's own earlier `mentionable` fact. The prior stays active and mentionable."""
    store = SqliteStore(str(tmp_path / "p.db"))
    ingest_event(store, _llm(_t("located_at", "Toronto")), U, event_text="I'm based in Toronto.",
                 author=EvidenceAuthor.USER, date="2026-10-01", context=EvidenceContext.direct())
    ingest_event(store, _llm(_t("located_at", "Toronto")), U, event_text="Human: hi\nAI: I'm based in Toronto.",
                 author=EvidenceAuthor.USER, date=DATE, context=EvidenceContext.direct())
    live = [e for e in store.edges(U) if e.object == "Toronto"]
    assert live and all(e.provenance.disclosure == Disclosure.MENTIONABLE for e in live if e.att == "attested")
    assert any(e.provenance.disclosure == Disclosure.MENTIONABLE and e.att == "attested" for e in live)


def test_the_extraction_prompt_carries_the_speaker_rule():
    from veracium.prompts import EXTRACT_PROMPT
    assert ("A statement in a turn labelled for\n  another speaker (an assistant, AI, bot or agent) is never a fact "
            "about the\n  user: omit it from `triples`, and in the episode attribute it to that speaker.") in EXTRACT_PROMPT


# --------------------------------------------------------------------- the counter's other carriers (INV-S7)
def test_s7_the_mcp_tool_result_strips_the_counter():
    """An operator counter never reaches the model (0031 §4d), like its siblings. Read from the source, so the floor
    lane (no `mcp` extra) runs it too. Mutant: the counter left out of the strip list."""
    import ast
    tree = ast.parse((SRC / "mcp_server.py").read_text())
    strip = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", None) == "_OPERATOR_ONLY" for t in n.targets))
    assert "speaker_restricted" in ast.literal_eval(strip)


def test_s7_the_dry_run_reports_the_counter(tmp_path):
    """`veracium remember --dry-run` prints the ingest's counters verbatim. Mutant: the counter left out."""
    from veracium import dryrun
    dr = dryrun.run(str(tmp_path / "d.db"), _llm(_t("located_at", "Toronto")), U, MIXED, author=EvidenceAuthor.USER,
                    date=DATE, context=EvidenceContext.direct())
    assert dr.result["speaker_restricted"] == 1 and "speaker_restricted=1" in dryrun.render(dr)
