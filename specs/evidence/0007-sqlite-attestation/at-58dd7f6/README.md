# The SQLite amendment's evidence at veracium `58dd7f6` (research, 2026-10-25)

Research's re-run of dev's read (`coordination` c971465, `dev-handoff/sqlite-amendment-read-at-58dd7f6/READ.md`), and
one measurement dev's read did not make. Every run is on research's own `git archive 58dd7f6` in the session scratchpad,
never a working tree. Interpreters: the qualified build is research's veracium-less venv
(`~/.cache/veracium-leg/venv-py3.14-0de5a29117f6`, CPython 3.14.7, SQLite 3.45.1, pydantic 2.14.1); the other is uv's
CPython 3.14.7 (python-build-standalone, SQLite 3.53.1) with that venv's site-packages on `PYTHONPATH`. Nothing installed.

## 1. Dev's figures, re-run (`run-rerun.sh`; exits in `rerun-exits.txt`)

Research's own copies of `probe_build_reproduces.py` and `steptable.py` (sha16 `5b81c3ae0d9f1b9f`, the same bytes as
dev's) from `proposals/evidence-sqlite-gate/`.

| what | result | against dev's |
|---|---|---|
| probe, `open`, 3.53.1 (`probe-u-open-…`) | 16 of 16 digests in the accepted set, manifestations equal; existing and new store both REFUSED `unsupported-sqlite` | same |
| probe, `create`, 3.53.1 (`probe-u-create-…`) | refused (traceback; exit 1 is that refusal) | same |
| probe, both modes, 3.45.1 (`probe-q-…`) | opens and creates | same |
| step table `--compare` (`compare-at-58dd7f6.out`) | 98 paths, 98 identical end state AND write sequence | **byte-identical** (sha16 `d35dbdc74ac7e1c9`) |
| step table `--table` (`table-at-58dd7f6.out`) | | **byte-identical** (sha16 `1a418a70ff3afff1`) |
| campaign (`steptable-campaign-at-58dd7f6.out`, the whole run's output; dev's file is the campaign section only) | 9,636 outcome lines: KILLED END-STATE 3,697, COLLATERAL 1,663, BYTE-MATCH 1,623, ABSORBED 2,539, N/A 114, SURVIVED 0 | the 9,636 outcome lines are **identical, line for line** (`grep -E "KILLED\|ABSORBED\|N/A\|SURVIVED"` on both, `diff` rc 0) |

Not committed (size): the ladder JSON `q.json` sha256 `f90efeba280328b56d3e13d0e29ce347e2af3b9a2bf2685c62d9233087b22c3b`
and `u.json` `29a0b1787078d04722c87df5f5c14801ed198fd4d908934ea1f4bbe8c095590a`.

## 2. The step table never issues the arity-inventory INSERT

`unmatched-steptable-ladder.out` (`unmatched.py`): every write the step table's unperturbed ladder recorded, mapped
through the product campaign's own `step_of` (specs/evidence/0013/pa1_campaign.py). **`v16-arity-inventory` has 0
writes on all 98 paths.** Its INSERT runs once per qualifying edge (migration.py L531–L534), and no step-table fixture
holds one. Dev's read names the notice-state backfill as the one v16 step the step table cannot exercise; the arity
inventory is a second. Its cells are the 0013-PA1 campaign's (144, all killed at the step), whose fixtures add arity
rows (`_add_arity_rows`). Every other non-DDL write maps to a step, and every unmapped write is DDL
(`_apply_forward` 1,645, `_repair_drift` 40).

## 3. The product's campaign does not see a write that maps to no step (dev's INV-S10 mutant)

`pa1_campaign.campaign_a` takes each recorded write's step from `step_of`, a hand-written table of matchers (by
function name and SQL text), and **`if step is None: continue`**: a write no matcher claims gets no cell. `problems()`
checks that every `STEP_*` name has cells, not that every write has a step.

`gap.py` runs, on a tree, every campaign path unperturbed (counting non-DDL writes `step_of` maps to no step) and then
`campaign_a` in full:

| tree | non-DDL writes mapped to no step | part A cells | not killed |
|---|---|---|---|
| control: `58dd7f6` unchanged (`gap-control.out`) | 0 | 1,480 (the committed table's count) | 0 |
| mutant: one unwrapped `UPDATE episodes SET json = json_set(json, '$.planted', 1)` before the stamp (`mutant-unwrapped.diff`) | **48** (every path) | **1,480** | 0 |

The two runs' cell multisets are **equal** (sha256 `c722b1c00bd37310d0775aaf50e1bb86514e474dfa1c52cf65050118aa75960f`
for both; not committed). `landed.py`: on the mutant, v15#0 and v9#0 migrate to `user_version` 16 with the planted key
committed in the store. So regenerating the table with `--write` would pass this mutant. **The gate dev proposes has to
assert the complement: every non-DDL write maps to exactly one step.**

## 4. v0.11.1: dev's conditional mutant, the site check, and line coverage (`run2.sh`; exits in `exits2.txt`)

Dev's re-read (coordination `462897b`, `dev-handoff/sqlite-amendment-read-at-58dd7f6/v0.11-reread/`) planted the
same UPDATE behind a SELECT no fixture satisfies (`mutant2-conditional-dev.diff`, dev's bytes), and proposed a site
check (`sites2-dev.py`, dev's bytes, `cmp`-equal to dev's copy). Research re-ran both on its own export:

| on the conditional mutant | result | against dev's |
|---|---|---|
| the complement (`gap.py`, `gap-mutant2.out`) | 0 non-DDL writes mapped to no step; 1,480 cells, multiset sha16 `c722b1c00bd37310`, **the control's**. It passes | same |
| the site check (`sites2-mutant2.out`) | `migration.py:_apply_forward:550` NEVER observed | equal to dev's output, past the header line |
| the site check on the control (`sites2-control.out`) | every migration.py site observed; 6 never observed, all in `open_versioned` (create L1985, L2027, L2031; adopt L2081, L2093; ROLLBACK L2103) | equal to dev's |

**Line coverage, which dev did not measure** (`cov.py`): sys.monitoring LINE events, switched on only inside
`pa1_campaign.run_case` (the migration), over every function under `src/veracium` entered there. Each function's
executable lines are its own code object's `co_lines`.

| run | functions entered | executable lines | never executed |
|---|---|---|---|
| control, 48 unperturbed paths (`cov-control-ladder.out`) | 78 | 969 | 304 |
| conditional mutant, 48 paths (`cov-mutant2-ladder.out`) | 78 | 971 | 305 (the extra one is L550, the planted UPDATE) |
| control, 48 paths plus all 1,480 campaign cells (`cov-control-campaign.out`) | 81 | 1,001 | 288 |

`classify.py` sorts the never-executed lines of `store/migration.py`, over the full campaign
(`classify-control-campaign.out`), by dev's proposed exemption (an if/else/except block whose last statement is
`raise`):
- **81 never executed: 31 exempt, 50 FLAGGED.**
- **40 of the 50 are problem-report lines in the postcondition functions** (`_*_problems`, `_check_outcome_chains`,
  `_compare_converted`): appends that run only when one particular postcondition clause fails, and no campaign cell
  fails it.
- **10 are paths:**
  - `_migrate_outcome_chains` L215–L216: a NON-outcome episode on a base-1/2 store, validated and skipped. No
    campaign fixture holds one below v3.
  - `_raw_object` L154–L155: an episode json that does not parse.
  - `migrate_store` L798–L802: the `migration_committed` audit event, because the campaign runs with no
    `audit_sink`.
  - `_older` L785.

So a statement-coverage gate with dev's exemption would refuse the correct tree at `58dd7f6` on 50 lines. That figure
is for this campaign's scope only. The wider suite may run some of these lines, but nothing measured here shows it.
