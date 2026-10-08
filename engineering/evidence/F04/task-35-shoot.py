"""F04-T35 / T36 screenshots: the erdos-1094 pages the lead found on 2026-10-08, rendered locally
from the live graph clone.

Serves a rendered site (``python -m opn_site.cli render --graph <graph clone> ...``), shoots one
element per page at desktop width (and the whole page at phone width), and prints what each
shot is meant to show as text beside it, so the evidence does not rest on the picture alone
(engineering/CLAUDE.md, 2026-09-18/19). The page is scrolled to the element before capture.

    uv run --with playwright python engineering/evidence/F04/task-35-shoot.py \
        --site <rendered site> --out engineering/evidence/F04 --tag before|after --task 35|36
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

#: (name, path, selector of the element that carries the defect, text to report)
SHOTS: dict[str, list[tuple[str, str, str]]] = {
    "35": [
        ("root-partial", "/nodes/erdos-1094/erdos-1094/", 'div[data-block="partial"] p.label'),
        ("h3-partial", "/nodes/erdos-1094/erdos-1094--h3/", 'div[data-block="partial"] p.label'),
        ("h1-attestation", "/nodes/erdos-1094/erdos-1094--h1/", 'div[data-block="attestation"]'),
    ],
    "36": [
        ("annex-provenance", "/nodes/erdos-1094/erdos-1094/", 'div[data-block="annex"] p.label'),
        ("outline-titles", "/problems/erdos-1094/", "div.panel-outlines"),
        ("problem-provenance", "/problems/erdos-1094/", ".provenance-line"),
    ],
}


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--task", required=True, choices=sorted(SHOTS))
    args = ap.parse_args()
    server, port = serve(args.site)
    base = f"http://127.0.0.1:{port}"
    report: dict[str, Any] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, path, selector in SHOTS[args.task]:
            page.goto(base + path)
            el = page.locator(selector).first
            el.scroll_into_view_if_needed()
            shot = args.out / f"task-{args.task}-{args.tag}-{name}-1440.png"
            el.screenshot(path=str(shot))
            report[name] = {
                "shot": shot.as_posix(),
                "text": " ".join(el.inner_text().split()),
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
            }
        if args.tag == "after":
            phone = browser.new_page(viewport={"width": 390, "height": 900})
            for name, path, _ in SHOTS[args.task][:1]:
                phone.goto(base + path)
                report[f"{name}@390"] = {
                    "scrollWidth": phone.evaluate("document.documentElement.scrollWidth")
                }
        browser.close()
    server.shutdown()
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
