"""A FIXTURE instrumentation package (not product code — a draft spec authorises none): three
modules whose decisions are expressed THROUGH a declared site (0042 Part A-0-quater), so the
counter update and the decision are one call and cannot be separated; one module is never
imported, so the derivations have an out-of-reach site to name.

Round 4 (the reviewer): `declare_site` recorded an id and returned it; the decision functions
carried NO counter updates; both decisions executed and every counter stayed at zero. A
registration is a PROXY for a counter bound to the decision. Now the site IS the counter:

    SITE = declare_site("gate.answer.unverified-only")
    with SITE.consult():                       # consulted += 1, at the decision
        if not assertable:
            raise SITE.fire(ValueError(...))   # fired += 1, ON the returned decision
"""
from __future__ import annotations

import contextlib

_REGISTRY: dict[str, "Site"] = {}


class Site:
    """The counter bound to one decision site. `consult()` brackets the decision; `fire(x)` counts
    the decision as taken and returns x unchanged, so it wraps the raise/return itself."""
    __slots__ = ("site_id", "module", "line", "consulted", "fired", "errors")

    def __init__(self, site_id: str, module: str, line: int):
        self.site_id, self.module, self.line = site_id, module, line
        self.consulted = self.fired = self.errors = 0

    @contextlib.contextmanager
    def consult(self):
        self.consulted += 1
        yield self

    def fire(self, decision):
        self.fired += 1
        return decision

    def counters(self) -> dict:
        return {"consulted": self.consulted, "fired": self.fired, "errors": self.errors}


def declare_site(site_id: str) -> Site:
    """The import-time record: registering is what happens when the module holding the call LOADS.
    Returns the Site the decision must be expressed through — a bare registration counts nothing."""
    import inspect
    fr = inspect.stack()[1]
    s = Site(site_id, fr.filename.rsplit("/", 1)[-1], fr.lineno)
    _REGISTRY[site_id] = s
    return s


def registry() -> dict[str, dict]:
    return {k: {"module": s.module, "line": s.line} for k, s in _REGISTRY.items()}


def counters() -> dict[str, dict]:
    """What the census reads: per registered id, the live counters."""
    return {k: s.counters() for k, s in _REGISTRY.items()}


def reset_counters() -> None:
    for s in _REGISTRY.values():
        s.consulted = s.fired = s.errors = 0
