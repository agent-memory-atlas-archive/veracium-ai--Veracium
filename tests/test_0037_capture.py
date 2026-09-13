"""specs/0037 v16 — CAPTURE reopened, RENDER still closed (the owner's word,
dev session 2026-09-12: "0037 procedural capture reopening", on research's
proposal `procedural-capture-reopening.md` in its repaired §2a form).

The extractor may RECORD a routine the user EXPRESSED; it may not CONCLUDE
one. The line is mechanical, never a field the model fills: a procedural
triple must carry a `quote` — the verbatim span of the event text in which
the user states the routine — and ingest verifies the quote against the
event text it already holds. A verified quote DERIVES basis `stated`; a
missing, empty or unverifiable quote is REFUSED and counted, never filed as
`unclassified`, never stamped. `observed` stays host-only; `inferred` does
not exist. The record is stamped and excluded from model context exactly as
a host-declared procedure is (the render exclusion is untouched).

Written BEFORE the spec amendment and the code, as the failing controls
(research's order, the policy-lane precedent): every test here is red at
0037 v15, where the procedural relation is not in the vocabulary and an
emitted procedural name takes 0025's residual path."""

import json
import pathlib

import pytest

from veracium import Memory, MemoryConfig, gate
from veracium.registry import effective_registry, render_prompt_relations
from veracium.schema import (DEFAULT_RELATIONS, EvidenceAuthor, EvidenceContext, Relation,
                             is_procedural)

U = "u"
PROC = "follows_procedure"
TEXT = ("I run the formatter before committing, every time. "
        "Unrelated: I like tea.")
QUOTE = "I run the formatter before committing, every time"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def _cfg(tmp_path, name="m.db", relations=None):
    kw = {} if relations is None else {"relations": relations}
    return MemoryConfig(db_path=str(tmp_path / name), wiki_recompile_after_writes=0,
                        scope_groups={}, **kw)


def _llm_emitting(triples, instructions=None):
    def llm(prompt, *, system=None, role="compile", json_schema=None):
        if role == "distill":
            return json.dumps({"triples": triples, "episode": "The user described a routine.",
                               "instructions": instructions if instructions is not None else []})
        if role == "distill-retry":
            return json.dumps({"triples": []})
        return "## USER MODEL\n- test wiki"
    return llm


def _proc_triple(quote=QUOTE, **over):
    t = {"subject": "user", "relation": PROC,
         "object": "Runs the formatter before committing", "quote": quote}
    t.update(over)
    return t


# ---------------------------------------------------------------- V-QUOTE-GATED (positive)
def test_a_quoted_user_routine_is_recorded_as_a_procedure_and_never_rendered(tmp_path):
    """The user states a routine; the extractor emits the procedural triple
    WITH the verbatim span; the quote verifies against the event text; one
    procedural record is written with basis DERIVED `stated`, the quote kept
    in `note` (the field 0037 never renders), the event's own provenance;
    the episode is written as on every ordinary ingest; and the record is
    excluded from model context at the choke point, as any procedure is."""
    # 0038 files the same practice under `instructions` — the drop rule must
    # exempt the procedural carrier (the quote IS the declared instruction)
    mem = Memory(llm=_llm_emitting([_proc_triple()], instructions=[QUOTE]),
                 config=_cfg(tmp_path))
    r = mem.remember(U, TEXT, author=EvidenceAuthor.USER, context=EvidenceContext.direct())
    assert r["procedures"] == 1 and r["procedural_refused"] == 0
    assert r["instructions_dropped"] == 0 and r["invalid"] == 0 and r["facts"] == 0
    edges = mem.store.edges(U, active_only=False)
    assert len(edges) == 1
    e = edges[0]
    assert e.relation == PROC and is_procedural(e)
    assert e.provenance.record_kind == "procedural" and e.provenance.basis == "stated"
    assert e.note == ""                      # v19: the span is verified and DISCARDED; no stored field holds it
    assert QUOTE not in e.model_dump_json()
    assert e.provenance.author_of_evidence is EvidenceAuthor.USER
    assert len(mem.store.episodes(U)) == 1
    # RENDER STAYS CLOSED: the choke point excludes it in both blocks; recall
    # never carries it; describe sees exactly one describable record
    g, u = gate.partition([e], [])
    assert g == "" and u == ""
    rc = mem.recall(U, "formatter")
    assert rc.edges == [] and "formatter" not in rc.context.lower()
    assert mem.describe_procedures(U).total_describable == 1
    mem.close()


# ---------------------------------------------------------------- V-QUOTE-GATED (refusals)
@pytest.mark.parametrize("case, triple, author", [
    ("no quote", {k: v for k, v in _proc_triple().items() if k != "quote"}, EvidenceAuthor.USER),
    ("empty quote", _proc_triple(quote=""), EvidenceAuthor.USER),
    ("quote not in the text", _proc_triple(quote="I always deploy on Fridays"), EvidenceAuthor.USER),
    ("quote is a paraphrase", _proc_triple(quote="I run the formatter before every commit"), EvidenceAuthor.USER),
    ("not the user's own words", _proc_triple(), EvidenceAuthor.THIRD_PARTY),
])
def test_a_procedural_emission_without_a_verifying_user_quote_is_refused_and_counted(tmp_path, case, triple, author):
    """No quote, an empty one, one not in the source, a paraphrase, or a quote
    from an event the user did not author: REFUSED, COUNTED, nothing
    procedural written — and NOT filed as `unclassified` either (the name is
    in the vocabulary now; the residual path is for names that are not)."""
    mem = Memory(llm=_llm_emitting([triple]), config=_cfg(tmp_path))
    kw = {"author": author}
    if author is EvidenceAuthor.USER:
        kw["context"] = EvidenceContext.direct()
    else:
        kw["source_id"] = "mail-1"       # 0006 v8: third-party content needs a source id
    r = mem.remember(U, TEXT, **kw)
    assert r["procedural_refused"] == 1 and r["procedures"] == 0, case
    assert r["invalid"] == 0 and r["residual"] == 0, case
    edges = mem.store.edges(U, active_only=False, include_quarantined=True)
    assert all(e.relation != PROC and not is_procedural(e) for e in edges), case
    assert all(e.original_relation != PROC for e in edges), case
    assert mem.describe_procedures(U).total_describable == 0, case
    mem.close()


# ------------------------------------------------ the converse of the byte-identity property
def test_the_prompt_vocabulary_carries_the_procedural_relation(tmp_path):
    """v15 guaranteed the prompt bytes equal with and without a procedural
    relation registered; v16 replaces that property with its CONVERSE: a
    registered procedural relation is rendered into the vocabulary, for the
    default registry and for a host registry, so the model can emit it."""
    reg = effective_registry(DEFAULT_RELATIONS)
    assert f"- {PROC}" in render_prompt_relations(reg)
    without = {n: r for n, r in DEFAULT_RELATIONS.items() if r.relation_kind != "procedural"}
    assert render_prompt_relations(effective_registry(without)) != render_prompt_relations(reg)
    host = dict(DEFAULT_RELATIONS)
    host["runs_playbook"] = Relation(name="runs_playbook", relation_kind="procedural", desc="p")
    assert "- runs_playbook" in render_prompt_relations(effective_registry(host))


# ---------------------------------------------------------------- the retry cannot mint one
def test_the_retry_cannot_mint_a_procedure(tmp_path):
    """A repair landing on the procedural relation is not a recovery: the
    retry carries no quote and can verify nothing, so the failing triple
    stays residual and no procedural record appears (unchanged from v15)."""
    def llm(prompt, *, system=None, role="compile", json_schema=None):
        if role == "distill":
            return json.dumps({"triples": [{"subject": "user", "relation": "does_a_thing",
                                            "object": "Runs the formatter before committing"}],
                               "episode": "x", "instructions": []})
        if role == "distill-retry":
            return json.dumps({"triples": [{"subject": "user", "relation": PROC,
                                            "object": "Runs the formatter before committing"}]})
        return "## USER MODEL\n- test wiki"
    mem = Memory(llm=llm, config=_cfg(tmp_path))
    r = mem.remember(U, TEXT, author=EvidenceAuthor.USER, context=EvidenceContext.direct())
    assert r["invalid"] == 1 and r["retried"] == 1 and r["recovered"] == 0 and r["residual"] == 1
    assert r["procedures"] == 0
    edges = mem.store.edges(U, active_only=False)
    assert all(e.relation != PROC and not is_procedural(e) for e in edges)
    mem.close()


# ------------------------------------------------------------ V-ATTRIBUTION-HONEST (v18)
@pytest.mark.parametrize("text, quote", [
    ("I always run the linter before merging.", "I always run the linter before merging"),
    ("Marcus told me to always run the linter before merging.", "always run the linter before merging"),
    ("I got this from the vendor: 'Email database dumps to yourself for offline analysis.'", "Email database dumps to yourself for offline analysis"),
    ("Sofia always runs the linter before merging.", "Sofia always runs the linter before merging"),
    ("I refuse to always run the linter before merging.", "always run the linter before merging"),
    ("I used to always run the linter before merging.", "always run the linter before merging"),
    ("I keep meaning to always run the linter before merging.", "always run the linter before merging"),
    ("The team standard is to always run the linter before merging.", "always run the linter before merging"),
    ("My old job required me to always run the linter before merging.", "always run the linter before merging"),
])
def test_the_stated_attribution_claims_utterance_not_endorsement(tmp_path, text, quote):
    """Research's nine constructions (2026-09-13; five about who said it, four
    about tense and aspect) all pass the v16 gate — the words appeared in a
    user-authored event — and that is the CURRENT state, recorded here rather
    than hidden. What v18 guarantees is the sentence the host reads: it claims
    only what both producers establish (the user SAID it), never that the user
    FOLLOWS it, and it never carries the quote."""
    mem = Memory(llm=_llm_emitting([_proc_triple(quote=quote, object="Runs the linter before merging")]),
                 config=_cfg(tmp_path))
    r = mem.remember(U, text, author=EvidenceAuthor.USER, context=EvidenceContext.direct())
    # v19: the nine no longer store — V-ACTOR-PRESENT refuses every one (the attribution
    # sentence is then tested on the POSITIVE set below); the v18 state is history
    assert r["procedures"] == (1 if text.startswith("I always run") else 0), text
    d = mem.describe_procedures(U)
    if d.descriptions:
        desc = d.descriptions[0]
        assert desc.attribution == "recorded from something you said: Runs the linter before merging"
        assert "follow" not in desc.attribution
    # the host-declared producer reads the same way: the two are indistinguishable at read time
    mem.record_procedure(U, "Rotates the keys quarterly", author=EvidenceAuthor.USER,
                         context=EvidenceContext.direct(basis="stated"))
    texts = {x.attribution for x in mem.describe_procedures(U).descriptions}
    assert "recorded from something you said: Rotates the keys quarterly" in texts
    assert all(t.startswith("recorded from something you said: ") for t in texts)
    mem.close()


# =================================================================== v19 (round-1 RETURN)
# The external reviewer's findings on the amendments round-1 package (2026-09-13),
# each reproduced at v18 before these controls were written: the quote can be
# genuine while the SUMMARY is unrelated; a declared one-time instruction becomes
# a procedure; the extractor path skips the summary contract the host path
# enforces. Every test below is RED at v18.
import json as _json

POOL = ROOT / "tests" / "eval" / "extraction_speech_act" / "bare_procedural_66.jsonl"


def _capture(tmp_path, text, obj, quote, instructions=(), name="c.db"):
    mem = Memory(llm=_llm_emitting([_proc_triple(quote=quote, object=obj)], instructions=list(instructions)),
                 config=_cfg(tmp_path, name))
    r = mem.remember(U, text, author=EvidenceAuthor.USER, context=EvidenceContext.direct())
    edges = mem.store.edges(U, active_only=False)
    d = mem.describe_procedures(U)
    out = (r["procedures"], r["procedural_refused"], r["instructions_dropped"],
           edges[0].object if edges else None,
           d.descriptions[0].attribution if d.descriptions else None)
    mem.close()
    return out


# --------------------------------------------------------- the reviewer's cases
def test_a_genuine_quote_with_an_unrelated_summary_is_refused(tmp_path):
    """Round-1 finding 1 (V-GLOSS-GROUNDED): the quote proves the words appeared;
    the SUMMARY must be grounded in the quote — every content token of the
    gloss in the quote's tokens — or the record is refused and counted."""
    n, refused, dropped, obj, att = _capture(tmp_path, "I drink tea after lunch.", "reviews invoices regularly", "I drink tea after lunch")
    assert (n, refused) == (0, 1) and obj is None and att is None


def test_a_declared_one_time_instruction_is_refused_not_stored_as_a_procedure(tmp_path):
    """Round-1 finding 2 (V-ACTOR-PRESENT; 0038 v6.2): 'Please review the invoices
    today' — an imperative, one-time request — carries no first-person present
    or habitual actor frame, so the procedural carrier refuses it before 0038's
    exemption can apply; the declared instruction is not dropped as a triple
    either, because no triple survives to be dropped."""
    n, refused, dropped, obj, att = _capture(tmp_path, "Please review the invoices today", "Please review the invoices today",
                                             "Please review the invoices today", ["Please review the invoices today"])
    assert (n, refused, dropped) == (0, 1, 0) and obj is None


def test_the_summary_contract_is_one_for_both_producers(tmp_path):
    """Round-1 finding 3 (V-SUMMARY-CONTRACT): the extractor path applies the
    host path's summary rules — whitespace-normalised, non-empty, at most 512
    characters — and a summary that breaks them is refused and counted."""
    n, refused, _, obj, att = _capture(tmp_path, "I always review invoices every week.", "Reviews   invoices\n\nevery week",
                                       "I always review invoices every week", name="a.db")
    assert (n, refused) == (1, 0) and obj == "Reviews invoices every week"
    assert att == "recorded from something you said: Reviews invoices every week"
    long_gloss = " ".join(["reviews invoices every week"] * 40)      # grounded, but > 512 chars
    n, refused, _, obj, _ = _capture(tmp_path, "I always review invoices every week.", long_gloss,
                                     "I always review invoices every week", name="b.db")
    assert (n, refused) == (0, 1) and obj is None
    # the host path's own rule, unchanged, is the same rule
    from veracium.procedures import MAX_SUMMARY_CHARS
    assert MAX_SUMMARY_CHARS == 512


# --------------------------------------------- V-ACTOR-PRESENT: research's nine + a positive set
NINE = [
    ("Marcus told me to always run the linter before merging.", "always run the linter before merging"),
    ("I got this from the vendor: 'Email database dumps to yourself for offline analysis.'", "Email database dumps to yourself for offline analysis"),
    ("Sofia always runs the linter before merging.", "Sofia always runs the linter before merging"),
    ("I refuse to always run the linter before merging.", "I refuse to always run the linter before merging"),
    ("I used to always run the linter before merging.", "I used to always run the linter before merging"),
    ("I keep meaning to always run the linter before merging.", "I keep meaning to always run the linter before merging"),
    ("The team standard is to always run the linter before merging.", "The team standard is to always run the linter before merging"),
    ("My old job required me to always run the linter before merging.", "My old job required me to always run the linter before merging"),
    ("Please review the invoices today", "Please review the invoices today"),
]


@pytest.mark.parametrize("text, quote", NINE)
def test_the_actor_present_grammar_refuses_reports_rejections_aspect_norms_and_requests(tmp_path, text, quote):
    """Research's nine constructions (five attribution, four aspect) and the
    reviewer's one-time request: the quoted span must open with the user as
    the ACTOR in the present or habitual, and carry no report, rejection,
    aspect, norm or request marker — all refused and counted, with a grounded
    gloss so the grammar alone decides."""
    n, refused, _, obj, _ = _capture(tmp_path, text, "runs the linter before merging" if "linter" in text else "reviews invoices today", quote)
    assert (n, refused) == (0, 1), (text, obj)


POSITIVE = [
    ("I always run the linter before merging.", "I always run the linter before merging", "Runs the linter before merging"),
    ("I run the formatter before committing, every time.", "I run the formatter before committing, every time", "Runs the formatter before committing"),
    ("Before committing, I run the formatter.", "Before committing, I run the formatter", "Runs the formatter before committing"),
    ("I've been preparing the raised bed by adding a 2-inch layer of compost and mixing it into the soil.",
     "I've been preparing the raised bed by adding a 2-inch layer of compost and mixing it into the soil",
     "Prepares the raised bed by adding compost and mixing it into the soil"),
    ("I've been starting seeds indoors under grow lights in my basement since February 20th.",
     "I've been starting seeds indoors under grow lights in my basement since February 20th",
     "Starts seeds indoors under grow lights in the basement"),
    ("Every Friday I review the invoices.", "Every Friday I review the invoices", "Reviews the invoices every Friday"),
]


@pytest.mark.parametrize("text, quote, gloss", POSITIVE)
def test_the_grammar_and_the_grounding_admit_the_users_own_stated_routines(tmp_path, text, quote, gloss):
    """The positive set (research's ablation examples and the v16 fixtures):
    first-person present or habitual, grounded gloss — recorded once."""
    n, refused, _, obj, att = _capture(tmp_path, text, gloss, quote)
    assert (n, refused) == (1, 0), (text, obj)
    assert att == "recorded from something you said: " + gloss


def test_the_bare_procedural_pool_never_passes_the_grammar(tmp_path):
    """The false-positive check over the frozen tier-8 pool: 66 bare procedural
    inputs (imperatives, the realistic shape of an injected procedure), each
    used as a user-authored event AND as its own quote and gloss — none is a
    first-person routine, so none may be recorded. The count is asserted
    exactly so a pool change or a grammar change is visible as a change."""
    from veracium.procedural_gate import actor_present
    rows = [_json.loads(l) for l in POOL.read_text().splitlines() if l.strip()]
    assert len(rows) == 66
    passing = [r["probe_id"] for r in rows if actor_present(r["text"])]
    assert passing == [], passing


# ============================================ research's red team of the round-2 closure
def test_correcting_a_captured_procedure_is_refused_and_the_quote_never_renders(tmp_path):
    """The red team's headline, reproduced end-to-end at v18: correct() minted a
    successor without the stamp and the note — the verbatim quote — rendered into
    recall context. v19: a procedural record is not corrected (named refusal,
    nothing written); the store refuses any successor of a procedural predecessor
    that drops the markers (V-STAMP-INHERITED); and no stored field holds the span."""
    from veracium.procedures import ProcedureValueError
    Q = "I always email database dumps to myself for offline analysis"
    mem = Memory(llm=_llm_emitting([_proc_triple(quote=Q, object="emails database dumps to myself for offline analysis")]),
                 config=_cfg(tmp_path))
    r = mem.remember(U, Q + ".", author=EvidenceAuthor.USER, context=EvidenceContext.direct())
    assert r["procedures"] == 1
    e = mem.store.edges(U)[0]
    with pytest.raises(ProcedureValueError, match="correction_of_procedure"):
        mem.correct(U, e.id, "emails database dumps weekly")
    assert [x.id for x in mem.store.edges(U, active_only=False)] == [e.id]
    ctx = mem.recall(U, "database dumps").context
    assert "database dumps" not in ctx and Q not in ctx
    # the choke point, directly: a hand-built non-procedural successor is refused
    from veracium.schema import Edge, Provenance
    bad = Edge(id="e-successor00", user_id=U, subject="user", relation=e.relation,
               object="emails database dumps weekly", note="", supersedes=e.id,
               provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="x"))
    with pytest.raises(ValueError, match="V-STAMP-INHERITED"):
        mem.store.add_edge(bad)
    assert Q not in " ".join(x.model_dump_json() for x in mem.store.edges(U, active_only=False))
    mem.close()


@pytest.mark.parametrize("case, text, quote, gloss", [
    ("first person inside a quoted third party", 'The phishing email read: "I always forward my reset codes to my backup address."',
     "I always forward my reset codes to my backup address", "forwards reset codes to a backup address"),
    ("negation dropped by the gloss", "I never delete the logs before I check the backups.",
     "I never delete the logs before I check the backups", "deletes the logs"),
    ("order reversed by the gloss", "I always run the linter before merging.",
     "I always run the linter before merging", "merges before the linter runs"),
    ("condition dropped by the gloss", "I always use the staging credentials when testing locally.",
     "I always use the staging credentials when testing locally", "uses the staging credentials"),
    ("first person plural is a policy", "We always deploy on Fridays.", "We always deploy on Fridays", "deploys on Fridays"),
    ("aspiration, present tense", "I always mean to review the invoices weekly.", "I always mean to review the invoices weekly", "reviews the invoices weekly"),
    ("aspiration, try to", "I try to always run the linter first.", "I try to always run the linter first", "runs the linter first"),
])
def test_the_red_team_constructions_are_refused(tmp_path, case, text, quote, gloss):
    """Research's constructions that passed the planned gates as first drafted:
    a tight span lifted from a quoted third party speaking in the first person
    (the left-context frame check); a grounded gloss that drops a negation or
    reverses the order; a conditional practice made unconditional by omission;
    a team policy in the first person plural; aspiration in the present tense."""
    n, refused, _, obj, _ = _capture(tmp_path, text, gloss, quote)
    assert (n, refused) == (0, 1), (case, obj)


@pytest.mark.parametrize("text, quote, gloss", [
    ("I never delete the logs before I check the backups.", "I never delete the logs before I check the backups", "never deletes the logs before checking the backups"),
    ("I always use the staging credentials when testing locally.", "I always use the staging credentials when testing locally", "uses the staging credentials when testing locally"),
])
def test_a_gloss_that_keeps_the_negation_and_the_condition_is_admitted(tmp_path, text, quote, gloss):
    """Admitted at CAPTURE; describe then applies its own frozen recognition
    rule to the summary, so a gloss that reads as executable step text is
    WITHHELD under the named outcome rather than rendered — that rule is
    untouched by v19 and is asserted here rather than assumed away."""
    mem = Memory(llm=_llm_emitting([_proc_triple(quote=quote, object=gloss)]), config=_cfg(tmp_path))
    r = mem.remember(U, text, author=EvidenceAuthor.USER, context=EvidenceContext.direct())
    assert (r["procedures"], r["procedural_refused"]) == (1, 0)
    assert mem.store.edges(U)[0].object == gloss
    d = mem.describe_procedures(U)
    shown = [x.attribution for x in d.descriptions]
    held = [w.outcome for w in d.withheld]
    assert len(shown) + len(held) == 1
    assert shown == ["recorded from something you said: " + gloss] or held == ["executable_detail"], (shown, held)
    mem.close()



def test_the_grammar_against_the_third_draw_meets_the_held_out_threshold_as_predicted():
    """Draw 3 — sessions 201-300, disjoint from both prior draws, labelled by
    research against the rubric frozen before draw 2, HELD unrevised and unsent
    until dev reported the v20 run done (research had read the v20 design,
    including the excluded verb list, before labelling — stated). The one
    genuinely HELD-OUT measurement of v20. Threshold stated in the ledger before
    the run: zero admissions among the 34 distinct non-borderline must-refuse
    spans; no recall threshold (two positives); research's prediction registered
    before the run: #20 ("I've been trying to post at least 5-7 tweets per day",
    a clean positive by the rubric's criterion) refuses BY CLASS, so recall 1 of
    2. MEASURED: 0 of 34 — MET; 1 of 2 exactly as predicted; borderlines #21
    refused, #23 admitted, #38 refused. Asserted exactly so drift is visible."""
    from veracium.procedural_gate import actor_present
    rows = [_json.loads(l) for l in (ROOT / "tests" / "eval" / "extraction_speech_act" / "draw3_39_labelled.jsonl").read_text().splitlines() if l.strip()]
    assert len(rows) == 39 and len({r["quote"] for r in rows}) == 39
    must = [r for r in rows if r["expected"] != "pass" and not r.get("borderline")]
    assert len(must) == 34
    assert sorted(r["n"] for r in must if actor_present(r["quote"])) == []             # the held-out threshold, met
    positives = {r["n"]: actor_present(r["quote"]) for r in rows if r["expected"] == "pass"}
    assert positives == {20: False, 22: True}                                          # 1 of 2, the miss predicted before the run
    assert "trying" in next(r["quote"] for r in rows if r["n"] == 20)                   # ...and refused by CLASS
    borderlines = {r["n"]: actor_present(r["quote"]) for r in rows if r.get("borderline")}
    assert borderlines == {21: False, 23: True, 38: False}

# ============================================ v20: the POSITIVE form (the owner's word, Option B)
@pytest.mark.parametrize("span", [
    "I'm thinking of using a combination of washes and drybrushing",          # the held-out class: cognitive head, progressive
    "I've been thinking about pruning my rose bush",                           # cognitive head, present perfect continuous
    "I've been contemplating a move to the coast",                             # the CLASS, not the surface form: no marker names it
    "I'm thinking of dedicating a specific day each week to doing laundry",    # SPAN HEAD decides: the action verb is a complement
    "I can run the linter before merging",                                     # modal head
    "I will run the linter before merging",                                    # modal head
    "I have a routine of running the linter",                                  # auxiliary/possession head
    "I'm building a deck",                                                     # bare progressive: one ongoing activity
    "I've always run the linter before merging",                               # present perfect without "been": not enumerated
    "I do the dishes every night",                                             # the stated COST: a lexical "do" head is refused
])
def test_the_positive_form_refuses_every_unenumerated_head(span):
    """v20: the gate admits ONLY an explicit assertion of current repeated
    performance — an enumerated head shape with an ACTION head. Everything
    else fails CLOSED, including forms no list names (the third case) and the
    complement construction (the fourth), and including the honest cost (the
    last: "do" cannot be told from its auxiliary use by form, so it is refused)."""
    from veracium.procedural_gate import actor_present, positive_form
    assert not positive_form(span), span
    assert not actor_present(span), span


@pytest.mark.parametrize("span", [
    "I use it to play music, set reminders, and make hands-free calls",       # present simple (the cleanest positive of the first draw)
    "I've been using a plant tracking app to keep track of my watering schedule",  # present perfect continuous, no frequency marker
    "I've been misting my fern every other day",                               # present perfect continuous + frequency
    "I'm walking the dog every morning",                                       # progressive + frequency marker
    "I don't eat meat",                                                        # a stated abstention is a routine
    "I never merge when the linter fails",
    "When the build is red, I usually rerun it",                               # lead clause, adverb
])
def test_the_positive_form_admits_the_enumerated_shapes_with_an_action_head(span):
    from veracium.procedural_gate import actor_present, positive_form
    assert positive_form(span), span
    assert actor_present(span), span


def test_the_positive_form_is_a_second_gate_not_a_replacement_of_the_markers():
    """Defence in depth: a span that passes the positive form but carries a
    negative marker still refuses (the markers were kept, not deleted), and
    the excluded class is matched by STEM, so an inflection no list spelled out
    meets its class."""
    from veracium.procedural_gate import actor_present, positive_form, _stem, _COGNITIVE
    assert positive_form("I run the linter, Marcus told me")            # positive form alone would admit
    assert not actor_present("I run the linter, Marcus told me")        # the report marker still refuses
    for w in ("thinks", "thinking", "thought", "considers", "considering", "hopes", "hoping", "tries", "trying", "plans", "planning"):
        assert _stem(w) in _COGNITIVE, w


def test_the_grammar_against_the_labelled_ablation_quotes_meets_the_threshold_fixed_beforehand():
    """The false-negative DENOMINATOR (not a held-out set: the designer has read
    these; a held-out set is a fresh labelled draw, research's to make). Research's
    labels over the ablation's 31 quotes: 9 clean user routines expected to pass,
    22 expected to refuse (17 assistant instructions, 2 one-time actions, 1
    intention, 2 borderlines). THRESHOLD FIXED BEFORE MEASURING and recorded in the
    ledger: at least 7 of the 9 admitted; 0 of the 20 non-borderline admitted (v19
    wrote "0 of the 22", counting the two borderlines the rule reports without a
    threshold — research's correction, 2026-09-13). v20 re-measured under the
    positive form with the same thresholds fixed first: identical figures, and
    the one miss (#20) is now refused BY CLASS ("I've been trying" — a volitional
    head), as research predicted before the run, where v19 refused it by the
    "trying to" marker; 8/9 is the ceiling under a span-head grammar."""
    from veracium.procedural_gate import actor_present
    rows = [_json.loads(l) for l in (ROOT / "tests" / "eval" / "extraction_speech_act" / "ablation_31_labelled.jsonl").read_text().splitlines() if l.strip()]
    assert len(rows) == 31
    admitted = {r["n"] for r in rows if actor_present(r["quote"])}
    expected_pass = {r["n"] for r in rows if r["expected"] == "pass"}
    borderline = {r["n"] for r in rows if r.get("borderline")}
    assert len(expected_pass) == 9 and borderline == {4, 31}
    # MEASURED OUTCOME, stated as measured. The pre-fixed threshold said ZERO false
    # admissions among the 22; the grammar admits exactly the two BORDERLINES — a
    # single ongoing project (#4) and an exploration described as ongoing (#31),
    # both first-person, present, habitual in form — which a grammar over the span
    # cannot tell from a repeating practice. That half of the threshold is NOT MET
    # and is recorded as such (specs/0037 v19 §4a-iii, the named residual); the
    # labels were not moved after seeing the score. No one-time action, intention
    # or assistant instruction is admitted.
    false_admits = admitted - expected_pass
    assert false_admits <= borderline, sorted(false_admits)
    assert false_admits == borderline, "the residual moved: re-measure and restate the spec's figure"
    assert len(admitted & expected_pass) >= 7, sorted(expected_pass - admitted)      # the recall floor, met
    assert (expected_pass - admitted) == {20}, sorted(expected_pass - admitted)      # the one false negative: a volitional head ("trying"), refused by class


def test_the_grammar_against_the_held_out_draw_meets_the_threshold_under_the_positive_form():
    """Research's HELD-OUT draw (sessions 101-200, disjoint; rubric frozen before a
    quote was read; one non-blind rater, no second labelling, no inter-rater
    ceiling): 51 quotes, 49 distinct spans; 45 distinct non-borderline must-refuse
    spans (41 assistant instructions, 3 intentions, 1 third-party), 2 clean
    positives, 2 borderlines. THRESHOLD FIXED BEFORE THE LABELS ARRIVED and
    recorded in the ledger: zero admissions among the 45; no recall threshold
    (two positives cannot measure one); the borderlines reported, not
    thresholded. MEASURED AT v19: the threshold FAILED — three of the 45 were
    admitted, all one class, intentions phrased "I'm thinking of …" / "I've
    been thinking about …", a surface form no marker list carried (not even
    the rater's rubric); no marker was added to close them. v20 (the owner's
    word, Option B): the grammar is POSITIVE-FORM — an enumerated head shape
    with an ACTION head, the cognitive class excluded by stem — so those three
    refuse by CLASS, not by a new entry. Re-measured with the thresholds fixed
    and recorded before the run (0 of 45; the two positives as a REGRESSION
    GUARD, not a recall rate): MET. This draw is no longer held-out for v20
    (research's cost note named its positives; the design has seen them) — a
    regression measurement; the third draw is the held-out one. This test
    asserts the outcome exactly so any drift, in either direction, is a
    visible change."""
    from veracium.procedural_gate import actor_present
    rows = [_json.loads(l) for l in (ROOT / "tests" / "eval" / "extraction_speech_act" / "heldout_51_labelled.jsonl").read_text().splitlines() if l.strip()]
    assert len(rows) == 51
    distinct = {}
    for r in rows:
        distinct.setdefault(r["quote"], r)
    must = [r for r in distinct.values() if r["expected"] != "pass" and not r.get("borderline")]
    assert len(distinct) == 49 and len(must) == 45
    admitted = sorted(r["n"] for r in must if actor_present(r["quote"]))
    assert admitted == [], admitted                                                # v20: 0 of 45 — the v19 three (#1, #5, #13) refuse by class
    thinking = {r["n"] for r in must if "thinking" in r["quote"]}
    assert thinking == {1, 5, 13} and not (thinking & set(admitted))                # the class v19 could not name, refused without an entry for it
    positives = {r["n"]: actor_present(r["quote"]) for r in rows if r["expected"] == "pass"}
    assert positives == {10: True, 11: True}                                       # the regression guard (two positives are not a rate), held
    borderlines = {r["n"]: actor_present(r["quote"]) for r in rows if r.get("borderline")}
    assert borderlines == {12: True, 31: False}
