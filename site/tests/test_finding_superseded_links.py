"""F04-T18: a superseded statement names the statement that replaced it, and why (Q20).

An outside contributor was handed ``/problems/erdos-69/#node=erdos-69--h2-v2--h1``, a node a D-8
revision had replaced the evening before. The page said one word, "superseded". Neither the
panel nor the statement's own page named the successor or the reason; the service's
``409 node-not-open`` did not either. The contributor guessed the successor from the ``-v2``
suffix. Everything needed was already in the tree: the old node's status record carries
``reference`` (the successor) and ``cause`` (the curator's sentence naming the revision request
and its defect class), and the successor's ``META.yaml`` carries ``supersedes``.
"""

from __future__ import annotations

import dataclasses

import fixture
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
PROBLEM = f"problems/{TARGET}/index.html"
OLD, NEW = fixture.REVISED_HOLE, fixture.REVISION


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = fixture.build_with_revised_hole(tmp_path_factory.mktemp("superseded"))
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)


def panel(page: str, node_id: str) -> str:
    panels = page.split('<div class="card panel" ')[1:]
    return str(next(p for p in panels if p.startswith(f'data-node="{node_id}"')))


def test_the_model_reads_both_ends_of_a_revision(built: tuple[model.Site, dict[str, str]]) -> None:
    site, _pages = built
    nodes = site.targets[TARGET].nodes
    assert nodes[OLD].superseded_by == NEW
    assert nodes[OLD].superseded_cause == fixture.REVISION_CAUSE
    assert nodes[NEW].supersedes == OLD
    assert nodes[fixture.HOLE].superseded_by is None and nodes[fixture.HOLE].supersedes is None


def test_the_superseded_page_links_its_replacement_and_says_why(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"nodes/{TARGET}/{OLD}/index.html"]
    assert f'Superseded by <a href="/nodes/{TARGET}/{NEW}/">{NEW}</a>' in page
    assert render.esc(fixture.REVISION_CAUSE) in page
    assert "Work continues on the replacement" in page


def test_the_replacement_page_links_what_it_revises(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"nodes/{TARGET}/{NEW}/index.html"]
    assert f'Revises <a href="/nodes/{TARGET}/{OLD}/">{OLD}</a>' in page


def test_the_panel_a_deep_link_selects_points_at_the_live_statement(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """``#node=<superseded id>`` still selects that panel (history stays addressable); the way
    forward is in it, selecting the successor's panel on the same page."""
    _site, pages = built
    old = panel(pages[PROBLEM], OLD)
    assert f'Superseded by <a href="#node={NEW}">{NEW}</a>' in old
    assert f'Revises <a href="#node={OLD}">{OLD}</a>' in panel(pages[PROBLEM], NEW)
    script = (render.STATIC / "problem.js").read_text(encoding="utf-8")
    assert "hashchange" in script  # an in-page #node= link has to reselect


def test_the_curators_sentence_is_escaped(built: tuple[model.Site, dict[str, str]]) -> None:
    site, _pages = built
    nv = site.targets[TARGET].nodes[OLD]
    hostile = dataclasses.replace(nv, superseded_cause="<script>alert(1)</script>")
    note = render.Renderer(site, repo_url=REPO).revision_note(TARGET, hostile, in_page=False)
    assert "<script>" not in note and "&lt;script&gt;" in note


def test_a_superseded_record_with_no_reference_says_only_what_it_knows(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """A curator's hand-written record may omit ``reference`` (node-status/v1 lets it)."""
    site, _pages = built
    nv = dataclasses.replace(site.targets[TARGET].nodes[OLD], superseded_by=None)
    note = render.Renderer(site, repo_url=REPO).revision_note(TARGET, nv, in_page=False)
    assert "Superseded by" not in note and render.esc(fixture.REVISION_CAUSE) in note
