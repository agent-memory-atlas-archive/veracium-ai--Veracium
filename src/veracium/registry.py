"""The effective relation registry — specs/0025 §4b-ii, accepted v13.

The host's registry dict is validated AS SUPPLIED at the `ingest_event`
boundary, the reserved members are injected, and the result is EXTRACTED
into an immutable per-event snapshot of frozen `(name, functional, desc)`
records (with `relation_kind` and, specs/0044 §2, `arity`) — all prompt- and classification-bearing fields (X11). This ONE
snapshot feeds prompt rendering, retry validation, membership, and
supersession; there is no second registry read anywhere in the event.

Construction order (each step's position is load-bearing — §4b-ii):
  1. shape (every value a Relation, every key == its value's name); specs/0044
     §2c: its arity is one of the operational two — `keyed` is reserved and
     refused, and an arity disagreeing with `functional` is refused
  2. empty AS SUPPLIED (before injection can mask it — X5)
  3. conflicting-shadow refusal (the COMPLETE canonical form, desc
     included; an empty gloss is drift too — rounds 2/3/4 each narrowed
     this rule and the shipped DEFAULT_RELATIONS passes verbatim)
  4. injection of both reserved members (X8)
  5. the frozen snapshot (X11)

Differentially tested against specs/evidence/0025/reference_enforcement.py.
"""
from types import MappingProxyType
from typing import NamedTuple

from .schema import QUARANTINE_RELATION, RESERVED_RELATIONS, UNCLASSIFIED_RELATION
from .census import declare_site

# specs/0042 (tranche 3): the enforcement points of this module, each a declared site the
# decision is returned THROUGH — consult() brackets the decision, fire() wraps the value
_SITE_REGISTRY_EMPTY = declare_site("registry.empty-refused")
_SITE_RESERVED_SHADOWED = declare_site("registry.reserved-shadowed")
_SITE_REGISTRY_ARITY = declare_site("registry.arity-refused")


class FrozenRel(NamedTuple):
    """The snapshot's OWN record — never the host's mutable model.
    `relation_kind` (specs/0037 §4a) rides the snapshot so the prompt
    filter, the vocabulary check and the retry pool all read ONE frozen
    declaration per event."""
    name: str
    functional: bool
    desc: str
    relation_kind: str = "declarative"

    @property
    def arity(self) -> str:
        """specs/0044 §2: the snapshot carries arity DERIVED from its one stored bit, so the two can never
        disagree on a record. Stage 1 admits only `single` and `multi` (the boundary refuses `keyed` and any
        disagreement before a FrozenRel is built), so `functional` determines it."""
        return "single" if self.functional else "multi"


class RegistryError(ValueError):
    """A host registry the boundary refuses (X5/X9)."""


def declared_arity(v) -> str:
    """specs/0044 §4a: an entry's arity — its own declaration, or (absent, as on every registry written before
    0044 and on a duck-typed entry) derived from `functional`, so `functional=True ≡ single`."""
    a = getattr(v, "arity", None)
    return a if a is not None else ("single" if v.functional else "multi")


def effective_registry(host: dict) -> MappingProxyType:
    # 1. shape
    for k, v in host.items():
        if not hasattr(v, "name") or not hasattr(v, "functional"):
            raise RegistryError(f"value for {k!r} is not a Relation")
        if k != v.name:
            raise RegistryError(f"key {k!r} != Relation.name {v.name!r} — "
                                f"membership and lookup would disagree")
        # specs/0044 §2c (INV-A3, INV-A10): checked on the entry AS SUPPLIED, whatever class built it — a model
        # instance mutated after construction, or a duck-typed entry, never reached Relation's validator
        with _SITE_REGISTRY_ARITY.consult():
            a = declared_arity(v)
            if a == "keyed":
                raise _SITE_REGISTRY_ARITY.fire(RegistryError(
                    f"relation {k!r} declares arity 'keyed', a reserved word no registry may declare yet "
                    f"(specs/0044 §4a, INV-A3)"))
            if a not in ("single", "multi"):
                raise _SITE_REGISTRY_ARITY.fire(RegistryError(
                    f"relation {k!r} declares arity {a!r}, outside single/multi (specs/0044 §2c)"))
            if bool(v.functional) != (a == "single"):
                raise _SITE_REGISTRY_ARITY.fire(RegistryError(
                    f"relation {k!r} declares functional={v.functional!r} and arity={a!r}, which disagree "
                    f"(specs/0044 INV-A10)"))
    # 2. empty — AS SUPPLIED (X5)
    with _SITE_REGISTRY_EMPTY.consult():
        if not host:
            raise _SITE_REGISTRY_EMPTY.fire(RegistryError("empty registry refused — every relation would "
                                "be off-vocabulary, silently"))
    # 3. conflicting shadows only; the canonical form is COMPLETE (desc
    #    included, empty is drift)
    for name, canon in RESERVED_RELATIONS.items():
        if name in host:
            v = host[name]
            with _SITE_RESERVED_SHADOWED.consult():
                if (bool(v.functional) != canon.functional
                        or getattr(v, "desc", "") != canon.desc):
                    raise _SITE_RESERVED_SHADOWED.fire(RegistryError(
                        f"reserved name conflictingly shadowed: {name!r} — the "
                        f"canonical form is (functional={canon.functional}, "
                        f"desc={canon.desc!r})"))
    # 4. injection — any reserved member not already (canonically) present
    eff = {k: FrozenRel(v.name, bool(v.functional), getattr(v, "desc", ""),
                        getattr(v, "relation_kind", "declarative"))
           for k, v in host.items()}
    for name, canon in RESERVED_RELATIONS.items():
        eff.setdefault(name, FrozenRel(canon.name, canon.functional,
                                       canon.desc))
    # 5. the snapshot
    return MappingProxyType(eff)


def render_prompt_relations(reg) -> str:
    """§4b-iv: the extractor-SELECTABLE set — the effective registry minus
    `unclassified` — rendered in the registry's INSERTION order (round 4,
    R4-2: sorting changed prompt bytes), in the exact line format the
    prompt has always used. `third_party_claim` stays selectable: the
    trust convention requires the extractor to emit it for hearsay."""
    # specs/0037 v16 §4a-iii (V-EXTRACTOR-QUOTE-GATED; replaces v15's
    # V-EXTRACTOR-BLIND filter): a PROCEDURAL relation IS in the extractor's
    # vocabulary — the selectable set is exactly 0025 §4b-iv's, the effective
    # registry minus `unclassified` — and a triple under it is admitted at
    # ingest only with a verbatim `quote` verified against the event text.
    return "\n".join(
        f"- {name}: {r.desc}" if r.desc else f"- {name}"
        for name, r in reg.items()
        if name != UNCLASSIFIED_RELATION)
