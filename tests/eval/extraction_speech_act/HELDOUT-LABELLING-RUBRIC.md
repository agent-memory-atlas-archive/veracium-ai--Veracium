# Held-out labelling rubric — FROZEN BEFORE THE DRAW

*Research, 2026-09-13T14:35Z. **Written and frozen before a single quote from
sessions 101-200 has been read**, and before dev states the threshold. Its digest
is recorded in `COORDINATION.md` so the freeze is checkable rather than asserted.*

## Why a rubric at all, and the limit it cannot fix

**Research is NOT a blind labeller for this measurement.** Research has read
dev's grammar in prose (*"a first-person present/habitual actor frame at its
head, optionally after a leading before/after/when clause; aspect, norm, report,
rejection and request markers refuse"*) and **designed five of its controls**.
Labels from a rater who knows the classifier's rules are not independent of the
classifier, in either direction — they can flatter it or punish it.

**This rubric does not make research blind. It makes the labelling AUDITABLE:**
the criterion is fixed in advance, from 0037's own definition rather than from
the grammar, so a second rater can disagree cell by cell and any drift toward the
grammar is visible as a departure from this text.

> **Stated for the record: one non-blind rater is the ceiling on this
> measurement. The residual figure it produces is bounded by that and should
> carry the caveat wherever it is quoted.**

## The criterion — 0037's, not the grammar's

0037 §4a: what makes a record procedural is *"the registry at write, the
record's own stamp at read … **never the text**"*. For a SPAN, the question the
capture gate must answer is narrower and is the one labelled here:

> **Does this span, read alone, assert that the user has an established practice
> they currently follow?**

Three words carry it: **the user** (not a third party, not a group), **has**
(not intends, hopes, or once did), **established practice** (repeating, not a
single occurrence or a single ongoing project).

## Labels

| label | test | expected of the gate |
|---|---|---|
| `user_routine` | first party, currently holds, repeats | **pass** |
| `user_onetime` | first party, currently or formerly true, but **one occurrence** — "I did X", "I just used Y" | refuse |
| `user_project` | first party, ongoing, but a **single piece of work with an end** — one raised bed, one migration | refuse |
| `user_intention` | first party, but asserts the practice **does not yet exist** — "I'll try to", "I mean to", "I want to make it a habit" | refuse |
| `group_practice` | a practice, but the subject is **not the individual user** — "we", "the team", "at my company" | refuse |
| `assistant_instruction` | the ASSISTANT telling the user how to do something | refuse |
| `third_party` | the span reports **someone else's** practice or instruction, including text the user quoted or pasted | refuse |
| `not_procedural` | a preference, a fact, a feeling, a plan about a thing rather than a practice | refuse |

**`user_routine` is the ONLY `expected: pass`.**

## Rules that bind the labelling

1. **Label the SPAN ALONE, exactly as the gate sees it.** Do not use surrounding
   transcript to rescue a span or to condemn it. If the span alone is ambiguous,
   it is ambiguous — see rule 3.
2. **Tense and aspect are evidence, not the verdict.** "I've been X-ing" is
   ongoing; whether it is a PRACTICE or a PROJECT depends on whether X repeats.
   A raised bed does not repeat; a morning walk does.
3. **Ambiguity is recorded, never resolved silently.** `borderline: true`, with
   the reason, and **excluded from `expected: pass`**. A borderline moved after
   seeing the score is a label chosen to fit the result.
4. **Every label carries its reason in `note`**, so disagreement can be specific.
5. **The probe's own instructions are NOT a filter.** `ablation.py` already tells
   the model to exclude plans and one-off events, and the first 100 sessions
   returned three spans that violate that instruction. **Quotes are labelled as
   they arrive**; a span that should not have been returned is labelled for what
   it is, not dropped.
6. **Labels are written before dev's threshold is known**, and are not revised
   after it is stated.

## Order of operations, fixed here

1. this rubric frozen (digest recorded) · 2. the probe runs on sessions 101-200 ·
3. research labels against this rubric · 4. dev states the pre-fixed threshold ·
5. labels sent, unrevised · 6. dev measures.

**If dev states the threshold before step 3 completes, research will say so and
the measurement is downgraded to a second denominator rather than a held-out
test.**
