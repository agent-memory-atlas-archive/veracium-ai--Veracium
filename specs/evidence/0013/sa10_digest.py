#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0013_sa10_gate.py::test_the_comparator_refuses_another_build_and_names_each_section
"""INV-SA10's replay comparator (0013 §5f.1; stage-1 read item 5): a content digest of one closed SQLite file.

usage: python -I sa10_digest.py <store> <sqlite_version> <sqlite_source_id>

Run by sa10_gate.py in a FRESH ISOLATED interpreter (`-I`), so the code under test cannot reach it. The file is
opened read-only (`mode=ro`). The build is ASSERTED, not recorded: the census process passes its own
`sqlite_version()` and `sqlite_source_id()`, and this script refuses (exit 4) when its build differs. Output, on
stdout, one JSON object:
  sections  "schema": every sqlite_schema row's type, name, tbl_name and sql, WITHOUT rootpage (physical placement);
            "table:<name>": every row of every object of type `table`, internal ones included, as (rowid, then each
            column's typeof and value, TEXT read as bytes) ordered by rowid;
            "pragmas": user_version, application_id, schema_version (the cookie), encoding, page_size, auto_vacuum.
  integrity PRAGMA integrity_check's rows (index entries are not in the row digest; a raw write can corrupt an index
            page while every table scan stays equal).
It takes NO normalisation. A table it has no exact rule for (a virtual table, a table without a rowid) is a refusal
(exit 5), never a guess; so is a journal or WAL file left beside the store (exit 3), which a read-only open could not
roll back.
"""
import hashlib
import json
import os
import sqlite3
import sys
import urllib.parse


def _h(obj) -> str:
    return hashlib.sha256(repr(obj).encode("utf-8")).hexdigest()


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def main(argv) -> int:
    if len(argv) != 4:
        print(__doc__.split("\n")[2], file=sys.stderr)
        return 2
    path, want_version, want_source = argv[1:]
    for suffix in ("-journal", "-wal"):
        if os.path.exists(path + suffix) and os.path.getsize(path + suffix) > 0:
            print(f"refused: {path + suffix} is present and not empty")
            return 3
    con = sqlite3.connect(f"file:{urllib.parse.quote(os.path.abspath(path))}?mode=ro", uri=True)
    try:
        version, source = con.execute("SELECT sqlite_version(), sqlite_source_id()").fetchone()
        if (version, source) != (want_version, want_source):
            print(f"refused: this interpreter's SQLite is {version} {source!r}, the census ran "
                  f"{want_version} {want_source!r}")
            return 4
        schema = con.execute("SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name, tbl_name, sql"
                             ).fetchall()
        sections = {"schema": _h(schema)}
        counts = {}
        for typ, name, _tbl, sql in schema:
            if typ != "table":
                continue
            if (sql or "").upper().startswith("CREATE VIRTUAL TABLE"):
                print(f"refused: {name} is a virtual table; no rule for its content was given")
                return 5
            cols = [r[0] for r in con.execute("SELECT name FROM pragma_table_xinfo(?)", (name,))]
            if not cols:                # every table has a column: an empty list means the lookup missed the table
                print(f"refused: no columns read for {name}; its rows would digest as rowids alone")
                return 5
            try:
                probe = con.execute(f"SELECT rowid FROM {_q(name)} LIMIT 0")
                probe.close()
            except sqlite3.OperationalError:
                print(f"refused: {name} has no rowid; no ordering rule for it was given")
                return 5
            if "rowid" in [c.lower() for c in cols]:
                print(f"refused: {name} has a column named rowid; the rowid is not addressable")
                return 5
            sel = ", ".join(f"typeof({_q(c)}), {_q(c)}" for c in cols)
            con.text_factory = bytes
            try:
                rows = con.execute(f"SELECT rowid{', ' + sel if sel else ''} FROM {_q(name)} ORDER BY rowid").fetchall()
            finally:
                con.text_factory = str
            sections[f"table:{name}"] = _h(rows)
            counts[name] = len(rows)
        pragmas = {p: con.execute(f"PRAGMA {p}").fetchone()[0]
                   for p in ("user_version", "application_id", "schema_version", "encoding", "page_size",
                             "auto_vacuum")}
        sections["pragmas"] = _h(sorted(pragmas.items()))
        integrity = [r[0] for r in con.execute("PRAGMA integrity_check")]
    finally:
        con.close()
    print(json.dumps({"sqlite_version": version, "source_id": source, "python": sys.version.split()[0],
                      "sections": sections, "pragmas": pragmas, "counts": counts, "integrity": integrity}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
