"""F27-T13 screenshots and counts: erdos-1094's problem page with strictly harder routes off the
routes view (D-25 v3.51), rendered from graph 257feba234 by this branch's site.

    uv run --frozen --with 'playwright==1.58.0' python engineering/evidence/F27/task-13-shoot.py \\
        --site DIR --out engineering/evidence/F27
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

COUNTS = """() => { const svg = document.querySelector('svg.dag');
  const shown = [...svg.querySelectorAll('[data-node]')].filter(g => !g.classList.contains('off-view'));
  return {pills_shown: shown.filter(g => g.classList.contains('node')).length,
          junctions_shown: shown.filter(g => g.classList.contains('junction')).length,
          harder_shown: shown.filter(g => g.classList.contains('harder')).length,
          harder_total: svg.querySelectorAll('.harder').length,
          toggle: document.querySelector('.view-toggle')?.textContent,
          sets: document.querySelectorAll('[data-set]').length,
          scroll: document.documentElement.scrollWidth, width: window.innerWidth}; }"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(a.site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{port}/problems/erdos-1094/"
        report: dict[str, object] = {"url_path": "/problems/erdos-1094/"}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                page = b.new_page(viewport={"width": width, "height": 1100})
                page.goto(url)
                page.wait_for_timeout(800)
                svg = page.locator("svg.dag").first
                svg.scroll_into_view_if_needed()
                report[f"default-{width}"] = page.evaluate(COUNTS)
                page.screenshot(path=str(a.out / f"task-13-{width}-default.png"), full_page=False)
                if width == 1440:
                    page.locator(".view-toggle").first.click()
                    page.wait_for_timeout(800)
                    report["toggled-1440"] = page.evaluate(COUNTS)
                    svg.scroll_into_view_if_needed()
                    page.screenshot(path=str(a.out / "task-13-1440-toggled.png"), full_page=False)
                page.close()
            b.close()
        httpd.shutdown()
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
