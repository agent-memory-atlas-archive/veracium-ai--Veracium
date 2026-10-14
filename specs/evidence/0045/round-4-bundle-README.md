<!-- TERMINAL RECORD — the round-4 review bundle README of specs 0045 and 0047 (with the 0008, 0019 and 0041 amendments), byte-copied
UNMODIFIED from the ACCEPTED package (sha256 f16c0487b62db68fc66702841527c92fb9fa957ab915088af45866e0c5e2d1f6
@ af1e564ac12adf620890d83afc255bb5b812e6f9, CI 38457338568) on 2026-10-14, after the 2026-10-13 verdict in which
the reviewer accepted 0045 v1.11 and 0047 v1.14 jointly at the design level and froze their invariant surfaces. It is the one carrier holding the four rounds' dispositions,
the disclosed hotfix and the errors ledger together; the version cells carry lineage, not the reviewer's
dispositions. The package remains the archive; this copy is the record. THE BYTES AFTER THE BLANK LINE FOLLOWING
THIS COMMENT equal the packaged README:
sha256 ec69907e826442fe27b362a65b2d448af8b2447f082957e2dca783f434ef8c48, 11951 bytes — verifiable forever against the archived package.
On the tarball: tar xzf <pkg> -O 0045-0047-round4-review-package/README-0045-0047-round4-bundle.md | sha256sum
Here: sed '1,/^-->$/d' <this file> | tail -n +2 | sha256sum   (the comment closes on its own line)
-->

# 0045 grounding and 0047 the right of reply, with amendments to 0008, 0019 and 0041 — round-4 external review bundle

Assembled 2026-10-13 by dev, read before the seal by research. **This is the fourth external round, at the design level:
round 3 returned the joint package for two bounded import-construction corrections (R3-01, R3-02) and bounded carrier
and text corrections, closed 0045's attestation finding (R2-01), and retained the 0019 amendment's acceptance. The
question is whether 0045 v1.11, 0047 v1.14 and the 0008 and 0041 amendments close R3-01 and R3-02 inside the finite-review
boundary round 3 set, so that they can be ACCEPTED and their implementation may follow.** No product code for the five
documents ships with it: the pinned tree carries the two draft specs and their evidence. The one change to `src/`
since round 3's pin is the 0041 hotfix described below.

**Canonical artifacts:** `specs/0045-declarative-grounding.md` and `specs/0047-subject-reply.md` at the pinned commit
(`PIN.txt`); on any doubt the repo wins. The copies here (`0045-declarative-grounding-SPEC-v1.11.md`,
`0047-subject-reply-SPEC-v1.14.md`) are byte-identical to `tree/specs/`.
**The three amendments are deliberately NOT in the tree**: `0008-request-registry-AMENDMENT-v1.9.md`,
`0019-nonuser-refusal-AMENDMENT-v2.2.md` and `0041-replies-AMENDMENT-v1.13.md`. Each amends an ACCEPTED spec, so each
travels beside the tree, is normative only on acceptance, and is then folded into its spec as a new version. Read each
against its accepted base in `tree/specs/` (`0008-staleness-clearing.md`, `0019-ungrounded-flag.md`,
`0041-targeted-redaction.md`) as it stands at the pin. Their sha256 digests and ids are in `PIN.txt`.

**The 0008 amendment is shared.** It travels at the same digest in the 0044 round-4 package, which this reviewer also
has. **The 0019 amendment is unchanged since round 3**, which retained its acceptance; its diff from the accepted v2.1
is `collected/0019am-v2.1-to-v2.2.diff`, and its fold waits for 0045's acceptance because the accepted text cites
0045's states.

## What changed since round 3

Each document's **§9** carries the per-finding closure ledger. In short:

- **R3-01, notice treatment and portable act replay did not compose** (0047 §4f; the 0008 amendment §6e; the 0041
  amendment §4). HELD is the staged union, so conflicting identities within one unit are seen; equality is on the
  canonical TREATED projection; a notice authorizes one transition, of content carriers only; coverage is all or
  nothing per row. INV-I4..I6, RR8, RR9.
- **R3-02, chronology read an intermediate state** (0047 §4f; the 0008 amendment §6f). Validation runs over the merged
  history, with act and resolve references remapped first; ties, second resolves and unknown orders refuse. INV-R23,
  INV-Q10.
- **The bounded corrections:** the recorded origin (the trust label is the destination's, excluded from the projection
  and never changed by a replay); inspection ordering is a PRODUCT contract, and a cross-origin position sort is
  display only; one snapshot per inspection; the complete migration carrier inventory, with legacy positions unknown;
  `request_redacted` precedes replay for every verb, undo included (INV-Q7); §6's gate wording (MODEL checks at the
  design gate, PRODUCT tests at implementation); and the carrier census's render-or-withhold wording, fixed in the
  census tool.
- **0045: R2-01 closed at round 3,** with no independent 0045 blocker. 0045 folds only the bounded corrections: no
  challenge-gate privilege, everywhere; the guarantee wording removed (H1's figure is a fixture measurement); a durable
  version carrier for the attestation label (`attv`, the owner's ruling; INV-G13; ATTEST-3 itself unchanged); and §6's
  gate wording. Its §2c-ii was re-run at `f98a3a0`, with no rule change. The ATTEST evidence is round 3's, re-run at
  the pin in `collected/attest-results.txt`.
- **The 0019 amendment:** round 3 retained its acceptance on INV-N1–N4 and confirmed correction #4; it travels at the
  same digest.
- **The model.** Reference model II encodes R3-01, R3-02 and the notice rules below, and counts a mutant killed only
  when its owning invariant returns False with the mutated function reached.

## The notice-binding hotfix: the one change to `src/` since round 3's pin

While reference model II was being encoded for this round, it found a defect in accepted 0041 as implemented: an
imported redaction notice bound to its target by id alone. An untrusted (default-mode) import file carrying only a
notice permanently redacted the user's own held fact; for an absent id it left a standing notice that refused the
user's own later write; and it redacted a later arrival of that id. The code was on main since `8ea59e7` (notice
import) and was never in a release. It was fixed in `98327c2` on the owner's rulings: on the default path, a notice
binds only to a record the import itself inserts; in both modes it applies only where a record shows the redaction (the
file's copy, or, on a restore with no copy, the held record); a file carrying a notice's record unredacted refuses whole
wherever that record would be admitted under it, unless this store already holds that notice as applied. The fix is recorded as 0041 v15.6 (`b1050f5`),
with internal finding 0041-PA1 and a 13-mutant table (`tree/specs/evidence/0041/mutation-table.json`, every mutant
killed). It changed four files, `src/veracium/cli.py`, `src/veracium/portability.py`, `src/veracium/redaction.py` and
`src/veracium/store/sqlite.py`; nothing else in `src/` moved since round 3's pin.

**Round 4's text designs beyond the hotfix**
(the 0041 amendment here, and the 0008 amendment, which travels in both packages): a notice over a target this store already holds is PENDING in
a default import until the user calls `confirm_notice`; wherever content would land under a notice, the unit refuses;
and no rule reads a notice's origin, so the 0006 amendment that would have licensed origin binding is withdrawn. The
hotfix's one rule with no round-4 counterpart is its default-path origin check: fail-closed hotfix behaviour that
round 4 supersedes.

**How the 0041 amendment got here.** Round 3 returned v1.3. On the way to v1.13 it first bound standing notices by
origin, then added the fixed point and made an origin mismatch pending, and then, on the owner's rulings, refused
wherever content would land and dropped origin binding, with the 0006 amendment that had licensed it. Each step is in
its Version cell, and its §9 states the delta from the hotfix.

## Where the authors ask you to attack

Each document's own brief is its **§9**. Every claim about reach carries its command in §2c-ii. Research re-ran every
READ row of both packages' documents except the 0019 amendment's at `f98a3a0`, after the hotfix; `src/` is unchanged from there
to the pin. The stage re-ran research's sweep at the pin (`collected/reach-sweep.txt`, identical to research's run at
`f98a3a0`), and itself re-ran every row the sweep does not judge (the EXECUTED rows, and the 0019 amendment's), each
giving its recorded result.

## Errors ledger

**Found by the two seats before anything shipped.**

- **The 0041 defect above** was found by reference model II's round-4 encoding, not by a test.
- **The hotfix's first candidate had a hole (case 7),** found by research's probe of it: once the store admits the
  user's own later write under a hostile standing notice, the store's own export pairs that notice with the user's
  unredacted fact, so the export, imported elsewhere, would redact it. Closed by the fixed point: a notice applies
  only where the file carries its record already redacted.
- **A later candidate admitted and skipped:** it admitted a record that arrived unredacted beside its notice and
  skipped the notice, landing content its source says it redacted. The owner ruled that such a file refuses whole;
  round 4 keeps that rule, and the 0041 amendment's INV-RR14 names admit-and-skip among its mutants.
- **Two defects in round 3's reference model II,** found by its round-4 encoding: a resolve was bound to its challenge
  by row id, and an internal `#act:` key was used as an act's original request id. Both are fixed in the model.
- **A cross-worker test race:** two tests rewrote tracked evidence files that a parallel worker reads. The two-phase
  parallel suite exposed it when one run read a torn file; both tests now work on private copies.
- **Ambiguities in the amendments' text,** found while encoding model II against them: each was ruled in the text
  before adoption, and the 0041 and 0008 amendments' Version cells record the rulings.
- **The 0041 amendment once cited the defect as its precedent:** research's v1.4 said the amendment adds no authority,
  citing as precedent the very notice behaviour the hotfix removed. The claim was withdrawn at v1.5.
- **The hotfix's origin mutant survived its first mutation campaign:** the test meant to kill it could not tell the
  origin refusal from the fixed-point refusal, since both refused the same arrival. A cell only the origin check can
  fail (a redacted arrival from another origin) now kills it.

## Suite and capture

Fresh-clone capture at the pin, profile `[dev,mcp]`: 5722 passed, 12 skipped, 8 warnings in 2946.88s (0:49:06). Its interpreter, pytest and SQLite versions and its
clock's UTC offset are in `collected/COLLECTED.txt`, read from the capture, with the junit reconciled against the result
line and the resolved dependency versions beside it (`requirements-resolved.txt`).
CI at the pin: run 38457338568, all four jobs green (py3.14, the pydantic floor, spec reference, build & twine).
**The tree is the pin's**: `bash collected/tree_hash_witness.sh tree 3e424b713253bec38bb69df2f46ae7c988897a0f`.

## Contents

- `0045-declarative-grounding-SPEC-v1.11.md` — the draft spec at the pin, byte-identical to `tree/specs/`
- `0047-subject-reply-SPEC-v1.14.md` — the draft spec at the pin, byte-identical to `tree/specs/`
- `0008-request-registry-AMENDMENT-v1.9.md` — the amendment to accepted 0008, shared with the 0044 package; NOT in `tree/` (normative only on acceptance)
- `0019-nonuser-refusal-AMENDMENT-v2.2.md` — the amendment to accepted 0019 §4c (v2.1 accepted, plus correction #4; unchanged since round 3); NOT in `tree/`
- `0041-replies-AMENDMENT-v1.13.md` — the amendment to accepted 0041; NOT in `tree/`
- `PIN.txt` — commit and tree hash, CI run id, suite line, each amendment's sha256 and id, the change to src/ since round 3's pin, the predecessors (rounds 1, 2 and 3)
- `prior-rounds/` — round 1's README (`README-0045-0047-round1-bundle.md`) and verdict (`0045-0047-round1-verdict-verbatim.md`); round 2's README (`README-0045-0047-round2-bundle.md`) and verdict (`0045-0047-round2-verdict-verbatim.md`); round 3's README (`README-0045-0047-round3-bundle.md`) and verdict (`0045-0047-round3-verdict-verbatim.md`)
- `collected/` — the fresh-clone capture (`COLLECTED.txt`, `suite-run-raw.txt`, `suite-results.xml`, `requirements-resolved.txt`), `tree_hash_witness.sh`, the 0019 amendment's diff (`0019am-v2.1-to-v2.2.diff`), research's reach sweep run at the pin (`reach-sweep.txt`), and four runs made at the pin under the capture's interpreter: the reference model's result (`model-II-results.json`), the citation check over all five documents (`model-citations.txt`), the carrier census 0047 §4d cites as its surface list (`carrier-inventory.txt`), and the ATTEST evidence re-run (`attest-results.txt`: ATTEST-3 on H2 under both labellings, its mechanism mutants and regression gate, ATTEST-2 on H2, H1 as regression)
- `tree/` — `git archive` at the pin (tracked files only)
- `SHA256SUMS` — every file above, excluding itself

The protocol is the two-seat hand-assembled seal (`tree/specs/REVIEWER_GUIDE.md`, protocol (b));
`collected_header.json` is not part of this archive.
