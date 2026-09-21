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
        r.refuse_rebound_globals(r.site_names())
    clean = sr.Resolver("from .census import declare_site\nS = declare_site('s')\ndef f():\n    global S\n    return S.fire(1)\n")
    clean.refuse_rebound_globals(clean.site_names())          # a read-only global is not refused


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
            r = sr.Resolver(f.read_text(), str(f)); r.refuse_rebound_globals(r.site_names())
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
