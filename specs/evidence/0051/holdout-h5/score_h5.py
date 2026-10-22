"""Research's ONE scoring of holdout H5, with H3 and H4 as ATTEST-6's regression sets (pre-registered: committed before
it ran).
    PYTHONPATH=<export>/src python score_h5.py <h5.json> <h5_labels.json> <h4.json> <h4_labels.json> <h3.json> <h3_labels.json>
The export holds veracium at 07df8f8, where `attest_turns.py` is ATTEST-5 (0bb7779f), with ATTEST-6's frozen bytes
beside it as `attest_turns6.py` (ccabb664) and attest_v3.py (b1329a81); all three digests are asserted. The product
backstop (`speaker_backstop.speaker_restricts`) takes its turns from the frozen file's `turns` and nothing else from
it, so it is scored under each version by rebinding that one name. Per holdout, stratum and gold (the author's; the
second labeller's; the items both agree on): each version's confusion, false attestations with an exact one-sided 95%
upper bound, recall, every false attestation; every item ATTEST-5 and ATTEST-6 answer differently; the backstop under
each version; and the product outcome that RII-02 broke, a gold-false item both attested and NOT restricted (stored
attested and mentionable). The three pre-registered predictions (README, step 0) are checked at the end."""
import hashlib, json, math, pathlib, sys
from collections import Counter
from veracium import attest_v3 as A3, attest_turns as A5, attest_turns6 as A6, speaker_backstop as SB

for mod, want in ((A3, "b1329a81c9c3c899a13fd4db94bd8ac3d52283a56321d466898696893942b5f1"),
                  (A5, "0bb7779fd9f3a015da4d285fdf7f988813d2fdf74822bf7fc088aa4f6ae82150"),
                  (A6, "ccabb664bbf1567a6d45bae6c64c7dbf08ff0c3a319f69bf83d9642700b1cba7")):
    got = hashlib.sha256(pathlib.Path(mod.__file__).read_bytes()).hexdigest()
    assert got == want, (mod.__name__, got)
assert SB.turns is A5.turns          # the backstop's one dependency, rebound per version below


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


VERS = (("ATTEST-3", A3), ("ATTEST-5@0bb7779f", A5), ("ATTEST-6@ccabb664", A6))


def restricts(turn_mod, obj, text):
    SB.turns = turn_mod.turns
    try:
        return SB.speaker_restricts("user", obj, text)
    finally:
        SB.turns = A5.turns


def counted_letters(text):
    names = {l[2] for l in A6._labels(text)}
    return bool({"h", "q"} & names and "a" in names)


def run(tag, hpath, lpath):
    items = json.load(open(hpath), object_pairs_hook=strict)
    lab = {x["id"]: x for x in json.load(open(lpath), object_pairs_hook=strict)}
    assert set(lab) == {i["id"] for i in items}
    by = {i["id"]: i for i in items}
    v = {name: {k: m.attests("user", i["relation"], i["object"], i["text"]) == "ATTESTED" for k, i in by.items()}
         for name, m in VERS}
    bs = {name: {k: restricts(m, i["object"], i["text"]) for k, i in by.items()} for name, m in VERS[1:]}
    strata = sorted({i.get("stratum", "-") for i in items})
    out = {"diff56": [k for k in by if v["ATTEST-5@0bb7779f"][k] != v["ATTEST-6@ccabb664"][k]]}
    print(f"\n######## {tag}: {len(items)} items; counted letters in {sum(counted_letters(i['text']) for i in items)}; "
          f"classes differ (ATTEST-5 vs 6) in "
          f"{sum(A5._classify(A5._labels(i['text'])) != A6._classify(A6._labels(i['text'])) for i in items)}; "
          f"turns differ in {sum(A5.turns(i['text']) != A6.turns(i['text']) for i in items)}")
    golds = {"author": {k: i["gold"] for k, i in by.items()}, "labeller": {k: x["gold"] for k, x in lab.items()}}
    golds["agreed"] = {k: g for k, g in golds["author"].items() if golds["labeller"][k] == g}
    print(f"  gold agreement author/labeller: {len(golds['agreed'])}/{len(by)}; disagreeing: "
          + (", ".join(k for k in by if k not in golds["agreed"]) or "none"))
    for stratum in strata + (["all"] if len(strata) > 1 else []):
        ids = [k for k in by if stratum == "all" or by[k].get("stratum", "-") == stratum]
        for gname, gold in golds.items():
            g = {k: gold[k] for k in ids if k in gold}
            print(f"\n== {tag} stratum {stratum}, gold: {gname} ({len(g)} items; {sum(g.values())} true)")
            for name, _m in VERS:
                tp = sum(1 for k, x in g.items() if x and v[name][k]); fn = sum(1 for k, x in g.items() if x and not v[name][k])
                fp = sum(1 for k, x in g.items() if not x and v[name][k]); tn = sum(1 for k, x in g.items() if not x and not v[name][k])
                print(f"  {name}: TP {tp} FN {fn} FP {fp} TN {tn} | false attestations {fp}/{fp + tn} "
                      f"(one-sided 95% upper bound {upper95(fp, fp + tn):.1%}) | recall {tp}/{tp + fn}")
                for k, x in g.items():
                    if not x and v[name][k]:
                        print(f"    FALSE ATTESTATION {k} {by[k]['relation']} {by[k]['object']!r} [{by[k]['style']}]")
                if name != "ATTEST-3":
                    mention = [k for k, x in g.items() if not x and v[name][k] and not bs[name][k]]
                    print(f"    gold-false stored attested AND mentionable (not restricted): {len(mention)}"
                          + (" -> " + ", ".join(mention) if mention else ""))
                    out.setdefault("fp", {})[(stratum, gname, name)] = fp
    print(f"\n== {tag}: every item ATTEST-5 and ATTEST-6 answer differently: {len(out['diff56'])}")
    for k in out["diff56"]:
        print(f"  {k} [{by[k].get('stratum', '-')}] gold author={by[k]['gold']} labeller={lab[k]['gold']} "
              f"ATTEST-5={v['ATTEST-5@0bb7779f'][k]} ATTEST-6={v['ATTEST-6@ccabb664'][k]} {by[k]['relation']} "
              f"{by[k]['object']!r}")
    for name in bs:
        print(f"\n== {tag} backstop under {name} (author's gold and value_source)")
        c = Counter((by[k]["gold"], by[k]["value_source"], bs[name][k]) for k in by)
        for key in sorted(c, key=str): print(f"  gold={key[0]!s:5} value_source={key[1]:7} restricted={key[2]!s:5}: {c[key]}")
        for gname in ("author", "labeller"):
            g = golds[gname]
            print(f"  gold-TRUE (by {gname}) restricted (a user fact lost):", [k for k in by if g[k] and bs[name][k]] or "none")
    return out


h5 = run("H5 (holdout)", sys.argv[1], sys.argv[2])
h4 = run("H4 (regression)", sys.argv[3], sys.argv[4])
h3 = run("H3 (regression)", sys.argv[5], sys.argv[6])

print("\n######## the pre-registered predictions (README, step 0)")
print(f"  P1 H3 and H4 identical under ATTEST-5 and ATTEST-6: {'HOLDS' if not h3['diff56'] and not h4['diff56'] else 'FAILS'}"
      f" (differing items: H3 {len(h3['diff56'])}, H4 {len(h4['diff56'])})")
g_diff = [k for k in h5["diff56"] if k in {i["id"] for i in json.load(open(sys.argv[1])) if i["stratum"] == "G"}]
print(f"  P2 on H5-G, ATTEST-6 equals ATTEST-5 on almost every item: {len(g_diff)} of 65 differ (reported, not graded)")
for gname in ("author", "labeller", "agreed"):
    f5, f6 = h5["fp"][("T", gname, "ATTEST-5@0bb7779f")], h5["fp"][("T", gname, "ATTEST-6@ccabb664")]
    print(f"  P3 on H5-T, gold {gname}: false attestations ATTEST-6 {f6} <= ATTEST-5 {f5}: {'HOLDS' if f6 <= f5 else 'FAILS'}")
