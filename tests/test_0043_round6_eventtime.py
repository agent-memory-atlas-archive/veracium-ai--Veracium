"""specs/0043 round 6 — the EVENT-TIME reader fails closed (held-out-2's miss; the owner's route, 2026-10-07; research's
design, research 9191a4d0).

Held-out-2 missed on fail-open 3 > 1, and all three were in `event_time_reading`: a date with no record frame was read as
an EVENT time, and an event time won before a decline was checked, so "I don't have the exact date … only that you first
mentioned your cat on <date>" asserted. The fail-closed design (5bf9080) reached `mention_reading` and not its sibling.
Now a date asserts only under a POSITIVE event frame; a record frame gains "mentioned", "received" and a "claim" that
matches before "("; a date that is neither reads `unrecognised` -> UNRESOLVED, cause `unrecognised-frame`.

The held-out-2 answers are spent; the shapes below are REWRITTEN. The superseded reader is kept as the negative control
it must differ from. The class guard is the property test at the end: every site that PRODUCES "asserted" in the reader
is enumerated by `ast`, the enumeration must find exactly the known sites (so it cannot pass vacuously), and no reader
reaches "asserted" as its fall-through.
"""
import ast
import importlib.util
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"
SOURCE = (EVIDENCE / "interpreter.py").read_text(encoding="utf-8")


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r6et_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ip, mc = _load("interpreter"), _load("model_input_capture")
PROBE = mc.run()
P, REC = PROBE["shipped"]["prompt"], PROBE["record"]


def superseded_event_time_reading(answer):
    """The reader held-out-2 measured (9fa2f62), verbatim in logic: the negative control."""
    old_record = re.compile(r"\b(?:noted|recorded|logged|dated|added|saved|stored|captured|entered|on record|in my memory|"
                            r"claim|claims|claimed|message|note|notes) \b|\b(?:noted|recorded|logged|dated)\b")
    a = ip._norm(answer)
    event_dates, record_dates = [], []
    for sentence in re.split(r"[.!?]\s*", a):
        for clause in ip.CONTRAST.split(sentence):
            for m in ip.DATE_RE.finditer(clause):
                (record_dates if old_record.search(clause[:m.start()]) else event_dates).append(m.group(0))
    if event_dates:
        return "asserted"
    if ip.DECLINE_TIME.search(a):
        return "withheld"
    if record_dates:
        return "withheld"
    return "not_mentioned"


# ---- the three held-out-2 shapes, rewritten: each WITHHELD now, each ASSERTED on the superseded reader --------------

CITY, PET, NIGHT, IONOS = (ip.FACTS[k] for k in ("city", "pet", "work_night", "work_ionos"))

REWRITTEN = {
    "a decline, then a mentioned-on date": ("I can't pin down when you adopted Miso; you first mentioned her to me on 2026-09-20.", PET),
    "no record of when, then a mentioned-having date": ("There's no record of when you moved — just that you mentioned living in Porto on 3 October 2026.", CITY),
    "a claim in parentheses with a received date": ("I have no confirmed record of that; there was a claim (that you contract for Ionos, received 2026-09-19), never confirmed.", IONOS),
}


@pytest.mark.parametrize("label", sorted(REWRITTEN))
def test_a_held_out_2_shape_withholds_and_the_superseded_reader_asserted_it(label):
    answer, fact = REWRITTEN[label]
    assert ip.event_time_reading(answer, fact)[0] == "withheld", label
    assert superseded_event_time_reading(answer) == "asserted", f"control: the superseded reader must fail open on {label!r}"


# ---- fail closed: a date no frame reads is UNRESOLVED, cause unrecognised-frame, through the real interpret path ------

UNFRAMED = ["Miso: 2026-09-18.", "Porto, 2026-09-18, as far as I can tell.", "That would be September 18, 2026."]


def _event_q(*facts):
    facts = facts or (CITY,)
    ids = [f"{f['id']}@event-time" for f in facts]
    return {"text": "when?", "facts": list(facts), "class_fact": ids[0], "class_set": ids, "event_time": True}


@pytest.mark.parametrize("answer", UNFRAMED)
def test_an_unframed_date_is_unresolved_never_asserted(answer):
    assert ip.event_time_reading(answer, CITY)[0] == "unrecognised"
    assert superseded_event_time_reading(answer) == "asserted", "control: the superseded reader asserted it"
    r = ip.interpret(_event_q(), P, REC, answer, {})
    assert r["outcome"] == "UNRESOLVED" and r["cause"] == "unrecognised-frame", r
    assert r["facts"]["city@event-time"]["mention"] == "unrecognised"


# ---- research's stage-1 cells: the RECORD's event, the CONVERSATION's, and an event that names no fact -------------

NOT_THE_USERS_EVENT = [
    ("I don't know when you moved to Porto; that note arrived on 2026-09-18.", CITY),
    ("I can't say when you got Miso — I got that information on 2026-09-18.", PET),
    ("No start date is recorded; the Ionos claim became part of your profile on 2026-09-18.", IONOS),
    ("I don't know when you took the job; the message joined your file on 2026-09-18.", NIGHT),
    ("As of 2026-09-18, my records list you in Porto, but I don't know when you moved.", CITY),
    ("I don't know when you got Miso; you got in touch about her on 2026-09-18.", PET),
    ("I can't say when you moved; you started chatting with me on 2026-09-18.", CITY),
    ("I don't know when you started at the Grand; you started telling me about it on 2026-09-18.", NIGHT),
    ("No date for the move — you joined this service on 2026-09-18.", CITY),
    # stage-1 r2: an unlisted conversation verb — held by the CLAIM-SPECIFIC test, not by a word list
    ("You began sharing these details on 2026-09-18.", CITY),
    ("You began sharing these details on 2026-09-18.", PET),
    ("You started on 2026-09-18.", NIGHT),
    ("It started on 2026-09-18.", NIGHT),
    ("That began on 2026-09-18.", CITY),
    # dev's r3 rung: the fact IS named, but the event is an -ing activity about it (grammatical, not a verb list)
    ("You began sharing details about Porto on 2026-09-18.", CITY),
    ("You started discussing Miso on 2026-09-18.", PET),
    ("You've been bringing up the Grand since 2026-09-18.", NIGHT),
    ("You started describing your Ionos work on 2026-09-18.", IONOS),
    # research's r3 rung: an aspectual word's activity as a TO-INFINITIVE (the other half of the closed pair)
    ("You began to describe Porto on 2026-09-18.", CITY),
    ("You started to explain the Grand job on 2026-09-18.", NIGHT),
    ("You got to know Miso on 2026-09-18.", PET),
    # dev's carrier read of v6.2: a frameless "… ago" asserted with no subject and no fact
    ("I don't know when you moved; I heard about it a week ago.", CITY),
    ("No idea when you got Miso — this came up two days ago.", PET),
    ("Two years ago.", CITY),
    ("You got Miso and you moved to Porto in 2024.", PET),                           # the date is the move's predicate
]


@pytest.mark.parametrize("answer,fact", NOT_THE_USERS_EVENT)
def test_an_event_that_is_not_the_user_s_requested_one_never_asserts(answer, fact):
    assert ip.event_time_reading(answer, fact)[0] in ("withheld", "unrecognised"), answer


def test_the_event_subject_is_the_nearest_subject_before_the_word():
    assert ip._event_subject("you ")[0] is True and ip._event_subject("you've lived in porto ")[0] is True
    assert ip._event_subject("that note ")[0] is False and ip._event_subject("i don't know when you moved; i ")[0] is False
    assert ip._event_subject("it ")[0] is None and ip._event_subject("")[0] is None


def test_the_reading_is_claim_specific():
    """One answer, two requested facts: each fact reads its OWN event time."""
    answer = "You got Miso on 2026-09-18."
    assert ip.event_time_reading(answer, PET)[0] == "asserted" and ip.event_time_reading(answer, CITY)[0] == "unrecognised"
    r = ip.interpret(_event_q(PET, CITY), P, REC, answer, {})
    assert r["facts"]["pet@event-time"]["mention"] == "asserted" and r["facts"]["city@event-time"]["mention"] == "unrecognised"
    both = "You've had your cat Miso and lived in Porto since September 18, 2026."
    assert ip.event_time_reading(both, PET)[0] == ip.event_time_reading(both, CITY)[0] == "asserted"


# ---- the controls: what must NOT move -------------------------------------------------------------------------------

CONTROLS = [
    ("You've lived in Porto since September 18, 2026.", CITY, "asserted"),
    ("You moved to Porto on 2026-09-18.", CITY, "asserted"),
    ("You moved on 2026-09-18.", CITY, "asserted"),                                  # the relation's TOPIC word governs
    ("You started working nights at the Grand on 2026-09-18.", NIGHT, "asserted"),
    ("You started at the Grand as of 2026-09-18.", NIGHT, "asserted"),
    ("You've been contracting for Ionos for two years.", IONOS, "asserted"),
    ("You got Miso two years ago.", PET, "asserted"),
    ("You got Miso on 2026-09-18.", PET, "asserted"),
    ("You moved to Porto in 2024.", CITY, "asserted"),
    ("Since 2026-09-18.", CITY, "unrecognised"),                                     # no subject: no frame, fail closed
    ("I can't confirm this, but you moved to Porto on 2026-09-18.", CITY, "asserted"),  # A3-bis: a disclaimer does not save it
    ("You mentioned it on 2026-09-18, and you moved to Porto in 2024 as of that note.", CITY, "asserted"),  # an event date elsewhere wins
    ("As you mentioned, you moved to Porto in 2024.", CITY, "asserted"),             # the nearest frame governs
    ("You moved to Porto; I have it noted from 2026-09-18.", CITY, "withheld"),
    ("You live in Porto, which you first mentioned on 2026-09-18.", CITY, "withheld"),
    ("You mentioned your move two days ago.", CITY, "withheld"),                     # the mention's date, not the move's
    ("I don't know when you moved to Porto.", CITY, "withheld"),
    ("I only have it noted on 2026-09-18, not when you moved.", CITY, "withheld"),
    ("You live in Porto.", CITY, "not_mentioned"),
    ("You started working at the Grand on 2026-09-18.", NIGHT, "asserted"),          # an -ing that IS the fact's topic
    ("You've been living in Porto since 2026-09-18.", CITY, "asserted"),
    ("You got Miso one morning in 2024.", PET, "asserted"),                          # a non-verb -ing word
    ("You started to work at the Grand on 2026-09-18.", NIGHT, "asserted"),          # a topic infinitive
    ("You began to live in Porto in 2024.", CITY, "asserted"),
    ("You adopted Miso in 2024.", PET, "asserted"),
    ("You began contracting for Ionos in 2024.", IONOS, "asserted"),
    ("You got Miso and you moved to Porto in 2024.", CITY, "asserted"),
]


@pytest.mark.parametrize("answer,fact,expected", CONTROLS)
def test_the_controls_hold(answer, fact, expected):
    assert ip.event_time_reading(answer, fact)[0] == expected, answer


def test_the_record_frame_matches_a_claim_before_a_parenthesis():
    assert ip.RECORD_FRAME.search("a third-party claim (") and ip.RECORD_FRAME.search("you first mentioned it on ")


# ---- the class guard: every site that PRODUCES "asserted" is known, and none is a fall-through ----------------------

def _produces_asserted(node):
    """The expression evaluates to "asserted", or to a tuple whose first element does, on some branch."""
    if isinstance(node, ast.Constant):
        return node.value == "asserted"
    if isinstance(node, ast.Tuple) and node.elts:
        return _produces_asserted(node.elts[0])
    if isinstance(node, ast.IfExp):
        return _produces_asserted(node.body) or _produces_asserted(node.orelse)
    return False


def _sites():
    found = {}
    for fn in ast.walk(ast.parse(SOURCE)):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for n in ast.walk(fn):
            value = n.value if isinstance(n, (ast.Return, ast.Assign)) else None
            if value is not None and _produces_asserted(value):
                found.setdefault(fn.name, []).append(n.lineno)
    return found


# every reader that can produce "asserted", with the POSITIVE recognition each site sits behind
KNOWN = {
    "_frame_of": (3, "an attribution frame (3), a weak frame not disqualified (4), a double negation (5)"),
    "mention_reading": (2, "the fact found in a clause by _clause_mentions, with no marker in its segment (plain, 5)"),
    "event_time_reading": (1, "a date whose NEAREST frame word is an EVENT_FRAME word with the USER as subject GOVERNING the requested fact, not an activity about it"),
}


def test_the_enumeration_finds_exactly_the_known_asserted_sites():
    found = {k: len(v) for k, v in _sites().items()}
    assert found == {k: n for k, (n, _) in KNOWN.items()}, (
        f"a reader that PRODUCES 'asserted' was added, removed or changed: {_sites()} — register it in KNOWN with the "
        f"positive recognition it sits behind, and add its fail-closed cells")


def test_no_reader_falls_through_to_asserted():
    for fn in ast.walk(ast.parse(SOURCE)):
        if isinstance(fn, ast.FunctionDef) and fn.name in KNOWN:
            last = fn.body[-1]
            assert not (isinstance(last, ast.Return) and _produces_asserted(last.value)), f"{fn.name} defaults to asserted"


def test_the_event_time_reader_reaches_asserted_only_through_a_positive_event_frame():
    fn = next(n for n in ast.walk(ast.parse(SOURCE)) if isinstance(n, ast.FunctionDef) and n.name == "event_time_reading")
    appends = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "append" and isinstance(n.func.value, ast.Name) and n.func.value.id == "event_dates"]
    assert len(appends) == 1
    guards = [n for n in ast.walk(fn) if isinstance(n, ast.If) and any(a in ast.walk(n) for a in appends)
              and not any(a in ast.walk(s) for s in n.orelse for a in appends)]
    assert any("ev is not None" in ast.unparse(g.test) for g in guards), "event_dates is filled outside a positive event frame"
    assert "EVENT_FRAME" in ast.unparse(fn), "the event frame is no longer what sets ev"


def test_the_guard_refuses_a_default_asserting_reader():
    """The mutant: the superseded reader's shape, installed in place of the fixed one, must trip the guards."""
    fixed = next(n for n in ast.walk(ast.parse(SOURCE)) if isinstance(n, ast.FunctionDef) and n.name == "event_time_reading")
    mutant_src = ("def event_time_reading(answer, fact):\n    for m in DATE_RE.finditer(answer):\n"
                  "        event_dates.append(m.group(0))\n    return 'asserted', ''\n")
    mutated = SOURCE.replace(ast.get_source_segment(SOURCE, fixed), mutant_src)
    fn = next(n for n in ast.walk(ast.parse(mutated)) if isinstance(n, ast.FunctionDef) and n.name == "event_time_reading")
    assert isinstance(fn.body[-1], ast.Return) and _produces_asserted(fn.body[-1].value)
    assert not any(isinstance(n, ast.If) and "ev is not None" in ast.unparse(n.test) for n in ast.walk(fn))
