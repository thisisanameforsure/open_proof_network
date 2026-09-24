"""F04-T26 (Q28): a circular statement is drawn, keyed and defined as circular.

The finding (2026-09-24, the erdos-1050 MCP tester, 12:26Z): the problem page's selected-statement
card called ``erdos-1050--h1-v2--h1`` "circular", while the statement graph's key listed only
proved, open, blocked and superseded, so nothing on the page said what circular meant.

Reading the renderer showed it was worse than a missing word. A merged circularity claim (D-16,
F08-T17) leaves the node's ``status`` as published (``ready``) and sets ``cause: circular``, and the
graph's pills are coloured by the bare status. So the circular hole was drawn with the accent ring
of an open, claimable statement: the exact node the claim took off the frontier. The key's own
guard, ``test_every_status_the_gate_can_derive_has_a_key_entry``, iterates statuses only, so it
could never see a state that comes from a cause.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import fixture

from opn_gate import graph as gate_graph
from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
ROOT = "and-swap-reassoc"
DEP = "and-reassoc"
CSS = (Path(render.__file__).resolve().parent / "static" / "site.css").read_text(encoding="utf-8")


def site_and_target(tmp_path: Path) -> tuple[Any, Any]:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    return site, site.targets[TARGET]


def circular_page(tmp_path: Path, node_id: str = DEP) -> str:
    """The fixture's problem page with one node as a merged circularity claim leaves it."""
    site, tv = site_and_target(tmp_path)
    nodes = dict(tv.nodes)
    nv = nodes[node_id]
    entry = {**nv.graph_entry, "status": "ready", "cause": gate_graph.CAUSE_CIRCULAR}
    nodes[node_id] = dataclasses.replace(nv, graph_entry=entry)
    graph = {
        **tv.graph,
        "nodes": [
            {**n, "status": "ready", "cause": gate_graph.CAUSE_CIRCULAR}
            if n.get("node_id") == node_id
            else n
            for n in tv.graph["nodes"]
        ],
    }
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    return r.target(dataclasses.replace(tv, nodes=nodes, graph=graph))


def legend_words(html: str) -> list[str]:
    m = re.search(r'<div class="dag-legend">(.*?)</div>', html, re.S)
    assert m is not None, "the problem page has no graph key"
    return re.findall(
        r'<span class="dot dot-[a-z-]+"></span>([a-z ]+)<span class="term-card"', m.group(1)
    )


def gate_causes() -> list[str]:
    return [v for k, v in vars(gate_graph).items() if k.startswith("CAUSE_") and isinstance(v, str)]


def test_every_state_a_node_can_take_has_a_key_entry(tmp_path: Path) -> None:
    """Every word ``node_state`` can return, from any status the gate publishes with any cause it
    derives, has a glossary card and a place in the key: the guard the status-only test missed."""
    _site, tv = site_and_target(tmp_path)
    nv = tv.nodes[ROOT]
    missing = []
    for status in render.STATUS_WORDS:
        for cause in (None, *gate_causes()):
            entry = {**nv.graph_entry, "status": status, "cause": cause}
            state = render.Renderer.node_state(dataclasses.replace(nv, graph_entry=entry))
            keyed = state in (*render.DOTTED_KEYS, *render.LEGEND_EXTRA)
            if state not in render.GLOSSARY_BY_KEY or not keyed:
                missing.append((status, cause, state))
    assert not missing, missing


def test_a_circular_statement_is_named_in_the_key(tmp_path: Path) -> None:
    assert "circular" in legend_words(circular_page(tmp_path))


def test_a_circular_statement_is_not_drawn_as_open(tmp_path: Path) -> None:
    """The pill wears the state the row names, as T17 did for a needs-witness hole."""
    html = circular_page(tmp_path)
    pill = re.search(rf'<g class="node status-([a-z-]+)"[^>]*>(?:(?!</g>).)*?{DEP}', html, re.S)
    assert pill is not None
    assert pill.group(1) == "circular"


def test_the_stylesheet_gives_circular_its_own_mark() -> None:
    for selector in (".dot-circular", ".dag .status-circular circle", ".status-circular .mark"):
        assert selector in CSS, selector


def test_the_glossary_says_what_circular_means_and_where_it_comes_from() -> None:
    _word, meaning, proto = render.GLOSSARY_BY_KEY["circular"]
    assert "defect claim" in meaning
    assert "not accepting work" in meaning.lower()
    assert "D-16" in proto


def test_the_docs_state_map_lists_circular() -> None:
    assert "circular" in render.STATE_MAP_STATEMENT_KEYS
