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
