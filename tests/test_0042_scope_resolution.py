"""specs/0042 — the shared scope resolver (round 7, F2 and F4a's shared root).

The instrument under test replaced a HAND-ENUMERATED list of the forms that bind a name with CPython's own scope
analysis. So the matrix here is the binding grammar itself: the two forms the round-7 reviewer found (`:=` and a
`match` capture), the ones research named in advance, and — the half that catches an over-strict resolver — the
forms that must NOT shadow (a comprehension target, a class-body attribute, a nested function's own parameter).
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "specs" / "evidence" / "0042"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m; spec.loader.exec_module(m); return m


sr = _load("scope_resolution_under_test", EVIDENCE / "scope_resolution.py")

# (label, source, does `S` at the marked use resolve to the MODULE binding?)
GRAMMAR = [
    ("a plain outward read",            "S = 1\ndef f(x):\n    return S.fire(x)\n", True),
    ("an ordinary assignment",          "S = 1\ndef f(x):\n    S = x\n    return S.fire(x)\n", False),
    ("an assignment expression",        "S = 1\ndef f(x):\n    if (S := x):\n        return S.fire(x)\n    return 0\n", False),
    ("a match capture",                 "S = 1\ndef f(x):\n    match x:\n        case [S]:\n            return S.fire(1)\n    return 0\n", False),
    ("a parameter",                     "S = 1\ndef f(S):\n    return S.fire(1)\n", False),
    ("a parameter with a default",      "S = 1\ndef f(S=None):\n    return S.fire(1)\n", False),
    ("a for target",                    "S = 1\ndef f(xs):\n    for S in xs:\n        return S.fire(1)\n", False),
    ("a tuple for target",              "S = 1\ndef f(xs):\n    for (a, S) in xs:\n        return S.fire(1)\n", False),
    ("a star for target",               "S = 1\ndef f(xs):\n    for a, *S in xs:\n        return S.fire(1)\n", False),
    ("a with-as target",                "S = 1\ndef f(cm):\n    with cm as S:\n        return S.fire(1)\n", False),
    ("an except-as target",             "S = 1\ndef f():\n    try:\n        pass\n    except Exception as S:\n        return S.fire(1)\n", False),
    ("an augmented assignment",         "S = 1\ndef f(x):\n    S += x\n    return S.fire(1)\n", False),
    ("a deleted name",                  "S = 1\ndef f(x):\n    del S\n    return S.fire(1)\n", False),
    ("an `import x as S`",              "S = 1\ndef f():\n    import os as S\n    return S.fire(1)\n", False),
    ("a `from x import y as S`",        "S = 1\ndef f():\n    from os import path as S\n    return S.fire(1)\n", False),
    ("a name bound on ONE branch",      "S = 1\ndef f(x):\n    if x:\n        S = x\n    return S.fire(1)\n", False),
    ("an ENCLOSING function's binding", "S = 1\ndef outer(o):\n    S = o\n    def inner():\n        return S.fire(1)\n    return inner\n", False),
    ("a nonlocal declaration",          "S = 1\ndef outer(o):\n    S = o\n    def inner():\n        nonlocal S\n        return S.fire(1)\n    return inner\n", False),
    # the half that catches an OVER-STRICT resolver: these must still reach the module binding
    ("a comprehension target",          "S = 1\ndef f(xs):\n    ys = [S for S in xs]\n    return S.fire(1)\n", True),
    ("a generator-expression target",   "S = 1\ndef f(xs):\n    ys = list(S for S in xs)\n    return S.fire(1)\n", True),
    ("a class-body attribute",          "S = 1\ndef f(x):\n    class C:\n        S = 2\n    return S.fire(x)\n", True),
    ("a NESTED function's parameter",   "S = 1\ndef f(x):\n    def g(S):\n        return S\n    return S.fire(x)\n", True),
    ("a `global` read with no assign",  "S = 1\ndef f(x):\n    global S\n    return S.fire(x)\n", True),
]


def _marked_call(resolver):
    """The `S.fire(...)` call this matrix asks about — exactly one per fixture."""
    calls = [n for n in ast.walk(resolver.tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "fire"]
    assert len(calls) == 1, calls
    return calls[0]


@pytest.mark.parametrize("label,src,outward", GRAMMAR, ids=[g[0].replace(" ", "-") for g in GRAMMAR])
def test_the_resolver_answers_every_binding_form(label, src, outward):
    """Every form the LANGUAGE has for binding a name, answered by CPython's own scope analysis rather than by an
    enumeration someone maintains. `:=` and the `match` capture are the round-7 reviewer's two; the rest are
    research's announced attack list plus the must-not-shadow half."""
    r = sr.Resolver(src, f"<{label}>")
    assert r.refers_to_module_binding(_marked_call(r), "S") is outward, label


def test_the_matrix_covers_both_answers_and_the_reviewers_two_forms():
    """A matrix of all-True or all-False rows would pass a resolver that answers a constant (the unfailable class)."""
    answers = {g[2] for g in GRAMMAR}
    assert answers == {True, False} and sum(1 for g in GRAMMAR if g[2]) >= 4 and sum(1 for g in GRAMMAR if not g[2]) >= 4
    labels = " ".join(g[0] for g in GRAMMAR)
    assert "assignment expression" in labels and "match capture" in labels


def test_a_constant_answering_resolver_fails_this_matrix():
    """RULE ZERO's negative control, executed: a resolver that always says True, and one that always says False,
    each fail at least one row — so a green matrix is evidence about the resolver and not about the fixtures."""
    for constant in (True, False):
        wrong = [g[0] for g in GRAMMAR if g[2] is not constant]
        assert wrong, f"a resolver answering {constant} constantly would pass every row"


def test_the_module_block_is_the_binding_itself():
    """A use at module level IS the declared binding, not a reference resolving outward to one."""
    r = sr.Resolver("S = 1\nS.fire(1)\n")
    assert r.refers_to_module_binding(_marked_call(r), "S") is True


def test_site_names_are_the_module_level_declare_site_targets():
    r = sr.Resolver("from .census import declare_site\nA = declare_site('a')\nB = declare_site('b')\n"
                    "def f():\n    C = declare_site('c')\n    return C\n")
    assert r.site_names() == {"A", "B"}          # C is not a module-level binding


def test_a_global_rebinding_of_a_site_is_refused_not_resolved():
    """`global S` alone reads the site; `global S` WITH an assignment replaces the module binding for every other
    reader, which no static reading can account for — refused by name, the reviewer's sanctioned alternative."""
    r = sr.Resolver("from .census import declare_site\nS = declare_site('s')\ndef f(o):\n    global S\n    S = o\n")
    with pytest.raises(sr.UnresolvableScope, match="replaces the declared site"):
        r.refuse_site_rebindings(r.site_names())
    clean = sr.Resolver("from .census import declare_site\nS = declare_site('s')\ndef f():\n    global S\n    return S.fire(1)\n")
    clean.refuse_site_rebindings(clean.site_names())          # a read-only global is not refused


def test_two_scopes_on_one_line_are_joined_in_source_order():
    """symtable exposes no column, so same-line blocks are joined in source order. The control that would catch
    that order diverging: two generator expressions on ONE line binding DIFFERENT names (`asof/resolve.py:445` is
    the real instance that made refusing them unusable)."""
    r = sr.Resolver("def f(xs, ys):\n    return list((aaa for aaa in xs)) + list((bbb for bbb in ys))\n")
    gens = sorted((n for n in ast.walk(r.tree) if isinstance(n, ast.GeneratorExp)), key=lambda n: n.col_offset)
    got = [sorted(x for x in r.block_of(g.elt).get_identifiers() if not x.startswith(".")) for g in gens]
    assert got == [["aaa"], ["bbb"]], got


def test_every_product_and_evidence_module_resolves():
    """The resolver refuses what it cannot join, so 'it refuses nothing on the real tree' is a claim to execute:
    a resolver that refused one real module would take the scan with it."""
    refused = []
    for f in sorted((ROOT / "src" / "veracium").rglob("*.py")) + sorted(EVIDENCE.glob("*.py")):
        try:
            r = sr.Resolver(f.read_text(), str(f)); r.refuse_site_rebindings(r.site_names())
        except sr.UnresolvableScope as e:
            refused.append(f"{f}: {e}")
    assert refused == [], refused


def test_same_line_blocks_of_DIFFERENT_kinds_resolve_to_their_own_owners():
    """Research's stage-1 BLOCKING 2. The same-line join is by (line, symtable's block name) and consumes each
    key's list in source order; the control shipped with it was two GENEXPRS, both arms the same kind. If AST
    traversal order and symtable's child order ever diverged, the plausible cause is a PER-KIND difference in how
    each side enumerates, and a same-kind pair cannot see it. So: mixed kinds on one line, each binding a
    different name, plus a NESTED same-kind pair where one block is inside the other rather than beside it —
    the two shapes where an order assumption would break differently."""
    mixed = sr.Resolver("def f(xs):\n    return (lambda aaa: aaa)(1), list(bbb for bbb in xs)\n")
    lam = [n for n in ast.walk(mixed.tree) if isinstance(n, ast.Lambda)][0]
    gen = [n for n in ast.walk(mixed.tree) if isinstance(n, ast.GeneratorExp)][0]
    assert sorted(x for x in mixed.block_of(lam.body).get_identifiers() if not x.startswith(".")) == ["aaa"]
    assert sorted(x for x in mixed.block_of(gen.elt).get_identifiers() if not x.startswith(".")) == ["bbb"]
    nested = sr.Resolver("def f(xs):\n    return list(ooo for ooo in (iii for iii in xs))\n")
    gens = [n for n in ast.walk(nested.tree) if isinstance(n, ast.GeneratorExp)]
    owners = {sorted(x for x in nested.block_of(g.elt).get_identifiers() if not x.startswith("."))[0] for g in gens}
    assert owners == {"ooo", "iii"}, owners          # each element resolves inside its OWN comprehension
    # and the property the join exists for, across kinds: a site read in the lambda is the module's, a site
    # REBOUND as the lambda's parameter is not
    r = sr.Resolver("S = 1\ndef f(xs):\n    return (lambda q: S.fire(q)), list(S for S in xs)\n")
    inner = [n for n in ast.walk(r.tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "fire"][0]
    assert r.refers_to_module_binding(inner, "S") is True
    r2 = sr.Resolver("S = 1\ndef f(xs):\n    return (lambda S: S.fire(1)), 2\n")
    inner2 = [n for n in ast.walk(r2.tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "fire"][0]
    assert r2.refers_to_module_binding(inner2, "S") is False


# (label, source, does `S` at the single `S.fire(...)` resolve to the MODULE binding?)
COMPREHENSIONS = [
    ("module-level listcomp rebinding S",      "S = 1\nxs = [S.fire(1) for S in (1,2)]\n", False),
    ("module-level genexpr rebinding S",       "S = 1\nxs = list(S.fire(1) for S in (1,2))\n", False),
    ("listcomp in a function rebinding S",     "S = 1\ndef f(xs):\n    return [S.fire(1) for S in xs]\n", False),
    ("dictcomp rebinding S (its value)",       "S = 1\nxs = {1: S.fire(1) for S in (1,)}\n", False),
    ("setcomp rebinding S",                    "S = 1\ndef f(xs):\n    return {S.fire(1) for S in xs}\n", False),
    ("a nested comprehension's INNER target",  "S = 1\nxs = [[S.fire(1) for S in row] for row in (1,)]\n", False),
    ("a nested comprehension's OUTER target",  "S = 1\nxs = [[S.fire(1) for q in row] for S in (1,)]\n", False),
    ("a genexpr nested in a listcomp",         "S = 1\nxs = [list(S.fire(1) for S in row) for row in (1,)]\n", False),
    ("a SECOND generator's iterable",          "S = 1\nxs = [q for S in (1,) for q in S.fire((2,))]\n", False),
    ("an `if` clause of the comprehension",    "S = 1\nxs = [q for S in (1,) if S.fire(q)]\n", False),
    # the must-NOT-shadow half: the first iterable is the enclosing scope's, and an unrebound name is the module's
    ("the FIRST iterable (enclosing scope)",   "S = 1\nxs = [q for S in S.fire((1,2))]\n", True),
    ("a listcomp that does NOT rebind S",      "S = 1\nxs = [S.fire(q) for q in (1,2)]\n", True),
    ("a function listcomp not rebinding S",    "S = 1\ndef f(xs):\n    return [S.fire(q) for q in xs]\n", True),
    ("nested, neither rebinding S",            "S = 1\nxs = [[S.fire(1) for q in row] for row in (1,)]\n", True),
]


@pytest.mark.parametrize("label,src,outward", COMPREHENSIONS, ids=[c[0].replace(" ", "-") for c in COMPREHENSIONS])
def test_a_comprehension_target_shadows_on_every_interpreter(label, src, outward):
    """Research's stage-2 BLOCKING, and the reason it is worth a matrix of its own: the answer used to DEPEND ON
    THE INTERPRETER. PEP 709 inlines list/set/dict comprehensions from 3.12, so they have a symtable block on
    3.10 and 3.11 and none on 3.12+. With the block, symtable answers; without it the nodes are owned by the
    enclosing block, and at module level `refers_to_module_binding` short-circuits to True — so a `.fire()` on a
    name the comprehension REBINDS read as the module's site on 3.12 and not on 3.10. Both consumers take that at
    face value: the scan computes `bound` from it and the transform decides WHAT TO REWRITE from it.

    PEP 709 removed the BLOCK, not the SCOPING, and the interpreter says so itself — the control below runs it.
    CI runs 3.10, 3.11, 3.12 and 3.13, so this matrix asserting the SAME answers on all four is the cross-version
    control: on two of them it exercises the symtable path and on two the inlined path."""
    r = sr.Resolver(src, f"<{label}>")
    assert r.refers_to_module_binding(_marked_call(r), "S") is outward, label


def test_the_interpreter_itself_agrees_that_a_comprehension_target_does_not_leak():
    """The premise the matrix above rests on, EXECUTED rather than cited — on whichever interpreter is running."""
    S = "the module binding"
    seen = [S for S in ("a", "b")]                                  # noqa: F841 — the point is the rebinding
    assert seen == ["a", "b"] and S == "the module binding"
    import symtable as _st
    inlined = [c.get_name() for c in _st.symtable("[x for x in y]", "<p>", "exec").get_children()] == []
    assert inlined is (sys.version_info >= (3, 12)), (sys.version_info[:2], inlined)


def test_the_comprehension_matrix_exercises_both_answers_and_both_regimes():
    """A matrix of all-False rows would pass a resolver that answers False inside any comprehension — which would
    break the first iterable and every unrebound read. Both halves are present and counted."""
    answers = {c[2] for c in COMPREHENSIONS}
    assert answers == {True, False}
    assert sum(1 for c in COMPREHENSIONS if not c[2]) >= 8 and sum(1 for c in COMPREHENSIONS if c[2]) >= 4
    kinds = " ".join(c[0] for c in COMPREHENSIONS)
    for kind in ("listcomp", "genexpr", "dictcomp", "setcomp", "nested", "FIRST iterable"):
        assert kind in kinds, kind


def test_a_module_level_rebinding_of_a_site_is_refused_including_a_walrus_in_a_comprehension():
    """Research's stage-2 held probe, answered before the pin rather than after it. PEP 572 binds a walrus in the
    ENCLOSING scope ON PURPOSE, so at module level `[(S := q) for q in ...]` genuinely reassigns the site's name —
    and every static reading still says "S is the module binding", which is TRUE OF THE NAME and false of the
    object. The refusal used to cover only `global S` with an assignment inside a function; it now covers any
    module-level rebinding, which is the property that was actually meant."""
    decl = "from .census import declare_site\nS = declare_site('t')\n"
    for label, src in {
        "a walrus inside a comprehension": decl + "xs = [(S := q) for q in (1, 2)]\n",
        "a plain second assignment":       decl + "S = object()\n",
        "a module-level for target":       decl + "for S in (1, 2):\n    pass\n",
        "a module-level with-as":          decl + "import contextlib\nwith contextlib.nullcontext() as S:\n    pass\n",
    }.items():
        r = sr.Resolver(src, f"<{label}>")
        with pytest.raises(sr.UnresolvableScope, match="bound .* times at module level"):
            r.refuse_site_rebindings(r.site_names())
    # the controls: a comprehension's own TARGET is comprehension-local and binds nothing at module level, and a
    # function-local name of the same spelling is a shadow, not a rebinding — neither may be refused
    for label, src in {
        "a comprehension's for target":    decl + "xs = [S for S in (1, 2)]\n",
        "a function-local shadow":         decl + "def f():\n    S = object()\n    return S\n",
        "a nested function's parameter":   decl + "def f(S):\n    return S\n",
        "the declaration alone":           decl,
    }.items():
        r = sr.Resolver(src, f"<{label}>")
        r.refuse_site_rebindings(r.site_names())
    # and the runtime confirms the premise the refusal rests on
    ns = {"declare_site": lambda i: f"<site {i}>"}
    exec("S = declare_site('t')\nxs = [(S := q) for q in (1, 2)]\n", ns)
    assert ns["S"] == 2, "PEP 572 binds the walrus in the enclosing scope; the site object is replaced"


# (label, the listcomp form, the genexpr form, the expected answer) — the SAME question in both spellings
REGIME_PAIRS = [
    ("the first iterable",        "S = 1\nxs = [q for S in S.fire((1,2))]\n",          "S = 1\nxs = list(q for S in S.fire((1,2)))\n", True),
    ("the element, rebound",      "S = 1\nxs = [S.fire(1) for S in (1,2)]\n",          "S = 1\nxs = list(S.fire(1) for S in (1,2))\n", False),
    ("a second iterable",         "S = 1\nxs = [q for S in (1,) for q in S.fire((2,))]\n", "S = 1\nxs = list(q for S in (1,) for q in S.fire((2,)))\n", False),
    ("an `if` clause",            "S = 1\nxs = [q for S in (1,) if S.fire(q)]\n",      "S = 1\nxs = list(q for S in (1,) if S.fire(q))\n", False),
    ("the element, NOT rebound",  "S = 1\nxs = [S.fire(q) for q in (1,)]\n",           "S = 1\nxs = list(S.fire(q) for q in (1,))\n", True),
    ("inside a function",         "S = 1\ndef f():\n    return [q for S in S.fire((1,))]\n", "S = 1\ndef f():\n    return list(q for S in S.fire((1,)))\n", True),
]


@pytest.mark.parametrize("label,listcomp,genexpr,outward", REGIME_PAIRS, ids=[p[0].replace(" ", "-") for p in REGIME_PAIRS])
def test_both_scope_regimes_agree_and_a_genexpr_proves_the_other_one_locally(label, listcomp, genexpr, outward):
    """THE TECHNIQUE, and it is the reusable part: a GENERATOR EXPRESSION keeps its own symtable block on EVERY
    version, so on 3.12 it exercises exactly the branch a LIST COMPREHENSION takes on 3.10 and 3.11. Pairing the
    two spellings of one question therefore tests BOTH regimes on ONE interpreter — a local cross-version control,
    where the version matrix alone can only be checked by CI.

    It is not hypothetical: the first version of this fix handled the first-iterable rule on the inlined path
    only, every local test passed, and CI's 3.10 and 3.11 jobs went red on precisely the row below that asserts
    it. The pair would have caught it here."""
    got = [sr.Resolver(src, f"<{label}>") for src in (listcomp, genexpr)]
    answers = [r.refers_to_module_binding(_marked_call(r), "S") for r in got]
    assert answers == [outward, outward], (label, answers)


def test_the_regime_pairs_really_do_take_different_paths():
    """The control for the technique itself: if a genexpr and a listcomp were handled identically on this
    interpreter, the pairs above would prove nothing. On 3.12 the listcomp has NO block and the genexpr has one;
    before 3.12 both have one, and the pairs still assert the shared rules."""
    import symtable as _st
    lc = [c.get_name() for c in _st.symtable("[x for x in y]", "<p>", "exec").get_children()]
    ge = [c.get_name() for c in _st.symtable("(x for x in y)", "<p>", "exec").get_children()]
    assert ge == ["genexpr"], ge
    if sys.version_info >= (3, 12):
        assert lc == [], lc                      # inlined: the pairs exercise two DIFFERENT paths here
    else:
        assert lc == ["listcomp"], lc            # both blocked: the pairs still assert the same answers


def test_the_site_question_refuses_until_the_rebinding_guarantee_is_established():
    """Research's stage-1 note on the stage-2 fix, made a MECHANISM rather than a docstring sentence. There are
    two questions here and they are not the same one: `refers_to_module_binding` answers whether the NAME
    resolves to the module binding, and both consumers need whether the receiver IS THE DECLARED SITE OBJECT.
    They coincide only while the module name is bound exactly once, which `refuse_site_rebindings` establishes —
    in a different function. A guarantee held in the CALL ORDER is one a later caller or a refactor can drop
    with nothing failing, because every existing test happens to run both. So the site question refuses until
    the guarantee exists, and the name question stays available under its honest name."""
    src = "from .census import declare_site\nS = declare_site('t')\nr = S.fire(1)\n"
    r = sr.Resolver(src)
    call = _marked_call(r)
    assert r.refers_to_module_binding(call, "S") is True          # the NAME question: answerable immediately
    with pytest.raises(sr.UnresolvableScope, match="before `refuse_site_rebindings`"):
        r.refers_to_declared_site(call, "S")                      # the SITE question: refused until established
    r.refuse_site_rebindings(r.site_names())
    assert r.refers_to_declared_site(call, "S") is True           # and answerable after
    # a name the guarantee was never asked about stays refused, even once OTHERS are cleared
    with pytest.raises(sr.UnresolvableScope, match="before `refuse_site_rebindings`"):
        r.refers_to_declared_site(call, "some_other_name")
    # and both consumers ask the SITE question, not the name one
    for mod in ("installed_sites.py", "inv7_uninstrument.py"):
        text = (EVIDENCE / mod).read_text()
        assert "refers_to_declared_site(" in text, mod
        assert "refers_to_module_binding(" not in text, f"{mod} asks the NAME question where it needs the SITE one"
