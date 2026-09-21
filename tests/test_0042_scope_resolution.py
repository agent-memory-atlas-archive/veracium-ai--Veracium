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
import subprocess
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
    # The expected message is named per row, because the WALRUS row is answered by a different reading on each
    # side of PEP 709: on 3.12+ the comprehension is inlined and its store is in the module's own code object
    # (rule A counts two); on 3.10/3.11 it is a separate code object that binds the ENCLOSING scope, which the
    # interpreter's module-level reading cannot see at all, and symtable answers it instead (rule C).
    inlined = sys.version_info >= (3, 12)
    for label, src, expected in [
        ("a walrus inside a comprehension", decl + "xs = [(S := q) for q in (1, 2)]\n",
         "bound 2 times in the module's own code" if inlined
         else "assigns the MODULE-level name"),
        ("a plain second assignment",       decl + "S = object()\n", "bound 2 times"),
        ("a module-level for target",       decl + "for S in (1, 2):\n    pass\n", "bound 2 times"),
        ("a module-level with-as",          decl + "import contextlib\nwith contextlib.nullcontext() as S:\n    pass\n",
         "bound 2 times"),
    ]:
        r = sr.Resolver(src, f"<{label}>")
        with pytest.raises(sr.UnresolvableScope, match=expected):
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


# ---------------------------------------------------------------------------------------------------------------
# Round 8e — research's stage-2 finding: SIX module-level binding spellings were accepted, because the refusal's
# only reading was an AST walk over `ast.Name` in a `Store` context and none of the six is one. The matrix below
# is the binding grammar of a MODULE SCOPE, both halves, and it is the negative space of the `GRAMMAR` table
# above: there the question was "which binding does this name see", here it is "is the declared site still the
# object this name denotes". Every row is a module whose first two lines declare a site called `S`.
# ---------------------------------------------------------------------------------------------------------------
DECL = "from .census import declare_site\nS = declare_site('t')\n"

# (label, the source after the declaration, must the refusal fire?)
REBINDING_MATRIX = [
    # --- the six research found. None is an `ast.Name` in a `Store` context; all six replace or remove the site.
    ("import os as S",                   "import os as S\n", True),
    ("from os import path as S",         "from os import path as S\n", True),
    ("except Exception as S",            "try:\n    pass\nexcept Exception as S:\n    pass\n", True),
    ("del S",                            "del S\n", True),
    ("def S()",                          "def S():\n    pass\n", True),
    ("class S",                          "class S:\n    pass\n", True),
    # --- their neighbours in the same grammar, none of them named by anyone
    ("async def S()",                    "async def S():\n    pass\n", True),
    ("import os as S inside a try",      "try:\n    import os as S\nexcept ImportError:\n    pass\n", True),
    ("a match capture",                  "match 1:\n    case S:\n        pass\n", True),
    ("a match as-pattern",               "match 1:\n    case int() as S:\n        pass\n", True),
    # --- the forms the AST walk already saw, which must keep being refused
    ("a plain second assignment",        "S = object()\n", True),
    ("an augmented assignment",          "S += 1\n", True),
    ("an annotated assignment",          "S: int = 1\n", True),
    ("a module-level for target",        "for S in (1, 2):\n    pass\n", True),
    ("a module-level with-as",           "import contextlib\nwith contextlib.nullcontext() as S:\n    pass\n", True),
    ("tuple unpacking",                  "(S, y) = (1, 2)\n", True),
    ("starred unpacking",                "[*S, y] = (1, 2, 3)\n", True),
    ("a module-level walrus",            "if (S := 1):\n    pass\n", True),
    # --- bound from INSIDE a nested code object, at the module scope: the half rule A cannot see
    ("a walrus in a listcomp",           "xs = [q for q in (1, 2) if (S := q)]\n", True),
    ("a walrus in a genexpr",            "xs = list(q for q in (1, 2) if (S := q))\n", True),
    ("`global S` assigned in a function", "def f():\n    global S\n    S = 1\n", True),
    ("`global S` deleted in a function",  "def f():\n    global S\n    del S\n", True),
    ("`global S` in a class body",        "class K:\n    global S\n    S = 1\n", True),
    ("`global S` two scopes down",        "def outer():\n    def inner():\n        global S\n        S = 1\n"
                                          "    return inner\n", True),
    # --- the other half: an over-strict refusal is a refusal of CORRECT code, and it is the half a matrix of
    # --- all-True rows would never catch. None of these replaces the site object.
    ("the declaration alone",            "", False),
    ("a listcomp target",                "xs = [S for S in (1, 2)]\n", False),
    ("a genexpr target",                 "xs = list(S for S in (1, 2))\n", False),
    ("a setcomp target",                 "a = {S for S in (1, 2)}\n", False),
    ("a dictcomp target",                "b = {S: S for S in (1, 2)}\n", False),
    ("a nested comprehension target",    "b = [[S for S in r] for r in ((1,),)]\n", False),
    ("a function-local shadow",          "def f():\n    S = 1\n    return S\n", False),
    ("a function parameter",             "def f(S=None):\n    return S\n", False),
    ("a lambda parameter",               "f = lambda S: S\n", False),
    ("a class-body attribute",           "class K:\n    S = 1\n", False),
    ("except-as inside a function",      "def f():\n    try:\n        pass\n    except Exception as S:\n"
                                         "        pass\n", False),
    ("a for target inside a function",   "def f():\n    for S in (1, 2):\n        pass\n", False),
    ("`global S` READ in a function",    "def f():\n    global S\n    return S\n", False),
    ("an ordinary module-level use",     "with S.consult():\n    pass\n", False),
    ("an ordinary use in a function",    "def f():\n    with S.consult():\n        return 1\n", False),
    # --- research's Q2: counting binding OPERATIONS cannot tell "bound twice in sequence" from "bound once in
    # --- two mutually exclusive branches". All three below count more than one and are REFUSED, and the
    # --- decision is recorded here rather than inherited from the counting: a static reading cannot tell a
    # --- dead branch from a live one unless the condition is a literal the compiler folds, and a site declared
    # --- ONCE and UNCONDITIONALLY is the premise of the scan this refusal protects. The `TYPE_CHECKING` row is
    # --- the sharpest — that branch never executes, so the refusal is false IN FACT — and the trade is taken
    # --- knowingly: it needs a site name to collide with a type-checking alias, and no module in the tree
    # --- does that. `if False:` sits two rows below it, ACCEPTED, because the compiler folds it away; the two
    # --- are adjacent so the asymmetry explains itself where a reader meets it.
    ("a try/except import fallback",     "try:\n    import os as S\nexcept ImportError:\n    import sys as S\n",
     True),
    ("a site declared in both branches", "flag = True\nif flag:\n    S = declare_site('a')\nelse:\n"
                                         "    S = declare_site('b')\n", True),
    ("an `if TYPE_CHECKING` import",     "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n"
                                         "    import os as S\n", True),
    ("a dead `if False` branch",         "if False:\n    S = 1\n", False),
    ("a bare annotation",                "S: int\n", False),
]


def _refusal(module, src):
    """The refusal message for one matrix row, or None if the row was accepted."""
    r = module.Resolver(DECL + src, "<matrix>")
    try:
        r.refuse_site_rebindings(r.site_names())
        return None
    except module.UnresolvableScope as e:
        return str(e)


def test_every_module_level_binding_form_is_refused_and_no_shadow_is():
    """The whole matrix at once, reporting EVERY disagreement rather than the first — a row-per-run matrix hides
    how much of the grammar a regression takes with it. Both halves are asserted because an always-refusing
    resolver would pass the first half and refuse the entire product tree."""
    wrong = []
    for label, src, must_refuse in REBINDING_MATRIX:
        got = _refusal(sr, src)
        if (got is not None) != must_refuse:
            wrong.append(f"{label}: expected {'a refusal' if must_refuse else 'acceptance'}, got {got!r}")
    assert not wrong, "\n".join(wrong)


def test_the_rebinding_matrix_covers_both_answers_and_the_six_forms_by_name():
    """The table's own shape, so a row silently deleted from either half is visible."""
    assert len(REBINDING_MATRIX) == 44
    assert len({row[0] for row in REBINDING_MATRIX}) == 44, "labels are the ids; they must be distinct"
    refused = [row for row in REBINDING_MATRIX if row[2]]
    assert len(refused) == 27 and len(REBINDING_MATRIX) - len(refused) == 17
    labels = " ".join(row[0] for row in REBINDING_MATRIX)
    for form in ("import os as S", "from os import path as S", "except Exception as S", "del S", "def S()",
                 "class S", "a walrus in a genexpr", "`global S` READ in a function", "a listcomp target",
                 "an `if TYPE_CHECKING` import", "a dead `if False` branch", "a bare annotation"):
        assert form in labels, form


def test_the_interpreter_confirms_each_spelling_really_does_replace_the_site():
    """The premise under the first half, EXECUTED. A refusal of a form that does not actually replace the object
    would be a refusal of correct code, so the six are run and the name is read afterwards: in every case `S` is
    no longer the site the declaration returned. This is the 'true of the name, false of the object' distinction
    the whole refusal exists to keep, and nothing here is derived from reading the grammar."""
    site = object()
    for label, src, expect_gone in [
        ("import os as S",           "import os as S\n", True),
        ("from os import path as S", "from os import path as S\n", True),
        ("except Exception as S",    "try:\n    raise ValueError()\nexcept Exception as S:\n    pass\n", True),
        ("del S",                    "del S\n", True),
        ("def S()",                  "def S():\n    pass\n", True),
        ("class S",                  "class S:\n    pass\n", True),
        ("a walrus in a genexpr",    "xs = list(q for q in (1, 2) if (S := q))\n", True),
        ("`global S` in a function", "def f():\n    global S\n    S = 1\nf()\n", True),
        ("a listcomp target",        "xs = [S for S in (1, 2)]\n", False),
        ("a function-local shadow",  "def f():\n    S = 1\n    return S\nf()\n", False),
    ]:
        ns = {"declare_site": lambda i: site}
        exec("S = declare_site('t')\n" + src, ns)
        still = ns.get("S", None) is site
        assert still is (not expect_gone), f"{label}: after execution S is {'still' if still else 'no longer'} the site"


def _mutant(old, new):
    """The resolver with one rule disabled, loaded as its own module. A rule that no row depends on is a rule
    that can be deleted without anyone noticing, which is the dead-check taxonomy's UNFAILABLE entry."""
    src = (EVIDENCE / "scope_resolution.py").read_text()
    assert src.count(old) == 1, f"the mutant's anchor {old!r} matched {src.count(old)} times"
    path = pathlib.Path(__import__("tempfile").mkdtemp()) / "scope_resolution_mutant.py"
    path.write_text(src.replace(old, new))
    return _load(f"scope_resolution_mutant_{abs(hash(old))}", path)


RULE_A = ("            if len(executed) > 1:", "            if False:")
RULE_C = ("                if sym.is_global() and sym.is_assigned():", "                if False:")


def test_both_readings_are_load_bearing_and_neither_over_refuses():
    """Disable one rule in the SOURCE and the matrix must redden — the reviewer's next move, made first. Two
    readings remain, both of them the language's own, and each owns part of the grammar:

      A  the module's own COMPILED CODE OBJECT binds the name more than once. Total over syntax by
         construction. Sole catcher of every rebinding performed by this scope, whatever its spelling.
      C  a NESTED block assigns the name as a global (`is_global()` AND `is_assigned()`). Sole catcher of
         `global` from a function, a class body or two scopes down, and of a comprehension's walrus, which
         binds the enclosing scope with no `global` statement in the source (though
         `symtable` synthesises the declared-global flag for it on 3.10/3.11, which is why the two predicates
         turn out to agree — see `test_the_two_global_predicates_agree_over_the_whole_matrix`).

    A third reading — refuse when the two disagree — was written here and deleted; the paragraph in
    `scope_resolution.py` says why, and `test_no_reading_of_this_module_is_a_hand_enumeration` keeps the walk
    it cross-checked from coming back. Each mutant is also asked whether it refuses CORRECT code, because a
    mutant that reddens the acceptance half proves nothing about the rule it disabled."""
    for rule, (old, new_), sole in [("A", RULE_A, "a plain second assignment"),
                                    ("C", RULE_C, "`global S` assigned in a function")]:
        mutant = _mutant(old, new_)
        survivors = [row[0] for row in REBINDING_MATRIX if row[2] and _refusal(mutant, row[1]) is None]
        assert sole in survivors, (rule, sole, survivors)
        wrongly = [row[0] for row in REBINDING_MATRIX if not row[2] and _refusal(mutant, row[1]) is not None]
        assert not wrongly, f"rule {rule}'s mutant refuses correct code, so the redness is not the rule's: {wrongly}"


def test_the_deleted_third_reading_would_refuse_correct_code():
    """The deletion, kept honest. Round 8e first ADDED a rule that refused when the interpreter's reading and an
    AST walk disagreed about where a name is bound, and demoted it to a tripwire when its own mutant showed it
    caught nothing the other two did. Running two rows research proposed as must-accept showed what it actually
    fires on: a dead branch the compiler folds away, and a bare annotation whose target carries a `Store`
    context and binds nothing. Both are correct code. This test rebuilds that rule and asserts it refuses them,
    so the reason for the deletion is a RESULT and not a remark in a docstring.

    THE LIMIT, STATED SO A LATER READER DOES NOT OVERREAD IT (research's note): the rule is DELETED, so this
    asserts a property of a REBUILD written here, not of any code that ever shipped. It cannot be bound to what
    D was, because what D was is only in the history. What it can do — and does, below — is show that the two
    rows are refused by the rebuilt reading ALONE: disabling either surviving rule leaves them accepted, so the
    refusal being demonstrated is the rebuilt one's and not a side effect of A or C."""
    src = (EVIDENCE / "scope_resolution.py").read_text()
    anchor = "            if len(executed) > 1:"
    assert src.count(anchor) == 1
    restored = src.replace(anchor, """            walked = []

            def _walk(node, out):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                        continue
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store) and child.id == n:
                        out.append(child.lineno)
                    _walk(child, out)
            _walk(self.tree, walked)
            if sorted(set(walked)) != executed_lines:
                raise UnresolvableScope(f"site {n!r}: the two readings disagree")
            if len(executed) > 1:""")
    tmp = pathlib.Path(__import__("tempfile").mkdtemp()) / "with_d.py"
    tmp.write_text(restored)
    with_d = _load("scope_resolution_with_deleted_rule", tmp)
    for label in ("a dead `if False` branch", "a bare annotation"):
        body = next(row[1] for row in REBINDING_MATRIX if row[0] == label)
        assert _refusal(sr, body) is None, f"{label} must be accepted by the shipped resolver"
        message = _refusal(with_d, body)
        assert message is not None and "readings disagree" in message, \
            f"the deleted rule no longer refuses {label}, so the stated reason for deleting it has gone stale"
        # and the refusal is the rebuilt reading's alone: neither surviving rule refuses these rows either way
        for rule, pair in (("A", RULE_A), ("C", RULE_C)):
            assert _refusal(_mutant(*pair), body) is None, (
                f"{label} is refused with rule {rule} disabled, so the rebuilt rule is not what refuses it and "
                f"this test is measuring something else")


_AST_CONSULTATION_PROBE = r"""
# Counts every consultation of the AST during `refuse_site_rebindings`, for the shipped resolver and for two
# mutants that reinstate an enumeration. The counters are installed BEFORE any of the three modules is imported,
# so a module-level `from ast import walk as _w` binds to a counter too — which a sabotage-after-import control
# would miss. Runs as a SUBPROCESS: it monkeypatches the stdlib `ast` module, and doing that in the session would
# be fixture state living outside the thing under test, which is this round's other recurring defect.
import ast, importlib.util, pathlib, sys, tempfile

CALLS = {"n": 0}
REAL_STORE = ast.Store

class _StoreMeta(type):
    def __instancecheck__(cls, obj):
        CALLS["n"] += 1
        return isinstance(obj, REAL_STORE)

for _name in ("walk", "iter_child_nodes", "iter_fields", "dump"):
    def _wrapper(*a, _real=getattr(ast, _name), **k):
        CALLS["n"] += 1
        return _real(*a, **k)
    setattr(ast, _name, _wrapper)
ast.Store = _StoreMeta("Store", (), {})

def load(name, text):
    d = pathlib.Path(tempfile.mkdtemp()); f = d / (name + ".py"); f.write_text(text)
    sp = importlib.util.spec_from_file_location(name, f); m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m; sp.loader.exec_module(m); return m

SRC = pathlib.Path(sys.argv[1]).read_text()
ANCHOR = "        declared_here = self.site_names()"
assert SRC.count(ANCHOR) == 1, "the probe's anchor moved; the mutants are not being injected"
ALIASED = SRC.replace(ANCHOR, "        from ast import walk as _w, Store as _St\n"
                              "        _back = [n.lineno for n in _w(self.tree)\n"
                              "                 if n.__class__.__name__ == 'Name' and isinstance(n.ctx, _St)]\n" + ANCHOR)
TOPLEVEL = SRC.replace("import symtable\n", "import symtable\nfrom ast import walk as _topwalk\n", 1) \
              .replace(ANCHOR, "        _back = [n for n in _topwalk(self.tree)]\n" + ANCHOR)

DECL = "from .census import declare_site\nS = declare_site('t')\n"
ROWS = [("import os as S\n", True), ("del S\n", True), ("S = object()\n", True),
        ("def f():\n    global S\n    S = 1\n", True), ("xs = [S for S in (1, 2)]\n", False),
        ("if False:\n    S = 1\n", False), ("S: int\n", False), ("", False)]

for tag, text in (("SHIPPED", SRC), ("ALIASED", ALIASED), ("MODULE_ALIAS", TOPLEVEL)):
    m = load(tag.lower() + "_probe", text)
    built = [(m.Resolver(DECL + b, "<c>"), must) for b, must in ROWS]   # __init__ legitimately walks the AST
    CALLS["n"] = 0
    got = []
    for r, must in built:
        try:
            r.refuse_site_rebindings(r.site_names()); got.append(False)
        except m.UnresolvableScope:
            got.append(True)
    ok = got == [must for _, must in built]
    print(tag + "\t" + str(CALLS["n"]) + "\t" + str(ok))
"""


def test_the_refusal_never_consults_the_ast(tmp_path):
    """THE PROPERTY, MEASURED — replacing a text check that a rename defeated.

    Round 8e first gated this by refusing the strings `ast.Store`, `ast.walk` and `ast.iter_child_nodes` inside
    the refusal's source. Research defeated it in one line: `from ast import walk as _w, Store as _St` contains
    none of them, reinstates the whole enumeration, and the test passes. A text check for names is a narrow
    matcher, inside the test written to prevent narrow matchers — the finding's own class, one level up again.

    So the claim is measured instead. Every AST-walking callable is wrapped in a counter and `ast.Store` is
    replaced by a class whose instance checks count, BEFORE the resolver is imported; then a Resolver is built
    (its `__init__` legitimately walks the AST to index scopes, so the count is taken after), and the refusal is
    called. The shipped code must consult the AST ZERO times. Two mutants that reinstate a walk — one aliasing
    inside the function, one aliasing at module level, which a patch-after-import control could not see — must
    both be caught, and both must still return the right verdicts, so the redness is the property and not a
    broken mutant.

    TWO PROPERTIES OF THIS TEST THAT MUST SURVIVE ANY SIMPLIFICATION (research's note). Both mutants return
    CORRECT verdicts, so what goes red is the property and not a broken mutant. And the probe runs in a
    SUBPROCESS, because it monkeypatches the stdlib `ast` module and doing that in the session would be fixture
    state living outside the thing under test — this round's other recurring class, which would have leaked into
    every test that parses anything, under a shuffle, with no way to tell where it came from.
    """
    probe = tmp_path / "ast_consultation_probe.py"
    probe.write_text(_AST_CONSULTATION_PROBE)
    run = subprocess.run([sys.executable, str(probe), str(EVIDENCE / "scope_resolution.py")],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-2000:]
    rows = {}
    for line in run.stdout.strip().splitlines():
        tag, count, verdicts_ok = line.split("\t")
        rows[tag] = (int(count), verdicts_ok == "True")
    assert set(rows) == {"SHIPPED", "ALIASED", "MODULE_ALIAS"}, rows
    for tag, (_, verdicts_ok) in rows.items():
        assert verdicts_ok, f"{tag} returns wrong verdicts, so its count says nothing about the refusal"
    assert rows["SHIPPED"][0] == 0, (
        f"the refusal consulted the AST {rows['SHIPPED'][0]} times — it is supposed to decide from the compiled "
        f"code object and symtable alone, and an AST walk here is the enumeration round 8 removed")
    for tag in ("ALIASED", "MODULE_ALIAS"):
        assert rows[tag][0] > 0, f"the {tag} mutant reinstates an AST walk and this control did not see it"


def test_the_binding_count_matches_a_hand_count_on_modules_small_enough_to_count():
    """Research's third target: confirming the four opcode names against `dis.opmap` catches a RENAME and not an
    ADDITION. A new binding opcode in a future CPython would leave all four valid and the count SHORT, silently —
    the enumeration moved down a layer rather than vanishing, to a layer that changes rarely and fails loudly on
    rename, but a hand list all the same. So the reading is also checked against modules whose module-level
    bindings of one name can be counted by eye. A new opcode shows up here as a count that stopped matching.

    The last three rows are the other half: a binding that is NOT this scope's must not be counted."""
    for label, body, expected in [
        ("one plain assignment",             "S = 1\n", 1),
        ("two plain assignments",            "S = 1\nS = 2\n", 2),
        ("an assignment and a del",          "S = 1\ndel S\n", 2),
        ("assignment, import-as, del",       "S = 1\nimport os as S\ndel S\n", 3),
        ("three, one shadowed in a function", "S = 1\nS = 2\nS = 3\ndef f():\n    S = 4\n    return S\n", 3),
        ("one, plus a comprehension target", "S = 1\nxs = [S for S in (1, 2)]\n", 1),
        ("one, plus a class-body attribute", "S = 1\nclass K:\n    S = 2\n", 1),
    ]:
        got = sr.Resolver(body, f"<{label}>")._module_binding_ops("S")
        assert len(got) == expected, f"{label}: hand-counted {expected}, the reading found {len(got)} ({got})"


def test_the_interpreters_reading_is_read_at_the_right_lines():
    """`_module_binding_ops` reports LINES, and CPython has spelled an instruction's line three ways across the
    versions CI runs (3.10 `starts_line`, 3.11+ `positions.lineno`, 3.13 `line_number`). A version that adds a
    fourth would silently report line 0 for everything and every refusal message would lose its location, while
    the verdicts above stayed green — so the lines are asserted, not just the counts."""
    r = sr.Resolver(DECL + "import os as S\n", "<lines>")
    ops = r._module_binding_ops("S")
    assert [line for _, line in ops] == [2, 3], ops
    assert all(op in sr._MODULE_BINDING_OPS for op, _ in ops), ops
    assert "lines 2, 3" in (_refusal(sr, "import os as S\n") or ""), "the message must carry the lines"


def test_rule_A_is_the_interpreters_reading_and_not_a_second_node_list():
    """What makes rule A total is that it reads the compiled module, so a form nobody enumerated is counted like
    any other. The proof is that it is right about a form this test file never lists: the `__all__`-style
    conditional import below binds `S` twice with no `ast.Name` store in sight on either line."""
    src = "import sys\nif sys.platform:\n    import os as S\nelse:\n    from os import path as S\n"
    r = sr.Resolver(DECL + src, "<unlisted>")
    assert [line for _, line in r._module_binding_ops("S")] == [2, 5, 7], "the interpreter sees both branches"
    assert "bound 3 times" in (_refusal(sr, src) or "")
    # the condition is deliberately not a constant: `if 1:` is folded away and the `else` branch is never
    # compiled, so a folded example would have understated the interpreter's reading and passed for a wrong reason
    folded = sr.Resolver(DECL + "if 1:\n    import os as S\nelse:\n    from os import path as S\n", "<folded>")
    assert len(folded._module_binding_ops("S")) == 2, "the dead branch really is absent from the code object"


def test_the_opcode_names_are_confirmed_against_this_interpreters_table():
    """A check that reads opcodes BY NAME weakens silently if a name moves: every count falls to zero, every
    module is accepted, and nothing is red. The names are therefore confirmed against `dis.opmap` at import.
    The control is a copy of the module with one name misspelled, which must refuse to import at all."""
    import dis as _dis
    assert all(op in _dis.opmap for op in sr._MODULE_BINDING_OPS), sr._MODULE_BINDING_OPS
    broken = (EVIDENCE / "scope_resolution.py").read_text().replace('"DELETE_GLOBAL")', '"DELETE_GLOBAL_")', 1)
    path = pathlib.Path(__import__("tempfile").mkdtemp()) / "renamed_opcode.py"
    path.write_text(broken)
    with pytest.raises(RuntimeError, match="dis.opmap"):
        _load("scope_resolution_renamed_opcode", path)


def test_source_that_parses_but_does_not_compile_is_refused_not_raised_through():
    """`ast.parse` accepts text the compiler rejects, so `__init__` can succeed where the interpreter's reading
    cannot be taken at all. That is a refusal in this module's own vocabulary, not a bare SyntaxError escaping
    from the middle of a scan."""
    import ast as _ast
    assert _ast.parse("return 1"), "the premise: this parses"
    with pytest.raises(SyntaxError):
        compile("return 1", "<p>", "exec")
    r = sr.Resolver(DECL + "return 1\n", "<uncompilable>")
    with pytest.raises(sr.UnresolvableScope, match="parses but does not compile"):
        r.refuse_site_rebindings(r.site_names())


def test_a_reading_that_finds_nothing_is_a_broken_reading_not_a_clean_module():
    """The failure mode of the guard above, one level in: if the interpreter's reading ever returns EMPTY for a
    name this module declares at module level, the reading is broken and every rebinding would be accepted in
    silence. An empty reading is a refusal, and the control is the same module read normally."""
    r = sr.Resolver(DECL + "S = object()\n", "<blinded>")
    assert r.site_names() == {"S"}
    with pytest.raises(sr.UnresolvableScope, match="bound 2 times"):
        r.refuse_site_rebindings(r.site_names())
    r._module_binding_ops = lambda name: []                      # the reading goes blind
    with pytest.raises(sr.UnresolvableScope, match="the reading is broken"):
        r.refuse_site_rebindings(r.site_names())


def test_a_refusal_never_claims_a_global_statement_the_module_does_not_contain():
    """CI found this on 3.10 and 3.11, and it was a FALSE SENTENCE IN A REFUSAL, not a stale expectation.

    Rule C chose its wording with `is_declared_global()`, on the assumption that the flag means the source said
    `global`. It does not: for a WALRUS inside a comprehension, `symtable` synthesises the flag, and the refusal
    told the reader `` `global S` with an assignment `` about a module containing no `global` anywhere. A
    refusal is read by someone deciding what to change; sending them to look for a statement that is not there
    is worse than saying less. The message now names both spellings and claims neither.

    The assertion is version-independent by construction — on 3.12 the row is answered by rule A, whose message
    also contains no such claim — so this test does not encode which rule answers it."""
    body = "xs = [(S := q) for q in (1, 2)]\n"
    source = DECL + body
    assert "global" not in source, "the premise: this module contains no `global` statement"
    message = _refusal(sr, body)
    assert message is not None, "a walrus in a comprehension rebinds the site and must be refused"
    assert "`global S` with an assignment" not in message, (
        f"the refusal claims a `global` statement this module does not contain: {message}")
    # and the fact that caused it, recorded where it will be re-measured rather than remembered
    import symtable as _st
    blocks = [c for c in _st.symtable(source, "<w>", "exec").get_children() if c.get_name() == "listcomp"]
    if blocks:                                    # 3.10/3.11 only; from 3.12 PEP 709 inlines it away
        sym = blocks[0].lookup("S")
        assert sym.is_declared_global(), (
            "symtable no longer synthesises declared-global for a comprehension walrus on this interpreter — "
            "the premise of this test has moved, and rule C's docstring says the two predicates agree")


def test_the_two_global_predicates_agree_over_the_whole_matrix():
    """A SURVIVING MUTANT, DECLARED. Rule C asks `is_global()`; the narrower `is_declared_global()` gives the
    same verdict on all 44 rows, on 3.10 and on 3.12, so the choice is NOT pinned by this matrix. The wider one
    is kept because wider is the fail-closed direction for an unenumerated case — a reason about risk, not
    about evidence — and this test exists so that a future interpreter which separates the two predicates
    reports it as a change rather than letting the docstring quietly go stale."""
    narrowed = _mutant("                if sym.is_global() and sym.is_assigned():",
                       "                if sym.is_declared_global() and sym.is_assigned():")
    disagreements = [row[0] for row in REBINDING_MATRIX
                     if (_refusal(narrowed, row[1]) is not None) != (_refusal(sr, row[1]) is not None)]
    assert not disagreements, (
        "the two predicates now disagree on these rows, which makes rule C's choice evidence-backed rather "
        f"than risk-backed — say so in its docstring: {disagreements}")
