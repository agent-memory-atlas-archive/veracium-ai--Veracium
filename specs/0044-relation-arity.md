# Feature spec: relation arity — a functional relation is ONE SLOT PER SUBJECT, and three of ours should not be

Spec-Status: draft
Spec-Requires: 0003[0044/0003-contested-order], 0018[0044/0018-data-migration], 0029[0044/0029-reinstated-reason], 0008[0047/0008-request-registry]

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.1 2026-09-20 from `0044-relation-arity-CANDIDATE.md` (sha16 3f9f9db8ea92cc0a); v1.2 2026-10-10 from `0044-relation-arity-CANDIDATE.md` (sha16 72cd614748837a31); v1.3 2026-10-11 from `0044-relation-arity-CANDIDATE.md` (sha16 3741b0c83f8bde59); v1.4 2026-10-12 from `0044-relation-arity-CANDIDATE.md` (sha16 5b268c4400197810); v1.5 2026-10-13 from `0044-relation-arity-CANDIDATE.md` (sha16 e409e03da96f6721) |
| **Version** | **v1.5 — 2026-10-13, round-4 fold (re-issued the same day after reference model I was encoded against it: §4l compares the lifecycle STAGE, never `undone_at`'s value, and two different endings refuse; the edge's removal ends an episode, defensively; `refusal_inventory` is named and erased; an equivalent mutant is dropped from INV-A22): round 3 returned v1.4 and the 0018 amendment for bounded corrections, approved the 0003 amendment's design, and retained the 0029 amendment's acceptance.** **R3-01** (a same-id upsert bypassed the lifetime hooks): new §4f-ii. Every lifetime transition is derived ONCE, at 0029's emission choke point, from the persisted prior and new row, before its unchanged-bytes return. In the implementation change after acceptance (`src/` is unchanged at this pin), `EDGE_WRITE_SITE_RULINGS` gains a `lifetime` disposition per site, and its two false “SOLE” rulings are corrected. The import's same-id write agrees with 0009. `add_edge` is unchanged; backend conformance is one sentence on `Store.add_edge` (the owner, 2026-10-13). §4i's statement that a redaction does not pass the choke point is corrected: it does. **R3-02** (held outcome identity was not exact replay), §4l: the outcome's canonical projection, one outcome per `(plan_id, edge_id)` slot, replay decided by comparison, the store-local `undo_request_ref` excluded, and an ended episode never revived (the owner). One admission rule: an outcome's edge must be IN the unit. **R3-03** is the reference model's and the 0018 amendment's (§6's rows follow it). **Bounded corrections:** the 0008 amendment is cited by its §6e–§6g, and 0029 v12 is cited as folded, no longer travelling. §4i's replay yields to the terminal `request_redacted`. INV-A22 and A23 are new; A12 and A19 gain the upsert mutants. §9 is the round-4 brief. Prior: **v1.4 — 2026-10-12, round-3 fold: round 2 returned for amendment (R2-01, R2-02, R2-04..R2-08 on this document).** Done here: **the owner's 2026-10-12T22:56Z rulings**: Q8 ADOPTED as the reviewer answered, with its three retention cases (§4d); the release text says “no longer supersede incomparable values” in place of “now keep every value” (§8); `Spec-Requires` gains the 0008 amendment, which hosts both shared constructions. **R2-02** in part: a plan HEADER persists the plan's identity and input digest even when its relation set is empty, so uninitialized, initialized-empty and initialized-nonempty are three states (§4e); a pre-arity file imported before any plan exists is REFUSED, naming the 0018 amendment's new PLAN-ONLY mode as the prerequisite (§4l; Q9, the owner, 2026-10-12T23:03Z). The verdict's correction: “new refusals are not created under `multi`” is narrowed to the ordinary supersession path (§4d). **Part 2, on the 0008 amendment's constructions (v2, coordination a8a499a; research's stage-1 read 454a6139):** **R2-01**: eligibility is membership of the schema step's retirement INVENTORY with the retirement unchanged, ended terminally by a reinstatement; no clock is compared (§4f; §4d reads the refusal inventory). **R2-04**: `applicable` is the restoration episode's flag, cleared terminally by any retirement, a redaction or erasure; undo is the registry verb `undo`, sharing ids with `confirm` and `reply` both ways and replaying before it reads the edge (§4i). **R2-05**: outcomes travel under the 0008 amendment's origin matrix, proof vs testimony, never upgraded, with whole-unit validation; no undo from testimony (§4i, §4k, §4l). **R2-06**: 0009's collision rule kept; the only new skip is conversion of an already-admitted row (§4l). **R2-07**: erasure removes every row this feature records, and replay and once-per-plan end there (§4g-ii). §6 gains INV-A19..A21 and revised A6, A12, A13, A16 and A17. **Part 3, R2-08:** §6 states the package's one model/product gate. `specs/evidence/0044/obligations.py` derives the obligation map (the review manifest) from §6, and dev's model I v2 kills every claimed mutant semantically. R2-03 is the 0018 amendment's §4c. §9 is the round-3 brief. Prior: **v1.3 — 2026-10-11: round 1 returned for amendment (R1-01..R1-10); this version is STAGE 1, the accumulation stage, on the owner's ruling (A), “defer keys”** (2026-10-11, first-hand in the dev session, relayed by dev). `single` and `multi` are operational; `keyed` is a reserved word that a registry may not yet declare; `measures`, `prefers` and `health_state` become `multi`; operational keys are a later round, carrying the reviewer's warning that a deterministic rule over a model-chosen object is not a trusted key source. **The restoration of values already retired is rebuilt** to answer R1-01 (standing revocation), R1-03 (completion, restart and receipt — through a companion AMENDMENT TO 0018, a separate host operation), R1-04 (truthful successor evidence), R1-05 (durable operation identity, not “the latest event”), and R1-06 (a persisted plan from the host's effective registry). **The owner made the restoration OPTIONAL, with a warning** (2026-10-11): §4h states the cost. **The authors' P-1..P-8** (the round's addendum, credited by the reviewer as author-disclosed) are folded where each belongs. **Q6 is answered: KEEP the successor's pointer** (the reviewer's recommendation, conditional on R1-04/R1-05, both now met). Every rule in §4 was model-checked before this text: dev's reference model (pure Python, `specs/evidence/0044/` when landed) — every invariant holds on research's rule set and every mechanism mutant is killed by the invariant that names it (the counts are the model's run result in the package, not restated: they moved as the amendments' invariants joined). Prior: v1.2 · v1.1 · v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — round 4. Round 1: `0044-round1-review-package` (sha256 262e8037…), RETURN FOR AMENDMENT, ten findings. Round 2: RETURN FOR AMENDMENT, nine findings. Round 3: RETURN FOR BOUNDED CORRECTIONS (R3-01..R3-03), the 0003 amendment's design APPROVED. |
| **Decision + date** | (A) defer keys: the owner, 2026-10-11. Restoration of the superset with a receipt: the owner, 2026-10-10. Restoration optional with a warning: the owner, 2026-10-11. Acceptance: pending round 2. |
| **Path** | **full** |
| **Number** | 0044 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | none. Occasioned by `TRACK-B-RENDER-PATH-RESULT.md` §5–6 (fix **B**, *“stop treating multi-valued attributes as functional”*, recorded there as *“the real modelling question and the owner's”*). **Travels with** the 0003 contested-order amendment in one review package (the owner's grouping, 2026-09-19: the two share the contested-render surface a reviewer needs whole) |
| **Requires** | **Machine-checked by the `Spec-Requires:` line above** (R1-10; the gate binds by CONTENT — each id must appear on the prerequisite's `Folds:` line, which its fold writes in the same commit as the folded text; the owner, 2026-10-11, "Bind by content"). Two of its own amendments travel in this package, `0044/0003-contested-order` and `0044/0018-data-migration`. **`0044/0029-reinstated-reason` no longer travels**: it was accepted at round 2 and is folded into 0029 v12 at the pin, whose `Folds:` line carries its id (v1.5: the round-3 reviewer's stale-text correction). **From round 3, 0044 also requires package II's 0008 amendment (`0047/0008-request-registry`)**, which hosts the two constructions both packages use, the operation order and the import identity with its request registry (the owner, 2026-10-12T22:56Z). Package I carries that amendment at the SAME digest as package II, and 0044's acceptance waits on its acceptance. The folded 0003 carries `Spec-Requires: 0044` in return, so the two flip together. |

---

## 1. Problem and motivation

### 1a. The defect, reproduced — with a control that separates

**The supersession scope is `(user, subject, relation)`** (`graph._build_supersession_plan`'s scope read), and for a
relation flagged `functional` **any differing object retires the prior**. So `functional` means **one slot per
subject**, not one slot per quantity, per topic or per condition.

Driving the supersession path the ingest path applies (`graph.apply_supersession`) with two differing values under
one `(subject, relation)`, then reading the active set (§2c-ii row 1):

| relation | `functional` | active after the second value |
|---|---|---|
| **`prefers`** | `True` | only the second — *“oat milk”* retired by *“window seats”* |
| **`health_state`** | `True` | only the second — *“asthma”* retired by *“iron deficiency”* |
| **`measures`** | `True` | only the second — *“weight 78 kg”* retired by *“savings 4200”* |
| 🔴 **`uses_tool`** *(the control)* | **`False`** | **both** |

🔴 **`measures`' own gloss names three different quantities — “weight, reading progress, savings balance” — and then
files them in ONE slot.**

**“Retired” means:** the prior row is KEPT — `invalidated_at` set, `invalidation_reason = 'superseded'` — and leaves
every active read. *The agent stops “knowing” a person's asthma the moment a second condition is mentioned, and nothing
tells anyone.*

> **Method note.** A probe through the raw `Store.add_edge` writer shows both rows ACTIVE — the raw writer applies no
> supersession. The table above drives the supersession path itself.

**A figure removed rather than caveated (v1.1, A7):** v1 carried a share figure from a store that no longer exists;
it is not restated. The owner's 2026-10-10 answer that store statistics may travel does not make it re-derivable.

### 1b. What the boolean carries, and why stage 1 accepts accumulation

`functional` answers two questions with one bit: *does a new value REPLACE an old one?* and *what is the slot?* For
`prefers`, `measures`, `health_state` the slot is the topic, the quantity, the condition — not the subject.

**v1.1 and v1.2 called “flip the flag to non-functional” the narrow dodge** and proposed `keyed` arity. Round 1 found
that `keyed` had no key carrier and that slot identity stopped at the supersession branch (R1-02); the reviewer judged
that *“a clearly described accumulation stage is defensible”* rather than *“preserv[ing] known cross-quantity
retirement simply to keep some update behavior.”* **The owner chose (A): this version ships the accumulation stage,
and keys are a later round.** The cost is stated where it lands (§4c): no latest-value semantics for `measures`.

### 1c. Alternatives rejected

- **Keep the three relations `single`** — retains the reproduced defect (§1a) to keep update behaviour; the reviewer
  and the owner rejected it.
- **Specify the key carrier now** ((B)) — the owner chose (A); no host supplies keys today.
- **Split `measures` into per-quantity relations** — workable for a small closed set; does not solve open-ended
  preferences or conditions. Remains a stage-2 alternative.
- **Leave already-retired values retired** — not chosen: the owner chose restoration with a receipt (2026-10-10).
- **Reinstate silently** — rejected: it changes what the agent says about a person with no record of why.
- **Clear the successor's `supersedes` pointer at restoration** — rejected (Q6, the reviewer's recommendation): for
  every correctly replaced pair the pointer is a true record of a storage transition.
- **Select restorable rows by relation name** — rejected (R1-06): a host's custom `single` declaration of the same name
  would be restored against its intent; §4e's plan replaces it.

---

## 2. Field contracts touched

**Consumers enumerated FROM THE SITES, not only by a grep for `functional`** (round 1: a grep finds readers, never a
consumer that forgot the field). The `functional` textual census (§2c-ii row 6, nine lines) is the compatibility
census; the slot census adds the sites that group or combine by `(subject, relation)` without reading the flag.

| field / site | read / written | contract | stage-1 change |
|---|---|---|---|
| `Relation.arity` *(new)* | read by every consumer below | `single` · `multi` (operational) · `keyed` (reserved) | new; **a registry declaring `keyed` is REFUSED at validation** |
| `Relation.functional` (`schema.py`) | compatibility | *“one current value per subject”* | **derived** (`single ⇒ True`); a registry declaring both and disagreeing is refused |
| `registry.FrozenRel` construction (`registry.py` L74 host relations, L78 reserved relations) | snapshot | carries `functional` | **both sites carry `arity`** |
| supersession planner (`graph.py` L548) | reads | a differing value under a functional relation retires the prior | unchanged for `single`; `multi` never supersedes (as today) |
| reinforcement and absorption (`graph.py` L436–L460, before the functional branch) | write | same-or-subsuming values reinforce or absorb within `(user, subject, relation)` | **unchanged** — as for every `multi` relation today (§4b, INV-A2 narrowed) |
| contention ordering (`graph.py` L658), recall contested groups (`__init__.py` L1413), wiki compile's refusal exclusion (`compile.py` L116) | read | group or exclude refusal pairs of a functional relation | **`multi` forms no new groups; refusals recorded while the relation was `single` KEEP their protection (§4d)** |
| recall variants tier (`__init__.py` L1507) | reads | groups by `(subject, relation)` | unchanged under stage 1 (no keys); **stage 2 must group by slot** (P-2) |
| wiki value groups (`compile.py`, the `_value_groups` construction) | reads | one survivor per incomparable value | unchanged; the render consequence is §4c |
| `compile._policy_digest` (`compile.py` L79–80) | reads | binds the functional names | binds arity; **one recompilation per affected cached user view, generally on a later read** (not once per store) |
| `Edge.invalidated_at`, `invalidation_reason` | written by restoration and undo (§4f, §4i) | `superseded` = retired by a later value in the slot | cleared on restoration; restored per field on undo |
| journal `reinstated` event (`_journal_edge_write`) | written | reason non-NULL iff `invalidated`/`redacted` (0029) | **0029 v12 (the folded amendment, §4j):** `reinstated` carries a closed reason |
| `doctor`'s `refs` rule (`doctor.py` L294–L310) | reads | an active predecessor of an active successor warns (exit 1) | **downgraded to `info` for a restoration recorded in `migration_outcome`** (§4k) |
| `migration_run`, `migration_outcome`, `reclassification_plan` *(new tables)* | written by the 0018 amendment's operation | — | §4e–§4i |
| portability (`portability.py`) | export / import | reproduces superseded history exactly | **exports `migration_outcome` rows for exported edges; import-time conversion for pre-arity files** (§4l) |

**Documentation that states the old meaning and changes with it:** the `functional` comment in `schema.py` (L457),
`graph.py`'s module docstring, and `_policy_digest`'s docstring.

---

## 2c. Untrusted inputs — REQUIRED, blocking

| uncontrolled input | empty | malformed | unrecognised | adversarial | **invariant** |
|---|---|---|---|---|---|
| **extractor output** — relation and object from `remember`'s text | no edge | the extractor's refusal | unclassified route | a model-chosen object cannot retire a stored value under a `multi` relation; under `single`, 0003's authority gate is unchanged | **INV-A1**, **INV-A2** |
| **host registry** (`arity`, `functional`) | absent `arity` → derived from `functional` | an `arity` outside the set → refused | **`keyed` → refused** | `functional=True` with `arity=multi` → refused | **INV-A4**, **INV-A10** |
| **the registry passed to the restoration** (0018 amendment) | refused | refused by 0025's validator | — | a later call with different declarations for the three relations → `registry-changed`, nothing changed | **INV-A15** |
| **data written by an older version** — rows retired as `superseded` | the plan selects none | an unparseable row aborts that user's transaction | a redacted row (its `relation` is the marker) is never considered | **a row whose source is under standing revocation is never restored** | **INV-A7**, **INV-A11** |
| **an import file** | — | the existing import refusals | — | a pre-arity file's retired rows are converted (refused while the plan is uninitialized); a held id keeps 0009's rule (equal → skipped, differing → the whole import refused); a newer file's unexplained retirement is never reinstated by guess; default-import testimony gives no `doctor` exemption and no undo, on every hop | **INV-A16**, **INV-A17**, **INV-A21** |
| **the undo request** (`edge_id`, `correlation_id`) | refused | refused | an edge the restoration did not restore → refused | the same id for a different edge or verb → refused (0008's rule) | **INV-A12**, **INV-A13** |
| CLI / environment / network | n/a | | | | |

### 2c-ii. Assertions about reach — REQUIRED

Commands run from the repository root at `1054cc4`, with a Python carrying the package's dependencies (research,
CPython 3.14.7, 2026-10-11). The three probe scripts are research's, to be landed beside dev's model under
`specs/evidence/0044/probes/`. **EXECUTED** = run and read; **READ** = the cited lines.

| # | assertion | command | result |
|---|---|---|---|
| 1 | a second value under `prefers` / `health_state` / `measures` retires the first; `uses_tool` keeps both | `PYTHONPATH=src python -c "from veracium.graph import apply_supersession as ap; from veracium.schema import DEFAULT_RELATIONS as R, Edge, Provenance, EvidenceAuthor as A, Disclosure as D; from veracium.store.sqlite import SqliteStore as S; E=lambda i,r,o: Edge(id=i,user_id=\"u\",subject=\"user\",relation=r,object=o,provenance=Provenance(author_of_evidence=A.USER,evidence_ref=\"ev\",disclosure=D.MENTIONABLE)); run=lambda r,a,b:(s:=S(\":memory:\"),s.add_edge(E(\"p\",r,a)),ap(s,E(\"i\",r,b),R),s.add_edge(E(\"i\",r,b)),sorted(x.object for x in s.edges(\"u\")))[-1]; [print(r, run(r,a,b)) for r,a,b in ((\"prefers\",\"oat milk\",\"window seats\"),(\"health_state\",\"asthma\",\"iron deficiency\"),(\"measures\",\"weight 78 kg\",\"savings 4200\"),(\"uses_tool\",\"Notion\",\"Figma\"))]"` | EXECUTED: `prefers ['window seats']` · `health_state ['iron deficiency']` · `measures ['savings 4200']` · `uses_tool ['Figma', 'Notion']` |
| 2 | `Relation` has no key field and `remember` takes none | `PYTHONPATH=src python -c "import inspect; from veracium.schema import Relation; from veracium import Memory; print(list(Relation.model_fields)); print(list(inspect.signature(Memory.remember).parameters))"` | EXECUTED: `['name', 'functional', 'desc', 'relation_kind']` · no key parameter |
| 3 | revoking a source leaves an ALREADY-retired row's reason `superseded` (R1-01) | `PYTHONPATH=src python specs/evidence/0044/probes/revocation_keeps_superseded.py` | EXECUTED: `after revoking feed-A, the retired prior's reason: superseded` |
| 4 | a non-functional `measures` still absorbs `80` into `weight 80` (R1-02) | `PYTHONPATH=src python specs/evidence/0044/probes/multi_still_absorbs.py` | EXECUTED: `{'80': 'absorbed_duplicate', 'weight 80': None}` |
| 5 | reinstatement widens the past valid-time window (P-6) | `PYTHONPATH=src python specs/evidence/0044/probes/asof_past_window.py` | EXECUTED: control — the retired window shows only `window seats`; reinstated — the same window shows both |
| 6 | nine lines in `src/` read `.functional` | `grep -rn --include="*.py" -e "\.functional\b" src/` | READ: 9 lines; `registry.py` L74 and L78 are the two `FrozenRel` construction sites |
| 7 | `supersedes` is a single field (R1-04) | `PYTHONPATH=src python -c "from veracium.schema import Edge; print(Edge.model_fields['supersedes'].annotation)"` | EXECUTED: `str` or `None` |
| 8 | the journal is not exported (P-5) | `grep -ci -e edge_events -e journal src/veracium/portability.py` | EXECUTED: `0` |
| 9 | `doctor` exits 1 on a warning | `grep -n "return 1 if any(f.level in (\"error\", \"warn\")" src/veracium/doctor.py` | READ: L142 |
| 10 | the variants tier groups by subject and relation (P-2) | `grep -n "g = (e.subject, e.relation)" src/veracium/__init__.py` | READ: L1507 |

---

## 3. Trust-class matrix — REQUIRED, blocking

Classes from the enums at `1054cc4`: `EvidenceAuthor` = user, third_party, system, assistant; `Disclosure` =
mentionable, use_only, quarantined.

### 3a. Supersession — directional, stage 1

**Stage 1 changes which relations supersede, never the authority rule.** For a `single` relation every cell is 0003's
matrix, unchanged. For a `multi` relation:

| | prior=A, incoming=B | prior=B, incoming=A | same class | involving quarantined | involving `use_only` |
|---|---|---|---|---|---|
| **differing value** | no candidate — both stand | no candidate | no candidate | no candidate | no candidate |
| **same-or-subsuming value** | reinforcement / absorption as today (0012, 0014) | as today | as today | as today | as today |

### 3b-i. The restoration — a state transition over a planned set

| row's author | mentionable | use_only | quarantined |
|---|---|---|---|
| any, source NOT under standing revocation | restored; provenance, disclosure, confidence unchanged | same | **restored and still quarantined** |
| any, source under standing revocation (direct or contribution-derived) | **withheld (`withheld_revoked`)** | same | same |
| any, redacted | **never considered** (its `relation` is the marker) | same | same |

- *User-asserted fact made non-assertable?* No — supersession can only retire LESS; restoration only reinstates.
- *Non-user content gains user-grade authority?* No — each row keeps its own stamp.
- 🔴 *A correctly replaced value made current again?* **Yes, by the owner's decision** — the receipt names it; §4i
  re-retires it.
- *`needs_confirmation`, provenance merge?* Untouched.

## 3b. Authorization and scope — *full specs only*

- No user, tenant or scope boundary is crossed; every operation acts on one user's rows.
- **The restoration** is the 0018 amendment's host operation: a store path, 0018's quiescence attestation (for its
  backup reference — the only whole-store undo for a superset restoration), and the host's registry. Not MCP.
- **The undo verb** is host-only, per row. Not MCP (as `dispute()` is not).
- **The receipt read** returns one user's outcomes.
- **Nothing becomes visible to a principal who could not see it before:** a restored row returns to the same user's
  surfaces, under its own disclosure.

---

## 4. Behaviour

### 4a. Arity in stage 1

| arity | stage-1 status |
|---|---|
| `single` | one value per `(user, subject, relation)`; a differing value supersedes, under 0003's authority gate |
| `multi` | a differing value never supersedes |
| `keyed` | **reserved word; a registry declaring it is refused.** Defined by a later round |

`functional=True ≡ single`, `functional=False ≡ multi`: every host registry valid today keeps its meaning.

### 4b. The reclassification, and what `multi` does and does not do

`measures`, `prefers`, `health_state` → `multi`. Every other default unchanged (`works_as`, `located_at`, `deadline`,
`scope` stay `single`).

**A differing value never supersedes. Reinforcement and absorption are unchanged** (R1-02, INV-A2 narrowed): a
same-or-subsuming value reinforces or absorbs within the `(user, subject, relation)` scope, exactly as for every
`multi` relation today (`80` then `weight 80` → `absorbed_duplicate`, §2c-ii row 4). *Absorption requires one value
key to subsume the other, so unrelated quantities (`weight 78 kg`, `savings 4200`) never merge. Residual, stated: a bare
less-specific reading can be absorbed by a more specific one of a different quantity whose text contains it — today's
`multi` behaviour, not new.*

### 4c. 🔴 The render consequence (P-1, in the reviewer's terms)

Incomparable readings remain eligible as **simultaneous current facts** in compiler input and recall; ordinary
visibility, trust and budget limits still apply; a generative wiki is not guaranteed to print every survivor. **There
are no latest-value semantics for `measures`** until a later round defines keys: “I weigh 78 kg” and “I weigh 80 kg”
are both current. *That is the cost of stage 1, and the reviewer and the owner accepted it over cross-quantity
retirement. It is not “strictly better” in every respect.*

### 4d. Historical refusal protection is RETAINED

A `supersession_refusals` row under one of the three relations that is **in the schema step's refusal inventory**
(§4f: the rows that existed when the v16 step's transaction committed, so recorded while the relation was `single`;
never decided from a timestamp) keeps its contested rendering and compiler exclusion. **The ordinary supersession path creates no new refusals under `multi`.** The separately
authorized correction planner can still record a refusal without reading relation arity: a refused correction does
not insert its replacement, and its record forms no new live `multi` group. *Stage 1 has no slot evidence to resolve
such a pair; it stays contested until an existing verb (correct, dispute, redaction) retires a member — no expiry*
(INV-A14).

**Retention (Q8, adopted as the reviewer answered; the owner, 2026-10-12):** a historical refusal is kept while its
members still satisfy the live-contention predicate, never removed because time passed or because restoration is
optional. *No expiry* is the refusal's policy; it does not prohibit any existing operation on its members.
- **Before any plan exists** (uninitialized, §4e): retained. The protection is keyed to the schema step's era, not to
  the plan, so a host that never runs the optional operation keeps it.
- **After a completed EMPTY plan** (the host kept its own `single` declaration for the relation): the relation is
  still `single`, so its refusals, old and new, are ordinary live refusals under the existing rule. None is
  historical.
- **After a later lifecycle transition:** an authorized correction, dispute, redaction or other ruled transition that
  retires a member ends the live pair, and the refusal's protection ends with it. That is the existing resolution
  path, not a new expiry. *Without this, existing disagreements such as USER
`weight 78` / SYSTEM `weight 80` would lose their deterministic read-side protection (the reviewer's non-blocking
note).*

### 4e. The reclassification plan (R1-06)

A persisted store-level record, written by the 0018 amendment's operation **from the effective registry the host
passes to it**: `plan(plan_id, relation, from='single', to='multi', effective_at, registry_digest)`. `effective_at` is
the v16 schema step's commit time. **A relation enters the plan only if its effective declaration is canonically the
default** — a host that keeps its own `single` declaration for one of these names gets no plan row for it, and its
supersessions stay. *Unknown history, stated:* the registry is host configuration and is not stored, so a host that
used a custom `single` declaration in the past and the default today is indistinguishable from one that always used
the default. The plan is fixed at its first write; later different declarations are refused (`registry-changed`).

**The plan HEADER (R2-02).** The plan's identity is a single header row, `plan_header(plan_id, effective_at,
registry_digest, op_id)` (the operation that wrote it, R2-03), written in the SAME transaction as the plan's relation rows, **including when the
relation set is empty**. A host whose own `single` declarations keep all three relations gets a header with no
relation rows, which records that decision. That gives three durable states:

| state | stored | meaning |
|---|---|---|
| **uninitialized** | no header | the operation has never planned |
| **initialized-empty** | a header, no relation rows | planned; nothing reclassified, so nothing to restore |
| **initialized-nonempty** | a header and ≥1 relation row | planned; restoration applies to those relations |

**Admission:** the plan phase runs in ONE write transaction. Exactly one header can exist (a uniqueness constraint,
so a second insert fails closed even outside the lock). A call that finds a header compares its own input digest:
equal continues with no plan write; different returns `registry-changed` and changes nothing. Two concurrent first
calls therefore produce one header; the second sees it and is admitted or refused by digest. The diagnostic for each
state, and the result carrier that reports a plan-only commit, are the 0018 amendment's (§4e there; R2-03).

### 4f. Eligibility (R1-01, R1-03; R2-01)

**The operation-era boundary is an INVENTORY, never a clock (R2-01).** The v16 schema step writes, in its own
transaction, `arity_inventory`: every retirement that is at that moment `superseded` under the three default relation
names, as `(edge_id, user_id, pre_invalidated_at, pre_reason)`. The same transaction inventories the
`supersession_refusals` rows that exist, as `refusal_inventory(refusal_id, user_id)` (§4d reads that list; v1.5
names its carrier). *The construction is this spec's (the construction note's §2d,
hosted here and in the 0018 amendment's step, not in the 0008 amendment).* The old-policy population is exactly the retirements committed before the step's
transaction, whatever their valid-time endpoints: `invalidated_at` holds the incoming statement's `valid_from` (`graph.py`'s supersession write),
a valid-time endpoint, not the retirement's commit, so no comparison of it with `effective_at` can say which rule
retired the row. *Both directions of that error are reproduced at the round-2 pin: a pre-upgrade retirement dated 2050
was excluded, and a post-upgrade one dated 1990 was admitted.* **A reinstatement of an inventoried edge ends its
membership terminally**, in the same transaction, at WHICHEVER write makes the row active again, so a later
re-retirement never matches, whatever its timestamp. *v1.5 (R3-01): the reinstate method is not the only such write;
`add_edge`'s same-id upsert is another. §4f-ii binds the transition to persisted state on every writer.* *Legacy history needs no policy: the inventory reads current row state, so a row retired before
the journal existed is inventoried like any other.*

A row `r` is **considered** iff its `relation` has a plan row, `invalidation_reason = 'superseded'`, it is a member of
`arity_inventory`, and its current retirement EQUALS the inventoried one (`invalidated_at`, `invalidation_reason`). A
considered row is evaluated **inside the user's write transaction**:

1. **Redacted** (its carriers hold the marker, or a redaction attestation names it): never considered. *Today a
   redacted row already fails the first test, because 0041 replaces `relation`; this guard is defence in depth.*
2. **Standing revocation:** if the revocation sweep's OWN predicate — the standing set and its contribution-derived
   basis, evaluated for `r` as if active — yields a `revoked_source` effect, the outcome is **`withheld_revoked`**.
   *One implementation: the sweep's.*
3. **Once per plan, ever:** if a `migration_outcome` row exists for (plan, `r`), `r` is not considered again. This
   holds independently of the inventory (INV-A9).
4. Otherwise **`restored`**: clear `invalidated_at` and `invalidation_reason` (0022's reinstate write), journal
   `reinstated` with reason `arity_reclassified` (§4j), and record the outcome with `applicable = true` (§4i).

*An imported row is never in the inventory. §4l's pre-format conversion has its own rule and does not consult it.*

### 4f-ii. Lifetime transitions are derived from persisted state, at one choke point (R3-01; the owner, 2026-10-13)

Membership's end (§4f) and `applicable`'s clearing (§4i) are LIFETIME TRANSITIONS of an edge row. Round 3 showed a
same-id `add_edge` upsert that reinstates and re-retires a row without passing the reinstate or invalidate method.
So a transition is never inferred from which method ran, nor from the journal event's kind (a changed same-id upsert
journals `mutated`). **It is derived once, at 0029's emission choke point, `_journal_edge_write`, from the persisted
prior row and the new row**, which every `edges` writer already passes it inside its own transaction. The
derivation runs BEFORE the choke point's return on unchanged bytes (an unchanged row is no transition):

| persisted prior | new row | transition | effect, in the same transaction |
|---|---|---|---|
| none | any (an insert, including a row ARRIVING already retired) | none: a new row is not a held row changing | nothing (an imported row is never inventoried, §4f) |
| retired | active | **reinstatement** | ends the row's `arity_inventory` membership, terminally |
| active | retired | **retirement** | clears `applicable` on the row's outcome, terminally |
| retired | retired with a different `(invalidated_at, invalidation_reason)` | **re-retirement** | as a retirement; and membership no longer matches (§4f's equality test) |
| any | redacted (the `redacted` write) | **redaction** | clears `applicable`, terminally |
| active | active, other fields changed | none | nothing: ordinary mutations (counters, confirmation, reinforcement) keep the flag |

**The writer set is the store's generated census, not a list here.** `EDGE_WRITE_SITE_RULINGS` names every function
that writes the `edges` table (eight at `1fd3e52`, user erasure included), and the existing coverage test refuses a
write site without a ruling. **In the implementation change, after acceptance** (`src/` is unchanged at this pin, as
the package states), each ruling gains a **`lifetime` disposition**: `choke-point` (its transitions are
derived as above) or `erasure` (`forget_user`, under the 0008 amendment's one erasure rule). The test refuses a site
without one. *Two rulings at the pin are false and are corrected in that implementation change: `_invalidate_edge_row` is not
“the SOLE active=0 writer”, and `_reinstate_edge_row` is not “the SOLE active=1-restoring writer”. The same-id upsert
writes both states. v1.4's “the store's only non-NULL `invalidated_at` write” rested on that unchecked word.*

**The import's same-id write agrees with 0009.** `commit_outcome_import_plan`'s same-id replace writes a held row only
as 0009 admits it: a record-equal row is skipped, a differing row refuses the whole import, and a valid notice
follows 0041 (a redaction, the table's fifth row). So an import never changes a held row's lifetime except by an
attested redaction.

**`add_edge` is unchanged** (the owner): no lifetime-changing same-id write is refused; its transitions are bound.
**Backend conformance:** in the same implementation change, `Store.add_edge`'s contract (`src/veracium/store/base.py`)
gains one sentence: a backend derives these
transitions from the persisted old and new row on every write that can change an edge's lifetime. At the pin
`SqliteStore` is the only backend.

### 4g. Outcomes and the receipt (R1-04)

`migration_outcome(plan_id, user_id, edge_id, outcome, pre_invalidated_at, pre_reason, successor_evidence, applicable,
origin, outcome_uid, undone_at, undo_request_ref)`, written in the same transaction as the restorations.
- `applicable` (R2-04) is true when written and is cleared TERMINALLY by the events §4i names.
- `origin` is `local`, `restored` or `imported`, under the 0008 amendment's origin matrix (§4l).
- `outcome_uid` is the portable identity `(origin_store, origin_user, plan_id, edge_ref)`, set when the row is written
  and carried unchanged on every hop (the 0008 amendment §6e, with its canonical encoding).
- `undo_request_ref` names the undo's row in the 0008 amendment's request registry (§4i). It replaces v1.3's digest
  and op-id columns. **It is store-local** (the registry is never exported, the 0008 amendment §6d), so it is not
  exported, an imported outcome carries NULL, and it is excluded from the outcome's comparison projection (§4l, v1.5).

- **Successor evidence:** `pointer:[ids]` = every row whose `supersedes` names `r` — zero, one or many — and `none`
  when there is none. *`supersedes` is a single field (§2c-ii row 7), so two retired restatements can have one
  successor between them; the evidence is never filled by matching quantity or time.* The receipt says “replaced by:
  unknown” for `none`.
- **The receipt is a view** over these rows (the 0018 amendment's `data_migration_receipt`): ids, outcomes,
  timestamps, successor ids; object text is read from the LIVE edge at read time (a redacted edge shows the marker).
  *No copy of memory content is stored in the receipt.* An absent edge renders `no longer held` from the outcome row
  alone, without reading the edge. *That is defensive: at the pin no public path removes one edge while its user is
  retained (§4g-ii).*

### 4g-ii. Erasure (R2-07)

**User erasure ends everything this feature recorded for the user.** `forget_user` deletes, atomically with the user's
records, the user's `migration_outcome`, `migration_run`, `arity_inventory` and `refusal_inventory` rows and their
request-registry rows,
all of which join `_ERASE_TABLES`. *The rule is the 0008 amendment's single erasure rule (its §6g), which both packages
cite.* They are user-linked metadata even though they store no object text.
- **Replay and once-per-plan end at erasure:** a retry after erasure is a new request.
- **A recreated user has no inventory rows,** so nothing is restorable for it. Nothing erased is recreated in order to
  replay an old operation.
- **An absent edge while the user is retained is unreachable at the pin.** At `e05e4e6` the only statement that
  deletes from `edges` is the per-user erasure loop (`sqlite.py:3053`, one of 15 `DELETE FROM` statements in `src`),
  and redaction keeps the row. A census test fails if any other `DELETE FROM edges` appears, which would reopen this
  case.

### 4h. The operation — the 0018 amendment (R1-03), OPTIONAL

The schema step v15 → v16 creates the feature's tables, stamps `effective_at` and writes the two inventories (§4f) in
its own transaction, changing no edge. The restoration is a
separate host operation, `run_data_migration(path, *, host_attestation, registry, op_id, plan_only=False)`: the plan once, then one
transaction per user, continuing past a failing user, idempotent on re-call, with the receipt recoverable at any time
after each user's commit. Its full contract, result table and failure boundaries are the 0018 amendment's.

🔴 **The owner made it optional (2026-10-11).** A v16 store opens normally. **Until the operation runs, the values
retired under the old rule stay hidden and no receipt exists; `doctor` warns and names the operation.** The owner
accepted that cost explicitly.

### 4i. Undo (R1-05, P-7; R2-04, R2-05)

`undo_restoration(user_id, edge_id, *, correlation_id=None)` — host-only.

1. **Replay first, from the request registry (R2-04).** Undo is a verb, `undo`, of the 0008 amendment's request
   registry. A `correlation_id` is unique per USER across EVERY verb of that registry (`confirm`, `reply`, `undo`), in
   both directions: an id held by `confirm` or `reply` is refused on `undo`, and an id held by `undo` is refused on
   `confirm` or `reply`. Same id + same request digest (operation, user, edge, plan) → the recorded result,
   **replayed from the registry's result reference (the outcome row) without reading the edge**. It therefore replays
   after the edge is retired or absent, and ends at user erasure (§4g-ii). **A redacted request returns the terminal
   `request_redacted`, which takes precedence over this replay** (the 0008 amendment §6g, v1.3): once the edge's
   redaction has replaced the undo's digest, its retained result reference never authorizes a replay. **Without an id**, a call on an already-undone row returns the
   recorded `already undone at T`.
2. **Eligibility:** the outcome is `restored`, not undone, **`applicable`**, of origin `local` or `restored`, and the
   edge is not redacted. It is compared and updated under the write lock.
   - **`applicable` belongs to this restoration EPISODE (R2-04).** It is cleared TERMINALLY, in the same transaction,
     by:
     - any retirement of the edge, by WHICHEVER writer (§4f-ii: derived at the emission choke point from the persisted
       prior and new row, so the invalidate method and a same-id upsert are treated alike);
     - a redaction of the edge (its `redacted` write passes the same choke point; v1.4 said it did not, which was
       wrong at the pin);
     - user erasure, which deletes the row;
     - defensively, any removal of the edge row while its outcome row is retained (§4g's absent-edge case, unreachable
       at the pin, §4g-ii). The removal ends the episode, so a later insert under the same id finds `applicable`
       already cleared. An insert is never a transition (§4f-ii), and it never needs to be one.
   - A later `reinstated` (a source lift) never sets it back. After restoration → revocation → lift, the edge is
     active again but the outcome is NOT applicable: no undo and no `doctor` exemption.
   - Ordinary mutations (outcome counters, confirmation, reinforcement) leave the flag set.
   - *Neither "the edge is active" nor "the latest journal event is `reinstated`" identifies the episode (R1-05,
     R2-04).*
   - **No undo from testimony (R2-05):** an `imported` outcome records what another store did, and this store cannot
     reverse it. Only the trusted-restore column ever promised undo. *The verdict asked the draft to rule this
     explicitly. It is a fail-closed design choice, given to the owner as a notice.*
3. **Per-field restore:** `invalidated_at := pre_invalidated_at`, `invalidation_reason := pre_reason`; every other
   field untouched. One transaction; a concurrent duplicate commits once and replays.

### 4j. The journal — 0029 v12 (the folded amendment `0044/0029-reinstated-reason`)

*The amendment this section carried was accepted at round 2 and is folded into 0029 v12 at the pin; it no longer
travels with this package. The rule, as folded:*

`reinstated` gains a reason from a CLOSED vocabulary — `source_restored` (0022's verb, updated to write it) and
`arity_reclassified` — refused outside it at the emission choke point. Events written before the amendment keep NULL,
read as `source_restored`. *The journal stays store-local (0029 V-INERT); it is diagnostic history, not the
restoration's evidence — `migration_outcome` is.*

### 4k. `doctor`

The `refs` warning for an active predecessor is **`info`** iff a `migration_outcome` row records it `restored`, not
undone and **`applicable`**, with origin `local` or `restored`: that is PROOF. An `imported` outcome is TESTIMONY, so
the warning stays and its text names the imported testimony (R2-05). Every other `doctor` check is unchanged. The
revocation check has nothing to report, because of §4f.2.

### 4l. Portability (P-4, P-5; R2-05, R2-06)

**Outcomes travel under the SAME origin matrix as acts (R2-05):** the 0008 amendment's §3 and §6d–§6e, one trust
model, not two.
- `local` (written by this store's operation) and `restored` (a trusted restore of this store's own history) are PROOF.
- `imported` is TESTIMONY.
- A trusted restore maps `local → restored`, and **never upgrades `imported`**.
- So the chain *migrate → export → default import → export → trusted restore* still reads `imported` at its end, and
  permits no undo (INV-A16′). *Round 2's model set the trust bit from the import MODE, which turned the warning into
  `info` on the second hop.*

**Edges and records keep 0009's collision rule (R2-06).**
- A record-equal row under a held id is skipped.
- A DIFFERING row under a held id refuses the whole import.
- A valid redaction notice for a held record follows 0041's rule.
- *Round 2's “an incoming id already held locally: SKIPPED” is withdrawn: it contradicted the accepted import
  boundary.*
- **The only new skip:** restoration CONVERSION never treats an already-admitted local row as a conversion target, and
  an import never replays a local undo. No general collision semantics change.

**The outcome's identity, projection and slot (v1.5, R3-02; the owner, 2026-10-13).** Round 3 showed model I
treating an equal `outcome_uid` as proof of replay: an outcome changed under its uid was skipped without comparison.
An outcome now gets the same construction as an act (the 0008 amendment §6e), over the same STAGED UNION
(destination ∪ unit, after remapping):

- **Canonical comparison projection:** `outcome_uid`; `plan_id`; the edge reference after user and id remapping;
  `outcome`; `pre_invalidated_at`; `pre_reason`; `successor_evidence` as remapped references; and the lifecycle
  STAGE, one of `live` (applicable, not undone), `ended` (not applicable, not undone: a retirement, a redaction or the
  edge's removal ended it) and `undone`. **Excluded:** the row id, the write time, the trust label (`origin`, the
  destination's own judgement, as for acts), `undo_request_ref` (store-local, never exported, §4g), and the VALUE of
  `undone_at`: it is the undoing store's own clock, so two stores that each undid the same episode compare equal by
  stage, never by time (v1.5, dev's model probe; comparing it would be R2-01's mixed-clock class).
- **Destination slot:** `(plan_id, destination edge_id)`. **One outcome per slot.** A second `outcome_uid` on a slot
  that is held, or two outcomes for one slot in one unit, **refuses the whole import**. No precedence between them is
  defined, and no undo lookup ever chooses between two.
- **Exact replay is decided by COMPARISON:** equal `outcome_uid` AND equal projections → a no-op. Equal uid,
  differing projection → **the whole import is refused**, atomically, naming the outcome.
- **An ended local episode is never revived.** The stage moves only from `live` to ONE of two endings, `ended` or
  `undone`, and the two endings are different histories, not stages of one. When the HELD row is `ended` or `undone`
  and the arriving row differs from it ONLY by being `live`, the arrival is older evidence of the same episode: an
  exact replay, a no-op, and the held stage is kept. An arrival never sets `applicable` back to true and never clears
  an undo. **Every other stage difference refuses the import:** an arriving ending over a held `live` row (the source's
  later history; 0009 usually refuses its edge first), and an `ended` arrival over an `undone` held row or the
  reverse (two different endings, v1.5: dev's model question). *The edge row is still judged by 0009's rule on its own: an older snapshot usually carries the edge in its
  earlier state, and a differing edge record refuses the import whatever the outcome rule says. This rule only stops an
  outcome from reviving the episode.*
- **Redaction of the outcome's edge** reaches the outcome only through `applicable` (§4f-ii). An incoming outcome whose
  edge arrives under a covering notice is compared after that treatment, as an act is (the 0008 amendment §6e).

**Whole-unit validation, before any write — ONE admission rule for outcomes (v1.5: §4l's “present in the unit or
already held” is withdrawn, so that this list and the matrix below say the same thing):**
- **every outcome's edge is IN THE UNIT** (an export always carries the outcome's edge); an outcome whose edge is held
  but not in the unit is refused, as the matrix's row “outcome rows for edges NOT in the file” says;
- every outcome's `outcome_uid` is unique in the unit, or its copies are equal (an exact replay of itself);
- the slot rule above holds over the staged union;
- the edge's state in the unit is consistent with the outcome: `restored` + `applicable` ⇒ the edge is active, and
  `undone` ⇒ the edge is retired with the recorded pre-state;
- a conflicting replay, an outcome with no edge in the unit, a remapped reference that does not resolve, or a slot
  collision → **the whole unit is refused**.

**Controls the round-3 verdict asked for, each owned by INV-A23:** unchanged replay in both import modes; remapping;
an ended episode (held not applicable, arriving applicable); a second hop; and the negative probe (one field changed
under the same uid, plus an unrelated new edge in the same import, which must refuse the whole unit).

| | default import | trusted restore |
|---|---|---|
| edges | capped (today) | as recorded |
| `migration_outcome` rows for edges IN the file | origin `imported` (testimony): no `doctor` exemption, no undo | origin `local → restored`, `imported` stays `imported`; exemption and undo only on an applicable `restored` row |
| outcome rows for edges NOT in the file | refused | refused |
| a file from a format BEFORE the arity version | **if the store's plan is uninitialized (§4e): REFUSED**, `requires-data-migration-plan`, naming the prerequisite: `run_data_migration(…, plan_only=True)`, which writes the plan and restores nothing, so restoration stays optional (R2-02; Q9, the owner). Otherwise **import-time conversion**: its retired rows under plan relations are run through §4f's steps (no inventory, no time test; an incoming row was retired under `single` by construction) under a new operation id, in the import's transaction, with a receipt. An initialized-EMPTY plan has no plan relations, so nothing converts, and the report says so | same |
| a file at or after the arity version, with a `superseded` row under a plan relation and no outcome row | kept retired; reported `unknown-linkage`; never reinstated by guess | same |
| an incoming record under an id already held locally | 0009's rule: record-equal → skipped; differing → **the whole import is refused**; a valid notice → 0041's rule (R2-06) | same |

*Conversion touches only incoming rows: it never rescans local rows and never reverses a local undo.*

### 4m. Valid time (P-6)

Restoration clears `invalidated_at`, so the restored row's valid-time interval widens, **including past dates**: an
as-of query for a moment inside the old retirement window now returns it (§2c-ii row 5). Local operational history
remains in the store's journal; ordinary export does not carry it. *Because the owner chose a superset restoration,
some widened intervals belong to values that were correctly replaced.*

---

## 5. Regime analysis — where does this behave differently?

| regime | behaviour |
|---|---|
| default extractor path | the three relations accumulate; all incomparable readings current (§4c) |
| host registry with no `multi` change | byte-identical to today, except `keyed` is refused |
| host keeping a custom `single` declaration for one of the names | no plan row; its supersessions stay |
| store upgraded, restoration never run | values stay hidden; `doctor` warns (§4h) |
| store upgraded, restoration run | restored per user; receipts recoverable |
| restoration, then undo, then re-run | the undone row is not re-restored (§4f.3) |
| a source revoked before the restoration | its rows are withheld (§4f.2) |
| import of a pre-arity export after the restoration | converted on import; local undo untouched (§4l) |
| multi-user store | one recompilation per affected cached user view, on a later read |

---

## 6. Invariants and executable checks — REQUIRED, blocking

**The gate, stated the same way in 0044, the 0003 amendment and the 0018 amendment (R2-08):** before design acceptance, a row is either a MODEL check or a stated PRODUCT obligation. A MODEL check runs in dev's reference model (`specs/evidence/0044/`): each claimed mutant REACHES its mutated path and is killed SEMANTICALLY, by an owning invariant that returns False. An exception is a harness failure, never a kill, and a mutant may have more than one killing invariant. Which kind each row is is not restated here: `specs/evidence/0044/obligations.py` derives the map from this section, and refuses an unmapped row, a mapping to an invariant that owns no killed mutant, and a model invariant no row claims. It is also the package's review manifest. At the implementation gate, every row is in addition a named PRODUCT test, demonstrated red against its mutant. *The model also carries invariants of the amendments that travel with this spec (the 0003 amendment's ordering and 0029 v12's INV-J1–J3); its counts are its machine-readable run result in the package, not restated here.*

| | invariant | mechanism mutant that must fail |
|---|---|---|
| **INV-A1** | a `multi` relation never supersedes on a differing value | supersede under `multi` |
| **INV-A2** | under `multi`, reinforcement and absorption behave exactly as today, and only for same-or-subsuming values | absorb non-subsuming values |
| **INV-A3** | a registry declaring `keyed` is refused | accept it |
| **INV-A4** | every registry valid today keeps its meaning (`functional=True ≡ single`) | map `True` to `multi` |
| **INV-A5** | the plan admits only canonically default declarations | a name-only selector |
| **INV-A6** | historical refusals keep their protection after reclassification, read from the step's refusal inventory (§4d) | declassify them; decide by the refusal's timestamp (a backdated post-step refusal is retained) |
| **INV-A7** | a redacted row is never restored (both arms) | select by reason alone |
| **INV-A8** | the receipt names every considered row with honest successor evidence | a guessed successor; a single-pointer-only lookup |
| **INV-A9** | a row is considered once per plan, ever (re-import after undo) | selector-only completion |
| **INV-A10** | `functional` and `arity` cannot disagree | accept the disagreement |
| **INV-A11** | a row under standing revocation is never restored | omit the standing-set check |
| **INV-A12** | undo eligibility is the outcome row plus `applicable`, this restoration EPISODE's flag, cleared terminally by any retirement, a redaction or erasure (R2-04), by WHICHEVER writer (§4f-ii) | the current active bit alone (restoration → revoke → lift is then undoable); latest-event eligibility; clear the flag only on `superseded` retirements; keep it across a redaction; clear it only in the invalidate method (round 3's upsert re-retirement keeps it) |
| **INV-A13** | undo restores per field, replays by user-scoped id from the request registry BEFORE reading the edge, shares the namespace with `confirm` and `reply` in both directions, and is idempotent without an id (R2-04) | whole-snapshot undo; per-edge id scope; check only the new verb's table (run both ways); read the edge before the registry (a completed undo of an absent edge fails to replay) |
| **INV-A14** | retained refusals have no expiry | expire them |
| **INV-A15** | the plan is fixed at its first write | re-plan on each call |
| **INV-A16** | import converts only incoming pre-arity rows, keeps 0009's collision rule, never reverses a local undo (R2-06) | rescan local rows; overwrite on collision; skip every collision (a differing own-history restore must refuse) |
| **INV-A17** | `doctor`'s exemption and undo follow PROOF (`local`/`restored`, applicable); `imported` testimony is never upgraded, so migrate → export → default import → export → trusted restore still reads `imported` (R2-05) | journal-keyed exemption; default-import exemption; the trust bit set from the import mode; undo from testimony |
| **INV-A18** | `reinstated`'s reason is closed (0029 v12) | accept any reason |
| **INV-A19** | the operation-era boundary is the schema step's INVENTORY of retirements: a pre-upgrade retirement is eligible whatever its valid-time endpoint, a post-upgrade one never, however backdated (R2-01) | `invalidated_at < effective_at` (the shipped cutoff: the 2050-dated pre-upgrade and 1990-dated post-upgrade cells both fail it); match the inventory by edge id only; keep membership across a reinstatement (reinstate, then re-retire with an identical `invalidated_at` and reason); end membership only in the reinstate method (round 3's upsert reinstatement keeps it) |
| **INV-A20** | user erasure removes the user's outcomes, runs, inventory and registry rows atomically; replay and once-per-plan end there, and a recreated user restores nothing (R2-07) | keep the outcome rows after erasure; replay an erased request; a `DELETE FROM edges` outside the erasure loop (the census) |
| **INV-A22** | **(v1.5, R3-01)** every lifetime transition of an edge row is derived from its persisted prior and new state at the emission choke point, by every writer: round 3's sequence (create; upsert retired; upsert active; upsert the identical retirement) ends inventory membership at the reinstatement and clears `applicable` at the re-retirement; a row ARRIVING retired is not a transition; and, a PRODUCT obligation at the implementation gate, every `EDGE_WRITE_SITE_RULINGS` entry carries a `lifetime` disposition | hook only the invalidate and reinstate methods (the upsert sequence keeps membership and the flag); infer the transition from the journal kind (`mutated` hides it); treat an inactive insert as a retirement; a write site with no `lifetime` disposition (the coverage test) |
| **INV-A23** | **(v1.5, R3-02)** an outcome's replay is decided by comparing canonical projections over the staged union: equal → no-op; a changed field under the same uid → the whole import refused, even beside an unrelated new edge; one outcome per `(plan_id, edge_id)` slot (a second uid on a held slot, or two in one unit, refuses); `undo_request_ref` is not compared or exported; an ended local episode is never revived | equal `outcome_uid` alone admits (round 3's changed-outcome witness); replace the slot's row on a different uid; let an arriving applicable copy set `applicable` again; compare `undo_request_ref` (a second hop conflicts); compare `undone_at` by value (two stores that each undid the episode refuse); treat an `ended` arrival over an `undone` held row as an earlier stage (two endings, not one) |
| **INV-A21** | the plan has three durable states under one header: an empty plan is recorded, a later call is admitted or refused by digest, and a pre-arity import into an uninitialized store is refused, naming the plan-only mode (R2-02) | no header for an empty plan (a later default call re-plans); two headers from concurrent first calls; convert silently with no plan |

---

## 7. Failure modes and reversibility

- **Silent failure:** a host that never runs the restoration (§4h) — warned, not silent to the operator; silent to the
  user. The superset restoration's correctly replaced values — named in the receipt; re-retirable by §4i.
- **Reversible?** Per row by §4i; whole-store by the backup the 0018 amendment's attestation requires.
- **Partial failure:** per-user transactions; the 0018 amendment's `partial` names each failed user; a re-call
  retries exactly those.
- **Attack surface:** the undo verb is narrow by construction and host-only. Stage 1 removes a surface: text the model
  extracts can no longer retire a stored value under these three relations.

---

## 8. Claims and limits

**Claimed:** under `prefers`, `health_state` and `measures`, a later statement no longer retires an earlier,
different one; values retired that way can be restored — once per user, never against a standing revocation, with a
receipt that names each one and with a per-row undo — when the host runs the restoration.

**NOT claimed:**
- **latest-value semantics for `measures`** — every incomparable reading is current (§4c);
- **that the restoration restores only wrongly retired values** — it restores a superset, by the owner's decision;
- **that the restoration runs** — it is optional (§4h);
- **keyed behaviour** — reserved, refused, a later round;
- **that `works_as` is right** — retained as a separate question.

**Release text (the owner's costs, in substance):** *“`prefers`, `health_state` and `measures` no longer supersede incomparable values:
a second preference, condition or measurement no longer retires the first. One consequence: every measurement you
have recorded is treated as current. This upgrade does not restore values the old rule already retired; run
`run_data_migration` to restore them and get a receipt listing each one — some were correctly replaced, and the
receipt lets you re-retire those. Until you run it, those values stay hidden and `doctor` warns.”*

---

## 9. Brief for the external reviewer — ROUND 4

**The question this round asks: do v1.5 and the 0018 amendment v4 close R3-01 to R3-03, inside the finite-review
boundary you set? The 0003 amendment carries only the two text corrections you asked for before folding.**

| round-3 item | closure |
|---|---|
| R3-01: same-id upsert bypasses the lifetime hooks | §4f-ii: transitions derived from persisted prior and new state at the emission choke point that every writer calls; at implementation, the generated writer census gains a `lifetime` disposition and the two false SOLE rulings are corrected (`src/` is unchanged at this pin); import agrees with 0009; `Store.add_edge` conformance. INV-A22 (and A12, A19's new mutants) |
| R3-02: held outcome identity is not exact replay | §4l: canonical projection, one outcome per slot, comparison decides replay, `undo_request_ref` excluded, an ended episode never revived, one admission rule. INV-A23 |
| R3-03: the model map overstates four rows | the reference model and the 0018 amendment v4 (its §4b.2 digest scope and §4c's carrier, stated unambiguously); the undo-under-redaction row reads the 0008 amendment v1.3 §6g; the erasure row's refusal inventory is in the one erasure rule |
| bounded: stale cross-references, travelling-amendment wording | the 0008 amendment §6e–§6g; 0029 v12 folded |
| your writer-table request | §4f-ii's transition table, and `EDGE_WRITE_SITE_RULINGS` with its `lifetime` field as the per-writer table |

- **Least sure of:** treating a re-retirement with a changed tuple on an already retired row as a retirement (§4f-ii's
  fourth row). It changes nothing that is not already cleared, and we state it so the table is total.

**Round 3's brief, kept for the record.** The question that round asked: do v1.4 and its three amendments close R2-01
to R2-09 on the amended artifacts, with the two shared constructions this package now carries?

- **Round 2, finding by finding:**
  - R2-01 → §4f: eligibility is membership of the schema step's retirement inventory, and nothing compares a clock.
    INV-A19.
  - R2-02 → §4e: the plan header and its three states. §4l: a pre-arity import before planning is refused, naming the
    plan-only mode. The 0018 amendment §4b. INV-A21.
  - R2-03 → the 0018 amendment §4c: the total carrier, and recovery by `op_id`. I29.
  - R2-04 → §4i: the `applicable` episode flag, and undo as a registry verb, replaying before it reads the edge.
    INV-A12, A13.
  - R2-05 → §4i, §4k, §4l: proof vs testimony under one origin matrix, and no undo from testimony. INV-A17.
  - R2-06 → §4l: 0009's collision rule is kept. INV-A16.
  - R2-07 → §4g-ii: one erasure rule, and the census. INV-A20.
  - R2-08 → §6: the package's one model/product gate. The obligation map (`specs/evidence/0044/obligations.py`) is also the review
    manifest.
  - R2-09 → the 0003 amendment §2 and §4c.
  - The bounded corrections → §4d (refusals under `multi`); the 0003 and 0018 amendments' own briefs.
- **The two shared constructions are in package II's 0008 amendment** (`0047/0008-request-registry`), which this
  package carries at the SAME digest (the owner's hosting ruling). 0044 now requires it: `Spec-Requires`.
  - The operation order is NOT 0029's `txn`. That counter exists only for transactions that journal an edge event, so
    a store-wide act ordinal that is never reset stands beside it (the owner's rulings, recorded in the 0008
    amendment §6f). 0029's accepted surface (INV-J1–J3) is untouched.
  - The era boundary uses no ordinal at all: it is the schema step's inventory.
- **The owner's rulings since round 2:**
  - Q8 adopted as you answered (§4d).
  - QO4 adopted (the 0003 amendment §10).
  - The release text now reads “no longer supersede incomparable values”.
  - Q9: refuse a pre-arity import before planning, plus a plan-only mode.
  - The constructions are hosted in the 0008 amendment.
- **Least sure of:**
  1. §4f's terminal end of inventory membership at a reinstatement. Is any reinstatement path NOT at the reinstate
     choke point?
  2. §4i's set of terminal events for `applicable`: any retirement, a redaction, erasure. Is there a lifecycle event we
     have not named?
  3. §4l's mixed-era rule: a file whose outcomes do not all bind edges of the same unit is refused whole.
- **What we are NOT asking:** keys, the superset and optional restoration (the owner's, not reopened); the 0029
  amendment's design (accepted at round 2).
- **Reviewer-safe copy:** nothing generalised.

---

## 10. Open questions

| # | question | who decides | by when | class |
|---|---|---|---|---|
| Q6 | keep or clear the successor's pointer — **RESOLVED: keep** (round 1's recommendation; R1-04/R1-05 met) | — | — | resolved |
| Q5 | operational keys (stage 2) | owner + dev | a later round | deferred |
| Q7 | `works_as` | owner | — | deferred |
| Q8 | §9 (1): an expiry or resolution path for retained refusals — **RESOLVED 2026-10-12: no expiry; kept while live-contended**; an existing ruled transition that retires a member ends it (the round-2 reviewer's answer, adopted by the owner, 2026-10-12T22:56Z; §4d's three cases) | owner | — | resolved |
| Q9 | a pre-arity file imported before any plan exists: refuse, or plan atomically at import — **RESOLVED 2026-10-12: REFUSE** (`requires-data-migration-plan`), **and `run_data_migration` gains a PLAN-ONLY mode** (the plan under the host attestation, nothing restored), which the refusal names; restoration stays optional for importers (the owner, 2026-10-12T23:03Z, on dev's recommendation). Planning at import was rejected: it would fix the store-wide plan as a side effect of one import, without the attestation | owner | — | resolved |

---

## Reviewer checklist

- [ ] §3 has no unanswered cells, and is directional where the operation is
- [ ] §3's classes were read from the enums
- [ ] Prohibitions AND permissions are both tested
- [ ] Every default fails closed
- [ ] §2c has a row per uncontrolled input and no empty invariant cell
- [ ] §2c-ii: every reach claim carries its command
- [ ] §2 consumers were enumerated from the sites, not only by grep
- [ ] Every §6 invariant names its mutant, and the model kills it
- [ ] §10 questions each carry a class
- [ ] §8 states what this does not establish
- [ ] I have said where I think the author's conclusion is wrong, not only where the text is wrong
- [ ] I re-read the current version before reviewing, and I am quoting the version I approve
