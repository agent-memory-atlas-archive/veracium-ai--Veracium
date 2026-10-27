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
    "status": st.status, "reason": st.reason, "key_readable": st.key is not None, "unreadable": list(st.unreadable),
    "doctor_runtime": [(f.level, f.message[:140]) for f in rep.findings if f.check == "runtime"],
    "opens": opened,
    "unattested_warnings": sum(issubclass(w.category, sv.UnattestedBuildWarning) for w in caught),
}, indent=1))
