import importlib.util, os, sqlite3, sys, tempfile
T = os.path.realpath(sys.argv[1]); spec = importlib.util.spec_from_file_location("pa1", f"{T}/specs/evidence/0013/pa1_campaign.py")
m = importlib.util.module_from_spec(spec); sys.modules["pa1"] = m; spec.loader.exec_module(m)
p = os.path.join(tempfile.mkdtemp(dir=sys.argv[2]), "a.db")
for label in ("v15#0", "v9#0"):
    m.fresh_fixture(p, label); r = m.run_case(p)
    c = sqlite3.connect(p); n = c.execute("SELECT COUNT(*), SUM(json_extract(json,'$.planted')=1) FROM episodes").fetchone()
    print(label, "exc", r["exc"], "user_version", c.execute("PRAGMA user_version").fetchone()[0], "episodes, planted:", n); c.close()
