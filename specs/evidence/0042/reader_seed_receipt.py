"""The reader/seed receipt (the round-33 verdict's suggestion, taken on the owner's word): what the INV-7 measurement's
newly trusted channel rests on, reported by the interpreter it rests on — so it can be audited on another interpreter
without re-reading the describer's source.

The round-33 verdict accepted two things for the exercised build only: the set reader, which reads CPython's PySetObject
table at fixed offsets once an import-time check proves each field (inv7_uninstrument._set_reader_check), and the hash
seed, pinned to 0 in route B's children and in every arm because a set of strings sits in its table by a seed-dependent
hash. This script reports, for the interpreter that runs it:

  - WHAT IT IS: the binary (its resolved path and sha256), sys.version, the commit of the tree it runs from (or null, and
    why, in a copy without git);
  - the build: implementation, pointer width, free threading, debug refcounts;
  - the effective seed: sys.flags.hash_randomization (0 only under PYTHONHASHSEED=0), the variable as the process saw
    it, and one string's hash, which under seed 0 is a constant of the build;
  - the set reader's check: proven or not, with the first field that disagreed if not — the describer's own
    import-time result AND a fresh run of the same check, which must agree;
  - ROUTE B: the same seed and reader facts from a child started by route B's own launch (the describer's
    `_ROUTE_B_FLAGS` and `_isolated_env()`), with the child's safe_path, no_user_site and dont_write_bytecode flags
    and its PYTHON* variables.

WHAT PROCESS THIS IS, stated plainly (the second seat's mark): the receipt is written by a SEPARATE PROCESS launched with
an arm's executable and an arm's seed environment — a proxy for the arm, not the arm's own state. It shows what that
binary and those settings give; it does not read the state of a run that has finished. The route-B section is route B's
real launch path, run once more.

    PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 python specs/evidence/0042/reader_seed_receipt.py [out.json]

It prints the receipt as JSON (keys sorted, no addresses) and writes it to out.json if named. Exit 0 only when the seed
is pinned to 0 and the reader is proven at import and fresh, agreeing, in BOTH this process and route B's child — the
condition the INV-7 result was accepted under — else 1; the receipt is written either way, so an unpinned or unproven run
is recorded, never silent.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import subprocess
import sys
import sysconfig

HERE = pathlib.Path(__file__).resolve().parent

# route B's child for this receipt: ASCII only, as route B's own child source is (a C-locale spawn decodes it as ASCII)
_ROUTE_B_PROBE = r"""
import importlib.util, json, os, sys
s = importlib.util.spec_from_file_location("un_receipt_child", sys.argv[1]); un = importlib.util.module_from_spec(s)
sys.modules[s.name] = un; s.loader.exec_module(un)
d, why = un._set_reader_check()
print(json.dumps({"safe_path": bool(sys.flags.safe_path), "no_user_site": bool(sys.flags.no_user_site),
                  "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
                  "hash_randomization": sys.flags.hash_randomization, "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
                  "python_env": sorted(k for k in os.environ if k.startswith("PYTHON")),
                  "proven_at_import": un._SET_DUMMY is not None, "reason_at_import": un._SET_READER_BROKEN,
                  "proven_fresh": d is not None, "reason_fresh": why}, sort_keys=True))
"""


def _describer():
    spec = importlib.util.spec_from_file_location("inv7_uninstrument_receipt", HERE / "inv7_uninstrument.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _commit():
    try:
        r = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
    except OSError as e:
        return None, f"git could not run: {type(e).__name__}"
    if r.returncode != 0 or len(r.stdout.strip()) != 40:
        return None, "not a git checkout (a git archive or a copy): the tree's commit is the package's PIN.txt"
    return r.stdout.strip(), None


def _reader(un) -> dict:
    fresh_dummy, fresh_reason = un._set_reader_check()
    at_import = un._SET_DUMMY is not None
    return {"proven_at_import": at_import, "reason_at_import": un._SET_READER_BROKEN,
            "proven_fresh": fresh_dummy is not None, "reason_fresh": fresh_reason,
            "agree": at_import == (fresh_dummy is not None)}


def _route_b(un) -> dict:
    """Route B's launch, as _described_in_isolation makes it: the same executable, the describer's own `_ROUTE_B_FLAGS`
    and `_isolated_env()` — read from the describer, never restated here, so a change to route B's launch is a change
    to what this audits."""
    r = subprocess.run([sys.executable, *un._ROUTE_B_FLAGS, "-c", _ROUTE_B_PROBE, str(HERE / "inv7_uninstrument.py")],
                       env=un._isolated_env(), capture_output=True, timeout=300)
    if r.returncode != 0:
        return {"ran": False, "exit": r.returncode, "stderr_tail": r.stderr.decode("ascii", "replace")[-400:]}
    _strict_pairs = un._strict_pairs   # the describer's own duplicate-refusing hook (0026's evidence-boundary rule)
    child = json.loads(r.stdout.decode("ascii"), object_pairs_hook=_strict_pairs)
    child["ran"] = True
    child["agree"] = child["proven_at_import"] == child["proven_fresh"]
    return child


def receipt(un=None, route_b: bool = True) -> dict:
    import ctypes
    un = un if un is not None else _describer()
    exe = pathlib.Path(sys.executable).resolve()
    commit, commit_why = _commit()
    seed = sys.flags.hash_randomization
    out = {
        "process": ("a separate process launched with an arm's executable and seed environment: a proxy for the arm, "
                    "not the arm's own state"),
        "identity": {"executable": str(exe), "executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
                     "sys_version": sys.version, "commit": commit, "commit_unavailable": commit_why},
        "build": {"version": platform.python_version(), "implementation": platform.python_implementation(),
                  "pointer_bytes": ctypes.sizeof(ctypes.c_void_p),
                  "free_threaded": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
                  "debug_refcounts": hasattr(sys, "gettotalrefcount")},
        "seed": {"hash_randomization": seed, "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
                 "hash_of_probe_string": hash("veracium-0042-receipt"), "pinned_to_zero": seed == 0},
        "set_reader": dict(_reader(un), offsets={
            "fill": un._SET_FILL, "used": un._SET_USED, "mask": un._SET_MASK, "table": un._SET_TABLE,
            "finger": un._SET_FINGER, "small_table": un._SET_SMALL, "entry_bytes": un._SET_ENTRY}),
    }
    if route_b:
        out["route_b_child"] = _route_b(un)
    return out


def accepted(r: dict) -> bool:
    """The condition the INV-7 result was accepted under, read from a receipt."""
    sr = r["set_reader"]
    ok = r["seed"]["pinned_to_zero"] and sr["proven_at_import"] and sr["proven_fresh"] and sr["agree"]
    b = r.get("route_b_child")
    if b is not None:
        ok = ok and b.get("ran", False) and b["safe_path"] and b["no_user_site"] and b["dont_write_bytecode"] \
            and b["hash_randomization"] == 0 and b["python_env"] == ["PYTHONHASHSEED"] \
            and b["proven_at_import"] and b["proven_fresh"] and b["agree"]
    return bool(ok)


def main(argv: list) -> int:
    r = receipt()
    text = json.dumps(r, sort_keys=True, indent=2) + "\n"
    sys.stdout.write(text)
    if len(argv) > 1:
        pathlib.Path(argv[1]).write_text(text, encoding="utf-8")
    return 0 if accepted(r) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
