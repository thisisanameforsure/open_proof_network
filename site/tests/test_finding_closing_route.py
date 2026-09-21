"""The "closable through its holes" line on a statement's panel (Mike, 2026-09-21).

Two outside agents worked a target's holes for a session before finding, by experiment, that
the root could not be assembled from them. Since F00-T10 it can: a proof reaches its holes'
theorems through the node's own Context, which a newer statement imports and an older one's
proof may import itself. The panel of a node that *has* holes says so, and says which; a node
with none says nothing. The same function decides as on the MCP's ``get_node``
(``layout.imports_own_context``).
"""

from __future__ import annotations

import dataclasses
import re

import fixture
import pytest
from harness import TARGET

from opn_gate import graph as graphmod
from opn_gate import layout
from opn_site import model, render

REPO = "https://github.com/example/graph"
PARENT = "and-swap-reassoc"


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> model.Site:
    root = fixture.build_with_revised_hole(tmp_path_factory.mktemp("closing"))
    return model.load_site(root, fixture.COMMIT)


def panel(page: str, node_id: str) -> str:
    (hit,) = re.findall(
        rf'<div class="card panel" data-node="{re.escape(node_id)}".*?\n</div>', page, flags=re.S
    )
    return str(hit)


def test_the_line_is_on_exactly_the_open_nodes_that_have_holes(site: model.Site) -> None:
    """Held to the graph's own notion of a hole, so the page cannot invent or miss one."""
    tv = site.targets[TARGET]
    page = render.render_site(site, repo_url=REPO)[f"problems/{TARGET}/index.html"]
    with_holes = {
        nid
        for nid, nv in tv.nodes.items()
        if nv.status not in ("proved", "superseded")
        and any(
            graphmod.is_hole_of(nid, other, str(ov.graph_entry.get("origin")))
            and ov.status != "superseded"
            for other, ov in tv.nodes.items()
        )
    }
    assert with_holes == {PARENT}, "guard: the fixture"
    shown = {nid for nid in tv.nodes if "closing-note" in panel(page, nid)}
    assert shown == with_holes


def test_a_statement_that_imports_its_context_says_the_holes_are_in_reach(site: model.Site) -> None:
    tv = site.targets[TARGET]
    assert layout.imports_own_context(PARENT, tv.nodes[PARENT].statement), "guard: the fixture"
    note = render.Renderer(site, repo_url=REPO).closing_note(tv, tv.nodes[PARENT])
    assert "Closable through its holes" in note
    assert "adds" not in note  # nothing for the contributor to add


def test_an_older_statement_says_which_line_the_proof_adds(site: model.Site) -> None:
    """The live shape: nine of the ten nodes with holes on the graph of 2026-09-21."""
    tv = site.targets[TARGET]
    old = dataclasses.replace(
        tv.nodes[PARENT],
        statement=tv.nodes[PARENT].statement.replace(f"import Nodes.«{PARENT}».Context\n", ""),
    )
    note = render.Renderer(site, repo_url=REPO).closing_note(tv, old)
    assert "Closable through its holes" in note
    assert f"import Nodes.«{PARENT}».Context" in note and "adds" in note
