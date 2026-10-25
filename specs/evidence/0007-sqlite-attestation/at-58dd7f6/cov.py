# Line coverage (sys.monitoring LINE) of every function ENTERED during the ladder: argv <tree> <scratch> [--campaign].
# Monitoring is on only inside pa1_campaign.run_case (the migration), over the unperturbed 48 paths, and with
# --campaign also over campaign_a's 1,480 perturbed runs. Reports, per entered function under src/veracium, the
# executable lines (co_lines of that code object only) never executed.
import collections, importlib.util, os, sys, tempfile
T = os.path.realpath(sys.argv[1]); SRC = os.path.join(T, "src", "veracium") + os.sep
spec = importlib.util.spec_from_file_location("pa1", f"{T}/specs/evidence/0013/pa1_campaign.py")
m = importlib.util.module_from_spec(spec); sys.modules["pa1"] = m; spec.loader.exec_module(m)
import veracium; assert os.path.realpath(veracium.__file__).startswith(T)
mon = sys.monitoring; TOOL = 3; mon.use_tool_id(TOOL, "cov")
hit = collections.defaultdict(set); codes = {}
def on_line(code, line):
    if code.co_filename.startswith(SRC):
        codes[id(code)] = code; hit[id(code)].add(line)
    return mon.DISABLE if not code.co_filename.startswith(SRC) else None
mon.register_callback(TOOL, mon.events.LINE, on_line)
orig = m.run_case
def run_case(*a, **kw):
    mon.set_events(TOOL, mon.events.LINE)
    try: return orig(*a, **kw)
    finally: mon.set_events(TOOL, 0)
m.run_case = run_case
work = tempfile.mkdtemp(dir=sys.argv[2]); path = os.path.join(work, "a.db"); L = m.lib()
for label, _b, _a, _st in L["paths"]():
    m.fresh_fixture(path, label); r = m.run_case(path); assert r["exc"] is None, (label, r["exc"])
if "--campaign" in sys.argv:
    mon.restart_events(); m.campaign_a(tempfile.mkdtemp(dir=sys.argv[2]))
tot_exec = tot_miss = 0; rows = []
for cid, code in codes.items():
    lines = {l for _, _, l in code.co_lines() if l is not None and l != code.co_firstlineno}
    miss = sorted(lines - hit[cid]); tot_exec += len(lines); tot_miss += len(miss)
    if miss: rows.append((code.co_filename[len(SRC):], code.co_qualname, code.co_firstlineno, len(lines), miss))
print(f"entered functions {len(codes)}; executable lines {tot_exec}; never executed {tot_miss}")
for f, q, fl, n, miss in sorted(rows):
    print(f"  {f}:{q}@{fl}  {len(miss)}/{n} missed: {miss}")
