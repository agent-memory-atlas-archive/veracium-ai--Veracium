"""Research's ONE scoring of holdout H4, with H3 as ATTEST-5's regression set (pre-registered: committed before it ran).
    PYTHONPATH=<export>/src python score_h4.py <h4.json> <h4_labels.json> <h3.json> <h3_labels.json>
The export holds veracium at 3914f73 with dev's frozen files beside attest_v3.py (b1329a81): ATTEST-4's bytes as
attest_turns4.py (ba09a2a1) and ATTEST-5's as attest_turns5.py (0bb7779f); all three digests are asserted. Per holdout
and gold (the author's; the second labeller's; the items both agree on): each version's confusion, false attestations
with an exact one-sided 95% upper bound, recall, every false attestation, every attestation a version removed relative to
ATTEST-3; then §4b (only_in_non_user_turns) for ATTEST-4 and ATTEST-5: restricted items by gold and the author's
value_source, every gold-TRUE item restricted (a user fact lost), every gold-false item whose value only another speaker
gave that is NOT restricted."""
import hashlib, json, math, pathlib, sys
from collections import Counter
from veracium import attest_v3 as A3, attest_turns4 as A4, attest_turns5 as A5

for mod, want in ((A3, "b1329a81c9c3c899a13fd4db94bd8ac3d52283a56321d466898696893942b5f1"),
                  (A4, "ba09a2a12ab193eb1110d02e8be5dd7a173898efa869da7efe556ba48b65dd00"),
                  (A5, "0bb7779fd9f3a015da4d285fdf7f988813d2fdf74822bf7fc088aa4f6ae82150")):
    got = hashlib.sha256(pathlib.Path(mod.__file__).read_bytes()).hexdigest()
    assert got == want, (mod.__name__, got)

def strict(pairs):
    d = {}
    for k, v in pairs:
        if k in d: raise ValueError(k)
        d[k] = v
    return d

def upper95(k, n):
    if n == 0: return float("nan")
    if k == n: return 1.0
    lo, hi = k / n, 1.0
    for _ in range(60):
        p = (lo + hi) / 2
        cdf = sum(math.comb(n, j) * p**j * (1 - p)**(n - j) for j in range(k + 1))
        lo, hi = (p, hi) if cdf > 0.05 else (lo, p)
    return hi

VERS = (("ATTEST-3", A3), ("ATTEST-4@ba09a2a1", A4), ("ATTEST-5@0bb7779f", A5))

def run(tag, hpath, lpath):
    items = json.load(open(hpath), object_pairs_hook=strict)
    lab = {x["id"]: x for x in json.load(open(lpath), object_pairs_hook=strict)}
    assert set(lab) == {i["id"] for i in items}
    by = {i["id"]: i for i in items}
    v = {name: {i["id"]: m.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED" for i in items}
         for name, m in VERS}
    golds = {"author": {i["id"]: i["gold"] for i in items}, "labeller": {k: x["gold"] for k, x in lab.items()}}
    golds["agreed"] = {k: g for k, g in golds["author"].items() if golds["labeller"][k] == g}
    print(f"\n######## {tag}: {len(items)} items; non-user turn found by ATTEST-4 in "
          f"{sum(A4.user_text(i['text']) is not None for i in items)}, by ATTEST-5 in "
          f"{sum(A5.user_text(i['text']) is not None for i in items)}")
    for gname, gold in golds.items():
        print(f"\n== {tag} gold: {gname} ({len(gold)} items; {sum(gold.values())} true)")
        for name, _m in VERS:
            tp = sum(1 for k, g in gold.items() if g and v[name][k]); fn = sum(1 for k, g in gold.items() if g and not v[name][k])
            fp = sum(1 for k, g in gold.items() if not g and v[name][k]); tn = sum(1 for k, g in gold.items() if not g and not v[name][k])
            print(f"  {name}: TP {tp} FN {fn} FP {fp} TN {tn} | false attestations {fp}/{fp + tn} "
                  f"(one-sided 95% upper bound {upper95(fp, fp + tn):.1%}) | recall {tp}/{tp + fn}")
            for k, g in gold.items():
                if not g and v[name][k]:
                    print(f"    FALSE ATTESTATION {k} {by[k]['relation']} {by[k]['object']!r} [{by[k]['style']}]")
            if name != "ATTEST-3":
                rem = [k for k in gold if v["ATTEST-3"][k] and not v[name][k]]
                print(f"    removed vs ATTEST-3: {len(rem)} -> " + ", ".join(f"{k}(gold {gold[k]})" for k in rem))
    for name, m in VERS[1:]:
        bs = {k: m.only_in_non_user_turns("user", by[k]["object"], by[k]["text"]) for k in by}
        print(f"\n== {tag} §4b under {name} (author's gold and value_source)")
        c = Counter((by[k]["gold"], by[k]["value_source"], bs[k]) for k in by)
        for key in sorted(c, key=str): print(f"  gold={key[0]!s:5} value_source={key[1]:7} restricted={key[2]!s:5}: {c[key]}")
        for gname in ("author", "labeller"):
            g = golds[gname]
            print(f"  gold-TRUE (by {gname}) restricted (a user fact lost):", [k for k in by if g[k] and bs[k]] or "none")
            print(f"  gold-false (by {gname}), value only from another speaker, NOT restricted:",
                  [f"{k}[{by[k]['style']}]" for k in by if not g[k] and by[k]["value_source"] == "other" and not bs[k]] or "none")

run("H4 (holdout)", sys.argv[1], sys.argv[2])
run("H3 (regression)", sys.argv[3], sys.argv[4])
