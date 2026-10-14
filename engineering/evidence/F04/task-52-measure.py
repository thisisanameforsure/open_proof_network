"""F04-T52 measurements: does any problem page scroll sideways at 390, and which pills reach past it?

Renders the site from an export of the live graph (``--live-graph DIR --commit SHA``) with the
working tree's renderer and stylesheet, opens every ``/problems/<target>/`` page at 390 and at
1440, and records the document's ``scrollWidth``, every ``.tag`` whose right edge passes the
viewport, and the height of every ``.tag`` on the page (a short status pill must stay one line,
22 px, at 1440). With ``--shots DIR --tag before|after`` it also captures erdos-1094's header at
both widths.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-52-measure.py \
        --live-graph DIR --commit SHA --tag after --shots engineering/evidence/F04
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

from opn_site import model, render

MEASURE = """() => {
  const vw = window.innerWidth;
  const tags = [...document.querySelectorAll('.tag')].map(e => {
    const r = e.getBoundingClientRect();
    return {cls: e.className, text: e.textContent.trim().slice(0, 60),
            right: Math.round(r.right), height: Math.round(r.height)};
  });
  return {scroll: document.documentElement.scrollWidth,
          over: tags.filter(t => t.right > vw),
          heights: tags.map(t => [t.cls, t.height, t.text])};
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-graph", type=Path, required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--shots", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    site = model.load_site(args.live_graph, args.commit)
    targets = sorted(
        p.parent.name for p in (args.live_graph / "targets").glob("*/gate-spec.json")
    )
    result: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        render.write(render.render_site(site, repo_url="https://github.com/example/graph"), out)
        handler = functools.partial(Quiet, directory=str(out))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            with sync_playwright() as p:
                b = p.chromium.launch()
                for width in (390, 1440):
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    for t in targets:
                        pg.goto(f"{base}/problems/{t}/")
                        pg.wait_for_load_state("networkidle")
                        result.setdefault(t, {})[str(width)] = pg.evaluate(MEASURE)
                        if args.shots and t == "erdos-1094":
                            pg.locator(".problem-id-row").scroll_into_view_if_needed()
                            box = pg.locator(".problem-id-row").bounding_box()
                            assert box is not None
                            pg.screenshot(
                                path=str(args.shots / f"task-52-{args.tag}-erdos-1094-{width}.png"),
                                clip={"x": 0, "y": max(0, box["y"] - 80), "width": width,
                                      "height": box["height"] + 200},
                                full_page=True,
                            )
                    pg.close()
                b.close()
    wide = {t: r["390"]["scroll"] for t, r in result.items() if r["390"]["scroll"] != 390}
    print(f"[{args.tag}] graph {args.commit[:12]}: {len(targets)} problem pages")
    print(f"  scrollWidth != 390 at 390: {len(wide)} {wide}")
    for t, r in result.items():
        for o in r["390"]["over"]:
            print(f"  {t}@390 pill past the viewport: right={o['right']} {o['cls']!r} {o['text']!r}")
    tall = sorted(
        {(c, h) for r in result.values() for c, h, _ in r["1440"]["heights"] if "review-state" not in c}
    )
    print(f"  pill classes and heights at 1440, review pill excluded: {tall}")
    rev = sorted({h for r in result.values() for c, h, _ in r["1440"]["heights"] if "review-state" in c})
    print(f"  review pill heights at 1440: {rev}")
    if args.json:
        args.json.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
