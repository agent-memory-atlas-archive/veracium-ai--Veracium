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
# Fields of a def/class statement evaluated in the ENCLOSING scope when the statement runs (round 12, S2-1).
# Defaults and annotations live one level down, inside `ast.arguments`, and are split there.
_DEFINITION_TIME_FIELDS = frozenset({"decorator_list", "bases", "keywords", "returns"})
SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
               ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

def _enclosing_parts(node) -> list:
    """(role, part) for every part of a def, lambda or class statement Python evaluates in the ENCLOSING scope, before
    the statement's own block exists — the ONE definition of that set: the resolver assigns exactly these first and
    skips exactly these, by identity, inside. (A comprehension's single header part, its first iterable, is handled in
    `_comprehension`; it has one role, so it needs ordering and never a refusal.) ROLES, not fields: the interpreter groups a header by role, and two scopes in one role are created
    in sequence. Annotations are split by parameter kind because research measured their order — `**kwargs`'
    annotation comes BEFORE kw-only annotations, the opposite of `iter_fields` (round 12, S2b-1)."""
    parts = []
    for field, role in (("decorator_list", "decorator"), ("bases", "base"), ("keywords", "keyword")):
        parts += [(role, x) for x in (getattr(node, field, None) or [])]
    if getattr(node, "returns", None) is not None:
        parts.append(("return annotation", node.returns))
    a = getattr(node, "args", None)
    if isinstance(a, ast.arguments):
        parts += [("default", d) for d in a.defaults]
        parts += [("kw-only default", d) for d in a.kw_defaults if d is not None]
        # ROUND 13 (research's S2c-3): the MEASURED order — `**kwargs` BEFORE kw-only. This list had kw-only first while
        # the docstring cited the measurement; harmless while two header roles on one line are refused, and wrong for
        # whoever relaxes that refusal.
        for role, args in (("posonly annotation", a.posonlyargs), ("annotation", a.args),
                           ("*args annotation", [a.vararg] if a.vararg else []),
                           ("**kwargs annotation", [a.kwarg] if a.kwarg else []),
                           ("kw-only annotation", a.kwonlyargs)):
            parts += [(role, x.annotation) for x in args if x.annotation is not None]
    return parts


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
# MY OWN MUTANT CAMPAIGN FOUND THIS ASSERTION CLAIMING MORE THAN IT CHECKED. It read `set(_NESTED_BINDING_OPS)
# < set(_MODULE_BINDING_OPS)` under a comment saying it stops rule C reading a tuple that refuses
# `class K: S = 1` — and the B1-dangerous value PASSES it: ("STORE_GLOBAL", "DELETE_GLOBAL", "STORE_NAME") is
# still a strict subset of rule A's four, because DELETE_NAME is absent. The label read true and the property
# was the wrong one. So the property that actually matters is asserted directly: NO `_NAME` SPELLING, because
# a `_NAME` opcode in a nested code object is that scope's OWN binding and never a write to this module's.
# The subset relation is kept beside it — it is true, and it says rule C may not invent an opcode rule A does
# not know — but it is no longer the thing standing in for the real claim.
_NESTED_NAME_OPS = [op for op in _NESTED_BINDING_OPS if op.endswith("_NAME")]
assert not _NESTED_NAME_OPS, (
    f"rule C must not read {_NESTED_NAME_OPS}: a `_NAME` opcode in a NESTED code object is that scope's own "
    f"binding, not a write to this module's, so reading it there refuses `class K: S = 1` — correct code, and "
    f"every class in the tree whose attribute collides with a site name")
assert set(_NESTED_BINDING_OPS) < set(_MODULE_BINDING_OPS), (
    "rule C must read a STRICT subset of rule A's opcodes: it may not invent a binding opcode the module-level "
    "reading does not know about")


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
        self._joined: dict[tuple, list] = {}          # key -> [(node, block)] in the order the queue was drained
        self._assign(self.tree, self.table)
        self._check_join()

    # ROUND 13 — THE JOIN IS CHECKED, not only ordered (the round-12 verdict's F1, and the class it belongs to). Every
    # silent defect in rounds 12 and 13 was one shape: two same-line, same-kind scopes whose symbol-table blocks this
    # resolver handed out in the wrong order, each fixed by ORDERING one more construct. An order is a claim about
    # the interpreter that a new construct can falsify silently; this check makes a mis-pairing REFUSE instead.
    # THE RULE IS RESEARCH'S (stage-1 read of round 13, P2'), and it is one rule for both seats:
    #   a same-key group of 2+ blocks is SAFE if every block's FULL FINGERPRINT is identical — a swap cannot change any
    #     answer, since `refers_to_module_binding` reads only the block's type and the looked-up symbol's flags;
    #   otherwise EACH NODE must be corroborated by its SIGNATURE: exactly one block in the group fits it, and it is
    #     the block the order gave it. Two fitting blocks is the case the order alone decided — REFUSED.
    # A signature is a lambda's or def's PARAMETERS, and a comprehension's own generator TARGETS (its only parameter is
    # `.0`). Research's first version keyed comprehensions on parameters and would have refused asof/resolve.py:445.
    # Parameter equality ALONE was dev's first proposal and is blind to exactly the case that matters: two
    # parameter-less lambdas, one binding `_census` by walrus, swapped — research's R1, silent end to end.
    @staticmethod
    def _fingerprint(block) -> tuple:
        return (block.get_type(), tuple(sorted((s.get_name(), s.is_parameter(), s.is_local(), s.is_global(),
                                                 s.is_free()) for s in block.get_symbols())))

    @staticmethod
    def _fits(node, block) -> bool:
        if isinstance(node, _COMPREHENSIONS):
            if block.get_type() != "function":
                return False
            locals_ = {s.get_name() for s in block.get_symbols() if s.is_local() and not s.is_parameter()}
            return Resolver._comprehension_signature(node) == locals_
        if isinstance(node, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            params = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs] + [x.arg for x in (a.vararg, a.kwarg) if x]
            return block.get_type() == "function" and sorted(block.get_parameters()) == sorted(params)
        return True                                                       # a class is joined by its NAME already

    @staticmethod
    def _comprehension_signature(node) -> frozenset:
        """The names a comprehension's own BLOCK holds as non-parameter locals, derived from the AST: its own targets
        and, on 3.12+, the targets of every INLINABLE comprehension nested in its body — PEP 709 merges an inlined
        comprehension's variables into the block that contains it (measured: `(x for x in a if [y for y in b])` holds
        x and y on 3.12/3.13, x alone on 3.11). The walk does not enter the node's own first iterable (evaluated in the
        enclosing scope) or any scope that keeps a block of its own. EQUALITY, not a subset, because research's rule
        corroborates a pairing by the signature: `(n for n …)` and `(tg for n … for tg …)` on one line — live at
        inv7_uninstrument.py:499 — are told apart only by `tg`, and a subset test fitted the first to both."""
        names = set(Resolver._comprehension_targets(node))
        if sys.version_info >= (3, 12):
            first = node.generators[0].iter if node.generators else None
            stack = [c for c in ast.iter_child_nodes(node) if c is not first]
            while stack:
                n = stack.pop()
                if isinstance(n, _INLINABLE):
                    names |= Resolver._comprehension_targets(n)
                elif isinstance(n, SCOPE_NODES):
                    continue                                   # a lambda, def, class or genexp keeps its own block
                stack.extend(ast.iter_child_nodes(n))
        return frozenset(names)

    def _check_join(self) -> None:
        for key, pairs in self._joined.items():
            group = self._blocks.get(key) or []
            if len(group) < 2 or len({self._fingerprint(b) for b in group}) == 1:
                continue
            for node, given in pairs:
                fitting = [b for b in group if self._fits(node, b)]
                if len(fitting) != 1 or fitting[0] is not given:
                    raise UnresolvableScope(
                        f"line {node.lineno}: {len(group)} same-line {key[1]} scopes whose symbol tables differ, and "
                        f"this {type(node).__name__} is fitted by {len(fitting)} of them"
                        f"{'' if len(fitting) != 1 else ' — not the one the join order gave it'}: the pairing would "
                        f"rest on an order alone, so it is refused rather than guessed (round 13, the join check)")

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
            self._refuse_role_collisions(child)          # ROUND 12, S2b-1: two or more HEADER roles on one key
            # ROUND 12, S2b-1 — ORDER. The parts evaluated in the ENCLOSING scope are assigned FIRST: the interpreter
            # creates their nested blocks BEFORE this statement's own block exists, and this resolver used to take
            # its own block from the queue first — so a lambda in a lambda's default, or a return annotation beside
            # a same-line body lambda, was handed the other one's table. Single-role, documented order: not guessed.
            outer = [part for _, part in _enclosing_parts(child)]
            for part in outer:
                self._assign_child(part, block, shadowed)
            key = (child.lineno, _expected_name(child))
            queue = self._blocks.get(key) or []
            cursor = self._cursor.get(key, 0)
            if cursor >= len(queue):
                raise UnresolvableScope(f"line {child.lineno}: no symbol-table block joins this "
                                        f"{type(child).__name__} — the resolver will not guess its scope")
            inner = queue[cursor]; self._cursor[key] = cursor + 1
            self._owner[id(child)] = inner
            self._joined.setdefault(key, []).append((child, inner))
            self._assign_definition(child, inner, {id(p) for p in outer})
            return
        self._owner[id(child)] = block
        self._assign(child, block, shadowed)

    def _refuse_role_collisions(self, node) -> None:
        """REFUSE, rather than guess, when same-line nested scopes of one kind sit in TWO OR MORE HEADER ROLES of one
        statement. Round 12, research's stage-2b S2b-1 — and it was SILENT.

        One key, `(line, kind)`, names every lambda (or comprehension of a kind) on a line, and this resolver drains
        that key's queue of symbol-table blocks in its own visiting order. The interpreter fills it in a different one:
        it evaluates a statement's header in the ENCLOSING scope and groups it by ROLE — research MEASURED the order:
        positional defaults, kw-only defaults, annotations (posonly, args, *args, **kwargs, kw-only), return. A walk by
        field disagrees, and with one scope binding `_census` as its own parameter and another reading the module's
        alias, the read resolved to the parameter: a live census call in the twin, nothing reported.

        TWO DIFFERENT PROBLEMS, TWO DIFFERENT REMEDIES, on Quentin's word:
          * the order AMONG header roles is subtle — research had to measure `**kwargs` before kw-only to get it
            right — and a wrong guess is silent again. So two or more header roles on one key are REFUSED (remedy
            (b)); research measured this refuses nothing in the tree.
          * the order of the header against the statement's OWN block and its BODY is not subtle: the header runs in
            the enclosing scope before the block exists, the body inside it after. That is FIXED BY ORDERING in
            `_assign_child` and `_comprehension`, never refused — refusing it would have refused real product code
            (asof/resolve.py:445, a genexp in a genexp's first iterable, live and swapped), and the language defines
            the order.
        One header role holding several scopes is not refused either: its scopes are walked and created in sequence."""
        roles: dict = {}
        for role, part in _enclosing_parts(node):
            for n in ast.walk(part):
                if isinstance(n, SCOPE_NODES):
                    roles.setdefault((n.lineno, _expected_name(n)), set()).add(role)
        for (line, kind), rs in sorted(roles.items()):
            if len(rs) >= 2:
                raise UnresolvableScope(
                    f"line {line}: {kind!r} scopes on this line sit in different roles of one statement's header "
                    f"({', '.join(sorted(rs))}). The interpreter orders a header by ROLE and this resolver walks it by "
                    f"FIELD, so which table belongs to which scope is not established — refused rather than guessed "
                    f"(round 12, S2b-1)")

    def _assign_definition(self, node, inner, enclosing_ids: set) -> None:
        """A `def`, `lambda` or `class` statement: its BODY and its parameter BINDINGS belong to the inner block, and
        everything evaluated WHEN THE STATEMENT RUNS belongs to the enclosing one.

        ROUND 12, research's stage-2 S2-1 — THE RESOLVER SENT EVERY CHILD OF THE STATEMENT TO THE INNER BLOCK. Python
        evaluates decorators, defaults (positional, positional-only, keyword-only), argument and return annotations,
        and a class's bases and keywords in the ENCLOSING scope, when the statement executes — so a site or census
        alias read there is the MODULE's binding, and this answered "a local: not ours". Measured at d61fd62: twelve
        definition-time positions, all twelve wrong, and two consumers took the answer at face value — round 12's R2
        refusal missed every one of them, and round 11's unresolved-bypass detector went SILENT
        (`def f(q, on=_census.enabled())` left a live census call in the twin with nothing reported). The
        comprehension handler below already made exactly this distinction for its first iterable; definitions
        never got it.

        THE ENCLOSING PARTS ARE ASSIGNED BY THE CALLER, FIRST, and skipped here BY IDENTITY (round 12, S2b-1): one
        definition of which parts are enclosing — `_enclosing_parts` — and this pass excludes exactly the node objects
        it returned. Two definitions of one set (one by role, one by field) would visit a node twice, a double pop and
        an UnresolvableScope on correct code, or never, a node the resolver cannot place.

        EACH NODE IS VISITED EXACTLY ONCE. The tempting fix — assign everything to the inner block as before, then
        RE-assign the definition-time parts to the enclosing one — visits a lambda or comprehension nested inside a
        default TWICE, and each visit consumes a symbol-table block from the cursor queue: a wrong answer, or an
        UnresolvableScope on a correct module. The statement is split before anything is recursed into.

        NAMED BOUNDARY: PEP 695 type parameters (3.12+) and PEP 649 annotation scopes (3.14) evaluate in scopes of
        their own. Neither can appear in code that must parse on 3.10, this project's floor, so `type_params` keeps
        the inner block and annotations are treated as 3.10-3.13 evaluate them."""
        for field, value in ast.iter_fields(node):
            for item in (value if isinstance(value, list) else [value]):
                if not isinstance(item, ast.AST) or id(item) in enclosing_ids:
                    continue                                   # an enclosing part: assigned to the outer block, first
                if isinstance(item, ast.arguments):
                    self._owner[id(item)] = inner; self._comp_local[id(item)] = frozenset()
                    for avalue in (v for _, v in ast.iter_fields(item)):
                        for a in (avalue if isinstance(avalue, list) else [avalue]):
                            if not isinstance(a, ast.AST) or id(a) in enclosing_ids:
                                continue                       # None for "no default", or a default: enclosing
                            self._owner[id(a)] = inner         # an ast.arg: the PARAMETER binds inside; its
                            self._comp_local[id(a)] = frozenset()  # annotation was an enclosing part, done first
                else:
                    self._assign_child(item, inner, frozenset())       # a real block resets any inlined shadowing

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
        # ROUND 12, research's stage-2c S2c-2 — WHERE SYMTABLE IS NOT THE INTERPRETER, REFUSE. An INLINABLE comprehension
        # in this comprehension's FIRST iterable, inside a function or class block: 3.13's symtable calls a variable
        # of it LOCAL where the compiler resolves it to the module — measured by EXECUTING it, which returned the
        # module's value on 3.10, 3.11 and 3.13 while 3.13's table said local; through the transform a census read
        # there stayed live with unresolved=0. On 3.12.3 the source itself raises UnboundLocalError. This resolver's
        # premise is that symtable IS the interpreter's analysis; here, on 3.12+, it is not, so there is no answer
        # to give. 3.10/3.11 agree with their compiler and resolve correctly: the refusal is loud where it fires and
        # the answer right where it does not, which is not round 8's SILENT version divergence. Module level is
        # exempt because `refers_to_module_binding` answers module there without consulting the table. Refused on
        # Quentin's word; research measured it over-refuses nothing in the tree.
        if sys.version_info >= (3, 12) and block.get_type() != "module" and child.generators \
                and any(isinstance(n, _INLINABLE) for n in ast.walk(child.generators[0].iter)):
            raise UnresolvableScope(
                f"line {child.lineno}: an inlinable comprehension sits in this comprehension's first iterable, inside a "
                f"{block.get_type()} block — on Python 3.12+ the symtable's reading of that shape disagrees with the "
                f"compiler's (3.13 calls a comprehension variable local where the compiled code reads the module), so "
                f"no scope answer here can be trusted; refused rather than guessed (round 12, S2c-2)")
        # ROUND 12, S2b-1 — ORDER: the FIRST ITERABLE is assigned BEFORE this comprehension's block is taken from the
        # queue. The interpreter evaluates it in the enclosing scope and creates any block nested in it FIRST; this
        # handler took its own block first, so `list(ooo for ooo in (iii for iii in xs))` handed each genexp the
        # other's table — on every version, and live at asof/resolve.py:445, while a test compared the two owners as
        # a SET and could not see it. One role, documented order: fixed by ordering, never refused. (The FIRST iterable only;
        # everything else inside the comprehension is ordered below, and that order was wrong until round 13.)
        first_iter = child.generators[0].iter if child.generators else None
        if first_iter is not None:
            self._assign_child(first_iter, block, shadowed)         # the enclosing scope, both regimes
        key = (child.lineno, _expected_name(child))
        queue = self._blocks.get(key) or []
        cursor = self._cursor.get(key, 0)
        inner = None
        if cursor < len(queue):
            inner = queue[cursor]; self._cursor[key] = cursor + 1
            self._joined.setdefault(key, []).append((child, inner))
        elif not isinstance(child, _INLINABLE):
            raise UnresolvableScope(f"line {child.lineno}: no symbol-table block joins this "
                                    f"{type(child).__name__} — the resolver will not guess its scope")
        self._owner[id(child)] = block
        body_block = inner if inner is not None else block
        body_shadow = frozenset() if inner is not None else shadowed | self._comprehension_targets(child)
        # ROUND 13, the round-12 verdict's F1 (research's S2c-1) — THE ORDER INSIDE THE COMPREHENSION IS CPython's, not
        # a field walk. `symtable_handle_comprehension` visits the outermost target and ifs, then each later generator
        # as target, iter, ifs (`symtable_visit_comprehension`), then a dict comprehension's VALUE, then the element or
        # KEY last. This handler walked elt/key/value FIRST, so same-line same-kind scopes split between the element and
        # an `if` or later iterable — or between a key and a value — were handed each other's tables: a census read
        # stayed live in the twin with verify() clean and unresolved=0, on every version. It was disclosed as open in
        # round 12 and returned as blocking. Round 12's comment above says "One role, documented
        # order: fixed by ordering" — true of the first iterable only.
        for i, gen in enumerate(child.generators):
            self._comp_local[id(gen)] = body_shadow
            self._owner[id(gen)] = body_block
            self._assign_child(gen.target, body_block, body_shadow)
            if i:
                self._assign_child(gen.iter, body_block, body_shadow)
            for cond in gen.ifs:
                self._assign_child(cond, body_block, body_shadow)
        for field in ("value", "elt", "key"):
            sub = getattr(child, field, None)
            if sub is not None:
                self._assign_child(sub, body_block, body_shadow)

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

    def nested_global_bindings(self, name: str) -> list[tuple[str, int]]:
        """Every NESTED code object that binds this module's `name`, as (code object, line) — RULE C's
        reading, made public beside rule A's.

        ROUND 11: both readings are public now because the CENSUS ALIAS needs the same pair the SITE question
        has always used, and round 10 gave it only `module_binding_count`. A nested `global X; X = ...`, a
        nested import and a comprehension walrus all replace a module binding WITHOUT moving the module-level
        count, which is precisely why the site question reads both. One of these two being public and the
        other private is how the asymmetry survived a round."""
        return self._nested_global_bindings(name)

    def module_binding_count(self, name: str) -> int:
        """How many times the MODULE's own code object binds `name` — rule A's reading, made public.

        ROUND 10: the twin transform needs it for the CENSUS ALIAS, not just for sites. A name imported once
        and then reassigned (`from . import census as _census` … `_census = On()`) is bound TWICE here, which
        is the only part of "does this name still denote the census module?" a static reading can answer.
        It answers WHETHER THE BINDING MOVED, never WHAT IT DENOTES — see `_is_census_alias`."""
        return len(self._module_binding_ops(name))

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
