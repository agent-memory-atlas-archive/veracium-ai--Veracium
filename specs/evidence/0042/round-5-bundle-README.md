<!-- TERMINAL RECORD — the round-5 review bundle README of specs 0042 and 0043, byte-copied
UNMODIFIED from the ACCEPTED package (sha256 791c1089776d9f49332483f8ff88b25794dec795ee8a7cf8eb33b441eaa1747a
@ a9d3622d6252a19387b2ecb66a665f101825fb36, CI 35382261953) on 2026-09-18, the day the reviewer
accepted both specifications at the design level and froze their invariant surfaces. It is the one
carrier holding the five per-round dispositions and the errors ledgers together; the version cells
carry lineage, not the reviewer's dispositions. The package remains the archive; this copy is the
record. THE BYTES AFTER THE BLANK LINE FOLLOWING THIS COMMENT equal the packaged README:
sha256 5883f018518d780efc29d86feb403e58c9544f4ca9e1d3622775814cfb31e099, 9585 bytes — verifiable forever against the archived package.
On the tarball: tar xzf <pkg> -O 0042-round5-review-package/README-0042-round5-bundle.md | sha256sum
Here: sed '1,/^-->$/d' <this file> | tail -n +2 | sha256sum   (the comment closes on its own line)
-->

# 0042 exercised guarantees — round-5 external review bundle (two specs)

Assembled 2026-09-18 by dev. The answer to the round-4 verdict, which returned BOTH
specifications with two remaining design issues and closed A6 at the design level
(banked verbatim in `prior-rounds/`, beside rounds 1–3): 0042 owed A4 (establishing
that counters are installed); 0043 owed A3 (consistent adjudication across
comparison arms) plus four bounded interpreter corrections. This bundle carries two
spec copies, each byte-identical to `tree/specs/` at the pin:

- `0042-exercised-guarantees-SPEC-v7.md` — **0042 v7, round 5 of this line.**
- `0043-refusal-harness-SPEC-v4.md` — **0043 v4, round 4 of its own line.**

**Canonical artifacts:** `specs/0042-exercised-guarantees.md` and
`specs/0043-refusal-harness.md` at the pinned commit (see `PIN.txt`); on any doubt
the repo wins.

## What round 4 found, stated plainly, and what changed

Both findings were the same shape as round 3's, one layer further in: a thing that
stood in for the thing under test. A `declare_site` call stood in for a counter bound
to a decision — both fixture decisions executed, the registry check and the four-set
reconciliation passed, and every counter stayed at zero. A prompt SECTION stood in for
a record's trust class — the baseline transform removes the sections, so the same
answer scored `REFUSED-QUARANTINED` on the shipped arm and `OTHER` on the baseline.
And our own control had degenerated: it was named "delete a counter" and deleted the
declaration, on a fixture that had no counters. Every item was reproduced at the pin
before anything changed; each design issue is closed by a DESIGN decision plus
evidence built to it, with the reviewer's reproduction as a standing control.

| issue | design decision, where | evidence, and the control that can fail |
|---|---|---|
| A4 — registration does not establish working instrumentation | 0042 Part A-0-quater: **THE SITE BINDS THE DECISION** — the decision is expressed THROUGH the declared site (`with SITE.consult(): raise SITE.fire(...)`), so the update and the decision are one call that cannot be separated. INSTALLED is the static scan of the BINDING: a `declare_site` call AND a `.consult` AND a `.fire` use inside a function body of the declaring module (AND, not either — consult without fire would read `UNEXERCISED` for a site that fired). A declared, registered, unbound id REFUSES as "registered, not installed". The RUNTIME derivation is the reviewer's round-4 test made an assertion: execute a declining decision, `consulted ≥ 1` AND `fired ≥ 1` | `specs/evidence/0042/installed_sites.py` and the fixture package rewritten through the site: the binding scan; the registry check refusing "registered, not installed"; **after one declining decision per loaded site the counters read (1, 1) and the report reads `EXERCISED` — never `UNREACHED` for a site that ran**; three refusing controls — strip the binding keeping the declaration and the raise (what "delete a counter" was always supposed to mean, now on a fixture that HAS counters), consult without fire, delete the declaration (kept under its honest, structural name); full binding with no traffic → `UNREACHED`. On this tree `declare_site` occurs zero times in `src/`, INSTALLED = ∅, and the test asserts it |
| A3 — removing baseline annotations changes the scoring reference | 0043 A3-quater: **PRESENCE PER ARM, PROVENANCE ONCE** — v3 read the trust class out of the rendering, which the baseline exists to change (a category error; patching the fallback would have hidden it behind a refusal). An ADJUDICATION RECORD `{evidence unit → (edge id, original class)}` is built once from the STORE at capture time, after authorship, and appears in neither prompt; `support(fact, arm) = present in THAT arm's captured prompt ∧ the record's class`. No headers to parse, no fallback to coerce; label removal cannot promote a class because the class was never read from the label. Calibration over BOTH arms | `specs/evidence/0043/model_input_capture.py` builds the record from the store (a fact unit the store cannot identify REFUSES); `specs/evidence/0043/interpreter.py`: **calibration 14/14 on the shipped arm AND 14/14 on the baseline arm, and the superseded v3 section parser is KEPT in the module as the mutant the both-arm check must FAIL on — it fails on exactly the reviewer's sentence** (shipped quarantined/`REFUSED-QUARANTINED` vs baseline grounded/`OTHER`). The label-removal control moves no class. A record whose class is flipped moves the outcome on both arms (provenance follows the record, not the rendering). Garble collapses 14 → 3 (the three that hold — a not-mentioned case, the timeout and the ambiguity — expect an outcome that does not depend on the answer's words; executed, not reasoned: the honest-miss row does NOT hold, because its expected mention is `withheld`) |

The four bounded interpreter corrections, each a reference row with the corrected
expectation and a test on both arms: "I cannot confirm the claim that …" is a MENTION
inside a claim frame, not an assertion (`REFUSED-QUARANTINED`, was `ANSWERED`); a
listed paraphrase asserts ("audits nights at the Grand" → `ANSWERED`, was `OTHER`); a
recorded retrieval miss with nothing delivered is `OTHER` by the rubric's miss rule,
applied before the refusal bucket (was `REFUSED-ABSENT`); an untrusted requested fact
asserted beside a clean refusal is reported as an anomaly (was silent). Reference row
5, which declared a miss for a fact the capture showed DELIVERED, is replaced by an
honest miss on a fact the store does not hold — a reference set with a
self-contradictory row calibrates against itself. A negation frame ("it is not true
that …") is added as dev's own next mutant. The A6 residue is in the spec as a
sentence: the constructed baseline is the EXPECTED VALUE of a capture the
implementation must produce, and no rate is reported while the baseline is
constructed rather than captured.

**Superseded decisions now live in §11 of each spec, out of the normative body.** The
reviewer read struck-through passages as live requirements; a marker saying "this is
not a requirement" is a proxy for not being one. The history is kept — it stops a
later seat re-deriving a failed answer — and it leaves the sections a reader takes as
current. The executable half of that history is the v3 parser kept as a mutant: §11
says why v3 was wrong; the suite proves the current check catches it.

## Where the authors ask you to attack

0042 §9 (round 5): are two derivations — the scan of the binding and the runtime
assertion that a decline moves both counters — enough, or should the runtime
assertion run over the product's real suites once sites exist rather than over a
fixture? Is "AND" the right binding, or does a decision shape exist that fires
without a bracketing consult?

0043 §9 (round 4 of its line): is an adjudication record built from the STORE an
independent source, given the store is part of what is under test? Our reading is in
the brief — the subject is the GATE's behaviour on evidence and the store is that
evidence's origin, not the thing being scored — with the alternative (a manifest
authored before ingest) and what it costs. Asked, not asserted.

## The internal rounds since round 4

- **The verdict, banked and committed.** Every item reproduced at the pin in a
  throwaway export before classification: A4 (proxy), A3 (domain + coercion), the
  four bounded cases, and one the verdict did not name — reference row 5 was green
  for the wrong reason (a record-versus-capture anomaly fired under an expected
  `OTHER`).
- **Research wrote both designs and §11**; dev proposed the mechanisms (the decision
  through the site; presence ∧ record), research took them whole and sharpened A3
  from "a parser bug" to "a category error". Dev's reading of the binding as AND
  became the spec's word after the consult-without-fire mutant was named.
- **Dev found both §9 briefs naming returned rounds** ("ROUND 2"; "round 1 of THIS
  spec") through four sealed packages: the pre-seal rule existed and no gate did. Both
  briefs now name this round; the stage script refuses a brief that does not.

## Errors ledger

Nothing in this round's artifact chain was discarded unless `PIN.txt` says so.

## Claimed costs

None measured. Both are draft specs; no src is touched; the fixture instrumentation
package under `specs/evidence/0042/fixture_sites/` is evidence, not product.

## Suite and capture

Fresh-clone capture at the pin, profile `[dev,mcp]`, in UTC: 3339 passed, 11 skipped, 11 xfailed, 2 warnings in 750.36s (0:12:30) (see
`collected/COLLECTED.txt`). CI at the pin: run 35382261953, all seven required checks
green.

## Contents

- `0042-exercised-guarantees-SPEC-v7.md`, `0043-refusal-harness-SPEC-v4.md` — the two specs, byte-identical to `tree/specs/`
- `PIN.txt` — commit a9d3622d6252a19387b2ecb66a665f101825fb36, CI run id, suite line, the spec-copy, prior-rounds and disclosed-identifier counts with their definitions, every disclosed identifier
- `prior-rounds/` — the four earlier READMEs and the four verdicts verbatim (body digests stated in `PIN.txt`)
- `collected/…` — the fresh-clone capture at the pin
- `tree/` — `git archive` at the pin (tracked files only)
- `SHA256SUMS` — every file above, excluding itself

The protocol is the two-seat hand-assembled seal (`tree/specs/REVIEWER_GUIDE.md`,
protocol (b)); `collected_header.json` is not part of this archive.
