# Holdout H3 for 0051's ATTEST-4 (research, 2026-10-20 00:38 UTC)

The fresh holdout frozen 0045 §4a requires before a new predicate version ships. 0051 v0.1 (sha16 c12075491ad7bde7)
names ATTEST-4. Built to H2's protocol (`specs/evidence/0045/attest/README.md`), in this order:

| step | what |
|---|---|
| 1 | `holdout_h3.json`: 130 items (10 per ATTEST relation; 58 true, 72 false). Written by an independent author, a Sonnet subagent with **0 tool uses** (counted from its transcript). Its brief held only the gold question, the 13 relation glosses, and a mix of genres: pasted multi-speaker conversations "as people actually paste or export them", the user's own structured notes, and single messages. It was **never shown 0051, its label grammar, ATTEST, H1, H2 or any development set.** The text was extracted programmatically from the author's final message, verbatim; three items carry the HTML entity `&amp;` as written. **Committed before ATTEST-4 exists and before any scoring.** |
| 2 | a second blind labelling by a separate subagent (no gold, no notes, no `value_source`) |
| 3 | scored ONCE, on dev's frozen ATTEST-4 file, by research |

**Gold question:** "In this text, does the USER, in their own words and in a part of the text that is theirs, state as
currently true about themselves that <relation meaning>: <object>?" A bare agreement with another speaker's wording
is false. `value_source` is where the object's words appear: user / other / both / neither. It is §4b's input.

**Who may read this file before step 3:** research, and the second labeller (texts and candidate facts only). **Dev
must not read it before ATTEST-4's file is frozen and its digest sent to research**; otherwise the set stops being a
holdout for that file.

**Research's own exposure, stated:** research wrote the brief after reading 0051's grammar, which is why the brief
names no format, label or speaker convention. The brief's genre mix and "the assistant states the value" negatives
come from the gold question and 0051's stated problem (§1), not from the grammar.

## Step 2 — the second blind labelling (2026-10-20 00:40 UTC)

`labels_h3_b.json`: a separate Sonnet subagent, extracted verbatim from its final message. Its brief held the gold
question and glosses only. **One tool use**, recorded: a Read of `h3_items_for_labelling.json` (id, relation, object,
text; no gold, note, style or `value_source`; sha256 `2c92615e…`), the only file in its own directory. *H2's labeller
had 0 tool uses because its items were in the prompt. Research chose one file read over retyping 130 texts into a
prompt, which risked changing them. The labeller saw nothing the protocol withholds.*

- **gold: 128/130 agree.** Disagreements: h3-063 and h3-093, both Reddit threads where nothing marks which poster is
  the user (the author's gold: true; the labeller's: false). Genuinely ambiguous. **Scored under BOTH golds and
  reported both**, with the 128 agreed items as the headline set.
- **value_source: 120/130 agree.** The 10 differences are paraphrase-vs-literal calls ("Teams" for "Microsoft Teams")
  and speaker identity in the same two Reddit items. §4b's own match is computed by the product, not read from this
  field; the field only describes the set.

## Step 3 — scored ONCE (2026-10-20 00:58 UTC)

ATTEST-4 = dev's frozen `attest_turns.py`, sha256 `ba09a2a1…` (copy here as received), with ATTEST-3 `b1329a81…`
unchanged; both digests are asserted by `score_h3.py` (pre-registered at 35f7ec46). Dev reported not opening this
directory. Output: `results_h3.txt`.

| gold | ATTEST-3 | ATTEST-4 |
|---|---|---|
| author (58 true / 72 false) | false attestations **0/72** (one-sided 95% upper bound 4.1%), recall **1/58** | identical |
| labeller (56 / 74) | 0/74 (4.0%), recall 1/56 | identical |
| agreed 128 (56 / 72) | 0/72 (4.1%), recall 1/56 | identical |

**What this measures, at its width.** ATTEST-4's false-attestation rate on a fresh holdout is reported, as 0045 §4a
requires: 0/72. But ATTEST-3 attests ONE item of 130 on this genre (h3-021), so ATTEST-4 had nothing to remove. **H3 does
not exercise the conjunction at all.** The FA figure holds for ATTEST-4 because it is a subset (ATTEST-3: 0/72), not
because the conjunction was tested. The recall finding is 0045's, not 0051's: on realistic pasted and multi-speaker
text, ATTEST-3 recognises 1 statement in 58 (H2, written as single messages: 12/53).

**§4b's backstop** (`only_in_non_user_turns`), against the author's gold and `value_source`:
- It restricted 5 items. All 5 are gold-false with the value only in an AI assistant's turn (h3-002, 016, 082, 092, 124).
  **0 gold-true items restricted: no user fact lost.**
- 26 gold-false items have the value only in another speaker's words; 21 are not restricted. Post-scoring diagnosis
  (`diagnose_h3.py`, NOT pre-registered; `diagnose_h3.out`):
  - **17: the other speaker is a HUMAN** (WhatsApp, iMessage "Mom:", Slack, Teams, Zoom, email, Discord, a support
    agent "Agent Lin:"). By design an unlisted name, or a format with no label (timestamps first, no colon), is USER
    text. That is outside 0051's assistant scope, but it is the same leak class.
  - **3: an AI assistant in a format the grammar does not see**: the "You" / "Gemini" bare-name lines the author used
    for Gemini copies (h3-022, 045, 055).
  - **1: a paraphrase**, "cat named Pixel" vs "Pixel the cat" (h3-032; §8 limit 2).
- **Within 0051's scope** (AI-assistant-only values): 5 of 9 restricted.

**A grammar hole found after scoring** (`probe_codelines.py`, `probe_codelines.out`; not an H3 item). A line-start
`Word:` INSIDE an assistant's turn ("else:", "location: Toronto", "Note: I'm based in Toronto.") is an unlisted
name, so it opens a USER turn. The assistant's text after it is then user text, and §4a and §4b both fail open for the
rest of that turn: the pre-spec behaviour, not a regression, but it falsifies §8's claim for that text.
