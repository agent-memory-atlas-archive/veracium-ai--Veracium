"""Score a frozen ATTEST version on holdout H1. Usage: python score_h1.py attest_v2 [labels.json]
Without labels.json, gold is the H1 author's. With it ({"id","label"} list), gold is that labeller's."""
import importlib, json, sys


def _strict_pairs(pairs):
    """object_pairs_hook: refuse a duplicate key rather than keep the last (the product repo's evidence-boundary rule)."""
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"duplicate JSON key {k!r}")
        d[k] = v
    return d


A = importlib.import_module(sys.argv[1])
I = json.load(open("holdout_h1.json"), object_pairs_hook=_strict_pairs)
gold = {i["id"]: i["gold"] for i in I}
if len(sys.argv) > 2:
    gold = {x["id"]: x["label"] for x in json.load(open(sys.argv[2]), object_pairs_hook=_strict_pairs)}
c = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
for i in I:
    p = A.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED"; g = gold[i["id"]]
    c[("T" if p == g else "F") + ("P" if p else "N")] += 1
print(A.VERSION, "on H1, gold =", sys.argv[2] if len(sys.argv) > 2 else "author", c,
      f"recall {c['TP']}/{c['TP']+c['FN']}  false-attest {c['FP']}/{c['FP']+c['TN']}")
