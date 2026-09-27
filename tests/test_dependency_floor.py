"""specs/0016 D1, R6-4: the minimum-dependency CI job must run AT the declared floor, or its green says nothing.

This assertion was the job's anchor once and did not survive D2 (the job's comment still claimed "the floor regression
test asserts the installed version" while no test did). Restored at the Python 3.14 floor (2026-09-27), and it reads
the floor from pyproject.toml, so the declaration and the job cannot drift apart."""
import os
import pathlib
import re
import sys

import pytest


def _declared_pydantic_floor() -> str:
    text = (pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'"pydantic>=([0-9][0-9.]*)"', text)
    assert m, "pyproject.toml declares no pydantic floor"
    return m.group(1)


@pytest.mark.skipif(not os.environ.get("VERACIUM_MIN_DEP_JOB"),
                    reason="runs in CI's minimum-dependency job only (VERACIUM_MIN_DEP_JOB=1)")
def test_the_floor_job_runs_at_the_declared_pydantic_floor():
    import pydantic
    floor = _declared_pydantic_floor()
    want = floor if floor.count(".") == 2 else floor + ".0"
    assert pydantic.VERSION == want, (pydantic.VERSION, want)


def test_the_declared_python_floor_is_the_interpreter_floor():
    """requires-python and the interpreter this suite runs on agree: a floor above the running interpreter would mean
    the suite is testing a version the package refuses to install on."""
    text = (pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'requires-python = ">=(\d+)\.(\d+)"', text)
    assert m and sys.version_info[:2] >= (int(m.group(1)), int(m.group(2))), (m and m.groups(), sys.version_info[:2])
