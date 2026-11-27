"""F34 round 2 evidence: §1 of a problem page on the live graph's render, in each state the
round's decisions name, at 1440 and 390, with what the page says measured beside each capture.

    PYTHONPATH=gate:site:api uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/shoot_round2.py <rendered dir> <out dir> <problem> [state...]

<rendered dir> is a site rendered from the live graph by this branch. States: tree (as the page
opens), list (the List tab), harder (harder routes shown, Tree), harder-list, hard-route (a
harder route drawn), page (the whole page), scrolled (1400px into the figure), tapped (a phone,
a row of the outline tapped). Prints one JSON line per state and width.
"""

import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

src, out, problem = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
states = sys.argv[4:] or ["tree", "list", "harder", "harder-list", "hard-route"]

MEASURE = """() => {
  const svg = document.querySelector('svg.dag:not(.band)');
  const lays = JSON.parse(document.getElementById('graph-layouts').textContent);
  const view = svg.dataset.view;
  const junction = new Set([...svg.querySelectorAll('g.junction')].map(g => g.dataset.node));
  let boxes = 0;
  for (const id of Object.keys(lays[view].nodes)) {
    if (junction.has(id)) continue;
    const fold = id.startsWith('fold:') ? svg.querySelector(`[data-node="${id}"]`) : null;
    if (id.startsWith('fold:') && !fold) continue;
    boxes += fold ? parseInt(fold.getAttribute('aria-label'), 10) : 1;
  }
  const shown = s => [...document.querySelectorAll(s)].filter(e => e.checkVisibility());
  const picker = shown('svg.selector')[0];
  const ends = picker ? [...picker.querySelectorAll('g.sel-node')] : [];
  const parents = new Set(picker ? [...picker.querySelectorAll('path.sel-edge')].map(p => p.dataset.from) : []);
  const leaves = ends.filter(g => !parents.has(g.dataset.key));
  return {
    view, boxes,
    drawnBelow: (document.querySelector('.drawn-below') || {textContent: ''}).textContent,
    visibleStatementBoxes: shown('svg.dag[data-view] g.node:not(.off-view)').length,
    pickerEnds: leaves.length,
    numberedEnds: leaves.filter(g => g.classList.contains('kind-leaf')).length,
    harderEnds: leaves.filter(g => g.classList.contains('harder')).length,
    listRows: shown('li.route-row').length,
    harderLink: (document.querySelector('button.harder-link') || {textContent: null}).textContent,
    table: document.querySelectorAll('table.routes-table').length,
    scrollWidth: document.documentElement.scrollWidth,
  };
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def enter(pg, state: str) -> None:
    link = pg.locator("button.harder-link")
    if state in ("harder", "harder-list", "hard-route") and link.count():
        link.click()
        pg.wait_for_timeout(300)
    if state in ("list", "harder-list"):
        pg.locator('.route-tabs [aria-controls="sets-list"]').click()
    if state == "hard-route":
        end = pg.locator("svg.harder-picker g.sel-node.harder").first
        if end.count():
            end.click()
            pg.wait_for_timeout(1500)
    pg.mouse.move(2, 2)  # off the picker: a hover's tooltip is not part of the state
    pg.wait_for_timeout(400)


with socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=src)) as srv:
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    with sync_playwright() as p:
        b = p.chromium.launch()
        for state in states:
            for width in {"tapped": (390,), "scrolled": (1440,)}.get(state, (1440, 390)):
                pg = b.new_page(viewport={"width": width, "height": 1000})
                pg.goto(base + f"/problems/{problem}/")
                pg.wait_for_timeout(900)
                enter(pg, state)
                shot = str(out / f"round2-{problem}-{state}-{width}.png")
                if state == "page":  # the whole page as it opens
                    pg.screenshot(path=shot, full_page=True)
                elif state == "scrolled":  # 1400px into the figure: is the panel still beside it?
                    top = pg.evaluate(
                        "document.querySelector('.graph-grid').getBoundingClientRect().top"
                        " + window.scrollY"
                    )
                    pg.evaluate("y => window.scrollTo(0, y)", top + 1400)
                    pg.wait_for_timeout(400)
                    pg.screenshot(path=shot)
                elif state == "tapped":  # a phone: the second row of the outline tapped
                    row = pg.locator("ol.route-outline > li:not([hidden]) > a[data-node]").nth(1)
                    if row.count() and row.is_visible():
                        row.click()
                        pg.wait_for_timeout(400)
                    pg.locator("ol.route-outline").scroll_into_view_if_needed()
                    pg.screenshot(path=shot)
                else:
                    section = pg.locator(".statements-section").first
                    section.scroll_into_view_if_needed()
                    section.screenshot(path=shot)
                print(
                    json.dumps(
                        {"problem": problem, "state": state, "width": width, **pg.evaluate(MEASURE)}
                    )
                )
                pg.close()
        b.close()
