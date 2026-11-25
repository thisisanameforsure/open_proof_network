"""F34 captures: pages of the live graph rendered by this tree, at 1440 and 390, light and dark.

    PYTHONPATH=gate:site uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/shoot.py --graph <graph worktree at origin/main> \
        --tag task-1 [--pages home,problems,...]

Each capture is the viewport's top (not the full page, which runs to tens of thousands of pixels
on today's Docs and Problems) plus a JSON line per page: the page's ``scrollWidth`` against the
viewport width, the families the browser actually used for body text, a heading and the nav, and
whether every vendored font file answered 200.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import subprocess
import tempfile
import threading
from pathlib import Path

PAGES = {
    "home": "/",
    "problems": "/problems/",
    "erdos-257": "/problems/erdos-257/",
    "abc": "/problems/abc/",
    "singmaster": "/problems/singmaster/",
    "contributors": "/contributors/",
    "docs": "/docs/",
    "rules": "/rules/",
    "about": "/about/",
}

PROBE = """() => {
  const fam = (sel) => { const el = document.querySelector(sel);
    return el ? getComputedStyle(el).fontFamily.split(',')[0].replaceAll('"', '') : null; };
  return { scrollWidth: document.documentElement.scrollWidth, width: window.innerWidth,
           body: fam('main p') , heading: fam('main h1, main h2'), nav: fam('.site-nav a'),
           fontsLoaded: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight + ' ' + f.style) };
}"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True, type=Path)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    from opn_site import model, render  # noqa: PLC0415

    commit = subprocess.run(
        ["git", "-C", str(args.graph), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    files = render.render_site(
        model.load_site(args.graph, commit), repo_url="https://github.com/example/graph"
    )
    with tempfile.TemporaryDirectory() as tmp:
        render.write(files, Path(tmp))
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
        handler.log_message = lambda *a: None  # type: ignore[method-assign]
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            failed: list[str] = []
            with sync_playwright() as p:
                b = p.chromium.launch()
                for name in args.pages.split(","):
                    for scheme in ("light", "dark"):
                        for width in (1440, 390):
                            ctx = b.new_context(
                                viewport={"width": width, "height": 1100}, color_scheme=scheme
                            )
                            pg = ctx.new_page()
                            pg.on(
                                "response",
                                lambda r: (
                                    failed.append(r.url)
                                    if "/fonts/" in r.url and r.status != 200
                                    else None
                                ),
                            )
                            # today's Problems page is ~113,000px and never idles inside 30 s
                            pg.goto(base + PAGES[name], wait_until="load", timeout=180_000)
                            pg.evaluate("document.fonts.ready")
                            shot = args.out / f"{args.tag}-{name}-{scheme}-{width}.png"
                            if scheme == "light" or width == 1440:
                                pg.screenshot(path=str(shot))
                            probe = pg.evaluate(PROBE)
                            line = {"page": name, "scheme": scheme, **probe}
                            line["fontsLoaded"] = sorted(set(probe["fontsLoaded"]))
                            print(json.dumps(line))
                            ctx.close()
                b.close()
            print(json.dumps({"graph_commit": commit, "font_responses_not_200": failed}))


if __name__ == "__main__":
    main()
