"""F04-T57 screenshots: the home page rendered from the live graph, at 1440 and 390 px, and the
live site's home page as it stood before (the "before" shot). At 390 px the page must not scroll
sideways; every record row and all six lines must be on screen in the full-page shot.

    PYTHONPATH=gate:site uv run --frozen python -m opn_site.cli render \
        --graph <detached graph worktree at origin/main> --commit <its sha> --out <site dir>
    uv run --frozen --with playwright python engineering/evidence/F04/task-57-shoot.py \
        --site <site dir> --out engineering/evidence/F04
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

LIVE = "https://openproofnetwork.org/"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:  # port 0: never collide
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{httpd.server_address[1]}/"
        report: dict[str, object] = {}
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in (1440, 390):
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.goto(url, wait_until="networkidle")
                page.screenshot(path=str(args.out / f"task-57-home-{width}.png"), full_page=True)
                report[f"after-{width}"] = page.evaluate(
                    """() => ({
                      scrollWidth: document.documentElement.scrollWidth,
                      innerWidth: window.innerWidth,
                      h1: document.querySelector('h1').textContent,
                      rules: document.querySelectorAll('.rule-pair').length,
                      rows: [...document.querySelectorAll('.pulse-row')].map(r => r.innerText),
                      doors: [...document.querySelectorAll('.doors .kicker')].map(k => k.textContent),
                      drawing: !!document.querySelector('#worked svg.dag'),
                      hidden: [...document.querySelectorAll('.pulse-row, .rule-pair, .doors .card')]
                        .filter(e => !e.checkVisibility()).length,
                    })"""
                )
                page.close()
            before = browser.new_page(viewport={"width": 1440, "height": 900})
            before.goto(LIVE, wait_until="networkidle")
            before.screenshot(path=str(args.out / "task-57-before-1440.png"), full_page=True)
            browser.close()
        httpd.shutdown()
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
