"""Run ATTEST over the corpus and report the confusion, overall and per category, with the predicate version.

Usage: python run_attest.py            (from this directory)
UNSUPPORTED counts as NOT attested (the safe branch) and is reported separately.
"""
import collections
import json
import sys

import attest_v1 as A
from corpus_v1 import ITEMS

rows = []
for (iid, rel, obj, text, gold, cat) in ITEMS:
    got = A.attests("user", rel, obj, text)
    rows.append({"id": iid, "relation": rel, "category": cat, "gold": gold, "result": got,
                 "predicted": got == "ATTESTED"})

tp = sum(r["gold"] and r["predicted"] for r in rows)
fp = sum((not r["gold"]) and r["predicted"] for r in rows)
fn = sum(r["gold"] and not r["predicted"] for r in rows)
tn = sum((not r["gold"]) and not r["predicted"] for r in rows)
by = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    by[r["category"]]["n"] += 1
    by[r["category"]]["wrong"] += r["gold"] != r["predicted"]

print(f"predicate {A.VERSION}; corpus items {len(rows)}; author-labelled (second labelling PENDING)")
print(f"TP {tp}  FP {fp}  FN {fn}  TN {tn}   unsupported {sum(r['result']=='UNSUPPORTED' for r in rows)}")
for c in sorted(by):
    print(f"  {c:28s} n={by[c]['n']:2d} wrong={by[c]['wrong']}")
for r in rows:
    if r["gold"] != r["predicted"]:
        print("  MISS", json.dumps(r))
sys.exit(0)
