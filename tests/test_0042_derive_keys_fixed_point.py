"""specs/evidence/0042/derive_keys.py regenerates the committed review from itself unchanged (R-II round 3, NEXT-ROUND).

derive_keys rebuilt OVERRIDE from the plan-time literal alone, so an entry added after plan time lived only in the
committed review and every regeneration dropped it: four at RII-R2-01, each re-added by hand. A regeneration of the
committed review, over the committed inventory and with the committed reviewed_points.json, must now reproduce its
OVERRIDE and E exactly; without the reviewed points it must refuse rather than drop.
"""
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
E = ROOT / "specs" / "evidence" / "0042"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _derive(out, *extra):
    return subprocess.run([sys.executable, "-B", str(E / "derive_keys.py"), str(ROOT / "src" / "veracium"),
                           str(E / "decision_site_inventory_OUTPUT.json"), str(E / "semantic_review.py"), str(out),
                           *extra], capture_output=True, text=True, cwd=ROOT)


def test_a_regeneration_of_the_committed_review_reproduces_it(tmp_path):
    out = tmp_path / "review.py"
    r = _derive(out, str(E / "reviewed_points.json"))
    assert r.returncode == 0, r.stdout + r.stderr
    committed, regenerated = _load(E / "semantic_review.py", "committed"), _load(out, "regenerated")
    lost = {k: v for k, v in committed.OVERRIDE.items() if regenerated.OVERRIDE.get(k) != v}
    gained = {k: v for k, v in regenerated.OVERRIDE.items() if committed.OVERRIDE.get(k) != v}
    assert not lost and not gained, f"OVERRIDE lost {lost}, gained {gained}"
    assert committed.E == regenerated.E


def test_without_the_reviewed_points_an_input_with_later_entries_refuses(tmp_path):
    plan_time = _load(E / "override_at_plan.py", "plan_time").OVERRIDE
    assert len(_load(E / "semantic_review.py", "committed2").OVERRIDE) > len(plan_time), \
        "the committed review carries no entry added after plan time; this cell no longer exercises the refusal"
    r = _derive(tmp_path / "review.py")
    assert r.returncode != 0 and "pass the previous reviewed_points.json to carry them" in r.stderr, r.stdout + r.stderr
    assert not (tmp_path / "review.py").exists()
