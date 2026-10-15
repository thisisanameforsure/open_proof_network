"""F27-T3 measurements and screenshots: the Routes section of erdos-1094, rendered from an export of
the live graph (``git archive <sha>`` of the graph repository into ``--live-graph``).

Measures, with Playwright: every statement label's drawn box (``getBBox``) against its pill
(``rect.pill``), in the drawing's own coordinates; every node's box before, during and after a
selection; and the document's scroll width at 390. Captures the section at 1440 in the light and
the dark colour scheme (the site has one theme, so the two should match), at 390, and at 1440 with
the first set selected. Also lists which live problem pages carry a Routes section.

    PYTHONPATH=gate:gate/tests:site:site/tests \\
        uv run --frozen --with playwright python engineering/evidence/F27/task-3-shoot.py \\
        --out engineering/evidence/F27 --live-graph DIR --commit SHA
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import socketserver
import tempfile
import threading
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from opn_site import model, render

TARGET = "erdos-1094"

LABELS = """() => [...document.querySelectorAll('svg.routes-svg g.rnode')].map(g => {
  const rect = g.querySelector('rect.pill'), text = g.querySelector('text');
  const t = text.getBBox(), w = parseFloat(rect.getAttribute('width'));
  const ring = g.querySelector('circle.ring').getBBox();
  return {node: g.dataset.node, text_right: +(t.x + t.width).toFixed(1), pill: w,
          text_left: +t.x.toFixed(1), ring_right: +(ring.x + ring.width).toFixed(1),
          over: t.x + t.width > w - 4 || ring.x + ring.width > t.x};
})"""

BOXES = """() => Object.fromEntries([...document.querySelectorAll('svg.routes-svg [data-node]')]
  .map(g => { const r = g.getBoundingClientRect();
              return [g.dataset.node, [r.x, r.y, r.width, r.height].map(v => Math.round(v * 10) / 10)]; }))"""

STATE = """() => ({
  lit: document.querySelectorAll('svg.routes-svg [data-node].lit').length,
  nodes: document.querySelectorAll('svg.routes-svg [data-node]').length,
  lines_lit: document.querySelectorAll('svg.routes-svg .rline.lit').length,
  lines: document.querySelectorAll('svg.routes-svg .rline').length,
  wedges_off: document.querySelectorAll('svg.routes-svg .wedge.off').length,
  wedges: document.querySelectorAll('svg.routes-svg .wedge').length,
  picking: document.querySelector('svg.routes-svg').classList.contains('picking'),
})"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--live-graph", type=Path, required=True)
    ap.add_argument("--commit", required=True)
    args = ap.parse_args()
    files = render.render_site(
        model.load_site(args.live_graph, args.commit), repo_url="https://github.com/example/graph"
    )
    report: dict[str, Any] = {"graph_commit": args.commit}
    report["pages_with_routes"] = sorted(
        m.group(1)
        for path, html in files.items()
        if (m := re.fullmatch(r"problems/([^/]+)/index\.html", path))
        and 'class="routes-section"' in html
    )
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(Quiet, directory=str(site))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
            with sync_playwright() as p:
                b = p.chromium.launch()
                for scheme in ("dark", "light"):
                    pg = b.new_page(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
                    pg.emulate_media(reduced_motion="reduce")
                    pg.goto(url)
                    pg.wait_for_load_state("networkidle")
                    sec = pg.locator(".routes-section")
                    sec.scroll_into_view_if_needed()
                    sec.screenshot(path=str(args.out / f"task-3-1440-{scheme}.png"))
                    if scheme == "dark":
                        labels = pg.evaluate(LABELS)
                        report["labels"] = {
                            "count": len(labels),
                            "overflowing": [x for x in labels if x["over"]],
                            "tightest": min(x["pill"] - x["text_right"] for x in labels),
                        }
                        before = pg.evaluate(BOXES)
                        row = pg.locator("tr.set-row").nth(0)
                        row.click()
                        pg.mouse.move(2, 2)
                        report["selected_set_1"] = pg.evaluate(STATE)
                        report["moved_on_select"] = before != pg.evaluate(BOXES)
                        sec.screenshot(path=str(args.out / "task-3-1440-selected.png"))
                        pg.locator("tr.set-row").nth(1).hover()
                        report["hover_set_2_while_1_selected"] = pg.evaluate(STATE)
                        pg.mouse.move(2, 2)
                        pg.keyboard.press("Escape")
                        report["cleared"] = pg.evaluate(STATE)
                        report["moved_after_clear"] = before != pg.evaluate(BOXES)
                        pg.locator("button.routes-fewest").click()
                        report["fewest_open_first"] = {
                            "order": pg.eval_on_selector_all(
                                "tr.set-row", "rs => rs.map(r => r.dataset.index)"
                            ),
                            "selected": pg.eval_on_selector_all(
                                "tr.set-row[aria-selected=true]",
                                "rs => rs.map(r => r.dataset.index)",
                            ),
                        }
                    pg.close()
                pg = b.new_page(viewport={"width": 390, "height": 900})
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                sec = pg.locator(".routes-section")
                sec.scroll_into_view_if_needed()
                report["at_390"] = pg.evaluate(
                    "() => { const s = document.querySelector('.routes-scroll');"
                    " const t = document.querySelector('.routes-table-wrap');"
                    " const r = document.querySelector('svg.routes-svg g.root').getBoundingClientRect();"
                    " const b = s.getBoundingClientRect();"
                    " return {page_scroll_width: document.documentElement.scrollWidth,"
                    " drawing_scroll_left: s.scrollLeft,"
                    " root_in_view: r.left >= b.left && r.right <= b.right,"
                    " drawing_box: [s.scrollWidth, s.clientWidth],"
                    " table_box: [t.scrollWidth, t.clientWidth]}; }"
                )
                sec.screenshot(path=str(args.out / "task-3-390.png"))
                pg.close()
                b.close()
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
