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
    ("__init__.py", 917): "control-flow", ("__init__.py", 1514): "control-flow", ("__init__.py", 1655): "control-flow",
    ("__init__.py", 1677): "control-flow", ("__init__.py", 1726): "control-flow", ("__init__.py", 1733): "control-flow",
    ("__init__.py", 1744): "control-flow", ("__init__.py", 1751): "control-flow", ("__init__.py", 1780): "control-flow",
    ("__init__.py", 1806): "control-flow", ("__init__.py", 2090): "internal-invariant", ("__init__.py", 2155): "control-flow",
    ("__init__.py", 293): "internal-invariant", ("__init__.py", 300): "internal-invariant",
    ("__init__.py", 994): "internal-invariant", ("__init__.py", 998): "internal-invariant", ("__init__.py", 1002): "internal-invariant",
    ("__init__.py", 1009): "internal-invariant", ("__init__.py", 1011): "internal-invariant",
    ("agreement.py", 219): "predicate-helper", ("agreement.py", 267): "control-flow", ("agreement.py", 487): "control-flow",
    ("asof/adapter.py", 54): "internal-invariant", ("asof/resolve.py", 117): "internal-invariant", ("asof/resolve.py", 122): "internal-invariant",
    ("asof/resolve.py", 179): "control-flow", ("asof/resolve.py", 204): "predicate-helper",
    ("compile.py", 183): "predicate-helper", ("diagnostics.py", 216): "predicate-helper", ("diagnostics.py", 249): "predicate-helper",
    ("doctor.py", 394): "predicate-helper", ("dryrun.py", 68): "predicate-helper",
    ("graph.py", 56): "predicate-helper", ("graph.py", 71): "predicate-helper", ("graph.py", 230): "internal-invariant",
    ("graph.py", 890): "argument-check", ("grounding.py", 154): "control-flow",
    ("ingest.py", 180): "control-flow", ("ingest.py", 132): "argument-check",
    ("lifecycle.py", 184): "control-flow", ("lifecycle.py", 323): "control-flow",
    ("portability.py", 508): "control-flow",
    ("procedural_gate.py", 49): "argument-check", ("procedures.py", 104): "control-flow", ("procedures.py", 369): "control-flow",
    ("scope.py", 189): "predicate-helper", ("scope.py", 229): "internal-invariant", ("scope.py", 232): "internal-invariant",
    ("scope.py", 234): "internal-invariant", ("scope.py", 387): "predicate-helper", ("scope.py", 596): "control-flow", ("scope.py", 690): "control-flow",
    ("scope_linkage.py", 115): "control-flow", ("scope_linkage.py", 126): "control-flow", ("scope_linkage.py", 510): "predicate-helper",
    ("scope_linkage.py", 511): "predicate-helper", ("scope_linkage.py", 532): "control-flow",
    ("schema.py", 64): "control-flow", ("schema.py", 237): "predicate-helper", ("schema.py", 244): "predicate-helper",
    ("schema.py", 326): "predicate-helper", ("schema.py", 523): "predicate-helper", ("schema.py", 615): "internal-invariant",
    ("schema.py", 620): "internal-invariant", ("schema.py", 643): "internal-invariant", ("schema.py", 648): "internal-invariant",
    ("schema.py", 689): "predicate-helper", ("schema.py", 773): "predicate-helper", ("schema.py", 313): "internal-invariant", ("schema.py", 684): "internal-invariant",
    ("store/sqlite.py", 181): "control-flow", ("store/sqlite.py", 256): "control-flow", ("store/sqlite.py", 309): "control-flow",
    ("store/sqlite.py", 378): "control-flow", ("store/sqlite.py", 460): "control-flow", ("store/sqlite.py", 719): "control-flow",
    ("store/sqlite.py", 738): "control-flow", ("store/sqlite.py", 782): "control-flow", ("store/sqlite.py", 847): "control-flow",
    ("store/sqlite.py", 863): "predicate-helper", ("store/sqlite.py", 1018): "control-flow", ("store/sqlite.py", 2071): "control-flow",
    ("store/sqlite.py", 2098): "control-flow", ("store/sqlite.py", 2107): "predicate-helper", ("store/sqlite.py", 163): "argument-check",
    ("store/sqlite.py", 357): "argument-check", ("store/sqlite.py", 2169): "argument-check", ("store/sqlite.py", 2713): "argument-check",
    ("store/sqlite.py", 2728): "argument-check", ("store/sqlite.py", 352): "control-flow", ("store/sqlite.py", 731): "control-flow",
    ("store/sqlite.py", 1298): "control-flow", ("store/sqlite.py", 1574): "control-flow", ("store/sqlite.py", 1586): "control-flow",
    ("store/sqlite.py", 1601): "control-flow", ("store/sqlite.py", 2381): "control-flow", ("store/sqlite.py", 2403): "control-flow",
    ("store/sqlite.py", 2731): "control-flow", ("store/sqlite.py", 2146): "argument-check",
    ("store/revocation.py", 56): "predicate-helper", ("store/revocation.py", 110): "control-flow", ("store/revocation.py", 145): "control-flow",
    ("store/revocation_sweep.py", 172): "control-flow", ("store/revocation_sweep.py", 192): "control-flow",
    ("store/schema_version.py", 1666): "argument-check", ("store/schema_version.py", 1840): "control-flow",
    ("telemetry.py", 466): "control-flow", ("telemetry.py", 487): "control-flow", ("telemetry.py", 514): "control-flow",
    ("mcp_server.py", 560): "cli-usage", ("mcp_server.py", 566): "cli-usage", ("mcp_server.py", 570): "cli-usage", ("mcp_server.py", 582): "cli-usage",
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
e("asof/classify.py", 181, "asof.classify.assertable-as-of", "0028", "§4b", "withhold")
e("asof/recall.py", 41, "asof.recall.claim", "0028", "§4b", "withhold")
e("asof/recall.py", 37, "asof.recall.grounded", "0028", "§4b", "withhold")
e("asof/resolve.py", 315, "asof.resolve.edge-hidden-or-invalid", "0028", "§4b", "withhold")
e("asof/resolve.py", 307, "asof.resolve.edge-unclassified", "0028", "§4b", "withhold")
e("asof/resolve.py", 261, "asof.resolve.future-T", "0028", "§2c-i", "refuse")
e("asof/resolve.py", 243, "asof.resolve.held-at", "0028", "§2c-i", "withhold")
e("authority.py", 71, "authority.permitted", "0003", "§4a", "refuse")
e("authority.py", 84, "authority.self-assertion", "0003", "§4a", "withhold")
e("compile.py", 169, "compile.grounded-inputs", "0004", "§4", "withhold")
e("diagnostics.py", 276, "diagnostics.send.not-consented", "0015", "§4", "withhold")
e("gate.py", 54, "gate.exclude-procedural", "0037", "V-EXTRACTOR-QUOTE-GATED", "withhold")
e("gate.py", 178, "gate.partition-parts", "0001", "§4", "withhold")
e("gate.py", 125, "gate.scoped-assertable.entitlement", "0011", "§4c", "withhold")
e("gate.py", 119, "gate.scoped-assertable.invisible", "0020", "§4a", "withhold")
e("gate.py", 122, "gate.scoped-assertable.third-party-shaped", "0020", "§4a", "withhold")
e("graph.py", 289, "graph.absorption.cross-scope", "0020", "§4a-iii", "withhold")
e("graph.py", 291, "graph.absorption.no-flattening-plan", "0021", "§4a", "withhold")
e("graph.py", 286, "graph.absorption.scope-unresolved", "0020", "§4a-iii", "withhold")
e("graph.py", 1296, "graph.collapse-for-render", "0012", "§4c", "withhold")
e("graph.py", 357, "graph.correction.identity-mismatch", "0011", "§4b", "refuse")
e("graph.py", 369, "graph.correction.prior-not-active", "0011", "§4b", "refuse")
e("graph.py", 829, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 835, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 837, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 839, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 841, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 843, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 427, "graph.src-revoked", "0022", "§4a", "withhold")
e("graph.py", 431, "graph.src-revoked", "0022", "§4a", "withhold")
e("graph.py", 1201, "graph.strictly-redundant", "0012", "§4c", "withhold")
e("graph.py", 184, "graph.supersession.receipt-boundary", "0014", "R10", "refuse")
e("graph.py", 210, "graph.supersession.replay-mismatch", "0014", "§4b", "refuse")
e("grounding.py", 243, "grounding.ungrounded", "0019", "§4", "downgrade")
e("ingest.py", 310, "ingest.basis-via-remember", "0037", "§4b", "refuse")
e("ingest.py", 371, "ingest.instructions-not-a-list", "0039", "§2a", "downgrade")
e("ingest.py", 299, "ingest.source-id-required", "0006", "§4 rule 9", "refuse")
e("mcp_server.py", 113, "mcp.closed-set.author", "0011", "§4d", "refuse")
e("mcp_server.py", 122, "mcp.closed-set.trust-field", "0011", "§4d", "refuse")
e("__init__.py", 2041, "memory.correct.inactive-edge", "0011", "§4b", "refuse")
e("__init__.py", 2061, "memory.correct.procedural", "0037", "§4a-iii", "refuse")
e("__init__.py", 2097, "memory.correct.refused", "0011", "§4b", "refuse")
e("__init__.py", 1830, "memory.dispute.inactive-edge", "0003", "§4b", "refuse")
e("__init__.py", 1816, "memory.edge.unknown-target", "0041", "INV-5", "refuse")
e("__init__.py", 901, "memory.recall.as-of-on-proactive", "0028", "§2c", "refuse")
e("__init__.py", 1019, "memory.recall.policy-with-as-of", "0027", "v13 §4c", "refuse")
e("__init__.py", 1927, "memory.record-outcome.actor-vocabulary", "0008", "§4", "refuse")
e("__init__.py", 1930, "memory.record-outcome.human-judgment", "0008", "§4", "refuse")
e("__init__.py", 1933, "memory.record-outcome.system-judgment", "0008", "§4", "refuse")
e("__init__.py", 396, "memory.scope.local-origin-missing", "0006", "I9", "refuse")
e("portability.py", 136, "portability.export.non-quiescent", "0010", "X-quiesce", "refuse")
e("portability.py", 779, "portability.import.agreement-invalid", "0025", "§4c", "refuse")
e("portability.py", 258, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 262, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 271, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 275, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 279, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 284, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 291, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 296, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 345, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 348, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 351, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 368, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 381, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 388, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 396, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 404, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 864, "portability.import.origin-missing", "0006", "§4", "refuse")
e("portability.py", 1111, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1122, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1133, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1147, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1153, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1175, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1184, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1203, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1069, "portability.import.race-exhausted", "0009", "§4c", "refuse")
e("portability.py", 920, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 931, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 938, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 947, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 964, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 970, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 974, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 982, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1011, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1033, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 332, "portability.import.restore-not-bool", "0005", "P13", "refuse")
e("portability.py", 337, "portability.import.restore-with-user", "0005", "P5", "refuse")
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
e("schema.py", 843, "schema.edge.assertable", "0001", "§4", "withhold")
e("schema.py", 789, "schema.edge.quarantined", "0001", "§4", "quarantine")
e("schema.py", 801, "schema.edge.use-only", "0001", "§4", "withhold")
e("schema.py", 825, "schema.edge.valid-now", "0028", "S2", "withhold")
e("schema.py", 924, "schema.episode.active", "0022", "§4b-ii", "withhold")
e("schema.py", 943, "schema.episode.assertable", "0001", "§4", "withhold")
e("schema.py", 906, "schema.episode.quarantined", "0001", "§4", "quarantine")
e("schema.py", 917, "schema.episode.use-only", "0001", "§4", "withhold")
e("schema.py", 951, "schema.episode.valid-now", "0028", "S2", "withhold")
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
e("scope.py", 719, "scope.classify.evidence-not-digest", "0006", "§4", "refuse")
e("scope.py", 705, "scope.classify.no-policy", "0006", "§4", "refuse")
e("scope.py", 711, "scope.classify.principal-ungroupable", "0006", "I13", "refuse")
e("scope.py", 447, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 468, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 480, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 484, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 486, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 492, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 494, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 497, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 500, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 502, "scope.closure.walk", "0020", "§4a-iii", "refuse")
e("scope.py", 767, "scope.filters.apply", "0020", "§4e", "withhold")
e("scope.py", 754, "scope.filters.bad-value", "0020", "§4e", "refuse")
e("scope.py", 746, "scope.filters.not-mapping", "0020", "§4e", "refuse")
e("scope.py", 750, "scope.filters.unknown-field", "0020", "§4e", "refuse")
e("scope.py", 163, "scope.identity.groupable", "0006", "I13", "withhold")
e("scope.py", 644, "scope.membership.abandoned", "0021", "§4a", "refuse")
e("scope.py", 640, "scope.membership.unknown-state", "0021", "§4a", "refuse")
e("scope.py", 307, "scope.policy.digest-overlap", "0006", "§4", "refuse")
e("scope.py", 301, "scope.policy.non-groupable-member", "0006", "I13", "refuse")
e("scope.py", 564, "scope.prune.cycle", "0021", "§4a", "refuse")
e("scope.py", 352, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 355, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 360, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 365, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("scope.py", 375, "scope.revalidate", "0006", "§7 tamper-evidence", "refuse")
e("store/sqlite.py", 1639, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1651, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1659, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1666, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 1674, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 710, "store.confirm.correlation", "0008", "C9", "refuse")
e("store/sqlite.py", 643, "store.confirm.not-assertable", "0008", "§6d", "refuse")
e("store/sqlite.py", 656, "store.confirm.request-digest", "0008", "C9", "refuse")
e("store/sqlite.py", 638, "store.confirm.unknown-edge", "0008", "§6d", "refuse")
e("store/sqlite.py", 1491, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 1499, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 1532, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 2374, "store.consolidation.abandon-live-lease", "0010", "X7", "refuse")
e("store/sqlite.py", 2187, "store.consolidation.contended", "0010", "X7/X11", "refuse")
e("store/sqlite.py", 2359, "store.consolidation.delete-not-current", "0010", "X21", "refuse")
e("store/sqlite.py", 2219, "store.consolidation.renew-refused", "0010", "X7", "refuse")
e("store/sqlite.py", 2314, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2319, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2324, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2330, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2339, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2346, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2349, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2233, "store.consolidation.write-not-current", "0010", "X23", "refuse")
e("store/sqlite.py", 1314, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1318, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1324, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1329, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1138, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1145, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1149, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1153, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1157, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1163, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1168, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1172, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1734, "store.delete-episode.outcome", "0009", "§4c", "refuse")
e("store/sqlite.py", 1742, "store.delete-episode.reserved", "0010", "X21", "refuse")
e("store/sqlite.py", 896, "store.edges.read-fence", "0001", "§4", "withhold")
e("store/sqlite.py", 2779, "store.embedding.delayed-writer", "0027", "§4f", "refuse")
e("store/sqlite.py", 2786, "store.embedding.stale-content", "0027", "§4f", "refuse")
e("store/sqlite.py", 2757, "store.embedding.txn-locked", "0041", "§4e (0007 §4c form)", "refuse")
e("store/sqlite.py", 1631, "store.episode.attested-redaction", "0041", "§4b-ii INV-11", "refuse")
e("store/sqlite.py", 1624, "store.episode.kind-not-recognised", "0041", "§2d-iv/§4h(ii) write path", "refuse")
e("store/sqlite.py", 1619, "store.episode.marker-introduced", "0041", "§4b INV-11's mirror", "refuse")
e("store/sqlite.py", 2392, "store.export.non-quiescent", "0010", "X-quiesce", "refuse")
e("store/sqlite.py", 1409, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1418, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1427, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1432, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1455, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1847, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1852, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1856, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1862, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1869, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1876, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1891, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1894, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1897, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1900, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1904, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1908, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1953, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 1984, "store.import.attested-redaction", "0041", "§4b-ii INV-11 at the import boundary (§4g)", "refuse")
e("store/sqlite.py", 2010, "store.import.attested-redaction", "0041", "§4b-ii INV-11 at the import boundary (§4g)", "refuse")
e("store/sqlite.py", 2004, "store.import.episode-kind-not-recognised", "0041", "§2d-iv/§4h(ii) import boundary", "refuse")
e("store/sqlite.py", 370, "store.journal.pre-epoch", "0029", "§4a", "refuse")
e("store/sqlite.py", 315, "store.journal.reason-not-dispositioned", "0030", "V-TOTAL", "refuse")
e("store/sqlite.py", 323, "store.journal.redaction-reason", "0041", "§4c/§11.2 D1", "refuse")
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
e("store/sqlite.py", 1788, "store.outcome.context-ref", "0009", "§4c", "refuse")
e("store/sqlite.py", 1721, "store.read.input-claimed", "0010", "§4b", "withhold")
e("store/sqlite.py", 1718, "store.read.output-not-visible", "0010", "§4b", "withhold")
e("store/sqlite.py", 2518, "store.redact.both-or-neither", "0041", "§4a/INV-5", "refuse")
e("store/sqlite.py", 2584, "store.redact.disposition-changed", "0041", "§4h(i)", "refuse")
e("store/sqlite.py", 2541, "store.redact.input-claimed", "0041/0010", "X21", "refuse")
e("store/sqlite.py", 2522, "store.redact.reason-not-registered", "0041", "§11.2", "refuse")
e("store/sqlite.py", 2533, "store.redact.target", "0041", "§4a/INV-5", "refuse")
e("store/revocation.py", 140, "store.revocation.integrity", "0022", "§4c", "refuse")
e("store/revocation.py", 139, "store.revocation.ordinal-collision", "0022", "§4c", "refuse")
e("store/revocation_sweep.py", 360, "store.revocation.self-linkage", "0022", "§4c", "refuse")
e("store/revocation_sweep.py", 232, "store.revocation.source-not-revocable", "0022", "I13", "refuse")
e("store/revocation.py", 73, "store.revocation.unknown-state", "0022", "R5-1", "refuse")
e("store/schema_version.py", 1323, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1339, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1343, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1345, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/sqlite.py", 1072, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1090, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1106, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1111, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1189, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1211, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1219, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1238, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1243, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 247, "store.txn.locked", "0013", "§5b", "refuse")
e("store/sqlite.py", 272, "store.txn.locked-retry", "0013", "§5b", "refuse")
e("store/sqlite.py", 508, "store.upsert.attested-redaction", "0041", "§4b-ii INV-11", "refuse")
e("store/sqlite.py", 530, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 536, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 546, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 559, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 565, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 574, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 591, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 601, "store.upsert.immutable", "0008/0019/0037", "§6d/V-IMMUTABLE", "refuse")
e("store/sqlite.py", 499, "store.upsert.marker-introduced", "0041", "§4b INV-11's mirror", "refuse")
e("store/sqlite.py", 517, "store.upsert.relation-only-quarantine", "0041", "§4h(i)", "refuse")
e("telemetry.py", 545, "telemetry.collector.not-enabled", "0015", "§4", "withhold")
e("telemetry.py", 374, "telemetry.flush.invalid-consent", "0015", "§4", "withhold")
e("telemetry.py", 380, "telemetry.flush.not-enabled", "0015", "§4", "withhold")
e("telemetry.py", 345, "telemetry.preview.invalid-consent", "0015", "§4", "withhold")
e("telemetry.py", 350, "telemetry.preview.not-enabled", "0015", "§4", "withhold")
