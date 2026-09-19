"""The exercised-guarantees census — accepted spec 0042 (design level, external round 5).

An ENFORCEMENT POINT is any site that can return a decision other than the caller's request
(refuse, quarantine, withhold, abstain, downgrade). Each declares a site at module level and
expresses its decision THROUGH it (Part A-0-quater):

    SITE = declare_site("gate.answer.unverified-only")
    ...
    with SITE.consult():                       # consulted += 1, BEFORE the decision branches
        if not assertable:
            raise SITE.fire(ValueError(...))   # fired += 1, ON the returned decision

Observation only (INV-7): a site never alters a decision; `fire(x)` returns `x` unchanged. Counts carry
NO record content (INV-8): an id and integers. Activation is OPT-IN, DEFAULT OFF (Part A-2): with the
census off every site is a no-op and `census()` reports `DISABLED` per declared id — a measured zero
and an unmeasured one are different bytes. Counters are process-local and monotonic; increments are
atomic per id; a report is a per-id snapshot inside a recorded window (Part A-2, snapshot consistency).
A counter that raises reports `UNMEASURED` for its id and does not invalidate its neighbours.

The state table (Part A-1) is carried here VERBATIM in `STATE_TABLE`; the evidence in
`specs/evidence/0042/census_table.py` parses the spec's own table and asserts this one equals it.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Optional

# ---- Part A-1: the state table, the single authority, carried verbatim ---------------------------

STATE_TABLE = (
    ("DISABLED",    "enabled == false"),
    ("UNDECLARED",  "declared == false"),
    ("UNMEASURED",  "errors > 0"),
    ("UNREACHED",   "consulted == 0"),
    ("UNEXERCISED", "consulted > 0 and fired == 0"),
    ("EXERCISED",   "fired > 0"),
)
STATUSES = tuple(s for s, _ in STATE_TABLE)
_CONDITIONS = {
    "enabled == false":             lambda t: t["enabled"] is False,
    "declared == false":            lambda t: t["declared"] is False,
    "errors > 0":                   lambda t: t["errors"] > 0,
    "consulted == 0":               lambda t: t["consulted"] == 0,
    "consulted > 0 and fired == 0": lambda t: t["consulted"] > 0 and t["fired"] == 0,
    "fired > 0":                    lambda t: t["fired"] > 0,
}


def status_of(t: dict) -> str:
    """First matching row in precedence order; every tuple maps to exactly one status (Part A-1)."""
    for status, condition in STATE_TABLE:
        if _CONDITIONS[condition](t):
            return status
    raise ValueError(f"no status row matches {t} — the table has a gap")


# ---- the process-local registry and switch ------------------------------------------------------

_ENABLED = False
_TRACING = False
_REGISTRY: dict[str, "Site"] = {}
_REGISTRY_LOCK = threading.Lock()
_TRACE: list[tuple] = []
_TRACE_LOCK = threading.Lock()
_PROCESS_STARTED = time.time()


class CensusError(Exception):
    """A census-side refusal: a duplicate id, a malformed decision label."""


class Site:
    """One enforcement point's counters. `consult()` brackets the decision; `fire(x)` counts the
    decision as taken and returns `x` unchanged so it wraps the raise or return itself. WHERE a site
    lives is not recorded here: the static scan (specs/evidence/0042/installed_sites.py) derives
    (module, line) from the source, and the 0031 surface refuses the frame machinery in src."""
    __slots__ = ("site_id", "consulted", "fired", "errors", "_lock", "_declines")

    def __init__(self, site_id: str, declines=None):
        self.site_id = site_id
        self.consulted = self.fired = self.errors = 0
        self._lock = threading.Lock()
        # WHICH returned value is the decline (tranche 2, 2026-09-19): a site whose decision is
        # a predicate returns BOTH verdicts through fire() so the return statement keeps the
        # shape discovery finds; `fired` moves only on the declining one. None → the default
        # (an exception, None or False); a value → identity with it; a callable → its verdict.
        self._declines = declines

    def declined(self, decision) -> bool:
        d = self._declines
        if d is None:
            return decision is None or decision is False or isinstance(decision, BaseException)
        if callable(d):
            return bool(d(decision))
        return decision is d

    def _bump(self, field: str) -> None:
        """The one increment. Atomic per id; a raise here is the counter's OWN failure and lands in
        `errors` (UNMEASURED), never in the decision path. Literal attribute names only — the 0031
        attribute census refuses a non-literal getattr conservatively, and rightly."""
        with self._lock:
            if field == "consulted":
                self.consulted += 1
            elif field == "fired":
                self.fired += 1
            else:
                raise CensusError(f"unknown counter {field!r}")

    def consult(self):
        """The bracket: `with SITE.consult():`. The Site is its own context manager (no generator,
        no allocation) so a disabled census costs one global read per decision — the tranche-2
        sites include `Edge.assertable` and its siblings, consulted per edge per recall."""
        return self

    def __enter__(self):
        if _ENABLED:
            try:
                self._bump("consulted")
            except BaseException:            # the counter broke: UNMEASURED, and the decision proceeds
                try:
                    with self._lock:
                        self.errors += 1
                except BaseException:
                    pass
        return self

    def __exit__(self, exc_type, exc, tb):
        return False                          # never swallows the decision's raise

    def fire(self, decision, label: Optional[str] = None, *, declined: Optional[bool] = None):
        """Return the decision UNCHANGED, counting it as a decline when it IS one: by the site's
        declared declining value (`declined()`), or by the caller's explicit `declined=` when the
        decline is not visible in the value (a filter that reports what it withheld beside what
        it kept). `label` is the branch's fixed name for the trace (a refusal class or a fixed
        word, never content); default: the exception's class name, or "decision" for a value."""
        if not _ENABLED:
            return decision
        if declined is None:
            try:
                declined = self.declined(decision)
            except BaseException:
                declined = False
        if declined:
            try:
                self._bump("fired")
            except BaseException:
                try:
                    with self._lock:
                        self.errors += 1
                except BaseException:
                    pass
            if _TRACING:
                _record_trace(self.site_id, label if label is not None else _label_of(decision))
        return decision

    def counters(self) -> dict:
        with self._lock:
            return {"consulted": self.consulted, "fired": self.fired, "errors": self.errors}


def _label_of(decision) -> str:
    if isinstance(decision, BaseException):
        return type(decision).__name__
    if decision is None or isinstance(decision, bool):
        return repr(decision)
    return "decision"


def declare_site(site_id: str, declines=None) -> Site:
    """Register an enforcement point at import time. The id is code-supplied (never caller-supplied);
    a duplicate id REFUSES, so two sites cannot share a row (a re-imported module is the test
    harness's case and it clears the registry first). `declines` names the declining value for a
    predicate site (see `Site.declined`); omitted, an exception, None or False is the decline."""
    if type(site_id) is not str or not site_id or any(c.isspace() for c in site_id):
        raise CensusError(f"site id must be a non-empty string without whitespace, got {site_id!r}")
    with _REGISTRY_LOCK:
        if site_id in _REGISTRY:
            raise CensusError(f"duplicate enforcement-point id {site_id!r}")
        site = Site(site_id, declines)
        _REGISTRY[site_id] = site
        return site


def enable(on: bool = True) -> None:
    """The opt-in switch (Part A-2: default OFF). Process-wide."""
    global _ENABLED
    _ENABLED = bool(on)


def enabled() -> bool:
    return _ENABLED


def reset_counters() -> None:
    """Zero every counter (a harness affordance; production never calls it)."""
    with _REGISTRY_LOCK:
        for s in _REGISTRY.values():
            with s._lock:
                s.consulted = s.fired = s.errors = 0


def _clear_registry() -> None:
    """Harness affordance ONLY: forget every declared site (tests declare throwaway ids). Production
    sites are declared at import and never cleared; the underscore is the warning."""
    with _REGISTRY_LOCK:
        _REGISTRY.clear()


def registry() -> tuple[str, ...]:
    """The declared ids, in declaration order."""
    with _REGISTRY_LOCK:
        return tuple(_REGISTRY)


def counters() -> dict[str, dict]:
    with _REGISTRY_LOCK:
        return {k: s.counters() for k, s in _REGISTRY.items()}


# ---- the decision trace (Part A-2: exactly (seq, site_id, decision), nothing else) ---------------

def _record_trace(site_id: str, label: str) -> None:
    with _TRACE_LOCK:
        _TRACE.append((len(_TRACE) + 1, site_id, label))


def trace(on: bool = True) -> None:
    """Record every fired decision as (seq, site_id, decision) — the compared fields, no others."""
    global _TRACING
    _TRACING = bool(on)


def trace_snapshot() -> list[tuple]:
    with _TRACE_LOCK:
        return list(_TRACE)


def trace_reset() -> None:
    with _TRACE_LOCK:
        _TRACE.clear()


# ---- the report (Part A step 3; INV-1, INV-2b, INV-8) -------------------------------------------

def census(declaration: set[str]) -> dict:
    """The census over the DECLARATION: one row per declared id AND per reporting id, with the status
    Part A-1 assigns. Structural reconciliation is the CALLER's (the 0042 evidence's `validate_report`)
    and runs before status regardless of `enabled`; this function emits the rows, including the
    UNDECLARED reporter whose row is the evidence for that refusal."""
    start = time.time()
    enabled_now = _ENABLED
    snap = counters()
    rows = []
    for cid in sorted(set(snap) | set(declaration)):
        c = snap.get(cid, {"consulted": 0, "fired": 0, "errors": 0})
        t = {"enabled": enabled_now, "declared": cid in declaration, **c}
        st = status_of(t)
        rows.append({"id": cid, "status": st} if st == "DISABLED"
                    else {"id": cid, "status": st, "consulted": c["consulted"], "fired": c["fired"], "errors": c["errors"]})
    return {"snapshot": {"snapshot_id": uuid.uuid4().hex, "process_started": _PROCESS_STARTED,
                         "window_start": start, "window_end": time.time(), "enabled": enabled_now,
                         "process": os.getpid(), "unmeasured": sum(1 for r in rows if r["status"] == "UNMEASURED")},
            "rows": rows}
