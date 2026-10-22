"""Research's ONE scoring of holdout H3 (pre-registered: committed before it ran). Usage:
    PYTHONPATH=<export>/src python score_h3.py <holdout_h3.json> <labels_h3_b.json>
The export holds veracium at 3914f73 plus dev's frozen attest_turns.py (ATTEST-4@ba09a2a1) beside attest_v3.py
(b1329a81); both digests are asserted. Reports, under three golds (the author's; the second labeller's; the 128 items
both agree on): ATTEST-3 and ATTEST-4 confusions, false-attestation counts with an exact one-sided 95% upper bound,
recall, every false attestation, every attestation ATTEST-4 removed; then §4b's backstop (only_in_non_user_turns)
against gold and the author's value_source, listing every gold-true item it restricts (a user fact lost) and every
gold-false item whose value only another speaker gave that it does NOT restrict (the leak class it exists for)."""
import hashlib, json, math, pathlib, sys
from veracium import attest_v3 as A3, attest_turns as A4

for mod, want in ((A3, "b1329a81c9c3c899a13fd4db94bd8ac3d52283a56321d466898696893942b5f1"),
                  (A4, "ba09a2a12ab193eb1110d02e8be5dd7a173898efa869da7efe556ba48b65dd00")):
    got = hashlib.sha256(pathlib.Path(mod.__file__).read_bytes()).hexdigest()
    assert got == want, (mod.__name__, got)

def strict(pairs):
    d = {}
    for k, v in pairs:
        if k in d: raise ValueError(k)
        d[k] = v
    return d

items = json.load(open(sys.argv[1]), object_pairs_hook=strict)
lab = {x["id"]: x for x in json.load(open(sys.argv[2]), object_pairs_hook=strict)}
assert len(items) == 130 and set(lab) == {i["id"] for i in items}

def upper95(k, n):
    """Exact (Clopper-Pearson) one-sided 95% upper bound on a rate with k events in n."""
    if n == 0: return float("nan")
    if k == n: return 1.0
    lo, hi = k / n, 1.0
    for _ in range(60):
        p = (lo + hi) / 2
        cdf = sum(math.comb(n, j) * p**j * (1 - p)**(n - j) for j in range(k + 1))
        lo, hi = (p, hi) if cdf > 0.05 else (lo, p)
    return hi

v3 = {i["id"]: A3.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED" for i in items}
v4 = {i["id"]: A4.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED" for i in items}
bs = {i["id"]: A4.only_in_non_user_turns("user", i["object"], i["text"]) for i in items}
nu = {i["id"]: A4.user_text(i["text"]) is not None for i in items}
by = {i["id"]: i for i in items}

golds = {"author": {i["id"]: i["gold"] for i in items},
         "labeller": {k: v["gold"] for k, v in lab.items()}}
golds["agreed-128"] = {k: g for k, g in golds["author"].items() if golds["labeller"][k] == g}

print(f"items {len(items)}; events in which ATTEST-4's grammar finds a non-user turn: {sum(nu.values())}")
for name, gold in golds.items():
    print(f"\n== gold: {name} ({len(gold)} items; {sum(gold.values())} true, {len(gold) - sum(gold.values())} false)")
    for ver, v in (("ATTEST-3", v3), ("ATTEST-4", v4)):
        tp = sum(1 for k, g in gold.items() if g and v[k]); fn = sum(1 for k, g in gold.items() if g and not v[k])
        fp = sum(1 for k, g in gold.items() if not g and v[k]); tn = sum(1 for k, g in gold.items() if not g and not v[k])
        print(f"  {ver}: TP {tp} FN {fn} FP {fp} TN {tn} | false attestations {fp}/{fp + tn} "
              f"(one-sided 95% upper bound {upper95(fp, fp + tn):.1%}) | recall {tp}/{tp + fn}")
        for k, g in gold.items():
            if not g and v[k]:
                print(f"    FALSE ATTESTATION {k} {by[k]['relation']} {by[k]['object']!r} [{by[k]['style']}]")
    removed = [k for k in gold if v3[k] and not v4[k]]
    print(f"  attestations ATTEST-4 removed: {len(removed)} -> " + ", ".join(f"{k}(gold {gold[k]})" for k in removed))

print("\n== §4b backstop (only_in_non_user_turns), against the author's gold and value_source")
from collections import Counter
c = Counter((by[k]["gold"], by[k]["value_source"], bs[k]) for k in by)
for key in sorted(c, key=str): print(f"  gold={key[0]!s:5} value_source={key[1]:7} restricted={key[2]!s:5}: {c[key]}")
print("  gold-TRUE items restricted (a user fact lost):",
      [k for k in by if by[k]["gold"] and bs[k]] or "none")
for gname in ("author", "labeller"):
    g = golds[gname]
    print(f"  gold-false (by {gname}) with the value from another speaker only, NOT restricted:",
          [f"{k}[{by[k]['style']}]" for k in by if not g[k] and by[k]["value_source"] == "other" and not bs[k]] or "none")
