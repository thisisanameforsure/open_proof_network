"""F04-T49 screenshots: no sideways page scroll at 390, the graph scrolling in its own box, and a
panel's Lean scrolling in its block with its indentation, on summary_fixture's tree and (with
--live-graph, an export of the graph at --commit) on erdos-1094 rendered from the live record.
For each width it captures the viewport at the top of the page, the statement graph's card and
the hole's panel with its partial proof opened, and reports the page's scrollWidth, the graph
box's scroll and client widths, and each panel Lean block's.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-49-shoot.py \
        --out engineering/evidence/F04 [--live-graph DIR --commit SHA]
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

import fixture
import summary_fixture as sf
from harness import TARGET
from playwright.sync_api import sync_playwright

from opn_site import model, render

MEASURE = """(nid) => {
  const s = document.querySelector('.dag-scroll');
  const pres = [...document.querySelectorAll(`.panel[data-node="${nid}"] pre.lean`)];
  return {
    scrollWidth: document.documentElement.scrollWidth,
    graph: [s.scrollWidth, s.clientWidth],
    lean: pres.filter(p => p.offsetParent !== null).map(p => [p.scrollWidth, p.clientWidth,
      getComputedStyle(p).whiteSpace]),
  };
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--live-graph", type=Path)
    ap.add_argument("--commit", default=fixture.COMMIT)
    args = ap.parse_args()
    if args.live_graph is not None:
        shoot(
            args,
            model.load_site(args.live_graph, args.commit),
            "erdos-1094",
            "erdos-1094--h2",
            "live",
        )
        return
    with tempfile.TemporaryDirectory() as tmp:
        root = sf.summary_tree(Path(tmp) / "g")
        sf.publish(root)
        shoot(args, model.load_site(root, fixture.COMMIT), TARGET, sf.ROOT, "fixture")


def shoot(args: argparse.Namespace, site_model: model.Site, tid: str, nid: str, tag: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        files = render.render_site(site_model, repo_url="https://github.com/example/graph")
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(Quiet, directory=str(site))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            report: dict[str, object] = {}
            with sync_playwright() as p:
                b = p.chromium.launch()
                for width in (1440, 390):
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    pg.goto(f"{base}/problems/{tid}/#node={nid}")
                    pg.wait_for_load_state("networkidle")
                    pg.screenshot(path=str(args.out / f"task-49-{tag}-page-{width}.png"))
                    pg.locator(".dag-wrap").screenshot(
                        path=str(args.out / f"task-49-{tag}-graph-{width}.png")
                    )
                    panel = pg.locator(f'.panel[data-node="{nid}"]')
                    fold = panel.locator("details.split-lean summary").first
                    if fold.count():
                        fold.click()
                    panel.scroll_into_view_if_needed()
                    panel.screenshot(path=str(args.out / f"task-49-{tag}-panel-{width}.png"))
                    report[str(width)] = pg.evaluate(MEASURE, nid)
                    pg.close()
                b.close()
            print(json.dumps({tag: report}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
