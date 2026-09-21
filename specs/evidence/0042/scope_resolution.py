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
import symtable

# A block is joined to its AST node by (line, symtable's own name for that kind of block). The set of nodes that
# GET a block is an INTERPRETER FACT, not a constant: PEP 709 inlines list/set/dict comprehensions from 3.12, so on
# 3.12+ they have no block and their target lives in the enclosing block, while on 3.10/3.11 each has its own. CI
# runs 3.10 through 3.13, so the rule is DERIVED — a comprehension with no block is inlined (stay in the enclosing
# block); a def, class or lambda with no block is unjoinable and REFUSED.
_BLOCK_NAME = {ast.Lambda: "lambda", ast.ListComp: "listcomp", ast.SetComp: "setcomp",
               ast.DictComp: "dictcomp", ast.GeneratorExp: "genexpr"}
_INLINABLE = (ast.ListComp, ast.SetComp, ast.DictComp)
SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
               ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _expected_name(node) -> str:
    return node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else _BLOCK_NAME[type(node)]


class UnresolvableScope(Exception):
    """A name or a block the resolver will not guess at: an unjoinable scope, or `global <site>` with an assignment."""


class Resolver:
    """Answers, for any AST node in one module's source: does `NAME` here refer to the MODULE-level binding?"""

    def __init__(self, src: str, filename: str = "<scan>"):
        self.src = src
        self.tree = ast.parse(src)
        self.table = symtable.symtable(src, filename, "exec")
        self._blocks: dict[tuple, list] = {}
        self._cursor: dict[tuple, int] = {}
        self._index(self.table)
        self._owner: dict[int, symtable.SymbolTable] = {}
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

    def _assign(self, node, block) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, SCOPE_NODES):
                key = (child.lineno, _expected_name(child))
                queue = self._blocks.get(key) or []
                cursor = self._cursor.get(key, 0)
                if cursor >= len(queue):
                    if isinstance(child, _INLINABLE):
                        self._owner[id(child)] = block          # PEP 709 (3.12+): inlined into the enclosing block
                        self._assign(child, block)
                        continue
                    raise UnresolvableScope(f"line {child.lineno}: no symbol-table block joins this "
                                            f"{type(child).__name__} — the resolver will not guess its scope")
                inner = queue[cursor]; self._cursor[key] = cursor + 1
                self._owner[id(child)] = inner
                self._assign(child, inner)
            else:
                self._owner[id(child)] = block
                self._assign(child, block)

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
        """Does `name`, used at `node`, resolve to the module-level binding? The module block IS that binding;
        inside any other block the answer is symtable's GLOBAL (never LOCAL, PARAMETER or FREE)."""
        block = self.block_of(node)
        if block.get_type() == "module":
            return True
        try:
            sym = block.lookup(name)
        except KeyError:
            return False                       # the name is not used in this block at all
        return bool(sym.is_global()) and not sym.is_local() and not sym.is_parameter()

    def refuse_rebound_globals(self, names: set[str]) -> None:
        """`global S` alone still reads the site; `global S` WITH an assignment REPLACES the module binding for
        every other reader, which no static reading of the other sites can account for. Refused, not resolved."""
        def walk(block):
            for n in names:
                if block.get_type() == "module":
                    continue          # the module block's own `S = declare_site(...)` IS the declaration, not a rebinding
                try:
                    sym = block.lookup(n)
                except KeyError:
                    continue
                if sym.is_declared_global() and sym.is_assigned():
                    raise UnresolvableScope(f"block {block.get_name()!r} (line {block.get_lineno()}): "
                                            f"`global {n}` with an assignment replaces the declared site itself")
            for c in block.get_children():
                walk(c)
        walk(self.table)
