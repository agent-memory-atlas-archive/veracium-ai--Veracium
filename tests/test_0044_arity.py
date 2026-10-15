"""specs/0044 (accepted v1.6) — relation arity: the declaration and its refusals (T5-1).

INV-A3 (`keyed` is refused at the registry boundary), INV-A4 (every registry valid today keeps its meaning:
`functional=True ≡ single`) and INV-A10 (`functional` and `arity` cannot disagree). Each is checked on BOTH forms a
host can supply: a `Relation` model and a duck-typed entry, which never passes the model's validator.
"""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from veracium.registry import RegistryError, declared_arity, effective_registry
from veracium.schema import DEFAULT_RELATIONS, RESERVED_RELATIONS, Relation


def _host(**extra):
    """A host holding ONLY the cell's own subject (the boundary injects the reserved members): a cell about A3 or
    A10 must not depend on the default registry's derivation, which is A4's subject (a mutant of it would
    otherwise fail these cells by a refusal, not by their own assertion)."""
    return dict(extra)


def _accepted(what, host):
    """IO-II-7's form (as tests/test_0008_request_registry.py's `_permitted`): a registry a cell EXPECTS the boundary
    to accept is asserted as a permission, so a refusal fails as an ASSERTION naming it, never as an escaping
    RegistryError a mutation campaign cannot classify."""
    try:
        return effective_registry(host)
    except ValueError as x:
        raise AssertionError(f"{what} was refused: {type(x).__name__}: {x}") from x


# ---- INV-A4: no registry valid today changes meaning ------------------------------------------------------------

def test_an_absent_arity_is_derived_from_functional_on_every_default_and_reserved_relation():
    """Every relation declared without `arity` reads `single` iff it is functional: the default registry's own
    entries, the reserved members and a duck-typed host entry. A4's mutant (map `True` to `multi`) breaks every
    functional row. The default registry itself is ACCEPTED by the boundary."""
    for name, r in {**DEFAULT_RELATIONS, **RESERVED_RELATIONS}.items():
        assert declared_arity(r) == ("single" if r.functional else "multi"), name
    reg = _accepted("the default registry", DEFAULT_RELATIONS)
    for name, fr in reg.items():
        assert fr.arity == ("single" if fr.functional else "multi"), name
    assert reg["works_as"].arity == "single" and reg["uses_tool"].arity == "multi"
    duck = SimpleNamespace(name="tenure", functional=True, desc="years in role")
    assert declared_arity(duck) == "single"
    assert _accepted("a duck-typed functional entry", _host(tenure=duck))["tenure"].arity == "single"


def test_a_relation_changed_after_construction_keeps_the_meaning_it_had_before_0044():
    """research's T5-1 finding: `Relation` is a mutable model, so a host may set `functional` after construction or
    copy with `model_copy(update=…)`, which runs no validator. Both forms were valid at c31bd9f and must stay valid,
    reading the arity their CURRENT `functional` gives. The mutant: fill the arity at construction (the stored value
    then disagrees, and the boundary refuses a registry valid today)."""
    r = Relation(name="x")
    r.functional = True
    copied = Relation(name="y", functional=False).model_copy(update={"functional": True})
    reg = _accepted("a Relation mutated after construction, and one copied with model_copy", _host(x=r, y=copied))
    assert (reg["x"].functional, reg["x"].arity) == (True, "single")
    assert (reg["y"].functional, reg["y"].arity) == (True, "single")
    assert r.arity is None and copied.arity is None            # undeclared: derived at read, never stored


def test_an_absent_functional_is_derived_from_arity():
    assert Relation(name="r1", arity="single").functional is True
    assert Relation(name="r2", arity="multi").functional is False
    reg = _accepted("a declared single arity", _host(r1=Relation(name="r1", arity="single")))
    assert reg["r1"].functional is True and reg["r1"].arity == "single"


# ---- INV-A3: `keyed` is reserved -------------------------------------------------------------------------------

def test_a_registry_declaring_keyed_is_refused_in_both_forms():
    """The model HOLDS the reserved word (it is the spec's vocabulary); the registry boundary refuses it, so a
    duck-typed entry is refused by the same rule."""
    held = Relation(name="weighs", arity="keyed")
    assert held.arity == "keyed"
    for entry in (held, SimpleNamespace(name="weighs", functional=False, desc="", arity="keyed")):
        with pytest.raises(RegistryError, match="reserved word"):
            effective_registry(_host(weighs=entry))


def test_an_arity_outside_the_vocabulary_is_refused_in_both_forms():
    with pytest.raises(ValidationError):
        Relation(name="r", arity="several")
    with pytest.raises(RegistryError, match="outside single/multi"):
        effective_registry(_host(r=SimpleNamespace(name="r", functional=False, desc="", arity="several")))


# ---- INV-A10: the two declarations cannot disagree ----------------------------------------------------------------

@pytest.mark.parametrize("functional,arity", [(True, "multi"), (False, "single")])
def test_functional_and_arity_disagreeing_are_refused_in_both_forms(functional, arity):
    with pytest.raises(ValidationError, match="disagree"):
        Relation(name="r", functional=functional, arity=arity)
    # a model instance mutated after construction never re-runs the validator: the boundary refuses it
    mutated = Relation(name="r", functional=functional)
    mutated.arity = arity
    duck = SimpleNamespace(name="r", functional=functional, desc="", arity=arity)
    for entry in (mutated, duck):
        with pytest.raises(RegistryError, match="disagree"):
            effective_registry(_host(r=entry))


@pytest.mark.parametrize("functional,arity", [(True, "single"), (False, "multi")])
def test_functional_and_arity_agreeing_are_admitted(functional, arity):
    """The positive control for A10: the refusal is of disagreement, not of declaring both."""
    r = Relation(name="r", functional=functional, arity=arity)
    assert _accepted("an agreeing declaration", _host(r=r))["r"].arity == arity
