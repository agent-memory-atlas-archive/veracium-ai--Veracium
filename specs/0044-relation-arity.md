# Feature spec: relation arity — a functional relation is ONE SLOT PER SUBJECT, and three of ours should not be

Spec-Status: draft

| | |
|---|---|
| **Author / session** | research (veracium-research-48), the candidate's author → dev (veracium-2b), adopted at rest and re-read from the file: v1.1 2026-09-20 from `0044-relation-arity-CANDIDATE.md` (sha16 3f9f9db8ea92cc0a); v1.2 2026-10-10 from `0044-relation-arity-CANDIDATE.md` (sha16 72cd614748837a31) |
| **Version** | **v1.2 — 2026-10-10: the owner's answers folded, and the document restructured into the template's sections.** Base: the tree's adopted copy at `4ea1ce5` (v1.1); the Author and Number cells are dev's and are carried verbatim from that copy. 🔴 **§5's substrate question is DECIDED: the owner chose (b), "I approve (b)" (2026-10-10, first-hand in the dev session, relayed by dev)** — a one-time migration that reinstates the derivable set and NAMES every restored fact in a receipt, accepting that correctly replaced values come back too and are re-retired from the receipt. v1.1 named three obligations that choice carries (the superset, the successor's pointer, the journal and the release); **v1.2 turns each into a requirement (§4e–§4h) with an invariant (§6)**. 🔴 **v1.1 had none of the template's REQUIRED sections — §2c untrusted inputs, §2c-ii reach, §3 the trust-class matrix — and v1.2 adds them**, moving v1.1's argument rather than rewriting it: old §1–§2 → §1, old §3–§4 → §4a–§4d, old §5 → §4e–§4h, old §7 → §8, old §8 → §1c. **Found while writing them** (each with its command in §2c-ii): **nine lines in `src/` read `.functional`**, of which v1.1 named two (dev's carrier-read corrected research's first count of seven, which was the count of a narrower grep, not of readers) — the render-time contention ordering, the recall contested groups and the wiki compile's refusal-pair exclusion all group by `(subject, relation)` and must group per key (§2, §4d); the migration's safety against reviving a redacted tombstone rests on 0041 REPLACING `relation`, an unnamed dependency now pinned (INV-A7); and `dispute()` writes reason `disputed`, so no shipped verb can re-retire a reinstated value as `superseded` — §4h specifies a narrow one. **The owner also answered "yes" to Q1 (store statistics may travel in dispatched specs); it does not reach this spec:** v1.1 had already removed its share figure under the rule for a figure nobody can re-derive (§1a), and a ruling that a class of figure MAY travel does not make an unre-derivable one re-derivable. Prior: v1.1, v1. |
| **Status** | *narrative only — the canonical state is the `Spec-Status:` line at the top* |
| **Internal reviewers** | research (author) · dev |
| **External review** | **required** — this changes **stored semantics**: which records a later statement RETIRES, and (§4e) which already-retired records come back. A wrong answer silently retires facts a user stated, or silently restores ones that were correctly replaced. |
| **Decision + date** | **§5 / old Q3: (b), the owner, 2026-10-10** ("I approve (b)"). Acceptance: pending the external round. |
| **Path** | **full** |
| **Number** | 0044 — from `allocation.py --next` at adoption, 2026-09-20. |
| **Predecessor** | none. Occasioned by `TRACK-B-RENDER-PATH-RESULT.md` §5–6 (fix **B**, *“stop treating multi-valued attributes as functional”*, recorded there as *“the real modelling question and the owner's”*). **Travels with** the 0003 contested-order amendment in one review package (the owner's grouping, 2026-09-19: the two share the contested-render surface a reviewer needs whole). |

---

## 1. Problem and motivation

### 1a. The defect, reproduced — with a control that separates

**The supersession scope is `(user, subject, relation)`** (`graph._build_supersession_plan`'s scope read), and for a
relation flagged `functional` **any differing object retires the prior**
(the `rel.functional` branch in the same function). So `functional` means **one slot per subject**, not one slot per
quantity, per topic or per condition.

Driving the supersession path the ingest path applies (`graph.apply_supersession`) with two differing values under
one `(subject, relation)`, then reading the active set (§2c-ii row 1):

| relation | `functional` | active after the second value |
|---|---|---|
| **`prefers`** | `True` | only the second — *“oat milk”* retired by *“window seats”* |
| **`health_state`** | `True` | only the second — *“asthma”* retired by *“iron deficiency”* |
| **`measures`** | `True` | only the second — *“weight 78 kg”* retired by *“savings 4200”* |
| 🔴 **`uses_tool`** *(the control)* | **`False`** | **both** |

🔴 **`measures`' own gloss names three different quantities — “weight, reading
progress, savings balance” — and then files them in ONE slot.** *The documentation of
the relation contains the counter-example to its own arity.*

**What “retired” means, precisely** (§2c-ii row 1): the prior row is KEPT — `invalidated_at` set,
`invalidation_reason = 'superseded'` — and leaves every active read: recall, context, the wiki. It is not deleted,
which is what makes §4e's reinstatement possible. *The harm is silent: the agent stops “knowing” a person's asthma the
moment a second condition is mentioned, and nothing tells anyone.*

> **Method note, recorded because it nearly produced the opposite finding.** The first
> probe wrote through `Store.add_edge` and **both rows stayed `ACTIVE`** — the raw
> writer applies no supersession. *A probe that goes around the path under test reports
> the ABSENCE of the defect, in a form indistinguishable from a passing check.* The
> table above drives the supersession path itself.

🔴 **A FIGURE REMOVED RATHER THAN CAVEATED (dev's internal review, A7).** v1 carried
a figure for the share of active edges sitting under functional relations, twice
qualified: the store it was measured on no longer exists and nobody can re-derive it.
**The number is not restated here** — a removal notice that repeats the figure leaves it
liftable, which is the superseded claim travelling inside its own withdrawal. **This project's rule for a figure
nobody can check is to remove it, not to explain it.** *The owner's 2026-10-10 answer that store statistics MAY travel
in dispatched specs does not restore it: permission for a class of figure is not re-derivability for this one. The
defect stands on the probe above, which anyone can re-run on a fixture they build themselves.*

### 1b. What the boolean is actually carrying

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

### 1c. Alternatives rejected

- **Flip the three flags to non-functional.** §1b: it loses the update semantics that
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
  disagree** — one carrier, with a compatibility reader (§4c, INV-A10).
- **Split `measures` into per-quantity relations** (`weighs`, `saves`). It works, and
  it pushes the vocabulary's growth onto every host; `keyed` expresses the same thing
  once. *Worth the reviewer's attention as the cheaper alternative if `keyed` proves
  hard to key (§9).*
- **Leave the already-retired records retired** (old §5's option (a)). Correct going forward, wrong about the past.
  **Not chosen: the owner chose (b), 2026-10-10.**
- **Reinstate silently.** Rejected: it changes what the agent says about a person with no record of why.
- **Clear the successor's `supersedes` pointer at migration** instead of amending `doctor` (§4f). Rejected: the
  derivable set is a superset (§4e), so for every *correctly* replaced pair (weight 78 → 80) the pointer is TRUE, and
  clearing it would destroy a true supersession record to silence a check. §4f keeps the record and tells the check why.

---

## 2. Field contracts touched

Consumers enumerated by command, not recall (§2c-ii row 6: `grep -rn --include="*.py" -e "\.functional\b" src/`,
plus the declarations in `src/veracium/schema.py`).

| field / site | read / written | its documented contract | does this change preserve it? |
|---|---|---|---|
| `Relation.functional` (`schema.py`) | written by every registry declaration | *“one current value per subject → supersede on change”* | **Kept, now DERIVED from `arity`** (`single ⇒ True`). Every registry valid today keeps its meaning (INV-A4); a registry declaring both and disagreeing is REFUSED (INV-A10). |
| `Relation.arity` *(new)* | read by every consumer below | `single` · `multi` · `keyed` (§4a) | new |
| `graph._build_supersession_plan`, the `rel.functional` branch (`graph.py` L548) | reads | a differing value under a functional relation retires the prior | **Changed for `keyed` only:** the slot becomes `(user, subject, relation, key)`; an unkeyed record accumulates (§4b–§4c). `single` and `multi` unchanged. |
| contention ordering, `graph.py` L658 | reads | groups active edges of a functional relation by `(subject, relation)` and orders each group by recorded authority (0012 I6) | **Must group per key under `keyed`**, and must NOT group unkeyed `keyed` records (they are not contending). *The 0003 contested-order amendment travelling in this package is this surface.* |
| recall contested groups, `__init__.py` L1413 | reads | a refusal pair under a functional relation is surfaced as contested | **Same rule:** contested only within one key. |
| wiki compile's refusal-pair exclusion, `compile.py` L116 | reads | excludes contested pairs of a functional relation from the compiled view | **Same rule.** |
| `compile._policy_digest` (`compile.py` L79–80) | reads | binds the sorted functional relation names | **Changed:** binds arity per relation. Every store using the default registry recompiles its wiki ONCE at upgrade (§4i) — stated as the upgrade's cost. |
| `registry.FrozenRel` and the canonical-form check (`registry.py` L39–78) | reads, snapshots | the snapshot carries `functional`; a reserved relation's canonical form is compared on it (L67, L71) | **Carries `arity`** (and the derived `functional`) at BOTH construction sites — L74 (the host's relations) and L78 (the reserved relations' canonical form); the canonical comparison is on `arity`. |
| `Edge.invalidated_at`, `Edge.invalidation_reason` | written by the migration (§4e) | `superseded` means a later value under the same slot retired this one | **Cleared** for each reinstated row — the same write 0022's reinstate verb performs. |
| journal `reinstated` event (`store/sqlite.py`, `_journal_edge_write`) | written by the migration | *“`reason` is non-NULL iff kind == invalidated”* (0029) | **Changed — a 0029 amendment (§4g):** `reinstated` gains a closed reason vocabulary so a migration's reinstatement is distinguishable from 0022's. |
| `doctor`'s `refs` rule (`doctor.py` L294–310) | reads | an active edge whose `supersedes` names a still-active predecessor is a WARN (exit 1) | **Changed (§4f):** a pair whose predecessor's latest event is `reinstated` with the migration's reason is reported as `info`, not `warn`. |

**Documentation that states the old meaning and must change with it:** the `functional` comment in `schema.py`
(L457), `graph.py`'s module docstring (*“Supersession: for a functional relation, a new value invalidates the
prior”*), and `_policy_digest`'s docstring.

---

## 2c. Untrusted inputs — REQUIRED, blocking

| uncontrolled input | empty | malformed | unrecognised | adversarial | **invariant that pins it** |
|---|---|---|---|---|---|
| **extractor output** — the relation name and object string the model emits from `remember`'s event text | no edge, nothing retired | the extractor's existing refusal path; unchanged | a relation outside the registry → the existing unclassified route; unchanged | **the model cannot choose a slot key.** Text crafted to retire a stored fact can only do so within one declared key, under a registry rule the model does not author | **INV-A3** (no key derived by the model), **INV-A1** (no cross-key retirement) |
| **host registry** — a `Relation` declaration with `arity` (and, for compatibility, `functional`) | absent `arity` → derived from `functional` (`True ⇒ single`, `False ⇒ multi`) | an `arity` outside the three values → REFUSED at registry validation | — | `functional=True` with `arity=keyed` (two carriers disagreeing) → REFUSED | **INV-A4**, **INV-A10** |
| **a host-supplied key** *(no path exists today — §2c-ii row 2)* | treated as **unkeyed**: the record accumulates | treated as unkeyed | treated as unkeyed | a key is data: never a relation name, never SQL, never a slot outside its own relation | **INV-A2** (unkeyed accumulates); when a key path is added it is its own round (§4b) |
| **data written by an older version** — rows invalidated as `superseded` under a relation now `keyed` | the migration reinstates nothing (empty receipt) | a row that fails to parse aborts that user's migration transaction; nothing is half-applied | a row whose `relation` is the redaction MARKER is not under a reclassified relation and is never selected | a **redacted** row is never revived; a **quarantined** row comes back quarantined | **INV-A7**, **INV-A8**, **INV-A11** |
| **`MigrationAttestation`** (0018: the host-owned facts — quiescence, backup reference) | refused by 0018 | refused by 0018 | refused by 0018 | 0018's own §2c governs it; this spec adds no field to it | 0018's invariants, unchanged |
| **the undo verb's `edge_id`** (§4h) | refused | refused | an id the migration did not reinstate → **REFUSED** | the verb cannot retire an arbitrary edge: it is not a suppress verb | **INV-A12** |
| CLI / environment / git | n/a — this spec reads none | | | | |
| network / provider response | n/a — none | | | | |

### 2c-ii. Assertions about reach — REQUIRED

Every command runs from the repository root at `4ea1ce5` with a Python carrying the package's dependencies
(research ran them on CPython 3.14.7, 2026-10-10). **EXECUTED** = run and read; **READ** = the cited lines.

| # | assertion | command | result |
|---|---|---|---|
| 1 | a second value under `prefers` / `health_state` / `measures` retires the first; `uses_tool` keeps both | `PYTHONPATH=src python -c "from veracium.graph import apply_supersession as ap; from veracium.schema import DEFAULT_RELATIONS as R, Edge, Provenance, EvidenceAuthor as A, Disclosure as D; from veracium.store.sqlite import SqliteStore as S; E=lambda i,r,o: Edge(id=i,user_id=\"u\",subject=\"user\",relation=r,object=o,provenance=Provenance(author_of_evidence=A.USER,evidence_ref=\"ev\",disclosure=D.MENTIONABLE)); run=lambda r,a,b:(s:=S(\":memory:\"),s.add_edge(E(\"p\",r,a)),ap(s,E(\"i\",r,b),R),s.add_edge(E(\"i\",r,b)),sorted(x.object for x in s.edges(\"u\")))[-1]; [print(r, run(r,a,b)) for r,a,b in ((\"prefers\",\"oat milk\",\"window seats\"),(\"health_state\",\"asthma\",\"iron deficiency\"),(\"measures\",\"weight 78 kg\",\"savings 4200\"),(\"uses_tool\",\"Notion\",\"Figma\"))]"` | EXECUTED: `prefers ['window seats']` · `health_state ['iron deficiency']` · `measures ['savings 4200']` · `uses_tool ['Figma', 'Notion']`. The retired prior is kept with `invalidation_reason='superseded'` |
| 2 | `Relation` has no key field and `remember` takes no structured key | `PYTHONPATH=src python -c "import inspect; from veracium.schema import Relation; from veracium import Memory; print(list(Relation.model_fields)); print(list(inspect.signature(Memory.remember).parameters))"` | EXECUTED: `['name', 'functional', 'desc', 'relation_kind']` · `['self', 'user_id', 'event_text', 'author', 'date', 'event_type', 'evidence_ref', 'derived_from', 'context', 'source_id']` |
| 3 | a redacted, superseded prior keeps `invalidation_reason='superseded'` but its `relation` is the marker, so selection by relation name excludes it | `PYTHONPATH=src python -c "from veracium.graph import apply_supersession as ap; from veracium.schema import DEFAULT_RELATIONS as R, Edge, Provenance, EvidenceAuthor as A, Disclosure as D; from veracium.store.sqlite import SqliteStore as S; E=lambda i,o: Edge(id=i,user_id=\"u\",subject=\"user\",relation=\"prefers\",object=o,provenance=Provenance(author_of_evidence=A.USER,evidence_ref=\"ev\",disclosure=D.MENTIONABLE)); s=S(\":memory:\"); s.add_edge(E(\"p\",\"oat milk\")); ap(s,E(\"i\",\"window seats\"),R); s.add_edge(E(\"i\",\"window seats\")); s.redact(\"u\",edge_id=\"p\",reason=\"subject_request\"); p=[x for x in s.edges(\"u\",active_only=False,include_quarantined=True) if x.id==\"p\"][0]; print(repr(p.relation), p.invalidation_reason)"` | EXECUTED: `'\x00veracium:redacted\x00' superseded`. **The exclusion holds only because 0041 REPLACES `relation`** — pinned by INV-A7 |
| 4 | a `reinstated` journal event carries no reason today | `grep -n "reason. is non-NULL iff kind == invalidated" src/veracium/store/sqlite.py; grep -n "kind=\"reinstated\"" src/veracium/store/sqlite.py` | READ: L298 (the contract) · L852 (0022's reinstate verb writes `reinstated`, no reason) |
| 5 | after a reinstatement the successor fails `doctor` | `grep -n "predecessor is still active" src/veracium/doctor.py; grep -n "return 1 if any(f.level in (\"error\", \"warn\")" src/veracium/doctor.py` | READ: L308 (a `warn`) · L142 (a `warn` exits 1) |
| 6 | nine lines in `src/` read `.functional`, two of them constructing a `FrozenRel` | `grep -rn --include="*.py" -e "\.functional\b" src/` | READ: `__init__.py:1413`, `compile.py:79`, `compile.py:116`, `graph.py:548`, `graph.py:658`, `registry.py:67`, `registry.py:71`, `registry.py:74`, `registry.py:78`. **:74 and :78 are the two `FrozenRel` construction sites** — :74 the host's relations, :78 the RESERVED relations injected from their canonical form — and BOTH must carry `arity`. *A first count of seven came from a grep over `rel.`/`r.`/`v.` only and missed the two `canon.` reads; dev found them by complement.* |
| 7 | no shipped verb re-retires an edge as `superseded` | `grep -n "invalidated (reason .disputed.)" src/veracium/__init__.py; grep -n -e "^    def dispute(" -e "^    def correct(" src/veracium/__init__.py` | READ: L1839 — `dispute()` writes `disputed`; `correct()` (L2035) writes a corrected successor. **Neither labels a re-retired weight reading truthfully** |

---

## 3. Trust-class matrix — REQUIRED, blocking

Classes enumerated from the enums at `4ea1ce5`: `EvidenceAuthor` = user, third_party, system, assistant;
`Disclosure` = mentionable, use_only, quarantined.

### 3a. Supersession under a `keyed` relation — directional

**This spec changes the SLOT, never the AUTHORITY.** 0003's authority matrix (`authority.permitted`) decides whether
an incoming edge may retire a prior; 0044 decides only which priors are candidates. So every cell below reads
*“0003 decides”* or *“no candidate”*:

| incoming vs prior | prior=A, incoming=B | prior=B, incoming=A | same class | involving quarantined | involving `use_only` |
|---|---|---|---|---|---|
| **same key** | 0003 decides, unchanged | 0003 decides, unchanged | 0003 decides, unchanged | 0003 decides, unchanged | 0003 decides, unchanged |
| **different key** | **no candidate** — both stand | **no candidate** | **no candidate** | **no candidate** | **no candidate** |
| **either record unkeyed** | **no candidate** — accumulates (INV-A2) | **no candidate** | **no candidate** | **no candidate** | **no candidate** |

`single` and `multi` relations: **every cell unchanged** from 0003 / today.

### 3b-i. The migration (§4e) — a state-transition table over a derivable set

The migration is a **batch** over one user's rows. **It reads no trust class and changes none:** each row's
provenance is its OWN, never derived from another member of the set.

| row's `author_of_evidence` | mentionable | use_only | quarantined |
|---|---|---|---|
| user · third_party · system · assistant | reinstated: `invalidated_at`/`invalidation_reason` cleared; provenance, disclosure, confidence unchanged | same | **reinstated AND still quarantined** — not assertable (INV-A11) |
| any, **redacted** | **never selected** (INV-A7) | same | same |

- Can it make a **user-asserted fact non-assertable**? The change to supersession: **no** — it can only retire LESS
  (within one key instead of across the subject). The migration: **no** — it only reinstates.
- Can **non-user content gain user-grade authority**? **No.** Reinstatement restores each row to its own stamp; an
  assistant-authored row comes back assistant-authored, and 0003's authority rule still governs anything it contends
  with.
- 🔴 **Can it make a fact the person REPLACED current again?** **Yes — by the owner's decision (b).** A correctly
  replaced value (weight 78, replaced by 80) comes back. The receipt names it (INV-A8), and §4h re-retires it.
- Can it **clear `needs_confirmation`**? No; neither path touches it.
- Does it **merge, drop or overwrite provenance**? No.

**Write-time or maintain-time?** Supersession: write-time (new evidence). The migration: a one-time, operator-run
data change at upgrade, under 0018.

## 3b. Authorization and scope — *full specs only*

- **User / tenant / scope boundary?** None crossed. Supersession and the migration act within one user's rows; the
  migration runs per user, one transaction each.
- **Who may run the migration?** The operator, through 0018's orchestrator, with 0018's attestation (quiescence and a
  backup reference). **Not exposed over MCP and not a `remember`-path effect.**
- **Who may run the undo verb (§4h)?** The host, for one user, on an edge the migration reinstated. **Not exposed over
  MCP** — for the reason `dispute()` is not: an agent-callable retire verb is a prompt-injection target.
- **Does anything become visible to a principal who could not see it before?** Reinstated rows become visible again
  **to the same user's surfaces that saw them before they were retired**, under their own disclosure. Nothing
  crosses a user.

---

## 4. Behaviour

### 4a. Arity is DECLARED, and it has three values

Replace the boolean with a declared arity on the `Relation` record:

| arity | meaning | slot key | shipped examples |
|---|---|---|---|
| **`single`** | one value per subject; a differing value supersedes | `(user, subject, relation)` | `works_as`, `located_at`, `deadline`, `scope` |
| **`multi`** | values accumulate; nothing supersedes | *(no slot)* | `uses_tool`, `has_pet`, `relative_of` |
| 🔴 **`keyed`** | one value **per declared key**; a differing value supersedes **within that key only** | `(user, subject, relation, key)` | **`measures`, `prefers`, `health_state`** |

**`functional=True` maps to `single` and `functional=False` to `multi`**, so every
host registry that exists today keeps its present meaning; `keyed` is the new capacity
and nothing acquires it by default except the three relations reclassified in §4d.

### 4b. Where the key comes from — and where it must NOT come from

🔴 **The key is DECLARED, never inferred from the text by the model.** 0037 rejected
*“letting the extractor decide procedural-ness or basis from the text”* on the round's
ruling and on 0031's, and the same reasoning binds here: a slot key chosen by the model
is the model deciding which of a person's facts gets retired.

**Two admissible sources, in this order:**

1. **A structured key the host supplies** with the edge (the host knows its own domain).
2. **A registry-declared key FIELD** — the relation declares that its key is, e.g., the
   first segment of a structured object — so the rule is readable in the vocabulary and
   is the same for every record under that relation.

**If neither is available for a given record, the relation behaves as `multi` for that
record: it accumulates.** *Accumulating is recoverable; superseding across keys is the
present defect exactly.*

### 4c. 🔴 ON THE SHIPPED PATH THERE IS NO KEY

**Dev's internal review, A1, blocking, and it is right** (§2c-ii row 2). `Memory.remember` takes event text and
metadata and **no structured key**; `Relation` carries `name`, `functional`, `desc`, `relation_kind` and **no key
field**. So on the default extractor path BOTH sources above are absent, every record under a reclassified relation
is unkeyed, and **`keyed` behaves as `multi`.**

> 🔴 **Which means that, on the default path, v1 SHIPPED THE THING §1b CALLS THE NARROW
> DODGE.** *A spec that argues against flipping the flag and then delivers the flip through
> a fallback is worse than one that flips it honestly, because the argument conceals the
> outcome.*

**So the behaviour is stated, not implied:**

| | on the shipped extractor path | when a host supplies keys |
|---|---|---|
| `prefers`, `health_state` | **accumulate** — no value is retired by an unrelated one, and none supersedes | one current value **per topic / per condition** |
| `measures` | **accumulates** — 🔴 **and the update semantics are LOST until a key exists: “I now weigh 80” no longer retires 78** | one current value **per quantity**, which is the relation's stated purpose |

**That cost is real and it is the reason this spec is not finished at `multi`.** *Both are
strictly better than today — a weight reading no longer retires a job title — and neither
is the model the relation describes.*

**What returns the update semantics, and the rule it forces.** A **declared, deterministic registry rule over the
object, evaluated by the registry and never by the model** — e.g. `measures` keys on the leading quantity term. **It
is derivation from TEXT, and that is admissible; derivation by the MODEL is not** (INV-A3). *The rule is not specified
here. This spec ships the arity axis and the honest default; a default-path key is its own decision and its own
round, and pretending otherwise is how §1b's dodge got in.*

**`functional` is DERIVED (§1c):** `single ⇒ True`, otherwise `False`, so the consumers in §2 that read `functional`
keep working during the transition; each is moved to read `arity` (the contention, recall and compile readers must,
because `keyed` is not `single`).

### 4d. The reclassification, with the reason for each

| relation | today | proposed | why |
|---|---|---|---|
| **`measures`** | `single` | **`keyed`** by the quantity | its gloss already enumerates three quantities |
| **`prefers`** | `single` | **`keyed`** by the preference's subject-matter | a standing preference is per-topic; the gloss *“one current value”* is true **per topic**, false per person |
| **`health_state`** | `single` | **`keyed`** by the condition | *“a current health condition”* — people have several at once, and superseding one with another is a clinical falsehood the store then renders as current |
| `works_as` | `single` | **`single`** | one employment at a time is the intended model; a second job is a modelling question this spec does not open |
| `located_at`, `deadline`, `scope` | `single` | **`single`** | unchanged |
| everything else | `multi` | **`multi`** | unchanged |

**Contention follows the slot.** The contention ordering, the recall contested groups and the compile exclusion
(§2) group `keyed` records **per key**, and do not group unkeyed `keyed` records at all: two accumulated values are
not contending. *This is the surface the 0003 contested-order amendment in this package renders.*

### 4e. 🔴 The records ALREADY retired — the migration (DECIDED: the owner's (b), 2026-10-10)

**A flag change is not retroactive.** Every value wrongly retired under the old arity is still in the store —
invalidated, with `invalidation_reason = 'superseded'` — so the affected set is **derivable, not guesswork**:

> **The derivable set, per user:** rows whose `relation` is one of the relations reclassified to `keyed` (§4d) and
> whose `invalidation_reason` is `superseded`.

**The migration**, run once at upgrade through 0018's orchestrator, per user, in one transaction each:

1. **Reinstate** every row in the set: clear `invalidated_at` and `invalidation_reason` — the same write 0022's
   reinstate verb performs — and journal it as `reinstated` with reason **`arity_reclassified`** (§4g).
2. **Drop the user's compiled view** — *“the derived view changed in the restoring direction as surely as in the
   retiring one”* (0022's reinstate verb, whose rule this inherits).
3. **Emit a receipt** naming, for each reinstated row: its id, relation, object, and the successor that had retired
   it (the row whose `supersedes` names it). **And the derived views dropped** — the owner's A10 rule, inherited:
   *a change to a fact names what was derived from it.*

🔴 **THE SET IS A SUPERSET, AND THE OWNER CHOSE THAT KNOWINGLY (dev's internal review, A2).** It includes the
CORRECTLY retired readings — weight 78 → weight 80 is a true supersession — and the old rows carry no key to tell them
apart. **So both readings come back, and the receipt is how the person or host finds the ones to re-retire (§4h).**
*Scoping the migration to rows where a registry key resolves would avoid it, and that scoping does not exist until a
key rule does (§4c).*

**Selection is by relation name, and that is safe only because 0041 REPLACES `relation`** on a redacted row with the
marker (§2c-ii row 3). A redacted superseded row keeps `invalidation_reason='superseded'`; were 0041 ever to PRESERVE
`relation`, a selection by reason would revive a tombstone. **INV-A7 pins the exclusion directly** — a row carrying
the marker, or with a redaction attestation, is never selected — so the safety does not rest on 0041's map staying
as it is.

### 4f. The successor's pointer, and `doctor`

After reinstatement the successor still carries `supersedes = <prior>` while both are active, which `doctor`'s
`refs` rule reports as a `warn` — **and a `warn` exits 1** (§2c-ii row 5). **The pointer is KEPT** (§1c: for every
correctly replaced pair it is a true record). **`doctor`'s rule is amended:** a pair whose predecessor's latest
journal event is `reinstated` with reason `arity_reclassified` is reported at level `info` — *“reinstated by the
arity migration; the successor's `supersedes` is historical”* — and does not affect the exit code. Any other
unretired predecessor still warns.

### 4g. The journal — an amendment to 0029

0029's contract is that `reason` is non-NULL iff the kind is `invalidated` (and, since 0041, `redacted`) (§2c-ii
row 4). **So today a migration's reinstatement and 0022's are indistinguishable**, and neither `doctor` (§4f) nor
`why` could say which happened. **The amendment:** `reinstated` carries a reason from a CLOSED vocabulary —
`source_restored` (0022's verb, which this amendment updates to write it) and `arity_reclassified` (§4e) — refused
outside it at the emission choke point, exactly as the `invalidated` and `redacted` reasons are. **Events written
before the amendment keep `NULL`, read as `source_restored`**, the only reinstatement that existed.

### 4h. Re-retiring a correctly replaced value — the undo verb

`dispute()` would label a re-retired weight reading `disputed` (§2c-ii row 7), which is false: nobody disputes that
the person weighed 78 kg; it was replaced. **So the spec adds one narrow verb:** re-retire, with reason
`superseded`, a row whose latest event is `reinstated` with reason `arity_reclassified` — the migration's own
reinstatement, undone — restoring exactly what step 1 of §4e cleared. **It refuses any other row (INV-A12).** *The
shape is 0022's “reverse OUR OWN” rule: a verb that can only undo this migration's writes is not a suppress verb.*
Host-only; not over MCP (§3b).

### 4i. The upgrade's recompilation cost (A5)

`compile._policy_digest` binds the functional relation names (§2). Moving it to arity changes the digest **for every
store using the default registry**, because §4d reclassifies three default relations: **one forced wiki
recompilation per store at upgrade.** Stated as the upgrade's cost. *v1.1 offered “keep the blob byte-identical while
no relation is `keyed`”; that saves nothing on the default registry, which has three.* A host registry with no
`keyed` relation keeps a byte-identical blob and recompiles nothing.

---

## 5. Regime analysis — where does this behave differently?

| regime | behaviour |
|---|---|
| **default extractor path** (no key) | `prefers`, `health_state`, `measures` accumulate (§4c); `measures` loses update semantics until a key rule exists |
| **host supplies keys** | one current value per key |
| **a registry key rule** *(future, its own round)* | as host keys, for records the rule resolves; unresolved records accumulate |
| **new store** | no migration work: the derivable set is empty, the receipt is empty |
| **upgraded store** | one migration per user; one wiki recompilation per store (§4i) |
| **migration run twice** | the second run reinstates nothing: the set is empty after the first (INV-A9) |
| **store with redactions** | redacted rows are never selected (INV-A7) |
| **store with quarantined rows** | reinstated, still quarantined (INV-A11) |
| **host registry with no `keyed` relation** | supersession, contention and digest byte-identical to today |
| **scale** | the set is one indexed selection per user; the receipt is proportional to it |

---

## 6. Invariants and executable checks — REQUIRED, blocking

| | invariant | check, and the MUTANT it must fail on |
|---|---|---|
| **INV-A1** | **A `keyed` relation supersedes WITHIN a key and never across keys** | two differing values under different keys → both active; under the SAME key → the prior retires. **Mutant: drop the key from the slot tuple — the cross-key case must FAIL** |
| **INV-A2** | **An unkeyed record under a `keyed` relation ACCUMULATES** | a record with no resolvable key never retires anything. **Mutant: fall back to the subject-wide slot — must FAIL and name the record** |
| **INV-A3** | **Arity is DECLARED; no key is derived from free text BY THE MODEL** *(a deterministic registry-declared rule over the object IS admissible; the extractor emitting a key is not)* | the extractor cannot emit a slot key; the registry snapshot carries arity per relation. **Mutant: a model-derived key — refused** |
| **INV-A4** | **Every host registry valid today keeps its present meaning** | `functional=True ≡ single`, `functional=False ≡ multi`, over the shipped `DEFAULT_RELATIONS` (minus §4d's three) and a host registry fixture. **Mutant: map `functional=True` to `keyed` — must FAIL** |
| **INV-A5** | **A reinstatement names its descendants** | the receipt lists the derived views dropped. **Mutant: reinstate without the receipt → refuse** (A10's rule, inherited) |
| **INV-A6** | **Contention follows the slot** | two values under different keys of a `keyed` relation are NOT grouped by the contention ordering, the recall contested groups or the compile exclusion; two under one key ARE. **Mutant: group `keyed` by `(subject, relation)` — must FAIL** |
| **INV-A7** | **The migration never revives a redacted row** | a superseded row redacted before the migration stays a tombstone; asserted on a row carrying the marker AND on a fixture where `relation` is (wrongly) preserved but an attestation exists. **Mutant: select by `invalidation_reason` alone — must FAIL** |
| **INV-A8** | **The receipt names every reinstated row, including the correctly replaced ones** | receipt rows == the derivable set, as sets, per user; a weight 78 → 80 pair appears with its successor. **Mutant: omit rows whose successor is the same quantity — must FAIL** |
| **INV-A9** | **The migration is idempotent** | a second run reinstates nothing and emits an empty receipt. **Mutant: select by relation alone, ignoring the reason — the second run must FAIL** |
| **INV-A10** | **`functional` and `arity` cannot disagree** | a registry declaring `functional=True, arity="keyed"` is refused at validation. **Mutant: accept it — must FAIL** |
| **INV-A11** | **Reinstatement preserves disclosure** | a quarantined superseded row comes back quarantined and not assertable. **Mutant: reset disclosure on reinstatement — must FAIL** |
| **INV-A12** | **The undo verb undoes only the migration's own reinstatements** | it refuses an active row the migration did not reinstate, a row reinstated by 0022's verb, and a never-retired row; on a migration-reinstated row it writes `superseded`. **Mutant: drop the reason check — must FAIL on the 0022 row** |
| **INV-A13** | **`doctor` is clean after the migration, and only for the migration's pairs** | a migrated store exits 0 from `doctor`; an unretired predecessor with no `arity_reclassified` event still warns. **Mutant: exempt all reinstated pairs regardless of reason — must FAIL on a 0022 pair** |
| **INV-A14** | **`reinstated`'s reason is closed** (0029 amendment) | a `reinstated` write with a reason outside {`source_restored`, `arity_reclassified`} is refused at the emission choke point. **Mutant: accept any reason — must FAIL** |

**Each check must be demonstrated RED against its mutant before acceptance.**

---

## 7. Failure modes and reversibility

- **Silent failure.** The supersession change cannot fail silently in the retiring direction: INV-A1/A2 refuse any
  cross-key retirement. **The migration's silent failure mode is the superset:** a correctly replaced reading comes
  back current, and the first visible symptom is the agent stating an outdated value (two weights). **The receipt is
  the mitigation**, and it is why the owner's (b) and not silent reinstatement.
- **Reversible?** **Yes, from two records.** (1) 0018's attestation carries a backup reference taken before the
  migration — the complete prior state. (2) Every reinstatement is journaled `reinstated`/`arity_reclassified`, and
  §4h re-retires any of them, restoring exactly the fields step 1 cleared. The compiled view is regenerated, never
  restored.
- **Partial failure.** One transaction per user: a crash mid-user leaves that user untouched; users already migrated
  stay migrated, and a re-run continues (INV-A9). 0018's orchestrator governs the run's preflight and readback.
- **New attack surface?** The undo verb is narrow by construction (INV-A12) and host-only. The supersession change
  removes an attack surface: text the model extracts can no longer retire a stored fact under an unrelated value.

---

## 8. Claims and limits

**Claimed:** that a later statement under these three relations stops retiring an unrelated earlier one; that the
change is expressible in the declared vocabulary rather than inferred from text; and that the values already
retired this way are restored, each named in a receipt.

**NOT claimed:**
- **that the key is always resolvable.** §4b's fallback is `multi` by design, and on the shipped extractor path no
  record is keyed (§4c): `measures` loses its update semantics until a key rule exists.
- **that the migration restores only wrongly retired values.** It restores the derivable set, a superset (§4e); the
  correctly replaced ones are named for re-retirement, not separated.
- **that `works_as` is right.** One employment per subject is retained as the intended model and is a separate
  question.

**Changelog wording, when it ships:** *“`prefers`, `health_state` and `measures` no longer let a second value retire
an unrelated first one. An upgrade migration restores values retired that way and lists every restored value in a
receipt; some of them were correctly replaced and can be re-retired from the receipt.”*

---

## 9. Brief for the external reviewer — ROUND 1

**The one question this round asks:** **is `keyed` the right shape, or is the
per-quantity relation split the honest one?** *Our reading is that `keyed` states the
intent once in the vocabulary where a host can read it, and that splitting pushes a
combinatorial vocabulary onto every deployment — but the split has a real advantage we
do not want to argue away: a relation with one meaning cannot mis-key a record, and
§4b's fallback admits that ours can.*

- **Least sure of:** (1) whether keeping the successor's pointer and amending `doctor` (§4f) is better than any form
  of clearing it — we rejected clearing because the pointer is true for half the set; (2) whether the undo verb
  (§4h) is the right granularity, or a receipt-wide “re-retire all with a same-quantity successor” operation is
  needed once a key rule exists; (3) whether §4c's default — `measures` accumulating with no update semantics — is
  acceptable to ship before a key rule, or whether `measures` should stay `single` until one exists.
- **Where we may have overstated:** §3a's claim that 0044 changes the slot and never the authority — tell us if any
  cell of 0003's matrix behaves differently once the candidate set shrinks.
- **What would change our minds:** evidence that hosts rely on `functional=True` retiring across topics for
  `prefers` (then the reclassification is a breaking change, not a fix); or a key rule simple enough to scope the
  migration to the wrongly retired rows alone.
- **What we are NOT asking:** whether the three relations are wrongly classified today (§1a reproduces it with a
  control), or whether to restore the already-retired values (the owner decided (b)).
- **Reviewer-safe copy:** nothing generalised.

---

## 10. Open questions

| # | question | who decides | by when | class |
|---|---|---|---|---|
| Q1 | May store statistics travel in dispatched specs? **RESOLVED 2026-10-10: yes** (the owner). *Does not reach this spec* (§1a). | owner | — | resolved |
| Q3 | The records already retired: leave, or a migration with a receipt? **RESOLVED 2026-10-10: (b)** (the owner). Carried as §4e–§4h. | owner | — | resolved |
| Q5 | The default-path key rule for `measures` (and whether `prefers`/`health_state` get one) | owner + dev, its own round | after this spec's acceptance | deferred |
| Q6 | §4f: keep the pointer and amend `doctor`, or clear it | dev + external reviewer | before acceptance | blocking |
| Q7 | `works_as`: one employment per subject | owner | — | deferred |

---

## Reviewer checklist

- [ ] §3 has no unanswered cells, and is **directional** where the operation is
- [ ] §3's classes were read from the enums, not copied from the template
- [ ] Prohibitions AND the corresponding **permissions** are both tested — a guard drawn too broadly passes every prohibition test
- [ ] Every default fails **closed**: an unresolvable input costs assertability rather than granting it
- [ ] §2c has a row per uncontrolled input, and **no empty invariant cell**
- [ ] §2c-ii: every claim about what is reachable / exposed / available carries **the command**
- [ ] §2 consumers were enumerated by grep, not recall
- [ ] Every §6 invariant has a check that actually runs, demonstrated RED against its mutant
- [ ] §5 regimes are reachable by tests
- [ ] §3b: no principal can see anything they could not see before
- [ ] §10 questions each carry a class; unclassified means blocking
- [ ] §8 states what this does *not* establish
- [ ] I have said where I think the **author's conclusion is wrong**, not only where the text is wrong
- [ ] I re-read the current version before reviewing, and I am quoting the version I approve
