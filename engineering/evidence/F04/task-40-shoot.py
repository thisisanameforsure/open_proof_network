"""F04-T40 screenshots: the About page's contact section and the footer's contact link, on a local
render of the site's fixture graph, at 1440 and at 390. Measures rather than eyeballs: no page
scrolls sideways at 390 (scrollWidth), and following the footer link lands on the section.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-40-shoot.py \
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
        root = fixture.build(Path(tmp) / "g")
        files = render.render_site(
            model.load_site(root, fixture.COMMIT), repo_url="https://github.com/example/graph"
        )
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
        handler.log_message = lambda *a: None  # type: ignore[method-assign]
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{port}"
            report: dict[str, object] = {}
            with sync_playwright() as p:
                b = p.chromium.launch()
                for width in (1440, 390):
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    pg.goto(f"{base}/")
                    pg.locator("footer").scroll_into_view_if_needed()
                    pg.locator("footer").screenshot(path=str(args.out / f"task-40-footer-{width}.png"))
                    pg.click('footer a[href="/about/#contact"]')
                    pg.wait_for_load_state()
                    report[f"{width}"] = pg.evaluate(
                        """() => ({
                          url: location.pathname + location.hash,
                          scrollWidth: document.documentElement.scrollWidth,
                          clientWidth: document.documentElement.clientWidth,
                          sectionTop: Math.round(document.getElementById('contact')
                                                   .getBoundingClientRect().top),
                        })"""
                    )
                    pg.screenshot(path=str(args.out / f"task-40-about-contact-{width}.png"))
                    pg.close()
                b.close()
            srv.shutdown()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
