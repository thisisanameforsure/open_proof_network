"""F30-T4 (AC9): captures of the one statement graph on a full render of the live graph.

Usage: ``uv run --frozen --with playwright python engineering/evidence/F30/shoot.py <site dir>
<target> [--out DIR] [--static]``. Serves the rendered site locally and captures, per theme at
1440 and at 390: the page's statements section as it opens (the routes layout), the drawing after
a set is selected (the tree), one frame mid-transition, and after a selector edge is selected (a
segment); it also writes ``measure.json`` with the shared-node displacement between neighbouring
sets and the scroll width at 390. ``--static`` captures only the opening state (no script yet).
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


#: Each visible node's place in layout units (its translate), so a scroll of the page or a
#: rescale of the svg between views cannot read as movement.
BOXES = """() => {
  const out = {};
  document.querySelectorAll('svg.dag [data-node]').forEach(g => {
    if (getComputedStyle(g).display === 'none') return;
    const m = /translate\\(([-\\d.]+),\\s*([-\\d.]+)\\)/.exec(g.getAttribute('transform') || '');
    if (m) out[g.getAttribute('data-node')] = [parseFloat(m[1]), parseFloat(m[2])];
  });
  return out;
}"""


def displacement(a: dict[str, list[float]], b: dict[str, list[float]]) -> dict[str, float]:
    shared = sorted(set(a) & set(b))
    if not shared:
        return {"shared": 0, "still": 0, "median": 0.0, "max": 0.0}
    moves = sorted(abs(a[k][0] - b[k][0]) + abs(a[k][1] - b[k][1]) for k in shared)
    still = sum(1 for m in moves if m < 1)
    return {"shared": len(shared), "still": still, "median": moves[len(moves) // 2], "max": moves[-1]}


def main() -> None:  # noqa: PLR0915
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=Path)
    ap.add_argument("target")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    ap.add_argument("--static", action="store_true")
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(Quiet, directory=str(args.site))
    measure: dict[str, Any] = {}
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{args.target}/"
        with sync_playwright() as p:
            b = p.chromium.launch()
            for theme in ("dark", "light"):
                for width in (1440, 390):
                    pg = b.new_page(viewport={"width": width, "height": 1000}, color_scheme=theme)
                    pg.goto(url)
                    pg.wait_for_load_state("networkidle")
                    tag = f"{args.target}-{width}-{theme}"
                    section = pg.locator("section.statements-section")
                    section.scroll_into_view_if_needed()
                    section.screenshot(path=str(out / f"{tag}-opening.png"))
                    if width == 390:
                        measure[f"scrollWidth-{theme}"] = pg.evaluate(
                            "() => [document.documentElement.scrollWidth, window.innerWidth]"
                        )
                    if args.static:
                        pg.close()
                        continue
                    leaves = pg.locator("svg.selector .sel-node.kind-leaf")
                    edges = pg.locator("svg.selector .sel-edge[data-view]")
                    if leaves.count() == 0:
                        pg.close()
                        continue
                    before = pg.evaluate(BOXES)
                    leaves.nth(0).click()
                    time.sleep(0.35)  # inside the 400 ms move
                    pg.locator(".dag-wrap").screenshot(path=str(out / f"{tag}-mid-transition.png"))
                    time.sleep(1.0)
                    first = pg.evaluate(BOXES)
                    pg.mouse.move(5, 5)
                    section.screenshot(path=str(out / f"{tag}-set-selected.png"))
                    if leaves.count() > 1:
                        leaves.nth(1).click()
                        time.sleep(1.2)
                        second = pg.evaluate(BOXES)
                        measure[f"set1-to-set2-{tag}"] = displacement(first, second)
                        measure[f"routes-to-set1-{tag}"] = displacement(before, first)
                    if edges.count():
                        edges.nth(0).click()
                        time.sleep(1.2)
                        pg.mouse.move(5, 5)
                        section.screenshot(path=str(out / f"{tag}-edge-selected.png"))
                    pg.keyboard.press("Escape")
                    time.sleep(1.2)
                    restored = pg.evaluate(BOXES)
                    measure[f"restored-equals-opening-{tag}"] = restored == before
                    pg.close()
            b.close()
    (out / f"measure-{args.target}.json").write_text(json.dumps(measure, indent=1))
    print(json.dumps(measure, indent=1))


if __name__ == "__main__":
    main()
