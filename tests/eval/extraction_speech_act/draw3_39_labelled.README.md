# Third draw, labelled — HELD, NOT SENT

> ## ⛔ HELD AT DEV'S REQUEST. Do not send until dev reports the 0037 v20 run DONE.
>
> Sending it earlier would let the measured set influence the thing being
> measured. **The hold is the whole value of this file.**

*Research, 2026-09-13T16:53Z. LongMemEval sessions **201-300**, drawn with
`ablation.py 100 … 200`. **Disjoint from BOTH prior draws, verified not
assumed**: zero session ids shared with 1-100 or 101-200, and internally
distinct. 100 probed, 0 errors, 10 sessions with quotes, **39 quotes, all 39
spans distinct** (no dataset duplicates this time). Labelled against
`HELDOUT-LABELLING-RUBRIC.md` (sha256 `26227b51efa890f0…`), unchanged since it
was frozen before the second draw. Cost ≈ $0.35.*

| | |
|---|---|
| `draw3_39_labelled.jsonl` | sha256 `e06030f60cf65c5d24faa9a5…` |
| `ablation_draw3_201_300.jsonl` (raw) | sha256 `08b8123c973ea3d8a5b2d25c…` |

## Why this one is genuinely held out, and where it is not

**Held out on the anchor that matters:** dev's v20 design and thresholds were
fixed in the ledger at **16:47Z**; this draw was launched after that and did not
exist when the design was frozen. **The design cannot have seen it.**

🔴 **NOT held out in one respect, stated because it would otherwise be
discovered: research read dev's FULL v20 design — including the exact excluded
verb list — BEFORE labelling.** The first two draws were labelled by a rater who
knew the grammar in prose; this one by a rater who knows its lexicon. **The
rubric is the only protection, and it protects by being fixed and auditable, not
by making the rater blind.** This disclosure belongs beside the residual
wherever it is quoted.

**One rater. No second labelling. No inter-rater ceiling.**

## Counts

| label | n | expected |
|---|---|---|
| `assistant_instruction` | **31** | refuse |
| `user_intention` | **2** | refuse |
| `user_onetime` | **1** | refuse |
| `user_routine` | **5** — of which **3 borderline** | **pass** (2) |

**Clean positives: 2. Must-refuse non-borderline: 34 (34 distinct).**
Borderlines carry no threshold, per the rubric and dev's own rule.

> **The same thinness a third time.** Draw 1: 9 clean positives in 31 quotes.
> Draw 2: 2 in 51. Draw 3: **2 in 39**. Across 300 sessions that is **13 clean
> user-stated routines** — and it is draw 1 that looks unusual, not draws 2
> and 3. **The base rate research handed dev from the first draw was the
> outlier.**

## Two things in this draw bear directly on v20, and neither was arranged

**🔴 The aspiration class appears for the third consecutive draw, and this is
the most explicit instance yet:** #31 — *"I just **need to get into the habit
of** washing them regularly and taking them with me."* The span states in so
many words that the habit does not exist. **Three draws, three appearances: this
is a population, not an artifact.**

**🔵 And the draw contains TWO `try` forms, which is the exact class research
predicted v20 would refuse:** #20 *"I've been **trying** to post at least 5-7
tweets per day"* and #21 *"I **try** to stay consistent and engage with my
followers…"*. **#20 is labelled a CLEAN POSITIVE** — by the rubric's criterion,
which asks whether an established practice is asserted, not what any grammar
does with the head verb. **#20 is the same shape as draw 1's #20, labelled the
same way, before v20's verb list existed.**

> **So this draw tests the prediction rather than merely illustrating it.** If
> v20 refuses #20, that is the predicted class cost appearing on unseen data —
> **1 of 2 clean positives lost, and the recall figure on this draw is 1/2.**
> Research is not adjusting the label to spare the grammar; the label was set by
> the criterion and is recorded here before the run.

## The labels held to the earlier draws deliberately

#20 (`try` + frequency) matches draw 1 #20. #21, #23 and #38 are borderline for
the same reasons draw 1 #4/#31 and draw 2 #12/#31 were: an evaluative or
exploratory head with the practice in the complement. **Consistency with the
earlier labelling was chosen over a fresh reading**, because a rubric applied
differently on the third pass is not the same rubric.

## Fields

`n` · `session` · `quote` · `label` · `expected` (`pass`/`refuse`) ·
`borderline` · `note`.
