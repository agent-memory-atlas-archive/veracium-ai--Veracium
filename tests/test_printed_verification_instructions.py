"""Every verification command PRINTED inside an evidence carrier is executed as printed and must produce
the digest the carrier states.

2026-09-18, the 0042/0043 acceptance fold: the terminal record's provenance header told a future reader
how to verify the copied bytes — `sed '1,/^-->$/d' <file> | tail -n +2 | sha256sum` — and, run as
written, that command hashed EMPTY input and printed a digest anyway, because the comment did not close
on its own line. Nothing in the project checked the checkers' instructions; the defect lived in exactly
that gap (research named it; the owner's word: "any test that would increase quality without too much
of a performance penalty"). Cost: one shell pipeline per record, milliseconds.

The contract of a printed instruction, as this gate reads it, is the header's own facts: `sha256 <64
hex>`, `<N> bytes`, a line `Here: <command>` in which `<this file>` stands for the carrier's path, and
optionally a line `On the tarball: <command>` in which `<pkg>` stands for the archived package — resolved
by the package sha256 the header states against the sidecars in the local outbox, executed when it
resolves and reported N/A BY NAME when it does not (CI has no outbox). Both printed commands are
executed; nothing printed is silently skipped. A carrier with a TERMINAL RECORD header but NO printed
command is reported N/A by name (a not-run check must never look like a pass); the gate REFUSES if it
checked nothing at all; and it asserts that no TERMINAL RECORD exists outside its subject set
(`specs/evidence/**/*.md`), because a record elsewhere would be unseen, not N/A.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence"
# the file's LEADING comment, closed by a marker that CLOSES A LINE (trailing blanks tolerated here, NOT by a
# printed `^-->$`), never one quoted inside a printed command; a record is a leading comment that SAYS
# "TERMINAL RECORD" anywhere in it (0039's round-9 record opens on a bare `<!--` with the words on the next line)
HEADER = re.compile(r"\A\s*<!--.*?-->[ \t]*\n", re.S)
RECORD_WORDS = "TERMINAL RECORD"
DIGEST = re.compile(r"sha256 ([0-9a-f]{64}), (\d+) bytes")
COMMAND = re.compile(r"^Here: (.+?)(?:\s+\(.*\))?$", re.M)
TARBALL = re.compile(r"^On the tarball: (.+?)(?:\s+\(.*\))?$", re.M)
PKG_SHA = re.compile(r"\(sha256 ([0-9a-f]{64})\s")
OUTBOX = pathlib.Path.home() / "Documents" / "veracium" / "outbox"


def _package_for(pkg_sha: str):
    """The archived package whose BYTES hash to `pkg_sha`: ("ok", path) | ("absent", reason) |
    ("stale-sidecar", reason). The sidecar only nominates a candidate; the archive's own sha256 decides
    (research, 2026-09-18: a sidecar is a name standing in for the bytes — a stale one would select a
    repack whose README happens to match, and the gate would print "agrees" about the wrong package).
    ~0.009 s for a 9.6 MB archive."""
    if not OUTBOX.is_dir():
        return ("absent", "no local outbox")
    for side in OUTBOX.glob("*.tar.gz.sha256"):
        tar = side.with_suffix("")
        if side.read_text().split()[0] == pkg_sha and tar.exists():
            actual = hashlib.sha256(tar.read_bytes()).hexdigest()
            if actual != pkg_sha:
                return ("stale-sidecar", f"{side.name} states {pkg_sha[:16]}… but {tar.name} hashes to {actual[:16]}…")
            return ("ok", tar)
    return ("absent", f"no archive in the outbox hashes to {pkg_sha[:16]}…")


def _records():
    """(path, header) for every carrier under specs/evidence whose first comment is a TERMINAL RECORD."""
    out = []
    for p in sorted(EVIDENCE.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = HEADER.match(text)
        if m and RECORD_WORDS in m.group(0):
            out.append((p, m.group(0)))
    return out


def _name(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:                       # a control's copy under tmp_path
        return path.name


def _verify(path: pathlib.Path, header: str, *, cwd: pathlib.Path = ROOT) -> tuple[str, str]:
    """-> ("ok" | "N/A" | "FAIL", detail). Executes the printed command with `<this file>` bound to `path`."""
    d, c = DIGEST.search(header), COMMAND.search(header)
    if not (d and c):
        return "N/A", f"{_name(path)}: header prints no digest+command pair (nothing to execute)"
    stated, nbytes = d.group(1), int(d.group(2))
    cmd = c.group(1).replace("<this file>", str(path))
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    got = (r.stdout.split() or [""])[0]
    if r.returncode != 0 or got != stated:
        return "FAIL", f"{_name(path)}: `{cmd}` -> rc {r.returncode}, digest {got[:16] or '<none>'}…, stated {stated[:16]}…"
    # the byte count is a second, independent fact: the same command minus the hash must yield N bytes
    body_cmd = cmd.rsplit("|", 1)[0] + "| wc -c" if cmd.rstrip().endswith("sha256sum") else None
    if body_cmd:
        n = subprocess.run(body_cmd, shell=True, capture_output=True, text=True, cwd=cwd).stdout.strip()
        if n != str(nbytes):
            return "FAIL", f"{_name(path)}: the printed command yields {n} bytes, the header states {nbytes}"
    # the tarball-side instruction, when printed: executed if the package resolves, N/A by name if not
    t, k = TARBALL.search(header), PKG_SHA.search(header)
    tarball_note = ""
    if t:
        kind, pkg = _package_for(k.group(1)) if k else ("absent", "the header states no package sha256")
        if kind == "stale-sidecar":
            return "FAIL", f"{_name(path)}: tarball-side command not run — {pkg}"
        if kind != "ok":
            tarball_note = f"; tarball-side command N/A here ({pkg})"
        else:
            tcmd = t.group(1).replace("<pkg>", str(pkg))
            tr = subprocess.run(tcmd, shell=True, capture_output=True, text=True, cwd=cwd)
            tgot = (tr.stdout.split() or [""])[0]
            if tr.returncode != 0 or tgot != stated:
                return "FAIL", f"{_name(path)}: tarball-side `{tcmd}` -> rc {tr.returncode}, digest {tgot[:16] or '<none>'}…, stated {stated[:16]}…"
            tarball_note = f"; tarball-side command agrees ({pkg.name})"
    return "ok", f"{_name(path)}: {stated[:16]}… over {nbytes} bytes, by the printed command{tarball_note}"


def test_every_printed_verification_instruction_executes_to_its_stated_digest():
    results = [(_verify(p, h), p) for p, h in _records()]
    for (status, detail), _ in results:
        print(f"  {status:4s} {detail}")
    fails = [detail for (status, detail), _ in results if status == "FAIL"]
    assert not fails, "printed verification instructions that do NOT produce their stated digest:\n  " + "\n  ".join(fails)
    checked = [p for (status, _), p in results if status == "ok"]
    assert checked, "the gate checked NOTHING — no terminal record prints a digest+command pair; a gate with no subject is not a pass"


def test_no_terminal_record_exists_outside_the_gates_subject_set():
    """The subject set is specs/evidence/**/*.md. A record elsewhere would be UNSEEN, which the
    'checked nothing' assertion cannot tell from N/A — so the emptiness outside the set is asserted here,
    over the tracked tree, and this is the assertion that moves the day a record lands somewhere else."""
    tracked = subprocess.run(["git", "ls-files", "-z", "--", "*.md"], capture_output=True, cwd=ROOT)
    if tracked.returncode != 0:
        pytest.skip("no repository here (a git archive): the tracked-file enumeration cannot run")
    outside = []
    for rel in tracked.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if not rel:
            continue
        p = ROOT / rel
        if p.is_relative_to(EVIDENCE) or not p.exists():
            continue
        m = HEADER.match(p.read_text(encoding="utf-8", errors="replace"))
        if m and RECORD_WORDS in m.group(0):
            outside.append(rel)
    assert outside == [], f"TERMINAL RECORD carriers outside specs/evidence/ — unseen by the gate: {outside}"


def _round5_record():
    p = EVIDENCE / "0042" / "round-5-bundle-README.md"
    assert p.exists(), "the 0042 round-5 terminal record is the gate's first subject"
    return p


def test_control_a_wrong_stated_digest_is_refused(tmp_path):
    """Negative control 1: the same carrier with one hex digit of its stated digest changed → FAIL."""
    p = _round5_record(); text = p.read_text(encoding="utf-8")
    d = DIGEST.search(text); bad = ("0" if d.group(1)[0] != "0" else "1") + d.group(1)[1:]
    copy = tmp_path / p.name; copy.write_text(text.replace(d.group(1), bad, 1), encoding="utf-8")
    status, detail = _verify(copy, HEADER.match(copy.read_text(encoding="utf-8")).group(0))
    assert status == "FAIL" and "digest" in detail, (status, detail)


def test_control_a_changed_body_byte_is_refused(tmp_path):
    """Negative control 1b: the COPIED BYTES change by one character (the stated digest and count stay).
    The command must read the bytes the carrier holds, not anything reconstructed: digest AND byte
    count disagree. This is the mutation a terminal record exists to prevent."""
    p = _round5_record(); text = p.read_text(encoding="utf-8")
    head, body = text.split("\n-->\n\n", 1)
    assert body and body[0] == "#"
    copy = tmp_path / p.name; copy.write_text(head + "\n-->\n\n" + "!" + body[1:] + "x", encoding="utf-8")   # one byte changed, one added
    status, detail = _verify(copy, HEADER.match(copy.read_text(encoding="utf-8")).group(0))
    assert status == "FAIL" and "digest" in detail, (status, detail)
    copy.write_text(head + "\n-->\n\n" + "!" + body[1:], encoding="utf-8")                                  # same length, one byte changed
    status, detail = _verify(copy, HEADER.match(copy.read_text(encoding="utf-8")).group(0))
    assert status == "FAIL" and "digest" in detail, (status, detail)


def test_control_an_instruction_that_hashes_nothing_is_refused(tmp_path):
    """Negative control 2: the ORIGINAL defect's class — the comment's closing marker is not EXACTLY alone
    on its line (here: one trailing space), so the header still parses but the printed `sed '1,/^-->$/d'`
    range never matches and the pipeline hashes EMPTY input. The empty-input digest (e3b0c442…) is never
    the stated one and the byte count is 0, so this is refused twice over."""
    p = _round5_record(); text = p.read_text(encoding="utf-8")
    assert "\n-->\n" in text
    broken = text.replace("\n-->\n", "\n--> \n", 1)                       # the marker no longer matches ^-->$
    copy = tmp_path / p.name; copy.write_text(broken, encoding="utf-8")
    header = HEADER.match(broken).group(0)
    assert COMMAND.search(header), "the printed command must still be inside the header for this control to exercise the sed range"
    status, detail = _verify(copy, header)
    assert status == "FAIL" and "digest e3b0c44298fc1c14" in detail, (status, detail)
    empty = hashlib.sha256(b"").hexdigest()
    got = subprocess.run(COMMAND.search(header).group(1).replace("<this file>", str(copy)), shell=True, capture_output=True, text=True).stdout.split()[0]
    assert got == empty, "the broken instruction should hash EMPTY input — that is the defect this gate exists for"


def test_control_a_stale_sidecar_is_refused_not_read_as_the_package(tmp_path, monkeypatch):
    """Negative control 3: an outbox whose sidecar states the header's package sha256 beside an archive
    whose bytes do NOT hash to it. The sidecar nominates; the bytes decide; the mismatch is refused BY
    NAME, never read as "no outbox" and never as agreement."""
    p = _round5_record(); header = HEADER.match(p.read_text(encoding="utf-8")).group(0)
    k = PKG_SHA.search(header); assert k
    fake = tmp_path / "outbox"; fake.mkdir()
    (fake / "some-package.tar.gz").write_bytes(b"not the package")
    (fake / "some-package.tar.gz.sha256").write_text(f"{k.group(1)}  some-package.tar.gz\n")
    monkeypatch.setattr(_module(), "OUTBOX", fake)
    status, detail = _verify(p, header)
    assert status == "FAIL" and "hashes to" in detail, (status, detail)


def _module():
    import sys
    return sys.modules[__name__]


def test_a_record_without_a_printed_command_is_reported_not_passed(tmp_path):
    """A header with no digest+command pair is N/A by name, never counted as checked."""
    copy = tmp_path / "x.md"; copy.write_text("<!-- TERMINAL RECORD — no instruction printed -->\n\nbody\n", encoding="utf-8")
    m = HEADER.match(copy.read_text()); assert m and RECORD_WORDS in m.group(0)
    status, detail = _verify(copy, m.group(0))
    assert status == "N/A" and "nothing to execute" in detail
