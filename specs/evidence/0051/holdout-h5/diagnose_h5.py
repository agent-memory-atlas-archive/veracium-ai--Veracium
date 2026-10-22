"""POST-SCORING diagnosis of H5 (written after results_h5.txt was produced; it grades nothing). For the two items whose
outcome ATTEST-6 changed (h5-112's verdict, h5-048's backstop): ATTEST-3 over the raw text and over each version's user
text, each version's turns, and the backstop under each. Then INV-S8 on H5 under ATTEST-6: no item both restricted
by the backstop and attested. Same environment as score_h5.py.
Usage: PYTHONPATH=<export>/src python diagnose_h5.py <h5.json>"""
import json, sys
from veracium import attest_v3 as A3, attest_turns as A5, attest_turns6 as A6, speaker_backstop as SB

items = {i["id"]: i for i in json.load(open(sys.argv[1]))}


def restricts(m, obj, text):
    SB.turns = m.turns
    try:
        return SB.speaker_restricts("user", obj, text)
    finally:
        SB.turns = A5.turns


for k in ("h5-112", "h5-048"):
    i = items[k]
    print(f"== {k} [{i['stratum']}] {i['relation']} {i['object']!r} gold={i['gold']} value_source={i['value_source']}")
    print("  ATTEST-3 over the raw text:", A3.attests("user", i["relation"], i["object"], i["text"]))
    for name, m in (("ATTEST-5", A5), ("ATTEST-6", A6)):
        u = m.user_text(i["text"])
        print(f"  {name}: classes {m._classify(m._labels(i['text']))}")
        print(f"    user text: {u!r}")
        print(f"    ATTEST-3 over it: {A3.attests('user', i['relation'], i['object'], u) if u is not None else '(no user text)'}"
              f" | verdict {m.attests('user', i['relation'], i['object'], i['text'])}"
              f" | backstop restricts {restricts(m, i['object'], i['text'])}")
both = [k for k, i in items.items() if A6.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED"
        and restricts(A6, i["object"], i["text"])]
print(f"\nINV-S8 on H5 under ATTEST-6 (restricted AND attested): {len(both)} of {len(items)}" + (f" -> {both}" if both else ""))
