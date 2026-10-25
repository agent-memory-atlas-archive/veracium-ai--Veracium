"""Dev's two corrections to SA01 v3 §2b, checked in memory: (1) a table-valued pragma traces two statements in one
execute, and a two-statement string cannot reach execute/executemany at all; (2) DROP INDEX IF EXISTS on an absent
index reports no DROP_INDEX action."""
import sqlite3
A = {getattr(sqlite3, "SQLITE_" + a): a for a in ("DROP_INDEX", "DELETE", "UPDATE", "READ", "SELECT", "PRAGMA", "FUNCTION", "INSERT")}
c = sqlite3.connect(":memory:", isolation_level=None, cached_statements=0)
c.execute("CREATE TABLE t(a)"); c.execute("CREATE INDEX ix ON t(a)")
ev = []
c.set_authorizer(lambda code, a1, *r: (ev.append(("act", A.get(code, code), a1)), sqlite3.SQLITE_OK)[1])
c.set_trace_callback(lambda s: ev.append(("trace", s)))
c.execute("SELECT * FROM pragma_table_xinfo(?)", ("t",)).fetchall()
print("pragma_table_xinfo traces:", [e[1] for e in ev if e[0] == "trace"])
for form in ("execute", "executemany"):
    try:
        getattr(c, form)(*(("SELECT 1; DROP TABLE t",) if form == "execute" else ("SELECT 1; DROP TABLE t", [()])))
        print(form, "two statements: RAN")
    except Exception as e:
        print(form, "two statements:", type(e).__name__, str(e)[:60])
for label in ("present", "absent"):
    if label == "absent": c.execute("DROP INDEX ix")
    else: pass
    ev.clear(); c.execute("DROP INDEX IF EXISTS ix")
    print(f"DROP INDEX IF EXISTS on {label} index:", sorted({e[1] for e in ev if e[0] == "act"}))
    if label == "present": c.execute("CREATE INDEX ix ON t(a)")
