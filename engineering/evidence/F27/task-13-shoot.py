"""F27-T13 counts and screenshots on erdos-1094's problem page as F34 redesigned it: the strictly
harder routes behind a toggle of their own beside the key, and "Not on a route" (§2) not listing
them (D-25 v3.52, F34-R18). Rendered by this branch's site from the live graph.

    PYTHONPATH=gate:site:api uv run --frozen python -m opn_site.cli render --graph G --commit SHA --out DIR
    uv run --frozen --with 'playwright==1.58.0' python engineering/evidence/F27/task-13-shoot.py \\
        --site DIR --out engineering/evidence/F27
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

STATE = """() => { const svg = document.querySelector('svg.dag');
  const shown = [...svg.querySelectorAll('[data-node]')].filter(g => !g.classList.contains('off-view'));
  const t = document.querySelector('button.harder-toggle'), v = document.querySelector('button.view-toggle');
  return {view: svg.dataset.view,
          pills_shown: shown.filter(g => g.classList.contains('node')).length,
          harder_shown: shown.filter(g => g.classList.contains('harder')).length,
          harder_toggle: t && !t.hidden ? t.textContent : null,
          harder_pressed: t ? t.getAttribute('aria-pressed') : null,
          general_toggle: v && !v.hidden ? v.textContent : null,
          scroll: document.documentElement.scrollWidth, width: window.innerWidth}; }"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    page_html = (a.site / "problems" / "erdos-1094" / "index.html").read_text(encoding="utf-8")
    sec = page_html[page_html.find('id="not-on-route"') : page_html.find('<h2 id="statement"')]
    report: dict[str, object] = {
        "not_on_a_route_section": 'id="not-on-route"' in page_html,
        "not_on_a_route_statement_links": len(set(re.findall(r"/problems/erdos-1094/([^/\"]+)/", sec))),
    }
    handler = functools.partial(Quiet, directory=str(a.site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}/problems/erdos-1094/"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                pg = b.new_page(viewport={"width": width, "height": 1000})
                pg.goto(base + "#view=routes")
                pg.wait_for_load_state("networkidle")
                pg.wait_for_function("() => document.querySelector('svg.dag').dataset.view === 'routes'")
                report[f"routes-{width}"] = pg.evaluate(STATE)
                if width == 1440:
                    key = pg.locator("button.harder-toggle")
                    key.scroll_into_view_if_needed()
                    pg.screenshot(path=str(a.out / "task-13-1440-routes.png"))
                    key.click()
                    pg.wait_for_function("() => document.querySelector('svg.dag').dataset.view === 'harder'")
                    pg.wait_for_timeout(300)
                    report["harder-1440"] = pg.evaluate(STATE)
                    key.scroll_into_view_if_needed()
                    pg.screenshot(path=str(a.out / "task-13-1440-harder.png"))
                    key.click()
                    pg.wait_for_function("() => document.querySelector('svg.dag').dataset.view === 'routes'")
                    report["back-1440"] = pg.evaluate(STATE)
                else:
                    pg.screenshot(path=str(a.out / "task-13-390-routes.png"))
                pg.close()
            pg = b.new_page(viewport={"width": 1440, "height": 1000})
            pg.goto(base)
            pg.wait_for_load_state("networkidle")
            report["opening-view"] = pg.evaluate(STATE)
            b.close()
        httpd.shutdown()
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
