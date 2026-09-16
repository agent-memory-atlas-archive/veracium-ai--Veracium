#!/usr/bin/env python3
"""0041 — the mutant campaign over the transition table's rewritten strict xfails.

Round 5, finding 3: an outside reviewer satisfied three of our strict xfails with
stubs. Three found from outside means the population at risk was every xfail, not
those three, so this runs the campaign ourselves and keeps it runnable.

TWO HALVES, and the second is the one the old bodies could never have passed.

  NEGATIVE CONTROLS — each wrong implementation must make the test FAIL.
  A check that no stub can satisfy is only half a check.

  THE POSITIVE CONTROL — a CORRECT implementation must make the test PASS.
  Without it a test can be unfalsifiable in the other direction: the old
  after-attestation body asserted a refusal for a write that succeeds today, so
  it would have gone on xfailing through any implementation whatsoever and could
  never have announced the landing it was written to announce. That defect is
  invisible to every negative control and is caught only by trying to make the
  test green on purpose.

Nothing here is installed in the tree. Each mutant is injected into modules
already imported inside this throwaway process, and the test functions are called
directly rather than through pytest, so the strict-xfail marks do not mask the
outcome being measured.
"""
import pathlib
import sys
import tempfile
import importlib.util
import types

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

spec = importlib.util.spec_from_file_location(
    "tt", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tt)

from veracium.store import migration as MIG  # noqa: E402

RESULTS = []


def run(test, tmp):
    """Call one test body; return None if it passed, else the failure's text."""
    try:
        test(tmp)
        return None
    except BaseException as e:      # pytest's `Failed` inherits BaseException,
                                    # not Exception — catching Exception here let a
                                    # DID-NOT-RAISE escape the harness as a crash
        first = (str(e).splitlines() or [""])[0]   # a bare `assert x is True` has NO message
        return f"{type(e).__name__}: {first[:90]}" if first else type(e).__name__


def check(label, expect_fail, test, patch, unpatch):
    patch()
    try:
        with tempfile.TemporaryDirectory() as d:
            failure = run(test, pathlib.Path(d))
    finally:
        unpatch()
    ok = (failure is not None) == expect_fail
    verb = "KILLED" if expect_fail else "PASSED"
    got = ("failed: " + failure) if failure else "passed"
    print(f"  [{'OK ' if ok else '!! '}] {label}\n        expected {verb}, {got}")
    RESULTS.append((ok, label, got))


# ====================================================================
# A minimal but HONEST implementation, used as the positive control.
# ====================================================================
class _Receipt(dict):
    pass


def install_correct():
    """Redaction that honours §4b and the repeat-calls row."""
    state = {"receipts": {}, "events": [], "attested": set()}
    tt.Memory._0041_state = state

    def redact(self, *, kind, target_id, fields):
        key = (kind, target_id, tuple(fields))
        if key in state["receipts"]:
            r = _Receipt(state["receipts"][key])
            r["repeated"] = True                      # the ORIGINAL receipt, flagged
            return r
        for f in fields:
            self.store._conn.execute(
                f"UPDATE edges SET {f}=?, json=json_set(json,'$.{f}',?) WHERE id=?",
                (tt.MARKER, tt.MARKER, target_id))
        self.store._conn.commit()
        # ROUND 6: the honest implementation writes a `redacted` event into the
        # EXISTING edge_event journal, which is what §11.2 and §2d-ii specify —
        # not into a table of the test's own invention. The campaign caught this
        # the moment the helper was corrected: the positive control failed because
        # the stub still wrote the invented table, which is the control doing its
        # job on the implementation rather than on the check.
        row = self.store._conn.execute(
            "SELECT COALESCE(MAX(seq), -1) + 1, COALESCE(MAX(txn), -1) + 1 "
            "FROM edge_event WHERE user_id=?", (tt.U,)).fetchone()
        self.store._conn.execute(
            "INSERT INTO edge_event (user_id, seq, txn, edge_id, kind, reason, state, recorded_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (tt.U, row[0], row[1], target_id, "redacted", "subject_request",
             "tombstone", "2026-09-16T00:00:00Z"))
        self.store._conn.commit()
        state["events"].append(target_id)
        state["attested"].add((target_id, tuple(fields)))
        r = _Receipt(redacted_kind=kind, target_id=target_id,
                     fields_cleared=list(fields), recorded_at="2026-09-16T00:00:00Z",
                     repeated=False, reconstructed=False)
        state["receipts"][key] = dict(r)
        return r

    tt.Memory.redact = redact

    real_add = tt.Memory.__mro__ and None
    store_cls = type(tt._mem(pathlib.Path(tempfile.mkdtemp())).store)
    if not hasattr(store_cls, "_0041_real_add_edge"):
        store_cls._0041_real_add_edge = store_cls.add_edge

        def guarded_add_edge(self, edge, *a, **k):
            for (tid, fields) in state["attested"]:
                if edge.id == tid:
                    raise PermissionError(
                        "0041 INV-11: the field is attested-redacted; an ordinary "
                        "write may not reintroduce content")
            return store_cls._0041_real_add_edge(self, edge, *a, **k)

        store_cls.add_edge = guarded_add_edge
    tt._0041_store_cls = store_cls

    def report(store):
        rows = []
        for eid, obj in store._conn.execute("SELECT id, object FROM edges"):
            if obj == tt.MARKER and not any(eid == t for (t, _) in state["attested"]):
                rows.append({"target_id": eid, "field": "object"})
        return rows

    MIG.unattested_marker_report = report


def remove_correct():
    for name in ("redact", "_0041_state"):
        if hasattr(tt.Memory, name):
            delattr(tt.Memory, name)
    cls = getattr(tt, "_0041_store_cls", None)
    if cls is not None and hasattr(cls, "_0041_real_add_edge"):
        cls.add_edge = cls._0041_real_add_edge
        del cls._0041_real_add_edge
    if hasattr(MIG, "unattested_marker_report"):
        del MIG.unattested_marker_report


def stub(fn):
    def patch():
        tt.Memory.redact = fn
    return patch


def drop_redact():
    if hasattr(tt.Memory, "redact"):
        del tt.Memory.redact


def drop_report():
    if hasattr(MIG, "unattested_marker_report"):
        del MIG.unattested_marker_report


print(__doc__.strip().splitlines()[0])
print("\nT1 — test_F_a_repeated_call_returns_the_original_or_a_reconstructed_receipt")
T1 = tt.test_F_a_repeated_call_returns_the_original_or_a_reconstructed_receipt

check("the reviewer's mutant: a no-op redact()", True, T1,
      stub(lambda self, **k: None), drop_redact)
check("a fresh receipt every call, repeated always False", True, T1,
      stub(lambda self, **k: _Receipt(redacted_kind=k["kind"], target_id=k["target_id"],
                                      fields_cleared=list(k["fields"]),
                                      recorded_at="x", repeated=False,
                                      reconstructed=False)), drop_redact)
check("a receipt missing the `repeated` field entirely", True, T1,
      stub(lambda self, **k: _Receipt(redacted_kind="edge")), drop_redact)
check("POSITIVE CONTROL — an honest implementation", False, T1,
      install_correct, remove_correct)

print("\nT2 — test_C_the_migration_report_enumerates_unattested_marker_rows")
T2 = tt.test_C_the_migration_report_enumerates_unattested_marker_rows


def _report_stub(value):
    def patch():
        MIG.unattested_marker_report = lambda store: value
    return patch


check("the reviewer's mutant: a report that always returns []", True, T2,
      _report_stub([]), drop_report)
check("a report that names EVERY edge, marker or not", True, T2,
      _report_stub([{"target_id": i, "field": "object"}
                    for i in ("e-mark-1", "e-mark-2", "e-plain")]), drop_report)
check("a report that names the rows but not the carrier field", True, T2,
      _report_stub([{"target_id": "e-mark-1", "field": "subject"},
                    {"target_id": "e-mark-2", "field": "subject"}]), drop_report)
check("POSITIVE CONTROL — an honest report", False, T2,
      install_correct, remove_correct)

print("\nT3 — test_C_after_attestation_the_same_write_is_refused")
T3 = tt.test_C_after_attestation_the_same_write_is_refused

check("the reviewer's mutant: a no-op redact(), no attestation created", True, T3,
      stub(lambda self, **k: None), drop_redact)
check("POSITIVE CONTROL — redaction attests, and only the attested write is refused",
      False, T3, install_correct, remove_correct)

print("\nT4 — test_the_frozen_pre_restriction_store_matches_its_manifest (ROUND-6 FINDING 2)")
T4 = tt.test_the_frozen_pre_restriction_store_matches_its_manifest

# The reviewer's mutant, kept so the repair stays repaired. The original body ran
# the checker once, on the frozen bytes, and compared two digests for the altered
# copy — so forcing subprocess.run to succeed left it green. Both halves now read
# the same tool the same way, and the two mutants below are mirror images: one
# makes the checker always accept, the other always refuse.
import subprocess as _sp

_REAL_RUN = _sp.run


class _AlwaysOK:
    returncode, stdout, stderr = 0, "frozen fixture matches its manifest", ""


class _AlwaysRefuses:
    returncode, stdout, stderr = 1, "FROZEN FIXTURE CHANGED", ""


def _stub_run(cls):
    def patch():
        _sp.run = lambda *a, **k: cls()
    return patch


def _unstub():
    _sp.run = _REAL_RUN


check("the reviewer's mutant: a checker that always succeeds", True, T4,
      _stub_run(_AlwaysOK), _unstub)
check("its mirror: a checker that always refuses", True, T4,
      _stub_run(_AlwaysRefuses), _unstub)
check("POSITIVE CONTROL — the real checker, both halves", False, T4,
      lambda: None, lambda: None)

print("\n" + "=" * 72)
bad = [r for r in RESULTS if not r[0]]
print(f"{len(RESULTS)} mutants run, {len(RESULTS) - len(bad)} behaved as required")
if bad:
    for _, label, got in bad:
        print(f"  !! {label} — {got}")
    sys.exit(1)
print("every wrong implementation is refused AND every rewritten check can be made "
      "green by a correct one — the property the round-5 verdict found missing")
