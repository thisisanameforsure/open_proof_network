"""F04-T55: captures of the refuting side on a rendered problem page (a local render of the live
graph with ``relation: refutes`` mocked on the crux, since the revision does not exist yet).

Usage: ``uv run --frozen --with playwright python engineering/evidence/F04/task-55-shoot.py
<site dir> <target> --out DIR --tag TAG [--refuted]``. At 1440 and 390 it captures the drawing
with the refuting set selected in the selector (the trunk and branch in ``--refute``), the
selector panel, the sets table, and with ``--refuted`` the page's head (the "disproved" words);
it prints the measured strokes, the selected view and the head's words.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


STATE = """() => {
  const main = document.querySelector('svg.dag:not(.band)');
  const vis = el => getComputedStyle(el).display !== 'none';
  return {
    view: main.getAttribute('data-view'),
    shown: [...main.querySelectorAll('g.node[data-node]')].filter(vis).map(g => g.getAttribute('data-node')),
    trunk: [...main.querySelectorAll('path.edge.relation')].map(e => [e.getAttribute('class'), vis(e), getComputedStyle(e).stroke]),
    selEdges: [...document.querySelectorAll('svg.selector .sel-edge')].map(e => [e.getAttribute('data-to'), getComputedStyle(e).stroke]),
    rows: [...document.querySelectorAll('tr.set-row')].map(r => [r.getAttribute('class'), r.cells[0].innerText.split('\\n')[0]]),
    head: (k => k ? k.innerText.trim() : null)(document.querySelector('p.claimable')),
    how: (k => k ? k.innerText.trim() : null)(document.querySelector('.panel:not([hidden]) .how-line')),
    scroll: [document.documentElement.scrollWidth, window.innerWidth],
  };
}"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=Path)
    ap.add_argument("target")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--refuted", action="store_true")
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    tag = args.tag or args.target
    report: dict[str, Any] = {}
    handler = functools.partial(Quiet, directory=str(args.site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{args.target}/"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                ctx = b.new_context(viewport={"width": width, "height": 2400})
                pg = ctx.new_page()
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                name = f"task-55-{tag}-{width}"
                r: dict[str, Any] = {"rest": pg.evaluate(STATE)}
                if args.refuted:
                    pg.set_viewport_size({"width": width, "height": 900})
                    pg.screenshot(path=str(out / f"{name}-head.png"))
                else:
                    leaf = pg.locator('svg.selector .sel-node.side-refutes[data-view]').first
                    leaf.click()
                    pg.mouse.move(5, 5)
                    time.sleep(1.2)
                    r["refuting"] = pg.evaluate(STATE)
                    pg.locator(".dag-wrap").screenshot(path=str(out / f"{name}-refuting-set.png"))
                    pg.locator(".selector-wrap").screenshot(path=str(out / f"{name}-selector.png"))
                    table = pg.locator(".routes-table-wrap")
                    if table.count():
                        table.scroll_into_view_if_needed()
                        table.screenshot(path=str(out / f"{name}-table.png"))
                report[str(width)] = r
                ctx.close()
            b.close()
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
