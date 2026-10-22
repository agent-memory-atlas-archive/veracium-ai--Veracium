"""Merge the two authors' arrays (raw/author_G.txt, raw/author_T.txt, extracted verbatim from their final messages by
extract_final.py) into holdout_h5.json and the gold-free h5_items_for_labelling.json. The order is a shuffle seeded by
the sha256 of the two raw files, so it is reproducible and chosen by neither research nor the authors.
Usage: python -I merge_h5.py <dir>"""
import hashlib, json, pathlib, random, sys

def strict(pairs):
    d = {}
    for k, v in pairs:
        if k in d: raise ValueError(k)
        d[k] = v
    return d

D = pathlib.Path(sys.argv[1])
raw = {s: (D / "raw" / f"author_{s}.txt").read_bytes() for s in ("G", "T")}
items = []
for s, b in raw.items():
    arr = json.loads(b, object_pairs_hook=strict)
    assert len(arr) == 65, (s, len(arr))
    for x in arr:
        assert set(x) == {"relation", "object", "text", "gold", "value_source", "style", "note"}, (s, sorted(x))
        assert isinstance(x["gold"], bool) and x["value_source"] in ("user", "other", "both", "neither")
        items.append({"stratum": s, **x})
seed = hashlib.sha256(raw["G"] + raw["T"]).hexdigest()
random.Random(seed).shuffle(items)
out = [{"id": f"h5-{k:03d}", **x} for k, x in enumerate(items, 1)]
(D / "holdout_h5.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
blind = [{k: x[k] for k in ("id", "relation", "object", "text")} for x in out]
(D / "h5_items_for_labelling.json").write_text(json.dumps(blind, ensure_ascii=False, indent=1) + "\n")
print("seed", seed[:16], "| items", len(out), "| true", sum(x["gold"] for x in out),
      "| by stratum", {s: sum(1 for x in out if x["stratum"] == s) for s in raw})
