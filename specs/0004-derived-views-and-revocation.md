# Feature spec: derived views must not outlive a revoked trust decision

Spec-Status: accepted

*<!-- canonical machine-readable state; the header table below carries the narrative. Only `accepted` authorises implementation. -->*

> **draft v3.1 — REFRESHED 2026-08-17, internal round 1 folded and PASSED.** Split out of
> `0002` on 2026-08-01 and never reviewed; sixteen days of shipping moved the
> ground under it, so every mechanical claim below was RE-EXECUTED before this
> revision (§2c-ii carries the commands and their real output, run 2026-08-17).
> **Three things changed and are folded here:** (1) the fix is no longer new
> behaviour — `0003`'s refusal-contention rule already drops the wiki in the
> same mutation, for a NARROWER condition, so this spec now GENERALISES shipped
> code rather than introducing a mechanism; (2) `graph.py` no longer calls
> `invalidate_edge` — supersession invalidations ride the store's plan
> primitive, which *strengthens* the store-layer argument and moves its
> evidence; (3) `0020` excludes the wiki from principal-bearing recall
> entirely, so the exposure is now precisely the UNSCOPED path.
> **This spec is on `0022`'s critical path** (source revocation must reach what
> the model reads). **What `0022` §7b's rider must now say changed at v3.1:** with
> §4 drop-by-default, `revoked_source` needs NO addition to any trigger set — it
> already drops. The rider registers it in `DISPOSITIONED_REASONS` so W5 passes,
> which is a process edit, not a behaviour one. Still same-commit at that pair's
> acceptance; the failure mode if it is forgotten is now a RED BUILD rather than
> a silently retained wiki.

| | |
|---|---|
| **Author / session** | dev (`~/Dev/veracium`) |
| **Version** | **v3.4 (drafted by research 2026-10-23; ADOPTED by dev 2026-10-23 from research eb9cfb05, candidate sha256 5b4167a0da43bbb7…) — W10–W13: A SAME-ID REPLACEMENT IS A TRANSITION.** R-II round 2's RII-R2-01 (external, P1) and research's stage-1 read of it (research `bae9faae`, `55a8dd6f`). A public `add_edge` that replaced an existing edge under its own id changed what the wiki may assert, and it passed neither `_invalidate_edge_row` nor any eviction. The changes were: retiring the edge under a dropping reason, moving a challenged record's same-value key, lowering its `disclosure`, or replacing its content. `add_episode` did the same for episodes. Two premises of this spec were false for that path. One is §2c's "never perform an active→inactive TRANSITION", with W7's "this is what makes the born-state producers safe". The other is §4's "there is no post-ingest quarantine path", with §2's `Provenance.disclosure` row. Both rested on syntax that a whole-record replace never matches: a `SET active=0` sweep and a `disclosure\s*=` grep. Edits: §1 (one note), §2 (one row annotated, four new), §2c (one row annotated, one new), §2c-ii (two rows annotated, one new), §3 (seven rows), §4 (two paragraphs annotated), §4c (new), §5 (two rows), §6 (W7 annotated; W10–W13 new), §8 (one limit annotated, one new), §9 (one paragraph), §10 (W-Q3), the Review closure row RII-R2-01. **W1–W6, W8 and W9 are unchanged.** **v3.3 (drafted by research 2026-10-22; ADOPTED by dev 2026-10-22 from research 753198de, candidate sha256 e085b62ab5b2bcc5…) — W9: THE RULE REACHES THE BODY A RECALL SERVES, NOT ONLY THE CACHE.** R-II round 2's D10 (research's stage-1 read of the round-2 package design, measured at veracium `0e1489e`). A wiki body compiled during a recall was served for that call after a dropping invalidation of a fact it drew on: at the call's challenge snapshot, or during the compile itself. W1 drops the CACHE; it cannot reach a body held by the call. Edits: §3 (two rows), §4b (new), §5 (one row), §6 W9, §8 (one limit), §9 (one paragraph), the Review closure row D10. **W1–W8 are unchanged.** **v3.1** — internal round 1 folded and PASSED (research, 2026-08-17: R1 inverted cell, R2 the missed producer class, W-Q1 ruled; v3 @ `01a2d42`, PASS closed @ `da1a805b`). **v3.1 folds the packaging nit — and the nit found a SECOND carrier**: the ABSENT-reason cell still read v2's inverted rationale (now UNREACHABLE-BY-SIGNATURE, drops if forced), and chasing it showed §4 still stated the rule as a DENY-list of dropping reasons, which is the same inversion R1 caught in §2c. §4 is now drop-by-default over a closed RETAIN allow-list; W5 splits into a runtime constant and a process constant so the polarity is carried in CODE, not prose. **v3.2 — EXTERNAL round 1 (F5): the §5 regime table still read "flagged, not decided (W-Q1)" while §4, W8 and the question table all carried the resolved ruling. The FOURTH carrier of a decision whose other three were updated — in the document whose own v3.1 lesson was that a finding is not closed until every carrier is swept, and whose commit message said so. Folded, and the miss is recorded IN the cell rather than only here, because that is what v3.1 claimed to have learned.** |
| **Status** | *see `Spec-Status:` — canonical.* Split from `0002` §M8/§11c, unchanged in substance. |
| **Internal reviewers** | research — **found the defect**; round 1 PASS 2026-08-17 (R1/R2 + W-Q1 ruled), fix verified independently by both sessions |
| **External review** | required — touches `compile.py` and the store write path |
| **Decision + date** | **v3.4 ACCEPTED 2026-10-23 on the owner's word** ("I accept  0004 v3.4 and 0047 v1.17"), jointly with 0047 v1.17, after research's read of dev's adoption (5d78a79; research f9523943). Dev accepted the fix design on research's stage-1 read the same day. R-II round 3 carries v3.4 to the external reviewer. **v3.3 ACCEPTED 2026-10-22 on the owner's word** ("I accept 0004 v3.3"), after research's read of the adoption deltas and dev's adoption (ea8c638, with the deltas in 3163dbc and 4fc2448). The fix was ruled by the owner earlier the same day, "Fix now" (ledger 417490b). R-II round 2 carries v3.3 to the external reviewer. **ACCEPTED 2026-08-20** — external round 21, ATOMIC with `0022`/`0023` (Spec-Status flipped draft→accepted in the authorizing commit, per the reviewer's instruction). Implemented 2026-08-20/21; released 0.13.0. *(Row filled 2026-08-22 — the spec-table audit found it empty two days after acceptance.)* |
| **Path** | full |

> **Why this is its own spec.** It was filed in `0002` because that is where the
> maintenance audit found it. `0002` is a **retrospective for a shipped hotfix**
> and must be closeable; M8 is a **proposal** and is not. Keeping them together
> meant an unshipped fix held a finished record open, and everything citing
> `0002` waited behind both. **The finding is unchanged — only its home is.**

---

## 1. Problem and motivation

**Found by research, reproduced here.** §3 marks `compile.py` clean and the
architectural note covers *a correct filter defeated by upstream corruption of
its input*. **This is a third failure shape: the filter is correct, its input is
correct, and the OUTPUT is cached across subsequent trust changes.**

`compile.py:74` recompiles only after `wiki_recompile_after_writes` store
versions (**default 8**), and `__init__.py:225` appends the wiki to
**`grounded_parts`**. So a revocation takes effect on the edge immediately and
**not on the wiki**:

```
default wiki_recompile_after_writes = 8
wiki built: True
after dispute():
  edge active       : [False]
  'Acme' in GROUNDED: True      <-- disputed fact still asserted
```

**A user's explicit trust action is silently ineffective on the one surface that
matters — what the model reads.** Same for a late supersession, correction or
quarantine.

**Reachability, measured rather than inferred.** `cli.py:198` sets
`wiki_recompile_after_writes = 10**9 if has_wiki else 0`, so **once a wiki
exists the CLI never recompiles**. But `dispute` and `correct` are **not CLI
verbs** — `grep -n "add_parser" src/veracium/cli.py` lists telemetry ·
selfcheck · diagnostics · export · import · forget · recall · remember ·
introspect. **So the unbounded case is not "CLI user disputes and nothing
happens"; it is the mixed path: a host revokes through the API, an operator
later reads the same store with `veracium recall`, and that path never
recompiles — so the revoked fact stays in the grounded block indefinitely.**
Narrower than "the CLI is unbounded", and still real.

**Fix costs nothing and fails closed: a trust-reducing event DROPS the wiki
rather than recompiling it.** `invalidate_edge` with reason in
`{disputed, corrected, superseded}`, and any quarantine, empties the cache. No
LLM call, no latency; you lose curated breadth until the next natural recompile
and never assert revoked content.

> **Two clauses of the finding as filed are corrected in §4, and this is the
> finding AS FILED, not the normative rule.** (i) "any quarantine" is
> unreachable — there is no post-ingest quarantine path. (ii) The drop set is
> written above as a DENY-list, `{disputed, corrected, superseded}`; §4 states
> the rule in the opposite polarity, **drop by default with a closed RETAIN
> allow-list**, because the deny form silently retains on any reason nobody
> enumerated. **§4 governs.**
>
> **v3.4: clause (i)'s correction was itself wrong.** A same-ID `add_edge` or `add_episode` replacement
> lowers a stored record's `disclosure` after ingest. The struck clause returns in transition form, as one
> class of §4c's rule (W10).

**Finding for the spec, not an advisory** — attacker-free, and self-healing
within 8 writes on the library default. But it is **the same shape as both
advisories**: a derived artifact preserving a trust decision after the decision
changed.

---

## 2. Field contracts touched

| field | read / written | documented contract | consumers | change here |
|---|---|---|---|---|
| the compiled `wiki` cache (`get_wiki`/`set_wiki`) | read at recall, written at compile | a curated grounded view, recompiled every `wiki_recompile_after_writes` store versions | `recall()`'s grounded block (`__init__.py:595`) | DROPPED — not recompiled — whenever a trust-reducing invalidation commits |
| `invalidate_edge(edge_id, at, reason)` | written | deactivates an edge with a reason | `Memory.dispute()`/`correct()`, `lifecycle` expiry | the trust-reducing reasons additionally empty the user's wiki, in the SAME mutation |
| the supersession plan's `prior_invalidations` | written | the whole-outcome atomic plan (`0003` §4f) | `apply_supersession_plan` | same rule at the second invalidation site — this is where supersession now lives |
| `Provenance.disclosure` | written at ingest, **and by any same-ID replacement** (v3.4) | *v3.0–v3.3 read "written once at ingest", which is false for a same-ID replace (§4c)* | gate, render, the wiki's admission | v3.4: a change is an assertion-view change, which evicts the wiki and fails the bind (§4c) |
| `add_edge(edge)` replacing an EXISTING id (`_upsert_edge_row`: also the supersession plan's `prior_upserts` and its incoming insert) | written | `INSERT OR REPLACE`, under the 0008 §6d guards | every reader of `edges` | v3.4: when the replacement changes the record's assertion view, the user's wiki is evicted in the same transaction (§4c, W10) |
| `add_episode(episode)` replacing an existing id, and every other `episodes` write | written | `INSERT OR REPLACE` | every reader of `episodes` | v3.4: the same rule (§4c, W10) |
| `discard_wiki(user_id, text, store_version)` (v3.4, new) | written | deletes the wiki row only if it is still that row | `compile.bound_wiki` | a compiled body that fails its bind takes the row it published with it (W13) |
| `transition_consolidation_if_current(…, OUTPUTS_DURABLE)`, the 0010 visibility cutover | written | the op state flips which representation every ordinary read sees (X9), and bumps the version (X14) | every ordinary read of `episodes` | v3.4: also evicts the user's wiki, in the cutover's own transaction (§4c, W10) |

## 2c. Untrusted inputs — REQUIRED, blocking

| uncontrolled input | empty | malformed | unrecognised | adversarial | governing rule |
|---|---|---|---|---|---|
| the invalidation `reason` — **PRODUCERS: `Memory.dispute()`/`correct()` (host-initiated), `lifecycle` expiry/decay (the store's OWN clock-driven machinery), `apply_supersession_plan` (the store's own write path), and — post-`0022` — the revocation sweep** | **UNREACHABLE BY SIGNATURE** — `reason: str` is a required positional with no default on BOTH the protocol (`store/base.py:143`) and the implementation (`sqlite.py:263`), so there is no arity by which a caller omits it. Should an untyped caller pass `""` or `None`, it is not a special case: it falls to the SAME unrecognised rule and **DROPS**. **No cell in this row retains** (v3; internal-round nit — this cell was the last survivor of v2's inverted rationale, quoted and corrected in the next column) | an unknown reason string → **DROPS** (internal R1 — v2 had this INVERTED, and the inversion is worth naming: v2 said "retained (fail-OPEN on breadth, never on assertion)", which is backwards. Retaining on an unrecognised reason is precisely the assertion-side risk — if the unknown reason meant "revoked", a retained wiki serves revoked content. Dropping costs breadth only. A spec whose whole thesis is failing closed had a fail-OPEN cell in it) | a reason added by a future spec → drops at RUNTIME immediately, and the W5 registry check additionally FAILS until that spec dispositions it | a caller passing `lapsed` for a genuine revocation to keep the wiki alive | **two layers, in this order**: unknown-drops at runtime (the behaviour), then W5's registry (the process). v2 left W5 standing alone, which §9 itself called out as the only thing standing there |
| the wiki cache itself | absent → nothing to drop, no-op | — | — | a stale cache surviving a trust change | the whole point: the drop is unconditional on cache content |
| **`Edge.invalidation_reason` supplied AT CONSTRUCTION — the producer class v2 MISSED (internal R2; found by this spec's own §9 attack).** `invalidation_reason` is a settable field (`schema.py:249`) and `add_edge` accepts an Edge already carrying one, so the PUBLIC CONSTRUCTOR and the FORMAT-7 IMPORT round-trip both produce reason-bearing records that pass NEITHER drop site | — | — | — | a host constructing a born-invalid edge, or an import carrying one | **VERIFIED NON-TRANSITION, and the argument is now stated rather than assumed**: these producers create records that are ALREADY inactive; they never perform an active→inactive TRANSITION, and a record that was never active never contributed to a compiled wiki — no transition, no staleness. Import additionally cannot flip an existing record (its idempotency is exact-equality; a differing record REFUSES). **The defended invariant is therefore transition-form: every active→inactive transition passes the drop, and W7 enforces it structurally** — **v3.4: TRUE ONLY FOR A FRESH ID.** `add_edge` given the id of an EXISTING active edge replaces it; it does not construct one. A born-invalid record written over an active one IS an active→inactive transition, and it passed neither drop site (RII-R2-01, the reviewer's retirement witness). The invariant is restated over the assertion view, which a replacement cannot avoid (§4c, W10). W7 is annotated with it |
| **a same-ID replacement record (v3.4)**: every field of the Edge or Episode a host passes to `add_edge` / `add_episode` under an existing id | — | refused where an existing guard applies (0008 §6d, 0019 U4, 0037 §3, 0041 §4b, 0045 §2) | — | a replacement that lowers `disclosure`, replaces the content, or retires the record under a dropping reason, while a body still asserts the old record | **the assertion view (§4c):** a change to the view evicts at the write and fails the bind. A field outside the view is a KEEP, recorded with its reason in `schema.ASSERTION_VIEW_KEEPS`, and the partition is total (W11) |

### 2c-ii. Assertions about reach — RE-EXECUTED 2026-08-17

| assertion | command | result (run 2026-08-17) |
|---|---|---|
| the defect is STILL LIVE — a plain trust-reducing invalidation leaves the wiki served | build a store, `set_wiki`, `invalidate_edge(reason)`, `get_wiki` | wiki SURVIVES for `disputed`, `corrected` AND `superseded` — all three reproduce |
| the wiki still enters the grounded block | `grep -n "grounded_parts.append(wiki)" src/veracium/__init__.py` | `:595` (was `:225` at v1 — the citation drifted, the fact did not) |
| `compile.py` no longer carries the recompile gate | `grep -rn "wiki_recompile_after_writes" src/veracium/` | `config.py:40` (default 8) · `__init__.py:508` · `cli.py:207` (`10**9` once a wiki exists) · `selfcheck.py:43`; **`compile.py` does not appear** — v1's citation is stale |
| a wiki-drop ALREADY ships, on a narrower condition | `grep -n "DELETE FROM wiki" src/veracium/store/sqlite.py` | `:275` (in `invalidate_edge`, gated on `_edge_in_refusal`) and `:605` (in the supersession plan, gated on `touches_contention`) — **both `0003` refusal-contention rules** |
| `invalidate_edge` is still a choke point, but **`graph.py` is no longer among its callers** | `grep -rn "invalidate_edge(" --include=*.py src/veracium/` | `__init__.py:1181` (disputed) · `:1371` (corrected) · `lifecycle.py:53` (lapsed) · `:57` (decayed) · the `base.py`/`sqlite.py` definitions. Supersession moved into `apply_supersession_plan`'s `prior_invalidations` (`sqlite.py:326/505/550`) — **so the fix needs BOTH sites**, which v1 did not know |
| **`active=0` has exactly ONE writer, and BOTH drop sites funnel through it** (executed while folding internal R2 — stronger than the review's own "no third writer" formulation) | `grep -rn "SET active" --include=*.py src/veracium/` | a single hit: `sqlite.py:251`, inside `_invalidate_edge_row`, whose only callers are `invalidate_edge` (`:265`) and the supersession plan loop (`:551`). **This relocates the fix — see §4** *(v3.4: lexical only. A same-ID `INSERT OR REPLACE` writes `active=0` without a `SET active` statement; RII-R2-01)* |
| stored `disclosure` is still written in exactly one place | `grep -rn "disclosure\s*=" --include=*.py src/veracium/` | 7 hits, but only `ingest.py:181/199` WRITE a stored value; `scope_read.py:384` narrows a **`model_copy`** for the response and never persists; the rest are reads. The §4 correction stands, for a sharper reason *(v3.4: lexical only. A same-ID replace lowers a stored `disclosure` without an assignment, and the correction fell with it; see §4)* |
| (v3.4) a same-ID replacement changes what the wiki may assert, and nothing evicts it, at veracium `86cb30e` | the external reviewer's two witnesses (R-II round 2), and research's stage-1 probes in the research repo (`bae9faae`, its r2-01-stage1 evidence): two real connections, the default threshold of eight | every class in §4c's table was asserted. With a modelled eviction at the write, the compiled body was still asserted after a demotion, a content change and a drawn-record-becomes-a-twin replacement. An eviction on ANY stored change turned W8's pin red |

## 3. Trust-class matrix

**Not applicable in the usual direction, and that is the finding.** No trust
class is mis-assigned here: the filter is correct, its input is correct, and the
**output is cached across a subsequent trust change**. Every class is affected
identically, because the wiki is compiled from the grounded set and then frozen.

| edge state at compile | trust change after | served? | correct? |
|---|---|---|---|
| active, assertable | `dispute()` | **yes** | **NO** |
| active, assertable | `correct()` | **yes** | **NO** |
| active, assertable | superseded by a later ingest | **yes** | **NO** |
| active, assertable | `lapsed` / `decayed` | yes | acceptable — staleness, not revocation |
| active, assertable, drawn by a body compiled during the current recall | `dispute()`, `correct()`, a supersession or `revoked_source`, committed after the compile read it and before the call serves the body | **yes (v3.2)** → withheld (v3.3, W9) | v3.2: **NO** |
| the same | `lapsed` / `decayed` / `absorbed_duplicate` | yes | acceptable — the retain set (W3, W8) |
| active, assertable | a same-ID replacement retiring it under a dropping reason | **yes (v3.3)** → evicted, and the bind withholds (v3.4, W10, W12) | v3.3: **NO** |
| active, assertable | a same-ID replacement lowering its `disclosure` (`quarantined`, `use_only`) | **yes (v3.3)** → evicted and withheld (v3.4) | v3.3: **NO**. The same call rendered it UNVERIFIED |
| active, assertable | a same-ID replacement of its content (`subject`, `relation`, `object`, `valid_from`) | **yes (v3.3)** → evicted and withheld (v3.4) | v3.3: **NO**. It is `corrected`'s own case: the host replaced the content |
| active, assertable, unchallenged | a same-ID replacement of a CHALLENGED record that makes this one its same-value twin (0047's same-value twin rule) | **yes (v3.3)** → evicted; the bind's snapshot withholds it (v3.4; 0047 v1.17) | v3.3: **NO** |
| the same | a same-ID replacement changing only a KEEP field (the outcome counters, `note`, `confidence`, `needs_confirmation`) | yes | acceptable — the view is unchanged, so W3 and W8 hold on the replace path (W10's KEEP controls) |
| an episode, assertable | a same-ID replacement that retires it, lowers its `disclosure`, or changes its `date` or `summary` | **yes (v3.3)** → evicted and withheld (v3.4) | v3.3: **NO** |
| an episode, assertable, claimed as a consolidation input | the consolidation cutover, which hides the inputs and reveals the outputs before the inputs are deleted | **yes (v3.3)**, alongside the outputs in the same call → evicted at the cutover; the bind reads a hidden input as absent (v3.4) | v3.3: **NO**. One call showed both representations, against 0010 X9 |

**This is a third failure shape**, distinct from both advisories: 0.4.1 and
0.4.4 were *a correct filter defeated by corruption of its input*. Here nothing
upstream is corrupt. **A derived view that outlives its inputs is not downstream
of them** — the sentence that falsified `compile.py`'s guarded-list exclusion.

---

## 4. Behaviour

**Where — ONE function, corrected AGAIN at v3.** Folding internal R2 turned up
a fact neither v1 nor v2 had: **`active=0` has exactly one writer in the
codebase** — `_invalidate_edge_row` (`sqlite.py:251`) — and BOTH store paths
call it (`invalidate_edge:265`, the supersession plan loop `:551`). So the fix
does not belong at two call sites that must each remember it; **it belongs
INSIDE `_invalidate_edge_row`, the single point every active→inactive
transition already passes.** It has the `reason` and the `user_id` in hand,
which is everything the rule needs.

This is strictly better than v2's two-site design, and the difference is not
stylistic: at two sites a THIRD invalidation path added later inherits nothing
and the defect returns silently; inside the sole writer, any future path
inherits the drop by construction. W7 then guards the one assumption that
makes it work — that the writer stays sole.

*v3.4: "every active→inactive transition already passes" holds for UPDATE-form transitions only. A same-ID replace makes the transition by rewriting the row, and it never reaches `_invalidate_edge_row`. The sole writer remains necessary for W1; the transition invariant moves to §4c's view, at the journal every `edges` write passes.*

*(v2's reasoning, retained because it is what led here.)* **TWO store-layer
sites, corrected at the v2 refresh.** v1 said
`store.invalidate_edge` was a single choke point covering supersession via
`graph.py`. **Re-executed 2026-08-17, that is no longer true**: `graph.py` does
not call `invalidate_edge` at all; supersession invalidations now ride the
store's atomic plan (`apply_supersession_plan`'s `prior_invalidations`,
`sqlite.py:326/505/550`). The fix therefore lands at BOTH store sites:

* `invalidate_edge` — the `Memory.dispute()`/`correct()` and lifecycle path;
* `apply_supersession_plan` — the supersession path, inside the same transaction.

**This STRENGTHENS v1's argument rather than weakening it.** A fix in
`Memory.dispute()`/`correct()` would still miss supersession — the path an
attacker reaches — and now it would miss it via a *different* route than v1
described. The store layer is still not a stylistic preference; there are simply
two store-layer sites, and W2 is the check that proves the second one is covered.

**AND THE MECHANISM ALREADY SHIPS.** Both sites ALREADY execute
`DELETE FROM wiki` today (`sqlite.py:275` and `:605`) — gated on `0003`'s
refusal-contention condition (`_edge_in_refusal` / `touches_contention`). So this
spec does not introduce a mechanism, a code path, or a latency cost: **it
GENERALISES a shipped, reviewed drop from one trigger to the trust-reducing
set.** That is a materially smaller change than v1 proposed, and the reviewer
should hold it to that smaller claim.

**Which reasons drop the wiki — stated as a RETAIN allow-list, and the polarity
is load-bearing (v3).** The rule is **DROP BY DEFAULT**: *every* reason drops the
wiki EXCEPT the closed, enumerated retain set. It is deliberately NOT phrased as
"these three reasons drop", because that form is a deny-list — under it an
unrecognised reason retains, which is exactly the inversion internal R1 caught in
§2c. The same rule has two carriers, this section and that table; both now read
drop-by-default, and W5's registry constant is the third.

| retained (the CLOSED allow-list) | why retaining is safe |
|---|---|
| `lapsed` | time-based staleness, not a revoked trust decision; dropping curated breadth on every decay cycle pays a real cost for no trust gain |
| `decayed` | same |
| `absorbed_duplicate` | absorption is trust-preserving: the content stays backed by a live same-trust record, so the wiki serves nothing revoked (**W-Q1, ruled 2026-08-17; pinned by W8** — no longer "flagged rather than decided") |

Everything else drops — `disputed`, `corrected`, `superseded` today, an
unrecognised string at runtime, and **`revoked_source` when `0022` lands, which
needs no edit here because drop is the default** (that spec's §7b rider adds it
to W5's registry so the check passes; the seat is reserved, not defined here).
Adding a retaining reason is the change that requires an explicit spec decision —
which is the correct asymmetry.

**Where the exposure now IS, after `0020` (v2 refresh).** Principal-bearing
recall EXCLUDES the compiled wiki entirely (`0020` §4d/V5 — not filtered, not
compiled), so a scoped read cannot serve a stale wiki at all. The surviving
exposure is therefore precisely the UNSCOPED path — which is every call today,
since no host passes a principal yet, and remains the default path afterwards.
The finding is unchanged in force; it is narrower in description, and stating
that narrowing is what keeps the claim honest.

**Drop, do not recompile** — no LLM call, no latency, fails closed. Curated
breadth is lost until the next natural recompile; revoked content is never
asserted.

### ⚠️ Correction to the M8 finding: one clause is unreachable

The original text says the fix covers *"and any quarantine."* **There is no
post-ingest quarantine path.** Verified mechanically rather than recalled:

```
$ grep -rn "disclosure\s*=" --include=*.py src/veracium/
ingest.py:117   disclosure = _disclosure_for(author, relation, derived_from)
ingest.py:128   disclosure=disclosure, ...
```

`disclosure` is written in **exactly one place**, at ingest, and never lowered
afterwards. The clause describes an event that cannot occur, and it is **struck
rather than implemented** — building a handler for it would have produced dead
code that reads as coverage.

**Worth naming as a method note:** this is the third time in this spec that a
claim survived because it sounded right. It came from my own summary of
research's finding, not from research.

**v3.4 — the correction above was itself wrong, for the reason it gives: it was verified by a grep.** `disclosure\s*=` finds assignments. A same-ID `add_edge` or `add_episode` writes a whole record, and lowers `disclosure` without one. At veracium `86cb30e`, research's stage-1 probe stored `quarantined` and `use_only` that way. The text above is kept as written. The clause returns in transition form in §4c, as one class of the assertion-view rule, not as a separate quarantine handler.

**Checks.** `test_dispute_drops_the_wiki` (the reproducer becomes the fixture) ·
`test_third_party_supersession_drops_the_wiki` (the `graph.py` path, which is
why the fix is in the store) · `test_decay_does_not_drop_the_wiki` (the
exclusion is deliberate, so it is pinned).

### 4b. The body a call serves — W9 (v3.3)

**W1 drops the CACHE in the invalidating transaction. A body that is not in the
cache is out of its reach.** During a recall, `ensure_wiki` may compile a body
and return it for that call's own use, whether or not the publish succeeded:
0041's publish rule declines to publish over a moved store, and the unpublished
body is still served to the call that compiled it. A dropping invalidation
committed after the compile read its inputs, and before the call serves the
body, therefore left the body asserting a fact that the same call's edge read no
longer carried.

**Measured by research at veracium `0e1489e`** with a two-connection probe.
Four reasons were tried: `disputed`, `revoked_source`, `corrected` and
`superseded`.

| where the invalidation commits | `0e1489e` | `07df8f8` |
|---|---|---|
| at the call's challenge snapshot, the body compiled in the call | asserted, all four | (no bind) |
| during the compile | asserted, all four | asserted, all four (predates the bind) |
| a cached body, at the snapshot | withheld, all four (W1 evicted the row; the bind recomputes) | (no bind) |

**The rule.** A compiled body is served only if no fact it drew on has since
been invalidated with a reason that drops the wiki. Otherwise the body is
withheld: it is recomputed once (a compile reads only active edges, so the
recompute cannot draw the revoked fact), and if the recompute fails too, no
wiki is served for that call.

**The predicate is W1's, by construction.** ONE function decides "this reason
drops the wiki", both for the cache drop in `_invalidate_edge_row` and for the
served-body check, so the two cannot disagree. The retain set keeps the body as
it keeps the cache: a `lapsed`, `decayed` or `absorbed_duplicate` invalidation of
a drawn fact does not withhold it. That is W3 and W8, carried to the body; a
check on ANY reason would be the "drop on everything" erosion W3 exists to stop.

**Where.** At the one point every served body passes: `compile.bound_wiki`, which
binds the body recall serves to the call's snapshot (0047 §4d), through
its `_unbound_by` decision. At `0e1489e`, `bound_wiki` is `ensure_wiki`'s only
caller outside `compile.py`, and recall is `bound_wiki`'s only caller. A
principal-bearing call has no wiki (`0020`). So no other served path exists.

**Why at serve, not at write.** The writer can drop the cache because the
writer and the cache share a database. No write can reach a body held in
another call's memory; only the call holding it can check it, after its last
read of the store.

**Cost.** A recompute whenever a dropping invalidation of a drawn fact lands
between the compile's read and the serve, ordinary supersession at ingest
included. On a second failure the call serves no wiki and no notice. Curated
breadth is lost for that call, and a revoked fact is never asserted: §7's
trade, unchanged.

### 4c. A same-ID replacement is a transition — the assertion view (v3.4)

**What W1 and W9 missed.** Both key on an INVALIDATION: W1 at `_invalidate_edge_row`, and W9 by reading `invalidation_reason`. A same-ID `add_edge` changes a stored record by REPLACING it, and so passes neither. The evidence is the external reviewer's two witnesses (RII-R2-01) and research's stage-1 probes, both at veracium `86cb30e` with two real connections and the default threshold of eight:

| class of replacement | the cached body | a body compiled in the call (the write before the bind's snapshot) |
|---|---|---|
| the drawn edge retired under a dropping reason (`disputed`) | asserted | asserted: the retry read back, from the cache, the body the rejected compile had published |
| a challenged record replaced into the same value as a drawn one (0047's same-value twin rule) | asserted | asserted, the same way |
| the drawn edge's `disclosure` lowered to `quarantined` or `use_only` | asserted | asserted, beside the same call's UNVERIFIED rendering of it |
| the drawn edge's content replaced | asserted | asserted |
| the drawn edge replaced into a twin of a challenged record | not measured | asserted, while the same call's report counted it withheld |
| a drawn episode's `disclosure` lowered | asserted | asserted |

**The rule: one view, read at the write and at the bind.** `schema.assertion_view(record)` is the part of an Edge or an Episode that decides what a compiled body may assert from it. It is `None` for an absent record.

- **Edge:** `subject`, `relation`, `object`, `valid_from`, `ungrounded`, and the authority tuple (provenance's `disclosure`, `author_of_evidence`, `derived_from`, `record_kind` and `basis`). Its liveness is `invalidated_at is None or not wiki_drops_on(invalidation_reason)`. A retaining invalidation therefore leaves the view unchanged, so W3 and W8 hold by construction.
- **Episode:** `date`, `summary` and the same authority tuple. Its liveness is `retired_reason is None`, so any retirement changes the view. At `86cb30e` a retired episode is removed from the compile and from the bind, whatever its reason, and no ruling here retains one.
- **Every other field is a KEEP**, recorded with its reason in `schema.ASSERTION_VIEW_KEEPS`: the outcome counters, `note` (W8), `confidence` (W3), `needs_confirmation` (W-Q3), the grounding axis and the consolidation metadata. The view and the keeps partition the fields of Edge, Episode and Provenance, totally and disjointly. A new field fails the import until it is placed (W11).

The view follows the admission the compile applies: active, not quarantined, not use_only, not procedural, valid now, grounded. `quarantined` and `use_only` are not entries in it, because they derive from `relation` and the authority tuple. `Episode.use_only` also reads `third_party_influenced`, which derives from `author_of_evidence` and `derived_from`.

**At the write (W10).** A write that replaces or removes an existing record evicts the user's wiki in its own transaction when the prior view differs from the new one; an absent new row has the view `None`. A fresh insert never evicts: that stays W3's counter. The rule runs in one direction only. A write that moves a view must evict; a write that moves none may still evict for a cause of its own (a reply, a redaction, an erasure, the consolidation cutover).
- **Edges:** the check sits inside `_journal_edge_write`, after the 0044 lifetime hook and after the journal's kind and reason refusals, so a refused write has no eviction to apply. An unchanged row has already returned before the check, and an equal row has an equal view. Every `edges` writer already passes the journal with the persisted prior and the new row, so `add_edge`, the supersession plan, confirmation, import, invalidation, reinstatement and redaction inherit the check without a call of their own.
- **Episodes:** they have no journal. One helper, `SqliteStore._evict_wiki_on_view_change`, is called at each `episodes` write site.
- **The consolidation cutover** (`transition_consolidation_if_current` to `OUTPUTS_DURABLE`) writes no `episodes` row. It flips, through the op state, which representation every ordinary read sees: the claimed inputs are hidden and the outputs revealed. The inputs are deleted later, by a separate call. Without an eviction of its own, a cached body drawn on the inputs was served in that window, beside the outputs. The cutover therefore evicts in its own transaction, beside its X14 bump. That costs nothing new, because the inputs' deletion evicts anyway.

**Why not "any change to the stored row".** Research measured both rules at `86cb30e`, as models wrapped around `_upsert_edge_row`. Evicting on any stored change turned W8's pin red, because absorption rewrites the absorbed prior's `note`. It also evicted on every `record_outcome`, every decay step and every lifecycle confirmation flag. A model of the view rule kept all 329 wiki, supersession, lifecycle and outcome tests in that run green. The model evicted on subject, relation, object, disclosure and valid_from, and on retirement under a dropping reason. The full authority tuple adds fields that the upsert already refuses to change (`record_kind`, `basis`, `ungrounded`), plus `author_of_evidence` and `derived_from`. W10's inventory measures the view as built.

**At the bind (W12, extending W9).** `_unbound_by` re-reads the CURRENT row of every record a compiled body drew on, and decides in this order:

1. A drawn fact that the call's snapshot withholds → the disputed notice.
2. A drawn record that is redacted → the redacted notice (0041 round 10's, unchanged).
3. A drawn record that is absent, or whose current view differs from the drawn one → no wiki and no notice. The current episodes are the ordinary read (0010 X9's visibility) with retired rows included, so a hidden consolidation input reads as absent, while a retirement is compared by its view.

**Why three steps suffice.** Past step 3, every drawn record's current view equals its drawn one. The snapshot's twin match (`ChallengeSnapshot._withholders`, `_is_twin`) reads only an edge's `id`, `subject`, `relation`, `object` and `provenance.procedural`. All of these are view fields except `id`, which is the key the current row is looked up by. So step 1 has already answered for the current rows, and a fourth test of the current row could never fire. The reviewer's twin, a CHALLENGED record moving onto a drawn one's value, is caught at step 1, because the snapshot is read after the move. Drawn-becomes-twin moves the drawn record's `object`, so it is caught at step 3. The premise is a dependency on another module, and `test_the_snapshot_reads_only_view_fields` holds it: changing any KEEP field alone leaves `withheld` and `challenge_clear` unchanged, for a drawn record that twins a challenged one, is the challenged one, or is unrelated. *(Research's stage-1 read asked for that fourth test; the mutation pre-check showed it equivalent.)*

The order keeps 0041's specified notice. A redaction changes the view too, so putting step 3 first would replace the redacted notice. That only shows when both attempts fail: after a single redaction, the recompute binds cleanly in either order.

**The retry (W13).** A compiled body that fails its bind is recomputed once. Before the recompute, `bound_wiki` removes the cache row that its compile published, through `discard_wiki`. That is a delete conditional on the row still being the published one, so it cannot drop a newer valid row. Without it, the recompute read the rejected body back from the cache. **Once W10 is complete, every cause of a failed bind also evicts at its own write, so W13 is defence in depth.** Its check therefore disables W10's eviction, to show that W13 holds on its own.

**Cost.** One recompile whenever a same-ID write changes a record's view. A write outside the view (counters, notes, confidence) costs nothing new.

---

## 5. Regime analysis

| regime | behaviour |
|---|---|
| library default (`wiki_recompile_after_writes = 8`) | breadth returns within 8 writes of the drop; the window where a revoked fact could have been asserted closes immediately |
| CLI path (`10**9` once a wiki exists) | the drop is effectively permanent until something else compiles — the honest cost, and W-Q2's subject |
| `selfcheck` (`= 1`) | recompiles on the next write; the drop is invisible |
| a store with NO wiki | the drop is a no-op; no path changes |
| principal-bearing recall (`0020`) | the wiki is excluded from the response ENTIRELY, so this regime is unaffected by the cache's state — the exposure is the unscoped regime |
| staleness (`lapsed`/`decayed`) | NO drop, deliberately — time-based staleness is not a revoked trust decision, and paying curated breadth on every decay cycle buys no trust |
| `absorbed_duplicate` | **NO drop — RULED, not flagged (W-Q1 resolved 2026-08-17; pinned by W8).** Absorption is trust-preserving by construction: the content stays backed by a live same-trust record, so the wiki serves nothing revoked. **This cell read "flagged, not decided" until external round 1 (F5) found it — the FOURTH carrier of a ruling whose other three had been updated, in the document whose own v3.1 lesson was that a finding is not closed until every carrier is swept** |
| post-`0022` `revoked_source` | drops, by the rider this spec reserves |
| a dropping invalidation of a fact a recall's body drew on, committed during the compile or before the serve (v3.3) | the body is withheld: one recompute, then no wiki for that call. A retaining reason keeps the body (W9) |
| a same-ID replacement that changes a record's assertion view (v3.4) | the wiki is evicted at the write. A body compiled in the call fails its bind, is recomputed once, and then no wiki is served (W10, W12, W13) |
| a same-ID replacement that changes only KEEP fields (`record_outcome`, absorption's `note`, decay's `confidence`) | NO drop — the view is unchanged, so W3 and W8 carry to the replace path |

## 6. Invariants and executable checks — REQUIRED, blocking

| invariant | executable check | where |
|---|---|---|
| **W1** a revoking invalidation empties the wiki cache | `test_dispute_drops_the_wiki` — the measured reproducer becomes the fixture | CI |
| **W2** the drop covers the **supersession** path, not just the `Memory` verbs — and post-refresh that path is `apply_supersession_plan`'s `prior_invalidations`, NOT `graph.py` | `test_third_party_supersession_drops_the_wiki` (the second store site) | CI |
| **W3** staleness does **not** drop it | `test_decay_does_not_drop_the_wiki` — pins a deliberate exclusion so it cannot erode into "drop on everything" | CI |
| **W4** no LLM call on the drop path | `test_wiki_drop_makes_no_llm_call` — a `Complete` that raises if invoked | CI |
| **W5** the reason set is CLOSED and REGISTERED: every reason any producer can pass is dispositioned drop/retain, and a NEW reason fails the check until its spec dispositions it. **The registry is a CODE CONSTANT** (internal minor: v2 pointed at `schema.py:249`'s comment, and a comment cannot fail a check). **Two constants, not one, and the split carries the §4 polarity into the code: `WIKI_RETAINING_REASONS` is what the RUNTIME consults (membership → retain, everything else → drop); `DISPOSITIONED_REASONS` is the process record W5 diffs against. A reason omitted from BOTH still drops** — the registry can only fail the build, never widen what is served | `test_invalidation_reason_registry_is_total` — enumerate the reasons reachable at every producer (the §2c PRODUCERS row) and diff against `DISPOSITIONED_REASONS`; an un-dispositioned reason FAILS rather than defaulting. Plus `test_runtime_consults_only_the_retain_set` — an invented reason string drops, proving the runtime is not branching on a drop-list | CI |
| **W7** the transition invariant is STRUCTURAL: `_invalidate_edge_row` remains the SOLE writer of `active=0`, so every active→inactive transition inherits the drop (internal R2 — this is what makes the born-state producers safe, and it is enforced rather than grepped once) | `test_sole_active_zero_writer` — an AST sweep of `src/veracium/` asserting exactly one `SET active=0` writer and that it is `_invalidate_edge_row`; a second writer FAILS the build. **v3.4: the sweep stays, and so does its claim about `SET active=0`. The transition invariant it was said to secure is W10's.** A same-ID `INSERT OR REPLACE` makes the transition without matching the sweep (§2c). Beside it, in `tests/test_rii_r2_01_writer_inventory.py`, two checks in the same shape. `test_every_edges_writer_passes_the_journal`: every `edges` writer passes `_journal_edge_write`. `test_every_episodes_writer_calls_the_eviction`: every `INSERT`, `REPLACE`, `UPDATE` or `DELETE` on `episodes` in `src/veracium/store/sqlite.py` sits in a function that calls `_evict_wiki_on_view_change`, except `forget_user` and `_redact_in_txn`, which evict unconditionally | CI |
| **W8** the `absorbed_duplicate` exclusion is PINNED (W-Q1, ruled by research 2026-08-17: absorption is trust-preserving by construction and the content stays backed by a live same-trust record, so the exclusion shelters nothing revoked) | `test_absorption_does_not_drop_the_wiki` — the W3 pattern, so a deliberate exclusion cannot erode into "drop on everything" | CI |
| **W6** the generalisation does not REGRESS `0003`'s shipped refusal-contention drop — that condition still drops, in both sites | `test_refusal_contention_still_drops_the_wiki` (the shipped behaviour this spec widens, pinned so widening cannot silently replace it) | CI |
| **W9** (v3.3) a body a recall serves never asserts a fact invalidated with a dropping reason after the compile read it; a retaining reason keeps the body; the decision is W1's own (§4b) | cells added at implementation to `tests/test_0047_rii01_wiki_bind.py`, the RII-01 bind's file. On the compiled path, every `DISPOSITIONED_REASONS` key but `redacted` (which only a redaction writes, 0041 §11.2; its window is the redaction cell's, and `test_w9_every_dispositioned_reason_but_redacted_is_an_invalidation_reason` holds the exclusion to that one key) is invalidated at the call's snapshot and during the compile: a dropping reason withholds, a retaining one keeps. The cached path is the control. **Demonstrated RED** against three mutants, each named with the cell that kills it: (a) the clause removed, killed by `test_w9_a_revoking_invalidation_withholds_the_body_and_a_retaining_one_keeps_it`[<dropping reason>-compiled_at_snapshot / -compiled_during_compile] (8 cells); (b) the clause applied on ANY invalidation (W3's erosion), killed by the same test's [<retaining reason>-compiled_*] (6 cells); (c) the store's eviction leaves the shared rule (`if True:` at `_invalidate_edge_row`), killed by its [<retaining reason>-cached] (3 cells). All by assertion; controls pass | CI |
| **W10** (v3.4) a write that changes a stored edge's or episode's assertion view evicts the user's wiki in its own transaction. A write that leaves the view unchanged is never made to evict by this rule: it may evict only for a cause of its own (a reply, a redaction, an erasure, the consolidation cutover) | the behavioural inventory in `tests/test_rii_r2_01_writer_inventory.py`. `test_every_mutation_class_evicts_iff_it_moves_a_view` runs each mutation class on a real store with a published wiki row, and its oracle reads the persisted rows. The classes are: a fresh id or the same id; each view field; retirement under each disposition (drop and retain); a challenged record's same-value key; a drawn record becoming a twin; and the consolidation cutover as its own cell. `test_every_public_store_method_is_classed` classes every public store method, found by introspection of the public surface, as a READ or as a WRITER that names its cells or the test that pins it. An unclassified method FAILS. The KEEP controls (the outcome counters, `note`, `confidence`, `needs_confirmation`) must leave the row in place (`test_a_retaining_same_id_write_keeps_the_cached_body`). **Demonstrated RED** against: the eviction removed; each view field dropped from the view, one mutant per field, each killed by its own class; and the over-broad "any stored change" mutant, killed by W8's pin and the `record_outcome` control | CI |
| **W11** (v3.4) the view and `schema.ASSERTION_VIEW_KEEPS` partition the fields of Edge, Episode and Provenance, totally and disjointly | an import-time check (the AS_OF_DISPOSITION shape). In `tests/test_rii_r2_01_writer_inventory.py`: `test_the_mutation_tables_are_total`, `test_a_field_changes_the_view_iff_the_view_reads_it`, `test_a_provenance_field_changes_the_view_iff_the_view_reads_it`, `test_an_edge_retirement_moves_the_view_by_wiki_drops_on` and `test_any_episode_retirement_moves_the_view` | CI |
| **W12** (v3.4, extending W9) the bind reads the CURRENT rows of the records a compiled body drew on, in §4c's order | in `tests/test_rii_r2_01_writer_inventory.py`: `test_reviewer_twin_a_challenged_record_moving_its_twin_key`, `test_a_same_id_replacement_of_a_drawn_edge`, `test_the_drawn_edge_becoming_a_twin_of_a_challenged_record`, `test_an_episode_demoted_under_its_id` and `test_the_snapshot_reads_only_view_fields` (§4c's three-step premise). Between them they cover the reviewer's two families (sequential and interleaved, at the default threshold; the twin witness without its row-survives precondition); demotion to `quarantined` and to `use_only`; a content change; drawn-becomes-twin; an episode demotion; and `test_a_redaction_in_both_windows_ends_as_the_redacted_notice` (the drawn edge redacted before the first snapshot and the drawn episode before the second: the call serves the redacted notice and neither record). **Demonstrated RED** against the bind comparing presence only, not the drawn records' views (killed by drawn-becomes-twin); the view check placed before the redaction check (killed by the both-windows cell); and the snapshot's twin match reading a KEEP field (killed by `test_the_snapshot_reads_only_view_fields`) | CI |
| **W13** (v3.4) a compiled body that fails its bind cannot come back through the cache on the retry | `tests/test_rii_r2_01_writer_inventory.py`, `test_d2_a_rejected_compile_is_not_served_back_from_its_own_row`, with W10's eviction disabled at its site on both stores: red without `discard_wiki`, green with it. A newer row published meanwhile survives the discard, at store level: `test_the_discard_never_drops_a_newer_row` | CI |

**W2 is the one that matters** and is the reason the fix sits in the store.
A fix in `Memory.dispute()`/`correct()` passes W1 and W3 and **fails W2
silently** — the tests would be green and the attacker path open.

---

## 7. Failure modes and reversibility

**Failure mode is loss of curated breadth**, never assertion of revoked content.
The wiki is an optimisation; recall works without it. Reversible by reverting —
nothing is written that a later compile cannot rebuild.

**The cost is real and bounded:** on the library default
(`wiki_recompile_after_writes = 8`) breadth returns within 8 writes. On the CLI
path it does not, because `cli.py:198` sets `10**9` once a wiki exists — so a
CLI operator loses the wiki until something else triggers a compile. **That is
the correct trade** and it is the same asymmetry that governs T1: missing
breadth is inspectable, asserting a revoked fact is not.

---

## 8. Claims and limits

**Claim:** a trust-reducing event takes effect on every surface the model reads,
not only on the edge.

**Limit, stated because it is the honest one:** this makes the wiki *fail
closed*, it does not make it *incremental*. A large store loses its whole
curated view because one fact was disputed. Incremental invalidation is the
better answer and is deliberately **not** in scope — it needs a dependency map
from wiki text back to edges, which does not exist.

**Limits, v3.3 (W9).** W9 reads the INVALIDATION of facts a body drew on. An
episode is never invalidated; its removal is a redaction or an erasure, which
0041 and 0047's bind govern. *(v3.4: an episode is also retired, through `retired_reason`, and replaced under its own id. Both are view changes, §4c.)* A second failure serves no wiki and no notice: a
notice there would be a new text surface, and it is not in this amendment.

**Limits, v3.4.** The view describes the wiki's admission; it is not a dependency map. A write that changes only which value a contested group keeps (0003 §4c-ii), or that changes only a KEEP field, leaves the body to W3's staleness. `needs_confirmation` is a KEEP. Whether a fact flagged for confirmation should leave the assertable wiki is W-Q3, and it is not decided here.

---

## 9. Brief for the external reviewer

The seam we are least certain of: **the reason set's closure**. The fix's whole
safety argument is "these reasons revoke, those merely age", and that partition
is defended by W5's registry rather than by anything structural — a future spec
that adds an invalidation reason and forgets to disposition it gets a FAILING
check, not a silent retention, but the check is the only thing standing there.
Attack that: is there a producer of invalidation reasons the §2c PRODUCERS row
misses? The `0022` sweep will add one, which is the first real test of the
mechanism.

v3.3's seam: **W9 binds the body a call serves, not only the cache.** The cache
drop (W1) and the served-body check (W9) are two enforcement points of one
decision. They share one function, and mutant (c) is the check that they stay
one. Attack that: is there a path that serves a compiled body without passing
`bound_wiki`?

v3.4's seam: **the view's membership.** The rule is only as good as `assertion_view` and its KEEPS. Attack that in two places. Is there a field outside the view whose change alters what a compiled body may assert? Is there a write to `edges` or `episodes` that passes neither `_journal_edge_write` nor the episode helper?

Second seam: this spec makes the wiki fail closed but NOT incremental (§8's
stated limit). A large store loses its whole curated view because one fact was
disputed. We think that trade is correct and bounded; if you think the breadth
cost is understated, that is worth hearing before implementation rather than
after.

## 10. Open questions

| # | question | class | who | by when |
|---|---|---|---|---|
| **W-Q1** | Should `absorbed_duplicate` drop the wiki? | **RESOLVED 2026-08-17 (research, internal round 1): NO.** Absorption is trust-preserving by construction — the content stays backed by a live same-trust record — so the exclusion shelters nothing revoked. **The `0022` composition is closed**: the revocation sweep reaches absorbed contributors through the LEDGER, and a sole-basis survivor's retirement carries reason `revoked_source`, which drops the wiki through the seat this spec reserves. Pinned by W8. | `resolved` | research | done |
| **W-Q2** | Should the CLI's `10**9` recompile threshold be revisited, given it makes the breadth loss unbounded there? Out of scope for the fix; in scope for whether the trade is acceptable. | `deferred` | dev | own round |
| **W-Q3** | Should `needs_confirmation` keep a fact out of the compiled wiki? It is set by lifecycle CONFIRM and by a CHALLENGED outcome, which is not a 0047 challenge. It is a KEEP at v3.4. | `deferred` | owner | own round |

## Review closure

*(PROCESS §4a — one row per review finding, with openable evidence. 0004's
review closed at external round 2 (approved, frozen on W1–W8) and it was never
a candidate again through the nineteen further rounds its dependents ran. This
ledger is hand-written — 0004 predates the generated-ledger machinery its
dependents use — and every evidence command runs from the repo root. The spec
is accepted, NOT yet implemented: W1–W8's named tests are the §6 implementation
obligations, so the evidence below pins the FOLDS in this document, and
deliberately cites no test that does not exist yet.)*

| finding | round | summary | closed in | evidence |
|---|---|---|---|---|
| **R1** | internal 1 | the §2c unrecognised-reason cell was INVERTED — v2 retained the wiki on an unknown reason, calling it "fail-OPEN on breadth, never on assertion", which is backwards for a spec whose thesis is failing closed | §2c: an unknown reason DROPS at runtime, then W5's registry fails the build until the reason is dispositioned; the inversion is quoted in the corrected cell so it cannot be re-argued | `grep -n 'v2 had this INVERTED' specs/0004-derived-views-and-revocation.md` |
| **R2** | internal 1 | `invalidation_reason` is settable and `add_edge` accepts an Edge already carrying one, so the constructor and the FORMAT-7 import round-trip produced reason-bearing records passing NEITHER drop site — the spec's own §9 attack, landed | the fix RELOCATED into the sole `active=0` writer (`_invalidate_edge_row`), so every invalidation path inherits the drop by construction; W7 makes the sole-writer property an AST sweep, not a one-time grep | `grep -c '_invalidate_edge_row' specs/0004-derived-views-and-revocation.md  # 4 carriers, all naming the SAME sole writer` |
| **F5** | external 1 | the §5 regime table still read "flagged, not decided (W-Q1)" while §4, W8 and the question table carried the RESOLVED ruling — the FOURTH carrier of a decision whose other three were swept, in the document whose own v3.1 lesson was that a finding is not closed until every carrier is swept | v3.2: all four carriers aligned on the W-Q1 ruling (absorption is trust-preserving; the exclusion shelters nothing revoked), and the miss is recorded IN the corrected cell | `grep -c 'W-Q1' specs/0004-derived-views-and-revocation.md  # every carrier now cites the ruling` |
| **D10** | R-II round 2 (research's stage-1 read of the round-2 package design, 2026-10-22) | a body compiled during a recall was served after a dropping invalidation of a fact it drew on, committed at the call's snapshot or during the compile (the latter predates the bind). W1 drops the cache and cannot reach a body held by the call | v3.3: §4b and W9. The served body is checked with W1's own predicate at `bound_wiki`; one recompute, then no wiki. The owner ruled "fix now" (ledger 417490b) | `grep -n 'W9' specs/0004-derived-views-and-revocation.md` |
| **RII-R2-01** | R-II round 2 (external, P1, 2026-10-22) | a same-ID `add_edge` that replaced an existing edge, retiring it or moving a challenged record's same-value key, never evicted the wiki. The retry re-entered through the cache that the rejected compile had published. §2c's born-state argument and W7's rationale were false for that path. Research's stage-1 read added the disclosure demotion (§4's struck clause rested on a grep), the content change, the drawn-becomes-twin case, episodes and the consolidation cutover | v3.4: §4c and W10–W13. W7 is annotated, and §2, §2c, §2c-ii and §4 are annotated in place | `grep -c 'v3.4' specs/0004-derived-views-and-revocation.md` |
| **artifact 1** | external 2 | reviews.py carried 0004's round-1 SENT rows and no verdict — the source of truth recorded that a package went out and never that it came back | the round-1 verdict row was added then; the ROUND-2 verdict row repeated the same omission and was added at acceptance (2026-08-20), labelled as late rather than backdated | `python3 -c "import sys; sys.path.insert(0,'specs'); import reviews; rows=[r for r in reviews.REVIEWS if r['spec']=='0004' and not r['verdict'].startswith('SENT')]; assert {r['round'] for r in rows} >= {1,2,21}, rows; print('0004 verdict rows:', sorted(r['round'] for r in rows))"` |
