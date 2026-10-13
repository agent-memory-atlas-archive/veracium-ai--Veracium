"""The two package reference models, run as part of the suite (R1-10's MODEL checks, before design acceptance).

`specs/evidence/0044/run_model.py` encodes research's arity stage-1 rules (0044 v1.3, the 0003 and 0018 amendments);
`specs/evidence/0045/run_model.py` encodes the grounding x reply x confirmation rules (0045, 0047, the 0019
amendment). Each exits 0 only when every invariant holds AND every declared mutant is killed by the invariant that
owns it (other invariants may kill it too; that is a further detection, not a failure). Model II's runner counts a kill
only when the owner RETURNS False with the mutated function called while it ran: an owner that raises is a harness
failure (the 0044 round-2 verdict's R2-08). They are models, not product code (no `veracium` import): the product tests
that bind the same properties to shipped code belong to the implementation gate.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = {"0044": ROOT / "specs" / "evidence" / "0044" / "run_model.py",
          "0045": ROOT / "specs" / "evidence" / "0045" / "run_model.py"}


@pytest.mark.parametrize("spec", sorted(MODELS))
def test_the_reference_model_passes_and_every_mutant_dies_by_its_own_invariant(spec, tmp_path):
    out = tmp_path / "results.json"
    r = subprocess.run([sys.executable, "-B", str(MODELS[spec]), "--out", str(out)],
                       capture_output=True, text=True, cwd=MODELS[spec].parent)
    assert r.returncode == 0, r.stdout + r.stderr
    res = json.loads(out.read_text())
    assert res["verdict"] == "PASS"
    assert res["invariants"] and all(v is True for v in res["invariants"].values()), res["invariants"]
    # rule zero: the model can fail — there is at least one mutant, each killed, each by its OWN invariant, and every
    # invariant owns at least one mutant (an invariant no mutant has ever failed is not shown to be able to fail)
    muts = res["mutants"]
    assert muts and all(m["killed_by_owner"] for m in muts.values()), muts
    assert set(res["invariants"]) <= {m["owner"] for m in muts.values()}, \
        sorted(set(res["invariants"]) - {m["owner"] for m in muts.values()})


@pytest.mark.parametrize("spec", sorted(MODELS))
def test_the_model_leaves_its_directory_untouched(spec, tmp_path):
    """The runner writes only where --out says, so a test run cannot dirty the tracked tree."""
    d = MODELS[spec].parent
    before = sorted(p.name for p in d.iterdir() if p.name != "__pycache__")
    subprocess.run([sys.executable, "-B", str(MODELS[spec]), "--out", str(tmp_path / "r.json")],
                   capture_output=True, text=True, cwd=d)
    assert sorted(p.name for p in d.iterdir() if p.name != "__pycache__") == before


# ---------------------------------------------------------------------------------------------- the model's citations
_CITATIONS = ROOT / "specs" / "evidence" / "0045" / "model_citations.py"
_TREE_DOCS = {"0045": ROOT / "specs" / "0045-declarative-grounding.md",
              "0047": ROOT / "specs" / "0047-subject-reply.md"}


def _citations():
    import importlib.util
    spec = importlib.util.spec_from_file_location("model_citations", _CITATIONS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_model_citation_in_the_tree_specs_runs_its_mutant():
    """0045 and 0047 cite model II by invariant ("(model G2)"); each citation has a mutant answering that row, owned and
    killed by that invariant, and every model invariant a spec claims as its own is cited by one of its rows. The two
    amendments travel outside the tree, so the package stage runs the same check over all four documents."""
    mc = _citations()
    docs = {lab: p.read_text(encoding="utf-8") for lab, p in _TREE_DOCS.items()}
    problems = mc.check(docs, mc.run_model.run_mutants())
    assert not problems, "\n".join(problems)


def test_model_citations_refuses_each_broken_carrier():
    """model_citations.py's mutation matrix: each broken carrier is refused, by the refusal that names it; the tree's
    documents pass. Mutants are run once and edited as data, so each case moves exactly one thing."""
    mc = _citations()
    muts = mc.run_model.run_mutants()
    d47 = _TREE_DOCS["0047"].read_text(encoding="utf-8")
    assert not mc.check({"0047": d47}, muts)
    # the rows are FOUND by what they cite, never named here: this file is evidence about the documents, and a §6 id
    # written into tests/ would read, to the stage's design-round check, as an implementation test citing it
    rows47 = mc.parse(d47)[0]
    proc = next(i for i, c in rows47.items() if c == {"G12"})                   # the procedural row: cites G12 alone
    budget = next(i for i, c in rows47.items() if c == {"G4"})                  # the budget row: cites G4 alone
    proc_line = next(line for line in d47.splitlines() if line.startswith(f"| **{proc}**"))
    n_row = next(a.split(" ", 1)[1] for m in muts.values() for a in m["answers"] if a.startswith("0019am "))
    am = ("# Amendment\n\n## 6. Invariants\n\n| | invariant | mutant |\n|---|---|---|\n"
          f"| **{n_row}** | a | b |\n\n*MODEL: dev's reference model II encodes the write path (its {{g}}).*\n\n## 7. Next\n")
    proc_mutant = next(n for n, m in muts.items() if f"0047 {proc}" in m["answers"])

    def killed_false(name):
        m = {k: dict(v) for k, v in muts.items()}
        m[name]["killed_by_owner"] = False
        return m

    cases = {
        # name: (docs, mutants, a substring the refusal must carry)
        "a row cites a model invariant no mutant answers": (
            {"0047": d47.replace("(model G12)", "(model G12, model G9)", 1)}, muts, f"FORWARD 0047 {proc} cites model G9"),
        "a row drops its citation (the mutant now answers an uncited row)": (
            {"0047": d47.replace("→ FAILS** (model G4)", "→ FAILS**", 1)}, muts, f"REVERSE 0047 {budget}"),
        "a claimed invariant no row cites": (
            {"0047": d47.replace("→ FAILS** (model G4)", "→ FAILS**", 1)}, muts, "CLAIM 0047: claims model G4"),
        "a mutant answers a row the document does not have": (
            {"0047": d47.replace(proc_line + "\n", "", 1)}, muts, f"REVERSE 0047 {proc}: mutant"),
        "a citation with no number": (
            {"0047": d47.replace("(model G12)", "(model G)", 1)}, muts, "GRAMMAR 0047: a `model G` citation with no number"),
        "a document with no §6": (
            {"0047": d47.replace("\n## 6.", "\n## 6x.", 1)}, muts, "GRAMMAR 0047: no §6 section"),
        "a cited mutant its owner does not kill": (
            {"0047": d47}, killed_false(proc_mutant), f"KILL 0047 {proc}"),
        "a row names a mutant the model never tagged": (
            {"0047": d47.replace(proc_line, proc_line.replace("**Mutant: accept it → FAILS**",
                                                              "**Mutants: accept it; accept it twice → FAIL**"), 1)},
            muts, f"COUNT 0047 {proc}: the row names 2 mutant(s), the model tags 1"),
        "an amendment's model scope that no mutant answers": (
            {"0019am": am.format(g="G9")}, muts, "FORWARD 0019am: §6 says the model encodes it (its G9)"),
    }
    assert not mc.check({"0019am": am.format(g="G8")}, {k: v for k, v in muts.items()
                                                        if v["answers"] == [f"0019am {n_row}"]})
    for name, (docs, m, expect) in cases.items():
        problems = mc.check(docs, m)
        assert any(expect in p for p in problems), f"{name}: expected {expect!r} in {problems}"


def test_model_ii_counts_neither_a_crash_nor_an_unreached_mutant_as_a_kill():
    """R2-08 (0044 round 2): a runner that counted ANY exception as a kill reported a mutant with the wrong signature as
    killed, though it never reached the assertion it claimed. Model II's runner: the owner must RETURN False, and the
    installed function must have been called while the owner ran. Planted: a mutant whose replacement raises, and one
    installed on a function its owner never calls — neither is a kill; the honest table is all kills."""
    import importlib.util
    path = MODELS["0045"]
    spec = importlib.util.spec_from_file_location("run_model_ii_probe", path)
    rm = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(rm)
        honest = rm.run_mutants()
        assert all(m["killed_by_owner"] and m["owner_outcome"] == "failed" and m["mutated_path_reached"]
                   for m in honest.values()), {k: v for k, v in honest.items() if not v["killed_by_owner"]}

        def crashes(*a, **kw):
            raise TypeError("planted: wrong signature")
        saved, saved_g1 = dict(rm.MUTANTS), rm.INVARIANTS["MODEL-G1"]
        rm.MUTANTS.clear()
        rm.MUTANTS["planted crash"] = ("MODEL-G10", rm._set("import_rows", crashes), ())
        # the owner FAILS (stubbed), but for a reason the installed function had no part in: G1 never calls import_rows
        rm.MUTANTS["planted unreached"] = ("MODEL-G1", rm._set("import_rows", lambda *a, **kw: None), ())
        rm.INVARIANTS["MODEL-G1"] = lambda rules=None: False
        try:
            got = rm.run_mutants()
        finally:
            rm.MUTANTS.clear(); rm.MUTANTS.update(saved); rm.INVARIANTS["MODEL-G1"] = saved_g1
        assert got["planted crash"]["owner_outcome"].startswith("raised TypeError") and not got["planted crash"]["killed_by_owner"]
        assert got["planted unreached"]["owner_outcome"] == "failed"
        assert not got["planted unreached"]["mutated_path_reached"] and not got["planted unreached"]["killed_by_owner"]
    finally:
        _sys.path.remove(str(path.parent))


# ---------------------------------------------------------------------------------------------- package I's obligation map
_OBLIGATIONS = ROOT / "specs" / "evidence" / "0044" / "obligations.py"


def _obligations():
    import importlib.util
    spec = importlib.util.spec_from_file_location("obligations_0044", _OBLIGATIONS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _s6(*rows, extra=""):
    body = "".join(f"| **{r}** | x | y |\n" for r in rows)
    return f"# Doc\n\n## 6. Invariants\n\n| | invariant | mutant |\n|---|---|---|\n{body}\n{extra}\n## 7. Next\n"


def test_the_obligation_map_refuses_each_broken_carrier():
    """obligations.py's mutation matrix (R2-08's map): every refusal fires on its planted break, by the refusal that
    names it, and the honest control passes. Rows are planted as documents built from the map's own keys, so the map is
    exercised against its whole domain without naming a §6 id here."""
    ob = _obligations()
    muts = ob.RUN.run_mutants()                    # model I's runner, as the module under test loaded it
    docs = {d: _s6(*[r for dd, r in ob.ROWS if dd == d]) for d in sorted({d for d, _r in ob.ROWS})}
    assert ob.check_rows(docs, muts) == []                                       # the control: the map's own domain
    src = {"m": _OBLIGATIONS.with_name("arity_model.py").read_text()}
    assert ob.check_domains(src) == [] and ob.check_guards(src) == []             # the control: the model is clean
    first_doc, first_row = next(iter(ob.ROWS))
    model_row = next(k for k, v in ob.ROWS.items() if isinstance(v, list))
    owner = ob.ROWS[model_row][0]

    def rows_with(**edit):
        saved = dict(ob.ROWS)
        try:
            ob.ROWS.update(edit.get("set", {}))
            for k in edit.get("drop", ()):
                ob.ROWS.pop(k)
            return ob.check_rows(edit.get("docs", docs), edit.get("muts", muts))
        finally:
            ob.ROWS.clear(); ob.ROWS.update(saved)

    unclaimed_row = next(k for k, v in ob.ROWS.items() if isinstance(v, list) and len(v) == 1
                         and sum(v == w or (isinstance(w, list) and v[0] in w) or (isinstance(w, dict) and v[0] in w["model"])
                                 for w in ob.ROWS.values()) == 1)
    cases = {
        "an unmapped §6 row": (rows_with(docs={**docs, first_doc: docs[first_doc].replace("## 7.", "| **INV-Z99** | a | b |\n\n## 7.")}),
                               "INV-Z99: unmapped"),
        "a mapping whose row the document lost": (rows_with(docs={**docs, model_row[0]: docs[model_row[0]].replace(f"| **{model_row[1]}** | x | y |\n", "")}),
                                                  f"{model_row[1]}: mapped but not in"),
        "a row mapped to an invariant the model lacks": (rows_with(set={model_row: ["INV-M999"]}), "INV-M999, which the model does not define"),
        "an invariant that kills no mutant": (rows_with(muts={k: dict(v, killed_by_owner=False) if v["owner"] == owner else v for k, v in muts.items()}),
                                              f"{owner} owns no killed mutant"),
        "a PRODUCT mapping with no reason": (rows_with(set={model_row: ("PRODUCT", " ")}), "must be ('PRODUCT' or 'MODEL-II', reason)"),
        "a two-part mapping with no product reason": (rows_with(set={model_row: {"model": [owner], "product": ""}}), "exactly one reasoned"),
        "a two-part mapping with no model II reason": (rows_with(set={model_row: {"model": [owner], "model_ii": " "}}), "exactly one reasoned"),
        "a two-part mapping with no model part": (rows_with(set={model_row: {"model": [], "model_ii": "acts"}}), "exactly one reasoned"),
        "a two-part mapping with both other parts": (rows_with(set={model_row: {"model": [owner], "product": "p", "model_ii": "m"}}), "exactly one reasoned"),
        "a two-part mapping with an unknown part": (rows_with(set={model_row: {"model": [owner], "produkt": "p"}}), "exactly one reasoned"),
        "a model invariant no row claims": (rows_with(set={unclaimed_row: ("PRODUCT", "moved")}), f"{ob.ROWS[unclaimed_row][0]} is claimed by no row"),
    }
    for name, (problems, expect) in cases.items():
        assert any(expect in p for p in problems), f"{name}: expected {expect!r} in {problems}"
    saved = dict(ob.CARRIERS)
    try:
        ob.CARRIERS.pop("Edge.invalidated_at")
        assert any("Edge.invalidated_at: a model field with no declared carrier" in p for p in ob.check_domains({}))
    finally:
        ob.CARRIERS.clear(); ob.CARRIERS.update(saved)
    planted = {
        "two clocks compared": ("def consider(s, e):\n    return e.invalidated_at < s.header['written_txn']\n", "compares ['transaction', 'valid']"),
        "one alias hides the clock": ("def consider(s, e):\n    t = s.txn\n    return e.invalidated_at < t\n", "compares ['transaction', 'valid']"),
        "an operand of unknown domain": ("def f(s, e, x):\n    return e.invalidated_at < x\n", "with an operand of unknown domain"),
    }
    for name, (code, expect) in planted.items():
        assert any(expect in p for p in ob.check_domains({"p": code})), name
    direct = "def receipt(s, user):\n    return [s.edges[k].obj for k in s.outcomes]\n"
    helper = "def _text(s, k):\n    return s.edges[k].obj\n\ndef undo(s, user, k):\n    return _text(s, k)\n"
    assert any("`receipt`" in p for p in ob.check_guards({"p": direct}))
    assert any("`_text`" in p for p in ob.check_guards({"p": helper}))
    shared_row = next(r for (d, r), v in ob.ROWS.items() if d == "0008am" and isinstance(v, tuple) and v[0] == "MODEL-II")
    sys.path.insert(0, str(ROOT / "specs" / "evidence" / "0045"))
    try:
        import importlib.util
        spec2 = importlib.util.spec_from_file_location("run_model_ii_ob", ROOT / "specs" / "evidence" / "0045" / "run_model.py")
        rm2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(rm2)
        m2 = rm2.run_mutants()
        owner2 = next(m["owner"] for m in m2.values() if f"0008am {shared_row}" in m["answers"] and m["killed_by_owner"])
        uncited = _s6(shared_row)
        cited = _s6(shared_row, extra=f"*MODEL: dev's reference model II encodes it (its {owner2.split('-', 1)[1]}).*\n")
        assert any(f"SHARED 0008am {shared_row}: handed to model II, but the row cites no" in p for p in ob.check_shared(uncited, m2))
        assert not [p for p in ob.check_shared(cited, m2) if shared_row in p]
        # a TWO-OWNER row (model I's part plus a model II part) is handed to model II too: its model II half is
        # refused uncited exactly as a whole MODEL-II row is (the dict form must not escape check_shared)
        mixed = next(r for (d, r), v in ob.ROWS.items() if d == "0008am" and isinstance(v, dict) and "model_ii" in v)
        assert any(f"SHARED 0008am {mixed}: handed to model II, but the row cites no" in p
                   for p in ob.check_shared(_s6(mixed), m2))
    finally:
        sys.path.remove(str(ROOT / "specs" / "evidence" / "0045"))


def test_the_two_runners_never_shadow_each_other_whatever_the_import_order():
    """Both package models name their runner `run_model.py`. The round-3 suite (shuffled, parallel) loaded package I's
    obligation map, which imported model I's runner by bare name, and model_citations then got model I's runner — its
    mutants carry no `answers` (KeyError in two tests, on one seed). Each importer now loads its runner BY FILE under a
    unique name. Both orders, each in a fresh interpreter: each importer holds its own model's runner."""
    ob, mc = str(_OBLIGATIONS), str(_CITATIONS)
    probe = (
        "import importlib.util, sys\n"
        "def load(n, p):\n"
        "    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s)\n"
        "    s.loader.exec_module(m); return m\n"
        "order = sys.argv[1:]\n"
        "mods = {}\n"
        "for k in order:\n"
        "    mods[k] = load('probe_' + k, {'ob': %r, 'mc': %r}[k])\n"
        "print(mods['ob'].RUN.__file__); print(mods['mc'].run_model.__file__)\n"
        "print('run_model' in sys.modules)\n" % (ob, mc))
    for order in (("ob", "mc"), ("mc", "ob")):
        r = subprocess.run([sys.executable, "-B", "-c", probe, *order], capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0, r.stdout + r.stderr
        ob_runner, mc_runner, bare = r.stdout.split()
        assert ob_runner.endswith("0044/run_model.py") and mc_runner.endswith("0045/run_model.py"), (order, r.stdout)
        assert bare == "False", (order, "a bare `run_model` entered sys.modules")
