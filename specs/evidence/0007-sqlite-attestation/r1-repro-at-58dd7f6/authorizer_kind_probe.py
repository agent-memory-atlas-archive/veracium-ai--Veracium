"""B3 probe (in memory, no tree code but steptable._kind's text copied by AST): does the leading-keyword label miss
writes that SQLite's authorizer reports, and does the authorizer see them? Also: does Python's statement cache
suppress the authorizer on a re-executed statement?"""
import ast, pathlib, re, sqlite3, sys
src = pathlib.Path(sys.argv[1]).read_text()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_kind")
ns = {"re": re}; exec(compile(ast.Module([fn], []), "steptable._kind", "exec"), ns); _kind = ns["_kind"]
ACTIONS = ("CREATE_INDEX CREATE_TABLE CREATE_TEMP_INDEX CREATE_TEMP_TABLE CREATE_TEMP_TRIGGER CREATE_TEMP_VIEW "
           "CREATE_TRIGGER CREATE_VIEW DELETE DROP_INDEX DROP_TABLE DROP_TEMP_INDEX DROP_TEMP_TABLE DROP_TEMP_TRIGGER "
           "DROP_TEMP_VIEW DROP_TRIGGER DROP_VIEW INSERT PRAGMA READ SELECT TRANSACTION UPDATE ATTACH DETACH ALTER_TABLE "
           "REINDEX ANALYZE CREATE_VTABLE DROP_VTABLE FUNCTION SAVEPOINT RECURSIVE").split()
# authorizer ACTION codes only: result codes share the integers (9 is both SQLITE_DELETE and SQLITE_INTERRUPT)
names = {getattr(sqlite3, "SQLITE_" + a): "SQLITE_" + a for a in ACTIONS if hasattr(sqlite3, "SQLITE_" + a)}
assert len(set(names)) == len(names) == len(ACTIONS), (len(names), len(ACTIONS))
READS = {"SQLITE_READ", "SQLITE_SELECT", "SQLITE_FUNCTION", "SQLITE_RECURSIVE"}
def fresh(cache=128):
    c = sqlite3.connect(":memory:", cached_statements=cache, isolation_level=None)
    c.executescript("CREATE TABLE t(a); INSERT INTO t VALUES(1),(2); CREATE TABLE t2(a); CREATE INDEX ix ON t(a);")
    log = []
    c.set_authorizer(lambda code, a1, a2, db, trig: (log.append((names.get(code, code), a1, a2)), sqlite3.SQLITE_OK)[1])
    return c, log
cases = [("comment-prefixed DROP", "execute", "/* repair */ DROP TABLE t"),
         ("CTE DELETE", "execute", "WITH d AS (SELECT 1) DELETE FROM t"),
         ("script led by SELECT", "executescript", "SELECT 1; DROP TABLE t2"),
         ("stamp write", "execute", "PRAGMA user_version = 16"),
         ("stamp read", "execute", "PRAGMA user_version"),
         ("table_info read", "execute", "PRAGMA table_info(t)"),
         ("writable_schema", "execute", "PRAGMA writable_schema=ON"),
         ("ATTACH", "execute", "ATTACH ':memory:' AS x"),
         ("plain CREATE INDEX", "execute", "CREATE INDEX ix2 ON t(a)")]
for label, how, sql in cases:
    c, log = fresh()
    getattr(c, how)(sql)
    acts = sorted({x[0] for x in log})
    prag = [x for x in log if x[0] == "SQLITE_PRAGMA"]
    writes = [a for a in acts if a not in READS]
    print(f"{label:24s} _kind={_kind(sql):5s} authorizer={acts}  non-read={writes}" + (f"  pragma(arg1,arg2)={[(x[1], x[2]) for x in prag]}" if prag else ""))
# statement cache: same text twice
for cache in (128, 0):
    c, log = fresh(cache)
    for _ in range(2):
        log.clear(); c.execute("DELETE FROM t WHERE a = 99"); print(f"cached_statements={cache}: callbacks on this execution = {len(log)}")
print("sqlite", sqlite3.sqlite_version, "python", sys.version.split()[0])
