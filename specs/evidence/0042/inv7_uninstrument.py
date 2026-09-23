#!/usr/bin/env python3
"""specs/0042 INV-7 — THE UNINSTRUMENTED TWIN, DERIVED FROM HEAD (not exported from an old commit).

The first four-arm transcripts exported the twin from the commit the instrumentation tranches began from
(`84f9515`). That twin was right for exactly as long as src/ changed only by instrumentation; the moment a
later spec touched src the "uninstrumented" arm was also an OLDER product. So the twin is DERIVED: HEAD's src
with the census instrumentation REMOVED by an AST transform that inverts the instrumenter's forms and nothing
else — and, since round 6 (R6-6), REFUSES everything it has not established is instrumentation:

    NAME = declare_site(...)                 ->  (removed)            NAME is then a DECLARED name of this module
    from .census import declare_site …      ->  (removed)
    from . import census as _census          ->  (removed; restored if the module still reads the stub's surface)
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
`nonlocal`/`global` naming a declared site; and since round 13, a declared site another module reaches (imported
by name, star-imported, listed in `__all__`, or read as a module attribute), and `globals()`, `vars()`, `exec`,
`eval`, a `__dict__` or `sys.modules` in a module that declares a site. Every statement that is not one of the
listed forms is PRESERVED.

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
        self.removed_imports: list = []

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

    # module-level: drop declare_site assignments, and the census BINDINGS that exist only for instrumentation
    def visit_Module(self, node):
        kept = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.value, ast.Call) \
                    and is_site_declaration(stmt.value):
                self.sites += 1; continue
            # ROUND 11: all branches ask the SAME predicates. The third used to strip a name spelled `census` out
            # of ANY import, and the second checked `module` and never `level` — two halves of one decision
            # answering differently about one statement.
            #
            # ROUND 12 (the round-11 verdict's F1): THE UNIT IS THE BINDING, NOT THE STATEMENT. A surface import was
            # dropped WHOLE, so `from .census import declare_site, enabled` took `enabled` with it while the module
            # still called it — NameError in the twin, verify() clean. Round 11 had fixed exactly this for the
            # partial MODULE import (research's B-S2-2) and left the surface branch dropping the lot: the named
            # cell fixed, the matrix never enumerated. Now each NAME is decided: an instrumentation name is
            # stripped, a harness name the STUB answers is KEPT, anything else is REFUSED at the boundary.
            if is_census_surface_import(stmt):
                live = []
                for a in stmt.names:
                    if is_instrumentation_name(a.name):
                        if a.asname and a.asname != a.name:
                            raise Refused(f"line {stmt.lineno}: `{a.name}` is imported under another name "
                                          f"({a.asname!r}); a site declaration is recognised by that name, so a "
                                          f"declaration made through this alias could not be recognised or removed")
                        continue
                    if a.name not in _stub_names():
                        raise Refused(f"line {stmt.lineno}: this census import binds `{a.name}`, which the twin's "
                                      f"STUB census does not define. The STUB exposes only the harness surface "
                                      f"({', '.join(sorted(_stub_names()))}); a real-census or type-only name is "
                                      f"THIS boundary, not a transform defect — the twin would fail at import")
                    live.append(a)
                if len(live) < len(stmt.names):
                    self.imports += 1
                if live:
                    stmt.names = live; kept.append(stmt)
                continue
            if is_census_module_import(stmt):
                self.imports += 1; self.removed_imports.append(stmt); continue   # restored if the module still uses the surface
            # PARTIAL: the statement binds the census AND other names. Strip the census names and KEEP the
            # statement, so its neighbours survive (round 11, research's stage-2 B-S2-2).
            # ROUND 12: the strip asks the PREDICATE'S OWN RESULT (`a not in partial`, an identity test on the same
            # alias nodes) rather than re-testing the name against a literal of its own — that literal was a second
            # reading of "which names are the census", waived by the round-11 gate because this unit also calls a
            # predicate (the verdict's F2, met at the same line as its F1). And the stripped alias is now RECORDED
            # for restoration exactly like a whole-statement import: it was dropped and never restorable, so a
            # module still using its census through a mixed import lost it (the verdict's F1, module cell).
            partial = census_names_in_import(stmt)
            if partial:
                stmt.names = [a for a in stmt.names if a not in partial]
                self.imports += 1
                self.removed_imports.append(ast.copy_location(ast.ImportFrom(module=None, names=partial, level=1), stmt))
            kept.append(stmt)
        node.body = kept
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


def is_census_module_import(stmt) -> bool:
    """`from . import census [as X]` — the census MODULE, bound under a name this module then uses.

    LEVEL AND MODULE BOTH CHECKED. `from .. import census` is a DIFFERENT package's census and is not this
    one; `from totally_unrelated import census` is not a census at all. Round 10 narrowed this in
    `declared_names` and left `visit_Module` on the broad test, which is how recognition and removal came to
    give opposite answers about one statement.

    ROUND 11 STAGE 2: TRUE ONLY WHEN **EVERY** NAME IS THE CENSUS, because the caller DELETES the whole
    statement. `from . import census as _census, helpers` used to satisfy this, so the statement went and
    `helpers` went with it while the twin still called `helpers.tweak` — a NameError, which is the round-10
    verdict's finding 2 through a route the reviewer did not name. A statement binding the census AND
    something else has its census names stripped and is KEPT; `census_names_in_import` is what both callers
    ask, so the whole-statement case and the partial case cannot drift apart."""
    names = census_names_in_import(stmt)
    return bool(names) and len(names) == len(stmt.names)


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

    ROUND 12 (the verdict's F1): a surface import is decided per NAME. `declare_site` is stripped, because the
    twin declares nothing; every other name must be one the twin's STUB answers, or the transform refuses.
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
    return [tok for tok in ("declare_site", ".consult()", ".fire(") if tok in text]


def _stub_names() -> frozenset:
    """The names the twin's STUB census defines — DERIVED from STUB, so the refusal boundary a surface import is
    held to cannot drift from the stub that will actually answer it."""
    tree = ast.parse(STUB)
    return frozenset(n.name for n in tree.body if isinstance(n, ast.FunctionDef)) | frozenset(
        tg.id for n in tree.body if isinstance(n, ast.Assign) for tg in n.targets if isinstance(tg, ast.Name))


def _restoration_index(body: list) -> int:
    """Where a restored census import may be placed: after the module docstring and after every
    `from __future__` import.

    ROUND 12, research's stage-1 R3 — MEASURED ONE LINE FROM LIVE: restoration inserted at `body[0]`, ahead of
    both. A docstring then stops being one (`__doc__` silently None), and a `from __future__` import no longer
    first is a SyntaxError that `ast.parse` ACCEPTS and `compile()` refuses — which is why verify() could not see
    it. schema.py, the tree's only module-level census import, has both; appending `_ON = _census.enabled()` to
    it made restoration fire and the twin fail to compile. D2 widens restoration to partial aliases, which is
    more routes into exactly this, so the placement had to move before D2 could land."""
    i = 1 if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
        and isinstance(body[0].value.value, str) else 0
    while i < len(body) and isinstance(body[i], ast.ImportFrom) and body[i].module == "__future__":
        i += 1
    return i


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
    (`globals()[...]`, `exec`) is invisible to a static reading, so the transform REFUSES those forms in any module
    that declares a site; this reads ONE module at a time, so a binding lost ACROSS modules is read by
    `lost_cross_module_references` in verify(), and the transform refuses a site another module reaches. A changed
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

    AND EVERY OTHER USE OF A MODULE OBJECT (round 13, research's pre-seal P1). This docstring's first form named "a
    reference spelled dynamically" as a limit, and it was SILENT: `getattr(a, 'S')` and `import_module('pkg.a').S`
    broke the twin with verify() clean. A fix keyed on those SPELLINGS was then shown six more bypasses (`vars(a)`,
    `a.__dict__`, `operator.attrgetter('S')(a)`, `sys.modules[...]`, and aliases of `getattr` and `import_module`),
    so the rule is keyed on USE, research's: once an expression resolves to a package module — a name bound by an
    import, `import_module("<package module>")` inline or bound to a name (recognised by its BINDING, so an alias is
    seen), or a submodule attribute of either — its only uses are `m.<static, non-dunder attribute>` and the plain
    builtin `getattr(m, "<literal>")`, each listed as a static reference. Any other use is listed as an ESCAPE (name
    None), which `derive()` refuses when the module's CLOSURE holds a site — itself, every module under it if it is a
    package, and transitively every package module it binds (research's refinement: a module declaring no site can
    carry one as an attribute). Dynamic ACQUISITION — `sys.modules`, a
    non-literal `import_module`, `__import__` of the package — is listed as "dynamic" and refused anywhere. Measured on
    the real tree: the same static references as before, 0 dynamic rows, and ONE escape (`store/sqlite.py` passes the
    `semantic` module object to a method), which is not refused because `semantic.py` declares no site."""
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
        # BINDINGS, NOT SPELLINGS (research's input to P1, after B2): what `import_module`, `sys` and `sys.modules` are
        # called in THIS module is read from its imports, so `from importlib import import_module as im` is seen.
        im_names, importlib_names, sys_names, sys_modules_names = {"__import__"}, set(), set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and not node.level and node.module in ("importlib", "sys"):
                for a in node.names:
                    if node.module == "importlib" and a.name == "import_module":
                        im_names.add(a.asname or a.name)
                    if node.module == "sys" and a.name == "modules":
                        sys_modules_names.add(a.asname or a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "importlib":
                        importlib_names.add(a.asname or a.name)
                    if a.name == "sys":
                        sys_names.add(a.asname or a.name)

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
            tfile = _module_file(root, dotted)
            if tfile is not None and tfile != path:
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
                # ROUND 13, P1 — KEYED ON USE (research's rule): a package module OBJECT may be used only as `m.<attr>`
                # with a static, non-dunder attribute, or as the first argument of the plain builtin
                # `getattr(m, "<literal>")`, which is the same static reference. Any other use — passed to a call,
                # subscripted, its `__dict__` taken, aliased — lets the module object ESCAPE, whatever function it
                # escapes into (`vars`, `operator.attrgetter`, an alias of `getattr`); derive() refuses that when the
                # module's closure holds a site (`_site_closure`).
                if isinstance(up, ast.Attribute) and up.value is node and not up.attr.startswith("__"):
                    if module_of(up) is None:
                        add(dotted, up.attr, up.lineno, "attribute")
                elif is_plain_getattr(up) and up.args[0] is node and literal(up.args[1]) is not None:
                    add(dotted, literal(up.args[1]), up.lineno, "getattr")
                elif isinstance(up, ast.Assign) and isinstance(node, ast.Call):
                    pass                                   # `m = import_module("pkg.a")`: the binding itself
                else:
                    tfile = _module_file(root, dotted)
                    if tfile is not None and tfile != path:
                        refs.append((path, getattr(node, "lineno", 0), tfile, None,
                                     "escape: a package module object used other than as a static attribute read"))
            # DYNAMIC ACQUISITION, anywhere in the package (research's (b)): no static reading can say which module
            if isinstance(node, ast.Attribute) and node.attr == "modules" and isinstance(node.value, ast.Name) \
                    and node.value.id in sys_names or isinstance(node, ast.Name) and node.id in sys_modules_names \
                    and isinstance(node.ctx, ast.Load):
                refs.append((path, node.lineno, None, None, "dynamic: sys.modules"))
            elif isinstance(node, ast.Call) and is_import_module(node) and node.args:
                d = literal(node.args[0])
                if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                    if d is None or in_pkg(d):
                        refs.append((path, node.lineno, None, None, "dynamic: __import__ of the package"))
                elif d is None:
                    refs.append((path, node.lineno, None, None, "dynamic: import_module with a non-literal argument"))
    return refs


def _resolves(root: pathlib.Path, tfile: pathlib.Path, name: str) -> bool:
    return name in _module_bindings(tfile) or _module_file(root, f"{_dotted_of(root, tfile)}.{name}") is not None


def lost_cross_module_references(src: pathlib.Path, out: pathlib.Path) -> list:
    """The references the TWIN still makes that do not resolve in the twin and DID resolve in the source: an
    ImportError, an AttributeError at import (a star over a stale `__all__`), or an AttributeError at call time.
    verify()'s cross-module reading. It is a DIFFERENTIAL over the twin's own references — a reference the transform
    removed (`_census.declare_site`) is not the twin's and is not reported — and it asks nothing about which names
    are sites, so it does not share the transform's site recognition."""
    lost = []
    for path, line, tfile, name, form in cross_module_references(out, pkg=src.name):
        if tfile is None or name is None:
            continue                                      # dynamic or escape: refused by derive(), not resolvable here
        if _resolves(out, tfile, name):
            continue
        src_target = src / tfile.relative_to(out)
        if src_target.is_file() and _resolves(src, src_target, name):
            lost.append(f"{path.relative_to(out)}:{line}: {form} of {name!r} from {tfile.relative_to(out)} — bound "
                        f"there in the source and not in the twin: the twin fails where the source ran")
    return lost


def declared_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """(the module-level names bound by `NAME = declare_site(...)`, the aliases the census module is imported as)."""
    declared, aliases = set(), set()
    # ROUND 13 (research's stage-2 B3): a declaration is recognised by its BINDING, not its spelling. This accepted
    # ANY callee named `declare_site`, so `N = mock.MagicMock().declare_site('a')` — an object from outside the
    # package — was removed from the twin as a site, with verify() CLEAN: the source's `N.fire(4)` returned a
    # MagicMock, the twin's returned 4. Only `declare_site` bound by a census surface import, or `<census
    # alias>.declare_site`, declares a site; any other spelling keeps its token in the twin, which the token check
    # refuses. All 162 real declarations are one of the two.
    surface = {a.asname or a.name for st in tree.body if is_census_surface_import(st) for a in st.names
               if is_instrumentation_name(a.name)}
    census_bound = {a.asname or a.name for st in tree.body for a in census_names_in_import(st)}

    def is_bound_declaration(call) -> bool:
        f = call.func
        if isinstance(f, ast.Name):
            return f.id in surface and is_site_declaration(call)
        return isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in census_bound \
            and is_site_declaration(call)
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) \
                and isinstance(stmt.value, ast.Call) and is_bound_declaration(stmt.value):
            declared.add(stmt.targets[0].id)
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
    # an import-scoped check could not see it. Refused here, where the resolver can still say which loads are the
    # site; `lost_bindings` in verify() is the second, independent reading of the same fact.
    receivers = {id(n.func.value) for n in ast.walk(tree)
                 if (_is_fire_call(n) or _is_consult_call(n)) and isinstance(n.func.value, ast.Name)}
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in declared and id(n) not in receivers \
                and resolver.refers_to_declared_site(n, n.id):
            raise Refused(f"line {n.lineno}: the declared site {n.id!r} is loaded outside fire()/consult() — as a value, "
                          f"an argument or a container element — and the twin removes its declaration, so it would be "
                          f"unbound there")
    # ROUND 13 — THE MODULE NAMESPACE REACHED DYNAMICALLY, in a module that declares a site. Round 12 DISCLOSED this as
    # a limit (`globals()["S"]`: the twin raised KeyError with verify() clean) and the round-12 verdict returned the
    # disclosed silent limits as blocking. No static reading can say which name such a form reaches, so a site module
    # holding one is REFUSED. Keyed on the forms that reach THE MODULE's namespace — research's census at round 13
    # found 0 of them in the 28 site-declaring modules, and 27 `getattr` calls, all on ordinary objects: a refusal
    # keyed on getattr would have refused 8 real modules. NAMED LIMIT: `getattr(<this module>, "S")` via an imported
    # self-reference is not recognised; 0 in the tree.
    # ROUND 13, research's stage-2 B2 — KEYED ON BINDING, NOT SPELLING. The first form refused a CALL spelled
    # `globals()` and an attribute spelled `sys.modules`, and let three aliases through silently: `_g = globals;
    # _g()['S']`, `import sys as _s; _s.modules[...]`, `from sys import modules`. Now ANY load of the four builtins
    # (a call or not — `vars(obj)` included, measured to touch no real site module), `.modules` on any name an
    # import bound to `sys`, and `from sys import modules` itself.
    if declared:
        sys_names = {a.asname or a.name for st in ast.walk(tree) if isinstance(st, ast.Import)
                     for a in st.names if a.name == "sys"}
        for n in ast.walk(tree):
            form = None
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in ("globals", "vars", "exec", "eval"):
                form = f"{n.id}()"
            elif isinstance(n, ast.Attribute) and n.attr == "__dict__":
                form = "a `__dict__`"
            elif isinstance(n, ast.Attribute) and n.attr == "modules" and isinstance(n.value, ast.Name) \
                    and n.value.id in sys_names:
                form = "`sys.modules`"
            elif isinstance(n, ast.ImportFrom) and n.module == "sys" and not n.level \
                    and any(a.name == "modules" for a in n.names):
                form = "`sys.modules`"
            if form:
                raise Refused(f"line {n.lineno}: {form} in a module that declares a site — the module's namespace is "
                              f"reached dynamically, so no static reading can say whether a declared site is read "
                              f"through it (round 13: round 12 disclosed `globals()['S']` as a silent limit)")
    # ROUND 10: THE GUESSED-ALIAS FALLBACK IS GONE. `aliases or {"_census", "census"}` treated those two
    # spellings as the census in a module that imports no census at all, so an ordinary object bound to
    # `_census` had its condition rewritten and the twin computed a different answer. Removing it PRESERVES
    # ordinary behaviour in that module (the verdict's "preserve ordinary behavior OR explicitly refuse" —
    # preserving is the half that cannot over-refuse). Measured before removal: the twin derives
    # BYTE-IDENTICALLY, 162/302/152/4, digest a0f42316…, because every bypass is in schema.py, which
    # derives its alias properly.
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
    t = Uninstrument(declared, census_aliases, resolver); tree = t.visit(tree); ast.fix_missing_locations(tree)
    # a module that still USES the census surface after the instrumentation is gone (the opt-in switch,
    # `_census.enable(True)` in the package module) keeps its import: the twin's stub census answers it
    # ROUND 9, F3 (found by sweeping F3's class rather than fixing the cell the reviewer named): this read
    # `n.id in ("_census", "census")` — a hand-written literal sitting two lines below `census_aliases`, which
    # is DERIVED from this module's own imports. A module importing the census as anything else kept its
    # surface use and lost its import, so the twin died with `NameError`. Latent, not live: the tree's only
    # alias today is `_census`. Same shape as `_NESTED_BINDING_OPS` nearly reusing the wider tuple and as the
    # packaging README hand-listing filenames the stage derives — a literal next to the derivation that
    # should have produced it.
    still_used = any(isinstance(n, ast.Name) and n.id in census_aliases for n in ast.walk(tree))
    if still_used and t.removed_imports:
        k = _restoration_index(tree.body)                  # ROUND 12, R3: after the docstring and `from __future__`
        tree.body[k:k] = t.removed_imports; t.imports -= len(t.removed_imports)
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


STUB = ('"""INV-7 twin stub: the census module with NOTHING declared — the harness surface only."""\n'
        '_ENABLED = False\n\ndef enable(on=True):\n    global _ENABLED; _ENABLED = bool(on)\n\n'
        'def enabled():\n    return _ENABLED\n\ndef registry():\n    return ()\n\ndef counters():\n    return {}\n\n'
        'def trace(on=True):\n    pass\n\ndef trace_snapshot():\n    return []\n\ndef trace_reset():\n    pass\n\ndef reset_counters():\n    pass\n')


def _module_level_module_bindings(root: pathlib.Path, path: pathlib.Path) -> list:
    """The package modules a module binds AT MODULE LEVEL (its attributes that are module objects): `from . import x`,
    `from .p import x` where x is a submodule, `import pkg.x as y`, `import pkg.x` (which binds the package), and
    `m = import_module("pkg.x")`."""
    pkg = root.name
    here = _dotted_of(root, path)
    package = here if path.name == "__init__.py" else here.rsplit(".", 1)[0]
    out = []
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[:len(base) - (node.level - 1)] if node.level > 1 else base
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            for a in node.names:
                f = _module_file(root, f"{target}.{a.name}")
                if f is not None:
                    out.append(f)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name == pkg or a.name.startswith(pkg + "."):
                    f = _module_file(root, a.name if a.asname else pkg)
                    if f is not None:
                        out.append(f)
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and node.value.args \
                and isinstance(node.value.args[0], ast.Constant) and isinstance(node.value.args[0].value, str) \
                and node.value.args[0].value.startswith(pkg):
            f = _module_file(root, node.value.args[0].value)
            if f is not None:
                out.append(f)
    return out


def _site_closure(root: pathlib.Path, tfile: pathlib.Path, sites) -> pathlib.Path | None:
    """A site-declaring module reachable THROUGH the module object `tfile` — the module itself; for a package, every
    module under it (a package object carries its imported submodules as attributes); and, transitively, every package
    module it binds at module level. Research's pre-seal refinement of P1: "refuse the escape when the target declares
    a site" looked only at the escaped module, and `c` (no site) carrying `a` (a site) as `c.a` escaped silently."""
    seen, stack = set(), [tfile]
    while stack:
        f = stack.pop()
        if f in seen:
            continue
        seen.add(f)
        if sites(f):
            return f
        if f.name == "__init__.py":
            stack.extend(p for p in f.parent.rglob("*.py") if "__pycache__" not in p.parts)
        stack.extend(_module_level_module_bindings(root, f))
    return None


def _refuse_cross_module_sites(src: pathlib.Path) -> None:
    """ROUND 13, the round-12 verdict's F2: a declared site is removed from its module, so ANY other module that
    reaches it — imported by name, star-imported, or read as a module attribute (research's stage-1 R2) — would break
    in the twin. Refused, with both ends named. And a site listed in its own module's literal `__all__` is refused
    whether or not anything star-imports it today: the export is a promise the twin cannot keep."""
    declared = {}
    def sites(f):
        if f not in declared:
            declared[f] = declared_names(ast.parse(f.read_text()))[0]
        return declared[f]
    for path, line, tfile, name, form in cross_module_references(src):
        if form.startswith("escape"):
            carried = _site_closure(src, tfile, sites)
            if carried:
                raise Refused(f"{path.relative_to(src)}: line {line}: {form}, and {tfile.relative_to(src)} carries the "
                              f"site-declaring module {carried.relative_to(src)} — once the module object escapes, no static "
                              f"reading can say which of its names is read (round 13, research's pre-seal P1)")
            continue
        if form.startswith("dynamic"):
            raise Refused(f"{path.relative_to(src)}: line {line}: {form} — no static reading can say whether it reaches a "
                          f"declared site the twin removes (round 13, research's pre-seal P1)")
        if name in sites(tfile):
            raise Refused(f"{path.relative_to(src)}: line {line}: {form} of the declared site {name!r} from "
                          f"{tfile.relative_to(src)} — the twin removes the site, so this module would fail where the "
                          f"source runs (round 13, the round-12 verdict's F2)")
    for f in sorted(p for p in src.rglob("*.py") if "__pycache__" not in p.parts):
        tree = ast.parse(f.read_text())
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in stmt.targets):
                try:
                    listed = set(ast.literal_eval(stmt.value))
                except ValueError:
                    listed = set()
                if listed & sites(f):
                    raise Refused(f"{f.relative_to(src)}: line {stmt.lineno}: `__all__` exports the declared site(s) "
                                  f"{sorted(listed & sites(f))} — the twin removes them, so a star import fails")


def derive(src: pathlib.Path, out: pathlib.Path) -> dict:
    """Copy src/veracium to out, un-instrumenting every module; census.py itself is replaced by a stub that
    exposes the harness surface the observer touches (enabled(), registry()) and declares nothing. Writes the
    MANIFEST beside the twin (out/../twin_manifest.json): source hashes before and after, every count, the
    permitted transformations by name."""
    _refuse_cross_module_sites(pathlib.Path(src))
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
    totals = {"sites": 0, "fires": 0, "consults": 0, "consult_statements": 0, "bypasses": 0, "unresolved_bypass_candidates": 0, "imports": 0, "modules_changed": 0}
    manifest = {"permitted_transformations": [
                    "NAME = declare_site(...) removed (module level)",
                    "census bindings removed PER NAME: declare_site stripped from a surface import (the statement kept if a harness name the STUB answers remains); a census module import or alias removed, and RESTORED after the docstring and any from __future__ import if the module still reads it",
                    "with NAME.consult(): body -> body (NAME declared)", "NAME.consult() statement removed (NAME declared)",
                    "NAME.fire(X, ...) -> X (NAME declared; raise/return/assign)",
                    "if <census>.enabled(): [assign,] return NAME.fire(...) -> if False: [assign,] return X (kept dead; exit ordinals preserved)",
                    "if <census>.enabled(): [assign,] NAME2 = NAME.fire(NAME2) else: <assignments> -> if False: ... else: <assignments> (round 7: the four hot Edge predicates' one-return form; the else branch is product code, untouched)"],
                "refused_forms": ["fire()/consult() on an undeclared name", "fire() through an attribute chain", "fire() with no decision argument",
                                  "a with mixing consult and non-consult items", "an enabled block of any other shape",
                                  "a census-enabled bypass whose else branch is not simple assignments", "nonlocal/global naming a declared site",
                                  "a transform that changes a function's exit count", "an emitted module still carrying a census token",
                                  "a census surface import binding a name the twin's STUB does not define",
                                  "declare_site imported under another name",
                                  "a declared site referenced from another module (imported by name, star-imported, or read as a module attribute)",
                                  "a declared site listed in its module's literal __all__",
                                  "a package module whose closure holds a site-declaring module, used other than as a static attribute read (passed, subscripted, its __dict__ taken, an aliased or non-literal getattr)",
                                  "a module acquired dynamically (sys.modules, import_module with a non-literal argument, __import__ of the package)",
                                  "globals(), vars(), exec, eval, a __dict__ or sys.modules in a module that declares a site",
                                  "a declared site loaded outside fire()/consult() (as a value, an argument or a container element, including at a definition-time position: a default, decorator, annotation, or class base or keyword)"],
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
         R1 measured verify() refusing exactly that. A surviving `declare_site` is still refused, by token.
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
