"""specs/evidence/offline/testcase_manifest.py — the per-run testcase manifest (the 0041 round-10 reviewer's ask): one
line per testcase with its outcome and skip reason, and a REFUSAL when the cases do not reconcile with the testsuite's
own totals (a manifest that silently dropped a case would make two runs look reconciled when they are not)."""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tcm", ROOT / "specs" / "evidence" / "offline" / "testcase_manifest.py")
tcm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tcm)

CASES = """<testcase classname="tests.a" name="test_pass"/>
<testcase classname="tests.a" name="test_fail"><failure message="x"/></testcase>
<testcase classname="tests.a" name="test_err"><error message="y"/></testcase>
<testcase classname="tests.b" name="test_skip"><skipped type="pytest.skip" message="needs   git"/></testcase>
<testcase classname="tests.b" name="test_xf"><skipped type="pytest.xfail" message="known"/></testcase>"""


def _junit(tmp_path, tests=5, failures=1, errors=1, skipped=2):
    p = tmp_path / "j.xml"
    p.write_text(f'<testsuites><testsuite name="pytest" tests="{tests}" failures="{failures}" errors="{errors}" '
                 f'skipped="{skipped}">{CASES}</testsuite></testsuites>')
    return p


def test_every_outcome_and_reason_is_listed_and_sorted(tmp_path):
    rows, counts = tcm.manifest(str(_junit(tmp_path)))
    assert rows == sorted(rows) and len(rows) == 5
    assert "tests.b::test_skip\tskipped\tneeds git" in rows            # whitespace in a reason normalised
    assert "tests.b::test_xf\txfailed\tknown" in rows
    assert dict(counts) == {"passed": 1, "failed": 1, "error": 1, "skipped": 1, "xfailed": 1}


@pytest.mark.parametrize("field", ["tests", "failures", "errors", "skipped"])
def test_it_refuses_when_the_cases_do_not_reconcile_with_the_suite_totals(tmp_path, field):
    kw = {"tests": 5, "failures": 1, "errors": 1, "skipped": 2}
    kw[field] += 1
    with pytest.raises(SystemExit, match="REFUSED"):
        tcm.manifest(str(_junit(tmp_path, **kw)))
