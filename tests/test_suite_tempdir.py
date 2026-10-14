"""The suite-wide temp redirect (tests/conftest.py `_suite_tempdir`): what a test mints with the bare tempfile API, in
this process or in a child it launches, lands under pytest's own basetemp, never in the system temp directory."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile


def test_a_bare_mkdtemp_and_mkstemp_land_under_pytests_basetemp(tmp_path_factory):
    base = tmp_path_factory.getbasetemp().resolve()
    d = pathlib.Path(tempfile.mkdtemp()).resolve()
    fd, f = tempfile.mkstemp(); os.close(fd)
    assert d.is_relative_to(base), (d, base)
    assert pathlib.Path(f).resolve().is_relative_to(base), (f, base)
    assert pathlib.Path(tempfile.gettempdir()).resolve().is_relative_to(base)


def test_a_launched_child_interpreter_inherits_the_redirect(tmp_path_factory):
    """The evidence scripts the suite runs as subprocesses resolve their temp directory from TMPDIR, not from this
    process's `tempfile.tempdir`, so the redirect must reach the environment as well."""
    base = tmp_path_factory.getbasetemp().resolve()
    out = subprocess.run([sys.executable, "-c", "import tempfile; print(tempfile.mkdtemp())"],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert pathlib.Path(out).resolve().is_relative_to(base), (out, base)
