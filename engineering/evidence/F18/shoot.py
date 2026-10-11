"""F18 screenshots and measurements (the problem page's proof drawing).

Serves a rendered site, opens each problem page at desktop and phone width, selects each proof
in turn, and saves a screenshot per (page, width, proof). Measures what the eye misses
(engineering/CLAUDE.md, 2026-09-18 and 2026-09-19): the page's scrollWidth against the viewport,
every pill's label against its box, and which pills and lines each proof marks. Prints one JSON
document; exit 1 when a measurement fails.

    uv run --with playwright python engineering/evidence/F18/shoot.py \
        --site <rendered site> --out engineering/evidence/F18 --prefix task-2 \
        --page erdos-1050 --page euclid-primes
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

WIDTHS = {"desktop": 1440, "phone": 390}
MEASURE = """() => {
  const out = {scrollWidth: document.documentElement.scrollWidth, overflowing: []};
  for (const g of document.querySelectorAll('svg.dag g.node')) {
    const r = g.querySelector('rect').getBBox(), t = g.querySelector('text').getBBox();
    if (t.x < r.x || t.x + t.width > r.x + r.width) out.overflowing.push(g.dataset.node);
  }
  out.on = [...document.querySelectorAll('svg.dag g.node.on-proof')].map(g => g.dataset.node).sort();
  out.off = [...document.querySelectorAll('svg.dag g.node.off-proof')].map(g => g.dataset.node).sort();
  out.lines_on = document.querySelectorAll('svg.dag line.on-proof').length;
  out.buttons = [...document.querySelectorAll('.proof-picker button')].map(b => b.textContent);
  const picker = document.querySelector('.proof-picker');
  out.picker_width = picker ? picker.scrollWidth : null;
  out.picker_client = picker ? picker.clientWidth : null;
  return out;
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
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--page", action="append", required=True)
    ap.add_argument("--base", help="shoot a live site at this origin instead of serving --site")
    args = ap.parse_args()
    server, port = (None, 0) if args.base else serve(args.site)
    origin = args.base or f"http://127.0.0.1:{port}"
    report: dict[str, Any] = {"origin": origin, "shots": [], "ok": True}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, width in WIDTHS.items():
            page = browser.new_page(viewport={"width": width, "height": 1000})
            for problem in args.page:
                page.goto(f"{origin}/problems/{problem}/", wait_until="networkidle")
                count = page.locator(".proof-picker button").count()
                for k in range(max(count, 1)):
                    if count:
                        page.locator(f'.proof-picker button[data-proof="{k}"]').click()
                    m = page.evaluate(MEASURE)
                    shot = args.out / f"{args.prefix}-{problem}-{name}-proof{k + 1}.png"
                    page.locator(".statements-section").screenshot(path=str(shot))
                    ok = m["scrollWidth"] <= width and not m["overflowing"]
                    if m["picker_width"] is not None:
                        ok = ok and m["picker_width"] <= m["picker_client"]
                    report["ok"] = report["ok"] and ok
                    report["shots"].append(
                        {"page": problem, "width": width, "proof": k + 1, "file": shot.name, "ok": ok, **m}
                    )
            page.close()
        browser.close()
    if server is not None:
        server.shutdown()
    sys.stdout.write(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
