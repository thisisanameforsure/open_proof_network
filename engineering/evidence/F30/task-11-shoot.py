"""F30-T11 and F04-T55: captures and measurements of the crux band and the refuting side on a
rendered problem page (the fixture tree, or a local render of the live graph with the relation
mocked).

Usage: ``uv run --frozen --with playwright python engineering/evidence/F30/task-11-shoot.py
<site dir> <target> --out DIR --tag TAG``. Per width (1440, 390) it captures the drawing's card
as it opens (the band under the tree, no line across the gap), with the first band pill hovered
(its measured lines lit), with it clicked (pinned, pointer away), and the selector panel; and it
measures, rather than eyeballs (the 2026-09-19 rule): every ``path.band-link`` has no path and a
zero box at rest (getBBox); the hovered pill's links are lit with a path and the tree's far ends
lit; the band's translates are the same before and after a leaf selection; the page does not
scroll sideways at 390; the key names the band and each relation trunk the drawing has.
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
  const band = document.querySelector('svg.band');
  const vis = el => getComputedStyle(el).display !== 'none';
  const links = [...document.querySelectorAll('path.band-link')].map(p => {
    const b = p.getBBox();
    return {key: p.getAttribute('data-key'), kind: p.getAttribute('class'), shown: vis(p),
            lit: p.classList.contains('lit'), hasD: p.hasAttribute('d'), box: [b.width, b.height]};
  });
  const key = [...document.querySelectorAll('.dag-legend .term')].map(t => {
    const c = t.cloneNode(true); c.querySelectorAll('.term-card').forEach(x => x.remove());
    return c.textContent.trim();
  });
  return {
    links,
    band: band ? [...band.querySelectorAll('[data-node]')].map(g => [g.getAttribute('data-node'),
      g.getAttribute('transform'), g.classList.contains('lit')]) : null,
    bandLines: band ? band.querySelectorAll('path.edge').length : 0,
    mainLit: [...main.querySelectorAll('[data-node].lit')].map(g => g.getAttribute('data-node')),
    mainHovering: main.classList.contains('hovering'),
    trunks: [...main.querySelectorAll('path.edge.relation')].map(e => [e.getAttribute('class'),
      e.getAttribute('data-from'), e.getAttribute('data-to'), vis(e), getComputedStyle(e).stroke]),
    selector: [...document.querySelectorAll('svg.selector .sel-node')].map(g => [g.getAttribute('data-key'),
      g.getAttribute('class'), g.getAttribute('data-words'), getComputedStyle(g.querySelector('.dot')).stroke]),
    selEdges: [...document.querySelectorAll('svg.selector .sel-edge')].map(e => [e.getAttribute('data-to'),
      e.getAttribute('class'), getComputedStyle(e).stroke]),
    rows: [...document.querySelectorAll('tr.set-row')].map(r => [r.getAttribute('class'), r.cells[0].innerText.split('\\n')[0]]),
    kicker: (k => k ? k.textContent.trim() : null)(document.querySelector('.selector-wrap .kicker')),
    cue: (k => k ? k.textContent.trim() : null)(document.querySelector('.selector-wrap .sel-cue')),
    count: (k => k ? k.textContent.trim() : null)(document.querySelector('.routes-count')),
    key,
    // Every shown pill's label inside its box (getBBox, in the pill's own coordinates).
    overflow: [...document.querySelectorAll('svg.dag g.node')].filter(vis).flatMap(g => {
      const r = g.querySelector('rect.pill'), t = g.querySelector('text');
      if (!r || !t) return [];
      const rb = r.getBBox(), tb = t.getBBox();
      return (tb.x >= rb.x && tb.x + tb.width <= rb.x + rb.width + 0.5 &&
              tb.y >= rb.y && tb.y + tb.height <= rb.y + rb.height + 0.5)
        ? [] : [[g.getAttribute('data-node'), rb.width, tb.x + tb.width]];
    }),
    pills: document.querySelectorAll('svg.dag g.node').length,
    hash: location.hash,
    scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth,
    view: main.getAttribute('data-view'),
  };
}"""


def main() -> None:  # noqa: PLR0915
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=Path)
    ap.add_argument("target")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    tag = args.tag or args.target
    handler = functools.partial(Quiet, directory=str(args.site))
    report: dict[str, Any] = {}
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{args.target}/"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                # Tall enough that the card fits: an element capture taller than the viewport
                # is stitched by resizing it, which drops the hover's lit line from the shot.
                ctx = b.new_context(viewport={"width": width, "height": 2400})
                pg = ctx.new_page()
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                name = f"task-11-{tag}-{width}"
                card = pg.locator(".dag-wrap")
                card.scroll_into_view_if_needed()
                rest = pg.evaluate(STATE)
                card.screenshot(path=str(out / f"{name}-opening.png"))
                sel = pg.locator(".selector-wrap")
                if sel.count():
                    sel.screenshot(path=str(out / f"{name}-selector.png"))
                r: dict[str, Any] = {"rest": rest}
                pills = pg.locator("svg.band g.node")
                if pills.count():
                    # The first band pill with a link into the tree, else the first.
                    linked = {ln["key"].split(">")[0] for ln in rest["links"]} | {
                        ln["key"].split(">")[1] for ln in rest["links"]
                    }
                    ids = [b_[0] for b_ in rest["band"] if b_[0] in linked] or [rest["band"][0][0]]
                    pill = pg.locator(f'svg.band g.node[data-node="{ids[0]}"]')
                    pill.scroll_into_view_if_needed()
                    pill.hover()
                    time.sleep(0.2)
                    r["hovered"] = pg.evaluate(STATE)
                    r["hovered_pill"] = ids[0]
                    card.screenshot(path=str(out / f"{name}-band-hover.png"))
                    pill.click()
                    pg.mouse.move(5, 5)
                    time.sleep(0.2)
                    r["pinned"] = pg.evaluate(STATE)
                    card.screenshot(path=str(out / f"{name}-band-pinned.png"))
                    leaves = pg.locator("svg.selector .sel-node.kind-leaf")
                    if leaves.count():
                        leaves.nth(0).click()
                        pg.mouse.move(5, 5)
                        time.sleep(1.2)
                        r["on_leaf"] = pg.evaluate(STATE)
                        card.screenshot(path=str(out / f"{name}-band-pinned-leaf-selected.png"))
                        r["band_still"] = [x[:2] for x in r["on_leaf"]["band"]] == [
                            x[:2] for x in rest["band"]
                        ]
                        pg.keyboard.press("Escape")
                        time.sleep(1.2)
                    pill.click()
                    pg.mouse.move(5, 5)
                    time.sleep(0.2)
                    r["unpinned"] = pg.evaluate(STATE)
                r["at_rest_no_link_visible"] = all(
                    not ln["shown"] and not ln["hasD"] and ln["box"] == [0, 0]
                    for ln in rest["links"]
                )
                report[str(width)] = r
                ctx.close()
            b.close()
    (out / f"task-11-{tag}-measure.json").write_text(json.dumps(report, indent=1))
    summary = {
        w: {
            "links_at_rest": [ln["key"] for ln in r["rest"]["links"]],
            "at_rest_no_link_visible": r["at_rest_no_link_visible"],
            "hovered": r.get("hovered_pill"),
            "lit_links": [ln["key"] for ln in r.get("hovered", {}).get("links", []) if ln["lit"]],
            "tree_far_ends_lit": r.get("hovered", {}).get("mainLit"),
            "pinned_hash": r.get("pinned", {}).get("hash"),
            "band_still_across_selection": r.get("band_still"),
            "trunks": r["rest"]["trunks"],
            "selector": [(k, c, w_) for k, c, w_, _s in r["rest"]["selector"]],
            "rows": r["rest"]["rows"],
            "kicker": r["rest"]["kicker"],
            "count": r["rest"]["count"],
            "key": r["rest"]["key"],
            "scroll": [r["rest"]["scrollWidth"], r["rest"]["innerWidth"]],
            "labels_overflowing": r["rest"]["overflow"],
            "pills_measured": r["rest"]["pills"],
        }
        for w, r in report.items()
    }
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
