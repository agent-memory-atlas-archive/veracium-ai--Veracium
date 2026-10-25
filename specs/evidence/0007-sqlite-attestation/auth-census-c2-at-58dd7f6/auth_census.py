"""SQLite decides what is a write: the authorizer census over the 48 0013-PA1 fixture paths (0007 SQLite round 2,
dev's measurement for the amendment's §2b and C1's control).

Usage: PYTHONPATH=<tree>/src <python> -B auth_census.py <tree> <work> <out.json>

Every connection migrate_store opens is reached through the PA1 seam (`mig.sqlite3 = Shim`), opened with
cached_statements=0, with an authorizer and a trace callback installed. The four rules:
  1. actions are attributed per proxied call (a buffer cleared before the call, taken after); TRANSACTION actions
     and their traces go to their own TXN records;
  2. the TEMPLATE the call was given, never the traced (expanded) text, is what classification compares;
  3. completeness by trace: every trace and every authorizer callback falls inside a proxied call;
     an orphan is a refusal (no per-call count: a table-valued pragma traces a nested statement);
  4. executescript is refused outright.
A statement is a SCHEMA write if its action set holds CREATE/DROP index or table or ALTER_TABLE; a ROW write if it
holds INSERT/UPDATE/DELETE naming a table other than sqlite_master; the STAMP is PRAGMA user_version with an
argument. Schema writes are classified by template text against the tree's own constants: (a) a member of an
ALTERS_* tuple; (b1) a head table/index constructor; (b2) `DROP INDEX IF EXISTS <head rebuildable index>`. Row writes
must map to exactly one PA1 step. The prefix label (steptable._kind) is a cross-check, refusing in the escape
direction; a prefix-DDL text with no schema action is legitimate only as a (b2) no-op.
"""
import collections
import importlib.util
import json
import os
import pathlib
import re
import sqlite3
import sys
import tempfile

tree, work, output = map(pathlib.Path, sys.argv[1:4])
tree = tree.resolve()
spec = importlib.util.spec_from_file_location("pa1", tree / "specs/evidence/0013/pa1_campaign.py")
pa1 = importlib.util.module_from_spec(spec)
sys.modules["pa1"] = pa1
spec.loader.exec_module(pa1)
import veracium
import veracium.store.migration as mig
from veracium.store import schema_version as sv
assert pathlib.Path(veracium.__file__).resolve().is_relative_to(tree)
L = pa1.lib()
STEPS = pa1._steps()

A = sqlite3
SCHEMA_ACTS = {A.SQLITE_CREATE_INDEX, A.SQLITE_CREATE_TABLE, A.SQLITE_DROP_INDEX, A.SQLITE_DROP_TABLE,
               A.SQLITE_ALTER_TABLE}
REFUSED_ACTS = {A.SQLITE_CREATE_TEMP_INDEX, A.SQLITE_CREATE_TEMP_TABLE, A.SQLITE_CREATE_TEMP_TRIGGER,
                A.SQLITE_CREATE_TEMP_VIEW, A.SQLITE_CREATE_TRIGGER, A.SQLITE_CREATE_VIEW, A.SQLITE_DROP_TEMP_INDEX,
                A.SQLITE_DROP_TEMP_TABLE, A.SQLITE_DROP_TEMP_TRIGGER, A.SQLITE_DROP_TEMP_VIEW, A.SQLITE_DROP_TRIGGER,
                A.SQLITE_DROP_VIEW, A.SQLITE_ATTACH, A.SQLITE_DETACH, A.SQLITE_CREATE_VTABLE, A.SQLITE_DROP_VTABLE}
ROW_ACTS = {A.SQLITE_INSERT, A.SQLITE_UPDATE, A.SQLITE_DELETE}
MASTER = {"sqlite_master", "sqlite_temp_master", "sqlite_schema", "sqlite_temp_schema"}

head = sv.SCHEMAS[sv.SCHEMA_VERSION]
B1 = {o.ddl for o in head if o.key[0] in ("table", "index")}
B2 = {f"DROP INDEX IF EXISTS {o.key[1]}" for o in head if o.key[0] == "index" and o.policy == sv.REBUILDABLE}
ALTERS = {s for n in dir(sv) if n.startswith("ALTERS_") and isinstance(getattr(sv, n), tuple) for s in getattr(sv, n)}


class Census:
    def __init__(self):
        self.calls = []          # one record per proxied call
        self.orphans = []        # traces outside any proxied call
        self.cur = None

    def auth(self, code, a1, a2, db, trig):
        if self.cur is not None:
            self.cur["acts"].append((code, a1, a2))
        else:
            self.orphans.append({"auth": (code, a1, a2)})
        return A.SQLITE_OK

    def trace(self, text):
        if self.cur is not None:
            self.cur["traces"].append(text)
        else:
            self.orphans.append({"trace": text})


class AuthProxy:
    def __init__(self, real, census):
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "_c", census)

    def __getattr__(self, n):
        return getattr(self._real, n)

    def __setattr__(self, n, v):
        setattr(self._real, n, v)

    def __enter__(self):
        return self._real.__enter__()

    def __exit__(self, *a):
        return self._real.__exit__(*a)

    def _call(self, how, sql, run, n_rows=1):
        rec = {"how": how, "sql": sql, "by": L["_issuer"](), "acts": [], "traces": [], "n": n_rows}
        self._c.cur = rec
        try:
            return run()
        finally:
            self._c.cur = None
            self._c.calls.append(rec)

    def execute(self, sql, params=()):
        return self._call("execute", sql, lambda: self._real.execute(sql, params))

    def executemany(self, sql, seq):
        seq = list(seq)
        return self._call("executemany", sql, lambda: self._real.executemany(sql, seq), len(seq))

    def executescript(self, sql):
        return self._call("executescript", sql, lambda: self._real.executescript(sql))


def classify(rec):
    acts = [a for a in rec["acts"] if a[0] != A.SQLITE_TRANSACTION]
    txn = len(acts) != len(rec["acts"]) and not acts
    traces = [t for t in rec["traces"] if not re.match(r"\s*(BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE)\b", t, re.I)]
    codes = {a[0] for a in acts}
    out = {"refusals": []}
    if rec["how"] == "executescript":
        out["refusals"].append("executescript (rule 4)")
    # rule 3 is completeness only (orphans, counted by the caller): a table-valued pragma traces a nested statement,
    # and execute/executemany already refuse a second statement themselves
    out["traces"] = len(traces)
    if codes & REFUSED_ACTS:
        out["refusals"].append("refused action " + ",".join(str(c) for c in sorted(codes & REFUSED_ACTS)))
    pragmas = [(a[1], a[2]) for a in acts if a[0] == A.SQLITE_PRAGMA]
    if codes & SCHEMA_ACTS:
        s = rec["sql"]
        out["class"] = "a" if s in ALTERS else "b1" if s in B1 else "b2" if s in B2 else "OUTSIDE"
    elif any(a[0] in ROW_ACTS and a[1] not in MASTER for a in acts):
        w = {"kind": "DML", "sql": rec["sql"], "by": rec["by"]}
        hits = [n for n, pred in STEPS.items() if pred(w)]
        out["class"] = "row:mapped" if len(hits) == 1 else f"row:UNMAPPED({len(hits)})"
    elif pragmas and pragmas[0][0].lower() == "user_version" and pragmas[0][1] is not None:
        out["class"] = "stamp"
    elif pragmas:
        out["class"] = "pragma:" + pragmas[0][0].lower()
    elif txn:
        out["class"] = "txn"
    else:
        out["class"] = "read"
    if out["class"] in ("b1", "b2"):
        out["b_row_effects"] = sorted({a[1] for a in acts if a[0] in ROW_ACTS and a[1] not in MASTER})
    label = L["_kind"](rec["sql"])
    want = {"a": "DDL", "b1": "DDL", "b2": "DDL", "OUTSIDE": "DDL", "stamp": "STAMP", "txn": "TXN"}.get(
        out["class"], "DML" if out["class"].startswith("row") else "READ")
    out["prefix"] = label
    # the cross-check refuses in the ESCAPE direction (SQLite shows a write the prefix does not label); the reverse,
    # a prefix-DDL text with no schema action, is legitimate only as a (b2) no-op (`IF EXISTS` of an absent index)
    if label == "DDL" and out["class"] == "read" and rec["sql"] in B2:
        out["class"] = "b2-noop"
        out["disagree"] = False
    else:
        out["disagree"] = label != want
    return out


tot = collections.Counter()
disagreements, outside, unmapped, refusals, orphans, paths = [], [], [], [], [], []
path = str(pathlib.Path(tempfile.mkdtemp(dir=work)) / "probe.db")
MODE = os.environ.get("AUTH_CENSUS_FIXTURES", "pa1")
REBUILD = sorted(o for o in head if o.key[0] == "index" and o.policy == sv.REBUILDABLE)


def drifted(path, label):
    """C2/C3's fixtures: a PA1 path migrated to HEAD outside the census, then its rebuildable indexes drifted.
    `wrong`: ONE rebuildable index recreated under its own name on another column (a present-and-wrong index, the
    only case whose repair DROP has a DROP_INDEX action); `missing`: every rebuildable index dropped (the step
    table's HEAD-drift fixture, steptable.py _head_with_drift; every repair DROP is then a no-op)."""
    pa1.fresh_fixture(path, label)
    mig.migrate_store(path)
    c = sqlite3.connect(path)
    if MODE == "wrong":
        o = REBUILD[0]
        table = c.execute("SELECT tbl_name FROM sqlite_master WHERE type='index' AND name=?", (o.key[1],)).fetchone()[0]
        cols = {r[2] for r in c.execute(f"PRAGMA index_info({o.key[1]})")}
        other = next(r[1] for r in c.execute(f"PRAGMA table_info({table})") if r[1] not in cols)
        c.execute(f"DROP INDEX {o.key[1]}")
        c.execute(f"CREATE INDEX {o.key[1]} ON {table}({other})")
    else:
        for o in REBUILD:
            c.execute(f"DROP INDEX {o.key[1]}")
    c.commit()
    c.close()


labels = [lab for lab, _, _, _ in L["paths"]()]
for label in (labels if MODE == "pa1" else labels[:1]):
    if MODE == "pa1":
        pa1.fresh_fixture(path, label)
    else:
        drifted(path, label)
    c = sqlite3.connect(path)
    before = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    c.close()
    census = Census()

    class Shim(L["_Shim"]):
        def connect(self, *a, **kw):
            kw["cached_statements"] = 0
            real = sqlite3.connect(*a, **kw)
            real.set_authorizer(census.auth)
            real.set_trace_callback(census.trace)
            return AuthProxy(real, census)

    mig.sqlite3 = Shim(None, [])
    try:
        result, error = mig.migrate_store(path), None
    except Exception as exc:  # noqa: BLE001 - the outcome is the measurement
        result, error = None, repr(exc)
    finally:
        mig.sqlite3 = sqlite3
    c = sqlite3.connect(path)
    after = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    c.close()
    paths.append({"path": label, "result": str(result), "error": error, "episodes": [before, after]})
    for rec in census.calls:
        k = classify(rec)
        tot[k["class"]] += 1
        if k["disagree"]:
            disagreements.append((rec["sql"][:70], rec["by"], k["prefix"], k["class"]))
        if k["class"] == "OUTSIDE":
            outside.append((rec["sql"][:70], rec["by"]))
        if k["class"].startswith("row:UNMAPPED"):
            unmapped.append((rec["sql"][:70], rec["by"]))
        for r in k["refusals"]:
            refusals.append((r, rec["sql"][:60], rec["by"]))
        if k.get("b_row_effects"):
            refusals.append(("(b) statement with row effects " + ",".join(k["b_row_effects"]), rec["sql"][:60],
                             rec["by"]))
    orphans += census.orphans

C = collections.Counter
body = {"tree": str(tree), "paths": paths, "classes": dict(sorted(tot.items())),
        "disagreements": [list(k) + [n] for k, n in C(disagreements).items()],
        "outside": [list(k) + [n] for k, n in C(outside).items()],
        "unmapped_row_writes": [list(k) + [n] for k, n in C(unmapped).items()],
        "refusals": [list(k) + [n] for k, n in C(refusals).items()],
        "orphan_traces": len(orphans)}
output.write_text(json.dumps(body, indent=2) + "\n")
print(json.dumps({"paths": len(paths), "errors": sum(p["error"] is not None for p in paths),
                  "losing_episodes": sum(p["episodes"][1] < p["episodes"][0] for p in paths),
                  "classes": body["classes"], "disagreements": len(disagreements), "outside": len(outside),
                  "unmapped_row_writes": len(unmapped), "refusals": len(refusals), "orphans": len(orphans)}))
