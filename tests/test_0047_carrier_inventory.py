"""0047 §4d: the carrier inventory by complement (`specs/evidence/0047/carrier_inventory.py`).

The census is what makes 0047's "a new render path cannot land undecided" true, so it runs on the tree here in every
suite run, and its refusals are driven one by one on planted source trees (P1's mutation matrix). It is evidence for a
spec under review, not product code; it imports nothing from `veracium`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
_PATH = ROOT / "specs" / "evidence" / "0047" / "carrier_inventory.py"


def _load():
    spec = importlib.util.spec_from_file_location("carrier_inventory", _PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_tree_census_is_fully_classified(capsys):
    """Every function in src/ that carries a fact's content has a 0047 §4d disposition, none is stale, none awaits a
    ruling — a new render path fails this test until someone decides what it does with a challenged fact."""
    inv = _load()
    rc = inv.main()
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "unclassified 0; stale 0; RULING 0" in out


_BASE = {
    "schema.py": '''
        class Edge:
            object: str
        ''',
    "render.py": '''
        def render(edges):
            return [e.object for e in edges]
        ''',
}
_BASE_CLASSIFIED = {("render.py", "render"): ("RENDER", "the planted renderer")}


def _tree(tmp_path, extra=None):
    src = tmp_path / "src"
    src.mkdir(parents=True)
    for name, body in {**_BASE, **(extra or {})}.items():
        (src / name).write_text(textwrap.dedent(body), encoding="utf-8")
    return src


def test_the_inventory_refuses_each_planted_defect(tmp_path, capsys):
    """carrier_inventory's mutation matrix: each planted defect exits 1 and names its site; the honest tree exits 0."""
    inv = _load()
    cases = {
        # name: (extra source files, classification override, the line that must be printed)
        "an unclassified `.object` read": (
            {"new.py": "def leak(e):\n    return e.object\n"}, None, "UNCLASSIFIED: new.py:leak"),
        "an unclassified whole-model serialisation": (
            {"new.py": "def dump(e):\n    return e.model_dump()\n"}, None, "UNCLASSIFIED: new.py:dump"),
        "a carrier type annotated with a QUOTED Edge, constructed": (
            {"res.py": "class Hit:\n    fact: 'Edge'\n\ndef build(x):\n    return Hit(fact=x)\n"}, None,
            "UNCLASSIFIED: res.py:build"),
        "a TRANSITIVE carrier (a field typed with a class that carries Edge), constructed": (
            {"res.py": "class Hit:\n    fact: Edge\n\nclass Page:\n    hits: list[Hit]\n\n"
                       "def page(xs):\n    return Page(hits=xs)\n"}, None, "UNCLASSIFIED: res.py:page"),
        "a carrier constructed through a module attribute": (
            {"res.py": "class Hit:\n    fact: Edge\n", "use.py": "import res\n\ndef make(x):\n    return res.Hit(fact=x)\n"},
            None, "UNCLASSIFIED: use.py:make"),
        "a same-named method in another class (qualified keys)": (
            {"two.py": "class A:\n    def render(self, e):\n        return e.object\n\n"
                       "class B:\n    def render(self, e):\n        return e.object\n"},
            {**_BASE_CLASSIFIED, ("two.py", "A.render"): ("RENDER", "A")}, "UNCLASSIFIED: two.py:B.render"),
        "an inner function is its own site": (
            {"nest.py": "def outer(es):\n    def inner(e):\n        return e.object\n    return [inner(e) for e in es]\n"},
            {**_BASE_CLASSIFIED, ("nest.py", "outer"): ("RENDER", "outer")}, "UNCLASSIFIED: nest.py:outer.inner"),
        "a stale classification": (
            None, {**_BASE_CLASSIFIED, ("gone.py", "vanished"): ("RENDER", "gone")}, "STALE: gone.py:vanished"),
        "a site still awaiting a RULING": (
            None, {("render.py", "render"): ("RULING", "undecided")}, "RULING PENDING: render.py:render"),
    }
    honest = _tree(tmp_path / "honest")
    assert inv.main(honest, dict(_BASE_CLASSIFIED)) == 0, capsys.readouterr().out
    capsys.readouterr()
    for i, (name, (extra, classified, expect)) in enumerate(cases.items()):
        src = _tree(tmp_path / f"case{i}", extra)
        rc = inv.main(src, classified if classified is not None else dict(_BASE_CLASSIFIED))
        out = capsys.readouterr().out
        assert rc == 1, f"{name}: exited {rc}\n{out}"
        assert expect in out, f"{name}: expected {expect!r}\n{out}"


def test_the_derived_carrier_types_are_the_four_0047_names(capsys):
    """0047 §4d names the derived types at adoption; the census prints them, so the sentence is checkable."""
    inv = _load()
    assert inv.carrier_types() == {"AsOfFact", "ContestedGroup", "Recall", "SupersessionPlan"}
