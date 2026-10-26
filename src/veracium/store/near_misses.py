"""The packaged near-misses of `0007` §4g.6 4b, step 3 (discrimination).

Reproduction proves a SQLite build gives the RIGHT answer on the right schema. It does not prove the build still gives
a DIFFERENT answer on a wrong one, which is the failure `0007` §7 exists to prevent ("opening and silently
misreading"). So each near-miss is the HEAD constructor with ONE change, built in memory, and on every build that opens
a store it must produce a digest or a complete manifestation different from the accepted head manifestation (INV-SA4).

They live here, in the package, not in `tests/`, so the check runs on users' machines. Each edit is an exact text
replacement in one head constructor whose anchor must occur EXACTLY ONCE (or a drop of one object), so a head schema
change that moves an anchor refuses loudly instead of silently building the head itself. The six kinds §4b requires
are each present; `tests/test_store_versioning.py` asserts the set and that each member differs on the running build.
"""
from __future__ import annotations

from typing import NamedTuple, Optional


class NearMiss(NamedTuple):
    name: str
    kind: str                      # one of REQUIRED_KINDS
    target: tuple                  # the head object's key, (kind, name)
    anchor: Optional[str]          # None: the object is dropped
    replacement: Optional[str]


REQUIRED_KINDS = ("added-column", "changed-type", "dropped-rebuildable-index", "changed-index-column",
                  "changed-default", "reordered-column")

NEAR_MISSES = (
    NearMiss("episodes-added-column", "added-column", ("table", "episodes"),
             "json TEXT NOT NULL\n)", "json TEXT NOT NULL, near_miss TEXT\n)"),
    NearMiss("episodes-date-integer", "changed-type", ("table", "episodes"), "date TEXT,", "date INTEGER,"),
    NearMiss("ix-episodes-user-dropped", "dropped-rebuildable-index", ("index", "ix_episodes_user"), None, None),
    NearMiss("ix-episodes-user-one-column", "changed-index-column", ("index", "ix_episodes_user"),
             "ON episodes(user_id, date)", "ON episodes(user_id)"),
    NearMiss("redactions-state-default", "changed-default", ("table", "redactions"),
             "DEFAULT 'applied'", "DEFAULT 'standing'"),
    NearMiss("episodes-columns-reordered", "reordered-column", ("table", "episodes"),
             "user_id TEXT NOT NULL, date TEXT,", "date TEXT, user_id TEXT NOT NULL,"),
)


class NearMissError(ValueError):
    """A near-miss that cannot be built as its definition says (an anchor gone or doubled, a target missing)."""


def head_variant(nm: NearMiss, head) -> list:
    """The head constructor's DDL statements with `nm`'s ONE change applied, in declaration order."""
    keys = [o.key for o in head]
    if keys.count(nm.target) != 1:
        raise NearMissError(f"near-miss {nm.name}: head declares {keys.count(nm.target)} object(s) {nm.target}")
    out = []
    for o in head:
        if o.key != nm.target:
            out.append(o.ddl)
        elif nm.anchor is None:
            continue
        elif o.ddl.count(nm.anchor) != 1:
            raise NearMissError(f"near-miss {nm.name}: its anchor occurs {o.ddl.count(nm.anchor)} time(s) in "
                                f"{nm.target[0]} {nm.target[1]}")
        else:
            out.append(o.ddl.replace(nm.anchor, nm.replacement))
    return out
