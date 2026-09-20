"""specs/0042 INV-7 — OBSERVATION-ONLY, as a FOUR-ARM decision-trace diff (tranche 6b, 2026-09-19).

The frozen invariant: capture the decision trace with counters HEALTHY, FORCED TO ERROR and on an
UNINSTRUMENTED tree, and assert the traces byte-identical; the bypass at the four hot predicates
(tranche 2b) adds a fourth arm — instrumented but BYPASSED, the shipped default. The trace comes from
an instrument that is not the census (`specs/evidence/0042/inv7_observer.py`: every declared
enforcement function wrapped from outside, one content-free record per exit), because "two arms that
share the instrument cannot detect the instrument".

Three legs here:
  1. THE MINIATURE, in-process: the runtime leg's declining executions (tests/test_0042_sites.py —
     one per declared id) replayed under healthy, failing and off with the observer installed; the
     three observer traces are one byte string. The uninstrumented arm cannot run in-process (it is a
     different src tree), so:
  2. THE PINNED TRANSCRIPT: `specs/evidence/0042/inv7_transcript.txt` is the harness's four-arm run
     over the named suites, pinned to the commit it ran against; the pin must be an ancestor of HEAD
     with src/ unchanged since, and the transcript must read IDENTICAL with the exclusions it names
     equal to the ones the declaration derives today.
  3. THE MATRIX: the harness's comparison fails on each mutant (a changed record, a shorter arm, a
     census sequence the observer did not see, an id outside the declaration, a measured counter in
     the failing arm).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"
TRANSCRIPT = EVIDENCE / "inv7_transcript.txt"


def _load(name, path):
    """By path (tests/ is not a package) and REGISTERED in sys.modules: the observer rebinds from-import
    bindings by sweeping sys.modules, so a module it cannot see would call around it."""
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m


observer = _load("inv7_observer", EVIDENCE / "inv7_observer.py")
harness = _load("inv7_harness", EVIDENCE / "inv7_harness.py")
declaration = _load("inv7_declaration", EVIDENCE / "declaration.py")
ID_TO_SYMBOL = {row[0]: row[3] for row in declaration.DECLARATION}


def _nested_symbols():
    """The declared symbols an outside instrument cannot reach: nested inside a function."""
    out = set()
    for sym in {row[3] for row in declaration.DECLARATION}:
        parts = sym.split(":")[1].split(".")
        if len(parts) > 1 and not parts[0][0].isupper():
            out.add(sym)
    return out


# ---- leg 1: the miniature -------------------------------------------------------------------------

# loaded at COLLECTION, like the leg itself: its SITES snapshot reads the registry at import, and the census
# tests' autouse fixture clears the registry once tests RUN — a fixture-time load would snapshot nothing
LEG = _load("inv7_sites_leg", ROOT / "tests" / "test_0042_sites.py")


@pytest.fixture(autouse=True)
def _observer_state_restored():
    """EVERY upper-case module-level name of the observer, DERIVED from the module, must be classified by it as
    mutable state (`observer._STATE`, snapshotted before each test and restored after it — containers in place,
    scalars by assignment) or as a constant excluded by name with a reason (`observer._CONSTANTS`); a name in
    neither, or in both, fails here. Research, round 7: three leaks of this class in one round — restore-what-you-
    touch is a per-test discipline over fourteen things, and the fifteenth, or the first forgotten one, comes back
    as a wrong symbol index that is silent, order-dependent, and reads as a real divergence; and a filter over
    CONTAINERS alone would not see a scalar flag, so the derivation is over every upper-case name and the module
    must classify each."""
    import copy, re
    derived = {n for n in vars(observer) if re.fullmatch(r"_?[A-Z][A-Z0-9_]*", n)}
    state, consts = set(observer._STATE), set(observer._CONSTANTS)
    assert not (state & consts), sorted(state & consts)
    assert derived == state | consts, (sorted(derived - (state | consts)), sorted((state | consts) - derived),
                                        "an upper-case name of the observer is not classified as state or constant (or is declared and absent)")
    assert all(isinstance(r, str) and r for r in observer._CONSTANTS.values())
    snapshot = {n: copy.copy(getattr(observer, n)) for n in state}
    constants = {n: copy.copy(getattr(observer, n)) for n in consts}
    yield
    # a constant is ASSERTED constant, not declared so (research): a mutable thing misfiled under _CONSTANTS with a
    # plausible reason would be excluded from restore and the pollution class would return silently
    changed = sorted(n for n in consts if getattr(observer, n) != constants[n])
    assert changed == [], (changed, "a name classified as a constant was changed by this test — reclassify it as state")
    for n in state:
        v, s = getattr(observer, n), snapshot[n]
        if isinstance(v, (dict, set)):
            v.clear(); v.update(s)
        elif isinstance(v, (list, bytearray)):
            v[:] = s
        else:
            setattr(observer, n, s)


@pytest.fixture(scope="module")
def leg():
    """The runtime leg's tables (tests/ is not a package; loaded by path at collection)."""
    return LEG


def _replay(arm, leg, skip=()):
    from veracium import census
    observer.install(str(EVIDENCE / "declaration.py"))
    observer.reset_records()
    orig_bump = census.Site._bump
    # counters are read from the leg's SITES snapshot (the Site objects captured at its import), never from
    # census.counters(): the census tests' autouse fixture CLEARS the registry, so under a shuffled order the
    # registry is empty here while the module-level sites keep counting (the sites leg's own rule)
    def _counters():
        return {sid: site.counters() for sid, site in leg.SITES.items()}
    before = _counters()
    census.trace_reset()
    try:
        if arm in ("healthy", "failing"):
            census.enable(True); census.trace(True)
            if arm == "failing":
                def boom(self, field):
                    raise census.CensusError("INV-7 forced counter failure")
                census.Site._bump = boom
        else:
            census.enable(False)
        for sid in sorted(leg.DECLINES):
            if sid in skip:
                continue
            entry = leg.DECLINES[sid]
            with pytest.MonkeyPatch.context() as mp:
                if isinstance(entry, leg.TwoPhase):
                    entry.run(entry.setup(mp))
                else:
                    entry(mp)
        for sid in sorted(leg.SURFACE_DRIVEN):
            leg.SURFACE_DRIVEN[sid]()
        after = _counters()
        deltas = {sid: {k: after[sid][k] - before[sid][k] for k in ("consulted", "fired", "errors")} for sid in after}
        return {"bytes": observer.records(), "decoded": observer.decoded(),
                "census_trace": census.trace_snapshot(), "counters": deltas}
    finally:
        census.Site._bump = orig_bump
        census.enable(False); census.trace(False); census.trace_reset()
        observer.uninstall()


@pytest.fixture(scope="module")
def arms(leg):
    return {arm: _replay(arm, leg) for arm in ("healthy", "failing", "off")}


def test_the_three_in_process_arms_produce_one_observer_trace(arms, leg):
    h, f, o = arms["healthy"], arms["failing"], arms["off"]
    assert h["bytes"] and h["bytes"] == f["bytes"] == o["bytes"], \
        {"healthy/failing": harness.first_divergence(h["bytes"], f["bytes"]),
         "healthy/off": harness.first_divergence(h["bytes"], o["bytes"])}
    # the replay REACHES the declared functions: every id the leg declines maps to a symbol the
    # observer recorded, except the nested ones it cannot wrap (named, derived)
    observed = {s for s, _, _ in h["decoded"]}
    expected = {ID_TO_SYMBOL[sid] for sid in list(leg.DECLINES) + list(leg.SURFACE_DRIVEN)} - _nested_symbols()
    assert expected <= observed, sorted(expected - observed)


def test_the_census_sees_a_subsequence_of_what_the_observer_sees(arms):
    for arm in ("healthy", "failing"):
        obs = [s for s, _, _ in arms[arm]["decoded"]]
        nested = _nested_symbols()
        needle = [ID_TO_SYMBOL[rec[1]] for rec in arms[arm]["census_trace"]
                  if rec[1] in ID_TO_SYMBOL and ID_TO_SYMBOL[rec[1]] not in nested]
        assert needle, arm
        assert harness.subsequence_match(needle, obs) == len(needle), arm


def test_the_failing_arm_is_unmeasured_everywhere_and_the_off_arm_counts_nothing(arms, leg):
    c = arms["failing"]["counters"]
    touched = {sid for sid, v in c.items() if v["errors"] or v["consulted"] or v["fired"]}
    assert touched == set(leg.DECLINES) | set(leg.SURFACE_DRIVEN), (sorted(touched ^ (set(leg.DECLINES) | set(leg.SURFACE_DRIVEN))))
    assert all(c[sid]["errors"] > 0 and c[sid]["consulted"] == 0 and c[sid]["fired"] == 0 for sid in touched)
    assert all(v == {"consulted": 0, "fired": 0, "errors": 0} for v in arms["off"]["counters"].values())
    # and the healthy arm measured every one of them
    hc = arms["healthy"]["counters"]
    assert all(hc[sid]["consulted"] >= 1 and hc[sid]["fired"] >= 1 and hc[sid]["errors"] == 0 for sid in touched)


def test_the_comparison_can_fail_a_replay_that_took_a_different_path(arms, leg):
    """The negative control: skip one declining execution and the trace diverges at a named record."""
    victim = sorted(leg.DECLINES)[len(leg.DECLINES) // 2]
    other = _replay("healthy", leg, skip=(victim,))
    assert other["bytes"] != arms["healthy"]["bytes"]
    i = harness.first_divergence(other["bytes"], arms["healthy"]["bytes"])     # a BYTE index; records are 3 bytes
    assert i is not None and 0 <= i // observer.RECORD_WIDTH <= len(other["decoded"])


# ---- leg 2: the pinned four-arm transcript ------------------------------------------------------------

def _pin(text):
    m = re.search(r"^# generated \S+ against veracium @ ([0-9a-f]{7,40})$", text, re.M)
    assert m, "no pin line"
    return m.group(1)


def test_the_pinned_transcript_is_this_tree_and_reads_identical_across_four_arms():
    text = TRANSCRIPT.read_text()
    pin = _pin(text)
    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"], capture_output=True).returncode != 0:
        pytest.skip("no repository here: the transcript's pin cannot be checked against history")
    present = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{pin}^{{commit}}"], capture_output=True)
    assert present.returncode == 0, f"pin {pin[:7]} is not a commit here"
    anc = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", pin, "HEAD"], capture_output=True, text=True)
    if anc.returncode == 128:
        pytest.skip("shallow repository: the pin's ancestry cannot be checked")
    assert anc.returncode == 0, f"pin {pin[:7]} is not an ancestor of HEAD"
    moved = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", pin, "HEAD", "--", "src/"], capture_output=True, text=True).stdout.split()
    assert moved == [], f"src/ changed since the transcript's pin: {moved} — re-run the harness and re-pin"
    assert re.search(r"^VERDICT: observer traces IDENTICAL across 4 arms", text, re.M), "the transcript does not read IDENTICAL over four arms"
    rows = re.findall(r"^(healthy|failing|off|uninstrumented)\s+(\d+)\s+([0-9a-f]{64})\s+(.*)$", text, re.M)
    assert [r[0] for r in rows] == ["healthy", "failing", "off", "uninstrumented"]
    assert all(int(r[1]) > 0 for r in rows)
    # the verdict is PER TEST (a whole-trace digest also carries the non-reproducible tests' bytes, which is
    # why the arms' digests may differ while every compared test agrees): each arm compared with none differing
    per_arm = re.findall(r"^  (healthy|failing|off): (\d+) tests compared, (\d+) differing, (\d+) not in both$", text, re.M)
    assert [a for a, *_ in per_arm] == ["healthy", "failing", "off"], per_arm
    assert all(int(c) > 0 and d == "0" and n == "0" for _, c, d, n in per_arm), per_arm
    assert len({c for _, c, *_ in per_arm}) == 1                     # the same compared set in every arm
    # and the census arms' cross-checks read as the invariant requires
    assert re.search(r'^  healthy: \{.*"any_errors": false.*"subsequence_holds": true', text, re.M)
    assert re.search(r'^  failing: \{.*"all_unmeasured": true.*"subsequence_holds": true', text, re.M)
    assert re.search(r'^  off: \{"census_enabled": false, "registry_size": (\d+)\}', text, re.M).group(1) == str(len(declaration.DECLARED_IDS))
    assert re.search(r'^  uninstrumented: \{"census_enabled": false, "registry_size": 0', text, re.M)
    # the tests the run could not compare are NAMED (a reader sees the boundary of the claim), each a node id
    m = re.search(r"^EXCLUDED AS NON-REPRODUCIBLE.*$", text, re.M); assert m, "the transcript does not state its exclusions"
    over = re.search(r"over (\d+) tests \(reference: uninstrumented; (\d+) tests excluded", text); assert over
    assert int(over.group(1)) > 0
    tail = []
    for line in text[m.end():].splitlines()[1:]:      # the indented lines under the heading, and nothing after
        if not line.startswith("  "):
            break
        tail.append(line.strip())
    excluded_tests = [l for l in tail if l and l != "(none)"]
    assert len(excluded_tests) == int(over.group(2)) and all("::" in t for t in excluded_tests), excluded_tests
    # the exclusions the transcript names are exactly the nested symbols the declaration derives today
    excluded = set(re.findall(r"^  (\S+\.py:\S+): nested inside a function", text, re.M))
    assert excluded == _nested_symbols(), (sorted(excluded ^ _nested_symbols()))
    # the suites the transcript ran are the committed NAMED suites, derived by the reach measurement from the
    # spec's sentence plus a greedy cover — and the reach table's own list is that file
    named = json.loads((EVIDENCE / "inv7_named_suites.json").read_text())
    suites_line = re.search(r"^suites: (.*)$", text, re.M).group(1).split()
    assert suites_line == named, (suites_line[:3], named[:3])
    reach_text = (EVIDENCE / "inv7_reach_table.txt").read_text()
    listed = re.findall(r"^  (tests/\S+)$", reach_text.split("NAMED SUITES", 1)[1], re.M)
    assert listed == named
    assert all(f in named for f in harness.SPEC_NAMED_SUITES if f in reach_text), "a spec-named suite the reach measured is missing from the named set"
    # the src commits between the twin and the pin are LISTED (a reader sees what the twin lacks); the claim
    # that matters is asserted elsewhere: the uninstrumented arm registered zero sites. (A first version asserted
    # every listed commit was an 0042 tranche — true until the next spec touched src; a census of the moment
    # mistaken for a rule.)
    # the twin is DERIVED from HEAD by removing the instrumentation (2026-09-19; an exported old commit is a
    # different product as soon as src/ moves for any other reason): the transcript states the derivation and
    # the number of sites removed equals the declaration's ids at HEAD — the twin lacks exactly what HEAD declares
    m = re.search(r"^twin \(uninstrumented\): derived from HEAD ([0-9a-f]{40}) by inv7_uninstrument\.py$", text, re.M)
    assert m, "the transcript's twin is not the derived one"
    assert m.group(1) == pin
    d = re.search(r"^twin derivation: (\d+) declare_site removed, (\d+) fire\(\) unwrapped, (\d+) consult blocks spliced, (\d+) census-enabled bypass blocks removed", text, re.M)
    assert d, "the transcript does not state the derivation"
    assert int(d.group(1)) == len(declaration.DECLARED_IDS), (d.group(1), len(declaration.DECLARED_IDS))
    assert int(d.group(2)) > 0 and int(d.group(3)) > 0 and int(d.group(4)) == 4       # the four hot-predicate bypasses


# ---- leg 3: the harness's mutation matrix ------------------------------------------------------------

def _fabricate(tmp_path, arm, records, symbols=("m.py:f", "m.py:g"), labels=("None", "ValueError"), census=None, counters=None, enabled=False, boundaries=None, registry_size=2):
    d = tmp_path / arm; d.mkdir()
    recs = [(r[0], 0, r[1]) if len(r) == 2 else tuple(r) for r in records]       # (symbol, exit ordinal, label)
    raw = bytes(b for r in recs for b in r)
    (d / "observer_trace.bin").write_bytes(raw)
    bounds = boundaries if boundaries is not None else [[0, "t.py::a"], [2, "t.py::b"]]
    (d / "test_boundaries.jsonl").write_text("".join(json.dumps(b) + "\n" for b in bounds))
    summary = {"symbols": list(symbols), "labels": list(labels), "records": len(recs), "record_width": 3, "census_enabled": enabled,
               "census_registry_size": registry_size, "veracium_file": "x", "pytest_exit": 0}
    if census is not None:
        (d / "census_trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in census))
        summary["census_counters"] = counters or {}
    return summary


def test_the_harness_comparison_fails_on_each_mutant(tmp_path):
    """The matrix for specs/evidence/0042/inv7_harness.py (its `# Mutation-Matrix:` pointer names this test):
    the comparison is loaded here, from the file, and driven on fabricated arms."""
    harness = _load("inv7_harness_matrix", EVIDENCE / "inv7_harness.py")
    ids = {"a.id": "m.py:f", "b.id": "m.py:g"}
    good = [(0, 0), (1, 1), (0, 1)]
    healthy_census = [(1, "a.id", "None"), (2, "b.id", "ValueError")]
    ok_counters = {"a.id": {"consulted": 1, "fired": 1, "errors": 0}, "b.id": {"consulted": 1, "fired": 1, "errors": 0}}
    failing_counters = {"a.id": {"consulted": 0, "fired": 0, "errors": 2}, "b.id": {"consulted": 0, "fired": 0, "errors": 2}}
    S = {"healthy": _fabricate(tmp_path, "healthy", good, census=healthy_census, counters=ok_counters, enabled=True),
         "failing": _fabricate(tmp_path, "failing", good, census=healthy_census, counters=failing_counters, enabled=True),
         "off": _fabricate(tmp_path, "off", good), "uninstrumented": _fabricate(tmp_path, "uninstrumented", good)}
    arms = ["healthy", "failing", "off", "uninstrumented"]
    verdict, checks = harness.compare(tmp_path, arms, S, ids)
    assert verdict["identical"] and verdict["divergences"] == {}
    assert checks["healthy"]["subsequence_holds"] and checks["failing"]["all_unmeasured"]
    # mutant 1: one record changed in one arm → divergent, decoded at the record
    (tmp_path / "off" / "observer_trace.bin").write_bytes(bytes([0, 0, 0, 1, 0, 0, 0, 0, 1]))
    v, _ = harness.compare(tmp_path, arms, S, ids)
    assert not v["identical"] and v["divergences"]["off"]["first_index"] == 1
    assert v["divergences"]["off"]["this"] == ("m.py:g", 0, "None") and v["divergences"]["off"]["reference"] == ("m.py:g", 0, "ValueError")
    # mutant 2: an arm cut short → divergent at the shorter length
    (tmp_path / "off" / "observer_trace.bin").write_bytes(bytes([0, 0, 0, 1, 0, 1]))
    v, _ = harness.compare(tmp_path, arms, S, ids)
    assert not v["identical"] and v["divergences"]["off"]["first_index"] == 2 and v["divergences"]["off"]["lengths"] == [2, 3]
    (tmp_path / "off" / "observer_trace.bin").write_bytes(bytes(b for s, l in good for b in (s, 0, l)))
    # mutant 3: the census claims a fired sequence the observer never saw → the subsequence check fails
    (tmp_path / "healthy" / "census_trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in [(1, "b.id", "x"), (2, "b.id", "x"), (3, "b.id", "x")]))
    _, c = harness.compare(tmp_path, arms, S, ids)
    assert not c["healthy"]["subsequence_holds"]
    # mutant 4: a census id outside the declaration is LISTED, never silently dropped
    (tmp_path / "healthy" / "census_trace.jsonl").write_text(json.dumps((1, "phantom.id", "x")) + "\n")
    _, c = harness.compare(tmp_path, arms, S, ids)
    assert c["healthy"]["census_ids_not_in_declaration"] == ["phantom.id"]
    # mutant 5: a counter that MEASURED in the failing arm → not UNMEASURED everywhere
    S["failing"]["census_counters"] = {"a.id": {"consulted": 1, "fired": 0, "errors": 1}, "b.id": {"consulted": 0, "fired": 0, "errors": 2}}
    _, c = harness.compare(tmp_path, arms, S, ids)
    assert not c["failing"]["all_unmeasured"]
    # mutant 6: a compared test whose segment differs → DIVERGENT, and the TEST is named
    S["failing"]["census_counters"] = failing_counters
    (tmp_path / "off" / "observer_trace.bin").write_bytes(bytes([0, 0, 0, 1, 0, 1, 1, 0, 1]))     # test b's segment changed
    v, _ = harness.compare(tmp_path, arms, S, ids)
    assert not v["identical"] and v["per_test"]["off"]["differing"] == ["t.py::b"]
    assert v["divergences"]["off"]["owning_test"] == "t.py::b" and v["divergences"]["off"]["first_index"] == 2
    # mutant 7: the control run shows test b is NOT reproducible → b is excluded by name and the verdict holds on a
    _fabricate(tmp_path, "uninstrumented-control", [(0, 0, 0), (1, 0, 1), (1, 0, 0)])
    v, c = harness.compare(tmp_path, arms, S, ids, standing={})
    assert v["identical"] and v["control"]["non_reproducible"] == ["t.py::b"] and v["per_test"]["off"]["compared"] == 1
    # round 7 (research): b is NEWLY non-reproducible — excluded from the comparison, and a FINDING the exit refuses
    assert v["control"]["newly_non_reproducible"] == ["t.py::b"] and v["control"]["standing_excluded"] == []
    assert harness.final_status(v, c, S, arms) == 1 and v["gates"]["no_new_non_reproducible"] is False
    # … on the STANDING list by name with its cause, the same disagreement is an expected exclusion and the exit holds
    v, c = harness.compare(tmp_path, arms, S, ids, standing={"t.py::b": "fabricated: a known wall-clock dependence"})
    assert v["control"]["standing_excluded"] == ["t.py::b"] and v["control"]["newly_non_reproducible"] == [] and v["control"]["standing_causes"]["t.py::b"].startswith("fabricated")
    harness.final_status(v, c, S, arms); assert v["gates"]["no_new_non_reproducible"] is True     # (other gates carry earlier mutants' state)
    # a standing entry that names a test NOT in this run is neither excluded nor an error (it is listed as absent)
    v, _ = harness.compare(tmp_path, arms, S, ids, standing={"t.py::b": "x", "t.py::absent": "y"})
    assert v["control"]["standing_excluded"] == ["t.py::b"]
    # the real list loads and names its cause for every entry
    real = harness.load_standing_exclusions(); assert real and all(isinstance(k, str) and "::" in k and len(v_) > 40 for k, v_ in real.items())
    # … but a differing segment in test a still fails, control or no control
    (tmp_path / "off" / "observer_trace.bin").write_bytes(bytes([1, 0, 1, 1, 0, 1, 1, 0, 0]))
    v, _ = harness.compare(tmp_path, arms, S, ids)
    assert not v["identical"] and v["per_test"]["off"]["differing"] == ["t.py::a"]
    (tmp_path / "off" / "observer_trace.bin").write_bytes(bytes(b for s, l in good for b in (s, 0, l)))
    # a test present in one arm only is a divergence too
    _fabricate(tmp_path, "extra", good, boundaries=[[0, "t.py::a"], [2, "t.py::z"]])
    v, _ = harness.compare(tmp_path, arms + ["extra"], {**S, "extra": S["off"]}, ids)
    assert not v["identical"] and v["per_test"]["extra"]["tests_not_in_both"] == ["t.py::b", "t.py::z"]
    # the pure helpers, at their edges
    assert harness.first_divergence(b"", b"") is None and harness.first_divergence(b"\x00\x00", b"") == 0
    assert harness.subsequence_match([], ["x"]) == 0 and harness.subsequence_match(["x", "y"], ["x", "z", "y"]) == 2
    assert harness.subsequence_match(["y", "x"], ["x", "y"]) == 1


# ---- round 6 (2026-09-20), cells C and E ---------------------------------------------------------------------------

def test_r6_5_i_identical_bytes_with_different_dictionaries_are_different_traces(tmp_path):
    """R6-5(i): the comparison compared encoded bytes without their symbol and label tables — identical bytes whose
    label meant False in one arm and True in another read identical=True. Now the comparison is over the DECODED
    records and the transcript carries a dictionary-independent canonical digest per arm."""
    ids = {"a.id": "m.py:f"}
    good = [(0, 0), (0, 1)]
    S = {"uninstrumented": _fabricate(tmp_path, "uninstrumented", good, symbols=("m.py:f",), labels=("False", "True")),
         "healthy": _fabricate(tmp_path, "healthy", good, symbols=("m.py:f",), labels=("True", "False"), census=[], counters={}, enabled=True)}
    v, _ = harness.compare(tmp_path, ["uninstrumented", "healthy"], S, ids)
    assert not v["identical"] and v["per_test"]["healthy"]["differing"] == ["t.py::a"]     # both records sit in test a
    assert v["divergences"]["healthy"]["this"] == ("m.py:f", 0, "True") and v["divergences"]["healthy"]["reference"] == ("m.py:f", 0, "False")
    assert v["canonical_digest"]["healthy"] != v["canonical_digest"]["uninstrumented"]
    # the control: the same bytes with the SAME dictionaries are one trace, and their canonical digests agree
    S["healthy"] = _fabricate(tmp_path / "again", "healthy", good, symbols=("m.py:f",), labels=("False", "True"), census=[], counters={}, enabled=True) if (tmp_path / "again").mkdir() is None else None
    import shutil; shutil.copytree(tmp_path / "again" / "healthy", tmp_path / "healthy", dirs_exist_ok=True)
    v, _ = harness.compare(tmp_path, ["uninstrumented", "healthy"], S, ids)
    assert v["identical"] and v["canonical_digest"]["healthy"] == v["canonical_digest"]["uninstrumented"]


def test_r6_5_iii_the_harness_exit_requires_every_arm_and_every_cross_check(tmp_path):
    """R6-5(iii), EXECUTED against the real harness on the sealed package: a one-test suite that failed only in the
    twin gave exit 0. `final_status` is now the exit: identical AND every arm's pytest exit 0 AND every cross-check."""
    ids = {"a.id": "m.py:f", "b.id": "m.py:g"}
    good = [(0, 0), (1, 1), (0, 1)]
    census = [(1, "a.id", "None"), (2, "b.id", "ValueError")]
    ok = {"a.id": {"consulted": 1, "fired": 1, "errors": 0}, "b.id": {"consulted": 1, "fired": 1, "errors": 0}}
    fail = {"a.id": {"consulted": 0, "fired": 0, "errors": 2}, "b.id": {"consulted": 0, "fired": 0, "errors": 2}}
    S = {"healthy": _fabricate(tmp_path, "healthy", good, census=census, counters=ok, enabled=True),
         "failing": _fabricate(tmp_path, "failing", good, census=census, counters=fail, enabled=True),
         "off": _fabricate(tmp_path, "off", good), "uninstrumented": _fabricate(tmp_path, "uninstrumented", good, registry_size=0)}
    arms = ["healthy", "failing", "off", "uninstrumented"]
    v, c = harness.compare(tmp_path, arms, S, ids)
    assert harness.final_status(v, c, S, arms) == 0 and all(v["gates"].values()), v["gates"]
    # gate 1: an arm whose pytest did not exit 0 — the reproduction's case
    S["uninstrumented"]["pytest_exit"] = 1
    assert harness.final_status(v, c, S, arms) == 1 and v["gates"]["pytest_exit:uninstrumented"] is False
    S["uninstrumented"]["pytest_exit"] = 0
    # gate 2: a cross-check that does not hold (the failing arm measured something)
    c2 = json.loads(json.dumps(c)); c2["failing"]["all_unmeasured"] = False
    assert harness.final_status(v, c2, S, arms) == 1
    # gate 3: the census saw an id outside the declaration
    c3 = json.loads(json.dumps(c)); c3["healthy"]["census_ids_not_in_declaration"] = ["phantom.id"]
    assert harness.final_status(v, c3, S, arms) == 1
    # gate 4: the twin registered a site
    c4 = json.loads(json.dumps(c)); c4["uninstrumented"]["registry_size"] = 1
    assert harness.final_status(v, c4, S, arms) == 1
    # gate 5 (round 7, research): a control pair disagreeing on a test NOT on the standing list is a finding → exit 1;
    # the same test on the standing list by name → excluded, exit 0
    S["healthy-control"] = _fabricate(tmp_path, "healthy-control", [(0, 0), (1, 1), (1, 0)], census=census, counters=ok, enabled=True)
    v5, c5 = harness.compare(tmp_path, arms, S, ids, standing={})
    assert v5["control"]["newly_non_reproducible"] == ["t.py::b"] and harness.final_status(v5, c5, S, arms) == 1 and v5["gates"]["no_new_non_reproducible"] is False
    v6, c6 = harness.compare(tmp_path, arms, S, ids, standing={"t.py::b": "fabricated cause"})
    assert v6["control"]["standing_excluded"] == ["t.py::b"] and harness.final_status(v6, c6, S, arms) == 0


def _fire_exit_statements(tree, qual: str):
    """How many return/raise statements of the function `qual` (dotted, classes included) carry a `.fire(` call — the
    exits-per-function count the R6-5(ii) guard compares to the function's site count. None if `qual` is absent."""
    import ast
    found = [None]

    def walk(node, stack):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = ".".join(stack + [child.name])
                if q == qual and not isinstance(child, ast.ClassDef):
                    n = 0

                    def count(x):
                        nonlocal n
                        for c in ast.iter_child_nodes(x):
                            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                                continue
                            if isinstance(c, (ast.Return, ast.Raise)):
                                v = c.value if isinstance(c, ast.Return) else c.exc
                                if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "fire":
                                    n += 1
                            count(c)
                    count(child); found[0] = n
                walk(child, stack + [child.name])
    walk(tree, [])
    return found[0]


def test_r6_5_ii_every_declared_site_has_its_own_exit_statement_so_exit_keyed_records_separate_them():
    """R6-5(ii): an exit-keyed record separates two sites in one function only if they do not share a return/raise
    statement. Asserted over the declaration at HEAD: for every symbol carrying more than one site, the function's
    own fire() statements are at least as many as its sites (research's proxy count, made exact by the scanner's
    scope rules); a symbol failing this names the one function whose exits must be split."""
    import ast, collections
    by_symbol = collections.defaultdict(list)
    for row in declaration.DECLARATION:
        by_symbol[row[3]].append(row[0])
    src = ROOT / "src" / "veracium"; short = []
    for sym, sites in by_symbol.items():
        if len(sites) < 2:
            continue
        module, qual = sym.split(":"); tree = ast.parse((src / module).read_text())
        fires = _fire_exit_statements(tree, qual)
        assert fires is not None, sym
        if fires < len(sites):
            short.append((sym, len(sites), fires))
    multi = sum(1 for s in by_symbol.values() if len(s) > 1); held = sum(len(s) for s in by_symbol.values() if len(s) > 1)
    assert multi >= 1 and held >= 2                                     # the figure is real (88 of 162 at round 6)
    assert short == [], short


def test_r6_5_ii_control_two_sites_sharing_one_exit_statement_are_counted_short():
    """The guard's RED (research, round 7): a function whose two sites exit through ONE statement — the shape the
    old suite was silent on — counts one fire exit for two sites, which the guard above refuses; the same function
    with one exit per site counts two."""
    import ast
    shared = ast.parse("class C:\n    def f(self, x):\n        with A.consult():\n            with B.consult():\n"
                       "                return A.fire(B.fire(x))\n")
    split = ast.parse("class C:\n    def f(self, x):\n        with A.consult():\n            if x:\n                return A.fire(x)\n"
                      "        with B.consult():\n            return B.fire(x)\n")
    assert _fire_exit_statements(shared, "C.f") == 1 < 2          # two sites, one exit statement: SHORT
    assert _fire_exit_statements(split, "C.f") == 2                # one exit per site
    assert _fire_exit_statements(split, "C.g") is None            # an absent function is None, never a zero


def test_a_propagated_exception_is_never_attributed_to_a_walked_return_statement():
    """Research's mutant 1 (round 7): `try: return "A"` / `finally: boom()` reaches the return statement and exits by
    the callee's raise. The exception path must record EXIT_PROPAGATED (253) — the exception event's line is not a
    raise statement of this function — never the return's ordinal (the statement-line fallback is the RETURN path's
    witness only). Controls: a plain return (its ordinal), a raise statement (its ordinal), a propagated raise with no
    return walked (253)."""
    def boom():
        raise ValueError("callee")

    def plain(x):
        return x

    def raiser(x):
        raise KeyError(x)

    def control(x):
        y = boom()                                                 # the callee raises on a NON-exit line
        return y

    def on_the_return(x):
        return boom()                                              # the callee raises while the return statement executes

    def mutant(x):
        try:
            return "A"
        finally:
            boom()
    observer.reset_records(); observer._SYMBOLS[:] = ["t:plain", "t:raiser", "t:control", "t:on_the_return", "t:mutant"]
    observer._SYM_INDEX.clear(); observer._SYM_INDEX.update({s: i for i, s in enumerate(observer._SYMBOLS)})
    w = {i: observer._wrap_callable(fn, i) for i, fn in enumerate((plain, raiser, control, on_the_return, mutant))}
    w[0](1)
    for i in (1, 2, 3, 4):
        with pytest.raises((KeyError, ValueError)):
            w[i](1)
    recs = observer.decoded()
    assert recs[0] == ("t:plain", 0, "value")
    assert recs[1] == ("t:raiser", 0, "KeyError")
    assert recs[2] == ("t:control", observer.EXIT_PROPAGATED, "ValueError")
    # a raise DURING the return statement's own evaluation is attributed to that statement (the exception event's
    # line is the return line, which is in the exit map) — the label says it was a raise; stated, not hidden
    assert recs[3] == ("t:on_the_return", 0, "ValueError")
    assert recs[4] == ("t:mutant", observer.EXIT_PROPAGATED, "ValueError"), recs[4]      # the mutant: was (…, 0, …)
    observer.reset_records(); observer._SYMBOLS.clear(); observer._SYM_INDEX.clear()     # leave the tables as found


def test_r6_6_the_twin_transform_refuses_what_it_has_not_established_is_instrumentation_and_keeps_exits():
    """R6-6: the three round-6 cases (an unrelated `other.fire`, an unbound attribute chain, a side effect inside an
    enabled block) each REFUSE by name; an undeclared consult refuses; the recognised bypass is kept DEAD with its
    return statement in place (exit ordinals preserved) rather than deleted; the derived twin of THIS tree verifies
    clean and its manifest reports equal exit counts per function."""
    un = _load("inv7_uninstrument_r6", EVIDENCE / "inv7_uninstrument.py")
    refused = {
        "unrelated other.fire": "from .census import declare_site\nS = declare_site('x')\ndef f(other, x):\n    return other.fire(False)\n",
        "unbound attribute chain": "from .census import declare_site\nS = declare_site('x')\ndef g(a):\n    return a.b.c.fire(1)\n",
        "side effect inside an enabled block": "from . import census as _census\nfrom .census import declare_site\nS = declare_site('x')\ndef h(q):\n    if _census.enabled():\n        audit_log(q)\n        return q\n    return q\n",
        "consult on an undeclared name": "from .census import declare_site\nS = declare_site('x')\ndef k(o):\n    with o.consult():\n        return S.fire(o)\n",
        "a with mixing consult and another item": "from .census import declare_site\nS = declare_site('x')\ndef w(lock):\n    with S.consult(), lock:\n        return S.fire(None)\n",
    }
    for name, code in refused.items():
        with pytest.raises(un.Refused):
            un.uninstrument_source(code)
    # research's mutation campaign over the transform's refusals (round 7): neutering each `raise Refused` in turn found
    # three that no test drove — `global` naming a site (its `nonlocal` twin WAS driven), the consult STATEMENT on an
    # undeclared name (the `with` form was), and a bypass whose else branch does work — plus the no-argument fire.
    # Each is pinned to ITS OWN message, so another branch catching the input first would not pass for it.
    pinned = {
        "`global` names a declared site": "from .census import declare_site\nS = declare_site('x')\ndef f():\n    global S\n    return S.fire(1)\n",
        "consult\\(\\) statement on 'o', not a declared site": "from .census import declare_site\nS = declare_site('x')\ndef f(o):\n    o.consult()\n    return S.fire(1)\n",
        "else branch is not simple assignments": "from . import census as _census\nfrom .census import declare_site\nS = declare_site('x')\n"
                                                 "def h(self, q):\n    if _census.enabled():\n        with S.consult():\n            q = S.fire(q)\n    else:\n        audit(self)\n    return q\n",
        "fire\\(\\) with no decision argument": "from .census import declare_site\nS = declare_site('x')\ndef n():\n    return S.fire()\n",
    }
    for message, code in pinned.items():
        with pytest.raises(un.Refused, match=message):
            un.uninstrument_source(code)
    out, st = un.uninstrument_source("from . import census as _census\nfrom .census import declare_site\nS = declare_site('x')\n"
                                     "def p(self):\n    if _census.enabled():\n        with S.consult():\n            q = self.v()\n            return S.fire(q)\n    q = self.v()\n    return q\n")
    assert "if False:" in out and out.count("return q") == 2 and st["exits"] == {"p": 2} and st["bypasses"] == 1
    out2, st2 = un.uninstrument_source("from .census import declare_site\nS = declare_site('x')\ndef s(x):\n    S.consult()\n    if x:\n        raise S.fire(ValueError('no'))\n    return x\n")
    assert "consult" not in out2 and st2["consult_statements"] == 1 and st2["exits"] == {"s": 2}
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out_dir = pathlib.Path(d) / "src" / "veracium"
        totals = un.derive(ROOT / "src" / "veracium", out_dir)
        assert un.verify(out_dir, ROOT / "src" / "veracium") == []
        manifest = json.loads((out_dir.parent / "twin_manifest.json").read_text())
        assert manifest["totals"] == totals and totals["sites"] == len(declaration.DECLARATION)
        assert all("sha256_before" in m and "sha256_after" in m for m in manifest["modules"].values())
        changed = [m for m in manifest["modules"].values() if "exits" in m]
        assert changed and all(isinstance(m["exits"], dict) for m in changed)


def test_a_test_boundary_is_a_record_index_at_the_declared_width(tmp_path):
    """Round 7, found re-running the harness: the boundary side file was written as `len(bytes) // 2` after the
    records became three bytes, so every per-test segment was cut at 1.5x its true index — the per-test
    comparison compared misaligned windows and read a real divergence's owning test wrong. The boundary is a
    RECORD index: k records recorded, then a test starts, then its boundary is k, and the harness's owning_test
    maps record k to it and record k-1 to the test before."""
    observer.reset_records(); observer._BOUNDARIES.clear()
    observer._SYMBOLS[:] = ["m.py:f"]; observer._SYM_INDEX.clear(); observer._SYM_INDEX["m.py:f"] = 0
    observer.pytest_runtest_logstart("t.py::a", None)
    for _ in range(5):
        observer._record(0, 0, "None")
    observer.pytest_runtest_logstart("t.py::b", None)
    observer._record(0, 1, "None")
    assert observer._BOUNDARIES == [(0, "t.py::a"), (5, "t.py::b")], observer._BOUNDARIES
    assert len(observer.records()) == 6 * observer.RECORD_WIDTH
    (tmp_path / "test_boundaries.jsonl").write_text("".join(json.dumps(list(b)) + "\n" for b in observer._BOUNDARIES))
    assert harness.owning_test(tmp_path, 4) == "t.py::a" and harness.owning_test(tmp_path, 5) == "t.py::b"
    # the mutant: the old divisor puts b's boundary at 7 — past the end of a's five and one of b's records
    assert (5 * observer.RECORD_WIDTH) // 2 != 5
    observer.reset_records(); observer._BOUNDARIES.clear(); observer._SYMBOLS.clear(); observer._SYM_INDEX.clear()


def test_install_starts_from_an_empty_symbol_table_whatever_a_previous_test_left():
    """The floor lane, round 7 (found by CI after the push): a unit test left one entry in the observer's symbol
    table; under pytest-randomly it ran before the in-process arms, the first arm's install appended the declared
    symbols after it, and every record of that arm read one symbol index higher than the other two arms'. A
    symbol's index is its rank among the declared symbols — the same from a dirty table as from a clean one."""
    observer._SYMBOLS[:] = ["left.py:behind"]; observer._SYM_INDEX.clear(); observer._SYM_INDEX["left.py:behind"] = 0
    observer.install(str(EVIDENCE / "declaration.py"))
    try:
        dirty = list(observer._SYMBOLS)
    finally:
        observer.uninstall()
    observer.install(str(EVIDENCE / "declaration.py"))
    try:
        clean = list(observer._SYMBOLS)
    finally:
        observer.uninstall()
    assert dirty == clean and "left.py:behind" not in dirty and dirty[0] == sorted(dirty)[0]
    assert observer._SYMBOLS == [] and observer._SYM_INDEX == {}          # uninstall leaves the tables empty
