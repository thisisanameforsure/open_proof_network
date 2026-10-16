"""F04-T53 screenshots and measurements: the fixture tree with a merged circularity claim on
``and-swap-reassoc--h1`` (ancestor ``and-swap-reassoc``), rendered by ``task-53-render.py`` once
with origin/main's site ("before", the v3.35 label on the hole's row) and once with this branch's
("after", graph/v10).

For each render, at 1440 and at 390 (a fresh browser context per site and width, so no stylesheet
is served from cache), shoots the hole's page head and its defect-claims block, the problem
page's key, drawing and the hole's panel, and the listing's row for the hole; and *measures*: the
key's words, every circularity element left in the DOM, and the page's scrollWidth against the
viewport (no sideways scroll at 390; the 2026-09-18 lesson). Prints a JSON report.

    uv run --frozen --with playwright python engineering/evidence/F04/task-53-shoot.py \
        --site before=<dir> --site after=<dir> --out engineering/evidence/F04
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

TARGET = "propositional"
HOLE = "and-swap-reassoc--h1"
NODE = f"/nodes/{TARGET}/{HOLE}/"
PROBLEM = f"/problems/{TARGET}/"
LISTING = "/problems/"
CIRCULAR_DOM = """
() => ({
  circular_mark: document.querySelectorAll('.circular-mark').length,
  circular_label: document.querySelectorAll('.circular-label').length,
  circular_note: document.querySelectorAll('.circular-note').length,
  dot_circular: document.querySelectorAll('.dot-circular').length,
  data_circular: document.querySelectorAll('[data-circular]').length,
  proves_chip: document.querySelectorAll('.stmt .proves').length,
  arrow_in_svg: [...document.querySelectorAll('svg')]
    .filter(s => s.textContent.includes('⇒')).length,
  text_proves_an_ancestor: document.body.innerText.includes('proves an ancestor'),
})
"""
LEGEND_WORDS = """
() => [...document.querySelectorAll('.dag-legend .term')].map(t => {
  const c = t.cloneNode(true); c.querySelectorAll('.term-card').forEach(x => x.remove());
  return c.innerText.trim();
}).filter(Boolean)
"""
OVERFLOW = """
() => ({scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth})
"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None  # type: ignore[attr-defined]
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def shot(page: Any, selector: str, path: Path) -> str:
    el = page.locator(selector).first
    if el.count() == 0:
        return f"(no element {selector})"
    el.scroll_into_view_if_needed()
    el.screenshot(path=str(path))
    return " ".join(el.inner_text().split())[:500]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", action="append", required=True, help="label=dir")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    report: dict[str, Any] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for spec in args.site:
            label, _, root = spec.partition("=")
            server, port = serve(Path(root))
            base = f"http://127.0.0.1:{port}"
            for width in (1440, 390):
                ctx = browser.new_context(viewport={"width": width, "height": 900})
                page = ctx.new_page()
                tag = f"task-53-{label}"
                r: dict[str, Any] = {}
                page.goto(base + NODE, wait_until="networkidle")
                r["node_head"] = shot(page, ".node-head", args.out / f"{tag}-node-head-{width}.png")
                r["node_claims"] = shot(
                    page, ".defect-claims", args.out / f"{tag}-node-claims-{width}.png"
                )
                r["node_dom"] = page.evaluate(CIRCULAR_DOM)
                r["node_overflow"] = page.evaluate(OVERFLOW)
                page.goto(base + PROBLEM, wait_until="networkidle")
                r["key_words"] = page.evaluate(LEGEND_WORDS)
                r["key"] = shot(page, ".dag-legend", args.out / f"{tag}-problem-key-{width}.png")
                page.locator(".dag").first.scroll_into_view_if_needed()
                page.locator(".dag").first.screenshot(
                    path=str(args.out / f"{tag}-problem-graph-{width}.png")
                )
                r["problem_dom"] = page.evaluate(CIRCULAR_DOM)
                r["problem_overflow"] = page.evaluate(OVERFLOW)
                page.goto(base + PROBLEM + f"#node={HOLE}", wait_until="networkidle")
                page.wait_for_timeout(300)
                r["panel"] = shot(
                    page,
                    f'.panel[data-node="{HOLE}"]',
                    args.out / f"{tag}-problem-panel-{width}.png",
                )
                page.goto(base + LISTING, wait_until="networkidle")
                page.evaluate(
                    "document.querySelectorAll('details.more').forEach(d => d.open = true)"
                )
                row = f'.stmt:has(a[href="{NODE}"])'
                r["row"] = shot(page, row, args.out / f"{tag}-listing-row-{width}.png")
                r["listing_dom"] = page.evaluate(CIRCULAR_DOM)
                r["listing_overflow"] = page.evaluate(OVERFLOW)
                report[f"{label}@{width}"] = r
                ctx.close()
            server.shutdown()
        browser.close()
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
