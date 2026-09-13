# Fourth draw, span labels — HELD, NOT SENT

> ## ⛔ HELD. Do not send until dev reports the 0037 v21 run DONE.
>
> **This file is HALF the deliverable.** The other half is the (span, gloss)
> pairs, which cannot exist until v21 is committed — a pair is only meaningful
> against the version under test. **Span labels now; gloss labels after the
> commit; both held until dev says the run is done.**

*Research, 2026-09-13T18:45Z. LongMemEval sessions **301-400**, drawn with
`ablation.py 100 … 300`. **Disjoint from all three prior draws, verified**: zero
shared session ids, internally distinct. 100 probed, 0 errors, 14 sessions with
quotes, **120 quotes, 118 distinct spans.** Labelled against
`HELDOUT-LABELLING-RUBRIC.md` (sha256 `26227b51efa890f0…`), unchanged since it
was frozen before draw 2. Cost ≈ $0.35.*

## Counts

| label | n | expected |
|---|---|---|
| `assistant_instruction` | **112** | refuse |
| `user_onetime` | 2 | refuse |
| `user_intention` | 1 | refuse |
| `not_procedural` | 1 | refuse |
| `user_routine` | **4** (0 borderline) | **pass** |

**Clean positives: 4 rows, 3 DISTINCT** (#1 and #30 are identical text in two
sessions). **Must-refuse non-borderline: 116 rows, 115 distinct.**

## 🔴 The thinnest draw yet, and the trend is now four points long

| draw | sessions | quotes | clean positives |
|---|---|---|---|
| 1 | 1–100 | 31 | **9** |
| 2 | 101–200 | 51 | 2 |
| 3 | 201–300 | 39 | 2 |
| **4** | **301–400** | **120** | **3 distinct** |

**Across 400 sessions: 16 clean user-stated routines.** Draw 4 produced the
**most quotes and nearly the fewest positives** — 112 of its 120 spans are
assistant recipe and shoe-care instructions, because the probe faithfully
surfaces "how something is done" and these sessions are full of the assistant
explaining exactly that.

> **This is the fourth independent confirmation of the §8 census's conclusion,
> now from a corpus drawn to test something else entirely: user-stated routines
> are RARE, and draw 1 remains the outlier that research first handed over as
> representative.**

## What is here, and what is deliberately NOT

**Here:** the span label and the `expected` verdict — fixed BEFORE dev's v21 run,
which is what makes them a test rather than a description.

**Not here, and refused on purpose: an EXPECTED GLOSS for each positive.** Dev
asked; research declined. Authoring the gloss a model *should* emit would be a
design act, and research has now helped design this grounding twice — the rule
would then be measured against targets written by someone who knows the rule.
**That is the designed-from problem one level deeper than the one it would be
trying to avoid.**

**Instead:** once v21 is committed, run the REAL extractor over these sessions,
capture the glosses **it** emits, and label each (span, gloss) pair for meaning
preservation. **Judging an artifact research did not write is the only
independence still available**, and it is nearer the reviewer's *"evaluate the
full capture path on fresh data"* than authored targets would be.

## Two spans worth dev's eye before the pairing

- **#81** *"I go to the gym on Tuesdays, Thursdays, and Saturdays."* — present
  simple, explicit named schedule. **The cleanest positive in any draw**, and a
  natural test of the comma-coordinated NP list: a gloss "Goes to the gym on
  Tuesdays, Thursdays and Saturdays" must survive predicate splitting.
- **#59** *"I've got my French press ratio down to a science: 1 tablespoon of
  coffee for every 5 ounces of water."* — labelled a positive by the CRITERION
  (it asserts an established method in current use). Its head is stative
  (`have got`) and v21's positive form may well refuse it. **If it does, that is
  a recall cost on a genuine routine and it should be reported as one, not
  relabelled.**

## The ceiling, unchanged

**One rater, not blind** — research has read the v20 and v21 designs including
the verb classes. The rubric is fixed and auditable; it does not make the rater
independent. **No second labelling, no inter-rater ceiling.**

## Fields

`n` · `session` · `quote` · `label` · `expected` · `borderline` · `note`.
