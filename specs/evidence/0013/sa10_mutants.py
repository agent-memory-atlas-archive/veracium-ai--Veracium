#!/usr/bin/env python3
# Mutation-Matrix: tests/test_0013_sa10_mutants.py::test_the_table_check_refuses_each_tampered_table
"""INV-SA10 — the gate's mutation table (0013 §5f.1; 0007 I2): each negative cell red against the gate mutant §5f.1
names beside it, and the gate's own checks each red against the mutant that removes them.

Three kinds of mutant, one protocol:
  GATE     an edit to the gate (sa10_gate.py) or its comparator (sa10_digest.py) that reintroduces the weaker design
           §5f.1's table names in its "gate mutant it kills" column (N1–N15), or removes one of the gate's own
           checks (I1's campaign, kept here so it is reproducible);
  TREE     an edit to the ladder (src/veracium/store/migration.py, release_migration.py) that INV-SA10's mutation row
           names: a write that maps to no step, the same write behind a condition no fixture satisfies, DDL from a
           site not declared to issue it, and a write added to a release_migration function (stage-1 decision 5);
  CONTROL  an unrelated TypeError, which the shared classifier must read UNCLASSIFIED, never KILLED.

The protocol is pa1_campaign.py's part (B), on a copy of the tracked tree (TMPDIR=/dev/shm recommended):
  CLEAN    every named cell and every honest probe passes on the unmutated copy, FIRST and again LAST (a campaign whose
           controls fail at either end measured nothing);
  per mutant: every anchor occurs EXACTLY ONCE in its file and the bytes change; the gate and the ladder still import
           from the copy; its HONEST probes pass (a kill only because the clean path broke is vacuous); its NAMED cells
           run under pytest with a JUnit record, each failing cell classified by specs/evidence/mutation_kinds.py;
           KILLED iff the classifier says so AND every named cell failed AND, where the row declares a REASON, that
           text is in a named cell's failure (a clean-ladder cell fails on ANY problem, so its kill is pinned to the
           problem the mutant must cause); the file is restored byte-identically.
`--check` is FAST and re-runs nothing: definitions, anchors, digests, the named cells' existence, every row good.
    $PY specs/evidence/0013/sa10_mutants.py --check
    TMPDIR=/dev/shm $PY specs/evidence/0013/sa10_mutants.py --write
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TABLE = HERE / "sa10" / "mutation-table.json"     # the name tests/test_closure_mutants.py finds
SELF = "specs/evidence/0013/sa10_mutants.py"
GATE = "specs/evidence/0013/sa10_gate.py"
DIGEST = "specs/evidence/0013/sa10_digest.py"
MIGRATION = "src/veracium/store/migration.py"
RELEASE = "src/veracium/store/release_migration.py"
CELLS_FILE = "tests/test_0013_sa10_gate.py"
KINDS = "specs/evidence/mutation_kinds.py"
DIGESTED = (GATE, DIGEST, MIGRATION, RELEASE, "src/veracium/store/schema_version.py",
            "specs/evidence/0013/pa1_campaign.py", "specs/evidence/0013/steptable.py", CELLS_FILE, KINDS, SELF)
SUBJECT = "INV-SA10"


def _load_kinds():
    spec = importlib.util.spec_from_file_location("veracium_mutation_kinds", HERE.parent / "mutation_kinds.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


MK = _load_kinds()


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


C = lambda name: f"{CELLS_FILE}::{name}"                                     # noqa: E731
HARNESS = C("test_the_control_harness_is_green_without_a_channel[allowlist]")
ROUTE = lambda r: C(f"test_the_proxy_refuses_each_route_and_records_the_refusal[{r}]")           # noqa: E731
RULE = lambda i: C(f"test_each_classification_rule_refuses_its_case_and_admits_its_legitimate_one[{i}]")  # noqa: E731
FWD = lambda n: C(f"test_replay_equivalence_catches_each_unrecorded_route_with_the_allowlist_removed[{n}]")  # noqa: E731
ALW = lambda n: C(f"test_the_allowlist_refuses_each_connection_route_and_replay_still_sees_the_file_routes[{n}]")  # noqa: E731
N1315 = lambda n: C(f"test_n13_n15_a_zero_callback_channel_at_a_declared_site_is_refused[{n}]")  # noqa: E731
COMPARATOR = C("test_the_comparator_refuses_another_build_and_names_each_section")
PARAMS = C("test_parameters_are_recorded_by_value_and_replay_compares_every_outcome")
CLEAN_GATE = C("test_the_gate_passes_the_clean_ladder_on_every_path_and_entry")
RELEASE_SEAM = C("test_release_migration_opens_its_connections_through_the_seam")

_STAMP_REFUSE = ('        _refuse_unless(base, STEP_STAMP, [f"user_version reads {stamped}, not {SCHEMA_VERSION}"]\n'
                 '                       if stamped != SCHEMA_VERSION else [])\n')
_NO_OP_WRITE = '        conn.execute("UPDATE episodes SET json = json")\n'

# (id, kind, file, [(anchor, replacement)], named cells (EVERY one must fail), honest probes, reason or None, what)
MUTANTS = [
    # ---- the N-table's gate mutants (§5f.1; N13–N15 from stage-1 item 4) ------------------------------------------
    ("N1-site-admits-schema-writes", "gate", GATE,
     [("        if tc is None:\n            problems.append(f\"{where}: a schema write that is not class (a) or (b) by "
       "its text\")\n            cls = \"OUTSIDE\"\n        else:\n            cls = tc\n",
       "        if tc is None and not (rec.site is not None and (rec.site[0], rec.site[1]) in DDL_SITES):\n"
       "            problems.append(f\"{where}: a schema write that is not class (a) or (b) by its text\")\n"
       "            cls = \"OUTSIDE\"\n        else:\n            cls = tc or \"b1\"\n")],
     [C("test_n1_the_reviewers_drop_and_recreate_at_a_declared_site_is_refused"),
      C("test_n3_dropping_and_recreating_the_op_key_unique_index_is_refused_on_the_drop")], [HARNESS], None,
     "N1: class (b) decided by the site: every schema write at a declared site is admitted"),
    ("N2-b1-by-prefix", "gate", GATE,
     [('    return "a" if sql in alters else "b1" if sql in b1 else "b2" if sql in b2 else None',
       '    return "a" if sql in alters else "b1" if sql in b1 or (sql or "").startswith(("CREATE TABLE ", '
       '"CREATE INDEX ", "CREATE UNIQUE INDEX ")) else "b2" if sql in b2 else None')],
     [C("test_n2_a_count_preserving_rebuild_is_refused_statement_by_statement")], [HARNESS], None,
     "N2: (b1) matched by its prefix, not byte-equality to a head constructor"),
    ("N3-b2-every-index", "gate", GATE,
     [('    b2 = {f"DROP INDEX IF EXISTS {o.key[1]}" for o in head if o.key[0] == "index" and o.policy == '
       'sv.REBUILDABLE}', '    b2 = {f"DROP INDEX IF EXISTS {o.key[1]}" for o in head if o.key[0] == "index"}')],
     [C("test_n3_dropping_and_recreating_the_op_key_unique_index_is_refused_on_the_drop")], [HARNESS], None,
     "N3: (b2) widened from the rebuildable indexes to every index"),
    ("N4-N8-executescript-by-first-statement", "gate", GATE,
     [('               "close": lambda: census.call(cid, "close", None, None, real.close)}',
       '               "close": lambda: census.call(cid, "close", None, None, real.close),\n'
       '               "executescript": lambda script: census.call(cid, "execute", script.split(";")[0].strip(), (),\n'
       '                                                            lambda: real.executescript(script))}')],
     [C("test_n4_n8_a_script_on_the_ladders_connection_is_refused_outright[N4]"),
      C("test_n4_n8_a_script_on_the_ladders_connection_is_refused_outright[N8]"),
      ROUTE("connection.executescript")], [HARNESS], None,
     "N4/N8: executescript allowed, the script classified by its first statement"),
    ("N5-N10-constructor-assertion-dropped", "gate", GATE,
     [('    problems += [f"head constructor: {p}" for p in constructor_problems()]\n', "")],
     [C("test_n5_n10_a_head_constructor_that_is_not_a_plain_create_fails_the_gate[N5]"),
      C("test_n5_n10_a_head_constructor_that_is_not_a_plain_create_fails_the_gate[N10]")], [HARNESS], None,
     "N5/N10: the gate no longer asserts its head constructors are plain creates"),
    ("N6-N7-leading-keyword", "gate", GATE,
     [("    by_class = collections.defaultdict(list)\n",
       '    if label(rec.sql) == "READ":\n        return "read", problems\n'
       "    by_class = collections.defaultdict(list)\n")],
     [C("test_n6_a_comment_prefixed_drop_is_classified_by_its_actions"),
      C("test_n7_a_cte_prefixed_delete_at_no_step_is_refused")], [HARNESS], None,
     "N6/N7: a statement the prefix label calls a read is classified as a read"),
    ("N7-complement-over-labelled-DML", "gate", GATE,
     [("    if rows:\n", '    if rows and lab == "DML":\n')],
     [C("test_n7_a_cte_prefixed_delete_at_no_step_is_refused")], [HARNESS], None,
     "N7: the write complement runs over labelled DML only"),
    ("N9-every-pragma-reads", "gate", GATE,
     [("        if PRAGMA_READS.get(name) != shape or shape is None:\n", "        if False:\n")],
     [C("test_n9_writable_schema_at_a_declared_site_is_off_the_pragma_vocabulary"), RULE(8)], [HARNESS], None,
     "N9: every pragma other than the stamp is a read"),
    ("N11-orphans-skipped", "gate", GATE,
     [('    problems += [f"orphan {k} on connection {cid}: {str(x)[:100]}" for k, cid, x in census.orphans]\n', "")],
     [C("test_n11_a_statement_around_the_proxy_is_an_orphan")], [HARNESS], None,
     "N11: the orphan check skipped"),
    ("N12-schema-table-write-reads", "gate", GATE,
     [("    if book and not schema:\n", "    if False:\n")],
     [C("test_n12_setconfig_writable_schema_then_a_schema_table_delete_is_refused_twice_over"), RULE(6)], [HARNESS],
     None, "N12: a write to sqlite_master alone is classified as a read"),
    ("N12-getconfig-dropped", "gate", GATE,
     [("        if ws:\n", "        if False:\n")],
     [C("test_n12_setconfig_writable_schema_then_a_schema_table_delete_is_refused_twice_over"),
      C("test_the_configuration_guard_sees_setconfig_which_no_statement_shows")], [HARNESS], None,
     "N12: the getconfig assertion after every call dropped"),
    ("N13-N15-forward-unknown-attributes", "gate", GATE,
     [('            raise census.refuse(f"connection.{n}")', "            return getattr(real, n)")],
     [N1315("N13 blobopen"), N1315("N14 backup into the connection"),
      N1315("N15 set_authorizer(None), then DELETE"), ROUTE("connection.blobopen"), ROUTE("connection.backup"),
      ROUTE("connection.set_authorizer")], [HARNESS], None,
     "N13–N15: the connection proxy forwards every name it does not list to the real connection"),
    ("W3-allowlist-in-getattr", "gate", GATE,
     [("        __slots__ = ()\n\n        def __getattribute__(self, n):\n            f = methods.get(n)",
       "        def __getattr__(self, n):\n            f = methods.get(n)"),
      ("    return ConnectionProxy()\n",
       "    proxy = ConnectionProxy()\n    object.__setattr__(proxy, \"_real\", real)\n    return proxy\n")],
     [ROUTE("connection._real"), ROUTE("connection.__dict__")], [HARNESS], None,
     "stage-1 4(g): the superseded shape, the allowlist in __getattr__ with the real connection an instance "
     "attribute, so a name the object HAS (`_real`, `__dict__`) never reaches the allowlist"),
    ("W3-setattr-forwards", "gate", GATE,
     [("            if n not in CONN_SET_ATTRS:\n                raise census.refuse(f\"setting connection.{n}\")",
       "            if False:\n                raise census.refuse(f\"setting connection.{n}\")")],
     [ROUTE("setting connection._real"), ROUTE("setting connection.autocommit")], [HARNESS], None,
     "the proxy's __setattr__ forwards every name to the real connection: setting `_real` or `autocommit` is admitted"),
    ("enter-returns-real", "gate", GATE,
     [("        def __enter__(self):\n            return self", "        def __enter__(self):\n            return real")],
     [ROUTE("connection.blobopen (through with)")], [HARNESS], None,
     "stage-1 4(f): `with conn as c` binds the real connection"),
    ("execute-returns-real-cursor", "gate", GATE,
     [("        return cursor_proxy(cur, census, census.events[-1])\n\n    def executemany",
       "        return cur\n\n    def executemany")],
     [ROUTE("cursor.connection"), C("test_execute_hands_back_the_cursor_wrapper_never_the_real_cursor")], [HARNESS],
     None, "stage-1 4(f): execute returns the real cursor, whose .connection is the real connection"),
    ("cursor-iter-returns-real", "gate", GATE,
     [("        def __iter__(self):\n            return self", "        def __iter__(self):\n            return iter(cur)")],
     [ROUTE("cursor.connection (through iter)")], [HARNESS], None,
     "stage-1 4(f) note: iter() of the cursor wrapper is the real cursor"),
    # ---- the gate's own checks (I1's campaign) -------------------------------------------------------------------
    ("digest-rowid-only", "gate", DIGEST,
     [('            cols = [r[0] for r in con.execute("SELECT name FROM pragma_table_xinfo(?)", (name,))]\n'
       "            if not cols:",
       '            cols = [r[1] for r in con.execute(f"SELECT * FROM pragma_table_xinfo({_q(name)!r})")]\n'
       "            if False:")],
     [COMPARATOR], [HARNESS], None, "the comparator's column lookup misses every table: rows digest as rowids"),
    ("digest-no-typeof", "gate", DIGEST,
     [('sel = ", ".join(f"typeof({_q(c)}), {_q(c)}" for c in cols)', 'sel = ", ".join(f"{_q(c)}" for c in cols)')],
     [COMPARATOR], [HARNESS], None, "the comparator digests values without their storage class"),
    ("digest-rootpage", "gate", DIGEST,
     [('        sections = {"schema": _h(schema)}',
       '        sections = {"schema": _h(schema + con.execute("SELECT rootpage FROM sqlite_schema ORDER BY type, name, '
       'tbl_name, sql").fetchall())}')],
     [COMPARATOR], [HARNESS], None, "the comparator digests physical placement (rootpage) with the schema rows"),
    ("digest-build-unasserted", "gate", DIGEST,
     [("        if (version, source) != (want_version, want_source):", "        if False:")],
     [COMPARATOR], [HARNESS], None, "the comparator does not assert the census's SQLite build"),
    ("integrity-unasserted", "gate", GATE,
     [('    if real["integrity"] != ["ok"]:', "    if False:")],
     [FWD("raw file I/O corrupting only an index page"), ALW("raw file I/O corrupting only an index page")],
     [HARNESS], None, "integrity_check on the census file is not asserted"),
    ("replay-replays-nothing", "gate", GATE,
     [('    for ev in events:\n        if ev.kind == "connect-failed":',
       '    for ev in []:\n        if ev.kind == "connect-failed":')],
     [PARAMS], [ROUTE("connection.blobopen")], None, "replay re-runs nothing"),
    ("replay-ignores-outcomes", "gate", GATE,
     [("        if out != ev.outcome:", "        if False:")],
     [PARAMS], [HARNESS], None, "replay does not compare each call's outcome"),
    ("params-by-reference", "gate", GATE,
     [("        out = tuple(params)", "        out = params")],
     [PARAMS], [HARNESS], None, "parameters recorded by reference: a later mutation reaches the replay"),
    ("heartbeat-off", "gate", GATE,
     [('    if rec.outcome == ("ok",):\n        if not rec.traces:', '    if False:\n        if not rec.traces:')],
     [C("test_the_heartbeat_refuses_a_call_that_ran_with_the_instrument_removed"),
      FWD("set_authorizer(None), then a DELETE through execute")], [HARNESS], None,
     "a call that ran untraced and unauthorized is not refused"),
    ("type-check-off", "gate", GATE,
     [("        if isinstance(value, _FORBIDDEN_RETURN):\n            raise", "        if False:\n            raise")],
     [C("test_no_allowed_name_hands_back_a_real_connection_cursor_or_blob")], [HARNESS], None,
     "an allowed name may hand back a real Connection, Cursor or Blob"),
    ("site-coverage-blind", "gate", GATE,
     [("            if not any(lo <= ln <= hi for ln in lines):", "            if False:")],
     [C("test_site_coverage_reports_an_unobserved_site_in_a_function_the_census_entered")], [HARNESS], None,
     "site coverage reports no unobserved site"),
    ("cross-connection-callbacks-admitted", "gate", GATE,
     [('            if cur is None or cur.cid != cid:\n                self.orphans.append(("auth"',
       '            if cur is None:\n                self.orphans.append(("auth"')],
     [C("test_an_orphan_callback_and_a_cross_connection_callback_are_refusals")], [HARNESS], None,
     "an authorizer callback from another connection is attributed to the current call"),
    ("unknown-code-reads", "gate", GATE,
     [('cls = CODE_CLASS.get(a[0], "unknown")', 'cls = CODE_CLASS.get(a[0], "read")')],
     [C("test_the_action_table_is_a_closed_partition_of_the_33_codes_and_any_other_code_refuses")], [HARNESS], None,
     "an action code outside the closed table reads as a read"),
    ("c2-c3-not-required", "gate", GATE,
     [('        if c2 is None or c2["b2_with_drop_index"] < 1:', "        if False:")],
     [C("test_a_narrowed_path_set_refuses_loudly")], [HARNESS], None,
     "a gate run with no real (b2) observed passes"),
    ("stamp-value-unchecked", "gate", GATE,
     [("            if arg != str(head):", "            if False:")],
     [RULE(13)], [HARNESS], None, "a stamp below the head is admitted"),
    ("ddl-site-ignored", "gate", GATE,
     [("        if rec.site is None or (rec.site[0], rec.site[1]) not in DDL_SITES:", "        if False:")],
     [RULE(2)], [HARNESS], None, "a schema write from an undeclared site is admitted"),
    ("seam-skips-release-migration", "gate", GATE,
     [("    mig.sqlite3 = rm.sqlite3 = seam", "    mig.sqlite3 = seam")],
     [RELEASE_SEAM], [HARNESS], None, "release_migration's own connections bypass the seam"),
    ("exact-one-relaxed", "gate", GATE,
     [("        if len(hits) != 1:", "        if not hits:")],
     [C("test_a_row_write_two_steps_both_claim_is_refused")], [HARNESS], None,
     "a row write two steps' matchers both claim is admitted (exact-one ownership)"),
    ("per-call-trace-count", "gate", GATE,
     [("        if not rec.traces:\n",
       "        if len(rec.traces) > 1:\n            problems.append(f\"{where}: the call traced more than once\")\n"
       "        if not rec.traces:\n")],
     [C("test_the_clean_control_admits_a_call_whose_nested_pragma_traces_twice")], [ROUTE("connection.blobopen")],
     "the call traced more than once", "§5f.1 rule 3: a per-call trace count refuses the nested table-valued pragma"),
    # ---- tree mutants: the ladder (INV-SA10's mutation row; stage-1 decision 5) ----------------------------------
    ("tree-unmapped-write", "tree", MIGRATION,
     [(_STAMP_REFUSE, _STAMP_REFUSE + _NO_OP_WRITE)],
     [HARNESS], [ROUTE("connection.blobopen")], "a row write on ['episodes'] maps to 0 steps",
     "a ladder write that maps to no step, after the stamp postcondition"),
    ("tree-unreached-write", "tree", MIGRATION,
     [(_STAMP_REFUSE, _STAMP_REFUSE + "        if base == -1:\n    " + _NO_OP_WRITE)],
     [CLEAN_GATE], [HARNESS], "site never observed on any path: veracium/store/migration.py:_apply_forward:",
     "the same write behind a condition no fixture satisfies (dev's mutant2-conditional): the site check alone"),
    ("tree-undeclared-ddl", "tree", MIGRATION,
     [('    conn.execute("DELETE FROM wiki")\n',
       '    conn.execute("DROP INDEX IF EXISTS ix_episodes_user")\n'
       '    conn.execute("CREATE INDEX ix_episodes_user ON episodes(user_id, date)")\n'
       '    conn.execute("DELETE FROM wiki")\n')],
     [HARNESS], [ROUTE("connection.blobopen")], "a schema write from a site not declared to issue DDL",
     "(b2) and (b1) texts issued from _drop_wiki_cache, a site not declared to issue DDL"),
    ("tree-release-migration-write", "tree", RELEASE,
     [('            found = conn.execute("PRAGMA user_version").fetchone()[0]\n',
       '            found = conn.execute("PRAGMA user_version").fetchone()[0]\n'
       '            conn.execute("UPDATE episodes SET json = json")\n')],
     [RELEASE_SEAM], [HARNESS], "veracium/store/release_migration.py:_observe:",
     "a write added to release_migration's _observe, inside its BEGIN IMMEDIATE ... ROLLBACK"),
]

# (id, file, [(anchor, replacement)], named cells, what, the outcome the classifier must give)
CONTROLS = [
    ("CTRL-unrelated-TypeError", GATE,
     [("def text_classes():\n", "def text_classes():\n"
       '    raise TypeError("an unrelated execution failure (classifier negative control)")\n')],
     [C("test_n1_the_reviewers_drop_and_recreate_at_a_declared_site_is_refused"), HARNESS],
     "an UNRELATED TypeError in the gate's text classes: every path raises for no reason a cell names",
     "UNCLASSIFIED"),
]


def named_cells() -> list:
    return sorted({n for m in MUTANTS for n in m[4]} | {n for k in CONTROLS for n in k[3]})


def honest_nodes() -> list:
    return sorted({n for m in MUTANTS for n in m[5]})


def definition_sha(m) -> str:
    return hashlib.sha256(json.dumps(list(m), ensure_ascii=True).encode()).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _digests(root: pathlib.Path) -> dict:
    return {f: _sha(root / f) for f in DIGESTED}


def _snapshot(dst: pathlib.Path):
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                       capture_output=True, check=True)
    for f in filter(None, r.stdout.decode().split("\0")):
        src = ROOT / f
        if src.is_file():
            (dst / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / f)


def _env(root):
    return {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONDONTWRITEBYTECODE": "1"}


def _imports(root) -> str:
    code = ("import importlib, importlib.util, pathlib, sys\nroot = pathlib.Path(sys.argv[1]).resolve()\n"
            "for name in ('veracium.store.migration', 'veracium.store.release_migration'):\n"
            "    m = importlib.import_module(name)\n"
            "    assert pathlib.Path(m.__file__).resolve().is_relative_to(root / 'src'), m.__file__\n"
            "for stem in ('sa10_gate',):\n"
            "    s = importlib.util.spec_from_file_location(stem, root / 'specs/evidence/0013' / (stem + '.py'))\n"
            "    s.loader.exec_module(importlib.util.module_from_spec(s))\n")
    r = subprocess.run([sys.executable, "-B", "-c", code, str(root)], cwd=root, env=_env(root),
                       capture_output=True, text=True)
    return "ok" if r.returncode == 0 else "error: " + (r.stderr.strip().splitlines() or ["?"])[-1][:200]


def _pytest(root, nodes) -> dict:
    with tempfile.TemporaryDirectory() as d:
        xml = pathlib.Path(d) / "j.xml"
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:randomly", "-p", "no:cacheprovider",
                            f"--junitxml={xml}", *nodes], cwd=root, env=_env(root), capture_output=True, text=True)
        failed, errored, passed, kinds, texts = [], [], [], {}, {}
        if xml.exists():
            for tc in ET.parse(xml).iter("testcase"):
                node = f"{CELLS_FILE}::{tc.get('name')}"
                f = tc.find("failure")
                if f is not None:
                    failed.append(node)
                    kinds[node] = MK.failure_kind(f.get("message") or "")
                    texts[node] = (f.get("message") or "") + "\n" + (f.text or "")
                elif tc.find("error") is not None:
                    errored.append(node)
                elif tc.find("skipped") is None:
                    passed.append(node)
        summary = (r.stdout.strip().splitlines() or [""])[-1][:160]
    return {"exit": r.returncode, "passed": sorted(passed), "failed": sorted(failed), "errored": sorted(errored),
            "kinds": dict(sorted(kinds.items())), "texts": texts, "summary": summary}


def _apply(root, rel, edits) -> tuple:
    target = root / rel
    original = target.read_bytes()
    text = original.decode()
    counts = [text.count(a) for a, _ in edits]
    if counts != [1] * len(edits):
        return original, counts, False
    for a, r in edits:
        text = text.replace(a, r)
    if text.encode() == original:
        return original, counts, False
    target.write_text(text)
    return original, counts, True


def _clean(root, nodes) -> dict:
    imp = _imports(root)
    run = _pytest(root, nodes)
    ok = imp == "ok" and run["exit"] == 0 and not run["failed"] and not run["errored"] and run["passed"] == sorted(nodes)
    return {"import": imp, "passed": len(run["passed"]), "of": len(nodes), "ok": ok,
            "failed": run["failed"], "errored": run["errored"], "summary": run["summary"]}


def run_one(root: pathlib.Path, m) -> dict:
    mid, kind, rel, edits, cells, honest, reason, what = m
    row = {"id": mid, "finding": SUBJECT, "kind": kind, "file": rel, "what": what, "named_cells": list(cells),
           "honest_nodes": list(honest), "reason": reason, "definition_sha256": definition_sha(m)}
    original, counts, ok = _apply(root, rel, edits)
    row["anchor_counts"] = counts
    if not ok:
        return {**row, "outcome": "ANCHOR", "good": False}
    try:
        row["import"] = _imports(root)
        h = _pytest(root, list(honest)) if honest else None
        row["honest"] = ("n/a" if h is None else "pass" if h["exit"] == 0 and h["passed"] == sorted(honest)
                         else f"fail: {len(h['failed'])} failed, {len(h['errored'])} errored of {len(honest)}")
        c = _pytest(root, list(cells))
    finally:
        (root / rel).write_bytes(original)
    assert _sha(root / rel) == hashlib.sha256(original).hexdigest()
    row.update(MK.classify(c["kinds"], c["failed"], c["errored"]))
    row["named_failed"] = all(n in c["failed"] for n in cells)
    row["reason_seen"] = None if reason is None else any(reason in c["texts"].get(n, "") for n in cells)
    row["pytest"] = c["summary"]
    row["good"] = (row["import"] == "ok" and row["honest"] in ("pass", "n/a") and row["outcome"] == "KILLED"
                   and row["named_failed"] and row["reason_seen"] in (None, True))
    return row


def run_control(root: pathlib.Path, ctl) -> dict:
    cid, rel, edits, cells, what, expected = ctl
    row = {"id": cid, "file": rel, "what": what, "expected": expected, "named_cells": list(cells),
           "definition_sha256": definition_sha(ctl)}
    original, counts, ok = _apply(root, rel, edits)
    row["anchor_counts"] = counts
    if not ok:
        return {**row, "outcome": "ANCHOR", "good": False}
    try:
        row["import"] = _imports(root)
        c = _pytest(root, list(cells))
    finally:
        (root / rel).write_bytes(original)
    row.update(MK.classify(c["kinds"], c["failed"], c["errored"]))
    row["good"] = row["import"] == "ok" and row["outcome"] == expected and bool(row["cells_failed"])
    return row


def campaign() -> dict:
    t0 = time.time()
    nodes = sorted(set(named_cells()) | set(honest_nodes()))
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        _snapshot(root)
        digests = _digests(root)               # the bytes measured, never the live tree's at write time
        first = _clean(root, nodes)
        if not first["ok"]:
            raise SystemExit(f"CLEAN (first) failed — no mutant is meaningful on a tree whose cells fail: {first}")
        rows = []
        for m in MUTANTS:
            rows.append(run_one(root, m))
            r = rows[-1]
            print(f"  {r['id']:42s} {r.get('outcome', ''):12s} good={r['good']} import={r.get('import')} "
                  f"honest={r.get('honest')} named_failed={r.get('named_failed')} reason={r.get('reason_seen')} "
                  f"kinds={sorted(set(r.get('cell_kinds', {}).values()))}", flush=True)
        controls = [run_control(root, k) for k in CONTROLS]
        last = _clean(root, nodes)
        if not last["ok"]:
            raise SystemExit(f"CLEAN (last) failed — the copy changed under the campaign: {last}")
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.split("\n")
    body = {
        "header": {"spec": "0013", "finding": SUBJECT, "commit": head,
                   "tracked_changes": sorted(ln[3:] for ln in dirty if ln.strip()),
                   "python": platform.python_version(), "platform": platform.platform(),
                   "sqlite": sqlite3.sqlite_version, "digests": digests,
                   "definitions": {m[0]: definition_sha(m) for m in MUTANTS},
                   "control_definitions": {k[0]: definition_sha(k) for k in CONTROLS},
                   "cells": {SUBJECT: named_cells()}, "honest_nodes": honest_nodes(),
                   "clean": {"first": {k: v for k, v in first.items() if k in ("passed", "of", "ok")},
                             "last": {k: v for k, v in last.items() if k in ("passed", "of", "ok")}}},
        "rows": rows,
        "controls": controls,
        "summary": {"rows": len(rows), "by_kind": {k: sum(r["kind"] == k for r in rows) for k in ("gate", "tree")},
                    "killed": sum(r.get("outcome") == "KILLED" for r in rows), "good": sum(r["good"] for r in rows),
                    "controls": len(controls), "controls_good": sum(k["good"] for k in controls),
                    "seconds": round(time.time() - t0)},
    }
    return {**body, "body_sha256": hashlib.sha256(canonical(body)).hexdigest()}


def render(table: dict) -> str:
    return json.dumps(table, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def defined_tests(root: pathlib.Path = ROOT) -> set:
    tree = ast.parse((root / CELLS_FILE).read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}


def problems(path: pathlib.Path = TABLE, root: pathlib.Path = ROOT) -> list:
    if not path.exists():
        return [f"{path.name} does not exist — run --write"]
    try:
        t = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
    except ValueError as e:
        return [f"{path.name} is not JSON, or carries a duplicate key: {e}"]
    out = []
    body = {k: v for k, v in t.items() if k != "body_sha256"}
    if hashlib.sha256(canonical(body)).hexdigest() != t.get("body_sha256"):
        out.append("the table does not match its own body digest (edited after writing)")
    h = t.get("header", {})
    if h.get("spec") != "0013" or h.get("finding") != SUBJECT:
        out.append(f"the table declares {h.get('spec')!r}/{h.get('finding')!r}, not 0013/{SUBJECT}")
    if h.get("definitions") != {m[0]: definition_sha(m) for m in MUTANTS}:
        out.append("the mutant definitions differ from the runner's — run --write")
    if h.get("control_definitions") != {k[0]: definition_sha(k) for k in CONTROLS}:
        out.append("the control definitions differ from the runner's — run --write")
    if h.get("cells") != {SUBJECT: named_cells()} or h.get("honest_nodes") != honest_nodes():
        out.append("the named cells or honest probes differ from the runner's — run --write")
    clean = h.get("clean", {})
    if not (clean.get("first", {}).get("ok") is True and clean.get("last", {}).get("ok") is True):
        out.append(f"the clean runs are not both green: {clean}")
    live = _digests(root)
    stale = sorted(f for f in set(live) | set(h.get("digests", {})) if live.get(f) != h.get("digests", {}).get(f))
    if stale:
        out.append(f"stale: {stale} — run --write")
    for m in list(MUTANTS) + [(k[0], None, k[1], k[2]) for k in CONTROLS]:
        text = (root / m[2]).read_text(encoding="utf-8")
        for a, _r in m[3]:
            if text.count(a) != 1:
                out.append(f"{m[0]}: an anchor occurs {text.count(a)} time(s) in {m[2]}")
    tests = defined_tests(root)
    for n in sorted(set(named_cells()) | set(honest_nodes())):
        if n.split("::")[1].split("[")[0] not in tests:
            out.append(f"{n} is not a test in {CELLS_FILE}")
    rows = t.get("rows", [])
    if [r.get("id") for r in rows] != [m[0] for m in MUTANTS]:
        out.append("the rows are not one per mutant, in order")
    for r in rows:
        recount = MK.classify(r.get("cell_kinds") or {}, r.get("cells_failed") or [], r.get("cells_errored") or [])
        named = all(n in (r.get("cells_failed") or []) for n in r.get("named_cells") or ["<none>"])
        if not (r.get("outcome") == "KILLED" == recount["outcome"] and r.get("kill_kind") == recount["kill_kind"]
                and r.get("import") == "ok" and r.get("honest") in ("pass", "n/a") and r.get("good") is True
                and named and r.get("named_failed") is True and r.get("reason_seen") in (None, True)
                and (r.get("reason") is None) == (r.get("reason_seen") is None) and not r.get("cells_errored")):
            out.append(f"{r.get('id')}: not a good row (outcome {r.get('outcome')}, recounted {recount['outcome']}, "
                       f"import {r.get('import')}, honest {r.get('honest')}, every named cell failed {named}, "
                       f"reason seen {r.get('reason_seen')})")
    ctls = t.get("controls", [])
    if [k.get("id") for k in ctls] != [k[0] for k in CONTROLS]:
        out.append("the controls are not one per CONTROLS entry, in order")
    for k in ctls:
        recount = MK.classify(k.get("cell_kinds") or {}, k.get("cells_failed") or [], k.get("cells_errored") or [])
        if not (k.get("good") is True and k.get("outcome") == k.get("expected") == recount["outcome"] != "KILLED"):
            out.append(f"{k.get('id')}: the classifier's negative control is not good (outcome {k.get('outcome')}, "
                       f"recounted {recount['outcome']}, expected {k.get('expected')})")
    return out


def main() -> int:
    if "--try" in sys.argv:                     # a development aid: the named mutants on a copy, nothing written
        ids = sys.argv[sys.argv.index("--try") + 1:]
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            _snapshot(root)
            for m in [m for m in MUTANTS if m[0] in ids] + [k for k in CONTROLS if k[0] in ids]:
                r = run_one(root, m) if len(m) == 8 else run_control(root, m)
                print(json.dumps({k: r.get(k) for k in ("id", "outcome", "good", "import", "honest", "named_failed",
                                                        "reason_seen", "cell_kinds", "pytest")}), flush=True)
        return 0
    if "--write" in sys.argv:
        t = campaign()
        TABLE.parent.mkdir(exist_ok=True)
        TABLE.write_text(render(t), encoding="utf-8")
        print(f"wrote {TABLE.relative_to(ROOT)}: {json.dumps(t['summary'])} (body_sha256 {t['body_sha256']})")
        for k in t["controls"]:
            print(f"  {k['id']:42s} {k.get('outcome', ''):12s} good={k['good']}")
        bad = problems()
        for b in bad:
            print(f"PROBLEM: {b}")
        return 0 if not bad else 1
    bad = problems()
    for b in bad:
        print(f"STALE: {b}")
    if not bad:
        t = json.loads(TABLE.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)
        print(f"{TABLE.relative_to(ROOT)} current: {json.dumps(t['summary'])} (body_sha256 {t['body_sha256']})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
