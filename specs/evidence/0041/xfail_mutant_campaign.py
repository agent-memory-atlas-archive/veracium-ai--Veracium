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

    def redact(self, user_id, *, edge_id=None, episode_id=None, reason):
        # ROUND 7: §4a's signature — `redact(user_id, *, edge_id | episode_id,
        # reason)`. The honest implementation carried the adapter's INVENTED
        # signature until the adapter was corrected, and both positive controls
        # went red the moment it was. A positive control tests the implementation,
        # not the check, and these noticed the contract had moved under them — the
        # second time in two rounds that has happened, and the reason they are
        # worth their cost.
        kind = "edge" if edge_id is not None else "episode"
        target_id = edge_id if edge_id is not None else episode_id
        fields = ["object"]
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
      stub(lambda self, *a, **k: None), drop_redact)
check("a fresh receipt every call, repeated always False", True, T1,
      stub(lambda self, *a, **k: _Receipt(redacted_kind="edge", target_id=k.get("edge_id"),
                                         fields_cleared=["object"],
                                         recorded_at="x", repeated=False,
                                         reconstructed=False)), drop_redact)
check("a receipt missing the `repeated` field entirely", True, T1,
      stub(lambda self, *a, **k: _Receipt(redacted_kind="edge")), drop_redact)
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
      stub(lambda self, *a, **k: None), drop_redact)
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

print("\nT5 — test_B_an_import_carrying_a_prose_kind_is_refused (ROUND-7 CORRECTION 2)")
T5 = tt.test_B_an_import_carrying_a_prose_kind_is_refused

# The round-7 reviewer's own mutant, kept so the isolation stays isolated. The
# test exported the WHOLE frozen store, so an import rule rejecting MARKERS — with
# no kind validation at all — satisfied its expected rejection. The export is now
# isolated to the prose-kind episode, and this mutant proves it: a marker-only
# rule must NO LONGER be able to make this test pass.
import veracium.portability as _port

_REAL_IMPORT = _port.import_memory


class _Anything:
    """A recognised-kind set that admits every value: the landed closure switched OFF for one mutant."""
    def __contains__(self, item): return True
    def __iter__(self): return iter(("interaction", "outcome"))


import veracium.redaction as _red
_REAL_KINDS = _red.RECOGNISED_EPISODE_KINDS


def _marker_only_import():
    # ROUND-8 FOLLOW-UP 1: this mutant searched the RAW file text, and JSON escapes
    # the marker's NUL bytes — so it could never have found a marker in any export
    # and the "marker-only rule" it simulated was really a rule that does nothing.
    # A mutant that cannot do the wrong thing cannot prove a check refuses it.
    # It decodes now, through the same helper the test uses.
    # 0041 TRANCHE 1 (2026-09-19): the kind closure is LANDED (store/sqlite.py refuses an
    # unrecognised kind at the import commit), so a wrong import rule installed on top of
    # the real store can no longer let a prose kind through — the mutant must also switch
    # the landed closure OFF, or it is not a mutant of anything. It does, and restores it.
    _red.RECOGNISED_EPISODE_KINDS = _Anything()
    def rule(store, path, *a, **k):
        if tt._exported_markers(pathlib.Path(path)):
            raise ValueError("marker rejected at import — NO kind validation performed")
        return _REAL_IMPORT(store, path, *a, **k)
    _port.import_memory = rule


def _real_import():
    _port.import_memory = _REAL_IMPORT
    _red.RECOGNISED_EPISODE_KINDS = _REAL_KINDS


check("the reviewer's mutant: an import rule that rejects MARKERS and never looks "
      "at kinds", True, T5, _marker_only_import, _real_import)
check("POSITIVE CONTROL — the landed closure (0041 tranche 1): the real store refuses the prose kind at the import commit",
      False, T5, lambda: None, lambda: None)

# ====================================================================
# COVERAGE ACCOUNTING, corrected at round 7 and DERIVED rather than stated.
#
# The round-7 README claimed seven strict xfails awaited positive controls. The
# reviewer corrected it: there are FOUR positive controls but only THREE cover
# strict xfails — the fourth covers the ordinary fixture-checker test — so EIGHT
# await one. A completeness claim in a carrier, understated in the direction that
# flattered the evidence. It is computed here so the number cannot drift again.
# ====================================================================
import re as _re

_strict = 0
for _f in ("test_0041_transition_table.py", "test_0041_treatment_matrix.py",
           "test_0041_evidence.py"):
    _strict += (ROOT / "tests" / _f).read_text().count("xfail(strict=True")
_covered = sorted({lbl for ok, lbl, _ in RESULTS if "POSITIVE CONTROL" in lbl})
_strict_covered = [t for t in ("T1", "T2", "T3") ]
print("\n" + "=" * 72)
print("COVERAGE, derived:")
print(f"  strict xfails in the 0041 modules      {_strict}")
print(f"  positive controls in this campaign     {len(_covered)}")
print(f"  of those, covering a STRICT xfail      {len(_strict_covered)}  (T4 covers an ORDINARY test)")
print(f"  strict xfails still AWAITING one       {_strict - len(_strict_covered)}")
print("  §11.4-bis requires BOTH controls of every strict xfail; the remainder is")
print("  owed at implementation and is not claimed as done.")

print("\n" + "=" * 72)
bad = [r for r in RESULTS if not r[0]]
print(f"{len(RESULTS)} mutants run, {len(RESULTS) - len(bad)} behaved as required")
if bad:
    for _, label, got in bad:
        print(f"  !! {label} — {got}")
    sys.exit(1)
print("every wrong implementation is refused AND every rewritten check can be made "
      "green by a correct one — the property the round-5 verdict found missing")
