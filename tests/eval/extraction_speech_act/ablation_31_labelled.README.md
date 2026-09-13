# The ablation's 31 quotes, labelled — `ablation_31_labelled.jsonl`

*Research, 2026-09-13, for dev's V-ACTOR-PRESENT measurement. **Read this before
using the file**: the labels are not the binary split research quoted earlier,
and the difference changes the denominator.*

## 🔴 The 17/14 split research published is the WRONG SHAPE for this test

Research reported the ablation as *"17 are the ASSISTANT giving instructions and
14 are the USER describing their own routines."* **The 17 is right. The 14 is a
conflation**, and it conflates exactly the distinction V-ACTOR-PRESENT exists to
make. Re-read quote by quote, the 14 non-assistant quotes are:

| label | n | expected of the gate |
|---|---|---|
| `user_routine` | **11** (2 of them borderline) | **pass** |
| `user_onetime` | **2** | **refuse** — first person, past, one action (`"I just used a mixture of soap and water"`; `"I did have to dial down the exposure"`) |
| `user_intention` | **1** | **refuse** — `"I'll try to meditate at the same time every day … to make it a habit"` |

**Using 14 as the positive set would score a CORRECT refusal as a false
negative** on three quotes, and would set the acceptance threshold against a
denominator that includes cases the gate is supposed to reject. **Clean positives
are 9; 11 if the two borderlines are counted.**

🔵 **And #15 is worth its own line: the aspiration class research raised as a
CONSTRUCTED attack is present in the real data.** *"I'll **try to** meditate at
the same time every day, right after my morning walk, **to make it a habit**"* —
first person, explicitly periodic, and it states the habit does not yet exist.
It was not invented for the red team; it was already in the corpus.

## The two borderlines, stated rather than resolved

- **#4** `"I've been preparing the raised bed in my backyard by adding a 2-inch
  layer of compost"` — a single ongoing **project**, not a repeating practice.
  The project/routine line is one the grammar will have to draw and this is the
  cheapest case to draw it on.
- **#31** `"I've been having a blast playing around with different tunings"` —
  exploration described as ongoing.

**They are flagged `"borderline": true` and excluded from `expected: pass`.**
Move them if dev disagrees; **do not move them after seeing the score.**

## 🔴 This is NOT the unseen set, and calling it that reintroduces the objection

Dev's message describes this file as *"the unseen set"*. **It is not.** Dev's
original plan already named *"a positive set from your ablation examples"*, and
the design conversation has been informed by these quotes throughout. **A set the
designer has read is not held out, whatever it is called.**

What this file actually is: **the FALSE-NEGATIVE denominator** — does the gate
refuse genuine user routines? That is a coverage test, and it is necessary. It is
not a generalisation test.

> **For a genuinely unseen set, draw fresh sessions: the ablation probe ran over
> 100 LongMemEval sessions and 948 exist. A second run over sessions 101-200,
> labelled without looking at the grammar, costs one probe pass and is the only
> thing here that tests generalisation.** Research has not read those sessions.

## Provenance of the labels, stated because it bounds them

**One rater, research, re-derived 2026-09-13 by reading all 31.** There is no
second labelling and therefore **no inter-rater ceiling** — a disagreement
between the gate and these labels cannot be attributed to the gate without one.
The `note` field carries the reason for every label so a second rater can
disagree specifically rather than in aggregate.

## Fields

`n` · `session` · `quote` · `label` · `expected` (`pass`/`refuse`) ·
`borderline` · `note`.
