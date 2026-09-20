# Feature spec: relation arity — a functional relation is ONE SLOT PER SUBJECT, and three of ours should not be

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.1 2026-09-20 from `0044-relation-arity-CANDIDATE.md` (sha16 3f9f9db8ea92cc0a) |
| **Version** | **v1.1 — DEV'S INTERNAL REVIEW FOLDED (A1–A7); no external round yet.** 🔴 **A1 was blocking and it was the worst kind: on the shipped extractor path there is NO KEY** — `remember` takes no structured key and `Relation` has no key field — **so every reclassified relation fell to §3a's fallback and ACCUMULATED, which is the outcome §2 names as “the narrow dodge” and rejects.** *v1 argued against flipping the flag and then delivered the flip through a fallback, which is worse than flipping it honestly because the argument conceals the outcome.* **New §3b states the shipped-path behaviour as a table, names the cost (`measures` loses its update semantics until a key exists), and INV-A3 is reworded: no key derived from text BY THE MODEL — a deterministic registry-declared rule IS admissible.** **§5 gains the three things v1 did not name:** the derivable set is a SUPERSET, the successor's `supersedes` pointer fails `doctor` after a reinstatement, and the journal kind and 0018's release obligations are owed. **§8 concedes 0025 IS touched and makes `functional` DERIVED from `arity`**, plus the policy-digest recompilation cost. 🔴 **And v1's unre-derivable share figure is REMOVED rather than caveated a third time — named here by what it measured, not by its value, because a withdrawal that prints the number leaves it liftable** — this project's rule for a figure nobody can re-derive, which v1 knew and did not apply to itself. Prior: v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — this changes **stored semantics**: which records a later statement RETIRES. A wrong answer silently deletes facts a user stated. |
| **Decision + date** | |
| **Path** | **full** |
| **Number** | 0044 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | none. Occasioned by `TRACK-B-RENDER-PATH-RESULT.md` §5–6 (fix **B**, *“stop treating multi-valued attributes as functional”*, recorded there as *“the real modelling question and the owner's”*). |

---

## 1. The defect, reproduced — with a control that separates

**The supersession scope is `(user, subject, relation)`** (`graph._build_supersession_plan`'s scope read), and for a
relation flagged `functional` **any differing object retires the prior**
(the `rel.functional` branch in the same function). So `functional` means **one slot per subject**, not one slot per
quantity, per topic or per condition.

Driving `graph._build_supersession_plan` — the planner the ingest path applies — with
two differing values under one `(subject, relation)`:

| relation | `functional` | the second value's plan |
|---|---|---|
| **`prefers`** | `True` | `supersedes='e0'`, `prior_invalidations=[('e0', …, 'superseded')]` |
| **`measures`** | `True` | `supersedes='e0'`, `prior_invalidations=[('e0', …, 'superseded')]` |
| **`health_state`** | `True` | `supersedes='e0'`, `prior_invalidations=[('e0', …, 'superseded')]` |
| 🔴 **`uses_tool`** *(the control)* | **`False`** | `supersedes=None`, `prior_invalidations=[]` |

**In words, on the shipped default vocabulary:**

- *“I prefer oat milk”* is **retired** by *“I prefer window seats”*.
- *“weight 78 kg”* is **retired** by *“savings balance 4200”*.
- *“asthma”* is **retired** by *“iron deficiency”*.

🔴 **`measures`' own gloss names three different quantities — “weight, reading
progress, savings balance” — and then files them in ONE slot.** *The documentation of
the relation contains the counter-example to its own arity.*

> **Method note, recorded because it nearly produced the opposite finding.** The first
> probe wrote through `Store.add_edge` and **both rows stayed `ACTIVE`** — the raw
> writer applies no supersession. *A probe that goes around the path under test reports
> the ABSENCE of the defect, in a form indistinguishable from a passing check.* The
> table above drives the planner itself.

🔴 **A FIGURE REMOVED RATHER THAN CAVEATED (dev's internal review, A7).** v1 carried
a figure for the share of active edges sitting under functional relations, twice
qualified: the store it was measured on no longer exists and nobody can re-derive it.
**The number is not restated here** — a removal notice that repeats the figure leaves it
liftable, which is the superseded claim travelling inside its own withdrawal. **This project's rule for a figure
nobody can check is to remove it, not to explain it** — and v1 qualified it twice instead
of applying the rule. *The defect stands on the planner probe above, which anyone can
re-run on a fixture they build themselves.*

## 2. What the boolean is actually carrying

`functional` is answering two questions with one bit:

| question | for `works_as`, `located_at` | for `prefers`, `measures`, `health_state` |
|---|---|---|
| **does a new value REPLACE an old one?** | yes | **yes** — a weight reading supersedes last month's |
| **what is the slot that replacement is keyed by?** | the subject | 🔴 **NOT the subject** — the quantity, the topic, the condition |

> **So “flip the flag to non-functional” is the narrow dodge and this spec rejects it.**
> A non-functional `measures` accumulates: *“I now weigh 80 kg”* would stop retiring
> 78 kg, and the relation whose whole purpose is *“the number updates, history is
> kept”* would keep every reading live at once. **The bug is not that these relations
> supersede. It is that they supersede across unrelated values.**

## 3. Proposal — arity is DECLARED, and it has three values

Replace the boolean with a declared arity on the `Relation` record:

| arity | meaning | slot key | shipped examples |
|---|---|---|---|
| **`single`** | one value per subject; a differing value supersedes | `(user, subject, relation)` | `works_as`, `located_at`, `deadline`, `scope` |
| **`multi`** | values accumulate; nothing supersedes | *(no slot)* | `uses_tool`, `has_pet`, `relative_of` |
| 🔴 **`keyed`** | one value **per declared key**; a differing value supersedes **within that key only** | `(user, subject, relation, key)` | **`measures`, `prefers`, `health_state`** |

**`functional=True` maps to `single` and `functional=False` to `multi`**, so every
host registry that exists today keeps its present meaning; `keyed` is the new capacity
and nothing acquires it by default except the three relations reclassified in §4.

### 3a. Where the key comes from — and where it must NOT come from

🔴 **The key is DECLARED, never inferred from the text by the model.** 0037 rejected
*“letting the extractor decide procedural-ness or basis from the text”* on the round's
ruling and on 0031's, and the same reasoning binds here: a slot key chosen by the model
is the model deciding which of a person's facts gets deleted.

**Two admissible sources, in this order:**

1. **A structured key the host supplies** with the edge (the host knows its own domain).
2. **A registry-declared key FIELD** — the relation declares that its key is, e.g., the
   first segment of a structured object — so the rule is readable in the vocabulary and
   is the same for every record under that relation.

**If neither is available for a given record, the relation behaves as `multi` for that
record: it accumulates.** *Accumulating is recoverable; superseding is not. An unkeyed
record must never fall back to the subject-wide slot, which is the present defect
exactly.*

### 3b. 🔴 ON THE SHIPPED PATH THERE IS NO KEY — and v1 did not say so

**Dev's internal review, A1, blocking, and it is right.** `Memory.remember` takes event
text and metadata and **no structured key**; `Relation` carries `name`, `functional`,
`desc`, `relation_kind` and **no key field**. So on the default extractor path BOTH
sources above are absent, every record under a reclassified relation is unkeyed, and
**`keyed` behaves as `multi`.**

> 🔴 **Which means that, on the default path, v1 SHIPPED THE THING §2 CALLS THE NARROW
> DODGE.** *A spec that argues against flipping the flag and then delivers the flip through
> a fallback is worse than one that flips it honestly, because the argument conceals the
> outcome.*

**So the v1 behaviour is stated, not implied:**

| | on the shipped extractor path | when a host supplies keys |
|---|---|---|
| `prefers`, `health_state` | **accumulate** — no value is retired by an unrelated one, and none supersedes | one current value **per topic / per condition** |
| `measures` | **accumulates** — 🔴 **and the update semantics are LOST until a key exists: “I now weigh 80” no longer retires 78** | one current value **per quantity**, which is the relation's stated purpose |

**That cost is real and it is the reason this spec is not finished at `multi`.** *Both are
strictly better than today — a weight reading no longer retires a job title — and neither
is the model the relation describes.*

#### What returns the update semantics, and the rule it forces

**A DECLARED, DETERMINISTIC REGISTRY RULE over the object, evaluated by the registry and
never by the model** — e.g. `measures` keys on the leading quantity term. **It is
derivation from TEXT, and that is admissible; derivation by the MODEL is not.** So:

> 🔴 **INV-A3 is reworded, because v1's wording would have forbidden the only workable
> default-path key:** *no key is derived from free text **BY THE MODEL**. A registry-declared
> rule over the object is admissible iff it is deterministic, stated in the vocabulary, and
> identical for every record under that relation.*

*The rule is not specified here. This spec ships the arity axis and the honest default; a
default-path key is its own decision and its own round, and pretending otherwise is how §2's
dodge got in.*

## 4. The v1 reclassification, with the reason for each

| relation | today | proposed | why |
|---|---|---|---|
| **`measures`** | `single` | **`keyed`** by the quantity | its gloss already enumerates three quantities |
| **`prefers`** | `single` | **`keyed`** by the preference's subject-matter | a standing preference is per-topic; the gloss *“one current value”* is true **per topic**, false per person |
| **`health_state`** | `single` | **`keyed`** by the condition | *“a current health condition”* — people have several at once, and superseding one with another is a clinical falsehood the store then renders as current |
| `works_as` | `single` | **`single`** | one employment at a time is the intended model; a second job is a modelling question this spec does not open |
| `located_at`, `deadline`, `scope` | `single` | **`single`** | unchanged |
| everything else | `multi` | **`multi`** | unchanged |

## 5. 🔴 The substrate question: the records ALREADY retired

**A flag change is not retroactive, and this is the part that needs the owner's word
rather than a reviewer's.** Every value wrongly retired under the old arity is still in
the store — invalidated, with `invalidation_reason = 'superseded'` — so the affected
set is **derivable, not guesswork**: rows under a reclassified relation whose
invalidation reason is `superseded`.

**A reinstatement verb already exists and its scope is instructive.**
`_reinstate_edge_row` reverses 0022's revoked-source retirement, and its docstring
carries the rule this spec must not break: *“The wiki drops too: the derived view
changed in the restoring direction as surely as in the retiring one, and a stale cache
serving the pre-lift world is the same defect mirrored.”*

> 🔴 **That is the SAME HOLE the owner ruled on today in `A10`** — a change to a fact
> not reaching what was derived from it — **arriving from a third direction.** Any
> migration here inherits A10's answer: **the receipt NAMES the derived records the
> reinstatement invalidates, and the caller decides.**

**Three options, and this spec recommends the second:**

| | |
|---|---|
🔴 **THREE THINGS v1 DID NOT NAME (dev's internal review, A2/A3):**

| | |
|---|---|
| **the derivable set is a SUPERSET** | rows marked `superseded` under a reclassified relation include the CORRECTLY retired ones — weight 78 → weight 80 is a true supersession. **Separating them needs the key the old rows do not carry**, so under §3b's default the WHOLE set reinstates and both readings go live. *Stated as the migration's accepted cost, or the migration is scoped to rows where a registry key resolves — and that scoping does not exist until a key rule does* |
| **the successor's pointer** | the successor keeps `supersedes = <prior>`, and `doctor`'s refs rule requires the predecessor RETIRED. **A migrated store fails `veracium doctor` until the pointer is rewritten or the rule amended** — neither is free, and v1 named neither |
| **the journal and the release** | a migration-driven reinstatement needs its journal kind dispositioned under 0029 (an undispositioned reason is itself a bound refusal site), and a data-changing migration owes 0018's release-migration obligations |

| **do nothing** | correct going forward, wrong about the past; the store keeps facts marked superseded that were never superseded |
| 🔴 **a migration that reinstates, with a receipt** *(recommended)* | reinstate rows retired under a reclassified relation, drop the derived views, **name them in a receipt** — the data is present and the affected set is exactly derivable |
| **reinstate silently** | rejected: it changes what the agent says about a person with no record of why |

## 6. Invariants and executable checks

| | invariant | check, and the MUTANT it must fail on |
|---|---|---|
| **INV-A1** | **A `keyed` relation supersedes WITHIN a key and never across keys** | two differing values under different keys → both active; two under the SAME key → the prior retires. **Mutant: drop the key from the slot tuple — the cross-key case must then FAIL** |
| **INV-A2** | **An unkeyed record under a `keyed` relation ACCUMULATES** | a record with no resolvable key never retires anything. **Mutant: fall back to the subject-wide slot — the check must FAIL and name the record** |
| **INV-A3** | **Arity is DECLARED; no key is derived from free text BY THE MODEL** *(reworded, §3b: a deterministic registry-declared rule over the object IS admissible; the extractor emitting a key is not)* | the extractor cannot emit a slot key; the registry snapshot carries arity per relation. **Mutant: a text-derived key — refused** |
| **INV-A4** | **Every host registry valid today keeps its present meaning** | `functional=True ≡ single`, `functional=False ≡ multi`, asserted over the shipped `DEFAULT_RELATIONS` and over a host registry fixture |
| **INV-A5** | **A reinstatement names its descendants** | the migration's receipt lists the derived views dropped; **mutant: reinstate without the receipt → refuse** (A10's rule, inherited) |

## 7. Claims and limits

**Claimed:** that a later statement under these three relations stops deleting an
unrelated earlier one, and that the change is expressible in the declared vocabulary
rather than inferred from text.

**NOT claimed:**
- **that the key is always resolvable.** §3a's fallback is `multi` by design, so some
  records will accumulate where a key would have been better. *An accumulating store is
  recoverable; a superseded fact is not.*
- **that `works_as` is right.** One employment per subject is retained as the intended
  model and is a separate question.
- **anything about records already retired** — §5 is the owner's decision, and until it
  is taken, the store's past remains as it is and this spec does not describe it.

## 8. Alternatives rejected

- **Flip the three flags to non-functional.** §2: it loses the update semantics that
  make `measures` worth having, and the fix would be reported as complete while
  breaking the relation's stated purpose.
- **Amend 0025 in place by a dated blockquote.** 0025 governs registry *validation*;
  arity is *supersession* semantics, which is 0003's surface, and the change is stored
  rather than procedural. A change that alters which records are retired is not a
  blockquote. 🔴 **BUT v1 OVERSTATED THIS (A4): 0025 IS touched** — `Relation` is the record
  0025 validates, so adding `arity` is a registry-validation change whatever the
  supersession argument says. **And `functional` beside `arity` is two carriers of one
  fact, the drift this project keeps paying for.** So: **`functional` becomes DERIVED
  (`single ⇒ True`, otherwise `False`) and the validator REFUSES a registry where the two
  disagree** — one carrier, with a compatibility reader.
- 🔴 **A cost v1 did not name (A5):** `compile._policy_digest` binds the sorted set of
  functional relation names. **An arity-shaped blob changes that digest for EVERY store at
  upgrade — one forced wiki recompilation each, even where the registry's meaning is
  unchanged.** Either state it as the upgrade's cost, or **keep the blob byte-identical
  while no relation is `keyed`**, which makes the recompilation land only where the
  meaning actually changed.
- **Split `measures` into per-quantity relations** (`weighs`, `saves`). It works, and
  it pushes the vocabulary's growth onto every host; `keyed` expresses the same thing
  once. *Worth the reviewer's attention as the cheaper alternative if `keyed` proves
  hard to key.*

## 9. Brief for the external reviewer — ROUND 1

**The one question this round asks:** **is `keyed` the right shape, or is the
per-quantity relation split the honest one?** *Our reading is that `keyed` states the
intent once in the vocabulary where a host can read it, and that splitting pushes a
combinatorial vocabulary onto every deployment — but the split has a real advantage we
do not want to argue away: a relation with one meaning cannot mis-key a record, and
§3a's fallback admits that ours can.*

**What we are NOT asking:** whether the three relations are wrongly classified today.
§1 reproduces that against the shipped planner with a control, and the owner has ruled
the change.
