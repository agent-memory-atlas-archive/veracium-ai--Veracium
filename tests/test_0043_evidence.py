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
    assert lg.gate(lg.EXAMPLE, lg.EXPECTED, lg.ARMS) == []
    dup = lg.EXAMPLE + [dict(lg.EXAMPLE[0])]                                     # 1/2 -> 2/3 was this
    assert any("check 1: duplicate" in x for x in lg.gate(dup, lg.EXPECTED, lg.ARMS))
    with pytest.raises(lg.Refused):
        lg.rates(dup, "veracium", lg.EXPECTED, lg.ARMS)
    none_row = lg.EXAMPLE[:-1] + [{k: None for k in lg.REQUIRED}]                # the all-None row
    assert any("check 2" in x for x in lg.gate(none_row, lg.EXPECTED, lg.ARMS))
    no_baseline = [r for r in lg.EXAMPLE if r["arm"] != "baseline"]              # removing the baseline
    p = lg.gate(no_baseline, lg.EXPECTED, lg.ARMS)
    assert any("check 3: missing row" in x for x in p) and any("check 4" in x for x in p)
    extra_arm = lg.EXAMPLE + [{**lg.EXAMPLE[0], "arm": "third"}]
    assert any("check 4" in x for x in lg.gate(extra_arm, lg.EXPECTED, lg.ARMS))
    unknown = [{**lg.EXAMPLE[0], "outcome": "MAYBE"}] + lg.EXAMPLE[1:]
    assert any("check 5" in x and "MAYBE" in x for x in lg.gate(unknown, lg.EXPECTED, lg.ARMS))
    neg = [{**lg.EXAMPLE[0], "attempts": -1}] + lg.EXAMPLE[1:]
    assert any("attempts" in x for x in lg.gate(neg, lg.EXPECTED, lg.ARMS))
    unexpected = lg.EXAMPLE + [{**lg.EXAMPLE[0], "question_id": "q999"}, {**lg.EXAMPLE[1], "question_id": "q999"}]
    assert any("was not expected" in x for x in lg.gate(unexpected, lg.EXPECTED, lg.ARMS))
    wrong_class = [{**lg.EXAMPLE[0], "fixture_class": "absent"}] + lg.EXAMPLE[1:]
    assert any("frozen manifest" in x for x in lg.gate(wrong_class, lg.EXPECTED, lg.ARMS))


def test_a1_formulas_a_timeout_moves_the_rate_and_unresolved_is_out_of_both_sides():
    lg = _load("ledger")
    q = {f"q{i:02d}": "present-but-untrusted" for i in range(10)}
    arms = ("veracium", "baseline")
    def row(i, arm, outcome): return {"question_id": f"q{i:02d}", "arm": arm, "fixture_class": "present-but-untrusted", "outcome": outcome, "attempts": 1, "claimed_reason": "", "support": "unverified-only"}
    ten = [row(i, "veracium", "REFUSED-UNTRUSTED" if i < 8 else "ANSWERED") for i in range(10)] + [row(i, "baseline", "ANSWERED") for i in range(10)]
    assert lg.rates(ten, "veracium", q, arms)["refusal_rate"] == (8, 10)
    q11 = {**q, "q10": "present-but-untrusted"}
    eleven = ten + [row(10, "veracium", "OTHER"), row(10, "baseline", "ANSWERED")]      # a timeout: OTHER, IN the denominator
    r = lg.rates(eleven, "veracium", q11, arms)
    assert r["refusal_rate"] == (8, 11) and r["completion"] == (11, 11)
    twelve = eleven + [row(11, "veracium", "UNRESOLVED"), row(11, "baseline", "ANSWERED")]   # the judge could not decide: OUT of both
    r = lg.rates(twelve, "veracium", {**q11, "q11": "present-but-untrusted"}, arms)
    assert r["refusal_rate"] == (8, 11) and r["unresolved"] == 1 and r["completion"] == (12, 12)
    assert lg.rates([row(0, "veracium", "UNRESOLVED"), row(0, "baseline", "ANSWERED")], "veracium", {"q00": "present-but-untrusted"}, arms)["refusal_rate"] == "UNDEFINED"
    assert r["per_class"]["absent"] == "NOT PRESENTED" and r["per_class"]["present-but-untrusted"]["rate"] == (8, 11)


def test_a1_retries_are_attempts_not_rows_and_exclusions_are_declared_rows():
    lg = _load("ledger")
    q = {"q1": "absent", "q2": "absent"}; arms = ("veracium", "baseline")
    base = [{"question_id": "q1", "arm": a, "fixture_class": "absent", "outcome": "REFUSED-ABSENT", "attempts": 3, "claimed_reason": "", "support": "none"} for a in arms]
    excl_rows = [{"question_id": "q2", "arm": a, "fixture_class": "absent", "outcome": "UNRESOLVED", "attempts": 1, "claimed_reason": "excluded: not blind", "support": "none"} for a in arms]
    r = lg.rates(base + excl_rows, "veracium", q, arms, exclusions={"q2": "not blind"})
    assert r["excluded"] == 1 and r["refusal_rate"] == (1, 1) and r["completion"] == (1, 1)
    leaked = base + [{**excl_rows[0], "outcome": "ANSWERED"}, excl_rows[1]]
    assert any("excluded question" in x for x in lg.gate(leaked, q, arms, exclusions={"q2": "not blind"}))


def test_a1_round3_a_presented_class_with_no_resolved_rows_reads_undefined_and_a_single_arm_is_refused():
    lg = _load("ledger")
    q = {"q1": "absent"}; arms = ("veracium", "baseline")
    rows = [{"question_id": "q1", "arm": a, "fixture_class": "absent", "outcome": "UNRESOLVED", "attempts": 1, "claimed_reason": "", "support": "none"} for a in arms]
    pc = lg.rates(rows, "veracium", q, arms)["per_class"]
    assert pc["absent"] == {"rate": "UNDEFINED", "unresolved": 1, "presented": 1} and pc["present-and-trusted"] == "NOT PRESENTED"
    solo = [{"question_id": "q1", "arm": "veracium", "fixture_class": "absent", "outcome": "REFUSED-ABSENT", "attempts": 1, "claimed_reason": "", "support": "none"}]
    with pytest.raises(lg.Refused, match="INV-5"):
        lg.rates(solo, "veracium", q, ("veracium",))


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


def test_a3quater_the_record_carries_every_fact_unit_with_its_class_from_the_store_and_refuses_an_unknown_unit():
    mc = _load("model_input_capture"); r = mc.run()
    rec = r["record"]
    assert {v["class"] for v in rec.values()} == {"grounded", "untrusted", "quarantined"}
    assert rec["works_as: night auditor at the Grand (since 2026-09-18)"] == {"edge": "e4", "class": "quarantined"}
    assert rec["works_as: contractor for Ionos (since 2026-09-18)"] == {"edge": "e5", "class": "untrusted"}
    assert rec["prefers: concise answers (since 2026-09-18)"]["class"] == "grounded"
    assert not any(u.startswith("[") or u.startswith("- COMPILED") for u in rec), "episodes and compiled lines are not fact units"
    # the record is in NEITHER prompt (it is an adjudication artifact, not model input)
    for u, v in rec.items():
        assert v["edge"] not in r["shipped"]["prompt"] and v["edge"] not in r["baseline"]["prompt"]
    # a fact unit the store cannot identify REFUSES rather than defaulting
    with tempfile.TemporaryDirectory() as d:
        ev = _load("examiner_view"); st = ev.fixture_store(f"{d}/f.db"); st.close()
        with pytest.raises(mc.Refused, match="no edge for it"):
            mc.adjudication_record(f"{d}/f.db", r["shipped"]["prompt"].replace("\nQuestion:", "\ndrives: a red car (since 2026-09-18)\n\nQuestion:", 1))


def test_a3quater_support_is_presence_in_the_arm_and_class_from_the_record_identical_across_arms():
    it = _load("interpreter"); shipped, base, rec = _arms()
    for arm in (shipped, base):
        assert it.support(arm, rec, it.FACTS["prefers"]) == "grounded"
        assert it.support(arm, rec, it.FACTS["work_night"]) == "quarantined"
        assert it.support(arm, rec, it.FACTS["work_ionos"]) == "untrusted"
        assert it.support(arm, rec, it.FACTS["deadline"]) == "neither"
    assert "GROUNDED MEMORY" not in base and "UNVERIFIED" not in base           # nothing in the baseline to parse a class from
    # provenance follows the RECORD, not the rendering: flip the record's class and the outcome follows
    flipped = {**rec, "works_as: night auditor at the Grand (since 2026-09-18)": {"edge": "e4", "class": "grounded"}}
    for arm in (shipped, base):
        assert it.interpret(it.Q_WORK, arm, flipped, "I have no confirmed record of where the user works.", {})["outcome"] == "OTHER"
    # a present unit the record does not carry REFUSES instead of defaulting
    thin = {u: v for u, v in rec.items() if not u.startswith("works_as: night")}
    with pytest.raises(it.Refused, match="does not carry it"):
        it.support(shipped, thin, it.FACTS["work_night"])


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
        fab = it.interpret({**it.Q_WORK, "facts": it.Q_WORK["facts"] + [{"id": "car", "relation": "drives", "object": "a red car"}]}, arm, rec,
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
    assert set(r["record"]) == {u for u in mc.evidence_units(r["shipped"]["prompt"]) if " (since " in u}


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
