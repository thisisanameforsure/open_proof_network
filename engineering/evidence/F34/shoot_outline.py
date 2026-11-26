"""F34-T17 evidence: the phone outline on the live render — the route as an outline at 390, then a
statement tapped and its record open under it."""

import functools, http.server, json, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import model, render

graph, out, target = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
commit = subprocess.run(
    ["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
).stdout.strip()
files = render.render_site(
    model.load_site(graph, commit), repo_url="https://github.com/example/graph"
)
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
    h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 390, "height": 844})
            pg.emulate_media(reduced_motion="reduce")
            pg.goto(
                f"http://127.0.0.1:{srv.server_address[1]}/problems/{target}/", wait_until="load"
            )
            pg.locator(".route-outline").scroll_into_view_if_needed()
            pg.screenshot(path=str(out / f"task-17-{target}-outline-390.png"))
            rows = pg.evaluate(
                "[...document.querySelectorAll('.route-outline > li')].filter(l => l.checkVisibility()).map(l => [l.dataset.node, l.className])"
            )
            tap = rows[min(2, len(rows) - 1)][0]
            pg.locator(f'.route-outline > li[data-node="{tap}"] > a').click()
            pg.locator(
                f'.route-outline > li[data-node="{tap}"] > .panel'
            ).scroll_into_view_if_needed()
            pg.screenshot(path=str(out / f"task-17-{target}-tapped-390.png"))
            print(
                json.dumps(
                    {
                        "target": target,
                        "rows_shown": len(rows),
                        "first": rows[:4],
                        "tapped": tap,
                        "min_row_height": pg.evaluate(
                            "Math.min(...[...document.querySelectorAll('.route-outline > li > a')].filter(a => a.checkVisibility()).map(a => a.getBoundingClientRect().height))"
                        ),
                        "scrollWidth": pg.evaluate("document.documentElement.scrollWidth"),
                        "graph_commit": commit,
                    }
                )
            )
            b.close()
