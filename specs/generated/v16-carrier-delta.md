# The v16 carrier delta (GENERATED: `specs/evidence/0044/carrier_delta.py`; do not edit)

Base: **v14** (the released schema, v0.26.1); v15 (0041, unreleased) is shown as its own step.

## Step v14 -> v15: 4 added, 0 changed, 0 removed

- added table `episode_event` (required)
- added index `ix_episode_event_lookup` (rebuildable)
- added index `ix_redactions_target` (rebuildable)
- added table `redactions` (required)

## Step v15 -> v16: 17 added, 2 changed, 0 removed

- added table `act_counter` (required)
- added table `arity_era` (required)
- added table `arity_inventory` (required)
- added index `ix_arity_inventory_user` (rebuildable)
- added index `ix_migration_outcome_edge` (rebuildable)
- added index `ix_refusal_inventory_user` (rebuildable)
- added index `ix_replies_edge` (rebuildable)
- added index `ix_request_registry_target` (rebuildable)
- added table `migration_op` (required)
- added table `migration_outcome` (required)
- added table `migration_run` (required)
- added table `plan_header` (required)
- added table `reclassification_plan` (required)
- added table `refusal_inventory` (required)
- added table `replies` (required)
- added table `request_registry` (required)
- added index `ux_replies_resolve` (required)
- changed `confirmations`
- changed `redactions`

## The ALTER statements (byte-quoted)

`confirmations`:

```sql
ALTER TABLE confirmations ADD COLUMN origin TEXT NOT NULL DEFAULT 'local'
ALTER TABLE confirmations ADD COLUMN recorded_correlation_id TEXT
ALTER TABLE confirmations ADD COLUMN origin_store TEXT
ALTER TABLE confirmations ADD COLUMN origin_user TEXT
ALTER TABLE confirmations ADD COLUMN origin_act_id TEXT
ALTER TABLE confirmations ADD COLUMN act_seq INTEGER
```

`redactions`:

```sql
ALTER TABLE redactions ADD COLUMN state TEXT NOT NULL DEFAULT 'applied'
ALTER TABLE redactions ADD COLUMN pending_reason TEXT
```

## New columns, with their carrier class and erasure

| table | new in | erased with the user | column | type | carrier class (0041's account) |
|---|---|---|---|---|---|
| `act_counter` | v16 | no (store-level) | `id` | INTEGER | non-text (INTEGER): not a content carrier |
| `act_counter` | v16 | no (store-level) | `next_seq` | INTEGER | non-text (INTEGER): not a content carrier |
| `arity_era` | v16 | no (store-level) | `id` | INTEGER | non-text (INTEGER): not a content carrier |
| `arity_era` | v16 | no (store-level) | `effective_at` | TEXT | identifier / reference / clock / closed set |
| `arity_inventory` | v16 | yes | `edge_id` | TEXT | identifier / reference / clock / closed set |
| `arity_inventory` | v16 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `arity_inventory` | v16 | yes | `pre_invalidated_at` | TEXT | identifier / reference / clock / closed set |
| `arity_inventory` | v16 | yes | `pre_reason` | TEXT | identifier / reference / clock / closed set |
| `confirmations` | v16 (ALTER) | yes | `origin` | TEXT | identifier / reference / clock / closed set |
| `confirmations` | v16 (ALTER) | yes | `recorded_correlation_id` | TEXT | identifier / reference / clock / closed set |
| `confirmations` | v16 (ALTER) | yes | `origin_store` | TEXT | identifier / reference / clock / closed set |
| `confirmations` | v16 (ALTER) | yes | `origin_user` | TEXT | identifier / reference / clock / closed set |
| `confirmations` | v16 (ALTER) | yes | `origin_act_id` | TEXT | identifier / reference / clock / closed set |
| `confirmations` | v16 (ALTER) | yes | `act_seq` | INTEGER | non-text (INTEGER): not a content carrier |
| `episode_event` | v15 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `episode_event` | v15 | yes | `seq` | INTEGER | non-text (INTEGER): not a content carrier |
| `episode_event` | v15 | yes | `txn` | INTEGER | non-text (INTEGER): not a content carrier |
| `episode_event` | v15 | yes | `episode_id` | TEXT | identifier / reference / clock / closed set |
| `episode_event` | v15 | yes | `kind` | TEXT | identifier / reference / clock / closed set |
| `episode_event` | v15 | yes | `reason` | TEXT | D1 reason vocabulary (closed per field; §11.2) |
| `episode_event` | v15 | yes | `state` | TEXT | §4c journal state, tombstoned by every redaction |
| `episode_event` | v15 | yes | `recorded_at` | TEXT | identifier / reference / clock / closed set |
| `migration_op` | v16 | no (store-level) | `op_id` | TEXT | identifier / reference / clock / closed set |
| `migration_op` | v16 | no (store-level) | `mode` | TEXT | identifier / reference / clock / closed set |
| `migration_op` | v16 | no (store-level) | `inputs_digest` | TEXT | identifier / reference / clock / closed set |
| `migration_op` | v16 | no (store-level) | `admitted_at` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `plan_id` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `edge_id` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `outcome` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `pre_invalidated_at` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `pre_reason` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `successor_evidence` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `applicable` | INTEGER | non-text (INTEGER): not a content carrier |
| `migration_outcome` | v16 | yes | `origin` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `outcome_uid` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `undone_at` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `undo_request_ref` | TEXT | identifier / reference / clock / closed set |
| `migration_outcome` | v16 | yes | `op_id` | TEXT | identifier / reference / clock / closed set |
| `migration_run` | v16 | yes | `plan_id` | TEXT | identifier / reference / clock / closed set |
| `migration_run` | v16 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `migration_run` | v16 | yes | `op_id` | TEXT | identifier / reference / clock / closed set |
| `migration_run` | v16 | yes | `committed_at` | TEXT | identifier / reference / clock / closed set |
| `plan_header` | v16 | no (store-level) | `id` | INTEGER | non-text (INTEGER): not a content carrier |
| `plan_header` | v16 | no (store-level) | `plan_id` | TEXT | identifier / reference / clock / closed set |
| `plan_header` | v16 | no (store-level) | `effective_at` | TEXT | identifier / reference / clock / closed set |
| `plan_header` | v16 | no (store-level) | `registry_digest` | TEXT | identifier / reference / clock / closed set |
| `plan_header` | v16 | no (store-level) | `op_id` | TEXT | identifier / reference / clock / closed set |
| `reclassification_plan` | v16 | no (store-level) | `plan_id` | TEXT | identifier / reference / clock / closed set |
| `reclassification_plan` | v16 | no (store-level) | `relation` | TEXT | identifier / reference / clock / closed set |
| `reclassification_plan` | v16 | no (store-level) | `from_arity` | TEXT | identifier / reference / clock / closed set |
| `reclassification_plan` | v16 | no (store-level) | `to_arity` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v15 | yes | `id` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v15 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v15 | yes | `target_kind` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v15 | yes | `target_id` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v15 | yes | `fields` | TEXT | attestation field names — the kind's carrier paths, refused otherwise at the parser AND the commit (R9-08) |
| `redactions` | v15 | yes | `marker_version` | INTEGER | non-text (INTEGER): not a content carrier |
| `redactions` | v15 | yes | `reason` | TEXT | D1 reason vocabulary (closed per field; §11.2) |
| `redactions` | v15 | yes | `store_version_before` | INTEGER | non-text (INTEGER): not a content carrier |
| `redactions` | v15 | yes | `store_version_after` | INTEGER | non-text (INTEGER): not a content carrier |
| `redactions` | v15 | yes | `event_ref` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v15 | yes | `recorded_at` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v15 | yes | `source_body` | TEXT | a witnessed notice's foreign body: carrier-path NAMES, D1 vocabulary, versions, a time (R9-04/R9-05) |
| `redactions` | v15 | yes | `source_origin` | TEXT | a witnessed notice's SOURCE IDENTITY, held structured and compared exactly: an origin, a user id and an event ref — identifiers, the class of `redactions.user_id` / `event_ref`; NULL on a local row (round 11, R10-03) |
| `redactions` | v15 | yes | `source_user` | TEXT | a witnessed notice's SOURCE IDENTITY, held structured and compared exactly: an origin, a user id and an event ref — identifiers, the class of `redactions.user_id` / `event_ref`; NULL on a local row (round 11, R10-03) |
| `redactions` | v15 | yes | `source_event_ref` | TEXT | a witnessed notice's SOURCE IDENTITY, held structured and compared exactly: an origin, a user id and an event ref — identifiers, the class of `redactions.user_id` / `event_ref`; NULL on a local row (round 11, R10-03) |
| `redactions` | v16 (ALTER) | yes | `state` | TEXT | identifier / reference / clock / closed set |
| `redactions` | v16 (ALTER) | yes | `pending_reason` | TEXT | identifier / reference / clock / closed set |
| `refusal_inventory` | v16 | yes | `refusal_id` | TEXT | identifier / reference / clock / closed set |
| `refusal_inventory` | v16 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `id` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `edge_id` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `kind` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `target` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `text` | TEXT | treated side path (REPLACE) |
| `replies` | v16 | yes | `actor` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `correlation_id` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `request_digest` | TEXT | treated side path (REPLACE) |
| `replies` | v16 | yes | `origin` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `recorded_correlation_id` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `origin_store` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `origin_user` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `origin_act_id` | TEXT | identifier / reference / clock / closed set |
| `replies` | v16 | yes | `act_seq` | INTEGER | non-text (INTEGER): not a content carrier |
| `replies` | v16 | yes | `written_at` | TEXT | identifier / reference / clock / closed set |
| `request_registry` | v16 | yes | `user_id` | TEXT | identifier / reference / clock / closed set |
| `request_registry` | v16 | yes | `correlation_id` | TEXT | identifier / reference / clock / closed set |
| `request_registry` | v16 | yes | `verb` | TEXT | identifier / reference / clock / closed set |
| `request_registry` | v16 | yes | `target_edge_id` | TEXT | identifier / reference / clock / closed set |
| `request_registry` | v16 | yes | `request_digest` | TEXT | treated side path (REPLACE) |
| `request_registry` | v16 | yes | `result_ref` | TEXT | identifier / reference / clock / closed set |
| `request_registry` | v16 | yes | `written_at` | TEXT | identifier / reference / clock / closed set |

## The accepted v16 manifests (11)

| provenance | digest |
|---|---|
| constructor v16 | `d2669f67de09e1d7edd8ff56f685a00f98a2ee3148f444272c6d666c996aebf3` |
| migrated->v16 (0008 §2a: confirmations ALTER on a constructor-shaped base, sha a82ee8e8…); redactions ALTER, sha 8494279c… (a base 15) | `4c268285a246627d08ed5f5b37811a5a1555555fb32eb2ea70606db038899dfd` |
| migrated->v16 (0008 §2a: confirmations ALTER on a constructor-shaped base, sha a82ee8e8…); redactions inline (a base <= 14) | `bbaa3a27b8379d8e19fdf29ecfa2823c08e87f2fcf1e5cf349235cd1f4b8ffcc` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the constructor base, sha 336b762f…; ALTER-path ledger — 0019 rider C2, sha 027b5ca3…) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions ALTER, sha 8494279c… (a base 15) | `b113206cb5f199af3cb43b610431dcd454c8a7f3b54f6b0b2c39f938639b74e1` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the constructor base, sha 336b762f…; ALTER-path ledger — 0019 rider C2, sha 027b5ca3…) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions inline (a base <= 14) | `af650b0a1f820199d81c8103109679d5b5a2895816b9a04fecd06c94ee28ed9c` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the constructor base, sha 336b762f…; ledger inline) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions ALTER, sha 8494279c… (a base 15) | `7ce44e40679e28399b785ca797bbdebf3d1d73e912537e3c351e4ad26665f6be` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the constructor base, sha 336b762f…; ledger inline) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions inline (a base <= 14) | `59d2e24d86bcccce3390579f17e440681616d7d42f8f854c3b6cd7e466897a9d` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the v6 ALTER-path base, sha a788a867…; ALTER-path ledger — 0019 rider C2, sha 027b5ca3…) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions ALTER, sha 8494279c… (a base 15) | `a7fcd8a0de633402b2f172f72337be4e17b0bfad5d64f993d0380861fad218d5` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the v6 ALTER-path base, sha a788a867…; ALTER-path ledger — 0019 rider C2, sha 027b5ca3…) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions inline (a base <= 14) | `c37f8b0683bcf8864e2249f7f190543c38fd34e9673d588860e5b374c4a09544` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the v6 ALTER-path base, sha a788a867…; ledger inline) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions ALTER, sha 8494279c… (a base 15) | `1c108da1cbd954a5223907ba2f2afb35f93138a8865d75eefe78347727268762` |
| migrated->v16 (0025 §4b-v: v10 ALTER on the v6 ALTER-path base, sha a788a867…; ledger inline) [v15 shape + the 0008 v16 registry/counter and the confirmations ALTER, sha a82ee8e8… — specs/0008 §2a]; redactions inline (a base <= 14) | `6100b9656fdd2b8e739e57d3a918ba1d950bd03e662dfdcd837eb88384738451` |

## The ACTUAL DDL: `sqlite_master` from real stores

- **created at v16**: digest `d2669f67de09e1d7edd8ff56f685a00f98a2ee3148f444272c6d666c996aebf3`, in accepted_digests(16); text differing from the declared SCHEMA_V16: none

- **migrated from v14**: digest `bbaa3a27b8379d8e19fdf29ecfa2823c08e87f2fcf1e5cf349235cd1f4b8ffcc`, in accepted_digests(16); text differing from the declared SCHEMA_V16: `confirmations`

```sql
CREATE TABLE confirmations (
    id TEXT NOT NULL PRIMARY KEY, user_id TEXT NOT NULL, edge_id TEXT NOT NULL,
    confirmed_at TEXT NOT NULL, actor TEXT NOT NULL, call_path TEXT NOT NULL,
    correlation_id TEXT NOT NULL, request_digest TEXT NOT NULL, origin TEXT NOT NULL DEFAULT 'local', recorded_correlation_id TEXT, origin_store TEXT, origin_user TEXT, origin_act_id TEXT, act_seq INTEGER,
    UNIQUE(user_id, correlation_id)
)
```

- **migrated from v15**: digest `4c268285a246627d08ed5f5b37811a5a1555555fb32eb2ea70606db038899dfd`, in accepted_digests(16); text differing from the declared SCHEMA_V16: `confirmations`, `redactions`

```sql
CREATE TABLE confirmations (
    id TEXT NOT NULL PRIMARY KEY, user_id TEXT NOT NULL, edge_id TEXT NOT NULL,
    confirmed_at TEXT NOT NULL, actor TEXT NOT NULL, call_path TEXT NOT NULL,
    correlation_id TEXT NOT NULL, request_digest TEXT NOT NULL, origin TEXT NOT NULL DEFAULT 'local', recorded_correlation_id TEXT, origin_store TEXT, origin_user TEXT, origin_act_id TEXT, act_seq INTEGER,
    UNIQUE(user_id, correlation_id)
)
```

```sql
CREATE TABLE redactions (
    id                   TEXT NOT NULL PRIMARY KEY,
    user_id              TEXT NOT NULL,
    target_kind          TEXT NOT NULL,
    target_id            TEXT NOT NULL,
    fields               TEXT NOT NULL,
    marker_version       INTEGER NOT NULL,
    reason               TEXT NOT NULL,
    store_version_before INTEGER NOT NULL,
    store_version_after  INTEGER NOT NULL,
    event_ref            TEXT,
    recorded_at          TEXT NOT NULL,
    source_body          TEXT,
    source_origin        TEXT,
    source_user          TEXT,
    source_event_ref     TEXT
, state TEXT NOT NULL DEFAULT 'applied', pending_reason TEXT)
```

## The object DDL (declared, v16)

### `act_counter`

```sql
CREATE TABLE act_counter (
    id       INTEGER NOT NULL PRIMARY KEY CHECK (id = 1),
    next_seq INTEGER NOT NULL
)
```

### `arity_era`

```sql
CREATE TABLE arity_era (
    id           INTEGER NOT NULL PRIMARY KEY CHECK (id = 1),
    effective_at TEXT NOT NULL
)
```

### `arity_inventory`

```sql
CREATE TABLE arity_inventory (
    edge_id            TEXT NOT NULL PRIMARY KEY,
    user_id            TEXT NOT NULL,
    pre_invalidated_at TEXT NOT NULL,
    pre_reason         TEXT NOT NULL
)
```

### `confirmations`

```sql
CREATE TABLE confirmations (
    id TEXT NOT NULL PRIMARY KEY, user_id TEXT NOT NULL, edge_id TEXT NOT NULL,
    confirmed_at TEXT NOT NULL, actor TEXT NOT NULL, call_path TEXT NOT NULL,
    correlation_id TEXT NOT NULL, request_digest TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'local', recorded_correlation_id TEXT,
    origin_store TEXT, origin_user TEXT, origin_act_id TEXT, act_seq INTEGER,
    UNIQUE(user_id, correlation_id)
)
```

### `episode_event`

```sql
CREATE TABLE episode_event (
    user_id     TEXT    NOT NULL,
    seq         INTEGER NOT NULL,
    txn         INTEGER NOT NULL,
    episode_id  TEXT    NOT NULL,
    kind        TEXT    NOT NULL,
    reason      TEXT,
    state       TEXT    NOT NULL,
    recorded_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, seq)
)
```

### `ix_arity_inventory_user`

```sql
CREATE INDEX ix_arity_inventory_user ON arity_inventory(user_id)
```

### `ix_episode_event_lookup`

```sql
CREATE INDEX ix_episode_event_lookup ON episode_event(user_id, episode_id, seq)
```

### `ix_migration_outcome_edge`

```sql
CREATE INDEX ix_migration_outcome_edge ON migration_outcome(user_id, edge_id)
```

### `ix_redactions_target`

```sql
CREATE INDEX ix_redactions_target ON redactions(user_id, target_kind, target_id)
```

### `ix_refusal_inventory_user`

```sql
CREATE INDEX ix_refusal_inventory_user ON refusal_inventory(user_id)
```

### `ix_replies_edge`

```sql
CREATE INDEX ix_replies_edge ON replies(user_id, edge_id)
```

### `ix_request_registry_target`

```sql
CREATE INDEX ix_request_registry_target ON request_registry(user_id, target_edge_id)
```

### `migration_op`

```sql
CREATE TABLE migration_op (
    op_id         TEXT NOT NULL PRIMARY KEY,
    mode          TEXT NOT NULL CHECK (mode IN ('plan_only', 'restore', 'import-convert')),
    inputs_digest TEXT NOT NULL,
    admitted_at   TEXT NOT NULL
)
```

### `migration_outcome`

```sql
CREATE TABLE migration_outcome (
    plan_id            TEXT NOT NULL,
    user_id            TEXT NOT NULL,
    edge_id            TEXT NOT NULL,
    outcome            TEXT NOT NULL CHECK (outcome IN ('restored', 'withheld_revoked')),
    pre_invalidated_at TEXT NOT NULL,
    pre_reason         TEXT NOT NULL,
    successor_evidence TEXT NOT NULL,
    applicable         INTEGER NOT NULL CHECK (applicable IN (0, 1)),
    origin             TEXT NOT NULL CHECK (origin IN ('local', 'restored', 'imported')),
    outcome_uid        TEXT NOT NULL UNIQUE,
    undone_at          TEXT,
    undo_request_ref   TEXT,
    op_id              TEXT,
    UNIQUE(plan_id, edge_id)
)
```

### `migration_run`

```sql
CREATE TABLE migration_run (
    plan_id      TEXT NOT NULL,
    user_id      TEXT NOT NULL,
    op_id        TEXT NOT NULL,
    committed_at TEXT NOT NULL,
    PRIMARY KEY(plan_id, user_id)
)
```

### `plan_header`

```sql
CREATE TABLE plan_header (
    id              INTEGER NOT NULL PRIMARY KEY CHECK (id = 1),
    plan_id         TEXT NOT NULL UNIQUE,
    effective_at    TEXT NOT NULL,
    registry_digest TEXT NOT NULL,
    op_id           TEXT NOT NULL
)
```

### `reclassification_plan`

```sql
CREATE TABLE reclassification_plan (
    plan_id    TEXT NOT NULL,
    relation   TEXT NOT NULL,
    from_arity TEXT NOT NULL CHECK (from_arity = 'single'),
    to_arity   TEXT NOT NULL CHECK (to_arity = 'multi'),
    PRIMARY KEY(plan_id, relation)
)
```

### `redactions`

```sql
CREATE TABLE redactions (
    id                   TEXT NOT NULL PRIMARY KEY,
    user_id              TEXT NOT NULL,
    target_kind          TEXT NOT NULL,
    target_id            TEXT NOT NULL,
    fields               TEXT NOT NULL,
    marker_version       INTEGER NOT NULL,
    reason               TEXT NOT NULL,
    store_version_before INTEGER NOT NULL,
    store_version_after  INTEGER NOT NULL,
    event_ref            TEXT,
    recorded_at          TEXT NOT NULL,
    source_body          TEXT,
    source_origin        TEXT,
    source_user          TEXT,
    source_event_ref     TEXT,
    state                TEXT NOT NULL DEFAULT 'applied',
    pending_reason       TEXT
)
```

### `refusal_inventory`

```sql
CREATE TABLE refusal_inventory (
    refusal_id TEXT NOT NULL PRIMARY KEY,
    user_id    TEXT NOT NULL
)
```

### `replies`

```sql
CREATE TABLE replies (
    id                      TEXT NOT NULL PRIMARY KEY,
    user_id                 TEXT NOT NULL,
    edge_id                 TEXT NOT NULL,
    kind                    TEXT NOT NULL CHECK (kind IN ('challenge', 'context', 'withdrawn-consent', 'resolve')),
    target                  TEXT,
    text                    TEXT,
    actor                   TEXT NOT NULL,
    correlation_id          TEXT NOT NULL,
    request_digest          TEXT NOT NULL,
    origin                  TEXT NOT NULL CHECK (origin IN ('local', 'imported', 'restored')),
    recorded_correlation_id TEXT,
    origin_store            TEXT,
    origin_user             TEXT,
    origin_act_id           TEXT,
    act_seq                 INTEGER,
    written_at              TEXT NOT NULL,
    CHECK ((kind = 'resolve') = (target IS NOT NULL)),
    CHECK ((kind = 'resolve') = (text IS NULL)),
    UNIQUE(user_id, correlation_id)
)
```

### `request_registry`

```sql
CREATE TABLE request_registry (
    user_id        TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    verb           TEXT NOT NULL,
    target_edge_id TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    result_ref     TEXT NOT NULL,
    written_at     TEXT NOT NULL,
    UNIQUE(user_id, correlation_id)
)
```

### `ux_replies_resolve`

```sql
CREATE UNIQUE INDEX ux_replies_resolve ON replies(user_id, target) WHERE kind = 'resolve'
```
