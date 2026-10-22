"""Post-scoring diagnosis of H3 (NOT pre-registered; written after results_h3.txt): for the backstop's restricted items
and its 21 unrestricted other-speaker negatives, what the grammar saw (labels found, non-user turn or not) and whether
the object's tokens occur in any non-user turn. Read-only over the committed set."""
import json, sys
from veracium import attest_turns as A4
items = {i["id"]: i for i in json.load(open(sys.argv[1]))}
ids = sys.argv[2].split(",")
for k in ids:
    i = items[k]; t = i["text"]
    ts = A4.turns(t)
    labs = [(n, said) for _s, _e, n, said in A4._labels(t)]
    v = A4._side_tokens(i["object"])
    in_nu = any(A4._occurs(v, b) for sp, b in ts if sp == "non-user")
    print(f"{k} [{i['style']}] obj={i['object']!r} labels={labs} non-user-turn={any(sp=='non-user' for sp,_ in ts)} obj-in-non-user={in_nu} restricted={A4.only_in_non_user_turns('user', i['object'], t)}")
