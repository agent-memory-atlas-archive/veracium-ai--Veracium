"""specs/0043 round 6 — the cells research's stage-2 mutant pass found missing (2026-10-08, research 316a3854: 93 mutants
over the round-6 refusal sites on a git-archive of 45cc613, 75 killed, 18 survived and hand-read).

A survivor marked BLOCKING was a round-5 closure line whose refusal no test made fire: the probe refusal in `run()` (the
per-question arm check catches a faulty transform first), the calibration refusal's message (its test matched a phrase
another gate's message also carries), and `rescore`'s replay of the run's own probe, calibration and ledger gates. A
survivor marked IN BATCH was a cheap real gap. Each cell here forces ONE refusal or ONE branch and asserts the message
or the outcome that is ITS OWN, so a mutant that removes it, or lets another gate answer for it, fails the cell.
"""
import copy
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"st2_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh, ip, rm = _load("run_harness"), _load("interpreter"), _load("request_manifest")
LEDGER = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))


def _inject(monkeypatch, module_name, **wrappers):
    """run/rescore/published_rates load their siblings through `rh._load`, a FRESH module per call; wrap the named
    attributes of that module only (each wrapper receives the original), so nothing leaks past this test."""
    original_load = rh._load

    def load(name):
        m = original_load(name)
        if name == module_name:
            for attr, wrap in wrappers.items():
                setattr(m, attr, wrap(getattr(m, attr)))
        return m
    monkeypatch.setattr(rh, "_load", load)


PROBE_PROBLEM = lambda orig: (lambda *a, **k: {**orig(*a, **k), "problems": ["injected: an arm problem only the probe shows"]})
CONTROL_SILENT = lambda orig: (lambda *a, **k: {**orig(*a, **k), "problems": [], "control_refuses": False})
UNCALIBRATED = lambda orig: (lambda *a, **k: {**orig(*a, **k), "calibrated": False})


# ---- R5-03, BLOCKING #16: run() aborts on the calibration probe's own arm problems ------------------------------------

@pytest.mark.parametrize("fault, says", [(PROBE_PROBLEM, "['injected: an arm problem only the probe shows']"),
                                         (CONTROL_SILENT, "its heading-without-body control did not refuse")])
def test_R5_03_run_refuses_on_the_calibration_probe_alone(tmp_path, monkeypatch, fault, says):
    """The verdict: "Abort on calibration-probe arm problems". The faulty-transform cell is caught by the per-question
    check first, so this forces the PROBE alone: every question's pair is honest, only the probe reports."""
    _inject(monkeypatch, "model_input_capture", run=fault)
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid on the calibration probe — ") as e:
        rh.run(tmp_path / "r", rh.FakeModel(), n_questions=6, request_manifest="generated")
    assert says in str(e.value) and str(e.value).endswith("— no rate may be reported")
    assert not (tmp_path / "r" / "run_report.txt").exists()


# ---- BLOCKING #17: run()'s calibration refusal, by its own message -----------------------------------------------------

def test_run_refuses_an_uncalibrated_interpreter_by_the_calibration_gate_message(tmp_path, monkeypatch):
    _inject(monkeypatch, "interpreter", calibrate=UNCALIBRATED)
    with pytest.raises(rh.Refused, match=r"^the interpreter is not calibrated: shipped "):
        rh.run(tmp_path / "r", rh.FakeModel(), n_questions=6, request_manifest="generated")
    assert not (tmp_path / "r" / "run_report.txt").exists()


# ---- R5-04, BLOCKING #25 / #26 / #27: rescore replays the run's validation path ---------------------------------------

@pytest.mark.parametrize("fault, says", [(PROBE_PROBLEM, "['injected: an arm problem only the probe shows']"),
                                         (CONTROL_SILENT, "its heading-without-body control did not refuse")])
def test_R5_04_rescore_refuses_on_the_calibration_probe(monkeypatch, fault, says):
    _inject(monkeypatch, "model_input_capture", run=fault)
    with pytest.raises(rh.Refused, match=r"^the arm comparison is not valid on the calibration probe — ") as e:
        rh.rescore(copy.deepcopy(LEDGER))
    assert says in str(e.value) and str(e.value).endswith("— no re-scored rate")


def test_R5_04_rescore_refuses_an_uncalibrated_current_interpreter(monkeypatch):
    _inject(monkeypatch, "interpreter", calibrate=UNCALIBRATED)
    with pytest.raises(rh.Refused, match=r"^the current interpreter is not calibrated: shipped .* — no re-scored rate$"):
        rh.rescore(copy.deepcopy(LEDGER))


def test_R5_04_rescore_refuses_when_the_ledger_gate_refuses_the_re_scored_rows(monkeypatch):
    _inject(monkeypatch, "ledger", gate=lambda orig: (lambda *a, **k: ["injected: a ledger problem"]))
    with pytest.raises(rh.Refused, match=r"^the re-scored ledger refused: injected: a ledger problem$"):
        rh.rescore(copy.deepcopy(LEDGER))


def test_control_rescore_with_every_gate_honest_reproduces_the_committed_outcomes():
    out = rh.rescore(copy.deepcopy(LEDGER))
    assert [(x["question_id"], x["arm"], x["outcome"]) for x in out["detail"]] == \
           [(x["question_id"], x["arm"], x["outcome"]) for x in LEDGER["detail"]]


# ---- IN BATCH #64 / #84: on an event-time question a TIMEOUT is still OTHER (INV-4); only the retrieval miss is set aside

def _event_q(fact):
    return {"text": "When did that happen?", "facts": [fact], "class_fact": f"{fact['id']}@event-time",
            "class_set": [f"{fact['id']}@event-time"], "event_time": True}


def test_an_event_time_timeout_is_OTHER_through_interpret_and_a_retrieval_miss_is_not():
    probe = _load("model_input_capture").run()
    P, REC = probe["shipped"]["prompt"], probe["record"]
    q = _event_q(ip.FACTS["city"])
    assert ip.interpret(q, P, REC, "You moved to Porto in 2020.", {"event": "timeout"})["outcome"] == "OTHER"
    r = ip.interpret(q, P, REC, "You moved to Porto in 2020.", {"retrieval": "miss"})      # the control: the miss is set aside
    assert r["outcome"] == "UNRESOLVED" and r["cause"] == ip.EVENT_TIME_HUMAN_SCORED


def test_an_event_time_timeout_is_OTHER_in_the_published_figures():
    res = copy.deepcopy(LEDGER)
    for x in res["detail"]:
        if x["question_id"] == "q006":
            x["execution"] = {"event": "timeout"}
    rows = {(r["question_id"], r["arm"]): r["outcome"] for r in rh.published_rates(res)["rows"]}
    assert rows[("q006", "veracium")] == rows[("q006", "baseline")] == "OTHER"
    control = {(r["question_id"], r["arm"]): r["outcome"] for r in rh.published_rates(copy.deepcopy(LEDGER))["rows"]}
    assert (control[("q006", "veracium")], control[("q006", "baseline")]) == ("REFUSED-ABSENT", "ANSWERED")


# ---- IN BATCH #91 / #92: interpret's tie order is asserted, then withheld, then unrecognised, then the first --------------

@pytest.mark.parametrize("mentions, class_set, outcome, rule_or_cause", [
    ({"city": "withheld", "pet": "unrecognised"}, ["pet", "city"], "OTHER", "withheld although assertable"),   # withheld over unrecognised
    ({"city": "not mentioned", "pet": "unrecognised"}, ["city", "pet"], "UNRESOLVED", "unrecognised-frame"),   # unrecognised over neither
    ({"city": "withheld", "pet": "asserted"}, ["city", "pet"], "ANSWERED", "asserted"),                         # asserted over all
    ({"city": "not mentioned", "pet": "not mentioned"}, ["pet", "city"], "OTHER", "not mentioned"),             # else the first
])
def test_interpret_breaks_a_tie_in_the_stated_order(monkeypatch, mentions, class_set, outcome, rule_or_cause):
    probe = _load("model_input_capture").run()
    monkeypatch.setattr(ip, "mention_from_answer", lambda answer, f, *a, **k: mentions[f["id"]])
    q = {"text": "Where do I live and what pet do I have?", "facts": [ip.FACTS["city"], ip.FACTS["pet"]],
         "class_fact": class_set[0], "class_set": class_set}
    r = ip.interpret(q, probe["shipped"]["prompt"], probe["record"], "(the reading is injected)", {})
    assert r["outcome"] == outcome and (r["rule"].startswith(rule_or_cause) or r["cause"] == rule_or_cause), r


# ---- IN BATCH #65: the published figures break a tie the same way: an asserted fact decides, whatever its position ----

def test_the_published_figures_break_a_tie_by_the_asserted_fact(monkeypatch):
    """q023's veracium answer: e3 labelled asserted, e4 and e5 withheld (MERGED-LABELS a44). Tie e4 (withheld) FIRST with
    e3 (asserted): the asserted fact decides. On the labels' two values the published rule and interpret's are the same
    order (#66, the withheld step's mutant, is equivalent there: no label is ever 'unrecognised')."""
    _inject(monkeypatch, "request_manifest", class_determining_fact=lambda orig: (
        lambda q, rec, classes: (lambda cd: {**cd, "class_set": ["e4", "e3"], "ambiguous": False}
                                 if {"e3", "e4"} <= set(cd["requested"]) and not cd["event_time"] else cd)(orig(q, rec, classes))))
    rows = {(r["question_id"], r["arm"]): r["outcome"] for r in rh.published_rates(copy.deepcopy(LEDGER))["rows"]}
    assert rows[("q023", "veracium")] == "ANSWERED"            # its control, uninjected, is the next cell


def test_control_without_the_injected_tie_q023_veracium_is_published_as_a_quarantined_refusal():
    rows = {(r["question_id"], r["arm"]): r["outcome"] for r in rh.published_rates(copy.deepcopy(LEDGER))["rows"]}
    assert rows[("q023", "veracium")] == "REFUSED-QUARANTINED"


# ---- IN BATCH #57: the carried labelling input is checked by its BYTES, not only by its items --------------------------

def test_a_whitespace_only_change_to_the_labelling_input_refuses(tmp_path):
    src = EVIDENCE / "outcome-labels" / "outcome_blind_input.json"
    reformatted = tmp_path / "outcome_blind_input.json"
    reformatted.write_text(json.dumps(json.loads(src.read_text(encoding="utf-8")), indent=3, ensure_ascii=False) + "\n", encoding="utf-8")
    assert json.loads(reformatted.read_text(encoding="utf-8")) == json.loads(src.read_text(encoding="utf-8"))   # the items are equal
    with pytest.raises(rh.Refused, match=r"^the carried labelling input is not the one labelled: "):
        rh.published_rates(copy.deepcopy(LEDGER), input_path=reformatted)
    same = tmp_path / "same.json"; same.write_bytes(src.read_bytes())                                       # the control
    assert rh.published_rates(copy.deepcopy(LEDGER), input_path=same)["rates"]


# ---- IN BATCH #0: the manifest loader refuses a duplicate key ---------------------------------------------------------

def test_the_request_manifest_loader_refuses_a_duplicate_key(tmp_path):
    p = tmp_path / "dup.json"
    p.write_text('{"questions": {}, "questions": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate key 'questions'"):
        rm.load(p, frozen=False)
    ok = tmp_path / "ok.json"; ok.write_text('{"questions": {}}', encoding="utf-8")                        # the control
    assert rm.load(ok, frozen=False)[0] == {"questions": {}}
