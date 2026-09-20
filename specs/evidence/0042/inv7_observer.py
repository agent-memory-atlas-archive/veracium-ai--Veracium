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


RECORD_WIDTH = 3          # (symbol, exit ordinal, label) — round 6, R6-5(ii): an exit keyed on the STATEMENT, so two
                          # sites in one function that return the same value are two records, never one
EXIT_IMPLICIT = 254       # the function fell off its end (no return statement executed)
EXIT_PROPAGATED = 253     # an exception raised by a callee passed through (no raise statement of this function)
_EXIT_MAPS: dict = {}     # code object -> {lineno: ordinal} over the function's OWN return/raise statements, in source order


def _exit_map(fn) -> dict:
    code = fn.__code__
    m = _EXIT_MAPS.get(code)
    if m is None:
        m = {}
        try:
            src = inspect.getsource(fn); import textwrap, ast as _ast
            tree = _ast.parse(textwrap.dedent(src)); first = code.co_firstlineno
            # the first statement of the parsed snippet is the def (decorators may precede it: use the def's own line)
            node = next(n for n in _ast.walk(tree) if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)))
            offset = first - node.lineno if not node.decorator_list else first - node.decorator_list[0].lineno
            ordinal = 0
            def walk(n_):
                nonlocal ordinal
                for c in _ast.iter_child_nodes(n_):
                    if isinstance(c, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef, _ast.Lambda)):
                        continue
                    if isinstance(c, (_ast.Return, _ast.Raise)):
                        m[c.lineno + offset] = ordinal; ordinal += 1
                    walk(c)
            walk(node)
        except Exception:
            pass                                # no source (a twin stub, a builtin): every exit reads as implicit
        _EXIT_MAPS[code] = m
    return m


def _record(sym_idx: int, exit_idx: int, label: str) -> None:
    li = _LAB_INDEX.get(label)
    if li is None:
        if len(_LABELS) >= 255:
            raise RuntimeError("label table overflow")
        li = len(_LABELS); _LABELS.append(label); _LAB_INDEX[label] = li
    if exit_idx > 252 and exit_idx not in (EXIT_IMPLICIT, EXIT_PROPAGATED):
        raise RuntimeError("exit ordinal overflow")
    _RECORDS.append(sym_idx); _RECORDS.append(exit_idx); _RECORDS.append(li)
    k = (sym_idx, exit_idx, li); _HIST[k] = _HIST.get(k, 0) + 1


def _wrap_callable(fn, sym_idx: int):
    """Observe every exit of `fn`: the value or the exception, AND the exit STATEMENT (its ordinal among the
    function's return/raise statements), read from the frame's line at the moment it returns or raises — a
    local trace on fn's own frame only, line events off, installed for the duration of the call."""
    code = fn.__code__

    @functools.wraps(fn)
    def observed(*a, **k):
        # Three lines are read from fn's own frame: the last LINE event that landed on an exit statement,
        # the last EXCEPTION event, and the RETURN event. The return event alone is not enough: CPython 3.12
        # attributes the RETURN_VALUE that follows a `with` block's __exit__ call to the `with` statement's
        # line, so a `return` inside `with SITE.consult():` (every census-enabled hot predicate) would read
        # as an implicit exit. The line event on the return statement itself is the honest witness on the
        # RETURN path only: a return statement reached and a return event means that return executed. On the
        # exception path the witness is the exception event alone — a walked return line says nothing about
        # a raise that came from a callee.
        em = _exit_map(fn)
        ret_line = [None]; exc_line = [None]; stmt_line = [None]
        prev = sys.gettrace()

        def local(frame, event, arg):
            if event == "line":
                if frame.f_lineno in em:
                    stmt_line[0] = frame.f_lineno
            elif event == "return":
                ret_line[0] = frame.f_lineno
            elif event == "exception":
                exc_line[0] = frame.f_lineno
            return local

        def tracer(frame, event, arg):
            if event == "call" and frame.f_code is code:
                return local
            return prev(frame, event, arg) if prev else None

        sys.settrace(tracer)
        try:
            try:
                r = fn(*a, **k)
            except BaseException as exc:            # the decision is the raise; record and re-raise unchanged
                # NO statement-line fallback here (research's mutant 1, round 7): an exception event whose line is
                # not a raise statement of this function IS a propagated exception — `try: return x` / `finally:
                # boom()` walks the return line and exits by the callee's raise; the fallback named return #0.
                _record(sym_idx, em.get(exc_line[0], EXIT_PROPAGATED), _label_of("raise", exc))
                raise
            ln = ret_line[0]
            _record(sym_idx, em.get(ln, em.get(stmt_line[0], EXIT_IMPLICIT)), _label_of("return", r))
            return r
        finally:
            sys.settrace(prev)
    observed.__inv7_original__ = fn
    return observed


def _load_declaration():
    spec = importlib.util.spec_from_file_location("inv7_declaration", DECL_PATH)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _install() -> None:
    import veracium  # noqa: F401 — the package root; product modules import on demand below
    # the symbol table starts EMPTY: a symbol's index is its rank among the declared symbols, never "one past
    # whatever was left in the table" (round 7, the floor lane: a unit test left one entry behind and, under
    # pytest-randomly, the first in-process arm's every index read one higher than the other two arms')
    _SYMBOLS.clear(); _SYM_INDEX.clear()
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
    return [(_SYMBOLS[_RECORDS[i]], _RECORDS[i + 1], _LABELS[_RECORDS[i + 2]]) for i in range(0, len(_RECORDS), RECORD_WIDTH)]


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

# EVERY upper-case module-level name, CLASSIFIED (research, round 7 — the third leak of this class in one round: a
# fixture that cleared the production registry, a symbol-table entry left behind that shifted every index of one
# in-process arm, and residue that gave research's own mutant a wrong first reading). `_STATE` is what a run
# MUTATES (containers, and the one scalar `install()` reassigns); `_CONSTANTS` is what it never does, excluded BY
# NAME with the reason. The in-process tests snapshot and restore `_STATE` through a fixture that DERIVES the set of
# upper-case names from the module and asserts it equals the union of the two, so a new name — a container OR a
# scalar flag — must be classified here before the fixture passes. `install()` still starts the symbol table empty.
_STATE = ("_SYMBOLS", "_SYM_INDEX", "_LABELS", "_LAB_INDEX", "_RECORDS", "_HIST", "_EXCLUDED", "_WRAPPED", "_REBOUND",
          "_UNDO", "_REACH", "_LAST_COUNTERS", "_EXIT_MAPS", "_BOUNDARIES",
          "DECL_PATH")                                   # reassigned by install(declaration_path); a scalar
_CONSTANTS = {"ARM": "the arm, read once from the environment at import", "MODE": "trace or reach, read once at import",
              "OUT": "the output directory, read once at import", "TWIN": "the twin's src root, read once at import",
              "RECORD_WIDTH": "the record layout", "EXIT_IMPLICIT": "a sentinel exit ordinal", "EXIT_PROPAGATED": "a sentinel exit ordinal",
              "_T0": "the process start time, set at import", "_STATE": "this classification", "_CONSTANTS": "this classification"}


def pytest_runtest_logstart(nodeid, location):
    if MODE == "trace":
        _BOUNDARIES.append((len(_RECORDS) // RECORD_WIDTH, nodeid))     # a RECORD index, at the declared width


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
            "records": len(_RECORDS) // RECORD_WIDTH, "record_width": RECORD_WIDTH,
            "sha256": hashlib.sha256(bytes(_RECORDS)).hexdigest(),
            "symbols": _SYMBOLS, "labels": _LABELS,
            "histogram": {f"{_SYMBOLS[s]}#{e} -> {_LABELS[l]}": n for (s, e, l), n in sorted(_HIST.items())},
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
