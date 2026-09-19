"""The reference provider never returns an empty completion as a result (2026-09-19).

Research reproduced against the SDK: a hard prompt at the default `max_tokens` spends the
whole budget inside a `thinking` block; the call succeeds with `stop_reason == "max_tokens"`
and no text block; `AnthropicComplete` returned "" and the caller read it as a finding (an
empty gate answer looks like an abstention). The assembly is one pure function over the
message shape, tested here without the SDK; the provider is asserted to render through it.
"""
import inspect
from types import SimpleNamespace as NS

import pytest

from veracium.llm import anthropic as provider


def _msg(blocks, stop_reason, output_tokens=4096):
    return NS(content=blocks, stop_reason=stop_reason, usage=NS(output_tokens=output_tokens))


def _text(t):
    return NS(type="text", text=t)


def test_thinking_only_at_max_tokens_raises_and_names_the_cause():
    """Research's reproduction: block types ['thinking'], stop_reason max_tokens, 4096 output
    tokens, previously returned ''."""
    with pytest.raises(provider.EmptyCompletion) as ei:
        provider.text_of(_msg([NS(type="thinking", thinking="…")], "max_tokens"),
                         max_tokens=4096, model="claude-sonnet-5")
    e = ei.value
    assert e.stop_reason == "max_tokens" and e.output_tokens == 4096
    assert e.block_types == ["thinking"] and e.max_tokens == 4096
    assert "max_tokens" in str(e) and "raise max_tokens" in str(e) and "thinking" in str(e)


@pytest.mark.parametrize("stop_reason", ["end_turn", "refusal", "stop_sequence", "max_tokens"])
def test_no_text_block_is_refused_whatever_the_stop_reason(stop_reason):
    """An empty completion is never a result: not a refusal, not an end_turn with nothing said."""
    with pytest.raises(provider.EmptyCompletion) as ei:
        provider.text_of(_msg([], stop_reason, output_tokens=3), max_tokens=64, model="m")
    assert ei.value.stop_reason == stop_reason and ei.value.block_types == []


def test_text_blocks_are_joined_and_thinking_is_dropped():
    msg = _msg([NS(type="thinking", thinking="…"), _text("a"), _text("b")], "end_turn")
    assert provider.text_of(msg, max_tokens=64, model="m") == "ab"


def test_a_truncated_answer_with_text_is_returned_not_raised():
    """`max_tokens` WITH a text block is a cut-off answer, not an empty one: it is returned
    (the JSON roles fail parsing on their own recorded path); only emptiness is refused."""
    assert provider.text_of(_msg([_text("partial")], "max_tokens"), max_tokens=64, model="m") == "partial"


def test_the_provider_renders_through_the_one_assembly():
    """The surface calls `text_of` — not a copy of its join — so the control measures the
    thing that is wired up (the builder-binding lesson of the same day)."""
    src = inspect.getsource(provider.AnthropicComplete.__call__)
    assert "text_of(" in src
    assert '"".join' not in src


def test_the_empty_completion_is_an_error_the_pools_classify():
    """`lifecycle` wraps its completion in `except Exception` → `llm-error`; the new error is an
    ordinary RuntimeError so that path, and every host `except Exception`, keeps working."""
    assert issubclass(provider.EmptyCompletion, RuntimeError)
