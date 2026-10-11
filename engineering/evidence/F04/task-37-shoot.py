"""F04-T37 screenshots and measurements: the circularity label on a local render of the live
graph whose products were rewritten as the v3.35 gate writes them (graph/v6, frontier/v5; the
four live nodes under merged claims labelled and back on the frontier).

Serves the rendered site, shoots the node page's label, the problem page's key and drawing, the
listing's row, at 1440 and at 390, and *measures* rather than eyeballs: every circular mark's
text sits inside its tab (getBBox against the rect), the key's swatch has the tab's size, and no
page scrolls sideways at 390 (scrollWidth, the 2026-09-18 lesson). Prints a JSON report.

    uv run --with playwright python engineering/evidence/F04/task-37-shoot.py \
        --site <rendered site> --out engineering/evidence/F04
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

NODE = "/nodes/erdos-69/erdos-69--h2-v2--h1-v2--h4/"
PROBLEM = "/problems/erdos-69/"
LISTING = "/problems/"
MEASURE_MARKS = """
() => Array.from(document.querySelectorAll('.dag .circular-mark')).map(g => {
  const r = g.querySelector('rect').getBBox(), t = g.querySelector('text').getBBox();
  const pill = g.closest('.node');
  return {node: pill.dataset.node, status: [...pill.classList].find(c => c.startsWith('status-')),
          inside: t.x >= r.x && t.y >= r.y && t.x + t.width <= r.x + r.width && t.y + t.height <= r.y + r.height,
          rect: [r.width, r.height], text: [Math.round(t.width*10)/10, Math.round(t.height*10)/10]};
})
"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None  # type: ignore[attr-defined]
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def shot(page: Any, selector: str, path: Path) -> str:
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    el.screenshot(path=str(path))
    return " ".join(el.inner_text().split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    server, port = serve(args.site)
    base = f"http://127.0.0.1:{port}"
    report: dict[str, Any] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (1440, 390):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(base + NODE, wait_until="networkidle")
            report[f"node@{width}"] = {
                "lead": " ".join(page.locator("p.lead").first.inner_text().split()),
                "label": shot(page, "p.circular-label", args.out / f"task-37-node-label-{width}.png"),
                "not_claimable_on_page": "Not claimable" in page.content(),
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
            }
            page.goto(base + PROBLEM, wait_until="networkidle")
            report[f"problem@{width}"] = {
                "key": shot(page, ".dag-legend", args.out / f"task-37-problem-key-{width}.png"),
                "marks": page.evaluate(MEASURE_MARKS),
                "key_swatch": page.evaluate(
                    "(() => { const d = document.querySelector('.dag-legend .dot-circular');"
                    " const r = d.getBoundingClientRect(); return [r.width, r.height]; })()"
                ),
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
            }
            page.locator(".dag").first.scroll_into_view_if_needed()
            page.locator(".dag").first.screenshot(path=str(args.out / f"task-37-problem-graph-{width}.png"))
            # The labelled hole's panel, selected as the page's script selects it.
            page.goto(base + PROBLEM + "#node=erdos-69--h2-v2--h1-v2--h4", wait_until="networkidle")
            page.wait_for_timeout(300)
            report[f"panel@{width}"] = shot(
                page, '.panel[data-node="erdos-69--h2-v2--h1-v2--h4"]',
                args.out / f"task-37-problem-panel-{width}.png",
            )[:400]
            page.goto(base + LISTING, wait_until="networkidle")
            page.evaluate("document.querySelectorAll('#p-erdos-69 details.more').forEach(d => d.open = true)")
            rows = page.locator('#p-erdos-69 .stmt[data-circular="1"]')
            report[f"listing@{width}"] = {
                "labelled_rows": rows.count(),
                "row": shot(page, '#p-erdos-69 .stmt[data-circular="1"]', args.out / f"task-37-listing-row-{width}.png"),
                "workable": [rows.nth(i).get_attribute("data-workable") for i in range(rows.count())],
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
            }
            page.close()
        browser.close()
    server.shutdown()
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
