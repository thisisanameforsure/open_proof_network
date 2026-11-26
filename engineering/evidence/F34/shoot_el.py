"""F34 evidence: one element of a problem page on the live graph's render, at 1440 and 390.

    PYTHONPATH=gate:site:api uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/shoot_el.py <graph> <out dir> <tag> <css selector> [problem]
Prints, per width, the element's box and the page's scrollWidth.
"""

import functools, http.server, json, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import config, model, render

graph, out, tag, sel = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
problem = sys.argv[5] if len(sys.argv) > 5 else "erdos-257"
commit = subprocess.run(["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True,
                        text=True, check=True).stdout.strip()
files = render.render_site(model.load_site(graph, commit), repo_url="https://github.com/example/graph",
                           featured_target=config.DEFAULT_FEATURED_TARGET)
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
    h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                pg = b.new_page(viewport={"width": width, "height": 1000})
                pg.goto(base + f"/problems/{problem}/")
                pg.wait_for_timeout(800)
                el = pg.locator(sel).first
                if el.count() and el.is_visible():
                    el.scroll_into_view_if_needed()
                    el.screenshot(path=str(out / f"{tag}-{width}.png"))
                    box = el.bounding_box()
                else:
                    box = None
                print(json.dumps({"width": width, "box": box,
                                  "scrollWidth": pg.evaluate("document.documentElement.scrollWidth")}))
                pg.close()
            b.close()
