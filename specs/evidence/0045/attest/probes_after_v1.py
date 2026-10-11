"""Probes written AFTER ATTEST-1's corpus run, the predicate unchanged (research, 2026-10-11).
Result at ATTEST-1: 6 of 7 negatives FALSELY ATTESTED, 1 of 5 positives missed. ATTEST-1's 0 FP on corpus_v1 was a
development-set artifact: the corpus and the predicate were written together. Root cause: the object may occur
ANYWHERE after the trigger in the sentence, so the trigger and the object need not be in one clause.
These probes are now a DEVELOPMENT set for any later version and may not be quoted as a holdout rate."""
PROBES = [
    ("has_diet", "vegetarian", "I'm sure my wife is vegetarian.", False),
    ("health_state", "asthma", "I have a friend with asthma.", False),
    ("located_at", "Brisbane", "I live in Sydney, not far from my mate who moved to Brisbane.", False),
    ("works_as", "nurse", "I'm a big fan of the nurse on that show.", False),
    ("prefers", "tea", "I like that you remembered I prefer coffee over tea.", False),
    ("uses_tool", "Notion", "I use Obsidian because Notion is slow.", False),
    ("relative_of", "Maria", "My brother married Maria.", False),
    ("measures", "78 kg", "My weight is 78 kg.", True),
    ("located_at", "Brisbane", "Yes, I live in Brisbane now.", True),
    ("works_as", "nurse", "I'm a nurse.", True),
    ("health_state", "asthma", "I have had asthma since childhood.", True),
    ("has_pet", "cat", "I have a cat named Miso and she is not well.", True),
]
