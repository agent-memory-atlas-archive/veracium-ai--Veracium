<!-- TERMINAL RECORD — the round-4 review bundle README of spec 0044 (with the 0003, 0018 and 0008 amendments), byte-copied
UNMODIFIED from the ACCEPTED package (sha256 b06f700f19653c8671760b43741659d94c01e81c02437ee6d031cc9c740914b0
@ af1e564ac12adf620890d83afc255bb5b812e6f9, CI 38457338568) on 2026-10-14, after the 2026-10-13 verdict in which
the reviewer accepted 0044 v1.5 at the design level and froze its invariant surface. It is the one carrier holding the four rounds' dispositions,
the disclosed hotfix and the errors ledger together; the version cells carry lineage, not the reviewer's
dispositions. The package remains the archive; this copy is the record. THE BYTES AFTER THE BLANK LINE FOLLOWING
THIS COMMENT equal the packaged README:
sha256 c867c8ac0faa9f808fc20c245348f2ea691b36a33cb91c7bf688b6e09ff1ae27, 10791 bytes — verifiable forever against the archived package.
On the tarball: tar xzf <pkg> -O 0044-round4-review-package/README-0044-round4-bundle.md | sha256sum
Here: sed '1,/^-->$/d' <this file> | tail -n +2 | sha256sum   (the comment closes on its own line)
-->

# 0044 relation arity, stage 1, with amendments to 0003, 0018 and 0008 — round-4 external review bundle

Assembled 2026-10-13 by dev, read before the seal by research. **This is the fourth external round, at the design level:
round 3 returned 0044 v1.4 and the 0018 amendment v3 for bounded corrections (R3-01..R3-03), APPROVED the 0003
amendment's design on INV-O1–O10 with its activation held to 0044's, and returned the shared 0008 amendment under the
companion review. The question is whether 0044 v1.5 and the 0018 amendment v4 close R3-01..R3-03 inside the
finite-review boundary round 3 set, so that 0044 and its amendments can be ACCEPTED and their implementation may
follow.** No product code for 0044 or its amendments ships with it: the pinned tree carries the draft spec, its
reference model and its obligation map. The one change to `src/` since round 3's pin is the 0041 hotfix described
below.

**Canonical artifacts:** `specs/0044-relation-arity.md` at the pinned commit (`PIN.txt`); on any doubt the repo wins.
The copy here (`0044-relation-arity-SPEC-v1.5.md`) is byte-identical to `tree/specs/`. **The three amendments are
deliberately NOT in the tree**: `0003-contested-order-AMENDMENT-v1.5.md`, `0018-data-migration-AMENDMENT-v4.md` and
`0008-request-registry-AMENDMENT-v1.9.md`. Each amends an ACCEPTED spec, so each travels beside the tree, is normative
only on acceptance, and is then folded into its spec as a new version. Read each against its accepted base in
`tree/specs/` as it stands at the pin. Their sha256 digests and ids are in `PIN.txt`.

**The 0008 amendment is shared.** It travels at the same digest in the 0045–0047 round-4 package, which this reviewer
also has. It hosts the constructions both packages use (the request registry, the identity of an imported act or
outcome, and an act ordinal) and, at this round, the notice rules below; 0044's `Spec-Requires:` line names it.

## What changed since round 3

Each document's **§9** carries the per-finding closure ledger. In short:

- **R3-01, the lifetime construction missed same-id upserts.** §4f-ii now derives every lifetime transition from the
  persisted prior and new state at the emission choke point that every writer calls, the upsert included. At
  implementation the generated writer census gains a `lifetime` disposition per writer; nothing in `src/` changes for
  it at this pin. INV-A22.
- **R3-02, held outcome identity was not exact replay.** §4l: a canonical projection, one outcome per slot, and
  comparison decides replay (`undo_request_ref` excluded). An outcome's lifecycle STAGE is compared, never a store's
  clock; two different endings refuse; an ended episode is never revived. INV-A23.
- **R3-03, the model map overstated four rows.** The reference model and the 0018 amendment v4 now represent them:
  §4b.2's digest scope (an unrelated declaration change is admitted), §4c's carrier (`plan_written` is required, and
  the constructor's rejection matrix is stated), undo under redaction (the 0008 amendment §6g) and the erasure of both
  inventories (`refusal_inventory` is named and erased).
- **The 0018 amendment's clarifications.** `op_id` (the owner's ruling): a durable admission record binds the inputs
  digest and the mode; `op-id-conflict` is a tenth outcome; cumulative recovery is separate from the invocation's
  `committed`. §4e's diagnostic reads the inventory, not a time.
- **The 0003 amendment,** approved at round 3, carries only the two text corrections asked for before folding:
  INV-O7 reads the schema step's refusal inventory, and 0044 is named without a version.
- **The bounded text corrections:** stale cross-references and the travelling-amendment wording (the 0008 amendment
  §6e–§6g; 0029 v12 folded).
- **The shared 0008 amendment** closes the companion review's findings (HELD is the staged union; chronology is read
  over the merged history; `request_redacted` precedes replay for every verb, undo included) and carries round 4's
  notice rules.

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
(the 0041 amendment in the 0045–0047 package, and the 0008 amendment, which travels in both): a notice over a target this store already holds is PENDING in
a default import until the user calls `confirm_notice`; wherever content would land under a notice, the unit refuses;
and no rule reads a notice's origin, so the 0006 amendment that would have licensed origin binding is withdrawn. The
hotfix's one rule with no round-4 counterpart is its default-path origin check: fail-closed hotfix behaviour that
round 4 supersedes.

## Where the authors ask you to attack

Each document's own brief is its **§9**. Every claim about reach carries its command in §2c-ii. Research re-ran every
READ row of both packages' documents except the 0019 amendment's at `f98a3a0`, after the hotfix; `src/` is unchanged from there
to the pin, and the stage re-ran research's sweep at the pin: `collected/reach-sweep.txt`, identical to research's
run at `f98a3a0`. The sweep runs only READ rows: this package's EXECUTED rows (0044 rows 1–5, 7, 8; the 0003
amendment's rows 1–3) are re-run by nothing at the pin, as at round 3, and the shared 0008 amendment's are
re-run in the 0045–0047 package.

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
- **0044 and the 0018 amendment were re-issued the same day,** after reference model I was encoded against their
  first round-4 text: §4l compares an outcome's lifecycle STAGE, never the value of `undone_at` (a store's own clock),
  and two different endings refuse; the edge's removal ends an episode; `refusal_inventory` is named and erased; a call
  that writes nothing writes no admission record; an `op_id` outside its grammar is refused at entry. Each document's
  Version cell records it.

## Suite and capture

Fresh-clone capture at the pin, profile `[dev,mcp]`: 5722 passed, 12 skipped, 8 warnings in 2946.88s (0:49:06). Its interpreter, pytest and SQLite versions and its
clock's UTC offset are in `collected/COLLECTED.txt`, read from the capture, with the junit reconciled against the result
line and the resolved dependency versions beside it (`requirements-resolved.txt`).
CI at the pin: run 38457338568, all four jobs green (py3.14, the pydantic floor, spec reference, build & twine).
**The tree is the pin's**: `bash collected/tree_hash_witness.sh tree 3e424b713253bec38bb69df2f46ae7c988897a0f`.

## Contents

- `0044-relation-arity-SPEC-v1.5.md` — the draft spec at the pin, byte-identical to `tree/specs/`
- `0003-contested-order-AMENDMENT-v1.5.md` — the amendment to accepted 0003 §4c-ii, its design approved at round 3; NOT in `tree/` (normative only on acceptance)
- `0018-data-migration-AMENDMENT-v4.md` — the amendment to accepted 0018; NOT in `tree/`
- `0008-request-registry-AMENDMENT-v1.9.md` — the amendment to accepted 0008, shared with the 0045–0047 package; NOT in `tree/`
- `PIN.txt` — commit and tree hash, CI run id, suite line, each amendment's sha256 and id, the change to src/ since round 3's pin, the predecessors (rounds 1, 2 and 3)
- `prior-rounds/` — round 1's README (`README-0044-round1-bundle.md`), verdict (`0044-round1-verdict-verbatim.md`) and the authors' addendum (`0044-round1-authors-addendum.md`); round 2's README (`README-0044-round2-bundle.md`) and verdict (`0044-round2-verdict-verbatim.md`); round 3's README (`README-0044-round3-bundle.md`) and verdict (`0044-round3-verdict-verbatim.md`)
- `collected/` — the fresh-clone capture (`COLLECTED.txt`, `suite-run-raw.txt`, `suite-results.xml`, `requirements-resolved.txt`), `tree_hash_witness.sh`, the two reference models' results (`model-I-results.json` and `model-II-results.json`, each run at the pin under the capture's interpreter), the obligation map's run (`obligation-map.txt`), and research's reach sweep run at the pin (`reach-sweep.txt`)
- `tree/` — `git archive` at the pin (tracked files only)
- `SHA256SUMS` — every file above, excluding itself

The protocol is the two-seat hand-assembled seal (`tree/specs/REVIEWER_GUIDE.md`, protocol (b));
`collected_header.json` is not part of this archive.
