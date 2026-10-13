"""F04-T47 screenshots: the "Split into" block with its partial proof unfolded, on
test_finding_split_into's tree, and (with --live-graph, an export of the graph at --commit) the
same block on erdos-1094--h2 rendered from the live record, at 1440 and 390, no sideways scroll.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-47-shoot.py \
        --out engineering/evidence/F04
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
from harness import TARGET
from playwright.sync_api import sync_playwright
from test_finding_split_into import split_tree
from test_products import ROOT_NODE

from opn_gate import products
from opn_site import model, render


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--live-graph", type=Path)
    ap.add_argument("--commit", default=fixture.COMMIT)
    args = ap.parse_args()
    if args.live_graph is not None:
        shoot(args, args.live_graph, args.commit, "erdos-1094", "erdos-1094--h2", "live")
        return
    with tempfile.TemporaryDirectory() as tmp:
        root = split_tree(Path(tmp) / "g")
        products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
        shoot(args, root, fixture.COMMIT, TARGET, ROOT_NODE, "fixture")


def shoot(  # noqa: PLR0913 — where to render from and what to capture
    args: argparse.Namespace, root: Path, commit: str, tid: str, nid: str, tag: str
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        files = render.render_site(
            model.load_site(root, commit), repo_url="https://github.com/example/graph"
        )
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
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
                    block = pg.locator(f'.panel[data-node="{nid}"] section.split-into').first
                    fold = block.locator("details.split-lean")
                    closed = fold.evaluate("d => d.open")
                    fold.locator("summary").click()
                    block.scroll_into_view_if_needed()
                    block.screenshot(path=str(args.out / f"task-47-{tag}-{width}.png"))
                    report[str(width)] = {
                        "open_before_click": closed,
                        "lean_first_line": fold.locator("pre.lean").inner_text().splitlines()[0],
                        "block_bytes": len(block.evaluate("e => e.outerHTML").encode()),
                        "scrollWidth": pg.evaluate("document.documentElement.scrollWidth"),
                    }
                    pg.close()
                b.close()
            print(json.dumps({tag: report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
