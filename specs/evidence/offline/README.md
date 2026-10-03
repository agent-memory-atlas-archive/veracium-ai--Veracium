# Running the suite offline

This directory holds a self-contained, hash-locked test environment for the qualified runtime (CPython 3.14,
SQLite 3.45.1): eleven wheels, `requirements-test.lock`, the launcher `run_offline.sh`, and `verify_wheelset.py`,
which checks the wheels against the lock exactly. No network is used.

## The invocation

```
VERACIUM_PYTHON=<a CPython 3.14 interpreter> bash specs/evidence/offline/run_offline.sh \
    --basetemp=<a directory OUTSIDE the package tree, on the SAME filesystem as it> \
    --junitxml=<results.xml>
```

- **`VERACIUM_PYTHON`** chooses the interpreter. The launcher builds a fresh venv (it refuses to reuse one), installs
  the locked wheels with no network, then asks the repository's own predicate (`runtime_supported()`, specs/0007)
  whether that runtime is qualified, and **refuses** if it is not.
- **Any further arguments go to pytest unchanged**, after the launcher's own `-q tests -p no:randomly -rs`: the suite runs in definition order, every skip with its reason.
- **`--basetemp` on the package's filesystem.** One test,
  `tests/test_0026_relay_lexicon.py::test_bootstrap_paths_cannot_alias_and_worklists_stay_local`, hard-links a file of
  the tree into its `tmp_path`. A hard link cannot cross filesystems, so with a `tmp_path` elsewhere (a tmpfs `/tmp`,
  for instance) it fails, and it says so: `… on another filesystem (EXDEV): run pytest with --basetemp=…`. That is a
  property of the run's environment, not of the product; the 0041 round-10 reviewer met it, and passing `--basetemp`
  beside the package fixed it. Do not put the base directory INSIDE the package tree: the tree under review is not
  written to.
- **`--junitxml`** records the same run machine-readably.

## The testcase manifest

```
python specs/evidence/offline/testcase_manifest.py <results.xml> [<out.tsv>]
```

One line per testcase: its identity, its outcome, and for a skip its reason, sorted, with a count footer. It refuses
(exit 1) if the cases do not reconcile with the testsuite's own totals. Two runs reconcile by `diff` of their
manifests.

## What this profile does not install

The launcher installs exactly the locked wheels (the test requirements: pytest, pytest-randomly, pydantic and their dependencies) and runs with `PYTHONPATH=src`; it does not install `mcp`, so the MCP tests skip, by name. In a git-archive export
(no `.git`), the tests that check pins against git history skip too, by name. Every skip prints its cause under `-rs`.

There is no offline MCP profile; the round-10 verdict called one optional. The MCP tests run in the full profile, `pip install -e ".[dev,mcp]"` from a fresh clone, which is how every review package's capture is made (network required).

## Running the suite in pieces

The suite is meant to run as ONE pytest process. If you split it, keep the two groups named in
[JOINT-TEST-GROUPS.md](JOINT-TEST-GROUPS.md) whole.
