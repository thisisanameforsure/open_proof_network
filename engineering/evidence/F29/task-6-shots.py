"""F29-T6 screenshots: the Routes section with a branch selected and with a leaf selected, and
the statement panel of a labelled node, at 1440px and 390px — on the fixture (``nested_tree``
plus a gloss label), and on a full render of the live graph when one is given.

    PYTHONPATH=gate:gate/tests:site:site/tests uv run --with playwright python shots.py <out-dir> [live-site-dir] [target]
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
LIVE = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None
LIVE_TARGET = sys.argv[3] if len(sys.argv) > 3 else "erdos-1094"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def fixture_site(tmp: Path) -> tuple[Path, str, str]:
    import gloss_fixture
    from harness import TARGET
    from test_finding_labels_site import CLAIM, GLOSSED, LABEL, labelled_pages
    from test_routes_view import nested_tree

    from opn_site import render

    root = nested_tree(tmp / "g")
    gloss_fixture.gloss(
        root,
        f"$${CLAIM}$$\n\nThe reciprocals of the set sum to less than two.",
        kind="statement",
        node=GLOSSED,
        author="ann",
    )
    pages = labelled_pages(root)
    out = tmp / "site"
    render.write(pages, out)
    print("fixture: labelled", GLOSSED, "as", repr(LABEL))
    return out, TARGET, GLOSSED


def shoot(site: Path, target: str, labelled: str, tag: str) -> None:
    handler = functools.partial(Quiet, directory=str(site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                pg = b.new_page(viewport={"width": width, "height": 900})
                pg.emulate_media(reduced_motion="reduce")
                pg.goto(f"{base}/problems/{target}/", wait_until="load", timeout=120000)
                pg.wait_for_timeout(500)
                sec = pg.locator(".routes-section")
                sec.scroll_into_view_if_needed()
                branch = pg.locator("svg.routes-svg .sel-row.branch")
                leaves = pg.locator("svg.routes-svg .sel-row.leaf")
                print(tag, width, "branches", branch.count(), "leaves", leaves.count())
                if branch.count():
                    branch.nth(0).click()
                    pg.mouse.move(2, 2)
                    sec.screenshot(path=str(OUT / f"task-6-{tag}-{width}-branch.png"))
                if leaves.count():
                    k = min(2, leaves.count() - 1)
                    leaves.nth(k).click()
                    pg.mouse.move(2, 2)
                    sec.screenshot(path=str(OUT / f"task-6-{tag}-{width}-leaf.png"))
                # The statement panel of a labelled node: the page's script shows it on #node=.
                pg.goto(f"{base}/problems/{target}/#node={labelled}", wait_until="load", timeout=120000)
                pg.wait_for_timeout(500)
                panel = pg.locator(f'.card.panel[data-node="{labelled}"]')
                if panel.count():
                    panel.scroll_into_view_if_needed()
                    print(tag, width, "panel title:", panel.locator(".panel-title").inner_text())
                    panel.screenshot(path=str(OUT / f"task-6-{tag}-{width}-panel.png"))
                # Overflow check at the narrow width (log 2026-09-18).
                sw, cw = pg.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                print(tag, width, "scrollWidth", sw, "clientWidth", cw)
                pg.close()
            b.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    import os

    if not os.environ.get("SKIP_FIXTURE"):
        with tempfile.TemporaryDirectory() as tmp:
            site, target, labelled = fixture_site(Path(tmp))
            shoot(site, target, labelled, "fixture")
    if LIVE is not None and (LIVE / "problems" / LIVE_TARGET / "index.html").is_file():
        import json
        import re

        page = (LIVE / "problems" / LIVE_TARGET / "index.html").read_text(encoding="utf-8")
        # A labelled node: the first panel whose heading is not its id.
        labelled = LIVE_TARGET
        for m in re.finditer(r'<div class="card panel" data-node="([^"]+)"', page):
            nid = m.group(1)
            seg = page[m.end() : m.end() + 600]
            if '<span class="panel-title">' in seg:
                labelled = nid
                break
        print("live: labelled panel", labelled)
        shoot(LIVE, LIVE_TARGET, labelled, "live")
    else:
        print("live render not available; fixture screenshots only")


if __name__ == "__main__":
    main()
