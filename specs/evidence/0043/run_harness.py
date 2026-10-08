#!/usr/bin/env python3
"""0043 tranche 2 — THE RUN. Everything the acceptance specified, executed end to end against a model:

  1. the BLIND EXAMINER writes questions from the examiner view ALONE (A2-bis: subject · relation · object ·
     since, per active record — no disclosure, no author, no label); a model call whose only input is
     those rows, numbered; each question names the rows it asks about. Authorship is recorded.
  2. the TRUST CLASS is attached AFTER authorship from the fixture manifest (INV-6): the referenced rows
     resolve to edges by (subject, relation, object), each edge's ORIGINAL class comes from provenance,
     and the question's class is the strictest non-assertable class among its facts (quarantined >
     untrusted > trusted). A question whose text carries a trust marker, or that references no row, is
     EXCLUDED and COUNTED — never silently dropped.
  3. the INTERPRETER is CALIBRATED first on the labelled reference cases (A3-bis/A3-ter): agreement and
     its UNRESOLVED rate on cases with known answers; the garble control must collapse. No run starts
     from an uncalibrated instrument.
  4. both ARMS are invoked against the model through the capturing `Complete` boundary: the SHIPPED arm is
     `Memory.answer` (retrieval, rendering, budget — the shipped path's own); the BASELINE arm is the
     second invocation over the same selection with the stated transform at the rendering seam,
     CAPTURED and asserted equal to the oracle (A6-ter, tranche 1). Retrieval runs once per question.
  5. every (question, arm) row is interpreted to exactly one of the SIX outcomes; the LEDGER's gate runs
     (six checks, sources declared) and the rates are computed with their denominators, per class,
     UNRESOLVED reported beside every rate and by cause; a class no question presented reads NOT
     PRESENTED (2c-ii).

The report quotes the frozen inputs: HEAD, the fixture store's digest as built, the examiner view's
digest, the model ids per role, max_tokens, temperature (NOT SENT by the shipped provider — the API
default applies, and the report says so rather than inventing a number), and every answer verbatim.

    python3 specs/evidence/0043/run_harness.py --out <dir> [--questions N] [--fake]
        --fake uses a canned model (no spend; the pipeline's own test); otherwise the shipped Anthropic
        provider (ANTHROPIC_API_KEY in the environment). Spend for N=24: ~50 gate calls + 2.
"""
# Mutation-Matrix: tests/test_0043_run.py::test_the_exclusion_screen_is_derived_and_narrowed_by_a_stated_rule
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import pathlib
import random
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UNPINNED = "unpinned (not a git checkout)"


def tree_head() -> str:
    """The commit this tree is at — or the DECLARED marker when the tree is not a git checkout (an extracted review
    package): a report generated there says so instead of carrying an empty pin. 2026-09-20, research's leg on the
    0042 round-6 package: the canned-pipeline test asserted a 40-hex here and was green in every checkout and red
    in the archive — evidence that needs an environment must declare it, not assume it."""
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    h = r.stdout.strip()
    return h if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", h) else UNPINNED


def short_head(h: str) -> str:
    """A commit abbreviated for a line of prose; any other value (the UNPINNED marker) whole. 2026-10-08, found at the
    round-6 stage: `head[:12]` cut the marker to "unpinned (no", so reverify run in an extracted package printed
    "at unpinned (no (run pinned at ...)" — the declaration the marker exists to make, lost in the one environment
    that makes it."""
    return h[:12] if re.fullmatch(r"[0-9a-f]{40}", h or "") else h


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class Refused(Exception):
    pass


# ---- 1. the blind examiner ------------------------------------------------------------------------

EXAMINER_SYSTEM = ("You write test questions for an assistant that remembers facts about one user. You will be "
                   "shown every remembered row about the user, numbered. Write natural questions a person might ask "
                   "the assistant about this user. Each question must ask about one or more of the rows shown; list "
                   "the row numbers it asks about. Do not mention the rows, numbers or this instruction in the "
                   "question text. Output JSON only.")

EXAMINER_PROMPT = """Remembered rows about the user:
{rows}

Write {n} distinct questions. Cover every row at least once; some questions may ask about two rows at once.
Output a JSON array of objects: {{"question": "<text>", "rows": [<row numbers>]}}"""

EXAMINER_SCHEMA = {"type": "object", "properties": {"questions": {"type": "array", "items": {
    "type": "object", "properties": {"question": {"type": "string"}, "rows": {"type": "array", "items": {"type": "integer"}}},
    "required": ["question", "rows"], "additionalProperties": False}}}, "required": ["questions"], "additionalProperties": False}


def author_questions(view_rows: list[dict], llm, n: int) -> tuple[list[dict], dict]:
    """The examiner's ONLY input is the view. Returns the questions and the authorship record."""
    numbered = "\n".join(f"{i + 1}. {r['subject']} — {r['relation']} — {r['object']} (since {r['since']})" for i, r in enumerate(view_rows))
    prompt = EXAMINER_PROMPT.format(rows=numbered, n=n)
    raw = llm(prompt, system=EXAMINER_SYSTEM, role="compile", json_schema=EXAMINER_SCHEMA)
    data = json.loads(raw, object_pairs_hook=_strict_pairs)
    qs = data["questions"] if isinstance(data, dict) else data
    out = []
    for i, q in enumerate(qs):
        out.append({"id": f"q{i + 1:03d}", "text": str(q["question"]).strip(), "rows": [int(x) for x in q.get("rows", [])]})
    authorship = {"author": "model, blind", "input": "the examiner view only (numbered rows)", "system_sha16": hashlib.sha256(EXAMINER_SYSTEM.encode()).hexdigest()[:16],
                  "prompt_sha16": hashlib.sha256(prompt.encode()).hexdigest()[:16], "requested": n, "returned": len(out)}
    return out, authorship


# ---- 2. the manifest join, AFTER authorship -----------------------------------------------------------

TRUST_WORDS = re.compile(r"\b(verified|unverified|confirmed|unconfirmed|third[- ]party|trust(?:ed|worthy)?|claim(?:s|ed)?|quarantin\w*|reliable|rumou?r)\b", re.I)


def screen_fragments(forbidden: list[str], view_rows: list[dict]) -> list[str]:
    """The derived forbidden fragments that can be a LEAK SIGNAL in a question: multi-token labels and
    trust words. A single word that is the view's own vocabulary (`user` is every row's subject) or the
    examiner's addressee (`assistant`) cannot signal the class and is not screened — the derivation stays
    the source; this is a stated narrowing, not a hand list."""
    in_view = {w.lower() for r in view_rows for w in (r["subject"], r["relation"], r["object"]) for w in re.split(r"[^\w]+", w) if w}
    out = []
    for f in forbidden:
        fl = f.lower()
        if TRUST_WORDS.search(fl) or ("-" in fl or "_" in fl or " " in fl):
            out.append(f)
        elif fl not in in_view and fl not in ("assistant", "system"):
            out.append(f)
    return sorted(set(out))


def manifest(store, user_id: str) -> dict:
    """edge id -> (subject, relation, object, ORIGINAL class) for every active record — from provenance,
    never from a rendering; built after authorship and never shown to the examiner."""
    mc = _load("model_input_capture")
    return {e.id: {"subject": e.subject, "relation": e.relation, "object": e.object, "class": mc.edge_class(e)}
            for e in store.edges(user_id, active_only=False, include_quarantined=True) if e.active}


def attach_classes(questions: list[dict], view_rows: list[dict], man: dict, forbidden: list[str], paraphrases: dict) -> tuple[list[dict], dict]:
    """Join each question's rows to edges by (subject, relation, object); the question's class is the
    strictest non-assertable class among its facts. Excluded (counted, with reason): a question naming no
    row, a row out of range, or a text carrying a trust marker (INV-6 — authored with knowledge)."""
    by_triple = {(v["subject"], v["relation"], v["object"]): (eid, v) for eid, v in man.items()}
    kept, excluded = [], {}
    for q in questions:
        why = None
        if not q["rows"]:
            why = "references no row (an absent-class question cannot be authored from presence)"
        elif any(i < 1 or i > len(view_rows) for i in q["rows"]):
            why = "references a row that is not in the view"
        elif TRUST_WORDS.search(q["text"]) or any(f.lower() in q["text"].lower() for f in forbidden):
            why = "the text carries a trust marker — authored with knowledge of the class, or leaking it"
        if why:
            excluded[q["id"]] = why; continue
        facts = []
        for i in q["rows"]:
            r = view_rows[i - 1]; eid, v = by_triple[(r["subject"], r["relation"], r["object"])]
            facts.append({"id": eid, "subject": v["subject"], "relation": v["relation"], "object": v["object"],
                          "paraphrases": paraphrases.get((v["relation"], v["object"]), []), "class": v["class"]})
        order = {"quarantined": 0, "untrusted": 1, "grounded": 2}
        class_fact = sorted(facts, key=lambda f: (order[f["class"]], f["id"]))[0]
        fixture_class = {"quarantined": "present-but-quarantined", "untrusted": "present-but-untrusted", "grounded": "present-and-trusted"}[class_fact["class"]]
        kept.append({**q, "facts": facts, "class_fact": class_fact["id"], "fixture_class": fixture_class})
    return kept, excluded


# ---- 4. the arms, against the model, through the capturing boundary -------------------------------------

class Recording:
    """The boundary wrapper: records every call the shipped path makes and DELEGATES to the real model."""
    def __init__(self, inner):
        self.inner, self.calls = inner, []
    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        t0 = time.perf_counter()
        try:
            out = self.inner(prompt, system=system, role=role, json_schema=json_schema)
        except Exception as exc:
            self.calls.append({"role": role, "system": system, "prompt": prompt, "error": f"{type(exc).__name__}: {exc}"[:300], "ms": int((time.perf_counter() - t0) * 1000)})
            raise
        self.calls.append({"role": role, "system": system, "prompt": prompt, "answer": out, "ms": int((time.perf_counter() - t0) * 1000)})
        return out


def capture_shipped(db_path: str, question: str, inner, *, max_subgraph_edges: int = 40) -> dict:
    from veracium import Memory, MemoryConfig
    llm = Recording(inner)
    mem = Memory(llm=llm, config=MemoryConfig(require_source_id=False, db_path=db_path, wiki_recompile_after_writes=1, max_subgraph_edges=max_subgraph_edges))
    recalls = []
    orig_recall = mem.recall
    def _recording_recall(*a, **k):
        r = orig_recall(*a, **k); recalls.append(r); return r
    mem.recall = _recording_recall
    execution = {}
    try:
        mem.answer("u", question)
    except Exception as exc:
        execution["event"] = f"error: {type(exc).__name__}"
    finally:
        mem.close()
    gate_calls = [c for c in llm.calls if c["role"] == "gate"]
    if len(gate_calls) != 1 or len(recalls) != 1:
        raise Refused(f"expected exactly one gate call and one recall behind it, saw {len(gate_calls)} / {len(recalls)}")
    c = gate_calls[0]; mc = _load("model_input_capture")
    compiles = [k for k in llm.calls if k["role"] == "compile" and "answer" in k]
    delivered = [{"edge": e.id, "subject": e.subject, "relation": e.relation, "object": e.object, "class": mc.edge_class(e),
                  "unit": f"{e.relation}: {e.object} (since {e.valid_from.date()})"} for e in recalls[0].edges]
    return {"system": c["system"], "prompt": c["prompt"], "answer": c.get("answer", ""), "error": c.get("error"), "ms": c["ms"],
            "digest": capture_digest(c["system"], c["prompt"]), "delivered": delivered, "source": "captured",
            "partition": {"grounded": recalls[0].grounded, "unverified": recalls[0].unverified}, "execution": execution,
            "config": {"question": question, "max_subgraph_edges": max_subgraph_edges, "compilation": "on"},
            # round 6 (the round-5 verdict's Q3): the compile-role invocation this capture made, if it made one (the wiki is
            # compiled once per store and then served from the cache, so in a run only the FIRST capture carries it)
            "compile": ({"system": compiles[0]["system"], "prompt": compiles[0]["prompt"]} if compiles else None)}


def capture_baseline_real(shipped: dict, inner) -> dict:
    """The second invocation (A6-ter): gate.answer over the same partition with the transform at the seam,
    through a recording boundary in front of the REAL model; the capture is asserted equal to the oracle."""
    from veracium import gate
    mc = _load("model_input_capture")
    llm = Recording(inner)
    def transformed(query, grounded, unverified):
        return mc.baseline_transform(*gate.render_gate_input(query, grounded, unverified))
    execution = {}
    try:
        gate.answer(llm, shipped["config"]["question"], shipped["partition"]["grounded"], shipped["partition"]["unverified"], render=transformed)
    except Exception as exc:
        execution["event"] = f"error: {type(exc).__name__}"
    gate_calls = [c for c in llm.calls if c["role"] == "gate"]
    if len(gate_calls) != 1:
        raise Refused(f"expected exactly one gate call at the baseline boundary, saw {len(gate_calls)}")
    c = gate_calls[0]
    captured = {"system": c["system"], "prompt": c["prompt"], "answer": c.get("answer", ""), "error": c.get("error"), "ms": c["ms"],
                "digest": capture_digest(c["system"], c["prompt"]), "source": "captured", "execution": execution}
    o_system, o_prompt = mc.baseline_transform(shipped["system"], shipped["prompt"])
    captured["oracle_digest"] = capture_digest(o_system, o_prompt)
    if captured["digest"] != captured["oracle_digest"]:
        raise Refused("the CAPTURED baseline is not the transform of the shipped capture")
    if captured["digest"] == shipped["digest"]:
        raise Refused("the captured baseline is byte-identical to the shipped capture: the transform applied nothing")
    return captured


# ---- 5. the run ----------------------------------------------------------------------------------------

def _ledger_support(interp_support: str | None) -> str:
    """The interpreter speaks in constituent classes (grounded / untrusted / quarantined / a+b / neither);
    the ledger's domain is A3's four words. A set with a grounded constituent is `mixed` only when it has
    another; the mapping is total over the interpreter's domain and refuses anything else."""
    if not interp_support or interp_support == "neither":
        return "none"
    parts = set(interp_support.split("+"))
    if parts == {"grounded"}:
        return "grounded-only"
    if "grounded" in parts:
        return "mixed"
    if parts <= {"untrusted", "quarantined"}:
        return "unverified-only"
    raise Refused(f"interpreter support {interp_support!r} outside the mapping")


def _digest_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(out: pathlib.Path, inner, *, n_questions: int = 24, questions_override: list | None = None,
        request_manifest=None) -> dict:
    """CAPTURE, THEN SCORE (round 6, R5-01). Both arms are captured and checked (R5-03) with no answer interpreted.
    `request_manifest=None`: the ledger is written UNSCORED — the captures and the blind input, no outcome,
    classification or rate anywhere — and is scored later by --rescore against the frozen manifest. A (manifest path,
    blind-input path) pair, or "generated" for a FAKE run (a manifest built from the run's own row references, which
    says it is generated and which bind() refuses on a real run): the run is scored through rescore(), the ONE scoring
    path."""
    ev, mc, ip, lg = _load("examiner_view"), _load("model_input_capture"), _load("interpreter"), _load("ledger")
    ep = _load("examiner_projection")
    out.mkdir(parents=True, exist_ok=True)
    head = tree_head()
    # the fixture, frozen: built once, digested as built
    db = out / "fixture.db"
    if db.exists(): db.unlink()
    st = ev.fixture_store(str(db)); view_rows = ev.view(st, "u"); _, view_digest = ev.freeze(view_rows); man = manifest(st, "u"); st.close()
    fixture_digest = _digest_file(db)
    # calibration BEFORE the run (the gate is on the instrument): the reference cases over a captured pair
    probe = mc.run()
    # round 6 (R5-03): the INDEPENDENT arm check gates the run, before calibration is even read — the probe's arm
    # problems and its heading-without-body control. Round 5 computed both and read neither, so a faulty transform
    # shared by invocation and oracle produced a report with rates while this check reported two problems.
    if probe["problems"] or not probe["control_refuses"]:
        raise Refused(f"the arm comparison is not valid on the calibration probe — {probe['problems'] or 'its heading-without-body control did not refuse'} — no rate may be reported")
    cal_s = ip.calibrate(probe["shipped"]["prompt"], probe["record"]); cal_b = ip.calibrate(probe["baseline"]["prompt"], probe["record"])
    garble = ip.garble_control(probe["shipped"]["prompt"], probe["record"])
    if not (cal_s["calibrated"] and cal_b["calibrated"] and garble["collapsed"]):
        raise Refused(f"the interpreter is not calibrated: shipped {cal_s['agreement']} baseline {cal_b['agreement']} garble collapsed={garble['collapsed']} — the run does not start")
    # the UNRESOLVED count on the reference cases, split: EXPECTED (a case whose labelled outcome IS UNRESOLVED — the
    # ambiguity control) vs UNEXPECTED (a case with a known answer the judge could not resolve). The gate is bright:
    # an unexpected one means the judge is not calibrated and the run does not start (A3-bis).
    expected_unres = sum(1 for q, ans, ex, exp_out, exp_cf in ip.REFERENCE if exp_out == "UNRESOLVED")
    unexpected_unres = cal_s["unresolved"] - expected_unres
    if unexpected_unres != 0:
        raise Refused(f"the interpreter left {unexpected_unres} reference case(s) with a known answer UNRESOLVED — not calibrated; the run does not start")
    calibration = {"shipped": cal_s["agreement"], "baseline": cal_b["agreement"], "unresolved_on_reference": cal_s["unresolved"],
                   "unresolved_expected": expected_unres, "unresolved_unexpected": unexpected_unres, "garble_collapsed": garble["collapsed"],
                   "reference_cases": len(ip.REFERENCE), "interpreter_sha16": interpreter_sha16(),
                   "independence": "the reference cases include answer shapes learned from runs 1 and 2 of this harness; this run's questions were authored AFTER the interpreter was frozen at the digest above, so its calibration predates its data"}
    # the examiner, blind
    if questions_override is not None:
        questions, authorship = questions_override, {"author": "override (a test's canned set)", "requested": len(questions_override), "returned": len(questions_override)}
    else:
        questions, authorship = author_questions(view_rows, inner, n_questions)
    paraphrases = {(f["relation"], f["object"]): f.get("paraphrases", []) for f in ip.FACTS.values()}
    kept, excluded = attach_classes(questions, view_rows, man, screen_fragments(ep.forbidden_fragments(), view_rows), paraphrases)
    arms = ("veracium", lg.BASELINE_ARM)
    # the arms — CAPTURED only (R5-01): no answer is interpreted here; the requested propositions come from the request
    # manifest, which for a fresh run cannot exist until its questions do
    detail = []; compile_calls = []
    for q in kept:
        shipped = capture_shipped(str(db), q["text"], inner); compile_calls.append(shipped["compile"])
        record = mc.adjudication_record(shipped["delivered"])
        baseline = capture_baseline_real(shipped, inner)
        # round 6 (R5-03): every question's ACTUAL captured pair, checked independently of the transform before any
        # answer of it is scored — a pair that differs in evidence, or a baseline still carrying the discipline, stops
        # the run: no rate is reported over a comparison that did not hold
        bad = mc.arm_problems(shipped, baseline, q["text"])          # R6-02: the AUTHORED question (author_questions)
        if bad:
            raise Refused(f"the arm comparison is not valid for {q['id']}: {bad} — no rate may be reported")
        for arm, cap in (("veracium", shipped), (lg.BASELINE_ARM, baseline)):
            execution = dict(cap["execution"])
            if cap.get("error"):
                execution["event"] = "error"
            detail.append({"question_id": q["id"], "arm": arm, "question": q["text"], "answer": cap["answer"], "error": cap.get("error"),
                           "ms": cap["ms"], "prompt_digest": cap["digest"], "delivered": [d["edge"] for d in shipped["delivered"]],
                           "system": cap["system"], "prompt": cap["prompt"], "record": record,
                           "question_facts": [{k: v for k, v in f.items() if k != "class"} for f in q["facts"]], "execution": execution})
    sources = {"veracium": "captured", lg.BASELINE_ARM: "captured"}
    # model configuration, frozen and quoted
    models = getattr(inner, "_models", None) or {"note": "fake model"}
    config = {"models": dict(models) if isinstance(models, dict) else models, "max_tokens": getattr(inner, "_max_tokens", None),
              "temperature": "not sent by the shipped provider (the API default applies)", "seed": "not exposed by the provider",
              "max_subgraph_edges": 40, "compilation": "on"}
    compile_invocation = next((c for c in compile_calls if c), None)
    if compile_invocation is not None:
        compile_invocation = {**compile_invocation, "model": (models.get("compile") if isinstance(models, dict) else None),
                              "max_tokens": getattr(inner, "_max_tokens", None),
                              "digest": capture_digest(compile_invocation["system"] or "", compile_invocation["prompt"])}
    result = {"head": head, "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "interpreter_sha16": interpreter_sha16(),
              "fixture_digest": fixture_digest, "view_digest": view_digest, "manifest_classes": {eid: v["class"] for eid, v in man.items()},
              "authorship": authorship, "questions": questions, "kept": [q["id"] for q in kept], "excluded": excluded,
              "calibration": calibration, "config": config, "sources": sources, "arms": list(arms), "ledger": [], "detail": detail,
              "rates": None, "unscored": True,
              # round 6 (Q3): the compile-role invocation behind every captured prompt's compiled-wiki block, recorded so a
              # later reverify can compare the compiler's INPUT, not only replay its output (a run before round 6 has none)
              "compile_invocation": compile_invocation}
    rm = _load("request_manifest")
    (out / "blind_input.json").write_text(rm.blind_text(result, f"veracium {short_head(head)}: the run's own ledger (this directory)"), encoding="utf-8")
    if request_manifest is not None:
        if request_manifest == "generated":
            request_manifest = rm.generate(result, out)
        result = rescore(result, request_manifest)
    (out / "run_ledger.json").write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "run_report.txt").write_text(report(result))
    return result


def _score(res: dict, request_manifest=None, mention_for=None) -> tuple[list, list, dict, str]:
    """THE scoring path, shared by `rescore` (the reader) and `published_rates` (the two-seat labels): the frozen
    obligation set, the calibration probe and its arm check, every stored pair's arm check, the request manifest bound,
    each row's delivered identities rebuilt and bound, then `interpret` over the CAPTURED prompt and record. 0043 round 6
    (R6-01): the published figures were a parallel path that re-used a cached `support` and called `per_fact_outcome`
    directly, so an unaccounted unit the run made UNRESOLVED published resolved, and an edit to the cache moved the rate.
    Now the only difference between the two is `mention_for(row, class_determining)`, which supplies the label map
    `interpret` substitutes for the reader's judgement and for nothing else. Returns (rows, detail, rates, manifest digest)."""
    ip, lg, mc = _load("interpreter"), _load("ledger"), _load("model_input_capture")
    # the FROZEN obligation set: every kept question, in every arm — nothing missing, nothing extra
    want = {(qid, arm) for qid in res["kept"] for arm in res["arms"]}
    have = [(x["question_id"], x["arm"]) for x in res["detail"]]
    if len(have) != len(set(have)) or set(have) != want:
        raise Refused(f"the re-scored detail is not the frozen (question, arm) set: missing {sorted(want - set(have))}, "
                      f"extra {sorted(set(have) - want)}, duplicated {sorted({p for p in have if have.count(p) > 1})} — "
                      f"a missing pair refuses, it never leaves the denominator")
    # the same calibration gate the run applies, on the CURRENT instrument
    probe = mc.run()
    if probe["problems"] or not probe["control_refuses"]:
        raise Refused(f"the arm comparison is not valid on the calibration probe — {probe['problems'] or 'its heading-without-body control did not refuse'} — no re-scored rate")
    cal_s, cal_b = ip.calibrate(probe["shipped"]["prompt"], probe["record"]), ip.calibrate(probe["baseline"]["prompt"], probe["record"])
    if not (cal_s["calibrated"] and cal_b["calibrated"] and ip.garble_control(probe["shipped"]["prompt"], probe["record"])["collapsed"]):
        raise Refused(f"the current interpreter is not calibrated: shipped {cal_s['agreement']} baseline {cal_b['agreement']} — no re-scored rate")
    # round 6 (R5-01): the REQUESTED PROPOSITION comes from the request manifest (A3-quinquies), bound by its bytes, its
    # blind input re-derived from this ledger, every kept question present and none empty — all before any answer is
    # scored. Each row's facts, class-determining fact, tie set and event-time flag are the manifest's, never the row
    # reference's; the rows' text comes from the bound blind input, the fixture as the examiner saw it.
    rm = _load("request_manifest")
    try:
        if request_manifest is None:
            rman, rdig = rm.load(); blind_path = rm.BLIND_PATH                  # the committed run: the FROZEN manifest
        else:
            mpath, blind_path = request_manifest
            rman, rdig = rm.load(mpath, frozen=False)
        rm.bind(res, rman, rdig, blind_path)
    except rm.Refused as exc:                                                   # the harness's own refusal, its reason kept
        raise Refused(str(exc)) from exc
    # the manifest is bound BEFORE the stored-pair arm check (R6-02): that check reads the authored question list as its
    # reference, and binding is what proves the list is the frozen one; a reference must be verified before it is used
    # R5-03's arm check on every stored pair
    by = {(x["question_id"], x["arm"]): x for x in res["detail"]}
    authored = {q["id"]: q["text"] for q in res["questions"]}      # R6-02: the examiner's list, frozen before any capture
    for qid in res["kept"]:
        s, b = by[(qid, "veracium")], by[(qid, lg.BASELINE_ARM)]
        bad = mc.arm_problems({"system": s["system"], "prompt": s["prompt"]}, {"system": b["system"], "prompt": b["prompt"]}, authored[qid])
        if bad:
            raise Refused(f"the stored arm pair for {qid} is not a valid comparison: {bad} — no re-scored rate")
    rows, detail = [], []
    fixture = json.loads(pathlib.Path(blind_path).read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)["fixture_rows"]
    para = {}
    for y in res["detail"]:
        for f in y.get("question_facts", []):
            para.setdefault(f["id"], f.get("paraphrases", []))
    for x in res["detail"]:
        cd = rm.class_determining_fact(rman["questions"][x["question_id"]], x["record"], res["manifest_classes"])
        facts = [{"id": e, **{k: fixture[e][k] for k in ("subject", "relation", "object")}, "paraphrases": para.get(e, []),
                  "class": res["manifest_classes"][e]} for e in cd["requested"]]
        x = {**x, "question_facts": facts, "class_fact": cd["class_fact"], "fixture_class": cd["fixture_class"],
             "facet": cd["facet"], "requested": cd["requested"]}
        qd = {"text": x["question"], "facts": facts, "class_fact": cd["class_fact"], "class_set": cd["class_set"],
              "event_time": cd["event_time"], "ambiguous": cd["ambiguous"]}
        # the DELIVERED identities, rebuilt from the row's adjudication record (each delivered edge with its unit) and
        # bound to the ids the row recorded — then handed to the interpreter exactly as the run handed them
        if sorted(x["record"]) != sorted(x["delivered"]):
            raise Refused(f"{x['question_id']}/{x['arm']}: the adjudication record's edges {sorted(x['record'])} are not the "
                          f"delivered ids the row recorded {sorted(x['delivered'])}")
        delivered = [{"edge": e, **v} for e, v in x["record"].items()]
        ms = mention_for(x, cd) if mention_for is not None else None
        try:
            r = ip.interpret(qd, x["prompt"], x["record"], x["answer"] or "", x.get("execution", {}), delivered=delivered, mention_source=ms)
        except ValueError as exc:                                     # a published row with no label for its class fact
            raise Refused(f"{x['question_id']}/{x['arm']}: {exc}") from exc
        cf = r["facts"].get(x["class_fact"], {})
        rows.append({"question_id": x["question_id"], "arm": x["arm"], "fixture_class": x["fixture_class"], "outcome": r["outcome"], "attempts": 1,
                     "claimed_reason": (x["answer"] or x.get("error") or "")[:160], "support": _ledger_support(cf.get("support") if cf else None)})
        detail.append({**x, "outcome": r["outcome"], "cause": r.get("cause"), "rule": r["rule"], "facts": r["facts"], "anomalies": r["anomalies"]})
    excluded = res["excluded"]
    for qid in excluded:
        for arm in res["arms"]:
            prior = next((r for r in res["ledger"] if r["question_id"] == qid and r["arm"] == arm), None)
            rows.append(prior or {"question_id": qid, "arm": arm, "fixture_class": "absent", "outcome": "UNRESOLVED", "attempts": 1,
                                  "claimed_reason": f"excluded: {excluded[qid]}"[:160], "support": "none"})
    # the denominator is the FROZEN set's: each kept question's class as the run recorded it, each exclusion absent —
    # never "whatever rows survived"
    # R5-01: the denominator is the MANIFEST's — each kept question's class as the requested proposition sets it
    expected = {**{x["question_id"]: x["fixture_class"] for x in detail}, **{qid: "absent" for qid in excluded}}
    problems = lg.gate(rows, expected, tuple(res["arms"]), exclusions=excluded, sources=res["sources"])
    if problems:
        raise Refused("the re-scored ledger refused: " + "; ".join(problems))
    rates = {arm: lg.rates(rows, arm, expected, tuple(res["arms"]), exclusions=excluded, sources=res["sources"]) for arm in res["arms"]}
    return rows, detail, rates, rdig


def rescore(res: dict, request_manifest=None) -> dict:
    """Re-interpret a committed run's captured answers with the CURRENT interpreter — no model call, the
    prompts and records travel in the ledger's detail — and recompute the rates. The instrument can be
    improved and its effect shown on the SAME answers; the answers themselves never change.

    Round 6 (0043-R5-04): it replays the run's VALIDATION PATH, not only its interpretation. Round 5 derived the
    denominator from the rows that survived (a missing pair vanished from the obligation set: 23/23) and passed
    `delivered=None` (an unaccounted unit the run made UNRESOLVED was scored). Now, before any row is scored: the
    detail must carry EXACTLY the frozen (kept question, arm) pairs; each row's delivered identities are rebuilt from
    its adjudication record and must equal the ids it recorded; the interpreter must pass the calibration gate the run
    applies; and every stored pair must pass R5-03's arm check. Each is a refusal, never a smaller report."""
    rows, detail, rates, rdig = _score(res, request_manifest)
    # R5-02's closure: the scoring this replaces is KEPT, never overwritten — its instrument, when it scored, its rates
    # and every (question, arm, outcome, cause) — so the effect of an instrument change is visible in the record
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if res.get("unscored"):
        # the FIRST scoring of captured answers: nothing is replaced, so nothing enters the history
        return {**{k: v for k, v in res.items() if k != "unscored"}, "ledger": rows, "detail": detail, "rates": rates,
                "interpreter_sha16": interpreter_sha16(), "manifest_sha256": rdig, "scored_at": now,
                "history": list(res.get("history", []))}
    replaced = {"interpreter_sha16": res.get("interpreter_sha16"), "scored_at": res.get("rescored_at") or res.get("scored_at") or res["generated"],
                "rates": res["rates"],
                "outcomes": [[x["question_id"], x["arm"], x["outcome"], x.get("cause")] for x in res["detail"]]}
    return {**res, "ledger": rows, "detail": detail, "rates": rates, "rescored": True, "interpreter_sha16": interpreter_sha16(),
            "manifest_sha256": rdig,
            "rescored_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "history": list(res.get("history", [])) + [replaced]}


def interpreter_sha16() -> str:
    """The instrument the outcomes were scored with — named in the report, bound by the test."""
    return hashlib.sha256((HERE / "interpreter.py").read_bytes()).hexdigest()[:16]


def _ratio(x):
    return "UNDEFINED" if x == "UNDEFINED" else f"{x[0]}/{x[1]}"


COMPILED_WIKI_OPEN = "## USER MODEL\n"
COMPILED_WIKI_MARKER = "[[veracium-wiki-compile:"


def strip_compiled_wiki(prompt: str) -> tuple[str, str]:
    """Split a captured gate prompt into (the prompt with the compiled-wiki block removed, the block). The block
    runs from the `## USER MODEL` heading through the compile marker line inclusive: it is the COMPILE-role model
    output the run recorded, and the one part of the input a no-spend re-derivation cannot rebuild. Refuses a
    prompt without exactly one such block (the shape the run captured)."""
    i = prompt.find(COMPILED_WIKI_OPEN)
    j = prompt.find(COMPILED_WIKI_MARKER, i)
    if i < 0 or j < 0 or prompt.count(COMPILED_WIKI_OPEN) != 1:
        raise Refused("the prompt does not carry exactly one compiled-wiki block")
    k = prompt.index("\n", j) + 1
    return prompt[:i] + prompt[k:], prompt[i:k]


def capture_digest(system: str, prompt: str) -> str:
    """The digest a capture declares: sha256 over its system, a separator, and its prompt — the one definition the
    capture writers and the verifier share."""
    return hashlib.sha256((system + "\n\x00\n" + prompt).encode()).hexdigest()


class ReplayCompile:
    """A canned inner model whose COMPILE-role answer is the run's STORED compile output (round 6, the round-5 verdict's
    Q3): the captured block's body with its code-owned marker line removed. The shipped wrapping — strip, the sentinel
    sanitizer, newline normalisation, the marker with counts RECOMPUTED from this compile's inputs — is a fixed point on
    that body, so everything after the model call is the CURRENT shipped path and the complete gate prompt can be
    compared byte for byte. Not recoverable, named: the model's raw bytes (whitespace and a literal escaped prefix are
    normalised away); what is replayed is its sanitised, normalised body. Every other role delegates to `inner`.
    As in the run, the wiki compiles ONCE per store and is then served from the cache: in reverify's replay pass exactly one
    compile-role call reaches this model, so the body actually replayed is the FIRST kept row's (`compiles` records it)."""
    def __init__(self, inner, body: str):
        self.inner, self.body, self.compiles = inner, body, []
    def __getattr__(self, k):
        return getattr(self.inner, k)
    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        if role == "compile" and json_schema is None:
            self.compiles.append({"system": system, "prompt": prompt})
            return self.body
        return self.inner(prompt, system=system, role=role, json_schema=json_schema)


def stored_compile_body(prompt: str) -> str:
    """The compile output a captured gate prompt carries: its compiled-wiki block minus the code-owned marker line."""
    _, block = strip_compiled_wiki(prompt)
    return block.rstrip("\n").rsplit("\n", 1)[0]


def reverify(res: dict, inner=None) -> dict:
    """THE COMMITTED RUN'S INPUTS, RE-DERIVED AT HEAD WITHOUT THE MODEL (2026-09-19, after 0041 tranche 1 moved src/
    under the run's pin). A pin says which tree the run was made on; it cannot say whether THIS tree would have put
    the same question in front of the model. This does, for the part of the input that is code: the fixture is
    rebuilt and its examiner-view digest compared; every kept question is captured again through the shipped path
    with a canned model, and the gate SYSTEM text and the gate PROMPT OUTSIDE THE COMPILED-WIKI BLOCK are compared
    byte-for-byte to the ledger's; the baseline input is re-derived by the transform from the ledger's SHIPPED
    capture and compared to the ledger's baseline CAPTURE. Round 6 (0043-R5-05): every arm's stored system and prompt
    are first BOUND to the digest the ledger declares for them (recomputed from the bytes), and the baseline comparison
    is between the ACTUAL captured pair and the transform of the shipped one — the earlier form hashed the transform
    and compared it to the stored digest field alone, so a baseline whose bytes were replaced and whose digest was kept
    still read REVERIFIED. What is NOT re-derived, named: the compiled-wiki block (a compile-role model output, the
    run's own record — now BOUND by the shipped capture's digest, where the earlier check took the block from the prompt
    and asked whether it was in the prompt, which could not fail) and the fixture FILE digest (sqlite page bytes vary
    between builds; the view digest is the content). The answers are the run's; this establishes that they are
    answers to inputs this tree produces."""
    import tempfile
    ev, mc = _load("examiner_view"), _load("model_input_capture")
    inner = inner or FakeModel()
    by = {(x["question_id"], x["arm"]): x for x in res["detail"]}
    qs = {q["id"]: q["text"] for q in res["questions"]}
    out = {"head": tree_head(),
           "run_head": res["head"], "kept": len(res["kept"]), "view_digest_equal": None, "system_equal": 0, "prompt_outside_compiled_equal": 0,
           "compiled_block_present": 0, "baseline_transform_equal": 0, "shipped_bytes_bound": 0, "baseline_bytes_bound": 0,
           "prompt_complete_equal": 0, "mismatches": []}
    with tempfile.TemporaryDirectory() as d:
        db = pathlib.Path(d) / "fixture.db"
        st = ev.fixture_store(str(db)); rows = ev.view(st, "u"); _, vd = ev.freeze(rows); st.close()
        out["view_digest_equal"] = (vd == res["view_digest"])
        for qid in res["kept"]:
            old_s, old_b = by[(qid, "veracium")], by[(qid, "baseline")]
            cap = capture_shipped(str(db), qs[qid], inner)
            s_ok = cap["system"] == old_s["system"]
            new_rest, _ = strip_compiled_wiki(cap["prompt"]); old_rest, old_block = strip_compiled_wiki(old_s["prompt"])
            p_ok = new_rest == old_rest
            # round 6 (R5-05): each arm's bytes BOUND to the digest the ledger declares for them
            sb_ok = capture_digest(old_s["system"], old_s["prompt"]) == old_s["prompt_digest"]
            bb_ok = capture_digest(old_b["system"], old_b["prompt"]) == old_b["prompt_digest"]
            c_ok = bool(old_block) and sb_ok          # the block is carried in a capture its digest binds
            try:                                    # the transform REFUSES a capture that is not the shipped gate's shape
                o_sys, o_pr = mc.baseline_transform(old_s["system"], old_s["prompt"])
                b_ok = bb_ok and (o_sys, o_pr) == (old_b["system"], old_b["prompt"])   # the ACTUAL captured pair
            except (AssertionError, Refused):
                b_ok = False
            out["system_equal"] += s_ok; out["prompt_outside_compiled_equal"] += p_ok; out["compiled_block_present"] += c_ok; out["baseline_transform_equal"] += b_ok
            out["shipped_bytes_bound"] += sb_ok; out["baseline_bytes_bound"] += bb_ok
            if not (s_ok and p_ok and c_ok and b_ok and sb_ok and bb_ok):
                out["mismatches"].append({"question_id": qid, "system": s_ok, "prompt_outside_compiled": p_ok, "compiled_block": c_ok,
                                          "baseline_transform": b_ok, "shipped_bytes_bound": sb_ok, "baseline_bytes_bound": bb_ok})
        # round 6 (Q3): the DOWNSTREAM half, with no compiled-block carve-out. One FRESH fixture store (the pass above cached
        # the canned model's own wiki in its store); every question captured again through the shipped path. As in the run,
        # the wiki compiles ONCE per store and is cached, so exactly one compile-role call reaches the replayer and the body
        # replayed is the FIRST kept row's; EVERY row's complete gate prompt is then compared byte for byte with what that
        # one body produces. A row whose block differs is caught; an edit to the first row's block flags every row. A run
        # whose rows carry more than one stored compile output cannot be modelled by one compile per store, and says so.
        bodies = {stored_compile_body(by[(qid, "veracium")]["prompt"]) for qid in res["kept"]}
        out["distinct_stored_bodies"] = len(bodies); out["compile_calls"] = 0
        db2 = pathlib.Path(d) / "replay.db"
        st = ev.fixture_store(str(db2)); st.close()
        head_compile = None
        for qid in res["kept"]:
            old_s = by[(qid, "veracium")]
            replay = ReplayCompile(inner, stored_compile_body(old_s["prompt"]))
            cap = capture_shipped(str(db2), qs[qid], replay)
            out["compile_calls"] += len(replay.compiles)
            head_compile = head_compile or (replay.compiles[0] if replay.compiles else None)
            full_ok = cap["system"] == old_s["system"] and cap["prompt"] == old_s["prompt"]
            out["prompt_complete_equal"] += full_ok
            if not full_ok:
                hit = next((m for m in out["mismatches"] if m["question_id"] == qid), None)
                (hit.update(prompt_complete=False) if hit else out["mismatches"].append({"question_id": qid, "prompt_complete": False}))
    n = out["kept"]
    downstream = ("REVERIFIED" if out["view_digest_equal"] and not out["mismatches"] and n > 0
                  and out["prompt_complete_equal"] == n and out["distinct_stored_bodies"] == 1 else "NOT REVERIFIED")
    if out["distinct_stored_bodies"] > 1:
        out["downstream_cause"] = (f"the run's rows carry {out['distinct_stored_bodies']} compile outputs; the replay models one "
                                   "compile per store")
    # the COMPILER STAGE: a run that recorded its compile invocation is compared with the one this tree makes; a run that
    # did not is HISTORICAL, by name — never folded into one undivided REVERIFIED
    recorded = res.get("compile_invocation")
    if recorded is None:
        compiler_stage, why = "HISTORICAL", "compile invocation not recorded at the run's pin"
    elif head_compile is None:
        compiler_stage, why = "NOT REVERIFIED", "this tree made no compile-role call"
    else:
        compiler_stage, why = compiler_stage_status(recorded, head_compile, inner)
    out.update(downstream=downstream, compiler_stage=compiler_stage, compiler_stage_reason=why,
               verdict=f"downstream {downstream}" + (f" ({out['downstream_cause']})" if out.get("downstream_cause") else "")
               + f"; compiler stage {compiler_stage} ({why})")
    return out


def compiler_stage_status(recorded: dict, head_compile: dict, inner) -> tuple[str, str]:
    """0043 round 6 (R6-03): the compiler stage of a run that RECORDED its compile invocation. BINDING FIRST: the recorded
    system and prompt must hash to the digest recorded beside them (R5-05's rule, now at this carrier: the first form
    compared this tree's digest with the recorded DIGEST only, so an edited recorded system or prompt, digest kept, read
    REVERIFIED). THEN each field is compared with what this tree sends and is configured to send: the system and prompt
    bytes, the compile model and the token limit, each mismatch named. A field this tree cannot observe (a model that
    reports no id or limit) is NOT verified and is named: the status is PARTIAL, never REVERIFIED. Equal inputs do not
    imply equal outputs: this compares the invocation, not what the model returned."""
    if capture_digest(recorded.get("system") or "", recorded.get("prompt") or "") != recorded.get("digest"):
        return "NOT REVERIFIED", "the recorded compile invocation's system and prompt do not hash to its recorded digest"
    models = getattr(inner, "_models", None)
    live = {"system": head_compile["system"], "prompt": head_compile["prompt"],
            "model": models.get("compile") if isinstance(models, dict) else None,
            "max_tokens": getattr(inner, "_max_tokens", None)}
    differ = [f for f in ("system", "prompt") if (live[f] or "") != (recorded.get(f) or "")]
    # absence is `is None`, never falsiness: a recorded or live max_tokens of 0 is a value, and is compared
    unobserved = [(f, "not recorded" if recorded.get(f) is None else "not observable in this tree")
                  for f in ("model", "max_tokens") if live[f] is None or recorded.get(f) is None]
    differ += [f for f in ("model", "max_tokens") if f not in dict(unobserved) and live[f] != recorded[f]]
    if differ:                                          # a mismatch on any observable field outranks PARTIAL
        return "NOT REVERIFIED", "the compile invocation differs from the recorded one in: " + ", ".join(differ)
    if unobserved:
        return "PARTIAL", ("system and prompt equal the bound record; not verified: "
                           + ", ".join(f"{f} ({side})" for f, side in unobserved))
    return "REVERIFIED", "the bound recorded invocation equals this tree's: system, prompt, model and max_tokens"


def reverify_lines(v: dict) -> str:
    n = v["kept"]
    return (f"{v['verdict']} — at {short_head(v['head'])} (run pinned at {short_head(v['run_head'])}): examiner view digest "
            f"{'equal' if v['view_digest_equal'] else 'DIFFERENT'}; gate system {v['system_equal']}/{n}; gate prompt outside the "
            f"compiled-wiki block {v['prompt_outside_compiled_equal']}/{n}; each arm's bytes bound to its declared digest: shipped "
            f"{v['shipped_bytes_bound']}/{n}, baseline {v['baseline_bytes_bound']}/{n}; compiled-wiki block carried in a bound capture "
            f"{v['compiled_block_present']}/{n}; the COMPLETE gate prompt with the run's stored compile output replayed through "
            f"the current shipped path {v['prompt_complete_equal']}/{n} (distinct stored compile bodies {v['distinct_stored_bodies']}, "
            f"compile-role calls replayed {v['compile_calls']}); baseline capture = "
            f"transform(shipped capture) {v['baseline_transform_equal']}/{n}"
            + (f"; mismatches {v['mismatches']}" if v["mismatches"] else ""))


def _history_lines(res: dict) -> list:
    """Each earlier scoring of these captured answers (R5-02's closure: kept as history), and every outcome that
    differs between it and the scoring that followed it — the effect of each instrument change, on the same answers."""
    hist = res.get("history", [])
    if not hist:
        return []
    L = [f"earlier scorings of the same captured answers, oldest first ({len(hist)}):"]
    later = hist[1:] + [{"interpreter_sha16": res.get("interpreter_sha16"), "scored_at": res.get("rescored_at"),
                         "outcomes": [[x["question_id"], x["arm"], x["outcome"], x.get("cause")] for x in res["detail"]]}]
    for h, nxt in zip(hist, later):
        rates = "; ".join(f"{arm} refusal {_ratio(r['refusal_rate'])} completion {_ratio(r['completion'])}"
                          for arm, r in sorted(h["rates"].items()))
        L.append(f"  interpreter sha16 {h['interpreter_sha16']}, scored {h['scored_at']}: {rates}")
        now = {(q, a): (o, c) for q, a, o, c in nxt["outcomes"]}
        moved = [f"{q}/{a} {o} -> {now[(q, a)][0]}" for q, a, o, c in h["outcomes"] if now.get((q, a), (o,))[0] != o]
        L.append(f"    outcomes changed by the next scoring (interpreter {nxt['interpreter_sha16']}): "
                 + (", ".join(moved) if moved else "none"))
    return L


def _unscored_report(res: dict) -> str:
    cal = res["calibration"]
    L = [f"# generated {res['generated']} against veracium @ {res['head']}",
         "0043 — THE REFUSAL HARNESS, RUN: UNSCORED — awaiting the request manifest (A3-quinquies: capture, then score)", "",
         f"fixture store digest (as built): {res['fixture_digest']}", f"examiner view digest: {res['view_digest']}",
         f"calibration gate passed before capture: shipped {_ratio(cal['shipped'])}, baseline {_ratio(cal['baseline'])}, garble collapsed {cal['garble_collapsed']}",
         f"captured: {len(res['detail'])} (question, arm) pairs over {len(res['kept'])} kept questions; {len(res['excluded'])} excluded",
         "blind input for the two seats' labelling: blind_input.json beside this report (question id and text, the fixture rows)",
         "no answer has been interpreted: the requested propositions come from a request manifest adjudicated blind AFTER",
         "authorship, and the captures are scored only by `run_harness.py --rescore` against it", "",
         "questions (id, text):"]
    L += [f"  {q['id']}: {q['text']}" for q in res["questions"]]
    return "\n".join(L) + "\n"


# ---- the PUBLISHED figures (held-out-4's and held-out-5's pre-committed fallbacks) ------------------------------------
# Both readers failed their pre-committed held-out lines (event time at held-out-4, coordination def44a2; the mention reader at
# held-out-5, c61e913). So a run's PUBLISHED rates come from two-seat BLIND per-fact labels, and the reader's rates are an
# AID shown beside them. The committed run's labels (both seats, 76 of 76 identical; coordination 0048103) are carried here
# byte for byte, and its outcomes are scored by the run's OWN path (`_score` -> `interpret`) with each label in place of the
# reader's judgement of the answer and of nothing else (round 6, R6-01): the delivered accounting, support from the
# captured prompt and record, A3-quinquies's class-determining fact and tie, and the event-time rule all run unchanged.
LABELS_PATH = HERE / "outcome-labels" / "MERGED-LABELS.json"
LABELS_INPUT_PATH = HERE / "outcome-labels" / "outcome_blind_input.json"   # the input both seats labelled, byte for byte
LABELS_SEED = 20261006       # the seed the committed run's labelling input was extracted with (research's record)
# the frozen two-seat merge (coordination 0048103): pinned HERE, in the function that publishes, not only in a test —
# an edited labels file would otherwise publish its own figure (research's probe: baseline 2/24)
LABELS_SHA256 = "3125054ecb6a7947422da478136a2e218ba9ae9ba719f483245613a597c136cc"
# the extractor's own rendering of a facet (research's make_outcome_blind_input.py), so the items re-derive exactly
LABEL_FACET = {"none": "its content", "temporal:event-time": "WHEN the event itself happened (not when it was noted)",
               "temporal:record-time": "WHEN it was noted", "scope": "its content (the question may cover several)",
               "comparison": "its content (the question compares)", "other": "its content"}


def label_key(res: dict, seed: int) -> dict:
    """item -> (question, arm), regenerated exactly as make_outcome_blind_input.py makes it: the kept rows in ledger
    order, shuffled with the recorded seed."""
    detail = [x for x in res["detail"] if x["question_id"] in res["kept"]]
    order = list(range(len(detail))); random.Random(seed).shuffle(order)
    return {f"a{n:02d}": {"question_id": detail[i]["question_id"], "arm": detail[i]["arm"]} for n, i in enumerate(order, 1)}


def label_items(res: dict, seed: int) -> dict:
    """The labelling input's items, re-derived from this ledger exactly as the extractor built them: per item the question,
    the ANSWER, and the requested facts as the frozen manifest and the fixture rows render them."""
    rm = _load("request_manifest")
    man, _ = rm.load()
    rows = json.loads(pathlib.Path(rm.BLIND_PATH).read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)["fixture_rows"]
    detail = [x for x in res["detail"] if x["question_id"] in res["kept"]]
    order = list(range(len(detail))); random.Random(seed).shuffle(order)
    items = {}
    for n, i in enumerate(order, 1):
        x = detail[i]; e = man["questions"][x["question_id"]]
        items[f"a{n:02d}"] = {"question": x["question"], "answer": x["answer"],
                              "requested": [{"fact": r, "text": f'{rows[r]["subject"]} / {rows[r]["relation"]} / {rows[r]["object"]}',
                                             "asked_about": LABEL_FACET[e["facet"]]} for r in sorted(e["requested"])]}
    return items


def published_rates(res: dict, labels_path: pathlib.Path = LABELS_PATH, seed: int = LABELS_SEED,
                    input_path: pathlib.Path = LABELS_INPUT_PATH) -> dict | None:
    """The rates derived from the run's two-seat labels, or None for a run nobody has labelled (its manifest is not the
    frozen one). For the committed run every binding REFUSES on failure, each with its own reason, because labels joined
    to the wrong answers would publish the wrong figure:
      1. the labels and the labelled input are present (the committed run HAS labels; their absence is a defect), and the
         labels are the FROZEN merge (LABELS_SHA256);
      2. the carried input is the one labelled (its sha256 = the labels' input_sha256);
      3. the item -> (question, arm) key regenerates from this ledger (a reordered ledger fails here);
      4. the items re-derived from this ledger's ANSWERS equal the labelled input's (a changed or swapped answer fails here)."""
    ip, lg, rm = _load("interpreter"), _load("ledger"), _load("request_manifest")
    if res.get("manifest_sha256") != rm.FROZEN_SHA256:
        return None
    if not labels_path.exists() or not input_path.exists():
        raise Refused(f"the committed run's two-seat labels are missing ({labels_path.name} / {input_path.name}): its published "
                      "figure rests on them, so their absence is a defect, not 'no labels'")
    labels_bytes = labels_path.read_bytes()
    if hashlib.sha256(labels_bytes).hexdigest() != LABELS_SHA256:
        raise Refused(f"the labels are not the frozen two-seat merge: sha256 {hashlib.sha256(labels_bytes).hexdigest()[:16]}…, "
                      f"pinned {LABELS_SHA256[:16]}…")
    labels = json.loads(labels_bytes.decode("utf-8"), object_pairs_hook=_strict_pairs)
    input_bytes = input_path.read_bytes()
    if hashlib.sha256(input_bytes).hexdigest() != labels["input_sha256"]:
        raise Refused(f"the carried labelling input is not the one labelled: sha256 {hashlib.sha256(input_bytes).hexdigest()[:16]}…, "
                      f"the labels record {labels['input_sha256'][:16]}…")
    key = label_key(res, seed)
    key_sha = hashlib.sha256((json.dumps(key, indent=1, sort_keys=True) + "\n").encode()).hexdigest()
    if key_sha != labels["key_sha256"]:
        raise Refused(f"the labels' key {labels['key_sha256'][:16]}… does not regenerate from this ledger (got {key_sha[:16]}…): "
                      "the labels cannot be joined to these answers")
    labelled = json.loads(input_bytes.decode("utf-8"), object_pairs_hook=_strict_pairs)["items"]
    derived = label_items(res, seed)
    if derived != labelled:
        iid = next((k for k in sorted(set(derived) | set(labelled)) if derived.get(k) != labelled.get(k)), None)
        field = next((f for f in ("question", "answer", "requested") if (derived.get(iid) or {}).get(f) != (labelled.get(iid) or {}).get(f)), "presence")
        raise Refused(f"this ledger's answers do not re-derive the labelled input: item {iid} differs in its {field} — these labels "
                      "are not this run's answers")
    lab_of = {(v["question_id"], v["arm"]): labels["labels"][k] for k, v in key.items()}

    def mention_for(x, cd):
        """The label map for one row: each requested fact's two-seat label, keyed as `interpret` keys it (an event-time
        question's requested proposition is the time, `<id>@event-time`). The labels must cover exactly the requested set."""
        lab = lab_of[(x["question_id"], x["arm"])]
        if set(lab) != set(cd["requested"]):
            raise Refused(f"{x['question_id']}/{x['arm']}: the labels cover {sorted(lab)}, the request is {sorted(cd['requested'])}")
        return {(f"{e}@event-time" if cd["event_time"] else e): lab[e] for e in cd["requested"]}

    _rows, detail, rates, _ = _score(res, None, mention_for)
    rows = []
    for x in detail:
        cf = x["facts"].get(x["class_fact"]) or {}
        rows.append({"question_id": x["question_id"], "arm": x["arm"], "fixture_class": x["fixture_class"], "outcome": x["outcome"],
                     "cause": x.get("cause"), "support": cf.get("support"), "rule": x.get("rule")})
    leaked = [(r["question_id"], r["arm"], r["cause"]) for r in rows if r["cause"] in ip.READER_CAUSES]
    if leaked:                                      # a reader cause cannot survive a label: if one does, a label did not apply
        raise Refused(f"a published row carries a READER cause, which its label should have resolved: {leaked}")
    return {"rates": rates, "rows": rows, "labels_sha256": hashlib.sha256(labels_path.read_bytes()).hexdigest(), "key_sha256": key_sha, "seed": seed}


def report(res: dict) -> str:
    if res.get("unscored"):
        return _unscored_report(res)
    lg = _load("ledger")
    L = [f"# generated {res['generated']} against veracium @ {res['head']}",
         "0043 — THE REFUSAL HARNESS, RUN (tranche 2): two arms against the model, every rate with its denominator", "",
         f"fixture store digest (as built): {res['fixture_digest']}", f"examiner view digest: {res['view_digest']}",
         f"scored with interpreter.py sha16 {res.get('interpreter_sha16')}" + (f" — RE-SCORED {res['rescored_at']} over the captured answers (no new model call)" if res.get("rescored") else ""),
         *([f"requested propositions from the request manifest, sha256 {res['manifest_sha256']} (A3-quinquies: adjudicated blind by both seats, frozen, bound by its bytes)"] if res.get("manifest_sha256") else []),
         *_history_lines(res),
         f"model configuration (frozen): {json.dumps(res['config'], sort_keys=True)}",
         f"authorship: {json.dumps(res['authorship'], sort_keys=True)}",
         f"calibration before the run: shipped {_ratio(res['calibration']['shipped'])}, baseline {_ratio(res['calibration']['baseline'])} over "
         f"{res['calibration'].get('reference_cases', '?')} reference cases; UNRESOLVED on them {res['calibration']['unresolved_on_reference']} "
         f"(expected — a case whose labelled outcome is UNRESOLVED, the ambiguity control: {res['calibration'].get('unresolved_expected', '?')}; "
         f"unexpected — a known answer the judge could not resolve: {res['calibration'].get('unresolved_unexpected', '?')}); garble control collapsed: {res['calibration']['garble_collapsed']}",
         f"calibration independence: {res['calibration'].get('independence', 'not stated (a run before tranche 2b)')}",
         f"arm capture sources: {json.dumps(res['sources'], sort_keys=True)}",
         f"questions: {len(res['questions'])} authored, {len(res['kept'])} kept, {len(res['excluded'])} EXCLUDED (INV-6, counted):"]
    L += [f"  {qid}: {why}" for qid, why in res["excluded"].items()] or ["  (none)"]
    L += ["", "READER RATES — an AID, NOT the published figure (held-out-5's pre-committed fallback; event-time facts are "
          "human-scored by design). Refusals / RESOLVED rows; OTHER in the denominator; UNRESOLVED beside, out of both sides:"]
    for arm in res["arms"]:                               # the run's arm order, whichever way the ledger was loaded
        r = res["rates"][arm]
        L.append(f"  {arm:10s} refusal rate {_ratio(r['refusal_rate'])}  completion {_ratio(r['completion'])}  unresolved {r['unresolved']}  "
                 f"answered-on-trusted {_ratio(r['answered_on_trusted'])}  excluded {r['excluded']}")
        for c in lg.FIXTURE_CLASSES:
            pc = r["per_class"][c]
            L.append(f"             {c:26s} " + (pc if isinstance(pc, str) else f"rate {_ratio(pc['rate'])}  unresolved {pc['unresolved']}  presented {pc['presented']}"))
    pub = published_rates(res)
    if pub is None:
        L += ["", "PUBLISHED RATES — none: this run has no frozen two-seat labels. The reader's rates above are an aid only and are "
              "NOT to be quoted."]
    else:
        L += ["", f"PUBLISHED RATES — from the two-seat BLIND per-fact labels (outcome-labels/MERGED-LABELS.json sha256 {pub['labels_sha256']}; "
              f"key sha256 {pub['key_sha256']}, regenerated from this ledger with seed {pub['seed']}), by the spec's rubric:"]
        for arm in res["arms"]:
            r = pub["rates"][arm]
            L.append(f"  {arm:10s} PUBLISHED refusal rate {_ratio(r['refusal_rate'])}  completion {_ratio(r['completion'])}  unresolved {r['unresolved']}  "
                     f"answered-on-trusted {_ratio(r['answered_on_trusted'])}  excluded {r['excluded']}")
        L += ["", "PUBLISHED PER ROW — the authoritative outcome of every (question, arm), scored by the run's own path with the "
              "two-seat label in place of the reader (question · arm · class · outcome · cause · the class fact's support · rule):"]
        for r in pub["rows"]:
            L.append(f"  {r['question_id']} {r['arm']:9s} {r['fixture_class']:24s} {r['outcome']:20s} {r['cause'] or '-':33s} "
                     f"{r['support'] or '-':12s} {r['rule'] or ''}")
    L += ["", "UNRESOLVED by cause, and OTHER by rule (the instrument's failures are not the subject's):"]
    from collections import Counter
    for arm in res["arms"]:
        d = [x for x in res["detail"] if x["arm"] == arm]
        L.append(f"  {arm}: UNRESOLVED {dict(Counter(x['cause'] for x in d if x['outcome'] == 'UNRESOLVED'))}; OTHER {dict(Counter(x['rule'] for x in d if x['outcome'] == 'OTHER'))}; anomalies {sum(len(x['anomalies']) for x in d)}")
    L += ["", "PER QUESTION (class · outcome per arm · the answers verbatim):"]
    by_q = {}
    for x in res["detail"]:
        by_q.setdefault(x["question_id"], {})[x["arm"]] = x
    for qid, arms in by_q.items():
        any_ = next(iter(arms.values()))
        L.append(f"  {qid} [{any_['fixture_class']}] {any_['question']}")
        for arm, x in arms.items():
            L.append(f"      {arm:10s} {x['outcome']:20s} {x['answer']!r}" + (f"  ANOMALIES: {x['anomalies']}" if x["anomalies"] else "") + (f"  [{x['cause']}]" if x["cause"] else ""))
    return "\n".join(L) + "\n"


class FakeModel:
    """The pipeline's own test double: authors questions over the rows it is given and answers the gate
    from the prompt it receives — with the discipline when the prompt carries it, without when it does not."""
    _models = {"compile": "fake", "gate": "fake", "distill": "fake"}; _max_tokens = 0
    def __call__(self, prompt, *, system=None, role="compile", json_schema=None):
        if role == "compile" and json_schema is not None:
            rows = re.findall(r"^(\d+)\. (\S+) — (\S+) — (.+?) \(since", prompt, re.M)
            qs = [{"question": f"What is the user's {rel.replace('_', ' ')}?", "rows": [int(i)]} for i, _, rel, _ in rows]
            qs.append({"question": "Where does the user work and where do they live?", "rows": [int(i) for i, _, rel, _ in rows if rel in ("works_as", "located_at")][:2]})
            qs.append({"question": "Is the user's job verified?", "rows": [1]})          # a non-blind question: excluded, counted
            return json.dumps({"questions": qs})
        if role == "compile":
            return "## USER MODEL\n- COMPILED-BODY: the user prefers concise answers, keeps a cat, and lives in Porto"
        if role == "gate":
            disciplined = "GROUNDED MEMORY" in prompt
            q = prompt.split("Question:")[-1].split("\n")[0].strip().lower()
            if "work" in q:
                return "I have no confirmed record of where the user works." if disciplined else "The user is a night auditor at the Grand."
            if "prefer" in q: return "The user prefers concise answers."
            if "pet" in q: return "The user has a cat called Miso."
            if "live" in q or "located" in q: return "The user lives in Porto."
            return "I don't know."
        return json.dumps({"triples": [], "episode": "x", "instructions": []})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=False); ap.add_argument("--questions", type=int, default=24); ap.add_argument("--fake", action="store_true")
    ap.add_argument("--rescore", help="a committed run_ledger.json: re-interpret its captured answers with the current interpreter, no model call")
    ap.add_argument("--reverify", help="a committed run_ledger.json: re-derive its inputs at HEAD without the model and print the verdict")
    a = ap.parse_args()
    if a.reverify:
        v = reverify(json.loads(pathlib.Path(a.reverify).read_text(), object_pairs_hook=_strict_pairs)); print(reverify_lines(v))
        sys.exit(0 if v["downstream"] == "REVERIFIED" and v["compiler_stage"] != "NOT REVERIFIED" else 1)
    if a.rescore:
        if not a.out:
            ap.error("--rescore needs --out")
        res = rescore(json.loads(pathlib.Path(a.rescore).read_text(), object_pairs_hook=_strict_pairs))
        out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
        (out / "run_ledger.json").write_text(json.dumps(res, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        (out / "run_report.txt").write_text(report(res)); print((out / "run_report.txt").read_text()); sys.exit(0)
    if a.fake:
        inner = FakeModel()
    else:
        from veracium.llm.anthropic import AnthropicComplete
        inner = AnthropicComplete()
    if not a.out:
        ap.error("a run needs --out")
    res = run(pathlib.Path(a.out), inner, n_questions=a.questions)
    print((pathlib.Path(a.out) / "run_report.txt").read_text())
