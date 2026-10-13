"""F04-T45 screenshots: a statement panel with one stepped annex (an outline) and one note, and
the graph's tab counting the outline only, at 1440 and 390, with no sideways scroll.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-45-shoot.py \
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
from test_finding_outlines_are_stepped import stepped_and_note
from test_products import ROOT_NODE

from opn_gate import products
from opn_site import model, render


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root, _ = stepped_and_note(Path(tmp))
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
                    dag = pg.locator(".dag-wrap")
                    dag.scroll_into_view_if_needed()
                    dag.screenshot(path=str(args.out / f"task-45-graph-{width}.png"))
                    panel = pg.locator(f'.panel[data-node="{ROOT_NODE}"]')
                    panel.scroll_into_view_if_needed()
                    panel.screenshot(path=str(args.out / f"task-45-panel-{width}.png"))
                    report[str(width)] = {
                        "tab": pg.locator(
                            f'g.node[data-node="{ROOT_NODE}"] .outline-mark text'
                        ).all_text_contents(),
                        "outlines": panel.locator("ul.outlines:not(.notes)").inner_text(),
                        "notes": panel.locator("ul.outlines.notes").inner_text(),
                        "scrollWidth": pg.evaluate("document.documentElement.scrollWidth"),
                    }
                    pg.close()
                b.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
