"""F23-T10: render the fixture site, open /docs/ at 1440 and 390, and measure the Stewards
section's height (its h2 to the next h2) against a 900px screen; screenshot it.

    uv run --frozen --with playwright python engineering/evidence/F23/task-10-measure.py
"""

from __future__ import annotations

import functools
import http.server
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for rel in ("gate", "gate/tests", "site", "site/tests"):
    sys.path.insert(0, str(ROOT / rel))

import fixture  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from opn_site import model, render  # noqa: E402

OUT = Path(__file__).resolve().parent
MEASURE = """() => {
  const h = document.getElementById('stewards');
  const next = document.getElementById('propose');
  h.scrollIntoView();
  return {height: next.getBoundingClientRect().top - h.getBoundingClientRect().top,
          scroll: document.documentElement.scrollWidth};
}"""

with tempfile.TemporaryDirectory() as tmp:
    root = fixture.build(Path(tmp) / "g")
    site = Path(tmp) / "site"
    render.write(
        render.render_site(
            model.load_site(root, fixture.COMMIT), repo_url="https://github.com/example/graph"
        ),
        site,
    )
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    handler.log_message = lambda *a: None  # type: ignore[method-assign]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for label, width in (("desktop", 1440), ("phone", 390)):
            page = b.new_page(viewport={"width": width, "height": 900})
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/docs/#stewards")
            m = page.evaluate(MEASURE)
            print(
                f"{label} {width}px: stewards section {m['height']:.0f}px tall, scrollWidth {m['scroll']}"
            )
            page.screenshot(path=str(OUT / f"docs-stewards-{label}.png"))
        b.close()
    server.shutdown()
