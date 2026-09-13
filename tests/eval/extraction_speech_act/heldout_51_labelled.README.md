# The held-out draw, labelled — `heldout_51_labelled.jsonl`

*Research, 2026-09-13. LongMemEval sessions **101-200**, drawn with
`ablation.py 100 … 100`. **Disjoint from the published draw, verified rather than
assumed**: offset 0 reproduces the first 100 session ids exactly and this slice
shares none of them. 100 sessions probed, 0 errors, 9 sessions with at least one
quote, **51 quotes**. Labelled against `HELDOUT-LABELLING-RUBRIC.md` (sha256
`26227b51efa890f0…`), frozen before any quote was read and before dev stated any
threshold. Cost ≈ $0.35 (369K input tokens, `claude-haiku-4-5` via the `distill`
role).*

## 🔴 READ THIS BEFORE SETTING A RECALL THRESHOLD: there are TWO clean positives

| label | n | expected |
|---|---|---|
| `assistant_instruction` | **41** | refuse |
| `user_intention` | **4** | refuse |
| `third_party` | **2** | refuse |
| `user_routine` | **4** — of which **2 borderline** | **pass** (2) |

**Expected pass: 2. Expected refuse: 49.**

> **This set is a strong FALSE-ADMISSION test and a nearly useless RECALL test.**
> Forty-nine spans that must be refused is real evidence about over-admission.
> **Two positives cannot distinguish a gate with 80% recall from one with 100%** —
> a single disagreement moves the rate by fifty points. **Any recall figure
> quoted from this draw is noise and should not be quoted.**

**And this is itself the finding about the first draw:** the published 100
sessions yielded **9 clean positives in 31 quotes**; a disjoint 100 yielded **2
in 51**. **The first draw was unusually rich in user routines, and the
9-clean-positive denominator research handed over was not representative.** The
honest reading of both together: **user-stated routines are RARE — roughly 11
clean instances across 200 sessions** — which is the §8 census's conclusion
arriving a third time, from a corpus drawn to test something else.

## Two spans are duplicates

`answer_d8e33f5c_1` and `answer_d8e33f5c_abs_1` are the same underlying session
in two dataset variants, so **#1/#3 and #2/#4 are identical text**. **49 distinct
spans, 51 rows.** They are kept as separate rows because the gate will see both,
and marked in `note`. **A rate computed over 51 double-counts them.**

## Two classes research constructed for the red team appear here naturally

- **`user_intention` (4 of 51)** — *"I'm thinking of dedicating a specific day
  each week to doing laundry"*. Periodic in content, explicitly not yet adopted.
  The aspiration class again, and more common here than in the first draw.
- **`third_party` (2 of 51)** — *"One of the guys at the meetup showed me how to
  use the tape to create sharp, defined edges"*. A method the user was TAUGHT,
  with no assertion they practise it. **This is red-team attack #2 occurring in
  real data rather than as a construction.**

**Neither was invented to trap the grammar. Both were already in the corpus.**

## The probe's own instructions were violated again

`ablation.py`'s prompt says a plan (*"I'll try X"*) is not a routine and must not
be returned. **Four intentions came back anyway**, matching the first draw's one.
**The probe is not a filter and its output must be labelled, not trusted** —
which is why the labels exist.

## The two borderlines

- **#12** *"I've been keeping it in a spot with a consistent temperature"* — a
  maintained CONDITION, not a repeated act.
- **#31** *"I've been experimenting with different camera angles … playing around
  with editing software"* — exploration described as ongoing.

Flagged, excluded from `expected: pass`, **and not to be moved after the score is
seen.**

## The ceiling, unchanged and restated

**One rater, research, and NOT a blind one** — research has read dev's grammar in
prose and designed five of its controls. The rubric makes the labelling
auditable, not independent. **There is no inter-rater ceiling, so a
gate/label disagreement cannot be charged to the gate.** Every label carries its
reason so a second rater can disagree cell by cell.

## Fields

`n` · `session` · `quote` · `label` · `expected` (`pass`/`refuse`) ·
`borderline` · `note`.
