"""F19-T9, F20-T12 screenshots and measurements: the Docs page's reading section and the guide's
section on glosses, explainers and outlines, at desktop and phone width.

Builds the site tests' fixture graph with the tested guide copied in (as the live graph carries
it), renders it, serves it, and captures the two sections. Measures the page's scrollWidth against
the viewport, whether the labels table's wrapper scrolls, and that the "Improve these words"
target exists on the page. Prints one JSON document; exit 1 when a measurement fails.

    UV_PROJECT_ENVIRONMENT=<repo>/.venv uv run --frozen --with playwright \
        python engineering/evidence/F20/shoot_docs.py --out engineering/evidence/F20
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
for rel in ("gate", "gate/tests", "site", "site/tests"):
    sys.path.insert(0, str(REPO_ROOT / rel))

import fixture  # noqa: E402 — site/tests, on the path just above
from playwright.sync_api import sync_playwright  # noqa: E402

from opn_site import model, render  # noqa: E402

REPO = "https://github.com/example/graph"
WIDTHS = {"desktop": 1440, "phone": 390}
MEASURE = """(fragment) => ({
  viewport: document.documentElement.clientWidth,
  scrollWidth: document.documentElement.scrollWidth,
  labels_table_scrolls: [...document.querySelectorAll('table.reading-labels')]
    .map(t => t.parentElement.scrollWidth > t.parentElement.clientWidth + 1),
  target_exists: document.getElementById(fragment) !== null,
})"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fragment = render.GLOSS_GUIDE_HREF.partition("#")[2]
    report: dict[str, Any] = {"fragment": fragment, "shots": []}
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        root = fixture.build(Path(tmp) / "graph")
        shutil.copyfile(REPO_ROOT / "gate" / "agents" / "AGENTS.md", root / "AGENTS.md")
        files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
        site = Path(tmp) / "site"
        for rel, body in files.items():
            dest = site / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
            port = httpd.server_address[1]
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for name, width in WIDTHS.items():
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    page.goto(f"http://127.0.0.1:{port}/docs/index.html")
                    measured = page.evaluate(MEASURE, fragment)
                    for section, selector in (
                        ("reading", "#reading"),
                        ("guide-glosses", f"#{fragment}"),
                    ):
                        page.locator(selector).scroll_into_view_if_needed()
                        page.evaluate(f"document.querySelector('{selector}').scrollIntoView()")
                        shot = args.out / f"task-12-docs-{section}-{name}.png"
                        page.screenshot(path=str(shot))
                        report["shots"].append(shot.name)
                    good = (
                        measured["scrollWidth"] <= measured["viewport"]
                        and measured["target_exists"]
                        and not any(measured["labels_table_scrolls"])
                    )
                    ok = ok and good
                    report[name] = {**measured, "ok": good}
                    page.close()
                browser.close()
            httpd.shutdown()
    report["ok"] = ok
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
