"""R-A round 2, RA-03 (0008 §2a/§6c, INV-Q2; §6g, INV-Q7): the PUBLIC `Memory.confirm` decides replay, conflict and
the terminal `RequestRedacted` from the request registry BEFORE it reads live target state, as the store does.

At the R-A pin the public wrapper looked the edge up first, so a retained redacted id retried with an absent target
raised the missing-edge ValueError instead of `RequestRedacted`, and an occupied id retried with an absent target
raised it instead of the integrity conflict. The store's ordering was right and our campaign mutated only the store;
these cells attack the public surface. The matrix is the verdict's acceptance list, every row:

  retained REDACTED id   × {same target, a different existing target, an absent target} → RequestRedacted
  occupied NON-redacted  × {a different existing target, an absent target}             → the integrity conflict
  the same id + target after the edge was invalidated                                   → replayed, through the
                                                                                         public read of valid_from
  a NEW id × an absent target                                                            → the ordinary ValueError
"""
from datetime import datetime, timezone

import pytest

from veracium import Memory, MemoryConfig
from veracium.schema import Disclosure, Edge, EvidenceAuthor, Provenance
from veracium.store.base import RequestRedacted

U = "ra2-registry-user"


def _memory(path):
    return Memory(llm=lambda *a, **k: "", config=MemoryConfig(
        db_path=str(path), wiki_recompile_after_writes=0, scope_groups={}, require_source_id=False))


def _add(m, ident):
    m.store.add_edge(Edge(id=ident, user_id=U, subject="user", relation="likes", object=f"{ident}-content",
                          provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ra2",
                                                disclosure=Disclosure.MENTIONABLE)))


def _permitted(what, fn, *a, **k):
    try:
        return fn(*a, **k)
    except (ValueError, KeyError, RuntimeError) as x:
        raise AssertionError(f"{what} was refused: {type(x).__name__}: {x}") from x


def _refuses(cls, fn, *a, match=None, **k):
    """An EXPECTED refusal asserted by its class (test_0008_request_registry.py's form): a different refusal, or none,
    fails as an ASSERTION naming what happened, never as an escaping exception."""
    try:
        fn(*a, **k)
    except cls as x:
        assert match is None or match in str(x), f"refused, but not as {match!r}: {x}"
        return
    except (ValueError, KeyError, RuntimeError) as x:
        raise AssertionError(f"expected {cls.__name__}, refused instead with {type(x).__name__}: {x}") from x
    raise AssertionError(f"DID NOT RAISE {cls.__name__}")


@pytest.fixture
def m(tmp_path):
    mem = _memory(tmp_path / "registry.db")
    _add(mem, "known-target"); _add(mem, "other-target")
    _permitted("the first confirmation", mem.confirm, U, "known-target", correlation_id="ra2-request")
    yield mem
    mem.close()


@pytest.mark.parametrize("target", ["known-target", "other-target", "never-stored-target"])
def test_a_retained_redacted_request_is_terminal_whatever_its_target(m, target):
    m.redact(U, edge_id="known-target", reason="subject_request")
    _refuses(RequestRedacted, m.confirm, U, target, correlation_id="ra2-request")


@pytest.mark.parametrize("target", ["other-target", "never-stored-target"])
def test_an_occupied_request_is_an_integrity_conflict_before_any_target_lookup(m, target):
    _refuses(ValueError, m.confirm, U, target, correlation_id="ra2-request", match="integrity conflict")


def test_a_replay_after_the_target_was_invalidated_returns_the_recorded_confirmation(m):
    """The same id and target, after the edge was retired: the registry replays it (INV-Q2), and the public return
    reads the edge's valid_from AFTER that decision (it is still held, inactive)."""
    m.store.invalidate_edge("known-target", datetime.now(timezone.utc), "disputed")
    out = _permitted("the replay", m.confirm, U, "known-target", correlation_id="ra2-request")
    assert out["replayed"] is True and out["confirmed"] == "known-target"


def test_a_new_request_for_an_absent_target_keeps_the_public_refusal(m):
    """The control: a genuinely new request on an edge this store does not hold raises the same ValueError, with the
    same words, that the public method always raised."""
    _refuses(ValueError, m.confirm, U, "never-stored-target", correlation_id="ra2-new-request",
             match="no edge 'never-stored-target' for user")
