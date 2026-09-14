"""The amendments reviewer, round 9, F2 (2026-09-14; a pre-existing defect,
fixed beside 0037 v24.5): `remember`, `record_procedure` and the other paths
that default an omitted event date used the host's LOCAL calendar date, while
ingestion reads a bare date as UTC midnight (`_event_dt`). On a runtime whose
local date runs ahead of UTC — the reviewer's, at 22:01 UTC — a routine was
stored with tomorrow's `valid_from` and withheld as `not_yet_valid` until UTC
midnight. One clock now: the default is the UTC calendar date the reading uses.

The regression exercises the boundary rather than assuming it: it picks the
fixed-offset zones fourteen hours ahead of and twelve hours behind UTC, asserts
that the zone's LOCAL date differs from the UTC date at the moment of the run
(at every hour of the day at least one of the two does), records a routine
with no date under that zone, and checks the stored date is the UTC date and
the routine is describable at once. Under the old default the stored date was
the local one, which this fails on either side of the boundary.
"""

import importlib.util
import pathlib
import time

import pytest

from veracium import _today_utc
from veracium.schema import utcnow


def _module(name):
    path = pathlib.Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name[:-3] + "_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = _module("test_0037_procedural.py")
U = base.U


@pytest.mark.parametrize("zone", ["Etc/GMT-14", "Etc/GMT+12"])   # POSIX signs: GMT-14 is UTC+14
def test_an_omitted_date_is_the_utc_date_on_both_sides_of_the_local_boundary(tmp_path, monkeypatch, zone):
    monkeypatch.setenv("TZ", zone)
    time.tzset()
    try:
        utc_date = utcnow().date().isoformat()
        local_date = time.strftime("%Y-%m-%d")
        if local_date == utc_date:
            pytest.skip(f"{zone}'s local date equals the UTC date at this hour; the other zone carries the boundary")
        assert _today_utc() == utc_date
        mem = base._mem(tmp_path, f"{zone.replace('/', '_')}.db")
        eid = base._record(mem, "I rotate the service credentials every quarter.")   # a stated routine, not an imperative (the frozen executable-detail rule withholds those)
        edge = next(e for e in mem.store.edges(U) if e.id == eid)
        assert edge.valid_from.date().isoformat() == utc_date, (local_date, utc_date)
        r = mem.describe_procedures(U)
        assert r.total_describable == 1 and r.descriptions[0].edge_id == eid, (r.withheld, local_date, utc_date)
        assert not [w for w in r.withheld if w.outcome == "not_yet_valid"], (r.withheld, local_date, utc_date)
        mem.close()
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()


def test_every_omitted_date_default_uses_the_utc_clock():
    """No path defaults a date from the local calendar: the only `today()` in the
    package is inside `_today_utc`, and it reads `utcnow()`."""
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "veracium"
    hits = [(p.name, i + 1) for p in src.rglob("*.py")
            for i, line in enumerate(p.read_text().splitlines()) if ".today()" in line]
    assert hits == [], hits
    assert "utcnow().date().isoformat()" in (src / "__init__.py").read_text()
