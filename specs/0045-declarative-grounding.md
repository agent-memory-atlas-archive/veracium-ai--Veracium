# Feature spec: the declarative grounding axis — was a fact STATED, or not shown to be?

Spec-Status: draft
Spec-Requires: 0047, 0019[0045/0019-nonuser-refusal], 0008[0047/0008-request-registry]

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.3 2026-09-20 from `0045-declarative-grounding-CANDIDATE.md` (sha16 bca55cc31018d5de); v1.4 2026-10-10 from `0045-declarative-grounding-CANDIDATE.md` (sha16 7e306b4bcd327921); v1.7 2026-10-11 from `0045-declarative-grounding-CANDIDATE.md` (sha16 e7ef2f26ad8af86e); v1.8 2026-10-12 from `0045-declarative-grounding-CANDIDATE.md` (sha16 1da099c906128cdf); v1.10 2026-10-13 from `0045-declarative-grounding-CANDIDATE.md` (sha16 f7ce9e4af1258b7c) |
| **Version** | **v1.10 — 2026-10-13: §2c-ii re-run at veracium `f98a3a0` (main at this fold; `src/` and `specs/` as at `55a7209`); no rule changes.** The 0041 notice-binding hotfix (veracium `98327c2`, on main, never released; recorded as 0041 v15.6, `b1050f5`) shifted `store/sqlite.py`: row 4 now reads L694 (L686 at `cfb4151`). Every other row reads the lines it cited. Prior: **v1.9 — 2026-10-13, round-4 fold (re-issued the same day after reference model II was encoded against it: `attv` names WHAT produced `att`, adding `non-user-effective`, and may be NULL for a restored `att` without one): round 3 CLOSED R2-01, raised no independent 0045 blocker, and held joint acceptance to 0047.** Its bounded corrections, folded here: every “no downstream privilege” now says **“no challenge-gate privilege”**, because §4d's source-redacted guard deliberately distinguishes `attested` from `not_attested`, and §4a now says so. The stale “It is safe” sentence is gone (§1b), and so is §7's residual “the speaker said it”. §6's red-before-acceptance sentence follows its MODEL/PREDICATE/PRODUCT split. **The owner's ruling (2026-10-13), the version carrier:** a durable `attv(e)` is written with `att`, from the same evaluation, and never rewritten. It travels with `att` on export. A legacy row reads “version unknown”, never the current version. It has its own redaction, erasure and export disposition (§2, §4f). INV-G13 is new. §9 is the round-4 brief. Prior: **v1.8 — 2026-10-12, round-3 fold: round 2 returned v1.7 for amendment (R2-01, with a joint dependency on 0047).** **R2-01:** ATTEST-3 replaces ATTEST-2: one supported construction instead of a blacklist (§4a), frozen before its fresh blind holdout H2, scored once: 1 / 67 false attestations (one-sided 95% upper bound ≈ 6.9%) and 12 / 53 recall, against ATTEST-2's 5 / 67 and 16 / 53 on the same H2. Every R2-01 negative stays non-attested, and 8 mechanism mutants are killed. **The owner's rulings:** ATTEST-3 in round 3 (2026-10-12, option A); then, on its result, **`attested` is a LABEL with no challenge-gate privilege** (2026-10-12T23:40Z, option 3, the verdict's narrowing route; 0047 v1.8 §4c). §2c, §3, §4c, §6 (INV-G2), §7, §8, §9 and §10 (G1) follow. Prior: **v1.7 — 2026-10-11: `confirmed` counts only `local` and `restored` confirmations.** An `imported` one is testimony: 0047 v1.6 stores an act's `origin` by the 0008 amendment `0047/0008-request-registry`, now in `Spec-Requires:`. v1.6's “any 0008 confirmation” would have read an imported confirmation as the user's own act (the 0044 round-2 verdict's R2-05 class, found here before the seal). §6 cites rules draft 3.4. Prior, same day: **v1.6 — the ATTEST evidence lands WITH this spec, at `specs/evidence/0045/attest/`** (dev's README read: v1.5's §4a said the implementation gate and its §9 said with the spec; G1 is blocking and its closure is that measurement, so a reviewer must be able to re-run it). §4a, §4a's measurement line and §9's R1-01 row name the landed path. Prior, same day: **v1.5 — round 1 returned (R1-01..R1-03 owned here), and the owner's “Label, don't block” and “Add the link” folded.** Base: the tree's adopted copy at `cfb4151` (v1.4); the Author and Number cells are dev's and are carried verbatim. 🔴 **v1.4's central argument is WITHDRAWN:** §1c said this spec “EXTENDS 0019 and adds no field” by widening 0019's predicate from specifics to terms. **R1-01** showed a terms test cannot establish that the user asserted the relation (“I do not work as a dental technician” passes it). **R1-02** showed `ungrounded = False` never meant “stated”. And the reviewer's closing note: *the no-new-field preference is useful only while the available state supports the promised meaning*. So v1.5 adds **two stored per-edge values**, `att` (the attestation verdict) and `src` (the source episode it judged), and **leaves 0019's predicate unchanged**. **R1-01's construction is measured**: a bounded relation-specific grammar, ATTEST-2, scored on a blind 120-item holdout. It falsely attested **0 of 66** negatives, and it recognised **9 of 54** genuine statements. **That measurement produced the owner's ruling** (2026-10-11, “Label, don't block”): an unrecognised USER statement is STORED and labelled `not_attested`, not refused. **This reverses v1.4's persistence line for USER-effective events.** The proposal mechanism of v1.4's companion amendment is withdrawn with it. The upgrade to `confirmed` is 0008's existing `confirm()` on the stored edge, and the source link (“Add the link”, 2026-10-11) keeps the owner's R1-04 ruling. The transition rules are a separate artifact, executed by dev's reference model (§6). **The label is `not_attested`** (renamed from `not_verified` after dev's carrier read, before adoption): see §4c. Prior: v1.4 · v1.3 · v1.2 · v1.1 · v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — it changes what the agent may ASSERT about a person, and what ingest records about how it knows. Round 4. |
| **Decision + date** | **Q2 (a confirmation path is intended): yes, the owner, 2026-10-10.** **R1-02's legacy policy: an explicit `unknown`, the owner, 2026-10-10.** **R1-04: an erased source ends the upgrade path, the owner, 2026-10-10.** **GP1: MCP-only gets no confirmation path, the owner, 2026-10-10, narrowed 2026-10-11 to “cannot upgrade”.** **“Label, don't block”: the owner, 2026-10-11. “Add the link”: the owner, 2026-10-11. “Only declared-direct calls” (G5): the owner, 2026-10-11.** Acceptance: pending the external round. |
| **Path** | **full** |
| **Number** | 0045 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | none. Occasioned by `A9` (Solove's aggregation; Lee et al., CHI 2024, from 321 documented AI privacy incidents). **Travels with** 0047 (the subject's reply) and the 0019 amendment (`0045/0019-nonuser-refusal`) in one package. |

---

## 1. Problem and motivation

### 1a. The demand, and why it is not a preference

The harm literature names **correct-but-uninvited inference** as a harm in its own right — *“don't derive the thing
I deliberately never told you”* — and benchmarks reward precisely that, since it is what multi-hop items score. **The
scoring rule and the demand have opposite signs.** Our extractor infers.

**A9's ruling:** *“ingest never writes an attribute the user did not state UNLESS CONFIRMED.”* This spec is the axis
that ruling needs: **was a fact STATED, or not shown to be?**

### 1b. 🔴 What the round-1 measurement changed

R1-01 asked for a bounded attestation predicate with a measured corpus. We built one and measured it blind
(§4a). On its first blind holdout (H1) it falsely attested **0 of 66** negatives, a measurement of that fixture, not a
guarantee (round 2 then found negatives it attests, §4a). And it recognised only **9 of 54** genuine
self-statements, because real people say “been vegan for 3 years now” and “Brisbane-based here”, not “I am
vegan”. Under v1.4's line, the other 45 would not have been written. In an MCP-only deployment, which has no
confirmation path (GP1), **about 5 in 6 of what users say about themselves would have been dropped.**

**The owner's ruling (2026-10-11), “Label, don't block”:**
- the strict predicate is the ONLY way to earn `attested`;
- a USER-effective statement it does not recognise is **stored** and labelled `not_attested`;
- 0019's marker stays wherever 0019's flag is set;
- inferences from non-user sources are still refused;
- upgrading to `confirmed` is optional.

**So A9's line now reads:** *ingest never writes an attribute as though the user stated it unless the predicate
recognises the statement or the user confirms it.* What is written otherwise is labelled, not hidden.

### 1c. `basis` cannot be borrowed (unchanged from v1.4)

0037's `basis` is “never applicable to a declarative record”, and the stored rule is
`procedural iff record_kind == "procedural" OR basis is not None`. **Stamping `basis` on a fact would make it
procedural by floor**, which is 0037's anti-laundering invariant working as designed (§2c-ii row 2).

### 1d. Why two new stored values, against v1.4's “no new field”

- **`att(e)`, the attestation verdict.** The predicate reads the source event's RAW text, and **no raw text is
  retained** (R1-02). So the verdict cannot be recomputed later and must be stored at insert.
- **0019's `ungrounded` flag cannot carry it.** The flag is a different predicate over a different input: specifics
  tokens against the episode carrier. Its `False` never meant “stated”, as the reviewer's witness shows:
  `ungrounded("electrician", "I repair radios on weekends.", …)` is `False`.
- **`src(e)`, the source episode `att` judged.** A verdict about one event, stored without naming the event, cannot
  be audited, and it goes stale silently when its source is redacted. The owner's R1-04 ruling needs exactly that
  link (§4d).
- **The two predicates stay ORTHOGONAL.** Neither is derived from the other. **0019's predicate, flag and marker are
  unchanged.**

### 1e. Alternatives rejected

- **Widen 0019's predicate from specifics to terms** (v1.4): R1-01's counterexamples. A terms test admits negation,
  conditionals and other speakers.
- **Derive grounding from 0019's flag** (v1.4, and rules draft 2): R1-02. It labels every unflagged row “stated”.
- **Refuse what the predicate does not recognise** (v1.4's persistence line): at 9 in 54 recall it drops most of
  what users say (§1b). Rejected by the owner.
- **An LLM judge for attestation:** much higher recall, but the event text is untrusted, so the judge can be
  injected **at the field that certifies trust**, and it is nondeterministic. Rejected in favour of a
  deterministic grammar measured version by version.
- **Reuse `basis`** (§1c). **Make the model declare grounding** (§4a: it would be marking its own homework).
- **A minted proposal token for the upgrade** (v1.4's amendment; GP2's HMAC): it existed only because the
  unattested triple was not stored. Now it is stored, and the upgrade acts on the edge (§4c).

---

## 2. Field contracts touched

| field / site | read / written | its documented contract | preserved? |
|---|---|---|---|
| **`att(e)`** *(new, stored)* — **declarative edges only** | written ONCE at insert by ingest, from ATTEST over the source event's raw text; immutable | `attested` · `not_attested` · NULL (written before this spec) | new |
| **`src(e)`** *(new, stored)* | written ONCE at insert, from the SAME input as `att`; immutable | the episode id of the event `att` judged · NULL | new |
| **`attv(e)`** *(new, stored; v1.9, the owner's ruling)* | written ONCE at insert WITH `att`, from the same evaluation; immutable; read by `why` | WHAT PRODUCED `att`: the predicate version that judged it (`ATTEST-3@b1329a81`) · `non-user-effective` (§3, §4b: the write path set `not_attested` for a non-USER-effective event, and no predicate ran) · `default-import` (§4e: no predicate judged it here) · NULL when `att` is NULL (legacy), or when a trusted restore's file carries `att` without `attv` (both read “version unknown”) | new |
| `g(e)` grounding *(derived, never stored)* | read by render, `why`, `introspect`, the structured returns, 0047's gate | `confirmed` if any 0008 confirmation whose `origin` is `local` or `restored` (an `imported` one is testimony, 0047 §4f) · else `attested` / `not_attested` / `unknown` (from `att`, with NULL → `unknown`) | new |
| `Edge.ungrounded` and 0019's predicate | read and written as today | 0019 §4b–§4d | **preserved, unchanged** — v1.4's widening is withdrawn |
| ingest's write path | writes | 0019: store a flagged edge with its marker | **preserved for USER-effective and unflagged non-user events; non-user + flag set is REFUSED and counted** — the 0019 amendment, `0045/0019-nonuser-refusal` |
| `confirm()` (0008) | refuses | refuses an unknown or non-assertable edge | **one refusal added: a `not_attested` edge whose `src` carries a 0041 redaction notice** (`store.confirm.source-redacted`, “state it anew”). 0047 adds the active-challenge refusal |
| the schema | a step | — | a step adding `att`, `src` and `attv`, taken AFTER whichever package's step lands first (0044's in package I). **This spec names the dependency, not a number** |

---

## 2c. Untrusted inputs — REQUIRED, blocking

| uncontrolled input | empty | malformed | unrecognised | adversarial | **invariant that pins it** |
|---|---|---|---|---|---|
| **extractor output**, including any field claiming the triple's grounding | no triple | the extractor's refusal | outside the vocabulary → unclassified route | **a model-supplied grounding claim is IGNORED**; `att` comes only from ATTEST over the raw text | **INV-G1** |
| **the source event's raw text** (host-supplied) | `not_attested` | `not_attested` | a construction outside the grammar → `not_attested` (the safe direction) | whoever authors the event text authors what ATTEST reads; **ATTEST recognises only first-person USER statements in one supported construction, so it can be fooled into `attested` only by text that states the fact in that construction** (0019 §8 limit 1, inherited), *or, as H2 measured once in 67, by a retraction phrased outside its closed list (§4a); which is why `attested` carries no challenge-gate privilege* | **INV-G2**, §4a |
| **the source event's author** | — | — | — | non-user events never earn `attested` under ATTEST-3 | **INV-G2** |
| **the query** (recall) | — | — | — | the persistence line does not reach query time | **INV-G6** |
| **data written by an older version** | `att` NULL → `unknown`; never re-derived | — | — | **treating an old False or missing flag as attested is the mutant R1-02 names** | **INV-G7** |
| **an import file's `att` / `src` / `attv`** | — | an `attv` outside its grammar (`ATTEST-<n>@<8 hex>`, `non-user-effective` or `default-import`) → the unit refused | — | default import writes `not_attested`, NULL and `default-import` whatever the file says; trusted restore as recorded, with a referential check on `src`; a file `att` without an `attv` is restored with `attv` NULL (“version unknown”), never the current version | **INV-G9**, **INV-G13** |

### 2c-ii. Assertions about reach — REQUIRED

Commands run from the repository root at `cfb4151` (research, 2026-10-11); re-run at `f98a3a0` (research, 2026-10-13), where row 4 reads L694 and every other row the same lines.

| # | assertion | command | result |
|---|---|---|---|
| 1 | 0019's predicate is specifics-only, and stays so | `grep -n "True iff any specifics token of the" src/veracium/grounding.py` | READ: L201 |
| 2 | `basis` makes a record procedural by floor | `grep -n "basis is not None" src/veracium/schema.py` | READ: L233, L237, L283, L319 |
| 3 | ingest stores a flagged edge today | `grep -n "A failing edge is STORED with the flag" src/veracium/ingest.py` | READ: L729 |
| 4 | `confirm_edge` refuses a non-assertable edge | `grep -n "is not assertable (quarantined/use_only/" src/veracium/store/sqlite.py` | READ: L686 · at `f98a3a0`: L694 |
| 5 | MCP exposes no confirm tool | `grep -n -A1 "@server.tool()" src/veracium/mcp_server.py` | READ: six tools, `remember` `recall` `answer` `maintain` `record_procedure` `describe_procedures` (the two other matches are comments, L38 and L382) |

*Lexical reach only, as the reviewer distinguished. The executed evidence is §4a's corpus and §6's model.*

---

## 3. Trust-class matrix — REQUIRED, blocking

Classes from the enums at `cfb4151`: `EvidenceAuthor` = user, third_party, system, assistant; `Disclosure` =
mentionable, use_only, quarantined.

**The axis is orthogonal to trust class:** grounding never changes authority, disclosure or confidence. What differs
by class is what ATTEST can establish and what ingest refuses.

**USER-effective is the product's own resolved trust, not a new notion:** the effective author is `user` AND the
resolved content source is direct (`EvidenceContext.direct()`). 🔴 **So a caller that does not declare first-party
capture is NOT USER-effective**: the Python API's default (`context=None` resolves to the floor `derived(THIRD_PARTY)`,
0011) and MCP under capability NONE (author baseline `third_party`, 0031). For those callers nothing is `attested`,
and a flagged triple is refused (the 0019 amendment). **RESOLVED 2026-10-11 by the owner: “Only declared-direct calls”** (reading (A)): the floor is non-user here; only a declared-direct
USER call gets the user path (§10 G5).


| source event (effective) | 0019 flag unset | 0019 flag set |
|---|---|---|
| **user** | stored; `att = attested` if ATTEST recognises the statement, else `not_attested` | stored with 0019's marker; `att` as on the left |
| **system** · **assistant** · **third_party** (any disclosure) | stored; `att = not_attested` (ATTEST-3 covers first-person USER statements only, so a statement in a third-party event is never attributed to the user, R1-02) | **refused and counted** (`nonuser_ungrounded_refused`) — the 0019 amendment |

- Can it make a **user-asserted fact non-assertable**? **No**, the reversal of v1.4. An unrecognised user statement
  is stored and assertable exactly as today (0047's gate restricts only challenged facts).
- Can **non-user content gain user-grade authority, or be labelled as the user's statement**? No.
- Can it **clear `needs_confirmation`**, or **merge, drop or overwrite provenance**? No. `src` ADDS provenance.

**Write-time or maintain-time?** Write-time. Nothing re-labels a stored edge.

## 3b. Authorization and scope — *full specs only*

No new surface. `confirm()` keeps 0008's authorization; MCP gains no tool (§2c-ii row 5). `g(e)` appears in `why`,
`introspect` and structured returns under each surface's existing scope.

---

## 4. Behaviour

### 4a. Attestation is a bounded, versioned construction — R1-01, R2-01

**The predicate, ATTEST-3** (frozen before its holdout existed, sha256 `b1329a81…`; research's 0045 evidence set,
landed with this spec at `specs/evidence/0045/attest/`, so that every figure below can be re-run). ATTEST-2 matched a
trigger anywhere in a sentence and then excluded bad contexts with a finite blacklist; round 2's reviewer showed six
strings it attested that state nothing of the kind (R2-01). **ATTEST-3 accepts ONE positive construction and nothing
else:**

| R2-01 asked for | ATTEST-3 |
|---|---|
| scope | `subject = user` and a declarative relation with a trigger table. **The procedural path is exempt**: 0037's quote gate governs it, and it is never passed here. Any other subject or relation → `UNSUPPORTED` → `not_attested` |
| quotation | double-quoted text is removed from the WHOLE event before it is split into sentences, so a quote spanning sentences is removed whole; an unbalanced quote removes the rest (fail closed). *Single quotes cannot be told from apostrophes and are NOT removed: stated* |
| assertion scope | the trigger must BEGIN its sentence; before it, only a closed set of discourse fillers (“yes,”, “honestly,”, “these days”). Any other frame (“Suppose”, “It is false that”, “He wrote:”, “Example sentence:”) puts the trigger inside it, and nothing is attested |
| the complete complement | the object must be the trigger's WHOLE complement: after it, the end of the sentence, clause punctuation, or a closed list of function words. A following content word, a possessive or a hyphen means the object named only part of what was said (“dentist assistant”, “dentist's receptionist”, “dentist-in-training”) |
| binding the relation | a SPECIFIC trigger binds its relation (“I work as”, “I live in”); a GENERIC one (“I'm a”, “I am”, “I have”) binds it only through that relation's closed lexicon (occupations, diets, conditions, animals). “I am a diabetic” is not an occupation; “I am tired” is not a diet |
| polarity, modality, reported speech | ATTEST-2's lists, kept as defence in depth, over the rest of the sentence |
| questions; retraction | a sentence ending `?` asserts nothing; a retraction ANYWHERE in the event (a closed list: “just kidding”, “not really”, …) attests nothing from it |
| normalisation (enumerated, and only these) | case-fold; curly to straight apostrophes; whitespace collapsed; a number and a unit from a closed list joined (`78 kg` = `78kg`); trailing punctuation stripped; a leading article dropped from the object |
| empty input | `not_attested` |

**The measurement, in the order it happened** (the evidence set's README is the account; the commits are in research's
repository, which a reviewer cannot open, so the files are the evidence):

| step | result |
|---|---|
| ATTEST-1 on a corpus written with it, then 12 probes written after | 0 false attestations, then **6 of 7 negatives falsely attested** |
| ATTEST-2 frozen; holdout H1 (120 items) written blind by an independent author with no tool access; a second blind labelling | 120/120 agreement; **0 / 66 false attestations, 9 / 54 recall** |
| Round 2's reviewer, and research's same-class probes | **ATTEST-2 attests 6 + 17 negatives** (R2-01) |
| ATTEST-3 frozen with its development gate | the 23 negatives and 12 more of the same classes stay non-attested; the earlier development sets give 0 false attestations in 56 negatives. **Tuned on development sets only** |
| ATTEST-3's mechanism mutants, one per rule above plus R1-01's three (drop polarity, swap subject, terms presence) | **all 8 KILLED** on development negatives only; control clean first and last |
| holdout **H2** (120 items, 53 true), written by an independent author with no tool access from the gold question and relation glosses only, then a second blind labelling (120/120 agreement); scored ONCE | **ATTEST-3: 1 / 67 false attestations** (one-sided 95% upper bound ≈ 6.9%), **12 / 53 recall (23%)**. ATTEST-2 on the same H2: 5 / 67 and 16 / 53 |
| H1, as regression only | ATTEST-3: 0 / 66, 5 / 54 |

**The one false attestation on H2** is “I use Obsidian. Actually wait, no, I switched to Logseq last month, ignore
that.” A retraction in a later sentence, phrased outside ATTEST-3's closed retraction list: an OPEN-ENDED class, and
the same structural weakness the reviewer named in ATTEST-2. It is reported, not repaired; a repair is a new version
with a fresh holdout.

**What `attested` therefore means, and what it does not (the owner's ruling, 2026-10-12, R2-01's narrowing route):**
`attested` is a LABEL, “ATTEST-3's construction matched a first-person statement of this fact in the user's own
event”, **never proof of what the speaker stated**. It carries **no challenge-gate privilege**: under an active
challenge it gates like every other value (0047 v1.8 §4c). *It is not without effect elsewhere, and this spec says so
(v1.9): §4d's source-redacted guard refuses confirming a `not_attested` edge whose source was redacted, and does not
refuse an `attested` one. That distinction is the owner's narrower guard, retained as ruled.* Its gain over ATTEST-2
(5 → 1 false attestations on H2, and every R2-01 negative refused) stays in the label.

**The version carrier (v1.9, the owner's ruling).** Every `att` is written with **`attv(e)`**, the identity of WHAT
produced it, from the SAME evaluation, in the same insert, and never rewritten: for a statement the predicate judged,
`ATTEST-3@b1329a81` (the version and the first 8 hex digits of its frozen sha256); for a non-USER-effective event,
where the write path sets `not_attested` and no predicate runs (§3, §4b), `non-user-effective`, never a predicate
version that did not run. `why` names the version FROM `attv`, never from the
predicate the running build carries. So a historical verdict is never labelled with the current version, and a
second predicate version can coexist with the first.

**Versioning:** a later version ships only after it is measured on a FRESH holdout, with its false-attestation rate
reported beside the version. A version change never rewrites stored `att`.

### 4b. The persistence line — the policy half of `A9`, as ruled

| | |
|---|---|
| **at query time** | 🔴 **derivation is unrestricted.** A question invites its own derivation (INV-G6) |
| **at ingest, USER-effective** | **stored**, labelled `attested` or `not_attested` (**reverses v1.4's “an unattested attribute is NOT WRITTEN”**, the owner's ruling) |
| **at ingest, non-user, 0019 flag set** | **refused and counted** (`nonuser_ungrounded_refused`) |
| **at ingest, non-user, flag unset** | stored, `not_attested` |
| **edges, not episodes** | this spec claims EDGES. Episode-level derivation is OUT OF SCOPE: an episode is a narrative summary whose nature is derivation |

### 4c. Grounding — four derived values

| `g(e)` | when | meaning claimed | rendered |
|---|---|---|---|
| **`attested`** | `att = attested`, no confirmation | **a LABEL:** ATTEST-3's construction matched a first-person statement of it in the source event, never proof (§4a; 1 / 67 false on H2) | today's line; `why` names the label and its version, read from `attv` (v1.9); **no “you said” claim**, and no challenge-gate privilege (0047 §4c) |
| **`confirmed`** | any 0008 confirmation of `origin` `local` or `restored` | the user confirmed it | today's line; “you confirmed” |
| **`not_attested`** | `att = not_attested`, no confirmation | **only that ATTEST did not attest it** — the predicate cannot tell a casual true statement from an extractor's inference, so the label never says “inferred” or “unstated” | today's line, **no new inline marker** |
| **`unknown`** | `att` NULL (written before this spec), no confirmation | grounding was never recorded | today's line |

**The name is `not_attested`, never “unverified” / “not verified”** — 0019 §4c's own ruling, which applies here a fortiori: “unverified” is the product's THIRD-PARTY-CLAIMS partition (`Recall.unverified`, rendered under `## UNVERIFIED THIRD-PARTY CLAIMS (never assert as fact)`; the `gate.answer.unverified-only` site), so a user's own statement labelled “not verified” would read, to a model or host, as never-assert — the block this ruling refuses. `not_attested` claims exactly what was measured: ATTEST did not attest it. (0 matches for `not_attested` in src/, specs/ or the test harness at cfb4151.)

**Procedural edges carry NO `att`, NO `attv` and NO `g(e)`** — 0037 governs them, and its `basis` (derived from the quote gate) is their grounding; a procedural row is one with `record_kind == "procedural"` or `basis` set (0037's floor rule). A NULL `att` on a procedural row is never read as legacy, and no grounding gate or reply applies to it. *(Found from dev's carrier census, 2026-10-11: as first written, “an insert without `att` is refused” would have refused every new procedural edge.)*

**0019's marker is independent of all four values** (INV-G8): wherever 0019's flag is set, the marker renders,
whatever `g(e)` is.

**Where the label lives:** `why`, `introspect` and the structured returns carry `g(e)` by name. *An inline marker on
5 in 6 user facts would teach readers to ignore markers, 0019's included. The label sits where a reader asks “how
do you know?”.*

### 4d. The upgrade path, and the source link — R1-04, GP1

**`not_attested` → `confirmed` is 0008's `confirm()` on the stored edge.** It is optional, and a host that never
offers it loses nothing. **MCP-only deployments cannot upgrade** (no confirm tool, §2c-ii row 5). GP1 as narrowed by
the owner: **under capability DIRECT** they no longer lose a user's statements; **under capability NONE** every call is
non-USER-effective (§3), so unflagged triples are stored and flagged ones refused (§10 G5, resolved).

**The owner's R1-04 ruling** (an erased source ends the upgrade): `confirm()` **REFUSES a `not_attested` edge whose
`src` carries a 0041 redaction notice**, “state it anew”. *Dev executed the need: without this rule, after
`Memory.redact(episode_id=…)` the derived edge stays active and assertable, and `confirm()` accepted it.*

| the rule's boundary, stated | |
|---|---|
| scope | `not_attested` only. The ruling was about suggestions. The uniform rule would ALSO refuse confirming an `attested` edge whose source is redacted (the model shows the case), and would change accepted 0008 |
| post-version only | legacy rows (`att` NULL) have `src` NULL and keep today's `confirm()` |
| an event with no episode carrier | `src` NULL with `att` set. Nothing is linked, so **the R1-04 protection does not apply on that path** |
| a redaction AFTER a confirmation | the confirmation stands (the rule gates `confirm()`, it does not revoke), consistent with “erased BEFORE the user confirms” |
| the 0046 boundary | `src` is ONE source episode per edge row, not the contributor set behind a consolidated fact. 0046's typed contributor is still owed |

### 4e. Identity transitions and import — R1-03, for this spec's state

The full matrix is the transition rules' §7–§8, executed by the model. This spec's state follows it:
- **absorption:** the survivor's `att` and `src` are the INCOMING edge's own. The survivor's object is the
  incoming's, and ATTEST judged that object against that event. *Never copy an attestation or confirmation to a more
  specific proposition* (the reviewer's mutant).
- **supersession:** the new edge's are its own.
- **default import:** `att = not_attested`, `src` NULL and `attv = default-import`, whatever the file says.
- **trusted restore:** as recorded, `attv` with `att`, with a referential check on `src`.
- **0019/0014's absorption OR rule for the flag is unchanged.** The axis never reads the flag, so draft 2's
  verifier amendment (G2) is withdrawn. The model shows every invariant holding with the OR rule on and off.
- **`attv` moves with `att`, always** (v1.9): wherever this list carries `att` (the incoming's, the new edge's, the
  recorded one), it carries that row's `attv`.

### 4f. The grounding carriers' dispositions (v1.9)

Round 3 asked that the version carrier have its own redaction, erasure and export disposition. The three stored
fields are stated together, since the same question applies to each:

| carrier | redaction (0041) | user erasure | export / import |
|---|---|---|---|
| `att` | **PRESERVE**: a closed value, no content | deleted with its edge | carried on the edge line; §4e's import rules |
| `src` | **PRESERVE**: an episode id; it must survive so that §4d's guard can see the SOURCE's redaction | deleted with its edge | carried; trusted restore checks it refers to an episode in destination ∪ file; default import writes NULL |
| `attv` | **PRESERVE**: a producer identifier, no content | deleted with its edge | **carried WITH `att`**, so a second hop cannot relabel a historical verdict; default import writes `default-import`; a file without it restores NULL (“version unknown”) |

None of the three holds text derived from the fact or the event. *That is this spec's claim. 0041's carrier census is
the PRODUCT check that they add no content carrier, run when they land.*

---

## 5. Regime analysis — where does this behave differently?

| regime | behaviour |
|---|---|
| **a user statement ATTEST recognises** | stored `attested`; renders as today |
| **a user statement it does not recognise** (5 in 6 on H1) | stored `not_attested`; renders as today; optionally confirmed |
| **a non-user event, 0019 flag set** | **refused and counted** — the one new refusal |
| **legacy store** | `unknown`; nothing re-derived (INV-G7) |
| **MCP-only, capability DIRECT** | a user's statements kept; no upgrade |
| **an undeclared caller** (Python default, MCP capability NONE) | non-USER-effective (§3): unflagged stored `not_attested`, flagged refused; nothing `attested` (§10 G5) |
| **query time** | unchanged (INV-G6) |

**Not measured:** how often non-user flagged triples occur. The new refusal's loss is unmeasured, and this spec makes
no usefulness claim about it (the reviewer's G2 note).

---

## 6. Invariants and executable checks — REQUIRED, blocking

**MODEL checks** run against the transition rules (research's grounding × reply × confirmation
transition rules, draft 3.4, sha16 b697bda6) in dev's executable reference model II **before design acceptance**: every invariant holds
and every declared mutant is killed by its own invariant — the counts are the model's machine-readable run result in the
package, not restated here (they moved three times while this text was written). **PREDICATE checks** run against frozen ATTEST-3: its development gate, its mechanism
mutants, and the blind holdout H2 (§4a). **PRODUCT tests** are named here and land at the implementation gate. *v1.4's sentence that conflated the
model and product checks is withdrawn.*

| | invariant | check, and the MUTANT it must fail on |
|---|---|---|
| **INV-G1** | **`att` comes only from ATTEST, never from the model** | an extractor output claiming its grounding is ignored. **Mutant: honour the field → FAILS** |
| **INV-G2** | **ATTEST attests only its supported construction, and `attested` is a label with no challenge-gate privilege** (R2-01) | predicate checks: every R2-01 negative and its classes stay non-attested; the blind holdout H2 is reported as measured (1 / 67). **Mutants: quotes removed after splitting · any material before the trigger · a prefix of the complement · generic triggers without the lexicon · retractions ignored · drop polarity · swap subject · terms presence → each KILLED** (§4a). The privilege's absence is 0047's INV-R12 |
| **INV-G6** | **The persistence line does not reach query time** | a multi-hop question is still answered. **Mutant: apply the ingest rule at recall → FAILS** |
| **INV-G7** | **Legacy rows are `unknown`, never re-derived** | **Mutant: read an old False or missing flag as `attested` → FAILS** (model G1) |
| **INV-G8** | **0019's marker follows the FLAG on every grounding value**, legacy included | **Mutant: suppress the marker on `attested` or `unknown` → FAILS** (model G7) |
| **INV-G9** | **The write path is “label, don't block”**: every USER statement is stored; a non-user flagged triple is refused and counted; non-user unflagged is stored `not_attested` | **Mutant: the rejected design, “an unrecognised user statement is not stored” → FAILS** (model G8); default import writes `not_attested` and NULL `src` (model G10) |
| **INV-G10** | **`confirm()` refuses a `not_attested` edge whose source is redacted**, with controls: a standing source confirms; legacy NULL keeps today's behaviour | **Mutant: `confirm()` ignores a redacted source → FAILS** (model G9) |
| **INV-G11** | **an absorbed survivor's `att` and `src` are the incoming's** | **Mutant: copy the prior's `att` (laundering) → FAILS** (model G6) |
| **INV-G12** | **Procedural edges carry no `att` and no `g(e)`**: a post-version procedural insert without `att` is admitted, and a declarative control keeps its axis | **Mutant: refuse an att-less insert, procedural included (rules draft 3.2's rule) → FAILS** (model G12) |
| **INV-G13** | **(model G21)** **`attv` is written with `att`, from the same evaluation, and never rewritten; a non-USER-effective write records `non-user-effective`, never a predicate version it did not run; `why` reads the version from `attv`; a legacy row reads “version unknown”; `attv` travels with `att`** (v1.9, the owner's ruling) | **Mutants: label a legacy or version-less row with the current predicate's version; record the predicate version for a non-user-effective write; read `why`'s version from the running build instead of `attv`; drop `attv` on export (a second hop relabels) → each FAILS**. Controls: two coexisting predicate versions in one store; default import writes `default-import` |

**Each MODEL and PREDICATE check is demonstrated RED against its mutant at the design gate**, and the model's run
result is machine-readable and travels in the package. **Each PRODUCT test is demonstrated red at the implementation
gate**, where it is owed (v1.9: this follows the split above, and does not demand unimplemented product tests at
design acceptance).

---

## 7. Failure modes and reversibility

- **Silent failure:** ATTEST is too narrow, so most real statements are `not_attested` (measured on H2: 41 of 53). **Not
  silent and not lossy:** they are stored and assertable, and the label is visible on `why` / `introspect`. The cost
  is a weaker “you said” claim, not a missing fact.
- **The other direction:** ATTEST attests something not stated. Measured on H2: 1 of 67 (≈ 6.9% upper bound), a
  retraction outside its closed list; on authored chat, not real ingest. **Its consequence is bounded by design:**
  `attested` is a label and carries no challenge-gate privilege, so a false attestation changes a word in `why`, never
  what is asserted under a challenge (§4a, 0047 §4c). Its one other effect is §4d's guard: a falsely `attested` edge
  whose source was redacted can still be confirmed by the user, as an `attested` one is by design.
- **The new refusal:** non-user flagged triples are refused; the count names it.
- **Reversible?** `att` and `src` are additive and never rewritten. A refused non-user triple stores nothing; its
  evidence is the episode and the count.
- **Attack surface:** an author who writes first-person text in ATTEST's enumerated forms earns `attested` for it.
  The label claims only that the construction matched (§4a), never that the speaker said it. Text from a non-user
  source never earns it.

---

## 8. Claims and limits

**Claimed:**
- an attribute is labelled `attested` only if the user's own event matches the pinned predicate's construction (a
  label, not proof: §4a);
- an unrecognised statement is stored and labelled as not attested, never as stated;
- grounding is never declared by the model;
- confirming a not-attested fact whose source the user erased is refused, for post-version edges with a recorded
  source.

**NOT claimed:**
- **that `not_attested` means inferred.** Most `not_attested` facts are true user statements in forms the grammar
  does not reach.
- **that `attested` is proof of what the speaker stated** (§4a: 1 / 67 on H2), or that it outranks a challenge.
- **any rate outside the project.** H1 and H2 are authored chat (H2 deliberately hard), and each pair of labellings
  is the same model family. A human labelling
  and naturally occurring text are owed before a rate is quoted elsewhere.
- **that query-time derivation is restricted** (§4b).
- **anything about episodes** (§4b).
- **contributor tracking** (§4d: one source per row).

---

## 9. Brief for the external reviewer — ROUND 3

## 9-bis. Round 4 (v1.9)

**Round 3 closed R2-01 and raised no independent 0045 blocker; joint acceptance waits for 0047.** v1.9 folds only
the bounded corrections and the owner's version-carrier ruling:

| round-3 item | v1.9 |
|---|---|
| narrow “no downstream privilege” | “no challenge-gate privilege” everywhere; §4a states the source-redacted guard's retained distinction |
| remove “It is safe” and any guarantee wording | §1b (H1's 0 / 66 is a fixture measurement); §7's “the speaker said it” replaced |
| a durable version carrier | `attv`, §2, §4a, §4e, §4f; INV-G13. ATTEST-3 itself is unchanged |
| §6's gate wording | MODEL and PREDICATE checks red at the design gate; PRODUCT tests at implementation |

**Round 3's brief, kept for the record.** The question that round asked: does v1.8 close R2-01, by a repaired
predicate measured on a fresh holdout AND the narrowing of `attested` to a label with no challenge-gate privilege?

| finding | closure | evidence |
|---|---|---|
| R2-01 | **ATTEST-3** (§4a): one supported construction (quotation removed before splitting, the trigger begins its sentence, the complete complement, generic triggers bound by a lexicon, an event-level retraction attests nothing). Every negative you listed, and 29 more of the same classes, stays non-attested; 8 mechanism mutants are killed. **Fresh blind holdout H2: 1 / 67 false attestations, 12 / 53 recall.** The one miss is a retraction outside the closed list, an open-ended class, so **the owner narrowed `attested` to a LABEL with no challenge-gate privilege** (§4a, §4c; 0047 v1.8 §4c, INV-R12) | the evidence set at `specs/evidence/0045/attest/`: the frozen predicate, its development gate and mutants, H2, both labellings, the scorer and the raw result, and the README's account of their order |
| your G2 answer | accepted as you answered: the narrowed declared-direct boundary, the 0019 amendment's design accepted at round 2, and its v2.2 correction #4 (the diff travels in this package) | the 0019 amendment v2.2 |
| your G4 answer | the source-redacted guard stays 0045's contract, cross-referenced from the 0008 fold | §4d |

- **Least sure of:**
  1. Whether a label with no challenge-gate privilege is still worth its predicate. We think yes: it is what `why` and the
     structured returns show, and its false-attestation count fell from 5 to 1 on H2.
  2. ATTEST-3's recall (23% on H2), lower than ATTEST-2's (30%). Most genuine statements are stored `not_attested` and
     labelled, under “Label, don't block”.
- **What would change our minds:** a false-attestation rate on naturally occurring text materially above H2's bound,
  which would argue for withdrawing the label too.
- **What we are NOT asking:** label rather than block (ruled); an LLM judge (rejected, §1e).
- **Reviewer-safe copy:** nothing generalised. A human labelling and naturally occurring text are still owed before
  any rate is quoted outside the project.

**Joint acceptance (R1-10):** 0045 and 0047 cannot be accepted independently. This is now **machine-checked**, not
asserted in prose: each document's `Spec-Requires:` line names the other, and the gate refuses a tree in which one is
accepted without the other. *v1.4's “carried VERBATIM into README and PIN” sentence is withdrawn. The reviewer found
it was not verbatim, and the gate replaces it.*

---

## 10. Open questions

| # | question | who decides | by when | class |
|---|---|---|---|---|
| Q2 | Is a confirmation path intended? **RESOLVED 2026-10-10: yes**; 2026-10-11: it is `confirm()` on the stored edge | owner | — | resolved |
| G1 | The attestation test (R1-01, R2-01). **CLOSED at round 3** (the reviewer: closed by ATTEST-3 and the owner's narrowing of `attested` to a label with no challenge-gate privilege, §4a) | external reviewer | — | resolved |
| G2 | Non-user events (R1-01's G2). **ANSWERED: refuse when flagged, label `not_attested` otherwise** | external reviewer | round 2 | blocking |
| G3 | No inline marker on `not_attested` (§9 (1)) | external reviewer | round 2 | non-blocking |
| G4 | Source-redacted refusal: this spec's, or an 0008 amendment (§9 (2)) — dev: this spec's (0008 has no closed refusal list) | external reviewer + dev | round 2 | blocking |
| G5 | Is the absent-context floor non-USER-effective (§3)? **RESOLVED 2026-10-11 by the owner: “Only declared-direct calls”** (reading (A)): yes — undeclared callers (the Python default, MCP capability NONE) earn no `attested`; their unrecognised statements are stored `not_attested`; their flagged triples are refused (they were `use_only`, never assertable) | owner | — | resolved |

---

## Reviewer checklist

- [ ] §3 has no unanswered cells
- [ ] §3's classes were read from the enums, not copied from the template
- [ ] Prohibitions AND the corresponding **permissions** are both tested
- [ ] Every default fails **closed**
- [ ] §2c has a row per uncontrolled input, and **no empty invariant cell**
- [ ] §2c-ii: every claim about what is reachable carries **the command**
- [ ] Every §6 invariant has a check that actually runs, demonstrated RED against its mutant
- [ ] §10 questions each carry a class
- [ ] §8 states what this does *not* establish
- [ ] I have said where I think the **author's conclusion is wrong**, not only where the text is wrong
- [ ] I re-read the current version before reviewing, and I am quoting the version I approve
