# Feature spec: exercised guarantees — measuring whether what we specify is what runs

Spec-Status: accepted

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-61), each adoption at rest and re-read from the file, dated per entry: v3.1 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 28068200aa6f90fa); v4 2026-09-18 from the same file (sha16 0fd0af01bfb56a39); v5 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 f8cf6f68e0016625); v6 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 ba262106068d3efc); v7 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 ccf0715041f3148a); v8.1 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 b94d814d20b96d2c); v9.2 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 a230ae09793790be) — ACCEPTED at the design level, the flip on the owner's word |
| **Version** | **v9.2 — THE CITATION FIXED, AND THEN FIXED AGAIN IN THE CELL THAT ANNOUNCED IT.** 🔴 **A Part B sentence cited the gate by its MODULE name in the backticked form the citation gate reads as a TEST NODE, so the accepted spec cited a test that does not exist.** *It sat there from v6 and was invisible while the spec was a draft: **drafts are exempt from that gate, and acceptance is where a cited name stops being a note and becomes a claim.** The suite failed on the STATUS, not on any change to the text.* It now names the node that does the checking, `tests/test_spec_gate.py::test_no_spec_names_a_module_or_script_that_does_not_exist`. 🔴 **Then v9.1's own Version cell REPEATED THE OFFENDING TOKEN while explaining it, and the derivation caught that too — the failure class named in a carrier the gate scans, one level up, inside the correction.** *Both passes were derived rather than taken: every backticked `test_…` token in both candidates, extracted with the gate's own pattern, against the tree's defined test names — one hit in 0042, none in 0043, and zero after this cell.* **No other change; v9's cell follows.** **v9 — THE ACCEPTANCE FOLD.** 🏁 **ACCEPTED AT THE DESIGN LEVEL at external round 5, 2026-09-18:** *“both specifications are accepted at the design level and may proceed to implementation”* — the accepted artifact is the ROUND-5 PACKAGE — sha256 `791c1089776d9f49332483f8ff88b25794dec795ee8a7cf8eb33b441eaa1747a` @ pin `a9d3622d6252a19387b2ecb66a665f101825fb36`, CI `35382261953`, fresh-clone capture at the pin **3339 passed, 11 skipped, 11 xfailed in 750.36s** — which the reviewer holds; **no seal follows this fold.** 🔴 **FROZEN INVARIANT SURFACE, in the reviewer's words: INV-1, INV-2, INV-2b–2d, INV-7, INV-8.** 🔴 **THE RULE FORWARD: a change to a FROZEN invariant is a NEW EXTERNAL ROUND, not a version bump.** Everything else moves under the standing rule this arc paid five rounds to state — **the correction at the sentence an implementer copies, the record of what it replaced in §11.** The closure ledger under *Review closure* carries one row per finding with evidence a reader can RUN or OPEN and **derives its own counts; this cell does not restate them.** **WHAT THE FIVE ROUNDS DID TO THIS SPEC: `INSTALLED` was defined FOUR TIMES and the first three were PROXIES that passed their own checks** — the declaration plus runtime reports *(satisfied by code containing no instrumentation)*, a scan for `declare_site` calls *(both fixture decisions executed, reconciliation passed, the counters never moved)*, and the binding scanned over the MODULE *(`.consult` in one function and `.fire` in another read as bound)*. **Each was checkable; each was checkable against something other than what it claimed.** *The current definition — one lexical function body, unshadowed name, counters asserted as DELTAS across the decision — is the first that cannot be satisfied without the guarantee being measured, and the three superseded forms are kept in §11 as mutants their replacement must fail on.* **CREDITS.** The external reviewer reproduced every claim at the pin and returned the line four times; the three defects he found at acceptance had all passed our own controls. Dev (`veracium-2b`) built every evidence leg and its mutants, and caught the §9 briefs naming returned rounds — a carrier nothing re-derived. Research (`veracium-research-48`) authored the specs and the design answers and ran the second seal leg. The owner ruled the split, ruled `UNRESOLVED` a terminal outcome, and dispatched every round. *(The `Spec-Status: draft → accepted` flip is the adoption's declared delta, on the owner's word; this candidate leaves the line as it stands.)* Prior: v8.1 · v8 · v7 · v6 · v5 · v4 · v3.1 · v3 · v2 · v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — §4's counters sit in `gate.py`, `graph.py`, `lifecycle.py`, `ingest.py`, `schema.py`, all guarded |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 0042. 🔴 **CORRECTED v4 (round-1 carrier finding C2, research's): v3.1 said “0040 is free but was VACATED”. IT IS NOT FREE — `specs/ALLOCATION.md` records it under the column `spent on`, consumed by the WITHDRAWN procedural-text proposal.** Vacated and free are different states and this cell asserted the wrong one against the registry. *(Found by the external reviewer. Research had swept 63 `0040` references across 21 files the same night and classified THIS line as correct — by asking whether the file explains the renumbering rather than whether the sentence agrees with the registry. A category check where a content check was owed.)* **0042 is this spec; the refusal harness takes its own number from `allocation.py --next` at adoption.** |

---

> **Implementation note, tranche 2 (2026-09-19; the owner's word "implement all 3"; no
> frozen invariant touched — INV-1, INV-2, INV-2b–2d, INV-7, INV-8 stand as accepted).** Twenty-eight
> enforcement points in gate, schema, compile, grounding, authority and asof are now expressed
> through declared sites (28 ids; `asof.adapter.adapt.refuse` binds thirteen refusals of one
> function to one id, as §4a allows for one guarantee enforced at several branches). Two
> refinements the accepted text did not foresee, because no product site existed when it was
> written: **(i) a predicate site declares its declining value** — `declare_site(id,
> declines=False)` (or `True`, or a callable over the returned tuple) — and returns BOTH verdicts
> through `fire()`, so the return statement keeps the shape Part A-4's discovery finds and `fired`
> moves only on the decline (an exception, `None` or `False` decline by default; a filter whose loss
> is not in its return value passes `declined=` explicitly); **(ii) discovery looks through the
> wrapper** — `NAME.fire(x, …)` is the decision `x`, since `fire` returns its first argument
> unchanged — so an instrumented site keeps its kind at its statement and does not vanish from the
> inventory it was reviewed in (the inventory grew 745 → 748 by the census module's own three
> candidates, none an enforcement point). The runtime leg (`tests/test_0042_sites.py`) executes one
> declining decision at every declared id and asserts Δconsulted == 1 and Δfired == 1; the two
> as-of recall sites are inner functions driven through a recall with one candidate. Cost at the
> shipped default (census OFF), measured on the rebuilt ten-conversation store over 180 timed
> recalls: one adjacent pair read median 152.1 ms → 158.9 ms (+4.5 %) with the plain idiom at
> every site (re-measured alternating twice against the pre-tranche tree: +1.6 % and +6.1 % —
> the cost is real, both positive; its magnitude is not established at two alternations), after
> the site became its own context manager (1.00 µs → 0.20 µs per
> consult+fire disabled). Measured where it
> came from: 12,527 decisions per recall, 12,385 of them the four `Edge` predicates (`quarantined`
> 4,314, `use_only` 2,732, `assertable` 2,727, `valid_now` 2,612). **The owner's word (question
> form, 2026-09-19): a bypass at those four.** The decision is computed ONCE (`q = <expr>`), the
> census machinery runs only when the census is enabled, and both returns are discovered under
> the one id (discovery applies FILTER_RETURN's name rule to Boolean names). Re-measured
> ALTERNATING the pre-tranche tree and this one, twice, 180 timed recalls each: 149.9 / 151.1 ms
> against 150.5 / 147.6 ms — inside run-to-run noise; the figure is from the alternating run only.
> **Three things stated, not implied.** (a) The trade against §4A-2's letter: `consulted` is
> counted AFTER the decision is computed (so the predicate is written once, never twice), which
> honours the clause's purpose — counted at the site, never at a consumer — and not its letter; the
> one observable consequence is that a predicate that RAISES is invisible to the census at these
> four sites (`test_a_raising_predicate_raises_identically_on_both_paths_and_is_invisible_to_the_
> census` executes exactly that, and asserts `Site.__exit__` never swallows the raise). (b) The
> price research named: the shipped default is now a FOURTH code path at these sites, so the INV-7
> harness, when it lands, gains a fourth arm — instrumented-but-bypassed — compared with the
> healthy arm on decision OUTPUTS (a bypassed arm emits no trace), its sharpest case a predicate
> that raises; `test_the_enabled_and_bypassed_paths_agree_on_every_verdict` is that arm in
> miniature today. (c) A third option, considered and not taken: a per-recall count at the four
> would have removed the cost without a bypass but made the counter values two units across one
> report. **Tranche 3 (the same day):** forty more ids — graph (13), proactive (2), ingest (3),
> procedures (1), the procedural gate (2), the registry (2), the MCP closed set (2), the Memory
> surface (11), diagnostics (1), telemetry (5) — 68 bound in all, by a generic AST-positioned
> instrumenter: a return or raise keeps its ORIGINAL value inside `fire(...)` (the inventory stays
> at 752), `consult()` brackets the enclosing `if` for a refusal or the whole body for a predicate
> with several exits. Two review corrections: `_src_revoked` and `_is_variant` each bind ONE id —
> their `return False` exits are the non-declining branch of one decision (`declines=True`), not
> enforcement points of their own; a structural sweep of the whole review for that shape (a
> function carrying more than one id on non-raising exits) found seven functions, every one a set
> of DISTINCT declining reasons on hand-reading — no further instance. The DECLARED/INSTALLED half
> of the reconciliation holds per tranche; the DISCOVERED/REVIEWED half lands with the review file
> in the last tranche.

## 1. Problem and motivation

**We assert guarantees we have never measured being exercised.** Two independent
competitors found the same defect in their own systems by measuring, and neither
found it by testing:

| | |
|---|---|
| `tigerless-labs/agent-memory` | *"Across **3,744 memories** written in a 120-episode run, the supersede edge count was **ZERO** — the mechanism the whole time-travel guarantee rests on was **reachable in principle and unused in practice**."* |
| `inspeximus` | *"the field was measured at **0.0000% coverage across 111,264 records** — every store this deployment runs — which made `strict_corroboration` **unable to fire anywhere**… nothing could reach it, **this server included, and we dogfood through this server**."* |

**Both had passing tests.** The tests construct the conditions the guarantee
needs; production never presented them.

> **Coverage measures whether a TEST reached a line. This spec measures whether
> PRODUCTION reaches the GUARANTEE.** They are different questions and we have
> only ever answered the first.

**And this project has been finding the same class by hand, one instance at a
time, for a week** — a refusal that could never fire because a test above it
rewrote its input; a reconciliation bound that could not see a section added
after it was written; two controls that reported PASS without executing; a
status check that printed `ok` when its lookup broke. **Every one was found by a
person noticing. This is the systematic version.**

### What this spec claims ON ITS OWN — and what it no longer claims

🔴 **v4 REPLACES v3.1's “Why the two halves are ONE spec”, which rested on a
dependency the round-1 reviewer removed.** That section argued *“Part B cannot
produce a rate without Part A's counter”*. The reviewer ruled otherwise, and the
ruling is accepted here verbatim:

> *“A refusal rate needs a defined denominator, but a controlled question harness
> can count attempts and outcomes itself. Part A adds valuable evidence about
> internal decisions; Part B does not inherently depend on process-wide counters
> to calculate a rate.”*

**So the harness is now its own spec, and this one keeps only the census.** The
honest consequence is stated rather than absorbed: **0042's original value
proposition was partly that it supplied another spec's denominator, and it no
longer does.** What remains is narrower and stands alone:

> **Does what we specify actually RUN?** For every enforcement point this project
> declares, is it INSTALLED, is it EXERCISED in production, and can we tell those
> two apart from a deployment that never switched the census on? **No rate, no
> onward dependency, no second arm.**

**That claim needs no harness and answers the competitors' finding directly** —
`tigerless-labs` learned its supersede count was zero by counting, and this is
the counting. **The refusal harness cites this spec for evidence about internal
decisions; it does not draw its denominator from it.**

## 2. Field contracts touched

**No stored field changes.** The census adds a process-local counter keyed by a
declared enforcement-point id, and nothing else. *(v3.1 also described Part B's
surface here; Part B is now its own spec and describes its own.)*

| contract | touched how |
|---|---|
| `Memory.recall` / `gate` decision path | **observation only** — a counter increments beside the decision; the decision is unchanged |
| receipts (0027 `policy_receipt`) | **read** — the receipt already records what a lane did; Part A does not extend it in v1 (see §10 Q3) |
| 🔴 **the enforcement-point DECLARATION** | **CREATED BY THIS SPEC — it does not exist.** v2 said the expected set was *"derived from the invariant registry"*. **There is no such registry.** `INV-` appears **0 times in `src/`**, and every occurrence under `specs/` is **0041's own** — 117 in the spec, 48 across `reviews.py`, `closure_findings.py` and `specs/evidence/0041/` — **no other spec uses the prefix**; the only registries in code are 0037's relations, 0028's successors, 0020's scope policy and the active-operation table. **And it cannot be derived from the existing §6 tables either.** The id sits inside a prose cell, not a column, and the vocabulary has **TWO FAMILIES**: digit-suffixed (`M1`, `V12`, `INV-11`) and **named** (`V-CENSUS`, `V-NO-INLINE-SEND`). Counting distinct `(spec, id)` pairs: **641 — 464 digit-bearing in 35 shapes, and 177 named.** 🔴 **A grammar that requires a digit DROPS the 177 named ids (28% of the vocabulary); one that does not degenerates to counting names.** **There is no fixed grammar over an id column because there is no id column.**

> **The definition is given EXECUTABLE, not in prose, and that is deliberate.** The two seats derived this independently and disagreed across three rounds — 207, then 36, then 651 — **and the disagreement closed only when both ran the same pattern, never when we compared conclusions, which agreed from the first message.** A prose definition (*"leading bold token starting with a capital"*) admits `**The live instrument**`, a sentence-case prose cell, as an id; the second seat implemented the stated words literally and got it.
>
> ```python
> ID = re.compile(r"^\s*\*\*([A-Z][A-Za-z0-9\-]*)\*\*")   # first cell of each `|` row,
> #   between the heading "## 6." and the next "## ".  Count DISTINCT (spec, id) pairs.
> ```
>
> **Re-derived by the second seat to within one on every family** (642 / 465 / 177 / 36). *The residual is one edge row; it is not a definitional gap.* **That three rounds were needed to agree what an id IS — in a project where every spec carries a §6 table of them — is itself the argument for §4a's declaration.** So the declaration is part of the work, not a dependency of it (§4a) |

## 2c. Untrusted inputs — REQUIRED, blocking

| input | source | treatment |
|---|---|---|
| ~~**examiner questions**~~ — **MOVED to the harness spec** | a human or model that has NOT read the implementation | **data, never instructions.** Questions are asked through the ordinary public API; no question text reaches a prompt with authority |
| ~~**the fixture store's records**~~ — **MOVED to the harness spec** | includes deliberately poisoned and deliberately quarantined rows | **the material under test.** A poisoned row must be able to reach recall — excluding it in the fixture would measure the fixture |
| **enforcement-point ids** (Part A) | declared in source, read by the census | **code-supplied, not caller-supplied.** An id that is not in the derived registry is a REFUSAL, not a new row |

### 2c-ii. Assertions about reach — REQUIRED

**A census count is a statement about ONE deployment's runs, never about the
mechanism in general.** A zero from our fixture corpus says *"our corpus never
presented the condition"*, not *"this guard cannot fire"*. **The two must never
be collapsed** — the second requires a reachability argument over the code, which
this spec does not attempt.

## 3. Trust-class matrix — REQUIRED, blocking

| class | may the census count it? | *(the harness spec carries its own question-class column — MOVED)* |
|---|---|---|
| **first-party stated** | yes | yes — the ANSWERED baseline |
| **third-party / unverified** | yes | 🔴 **yes, and this is the contribution** — the question class where the answer IS present and MAY NOT be asserted |
| **quarantined** | yes | yes — must produce REFUSED-UNTRUSTED, never ANSWERED |
| **redacted / absent** | yes | yes — must produce REFUSED-ABSENT |
| **counts themselves** | **carry no record content** — an id and an integer, nothing else (§7) | n/a |

## 3b. Authorization and scope

The census is **observation-only and cannot alter a decision** (INV-7, now a
THREE-arm diff — see Part A-2). It has no authorization surface of its own: it
reads what the host already computes. 🔴 **It runs in PRODUCTION and is opt-in,
default OFF**; the fixture-store constraint that stood here belonged to the
harness and travelled with it.

## 4. Behaviour

### Part A-0 — what an ENFORCEMENT POINT is, and where the expected set comes from

🔴 **Both were undefined in v2 and both are load-bearing.**

**DEFINITION.** An enforcement point is **any site that can return a decision
other than the caller's request** — refuse, quarantine, withhold, abstain,
downgrade. **It is a property, not a choice.** v2 said *"each enforcement point
declares a stable id"* without saying which sites those are, which made the
census's domain "whatever someone instrumented" — **a hand list one level up, in
the spec written to kill hand lists.** 🔴 **THE 162 IS WITHDRAWN — NOT REPAIRED. (Round-1 amendment 4.)**

v3.1 offered a count of *"decision-shaped sites in the five guarded files"* and
labelled it an UPPER BOUND on candidates. **The reviewer reproduced it and showed
it is not a bound at all:** it misses ordinary `return False` decisions and
excludes relevant modules such as `scope.py`.

> **Both of its boundaries were CHOSEN, not derived.** The five files came from
> the GUARDED set — which exists to route review, a different purpose entirely —
> and the pattern came from me. **A lexical line count over a hand-picked file
> set is the same defect as a hand list of enforcement points, one level up, in
> the section written to kill hand lists.** v3.1 already said it counts comments
> and docstrings; what it did not say is that a line is not a site and that
> nothing established the file set.
>
> 🔴 **So it is not restated with a caveat. It is gone.** A quantity whose domain
> was picked by its author cannot bound anything, and carrying it with a warning
> would let a reviewer cite the number and drop the warning — which is how the
> withdrawn figures in this project's own history survived.

**THE DOMAIN IS NOW MEASURED, and it is a PREREQUISITE of this spec rather than a
premise inside it.** The inventory is an AST pass over **all of `src/veracium`**,
not a lexical pattern over a chosen subset, and it defines:

| | |
|---|---|
| **counting unit** | 🔴 **THE TOOL'S UNIT, STATED VERBATIM, because 636 is the tool's number:** one AST node of a listed kind — **`RAISE`** (every `raise` statement, no branch condition) · **`RETURN_FALSE`** (`return False`) · **`RETURN_NONE`** (`return None` or a bare `return`, *only inside a function that also returns a value somewhere*). Not a line, not a function. *(v4 first wrote a STRICTER unit — “reached on a branch that can also return the caller's request” — which the tool does not implement and nothing executes. A prose definition and a figure that disagree are two definitions of one quantity: the same defect this spec's §2 raises about ids, at the definition rather than the count. The branch condition is exactly what the INSPECTION adds; it is not in the inventory.)* |
| **site identity** | `(module, qualname, line)` — stable across formatting, and the key the declaration joins on |
| **bounded scope** | every module under `src/veracium`, stated by name in the evidence output, so a later reader can see what was NOT scanned |

**THE INVENTORY HAS NOW RUN** (`specs/evidence/0042/decision_site_inventory.py`,
against `src/` at pin `5121501`):

| | |
|---|---|
| modules scanned | **55**, every `src/veracium/**/*.py`, nothing excluded |
| modules with at least one site | **40** |
| **candidate sites** | **636** = `RAISE` **482** + `RETURN_FALSE` **82** + `RETURN_NONE` **72** |

> 🔴 **THIS IS AN INVENTORY OF CANDIDATES BY SYNTACTIC KIND. IT IS NOT A COUNT
> OF ENFORCEMENT POINTS AND IT IS NOT A VERDICT.** A `raise` may be an argument
> check; a `return False` may be a predicate. **It is where an inspector STARTS.**
> *(The superseded “inspected subset” comparison is in §11.)*

**Both seats derived it independently and disagreed, and the disagreement was
research's.** Dev reported 636; research's first pass returned **652**, with
`RAISE` agreeing exactly at 482 and only the return kinds differing. The cause
was research's: `ast.walk(fn)` descends into NESTED functions, so a `return` in a
closure was counted once for the enclosing function and again for the closure.
Re-run with a visitor that sees each `Return` once: **636, all three kinds
matching.**

> **The lesson is the one this spec exists to make.** Two counts of one quantity
> differed by 16, and comparing the COUNTS would have said only that somebody was
> wrong. **Reading the other seat's DEFINITION is what located it** — and it
> located it in the seat that went looking. *A disagreement is self-announcing;
> an agreement is not.*

**THE EXPECTED SET comes from a spec-side DECLARATION this spec creates**, one
row per point: `id · governing spec · §6 invariant it enforces · file:symbol`.
**It must be authored, not scraped** — see §2's row. **INV-1 then has TWO
independent sources**: EXPECTED from the declaration, OBSERVED from the sites.
Neither derives from the other, so **drift is a refusal in both directions**: a
declared id that never reports, and a reporting id never declared.

> **Without two sources INV-1 is vacuous.** If the expected set is collected from
> the ids at the sites, absent-from-report is impossible by construction.

### Part A — the firing census

1. Each enforcement point declares a stable id at its decision site, **and the
   same id appears in the declaration**. 🔴 **`consulted` is incremented BEFORE
   THE DECISION BRANCHES**, never where the result is consumed — otherwise a
   point consulted and short-circuited downstream reads as unconsulted.
2. When the point EXECUTES, it increments `consulted`; when it DECLINES
   (refuses, quarantines, withholds), it also increments `fired`.
3. `census()` returns, for every id **in the declaration**:
   `{id, status, consulted, fired, errors}` where **`status` is one of the SIX
   in Part A-1's state table** — `DISABLED` · `UNDECLARED` · `UNMEASURED` ·
   `UNREACHED` · `UNEXERCISED` · `EXERCISED`, in that precedence order.
   🔴 **Part A-1 is the sole authority for the enum and its conditions; this
   step does not restate them.** *v4 enumerated five here and the validator
   implemented four — three carriers of one value is how they drift, so this one
   now points instead of copying.*
   🔴 **`UNMEASURED` needs its own field, and so does the count of five.** v2 put it in
   §7 prose while the row shape was `{id, consulted, fired}`, so **a counter that
   raised before incrementing rendered as `consulted=0`** — *which under Part A-1
   now renders as `UNREACHED`; the defect is identical and the status it wore
   changed* — the
   ok-vs-na collapse this spec names at §10.1, inside its own report.
4. A declared id absent from the report is a **failure of the census**, not a
   zero (INV-1).

### Part A-0-bis — THE THREE SETS *(round-2 amendment A4)* — 🔴 **SUPERSEDED IN PART BY A-0-ter: THERE ARE FOUR**

> 🔴 **Round 3 found the fourth.** This section derived DISCOVERED and authored REVIEWED and DECLARED — and then rested **INSTALLED** on the two authored ones, which can both be true of code containing no instrumentation. **`INSTALLED` is now derived from the source by a static scan (A-0-ter).** *The sets and refusals below stand; only INSTALLED's definition moved.*

🔴 **Round 2 found a contradiction and it is real: §4 A-0 says the declaration
is compared against an “INSPECTED SUBSET” of the inventory, while INV-2d refuses
on ANY inventory site absent from the declaration. With 636 syntactic candidates
that means declaring every ordinary `raise`** — including argument checks and
predicates that are not enforcement points at all.

**The fix is that there are THREE sets, not two, and v4 named two.**

| set | what it is | who made it |
|---|---|---|
| **DISCOVERED** | the AST inventory — **636 candidates by syntactic kind** | 🔴 **nobody.** Derived from the code; its value is that no one chose its members |
| 🔴 **REVIEWED** | **one INCLUSION-OR-EXCLUSION DECISION for every discovered candidate**: `{candidate_id → decision: enforcement \| not, reason, reviewer}` | **authored, and that is the point** — *the reviewer's “record inclusion/exclusion decisions”* |
| **INSTALLED** | **the scan of the BINDING — see Part A-0-quater, which is the current definition** | **nobody** — derived from the source. *Two earlier definitions were tried and failed; both are in §11 with what each missed.* |

#### The refusals, rewritten so they compare the RIGHT pair

| condition | verdict |
|---|---|
| a **DISCOVERED** candidate with **no decision in REVIEWED** | 🔴 **REFUSE.** *This is what makes the third source bite — and it demands a DECISION, never a declaration, so an ordinary `raise` is discharged by recording “not an enforcement point, argument check”* |
| **REVIEWED-as-enforcement** but **not DECLARED** | **REFUSE** — a point we agreed enforces something and nobody declared |
| **DECLARED** but **not REVIEWED-as-enforcement** | **REFUSE** — a declaration nobody reviewed |
| **reporting** but not **DECLARED** | `UNDECLARED` (Part A-1), and the report refuses |

> **The inventory never forces a declaration. It forces a DECISION.** *That is the
> whole difference between a third source that bites and one that would require
> declaring predicates, and v4 collapsed them by comparing the declaration
> against the inventory directly.*

#### The coverage claim, stated at its real width

**DISCOVERY covers the node kinds it scans and NOTHING ELSE.** Round 2 named four
policy decisions it misses — `Edge.assertable`, `Edge.quarantined`,
`gate.partition_parts`, `gate.exclude_procedural` — **Boolean-returning properties
and collection-returning filters, which are not `raise` / `return False` /
`return None`.** The discovery kinds are widened to cover them.

> 🔴 **And the claim is narrowed in the same breath, because widening a scan can
> never establish that nothing is left:** *a generated inventory is independent
> evidence about the kinds it scans. It is NOT evidence of semantic
> completeness, and this spec does not claim it is.* **What the REVIEWED set
> establishes is that every candidate the scan found got a human decision — not
> that the scan found everything.**

### Part A-0-ter — INSTALLED IS DERIVED FROM THE CODE *(round-3 blocker A4)*

🔴 **Round 3: REVIEWED + DECLARED does not establish INSTALLED.** With every
candidate reviewed, every enforcement point declared, **no counters and no
reports**, the three-set reconciliation PASSES and `report_rows()` yields valid
`UNREACHED` rows — **byte-identical for installed-but-unused and for
instrumentation that was never installed at all.** That is the exact distinction
INV-2c exists to draw, and A-0-bis could not draw it **because both of its
authored sets can be true of code that contains no instrumentation.**

> **Two authored lists agreeing proves consistency, not installation.** A-0-bis
> said that about COMPLETENESS and then rested INSTALLED on the same two lists.
> *The third set was derived; the fourth quantity was not, and nobody noticed
> because the derived one was standing next to it.*

#### INSTALLED comes from the code, by two derivations that check each other

| set | how it is derived | who authored it |
|---|---|---|
| **SCAN** | 🔴 a static AST pass for ids carrying **BOTH `declare_site(…)` AND a `.consult`/`.fire` BINDING** (A-0-quater), yielding `(id, module, qualname, line)` | **nobody** — derived from the source |
| **REGISTRY** | the **import-time record**: each `declare_site(id)` registers when its module loads | **nobody** — produced by execution |

**`INSTALLED` is defined at Part A-0-quater.** *(Two superseded definitions are in §11.)*

**The REGISTRY is the CHECK ON THE SCAN, not a second opinion about it:**

| condition | verdict |
|---|---|
| a module LOADED and a scanned site in it did **not** register | 🔴 **REFUSE** — the call is in the source and did not run: dead branch, guarded import, or a site the scan misread |
| a module **did not load** in this process | its sites are **NAMED IN THE REPORT as out of reach**, never silently absent — *a census must state what it could not observe* |
| registered but **not** in the scan | **REFUSE** — something registered that the source does not show |

#### The reconciliation, now over FOUR sets

    DISCOVERED  -> every candidate carries a DECISION in REVIEWED        else REFUSE
    REVIEWED-as-enforcement  ==  DECLARED                                else REFUSE
    DECLARED    ==  INSTALLED (the scan)                                 else REFUSE
    reporting   ⊆  DECLARED                                             else UNDECLARED + refuse

#### 🔴 The reviewer's demonstration, made the standing control

> **Delete a counter while KEEPING its decision and its declaration.** The scan
> loses it → `INSTALLED` ≠ `DECLARED` → **REFUSE.**
> **Keep the counter and send no traffic** → `INSTALLED` has it, `consulted == 0`
> → **`UNREACHED`.**
>
> **Those two must produce different verdicts, and before round 3 they produced
> the same one.** *This is the general control A6-ter states for the harness,
> applied here: for every clause saying “X is established”, delete X and require
> the check to fail.*

**Completing all 738 reviews remains implementation work** — the reviewer said so
and he is right; the refusal on our own tree is honest evidence, not a gap in the
design. **What was missing was the derivation of INSTALLED, and it is here.**

### Part A-0-quater — THE SITE BINDS THE DECISION *(round-4 blocker A4)*

🔴 **Round 4: “registration does not establish working instrumentation.”** With
both fixture decisions executed — the gate declined, ingest returned `False` —
the registry check found no refusals, the four-set reconciliation PASSED, **and
the counters never moved.** All three sites reported `UNREACHED` from empty
counters.

> **A-0-ter derived INSTALLED from a `declare_site` CALL, and a call is a PROXY
> for a counter bound to the decision.** *The scan was honest about what it
> scanned; what it scanned was the wrong thing.*

🔴 **AND OUR OWN CONTROL DEGENERATED.** It was named *“delete a counter”* and it
deleted the `declare_site` LINE, on a fixture that had no counters at all — so it
tested **missing registration** while its name promised **missing
instrumentation**. *The name asserted a property the body did not check: the
item-8 class, in the control written to prevent exactly this.*

#### The decision is expressed THROUGH the site

**So the update and the decision become ONE CALL and cannot be separated:**

```python
SITE = declare_site("gate.answer.unverified-only")
...
with SITE.consult():          # consulted += 1, at the decision
    if not assertable:
        raise SITE.fire(ValueError(...))   # fired += 1, ON the returned decision
```

| | |
|---|---|
| **`INSTALLED`** | 🔴 an id with a `declare_site` call **AND, in ONE function body, BOTH a `.consult()` use AND a `.fire(` use** on the declared name — 🔴 **the body is the LEXICAL one and the name must be UNSHADOWED: a nested function is its own scope, and a parameter or a local assignment rebinding that name is not the site** (round 5). *Not either: a body with `consult` and no `fire` takes traffic that moves `consulted` while a decline never moves `fired`, so the row reads `UNEXERCISED` for a site that FIRED — the exact confusion Part A-1 exists to prevent, reintroduced through a permissive binding rule.* |
| **declared, registered, NOT bound** | **REFUSE** — *“registered, not installed”*, which is precisely what round 4 found and A-0-ter called installed |
| 🔴 **bound in the MODULE but not in one body** | **REFUSE** — *round 5 reproduced v7's scan: `.consult()` in one function, `.fire()` in another, keyed only by variable name, reported `bound=True` and the registry check accepted it. **A scan keyed by NAME answers “does this module mention both” — a different question, true more often than the one asked.*** |

#### Two derivations, and the second is the reviewer's own test made an assertion

| | |
|---|---|
| **STATIC** | the scan above — the code binds the counter to the decision |
| 🔴 **RUNTIME** | **execute ONE declining decision and assert the counters MOVED ACROSS IT: Δ`consulted` == 1 AND Δ`fired` == 1**, measured as the difference between a snapshot before and a snapshot after that decision (Part A-2's snapshot contract). 🔴 **NOT `consulted ≥ 1` / `fired ≥ 1`, which is what v8 asserted: a LEVEL says the counter is positive, and an EARLIER decision can have made that true — “an already-positive counter must not establish that a later decision was measured” (round 5). A level assertion on a counter is the proxy defect this whole Part exists to fix, one level up.** *Exactly one, not at least one: `≥` also passes a site that double-counts.* **And one counter is not enough** — a site bound only for `consult` passes a one-counter assertion while never recording that it fired. *The scan says the binding exists; the execution says BOTH halves of it work. Round 4 is what happens when only the first is checked; round 5 is what happens when the second is checked with the wrong operator* |

#### The controls, with the naming defect fixed

| control | must |
|---|---|
| **strip the wrappers, KEEP the `declare_site` line and the `raise`** · **and separately: keep `.consult`, strip `.fire`** | **REFUSE** — *this is what “delete a counter” was always supposed to mean, and now the fixture HAS counters so the name and the body agree* |
| 🔴 **`.consult()` in one function and `.fire()` in another — same module, same name** · **and: `.fire` inside a NESTED function** · **and: both uses on a name a parameter or local assignment SHADOWS** | **REFUSE** — *the reviewer's round-5 reproduction and its two neighbours, made standing regression checks* |
| 🔴 **counters PRE-LOADED positive, then a decision that never reaches the site** | **REFUSE.** *This is the mutant for the runtime assertion: under `≥ 1` it PASSES. If the check does not fail here it is measuring the counter's HISTORY, not this decision* |
| **full binding, no traffic** | `UNREACHED` |
| **execute a decision** | the counters move **by exactly one each, asserted as a delta** |

> **The fixture must carry REAL COUNTER UPDATES.** *A control cannot delete what
> the fixture never had, and a fixture that cannot present the thing under test
> makes every control over it vacuous — the same finding as round 3's
> compilation-off fixture, one spec over.*

### Part A-1 — THE STATE TABLE *(round-2 amendment A5; the single authority)*

🔴 **This table is the ONE definition. Prose, schema and tests all derive from
it, and where any of them disagreed before, this table wins.** Round 2 found the
spec naming five statuses, the validator supporting four, and its test requiring
four — three carriers of one value, which is the defect this spec exists to
measure.

#### The two counters, defined once

| | |
|---|---|
| **`consulted`** | the site was **REACHED and EVALUATED** — control arrived, the condition was tested |
| **`fired`** | the site **RETURNED A DECISION OTHER THAN THE CALLER'S REQUEST** — refused, quarantined, withheld, abstained, downgraded |

> **`fired` ≤ `consulted` always.** A site cannot decide without being reached.

#### 🔴 SIX statuses, not five — and the sixth is the one the reviewer's question forces

**The reviewer asked for one authoritative reading of `consulted` vs `fired`.
Giving one exposes that FIVE STATUSES CANNOT CARRY IT.** `consulted = 0` and
`consulted > 0, fired = 0` are **different findings**:

- **`consulted = 0`** — the site never ran. *Nothing was asked of the guarantee.*
- **`consulted > 0, fired = 0`** — the site ran and **the guarantee never
  engaged.** *This is exactly `tigerless-labs`' finding in §1: 3,744 memories
  written, supersede edge count **ZERO** — the mechanism executed and its outcome
  never once occurred.*

**Collapsing those two into one `UNEXERCISED` destroys the distinction §1 is
built on**, and it is the `ok`-vs-`na` collapse this spec names at §10.1,
committed inside its own status enum. **So the table has six rows.**

| status | condition | precedence |
|---|---|---|
| **`DISABLED`** | `enabled == false` | **1** — wins over everything; no count is meaningful, and the counts are omitted rather than reported as zero |
| **`UNDECLARED`** | `declared == false` | **2** — see the INV-1 disposition below |
| **`UNMEASURED`** | `errors > 0` | **3** — a counter that raised cannot be read as a count |
| 🔴 **`UNREACHED`** | `consulted == 0` | **4** — *the site never ran.* **NEW at round 3** |
| **`UNEXERCISED`** | `consulted > 0 and fired == 0` | **5** — *it ran; the guarantee never engaged.* **This is the finding the spec exists for** |
| **`EXERCISED`** | `fired > 0` | **6** |

**Precedence is evaluated top to bottom and the first match wins**, so every
`(consulted, fired, errors, declared, enabled)` tuple maps to exactly one status
and no tuple maps to none. *A state table that does not say what happens when two
conditions hold at once is a table with a gap, and the gap is where the
implementations diverge.*

#### 🔴 STRUCTURAL RECONCILIATION RUNS BEFORE STATUS *(round-3 bounded obligation A5)*

**Round 3 found that disabling measurement let an UNDECLARED id through
validation.** The sentence below is dev's, verbatim, and it is the spec BECAUSE
the validator does this — not a description that happens to agree with it:

> **STRUCTURAL RECONCILIATION RUNS BEFORE STATUS AND DOES NOT DEPEND ON
> `enabled`. An id that reports but is not declared, a declared id absent from
> the report, and a duplicate id each REFUSE the report whether measurement is on
> or off. The state table orders STATUSES; it never switches reconciliation off.
> So under `enabled == false` an undeclared reporter's row is emitted with status
> `DISABLED` (precedence 1) AND the report refuses (INV-1) — the row is the
> evidence for the refusal, exactly as for `UNDECLARED` when measurement is on.**

*The precedence table orders what a row is CALLED. It was never a gate on whether
the report is checked, and v5 did not say so — which is how `enabled=false` came
to suppress a refusal that has nothing to do with measurement.*

#### The three things round 2 found unresolved, resolved

| | |
|---|---|
| **`UNEXERCISED` with `consulted=10, fired=0`** | 🔴 **VALID, and it is the central case.** The validator rejecting it was wrong and INV-2's prose was right. *A guard consulted ten times that never fired is the thing we set out to detect.* |
| **`UNDECLARED`: reported or refused?** | 🔴 **BOTH, and that is not a contradiction.** The row IS EMITTED with status `UNDECLARED`, **and the report as a whole REFUSES** (INV-1). *The row is the EVIDENCE FOR the refusal — a refusal that does not say which id caused it is an `ok`-vs-`na` collapse in the other direction.* |
| **negative counts** | **REFUSE the report.** Not a status: a negative `consulted` is not a census outcome, it is a broken counter, and §4's contract is that a broken instrument reports `UNMEASURED` **only when it knows it broke**. A negative it did not notice is worse and must stop the report. |

### Part A-2 — the counter lifecycle and the observation-only contract *(amendment 5)*

**v3.1 left activation unresolved and said nothing about concurrency, snapshot
consistency or partial failure.** Each of those turns a census into a number
nobody can interpret, and the reviewer named all four.

| | |
|---|---|
| **activation** | **opt-in, default OFF** (Quentin, 2026-09-18, *relayed to this seat through dev*). Resolved for v1 rather than deferred |
| **disabled ≠ zero** | a deployment that never enabled it reports `DISABLED` per id (INV-2b). 🔴 *A measured zero and an unmeasured one are the same bytes unless the status distinguishes them, which is this spec's own thesis applied to its own output* |
| **concurrency** | counters are process-local and monotonic; increments are atomic per id. A report names the process it read |
| 🔴 **snapshot consistency — ONE ANSWER (round-2 A5)** | **PER-ID ATOMIC; report-level WINDOW, recorded.** *v4's prose allowed a window while the schema demanded one atomic read under one lock — two answers to one question.* **Per-id is sufficient and a global lock is not**, because every status in Part A-1 is a function of ONE id's tuple: no row depends on another row's counters, so cross-id atomicity buys nothing a reader can use. **The report carries `window_start` and `window_end`**; a report whose window exceeds a deployment-stated bound says so in the header rather than being refused. ⚠️ **And a global lock is the WRONG trade here specifically**: it would serialise the very sites INV-7 must show are unaffected, so the cheap consistency guarantee would be bought by making the observation-only claim harder to hold. |
| **partial failure** | a counter that raised reports `UNMEASURED` for that id **and does not invalidate its neighbours**; the report states how many ids are `UNMEASURED`. 🔴 **An incomplete set of counters must never produce an apparently valid total** |

#### 🔴 THE COMPARED TRACE FIELDS *(round-2 amendment A5 — v4 said these were "named" and named none)*

**A decision trace is an ordered sequence of records, one per enforcement point
REACHED, carrying exactly these fields and no others:**

| field | why it is IN |
|---|---|
| `seq` | the position in the sequence. **Order is the signal**: a census that changed which site runs first has altered a decision even if every site still runs |
| `site_id` | which enforcement point was reached |
| `decision` | the branch taken — the caller's request, or the refusal/quarantine/withhold/abstain/downgrade actually returned |

| field | why it is OUT |
|---|---|
| **wall-clock / duration** | differs between arms **BY CONSTRUCTION** — the instrumented arm does more work. Including it makes INV-7 fail on every run and the failure would carry no information |
| **counter VALUES** | the census is the independent variable. Comparing it across arms compares the thing being varied |
| **record content, user ids, digests** | INV-8 forbids them in the census and they are no safer in a trace |

> **The comparison is `[(seq, site_id, decision), …]` byte-identical across all
> three arms.** *Naming the fields is the whole assertion: “the traces match” is
> unfalsifiable until someone says which bytes, and v4 asserted that someone had.*

#### The third arm *(amendment 5's sharper half)*

**v3.1's INV-7 compared healthy counters against counters forced to error.** The
reviewer's objection is one both arms share a defect:

> *“Comparing healthy counters with failing counters is useful, but both versions
> could introduce the same change to product behavior.”*

🔴 **He is right, and it is this project's own control lesson: two arms that
share the instrument cannot detect the instrument.** So INV-7 becomes a **THREE-ARM
decision-trace diff** — healthy · failing · **UNINSTRUMENTED** — and the trace
fields compared are **named in the spec** rather than left to the harness. *An
uninstrumented reference is the only arm that can show the census changed nothing,
because it is the only one without a census in it.*

### Part B — MOVED OUT OF THIS SPEC

🔴 **The refusal harness is no longer part of 0042.** On Quentin's ruling
(2026-09-18) it becomes its own candidate:
`proposals/0043-refusal-harness-CANDIDATE.md` — **allocated 0043 at adoption `1bc2917` from
`allocation.py --next`, read from the registry rather than from a filename or a message.**
🔴 *v4 pointed at `0042B-…`, a placeholder name that was true when written and
dangling from the moment the candidate was renamed — and the gate that catches a
stale reference, `tests/test_spec_gate.py::test_no_spec_names_a_module_or_script_that_does_not_exist`,
matches backticked `.py` names ONLY, so this `.md` would have shipped silently.* *0040 is spent, 0042 is this spec; a filename is not an
allocation, and this project has already paid once for treating one as if it were.*

**It carries round-1 amendments 1, 2, 3 and 6, and invariants INV-3/4/5/6.** It is
moved rather than redrafted, so the new spec starts from the text the reviewer
actually read.

**What this spec still owes it:** nothing. The harness counts its own attempts and
outcomes. **0042 supplies evidence about internal decisions; it does not supply a
denominator** — that dependency was the round-1 reviewer's §9 ruling and its
removal is why the two are separable at all.

## 5. Regime analysis

| regime | behaviour |
|---|---|
| ~~**fixture corpus**~~ | **MOVED with the harness** — the census runs against the PRODUCTION store, which is the point of it |
| **a store where a class never occurs** | 🔴 the census reports **`UNREACHED`** with the id named — *the site was never consulted, which is a different finding from `UNEXERCISED` (consulted, never fired) and the distinction is the point of Part A-1* — **and, if the census was never switched on, `DISABLED` instead (INV-2b), which is a different fact about a different thing** |
| **long-running host** | counters are process-local and reset on restart; a census is a statement about one process's lifetime (§8) |
| **concurrent recalls** | counts may interleave; the census claims totals, never per-request attribution |

## 6. Invariants and executable checks — REQUIRED, blocking

| id | invariant | executable check |
|---|---|---|
| **INV-1** | **CENSUS-TOTAL, FROM TWO INDEPENDENT SOURCES** — every id in the DECLARATION appears in the report, and every reporting id is declared | add a declared id with no site → report REFUSES; add a site with no declared id → report REFUSES. **Both directions, or the check is one source comparing with itself** |
| **INV-2** | **ZERO-IS-A-VERDICT, AND AN ERROR IS A THIRD ONE** — 🔴 **and “zero” is TWO verdicts, not one**: `consulted == 0` → `UNREACHED`, `consulted > 0 and fired == 0` → `UNEXERCISED`, both with the id named (Part A-1); a counter that raised → `UNMEASURED`; never omitted, never `ok` | two fixtures: a never-fired guard asserts `UNEXERCISED`; **a FORCED-RAISE counter asserts `UNMEASURED` and must NOT render `UNEXERCISED`** |
| **INV-2b** | 🔴 **DISABLED IS A STATUS, NOT A MISSING REPORT** — activation is opt-in and default OFF (Quentin, 2026-09-18, *relayed*); a deployment that never enabled the census reports **`DISABLED`** for every declared id. **Never a zero, never `UNREACHED` or `UNEXERCISED`, and never a report-level flag a per-id reader can skip.** **The enum and its precedence live in Part A-1 and nowhere else** | run the report with the census off; assert every row reads `DISABLED` and that NO row reads `UNEXERCISED` |
| **INV-2c** | 🔴 **INSTALLED IS NOT EXERCISED, AND RUNTIME CANNOT TELL THEM APART** (amendment 4) — *a correctly installed site with no traffic and a MISSING site both produce no runtime events.* So INV-1's missing-site check is settled against the **AST inventory**, never against runtime counts | 🔴 **the missing-site check compares the DECLARATION against the REVIEWED set, never against DISCOVERED (Part A-0-bis)** — four checks, each with its own fixture: **installed-but-unused** (asserts 🔴 **`UNREACHED`**, not missing — *`consulted == 0`; v4 said `UNEXERCISED` and the six-status change reached A-1 and INV-2 but not this row*) · **missing** (🔴 **REVIEWED-as-enforcement, absent from the declaration → REFUSE** — *v4 compared the raw inventory to the declaration, which would demand declaring every ordinary `raise`; Part A-0-bis*) · **undeclared** (reports an id nobody declared → REFUSE) · **duplicate id** (two sites, one id → REFUSE) |
| **INV-2d** | 🔴 **TWO AUTHORED LISTS AGREEING PROVE CONSISTENCY, NOT COMPLETENESS** (amendment 4) — the declaration and the report are both authored; their agreement cannot establish that neither omits the same point. **The third source is the AST inventory, which nobody authored** | 🔴 assert the report REFUSES when a **DISCOVERED candidate has NO DECISION in the REVIEWED set** — *not when it is absent from the DECLARATION, which round 2 showed would require declaring every ordinary `raise`. The inventory forces a DECISION, never a declaration (Part A-0-bis)* |
| **INV-7** | **OBSERVATION-ONLY** — no counter may alter a decision | **a THREE-ARM DECISION-TRACE DIFF, not a green run** (amendment 5; the two-arm form is withdrawn because both arms carry the instrument): capture the trace with counters **healthy**, **forced to error**, and **UNINSTRUMENTED**, over **the trace fields listed in Part A-2's table below**, and assert all three are **byte-identical**. Name the suites that actually reach the instrumented sites — **0027's (graph.py) and the gate/ingest/schema suites**. 🔴 **NOT 0041's**: it is accepted and UNIMPLEMENTED, its tests are frozen-record transition tests with eleven strict xfails, and none exercises a gate decision — **forcing counters to error there changes nothing they can observe, so that half would pass vacuously** |
| **INV-8** | **COUNTS CARRY NO CONTENT** — a census row is an id and integers | assert no record text, user id, or digest appears in the report |

**Each check must be demonstrated RED** against a deliberately wrong
implementation before it is accepted — an undemonstrated control is the defect
this spec exists to find.

## 7. Failure modes and reversibility

| failure | consequence | reversal |
|---|---|---|
| a counter raises | 🔴 **must not fail the caller** — the decision is the product; the measurement is not. The row's `status` becomes **`UNMEASURED`** and `errors` increments (§4 step 3), which is a FIELD and not prose | remove the counter; no stored state |
| the registry and the call sites drift | INV-1 turns it into a refusal rather than a silent gap | — |
| the declaration omits a point the code has | **INV-2c/2d: the AST inventory is a third source neither list authored** — 🔴 and a DISCOVERED candidate carrying **no DECISION in the REVIEWED set** is a REFUSAL *(not one absent from the declaration; Part A-0-bis)* | re-run the inventory; it is derived, not maintained |
| counts leak content | INV-8; counters take an id and an integer only | — |

**Fully reversible.** No schema change, no stored field, no migration.

## 8. Claims and limits

**Claimed:** for a named deployment and a named read window, **which declared
enforcement points were INSTALLED, which were EXERCISED, which were not, and
which could not be measured** — each id carrying one of the SIX statuses in Part A-1's table. 🔴 **NO
RATE IS CLAIMED HERE.** v3.1 claimed a refusal rate beside a baseline arm; that
claim, its arms and its denominator argument all travelled to the harness spec
with the round-1 reviewer's §9 ruling.

**NOT claimed:**
- that a zero-count guard cannot fire — only that **this corpus never presented
  the condition** (§2c-ii)
- 🔴 **that the census generalises beyond THIS deployment and THIS process
  lifetime.** A census is a fact about what ran where it ran (§5)
- 🔴 **semantic completeness of discovery.** The inventory is evidence about the
  node kinds it scans; **widening a scan can never establish that nothing is
  left** (Part A-0-bis)
- 🔴 **a rate of any kind.** The census reports statuses and counts. Every rate in
  this arc belongs to the harness spec

> 🔴 **THREE HARNESS LIMITS WERE REMOVED FROM THIS LIST AT ROUND 3** — *the
> fixture generalising to a production store* (the census has no fixture and §5's
> row moved out), *comparison to another system's published refusal figures* (the
> census publishes no refusal figure), and *the answer-quality limit* whose
> sentence **had already been MOVED to 0043 §8 by a note in this file and
> survived here anyway.** **That is the reviewer's C4 — “remove obsolete harness
> claims from 0042” — and a limit that names an artifact the spec no longer has
> is not caution, it is a claim about the wrong document.**

## 9. Brief for the external reviewer — ROUND 5

🔴 **This §9 named ROUND 2 until now, and four packages sealed with it.** *The
pre-seal rule refuses a §9 naming a returned round; no stage script gated §9 for
this arc, so the brief went out four times describing questions the reviewer had
already answered. **A section that states its own round is a carrier of the round
number, and nothing was re-deriving it.*** The sealing script now refuses a
mismatch.

**Rounds 1–4 are answered and not re-asked.** The split, the six-status table, the
three sets, the derivation of `INSTALLED`, and the removal of harness claims are
settled. **A6 closed at round 4.** Round 4's A4 is answered by Part A-0-quater,
and the two questions below are what that answer leaves open.

### The questions this round asks

1. 🔴 **Is “both derivations” enough for `INSTALLED`?** A-0-quater derives it
   statically (the scan requires a `declare_site` **and both** a `.consult()` and
   a `.fire(` in one body) and dynamically (execute a declining decision; both
   counters must move). **Both run over a FIXTURE.** *Should the runtime
   assertion be required to run over the PRODUCT's real suites once `src` carries
   its first site — and if so, is a suite that never presents a declining
   condition for some site a gap the census must report, or a fact about the
   suite?*
2. **Does the four-set reconciliation now rest on anything still authored?**
   DISCOVERED and INSTALLED are derived; REVIEWED and DECLARED are authored by
   construction. *We believe the refusals are placed so that no authored pair can
   agree its way past a missing binding — we would rather be told early if a
   pair remains that can.*

> 🔴 **ANSWERED, round 5 — recorded beside the question, which is left as
> dispatched:** *“require runtime checks at real product sites once implemented,
> alongside the three-arm decision-trace comparison. **A suite that never supplies
> a declining case is a test coverage gap.** The census should continue reporting
> observed statuses: `UNREACHED` when never consulted, or `UNEXERCISED` when
> consulted without firing.”* **And on authored agreement:** *“corrected
> independent scans prevent the authored sets from agreeing past a structurally
> missing binding. Human decisions about which candidates constitute enforcement
> remain a semantic review responsibility.”* — *so A-0-bis's two-authored-lists
> hazard is answered by the scan, not by more authorship, and the residual
> judgement is named as judgement.*

### What we are NOT asking

**Whether 738 reviews are complete.** *Round 3 ruled that implementation work and
round 4 did not reopen it; the tree's red on `installed_sites` is the honest
state and the test is written to fail the day the first real site lands.*

## 10. Open questions

1. ⚖️ **RULED 2026-09-18 — INSTRUMENT PRODUCTION.** Quentin: *"if the census
   instrumenting production will give us better results then we should go that
   direction."* **It does, and the reason is stronger than "better": the replay
   variant is STRUCTURALLY INCAPABLE of answering the question.**

   `Memory.recall` writes a receipt under `if receipt_raw is not None:` — **the
   record exists only when the lane FIRED.** So a replay census over receipts:

   - **cannot observe a zero.** No receipt is written when nothing fires, so
     *"never fired"* and *"never invoked"* produce the same evidence — **exactly
     the distinction this spec exists to draw**, and the `ok`-vs-`na` failure one
     level up
   - 🔴 **cannot observe INSTALLATION, which is a second blindness and the one
     amendment 4 names.** The bullet above is about *never fired* vs *never
     invoked*; this one is about **a site that was never INSTALLED.** A missing
     site and a correctly installed site with no traffic write **the same
     nothing**, so no replay over receipts can implement INV-1's missing-site
     check. *That is why the check settles against the REVIEWED set (Part
     A-0-bis) rather than against runtime evidence.*
     *(v4 history: this bullet once cited §1's argument that Part B needs Part
     A's denominator — a claim §1 no longer makes. The round-2 rewording then
     restated the bullet above it instead of saying this; **a correction that
     duplicates its neighbour is a correction that did not land**, and dev caught
     it reading the two in sequence.)*
   - **sees one mechanism.** Supersession, correction, `forget_user`, quarantine
     promotion and the reserve write no `policy_receipt`; the candidate set is
     five and receipts cover one

   **Consequence, accepted with the ruling: `Path: full`, external review
   required** (the counters land in guarded files). **The replay variant is
   withdrawn, not deferred** — keeping it as a fallback would invite a later
   seat to take the cheap half and report zeros it cannot see.
2. ⚖️ **RULED — no longer open.** *Always-on or opt-in?* **Opt-in, default OFF,
   with `DISABLED` reported per id** (Quentin, 2026-09-18; **that ruling reached
   this seat RELAYED through dev, marked so a later reader can tell which rulings
   arrived first-hand**). Implemented at Part A-2 and INV-2b. *v4 left this open
   while two other sections recorded it ruled — a clause and its open question are
   two carriers of one value, and this project has had them disagree before.*
3. **Should `policy_receipt` carry the enforcement-point ids?** It would make the
   census durable and queryable rather than process-local — but it is a schema
   change and 0027 v14 has just shipped.
4. ~~**Who is the blind examiner?**~~ · ~~**How many questions per class?**~~
   **Both MOVED to the harness spec** — they are questions about an examiner and a
   rate, and this spec has neither.

---

## 11. Superseded decisions *(round-4: the reviewer read struck-through passages as live requirements)*

🔴 **This section exists because the practice of annotating in place was
CAUSING THE HARM IT PREVENTS.** Recording what was tried stops a later seat
re-deriving a failed answer — that is real and it is why the history is kept. But
**a superseded passage sitting inline in a normative section is read as a
requirement**, and round 4's reviewer did exactly that.

> **So the rule is refined rather than abandoned: THE HISTORY IS KEPT, AND IT
> LEAVES THE NORMATIVE BODY.** *A marker saying “this is not a requirement” is a
> PROXY for not being a requirement, and this arc has spent four rounds learning
> what proxies do. Structure asks nothing of the reader; a marker asks them to
> read more carefully than they just did.*

### The declaration compared against the raw inventory — superseded

**v4's §4 A-0 compared the declaration against an “INSPECTED SUBSET” of the
inventory while INV-2d refused on any absent site.** *Round 2: with 636 syntactic
candidates that means declaring every ordinary `raise`.* **Superseded by
A-0-bis's three sets — the inventory forces a DECISION, never a declaration.**

### `INSTALLED` — two superseded definitions

| version | definition | what it missed |
|---|---|---|
| **v5** (A-0-bis) | the declaration plus the ids that report at runtime | **Round 3: satisfied by code containing no instrumentation at all.** Both inputs were AUTHORED — and A-0-bis's own text said two authored lists agreeing proves consistency, not completeness |
| **v6** (A-0-ter) | a static scan for `declare_site(…)` calls | **Round 4: a registration is a PROXY for a counter bound to the decision.** Both fixture decisions executed, reconciliation passed, counters never moved |
| **v7** (A-0-quater) | the scan of the **BINDING** — `declare_site` **and** a `.consult`/`.fire` use, accumulated **over the MODULE and keyed by variable name** | **Round 5: “does this module mention both” is a different question.** `.consult()` in one function and `.fire()` in another reported `bound=True`; nested scopes and shadowed names were invisible to it. *The binding was right and the SCOPE it was checked over was wrong* |
| **v8** (A-0-quater) | the same binding, 🔴 **function-local, lexical and unshadowed**, with the runtime leg asserting **DELTAS across the decision** rather than positive levels | *current* |

### The “delete a counter” control — superseded

**v6's control deleted the `declare_site` LINE on a fixture with no counters**, so
it tested missing *registration* under a name promising missing *instrumentation*.
**The name asserted a property the body did not check.** v7's fixture carries real
counter updates and the control strips the binding while keeping the declaration.

## Review closure

This spec's ledger runs from the pre-split round 1 (0042 v3.1, one document) through round 5; rounds 2–5 were dispatched in one package with 0043, whose own ledger starts at its round 1 (= package round 2).

**PROCESS §4a: a spec at `accepted` carries one row per review finding, with
evidence a reader can RUN or OPEN.** Everything between the markers below is
GENERATED from `specs/reviews.py` and `specs/closure_findings.py` — the round
index from the first, the per-finding ledger from the second, validated against
each other on `(spec, kind, round, id)` exactly. **Do not edit it here.** A
ledger maintained beside the thing it summarises is the defect this project has
paid for most often, and the whole point of generating it is that a round
appearing in one and not the other is impossible rather than unnoticed.

**Two conventions a reader needs, and no count of them is written here.** A
round has TWO rows — the **SENT** dispatch record and the returning **verdict**
— labelled so the two are never summed; the totals are in the generated block
below, which derives them. And **some rows cite a FOLD COMMIT rather than a
test**, because for those findings the fold WAS this document's text: the line
had no implementation to point at, and P4's rule prefers an openable commit to a
grep that any file containing the new wording would satisfy. **Those rows are
enumerated in
`tests/test_spec_gate.py::test_new_closure_evidence_is_behavioral`, which is
where the list is maintained and where adding one is a visible diff**, and their
cost is pinned rather than absorbed: **a reviewer holding only the sealed archive
has no `.git` and cannot run them**, and
`::test_the_count_of_closure_evidence_unrunnable_in_a_package_is_pinned` fails
the day that number moves without a reason beside it. Every other row cites a
pytest node or the mutant campaign and runs anywhere.

> ⚠️ **This paragraph deliberately states no total.** The first draft of it said
> "five external rounds" or "N of the M rows" — hand-carried counts
> in the one section of this document whose entire subject is that a summary
> maintained beside the thing it summarises drifts. **Implementation review will
> add rounds and rows to this ledger**, at which point both figures would have
> been quietly wrong, in a paragraph introducing a generated block that has them
> right.


<!-- GENERATED:review-closure -->

**0 internal round(s) and 5 external round(s) with a returned VERDICT are recorded for `0042`; 5 package(s) were dispatched** — counted from `specs/reviews.py`, which is the source this block is generated from. A round appearing here and not there, or the reverse, is impossible by construction. **SENT rows are dispatch records, not outcomes**, and are labelled below so the two are never summed.

| round | date | findings raised (from `raised=`) | verdict (compressed) |
|---|---|---|---|
| external 1 (SENT) | 2026-09-18 | — | SENT (round-1 package 178b0d861be8c4bce0b6e9928b025531a1b43154145c1ec4dd6cfe7b13281f2a @ pin 5121501458b8ed78469d05aff45140b9cd217225, CI 35299877700; 0042 v3.1; fresh-clone capture at the pin: 3283 passed, 11 skipped, 11 xfailed, 2 warnings in 639.03s (0:10:39)). 0042 v3.1 — the line's first dispat… |
| external 1 (verdict) | 2026-09-18 | 6 | RETURNED FOR AMENDMENT — six amendments over one document: (1) define the rates and their measurement windows; (2) the proposed examiner input violates blindness; (3) define an independent outcome judge and question-level reference labels; (4) separate installed instrumentation from observed traffic… |
| external 2 (SENT) | 2026-09-18 | — | SENT (round-2 package 5253ab921c898881ee9e066937f6edbca96fab52d2b3a4e43bb46224ca577cbc @ pin 1bc29178014016d040e8cdb1ee92d81420970244, CI 35342079472; 0042 v4; fresh-clone capture at the pin: 3299 passed, 9 skipped, 11 xfailed, 2 warnings in 641.21s (0:10:41)). 0042 v4 — the census alone after the s… |
| external 2 (verdict) | 2026-09-18 | 2 | Both specifications are returned for amendment. Census side, two of six: A4 — The AST inventory cannot yet support the completeness claim. A5 — The census schema and comparison contract remain inconsistent. Verdict banked verbatim at `0042-round2-verdict-verbatim.md`, file sha16 c6ac407ec6d172c8, bo… |
| external 3 (SENT) | 2026-09-18 | — | SENT (round-3 package 61978df8fe0cfd1170c6cd71bfb06ab6ffa51c6667702ab929f1dd738540f415 @ pin f33f5bc2feab1798ba11f5cfd4ebc8e335ca451d, CI 35364857448; 0042 v5; fresh-clone capture at the pin: 3318 passed, 11 skipped, 11 xfailed, 2 warnings in 667.77s (0:11:07)). 0042 v5 — A4 answered by the reconcil… |
| external 3 (verdict) | 2026-09-18 | 3 | Both specifications are returned for amendment, with three remaining design blockers. Census side: A4 — Reviewed and declared does not establish installed. Bounded, not design: A5 — `errors > 0` correctly takes precedence over zero consultations. And the observation-only evidence bound (branch-seque… |
| external 4 (SENT) | 2026-09-18 | — | SENT (round-4 package 51887b16bbabc8b9616268958acedd101b1e6c1be3cfe1d214d8d653ddff9058 @ pin 43c1c637cef4372dadcf315a23f06ae8e1c8100d, CI 35373684787; 0042 v6; fresh-clone capture at the pin: 3330 passed, 11 skipped, 11 xfailed, 2 warnings in 685.41s (0:11:25)). 0042 v6 — Part A-0-ter: INSTALLED der… |
| external 4 (verdict) | 2026-09-18 | 2 | Round 4 verdict: returned for amendment. Census side: A4 — Registration still does not establish working instrumentation. Advisory: Consolidating the superseded passages would also help prevent old timeout and installation wording from being mistaken for current requirements. Verdict banked verbatim… |
| external 5 (SENT) | 2026-09-18 | — | SENT (round-5 package 791c1089776d9f49332483f8ff88b25794dec795ee8a7cf8eb33b441eaa1747a @ pin a9d3622d6252a19387b2ecb66a665f101825fb36, CI 35382261953; 0042 v7; fresh-clone capture at the pin: 3339 passed, 11 skipped, 11 xfailed, 2 warnings in 750.36s (0:12:30)). 0042 v7 — Part A-0-quater: the site B… |
| external 5 (verdict) | 2026-09-18 | 2 | Round 5 verdict: both specifications are accepted at the design level and may proceed to implementation. 0042 v7: ACCEPTED — DESIGN, frozen scope INV-1, INV-2, INV-2b–2d, INV-7, INV-8. One implementation obligation carried: make the binding scan function-local and scope-aware. Document maintenance: … |

**Per-finding closure ledger — PROCESS §4a.** **15 finding(s) for `0042`** — every number here is DERIVED from the rows below (external round 7, R7-1: the manifest claimed 26 while the ledgers held 31, and 0023 said 9/9 above a 10-row table); the total across the tracked specs is derived once, in `specs/STATUS.md`. Generated from `specs/closure_findings.py` and validated against `specs/reviews.py` on `(spec, kind, round, id)` EXACTLY — extras, duplicates, wrong rounds and empty evidence all fail the build.

| finding | round | what it was | closed in | evidence (runnable) |
|---|---|---|---|---|
| **0042-R1-1** | external 1 | the rates and their measurement windows were undefined (§§1, 4B, 5; INV-3/4): the denominator argument was overstated | travelled to 0043 at the split (owner's ruling, 2026-09-18): A1's ledger form — per-(question, arm) rows, rates over RESOLVED rows with the denominator stated, the timeout as its own terminal row; 0043 v1 §4B/INV-3/INV-4 | `git show 1bc29178014016d040e8cdb1ee92d81420970244 -- specs/0043-refusal-harness.md # v1 A1 — the ledger form` |
| **0042-R1-2** | external 1 | the proposed examiner input violated blindness (§4B step 1; INV-6) | travelled to 0043: the examiner view restricted to (subject, relation, object, since) with the flip test as the blindness proof; 0043 v1 §4B step 1, INV-6 | `git show 1bc29178014016d040e8cdb1ee92d81420970244 -- specs/0043-refusal-harness.md # v1 A2 — the examiner view` |
| **0042-R1-3** | external 1 | no independent outcome judge and no question-level reference labels (§§3, 4B; INV-4/6) | travelled to 0043: the adjudication rubric with reference cases, later replaced by the interpretation stage (A3-ter/A3-quater); 0043 v1 §4B | `git show 1bc29178014016d040e8cdb1ee92d81420970244 -- specs/0043-refusal-harness.md # v1 A3 — the rubric` |
| **0042-R1-4** | external 1 | installed instrumentation was not separated from observed traffic (§4A-0/A; INV-1/2) | Part A-0 gained the three sets and Part A-1 the six-status state table (UNREACHED vs UNEXERCISED vs UNMEASURED; DISABLED as a status) — parsed from the spec by the evidence, not hand-listed | `$PY -m pytest tests/test_0042_evidence.py::test_a1_state_table_is_parsed_from_the_spec_and_the_code_conditions_match_it_one_to_one tests/test_0042_evidence.py::test_a1_every_tuple_maps_to_exactly_one_status_in_precedence_order` |
| **0042-R1-5** | external 1 | the counter lifecycle and the observation-only contract were incomplete (§§4A, 5, 7, 10; INV-2/7) | Part A-2: the counter lifecycle, the three-arm decision-trace diff over exactly (seq, site_id, decision) with its bound stated | `$PY -m pytest tests/test_0042_evidence.py::test_a2_three_arm_trace_diff_compares_only_the_named_fields_and_refuses_extra_ones` |
| **0042-R1-6** | external 1 | the baseline treatment was unspecified (§4B step 3; INV-5) | travelled to 0043: the baseline arm, replaced three times (merged prompt → examiner view → the CAPTURED model input under a stated transform, A6-ter), the history in 0043 §11 | `git show 1bc29178014016d040e8cdb1ee92d81420970244 -- specs/0043-refusal-harness.md # v1 A6 — the first baseline definition` |
| **0042-R2-1** | external 2 | the AST inventory could not support the completeness claim: candidate discovery, reviewed enforcement points and installed instrumentation were one undifferentiated set | Part A-0-bis: DISCOVERED (derived by the inventory: RAISE, RETURN_FALSE, RETURN_NONE, BOOL_RETURN, FILTER_RETURN), REVIEWED (recorded decisions), DECLARED; the three-sets check refuses on this tree because no decisions exist yet | `$PY -m pytest tests/test_0042_evidence.py::test_a0bis_the_three_sets_check_refuses_each_wrong_pair_and_passes_the_complete_fixture tests/test_0042_evidence.py::test_a0bis_on_the_real_tree_the_third_source_bites_because_no_decisions_exist_yet tests/test_0042_evidence.py::test_a4_discovery_finds_the_four_symbols_round_2_named_and_states_its_unit` |
| **0042-R2-2** | external 2 | the census schema and the comparison contract were inconsistent across prose, schema and tests (statuses 4 vs 5; invalid counts; the compared trace fields unnamed) | Part A-1 is the single authority: the state table parsed from the spec with the count cross-checked against the prose; the report gate refuses every named defect; Part A-2 names the compared fields | `$PY -m pytest tests/test_0042_evidence.py::test_a1_parser_refuses_a_missing_table_and_a_count_that_disagrees_with_the_prose tests/test_0042_evidence.py::test_a1_report_gate_refuses_every_named_defect_and_emits_the_undeclared_row` |
| **0042-R3-1** | external 3 | reviewed and declared does not establish installed: with every candidate reviewed, every point declared and no counters at all, the reconciliation passed | Part A-0-ter derived INSTALLED from a static scan checked by the import-time registry — itself found a proxy in round 4 and replaced by A-0-quater (the binding); see 0042-R4-1 | `git show 43c1c637cef4372dadcf315a23f06ae8e1c8100d -- specs/0042-exercised-guarantees.md # v6 Part A-0-ter` |
| **0042-R3-2** | external 3 | A5 bounded: disabling measurement allowed an undeclared reporter to pass | structural reconciliation runs BEFORE status and does not depend on `enabled`: an undeclared reporter under enabled == false is emitted DISABLED and refused | `$PY -m pytest tests/test_0042_evidence.py::test_a5_an_undeclared_reporter_is_refused_even_when_measurement_is_off` |
| **0042-R3-3** | external 3 | observation-only evidence: (seq, site_id, decision) supports branch-sequence equivalence only; replay inputs and execution conditions must be frozen and the bound stated | Part A-2 states the bound (branch-sequence equivalence under frozen inputs; results and state checked separately); the trace key refuses records carrying anything else | `$PY -m pytest tests/test_0042_evidence.py::test_a2_three_arm_trace_diff_compares_only_the_named_fields_and_refuses_extra_ones` |
| **0042-R4-1** | external 4 | registration does not establish working instrumentation: a declare_site call is a proxy for a counter bound to the decision — both fixture decisions executed, every counter stayed at zero, the report read UNREACHED; the deletion control deleted the declaration on a fixture with no counters | Part A-0-quater: the decision is expressed THROUGH the site; INSTALLED = the scan of the binding; the runtime assertion is the reviewer's own test; the controls with the naming defect fixed | `$PY -m pytest tests/test_0042_evidence.py::test_a0quater_the_reviewers_round4_test_executing_both_decisions_moves_both_counters_and_reads_exercised tests/test_0042_evidence.py::test_a0quater_strip_the_binding_keep_the_declaration_refuses_and_consult_without_fire_refuses tests/test_0042_evidence.py::test_a0quater_registered_but_unbound_is_refused_by_the_registry_check_as_registered_not_installed` |
| **0042-R5-1** | external 5 | the binding scan accumulated method uses across the whole module by variable name: consult() in one function and fire() in another read as bound; an already-positive counter must not establish that a later decision was measured | the binding is function-local and scope-aware (nested functions are their own scope; a shadowed name is not the site); the runtime assertion is over DELTAS around the particular decision; the split-function, nested and shadowed mutants refuse | `$PY -m pytest tests/test_0042_evidence.py::test_a0quater_round5_the_binding_is_function_local_and_scope_aware tests/test_0042_evidence.py::test_a0quater_the_reviewers_round4_test_executing_both_decisions_moves_both_counters_and_reads_exercised` |
| **0042-R4-2** | external 4 | advisory: consolidating the superseded passages would help prevent old installation wording from being mistaken for current requirements | acknowledged at v7 with §11 (superseded decisions out of the normative body) — and round 5 found the class still present, so the record shows the ask twice; closed at v8 (see 0042-R5-2) | `git show a9d3622d6252a19387b2ecb66a665f101825fb36 -- specs/0042-exercised-guarantees.md # v7 §11` |
| **0042-R5-2** | external 5 | superseded normative wording still readable as live requirements — the class the reviewer named in round 4 and again at acceptance ("finish removing superseded normative wording") | removed at v8: the diff moves the contiguous superseded blocks out of the normative body into §11 (the 'inspected subset' comparison; the A-0-ter INSTALLED definition); the history stays in §11 | `git show c6dd4078b877088684b381add72fe08feb1354b4 -- specs/0042-exercised-guarantees.md # v8 — the superseded blocks moved to §11` |

<!-- /GENERATED:review-closure -->
