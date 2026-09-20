# Feature spec: the declarative grounding axis — was a fact STATED, or did we work it out?

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.3 2026-09-20 from `0045-declarative-grounding-CANDIDATE.md` (sha16 bca55cc31018d5de) |
| **Version** | **v1.3 — CITATION FORM CORRECTED (2026-09-20, pre-copy, on dev's word; no normative text changed): Part B is cited by its adopted NUMBER, 0047, not by a filename in the research tree, which dangled the moment the candidates were renamed to their allocated stems. Prior: v1.2 — PART B SPLIT OUT; this candidate is the grounding axis alone.** 🔴 **The split criterion is PARENTS, not surface (dev's C4 reading, adopted): this extends 0019 alone, while the reply table extends 0041 and portability and must amend an accepted enumeration claim.** *v1 argued the two were one document because they meet at one assertability surface — they do, and that was the wrong criterion; a return on either half would have blocked the other.* **The composition rule lives with the reply candidate, with its dependency on this axis stated; neither may be accepted without the other having been read.** *v1.1 folded dev's C1–C5: Part A EXTENDS `Edge.ungrounded` (0019) rather than adding a field — v1's “every plausible existing carrier is spoken for” was an exhaustiveness claim over four carriers with a fifth on the same model; “unless confirmed” gained its home and its open question; episodes are out of scope.* Prior: v1.1 · v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — both halves change what the agent may ASSERT about a person, and one of them adds a record a person writes about themselves. |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 0045 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | none. Occasioned by `A9` (Solove's aggregation; Lee et al., CHI 2024, from 321 documented AI privacy incidents) and `A8` (LINDDUN's non-repudiation requirement). |

---

## 1. Why these are ONE document, and what drafting them apart would have produced

**They are not one mechanism. They are two carriers that meet at one surface**, and
that is exactly why they had to be drafted together.

| | **Part A — grounding** | **Part B — reply** |
|---|---|---|
| **who writes it** | the product, at ingest | **a person**, at any time after |
| **when** | write-time, once | any time, repeatedly |
| **domain** | closed: `stated` \| `inferred` | open: the subject's own words |
| **mutability** | immutable with the record | **append-only**, never edits the record |

> 🔴 **Drafted separately, each half would have grown its own render path and its own
> qualification on the gate — and the gate would then hold two qualifications that do
> not compose.** *Neither document alone would have asked what happens to a fact that is
> **inferred AND contested**, because neither owns both words.* §5 answers it, and §5 is
> the only part of this spec that could not have been written twice.

**The 0043 lesson, applied in the other direction.** That spec's v2 shared ONE artifact
between two requirements and round 3 found the sharing was the defect. **The rule that
survives is not “never share” — it is that sharing is a claim about the requirements,
so it gets stated and tested.** Here the claim is: **separate carriers, one composed
surface rule.**

---

## 2. Part A — the declarative grounding axis

### 2a. The demand, and why it is not a preference

The harm literature names **correct-but-uninvited inference** as a harm in its own
right — *“don't derive the thing I deliberately never told you”* — and benchmarks
reward precisely that, since it is what multi-hop items score. **The scoring rule and
the demand have opposite signs.** Our extractor infers.

### 2b. 🔴 `basis` cannot be borrowed, and this is load-bearing

0037 established the concept exactly — *“an inferred procedure is not less TRUSTED than
a stated one; it is differently GROUNDED”* — and then scoped its carrier to procedural
records: **`basis` is “never applicable to a declarative record”**, and the stored rule
is

    procedural  iff  record_kind == "procedural"  OR  basis is not None

**So stamping `basis` on a fact would make that fact PROCEDURAL BY FLOOR**, which is
0037's anti-laundering invariant working exactly as designed. 0037 also already rejected
a fourth `Disclosure` tier (*“the tier was never the problem; the author was”*),
`derived_from` (trust-capping only), and `needs_confirmation` (a ranking input inside
the assertable set, not a gate). ~~**Every plausible existing carrier is spoken for. Part A is a new field.**~~

### 2b-bis. 🔴 THE CARRIER v1 MISSED, AND IT IS ON THE SAME MODEL

**Dev's internal review, C1, blocking, verified here.** `Edge.ungrounded` is shipped and
externally accepted under **0019**, and it is a **product-derived, ingest-time, never
model-declared grounding check**: `grounding.ungrounded(obj_raw, event_text, session_date)`
is True iff any **specifics** token of the object — digit tokens, alphanumeric identifiers,
proper-noun runs, ISO dates through the resolution set — is not grounded in the event text.
It carries a render marker, proactive suppression, export carriage with a pre-v6 strip
rule, and it is **monotone**.

> 🔴 **So v1's §9 “open question” — *bind the fact's TERMS to the event text while allowing
> the object to be normalised* — IS 0019 §4b's predicate, widened from SPECIFICS to TERMS.**
> *v1 posed as an open design question something the product already answers in a narrower
> form, and concluded “every plausible existing carrier is spoken for” about a carrier on
> the same model. **That was an exhaustiveness claim v1 had not earned**, and the four it
> did enumerate made it read as one that had been.*

**Two booleans on one edge with overlapping meaning is the carrier split §1 says this
document exists to prevent.** So:

> **PART A EXTENDS 0019; IT DOES NOT ADD A FIELD.** `grounding` is READ from the existing
> carrier — **`stated` iff the predicate finds nothing ungrounded** — and the change is the
> PREDICATE'S WIDTH, from specifics to terms, not a new column.

**The persistence line then changes the CONSEQUENCE, not the computation:** 0019 today
**marks**; A9's ruling requires ingest not to **write** an unattested attribute unless
confirmed. *The predicate already exists and already runs at ingest; the line moves what
happens at the mark.*

**Inherited, because extending an accepted spec inherits its obligations:** 0019 §8's
limit 1 — *whoever authors the event text authors the grounding corpus* — binds any corpus
built for this, and 0019 §7b's list of what a change here owes (0014's ledger, 0016/0018's
final-form amendments, 0009's record equality, 0005's import boundary, 0008, 0012's marker
clamp, 0015's telemetry) is the carrier list this spec satisfies rather than rediscovers.

### 2c. How grounding is DERIVED — structurally, never asked of the model

**0037's procedural path already does this and its rule is the precedent:**
`V-EXTRACTOR-QUOTE-GATED` admits a procedural triple only when its `quote` is a verbatim
span of the event and the author is the user — *“basis is DERIVED `stated` below, never
read from the model.”*

> **The same discipline binds here: the model never declares a fact's grounding.**
> *A model asked “did they state this or did you work it out?” is being asked to mark
> its own homework, on the one axis where its incentive runs the wrong way.*

🔴 **But the procedural gate cannot be reused verbatim, and pretending otherwise would
sink the feature.** A declarative object is normally a NORMALISED value — `works_as:
night auditor at the Grand` — not a verbatim span, so a strict substring gate would
refuse most legitimate extraction. **The attestation test for declarative facts is the
open design question this spec takes to review (§9).**

### 2d. The persistence line — the policy half of `A9`

| | |
|---|---|
| **at query time** | 🔴 **derivation is unrestricted.** A question invites its own derivation; answering it is not the harm the literature names |
| **at ingest** | **an unattested attribute is NOT WRITTEN.** The default is refusal, counted, never silently filed |
| **where the product must persist a derivation** | 🔴 **C3, corrected: `Episode` IS A SEPARATE MODEL and 0019 put `ungrounded` on `Edge` ONLY, so v1's sentence named a field that does not exist there.** **This spec claims EDGES**: an edge stored from a derivation carries the mark and is never rendered as stated. *Episode-level derivation is OUT OF SCOPE and said so — an episode is a narrative summary whose whole nature is derivation, and marking it inferred tells a reader nothing they did not know.* |

#### 🔴 C2 — “unless confirmed” had no carrier in v1

**The ruling is “ingest never writes an attribute the user did not state UNLESS
CONFIRMED”, and v1 carried no confirmation path** — its only `confirm` was the rejection
of `needs_confirmation` as a carrier. **0008's `Memory.confirm` gives the clause a home**;
what it does not give is the answer to the question it raises:

> **What grounding does a CONFIRMED inference get?** `stated`, because a person affirmed
> it — or a third value recording that the system proposed it and a person then affirmed?
> *Research's reading is the THIRD VALUE: collapsing a confirmed inference into `stated`
> erases that the system proposed it, which is the asymmetry Part B exists to answer. But a
> third value widens 0019's monotone boolean into an enum, which is a change to an accepted
> spec's carrier — **named here, and left to the round rather than decided in a candidate.***

> **The axis exists because the line has exceptions.** *A rule with an unmarked
> exception becomes a lie the first time the exception runs; the exceptions are marked,
> so the claim in §7 stays true.*

---

## 3. 🔴 PART B HAS BEEN SPLIT OUT — and the split criterion is PARENTS

**Part B (the subject's right of reply) is now its own candidate, adopted as 0047**, on dev's
internal review (C4).

> **§1 argued these were one document because they meet at one surface. They do — and that
> was the wrong criterion.** *This half extends **0019** alone. That half extends **0041**
> and **portability**, and must amend an accepted enumeration claim to exist at all. **Two
> parents in one candidate is the shape that produced last week's
> four-candidates-seven-definitions count**, and a return on either half would have blocked
> the other.*

**What the joint draft got right is kept there, not here:** the composition rule — the cell
where a fact is BOTH inferred and disputed — lives in the reply candidate §5 **with its
dependency on this document's axis stated**. *Neither may be ACCEPTED without the other
having been read; they may be reviewed in either order.*

## 6. Invariants and executable checks

| | invariant | check, and the MUTANT it must fail on |
|---|---|---|
| **INV-G1** | **Grounding is DERIVED, never model-declared** | an extractor output claiming its own grounding is IGNORED, and the derivation is recomputed. **Mutant: honour the model's field → refuse** |
| **INV-G2** | **An unattested attribute is not written at ingest** | the refusal is counted and named. **Mutant: file it as `stated` → the count must move and the check FAIL** |
| **INV-G6** | **The persistence line does not reach query time** | a multi-hop question is still answered from the store. **Mutant: apply the ingest rule at recall → the answer disappears and the check FAILS** |

## 7. Claims and limits

**Claimed:** that an attribute the user never stated is not written as though they had;
that where the product must persist a derivation it is marked and never rendered as
stated; and that a subject's reply is as durable as the claim it answers.

**NOT claimed:**
- **that we can always tell.** §2c is unresolved for declarative objects; a weak
  attestation test will mark some stated facts inferred. *That direction is the safe
  one and it is still a cost.*
- **deniability.** Part B does not let a person unsay something. **It lets them answer,
  durably, wherever the claim is rendered** — and §3c says what it is not.
- **that the tension is resolved.** It is NAMED and answered. An enterprise buyer and a
  data subject still want opposite things, and the materials say so.

## 8. Alternatives rejected

- **Reuse `basis` for declarative facts** — §2b: the procedural floor rule makes a
  stamped fact procedural, laundering recall.
- **Reuse `needs_confirmation` for a dispute** — 0037 already rejected it for a
  neighbouring purpose: it is a RANKING input inside the assertable set, and a flagged
  record still renders as grounded. **A dispute that renders as grounded is not a
  dispute.**
- **Reuse `AgreementRecord`** — 0026's lexicon finding is what a MARKER SCANNER found on
  an edge, bound to a lexicon version. It is a machine observation; a reply is a person's
  words. *Same slot, opposite authorship.*
- **Make a dispute supersede the edge** — §3c: it would let a reply rewrite history and
  would destroy the audit trail the buyer is paying for, answering the critique by
  conceding the product.
- **One carrier for both halves** — §4.

## 9. Brief for the external reviewer — ROUND 1

**The question this round asks: what is the attestation test for a DECLARATIVE fact?**
The procedural gate demands a verbatim span; a declarative object is normally a
normalised value, so the same gate would refuse most legitimate extraction. *Our reading
is that attestation must bind the fact's TERMS to the event text — subject and object
tokens present, relation from the declared vocabulary — while allowing the object to be
normalised; but that test admits an inference whose terms happen to appear, and we would
rather have the weakness named than argue it away.*

**A second, smaller question:** §5's `stated` + `disputed` cell keeps the fact assertable
with the reply rendered beside it. **Is that the right side of the line, or should a
disputed fact be non-assertable until a human resolves it?** *We chose assertable-with-
reply because non-assertable hands any subject a veto over any record about them, which
an enterprise buyer cannot accept and which no statute requires.*

**What we are NOT asking:** whether to build the axis. It is ruled.

> 🔴 **A SENTENCE A SEALER CHECKS, not only an author — carried VERBATIM into this package's
> README and PIN, and into Package III's:**
>
> **“The declarative grounding axis and the subject's right of reply CANNOT BE ACCEPTED
> INDEPENDENTLY. The composition rule — the cell where a fact is both `inferred` and
> `disputed` — needs both documents. They may be REVIEWED in either order; accepting one
> without the other accepts half of a rule.”**
