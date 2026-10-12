"""0048 round 2: a small runnable contract harness for §4 (A-D), with §6's planned mechanism mutants run against it.

    python contract_harness_0048.py <tree-root>

<tree-root>/src/veracium must exist: the harness imports `veracium.schema` (Edge, Provenance, EvidenceAuthor,
Volatility, ExpiryBehavior, DEFAULT_EXPIRY) for the model; N4i's baseline arm also imports `veracium.lifecycle` and
`veracium.store.sqlite`. Stdlib sqlite3 plus pydantic. No other argument is taken; a missing or wrong one is refused
(exit 2). About 40 s.

WHAT THIS IS. A MODEL of the design under review, not the implementation, in the shape of the round-1 reviewer's
isolated model. Every name in the MODEL section (`check_bound`, `ModelConfig`, `ModelStore`, `serialise_edge`,
`expire`, `transition`, `confirm`, ...) is THE MODEL'S OWN; none is a name the implementation must use.
- A  `check_bound`, one validator, used by `ModelConfig` construction (`__post_init__`), by its `__setattr__` on the
     two fields (validate, then set), and by `expire()`'s entry. Construction and assignment are separate call sites
     here so that §6's "construction check removed" and "assignment check removed" are separate mutants.
- B  `expire()` reads the three policy values once and validates the pair at entry, before any read of the store;
     the decayed stamp is built by `Provenance.model_validate` (defence in depth).
- C  `serialise_edge` is `Edge.model_validate(e.model_dump()).model_dump_json()`; every edges `json` write in
     `ModelStore` binds its return value, which the N4f gate checks over this file's MODEL section. The gate fails
     CLOSED by the connection's receiver (R2-01): every reference to the store's connection is a form it resolves, or
     it is refused.
- D  one transition per due edge, decided from the row read INSIDE `BEGIN IMMEDIATE` (the only form from v3.3).
     The store keeps a journal and counters, so N4d's snapshot covers more than the edges table. DECAY keeps the
     shipped result (R2-02, v4): `decayed` counts decay-triggered invalidations only, and below the floor the row as
     read is retired with its stored confidence unchanged. N4i checks the model against a fixed table AND against the
     tree's own `expire()` on a real store.
N4h's schedule is §6's: A paused after its listing, B commits, A resumes; the serial control runs B, then A.

WHAT A KILL MEANS HERE. Each §6 mechanism mutant is applied to the MODEL section as exact-once text replacements, and
the §6 cell named as its killer is run on the mutated model. KILLED means that cell fails there BY ITS OWN REFUSAL
and, where §6 names a case in parentheses, that case is among the failures. This shows each cell CAN fire against the design. It is not
the implementation's mutation result, which the round-1 verdict asks for "When implementation is ready".

H-01 (found by this harness, 2026-10-12; closed in v3.3). v3.2's §4D permitted "an equivalent form", a write
conditional on the whole row as read. When that write loses a race, a transition still due on the committed row is
dropped and not counted, which matches no serial order: on N4h's decay case B commits 0.225, A leaves 0.225, and the
serial control gives 0.1125. v3.3 removes the permission and adds the mutant row "a conditional write on the row as
read in place of the in-transaction read"; its MUTANT line below prints those three values.

ROUND 2'S VERDICT (2026-10-12, design ACCEPTED; folded in v4). R2-01: this file's first gate visited only attribute
calls named `execute`/`executescript` and skipped every other call, so `executemany`, an alias of `execute`,
`getattr(conn, "execute")` and `conn.cursor().executemany` each passed it while storing confidence 1.8 (the reviewer
found two, research two more). The gate now refuses any reference to the connection it does not resolve, and nine
forms are mutants of one §6 row. R2-02: the model counted every decay and stored the decayed value below the floor;
the shipped `expire()` does neither (proposals/evidence-0048/r2-verdict/r2_02_matrix.py in the research tree: 7 of 13
branches differed, all from those two mechanisms). The model now keeps the shipped meaning, and N4i holds it.

§6 MUTANT ROWS OUTSIDE THIS MODEL (the complement, stated): the two N4c rows,
  "a copy site writing `confidence` removed from the declared table" and
  "a writer of a form the census does not see, its trigger tokens left unclassified".
They are held by the census and the tripwire (specs/evidence/0048/census_0048.py, tripwire_0048.py, and
tests/test_0048_evidence.py) over the tree, not over a model. Every other §6 mutant row is run here; the row
"**for each of the declared edge writers:** that writer bypasses the helper" runs once per model edge writer
(add_edge, confirm, transition), and the row "**for each connection form the gate does not resolve:** a writer
reaches the connection that way" once per form (nine).

OUTPUT GRAMMAR (dev's test asserts on it; do not reword without telling dev):
  CONTROL <PASS|FAIL> | `<cell>`[ | <failing cases>]
  MUTANT <KILLED|SURVIVED|CRASHED> | <§6 mutant cell text, verbatim> | <§6 killing cell text, verbatim> | <instance> | <detail>
  TALLY: mutants <k>/<n> killed; controls <c>/<m> pass
KILLED means the cell failed by its OWN refusal (and the named case is among its failures); an exception that is not
the cell's refusal is CRASHED, never KILLED (H-02). A CONTROL that crashes is a FAIL. Exit 0 only when k == n, c == m
and nothing crashed; 1 otherwise; 2 on a usage or harness error (a mutant anchor not matching exactly once).
"""
# Mutation-Matrix: tests/test_0048_evidence.py::test_contract_harness_0048_counts_only_a_refusal_as_a_kill
import ast
import itertools
import math
import pathlib
import random
import re
import sys
import tempfile
import threading
import types

if __name__ == "__main__":                            # the MODEL section below imports the tree's schema
    if len(sys.argv) != 2 or not (pathlib.Path(sys.argv[1]) / "src" / "veracium" / "schema.py").is_file():
        print("usage: contract_harness_0048.py <tree-root>   (<tree-root>/src/veracium/schema.py must exist)",
              file=sys.stderr)
        sys.exit(2)
    sys.path.insert(0, str(pathlib.Path(sys.argv[1]).resolve() / "src"))

# ======================================= MODEL BEGIN =======================================
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from veracium.schema import DEFAULT_EXPIRY, Edge, EvidenceAuthor, ExpiryBehavior, Provenance, Volatility

EXPIRY = dict(DEFAULT_EXPIRY)            # cells map SLOW -> DECAY on this copy, as §6's "DECAY mapped for the test"
BOUNDED = ("decay_factor", "confidence_floor")


def check_bound(name, x):
    """A: a real number (int or float, never bool), finite, 0.0 <= x <= 1.0 inclusive; else ValueError naming both."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(f"{name} must be a real number, not {x!r}")
    if not (0.0 <= x <= 1.0):
        raise ValueError(f"{name} must lie in [0, 1], not {x!r}")


class ModelConfig:
    def __init__(self, decay_factor=0.5, confidence_floor=0.3, volatility_lifetime_days=None):
        object.__setattr__(self, "_built", False)
        self.decay_factor = decay_factor
        self.confidence_floor = confidence_floor
        self.volatility_lifetime_days = volatility_lifetime_days or {
            Volatility.PERMANENT: None, Volatility.DURABLE: 730, Volatility.SLOW: 120,
            Volatility.TRANSIENT: 7, Volatility.EPHEMERAL: 1}
        self.__post_init__()

    def __post_init__(self):
        for name in BOUNDED:
            check_bound(name, getattr(self, name))
        object.__setattr__(self, "_built", True)

    def __setattr__(self, name, value):
        if name in BOUNDED and self._built:
            check_bound(name, value)
        object.__setattr__(self, name, value)


def serialise_edge(e):
    """C: revalidate from DUMPED data (an instance is not revalidated: its nested model may be unvalidated)."""
    return Edge.model_validate(e.model_dump()).model_dump_json()


DDL = """
CREATE TABLE edges (rowid INTEGER PRIMARY KEY, id TEXT NOT NULL, user_id TEXT NOT NULL, json TEXT NOT NULL,
                    UNIQUE (id, user_id));
CREATE TABLE journal (seq INTEGER PRIMARY KEY, op TEXT NOT NULL, target TEXT NOT NULL);
CREATE TABLE counters (name TEXT PRIMARY KEY, n INTEGER NOT NULL);
CREATE TABLE redacted (user_id TEXT NOT NULL, target TEXT NOT NULL);
"""


class ModelStore:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=10)
        if not self.conn.execute("SELECT 1 FROM sqlite_master WHERE name='edges'").fetchone():
            self.conn.executescript(DDL)

    def _journal(self, op, target):
        self.conn.execute("INSERT INTO journal (op, target) VALUES (?, ?)", (op, target))
        self.conn.execute("INSERT INTO counters (name, n) VALUES (?, 1) ON CONFLICT(name) DO UPDATE SET n = n + 1",
                          (op,))

    def _begin(self):
        self.conn.execute("BEGIN IMMEDIATE")

    def _end(self, ok):
        if ok:
            self.conn.execute("COMMIT")
        else:
            self.conn.execute("ROLLBACK")

    def add_edge(self, e):
        self._begin()
        try:
            self.conn.execute("INSERT INTO edges (id, user_id, json) VALUES (?, ?, ?) "
                              "ON CONFLICT(id, user_id) DO UPDATE SET json = excluded.json",
                              (e.id, e.user_id, serialise_edge(e)))
            self._journal("add", e.id)
        except BaseException:
            self._end(False)
            raise
        self._end(True)

    def read(self, eid, user_id):
        r = self.conn.execute("SELECT json FROM edges WHERE id=? AND user_id=?", (eid, user_id)).fetchone()
        return None if r is None else r[0]

    def _redacted(self, eid, user_id):
        return self.conn.execute("SELECT 1 FROM redacted WHERE user_id=? AND target=?", (user_id, eid)).fetchone()

    def due_candidates(self, user_id, lifetimes, now):
        out = []
        for eid, raw in self.conn.execute("SELECT id, json FROM edges WHERE user_id=? ORDER BY rowid", (user_id,)):
            e = Edge.model_validate_json(raw)
            if e.invalidated_at is None and not self._redacted(eid, user_id) and _due(e, lifetimes, now):
                out.append((eid, raw))
        return out

    def confirm(self, eid, user_id, now):
        """The overlapping operation of N4h (B): the 0008 shape, max(c, 0.9), observed now, unflagged."""
        self._begin()
        try:
            e = Edge.model_validate_json(self.read(eid, user_id))
            e.provenance = Provenance.model_validate({**e.provenance.model_dump(), "observed_at": now,
                                                      "confidence": max(e.provenance.confidence, 0.9)})
            e.needs_confirmation = False
            self.conn.execute("UPDATE edges SET json=? WHERE id=? AND user_id=?", (serialise_edge(e), eid, user_id))
            self._journal("confirm", eid)
        except BaseException:
            self._end(False)
            raise
        self._end(True)

    def transition(self, eid, user_id, policy, now, listed_raw):
        """D: one store transition per edge, decided from the row read INSIDE the write transaction. Returns the
        counter it moved, or None (no write, not counted). `listed_raw` is the listing's copy of the row; the
        transition does not decide from it (§6's mutants do)."""
        self._begin()
        try:
            raw = self.read(eid, user_id)
            e = _decide_on(raw, eid, user_id, policy, now, self)
            if e is None:
                self._end(True)
                return None
            new, counter = e
            n = self.conn.execute("UPDATE edges SET json=? WHERE id=? AND user_id=?",
                                  (serialise_edge(new), eid, user_id)).rowcount
            if n:
                self._journal(counter, eid)
        except BaseException:
            self._end(False)
            raise
        self._end(True)
        return counter if n else None


def _due(e, lifetimes, now):
    lifetime = lifetimes.get(e.volatility)
    return lifetime is not None and (now - e.provenance.observed_at).days > lifetime


def _decide_on(raw, eid, user_id, policy, now, store):
    """D steps 1-3 on the row as read: absent, inactive, redacted or not due -> None; else (new edge, counter)."""
    factor, floor, lifetimes = policy
    if raw is None or store._redacted(eid, user_id):
        return None
    e = Edge.model_validate_json(raw)
    if e.invalidated_at is not None or not _due(e, lifetimes, now):
        return None
    behaviour = EXPIRY[e.volatility]
    if behaviour == ExpiryBehavior.LAPSE:
        return _invalidated(e, now, "lapsed"), "lapsed"
    if behaviour == ExpiryBehavior.DECAY:
        # R2-02: the shipped meaning. Strictly below the floor, the row AS READ is retired, its stored confidence
        # unchanged, and counted; otherwise the decayed edge is written, and a retained decay is not counted.
        if e.provenance.confidence * factor < floor:
            return _invalidated(e, now, "decayed"), "decayed"
        e.provenance = Provenance.model_validate({**e.provenance.model_dump(),
                                                  "confidence": e.provenance.confidence * factor})
        return e, "decayed_kept"
    if e.needs_confirmation:
        return None
    e.needs_confirmation = True
    return e, "flagged_for_confirmation"


def _invalidated(e, now, reason):
    e.invalidated_at = now
    e.invalidation_reason = reason
    return e


def expire(store, user_id, config, *, now):
    """B: the policy is read ONCE and validated at entry, before the store is read; then one transition per edge."""
    factor, floor = config.decay_factor, config.confidence_floor
    lifetimes = dict(config.volatility_lifetime_days)
    check_bound("decay_factor", factor)
    check_bound("confidence_floor", floor)
    policy = (factor, floor, lifetimes)
    counts = {"lapsed": 0, "decayed": 0, "flagged_for_confirmation": 0}
    for eid, listed_raw in store.due_candidates(user_id, lifetimes, now):
        moved = store.transition(eid, user_id, policy, now, listed_raw)
        if moved is not None and moved != "decayed_kept":     # R2-02: `decayed` counts decay invalidations only
            counts[moved] += 1
    return counts
# ======================================== MODEL END ========================================

HERE = pathlib.Path(__file__)
U = "u1"
NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)
OLD = datetime(2024, 1, 1, tzinfo=timezone.utc)
NEAR_ABOVE_1 = math.nextafter(1.0, 2.0)
NEAR_BELOW_0 = math.nextafter(0.0, -1.0)
REJECTED = (2.0, -1.0, float("nan"), float("inf"), float("-inf"), True, "0.5", NEAR_ABOVE_1, NEAR_BELOW_0)


#: exceptions that mean the MODEL is broken (a mutant's text drifted), never that a cell detected a defect: a cell that
#: catches broadly re-raises these, so run_cell reports them as CRASHED (H-02's class, one level down)
BREAKAGE = (NameError, AttributeError, ImportError, SyntaxError)


def _strict_pairs(pairs):
    """The strict decoder (the evidence-boundary rule, tests/test_0026_relay_lexicon.py): refuse a duplicate key."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


class CellFailure(Exception):
    def __init__(self, cases):
        super().__init__("; ".join(cases))
        self.cases = cases


def model_source():
    s = HERE.read_text()
    a = s.index("# " + "=" * 39 + " MODEL BEGIN")
    b = s.index("# " + "=" * 40 + " MODEL END")
    return s[a:b]


def load(src):
    mod = types.ModuleType("model_0048")
    exec(compile(src, "<model_0048>", "exec"), mod.__dict__)
    return mod


def edge(m, eid, vol, conf, observed=OLD):
    return m.Edge(id=eid, user_id=U, subject="user", relation="works_on", object=eid, volatility=vol,
                  provenance=m.Provenance(author_of_evidence=m.EvidenceAuthor.USER, evidence_ref="ev", confidence=conf,
                                          observed_at=observed))


class Fixture:
    def __init__(self, m):
        self.m = m
        self.dir = tempfile.TemporaryDirectory()
        self.n = 0

    def store(self, name=None):
        self.n += 1
        return self.m.ModelStore(str(pathlib.Path(self.dir.name) / f"{name or self.n}.db"))

    def path(self, name):
        return str(pathlib.Path(self.dir.name) / f"{name}.db")


def snapshot(store):
    return "\n".join(store.conn.iterdump())


def decay_mapped(m):
    m.EXPIRY[m.Volatility.SLOW] = m.ExpiryBehavior.DECAY


def unmapped(m):
    m.EXPIRY.clear()
    m.EXPIRY.update(m.DEFAULT_EXPIRY)


def duck(factor=0.5, floor=0.3):
    """A duck-typed config: no validation of its own, so only B stands between it and the store."""
    from veracium.schema import Volatility as V
    return types.SimpleNamespace(decay_factor=factor, confidence_floor=floor, volatility_lifetime_days={
        V.PERMANENT: None, V.DURABLE: 730, V.SLOW: 120, V.TRANSIENT: 7, V.EPHEMERAL: 1})


def _raises_naming(fn, field):
    try:
        fn()
    except ValueError as ex:
        return field in str(ex)
    return False


# ------------------------------------------------ the §6 cells, over the model ------------------------------------------------
# Each cell is `model_<§6 test name>`, never the §6 name itself: specs/citation_debt.py resolves an accepted spec's
# cited `test_*` names to `^def test_...(` anywhere under specs/evidence/, so a model cell carrying the name would
# make the implementation's owed test read as written (found at the v4 fold, 2026-10-12). Output lines print the
# §6 name.

def model_test_no_maintenance_op_raises_confidence(m, fx):
    decay_mapped(m)
    rng = random.Random(48)
    bad = []
    moved = {"lapsed": 0, "decayed": 0, "flagged_for_confirmation": 0}
    for trial in range(40):
        s = fx.store()
        vols = list(m.Volatility)
        for i in range(6):
            s.add_edge(edge(m, f"e{i}", rng.choice(vols), rng.choice((0.0, 0.3, 0.5, 0.9, 1.0, rng.random())),
                            NOW - timedelta(days=rng.choice((0, 2, 30, 200, 1000)))))
        cfg = m.ModelConfig(decay_factor=rng.choice((0.0, 0.5, 0.9, 1.0, 1, 0)), confidence_floor=rng.choice((0.0, 0.3, 1.0)))
        for run in range(rng.randint(1, 4)):
            before = {i: m.Edge.model_validate_json(s.read(f"e{i}", U)).provenance.confidence for i in range(6)}
            for key, v in m.expire(s, U, cfg, now=NOW + timedelta(days=run)).items():
                moved[key] += v
            for i in range(6):
                c = m.Edge.model_validate_json(s.read(f"e{i}", U)).provenance.confidence
                if not (c <= before[i] and 0.0 <= c <= 1.0):
                    bad.append(f"trial {trial} run {run} e{i}: {before[i]} -> {c}")
    if not all(moved.values()):                 # non-vacuity: every behaviour was exercised
        bad.append(f"a behaviour never ran: {moved}")
    if bad:
        raise CellFailure(bad[:3])


def model_test_config_bounds_are_validated(m, fx):
    bad = [f"{f}={v!r}" for f in m.BOUNDED for v in REJECTED
           if not _raises_naming(lambda: m.ModelConfig(**{f: v}), f)]
    if bad:
        raise CellFailure(bad)


def model_test_boundary_configs_are_still_valid(m, fx):
    bad = []
    for f in m.BOUNDED:
        for v in (0.0, 1.0, 0, 1):
            try:
                m.ModelConfig(**{f: v})
                c = m.ModelConfig()
                setattr(c, f, v)
                if getattr(c, f) != v:
                    bad.append(f"{f}={v!r} assign")
            except ValueError:
                bad.append(f"{f}={v!r}")
    if bad:
        raise CellFailure(bad)


def model_test_config_bounds_hold_on_assignment(m, fx):
    bad = []
    for f in m.BOUNDED:
        for v in REJECTED:
            c = m.ModelConfig()
            old = getattr(c, f)
            if not _raises_naming(lambda: setattr(c, f, v), f):
                bad.append(f"{f}={v!r} accepted")
            elif not (getattr(c, f) == old):
                bad.append(f"{f}={v!r} old value lost")
    if bad:
        raise CellFailure(bad)


def model_test_decay_config_refusal_writes_nothing(m, fx):
    decay_mapped(m)
    bad = []
    configs = [("factor", v, duck(factor=v)) for v in (2.0, -1.0, float("nan"), True, "0.5")] + \
              [("floor", v, duck(floor=v)) for v in (2.0, -0.5, float("nan"))]
    for kind, v, cfg in configs:
        for empty in (False, True):
            s = fx.store()
            if not empty:                       # the TRANSIENT edge is listed first; SLOW is mapped to DECAY
                s.add_edge(edge(m, "t", m.Volatility.TRANSIENT, 0.9))
                s.add_edge(edge(m, "s", m.Volatility.SLOW, 0.9))
            before = snapshot(s)
            label = f"{kind} {v!r}{' (empty store)' if empty else ''}"
            try:
                m.expire(s, U, cfg, now=NOW)
                bad.append(f"{label}: no ValueError")
            except ValueError:
                pass
            except BREAKAGE:
                raise
            except Exception as ex:                 # e.g. the shipped TypeError for "0.5": a real N4d failure
                bad.append(f"{label}: {type(ex).__name__}")
            if snapshot(s) != before:
                bad.append(f"{label}: store changed")
    if bad:
        raise CellFailure(bad)


def model_test_a_later_failure_keeps_the_processed_prefix(m, fx):
    decay_mapped(m)
    s = fx.store()
    s.add_edge(edge(m, "t", m.Volatility.TRANSIENT, 0.9))
    s.add_edge(edge(m, "s", m.Volatility.SLOW, 0.9))
    real = s._journal

    def failing(op, target):
        if target == "s" and op != "add":
            raise RuntimeError("injected store failure")
        real(op, target)
    s._journal = failing
    bad = []
    try:
        m.expire(s, U, m.ModelConfig(), now=NOW)
        bad.append("the injected failure did not propagate")
    except RuntimeError:
        pass
    if m.Edge.model_validate_json(s.read("t", U)).invalidated_at is None:
        bad.append("the first edge's transition was not committed")
    if m.Edge.model_validate_json(s.read("s", U)).provenance.confidence != 0.9:
        bad.append("the second edge's transition was committed")
    if bad:
        raise CellFailure(bad)


def model_test_valid_decay_never_raises(m, fx):
    decay_mapped(m)
    bad = []
    for f, fl in itertools.product((0.0, 0.25, 0.5, 1.0, 0, 1), (0.0, 0.3, 1.0, 0, 1)):
        s = fx.store()
        for i, c in enumerate((0.0, 0.3, 0.9, 1.0)):
            s.add_edge(edge(m, f"e{i}", m.Volatility.SLOW, c))
        try:
            m.expire(s, U, m.ModelConfig(decay_factor=f, confidence_floor=fl), now=NOW)
            for i in range(4):
                m.Edge.model_validate_json(s.read(f"e{i}", U))
        except BREAKAGE:
            raise
        except Exception as ex:
            bad.append(f"f={f!r} floor={fl!r}: {type(ex).__name__}")
    if bad:
        raise CellFailure(bad)


RECOGNISED = {  # normalised SQL -> the index of its `json` parameter
    "insert into edges (id, user_id, json) values (?, ?, ?) on conflict(id, user_id) do update set json = "
    "excluded.json": 2,
    "update edges set json=? where id=? and user_id=?": 0,
    "update edges set json=? where id=? and user_id=? and json=?": 0,
}


def _sql(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _sql(node.left), _sql(node.right)
        return None if a is None or b is None else a + b
    return None


CONN_CALLS = ("execute", "executescript")         # the only connection methods the gate resolves
DYNAMIC = ("getattr", "setattr", "delattr", "vars", "eval", "exec", "compile", "__import__", "globals", "locals")


def _is_self_conn(n):
    return isinstance(n, ast.Attribute) and n.attr == "conn" and isinstance(n.value, ast.Name) and n.value.id == "self"


def _unresolved(tree):
    """R2-01: fail CLOSED by the connection's RECEIVER, not by a method name. Every reference to the store's connection
    is one the gate resolves (a direct call `self.conn.execute(...)` / `self.conn.executescript(...)`, or the one
    assignment in `ModelStore.__init__`); `sqlite3` is used only for that connection; no dynamic attribute access
    outside `ModelConfig`. Anything else (an alias, `executemany`, a cursor, `getattr`, the unbound method, the
    connection passed as an argument, `__dict__`, a second connection) is refused, never skipped."""
    parent = {ch: node for node in ast.walk(tree) for ch in ast.iter_child_nodes(node)}

    def enclosing(node, kind):
        while node in parent:
            node = parent[node]
            if isinstance(node, kind):
                return node
        return None

    def in_store_init(node):
        fn, cls = enclosing(node, ast.FunctionDef), enclosing(node, ast.ClassDef)
        return fn is not None and fn.name == "__init__" and cls is not None and cls.name == "ModelStore"

    bad = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        cls = enclosing(node, ast.ClassDef)
        if isinstance(node, ast.ImportFrom) and node.module == "sqlite3":
            bad.append(f"line {line}: sqlite3 used other than for the store's one connection (from-import)")
        elif isinstance(node, ast.Name) and node.id == "sqlite3":
            p = parent.get(node)
            call = parent.get(p)
            ok = (isinstance(p, ast.Attribute) and p.attr == "connect" and isinstance(call, ast.Call)
                  and call.func is p and isinstance(parent.get(call), ast.Assign)
                  and any(_is_self_conn(t) for t in parent[call].targets) and in_store_init(node))
            if not ok:
                bad.append(f"line {line}: sqlite3 used other than for the store's one connection")
        elif isinstance(node, ast.Attribute) and node.attr == "conn":
            p = parent.get(node)
            if not _is_self_conn(node):
                bad.append(f"line {line}: the connection reached through something other than `self`")
            elif isinstance(p, ast.Assign) and node in p.targets:
                if not in_store_init(node):
                    bad.append(f"line {line}: the connection rebound outside ModelStore.__init__")
            elif not (isinstance(p, ast.Attribute) and p.attr in CONN_CALLS and isinstance(parent.get(p), ast.Call)
                      and parent[p].func is p):
                bad.append(f"line {line}: the connection is reached in a form the gate does not resolve")
        if cls is not None and cls.name == "ModelConfig":
            continue
        if isinstance(node, ast.Name) and node.id in DYNAMIC:
            bad.append(f"line {line}: dynamic access (`{node.id}`) outside ModelConfig")
        elif isinstance(node, ast.Attribute) and node.attr in ("__dict__", "__setattr__", "__getattribute__"):
            bad.append(f"line {line}: dynamic access (`{node.attr}`) outside ModelConfig")
    return bad


def model_test_every_edge_write_goes_through_the_validating_serialiser(m, fx, src=None):
    tree = ast.parse(src)
    bad = _unresolved(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and _is_self_conn(node.func.value)):
            continue
        if node.func.attr == "executescript":
            if not (len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id == "DDL"):
                bad.append(f"line {node.lineno}: executescript of something other than DDL")
            continue
        if node.func.attr != "execute":
            continue
        sql = _sql(node.args[0]) if node.args else None
        if sql is None:
            bad.append(f"line {node.lineno}: an execute whose SQL is not a literal")
            continue
        norm = " ".join(sql.lower().split())
        if not re.search(r"\b(insert|update|replace)\b.*\bedges\b", norm):
            continue
        if norm not in RECOGNISED:
            bad.append(f"line {node.lineno}: an edges write of an unrecognised form")
            continue
        params = node.args[1] if len(node.args) > 1 else None
        k = RECOGNISED[norm]
        v = params.elts[k] if isinstance(params, ast.Tuple) and len(params.elts) > k else None
        if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "serialise_edge"):
            bad.append(f"line {node.lineno}: json is not bound to serialise_edge(...)'s return value")
    if bad:
        raise CellFailure(bad)


def model_test_the_store_refuses_an_out_of_bound_edge(m, fx):
    s = fx.store()
    s.add_edge(edge(m, "ok", m.Volatility.SLOW, 0.5))
    before = snapshot(s)
    p = m.Provenance.model_construct(author_of_evidence=m.EvidenceAuthor.USER, evidence_ref="ev", confidence=1.8, observed_at=OLD)
    e = m.Edge(id="bad", user_id=U, subject="user", relation="works_on", object="x", provenance=p)
    bad = []
    try:
        s.add_edge(e)
        bad.append("an edge carrying confidence 1.8 was accepted")
    except ValueError:
        pass
    if snapshot(s) != before:
        bad.append("the table changed")
    if bad:
        raise CellFailure(bad)


def model_test_factor_is_validated_whatever_the_confidence(m, fx):
    decay_mapped(m)
    bad = []
    for c, f in itertools.product((0.0, 0.3, 0.9), (2.0, NEAR_ABOVE_1, -1.0, float("nan"), True)):
        s = fx.store()
        s.add_edge(edge(m, "s", m.Volatility.SLOW, c))
        before = snapshot(s)
        listed = []
        real = s.due_candidates
        s.due_candidates = lambda *a, **k: listed.append(1) or real(*a, **k)
        label = f"{c} × {f!r}"
        try:
            m.expire(s, U, duck(factor=f), now=NOW)
            bad.append(label)
        except ValueError:
            if listed or snapshot(s) != before:
                bad.append(label)
    if bad:
        raise CellFailure(bad)


def _row(s):
    d = json.loads(s.read("e-1", U), object_pairs_hook=_strict_pairs)
    return {"confidence": round(d["provenance"]["confidence"], 9), "observed": d["provenance"]["observed_at"],
            "needs_confirmation": d["needs_confirmation"], "invalidated": d["invalidated_at"] is not None}


N4H_CASES = (  # name, volatility, observed, confidence, B's operations (on B's store)
    ("confirm", "slow", OLD, 0.6, ("confirm",)),
    ("confirm95", "slow", OLD, 0.95, ("confirm",)),
    ("lapse", "transient", NOW - timedelta(days=60), 0.6, ("confirm",)),
    ("decay", "slow", OLD, 0.9, ("expire", "expire")),
)


def model_test_expiry_is_decided_from_the_current_row(m, fx):
    bad = []
    for name, vol, observed, conf, b_ops in N4H_CASES:
        if name == "decay":
            decay_mapped(m)
        cfg = m.ModelConfig(decay_factor=0.5, confidence_floor=0.0)

        def b_run(B):
            for op in b_ops:
                B.confirm("e-1", U, NOW) if op == "confirm" else m.expire(B, U, cfg, now=NOW)
        # the serial control: B commits, THEN A runs
        S = fx.m.ModelStore(fx.path(f"{name}-serial"))
        S.add_edge(edge(m, "e-1", m.Volatility(vol), conf, observed))
        b_run(S)
        m.expire(S, U, cfg, now=NOW)
        serial = _row(S)
        # the overlap: A paused after its listing, B commits, A resumes
        A = fx.m.ModelStore(fx.path(name))
        B = fx.m.ModelStore(fx.path(name))
        A.add_edge(edge(m, "e-1", m.Volatility(vol), conf, observed))
        listed, go, out = threading.Event(), threading.Event(), {}
        real = A.due_candidates

        def paused(*a, **k):
            r = real(*a, **k)
            listed.set()
            go.wait(10)
            return r
        A.due_candidates = paused
        def a_run():
            try:
                out["A"] = m.expire(A, U, cfg, now=NOW)
            except BaseException as ex:            # surfaced below: a thread's exception is otherwise lost
                out["exc"] = ex
        t = threading.Thread(target=a_run)
        t.start()
        if not listed.wait(10):
            bad.append(f"{name}: A never reached its listing (the overlap did not happen)")
        b_run(B)
        committed = _row(B)
        go.set()
        t.join(10)
        if isinstance(out.get("exc"), BREAKAGE):
            raise out["exc"]
        if t.is_alive() or "A" not in out:
            bad.append(f"{name}: A did not complete")
        after = _row(B)
        if after != serial:
            bad.append(f"{name}: B committed {committed}, A left {after}, serial gives {serial}")
        unmapped(m)
    # the legacy-bytes control: valid, non-canonical json (keys reordered) is processed, not skipped
    s = fx.store("legacy")
    s.add_edge(edge(m, "e-1", m.Volatility.SLOW, 0.6))
    canon = json.loads(s.read("e-1", U), object_pairs_hook=_strict_pairs)
    s.conn.execute("UPDATE edges SET json=? WHERE id=?", (json.dumps(dict(reversed(list(canon.items())))), "e-1"))
    m.expire(s, U, m.ModelConfig(), now=NOW)
    if not json.loads(s.read("e-1", U), object_pairs_hook=_strict_pairs)["needs_confirmation"]:
        bad.append("legacy-bytes control: the row was skipped")
    if bad:
        raise CellFailure(bad)


N4I_CASES = (  # name, confidence, flagged, factor, floor -> the shipped result: (decayed, active, confidence, flagged)
    ("retained", 0.9, False, 0.5, 0.3, (0, True, 0.45, False)),
    ("below the floor", 0.9, False, 0.5, 0.5, (1, False, 0.9, False)),
    ("exactly at the floor", 0.6, False, 0.5, 0.3, (0, True, 0.3, False)),
    ("factor 1.0", 0.9, False, 1.0, 0.3, (0, True, 0.9, False)),
    ("factor 0, floor 0", 0.9, False, 0.0, 0.0, (0, True, 0.0, False)),
    ("factor 0, floor 0.3", 0.9, False, 0.0, 0.3, (1, False, 0.9, False)),
    ("already flagged, retained", 0.9, True, 0.5, 0.3, (0, True, 0.45, True)),
)


def _n4i_result(counts, e):
    return (counts["decayed"], e.invalidated_at is None, round(e.provenance.confidence, 9), e.needs_confirmation)


def model_test_decay_keeps_the_shipped_result(m, fx):
    """N4i (R2-02): SLOW mapped to DECAY, one due edge per case. The model's returned `decayed` count and stored
    edge equal the shipped result table; and the table is the tree's: its own `expire()` on a real store gives it too
    (the baseline arm, so the table cannot drift from what the tree does)."""
    from veracium import lifecycle
    from veracium.schema import DEFAULT_EXPIRY
    from veracium.store.sqlite import SqliteStore
    bad = []
    for name, c, flagged, f, fl, want in N4I_CASES:
        e0 = edge(m, "e", m.Volatility.SLOW, c)
        e0.needs_confirmation = flagged
        decay_mapped(m)
        s = fx.store()
        s.add_edge(e0)
        got = _n4i_result(m.expire(s, U, m.ModelConfig(decay_factor=f, confidence_floor=fl), now=NOW),
                          m.Edge.model_validate_json(s.read("e", U)))
        unmapped(m)
        if got != want:
            bad.append(f"{name}: model {got}, shipped {want}")
        saved = DEFAULT_EXPIRY[m.Volatility.SLOW]
        DEFAULT_EXPIRY[m.Volatility.SLOW] = m.ExpiryBehavior.DECAY      # as a host maps it (§2c row 4)
        try:
            st = SqliteStore(fx.path(f"n4i-{name}"))
            st.add_edge(e0)
            bc = lifecycle.expire(st, U, duck(factor=f, floor=fl), now=NOW)
            base = _n4i_result(bc, [x for x in st.edges(U, active_only=False) if x.id == "e"][0])
        finally:
            DEFAULT_EXPIRY[m.Volatility.SLOW] = saved
        if base != want:
            bad.append(f"{name}: the tree's own expire() gives {base}, the table says {want} (the table is stale)")
    if bad:
        raise CellFailure(bad)


CELLS = [model_test_no_maintenance_op_raises_confidence, model_test_config_bounds_are_validated,
         model_test_boundary_configs_are_still_valid, model_test_config_bounds_hold_on_assignment,
         model_test_decay_config_refusal_writes_nothing, model_test_a_later_failure_keeps_the_processed_prefix,
         model_test_valid_decay_never_raises, model_test_every_edge_write_goes_through_the_validating_serialiser,
         model_test_the_store_refuses_an_out_of_bound_edge, model_test_factor_is_validated_whatever_the_confidence,
         model_test_expiry_is_decided_from_the_current_row, model_test_decay_keeps_the_shipped_result]

# ------------------------------------------------ §6's mutants ------------------------------------------------
# (§6 mutant cell, §6 killing cell, instance, required failing case(s) or None,
#  [(old, new), ...] exact-once replacements in the MODEL section)
ENTRY = ('    check_bound("decay_factor", factor)\n    check_bound("confidence_floor", floor)\n', "")
TXN_READ = "            raw = self.read(eid, user_id)\n            e = _decide_on"
FROM_LISTING = (TXN_READ, "            raw = listed_raw\n            e = _decide_on")
TXN_WRITE = ('            n = self.conn.execute("UPDATE edges SET json=? WHERE id=? AND user_id=?",\n'
             '                                  (serialise_edge(new), eid, user_id)).rowcount')
MUTANTS = [
    ("construction check removed", "`test_config_bounds_are_validated`", "-", None,
     [("        for name in BOUNDED:\n            check_bound(name, getattr(self, name))\n", "")]),
    ("assignment check removed", "`test_config_bounds_hold_on_assignment`", "-", None,
     [("        if name in BOUNDED and self._built:\n            check_bound(name, value)\n", "")]),
    ("assignment sets before validating", "`test_config_bounds_hold_on_assignment`", "-", "old value lost",
     [("        if name in BOUNDED and self._built:\n            check_bound(name, value)\n"
       "        object.__setattr__(self, name, value)\n",
       "        object.__setattr__(self, name, value)\n"
       "        if name in BOUNDED and self._built:\n            check_bound(name, value)\n")]),
    ("exclusive bound (`0 < x < 1`)", "`test_boundary_configs_are_still_valid`", "-", None,
     [("    if not (0.0 <= x <= 1.0):\n", "    if not (0.0 < x < 1.0):\n")]),
    ("NaN-blind comparison (`x < 0 or x > 1`)", "`test_config_bounds_are_validated`", "-", "nan",
     [("    if not (0.0 <= x <= 1.0):\n", "    if x < 0.0 or x > 1.0:\n")]),
    ("`bool` accepted (no explicit refusal)", "`test_config_bounds_are_validated`", "-", "True",
     [("    if isinstance(x, bool) or not isinstance(x, (int, float)):\n",
       "    if not isinstance(x, (int, float)):\n")]),
    ("the entry validation removed, B and C intact", "`test_factor_is_validated_whatever_the_confidence` (`0.3 × 2.0`)",
     "-", "0.3 × 2.0", [ENTRY]),
    ("the floor left unvalidated at entry", "`test_decay_config_refusal_writes_nothing` (floor 2.0)", "-",
     "floor 2.0", [('    check_bound("confidence_floor", floor)\n    policy', "    policy")]),
    ("the entry validation moved back inside the DECAY branch",
     "`test_decay_config_refusal_writes_nothing` (the TRANSIENT edge is lapsed first)", "-",
     "factor 2.0: store changed",
     [ENTRY, ("    if behaviour == ExpiryBehavior.DECAY:\n",
              "    if behaviour == ExpiryBehavior.DECAY:\n"
              '        check_bound("decay_factor", factor)\n        check_bound("confidence_floor", floor)\n')]),
    ("decay write back to unvalidated `model_copy`, entry check also removed",
     "`test_decay_config_refusal_writes_nothing`", "-", None,
     [ENTRY, ('        e.provenance = Provenance.model_validate({**e.provenance.model_dump(),\n'
              '                                                  "confidence": e.provenance.confidence * factor})\n',
              '        e.provenance = e.provenance.model_copy(update={"confidence": e.provenance.confidence * factor})\n')]),
    ("the store helper serialises without validating", "`test_the_store_refuses_an_out_of_bound_edge`", "-", None,
     [("    return Edge.model_validate(e.model_dump()).model_dump_json()\n", "    return e.model_dump_json()\n")]),
    ("the helper accepts an instance without revalidating nested data",
     "`test_the_store_refuses_an_out_of_bound_edge`", "-", None,
     [("    return Edge.model_validate(e.model_dump()).model_dump_json()\n",
       "    return Edge.model_validate(e).model_dump_json()\n")]),
]
BYPASS = "**for each of the declared edge writers:** that writer bypasses the helper"
GATE = "`test_every_edge_write_goes_through_the_validating_serialiser`"
for inst, old in (("add_edge", "                              (e.id, e.user_id, serialise_edge(e)))\n"),
                  ("confirm", '"UPDATE edges SET json=? WHERE id=? AND user_id=?", (serialise_edge(e), eid, user_id))'),
                  ("transition", "(serialise_edge(new), eid, user_id)).rowcount")):
    MUTANTS.append((BYPASS, GATE, inst, None,
                    [(old, old.replace("serialise_edge(e)", "e.model_dump_json()")
                           .replace("serialise_edge(new)", "new.model_dump_json()"))]))
INSERT = ('            self.conn.execute("INSERT INTO edges (id, user_id, json) VALUES (?, ?, ?) "\n'
          '                              "ON CONFLICT(id, user_id) DO UPDATE SET json = excluded.json",\n'
          '                              (e.id, e.user_id, serialise_edge(e)))\n')
_SQL = '"INSERT INTO edges (id, user_id, json) VALUES (?, ?, ?) ON CONFLICT(id, user_id) DO UPDATE SET json = excluded.json"'
_P = "(e.id, e.user_id, e.model_dump_json())"
_I = "            "
FORMS = "**for each connection form the gate does not resolve:** a writer reaches the connection that way"
for inst, need, new in (
        ("executemany", "does not resolve", f"{_I}self.conn.executemany({_SQL}, [{_P}])\n"),
        ("a bound execute alias", "does not resolve", f"{_I}_x = self.conn.execute\n{_I}_x({_SQL}, {_P})\n"),
        ("getattr(conn, 'execute')", "dynamic access", f"{_I}getattr(self.conn, 'execute')({_SQL}, {_P})\n"),
        ("cursor().executemany", "does not resolve", f"{_I}self.conn.cursor().executemany({_SQL}, [{_P}])\n"),
        ("SQL held in a variable", "not a literal", f"{_I}_q = {_SQL}\n{_I}self.conn.execute(_q, {_P})\n"),
        ("parameters held in a variable", "not bound", f"{_I}_p = {_P}\n{_I}self.conn.execute({_SQL}, _p)\n"),
        ("the unbound sqlite3.Connection.execute", "sqlite3 used",
         f"{_I}sqlite3.Connection.execute(self.conn, {_SQL}, {_P})\n"),
        ("a second connection", "sqlite3 used", f"{_I}sqlite3.connect(':memory:').execute({_SQL}, {_P})\n"),
        ("the instance __dict__", "dynamic access", f"{_I}self.__dict__['conn'].execute({_SQL}, {_P})\n")):
    MUTANTS.append((FORMS, GATE, inst, need, [(INSERT, new)]))
MUTANTS += [
    ("a writer calls the helper and ignores its return value", GATE, "add_edge", None,
     [("        self._begin()\n        try:\n            self.conn.execute(\"INSERT INTO edges",
       "        self._begin()\n        try:\n            serialise_edge(e)\n            self.conn.execute(\"INSERT INTO edges"),
      ("                              (e.id, e.user_id, serialise_edge(e)))\n",
       "                              (e.id, e.user_id, e.model_dump_json()))\n")]),
    ("the transition decides from the listing (read outside the transaction)",
     "`test_expiry_is_decided_from_the_current_row` (all four cases)", "-",
     ("confirm:", "confirm95:", "lapse:", "decay:"), [FROM_LISTING]),
    # the two conditional-write rows: decided from the listing's row (the only read a lost race can make stale under
    # N4h's schedule), written conditionally on the fields, or on the read model re-serialised
    ("a write conditional on (confidence, active) as read",
     "`test_expiry_is_decided_from_the_current_row` (`confirm95`)", "-", "confirm95:",
     [FROM_LISTING,
      (TXN_WRITE,
       '            n = self.conn.execute("UPDATE edges SET json=? WHERE id=? AND user_id=? AND '
       "json_extract(json, '$.provenance.confidence')=? AND json_extract(json, '$.invalidated_at') IS NULL\",\n"
       "                                  (serialise_edge(new), eid, user_id, "
       "json.loads(raw)['provenance']['confidence'])).rowcount")]),
    ("a conditional write binding the read model re-serialised",
     "`test_expiry_is_decided_from_the_current_row` (legacy-bytes control)", "-", "legacy-bytes control",
     [(TXN_WRITE,
       '            n = self.conn.execute("UPDATE edges SET json=? WHERE id=? AND user_id=? AND json=?",\n'
       "                                  (serialise_edge(new), eid, user_id, "
       "serialise_edge(Edge.model_validate_json(raw)))).rowcount")]),
    # v3.3 (H-01): §4D's former "equivalent form", decided from the listing's row and written conditionally on the
    # raw json listed with it; a lost race drops a transition still due on the committed row
    ("a conditional write on the row as read in place of the in-transaction read",
     "`test_expiry_is_decided_from_the_current_row` (`decay`)", "-", "decay:",
     [FROM_LISTING,
      (TXN_WRITE,
       '            n = self.conn.execute("UPDATE edges SET json=? WHERE id=? AND user_id=? AND json=?",\n'
       "                                  (serialise_edge(new), eid, user_id, raw)).rowcount")]),
    # v4 (R2-02): the model's pre-verdict decay semantics, each a departure from the shipped result
    ("a retained decay counted as `decayed`", "`test_decay_keeps_the_shipped_result` (`retained`)", "-", "retained:",
     [('        if moved is not None and moved != "decayed_kept":     # R2-02: `decayed` counts decay invalidations only\n'
       "            counts[moved] += 1\n",
       "        if moved is not None:\n"
       '            counts["decayed" if moved == "decayed_kept" else moved] += 1\n')]),
    ("below the floor, the decayed confidence stored", "`test_decay_keeps_the_shipped_result` (`below the floor`)",
     "-", "below the floor:",
     [('        if e.provenance.confidence * factor < floor:\n'
       '            return _invalidated(e, now, "decayed"), "decayed"\n'
       '        e.provenance = Provenance.model_validate({**e.provenance.model_dump(),\n'
       '                                                  "confidence": e.provenance.confidence * factor})\n',
       '        e.provenance = Provenance.model_validate({**e.provenance.model_dump(),\n'
       '                                                  "confidence": e.provenance.confidence * factor})\n'
       '        if e.provenance.confidence < floor:\n'
       '            return _invalidated(e, now, "decayed"), "decayed"\n')]),
    ("the floor comparison inclusive (`<=`)", "`test_decay_keeps_the_shipped_result` (`exactly at the floor`)", "-",
     "exactly at the floor:",
     [("        if e.provenance.confidence * factor < floor:\n", "        if e.provenance.confidence * factor <= floor:\n")]),
]


def run_cell(cell, m, src):
    """-> (outcome, cases): "passed"; "refused", the cell's own CellFailure with its failing cases; or "crashed", any
    other exception. Only a refusal can kill a mutant: a mutant whose text breaks the model (a NameError, a drifted
    signature) crashes, and a crash is not the cell detecting the defect (H-02, dev, 2026-10-12; the 0045 r2 class)."""
    fx = Fixture(m)
    try:
        if cell is model_test_every_edge_write_goes_through_the_validating_serialiser:
            cell(m, fx, src=src)
        else:
            cell(m, fx)
        return "passed", []
    except CellFailure as f:
        return "refused", f.cases
    except Exception as ex:
        return "crashed", [f"{type(ex).__name__}: {str(ex).splitlines()[0][:120] if str(ex) else ''}"]
    finally:
        unmapped(m)
        fx.dir.cleanup()


def main():
    src0 = model_source()
    by_name = {c.__name__.removeprefix("model_"): c for c in CELLS}
    k = n = c = mm = crashed = 0
    m = load(src0)
    for cell in CELLS:
        outcome, fails = run_cell(cell, m, src0)
        mm += 1
        c += outcome == "passed"
        print(f"CONTROL {'PASS' if outcome == 'passed' else 'FAIL'} | `{cell.__name__.removeprefix('model_')}`"
              + ("" if outcome == "passed" else f" | {outcome}: {'; '.join(fails)[:400]}"))
    for row, killer, inst, need, reps in MUTANTS:
        src = src0
        for old, new in reps:
            if src.count(old) != 1:
                print(f"HARNESS ERROR: {row!r} [{inst}]: an anchor occurs {src.count(old)} times", file=sys.stderr)
                sys.exit(2)
            src = src.replace(old, new)
        cell = by_name[re.match(r"`(\w+)`", killer).group(1)]
        outcome, fails = run_cell(cell, load(src), src)
        needs = (need,) if isinstance(need, str) else (need or ())
        killed = outcome == "refused" and all(any(x in f for f in fails) for x in needs)
        verdict = "KILLED" if killed else "CRASHED" if outcome == "crashed" else "SURVIVED"
        n += 1
        k += killed
        crashed += outcome == "crashed"
        print(f"MUTANT {verdict} | {row} | {killer} | {inst}"
              + f" | {'; '.join(fails)[:600] if fails else 'cell passed'}")
    print(f"TALLY: mutants {k}/{n} killed; controls {c}/{mm} pass")
    sys.exit(0 if (k == n and c == mm and not crashed) else 1)


if __name__ == "__main__":
    main()
