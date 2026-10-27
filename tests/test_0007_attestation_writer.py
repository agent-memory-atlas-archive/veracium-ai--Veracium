"""0007 §4g.6 4d and v19: the attestation-record writer (specs/attestation_writer.py), I4's writer side.

The record's key is this process's own; one validator both directions and a read-back round trip; fixture marks
refused; v19's cross-run order arm by arm, each refusal asserting its MESSAGE, driven through an injectable git and
grounded by REAL temporary repositories (an ancestor, an older commit, a sibling branch, a file:// shallow clone, an
unknown commit's exit 128); the record's commit must be the checkout's HEAD; git's environment pinned; merge over the
full key; atomic publication over a closed top level.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("veracium_attestation_writer", ROOT / "specs" / "attestation_writer.py")
aw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aw)
sv = aw.sv

A = "a" * 40
B = "b" * 40


def evidence(digest="e" * 64):
    return digest, {k: True for k in sv.CONFINEMENT_PROBE_KEYS}


def record(commit=A, digest="e" * 64, **over):
    d, c = evidence(digest)
    r = aw.build_record(d, c, [{"route": "setup-python", "runner_image": "ubuntu-24.04", "run_id": "1",
                                 "job_id": 1, "commit": commit}])
    r.update(over)
    return r


def fake_git(head=A, shallow="false", fmt="sha1", inside="true", ancestor=None, version_rc=0):
    """An injectable git: `ancestor` maps (old, new) to --is-ancestor's exit code."""
    ancestor = ancestor or {}

    def git(args, repo):
        if args == ["--version"]:
            return version_rc, "git version 2.43.0"
        if args == ["rev-parse", "--is-inside-work-tree"]:
            return (0, inside) if inside is not None else (128, "")
        if args == ["rev-parse", "--is-shallow-repository"]:
            return 0, shallow
        if args == ["rev-parse", "--show-object-format"]:
            return 0, fmt
        if args == ["rev-parse", "HEAD"]:
            return 0, head
        if args[:2] == ["merge-base", "--is-ancestor"]:
            return ancestor.get((args[2], args[3]), 128), ""
        raise AssertionError(args)
    return git


# ---- the record and its validation (W1–W4) ---------------------------------------------------------------------------
def test_the_key_is_this_builds_own_and_the_record_validates_as_the_reader_does():
    r = record()
    assert sv.attestation_key(r) == sv.attestation_key(sv.attestation_identity())
    assert sv.attestation_record_problems(r) == []


def test_a_record_whose_provenance_names_two_commits_is_malformed():
    """W1 (a production rule): one record, one commit — v19's ancestry compares exactly that one."""
    r = record()
    r["provenance"] = sorted(r["provenance"] + [dict(r["provenance"][0], job_id=2, commit=B)],
                             key=lambda j: (j["route"], j["runner_image"], j["job_id"]))
    assert any("the same commit" in p for p in sv.attestation_record_problems(r))
    with pytest.raises(aw.AttestationRefused, match="malformed"):
        aw.merged([], r, git=fake_git())


@pytest.mark.parametrize("mark", ["commit", "run_id"])
def test_a_fixture_mark_is_refused_by_the_writer(mark):
    """W4: the writer never writes a fixture (B12's marks), so the packaged artifact holds none by construction."""
    r = record(commit=aw.FIXTURE_COMMIT if mark == "commit" else A)
    if mark == "run_id":
        r["provenance"][0]["run_id"] = "fixture-x"
    with pytest.raises(aw.AttestationRefused, match="fixture mark"):
        aw.merged([], r, git=fake_git(head=r["provenance"][0]["commit"]))


# ---- v19's order, arm by arm, through an injectable git --------------------------------------------------------------
ARMS = {
    # name: (git, existing records, the message the refusal must carry)
    "no git": (fake_git(version_rc=127), [], "unanswerable: git is not available"),
    "outside a repository": (fake_git(inside=None), [], "not inside a git repository"),
    "shallow": (fake_git(shallow="true"), [], "unanswerable: the repository is shallow"),
    "unreadable object format": (fake_git(fmt="sha0"), [], "object format is unreadable"),
    "the record's commit is not HEAD": (fake_git(head=B), [], f"the record's commit {A} is not this checkout's HEAD {B}"),
    "the same commit, different evidence": (fake_git(), "same", "the same commit"),
    "the writing commit is OLDER": (fake_git(ancestor={(B, A): 1, (A, B): 0}), "older", "the writing commit"),
    "sibling branches": (fake_git(ancestor={(B, A): 1, (A, B): 1}), "older", "sibling branches"),
    "--is-ancestor unanswerable": (fake_git(ancestor={(B, A): 128}), "older", "unanswerable: --is-ancestor exited 128"),
    "the reverse unanswerable": (fake_git(ancestor={(B, A): 1, (A, B): 129}), "older",
                                 "unanswerable: the reverse --is-ancestor exited 129"),
}


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_each_cross_run_arm_refuses_with_its_message(arm):
    """v19 §4g.6 4d, each refusal by its MESSAGE. Mutants (stage 2): drop an arm; move the shallow check after
    --is-ancestor; take the same-commit step after step 4; read any nonzero exit as one class; a claimed commit."""
    git, existing, want = ARMS[arm]
    if existing == "same":
        existing = [record(digest="d" * 64)]
    elif existing == "older":
        existing = [record(commit=B)]
    with pytest.raises(aw.AttestationRefused) as e:
        aw.merged(existing, record(), git=git)
    assert want in str(e.value), str(e.value)


def test_the_same_commit_with_equal_evidence_is_idempotent(tmp_path):
    path = tmp_path / "sqlite_runtimes.json"
    path.write_text(json.dumps({"attestations": [record()]}))
    before = path.read_bytes()
    assert aw.write(record(), path=path, git=fake_git()) == "idempotent"
    assert path.read_bytes() == before


def test_an_ancestor_replaces_and_every_other_key_is_kept():
    """10(d)'s replacement-by-key, inverted from the legacy writer: an ancestor's record of THIS key is replaced; a
    record of another key (here another machine) is kept byte for byte."""
    other = record(commit=B, machine="aarch64")
    out, outcome = aw.merged([record(commit=B), other], record(), git=fake_git(ancestor={(B, A): 0}))
    assert outcome == "replaced" and out[0] == other and len(out) == 2
    assert sv.record_commit(out[1]) == A


def test_a_superseded_revision_is_replaced_only_on_the_full_key():
    """W7 / 10(a): an OLDER-revision record of the same full key is superseded; one sharing (version, source_id) on
    ANOTHER key is kept."""
    old_mine = record(manifest_algorithm=sv.MANIFEST_ALGORITHM - 1)
    old_other = record(manifest_algorithm=sv.MANIFEST_ALGORITHM - 1, libc="musl")
    assert (old_other["sqlite_version"], old_other["source_id"]) == (old_mine["sqlite_version"], old_mine["source_id"])
    out, _ = aw.merged([old_mine, old_other], record(), git=fake_git())
    assert old_mine not in out and old_other in out


def test_a_future_revision_of_this_key_is_never_overwritten_and_another_keys_does_not_block():
    """S75 / 10(d): a NEWER revision of this key refuses; a newer revision of ANOTHER key blocks nothing."""
    with pytest.raises(aw.AttestationRefused, match="NEWER revision"):
        aw.merged([record(commit=B, schema_version=sv.SCHEMA_VERSION + 1)], record(), git=fake_git())
    out, outcome = aw.merged([record(commit=B, schema_version=sv.SCHEMA_VERSION + 1, machine="aarch64")], record(),
                             git=fake_git())
    assert outcome == "written" and len(out) == 2


def test_a_record_with_a_failed_confinement_probe_is_refused_as_malformed():
    """W2: the NEW record is validated by production's record validator before anything else runs."""
    d, c = evidence()
    r = record()
    r["confinement"] = dict(c, **{sorted(c)[0]: False})
    with pytest.raises(aw.AttestationRefused, match="the record is malformed"):
        aw.merged([], r, git=fake_git())


def test_a_record_that_would_not_read_back_attested_is_refused(monkeypatch):
    """W2's round trip is a refusal of its own, not only a property of valid input: a reader that would not answer
    attested for the written key stops the write (forged reader; nothing valid reaches this arm otherwise)."""
    monkeypatch.setattr(sv, "attested_key", lambda key, records, *a, **k: False)
    with pytest.raises(aw.AttestationRefused, match="would not read back attested"):
        aw.merged([], record(), git=fake_git())


def test_git_env_scrubs_inherited_repository_variables_and_pins_config():
    """BLOCKING 2 (widened at stage 2), on the environment itself: EVERY inherited GIT_* variable is gone, including
    ones no list named, and exactly the pins are set, whatever the caller inherited."""
    base = {k: "/elsewhere" for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE",
                                      "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_A_NAME_NO_LIST_HAS")}
    base.update(PATH="/usr/bin", GIT_CONFIG_GLOBAL="/home/dev/.gitconfig", GIT_CONFIG_NOSYSTEM="0",
                GIT_NO_REPLACE_OBJECTS="0")
    env = aw.git_env(base)
    assert {k: v for k, v in env.items() if k.startswith("GIT_")} == {
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1"}
    assert env["PATH"] == "/usr/bin"


def test_an_idempotent_re_record_into_a_poisoned_artifact_is_refused():
    """Stage 2's should-fix: the artifact checks run on the unchanged list too. Another key's conflicting pair already
    poisons the artifact; re-recording this key's equal evidence must not answer idempotent, rc 0."""
    other = record(machine="aarch64")
    poisoned = [record(), other, dict(other, result_digest="b" * 64)]
    with pytest.raises(aw.AttestationRefused, match="would be poisoned"):
        aw.merged(poisoned, record(), git=fake_git())


def test_the_cli_never_builds_a_record(tmp_path, monkeypatch):
    """Stage 2, BLOCKING 2: a job input (evidence plus provenance, no key) is refused. A record built here would wrap
    THIS process's key around another build's evidence. Already-built records are what the CLI merges. (The artifact
    path is redirected, so no mutant of this arm can reach package data.)"""
    import contextlib
    import io
    monkeypatch.setattr(sv, "RUNTIMES", tmp_path / "sqlite_runtimes.json")
    d, c = evidence()
    job_input = tmp_path / "job.json"
    job_input.write_text(json.dumps({"result_digest": d, "confinement": c, "provenance": record()["provenance"]}))
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        rc = aw.main(["attestation_writer.py", str(job_input)])
    assert rc == 1 and "never builds one" in err.getvalue(), err.getvalue()
    assert not (tmp_path / "sqlite_runtimes.json").exists()


def test_a_record_the_reader_would_poison_is_never_written():
    """W2: one validator both directions — the prospective artifact must pass the reader's checks."""
    with pytest.raises(aw.AttestationRefused, match="would be poisoned"):
        aw.merged([{"manifest_algorithm": True, "schema_version": 16}], record(), git=fake_git())


# ---- publication (W6) and the round trip (W2) ------------------------------------------------------------------------
def test_a_written_record_reads_back_attested(tmp_path, monkeypatch):
    path = tmp_path / "sqlite_runtimes.json"
    assert aw.write(record(), path=path, git=fake_git()) == "written"
    monkeypatch.setattr(sv, "RUNTIMES", path)
    assert set(json.loads(path.read_text())) == {"attestations"}
    assert sv.runtime_status().status == "attested"


def test_a_failed_publish_leaves_the_artifact_unchanged_and_no_temporary(tmp_path, monkeypatch):
    path = tmp_path / "sqlite_runtimes.json"
    path.write_text(json.dumps({"attestations": []}))
    before = path.read_bytes()

    def boom(*a):
        raise OSError("disk full")
    monkeypatch.setattr(aw.os, "replace", boom)
    with pytest.raises(OSError):
        aw.write(record(), path=path, git=fake_git())
    assert path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["sqlite_runtimes.json"]


def test_an_artifact_with_a_foreign_top_level_key_is_refused(tmp_path):
    path = tmp_path / "sqlite_runtimes.json"
    path.write_text(json.dumps({"attestations": [], "runtimes": []}))
    with pytest.raises(aw.AttestationRefused, match="top level"):
        aw.write(record(), path=path, git=fake_git())


def test_the_release_check_reports_every_stale_attestation_record():
    """S77 (round 13, finding 3) on the attestation class: superseded and future-revision records never disqualify a
    build at open time (the reader reads current records), and the release check reports EACH for cleanup; a current
    record and a malformed one are not its to report. A FUTURE record's remedy never says remove (S75: that is the
    downgrade it forbids) nor re-attest (the writer refuses to). Mutants: drop either revision from the report; give
    the future record superseded's remedy."""
    sys.path.insert(0, str(ROOT / "specs"))
    import schema_evidence as ev
    current = record()
    superseded = record(manifest_algorithm=sv.MANIFEST_ALGORITHM - 1)
    future = record(commit=B, schema_version=sv.SCHEMA_VERSION + 1, machine="aarch64")
    malformed = {"manifest_algorithm": True}
    found = ev.stale_attestation_problems([current, superseded, future, malformed, 42])          # total
    assert len(found) == 2 and "superseded revision" in found[0] and "re-attest or remove" in found[0], found
    assert "future revision" in found[1] and "cannot read" in found[1] and "remove" not in found[1], found   # S75
    assert sv.attested_key(sv.attestation_key(current), [current, superseded, future])   # never disqualifying
    assert ev.stale_attestation_problems([current]) == []


def test_the_release_check_itself_carries_the_stale_record_report(monkeypatch, capsys):
    """S77's report is the RELEASE CHECK's, not only a helper's: a superseded record planted in the artifact reaches
    `check()`'s problems, and without it the report is absent (the control). Release probing is stubbed as in
    test_schema_model's missing-versions precedent; skips outside a git checkout, where check() returns 2 first."""
    sys.path.insert(0, str(ROOT / "specs"))
    import schema_evidence as ev
    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=ROOT, capture_output=True).returncode:
        pytest.skip("no git checkout: check() returns 2 before reaching this")
    monkeypatch.setattr(ev, "_tags", lambda: [])
    monkeypatch.setattr(ev, "_probe_at", lambda ref, work: {"tag": ref, "commit": "x", "on_disk_user_version": 0,
                                                            "store_schema_version": 1, "digest": None, "result": "ok",
                                                            "_objects": {}})
    superseded = record(manifest_algorithm=sv.MANIFEST_ALGORITHM - 1)
    for planted, present in (([], False), ([superseded], True)):
        monkeypatch.setattr(sv, "attestations", lambda planted=planted: list(planted))
        ev.check()
        err = capsys.readouterr().err
        assert ("superseded revision" in err and "re-attest or remove it before release" in err) is present, err[-800:]


# ---- REAL repositories: they ground the injectable git's exit semantics (research's W10(c)) --------------------------
@pytest.fixture
def repo(tmp_path, monkeypatch):
    return _make_repo(tmp_path, monkeypatch)


def _make_repo(tmp_path, monkeypatch):
    """A real repository: commits A0 -> A1 on main, and a sibling S off A0. HOME is the test's own, so no developer
    configuration reaches git (BLOCKING 2's pins are the writer's own)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    r = tmp_path / "repo"
    r.mkdir()

    def g(*args, cwd=r):
        return subprocess.run(["git", *args], cwd=str(cwd), env=aw.git_env(), capture_output=True, text=True,
                              check=True).stdout.strip()
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "t")
    (r / "f").write_text("0")
    g("add", "f"); g("commit", "-q", "-m", "A0")
    a0 = g("rev-parse", "HEAD")
    g("checkout", "-q", "-b", "side")
    (r / "f").write_text("s")
    g("commit", "-q", "-am", "S")
    s = g("rev-parse", "HEAD")
    g("checkout", "-q", "main")
    (r / "f").write_text("1")
    g("commit", "-q", "-am", "A1")
    a1 = g("rev-parse", "HEAD")
    return {"path": r, "A0": a0, "A1": a1, "S": s, "git": g}


def test_real_an_ancestor_replaces(repo):
    assert aw.run_git(["merge-base", "--is-ancestor", repo["A0"], repo["A1"]], repo["path"])[0] == 0    # precondition
    out, outcome = aw.merged([record(commit=repo["A0"])], record(commit=repo["A1"]), repo=repo["path"])
    assert outcome == "replaced"


def test_real_the_same_commit_is_idempotent_not_a_replacement(repo):
    """v19 step 3 before step 4: a commit IS its own ancestor (real exit 0), so the same-commit step must come first."""
    assert aw.run_git(["merge-base", "--is-ancestor", repo["A1"], repo["A1"]], repo["path"])[0] == 0   # precondition
    out, outcome = aw.merged([record(commit=repo["A1"])], record(commit=repo["A1"]), repo=repo["path"])
    assert outcome == "idempotent"


def test_real_an_older_writing_commit_refuses(repo):
    repo["git"]("checkout", "-q", repo["A0"])                       # the writer stands at the OLDER commit
    assert aw.run_git(["rev-parse", "HEAD"], repo["path"])[1] == repo["A0"]                                # precondition
    with pytest.raises(aw.AttestationRefused, match="the writing commit .* is OLDER"):
        aw.merged([record(commit=repo["A1"])], record(commit=repo["A0"]), repo=repo["path"])


def test_real_a_sibling_branch_refuses(repo):
    assert aw.run_git(["merge-base", "--is-ancestor", repo["S"], repo["A1"]], repo["path"])[0] == 1        # precondition
    assert aw.run_git(["merge-base", "--is-ancestor", repo["A1"], repo["S"]], repo["path"])[0] == 1
    with pytest.raises(aw.AttestationRefused, match="sibling branches"):
        aw.merged([record(commit=repo["S"])], record(commit=repo["A1"]), repo=repo["path"])


def test_real_an_unknown_commit_is_unanswerable_not_older(repo):
    unknown = "c" * 40
    assert aw.run_git(["merge-base", "--is-ancestor", unknown, repo["A1"]], repo["path"])[0] == 128       # precondition
    with pytest.raises(aw.AttestationRefused, match="unanswerable: --is-ancestor exited 128"):
        aw.merged([record(commit=unknown)], record(commit=repo["A1"]), repo=repo["path"])


def test_real_a_shallow_clone_is_unanswerable_before_any_ancestry(repo, tmp_path):
    """Research's W10(c): the clone MUST be file:// — a plain local path ignores --depth and makes a FULL clone."""
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{repo['path']}", str(shallow)], env=aw.git_env(),
                   check=True, capture_output=True)
    assert aw.run_git(["rev-parse", "--is-shallow-repository"], shallow) == (0, "true")                  # precondition
    with pytest.raises(aw.AttestationRefused, match="unanswerable: the repository is shallow"):
        aw.merged([record(commit=repo["A0"])], record(commit=repo["A1"]), repo=shallow)


def test_real_the_records_commit_must_be_head(repo):
    """BLOCKING 1: an input commit that IS an ancestor of HEAD but not HEAD refuses, naming both."""
    with pytest.raises(aw.AttestationRefused) as e:
        aw.merged([], record(commit=repo["A0"]), repo=repo["path"])
    assert repo["A0"] in str(e.value) and repo["A1"] in str(e.value) and "not this checkout's HEAD" in str(e.value)


def test_real_a_planted_shallow_file_cannot_make_a_shallow_clone_answerable(repo, tmp_path, monkeypatch):
    """Stage 2, BLOCKING 1, measured by research: GIT_SHALLOW_FILE=/nonexistent made a shallow clone answer
    --is-shallow-repository "false". The writer's git never inherits it."""
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{repo['path']}", str(shallow)], env=aw.git_env(),
                   check=True, capture_output=True)
    monkeypatch.setenv("GIT_SHALLOW_FILE", str(tmp_path / "nonexistent"))
    leak = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=str(shallow), capture_output=True,
                          text=True, env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"}).stdout.strip()
    assert leak == "false"                                    # precondition: the variable DOES defeat the question
    with pytest.raises(aw.AttestationRefused, match="unanswerable: the repository is shallow"):
        aw.merged([record(commit=repo["A0"])], record(commit=repo["A1"]), repo=shallow)


def test_real_a_replace_ref_cannot_turn_a_true_ancestor_into_not_an_ancestor(repo):
    """Stage 2, BLOCKING 1: a refs/replace object that drops A1's parent made `--is-ancestor A0 A1` exit 1. The writer
    pins GIT_NO_REPLACE_OBJECTS=1, so the true ancestor still replaces."""
    g = repo["git"]
    tree = g("rev-parse", f"{repo['A1']}^{{tree}}")
    orphan = subprocess.run(["git", "commit-tree", tree, "-m", "no parent"], cwd=str(repo["path"]), env=aw.git_env(),
                            capture_output=True, text=True, check=True).stdout.strip()
    g("replace", repo["A1"], orphan)
    honoured = subprocess.run(["git", "merge-base", "--is-ancestor", repo["A0"], repo["A1"]], cwd=str(repo["path"]),
                              env={k: v for k, v in aw.git_env().items() if k != "GIT_NO_REPLACE_OBJECTS"}).returncode
    assert honoured == 1                                      # precondition: the replace ref DOES move the answer
    try:
        out, outcome = aw.merged([record(commit=repo["A0"])], record(commit=repo["A1"]), repo=repo["path"])
    except aw.AttestationRefused as exc:                      # the defect itself: a TRUE ancestor refused
        pytest.fail(f"a replace ref moved the writer's ancestry answer: {exc}")
    assert outcome == "replaced"


def test_real_an_inherited_git_dir_cannot_answer_for_another_repository(repo, tmp_path, monkeypatch):
    """BLOCKING 2: GIT_DIR pointing at ANOTHER repository is scrubbed, so HEAD is read from the repository the writer
    stands in."""
    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(other), env=aw.git_env(), check=True)
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "nope"))
    assert aw.run_git(["rev-parse", "HEAD"], repo["path"]) == (0, repo["A1"])
    out, outcome = aw.merged([], record(commit=repo["A1"]), repo=repo["path"])
    assert outcome == "written"


# ---- the writer's mutation matrix (P1; CLAUDE.md item 9) ------------------------------------------------------------
WRITER = ROOT / "specs" / "attestation_writer.py"
SHALLOW = ('''    rc, out = git(["rev-parse", "--is-shallow-repository"], repo)
    if rc != 0 or out != "false":
        raise AttestationRefused("unanswerable: the repository is shallow (or its shallowness cannot be read), so "
                                 "--is-ancestor's exit 1 would be ambiguous")
''')
ARM = "test_each_cross_run_arm_refuses_with_its_message"
MUTANTS = {
    # name: ([(anchor, replacement), ...], [(killing cell, its parameters), ...])
    "shallow check dropped": ([('    if rc != 0 or out != "false":\n', "    if False:\n")],
                              [(ARM, {"arm": "shallow"}), ("test_real_a_shallow_clone_is_unanswerable_before_any_ancestry", {})]),
    "shallow check after the ancestry": (
        [(SHALLOW, ""), ("        out.append(new)\n    # Both checks", "        out.append(new)\n"
                         + SHALLOW.replace("rc, out", "s_rc, s_out").replace("rc != 0 or out", "s_rc != 0 or s_out")
                         + "    # Both checks")],
        [("test_real_a_shallow_clone_is_unanswerable_before_any_ancestry", {})]),
    "same-commit step dropped": ([("    if old_commit == new_commit:", "    if False:")],
                                 [(ARM, {"arm": "the same commit, different evidence"}),
                                  ("test_the_same_commit_with_equal_evidence_is_idempotent", {})]),
    "same-commit step after --is-ancestor": (
        [("    if old_commit == new_commit:", '    if git(["merge-base", "--is-ancestor", old_commit, new_commit], repo)[0] == 0:\n'
          '        return "replace"\n    if old_commit == new_commit:')],
        [("test_real_the_same_commit_is_idempotent_not_a_replacement", {})]),
    "any nonzero --is-ancestor read as 'not an ancestor'": ([("    if rc == 1:\n        rrc", "    if rc != 0:\n        rrc")],
        [(ARM, {"arm": "--is-ancestor unanswerable"}), ("test_real_an_unknown_commit_is_unanswerable_not_older", {})]),
    "any nonzero reverse read as 'sibling'": ([("        if rrc == 1:\n", "        if rrc != 0:\n")],
                                              [(ARM, {"arm": "the reverse unanswerable"})]),
    "a claimed commit accepted": ([("    if rc != 0 or head != commit:\n", "    if rc != 0:\n")],
                                  [(ARM, {"arm": "the record's commit is not HEAD"}), ("test_real_the_records_commit_must_be_head", {})]),
    "fixture commit mark dropped": ([('j["commit"] == FIXTURE_COMMIT or ', "")],
                                    [("test_a_fixture_mark_is_refused_by_the_writer", {"mark": "commit"})]),
    "fixture run-id mark dropped": ([(' or j["run_id"].startswith("fixture-")', "")],
                                    [("test_a_fixture_mark_is_refused_by_the_writer", {"mark": "run_id"})]),
    "a future revision overwritten (S75)": ([('        if rev == "future":\n', "        if False:\n")],
        [("test_a_future_revision_of_this_key_is_never_overwritten_and_another_keys_does_not_block", {})]),
    "the key reduced to (version, source_id) (W7)": (
        [("sv.attestation_key(r) != key:", '(r.get("sqlite_version"), r.get("source_id")) != (new["sqlite_version"], new["source_id"]):')],
        [("test_a_superseded_revision_is_replaced_only_on_the_full_key", {}),
         ("test_a_future_revision_of_this_key_is_never_overwritten_and_another_keys_does_not_block", {})]),
    "a superseded record kept": ([("            continue                                  # 10(a)", "            out.append(r); continue  # 10(a)")],
                                 [("test_a_superseded_revision_is_replaced_only_on_the_full_key", {})]),
    "another key's record dropped (W6)": ([("            out.append(r)                             # another key", "            pass  # another key")],
                                          [("test_an_ancestor_replaces_and_every_other_key_is_kept", {})]),
    "the new record unvalidated": ([('    if problems:\n        raise AttestationRefused(f"the record is malformed', '    if False:\n        raise AttestationRefused(f"the record is malformed')],
                                   [("test_a_record_with_a_failed_confinement_probe_is_refused_as_malformed", {})]),
    "the prospective artifact unvalidated": ([('    if problems:\n        raise AttestationRefused(f"the prospective', '    if False:\n        raise AttestationRefused(f"the prospective')],
                                             [("test_a_record_the_reader_would_poison_is_never_written", {})]),
    "the round trip dropped": ([("    if not sv.attested_key(key, out):\n", "    if False:\n")],
                               [("test_a_record_that_would_not_read_back_attested_is_refused", {})]),
    "git's environment unscrubbed": ([('if not k.startswith("GIT_")}', "if True}")],
        [("test_real_an_inherited_git_dir_cannot_answer_for_another_repository", {}),
         ("test_git_env_scrubs_inherited_repository_variables_and_pins_config", {})]),
    "global config not pinned": ([('"GIT_CONFIG_GLOBAL": os.devnull, ', "")],
                                 [("test_git_env_scrubs_inherited_repository_variables_and_pins_config", {})]),
    "a named scrub list (stage 2)": ([('if not k.startswith("GIT_")}', 'if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_INDEX_FILE", "GIT_CEILING_DIRECTORIES")}')],
                                     [("test_real_a_planted_shallow_file_cannot_make_a_shallow_clone_answerable", {}),
                                      ("test_git_env_scrubs_inherited_repository_variables_and_pins_config", {})]),
    "replace objects honoured (stage 2)": ([(', "GIT_NO_REPLACE_OBJECTS": "1"}', "}")],
                                           [("test_real_a_replace_ref_cannot_turn_a_true_ancestor_into_not_an_ancestor", {})]),
    "idempotent skips the artifact checks (stage 2)": ([('            out, outcome = list(records), "idempotent"\n            break', '            return list(records), "idempotent"')],
                                                       [("test_an_idempotent_re_record_into_a_poisoned_artifact_is_refused", {})]),
    "the CLI builds from a job input (stage 2)": ([('    records = data.get("records") if isinstance(data, dict) else data\n', '    records = ([build_record(data["result_digest"], data["confinement"], data["provenance"])]\n               if isinstance(data, dict) and "result_digest" in data else data)\n')],
                                                  [("test_the_cli_never_builds_a_record", {})]),
    "publication not atomic": ([("        os.replace(tmp, path)\n", "        path.write_text(pathlib.Path(tmp).read_text())\n")],
                               [("test_a_failed_publish_leaves_the_artifact_unchanged_and_no_temporary", {})]),
    "an idempotent write rewrites the file": ([('    if set(outcomes.values()) <= {"idempotent"}:\n        return outcomes\n', "")],
                                              [("test_the_same_commit_with_equal_evidence_is_idempotent", {})]),
    "the top level left open": ([("    if not isinstance(data, dict) or set(data) - sv.ARTIFACT_KEYS or ", "    if not isinstance(data, dict) or ")],
                                [("test_an_artifact_with_a_foreign_top_level_key_is_refused", {})]),
}


def _load_writer(text, name):
    import types
    mod = types.ModuleType(name)
    mod.__file__ = str(WRITER)
    exec(compile(text, str(WRITER), "exec"), mod.__dict__)
    return mod


def _run_cell(mod, cell, params, tmp_path_factory):
    """'pass', 'kill' (an assertion or DID NOT RAISE: the classifier's two kill kinds) or 'crash: <type>'."""
    import inspect
    this = sys.modules[__name__]
    fn = getattr(this, cell)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(this, "aw", mod)
        tmp = tmp_path_factory.mktemp("cell")
        args = {}
        for name in inspect.signature(fn).parameters:
            if name in params:
                args[name] = params[name]
            elif name == "tmp_path":
                args[name] = tmp
            elif name == "monkeypatch":
                args[name] = mp
            elif name == "repo":
                args[name] = _make_repo(tmp, mp)
            else:
                raise AssertionError(f"{cell}: no argument for {name}")
        try:
            fn(**args)
        except (AssertionError, pytest.fail.Exception):
            return "kill"
        except Exception as exc:  # noqa: BLE001 - a crash is reported, never counted as a kill
            return f"crash: {type(exc).__name__}: {exc}"
    return "pass"


def test_the_attestation_writer_mutation_matrix(tmp_path_factory):
    """P1's matrix for specs/attestation_writer.py: every mutant is killed BY ASSERTION in at least one of its named
    cells, each cell passing on the unmutated source loaded the same way (the control, run first and last). Each
    anchor must occur exactly once and the mutant must change the bytes (mutate.py's rule)."""
    text = WRITER.read_text()
    cells = sorted({(c, tuple(sorted(p.items()))) for _, kills in MUTANTS.values() for c, p in kills})

    def control(label):
        mod = _load_writer(text, "aw_control")
        bad = {c: r for c, p in cells if (r := _run_cell(mod, c, dict(p), tmp_path_factory)) != "pass"}
        assert not bad, (label, bad)
    control("control, first")
    survivors = {}
    for name, (edits, kills) in MUTANTS.items():
        mutated = text
        for anchor, replacement in edits:
            assert mutated.count(anchor) == 1, (name, anchor)
            mutated = mutated.replace(anchor, replacement)
        assert mutated != text, name
        mod = _load_writer(mutated, "aw_mutant")
        results = {c: _run_cell(mod, c, p, tmp_path_factory) for c, p in kills}
        if "kill" not in results.values():
            survivors[name] = results
    control("control, last")
    assert not survivors, survivors
