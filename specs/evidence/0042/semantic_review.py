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
    "contention.py": "predicate-helper",     # 0044 §4d (T5): is_live_refusal — consumed by recall's contested groups and the compiler's grounded-inputs site
    "attest_v3.py": "predicate-helper",      # 0045 §4a (T9): ATTEST-3, vendored byte-identical — its returns are the predicate's own verdict, consumed by attestation.attestation
    "attestation.py": "predicate-helper",    # 0045 §2/§4c (T9): the (att, attv) derivation, the attv grammar and g(e) — consumed by ingest's write, the Edge validator and confirm's guard
    "store/lifetime.py": "predicate-helper",  # 0044 §4f-ii (T5): the lifetime transition — consumed by the choke point's effects and the v16 step
    "store/data_migration.py": "internal-invariant",  # 0018 §4i (T6): run_data_migration's refusals are rows of its closed result carrier, release_migration's precedent
    "schema.py": "argument-check", "scope.py": "argument-check", "scope_linkage.py": "internal-invariant",
    "scope_read.py": "control-flow", "semantic.py": "internal-invariant", "source_identity.py": "control-flow",
    "store/base.py": "internal-invariant", "store/current_state.py": "internal-invariant", "store/migration.py": "internal-invariant",
    "store/release_migration.py": "internal-invariant", "store/revocation.py": "internal-invariant",
    "store/revocation_sweep.py": "internal-invariant", "store/schema_version.py": "internal-invariant",
    "store/sqlite.py": "internal-invariant", "telemetry.py": "control-flow", "census.py": "internal-invariant",
}
OVERRIDE = {  # (module, line) -> reason class, where the module default is not the truth for that line
    ("__init__.py", 395): "control-flow", ("__init__.py", 476): "control-flow", ("__init__.py", 604): "control-flow",
    ("__init__.py", 928): "control-flow", ("__init__.py", 1537): "control-flow", ("__init__.py", 1678): "control-flow",
    ("__init__.py", 1700): "control-flow", ("__init__.py", 1749): "control-flow", ("__init__.py", 1756): "control-flow",
    ("__init__.py", 1767): "control-flow", ("__init__.py", 1774): "control-flow", ("__init__.py", 1803): "control-flow",
    ("__init__.py", 1829): "control-flow", ("__init__.py", 2212): "internal-invariant", ("__init__.py", 2300): "control-flow",
    ("__init__.py", 297): "internal-invariant", ("__init__.py", 304): "internal-invariant",
    ("__init__.py", 1005): "internal-invariant", ("__init__.py", 1009): "internal-invariant", ("__init__.py", 1013): "internal-invariant",
    ("__init__.py", 1020): "internal-invariant", ("__init__.py", 1022): "internal-invariant",
    ("agreement.py", 219): "predicate-helper", ("agreement.py", 267): "control-flow", ("agreement.py", 487): "control-flow",
    ("asof/adapter.py", 54): "internal-invariant", ("asof/resolve.py", 117): "internal-invariant", ("asof/resolve.py", 122): "internal-invariant",
    ("asof/resolve.py", 179): "control-flow", ("asof/resolve.py", 204): "predicate-helper",
    ("compile.py", 189): "predicate-helper", ("diagnostics.py", 216): "predicate-helper", ("diagnostics.py", 249): "predicate-helper",
    ("doctor.py", 483): "predicate-helper", ("dryrun.py", 68): "predicate-helper",
    ("graph.py", 59): "predicate-helper", ("graph.py", 74): "predicate-helper", ("graph.py", 233): "internal-invariant",
    ("graph.py", 903): "argument-check", ("grounding.py", 154): "control-flow",
    ("ingest.py", 181): "control-flow", ("ingest.py", 133): "argument-check",
    ("lifecycle.py", 208): "control-flow", ("lifecycle.py", 354): "control-flow",
    ("portability.py", 611): "control-flow",
    ("procedural_gate.py", 49): "argument-check", ("procedures.py", 104): "control-flow", ("procedures.py", 369): "control-flow",
    ("scope.py", 189): "predicate-helper", ("scope.py", 229): "internal-invariant", ("scope.py", 232): "internal-invariant",
    ("scope.py", 234): "internal-invariant", ("scope.py", 387): "predicate-helper", ("scope.py", 596): "control-flow", ("scope.py", 690): "control-flow",
    ("scope_linkage.py", 115): "control-flow", ("scope_linkage.py", 126): "control-flow", ("scope_linkage.py", 510): "predicate-helper",
    ("scope_linkage.py", 511): "predicate-helper", ("scope_linkage.py", 532): "control-flow",
    ("schema.py", 64): "control-flow", ("schema.py", 280): "predicate-helper", ("schema.py", 287): "predicate-helper",
    ("schema.py", 369): "predicate-helper", ("schema.py", 597): "predicate-helper", ("schema.py", 689): "internal-invariant",
    ("schema.py", 694): "internal-invariant", ("schema.py", 717): "internal-invariant", ("schema.py", 722): "internal-invariant",
    ("schema.py", 763): "predicate-helper", ("schema.py", 872): "predicate-helper", ("schema.py", 356): "internal-invariant", ("schema.py", 758): "internal-invariant",
    ("store/sqlite.py", 269): "control-flow", ("store/sqlite.py", 346): "control-flow", ("store/sqlite.py", 405): "control-flow",
    ("store/sqlite.py", 496): "control-flow", ("store/sqlite.py", 579): "control-flow", ("store/sqlite.py", 962): "control-flow",
    ("store/sqlite.py", 1183): "control-flow", ("store/sqlite.py", 1228): "control-flow", ("store/sqlite.py", 1297): "control-flow",
    ("store/sqlite.py", 1313): "predicate-helper", ("store/sqlite.py", 1468): "control-flow", ("store/sqlite.py", 2756): "control-flow",
    ("store/sqlite.py", 2784): "control-flow", ("store/sqlite.py", 2793): "predicate-helper", ("store/sqlite.py", 251): "argument-check",
    ("store/sqlite.py", 475): "argument-check", ("store/sqlite.py", 2855): "argument-check", ("store/sqlite.py", 3716): "argument-check",
    ("store/sqlite.py", 3731): "argument-check", ("store/sqlite.py", 470): "control-flow", ("store/sqlite.py", 1176): "control-flow",
    ("store/sqlite.py", 1759): "control-flow", ("store/sqlite.py", 2035): "control-flow", ("store/sqlite.py", 2049): "control-flow",
    ("store/sqlite.py", 2064): "control-flow", ("store/sqlite.py", 3079): "control-flow", ("store/sqlite.py", 3101): "control-flow",
    ("store/sqlite.py", 3734): "control-flow", ("store/sqlite.py", 2832): "argument-check",
    ("store/revocation.py", 56): "predicate-helper", ("store/revocation.py", 110): "control-flow", ("store/revocation.py", 145): "control-flow",
    ("store/revocation_sweep.py", 172): "control-flow", ("store/revocation_sweep.py", 192): "control-flow",
    ("store/schema_version.py", 1934): "argument-check", ("store/schema_version.py", 2108): "control-flow",
    ("telemetry.py", 466): "control-flow", ("telemetry.py", 487): "control-flow", ("telemetry.py", 514): "control-flow",
    ("mcp_server.py", 563): "cli-usage", ("mcp_server.py", 569): "cli-usage", ("mcp_server.py", 573): "cli-usage", ("mcp_server.py", 585): "cli-usage",
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

# T7 (0044 §4i undo; research's T7 stage-1 classification f8ec28ed: every one an enforcement point that refuses)

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
e("compile.py", 175, "compile.grounded-inputs", "0004", "§4", "withhold")
e("diagnostics.py", 276, "diagnostics.send.not-consented", "0015", "§4", "withhold")
e("gate.py", 54, "gate.exclude-procedural", "0037", "V-EXTRACTOR-QUOTE-GATED", "withhold")
e("gate.py", 178, "gate.partition-parts", "0001", "§4", "withhold")
e("gate.py", 125, "gate.scoped-assertable.entitlement", "0011", "§4c", "withhold")
e("gate.py", 119, "gate.scoped-assertable.invisible", "0020", "§4a", "withhold")
e("gate.py", 122, "gate.scoped-assertable.third-party-shaped", "0020", "§4a", "withhold")
e("graph.py", 292, "graph.absorption.cross-scope", "0020", "§4a-iii", "withhold")
e("graph.py", 294, "graph.absorption.no-flattening-plan", "0021", "§4a", "withhold")
e("graph.py", 289, "graph.absorption.scope-unresolved", "0020", "§4a-iii", "withhold")
e("graph.py", 1309, "graph.collapse-for-render", "0012", "§4c", "withhold")
e("graph.py", 360, "graph.correction.identity-mismatch", "0011", "§4b", "refuse")
e("graph.py", 372, "graph.correction.prior-not-active", "0011", "§4b", "refuse")
e("graph.py", 842, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 848, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 850, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 852, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 854, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 856, "graph.semantic-duplicate.keep", "0012", "§4c", "withhold")
e("graph.py", 430, "graph.src-revoked", "0022", "§4a", "withhold")
e("graph.py", 434, "graph.src-revoked", "0022", "§4a", "withhold")
e("graph.py", 1214, "graph.strictly-redundant", "0012", "§4c", "withhold")
e("graph.py", 187, "graph.supersession.receipt-boundary", "0014", "R10", "refuse")
e("graph.py", 213, "graph.supersession.replay-mismatch", "0014", "§4b", "refuse")
e("grounding.py", 243, "grounding.ungrounded", "0019", "§4", "downgrade")
e("ingest.py", 315, "ingest.basis-via-remember", "0037", "§4b", "refuse")
e("ingest.py", 376, "ingest.instructions-not-a-list", "0039", "§2a", "downgrade")
e("ingest.py", 304, "ingest.source-id-required", "0006", "§4 rule 9", "refuse")
e("mcp_server.py", 113, "mcp.closed-set.author", "0011", "§4d", "refuse")
e("mcp_server.py", 122, "mcp.closed-set.trust-field", "0011", "§4d", "refuse")
e("__init__.py", 1931, "memory.confirm.unknown-target", "0008", "§6c INV-Q2", "refuse")
e("__init__.py", 2163, "memory.correct.inactive-edge", "0011", "§4b", "refuse")
e("__init__.py", 2183, "memory.correct.procedural", "0037", "§4a-iii", "refuse")
e("__init__.py", 2229, "memory.correct.refused", "0011", "§4b", "refuse")
e("__init__.py", 1868, "memory.dispute.inactive-edge", "0003", "§4b", "refuse")
e("__init__.py", 1849, "memory.edge.unknown-target", "0041", "INV-5", "refuse")
e("__init__.py", 1840, "memory.feedback.attested-target", "0041", "§4b-ii INV-11 (derived episodes)", "refuse")
e("__init__.py", 912, "memory.recall.as-of-on-proactive", "0028", "§2c", "refuse")
e("__init__.py", 1030, "memory.recall.policy-with-as-of", "0027", "v13 §4c", "refuse")
e("__init__.py", 2039, "memory.record-outcome.actor-vocabulary", "0008", "§4", "refuse")
e("__init__.py", 2042, "memory.record-outcome.human-judgment", "0008", "§4", "refuse")
e("__init__.py", 2045, "memory.record-outcome.system-judgment", "0008", "§4", "refuse")
e("__init__.py", 400, "memory.scope.local-origin-missing", "0006", "I9", "refuse")
e("portability.py", 152, "portability.export.non-quiescent", "0010", "X-quiesce", "refuse")
e("portability.py", 892, "portability.import.agreement-invalid", "0025", "§4c", "refuse")
e("portability.py", 347, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 351, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 360, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 364, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 368, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 373, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 380, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 385, "portability.import.chain", "0009", "§4c/H5", "refuse")
e("portability.py", 434, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 437, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 440, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 457, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 471, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 478, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 490, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 497, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 505, "portability.import.file", "0005", "§4", "refuse")
e("portability.py", 988, "portability.import.origin-missing", "0006", "§4", "refuse")
e("portability.py", 1276, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1280, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1291, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1306, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1310, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1333, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1342, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1346, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1354, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1373, "portability.import.preflight", "0009", "§4c", "refuse")
e("portability.py", 1234, "portability.import.race-exhausted", "0009", "§4c", "refuse")
e("portability.py", 1044, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1055, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1062, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1071, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1088, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1094, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1098, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1106, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1135, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 1187, "portability.import.record", "0009", "§4c/0014 §2c", "refuse")
e("portability.py", 421, "portability.import.restore-not-bool", "0005", "P13", "refuse")
e("portability.py", 426, "portability.import.restore-with-user", "0005", "P5", "refuse")
e("proactive.py", 154, "proactive.eligible", "0012", "§4", "withhold")
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
e("registry.py", 78, "registry.arity-refused", "0044", "§2c INV-A3/A10", "refuse")
e("registry.py", 82, "registry.arity-refused", "0044", "§2c INV-A3/A10", "refuse")
e("registry.py", 85, "registry.arity-refused", "0044", "§2c INV-A3/A10", "refuse")
e("registry.py", 91, "registry.empty-refused", "0025", "§4b-iv X5", "refuse")
e("registry.py", 101, "registry.reserved-shadowed", "0025", "§4b-iv", "refuse")
e("schema.py", 942, "schema.edge.assertable", "0001", "§4", "withhold")
e("schema.py", 888, "schema.edge.quarantined", "0001", "§4", "quarantine")
e("schema.py", 900, "schema.edge.use-only", "0001", "§4", "withhold")
e("schema.py", 924, "schema.edge.valid-now", "0028", "S2", "withhold")
e("schema.py", 1023, "schema.episode.active", "0022", "§4b-ii", "withhold")
e("schema.py", 1042, "schema.episode.assertable", "0001", "§4", "withhold")
e("schema.py", 1005, "schema.episode.quarantined", "0001", "§4", "quarantine")
e("schema.py", 1016, "schema.episode.use-only", "0001", "§4", "withhold")
e("schema.py", 1050, "schema.episode.valid-now", "0028", "S2", "withhold")
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
e("store/sqlite.py", 846, "store.act-counter.allocate", "0008", "§6f (v7: the never-reset act counter)", "refuse")
e("store/sqlite.py", 2104, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 2116, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 2124, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 2131, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 2150, "store.add-episode", "0009/0010", "X21", "refuse")
e("store/sqlite.py", 3275, "store.confirm-notice.standing", "0041", "§11.6.6 (confirm_notice: a standing row is not pending)", "refuse")
e("store/sqlite.py", 3282, "store.confirm-notice.target-absent", "0041", "§11.6.6 (confirm_notice: a pending notice whose target is gone is inert)", "refuse")
e("store/sqlite.py", 3267, "store.confirm-notice.unknown", "0041", "§11.6.6 (confirm_notice: an unknown or another user's id, one refusal)", "refuse")
e("store/sqlite.py", 881, "store.confirm.active-challenge", "0047", "§4c INV-R13", "refuse")
e("store/sqlite.py", 954, "store.confirm.correlation", "0008", "C9", "refuse")
e("store/sqlite.py", 872, "store.confirm.not-assertable", "0008", "§6d", "refuse")
e("store/sqlite.py", 824, "store.confirm.request-digest", "0008", "C9", "refuse")
e("store/sqlite.py", 895, "store.confirm.source-redacted", "0045", "§4d INV-G10", "refuse")
e("store/sqlite.py", 867, "store.confirm.unknown-edge", "0008", "§6d", "refuse")
e("store/sqlite.py", 1952, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 1960, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 1993, "store.consolidation-contribution", "0014", "§2c", "refuse")
e("store/sqlite.py", 3072, "store.consolidation.abandon-live-lease", "0010", "X7", "refuse")
e("store/sqlite.py", 2886, "store.consolidation.contended", "0010", "X7/X11", "refuse")
e("store/sqlite.py", 3057, "store.consolidation.delete-not-current", "0010", "X21", "refuse")
e("store/sqlite.py", 2870, "store.consolidation.input-redacted", "0041", "§4b-ii INV-11", "refuse")
e("store/sqlite.py", 2917, "store.consolidation.renew-refused", "0010", "X7", "refuse")
e("store/sqlite.py", 3012, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 3017, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 3022, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 3028, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 3037, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 3044, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 3047, "store.consolidation.transition", "0010", "§4b", "refuse")
e("store/sqlite.py", 2931, "store.consolidation.write-not-current", "0010", "X23", "refuse")
e("store/sqlite.py", 1775, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1779, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1785, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1790, "store.contribution", "0014", "§4b", "refuse")
e("store/sqlite.py", 1594, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1601, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1605, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1609, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1613, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1619, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1624, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/sqlite.py", 1628, "store.correction.authorisation", "0011", "§4b", "refuse")
e("store/data_migration.py", 312, "store.data-migration.op-id-conflict", "0018", "§4i I32", "refuse")
e("store/data_migration.py", 483, "store.data-migration.read-refused", "0018", "§4i §4d", "refuse")
e("store/data_migration.py", 437, "store.data-migration.redacted-not-considered", "0044", "§4f.1 INV-A7", "withhold")
e("store/data_migration.py", 332, "store.data-migration.registry-changed", "0018", "§4i I25", "refuse")
e("store/data_migration.py", 445, "store.data-migration.withheld-revoked", "0044", "§4f.2 INV-A11", "withhold")
e("store/sqlite.py", 2209, "store.delete-episode.outcome", "0009", "§4c", "refuse")
e("store/sqlite.py", 2217, "store.delete-episode.reserved", "0010", "X21", "refuse")
e("store/sqlite.py", 1346, "store.edges.read-fence", "0001", "§4", "withhold")
e("store/sqlite.py", 3782, "store.embedding.delayed-writer", "0027", "§4f", "refuse")
e("store/sqlite.py", 3789, "store.embedding.stale-content", "0027", "§4f", "refuse")
e("store/sqlite.py", 3760, "store.embedding.txn-locked", "0041", "§4e (0007 §4c form)", "refuse")
e("store/sqlite.py", 2143, "store.episode.attested-redaction", "0041", "§4b-ii INV-11", "refuse")
e("store/sqlite.py", 2095, "store.episode.kind-not-recognised", "0041", "§2d-iv/§4h(ii) write path", "refuse")
e("store/sqlite.py", 2082, "store.episode.marker-introduced", "0041", "§4b INV-11's mirror", "refuse")
e("store/sqlite.py", 2090, "store.episode.retired-reason-not-registered", "0041", "§11.2 D1 (write path)", "refuse")
e("store/sqlite.py", 3090, "store.export.non-quiescent", "0010", "X-quiesce", "refuse")
e("store/sqlite.py", 1870, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1879, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1888, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1893, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 1916, "store.flattening", "0021", "§4a", "refuse")
e("store/sqlite.py", 2325, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2330, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2334, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2340, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2347, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2354, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2375, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2380, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2384, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2392, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2396, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2400, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2406, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2456, "store.import-plan", "0009", "§4c", "refuse")
e("store/sqlite.py", 2503, "store.import.attested-redaction", "0041", "§4b-ii INV-11 at the import boundary (§4g)", "refuse")
e("store/sqlite.py", 2510, "store.import.attested-redaction", "0041", "§4b-ii INV-11 at the import boundary (§4g)", "refuse")
e("store/sqlite.py", 2554, "store.import.attested-redaction", "0041", "§4b-ii INV-11 at the import boundary (§4g)", "refuse")
e("store/sqlite.py", 2563, "store.import.attested-redaction", "0041", "§4b-ii INV-11 at the import boundary (§4g)", "refuse")
e("store/sqlite.py", 2548, "store.import.episode-kind-not-recognised", "0041", "§2d-iv/§4h(ii) import boundary", "refuse")
e("store/sqlite.py", 2648, "store.import.notice-body-conflict", "0041", "§4g", "refuse")
e("store/sqlite.py", 2690, "store.import.notice-record-unredacted", "0041", "§11.6.6 (INV-RR12/RR14: a record an import creates, or a restore's held record, beside its notice must show it)", "refuse")
e("store/sqlite.py", 2711, "store.import.notice-record-unredacted", "0041", "§11.6.6 (INV-RR12/RR14: a record an import creates, or a restore's held record, beside its notice must show it)", "refuse")
e("store/sqlite.py", 2741, "store.import.notice-record-unredacted", "0041", "§11.6.6 (INV-RR12/RR14: a record an import creates, or a restore's held record, beside its notice must show it)", "refuse")
e("store/sqlite.py", 2493, "store.import.reason-not-registered", "0041", "§11.2 D1 (import boundary)", "refuse")
e("store/sqlite.py", 2532, "store.import.reason-not-registered", "0041", "§11.2 D1 (import boundary)", "refuse")
e("store/sqlite.py", 488, "store.journal.pre-epoch", "0029", "§4a", "refuse")
e("store/sqlite.py", 411, "store.journal.reason-not-dispositioned", "0030", "V-TOTAL", "refuse")
e("store/sqlite.py", 419, "store.journal.redaction-reason", "0041", "§4c/§11.2 D1", "refuse")
e("store/sqlite.py", 428, "store.journal.reinstatement-reason", "0029", "§4b-i (v12, INV-J1)", "refuse")
e("store/migration.py", 227, "store.migration.duplicate-outcome-chain", "0009", "§4c", "refuse")
e("store/migration.py", 85, "store.migration.postcondition", "0013", "§4f (v33, 0013-PA1: each step checked at the step)", "refuse")
e("store/migration.py", 284, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 348, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 376, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 402, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 458, "store.migration.version", "0013", "§4", "refuse")
e("store/migration.py", 491, "store.migration.version", "0013", "§4", "refuse")
e("store/sqlite.py", 3224, "store.notice.state-domain", "0041", "§11.6.6 (T4: the notice state's one writer)", "refuse")
e("store/schema_version.py", 1967, "store.open.invalid-version", "0007", "§4a", "refuse")
e("store/schema_version.py", 2039, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 2049, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 2065, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 2075, "store.open.legacy", "0007", "§4h", "refuse")
e("store/schema_version.py", 1954, "store.open.locked", "0007", "§4a", "refuse")
e("store/schema_version.py", 1971, "store.open.newer", "0007", "§4a", "refuse")
e("store/schema_version.py", 1939, "store.open.runtime-unsupported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1854, "store.open.unaccepted-shape", "0007", "§4a-v", "refuse")
e("store/schema_version.py", 1861, "store.open.unaccepted-shape", "0007", "§4a-v", "refuse")
e("store/schema_version.py", 1869, "store.open.unaccepted-shape", "0007", "§4a-v", "refuse")
e("store/sqlite.py", 2267, "store.outcome.context-ref", "0009", "§4c", "refuse")
e("store/sqlite.py", 2196, "store.read.input-claimed", "0010", "§4b", "withhold")
e("store/sqlite.py", 2193, "store.read.output-not-visible", "0010", "§4b", "withhold")
e("store/sqlite.py", 3424, "store.redact.both-or-neither", "0041", "§4a/INV-5", "refuse")
e("store/sqlite.py", 3497, "store.redact.disposition-changed", "0041", "§4h(i)", "refuse")
e("store/sqlite.py", 3469, "store.redact.input-claimed", "0041/0010", "X21", "refuse")
e("store/sqlite.py", 3618, "store.redact.nothing-to-redact", "0041", "§4b-ii (round 11: the owner's ruling, nothing to redact)", "refuse")
e("store/sqlite.py", 3430, "store.redact.reason-not-registered", "0041", "§11.2", "refuse")
e("store/sqlite.py", 3443, "store.redact.target", "0041", "§4a/INV-5", "refuse")
e("store/sqlite.py", 613, "store.redacted-reason.not-a-redaction", "0041", "§11.2 (only a redaction writes `redacted`)", "refuse")
e("store/sqlite.py", 802, "store.registry.request-redacted", "0008", "§6g (v7: the terminal rule, INV-Q7)", "refuse")
e("store/sqlite.py", 831, "store.registry.result-missing", "0008", "§6c (v7: replay reconstructs from result_ref; a dangling ref is an integrity conflict)", "refuse")
e("store/sqlite.py", 805, "store.registry.verb-held", "0008", "§6c (v7: the registry first; a held id names its verb)", "refuse")
e("store/sqlite.py", 1033, "store.reply.actor", "0047", "§2c who wrote it (a closed label until 0050)", "refuse")
e("store/sqlite.py", 1029, "store.reply.kind", "0047", "§2c INV-R8", "refuse")
e("store/sqlite.py", 1042, "store.reply.marker", "0047/0041", "§2c INV-R7 / 0041 INV-RR1", "refuse")
e("store/sqlite.py", 1063, "store.reply.procedural-edge", "0047", "§4d ruling INV-R19", "refuse")
e("store/sqlite.py", 1058, "store.reply.redacted-edge", "0047", "§0 INV-R9", "refuse")
e("store/sqlite.py", 996, "store.reply.request-digest", "0047/0008", "§4b INV-R15/R24 (0008 §6c)", "refuse")
e("store/sqlite.py", 1075, "store.reply.resolve-repeat", "0047", "§4b INV-R14", "refuse")
e("store/sqlite.py", 1100, "store.reply.resolve-repeat", "0047", "§4b INV-R14", "refuse")
e("store/sqlite.py", 1071, "store.reply.resolve-target", "0047", "§4b INV-R14", "refuse")
e("store/sqlite.py", 1003, "store.reply.result-missing", "0008/0047", "§6c (reply: replay reconstructs from result_ref; a dangling ref is an integrity conflict)", "refuse")
e("store/sqlite.py", 1039, "store.reply.shape", "0047", "§4b the closed request (research's T10a F1)", "refuse")
e("store/sqlite.py", 1053, "store.reply.unknown-edge", "0047", "§2c INV-R9", "refuse")
e("store/revocation.py", 140, "store.revocation.integrity", "0022", "§4c", "refuse")
e("store/revocation.py", 139, "store.revocation.ordinal-collision", "0022", "§4c", "refuse")
e("store/revocation.py", 345, "store.revocation.revoke-reason-not-registered", "0041", "§11.2 D1 (revoke)", "refuse")
e("store/revocation_sweep.py", 360, "store.revocation.self-linkage", "0022", "§4c", "refuse")
e("store/revocation_sweep.py", 232, "store.revocation.source-not-revocable", "0022", "I13", "refuse")
e("store/revocation.py", 73, "store.revocation.unknown-state", "0022", "R5-1", "refuse")
e("store/schema_version.py", 1586, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1602, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1606, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/schema_version.py", 1608, "store.runtime-supported", "0007", "§4a-viii", "refuse")
e("store/sqlite.py", 1153, "store.supersession.absorb-acted", "0047", "§4e INV-R17 (a plan absorbing an acted prior is stale)", "refuse")
e("store/sqlite.py", 1522, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1540, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1556, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1561, "store.supersession.integrity", "0014", "§4b", "refuse")
e("store/sqlite.py", 1645, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1667, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1675, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1694, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 1699, "store.supersession.plan", "0014/0019", "§4b", "refuse")
e("store/sqlite.py", 337, "store.txn.locked", "0013", "§5b", "refuse")
e("store/sqlite.py", 362, "store.txn.locked-retry", "0013", "§5b", "refuse")
e("store/data_migration.py", 556, "store.undo.ambiguous-outcome", "0044", "§4i (research's T7 annotation: no undo lookup chooses between two)", "refuse")
e("store/data_migration.py", 612, "store.undo.correlation", "0008", "C9 (the C8 fallback)", "refuse")
e("store/data_migration.py", 589, "store.undo.edge-unavailable", "0044", "§4i.2", "refuse")
e("store/data_migration.py", 566, "store.undo.no-outcome", "0044", "§4i.2 INV-A12", "refuse")
e("store/data_migration.py", 583, "store.undo.not-applicable", "0044", "§4i.2 INV-A12", "refuse")
e("store/data_migration.py", 571, "store.undo.not-restored", "0044", "§4i.2 INV-A12", "refuse")
e("store/data_migration.py", 627, "store.undo.request-digest", "0008", "C9", "refuse")
e("store/data_migration.py", 634, "store.undo.result-missing", "0008", "§6c (v7: replay reconstructs from result_ref; a dangling ref is an integrity conflict)", "refuse")
e("store/data_migration.py", 578, "store.undo.testimony", "0044", "§4i.2 R2-05 INV-A17", "refuse")
e("store/sqlite.py", 639, "store.upsert.attested-redaction", "0041", "§4b-ii INV-11", "refuse")
e("store/sqlite.py", 671, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 677, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 687, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 700, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 706, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 715, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 726, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 741, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 751, "store.upsert.immutable", "0008/0019/0037/0045", "§6d/V-IMMUTABLE/INV-G13", "refuse")
e("store/sqlite.py", 653, "store.upsert.invalidation-reason-not-registered", "0041", "§11.2 D1 (write path)", "refuse")
e("store/sqlite.py", 630, "store.upsert.marker-introduced", "0041", "§4b INV-11's mirror", "refuse")
e("store/sqlite.py", 658, "store.upsert.relation-only-quarantine", "0041", "§4h(i)", "refuse")
e("telemetry.py", 545, "telemetry.collector.not-enabled", "0015", "§4", "withhold")
e("telemetry.py", 374, "telemetry.flush.invalid-consent", "0015", "§4", "withhold")
e("telemetry.py", 380, "telemetry.flush.not-enabled", "0015", "§4", "withhold")
e("telemetry.py", 345, "telemetry.preview.invalid-consent", "0015", "§4", "withhold")
e("telemetry.py", 350, "telemetry.preview.not-enabled", "0015", "§4", "withhold")
