"""Package II's documents cite reference model II by invariant ("(model G2)"); this checks every such citation against
the model's own mutant table, data to data, so a spec row cannot cite a model check that does not run its mutant.

Usage: model_citations.py LABEL=PATH [LABEL=PATH ...]     e.g. 0045=specs/0045-declarative-grounding.md
LABEL is the prefix the model's mutant table uses for that document's rows ("0045", "0047", "0019am", "0041am").

For each document, from its §6 only (the heading `## 6.` up to the next `## `):
  * a ROW is a table line starting `| **INV-…**`; it CITES model G<n> wherever it says `model G<n>`;
  * a document-level citation `(its G<n>)` in §6 (the amendments' form: "dev's model II encodes the write path (its
    G8)") names the model's SCOPE for that document, not a citation on every row: at least one of its rows must be
    answered by a mutant owned by MODEL-G<n>, and a mutant answering any of its rows may be owned by it;
  * a sentence "its invariants G2–G5, G10, … are this spec's" CLAIMS those model invariants for the document.
Refusals (exit 1):
  FORWARD  a row that cites model G<n> has no mutant answering it that is owned by MODEL-G<n>; or a document-level
           `(its G<n>)` that no mutant owned by MODEL-G<n> answers on any row;
  REVERSE  a mutant answers a row that does not exist, or that does not cite the mutant's owner;
  CLAIM    a claimed model invariant that no row of the document cites;
  COUNT    a model-covered row NAMES more mutants than the model tags as answering it (a row is model-covered when it
           cites a model invariant, or, under a document-level scope, when any mutant answers it). Its mutant cell is
           the text after `Mutant:`/`Mutants:` up to the arrow, or the whole last cell where the table has no such
           label; names are separated by `;` or ` · `. A count, so it catches a named mutant the model never tagged
           (0045-0047 round 2, research's stage-1 read: two such were found by reading), not a mistagged one;
  KILL     a mutant answering a row is not killed by its owner (the model's own run decides);
  GRAMMAR  `model G` not followed by a number, or a §6 with no row at all — a citation this parser cannot read is a
           refusal, never a silent skip.
Only labels given on the command line are checked in the REVERSE direction, so the suite can check the two documents
in the tree while the stage checks all four.
"""
# Mutation-Matrix: tests/test_reference_models.py::test_model_citations_refuses_each_broken_carrier
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))   # for grounding_model, which the runner imports


def _load_runner():
    """Model II's runner, loaded BY FILE under a unique module name. Both package models name their runner
    `run_model.py`; a bare `import run_model` returned whichever the process had imported first, and the round-3 suite
    (shuffled, parallel) handed this module model I's runner — its mutants carry no `answers` (KeyError)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("grounding_run_model_0045",
                                                  pathlib.Path(__file__).resolve().parent / "run_model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run_model = _load_runner()

_ROW = re.compile(r"^\|\s*\*\*(INV-[A-Z]+\d+′?)\*\*\s*\|(.*)$")   # ′: a revised row keeps its id primed (0008am INV-Q4′)
_CITE = re.compile(r"\bmodel (G\d+)\b")
_BAD_CITE = re.compile(r"\bmodel G(?!\d)")
_DOC_CITE = re.compile(r"\(its (G\d+)\b")   # "(its G20)" and "(its G20; model I's … too)" alike
_CLAIM = re.compile(r"its invariants ((?:G\d+(?:[–-]G\d+)?(?:,\s*|\s+and\s+)?)+) are this spec's")


def section6(text: str) -> str:
    m = re.search(r"^## 6\..*?(?=^## )", text, re.M | re.S)
    return m.group(0) if m else ""


def named_mutants(line: str) -> int:
    """How many mutants a §6 row names (see COUNT in the module docstring)."""
    cell = re.split(r"(?<!\\)\|", line)[-2].strip()
    m = re.search(r"Mutants?:\s*(.*?)\s*→", cell)
    body = m.group(1) if m else cell
    return len([x for x in re.split(r";| · ", body) if x.strip()])


def parse(text: str) -> tuple[dict, set, set, list, dict]:
    """(rows {INV-id: set of 'G<n>'}, document-level cites, claimed set, grammar problems, {INV-id: mutants named})."""
    s6 = section6(text)
    problems = []
    if not s6:
        return {}, set(), set(), ["no §6 section"], {}
    flat = re.sub(r"\s+", " ", s6)
    doc = set(_DOC_CITE.findall(flat))
    claimed = set()
    for m in _CLAIM.finditer(flat):
        for a, b in re.findall(r"G(\d+)(?:[–-]G(\d+))?", m.group(1)):
            claimed |= {f"G{n}" for n in range(int(a), int(b or a) + 1)}
    rows, named = {}, {}
    for line in s6.splitlines():
        m = _ROW.match(line)
        if m:
            rows[m.group(1)] = set(_CITE.findall(line))
            named[m.group(1)] = named_mutants(line)
    if _BAD_CITE.search(flat):
        problems.append("a `model G` citation with no number")
    if not rows:
        problems.append("§6 has no `| **INV-…**` row")
    return rows, doc, claimed, problems, named


def check(docs: dict, mutants: dict) -> list[str]:
    """docs: {label: text}; mutants: run_model.run_mutants()'s output. Returns the refusals."""
    out = []
    parsed = {lab: parse(t) for lab, t in docs.items()}
    answering = {}                                        # "LABEL INV-x" -> [(mutant, owner, killed_by_owner)]
    for name, m in mutants.items():
        for a in m["answers"]:
            answering.setdefault(a, []).append((name, m["owner"], m["killed_by_owner"]))
    for lab, (rows, doc, claimed, problems, named) in parsed.items():
        out += [f"GRAMMAR {lab}: {p}" for p in problems]
        for inv, cites in sorted(rows.items()):
            for g in sorted(cites):
                if not any(owner == f"MODEL-{g}" for _n, owner, _k in answering.get(f"{lab} {inv}", [])):
                    out.append(f"FORWARD {lab} {inv} cites model {g}, but no mutant owned by MODEL-{g} answers it")
        for g in sorted(doc):
            if not any(owner == f"MODEL-{g}" for inv in rows for _n, owner, _k in answering.get(f"{lab} {inv}", [])):
                out.append(f"FORWARD {lab}: §6 says the model encodes it (its {g}), but no mutant owned by MODEL-{g} "
                           f"answers any of its rows")
        for inv in sorted(rows):
            tagged = len(answering.get(f"{lab} {inv}", []))
            if (rows[inv] or (doc and tagged)) and tagged < named[inv]:
                out.append(f"COUNT {lab} {inv}: the row names {named[inv]} mutant(s), the model tags {tagged} as answering it")
        cited = (set().union(*rows.values()) if rows else set()) | doc
        for g in sorted(claimed - cited):
            out.append(f"CLAIM {lab}: claims model {g} as its own, but no §6 row cites it")
    for key, ms in sorted(answering.items()):
        lab, inv = key.split(" ", 1)
        if lab not in parsed:
            continue
        rows, doc = parsed[lab][0], parsed[lab][1]
        for name, owner, killed in ms:
            if inv not in rows:
                out.append(f"REVERSE {key}: mutant '{name}' answers a row that {lab}'s §6 does not have")
            elif owner.removeprefix("MODEL-") not in rows[inv] | doc:
                out.append(f"REVERSE {key}: mutant '{name}' is owned by {owner}, which that row does not cite")
            if not killed:
                out.append(f"KILL {key}: mutant '{name}' is not killed by its owner {owner}")
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    docs = {}
    for a in argv:
        lab, _, path = a.partition("=")
        if not lab or not path:
            print(f"bad argument {a!r}: expected LABEL=PATH")
            return 2
        docs[lab] = pathlib.Path(path).read_text(encoding="utf-8")
    problems = check(docs, run_model.run_mutants())
    for p in problems:
        print(p)
    n = sum(len(parse(t)[0]) for t in docs.values())
    print(f"model citations: {len(docs)} document(s), {n} §6 rows, {len(problems)} refusal(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
