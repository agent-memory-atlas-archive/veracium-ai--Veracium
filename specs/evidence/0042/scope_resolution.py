"""specs/0042 — ONE name resolver, shared by the two instruments that must agree about which NAME is which object.

Round 7, F2 and F4a, one root: both the binding SCAN (`installed_sites`) and the twin TRANSFORM
(`inv7_uninstrument`) asked "does this `NAME` refer to the module-level site?" and each answered it by walking the
AST and enumerating the forms that bind a name. That enumeration is a hand list standing in for a set the LANGUAGE
defines, and the reviewer found the two rungs it had not reached: an assignment expression (`S := …`) and a `match`
capture. Both read `bound=True` while the declared site's counters never moved. A third rung was in the transform:
a function PARAMETER shadowing a site name still had its own ordinary method call rewritten.

So the enumeration is gone. `symtable` is CPython's own scope analysis — the same pass the compiler runs — and it
answers the question by construction for every binding form the language has, including the ones nobody listed:

    module-level site, read in a function          GLOBAL  -> the site
    assignment · walrus · match capture            LOCAL   -> a shadow
    parameter · default-shadowed parameter         PARAM   -> a shadow
    for target (plain, tuple, star) · with-as
      · except-as · augmented assign · del
      · `import x as S` · `from x import y as S`   LOCAL   -> a shadow
    bound on ONE branch only                       LOCAL   -> a shadow (correctly: the binding is the block's)
    comprehension target                           its own block in py3, so the enclosing use is unaffected
    class-body attribute                           a class body is not a closure scope
    an ENCLOSING FUNCTION's binding, read inside    FREE    -> that binding, NOT the module's

A name this module cannot resolve is REFUSED (`UnresolvableScope`), never guessed at — the reviewer's own sanctioned
alternative to covering a form. `symtable` reads SOURCE, so an instrument must hand it the same text the runtime
executes; a generated or stubbed module is where that breaks, and the caller supplies the text it actually used.
"""
# Mutation-Matrix: tests/test_0042_scope_resolution.py::test_the_resolver_answers_every_binding_form
from __future__ import annotations

import ast
import dis
import symtable
import sys

# A block is joined to its AST node by (line, symtable's own name for that kind of block). The set of nodes that
# GET a block is an INTERPRETER FACT, not a constant: PEP 709 inlines list/set/dict comprehensions from 3.12, so on
# 3.12+ they have no block and their target lives in the enclosing block, while on 3.10/3.11 each has its own. CI
# runs 3.10 through 3.13, so the rule is DERIVED — a comprehension with no block is inlined (stay in the enclosing
# block); a def, class or lambda with no block is unjoinable and REFUSED.
_BLOCK_NAME = {ast.Lambda: "lambda", ast.ListComp: "listcomp", ast.SetComp: "setcomp",
               ast.DictComp: "dictcomp", ast.GeneratorExp: "genexpr"}
_INLINABLE = (ast.ListComp, ast.SetComp, ast.DictComp)      # no block from 3.12 (PEP 709)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
               ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

# The four opcodes by which a MODULE's own code object binds a name. This is the interpreter's reading of "what
# binds here", and it is TOTAL over syntax by construction: every module-level binding form the language has —
# including the ones no list contains — compiles to one of these four. The two `_GLOBAL` spellings appear at
# module level whenever some nested block also treats the name as a global, which is why they are counted as
# ordinary module-level bindings here and the nested write is a separate reading (rule C below).
_MODULE_BINDING_OPS = ("STORE_NAME", "DELETE_NAME", "STORE_GLOBAL", "DELETE_GLOBAL")

# The opcodes by which a NESTED code object binds a name belonging to THIS module's scope — rule C's reading,
# and a STRICT SUBSET of the four above. The subset is the whole point and it is the reason this constant
# exists at all rather than rule C reusing `_MODULE_BINDING_OPS` four lines up: a CLASS BODY assigning an
# ordinary attribute emits STORE_NAME in its own code object, so a nested walk over the wider tuple REFUSES
#
#     class K:
#         S = 1
#
# which is correct, ordinary code, for every class in the tree whose attribute collides with a site name.
# Measured on 3.10, 3.11, 3.12 and 3.13: nested hits over these two are 0 and over the four are 1. Found by
# research's differential harness BEFORE this rule was written, which is the only reason it is not shipped —
# the wider tuple was the nearer one to hand. The `_NAME` spellings can only ever be a nested scope's OWN
# binding; only the `_GLOBAL` pair reaches out to the module.
_NESTED_BINDING_OPS = ("STORE_GLOBAL", "DELETE_GLOBAL")

# A check that reads opcodes BY NAME weakens silently if a name ever moves: every count would fall to zero and
# every module would be accepted, which is the shape where deleting the subject reads as fixing the problem. So
# the names are confirmed against this interpreter's own table at import, loudly, before anything asks a
# question of them.
_MISSING_OPS = [op for op in (*_MODULE_BINDING_OPS, *_NESTED_BINDING_OPS) if op not in dis.opmap]
if _MISSING_OPS:                                                                        # pragma: no cover
    raise RuntimeError(f"specs/0042 scope_resolution: this interpreter ({sys.version.split()[0]}) has no "
                       f"{', '.join(_MISSING_OPS)} in dis.opmap, so counting module-level bindings by opcode "
                       f"name would silently return zero for every module and every nested scope, and accept "
                       f"every rebinding. The "
                       f"opcode set must be re-derived for this version before the census can be trusted.")

# ORDER MATTERS AND AN EXISTING TEST PROVED IT. This claim sits AFTER the opmap guard, not beside the tuple it
# is about: `test_the_opcode_names_are_confirmed_against_this_interpreters_table` renames an opcode in
# `_MODULE_BINDING_OPS` and expects the RuntimeError above. Asserted first, this raised AssertionError instead
# and shadowed the louder, more specific diagnosis — a guard whose remedy is wrong is obeyed, so the precise
# branch has to be reachable before the general one.
assert set(_NESTED_BINDING_OPS) < set(_MODULE_BINDING_OPS), (
    "rule C must read a STRICT subset of rule A's opcodes: the _NAME spellings can only be a nested scope's "
    "OWN binding, and reading them there refuses `class K: S = 1`")


def _instruction_line(instruction, carried: int) -> int:
    """The source line of one instruction, across the three spellings CPython has used (3.10 `starts_line` int;
    3.11+ `positions.lineno`; 3.13 `line_number`). An instruction that starts no new line carries the last one."""
    positions = getattr(instruction, "positions", None)
    if positions is not None and getattr(positions, "lineno", None):
        return positions.lineno
    for attribute in ("line_number", "starts_line"):
        value = getattr(instruction, attribute, None)
        if isinstance(value, int) and value:
            return value
    return carried


def _expected_name(node) -> str:
    return node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else _BLOCK_NAME[type(node)]


class UnresolvableScope(Exception):
    """A name or a block the resolver will not guess at: an unjoinable scope, or `global <site>` with an assignment."""


class Resolver:
    """Answers, for any AST node in one module's source: does `NAME` here refer to the MODULE-level binding?"""

    def __init__(self, src: str, filename: str = "<scan>"):
        self.src = src
        self.filename = filename
        self.tree = ast.parse(src)
        self.table = symtable.symtable(src, filename, "exec")
        self._code = None
        self._blocks: dict[tuple, list] = {}
        self._cursor: dict[tuple, int] = {}
        self._rebindings_checked: set[str] = set()
        self._index(self.table)
        self._owner: dict[int, symtable.SymbolTable] = {}
        self._comp_local: dict[int, frozenset] = {}
        self._assign(self.tree, self.table)

    def _index(self, block) -> None:
        """Blocks are keyed by (line, symtable's own name for the block); symtable reports the line of the
        `def`/`class`/expression identically to the AST (decorators excluded, verified). Several blocks CAN share a
        key — `asof/resolve.py:445` has two generator expressions on one line — so a key holds the LIST of them in
        symtable's order, and `_assign` consumes that list in the AST's order. Both orders are source order, and
        the control that would catch them diverging is two same-line genexprs binding DIFFERENT names, asserted in
        tests/test_0042_scope_resolution.py. symtable exposes no column, so order is the only join available; the
        alternative, refusing, would refuse real product source."""
        for child in block.get_children():
            self._blocks.setdefault((child.get_lineno(), child.get_name()), []).append(child)
            self._index(child)

    @staticmethod
    def _comprehension_targets(comp) -> frozenset:
        """The names a comprehension's own `for` targets bind. They are COMPREHENSION-LOCAL on every version —
        PEP 709 removed the BLOCK, not the SCOPING, which the interpreter itself demonstrates:
        `S = 1; [S for S in ("a","b")]` leaves `S == 1`."""
        names = set()
        for gen in comp.generators:
            for n in ast.walk(gen.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        return frozenset(names)

    def _assign(self, node, block, shadowed: frozenset = frozenset()) -> None:
        for child in ast.iter_child_nodes(node):
            self._assign_child(child, block, shadowed)

    def _assign_child(self, child, block, shadowed: frozenset) -> None:
        """One child, one place — the comprehension branch recurses THROUGH here rather than walking its own
        children, so a comprehension nested inside another still gets the scope-node treatment (it did not, first
        time: the inner listcomp of `[[S.fire(1) for S in row] for row in xs]` was walked past)."""
        self._comp_local[id(child)] = shadowed
        if isinstance(child, _COMPREHENSIONS):
            self._comprehension(child, block, shadowed)
            return
        if isinstance(child, SCOPE_NODES):
            key = (child.lineno, _expected_name(child))
            queue = self._blocks.get(key) or []
            cursor = self._cursor.get(key, 0)
            if cursor >= len(queue):
                raise UnresolvableScope(f"line {child.lineno}: no symbol-table block joins this "
                                        f"{type(child).__name__} — the resolver will not guess its scope")
            inner = queue[cursor]; self._cursor[key] = cursor + 1
            self._owner[id(child)] = inner
            self._assign(child, inner)                     # a real block resets any inlined shadowing
            return
        self._owner[id(child)] = block
        self._assign(child, block, shadowed)

    def _comprehension(self, child, block, shadowed: frozenset) -> None:
        """A comprehension, in BOTH regimes and with the language's own rule applied once for both.

        THE REGIMES: PEP 709 inlines list/set/dict comprehensions from 3.12, so on 3.12+ they carry no symtable
        block and their nodes are owned by the ENCLOSING block — where the comprehension's own targets must still
        shadow, because PEP 709 removed the block and NOT the scoping (the tests run `S = 1; [S for S in
        ("a","b")]` and assert S survives). On 3.10 and 3.11 the block exists and symtable answers. Generator
        expressions carry a block on every version. Round 8, research's stage-2 BLOCKING: without the inlined
        shadowing the answer DIFFERED between 3.10 and 3.12, and both consumers take it at face value.

        THE RULE THAT IS THE SAME IN BOTH: the FIRST iterable is evaluated in the ENCLOSING scope — CPython
        compiles it there and passes it in as `.0` — so a site read in it is the enclosing binding, whether or
        not the rest of the comprehension has a block of its own. Handling that only on the inlined path is what
        CI's 3.10 and 3.11 jobs caught, on the one case of the matrix that asserts it (the matrix was written for
        exactly this and found it on the versions this machine cannot run)."""
        key = (child.lineno, _expected_name(child))
        queue = self._blocks.get(key) or []
        cursor = self._cursor.get(key, 0)
        inner = None
        if cursor < len(queue):
            inner = queue[cursor]; self._cursor[key] = cursor + 1
        elif not isinstance(child, _INLINABLE):
            raise UnresolvableScope(f"line {child.lineno}: no symbol-table block joins this "
                                    f"{type(child).__name__} — the resolver will not guess its scope")
        self._owner[id(child)] = block
        body_block = inner if inner is not None else block
        body_shadow = frozenset() if inner is not None else shadowed | self._comprehension_targets(child)
        first_iter = child.generators[0].iter if child.generators else None
        if first_iter is not None:
            self._assign_child(first_iter, block, shadowed)         # the enclosing scope, both regimes
        for field in ("elt", "key", "value"):
            sub = getattr(child, field, None)
            if sub is not None:
                self._assign_child(sub, body_block, body_shadow)
        for i, gen in enumerate(child.generators):
            self._comp_local[id(gen)] = body_shadow
            self._owner[id(gen)] = body_block
            if i:
                self._assign_child(gen.iter, body_block, body_shadow)
            self._assign_child(gen.target, body_block, body_shadow)
            for cond in gen.ifs:
                self._assign_child(cond, body_block, body_shadow)

    def block_of(self, node) -> symtable.SymbolTable:
        b = self._owner.get(id(node))
        if b is None:
            raise UnresolvableScope(f"a node of type {type(node).__name__} was not indexed by this resolver")
        return b

    def site_names(self) -> set[str]:
        """The module-level `NAME = declare_site("<literal>")` targets."""
        out = set()
        for n in self.tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                    and isinstance(n.value, ast.Call):
                f = n.value.func
                if (f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)) == "declare_site":
                    out.add(n.targets[0].id)
        return out

    def refers_to_module_binding(self, node, name: str) -> bool:
        """THE NAME QUESTION: does `name`, used at `node`, resolve to the module-level BINDING? The module block
        IS that binding; inside any other block the answer is symtable's GLOBAL (never LOCAL, PARAMETER or FREE).

        THIS IS NOT THE SITE QUESTION, and the difference is not academic (round 8, research's stage-1 note on
        the stage-2 fix). Both consumers need to know whether the receiver IS THE DECLARED SITE OBJECT, and this
        answers whether it is the module NAME. The two coincide only while that name is bound exactly once at
        module scope — `S = declare_site('t'); [(S := q) for q in (1, 2)]` is the shape where they part, leaving
        the name bound and the site object gone, with this function still answering True and being right about
        the name. `refuse_site_rebindings` is what establishes the coincidence, and it lives in another function,
        so ASK `refers_to_declared_site` INSTEAD when the question is about the site: it refuses unless the
        guarantee has actually been established, rather than relying on the caller remembering the order."""
        if name in self._comp_local.get(id(node), frozenset()):
            return False            # bound by an INLINED comprehension's own target: comp-local, never the module's
        block = self.block_of(node)
        if block.get_type() == "module":
            return True
        try:
            sym = block.lookup(name)
        except KeyError:
            return False                       # the name is not used in this block at all
        return bool(sym.is_global()) and not sym.is_local() and not sym.is_parameter()

    def refers_to_declared_site(self, node, name: str) -> bool:
        """THE SITE QUESTION: is the receiver `name`, used at `node`, THE DECLARED SITE OBJECT? That is the
        question both consumers actually have, and it is answerable only where `refuse_site_rebindings` has
        established that the module name is bound once — so this REFUSES rather than answering without it. The
        guarantee used to live in the call ORDER, which is a thing a later caller or a refactor can drop with no
        test failing, because every existing test happens to run both."""
        if name not in self._rebindings_checked:
            raise UnresolvableScope(
                f"the site question was asked about {name!r} before `refuse_site_rebindings` established that its "
                f"module-level name is bound once — without that, a resolved NAME is not evidence about the OBJECT")
        return self.refers_to_module_binding(node, name)

    def _compiled(self):
        """This module's own code object, compiled once. BOTH readings go through here: rule A reads the module
        object's own instructions, rule C walks the nested objects hanging off it, and neither can be looking at
        a different compilation of the source than the other."""
        if self._code is None:
            try:
                self._code = compile(self.src, self.filename, "exec", dont_inherit=True)
            except SyntaxError as exc:      # `ast.parse` accepts text the compiler rejects (`return` at module
                raise UnresolvableScope(    # level, `await` outside `async`), so this is reachable past __init__
                    f"{self.filename}: the source parses but does not compile ({exc.msg} at line "
                    f"{exc.lineno}), so the interpreter has no reading of what this module binds") from exc
        return self._code

    def _nested_global_bindings(self, name: str) -> list[tuple[str, int]]:
        """Every NESTED code object that binds THIS module's `name`, as (code object name, line). Rule C's
        reading, and the same KIND of reading as rule A: what the interpreter will actually execute.

        IT REPLACED A HAND-PICKED PREDICATE PAIR, `sym.is_global() and sym.is_assigned()`, which round 8's
        reviewer defeated with a nested `import os as S` under `global S` — symtable reports that symbol
        `is_imported` and NOT `is_assigned`, so the pair never fired and the site was silently replaced. The
        fix is not a third predicate. `is_namespace` would have been the next rung of exactly the ladder
        CLAUDE.md item 9 exists to stop, and the module's whole argument is that a hand list standing in for
        what the language already knows is the defect. Rule A earned "total over syntax by construction" by
        asking the compiler; rule C sat beside it inheriting the sentence and never had the property.

        MEASURED EQUIVALENCE, on 3.10, 3.11, 3.12 and 3.13: against the deleted predicate pair over 24
        constructed nested forms, the two readings differ on exactly two — `import x as S` and
        `from x import y as S` under `global S`, which this one catches and the pair missed. They agree on the
        other 22, the read-only `global S` positive control included.

        WHY A STRICT SUBSET OF RULE A'S OPCODES (`_NESTED_BINDING_OPS`): see that constant. A class body's
        ordinary attribute assignment emits STORE_NAME in its own code object, so the wider tuple refuses
        `class K: S = 1`.

        NO COUNT IS REPORTED, and that is a decision rather than an omission. One source construct can emit
        several of these: `except Exception as S` under `global S` emits FIVE on all four versions (the store
        plus the implicit cleanup deletes) where symtable reported one. Rule A needs a count, because its
        question is "more than the one expected binding?". Rule C's question is "does any nested scope reach
        this name?", which one hit settles, so lines are DEDUPLICATED and no arithmetic reaches the message."""
        found = []

        def nested(code):
            for const in code.co_consts:
                if hasattr(const, "co_code"):
                    yield const
                    yield from nested(const)

        for obj in nested(self._compiled()):
            line = obj.co_firstlineno
            for instruction in dis.get_instructions(obj):
                line = _instruction_line(instruction, line)
                if instruction.opname in _NESTED_BINDING_OPS and instruction.argval == name:
                    found.append((obj.co_name, line))
        return found

    def _module_binding_ops(self, name: str) -> list[tuple[str, int]]:
        """Every binding operation the MODULE's OWN code object performs on `name`, as (opcode, line).

        THE INTERPRETER'S READING, and the only one this scope gets. A walk over AST node kinds knows only the
        forms somebody listed; this compiles the same source and counts what the module will actually execute,
        so a binding form nobody enumerated is counted like any other. It is the answer to round 8's stage-2 finding,
        where six spellings — `import os as S`, `from os import path as S`, `except Exception as S`, `del S`,
        `def S()`, `class S` — were all accepted because none of them is an `ast.Name` in a `Store` context.

        Nested code objects (a function, a class body, a comprehension that still gets one) live in `co_consts`
        and are NOT walked: a binding they perform is theirs, except when it targets this scope, which is rule C.
        Compiled with `dont_inherit=True` so the SCANNER's own `__future__` flags cannot change the reading."""
        found, line = [], 0
        for instruction in dis.get_instructions(self._compiled()):
            line = _instruction_line(instruction, line)
            if instruction.opname in _MODULE_BINDING_OPS and instruction.argval == name:
                found.append((instruction.opname, line))
        return found

    def refuse_site_rebindings(self, names: set[str]) -> None:
        """A declared site's NAME must denote the site everywhere the module reads it. Every way it stops doing so
        is REFUSED rather than resolved — the reviewer's sanctioned alternative to covering a form.

        TWO READINGS, BOTH THE LANGUAGE'S OWN, AND NEITHER OF THEM AN AST WALK. Round 8's first attempt had one
        reading, an AST walk over `ast.Name` in a `Store` context, and research's stage-2 mutants found six
        module-level binding spellings it could not see. A hand list standing in for what the language already
        knows is the defect this whole module exists to remove, and it had grown back one layer down.

        (The two are lettered A and C because a third, lettered D, was written in the same fix and DELETED —
        the paragraph after them says why. The surviving letters are NOT renumbered: the tests, the mutants,
        the CHANGELOG and the ledger all cite them by name, and renaming a rule to tidy a gap is how a citation
        starts pointing at the wrong thing. There is no B.)

          A. THE MODULE'S OWN CODE OBJECT BINDS THE NAME MORE THAN ONCE (`_module_binding_ops`). Total over syntax
             by construction. Catches the six spellings above and every ordinary rebinding — a second assignment,
             an augmented assignment, a `for` target, `with … as`, tuple and starred unpacking, a `match` capture,
             a module-level walrus. The declaration itself is the one binding that is expected.

        A THIRD READING WAS WRITTEN HERE AND DELETED, AND THE REASON BELONGS IN THE FILE. It compared the two
        readings and refused when they disagreed — research's "put an assertion between the two readings". Its
        own mutant showed it caught nothing A and C do not; then running two rows research proposed as
        must-accept showed what it DOES catch: `if False: S = 1`, where CPython folds the dead branch the walk
        can still see, and `S: int`, where a bare annotation's target carries a `Store` context and binds
        nothing. Both were REFUSED — correct code, a common idiom. A tripwire whose only reachable firings are
        false is worse than no tripwire, so it went, and the hand-written AST walk it existed to cross-check
        went with it. That walk was the enumeration this whole finding is about; the refusal now contains none.

        THE GENERAL FORM, because the instinct that produced it will produce another (research's formulation):
        a cross-check between two readings is right when they are two IMPLEMENTATIONS OF ONE RULE, where a
        difference is by definition a defect; it is harmful when they are two readings of DIFFERENT RULES, where
        a difference is an ordinary state of correct code. A asks what THIS scope binds and C asks what a NESTED
        block binds against it. Those are different questions, so "they disagree" was never evidence of
        anything — which is exactly why every firing it had was on a legitimate module.

        THE BRANCH DECISION, RECORDED RATHER THAN INHERITED. Counting binding operations cannot distinguish
        "bound twice in sequence" from "bound once in two mutually exclusive branches", and three real idioms
        count more than one: a `try`/`except ImportError` import fallback, a site declared in both arms of an
        `if`, and `if TYPE_CHECKING: import x as S`. All three are REFUSED. A static reading cannot tell a dead
        branch from a live one unless the condition is a literal the compiler folds, and a site declared ONCE
        and UNCONDITIONALLY is the premise of the scan this refusal protects. The refusal is loud, names its
        lines and reaches a person; accepting would risk the name question answering about the wrong object in
        silence, which is the failure being prevented. The `TYPE_CHECKING` row is the sharpest — at runtime that
        branch never executes, so the refusal is false in fact — and it is taken knowingly: it needs a site name
        to collide with a type-checking alias, and no module in the tree does that. `if False:` is ACCEPTED
        because the compiler folds it away, and the two rows sit together in the matrix so the asymmetry is
        recorded where a reader meets it.
          C. A NESTED CODE OBJECT BINDS THE NAME WITH `STORE_GLOBAL` OR `DELETE_GLOBAL`
             (`_nested_global_bindings`). The interpreter's reading again, so it is total over syntax for the
             same reason A is. Reaches the module binding from inside a function, a class body, two scopes
             down, and from a comprehension that still gets its own code object — a generator expression on
             EVERY version, and a list comprehension before 3.12, after which PEP 709 inlines it into the
             module and rule A counts it instead. Which rule owns that row therefore depends on the
             interpreter, while the refusal does not; `test_every_refused_row_names_the_rule_that_caught_it`
             pins the ownership so a row changing hands is a failure and not a silent re-attribution.
             IT REPLACED A HAND-PICKED PREDICATE PAIR IN ROUND 9. The pair was `is_global() and
             is_assigned()`, and the round-8 reviewer defeated it with a nested `import os as S` under
             `global S`: symtable reports that symbol `is_imported` and NOT `is_assigned`, so the pair never
             fired and the site was replaced in silence. The fix was NOT a third predicate — `is_namespace`
             is the next rung of exactly the ladder this module exists to get off, and a hand list standing
             in for what the language already knows is the defect the whole file is about. Rule A had earned
             "total over syntax by construction" by asking the compiler; rule C sat beside it inheriting the
             sentence and never had the property, which is the miss worth carrying.
             MEASURED AGAINST THE SUPERSEDED PAIR, on 3.10, 3.11, 3.12 AND 3.13: the two readings differ on
             the two nested imports and agree on every other row of the matrix. The pair is kept as the
             negative control its replacement must beat, in
             `test_the_superseded_predicate_pair_misses_exactly_the_nested_imports`, which asserts both
             directions — so "the new reading catches more" cannot hide "and also started refusing something
             else".
             THE OPCODE SET IS A STRICT SUBSET OF RULE A'S, and that is load-bearing rather than tidy: a
             class body's ordinary attribute assignment emits STORE_NAME in ITS OWN code object, so reading
             the wider tuple here refuses `class K: S = 1` — correct code, and every class in the tree whose
             attribute collides with a site name. Research's differential harness measured that on all four
             interpreters BEFORE this rule was written, which is the only reason it is not shipped.

        Verified against a 46-case matrix — 29 that must be refused, 17 that must be ACCEPTED — on 3.10 and
        3.11 (a block per comprehension) and 3.12 and 3.13 (inlined), in
        `tests/test_0042_scope_resolution.py`. Both rules are sole catchers of part of it, so deleting either
        reddens it. The 17 are as load-bearing as the 29: three drafts of this fix refused correct code, and
        that is what the acceptance half is for.

        (Named `refuse_rebound_globals` until round 8, when it stopped being only about `global`.)"""
        declared_here = self.site_names()
        for n in sorted(names):
            executed = self._module_binding_ops(n)
            executed_lines = sorted({line for _, line in executed})
            if not executed and n in declared_here:
                raise UnresolvableScope(
                    f"site {n!r} is declared at module level by this module and the interpreter's reading of "
                    f"the compiled module finds no binding for it at all — the reading is broken, not the "
                    f"module, and a broken reading accepts every rebinding in silence")
            if len(executed) > 1:
                whose = (" and exactly one of those is the declaration" if n in declared_here else "")
                raise UnresolvableScope(
                    f"site {n!r} is bound {len(executed)} times in the module's own code (lines "
                    f"{', '.join(map(str, executed_lines))}){whose} — a rebinding replaces the declared site "
                    f"object while every static reading still resolves the NAME to it")

        for n in sorted(names):
            nested = self._nested_global_bindings(n)
            if nested:
                where = sorted({obj for obj, _line in nested})
                lines = sorted({line for _obj, line in nested})
                raise UnresolvableScope(
                    f"nested scope(s) {', '.join(map(repr, where))} (line(s) "
                    f"{', '.join(map(str, lines))}) assigns the MODULE-level name {n!r} from inside a nested "
                    f"scope, which replaces the declared site object while every static reading still resolves "
                    f"the NAME to it. The refusal names no spelling and counts nothing: several spellings reach "
                    f"here (a `global {n}` statement with a write, an assignment expression, which PEP 572 binds "
                    f"in the ENCLOSING scope, and an import targeting the module name), and one construct can "
                    f"emit several operations")
        self._rebindings_checked |= set(names)      # only now is the NAME question evidence about the OBJECT
