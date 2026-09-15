> 🔢 **THIS IS 0041, NOT 0040 — the number changed at the adoption boundary
> (dev's catch, 2026-09-15; research verified it in the registry).**
> **`0040` is SPENT.** `specs/allocation.py` records it consumed by a DIFFERENT
> proposal — *"procedural text at the choke point — the store inferring content
> kind from text shape"* — **withdrawn on Quentin's word of 2026-09-08** ("Q1
> answered NO"), its record kept at
> `proposals/0040-procedural-text-at-the-choke-point-WITHDRAWN.md`. The registry
> is explicit: *"a SPENT number that a tree file also holds is a duplicate and
> the gate refuses it"*, and `allocation.py --next` returns **0041**.
>
> **The collision was not hypothetical — it was already on disk.** Two different
> proposals have been sharing `0040` in this one directory for days: the
> withdrawal record and this candidate. Anyone looking up "0040" could have found
> the withdrawal and concluded that targeted redaction was withdrawn, which is
> precisely the confusion the SPENT list exists to prevent.
>
> **Nothing in D1–D4 changes; only the number does.** Quentin's decisions were
> worded against "0040" and stand unaltered.
>
> ⚠️ **TWO OCCURRENCES OF "0040" BELOW ARE LEFT VERBATIM ON PURPOSE, because they
> are QUOTATIONS and renumbering inside a quote would falsify it:** the header's
> *"Write the 0040 …"* (Quentin's own word) and §2b-ii-bis's quotation of the
> pre-v14.1 schema comment. The tree's own references move at adoption, in dev's
> commit.

# Feature spec: targeted redaction

Spec-Status: draft

*Research-authored candidate, 2026-09-12, on Quentin's word **"Write the 0040
candidate"**. Premises already ruled: **C0 answer 2** (the product owes a
redaction/erase surface), **"keep the split"** (ledger rows cascade, judgments
outlive their subject), **the one-month explanation horizon**, and **the
administrator-history limit** (landed `f4d607a`). The journal decision in §4c is
research's recommendation, approved in principle; the reviewer should attack it
first.*

| | |
|---|---|
| **Author / session** | research (veracium-research), the candidate's author → dev (veracium-61), adopted 2026-09-15 from `0041-targeted-redaction-CANDIDATE.md` at rest (sha16 eecd5a4db4426058, re-read from the file at adoption) |
| **Version** | **v2 — internal review folded into the BODY** (v1 carried it as a banner only). *Re-read before editing; quote the version you approve* |
| **Internal reviewers** | dev · research |
| **External review** | **required** — touches `store/sqlite.py`, `store/edge_events.py`, `store/schema_version.py` |
| **Decision + date** | — |
| **Path** | **full** |

> ## 📥 DEV'S INTERNAL READ — RECEIVED AND FOLDED 2026-09-13. Eight items; research verified three at the tree and WIDENED the blocking one.
>
> **Status: v1 is NOT clean. Item 1 blocks §2/INV-2 and must be fixed before any
> external dispatch.** Dev checked every claim at `17d2f42`; research re-checked
> items 1, 2 and 5 independently rather than folding on the word.
>
> ### 🔴 1. BLOCKING — `edges.subject` is a duplicated column too, and so is `relation`
>
> **VERIFIED at `store/schema_version.py:123-127`.** The DDL is
> `id, user_id, subject TEXT, relation TEXT, object TEXT, active, quarantined, json TEXT`.
> §2 names **only `object`** as "the second site" and INV-2 plants a mutant for
> that one column alone. **Dev found `subject`. Research's re-derivation from
> the DDL finds THREE duplicated columns, not two: `subject`, `relation` and
> `object`.**
>
> **A redaction that tombstones `json.subject` and leaves the column is the §7
> worst outcome** — the content survives in a place nothing looks.
>
> **Fix: INV-2 becomes "every column that duplicates a json field", ENUMERATED
> FROM THE DDL at implementation, with a mutant planted PER COLUMN.** A
> hand-listed carrier set is what produced this hole in the first place —
> derive it from the schema, do not maintain it. **And say why `relation` is
> treated differently if it is** (closed vocabulary rather than user content);
> silently omitting it is how `subject` was omitted.
>
> ### 2. `why` renders event reasons, so the redaction reason reaches a surface
>
> `episodes.json` carries `retired_reason` (`schema.py:822`) and
> `edge_event.reason TEXT` already exists. **`why.py:73` renders event reasons
> (`events: [{seq, txn, kind, reason, at, changed}]`).** So **the redaction
> reason WILL reach the `why` output unless INV-6 says otherwise.** §2c's third
> row is right that this is the ConfirmationActor shape. **Open decision for the
> spec: is `why` inside INV-6's fence? It is a CLI verb — and the spec must say
> whether it is also served through MCP.**
>
> ### 3. `contribution_ledger.payload` is NOT a content carrier — record the negative
>
> The closed per-site payload schemas carry metadata only (`observed_at,
> confidence, valid_from, disclosure, derived_from, basis, author_of_evidence,
> date` — `contribution.py:44-60`). **The "evidence_ref_digest rows" row stands
> as written.** Recorded so a reviewer does not re-derive it.
>
> ### 4. §4a and the wiki row contradict each other for one carrier
>
> *"Invalidated and recompiled, never edited in place"* — **the recompile is a
> model call and cannot sit inside the single transaction §4a promises.**
> Between the transaction and the recompile the wiki `text` still carries the
> content. **"Every carrier or none" and "recompiled" cannot both be true for
> this carrier.** Either the transaction BLANKS the wiki text (invalidate =
> tombstone now, recompile later) or the spec STATES the window. Research's
> view: blank it — a stated window on a privacy operation is a window someone
> will be inside.
>
> ### 🔴 5. §8's survival claim is FALSE across export/import
>
> **VERIFIED independently: `edge_event` appears ZERO times in
> `portability.py`.** It exports edges and episodes. **So a re-import of a
> redacted store carries the tombstoned edge but NOT the `redacted` event**, and
> §8's *"the record that it existed and was redacted survives"* does not hold
> across the boundary. **Either export carries the redacted event, or §8 narrows
> its claim to the live store.**
>
> **And this is where §9's third question bites**, which dev is right to link:
> redaction is not an entitlement operation — except that on re-import **a
> redacted edge without its event is indistinguishable from an edge someone
> simply blanked.**
>
> ### 6. The tombstone gets embedded unless the rebuild skips it
>
> `semantic.py:31 content_digest(edge)` is computed from the edge's content, so
> after redaction **the next index build embeds the TOMBSTONE and writes a fresh
> `edge_embedding` row.** Harmless as an oracle — the pre-image is the public
> marker — but **INV-7's "no `content_digest` survives" is then true of the
> ORIGINAL while a tombstone row reappears.** Decide and state which.
>
> ### 7. v19 removes a carrier, and hands §6 an obligation
>
> A captured procedure's `note` is now empty; the gloss is in `object`, already
> in the table. **But `describe_procedures` renders `object` for procedural
> records**, so §6 needs INV-3's sibling — **describe degrades to "redacted" and
> never fails** — or the tombstone marker is what the host reads back as the
> user's routine.
>
> ### ✅ THE TWO OPEN DECISIONS — DEV'S ANSWERS 2026-09-13, both verified by research at the tree
>
> **(2a) `why` IS OUTSIDE INV-6's FENCE.** `why.py` is imported at exactly ONE
> site (`cli.py:272`); the six `@server.tool()` names are `remember`, `recall`,
> `answer`, `maintain`, `record_procedure`, `describe_procedures` — **no `why`,
> and `Memory` has no biography method.** So `why` is a CLI-operator surface:
> not a prompt, not recall, not export, not MCP — exactly the four names INV-6
> lists. **`why` SHOULD render the redaction reason; the operator asking "why is
> this blank" is its one legitimate reader.** Dev's proposed test is the right
> shape: assert the served tool set BY NAME against 0031's reflected inventory,
> so it fails the day a `why` tool appears rather than the day someone checks.
>
> **(2b) BLANK THE WIKI TEXT IN THE TRANSACTION** and let the next compile
> rebuild. Verified safe, and the branch it takes is worth naming in the spec:
> the recompile trigger (`compile.py:160-168`) has two — `cached is None`
> (branch 1) and a policy-digest mismatch parsed **out of the stored text**
> (branch 2). **Blanking takes BRANCH 2.** Research ran it: `_split_envelope('')`
> returns `(None, '')`, so the digest never matches and recompile fires.
> ⚠️ **Deleting the ROW would take branch 1, which is unconditional.** Dev's own
> argument — *"a blank row is the same shape the store has before its first
> compile"* — describes branch 1, but before the first compile there is **no
> row**, not an empty one. **Either works; the spec must say which branch carries
> the guarantee**, because the two have different dependencies and only one is
> visible in the sentence.
>
> ### 🔴 AND A CROSS-FINDING NEITHER ANSWER SEES ALONE: (2a) AND ITEM 5 COLLIDE
>
> **`edge_event.reason` is free TEXT** (`schema_version.py:490`). Under (2a)
> `why` renders it — so an operator who writes *"redacted: user's HIV status"*
> into the reason has put the content back into the store, **in a field §2 does
> not enumerate as a carrier.**
>
> **It is confined today by exactly two facts: `why` is not in MCP, and
> `edge_event` IS NOT EXPORTED** (item 5: zero occurrences in `portability.py`).
> **But item 5's fix is to make the redacted event exportable — which removes
> the confinement (2a) relies on.** The fix for one item dissolves the other's
> premise.
>
> **Three genuinely different resolutions, none recommended here:** constrain
> the reason to a CLOSED VOCABULARY (cheapest; makes the field a non-carrier by
> construction) · export the event **without** the reason (keeps §8's claim and
> the confinement; costs an asymmetric export shape) · narrow §8 to the live
> store and leave the reason free (costs the survival claim that motivated
> item 5).
>
> **Either way §2's enumeration MUST NAME `edge_event.reason`, even while it is
> confined.** An unenumerated carrier is exactly how `subject` was missed, and
> *"it cannot travel today"* is a property of two other decisions rather than of
> the field.
>
> ### 8. Line drift
>
> The `(true value: …)` write is at `__init__.py:1683`, not `:1681`.
>
> ### What dev did NOT find, recorded because a negative from a full sweep is worth as much as a hit
>
> **No other TEXT/BLOB column carries content** — confirmations,
> consolidation_ops, supersession_*, source_revocations, store_identity and
> store_epoch hold ids, digests and timestamps. ⚠️ **`Edge`'s json string fields
> were NOT enumerated from the model** (the DDL cannot see inside `json`), and
> **the spec must not claim that enumeration until someone has done it.**

> ## ⚠️ §3'S CARRIER ENUMERATION CHANGES WHEN 0037 v19 LANDS — dev's answer, 2026-09-13T14:25Z
>
> Research asked dev, before the internal read, whether v19 adds or removes a
> content carrier — because **§3's enumeration is stale the moment it does**, and
> finding that from an external reviewer would be the worse way to learn it.
>
> **Dev's answer: v19 REMOVES one and ADDS none.** On 0.24.0 a captured
> procedure's `note` held the **verbatim span**; under v19 the span is verified
> and **discarded**, so the note is empty. The gloss stays in `object` as before;
> `procedural_refused` is a count; **no digest is stored** — dev cites this
> document's own §4 confirmation-oracle argument as the reason.
>
> **So §3 loses one row and gains nothing.** *(Do not edit the enumeration until
> v19 is actually on main — the candidate should describe what is shipped, not
> what is intended.)*

---

## 1. Problem and motivation

**Three independent routes reached the same missing capability**, which is why
this is a spec rather than a backlog item:

1. **C0 (ruled).** The one real deployment holds third-party content — 7,023 of
   7,023 note-bearing edges are third-party in origin. A correspondent asking for
   their content removed has **no targeted path**: `delete_episode` is a silent
   no-op for confirmation episodes' siblings, `source_id` is NULL on all 7,154
   edges so 0022 revocation cannot fire, and `forget_user` removes everything.
2. **T12.** `delete_episode` **refuses** outcome-chain links (0009 H14), so
   deleting supporting content does not delete the judgment built on it.
   Append-only history and privacy deletion contradict each other today.
3. **The embedded value.** `__init__.py:1681` writes
   `f" (true value: {corrected_value})"` into a judgment's summary, **so a
   `CORRECTED` judgment carries user-supplied content inside a chain nothing can
   remove short of `forget_user`.**

**All three need CONTENT gone, not RECORDS gone.** That distinction is the
spec's spine: the existing refusals (0009 H14, 0010 X21) are deliberate fences
against *"the unfenced-door class"*, and **a deletion operation that relaxed them
would be the exact failure they were built to prevent.**

## 2. Field contracts touched

> **🔧 DERIVED, NOT HAND-MAINTAINED — v3.** This table is produced by
> `0041-carrier-enumeration.py`, which reads the DDL **and** the pydantic models,
> because neither sees what the other does: SQL cannot look inside `edges.json`,
> and the models cannot see that three columns duplicate what the blob holds.
> **v1 hand-listed one duplicated column and INV-2 planted one mutant. There are
> three.** Re-run the script rather than editing this table.
>
> ### 🔴 v3, 2026-09-13 — AND THE DERIVED ENUMERATION ITSELF SWEPT ONE TABLE OF FOURTEEN
>
> **The script read `SCHEMA_V1` and looped over `edges`.** The live schema is
> `SCHEMA_V13`. Eleven tables were outside its corpus — **including
> `edge_event`, `edge_embedding` and `contribution_ledger`, which the table
> below already names**, so the enumeration had never confirmed the very rows it
> was cited as deriving. It looked correct because its `edges` output was
> correct. **A derivation is only as wide as its corpus; "derived" is a claim
> about the corpus, not about the method.** The script now resolves the newest
> `SCHEMA_Vn` by version number, so the receipt's v14 table enters the sweep
> with nobody remembering to add it. **The widened sweep's findings are §2b.**

| carrier | field | change |
|---|---|---|
| `edges` | `json.subject`, `json.relation`, `json.object`, `json.note` | content replaced by the tombstone |
| `edges` | 🔴 **`subject`, `relation` AND `object` COLUMNS** | **same values, second site — THREE columns, not one.** INV-2 plants a mutant **per column**, enumerated from the DDL at implementation |
| `edges` | 🔴 **`json.invalidation_reason`** | **free text, newly enumerated.** Nobody had named it; it is the same shape as `edge_event.reason` below |
| `edges` | `json.original_relation`, `json.supersedes` | identifiers/vocabulary, not user content — **stated so the negative is recorded** |
| `edges` | `json.evidence_ref`, `json.source_id`, `json.origin` | host-supplied identifiers — §8's limit applies, not redacted here |
| `episodes` | `json.summary` | content replaced; **includes the embedded `(true value: …)`** |
| `wiki` | **the ROW** | 🔴 **DELETE THE ROW in the transaction** (v2, dev's answer as amended). v1 said *"invalidated and recompiled"* — **the recompile is a model call and cannot sit inside the transaction**, so the content stayed in the row for the whole window and *"every carrier or none"* was false for this one. **Deleting takes `compile.py:161`'s `cached is None` branch, which is unconditional**; blanking the text takes the digest-mismatch branch, which works only because `_split_envelope('')` returns a non-matching digest — verified, but a guarantee resting on a parser's behaviour on empty input |
| `edge_embedding` | `vector` | **dropped** |
| `edge_embedding` | `content_digest` | **dropped** — see §2c |
| `contribution_ledger` | `evidence_ref_digest` rows | **dropped** for the redacted survivor |
| `edge_event` | `state` | **tombstoned**, plus a new `redacted` event — §4c |
| `edge_event` | 🔴 **`reason`** | **free TEXT, and A CARRIER — enumerated here even though it cannot travel today.** `why.py:73` renders event reasons and `why` is a CLI-operator surface (verified: imported once at `cli.py:272`; not among the six MCP tools). **Its confinement is a property of TWO OTHER DECISIONS — that `why` stays out of MCP, and that `edge_event` stays unexported — and §8's fix proposes changing the second.** See the decisions below |

**Nothing structural changes.** No row is deleted, no `seq` shifts, no reference
is orphaned. That is why this is redaction and not deletion.

## 2b. The other eight tables — swept 2026-09-13, three carriers found

*The table above names six tables. `SCHEMA_V13` has fourteen. **The eight never
examined are enumerated here with a verdict each, because an unexamined table
and a cleared one are indistinguishable in a document that simply omits both.***

### Carriers — must be added to §2's treatment

| carrier | field | why it carries | status |
|---|---|---|---|
| `source_revocations` | 🔴 **`reason`** | **free TEXT, host-supplied** (`revocation.py:122`), written verbatim. **The same shape as `edge_event.reason`, which §2 already classes a carrier** — and §2c's third row exists precisely because a free-form reason "lets a host smuggle prose past the constraints on the other fields." One reason field was found and confined; its twin was not. | **NEW — §2 must treat it as it treats `edge_event.reason`** |
| `supersession_refusals` | 🔴 **`relation`** | the **edge's own `relation` value**, copied at `graph.py:549`. §2's headline finding was *"three columns duplicate the json — not one."* **This is a fourth site, in a different table**, and it survives a redaction that rewrites all three. | **NEW — tombstone with the others** |
| `supersession_operations` | 🔴 **`request_digest`, `logical_request_digest`** | **SHA-256 over `raw_request_snapshot` — "the COMPLETE Edge model dump… EVERY field"** (`contribution.py:213`), which includes `subject`, `relation`, `object`, `note`. **This is the confirmation-oracle class §2c-ii names: it cannot reconstruct the text, but given a candidate it verifies it — and that is exactly why §2 orders `edge_embedding.content_digest` DROPPED.** The oracle 0041 closes in one table stands open in another. | **NEW — and it needs a ruling, D4 below** |

> **🔴 D4 — DECISION REQUIRED. The receipt digest cannot simply be dropped the
> way `content_digest` can, and the difference must be stated rather than
> assumed away.**
>
> **Two honest asymmetries, both against a straight drop:**
> 1. **It is a weaker oracle than `content_digest`.** `content_digest` digests
>    the content alone; this digests the whole edge dump, so confirming a guess
>    requires already holding `id`, `user_id`, every timestamp and every
>    confidence. The guess space is enormously larger. **Weaker is not closed** —
>    an adversary holding a pre-redaction export holds exactly that.
> 2. **It is load-bearing.** It is the replay identity that separates a true
>    retry from a collision (`sqlite.py:1127` refuses at write via
>    `validate_receipt_state`). **Dropping it does not degrade a receipt; it
>    breaks idempotency for that operation.**
>
> **Research recommends: tombstone the receipt's digest columns to a sentinel
> and record the redaction on the operation, accepting that a replay of a
> redacted supersession can no longer be distinguished from a collision and must
> therefore REFUSE rather than silently re-apply.** A refusal after redaction is
> correct degradation, on the same reasoning §4g already accepted for a receipt
> naming a redacted record — **it becomes unreadable, and unreadable is the
> right answer.** But this trades an availability property for a privacy one and
> **is the owner's call, not research's.**

### Cleared — the negatives, recorded so the sweep is auditable

| table | what it holds | verdict |
|---|---|---|
| `contribution_ledger` | `payload` is a **CLOSED field set** — `observed_at, confidence, valid_from, disclosure` + optional `derived_from, basis` (`contribution.py:48-52`), validated on write. **`basis` is a closed vocabulary** (0037 §4b, `V-BASIS-CLOSED`), not prose. | **not a carrier.** §2's existing row (drop `evidence_ref_digest`) is unchanged and now checked rather than assumed |
| `supersession_operations` | `response` is `effect_payload(result)` — **three integers** (`inserted_incoming`, `invalidated`, `refused`), `sqlite.py:1120` | **not a carrier** (the digests on the same row ARE — above) |
| `confirmations` | `actor`/`call_path` closed enums; `correlation_id` and `request_digest` **host-supplied identity** — §8's limit applies, as it does to `evidence_ref` | **not redacted here; §8's limit, stated** |
| `consolidation_ops` | `operation_id, fence, state, owner, lease_*, claimed_ids` (`sqlite.py:1820`) — lease bookkeeping and identifiers | **not a carrier** |
| `store_epoch` | `started_at` | **not a carrier** |
| `store_identity` | `origin` | **not a carrier** |
| `write_counter` | `user_id` | **not a carrier** |

### 2b-ii-bis. 🔴 THE TABLE SHIPPED, AND NEITHER THE DDL NOR THE CONSTRAINT IS WHAT §2b-ii WAS WRITTEN AGAINST

*Research, 2026-09-14T23:38Z — re-derived at the moment of adoption, because
0027 v14 landed `policy_receipt` after §2b-ii was written and the frozen-candidate
rule makes this the last moment to respin. **The carrier enumeration found it
without being told**: it resolves the newest `SCHEMA_Vn` by version number, so
`SCHEMA_V14`'s fifteenth table appeared on the next run. That widening was made
for exactly this.*

**Three ways the shipped table differs from the one §2b-ii classified.**

**1. The DDL is not three constrained columns — it is a JSON BLOB.** As shipped:

```sql
CREATE TABLE policy_receipt (
  user_id TEXT, recall_id TEXT, policy_id TEXT, policy_version TEXT,
  recorded_at TEXT, receipt TEXT NOT NULL, PRIMARY KEY (user_id, recall_id))
```

`tags_matched` is **not a column**. It lives inside `receipt`, which holds the
receipt's JSON verbatim. **So `policy_receipt.receipt` is a SECOND blob carrier
of the same kind as `edges.json`** — a TEXT column whose interior the schema
cannot describe and a column-level sweep cannot reach. §2 handles `edges.json`
as a special case; **it must now handle two, and the enumeration's section B
warning ("the DDL is blind to these") applies to this column as well.**

**2. The constraint §2b-ii endorsed was never implemented.** Dev's 2026-09-13
reply said the three fields "will constrain them at the model to identifier
shape (letters, digits, `._:-`, ≤64 chars each), refused otherwise, so that the
table carries no free TEXT column". **Measured at v14, all three accept
arbitrary prose:**

| field | value accepted at v14 | lands in |
|---|---|---|
| `policy_id` | `'a whole sentence, with spaces and punctuation.'` | its own TEXT column |
| `policy_version` | `'diagnosis: hiv-positive, disclosed here'` | its own TEXT column |
| `tags_matched` | a 400-character string; a full prose sentence | inside `receipt` |

`PolicyLane.__post_init__` checks `policy_id` and `policy_version` are non-empty
strings and `ranks` is a dict. **`tags_matched` is not validated at all.**

**3. The schema's own comment asserts a property the code does not hold.**
`schema_version.py:510` says `receipt` is *"ids only, never content
(V-RECEIPT-IDS-ONLY), so the table is a new carrier of nothing 0040's
enumeration does not already reach."* **Verified false as shipped:** a recall
with `tags_matched=('diagnosis:hiv-positive', 'a whole sentence about the
patient, with spaces and punctuation.')` stores both strings verbatim in
`policy_receipt.receipt`.

> ✅ **RE-READ AGAINST THE COMMITTED TEXT AND AT REST — research, 2026-09-15T00:03Z.**
> Verified against `181199d` (not the working tree the first pass measured, which
> is the point of the re-read): all **nine** boundary rows and all **eight**
> residual examples reproduce exactly; the schema comment now scopes
> `V-RECEIPT-IDS-ONLY` to the RANKING fields — where it is true — and names the
> identity fields *"bounded, not content-free"* with `receipt` as *"a second blob
> carrier beside `edges.json`"*; `V-POLICY-IDENTIFIERS-BOUNDED` stands at
> `specs/0027-semantic-hybrid-recall.md:838`; the guidance *"a policy tag names a
> policy, not a subject"* is in the spec and the CHANGELOG; and
> `test_an_identifier_shaped_disclosure_is_accepted_and_persisted_the_stated_limit`
> **asserts the limit rather than hiding it.** Nothing in §2b-ii-bis is left
> unverified. **From adoption the frozen-candidate rule binds research too:
> corrections queue as the next version.**

### ⚖️ RESOLVED at v14.1 — dev implemented the constraint AND corrected the comment

*Dev's decision, 2026-09-14, after reproducing the above by execution: constrain
at construction and state the limit honestly rather than choose one. **Verified
here as built**, every boundary:*

| | |
|---|---|
| `policy_id`, `policy_version`, each tag | must match `^[A-Za-z0-9._:-]{1,64}$` |
| refused | a sentence · a 400-char tag · a 65-char id · a `bool` · an empty tag · a tag containing a space · a 65th tag |
| accepted | a 64-char id · 64 tags |

**So the three fields take the bounded-identifier class** — research's row
holding `evidence_ref`, `source_id`, `origin` and
`confirmations.correlation_id` — and **`policy_receipt.receipt` is a second blob
carrier beside `edges.json` whose INTERIOR IS NOW SHAPED**: record ids, numbers,
booleans, ISO timestamps, and identifier-shaped host strings. **That shaping is
a gift to §2's sweep**: unlike `edges.json`, whose interior holds free prose, a
sweep over this blob can be TYPED — it knows what each position may contain, so
a value that is not one of those shapes is itself a finding.

### 🔴 The residual, stated at its true width — the charset forbids PROSE and permits RECORDS

Dev kept the honest half (`diagnosis:hiv-positive` passes and persists). **The
limit is sharper than that example, and a host needs the sharper version.**
Every one of these is accepted at v14.1 and persisted verbatim:

| accepted tag | what it is |
|---|---|
| `ssn:123-45-6789` | a US social security number |
| `dob:1974-03-02` | a date of birth |
| `dx:C50.9` | an ICD-10 diagnosis code |
| `phone:555-123-4567` | a phone number |
| `acct:GB29-NWBK-6016-1331-9268-19` | an IBAN |
| `salary:184000` | a salary |
| `addr:10-downing-st.london` | a street address |
| `diagnosis:hiv-positive`, `hiv`, `is-pregnant` | the original example and its short forms |

> **`[A-Za-z0-9._:-]` is precisely the alphabet of structured identifiers, which
> is precisely the alphabet of most structured PII.** The constraint eliminates
> free-text leakage, which is a real improvement — **and its residual is
> arguably the more dangerous category, because an SSN identifies a person more
> completely than a sentence about them does.** 64 characters is room for an
> IBAN and change.
>
> **The guidance this implies, which belongs in the host documentation rather
> than in a validator: a policy tag names a POLICY, not a SUBJECT.** No rule
> over an alphabet can enforce that distinction — it is a distinction about
> reference, not shape — so it must be said to the host in words and enforced by
> 0041's redaction reach, not pretended away by a charset.

> **§2b-ii's CONCLUSION IS UNCHANGED AND NOW BETTER SUPPORTED.** It disputed
> "closed by construction" on the ground that identifier-SHAPED is not closed —
> *"`diagnosis:hiv-positive` is twenty-one characters, uses only letters and
> `:-`, passes every rule proposed, and is a disclosure."* **That example now
> runs: it is accepted and persisted.** The classification research argued for —
> the class holding `evidence_ref`, `source_id`, `origin` and
> `confirmations.correlation_id` — is the correct row for all three fields, and
> `policy_receipt.receipt` joins `edges.json` as a blob §2 must reach into.

**This is also a PRODUCT finding, not only a spec one**, and 0027 v14 is
unreleased, so it can be fixed before it ships: either implement the constraint
the comment assumes, or correct the comment — but **V-RECEIPT-IDS-ONLY as
written is not true of the code beneath it**, and an invariant name that a
reader trusts is worse than no name.

### 2b-ii. The fourteenth table, classified BEFORE its DDL freezes

*Dev's reply to the sweep, 2026-09-13: commit 2's receipt table carries
`policy_id`, `policy_version` and `tags_matched` — **host-supplied strings** —
and will constrain them at the model to identifier shape (letters, digits,
`._:-`, ≤64 chars each), refused otherwise, so that "the table carries no free
TEXT column and lands in your enumeration as closed by construction."*

**Research endorses the constraint and disputes the classification.** The
tightening is worth shipping: it eliminates sentences, whitespace and
multi-clause prose, and it is strictly better than commit 1's non-empty check.
**But identifier-SHAPED is not closed, and §2c already draws exactly this
distinction.**

> **`ConfirmationActor` is closed because the permitted VALUE SET is finite and
> OURS. These three have an unbounded value set and only a constrained
> ALPHABET.** `diagnosis:hiv-positive` is twenty-one characters, uses only
> letters and `:-`, passes every rule proposed, and is a disclosure. **A charset
> forbids the shape of prose, not the content of a label** — and a label is how
> you say something about a person in few characters.

**So the correct §2b row for these three is the one §2 already has** — the class
holding `evidence_ref`, `source_id`, `origin` and `confirmations.correlation_id`:

| carrier | field | change |
|---|---|---|
| *v14 receipt table* | `policy_id`, `policy_version`, `tags_matched` | **host-supplied identifiers — §8's limit applies, not redacted here.** Identifier-shaped and length-capped by construction (commit 2), which is a real narrowing and not a closure |

**And `tags_matched` should be separated from the other two.** A `policy_id`
names an object the host owns and versions. **A matched tag is an assertion that
FIRED ON THIS RECALL** — the docstring's own words are *"which host tags fired
it"* — so it is a host-chosen label co-located with one user's retrieval.
Whether a given tag describes the policy's trigger, the query, or the user **is
the host's choice and not ours**, which under §2c's untrusted-input discipline
means it must be classified by its worst admissible value, not its intended one.

> **This does not block commit 2 and is not a design objection.** Ship the
> constraint. What changes is one line of documentation: the column set is
> **narrowed**, not closed, and §8's limit is the honest place for it to rest.
> **The risk of recording it as "closed by construction" is that the next sweep
> reads the word "closed" and skips the table** — which is precisely how eleven
> tables went eleven versions unexamined.

> ✅ **SETTLED 2026-09-13, same day.** Dev accepted both halves: commit 2 ships
> the constraint and records the row as **narrowed** — the class holding
> `evidence_ref`, `source_id`, `origin`, `correlation_id`, §8's limit applies,
> not redacted here — **and `tags_matched` is split out and named on its own**,
> classified by its worst admissible value under §2c. **The same words go into
> 0027's v14 amendment and the CHANGELOG line, so a host reads one
> classification in both places rather than two.** Recorded here because the
> disagreement was over a single word and the resolution is the reason the
> table stays inside the swept set.

> **What this sweep cost and what it bought.** It was run only because dev
> announced that receipt commit 2 adds a **fourteenth table**, and the obvious
> question — *can my enumeration see it?* — turned out to have the answer *no,
> and it could not see ten of the existing thirteen either.* **Three carriers in
> tables nobody had looked at, one of them an oracle this very spec orders closed
> elsewhere.** The rule that generalises: **a tool that exists to replace a
> hand-list inherits the hand-list's failure the moment its corpus is pinned to a
> literal.**

## 2c. Untrusted inputs — REQUIRED, blocking

| uncontrolled input | empty | malformed | unrecognised | adversarial | **invariant that pins it** |
|---|---|---|---|---|---|
| **target id** (host-supplied) | refuse, `ValueError` | refuse | **refuse — never a silent no-op** | an id for another `user_id` → refuse | **INV-5** |
| **`user_id`** | refuse | refuse | refuse | cross-user target → refuse | **INV-5** |
| **reason string** (host-supplied, stored) | permitted, stored empty | length-capped | n/a | **prose smuggled into a content-bearing field** → the reason is stored on the `redacted` EVENT, never rendered into a prompt | **INV-6** |
| **data written by an older version** | a pre-0041 store has no `redacted` kind | a `state` that does not parse | baseline events carrying full json | **the whole existing corpus is in this class** | **INV-4** |

> **The third row is the one to read twice.** `ConfirmationActor` was closed as an
> enum precisely because a free-form string *"let a host smuggle prose past the
> constraints on the other fields"* (0008 §6b, finding 7). **A redaction reason is
> the same shape**, and this spec must not reintroduce the hole it is removing.

### 2c-ii. Assertions about reach

- **Consumers of `edge_event.state`: exactly one.** `why.py` parses it and diffs
  consecutive states. **`doctor.py` reads `edge_event` for reference integrity
  only and never touches `state`.**

  *Verified 2026-09-12 by READING the occurrences, not by counting them:
  `doctor.py` contains three matches for "state" and all three are prose — "the
  stated version", "the state the standing set requires", a comment. **A grep
  count alone would have read as a contradiction of this assertion.** Recorded
  because §2c-ii exists for claims that turn out wrong on checking, and this one
  looked wrong until it was read.*
- **Producers of `edge_event`: one choke point**, `_journal_edge_write`, plus
  `journal_baselines` at migration.
- **`content_digest` is not a vector and not reversible — it is a CONFIRMATION
  ORACLE.** It cannot reconstruct the text; given a candidate it verifies it.
  **Dropping the vector and keeping the digest would leave the oracle standing.**

## 3. Trust-class matrix — REQUIRED, blocking

**Enumerate from `EvidenceAuthor` and `Disclosure` at implementation time, not
from this table.** The operation is uniform across classes by design:

| author class of the target | redaction permitted? | rationale |
|---|---|---|
| `USER` | **yes** | the subject's own content is the primary case |
| `SYSTEM` | **yes** | derived content can carry the same text |
| `ASSISTANT` | **yes** | same |
| `THIRD_PARTY` | **yes — the motivating case** | C0's correspondents |

> **Redaction does NOT consult the authority ladder, and that is deliberate.**
> `permitted()` governs who may RETIRE a record — a claim about truth. Redaction
> makes no claim about truth; it removes content. **Gating redaction on authority
> would mean a low-authority party could not have their own content removed**,
> which inverts the purpose. **Authorisation is §3b's subject, not the ladder's.**

## 3b. Authorization and scope

Under C1's ruled model — embedded, operator and policy controller the same party
— **redaction is a host-invoked operation**, like `forget_user`. The library does
not decide who may request it; the host does, and the spec says so rather than
implying a model the deployment does not have.

**Out of scope for v1:** a self-service path for a data subject who is not the
operator. **C0 named that party and C2 ruled they are not separately modelled in
v1**; when C2 changes, this section is the one that reopens.

## 4. Behaviour

### 4a. The operation

`redact(user_id, *, edge_id | episode_id, reason) -> RedactionReceipt`

Single transaction. Every carrier in §2 or none.

### 4b. The tombstone

A single reserved marker, distinguishable from a legitimately empty field.
**`state TEXT NOT NULL` already forbids a silent blank**, so the schema enforces
an explicit marker rather than leaving it to discipline.

### 4c. The journal — the decision this spec exists to make

**`edge_event.state` holds the edge's FULL JSON as found** (0029 V-BASELINE:
*"the bytes, not a re-serialization"*), and every write journals through the same
choke point. **So redacting the live row alone is cosmetic: every prior version
remains in the journal, in the same file.**

**RULED APPROACH: tombstone `state` on every event for the redacted edge, and
append a new `redacted` event recording the redaction.**

`created` → `mutated` → **`redacted`**, with its own `seq`, `txn`,
`recorded_at`, and the reason.

**Why this is not a hole:** the journal exists to record the sequence of writes,
and **a redaction is a write.** Removing content while leaving no record of the
removal would be the hole; recording the removal preserves the property the
journal is for. **It composes with the administrator ruling already landed
(`f4d607a`): the journal was never tamper-evidence against the operator, so
nothing that was being claimed is lost.**

**Cost, stated:** `veracium why` can no longer show WHAT a redacted edge said,
only that fields moved and when. **`why` must render "redacted" and must not
fail** — see INV-3.

### 4d. What redaction does NOT do

- **It does not delete rows.** Chains, seqs and references are untouched.
- **It does not retire, quarantine or supersede.** Those are entitlement
  operations; redaction is not one, and conflating them would put a
  content-removal request on the trust surface.
- **It is not reversible.** A reversible redaction is not a redaction.
- **A redacted edge remains recallable** — structurally present, content absent.
  Otherwise redaction becomes deletion by another name and reopens every fence.

## 5. Regime analysis

| regime | behaviour |
|---|---|
| pre-0041 store, no `redacted` kind | migration adds the kind; **existing baseline events carry full json and are redactable by the same operation** |
| semantic lane enabled | vector and digest dropped; **next recall simply has no semantic entry for that edge** |
| semantic lane disabled | no embedding rows to drop; the rest is identical |
| consolidation in flight | the fenced primitives own claimed ids — **redaction of a claimed input must refuse and say why**, not proceed (0010 X21's shape) |
| `forget_user` afterwards | unaffected; wholesale erasure still removes everything |

## 6. Invariants and executable checks — REQUIRED, blocking

| invariant | executable check | where |
|---|---|---|
| **INV-1 structure preserved** — after redaction, chain lengths, `seq` contiguity and reference integrity are unchanged | redact mid-chain; assert chain length, every `seq`, and `doctor` clean | CI |
| **INV-2 no partial carrier** — the duplicated `edges.object` column and the json agree after redaction | planted mutant that redacts json only; the check must fail | CI |
| **INV-3 `why` degrades, never fails** | `why` on a redacted edge returns a biography whose mutation diff is "redacted" | CI |
| **INV-4 journal carries no residue** — no event for a redacted edge yields the original content | sweep every `edge_event.state` for that edge id; assert tombstone | CI |
| **INV-5 scope** — cross-user or unknown target refuses loudly | `pytest.raises` on each; **never a silent no-op** (the `delete_episode` defect's shape) | CI |
| **INV-6 reason is not a content channel** — the reason never reaches a prompt, recall, export or MCP surface | the 0022 §7a seam sweep pattern, extended to the reason | CI |
| **INV-7 oracle disposal** — no `content_digest` or `evidence_ref_digest` survives for redacted content | assert both row sets empty | CI |

**INV-2 and INV-7 are the two a reasonable implementation gets wrong**, which is
why both carry planted mutants rather than positive assertions alone.

## 7. Failure modes and reversibility

| failure | consequence | mitigation |
|---|---|---|
| partial redaction (one carrier missed) | **content survives while the record says redacted — the worst outcome available** | INV-2, INV-7, and the single transaction |
| redaction of the wrong id | irreversible content loss | INV-5; refuse on anything unrecognised |
| `why` crashes on a tombstone | a DX verb broken by a privacy feature | INV-3 |
| reason used as a content channel | reintroduces the hole 0008 closed | INV-6 |

**Reversibility: none, by design.** The mitigation is refusal on doubt, not undo.

## 8. Claims and limits

**Claimed:** after redaction, the named content is absent from every carrier this
spec enumerates, **and the record that it existed and was redacted survives IN
THE LIVE STORE.**

> 🔴 **v1 CLAIMED THAT SURVIVAL WITHOUT THE QUALIFIER, AND IT WAS FALSE ACROSS
> EXPORT/IMPORT.** Verified independently by both seats: **`edge_event` appears
> ZERO times in `portability.py`**, which exports edges and episodes. So a
> re-import carries the tombstoned edge and **not** the `redacted` event — and a
> redacted edge without its event **is indistinguishable from an edge someone
> simply blanked**, which is §9's entitlement question arriving by the back door.
> **The claim is narrowed to the live store until the decision below is taken.**

**NOT claimed:**
- **that the content is unrecoverable from a copy of the file taken earlier.**
  Redaction is not retroactive across backups, and no embedded product can make
  it so.
- **that redaction is detectable as complete by the redacting party alone** — the
  administrator-history limit applies here as everywhere (`f4d607a`).
- **that `evidence_ref` names resolved by the host are redacted** — Veracium does
  not hold them. **The host's own copy is the host's obligation**, and C0's
  `source_id` requirement is the handle for it.

## 9. Brief for the external reviewer

**Attack §4c first.** The journal decision is the one that is a judgement rather
than a derivation: tombstoning `state` removes content from the product's only
history artifact, and the argument that this is acceptable rests on the
administrator ruling landed the same day. **If that argument is wrong, the spec
is wrong at its centre.**

**Second: §2's carrier list is the whole safety claim.** It was enumerated from
the schema, not from a design discussion — the duplicated `object` column, the
`content_digest` oracle and the journal are the three a design discussion would
miss. **A carrier this list omits is a silent partial redaction, which §7 names
as the worst outcome available.**

**Third: is §3's refusal to consult the authority ladder right?** Research argues
redaction makes no claim about truth and gating it on authority would prevent a
low-authority party removing their own content. A reviewer may see an entitlement
effect research does not.

## 9b. ⚖️ FOUR DECISIONS — ALL RULED BY THE OWNER 2026-09-14

> **⚖️ RULED, research session 2026-09-14:**
>
> | | ruling |
> |---|---|
> | **D1** | **the CLOSED VOCABULARY.** And it binds the SHAPE, not one field — the enumeration has found **three** host-supplied reason fields (`edge_event.reason`, `Edge.invalidation_reason`, `source_revocations.reason`); all three close, or the next sweep finds a fourth |
> | **D2** | **RULED IN THE OWNER'S OWN WORDS: *"carry it — but carry only the redacted events, not the journal."*** The constraint is his instruction, **not research's gloss on a one-word yes** |
> | **D3** | **SKIP redacted edges in the semantic rebuild** |
> | **D4** | **TOMBSTONE the receipt's request digest**, and a replay of a redacted supersession REFUSES rather than silently re-applying |
>
> **D2's reasoning, recorded because the question was put to research rather than
> answered by the document — and then RULED back in the owner's own words,
> constraint included, so the narrowing is not research's to soften or widen.** D1(a) removes the only objection: a vocabulary
> reason carries no content, so the event exports safely. The harm of NOT
> carrying it is sharper than a lost claim — **a re-imported tombstone is
> indistinguishable from a record someone simply blanked**, so a lawful redaction
> and arbitrary tampering read identically after a round-trip, which is §9's
> entitlement question arriving by the back door.
>
> 🔴 **But "carry the event" must not become "export the journal." Verified:
> `edge_event` appears ZERO times in `portability.py` — it has never been
> exported at all.** The journal holds every state transition for every edge;
> newly exporting it is a large disclosure surface unrelated to redaction and
> would need its own review. **So: `edge_event` rows of kind `redacted` ONLY.**
> **Consequence: `FORMAT_VERSION` bumps under 0025/0026 §3d** (a new exported
> field bumps the format so an old reader refuses rather than sheds it) — 12→13,
> after the producer field's 11→12.



**Each is a real fork with a cost on both sides. Research states a preference and
does not pick.**

### D1 — the `edge_event.reason` field

It is free TEXT and `why` renders it. An operator who writes *"redacted: the
user's HIV status"* into the reason has put the content back into the store.

| option | buys | costs |
|---|---|---|
| **(a) closed vocabulary** *(dev's recommendation; research concurs)* | **makes the field a non-carrier BY CONSTRUCTION**; 0008's `ConfirmationActor` precedent for the same hole; lets the redacted event export freely | the operator loses free prose — **which they should not be writing into a store they are redacting** |
| (b) export the event WITHOUT the reason | keeps §8's survival claim and the confinement | an asymmetric export shape someone must remember |
| (c) narrow §8 to the live store, leave the reason free | nothing changes | **costs the survival claim that motivated raising it** |

> ⚠️ **And D1 now reaches further than the event: the derived enumeration found
> `Edge.invalidation_reason`, free text on the edge itself.** Whatever is decided
> for one reason field should be decided for both, or the next enumeration finds
> the other one.
>
> 🔴 **It did. The widened sweep (§2b) found a THIRD free-text reason —
> `source_revocations.reason` — in a table this spec had never examined.** The
> sentence above was written as a warning and came true within the day.
> **So D1 is not a decision about one field: it is a decision about the SHAPE
> "host-supplied reason string", and it must be applied to every instance the
> enumeration returns, now and at each future sweep.** Three are known:
> `edge_event.reason`, `Edge.invalidation_reason`, `source_revocations.reason`.

### D2 — does `export` carry the `redacted` event?

**Coupled to D1 and that is the point.** Carrying the event restores §8's
survival claim across re-import; it also carries whatever the reason holds.
**Under D1(a) the coupling dissolves** and the event can export safely.

### D3 — does the semantic rebuild skip redacted edges?

If not, the tombstone is embedded and a fresh `edge_embedding` row appears.
**Harmless as an oracle** — the pre-image is the public marker — **but INV-7 must
then say it is true of the ORIGINAL digest and not of the row.** Research's
preference: **skip redacted edges**, because an invariant needing a footnote
about which row it means is one nobody will hold.


### D4 — the supersession receipt's request digest

**Stated in full at §2b, where the evidence is.** In one line: the receipt
carries a SHA-256 over the complete edge dump, which is the confirmation-oracle
class §2 orders dropped for `edge_embedding.content_digest` — but here the
digest is the replay identity, so dropping it converts a privacy hole into an
idempotency hole. **Research recommends tombstoning it and letting a replay of a
redacted supersession REFUSE; that is a trade of availability for privacy and is
the owner's to make.**

## 10. Open questions

1. **Does redaction propagate to consolidated outputs** whose `lineage` names a
   redacted input? Research's view: the output is separately-authored content and
   is redacted separately if it carries the text — but this is unverified and
   0010's lineage rules govern.
2. ~~**Should a redacted edge's `content_digest` removal invalidate the semantic
   index's freshness bookkeeping**, or is absence sufficient?~~ **ANSWERED
   2026-09-13 (dev, against the tree):** `semantic.py:31 content_digest(edge)` is
   computed from the edge's content, so after redaction **the tombstone has its
   own digest and the next index build EMBEDS THE TOMBSTONE**, writing a fresh
   `edge_embedding` row. Harmless as an oracle — the pre-image is the public
   marker — **but INV-7's *"no `content_digest` survives"* is then true of the
   ORIGINAL while a tombstone row reappears.** Absence is sufficient **only if
   the rebuild skips redacted edges**; the spec must say which it wants.
3. ~~**Does `export` carry tombstones or omit redacted records?**~~ **NO LONGER
   OPEN — it is now a DECISION, see below.** Export carries the tombstoned edge
   and **not** the `redacted` event, because `edge_event` is not exported at all.
