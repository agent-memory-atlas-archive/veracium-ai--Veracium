# Feature spec: the subject's right of reply — the record stands, and the reply travels with it

Spec-Status: draft
Spec-Requires: 0045, 0041[0047/0041-replies], 0008[0047/0008-request-registry]

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.2 2026-09-20 from `0047-subject-reply-CANDIDATE.md` (sha16 e8daf82c70cb4031); v1.3 2026-10-10 from `0047-subject-reply-CANDIDATE.md` (sha16 c5f61f2972e97a58); v1.7 2026-10-11 from `0047-subject-reply-CANDIDATE.md` (sha16 c2651accfcc5dc39); v1.8 2026-10-12 from `0047-subject-reply-CANDIDATE.md` (sha16 39286844f0a82358) |
| **Version** | **v1.8 — 2026-10-12, round-3 fold (re-issued the same day: §4c's `attested` × challenged cell is NOT ASSERTABLE, the owner's ruling on 0045 R2-01, option 3, after ATTEST-3's holdout result; §3's bullet, §4c's rationale, §5's regime rows and §9 follow); **re-issued again: NOT ASSERTABLE means WITHHELD** for every value, so §4d's assertion surfaces withhold a challenged fact and the unit lives where the record is inspected; INV-R3, R6 and R20 restated; §8's claim follows (dev's model II run found §4c and §4d disagreeing): round 2 returned v1.7 for amendment (R2-02..R2-06 bind this spec, with the 0008 and 0041 amendments).** **R2-02:** an imported act's own key is an internal `#act:` key outside the caller grammar (§2, §4f). **R2-03:** the restore rule reads POSITION (`pos = (origin_store, act_seq)`, the 0008 amendment §6f), never `confirmed_at`, and refuses an order it cannot establish; INV-R23 (§4b, §4f). **R2-04:** exact replay by `act_uid` and projection is a no-op checked before the held-target refusal, and a changed row refuses the file (§4f). **R2-05:** `replies.request_digest` and the registry's digest are treated at redaction (the 0041 amendment v1.3, the 0008 amendment §6g). **R2-06:** an ordinary reply onto a target redacted under a notice that does not cover `replies.text` is refused (§4f). The verdict's bounded corrections: **#2** reinforcement writes a new edge id at the pin, so acts stay on the prior's identity (§4e); **#3** the `unknown` cell states its NEW restriction (§4c); **#5** the reply request's canonical identity is closed, INV-R24 (§4b). *#1, the carrier inventory's ASOF wording, is in dev's generated disposition text, not in this document.* §9 is the round-3 brief. Prior: **v1.7 — 2026-10-11: an imported act's file id is evidence in `recorded_correlation_id`** (the 0008 amendment v1.1's additive construction, dev's as schema owner); INV-R20, R21 and R22 cite their model invariants (G13, G10, G14), and §6's claim list gains G13 and G14. Prior, same day: **v1.6 — four of the 0044 round-2 verdict's classes, found in this spec before its seal and folded.** **(1) The shared id space is CONSTRUCTED** by a new 0008 amendment, `0047/0008-request-registry` (in `Spec-Requires:`). v1.5's INV-R15 promised one id space with `confirm()`, but the product's replay lookup reads only `confirmations`, so a reply's id was invisible to `confirm()` (R2-04's class). **(2) Historical recall renders the CURRENT acts**, never “written at or before T”: T is valid time and `written_at` is commit time (R2-01's class; INV-R20). **(3) An act's `origin` is stored** and never upgraded, and only `local` and `restored` confirmations count toward `g(e)`. v1.5's “testimony (`origin = imported`)” had no column (R2-05's class; INV-R21). **(4) User erasure removes replies** with their registry rows (R2-07's class; INV-R22). Exporting confirmations reverses 0008 §6d's “excluded”, which v1.5 did without an amendment; the 0008 amendment now says so (R2-06's class). Prior, same day: **v1.5 — INV-R6's mutant cites model G4** (dev's carrier read, T1: §6 claimed G4 as this spec's and no row cited it; the model now runs R6's mutant, the open count derived from the budget-selected challenges, and G4 kills it). Prior, same day: **v1.4 — round 1 returned (R1-03, R1-05..R1-08, R1-10 owned here); the reviewer's answers to R1 and R2 adopted; aligned to 0045 v1.5.** Base: the tree's adopted copy at `cfb4151` (v1.3); the Author and Number cells are dev's and are carried verbatim. 🔴 **v1.3's §0 (the 0041 amendment) is now its OWN document**, `0047/0041-replies`, bound by this spec's `Spec-Requires:` line (R1-10; the owner's “Bind by content”); it answers R1-07 through 0041's existing attested-carriage path. 🔴 **The reply kind `disputed` is renamed `challenge`** (R2, the reviewer's preference) and a structured **`resolve`** kind is added (R1-06): context text never clears a challenge, and v1.3's “a `context` reply saying the dispute no longer stands” recovery is WITHDRAWN — the reviewer showed it could not work. 🔴 **§4c's grid reads 0045 v1.5's four values** (`attested` · `confirmed` · `not_attested` · `unknown`), and is stated as an ADDITIONAL restriction only (R1-05). **§4d is the rendering construction R1-05 asked for:** a deterministic mandatory unit, withholding on overflow, wiki exclusion with atomic eviction and an in-flight fence, historical semantics at T. **§4e–§4f are R1-03's and R1-08's matrices.** **One narrowing, stated:** v1.3 rendered `context` and `withdrawn-consent` replies beside the edge in recall; v1.4 confines them to `why` and the structured returns, so the recall unit has ONE deterministic shape (R1-05) — §9 names it as least sure. **§0a is decided** (the reviewer agreed with refusing a new content reply to a redacted edge; restoring an already-redacted reply is the amendment's notice path). The rules are a separate artifact executed by dev's reference model (§6). Prior: v1.3 · v1.2 · v1.1 (the joint candidate's Part B). |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — it adds a CONTENT-CARRYING table and a gate on what the agent may assert. Round 2. |
| **Decision + date** | **The reply is wanted, and amending 0041 is accepted if required: the owner, 2026-10-10.** Acceptance: pending the external round. |
| **Path** | **full** |
| **Number** | 0047 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | the joint candidate's v1.1 Part B — that half is now the declarative grounding axis, adopted as **0045**. **Travels with** 0045, the 0019 amendment `0045/0019-nonuser-refusal` and the 0041 amendment `0047/0041-replies` in one package. |

---

## 0. The 0041 amendment, and the post-redaction reply — DECIDED

**The amendment is its own document** (`0047/0041-replies`): `replies.text` joins 0041's side-table treatments of an
edge as REPLACE, so a redaction treats every reply's text in its transaction, keeps the rows, and attests the field;
a redacted reply round-trips only through 0041's notice path. *Why the reply needs it at all — no carrier avoids it —
is §1c.*

**The post-redaction reply (v1.3's §0a, the round's question) — DECIDED: REFUSE a new reply to a redacted edge.** The
reviewer agreed (*“refusing a new content reply to an attested-redacted edge in this feature”*), and named the
alternative — operator-only replies to tombstone existence — as needing its own content lifetime and redaction
target, *“not a small exception”*. **Distinct from that, and admitted:** restoring an EXISTING reply that was redacted
with its edge (the amendment's import rows; R1-07).

---

## 1. Problem and motivation

### 1a. What it answers

LINDDUN lists *“let me be able to deny I said that”* as a first-class requirement. **Veracium is built to defeat that
sentence** — durable attribution is the product, and an enterprise buyer is paying for exactly what a data subject may
not want. The owner's ruling (`A8`) names the tension publicly **and** builds the counterweight.

> 🔴 **THE SHAPE OF THE COUNTERWEIGHT: the record stands, and the reply travels with it.** *We do not resolve the
> tension by weakening attribution. We make the subject's answer as durable as the claim, and refuse to let the claim
> be rendered without it.*

### 1b. What it deliberately does NOT give

- **not deletion** — 0041's targeted redaction, a different right
- **not supersession** — a challenge is not a correction; *“that's wrong” and the record being wrong are different
  facts*
- **not removal from an audit trail**

### 1c. Why a table, and why the 0041 amendment is intrinsic (the owner's “better way” question)

A reply holds the subject's own words about a fact, and those words routinely RESTATE it — *“I never took
sertraline.”* Redact the edge, and a surviving reply re-publishes what was redacted. **So whatever carries the reply
must be treated in the redaction's transaction — 0041's job.** The reviewer confirmed: *“The 0041 amendment is
intrinsic to storing free-text replies about a target, regardless of whether that text lives in a table, an edge or
an episode. Rejecting a reply-as-edge shortcut is justified.”*

| carrier | avoids amending 0041? | what else it costs |
|---|---|---|
| **a table + one treatment row** *(chosen)* | no — one REPLACE row | the first free-text side column |
| a reply as an EDGE | no — worse: no edge→edge cascade exists | a reply becomes a FACT: recalled, superseded, decayed, consolidated |
| text inside the edge | — | edits the record: breaks append-only |
| host-side replies, a digest in the store | yes | the store cannot render the reply beside the claim; export loses it |
| a reply as an EPISODE | no | episodes feed ingest: the reply would be extracted into facts |

### 1d. 🔴 Two names this spec must not be confused with

- **`Memory.dispute()`** (shipped) **RETIRES** an edge (reason `disputed`, §2c-ii row 1). **A `challenge` reply
  retires nothing** (INV-R1). *v1.3 used `disputed` for the reply kind; the reviewer preferred `challenge`, keeping
  `dispute()` and its retirement reason unchanged.*
- **0003's “contested” facts** are functional facts with refused challengers. A challenged fact is not contested in
  that sense.

---

## 2. Field contracts touched

| field / site | read / written | its documented contract | preserved? |
|---|---|---|---|
| `replies` *(new table)*: `id`, `user_id`, `edge_id`, `kind` ∈ {`challenge`, `context`, `withdrawn-consent`, `resolve`}, `target` (a `resolve`'s challenge id, else NULL), `text` (NULL for `resolve`), `actor`, `correlation_id`, `request_digest`, `origin` ∈ {`local`, `imported`, `restored`}, `recorded_correlation_id` (NULL for `local`; else the ORIGINAL request's id), `written_at`, and (v1.8) **`act_uid`** and **`pos = (origin_store, act_seq)`** with `origin_user` as provenance (the 0008 amendment §6e–§6f) | written by the reply verb (`origin = local`, with a request-registry row in the same transaction) and by import (§4f); read by the gate, render, `why`, `doctor`, export; **erased with the user** (`_ERASE_TABLES`, INV-R22) | — | new; append-only (INV-R2) |
| the request registry (the 0008 amendment `0047/0008-request-registry`) | written by `add_reply` and `confirm`, each in its own transaction; read FIRST by both | 0008 §6c: one user-scoped id space | **constructed**: one `UNIQUE(user_id, correlation_id)` across every verb (`confirm`, `reply`, 0044's `undo`; INV-R15); an imported act's own key is an internal `#act:` key outside the caller grammar (the 0008 amendment §6e, R2-02) |
| 0041's treatment map and enumeration | — | — | **amended by `0047/0041-replies`** |
| the render of an edge, on every surface §4d lists | reads | an edge renders in its partition | **Qualified (§4c–§4d)** |
| 0045's grounding `g(e)` | read | `attested` · `confirmed` · `not_attested` · `unknown` | read only |
| `store.confirm_edge` (0008) | refuses | refuses an unknown or non-assertable edge | **gains one refusal: an edge with an active challenge** (`store.confirm.active-challenge`, INV-R13). *0008 lists no closed set of refusals (dev's check); this restricts only.* **Its replay lookup moves to the request registry** (the 0008 amendment), so a reply's id conflicts on `confirm` |
| `doctor`'s `refs` check | reads | dangling references are reported | **gains** the orphan-reply row (INV-R5) |
| portability | writes / reads | record lines and stamps | **gains** `reply` and `confirmation` lines under a conditional stamp (§4f) |
| absorption (`graph.py`) and the store's absorption verifier | — | 0019/0014's OR rule for the flag | **gains a refusal: a contributor carrying a confirmation or reply is NOT absorbed** (§4e, R1-03); the verifier amended in the same change |

---

## 2c. Untrusted inputs — REQUIRED, blocking

| uncontrolled input | empty | malformed | unrecognised | adversarial | **invariant that pins it** |
|---|---|---|---|---|---|
| **the reply text** | refused (except `resolve`, which carries none) | n/a | n/a | **marker-carrying** → refused (the amendment's INV-RR1); **unbounded** → clamped in the unit (§4d) | **INV-R7**, **INV-R6** |
| **the reply `kind`** | refused | refused | **outside the closed set → refused at the write path** | — | **INV-R8** |
| **a `resolve`'s `target`** | refused | refused | not a `challenge` of the SAME edge → refused | a second `resolve` of the same challenge → refused | **INV-R14** |
| **the target `edge_id`** | refused | refused | absent for that user → refused | **a redacted edge** → refused (§0); **a PROCEDURAL edge** → refused (§4d's ruling) | **INV-R9**, **INV-R19** |
| 🔴 **who wrote it** — the `actor` | refused | refused | outside the closed set → refused | **an assistant-authored reply LABELLED as the subject's is NOT detected**: the store enforces the label until authenticated principals exist (0050). *Enforced today: a reply labelled assistant or extractor is refused, and the verb is not reachable by the model (§3b)* | **INV-R2**, **INV-R10** |
| **`correlation_id`** | generated; no retry protection | — | — | same id + a different request OR a different verb → refused, in both orders (the request registry, the 0008 amendment) | **INV-R15** |
| **an import file's replies and confirmations** | — | the existing import refusals | — | **a reply or confirmation aimed at a PRE-EXISTING local edge under default import → refused** (R1-08's reply-only attack); **v1.8:** a default file claiming THIS store's origin → refused, so its positions cannot order an act before a local challenge; a position the restore rule cannot order → refused; an act under a held `act_uid` is an exact replay (no-op) or a conflict (the whole file refused); an ordinary reply onto a target redacted under a notice that does not cover `replies.text` → refused | **INV-R11**, **INV-R16**, **INV-R23**, the 0008 amendment's **INV-Q9** and **INV-I1..I3**, the 0041 amendment's notice-coverage invariant |

### 2c-ii. Assertions about reach — REQUIRED

Commands run from the repository root at `cfb4151` (research, 2026-10-11).

| # | assertion | command | result |
|---|---|---|---|
| 1 | `dispute()` retires, and is not an MCP tool | `grep -n '"disputed": "drop"' src/veracium/schema.py; grep -n "Not exposed over MCP (an agent-callable suppress verb" src/veracium/__init__.py` | READ: L578 · L1843 |
| 2 | `confirm()` checks only the edge's own `assertable`, which reads no reply | `grep -n "if not edge.assertable:" src/veracium/store/sqlite.py; grep -n "def assertable(self) -> bool:" src/veracium/schema.py` | READ: L684 · L828 (`Edge`; L927 is `Episode`'s) |
| 3 | the wiki compiler's in-flight return fence checks REDACTION only | `grep -n "drew_edges = {e.id for e in edges} & store.redacted_targets(user_id, \"edge\")" src/veracium/compile.py` | READ: L284 — the fence §4d extends to replies |
| 4 | the historical renderer is separate from `graph.render_edges` | `grep -n "def render_line" src/veracium/asof/resolve.py; grep -n "def render_edges" src/veracium/graph.py` | READ: L408 · L1299 |
| 5 | no reply table exists today | `grep -rn --include="*.py" -e "CREATE TABLE replies" src/; echo "exit $?"` | EXECUTED: `exit 1` (no match) |

*Lexical reach only. The renderer census R1-05 asks for is built FROM THE CODE BY COMPLEMENT (§4d), not by grep for
readers — a grep finds readers, never a renderer that forgot the field.*

---

## 3. Trust-class matrix — REQUIRED, blocking

Classes from the enums at `cfb4151`: `EvidenceAuthor` = user, third_party, system, assistant; `Disclosure` =
mentionable, use_only, quarantined.

**The reply's AUTHOR:** the subject (or the user acting on their behalf) only. A reply labelled **assistant**,
**system** or **third_party** is refused (INV-R2) — enforced on the label until 0050.

**The EDGE replied to, by its author and disclosure — what the reply changes:**

| edge's author | mentionable | use_only | quarantined |
|---|---|---|---|
| user · third_party · system · assistant | the edge is unchanged (INV-R1); an active challenge restricts its render per §4c | same | not assertable today; the reply is stored and shown in `why`; nothing becomes assertable |

- Can it make a **user-asserted fact non-assertable**? **Yes:** a `confirmed`, `not_attested` or `unknown` fact with
  an active challenge (§4c). **Since v1.8 this includes an `attested` fact** (the owner, 2026-10-12): the record
  stands and the reply travels with it in `why`, but no grounding value keeps a fact assertable over the subject's
  open challenge.
- Can **non-user content gain user-grade authority**? **No.** A reply is not evidence for the fact.
- Can it **clear `needs_confirmation`**, or **merge, drop or overwrite provenance**? No (INV-R1). It REFUSES one
  absorption that would move a person's act (§4e).

**Write-time or maintain-time?** A write — of the reply, never of the edge.

## 3b. Authorization and scope — *full specs only*

- **The reply verb is HOST API ONLY**, not an MCP tool (INV-R10): never the extractor, never the assistant.
- **Scope:** per user; a reply attaches to an edge of the same `user_id`.
- **Who sees it:** every surface that renders its edge, under the edge's own disclosure. **Nothing becomes visible to
  a principal who could not see it before.**
- **Redaction:** the reply's text is treated with its edge's (the amendment).

---

## 4. Behaviour

### 4a. The carrier

| | |
|---|---|
| **what** | a reply record bound to an edge, with a closed `kind`: **`challenge`** · **`context`** · **`withdrawn-consent`** · **`resolve`** |
| **who** | the SUBJECT of the edge, or the user acting on their behalf — never the extractor, never the assistant |
| **effect on the edge** | 🔴 **NONE.** It does not retire, supersede, edit or delete |
| **shape** | **append-only.** Nothing is edited; a `resolve` is a new row that NAMES the challenge it withdraws |
| **effect on the agent** | §4c–§4d |

### 4b. The active-challenge predicate — R1-06

    active_challenges(e) = { c ∈ R(e) : c.kind = challenge ∧ ∄ r ∈ R(e) : r.kind = resolve ∧ r.target = c.id }

- **`context` text NEVER clears a challenge**, whatever it says (the reviewer's mutant: “any context reply clears all
  challenges” must fail).
- A `resolve` names ONE `challenge` row of the SAME edge, written by the same subject label; else refused. A challenge
  is resolved at most once; a second `resolve` is refused.
- **Retry: the request registry** (the 0008 amendment `0047/0008-request-registry`). `add_reply` writes a registry
  row in its own transaction under the one `UNIQUE(user_id, correlation_id)` that `confirm` also writes under. Same
  id + same verb + same request → the first result; the id under a different verb or request → refused, in both
  orders. The registry is read BEFORE any live edge state.
- **The reply request's canonical identity is closed (correction #5):** `(verb = reply, user_id, edge_id, kind,
  target, text)`, with `kind` in its closed set, `target` present iff `kind = resolve`, and `text` NULL iff `kind =
  resolve`. A retry under the same id after the edge changed, was invalidated or was redacted returns this verb's
  own recorded result, or the terminal `request_redacted` after a redaction (the 0008 amendment §6g), never another
  verb's result (INV-R24). Its portable comparison projection is the 0008 amendment's (§6e).
- **Ordering:** each reply write and each confirmation runs in `BEGIN IMMEDIATE` and re-reads `active_challenges`
  inside the transaction; the serial order of commits IS the local order, and each act records it as its POSITION,
  `pos = (origin_store, act_seq)` (the 0008 amendment §6f, R2-03). **No order is ever read from a caller's date**:
  `confirmed_at` is the caller's admitted `date=` (a valid 2025 date can be given in 2026), and `written_at` is a
  local clock that does not travel as an order.

### 4c. 🔴 THE GATE — with 0045 v1.5's four values

**An ADDITIONAL restriction only:** the grid applies to edges that pass EVERY existing gate — scope, disclosure,
activity, temporal. **A cell saying “assertable” never promotes an otherwise ineligible edge** (R1-05).

| `g(e)` | `active_challenges(e) = ∅` | `active_challenges(e) ≠ ∅` |
|---|---|---|
| **`attested`** | assertable — today's behaviour | 🔴 **NOT ASSERTABLE** (v1.8, the owner's ruling on 0045 R2-01) |
| **`confirmed`** | assertable — today's line | 🔴 **NOT ASSERTABLE** |
| **`not_attested`** | assertable — today's line | 🔴 **NOT ASSERTABLE** |
| **`unknown`** | assertable — today's behaviour | 🔴 **NOT ASSERTABLE** — *a NEW restriction, stated (correction #3):* a challenge written after this feature can target an old declarative row, and that row then stops being assertable until the challenge is resolved. A legacy row with no challenge is unchanged |

*Why no value survives a challenge (v1.8).* Round 2's reviewer showed ATTEST-2 attesting six strings that state nothing of the kind, and with `attested` the one value that stayed assertable under a challenge, a false attestation kept a challenged fact asserted. The owner chose a repaired predicate first (ATTEST-3, 0045 v1.8), and it was measured once on a fresh blind holdout: 1 false attestation in 67 negatives (one-sided 95% upper bound ≈ 6.9%), a later-sentence retraction phrased outside its closed list, an open-ended class. **So the label carries no privilege: the owner ruled (2026-10-12) that `attested` gates like every other value.** *This is the verdict's offered route, "narrow the label's meaning and its downstream privilege". It is not the universal veto round 1's reviewer advised against: nothing is deleted or hidden from the record, the subject's answer stays attached, and the subject's own `resolve` restores assertability. What changes is that, while a challenge is open, the store asserts nothing the subject disputes. A8's counterweight still holds: the record stands, the claim is never asserted while the subject disputes it, and wherever the record is inspected the reply is attached (§4d).*

**`confirm()` REFUSES an edge with an active challenge** (`store.confirm.active-challenge`, INV-R13), in every row; no
confirmation can post-date an unresolved challenge. **After a `resolve`, confirmation is admitted again.** The rule
is *“an unresolved challenge blocks confirmation”*, and resolution is the explicit way back.

### 4d. Rendering — the mandatory unit, and every carrier — R1-05

**v1.8: NOT ASSERTABLE means WITHHELD, for every value** (§4c). Under an active challenge a fact reaches NO
assertion surface (recall detail, contested groups, proactive, the wiki, as-of). The report line counts what was
withheld, so the silence is not silent. **Wherever the record is INSPECTED** (`why`, `introspect`, the structured
returns), it carries the mandatory unit. *v1.7 rendered an `attested` fact WITH the unit on assertion surfaces;
that was the privilege the owner removed, and no disputed-rendering outcome replaces it.*

**The mandatory unit** for an edge with an active challenge, wherever the record is inspected:
`fact line + 0019's marker where flagged + "[challenged by the subject: N open; latest: <clamped text>]"`.

| rule | |
|---|---|
| order | challenges by `(written_at, id)`; the LATEST open challenge's text is rendered |
| count | N counts ALL open challenges, computed BEFORE any budget selection — **budget never decides whether a challenge exists** |
| clamp | the challenge text is clamped to its class cap; the marker is never clamped away (0019's rule); marker and challenge clamp together |
| on an assertion surface | the fact is **WITHHELD**, at every budget, and counted in the report line (v1.8); the count of withheld challenged facts is computed before any budget selection |
| `context` / `withdrawn-consent` | rendered in `why` and the structured returns; they do not enter the recall unit |

**The surface list is GENERATED, not written:** dev's carrier inventory (it lands as `specs/evidence/0047/carrier_inventory.py`
with this package) is a census by complement over the AST of `src/`. It covers every function that reads an edge's `.object`, every
whole-model serialisation, and every construction of a FACT-CARRYING RESULT TYPE (derived: a class with a field
annotated `Edge` — today `AsOfFact`, `ContestedGroup`, `Recall`, `SupersessionPlan`). **Every censused function
carries a disposition** (RENDER · CONTESTED · PROACTIVE · WIKI · ASOF · COLLAPSE · RAW · EXPORT · INTERNAL with a
reason · RULING). The script **exits 1 on an UNCLASSIFIED site** (a new render path cannot land undecided) **or a
STALE one**. At 2026-10-11 it lists 65 functions. The dispositions it uses:

| surface | disposition |
|---|---|
| recall detail, contested groups, proactive (where it renders the fact) | **withhold** a challenged fact, counted in the report line (v1.8; v1.7 rendered an `attested` one with the unit) |
| **compiled wiki** | **EXCLUDE challenged facts from compiler input** (a free-text compiler cannot be made to carry the unit — 0019's own reason for flagged facts); **a reply write atomically evicts the user's wiki and bumps its version**; the in-flight return fence (§2c-ii row 3, today redaction-only) **also withholds a body compiled before a reply to a fact it drew on** |
| **as-of / historical recall** (`render_line`, `facts_valid_at`) | **withhold** a fact that is challenged NOW, whatever T: the challenge state is read from the **CURRENT** replies and confirmations (the query snapshot's), **never filtered by T**: T is valid time (`facts_valid_at` selects `valid_from ≤ T < invalidated_at`) and an act's `written_at` is commit time. v1.5's “written at or before T” mixed the two, and hid a challenge raised after T from a query about a time before it (INV-R20). With 0019's marker (landed, `84b50c2`) |
| **raw structured returns** (`Recall.edges`, `AsOfFact`) and inspection (`why`, `introspect`) | carry the mandatory unit, the `active_challenges` count and `g(e)`; the consumer contract says a caller must not assert a challenged fact, and must show the unit wherever it shows the record |

**The census's five RULING sites, decided:**

| site | ruling |
|---|---|
| `procedures.describe_procedures`, `describe_outcome`, `_rel` (MCP-exposed) | 🔴 **a reply cannot attach to a PROCEDURAL edge** — the reply verb REFUSES it (`store.reply.procedural-edge`, INV-R19). 0037 governs procedural records, they carry no grounding value (0045 §4c), and the gate's grid has no row for them. So these surfaces never meet a challenge and need no unit. *A right of reply for procedures is deferred (§10 R6), not denied* |
| `Memory.dispute()` and `Memory.correct()`, and likewise `record_outcome()` (their episode-summary writes at `__init__.py` L1860, L2129, L1973–L1974 at cfb4151) | **INTERNAL — a WRITE of an act episode, not a render.** Each writes an EPISODE whose summary names the edge's value as the OBJECT of an act (*“disputed the remembered fact '…'”*, *“corrected '…' to '…'”*, *“<outcome>: use of '…'”*). That records an act about the fact and never asserts it. This spec claims EDGES, not episodes (0045 §4b), so such an episode does NOT carry the challenge unit, and §8 says so. The challenge rows stay on the retired or superseded edge (§4e: acts stay where they were made) |

### 4e. Identity transitions — R1-03

| operation | prior carries a confirmation or reply? | rule |
|---|---|---|
| reinforcement (same value) | either | allowed. *At the pin `graph.apply_supersession` writes an incoming reinforcement as a NEW edge id under 0012 (correction #2):* the incoming edge carries its OWN grounding and source values, and the prior keeps its acts on its own identity. No act moves |
| absorption (new survivor id) | **no** | allowed; the survivor's `att`/`src` are the incoming's (0045 §4e) |
| absorption | **yes** | 🔴 **NOT absorbed**: the incoming edge is written as its own record; the prior keeps its acts. The store's absorption verifier is amended in the same change (the reviewer: “changing the planner alone will be refused by the store”) |
| supersession (functional, new value) | either | allowed; the prior's acts STAY on the prior — a confirmation of the old value is not one of the new |
| render-time duplicate collapse | members differ in confirmations or replies | **not collapsed**: each renders with its own unit |

**Never copy a confirmation or reply to a more specific proposition** (the reviewer's named mutant).

### 4f. Import and restore of a person's acts — R1-07, R1-08

**Export** carries full `confirmations` rows (all 0008 columns, `origin` included) and full `replies` rows (`origin`
included); never the derived `g(e)`, and never the request registry. *Exporting confirmations reverses 0008 §6d's
“excluded” (and C11's export test); the 0008 amendment `0047/0008-request-registry` makes that change.*
**The whole file is preflighted** against destination ∪ incoming, after user/id remapping, **then one transaction**.

| | default import | trusted restore (0005's explicit trust) |
|---|---|---|
| a confirmation or reply for an edge in the SAME file | imported as **testimony**: stored `origin = imported` whatever the file says; shown in `why`; **not counted in `g(e)`** | imported with its recorded origin mapped **`local → restored`**, `restored` and `imported` kept, **never upgraded** (INV-R21); shape and chronology validated |
| an act's `correlation_id` | the ORIGINAL request's id is kept as evidence in `recorded_correlation_id`; the act's own key is an internal `#act:` key outside the caller grammar and **writes no registry row**, so a file cannot consume or collide with this store's ids (R2-02; the 0008 amendment §6e) | same |
| an act claiming THIS store's origin | **refused** (the 0008 amendment §6e rule 0): only a trusted restore of own history may carry it | admitted under the matrix |
| a confirmation or reply aimed at a **PRE-EXISTING local edge**, and NEW here (its `act_uid` not held) | 🔴 **REFUSED** — an untrusted file cannot act as the subject over a local fact (R1-08's reply-only attack) | admitted only if consistent with local rows **by POSITION** (R2-03): an incoming confirmation against an OPEN destination challenge is admitted only if its position is ordered before that challenge's (the same `origin_store`); **an order that cannot be established (another origin, or a legacy unknown position) is REFUSED**; a RESOLVED destination challenge needs no order (INV-R23) |
| a redacted reply (`text` = the marker) | admitted only through the amendment's notice path | same |
| an ordinary reply onto a target attested redacted by a notice that does NOT cover `replies.text` | **refused** (R2-06; the 0041 amendment §4): never admitted with content, never by rewriting the foreign notice | same |
| an orphan (no edge in destination ∪ file) | **the whole file refused** | same |
| an act whose `act_uid` is already held | **exact replay** (equal projection, the 0008 amendment §6e) → **no-op**, checked BEFORE the held-target refusal, so an unchanged file imports twice as a no-op; a **changed** row → the whole file refused; an exact replay admits no new act on its target (R2-04; INV-I1..I3) | same |

**Never manufacture a confirmation** from a three-valued summary: an import that carries only `g(e)` creates no
confirmation row (R1-08).

---

## 5. Regime analysis — where does this behave differently?

| regime | behaviour |
|---|---|
| **no replies** | byte-identical to today |
| **`context` / `withdrawn-consent`** | shown in `why` and structured returns; assertability unchanged |
| **an active challenge, on any value** | not assertable; the record and the reply are visible in `why` and the structured returns (v1.8: `attested` included) |
| **challenge then `resolve`** | the challenge is inactive; confirmation admitted again; both rows kept |
| **edge redacted after a reply** | reply texts replaced in the same transaction (the amendment) |
| **reply attempted after redaction** | refused (§0) |
| **absorption over a contributor with acts** | refused; separate records |
| **default import of acts on local facts** | refused |
| **MCP-only deployment** | no reply path (host API only) |

---

## 6. Invariants and executable checks — REQUIRED, blocking

**MODEL checks** run against the transition rules (research's grounding × reply × confirmation transition rules,
draft 3.4, sha16 b697bda6) in dev's executable reference model II **before design acceptance**; its invariants
G2–G5, G10, G11, G12, G13 and G14 are this spec's (counts: the model's run result in the package). **PRODUCT tests** are named here and land at the implementation gate. *v1.3's sentence
conflating them is withdrawn.*

| | invariant | check, and the MUTANT it must fail on |
|---|---|---|
| **INV-R1** | **A reply mutates nothing** | **Mutant: let a reply set `invalidated_at` → FAILS** |
| **INV-R2** | **Append-only, subject-labelled** | **Mutant: allow an edit in place → FAILS** |
| **INV-R3** | 🔴 **An edge with an active challenge reaches NO assertion surface §4d lists, whatever its grounding value; wherever it is inspected, its unit is present** (v1.8) | **Mutants: render a challenged fact on ONE assertion surface (v1.7's `attested` cell included); omit the unit from ONE inspection carrier → each FAILS** (the reviewer's mutant, restated) |
| **INV-R5** | **An orphan reply is reachable and reportable** | **Mutant: silence `doctor`'s row → FAILS** |
| **INV-R6** | **The unit is deterministic, and budget never decides a challenge exists**: the open count in the unit, and the report line's count of withheld challenged facts, are computed before any budget selection | **Mutant: derive challenge state from budget-selected replies → FAILS** (model G4); large reply sets; both truncation orders |
| **INV-R7** | **A marker-carrying ordinary reply is refused** (with the amendment's INV-RR1) | **Mutant: accept it → FAILS** |
| **INV-R8** | **`kind` is closed at the write path** | **Mutant: accept an out-of-set kind → FAILS** |
| **INV-R9** | **A reply to a redacted or absent edge is refused** | **Mutant: accept it → FAILS** |
| **INV-R10** | **The reply verb is not reachable over MCP** | **Mutant: register it → FAILS** |
| **INV-R11** | **An import with an orphan is refused whole, before any write** | **Mutant: import the rest → FAILS** |
| **INV-R12** | **§4c's grid, all eight cells, restriction-only; under an active challenge NO value is assertable** (v1.8) | **Mutants: let an “assertable” cell promote an ineligible edge; keep `attested` assertable under a challenge (v1.7's cell) → each FAILS** (model G3) |
| **INV-R13** | **`confirm()` is refused under an active challenge and admitted after `resolve`** | **Mutant: drop the refusal → FAILS**; control: resolve → reconfirm succeeds (model G2) |
| **INV-R14** | **Only a `resolve` clears a challenge, and only the one it names** | **Mutant: any `context` reply clears all challenges → FAILS**; multiple challenges with one resolved (model G2) |
| **INV-R15** | **Replies, `confirm()` and 0044's `undo` share ONE request registry** (the 0008 amendment): an id held by any verb is refused to the others, in both orders (model G11) | **Mutants: same id + different request returns the first result; each verb checks only its own table → FAIL** |
| **INV-R16** | **Default import cannot act as the subject over a local edge** | **Mutant: apply the edge cap while trusting every incoming side-row act → FAILS** (the reviewer's mutant; model G10) |
| **INV-R17** | **Acts stay where they were made** (§4e) | **Mutants: copy every confirmation to a more specific proposition; drop a contributor's reply when selecting its survivor → FAIL** (model G5) |
| **INV-R18** | **The wiki never serves a fact challenged since its compile** | **Mutants: remove the eviction; allow a stale in-flight return → FAIL**; a scripted compiler that drops every reply; warm-cache and two-connection races |
| **INV-R19** | **A reply to a procedural edge is refused**, and writes nothing | **Mutant: accept it → FAILS** (model G12) |
| **INV-R20** | **Historical recall reads the CURRENT acts**, whatever T: a fact challenged now is withheld as of any T (model G13) | **Mutant: filter acts by the valid-time T → FAILS** on a fixture whose challenge is written after T about a fact valid before it (the fact would render as of T) |
| **INV-R21** | **An act's origin never upgrades, and only `local` and `restored` confirmations count toward `g(e)`** (model G10) | **Mutants: count `imported` confirmations; trusted restore writes recorded acts as `local`; default import keeps the file's origin → FAIL**; the chain local → export → default import → export → trusted restore still reads `imported` |
| **INV-R22** | **User erasure removes the user's replies and registry rows** with their confirmations, atomically; a post-erasure retry is not a replay (model G14) | **Mutants: keep replies after `forget_user`; keep registry rows after erasure → FAIL** |
| **INV-R23** | **The restore rule reads POSITION, never `confirmed_at`**: an incoming confirmation is admitted against an OPEN destination challenge only when ordered before it within one origin; an order it cannot establish is refused; a resolved challenge needs none (R2-03) (model G16) | **Mutants: order by `confirmed_at` (the verdict's 2025-dated confirmation sorts before a 2026 challenge); treat an unknown position as earliest → FAIL** |
| **INV-R24** | **A reply retry replays only its own verb's result** after the edge changed, was invalidated or was redacted (then `request_redacted`); the canonical request is closed (correction #5) (model G18) | **Mutants: replay by edge state; return a `confirm` result under a reply id → FAIL** |

*INV-R4 (v1.3: the reply survives redaction as a row) moves to the amendment as INV-RR2.* **Each check is
demonstrated RED against its mutant before acceptance**; the model's run is machine-readable and travels in the
package.

---

## 7. Failure modes and reversibility

- **Silent failure:** a render path that forgets the unit — INV-R3, made checkable by dev's census by complement; a
  reply labelled as the subject's that the subject did not write (undetectable until 0050).
- **Reversible?** A reply is append-only; a challenge is withdrawn by a `resolve`, never by editing. The edge is
  never touched.
- **Partial failure:** every reply write, confirmation and import is one transaction.
- **Attack surface:** a new free-text table, bounded by host-only reachability (INV-R10), the marker mirror (INV-R7),
  the closed kind (INV-R8), the clamp (§4d) and redaction's treatment (the amendment).

---

## 8. Claims and limits

**Claimed:** a subject's answer to a record about them is as durable as the record; while a challenge is open,
the record is withheld from every assertion surface, and wherever the record is inspected it carries the challenge;
only the subject's explicit `resolve` withdraws it.

**NOT claimed:**
- **not deniability** — it lets a person answer, durably, not unsay.
- **not deletion, not supersession, not removal from an audit trail** (§1b).
- **not that the subject wrote it** — the store enforces the LABEL until 0050 (§2c).
- **that an EPISODE naming a challenged value carries the challenge.** `dispute()`, `correct()` and `record_outcome()`
  write act episodes that name the edge's value as the object of the act; this spec claims edges (§4d's rulings).
- **that the surface list is complete beyond what the census keys see** — functions reading `.object`, whole-model
  serialisation, fact-carrying result types (§4d).
- **that the tension is resolved** — it is named and answered.
- **that a restore admits every history it could order with more information** (v1.8): an incoming confirmation whose
  order against an OPEN local challenge cannot be established from positions (another origin, or a legacy unknown
  position) is refused, not guessed (R2-03).

---

## 9. Brief for the external reviewer — ROUND 3

**The question this round asks: do v1.8 and the 0008 and 0041 amendments (v1.2, v1.3) close R2-02 to R2-06, with the
bounded corrections folded?** R2-01 is 0045's; its contract names this spec's §4c, and **§4c's `attested` cell is now NOT ASSERTABLE**:
ATTEST-3 measured 1/67 false attestations on its fresh holdout, and the owner ruled that the label carries no privilege
(the verdict's narrowing route).

| finding | closure |
|---|---|
| R2-02 | an imported act's own key is an internal `#act:` key outside the caller grammar (§2, §4f; the 0008 amendment §6e, INV-Q4′) |
| R2-03 | the restore rule reads POSITION and refuses an order it cannot establish, never `confirmed_at` (§4b, §4f; INV-R23; the 0008 amendment §6f) |
| R2-04 | exact replay by `act_uid` and projection is a no-op, checked before the held-target refusal; a changed row refuses the file (§4f; INV-I1–I3) |
| R2-05 | reply and registry digests REPLACED at redaction; terminal `request_redacted` (the 0041 amendment v1.3; the 0008 amendment §6g) |
| R2-06 | an ordinary reply onto a target redacted under a notice that does not cover `replies.text` refuses the unit (§4f; the 0041 amendment INV-RR6) |
| corrections #2, #3, #5 | §4e (reinforcement writes a new edge id at the pin); §4c (the `unknown` cell's new restriction, stated); §4b (the reply request's closed canonical identity, INV-R24) |
| correction #1 | the carrier inventory's generated disposition text (dev's generator), not this document |
| correction #6 | §6 keeps the MODEL/PRODUCT split; model II v2 names what it does not represent |

- **Least sure of:**
  1. Refusing a restore whose order against an OPEN local challenge cannot be established (§4f, §8), rather than
     admitting it as testimony.
  2. Correction #3's new restriction on legacy rows, which a NEW challenge triggers.
- **What we are NOT asking:** a cross-store merge of positions (refused by design), or a universal subject veto.
- **Reviewer-safe copy:** nothing generalised.

---

## 10. Open questions

| # | question | who decides | by when | class |
|---|---|---|---|---|
| R1 | the post-redaction reply | **RESOLVED**: refuse a new reply; restore an existing one through the notice path (the reviewer, round 1) | — | resolved |
| R2 | rename the kind | **RESOLVED**: `challenge` (the reviewer, round 1) | — | resolved |
| R3 | verified subject authorship | owner + dev | with 0050 | deferred |
| R4 | an MCP-surface reply path | owner + dev | after acceptance | deferred |
| R5 | dev's carrier inventory by complement (§4d) — **BUILT** (65 functions; the 5 RULING sites decided in §4d) | dev | — | resolved |
| R6 | a right of reply for PROCEDURAL records (§4d's ruling refuses it in this feature) | owner + dev | after acceptance | deferred |

---

## Reviewer checklist

- [ ] §3 has no unanswered cells
- [ ] §3's classes were read from the enums, not copied from the template
- [ ] Prohibitions AND the corresponding **permissions** are both tested
- [ ] Every default fails **closed**
- [ ] §2c has a row per uncontrolled input, and **no empty invariant cell**
- [ ] §2c-ii: every claim about what is reachable carries **the command**
- [ ] Every §6 invariant has a check that actually runs, demonstrated RED against its mutant
- [ ] §3b: no principal can see anything they could not see before
- [ ] §10 questions each carry a class
- [ ] §8 states what this does *not* establish
- [ ] I have said where I think the **author's conclusion is wrong**, not only where the text is wrong
- [ ] I re-read the current version before reviewing, and I am quoting the version I approve
