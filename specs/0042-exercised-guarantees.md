# Feature spec: exercised guarantees — measuring whether what we specify is what runs

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-61), adopted at rest and re-read from the file: v3.1 2026-09-18 from `0042-exercised-guarantees-CANDIDATE.md` (sha16 28068200aa6f90fa) |
| **Version** | **v3.1 — two figures corrected in dev's pre-adoption re-derivation window, BOTH mine and BOTH unit errors: `127×` was `grep -rc` SUMMED, which counts LINES not occurrences; `163` was asserted with no recipe and is unreproducible. Neither argument changes; both numbers do.** **v3 — dev's internal read folded: F1–F6 before external review, F7's wording taken.** 🔴 **F1 was load-bearing and v2 was wrong: the "invariant registry" the census derived its expected set from DOES NOT EXIST** (`INV-` **0× in `src/`**, and in `specs/` it is **0041's alone** — 117 occurrences in that spec, 48 more in its ledgers and evidence; **no other spec uses the prefix at all**), and it cannot be scraped from §6 either — the id is embedded in prose rather than a column, and the vocabulary has two families: **a grammar requiring a digit drops 177 of 641 ids; one that does not degenerates to counting names** (definition given EXECUTABLE in §4a after three rounds of seat disagreement — 181 was mine, pre-dedup). The declaration is now CREATED BY THIS SPEC, and INV-1 gains a second independent source. F2: *enforcement point* DEFINED as a property, with the candidate count now EXECUTABLE — **162 lines matching a lexical pattern over the five guarded files, an upper bound on candidates, not 162 confirmed sites** (v3.1; v3's **163** is withdrawn as unreproducible). F3: the baseline arm is a HARNESS construction — there is no gate-off mode and this spec does not add one. F4: `UNMEASURED` is a field, not prose. F5: `REFUSED-QUARANTINED` split out. F6: INV-7 is a decision-trace diff and names suites that reach the sites — not 0041's, which would pass vacuously. Prior: v2 — Q1 ruled, replay withdrawn · v1 — first draft |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — §4's counters sit in `gate.py`, `graph.py`, `lifecycle.py`, `ingest.py`, `schema.py`, all guarded |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 0042. **0040 is free but was VACATED** in the 0040→0041 renumbering; reusing a vacated number invites a stale reference to resolve to the wrong spec |

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

### Why the two halves are ONE spec

**Part A (the firing census)** counts how often each enforcement point executes.
**Part B (the refusal measurement)** measures how often the assertion gate
declines when it should.

They are not merely related: **Part B cannot produce a rate without Part A's
counter.** A refusal rate needs a denominator — *how many times was the gate
consulted?* — and that denominator is exactly a census count. **Shipping B
without A yields a numerator with no denominator, which is the shape of every
unfalsifiable claim this project has withdrawn.**

## 2. Field contracts touched

**No stored field changes.** Part A adds a process-local counter keyed by a
declared enforcement-point id; Part B adds no product surface at all and consumes
Part A's counters plus a fixture store.

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
| **examiner questions** (Part B) | a human or model that has NOT read the implementation | **data, never instructions.** Questions are asked through the ordinary public API; no question text reaches a prompt with authority |
| **the fixture store's records** (Part B) | includes deliberately poisoned and deliberately quarantined rows | **the material under test.** A poisoned row must be able to reach recall — excluding it in the fixture would measure the fixture |
| **enforcement-point ids** (Part A) | declared in source, read by the census | **code-supplied, not caller-supplied.** An id that is not in the derived registry is a REFUSAL, not a new row |

### 2c-ii. Assertions about reach — REQUIRED

**A census count is a statement about ONE deployment's runs, never about the
mechanism in general.** A zero from our fixture corpus says *"our corpus never
presented the condition"*, not *"this guard cannot fire"*. **The two must never
be collapsed** — the second requires a reachability argument over the code, which
this spec does not attempt.

## 3. Trust-class matrix — REQUIRED, blocking

| class | may the census count it? | may Part B ask about it? |
|---|---|---|
| **first-party stated** | yes | yes — the ANSWERED baseline |
| **third-party / unverified** | yes | 🔴 **yes, and this is the contribution** — the question class where the answer IS present and MAY NOT be asserted |
| **quarantined** | yes | yes — must produce REFUSED-UNTRUSTED, never ANSWERED |
| **redacted / absent** | yes | yes — must produce REFUSED-ABSENT |
| **counts themselves** | **carry no record content** — an id and an integer, nothing else (§7) | n/a |

## 3b. Authorization and scope

The census is **observation-only and cannot alter a decision** (INV-7). It has no
authorization surface of its own: it reads what the host already computes. Part B
runs against a fixture store, never a live user store.

## 4. Behaviour

### Part A-0 — what an ENFORCEMENT POINT is, and where the expected set comes from

🔴 **Both were undefined in v2 and both are load-bearing.**

**DEFINITION.** An enforcement point is **any site that can return a decision
other than the caller's request** — refuse, quarantine, withhold, abstain,
downgrade. **It is a property, not a choice.** v2 said *"each enforcement point
declares a stable id"* without saying which sites those are, which made the
census's domain "whatever someone instrumented" — **a hand list one level up, in
the spec written to kill hand lists.** The domain is far larger than the five
mechanisms §1 names — **and, per this spec's own argument about ids, the count is
given EXECUTABLE rather than asserted:**

```bash
# over the five guarded files graph.py ingest.py schema.py gate.py lifecycle.py
grep -cE '^\s*raise |refus|quarantin|withh|abstain|downgrade' <file>
#   graph 45  ingest 50  schema 56  gate 8  lifecycle 3   =  162
```

> 🔴 **STATED AS WHAT IT IS: 162 LINES matching a lexical pattern, NOT 162
> confirmed enforcement points.** It counts comments and docstrings, so it is an
> **UPPER BOUND on candidates** and the per-site confirmation is Part A's work,
> not a premise of it. **The argument needs only that the domain is ≫ 5**, and it
> is: even if most of the 162 fall away, the five §1 names do not describe it.
>
> *(v3.1: v3 said **163**, asserted with no recipe. Two seats independently reach
> **162** under the pattern above — dev's five-file refuse/quarantine split sums
> to the same. **The 163 is WITHDRAWN as unreproducible; I could not re-derive my
> own figure, which is precisely the defect §2 raises about ids.**)*

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
   `{id, status, consulted, fired, errors}` where **`status` is one of
   `EXERCISED` · `UNEXERCISED` · `UNMEASURED`** — including ids with zero, named.
   🔴 **`UNMEASURED` is a FOURTH state and it needs its own field.** v2 put it in
   §7 prose while the row shape was `{id, consulted, fired}`, so **a counter that
   raised before incrementing rendered as `consulted=0` → UNEXERCISED** — the
   ok-vs-na collapse this spec names at §10.1, inside its own report.
4. A declared id absent from the report is a **failure of the census**, not a
   zero (INV-1).

### Part B — the refusal measurement

1. A **blind examiner** writes N questions from `introspect`'s listing alone
   (*v2 said "the store's INDEX", which names no surface*), never having read the
   gate, this spec, **or the fixture's trust manifest** (INV-6). Question
   authorship is recorded.
2. Four classes, fixed in advance: **present-and-trusted** · **absent** ·
   🔴 **present-but-untrusted** · **present-but-quarantined**.
3. Each question is asked of (a) Veracium as shipped and (b) a **baseline arm**
   — the confabulating control. 🔴 **THE BASELINE IS A HARNESS CONSTRUCTION, NOT
   A PRODUCT MODE.** There is no gate-off switch and this spec does not add one:
   zero hits in `src/` for any gate-disable flag, and the gate is consulted at
   `__init__.py:1593`. The arm is built **in the harness** by merging the
   grounded and unverified partitions into one prompt and answering from that —
   **never through `Memory.recall`**. *"Gate off" reads as a switch; a switch
   would be a trust-surface change needing its own §3 row, and §2's "Part B adds
   no product surface" would become false.*
4. Every answer resolves to exactly one of **ANSWERED / REFUSED-ABSENT /
   REFUSED-UNTRUSTED / REFUSED-QUARANTINED / OTHER**, where OTHER (errored,
   timed out, fell silently through) is **its own bucket and is never folded into
   a refusal** (INV-4). **`REFUSED-QUARANTINED` is separate from
   `REFUSED-UNTRUSTED`**: v2 gave classes 3 and 4 distinct question classes and
   one shared bucket, so a reader could not tell an intended outcome from a
   mis-classification.
5. The report states the rate **with its denominator** and the baseline arm
   beside it. A rate without a baseline is void (INV-5).

> **The contribution is class 3.** Everyone can refuse what is absent.
> **Refusing what is PRESENT AND UNTRUSTED is the claim we make and have never
> measured**, and it is the case where a grounded system with no trust surface
> answers confidently and wrongly.

## 5. Regime analysis

| regime | behaviour |
|---|---|
| **fixture corpus** | the only regime Part B claims; results are scoped to it |
| **a store where a class never occurs** | the census reports UNEXERCISED; Part B reports that class as **NOT PRESENTED**, never as 100% |
| **long-running host** | counters are process-local and reset on restart; a census is a statement about one process's lifetime (§8) |
| **concurrent recalls** | counts may interleave; the census claims totals, never per-request attribution |

## 6. Invariants and executable checks — REQUIRED, blocking

| id | invariant | executable check |
|---|---|---|
| **INV-1** | **CENSUS-TOTAL, FROM TWO INDEPENDENT SOURCES** — every id in the DECLARATION appears in the report, and every reporting id is declared | add a declared id with no site → report REFUSES; add a site with no declared id → report REFUSES. **Both directions, or the check is one source comparing with itself** |
| **INV-2** | **ZERO-IS-A-VERDICT, AND AN ERROR IS A THIRD ONE** — zero → `UNEXERCISED` with the id named; a counter that raised → `UNMEASURED`; never omitted, never `ok` | two fixtures: a never-fired guard asserts `UNEXERCISED`; **a FORCED-RAISE counter asserts `UNMEASURED` and must NOT render `UNEXERCISED`** |
| **INV-3** | **DENOMINATOR-BEFORE-RATE** — no rate without its denominator; a zero denominator reports **UNDEFINED**, never `0%` | assert `UNDEFINED` on an unconsulted gate |
| **INV-4** | **THREE-OUTCOMES-PLUS-OTHER** — every question resolves to exactly one bucket; OTHER is never folded into a refusal | inject a timeout; assert it lands in OTHER and the refusal rate is unchanged |
| **INV-5** | **BASELINE-REQUIRED** — a refusal measurement without a comparison arm is void | assert the report REFUSES to emit a rate when the baseline arm is missing |
| **INV-6** | **BLIND TO THE TRUST CLASS, not only to the implementation** — the examiner writes from the record's PRESENCE alone; the trust class is attached afterwards from the fixture manifest, never by the examiner. Questions authored with either kind of knowledge are excluded AND counted | assert the excluded count is reported, not silently dropped. 🔴 *If the examiner knows a record is untrusted while writing the question, the question is about the GATE and not about the STORE, and the measurement collapses into testing* |
| **INV-7** | **OBSERVATION-ONLY** — no counter may alter a decision | **a DECISION-TRACE DIFF, not a green run**: capture the decision trace with counters healthy and with them forced to error, and assert the two are **byte-identical**. Name the suites that actually reach the instrumented sites — **0027's (graph.py) and the gate/ingest/schema suites**. 🔴 **NOT 0041's**: it is accepted and UNIMPLEMENTED, its tests are frozen-record transition tests with eleven strict xfails, and none exercises a gate decision — **forcing counters to error there changes nothing they can observe, so that half would pass vacuously** |
| **INV-8** | **COUNTS CARRY NO CONTENT** — a census row is an id and integers | assert no record text, user id, or digest appears in the report |

**Each check must be demonstrated RED** against a deliberately wrong
implementation before it is accepted — an undemonstrated control is the defect
this spec exists to find.

## 7. Failure modes and reversibility

| failure | consequence | reversal |
|---|---|---|
| a counter raises | 🔴 **must not fail the caller** — the decision is the product; the measurement is not. The row's `status` becomes **`UNMEASURED`** and `errors` increments (§4 step 3), which is a FIELD and not prose | remove the counter; no stored state |
| the registry and the call sites drift | INV-1 turns it into a refusal rather than a silent gap | — |
| the fixture is unrepresentative | Part B's rate is scoped to the fixture and says so (§2c-ii) | re-run on a new corpus |
| counts leak content | INV-8; counters take an id and an integer only | — |

**Fully reversible.** No schema change, no stored field, no migration.

## 8. Claims and limits

**Claimed:** for a named corpus and a named process lifetime, the rate at which
each declared enforcement point was consulted and fired; and the rate at which
the assertion gate declined on four fixed question classes, beside a baseline arm.

**NOT claimed:**
- that a zero-count guard cannot fire — only that **this corpus never presented
  the condition** (§2c-ii)
- that the fixture generalises to a production store
- any comparison to another system's published refusal figures: **different
  corpora, different question sets, no shared axis** — the numbers must not share
  a table
- an answer-quality claim. **This measures REFUSAL, not correctness** — a system
  that refuses everything scores perfectly here and is useless, which is why the
  ANSWERED-on-present-and-trusted class is reported beside it

## 9. Brief for the external reviewer

Two questions above all. **(1) Is the denominator argument sound** — is a
refusal rate meaningful only relative to consultations, and does §4's `consulted`
counter measure that? **(2) Is class 3 (present-but-untrusted) well-posed**, or
does asking a question whose answer is present-but-untrusted smuggle in an
assumption about what the gate *should* do? We believe it is the whole point;
we would rather be told early if it is circular.

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
   - **cannot produce a denominator.** §1's own argument for shipping the halves
     together is that a rate without one is the shape of every unfalsifiable
     claim we have withdrawn. Replay supplies the numerator only
   - **sees one mechanism.** Supersession, correction, `forget_user`, quarantine
     promotion and the reserve write no `policy_receipt`; the candidate set is
     five and receipts cover one

   **Consequence, accepted with the ruling: `Path: full`, external review
   required** (the counters land in guarded files). **The replay variant is
   withdrawn, not deferred** — keeping it as a fallback would invite a later
   seat to take the cheap half and report zeros it cannot see.
2. **Always-on or opt-in?** Always-on gives real numbers and a permanent cost;
   opt-in gives numbers only where someone already suspected a problem — which is
   how we have been finding these by hand.
3. **Should `policy_receipt` carry the enforcement-point ids?** It would make the
   census durable and queryable rather than process-local — but it is a schema
   change and 0027 v14 has just shipped.
4. **Who is the blind examiner?** A person is ideal and expensive; a model that
   has not read the implementation is cheap and its blindness is harder to prove.
5. **How many questions per class** before a rate is worth publishing?
   `distill-kura` reported n=6 on its refusal class — blind, and small.
