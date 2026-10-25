# census: every recorded write on the unperturbed ladder (steptable q.json) vs the product campaign's step_of
import collections, importlib.util, json, sys
T, Q = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("pa1", f"{T}/specs/evidence/0013/pa1_campaign.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import veracium; assert veracium.__file__.startswith(T), veracium.__file__
lad = json.load(open(Q))["ladder"]
c = collections.Counter(); ex = {}
for path, e in lad.items():
    if "writes" not in e: c[("--", "NO WRITES RECORDED", e.get("outcome", "?"), "")] += 1; ex.setdefault(("--", "NO WRITES RECORDED", e.get("outcome", "?"), ""), path); continue
    for kind, sql, by, rows in e["writes"]:
        st = m.step_of({"kind": kind, "sql": sql, "by": by, "rows": rows})
        key = (kind, st or "-- NO STEP --", by.split(":")[1] if st is None else "", sql[:60] if st is None and kind != "DDL" else "")
        c[key] += 1; ex.setdefault(key, path)
for k, n in sorted(c.items(), key=lambda kv: (kv[0][1] != "-- NO STEP --", kv[0])):
    print(f"{n:6d}  {k[0]:5s} {k[1]:24s} {k[2]:28s} {k[3]}  e.g. {ex[k]}")
