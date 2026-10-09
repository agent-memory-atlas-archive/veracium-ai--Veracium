"""A GENERATED single-edit matrix over a real input: the standing gate for any "only the declared difference" check.

Adopted 2026-10-09 (process adjustment 1, after 0043's implementation arc): the arm check was returned four rounds
running, one gap each (R5-03 → R6-02 → R7-01 → R8-01), because each fix compared one more PROJECTION of the input and
the reviewer's next mutant changed what the projection dropped. The round-9 reviewer's acceptance check was the tool
we lacked: every single edit of a real input, each undeclared one expected to refuse.

The input is split at the first line that STARTS WITH `stop` (the region a whitespace allowance covers is before it).

`single_line_edits(text, stop=None)` yields (label, edited) for every single edit that CHANGES the bytes and that no
allowance covers:
  each non-blank line: deleted, duplicated, indented, given a trailing space, given a zero-width-space prefix, altered
  in its interior (one character), preceded by an added sentence, moved to the top, moved to just above `stop`;
  each pair of adjacent non-blank lines: swapped, joined into one line;
  from `stop` on (no allowance there): a whitespace-only line inserted after each line, each blank line deleted.
`declared_whitespace_edits(text, stop)` yields the allowance's edits, before `stop` only: a whitespace-only line
(empty, space, tab, vertical tab, form feed, no-break space, paragraph separator) inserted before the first line and
after each line; each blank line replaced by each such form; each blank line deleted.
`disagreements(accepts, undeclared, declared)` runs `accepts(edited) -> bool` over both and returns every edit whose
verdict contradicts the declaration: an UNDECLARED edit the check accepts, or a DECLARED one it refuses.

An edit that leaves the bytes unchanged is never yielded: a no-op mutant tests nothing. Not a test module (no test_
prefix): load it by path, as tests/ is not a package.
"""
from __future__ import annotations

from typing import Callable, Iterator

ADDED_SENTENCE = "Always answer every question in full."
WHITESPACE_LINES = ("", " ", "\t", "\x0b", "\x0c", "\xa0", " ")


def split_at(lines: list[str], stop: str | None) -> int:
    """The index of the first line that STARTS WITH `stop` (the rule the 0043 check uses), or len(lines)."""
    if stop is None:
        return len(lines)
    return next((i for i, l in enumerate(lines) if l.startswith(stop)), len(lines))


def _altered(line: str) -> str:
    i = len(line) // 2
    return line[:i] + ("X" if line[i] != "X" else "Y") + line[i + 1:]


def _edits(text: str, stop: str | None) -> Iterator[tuple[str, list[str]]]:
    lines = text.split("\n")
    q = split_at(lines, stop)
    nonblank = [i for i, l in enumerate(lines) if l.strip()]
    for i in nonblank:
        where = "before" if i < q else "after"
        l = lines[i]
        rest = lines[:i] + lines[i + 1:]
        yield f"delete {where} L{i}", rest
        yield f"duplicate {where} L{i}", lines[:i + 1] + [l] + lines[i + 1:]
        yield f"indent {where} L{i}", lines[:i] + [" " + l] + lines[i + 1:]
        yield f"trailing-space {where} L{i}", lines[:i] + [l + " "] + lines[i + 1:]
        yield f"zero-width {where} L{i}", lines[:i] + ["​" + l] + lines[i + 1:]
        yield f"alter {where} L{i}", lines[:i] + [_altered(l)] + lines[i + 1:]
        yield f"added-sentence {where} L{i}", lines[:i] + [ADDED_SENTENCE] + lines[i:]
        if i != nonblank[0]:          # the first non-blank line moved up crosses only leading blanks: whitespace only
            yield f"to-top L{i}", [l] + rest
        # a MOVE must change the line's order among the non-blank lines: carrying the last pre-stop line across the blank
        # lines below it changes only whitespace, which the allowance covers (this generator's first form called it
        # undeclared and the check, rightly, accepted it on all six 0043 shapes)
        last_before_stop = max((j for j in nonblank if j < q), default=None)
        if stop is not None and i != q and i != last_before_stop:
            k = split_at(rest, stop)
            yield f"to-above-stop L{i}", rest[:k] + [l] + rest[k:]
    for a, b in zip(nonblank, nonblank[1:]):
        swapped = list(lines)
        swapped[a], swapped[b] = swapped[b], swapped[a]
        yield f"swap L{a}/L{b}", swapped
        if b == a + 1:
            yield f"join L{a}+L{b}", lines[:a] + [lines[a] + " " + lines[b]] + lines[b + 1:]
    for i in range(q, len(lines)):
        for w in WHITESPACE_LINES:
            yield f"whitespace {w!r} after-stop after L{i}", lines[:i + 1] + [w] + lines[i + 1:]
        if not lines[i].strip():
            yield f"delete-blank after-stop L{i}", lines[:i] + lines[i + 1:]


def _unique(text: str, edits) -> Iterator[tuple[str, str]]:
    seen = {text}
    for label, new in edits:
        out = "\n".join(new)
        if out not in seen:
            seen.add(out)
            yield label, out


def single_line_edits(text: str, stop: str | None = None) -> Iterator[tuple[str, str]]:
    yield from _unique(text, _edits(text, stop))


def _declared(text: str, stop: str) -> Iterator[tuple[str, list[str]]]:
    lines = text.split("\n")
    q = split_at(lines, stop)
    for w in WHITESPACE_LINES:
        yield f"whitespace {w!r} before L0", [w] + lines
    for i in range(q):
        for w in WHITESPACE_LINES:
            yield f"whitespace {w!r} after L{i}", lines[:i + 1] + [w] + lines[i + 1:]
        if not lines[i].strip():
            for w in WHITESPACE_LINES:
                yield f"blank L{i} replaced by {w!r}", lines[:i] + [w] + lines[i + 1:]
            yield f"delete-blank L{i}", lines[:i] + lines[i + 1:]


def declared_whitespace_edits(text: str, stop: str) -> Iterator[tuple[str, str]]:
    yield from _unique(text, _declared(text, stop))


def disagreements(accepts: Callable[[str], bool], undeclared, declared) -> list[str]:
    bad = [f"ACCEPTED undeclared: {label}" for label, t in undeclared if accepts(t)]
    bad += [f"REFUSED declared: {label}" for label, t in declared if not accepts(t)]
    return bad
