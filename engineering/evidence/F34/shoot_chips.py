"""F34-T27 evidence: the "+ n speculative ↓" chips on the live graph's render, and a click on one.

    PYTHONPATH=gate:site:api uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/shoot_chips.py <graph worktree at origin/main> <out dir>
"""

import functools, http.server, json, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import config, model, render

graph, out = Path(sys.argv[1]), Path(sys.argv[2])
commit = subprocess.run(
    ["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
).stdout.strip()
files = render.render_site(
    model.load_site(graph, commit),
    repo_url="https://github.com/example/graph",
    featured_target=config.DEFAULT_FEATURED_TARGET,
)
pages = {k: v for k, v in files.items() if k.startswith("problems/") and k.endswith("/index.html")}
counts = {k: v.count('class="spec-chip"') for k, v in pages.items()}
print(json.dumps({"pages_with_chips": sum(1 for n in counts.values() if n),
                  "chips": sum(counts.values()),
                  "erdos-257": counts.get("problems/erdos-257/index.html")}))
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
                pg.wait_for_timeout(500)
                chip = pg.locator("svg.dag g.spec-chip").first
                if not chip.is_visible():  # a phone shows the outline in place of the drawing
                    more = pg.locator("a.spec-more:visible").first
                    more.scroll_into_view_if_needed()
                    r = more.bounding_box()
                    pg.screenshot(path=str(out / f"task-27-outline-{width}.png"),
                                  clip={"x": 0, "y": max(0, r["y"] - 200), "width": width,
                                        "height": 320})
                    before = pg.evaluate("() => location.hash")
                    more.click()
                    pg.wait_for_timeout(600)
                    after = pg.evaluate(
                        "() => [location.hash, Math.round(document.querySelector('.off-group')"
                        ".getBoundingClientRect().top), document.documentElement.scrollWidth]"
                    )
                    pg.screenshot(path=str(out / f"task-27-after-click-{width}.png"))
                    print(json.dumps({"width": width, "outline_link": r, "before": before,
                                      "after": after}))
                    pg.close()
                    continue
                chip.scroll_into_view_if_needed()
                box = chip.bounding_box()
                pill = pg.evaluate(
                    "() => (g => { const r = g.closest('g.node').querySelector('rect.pill')"
                    ".getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })"
                    "(document.querySelector('svg.dag g.spec-chip'))"
                )
                pad = 120
                clip = {"x": max(0, pill[0] - pad), "y": max(0, pill[1] - pad),
                        "width": min(width - max(0, pill[0] - pad), pill[2] + 2 * pad),
                        "height": pill[3] + 2 * pad}
                pg.screenshot(path=str(out / f"task-27-chip-{width}.png"), clip=clip)
                before = pg.evaluate("() => [location.hash, document.querySelector('svg.dag').dataset.view]")
                chip.click()
                pg.wait_for_timeout(600)
                after = pg.evaluate(
                    "() => [location.hash, document.querySelector('svg.dag').dataset.view,"
                    " Math.round(document.querySelector('.off-group').getBoundingClientRect().top)]"
                )
                pg.screenshot(path=str(out / f"task-27-after-click-{width}.png"))
                print(json.dumps({"width": width, "chip_box": box, "pill": pill,
                                  "before": before, "after": after}))
                pg.close()
            b.close()
