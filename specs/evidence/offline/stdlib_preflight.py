"""Import preflight for the offline launcher: does this interpreter have the compiled standard-library modules the
suite loads?

    python stdlib_preflight.py <stdlib_extensions.txt>

run_offline.sh runs it with the requested interpreter before it builds anything. The 0048 round-1 reviewer's own
CPython build lacked `_ctypes`; the suite only found out partway through a long run (one evidence script imports
`ctypes`, in a subprocess). The list beside this script is MEASURED, not written by hand: every module that the
launcher's own run, traced across every process it started, loaded from the qualified interpreter's `lib-dynload`
(the header of the list says how and where). A module that is missing exits 2, and every missing one is named with
its import error. A build can lack a module that only an accelerated path uses (a pure-Python fallback exists), so
the refusal names its own override: VERACIUM_PREFLIGHT=warn reports the same list and lets the suite run, and then the
suite's own result says what the absence cost.

This script imports nothing optional itself: it has to run on exactly the interpreter it is judging.
"""
# Mutation-Matrix: tests/test_offline_preflight.py::test_stdlib_preflight_refuses_a_missing_extension
import importlib
import os
import sys

names = [ln.strip() for ln in open(sys.argv[1], encoding="utf-8") if ln.strip() and not ln.startswith("#")]
if not names:
    print("preflight: the module list is empty; a list that names nothing checks nothing", file=sys.stderr)
    sys.exit(2)
missing = []
for name in names:
    try:
        importlib.import_module(name)
    except Exception as e:                 # ImportError, and a broken shared object's own error, both name the cause
        missing.append(f"{name}: {type(e).__name__}: {e}")
print(f"  {len(names) - len(missing)} of {len(names)} compiled standard-library modules import")
if missing:
    warn = os.environ.get("VERACIUM_PREFLIGHT") == "warn"
    print(("WARNING" if warn else "REFUSED") + ": this interpreter cannot import compiled standard-library modules that"
          " the qualified run loaded:", file=sys.stderr)
    for m in missing:
        print(f"  {m}", file=sys.stderr)
    if warn:
        print("  VERACIUM_PREFLIGHT=warn: continuing; the suite's result will show what each absence costs",
              file=sys.stderr)
        sys.exit(0)
    print("  Rebuild the interpreter with these modules (each needs its library's headers at build time, e.g.\n"
          "  libffi for _ctypes), or set VERACIUM_PREFLIGHT=warn to run anyway and let the suite say what failed.",
          file=sys.stderr)
    sys.exit(2)
