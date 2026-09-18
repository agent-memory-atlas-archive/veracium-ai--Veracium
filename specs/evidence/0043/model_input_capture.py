#!/usr/bin/env python3
"""0043 A6-ter — THE MODEL-INPUT BOUNDARY: capture what the model is actually given, and compare
two CAPTURED prompts, never two reconstructions.

The boundary is the `Complete` callable. `Memory(llm=…)` is injectable, so this harness wraps the
llm and records the exact (system, prompt) that the shipped path sends — after retrieval, after
rendering, after the shipped path's own budget. `Memory.answer` reaches the model through
`gate.answer` (gate.py): GATE_SYSTEM + GATE_PROMPT over the shipped grounded/unverified rendering,
and the grounded rendering carries the COMPILED context when compilation is on.

  shipped arm   the captured (system, prompt), verbatim, frozen by digest
  baseline arm  the SAME captured prompt under a STATED TRANSFORM — every changed instruction is
                named in CHANGED_INSTRUCTIONS and nothing else changes
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
    mem.answer("u", question); mem.close()
    gate_calls = [c for c in llm.calls if c["role"] == "gate"]
    if len(gate_calls) != 1:
        raise RuntimeError(f"expected exactly one gate call at the boundary, saw {len(gate_calls)}")
    c = gate_calls[0]
    frozen = hashlib.sha256((c["system"] + "\n\x00\n" + c["prompt"]).encode()).hexdigest()
    return {"system": c["system"], "prompt": c["prompt"], "digest": frozen,
            "config": {"question": question, "max_subgraph_edges": max_subgraph_edges, "compilation": "on"}}


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
    b_system, b_prompt = baseline_transform(shipped["system"], shipped["prompt"])
    baseline = {"system": b_system, "prompt": b_prompt, "digest": hashlib.sha256((b_system + "\n\x00\n" + b_prompt).encode()).hexdigest()}
    problems = check(shipped, baseline)
    control = check(heading_without_body_control(shipped), baseline)
    return {"shipped": shipped, "baseline": baseline, "problems": problems,
            "control_refuses": bool(control), "control_problems": control, "changed_instructions": CHANGED_INSTRUCTIONS}


if __name__ == "__main__":
    r = run()
    print("--- captured shipped (system):", r["shipped"]["system"][:90], "…")
    print("--- captured shipped (prompt):"); print(r["shipped"]["prompt"])
    print("--- baseline (prompt):"); print(r["baseline"]["prompt"])
    print("--- evidence units (shipped):", evidence_units(r["shipped"]["prompt"]))
    print("CHANGED INSTRUCTIONS:"); [print("  -", c) for c in r["changed_instructions"]]
    print("ARM CHECK:", "PASS" if not r["problems"] else r["problems"])
    print("HEADING-WITHOUT-BODY CONTROL:", "REFUSES (correct)" if r["control_refuses"] else "WRONG: passed")
    sys.exit(0 if not r["problems"] and r["control_refuses"] else 1)
