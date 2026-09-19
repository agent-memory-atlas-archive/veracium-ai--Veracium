"""GENERATE the REVIEWED set (specs/0042 Part A-0-bis) from the authored semantic review and the
derived inventory, so that every decision carries what a second reader needs to re-derive it
rather than re-read it (research, 2026-09-19): the candidate's stable key (module, qualname, kind,
ordinal), the line it sat at when generated, the STATEMENT TEXT at that line, and the decision —
a site id (enforcement) or a NOT class with its reason text.

Ordering, for the human reader: the enforcement decisions first (by site id), then the NOT
decisions GROUPED BY CLASS with their reasons — a wrong "not an enforcement point" is caught by
nothing downstream and is the reading that matters.

Usage: reviewed_points_gen.py <src/veracium> <inventory OUTPUT.json> <semantic_review.py> <out.json>
"""
import importlib.util, json, pathlib, sys, collections


def _strict_pairs(pairs):
    """0026's evidence-boundary rule: a duplicate key is a REFUSAL, never last-wins."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out

src_root, inv_path, review_path, out_path = (pathlib.Path(a) for a in sys.argv[1:5])
inv = json.load(open(inv_path), object_pairs_hook=_strict_pairs)["sites"]
spec = importlib.util.spec_from_file_location("review", review_path); review = importlib.util.module_from_spec(spec); spec.loader.exec_module(review)


def candidate_id(site):                      # the evidence module's format, verbatim
    return f"{site['module']}:{site['qualname']}:{site['line']}:{site['kind']}"


ordinal = collections.Counter()
rows = {}
srcs = {}
for site in sorted(inv, key=lambda s: (s["module"], s["line"])):
    g = (site["module"], site["qualname"], site["kind"]); ordinal[g] += 1
    key = (site["module"], site["line"])
    lines = srcs.setdefault(site["module"], (src_root / site["module"]).read_text().split("\n"))
    stmt = lines[site["line"] - 1].strip()
    base = {"key": f"{site['module']}:{site['qualname']}:{site['kind']}:{ordinal[g]}", "line": site["line"], "statement": stmt}
    if key in review.E:
        sid, spec_, inv_, label = review.E[key]
        rows[candidate_id(site)] = {"decision": "enforcement", "reason": f"enforces {spec_} {inv_} ({label}) through site {sid}",
                                    "reviewer": "dev", "site": sid, "class": "enforcement", **base}
    else:
        cls = review.OVERRIDE.get(key, review.DEFAULT.get(site["module"]))
        assert cls is not None, f"no NOT class for {candidate_id(site)} — the module has no default"
        rows[candidate_id(site)] = {"decision": "not", "reason": review.REASON_TEXT[cls], "reviewer": "dev", "class": cls, **base}

order = ["enforcement"] + sorted({r["class"] for r in rows.values() if r["class"] != "enforcement"})
out = {}
for cls in order:
    for cid, r in sorted(rows.items(), key=lambda kv: (kv[1].get("site", ""), kv[0])):
        if r["class"] == cls:
            out[cid] = r
assert len(out) == len(inv) == len(rows)
pathlib.Path(out_path).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
by_cls = collections.Counter(r["class"] for r in out.values())
print(f"reviewed_points.json: {len(out)} decisions over {len(inv)} candidates | enforcement {by_cls['enforcement']} ({len({r['site'] for r in out.values() if r['class']=='enforcement'})} ids) | " + " ".join(f"{c} {n}" for c, n in sorted(by_cls.items()) if c != "enforcement"))
