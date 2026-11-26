"""F34 evidence: the top of a problem page on the live graph's render, at 1440 and 390, beside the
mockup's screenshot of the same width (cropped to the same height).

    PYTHONPATH=gate:site:api uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/shoot_head.py <graph worktree> <out dir> <tag> [problem] [height]
"""

import functools, http.server, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
from opn_site import config, model, render

graph, out, tag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
problem = sys.argv[4] if len(sys.argv) > 4 else "erdos-257"
height = int(sys.argv[5]) if len(sys.argv) > 5 else 700
mock = Path("site/docs/design_handoff_2026-11/screenshots")
commit = subprocess.run(
    ["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
).stdout.strip()
files = render.render_site(
    model.load_site(graph, commit),
    repo_url="https://github.com/example/graph",
    featured_target=config.DEFAULT_FEATURED_TARGET,
)
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
    h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for width, kind in ((1440, "desktop"), (390, "phone")):
                pg = b.new_page(viewport={"width": width, "height": height})
                pg.goto(base + f"/problems/{problem}/")
                pg.wait_for_timeout(800)
                live = out / f"{tag}-{width}.png"
                pg.screenshot(path=str(live))
                print(width, "scrollWidth", pg.evaluate("document.documentElement.scrollWidth"))
                pg.close()
                ref = mock / f"New-Erdos257-{kind}.png"
                if not ref.exists():
                    ref = mock / ("New-Erdos257-desktop.png" if kind == "desktop" else "New-Phone-Select-phone.png")
                if ref.exists():
                    a = Image.open(ref); r = width / a.width
                    a = a.resize((width, int(a.height * r))).crop((0, 0, width, height))
                    l = Image.open(live).convert("RGB")
                    both = Image.new("RGB", (width * 2 + 20, height), "white")
                    both.paste(a.convert("RGB"), (0, 0)); both.paste(l, (width + 20, 0))
                    both.save(out / f"{tag}-{width}-side.jpg", quality=80)
            b.close()
