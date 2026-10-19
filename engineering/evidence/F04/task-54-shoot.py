"""F04-T54 screenshots and measurements: the literature marks (D-25 v3.45) on a local render of
the live graph (``/Users/mikehiggins/Desktop/repos/opn-lit-graph`` at origin/main, read-only),
rendered with ``python -m opn_site.cli render`` and served from a directory.

At 1440 and at 390 (a fresh context per width, so no stylesheet comes from cache) it shoots
erdos-1094's statement graph with its key, the node page of ``erdos-1094--h2--h1--h1`` (a
``known`` proposal: its head and its literature block) and of
``erdos-1094--h2--h2--h3--h1--h1`` (no record), and *measures* rather than eyeballs (the
2026-09-19 rule): every literature key item's text sits inside the key's box; every mark's
rect sits inside its pill's rect (getBBox, SVG units); the key's words and the marks' titles
name every state the drawing shows; no page scrolls sideways at 390; the signed-out node page
shows no control. Prints a JSON report, which is also written beside the shots.

    uv run --frozen --with playwright python engineering/evidence/F04/task-54-shoot.py \
        --site <rendered dir> --out engineering/evidence/F04
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

TARGET = "erdos-1094"
KNOWN = f"{TARGET}--h2--h1--h1"
BARE = f"{TARGET}--h2--h2--h3--h1--h1"

KEY = """
() => {
  const key = document.querySelector('.dag-legend');
  const box = key.getBoundingClientRect();
  return Array.from(key.querySelectorAll('.term.lit-term')).map(t => {
    const r = t.getBoundingClientRect();
    const c = t.cloneNode(true); c.querySelectorAll('.term-card').forEach(x => x.remove());
    const card = t.querySelector('.term-card');
    return {word: c.innerText.trim(), card: card ? card.textContent.trim() : '',
            inside: r.left >= box.left - 0.5 && r.right <= box.right + 0.5
                 && r.top >= box.top - 0.5 && r.bottom <= box.bottom + 0.5};
  });
}
"""
MARKS = """
() => Array.from(document.querySelectorAll('.dag .node')).map(g => {
  const pill = g.querySelector('rect.pill, rect');
  const m = g.querySelector('.lit-mark');
  if (!m) return {node: g.dataset.node, mark: null};
  const p = pill.getBBox(), r = m.querySelector('rect').getBBox(), ctm = m.getCTM(), pm = pill.getCTM();
  // both in the pill group's frame: the mark's translate is relative to the group
  const t = m.transform.baseVal.consolidate().matrix;
  const x = t.e + r.x, y = t.f + r.y;
  const text = g.querySelector('text').getBBox();
  return {node: g.dataset.node, mark: m.getAttribute('class'), title: m.querySelector('title').textContent,
          inside: x >= p.x && y >= p.y && x + r.width <= p.x + p.width && y + r.height <= p.y + p.height,
          clear_of_label: x >= text.x + text.width || y + r.height <= text.y,
          clear_of_tab: (() => { const o = g.querySelector('.outline-mark'); if (!o) return true;
            const ot = o.transform.baseVal.consolidate().matrix, ob = o.querySelector('rect').getBBox();
            return x + r.width <= ot.e + ob.x || y >= ot.f + ob.y + ob.height; })(),
          rect: [p.width, p.height], at: [x, y, r.width, r.height],
          hidden: getComputedStyle(g).display === 'none'};
}).filter(e => e.mark)
"""
OVERFLOW = "() => ({scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth})"
NODE_DOM = """
() => ({
  badge: Array.from(document.querySelectorAll('.node-head .lit-badge')).map(b => [b.getAttribute('class'), b.title]),
  block: !!document.querySelector('[data-block="literature"]'),
  act: (() => { const a = document.querySelector('.lit-act'); return a ? {hidden: a.hidden, buttons: a.querySelectorAll('button').length} : null; })(),
  buttons_in_main: document.querySelectorAll('main button, main form, main textarea, main select').length,
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
    if el.count() == 0:
        return f"(no element {selector})"
    el.scroll_into_view_if_needed()
    el.screenshot(path=str(path))
    return " ".join((el.text_content() or "").split())[:300]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    server, port = serve(args.site)
    base = f"http://127.0.0.1:{port}"
    report: dict[str, Any] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (1440, 390):
            ctx = browser.new_context(viewport={"width": width, "height": 900})
            page = ctx.new_page()
            page.goto(f"{base}/problems/{TARGET}/", wait_until="networkidle")
            page.evaluate(
                "document.querySelectorAll('.dag-toggle, .view-toggle').forEach(b => b.hidden = false)"
            )
            keys = page.evaluate(KEY)
            marks = page.evaluate(MARKS)
            report[f"problem@{width}"] = {
                **page.evaluate(OVERFLOW),
                "key_items": keys,
                "key_overflow": [k["word"] for k in keys if not k["inside"]],
                "marks": len(marks),
                "mark_states": sorted({m["mark"] for m in marks}),
                "mark_titles": sorted({m["title"] for m in marks}),
                "marks_outside_pill": [m for m in marks if not m["inside"]],
                "marks_on_label": [m for m in marks if not m["clear_of_label"]],
                "marks_on_outline_tab": [m for m in marks if not m["clear_of_tab"]],
                "marks_hidden_off_view": sum(1 for m in marks if m["hidden"]),
            }
            shot(page, ".dag-legend", args.out / f"task-54-problem-key-{width}.png")
            shot(page, ".dag", args.out / f"task-54-problem-graph-{width}.png")
            shot(page, ".dag-wrap", args.out / f"task-54-problem-card-{width}.png")
            if width == 1440:
                # The key item hovered: scroll first, then hover, then capture (2026-10-04).
                item = page.locator(".dag-legend .lit-term").first
                item.scroll_into_view_if_needed()
                item.hover()
                page.wait_for_timeout(150)
                # The card hangs below the key; a viewport clip keeps the pointer where it is
                # (an element screenshot scrolls, and the hover is lost — 2026-10-04).
                box = page.locator(".dag-legend").bounding_box()
                page.screenshot(
                    path=str(args.out / "task-54-problem-key-hover-1440.png"),
                    clip={"x": box["x"] - 8, "y": box["y"] - 8, "width": box["width"] + 16,
                          "height": box["height"] + 200},
                )
            for label, nid in (("known", KNOWN), ("bare", BARE)):
                page.goto(f"{base}/nodes/{TARGET}/{nid}/", wait_until="networkidle")
                r = {**page.evaluate(OVERFLOW), **page.evaluate(NODE_DOM)}
                r["head"] = shot(page, ".node-head", args.out / f"task-54-node-{label}-head-{width}.png")
                if r["block"]:
                    page.evaluate(
                        "document.querySelectorAll('[data-section=known] details').forEach(d => d.open = true)"
                    )
                    r["block_text"] = shot(
                        page, '[data-block="literature"]', args.out / f"task-54-node-{label}-block-{width}.png"
                    )
                report[f"node-{label}@{width}"] = r
            ctx.close()
        browser.close()
    server.shutdown()
    out = json.dumps(report, indent=1, ensure_ascii=False)
    (args.out / "task-54-measure.json").write_text(out + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
