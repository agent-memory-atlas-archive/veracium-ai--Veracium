"""specs/0042 INV-7 — THE STANDING EXCLUSION LIST: test units whose own observer trace is known to differ between
two runs of ONE arm, excluded from every cross-arm comparison BY NAME, each with its cause.

Why a standing list (research, round 7): a control pair is a sample of two — a test that diverges with probability
p is excluded only when the pair disagrees (~2p) while the four-arm comparison trips at ~4p, so about half of rare
flakes trip the comparison without ever having been excluded; and an exclusion set re-derived every run means
"IDENTICAL over N tests, K excluded" names a different set each run, and re-running until the control catches a
flake is p-hacking the evidence with the instrument's own noise. So: a test that is non-reproducible goes HERE, by
name, with its cause, deliberately; the transcript reports the standing exclusions and, separately, any test the
control pairs found NEWLY non-reproducible this run — and a new one FAILS the harness's exit (`final_status`),
because it is a finding, not housekeeping. The real fix for each entry belongs to its suite's owner.
"""
# Mutation-Matrix: tests/test_0042_inv7.py::test_the_harness_comparison_fails_on_each_mutant

STANDING = {
    "tests/eval/edge_events/test_0029_acceptance_corpus.py::test_acceptance_corpus_passes_100_percent":
        "the acceptance corpus's supersession step is sensitive to the wall clock: a supersession batch (two upserts "
        "under one transaction) lands at a different scenario step between two runs of one arm — first sampled "
        "2026-09-20 by the healthy arm's slower timing, then by the failing arm's control pair; the test agrees with "
        "itself in isolation and with the harness's suite prefix. The corpus runner accepts an injected clock and the "
        "acceptance test injects none (specs/0029's owner; the Dev queue carries the follow-up). Excluded until it does.",
}
