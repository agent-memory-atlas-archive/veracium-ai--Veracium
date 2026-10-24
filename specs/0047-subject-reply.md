# Feature spec: the subject's right of reply — the record stands, and the reply travels with it

Spec-Status: accepted
Spec-Requires: 0045, 0041[0047/0041-replies], 0008[0047/0008-request-registry]

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.2 2026-09-20 from `0047-subject-reply-CANDIDATE.md` (sha16 e8daf82c70cb4031); v1.3 2026-10-10 from `0047-subject-reply-CANDIDATE.md` (sha16 c5f61f2972e97a58); v1.7 2026-10-11 from `0047-subject-reply-CANDIDATE.md` (sha16 c2651accfcc5dc39); v1.8 2026-10-12 from `0047-subject-reply-CANDIDATE.md` (sha16 39286844f0a82358); v1.8.1 2026-10-13 from `0047-subject-reply-CANDIDATE.md` (sha16 467cb43826c37955); v1.13 2026-10-13 from `0047-subject-reply-CANDIDATE.md` (sha16 4e17cbdb5fa5a7ae); v1.14 2026-10-13 from `0047-subject-reply-CANDIDATE.md` (sha16 5aca68720eea131c); v1.16 2026-10-14 from `0047-subject-reply-CANDIDATE.md` (sha16 860989b75d527920), ACCEPTED (design) at round 4 |
| **Version** | **v1.17 (drafted by research 2026-10-23; ADOPTED by dev 2026-10-23 from research eb9cfb05, candidate sha256 fd2edec22a0a8e00…) — §4d's wiki row: an EDGE write moves challenge matching too.** RII-R2-01 (R-II round 2, external, P1), with research's stage-1 read of it (research `bae9faae`). §4d named "a reply write atomically evicts the user's wiki" as INV-R18's construction, and the RII-01 census held the writer set to reply writes and functions already deleting wiki rows. But a challenged record's same-value twins (F7, ruled (a)) are computed from the challenged EDGE's content. A same-ID replacement of that edge therefore changes what an existing reply withholds, and a same-ID replacement of a drawn edge can make it a twin. Neither is a reply write. Edits: §4d (one row), §6 INV-R18 (the mutants), a Review closure section. **No rule changes:** INV-R18's statement already covers both cases, and this version names the construction that makes it hold. It travels with 0004 v3.4, which states the rule (§4c, W10–W13). **v1.16 — THE ACCEPTANCE FOLD, 2026-10-14.** 🏁 **ACCEPTED AT THE DESIGN LEVEL, jointly with 0045, at external round 4, 2026-10-13:** “**Disposition: Accept 0045 and 0047 jointly at design level, with their 0008 and 0041 constructions.** R3-01 and R3-02 are closed. Retain the 0019 amendment's approval and the closure of 0045 R2-01.” For this document: “Design accepted on the current challenge restriction and reply/act rules”. The accepted artifact is the round-4 package, which the reviewer holds: 0045-0047-round4-review-package.tar.gz, sha256 `f16c0487b62db68fc66702841527c92fb9fa957ab915088af45866e0c5e2d1f6` @ pin `af1e564ac12adf620890d83afc255bb5b812e6f9` (tree `3e424b713253bec38bb69df2f46ae7c988897a0f`), carrying 0045 v1.11 and 0047 v1.14 with the shared 0008 amendment v1.9 (sha256 `1c39f735013e1218d9b67fa4ec07bb98cbd9dbc3ab9b188c1f48debefb74912a`), the 0019 amendment v2.2 (sha256 `c4e1443eca0c5a3647d195981faa1ca13156996a6aa0d7de1abdce4dbe9a050b`) and the 0041 amendment v1.13. The verdict is the inbox file with sha256 `12576a39a0c51cb8de24e4681cfca77df6780bd5338fc5da312a471ca88818b3`, banked verbatim in the coordination repository; the reviewer's evidence archive, shared with the companion 0044 verdict, has sha256 `95ac5e8af2ea47179c79698d775d51068ba5d62eba31552eaf768f4b3ade42e4`. This version is v1.15, the consolidation the verdict asked for, plus this cell; v1.15 changed no rule. **No seal follows this fold.** It is design acceptance, not release approval: “This is design approval, not release approval.” 🔴 **THE FROZEN INVARIANT SURFACE, in the reviewer's words:** “Freeze the active invariant rows in **0045 §6** (including new **INV-G13**), **0047 §6** through **INV-R24** (R4 remains moved to the amendment), **0008 INV-Q1–Q10 including Q4′ and INV-I1–I7**, **0041 amendment INV-RR1–RR12 and RR14** (RR13 remains withdrawn), and **0019 INV-N1–N4**. Preserve each row's MODEL/PREDICATE/PRODUCT allocation and the stated limits. This does not certify unimplemented migrations, concurrency, cache fencing or every wire validation path.” 🔴 **THE GOVERNING RULE FORWARD, verbatim:** “These obligations preserve the frozen design. Product findings should be repaired against it rather than restarting debate over label-versus-block, unrestricted query derivation, procedures, authenticated principals, cross-store replay or operational keys.” **THE IMPLEMENTATION OBLIGATIONS, IO-II-1..IO-II-7** — the next implementation review judges “the real implementation against this frozen surface, including the bounded obligations above”: IO-II-1, preserve the specified `existing` behavior for a pending default replay; IO-II-2, make the final folded wording agree with the operative notice table; IO-II-3, bind the notice state machine to durable product state; IO-II-4, bind portable act equality and chronology to the actual schema/wire transaction; IO-II-5, implement the consumer and rendering contracts together; IO-II-6, keep cross-package carrier and registry gates; IO-II-7, correct the hotfix campaign's semantic-failure classification. **Closed at this fold:** IO-II-1 (dev's model fix) and IO-II-7 (dev's campaign classifier), both in the commit that adopts this version; IO-II-2 by the 0041 amendment v1.14 and by the consolidation of this spec's version narrative (v1.15). The other four are open, and the verdict's text holds each one's tests. **On the current product:** the hotfix's default origin check is superseded by the pending-notice rule, but “Do not remove it from the current product before the replacement state machine and its tests land together.” **The limit this acceptance keeps:** “**A resolved challenge with incomparable position may remain admitted under the chosen rule.** This is consistency with the merged resolved state, not proof that the original confirmation followed the resolution. The exact limitation is stated. Keep that distinction in user-facing history and tests; do not claim a total cross-origin audit order.” **CREDITS.** The external reviewer reproduced the package at the pin (all 57 reach rows, reference model II's 21 invariants and 100 owner kills, model I's 30 and 62, the 13 hotfix mutants, and the complete offline suite, 5682 passed and 52 skipped over the same 5734 test identities as the capture), and found two things our green results did not show: a pending notice's reason changing on a default replay, a state transition model II never exercised (IO-II-1), and three campaign kills that were domain refusals rather than assertions (IO-II-7). Dev built reference models I and II, the notice-binding hotfix and its 13-mutant campaign, the round-4 stages and both seals. Research authored 0045, 0047 and the 0008 and 0041 amendments and read each stage. The owner made the rulings in the Decision cell, chose the pending-notice rule, and dispatched every round. **THE ARC, FOUR ROUNDS:** rounds 1 and 2 returned the joint package; round 3 returned it for two bounded import-construction corrections (R3-01, R3-02); round 4 accepts. In the reviewer's words: “The earlier import counterexamples now have explicit rules over the whole staged unit,” and “The new pending-notice construction separates a file's claim from this store's authorization to apply it.” During the round-4 preparation, the 0041 amendment's v1.4 first cited the product's present notice behaviour as precedent; that behaviour was the defect. It was withdrawn at v1.5, and the defect was fixed in the hotfix that the reviewer then replayed. *(The `Spec-Status: draft → accepted` flip, the lineage and the FROZEN-at-round-4 markers are the adoption's declared deltas, on the owner's word; this candidate leaves the line as it stands. This cell cites no evidence-module digest, so adding the markers does not respin it.)* *Annotation (research, 2026-10-24; append-only, no rule changes):* 🏁 **THE IMPLEMENTATION ACCEPTED, jointly with 0045, at external R-II round 4, 2026-10-24:** “**Disposition: accept the bounded R-II implementation at this pin. Close RII-R3-01, the remaining broad closure of RII-R2-01, and nonblocking comment C1. The R-II review hold on the combined programme's T12 completion is lifted.** Preserve the accepted design, R-A closure and the bounded R-I acceptance from round 2. This is implementation review acceptance, not release authorization or a new full review of R-I.” The accepted artifact is the round-4 package, which the reviewer holds: 0045-0047-RII-round4-implementation-review-package.tar.gz, sha256 `9264ec6137ddedba387ce3cd66e5971029f72afdb4cd22ce3c032b35b40b82d7`, with the shared tree 0045-0047-RII-r4-tree.tar.gz, sha256 `ef10d0e86a714d53e566dadae497e3237b9380aaf7d08aeaee603ac3366c06c6`, @ pin `aca9874c9292a6c3c87304c7b759ccf288286496` (tree `c0739fe3281793831c6085c734c76a98c915da94`, 987 files). The verdict is the inbox file with sha256 `d908c24fee5f2eba899ab4b07a9c775622c66ac019ae091be3b7aa1184ecad29`, whose one verdict member (sha256 `1e152865f2b6c2cc9f200def66fcfbc4554c6b99f1349fd7b30439853f774307`) is banked verbatim in the coordination repository; the reviewer's evidence archive has sha256 `609881816b34db8d46b2d03943a8bba753c3c4b32471a8e77893e3dfe76fd4de`. **No seal follows this annotation.** 🔴 **THE FROZEN SURFACE, in the reviewer's words:** “Preserve the accepted frozen surface: active **0045 §6**, including **INV-G13**; **0047 §6 through INV-R24** (R4 remains moved to the amendment); **0008 INV-Q1–Q10, including Q4′, and INV-I1–I7**; **0041 amendment INV-RR1–RR12 and RR14**, with RR13 withdrawn; and **0019 INV-N1–N4**. Preserve each row's MODEL/PREDICATE/PRODUCT allocation and stated limits. This implementation closure additionally judges the submitted **0004 v3.5 W1–W13** construction and its ownership, reservation and redaction obligations.” 🔴 **THE GOVERNING RULE FORWARD, verbatim:** “It does not reopen accepted design choices or extend the supported principal, query, procedure or cross-store replay model.” and “Other release and dependency gates remain in force”. **The limits this acceptance keeps, verbatim:** “The suite and finite mutation campaign support this bounded acceptance; neither is proof of every future composition or input.” “Preserve the distinction between the syntactic writer census and the behavioral obligations it supports.” **The two nonblocking items** (the import owner conflict's generic retry diagnostic; the reviewer's MARKER-kind ownership cases and import preflight-to-commit rollback cases, to join the maintained regression set) are answered by `537dcd8e2b9dd0413d11b3c9f48f26ea214fa8a9`. **CREDITS.** The external reviewer reproduced the round-4 package at the pin (the complete offline suite, 6,891 passed and 56 skipped over the same 6,947 identities as the capture; the mutation campaign, 543 of 543 killed over 118 groups, every control re-run), built a 16-case probe of import rollback with a second writer between plan and commit and six MARKER-kind ownership cases, and across the four R-II rounds found what our green results did not show: a cached wiki read before the challenge snapshot (RII-01) and counted H/Q labels the weak-speaker test omitted (RII-02); a stable wiki row taken as proof of validity across a same-ID edge replacement (RII-R2-01); and an episode whose owner a same-ID write could change (RII-R3-01). Dev built the implementation, each fix, the stages and the seals. Research read the fixes and the stages, drafted 0004 v3.3–v3.5 and ran the second seal leg on each package. The owner ruled that the redaction holds the ID, accepted 0004 v3.4 and v3.5 and 0047 v1.17, and dispatched every round. **THE ARC, FOUR ROUNDS:** round 1 (pin `07df8f8`) returned the package for RII-01 and RII-02; round 2 (`86cb30e`) for RII-R2-01; round 3 (`6cdb9aa`) for RII-R3-01; round 4 (`aca9874`) accepts. It follows the R-A checkpoint over T2–T4 (accepted at its round 2, pin `7168070`) and stands beside the bounded R-I acceptance (0044, its round 2, pin `86cb30e`). In the reviewer's words: “The chosen repair makes the ownership premise true at the durable write.” *(This annotation is the adoption's only delta to this file; it cites no evidence-module digest.)* **Earlier versions:** the Version history at the end of this document, which records superseded rules; none of them is current. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — it adds a CONTENT-CARRYING table and a gate on what the agent may assert. **Round 4: ACCEPTED (design), 2026-10-13**, jointly with 0045; the verdict banked verbatim, sha16 12576a39a0c51cb8. Rounds 1–3 returned. |
| **Decision + date** | **v1.17 ACCEPTED 2026-10-23 on the owner's word** ("I accept  0004 v3.4 and 0047 v1.17"), jointly with 0004 v3.4, after research's read of dev's adoption (5d78a79; research f9523943). R-II round 3 carries v1.17 to the external reviewer. **ACCEPTED — DESIGN, 2026-10-13, at external round 4, jointly with 0045** (“Accept 0045 and 0047 jointly at design level, with their 0008 and 0041 constructions.”; the frozen surface and the rule forward are in the Version cell). **The reply is wanted, and amending 0041 is accepted if required: the owner, 2026-10-10.** |
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
| **an import file's replies and confirmations** | — | the existing import refusals | — | **a reply or confirmation aimed at a PRE-EXISTING local edge under default import → refused** (R1-08's reply-only attack); **v1.8:** a default file claiming THIS store's origin → refused, so its positions cannot order an act before a local challenge; a position the restore rule cannot order → refused; an act under a held `act_uid` is an exact replay (no-op) or a conflict (the whole file refused); an ordinary reply onto a target redacted under a notice that does not cover `replies.text` → refused; **v1.9:** two differing copies of one `act_uid` in one file → refused; a confirmation made under a challenge unresolved in the merged history → refused; a notice covering only some of a row's content carriers → refused | **INV-R11**, **INV-R16**, **INV-R23**, the 0008 amendment's **INV-Q9** and **INV-I1..I3**, the 0041 amendment's notice-coverage invariant |

### 2c-ii. Assertions about reach — REQUIRED

Commands run from the repository root at `cfb4151` (research, 2026-10-11); re-run at `f98a3a0` (research, 2026-10-13), where row 2 reads L692 and every other row the same lines.

| # | assertion | command | result |
|---|---|---|---|
| 1 | `dispute()` retires, and is not an MCP tool | `grep -n '"disputed": "drop"' src/veracium/schema.py; grep -n "Not exposed over MCP (an agent-callable suppress verb" src/veracium/__init__.py` | READ: L578 · L1843 |
| 2 | `confirm()` checks only the edge's own `assertable`, which reads no reply | `grep -n "if not edge.assertable:" src/veracium/store/sqlite.py; grep -n "def assertable(self) -> bool:" src/veracium/schema.py` | READ: L684 · L828 (`Edge`; L927 is `Episode`'s) · at `f98a3a0`: L692 · L828, L927 |
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

*Why no value survives a challenge (v1.8).* Round 2's reviewer showed ATTEST-2 attesting six strings that state nothing of the kind, and with `attested` the one value that stayed assertable under a challenge, a false attestation kept a challenged fact asserted. The owner chose a repaired predicate first (ATTEST-3, 0045 v1.8), and it was measured once on a fresh blind holdout: 1 false attestation in 67 negatives (one-sided 95% upper bound ≈ 6.9%), a later-sentence retraction phrased outside its closed list, an open-ended class. **So the label carries no challenge-gate privilege: the owner ruled (2026-10-12) that `attested` gates like every other value.** *This is the verdict's offered route, "narrow the label's meaning and its downstream privilege". It is not the universal veto round 1's reviewer advised against: nothing is deleted or hidden from the record, the subject's answer stays attached, and the subject's own `resolve` restores assertability. What changes is that, while a challenge is open, the store asserts nothing the subject disputes. A8's counterweight still holds: the record stands, the claim is never asserted while the subject disputes it, and wherever the record is inspected the reply is attached (§4d).*

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
| order | challenges by `(written_at, id)`; the LATEST open challenge's text is rendered. **A PRODUCT display contract** (v1.9): reference model II carries no reply `written_at`, so this row is checked at implementation, not by the model. A sort by position across origins is a display convention only, and never an operation order (§4f reads order from positions within ONE origin) |
| count | N counts ALL open challenges, computed BEFORE any budget selection — **budget never decides whether a challenge exists** |
| clamp | the challenge text is clamped to its class cap; the marker is never clamped away (0019's rule); marker and challenge clamp together |
| on an assertion surface | the fact is **WITHHELD**, at every budget, and counted in the report line (v1.8); the count of withheld challenged facts is computed before any budget selection |
| `context` / `withdrawn-consent` | rendered in `why` and the structured returns; they do not enter the recall unit |
| **one snapshot** (v1.9) | an assertion surface's withholding, the structured returns' consumer duties and an inspection display read the challenge state from the SAME query snapshot, so a challenge cannot be withheld on one and missing from another within one call |

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
| **compiled wiki** | **EXCLUDE challenged facts from compiler input** (a free-text compiler cannot be made to carry the unit — 0019's own reason for flagged facts); **a reply write atomically evicts the user's wiki and bumps its version**; the in-flight return fence (§2c-ii row 3, today redaction-only) **also withholds a body compiled before a reply to a fact it drew on**. **v1.17: a write that changes a stored edge's assertion view also evicts the wiki, by 0004 v3.4 §4c (W10).** That covers a same-ID replacement of a challenged record, whose twins move with its content, and of a drawn record. The bind compares each drawn record's CURRENT view with the drawn one, after the call's snapshot is read (0004 W12). The census of reply writers stays, but it is not the writer set |
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
**The whole file is preflighted** against the STAGED UNION, destination ∪ incoming, after user/id remapping, **then one
transaction** (v1.9: every rule below that says “held” reads that union, the 0008 amendment §6e, so a unit's rows
meet each other exactly as they meet the destination's).

| | default import | trusted restore (0005's explicit trust) |
|---|---|---|
| a confirmation or reply for an edge in the SAME file | imported as **testimony**: stored `origin = imported` whatever the file says; shown in `why`; **not counted in `g(e)`** | imported with its recorded origin mapped **`local → restored`**, `restored` and `imported` kept, **never upgraded** (INV-R21); shape and chronology validated |
| an act's `correlation_id` | the ORIGINAL request's id is kept as evidence in `recorded_correlation_id`; the act's own key is an internal `#act:` key outside the caller grammar and **writes no registry row**, so a file cannot consume or collide with this store's ids (R2-02; the 0008 amendment §6e) | same |
| an act claiming THIS store's origin | **refused** (the 0008 amendment §6e rule 0): only a trusted restore of own history may carry it | admitted under the matrix |
| a confirmation or reply aimed at a **PRE-EXISTING local edge**, and NEW here (its `act_uid` not held) | 🔴 **REFUSED** — an untrusted file cannot act as the subject over a local fact (R1-08's reply-only attack) | admitted only if consistent with the MERGED history **by POSITION** (R2-03, R3-02; the 0008 amendment §6f): every challenge of the edge in destination ∪ file is either ordered after the confirmation, or resolved before it within one origin; **a challenge still unresolved in that history and ordered before the confirmation, or one whose order cannot be established (another origin, or a legacy unknown position), refuses the unit**; a challenge RESOLVED in that history needs no order when none can be established (INV-R23) |
| a redacted reply (`text` = the marker) | admitted only through the amendment's notice path | same |
| an ordinary reply onto a target attested redacted by a notice that does NOT cover `replies.text` | **refused** (R2-06; the 0041 amendment §4): never admitted with content, never by rewriting the foreign notice | same |
| an orphan (no edge in destination ∪ file) | **the whole file refused** | same |
| an act whose `act_uid` is already held (in the destination, or earlier or later in the same file) | **exact replay** (equal CANONICAL TREATED projection under the staged union's notice coverage, the 0008 amendment §6e, v1.9) → **no-op**, checked BEFORE the held-target refusal, so an unchanged file imports twice as a no-op, and a treated held copy replays an untreated arrival the coverage treats; a held ordinary act receiving its source's redaction (a treated copy with its covering notice) is an exact replay under the coverage: the held act unchanged, the notice recorded PENDING for the user's `confirm_notice` (v1.10; the 0041 amendment v1.5 §4, the 0008 amendment v1.4 INV-I7); a **structural** difference → the whole file refused; two differing copies in one file → the whole file refused; an exact replay admits no new act on its target and exempts no other act from validation (R2-04, R3-01; INV-I1..I6) | same, except that a held ordinary act receiving its source's redaction takes the treatment and nothing else (the authorized transition; restore only, v1.10), when the unit carries the target edge already showing the redaction (v1.11); a unit carrying the edge unredacted refuses the whole file, and with no copy of the edge the notice is pending unless the held edge already shows it (v1.12; the 0041 amendment v1.8) |

**Never manufacture a confirmation** from a three-valued summary: an import that carries only `g(e)` creates no
confirmation row (R1-08).

**Chronology over the merged history (v1.9, R3-02).** The restore rule never reads an intermediate destination.
Every incoming `challenge`, `resolve` and `confirmation` is first placed in the merged history H, with its
references remapped, and only then is any pair of a challenge and a confirmation of one edge judged, whenever at
least one of the two is new in this import (the 0008 amendment §6f's table): an incoming challenge is judged against a
held confirmation as much as an incoming confirmation against a held challenge. So the three round-3
witnesses come out the same in one file or as successive snapshots of the source:
- a challenge and a later same-origin confirmation made while it was unresolved are refused in ONE file, as they are
  across two;
- a history in which the source opened a challenge, resolved it, then confirmed is ADMITTED when the destination
  already holds the challenge and the file brings the resolve and the confirmation.

Ties, a second resolve of one challenge and a resolve ordered before its challenge each refuse the unit.

**The trust label is the destination's (v1.9).** An act's stored `origin` is decided at its first admission (the
matrix above). It is never part of the comparison, and a replay never changes it, so a trusted restore of an act
already held as testimony leaves it testimony (INV-R21).

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
G2–G5, G10–G14, G16 and G18 are this spec's (counts: the model's run result in the package). *v1.9's rules are encoded at
the round-4 adoption: chronology over the merged history (INV-R23) → G16; the staged union and replay → G17; the
canonical treated projection → G19.* **PRODUCT tests** are named here and land at the implementation gate. *v1.3's sentence
conflating them is withdrawn.* **What the model does NOT establish (correction #6):** full wire validation of the
export format, the migrations, SQL-level concurrency, cache fencing and the full carrier census are PRODUCT checks at
implementation. The model represents the rules (the gate, rendering and inspection, the registry, the origin matrix,
positions, notice coverage), not the store's mechanisms.

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
| **INV-R18** | **The wiki never serves a fact challenged since its compile** | **Mutants: remove the eviction; allow a stale in-flight return → FAIL**; a scripted compiler that drops every reply; warm-cache and two-connection races. **v1.17 mutants:** evict on reply writes only (killed by a same-ID replacement that moves a challenged record onto a drawn record's value); the bind compares presence only, not the drawn records' views (killed by a drawn record replaced into a twin); let the rejected compiled body re-enter through the cache on the retry (killed by 0004 W13's cell, with the write eviction disabled). Each must → FAIL |
| **INV-R19** | **A reply to a procedural edge is refused**, and writes nothing | **Mutant: accept it → FAILS** (model G12) |
| **INV-R20** | **Historical recall reads the CURRENT acts**, whatever T: a fact challenged now is withheld as of any T (model G13) | **Mutant: filter acts by the valid-time T → FAILS** on a fixture whose challenge is written after T about a fact valid before it (the fact would render as of T) |
| **INV-R21** | **An act's origin never upgrades, and only `local` and `restored` confirmations count toward `g(e)`** (model G10) | **Mutants: count `imported` confirmations; trusted restore writes recorded acts as `local`; default import keeps the file's origin → FAIL**; the chain local → export → default import → export → trusted restore still reads `imported` |
| **INV-R22** | **User erasure removes the user's replies and registry rows** with their confirmations, atomically; a post-erasure retry is not a replay (model G14) | **Mutants: keep replies after `forget_user`; keep registry rows after erasure → FAIL** |
| **INV-R23** | **The restore rule reads POSITION, never `confirmed_at`, over the MERGED history** (v1.9): an incoming confirmation is refused when a challenge of its edge is unresolved in destination ∪ file and ordered before it, or when an order it needs cannot be established; a challenge resolved in that history needs none; the result does not depend on row order, and is the same in one file or as successive snapshots of the source; an arbitrary split is not equivalent (a file with the challenge and the confirmation but not the resolve between them refuses, the 0008 amendment §6f) (R2-03, R3-02) (model G16) | **Mutants: order by `confirmed_at` (the verdict's 2025-dated confirmation sorts before a 2026 challenge); treat an unknown position as earliest; check confirmations before installing the file's challenges (round 3's one-file witness admits); check held challenges before applying the file's resolves (round 3's valid resolved-history restore refuses) → FAIL**. Controls: confirmation before the challenge; valid resolution before the confirmation; ties; unknown positions; incomparable origins; remapping; input order |
| **INV-R24** | **A reply retry replays only its own verb's result** after the edge changed, was invalidated or was redacted (then `request_redacted`); the canonical request is closed (correction #5) (model G18) | **Mutants: replay by edge state; return a `confirm` result under a reply id → FAIL** |

*INV-R4 (v1.3: the reply survives redaction as a row) moves to the amendment as INV-RR2.* **Each MODEL check is
demonstrated RED against its mutant at the design gate**, and the model's run is machine-readable and travels in the
package. **Each PRODUCT test is demonstrated red at the implementation gate**, which is where it is owed (v1.9: this
sentence follows the MODEL/PRODUCT split above, and does not demand unimplemented product tests at design
acceptance).

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
- **that a restore admits every history it could order with more information** (v1.8, v1.9): an incoming confirmation
  whose order against a challenge that is unresolved in the merged history cannot be established from positions
  (another origin, or a legacy unknown position) is refused, not guessed (R2-03, R3-02).
- **that a trusted restore upgrades an act already held as testimony** (v1.9): the stored label is the destination's
  first judgement, and a replay never changes it.

---

## 9. Brief for the external reviewer — ROUND 4

**Round 4's brief, kept for the record: round 4 reviewed the versions named below and ACCEPTED the design (verdict 2026-10-13); later versions fold its bounded corrections.**

**The question this round asks: do v1.14 and the 0008 and 0041 amendments (v1.9, v1.13) close round 3's R3-01 and
R3-02, with the bounded corrections folded, inside the finite-review boundary you set?**

| round-3 item | closure |
|---|---|
| R3-01: notice treatment × act replay; same-unit UIDs | §4f, the 0008 amendment §6e, the 0041 amendment §4: HELD is the staged union; equality on the canonical treated projection; one authorized transition, content carriers only; coverage all or nothing per row. INV-I4..I6, RR8, RR9 |
| R3-02: chronology reads an intermediate state | §4f, the 0008 amendment §6f: validation over the merged history, references remapped first. INV-R23 restated, INV-Q10 |
| recorded origin | §4f: the trust label is the destination's, never compared, and never changed by a replay (the 0008 amendment §6e) |
| inspection ordering | §4d: display order is a PRODUCT contract; a cross-origin position sort is display only |
| one snapshot | §4d's new row |
| gate wording | §6: MODEL checks red at the design gate, PRODUCT tests at implementation |
| the carrier census's render-or-withhold wording | in dev's census tool (`specs/evidence/0047/carrier_inventory.py`), not this document; §4d's table already reads “withhold” |

- **Least sure of:** a challenge that is resolved in the merged history but cannot be ordered against the
  confirmation is admitted (v1.8's “a resolved challenge needs no order”, now read over the union).

**Round 3's brief, kept for the record.** The question that round asked: do v1.8 and the 0008 and 0041 amendments
(v1.2, v1.3) close R2-02 to R2-06, with the bounded corrections folded? R2-01 is 0045's; its contract names this spec's §4c, and **§4c's `attested` cell is now NOT ASSERTABLE**:
ATTEST-3 measured 1/67 false attestations on its fresh holdout, and the owner ruled that the label carries no challenge-gate privilege
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
| correction #6 | §6 states what the model does NOT establish (wire validation, migrations, SQL concurrency, cache fencing, the full carrier census: PRODUCT checks) beside the MODEL/PRODUCT split. *v1.8 claimed this was done before it was; corrected in v1.8.1* |

- **Least sure of:**
  1. Refusing a restore whose order against an OPEN local challenge cannot be established (§4f, §8), rather than
     admitting it as testimony.
  2. Correction #3's new restriction on legacy rows, which a NEW challenge triggers.
- **What we are NOT asking:** a cross-store merge of positions (refused by design), or a universal subject veto.
- **Reviewer-safe copy:** nothing generalised.

### Review closure — round 1

*Joint review with 0045. One row per finding this spec answers or shares; the round-1 verdict's named owners are given where they are not this spec alone. Each assessment is quoted from the NEXT round's verdict; a part it carried forward is that round's row below.*

| finding | the round-2 verdict's assessment | where this spec answers it |
|---|---|---|
| **R1-03** absorption breaks the three-state derivation and strands edge-bound replies (owners: all three documents) | “**Closed at design level** for absorption and collapse: acts prevent absorption and differing act histories prevent render collapse.” | §4e; 0045 §4e for its state |
| **R1-05** “the reply travels with the claim” has no complete rendering construction (owners: this spec and the marker readers) | “**Closed at design level.** Restriction-only gate, mandatory unit, overflow withholding, wiki exclusion/eviction/fence, and a declared structured-consumer obligation. Product coverage remains owed” | §4c, §4d |
| **R1-06** a later `context` reply cannot restore the state the spec says it restores | “**Closed.** Only a structured resolve targeting one challenge clears it; context does not” | §4b |
| **R1-07** the reply import rules reject the feature's own valid exports (owner: this spec's 0041 amendment) | “**Partial.** Notice-based carriage fixes blanket marker refusal. Repeat identity and older notice coverage remain R2-04 and R2-06” | §0 and the 0041 amendment (`0047/0041-replies`); §4f; round 2's R2-04, R2-06 |
| **R1-08** import has no trust or identity contract for confirmations and replies (owners: the 0019 amendment and this spec) | “**Partial.** Stored origin and non-upgrading restore are clear improvements. Portable history and identity remain R2-02 through R2-04” | §4f; the act's origin by the 0008 amendment (`0047/0008-request-registry`); round 2's R2-02 to R2-04 |
| **R1-10** joint acceptance and the stated pre-acceptance evidence gate are not enforceable as packaged (owners: the package and all three documents) | “**Closed as a governance construction.** Mutual dependencies and amendment fold IDs are checked; model evidence is separated from implementation evidence.” | the `Spec-Requires:` line (0045, and the 0041 and 0008 amendments by id); §6's MODEL and PRODUCT split |

### Review closure — round 2

| finding | the round-3 verdict's assessment | where this spec answers it |
|---|---|---|
| **R2-02** generated import identifiers still occupy the retained uniqueness constraint | “**Closed at design level.** `#act:` keys cannot be supplied through the caller grammar; portable UID serialization is explicit.” | §2, §4f; the 0008 amendment §6e, INV-Q4′ |
| **R2-03** portable confirmation chronology has no carrier for the model's commit clock | “**Carrier defect closed.** Positions are durable, origin-bound and never synthesized for legacy rows. Their merged-history application remains R3-02” | §4b, §4f; INV-R23; the 0008 amendment §6f |
| **R2-04** repeat import conflicts with local target refusal and lacks canonical act equality | “**Core construction improved.** Portable UID, original request provenance and comparison precedence are now specified. Notice composition, same-unit conflicts and the recorded-origin carrier remain R3-01 and the bounded corrections below” | §4f; INV-I1–I3 |
| **R2-05** reply and registry digests are missing from the redaction construction | “**Normative treatment and terminal retry closed.** The arrival model retains a digest, and the cross-package undo model still replays it after redaction; R3-01 and companion 0044 R3-03 cover those evidence gaps” | the 0041 amendment; the 0008 amendment §6g |
| **R2-06** an older notice does not cover an arriving reply's new content carrier | “**Core target-state refusal closed.** The fully composed treatment/equality and partial-coverage construction remains R3-01” | §4f; the 0041 amendment, INV-RR6 |
| the six bounded corrections | “The six round-2 bounded corrections are substantially incorporated” | §4e (reinforcement's own edge id); §4c (the `unknown` cell's restriction); §4b (the reply request's identity, INV-R24); §6 (MODEL versus PRODUCT) |

### Review closure — round 3

| finding | the round-4 verdict's assessment | where this spec answers it |
|---|---|---|
| **R3-01** notice treatment and portable act replay do not compose | “**Closed at design level.** The canonical treated projection covers every non-NULL content carrier, includes held and arriving notice coverage, and preserves structural equality.” | §4f; the 0008 amendment §6e; the 0041 amendment §4; INV-I4..I6, RR8, RR9 |
| **R3-01**, conflicting UIDs inside one unit | “**Closed.** The staged identity map includes incoming rows.” | §4f; the 0008 amendment §6e |
| **R3-02** chronology validation does not read the merged history | “**Closed.** A same-unit unresolved challenge followed by a later confirmation is refused, as it is in successive arrivals.” | §4f; the 0008 amendment §6f; INV-R23, INV-Q10 |
| the recorded-origin carrier | “**Closed by normalization rather than another column.**” | §4f; the 0008 amendment §6e |
| rendering and gate wording | “**Closed.** The current contract withholds every challenged grounding value, uses one query snapshot, and separates display ordering from operation ordering.” | §4d; §6 |

### Review closure — round 4 (v1.16; the verdict ACCEPTED, jointly with 0045, the design of v1.14)

| item | the round-4 verdict | where |
|---|---|---|
| disposition | “**Disposition: Accept 0045 and 0047 jointly at design level, with their 0008 and 0041 constructions.** R3-01 and R3-02 are closed. Retain the 0019 amendment's approval and the closure of 0045 R2-01.” | the Version cell, which quotes the frozen surface and the rule forward |
| the limit this acceptance keeps | “**A resolved challenge with incomparable position may remain admitted under the chosen rule.** This is consistency with the merged resolved state, not proof that the original confirmation followed the resolution.” | INV-R23 (“a challenge resolved in that history needs none”); §9's round-4 “least sure of” |
| IO-II-1, the pending default replay's `existing` reason | “Retain the existing pending row/reason in that branch and add both controls to the model and the eventual store test.” | closed in the commit that adopts this version: model II's `_notice_effect`, its control and its mutant |
| IO-II-2, the folded wording | “consolidate the historical version narrative when folding so withdrawn intermediate rules cannot read as current permissions.” | closed: the 0041 amendment v1.14, and this spec's v1.15 (the Version history) |
| IO-II-7, the campaign's failure classification | “This is a nonblocking evidence-runner correction” | closed in the commit that adopts this version: the campaign classifier, its controls and its tamper cases |
| owed at implementation (the verdict, not reopened) | “These obligations preserve the frozen design.” | IO-II-3, bind the notice state machine to durable product state; IO-II-4, bind portable act equality and chronology to the actual schema/wire transaction; IO-II-5, implement the consumer and rendering contracts together; IO-II-6, keep cross-package carrier and registry gates |

### Review closure — R-II round 2, implementation (v1.17; RII-R2-01)

| item | the round-2 verdict | where |
|---|---|---|
| RII-R2-01 (P1), challenge matching | “The author tests' census sees functions already deleting wiki rows and writers of reply rows. It does not see that replacing a challenged edge changes the meaning of an existing reply's twin restriction.” | §4d's wiki row and INV-R18 (v1.17); the rule is 0004 v3.4 §4c |
| the design | “Keep the accepted 0045/0047 design and its 0008, 0041 and 0019 constructions.” | unchanged: v1.17 changes no rule |

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

---

## Version history — superseded, not the current contract

*Consolidated at the round-4 fold (the round-4 verdict asked that superseded intermediate rules be kept as history, apart from the current contract). Each entry below records what changed at that version, newest first, moved verbatim from the Version cell. **A rule that appears only here, or that an entry here calls withdrawn or superseded, is NOT part of the current contract**, which is the body of this document above.*

- **v1.15 — 2026-10-14: the consolidation the round-4 verdict asked for.** The version narrative moves to the Version history, so superseded intermediate rules cannot read as current. No rule changes. **Earlier versions:** the Version history at the end of this document, which records superseded rules; none of them is current.
- **v1.14 — 2026-10-13: §9's round-4 question names the versions under review.** It asked about v1.9 and the 0008 and 0041 amendments v1.3 and v1.4, which were round 3's. It now names v1.14, the 0008 amendment v1.9 and the 0041 amendment v1.13. No rule changes; found by dev's round-4 stage drafting, then by research's sweep of every version named in a §9 heading or question (paragraph-joined; a question kept for the record is the round-3 one, and stays).
- **v1.13 — 2026-10-13: §2c-ii re-run at veracium `f98a3a0` (main at this fold; `src/` and `specs/` as at `55a7209`); no rule changes.** The 0041 notice-binding hotfix (veracium `98327c2`, on main, never released; recorded as 0041 v15.6, `b1050f5`) shifted `store/sqlite.py`: row 2 now reads L692 (L684 at `cfb4151`). Every other row reads the lines it cited.
- **v1.12 — 2026-10-13: §4f reads the 0041 amendment v1.8 and the 0008 amendment v1.6 (the owner's rulings: refuse where content would land; no origin binding).** In a trusted restore, a held ordinary act takes its source's redaction when the unit carries the target edge showing it; a unit carrying the edge UNREDACTED refuses the whole file; with no copy of the edge the notice is pending unless the held edge already shows it. `Spec-Requires:` drops `0006[0041/0006-origin-restricts]`: that amendment is WITHDRAWN. No rule of this spec's own changes.
- **v1.11 — 2026-10-13: §4f reads the 0041 amendment v1.6 and the 0008 amendment v1.5.** A notice takes effect only where its file SHOWS the redaction, in both modes (the fixed-point rule, the owner's ruling), so §4f's restore-only treatment of a held ordinary act also needs the unit to carry the target edge already treated, and is pending otherwise. v1.10's “shipped 0041 defect” is wrong in the release sense: the defect is in accepted 0041 as implemented on main since `8ea59e7`, in no release. No rule of this spec's own changes.
- **v1.10 — 2026-10-13: an untrusted file's notice never writes held content (the owner's rulings of 2026-10-13, after a shipped 0041 defect).** §4f's replay row reads the 0041 amendment v1.5 and the 0008 amendment v1.4: a held ordinary act receiving its source's redaction (a treated copy with its covering notice) takes the treatment in a TRUSTED RESTORE only. In a default import it is an exact replay (a no-op), the held act is unchanged, and the notice is recorded PENDING for the user's `confirm_notice`. `Spec-Requires:` gains `0006[0041/0006-origin-restricts]`, the 0006 amendment the 0041 amendment's binding requires (an amendment carries no `Spec-Requires:` line, so this spec states the transitive requirement).
- **v1.9 — 2026-10-13, round-4 fold (re-issued the same day after reference model II was encoded against it: the packaging claim is narrowed to one file or successive snapshots of the source, since an arbitrary split is not equivalent): round 3 returned v1.8.1 for R3-01 and R3-02.** **R3-01** (notice treatment × act replay; same-unit UIDs): §4f reads the 0008 amendment v1.3. HELD is the staged union, equality is decided on the canonical treated projection under the union's notice coverage, one authorized transition changes content carriers only, and coverage is all or nothing per row (with the 0041 amendment v1.4). **R3-02** (chronology): the restore rule is validated over the MERGED act history, with references remapped first (§4f, the 0008 amendment §6f). A confirmation made under a challenge unresolved in that history is refused. A legitimate challenge → resolve → confirm history is admitted whether it arrives in one file or as successive snapshots of the source. INV-R23 is restated with the verdict's controls. **Bounded corrections:** the inspection order is a PRODUCT display contract, and a cross-origin position sort is display only, never operation order (§4d). Assertion surfaces, structured consumer duties and inspection displays read ONE snapshot (§4d). §6's red-before-acceptance sentence follows the MODEL/PRODUCT split. The trust label is never compared, and a replay never changes it (§4f). §9 is the round-4 brief.
- **v1.8.1 — 2026-10-13: correction #6 made true.** v1.8's §9 row said the model “names what it does not represent”, and nothing did (found at the package's stage read: research's own unverified closure row). §6 now states what the model does NOT establish (wire validation, migrations, SQL concurrency, cache fencing, the full carrier census), and §9's row points at it. §6's list of this spec's model invariants gains G16 and G18 (INV-R23, R24), which v1.8 cited per row but omitted from the list. The Author cell is taken from the tree (f2195fe). No rule changes.
- **v1.8 — 2026-10-12, round-3 fold (re-issued the same day: §4c's `attested` × challenged cell is NOT ASSERTABLE, the owner's ruling on 0045 R2-01, option 3, after ATTEST-3's holdout result; §3's bullet, §4c's rationale, §5's regime rows and §9 follow); **re-issued again: NOT ASSERTABLE means WITHHELD** for every value, so §4d's assertion surfaces withhold a challenged fact and the unit lives where the record is inspected; INV-R3, R6 and R20 restated; §8's claim follows (dev's model II run found §4c and §4d disagreeing): round 2 returned v1.7 for amendment (R2-02..R2-06 bind this spec, with the 0008 and 0041 amendments).** **R2-02:** an imported act's own key is an internal `#act:` key outside the caller grammar (§2, §4f). **R2-03:** the restore rule reads POSITION (`pos = (origin_store, act_seq)`, the 0008 amendment §6f), never `confirmed_at`, and refuses an order it cannot establish; INV-R23 (§4b, §4f). **R2-04:** exact replay by `act_uid` and projection is a no-op checked before the held-target refusal, and a changed row refuses the file (§4f). **R2-05:** `replies.request_digest` and the registry's digest are treated at redaction (the 0041 amendment v1.3, the 0008 amendment §6g). **R2-06:** an ordinary reply onto a target redacted under a notice that does not cover `replies.text` is refused (§4f). The verdict's bounded corrections: **#2** reinforcement writes a new edge id at the pin, so acts stay on the prior's identity (§4e); **#3** the `unknown` cell states its NEW restriction (§4c); **#5** the reply request's canonical identity is closed, INV-R24 (§4b). *#1, the carrier inventory's ASOF wording, is in dev's generated disposition text, not in this document.* §9 is the round-3 brief.
- **v1.7 — 2026-10-11: an imported act's file id is evidence in `recorded_correlation_id`** (the 0008 amendment v1.1's additive construction, dev's as schema owner); INV-R20, R21 and R22 cite their model invariants (G13, G10, G14), and §6's claim list gains G13 and G14. Prior, same day: **v1.6 — four of the 0044 round-2 verdict's classes, found in this spec before its seal and folded.** **(1) The shared id space is CONSTRUCTED** by a new 0008 amendment, `0047/0008-request-registry` (in `Spec-Requires:`). v1.5's INV-R15 promised one id space with `confirm()`, but the product's replay lookup reads only `confirmations`, so a reply's id was invisible to `confirm()` (R2-04's class). **(2) Historical recall renders the CURRENT acts**, never “written at or before T”: T is valid time and `written_at` is commit time (R2-01's class; INV-R20). **(3) An act's `origin` is stored** and never upgraded, and only `local` and `restored` confirmations count toward `g(e)`. v1.5's “testimony (`origin = imported`)” had no column (R2-05's class; INV-R21). **(4) User erasure removes replies** with their registry rows (R2-07's class; INV-R22). Exporting confirmations reverses 0008 §6d's “excluded”, which v1.5 did without an amendment; the 0008 amendment now says so (R2-06's class). Prior, same day: **v1.5 — INV-R6's mutant cites model G4** (dev's carrier read, T1: §6 claimed G4 as this spec's and no row cited it; the model now runs R6's mutant, the open count derived from the budget-selected challenges, and G4 kills it). Prior, same day: **v1.4 — round 1 returned (R1-03, R1-05..R1-08, R1-10 owned here); the reviewer's answers to R1 and R2 adopted; aligned to 0045 v1.5.** Base: the tree's adopted copy at `cfb4151` (v1.3); the Author and Number cells are dev's and are carried verbatim. 🔴 **v1.3's §0 (the 0041 amendment) is now its OWN document**, `0047/0041-replies`, bound by this spec's `Spec-Requires:` line (R1-10; the owner's “Bind by content”); it answers R1-07 through 0041's existing attested-carriage path. 🔴 **The reply kind `disputed` is renamed `challenge`** (R2, the reviewer's preference) and a structured **`resolve`** kind is added (R1-06): context text never clears a challenge, and v1.3's “a `context` reply saying the dispute no longer stands” recovery is WITHDRAWN — the reviewer showed it could not work. 🔴 **§4c's grid reads 0045 v1.5's four values** (`attested` · `confirmed` · `not_attested` · `unknown`), and is stated as an ADDITIONAL restriction only (R1-05). **§4d is the rendering construction R1-05 asked for:** a deterministic mandatory unit, withholding on overflow, wiki exclusion with atomic eviction and an in-flight fence, historical semantics at T. **§4e–§4f are R1-03's and R1-08's matrices.** **One narrowing, stated:** v1.3 rendered `context` and `withdrawn-consent` replies beside the edge in recall; v1.4 confines them to `why` and the structured returns, so the recall unit has ONE deterministic shape (R1-05) — §9 names it as least sure. **§0a is decided** (the reviewer agreed with refusing a new content reply to a redacted edge; restoring an already-redacted reply is the amendment's notice path). The rules are a separate artifact executed by dev's reference model (§6).
- v1.3 · v1.2 · v1.1 (the joint candidate's Part B).

## Annotation — T11b, act portability (2026-10-20; every row above is kept as written)

*Append-only; this spec's accepted text above is unchanged. T11b implemented §4f. Two readings it took of rows here, §4b's
"written by the same subject label" (L177) and `written_at` as "a local clock that does not travel as an order" (L191–L192)
beside §4d's display order (L225), are recorded with the owner's two rulings on act portability (R-D6, the remap
namespace; R-M1, legacy order in a trusted restore; Quentin, 2026-10-20) in specs/0008's T11b annotation, which quotes
each. Disclosed to the R-II package's reviewer.*

### Addendum — T12, the census at the closing gate (2026-10-20; the rows above are kept as written)

*§4d's count is dated ("At 2026-10-11 it lists 65 functions", L238) and stays as written. At T12 the carrier inventory
(`specs/evidence/0047/carrier_inventory.py`) censuses 69 functions, 0 unclassified, 0 stale, 0 awaiting a ruling. The R-II
package records the census re-run at its pin, and quotes §8's statement of what the three keys do not see.*
