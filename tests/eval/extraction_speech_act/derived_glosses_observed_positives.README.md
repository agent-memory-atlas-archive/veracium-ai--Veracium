# The sixteen observed positives, derived — and the record of the rejected design

`derived_glosses_observed_positives.jsonl` is the LIVE rule's output over the sixteen
clean user-stated routines observed across four LongMemEval draws (400 sessions):
`{draw, n, quote, admitted, derived}` per row, regenerated from the four labelled
files by `tests/test_0037_capture.py::test_the_derived_gloss_of_every_observed_positive_is_pinned`
and compared byte for byte. The live rule (specs/0037 v21 §4a-iii Gate 4): the user's
sentence, whitespace-normalised, with a comma-introduced relative clause cut and
nothing else.

`derive_gloss_reference_REJECTED_DESIGN.py` and `derived_glosses_16_REJECTED_DESIGN.jsonl`
are research's INDEPENDENT implementation and output of the design that was measured
and REJECTED on 2026-09-13 — contraction expansion and clause-opening subject dropping,
both asked for by dev and measured by research — kept with the code untouched and a
header saying so, because their value is not the code (obsolete by design) but the fact
that BOTH designs were implemented and measured, independently, before the choice: two
implementations agreeing on a mechanical transform is evidence; one implementation plus
a claim about what the other would have done is not. The rejection is pinned as its
failure by `test_the_derived_gloss_is_not_withheld_by_describes_frozen_floor`: the
subject-dropped fragment is withheld by describe's frozen executable-detail floor, the
sentence is rendered. Do not read the rejected file as the spec.
