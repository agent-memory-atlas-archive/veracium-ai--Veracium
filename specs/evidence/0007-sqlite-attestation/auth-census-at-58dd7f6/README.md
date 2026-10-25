# The authorizer census (0007 SQLite round 2, dev)

At `58dd7f6` (dev's `git archive` exports), CPython 3.14.7 / SQLite 3.45.1 x86_64, over the 48 0013-PA1 fixture
paths, through the PA1 Shim seam with `cached_statements=0`. `auth_census.py`'s docstring states its rules.

| tree | diff vs the pin | what it is |
|---|---|---|
| ctl | none | the control |
| mut | `mut.diff` | N1: the reviewer's class-b mutant, byte-equal to their `probes/class-b-mutant.diff` |
| mut2 | `mut2.diff` | N6: N1 with `/* repair */ ` before `DROP TABLE episodes` |
| mut3 | `mut3.diff` | N7: `WITH doomed AS (SELECT 1) DELETE FROM episodes` after the stamp |

- `auth-census-<tree>.json/.log`: the census under the corrected rules (rule 3 = completeness only; the prefix
  cross-check refuses in the escape direction, and a prefix-DDL text with no schema action is legitimate only as
  a (b2) no-op).
- `first-rules-<tree>.json`: the same runs under the rules as first drafted (per-call trace count; refusal on
  any disagreement). They are the corrections' mutants: 1,904 false refusals on the control (`pragma_table_xinfo`
  traces a nested statement), and the (b2) no-op `DROP INDEX IF EXISTS ix_episodes_user` flagged on N1/N6.
- `census-mut2.json`, `census-mut3.json`: the reviewer's `census_probe.py` on N6 and N7. They show the
  prefix-labelled census is blind to both: N6's DROP is missing from its DDL records, and N7 reports 513 mapped
  writes and 1,645 DDL statements, the control's figures.
