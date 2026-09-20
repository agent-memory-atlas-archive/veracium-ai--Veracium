# Feature spec: the correction receipt — a corrected fact names what still rests on it

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.1 2026-09-20 from `0046-correction-receipt-CANDIDATE.md` (sha16 260392a4c98bcaad) |
| **Version** | **v1.1 — DEV'S INTERNAL REVIEW FOLDED (D1–D4); no external round yet.** 🔴 **D1 was blocking and it is the one that changes the document: THE MECHANISM CANNOT FIRE.** The sole `ContributionDraft` writer is absorption, whose contributor is retired `absorbed_duplicate` in the same plan; `correct()` accepts only an ACTIVE edge; consolidation writes NULL contributor columns by decision and consumes EPISODES, never edges. **So the join returns `[]` for every edge a correction accepts, on every store — and v1 would have reported that as `complete`, which is the exact sentence §3a wrote to forbid, produced by its own design.** **§3 is rewritten around it:** what survives (§2's wiki handling, the mint site), the completeness vocabulary gains a third value **`untracked`** — *“nothing is watching”, not “nothing rests on it”* — with `complete` made UNREACHABLE while it is true, and §3d names the two missing pieces (a typed contributor at consolidation, and an edge→episode link the data model does not have). **INV-C1's non-empty half is marked NOT RUN BY NAME rather than skipped**, because v1's mutant would have failed on correct behaviour. **§4 names the carriers v1 omitted** (the public dict's three carriers, the mint site's three callers) and puts the owner's decision plainly: **ship the truthful degenerate form, or hold until a writer exists.** **§7 withdraws the parity claim.** Prior: v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — it adds a completeness claim about what a correction leaves behind, and a receipt that under-reports is worse than no receipt. |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 0046 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | 0041 §10.1/§8 (the owner's F6 ruling, *“outputs are separate”*), whose receipt shape this reuses. |

---

## 1. The gap, read at the return statement

`Memory.correct()` retires the named prior with `invalidation_reason="corrected"`,
inserts the replacement atomically, and returns:

    {"corrected": edge_id, "replacement": new.id}

**Two keys. Nothing about what was built on the value that just became wrong.** *“That's
wrong — fix it, and fix everything you concluded from the wrong version”* — we do the
first clause and say nothing about the second.

**The asymmetry is the reason this is a gap rather than a missing feature:** for
REDACTION the owner already ruled (0041 F6) and the receipt *“names the surviving
derived records so the caller can redact them too.”* For ordinary correction there is no
ruling, no receipt and no notice.

## 2. 🔴 What is NOT the gap — the compiled view is already handled, BY CONSTRUCTION

**Probed rather than assumed, with a stub LLM and no spend:** compile a wiki carrying a
value, correct the fact, read the cache — **`get_wiki` returns `None`.**

The reason is worth stating because it is also this spec's design:

> **the wiki drop lives HERE, in the sole `active=0` writer, so every invalidation path
> — present and future — inherits it by construction instead of having to remember it.
> The RETAIN-set is consulted, never a drop-list: a registered reason outside it drops
> (fail-closed).**

**A derived VIEW that is recomputed on demand is safe. A derived RECORD is not** — it is
a stored row that keeps asserting what it was built from. *That is the whole of the
remaining gap, and it is narrower and sharper than “a correction does not reach what was
derived from it”.*

## 3. 🔴 THE MECHANISM CANNOT FIRE ON THE SHIPPED TREE — and v1 did not know

**Dev's internal review, D1, blocking, verified here independently. This is the section
v1 got wrong, and getting it wrong produced the exact claim §3a warned against.**

### 3a. The carrier v1 named, and why it is empty

`contributions_naming(user_id, contributor_ref)` is the right join — 0021 §7b's typed
reverse join, the one the export path uses. *(v1's other correction stands: the register's
`Episode.lineage` is episode→episode and names no edge.)* **But nothing writes an EDGE
contributor that a correction can see:**

| | |
|---|---|
| **the only writer** | `graph.py`'s absorption path is the sole `ContributionDraft(` constructor in `src` |
| **what it names** | `contributor_id = prior.id` — **and the same plan invalidates that prior `absorbed_duplicate`** |
| **what `correct()` accepts** | 🔴 **an ACTIVE edge only** — it fires `_SITE_CORRECT_INACTIVE` otherwise |
| **consolidation** | writes **NULL** contributor columns *today, by a documented decision*, and consumes **EPISODES**, never edges |

> 🔴 **So for every edge `correct()` accepts, the join returns `[]` — on every store, by
> construction, not by staleness.** And v1's receipt would have reported that as
> **`complete`**: the literal sentence §3a wrote to forbid — *“converts ‘I do not know what
> rests on this’ into ‘nothing rests on this’, which is a claim”* — produced by its own
> design, everywhere, on the first call.

**v1's “COMPLETE from v8 onward” was false for a second reason as well:** pre-v8 NULL
`contributor_ref` is one class, and **consolidation's NULL is a second, permanent one** —
not legacy, not migrating away.

### 3b. What survives, stated before what changes

**§2 stands** — the compiled view is dropped by construction in the sole `active=0` writer,
verified by probe. **§4's mint site stands** — a receipt minted in that same writer is
inherited by every retirement path. *The architecture was right; the thing it was to carry
does not exist.*

### 3c. 🔴 The completeness vocabulary needs a THIRD value, and today's answer is that value

| value | meaning | true today? |
|---|---|---|
| `complete` | the ledger tracks edge contributors on this store, and **nothing** names the corrected fact | **never reachable today** |
| `partial` | some contributions cannot be named *(pre-v8 NULL `contributor_ref`)* | reachable |
| 🔴 **`untracked`** | **the ledger records no edge contributors AT ALL on this store** — the answer is not “nothing rests on it”, it is **“nothing is watching”** | 🔴 **the answer for every store, today** |

**`complete` must be UNREACHABLE while `untracked` is the truth, and the check must
enforce that** — otherwise the feature's first act is the false claim it was written to
prevent.

### 3d. What would make the receipt able to name anything

**Two things the data model does not have**, and naming them is this spec's real
contribution today:

1. **a typed contributor written at the consolidation site** — consolidation currently
   writes NULL contributor columns by decision, so its survivors name nothing;
2. 🔴 **an edge→episode link**, which does not exist: an episode's inputs are event text
   and other episodes. **A corrected EDGE has no recorded descendant of any kind.**

> **Until both exist, a correction receipt can only ever say `untracked`.** *That is worth
> shipping only if a truthful “nothing is watching” is worth more to a caller than the
> two-key dict they have today — and that is the owner's judgement, not research's.*

## 4. What the receipt is — and the decision the owner owes before it is built

| | |
|---|---|
| **minted where** | in the sole `active=0` writer, beside the wiki drop — *every retirement path inherits it* |
| **returned by** | `correct()`: `{"corrected", "replacement", "still_resting_on_it", "completeness"}` |
| **contents** | the typed survivors naming the corrected edge — `(survivor_type, survivor_id, site)` — and nothing about their content |
| **completeness** | `complete` \| `partial:…` \| 🔴 **`untracked`**, derived per user FROM THE LEDGER *(rows with a NULL `contributor_ref` present)*, **never from the store version** — a migrated v8 store carries NULL rows and a fresh one does not |
| **effect** | **NONE on any survivor.** It names; it does not retire, rebuild, flag or notify |
| 🔴 **the carriers of the new keys** | `correct()`'s dict is public API: **the README, the CHANGELOG and the MCP tool's declared result** all carry its shape, and all three are named here because v1 named none |
| 🔴 **the minting site's callers** | `_invalidate_edge_row` returns the user id and has **three callers**; a receipt minted there changes that return at all three, or needs a side channel — the callers are the carrier list |

> 🔴 **THE DECISION, PUT PLAINLY: ship the truthful degenerate form now, or hold the
> candidate until a contributor writer exists.** *Research's recommendation is to SHIP IT,
> because `untracked` is a true and useful sentence — “this store records no derived
> dependents, so I cannot tell you what rests on this” is strictly more than the two-key
> dict says — and because the mint site and the vocabulary are the hard parts and they can
> land once. But the ruled parity with redaction is NOT achieved by it: 0041's receipt
> names survivors because redaction has survivors to name, and correction has none until
> §3d exists. A reviewer will say so, and they will be right.*

## 5. Why not the sweep

The owner's ruling withholds the automatic descendant sweep, and the reason is a fact
about the store rather than a matter of cost: **nothing records whether a correction was
MATERIAL to a given descendant.** A summary that says *“the user works nights”* may
survive a correction from `night auditor at the Grand` to `night porter at the Bell`
intact, or may be destroyed by it, and the ledger cannot tell which. **A sweep would
therefore destroy still-true derived work on the system's own judgement, and the
judgement is not available.** *The caller holding the list has the context the store
does not.*

## 6. Invariants and executable checks

| | invariant | check, and the MUTANT it must fail on |
|---|---|---|
| **INV-C1** | 🔴 **A correction returns the survivors that name it — AND THE NON-EMPTY CASE IS UNREACHABLE UNTIL §3d EXISTS** | the fixture needs a writer that produces an edge contributor a correction can see, and none exists. **So the check is written in two halves: (i) on the shipped tree the receipt reports `untracked` and an empty list, asserted; (ii) the non-empty half is marked NOT RUN BY NAME, with the missing writer named, and is NOT a skip that reads as a pass.** *v1's mutant — “return `[]` → FAILS” — would have failed on correct behaviour, because `[]` IS the answer today* |
| **INV-C2** | 🔴 **`complete` is UNREACHABLE while the ledger tracks no edge contributors** | the value is derived per user FROM THE LEDGER, never from the store version. **Mutant: report `complete` on a store with no tracked contributors → REFUSE** — *that is the exact false claim §3a forbids, and v1's design produced it on every call* |
| **INV-C3** | **The receipt changes nothing** | survivor bytes identical before and after; no episode retired, no wiki state assumed. **Mutant: let the receipt invalidate a survivor → refuse** |
| **INV-C4** | **Every invalidation path mints it** | the hook is in the sole `active=0` writer; a new retirement reason inherits it without edit. **Mutant: move the mint into `correct()` → a second path must then be shown to lose it** |
| **INV-C5** | **`lineage` is not the carrier** | the derivation reads the contribution ledger; an episode whose `lineage` names the corrected edge's SOURCE EPISODE is not reported as resting on the edge. *Guards the confusion §3 corrects* |

## 7. Claims and limits

**Claimed, and it is smaller than v1 claimed:** that after a correction the caller is told,
in the same return value, **what the ledger can see about what still rests on the corrected
fact — including, truthfully, that it can see nothing.**

🔴 **NOT claimed: parity with redaction.** *0041's receipt names surviving derived records
because redaction has survivors to name. Correction has none until §3d's two missing pieces
exist, so this delivers the RULING'S MECHANISM and not yet its effect.*

**NOT claimed:**
- **no sweep, no rebuild, no invalidation** — §5
- **no notification of RECIPIENTS.** *Art 19 asks a controller to communicate a
  rectification to those it disclosed to. Veracium is a library; the controller is our
  customer. Giving them the list is the division of responsibility we can honour; posting
  their notifications is not ours to do, and claiming it would be false.*
- **nothing about pre-v8 stores** beyond the stated boundary
- **nothing about derived VIEWS** — they are handled by construction (§2), and this spec
  would be repeating an existing guarantee rather than adding one

## 8. Alternatives rejected

- **Build it on `Episode.lineage`** — §3: wrong direction and wrong node type; it would
  name nothing and look complete.
- **Mint the receipt inside `correct()`** — it works for the ruled case and no other, and
  §2's writer-level rule exists precisely because per-path memory fails.
- **Sweep and invalidate** — §5, the owner's ruling, on a stated reason.
- **Wait for 0041's implementation and share one receipt type.** *0041 is accepted and
  UNIMPLEMENTED — its nineteen closure rows point at spec text, not code. Waiting would
  block a shipped path on an unbuilt one; correction becomes the reference
  implementation and redaction adopts it.* **Named because a reviewer will ask why the
  parity runs in this direction.**

## 9. Brief for the external reviewer — ROUND 1

**The question this round asks: is a receipt that can say `partial` honest enough to
ship, or does a completeness boundary make the feature misleading in exactly the stores
that most need it?** *Our reading: a named boundary is strictly better than silence, and
the alternative — refusing to report anything until every store can be complete — leaves
the caller with the two-key dict they have today. **But the failure mode is real: a
reader who sees an empty list and misses the word `partial` concludes nothing rests on
the corrected fact**, and we would rather have that attacked than defend it.*

**What we are NOT asking:** whether to sweep. The owner ruled, with a reason recorded in
§5.
