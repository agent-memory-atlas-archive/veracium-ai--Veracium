"""specs/0042 Part A-0-bis — THE SEMANTIC REVIEW: one decision for every DISCOVERED candidate, AUTHORED
by dev on 2026-09-19 from specs/evidence/0042/decision_site_inventory_OUTPUT.json read site by site.

`E` maps a candidate (module, line) to (site_id, governing spec, invariant/section, decision label) for
every candidate that IS an enforcement point: a site that can return a decision other than the
caller's request (refuse, quarantine, withhold, abstain, downgrade) enforcing a spec's stated
guarantee at a product boundary. Everything else takes a NOT decision with a reason class — the
module DEFAULT, or a per-line OVERRIDE where the default is not the truth for that line:
  argument-check      the caller's input is malformed (type, shape, range, closed parameter vocabulary)
  internal-invariant  a validator of the product's own contracts (carriers, ledgers, registries, package)
  predicate-helper    a Boolean/None helper whose CONSUMER makes the decision
  control-flow        lookups returning None for absent rows, early returns, re-raise after logging,
                      filters by non-policy criteria, budget/shape plumbing
  cli-usage           usage/exit handling of the command line

THE KEYS ARE DERIVED, NOT MAINTAINED (2026-09-19): the enforcement keys of every instrumented id are
rebuilt from the source by specs/evidence/0042/derive_keys.py (every `fire()`-wrapped candidate binds its
statement to its id), and the OVERRIDE keys are re-keyed by (module, qualname, kind, ordinal) in ONE hop
from the plan-time literal (override_at_plan.py) — after a sequential re-key had drifted two keys onto
neighbouring statements while every test stayed green. reviewed_points.json and declaration.py are
GENERATED from this module and the inventory; a change of judgement is made HERE.

Review corrections recorded: `_src_revoked` and `_is_variant` each bind ONE id — their `return False`
exits are the non-declining branch of one decision (`declines=True`), not enforcement points of their
own (found by touching, tranche 3); research's structural sweep over the whole review then found no
further instance (seven functions with more than one id on non-raising exits, each a set of distinct
declining reasons — the frozen allow-list lives in tests/test_0042_reconciliation.py).
"""

E = {}
def e(module, line, site_id, spec, inv, label): E[(module, line)] = (site_id, spec, inv, label)

# ---- __init__.py (Memory: the public surface) ----
# ---- asof/ ----
# ---- authority / grounding / compile / gate / schema ----
# ---- graph.py ----
# ---- ingest.py ----
# ---- mcp_server.py / procedures.py / procedural_gate.py / proactive.py / registry.py ----
# ---- portability.py (the import/export boundary) ----
# ---- scope.py / scope_linkage.py / scope_read.py ----
# ---- store/ ----
# ---- telemetry / diagnostics (0015 consent) ----


# ---- NOT decisions: module defaults + per-line overrides ----
DEFAULT = {
    "__init__.py": "argument-check", "_json.py": "control-flow", "agreement.py": "internal-invariant",
    "asof/adapter.py": "predicate-helper", "asof/classify.py": "predicate-helper", "asof/recall.py": "predicate-helper",
    "asof/resolve.py": "argument-check", "authority.py": "predicate-helper", "budgets.py": "argument-check",
    "cli.py": "cli-usage", "compile.py": "control-flow", "config.py": "argument-check", "contribution.py": "internal-invariant",
    "diagnostics.py": "control-flow", "doctor.py": "control-flow", "dryrun.py": "control-flow", "gate.py": "predicate-helper",
    "graph.py": "control-flow", "grounding.py": "predicate-helper", "ingest.py": "argument-check", "introspect.py": "argument-check",
    "lifecycle.py": "argument-check", "llm/anthropic.py": "internal-invariant", "llm/metered.py": "predicate-helper",
    "mcp_server.py": "cli-usage", "portability.py": "control-flow", "proactive.py": "argument-check",
    "procedural_gate.py": "predicate-helper", "procedures.py": "argument-check", "registry.py": "argument-check",
    "redaction.py": "predicate-helper",      # 0041 tranche 1: carries_marker / marker_fields — consumed by the upsert and add_episode sites
    "schema.py": "argument-check", "scope.py": "argument-check", "scope_linkage.py": "internal-invariant",
    "scope_read.py": "control-flow", "semantic.py": "internal-invariant", "source_identity.py": "control-flow",
    "store/base.py": "internal-invariant", "store/current_state.py": "internal-invariant", "store/migration.py": "internal-invariant",
    "store/release_migration.py": "internal-invariant", "store/revocation.py": "internal-invariant",
    "store/revocation_sweep.py": "internal-invariant", "store/schema_version.py": "internal-invariant",
    "store/sqlite.py": "internal-invariant", "telemetry.py": "control-flow", "census.py": "internal-invariant",
}
OVERRIDE = {  # (module, line) -> reason class, where the module default is not the truth for that line
    ("__init__.py", 391): "control-flow", ("__init__.py", 472): "control-flow", ("__init__.py", 600): "control-flow",
    ("__init__.py", 917): "control-flow", ("__init__.py", 1503): "control-flow", ("__init__.py", 1644): "control-flow",
    ("__init__.py", 1666): "control-flow", ("__init__.py", 1715): "control-flow", ("__init__.py", 1722): "control-flow",
    ("__init__.py", 1733): "control-flow", ("__init__.py", 1740): "control-flow", ("__init__.py", 1769): "control-flow",
    ("__init__.py", 1795): "control-flow", ("__init__.py", 2079): "internal-invariant", ("__init__.py", 2144): "control-flow",
    ("__init__.py", 293): "internal-invariant", ("__init__.py", 300): "internal-invariant",
    ("__init__.py", 994): "internal-invariant", ("__init__.py", 998): "internal-invariant", ("__init__.py", 1002): "internal-invariant",
    ("__init__.py", 1009): "internal-invariant", ("__init__.py", 1011): "internal-invariant",
    ("agreement.py", 219): "predicate-helper", ("agreement.py", 267): "control-flow", ("agreement.py", 487): "control-flow",
    ("asof/adapter.py", 54): "internal-invariant", ("asof/resolve.py", 117): "internal-invariant", ("asof/resolve.py", 122): "internal-invariant",
    ("asof/resolve.py", 179): "control-flow", ("asof/resolve.py", 204): "predicate-helper",
    ("compile.py", 175): "predicate-helper", ("diagnostics.py", 216): "predicate-helper", ("diagnostics.py", 249): "predicate-helper",
    ("doctor.py", 386): "predicate-helper", ("dryrun.py", 68): "predicate-helper",
    ("graph.py", 56): "predicate-helper", ("graph.py", 71): "predicate-helper", ("graph.py", 230): "internal-invariant",
    ("graph.py", 888): "argument-check", ("grounding.py", 154): "control-flow",
    ("ingest.py", 180): "control-flow", ("ingest.py", 132): "argument-check",
    ("lifecycle.py", 184): "control-flow", ("lifecycle.py", 323): "control-flow",
    ("portability.py", 433): "control-flow",
    ("procedural_gate.py", 49): "argument-check", ("procedures.py", 104): "control-flow", ("procedures.py", 364): "control-flow",
    ("scope.py", 189): "predicate-helper", ("scope.py", 229): "internal-invariant", ("scope.py", 232): "internal-invariant",
    ("scope.py", 234): "internal-invariant", ("scope.py", 385): "predicate-helper", ("scope.py", 594): "control-flow", ("scope.py", 688): "control-flow",
    ("scope_linkage.py", 115): "control-flow", ("scope_linkage.py", 126): "control-flow", ("scope_linkage.py", 510): "predicate-helper",
    ("scope_linkage.py", 511): "predicate-helper", ("scope_linkage.py", 532): "control-flow",
    ("schema.py", 64): "control-flow", ("schema.py", 237): "predicate-helper", ("schema.py", 244): "predicate-helper",
    ("schema.py", 326): "predicate-helper", ("schema.py", 523): "predicate-helper", ("schema.py", 615): "internal-invariant",
    ("schema.py", 620): "internal-invariant", ("schema.py", 643): "internal-invariant", ("schema.py", 648): "internal-invariant",
    ("schema.py", 689): "predicate-helper", ("schema.py", 773): "predicate-helper", ("schema.py", 313): "internal-invariant", ("schema.py", 684): "internal-invariant",
    ("store/sqlite.py", 177): "control-flow", ("store/sqlite.py", 252): "control-flow", ("store/sqlite.py", 303): "control-flow",
    ("store/sqlite.py", 372): "control-flow", ("store/sqlite.py", 454): "control-flow", ("store/sqlite.py", 713): "control-flow",
    ("store/sqlite.py", 732): "control-flow", ("store/sqlite.py", 776): "control-flow", ("store/sqlite.py", 841): "control-flow",
    ("store/sqlite.py", 857): "predicate-helper", ("store/sqlite.py", 1012): "control-flow", ("store/sqlite.py", 1959): "control-flow",
    ("store/sqlite.py", 2008): "control-flow", ("store/sqlite.py", 2017): "predicate-helper", ("store/sqlite.py", 159): "argument-check",
    ("store/sqlite.py", 351): "argument-check", ("store/sqlite.py", 2079): "argument-check", ("store/sqlite.py", 2550): "argument-check",
    ("store/sqlite.py", 2565): "argument-check", ("store/sqlite.py", 346): "control-flow", ("store/sqlite.py", 725): "control-flow",
    ("store/sqlite.py", 1292): "control-flow", ("store/sqlite.py", 1568): "control-flow", ("store/sqlite.py", 1580): "control-flow",
    ("store/sqlite.py", 1595): "control-flow", ("store/sqlite.py", 2291): "control-flow", ("store/sqlite.py", 2313): "control-flow",
    ("store/sqlite.py", 2568): "control-flow", ("store/sqlite.py", 2056): "argument-check",
    ("store/revocation.py", 56): "predicate-helper", ("store/revocation.py", 110): "control-flow", ("store/revocation.py", 145): "control-flow",
    ("store/revocation_sweep.py", 172): "control-flow", ("store/revocation_sweep.py", 192): "control-flow",
    ("store/schema_version.py", 1666): "argument-check", ("store/schema_version.py", 1840): "control-flow",
    ("telemetry.py", 466): "control-flow", ("telemetry.py", 487): "control-flow", ("telemetry.py", 514): "control-flow",
    ("mcp_server.py", 555): "cli-usage", ("mcp_server.py", 561): "cli-usage", ("mcp_server.py", 565): "cli-usage", ("mcp_server.py", 577): "cli-usage",
    ("source_identity.py", 59): "argument-check", ("_json.py", 43): "control-flow", ("introspect.py", 54): "argument-check",
}
REASON_TEXT = {
    "argument-check": "not an enforcement point: the caller's input is malformed (type, shape, range or closed parameter vocabulary); the request is refused as ill-formed, not declined on trust or policy",
    "internal-invariant": "not an enforcement point: a validator of the product's own contract (a carrier, ledger, registry, audit record or package consistency), never a decision about a caller's request",
    "predicate-helper": "not an enforcement point: a Boolean/None helper whose consumer takes the decision",
    "control-flow": "not an enforcement point: a lookup returning None for an absent row, an early return, a re-raise after logging, a filter by a non-policy criterion or budget/shape plumbing",
    "cli-usage": "not an enforcement point: command-line usage and exit handling",
}


# THE PREDICATE-HELPER REASON'S SUBJECT (research's second read of the NOT half, 2026-09-19): the generator
# derives each helper's consumers from the source and names them in the reason. For a helper NO product
# function references, the review states the consumer by hand here; a helper with neither REFUSES generation.
CONSUMED_OUTSIDE = {
    "llm/metered.py:Metered.totals": "a public read of the meter (the host and tests); the product never branches on it",
    "schema.py:EvidenceContext.__eq__": "the language's == operator (record equality); no product decision consumes it",
    "schema.py:SuccessorLookup.__eq__": "the language's == operator (record equality); no product decision consumes it",
    "scope.py:same_identity": "exported in scope's __all__ for the 0020 vector harness and tests; no product function calls it",
}

# specs/0041 tranche 1 (2026-09-19): INV-11's mirror, the relation-only quarantine, the kind closure

# specs/0041 tranche 3 (2026-09-19): the operation's refusals and INV-11 at the two whole-record writers

# ---- DERIVED from the instrumented source (derive_keys.py): every fire()-wrapped candidate ----
e("asof/adapter.py", 160, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 162, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 165, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 168, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 173, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 179, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 182, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 184, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 187, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 189, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 193, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 196, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 198, "asof.adapter.adapt.refuse", "0030", "V-EXTRACT", "refuse")
e("asof/adapter.py", 100, "asof.adapter.derive-quarantined", "0030", "V-CARRIER-AGREES", "quarantine")
e("asof/adapter.py", 108, "asof.adapter.derive-use-only", "0030", "V-CARRIER-AGREES", "withhold")
e("asof/classify.py", 167, "asof.classify.assertable-as-of", "0028", "§4b", "withhold")
e("asof/recall.py", 41, "asof.recall.claim", "0028", "§4b", "withhold")
e("asof/recall.py", 37, "asof.recall.grounded", "0028", "§4b", "withhold")
e("asof/resolve.py", 314, "asof.resolve.edge-hidden-or-invalid", "0028", "§4b", "withhold")
e("asof/resolve.py", 307, "asof.resolve.edge-unclassified", "0028", "§4b", "withhold")
e("asof/resolve.py", 261, "asof.resolve.future-T", "0028", "§2c-i", "refuse")
e("asof/resolve.py", 243, "asof.resolve.held-at", "0028", "§2c-i", "withhold")
e("authority.py", 71, "authority.permitted", "0003", "§4a", "refuse")
e("authority.py", 84, "authority.self-assertion", "0003", "§4a", "withhold")
e("compile.py", 161, "compile.grounded-inputs", "0004", "§4", "withhold")
e("diagnostics.py", 276, "diagnostics.send.not-consented", "0015", "§4", "withhold")
e("gate.py", 54, "gate.exclude-procedural", "0037", "V-EXTRACTOR-QUOTE-GATED", "withhold")
e("gate.py", 175, "gate.partition-parts", "0001", "§4", "withhold")
e("gate.py", 122, "gate.scoped-assertable.entitlement", "0011", "§4c", "withhold")
e("gate.py", 118, "gate.scoped-assertable.invisible", "0020", "§4a", "withhold")
e("gate.py", 120, "gate.scoped-assertable.third-party-shaped", "0020", "§4a", "withhold")
e("graph.py", 288, "graph.absorption.cross-scope", "0020", "§4a-iii", "withhold")
e("graph.py", 289, "graph.absorption.no-flattening-plan", "0021", "§4a", "withhold")
e("graph.py", 286, "graph.absorption.scope-unresolved", "0020", "§4a-iii", "withhold")
e("graph.py", 1294, "graph.collapse-for-render", "0012", "§4c", "withhold")
e("graph.py", 355, "graph.correction.identity-mismatch", "0011", "§4b", "refuse")
e("graph.py", 367, "graph.correction.prior-not-active", "0011", "§4b", "refuse")
e("graph.py", 827, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 833, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 835, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 837, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 839, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 841, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 425, "graph.src-revoked", "0022", "§4a", "withhold")
e("graph.py", 429, "graph.src-revoked", "0022", "§4a", "withhold")
e("graph.py", 1199, "graph.strictly-redundant", "0012", "§4c", "withhold")
e("graph.py", 184, "graph.supersession.receipt-boundary", "0014", "R10", "refuse")
e("graph.py", 210, "graph.supersession.replay-mismatch", "0014", "§4b", "refuse")
e("grounding.py", 243, "grounding.ungrounded", "0019", "§4", "downgrade")
e("ingest.py", 310, "ingest.basis-via-remember", "0037", "§4b", "refuse")
e("ingest.py", 371, "ingest.instructions-not-a-list", "0039", "§2a", "downgrade")
e("ingest.py", 299, "ingest.source-id-required", "0006", "§4 rule 9", "refuse")
e("mcp_server.py", 111, "mcp.closed-set.author", "0011", "§4d", "refuse")
e("mcp_server.py", 117, "mcp.closed-set.trust-field", "0011", "§4d", "refuse")
e("__init__.py", 2030, "memory.correct.inactive-edge", "0011", "§4b", "refuse")
e("__init__.py", 2050, "memory.correct.procedural", "0037", "§4a-iii", "refuse")
e("__init__.py", 2086, "memory.correct.refused", "0011", "§4b", "refuse")
e("__init__.py", 1819, "memory.dispute.inactive-edge", "0003", "§4b", "refuse")
e("__init__.py", 1805, "memory.edge.unknown-target", "0041", "INV-5", "refuse")
e("__init__.py", 901, "memory.recall.as-of-on-proactive", "0028", "§2c", "refuse")
e("__init__.py", 1019, "memory.recall.policy-with-as-of", "0027", "v13 §4c", "refuse")
e("__init__.py", 1916, "memory.record-outcome.actor-vocabulary", "0008", "§4", "refuse")
e("__init__.py", 1919, "memory.record-outcome.human-judgment", "0008", "§4", "refuse")
e("__init__.py", 1922, "memory.record-outcome.system-judgment", "0008", "§4", "refuse")
e("__init__.py", 396, "memory.scope.local-origin-missing", "0006", "I9", "refuse")
e("portability.py", 128, "portability.export.non-quiescent", "0010", "X-quiesce", "refuse")
e("portability.py", 697, "portability.import.agreement-invalid", "0025", "§4c", "refuse")
e("portability.py", 238, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 242, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 251, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 255, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 259, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 264, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 271, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 276, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 323, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 326, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 329, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 342, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 780, "portability.import.origin-missing", "0006", "§4", "refuse")
e("portability.py", 1016, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1027, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1040, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1062, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1071, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1090, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 981, "portability.import.race-exhausted", "0009", "§4c", "refuse")
e("portability.py", 835, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 846, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 853, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 862, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 879, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 885, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 889, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 897, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 926, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 948, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 312, "portability.import.restore-not-bool", "0005", "P13", "refuse")
e("portability.py", 316, "portability.import.restore-with-user", "0005", "P5", "refuse")
e("proactive.py", 149, "proactive.eligible", "0012", "§4", "withhold")
e("proactive.py", 88, "proactive.variant", "0012", "I8j", "withhold")
e("proactive.py", 92, "proactive.variant", "0012", "I8j", "withhold")
e("procedural_gate.py", 203, "procedural-gate.actor-present", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 205, "procedural-gate.actor-present", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 207, "procedural-gate.actor-present", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 212, "procedural-gate.actor-present", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 214, "procedural-gate.actor-present", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 217, "procedural-gate.actor-present", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 185, "procedural-gate.positive-form", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 188, "procedural-gate.positive-form", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 190, "procedural-gate.positive-form", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 192, "procedural-gate.positive-form", "0037", "Gate 3", "refuse")
e("procedural_gate.py", 193, "procedural-gate.positive-form", "0037", "Gate 3", "refuse")
e("procedures.py", 165, "procedures.source-id-required", "0006", "§4 rule 9", "refuse")
e("registry.py", 59, "registry.empty-refused", "0025", "§4b-iv X5", "refuse")
e("registry.py", 69, "registry.reserved-shadowed", "0025", "§4b-iv", "refuse")
e("schema.py", 832, "schema.edge.assertable", "0001", "§4", "withhold")
e("schema.py", 833, "schema.edge.assertable", "0001", "§4", "withhold")
e("schema.py", 785, "schema.edge.quarantined", "0001", "§4", "quarantine")
e("schema.py", 786, "schema.edge.quarantined", "0001", "§4", "quarantine")
e("schema.py", 795, "schema.edge.use-only", "0001", "§4", "withhold")
e("schema.py", 796, "schema.edge.use-only", "0001", "§4", "withhold")
e("schema.py", 817, "schema.edge.valid-now", "0028", "S2", "withhold")
e("schema.py", 818, "schema.edge.valid-now", "0028", "S2", "withhold")
e("schema.py", 914, "schema.episode.active", "0022", "§4b-ii", "withhold")
e("schema.py", 933, "schema.episode.assertable", "0001", "§4", "withhold")
e("schema.py", 896, "schema.episode.quarantined", "0001", "§4", "quarantine")
e("schema.py", 907, "schema.episode.use-only", "0001", "§4", "withhold")
e("schema.py", 941, "schema.episode.valid-now", "0028", "S2", "withhold")
e("scope_linkage.py", 535, "scope-linkage.export.ambiguous-absorber", "0020", "§4a-iii", "refuse")
e("scope_linkage.py", 458, "scope-linkage.import.rows", "0020", "R6-2", "refuse")
e("scope_linkage.py", 478, "scope-linkage.import.rows", "0020", "R6-2", "refuse")
e("scope_linkage.py", 389, "scope-linkage.import.winner", "0020", "R6-1", "refuse")
e("scope_linkage.py", 397, "scope-linkage.import.winner", "0020", "R6-1", "refuse")
e("scope_linkage.py", 409, "scope-linkage.import.winner", "0020", "R6-1", "refuse")
e("scope_linkage.py", 413, "scope-linkage.import.winner", "0020", "R6-1", "refuse")
e("scope_read.py", 451, "scope-read.narrow-edges", "0020", "§4e", "withhold")
e("scope_read.py", 417, "scope-read.scoped", "0020", "§4a", "withhold")
e("scope_read.py", 313, "scope-read.view.no-policy", "0006", "§4", "refuse")
e("scope_read.py", 305, "scope-read.view.principal-not-identity", "0006", "§4", "refuse")
e("scope_read.py", 320, "scope-read.view.principal-ungroupable", "0006", "I13", "refuse")
e("scope.py", 717, "scope.classify.evidence-not-digest", "0006", "§4", "refuse")
e("scope.py", 703, "scope.classify.no-policy", "0006", "§4", "refuse")
e("scope.py", 709, "scope.classify.principal-ungroupable", "0006", "I13", "refuse")
e("scope.py", 445, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 466, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 478, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 482, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 484, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 490, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 492, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 495, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 498, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 500, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 765, "scope.filters.apply", "0020", "§4e", "withhold")
e("scope.py", 752, "scope.filters.bad-value", "0020", "§4e", "refuse")
e("scope.py", 744, "scope.filters.not-mapping", "0020", "§4e", "refuse")
e("scope.py", 748, "scope.filters.unknown-field", "0020", "§4e", "refuse")
e("scope.py", 163, "scope.identity.groupable", "0006", "I13", "withhold")
e("scope.py", 642, "scope.membership.abandoned", "0021", "§4a", "refuse")
e("scope.py", 638, "scope.membership.unknown-state", "0021", "§4a", "refuse")
e("scope.py", 305, "scope.policy.digest-overlap", "0006", "§4", "refuse")
e("scope.py", 300, "scope.policy.non-groupable-member", "0006", "I13", "refuse")
e("scope.py", 562, "scope.prune.cycle", "0021", "§4a", "refuse")
e("scope.py", 350, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 353, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 358, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 363, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 373, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("store/sqlite.py", 1633, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1645, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1653, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1660, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1668, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 704, "store.confirm.correlation", "0008", "C9", "refuse")
e("store/sqlite.py", 637, "store.confirm.not-assertable", "0008", "§6d", "refuse")
e("store/sqlite.py", 650, "store.confirm.request-digest", "0008", "C9", "refuse")
e("store/sqlite.py", 632, "store.confirm.unknown-edge", "0008", "§6d", "refuse")
e("store/sqlite.py", 1485, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 1493, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 1526, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 2284, "store.consolidation.abandon-live-lease", "0010", "X7", "refuse")
e("store/sqlite.py", 2097, "store.consolidation.contended", "0010", "X7/X11", "refuse")
e("store/sqlite.py", 2269, "store.consolidation.delete-not-current", "0010", "X21", "refuse")
e("store/sqlite.py", 2129, "store.consolidation.renew-refused", "0010", "X7", "refuse")
e("store/sqlite.py", 2224, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2229, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2234, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2240, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2249, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2256, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2259, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2143, "store.consolidation.write-not-current", "0010", "X23", "refuse")
e("store/sqlite.py", 1308, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1312, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1318, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1323, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1132, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1139, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1143, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1147, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1151, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1157, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1162, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1166, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1728, "store.delete-episode.outcome", "0009", "§4c", "refuse")
e("store/sqlite.py", 1736, "store.delete-episode.reserved", "0010", "X21", "refuse")
e("store/sqlite.py", 890, "store.edges.read-fence", "0001", "§4", "withhold")
e("store/sqlite.py", 2590, "store.embedding.delayed-writer", "0027", "§4f", "refuse")
e("store/sqlite.py", 2597, "store.embedding.stale-content", "0027", "§4f", "refuse")
e("store/sqlite.py", 1625, "store.episode.attested-redaction", "0041", "§4b-ii INV-11", "refuse")
e("store/sqlite.py", 1618, "store.episode.kind-not-recognised", "0041", "§2d-iv/§4h(ii) write path", "refuse")
e("store/sqlite.py", 1613, "store.episode.marker-introduced", "0041", "§4b INV-11's mirror", "refuse")
e("store/sqlite.py", 2302, "store.export.non-quiescent", "0010", "X-quiesce", "refuse")
e("store/sqlite.py", 1403, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1412, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1421, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1426, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1449, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1841, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1846, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1850, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1856, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1863, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1870, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1918, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1959, "store.import.episode-kind-not-recognised", "0041", "§2d-iv/§4h(ii) import boundary", "refuse")
e("store/sqlite.py", 364, "store.journal.pre-epoch", "0029", "§4a", "refuse")
e("store/sqlite.py", 309, "store.journal.reason-not-dispositioned", "0030", "V-TOTAL", "refuse")
e("store/sqlite.py", 317, "store.journal.redaction-reason", "0041", "§4c/§11.2 D1", "refuse")
e("store/migration.py", 62, "store.migration.duplicate-outcome-chain", "0009", "§4c", "refuse")
e("store/migration.py", 118, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 172, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 200, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 226, "store.migration.version", "0013", "§4", "refuse")
e("store/schema_version.py", 1699, "store.open.invalid-version", "0007", "§4a", "refuse")
e("store/schema_version.py", 1771, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 1781, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 1797, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 1807, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 1686, "store.open.locked", "0007", "§4a", "refuse")
e("store/schema_version.py", 1703, "store.open.newer", "0007", "§4a", "refuse")
e("store/schema_version.py", 1671, "store.open.runtime-unsupported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1593, "store.open.unaccepted-shape", "0007", "§4a-v", "refuse")
e("store/schema_version.py", 1601, "store.open.unaccepted-shape", "0007", "§4a-v", "refuse")
e("store/sqlite.py", 1782, "store.outcome.context-ref", "0009", "§4c", "refuse")
e("store/sqlite.py", 1715, "store.read.input-claimed", "0010", "§4b", "withhold")
e("store/sqlite.py", 1712, "store.read.output-not-visible", "0010", "§4b", "withhold")
e("store/sqlite.py", 2433, "store.redact.disposition-changed", "0041", "§4h(i)", "refuse")
e("store/sqlite.py", 2401, "store.redact.input-claimed", "0041/0010", "X21", "refuse")
e("store/sqlite.py", 2382, "store.redact.reason-not-registered", "0041", "§11.2", "refuse")
e("store/sqlite.py", 2378, "store.redact.target", "0041", "§4a/INV-5", "refuse")
e("store/sqlite.py", 2393, "store.redact.target", "0041", "§4a/INV-5", "refuse")
e("store/revocation.py", 140, "store.revocation.integrity", "0022", "§4c", "refuse")
e("store/revocation.py", 139, "store.revocation.ordinal-collision", "0022", "§4c", "refuse")
e("store/revocation_sweep.py", 360, "store.revocation.self-linkage", "0022", "§4c", "refuse")
e("store/revocation_sweep.py", 232, "store.revocation.source-not-revocable", "0022", "I13", "refuse")
e("store/revocation.py", 73, "store.revocation.unknown-state", "0022", "R5-1", "refuse")
e("store/schema_version.py", 1323, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1339, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1343, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1345, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/sqlite.py", 1066, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1084, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1100, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1105, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1183, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1205, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1213, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1232, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1237, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 243, "store.txn.locked", "0013", "§5b", "refuse")
e("store/sqlite.py", 268, "store.txn.locked-retry", "0013", "§5b", "refuse")
e("store/sqlite.py", 502, "store.upsert.attested-redaction", "0041", "§4b-ii INV-11", "refuse")
e("store/sqlite.py", 524, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 530, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 540, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 553, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 559, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 568, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 585, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 595, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 493, "store.upsert.marker-introduced", "0041", "§4b INV-11's mirror", "refuse")
e("store/sqlite.py", 511, "store.upsert.relation-only-quarantine", "0041", "§4h(i)", "refuse")
e("telemetry.py", 545, "telemetry.collector.not-enabled", "0015", "§4", "withhold")
e("telemetry.py", 374, "telemetry.flush.invalid-consent", "0015", "§4", "withhold")
e("telemetry.py", 380, "telemetry.flush.not-enabled", "0015", "§4", "withhold")
e("telemetry.py", 345, "telemetry.preview.invalid-consent", "0015", "§4", "withhold")
e("telemetry.py", 350, "telemetry.preview.not-enabled", "0015", "§4", "withhold")
