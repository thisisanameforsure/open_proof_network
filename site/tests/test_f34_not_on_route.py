"""F34-T18 (R18; handoff §3.4.4): "§2 Not on a route" places every statement no route uses, so
that the page places every statement of the problem exactly once — on a route in the drawing,
or here.

Groups, in order: statements proposed for a statement (grouped by it); statements proposed for
none; related results; special cases no split uses; superseded statements, each with what
replaced it; anything else no route reaches. A problem whose every statement is on a route has
no §2 and no link to it.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import fixture
from harness import TARGET
from test_crux_band import CRUX, band_tree
from test_one_view import VARIANT, off_route
from test_one_view_markup import layouts_in
from test_products import ROOT_NODE
from test_routes_view import render_tree, two_routes

from opn_site import model

PAGE = f"problems/{TARGET}/index.html"


def section(page: str) -> str | None:
    m = re.search(r'<section class="off-route">(.*?)</section>', page, re.S)
    return m.group(1) if m else None


def placed(page: str) -> Counter[str]:
    """Each statement §2 places: a line of a group's list, or (F34-T43: the tree is the list) a
    box of a group's small tree."""
    body = section(page) or ""
    trees = "".join(re.findall(r'<svg class="dag mini-tree".*?</svg>', body, re.S))
    return Counter(
        re.findall(r'<li data-node="([^"]+)"', body)
        + re.findall(r'<g class="node[^"]*" data-node="([^"]+)"', trees)
    )


def on_route(page: str) -> set[str]:
    """Drawn on a route: in the routes view, or (F27-R14, D-25 v3.52) on a strictly harder route,
    drawn in the ``harder`` view behind its own toggle — on a route either way, never in §2."""
    lays = layouts_in(page)
    views = [lays["routes"], *([lays["harder"]] if "harder" in lays else [])]
    return {n for v in views for n in v["nodes"] if "@" not in n}


def every_statement(root: Path) -> set[str]:
    return set(model.load_site(root, fixture.COMMIT).targets[TARGET].nodes)


def assert_each_placed_once(root: Path, page: str) -> None:
    here = placed(page)
    assert all(n == 1 for n in here.values()), here
    drawn = on_route(page)
    assert not drawn & set(here), drawn & set(here)
    assert drawn | set(here) == every_statement(root)


def test_a_statement_proposed_for_none_is_listed_once(tmp_path: Path) -> None:
    root = off_route(tmp_path / "g")
    page = render_tree(root)[PAGE]
    body = section(page)
    assert body is not None
    assert '<h2 id="not-on-route"><span class="sec">§2</span> Not on a route</h2>' in body
    group = re.search(r"<h3>Proposed for no statement</h3>\s*<ul>(.*?)</ul>", body, re.S)
    assert group is not None and f'data-node="{VARIANT}"' in group.group(1)
    assert_each_placed_once(root, page)
    assert 'href="#not-on-route"' in page  # On this page links it


def test_a_crux_is_grouped_under_the_statement_it_was_proposed_for(tmp_path: Path) -> None:
    root = band_tree(tmp_path / "g")
    page = render_tree(root)[PAGE]
    body = section(page)
    assert body is not None
    # F34-T26, T43: the group's small tree under its heading is its list
    # F34-T44: the heading names the statement by its words ('For "…"')
    group = re.search(r"<h3>For &ldquo;(.*?)</h3>(.*?)</div><!-- /off-group -->", body, re.S)
    assert group is not None
    assert f'href="/nodes/{TARGET}/{ROOT_NODE}/"' in group.group(1)
    assert f'data-node="{CRUX}"' in group.group(2)
    assert_each_placed_once(root, page)


def test_every_statement_on_a_route_means_no_section(tmp_path: Path) -> None:
    root = two_routes(tmp_path / "g")
    page = render_tree(root)[PAGE]
    assert section(page) is None and 'href="#not-on-route"' not in page
    assert on_route(page) == every_statement(root)


# -- F34-Q26 closed (the owner, 2026-11-26): the speculative column becomes §2's small trees ------


def test_a_proposed_group_is_drawn_as_a_small_tree(tmp_path: Path) -> None:
    """Each "Proposed for" group in §2 is drawn — its statements as pills, the lines among them —
    before its list; the speculative column is no longer in §1."""
    root = band_tree(tmp_path / "g")
    page = render_tree(root)[PAGE]
    body = section(page)
    assert body is not None
    group = re.search(r'<div class="off-group"[^>]*>(.*?)</div><!-- /off-group -->', body, re.S)
    assert group is not None
    tree = re.search(r'<svg class="dag mini-tree"[^>]*>(.*?)</svg>', group.group(1), re.S)
    assert tree is not None
    assert f'data-node="{CRUX}"' in tree.group(1)
    assert 'class="band-wrap"' not in page and '<svg class="dag band"' not in page
