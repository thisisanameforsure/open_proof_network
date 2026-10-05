"""F21-T7 screenshots and measurements: the Problems page's "Needs words" filter (R9, AC8).

Builds the AC8 fixture (``site/tests/test_needs_words_filter.py``: the propositional problem with
files lacking words, and euclid-primes with words for every file and proof), renders the site,
serves it, and at 1440 and 390 shoots the Problems page unfiltered and with the "Needs words"
segment clicked. Measures what the eye misses: scrollWidth against the viewport, and — with the
page's own script running — which cards the filter leaves visible against which carry a count
above zero. Prints one JSON document; exit 1 when a measurement fails.

    PYTHONPATH=gate:gate/tests:site:site/tests uv run --with playwright \
        python engineering/evidence/F21/task-7-shoot.py --out engineering/evidence/F21
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

import fixture
from harness import take_in
from playwright.sync_api import sync_playwright
from test_needs_words_filter import REPO, WORDED, give_words, render_products

from opn_site import model, render

WIDTHS = {"1440": 1440, "390": 390}


def build(tmp: Path) -> Path:
    root = fixture.curated(tmp / "graph-src")
    take_in(root, WORDED)
    render_products(root)
    give_words(root, WORDED)
    render_products(root)
    site = model.load_site(root, fixture.COMMIT)
    out = tmp / "site"
    render.write(render.render_site(site, repo_url=REPO), out)
    return out


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


VISIBLE = "els => els.filter(e => !e.hidden).map(e => [e.id, e.dataset.words])"
ALL = "els => els.map(e => [e.id, e.dataset.words])"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    report: dict[str, Any] = {"pages": {}, "ok": True}
    with tempfile.TemporaryDirectory() as tmp:
        server, port = serve(build(Path(tmp)))
        base = f"http://127.0.0.1:{port}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, width in WIDTHS.items():
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.goto(f"{base}/problems/")
                page.screenshot(path=str(args.out / f"task-7-problems-{name}.png"), full_page=True)
                cards = page.eval_on_selector_all("article.problem", ALL)
                sw_all = page.evaluate("document.documentElement.scrollWidth")
                page.click('.seg-opt[data-filter="words"]')
                page.screenshot(
                    path=str(args.out / f"task-7-problems-words-{name}.png"), full_page=True
                )
                visible = page.eval_on_selector_all("article.problem", VISIBLE)
                wanted = [c for c in cards if int(c[1] or 0) > 0]
                entry = {
                    "scrollWidth": sw_all,
                    "scrollWidth_filtered": page.evaluate(
                        "document.documentElement.scrollWidth"
                    ),
                    "cards": cards,
                    "visible_after_filter": visible,
                    "segment": page.locator('.seg-opt[data-filter="words"]').inner_text(),
                    "url": page.url,
                    "showing": page.locator(".showing").inner_text(),
                    "words_lines": page.locator(".words").all_inner_texts(),
                }
                report["pages"][f"problems@{name}"] = entry
                # a zero is a claim about the accessor (Log 2026-09-16): two cards, one kept
                report["ok"] &= (
                    len(cards) == 2
                    and len(wanted) == 1
                    and visible == wanted
                    and sw_all <= width
                    and entry["scrollWidth_filtered"] <= width
                )
                page.close()
            browser.close()
        server.shutdown()
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
