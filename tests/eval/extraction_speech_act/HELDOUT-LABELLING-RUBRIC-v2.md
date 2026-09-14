# Held-out labelling rubric — **v2, EVENT-AWARE**, frozen 2026-09-14T11:15Z

*Research. **v1 is not edited and not superseded as a record**: its digest
`26227b51efa890f0…` is in `COORDINATION.md` and it remains the rubric draws 1-5
were labelled under. This is the rubric for the NEXT draw, frozen before that
draw is taken, and it exists because the round-4 verdict named four things v1
could not give.*

## 0. Why v2 — the four requirements, each from a named failure

> The reviewer, round 4: *"For the next held-out draw, freeze an **event-aware
> rubric**, use **disjoint data**, **complete and freeze labels before the rater
> sees thresholds or gate results**, then **run the full path**."*

| requirement | the failure it repairs |
|---|---|
| **event-aware** | v1 rule 1 said *"label the SPAN ALONE, exactly as the gate sees it"*. **The gate stopped seeing the span alone.** It now evaluates `(event, quote)`, so rule 1's letter and its own stated purpose came apart, and four span-alone `pass` labels were mid-sentence clauses a pair evaluation correctly refused |
| **disjoint data** | `ablation.sessions` slices are disjoint by POSITION, not by SESSION ID — 948 positions, 940 distinct ids. Draws 1-4 were disjoint **by luck**; positions 401-500 collide with draw 4 |
| **labels frozen before thresholds or verdicts** | draw 5 broke v1's own order of operations in **both** directions: dev stated thresholds before labelling, and the rater had already published which rows admitted |
| **run the full path** | the packaged draw-5 test checked helper functions and one assistant row; stored text and descriptions were never asserted for the labelled pairs |

## 1. The unit of labelling is the PAIR — v1 rule 1, replaced

> **Label `(event_text, quote)`, exactly as `check_capture` receives it.**

**v1's purpose was always "label what the gate sees"; only its letter said
"span alone". v2 keeps the purpose and drops the letter.** A label therefore
answers two questions, recorded separately and never merged:

| field | question |
|---|---|
| `label` | Does the SPAN, read as the user's words, assert an established practice they currently follow? *(v1 §"The criterion", unchanged — the eight labels and their tests carry over verbatim)* |
| 🔴 `span_is_whole_sentence` | Is the span a complete sentence **of this event**, or a fragment/clause/multi-sentence join? **Recorded by the rater from the EVENT, before any gate is run.** |

**Both are needed because they answer different questions and a single number
hides one of them:** a span may be a genuine routine *and* a mid-sentence clause.
That is not a gate defect — and it is still a capture the product did not make.

## 2. 🔴 Two denominators, both reported, neither replacing the other

*From the verdict: **"'2 of 2 whole-sentence positives' describes an eligible
subset; it should not replace the broader capture-yield denominator. Intended
refusals still have a product cost."***

| figure | denominator | what it answers |
|---|---|---|
| **gate correctness** | labelled positives that ARE whole sentences | does the gate admit what it is supposed to? |
| **capture yield** | **ALL labelled positives** (rows AND distinct passages) | how much of what users actually say does the product capture? |

**Reporting only the first is the error v2 exists to prevent.** Distinct-passage
counts are mandatory beside row counts, because a repeated span inflates a row
count without adding evidence (draw 5: 6 rows, 4 distinct).

## 3. Order of operations — BINDING, and each step's completion is recorded

1. **this rubric frozen**, digest recorded in `COORDINATION.md`
2. **the draw taken**, sessions selected **by SESSION ID**, disjoint from every
   earlier draw, asserted in code **before the first API call**
3. **event text captured AT COLLECTION**, never reconstructed by join
4. 🔴 **labels COMPLETE and FROZEN**, digest recorded — **before any threshold is
   stated and before any gate result is seen by the rater**
5. dev states thresholds
6. the **FULL PATH** is run: `remember` → store → `describe_procedures`, asserting
   stored text and the description's summary and attribution **for every labelled
   pair**
7. results reported with **both** denominators of §2

> **If steps 4 and 5 invert, or the rater has seen any gate verdict, v2 requires
> the same disclosure v1 did and the same downgrade: a SECOND DENOMINATOR, not a
> held-out test.** Draw 5 is the worked example and the reviewer accepted the
> disclosure — **the disclosure is not the problem; substituting it for the
> protocol would be.**

## 4. What v2 does NOT change

**The criterion, the eight labels, and rules 2-6 of v1 carry over unchanged**,
including *ambiguity is recorded, never resolved silently* and *labels are not
revised after a threshold is known*. **v2 is a change of UNIT and of REPORTING,
not of what makes a span a routine.**

## 5. The limit v2 still cannot fix

**One non-blind rater remains the ceiling.** v1 said so and it is still true:
research designed controls for this gate and has read its grammar. **v2 adds the
protocol that makes a blind rater POSSIBLE — labels frozen before verdicts exist
— but it cannot supply a second rater.** A genuinely held-out result needs one,
and that is a commissioning decision, not a rubric clause.
