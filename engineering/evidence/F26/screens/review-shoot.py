"""F26-T12 screenshots and measurements (AC15): the review page and the target page's state line
on a local render of the site's fixture graph with ``fixture.build_with_review``'s review (four
candidates, two tests, one answered and one waiting question, one pair proved both ways and one
open, the intent signer's accept).

Renders the fixture, serves it, and at 1440 and at 390 shoots the whole review page, each of its
six sections and the problem page's id row with the state tag — and *measures* rather than
eyeballs (the 2026-09-19 rule): no page scrolls sideways (scrollWidth), the six sections are in
R16's order, each wears exactly one of the two section styles, and the state tag's words are the
page's own. The report is written beside the shots as ``review-measure.json``.

    uv run --frozen --with playwright python engineering/evidence/F26/screens/review-shoot.py \
        --out engineering/evidence/F26/screens
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
ROOT = HERE.parents[4]
for rel in ("gate", "site", "api", "gate/tests", "site/tests"):
    sys.path.insert(0, str(ROOT / rel))

import fixture  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from opn_site import model, render  # noqa: E402

REPO = "https://github.com/example/graph"
SECTIONS = ("candidates", "pairs", "questions", "tests", "screens", "signatures")
MEASURE = """
() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
  sections: Array.from(document.querySelectorAll('section.review-section')).map(s => ({
    id: s.querySelector('h2').id,
    kind: s.classList.contains('exhibits') ? 'exhibits' : s.classList.contains('judgements') ? 'judgements' : null,
    label: s.querySelector('.section-kind').textContent.trim().slice(0, 40),
    left_border: getComputedStyle(s).borderLeftColor,
    border_style: getComputedStyle(s).borderTopStyle,
  })),
  pre_count: document.querySelectorAll('pre.lean').length,
  matrix_cells: Array.from(document.querySelectorAll('table.review-matrix td.cell')).map(c => c.className),
  slots: Array.from(document.querySelectorAll('.signature-slot')).map(s => s.className),
})
"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

    handler = functools.partial(Quiet, directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def shot(page: Any, selector: str, path: Path) -> str:
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    el.screenshot(path=str(path))
    return " ".join((el.text_content() or "").split())[:120]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = fixture.build_with_review(Path(tmp) / "graph")
        site = model.load_site(root, fixture.COMMIT)
        files = render.render_site(site, repo_url=REPO)
        rendered = Path(tmp) / "site"
        render.write(files, rendered)
        server, port = serve(rendered)
        base = f"http://127.0.0.1:{port}"
        target = fixture.TARGET
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in (1440, 390):
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.goto(f"{base}/problems/{target}/review/", wait_until="networkidle")
                m = page.evaluate(MEASURE)
                page.screenshot(path=str(out / f"review-page-{width}.png"), full_page=True)
                for sid in SECTIONS:
                    shot(page, f"section.review-section:has(#{sid})", out / f"review-{sid}-{width}.png")
                report[f"review@{width}"] = m
                page.goto(f"{base}/problems/{target}/", wait_until="networkidle")
                tag = shot(page, ".problem-id-row", out / f"review-state-line-{width}.png")
                report[f"problem@{width}"] = {
                    "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
                    "id_row": tag,
                    "state_tag": page.locator(".review-state").first.text_content(),
                    "state_href": page.locator(".review-state").first.get_attribute("href"),
                }
                page.close()
            browser.close()
        server.shutdown()
    for width in (1440, 390):
        m = report[f"review@{width}"]
        assert m["scrollWidth"] <= m["clientWidth"], (width, m["scrollWidth"], m["clientWidth"])
        assert [s["id"] for s in m["sections"]] == list(SECTIONS), m["sections"]
        assert all(s["kind"] in ("exhibits", "judgements") for s in m["sections"])
        assert report[f"problem@{width}"]["scrollWidth"] <= width
    (out / "review-measure.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
