# Does the product's 0013-PA1 campaign (part A) see a ladder write that maps to no STEP? Run on a tree (argv[1]).
import collections, importlib.util, json, os, sys, tempfile
T = os.path.realpath(sys.argv[1])
spec = importlib.util.spec_from_file_location("pa1", f"{T}/specs/evidence/0013/pa1_campaign.py")
m = importlib.util.module_from_spec(spec); sys.modules["pa1"] = m; spec.loader.exec_module(m)
import veracium; assert os.path.realpath(veracium.__file__).startswith(T), veracium.__file__
work = tempfile.mkdtemp(dir=sys.argv[2]); path = os.path.join(work, "a.db")
L = m.lib(); unmatched = collections.Counter(); outcomes = collections.Counter(); paths = 0
for label, _b, _a, _st in L["paths"]():
    m.fresh_fixture(path, label); r = m.run_case(path); paths += 1
    outcomes[str(r.get("outcome"))[:40] if r["exc"] is None else "EXC " + type(r["exc"]).__name__] += 1
    for w in r["writes"]:
        if w["kind"] != "DDL" and m.step_of(w) is None:
            unmatched[(w["kind"], w["sql"][:70], w["by"].split(":")[1])] += 1
print("tree", T); print("paths", paths, "outcomes", dict(outcomes))
print("non-DDL writes mapped to NO step:", sum(unmatched.values()), dict(unmatched))
cells = m.campaign_a(tempfile.mkdtemp(dir=sys.argv[2]))
ms = collections.Counter((c["path"], c["step"], c["mode"], c.get("outcome"), c.get("killed")) for c in cells)
bad = [c for c in cells if c.get("killed") is False]
print("part A cells", len(cells), "not killed", len(bad), "per step", dict(collections.Counter(c["step"] for c in cells)))
json.dump(sorted(map(list, ms.elements())), open(sys.argv[3], "w"))
