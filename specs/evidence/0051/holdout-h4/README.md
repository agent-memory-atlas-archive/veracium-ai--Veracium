# Holdout H4 for 0051's ATTEST-5 (research, 2026-10-20 01:10 UTC)

H3 was spent on ATTEST-4 and never exercised the conjunction (ATTEST-3 attested 1 of its 130). 0045 §4a needs a fresh
holdout for ATTEST-5. Built to H2's protocol:

| step | what |
|---|---|
| 1 | `holdout_h4.json`: 130 items, 10 per relation. Written by an independent author, a Sonnet subagent with **0 tool uses** (counted from its transcript). Its brief held only the gold question, the 13 glosses, and two asks: about 100 user–AI conversations "as people actually paste or export them", with realistically formatted assistant replies (headings, lists, code, config, notes, tips); and at least 40 in which the ASSISTANT states the candidate value in a plain first-person sentence (self-description, role-play, examples, drafts, personas). Both asks come from 0051 §1's stated problem and from what real assistant text looks like. **The author was never shown 0051, its grammar, ATTEST, or H1–H3.** Its brief was written AFTER ATTEST-5 was frozen (dev's message), but the author saw no part of it. Extracted verbatim; HTML entities (`&gt;`, `&amp;`, `&lt;`) kept as written. **Committed before any scoring.** |
| 2 | a second blind labelling by a separate subagent |
| 3 | scored ONCE: ATTEST-3, ATTEST-4 (ba09a2a1) and ATTEST-5 (0bb7779f) side by side, with H3 as ATTEST-5's regression set |

**Dev must not read this directory before step 3 is committed.**

## Step 2: the second blind labelling (2026-10-20 01:11 UTC)

`labels_h4_b.json`: a separate Sonnet subagent with one tool use (a Read of the gold-free `h4_items_for_labelling.json`,
the only file in its directory), as for H3. Its answer came wrapped in a ```json fence; the first and last lines were
stripped and nothing else was changed. **Gold agreement: 130/130.** `value_source`: 121/130.

## Step 3: scored ONCE (2026-10-20 01:12 UTC)

`score_h4.py` (pre-registered at 9d1130c8) on an export with ATTEST-4's bytes (`attest_turns4.py`, ba09a2a1) and
ATTEST-5's (`attest_turns5.py`, 0bb7779f) beside ATTEST-3 (b1329a81); all three digests asserted. Output:
`results_h4.txt`. The author's and the labeller's golds are identical (130/130), so one table:

| H4 (58 true / 72 false) | false attestations (one-sided 95% upper bound) | recall | removed vs ATTEST-3 |
|---|---|---|---|
| ATTEST-3 | **7/72** (17.5%) | 12/58 | — |
| ATTEST-4@ba09a2a1 | 4/72 (12.3%) | 11/58 | 3 false, 1 true |
| **ATTEST-5@0bb7779f** | **3/72** (10.4%) | **9/58** | 4 false, 3 true |

- **0051's problem, on a blind set:** ATTEST-3 attests seven sentences only the assistant said (a persona blurb, a
  sample profile, a role-play patient, a placeholder README, a sample blog, a wizard persona).
- **ATTEST-5 removes four of them**, including h4-042: an assistant's `**Patient (Mr. Ellis, 54):**` heading reopened a
  user turn under ATTEST-4 (B3) but not under ATTEST-5.
- **The three true attestations it removes were earned by the assistant's echo** (`diagnose_h4.py`, post-scoring):
  ATTEST-3 over the user's own text says NOT_ATTESTED for h4-014, 083 and 103. The raw label came from the assistant's
  draft repeating the fact in ATTEST-3's construction ("I am a client of Reyes Immigration Law", "I prefer a window
  seat", "I use Notion every day"). Removing an `attested` that rests on the assistant's sentence is 0051's purpose;
  the facts stay stored and assertable.
- **ATTEST-5's three remaining false attestations** are formats outside the grammar: an API role transcript
  (`[system]`/`[user]`/`[assistant]`, h4-008), a terminal coding agent (`>` user lines, `●` agent lines, h4-056), and
  a named AI persona (`You:` / `Dr. Voss:`, h4-106).

**§4b under ATTEST-5** (author's gold and `value_source`):
- **12 of 32 assistant-only negatives restricted** (ATTEST-4: 9).
- **2 gold-TRUE items restricted, so two user facts were lost:**
  - h4-073: the user wrote "my husband Daniel's 40th birthday". `_TOKEN` keeps the apostrophe, so the token is
    `daniel's`, not `daniel`, while the assistant's toast says "My husband Daniel". **A tokenizer defect.**
  - h4-083: the user wrote "window seats", the assistant "a window seat". An inflection. Limit 2 covers a value
    found in NO turn; this is a value inflected in the user's turn and exact in the assistant's, which RESTRICTS.
- **The 20 unrestricted assistant-only negatives**, by format:
  - 10 named AI personas (Character.ai, `You:` plus a character name; both unlisted, so user text);
  - 3 API role brackets;
  - 2 support bots (`Agent (Priya):` without a USER label; `Bright (virtual assistant):`);
  - 2 Gemini bare-name lines (with H3's 3, five in all);
  - 1 terminal agent; 1 Slack bot without a colon; 1 paraphrase.

**H3, as ATTEST-5's regression set:** unchanged from ATTEST-4 (0/72, recall 1/58; §4b 5 restricted, 0 user facts lost).

## Annotation (2026-10-20 01:20 UTC): the timeline in step 1 is wrong in one clause

Step 1 says "Its brief was written AFTER ATTEST-5 was frozen (dev's message)". The order was:
1. dev proposed the Route 2 rule;
2. research replied, and in the same turn wrote this brief and launched the author;
3. dev's "ATTEST-5 is FROZEN" message arrived (sha256 0bb7779f);
4. research committed H4 (375089fb), then labelled and scored it.

So the brief was written BEFORE ATTEST-5's bytes existed, by research, knowing the proposed rule's shape (a heading
inside a reply stays in it). That is why the brief asks for realistically formatted assistant replies; the brief
names no rule. **What holds the holdout:**
- the author saw neither the rule nor the file;
- ATTEST-5 was frozen before H4 was committed anywhere dev could read;
- dev reports not opening this directory before research's score.
