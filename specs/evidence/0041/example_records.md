# 0041 — example redaction records and the import / failure-case matrix

*Evidence for the round-2 package (rows 3, 9, 9a–9c, the receipt and §1's `evidence_ref` corrected for round 3 against v4's rulings), built from 0041 v3's §4b, §4b-ii, §4c, §4f and
§4g by dev on 2026-09-15. Every shape here is PROPOSED — 0041 is a draft and
nothing below is implemented; the records are what the contract says the store
will hold, written out so the reviewer can check the contract against concrete
instances rather than prose. Where the contract leaves a value to
implementation, the example says so.*

The marker is the exact byte string `\x00veracium:redacted\x00` (§4b). It is
shown below as `<MARKER>` because a leading NUL does not survive most viewers;
in the store it is the bytes, never the placeholder.

## 1. An edge before and after redaction

Before (the `edges` row: the three duplicated columns and the `json` blob; the
`json` shown abbreviated to the carrier fields):

| column | value |
|---|---|
| `id` | `e-7c1a` |
| `subject` | `user` |
| `relation` | `has_condition` |
| `object` | `hiv-positive since 2019` |
| `json` | `{"id":"e-7c1a","subject":"user","relation":"has_condition","object":"hiv-positive since 2019","note":"told me in confidence","original_relation":"told me in confidence about the diagnosis", "provenance":{"evidence_ref":"ev-12", …}, …}` |

After `redact(user_id="u", edge_id="e-7c1a", reason="subject_request")`:

| column | value |
|---|---|
| `id` | `e-7c1a` (unchanged — identity preserved) |
| `subject` | `<MARKER>` |
| `relation` | `<MARKER>` |
| `object` | `<MARKER>` |
| `json` | per the treatment map (§2d-ii): `subject`, `relation`, `object`, `note`, `original_relation` hold `<MARKER>`; each `agreement.markers` entry is `<MARKER>` (arity preserved — a two-entry list is INVALID under today's uniqueness validator: a blocking code change, §2d-ii); `outcome_counts` is `{}`; **`provenance.evidence_ref` is PRESERVED** (§2 excludes it — round-2 F6 corrected this example; §8 states the limit); `id`, `user_id`, timestamps, booleans, `provenance.author_of_evidence`, `disclosure`, `agreement.direction`/`lexicon` unchanged |
| `active`, `quarantined` | unchanged (§4d: redaction is not invalidation) |

The three duplicated columns and the `json` agree (INV-2, one mutant per column);
`""` in any of them is REJECTED by the tombstone CHECK (INV-8, red before the
CHECK exists).

## 2. The edge's journal event (§4c)

One `edge_event` row, in the redaction transaction, after `_bump` (§4e):

| column | value |
|---|---|
| `user_id` | `u` |
| `seq` | next per-user ordinal |
| `txn` | the redaction transaction's batch id |
| `edge_id` | `e-7c1a` |
| `kind` | `redacted` (new kind; 0029 amended, §11.4) |
| `reason` | `subject_request` — a D1 vocabulary value, never prose |
| `state` | the post-write serialisation with every carrier at `<MARKER>` — and every EARLIER event's `state` for `e-7c1a` rewritten to the same tombstone in the same transaction (§4c: the journal is redacted, not just appended to; INV-4) |
| `recorded_at` | store-minted, monotone |

## 3. An episode before and after redaction (§4b-ii)

Before: `episodes` row `ep-31` with `json` `{"id":"ep-31","date":"2026-09-01","summary":"User disclosed a diagnosis and asked that it not be shared.","retired_reason":null,…}`.

After `redact(user_id="u", episode_id="ep-31", reason="subject_request")`:

| carrier | value |
|---|---|
| `json.summary` | `<MARKER>` |
| `json.retired_reason` | unchanged if it holds a D1 vocabulary value; `<MARKER>` if it holds legacy free text (§11.2's legacy treatment: a pre-D1 reason is content) |
| `episode_event` row (new table, `edge_event`'s shape) | `episode_id=ep-31, kind=redacted, reason=subject_request, state=<the tombstoned serialisation>, recorded_at=…` |

## 4. The receipt (§4b-ii, §4f, §11.5)

Returned to the caller and durable (the receipt's own carrier is bounded: ids,
vocabulary values, booleans, integers, timestamps — no content):

```
{
  "redacted_kind":       "edge",
  "target_id":           "e-7c1a",
  "reason":              "subject_request",
  "carriers_cleared":    ["edges.subject", "edges.relation", "edges.object",
                          "json.subject", "json.relation", "json.object", "json.note",
                          "json.original_relation", "json.provenance.evidence_ref",
                          "edge_event.state[seq=4]", "edge_event.state[seq=9]",
                          "edge_embedding[row deleted]"  (INV-7 — the receipt never carries the removed digest; round-2 F5),
                          "contribution_ledger.payload[id=…]", "wiki[user=u]" (cleared)],
  "marker_version":      1,
  "store_version_before": 41,
  "store_version_after":  42,
  "repeated":            false,
  "surviving_derived":   ["ep-consolidated-8"],          # F6: named, NOT redacted
  "receipts_cleared":    [],                             # §4f at v4: no exact tier exists for ANY domain today
  "receipts_complete":   false,                            # §4f at v4: conservative reporting is the ORDINARY case
  "domains_not_recomputed": ["veracium.supersession-request.v2"]
}
```

A second call on the same target returns the same receipt with
`repeated: true` and writes no event (§4b-ii). If the record itself cannot be
tombstoned (step 1 fails), the operation REFUSES and returns no receipt (§4f's
split: partial-and-say-so applies only once the record is redacted).

## 5. Import of redaction events — the acceptance matrix (§4g)

| # | destination state | source event | outcome | flags on the imported event |
|---|---|---|---|---|
| 1 | holds `e-7c1a`, same version | `redacted` for `e-7c1a` | record and its redaction commit in ONE transaction; every carrier tombstoned; a local `redacted` event written as a NOTICE | `witnessed=false`, `source_origin`, `source_seq`, `source_txn`, `source_recorded_at` |
| 2 | holds a DIFFERENT version of `e-7c1a` | same | redacted anyway (id match); notice written | as 1, plus `inconsistent=true` |
| 3 | does not hold `e-7c1a` | same | the event is imported as a STANDING NOTICE; if the record arrives later it is redacted on arrival | as 1, plus `pending=true` |
|   | *executed 2026-09-15 (`probe-0041-standing-notice.py`, dev's scratchpad; to be carried as `specs/evidence/0041/standing_notice_probe.py`):* the store TODAY accepts a journal event whose `edge_id` names no row (`PRAGMA foreign_keys` is 0 and `edge_event` declares no FK); `edge_events(user, edge_id)` returns it; **`doctor` reports it as an ERROR** (`refs`: "journaled edge id(s) with no row … the journal outlived its subject"); and `export` carries no events at all (record kinds: edge, episode only — `unknown record kind` for anything else). So the row is REPRESENTABLE but not yet HONEST: §11.4 must amend 0029's doctor `refs` check to classify a `pending` redaction notice as expected, or the standing notice ships as a permanent doctor error. Reported to research for the §4g respin. | — |
| 4 | holds `e-7c1a`, already redacted locally | same | idempotent on `(origin, target_id, event_id)`: no second tombstone, no second event | `repeated=true` |
| 5 | holds `e-7c1a` redacted; a later export from the same source LACKS the event | — | nothing inferred; absence is not un-redaction; no path restores content | — |
| 6 | import with `user_id` remapped `u → u2` | `redacted` for `e-7c1a` under `u` | the event's subject is remapped WITH the record, in the same mapping; the notice lands under `u2` | `source_user=u` retained as metadata |
| 7 | destination already uses the source's `seq=9` / `txn=3` | same | destination-local `seq`/`txn` allocated by the destination's own allocator; source numbers kept ONLY as attributes | `source_seq=9`, `source_txn=3` |
| 8 | the source export has gaps (only redaction events travel) | — | gaps carry no meaning; not repaired; not reported as missing data | — |
| 9 | the event names a `reason` outside the per-operation vocabulary (§11.2) | — | 🔴 RULED v4 (round-2 F4): the record-and-notice UNIT is REFUSED with an explicit failure result — the record is NOT imported un-redacted and the notice is NOT silently discarded; the import reports the refused unit (origin, target_id, event_id, the reason) and the caller decides whether to reject the whole file | — |
| 9a | a tombstone arrives (every content leaf already `<MARKER>`) with NO notice for it | — | accepted as content — it holds none — and FLAGGED (`notice_missing=true`); the local journal records the arrival, never a local redaction (INV-10) | `notice_missing=true` |
| 9b | two notices sharing `(origin, target_id, event_id)` with DIFFERENT bodies | — | an INTEGRITY REFUSAL of the unit (the key is the identity; two bodies under one identity is corruption, not a repeat) | — |
| 9c | `event_id` — the idempotency key's third element | — | DEFINED: the source's `(user_id, seq)` pair, carried as attributes on the imported notice; the destination never reuses it as a local position (§4g's seq/txn rule) | `source_user`, `source_seq` |
| 10 | the event's `target_id` belongs to another user at the destination | — | REFUSED loudly (INV-5's shape); never a silent no-op | — |
| 11 | the record and its event arrive but the transaction fails after the record's write | — | ROLLED BACK whole: no window in which the record exists un-redacted (INV-3, extended to import) | — |

The witness distinction (§4g): every imported notice's local journal line reads
"this store was told that the source redacted X", never "this store redacted
X" — `witnessed=false` is the executable form of that sentence (INV-10).

## 6. Failure cases of the operation itself (§4a, §7, INV-5)

| call | outcome |
|---|---|
| `redact` on an unknown target id | refuses loudly (`UnknownTarget`); no event, no receipt |
| `redact` across users (target belongs to another user) | refuses loudly; no event, no receipt |
| `redact` with a reason outside the redaction operation's vocabulary (§11.2 at v4: reasons are closed PER OPERATION; the seven lifecycle reasons stay theirs) | refuses at the API, before any read |
| `redact` when the record cannot be tombstoned (step 1 fails: a CHECK refuses the marker, a lock cannot be taken) | refuses; nothing written; the content stays and the caller is told |
| `redact` when a supersession receipt's digest domain cannot be recomputed (§4f) | proceeds; `receipts_complete=false` with the domain named |
| an ordinary write to a field holding the marker (`remember`, `correct`, `confirm`, import) | REFUSED (INV-11), not merged |
| a delayed compiler publishing across the redaction | not published: `store_version != v_begin` (§4e, INV-9); the wiki row stays absent and `needs_recompile` reports true |

*Every row above is a claim the implementation must turn into a test; none is
asserted of the shipped code today. The round-1 reproductions in
`round1_reproductions.py` are the negative controls the same tests must first
fail.*
