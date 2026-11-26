"""F34-T21: every page beside its mockup, at 1440 and 390 — the live graph rendered by this tree,
captured full-page, and composed next to the handoff's screenshot (each scaled to one width)."""

import functools
import http.server
import json
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from opn_site import config, model, render

graph, mockups, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
PAIRS = {
    "Home": "/",
    "Problems": "/problems/",
    "Problem-abc": "/problems/abc/",
    "Erdos257": "/problems/erdos-257/",
    "Docs-Home": "/docs/",
    "Docs-Article": "/docs/token/",
    "Contributors": "/contributors/",
    "Steward-Signup": "/steward/erdos-1094/",
    "Review": "/problems/erdos-257/review/",
}
WIDTH = {"desktop": 1440, "phone": 390}
CAP = 6000  # px of page height kept, so a long page stays comparable to its mockup

commit = subprocess.run(
    ["git", "-C", str(graph), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
).stdout.strip()
files = render.render_site(
    model.load_site(graph, commit),
    repo_url="https://github.com/example/graph",
    featured_target=config.DEFAULT_FEATURED_TARGET,
)
report = []
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
    h.log_message = lambda *a: None  # type: ignore[method-assign]
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name, path in PAIRS.items():
                for form, width in WIDTH.items():
                    mock = mockups / f"New-{name}-{form}.png"
                    if not mock.is_file():
                        continue
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    pg.emulate_media(reduced_motion="reduce")
                    pg.goto(base + path, wait_until="load", timeout=180_000)
                    pg.wait_for_timeout(600)
                    shot = out / f"ours-{name}-{form}.png"
                    pg.screenshot(path=str(shot), full_page=True)
                    height = pg.evaluate("document.documentElement.scrollHeight")
                    pg.close()
                    a, o = Image.open(mock).convert("RGB"), Image.open(shot).convert("RGB")
                    o = o.crop((0, 0, o.width, min(o.height, CAP)))
                    w = width if form == "desktop" else 390
                    a = a.resize((w, round(a.height * w / a.width)))
                    o = o.resize((w, round(o.height * w / o.width)))
                    side = Image.new("RGB", (w * 2 + 24, max(a.height, o.height)), "white")
                    side.paste(a, (0, 0))
                    side.paste(o, (w + 24, 0))
                    side.save(out / f"side-{name}-{form}.png")
                    report.append(
                        {
                            "page": name,
                            "form": form,
                            "path": path,
                            "mockup_h": a.height,
                            "ours_h": height,
                        }
                    )
            b.close()
print(json.dumps({"graph_commit": commit, "pairs": report}, indent=1))
