#!/usr/bin/env python3
"""0041 round 5 — the verdict's executed claims, reproduced at the pin BEFORE any fix.

Pin `a3ef39af276b63823d13d721ff47149f356c8ded` (0041 v10). Run from a tree whose
`src/` and `specs/` are byte-identical to that pin; the reproduction asserts that
itself (R0) rather than trusting the checkout, because these findings are claims
about the SHIPPED model and a drifted tree would answer a different question.

Each claim is stated as a SENTENCE first, then executed. A claim that fails to
reproduce is a finding about the verdict and is printed as such, not silently
dropped.
"""
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
PIN = "a3ef39af276b63823d13d721ff47149f356c8ded"
FAILURES = []


def claim(n, sentence):
    print(f"\n=== R{n} — {sentence}")


def result(ok, detail):
    print(("    REPRODUCED: " if ok else "    DID NOT REPRODUCE: ") + detail)
    if not ok:
        FAILURES.append(detail)


# ---------------------------------------------------------------- R0
claim(0, "the tree's product and spec surface is byte-identical to the pin, so "
         "what follows is a claim about the reviewed bytes")
if not (ROOT / ".git").exists():
    # A review package is a `git archive` and has no repository. Say so OUT LOUD:
    # a check that quietly does not run is indistinguishable from one that passed,
    # and this is the check that says the rest are about the reviewed bytes.
    print("    N/A — no .git here (a packaged tree). The pin comparison cannot run, "
          "so the claims below are about THIS tree's bytes and the reader must "
          "establish for themselves that they are the pin's.")
else:
    out = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only",
                          f"{PIN}..HEAD", "--", "src/", "specs/"],
                         capture_output=True, text=True)
    drifted = [l for l in out.stdout.splitlines() if l.strip()]
    result(out.returncode == 0 and not drifted,
           f"git diff {PIN[:8]}..HEAD over src/ and specs/ lists {len(drifted)} files"
           + (f": {drifted}" if drifted else ""))

sys.path.insert(0, str(ROOT / "src"))
from veracium.schema import Episode, Provenance, Disclosure, DISPOSITIONED_REASONS  # noqa: E402


def an_active_episode() -> Episode:
    return Episode(
        id="ep-1", user_id="u", date="2026-09-16", summary="a summary",
        provenance=Provenance(author_of_evidence="user", evidence_ref="ref-1",
                              disclosure=Disclosure.MENTIONABLE),
    )


# ---------------------------------------------------------------- R1
claim(1, "an ordinary active episode carries retired_reason=None and active=True")
ep = an_active_episode()
result(ep.retired_reason is None and ep.active is True,
       f"retired_reason={ep.retired_reason!r}, active={ep.active}")

# ---------------------------------------------------------------- R2
claim(2, "None is not in DISPOSITIONED_REASONS, so row 49's `else` branch is the "
         "one an active episode takes")
result(None not in DISPOSITIONED_REASONS,
       f"None in DISPOSITIONED_REASONS -> {None in DISPOSITIONED_REASONS}; "
       f"the registry holds {len(DISPOSITIONED_REASONS)} keys: "
       f"{sorted(DISPOSITIONED_REASONS)}")

# ---------------------------------------------------------------- R3
claim(3, "applying row 49 as written to that episode flips a DERIVED disposition: "
         "active True -> False, which is what §4h forbids")
before = (ep.retired_reason, ep.active)
redacted = ep.model_copy(update={"retired_reason": "redacted"})   # row 49's `else`
after = (redacted.retired_reason, redacted.active)
result(before == (None, True) and after == ("redacted", False),
       f"{before} -> {after}")

# ---------------------------------------------------------------- R4
claim(4, "the flip reaches `assertable`, the shared predicate text consumers call, "
         "so the damage is not confined to the retirement axis")
result(ep.assertable is True and redacted.assertable is False,
       f"assertable {ep.assertable} -> {redacted.assertable}")

# ---------------------------------------------------------------- R5
claim(5, "a registered reason is unaffected — the defect is specific to ABSENCE, "
         "which is the distinction the verdict asks for")
name = sorted(DISPOSITIONED_REASONS)[0]
retired = ep.model_copy(update={"retired_reason": name})
kept = retired.model_copy(update={"retired_reason": name})        # row 49's PRESERVE
result(retired.active is False and kept.retired_reason == name and kept.active is False,
       f"a {name!r} episode stays {kept.retired_reason!r}, active={kept.active}")

# ---------------------------------------------------------------- R6
claim(6, "the packaged absence-preservation test expects None, so the spec and the "
         "evidence in the same package disagree")
# A DIRECTORY WALK, not `git grep`: git grep sees only TRACKED files and returns
# nothing at all inside a review package, where this script has to run. It also
# answers a slightly different question — what the tree carries, rather than what
# the index carries — and the tree is what the reviewer runs.
found = sorted(
    str(f.relative_to(ROOT))
    for f in (ROOT / "tests").rglob("test_*.py")
    if "retired_reason" in (text := f.read_text()) and "retired_reason is None" in text)
result(bool(found), f"test files asserting retired_reason and `is None`: {found}")

print("\n" + "=" * 72)
if FAILURES:
    print(f"{len(FAILURES)} claim(s) DID NOT reproduce — each is a finding about the "
          f"verdict and is owed an answer before any fix:")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print("all claims reproduced at the pin; no fix has been applied")


# ====================================================================
# FINDING 3 — the three bodies AS THEY STOOD AT THE PIN.
#
# FROZEN QUOTATIONS, not a re-read of the tree. The bodies have since been
# rewritten, so running the reviewer's mutants against today's files would prove
# the FIX and not the FINDING, and a reproduction that silently becomes a
# different claim is worse than none.
#
# Frozen rather than fetched with `git show` for a second reason: that would make
# this one more piece of evidence a packaged tree cannot run, which is exactly
# the cost `test_the_count_of_closure_evidence_unrunnable_in_a_package_is_pinned`
# exists to count. The kill evidence for the REWRITTEN bodies lives in
# `xfail_mutant_campaign.py`, which runs ten mutants including three positive
# controls.
# ====================================================================
import ast

PIN_FILE_SHA16 = "97ad5419f71c40a0"   # sha256 of tests/test_0041_transition_table.py at the pin

PIN_BODIES = {
    "test_C_the_migration_report_enumerates_unattested_marker_rows":
        "def f(tmp_path):\n    from veracium.store import migration\n    assert hasattr(migration, \"unattested_marker_report\")",
    "test_F_a_repeated_call_returns_the_original_or_a_reconstructed_receipt":
        "def f():\n    assert hasattr(Memory, \"redact\")",
    "test_C_after_attestation_the_same_write_is_refused":
        "def f(tmp_path):\n    st = _mem(tmp_path).store\n    st.add_edge(Edge(id=\"e-m\", user_id=U, subject=\"user\", relation=\"works_as\", object=\"secret\", provenance=_prov()))\n    Memory.redact                                                       # the API, then the attested refusal\n    with pytest.raises(Exception):\n        st.add_edge(Edge(id=\"e-m\", user_id=U, subject=\"user\", relation=\"works_as\", object=\"Porto\", provenance=_prov()))",
}


print("\n" + "=" * 72)
print("FINDING 3 — the pin's three bodies, quoted and classified")

EXISTENCE = {"hasattr", "getattr", "callable"}


def verdict_on(source):
    """Can this body be satisfied without the behaviour its name promises?"""
    fn = ast.parse(source).body[0]
    asserts = [n for n in ast.walk(fn) if isinstance(n, ast.Assert)]
    bare = [n.value.attr for n in fn.body
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Attribute)]
    existence = [a for a in asserts
                 if isinstance(a.test, ast.Call)
                 and getattr(a.test.func, "id", "") in EXISTENCE]
    if asserts and len(existence) == len(asserts):
        return "EXISTENCE-ONLY — a stub satisfies every assertion it makes"
    if bare and not asserts:
        return (f"BARE REFERENCE to {bare} — a no-op the moment the attribute "
                f"exists, and the refusal asserted afterwards comes from elsewhere")
    return None


for _name, _src in PIN_BODIES.items():
    claim(_name[5:40], "the body at the pin cannot establish what its name promises")
    _v = verdict_on(_src)
    result(_v is not None,
           f"{_name}: {_v or 'the body has teeth — the verdict does NOT reproduce'}")

claim("fix", "and no body in the tree today carries those shapes")
_live = (ROOT / "tests" / "test_0041_transition_table.py").read_text()
_left = [n for n, s in PIN_BODIES.items()
         if s.split("\n", 1)[1].strip() in _live]
result(not _left, f"pin-era bodies still present in the tree: {_left or 'none'}")

print("\n" + "=" * 72)
if FAILURES:
    print(f"{len(FAILURES)} claim(s) DID NOT reproduce:")
    for _f in FAILURES:
        print("  - " + _f)
    sys.exit(1)
print("every claim in the round-5 verdict reproduced at the pin, and finding 3's "
      "three bodies are gone from the tree")
