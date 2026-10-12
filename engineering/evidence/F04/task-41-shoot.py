"""F04-T41 screenshots: the fixture problem page before and after the separators, to show the
look is unchanged. Run once from a checkout of the commit before the fix and once from the fix,
each with its own tree on PYTHONPATH; then compare the PNGs pixel for pixel (``--compare``).

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-41-shoot.py \
        --out engineering/evidence/F04 --tag after
    (the same from a detached worktree at the parent commit, with --tag before)
    uv run --frozen --with playwright python engineering/evidence/F04/task-41-shoot.py \
        --out engineering/evidence/F04 --compare

Each shot is taken with the status tag hovered (its card open) and one with the page at rest;
the page's own text, as ``textContent`` reads it, is printed around the status tag and a pill.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import tempfile
import threading
from pathlib import Path

SHOTS = ("rest-1440", "card-1440", "rest-390")


def shoot(out: Path, tag: str) -> None:
    import fixture  # noqa: PLC0415
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    from opn_site import model, render  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        root = fixture.build(Path(tmp) / "g")
        files = render.render_site(
            model.load_site(root, fixture.COMMIT), repo_url="https://github.com/example/graph"
        )
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
        handler.log_message = lambda *a: None  # type: ignore[method-assign]
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{srv.server_address[1]}/problems/propositional/"
            report: dict[str, object] = {}
            with sync_playwright() as p:
                b = p.chromium.launch()
                for width in (1440, 390):
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    pg.goto(url)
                    pg.wait_for_load_state("networkidle")
                    pg.screenshot(path=str(out / f"task-41-{tag}-rest-{width}.png"), full_page=True)
                    if width == 1440:
                        status = pg.locator(".problem-id-row .term.tag").first
                        status.scroll_into_view_if_needed()
                        status.hover()
                        pg.wait_for_timeout(200)
                        pg.screenshot(path=str(out / f"task-41-{tag}-card-1440.png"))
                        report["status_tag_textContent"] = status.evaluate("e => e.textContent")
                        report["status_tag_innerText"] = status.evaluate("e => e.innerText")
                        pill = pg.locator("svg.dag a").first
                        report["pill_textContent"] = pill.evaluate("e => e.textContent")
                        report["scrollWidth"] = pg.evaluate(
                            "document.documentElement.scrollWidth"
                        )
                    pg.close()
                b.close()
            print(json.dumps({tag: report}, ensure_ascii=False, indent=2))


def compare(out: Path) -> None:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    js = """async ([a, b]) => {
      const load = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = src; });
      const [x, y] = await Promise.all([load(a), load(b)]);
      if (x.width !== y.width || x.height !== y.height)
        return {same_size: false, a: [x.width, x.height], b: [y.width, y.height]};
      const px = img => { const c = document.createElement('canvas'); c.width = img.width;
        c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
        return g.getImageData(0, 0, img.width, img.height).data; };
      const p = px(x), q = px(y); let diff = 0;
      for (let i = 0; i < p.length; i += 4)
        if (p[i] !== q[i] || p[i+1] !== q[i+1] || p[i+2] !== q[i+2]) diff++;
      return {same_size: true, size: [x.width, x.height], differing_pixels: diff};
    }"""
    import base64  # noqa: PLC0415

    result = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        for shot in SHOTS:
            a, c = (out / f"task-41-{t}-{shot}.png" for t in ("before", "after"))
            uris = [
                "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()
                for f in (a, c)
            ]
            result[shot] = pg.evaluate(js, uris)
        b.close()
    print(json.dumps({"pixel_compare_before_vs_after": result}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tag", choices=("before", "after"))
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    if args.compare:
        compare(args.out)
    else:
        shoot(args.out, args.tag)


if __name__ == "__main__":
    main()
