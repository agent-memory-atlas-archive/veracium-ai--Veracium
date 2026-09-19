"""specs/0042 INV-7 — the INDEPENDENT DECISION OBSERVER (a pytest plugin), one instrument for every arm.

INV-7 (frozen at acceptance) is a decision-trace diff across arms — counters HEALTHY, counters FORCED
TO ERROR, and an UNINSTRUMENTED tree — and the bypass at the four hot predicates (tranche 2b) obliges
a fourth arm, instrumented-but-BYPASSED (the shipped default: census OFF). The trace cannot come from
the census, because the uninstrumented arm has no census in it and the bypassed arm emits none: "two
arms that share the instrument cannot detect the instrument". So this plugin is the instrument the
census is measured against. It wraps every enforcement FUNCTION the declaration names
(`specs/evidence/0042/declaration.py`, column file:symbol — module functions, class methods and
properties; the seven functions nested inside another function cannot be reached from outside and
are EXCLUDED BY NAME in the summary) and records one record per EXIT of such a function:

    (seq, symbol, decision)   decision = the exception's class name, or None / False / True, or "value"

— the census's (seq, site_id, decision) at the granularity an outside instrument can name: a symbol
carries one id for 76 of the 102 declared symbols, and where it carries several the reconciliation
test's COLLAPSE_SWEEP_READ pins them as DISTINCT declining reasons. The record is content-free
(INV-8): no arguments, no return values, no ids. Records are appended as two bytes (symbol index,
label index) and the arm's summary carries their count, their sha256, and the per-(symbol, label)
histogram, so four arms are compared byte-for-byte without holding four traces in one process.

Arms (env `INV7_ARM`): healthy — census enabled + tracing; failing — the same with `Site._bump`
forced to raise (every increment lands in `errors`, UNMEASURED); off — the shipped default; the
census stays disabled and the bypass path runs; uninstrumented — the twin tree (the commit the
tranches began from) on PYTHONPATH: the census module exists there with ZERO declared sites, and
the plugin asserts both facts. In the two census arms the census's own trace and counters are dumped
beside the observer's, for the cross-check the harness runs (the census sees a subsequence of what
the observer sees).

`INV7_MODE=reach` (any arm with the census enabled) records, per test FILE, which declared ids the
file's tests consulted — the measured answer to "name the suites that actually reach the sites".
"""
from __future__ import annotations

import functools
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import pathlib
import sys
import time

ARM = os.environ.get("INV7_ARM", "off")
OUT = pathlib.Path(os.environ.get("INV7_OUT", "inv7-out"))
DECL_PATH = os.environ.get("INV7_DECLARATION")
MODE = os.environ.get("INV7_MODE", "trace")
TWIN = os.environ.get("INV7_TWIN")           # the uninstrumented arm's src root, when ARM == uninstrumented

_SYMBOLS: list[str] = []
_SYM_INDEX: dict[str, int] = {}
_LABELS: list[str] = []
_LAB_INDEX: dict[str, int] = {}
_RECORDS = bytearray()
_HIST: dict[tuple[int, int], int] = {}
_EXCLUDED: list[tuple[str, str]] = []
_WRAPPED: list[str] = []
_REBOUND: list[str] = []
_UNDO: list = []                      # (holder, name, original attribute) and (module, attr, original) — restore order
_REACH: dict[str, dict[str, int]] = {}
_LAST_COUNTERS: dict[str, dict] = {}
_T0 = time.time()


def _label_of(kind: str, value) -> str:
    if kind == "raise":
        return type(value).__name__
    if value is None or isinstance(value, bool):
        return repr(value)
    return "value"


def _record(sym_idx: int, label: str) -> None:
    li = _LAB_INDEX.get(label)
    if li is None:
        if len(_LABELS) >= 255:
            raise RuntimeError("label table overflow")
        li = len(_LABELS); _LABELS.append(label); _LAB_INDEX[label] = li
    _RECORDS.append(sym_idx); _RECORDS.append(li)
    k = (sym_idx, li); _HIST[k] = _HIST.get(k, 0) + 1


def _wrap_callable(fn, sym_idx: int):
    @functools.wraps(fn)
    def observed(*a, **k):
        try:
            r = fn(*a, **k)
        except BaseException as exc:            # the decision is the raise; record and re-raise unchanged
            _record(sym_idx, _label_of("raise", exc))
            raise
        _record(sym_idx, _label_of("return", r))
        return r
    observed.__inv7_original__ = fn
    return observed


def _load_declaration():
    spec = importlib.util.spec_from_file_location("inv7_declaration", DECL_PATH)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _install() -> None:
    import veracium  # noqa: F401 — the package root; product modules import on demand below
    decl = _load_declaration()
    symbols = sorted({row[3] for row in decl.DECLARATION})
    if len(symbols) >= 255:
        raise RuntimeError("symbol table overflow")
    originals = {}
    for sym in symbols:
        module_rel, qual = sym.split(":")
        modname = "veracium." + module_rel[:-3].replace("/", ".")
        if modname.endswith(".__init__"):      # the package module is `veracium`, never a second
            modname = modname[:-len(".__init__")]   # execution of __init__.py under another name
        mod = importlib.import_module(modname)
        parts = qual.split(".")
        holder = mod
        for p in parts[:-1]:
            holder = getattr(holder, p)
        if not (inspect.ismodule(holder) or inspect.isclass(holder)):
            _EXCLUDED.append((sym, "nested inside a function; unreachable from outside"))
            continue
        name = parts[-1]
        raw = holder.__dict__.get(name)
        if raw is None:
            _EXCLUDED.append((sym, f"{name!r} not in {holder.__name__}.__dict__"))
            continue
        idx = len(_SYMBOLS); _SYMBOLS.append(sym); _SYM_INDEX[sym] = idx
        if isinstance(raw, property):
            new = property(_wrap_callable(raw.fget, idx), raw.fset, raw.fdel, raw.__doc__)
        elif isinstance(raw, staticmethod):
            new = staticmethod(_wrap_callable(raw.__func__, idx))
        elif isinstance(raw, classmethod):
            new = classmethod(_wrap_callable(raw.__func__, idx))
        elif inspect.isfunction(raw):
            new = _wrap_callable(raw, idx)
            originals[id(raw)] = (new, sym, raw)       # keyed by identity: module globals include unhashables
        else:
            _EXCLUDED.append((sym, f"unsupported attribute kind {type(raw).__name__}"))
            _SYMBOLS.pop(); del _SYM_INDEX[sym]
            continue
        _UNDO.append((holder, name, raw))
        if inspect.isclass(holder):
            type.__setattr__(holder, name, new)
        else:
            setattr(holder, name, new)
        _WRAPPED.append(sym)
    # from-import bindings: a module that did `from x import f` holds the ORIGINAL; rebind by identity
    # … in EVERY loaded module, not only the package's: a test module or a harness that imported the
    # function by name holds the original too, and would call around the observer
    for modname, mod in list(sys.modules.items()):
        if mod is None or not hasattr(mod, "__dict__"):
            continue
        for attr, val in list(vars(mod).items()):
            hit = originals.get(id(val))
            if hit is not None and hit[2] is val:
                _UNDO.append((mod, attr, val))
                setattr(mod, attr, hit[0]); _REBOUND.append(f"{modname}.{attr} -> {hit[1]}")


def install(declaration_path: str) -> None:
    """In-process use (the miniature in tests/): wrap the declared symbols now; `uninstall()` restores
    every attribute this touched, in reverse order, so a pytest session is left as it was found."""
    global DECL_PATH
    DECL_PATH = declaration_path
    _install()


def uninstall() -> None:
    while _UNDO:
        holder, name, original = _UNDO.pop()
        if inspect.isclass(holder):
            type.__setattr__(holder, name, original)
        else:
            setattr(holder, name, original)
    _WRAPPED.clear(); _REBOUND.clear(); _EXCLUDED.clear()
    _SYMBOLS.clear(); _SYM_INDEX.clear()


def wrapped() -> list:
    return list(_WRAPPED)


def reset_records() -> None:
    """Start a fresh trace (labels/symbols keep their indices so two traces compare byte for byte)."""
    del _RECORDS[:]; _HIST.clear()


def records() -> bytes:
    return bytes(_RECORDS)


def decoded() -> list:
    return [(_SYMBOLS[_RECORDS[i]], _LABELS[_RECORDS[i + 1]]) for i in range(0, len(_RECORDS), 2)]


def _arm_setup() -> None:
    import veracium
    import veracium.census as C
    if ARM == "uninstrumented":
        assert TWIN and pathlib.Path(veracium.__file__).resolve().is_relative_to(pathlib.Path(TWIN).resolve()), \
            (veracium.__file__, TWIN)
        assert not C.enabled()
        return
    if ARM in ("healthy", "failing"):
        C.enable(True); C.trace(True); C.trace_reset(); C.reset_counters()
        if ARM == "failing":
            def boom(self, field):
                raise C.CensusError("INV-7 forced counter failure")
            C.Site._bump = boom
        return
    if ARM == "off":
        assert not C.enabled()
        return
    raise RuntimeError(f"unknown arm {ARM!r}")


def pytest_configure(config):
    OUT.mkdir(parents=True, exist_ok=True)
    _arm_setup()
    if MODE == "trace":
        _install()


_BOUNDARIES: list = []          # (record index at test start, nodeid) — a side file, never in the trace


def pytest_runtest_logstart(nodeid, location):
    if MODE == "trace":
        _BOUNDARIES.append((len(_RECORDS) // 2, nodeid))


def pytest_runtest_logfinish(nodeid, location):
    if MODE != "reach":
        return
    import veracium.census as C
    now = C.counters()
    f = nodeid.split("::")[0]
    bucket = _REACH.setdefault(f, {})
    for sid, c in now.items():
        prev = _LAST_COUNTERS.get(sid, {"consulted": 0, "fired": 0, "errors": 0})
        d = c["consulted"] - prev["consulted"]
        if d > 0:
            bucket[sid] = bucket.get(sid, 0) + d
    _LAST_COUNTERS.update({k: dict(v) for k, v in now.items()})


def pytest_sessionfinish(session, exitstatus):
    import veracium
    import veracium.census as C
    summary = {
        "arm": ARM, "mode": MODE, "exitstatus": int(exitstatus), "python": sys.version.split()[0],
        "veracium_file": veracium.__file__, "duration_s": round(time.time() - _T0, 1),
        "census_enabled": C.enabled(), "census_registry_size": len(C.registry()),
    }
    if MODE == "trace":
        (OUT / "observer_trace.bin").write_bytes(bytes(_RECORDS))
        with open(OUT / "test_boundaries.jsonl", "w") as fh:
            for idx, nodeid in _BOUNDARIES:
                fh.write(json.dumps([idx, nodeid]) + "\n")
        summary.update({
            "records": len(_RECORDS) // 2,
            "sha256": hashlib.sha256(bytes(_RECORDS)).hexdigest(),
            "symbols": _SYMBOLS, "labels": _LABELS,
            "histogram": {f"{_SYMBOLS[s]} -> {_LABELS[l]}": n for (s, l), n in sorted(_HIST.items())},
            "wrapped": _WRAPPED, "excluded": _EXCLUDED, "rebound": _REBOUND,
        })
        if ARM in ("healthy", "failing"):
            tr = C.trace_snapshot()
            with open(OUT / "census_trace.jsonl", "w") as fh:
                for rec in tr:
                    fh.write(json.dumps(rec) + "\n")
            summary["census_trace_records"] = len(tr)
            summary["census_counters"] = C.counters()
    else:
        summary["reach"] = _REACH
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
