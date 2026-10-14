#!/usr/bin/env python3
# Mutation-Matrix: tests/test_mutation_kinds.py::test_each_rule_of_the_classifier_is_load_bearing
"""What a mutation campaign may call a KILL — one definition, shared by every campaign that reads JUnit failures
(0041's notice-binding hotfix campaign, 0043's mechanism campaign).

Round-4 IO-II-7: a runner that calls every JUnit `<failure>` an assertion kill overstates its evidence, because a test
body that raises an unrelated exception is also a JUnit failure. The 0041 campaign had three such detections (escaping
domain refusals); the class sweep found 0043's R5-04a killed by a single escaping KeyError. So each failing cell is
classified from its failure message:

  assertion                  an AssertionError or a bare `assert` (a permission helper's assertion included)
  expected-refusal-missing   `pytest.raises` saw no exception: "Failed: DID NOT RAISE"
  declared-fail-closed       ONLY for a row declared fail-closed, and only on the cells it names: the declared
                             refusal type (an exception whose name ends with the declared suffix) — the honest
                             controls refusing IS that row's observation (0043 research stage-1, 2026-10-10)
  other: <type>              anything else: a TypeError, an undeclared ValueError, `pytest.fail`, a setup failure

A row is KILLED iff >=1 failing cell has a qualifying kind, NO failing cell is `other`, and none ERRORS; a row with a
failure the classifier cannot vouch for is UNCLASSIFIED, never KILLED. The kinds are recorded per cell, so a reader can
recount every kill from the table without re-running it.
"""
from __future__ import annotations

QUALIFYING = ("assertion", "expected-refusal-missing")
DECLARED = "declared-fail-closed"


def failure_kind(message: str) -> str:
    """A failing cell's kind, from its JUnit failure message (the line pytest writes as the `message` attribute)."""
    m = (message or "").lstrip()
    if m.startswith("AssertionError") or m.startswith("assert "):
        return "assertion"
    if m.startswith("Failed: DID NOT RAISE"):
        return "expected-refusal-missing"
    return "other: " + ((m.split(":")[0].split() or ["<no message>"])[0])[:60]


def admitted_kind(node: str, kind: str, admits) -> str:
    """`admits` is None, or (suffix, cells): a fail-closed row's declared observation. A cell in `cells` whose kind is
    `other: <name>` with <name> ending in `.<suffix>` or equal to `<suffix>` reads DECLARED; everything else as is."""
    if not admits or not kind.startswith("other: "):
        return kind
    suffix, cells = admits
    name = kind[len("other: "):]
    if node in cells and (name == suffix or name.endswith("." + suffix)):
        return DECLARED
    return kind


def classify(kinds: dict, failed: list, errored: list, admits=None) -> dict:
    """kinds: {failing node: raw kind}; failed / errored: the node lists. Returns the row fields: cells_failed,
    cells_errored, cell_kinds (raw, as observed), outcome (KILLED / UNCLASSIFIED / SURVIVED / ERROR) and kill_kind (the
    qualifying kinds joined by '+', or None)."""
    eff = {n: admitted_kind(n, k, admits) for n, k in kinds.items()}
    ok = set(QUALIFYING) | ({DECLARED} if admits else set())
    qual = sorted({k for k in eff.values() if k in ok})
    other = any(k not in ok for k in eff.values())
    if errored:
        outcome = "ERROR"
    elif not failed:
        outcome = "SURVIVED"
    elif other or not qual or set(kinds) != set(failed):
        outcome = "UNCLASSIFIED"
    else:
        outcome = "KILLED"
    return {"cells_failed": sorted(failed), "cells_errored": sorted(errored), "cell_kinds": dict(sorted(kinds.items())),
            "outcome": outcome, "kill_kind": "+".join(qual) if outcome == "KILLED" else None}
