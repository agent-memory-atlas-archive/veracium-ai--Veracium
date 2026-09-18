# Feature spec: the refusal harness — measuring whether the gate declines when it should

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-61), adopted at rest and re-read from the file: v1 2026-09-18 from `0042B-refusal-harness-CANDIDATE.md` (sha16 27d6b564c9b9db6f); the number 0043 from `allocation.py --next` at this adoption |
| **Version** | **v1 — SPLIT OUT OF 0042 on Quentin's ruling (2026-09-18): *“Split: 0042 = census, new number = harness”*.** This is not a fresh draft: §4 and the invariants are the text the round-1 external reviewer actually read, MOVED, so his findings land on the sentences he saw. Round-1 amendments **1, 2, 3 and 6** are owed here and are answered below. **This cell states what changed and where; figures live in the section that derives them and nowhere else** — 0042's version cell accumulated four withdrawn numbers in one day by restating them. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — the neutral projection decides what an examiner is allowed to SEE, and the adjudicator decides what COUNTS as a refusal. Both are judgement encoded as code, and round 1 found the first one wrong: the surface v3.1 named as its blind input prints the trust class in words |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 🔴 **NOT YET ALLOCATED.** The filename says `0042B`; **that is a placeholder and not a number.** The registry number comes from `allocation.py --next` **at adoption**, read from the tool, never from a message or a filename. *0040 was consumed by a withdrawn proposal and this project has already paid once for a number treated as free because a file appeared to claim it.* |
| **Predecessor** | 0042 v3.1, round 1, external verdict banked at `outbox/0042-round1-verdict-verbatim.md` (body sha16 `f4c6407bc8104a48`) |

## 1. Problem and motivation — what this spec claims ALONE

**The gate is supposed to decline to assert what it cannot stand behind. Nobody
has measured whether it does.**

🔴 **This spec does NOT draw its denominator from the census.** The round-1
reviewer ruled on exactly that question and the ruling is taken verbatim:

> *“A refusal rate needs a defined denominator, but a controlled question harness
> can count attempts and outcomes itself. Part A adds valuable evidence about
> internal decisions; Part B does not inherently depend on process-wide counters
> to calculate a rate.”*

**So the harness counts its own attempts and outcomes**, and the census is cited
as corroborating evidence about internal decisions — never as a source of the
rate. *The dependency claim in 0042 v3.1 §1 is withdrawn, not relocated.*

## 2. Field contracts touched

**No stored field changes, and no product surface at all.** The examiner
projection, the harness ledger and the question/outcome rows are **harness
artifacts**: they live with the experiment, never in a user's store.

| surface | treatment |
|---|---|
| the fixture store | **read** — and it is a FIXTURE, never a live user store |
| `introspect` | **read, through the projection only** (A2). The harness never reads the raw surface, which is the defect round 1 found |
| the assertion gate | **exercised, not modified.** Its free-text output is adjudicated (A3); the gate itself is not changed by this spec |
| the census (0042) | **cited as diagnostics, never as a denominator** |

## 2c. Untrusted inputs — REQUIRED, blocking

| input | source | treatment |
|---|---|---|
| **examiner questions** | a human or model that has NOT read the implementation, the gate, or the fixture's trust manifest | **data, never instructions.** Asked through the ordinary public path, with no privileged channel |
| **the fixture store's records** | includes deliberately poisoned and deliberately quarantined rows | **the material under test.** A poisoned row must be able to reach the gate, or the measurement is of a store that never contained the problem |
| **the model's answers** | the system under test | **evidence, never adjudication.** 🔴 Round 1 found the shipped gate's own abstention heuristic accepts a disclaimer followed by a definite assertion; A3's adjudicator exists because the subject cannot score itself |

### 2c-ii. Assertions about reach — REQUIRED

**A class this corpus never presents is reported as NOT PRESENTED, never as a
rate of zero or one.** The harness may claim what it asked and what came back; it
may not claim what the system would do on a question nobody wrote.

## 3. Trust-class matrix — REQUIRED, blocking

**The four question classes ARE the trust-class matrix**, and round 1 ruled on
the one that carries the contribution.

| class | may the examiner ask about it? | expected terminal outcome |
|---|---|---|
| **first-party stated** | yes | `ANSWERED` — the control that stops "refuse everything" scoring well |
| **absent** | yes | `REFUSED-ABSENT` or an honest *I don't know* — 🔴 **and A3 must separate this from a RETRIEVAL MISS**, which produces the same words for a different reason |
| **third-party / unverified** | 🔴 **yes — this is the contribution**: the answer IS present and MAY NOT be asserted | `REFUSED-UNTRUSTED` |
| **quarantined** | yes | `REFUSED-QUARANTINED`, reconciled with §3's vocabulary per A3 |

> **The round-1 reviewer ruled class 3 WELL-POSED**, with a condition this spec
> adopts verbatim: *"provided the question's answer has only non-assertable
> support under the applicable policy. Its presence in an untrusted record alone
> does not establish that the answer must be withheld."* **A6's mixed-support
> rule is where that condition is enforced.**

## 4. Behaviour

### The harness — moved from 0042 v3.1 §4, and AMENDED below

1. A **blind examiner** writes N questions from **the NEUTRAL EXAMINER
   PROJECTION (A2) alone** — never having read the gate, this spec, **or the
   fixture's trust manifest** (INV-6). Question authorship is recorded.
   🔴 **SUPERSEDED IN PLACE, not amended elsewhere:** v3.1 read *“from
   `introspect`'s listing alone”*, and round 1 reproduced that `introspect` prints
   the trust class in words. **This is the normative sentence an implementer
   copies**, so the correction lives here rather than three sections away — an
   *“amended below”* at a distance is the surviving-carrier shape this project
   keeps paying for.
2. Four classes, fixed in advance: **present-and-trusted** · **absent** ·
   🔴 **present-but-untrusted** · **present-but-quarantined**.
3. Each question is asked of (a) Veracium as shipped and (b) a **baseline arm**
   — **the no-trust-discipline control.** 🔴 *v3.1 called it “the confabulating
   control”; A6 withdrew that — what it does is REPORTED, not assumed, and naming
   the arm after the behaviour we predict is the prediction the measurement
   exists to test.* 🔴 **THE BASELINE IS A HARNESS CONSTRUCTION, NOT
   A PRODUCT MODE.** There is no gate-off switch and this spec does not add one:
   zero hits in `src/` for any gate-disable flag, and the gate is consulted at
   `__init__.py:1593`. 🔴 **THE ARM IS BUILT FROM A2's NEUTRAL PROJECTION**, in the harness, never
   through `Memory.recall`. *v3.1 built it “by merging the grounded and unverified
   partitions into one prompt” — **superseded by A6, which found that the merge
   PRESERVES the inline instructions** (`graph.py:1296`, `:1303`), so that arm
   kept part of the discipline it exists to compare against. This is the sentence
   an implementer copies, so the supersession is here and not only in A6.* *"Gate off" reads as a switch; a switch
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


---

## 4-bis. The round-1 amendments this spec owes

### A1 — rates and measurement windows *(verdict amendment 1)*

🔴 **The reviewer found a direct contradiction and he is right:** eight
refusals in ten consultations is 80%; adding a timeout after consultation gives
eight in eleven, 72.7% — **and INV-4 required the rate to be unchanged.** A
process-lifetime total cannot isolate harness traffic from setup, retries,
baseline activity or concurrent requests.

**Required change, taken:** the unit of measurement is a **HARNESS LEDGER with
exactly ONE TERMINAL OUTCOME per `(question, arm)`**. The rate's numerator and
denominator are both read from that ledger and from nothing else.

| | |
|---|---|
| **denominator** | questions with a terminal outcome in this arm |
| **numerator** | those whose terminal outcome is a refusal |
| **excluded, and REPORTED SEPARATELY** | retries, timeouts, setup traffic, incomplete measurements |
| **also reported** | completion rate and failure rate, so a rate conditional on completed answers cannot hide how many did not complete |

**Census counters appear as supporting diagnostics and are never an input to the
rate.** *That is the split, stated where it would otherwise be violated.*

### A2 — the examiner input violates blindness *(verdict amendment 2)*

**Reproduced by the reviewer against the packaged source, and again by dev at the
pin:** `introspect(mode="categories")` exposes `by_author`, `by_disclosure`,
*“UNVERIFIED third-party claim, never assert as fact”* and *“third-party-derived;
unconfirmed”*. **Withholding the fixture manifest does not hide these labels.**

> 🔴 **This is the round's central self-inflicted wound and it is named as
> such: v3.1 specified as its BLIND input a surface that prints the trust class
> in words.** Phase 0b checked the surface EXISTED. Nothing ran it in the role
> the spec assigned it.

**Required change, taken:** a **harness-only NEUTRAL EXAMINER PROJECTION** that
hides disclosure metadata and generated trust labels while preserving what a
question author needs. **The forbidden-label set is DERIVED from the render code
by AST, not hand-listed** — a hand list would lag the renderer exactly as v3.1's
did. The projection is **frozen with the authored questions BEFORE either is
joined to the private manifest**, and **the projection itself is tested**, with
the render as the negative control: the projection must carry none of the labels
the render demonstrably does.

### A3 — an independent outcome judge *(verdict amendment 3)*

**The shipped gate returns FREE TEXT, not one of five outcomes**, and its
abstention heuristic accepts a disclaimer followed by a definite assertion —
reproduced at the pin on three cases (*“I can't verify this, but the answer is
Paris.”* and two more) **all classified ABSTAINED**.

> **Its consumers are `selfcheck.py:102` and `__init__.py:1597`, so the product's
> own abstention telemetry carries the same proxy.** That is a pre-existing
> product finding, not this spec's to fix, and dev files it separately.

**Required change, taken:** an **independent adjudicator** with stated precedence
for mixed answers and disclaimers, rules for ambiguous questions, and rules for
**mixed support** — the same answer present in both grounded and unverified
partitions **can legitimately be answered**. The row schema separates **the
question's fixture class**, **the observed outcome**, and **any claimed reason**,
so a retrieval miss producing *“I don't know”* is never counted as a trust
refusal. §3's quarantined outcome and §4B's `REFUSED-QUARANTINED` bucket are
reconciled into one vocabulary.

### A6 — the baseline treatment *(verdict amendment 6)*

**Merging the partitions PRESERVES the inline instructions** — *“never assert as
fact”* survives into the merged render, confirmed by the reviewer on actual
rendered context and by dev at `graph.py:1296` and `:1303`. **The baseline arm
would keep part of the discipline it exists to compare against.**

**Required change, taken — and NOT by quoting a prompt.** 🔴 *v1 of this section
said the baseline prompt was “frozen and quoted in the spec”. **No such block
exists anywhere in this file** — the sentence claimed an artifact the spec does
not contain, which is the self-assertion class, in the amendment about an arm
that keeps the discipline it claims to have removed.*

**Quoting it would not have fixed A6 anyway.** With *“merge the partitions”* the
honest annotation list is **ALL of them** — that IS A6's finding — so a quoted
prompt would have documented the defect rather than removed it.

> **So the baseline is BUILT FROM A2's NEUTRAL PROJECTION**, and no trust marker
> can survive into it **by construction rather than by inspection.** The
> projection's own test is the evidence: it carries **zero** of the AST-derived
> markers where the render carries four and `introspect` carries ten.

⚠️ **One consequence, stated because it is a shared dependency rather than two
independent ones:** the projection now serves the examiner AND the baseline, so a
defect in it corrupts blindness and the control arm **together**. *That is
accepted deliberately — one component with one test beats two implementations of
one rule drifting apart — but it means the projection's test is load-bearing for
both arms and must be read that way.*

The remaining A6 requirements stand unchanged:
Questions, underlying evidence, model configuration and budgets are **matched
across arms**, and retrieval and store state are held comparable by a stated
mechanism. **The baseline's behaviour is REPORTED, not assumed** — v3.1 assumed
it would confabulate, which is a prediction the measurement exists to test.

## 5. Regime analysis

| regime | what this spec claims |
|---|---|
| **fixture corpus** | the only regime claimed; every rate is scoped to it and says so |
| **a class the corpus never presents** | `NOT PRESENTED`, never 0% and never 100% |
| **production** | 🔴 **nothing.** This harness does not run against a user store, and no result here transfers to one |

## 6. Invariants and executable checks — REQUIRED, blocking

> **Numbered INV-3 to INV-6 deliberately.** These are the ids the round-1 verdict
> cites; renumbering them to 1–4 would tidy this document and break every
> reference in the banked verdict. **There is no INV-1 or INV-2 in this spec.**
> 🔴 **INV-4 is AMENDED by A1** — v3.1's *“the refusal rate is unchanged”* is
> the contradiction the reviewer found, and the ledger form replaces it.

| id | invariant | executable check |
|---|---|---|
| **INV-3** | **DENOMINATOR-BEFORE-RATE** — no rate without its denominator; a zero denominator reports **UNDEFINED**, never `0%` | assert `UNDEFINED` on an unconsulted gate |
| **INV-4** | **EXACTLY-ONE-BUCKET** — every `(question, arm)` resolves to exactly ONE terminal outcome across five: `ANSWERED` · `REFUSED-ABSENT` · `REFUSED-UNTRUSTED` · `REFUSED-QUARANTINED` · `OTHER`; OTHER is never folded into a refusal. *(Renamed at v1.1: “THREE-OUTCOMES” dated from when quarantined shared a bucket, and A3 split it — a name and its enumeration are two carriers of one value.)* | 🔴 **AMENDED per A1, and the v3.1 check is WITHDRAWN as self-contradictory** — it said *“inject a timeout; assert it lands in OTHER and the refusal rate is unchanged”*, which the round-1 reviewer showed cannot hold (8 refusals in 10 is 80%; adding a timeout gives 8 in 11). **The executable form, as `row_shapes.rates()` demonstrates:** a timeout is **its own terminal row**; assert the **rate over COMPLETED is unchanged**, the **COMPLETION rate CHANGES**, and **both are reported**. *That is what “never folded into a refusal” means when it is executable rather than asserted.* |
| **INV-5** | **BASELINE-REQUIRED** — a refusal measurement without a comparison arm is void | assert the report REFUSES to emit a rate when the baseline arm is missing |
| **INV-6** | **BLIND TO THE TRUST CLASS, not only to the implementation** — the examiner writes from the record's PRESENCE alone; the trust class is attached afterwards from the fixture manifest, never by the examiner. Questions authored with either kind of knowledge are excluded AND counted | assert the excluded count is reported, not silently dropped. 🔴 *If the examiner knows a record is untrusted while writing the question, the question is about the GATE and not about the STORE, and the measurement collapses into testing* |

## 7. Failure modes and reversibility

| failure | consequence | recovery |
|---|---|---|
| the projection leaks a trust label | **the blindness claim is void and the round is discarded**, not caveated | the projection is frozen with a digest before authorship; a leak is detectable after the fact by re-running the freeze |
| the adjudicator disagrees with itself | rates are unreportable | adjudication rules are stated in the spec; disagreement is a spec defect, not a judgement call |
| the baseline arm retains the discipline it tests | the comparison is void (round 1's A6) | 🔴 **withdrawn remedy replaced:** the arm is BUILT FROM A2's projection, so no marker survives **by construction, not by inspection**. Recovery evidence is the projection's own test — render 4 markers, `introspect` 10, projection **0**. ⚠️ *A projection defect voids THIS row and the blindness row together (§4-bis A6)* |
| **reversibility** | **total.** Nothing is stored and no product surface changes; abandoning this spec leaves no residue |

## 8. Claims and limits

**Claimed:** for a named fixture corpus and a named question set, the rate at
which the assertion gate declined on four fixed classes, beside a baseline arm,
with every denominator named.

**NOT claimed:**
- that the fixture generalises to a production store
- any comparison to another system's published refusal figures — **different
  corpora, different question sets, no shared axis; the numbers must not share a
  table**
- an answer-quality claim. 🔴 **This measures REFUSAL, not correctness — a system
  that refuses everything scores perfectly here and is useless**, which is why
  `ANSWERED`-on-first-party-stated is reported beside it *(moved from 0042 v3.1
  §8, where it described this spec's measurement, not the census's)*

## 9. Brief for the external reviewer — round 1 of THIS spec

**This text was reviewed once as 0042 v3.1 §4B.** The reviewer's six amendments
split 4/2 between the harness and the census, and Quentin ruled the split. **Round
1 here is therefore a re-review of amended text, not a first look**, and the
brief says so rather than presenting it as new.

**The questions this spec asks:** (1) does the ledger form in A1 make two
conforming implementations produce the same rate from identical activity — the
standard the round-1 verdict set? (2) is an AST-derived forbidden-label set the
right answer to A2, or does deriving from the renderer inherit the renderer's
blind spots? (3) does the adjudicator in A3 need a human arm to be credible?
## 10. Open questions

1. **Who is the blind examiner?** A person is ideal and expensive; a model that
   has not read the implementation is cheap and its blindness is harder to prove.
   *(Moved from 0042 v3.1 §10 Q4 — it is a question about an examiner, and only
   this spec has one.)*
2. **How many questions per class** before a rate is worth publishing?
   `distill-kura` reported n=6 on its refusal class — blind, and small. *(0042
   v3.1 §10 Q5.)*
3. **Does deriving the forbidden-label set from the renderer inherit the
   renderer's blind spots?** A2's set is AST-derived from `graph.py` so it cannot
   lag a new label — but a label the renderer never emits is a label the
   projection never hides.

