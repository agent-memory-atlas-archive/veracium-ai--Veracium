"""specs/0042 — THE PAIRING ORACLE: the scope resolver's AST-to-symbol-table join, tested against CPython's BYTECODE.

WHY IT EXISTS (round 13). Every silent defect of rounds 12 and 13 was one shape: two same-line, same-kind scopes whose
symbol-table blocks the resolver handed out in the wrong order — a definition-time part (S2-1), a header beside its own
block (S2b-1), a comprehension's element against its `if` or later iterable (S2c-1, the round-12 verdict's F1). Each was
found by a hand-built cell and each closed by ordering ONE more construct. This tests the CLASS: random one-line
programs dense with nested same-kind scopes, and for every tagged read, the resolver's answer compared with the one
the interpreter's compiler gives.

GROUND TRUTH IS THE BYTECODE, NOTHING ELSE. A tagged read `(NAME, TAG)` compiles to a load instruction; LOAD_GLOBAL /
LOAD_NAME / LOAD_FROM_DICT_OR_GLOBALS means the compiler resolved NAME to the module, any other LOAD means it did not.
Research's first oracle computed expectations from a scoping MODEL of its own; that model disagreed with the bytecode
on 3,868 of 303,193 reads, so it is not vendored — only the program generator and the bytecode reading are (research's
stage-1 read of round 13, R3(i)). Instruction positions (3.11+) locate each read; 3.10 has none, so the gate SKIPS
there, visibly, and never passes (R3(iii)).

THE GENERATOR COVERS TIED SIGNATURES ON PURPOSE (R3). Research's generator gave every lambda a unique parameter and
every comprehension a unique target, so signatures always differed and the resolver's join check looked complete
against it BY CONSTRUCTION. This one also makes parameter-less lambdas that bind a name by walrus, and comprehensions
that share a target — the cases where a signature cannot tell two blocks apart.

A GATE THAT CANNOT FAIL IS NOT A GATE (R3(ii)). `positive_control_resolver()` builds, from this tree's own resolver
source, the round-12 comprehension order with the join check removed; the gate asserts it produces SILENT wrong
answers on the same programs every time it runs. If it does not, the programs no longer reach the defect class and the
gate says so instead of passing.

Vendored from veracium-research proposals/probes/0042-round12-STAGE2c-oracle.py (the generator) and -oracle2.py (the
bytecode truth); this copy is the one both seats load.
"""
# Mutation-Matrix: tests/test_0042_scope_resolution.py::test_r13_the_pairing_oracle_finds_no_silent_answer_and_its_control_does
from __future__ import annotations

import ast
import collections
import dis
import importlib.util
import pathlib
import random
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
MODULE_OPS = {"LOAD_GLOBAL", "LOAD_NAME", "LOAD_FROM_DICT_OR_GLOBALS"}


def _load_resolver(path: pathlib.Path, name: str):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


class _Gen:
    """One program's scopes. Reads are placeholders until every binder is known; each is then filled with a read of
    EVERY name, so every symbol table holds every name and a swapped table flips at least one answer."""

    def __init__(self, rng):
        self.rng, self.n, self.binders, self.reads = rng, 0, [], 0
        self.role, self.read_roles = "expression", []          # round 19 (N5): the ROLE each read was generated in

    def read(self):
        self.reads += 1
        self.read_roles.append(self.role)
        return f"@R{self.reads - 1}@"

    def in_role(self, role, depth):
        """An expression generated as `role` (an annotation) — every read inside it, however deep, carries the role."""
        outer, self.role = self.role, role
        try:
            return self.expr(depth)
        finally:
            self.role = outer

    def expr(self, depth):
        r = self.rng.random()
        if depth <= 0 or r < 0.2:
            return self.read()
        k = self.n; self.n += 1
        kind = self.rng.choice(["lambda", "lambda", "walrus-lambda", "genexp", "listcomp", "setcomp", "dictcomp"])
        if kind == "lambda":
            p = f"p{k}"; self.binders.append(p)
            dflt = f"={self.expr(depth - 1)}" if self.rng.random() < 0.5 else ""
            return f"(lambda {p}{dflt}: {self.expr(depth - 1)})"
        if kind == "walrus-lambda":                     # R3: a PARAMETER-LESS lambda binding a name by walrus
            w = f"w{k}"; self.binders.append(w)
            return f"(lambda: ((({w} := 0)), {self.expr(depth - 1)}))"
        # a comprehension; R3: its target is SHARED with other comprehensions a third of the time
        t = "tt" if self.rng.random() < 0.33 else f"t{k}"
        self.binders.append(t)
        first = self.expr(depth - 1)                     # the first iterable: evaluated in the ENCLOSING scope
        tail = ""
        if self.rng.random() < 0.4:
            tail += f" if {self.expr(depth - 1)}"
        if self.rng.random() < 0.4:
            u = f"u{k}"; self.binders.append(u)
            tail += f" for {u} in {self.expr(depth - 1)}"
            if self.rng.random() < 0.4:
                tail += f" if {self.expr(depth - 1)}"
        if kind == "dictcomp":
            return f"{{{self.expr(depth - 1)}: {self.expr(depth - 1)} for {t} in {first}{tail}}}"
        o, c = {"genexp": "()", "listcomp": "[]", "setcomp": "{}"}[kind]
        return f"{o}{self.expr(depth - 1)} for {t} in {first}{tail}{c}"

    def fill(self, text):
        names = sorted(set(self.binders)) or ["M"]
        for i in range(self.reads):
            text = text.replace(f"@R{i}@", "(" + ", ".join(f"({nm}, {1000 * i + j})" for j, nm in enumerate(names)) + ",)", 1)
        return text, names


def program(rng) -> tuple[str, int]:
    src, discarded, _roles = program_with_roles(rng)
    return src, discarded


def program_with_roles(rng, future: bool = False) -> tuple[str, int, list]:
    """-> (one module, programs discarded to reach it). Every name bound once at module level, then one line holding
    the generated scopes — a def with its header roles, a lambda, a class header, or a bare expression. The walrus has
    lexical restrictions the generator does not model (none inside a comprehension's iterable, even within a lambda),
    so a draw that does not COMPILE is discarded and counted rather than encoded as another rule here."""
    discarded = 0
    while True:
        src, roles = _draw(rng, future)
        try:
            compile(src, "<oracle>", "exec", dont_inherit=True)
            return src, discarded, roles
        except SyntaxError:
            discarded += 1


def _draw(rng, future: bool = False) -> tuple[str, list]:
    """-> (one module, each read's role). Round 19 (N5, the second seat's stage-1 read): annotations are ROLES — a
    parameter's, a keyword-only parameter's and the return's, on a module-level def and on a METHOD in a class body,
    where class-scope resolution is subtle — so the gate judges reads inside them. `future=True` draws only annotated
    shapes under `from __future__ import annotations`, the NAMED control: stringified annotations have no load, so
    those reads must read "no instruction", never "wrong"."""
    g = _Gen(rng)
    shape = rng.choice(["def", "method"]) if future else rng.choice(["def", "def", "method", "lambda", "class", "expr", "expr"])
    D = rng.choice([1, 2, 3])

    def maybe():
        return g.expr(D) if rng.random() < 0.5 else None

    def maybe_ann(role):
        return g.in_role(role, D) if (future or rng.random() < 0.5) else None

    def header(first, where):
        a = maybe_ann(f"{where} parameter annotation"); d = maybe(); ka = maybe_ann(f"{where} keyword-only annotation")
        kd = maybe(); ret = maybe_ann(f"{where} return annotation")
        return (f"({first}a0{': ' + a if a else ''}{' = ' + d if d else ''}, *, k0{': ' + ka if ka else ''}"
                f"{' = ' + kd if kd else ''}){' -> ' + ret if ret else ''}")
    if shape == "def":
        line = f"def f{header('', 'function')}: return {g.expr(D)}"
    elif shape == "method":
        line = f"class C:\n    def m{header('self, ', 'method')}: return {g.expr(D)}"
    elif shape == "lambda":
        k = g.n; g.n += 1; p = f"p{k}"; g.binders.append(p)
        d = maybe(); line = f"L = lambda {p}{'=' + d if d else ''}: {g.expr(D)}"
    elif shape == "class":
        line = f"class C(mk({g.expr(D)})): pass"
    else:
        line = f"X = ({g.expr(D)}, {g.expr(D)})"
    line, names = g.fill(line)
    head = "from __future__ import annotations\n" if future else ""
    return head + "def mk(*a, **k): return object\nM = 0\n" + "".join(f"{nm} = 0\n" for nm in names) + line + "\n", list(g.read_roles)


def truth(src: str) -> dict:
    """(line, column, name) -> the compiler resolved this read to the MODULE. Every load of a tagged name, in every
    code object, located by its instruction position (3.11+). A read with no instruction at its position is NOT judged
    and is counted as unmapped. On 3.11 and 3.12 there are none. On 3.13 there are two causes, each measured read by read
    (round 19, the corpus at seed 13 after annotations became roles — 182 unmapped reads, every one attributed): 138 are
    reads FUSED into a STORE_FAST_LOAD_FAST superinstruction (a local read immediately after its own store, e.g. a
    comprehension target read at the start of the body — the instruction is a STORE and carries one position), and 44
    are reads inside ANNOTATIONS, parameter and return alike. An earlier form of this docstring attributed them to
    return annotations alone, measured at a time no read carried its role. The gate bounds the unmapped share."""
    out = {}

    def walk(co):
        for ins in dis.get_instructions(co):
            pos = getattr(ins, "positions", None)
            if ins.opname.startswith("LOAD") and isinstance(ins.argval, str) and pos is not None \
                    and pos.col_offset is not None:
                out[(pos.lineno, pos.col_offset, ins.argval)] = ins.opname in MODULE_OPS
        for c in co.co_consts:
            if isinstance(c, types.CodeType):
                walk(c)
    walk(compile(src, "<oracle>", "exec", dont_inherit=True))
    return out


def is_tied(src: str) -> bool:
    """Does the PROGRAM hold the case the join check exists for — a same-line, same-kind group of symbol-table blocks
    two of which have EQUAL signatures and DIFFERENT fingerprints? Read from `symtable` directly, never from the
    resolver's outcome (research's stage-2 B1: the gate first counted join-check REFUSALS as "tied programs reached",
    and every one of the 39 it counted at its own settings was an over-refusal of an UNTIED program, so switching the
    tied generators off left the assertion met). Research's definitions, so both seats count one thing: a signature is
    a function block's parameters (`.0` excluded) or a comprehension block's non-parameter locals; a fingerprint is
    the block type and every symbol's (name, parameter, local, global, free)."""
    import symtable
    groups = collections.defaultdict(list)

    def walk(t):
        for c in t.get_children():
            groups[(c.get_lineno(), c.get_name())].append(c); walk(c)
    walk(symtable.symtable(src, "<oracle>", "exec"))

    def sig(b):
        if b.get_name() in ("genexpr", "listcomp", "setcomp", "dictcomp"):
            return ("comp", tuple(sorted(x.get_name() for x in b.get_symbols() if x.is_local() and not x.is_parameter())))
        return ("fn", tuple(sorted(p for p in b.get_parameters() if p != ".0")) if b.get_type() == "function" else ())

    def fp(b):
        return (b.get_type(), tuple(sorted((x.get_name(), x.is_parameter(), x.is_local(), x.is_global(), x.is_free())
                                           for x in b.get_symbols())))
    for blocks in groups.values():
        for i, a in enumerate(blocks):
            for b in blocks[i + 1:]:
                if sig(a) == sig(b) and fp(a) != fp(b):
                    return True
    return False


def judge(resolver_module, src: str, roles: list | None = None, by_role: collections.Counter | None = None) -> tuple[str, int, int]:
    """-> (outcome, reads checked, reads the bytecode did not locate). OK, SILENT (a wrong answer, nothing refused),
    or REFUSED (loud — the resolver declined). With `roles` (each read's role, from program_with_roles) and a
    `by_role` counter, every read is also tallied as (role, "judged") or (role, "no instruction") — round 19 (N5): a role
    whose reads are never judged would pass the gate silently, so the gate MEASURES the numerator per role."""
    tr = truth(src)
    try:
        r = resolver_module.Resolver(src, "<oracle>")
    except resolver_module.UnresolvableScope as e:
        # split so the gate can assert the TIED-signature programs are reached: the join check refuses exactly those
        return ("REFUSED by the join check" if "join check" in str(e) else "REFUSED otherwise"), 0, 0
    checked = unmapped = 0; wrong = False
    for n in ast.walk(r.tree):
        if isinstance(n, ast.Tuple) and len(n.elts) == 2 and isinstance(n.elts[0], ast.Name) \
                and isinstance(n.elts[1], ast.Constant) and type(n.elts[1].value) is int:
            nm = n.elts[0]; key = (nm.lineno, nm.col_offset, nm.id)
            role = roles[n.elts[1].value // 1000] if roles is not None else None
            if key not in tr:
                unmapped += 1
                if by_role is not None:
                    by_role[(role, "no instruction")] += 1
                continue
            checked += 1
            if by_role is not None:
                by_role[(role, "judged")] += 1
            if r.refers_to_module_binding(nm, nm.id) != tr[key]:
                wrong = True
    return ("SILENT" if wrong else "OK"), checked, unmapped


_NEW_ORDER = '''        for i, gen in enumerate(child.generators):
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
                self._assign_child(sub, body_block, body_shadow)'''
_OLD_ORDER = '''        for field in ("elt", "key", "value"):
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
                self._assign_child(cond, body_block, body_shadow)'''


def positive_control_resolver():
    """THE GATE'S OWN MUTANT: this tree's resolver with round 12's comprehension order restored and the join check
    removed. It must produce SILENT answers on the gate's programs — built from the source text, and REFUSING if the
    anchors no longer match, because a control that silently stops being a mutant is the failure it exists to catch."""
    src = (HERE / "scope_resolution.py").read_text()
    for anchor in (_NEW_ORDER, "        self._check_join()\n"):
        if src.count(anchor) != 1:
            raise RuntimeError(f"the positive control's anchor matched {src.count(anchor)} times: {anchor[:60]!r}")
    src = src.replace(_NEW_ORDER, _OLD_ORDER).replace("        self._check_join()\n", "")
    path = pathlib.Path(tempfile.mkdtemp()) / "scope_resolution_positive_control.py"
    path.write_text(src)
    return _load_resolver(path, "scope_resolution_positive_control")


def run(n: int, seed: int, resolver_module=None) -> collections.Counter:
    if sys.version_info < (3, 11):
        raise RuntimeError("the pairing oracle needs instruction positions (3.11+); on 3.10 it must SKIP, never pass")
    mod = resolver_module or _load_resolver(HERE / "scope_resolution.py", "scope_resolution_oracle")
    rng = random.Random(seed); t = collections.Counter()
    for _ in range(n):
        src, discarded, roles = program_with_roles(rng)
        outcome, checked, unmapped = judge(mod, src, roles, t)
        t[outcome] += 1; t["reads checked"] += checked; t["reads unmapped"] += unmapped; t["draws discarded"] += discarded
        if is_tied(src):
            t["TIED programs"] += 1; t[f"TIED programs {outcome}"] += 1
    return t


if __name__ == "__main__":
    n, seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1000, int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print("resolver:        ", dict(run(n, seed)))
    print("positive control:", dict(run(n, seed, positive_control_resolver())))
