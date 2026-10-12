"""F04-T44 screenshots: the steward card of a problem with a steward, and that problem's steward
form page, on the stewards fixture, at 1440 and 390, with the text of each and no sideways scroll.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-44-shoot.py \
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
    tid = fixture.STEWARDED_TARGET
    with tempfile.TemporaryDirectory() as tmp:
        root = fixture.build_with_stewards(Path(tmp) / "g")
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
                    pg.goto(f"{base}/problems/{tid}/")
                    pg.wait_for_load_state("networkidle")
                    card = pg.locator("aside.steward-card")
                    card.scroll_into_view_if_needed()
                    card.screenshot(path=str(args.out / f"task-44-card-{width}.png"))
                    card_text = card.inner_text()
                    card_sw = pg.evaluate("document.documentElement.scrollWidth")
                    pg.goto(f"{base}/steward/{tid}/")
                    pg.wait_for_load_state("networkidle")
                    pg.screenshot(path=str(args.out / f"task-44-form-{width}.png"), full_page=True)
                    report[str(width)] = {
                        "card": card_text,
                        "card_page_scrollWidth": card_sw,
                        "form_head": pg.locator("section.steward-head").inner_text(),
                        "form_card_visible": pg.locator(".steward-form-card").is_visible(),
                        "form_page_scrollWidth": pg.evaluate(
                            "document.documentElement.scrollWidth"
                        ),
                    }
                    pg.close()
                b.close()
            print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
