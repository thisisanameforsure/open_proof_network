"""F32-T6 screenshots: the page of a hole born proved (AC6's merge, recorded as the graph
workflow leaves it), at 1440 and 390 px, with the facts column's ``proof`` row and every
``Proof.lean`` link printed. Run with pytest, since the tree is built through the post-merge
command over the scripted-docker seam:

    uv run --frozen --with playwright pytest engineering/evidence/F32/task-6-shoot.py \
        -p no:cacheprovider -q -s
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from pathlib import Path

import pytest
from test_cli_sandboxed import Seam
from test_cli_sandboxed import seam as seam  # noqa: PLC0414 — the scripted-docker fixture
from test_finding_carried_proof_postmerge import H1, recorded

from opn_site import model, render

OUT = Path(__file__).resolve().parent
REPO = "https://github.com/example/graph"


def test_shoot(tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]) -> None:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    root, merge, bot = recorded(tmp_path, seam, capsys)
    files = render.render_site(model.load_site(root, bot), repo_url=REPO)
    site = tmp_path / "site"
    render.write(files, site)
    page_html = files[f"nodes/propositional/{H1}/index.html"]
    links = re.findall(r'href="([^"]*Proof\.lean[^"]*)"', page_html)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    handler.log_message = lambda *a: None  # type: ignore[method-assign]
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/nodes/propositional/{H1}/"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                pg = b.new_page(viewport={"width": width, "height": 900})
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                pg.screenshot(path=str(OUT / f"task-6-hole-{width}.png"), full_page=True)
                if width == 1440:
                    row = pg.locator("dt", has_text="proof").first.locator("xpath=following-sibling::dd[1]")
                    fact = row.inner_text() if row.count() else "(no proof row found)"
                    overflow = pg.evaluate("document.documentElement.scrollWidth")
                else:
                    overflow = pg.evaluate("document.documentElement.scrollWidth")
                with capsys.disabled():
                    if width == 1440:
                        print(f"proof row: {fact!r}")
                    print(f"{width}px: scrollWidth {overflow}")
            b.close()
    with capsys.disabled():
        print(f"merge {merge}\nbot   {bot}")
        for link in links:
            print(f"link: {link}")
