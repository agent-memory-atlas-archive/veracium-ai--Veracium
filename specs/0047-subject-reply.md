# Feature spec: the subject's right of reply — the record stands, and the reply travels with it

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.2 2026-09-20 from `0047-subject-reply-CANDIDATE.md` (sha16 e8daf82c70cb4031) |
| **Version** | **v1.2 — CITATION FORM CORRECTED (2026-09-20, pre-copy, on dev's word; no normative text changed): the sibling is cited by its adopted NUMBER, 0045, not by a filename in the research tree. A filename is a temporary handle and dangles at the next rename — which is exactly what happened when the candidates were renamed to their allocated stems, inside the very cell below that warns about it. Prior: v1.1 — SPLIT OUT of the joint grounding-and-reply candidate (now the declarative grounding axis, 0045) on dev's internal review (C4), then folded dev's review of THIS document.** 🔴 **The split criterion is PARENTS, not surface.** *The joint draft was right that the two halves meet at one assertability surface; it was wrong that this made them one candidate. Part A extends **0019** alone. This half extends **0041** and **portability** and must amend an ACCEPTED enumeration claim — two parents in one document is the shape that produced last week's four-candidates-seven-definitions count.* |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — it adds a CONTENT-CARRYING table and amends an accepted spec's enumeration. |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 0047 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | the joint candidate's v1.1 Part B — that half is now the declarative grounding axis, adopted as **0045**. *(Cited by NUMBER rather than by filename, and that is the correction: v1.1 named the sibling's file, the file was renamed to its allocated stem, and this cell — the one warning that a reference to a renamed file is the defect this project has already paid for — became an instance of it. A number survives every rename.)* On the owner's `A8` ruling. **Its §5 composition rule depends on Part A's axis and is carried here with that dependency stated.** |

---

## 0. 🔴 THE FIRST SECTION IS AN AMENDMENT TO ACCEPTED 0041, BECAUSE A NEW COLUMN MUST ANSWER IT

**0041 §3, accepted, states: “no other TEXT/BLOB column carries content.”** *A reply table
is exactly such a column, so this spec cannot be shipped beside that sentence — it lands
WITH an amendment of it, or it does not land.*

> **That sentence was written as an ENUMERATION CLAIM precisely so a new column would have
> to answer it.** *It is the census-that-refuses-on-change working as designed: the carrier
> enumeration lists the new column the moment the model exists and its byte-for-byte test
> goes red. The obligation is the feature, not an obstacle to it.*

**What the amendment carries, in the shape 0041 already uses for side rows** *(dev's
reading of the landed mechanism, and it is the same shape as `confirmations.request_digest`
and the refusal rows' copied `relation`)*:

| | |
|---|---|
| **the treatment map** | gains a row: **`replies.text` → REPLACE with the marker**, the ROW KEPT so append-only survives, the closed `kind` PRESERVED |
| **when** | in the SAME transaction as the edge's redaction, with the attestation record naming it |
| **the carriers** | one line in the store's `SIDE_TABLE_TREATMENTS`, one in the receipt, and the enumeration's own figures move by this model's carriers |
| **export / import** | the redaction-era precedent exactly: a `reply` record line under a conditional stamp, older readers refuse. 🔴 **On import, a reply for an edge the destination does not hold REFUSES THE WHOLE FILE BEFORE ANY WRITE** — not a flag, and not a standing notice. *Closed here rather than left to the round, on 0009 §4c's chain precedent (an outcome chain referencing a missing edge refuses the file) and on INV-R5's own logic: an admitted orphan is content nothing can see. **A file carrying a reply carries its edge, or it is inconsistent.*** |
| **`doctor`** | one more `refs` row for the orphan check |
| 🔴 **the `kind` is closed only if something REFUSES** | 0041 §2d-iv: a closed set is closed **at the WRITE path or not at all**. **The reply writer refuses a `kind` outside the set** — *without that refusal the column is prose, and at redaction the two-branch rule replaces it with the marker instead of preserving it* |
| 🔴 **INV-11's MIRROR binds the reply writer** | a NON-redaction write may not introduce the marker, **so a marker-carrying reply is refused at write AND at import.** *Every other writer is bound by it; a new content table that was not would be the hole the invariant exists to close* |
| 🔴 **the map must be TOTAL over the table** | the reply's other columns — ids, the subject's actor field, timestamps — are **PRESERVE** rows and are listed as such, **because the carrier enumeration will list them and a partial map is a map with an unstated default** |
| **0012** | the reserve rule every rendered class has — an unbounded reply cannot crowd the block it is attached to |

## 0a. 🔴 THE DECISION THIS ROUND MUST MAKE, named rather than decided

**What happens to a reply written AFTER its edge is redacted?**

| | |
|---|---|
| **refuse it** | the edge is a tombstone, and words attached to a tombstone would make the reply table the content channel INV-6 fences. *Dev leans here; so does research, for the same reason* |
| **admit it, and make the reply itself a redaction target** | `redact(reply_id=…)` as a third target kind |

> 🔴 **AND A THIRD READING THAT THE BINARY HIDES, which research adds:** **0041 lets a
> redaction DISCLOSE THAT A RECORD EXISTED.** Where existence remains disclosable, there IS
> something to reply to — *“you are telling people a record about my medication existed;
> I never said that”* — and a flat refusal silences the subject exactly where the system is
> still speaking about them. **So the honest form of the question is conditional on the
> redaction's own existence-disclosure, not a global yes or no.** *Named here because the
> binary reads complete and is not.*
>
> 🔴 **AND THE CONSEQUENCE, which is the argument AGAINST the reading and belongs beside
> it:** the row exists structurally after redaction and `why` renders `redacted`, so a reply
> COULD be attached to the id — **but no surface that speaks to the MODEL renders a
> tombstone.** Recall, the wiki and the contested groups all exclude it by the attestation
> record. *So a post-redaction reply would be rendered nowhere but the biography: **the
> subject answers, durably, to an audience of the operator.*** **That is the honest binary
> the conditional form hides — refuse, or admit a reply that lives only in `why` — and the
> round chooses between THOSE, not between yes and no.**

## 3. Part B — the subject's right of reply

### 3a. What it answers

LINDDUN lists *“let me be able to deny I said that”* as a first-class requirement.
**Veracium is built to defeat that sentence** — durable attribution is the product, and
an enterprise buyer is paying for exactly what a data subject may not want. The owner's
ruling names the tension publicly **and** builds the counterweight.

> 🔴 **THE SHAPE OF THE COUNTERWEIGHT: the record stands, and the reply travels with
> it.** *We do not resolve the tension by weakening attribution — that would sell the
> product's premise to answer a critique of it. We resolve it by making the subject's
> answer as durable as the claim, and by refusing to let the claim be rendered without
> it.*

### 3b. The carrier

| | |
|---|---|
| **what** | a **reply record** bound to an edge: the subject's own words, with a closed `kind` (**`disputed`** \| **`context`** \| **`withdrawn-consent`**) |
| **who** | the SUBJECT of the edge, or the user acting on their behalf — **never the extractor, never the assistant** |
| **effect on the edge** | 🔴 **NONE.** It does not retire, supersede, edit or delete. *0022's rule already governs this shape: “revocation retains every record”* |
| **shape** | **append-only.** A second reply does not replace the first; a reply is never edited, only added to |
| **effect on the AGENT** | §5: a replied-to edge cannot be rendered without its reply |

#### 3b-bis. 🔴 C4 — A NEW CONTENT-CARRYING TABLE OWES A CARRIER LIST, and v1 gave none

**A reply table holds a person's own words, so it is a new content surface and every
boundary that governs content governs it:**

| carrier | what it owes |
|---|---|
| **export / import** (0021, portability) | replies cross the boundary or are stated as not crossing; the confirmations table is the precedent for both shapes |
| 🔴 **0041** | its accepted §3 states **“no other TEXT/BLOB column carries content”** — **a reply table is exactly that**, so redaction must say what happens to a subject's own words attached to a redacted edge. *This is the one that could make Part B unshippable as drafted, and v1 did not mention it* |
| **0012** | a reply is open-domain and unbounded, and §5 forbids rendering the edge without it — **so a long reply can crowd the block: it needs a cap or a reserve, like every other rendered class** |
| **`veracium why` / `doctor`** | an orphan reply (its edge gone) must be reachable and reportable, or it is content nothing can see |

## 3c. What Part B deliberately does NOT give

- **not deletion** — that is 0041's targeted redaction, and it is a different right with
  a different ruling
- **not supersession** — a dispute is not a correction; *a subject saying “that's wrong”
  and the record being wrong are different facts, and merging them would let a reply
  silently rewrite history*
- **not removal from an audit trail** — the enterprise premise survives this feature or
  the feature is dishonest

---


## 5. 🔴 THE ONE SURFACE RULE — carried from the joint draft, WITH ITS DEPENDENCY STATED

> **This section needs Part A's axis to state its rows, and Part A is now a separate
> candidate. That dependency is the price of the split and it is stated rather than
> hidden: the cell that matters — `inferred` AND `disputed` — cannot be evaluated by a
> reviewer holding only this document.** *Neither candidate may be ACCEPTED without the
> other having been read; they may be reviewed in either order.*


**Grounding and reply are separate carriers and ONE decision at the gate.**

| | **no reply** | **replied-to (`disputed`)** |
|---|---|---|
| **`stated`** | assertable — today's behaviour, unchanged | 🔴 **assertable ONLY WITH THE REPLY RENDERED BESIDE IT.** *The claim stands; the subject's answer travels with it. This is the whole of A8's counterweight* |
| **`inferred`** | **assertable ONLY AS AN INFERENCE, with its derivation named** — never as a thing the person said | 🔴 **NOT ASSERTABLE.** *An unattested derivation that its own subject disputes has nothing left holding it up: no statement, and a denial* |

🔴 **C5 — WHERE THAT CELL SITS, which v1 left unsaid.** *“Assertable only with the reply
rendered beside it”* is **a render qualification INSIDE the assertable partition, not a new
class.** The gate's partitions are unchanged; what changes is that an edge carrying a
`disputed` reply may not be emitted without it. **In 0012 §4c(iv)'s class order it rides
with its edge** — a reply is not a class competing for budget, it is a condition on
rendering the thing it answers. *Stated because “a new rendering state” could mean a sixth
class, and a sixth class would need a position, a budget share and a truncation rule that
this spec does not define.*

**Neither qualification may mask the other.** A rendering that shows the reply and drops
the grounding, or the reverse, **fails INV-G4** — that is the composition defect this
joint draft exists to prevent.

---


## 6. Invariants and executable checks

| | invariant | check, and the MUTANT it must fail on |
|---|---|---|
| **INV-R1** | **A reply mutates nothing** | edge bytes identical before and after; the edge is neither retired nor superseded. **Mutant: let a reply set `invalidated_at` → refuse** |
| **INV-R2** | **Append-only, subject-authored** | a second reply adds; an assistant-authored reply is refused. **Mutant: allow an edit in place → refuse** |
| **INV-R3** | 🔴 **A replied-to edge cannot be rendered without its reply** | render a `disputed` edge: the reply is beside it. **Mutant: drop the reply from the render while keeping the edge → FAILS** |
| **INV-R4** | 🔴 **The reply survives its edge's redaction as a ROW and not as CONTENT** | redact the edge: `replies.text` carries the marker, the row is kept, the closed `kind` is preserved, and the attestation names it. **Mutant: delete the row → append-only broken; mutant: keep the text → 0041's content claim broken** *(both buildable against the landed redaction: the first deletes reply rows as embedding rows are deleted, the second omits the replies treatment — the json-only pattern)*. 🔴 **AND A THIRD THE TWO HIDE: treat the text but do NOT name `replies.text` in the attestation** — the content claim still holds, INV-11 at the reply writer never fires, and nothing records that the treatment happened. *The carrier-completeness miss, and the mutant a reviewer builds* |
| **INV-R5** | **An orphan reply is reachable and reportable** | a reply whose edge is gone appears in `doctor`'s refs check. **Mutant: silence it → FAILS** — *content nothing can see is the failure this table would otherwise introduce* |
| **INV-R6** | **A reply is bounded in the render** | it takes the reserve rule every rendered class has. **Mutant: unbounded reply text → it crowds the block and the check FAILS** |

## 7. Claims and limits

**Claimed:** that a subject's answer to a record about them is as durable as the record,
travels wherever the record is rendered, and survives the record's redaction as an
attested row rather than as content.

**NOT claimed:**
- **not deniability.** *It does not let a person unsay something; it lets them answer,
  durably.*
- **not deletion, not supersession, not removal from an audit trail** — those are 0041's
  and 0003's, and answering the non-repudiation critique by weakening attribution would
  sell the premise to defend it.
- 🔴 **nothing about a reply written after its edge is redacted** — §0a is the round's
  decision and this spec does not pre-empt it.

## 8. Brief for the external reviewer — ROUND 1

**The question this round asks: is the post-redaction reply refused, admitted as its own
redaction target, or decided CONDITIONALLY on whether that redaction still discloses the
record's existence?** *Research's reading is the third — a flat refusal silences the
subject exactly where the system is still speaking about them — but the conditional form
costs a branch in a contract whose whole value is that it has none, and we would rather
have that attacked than assume it.*

**What we are NOT asking:** whether the table needs 0041's amendment. §0 settles that: the
accepted sentence is an enumeration claim and a new column must answer it.

> 🔴 **A SENTENCE A SEALER CHECKS, not only an author — carried VERBATIM into this package's
> README and PIN, and into Package II's:**
>
> **“The declarative grounding axis and the subject's right of reply CANNOT BE ACCEPTED
> INDEPENDENTLY. The composition rule — the cell where a fact is both `inferred` and
> `disputed` — needs both documents. They may be REVIEWED in either order; accepting one
> without the other accepts half of a rule.”**
