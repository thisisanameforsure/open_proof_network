"""F27-T13 (R14; D-25 v3.52): the problem page draws a strictly harder route only on request.

Root ``t`` with two routes: ``[a]`` and ``[a, b, p]``, ``b`` open and ``p`` proved. The second
needs everything the first needs and ``b`` besides, so it is dominated with ``b`` and ``p``.

Under F34 every statement is placed exactly once, drawn on a route or listed in "Not on a route"
(§2). A strictly harder statement is on a route, so §2 never lists it; the drawing has a view of
its own for it (F34-T48, ROUND-2 D2: ``hard/<set>``, the harder route alone), drawn when the
picker selects its numbered end; a quiet control under the picker adds those ends and counts
them. The general toggle appears only when something is on no route.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fixture
from harness import TARGET
from test_decompositions import HOLE_IDS
from test_one_view import browser, classes, element, layouts_in
from test_products import attest as gate_attest
from test_products import nodes_dir
from test_routes_view import REPO, THIRD, node, render_tree, two_routes

from opn_gate import routes
from opn_site import model, one_view, render


def harder_doc(*, stray: bool = False) -> dict[str, Any]:
    """``stray`` adds ``u``, an authored statement on no route: the general toggle's own case."""
    rows = [
        node("t", origin="authored", routes=[["t--a"], ["t--a", "t--b", "t--p"]]),
        node("t--a"),
        node("t--b"),
        node("t--p", "proved"),
    ]
    if stray:
        rows.append(node("u", origin="authored"))
    return {"schema": "graph/v16", "target_id": "t", "root": "t", "nodes": rows}


def test_a_dominated_route_has_a_view_of_its_own_and_no_set() -> None:
    g = harder_doc()
    whole = routes.read(g, [], harder=True)
    hard = [(k, s) for k, s in enumerate(whole.sets, start=1) if k > 1]
    vs = one_view.views(g, routes.read(g, []), harder_sets=hard)
    harder = {"t--b", "t--p", "t@2"}
    assert harder <= set(vs[one_view.ALL].nodes)
    assert not harder & set(vs[one_view.ROUTES].nodes)
    # F34-T48 (ROUND-2 D2): the view is the harder route alone, a leaf like any route's; the
    # ``harder`` view, every harder statement at once, is gone
    assert one_view.HARDER not in vs
    (key,) = [k for k in vs if k.startswith(one_view.HARD)]
    assert vs[key].kind == "leaf" and vs[key].index == 2
    assert set(vs[key].nodes) == {"t", "t--a", "t@2", *harder}
    lines = {(s, t) for s, t, _k in vs[key].lines}
    assert ("t@2", "t") in lines and ("t--b", "t@2") in lines
    set_views = [v for k, v in vs.items() if k == one_view.TOP or k.startswith(("sel/", "edge/"))]
    assert set_views
    assert all(not {"t--b", "t--p"} & set(v.nodes) for v in set_views)


def test_no_harder_view_when_nothing_is_dominated() -> None:
    g = harder_doc()
    g["nodes"][0] = node("t", origin="authored", routes=[["t--a"], ["t--b", "t--p"]])
    vs = one_view.views(g, routes.read(g, []))
    assert not [k for k in vs if k.startswith(one_view.HARD)]
    d = one_view.drawing(g, [], href={})
    assert d.harder == 0 and d.harder_toggle == "" and "harder" not in d.marks
    assert d.harder_selector == ""


def test_the_harder_toggle_counts_routes_statements_and_proved() -> None:
    d = one_view.drawing(harder_doc(), [], href={})
    assert d.harder == 2
    # F34-T48 (ROUND-2 D2): a quiet control that counts the ends it adds to the picker
    assert 'class="harder-link"' in d.harder_toggle and "data-view" not in d.harder_toggle
    assert "Show 1 harder route" in d.harder_toggle
    assert "Hide harder route" in d.harder_toggle
    assert d.toggle == ""  # everything else is on a route: no general toggle
    assert "harder" in d.marks
    assert "harder" in render.ROUTE_MARK_KEYS and "harder" in render.GLOSSARY_BY_KEY


def test_the_general_toggle_appears_only_for_what_is_on_no_route() -> None:
    """F34-T55 restates this: the line under the drawing counts what is on no route and links
    to §2, which lists it; the statements on strictly harder routes are behind their own
    control and are not counted; with nothing on no route there is no line."""
    d = one_view.drawing(harder_doc(stray=True), [], href={})
    assert "1 more statement is not on a route ↓" in d.toggle and "harder" not in d.toggle
    assert "Show 1 harder route" in d.harder_toggle
    assert one_view.drawing(harder_doc(), [], href={}).toggle == ""


def test_not_on_a_route_never_lists_a_strictly_harder_statement() -> None:
    """F34-R18: placed once. The strictly harder statements are on a route (behind the
    toggle); only ``u`` is on no route."""
    d = one_view.drawing(harder_doc(stray=True), [], href={})
    assert {"t--a", "t--b", "t--p"} <= d.on_route
    assert "u" not in d.on_route


def test_pills_and_junction_say_why() -> None:
    d = one_view.drawing(harder_doc(), [], href={})
    assert "harder" in classes(d.svg, "t--b") and "harder" in classes(d.svg, "t--p")
    assert "harder" not in classes(d.svg, "t--a")
    title = re.search(r"<title>(.*?)</title>", element(d.svg, "t--b")).group(1)  # type: ignore[union-attr]
    assert "strictly harder" in title
    assert "strictly harder" in element(d.svg, "t@2")


def harder_tree(tmp_path: Path) -> Path:
    """``two_routes`` (routes ``[h1, h2]`` and ``[h3]``) with ``h3`` proved: the second route
    needs nothing open, so the first, needing ``h1`` and ``h2``, is strictly harder."""
    root = two_routes(tmp_path)
    hole = nodes_dir(root) / THIRD
    statement = (hole / "Statement.lean").read_text(encoding="utf-8")
    (hole / "Proof.lean").write_text(statement.replace("sorry", "exact trivial"), encoding="utf-8")
    gate_attest(root, THIRD, n=12, footprint={"nodes": []})
    return root


def test_showing_the_harder_route_draws_nothing_until_it_is_selected(tmp_path: Path) -> None:
    """In a browser (Playwright). F34-T48 (ROUND-2 D2; the owner, 2026-11-27) restates F27-T13's
    toggle: showing the harder route adds it to the picker and leaves the figure alone; selecting
    its numbered end draws it, its holes among it; hiding the harder routes comes back."""
    with browser(harder_tree(tmp_path / "g"), tmp_path / "site") as pg:
        assert one_view.HARDER not in layouts_in(pg)
        link = pg.locator("button.harder-link")
        assert link.is_visible() and link.inner_text() == "Show 1 harder route"

        def drawn(nid: str) -> bool:
            found: bool = pg.evaluate(
                '(n) => { const g = document.querySelector(`svg.dag [data-node="${n}"]`);'
                " return !!g && !g.classList.contains('off-view'); }",
                nid,
            )
            return found

        home = pg.evaluate("document.querySelector('svg.dag').dataset.view")
        assert not drawn(HOLE_IDS[0]) and not drawn(HOLE_IDS[1]) and drawn(THIRD)
        link.click()
        pg.wait_for_selector("svg.harder-picker:not([hidden])")
        assert not drawn(HOLE_IDS[0]) and not drawn(HOLE_IDS[1]) and drawn(THIRD)
        assert link.get_attribute("aria-pressed") == "true"
        end = pg.locator("svg.harder-picker g.sel-node.harder").first
        view = end.get_attribute("data-view")
        end.click()
        pg.wait_for_function("v => document.querySelector('svg.dag').dataset.view === v", arg=view)
        assert drawn(HOLE_IDS[0]) and drawn(HOLE_IDS[1]) and not drawn(THIRD)
        link.click()
        pg.wait_for_function("v => document.querySelector('svg.dag').dataset.view === v", arg=home)
        assert not drawn(HOLE_IDS[0]) and drawn(THIRD)
        assert link.get_attribute("aria-pressed") == "false"


# -- F27-T15 (R14): the site invites work only on what the frontier offers ------------------------
# Found on the live erdos-1094 page after the re-pin, 2026-11-27: the frontier dropped 51 entries
# (69 → 18) while the header still said "69 statements open" and every strictly harder statement's
# panel and page said "Work on this statement →", a claim the service answers 409 node-dominated.


def test_the_sites_workable_statements_are_still_the_frontiers(tmp_path: Path) -> None:
    """F04-T17's one set, two readers, on a tree with a strictly harder route: ``h1`` and ``h2``
    are off the frontier, so the site neither counts them as open nor offers them."""
    root = harder_tree(tmp_path / "g")
    pages = render_tree(root)
    site = model.load_site(root, fixture.COMMIT)
    frontier = json.loads((root / "frontier.json").read_text(encoding="utf-8"))
    # This fixture's target is not claimable itself (no intake record), so every entry reads
    # ``claimable: false`` for the target's reason; what the frontier offers is what it lists.
    offered = {e["node_id"] for e in frontier["entries"]}
    assert not {HOLE_IDS[0], HOLE_IDS[1]} & offered, "guard: the route is strictly harder"
    r = render.Renderer(site, repo_url=REPO)
    tv = site.targets[TARGET]
    workable = {nid for nid, nv in tv.nodes.items() if r.node_state(nv) in render.WORKABLE_STATES}
    assert workable == offered
    assert r.open_count(tv) == len(offered)
    for hole in HOLE_IDS[:2]:
        nv = tv.nodes[hole]
        assert nv.status in render.CLAIMABLE_STATUSES, "guard: still open on the record"
        assert r.node_state(nv) == "harder"
        assert "Work on this statement" not in r.panel_action(tv, nv)
        node_page = pages[f"nodes/{TARGET}/{hole}/index.html"]
        assert "Work on this statement" not in node_page
        assert "Not offered: every route through this statement is" in node_page
        assert r.state_label(r.node_state(nv)) == "strictly harder"
