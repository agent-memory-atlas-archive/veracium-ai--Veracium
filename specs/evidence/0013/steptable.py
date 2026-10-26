"""The 0007am §4c MIGRATION STEP TABLE, by instrumentation (not by reading the ladder).

QUESTION: for every step of every migration path a store can take to HEAD, is the step's
output (a) BYTE-MATCHED at the step against a reviewed constant, (b) only REVALIDATED by the
same-transaction end-state check (`_validated_current`: accepted_digests + drift repair), or
(c) NEITHER — and does the step write ROWS?

Reproduce from git alone (steptable.out is exactly these five commands' output, in order):
    git -C <repo> archive af1e564 | tar -x -C <tree>
    Q=<repo>/.venv/bin/python                       # CPython 3.14.7, SQLite 3.45.1 (qualified)
    U=<uv cpython-3.14.7>/bin/python3.14            # CPython 3.14.7, SQLite 3.53.1 (unqualified)
    SP=<repo>/.venv/lib/python3.14/site-packages
    STEPTABLE_WORK=/dev/shm PYTHONPATH=<tree>/src $Q -B steptable.py <tree> q.json --campaign
    STEPTABLE_WORK=/dev/shm PYTHONPATH=<tree>/src:$SP $U -B steptable.py <tree> u.json
    python3 steptable.py --compare q.json u.json
    python3 steptable.py --table q.json u.json
(STEPTABLE_PROCS sets the campaign's forked workers, default 6; each has its own store file.)
The qualified build: the repo's .venv (CPython 3.14.7, SQLite 3.45.1). The unqualified build:
uv CPython 3.14.7 (SQLite 3.53.1) with the .venv's site-packages appended to PYTHONPATH
(same ABI). Nothing is installed; the import path is asserted to be <tree>/src.

METHOD
  Paths   : every (base version b < HEAD) x (every ACCEPTED manifest recorded at b), built
            object-by-object from the recorded `objects` sql, fidelity asserted (digest AND
            complete identity equal the record); plus the unstamped legacy base(s); plus the
            0018 release orchestrator over every fixture; plus the HEAD drift-repair path.
            Every fixture is POPULATED (one or more rows per table) so DATA steps act on rows.
  Record  : a proxy over the migration's sqlite3 connection records every statement, the
            issuing frame (first frame under src/veracium/), the rows it changed
            (total_changes delta).
  Classify: on the qualified build, each WRITE statement of each path is perturbed, one at a
            time, at its execution: DDL by text (whitespace, identifier quoting, an added
            column, a changed type, a changed DEFAULT, a changed index, a partial index, the
            object skipped); DML by data (one written value altered, one written row dropped,
            the statement skipped); the stamp by value. The outcome is where it is KILLED:
            at the step's own byte-match check, at the end-state check, by a collateral
            error, ABSORBED (the end state equals the unperturbed one), or SURVIVED.
  Control : the "mutated rewriter" — every DDL statement of a path rewritten at once
            (whitespace; quoting) as a build that normalises stored DDL differently would.
  Builds  : the unperturbed ladder on both builds; --compare checks every path's end state.
            On an unqualified build the 0007 runtime gate is BYPASSED (stated in the output):
            this instrument measures the ladder, not the gate.
Determinism: uuid.uuid4 and the migration's clock are replaced by deterministic fakes so two
runs' end states are comparable byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import traceback
import uuid
from datetime import datetime as _RealDT, timezone

TREE = os.path.realpath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None


# --------------------------------------------------------------------------- compare mode
def compare(a_path, b_path):
    a, b = json.load(open(a_path)), json.load(open(b_path))
    print(f"COMPARE {a['build']['sqlite_version']} ({a['build']['source_id'][:28]}...) vs "
          f"{b['build']['sqlite_version']} ({b['build']['source_id'][:28]}...)")
    keys = sorted(set(a["ladder"]) | set(b["ladder"]))
    bad = 0
    for k in keys:
        x, y = a["ladder"].get(k), b["ladder"].get(k)
        same = x == y
        bad += not same
        print(f"  {'SAME' if same else 'DIFF'}  {k}: "
              f"{(x or {}).get('outcome')}/{(y or {}).get('outcome')} "
              f"schema {(x or {}).get('schema_sha', '-')[:12]}|{(y or {}).get('schema_sha', '-')[:12]} "
              f"data {(x or {}).get('data_sha', '-')[:12]}|{(y or {}).get('data_sha', '-')[:12]} "
              f"writes {(x or {}).get('writes_sha', '-')[:12]}|{(y or {}).get('writes_sha', '-')[:12]}")
    print(f"COMPARE: {len(keys)} paths, {len(keys) - bad} identical end state AND write sequence, {bad} differ")
    return 1 if bad else 0


def _target(kind, sql):
    s = " ".join(sql.split())
    if kind == "DDL":
        m = re.match(r"(?i)CREATE\s+(UNIQUE\s+)?(TABLE|INDEX)\s+(\w+)", s)
        if m:
            return f"CREATE {(m.group(1) or '').upper()}{m.group(2).upper()} {m.group(3)}"
        m = re.match(r"(?i)ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", s)
        if m:
            return f"ALTER {m.group(1)} ADD {m.group(2)}"
        m = re.match(r"(?i)DROP\s+INDEX\s+(?:IF\s+EXISTS\s+)?(\w+)", s)
        if m:
            return f"DROP INDEX {m.group(1)}"
    if kind == "DML":
        m = re.match(r"(?i)(INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM)\s+(\w+)", s)
        if m:
            return f"{m.group(1).split()[0].upper()} {m.group(2)}"
    if kind == "STAMP":
        return "PRAGMA user_version"
    return s[:40]


def table(q_path, u_path):
    """THE STEP TABLE, generated from the qualified run's campaign and both builds' ladders."""
    q, u = json.load(open(q_path)), json.load(open(u_path))
    assert q["build"]["qualified"] and not u["build"]["qualified"], "argument order: qualified, unqualified"
    steps = {}
    for row in q["campaign"]:
        fn = row["by"].rsplit(":", 1)[0]          # file:function (the line kept separately)
        key = (row["by"], _target(row["kind"], row["sql"]))
        st = steps.setdefault(key, {"kind": row["kind"], "paths": set(), "rows": set(), "verdicts": [],
                                    "skip": [], "first": None})
        st["paths"].add(row["path"])
        st["rows"].add(row["rows"])
        (st["skip"] if row["mode"] == "skip" and row["kind"] == "DDL" else st["verdicts"]).append(
            (row["mode"], row["verdict"], (row["kill"] or {}).get("site")))
    def ran_ok(build, by, target):
        hit, ok = 0, 0
        for label, lad in build["ladder"].items():
            if "@orchestrator" in label:
                continue
            if any(w[2] == by and _target(w[0], w[1]) == target for w in lad.get("writes", [])):
                hit += 1
                ok += lad["outcome"] in ("migrated", "current")
        return f"{ok}/{hit}"
    print("THE STEP TABLE (generated). class: (a) every shape perturbation killed by the step's OWN "
          "byte-match; (b) every shape perturbation killed by the end-state check or ABSORBED by drift "
          "repair + S33 revalidation; (c) some perturbation SURVIVED. 'ok' = paths where the unperturbed "
          "step ran and the path completed / paths where the step ran.")
    print("| # | issuing function (file:func:line) | step (target) | kind | writes rows? | paths | class "
          "| killing check(s) | 3.45.1 ok | 3.53.1 ok | skipped-object outcome |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    order = sorted(steps, key=lambda k: (k[0].split(":")[0], int(k[0].rsplit(":", 1)[1]), k[1]))
    crows = []
    for i, key in enumerate(order, 1):
        st = steps[key]
        by, target = key
        vs = st["verdicts"]
        killed_own = all(v.startswith("KILLED BYTE-MATCH") and "OTHER" not in v for _, v, _ in vs
                         if not v.startswith("N/A"))
        caught = all(v.startswith(("KILLED BYTE-MATCH", "KILLED END-STATE")) or v == "ABSORBED"
                     for _, v, _ in vs if not v.startswith("N/A"))
        if st["kind"] == "DDL" and not vs:
            cls = "n/a: no stored output (DROP IF EXISTS; the next statement recreates)"
        elif st["kind"] == "DDL" and vs and killed_own:
            cls = "(a)"
        elif st["kind"] == "DDL" and vs and caught:
            cls = "(b)" + (" repair" if any(v == "ABSORBED" for _, v, _ in vs) else "")
        else:
            cls = "(c)"
        sites = sorted({site for _, v, site in vs if site}) or (
            ["absorbed: _repair_drift + S33 revalidation"] if any(v == "ABSORBED" for _, v, _ in vs) else ["none"])
        if any(v == "ABSORBED" for _, v, _ in vs) and sites[0] != "absorbed: _repair_drift + S33 revalidation":
            sites.append("absorbed by drift repair")
        modes = ", ".join(f"{m}:{v.split()[0]}" for m, v, _ in vs)
        writes_rows = "yes" if st["kind"] in ("DML",) and max(st["rows"]) > 0 else (
            "no" if st["kind"] == "DDL" else "no (stamp)" if st["kind"] == "STAMP" else "no")
        skip = ", ".join(sorted({v.split(" @")[0][:40] for _, v, _ in st["skip"]})) or "-"
        print(f"| {i} | {by} | {target} | {st['kind']} | {writes_rows} | {len(st['paths'])} | {cls} "
              f"| {'; '.join(sites)} | {ran_ok(q, by, target)} | {ran_ok(u, by, target)} | {skip} |")
        if cls == "(c)":
            crows.append((i, by, target, sorted({v[:60] for _, v, _ in vs})))
    print("\n(c) ROWS — 'neither': each perturbation's verdict set")
    for i, by, target, vs in crows:
        print(f"  #{i} {target} [{by}]: {vs}")
    counts = {}
    for _, v, _ in [x for st in steps.values() for x in st["verdicts"] + st["skip"]]:
        counts[v.split(" @")[0][:48]] = counts.get(v.split(" @")[0][:48], 0) + 1
    print(f"\n{len(order)} distinct steps over {len({p for st in steps.values() for p in st['paths']})} paths; "
          f"{sum(len(st['verdicts']) + len(st['skip']) for st in steps.values())} perturbations")
    return 0


if len(sys.argv) > 1 and sys.argv[1] == "--compare":
    sys.exit(compare(sys.argv[2], sys.argv[3]))
if len(sys.argv) > 1 and sys.argv[1] == "--table":
    sys.exit(table(sys.argv[2], sys.argv[3]))

OUT_JSON = sys.argv[2]
CAMPAIGN = "--campaign" in sys.argv

# --------------------------------------------------------------------------- import + assert
import veracium  # noqa: E402
assert os.path.realpath(veracium.__file__).startswith(TREE + os.sep + "src" + os.sep), \
    f"veracium imported from {veracium.__file__}, not from the export {TREE}"
SRC = os.path.join(TREE, "src", "veracium") + os.sep

import veracium.store.schema_version as sv  # noqa: E402
import veracium.store.migration as mig  # noqa: E402
import veracium.store.release_migration as rm  # noqa: E402
import veracium.store.edge_events as ee  # noqa: E402
from veracium.schema import Edge, Provenance  # noqa: E402

HEAD = sv.SCHEMA_VERSION
# STEPTABLE_WORK: where the throwaway stores live (default: beside the output). The run that
# produced steptable.out used /dev/shm: the box's root filesystem was 99% full and fsync-bound.
WORK = tempfile.mkdtemp(prefix="steptable-", dir=os.environ.get("STEPTABLE_WORK")
                        or os.path.dirname(os.path.realpath(OUT_JSON)))

_lines = []


def out(s=""):
    _lines.append(s)
    print(s, flush=True)


ident = sv.runtime_identity()
out(f"BUILD: python {sys.version.split()[0]} sqlite {sqlite3.sqlite_version} source_id {ident['source_id']}")
out(f"veracium imported from {veracium.__file__} (asserted under the export {TREE})")
STATUS = sv.runtime_status()
out(f"runtime_status() = {STATUS.status}" + (f" ({STATUS.reason})" if STATUS.reason else ""))
# The gate (0007 §4g.6 4a) rebuilds every version's constructor and the near-misses on each call, drawing uuids (the
# v5+ mint): memoized to the status computed above so it neither costs each run nor shifts the deterministic uuid
# sequence the cross-build comparison relies on. open_versioned and release_migration read sv's global.
if STATUS.status != "refused":
    sv.runtime_status = lambda: STATUS
    out(f"runtime gate MEMOIZED for this run (computed once above: {STATUS.status})")
else:
    sv.runtime_status = lambda: STATUS._replace(status="verified", reason=None)
    out("RUNTIME GATE BYPASSED for this run: sv.runtime_status -> verified. The instrument measures "
        "the migration ladder on this build, not the 0007 gate (which refuses this build).")
out(f"HEAD = {HEAD}; release orchestrator _MINT_BASE = {rm._MINT_BASE}")

# --------------------------------------------------------------------------- determinism
_ctr = [0]


def _fake_uuid4():
    _ctr[0] += 1
    return uuid.UUID(int=_ctr[0], version=4)


uuid.uuid4 = _fake_uuid4


class _FixedDT(_RealDT):
    @classmethod
    def now(cls, tz=None):
        return _RealDT(2026, 10, 13, 12, 0, 0, tzinfo=tz or timezone.utc)


import veracium.schema as _schema  # noqa: E402
# veracium.schema.utcnow (Provenance.observed_at's default_factory) reads its module's `datetime`:
# the v2->v3 data step re-validates legacy episodes that carry no observed_at, so the model
# FILLS it with the migration's clock — measured, and pinned here so runs compare.
for _m in (mig, sv, ee, _schema):
    _m.datetime = _FixedDT


def _reset_determinism():
    _ctr[0] = 0


# --------------------------------------------------------------------------- the proxy
def _kind(sql):
    s = sql.lstrip().upper()
    if s.startswith(("CREATE", "ALTER", "DROP")):
        return "DDL"
    if s.startswith(("INSERT", "UPDATE", "DELETE", "REPLACE")):
        return "DML"
    if re.match(r"PRAGMA\s+USER_VERSION\s*=", s):
        return "STAMP"
    if s.startswith(("BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE")):
        return "TXN"
    return "READ"


def _issuer():
    f = sys._getframe(2)
    while f is not None:
        fn = os.path.realpath(f.f_code.co_filename)
        if fn.startswith(SRC):
            return f"{os.path.relpath(fn, os.path.join(TREE, 'src'))}:{f.f_code.co_name}:{f.f_lineno}"
        f = f.f_back
    return "?"


class Plan:
    """What to perturb: the k-th WRITE statement (DDL/DML/STAMP) of the run, with a mode;
    or a whole-run DDL rewriter. `expect` is the anchor: the unperturbed sql at k."""

    def __init__(self, k=None, mode=None, expect=None, rewrite_all=None):
        self.k, self.mode, self.expect, self.rewrite_all = k, mode, expect, rewrite_all
        self.anchor_ok = None
        self.applied = None


class Proxy:
    def __init__(self, real, rec, plan):
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "_rec", rec)
        object.__setattr__(self, "_plan", plan)
        object.__setattr__(self, "_w", 0)

    def __getattr__(self, n):
        return getattr(self._real, n)

    def __setattr__(self, n, v):
        setattr(self._real, n, v)

    def __enter__(self):
        return self._real.__enter__()

    def __exit__(self, *a):
        return self._real.__exit__(*a)

    def executescript(self, sql):
        self._rec.append({"kind": "SCRIPT", "sql": sql, "by": _issuer(), "rows": None})
        return self._real.executescript(sql)

    def executemany(self, sql, seq):
        before = self._real.total_changes
        r = self._real.executemany(sql, seq)
        self._rec.append({"kind": _kind(sql), "sql": sql, "by": _issuer(),
                          "rows": self._real.total_changes - before, "many": True})
        return r

    def execute(self, sql, params=(), *a, **kw):
        kind = _kind(sql)
        by = _issuer()
        plan = self._plan
        if kind in ("DDL", "DML", "STAMP"):
            k = self._w
            object.__setattr__(self, "_w", k + 1)
            if plan is not None and plan.rewrite_all and kind == "DDL":
                new = plan.rewrite_all(sql)
                before = self._real.total_changes
                r = self._real.execute(new, params)
                self._rec.append({"kind": kind, "sql": sql, "by": by, "rows": 0, "rewritten": new})
                return r
            if plan is not None and plan.k == k:
                plan.anchor_ok = (sql == plan.expect)
                return _perturb(self._real, sql, params, plan, kind, self._rec, by)
        before = self._real.total_changes
        r = self._real.execute(sql, params)
        self._rec.append({"kind": kind, "sql": sql, "by": by,
                          "rows": self._real.total_changes - before,
                          "params": _short(params)})
        return r


def _short(p):
    try:
        return [x if not isinstance(x, str) or len(x) < 60 else x[:57] + "..." for x in p]
    except TypeError:
        return str(p)[:60]


# --------------------------------------------------------------------------- perturbations
_TABLE_RE = re.compile(r"^\s*(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM)\s+([A-Za-z_][\w]*)", re.I)


def _create_name(sql):
    m = re.match(r"\s*CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_]\w*)", sql, re.I)
    return (m.group(1).upper(), m.group(2)) if m else (None, None)


def _alter_parts(sql):
    m = re.match(r"\s*ALTER\s+TABLE\s+([A-Za-z_]\w*)\s+ADD\s+COLUMN\s+([A-Za-z_]\w*)(.*)$", sql, re.I | re.S)
    return (m.group(1), m.group(2), m.group(3)) if m else (None, None, None)


def ddl_modes(sql):
    s = sql.lstrip().upper()
    if s.startswith("ALTER"):
        modes = ["ws", "quote", "retype", "addcol", "skip"]
        if "DEFAULT" in s:
            modes.insert(3, "default")
        return modes
    typ, _ = _create_name(sql)
    if typ == "TABLE":
        modes = ["ws", "quote", "addcol", "retype", "skip"]
        if "DEFAULT" in s:
            modes.insert(4, "default")
        return modes
    if typ == "INDEX":
        return ["ws", "quote", "cols", "partial", "skip"]
    return ["skip"]


def dml_modes(sql):
    s = sql.lstrip().upper()
    if s.startswith("INSERT"):
        return ["alter", "dropone", "skip"]
    if s.startswith("UPDATE"):
        return ["alter", "skip"]
    if s.startswith("DELETE"):
        return ["skip"]
    return ["skip"]


def _rewrite_ddl(sql, mode):
    """Return the perturbed DDL text, or None for n/a."""
    s = sql
    if s.lstrip().upper().startswith("ALTER"):
        t, col, rest = _alter_parts(s)
        if t is None:
            return None
        if mode == "ws":
            return f"ALTER TABLE {t} ADD COLUMN {col}  {rest.strip()}"
        if mode == "quote":
            return f'ALTER TABLE {t} ADD COLUMN "{col}"{rest}'
        if mode == "retype":
            r2 = re.sub(r"\bTEXT\b", "BLOB", rest, count=1)
            if r2 == rest:
                r2 = re.sub(r"\bINTEGER\b", "NUMERIC", rest, count=1)
            return None if r2 == rest else f"ALTER TABLE {t} ADD COLUMN {col}{r2}"
        if mode == "default":
            r2 = re.sub(r"(DEFAULT\s+)(\S+?)(?=[\s,)]|$)", r"\g<1>999", rest, count=1, flags=re.I)
            return None if r2 == rest else f"ALTER TABLE {t} ADD COLUMN {col}{r2}"
        return None
    typ, name = _create_name(s)
    if typ is None:                       # DROP and anything not CREATE TABLE/INDEX: not rewritten
        return None
    if mode == "ws":
        i = s.index("(")
        return s[:i + 1] + " " + s[i + 1:]
    if mode == "quote":
        return re.sub(rf"\b{re.escape(name)}\b", f'"{name}"', s, count=1)
    if typ == "TABLE":
        if mode == "addcol":
            i = s.index("(")
            return s[:i + 1] + "zz_mut INTEGER, " + s[i + 1:]
        if mode == "retype":
            r2 = re.sub(r"\bTEXT\b", "BLOB", s, count=1)
            if r2 == s:
                r2 = re.sub(r"\bINTEGER\b", "NUMERIC", s, count=1)
            return None if r2 == s else r2
        if mode == "default":
            r2 = re.sub(r"(DEFAULT\s+)(\S+?)(?=[\s,)]|$)", r"\g<1>999", s, count=1, flags=re.I)
            return None if r2 == s else r2
    if typ == "INDEX":
        m = re.search(r"\(([^()]*)\)\s*(WHERE.*)?$", s, re.S)
        if mode == "cols" and m:
            cols = m.group(1)
            parts = [c.strip() for c in cols.split(",")]
            newcols = ", ".join(parts[:-1]) if len(parts) > 1 else parts[0] + " DESC"
            return s[:m.start(1)] + newcols + s[m.end(1):]
        if mode == "partial":
            return None if re.search(r"\bWHERE\b", s, re.I) else s.rstrip() + " WHERE 1"
    return None


def _perturb(real, sql, params, plan, kind, rec, by):
    mode = plan.mode
    if mode == "skip":
        plan.applied = "skipped"
        rec.append({"kind": kind, "sql": sql, "by": by, "rows": 0, "perturbed": "skip"})
        return real.execute("SELECT 1")
    if kind == "DDL":
        if mode == "addcol" and sql.lstrip().upper().startswith("ALTER"):
            r = real.execute(sql, params)
            t, _, _ = _alter_parts(sql)
            real.execute(f"ALTER TABLE {t} ADD COLUMN zz_mut INTEGER")
            plan.applied = "extra ADD COLUMN zz_mut"
            rec.append({"kind": kind, "sql": sql, "by": by, "rows": 0, "perturbed": mode})
            return r
        new = _rewrite_ddl(sql, mode)
        if new is None:
            plan.applied = "n/a"
            return real.execute(sql, params)
        plan.applied = new
        rec.append({"kind": kind, "sql": sql, "by": by, "rows": 0, "perturbed": mode})
        return real.execute(new, params)
    if kind == "STAMP":
        if mode == "alter":
            n = int(re.search(r"=\s*(\d+)", sql).group(1))
            plan.applied = f"stamp {n - 1}"
            return real.execute(f"PRAGMA user_version = {n - 1}")
        plan.applied = "n/a"
        return real.execute(sql, params)
    # DML
    m = _TABLE_RE.match(sql)
    table = m.group(1) if m else None
    if mode == "alter" and sql.lstrip().upper().startswith("UPDATE"):
        p = list(params)
        if p and isinstance(p[0], str):
            try:
                d = json.loads(p[0])
                if isinstance(d, dict):
                    d["zz_mut"] = 1
                    p[0] = json.dumps(d)
                else:
                    p[0] = p[0] + "~"
            except ValueError:
                p[0] = p[0] + "~"
            plan.applied = "UPDATE param[0] altered"
            return real.execute(sql, tuple(p))
        plan.applied = "n/a"
        return real.execute(sql, params)
    before = real.total_changes
    r = real.execute(sql, params)
    changed = real.total_changes - before
    if not changed or table is None:
        plan.applied = "n/a (statement wrote no row)"
        return r
    if mode == "dropone":
        real.execute(f"DELETE FROM {table} WHERE rowid = last_insert_rowid()")
        plan.applied = f"deleted the row just inserted into {table}"
        return r
    if mode == "alter":
        cols = [(c[1], (c[2] or "").upper(), c[5]) for c in real.execute(
            "SELECT * FROM pragma_table_xinfo(?)", (table,)).fetchall()]
        row = real.execute(f"SELECT * FROM {table} WHERE rowid = last_insert_rowid()").fetchone()
        if row is None:
            plan.applied = "n/a (no rowid row)"
            return r
        for (name, typ, pk), val in zip(cols, row):
            if pk:
                continue
            if isinstance(val, str):
                real.execute(f"UPDATE {table} SET {name} = ? WHERE rowid = last_insert_rowid()", (val + "~",))
                plan.applied = f"{table}.{name} altered (+'~')"
                return r
        for (name, typ, pk), val in zip(cols, row):
            if not pk and isinstance(val, int):
                real.execute(f"UPDATE {table} SET {name} = ? WHERE rowid = last_insert_rowid()", (val + 1,))
                plan.applied = f"{table}.{name} altered (+1)"
                return r
        plan.applied = "n/a (no alterable column)"
        return r
    plan.applied = "n/a"
    return r


# --------------------------------------------------------------------------- fixtures
U1, U2 = "u1", "u2"


def _edge_json(eid, user, obj):
    return Edge(id=eid, user_id=user, subject="user", relation="located_at", object=obj,
                valid_from=_RealDT(2026, 1, 1, tzinfo=timezone.utc),
                provenance=Provenance(author_of_evidence="user", evidence_ref=f"ev-{eid}",
                                      observed_at=_RealDT(2026, 1, 1, tzinfo=timezone.utc))
                ).model_dump_json()


LEGACY_OUTCOME = {"id": "leg-1", "user_id": U1, "date": "2026-05-05", "summary": "legacy use",
                  "kind": "outcome", "edge_id": "e1", "outcome": "concurred",
                  "provenance": {"author_of_evidence": "system", "evidence_ref": "run-1"}}

POPULATION_NOTES = {}


def _generic_row(conn, table, overrides):
    cols = conn.execute("SELECT * FROM pragma_table_xinfo(?)", (table,)).fetchall()
    names, vals = [], []
    for cid, name, typ, notnull, dflt, pk, hidden in cols:
        if hidden:
            continue
        if name in overrides:
            v = overrides[name]
        else:
            t = (typ or "").upper()
            v = (1 if "INT" in t else 1.0 if "REAL" in t or "FLOA" in t
                 else b"x" if "BLOB" in t else f"x-{name}")
        names.append(name)
        vals.append(v)
    return names, vals


def _populate(conn, version, label):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    filled, failed = [], []
    for t in tables:
        rows = []
        if t == "edges":
            for eid, user, obj in (("e1", U1, "Porto"), ("e2", U1, "Faro"), ("e3", U2, "Braga")):
                rows.append({"id": eid, "user_id": user, "subject": "user", "relation": "located_at",
                             "object": obj, "active": 1, "quarantined": 0,
                             "json": _edge_json(eid, user, obj)})
        elif t == "episodes":
            rows.append({"id": "leg-1", "user_id": U1, "date": "2026-05-05",
                         "json": json.dumps(LEGACY_OUTCOME)})
        elif t in ("store_identity", "store_epoch"):
            rows.append({"id": 1})
        else:
            rows.append({})
        ok = True
        for ov in rows:
            names, vals = _generic_row(conn, t, ov)
            try:
                conn.execute(f"INSERT INTO {t}({','.join(names)}) VALUES({','.join('?' * len(vals))})", vals)
            except sqlite3.Error as e:
                # second try: every column the schema lets be NULL left NULL
                cols = conn.execute("SELECT * FROM pragma_table_xinfo(?)", (t,)).fetchall()
                nn = {c[1] for c in cols if c[3] or c[5]}
                n2 = [n for n in names if n in nn or n in ov]
                v2 = [v for n, v in zip(names, vals) if n in nn or n in ov]
                try:
                    conn.execute(f"INSERT INTO {t}({','.join(n2)}) VALUES({','.join('?' * len(v2))})", v2)
                except sqlite3.Error as e2:
                    ok = False
                    failed.append(f"{t} ({e2})")
                    break
        if ok:
            filled.append(t)
    POPULATION_NOTES[label] = {"filled": filled, "failed": failed}


def build_fixture(path, version, record, stamped=True, populate=True, label=""):
    conn = sqlite3.connect(path)
    objs = record["objects"]
    for key in sorted(objs, key=lambda k: (objs[k]["type"] != "table", k)):
        conn.execute(objs[key]["sql"])
    got = sv.manifest(conn)
    assert sv.digest(got, version) == record["digest"], f"fixture {label}: digest differs from the record"
    rec_identity = {k: v["sql"] for k, v in objs.items()}
    got_identity = {f"{k[0]}:{k[1]}": v["sql"] for k, v in got.items()}
    assert rec_identity == got_identity, f"fixture {label}: complete identity differs from the record"
    if populate:
        _populate(conn, version, label)
    if stamped:
        conn.execute(f"PRAGMA user_version = {version}")
    conn.commit()
    conn.close()


def paths():
    recs = sv.version_records()
    for b in range(1, HEAD):
        for i, a in enumerate(recs[str(b)]["accepted"]):
            yield f"v{b}#{i}", b, a, True
    for b in sorted(sv.legacy_base_versions()):
        for i, a in enumerate(recs[str(b)]["accepted"]):
            yield f"v{b}#{i}-unstamped", b, a, False


# --------------------------------------------------------------------------- end state
def end_state(path):
    c = sqlite3.connect(path)
    try:
        objs = sv.manifest(c)
        schema = {f"{k[0]}:{k[1]}": v for k, v in sorted(objs.items())}
        data = {}
        for (typ, name) in sorted(objs):
            if typ == "table":
                data[name] = sorted(repr(r) for r in c.execute(f"SELECT * FROM {name}"))
        uv = c.execute("PRAGMA user_version").fetchone()[0]
    finally:
        c.close()
    h = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()
    return {"user_version": uv, "schema_sha": h(schema), "data_sha": h(data),
            "schema": schema, "data": data}


def _diff(a, b):
    d = []
    if a["user_version"] != b["user_version"]:
        d.append(f"user_version {a['user_version']}->{b['user_version']}")
    for k in sorted(set(a["schema"]) | set(b["schema"])):
        if a["schema"].get(k) != b["schema"].get(k):
            d.append(f"schema {k}")
    for k in sorted(set(a["data"]) | set(b["data"])):
        if a["data"].get(k) != b["data"].get(k):
            d.append(f"rows {k}")
    return d


# --------------------------------------------------------------------------- one run
class _Shim:
    def __init__(self, plan, rec):
        self.plan, self.rec = plan, rec

    def __getattr__(self, n):
        return getattr(sqlite3, n)

    def connect(self, *a, **kw):
        return Proxy(sqlite3.connect(*a, **kw), self.rec, self.plan)


def _kill_site(exc):
    tb = traceback.extract_tb(exc.__traceback__)
    inner = [f for f in tb if os.path.realpath(f.filename).startswith(SRC)]
    f = inner[-1] if inner else tb[-1]
    return f"{os.path.relpath(os.path.realpath(f.filename), os.path.join(TREE, 'src'))}:{f.lineno}", f.name


def run(label, b, record, stamped, plan=None, orchestrator=False, fixture_path=None):
    _reset_determinism()
    p = fixture_path or os.path.join(WORK, f"s{os.getpid()}.db")
    if record is not None:                 # a caller-built fixture (fixture_path) is left alone
        for suffix in ("", "-journal", "-wal", rm._AUDIT_SUFFIX):
            try:
                os.remove(os.path.realpath(p) + suffix)
            except FileNotFoundError:
                pass
        build_fixture(p, b, record, stamped=stamped, label=label)
    _reset_determinism()
    rec = []
    shim = _Shim(plan, rec)
    mig.sqlite3, rm.sqlite3 = shim, shim
    try:
        if orchestrator:
            r = rm.run_release_migration(p, host_attestation=rm.MigrationAttestation(
                quiesced=True, backup_ref="steptable"))
            outcome = f"orchestrator:{r.outcome}"
        else:
            r = mig.migrate_store(p)
            outcome = str(r)
        kill = None
    except BaseException as e:   # noqa: BLE001 — the outcome IS the measurement
        site, fn = _kill_site(e)
        outcome = f"raised {type(e).__name__}" + (f"[{e.reason}]" if hasattr(e, "reason") else "")
        kill = {"site": site, "func": fn, "msg": str(e)[:160]}
    finally:
        mig.sqlite3, rm.sqlite3 = sqlite3, sqlite3
    st = end_state(p)
    return {"outcome": outcome, "kill": kill, "rec": rec, "state": st}


# --------------------------------------------------------------------------- byte-match map
def _bytematch_checks():
    """{raise line in migration.py: the table it checks}, read from the source (not typed)."""
    src = open(os.path.join(SRC, "store", "migration.py")).read().splitlines()
    m = {}
    for i, line in enumerate(src, 1):
        if "raise _SITE_MIGRATION_VERSION.fire" in line:
            for j in range(i - 1, max(0, i - 8), -1):
                mm = re.search(r"AND name='(\w+)'", src[j - 1])
                if mm:
                    m[i] = mm.group(1)
                    break
    return m


BYTEMATCH = _bytematch_checks()
END_STATE_FUNC = "_validated_current"


def kill_class(res, stmt):
    """Where a perturbation of `stmt` was killed."""
    k = res["kill"]
    if k is None:
        return None
    file_line = k["site"]
    if file_line.startswith("veracium/store/migration.py:"):
        ln = int(file_line.rsplit(":", 1)[1])
        if ln in BYTEMATCH:
            if stmt is None:                    # the whole-path rewriter: no single statement
                return f"BYTE-MATCH({BYTEMATCH[ln]})"
            t, _, _ = _alter_parts(stmt["sql"])
            own = t == BYTEMATCH[ln]
            return f"BYTE-MATCH({BYTEMATCH[ln]})" + ("" if own else "-OTHER-STEP")
    if k["func"] == END_STATE_FUNC:
        return "END-STATE"
    return f"COLLATERAL({k['func']})"


# --------------------------------------------------------------------------- main
summary = {"build": {"python": sys.version.split()[0], "sqlite_version": sqlite3.sqlite_version,
                     "source_id": ident["source_id"], "qualified": QUALIFIED},
           "ladder": {}, "campaign": [], "rewriter": {}, "population": POPULATION_NOTES}

out("\n== 1. THE UNPERTURBED LADDER (every accepted manifest at every base < HEAD) ==")
baseline = {}
for label, b, a, stamped in paths():
    res = run(label, b, a, stamped)
    writes = [s for s in res["rec"] if s["kind"] in ("DDL", "DML", "STAMP")]
    reads = sum(1 for s in res["rec"] if s["kind"] == "READ")
    baseline[label] = (b, a, stamped, res, writes)
    wsha = hashlib.sha256(json.dumps([(s["kind"], s["sql"], s["rows"]) for s in writes]).encode()).hexdigest()
    summary["ladder"][label] = {"outcome": res["outcome"], "schema_sha": res["state"]["schema_sha"],
                                "data_sha": res["state"]["data_sha"], "user_version": res["state"]["user_version"],
                                "writes_sha": wsha,
                                "writes": [[s["kind"], s["sql"], s["by"], s["rows"]] for s in writes]}
    acc = sv.digest(sv.manifest(sqlite3.connect(os.path.join(WORK, f"s{os.getpid()}.db"))), HEAD) in sv.accepted_digests(HEAD)
    out(f"-- {label} (base {b}, {a.get('provenance')}): {res['outcome']}; {len(writes)} writes, {reads} reads; "
        f"end user_version {res['state']['user_version']}, end digest accepted at HEAD: {acc}; "
        f"populated {POPULATION_NOTES[label]['filled']}; NOT populated {POPULATION_NOTES[label]['failed']}")
    for i, s in enumerate(writes):
        out(f"   W{i:02d} {s['kind']:5} rows={s['rows']} by {s['by']}  {s['sql'][:150]!r}"
            + (f" params={s.get('params')}" if s['kind'] == 'DML' else ""))

out("\n== 1b. THE 0018 RELEASE ORCHESTRATOR over every fixture ==")
for label, (b, a, stamped, _, _) in baseline.items():
    res = run(label, b, a, stamped, orchestrator=True)
    writes = [s for s in res["rec"] if s["kind"] in ("DDL", "DML", "STAMP")]
    summary["ladder"][label + "@orchestrator"] = {"outcome": res["outcome"], "schema_sha": res["state"]["schema_sha"],
                                                 "data_sha": res["state"]["data_sha"],
                                                 "user_version": res["state"]["user_version"],
                                                 "writes_sha": hashlib.sha256(json.dumps(
                                                     [(s["kind"], s["sql"], s["rows"]) for s in writes]).encode()).hexdigest()}
    same = [(s["kind"], s["sql"]) for s in writes] == [(s["kind"], s["sql"]) for s in baseline[label][4]]
    out(f"-- {label}: {res['outcome']}; {len(writes)} writes"
        + (f" — the SAME write sequence as migrate_store's" if same and writes else "")
        + ("" if same or not writes else " — DIFFERS from migrate_store's: " +
           "; ".join(f"{s['by']} {s['sql'][:80]!r}" for s in writes)))

out("\n== 1c. THE HEAD DRIFT-REPAIR PATH (open / release _repair_current): a HEAD store with every rebuildable index dropped ==")
head_rec = sv.version_records()[str(HEAD)]["accepted"][0]
rebuild = sorted(k[1] for k in sv.rebuildable_keys(HEAD))
def _hp():
    return os.path.join(WORK, f"head{os.getpid()}.db")


def _head_with_drift():
    hp = _hp()
    for suffix in ("", rm._AUDIT_SUFFIX):
        try:
            os.remove(os.path.realpath(hp) + suffix)
        except FileNotFoundError:
            pass
    build_fixture(hp, HEAD, head_rec, label="HEAD-drift")
    c = sqlite3.connect(hp)
    for n in rebuild:
        c.execute(f"DROP INDEX {n}")
    c.commit()
    c.close()


_head_with_drift()
res = run("HEAD-drift", HEAD, None, True, fixture_path=_hp())
hwrites = [s for s in res["rec"] if s["kind"] in ("DDL", "DML", "STAMP")]
summary["ladder"]["HEAD-drift"] = {"outcome": res["outcome"], "schema_sha": res["state"]["schema_sha"],
                                   "data_sha": res["state"]["data_sha"], "user_version": res["state"]["user_version"],
                                   "writes": [[s["kind"], s["sql"], s["by"], s["rows"]] for s in hwrites],
                                   "writes_sha": hashlib.sha256(json.dumps(
                                       [(s["kind"], s["sql"], s["rows"]) for s in hwrites]).encode()).hexdigest()}
out(f"-- HEAD-drift via migrate_store: {res['outcome']}; {len(hwrites)} writes")
for i, s in enumerate(hwrites):
    out(f"   W{i:02d} {s['kind']:5} by {s['by']}  {s['sql'][:150]!r}")
baseline["HEAD-drift"] = (HEAD, None, True, res, hwrites)
_head_with_drift()
ores = run("HEAD-drift", HEAD, None, True, orchestrator=True, fixture_path=_hp())
owrites = [s for s in ores["rec"] if s["kind"] in ("DDL", "DML", "STAMP")]
osame = [(s["kind"], s["sql"]) for s in owrites] == [(s["kind"], s["sql"]) for s in hwrites]
out(f"-- HEAD-drift via the 0018 orchestrator (_repair_current): {ores['outcome']}; {len(owrites)} writes"
    + (" — the SAME write sequence as migrate_store's" if osame else " — DIFFERS from migrate_store's"))
summary["ladder"]["HEAD-drift@orchestrator"] = {"outcome": ores["outcome"], "schema_sha": ores["state"]["schema_sha"],
                                                "data_sha": ores["state"]["data_sha"],
                                                "user_version": ores["state"]["user_version"]}

# --------------------------------------------------------------------------- the rewriter control
out("\n== 3. THE MUTATED-REWRITER CONTROL: every DDL statement of a path rewritten at once ==")
REWRITERS = {
    "ws": lambda s: _rewrite_ddl(s, "ws") or s,
    "quote": lambda s: _rewrite_ddl(s, "quote") or s,
}
for rname, fn in REWRITERS.items():
    for label, (b, a, stamped, base_res, writes) in baseline.items():
        if label == "HEAD-drift":
            _head_with_drift()
            res = run(label, b, None, stamped, plan=Plan(rewrite_all=fn), fixture_path=_hp())
        else:
            res = run(label, b, a, stamped, plan=Plan(rewrite_all=fn))
        n_ddl = sum(1 for s in res["rec"] if s.get("rewritten"))
        where = kill_class(res, None) if res["kill"] else None
        survived = _diff(base_res["state"], res["state"]) if not res["kill"] else []
        summary["rewriter"][f"{rname}:{label}"] = {"outcome": res["outcome"], "kill": res["kill"],
                                                   "where": where, "survived_diff": survived}
        out(f"-- [{rname}] {label}: {n_ddl} DDL rewritten -> {res['outcome']}"
            + (f" at {res['kill']['site']} ({where})" if res["kill"] else "")
            + (f"; END STATE DIFFERS: {survived}" if survived else
               ("; end state = unperturbed (absorbed)" if not res["kill"] else "")))

# --------------------------------------------------------------------------- the campaign
def _one(job):
    label, k, mode = job
    b, a, stamped, base_res, writes = baseline[label]
    s = writes[k]
    plan = Plan(k=k, mode=mode, expect=s["sql"])
    if label == "HEAD-drift":
        _head_with_drift()
        res = run(label, b, None, stamped, plan=plan, fixture_path=_hp())
    else:
        res = run(label, b, a, stamped, plan=plan)
    if plan.anchor_ok is not True:
        verdict = f"ANCHOR-MISMATCH (anchor_ok={plan.anchor_ok})"
    elif plan.applied in (None, "n/a") or str(plan.applied).startswith("n/a"):
        verdict = f"N/A ({plan.applied})"
    elif res["kill"]:
        verdict = "KILLED " + kill_class(res, s)
    else:
        d = _diff(base_res["state"], res["state"])
        verdict = ("SURVIVED " + ", ".join(d)) if d else "ABSORBED"
    return {"path": label, "k": k, "by": s["by"], "kind": s["kind"], "rows": s["rows"],
            "sql": s["sql"], "mode": mode, "applied": str(plan.applied)[:120],
            "verdict": verdict, "kill": res["kill"]}


if CAMPAIGN:
    import multiprocessing as _mp
    out("\n== 2. THE PERTURBATION CAMPAIGN (qualified build): every write statement of every path ==")
    jobs = []
    for label, (b, a, stamped, base_res, writes) in baseline.items():
        for k, s in enumerate(writes):
            modes = ddl_modes(s["sql"]) if s["kind"] == "DDL" else (
                dml_modes(s["sql"]) if s["kind"] == "DML" else ["alter", "skip"])
            jobs += [(label, k, m) for m in modes]
    out(f"   {len(jobs)} perturbations; run in {int(os.environ.get('STEPTABLE_PROCS', '6'))} forked workers "
        f"(each with its own store file), reported in job order")
    with _mp.get_context("fork").Pool(int(os.environ.get("STEPTABLE_PROCS", "6"))) as pool:
        rows = pool.map(_one, jobs, chunksize=8)
    for row in rows:
        summary["campaign"].append(row)
        out(f"   {row['path']} W{row['k']:02d} {row['kind']:5} {row['mode']:8} -> {row['verdict']}"
            + (f" @ {row['kill']['site']}" if row["kill"] else "") + f"   [{row['by']}]")

json.dump(summary, open(OUT_JSON, "w"), indent=1, sort_keys=True, default=str)
out(f"\nwrote {OUT_JSON}")
