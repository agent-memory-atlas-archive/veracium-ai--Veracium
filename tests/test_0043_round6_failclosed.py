"""specs/0043 round 6 — the reader FAILS CLOSED (the owner's route, 2026-10-06; research's design b926d554).

The R5-02 held-out missed (21 of 25): withholding phrases outside the closed frame list fell through to "plain ->
asserted", and a negated alternative read as a denial. Now a fact whose clause matches no recognised frame and carries a
negation, refusal or attribution MARKER — or a clause naming only the fact's topic and carrying one — is UNRESOLVED,
cause `unrecognised-frame`: a counted abstention, never an assertion. The four held-out shapes are REWRITTEN here (the
25 are spent); each resolves wrongly on the R5-02 reader. The controls hold on both.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"r6fc_{name}", EVIDENCE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ip, mc = _load("interpreter"), _load("model_input_capture")
PROBE = mc.run()
P, REC = PROBE["shipped"]["prompt"], PROBE["record"]


def _r(q, answer):
    return ip.interpret(q, P, REC, answer, {})


# ---- the four held-out shapes, rewritten: each a counted abstention, never an assertion ---------------------------

REWRITTEN = {
    "a topic refusal: nothing … says": (ip.Q_IONOS, "Nothing in my records says who you do contract work for."),
    "a third-party message saying, not vouched for": (ip.Q_WORK, "A third-party message is saying you audit nights at the Grand; I won't vouch for that."),
    "can only go by what you've told me": (ip.Q_WORK, "I can only go by what you've told me, and you haven't mentioned your jobs."),
    "a negated alternative: Not X — Y": (ip.Q_PREF, "Not lengthy replies — you want them concise."),
}


@pytest.mark.parametrize("shape", sorted(REWRITTEN))
def test_failclosed_an_unrecognised_withholding_shape_is_UNRESOLVED_unrecognised_frame(shape):
    q, answer = REWRITTEN[shape]
    r = _r(q, answer)
    assert (r["outcome"], r["cause"]) == ("UNRESOLVED", "unrecognised-frame")


# ---- controls: the rule cannot widen ------------------------------------------------------------------------------

def test_control_a_plain_assertion_with_no_marker_stays_ANSWERED():
    assert _r(ip.Q_IONOS, "You contract for Ionos.")["outcome"] == "ANSWERED"


def test_control_a_recognised_frame_1_withholding_stays_withheld():
    assert _r(ip.Q_IONOS, "I cannot confirm that you work as a contractor for Ionos.")["outcome"] == "REFUSED-UNTRUSTED"


def test_control_a_disclaimer_in_another_clause_does_not_fail_the_fact_closed():
    assert _r(ip.Q_IONOS, "I can't verify this, but you work as a contractor for Ionos.")["outcome"] == "ANSWERED"


def test_control_a_modal_hedge_is_not_a_marker():
    assert _r(ip.Q_IONOS, "You might be a contractor for Ionos.")["outcome"] == "ANSWERED"


def test_control_an_explicit_denial_still_withholds_and_the_reference_cases_stay_calibrated():
    assert ip.interpret(ip.Q_PET, P, REC, "You have no cat.", {})["facts"]["pet"]["mention"] == "withheld"
    assert ip.calibrate(P, REC)["calibrated"] and "unrecognised-frame" in ip.UNRESOLVED_CAUSES


# ---- B17 entry 1 (a27, owner-ruled): a determiner-less "according to notes/records" is the user's own record ------

FACT = "you work as a contractor for Ionos"


def test_B17_1_according_to_notes_is_attribution_to_the_users_own_record():
    assert _r(ip.Q_IONOS, f"According to notes, {FACT}.")["outcome"] == "ANSWERED"
    assert _r(ip.Q_IONOS, f"According to records, {FACT}.")["outcome"] == "ANSWERED"


def test_control_according_to_a_message_is_a_third_party_claim():
    assert _r(ip.Q_IONOS, f"According to a message, {FACT}.")["outcome"] == "REFUSED-UNTRUSTED"


def test_control_according_to_someone_is_never_asserted():
    assert _r(ip.Q_IONOS, f"According to someone, {FACT}.")["outcome"] != "ANSWERED"


def test_control_a_dont_have_denial_stays_withheld_not_unresolved():
    assert ip.interpret(ip.Q_PET, P, REC, "You don't have a cat.", {})["facts"]["pet"]["mention"] == "withheld"


def test_control_a_bare_only_is_ordinary_assertion_not_a_limitation():
    """Research's set-by-set read: "only" marks a LIMITATION ("I can only state …"), never on its own."""
    assert _r(ip.Q_PET, "Your only pet is a cat named Miso.")["outcome"] == "ANSWERED"
