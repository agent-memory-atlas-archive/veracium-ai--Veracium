"""B3 detail: which table each write action names for DDL (schema bookkeeping vs application rows), and whether a
trace callback sees each statement of an executescript (so executions can be counted when the cache hides prepares)."""
import sqlite3
A = {getattr(sqlite3, "SQLITE_" + a): a for a in ("CREATE_INDEX", "CREATE_TABLE", "DELETE", "DROP_INDEX", "DROP_TABLE",
     "INSERT", "UPDATE", "REINDEX", "ALTER_TABLE", "READ", "SELECT", "PRAGMA", "FUNCTION")}
c = sqlite3.connect(":memory:", isolation_level=None, cached_statements=0)
c.executescript("CREATE TABLE t(a); INSERT INTO t VALUES(1); CREATE TABLE t2(a);")
log, trace = [], []
c.set_authorizer(lambda code, a1, a2, db, trig: (log.append((A.get(code, code), a1, a2)), sqlite3.SQLITE_OK)[1])
c.set_trace_callback(trace.append)
for sql in ("CREATE INDEX ix ON t(a)", "DROP TABLE t2", "ALTER TABLE t ADD COLUMN b", "DROP INDEX IF EXISTS ix", "INSERT INTO t(a) VALUES(2)"):
    log.clear(); c.execute(sql)
    print(f"{sql:30s}", sorted({(x[0], x[1]) for x in log if x[0] not in ("READ", "SELECT", "FUNCTION")}))
trace.clear(); c.executescript("SELECT 1; CREATE TABLE t3(a); DROP TABLE t3;")
print("trace inside executescript:", trace)
