#!/usr/bin/env python3
"""0041 round 10 — the verdict's four implementation findings, reproduced at the pin BEFORE any fix.

Pin `de9f9659855069118fcdaa74650e5bbb030c463a` (0041 v15). The reviewer's own regressions and probes (in their
evidence archive) were not supplied to this seat, so each scenario is built from the verdict's description, through
the REAL paths (`Memory`, `SqliteStore`, `export_memory`/`import_memory`, `delete_episode`). Records and notices come
from real exports; a file is hand-assembled only where the verdict's own reproduction assembles one (R10-02 puts an
older record beside a later notice; R10-03(a) is two notice inputs differing only in where a separator falls).

Each check prints the reviewer's claim and the outcome at this tree beside it: REPRODUCED means the defect is present.
Each finding also runs the CONTROLS the verdict names; a control that does not behave makes the run exit non-zero,
because a reproduction whose control fails shows nothing.
Run from the repository root (or an export): python specs/evidence/0041/round10_reproductions.py
"""
import importlib.util
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from veracium import redaction as R                                  # noqa: E402
from veracium.portability import export_memory, import_memory        # noqa: E402
from veracium.schema import Edge, Episode                            # noqa: E402

_spec = importlib.util.spec_from_file_location("tt41_r10", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r10"] = tt
_spec.loader.exec_module(tt)

U = "u"
SECRET = "REVIEW-CONTENT-ALPHA"
RESULTS = []          # (finding, reproduced)
CONTROLS = []         # (finding, behaved)


def claim(n, sentence):
    print(f"\n=== R10-0{n} — {sentence}")


def result(n, ok, detail):
    print(("    REPRODUCED: " if ok else "    DID NOT REPRODUCE: ") + detail)
    RESULTS.append((n, ok))


def control(n, ok, detail):
    print(("    control holds: " if ok else "    CONTROL FAILED: ") + detail)
    CONTROLS.append((n, ok))


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def mem(d, name):
    return tt._mem(pathlib.Path(d), name)


def lines(path):
    return [json.loads(x, object_pairs_hook=_strict_pairs) for x in path.read_text().splitlines() if x.strip()]


def write_lines(path, recs):
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return path


def header(recs):
    return [r for r in recs if r.get("kind") == "veracium-export"]


def notices(recs):
    return [r for r in recs if r.get("record") == "redaction"]


def ep_json(st, eid):
    row = st._conn.execute("SELECT json FROM episodes WHERE id=?", (eid,)).fetchone()
    return None if row is None else json.loads(row[0], object_pairs_hook=_strict_pairs)


def attested(st, user, kind, tid):
    return sorted(st._attested_fields(user, kind, tid))


def attempt(fn):
    try:
        return "ok", fn()
    except Exception as e:                       # the outcome IS the observation
        return "refused", f"{type(e).__name__}: {str(e)[:150]}"


# ---------------------------------------------------------------- R10-01
claim(1, "a full export carrying a newly redacted OUTCOME cannot apply its notice to a destination holding the earlier "
         "outcome: the outcome-chain branch refuses a held link whose content differs, notice or not")


def outcome_source(d, name):
    src = mem(d, f"{name}.db")
    src.store.add_edge(Edge(id="e-1", user_id=U, subject="user", relation="prefers", object=SECRET, provenance=tt._prov()))
    src.record_outcome(U, "e-1", outcome="confirmed", actor="user", evidence_ref="ev-outcome")
    oid = [e.id for e in src.store.episodes(U) if e.kind == "outcome"][0]
    p1 = pathlib.Path(d) / f"{name}-1.jsonl"
    export_memory(src.store, U, p1)
    src.redact(U, episode_id=oid, reason="subject_request")
    p2 = pathlib.Path(d) / f"{name}-2.jsonl"
    export_memory(src.store, U, p2)
    return src, oid, p1, p2


for restore in (False, True):
    with tempfile.TemporaryDirectory() as d:
        _src, oid, p1, p2 = outcome_source(d, f"o{int(restore)}")
        dst = mem(d, f"dst1-{int(restore)}.db")
        import_memory(dst.store, p1, restore=restore)
        held = ep_json(dst.store, oid)
        kind, got = attempt(lambda: import_memory(dst.store, p2, restore=restore))
        after = ep_json(dst.store, oid)
        result(1, kind == "refused" and "outcome link" in got and SECRET in json.dumps(after)
               and not attested(dst.store, U, "episode", oid),
               f"restore={restore}: the held outcome carried the content: {SECRET in json.dumps(held)}; the second "
               f"import → {kind}: {got if kind == 'refused' else {k: got.get(k) for k in ('notices_applied', 'notices_existing')}}; "
               f"afterwards the held outcome still carries it: {SECRET in json.dumps(after)}; attested: "
               f"{attested(dst.store, U, 'episode', oid)}")
    # control: the NOTICE ALONE treats the held outcome
    with tempfile.TemporaryDirectory() as d:
        _src, oid, p1, p2 = outcome_source(d, f"oc{int(restore)}")
        dst = mem(d, f"dst1c-{int(restore)}.db")
        import_memory(dst.store, p1, restore=restore)
        recs = lines(p2)
        only = write_lines(pathlib.Path(d) / "notice-only.jsonl", header(recs) + notices(recs))
        kind, got = attempt(lambda: import_memory(dst.store, only, restore=restore))
        after = ep_json(dst.store, oid)
        control(1, kind == "ok" and SECRET not in json.dumps(after) and attested(dst.store, U, "episode", oid),
                f"restore={restore}: the notice alone → {kind}; held outcome treated: {SECRET not in json.dumps(after)}; "
                f"attested {attested(dst.store, U, 'episode', oid)}")
# control: a changed outcome WITHOUT a notice is still refused
with tempfile.TemporaryDirectory() as d:
    _src, oid, p1, _p2 = outcome_source(d, "ocn")
    dst = mem(d, "dst1n.db")
    import_memory(dst.store, p1)
    recs = lines(p1)
    changed = [dict(r, summary=r["summary"] + " (edited)") if r.get("record") == "episode" and r.get("id") == oid
               else r for r in recs]
    kind, got = attempt(lambda: import_memory(dst.store, write_lines(pathlib.Path(d) / "chg.jsonl", changed)))
    control(1, kind == "refused" and "outcome link" in got,
            f"a changed outcome with no notice → {kind}: {got if kind == 'refused' else got}")

# ---------------------------------------------------------------- R10-02
claim(2, "after a treated interaction episode is DELETED, re-importing the identical file (the older record plus its "
         "already-applied notice) repopulates it: the primitive admits the record because a notice is in the plan, "
         "then skips the notice as existing")


def episode_file(d, name):
    src = mem(d, f"{name}.db")
    src.store.add_episode(Episode(id="ep-1", user_id=U, date="2026-10-01", summary=f"we discussed {SECRET}",
                                  provenance=tt._prov()))
    p_old = pathlib.Path(d) / f"{name}-old.jsonl"
    export_memory(src.store, U, p_old)
    src.redact(U, episode_id="ep-1", reason="subject_request")
    p_new = pathlib.Path(d) / f"{name}-new.jsonl"
    export_memory(src.store, U, p_new)
    old, new = lines(p_old), lines(p_new)
    rec = [r for r in old if r.get("record") == "episode" and r.get("id") == "ep-1"]
    combined = write_lines(pathlib.Path(d) / f"{name}-combined.jsonl", header(new) + rec + notices(new))
    record_only = write_lines(pathlib.Path(d) / f"{name}-record.jsonl", header(new) + rec)
    return combined, record_only


for restore in (False, True):
    with tempfile.TemporaryDirectory() as d:
        combined, _r = episode_file(d, f"e{int(restore)}")
        dst = mem(d, f"dst2-{int(restore)}.db")
        r1 = import_memory(dst.store, combined, restore=restore)
        first_treated = SECRET not in json.dumps(ep_json(dst.store, "ep-1"))
        dst.store.delete_episode("ep-1")
        kind, r2 = attempt(lambda: import_memory(dst.store, combined, restore=restore))
        after = ep_json(dst.store, "ep-1")
        rep_kind, rep = attempt(lambda: dst.redact(U, episode_id="ep-1", reason="subject_request"))
        after_redact = ep_json(dst.store, "ep-1")
        result(2, first_treated and kind == "ok" and after is not None and SECRET in json.dumps(after)
               and attested(dst.store, U, "episode", "ep-1") and rep_kind == "ok" and rep.repeated
               and SECRET in json.dumps(after_redact),
               f"restore={restore}: first import applied {r1.get('notices_applied')}, treated: {first_treated}; after "
               f"delete_episode the identical file → {kind}: "
               f"{ {k: r2.get(k) for k in ('episodes', 'notices_existing', 'notices_applied')} if kind == 'ok' else r2}; "
               f"the summary carries the content again: {after is not None and SECRET in json.dumps(after)} while "
               f"attested {attested(dst.store, U, 'episode', 'ep-1')}; a public redact then → repeated="
               f"{getattr(rep, 'repeated', rep)}, content still present: {SECRET in json.dumps(after_redact)}")
    with tempfile.TemporaryDirectory() as d:          # control: the same repeat WITHOUT the deletion stays treated
        combined, _r = episode_file(d, f"ec{int(restore)}")
        dst = mem(d, f"dst2c-{int(restore)}.db")
        import_memory(dst.store, combined, restore=restore)
        kind, _ = attempt(lambda: import_memory(dst.store, combined, restore=restore))
        control(2, SECRET not in json.dumps(ep_json(dst.store, "ep-1")),
                f"restore={restore}: repeat without deletion → {kind}; still treated: "
                f"{SECRET not in json.dumps(ep_json(dst.store, 'ep-1'))}")
    with tempfile.TemporaryDirectory() as d:          # control: re-arrival WITHOUT a notice refuses, episode stays absent
        combined, record_only = episode_file(d, f"en{int(restore)}")
        dst = mem(d, f"dst2n-{int(restore)}.db")
        import_memory(dst.store, combined, restore=restore)
        dst.store.delete_episode("ep-1")
        kind, got = attempt(lambda: import_memory(dst.store, record_only, restore=restore))
        control(2, kind == "refused" and ep_json(dst.store, "ep-1") is None,
                f"restore={restore}: re-arrival with no notice → {kind}; absent afterwards: {ep_json(dst.store, 'ep-1') is None}")

# ---------------------------------------------------------------- R10-03
claim(3, "the notice identity joins unrestricted strings with U+001F and compares the source identity by a substr "
         "prefix: separator-bearing triples collide, a relay loses the source triple, and a NUL defeats the "
         "cross-import body comparison")


def edge_notice_file(d, name, user=U, obj=SECRET, reason="subject_request"):
    src = mem(d, f"{name}.db")
    src.store.add_edge(Edge(id="e-x", user_id=user, subject="user", relation="lives_at", object=obj, provenance=tt._prov()))
    src.redact(user, edge_id="e-x", reason=reason)
    p = pathlib.Path(d) / f"{name}.jsonl"
    export_memory(src.store, user, p)
    return src, p


# (a) two DISTINCT source triples that encode equal
with tempfile.TemporaryDirectory() as d:
    _src, p = edge_notice_file(d, "c-a")
    recs = lines(p)
    n0 = notices(recs)[0]
    a = dict(n0, origin="origin\u001fpart", source_user="owner", source_event_ref="event")
    b = dict(n0, origin="origin", source_user="part\u001fowner", source_event_ref="event")
    dst = mem(d, "dst3a.db")
    ra = import_memory(dst.store, write_lines(pathlib.Path(d) / "a.jsonl", header(recs) + [a]))
    kind, rb = attempt(lambda: import_memory(dst.store, write_lines(pathlib.Path(d) / "b.jsonl", header(recs) + [b])))
    rows = dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0]
    result(3, kind == "ok" and rb.get("notices_existing") == 1 and rows == 1,
           f"(a) source triple ('origin\\x1fpart','owner','event') then ('origin','part\\x1fowner','event'): first standing "
           f"{ra.get('notices_standing')}; second → {kind}: "
           f"{ {k: rb.get(k) for k in ('notices_standing', 'notices_existing')} if kind == 'ok' else rb}; rows held: {rows}")

# (b) a native source user carrying U+001F: the relay re-labels the foreign identity as its own
for user, is_control in (("owner\u001fpart", False), ("owner", True)):
    with tempfile.TemporaryDirectory() as d:
        src, p = edge_notice_file(d, "c-b", user=user)
        orig = notices(lines(p))[0]
        dst = mem(d, "dst3b.db")
        import_memory(dst.store, p, user_id="destination")
        relay = pathlib.Path(d) / "relay.jsonl"
        export_memory(dst.store, "destination", relay)
        rel = notices(lines(relay))[0]
        triple = lambda n: (n["origin"], n["source_user"], n["source_event_ref"])
        same = triple(rel) == triple(orig)
        if is_control:
            control(3, same, f"(b) control source user 'owner': the relay preserves the source triple: {same}")
        else:
            result(3, not same,
                   f"(b) source user 'owner\\x1fpart', imported remapped to 'destination', re-exported: source triple "
                   f"{triple(orig)!r} became {triple(rel)!r}")

# (c) a native source user carrying NUL: the cross-import body comparison does not run
for user, is_control in (("owner\u0000part", False), ("owner", True)):
    with tempfile.TemporaryDirectory() as d:
        _src, p = edge_notice_file(d, "c-c", user=user)
        recs = lines(p)
        n0 = notices(recs)[0]
        dst = mem(d, "dst3c.db")
        import_memory(dst.store, write_lines(pathlib.Path(d) / "n1.jsonl", header(recs) + [n0]))
        changed = dict(n0, reason="legal_obligation")
        kind, got = attempt(lambda: import_memory(dst.store, write_lines(pathlib.Path(d) / "n2.jsonl", header(recs) + [changed])))
        if is_control:
            control(3, kind == "refused" and "different body" in got,
                    f"(c) control source user 'owner': the same identity with a changed reason → {kind}")
        else:
            result(3, kind == "ok",
                   f"(c) source user 'owner\\x00part': a standing notice, then the same identity with reason "
                   f"'legal_obligation' → {kind}: {got if kind == 'refused' else {k: got.get(k) for k in ('notices_existing', 'notices_standing')}}")

# ---------------------------------------------------------------- R10-04
claim(4, "`imported_notice` is an admitted reason of the public Memory.redact, and the reason text is then read as "
         "provenance: the local receipt reads reconstructed and the export is one the importer refuses")
for reason in R.REDACTION_REASONS:
    with tempfile.TemporaryDirectory() as d:
        src, p = edge_notice_file(d, "r4", reason=reason)
        receipt = src.redact(U, edge_id="e-x", reason=reason)          # the repeat returns the record's receipt
        n0 = notices(lines(p))[0]
        dst = mem(d, "dst4.db")
        kind, got = attempt(lambda: import_memory(dst.store, p, restore=True))
        facts = (receipt.reconstructed, n0.get("marker_version"), n0.get("reason"))
        if reason == "imported_notice":
            result(4, receipt.reconstructed and n0.get("marker_version") is None and kind == "refused",
                   f"reason 'imported_notice': receipt reconstructed={receipt.reconstructed}, marker_version="
                   f"{receipt.marker_version}, event_ref={receipt.event_ref}; the export's notice marker_version="
                   f"{n0.get('marker_version')}, reason={n0.get('reason')}; restore into an empty store → {kind}: "
                   f"{got if kind == 'refused' else ''}")
        else:
            control(4, not receipt.reconstructed and kind == "ok",
                    f"reason {reason!r}: (reconstructed, marker_version, reason) = {facts}; restore → {kind}")

# ---------------------------------------------------------------- summary
print("\n" + "-" * 100)
for n, ok in RESULTS:
    print(f"  R10-0{n}: {'REPRODUCED' if ok else 'DID NOT REPRODUCE'}")
bad = [n for n, ok in CONTROLS if not ok]
print(f"  controls: {len(CONTROLS) - len(bad)} of {len(CONTROLS)} hold" + (f"; FAILED for {sorted(set(bad))}" if bad else ""))
sys.exit(0 if all(ok for _, ok in RESULTS) and not bad else 1)
