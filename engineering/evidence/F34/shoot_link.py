"""F34-T37 evidence: erdos-257 on the live graph's render at 1440 — the line from the selected box
to the panel at rest, and after selecting the open core — and at 390 (no line).

    PYTHONPATH=gate:site:api uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/shoot_link.py <graph> <out dir>
"""

import functools, http.server, json, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import config, model, render

graph, out = Path(sys.argv[1]), Path(sys.argv[2])
commit = subprocess.run(["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True,
                        text=True, check=True).stdout.strip()
files = render.render_site(model.load_site(graph, commit), repo_url="https://github.com/example/graph",
                           featured_target=config.DEFAULT_FEATURED_TARGET)
SHOWN = "(() => { const l = document.querySelector('svg.panel-link'); return !!l && getComputedStyle(l).display !== 'none'; })()"
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
    h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 1000})
            pg.goto(base + "/problems/erdos-257/")
            pg.wait_for_timeout(800)
            pg.locator(".graph-grid").scroll_into_view_if_needed()
            pg.wait_for_timeout(200)
            pg.screenshot(path=str(out / "task-37-link-root-1440.png"))
            print(json.dumps({"width": 1440, "at": "root", "line": pg.evaluate(SHOWN)}))
            pg.locator("svg.dag g.node:not(.selected):not(.off-view)").nth(1).click()
            pg.wait_for_timeout(800)
            pg.screenshot(path=str(out / "task-37-link-other-1440.png"))
            print(json.dumps({"width": 1440, "at": pg.evaluate("document.querySelector('svg.dag g.node.selected').dataset.node"), "line": pg.evaluate(SHOWN)}))
            pg.close()
            pg = b.new_page(viewport={"width": 390, "height": 900})
            pg.goto(base + "/problems/erdos-257/")
            pg.wait_for_timeout(800)
            print(json.dumps({"width": 390, "line": pg.evaluate(SHOWN),
                              "scrollWidth": pg.evaluate("document.documentElement.scrollWidth")}))
            pg.close()
            b.close()
