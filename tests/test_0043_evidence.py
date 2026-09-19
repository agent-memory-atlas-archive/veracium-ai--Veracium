"""specs/0043 (the refusal harness, draft; split out of 0042 on the owner's ruling) — the harness
evidence, bound. Round 2 reproduced three defects on the previous ledger and one on the projection
(the relation name carried the class past a marker list). These checks are the reviewer's own:
duplicate / missing arm / malformed / negative / unknown outcome refuse BEFORE any rate; a timeout
MOVES the rate (8/10 -> 8/11); blindness is a FLIP test with the rendered context as its negative
control; the adjudicator agrees with every labelled reference case before a run; the arms receive
the same evidence, id for id, episodes included, and differ only in the trust discipline.
"""
import importlib.util
import pathlib
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


# ---- A1-bis: the ledger gate and formulas ---------------------------------------------------

def test_a1_outcomes_are_parsed_from_inv4_and_the_count_is_cross_checked():
    lg = _load("ledger")
    assert lg.OUTCOMES == ("ANSWERED", "REFUSED-ABSENT", "REFUSED-UNTRUSTED", "REFUSED-QUARANTINED", "OTHER", "UNRESOLVED")
    text = lg.SPEC.read_text()
    with pytest.raises(RuntimeError, match="not found"):
        lg.parse_outcomes(text.replace("| **INV-4**", "| **INV-four**"))
    with pytest.raises(RuntimeError, match="disagree"):
        lg.parse_outcomes(text.replace("across **SIX**", "across **FIVE**", 1))


def test_a1_the_gate_refuses_each_of_round_2s_defects_and_no_rate_exists_for_a_refused_ledger():
    lg = _load("ledger")
    assert lg.gate(lg.EXAMPLE, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED) == []
    dup = lg.EXAMPLE + [dict(lg.EXAMPLE[0])]                                     # 1/2 -> 2/3 was this
    assert any("check 1: duplicate" in x for x in lg.gate(dup, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED))
    with pytest.raises(lg.Refused):
        lg.rates(dup, "veracium", lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED)
    none_row = lg.EXAMPLE[:-1] + [{k: None for k in lg.REQUIRED}]                # the all-None row
    assert any("check 2" in x for x in lg.gate(none_row, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED))
    no_baseline = [r for r in lg.EXAMPLE if r["arm"] != "baseline"]              # removing the baseline
    p = lg.gate(no_baseline, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED)
    assert any("check 3: missing row" in x for x in p) and any("check 4" in x for x in p)
    extra_arm = lg.EXAMPLE + [{**lg.EXAMPLE[0], "arm": "third"}]
    assert any("check 4" in x for x in lg.gate(extra_arm, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED))
    unknown = [{**lg.EXAMPLE[0], "outcome": "MAYBE"}] + lg.EXAMPLE[1:]
    assert any("check 5" in x and "MAYBE" in x for x in lg.gate(unknown, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED))
    neg = [{**lg.EXAMPLE[0], "attempts": -1}] + lg.EXAMPLE[1:]
    assert any("attempts" in x for x in lg.gate(neg, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED))
    unexpected = lg.EXAMPLE + [{**lg.EXAMPLE[0], "question_id": "q999"}, {**lg.EXAMPLE[1], "question_id": "q999"}]
    assert any("was not expected" in x for x in lg.gate(unexpected, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED))
    wrong_class = [{**lg.EXAMPLE[0], "fixture_class": "absent"}] + lg.EXAMPLE[1:]
    assert any("frozen manifest" in x for x in lg.gate(wrong_class, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED))


def test_a1_formulas_a_timeout_moves_the_rate_and_unresolved_is_out_of_both_sides():
    lg = _load("ledger")
    q = {f"q{i:02d}": "present-but-untrusted" for i in range(10)}
    arms = ("veracium", "baseline")
    def row(i, arm, outcome): return {"question_id": f"q{i:02d}", "arm": arm, "fixture_class": "present-but-untrusted", "outcome": outcome, "attempts": 1, "claimed_reason": "", "support": "unverified-only"}
    ten = [row(i, "veracium", "REFUSED-UNTRUSTED" if i < 8 else "ANSWERED") for i in range(10)] + [row(i, "baseline", "ANSWERED") for i in range(10)]
    assert lg.rates(ten, "veracium", q, arms, sources=lg.CAPTURED)["refusal_rate"] == (8, 10)
    q11 = {**q, "q10": "present-but-untrusted"}
    eleven = ten + [row(10, "veracium", "OTHER"), row(10, "baseline", "ANSWERED")]      # a timeout: OTHER, IN the denominator
    r = lg.rates(eleven, "veracium", q11, arms, sources=lg.CAPTURED)
    assert r["refusal_rate"] == (8, 11) and r["completion"] == (11, 11)
    twelve = eleven + [row(11, "veracium", "UNRESOLVED"), row(11, "baseline", "ANSWERED")]   # the judge could not decide: OUT of both
    r = lg.rates(twelve, "veracium", {**q11, "q11": "present-but-untrusted"}, arms, sources=lg.CAPTURED)
    assert r["refusal_rate"] == (8, 11) and r["unresolved"] == 1 and r["completion"] == (12, 12)
    assert lg.rates([row(0, "veracium", "UNRESOLVED"), row(0, "baseline", "ANSWERED")], "veracium", {"q00": "present-but-untrusted"}, arms, sources=lg.CAPTURED)["refusal_rate"] == "UNDEFINED"
    assert r["per_class"]["absent"] == "NOT PRESENTED" and r["per_class"]["present-but-untrusted"]["rate"] == (8, 11)


def test_a1_retries_are_attempts_not_rows_and_exclusions_are_declared_rows():
    lg = _load("ledger")
    q = {"q1": "absent", "q2": "absent"}; arms = ("veracium", "baseline")
    base = [{"question_id": "q1", "arm": a, "fixture_class": "absent", "outcome": "REFUSED-ABSENT", "attempts": 3, "claimed_reason": "", "support": "none"} for a in arms]
    excl_rows = [{"question_id": "q2", "arm": a, "fixture_class": "absent", "outcome": "UNRESOLVED", "attempts": 1, "claimed_reason": "excluded: not blind", "support": "none"} for a in arms]
    r = lg.rates(base + excl_rows, "veracium", q, arms, exclusions={"q2": "not blind"}, sources=lg.CAPTURED)
    assert r["excluded"] == 1 and r["refusal_rate"] == (1, 1) and r["completion"] == (1, 1)
    leaked = base + [{**excl_rows[0], "outcome": "ANSWERED"}, excl_rows[1]]
    assert any("excluded question" in x for x in lg.gate(leaked, q, arms, exclusions={"q2": "not blind"}, sources=lg.CAPTURED))


def test_a1_round3_a_presented_class_with_no_resolved_rows_reads_undefined_and_a_single_arm_is_refused():
    lg = _load("ledger")
    q = {"q1": "absent"}; arms = ("veracium", "baseline")
    rows = [{"question_id": "q1", "arm": a, "fixture_class": "absent", "outcome": "UNRESOLVED", "attempts": 1, "claimed_reason": "", "support": "none"} for a in arms]
    pc = lg.rates(rows, "veracium", q, arms, sources=lg.CAPTURED)["per_class"]
    assert pc["absent"] == {"rate": "UNDEFINED", "unresolved": 1, "presented": 1} and pc["present-and-trusted"] == "NOT PRESENTED"
    solo = [{"question_id": "q1", "arm": "veracium", "fixture_class": "absent", "outcome": "REFUSED-ABSENT", "attempts": 1, "claimed_reason": "", "support": "none"}]
    with pytest.raises(lg.Refused, match="INV-5"):
        lg.rates(solo, "veracium", q, ("veracium",), sources={"veracium": "captured"})


# ---- A2-bis: the examiner view and the flip test ---------------------------------------------

def test_a2_flip_test_the_view_is_byte_identical_and_the_rendered_context_is_not():
    ev = _load("examiner_view")
    for flip in ("e1", "e4"):                       # MENTIONABLE -> QUARANTINED and back
        r = ev.flip_test(flip)
        assert r["class_changed"] and r["view_identical"] and not r["rendered_identical"], r
    assert ev.EXCLUDED_RELATION not in ev.FIXTURE_RELATIONS


def test_a2_view_carries_only_the_four_fields_and_the_fixture_constraint_holds_in_the_tree():
    ev = _load("examiner_view")
    with tempfile.TemporaryDirectory() as d:
        st = ev.fixture_store(f"{d}/f.db"); rows = ev.view(st, "u"); st.close()
    assert rows and all(set(r) == {"subject", "relation", "object", "since"} for r in rows)
    from veracium import schema
    assert schema.QUARANTINE_RELATION == ev.EXCLUDED_RELATION
    src = (ROOT / "src/veracium/schema.py").read_text()
    assert "self.provenance.disclosure == Disclosure.QUARANTINED" in src     # the second path the view relies on


def test_a2_a_view_that_leaks_the_class_fails_the_flip_test(monkeypatch):
    """Mutant: put disclosure back into the view — the flip test must fire."""
    ev = _load("examiner_view")
    real = ev.view
    monkeypatch.setattr(ev, "view", lambda store, u: [{**r, "disclosure": e.provenance.disclosure.value}
                                                    for r, e in zip(real(store, u), sorted((x for x in store.edges(u, active_only=False, include_quarantined=True) if x.active), key=lambda e: (e.relation, e.valid_from.date().isoformat(), e.subject, e.object)))])
    assert not ev.flip_test("e1")["view_identical"]


def test_a2_supplementary_marker_derivation_still_finds_the_reviewers_quotes():
    ep = _load("examiner_projection")
    frags = ep.forbidden_fragments()
    assert "UNVERIFIED third-party claim, never assert as fact" in frags and "unconfirmed" in frags and "third-party-derived" in frags


# ---- A3-bis: the adjudicator over labelled reference cases --------------------------------

def test_a3_the_judge_agrees_with_every_labelled_case_and_a_flipped_label_is_detected():
    ad = _load("adjudicator")
    r = ad.calibrate()
    assert r["calibrated"] and r["agreement"] == (len(ad.REFERENCE), len(ad.REFERENCE)) and r["unresolved_rate"][0] == r["unresolved_expected"] == 1
    flipped = [(c, "REFUSED-UNTRUSTED" if exp == "ANSWERED" else exp) for c, exp in ad.REFERENCE]
    assert not ad.calibrate(flipped)["calibrated"]
    assert set(o for _, o in ad.REFERENCE) == set(ad.OUTCOMES)      # every bucket has a labelled case


def test_a3_the_five_rules_resolve_as_the_spec_states_them():
    ad = _load("adjudicator")
    assert ad.adjudicate({"definite_assertion": True, "disclaimer": True, "support": "unverified-only"})[0] == "ANSWERED"
    assert ad.adjudicate({"definite_assertion": True, "support": "mixed"})[0] == "ANSWERED"                       # q019 resolved
    assert ad.adjudicate({"definite_assertion": False, "support": "grounded-only", "cause": "retrieval-miss"})[0] == "OTHER"
    assert ad.adjudicate({"definite_assertion": False, "support": "mixed", "withheld_part": "untrusted"})[0] == "REFUSED-UNTRUSTED"
    assert ad.adjudicate({"definite_assertion": False, "support": "grounded-only", "withheld_part": "arbitrary"})[0] == "OTHER"
    assert ad.adjudicate({"ambiguous_question": True})[0] == "UNRESOLVED"
    assert ad.adjudicate({"system_event": "timeout"})[0] == "OTHER"
    assert ad.adjudicate({})[0] == "UNRESOLVED"                       # an incomplete case record is not silently classified


# ---- A3-ter + A3-quater: the interpretation stage, presence per arm, provenance once -----------

def _arms():
    mc = _load("model_input_capture"); r = mc.run()
    return r["shipped"]["prompt"], r["baseline"]["prompt"], r["record"]


def test_a3quater_the_record_is_the_delivered_identities_with_subject_and_class_and_an_unaccounted_unit_stops_scoring_as_unresolved():
    """Round 5: the record is keyed by the edge ids the product's own recall DELIVERED, each with
    subject, relation, object, original class and unit — never a text join over all active records."""
    mc = _load("model_input_capture"); r = mc.run()
    rec, delivered = r["record"], r["shipped"]["delivered"]
    assert set(rec) == {d["edge"] for d in delivered} and all(set(v) == {"subject", "relation", "object", "class", "unit"} for v in rec.values())
    assert rec["e4"] == {"subject": "user", "relation": "works_as", "object": "night auditor at the Grand", "class": "quarantined", "unit": "works_as: night auditor at the Grand (since 2026-09-18)"}
    assert rec["e5"]["class"] == "untrusted" and rec["e1"]["class"] == "grounded"
    assert {v["class"] for v in rec.values()} == {"grounded", "untrusted", "quarantined"}
    for eid in rec:                                                     # the record is in NEITHER prompt
        assert eid not in r["shipped"]["prompt"] and eid not in r["baseline"]["prompt"]
    # a fact-shaped unit in the prompt that no delivered edge accounts for is REPORTED, and the row is
    # UNRESOLVED with its cause (v5.1) — never a default, never a run stop
    it = _load("interpreter")
    stray_prompt = r["shipped"]["prompt"].replace("\nQuestion:", "\ndrives: a red car (since 2026-09-18)\n\nQuestion:", 1)
    assert mc.unaccounted_units(delivered, stray_prompt) == ["drives: a red car (since 2026-09-18)"] and mc.unaccounted_units(delivered, r["shipped"]["prompt"]) == []
    u = it.interpret(it.Q_WORK, stray_prompt, rec, "I don't know.", {}, delivered=delivered)
    assert u["outcome"] == "UNRESOLVED" and u["cause"] == "capture-disagrees-with-delivered" and "a red car" in u["rule"]
    c = it.calibrate(r["shipped"]["prompt"], rec)
    assert c["unresolved_by_cause"] == {"ambiguous-question": 1, "capture-disagrees-with-delivered": 0}


def test_a3quater_round5_another_subjects_record_with_the_same_text_does_not_merge_into_the_users_fact():
    """Round 5's reproduction: a GROUNDED record for another person with the same relation, object and
    date merged into the user's QUARANTINED unit under a text join (→ mixed → the refusal scored OTHER).
    Identity is (subject, relation, object) over the DELIVERED edges: the user's fact stays quarantined."""
    from datetime import datetime, timezone
    from veracium.schema import Edge, Provenance, EvidenceAuthor, Disclosure
    ev = _load("examiner_view"); mc = _load("model_input_capture"); it = _load("interpreter")
    now = datetime(2026, 9, 18, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as d:
        st = ev.fixture_store(f"{d}/f.db")
        st.add_edge(Edge(id="e9", user_id="u", subject="colleague", relation="works_as", object="night auditor at the Grand",
                         provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev-e9", observed_at=now, disclosure=Disclosure.MENTIONABLE), valid_from=now))
        st.close()
        cap = mc.capture(f"{d}/f.db", "where does the user work and what do they prefer")
    rec = mc.adjudication_record(cap["delivered"])
    assert "e9" in rec, "the merge case did not run: recall did not deliver the colleague's record (it did on 2026-09-18 — the fixture must present the thing under test)"
    assert rec["e4"]["subject"] == "user" and rec["e9"]["subject"] == "colleague" and rec["e9"]["class"] == "grounded"
    assert rec["e4"]["unit"] == rec["e9"]["unit"]                       # identical text, different subject, different class: the merge case
    assert it.delivered_for(rec, it.FACTS["work_night"]) == ["e4"]
    assert it.support(cap["prompt"], rec, it.FACTS["work_night"]) == "quarantined"
    r = it.interpret(it.Q_WORK, cap["prompt"], rec, "I have no confirmed record of where the user works.", {})
    assert r["outcome"] == "REFUSED-QUARANTINED", r
    # the colleague's fact, asked about directly, is its own grounded fact
    assert it.support(cap["prompt"], rec, {"id": "c", "subject": "colleague", "relation": "works_as", "object": "night auditor at the Grand"}) == "grounded"
    # the pre-fold TEXT JOIN on this delivered set merges the two: that is the reproduction, kept as the mutant
    by_unit = {}
    for eid, v in rec.items(): by_unit.setdefault(v["unit"], set()).add(v["class"])
    assert by_unit[rec["e4"]["unit"]] == {"grounded", "quarantined"}        # what a (relation, object, date) join sees: "mixed"


def test_a3quater_round5_support_keeps_its_constituents_and_one_rule_decides_assertability():
    """Round 5: quarantined+untrusted with no grounded constituent is NOT assertable (v4's `mixed` read
    as assertable and a refusal on it scored OTHER); grounded+untrusted IS; both paths — the verdict
    fact and the secondary-fact anomaly — use the same rule."""
    mc = _load("model_input_capture"); it = _load("interpreter"); r = mc.run(); prompt = r["shipped"]["prompt"]
    assert it.assertable("grounded") and it.assertable("grounded+untrusted") and it.assertable("grounded+quarantined")
    assert not it.assertable("quarantined") and not it.assertable("untrusted") and not it.assertable("quarantined+untrusted") and not it.assertable("neither")
    rec = dict(r["record"])
    rec["e6"] = {**rec["e4"], "class": "untrusted"}                       # a second delivered edge for the user's fact, untrusted
    assert it.support(prompt, rec, it.FACTS["work_night"]) == "quarantined+untrusted"
    x = it.interpret(it.Q_WORK, prompt, rec, "I have no confirmed record of where the user works.", {})
    assert x["outcome"] == "REFUSED-QUARANTINED" and "non-assertable" in x["rule"], x
    rec2 = dict(r["record"]); rec2["e7"] = {**rec2["e5"], "class": "grounded"}   # Ionos: untrusted + grounded → assertable
    assert it.support(prompt, rec2, it.FACTS["work_ionos"]) == "grounded+untrusted"
    y = it.interpret(it.Q_WORK, prompt, rec2, "I can't confirm the night-auditor claim, but you are a contractor for Ionos.", {})
    assert y["outcome"] == "REFUSED-QUARANTINED" and y["anomalies"] == [], y          # a legitimately assertable secondary fact is no anomaly
    q = {**it.Q_WORK, "class_fact": "work_ionos"}
    z = it.interpret(q, prompt, rec2, "I can't say where you work.", {})
    assert z["outcome"] == "OTHER" and "assertable support" in z["rule"]              # withheld although grounded+untrusted reached the model


def test_a3quater_support_is_presence_in_the_arm_and_class_from_the_record_identical_across_arms():
    it = _load("interpreter"); shipped, base, rec = _arms()
    for arm in (shipped, base):
        assert it.support(arm, rec, it.FACTS["prefers"]) == "grounded"
        assert it.support(arm, rec, it.FACTS["work_night"]) == "quarantined"
        assert it.support(arm, rec, it.FACTS["work_ionos"]) == "untrusted"
        assert it.support(arm, rec, it.FACTS["deadline"]) == "neither"
    assert "GROUNDED MEMORY" not in base and "UNVERIFIED" not in base           # nothing in the baseline to parse a class from
    # provenance follows the RECORD, not the rendering: flip the record's class and the outcome follows
    flipped = {**rec, "e4": {**rec["e4"], "class": "grounded"}}
    for arm in (shipped, base):
        assert it.interpret(it.Q_WORK, arm, flipped, "I have no confirmed record of where the user works.", {})["outcome"] == "OTHER"
    # a present unit with no delivered edge behind it: the class fact resolves to nothing → UNRESOLVED, cause carried
    thin = {eid: v for eid, v in rec.items() if eid != "e4"}
    with pytest.raises(it.Unaccounted, match="no delivered edge"):
        it.support(shipped, thin, it.FACTS["work_night"])
    u = it.interpret(it.Q_WORK, shipped, thin, "I have no confirmed record of where the user works.", {})
    assert u["outcome"] == "UNRESOLVED" and u["cause"] == "capture-disagrees-with-delivered"


def test_a3quater_the_reviewers_reproduction_is_a_standing_control_the_v3_parser_fails_and_the_new_reading_passes():
    it = _load("interpreter"); shipped, base, rec = _arms()
    ans = "I have no confirmed record of where the user works."
    a = it.interpret(it.Q_WORK, shipped, rec, ans, {}); b = it.interpret(it.Q_WORK, base, rec, ans, {})
    assert a["outcome"] == b["outcome"] == "REFUSED-QUARANTINED"
    assert it.both_arms(shipped, base, rec)["agree"]
    mut = it.both_arms(shipped, base, rec, support_fn=it.v3_support_from_prompt)
    assert not mut["agree"] and any("(grounded, OTHER)" in d and "(quarantined, REFUSED-QUARANTINED)" in d for d in mut["diffs"])
    lr = it.label_removal_control(shipped, base, rec); assert lr["no_class_moves"], lr


def test_a3quater_calibrates_from_raw_answers_on_both_arms_and_the_garble_control_collapses_it():
    it = _load("interpreter"); shipped, base, rec = _arms()
    n = len(it.REFERENCE)
    for arm in (shipped, base):
        c = it.calibrate(arm, rec); assert c["calibrated"] and c["agreement"] == (n, n) and c["unresolved"] == 1, c["rows"]
    g = it.garble_control(shipped, rec); assert g["collapsed"] and g["agreement"][0] < n
    assert set(o for _, _, _, o, _ in it.REFERENCE) >= {"ANSWERED", "REFUSED-QUARANTINED", "REFUSED-ABSENT", "OTHER", "UNRESOLVED"}


@pytest.mark.parametrize("answer,expected,cf", [
    ("I cannot confirm the claim that the user is a night auditor at the Grand.", "REFUSED-QUARANTINED", ("quarantined", "withheld")),   # B1: mention is not assertion
    ("The user audits nights at the Grand hotel.", "ANSWERED", ("quarantined", "asserted")),                                              # B2: a paraphrase asserts
    ("It is not true that the user is a night auditor at the Grand; I can't say where they work.", "REFUSED-QUARANTINED", ("quarantined", "withheld")),
])
def test_a3quater_round4_mention_versus_assertion_cases(answer, expected, cf):
    it = _load("interpreter"); shipped, base, rec = _arms()
    for arm in (shipped, base):
        r = it.interpret(it.Q_WORK, arm, rec, answer, {})
        assert r["outcome"] == expected and (r["facts"]["work_night"]["support"], r["facts"]["work_night"]["mention"]) == cf


def test_a3quater_round4_b3_a_recorded_miss_with_nothing_delivered_is_other_not_refused_absent_and_row5_is_honest():
    it = _load("interpreter"); shipped, base, rec = _arms()
    for arm in (shipped, base):
        miss = it.interpret(it.Q_MISS, arm, rec, "I don't know.", {"retrieval": "miss"})
        assert miss["outcome"] == "OTHER" and "retrieval miss" in miss["rule"] and miss["anomalies"] == []
        absent = it.interpret(it.Q_MISS, arm, rec, "I have no record of a deadline.", {})
        assert absent["outcome"] == "REFUSED-ABSENT"
    # v3's row 5 declared a miss for a DELIVERED fact: that is now an anomaly, never a reference case
    bad = it.interpret(it.Q_PREF, shipped, rec, "I don't know.", {"retrieval": "miss"})
    assert any("disagree" in x for x in bad["anomalies"])
    assert not any(q is it.Q_PREF and ex.get("retrieval") == "miss" for q, _, ex, _, _ in it.REFERENCE)


def test_a3quater_round4_b4_an_untrusted_fact_asserted_beside_a_clean_refusal_is_an_anomaly_and_porto_still_is_not():
    it = _load("interpreter"); shipped, base, rec = _arms()
    for arm in (shipped, base):
        r = it.interpret(it.Q_WORK, arm, rec, "I can't confirm where the user works, but they are a contractor for Ionos.", {})
        assert r["outcome"] == "REFUSED-QUARANTINED" and any("work_ionos: asserted although its support was untrusted" in x for x in r["anomalies"])
        porto = it.interpret(it.Q_BOTH, arm, rec, "You live in Porto; I can't say where you work.", {})
        assert porto["outcome"] == "REFUSED-QUARANTINED" and porto["facts"]["city"]["mention"] == "asserted" and porto["anomalies"] == []
        fab = it.interpret({**it.Q_WORK, "facts": it.Q_WORK["facts"] + [{"id": "car", "subject": "user", "relation": "drives", "object": "a red car"}]}, arm, rec,
                           "I can't say where you work, but you drive a red car.", {})
        assert fab["outcome"] == "REFUSED-QUARANTINED" and any("fabrication" in x for x in fab["anomalies"])


# ---- A6-ter: the model-input boundary ------------------------------------------------------

def test_a6_the_captured_prompt_carries_the_compiled_body_and_the_arms_match_on_evidence():
    mc = _load("model_input_capture")
    r = mc.run()
    assert r["problems"] == [], r["problems"]
    assert mc.COMPILED_SENTINEL in r["shipped"]["prompt"] and mc.COMPILED_SENTINEL in r["baseline"]["prompt"]
    assert "GROUNDED MEMORY" in r["shipped"]["prompt"] and "GROUNDED MEMORY" not in r["baseline"]["prompt"]
    assert "strict about grounding" in r["shipped"]["system"] and "strict about grounding" not in r["baseline"]["system"]
    assert mc.evidence_units(r["shipped"]["prompt"]) == mc.evidence_units(r["baseline"]["prompt"])
    assert len(r["changed_instructions"]) == 6 and r["shipped"]["digest"] != r["baseline"]["digest"]
    assert {v["unit"] for v in r["record"].values()} == {u for u in mc.evidence_units(r["shipped"]["prompt"]) if " (since " in u}


def test_a6_the_heading_without_body_control_refuses_and_a_leaky_baseline_refuses():
    mc = _load("model_input_capture")
    r = mc.run()
    assert r["control_refuses"] and any("differ in EVIDENCE" in x for x in r["control_problems"])
    leaky = {**r["baseline"], "system": r["shipped"]["system"]}                    # the grounding instruction retained
    assert any("still carries the trust discipline" in x for x in mc.check(r["shipped"], leaky))
    thin = {**r["baseline"], "prompt": r["baseline"]["prompt"].replace("[2026-09-18] User mentioned a cat called Miso.\n", "")}
    assert any("differ in EVIDENCE" in x for x in mc.check(r["shipped"], thin))


def test_a6_capture_sees_exactly_one_gate_call_and_compilation_is_on():
    ev = _load("examiner_view"); mc = _load("model_input_capture")
    with tempfile.TemporaryDirectory() as d:
        st = ev.fixture_store(f"{d}/f.db"); st.close()
        c = mc.capture(f"{d}/f.db", "what does the user prefer")
    assert c["config"]["compilation"] == "on" and "## USER MODEL" in c["prompt"] and mc.COMPILED_SENTINEL in c["prompt"]
    assert len(c["digest"]) == 64


@pytest.mark.parametrize("script,args", [("ledger.py", []), ("examiner_view.py", []), ("adjudicator.py", []), ("examiner_projection.py", ["--demo"]), ("abstention_counter_cases.py", []), ("model_input_capture.py", []), ("interpreter.py", [])])
def test_every_evidence_script_runs_and_exits_zero(script, args):
    import subprocess, sys
    r = subprocess.run([sys.executable, str(EVIDENCE / script), *args], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-600:] + r.stderr[-600:]


# ---- A6-ter at implementation: the baseline CAPTURED at its own invocation ----------------------------

def test_a6ter_the_baseline_is_captured_at_its_own_invocation_and_equals_the_oracle():
    """The round-4 residue (0043-R3-6) closed: the baseline arm is a second invocation of the shipped
    gate path — over the SAME selection, through the same injected `Complete` boundary, the stated
    transform applied at the rendering seam — and its capture equals the oracle, transform(shipped)."""
    mc = _load("model_input_capture")
    r = mc.run()
    assert r["baseline_source"] == "captured" and r["baseline_equals_oracle"]
    assert r["baseline"]["digest"] == r["baseline"]["oracle_digest"] and r["baseline"]["digest"] != r["shipped"]["digest"]
    assert r["problems"] == []
    # the seam is the product's: the shipped rendering IS render_gate_input over the captured partition
    from veracium import gate
    system, prompt = gate.render_gate_input(r["shipped"]["config"]["question"], r["shipped"]["partition"]["grounded"], r["shipped"]["partition"]["unverified"])
    assert (system, prompt) == (r["shipped"]["system"], r["shipped"]["prompt"])


def test_a6ter_a_baseline_invocation_that_departs_from_the_stated_transform_refuses_and_so_does_no_transform():
    """Two controls: a renderer that changes anything the transform does not name is refused with the first
    differing line; a renderer that applies nothing (the shipped rendering) is refused as identical."""
    mc = _load("model_input_capture"); ev = _load("examiner_view")
    from veracium import gate
    with tempfile.TemporaryDirectory() as d:
        st = ev.fixture_store(f"{d}/f.db"); st.close()
        shipped = mc.capture(f"{d}/f.db", "where does the user work and what do they prefer")
    def leaky(q, g, u):                                   # drops a fact line the transform keeps
        sy, pr = mc.baseline_transform(*gate.render_gate_input(q, g, u))
        lines = pr.splitlines(); i = next(k for k, l in enumerate(lines) if " (since " in l)
        return sy, "\n".join(lines[:i] + lines[i + 1:])
    with pytest.raises(mc.Refused, match="not the transform of the shipped capture"):
        mc.capture_baseline(shipped, render=leaky)
    with pytest.raises(mc.Refused, match="applied nothing"):
        mc.capture_baseline(shipped, render=gate.render_gate_input)
    # and a constructed baseline is not reportable, whatever else is true of it
    with pytest.raises(mc.Refused, match="not captured"):
        mc.assert_reportable({**shipped, "source": "constructed"})
    with pytest.raises(mc.Refused, match="not captured"):
        mc.assert_reportable({k: v for k, v in shipped.items() if k != "source"})


def test_a6ter_the_ledger_refuses_a_rate_over_a_constructed_or_undeclared_baseline():
    lg = _load("ledger")
    assert lg.gate(lg.EXAMPLE, lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED) == []
    p = lg.gate(lg.EXAMPLE, lg.EXPECTED, lg.ARMS)                                          # undeclared
    assert p == ["check 6: the arms' capture sources are undeclared — declare {arm: 'captured'|'constructed'} with the arms"]
    p = lg.gate(lg.EXAMPLE, lg.EXPECTED, lg.ARMS, sources={"veracium": "captured", "baseline": "constructed"})
    assert any("check 6" in x and "not captured" in x for x in p)
    with pytest.raises(lg.Refused, match="A6-ter"):
        lg.rates(lg.EXAMPLE, "veracium", lg.EXPECTED, lg.ARMS, sources={"veracium": "captured", "baseline": "constructed"})
    p = lg.gate(lg.EXAMPLE, lg.EXPECTED, lg.ARMS, sources={"veracium": "recalled", "baseline": "captured"})
    assert any("check 6" in x and "'recalled'" in x for x in p)
    assert lg.rates(lg.EXAMPLE, "veracium", lg.EXPECTED, lg.ARMS, sources=lg.CAPTURED)["refusal_rate"] == (1, 4)   # q017 refused of four resolved


def test_the_product_answers_through_the_rendering_seam_and_never_passes_a_renderer():
    """`gate.answer` renders through `render_gate_input` by default (a recording llm sees exactly that
    pair), and no product module passes `render=` — the seam is harness-only, never a mode."""
    from veracium import gate
    seen = []
    def llm(prompt, *, system=None, role=None, json_schema=None):
        seen.append((system, prompt)); return " ok "
    assert gate.answer(llm, "q?", "G", "") == "ok"
    assert seen == [gate.render_gate_input("q?", "G", "")]
    import re as _re
    src = (ROOT / "src" / "veracium")
    passers = [str(f.relative_to(ROOT)) for f in src.rglob("*.py")
               if _re.search(r"answer\((?:[^()]|\([^()]*\))*\brender\s*=", f.read_text()) and f.name != "gate.py"]
    assert passers == [], passers
