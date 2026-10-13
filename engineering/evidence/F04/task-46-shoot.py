"""F04-T46 screenshots: the root's "Split into" block (two holes, one glossed in math, one shown as
its Lean) and a hole's origin line, on test_finding_split_into's tree, at 1440 and 390, with the
math rendered by KaTeX and no sideways scroll.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-46-shoot.py \
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
from test_decompositions import HOLE_IDS
from test_finding_split_into import split_tree
from test_products import ROOT_NODE

from opn_gate import products
from opn_site import model, render


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root = split_tree(Path(tmp) / "g")
        products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
        files = render.render_site(
            model.load_site(root, fixture.COMMIT), repo_url="https://github.com/example/graph"
        )
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
        handler.log_message = lambda *a: None  # type: ignore[method-assign]
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            report: dict[str, object] = {}
            with sync_playwright() as p:
                b = p.chromium.launch()
                for width in (1440, 390):
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    pg.goto(f"{base}/problems/{TARGET}/#node={ROOT_NODE}")
                    pg.wait_for_load_state("networkidle")
                    panel = pg.locator(f'.panel[data-node="{ROOT_NODE}"]')
                    panel.scroll_into_view_if_needed()
                    panel.screenshot(path=str(args.out / f"task-46-panel-{width}.png"))
                    block = panel.locator("section.split-into")
                    pg.goto(f"{base}/problems/{TARGET}/#node={HOLE_IDS[0]}")
                    pg.wait_for_load_state("networkidle")
                    hole = pg.locator(f'.panel[data-node="{HOLE_IDS[0]}"]')
                    hole.scroll_into_view_if_needed()
                    hole.screenshot(path=str(args.out / f"task-46-hole-{width}.png"))
                    pg.goto(f"{base}/problems/{TARGET}/#node={ROOT_NODE}")
                    pg.wait_for_load_state("networkidle")
                    report[str(width)] = {
                        "split": block.inner_text(),
                        "katex_in_split": block.locator(".katex").count(),
                        "hole_of": hole.locator("p.hole-of").inner_text(),
                        "scrollWidth": pg.evaluate("document.documentElement.scrollWidth"),
                    }
                    pg.close()
                b.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
