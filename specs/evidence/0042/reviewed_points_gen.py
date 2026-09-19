"""GENERATE the REVIEWED set (specs/0042 Part A-0-bis) from the authored semantic review and the
derived inventory, so that every decision carries what a second reader needs to re-derive it
rather than re-read it (research, 2026-09-19): the candidate's stable key (module, qualname, kind,
ordinal), the line it sat at when generated, the STATEMENT TEXT at that line, and the decision —
a site id (enforcement) or a NOT class with its reason text.

Ordering, for the human reader: the enforcement decisions first (by site id), then the NOT
decisions GROUPED BY CLASS with their reasons — a wrong "not an enforcement point" is caught by
nothing downstream and is the reading that matters.

THE PREDICATE-HELPER REASON HAS A SUBJECT (research, 2026-09-19, second read of the NOT half): "the
consumer makes the decision" is true whether or not a consuming site exists, so the 43 rows shared one
sentence that could not be wrong. Now the generator DERIVES each helper's consumers from the source (every
function whose body references the helper's name — by name, stated as such) and writes them into the reason:
the consumers that carry a declared site, with the site ids; or the consumers that carry none ("no consuming
site"); or, for a helper no product function references, the reading the review states by hand in
`CONSUMED_OUTSIDE` (the `==` operator, a public API read by the host). A helper with neither a consumer nor
a stated reading REFUSES generation.

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
inv_by_key = {(x["module"], x["line"]): x for x in inv}


def _function_references(src_root):
    """module:qualname -> the names its body references (Name loads and Attribute attrs)."""
    import ast
    refs = {}
    for path in sorted(src_root.rglob("*.py")):
        module = str(path.relative_to(src_root)); tree = ast.parse(path.read_text())

        def visit(node, qual):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    visit(child, qual + [child.name])
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    q = qual + [child.name]; names = set()
                    for n in ast.walk(child):
                        if isinstance(n, ast.Name):
                            names.add(n.id)
                        elif isinstance(n, ast.Attribute):
                            names.add(n.attr)
                    refs[f"{module}:{'.'.join(q)}"] = names
                    visit(child, q)
                else:
                    visit(child, qual)
        visit(tree, [])
    return refs


REFS = _function_references(src_root)


def consumer_statement(helper, site_symbols, review):
    """The subject of a predicate-helper reason: who consumes the helper and whether that consumer is a site."""
    name = helper.split(":")[1].split(".")[-1]
    consumers = sorted(f for f, names in REFS.items() if name in names and f != helper and not f.startswith(helper + "."))
    with_site = [f for f in consumers if f in site_symbols]
    if with_site:
        return "consumed (by name) by " + "; ".join(f"{f} [site {', '.join(sorted(site_symbols[f]))}]" for f in with_site) + \
               (f"; and by {', '.join(f for f in consumers if f not in site_symbols)} (no site)" if len(with_site) < len(consumers) else "")
    if consumers:
        return "no consuming site — consumed (by name) by " + ", ".join(consumers)
    stated = getattr(review, "CONSUMED_OUTSIDE", {}).get(helper)
    if stated is None:
        raise SystemExit(f"REFUSED: predicate-helper {helper} has no consumer in src and no CONSUMED_OUTSIDE reading")
    return "no product consumer — " + stated
spec = importlib.util.spec_from_file_location("review", review_path); review = importlib.util.module_from_spec(spec); spec.loader.exec_module(review)


def candidate_id(site):                      # the evidence module's format, verbatim
    return f"{site['module']}:{site['qualname']}:{site['line']}:{site['kind']}"


ordinal = collections.Counter()
rows = {}
srcs = {}
site_symbols = {}
for (module, line), (sid, *_rest) in review.E.items():
    site_symbols.setdefault(f"{module}:{inv_by_key[(module, line)]['qualname']}", set()).add(sid)
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
        reason = review.REASON_TEXT[cls]
        if cls == "predicate-helper":
            reason += "; " + consumer_statement(f"{site['module']}:{site['qualname']}", site_symbols, review)
        rows[candidate_id(site)] = {"decision": "not", "reason": reason, "reviewer": "dev", "class": cls, **base}

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
