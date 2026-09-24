#!/usr/bin/env python3
"""specs/0042 INV-7 — THE UNINSTRUMENTED TWIN, DERIVED FROM HEAD (not exported from an old commit).

The first four-arm transcripts exported the twin from the commit the instrumentation tranches began from
(`84f9515`). That twin was right for exactly as long as src/ changed only by instrumentation; the moment a
later spec touched src the "uninstrumented" arm was also an OLDER product. So the twin is DERIVED: HEAD's src
with the census MEASUREMENTS (every consult and every fire) removed by an AST transform that inverts the
instrumenter's forms and nothing else — and, since round 6 (R6-6), REFUSES everything it has not established is
instrumentation. Since round 14 the DECLARATIONS and census imports are PRESERVED verbatim, and census.py is
replaced by a STUB whose `declare_site` answers each declaration with an inert stand-in (a class named Site) that
records nothing and counts every use (see STUB):

    NAME = declare_site(...)                 ->  PRESERVED            NAME is then a DECLARED name of this module
    from .census import declare_site …      ->  PRESERVED            (declare_site under another name is REFUSED)
    from . import census as _census          ->  PRESERVED
    with NAME.consult(): <body>              ->  <body>               NAME declared; every item of the with a consult
    NAME.consult()                           ->  (removed)            the statement form (round 6, R6-2a)
    raise NAME.fire(EXC, ...)                ->  raise EXC            NAME declared; the value is the first argument
    return NAME.fire(EXPR, ...)              ->  return EXPR
    x = NAME.fire(EXPR, ...)                 ->  x = EXPR
    if _census.enabled(): <block>            ->  if False: <block'>   ONLY the recognised bypass shape at the four hot
                                                                      Edge predicates (a with-consult whose body is
                                                                      [assignment,] return NAME.fire(...)); the block
                                                                      is kept DEAD, not deleted, so the function's
                                                                      return/raise statements keep their number and
                                                                      order — the observer keys exits by ordinal

REFUSED (never guessed): `other.fire(...)` on a name that is not a declared site of the module; `a.b.fire(...)`
(an attribute chain the transform cannot bind); a consult on an undeclared name; a `with` mixing consult and
non-consult items; an enabled-block of any other shape (a side effect inside it would be product behaviour);
`nonlocal`/`global` naming a declared site; a census import binding a name the STUB does not define; and
`declare_site` imported under another name. (Rounds 12 and 13 also refused a declared site another module reaches
and the dynamic forms `globals()`, `vars()`, `exec`, `eval`, a `__dict__` or `sys.modules`; those refusals existed
only because the declaration was removed, and round 14, which keeps every declaration bound, withdrew them — each
such route now derives, verifies clean and runs as the source does.) Every statement that is not one of the listed
forms is PRESERVED.

`derive()` writes the twin AND a MANIFEST (`twin_manifest.json`): per module the source sha256 before and after,
the count of every transformation, and per function the number of return/raise statements before and after —
`verify()` asserts the exit counts equal, that no instrumentation survives, and that every non-instrumentation
statement of HEAD is still present in the twin (the transform removes and rewrites only the listed forms).

    python3 specs/evidence/0042/inv7_uninstrument.py <src/veracium> <out/src/veracium>
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import shutil
import symtable
import sys


def _sibling(name):
    """Load a sibling evidence module BY PATH (never `from x import y`: green where the directory happens to be on
    sys.path and red where it is not — the tests/ class)."""
    import importlib.util as _u
    s = _u.spec_from_file_location(f"_0042_{name}", pathlib.Path(__file__).resolve().parent / f"{name}.py")
    m = _u.module_from_spec(s); s.loader.exec_module(m); return m


_scope = _sibling("scope_resolution")


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins. Every JSON read in this layer
    goes through it — the round-8 suite caught the manifest read added for F4 arriving as a plain `json.loads`."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


class Refused(Exception):
    pass


def _receiver(call: ast.Call):
    """The receiver NAME of `NAME.method(...)`, or None for any other callee shape."""
    f = call.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return f.value.id
    return None


def _is_consult_call(c) -> bool:
    """`<NAME>.consult()` — the one reading of a consult CALL. ROUND 12 (research's R4a): the with-item form and the
    bare-statement form each spelled this test out, identically, in two places; now both ask this."""
    return isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "consult" and not c.args


def _is_consult_item(item: ast.withitem) -> bool:
    return _is_consult_call(item.context_expr)


def _is_fire_call(node) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fire"


def _is_enabled_call(node) -> bool:
    """`<Name>.enabled()` — the one reading of a census CONSULT. ROUND 12 (research's R4a): `visit_If` (which
    rewrites it) and the unresolved-bypass detector (which reports what was not rewritten) each spelled this test
    out, identically. Two readings of one question, identical today, are the shape every round of this arc found
    disagreeing one round later."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "enabled" \
        and isinstance(node.func.value, ast.Name)


def exits_per_function(tree: ast.AST) -> dict:
    """{qualname: number of return/raise statements in the function's OWN body (nested scopes excluded)}."""
    out = {}
    def walk(node, qual):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = ".".join(qual + [child.name]); n = 0
                def count(n_):
                    nonlocal n
                    for c in ast.iter_child_nodes(n_):
                        if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                            continue
                        if isinstance(c, (ast.Return, ast.Raise)):
                            n += 1
                        count(c)
                count(child); out[q] = n
                walk(child, qual + [child.name])
            elif isinstance(child, ast.ClassDef):
                walk(child, qual + [child.name])
            else:
                walk(child, qual)
    walk(tree, [])
    return out


class Uninstrument(ast.NodeTransformer):
    def __init__(self, declared: set[str], census_aliases: set[str], resolver=None):
        self.declared = declared; self.census_aliases = census_aliases
        # ROUND 7, F4a (F2's shared root): "is this NAME the declared site?" is a SCOPE question, and the transform
        # answered it by membership in `declared` alone. A function PARAMETER shadowing a module-level site name
        # therefore had its own ordinary method call rewritten, changing what the twin computes. The question now
        # goes to the same resolver the binding scan uses — CPython's own scope analysis.
        self.resolver = resolver
        self.sites = 0; self.fires = 0; self.consults = 0; self.consult_stmts = 0; self.bypasses = 0; self.imports = 0

    def _is_site(self, name, node) -> bool:
        """`name`, used at `node`, is the module-level declared site — not a local, a parameter, or an enclosing
        function's binding. With no resolver the transform REFUSES rather than falling back to membership, because
        the fallback IS the defect."""
        if name not in self.declared:
            return False
        if self.resolver is None:
            raise Refused(f"line {getattr(node, 'lineno', '?')}: no scope resolver was supplied, so {name!r} cannot "
                          f"be established as the declared site rather than a local of the same name")
        return self.resolver.refers_to_declared_site(node, name)

    def _is_census_alias(self, name, node) -> bool:
        """`name`, used at `node`, is the MODULE-level census import — not a parameter, a local, or an
        enclosing function's binding that happens to be spelled the same.

        ROUND 9, F3: THE TWIN OF `_is_site`, AND IT DID NOT EXIST. Round 7's F4a established that "is this NAME
        the declared site?" is a SCOPE question and routed it to the resolver — at the site call sites. The
        CENSUS-ALIAS question sat four methods away still answered by `name in self.census_aliases`, pure
        spelling, and that one REWRITES rather than refusing: an ordinary function taking a parameter named
        `_census` and branching on `_census.enabled()` had its branch turned into `if False:`, so the twin
        computed a different answer from the source (measured: original True, derived False) while `verify()`
        reported no problems. A fix applied at one of a question's two sites is the round's recurring shape.

        Fail direction matters here and it is why this one was the dangerous one: `visit_Global`/`visit_Nonlocal`
        also test membership, but they REFUSE on a hit, so a wrong answer over-refuses and is loud.

        WHAT THIS ESTABLISHES, IN THE MECHANISM'S OWN WORDS, AND WHAT IT DOES NOT. It establishes that the
        name resolves to a MODULE-LEVEL binding, that the binding is made by an import spelled
        `from . import census` (level 1, no module), and — via `module_binding_count` at the call in
        `uninstrument_source` — that the name is bound EXACTLY ONCE, so the import was not later replaced.
        IT DOES NOT ESTABLISH THAT THE BINDING DENOTES THIS PROJECT'S CENSUS MODULE, and no static reading
        can, which is the round-9 verdict's distinction between module scope and the identity of the object
        bound there. Research demonstrated the limit executably: two BYTE-IDENTICAL files,

            from . import census as _census
            def ordinary(): return _census.enabled()

        one under `real/sub/` and one under `fake/sub/`, bind different objects and return True and False.
        A static check cannot separate them BECAUSE THEY ARE THE SAME FILE — `.census` resolves against
        whichever package the module sits in. Three rounds of increasingly specific syntax (membership ->
        spelling -> scope) have a fourth rung that syntax cannot reach.

        SO IDENTITY IS CHECKED WHERE IT IS CHECKABLE: AT RUNTIME, in the behaviour regressions, which
        already execute both modules and can therefore assert that the object bound to the alias IS the
        census module the instrumentation uses. That assertion is
        `test_r9_the_alias_identity_is_established_at_runtime_because_it_cannot_be_established_statically`."""
        if name not in self.census_aliases:
            return False
        if self.resolver is None:
            raise Refused(f"line {getattr(node, 'lineno', '?')}: no scope resolver was supplied, so {name!r} "
                          f"cannot be established as the census module rather than a local of the same name")
        return self.resolver.refers_to_module_binding(node, name)

    # module-level: count the declarations (PRESERVED) and refuse the census imports the twin could not answer
    def visit_Module(self, node):
        # ROUND 14, the round-13 verdict's F1 — NOTHING IS REMOVED. Every declaration `NAME = declare_site(...)` and every
        # census import stays in the twin VERBATIM, and the twin's STUB census answers `declare_site` with an INERT
        # stand-in per declaration (see STUB). Rounds 11 to 13 removed the declaration and then chased, one spelling at
        # a time, every route by which another piece of code could still reach the name it bound — an import, a
        # star, `__all__`, an attribute, `getattr`, `import_module`, `sys.modules`, `__globals__`, `inspect`, `pkgutil`,
        # `runpy`… — and the round-13 verdict found five more. A name that is never unbound cannot be reached and
        # found missing, however the route is spelled. What stays refused here is what the transform must RECOGNISE:
        # a declaration made through an alias of `declare_site`, and a census name the STUB does not answer.
        # The declarations are COUNTED where they are recognised (`bound_declarations`, which `declared_names` also
        # reads), not here: round 14's docstring sweep found this loop counting by the callee's SPELLING while
        # recognition asks the BINDING (round 13's B3), and a membership test on `declared` here is round 7's F4a form.
        for stmt in node.body:
            if is_census_surface_import(stmt):
                for a in stmt.names:
                    if is_instrumentation_name(a.name) and a.asname and a.asname != a.name:
                        raise Refused(f"line {stmt.lineno}: `{a.name}` is imported under another name "
                                      f"({a.asname!r}); a site declaration is recognised by that name, so a "
                                      f"declaration made through this alias could not be recognised")
                    if a.name not in _stub_names():
                        raise Refused(f"line {stmt.lineno}: this census import binds `{a.name}`, which the twin's "
                                      f"STUB census does not define. The STUB exposes the harness surface, `declare_site` "
                                      f"and its stand-in class ({', '.join(sorted(_stub_names()))}); a real-census or type-only "
                                      f"name is THIS boundary, not a transform defect — the twin would fail at import")
        self.generic_visit(node)
        return node

    def visit_Global(self, node):
        if any(n in self.declared for n in node.names):
            raise Refused(f"line {node.lineno}: `global` names a declared site — not resolved by guess")
        return node

    def visit_Nonlocal(self, node):
        if any(n in self.declared for n in node.names):
            raise Refused(f"line {node.lineno}: `nonlocal` names a declared site — not resolved by guess")
        return node

    def visit_With(self, node):
        self.generic_visit(node)
        consults = [_is_consult_item(i) for i in node.items]
        if all(consults):
            for i in node.items:
                r = _receiver(i.context_expr)
                if not self._is_site(r, node):
                    raise Refused(f"line {node.lineno}: consult() on {r!r}, which is not this module's declared site "
                                  f"at this point (a local, a parameter, or an enclosing binding of the same name)")
            self.consults += 1
            return node.body                       # spliced into the parent's statement list
        if any(consults):
            raise Refused(f"line {node.lineno}: a consult() item beside a non-consult item — an unrecognised form")
        return node

    def visit_Expr(self, node):
        self.generic_visit(node)
        v = node.value
        if _is_consult_call(v):
            r = _receiver(v)
            if not self._is_site(r, node):
                raise Refused(f"line {node.lineno}: consult() statement on {r!r}, which is not this module's declared "
                              f"site at this point (a local, a parameter, or an enclosing binding of the same name)")
            self.consult_stmts += 1
            return None                            # the statement form: removed
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        t = node.test
        if _is_enabled_call(t) and self._is_census_alias(t.func.value.id, t.func.value):
            # the ONLY recognised shapes for the body (after the with was spliced by generic_visit above):
            # one or two statements, each a simple assignment to ONE Name, the last of them allowed to be a
            # `return <expr>` — the four hot Edge predicates, in their round-6 form (`q = …; return fire(q)`,
            # no else) and their round-7 form (`q = …; q = fire(q)` under an `else:` that computes the same
            # Name, ONE return after both: the exit statement is then the same in every arm, INV-7 R6-5).
            # The else branch is product code and is left exactly as written: with the test made False it
            # is the path every twin takes, which is the census-disabled path by construction.
            body = node.body

            def simple_assign(s):
                return isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name)
            ok = 1 <= len(body) <= 2 and all(simple_assign(s) for s in body[:-1]) and \
                 (simple_assign(body[-1]) or isinstance(body[-1], ast.Return))
            if not ok:
                raise Refused(f"line {node.lineno}: a census-enabled block whose body is not the recognised bypass shape "
                              f"([assignment,] assignment|return) — a side effect or another statement in it would be product behaviour")
            if node.orelse and not all(simple_assign(s) for s in node.orelse):
                raise Refused(f"line {node.lineno}: a census-enabled bypass whose else branch is not simple assignments — unrecognised")
            self.bypasses += 1
            node.test = ast.Constant(value=False)  # kept DEAD: a return statement in the body keeps its ordinal
            return node
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if _is_fire_call(node):
            r = _receiver(node)
            if r is None:
                raise Refused(f"line {node.lineno}: fire() reached through an attribute chain the transform cannot bind")
            if not self._is_site(r, node):
                raise Refused(f"line {node.lineno}: fire() on {r!r}, which is not this module's declared site at this "
                              f"point (a local, a parameter, or an enclosing binding of the same name)")
            if not node.args:
                raise Refused(f"line {node.lineno}: fire() with no decision argument")
            self.fires += 1
            return node.args[0]
        return node

    def generic_visit(self, node):
        # statement lists may receive lists from visit_With (splicing) — flatten them
        for field, old in ast.iter_fields(node):
            if isinstance(old, list):
                new = []
                for item in old:
                    if isinstance(item, ast.AST):
                        r = self.visit(item)
                        if r is None:
                            continue
                        if isinstance(r, list):
                            new.extend(r)
                        else:
                            new.append(r)
                    else:
                        new.append(item)
                old[:] = new
            elif isinstance(old, ast.AST):
                r = self.visit(old)
                if r is None:
                    delattr(node, field)
                else:
                    setattr(node, field, r)
        return node


# THE CENSUS PREDICATES — ONE DEFINITION EACH, AND EVERY CONSUMER ROUTES THROUGH THEM.
#
# ROUND 11, research's stage-1 enumeration: SIX units in this module decided "is this the census?" on THREE
# different readings, kept in step by hand, and every round found two of them disagreeing. Round 10's verdict
# was two instances at once — alias RECOGNITION narrowed while import REMOVAL was not, and rule A applied to
# the alias while rule C was not. Research then found a third and a fourth: a removal branch that checks
# `module` and never `level`, so `from .. import census` is UNRECOGNISED and REMOVED ANYWAY (the same
# NameError as the reviewer's finding 2, reached through the disagreement rather than through either answer);
# and a recogniser and a detector that both require `ast.If`, so a census consult in any other statement shape
# is invisible to BOTH.
#
# The remedy is not a fifth patch. It is that the predicates below are the only definitions, every consumer
# calls one of them, and `test_every_census_decision_routes_through_one_predicate` enumerates the consumers
# and fails the day one appears on a reading of its own. (This comment used to say "these TWO functions"
# and was wrong at five: a count describing a set that grows is a count that goes stale, so it names none.)
#
# ROUND 12 (research's stage-1 R4a): THE GATE'S BANNED SET IS DERIVED FROM THE STRING CONSTANTS INSIDE THESE
# PREDICATES, not written as the one literal "census". Round 11's gate banned that one word, so the same
# decision made with OTHER vocabulary was invisible to it — and research measured three such pairs, two of
# which had ALREADY drifted: the instrumentation tokens (a three-tuple here, a four-tuple in verify()) and
# the census FILE (top level here, any depth in verify()). Every recognition word now lives in exactly one
# predicate, so adding a word to a predicate bans it everywhere else without editing the gate.

def is_census_module_file(rel) -> bool:
    """The census module's OWN file, which the twin replaces with the stub.

    ROUND 11: a THIRD reading, found by the enumeration gate on its first run and NOT by the hand enumeration
    that preceded it — research's walk classified `derive` as "mention only, decides nothing", and it decides
    twice. Neither decision was wrong, which is exactly why a manual reading passed over them: the gate looks
    for units deciding on a reading of their own, not for units getting it wrong."""
    return str(rel) == "census.py"


def may_skip_uninstrumenting(text: str) -> bool:
    """A module that cannot be instrumented, skipped without parsing it.

    THE SAFETY ARGUMENT, STATED BECAUSE THE FALSE NEGATIVE IS THE DANGEROUS ONE: skipping a module that DOES
    use the census would leave instrumentation in the twin. Every route into the census carries one of these
    three tokens in the source text — the census import contains `census`, a declaration contains
    `declare_site`, a measured decision contains `.fire(`. A module containing none of them has no route in.
    This is a performance guard, not an identity decision, and it is named here so it cannot drift into one.

    ROUND 12: THE TOKENS ARE ASKED OF THEIR OWNER. This spelled out `.fire(` and `declare_site` itself, and its
    safety rested on "every route in carries one of THESE tokens" — so a fourth instrumentation token added to
    `instrumentation_tokens_in` would have been unknown here, a module carrying only it SKIPPED, and its
    instrumentation left live in the twin. Two predicates can both be definitions and still be a hand-kept pair;
    the derived gate cannot see that, because both are allowed to hold the word. Measured before the change: zero
    modules in src/veracium change their skip decision (the form adds `.consult()`, which no module carries alone)."""
    return "census" not in text and not instrumentation_tokens_in(text)


def _in_recognised_bypass(tree, call) -> bool:
    """Is this `<alias>.enabled()` call the TEST of an `if`, the one shape `visit_If` rewrites?

    Anything else — an assignment, a `while`, a ternary, a boolean operand — is a census consult the
    transform leaves in place, which the twin then carries live. The detector reports those rather than
    refusing them: preserving ordinary behaviour cannot over-refuse, and the manifest naming them is what
    makes the silence into a signal."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.test is call:
            return True
    return False


def census_names_in_import(stmt) -> list:
    """The `census` aliases a sibling `from . import ...` binds — [] if it is not one.

    ONE DERIVATION for both the whole-statement removal and the partial strip. Round 11's first form asked
    `any(...)` in the predicate and had no partial branch at all, so a multi-name import was all-or-nothing
    and the answer was ALL."""
    if not (isinstance(stmt, ast.ImportFrom) and stmt.level == 1 and stmt.module is None):
        return []
    return [a for a in stmt.names if a.name == "census"]


def is_census_surface_import(stmt) -> bool:
    """`from .census import declare_site, ...` — the instrumentation SURFACE, not the module object.

    `stmt.module` is checked EXACTLY, not by `endswith`: `from .not_really_census import x` is not this, and
    neither is `from totally_unrelated.census import x`. (Research's next-round item, taken now because it
    costs one comparison and this is the round that is supposed to stop hand-kept predicates.)

    BOTH SPELLINGS THE TREE ACTUALLY USES ARE ACCEPTED, and the first form of this predicate accepted only
    one. It required a RELATIVE import, and the suite caught it immediately: the tree carries
    `from .census import declare_site` (19) and `from ..census import declare_site` (9, in the store/ and
    asof/ subpackages), while the fixtures carry the ABSOLUTE `from veracium.census import declare_site`.
    Narrowing to the relative form left the emitted module still carrying `declare_site`, which the token
    check then refused. `endswith` was too wide; level>=1 alone was too narrow; the exact module name in
    either spelling is the property that is actually meant."""
    if not isinstance(stmt, ast.ImportFrom):
        return False
    if stmt.level >= 1:
        return stmt.module == "census"            # from .census / from ..census import <surface>
    return stmt.module == "veracium.census"        # from veracium.census import <surface>


def is_instrumentation_name(name: str) -> bool:
    """The one name on the census SURFACE that is instrumentation rather than a harness read.

    ROUND 12 (the verdict's F1): a surface import is decided per NAME. ROUND 14: nothing is stripped — `declare_site`
    is kept and answered by the STUB's inert stand-in, and it must be imported under its own name (an alias is
    refused, since a declaration is recognised by this name); every other name must be one the STUB answers, or the
    transform refuses.
    Research measured the boundary: 28 of the tree's 28 surface imports import `declare_site` alone, and the
    real census's public names missing from the STUB are exactly the ones a refusal should name."""
    return name == "declare_site"


def is_site_declaration(call) -> bool:
    """`declare_site(...)` or `<alias>.declare_site(...)` — a site DECLARATION, recognised by the callee's name.
    ROUND 12 (research's R4a): `visit_Module` and `declared_names` each spelled this test out; now both ask it."""
    f = call.func
    return is_instrumentation_name(getattr(f, "id", getattr(f, "attr", "")))


def instrumentation_tokens_in(text: str) -> list:
    """Every instrumentation TOKEN still present in `text`. ROUND 12 (research's R1): ONE definition for the
    transform's own emitted-module refusal AND for verify(), which kept a second tuple with a FOURTH token
    (`from .census import`). The two had drifted, and the fix for F1 would have made them contradict — a
    correct twin keeping `from .census import enabled` refused by verify() on its first run."""
    # ROUND 14: `declare_site` is no longer a token that must not survive — every declaration stays in the twin, bound
    # to the STUB's inert stand-in. What must not survive is a MEASUREMENT: a consult or a fire.
    return [tok for tok in (".consult()", ".fire(") if tok in text]


def _stub_names() -> frozenset:
    """The names the twin's STUB census defines — DERIVED from STUB, so the refusal boundary a surface import is
    held to cannot drift from the stub that will actually answer it."""
    tree = ast.parse(STUB)
    return frozenset(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))) | frozenset(
        tg.id for n in tree.body if isinstance(n, ast.Assign) for tg in n.targets if isinstance(tg, ast.Name))


def lost_bindings(src_text: str, twin_text: str) -> set:
    """Names the SOURCE binds at module level that the TWIN still reads and binds nowhere — a NameError waiting.

    THE CHECK OF A DIFFERENT KIND (the verdict's F1, its E half). verify() compares the twin against RE-DERIVING
    the transform, so a transform defect reproduces identically and reads clean; this does not re-derive anything.
    It is a DIFFERENTIAL over every module-level binding, not only imports (research's stage-1 R2: a declared site
    is ASSIGNMENT-bound, and an import-scoped check missed it). A differential rather than an absolute "unbound
    read" check, because both sides are read by one interpreter: CPython 3.12+ inlines comprehensions (PEP 709),
    so a comprehension variable appears as a module-level binding AND read there and on 3.10/3.11 does not — an
    absolute check would false-positive on half the regimes, while the difference cancels it on all four.

    NO BUILTIN EXCLUSION (round 12, research's stage-2 S2-2). This subtracted `dir(builtins)`, on the reasoning that
    a builtin name cannot be a lost binding. It is the ONE case that can be SILENT: a lost binding can only carry a
    builtin's name if the source SHADOWED that builtin, and losing the shadow raises no NameError — the name quietly
    resolves to the builtin. Measured: a site named `id`, read in a default, gave a twin passing the builtin `id`
    function where the source passed the site, with verify() CLEAN. The subtraction was never what kept ordinary
    builtin reads out; the differential is, because it only reports names the SOURCE bound.

    WHAT THIS DOES NOT READ, AND WHAT DOES (round 13 — round 12 listed these as limits, and the round-12 verdict
    returned a disclosed silent limit as blocking, so each now has an owner): a name bound DYNAMICALLY
    (`globals()[...]`, `exec`) is invisible to a static reading; this reads ONE module at a time, so a binding lost
    ACROSS modules is read by `lost_cross_module_references` in verify(). ROUND 14: the transform removes no binding
    — every declaration stays bound to its stand-in — so neither limit can be reached through a declared site, and
    the round-13 refusals of dynamic forms and of cross-module reach were withdrawn; this reading remains verify()'s
    check against a transform that DOES lose a binding (the mutant in tests/test_0042_inv7.py). A changed
    VALUE with no lost name — the round-12 verdict's F1 — is the scope resolver's pairing, which its join check now
    refuses rather than guesses; the pairing oracle over random programs is the class-level instrument."""

    def bound(text):
        top = symtable.symtable(text, "<twin-check>", "exec")
        return {s.get_name() for s in top.get_symbols() if s.is_assigned() or s.is_imported()}

    def reads(text):
        top = symtable.symtable(text, "<twin-check>", "exec")
        out = {s.get_name() for s in top.get_symbols() if s.is_referenced()}

        def walk(tab):
            for child in tab.get_children():
                out.update(s.get_name() for s in child.get_symbols() if s.is_global() and s.is_referenced())
                walk(child)
        walk(top)
        return out

    return (bound(src_text) - bound(twin_text)) & reads(twin_text)


def _module_file(root: pathlib.Path, dotted: str):
    """The file for `<package>.<a>.<b>` under `root` (the package directory), or None: a module or a package."""
    parts = dotted.split(".")[1:]
    base = root.joinpath(*parts) if parts else root
    for cand in (base.with_suffix(".py") if parts else None, base / "__init__.py"):
        if cand is not None and cand.is_file():
            return cand
    return None


def _dotted_of(root: pathlib.Path, path: pathlib.Path, pkg: str | None = None) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = [pkg or root.name, *rel.parts]
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _exported(path: pathlib.Path) -> set:
    """What `from <module> import *` binds: a literal `__all__` if the module has one, else its public names."""
    tree = ast.parse(path.read_text())
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets) and stmt.value is not None:
                try:
                    return set(ast.literal_eval(stmt.value))
                except ValueError:
                    return set()
    return {n for n in _module_bindings(path) if not n.startswith("_")}


def _module_bindings(path: pathlib.Path) -> set:
    """Module-level names a module binds, by the interpreter's own scope analysis."""
    top = symtable.symtable(path.read_text(), str(path), "exec")
    return {s.get_name() for s in top.get_symbols() if s.is_assigned() or s.is_imported()}


def cross_module_references(root: pathlib.Path, pkg: str | None = None) -> list:
    """Every reference, anywhere in the package at `root`, from one module to a NAME in another: `from X import N`
    (relative or absolute), `from X import *` (through X's `__all__` or public names), and an ATTRIBUTE read through
    a module object — bound by `from . import a`, `import pkg.a as m`, or `import pkg.a` and read as `pkg.a.N`.
    Returned as (importer, line, target module file, name, form). ROUND 13, the round-12 verdict's F2 and research's
    stage-1 R2: removing a declared site broke a sibling's import with verify() clean, and the attribute route
    (`from . import a` … `a.S`) broke at call time the same way.

    ALSO a literal `getattr(<package module>, "S")` and `import_module("<package module>")` — inline or bound to a name,
    recognised by its binding — which are the same static reference (round 13, research's pre-seal P1).

    ROUND 14 — WHAT THIS IS FOR NOW. Rounds 12 and 13 used these references to REFUSE a declared site that another
    module reached, because the twin removed the declaration; the round-13 verdict found five more routes (`pkgutil`,
    `runpy`, `importlib.util`, `__globals__`, `inspect`) and the list could not close. Round 14 keeps every declaration
    bound, so nothing here is refused. This remains as `verify()`'s cross-module DIFFERENTIAL — a reference the twin
    still makes that resolved in the source and does not in the twin — and it can still fire: a transform that
    deleted a declaration is the mutant that shows it (tests/test_0042_inv7.py)."""
    root = pathlib.Path(root); pkg = pkg or root.name       # a twin's directory may be named apart from its package
    files = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    refs = []
    for path in files:
        tree = ast.parse(path.read_text())
        here = _dotted_of(root, path, pkg)
        package = here if path.name == "__init__.py" else here.rsplit(".", 1)[0]
        modules = {}                                      # local name -> dotted module it is bound to
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")
                    base = base[:len(base) - (node.level - 1)] if node.level > 1 else base
                    target = ".".join(base + ([node.module] if node.module else []))
                else:
                    target = node.module or ""
                if target != pkg and not target.startswith(pkg + "."):
                    continue
                tfile = _module_file(root, target)
                for a in node.names:
                    if a.name == "*":
                        if tfile is not None:
                            refs += [(path, node.lineno, tfile, n, "star") for n in sorted(_exported(tfile))]
                    elif _module_file(root, f"{target}.{a.name}") is not None:
                        modules[a.asname or a.name] = f"{target}.{a.name}"          # a submodule, bound as a name
                    elif tfile is not None:
                        refs.append((path, node.lineno, tfile, a.name, "from-import"))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == pkg or a.name.startswith(pkg + "."):
                        if a.asname:
                            modules[a.asname] = a.name
                        else:
                            modules[pkg] = pkg                                     # `import pkg.a` binds `pkg`
        # BINDINGS, NOT SPELLINGS (research's input to P1, after B2): what `import_module` is called in THIS module is
        # read from its imports, so `from importlib import import_module as im` is seen.
        im_names, importlib_names = {"__import__"}, set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and not node.level and node.module == "importlib":
                for a in node.names:
                    if a.name == "import_module":
                        im_names.add(a.asname or a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "importlib":
                        importlib_names.add(a.asname or a.name)

        def is_import_module(call):
            f = call.func
            return (isinstance(f, ast.Name) and f.id in im_names) or \
                (isinstance(f, ast.Attribute) and f.attr == "import_module" and isinstance(f.value, ast.Name)
                 and f.value.id in importlib_names)

        def literal(node):
            return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

        def in_pkg(dotted):
            return dotted is not None and (dotted == pkg or dotted.startswith(pkg + "."))

        for node in ast.walk(tree):                   # `m = import_module("pkg.a")` binds a module like an import
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and is_import_module(node.value) \
                    and node.value.args and in_pkg(literal(node.value.args[0])):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        modules[t.id] = literal(node.value.args[0])

        def module_of(expr):
            """The package module an expression evaluates to, or None."""
            if isinstance(expr, ast.Name) and isinstance(expr.ctx, ast.Load):
                return modules.get(expr.id)
            if isinstance(expr, ast.Call) and is_import_module(expr) and expr.args \
                    and not (isinstance(expr.func, ast.Name) and expr.func.id == "__import__"):
                d = literal(expr.args[0])
                return d if in_pkg(d) else None
            if isinstance(expr, ast.Attribute) and isinstance(expr.ctx, ast.Load):
                base = module_of(expr.value)
                if base is not None and _module_file(root, f"{base}.{expr.attr}") is not None:
                    return f"{base}.{expr.attr}"
            return None

        def add(dotted, name, line, form):
            # NO SELF-EXEMPTION (round 13, research's pre-seal D1): a module referring to its OWN module object — `import
            # pkg.b as me`, `from . import b as me`, `import_module('pkg.b')` inside b — reaches its own site the same way
            # a sibling would. Exempting `tfile == path` made those silent. (Round 14: the twin removes no declaration, so
            # these references are verify()'s differential against a transform that does — the mutant that shows it.)
            tfile = _module_file(root, dotted)
            if tfile is not None:
                refs.append((path, line, tfile, name, form))

        parent = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent[id(child)] = node

        def is_plain_getattr(call):
            return isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "getattr" \
                and "getattr" not in modules and len(call.args) >= 2

        for node in ast.walk(tree):
            dotted = module_of(node) if isinstance(node, (ast.Name, ast.Call, ast.Attribute)) else None
            if dotted is not None:
                up = parent.get(id(node))
                # A package module read as `m.<static, non-dunder attribute>`, or through the plain builtin
                # `getattr(m, "<literal>")`, is a static reference. (Round 13 also listed every OTHER use as an escape
                # and every dynamic acquisition, for derive() to refuse; round 14 keeps every name bound, so those
                # refusals are gone and nothing consumes such rows.)
                if isinstance(up, ast.Attribute) and up.value is node and not up.attr.startswith("__"):
                    if module_of(up) is None:
                        add(dotted, up.attr, up.lineno, "attribute")
                elif is_plain_getattr(up) and up.args[0] is node and literal(up.args[1]) is not None:
                    add(dotted, literal(up.args[1]), up.lineno, "getattr")
    return refs


def _resolves(root: pathlib.Path, tfile: pathlib.Path, name: str) -> bool:
    return name in _module_bindings(tfile) or _module_file(root, f"{_dotted_of(root, tfile)}.{name}") is not None


def lost_cross_module_references(src: pathlib.Path, out: pathlib.Path) -> list:
    """The references the TWIN still makes that do not resolve in the twin and DID resolve in the source: an
    ImportError, an AttributeError at import (a star over a stale `__all__`), or an AttributeError at call time.
    verify()'s cross-module reading. It is a DIFFERENTIAL over the twin's own references — a reference only the SOURCE
    makes is not the twin's and is not reported (since round 14 the transform removes no reference to a binding: it
    removes consults and unwraps fires) — and it asks nothing about which names are sites, so it does not share the
    transform's site recognition."""
    lost = []
    for path, line, tfile, name, form in cross_module_references(out, pkg=src.name):
        if tfile is None or name is None:
            continue
        if _resolves(out, tfile, name):
            continue
        src_target = src / tfile.relative_to(out)
        if src_target.is_file() and _resolves(src, src_target, name):
            lost.append(f"{path.relative_to(out)}:{line}: {form} of {name!r} from {tfile.relative_to(out)} — bound "
                        f"there in the source and not in the twin: the twin fails where the source ran")
    return lost


def bound_declarations(tree: ast.Module) -> list:
    """Every module-level `NAME = declare_site(...)` statement that DECLARES A SITE — recognised by its census BINDING
    (below). The ONE recognition: `declared_names` takes its names from it and the transform its site COUNT, so the
    count cannot drift from what is recognised (round 14: it had counted by the callee's spelling)."""
    return [stmt for stmt in tree.body if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, ast.Call)
            and _is_bound_declaration(tree, stmt.value)]


def _is_bound_declaration(tree: ast.Module, call) -> bool:
    surface = {a.asname or a.name for st in tree.body if is_census_surface_import(st) for a in st.names
               if is_instrumentation_name(a.name)}
    census_bound = {a.asname or a.name for st in tree.body for a in census_names_in_import(st)}
    f = call.func
    if isinstance(f, ast.Name):
        return f.id in surface and is_site_declaration(call)
    return isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in census_bound \
        and is_site_declaration(call)


def declared_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """(the module-level names bound by `NAME = declare_site(...)`, the aliases the census module is imported as)."""
    declared, aliases = {stmt.targets[0].id for stmt in bound_declarations(tree)}, set()
    # ROUND 13 (research's stage-2 B3): a declaration is recognised by its BINDING, not its spelling. This accepted
    # ANY callee named `declare_site`, so `N = mock.MagicMock().declare_site('a')` — an object from outside the
    # package — was removed from the twin as a site, with verify() CLEAN: the source's `N.fire(4)` returned a
    # MagicMock, the twin's returned 4. Only `declare_site` bound by a census surface import, or `<census
    # alias>.declare_site`, declares a site. Any other spelling is ordinary code: ROUND 14 keeps it in the twin as
    # written (the token check no longer names `declare_site`), and a `fire()`/`consult()` on the name it binds is
    # refused, because that name is not a declared site. All 162 real declarations are one of the two.
    for stmt in tree.body:
        # ROUND 10, research's stage-1 B1. This tested `any(a.name == "census")` and NEVER LOOKED AT
        # `stmt.module` OR `stmt.level`, so six of seven spellings were collected — including
        # `from totally_unrelated import census`, `from conftest import census`, `from .vendor.fakes import
        # census` and `from .. import census`. A fix that said "the one binding must be the census import"
        # while asking THIS would have moved from spelling-of-the-alias to SPELLING-OF-THE-IMPORTED-NAME:
        # the same rung, one level up, which is the stop-one-rung-short this round was returned for.
        #
        # Only the SIBLING form is collected: `from . import census` — level 1, no module. That is the form
        # the tree uses (schema.py, where all four bypasses are; __init__.py's is function-local and
        # correctly not module-level). `from .. import census` is a DIFFERENT package's census and is no
        # longer collected. Measured before narrowing: zero modules in src/veracium use any other spelling,
        # so this over-refuses nothing that exists.
        for a in census_names_in_import(stmt):
            # ROUND 12: `a.name`, not the literal — identical for every alias `census_names_in_import` returns
            # (it returns only `a.name == "census"`), and a second copy of the word here is what the
            # derived gate now refuses.
            aliases.add(a.asname or a.name)
    return declared, aliases


def _statement_keys(tree: ast.AST) -> list:
    """Every non-instrumentation statement, as (qualname, kind, unparsed text) — the material the transform must PRESERVE."""
    keys = []
    def walk(node, qual):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                keys.append((".".join(qual), type(child).__name__, child.name)); walk(child, qual + [child.name]); continue
            if isinstance(child, ast.stmt):
                keys.append((".".join(qual), type(child).__name__, None))
            walk(child, qual)
    walk(tree, [])
    return keys


def uninstrument_source(text: str, filename: str = "<twin>") -> tuple[str, dict]:
    resolver = _scope.Resolver(text, filename)          # ROUND 7, F4a: the transform's scope question, resolved
    tree = resolver.tree
    declared, aliases = declared_names(tree)
    resolver.refuse_site_rebindings(declared)
    exits_before = exits_per_function(tree)
    # ROUND 12, research's stage-1 R2: A DECLARED SITE LOADED AS A VALUE. The transform removes `S = declare_site(...)`
    # and rewrites every `S.fire(x)` / `S.consult()`, so any OTHER load of `S` — an argument, a container element, an
    # attribute read — is left pointing at a name the twin no longer binds. Measured: `register(S)` raised NameError
    # at call time and `REGISTRY = [S]` at import, both with verify() CLEAN, because the name is ASSIGNMENT-bound and
    # an import-scoped check could not see it. It was refused here, where the resolver could still say which loads
    # were the site; `lost_bindings` in verify() was the second, independent reading of the same fact.
    # ROUND 14: round 12's R2 ("a declared site loaded outside fire()/consult()") and round 13's dynamic-namespace
    # refusal are GONE — both existed because the declaration was removed, and with the name kept bound to a faithful
    # stand-in, a site loaded as a value, or reached through `globals()`, is correct code (research's stage-1 read).
    census_aliases = aliases
    # AND THE BINDING MUST NOT HAVE MOVED. `from . import census as _census` followed by `_census = On()`
    # imports the census and then replaces it; the name still resolves to module scope, so the scope
    # question answers YES about a binding that no longer denotes the census. Rule A's reading answers the
    # one part of this a static check can: was the name bound more than once?
    # ROUND 10'S VERDICT, FINDING 1: THIS ASKED RULE A ONLY. The SITE question has always been answered by
    # TWO readings — the module's own code object (rule A) and the NESTED code objects (rule C) — and round 10
    # gave the census alias the first and not the second. `_nested_global_bindings` was in the same file, made
    # public in the same round, unused. So a nested `global _census; _census = On()`, a nested import, and a
    # generator-expression walrus all replaced the alias invisibly: ordinary() returned 101 in the source and
    # 1 in the twin, with verify() clean. Not a missing case — an existing mechanism applied to one half of
    # the question it was built for.
    for a in sorted(census_aliases):
        here = resolver.module_binding_count(a)                 # rule A: this scope's own bindings
        nested = resolver.nested_global_bindings(a)             # rule C: what nested scopes bind here
        if here != 1 or nested:
            where = f"{here} time(s) at module level" + (f" and from nested scope(s) {', '.join(sorted({n for n, _ in nested}))}" if nested else "")
            raise Refused(f"the census alias {a!r} is bound {where}, so the import does not establish what the "
                          f"name denotes where the bypass reads it. BOTH readings are asked, the module's own "
                          f"code object and the nested code objects, because a nested `global {a}` assignment, "
                          f"a nested import and a comprehension walrus all replace the binding without the "
                          f"module-level count moving")
    # ROUND 10, research's stage-2 F-S2-2: `bypasses: 0` HAD TWO MEANINGS AND THEY PRINTED IDENTICALLY —
    # a module with genuinely no census bypass, and a module WITH one whose alias could not be established,
    # whose twin therefore RETAINS a live `<name>.enabled()` call. In that region the twin is not an
    # uninstrumented reference at all, and its own manifest called it clean. That is the zero-versus-N/A
    # shape: "none present" and "present but not recognisable" are different facts and only the first is a
    # result. Four shapes reach it, all measured — a try/except import, an `if TYPE_CHECKING:` import, an
    # import under a runtime block, and no census import at all — because `declared_names` reads `tree.body`
    # and the bound-exactly-once refusal only fires on an ESTABLISHED alias, so the gap sits BEFORE both.
    #
    # The module is NOT refused: preserving ordinary behaviour cannot over-refuse, and refusing here would
    # reject an idiom no module in the tree uses. What changes is that the manifest stops reporting it clean.
    # Counted on the ORIGINAL tree, where the resolver can still answer about these nodes.
    # ROUND 11, research's stage-1 B2 — THEIR OWN ROUND-10 FINDING, FIXED AT ONE OF ITS TWO SITES, AND THE
    # SITE THEY DID NOT SPECIFY IS THE ONE I IMPLEMENTED. They asked for "does any surviving `<name>.enabled()`
    # call sit on a module-level name I could not establish" — SHAPE-AGNOSTIC. I wrote it on `ast.If` tests,
    # and the recogniser is on `ast.If` too, so a census consult in ANY other statement form was invisible to
    # BOTH. Measured with a perfectly ESTABLISHED alias: `on = _census.enabled()`, `while _census.enabled():`
    # and a ternary all gave bypasses=0, unresolved=0, and a twin that KEEPS the live call.
    #
    # So `bypasses: 0, unresolved: 0` had THREE meanings, not the two round 10 fixed: no bypass; a bypass on
    # an unestablished alias (reported); and a bypass in an unrecognised STATEMENT SHAPE (silent). This walks
    # every `<Name>.enabled()` call wherever it stands, and reports the ones the transform did not rewrite.
    unresolved = []
    for node in ast.walk(tree):
        if _is_enabled_call(node):
            nm = node.func.value.id
            if not resolver.refers_to_module_binding(node.func.value, nm):
                continue                                   # a local or a parameter of the same name: not ours
            if nm not in census_aliases:
                unresolved.append(f"{nm}.enabled() at line {node.lineno} (name not an established census alias)")
            elif not _in_recognised_bypass(tree, node):
                unresolved.append(f"{nm}.enabled() at line {node.lineno} (established alias, statement shape "
                                  f"the transform does not rewrite)")
    t = Uninstrument(declared, census_aliases, resolver)
    t.sites = len(bound_declarations(tree))              # counted where recognised (see `bound_declarations`)
    tree = t.visit(tree); ast.fix_missing_locations(tree)
    # a module that still USES the census surface after the instrumentation is gone (the opt-in switch,
    # `_census.enable(True)` in the package module) keeps its import: the twin's stub census answers it
    # ROUND 9, F3 (found by sweeping F3's class rather than fixing the cell the reviewer named): this read
    # `n.id in ("_census", "census")` — a hand-written literal sitting two lines below `census_aliases`, which
    # is DERIVED from this module's own imports. A module importing the census as anything else kept its
    # surface use and lost its import, so the twin died with `NameError`. Latent, not live: the tree's only
    # alias today is `_census`. Same shape as `_NESTED_BINDING_OPS` nearly reusing the wider tuple and as the
    # packaging README hand-listing filenames the stage derives — a literal next to the derivation that
    # should have produced it.
    out = ast.unparse(tree) + "\n"
    exits_after = exits_per_function(ast.parse(out))
    if exits_after != exits_before:
        diff = {k: (exits_before.get(k), exits_after.get(k)) for k in set(exits_before) | set(exits_after) if exits_before.get(k) != exits_after.get(k)}
        raise Refused(f"the transform changed a function's exit count — the observer keys exits by ordinal: {diff}")
    stats = {"sites": t.sites, "fires": t.fires, "consults": t.consults, "consult_statements": t.consult_stmts,
             "bypasses": t.bypasses, "imports": t.imports, "exits": exits_after,
             # the COUNT sums into the manifest totals; the DETAIL stays per module, under a key the
             # totals loop does not know, so a reviewer sees both the headline and which call it was.
             "unresolved_bypass_candidates": len(unresolved), "unresolved_bypass_detail": unresolved}
    # no INSTRUMENTATION may survive in the emitted module (a stub-answered surface read may)
    for token in instrumentation_tokens_in(out):         # ROUND 12, R1: ONE definition, shared with verify()
        raise Refused(f"the emitted module still carries {token!r}")
    return out, stats


# ROUND 14, research's stage 2 (K1, K2). The stand-in answers the WHOLE surface the real `Site` defines — its
# `__slots__` exactly, every method, inert and value-faithful to a census that is off (counters read the slots,
# `declined` is the real rule) — so a product read of any `Site` member derives, verifies and RUNS in the twin
# (K1: `S.failures` gave AttributeError with verify clean, once round 14 dropped the R2 refusal that had kept such
# reads out). And EVERY use counts (K2): `__getattribute__` counts each attribute access on an instance; every method
# body counts, so a call reached through the class (`type(S).counters(S)`) counts too; and each protocol Python
# dispatches on the TYPE, bypassing `__getattribute__` (hash, repr, ==, the four orderings, bool, with, sizeof,
# setattr, delattr), has a counting override. Protocols that REACH one of those count through it and have no override
# of their own, since an override whose count another already makes is a counter no test can redden: str() and
# format() reach __repr__ (object's), != reaches __eq__, and dir(), copy and pickle reach the instance through
# `__getattribute__` (`__dict__`, `__reduce_ex__`).
# `__class__` IS NOT COUNTED, and the class is NAMED `Site` so that is faithful (Quentin's decision, 2026-09-24): CI's
# pydantic-2.7.0 floor lane found that pydantic's model construction runs `isinstance(v, _PydanticWeakRef)` over every
# module global, and `isinstance` falls back to reading `v.__class__` — 126 "uses" at import, a correct twin gated as
# used. The class's name, qualname, module, repr and `type()` now read as the source's, and every `isinstance` a
# program can reach agrees (the only class it could compare against is the twin census's own `Site`). The residual,
# named: the class OBJECT's identity, and its members read through the class, which are the stand-in's.
# The surface is pinned against the real class and each use has a positive control
# (test_r14_k1_the_stand_in_answers_every_member_the_real_site_defines, test_r14_k2_every_use_of_a_stand_in_counts).
# NOT counted, and not countable by any hook a Python object can define: identity operations (`is`, `id()`,
# `type()`); any comparison CPython short-circuits on identity before calling `__eq__` — list/tuple `in`, `==`,
# `index` and `count` on an identity hit (research's stage 2; a set or dict reaches `__hash__` and counts); and
# operators neither `Site` nor the stand-in defines, which raise TypeError identically in both. Harmless in behaviour —
# identity is faithful per declaration, so no decision can diverge through it — and pinned as uncounted
# (test_r14_the_named_residual_is_uncounted_and_its_neighbours_count), so this list cannot go stale silently.
STUB = '''"""INV-7 twin stub: the census module with NOTHING MEASURED — the harness surface, and `declare_site`
answering each declaration with its own INERT stand-in (round 14): a class named Site, like the real one, that
answers every member the real Site defines, compares by identity like it, records nothing, and COUNTS every use —
any attribute access but `__class__`, every method call however reached, and every type-level protocol — so the
capture can assert the twin measured nothing: inert_calls() must read 0 and registry() stays empty."""
import threading as _threading

_ENABLED = False
_INERT_CALLS = 0


def _count():
    global _INERT_CALLS
    _INERT_CALLS += 1


_get = object.__getattribute__


class Site:
    __slots__ = ("site_id", "consulted", "fired", "errors", "_lock", "_declines", "failures")

    def __init__(self, site_id, declines=None):
        for k, v in (("site_id", site_id), ("consulted", 0), ("fired", 0), ("errors", 0),
                     ("_lock", _threading.Lock()), ("_declines", declines), ("failures", {})):
            object.__setattr__(self, k, v)

    def __getattribute__(self, name):
        if name != "__class__":
            _count()
        return _get(self, name)

    def __setattr__(self, name, value):
        _count()
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        _count()
        object.__delattr__(self, name)

    def declined(self, decision):
        _count()
        d = _get(self, "_declines")
        if d is None:
            return decision is None or decision is False or isinstance(decision, BaseException)
        if callable(d):
            return bool(d(decision))
        return decision is d

    def _bump(self, field):
        _count()

    def consult(self):
        _count()
        return self

    def _measurement_failed(self, exc):
        _count()

    def fire(self, decision, label=None, *, declined=None):
        _count()
        return decision

    def counters(self):
        _count()
        return {"consulted": _get(self, "consulted"), "fired": _get(self, "fired"), "errors": _get(self, "errors")}

    def failure_kinds(self):
        _count()
        return dict(_get(self, "failures"))

    def __enter__(self):
        _count()
        return self

    def __exit__(self, exc_type, exc, tb):
        _count()
        return False

    def __hash__(self):
        _count()
        return object.__hash__(self)

    def __eq__(self, other):
        _count()
        return object.__eq__(self, other)

    def __lt__(self, other):
        _count()
        return NotImplemented

    def __le__(self, other):
        _count()
        return NotImplemented

    def __gt__(self, other):
        _count()
        return NotImplemented

    def __ge__(self, other):
        _count()
        return NotImplemented

    def __repr__(self):
        _count()
        return object.__repr__(self)

    def __bool__(self):
        _count()
        return True

    def __sizeof__(self):
        _count()
        return object.__sizeof__(self)


def declare_site(site_id, declines=None):
    return Site(site_id, declines)


def inert_calls():
    return _INERT_CALLS


def enable(on=True):
    global _ENABLED; _ENABLED = bool(on)


def enabled():
    return _ENABLED


def registry():
    return ()


def counters():
    return {}


def trace(on=True):
    pass


def trace_snapshot():
    return []


def trace_reset():
    pass


def reset_counters():
    pass
'''


def derive(src: pathlib.Path, out: pathlib.Path) -> dict:
    """Copy src/veracium to out, un-instrumenting every module; census.py itself is replaced by the STUB, which
    exposes the harness surface the observer touches (enabled(), registry()) and answers each preserved declaration
    with an inert stand-in that registers nothing and counts every use (round 14). Writes the
    MANIFEST beside the twin (out/../twin_manifest.json): source hashes before and after, every count, the
    permitted transformations by name."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
    totals = {"sites": 0, "fires": 0, "consults": 0, "consult_statements": 0, "bypasses": 0, "unresolved_bypass_candidates": 0, "imports": 0, "modules_changed": 0}
    manifest = {"permitted_transformations": [
                    "NAME = declare_site(...) PRESERVED; the twin's STUB census answers it with an inert stand-in per declaration (round 14)",
                    "census imports PRESERVED (round 14)",
                    "with NAME.consult(): body -> body (NAME declared)", "NAME.consult() statement removed (NAME declared)",
                    "NAME.fire(X, ...) -> X (NAME declared; raise/return/assign)",
                    "if <census>.enabled(): [assign,] return NAME.fire(...) -> if False: [assign,] return X (kept dead; exit ordinals preserved)",
                    "if <census>.enabled(): [assign,] NAME2 = NAME.fire(NAME2) else: <assignments> -> if False: ... else: <assignments> (round 7: the four hot Edge predicates' one-return form; the else branch is product code, untouched)"],
                "refused_forms": ["fire()/consult() on an undeclared name", "fire() through an attribute chain", "fire() with no decision argument",
                                  "a with mixing consult and non-consult items", "an enabled block of any other shape",
                                  "a census-enabled bypass whose else branch is not simple assignments", "nonlocal/global naming a declared site",
                                  "a transform that changes a function's exit count", "an emitted module still carrying a measurement (a consult or a fire)",
                                  "a census surface import binding a name the twin's STUB does not define",
                                  "declare_site imported under another name"],
                "modules": {}}
    for p in sorted(out.rglob("*.py")):
        rel = str(p.relative_to(out)); before = p.read_bytes()
        if is_census_module_file(rel):
            p.write_text(STUB); manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(STUB.encode()).hexdigest(), "stub": True}
            continue
        text = before.decode()
        if may_skip_uninstrumenting(text):
            manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(before).hexdigest(), "unchanged": True}
            continue
        try:
            new, stats = uninstrument_source(text)
        except (Refused, _scope.UnresolvableScope) as e:
            # ROUND 13 (research's S2-6): an UnresolvableScope escaped here WITHOUT the module path, because only
            # Refused was wrapped — a refusal naming a line and not the file it is in. Each keeps its own type.
            raise type(e)(f"{rel}: {e}") from None
        p.write_text(new)
        # ROUND 10: summed BY PROPERTY, not by an exclusion list. This read `if k != "exits"`, so every
        # new stat had to be remembered in two places — and adding one that is not a number KeyErrors here,
        # which is how the unresolved-bypass detail first landed. A numeric stat now sums automatically and
        # a non-numeric one is carried per module without anyone maintaining a name list.
        for k, v in stats.items():
            if isinstance(v, int):
                totals[k] = totals.get(k, 0) + v
        totals["modules_changed"] += 1
        manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(new.encode()).hexdigest(), **stats}
    manifest["totals"] = totals
    (out.parent / "twin_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return totals


def verify(out: pathlib.Path, src: pathlib.Path | None = None, manifest: pathlib.Path | None = None) -> list[str]:
    """Does the twin at `out` differ from `src` BY THE INSTRUMENTATION AND NOTHING ELSE? Round 7, F4: the previous
    version answered only half the question and answered that half loosely. It checked that no instrumentation
    TOKEN survived, and — only when a source was passed, which the harness never did — compared a MULTISET of
    (qualname, node kind) for a few kinds. So it verified clean after `return False` became `return True` (same
    kind, same qualname), clean after a module was DELETED from the copy (it iterates the copy, so a missing file
    is simply not visited), and it never looked at the manifest it ships beside. Four readings now, and the source
    is REQUIRED — a verification that silently checks less when an argument is omitted is the round's other finding:

      1. FILE SET — the twin's modules equal the source's, both directions. A deletion or an addition is named.
      2. TOKENS — no instrumentation token (`instrumentation_tokens_in`, the ONE definition the transform's own
         refusal uses) survives an emitted module. ROUND 12: this clause used to add a fourth token, "census
         import", and it was TRUE only because every surface import was dropped whole; once a harness name the
         STUB answers is kept (the verdict's F1), a correct twin carries `from .census import enabled` — research's
         R1 measured verify() refusing exactly that. ROUND 14: `declare_site` is no longer a token — every declaration
         survives by design — and the tokens are the MEASUREMENTS, `.consult()` and `.fire(`.
      3. STRUCTURE — the twin's AST equals the AST of RE-DERIVING the transform from the source, compared with
         `ast.dump` including every expression and its ORDER. This is data against data: the permitted changes are
         whatever the transform does, so nothing has to enumerate them a second time and drift from the first.
      3b. ROUND 12 — TWO CHECKS OF A DIFFERENT KIND, because 3 re-derives with the SAME transform and so cannot see
         a defect IN it (round 9 learned this about F3 and answered one case; the round-11 verdict's F1 was the
         general form): every emitted module must COMPILE — `ast.parse` accepts a `from __future__` import that is
         no longer first, `compile()` does not — and `lost_bindings` finds any name the source binds at module
         level that the twin reads and binds nowhere. Neither re-derives anything, so neither inherits the defect.
      4. MANIFEST — every module's `sha256_before` matches the source file and `sha256_after` the emitted one, and
         the manifest's module set equals the file set. A manifest is looked for beside the twin unless one is given.
    """
    problems = []
    if src is None:
        return ["verify(out) was called WITHOUT a source: preservation cannot be established from the twin alone "
                "(round 7, F4 — the harness used to call it this way and got a token check silently standing in "
                "for a preservation check). Pass the source tree."]
    twin_files = {p.relative_to(out) for p in out.rglob("*.py")}
    src_files = {p.relative_to(src) for p in src.rglob("*.py") if "__pycache__" not in p.parts}
    for missing in sorted(src_files - twin_files):
        problems.append(f"{missing}: present in the source and MISSING from the twin")
    for extra in sorted(twin_files - src_files):
        problems.append(f"{extra}: present in the twin and absent from the source")
    for rel in sorted(twin_files & src_files):
        p_out = out / rel; text = p_out.read_text()
        if is_census_module_file(rel):                   # ROUND 12, R4: the transform's own reading, not a second one
            if text != STUB:
                problems.append(f"{rel}: the census module is not the twin STUB")
            continue
        for token in instrumentation_tokens_in(text):   # ROUND 12, R1: the transform's definition, not a drifted copy
            problems.append(f"{rel}: {token!r} survives")
        try:
            compile(text, str(rel), "exec", dont_inherit=True)
        except SyntaxError as e:
            problems.append(f"{rel}: the twin does not COMPILE ({e.msg}, line {e.lineno}) — `ast.parse` accepts text "
                            f"`compile()` refuses, such as a `from __future__` import that is no longer first")
            continue
        lost = lost_bindings((src / rel).read_text(), text)
        if lost:
            problems.append(f"{rel}: LOST BINDING(S) {sorted(lost)} — bound at module level in the source, still read "
                            f"by the twin, bound nowhere in it: the twin raises NameError where the source ran")
        try:
            redone, _ = uninstrument_source((src / rel).read_text(), str(src / rel))
        except Refused as e:
            problems.append(f"{rel}: re-deriving the transform from the source REFUSES ({e})")
            continue
        try:
            if ast.dump(ast.parse(text)) != ast.dump(ast.parse(redone)):
                problems.append(f"{rel}: the twin's program structure differs from re-deriving the transform from "
                                f"the source — the difference is NOT one of the permitted instrumentation changes")
        except SyntaxError as e:
            problems.append(f"{rel}: the twin does not parse ({e})")
    # ROUND 13, the round-12 verdict's F2 — a CROSS-MODULE reading. Every check above reads one module at a time, so a
    # sibling's `from .a import S` breaking with ImportError read clean. A differential over the twin's own references.
    problems += lost_cross_module_references(src, out)
    man_path = manifest if manifest is not None else out.parent / "twin_manifest.json"
    if not man_path.exists():
        problems.append(f"no twin manifest at {man_path} — the derivation's own record of what it rewrote is missing")
    else:
        man = json.loads(man_path.read_text(), object_pairs_hook=_strict_pairs)
        mods = man.get("modules") or {}
        if set(mods) != {str(r) for r in twin_files}:
            only_man = sorted(set(mods) - {str(r) for r in twin_files}); only_twin = sorted({str(r) for r in twin_files} - set(mods))
            problems.append(f"the manifest's module set differs from the twin's files (manifest only: {only_man[:4]}; twin only: {only_twin[:4]})")
        for rel, rec in sorted(mods.items()):
            p_out = out / rel; p_src = src / rel
            if p_out.exists() and hashlib.sha256(p_out.read_bytes()).hexdigest() != rec.get("sha256_after"):
                problems.append(f"{rel}: the emitted file's sha256 does not match the manifest's `sha256_after`")
            if p_src.exists() and hashlib.sha256(p_src.read_bytes()).hexdigest() != rec.get("sha256_before"):
                problems.append(f"{rel}: the SOURCE file's sha256 does not match the manifest's `sha256_before` — "
                                f"the manifest describes a different source than the one verified against")
    return problems


if __name__ == "__main__":
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    totals = derive(src, out)
    problems = verify(out, src)
    print("twin derived:", totals)
    print("verify:", "clean" if not problems else problems)
    sys.exit(0 if not problems else 1)
