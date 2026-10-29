"""F04-T62 screenshots: a statement page rendered from the live graph with its Attempts fold open,
at 1440 and 390 px, showing the postmortems' words. At 390 px the page must not scroll sideways.

    PYTHONPATH=gate:site uv run --frozen python -m opn_site.cli render \
        --graph <detached graph worktree at origin/main> --commit <its sha> --out <site dir>
    uv run --frozen --with playwright python engineering/evidence/F04/task-62-shoot.py \
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

PAGE = "nodes/erdos-849/variant-3969f1f7--h2--h1--h4--h2--h3/#attempts"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        report = {}
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in (1440, 390):
                page = browser.new_page(viewport={"width": width, "height": 1100})
                page.goto(f"http://127.0.0.1:{port}/{PAGE}")
                page.wait_for_timeout(600)
                blocks = page.locator('[data-block="postmortem"]')
                first = blocks.first
                first.scroll_into_view_if_needed()
                report[width] = {
                    "postmortem_blocks": blocks.count(),
                    "visible": first.is_visible(),
                    "scroll_width": page.evaluate("document.documentElement.scrollWidth"),
                }
                first.screenshot(path=str(args.out / f"task-62-postmortem-{width}.png"))
                page.close()
            browser.close()
        httpd.shutdown()
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
