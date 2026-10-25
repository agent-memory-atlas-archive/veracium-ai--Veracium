# The authorizer census on the drifted-HEAD fixtures (0007 SQLite round 2, dev): C2 and C3

`auth_census.py` here is the round-2 script at ba37c8a plus one environment switch, `AUTH_CENSUS_FIXTURES`
(`pa1`, the default, unchanged: its control output is byte-identical to ba37c8a's `auth-census-ctl.json`; `wrong`;
`missing`). Same pin, interpreter and seam as ba37c8a. Each drifted fixture is PA1 path `v1#0` migrated to HEAD outside
the census, then drifted, then opened by `migrate_store` inside the census.

| file | fixture | result |
|---|---|---|
| `auth-census-c2-wrong.json` | C2: ONE rebuildable index recreated under its own name on another column (present and wrong) | `current`; 1 (b2) WITH a DROP_INDEX action, 1 (b1) recreate; 0 outside, 0 disagreements, 0 refusals |
| `auth-census-c3-missing.json` | C3: every rebuildable index dropped (the step table's `_head_with_drift`) | `current`; 20 (b2) no-ops (no action), 20 (b1); 0 outside, 0 disagreements, 0 refusals |
