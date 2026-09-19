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
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


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
    delivered = [{"edge": e.id, "subject": e.subject, "relation": e.relation, "object": e.object, "class": mc.edge_class(e),
                  "unit": f"{e.relation}: {e.object} (since {e.valid_from.date()})"} for e in recalls[0].edges]
    return {"system": c["system"], "prompt": c["prompt"], "answer": c.get("answer", ""), "error": c.get("error"), "ms": c["ms"],
            "digest": hashlib.sha256((c["system"] + "\n\x00\n" + c["prompt"]).encode()).hexdigest(), "delivered": delivered, "source": "captured",
            "partition": {"grounded": recalls[0].grounded, "unverified": recalls[0].unverified}, "execution": execution,
            "config": {"question": question, "max_subgraph_edges": max_subgraph_edges, "compilation": "on"}}


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
                "digest": hashlib.sha256((c["system"] + "\n\x00\n" + c["prompt"]).encode()).hexdigest(), "source": "captured", "execution": execution}
    o_system, o_prompt = mc.baseline_transform(shipped["system"], shipped["prompt"])
    captured["oracle_digest"] = hashlib.sha256((o_system + "\n\x00\n" + o_prompt).encode()).hexdigest()
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


def run(out: pathlib.Path, inner, *, n_questions: int = 24, questions_override: list | None = None) -> dict:
    ev, mc, ip, lg = _load("examiner_view"), _load("model_input_capture"), _load("interpreter"), _load("ledger")
    ep = _load("examiner_projection")
    out.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    # the fixture, frozen: built once, digested as built
    db = out / "fixture.db"
    if db.exists(): db.unlink()
    st = ev.fixture_store(str(db)); view_rows = ev.view(st, "u"); _, view_digest = ev.freeze(view_rows); man = manifest(st, "u"); st.close()
    fixture_digest = _digest_file(db)
    # calibration BEFORE the run (the gate is on the instrument): the reference cases over a captured pair
    probe = mc.run()
    cal_s = ip.calibrate(probe["shipped"]["prompt"], probe["record"]); cal_b = ip.calibrate(probe["baseline"]["prompt"], probe["record"])
    garble = ip.garble_control(probe["shipped"]["prompt"], probe["record"])
    if not (cal_s["calibrated"] and cal_b["calibrated"] and garble["collapsed"]):
        raise Refused(f"the interpreter is not calibrated: shipped {cal_s['agreement']} baseline {cal_b['agreement']} garble collapsed={garble['collapsed']} — the run does not start")
    calibration = {"shipped": cal_s["agreement"], "baseline": cal_b["agreement"], "unresolved_on_reference": cal_s["unresolved"], "garble_collapsed": garble["collapsed"]}
    # the examiner, blind
    if questions_override is not None:
        questions, authorship = questions_override, {"author": "override (a test's canned set)", "requested": len(questions_override), "returned": len(questions_override)}
    else:
        questions, authorship = author_questions(view_rows, inner, n_questions)
    paraphrases = {(f["relation"], f["object"]): f.get("paraphrases", []) for f in ip.FACTS.values()}
    kept, excluded = attach_classes(questions, view_rows, man, screen_fragments(ep.forbidden_fragments(), view_rows), paraphrases)
    expected = {q["id"]: q["fixture_class"] for q in kept}
    arms = ("veracium", lg.BASELINE_ARM)
    # the arms
    rows, detail = [], []
    for q in kept:
        shipped = capture_shipped(str(db), q["text"], inner)
        record = mc.adjudication_record(shipped["delivered"])
        baseline = capture_baseline_real(shipped, inner)
        for arm, cap in (("veracium", shipped), (lg.BASELINE_ARM, baseline)):
            execution = dict(cap["execution"])
            if cap.get("error"):
                execution["event"] = "error"
            qd = {"text": q["text"], "facts": q["facts"], "class_fact": q["class_fact"]}
            r = ip.interpret(qd, cap["prompt"], record, cap["answer"] or "", execution, delivered=shipped["delivered"])
            cf = r["facts"].get(q["class_fact"], {})
            rows.append({"question_id": q["id"], "arm": arm, "fixture_class": q["fixture_class"], "outcome": r["outcome"], "attempts": 1,
                         "claimed_reason": (cap["answer"] or cap.get("error") or "")[:160], "support": _ledger_support(cf.get("support") if cf else None)})
            detail.append({"question_id": q["id"], "arm": arm, "question": q["text"], "fixture_class": q["fixture_class"], "class_fact": q["class_fact"],
                           "answer": cap["answer"], "error": cap.get("error"), "ms": cap["ms"], "outcome": r["outcome"], "cause": r.get("cause"), "rule": r["rule"],
                           "facts": r["facts"], "anomalies": r["anomalies"], "prompt_digest": cap["digest"], "delivered": [d["edge"] for d in shipped["delivered"]],
                           "system": cap["system"], "prompt": cap["prompt"], "record": record, "question_facts": q["facts"], "execution": execution})
    # excluded questions appear in the ledger with their reason (A1-bis) and are declared exclusions
    for qid, why in excluded.items():
        for arm in arms:
            rows.append({"question_id": qid, "arm": arm, "fixture_class": "absent", "outcome": "UNRESOLVED", "attempts": 1, "claimed_reason": f"excluded: {why}"[:160], "support": "none"})
    expected_all = {**expected, **{qid: "absent" for qid in excluded}}
    sources = {"veracium": "captured", lg.BASELINE_ARM: "captured"}
    problems = lg.gate(rows, expected_all, arms, exclusions=excluded, sources=sources)
    if problems:
        raise Refused("the ledger refused: " + "; ".join(problems))
    rates = {arm: lg.rates(rows, arm, expected_all, arms, exclusions=excluded, sources=sources) for arm in arms}
    # model configuration, frozen and quoted
    models = getattr(inner, "_models", None) or {"note": "fake model"}
    config = {"models": dict(models) if isinstance(models, dict) else models, "max_tokens": getattr(inner, "_max_tokens", None),
              "temperature": "not sent by the shipped provider (the API default applies)", "seed": "not exposed by the provider",
              "max_subgraph_edges": 40, "compilation": "on"}
    result = {"head": head, "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "interpreter_sha16": interpreter_sha16(),
              "fixture_digest": fixture_digest, "view_digest": view_digest, "manifest_classes": {eid: v["class"] for eid, v in man.items()},
              "authorship": authorship, "questions": questions, "kept": [q["id"] for q in kept], "excluded": excluded,
              "calibration": calibration, "config": config, "sources": sources, "arms": list(arms), "ledger": rows, "detail": detail, "rates": rates}
    (out / "run_ledger.json").write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "run_report.txt").write_text(report(result))
    return result


def rescore(res: dict) -> dict:
    """Re-interpret a committed run's captured answers with the CURRENT interpreter — no model call, the
    prompts and records travel in the ledger's detail — and recompute the rates. The instrument can be
    improved and its effect shown on the SAME answers; the answers themselves never change."""
    ip, lg = _load("interpreter"), _load("ledger")
    rows, detail = [], []
    for x in res["detail"]:
        qd = {"text": x["question"], "facts": x["question_facts"], "class_fact": x["class_fact"]}
        r = ip.interpret(qd, x["prompt"], x["record"], x["answer"] or "", x.get("execution", {}), delivered=None)
        cf = r["facts"].get(x["class_fact"], {})
        rows.append({"question_id": x["question_id"], "arm": x["arm"], "fixture_class": x["fixture_class"], "outcome": r["outcome"], "attempts": 1,
                     "claimed_reason": (x["answer"] or x.get("error") or "")[:160], "support": _ledger_support(cf.get("support") if cf else None)})
        detail.append({**x, "outcome": r["outcome"], "cause": r.get("cause"), "rule": r["rule"], "facts": r["facts"], "anomalies": r["anomalies"]})
    excluded = res["excluded"]
    for qid in excluded:
        for arm in res["arms"]:
            rows.append(next(r for r in res["ledger"] if r["question_id"] == qid and r["arm"] == arm))
    expected = {r["question_id"]: r["fixture_class"] for r in rows}
    problems = lg.gate(rows, expected, tuple(res["arms"]), exclusions=excluded, sources=res["sources"])
    if problems:
        raise Refused("the re-scored ledger refused: " + "; ".join(problems))
    rates = {arm: lg.rates(rows, arm, expected, tuple(res["arms"]), exclusions=excluded, sources=res["sources"]) for arm in res["arms"]}
    return {**res, "ledger": rows, "detail": detail, "rates": rates, "rescored": True, "interpreter_sha16": interpreter_sha16(),
            "rescored_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}


def interpreter_sha16() -> str:
    """The instrument the outcomes were scored with — named in the report, bound by the test."""
    return hashlib.sha256((HERE / "interpreter.py").read_bytes()).hexdigest()[:16]


def _ratio(x):
    return "UNDEFINED" if x == "UNDEFINED" else f"{x[0]}/{x[1]}"


def report(res: dict) -> str:
    lg = _load("ledger")
    L = [f"# generated {res['generated']} against veracium @ {res['head']}",
         "0043 — THE REFUSAL HARNESS, RUN (tranche 2): two arms against the model, every rate with its denominator", "",
         f"fixture store digest (as built): {res['fixture_digest']}", f"examiner view digest: {res['view_digest']}",
         f"scored with interpreter.py sha16 {res.get('interpreter_sha16')}" + (f" — RE-SCORED {res['rescored_at']} over the captured answers (no new model call)" if res.get("rescored") else ""),
         f"model configuration (frozen): {json.dumps(res['config'], sort_keys=True)}",
         f"authorship: {json.dumps(res['authorship'], sort_keys=True)}",
         f"calibration before the run: shipped {_ratio(res['calibration']['shipped'])}, baseline {_ratio(res['calibration']['baseline'])}, "
         f"UNRESOLVED on the reference cases {res['calibration']['unresolved_on_reference']}, garble control collapsed: {res['calibration']['garble_collapsed']}",
         f"arm capture sources: {json.dumps(res['sources'], sort_keys=True)}",
         f"questions: {len(res['questions'])} authored, {len(res['kept'])} kept, {len(res['excluded'])} EXCLUDED (INV-6, counted):"]
    L += [f"  {qid}: {why}" for qid, why in res["excluded"].items()] or ["  (none)"]
    L += ["", "RATES (refusals / RESOLVED rows; OTHER in the denominator; UNRESOLVED beside, out of both sides):"]
    for arm, r in res["rates"].items():
        L.append(f"  {arm:10s} refusal rate {_ratio(r['refusal_rate'])}  completion {_ratio(r['completion'])}  unresolved {r['unresolved']}  "
                 f"answered-on-trusted {_ratio(r['answered_on_trusted'])}  excluded {r['excluded']}")
        for c in lg.FIXTURE_CLASSES:
            pc = r["per_class"][c]
            L.append(f"             {c:26s} " + (pc if isinstance(pc, str) else f"rate {_ratio(pc['rate'])}  unresolved {pc['unresolved']}  presented {pc['presented']}"))
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
    ap.add_argument("--out", required=True); ap.add_argument("--questions", type=int, default=24); ap.add_argument("--fake", action="store_true")
    ap.add_argument("--rescore", help="a committed run_ledger.json: re-interpret its captured answers with the current interpreter, no model call")
    a = ap.parse_args()
    if a.rescore:
        res = rescore(json.loads(pathlib.Path(a.rescore).read_text(), object_pairs_hook=_strict_pairs))
        out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
        (out / "run_ledger.json").write_text(json.dumps(res, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        (out / "run_report.txt").write_text(report(res)); print((out / "run_report.txt").read_text()); sys.exit(0)
    if a.fake:
        inner = FakeModel()
    else:
        from veracium.llm.anthropic import AnthropicComplete
        inner = AnthropicComplete()
    res = run(pathlib.Path(a.out), inner, n_questions=a.questions)
    print((pathlib.Path(a.out) / "run_report.txt").read_text())
