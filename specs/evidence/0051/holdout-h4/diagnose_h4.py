"""Post-scoring diagnosis of H4 (NOT pre-registered; written after results_h4.txt). For the true attestations ATTEST-5
removed and the gold-true items §4b restricted: ATTEST-3 over the raw text and over ATTEST-5's user text, the object's
tokens, and whether they occur in the user text and in the non-user turns."""
import json, sys
from veracium import attest_v3 as A3, attest_turns5 as A5
items = {i["id"]: i for i in json.load(open(sys.argv[1]))}
for k in sys.argv[2].split(","):
    i = items[k]; t = i["text"]; u = A5.user_text(t) or ""
    v = A5._side_tokens(i["object"])
    print(f"{k} {i['relation']} {i['object']!r}: raw={A3.attests('user', i['relation'], i['object'], t)} "
          f"user-text={A3.attests('user', i['relation'], i['object'], u)} tokens={v} "
          f"in-user={A5._occurs(v, u)} in-non-user={any(A5._occurs(v, b) for sp, b in A5.turns(t) if sp == 'non-user')} "
          f"user-tokens-near={[x for x in A5._tokens(u) if x.startswith(v[0][:4])][:4]}")
