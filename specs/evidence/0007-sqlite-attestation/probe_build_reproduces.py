"""S-Q7 relaxation, the design's crux (research, 2026-10-13): on THIS interpreter's SQLite build, does the store's own
constructor reproduce what the packaged evidence accepts? And does the gate refuse an EXISTING store too, not only a new
one? argv[1] = a tree's src dir (asserted on the import path), argv[2] = a scratch dir, argv[3] = "create" or "open".

  create: build a store at <scratch>/s.db with this interpreter (expected: the qualified build).
  open:   report this build's identity and, per schema version, whether the on-the-fly constructor digest is in the
          accepted set and whether the complete manifestation equals the qualified record's; then open the store
          made by `create` and report the outcome.
Run with dev's .venv site-packages appended to sys.path (same CPython ABI), never by installing anything."""
import json, pathlib, sqlite3, sys
TREE, TMP, MODE = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]), sys.argv[3]
TMP.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(TREE))
import veracium
assert pathlib.Path(veracium.__file__).resolve().is_relative_to(TREE), veracium.__file__
from veracium.store import schema_version as sv

c = sqlite3.connect(":memory:")
print(f"python {sys.version.split()[0]} | sqlite {sqlite3.sqlite_version} | source_id …{c.execute('select sqlite_source_id()').fetchone()[0][-24:]}")
if MODE == "create":
    from veracium.store.sqlite import SqliteStore
    s = SqliteStore(str(TMP / "s.db")); s.close()
    print("created", TMP / "s.db", "| runtime_supported:", sv.runtime_supported())
    sys.exit(0)

me = sv.runtime_identity()
print("features:", json.dumps(me.get("features"), sort_keys=True))
print("runtime_supported():", sv.runtime_supported())
rec = sv.qualified_runtimes()[0]
print("qualified record: sqlite", rec["sqlite_version"], "| features", json.dumps(rec["features"], sort_keys=True),
      "| features equal here:", rec["features"] == me.get("features"))
same_d = same_m = 0
for v in sorted(sv.SCHEMAS):
    d = sv._constructor_digest(v)
    in_acc = d in sv.accepted_digests(v)
    eq_rec = d == rec["constructor_digests"].get(str(v))
    m_eq = rec["manifestations"].get(f"constructor v{v}") == sv._constructor_objects(v)
    same_d += in_acc; same_m += m_eq
    if not (in_acc and eq_rec and m_eq):
        print(f"  v{v}: digest in accepted {in_acc}, == record {eq_rec}, complete manifestation == record {m_eq}")
print(f"schema versions {len(sv.SCHEMAS)}: constructor digest in the accepted set on {same_d}; complete manifestation "
      f"equal to the qualified record on {same_m}")
from veracium.store.sqlite import SqliteStore
for label, path in (("EXISTING store made on the qualified build", TMP / "s.db"), ("NEW store", TMP / "new.db")):
    try:
        s = SqliteStore(str(path)); s.close(); print(f"open {label}: OPENED")
    except Exception as exc:
        print(f"open {label}: REFUSED {type(exc).__name__}: {getattr(exc, 'reason', '')} | {str(exc)[:160]}")
