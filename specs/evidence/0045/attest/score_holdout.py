"""Score a frozen ATTEST version on a holdout. Usage: python score_holdout.py <attest module> <holdout.json> [labels.json]
Without labels.json, gold is the holdout author's. With it ({"id","label"} list), gold is that labeller's. Prints the
confusion and every miss, so a reader can check each one by hand (UNSUPPORTED counts as not attested)."""
import importlib
import json
import sys


def _strict_pairs(pairs):
    """object_pairs_hook: refuse a duplicate key rather than keep the last (the product repo's evidence-boundary rule)."""
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"duplicate JSON key {k!r}")
        d[k] = v
    return d


A = importlib.import_module(sys.argv[1])
items = json.load(open(sys.argv[2]), object_pairs_hook=_strict_pairs)
gold = {i["id"]: i["gold"] for i in items}
if len(sys.argv) > 3:
    gold = {x["id"]: x["label"] for x in json.load(open(sys.argv[3]), object_pairs_hook=_strict_pairs)}
c = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
miss = []
for i in items:
    p = A.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED"
    g = gold[i["id"]]
    c[("T" if p == g else "F") + ("P" if p else "N")] += 1
    if p != g:
        miss.append(("FALSE ATTESTATION" if p else "missed") + f" {i['id']} {i['relation']} {i['object']!r} | {i['text']}")
print(A.VERSION, "on", sys.argv[2], "gold =", sys.argv[3] if len(sys.argv) > 3 else "author", c,
      f"recall {c['TP']}/{c['TP'] + c['FN']}  false-attest {c['FP']}/{c['FP'] + c['TN']}")
print("\n".join(miss))
