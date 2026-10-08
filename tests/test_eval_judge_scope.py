"""The acceptance eval's judge (tests/eval/run_eval.py), offline: the owner's scoping, 2026-10-08 — claude-haiku-5-5
judges CONTENT questions under a role of its own, never the product's `gate` role.

Each guard is driven here with a canned provider and no model call: a probe that is not declared content, or that
reads as an aspect question (when / how long / what date), refuses the run; a provider that does not DECLARE a model for
the `judge` role refuses (a provider that falls back to a default for an unknown role would judge with the wrong model);
a token limit with no headroom refuses; a reply with no boolean verdict is retried once and then counted as a judge
failure, never a silent "incorrect"; and the grading call goes to the judge role, not to `gate`.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ev = _load("tests/eval/run_eval.py", "ej_run_eval")
cli = _load("examples/claude_cli_provider.py", "ej_cli")


class Canned:
    """A provider that records every call and answers from a script of replies."""
    def __init__(self, replies, models=None, max_tokens=4096):
        self.replies, self.calls = list(replies), []
        self._models = {"gate": "model-under-test", "judge": "claude-haiku-5-5"} if models is None else models
        self._max_tokens = max_tokens

    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        self.calls.append(role)
        return self.replies.pop(0)


def test_every_shipped_probe_declares_content_and_none_reads_as_an_aspect_question():
    scenarios = json.loads(ev.SCENARIOS.read_text())
    assert sum(len(sc["probes"]) for sc in scenarios) == 5
    ev.check_probes(scenarios)                                       # refuses on any violation


@pytest.mark.parametrize("probe, why", [
    ({"q": "Which client is the user working for?"}, "declares asks=None"),
    ({"q": "Which client is the user working for?", "asks": "aspect"}, "declares asks='aspect'"),
    ({"q": "When did the user move to Porto?", "asks": "content"}, "asks about an aspect"),
    ({"q": "How long has the user had the cat?", "asks": "content"}, "asks about an aspect"),
    ({"q": "What date did the user start the job?", "asks": "content"}, "asks about an aspect"),
])
def test_a_probe_outside_the_validated_scope_refuses_the_run(probe, why):
    with pytest.raises(ev.JudgeRefused, match=why):
        ev.check_probes([{"name": "x", "probes": [probe]}])


def test_the_judge_role_must_be_declared_never_defaulted():
    with pytest.raises(ev.JudgeRefused, match="declares no model for the 'judge' role"):
        ev.judge_config(Canned([], models={"gate": "model-under-test", "compile": "c"}))
    with pytest.raises(ev.JudgeRefused, match="declares no model"):
        ev.judge_config(object())                                     # a provider that declares nothing
    cfg = ev.judge_config(Canned([]))
    assert cfg == {"role": "judge", "model": "claude-haiku-5-5", "max_tokens": 4096,
                   "effort": "the provider's default (not exposed)"}


def test_a_token_limit_with_no_headroom_refuses():
    with pytest.raises(ev.JudgeRefused, match="max_tokens 200 < 1024"):
        ev.judge_config(Canned([], max_tokens=200))


def test_the_grading_call_goes_to_the_judge_role_not_gate():
    p = Canned(['{"correct": true, "why": "ok"}'])
    assert ev.grade(p, ev.JUDGE_ROLE, "prompt") == (True, 1)
    assert p.calls == ["judge"]


@pytest.mark.parametrize("replies, expected", [
    (["not json at all", '{"correct": false, "why": "no"}'], (False, 2)),       # retried once, then a verdict
    (["not json", "still not json"], (None, 2)),                                 # a judge failure, never False
    (['{"why": "no verdict field"}', '{"correct": "yes"}'], (None, 2)),           # a non-boolean verdict is not one
    (['[{"correct": true}]', '{"correct": true}'], (True, 2)),                   # a list is not the verdict object
])
def test_a_reply_without_a_boolean_verdict_is_retried_once_then_a_judge_failure(replies, expected):
    assert ev.grade(Canned(replies), ev.JUDGE_ROLE, "prompt") == expected


def test_the_cli_provider_declares_the_judge_and_the_reference_judge_beside_the_model_under_test():
    m = cli.ClaudeCLIComplete._models
    assert m["judge"] == "claude-haiku-5-5" and m["judge_reference"] == "claude-sonnet-5"
    assert m["gate"] == "claude-sonnet-5"                            # the model under test is unchanged


ASPECT_CORPUS = json.loads((ROOT / "tests" / "eval_judge_aspect_corpus.json").read_text(encoding="utf-8"))["questions"]


def test_the_aspect_backstop_matches_every_adjudicated_event_time_question_in_the_0043_held_outs():
    """Research's measurement (round-8 judge review): the first, ANCHORED guard missed 6 of these 54, three of them
    compound questions of exactly the shape the Haiku judge failed on."""
    assert len(ASPECT_CORPUS) == 54
    missed = [q for q in ASPECT_CORPUS if not ev.ASPECT.search(q)]
    assert missed == [], missed


@pytest.mark.parametrize("q", ["What do I value when it comes to your responses, and where am I located?",
                               "When did I first ask for concise replies?", "When did you learn I prefer concise answers?"])
def test_the_known_over_matches_are_in_the_safe_direction_they_refuse(q):
    with pytest.raises(ev.JudgeRefused, match="asks about an aspect"):
        ev.check_probes([{"name": "x", "probes": [{"q": q, "asks": "content"}]}])


def test_the_eval_declares_its_user_events_first_party_and_names_its_third_party_sources():
    """The eval predated specs/0011 §4d (an undeclared event is floored to third-party-derived) and specs/0006's required
    source_id; it failed at HEAD from v0.25.0 until 2026-10-08. Driven over the SHIPPED scenarios with a recording memory."""
    from veracium import EvidenceContext
    from veracium.schema import EvidenceAuthor

    class Recording:
        def __init__(self): self.calls = []
        def remember(self, user_id, text, **kw): self.calls.append(kw)

    scenarios = json.loads(ev.SCENARIOS.read_text())
    seen = {"user": 0, "third_party": 0}
    for sc in scenarios:
        m = Recording(); ev.ingest_scenario(m, sc)
        assert len(m.calls) == len(sc["events"])
        for kw in m.calls:
            if kw["author"] == EvidenceAuthor.USER:
                assert kw.get("context") == EvidenceContext.direct() and "source_id" not in kw; seen["user"] += 1
            else:
                assert kw.get("source_id") == f"eval:{sc['name']}" and "context" not in kw; seen["third_party"] += 1
    assert seen["user"] > 0 and seen["third_party"] > 0          # both kinds exercised by the shipped scenarios
