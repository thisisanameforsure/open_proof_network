"""F34-T24 evidence: the drawing's folds on the live render, at 1440 — the home route folded, then a fold
opened (the tree laid out again) — with the drawing's height in each state and the layouts' size."""
import functools, http.server, json, re, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import model, render

graph, out = Path(sys.argv[1]), Path(sys.argv[2])
targets = sys.argv[3:]
commit = subprocess.run(["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
files = render.render_site(model.load_site(graph, commit), repo_url="https://github.com/example/graph")
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
    h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            b = p.chromium.launch()
            for t in targets:
                page_html = files[f"problems/{t}/index.html"]
                lay_bytes = len(re.search(r'id="graph-layouts">(.*?)</script>', page_html, re.S).group(1))
                pg = b.new_page(viewport={"width": 1440, "height": 1100})
                pg.emulate_media(reduced_motion="reduce")
                pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/problems/{t}/", wait_until="load")
                svg = "svg.dag:not(.band)"
                folded_h = pg.evaluate(f"document.querySelector('{svg}').getAttribute('height')")
                boxes = pg.evaluate(f"[...document.querySelectorAll('{svg} g.node.fold:not(.off-view) text')].map(t => t.textContent)")
                pg.locator(".dag-scroll").scroll_into_view_if_needed()
                pg.screenshot(path=str(out / f"task-24-{t}-folded-1440.png"))
                opened_h = None
                if boxes:
                    pg.locator(f"{svg} g.node.fold:not(.off-view)").first.click()
                    pg.wait_for_function(f"document.querySelector('{svg}').getAttribute('data-view').includes('~fold')")
                    opened_h = pg.evaluate(f"document.querySelector('{svg}').getAttribute('height')")
                    pg.mouse.move(5, 5)  # no hover highlighting in the capture
                    pg.wait_for_timeout(300)
                    pg.locator(".dag-scroll").scroll_into_view_if_needed()
                    pg.screenshot(path=str(out / f"task-24-{t}-opened-1440.png"))
                print(json.dumps({"target": t, "boxes": boxes, "drawing_height_folded": folded_h, "drawing_height_opened": opened_h,
                                  "layouts_bytes": lay_bytes, "scrollWidth": pg.evaluate("document.documentElement.scrollWidth")}))
                pg.close()
            b.close()
print(json.dumps({"graph_commit": commit}))
