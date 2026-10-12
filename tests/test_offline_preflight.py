"""The offline launcher's import preflight (0048 round 1's package note: the reviewer's own CPython build lacked
`_ctypes`, and only a long suite run found out).

`stdlib_preflight.py` is a checker, so its refusals are driven here on an interpreter made to lack a module: a
`_ctypes.py` that raises, placed first on PYTHONPATH, shadows the compiled module exactly as a build without libffi
would leave it missing. The launcher is driven the same way, through a VERACIUM_PYTHON wrapper, and must refuse
BEFORE it builds a venv: a refusal after a ten-minute install is the cost the preflight exists to remove.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OFF = ROOT / "specs" / "evidence" / "offline"
LIST = OFF / "stdlib_extensions.txt"


def _names():
    return [ln.strip() for ln in LIST.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


def _preflight(tmp_path, listfile, shadow=(), **env):
    sh = tmp_path / "shadow"
    sh.mkdir(exist_ok=True)
    for name in shadow:
        (sh / f"{name}.py").write_text(f"raise ImportError('planted: {name} is not built')\n")
    e = {**{k: v for k, v in os.environ.items() if k != "VERACIUM_PREFLIGHT"}, "PYTHONPATH": str(sh), **env}
    return subprocess.run([sys.executable, str(OFF / "stdlib_preflight.py"), str(listfile)], env=e,
                          capture_output=True, text=True, timeout=120)


def _missing(tmp_path, names, shadow=()):
    """The listed modules THIS interpreter cannot import, under the same shadow, asked of a clean subprocess: the
    truth the preflight's verdict is compared with."""
    sh = tmp_path / "shadow"
    sh.mkdir(exist_ok=True)
    for name in shadow:
        (sh / f"{name}.py").write_text(f"raise ImportError('planted: {name} is not built')\n")
    probe = ("import importlib, sys\nfor n in sys.argv[1:]:\n    try:\n        importlib.import_module(n)\n"
             "    except Exception:\n        print(n)\n")
    e = {**{k: v for k, v in os.environ.items() if k != "VERACIUM_PREFLIGHT"}, "PYTHONPATH": str(sh)}
    r = subprocess.run([sys.executable, "-c", probe, *names], env=e, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return r.stdout.split()


# the five compiled modules 0048 round 2's reviewer's CPython 3.14.7 build lacked; its full run was green without them
REVIEWER_LACKED = ("_bz2", "_lzma", "_uuid", "_zstd", "readline")


def test_stdlib_preflight_refuses_a_missing_extension(tmp_path):
    """stdlib_preflight.py's mutation matrix. Its verdict on the measured list equals the interpreter's own truth: exit
    0 when every listed module imports, else exit 2 naming exactly the ones that do not. The honest control is that
    comparison, not "every module imports": round 2's reviewer ran an interpreter lacking five listed modules, and an
    honest control that assumed a complete build failed the suite even under VERACIUM_PREFLIGHT=warn, the mode that
    exists to let the run go on. It runs twice, as found and with the reviewer's five shadowed. With `_ctypes` made
    missing (round 1's build) it exits 2 and names `_ctypes`; VERACIUM_PREFLIGHT=warn reports the same and lets the run
    continue; a name no build carries is refused by name; an empty list is refused (a list that names nothing checks
    nothing)."""
    names = _names()
    assert "_ctypes" in names and "_sqlite3" in names, names
    assert set(REVIEWER_LACKED) <= set(names), set(REVIEWER_LACKED) - set(names)
    for shadow in ((), REVIEWER_LACKED):
        lacking = _missing(tmp_path, names, shadow)
        assert set(shadow) <= set(lacking), (shadow, lacking)
        honest = _preflight(tmp_path, LIST, shadow=shadow)
        named = re.findall(r"^  ([A-Za-z0-9_.]+): \w+: ", honest.stderr, re.M)
        assert named == lacking, (shadow, named, lacking)
        assert honest.returncode == (2 if lacking else 0), honest.stdout + honest.stderr
        assert f"{len(names) - len(lacking)} of {len(names)} compiled standard-library modules import" in (
            honest.stdout + honest.stderr), honest.stdout + honest.stderr
    base = _missing(tmp_path, names)
    gone = _preflight(tmp_path, LIST, shadow=["_ctypes"])
    assert gone.returncode == 2 and "REFUSED" in gone.stderr, gone.stderr
    missing = re.findall(r"^  ([A-Za-z0-9_.]+): \w+: ", gone.stderr, re.M)
    assert missing == [n for n in names if n == "_ctypes" or n in base], (missing, base)
    assert "planted: _ctypes is not built" in gone.stderr, gone.stderr
    warned = _preflight(tmp_path, LIST, shadow=["_ctypes"], VERACIUM_PREFLIGHT="warn")
    assert warned.returncode == 0 and "WARNING" in warned.stderr and "_ctypes" in warned.stderr, warned.stderr
    bogus = tmp_path / "bogus.txt"
    bogus.write_text("# a list with one module no build carries\n_no_such_extension\n")
    r = _preflight(tmp_path, bogus)
    assert r.returncode == 2 and "_no_such_extension: ModuleNotFoundError" in r.stderr, r.stderr
    empty = tmp_path / "empty.txt"
    empty.write_text("# nothing\n")
    r = _preflight(tmp_path, empty)
    assert r.returncode == 2 and "names nothing" in r.stderr, r.stderr


def test_the_launcher_refuses_a_missing_extension_before_building_anything(tmp_path):
    """run_offline.sh asks stdlib_preflight.py first: given an interpreter that cannot import `_ctypes`, it exits 2,
    names the module, and has created no venv."""
    sh = tmp_path / "shadow"
    sh.mkdir()
    (sh / "_ctypes.py").write_text("raise ImportError('planted: _ctypes is not built')\n")
    wrapper = tmp_path / "python-without-ctypes"
    wrapper.write_text(f"#!/bin/sh\nPYTHONPATH={sh} exec {sys.executable} \"$@\"\n")
    wrapper.chmod(0o755)
    venv = tmp_path / "venv"
    r = subprocess.run(["bash", str(OFF / "run_offline.sh")], cwd=ROOT, capture_output=True, text=True, timeout=120,
                       env={**{k: v for k, v in os.environ.items() if k != "VERACIUM_PREFLIGHT"},
                            "VERACIUM_PYTHON": str(wrapper), "VERACIUM_OFFLINE_VENV": str(venv)})
    assert r.returncode == 2, r.stdout + r.stderr
    assert "_ctypes: ImportError: planted" in r.stderr, r.stderr
    assert not venv.exists(), "the launcher built a venv before refusing"


def test_stdlib_extensions_from_trace_reads_every_process_and_one_interpreter(tmp_path):
    """stdlib_extensions_from_trace.py's mutation matrix: the list is its OUTPUT, committed, so what it keeps and drops
    is driven on a planted trace. An open by a child process counts like the parent's; a second open of one module
    counts once; another interpreter's lib-dynload is counted in the header and not listed; a compiled module outside
    any lib-dynload (a wheel's, in site-packages) is not a standard-library module and is ignored."""
    dyn = tmp_path / "py" / "lib" / "python3.14" / "lib-dynload"
    dyn.mkdir(parents=True)
    so = "cpython-314-x86_64-linux-gnu.so"
    trace = tmp_path / "trace.log"
    trace.write_text("\n".join([
        f'100 openat(AT_FDCWD, "{dyn}/_ctypes.{so}", O_RDONLY|O_CLOEXEC) = 3',
        f'101 openat(AT_FDCWD, "{dyn}/_sqlite3.{so}", O_RDONLY|O_CLOEXEC) = 4',
        f'101 openat(AT_FDCWD, "{dyn}/_sqlite3.{so}", O_RDONLY|O_CLOEXEC) = 5',
        '102 openat(AT_FDCWD, "/usr/lib/python3.12/lib-dynload/_ssl.cpython-312-x86_64-linux-gnu.so", O_RDONLY) = 3',
        f'100 openat(AT_FDCWD, "{tmp_path}/venv/site-packages/pydantic_core/_pydantic_core.{so}", O_RDONLY) = 6',
        f'100 openat(AT_FDCWD, "{dyn}/../os.py", O_RDONLY|O_CLOEXEC) = 7',
    ]) + "\n")
    r = subprocess.run([sys.executable, str(OFF / "stdlib_extensions_from_trace.py"), str(trace), str(dyn), "planted"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    body = [ln for ln in r.stdout.splitlines() if not ln.startswith("#")]
    assert body == ["_ctypes", "_sqlite3"], r.stdout
    assert "# 2 modules from lib-dynload of the traced interpreter; 1 shared objects from any other" in r.stdout
    assert "# measured: planted" in r.stdout
