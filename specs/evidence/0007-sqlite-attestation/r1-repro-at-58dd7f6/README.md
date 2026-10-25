# SA-R1-02 / SA-R1-03: the reviewer's runtime-contract probe, re-run by research at veracium `58dd7f6` (2026-10-25)

- `runtime_contract_probe.py`: the reviewer's bytes, copied raw (sha256 `dee3d7bae6c97fb5044bb30e55feabbd263d8c20316b7601b0c40b47ee6e3aa6`,
  equal to the reviewer's evidence SHA256SUMS line; evidence archive sha256 `ca0f1088…`).
- Tree: research's own `git archive 58dd7f6` in the session scratchpad. Run from a separate output directory:
  - `rc-q.json`: `PYTHONPATH=<tree>/src <qualified venv python, CPython 3.14.7 / SQLite 3.45.1> -B -s -P runtime_contract_probe.py <tree> rc-q.json` (exit 0)
  - `rc-u.json`: `PYTHONPATH=<tree>/src:<that venv's site-packages> <uv CPython 3.14.7 / SQLite 3.53.1> -B -s -P runtime_contract_probe.py <tree> rc-u.json` (exit 0)
- Both interpreters are CPython 3.14.7 (the reviewer's 3.53.1 run was CPython 3.12.14). Results, and what they bear
  on, are in `../../SQLITE-ATTESTATION-R1-DRAFT-SA02-SA03.md` §0. Outputs are unedited; they contain no local paths.

## v2 additions (B2: the attestation suite)

- `suite_rule.py` (research): every `tests/**/test_*.py` whose AST imports `sqlite3`, `veracium.store.schema_version`,
  `veracium.store.migration`, `veracium.store.release_migration`, `schema_evidence` or `migrations_0013`, or names
  `schema_evidence.py` / `migrations_0013.py` in a string literal. `python3 -I suite_rule.py <tree> > suite-rule-at-58dd7f6.out`
  prints 55 modules at `58dd7f6` (stderr `TOTAL 55`; 250 `test_*.py` under tests/). Without `sqlite3` in the roots it
  prints 38.
- The classification of the 22 `skip_inventory` entries inside those modules, and the 13 of the reviewer's 48 changed
  statuses that fall inside them, are in the draft's §2, computed from `specs/skip_inventory.py` at the pin and the
  reviewer's `full-suite/reconciliation.json`.

## v3 additions

- `suite_rule_v2.py`: v2's rule with the string root narrowed to a literal passed inside a call's arguments (loading the file
  by path). `python3 -I suite_rule_v2.py <tree> > suite-rule-v2-at-58dd7f6.out` prints 54 modules (stderr `TOTAL 54`); the
  one module dropped is `tests/test_spec_gate.py` (its only reference is a skip-reason fixture string). Without `sqlite3`
  in the roots it prints 37. The v2 files above are kept as they were.
- `classb_freeze.py` (SA-R1-01): classifies every `ddl_records` entry of a census JSON by statement TEXT against the tree's
  constants (`SCHEMAS`, `REBUILDABLE`, `ALTERS_*`). Run as
  `PYTHONPATH=<tree>/src <qualified venv python> -B -s -P classb_freeze.py <evidence>/probes/census-{control,ddl}.json`
  on research's export of `58dd7f6`; both outputs are concatenated in `classb-freeze.out` (control: 1,645 statements,
  0 OUTSIDE; the reviewer's mutant: 1,837, 48 OUTSIDE, all `DROP TABLE episodes`). The census inputs are the reviewer's
  files (evidence archive sha256 `ca0f1088…`), not committed here.

## SA-R1-01 v2 additions (B3: SQLite decides what is a write)

- `authorizer_kind_probe.py <tree>/specs/evidence/0013/steptable.py` (qualified venv python, `-I -B`): copies `_kind` out of
  steptable.py by AST and compares its label with the authorizer's action codes on an in-memory database, for nine
  statements; it also measures the statement cache's effect on authorizer callbacks. Output `authorizer-kind-probe.out`.
- `authorizer_detail_probe.py` (same interpreter, no tree): the table each write action names for five DDL/DML statements,
  and the trace callback inside an `executescript`. Output `authorizer-detail-probe.out`.
- `ifnotexists.out`: `IF NOT EXISTS` across the 50 head constructors at `58dd7f6` (0), via `PYTHONPATH=<tree>/src`.
- `trace_attr_probe.py` (same interpreter, no tree; SA-R1-01 v3): the authorizer/trace event order for one `execute` and one
  three-row `executemany`, with `isolation_level=None` and legacy `""`. Output `trace-attr-probe.out`.
- `census_rule_probe.py` (same interpreter, no tree; v0.12): dev's two corrections checked in memory, the table-valued pragma's
  two traces in one `execute`, `ProgrammingError` on a two-statement string in `execute` and `executemany`, and
  `DROP INDEX IF EXISTS` reporting no action on an absent index. Output `census-rule-probe.out`.
- `schema_channel_probe.py` (same interpreter, no tree; v0.12.1): `setconfig(SQLITE_DBCONFIG_WRITABLE_SCHEMA, True)` fires no
  authorizer callback and no trace; a following `DELETE FROM sqlite_master` reports only `sqlite_master`; and which calls report
  `REINDEX` (CREATE INDEX does, beside `CREATE_INDEX`). Output `schema-channel-probe.out`.
