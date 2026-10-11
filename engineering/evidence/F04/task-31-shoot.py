"""F04-T31 screenshots and measurements: a problem resolved by a counterexample, and the Docs
state map's resolved box.

Serves a site rendered from ``site/tests/fixture.build_with_resolutions``, shoots the problem page
of ``disproved-target`` and ``ill-posed-target`` and the Problems page's cards at desktop and phone
width, and the Docs problem state map at desktop. Measures what the eye misses (engineering/
CLAUDE.md, 2026-09-19): the page's scrollWidth against the viewport, and every text in the problem
state map against the box it sits in. Prints one JSON document; exit 1 when a measurement fails.

    uv run --with playwright python engineering/evidence/F04/task-31-shoot.py \
        --site <rendered site> --out engineering/evidence/F04
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

WIDTHS = {"1440": 1440, "390": 390}
#: Each text in the problem state map whose x lies inside a box's span on the same rows must end
#: inside that box.
MEASURE_SMAP = """() => {
  const svg = document.querySelectorAll('svg.smap')[1];
  const boxes = [...svg.querySelectorAll('rect.box')].map(r => r.getBBox());
  const out = [];
  let inside = 0;
  for (const t of svg.querySelectorAll('text')) {
    const b = t.getBBox();
    const box = boxes.find(r => b.x >= r.x && b.x <= r.x + r.width && b.y >= r.y
                                && b.y + b.height <= r.y + r.height + 2);
    if (box) inside += 1;
    if (box && b.x + b.width > box.x + box.width) out.push(t.textContent);
  }
  return {inside: inside, overflowing: out};
}"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    server, port = serve(args.site)
    base = f"http://127.0.0.1:{port}"
    report: dict[str, Any] = {"pages": {}, "ok": True}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, width in WIDTHS.items():
            page = browser.new_page(viewport={"width": width, "height": 900})
            for tid in ("disproved-target", "ill-posed-target"):
                page.goto(f"{base}/problems/{tid}/")
                shot = args.out / f"task-31-{tid}-{name}.png"
                page.screenshot(path=str(shot), full_page=True)
                sw = page.evaluate("document.documentElement.scrollWidth")
                claim = page.locator("p.claimable").first.inner_text()
                report["pages"][f"{tid}@{name}"] = {"scrollWidth": sw, "claimable": claim}
                report["ok"] &= sw <= width
            page.goto(f"{base}/problems/")
            card = page.locator("#p-disproved-target")
            card.screenshot(path=str(args.out / f"task-31-card-{name}.png"))
            report["pages"][f"problems@{name}"] = {
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
                "statuses": page.eval_on_selector_all(
                    "article.problem", "els => els.map(e => [e.id, e.dataset.status])"
                ),
                "proved_count": page.locator('[data-filter="proved"] .n').inner_text(),
            }
            page.close()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{base}/docs/")
        smap = page.locator("svg.smap").nth(1)
        smap.screenshot(path=str(args.out / "task-31-docs-problem-map-1440.png"))
        overflow = page.evaluate(MEASURE_SMAP)
        report["smap_overflowing"] = overflow
        # a zero is a claim about the accessor (Log 2026-09-16): the map has 13 texts in boxes
        report["ok"] &= not overflow["overflowing"] and overflow["inside"] >= 13
        browser.close()
    server.shutdown()
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
