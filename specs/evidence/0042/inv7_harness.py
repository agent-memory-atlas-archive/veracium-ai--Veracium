"""specs/0042 INV-7 — THE FOUR-ARM DECISION-TRACE DIFF, run over the named suites.

Usage:
  inv7_harness.py trace --repo <root> --twin <commit> --out <dir> [--arms a,b,c,d] -- <test files…>
  inv7_harness.py reach --repo <root> --out <dir> -- <test files…>

`trace` runs the named suites once per arm under the independent observer (`inv7_observer.py`) —
healthy · failing · off (the shipped default, the bypass path) · uninstrumented (the twin tree, the
commit the instrumentation tranches began from, exported by `git archive` and put ahead of the
editable install on PYTHONPATH) — and compares the four observer traces byte for byte. It then
cross-checks the census against the observer in the two census arms (the census's fired sequence,
mapped id → symbol through the declaration, must be a subsequence of the observer's exit sequence),
asserts the failing arm is UNMEASURED everywhere and the off/uninstrumented arms carry no census
activity, and writes `inv7_transcript.txt` with every figure re-derived from the arm summaries.

`reach` runs the given suites once with the census enabled and records, per test file, which
declared ids its tests consulted — the measurement behind "the suites that actually reach the
sites".
"""
# Mutation-Matrix: tests/test_0042_inv7.py::test_the_harness_comparison_fails_on_each_mutant
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out

HERE = pathlib.Path(__file__).resolve().parent
ARMS = ("healthy", "failing", "off", "uninstrumented")

# INV-7's row names the suites that reach the instrumented sites — "0027's (graph.py) and the gate/ingest/
# schema suites"; these files are that sentence read against tests/, and the reach measurement then ADDS,
# greedily, the files that cover every id the whole suite reaches at all (a derivable set, not a hand list)
SPEC_NAMED_SUITES = (
    "tests/test_0027_policy_lane.py", "tests/test_0027_policy_receipt.py", "tests/test_0027_semantic_recall.py",
    "tests/test_compile_gate.py", "tests/test_0037_procedural.py",                        # the gates
    "tests/test_0019_ungrounded.py",                                                      # ingest
    "tests/test_0014_schema.py", "tests/test_schema_model.py",                            # schema
    "tests/test_0003_supersession_contested.py", "tests/test_0003_supersession_guard.py",
    "tests/test_0003_supersession_recall.py", "tests/test_0003_supersession_store.py",     # graph.py: supersession
)


def named_suites(reach: dict) -> list:
    """The spec-named files, then a greedy cover of every id any file reaches; deterministic (ties by name)."""
    sets = {f: set(ids) for f, ids in reach.items()}
    everything = set().union(*sets.values()) if sets else set()
    chosen = [f for f in SPEC_NAMED_SUITES if f in sets]
    covered = set().union(*(sets[f] for f in chosen)) if chosen else set()
    while covered != everything:
        best = min((f for f in sets if f not in chosen), key=lambda f: (-len(sets[f] - covered), f))
        if not sets[best] - covered:
            break
        chosen.append(best); covered |= sets[best]
    return chosen


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def export_twin(repo: pathlib.Path, commit: str, out: pathlib.Path) -> dict:
    """The uninstrumented twin. `commit == "derive"` (the default since 2026-09-19): HEAD's src with the census
    instrumentation REMOVED by `inv7_uninstrument.py` — the only twin that differs from HEAD by the instrumentation
    alone once other specs touch src. A commit id keeps the historical form (an export of an old tree) for the
    record; it is a different product as soon as src/ moved for any other reason."""
    twin = out / "twin"; twin.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("inv7_uninstrument", HERE / "inv7_uninstrument.py")
    un = importlib.util.module_from_spec(spec); spec.loader.exec_module(un)       # both branches ask its predicates
    if commit == "derive":
        totals = un.derive(repo / "src" / "veracium", twin / "src" / "veracium")
        # ROUND 7, F4d: WITH the source. Called without it, verify() checked only that no instrumentation token
        # survived — the preservation half was dead code in every run this harness ever made, so a twin that
        # differed from HEAD by more than the instrumentation would have passed here silently.
        problems = un.verify(twin / "src" / "veracium", repo / "src" / "veracium")
        assert not problems, problems
        head = sh(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
        return {"commit": f"derived from HEAD {head} by inv7_uninstrument.py", "src": str(twin / "src"), "src_commits_since_twin": [],
                "derivation": totals}
    full = sh(["git", "rev-parse", commit], cwd=repo).stdout.strip()
    p1 = subprocess.Popen(["git", "archive", full, "src/veracium"], cwd=repo, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(twin)], stdin=p1.stdout, check=True); p1.wait()
    assert p1.returncode == 0
    # the twin carries the census MODULE (tranche 1) and no site: `declare_site` occurs only in census.py
    hits = sh(["grep", "-rl", "declare_site", str(twin / "src" / "veracium")]).stdout.split()
    # ROUND 13 (research's R4, carried from round 12): "is this the census file?" asked of the ONE predicate, not by a
    # `Path.name` reading of its own — the fourth reading of that question, and the one the round-12 gate could not see
    # because it sits outside the transform's file.
    root = twin / "src" / "veracium"
    assert [un.is_census_module_file(pathlib.Path(h).relative_to(root)) for h in hits] == [True], hits
    since = sh(["git", "log", "--format=%h %s", f"{full}..HEAD", "--", "src/"], cwd=repo).stdout.strip().splitlines()
    return {"commit": full, "src": str(twin / "src"), "src_commits_since_twin": since}


def run_arm(repo, arm, suites, out, decl, twin_src=None, mode="trace", out_name=None):
    arm_out = out / (out_name or arm); arm_out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({"INV7_ARM": arm, "INV7_OUT": str(arm_out), "INV7_DECLARATION": str(decl), "INV7_MODE": mode,
                "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"})
    path = [str(HERE)] + ([twin_src] if twin_src else [])
    env["PYTHONPATH"] = os.pathsep.join(path + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    if twin_src:
        env["INV7_TWIN"] = twin_src
    cmd = [str(repo / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:randomly", "-p", "no:cacheprovider",
           "-p", "inv7_observer", *suites]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True)
    (arm_out / "pytest_stdout.txt").write_text(r.stdout); (arm_out / "pytest_stderr.txt").write_text(r.stderr)
    result_line = next((l for l in reversed(r.stdout.splitlines()) if " in " in l and ("passed" in l or "failed" in l or "error" in l)), "")
    summary = json.loads((arm_out / "summary.json").read_text(), object_pairs_hook=_strict_pairs)
    summary["pytest_exit"] = r.returncode; summary["pytest_result_line"] = result_line.strip()
    summary["wall_s"] = round(time.time() - t0, 1)
    (arm_out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


RECORD_WIDTH = 3   # (symbol, exit ordinal, label); the observer's constant, restated here and asserted equal per arm


def decode(arm_out: pathlib.Path, summary: dict):
    """The arm's records DECODED THROUGH ITS OWN DICTIONARIES: (symbol, exit ordinal, label). Round 6, R6-5(i): the
    comparison is over these canonical records, never over the bytes — two arms whose bytes agree but whose
    tables differ are DIFFERENT traces."""
    raw = (arm_out / "observer_trace.bin").read_bytes()
    w = summary.get("record_width", RECORD_WIDTH)
    if w != RECORD_WIDTH:
        raise ValueError(f"record width {w} != {RECORD_WIDTH}")
    syms, labs = summary["symbols"], summary["labels"]
    return [(syms[raw[i]], raw[i + 1], labs[raw[i + 2]]) for i in range(0, len(raw), w)]


def canonical_digest(records: list) -> str:
    """sha256 over the decoded records as JSON lines — what two arms are compared on, dictionary-independent."""
    h = hashlib.sha256()
    for r in records:
        h.update(json.dumps(list(r), separators=(",", ":")).encode()); h.update(b"\n")
    return h.hexdigest()


def first_divergence(a: list, b: list):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return None if len(a) == len(b) else n         # a common prefix: the divergence is where the shorter one ends


def owning_test(arm_out: pathlib.Path, index):
    """The test node whose execution produced record `index` (from the observer's boundary side file)."""
    p = arm_out / "test_boundaries.jsonl"
    if index is None or not p.exists():
        return None
    owner = None
    for line in p.read_text().splitlines():
        start, nodeid = json.loads(line, object_pairs_hook=_strict_pairs)
        if start <= index:
            owner = nodeid
        else:
            break
    return owner


def segments(arm_out: pathlib.Path, summary: dict) -> dict:
    """nodeid -> the arm's DECODED records produced while that test ran (from the boundary side file)."""
    recs = decode(arm_out, summary)
    bounds = [json.loads(l, object_pairs_hook=_strict_pairs) for l in (arm_out / "test_boundaries.jsonl").read_text().splitlines()]
    out = {}
    for k, (start, nodeid) in enumerate(bounds):
        end = bounds[k + 1][0] if k + 1 < len(bounds) else len(recs)
        out[nodeid] = tuple(recs[start:end])
    return out


def subsequence_match(needle: list[str], hay: list[str]) -> int:
    """How many of `needle` (in order) can be matched greedily inside `hay`; == len(needle) iff subsequence."""
    j = 0
    for x in hay:
        if j < len(needle) and x == needle[j]:
            j += 1
    return j


def load_declaration(path):
    spec = importlib.util.spec_from_file_location("inv7_decl", path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def load_standing_exclusions(path=None) -> dict:
    """The standing exclusion list (inv7_exclusions.STANDING): nodeid -> cause."""
    p = pathlib.Path(path) if path else HERE / "inv7_exclusions.py"
    spec = importlib.util.spec_from_file_location("inv7_exclusions", p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return dict(m.STANDING)


def compare(out: pathlib.Path, arms: list, summaries: dict, id_to_symbol: dict, standing: dict | None = None) -> tuple:
    """The verdict (observer traces identical across arms, first divergence decoded) and the cross-checks
    (census ⊆ observer in the census arms; UNMEASURED everywhere in the failing arm; no census activity
    in the off and uninstrumented arms). Pure over the arm directories, so a fabricated arm tests it."""
    ref = "uninstrumented" if "uninstrumented" in arms else arms[0]
    ref_dec = decode(out / ref, summaries[ref])
    verdict = {"reference_arm": ref, "identical": True, "divergences": {},
               "canonical_digest": {a: canonical_digest(decode(out / a, summaries[a])) for a in arms}}
    # THE CONTROL PAIR: the reference arm run twice. A test whose own trace differs between two runs of ONE
    # arm has inputs the run does not freeze (a directory order, a clock, state left by an earlier session);
    # it cannot witness the census either way and is EXCLUDED BY NAME. Every other test must match.
    ref_segments = segments(out / ref, summaries[ref])
    # Round 7: a control run may exist for ANY arm (main() runs one per arm); a test whose own trace differs
    # between the two runs of one arm has inputs the run does not freeze and is EXCLUDED BY NAME from every
    # cross-arm comparison — the union over arms. The reference-only pair missed noise that only the slowest
    # arm's timing sampled (the first round-7 run).
    # ROUND 9, F2: THE CONTROL SET HAS ONE DERIVATION, AND IT IS THIS ONE. It used to have two — `compare`
    # chose controls by DIRECTORY and substituted the main arm's summary for an absent one
    # (`summaries.get(arm + "-control", summaries[arm])`), while `final_status` gated the controls it found
    # among the summary KEYS. Two sets derived from different sources, free to disagree, and deleting one key
    # made them: the control was still compared (decoded through the WRONG arm's dictionaries) and its exit
    # check vanished, so a control run that FAILED gave exit 0. That is precisely the defect round 7's F3a
    # fix closed, restored by another route, because that fix changed the gate's source from `arms` to the
    # summary keys — both sets of what happens to be AVAILABLE, neither the set actually USED.
    # A control we cannot decode through its OWN dictionaries is not evidence: it is named here and it fails
    # the exit. It is never silently substituted.
    per_arm_ctl, ctl_without_summary = {}, []
    for arm in arms:
        control_dir = out / (arm + "-control")
        if control_dir.exists():
            key = arm + "-control"
            if key not in summaries:
                ctl_without_summary.append(key)
                continue
            segs_arm = ref_segments if arm == ref else segments(out / arm, summaries[arm])
            ctl = segments(control_dir, summaries[key])
            per_arm_ctl[arm] = {"tests": len(segs_arm), "non_reproducible": sorted(t for t in segs_arm if ctl.get(t) != segs_arm[t])}
    found = sorted(set().union(*(set(v["non_reproducible"]) for v in per_arm_ctl.values()))) if per_arm_ctl else []
    # Round 7 (research): the exclusion list is STANDING and NAMED (inv7_exclusions.STANDING, each entry with its cause),
    # never re-derived from this run alone; a test the control pairs found non-reproducible that is NOT on the list is
    # NEWLY non-reproducible — reported apart, and a FINDING that fails the exit (final_status), not housekeeping.
    standing = load_standing_exclusions() if standing is None else dict(standing)
    standing_present = sorted(t for t in standing if t in ref_segments)
    newly = sorted(t for t in found if t not in standing)
    nondet = sorted(set(standing_present) | set(newly))
    verdict["control"] = {"arms": per_arm_ctl, "without_summary": sorted(ctl_without_summary),
                          "tests": len(ref_segments), "non_reproducible": nondet,
                          "standing_excluded": standing_present, "standing_causes": {t: standing[t] for t in standing_present},
                          "newly_non_reproducible": newly}
    verdict["per_test"] = {}
    for arm in arms:
        if arm == ref:
            continue
        segs = segments(out / arm, summaries[arm])
        differing = sorted(t for t in ref_segments if t not in nondet and segs.get(t) != ref_segments[t])
        missing = sorted(set(ref_segments) ^ set(segs))
        verdict["per_test"][arm] = {"compared": len(ref_segments) - len(nondet), "differing": differing, "tests_not_in_both": missing}
        if differing or missing:
            verdict["identical"] = False
    for arm in arms:
        dec_a = decode(out / arm, summaries[arm]); dec_r = ref_dec
        if dec_a != dec_r and (verdict["per_test"].get(arm, {}).get("differing") or verdict["per_test"].get(arm, {}).get("tests_not_in_both")):
            i = first_divergence(dec_a, dec_r)
            verdict["divergences"][arm] = {"first_index": i, "owning_test": owning_test(out / arm, i), "this": dec_a[i] if i is not None and i < len(dec_a) else None,
                                            "reference": dec_r[i] if i is not None and i < len(dec_r) else None,
                                            "lengths": [len(dec_a), len(dec_r)]}
    # the cross-checks
    checks = {}
    for arm in ("healthy", "failing"):
        if arm not in arms:
            continue
        obs = [s for s, _e, _l in decode(out / arm, summaries[arm])]
        census = [json.loads(l, object_pairs_hook=_strict_pairs) for l in (out / arm / "census_trace.jsonl").read_text().splitlines()]
        observable = set(summaries[arm].get("wrapped") or id_to_symbol.values())   # the census also sees the
        needle = [id_to_symbol[rec[1]] for rec in census                              # seven nested symbols the
                  if rec[1] in id_to_symbol and id_to_symbol[rec[1]] in observable]    # observer cannot wrap
        unknown = sorted({rec[1] for rec in census if rec[1] not in id_to_symbol})
        matched = subsequence_match(needle, obs)
        checks[arm] = {"census_records": len(census), "census_ids_not_in_declaration": unknown,
                       "subsequence_matched": matched, "subsequence_holds": matched == len(needle)}
        c = summaries[arm]["census_counters"]
        if arm == "failing":
            checks[arm]["all_unmeasured"] = all(v["errors"] > 0 and v["consulted"] == 0 and v["fired"] == 0 for v in c.values() if v["errors"] or v["consulted"] or v["fired"]) and any(v["errors"] > 0 for v in c.values())
            checks[arm]["ids_with_errors"] = sum(1 for v in c.values() if v["errors"] > 0)
        else:
            checks[arm]["ids_consulted"] = sum(1 for v in c.values() if v["consulted"] > 0)
            checks[arm]["ids_fired"] = sum(1 for v in c.values() if v["fired"] > 0)
            checks[arm]["any_errors"] = any(v["errors"] for v in c.values())
    if "off" in arms:
        checks["off"] = {"census_enabled": summaries["off"]["census_enabled"], "registry_size": summaries["off"]["census_registry_size"]}
    if "uninstrumented" in arms:
        u_s = summaries["uninstrumented"]; off_ids = summaries["off"].get("census_registry_ids") if "off" in arms else None
        # ROUND 15: the twin's census is the source's own, so its registry holds the declarations exactly as the off arm's
        # does — compared as SETS, both ways (research's stage-1 condition 4) — and the reference arm's entries into census
        # code during the run are counted by the observer (None: the hook could not be shown alive).
        checks["uninstrumented"] = {"census_enabled": u_s["census_enabled"],
                                    "registry_size": u_s["census_registry_size"],
                                    "registry_equals_off": (None if off_ids is None or u_s.get("census_registry_ids") is None
                                                            else set(u_s["census_registry_ids"]) == set(off_ids)),
                                    "census_code_entries": u_s.get("census_code_entries"),
                                    "census_code_entry_detail": u_s.get("census_code_entry_detail"),
                                    "veracium_file": u_s["veracium_file"]}

    return verdict, checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("trace", "reach"))
    ap.add_argument("--repo", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--twin", default="derive", help="'derive' (HEAD minus the instrumentation, the default) or a commit to export"); ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--suites-from", help="a named_suites.json written by reach mode")
    ap.add_argument("--no-control", dest="control", action="store_false", help="skip the reference arm's control re-run")
    ap.add_argument("--ignore", action="append", default=[], help="passed to pytest as --ignore=<path> (reach mode: the census-toggling test files)")
    ap.add_argument("suites", nargs="*")
    a = ap.parse_intermixed_args()          # options and the suite list may interleave
    repo = pathlib.Path(a.repo).resolve(); out = pathlib.Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    decl_path = repo / "specs" / "evidence" / "0042" / "declaration.py"
    head = sh(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
    dirty = sh(["git", "status", "--short", "--", "src/"], cwd=repo).stdout.strip()
    suites = [s[2:] if s.startswith("./") else s for s in a.suites] + [f"--ignore={x}" for x in a.ignore]
    if a.suites_from:
        suites = json.loads(pathlib.Path(a.suites_from).read_text(), object_pairs_hook=_strict_pairs) + suites
    assert suites, "no suites: pass files or --suites-from"

    if a.mode == "reach":
        s = run_arm(repo, "healthy", suites, out, decl_path, mode="reach")
        decl = load_declaration(decl_path); declared = sorted(decl.DECLARED_IDS)
        reach = s["reach"]; by_id = {}
        for f, ids in reach.items():
            for sid, n in ids.items():
                by_id.setdefault(sid, {})[f] = n
        lines = [f"INV-7 REACH — which test files consult which declared ids (census healthy; HEAD {head[:12]}; {s['pytest_result_line']})",
                 f"declared ids: {len(declared)}; reached by at least one file: {sum(1 for i in declared if i in by_id)}; unreached: {sum(1 for i in declared if i not in by_id)}", ""]
        for f in sorted(reach, key=lambda f: -len(reach[f])):
            lines.append(f"{len(reach[f]):4d} ids  {f}")
        lines += ["", "UNREACHED (no test file consults the site — the 0042 runtime leg is its only exerciser):"]
        lines += [f"  {i}" for i in declared if i not in by_id]
        chosen = named_suites(reach)
        lines += ["", f"NAMED SUITES for the four-arm run ({len(chosen)} files: the {len([f for f in SPEC_NAMED_SUITES if f in reach])} spec-named, then a greedy cover of every reached id):"]
        lines += [f"  {f}" for f in chosen]
        (out / "reach_table.txt").write_text("\n".join(lines) + "\n")
        (out / "named_suites.json").write_text(json.dumps(chosen, indent=1) + "\n")
        print("\n".join(lines[:3]))
        return 0

    arms = a.arms.split(",")
    twin = export_twin(repo, a.twin, out) if "uninstrumented" in arms else None
    summaries = {}
    ref_arm = "uninstrumented" if "uninstrumented" in arms else arms[0]
    # Round 7: the control pair is run for EVERY arm, not only the reference. The first round-7 run found the
    # healthy arm alone diverging at one 0029 acceptance-corpus test — a supersession batch landing at a different
    # scenario step — while two runs of the twin agreed: wall-clock noise that only the slowest arm's timing
    # sampled. A test is excluded by name when two runs of ANY arm disagree on it; noise the reference arm
    # cannot sample is still noise.
    for arm in arms:
        if a.control:
            summaries[arm + "-control"] = run_arm(repo, arm, suites, out, decl_path, twin_src=(twin["src"] if arm == "uninstrumented" else None), out_name=arm + "-control")
            print(f"{arm + '-control':22s} records={summaries[arm + '-control'].get('records')} sha256={summaries[arm + '-control'].get('sha256', '')[:16]}", flush=True)
        summaries[arm] = run_arm(repo, arm, suites, out, decl_path, twin_src=(twin["src"] if arm == "uninstrumented" else None))
        print(f"{arm:15s} records={summaries[arm].get('records')} sha256={summaries[arm].get('sha256','')[:16]} "
              f"pytest={summaries[arm]['pytest_result_line']}", flush=True)

    decl = load_declaration(decl_path)
    id_to_symbol = {row[0]: row[3] for row in decl.DECLARATION}
    verdict, checks = compare(out, arms, summaries, id_to_symbol)
    ref = verdict["reference_arm"]

    # the transcript — every figure from the summaries just written
    import datetime
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    L = [f"# generated {stamp} against veracium @ {head}",
         "# the pin: tests/test_0042_inv7.py asserts this commit is an ancestor of HEAD with src/ unchanged since",
         f"INV-7 FOUR-ARM DECISION-TRACE DIFF — specs/0042", f"HEAD {head}" + ("  (src DIRTY: " + dirty.replace(chr(10), '; ') + ")" if dirty else ""),
         f"twin (uninstrumented): {twin['commit'] if twin else '-'}"]
    if twin and twin.get("derivation"):
        d = twin["derivation"]
        # ROUND 15: declarations are PRESERVED and the census is the source's own, copied verbatim; what makes the arm
        # "uninstrumented" in INV-7's sense is MEASURED: no census code runs in it beyond its import, the declarations and
        # the observer's reads, and its registry is the off arm's (both gated below).
        L += [f"twin derivation: {d['sites']} declare_site preserved, bound to the source's own census.py copied verbatim, {d['fires']} fire() unwrapped, {d['consults']} consult blocks spliced, "
              f"{d['bypasses']} census-enabled bypass blocks removed, across {d['modules_changed']} modules; no census code ran in the reference arm beyond its import, the declarations and the observer's reads, and its registry equals the off arm's (asserted below)"]
    elif twin:
        L += ["src commits between the twin and HEAD (the uninstrumented arm runs the twin's src; its census registry is empty — asserted below):"]
        L += [f"  {c}" for c in twin["src_commits_since_twin"]]
    L += ["", f"python {summaries[arms[0]]['python']}; pytest -q -p no:randomly -p no:cacheprovider -p inv7_observer; PYTHONHASHSEED=0", "suites: " + " ".join(suites)]
    # ROUND 15 (research's stage-1 scope note): the census-entry count is IN-PROCESS. The suites that spawn a subprocess
    # are DERIVED here by a static scan of each suite's text for `subprocess.` or `sys.executable`, never listed by hand.
    spawning = [s for s in suites if not s.startswith("--") and (repo / s).is_file() and any(tok in (repo / s).read_text() for tok in ("subprocess.", "sys.executable"))]
    L += [f"in-process: the reference arm's census-entry count covers the pytest process; {len(spawning)} of {len([s for s in suites if not s.startswith('--')])} suites spawn a subprocess "
          f"(static scan for `subprocess.` / `sys.executable`), outside the hook as their decisions are outside the observer: " + (" ".join(spawning) or "none")]
    # and the hook's liveness is checked at the END of the run (research's pre-commit note): a profiler or tracer set and
    # restored mid-run is a window it cannot see, so the suites that set one are DERIVED by a static scan and printed
    prof_re = re.compile(r"\b(setprofile|settrace|cProfile)\b|^\s*import profile\b|\bprofile\.run", re.M)
    profiling = [x for x in suites if not x.startswith("--") and (repo / x).is_file() and prof_re.search((repo / x).read_text())]
    L += [f"profilers and tracers: {len(profiling)} of {len([x for x in suites if not x.startswith('--')])} suites set one (static scan for `setprofile`, `settrace`, `cProfile`, "
          f"`import profile`, `profile.run`); the census-entry hook is checked alive at the END of the run: " + (" ".join(profiling) or "none"), ""]
    L += ["ARM              RECORDS     SHA256(observer trace)                                            PYTEST"]
    for arm in arms:
        s = summaries[arm]
        L.append(f"{arm:15s}  {s['records']:>9d}  {s['sha256']}  {s['pytest_result_line']} (exit {s['pytest_exit']}, {s['wall_s']}s)")
    ctl = verdict.get("control") or {}
    nd = ctl.get("non_reproducible", []); st_ex = ctl.get("standing_excluded", []); newly = ctl.get("newly_non_reproducible", [])
    compared = (ctl.get("tests", 0) - len(nd)) if ctl else len(segments(out / ref))
    ctl_arms = sorted((ctl.get("arms") or {}).keys())
    L += ["", f"VERDICT: observer traces {'IDENTICAL' if verdict['identical'] else 'DIVERGENT'} across {len(arms)} arms over {compared} tests (reference: {ref}; "
          f"excluded by the STANDING list: {len(st_ex)}; NEWLY non-reproducible this run: {len(newly)}{' — A FINDING' if newly else ''}; "
          f"control pairs run for {', '.join(ctl_arms) if ctl_arms else 'no arm'})"]
    L += [f"CANONICAL DIGESTS (decoded records, dictionary-independent — R6-5(i)): " + "; ".join(f"{a} {verdict['canonical_digest'][a][:16]}" for a in arms)]
    for arm, pt in verdict["per_test"].items():
        L.append(f"  {arm}: {pt['compared']} tests compared, {len(pt['differing'])} differing, {len(pt['tests_not_in_both'])} not in both")
        for t in pt["differing"][:20]:
            L.append(f"    DIFFERS {t}")
    L += ["", "EXCLUDED BY THE STANDING LIST (inv7_exclusions.STANDING: by name, with the cause; the arm(s) whose control pair sampled it THIS run in brackets, if any):"]
    L += [f"  {t}  [{', '.join(a for a, v in (ctl.get('arms') or {}).items() if t in v['non_reproducible']) or 'not sampled this run'}]\n      cause: {ctl.get('standing_causes', {}).get(t, '')}" for t in st_ex] or ["  (none)"]
    L += ["NEWLY NON-REPRODUCIBLE THIS RUN (a control pair disagreed on a test NOT on the standing list — a finding; the exit refuses it):"]
    L += [f"  {t}  [{', '.join(a for a, v in (ctl.get('arms') or {}).items() if t in v['non_reproducible'])}]" for t in newly] or ["  (none)"]
    for k in [k for k in summaries if k.endswith("-control")]:
        s_ = summaries[k]; L.append(f"control run {k}: records {s_['records']}, sha256 {s_['sha256']}, {s_['pytest_result_line']}")
    for arm, d in verdict["divergences"].items():
        L.append(f"  {arm}: first divergence at record {d['first_index']} (in {d.get('owning_test')}): this={d['this']} reference={d['reference']} lengths={d['lengths']}")
    L += ["", "CROSS-CHECKS:"]
    for k, v in checks.items():
        L.append(f"  {k}: {json.dumps(v, sort_keys=True)}")
    s0 = summaries[arms[0]]
    L += ["", f"OBSERVED SYMBOLS: {len(s0['wrapped'])} wrapped of {len(s0['wrapped']) + len(s0['excluded'])} declared; EXCLUDED (unreachable from outside, by name):"]
    L += [f"  {sym}: {why}" for sym, why in s0["excluded"]]
    L += [f"from-import bindings rebound: {len(s0['rebound'])}", "", "HISTOGRAM (reference arm), symbol -> decision: count"]
    L += [f"  {k}: {n}" for k, n in sorted(summaries[ref]["histogram"].items())]
    # ROUND 7, F3c: final_status is what ADDS `verdict["gates"]`, and the verdict used to be serialised BEFORE it
    # ran — so every shipped verdict.json lacked the gates both READMEs promised it carried. Compute first, write
    # second, and assert the serialised object carries them rather than trusting the order to stay this way.
    status = final_status(verdict, checks, summaries, arms)
    assert "gates" in verdict, "final_status did not record its gates on the verdict"
    # ROUND 15 (research's N-1): the gates and the exit are PRINTED, so a gate figure stated anywhere is readable from the
    # committed transcript rather than inherited from a verdict.json that is not in the tree.
    L += ["", f"GATES ({len(verdict['gates'])}, {sum(1 for v in verdict['gates'].values() if v is True)} true; the harness exit is 0 only if every one is true): "
          + json.dumps(verdict["gates"], sort_keys=True), f"HARNESS EXIT: {status}"]
    (out / "inv7_transcript.txt").write_text("\n".join(L) + "\n")
    (out / "verdict.json").write_text(json.dumps({"verdict": verdict, "checks": checks}, indent=1, sort_keys=True) + "\n")
    written = json.loads((out / "verdict.json").read_text(), object_pairs_hook=_strict_pairs)
    assert set(written["verdict"].get("gates") or {}) == set(verdict["gates"]), "the serialised verdict lost its gates"
    print("\n".join(L[:len(arms) + 12]))
    return status


def final_status(verdict: dict, checks: dict, summaries: dict, arms: list) -> int:
    """0 ONLY when the traces are identical AND every arm's pytest exited 0 AND every cross-check holds (round 6,
    R6-5(iii): the exit used to be the trace verdict alone, so an arm that never ran cleanly could not be told from
    one that ran and agreed). Pure over its inputs; the matrix test drives each gate."""
    gates = {"identical": bool(verdict.get("identical")),
             "no_new_non_reproducible": (verdict.get("control") or {}).get("newly_non_reproducible", []) == []}
    # ROUND 7, F3a: EVERY run whose result the verdict rests on, including the CONTROL runs that establish
    # reproducibility. The gate used to iterate `arms` alone, so a control run that FAILED still gave exit 0 —
    # and a failed control is exactly the run whose "these tests agree with themselves" claim is void.
    for a in arms:
        gates[f"pytest_exit:{a}"] = summaries.get(a, {}).get("pytest_exit") == 0
    # ROUND 9, F2. Every control run that HAS a summary is gated on its exit: having a summary means the run
    # happened, and its result counts whether or not the comparison used its directory.
    #
    # THIS WAS A UNION with the controls `compare` actually used, and MY OWN MUTANT CAMPAIGN KILLED IT — the
    # mutant that replaced the union with this line SURVIVED, which is the dead-check taxonomy's UNFAILABLE
    # entry. It survived because the union is provably equal to one of its operands: `compare` adds a control
    # to `per_arm_ctl` ONLY on the branch where its key is in `summaries`, so the used set is a subset of the
    # summary keys by construction and the union could never differ. A second operand that cannot change the
    # answer reads as defence in depth and is really a branch no test can redden, so it is gone rather than
    # commented.
    #
    # What makes the DIRECTORY-without-summary case fail is the gate below, and that one is load-bearing:
    # deleting it is a mutant the round-9 regression KILLS.
    ctl = verdict.get("control") or {}
    for a in sorted(k for k in summaries if k.endswith("-control")):
        gates[f"pytest_exit:{a}"] = summaries.get(a, {}).get("pytest_exit") == 0
    gates["controls_used_have_their_own_summary"] = (ctl.get("without_summary") or []) == []
    c = checks.get("healthy") or {}
    if "healthy" in arms:
        gates["healthy:subsequence"] = bool(c.get("subsequence_holds")); gates["healthy:no_errors"] = c.get("any_errors") is False
        gates["healthy:no_undeclared_ids"] = c.get("census_ids_not_in_declaration") == []
    f = checks.get("failing") or {}
    if "failing" in arms:
        gates["failing:all_unmeasured"] = bool(f.get("all_unmeasured")); gates["failing:subsequence"] = bool(f.get("subsequence_holds"))
    if "off" in arms:
        gates["off:census_disabled"] = checks.get("off", {}).get("census_enabled") is False
    if "uninstrumented" in arms:
        u = checks.get("uninstrumented", {}); gates["uninstrumented:census_disabled"] = u.get("census_enabled") is False
        # ROUND 15: the registry is the off arm's, as a set (only decidable when both arms ran), and NO census code ran
        # in the reference arm beyond its import, the product's declarations and the observer's reads. `== 0 and is not
        # None`: a missing count (the hook not alive, or a census with no observer) FAILS.
        if "off" in arms:
            gates["uninstrumented:registry_equals_off"] = u.get("registry_equals_off") is True
        gates["uninstrumented:no_census_code_in_decisions"] = u.get("census_code_entries") == 0 and u.get("census_code_entries") is not None
    verdict["gates"] = gates
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
