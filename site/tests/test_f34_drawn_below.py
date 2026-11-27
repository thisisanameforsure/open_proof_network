"""F34-T33 (REMINDERS-erdos-257 item 5; handoff §3.4.2, mockup ``New-Erdos257``): the page says
which route the drawing shows — "Drawn below ↓ Route 2 · …" under the route selector, and the
drawing captioned "Figure 1 · the selected route" with the same route's name.

Each numbered end of the selector carries its route's name (``data-route``: "Route n", then the
approach its last choice took, if any) and its counts (``data-count``); the page is rendered with
the opening route's words, so it reads right with no script, and graph.js rewrites both lines
whenever another route is drawn.

The browser half runs with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest site/tests/test_f34_drawn_below.py``
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from collections.abc import Iterator
from html import unescape
from pathlib import Path

import pytest
from harness import TARGET
from test_routes_view import render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"


def ends(page: str) -> dict[str, tuple[str, str]]:
    """Each numbered end's view key, route name and counts."""
    return {
        m["view"]: (unescape(m["route"]), unescape(m["count"]))
        for m in re.finditer(
            r'<g class="sel-node kind-leaf[^"]*" data-view="(?P<view>[^"]+)"[^>]*'
            r'data-route="(?P<route>[^"]+)" data-count="(?P<count>[^"]+)"',
            page,
        )
    }


def test_every_numbered_end_names_its_route(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    named = ends(page)
    assert len(named) >= 2
    for route, count in named.values():
        assert re.match(r"Route \d+( · .+)?$", route), route
        assert re.match(r"\d+ statements?, \d+ open$", count), count


def test_the_page_opens_saying_which_route_is_drawn(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    home = re.search(r'<svg class="dag" data-home="([^"]+)"', page)
    assert home is not None
    route, count = ends(page)[home.group(1)]
    below = re.search(r'<p class="drawn-below">Drawn below ↓ <strong>(.*?)</strong></p>', page)
    assert below is not None and unescape(below.group(1)) == f"{route} · {count}"
    cap = re.search(
        r'<p class="figure-cap"><span class="figure-n">Figure 1 · the selected route</span> '
        r"<strong>(.*?)</strong></p>",
        page,
    )
    assert cap is not None and unescape(cap.group(1)) == route
    assert page.index('class="drawn-below"') < page.index('class="figure-cap"')


# -- in a browser ---------------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-drawn-below")
    out = tmp / "site"
    render.write(render_tree(two_routes(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def test_choosing_another_route_rewrites_both_lines(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(300)
        home = pg.evaluate("document.querySelector('svg.dag').dataset.view")
        other = pg.locator(f'svg.selector g.kind-leaf:not([data-view="{home}"])').first
        want = (other.get_attribute("data-route"), other.get_attribute("data-count"))
        view = other.get_attribute("data-view")
        other.click()
        pg.wait_for_function(
            f"document.querySelector('svg.dag').dataset.view === {view!r}", timeout=5000
        )
        got = pg.evaluate(
            "[document.querySelector('.drawn-below strong').textContent,"
            " document.querySelector('.figure-cap strong').textContent]"
        )
        b.close()
    assert got == [f"{want[0]} · {want[1]}", want[0]], (got, want)


def test_a_route_is_named_by_the_gist_of_its_approach() -> None:
    """The mockup names a route by a short phrase ("Route 2 · fifteen special cases plus the
    rest"); a route's approach is often a paragraph, so its name takes the approach up to the
    first semicolon, and at most a line of it."""
    from opn_site import one_view  # noqa: PLC0415

    long = (
        "greedy walk; a representation of a rational is greedy (bookkeeping), and the open core "
        "is that a greedy set summing to a rational is finite"
    )
    assert one_view.route_gist(long) == "greedy walk"
    assert one_view.route_gist("route 2 of and-swap-reassoc") == "route 2 of and-swap-reassoc"
    word = "case split over the fifteen special cases already on the graph plus what is left over"
    gist = one_view.route_gist(word)
    assert gist.endswith("…") and len(gist) <= one_view.ROUTE_GIST_MAX + 1
    assert word.startswith(gist.removesuffix("…").rstrip())
