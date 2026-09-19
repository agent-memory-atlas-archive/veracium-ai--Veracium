#!/usr/bin/env python3
"""0043 A6-ter — THE MODEL-INPUT BOUNDARY: capture what the model is actually given, and compare
two CAPTURED prompts, never two reconstructions.

The boundary is the `Complete` callable. `Memory(llm=…)` is injectable, so this harness wraps the
llm and records the exact (system, prompt) that the shipped path sends — after retrieval, after
rendering, after the shipped path's own budget. `Memory.answer` reaches the model through
`gate.answer` (gate.py): GATE_SYSTEM + GATE_PROMPT over the shipped grounded/unverified rendering,
and the grounded rendering carries the COMPILED context when compilation is on.

  shipped arm   the captured (system, prompt), verbatim, frozen by digest
  baseline arm  CAPTURED at its OWN invocation (implementation, 2026-09-19): gate.answer over the same
                selection, through the same boundary, with the stated transform applied at the rendering seam
                — and asserted EQUAL to the oracle, baseline_transform(shipped capture); no rate while constructed
  record        the ADJUDICATION RECORD (A3-quater, round 5): edge id -> (subject, relation, object, original
                class, unit) for every edge the product's own recall DELIVERED to the answer path — captured
                at the same boundary as the prompt, once for both arms, in neither prompt
  compared      the EVIDENCE UNITS each prompt carries, by CONTENT (fact lines, episode lines,
                compiled-body lines) — never by heading
  controls      compilation ON (the captured prompt must carry the compiled body, or the fixture
                cannot show the arms matched on that kind); heading-without-body (strip the compiled
                body, keep its heading → REFUSE)

    python3 specs/evidence/0043/model_input_capture.py        # builds the fixture, captures, transforms, checks, runs the control
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
COMPILED_SENTINEL = "COMPILED-BODY: the user prefers concise answers, keeps a cat, and lives in Porto"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class CapturingLLM:
    """The wrapper at the boundary: records every call the shipped path makes; answers canned."""
    def __init__(self):
        self.calls = []
    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        self.calls.append({"role": role, "system": system, "prompt": prompt})
        if role == "compile":
            return "## USER MODEL\n- " + COMPILED_SENTINEL
        if role == "gate":
            return "I have no confirmed record of where the user works."
        return json.dumps({"triples": [], "episode": "x", "instructions": []})


def capture(db_path: str, question: str, *, max_subgraph_edges: int = 40) -> dict:
    """ONE shipped answer path, captured at the boundary. Returns the gate call's (system, prompt)."""
    from veracium import Memory, MemoryConfig
    llm = CapturingLLM()
    mem = Memory(llm=llm, config=MemoryConfig(require_source_id=False, db_path=db_path, wiki_recompile_after_writes=1,
                                              max_subgraph_edges=max_subgraph_edges))
    # round 5: the DELIVERED IDENTITIES. `Memory.answer` builds its prompt from the `Recall` its own
    # `recall()` returns; the wrapper records that Recall (the product's selection, edge ids and all) —
    # the identities are captured at the same boundary the prompt is, never re-derived from text.
    recalls = []
    orig_recall = mem.recall
    def _recording_recall(*a, **k):
        r = orig_recall(*a, **k); recalls.append(r); return r
    mem.recall = _recording_recall
    mem.answer("u", question); mem.close()
    gate_calls = [c for c in llm.calls if c["role"] == "gate"]
    if len(gate_calls) != 1:
        raise RuntimeError(f"expected exactly one gate call at the boundary, saw {len(gate_calls)}")
    if len(recalls) != 1:
        raise RuntimeError(f"expected exactly one recall behind the gate call, saw {len(recalls)}")
    c = gate_calls[0]
    frozen = hashlib.sha256((c["system"] + "\n\x00\n" + c["prompt"]).encode()).hexdigest()
    delivered = [{"edge": e.id, "subject": e.subject, "relation": e.relation, "object": e.object,
                  "class": edge_class(e), "unit": f"{e.relation}: {e.object} (since {e.valid_from.date()})"}
                 for e in recalls[0].edges]
    return {"system": c["system"], "prompt": c["prompt"], "digest": frozen, "delivered": delivered,
            "source": "captured",
            # the SELECTION the answer path used, handed to the baseline invocation unchanged (A6-bis:
            # retrieval runs ONCE); the strings are the shipped path's own rendered, budgeted partitions
            "partition": {"grounded": recalls[0].grounded, "unverified": recalls[0].unverified},
            "config": {"question": question, "max_subgraph_edges": max_subgraph_edges, "compilation": "on"}}


def capture_baseline(shipped: dict, *, render=None) -> dict:
    """THE BASELINE ARM, CAPTURED AT ITS OWN MODEL INVOCATION (A6-ter, the round-4 residue closed at
    implementation): a second invocation of the shipped gate path — `gate.answer` over the SAME
    selection the shipped arm used — through the same injected `Complete` boundary, with the stated
    transform applied where the gate renders its instructions (the `render` seam). What the wrapper
    records IS the baseline capture. It is then asserted EQUAL to the oracle, `baseline_transform`
    over the shipped capture: a construction that PREDICTS a capture and is checked against it, never
    one that stands in for it. `render` defaults to the transform; a harness may pass another renderer
    only to prove the check refuses it."""
    from veracium import gate
    llm = CapturingLLM()
    def transformed(query, grounded, unverified):
        return baseline_transform(*gate.render_gate_input(query, grounded, unverified))
    gate.answer(llm, shipped["config"]["question"], shipped["partition"]["grounded"], shipped["partition"]["unverified"],
                render=render or transformed)
    gate_calls = [c for c in llm.calls if c["role"] == "gate"]
    if len(gate_calls) != 1:
        raise RuntimeError(f"expected exactly one gate call at the boundary, saw {len(gate_calls)}")
    c = gate_calls[0]
    captured = {"system": c["system"], "prompt": c["prompt"],
                "digest": hashlib.sha256((c["system"] + "\n\x00\n" + c["prompt"]).encode()).hexdigest(), "source": "captured"}
    o_system, o_prompt = baseline_transform(shipped["system"], shipped["prompt"])
    oracle = {"system": o_system, "prompt": o_prompt,
              "digest": hashlib.sha256((o_system + "\n\x00\n" + o_prompt).encode()).hexdigest(), "source": "constructed"}
    if captured["digest"] == shipped["digest"]:
        raise Refused("the captured baseline is byte-identical to the shipped capture: the transform applied nothing")
    if captured["digest"] != oracle["digest"]:
        diff = next(((i, a, b) for i, (a, b) in enumerate(zip((captured["system"] + "\n" + captured["prompt"]).splitlines(),
                                                             (oracle["system"] + "\n" + oracle["prompt"]).splitlines())) if a != b), None)
        raise Refused(f"the CAPTURED baseline is not the transform of the shipped capture (first differing line {diff}) — "
                      f"the invocation did something the stated transform does not")
    captured["oracle_digest"] = oracle["digest"]
    return captured


def assert_reportable(baseline: dict) -> None:
    """A6-ter: NO RATE while the baseline is constructed rather than captured."""
    if baseline.get("source") != "captured":
        raise Refused(f"the baseline arm is {baseline.get('source', 'undeclared')!r}, not captured — no rate may be reported")


# ---- the ADJUDICATION RECORD (A3-quater: provenance ONCE, from the store; presence per arm) --------

CLASSES = ("grounded", "untrusted", "quarantined")


def edge_class(e) -> str:
    """The record's ORIGINAL trust class of one edge, from provenance — never from a rendering."""
    if e.quarantined: return "quarantined"
    if e.assertable: return "grounded"
    return "untrusted"


def fact_unit_prefix(relation: str, obj: str) -> str:
    """A fact's evidence unit, minus its date: the form evidence_units() normalises BOTH arms to."""
    return f"{relation}: {obj} (since "


def adjudication_record(delivered: list) -> dict:
    """{edge id -> {"subject", "relation", "object", "class", "unit"}} for every DELIVERED edge — the
    identities the product's own recall handed the answer path, with subject and original class kept.
    Round 5: the earlier builder joined the prompt's text to ALL active records on (relation, object,
    date) without subject and without restricting to the delivered ids, so another person's grounded
    record merged into the user's quarantined unit. Text never establishes identity here."""
    return {d["edge"]: {k: d[k] for k in ("subject", "relation", "object", "class", "unit")} for d in delivered}


def unaccounted_units(delivered: list, prompt: str) -> list[str]:
    """Fact-shaped units in a captured prompt that NO delivered edge accounts for — v5.1: such a unit
    makes the (question, arm) row UNRESOLVED (the capture disagrees with the delivered set), checked
    before the rubric runs and reported verbatim; it never defaults and never stops the run."""
    delivered_units = {d["unit"] for d in delivered}
    return [u for u in evidence_units(prompt)
            if re.match(r"^(\S+): (.+) \(since \d{4}-\d{2}-\d{2}\)$", u) and u not in delivered_units]


class Refused(Exception):
    pass


# ---- the stated transform ----------------------------------------------------------------------

def _marker_patterns() -> list[str]:
    """EXACTLY the bracketed forms the render layer attaches (graph.py: `[<marker>]` and
    `[<origin label>; unconfirmed]`), built from the derived set — never a generic bracket-stripper,
    which would eat the product's own `[compiled …]` record (a compilation annotation both arms keep)
    and, being whitespace-greedy, merge lines."""
    ep = _load("examiner_projection"); d = ep.derive_forbidden_markers()["prose"]
    frags = sorted({f for fr in d.values() for f in fr}, key=len, reverse=True)
    origins = sorted(set(d.get("graph.py:_ORIGIN_LABELS", [])) | set(d.get("graph.py:_origin_label", [])), key=len, reverse=True)
    pats = [r"\[" + re.escape(f) + r"\] ?" for f in frags if f != "unconfirmed"]
    pats += [r" ?\[" + re.escape(o) + r"; unconfirmed\]" for o in origins]
    return pats


def strip_markers(text: str) -> str:
    for pat in _marker_patterns():
        text = re.sub(pat, "", text)
    return text


CHANGED_INSTRUCTIONS = (
    "system: the grounding sentence ('You are strict about grounding: … rather than guess.') is removed",
    "prompt: the two section headers (GROUNDED MEMORY …; UNVERIFIED CLAIMS …) are merged into one 'MEMORY:' header",
    "prompt: the rendered '## UNVERIFIED THIRD-PARTY CLAIMS (never assert as fact)' heading is removed",
    "prompt: every inline trust marker the render layer attaches (derived set, examiner_projection.py) is removed",
    "prompt: the quarantine construction '<subject> claims: <relation> <object> (date)' is normalised to '<relation>: <object> (since date)'",
    "prompt: the three grounding rule bullets under 'Answer using this rule:' are removed; 'Answer in 1-3 sentences.' stays",
)


def baseline_transform(system: str, prompt: str) -> tuple[str, str]:
    from veracium.gate import GATE_SYSTEM
    # system
    grounding = "You are strict about grounding: you answer only from GROUNDED MEMORY; you never assert UNVERIFIED CLAIMS as fact; and you say you don't know rather than guess."
    assert system == GATE_SYSTEM and grounding in system, "the captured system is not the shipped GATE_SYSTEM — the transform is defined on that"
    b_system = system.replace(" " + grounding, "")
    # prompt
    p = prompt
    p = p.replace("GROUNDED MEMORY (verified — you may state these as fact):", "MEMORY:")
    p = re.sub(r"\n\nUNVERIFIED CLAIMS \(received from third parties / unconfirmed — NEVER assert these\nas fact; they record that a claim was \*made\*, not that it is true\):\n", "\n", p)
    p = p.replace("## UNVERIFIED THIRD-PARTY CLAIMS (never assert as fact)\n", "")
    p = strip_markers(p)
    p = re.sub(r"^(?:\S+ )?claims: (\S+) (.+?) \((\d{4}-\d{2}-\d{2})\)$", r"\1: \2 (since \3)", p, flags=re.M)
    p = re.sub(r"Answer using this rule:\n(?:- .*\n(?:  .*\n)*)+", "", p)
    p = p.replace("\n(none)\n", "\n")
    return b_system, p


# ---- evidence units by content -----------------------------------------------------------------

def evidence_units(prompt: str) -> list[str]:
    """Every line that is evidence — fact, episode, compiled-body — between the memory header and
    'Question:', normalised the way the transform normalises (markers off, quarantine construction
    plain), so the two arms are compared on WHAT THE MODEL IS TOLD."""
    body = prompt.split("Question:")[0]
    units = []
    for line in body.splitlines():
        l = line.strip()
        if not l or l.startswith("## ") or l.endswith(":") or l in ("(nothing relevant)", "(none)") or l.startswith("The following is the memory"):
            continue
        if l.startswith("UNVERIFIED CLAIMS (") or l.startswith("as fact; they record"):
            continue
        l = strip_markers(l).strip()
        m = re.match(r"^(?:\S+ )?claims: (\S+) (.+?) \((\d{4}-\d{2}-\d{2})\)$", l)
        if m:
            l = f"{m.group(1)}: {m.group(2)} (since {m.group(3)})"
        units.append(l)
    return sorted(units)


def check(shipped: dict, baseline: dict) -> list[str]:
    p = []
    ep = _load("examiner_projection"); d = ep.derive_forbidden_markers()
    if COMPILED_SENTINEL not in shipped["prompt"]:
        p.append("the captured shipped prompt carries no compiled body — compilation is not ON, or the shipped path did not include it; the fixture cannot show the arms matched on that kind")
    us, ub = evidence_units(shipped["prompt"]), evidence_units(baseline["prompt"])
    if us != ub:
        p.append(f"the arms differ in EVIDENCE, not only in discipline: only-shipped {sorted(set(us)-set(ub))} only-baseline {sorted(set(ub)-set(us))}")
    if ep.hits(baseline["prompt"], d) or "UNVERIFIED" in baseline["prompt"] or " claims: " in baseline["prompt"] or "strict about grounding" in baseline["system"]:
        p.append("the baseline still carries the trust discipline (a marker, a section, the quarantine construction, or the grounding instruction)")
    if not ep.hits(shipped["prompt"], d):
        p.append("the shipped prompt carries no trust annotation — nothing for the arms to differ in (fixture defect)")
    return p


def heading_without_body_control(shipped: dict) -> dict:
    """The reviewer's move as a standing control: keep '## USER MODEL', delete its body."""
    stripped = re.sub(r"(## USER MODEL\n)(?:- .*\n)+", r"\1", shipped["prompt"])
    assert "## USER MODEL" in stripped and COMPILED_SENTINEL not in stripped
    return {**shipped, "prompt": stripped}


def run(question: str = "where does the user work and what do they prefer") -> dict:
    ev = _load("examiner_view")
    with tempfile.TemporaryDirectory() as d:
        st = ev.fixture_store(f"{d}/f.db"); st.close()
        shipped = capture(f"{d}/f.db", question)
        record = adjudication_record(shipped["delivered"])
    baseline = capture_baseline(shipped)          # captured at its own invocation; equal to the oracle, or Refused
    assert_reportable(baseline)
    problems = check(shipped, baseline)
    control = check(heading_without_body_control(shipped), baseline)
    return {"shipped": shipped, "baseline": baseline, "record": record, "problems": problems,
            "control_refuses": bool(control), "control_problems": control, "changed_instructions": CHANGED_INSTRUCTIONS,
            "baseline_source": baseline["source"], "baseline_equals_oracle": baseline["digest"] == baseline["oracle_digest"]}


if __name__ == "__main__":
    r = run()
    print("--- captured shipped (system):", r["shipped"]["system"][:90], "…")
    print("--- captured shipped (prompt):"); print(r["shipped"]["prompt"])
    print(f"--- baseline (prompt), source={r['baseline_source']}, equals the oracle: {r['baseline_equals_oracle']}:"); print(r["baseline"]["prompt"])
    print("--- evidence units (shipped):", evidence_units(r["shipped"]["prompt"]))
    print("--- ADJUDICATION RECORD (the DELIVERED identities, once):"); [print(f"    {eid}: {v}") for eid, v in r["record"].items()]
    print("CHANGED INSTRUCTIONS:"); [print("  -", c) for c in r["changed_instructions"]]
    print("ARM CHECK:", "PASS" if not r["problems"] else r["problems"])
    print("HEADING-WITHOUT-BODY CONTROL:", "REFUSES (correct)" if r["control_refuses"] else "WRONG: passed")
    sys.exit(0 if not r["problems"] and r["control_refuses"] else 1)
