"""The v16 carrier delta, GENERATED (the round-4 verdicts: V44 L102 "actual migration DDL and carrier delta"; V45 L116
"a generated carrier delta"; T12, build note b2870871 D4 with addendum 1's M3).

The base is v14, the schema the last release carries (v0.26.1); v15 (0041's step, unreleased) is shown as its own step,
because a released store crosses both in one `migrate_store`. Two halves:
  DECLARED — from `schema_version.SCHEMA_V14/V15/V16`, by object name and equality: every object each step adds,
    changes or removes, with its DDL text and requirement class; the ALTER statements byte-quoted; every column a
    changed or added table gains, with its carrier class from the 0041 census's `DDL_ACCOUNT`
    (tests/test_0041_round10_matrix.py, the account the census enforces) and the table's erasure disposition
    (`_ERASE_TABLES`, 0008 §6g's one rule); the accepted v16 manifests, each digest.
  ACTUAL — `sqlite_master` read from three REAL stores: created at v16, and migrated by the real step from v14 and
    from v15; for each, the text of every object that differs from the declared `SCHEMA_V16` (the ALTER paths), the
    manifest digest and its membership in `accepted_digests(16)` — a digest outside it refuses.
Deriving all eleven accepted digests from every base is research's next-round item, not this artifact's.

    python carrier_delta.py --write   regenerate specs/generated/v16-carrier-delta.md
    python carrier_delta.py --check   exit 1 if a fresh derivation differs from it, or an actual digest is unaccepted
"""
# Mutation-Matrix: tests/test_0044_t12_carrier_delta.py::test_the_delta_refuses_each_planted_defect
from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import re
import sqlite3
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "specs" / "generated" / "v16-carrier-delta.md"


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _sv():
    sys.path.insert(0, str(ROOT / "src"))
    from veracium.store import schema_version as sv
    return sv


def _ddl_account() -> dict:
    """The 0041 census's column account, read from its test module (the account it enforces), {column: class}."""
    path = ROOT / "tests" / "test_0041_round10_matrix.py"
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "DDL_ACCOUNT" for t in node.targets):
            acc = ast.literal_eval(node.value)
            return {col: cls for cls, cols in acc.items() for col in cols}
    raise SystemExit("DDL_ACCOUNT not found in tests/test_0041_round10_matrix.py")


def _erase_tables() -> tuple:
    src = (ROOT / "src" / "veracium" / "store" / "sqlite.py").read_text()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_ERASE_TABLES" for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise SystemExit("_ERASE_TABLES not found in src/veracium/store/sqlite.py")


def _columns(ddl: str) -> list:
    """The (name, type) columns of a CREATE TABLE statement; table constraints (UNIQUE, CHECK, …) skipped."""
    body = ddl[ddl.index("(") + 1:ddl.rindex(")")]
    out, depth, cur = [], 0, ""
    for ch in body:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    cols = []
    for part in out:
        words = part.strip().split()
        if not words or words[0].split("(")[0].upper() in ("UNIQUE", "CHECK", "PRIMARY", "FOREIGN", "CONSTRAINT"):
            continue
        cols.append((words[0], words[1].upper() if len(words) > 1 else ""))
    return cols


def _carrier_class(table: str, col: str, ty: str, account: dict, side: dict):
    """The 0041 census's rule (tests/test_0041_round10_matrix.py, the TEXT/BLOB account): a treated SIDE PATH
    (`redaction.SIDE_TABLE_TREATMENTS`, with its treatment), else the column's `DDL_ACCOUNT` class; a column that is
    neither TEXT nor BLOB holds no content and is outside the census. None: an unaccounted TEXT/BLOB column."""
    path = f"{table}.{col}"
    if path in side:
        return f"treated side path ({side[path]})"
    if path in account:
        return account[path]
    if not ty.startswith(("TEXT", "BLOB")):
        return f"non-text ({ty or 'untyped'}): not a content carrier"
    return None


def _step(before, after) -> dict:
    b, a = {o.name: o for o in before}, {o.name: o for o in after}
    return {"added": sorted(set(a) - set(b)), "removed": sorted(set(b) - set(a)),
            "changed": sorted(n for n in set(a) & set(b) if a[n].ddl != b[n].ddl)}


def _actual(sv) -> list:
    """sqlite_master from a fresh v16 store and from stores migrated by the real step from v14 and v15."""
    from veracium.store.migration import migrate_store
    out = []
    decl = {o.name: o.ddl for o in sv.SCHEMA_V16}
    acc = sv.accepted_digests(16)
    with tempfile.TemporaryDirectory() as d:
        for label, base in (("created at v16", None), ("migrated from v14", 14), ("migrated from v15", 15)):
            p = str(pathlib.Path(d) / f"{label.split()[-1]}.db")
            c = sqlite3.connect(p)
            if base is None:
                sv.create(c, 16)
                c.close()
            else:
                sv.create(c, base)
                c.execute(f"PRAGMA user_version = {base}")
                c.commit()
                c.close()
                migrate_store(p)
            c = sqlite3.connect(p)
            try:
                dg = sv.digest(sv.manifest(c), 16)
                act = {n: s for n, s in c.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL")}
            finally:
                c.close()
            differs = sorted(n for n in set(decl) | set(act) if decl.get(n) != act.get(n))
            out.append({"label": label, "digest": dg, "accepted": dg in acc,
                        "differs": {n: act.get(n) for n in differs}})
    return out


def derive() -> dict:
    sv = _sv()
    account, erase = _ddl_account(), _erase_tables()
    from veracium import redaction as R
    side = {p: str(h) for entries in R.SIDE_TABLE_TREATMENTS.values() for p, h in entries if "." in p}
    v16 = {o.name: o for o in sv.SCHEMA_V16}
    steps = {"v14 -> v15": _step(sv.SCHEMA_V14, sv.SCHEMA_V15), "v15 -> v16": _step(sv.SCHEMA_V15, sv.SCHEMA_V16)}
    tables = []
    v14 = {o.name: o for o in sv.SCHEMA_V14}
    for name in sorted(v16):
        o = v16[name]
        if o.kind != "table":
            continue
        old = v14.get(name)
        new_cols = [c for c in _columns(o.ddl) if old is None or c[0] not in [x[0] for x in _columns(old.ddl)]]
        if not new_cols:
            continue
        v15 = {x.name: x for x in sv.SCHEMA_V15}
        v15_cols = [x[0] for x in _columns(v15[name].ddl)] if name in v15 else []

        def _new_in(col):
            if col in v15_cols:
                return "v15"
            return "v16 (ALTER)" if name in v15 else "v16"
        tables.append({"table": name, "erased_with_user": name in erase,
                       "columns": [{"column": c, "type": ty, "new_in": _new_in(c),
                                    "class": _carrier_class(name, c, ty, account, side)} for c, ty in new_cols]})
    manifests = sorted(json.loads((ROOT / "src" / "veracium" / "store" / "evidence" / "schema_versions.json")
                                  .read_text(), object_pairs_hook=_strict_pairs)["versions"]["16"]["accepted"], key=lambda m: m.get("provenance", ""))
    return {"steps": steps, "objects": {n: {"kind": v16[n].kind, "class": v16[n].policy, "ddl": v16[n].ddl}
                                        for s in steps.values() for n in s["added"] + s["changed"] if n in v16},
            "alters": {"confirmations": list(sv.ALTERS_V15_TO_V16), "redactions": list(sv.ALTERS_V15_TO_V16_REDACTIONS)},
            "tables": tables, "manifests": [{"provenance": m.get("provenance"), "digest": m.get("digest")}
                                            for m in manifests],
            "actual": _actual(sv)}


def problems(d: dict) -> list:
    out = []
    for a in d["actual"]:
        if not a["accepted"]:
            out.append(f"the store {a['label']} manifests digest {a['digest'][:16]}, outside accepted_digests(16)")
    for t in d["tables"]:
        for c in t["columns"]:
            if c["class"] is None:
                out.append(f"TEXT/BLOB column {t['table']}.{c['column']} is neither a treated side path nor in DDL_ACCOUNT")
    for s, v in d["steps"].items():
        if v["removed"]:
            out.append(f"step {s} removes {v['removed']} — the delta is additive by design (0013)")
    return out


def render(d: dict) -> str:
    L = ["# The v16 carrier delta (GENERATED: `specs/evidence/0044/carrier_delta.py`; do not edit)", "",
         "Base: **v14** (the released schema, v0.26.1); v15 (0041, unreleased) is shown as its own step.", ""]
    for s, v in d["steps"].items():
        L.append(f"## Step {s}: {len(v['added'])} added, {len(v['changed'])} changed, {len(v['removed'])} removed")
        L.append("")
        for n in v["added"]:
            o = d["objects"][n]
            L.append(f"- added {o['kind']} `{n}` ({o['class']})")
        for n in v["changed"]:
            L.append(f"- changed `{n}`")
        L.append("")
    L += ["## The ALTER statements (byte-quoted)", ""]
    for t, stmts in d["alters"].items():
        L += [f"`{t}`:", "", "```sql"] + stmts + ["```", ""]
    L += ["## New columns, with their carrier class and erasure", "",
          "| table | new in | erased with the user | column | type | carrier class (0041's account) |", "|---|---|---|---|---|---|"]
    for t in d["tables"]:
        for c in t["columns"]:
            L.append(f"| `{t['table']}` | {c['new_in']} | {'yes' if t['erased_with_user'] else 'no (store-level)'} | "
                     f"`{c['column']}` | {c['type']} | {c['class']} |")
    L += ["", f"## The accepted v16 manifests ({len(d['manifests'])})", "", "| provenance | digest |", "|---|---|"]
    for m in d["manifests"]:
        L.append(f"| {m['provenance']} | `{m['digest']}` |")
    L += ["", "## The ACTUAL DDL: `sqlite_master` from real stores", ""]
    for a in d["actual"]:
        L.append(f"- **{a['label']}**: digest `{a['digest']}`, {'in' if a['accepted'] else 'NOT in'} accepted_digests(16); "
                 f"text differing from the declared SCHEMA_V16: {', '.join(f'`{n}`' for n in a['differs']) or 'none'}")
        for n, sql in a["differs"].items():
            L += ["", "```sql", sql or "(absent)", "```"]
        L.append("")
    L += ["## The object DDL (declared, v16)", ""]
    for n, o in sorted(d["objects"].items()):
        L += [f"### `{n}`", "", "```sql", o["ddl"], "```", ""]
    return "\n".join(L).rstrip("\n") + "\n"


def main(argv) -> int:
    d = derive()
    bad = problems(d)
    for b in bad:
        print("REFUSED:", b)
    if bad:
        return 1
    text = render(d)
    if "--write" in argv:
        OUT.write_text(text)
        s = d["steps"]["v15 -> v16"]
        print(f"wrote {OUT.relative_to(ROOT)}: v15->v16 {len(s['added'])} added, {len(s['changed'])} changed; "
              f"{len(d['manifests'])} accepted manifests; actual: "
              + ", ".join(f"{a['label']} {a['digest'][:8]}" for a in d["actual"]))
        return 0
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text() != text:
            print(f"STALE: {OUT.relative_to(ROOT)} — regenerate with --write")
            return 1
        print("v16 carrier delta current")
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
