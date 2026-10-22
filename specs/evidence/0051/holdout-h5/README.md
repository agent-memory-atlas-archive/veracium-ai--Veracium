# Holdout H5 for 0051's ATTEST-6 (research, started 2026-10-21 23:19 UTC)

ATTEST-6 (`attest_turns.py`, sha256 `ccabb664bbf1567a6d45bae6c64c7dbf08ff0c3a319f69bf83d9642700b1cba7`) is
ATTEST-5 (`0bb7779f`) with one rule changed: a counted `h`/`q` now makes a weak name (Bot, System, Agent, Model,
`…bot`) NON-USER (R-II round 2, RII-02). 0045 §4a needs a fresh holdout before it ships. Dev froze the file and sent
its digest; research took its own copy and verified the digest and the 5→6 diff (`9e3f7fad…`) before writing any
brief.

**Why two strata.** H3 ∪ H4 (260 items) hold 0 events with counted letters, so ATTEST-6 changes none of them
(research's R-II stage-1 read, B3, `evidence-rii-r2/phase0/holdout-reach.out`; re-run on ATTEST-6's bytes: 0 changed).
A holdout written to H4's brief alone would measure nothing about the change.
- **H5-G** (general, 65 items): H4's two asks, the no-regression measure.
- **H5-T** (targeted, 65 items): letter-labelled transcripts with an automated weak-named participant, the change's
  own measure.

| step | what |
|---|---|
| 0 | the three briefs, committed verbatim before either author is launched (`brief_common.txt` + `brief_general.txt` → author G; `brief_common.txt` + `brief_targeted.txt` → author T) |
| 1 | two independent authors (Sonnet subagents, told to use no tools), one per stratum; their arrays extracted verbatim, merged and shuffled into `holdout_h5.json` with a `stratum` field; committed before any scoring |
| 2 | a second blind labelling of all 130 by a separate subagent (no gold, no notes, no `value_source`, no stratum) |
| 3 | the scorer, pre-registered (committed before it runs) |
| 4 | scored ONCE: ATTEST-3, ATTEST-5@0bb7779f and ATTEST-6@ccabb664 side by side, per stratum; H3 and H4 as regression sets |

**Research's own exposure, stated.** Research wrote these briefs knowing ATTEST-6's rule and AFTER its bytes were
frozen. The targeted brief names the label shapes under test; the authors never see 0051, its grammar, ATTEST or
H1–H4. The relation glosses are written fresh for H5 (H3/H4's were not kept verbatim), in plain language, not in
ATTEST-3's trigger phrases.

**Pre-registered predictions** (before any item exists): H3 and H4 verdicts are identical under ATTEST-5 and ATTEST-6.
On H5-G, ATTEST-6 equals ATTEST-5 on almost every item. On H5-T, ATTEST-6's false attestations are at most ATTEST-5's.

**Dev must not read this directory before step 4 is committed.**

## Step 1: the two authors and the corpus (2026-10-21 23:24 UTC)

Both authors were Sonnet subagents (general-purpose agents), each given `brief_common.txt` plus its own stratum brief,
verbatim, with nothing else. Each made **0 tool uses** (counted from its transcript by `extract_final.py`). Each
final message was extracted verbatim into `raw/author_G.txt` and `raw/author_T.txt` (HTML entities such as `&amp;`
and `&gt;` kept as written). `merge_h5.py` checks 65 items per author and every field. It adds `stratum`, shuffles
with a seed derived from the two raw files (sha256 prefix `8572e769584a2936`), assigns `h5-001`…`h5-130` and writes
the gold-free `h5_items_for_labelling.json`.

- **H5:** 130 items, 59 true / 71 false (author's gold); G 65, T 65; 5 per relation in each stratum.
- **Committed before any scoring,** and before any predicate has run on these items.

## Step 3: the scorer, pre-registered (2026-10-21 23:25 UTC)

`score_h5.py` is committed before it runs on H5. Its one smoke test ran on H4's items with FAKE strata (alternating
G/T) and on H3/H4's own labels: no H5 item or label was read. The second labeller had finished before this commit, and
its output had not been extracted, compared or scored. The run environment is a git-less export of 07df8f8 (ATTEST-5
as `attest_turns.py`) with ATTEST-6's bytes as `attest_turns6.py`.

## Step 2: the second blind labelling (extracted and committed 2026-10-21 23:26 UTC, after the scorer)

A separate Sonnet subagent, given `brief_labeller.txt` verbatim (committed before it was launched, research
`9e4baea9`), made **one tool use**: a Read of `h5_items_for_labelling.json` (id, relation, object, text; sha256
`d1706a3d…`), the only file in its own read-only directory. Its final message, pure JSON with no fence, is
`raw/labeller_b.txt` verbatim. `labels_h5_b.json` is the same array re-serialised, with the ids checked against the
item order. 130 labels, 59 true. The labels are compared with the author's gold only in step 4's output.

## Step 4: scored ONCE (2026-10-21 23:27 UTC)

`score_h5.py` (pre-registered at `b170840a`) ran on the export above, with all three digests asserted. The output is
`results_h5.txt` (`rc=0` appended by the run). **Gold agreement, author and labeller: 130/130**, so one table:

| H5 (author's gold) | G: false attestations | G: recall | T: false attestations | T: recall |
|---|---|---|---|---|
| ATTEST-3 | 0/38 | 2/27 | 0/33 | 2/32 |
| ATTEST-5@0bb7779f | 0/38 | 2/27 | 0/33 | 2/32 |
| **ATTEST-6@ccabb664** | **0/38** | **2/27** | **0/33** | **1/32** |

**The backstop** (product code; 0051 §4b), over all 130 items:

| | ATTEST-5 | ATTEST-6 |
|---|---|---|
| gold-false items whose value only another speaker gave, restricted | 21 of 28 | **26 of 28** |
| gold-true items restricted (a user fact lost) | 0 | **1** (h5-048) |

**The predictions:**
- **P1 HOLDS.** H3 and H4 are identical under ATTEST-5 and ATTEST-6 (0 items differ in each).
- **P2:** on H5-G, 0 of 65 items differ.
- **P3 holds only as 0 ≤ 0, and it measures nothing about false attestations.** ATTEST-3 attests 2 of H5-T's 65 items,
  so the T stratum gave the change no false attestation to remove. The targeted stratum DID exercise the change: 64 of
  its 65 items carry counted letters, and in all 64 the classes and the turns change. Its effect shows in the backstop
  and in one verdict, not in the false-attestation rate.

**The two items ATTEST-6 changed** (`diagnose_h5.py`, post-scoring; it grades nothing):
- **h5-112** (located_at Leeds, gold true): under ATTEST-5 the weak `Bot:` read UNLISTED, so the bot's "I'm based in
  Leeds." joined the user text, and ATTEST-3 attested on that sentence. The user's own "I'm in Leeds too" is outside
  ATTEST-3's construction (0051 §4f, F4's class). ATTEST-6 removes an attestation that rested on another speaker's
  sentence. That is 0051's purpose and H4's three-echo case again, not a regression. The fact stays stored and
  assertable.
- **h5-048** (works_on "thesis on coral bleaching", gold true): the user wrote "my thesis is on coral bleaching". The
  value's words appear in that order only in the bot's "I'm writing a thesis on coral bleaching.", so with the bot's
  line correctly non-user, the backstop restricts it: **a user fact made use-only.** This is the backstop's matching,
  which is product code, not the frozen file (the user's "is" splits the run of words). ATTEST-5 hid it by counting the
  bot's line as the user's. Restriction only (INV-S4): the row is stored, not dropped.

**INV-S8 on H5 under ATTEST-6** (restricted AND attested): **0 of 130.**

**What H5 establishes:** ATTEST-6 changes nothing outside counted-letter events (H3, H4, H5-G). Inside them it does
what RII-02 asked: 5 more other-speaker values restricted, and one attestation that rested on a bot's sentence
removed. It costs one user fact made use-only, through the backstop. **What it does not establish:** any change in the
false-attestation rate (none was available to measure), or any general accuracy rate.
