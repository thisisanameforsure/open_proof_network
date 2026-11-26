"""F34-T16 evidence: the panel's tabs on the live render — the problem's own statement on Claim, then a
statement selected from the drawing on Proof, with its path drawn heavier — at 1440 and 390."""
import functools, http.server, json, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import model, render

graph, out, target = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
commit = subprocess.run(["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
site = model.load_site(graph, commit)
files = render.render_site(site, repo_url="https://github.com/example/graph")
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
    h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{target}/"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width in (1440, 390):
                pg = b.new_page(viewport={"width": width, "height": 1100})
                pg.emulate_media(reduced_motion="reduce")
                pg.goto(url, wait_until="load")
                pg.locator(".panel:not([hidden])").scroll_into_view_if_needed()
                pg.screenshot(path=str(out / f"task-16-{target}-claim-{width}.png"))
                pill = pg.evaluate("[...document.querySelectorAll('svg.dag:not(.band) g.node')].map(g => g.dataset.node).find(n => n && n.includes('--h'))")
                pg.locator(f'svg.dag:not(.band) g.node[data-node="{pill}"]').click()
                panel = pg.locator(f'.panel[data-node="{pill}"]')
                panel.locator('.panel-tabs [data-tab="how"]').click()
                panel.scroll_into_view_if_needed()
                pg.screenshot(path=str(out / f"task-16-{target}-selected-{width}.png"))
                print(json.dumps({"width": width, "selected": pill,
                    "on_path": pg.evaluate("document.querySelectorAll('svg.dag path.edge.on-path').length"),
                    "visible_parts": pg.evaluate(f"[...document.querySelectorAll('.panel[data-node=\"{pill}\"] .panel-sec[data-section], .panel[data-node=\"{pill}\"] details.record')].filter(e => e.checkVisibility()).map(e => e.dataset.section || 'record')"),
                    "scrollWidth": pg.evaluate("document.documentElement.scrollWidth")}))
                pg.close()
            b.close()
print(json.dumps({"graph_commit": commit}))
