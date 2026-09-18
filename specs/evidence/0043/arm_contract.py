#!/usr/bin/env python3
"""0043 A6-bis — THE ARM CONTRACT: both arms receive the SAME evidence set (edges, episodes,
compiled context), id for id, from ONE selection; they differ in exactly one dimension — whether
the rendered text carries the trust discipline.

Round 2: the previous baseline was built from the examiner projection (active edges only) while
the shipped answer path receives selected edges + episodes + compiled context; the demonstration
fixture had three episodes and projected none. So: the examiner view and the baseline evidence set
are DIFFERENT artifacts; the selection runs ONCE (re-running it invites a different selection and
the comparison silently changes its own independent variable); the fixture MUST contain episodes
and both arms must receive them; the check is on the EVIDENCE (id sets), not on the rendering.

    python3 specs/evidence/0043/arm_contract.py     # builds the fixture, runs one selection, checks both arms
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _fake_llm(prompt, *, system=None, role="compile", json_schema=None):
    return "## USER MODEL\n- fixture wiki"          # the compile role only; no distill in this harness


def select_once(db_path: str, query: str, *, max_subgraph_edges: int = 40):
    """ONE selection: the shipped path's own `recall`. Returns the Recall and the frozen configuration."""
    from veracium import Memory, MemoryConfig
    mem = Memory(llm=_fake_llm, config=MemoryConfig(require_source_id=False, db_path=db_path, wiki_recompile_after_writes=0,
                                                    max_subgraph_edges=max_subgraph_edges))
    r = mem.recall("u", query); mem.close()
    return r, {"query": query, "max_subgraph_edges": max_subgraph_edges}


def evidence_set(recall) -> dict:
    """The ids handed to an arm — edges, episodes, compiled-context units (wiki sections)."""
    return {"edges": sorted(e.id for e in recall.edges), "episodes": sorted(ep.id for ep in recall.episodes),
            "context_units": sorted(h for h in re.findall(r"^## .+$", recall.context, re.M))}


def declassed(recall):
    """The SAME evidence with the trust class removed: copies of the selected edges whose
    provenance.disclosure is MENTIONABLE and derived_from is None, and the same episodes. Nothing else
    on any record changes — ids, subjects, relations, objects, dates are the ones recall selected."""
    from veracium.schema import Disclosure
    from veracium.schema import EvidenceAuthor
    def declass_prov(pv):   # the class, and the class ALONE: disclosure, authorship routing, derivation routing
        return pv.model_copy(update={"disclosure": Disclosure.MENTIONABLE, "derived_from": None, "author_of_evidence": EvidenceAuthor.USER})
    edges = [e.model_copy(update={"provenance": declass_prov(e.provenance)}) for e in recall.edges]
    episodes = [ep.model_copy(update={"provenance": declass_prov(ep.provenance)}) for ep in recall.episodes]
    return edges, episodes


def render_arm(edges, episodes) -> str:
    """The product's own partition render over an evidence set — the baseline uses the SAME renderer,
    so the only difference between arms is what the renderer had to say about trust."""
    from veracium.gate import partition
    grounded, unverified = partition(edges, episodes)
    return "## RELEVANT DETAIL\n" + grounded + ("\n\n## UNVERIFIED THIRD-PARTY CLAIMS (never assert as fact)\n" + unverified if unverified else "")


def facts(rendered: str) -> list[tuple]:
    """The (relation, object) facts and the episode lines a rendering carries, with every trust
    annotation and the quarantine construction ("<subject> claims: <relation> <object>") normalised
    away — what a reader is TOLD, independent of how it was marked."""
    ep = _load("examiner_projection")
    frags = sorted({f for fr in ep.derive_forbidden_markers()["prose"].values() for f in fr}, key=len, reverse=True)
    out = []
    for line in rendered.splitlines():
        if not line or line.startswith("## "):
            continue
        for f in frags:
            line = line.replace(f, "")
        line = re.sub(r"\s*\[[^\]]*\]", lambda m: m.group(0) if re.match(r"\s*\[\d{4}-\d{2}-\d{2}\]", m.group(0)) else "", line)
        line = line.strip()
        m = re.match(r"^(?:\S+ )?claims: (\S+) (.+?) \((\d{4}-\d{2}-\d{2})\)$", line)
        if m:
            out.append(("fact", m.group(1), m.group(2))); continue
        m = re.match(r"^(?:\S+ )?(\S+): (.+?) \(since (\d{4}-\d{2}-\d{2})\)", line)
        if m:
            out.append(("fact", m.group(1), m.group(2))); continue
        out.append(("line", line.strip()))
    return sorted(out)


def build_arms(db_path: str, query: str) -> dict:
    recall, cfg = select_once(db_path, query)
    shipped = {"evidence": evidence_set(recall), "rendered": render_arm(list(recall.edges), list(recall.episodes))}
    d_edges, d_eps = declassed(recall)                                       # SAME recall object, class removed
    baseline = {"evidence": {"edges": sorted(e.id for e in d_edges), "episodes": sorted(ep.id for ep in d_eps),
                             "context_units": shipped["evidence"]["context_units"]},
                "rendered": render_arm(d_edges, d_eps)}
    return {"config": cfg, "shipped": shipped, "baseline": baseline}


def check(arms: dict) -> list[str]:
    p = []
    if arms["shipped"]["evidence"] != arms["baseline"]["evidence"]:
        p.append("the arms' evidence sets differ")
    if not arms["shipped"]["evidence"]["episodes"]:
        p.append("no episodes reached the arms — the fixture must contain episodes and both arms must receive them")
    if not arms["shipped"]["evidence"]["edges"]:
        p.append("no edges reached the arms")
    ep = _load("examiner_projection"); d = ep.derive_forbidden_markers()
    if not ep.hits(arms["shipped"]["rendered"], d):
        p.append("the shipped rendering carries no trust annotation — nothing for the arms to differ in (fixture defect)")
    if ep.hits(arms["baseline"]["rendered"], d) or " claims: " in arms["baseline"]["rendered"] or "UNVERIFIED" in arms["baseline"]["rendered"]:
        p.append("the baseline rendering still carries the trust discipline (a marker, a section, or the quarantine construction)")
    fs, fb = facts(arms["shipped"]["rendered"]), facts(arms["baseline"]["rendered"])
    if fs != fb:
        p.append(f"the arms tell the reader different FACTS — they differ in evidence, not only in discipline: only-shipped {sorted(set(fs)-set(fb))} only-baseline {sorted(set(fb)-set(fs))}")
    return p


if __name__ == "__main__":
    ev = _load("examiner_view")
    with tempfile.TemporaryDirectory() as d:
        st = ev.fixture_store(f"{d}/f.db"); st.close()
        arms = build_arms(f"{d}/f.db", "where does the user work and what do they prefer")
    print(json.dumps({"config": arms["config"], "evidence": arms["shipped"]["evidence"]}, indent=1))
    print("--- shipped rendering:"); print(arms["shipped"]["rendered"]); print("--- baseline rendering:"); print(arms["baseline"]["rendered"])
    probs = check(arms); print("ARM CONTRACT:", "PASS" if not probs else probs); sys.exit(0 if not probs else 1)
