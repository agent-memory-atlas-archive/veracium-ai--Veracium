# 0045 R1-01 — attestation predicate evidence (research, 2026-10-11)

R1-01 asked for a bounded, testable predicate for `attested` grounding. This directory holds what was built and
how it measured. **Read the order of events; it is the evidence.**

The commit column names commits in **research's repository**, which a reviewer of the product repository cannot
open. The files in this directory are the evidence; the table is the account of the order in which they were written
and committed. This directory lands in the product repository with 0045, copied byte for byte from research's
repository by `git archive`.

| step | commit (research repo) | what |
|---|---|---|
| 1 | c17224b7 | ATTEST-1 and corpus_v1 written together: 0 FP / 2 FN on 68 items. Then 12 probes written after: **6 of 7 negatives falsely attested.** The corpus result was a development-set artifact. |
| 2 | c17224b7 | ATTEST-2 (one change: the object must be the trigger's immediate complement), frozen, sha256 `e1e1e3d3…`, before any holdout existed. Development sets: 0 FP. |
| 3 | 96008a70 | Holdout H1, 120 items, written by an independent author with no file or tool access, from the gold question and relation glosses only. Committed before any scoring. |
| 4 | 2208353e | A second blind labelling (labels_h1_b.json) of H1's texts, given no gold. Then ATTEST-2 scored. |
| 5 | 00cc1f9d | R1-01's required mutants run against the frozen ATTEST-2 (mutants_r1_01.py, polarity_pairs.py; below). |
| 6 | aa7df259 | The scorer's and the mutant runner's JSON reads refuse a duplicate key (`object_pairs_hook`), the product repository's rule for evidence files. attest_v2.py and the data are untouched, and every figure below re-ran unchanged. |

## Result — ATTEST-2 on H1

`python3 score_h1.py attest_v2` (author gold) and `python3 score_h1.py attest_v2 labels_h1_b.json` (second gold):
identical, because the labellings agree on 120/120.

| | |
|---|---|
| false attestations among negatives | **0 / 66** (95% upper bound ≈ 4.5%, rule of three) |
| true self-statements recognised | **9 / 54 (17%)** |

**ATTEST-2 is safe and nearly useless.** Real people state facts about themselves in forms a trigger grammar does not
reach: "been vegan for 3 years now", "Brisbane-based here", "we've got a dog, Rufus", "Figma's my daily driver".

## R1-01's required mutants (`python3 mutants_r1_01.py`)

| mutant | result |
|---|---|
| drop polarity | **SURVIVED on the first 200 items**: adjacency already excludes negation inside the trigger-object span. Minimal pairs with negation OUTSIDE it (polarity_pairs.py, written after, a fixture and never a rate) → 3 new false attestations → **KILLED** |
| swap subject | 7 new false attestations → **KILLED** |
| accept the relation without a supporting assertion (terms presence) | 113 new → **KILLED** |
| trust the extractor's grounding field | **no subject in the predicate**: `attests()` takes no such input. An ingest-layer property, 0045 INV-G1 (a product test at the implementation gate) |

ATTEST-2 on polarity_pairs: 6 of 7 correct. The miss is "I'm vegetarian, never been anything else", a safe-direction
cost of the outside-span negation rule.

## Limits of this evidence (stated, not implied)

- **The 120/120 agreement is not an inter-rater ceiling.** Both labellers are the same model reading the same
  written question, and the author wrote items to be clear-cut. It shows that H1 is unambiguous to that model. A
  human labelling and naturally occurring text (not authored-to-test) are still owed before any rate is quoted outside
  this project.
- H1 is authored chat, 10 items per relation. It is not a sample of real Veracium ingest.
- ATTEST-2 may not be tuned to H1 and then re-scored on it. A next version needs a fresh holdout (H2).

## The design question this raised, and the owner's ruling

With a deterministic grammar, most genuine self-statements (here 45 of 54) do not reach `attested`. Refusing them,
or routing each through a proposal, would put a confirmation burden on the user for ordinary facts. The owner ruled
"Label, don't block" (2026-10-11): such a statement is stored with `att = not_attested` and labelled. The upgrade to
`confirmed` is 0008's `confirm()` on the stored edge (0045 §4d). The proposal mechanism was withdrawn.

---

# 0045 v1.8 — ATTEST-3 and holdout H2 (research, 2026-10-12)

Package II's round-2 verdict (R2-01) showed six strings ATTEST-2 attests that state nothing of the kind. The owner
ruled for a repaired predicate in round 3, measured on a FRESH holdout (2026-10-12). Order of events, all in research's
repository:

| step | commit | what |
|---|---|---|
| 1 | d8d688a1 | ATTEST-3 written and FROZEN (`attest_v3.py`, sha256 `b1329a81…`) with its development gate `regressions_v3.py`: the verdict's 6 negatives, research's 17 (9ead5e9f) and 12 more of the same classes stay non-attested; 9 positives attest; the earlier development sets give 0 false attestations in 56 negatives. Tuned on development sets only |
| 2 | a86637e0 | `mutants_v3.py`: one mutant per rule of the construction, plus R1-01's three — all 8 KILLED on development negatives only, control clean first and last |
| 3 | 419df130 | holdout H2 (120 items, 53 true) written by an independent author (a subagent, 0 tool uses) from the gold question and relation glosses only. Committed before ATTEST-3 ran on it. *That commit's message says item h2-022 carries an HTML entity; it does not — the file holds a plain `>`; the entity was only in how the agent's result was displayed to research* |
| 4 | d86fe60c | a second blind labelling of H2 (a separate subagent, 0 tool uses; no gold, no notes): agrees with the author's gold on 120/120 |
| 5 | this commit | scored, once: `results_h2.txt` (`score_holdout.py`) |

## Result — ATTEST-3 on H2 (both golds identical)

| | ATTEST-3 | ATTEST-2, same H2 |
|---|---|---|
| false attestations among negatives | **1 / 67** (one-sided 95% upper bound ≈ 6.9%) | 5 / 67 (≈ 15.1%) |
| true self-statements recognised | 12 / 53 (23%) | 16 / 53 (30%) |

**The one false attestation is h2-109:** "I use Obsidian. Actually wait, no, I switched to Logseq last month, ignore
that." A retraction in a later sentence, phrased outside ATTEST-3's closed retraction list ("actually wait, no",
"ignore that"). It is the class ATTEST-3 claims to handle, by a list, and the list is open-ended by nature: **the same
structural weakness the reviewer named in ATTEST-2's blacklist.** It is reported, not repaired: changing the list is a
new version, and H2 cannot be used to tune it.

H1, as REGRESSION only (it was ATTEST-2's holdout): ATTEST-3 0 / 66 false attestations, 5 / 54 recall (ATTEST-2: 0 / 66,
9 / 54). The four positives ATTEST-2 found and ATTEST-3 does not are a cost of the sentence-start and
complete-complement rules.

## Limits of this evidence (stated, not implied)

- **H2 was authored to be hard,** from a brief that named the gold question's failure kinds, so it is not a sample of
  real ingest; its negatives are denser in hard constructions than real chat is likely to be.
- **The two labellings are the same model family,** and agree 120/120 on items written to be clear-cut: not a human
  inter-rater ceiling. A human labelling and naturally occurring text are still owed before any rate is quoted outside
  this project.
- **Recall is low by construction** (23% on H2): most genuine statements are stored `not_attested` and labelled, under
  the owner's "Label, don't block".
