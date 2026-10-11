"""Minimal pairs for R1-01's "drop polarity" mutant (research, 2026-10-11), written AFTER the mutant survived on
200 labelled items. Adjacency already excludes negation INSIDE the trigger-object span ("I don't work as a nurse"),
so only negation OUTSIDE it exercises ATTEST's NEGATION list. A mutation fixture written by the predicate's author:
never quoted as a rate. Last item: the list's cost, a safe-direction miss."""
PAIRS = [
    ("located_at", "Brisbane", "It's not true that I live in Brisbane.", False),
    ("located_at", "Brisbane", "It's true that I live in Brisbane.", True),
    ("uses_tool", "Notion", "I use Notion — not.", False),
    ("uses_tool", "Notion", "I use Notion daily.", True),
    ("health_state", "asthma", "I have asthma, no longer though.", False),
    ("health_state", "asthma", "I have asthma, mild though.", True),
    ("has_diet", "vegetarian", "I'm vegetarian, never been anything else.", True),
]
