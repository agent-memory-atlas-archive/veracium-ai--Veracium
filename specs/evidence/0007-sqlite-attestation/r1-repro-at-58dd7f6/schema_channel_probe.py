"""Dev's P1, checked in memory: setconfig(WRITABLE_SCHEMA) is invisible to authorizer and trace; a sqlite_master-only write
reports only sqlite_master; and which calls report REINDEX (it accompanies CREATE INDEX)."""
import sqlite3
ACTIONS = ("CREATE_INDEX CREATE_TABLE DELETE DROP_INDEX DROP_TABLE INSERT PRAGMA READ SELECT UPDATE ALTER_TABLE "
           "REINDEX ANALYZE FUNCTION TRANSACTION").split()
A = {getattr(sqlite3, "SQLITE_" + a): a for a in ACTIONS}
c = sqlite3.connect(":memory:", isolation_level=None, cached_statements=0)
c.execute("CREATE TABLE episodes(a)"); c.execute("INSERT INTO episodes VALUES (1)"); c.execute("CREATE TABLE t(a)")
ev = []
c.set_authorizer(lambda code, a1, *r: (ev.append(("act", A.get(code, code), a1)), sqlite3.SQLITE_OK)[1])
c.set_trace_callback(lambda s: ev.append(("trace", s)))
W_ = sqlite3.SQLITE_DBCONFIG_WRITABLE_SCHEMA
print("getconfig WRITABLE_SCHEMA before:", c.getconfig(W_), "| DEFENSIVE:", c.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE))
c.setconfig(W_, True)
print("setconfig(WRITABLE_SCHEMA, True) events:", ev, "| getconfig after:", c.getconfig(W_)); ev.clear()
c.execute("DELETE FROM sqlite_master WHERE name='episodes'")
print("DELETE FROM sqlite_master:", sorted({(e[1], e[2]) for e in ev if e[0] == "act"})); ev.clear()
c.setconfig(W_, False)
for sql in ("CREATE INDEX ix ON t(a)", "REINDEX ix", "REINDEX", "ANALYZE"):
    ev.clear(); c.execute(sql); print(f"{sql:24s}", sorted({(e[1], e[2]) for e in ev if e[0] == "act" and e[1] not in ("READ", "SELECT", "FUNCTION")}))
