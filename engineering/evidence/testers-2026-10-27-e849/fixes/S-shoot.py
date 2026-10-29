"""Fixer S screenshots (testers 2026-10-27, B-F3 and D-F-D4), from the live graph rendered locally.

The server stands in for the distribution: a directory serves its ``index.html`` (the viewer
function) and a missing path answers 404 with ``/404.html`` (the template's error response).

    PYTHONPATH=gate:site uv run --frozen python -m opn_site.cli render \
        --graph <graph clone at origin/main> --commit <its sha> --out <site dir>
    uv run --frozen --with playwright python \
        engineering/evidence/testers-2026-10-27-e849/fixes/S-shoot.py --site <site dir> --out <dir>
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

GUESSED = "problems/erdos-849/variant-3969f1f7--h2--h1/"
PARTIAL = "variant-0691f5bb"


class Distribution(http.server.SimpleHTTPRequestHandler):
    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        if code != 404:
            super().send_error(code, message, explain)
            return
        body = (Path(self.directory) / "404.html").read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    handler = functools.partial(Distribution, directory=str(args.site))
    report: dict[str, object] = {}
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:  # port 0: never collide
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{httpd.server_address[1]}/"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            resp = page.goto(url + "no/such/page/", wait_until="networkidle")
            report["missing"] = {
                "status": resp.status if resp else None,
                "h1": page.locator("main h1, h1").first.inner_text(),
                "home_section": page.get_by_text("Lately on the record").count(),
                "links": page.eval_on_selector_all("main a", "as => as.map(a => a.getAttribute('href'))"),
            }
            page.screenshot(path=str(args.out / "S-not-found-1440.png"), full_page=True)

            page.goto(url + GUESSED, wait_until="networkidle")
            page.wait_for_url("**/problems/erdos-849/#node=*")
            panel = page.locator('.card.panel[data-node="variant-3969f1f7--h2--h1"]')
            report["guessed"] = {
                "landed": page.url.removeprefix(url),
                "panel_visible": panel.is_visible(),
            }
            panel.scroll_into_view_if_needed()
            page.screenshot(path=str(args.out / "S-guessed-path-lands-1440.png"))

            page.goto(url + f"problems/erdos-849/#node={PARTIAL}", wait_until="networkidle")
            panel = page.locator(f'.card.panel[data-node="{PARTIAL}"]')
            panel.scroll_into_view_if_needed()
            report["partial"] = {
                "panel_visible": panel.is_visible(),
                "note": panel.locator(".panel-note").first.inner_text(),
            }
            panel.screenshot(path=str(args.out / "S-partial-panel.png"))
            browser.close()
        httpd.shutdown()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
