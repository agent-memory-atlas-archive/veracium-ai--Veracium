"""The proposed frozen class-(b) rule, decided per STATEMENT TEXT, never by site, from the tree's own constants:
(b1) byte-equal to a HEAD constructor DDL whose kind is table or index;
(b2) exactly `DROP INDEX IF EXISTS <name>` for a HEAD index key whose policy is rebuildable;
(a)  byte-equal to a member of a schema_version ALTERS_* tuple (unchanged by the freeze).
Everything else is OUTSIDE: it owes a named step with a postcondition and cells, or the gate refuses.
Also asserts every HEAD table constructor is a plain CREATE TABLE (no AS SELECT)."""
import json, re, sys
from veracium.store import schema_version as sv
head = sv.SCHEMAS[sv.SCHEMA_VERSION]
b1 = {o.ddl: o.key for o in head if o.key[0] in ("table", "index")}
rebuild_idx = {o.key[1] for o in head if o.key[0] == "index" and o.policy == sv.REBUILDABLE}
b2 = {f"DROP INDEX IF EXISTS {n}" for n in rebuild_idx}
alters = {s: n for n in dir(sv) if n.startswith("ALTERS_") and isinstance(getattr(sv, n), tuple) for s in getattr(sv, n)}
plain = [o.key for o in head if o.key[0] == "table" and re.search(r"\bAS\s+SELECT\b", o.ddl, re.I)]
print("kinds in HEAD:", sorted({o.key[0] for o in head}), "| rebuildable indexes:", len(rebuild_idx), "| table constructors AS SELECT:", plain)
out = {}
for r in json.load(open(sys.argv[1]))["ddl_records"]:
    s = r["sql"]
    c = ("b1 " + b1[s][0]) if s in b1 else "b2 drop" if s in b2 else ("a " + alters[s]) if s in alters else "OUTSIDE: " + " ".join(s.split())[:40]
    k = (c, r["site"]); out.setdefault(k, [0, 0]); out[k][0] += 1; out[k][1] += r["count"]
for k in sorted(out): print(f"{out[k][1]:5d} executions, {out[k][0]:2d} distinct  {k[0]:44s} {k[1]}")
print("TOTAL", sum(v[1] for v in out.values()), "OUTSIDE", sum(v[1] for k, v in out.items() if k[0].startswith("OUTSIDE")))
