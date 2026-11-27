"""F34-T36 evidence: click a statement in §2 of erdos-257 (live graph rendered by this tree) and
capture the viewport, at 1440 and 390.

    PYTHONPATH=gate:site:api uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/shoot_select_off.py <graph> <out dir>
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
                pg = b.new_page(viewport={"width": width, "height": 900})
                pg.goto(base + "/problems/erdos-257/")
                pg.wait_for_timeout(800)
                li = pg.locator("section.off-route li[data-node] > a").first
                nid = li.evaluate("a => a.parentNode.dataset.node")
                li.scroll_into_view_if_needed()
                li.click()
                pg.wait_for_timeout(600)
                state = pg.evaluate("""(id) => ({shown: [...document.querySelectorAll('.panel[data-node]')]
                    .filter(p => !p.hidden).map(p => p.dataset.node), path: location.pathname,
                    top: Math.round(document.querySelector('.panel[data-node="' + id + '"]')
                    .getBoundingClientRect().top)})""", nid)
                pg.screenshot(path=str(out / f"task-36-after-click-{width}.png"))
                print(json.dumps({"width": width, "clicked": nid, **state}))
                pg.close()
            b.close()
