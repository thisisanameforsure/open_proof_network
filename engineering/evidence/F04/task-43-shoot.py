"""F04-T43 screenshot: the catalog evidence block on the evidenced fixture's problem page, with
the reasons headed as score points, at 1440 and 390.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-43-shoot.py \
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
from playwright.sync_api import sync_playwright

from opn_site import model, render


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root = fixture.build_with_evidenced_target(Path(tmp) / "g")
        files = render.render_site(
            model.load_site(root, fixture.COMMIT), repo_url="https://github.com/example/graph"
        )
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
        handler.log_message = lambda *a: None  # type: ignore[method-assign]
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{fixture.LISTED_TARGET}/"
            report = {}
            with sync_playwright() as p:
                b = p.chromium.launch()
                for width in (1440, 390):
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    pg.goto(url)
                    pg.wait_for_load_state("networkidle")
                    ev = pg.locator("div.evidence").first
                    for d in pg.locator("details").all():  # open any section that holds it
                        d.evaluate("e => e.open = true")
                    ev.scroll_into_view_if_needed()
                    ev.screenshot(path=str(args.out / f"task-43-evidence-{width}.png"))
                    report[width] = {
                        "text": ev.inner_text(),
                        "scrollWidth": pg.evaluate("document.documentElement.scrollWidth"),
                    }
                    pg.close()
                b.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
