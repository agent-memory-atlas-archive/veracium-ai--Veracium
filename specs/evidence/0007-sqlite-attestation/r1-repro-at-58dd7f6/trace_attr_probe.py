"""Dev's precision item, checked: expanded SQL in trace; action/trace order on a legacy-isolation connection; and how
many traces one executemany() call produces (one prepare, so one action set, but N executions)."""
import sqlite3
A = {getattr(sqlite3, "SQLITE_" + a): a for a in ("INSERT", "TRANSACTION", "UPDATE", "READ", "CREATE_TABLE", "SELECT")}
for iso in (None, ""):
    c = sqlite3.connect(":memory:", isolation_level=iso, cached_statements=0)
    c.execute("CREATE TABLE t(a)")
    ev = []
    c.set_authorizer(lambda code, *a: (ev.append(("act", A.get(code, code), a[0])), sqlite3.SQLITE_OK)[1])
    c.set_trace_callback(lambda s: ev.append(("trace", s)))
    c.execute("INSERT INTO t VALUES (?)", ("x",))
    print(f"isolation_level={iso!r} execute:", ev); ev.clear()
    c.executemany("INSERT INTO t VALUES (?)", [("y",), ("z",), ("w",)])
    print(f"isolation_level={iso!r} executemany x3:", ev)
    c.close()
