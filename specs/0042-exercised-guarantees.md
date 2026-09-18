# Feature spec: exercised guarantees — measuring whether what we specify is what runs

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-61), each adoption at rest and re-read from the file, dated per entry: v3.1 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 28068200aa6f90fa); v4 2026-09-18 from the same file (sha16 0fd0af01bfb56a39); v5 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 f8cf6f68e0016625); v6 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 ba262106068d3efc) |
| **Version** | **v6 — THE ROUND-3 VERDICT FOLDED. Both specs returned again “with three remaining design blockers”; the census owed A4, and the reviewer ruled A1/A2/A5 need no further architectural redesign — bounded obligations, *“not invitations to reopen the design”*.** **A4 → Part A-0-ter: INSTALLED IS DERIVED FROM THE CODE.** Round 3 showed that REVIEWED + DECLARED does not establish it — with every candidate reviewed, every point declared and NO counters at all, the reconciliation passed and yielded valid `UNREACHED` rows, **identical for installed-but-unused and for instrumentation never installed.** 🔴 *The cause is a rule A-0-bis STATED and then violated in the same section: it wrote that two authored lists agreeing proves consistency and not completeness, and then rested INSTALLED on those same two lists. The third set was derived; the fourth quantity was not.* **`INSTALLED` is now a static scan of the source, with the import-time registry as the CHECK ON the scan rather than a second opinion, and the reconciliation runs over FOUR sets.** **The reviewer's own demonstration is the standing control** — delete a counter while keeping its decision and declaration and the report must REFUSE, while installed-but-unused stays `UNREACHED`. **A5 → A-1: structural reconciliation runs BEFORE status and does not depend on `enabled`**, in dev's words verbatim, because the validator does this and the spec should BE its behaviour rather than agree with it. **A-0-bis annotated, not rewritten** — its sets and refusals stand and only INSTALLED's definition moved, with the superseded row struck through so a later reader sees what was tried. **This cell states what changed and where and restates no figure.** Prior: v5 · v4 · v3.1 · v3 · v2 · v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — §4's counters sit in `gate.py`, `graph.py`, `lifecycle.py`, `ingest.py`, `schema.py`, all guarded |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 0042. 🔴 **CORRECTED v4 (round-1 carrier finding C2, research's): v3.1 said “0040 is free but was VACATED”. IT IS NOT FREE — `specs/ALLOCATION.md` records it under the column `spent on`, consumed by the WITHDRAWN procedural-text proposal.** Vacated and free are different states and this cell asserted the wrong one against the registry. *(Found by the external reviewer. Research had swept 63 `0040` references across 21 files the same night and classified THIS line as correct — by asking whether the file explains the renumbering rather than whether the sentence agrees with the registry. A category check where a content check was owed.)* **0042 is this spec; the refusal harness takes its own number from `allocation.py --next` at adoption.** |

---

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
> 🔴 **SUPERSEDED BY PART A-0-bis (round-2 A4).** v4 said the declaration is compared against an “inspected subset” of this inventory — which round 2
> showed contradicts INV-2d's refusal on any absent site, since 636 syntactic candidates would then all need declaring. **The comparison is against the
> REVIEWED set, and the inventory forces a DECISION rather than a declaration.** The sentence that stood here said
> and the inspection is work this spec requires rather than evidence it already
> has.
>
> **What it does establish, and what 162 could not:** the domain is **measured**,
> its boundary is **stated** (every module under `src/veracium`, named in the
> evidence output, so a reader can see what was not scanned), and its unit is
> **one AST node of a listed kind** with identity `(module, qualname, line)`.
> *Nobody chose which files to look at.*

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
| **INSTALLED** | ~~the declaration plus the ids that report at runtime~~ → 🔴 **A STATIC SCAN OF THE SOURCE for `declare_site(…)` calls, checked against the import-time registry (A-0-ter)** | 🔴 **nobody** — *round 3 showed “declaration + reporting ids” is satisfied by code with no instrumentation at all* |

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
| **SCAN** | a **static AST pass for `declare_site(…)` calls**, yielding `(id, module, qualname, line)` | **nobody** — derived from the source |
| **REGISTRY** | the **import-time record**: each `declare_site(id)` registers when its module loads | **nobody** — produced by execution |

**`INSTALLED` = the SCAN.** *The code either carries the instrumentation or it
does not, and that is a fact about the source rather than about a list.*

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
dangling from the moment the candidate was renamed — and `test_spec_gate` checks
backticked `.py` names ONLY, so this `.md` would have shipped silently.* *0040 is spent, 0042 is this spec; a filename is not an
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

## 9. Brief for the external reviewer

🔴 **ROUND 2, and the round-1 questions are both RETIRED rather than re-asked.**
v3.1 asked whether the denominator argument was sound and whether class 3 was
well-posed. **The reviewer answered both: the denominator argument was
OVERSTATED, and class 3 IS well-posed** provided the answer has only
non-assertable support under the applicable policy. *The first answer is why this
spec is now the census alone; the second travelled with the harness.*

**What round 2 asks instead, all census-side:**

1. **Is the AST inventory an adequate third source?** INV-2c/2d rest on it being
   authored by nobody. It is derived from the code it measures — **does that make
   it independent of the declaration, or merely independent of the declaration's
   AUTHOR?**
2. **Is `DISABLED` sufficient to keep an unmeasured deployment from reading as a
   measured one?** It is a status per id rather than a report-level flag,
   deliberately — but the reviewer's amendment 5 warned that incomplete counters
   must not yield apparently valid totals, and we would rather be told early if a
   status is too weak a carrier for that.
3. **Does the three-arm trace diff (healthy · failing · UNINSTRUMENTED) actually
   establish observation-only**, or does the uninstrumented arm differ for reasons
   that have nothing to do with the census?

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
