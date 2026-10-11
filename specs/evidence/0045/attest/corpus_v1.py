"""The ATTEST corpus, v1 (0045 round 2, R1-01's closure evidence). Research, 2026-10-11.

Hand-written minimal pairs. GOLD answers one question, independent of any predicate's rules:
  "Did the speaker, in this text, state this triple about THEMSELF, affirmatively, as a CURRENT fact?"
Categories name the construction each item exercises. This corpus is labelled by its author; a second INDEPENDENT
labelling is required before any rate is quoted (the reviewer's R1-01 and this project's inter-rater rule).
Do not tune ATTEST to this file and then report its rate: a new version is measured against a FRESH holdout.
"""

# (id, relation, object, text, gold, category)
ITEMS = [
    # works_as
    ("wa01", "works_as", "dental technician", "I work as a dental technician.", True, "positive"),
    ("wa02", "works_as", "dental technician", "I do not work as a dental technician.", False, "negation"),
    ("wa03", "works_as", "dental technician", "If I work as a dental technician, I will move.", False, "conditional"),
    ("wa04", "works_as", "dental technician", "Dana works as a dental technician; I work as a nurse.", False, "other_speaker"),
    ("wa05", "works_as", "nurse", "Dana works as a dental technician; I work as a nurse.", True, "positive_compound"),
    ("wa06", "works_as", "dental technician", "I used to work as a dental technician.", False, "past_habit"),
    ("wa07", "works_as", "dental technician", "My mum said \"I work as a dental technician\" at dinner.", False, "quoted"),
    ("wa08", "works_as", "dentist", "I fix people's teeth for a living.", False, "uninvited_inference"),
    ("wa09", "works_as", "Night Auditor", "i'm a night auditor at the Grand.", True, "normalization_case"),
    ("wa10", "works_as", "dental technician", "Do I work as a dental technician?", False, "question"),
    ("wa11", "works_as", "dental technician", "I might work as a dental technician next year.", False, "modality"),
    # measures
    ("me01", "measures", "78 kg", "I weigh 78 kg.", True, "positive"),
    ("me02", "measures", "78 kg", "I weigh 78kg these days.", True, "normalization_units"),
    ("me03", "measures", "78 kg", "I don't weigh 78 kg anymore.", False, "negation"),
    ("me04", "measures", "78 kg", "I would weigh 78 kg if I stopped running.", False, "conditional"),
    ("me05", "measures", "78 kg", "My brother weighs 78 kg.", False, "other_speaker"),
    ("me06", "measures", "4200", "I've saved 4200 so far.", True, "positive"),
    ("me07", "measures", "4200", "I hope to have saved 4200 by June.", False, "modality"),
    ("me08", "measures", "78 kg", "The scale said 78 kg this morning.", False, "uninvited_inference"),
    # prefers
    ("pr01", "prefers", "oat milk", "I prefer oat milk.", True, "positive"),
    ("pr02", "prefers", "oat milk", "I don't prefer oat milk.", False, "negation"),
    ("pr03", "prefers", "oat milk", "My partner prefers oat milk.", False, "other_speaker"),
    ("pr04", "prefers", "window seats", "I'd rather have window seats on long flights.", True, "positive"),
    ("pr05", "prefers", "oat milk", "Would I prefer oat milk?", False, "question"),
    ("pr06", "prefers", "oat milk", "I keep ordering oat lattes, so I guess oat milk is my thing.", False, "uninvited_inference"),
    ("pr07", "prefers", "oat milk", "I used to like oat milk.", False, "past_habit"),
    # located_at
    ("lo01", "located_at", "Brisbane", "I live in Brisbane.", True, "positive"),
    ("lo02", "located_at", "Brisbane", "I don't live in Brisbane.", False, "negation"),
    ("lo03", "located_at", "Brisbane", "I'm thinking about moving to Brisbane.", False, "modality"),
    ("lo04", "located_at", "Brisbane", "My sister lives in Brisbane.", False, "other_speaker"),
    ("lo05", "located_at", "Brisbane", "I took the ferry home to my flat by the Story Bridge.", False, "uninvited_inference"),
    ("lo06", "located_at", "Brisbane", "Next year I will live in Brisbane.", False, "modality"),
    # health_state
    ("hs01", "health_state", "asthma", "I have asthma.", True, "positive"),
    ("hs02", "health_state", "asthma", "I don't have asthma.", False, "negation"),
    ("hs03", "health_state", "asthma", "My son has asthma.", False, "other_speaker"),
    ("hs04", "health_state", "asthma", "I've been diagnosed with asthma.", True, "positive"),
    ("hs05", "health_state", "asthma", "The doctor thinks I might have asthma.", False, "modality"),
    ("hs06", "health_state", "asthma", "I carry an inhaler everywhere.", False, "uninvited_inference"),
    ("hs07", "health_state", "iron deficiency", "I was diagnosed with iron deficiency last month.", True, "positive"),
    # has_pet
    ("hp01", "has_pet", "cat", "I have a cat.", True, "positive"),
    ("hp02", "has_pet", "cat", "I don't have a cat.", False, "negation"),
    ("hp03", "has_pet", "cat", "My neighbour has a cat.", False, "other_speaker"),
    ("hp04", "has_pet", "cat", "I buy cat litter every week.", False, "uninvited_inference"),
    # has_diet
    ("hd01", "has_diet", "vegetarian", "I'm vegetarian.", True, "positive"),
    ("hd02", "has_diet", "vegetarian", "I'm not vegetarian.", False, "negation"),
    ("hd03", "has_diet", "vegetarian", "I'm thinking about going vegetarian.", False, "modality"),
    ("hd04", "has_diet", "vegetarian", "I always order the lentil curry.", False, "uninvited_inference"),
    # partner_of
    ("po01", "partner_of", "Sam", "My partner Sam is visiting.", True, "positive"),
    ("po02", "partner_of", "Sam", "Sam is not my partner.", False, "negation"),
    ("po03", "partner_of", "Sam", "Dana's partner Sam is visiting.", False, "other_speaker"),
    ("po04", "partner_of", "Sam", "Sam and I share a flat and a dog.", False, "uninvited_inference"),
    # relative_of
    ("ro01", "relative_of", "Maria", "My sister Maria lives nearby.", True, "positive"),
    ("ro02", "relative_of", "Maria", "Maria is not my sister.", False, "negation"),
    ("ro03", "relative_of", "Maria", "Tim's sister Maria lives nearby.", False, "other_speaker"),
    # works_on
    ("wo01", "works_on", "the billing migration", "I'm working on the billing migration.", True, "positive"),
    ("wo02", "works_on", "the billing migration", "I'm not working on the billing migration.", False, "negation"),
    ("wo03", "works_on", "the billing migration", "I might work on the billing migration.", False, "modality"),
    # uses_tool
    ("ut01", "uses_tool", "Notion", "I use Notion for notes.", True, "positive"),
    ("ut02", "uses_tool", "Notion", "I don't use Notion.", False, "negation"),
    ("ut03", "uses_tool", "Notion", "My team uses Notion.", False, "other_speaker"),
    ("ut04", "uses_tool", "Notion", "Should I use Notion?", False, "question"),
    # avoids_tool
    ("at01", "avoids_tool", "Jira", "I avoid Jira whenever I can.", True, "positive"),
    ("at02", "avoids_tool", "Jira", "I don't use Jira.", True, "positive_negative_trigger"),
    ("at03", "avoids_tool", "Jira", "My manager avoids Jira.", False, "other_speaker"),
    # unsupported relations (the grammar does not cover them; gold may be True)
    ("un01", "source_reliable", "the ABS census tables", "The ABS census tables were reliable for this.", True, "unsupported"),
    ("un02", "deadline", "the grant report", "The grant report is due on 2026-11-01.", True, "unsupported"),
    # empty and degenerate
    ("eg01", "works_as", "nurse", "", False, "empty"),
    ("eg02", "works_as", "nurse", "I work as a", False, "truncated"),
]
