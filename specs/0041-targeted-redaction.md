> # 0041 v3 — RESPUN FOR THE ROUND-1 RETURN, 2026-09-15
>
> **All seven findings are addressed, and all seven were spec-level.** F1 §2/§2d/§2e
> (the enumeration's own model set was a hand-list — the fourth failure of one
> class in this file); F2 §4e (publication-time validation; the delayed compiler
> undoes a redaction and stamps it current); F3 §4b/4b-ii/4b-iii (the marker
> defined and validated — `TEXT NOT NULL` permits `""`; the episode record; the
> reader inventory, where a sentinel currently reads as `MALFORMED`); F4 §4f (the
> receipt selection rule and the conservative outcome); F5 §4g (the import
> contract); F6 §10.1/§8 (**ruled by the owner: outputs are separate**); F7 §11
> (**the operative contract — everything above §11 is historical discussion**).
>
> **Dev reproduced every executed claim in the verdict at the pin, and the
> enumeration reproduces byte-for-byte in their tree** (`50531999b8caf5f0` /
> `90e1d907ed58560a`, bound by a test node in `specs/evidence/0041/`).
>
> ⚠️ **READ §11 FIRST IF YOU WANT THE CONTRACT.** The four conflicts F7 named
> existed because decisions were recorded where they were taken and the passages
> they invalidated sat elsewhere, still reading true locally. **No paragraph was
> wrong when written**, which is why section-at-a-time review could not see them.

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
| **Author / session** | research (veracium-research), the candidate's author → dev (veracium-61), adopted 2026-09-15 from `0041-targeted-redaction-CANDIDATE.md` at rest (v3: sha16 1d0c0389bef11a3f, re-read from the file at adoption; v2.1 earlier the same day from eecd5a4db4426058) |
| **Version** | **v3.1 — four things folded at adoption from the second seat's exchange over v3 (dev carried, research verified): §4e's exemption of the semantic rebuild, stated with the property it depends on and INV-12 as a test; §4f's two conditions on partial-and-say-so and the refusal split; §4g's standing notice EXECUTED at the tree (representable, but `doctor` reports it as an error and `export` carries no events at all) — §11.4 gains the doctor exemption row and its export/import row is replaced, §8's narrowing is extended to "until a carrier is BUILT"; nothing else moved.** *Prior:* **v3 — RESPUN FOR THE ROUND-1 RETURN, 2026-09-15.** Folds all seven findings: **F1** the carrier inventory rebuilt (§2, §2d, §2e — the enumeration's own model set was a hand-list, and §2's recorded negative on `json.original_relation` was FALSE); **F2** publication-time validation (§4e); **F3** the tombstone defined and the `TEXT NOT NULL` claim withdrawn, plus the episode record and the reader inventory (§4b, §4b-ii, §4b-iii); **F4** the receipt selection rule and its conservative outcome (§4f); **F5** the import contract (§4g); **F6** ⚖️ **RULED BY THE OWNER — *"outputs are separate"*** (§10.1, §8 narrowed); **F7** §11, **THE OPERATIVE CONTRACT — everything above §11 is historical discussion and §11 GOVERNS where they conflict.** *Re-read before editing; quote the version you approve* |
| **Prior chain** | v1 (banner-only internal read) → **v2** (internal review folded into the BODY) → **v2.1** (§2b's table count points forward to the fifteenth table, folded by dev at `436e4d4` before round 1) → **v3** (this) |
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

> ### 🔴 v3, 2026-09-15 — THE ENUMERATION'S OWN MODEL SET WAS A HAND-LIST. FOURTH FAILURE, SAME CLASS.
>
> The round-1 reviewer found this section missing `Edge.original_relation`,
> `Episode.retired_reason`, and `agreement.markers` under a foreign lexicon
> version. **They were missing together, and the reason they were missing
> together is the finding.** Section B of the enumeration read
> `text_fields(Edge)` and `text_fields(Provenance)` — **two model names written
> literally.** `Episode` was never walked, and nesting was never recursed at
> all. So the banner directly above, which corrected this script for reading
> `SCHEMA_V1` when the live schema was `SCHEMA_V13`, **fixed the corpus at the
> DDL source and left the identical defect standing one source lower.**
>
> **That is the fourth failure of one class in one script** — a line-anchored
> DDL regex, `SCHEMA_V1`, the fifteenth table, and now the model set. Each time
> the script looked correct because what it *did* enumerate was enumerated
> correctly. **"Derived" is a claim about the corpus, and this project has now
> paid for that sentence four times in the same file.**
>
> It now discovers every `BaseModel` in `veracium.schema` and recurses through
> nested models, cutting cycles on a visited set rather than a depth limit.
> **11 text-capable fields across 2 hand-named models → 125 across 18
> discovered.** All three fields the reviewer named appear, including
> `agreement.markers` at two levels of nesting.
>
> ### THE 125 ARE NOT 125 CARRIERS, AND THE RAW LIST MUST NOT LAND IN THIS TABLE
>
> 125 is a count of **paths**, not of fields. `ContestedGroup.exposed.note` and
> `SupersessionPlan.incoming_edge.note` are both `Edge.note` reached through a
> container; redacting the field redacts every path to it. **Pasted wholesale,
> this table would inventory `Edge.note` three times and the repetition would
> read as coverage.** Section C of the script collapses every path to its
> terminal `(model, field)` and classifies it:
>
> **84 terminal identities behind 135 paths = 64 carriers + 20 non-carriers + 0
> unresolved.** The bucket sum is asserted, so a field dropped in triage fails
> the run rather than vanishing from this table.
>
> **Two defects in the triage's first pass, both caught by its own controls and
> both pointing the expensive way** — recorded because the same two shapes will
> recur in the implementation:
>
> 1. **A FALSE CLEAN.** Persistence was first derived from `model_validate_json`
>    in `store/`, which sees JSON blobs and nothing else. `SupersessionRefusal`,
>    `Confirmation` and `ContributionRecord` are `INSERT`ed column by column, so
>    all three were reported *"never stored"* — **non-carriers, while being
>    written to disk.** Persistence is now derived from **both** storage
>    disciplines: the JSON round-trip, and the model *being* the row.
> 2. **A DEAD BRANCH THAT READ AS A PASSING CHECK.** The value-space test could
>    not fire: **`pattern=` appears nowhere in `veracium.schema`**, and `Literal`
>    fields never enter the walk. Every non-carrier was one for a reason that
>    check never supplied. It is kept with its emptiness **asserted**, so a field
>    that gains a pattern fails loudly instead of being quietly reclassified.
>
> An intermediate overlap test over-matched the other way, reporting
> `ContestedGroup` stored in `edges` on two shared field names. **Subset — the
> model IS the row — is the property that actually means "this is stored".**
>
> ### ⚠️ THE SENTENCE THIS SECTION MUST CARRY: THE NEGATIVES ARE STORAGE, NOT SHAPE
>
> **Every one of the 20 non-carriers is a non-carrier because it never reaches
> disk — NOT because its content is constrained.** Nothing in `veracium.schema`
> bounds a text value. `CorrectionAuthorisation.principal`,
> `OutcomeJudgmentDraft.summary` and `Relation.desc` hold whatever a caller puts
> in them; they are clear only while nothing persists them. **If any of these
> gains a storage site, all twenty become carriers at once**, and this table
> will be wrong without a single line of it changing.
>
> They are therefore recorded below as **excluded-by-storage**, never as
> excluded-by-shape, and the enumeration must be re-run at any change to what is
> persisted — not only at a schema change.
>
> ### The three the reviewer named, with their treatment
>
> | field | why it was missed | treatment |
> |---|---|---|
> | `Edge.original_relation` | `Edge` *was* walked; v1 classified this field as *"identifiers/vocabulary, not user content"* — see the row below, now **corrected**. Dev's reproduction confirms an unrecognised extractor relation lands here **verbatim** (`relation` becomes `unclassified`, the prose is kept) and **exports** | **content replaced by the tombstone.** It is extractor-supplied prose, not vocabulary |
> | `Episode.retired_reason` | `Episode` was never in the corpus — no model but `Edge` and `Provenance` was walked | **D1 applies.** It is the shape *"host-supplied reason string"*, the fourth known instance after `edge_event.reason`, `Edge.invalidation_reason` and `source_revocations.reason`. Dev's reproduction confirms prose through the sole retirement writer (`_retire_episode_row`), persisted and exported |
> | `agreement.markers` | nested two levels down; the walk did not recurse | **content replaced.** Under a **foreign lexicon version** the record is validated as opaque closed shapes only (0026-R7-1), so marker text is **not** vocabulary-constrained and carries prose — reproduced by dev, persists and exports |
>
> **`Edge.original_relation` is the one that matters most here**, because this
> table already named it and named it *wrong*: it sat in the "stated so the
> negative is recorded" row. **A recorded negative is load-bearing — a later
> reader trusts it instead of checking — and this one was false.**

| carrier | field | change |
|---|---|---|
| `edges` | `json.subject`, `json.relation`, `json.object`, `json.note` | content replaced by the tombstone |
| `edges` | 🔴 **`subject`, `relation` AND `object` COLUMNS** | **same values, second site — THREE columns, not one.** INV-2 plants a mutant **per column**, enumerated from the DDL at implementation |
| `edges` | 🔴 **`json.invalidation_reason`** | **free text, newly enumerated.** Nobody had named it; it is the same shape as `edge_event.reason` below |
| `edges` | 🔴 **`json.original_relation`** | **CORRECTED v3 — this row previously read *"identifiers/vocabulary, not user content"*, and that recorded negative is FALSE.** An extractor relation the registry does not recognise is kept **verbatim** here while `relation` becomes `unclassified`; it persists and exports (reproduced by dev at the round-1 pin). **Content replaced by the tombstone** |
| `edges` | `json.supersedes` | identifier, not user content — **stated so the negative is recorded**, and re-derived at v3 rather than inherited from the row it used to share with `original_relation` |
| `episodes` | 🔴 **`json.retired_reason`** | **free text, newly enumerated at v3 — `Episode` had never been in the enumeration's corpus.** **D1 applies**: the shape *"host-supplied reason string"*, fourth known instance. Prose reaches it through `_retire_episode_row`, persists and exports |
| `edges` | 🔴 **`json.agreement.markers`** | **newly enumerated at v3** (nested two levels; the walk did not recurse). Under a **foreign lexicon version** the record is validated as opaque closed shapes only (0026-R7-1), so markers are **not** vocabulary-bound and carry prose. **Content replaced** |
| `edges` | `json.evidence_ref`, `json.source_id`, `json.origin` | host-supplied identifiers — §8's limit applies, not redacted here |
| `episodes` | `json.summary` | content replaced; **includes the embedded `(true value: …)`** |
| `wiki` | **the ROW** | 🔴 **DELETE THE ROW in the transaction** (v2, dev's answer as amended). v1 said *"invalidated and recompiled"* — **the recompile is a model call and cannot sit inside the transaction**, so the content stayed in the row for the whole window and *"every carrier or none"* was false for this one. **Deleting takes `compile.py:161`'s `cached is None` branch, which is unconditional**; blanking the text takes the digest-mismatch branch, which works only because `_split_envelope('')` returns a non-matching digest — verified, but a guarantee resting on a parser's behaviour on empty input |
| `edge_embedding` | `vector` | **dropped** |
| `edge_embedding` | `content_digest` | **dropped** — see §2c |
| `contribution_ledger` | `evidence_ref_digest` rows | **dropped** for the redacted survivor |
| `edge_event` | `state` | **tombstoned**, plus a new `redacted` event — §4c |
| `edge_event` | 🔴 **`reason`** | **free TEXT, and A CARRIER — enumerated here even though it cannot travel today.** `why.py:73` renders event reasons and `why` is a CLI-operator surface (verified: imported once at `cli.py:272`; not among the six MCP tools). **Its confinement is a property of TWO OTHER DECISIONS — that `why` stays out of MCP, and that `edge_event` stays unexported — and §8's fix proposes changing the second.** See the decisions below |

**Nothing structural changes IN THE RECORD TABLES.** No `edges` or `episodes`
row is deleted, no `seq` shifts, no reference is orphaned. That is why this is
redaction and not deletion.

> 🔴 **CORRECTED v3 (F7).** This paragraph read *"No row is deleted"* flatly,
> while the table directly above it **deletes the `wiki` row**, drops
> `edge_embedding` rows and drops `contribution_ledger` rows. **Three deletions
> named in the table and denied in the sentence under it.** The distinction that
> was meant is between **records** — never deleted, which is the whole claim —
> and **derived rows**, which are rebuildable and carry no history. Stated that
> way it is true and it is the property that matters; stated flatly it was
> simply false, and it is the kind of false a reader accepts because it sounds
> like a summary of what they just read.

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
| **reason string** (host-supplied, stored) | permitted, stored empty | 🔴 **CLOSED VOCABULARY — v3.** This cell read *"length-capped"*, which **D1 superseded**: a length cap on free prose is exactly the hole D1 closed, since the content that matters is short. The value MUST be one of §11's allowed reasons | n/a | **prose smuggled into a content-bearing field** → the reason is stored on the `redacted` EVENT, never rendered into a prompt | **INV-6** |
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

## 2d. The derived inventory — 84 terminal identities, 64 carriers

*Generated by `0041-carrier-enumeration.py` §C. **Do not edit these lists** — re-run the script. Fields are TERMINAL identities: redacting `Edge.note` covers every container path that reaches it.*

### Carriers — where each one reaches disk

| model | storage discipline | text-capable fields |
|---|---|---|
| `AgreementRecord` | nested in `Edge` (inside a `json` blob) | 3 — `direction`, `lexicon`, `markers` |
| `Confirmation` | **ruled** (see §2e): `confirmations` | 5 — `correlation_id`, `edge_id`, `id`, `request_digest`, `user_id` |
| `ConsolidationOp` | is the row: `consolidation_ops` | 5 — `claimed_ids`, `lease_expires_at`, `operation_id`, `owner`, `user_id` |
| `ContributionDraft` | **ruled** (see §2e): `contribution_ledger` | 5 — `contributor_id`, `contributor_type`, `site`, `survivor_id`, `survivor_type` |
| `ContributionRecord` | is the row: `contribution_ledger` | 10 — `contributor_ref`, `contributor_type`, `evidence_ref_digest`, `id`, `identity_digest`, `op_key`, `site`, `survivor_id`, `survivor_type`, `user_id` |
| `Edge` | inside a `json` blob | 10 — `id`, `invalidation_reason`, `note`, `object`, `original_relation`, `outcome_counts`, `relation`, `subject`, `supersedes`, `user_id` |
| `Episode` | inside a `json` blob | 14 — `claimed_by`, `context_ref`, `date`, `date_end`, `date_start`, `edge_id`, `id`, `kind`, `lineage`, `operation_id`, `retired_reason`, `summary`, `supersedes_episode`, `user_id` |
| `Provenance` | nested in `Edge` (inside a `json` blob) | 3 — `evidence_ref`, `origin`, `source_id` |
| `SupersessionRefusal` | is the row: `supersession_refusals` | 6 — `incoming_edge_id`, `prior_edge_id`, `refusal_id`, `relation`, `rule_version`, `user_id` |
| `SupersessionRefusalDraft` | is the row: `supersession_refusals` | 3 — `incoming_edge_id`, `prior_edge_id`, `relation` |

### Excluded BY STORAGE, not by shape — 20 fields

> **Not one of these is constrained.** Each is clear only while nothing
> persists it. A storage site added to any of them makes it a carrier
> with no change to its declaration — so this list expires at any change
> to what is written, not only at a schema change.

| model | why | fields |
|---|---|---|
| `ConsolidationOutputDraft` | never written to disk | `date_end`, `date_start`, `summary` |
| `ContestedGroup` | a **view** assembled from rows, never written (§2e) | `prior_edge_ids`, `relation`, `subject` |
| `ContestedLinkage` | never written to disk | `edge_id`, `partition` |
| `CorrectionAuthorisation` | never written to disk | `kind`, `origin`, `principal`, `prior_edge_id`, `replacement_digest` |
| `OutcomeJudgmentDraft` | never written to disk | `context_ref`, `event_timestamp`, `summary` |
| `Relation` | never written to disk | `desc`, `name` |
| `SupersessionPlan` | never written to disk | `expected_state`, `operation_id` |

### ⚠️ "Carrier" here means CAN HOLD TEXT AND REACHES DISK — not "gets tombstoned"

**The 64 are the candidate set, not the treatment set.** Many are identifiers
(`id`, `user_id`, `request_digest`, `op_key`): they are text-capable and stored,
so the enumeration must return them, but §2's table is where each gets a
*treatment* — replaced, dropped, or **recorded as an explicit negative**.

**The enumeration's job is that nothing is missed; §2's job is that nothing is
mistreated.** Collapsing the two is how `Edge.original_relation` came to sit in
a negative row for two versions: it was classified *by its name* rather than by
what reaches it. **A field is a negative only when something checked what writes
to it** — which is what dev's round-1 reproduction does for the three above.

## 2e. The residual rulings — decided against the WRITE PATH, not the field names

Thirteen fields shared a table's column names without being a row. **They were
held in an UNRESOLVED tier rather than defaulted**: guessing non-carrier loses a
real carrier, and that is the direction that costs something. Each is ruled with
its evidence, and a ruling that outlives its question fails the run.

| model | ruling | evidence |
|---|---|---|
| `Confirmation` | **carrier** | subset failed on `replayed` **alone**, which `schema.py:149` comments *"runtime only: True when returned for a replay"* — not a column. The model **is** the `confirmations` row; `INSERT` at `sqlite.py:588` |
| `ContributionDraft` | **carrier** | subset failed on `contributor_id` **alone**, which is `INSERT`ed into the column `contributor_ref` — `sqlite.py:1236` documents its own rename. The draft's content reaches disk under a different name |
| `ContestedGroup` | **not a storage site** | `exposed`, `linkage` and `prior_edge_ids` are not columns of anything: it is a **view assembled from rows**, never written. Its text is `Edge`'s, already carried. `ContestedLinkage` sits inside it and therefore inherits nothing — **an unresolved container cannot confer persistence on what it holds** |

> **`ContestedGroup.partition` greps clean in `store/` for a reason worth
> recording: every hit is `str.partition()`.** Our own vocabulary, someone
> else's sense — the false-positive shape that grows with the size of the moat.


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

### 4b. The tombstone — v3, REWRITTEN (F3)

> 🔴 **THE SUPPORTING CLAIM WAS FALSE, AND THE REVIEWER RAN IT.** v1 said
> *"`state TEXT NOT NULL` already forbids a silent blank, so the schema enforces
> an explicit marker rather than leaving it to discipline."* **`TEXT NOT NULL`
> permits the empty string** — `NOT NULL` excludes NULL, nothing else —
> confirmed by dev's reproduction at the pin. **So the schema enforced nothing,
> and the sentence claiming it did is why nobody wrote the validation.** An
> invariant asserted of a constraint that does not hold it is worse than no
> invariant: the next reader trusts it instead of checking. (This is the second
> instance in this spec's lineage, after `V-RECEIPT-IDS-ONLY`.)

**The marker, defined rather than named.**

| | |
|---|---|
| **representation** | the exact byte string `\x00veracium:redacted\x00` — a leading NUL makes it unproducible by the extractor, by an LLM body, and by any host string that survives `sanitize_llm_body` |
| **validation** | a `CHECK` constraint per carrier column: the value is the marker **or** it is not the empty string. This is the enforcement v1 claimed `NOT NULL` already provided |
| **distinguishability** | `"" != marker`, so a legitimately empty field and a redacted one are different values. **The test is that the CHECK REJECTS `""` — a positive control, because the failure mode being guarded is precisely that an empty string passes** |
| **inside `json`** | the same marker as the field's value. A JSON blob has no column constraint, so validation is at the write path and INV-2 plants a mutant per carrier field, not per column |

**Why a reserved value and not a flag column:** a flag can disagree with the
content it describes. A marker IS the content, so there is no state in which the
record says redacted and still holds the text.

### 4b-ii. The episode redaction record (F3)

**The API accepts an edge or an episode; §4c defines only an edge journal
event.** `edge_event` is keyed by `edge_id` and cannot carry an episode, so an
episode redaction today would be durable in the record and **invisible in the
journal** — the asymmetry the reviewer named.

| | |
|---|---|
| **durable record** | an `episode_event` row of the same shape as `edge_event` (`episode_id`, `kind`, `reason`, `state`, `recorded_at`), written in the redaction transaction. **`reason` is D1's shape and takes D1's closed vocabulary** — this is the fourth instance (§9b/D1) |
| **receipt fields** | `redacted_kind` (`edge`/`episode`), the target id, the carrier fields cleared, the marker version, the store version **before and after**, and the surviving derived records F6 requires the caller be told about |
| **repeat calls** | **idempotent by content, not by attempt.** A second redaction of an already-redacted target writes **no** new event and returns the original receipt with `repeated=True`. Redaction is not an append-only log of intentions; a log of repeats is itself a signal about the target |
| **repopulation** | an ordinary write whose target field currently holds the marker is **refused**, not merged. Without this the tombstone is advisory: `remember()` on the same subject/relation would supersede it back into content |

> ⚠️ **The repopulation rule is the one with teeth, and it is a constraint on
> the WRITE path, not on redaction.** Redaction that does not change what
> subsequent writes may do is a delete with extra steps.

### 4b-iii. Readers — the inventory was incomplete (F3)

**Journal snapshots feed the 0030 classifier through `edge_state_at()`, and a
plain sentinel currently becomes `MALFORMED`.** A redacted historical read would
therefore not report *redacted*; it would report *corrupt*, which is a different
claim about the store and an alarming one.

| reader | redacted outcome |
|---|---|
| `edge_state_at()` / 0030 classifier | a **`REDACTED` state**, distinct from `MALFORMED`. The classifier must be taught the marker; a sentinel it does not recognise is indistinguishable from damage |
| `recall` | the record is **not returned**. Its absence is not concealment — §4d's existence fact is preserved in the journal, which is where it was already disclosed |
| `describe_procedures` | reports the procedure as redacted rather than omitting it, **subject to the existing visibility restrictions, which are unchanged** — redaction must not become a way to see that a record exists that the caller could not otherwise see |
| `why` | renders the event with D1's vocabulary reason; no free prose |
| `export` | D2 governs; F5 defines the import contract |

**The existing visibility restrictions are preserved in every row above.** A new
state that is visible where the record was not is a disclosure channel, and it
would be introduced by the feature whose purpose is removing disclosure.

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

### 4e. The delayed compiler — publication-time validation (F2)

**A single transaction makes the clearing atomic; it does not govern subsequent
publication.** The reviewer exercised the real compiler: it reads its inputs, a
redaction clears the content and the wiki row, compilation then finishes — and
**the original content reappears in `wiki`, stamped with the CURRENT store
version, with `needs_recompile()` returning false.** The redaction is undone and
the store reports itself fresh.

**The mechanism, read in the shipped code.** `compile_wiki` calls
`_grounded_inputs(store, …)` at the top, then `llm(prompt, …)` — a model call,
seconds to minutes, **outside any transaction** — and finally:

```python
store.set_wiki(user_id, f"{_ENVELOPE}{digest}\n{wiki}",
               store.store_version(user_id))        # compile.py:259
```

**`store_version` is read at PUBLISH time, not at input-read time.** The stamp
therefore describes a store the compiled text was never derived from. The
digest in the envelope covers compiler POLICY (the relation registry, the
budgets), not the inputs, so it does not detect this either — and
`needs_recompile` computes `store_version - version_at_compile`, which is `0`.
**Every component is behaving as written; the defect is that nothing compares
the two states.**

**The rule.** `compile_wiki` captures `v_begin = store.store_version(user_id)`
**before** `_grounded_inputs`, and publication is conditional on it:

| at publish | outcome |
|---|---|
| `store_version == v_begin` | publish, stamped `v_begin` |
| `store_version != v_begin` | 🔴 **DO NOT PUBLISH.** The compiled text is derived from a superseded state. Discard it and leave the wiki row absent — `needs_recompile` then takes `compile.py:161`'s unconditional `cached is None` branch and the next compilation runs against the redacted store |

**Stamping `v_begin` rather than the current version is load-bearing on its
own**, independently of the check: a text derived from version *n* must be
labelled *n*, or `needs_recompile` is answering a question about a state the
content never had. The conditional publish and the honest stamp are two
separate fixes and both are required.

**The redaction transaction's version change, defined (the reviewer's second
ask).** Redaction **MUST** call `_bump(user_id)` inside its transaction. Today
`_bump` is invoked per write method (`sqlite.py:512, 591, 763, 1163, 1542,
1608, 1661, 1833, 2095`) and a method that forgets it is silently invisible to
every version-based staleness check in the product. **A redaction that does not
move the counter is undetectable by the very mechanism above**, so this is a
prerequisite of the fix and not an implementation detail.

> ⚠️ **DELAYED WRITERS ARE A CLASS, AND THE WIKI IS ONE MEMBER.** The shape is:
> *read state → do slow work outside the transaction → write a result stamped as
> current.* **Every such writer can undo a redaction.** The wiki compiler is the
> one the reviewer found. The enumeration cannot find these — they are control
> flow, not fields — so this spec names the shape and requires that each
> read-compute-publish path either carry the `v_begin` check or be recorded here
> as not requiring it, **with the reason**. Known: `compile_wiki`;
> `ensure_wiki` through it. **The semantic rebuild (D3) must be checked against
> this shape before v3 is dispatched** — it reads edges and writes derived rows,
> which is the same silhouette.
>
> **v3.1 — checked, and EXEMPT by construction (dev at source; research verified
> at source).** `embed_backfill` reads edges, embeds outside any transaction, then
> `upsert_embedding` re-reads the LIVE row under the lock and REFUSES when the
> content digest has moved (`sqlite.py`, the embedding upsert; the INSERT is also
> `ON CONFLICT(edge_id, embedder_id, content_digest) DO NOTHING`) — a
> compare-and-set on the content the work was derived from, which is exactly what
> `compile_wiki` lacks. A second, independent guard excludes stale vectors at
> READ time (V-FRESH: a row whose stored digest no longer matches the live edge
> is not returned by search). Episodes are not embedded at all, so §4b-ii raises
> no rebuild question. **The exemption depends on a property neither function
> names:** `embedded_text`'s field set must remain a SUBSET of `content_digest`'s
> (today both are exactly {subject, relation, object, note}). Widening
> `embedded_text` alone — a plausible edit made to improve embedding quality —
> would write back a vector encoding redacted content with both guards passing.
> **INV-12** asserts the subset relation as a TEST derived by mutation
> (`tests/test_0041_evidence.py`), not as a sentence, because a sentence is what
> failed four times in this document's lineage. The wiki compiler's fix (above)
> takes the same shape: `v_begin` captured before the read, publication refused
> if the version moved, the wiki stamped with `v_begin`.

### 4f. Locating affected supersession receipts (F4)

**D4 named the digest fields to clear; the reviewer's point is that naming them
is insufficient without a rule for FINDING the receipts.**
`supersession_operations` stores `logical_request_digest`, `request_digest`,
`response` and an `operation_id` — **digests and an opaque identifier, with no
complete reverse mapping to affected records.** Dev reproduced a supported
operation that updates an existing edge under an arbitrary operation id, writing
a receipt with **zero contribution rows and zero refusal rows naming that
edge**. So the joins that exist can return nothing while a receipt containing
the target's content-derived digest sits in the table.

**The selection rule, in order.**

| step | what it finds | completeness |
|---|---|---|
| 1. **recompute** the target's content-derived digest(s) under **every** digest domain the table records (`request_digest_domain` exists precisely because there is more than one) and match `logical_request_digest` / `request_digest` | receipts whose digest is derivable from the content being redacted | **exact for current-domain receipts** |
| 2. scan `response` for the target id — it is a stored blob and §2's enumeration reaches it | receipts naming the record without a digest match | exact |
| 3. follow `contribution_ledger` and `supersession_refusals` rows naming the target | receipts reachable by the existing joins | **incomplete — this is the path dev's reproduction defeats** |

🔴 **STEP 1 IS INCOMPLETE BY CONSTRUCTION FOR OLDER RECEIPTS, AND THAT IS THE
POINT OF THE CONSERVATIVE OUTCOME.** A digest written under a **retired domain**
cannot be recomputed if the domain's inputs are no longer reconstructible, and a
receipt for an operation affecting a **prior** record may carry a digest over
content that has since been superseded. **Neither is findable by recomputation.**

**The conservative outcome, when the association cannot be established.** The
operation does **not** report success over the receipt table. Specifically:

- redaction of the record proceeds — **the record is the caller's actual ask**;
- every receipt found by steps 1–3 is cleared;
- **the receipt is marked `receipts_complete=False`** with the domains that
  could not be recomputed named in it;
- **§8's success claim is narrowed accordingly** (F6's ruling already limits it
  to the named carriers; this names a second boundary), and the caller is told
  which class of receipt may retain a digest over the redacted content.

> **Why not refuse the whole operation.** Refusing leaves the content in the
> record AND in the receipts. **A partial redaction that says so is strictly
> better than a refusal that says nothing**, provided the incompleteness is in
> the receipt rather than in the prose. The failure mode this spec must avoid is
> not incompleteness — it is **a success claim wider than what was done**.
>
> **v3.1 — two conditions on partial-and-say-so (dev's second opinion, research
> agreed).** (1) The operation is IDEMPOTENT and RE-RUNNABLE: a later call on the
> same target — after a migration adds the reverse mapping, or with a better
> selection rule — finishes the job and flips `receipts_complete` to `True`,
> writing no second event (§4b-ii's repeat rule). (2) The receipt names BOTH the
> digest domains that could not be recomputed AND the operation ids of the
> receipts that were cleared, so a caller can tell *partial* from *nothing*
> without reading the store. And the split, stated: partial-and-say-so applies
> only once the record itself is redacted; if step 1 fails — the record cannot be
> tombstoned — the operation REFUSES, because there the content stays everywhere
> and a receipt would claim an act that did not happen.

### 4g. The import contract for redaction events (F5)

**D2 settles what TRAVELS. It does not settle how a destination ACCEPTS it**,
and an export shape without an import contract is a format change presented as a
guarantee. **A format-version bump alone establishes none of the properties
below** — it announces that the bytes differ, not what a receiver must do.

**Binding.** A redaction event names a record. The destination may hold that
record, hold a different version of it, or not hold it at all.

| destination state | outcome |
|---|---|
| holds the record | apply the redaction **in the same transaction as the record's import**. Records and their redaction state **commit together or not at all** — a window in which the record exists un-redacted is the exact harm this spec exists to prevent |
| holds a **different version** | redact it anyway when the event's target id matches, and record an **inconsistent-notice** flag on the imported event. Content-derived divergence is not grounds to keep content the source says was redacted |
| **does not hold** the record | import the event as a **standing notice**, not a no-op. If the record arrives later it is redacted on arrival. **Dropping the event makes redaction order-dependent**, and import order is not something either side controls 🔴 **v3.1 — EXECUTED, and the row is REPRESENTABLE BUT NOT YET HONEST.** The store accepts a journal event whose `edge_id` names no row (`edge_event` declares no foreign key, `PRAGMA foreign_keys` is 0) and `edge_events(user, edge_id)` returns it — so a standing notice can be written and read today. **But `doctor` reports it as an ERROR** (check `refs`: *"journaled edge id(s) with no row"*), which is correct for every case that existed before this spec and wrong for this one. **As written, row 3 makes a healthy store permanently fail its own health check**, and an operator's rational response to a permanent error is to stop reading the errors. §11.4 amends 0029's `refs` check so a `pending` notice of kind `redacted` is EXPECTED rather than an orphan — a standing notice is the journal outliving its subject **on purpose**, which is the one case 0029's wording was not written against. |
| holds it and the event is **missing** from a later export | **nothing is inferred.** Absence is not un-redaction; there is no path by which an import restores redacted content |

**Repeat imports** are idempotent on `(origin, target_id, event_id)` — the same
event twice is one redaction and one notice, per §4b-ii's content-idempotence.

**User remapping.** An import that remaps `user_id` **must remap the event's
subject with the record's**, in the same mapping. A redaction event that keeps
the source's `user_id` after its record was remapped is **a redaction that no
longer points at anything** — the record survives un-redacted and the store
believes it handled the event.

**`seq` / `txn` — the reviewer's sharpest point.** Exporting **only** redaction
events **creates gaps in the source's sequence**, and the destination **may
already be using those numbers**. Therefore:

| | |
|---|---|
| **never reuse source numbers locally** | imported events are allocated **destination-local** `seq`/`txn` at import, from the destination's own allocator |
| **preserve source metadata** | the source `origin`, source `seq`/`txn` and source timestamp are retained **as attributes of the imported event**, never as its local position |
| **gaps are expected, not repaired** | a gap in the source sequence carries no meaning at the destination and **must not be treated as missing data**, because a partial export is the normal case |
| 🔴 **witness distinction** | an imported notice **must not present as a locally witnessed action.** The local journal says *"this store was told that the source redacted X"*, never *"this store redacted X"*. Collapsing the two makes the destination's journal claim an act it did not perform, and `why` would render it as local history |

> **The witness distinction is the one that matters beyond this spec.** The
> journal's value is that it records what THIS store did. An import that writes
> foreign acts as local acts corrupts that property for every reader, and
> redaction events would be the first records to do it.

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

**Claimed:** after redaction, the named content is absent from **every carrier
this spec enumerates AND NAMES IN THE RECEIPT**, and the record that it existed
and was redacted survives **in the live store**.

> ⚖️ **NARROWED v3 by the owner's F6 ruling — *"outputs are separate."*
> Redacting an input does NOT reach consolidated outputs, or other records
> containing its content.** The claim is bounded to the named carriers, and the
> receipt **names the surviving derived records so the caller can redact them
> too**. See §10.1.
>
> **This is a narrowing of the CLAIM, not of the operation** — the operation
> already did only this. What changes is that a caller is now told what remains
> after a success, which is the thing the reviewer said a caller needs to know.
> **A success claim wider than what was done is the failure mode this spec has
> to avoid**, and it is the same failure as §2's false negative on
> `original_relation`, one level up.

> 🔴 **v1 CLAIMED THAT SURVIVAL WITHOUT THE QUALIFIER, AND IT WAS FALSE ACROSS
> EXPORT/IMPORT.** Verified independently by both seats: **`edge_event` appears
> ZERO times in `portability.py`**, which exports edges and episodes. So a
> re-import carries the tombstoned edge and **not** the `redacted` event — and a
> redacted edge without its event **is indistinguishable from an edge someone
> simply blanked**, which is §9's entitlement question arriving by the back door.
> **The claim is narrowed to the live store until the decision below is taken.**
>
> 🔴 **v3.1 — AND THE NARROWING IS NOT LIFTED BY D2 ALONE.** `export` carries no
> events of any kind today (verified: the record kinds are `edge` and `episode`,
> anything else raises). **The claim stays bounded to the live store until a
> carrier is BUILT**, not until the decision is taken. D2 chose the cargo;
> nothing yet carries it.

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
>
> 🔴 **AND IT HAPPENED A THIRD TIME — v3, 2026-09-15: `Episode.retired_reason`
> is a FOURTH instance**, found once the enumeration stopped hand-naming the
> models it walked (§2). The warning above has now come true twice, on the two
> occasions the corpus was widened, which is the whole of the evidence about
> what widening it again will find.
>
> **D1's four instances: `edge_event.reason`, `Edge.invalidation_reason`,
> `source_revocations.reason`, `Episode.retired_reason`.** Dev's round-1
> reproduction confirms prose reaches the fourth through its sole writer
> (`_retire_episode_row`, the revocation path's `reason`), persists and exports
> — so option (a)'s closed vocabulary must cover it, or the field is the hole
> the other three were closed to prevent.
>
> ⚠️ **AND THE COUNT IS A FLOOR, NOT A TALLY.** Three of the four were found by
> widening the enumeration, each time after this document asserted the set was
> complete. **D1 should therefore be written as a rule over the shape, applied
> by the enumeration at each run, and not as a list of four field names** — a
> list is the artifact that has failed here four times.

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

1. ~~**Does redaction propagate to consolidated outputs** whose `lineage` names a
   redacted input?~~ ⚖️ **RULED BY THE OWNER 2026-09-15 (F6): NO — *"outputs are
   separate."*** Redacting an input does **not** reach consolidated outputs, or
   any other record containing its content. Research's view above was the
   recommendation and it was taken; **what was missing was not the answer but
   its consequence**, which the reviewer supplied:

   | | |
   |---|---|
   | **the operation** | unchanged — it redacts the named carriers of the named record |
   | **the receipt** | 🔴 **MUST NAME THE SURVIVING DERIVED RECORDS**, so the caller can redact them too. An output whose `lineage` names the target is identifiable at redaction time; **leaving the caller to discover it is what made "separate" sound like "absent"** |
   | **the claim** | §8 is bounded to the named carriers |
   | **repeat** | redacting an output is an ordinary redaction of that record; nothing about it is special |

   **§10.1 is CLOSED for v3.** The remaining lineage questions are 0010's, not
   this spec's, and they are about consolidation, not redaction.
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

---

# 11. THE OPERATIVE CONTRACT — v3, 2026-09-15 (F7)

> **Everything above this line is HISTORICAL DISCUSSION.** Where it conflicts
> with this section, **this section governs.** The reviewer found four live
> conflicts between the owner's decisions and passages that were never swept
> when those decisions landed — *"withdraw a claim, sweep its dependents"*,
> which this project has now paid for in both directions.
>
> **Why the conflicts existed, since it is the reusable part.** Each decision was
> recorded **where it was taken** — D1 in §9b, D2 in §9b, the column finding in
> §2 — and the passages those decisions invalidated sat elsewhere and still read
> as true locally. **No individual paragraph was wrong when written.** A spec
> that records decisions in place and never consolidates them accumulates exactly
> this, and it is invisible to any review that reads sections one at a time.

## 11.1 The four conflicts, resolved

| # | conflict | resolution |
|---|---|---|
| 1 | **D1** selects a closed reason vocabulary; **§2c** still permitted length-capped prose | **D1 governs.** §2c's cell is corrected in place. A length cap is not a defence — the content that matters is short |
| 2 | **D2** carries redaction events and vocabulary reasons; **INV-6** prohibited reasons from export and **§10** still said the event is omitted | **D2 governs.** INV-6 is amended below to fence *free* reasons, not vocabulary ones; §10's item 3 is superseded |
| 3 | **§2** requires all three duplicated edge columns; **INV-2** checked only `object` | **§2 governs.** INV-2 is restated to enumerate from the DDL |
| 4 | *"No row is deleted"* vs deleting `wiki`, `edge_embedding` and `contribution_ledger` rows | **the deletions govern.** The sentence is corrected: no **record** row is deleted; **derived** rows are, and they are rebuildable |

## 11.2 The allowed reason values, and legacy treatment

**`reason` is a closed vocabulary on every instance of D1's shape** —
`edge_event.reason`, `Edge.invalidation_reason`, `source_revocations.reason`,
`Episode.retired_reason`.

| value | meaning |
|---|---|
| `subject_request` | the data subject asked |
| `operator_policy` | a standing policy of the operator |
| `erroneous_capture` | the content should never have been stored |
| `legal_obligation` | a demand the operator is bound by |
| `imported_notice` | **set only by import** (§4g) — the source redacted it; this store did not witness the act |

**Legacy treatment, which the vocabulary needs and v1 never addressed.** Rows
predating the constraint hold arbitrary text. They are **not** rewritten — a
migration that edits historical reasons destroys the record it is meant to
preserve. Instead:

- the **CHECK applies to new writes only**;
- a legacy value reads back as `legacy_freeform`, with the original retained;
- 🔴 **`why` renders `legacy_freeform` as the token, NEVER the original text** —
  otherwise the vocabulary closes the write path and leaves the read path, which
  is the one the disclosure actually travels on.

## 11.3 The invariant matrix, expanded

| inv | statement | v3 change |
|---|---|---|
| **INV-1** | after redaction no carrier named in §2/§2d holds the content | **widened** — the enumeration's 64 carriers, not a hand-list |
| **INV-2** | a mutant is planted in **every column that duplicates a `json` field**, enumerated from the DDL at run time | 🔴 **was `object` only.** Three columns: `subject`, `relation`, `object` |
| **INV-3** | the record and its redaction state commit in one transaction | unchanged; **extended to import** (§4g) |
| **INV-6** | no **free-form** reason reaches a prompt, recall, export or MCP | 🔴 **amended** — it prohibited reasons from export outright, which D2 overrode. **Vocabulary reasons travel; free text never does**, and after 11.2 there is no free text to travel |
| **INV-7** | no `content_digest` over redacted content survives | **conditional on D3** — §10's item 2 shows a rebuild re-embeds the tombstone. True of the original either way |
| 🔴 **INV-8** *(new)* | `""` is **REJECTED** by the tombstone CHECK | the positive control for F3. `TEXT NOT NULL` permits `""`; this is the check that actually forbids it, and it must be seen to fail before the CHECK exists |
| 🔴 **INV-9** *(new)* | no read-compute-publish path republishes content across a redaction | F2. `compile_wiki` carries the `v_begin` check; every other such path is listed in §4e or recorded there as exempt **with its reason** |
| 🔴 **INV-10** *(new)* | an imported redaction notice never presents as locally witnessed | F5. The journal distinguishes *was told* from *did* |
| 🔴 **INV-11** *(new)* | an ordinary write to a field holding the marker is **refused** | F3. Without it the tombstone is advisory and `remember()` walks it back |
| 🔴 **INV-12** *(new, v3.1)* | `embedded_text`'s field set is a SUBSET of `content_digest`'s — the semantic rebuild's exemption from §4e's class holds only while it is | derived by mutation over every string field of `Edge`; asserted TODAY against the shipped code in `tests/test_0041_evidence.py`, ahead of redaction |

## 11.4 Amendments to existing contracts — named, not implied

**This spec changes contracts other specs own. Each is listed so the owning spec
is swept rather than discovering it later.**

| contract | amendment |
|---|---|
| **journal** (0029) | a new `redacted` event kind; a new `episode_event` table; imported events carry source metadata and destination-local `seq`/`txn` |
| **doctor / integrity** (0029) | 🔴 **the `refs` check must EXEMPT a standing redaction notice.** Today it flags any journaled `edge_id` with no row; a notice imported before its record is exactly that, by design. **Exempt the `redacted` kind in `pending` state and NOTHING else** — the check's value is that an orphan is normally a real defect, and widening it further would spend that |
| **reader** (0030) | `edge_state_at()` gains a **`REDACTED`** state. 🔴 **Today a plain sentinel classifies as `MALFORMED`** — a redacted read must not report as damage |
| **compiler** (0012) | publication is conditional on the store version the inputs were read at (§4e) |
| **export/import** (0006/portability) | 🔴 **`export` carries NO events at all today — verified, and this is larger than a format change.** The record kinds are `edge` and `episode`; anything else raises *"unknown record kind"*. So D2's travelling redaction event **has no existing carrier**, and §8's survival claim depends on building one. §4g is the acceptance contract for a transport that does not yet exist |
| **write path** | writes to a marker-holding field are refused (INV-11); redaction calls `_bump` (§4e) |
| **`why`** (CLI) | renders vocabulary reasons and `legacy_freeform` tokens only |

## 11.5 What a caller is guaranteed after a successful redaction

1. the named content is **absent from every carrier named in the receipt**;
2. the fact that a record existed and was redacted **survives in the live
   store**, and travels on export as a notice (D2);
3. **derived records that may still carry the content are NAMED in the receipt**
   (F6) — they are *not* redacted, and the caller can redact them;
4. **receipt-table completeness is reported, not assumed** (F4): if a digest
   domain could not be recomputed, `receipts_complete=False` says so.

> **Points 3 and 4 are limits stated as guarantees, and that is deliberate.** A
> caller can act on a named limit. The failure this spec keeps circling — the
> false negative on `original_relation`, the `TEXT NOT NULL` claim, the flat
> *"no row is deleted"* — is never that something was incomplete. **It is that
> the prose claimed more than what was done**, and a reader has no way to see
> the gap from inside the document.
