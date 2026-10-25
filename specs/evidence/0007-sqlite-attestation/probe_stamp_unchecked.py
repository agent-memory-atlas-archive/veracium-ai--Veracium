"""Dev's step-table finding, checked independently (research, 2026-10-13): is the migration's final stamp
(`PRAGMA user_version = SCHEMA_VERSION`, migration.py `_apply_forward`) checked by anything before commit?
argv[1] = a tree's src dir (asserted on the import path), argv[2] = a scratch dir, argv[3] = a label.
Run it on an unmutated tree (control) and on a scratch copy whose ONE stamp line writes SCHEMA_VERSION - 1 (mutant).
A store is built from the head-1 constructor and stamped head-1; migrate_store runs; the outcome, the committed stamp
and the next ordinary open are reported."""
import pathlib, sqlite3, sys
TREE, TMP, LABEL = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]), sys.argv[3]
TMP.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(TREE))
import veracium
assert pathlib.Path(veracium.__file__).resolve().is_relative_to(TREE), veracium.__file__
from veracium.store import schema_version as sv, migration as mg
from veracium.store.sqlite import SqliteStore
HEAD = sv.SCHEMA_VERSION
path = TMP / f"{LABEL}.db"; path.unlink(missing_ok=True)
c = sqlite3.connect(path); sv.create(c, HEAD - 1); c.execute(f"PRAGMA user_version = {HEAD - 1}"); c.commit(); c.close()
try:
    r = mg.migrate_store(str(path)); print(f"{LABEL}: migrate_store returned outcome={getattr(r, 'outcome', r)!r}")
except Exception as exc:
    print(f"{LABEL}: migrate_store REFUSED {type(exc).__name__}: {getattr(exc, 'reason', '')}")
c = sqlite3.connect(path)
print(f"{LABEL}: committed user_version = {c.execute('PRAGMA user_version').fetchone()[0]} (head {HEAD}); "
      f"shape digest in accepted({HEAD}): {sv.digest(sv.manifest(c), HEAD) in sv.accepted_digests(HEAD)}")
c.close()
try:
    s = SqliteStore(str(path)); s.close(); print(f"{LABEL}: next ordinary open: OPENED")
except Exception as exc:
    print(f"{LABEL}: next ordinary open: REFUSED {type(exc).__name__}: {getattr(exc, 'reason', '')}")
