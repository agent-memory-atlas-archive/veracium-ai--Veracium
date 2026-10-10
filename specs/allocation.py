#!/usr/bin/env python3
"""The spec-number ALLOCATION registry — one authoritative table of every
number: what holds it, its status, and which claims are RESERVATIONS rather
than drafts. Renders `specs/ALLOCATION.md`; `--check` refuses a stale render;
`tests/test_spec_allocation.py` refuses any NEW collision.

Why this exists (2026-09-06, external round 9 of the procedural design
round): the numbers 0033–0036 had been reserved for another arc two days
earlier, and the only record of that reservation was a sentence inside a
paragraph of a coordination-file row for a third spec. Two seats then
drafted, reviewed seven versions of, and merged `specs/0033-…` under the
reserved number without either checking, because there was nothing to check
against — the same defect class as a phantom citation: a claim with no
registry. The HOLDERS below are DERIVED from the tree (never hand-listed);
the RESERVATIONS are the one hand-maintained part, which is why each carries
its source and date and why the gate reads them as data.

Contested cells are RECORDED, not hidden: a collision that exists today is
named with its date and the ruling it awaits, and the gate refuses only a
collision that is not so recorded — the registry names the known state and
blocks the next one.

THE PEER TREE (2026-10-10). The number 0048 was claimed three times: twice
by drafts in the research tree (one with a built review package) and once by
a spec dispatched for review the same day. Every claim was made in good faith
from this registry, which saw only `specs/` — a numbered draft that lives
only in the peer seat's tree was neither a holder nor a reservation. So a
draft now claims its number WHERE IT IS WRITTEN: `peer_problems()` scans the
peer tree (named by the environment or this clone's git config, never by a
path in code) with the same keys as `specs/`, `next_number()` steps past
every peer claim, and `--next` REFUSES to answer without the peer unless
told `--repo-only`. The render stays repo-only so the rendered table cannot
depend on which machine wrote it; the peer scan is a separate gate
(`--peer-check`), run by every seal's stage script.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
#: `VERACIUM_SPECS_DIR` points the registry at another clone's live specs/
#: (the peer seat runs an exported copy of this script against dev's tree,
#: read-only, to see a spec adopted but not yet committed). Under it the
#: render is refused: a table derived from another tree is not this tree's.
SPECS_OVERRIDE = os.environ.get("VERACIUM_SPECS_DIR")
SPECS = pathlib.Path(SPECS_OVERRIDE) if SPECS_OVERRIDE else ROOT / "specs"
OUT = ROOT / "specs" / "ALLOCATION.md"
STATUS = re.compile(r"^Spec-Status:\s*(\S[^\n]*)$", re.M)
NUMBER = re.compile(r"^(\d{4})-")

#: RESERVATIONS — numbers claimed by an arc that has not drafted them. Each
#: carries WHO banked it, WHEN, WHERE (the carrier a reader can open), the
#: gate that must open before drafting, and — because a reservation is a
#: claim about the FUTURE that nothing in the tree can falsify — a REVIEW
#: TRIGGER: the date by which, or the condition under which, the claim is
#: reviewable. A reservation past its review is NAMED for the owner by
#: `allocation_problems()`, never auto-released (releasing is an allocation
#: decision, the owner's). Without the trigger a reservation whose arc dies
#: blocks its numbers forever with no pressure but memory (research,
#: 2026-09-06). Released only by an owner ruling recorded here.
RESERVATIONS: list[dict] = [
    {
        "range": ("0033", "0036"),
        "holder": "the self-learning concept review's decomposition "
                  "(0033 receipts / 0034 origin / 0035 admission / 0036) — LIVE, not "
                  "dormant: the concept note reached a second external review "
                  "2026-09-04 ('ready for owner adjudication, not yet for normative "
                  "drafting'); the owner approved its modifications and workflow, "
                  "fixing the sequence procedural memory → harness → self-learning; "
                  "and `0035 Requires: 0033 AND 0034` is an externally reviewed "
                  "dependency stated BY NUMBER — the numbers are load-bearing",
        "banked_by": "research",
        "banked_on": "2026-09-04",
        "carrier": "COORDINATION.md — a note inside the 0031 dev-queue row "
                   "(the reason this registry exists)",
        "gate": "ten owner decisions gate any drafting there (one partly taken: "
                "procedure-shaped records categorically outside 0035 v1's effect "
                "vocabulary)",
        "review_by": "2027-01-04",   # set by research, the banker, 2026-09-06 —
                                     # replacing dev's provisional 30-day date, which
                                     # would have fired mid-stage-one and trained
                                     # readers to ignore it
        "review_when": "self-learning is THIRD in the owner-approved sequence "
                       "procedural → harness → self-learning; review when the HARNESS "
                       "stage begins (the arc becomes next and its numbers are wanted), "
                       "or if the owner abandons or reorders the sequence, or by "
                       "review_by — whichever is first",
        "released": None,
    },
]

#: CONTESTED — a number both held by a file in the tree and inside a live
#: reservation, recorded with its date and the decision it awaits. The gate
#: refuses a collision NOT listed here; listing one is a disclosure, not a
#: permission.
CONTESTED: dict[str, dict] = {}   # 0033's collision CLEARED by the owner's renumber ruling (2026-09-06 → 0037);
                                  # the history lives in the commit that moved the file and in COORDINATION

#: SPENT — numbers consumed by a proposal that never entered this tree (a
#: withdrawn or rejected candidate whose record lives in the research tree).
#: Neither a holder (no file here) nor a reservation (no future claim), yet
#: `next_uncontested()` must never hand the number out again: a later spec
#: under a withdrawn number would collide with the record that explains why
#: the idea was not taken. Each entry carries the ruling, its date and where
#: the record lives (in prose — the file is not in this tree); a SPENT number
#: that a tree file also holds is a duplicate and the gate refuses it.
SPENT: dict[str, dict] = {
    "0040": {
        "what": "procedural text at the choke point — the store inferring "
                "content kind from text shape (research's proposal)",
        "ruling": "Quentin, 2026-09-08, \"Withdraw 0040 with the reasoning "
                  "recorded\" (ledger [Quentin, research session] 19:40Z): Q1 "
                  "answered NO — the store does not infer kind from text shape",
        "record": "the withdrawn proposal in the research tree, Spec-Status: "
                  "withdrawn, kept as a record so the next person with the idea "
                  "finds the argument rather than making it again",
        # every carrier of the reasoning is OUTSIDE this tree (the proposal in
        # the research tree, the ruling in COORDINATION), so `record` is a
        # pointer this gate cannot verify. A pointer that can dangle carries
        # its own GIST: if the record moves, a reader loses the argument's
        # detail, not its conclusion (research, 2026-09-08).
        "gist": "Q1: may the store infer content kind from text shape? NO. "
                "0037's recognition rule (`matches_executable_detail`) is safe "
                "because §4a-ii runs it as the LAST conjunct behind `stamp "
                "consistent`, inside the set a host already declared "
                "procedural — a false positive there withholds one description. "
                "The same function outside the declared set suppresses "
                "something a user asserted: identical code, categorically "
                "different blast radius, and the difference is in what the rule "
                "is allowed to decide, not in the rule. The §1 hazard stands "
                "(procedural text under an ordinary relation still renders as "
                "fact): the guarantee is about DECLARED provenance, not content "
                "safety. The real lever is adoption of `record_procedure`, not "
                "inference.",
        "spent_on": "2026-09-08",
    },
}


#: PEER_CONTESTED — a number claimed by two or more DIFFERENT spec titles
#: across the two trees, recorded with the exact set of titles, its date and
#: the ruling it awaits. The record covers exactly the titles it names: a
#: further title on the same number is a new collision and refused, and a
#: record whose collision is gone is stale and refused.
PEER_CONTESTED: dict[str, dict] = {}

#: The keys a document claims a number by, in either tree. A file named
#: `NNNN-…` claims NNNN when, within its first HEAD_LINES lines, it carries
#: a spec heading (`# Feature spec:` or `# Feature spec NNNN:` — that claim
#: has a TITLE, compared across claims) or a `Spec-Status:` line (a
#: withdrawn draft rewrites its heading and keeps its status: that claim
#: BLOCKS the number and takes no part in the title comparison). Anything
#: else named `NNNN-…` — rulings, legs, dated scans — is an artifact ABOUT a
#: number or no number at all, and claims nothing. A heading below line
#: HEAD_LINES is not seen; that bound is the key's stated limit.
HEAD_LINES = 15
HEADING = re.compile(r"^# Feature spec(?: (\d{4}))?:\s*(\S.*)$")
STATUS_LINE = re.compile(r"^Spec-Status:")


def norm_title(raw: str) -> str:
    """A title's identity: the heading text before its subtitle (the first
    spaced dash), without markup, lower-cased — so a spec's versions, whose
    subtitles and emphasis drift, are one title."""
    t = raw.replace("`", "").replace("*", "").strip()
    t = re.split(r"\s+[—–-]\s+", t, maxsplit=1)[0]
    return t.strip().lower()


def file_claim(path: pathlib.Path, label: str) -> dict | None:
    """The claim one `NNNN-…` document makes, or None."""
    m = NUMBER.match(path.name)
    if not m:
        return None
    try:
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:HEAD_LINES]
    except OSError:
        return None
    heading = next((h for h in (HEADING.match(x) for x in head) if h), None)
    status = any(STATUS_LINE.match(x) for x in head)
    if not heading and not status:
        return None
    return {"number": m.group(1), "file": label,
            "title": norm_title(heading.group(2)) if heading else None,
            "heading_number": heading.group(1) if heading else None}


class PeerTreeError(Exception):
    """The peer tree is configured but cannot be read as a git work tree."""


def peer_tree() -> pathlib.Path | None:
    """The peer seat's tree: `VERACIUM_PEER_TREE`, else this clone's
    `git config --local veracium.peerTree`. No default: a path in code is a
    path only one machine has. `VERACIUM_PEER_TREE=` (set, empty) is an
    explicit "none", so a test can see the unconfigured case in any clone."""
    if "VERACIUM_PEER_TREE" in os.environ:          # set and EMPTY means "no peer", over the git config
        env = os.environ["VERACIUM_PEER_TREE"]
        return pathlib.Path(env).expanduser() if env else None
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "config", "--local", "--get", "veracium.peerTree"],
                           capture_output=True, text=True)
    except OSError:
        return None
    return pathlib.Path(r.stdout.strip()).expanduser() if r.returncode == 0 and r.stdout.strip() else None


def peer_claims(peer: pathlib.Path) -> list[dict]:
    """Every claim in the peer tree, over the files git sees there —
    tracked AND untracked-not-ignored, because a draft written and not yet
    committed is exactly the race this scan exists for."""
    r = subprocess.run(["git", "-C", str(peer), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                       capture_output=True)
    if r.returncode != 0:
        raise PeerTreeError(f"{peer} is not a readable git work tree: "
                            f"{r.stderr.decode(errors='replace').strip()}")
    claims = []
    for rel in sorted(set(r.stdout.decode(errors="replace").split("\0")) - {""}):
        f = peer / rel
        if f.suffix == ".md" and NUMBER.match(f.name) and f.is_file():
            c = file_claim(f, f"peer:{rel}")
            if c:
                claims.append(c)
    return claims


def repo_claims() -> list[dict]:
    return [c for c in (file_claim(f, f"specs/{f.name}") for f in sorted(SPECS.glob("[0-9][0-9][0-9][0-9]-*.md"))) if c]


def peer_problems(peer: pathlib.Path) -> list[str]:
    """Every collision the two trees make together. Empty means: no number
    carries two different titles unless PEER_CONTESTED records exactly that
    set; no claim takes a SPENT number with a title or sits in a live
    reservation; no heading's own number disagrees with its filename; and no
    status-only claim blocks a number nothing else accounts for."""
    try:
        peer_c = peer_claims(peer)
    except PeerTreeError as e:
        return [f"peer tree: {e}"]
    problems: list[str] = []
    claims = repo_claims() + peer_c
    held = {r["number"] for r in holders()}
    live = [x for x in RESERVATIONS if x.get("released") is None]
    by_number: dict[str, list[dict]] = {}
    for c in claims:
        by_number.setdefault(c["number"], []).append(c)
        if c["heading_number"] and c["heading_number"] != c["number"]:
            problems.append(f"{c['file']}: its heading says {c['heading_number']} but its filename says {c['number']}")
    for c in peer_c:
        for x in live:
            if _in_range(c["number"], x["range"]):
                problems.append(f"{c['file']} claims {c['number']} inside the live reservation "
                                f"{x['range'][0]}–{x['range'][1]} ({x['holder']})")
        if c["number"] in SPENT and c["title"]:
            problems.append(f"{c['file']} claims SPENT number {c['number']} with a spec heading — a withdrawn number was reused")
    for n, cs in sorted(by_number.items()):
        titles = {c["title"] for c in cs if c["title"]}
        if len(titles) > 1:
            rec = PEER_CONTESTED.get(n)
            if rec is None or set(rec.get("titles", ())) != titles:
                where = "; ".join(f"{t!r} in {', '.join(c['file'] for c in cs if c['title'] == t)}" for t in sorted(titles))
                problems.append(f"number {n} is claimed by {len(titles)} different specs and "
                                f"{'the record names a different set' if rec else 'is NOT recorded'}: {where}")
        if not titles and n not in held and n not in SPENT and n not in PEER_CONTESTED:
            problems.append(f"number {n} is blocked by a status-only draft ({', '.join(c['file'] for c in cs)}) "
                            f"that no spec, SPENT entry or record accounts for — record it as SPENT, or give it its heading")
    for n, rec in PEER_CONTESTED.items():
        titles = {c["title"] for c in by_number.get(n, []) if c["title"]}
        if len(titles) < 2:
            problems.append(f"PEER_CONTESTED {n} records a collision the trees no longer carry — stale entry; remove it")
        for key in ("titles", "since", "awaits"):
            if not rec.get(key):
                problems.append(f"PEER_CONTESTED {n}: missing {key}")
    return problems


def next_number(peer: pathlib.Path | None, after: str | None = None) -> str:
    """The number a new spec may take: above every number held in specs/,
    SPENT, or claimed in the peer tree (heading or status), stepped past
    live reservations and SPENT numbers. `peer=None` is the repo-only answer
    (`--repo-only`), which can hand out a number a peer draft already holds."""
    tops = [after or "0000"] + [c["number"] for c in peer_claims(peer)] if peer is not None else [after or "0000"]
    return next_uncontested(max(tops))


def holders() -> list[dict]:
    """Every number the TREE holds — derived, never hand-listed."""
    rows = []
    for f in sorted(SPECS.glob("[0-9][0-9][0-9][0-9]-*.md")):
        m = NUMBER.match(f.name)
        if not m:
            continue
        text = f.read_text(encoding="utf-8")
        st = STATUS.search(text)
        title = text.splitlines()[0].lstrip("# ").replace("Feature spec: ", "", 1).strip() if text else ""
        rows.append({"number": m.group(1), "file": f.name,
                     "status": st.group(1).strip() if st else "MISSING",
                     "title": title})
    return rows


def _in_range(n: str, rng: tuple[str, str]) -> bool:
    return rng[0] <= n <= rng[1]


def _today() -> str:
    """ISO date, UTC; a module-level indirection so the gate's test can move
    the clock without patching the standard library."""
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).date().isoformat()


def allocation_problems() -> list[str]:
    """Every defect the registry can see. Empty means: no duplicate number in
    the tree, no UNRECORDED collision with a live reservation, no CONTESTED
    entry that is stale (its file gone or its reservation released), and
    every reservation carries its provenance."""
    problems: list[str] = []
    rows = holders()
    seen: dict[str, str] = {}
    for r in rows:
        if r["number"] in seen:
            problems.append(f"duplicate number {r['number']}: {seen[r['number']]} and {r['file']}")
        seen[r["number"]] = r["file"]
        if r["status"] == "MISSING":
            problems.append(f"{r['file']}: no Spec-Status line")
    live = [x for x in RESERVATIONS if x.get("released") is None]
    today = _today()
    for x in RESERVATIONS:
        for key in ("range", "holder", "banked_by", "banked_on", "carrier", "gate", "review_by", "review_when"):
            if not x.get(key):
                problems.append(f"reservation {x.get('range')}: missing {key} — a reservation must carry what would end it")
        if x.get("released") is None and x.get("review_by") and x["review_by"] < today:
            problems.append(
                f"reservation {x['range'][0]}–{x['range'][1]} is PAST REVIEW ({x['review_by']}; {x['review_when']}) — "
                f"named for the owner: release, renew with a new review_by, or draft")
    for r in rows:
        for x in live:
            if _in_range(r["number"], x["range"]) and r["number"] not in CONTESTED:
                problems.append(
                    f"{r['file']} takes number {r['number']} inside the live reservation "
                    f"{x['range'][0]}–{x['range'][1]} ({x['holder']}) and is NOT recorded as "
                    f"contested — record it or renumber")
    for n, s in SPENT.items():
        for key in ("what", "ruling", "record", "gist", "spent_on"):
            if not s.get(key):
                problems.append(f"SPENT {n}: missing {key} — a spent number must carry the ruling that spent it "
                                f"and the gist of its reasoning (its record lives outside this tree)")
        if n in seen:
            problems.append(f"SPENT {n} is also held by {seen[n]} in the tree — a withdrawn number was reused")
    for n, c in CONTESTED.items():
        if n not in seen:
            problems.append(f"CONTESTED {n} names no file in the tree ({c['file']}) — stale entry")
        elif seen[n] != pathlib.Path(c["file"]).name:
            problems.append(f"CONTESTED {n} names {c['file']} but the tree holds {seen[n]}")
        if not any(_in_range(n, x["range"]) for x in live):
            problems.append(f"CONTESTED {n} is inside no live reservation — stale entry; remove it")
    return problems


def next_uncontested(after: str | None = None) -> str:
    """The first number above the tree's highest (or `after`) that no live
    reservation covers and no SPENT entry consumed — the answer to "what
    number may a new spec take?"."""
    rows = holders(); top = max([r["number"] for r in rows] + list(SPENT) + [after or "0000"])
    n = int(top) + 1
    live = [x for x in RESERVATIONS if x.get("released") is None]
    while any(_in_range(f"{n:04d}", x["range"]) for x in live) or f"{n:04d}" in SPENT:
        n += 1
    return f"{n:04d}"


def render() -> str:
    rows = holders()
    out = ["# Spec allocation — every number, its holder, its status, and the reservations",
           "",
           "*Generated by `specs/allocation.py --write`; `--check` refuses a stale copy; "
           "`tests/test_spec_allocation.py` refuses any NEW collision. Holders are DERIVED "
           "from the tree; reservations are the hand-maintained part and carry their "
           "provenance. A new spec takes `allocation.py`'s next uncontested number.*",
           "",
           "## Held in the tree", "",
           "| number | file | status | title | note |", "|---|---|---|---|---|"]
    for r in rows:
        note = ""
        if r["number"] in CONTESTED:
            c = CONTESTED[r["number"]]
            note = f"**CONTESTED since {c['since']}** — inside a live reservation; awaits {c['awaits']}"
        out.append(f"| {r['number']} | `{r['file']}` | `{r['status']}` | {r['title']} | {note} |")
    out += ["", "## Reservations (claimed, not drafted)", "",
            "| range | holder | banked by | on | carrier | gate before drafting | review by / when | released |",
            "|---|---|---|---|---|---|---|---|"]
    for x in RESERVATIONS:
        out.append(f"| {x['range'][0]}–{x['range'][1]} | {x['holder']} | {x['banked_by']} | {x['banked_on']} | "
                   f"{x['carrier']} | {x['gate']} | {x.get('review_by', '—')} / {x.get('review_when', '—')} | {x['released'] or '—'} |")
    out += ["", "## Spent outside the tree (withdrawn or rejected before entering it)", "",
            "| number | what | ruling | where the record lives | gist of the reasoning | spent on |", "|---|---|---|---|---|---|"]
    for n, s in SPENT.items():
        out.append(f"| {n} | {s['what']} | {s['ruling']} | {s['record']} | {s['gist']} | {s['spent_on']} |")
    out += ["", "## Collisions across the two trees, recorded", "",
            "*A number claimed by two different spec titles across `specs/` and the peer seat's tree "
            "(`allocation.py --peer-check`). Listing one is a disclosure, not a permission.*", ""]
    if PEER_CONTESTED:
        out += ["| number | titles | since | awaits |", "|---|---|---|---|"]
        for n, rec in sorted(PEER_CONTESTED.items()):
            out.append(f"| {n} | {'; '.join(rec['titles'])} | {rec['since']} | {rec['awaits']} |")
    else:
        out.append("none")
    out += ["", f"**Next number from this tree alone:** `{next_uncontested()}`. *A new spec takes its number "
            "from `allocation.py --next`, which also steps past every draft in the peer seat's tree and "
            "refuses to answer without it — run it before the first numbered file is created, in either tree.*", ""]
    problems = allocation_problems()
    out += ["## Registry state", "", "no problems" if not problems else "\n".join(f"- {p}" for p in problems), ""]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if SPECS_OVERRIDE and ("--write" in argv or "--check" in argv):
        print(f"REFUSED: VERACIUM_SPECS_DIR={SPECS_OVERRIDE} — the rendered table is this tree's; "
              "use --next or --peer-check against another specs/")
        return 2
    text = render()
    if "--write" in argv:
        OUT.write_text(text, encoding="utf-8"); print(f"wrote {OUT.relative_to(ROOT)}")
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("ALLOCATION.md is stale — run allocation.py --write"); return 1
        print("ALLOCATION.md is current")
    problems = allocation_problems()
    wants_peer = "--peer-check" in argv or ("--next" in argv and "--repo-only" not in argv)
    peer = peer_tree()
    if wants_peer:
        if peer is None or not peer.is_dir():
            print("REFUSED: " + ("no peer tree configured" if peer is None else f"the peer tree {peer} does not exist")
                  + " — set VERACIUM_PEER_TREE, or `git config --local veracium.peerTree <path>` in this clone. "
                  "A number taken without the peer tree is how 0048 was claimed three times; "
                  "`--next --repo-only` answers from specs/ alone and says so.")
            return 2
        problems += peer_problems(peer)
        print(f"peer tree: CHECKED {peer}")
    elif "--next" in argv:
        print("peer tree: NOT CHECKED (--repo-only) — the number below ignores every draft outside specs/")
    for p in problems:
        print("PROBLEM:", p)
    if "--next" in argv:
        print(next_number(None if "--repo-only" in argv else peer))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
