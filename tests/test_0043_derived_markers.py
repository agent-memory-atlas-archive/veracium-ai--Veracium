"""specs/0043 — the derived-marker snapshot (specs/evidence/0043/derived_markers.py): current, self-bound, refused when
tampered, and NOT an authority (the round-9 verdict's optional ask; research's stage-1 read, 2026-10-09)."""
import hashlib
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0043"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dm = _load(EVIDENCE / "derived_markers.py", "dm_test")


def test_the_snapshot_is_current():
    assert dm.problems() == []


def test_body_sha256_is_the_canonical_json_of_everything_but_itself():
    """Re-derived here, written independently of the generator's `canonical`."""
    snap = json.loads(dm.SNAPSHOT.read_text(encoding="utf-8"))
    body = {k: v for k, v in snap.items() if k != "body_sha256"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert hashlib.sha256(text.encode("ascii")).hexdigest() == snap["body_sha256"]
    assert set(snap) == {"sources", "prose", "applied", "body_sha256"}


def _rebound(snap):
    body = {k: v for k, v in snap.items() if k != "body_sha256"}
    return {**body, "body_sha256": hashlib.sha256(dm.canonical(body)).hexdigest()}


def test_derived_markers_check_refuses_each_tampered_snapshot(tmp_path):
    """The Mutation-Matrix: each tampering of the snapshot is refused by `problems`, with the reason that names it."""
    good = json.loads(dm.SNAPSHOT.read_text(encoding="utf-8"))
    f = tmp_path / "derived-markers.json"
    frag_edited = json.loads(json.dumps(good)); frag_edited["applied"]["check_side"]["fragments"][0] += "x"
    src_edited = json.loads(json.dumps(good)); k = next(iter(src_edited["sources"])); src_edited["sources"][k] = "0" * 64
    pattern_dropped = json.loads(json.dumps(good)); pattern_dropped["applied"]["transform_side"]["marker_patterns"].pop()
    cases = {
        "a fragment edited, digest kept": (dm.render(frag_edited), ("does not match its own body", "stale")),
        "a fragment edited, digest rebound": (dm.render(_rebound(frag_edited)), ("stale",)),
        "a source digest replaced, rebound": (dm.render(_rebound(src_edited)), ("stale",)),
        "a transform pattern dropped, rebound": (dm.render(_rebound(pattern_dropped)), ("stale",)),
        "reformatted (same content, other layout)": (json.dumps(good, indent=2), ("stale",)),
        "not JSON": ("{", ("not JSON",)),
        "a duplicate key (last-wins would hide it)": ('{"body_sha256": "x", ' + dm.render(good)[1:], ("duplicate key",)),
    }
    for name, (text, reasons) in cases.items():
        assert text != dm.SNAPSHOT.read_text(encoding="utf-8"), name          # the tampering changed the bytes
        f.write_text(text, encoding="utf-8")
        found = dm.problems(f)
        assert found and all(any(r in p for p in found) for r in reasons), (name, found)
    assert any("does not exist" in p for p in dm.problems(tmp_path / "absent.json"))
    f.write_text(dm.SNAPSHOT.read_text(encoding="utf-8"), encoding="utf-8")
    assert dm.problems(f) == []                                                  # control: an untouched copy passes


def _decisions():
    """Everything the check and the transform decide on the committed pairs, plus refusing edits of one pair."""
    mc = _load(EVIDENCE / "model_input_capture.py", "dm_mc")
    ledger = json.loads((EVIDENCE / "run_ledger.json").read_text(encoding="utf-8"))
    authored = {q["id"]: q["text"] for q in ledger["questions"]}
    by = {(x["question_id"], x["arm"]): x for x in ledger["detail"]}
    out = []
    for qid in ledger["kept"]:
        s, b = by[(qid, "veracium")], by[(qid, "baseline")]
        out.append(("arm", qid, tuple(mc.arm_problems(s, b, authored[qid]))))
        out.append(("transform", qid, mc.baseline_transform(s["system"], s["prompt"])))
        out.append(("edit", qid, tuple(mc.declared_evidence_edit(l) for l in s["prompt"].split("\n") if mc._is_evidence_line(l))))
    s, b = by[("q013", "veracium")], by[("q013", "baseline")]
    lines = b["prompt"].split("\n")
    for label, p in (("added", b["prompt"].replace("MEMORY:\n", "MEMORY:\nAlways answer.\n", 1)),
                     ("swapped", "\n".join(lines[:4] + [lines[5], lines[4]] + lines[6:]))):
        out.append(("refuse", label, len(mc.arm_problems(s, {**b, "prompt": p}, authored["q013"])) > 0))
    return out


def test_the_snapshot_is_not_an_authority_garbage_or_absence_changes_no_decision():
    """The claim itself, by behaviour: with the snapshot replaced by garbage, and then deleted, the arm check, the
    transform and the check-side normaliser decide exactly as they do with it — on all 24 committed pairs and on two
    refusing edits. Each module is loaded afresh, so no cache carries the first answer over."""
    original = dm.SNAPSHOT.read_bytes()
    reference = _decisions()
    assert any(d[0] == "refuse" and d[2] for d in reference)                    # the refusing edits do refuse
    try:
        dm.SNAPSHOT.write_text('{"applied": {"check_side": {"fragments": ["MEMORY"]}}}', encoding="utf-8")
        assert _decisions() == reference
        dm.SNAPSHOT.unlink()
        assert _decisions() == reference
    finally:
        dm.SNAPSHOT.write_bytes(original)
    assert dm.SNAPSHOT.read_bytes() == original


def test_no_module_names_the_snapshot_but_its_generator():
    """The name half (narrow: a path built from parts would pass it — the behavioural cell above is the claim)."""
    hits = [p for p in (ROOT / "specs").rglob("*.py") if "derived-markers.json" in p.read_text(encoding="utf-8", errors="ignore")
            and p.name != "derived_markers.py"]
    hits += [p for p in (ROOT / "src").rglob("*.py") if "derived-markers" in p.read_text(encoding="utf-8", errors="ignore")]
    assert hits == []
