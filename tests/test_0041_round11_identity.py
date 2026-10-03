"""specs/0041 round 11 — R10-03: the notice's SOURCE IDENTITY over the whole admitted identifier domain.

Round 10 joined (origin, source user, source event ref, destination user, kind, target) with U+001F into the row id,
decoded it by splitting, and compared the source identity by a substr prefix. Over the strings the import boundary
admits that was not injective (two triples collided), not decodable (a relay re-labelled the row as LOCAL), and not
comparable (a NUL defeated the prefix). The identity is now three structured columns compared EXACTLY, and the row id
a digest over the six components, each length-framed.

Every cell goes through the real `export_memory` / `import_memory` / `Memory.redact` paths. The identifier values
under test are produced NATIVELY where a store can hold them (a user id is any string the store accepts); a file is
hand-assembled only where the verdict's own reproduction does (two notice inputs differing in where a separator
falls), and every adversarial value is paired with the ordinary control that must behave identically.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

from veracium.portability import export_memory, import_memory
from veracium.schema import Edge
from veracium.store.sqlite import SqliteStore

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tt41_r11i", ROOT / "tests" / "test_0041_transition_table.py")
tt = importlib.util.module_from_spec(_spec)
sys.modules["tt41_r11i"] = tt
_spec.loader.exec_module(tt)

SECRET = "SECRET-IDENTITY-R11"
# every value the import boundary admits for a source identity component that round 10's encoding mishandled,
# plus the characters research named, and the ordinary control (the same cells must hold for each)
ADVERSARIAL = {"US": "own\u001fer", "NUL": "own\u0000er", "%": "own%er", "_": "own_er", ":": "own:er",
               "|": "own|er", "non-ASCII": "öwnér-所有者", "ordinary": "owner"}
# the same classes as BARE boundary tokens: a join collides only when the bytes moved across a boundary are exactly
# its separator, so the injectivity cell moves each token alone (round 10's U+001F join fails the "US" row)
BOUNDARY = {"US": "\u001f", "NUL": "\u0000", "%": "%", "_": "_", ":": ":", "|": "|", "non-ASCII": "ö", "ordinary": "-"}


def _strict(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _lines(p):
    return [json.loads(x, object_pairs_hook=_strict) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]


def _write(p, recs):
    pathlib.Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def _head(recs):
    return [r for r in recs if r.get("kind") == "veracium-export"]


def _notices(recs):
    return [r for r in recs if r.get("record") == "redaction"]


def _triple(n):
    return (n["origin"], n["source_user"], n["source_event_ref"])


def _redacted_export(tmp_path, user, name="src"):
    """A NATIVE source whose user id is `user`: a real write, a real redaction, a real export."""
    src = tt._mem(tmp_path, f"{name}.db")
    src.store.add_edge(Edge(id="e-x", user_id=user, subject="user", relation="lives_at", object=SECRET,
                            provenance=tt._prov()))
    src.redact(user, edge_id="e-x", reason="subject_request")
    p = tmp_path / f"{name}.jsonl"
    export_memory(src.store, user, p)
    return src, p


# ------------------------------------------------------------------ the encoding itself

def test_two_triples_whose_separators_fall_differently_are_two_identities():
    """The verdict's first case, at the encoding: round 10's U+001F join made these equal."""
    a = SqliteStore.notice_id("origin\u001fpart", "owner", "event", "u", "edge", "e")
    b = SqliteStore.notice_id("origin", "part\u001fowner", "event", "u", "edge", "e")
    assert a != b


@pytest.mark.parametrize("label", sorted(ADVERSARIAL))
def test_the_row_id_is_injective_over_each_component(label):
    """Shifting a value between ANY two adjacent components changes the id (BEHAVIOUR: round 10's join already
    satisfied this for every value but the separator itself, so the other rows are its controls)."""
    v = BOUNDARY[label]
    comps = ["o", "s", "e", "u", "edge", "t"]
    for i in range(5):                       # move "<v>x" across the boundary between component i and i+1:
        left, right = list(comps), list(comps)
        left[i] = comps[i] + v + "x"         # ... "o<v>x" | "s"    ...
        right[i + 1] = "x" + v + comps[i + 1]  # ... "o"     | "x<v>s" ... — a join on <v> makes these EQUAL
        assert SqliteStore.notice_id(*left) != SqliteStore.notice_id(*right), (label, i)


@pytest.mark.parametrize("label", sorted(ADVERSARIAL))
def test_the_row_id_is_a_digest_that_carries_no_component(label):
    """REPRESENTATION (new in round 11): a fixed-shape digest, so no component's bytes appear in it to be parsed."""
    v = ADVERSARIAL[label]
    rid = SqliteStore.notice_id(v, v, v, v, "edge", v)
    assert rid.startswith("notice-") and len(rid) == len("notice-") + 64 and all(c in "0123456789abcdef" for c in rid[7:])


# ------------------------------------------------------------------ the verdict's three cases, through the real paths

def test_R10_03_a_two_source_triples_that_encoded_equal_are_two_standing_notices(tmp_path):
    _src, p = _redacted_export(tmp_path, "owner")
    recs = _lines(p)
    (n0,) = _notices(recs)
    a = dict(n0, origin="origin\u001fpart", source_user="owner", source_event_ref="event")
    b = dict(n0, origin="origin", source_user="part\u001fowner", source_event_ref="event")
    dst = tt._mem(tmp_path, "dst.db")
    ra = import_memory(dst.store, _write(tmp_path / "a.jsonl", _head(recs) + [a]))
    rb = import_memory(dst.store, _write(tmp_path / "b.jsonl", _head(recs) + [b]))
    assert ra["notices_standing"] == 1 and rb["notices_standing"] == 1 and rb["notices_existing"] == 0
    held = dst.store._conn.execute("SELECT source_origin, source_user, source_event_ref FROM redactions").fetchall()
    assert sorted(held) == sorted([("origin\u001fpart", "owner", "event"), ("origin", "part\u001fowner", "event")])


@pytest.mark.parametrize("label", sorted(ADVERSARIAL))
def test_R10_03_b_a_relay_preserves_the_native_source_triple(tmp_path, label):
    """Source user `v` (native), imported REMAPPED to 'destination', re-exported: the relay names the SOURCE, never
    itself — for every value, the ordinary one included (that is the control)."""
    user = ADVERSARIAL[label]
    _src, p = _redacted_export(tmp_path, user)
    (orig,) = _notices(_lines(p))
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p, user_id="destination")
    relay = tmp_path / "relay.jsonl"
    export_memory(dst.store, "destination", relay)
    (rel,) = _notices(_lines(relay))
    assert _triple(rel) == _triple(orig) and rel["source_user"] == user


@pytest.mark.parametrize("label", sorted(ADVERSARIAL))
def test_the_original_and_its_relay_are_held_as_one_source_identity(tmp_path, label):
    """REPRESENTATION (new in round 11): an honest relay is never read as a contradiction — beside the original in a
    third store it lands as a second BINDING (its destination user and minted target differ) of ONE source identity
    with ONE body, held in the structured columns."""
    user = ADVERSARIAL[label]
    _src, p = _redacted_export(tmp_path, user)
    (orig,) = _notices(_lines(p))
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p, user_id="destination")
    relay = tmp_path / "relay.jsonl"
    export_memory(dst.store, "destination", relay)
    third = tt._mem(tmp_path, "third.db")
    import_memory(third.store, p)
    import_memory(third.store, relay)
    held = third.store._conn.execute(
        "SELECT DISTINCT source_origin, source_user, source_event_ref, source_body FROM redactions").fetchall()
    assert len(held) == 1 and held[0][:3] == _triple(orig)


@pytest.mark.parametrize("label", sorted(ADVERSARIAL))
def test_R10_03_c_a_changed_body_under_the_same_source_identity_refuses(tmp_path, label):
    """A standing notice, then the SAME source identity with a changed valid reason: refused atomically, for every
    value — through the new exact comparison (the NUL row is the verdict's case; 'ordinary' is its control)."""
    user = ADVERSARIAL[label]
    _src, p = _redacted_export(tmp_path, user)
    recs = _lines(p)
    (n0,) = _notices(recs)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, _write(tmp_path / "n1.jsonl", _head(recs) + [n0]))
    changed = dict(n0, reason="legal_obligation")
    assert changed["reason"] != n0["reason"]
    rows_before = dst.store._conn.execute("SELECT * FROM redactions").fetchall()
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, _write(tmp_path / "n2.jsonl", _head(recs) + [changed]))
    assert dst.store._conn.execute("SELECT * FROM redactions").fetchall() == rows_before


def test_R10_03_c_the_comparison_crosses_a_destination_remap_for_a_NUL_identity(tmp_path):
    """S2-1's scope kept: one source event has ONE body whichever destination user it lands on — with a NUL in it."""
    user = ADVERSARIAL["NUL"]
    _src, p = _redacted_export(tmp_path, user)
    recs = _lines(p)
    (n0,) = _notices(recs)
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, _write(tmp_path / "n1.jsonl", _head(recs) + [n0]), user_id="d1")
    with pytest.raises(ValueError, match="different body"):
        import_memory(dst.store, _write(tmp_path / "n2.jsonl", _head(recs) + [dict(n0, reason="legal_obligation")]),
                      user_id="d2")


def test_control_an_equal_body_remapped_twice_is_not_a_contradiction(tmp_path):
    _src, p = _redacted_export(tmp_path, ADVERSARIAL["US"])
    dst = tt._mem(tmp_path, "dst.db")
    import_memory(dst.store, p, user_id="d1")
    r = import_memory(dst.store, p, user_id="d2")
    assert r["notices_applied"] == 1


# ------------------------------------------------------------------ the boundary and the local row

@pytest.mark.parametrize("key", ["origin", "source_user", "source_event_ref"])
def test_an_empty_source_component_is_refused_at_the_boundary(tmp_path, key):
    """An EMPTY component is refused before any write (the parser and the commit primitive): no identity is ever
    held with an empty part, so nothing can emit one."""
    _src, p = _redacted_export(tmp_path, "owner")
    recs = _lines(p)
    (n0,) = _notices(recs)
    dst = tt._mem(tmp_path, "dst.db")
    with pytest.raises(ValueError):
        import_memory(dst.store, _write(tmp_path / "e.jsonl", _head(recs) + [dict(n0, **{key: ""})]))
    assert dst.store._conn.execute("SELECT COUNT(*) FROM redactions").fetchone()[0] == 0


def test_a_local_redaction_holds_no_source_columns_and_exports_this_stores_own_identity(tmp_path):
    src, p = _redacted_export(tmp_path, ADVERSARIAL["US"])
    held = src.store._conn.execute("SELECT id, source_origin, source_user, source_event_ref FROM redactions").fetchone()
    assert held[0].startswith("rd-") and held[1:] == (None, None, None)
    (n,) = _notices(_lines(p))
    assert n["origin"] == src.store.local_origin() and n["source_user"] == ADVERSARIAL["US"]
