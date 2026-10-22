# 0051 predicate evidence: holdouts H3, H4 and H5

The evidence for ATTEST-4 (`ba09a2a1`, never shipped), ATTEST-5 (`0bb7779f`) and ATTEST-6 (`ccabb664`), as research
committed it. Every file under `holdout-h3/`, `holdout-h4/` and `holdout-h5/` is research's committed bytes, unchanged. `SHA256SUMS` lists each
file's sha256. 0051 §6 reports the results.

| directory | role | items |
|---|---|---|
| `holdout-h3/` | ATTEST-4's blind holdout; ATTEST-5's regression set | 130 (58 true / 72 false) |
| `holdout-h4/` | ATTEST-5's blind holdout | 130 (58 true / 72 false) |
| `holdout-h5/` | ATTEST-6's blind holdout, in two strata (G general, T targeted at counted letters with a weak-named participant); H3 and H4 as its regression sets | 130 (59 true / 71 false) |

Each directory holds:
- the corpus, with the author's gold (`holdout_h*.json`);
- the gold-free copy given to the second labeller (`h*_items_for_labelling.json`);
- the second blind labelling (`labels_h*_b.json`);
- the pre-registered scorer (`score_h*.py`) and its raw output (`results_h*.txt`);
- the post-scoring diagnoses (`diagnose_h*.py` / `.out`; H3 also `probe_codelines.*`);
- the frozen predicate copy the scorer asserts by sha256 (`attest_turns_ATTEST-4_ba09a2a1.py`,
  `attest_turns_ATTEST-5_0bb7779f.py`; ATTEST-3 is the tree's `src/veracium/attest_v3.py`, `b1329a81`);
- a README with the protocol and the results.

`holdout-h5/` also holds the briefs, verbatim (`brief_*.txt`); the authors' and labeller's final messages, verbatim
(`raw/`); and the scripts that extracted and merged them (`extract_final.py`, `merge_h5.py`). Its frozen ATTEST-6 copy
is not duplicated: ATTEST-6 is the tree's `src/veracium/attest_turns.py`, and the scorer asserts its digest.

## Re-scoring

The scorers ran on a git-less export of veracium at `3914f73`, with the frozen copies placed as modules:
- **H3:** the ATTEST-4 copy as `src/veracium/attest_turns.py`, then
  `PYTHONPATH=<export>/src python score_h3.py holdout_h3.json labels_h3_b.json`.
- **H4:** the ATTEST-4 copy as `src/veracium/attest_turns4.py` and the ATTEST-5 copy as `src/veracium/attest_turns5.py`,
  then `PYTHONPATH=<export>/src python score_h4.py holdout_h4.json labels_h4_b.json <H3's two files>`.

- **H5:** a git-less export of veracium at `07df8f8` (where `attest_turns.py` is ATTEST-5) with ATTEST-6's bytes as
  `src/veracium/attest_turns6.py`, then `PYTHONPATH=<export>/src python score_h5.py holdout_h5.json labels_h5_b.json
  <H4's two files> <H3's two files>`.

Research re-ran H3 and H4 from these bytes on 2026-10-21. H5 was scored once, by this command. Each output equals its `results_h*.txt` byte for byte, except
the committed file's last line, `rc=0`, which the run wrapper appended.

## Two disclosures

1. **The pre-registration order is research's commit order, which this archive cannot authenticate.** It is carried
   as provenance, as the CI claim is. Each file's first commit in research's repository, 2026-10-20 UTC:

   | step | H3 | H4 |
   |---|---|---|
   | corpus (and the README's first step) | `a18a2f52` 00:38:55 | `375089fb` 01:10:11 |
   | second labelling and its gold-free copy | `14e454d5` 00:40:46 | `7c79f29c` 01:11:30 |
   | scorer, with the frozen copy | `35f7ec46` 00:56:43 | `9d1130c8` 01:10:53 |
   | the one score, the diagnoses | `3a933ebf` 00:58:59 | `b3242a94` 01:12:45 |

   H5, 2026-10-21 UTC: briefs `90d25056` 23:19 (before either author was launched); corpus `41f1824e`; labeller brief
   `9e4baea9` (before the labeller was launched); scorer `b170840a`; labels `158cf9c7`; the one score and the diagnosis
   `76e34b3f`. H5's README records each step.

   Every file except the READMEs has exactly one commit. Each README grew one section per step: H3's in 3 commits,
   H4's in 4. The copies here are the final ones.

   For H4, the scorer's commit precedes the labelling's. The order that matters is that the corpus, the labels and the
   scorer all precede the score. `holdout-h4/README.md` gives the order of H4's brief relative to ATTEST-5's freezing.
2. **H3's and H4's authors' and labellers' briefs are not stored verbatim.** Each README describes its brief: what it
   held, what it did not, and that each author made 0 tool uses. H5's briefs ARE stored verbatim, each committed before
   its subagent was launched.
