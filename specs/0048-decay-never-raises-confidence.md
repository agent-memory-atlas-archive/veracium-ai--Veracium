# Feature spec: maintenance never raises confidence — the decay bounds (0002's N4, carried)

Spec-Status: draft

*<!-- canonical machine-readable state; the header table below carries the narrative. Only `accepted` authorises implementation. -->*

| | |
|---|---|
| **Author / session** | research (veracium-research-d5), the candidate's author → dev, adopted at rest and re-read from the file: v2 2026-10-10 from `0048-decay-never-raises-confidence-CANDIDATE.md` (sha16 f7336e49d33d1494) |
| **Version** | **v2 — 2026-10-10.** *Re-read before editing; quote the version you approve.* **v2 folds the owner's answer to Q1, "Yes, guard the store" (2026-10-10, first-hand in the dev session, relayed by dev): part C and N4f are IN, unconditional.** v1: research 2c134739, never adopted. A standalone carrier for one invariant of `specs/0002-maintenance-provenance-invariant.md` (Spec-Status `deferred`), on the owner's decision of 2026-10-10 (relayed by dev, given first-hand in the dev session): **"B"**, a small standalone spec, so the fix reaches `lifecycle.py` (guarded) through review rather than through an exception. No Spec-Exception fits: the hostile value is the host's own configuration, not an attacker's, so `security-hotfix` does not apply. |
| **Status** | *see `Spec-Status:` at the top — canonical.* |
| **Internal reviewers** | research (author) · dev |
| **External review** | required: the change touches two guarded files, `src/veracium/lifecycle.py` and `src/veracium/store/sqlite.py` |
| **Decision + date** | — |
| **Path** | full |

---

## 1. Problem and motivation

`specs/0002` states, as N4, that **no maintenance operation raises `confidence`**, and lists five tests that would
enforce it (N4b, N4b′, N4c, N4d, and the N4 property test). **None of the five exists** (§2c-ii, row 6). 0002 is
deferred, so the invariant has been a sentence for ten weeks. It is false today in exactly one place:

- `MemoryConfig` (`src/veracium/config.py`) is a plain `@dataclass`. `decay_factor` and `confidence_floor` are
  unvalidated: `2.0`, `-1.0`, `nan` and `inf` are each accepted at construction, and assignment after construction is
  accepted too (§2c-ii, rows 1–2).
- `expire()` (`src/veracium/lifecycle.py:72–73`) writes the decayed confidence with
  `e.provenance.model_copy(update={"confidence": e.provenance.confidence * config.decay_factor})`. pydantic's
  `model_copy(update=…)` **skips validation**, so `Provenance.confidence`'s declared bound (`Field(ge=0.0, le=1.0)`,
  `src/veracium/schema.py`) does not hold on this path. A config-only fix would leave this second hole, because
  `expire()` takes `config` duck-typed: any object with a `decay_factor` attribute is accepted.

**What happens if we do nothing.** Two facts decide the severity, and both were measured (§2c-ii, rows 3–5):

1. **With the shipped expiry table the decay branch is unreachable.** No `Volatility` maps to `ExpiryBehavior.DECAY`
   in `schema.DEFAULT_EXPIRY` (0 of 5), and no file in `src/`, `tests/`, `examples/`, `docs/`, `README.md` or
   `CHANGELOG.md` maps one. The branch runs only for a host that edits that exported, mutable module dict.
2. **When a host does reach it, the result is worse than a raised number.** With `DEFAULT_EXPIRY[SLOW] = DECAY` and
   `decay_factor=2.0`, `expire()` writes confidence `1.8` (0.9 × 2.0). The store accepts the write, but every later
   read of that user's edges raises `ValidationError` (`Edge.model_validate_json` on the read path enforces the bound
   the write skipped). With `decay_factor=nan` the value is stored as `NULL` and the reads raise the same way. **One
   maintenance run poisons the user's whole edge listing.**

So **a default store never reaches the decay branch**: it takes a host that maps a class to DECAY **and** sets an
out-of-range factor. The defect is latent in the shipped configuration and severe on the one path that reaches it. The cost of the fix
is small, and it turns a recurring invariant ("configuration may narrow, never widen", 0001; 0002 L727–731) into an
enforced one on the two numeric knobs that can widen it.

**Alternatives rejected.**
- **Remove `ExpiryBehavior.DECAY`.** It is unreachable by default, but `ExpiryBehavior` and `DEFAULT_EXPIRY` are
  exported (`schema.__all__`), so a host that maps DECAY today would break. Rejected for this spec; kept as §10 Q3.
- **Clamp instead of refuse** (`min(1.0, c·f)`). A clamp turns a host's misconfiguration into a silent behaviour
  (factor 2.0 would mean "never decays"), and NaN has no clamp. Refusal at construction is visible at host startup.
- **Validate the config only.** Leaves the duck-typed `config` path and the unvalidated copy (above).
- **Make `MemoryConfig` frozen.** Fixes assignment, but changes a public dataclass's API for every field; hosts may
  legitimately mutate other fields. Rejected in favour of validating the two fields on assignment (§10 Q4).

---

## 2. Field contracts touched

| field | read / written | its documented contract | every other consumer | does this change preserve the contract? |
|---|---|---|---|---|
| `MemoryConfig.decay_factor` | read by `expire()` | "confidence multiplier when a DECAY fact expires" (`config.py`) | `lifecycle.py` only | yes: it narrows the accepted values to the ones the comment already implies (a multiplier that decays) |
| `MemoryConfig.confidence_floor` | read by `expire()` | "below this, a decayed fact is invalidated" (`config.py`) | `lifecycle.py` only | yes: values outside [0, 1] could never be a floor of a value in [0, 1] |
| `Provenance.confidence` | written by `expire()`'s decay | `Field(default=0.9, ge=0.0, le=1.0)` (`schema.py`) | 8 files in `src/` (`why`, `lifecycle`, `dryrun`, `store/revocation`, `store/revocation_sweep`, `store/sqlite`, `contribution`, `graph`) | yes: the change makes the declared bound hold on a path where it did not |

Consumers enumerated by `grep -rcE '\.confidence\b|"confidence"' src/veracium --include=*.py | grep -v ':0$'` and
`grep -rn 'decay_factor\|confidence_floor' src/veracium`. **No meaning changes**, so no documentation states an old
meaning; the CHANGELOG gains a "who should take this" note (§8).

---

## 2c. Untrusted inputs — REQUIRED, blocking

| uncontrolled input | empty | malformed | unrecognised | adversarial | **invariant that pins it** |
|---|---|---|---|---|---|
| host configuration: `MemoryConfig(decay_factor=…, confidence_floor=…)` | n/a (defaults apply) | non-number, `bool`, `nan`, `±inf`: **refused** at construction | — | `> 1` or `< 0`: **refused** at construction; boundaries `0.0` and `1.0` **accepted** | **N4b**, **N4b′** |
| host configuration: assignment after construction (`c.decay_factor = 2.0`) | — | as above: **refused** | — | as above: **refused** | **N4b-assign** |
| host configuration: a duck-typed `config` object passed to `expire()` (not a `MemoryConfig`) | — | a non-number factor: the validated write **refuses** | — | factor `> 1`, `< 0` or `nan`: the validated write **refuses**; nothing is stored | **N4d**, **N4e** |
| host configuration: `schema.DEFAULT_EXPIRY` edited to map a class to DECAY | — | — | a non-`ExpiryBehavior` value: out of scope (unchanged behaviour, §8) | DECAY mapped: the decay path runs, under N4b–N4e | **N4**, **N4d** |
| data written by an older version: an edge whose stored confidence is `> 1` or `NULL` (only possible for a host that mapped DECAY with a factor `> 1` or `nan` before this fix) | — | the read path already **refuses** (`ValidationError`); unchanged by this spec | — | — | **none in this spec: §10 Q2 (repair)** — named, not hidden |

The last row has no invariant **in this spec**, and that is stated rather than filled: repairing rows already
written is a separate decision (§10 Q2). This spec prevents new ones.

### 2c-ii. Assertions about reach — REQUIRED

All commands run at veracium `0f93840` on CPython 3.14.7, from a git-archive copy (`PYTHONPATH=src`).

| # | assertion | command that establishes it | result |
|---|---|---|---|
| 1 | `MemoryConfig` accepts out-of-range and non-finite bounds at construction | `python -c "from veracium.config import MemoryConfig as M; [M(decay_factor=v) for v in (2.0, float('nan'), -1.0, float('inf'))]; [M(confidence_floor=v) for v in (2.0, -0.5, float('nan'))]"` | no exception (all 7 accepted) |
| 2 | assignment after construction is accepted | `python -c "from veracium.config import MemoryConfig as M; c=M(); c.decay_factor=2.0; print(c.decay_factor)"` | `2.0` |
| 3 | the shipped expiry table maps no class to DECAY | `python -c "from veracium.schema import DEFAULT_EXPIRY as D, ExpiryBehavior as B; print(sum(v==B.DECAY for v in D.values()), len(D))"` | `0 5` |
| 4 | nothing shipped maps DECAY or edits the table | `git grep -nE 'DEFAULT_EXPIRY\|ExpiryBehavior\.DECAY' -- src tests examples docs README.md CHANGELOG.md` | only the definition, `schema.__all__`, and `lifecycle.py:31,65,68` (the import and the two branch reads) |
| 5 | with DECAY mapped and `decay_factor=2.0`, the write succeeds and the user's reads then fail | a scratch `SqliteStore(":memory:")`, one SLOW edge at confidence 0.9 observed 400 days before `now`, `DEFAULT_EXPIRY[SLOW]=DECAY`, `expire(…, MemoryConfig(decay_factor=2.0))`, then `store.edges(U, active_only=False, include_quarantined=True)` | `expire` returns normally; the read raises `ValidationError … provenance.confidence: Input should be less than or equal to 1`. With `nan`: `… Input should be a valid number … input_value=None`. With `0.5`: confidence `0.45`, read succeeds |
| 6 | none of 0002's five named N4 tests exists | `for t in test_no_maintenance_op_raises_confidence test_config_bounds_are_validated test_boundary_configs_are_still_valid test_declared_bounds_hold_under_in_place_mutation test_decay_through_expire_cannot_exceed_the_bound; do git grep -c "def $t" -- tests; done` | 0 hits for each (the sixth, `test_no_maintenance_op_widens_disclosure`, exists) |
| 7 | the only bounded field in `schema.py`'s pydantic models is `Provenance.confidence`; `Provenance` is frozen; `validate_assignment` is off | enumerate every `BaseModel` subclass defined in `veracium.schema`, every field whose `metadata` carries `Ge`/`Le`/`Gt`/`Lt`/`Interval` | `[('Provenance', 'confidence', ['Ge(ge=0.0)', 'Le(le=1.0)'], frozen=True, validate_assignment=False)]` |
| 8 | of the seven `Provenance` copy-with-update sites in `src/`, four write `confidence`, and only the decay site multiplies by a host value | `grep -rnE 'model_copy\(\s*update' src/veracium`, then each site's update keys | `lifecycle.py:72` (× `decay_factor`); `store/sqlite.py:704` (confirm: `max(c, 0.9)`); `graph.py:514` (`max(incoming, prior)`); `store/sqlite.py:894` (0022's recompute: the value is read from a stored row, `store/revocation.py:190`). The other three (`scope_read.py:407`, `store/sqlite.py:2454`, `portability.py:863`) do not write `confidence` |
| 9 | no call site in `src/`, `tests/` or `examples/` sets either bound | `git grep -nE 'decay_factor\s*=\|confidence_floor\s*=' -- src tests examples` | no hits (the declarations in `config.py` read `decay_factor: float = 0.5`, which the pattern does not match; any keyword use `decay_factor=…` would) |
| 10 | the spec 0002 text reviewed at its seventh external review already carried N4's confidence clause and N4b–N4d | `git log --before=2026-08-02T12:53:00Z -1 -- specs/0002-maintenance-provenance-invariant.md` → `36374ae`; `git show 36374ae:specs/0002-… \| grep -cE '^\| \*\*N4[bcd]'` | `36374ae`; N4 row with "or raises `confidence`"; 4 rows. *Scope of this claim: the v7 verdict says "Invariant approved a seventh time", about 0002's headline invariant ("may never widen [trust]"); that the reviewer approved each N4 row is not claimed.* |

Rows 8's three non-decay `confidence` writers stay in range **because their inputs do** (each takes a maximum of
stored values, or a stored value). That is a dependency, not a guarantee, and part C (§4) closes it at the store's write
boundary: whatever a copy site computes, an out-of-bound edge is refused before it is stored.

---

## 3. Trust-class matrix — REQUIRED, blocking

`expire()`'s decay is **unary** (one edge at a time) and **maintain-time**, so this is a state-transition table.
Classes enumerated from the enums at `0f93840`: `EvidenceAuthor` = user, third_party, system, assistant;
`Disclosure` = mentionable, use_only, quarantined.

| edge's `author_of_evidence` | mentionable | use_only | quarantined |
|---|---|---|---|
| user | c → c·f, f ∈ [0, 1]; disclosure, author unchanged | same | same |
| third_party | same | same | same |
| system | same | same | same |
| assistant | same | same | same |

Every cell is the same rule, because decay does not read the class: **confidence can only fall or stay
(f = 1.0)**, and below `confidence_floor` the edge is invalidated (narrowing). After this change no cell can raise
confidence or write one outside [0, 1].

- Can it make a **user-asserted fact non-assertable**? Yes, by design: a DECAY fact below the floor is invalidated
  ("decayed"). Unchanged by this spec, and only for a host that mapped DECAY.
- Can **non-user content gain user-grade authority, confidence or currency**? Today, yes: confidence above 1.0 for any
  class. **After: no.** That is the change.
- Can it **clear `needs_confirmation`**? No; the decay branch does not touch it.
- Does it **merge, drop or overwrite provenance**? It replaces the stamp with a copy differing only in `confidence`;
  the validated write keeps every other field.

**Write-time or maintain-time?** Maintain-time: no new evidence arrives, so the only permitted direction is down.

## 3b. Authorization and scope — *full specs only*

n/a — `expire(store, user_id, …)` reads and writes one user's edges; nothing crosses a user, tenant or scope boundary,
and no principal sees anything new. The one cross-cutting effect today (a poisoned row makes **that user's** reads
raise) is removed by the change.

---

## 4. Behaviour

**A. `MemoryConfig` validates its two decay bounds** (`src/veracium/config.py`, not guarded). `decay_factor` and
`confidence_floor` must each be a real number (`int` or `float`, **not** `bool`), finite, with `0.0 ≤ x ≤ 1.0`. A
violation raises `ValueError` naming the field and the value, **at construction and on assignment** (a
`__setattr__` check on these two fields only; §10 Q4). The boundaries `0.0` and `1.0` stay valid. Defaults (0.5, 0.3)
are unchanged.

**B. The decay write is validated** (`src/veracium/lifecycle.py`, guarded). The new stamp is built so that pydantic
validates it (for example `Provenance.model_validate({**p.model_dump(), "confidence": c * f})`, or the equivalent);
a factor that would produce a value outside [0, 1], or NaN, raises **before anything is written**. This covers a
duck-typed `config` that is not a `MemoryConfig`. With a valid `MemoryConfig`, B never raises: c ∈ [0, 1] and
f ∈ [0, 1] give c·f ∈ [0, c].

**C. The store refuses to persist an edge that violates a declared bound** (the owner's answer to Q1). One
helper serialises an edge for storage after re-validating it; the seven writes of the edges table's `json` column in
`src/veracium/store/sqlite.py` (the SQL at L640, 722, 794, 850, 898, 2089, 2884 at `0f93840`, found by
`grep -nE 'INSERT (OR [A-Z]+ )?INTO edges|UPDATE edges SET[^"]*json'`) go through it, and a gate refuses a raw write.
This closes the class at the boundary instead of at one site. **A refusal raises before the SQL statement runs**, so
nothing is written; inside a transaction the existing rollback applies. With A and B in place, C never fires on a
valid configuration; it is the defence for every path that computes a bounded value (§2c-ii row 8), present or future.

**Interfaces:** `MemoryConfig` construction and assignment can now raise `ValueError` for the two fields. No CLI, MCP
or export-format change. **Rendering:** none.

**Migration:** none for stores written under the shipped expiry table (§2c-ii row 3: they cannot contain a decayed
out-of-range value). For a host that mapped DECAY with a factor > 1 or NaN **before** this fix, rows already written
remain unreadable; that is §10 Q2, unchanged by A–C.

---

## 5. Regime analysis — where does this behave differently?

- **Repeated maintenance runs compound**: c·fⁿ. With f ∈ [0, 1] the sequence is non-increasing, and it reaches the
  floor in finitely many runs whenever f < 1 and the floor is > 0. Tested by running `expire()` repeatedly (N4).
- **The boundaries**: f = 1.0 never decays; f = 0.0 drives confidence to 0 in one run (invalidated if floor > 0);
  floor = 0.0 never invalidates by decay; floor = 1.0 invalidates every decayed fact below 1.0. All four are tested
  (N4b′, N4).
- **Cost of C**: one re-validation per edge write. Measured as a microbenchmark only: `Edge.model_validate(e.model_dump())`
  ≈ 20 µs per edge against ≈ 11 µs for `model_dump_json()` alone (CPython 3.14.7, c6a.2xlarge, `timeit`, best of 5 ×
  20,000; 2026-10-10). **Not a workload measurement**: no ingest or maintenance run was timed.
- **Scale** does not enter: the rule is per edge, and the tests use small constructed stores, which reach every
  regime above. **Cold vs warm**: none (no cache).

---

## 6. Invariants and executable checks — REQUIRED, blocking

| invariant | executable check | where it runs |
|---|---|---|
| **N4** (confidence half) no maintenance operation raises `confidence` | `test_no_maintenance_op_raises_confidence` — property-based over a random sequence of `expire()` runs on edges of every volatility, with DECAY mapped for the test, under valid configs: every edge's confidence after ≤ before, and in [0, 1] | CI |
| **N4b** `MemoryConfig` rejects both bounds outside [0, 1], NaN and ±inf, and `bool` | `test_config_bounds_are_validated` — both fields × {>1, <0, nan, +inf, −inf, True, "0.5"} must raise `ValueError` naming the field | CI |
| **N4b′** the exact boundaries remain accepted | `test_boundary_configs_are_still_valid` — 0.0 and 1.0 on both fields, construct and assign. *A regression test: the cheapest wrong fix is an exclusive bound.* | CI |
| **N4b-assign** the bounds hold on assignment | `test_config_bounds_hold_on_assignment` — every rejected value of N4b, assigned after construction, raises, and the field keeps its old value | CI |
| **N4c** (restated from 0002: the hole moved) no write path stores a value outside a declared bound | `test_declared_bounds_hold_on_every_write_path` — **enumerated from the models**, not hand-listed: for every pydantic field in `veracium.schema` carrying `Ge`/`Le`/`Gt`/`Lt`, (i) construction past the bound raises, (ii) assignment raises (frozen model or `validate_assignment`), and (iii) **an AST enumeration of every `model_copy(update=…)` in `src/` that writes a bounded field must appear in a declared table with its reason** ("validated", or "in range by construction: <inputs>"). A new copy site writing a bounded field without an entry fails the test | CI |
| **N4d** the bound holds through the real path | `test_decay_through_expire_cannot_exceed_the_bound` — drives `expire()` (DECAY mapped) with a hostile **duck-typed** config (factor 2.0, −1.0, nan): `expire()` raises, and the store's rows are byte-identical to before | CI |
| **N4e** a valid config never makes B raise | `test_valid_decay_never_raises` — every factor/floor pair on a grid including both boundaries, over confidences {0, 0.3, 0.9, 1.0}: `expire()` completes and every stored row reads back | CI |
| **N4f** no edge write bypasses the validating serialiser, and the serialiser refuses an out-of-bound edge | `test_every_edge_write_goes_through_the_validating_serialiser` — AST over `src/veracium/store/sqlite.py`: every write of the edges table's `json` column takes its value from the helper; and `test_the_store_refuses_an_out_of_bound_edge` — an edge whose provenance carries confidence 1.8 (built with `model_construct`, as a buggy path would) is refused by `add_edge`, and the table is unchanged | CI |

**Planned mechanism mutants** (the closure-mutant rule of 2026-10-10 applies to any code finding this spec's review
raises; planning them here costs nothing). Each must be killed by the cells named, with the honest controls passing:

| mutant | reintroduces | killed by |
|---|---|---|
| construction check removed | N4b | `test_config_bounds_are_validated` |
| assignment check removed | N4b-assign | `test_config_bounds_hold_on_assignment` |
| exclusive bound (`0 < x < 1`) | N4b′ | `test_boundary_configs_are_still_valid` |
| NaN-blind comparison (`x < 0 or x > 1`) | N4b (nan) | `test_config_bounds_are_validated` |
| decay write back to unvalidated `model_copy` | N4d | `test_decay_through_expire_cannot_exceed_the_bound` |
| a copy site writing `confidence` removed from the declared table | N4c | `test_declared_bounds_hold_on_every_write_path` |
| the store helper serialises without validating | N4f | `test_the_store_refuses_an_out_of_bound_edge` |
| one edge write bypasses the helper | N4f | `test_every_edge_write_goes_through_the_validating_serialiser` |

**Reproducer retention:** §2c-ii row 5's run becomes the honest control of N4d (DECAY mapped, factor 0.5 → 0.45, read
succeeds).

---

## 7. Failure modes and reversibility

- **Silent failure today**: a host maps DECAY with factor > 1; nothing is visible until the next read of that user's
  edges raises, possibly days later (the next `expire()` run, then the next read). **After**: a bad `MemoryConfig`
  raises at host startup; a bad duck-typed config raises inside `expire()` before any write.
- **Reversible?** The change is a refusal; it writes nothing. A host that relied on `decay_factor > 1` (to raise
  confidence) loses that behaviour, which N4 forbids.
- **Partial failure**: B raises before `store.add_edge(e)`, and `expire()` has already invalidated or updated earlier
  edges in its loop. **Whether `expire()` is transactional across edges is unchanged by this spec**; a raise mid-loop
  leaves earlier edges processed, which is the existing behaviour for any exception there. Stated, not changed.
- **Existing tests that store an out-of-bound edge on purpose** would now be refused by C; the implementation finds
  them by running the suite, and each is either a test of the old defect (rewritten to expect the refusal) or a bug.
- **Attack surface**: none new. The change removes one way for a configuration value to influence stored state
  outside its declared range.

---

## 8. Claims and limits

**What we will say** (CHANGELOG): *"`MemoryConfig` now rejects `decay_factor` and `confidence_floor` outside
[0, 1] (and NaN/±inf), at construction and on assignment; the decay write in `expire()` is validated. **Who should
take this:** hosts that set either bound, or map a volatility class to `ExpiryBehavior.DECAY`. With the shipped
expiry table the decay path is not reached."*

**What this does NOT establish:**
- that confidence values are calibrated or meaningful; only that maintenance keeps them in range and never raises them;
- anything about the **disclosure** half of N4 (its test exists and is unchanged);
- validation of any other `MemoryConfig` field;
- that values already stored out of range are repaired (C refuses new ones; §10 Q2);
- that `DEFAULT_EXPIRY` edits are a supported configuration surface.

---

## 9. Brief for the external reviewer

- **Least sure of:** (1) whether C's helper covers every edge write (the gate enumerates the SQL writes of the `json`
  column; a write we did not recognise as one is the risk); (2) whether a `__setattr__` check on two fields of a plain dataclass is the right mechanism,
  versus a validated config type; (3) whether "unreachable by default" understates the risk, given `DEFAULT_EXPIRY`
  is exported and mutable.
- **Where we may have overstated:** §2c-ii row 10 scopes 0002's v7 approval to its headline invariant on purpose;
  tell us if the record supports more or less.
- **What would change our minds:** evidence that hosts map DECAY in practice (then Q2's repair becomes blocking), or
  that the duck-typed `config` is a documented extension point (then B is the primary control, not defence in depth).
- **Reviewer-safe copy:** nothing generalised.

---

## 10. Open questions

| # | question | who decides | by when | class |
|---|---|---|---|---|
| Q1 | Include **C**? **RESOLVED 2026-10-10: "Yes, guard the store"** (the owner, first-hand in the dev session, relayed by dev). C and N4f are in. | owner | — | resolved |
| Q2 | **Repair** for rows already written out of range by a host that mapped DECAY: a doctor check plus a repair verb, or a documented manual fix? No shipped configuration can have written them (§2c-ii row 3). | owner + dev | before the release carrying this | pre-release |
| Q3 | Should DECAY stay reachable only by editing a module dict, become a `MemoryConfig` field, or be removed? | owner | — | deferred |
| Q4 | Assignment validation: `__setattr__` on the two fields (this draft) or a frozen/validated config type? | dev + external reviewer | before acceptance | blocking |

---

## Reviewer checklist

- [ ] §3 has no unanswered cells (decay is unary: a state-transition table, every class enumerated from the enums)
- [ ] Prohibitions AND permissions tested: N4b (refusals) and N4b′/N4e (boundaries and valid grids accepted)
- [ ] Every default fails closed: a bad bound refuses at construction; a bad duck-typed factor refuses before writing
- [ ] §2c has a row per uncontrolled input; the one without an invariant here (older rows) is named and sent to Q2
- [ ] §2c-ii: every reach claim carries its command and result
- [ ] §2 consumers enumerated by grep
- [ ] Every §6 invariant has a check, and each planned mutant names the cell that must kill it
- [ ] §5 regimes are reached by constructed stores
- [ ] §3b: n/a with reason
- [ ] §8 states what this does not establish
- [ ] §10 questions each carry a class
