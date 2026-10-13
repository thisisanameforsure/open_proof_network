"""F04-T48 screenshots: the statement panel as a summary, on summary_fixture's tree (the root and
the math-first hole) and, with --live-graph (an export of the graph at --commit), on erdos-1094's
root and erdos-1094--h2 rendered from the live record, at 1440 and 390. Reports each panel's
visible word count as the browser lays it out (innerText with closed details closed) and the
page's scrollWidth.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-48-shoot.py \
        --out engineering/evidence/F04 [--live-graph DIR --commit SHA] [--tag 48]
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import socketserver
import tempfile
import threading
from pathlib import Path

import fixture
import summary_fixture as sf
from harness import TARGET
from playwright.sync_api import sync_playwright

from opn_site import model, render


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--live-graph", type=Path)
    ap.add_argument("--commit", default=fixture.COMMIT)
    ap.add_argument("--tag", default="48")
    args = ap.parse_args()
    if args.live_graph is not None:
        site = model.load_site(args.live_graph, args.commit)
        shoot(args, site, "erdos-1094", ["erdos-1094", "erdos-1094--h2"], "live")
        return
    with tempfile.TemporaryDirectory() as tmp:
        root = sf.summary_tree(Path(tmp) / "g")
        sf.publish(root)
        shoot(args, model.load_site(root, fixture.COMMIT), TARGET, [sf.ROOT, sf.H1], "fixture")


def shoot(
    args: argparse.Namespace, site_model: model.Site, tid: str, nids: list[str], tag: str
) -> None:
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
                    for k, nid in enumerate(nids):
                        pg = b.new_page(viewport={"width": width, "height": 900})
                        pg.goto(f"{base}/problems/{tid}/#node={nid}")
                        pg.wait_for_load_state("networkidle")
                        panel = pg.locator(f'.panel[data-node="{nid}"]')
                        panel.scroll_into_view_if_needed()
                        name = "root" if k == 0 else "hole"
                        panel.screenshot(
                            path=str(args.out / f"task-{args.tag}-{tag}-{name}-{width}.png")
                        )
                        text = panel.inner_text()
                        report[f"{nid}@{width}"] = {
                            "visible_words": sum(1 for w in text.split() if re.search(r"\w", w)),
                            "lean_folded": panel.locator("details.panel-lean").count(),
                            "katex": panel.locator(".katex").count(),
                            "scrollWidth": pg.evaluate("document.documentElement.scrollWidth"),
                        }
                        pg.close()
                b.close()
            print(json.dumps({tag: report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
