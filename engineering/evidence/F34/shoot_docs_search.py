"""F34-T10 evidence: Docs search on the live graph's render — type a query, capture, at 1440 and 390."""
import functools, http.server, json, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import config, model, render

graph, out = Path(sys.argv[1]), Path(sys.argv[2])
commit = subprocess.run(["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
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
            for width, query in ((1440, "witness"), (390, "token")):
                pg = b.new_page(viewport={"width": width, "height": 1000})
                pg.goto(base + "/docs/", wait_until="load")
                pg.fill(".docs-search input", query)
                pg.wait_for_function("() => document.querySelectorAll('.docs-results li').length > 0")
                found = pg.evaluate("[...document.querySelectorAll('.docs-results a')].map(a => a.getAttribute('href'))")
                pg.screenshot(path=str(out / f"task-10-docs-search-{width}.png"))
                print(json.dumps({"width": width, "query": query, "results": found,
                                  "scrollWidth": pg.evaluate("document.documentElement.scrollWidth")}))
            b.close()
print(json.dumps({"graph_commit": commit, "index_bytes": len(files["docs/search-index.js"])}))
