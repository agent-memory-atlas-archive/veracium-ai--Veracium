"""The allocation registry's PEER scan (specs/allocation.py, 2026-10-10).

The number 0048 was claimed three times — twice by drafts that lived only in
the research seat's tree (one with a built review package), once by a spec
dispatched the same day — because the registry saw only `specs/`. A draft
now claims its number where it is written: these tests drive the scan over a
SYNTHETIC peer tree (a throwaway git work tree), never over the real one,
so the suite does not depend on another seat's working state. Every refusal
has its control beside it, and the acceptance controls (the cases that must
NOT refuse) are written as deliberately as the refusals.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "specs"))
import allocation  # noqa: E402

PY = sys.executable


def _repo_spec(number: str) -> tuple[str, str]:
    """(file, normalised title) of a spec this tree holds."""
    f = next((ROOT / "specs").glob(f"{number}-*.md"))
    c = allocation.file_claim(f, f.name)
    assert c and c["title"], f
    return f.name, c["title"]


def _top() -> str:
    return max(r["number"] for r in allocation.holders())


def _fresh() -> str:
    """A number above everything this tree holds or has spent, outside every
    live reservation — where a new peer draft would land."""
    return allocation.next_uncontested()


class PeerTree(type(pathlib.Path())):
    """A throwaway git work tree standing in for the peer seat's."""

    def write(self, rel: str, text: str, *, add: bool = True) -> pathlib.Path:
        f = pathlib.Path(self, rel)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        if add:
            subprocess.run(["git", "-C", str(self), "add", rel], check=True)
        return f


@pytest.fixture
def peer(tmp_path):
    root = PeerTree(tmp_path / "peer")
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "proposals").mkdir()
    return root


def _spec(title: str, number_in_heading: str | None = None, status: str = "draft", banner: int = 0) -> str:
    head = f"# Feature spec {number_in_heading}: {title}" if number_in_heading else f"# Feature spec: {title}"
    return "".join("> a banner line\n" for _ in range(banner)) + f"{head}\n\nSpec-Status: {status}\n\nbody\n"


def test_the_motivating_case_two_titles_on_one_number_is_refused__and_the_same_spec_is_not(peer):
    """0048 as it happened: a peer draft takes the number a spec in specs/
    holds, under a DIFFERENT title — refused, naming both. Acceptance
    control: the peer's own copy of the SAME spec (its candidate, a package
    copy), with a different subtitle and markup, is one title, not two."""
    top = _top()
    _, title = _repo_spec(top)
    peer.write(f"proposals/{top}-something-else-CANDIDATE.md", _spec("something else entirely — a subtitle"))
    probs = allocation.peer_problems(peer)
    assert any(f"number {top} is claimed by 2 different specs" in p and "NOT recorded" in p for p in probs), probs
    (peer / f"proposals/{top}-something-else-CANDIDATE.md").unlink()   # tracked and deleted: no longer a claim
    peer.write(f"review-packages/pkg/{top}-copy-SPEC-v9.md", _spec(f"`{title.upper()}` — **another** subtitle"))
    assert allocation.peer_problems(peer) == []


def test_an_untracked_draft_claims_its_number__and_an_ignored_one_does_not(peer):
    """A draft written and not yet committed is the race window, so the scan
    covers untracked files; a gitignored file (caches, venvs) is not a
    draft. Both halves, because a scan over tracked files alone passes the
    first case silently."""
    top = _top()
    peer.write(f"proposals/{top}-untracked-CANDIDATE.md", _spec("an untracked rival"), add=False)
    assert any(f"number {top}" in p for p in allocation.peer_problems(peer))
    (peer / ".gitignore").write_text("ignored/\n")
    (peer / f"proposals/{top}-untracked-CANDIDATE.md").unlink()
    peer.write(f"ignored/{top}-cache-CANDIDATE.md", _spec("an ignored rival"), add=False)
    assert allocation.peer_problems(peer) == []


def test_the_keys_heading_within_the_head_lines_and_status_only(peer):
    """A banner above the heading does not hide it (within HEAD_LINES); a
    heading below that bound is not seen — the key's stated limit, pinned
    here so a change to it is a decision. A file with neither key claims
    nothing (rulings, legs, dated scans)."""
    top = _top()
    n = allocation.HEAD_LINES
    peer.write(f"proposals/{top}-bannered-CANDIDATE.md", _spec("bannered rival", banner=n - 1))
    assert any(f"number {top}" in p for p in allocation.peer_problems(peer))
    peer.write(f"proposals/{top}-bannered-CANDIDATE.md", _spec("bannered rival", banner=n + 1).replace("Spec-Status", "Status"))
    assert allocation.peer_problems(peer) == []
    peer.write(f"{top}-Q2-ruling.md", "# Ruling on Q2\n\nnot a spec\n")
    peer.write("scans/2026-07-27.md", "# a dated scan\n")
    assert allocation.peer_problems(peer) == []
    assert all(c["number"] != "2026" for c in allocation.peer_claims(peer))


def test_a_status_only_draft_blocks_its_number(peer):
    """A withdrawn draft rewrites its heading and keeps `Spec-Status:` — it
    still blocks its number, so `next_number` steps past it, and a
    status-only number nothing accounts for is named. Controls: the same
    file on a number this tree holds, or on a SPENT number, is accounted for."""
    fresh = _fresh()
    peer.write(f"proposals/{fresh}-withdrawn-WITHDRAWN.md", "# WITHDRAWN — an idea\n\nSpec-Status: withdrawn\n")
    assert any(f"number {fresh} is blocked by a status-only draft" in p for p in allocation.peer_problems(peer))
    assert allocation.next_number(peer) > fresh
    assert allocation.next_number(None) == fresh          # the repo-only answer hands it out: why --next refuses it
    (peer / f"proposals/{fresh}-withdrawn-WITHDRAWN.md").unlink()
    for n in (_top(), next(iter(allocation.SPENT))):     # held here; spent
        f = peer.write(f"proposals/{n}-fragment-DRAFT.md", "# a fragment\n\nSpec-Status: draft\n")
        assert allocation.peer_problems(peer) == [], n
        f.unlink()


def test_next_number_steps_past_every_peer_claim(peer):
    """The point that saves the work is the FIRST numbered file: a peer draft
    on the fresh number moves `--next` past it. Control: an empty peer
    answers the repo-only number."""
    fresh = _fresh()
    assert allocation.next_number(peer) == fresh
    peer.write(f"proposals/{fresh}-new-idea-CANDIDATE.md", _spec("a new idea"))
    assert allocation.peer_problems(peer) == []
    assert allocation.next_number(peer) == allocation.next_uncontested(fresh)
    assert allocation.next_number(peer) > fresh


def test_a_recorded_collision_passes_only_for_exactly_its_titles(peer, monkeypatch):
    """PEER_CONTESTED is a disclosure of one known set: it clears that set,
    a third title on the same number refuses again, and a record whose
    collision is gone is stale."""
    top = _top()
    _, title = _repo_spec(top)
    peer.write(f"proposals/{top}-rival-CANDIDATE.md", _spec("rival"))
    rec = {"titles": sorted([title, "rival"]), "since": "2026-10-10", "awaits": "a ruling"}
    monkeypatch.setattr(allocation, "PEER_CONTESTED", {top: rec})
    assert allocation.peer_problems(peer) == []
    peer.write(f"proposals/{top}-third-DRAFT.md", _spec("third"))
    assert any("the record names a different set" in p for p in allocation.peer_problems(peer))
    for rel in (f"proposals/{top}-third-DRAFT.md", f"proposals/{top}-rival-CANDIDATE.md"):
        (peer / rel).unlink()
    assert any("stale entry" in p for p in allocation.peer_problems(peer))


def test_heading_number_spent_number_and_reservation(peer, monkeypatch):
    """Three more ways a peer draft can misuse a number, each with its
    control: a heading whose own number disagrees with its filename; a
    titled draft on a SPENT number; a draft inside a live reservation."""
    fresh = _fresh()
    peer.write(f"proposals/{fresh}-x-DRAFT.md", _spec("x", number_in_heading=fresh))
    assert allocation.peer_problems(peer) == []
    peer.write(f"proposals/{fresh}-x-DRAFT.md", _spec("x", number_in_heading=_top()))
    assert any("its heading says" in p for p in allocation.peer_problems(peer))
    peer.write(f"proposals/{fresh}-x-DRAFT.md", _spec("x"))
    spent = next(iter(allocation.SPENT))
    peer.write(f"proposals/{spent}-reuse-CANDIDATE.md", _spec("reuse"))
    assert any(f"claims SPENT number {spent}" in p for p in allocation.peer_problems(peer))
    (peer / f"proposals/{spent}-reuse-CANDIDATE.md").unlink()
    assert allocation.peer_problems(peer) == []
    monkeypatch.setattr(allocation, "RESERVATIONS", [dict(allocation.RESERVATIONS[0], range=(fresh, fresh))])
    assert any(f"inside the live reservation {fresh}–{fresh}" in p for p in allocation.peer_problems(peer))


def test_a_peer_that_is_not_a_git_work_tree_is_a_problem(tmp_path):
    (tmp_path / "plain").mkdir()
    probs = allocation.peer_problems(tmp_path / "plain")
    assert len(probs) == 1 and "not a readable git work tree" in probs[0], probs


def _cli(*args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "VERACIUM_SPECS_DIR"}
    env["VERACIUM_PEER_TREE"] = ""      # explicitly none, over any clone's git config
    env.update(env_extra or {})
    return subprocess.run([PY, str(ROOT / "specs" / "allocation.py"), *args], capture_output=True, text=True, env=env)


def test_cli_next_refuses_without_the_peer__and_answers_with_it(peer):
    """`--next` is the act that takes a number, so it refuses without the
    peer (exit 2, naming how to configure it); `--repo-only` answers and
    says what it ignored; with the peer it steps past the peer's drafts.
    `--peer-check` refuses without the peer too."""
    r = _cli("--next")
    assert r.returncode == 2 and "REFUSED: no peer tree configured" in r.stdout and "veracium.peerTree" in r.stdout, r.stdout
    assert _cli("--peer-check").returncode == 2
    r = _cli("--next", "--repo-only")
    assert r.returncode == 0 and "NOT CHECKED (--repo-only)" in r.stdout and r.stdout.strip().endswith(_fresh()), r.stdout
    fresh = _fresh()
    peer.write(f"proposals/{fresh}-new-CANDIDATE.md", _spec("new"))
    r = _cli("--next", env_extra={"VERACIUM_PEER_TREE": str(peer)})
    assert r.returncode == 0 and f"CHECKED {peer}" in r.stdout, r.stdout
    assert r.stdout.strip().splitlines()[-1] == allocation.next_uncontested(fresh)
    r = _cli("--next", env_extra={"VERACIUM_PEER_TREE": str(peer / "nowhere")})
    assert r.returncode == 2 and "does not exist" in r.stdout


def test_cli_peer_check_fails_on_a_collision(peer):
    top = _top()
    peer.write(f"proposals/{top}-rival-CANDIDATE.md", _spec("rival"))
    r = _cli("--peer-check", env_extra={"VERACIUM_PEER_TREE": str(peer)})
    assert r.returncode == 1 and f"PROBLEM: number {top} is claimed by 2 different specs" in r.stdout, r.stdout


def test_the_render_is_this_trees_alone(peer):
    """`--check` (the rendered table, which CI runs) never reads the peer, so
    the table cannot depend on the machine; and under VERACIUM_SPECS_DIR the
    render is refused rather than written from another tree."""
    top = _top()
    peer.write(f"proposals/{top}-rival-CANDIDATE.md", _spec("rival"))
    r = _cli("--check", env_extra={"VERACIUM_PEER_TREE": str(peer)})
    assert r.returncode == 0 and "PROBLEM" not in r.stdout, r.stdout
    r = _cli("--check", env_extra={"VERACIUM_SPECS_DIR": str(ROOT / "specs")})
    assert r.returncode == 2 and "REFUSED: VERACIUM_SPECS_DIR" in r.stdout
