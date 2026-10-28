#!/usr/bin/env python3
"""0007 I6 (§4g.8 Gate, v0.6): a REAL route, on the interpreter that runs this script. Nothing is forced or patched: the
status is measured, doctor reports it, and two stores are opened and closed, counting the warnings.

    <python> specs/evidence/0007/routes/route_probe.py      # prints a transcript; exit 0
"""
import json
import pathlib
import platform
import sqlite3
import sys
import tempfile
import warnings

from veracium import doctor
from veracium.store import schema_version as sv
from veracium.store.sqlite import SqliteStore


def _loaded_library():
    """The SQLite library this process actually mapped, and that library's OWN source id read through ctypes, so a
    route run under LD_LIBRARY_PATH proves it measured the build it names (research's control, 2026-10-27). A build that
    links SQLite statically maps no libsqlite3: then None, and the SQL value stands alone."""
    import ctypes
    try:
        paths = {l.split()[-1] for l in open("/proc/self/maps") if "libsqlite3" in l.split()[-1]}
    except OSError:
        return None, None
    if len(paths) != 1:
        return (sorted(paths) or None), None
    p = paths.pop()
    lib = ctypes.CDLL(p)
    lib.sqlite3_sourceid.restype = ctypes.c_char_p
    return p, lib.sqlite3_sourceid().decode()


_conn = sqlite3.connect(":memory:")
SOURCE_ID = _conn.execute("SELECT sqlite_source_id()").fetchone()[0]
_conn.close()
LIBRARY, LIBRARY_SOURCE_ID = _loaded_library()
assert LIBRARY_SOURCE_ID in (None, SOURCE_ID), (LIBRARY, LIBRARY_SOURCE_ID, SOURCE_ID)   # the measured build IS the mapped one
st = sv.runtime_status()
rep = doctor.Report(db="(none)", readable=False)
doctor._check_runtime(rep)
with warnings.catch_warnings(record=True) as caught, tempfile.TemporaryDirectory() as d:
    warnings.simplefilter("always")
    opened = []
    for name in ("a.db", "b.db"):
        try:
            s = SqliteStore(str(pathlib.Path(d) / name))
            opened.append("opened")
            s.close()
        except sv.StoreVersionError as exc:
            opened.append(f"refused: {exc.reason}")
print(json.dumps({
    "python": platform.python_version(), "base_install": pathlib.Path(sys.base_prefix).name, "sqlite": sqlite3.sqlite_version,
    "source_id": SOURCE_ID, "library": LIBRARY,
    # stated either way (research): an absent control line reads like a control that passed
    "library_control": ("PASS: the mapped library's own sqlite3_sourceid() equals sqlite_source_id()" if LIBRARY_SOURCE_ID
                        else "N/A: statically linked (no libsqlite3 in /proc/self/maps)" if LIBRARY is None
                        else f"N/A: {LIBRARY!r} is not exactly one mapped libsqlite3"),
    "status": st.status, "reason": st.reason, "key_readable": st.key is not None, "unreadable": list(st.unreadable),
    "doctor_runtime": [(f.level, f.message[:140]) for f in rep.findings if f.check == "runtime"],
    "opens": opened,
    "unattested_warnings": sum(issubclass(w.category, sv.UnattestedBuildWarning) for w in caught),
}, indent=1))
