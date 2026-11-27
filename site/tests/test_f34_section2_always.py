"""F34-T49 (ROUND-2 D7): §2 is always there, and §1 and §2 together place every statement.

* "On a route" means drawn by a route of the picker, a harder one included. Before this it meant
  "in the old all-routes layout", which no page draws any more: on the live graph (2026-11-27)
  that counted 10 proved statements of erdos-1094 and 4 statements of erdos-257 as placed that no
  route draws — the pieces of proofs already complete, and a special case with its holes.
* A statement that only the proof of a proved statement rests on is listed in §2 under a heading
  of its own.
* A problem whose every statement is on a route still has §2, with one line saying so, so the
  section numbers never skip; "On this page" always lists it.
* In a §2 group, a statement that a route's statement uses says which route, with a link that
  draws it ("also used by Route 1").
"""

from __future__ import annotations

import re
from html import unescape
from pathlib import Path

import fixture
from harness import TARGET
from test_crux_band import CRUX, band_tree
from test_decompositions import HOLE_IDS
from test_f34_not_on_route import assert_each_placed_once, placed, section
from test_one_view import followed_doc
from test_one_view_dominated import harder_tree
from test_routes_view import REPO, render_tree, two_routes

from opn_site import model, one_view, render

PAGE = f"problems/{TARGET}/index.html"


def test_section_two_stands_when_every_statement_is_on_a_route(tmp_path: Path) -> None:
    root = two_routes(tmp_path / "g")
    page = render_tree(root)[PAGE]  # writes the products the site is loaded from
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    r = render.Renderer(site, repo_url=REPO)
    body = r.not_on_route(tv, frozenset(tv.nodes))
    assert body == (
        '<section class="off-route">'
        '<h2 id="not-on-route"><span class="sec">§2</span> Not on a route</h2>'
        '<p class="cue">Every statement is on a route.</p></section>'
    )
    assert section(page) is not None
    nav = re.search(r'<nav class="onpage".*?</nav>', page, re.S)
    assert nav is not None and 'href="#not-on-route"' in nav.group(0)
    order = [page.index(f'<span class="sec">§{n}</span>') for n in range(1, 7)]
    assert order == sorted(order), "the section numbers never skip"
    assert_each_placed_once(root, page)


def test_a_harder_routes_statements_are_on_a_route(tmp_path: Path) -> None:
    root = harder_tree(tmp_path / "g")
    page = render_tree(root)[PAGE]
    assert_each_placed_once(root, page)
    assert not set(HOLE_IDS) & set(placed(page)), "a harder route's statements are on a route"


def test_on_a_route_is_what_some_route_of_the_picker_draws() -> None:
    doc = followed_doc()
    d = one_view.drawing(doc, [], href={})
    lays = re.search(r">(.*)</script>", d.layouts_json, re.S)
    assert lays is not None
    ends = [
        unescape(v)
        for v in re.findall(r'<g class="sel-node kind-leaf[^"]*" data-view="([^"]+)"', d.selector)
    ]
    assert ends
    import json  # noqa: PLC0415

    drawn = {
        n
        for view in ends
        for n in json.loads(lays.group(1).replace("<\\/", "</"))[view]["nodes"]
        if "@" not in n
    }
    assert d.on_route == frozenset(drawn)
    every = {str(n["node_id"]) for n in doc["nodes"]}
    assert every - d.on_route, "the fixture has a statement only a finished proof rests on"


def test_pieces_of_a_finished_proof_are_told_apart() -> None:
    deps = {"t": ["a", "b"], "a": ["a1"], "a1": ["a2"], "b": ["b1"], "u": []}
    proved = {"a", "a1", "a2"}
    off = {"a1", "a2", "b1", "u"}
    assert render.beneath_proved(off, deps, proved) == {"a1", "a2"}


def test_a_used_statement_says_which_route_uses_it(tmp_path: Path) -> None:
    page = render_tree(band_tree(tmp_path / "g"))[PAGE]
    body = section(page)
    assert body is not None
    note = re.search(r'<p class="also-used">(.*?)</p>', body, re.S)
    assert note is not None, "the crux a route's statement uses says so"
    link = re.search(
        r'also used by <a href="#view=([^"]+)" class="route-ref">(Route \d+)</a>', note.group(1)
    )
    assert link is not None, note.group(1)
    ends = re.findall(r'<g class="sel-node kind-leaf[^"]*" data-view="([^"]+)"', page)
    assert unescape(link.group(1)) in {unescape(e) for e in ends}
    group = body[: body.index(note.group(0))]
    assert f'data-node="{CRUX}"' in group[group.rindex('<div class="off-group"') :]
