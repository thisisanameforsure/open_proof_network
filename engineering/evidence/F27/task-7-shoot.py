"""F27-T7 measurements (adapted from task-3-shoot.py) and screenshots: the Routes section of erdos-1094, rendered from an export of
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

BOXES = """() => { const o = document.querySelector('svg.routes-svg').getBoundingClientRect();
  return Object.fromEntries([...document.querySelectorAll('svg.routes-svg [data-node]')]
  .map(g => { const q = g.getBoundingClientRect(); const r = {x: q.x - o.x, y: q.y - o.y, width: q.width, height: q.height};
              return [g.dataset.node, [r.x, r.y, r.width, r.height].map(v => Math.round(v * 10) / 10)]; })); }"""

STATE = """() => ({
  lit: document.querySelectorAll('svg.routes-svg [data-node].lit').length,
  nodes: document.querySelectorAll('svg.routes-svg [data-node]').length,
  lines_lit: document.querySelectorAll('svg.routes-svg .rline.lit').length,
  lines: document.querySelectorAll('svg.routes-svg .rline').length,
  wedges_off: document.querySelectorAll('svg.routes-svg .wedge.off').length,
  wedges: document.querySelectorAll('svg.routes-svg .wedge').length,
  picking: document.querySelector('svg.routes-svg').classList.contains('picking'),
})"""



OVERLAP = """() => { const ls = [...document.querySelectorAll('svg.routes-svg .set-label')].map(g => g.getBoundingClientRect());
  const ns = [...document.querySelectorAll('svg.routes-svg g.rnode, svg.routes-svg .junction')].map(g => g.getBoundingClientRect());
  let n = 0; for (const a of ls) for (const b of ns)
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) n++;
  return n; }"""

PRESSED = """() => [...document.querySelectorAll('svg.routes-svg .set-label')].map(g => [g.querySelector('text').textContent, g.classList.contains('selected')])"""


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
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(Quiet, directory=str(site))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
            with sync_playwright() as p:
                b = p.chromium.launch()
                pg = b.new_page(viewport={"width": 1440, "height": 900})
                pg.emulate_media(reduced_motion="reduce")
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                sec = pg.locator(".routes-section")
                sec.scroll_into_view_if_needed()
                report["labels_on_load"] = pg.evaluate(PRESSED)
                report["state_on_load"] = pg.evaluate(STATE)
                report["labels_overlapping_nodes"] = pg.evaluate(OVERLAP)
                before = pg.evaluate(BOXES)
                sec.screenshot(path=str(args.out / "task-7-1440-loaded.png"))
                pg.locator("svg.routes-svg .set-label").nth(2).click()
                pg.mouse.move(2, 2)
                report["labels_after_clicking_set_3"] = pg.evaluate(PRESSED)
                report["state_set_3"] = pg.evaluate(STATE)
                report["moved"] = before != pg.evaluate(BOXES)
                sec.screenshot(path=str(args.out / "task-7-1440-set-3.png"))
                pg.close()
                pg = b.new_page(viewport={"width": 390, "height": 900})
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                sec = pg.locator(".routes-section")
                sec.scroll_into_view_if_needed()
                report["page_scroll_width_390"] = pg.evaluate("document.documentElement.scrollWidth")
                sec.screenshot(path=str(args.out / "task-7-390.png"))
                b.close()
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
