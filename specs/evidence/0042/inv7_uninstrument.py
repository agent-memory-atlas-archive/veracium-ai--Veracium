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
`nonlocal`/`global` naming a declared site. Every statement that is not one of the listed forms is PRESERVED.

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


def _is_consult_item(item: ast.withitem) -> bool:
    c = item.context_expr
    return isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "consult" and not c.args


def _is_fire_call(node) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fire"


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

    # module-level: drop declare_site assignments and census imports
    def visit_Module(self, node):
        kept = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.value, ast.Call) \
                    and getattr(stmt.value.func, "id", getattr(stmt.value.func, "attr", "")) == "declare_site":
                self.sites += 1; continue
            if isinstance(stmt, ast.ImportFrom) and stmt.module and stmt.module.endswith("census"):
                self.imports += 1; continue                      # `from .census import declare_site`: instrumentation only
            if isinstance(stmt, ast.ImportFrom) and stmt.module in (None, "") and all(a.name == "census" for a in stmt.names):
                self.imports += 1; self.removed_imports.append(stmt); continue   # restored if the module still uses the surface
            if isinstance(stmt, ast.ImportFrom) and any(a.name == "census" for a in stmt.names):
                stmt.names = [a for a in stmt.names if a.name != "census"]; self.imports += 1
                if not stmt.names:
                    continue
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
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "consult" and not v.args:
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
        if isinstance(t, ast.Call) and isinstance(t.func, ast.Attribute) and t.func.attr == "enabled" \
                and isinstance(t.func.value, ast.Name) and self._is_census_alias(t.func.value.id, t.func.value):
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


def declared_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """(the module-level names bound by `NAME = declare_site(...)`, the aliases the census module is imported as)."""
    declared, aliases = set(), set()
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) \
                and isinstance(stmt.value, ast.Call) and getattr(stmt.value.func, "id", getattr(stmt.value.func, "attr", "")) == "declare_site":
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
        if isinstance(stmt, ast.ImportFrom) and stmt.level == 1 and stmt.module is None \
                and any(a.name == "census" for a in stmt.names):
            for a in stmt.names:
                if a.name == "census":
                    aliases.add(a.asname or "census")
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
    for a in sorted(census_aliases):
        n = resolver.module_binding_count(a)
        if n != 1:
            raise Refused(f"the census alias {a!r} is bound {n} times at module level, so the import does "
                          f"not establish what the name denotes where the bypass reads it — a census import "
                          f"followed by a reassignment binds twice, and the transform will not rewrite a "
                          f"condition whose subject it cannot establish")
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
        tree.body[0:0] = t.removed_imports; t.imports -= len(t.removed_imports)
    out = ast.unparse(tree) + "\n"
    exits_after = exits_per_function(ast.parse(out))
    if exits_after != exits_before:
        diff = {k: (exits_before.get(k), exits_after.get(k)) for k in set(exits_before) | set(exits_after) if exits_before.get(k) != exits_after.get(k)}
        raise Refused(f"the transform changed a function's exit count — the observer keys exits by ordinal: {diff}")
    stats = {"sites": t.sites, "fires": t.fires, "consults": t.consults, "consult_statements": t.consult_stmts,
             "bypasses": t.bypasses, "imports": t.imports, "exits": exits_after}
    # no INSTRUMENTATION may survive in the emitted module (a stub-answered surface read may)
    for token in ("declare_site", ".consult()", ".fire("):
        if token in out:
            raise Refused(f"the emitted module still carries {token!r}")
    return out, stats


STUB = ('"""INV-7 twin stub: the census module with NOTHING declared — the harness surface only."""\n'
        '_ENABLED = False\n\ndef enable(on=True):\n    global _ENABLED; _ENABLED = bool(on)\n\n'
        'def enabled():\n    return _ENABLED\n\ndef registry():\n    return ()\n\ndef counters():\n    return {}\n\n'
        'def trace(on=True):\n    pass\n\ndef trace_snapshot():\n    return []\n\ndef trace_reset():\n    pass\n\ndef reset_counters():\n    pass\n')


def derive(src: pathlib.Path, out: pathlib.Path) -> dict:
    """Copy src/veracium to out, un-instrumenting every module; census.py itself is replaced by a stub that
    exposes the harness surface the observer touches (enabled(), registry()) and declares nothing. Writes the
    MANIFEST beside the twin (out/../twin_manifest.json): source hashes before and after, every count, the
    permitted transformations by name."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
    totals = {"sites": 0, "fires": 0, "consults": 0, "consult_statements": 0, "bypasses": 0, "imports": 0, "modules_changed": 0}
    manifest = {"permitted_transformations": [
                    "NAME = declare_site(...) removed (module level)", "census imports removed (restored if the surface is still read)",
                    "with NAME.consult(): body -> body (NAME declared)", "NAME.consult() statement removed (NAME declared)",
                    "NAME.fire(X, ...) -> X (NAME declared; raise/return/assign)",
                    "if <census>.enabled(): [assign,] return NAME.fire(...) -> if False: [assign,] return X (kept dead; exit ordinals preserved)",
                    "if <census>.enabled(): [assign,] NAME2 = NAME.fire(NAME2) else: <assignments> -> if False: ... else: <assignments> (round 7: the four hot Edge predicates' one-return form; the else branch is product code, untouched)"],
                "refused_forms": ["fire()/consult() on an undeclared name", "fire() through an attribute chain", "fire() with no decision argument",
                                  "a with mixing consult and non-consult items", "an enabled block of any other shape",
                                  "a census-enabled bypass whose else branch is not simple assignments", "nonlocal/global naming a declared site",
                                  "a transform that changes a function's exit count", "an emitted module still carrying a census token"],
                "modules": {}}
    for p in sorted(out.rglob("*.py")):
        rel = str(p.relative_to(out)); before = p.read_bytes()
        if rel == "census.py":
            p.write_text(STUB); manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(STUB.encode()).hexdigest(), "stub": True}
            continue
        text = before.decode()
        if "census" not in text and ".fire(" not in text and "declare_site" not in text:
            manifest["modules"][rel] = {"sha256_before": hashlib.sha256(before).hexdigest(), "sha256_after": hashlib.sha256(before).hexdigest(), "unchanged": True}
            continue
        try:
            new, stats = uninstrument_source(text)
        except Refused as e:
            raise Refused(f"{rel}: {e}") from None
        p.write_text(new)
        for k, v in stats.items():
            if k != "exits":
                totals[k] += v
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
      2. TOKENS — no `declare_site`, `.consult()`, `.fire(` or census import survives an emitted module.
      3. STRUCTURE — the twin's AST equals the AST of RE-DERIVING the transform from the source, compared with
         `ast.dump` including every expression and its ORDER. This is data against data: the permitted changes are
         whatever the transform does, so nothing has to enumerate them a second time and drift from the first.
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
        if rel.name == "census.py":
            if text != STUB:
                problems.append(f"{rel}: the census module is not the twin STUB")
            continue
        for token in ("declare_site", ".consult()", ".fire(", "from .census import"):
            if token in text:
                problems.append(f"{rel}: {token!r} survives")
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
