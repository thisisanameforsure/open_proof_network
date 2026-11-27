"""F34-T41 (REMINDERS-erdos-257 item 8; handoff §3.4.2, mockups ``New-Erdos257``,
``-List``): "Retire" on the drawn route's header, for a steward of the problem or a curator, as well
as on each route of the list (F31-Q18, unchanged).

Under the "Figure 1 · the selected route" caption the page carries one hidden group per numbered
end, holding the same ``.retire-act`` controls as that set's row of the table (one per
decomposition the route goes through); graph.js shows the group of the route drawn, and shelve.js
fills its controls for a signed-in steward or curator only (F31-T11). With no service address
there is no group at all.

The browser half runs with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_retire_header.py``
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from harness import TARGET
from test_shelving_controls import (  # noqa: F401 — the shelving test's site and fake service
    FakeService,
    pages,
    served,
    site,
    static_pages,
)

PAGE = f"problems/{TARGET}/index.html"


def groups(page: str) -> dict[str, str]:
    return dict(
        re.findall(r'<div class="figure-retire" data-view="([^"]+)" hidden>(.*?)</div>', page, re.S)
    )


def test_each_numbered_end_has_its_routes_retire_controls(pages: dict[str, str]) -> None:  # noqa: F811
    page = pages[PAGE]
    found = groups(page)
    ends = re.findall(r'<g class="sel-node kind-leaf[^"]*" data-view="([^"]+)"', page)
    assert ends and set(found) == set(ends), (sorted(found), ends)
    assert any('class="retire-act"' in g for g in found.values()), found


def test_no_service_no_header_controls(static_pages: dict[str, str]) -> None:  # noqa: F811
    assert 'class="figure-retire"' not in static_pages[PAGE]


def test_a_steward_sees_retire_on_the_drawn_routes_header(served: str) -> None:  # noqa: F811
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(served + f"/problems/{TARGET}/")
        pg.wait_for_selector(".figure-retire:not([hidden]) .retire-act button", timeout=10000)
        drawn = pg.evaluate("document.querySelector('svg.dag').dataset.view")
        shown = pg.evaluate(
            "[...document.querySelectorAll('.figure-retire:not([hidden])')]"
            ".map(g => g.dataset.view)"
        )
        label = pg.locator(".figure-retire:not([hidden]) .retire-act button").first.inner_text()
        pg.locator(".figure-cap").scroll_into_view_if_needed()
        box = pg.locator(".figure-cap").bounding_box()
        assert box is not None
        evidence = Path(__file__).resolve().parents[2] / "engineering/evidence/F34"
        pg.screenshot(
            path=str(evidence / "task-41-header-steward-1440.png"),
            clip={"x": box["x"] - 20, "y": box["y"] - 20, "width": 700, "height": 160},
        )
        b.close()
    assert shown == [drawn.split("~")[0]], (shown, drawn)
    assert label == "Retire this route"
