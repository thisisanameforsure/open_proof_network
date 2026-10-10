"""F04-T39 screenshots and measurements: the lemma line (D-12 v3.36) on a local render of the
site's fixture graph, whose products carry one lemma (``tutorial-and-swap`` may use
``and-reassoc``, hole ``h_reassoc``; ``fixture.LEMMA_*``).

Serves the rendered site and, at 1440 and at 390, shoots the problem page's statement graph with
the lemma line, its key, the node page's lemma list, and the hover state with the lemma line
lit — and *measures* rather than eyeballs (the 2026-09-19 rule): every key label's text box sits
inside the key, every pill's label inside its pill (getBBox against the rect), no page scrolls
sideways (scrollWidth), and hovering the parent lights exactly the lemma line and the parent's
own dependency line. ``measure`` is what ``site/tests/test_finding_lemma_edge.py`` asserts on,
so the shots and the assertions come from one run.

    uv run --frozen --with playwright python engineering/evidence/F04/task-39-shoot.py \
        --site <rendered site> --out engineering/evidence/F04
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

#: Every key term's text against the key's own box, and against its own row (nowrap, so a
#: label that does not fit would run past the key's right edge).
MEASURE_KEY = """
() => {
  const key = document.querySelector('.dag-legend');
  const box = key.getBoundingClientRect();
  return Array.from(key.querySelectorAll('.term')).map(t => {
    const r = t.getBoundingClientRect();
    const text = (t.childNodes[1] && t.childNodes[1].nodeType === 3 ? t.childNodes[1].textContent
                  : t.textContent.split('\\n')[0]).trim();
    const inside = r.left >= box.left - 0.5 && r.right <= box.right + 0.5
                && r.top >= box.top - 0.5 && r.bottom <= box.bottom + 0.5;
    return {word: text, inside, box: [Math.round(r.width), Math.round(r.height)]};
  });
}
"""
#: Every pill's label text (getBBox) against its rect, in the SVG's own units.
MEASURE_PILLS = """
() => Array.from(document.querySelectorAll('.dag .node')).map(g => {
  const r = g.querySelector('rect').getBBox(), t = g.querySelector('text').getBBox();
  return {node: g.dataset.node,
          inside: t.x >= r.x && t.y >= r.y && t.x + t.width <= r.x + r.width && t.y + t.height <= r.y + r.height,
          rect: [r.width, r.height], text: [Math.round(t.width * 10) / 10, Math.round(t.height * 10) / 10]};
})
"""
LIT = """
() => ({
  edges: Array.from(document.querySelectorAll('.dag path.edge.lit')).map(e => [e.dataset.from, e.dataset.to, e.getAttribute('class')]),
  pills: Array.from(document.querySelectorAll('.dag .node.lit')).map(g => g.dataset.node).sort(),
  hovering: document.querySelector('.dag').classList.contains('hovering'),
  lemma_stroke: getComputedStyle(document.querySelector('.dag path.edge.lemma')).strokeDasharray,
  use_stroke: (() => { const u = document.querySelector('.dag path.edge.use'); return u ? getComputedStyle(u).strokeDasharray : null; })(),
})
"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

    handler = functools.partial(Quiet, directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def shot(page: Any, selector: str, path: Path) -> str:
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    el.screenshot(path=str(path))
    return " ".join((el.text_content() or "").split())  # text_content: an SVG is no HTMLElement


def measure(site: Path, out: Path, *, target: str, parent: str, lemma: str) -> dict[str, Any]:
    """Shoot and measure; returns the report the test asserts on."""
    out.mkdir(parents=True, exist_ok=True)
    server, port = serve(site)
    base = f"http://127.0.0.1:{port}"
    problem, node = f"/problems/{target}/", f"/nodes/{target}/{parent}/"
    report: dict[str, Any] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (1440, 390):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(base + problem, wait_until="networkidle")
            keys = page.evaluate(MEASURE_KEY)
            pills = page.evaluate(MEASURE_PILLS)
            report[f"problem@{width}"] = {
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
                "key_words": [k["word"] for k in keys],
                "key_overflow": [k for k in keys if not k["inside"]],
                "pill_overflow": [q for q in pills if not q["inside"]],
                "pills": pills,
                "lemma_lines": page.evaluate(
                    "Array.from(document.querySelectorAll('.dag path.edge.lemma'))"
                    ".map(e => [e.dataset.from, e.dataset.to])"
                ),
            }
            shot(page, ".dag", out / f"task-39-graph-{width}.png")
            shot(page, ".dag-legend", out / f"task-39-key-{width}.png")
            page.goto(base + node, wait_until="networkidle")
            report[f"node@{width}"] = {
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
                "lemmas": shot(page, ".lemmas", out / f"task-39-node-lemmas-{width}.png"),
            }
            page.close()
        # The hover state: scroll first, then hover, then measure and capture (2026-10-04).
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + problem, wait_until="networkidle")
        page.locator(".dag").first.scroll_into_view_if_needed()
        page.locator(f'.dag g[data-node="{parent}"]').first.hover()
        page.wait_for_timeout(200)
        lit = page.evaluate(LIT)
        page.locator(".dag").first.screenshot(path=str(out / "task-39-hover-1440.png"))
        report["hover"] = {
            "hovered": parent,
            "expected_lemma_line": [lemma, parent],
            "lit_edges": lit["edges"],
            "lit_lemma": [[f, t] for f, t, cls in lit["edges"] if "lemma" in cls.split()],
            "lit_pills": lit["pills"],
            "hovering": lit["hovering"],
            "lemma_stroke": lit["lemma_stroke"],
            "use_stroke": lit["use_stroke"],
        }
        page.close()
        browser.close()
    server.shutdown()
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--target", default="propositional")
    ap.add_argument("--parent", default="tutorial-and-swap")
    ap.add_argument("--lemma", default="and-reassoc")
    args = ap.parse_args()
    report = measure(args.site, args.out, target=args.target, parent=args.parent, lemma=args.lemma)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
