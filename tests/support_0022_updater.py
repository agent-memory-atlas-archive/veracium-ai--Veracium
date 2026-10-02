"""The ONE definition both 0022 gates use for the one admitted updater of `source_revocations` (0022 §4a as amended by
0041 §11.4, round 10: the append-only rule admits EXACTLY ONE updater, the redaction treatment — 0029 V-APPEND's
precedent). Loaded by path by tests/test_0022_revocation_operation.py and tests/test_spec_gate.py (tests/ is not a
package), so the two gates cannot implement two readings of one rule.

A function is THE UPDATER iff ALL hold (by NAME and by PROPERTY):
  * it is `redact_revocation_reasons` in src/veracium/store/revocation.py;
  * its FIRST statement refuses outside a transaction: `if not <x>.in_transaction: raise …` (an explicit raise —
    an `assert` disappears under `python -O`);
  * every statement it writes to the table is an UPDATE whose SET clause, PARSED, assigns `reason` and nothing else
    (never seq / action / identity_digest / at — the columns the standing state derives from); no INSERT, no DELETE.
Anything else that UPDATEs or DELETEs the table is a violation of the append-only rule.
"""
import ast
import re

UPDATER = ("revocation.py", "redact_revocation_reasons")
_WRITE = re.compile(r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+source_revocations\b", re.I)
_SET = re.compile(r"\bUPDATE\s+source_revocations\s+SET\s+(.*?)\s+WHERE\b", re.I | re.S)


def _set_columns(sql_text):
    m = _SET.search(sql_text)
    if not m:
        return None
    cols = []
    for assign in m.group(1).split(","):
        name = assign.split("=")[0].strip().strip('"`[]')
        cols.append(name.lower())
    return cols


def _guarded(fn):
    if not fn.body:
        return False
    first = fn.body[0]
    if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
        first = fn.body[1] if len(fn.body) > 1 else None          # skip the docstring
    return (isinstance(first, ast.If) and isinstance(first.test, ast.UnaryOp) and isinstance(first.test.op, ast.Not)
            and isinstance(first.test.operand, ast.Attribute) and first.test.operand.attr == "in_transaction"
            and len(first.body) == 1 and isinstance(first.body[0], ast.Raise))


def classify(files):
    """`files`: {relative path: source text}. Returns (writers, updater_ok, violations).
    writers: [(path, fn name, lineno, body text)] for every function writing the table (any kind of write);
    updater_ok: the set of (path, fn name) that are THE updater and satisfy every property;
    violations: human-readable refusals."""
    writers, updater_ok, violations = [], set(), []
    for path, text in files.items():
        if "source_revocations" not in text:
            continue
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = ast.get_source_segment(text, node) or ""
            kinds = [m.group(1).split()[0].upper() for m in _WRITE.finditer(body)]
            if not kinds:
                continue
            writers.append((path, node.name, node.lineno, body))
            is_named = path.endswith(UPDATER[0]) and node.name == UPDATER[1]
            if "UPDATE" in kinds or "DELETE" in kinds:
                if not is_named:
                    violations.append(f"{path}:{node.lineno} `{node.name}` UPDATEs/DELETEs source_revocations and is not "
                                      f"the one admitted updater (0022 §4a as amended)")
                    continue
                problems = []
                if set(kinds) != {"UPDATE"}:
                    problems.append(f"writes {sorted(set(kinds))}, not UPDATE alone")
                cols = _set_columns(body)
                if cols != ["reason"]:
                    problems.append(f"SET assigns {cols}, not `reason` alone")
                if not _guarded(node):
                    problems.append("its first statement does not refuse outside a transaction")
                if problems:
                    violations.append(f"{path}:{node.lineno} `{node.name}`: " + "; ".join(problems))
                else:
                    updater_ok.add((path, node.name))
    return writers, updater_ok, violations
