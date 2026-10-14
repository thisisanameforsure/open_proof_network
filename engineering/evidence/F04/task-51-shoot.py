"""F04-T51 measurements and screenshots: does every formula in a statement panel fit its box?

Renders erdos-1094 from an export of the live graph (``--live-graph DIR --commit SHA``), opens
every node's panel in turn at 1440 and 390, and counts the panel formulas whose drawn extent is
wider than the box they sit in (``test_finding_panel_math_wrap.OVERFLOW``), split by whether the
formula is in a marked scrolling fallback box (``.math-overflows``), with every fold closed (as
a reader first sees it) and then with every fold open. Captures the panels of erdos-1094--h2 and
of the root at both widths, tagged ``--tag`` (``before`` or ``after``). With ``--pages`` it
measures the statement pages (``/nodes/<t>/<node>/``) as well. With ``--fallback`` it shoots the
test tree's unbreakable formula in its scrolling box instead.

    PYTHONPATH=gate:gate/tests:api:api/tests:site:site/tests \
        uv run --frozen --with playwright python engineering/evidence/F04/task-51-shoot.py \
        --out engineering/evidence/F04 --live-graph DIR --commit SHA --tag after [--pages]
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
from typing import Any

import fixture
import harness
import test_finding_panel_math_wrap as wrap
from playwright.sync_api import sync_playwright
from test_finding_panel_math_wrap import OPEN_FOLDS, OVERFLOW, wrap_tree
from test_outline_links import page_of

from opn_site import model, render

TARGET = "erdos-1094"
SHOTS = ("erdos-1094--h2", "erdos-1094")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--live-graph", type=Path, required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--pages", action="store_true")
    ap.add_argument("--fallback", action="store_true")
    args = ap.parse_args()
    if args.fallback:
        fallback(args)
        return
    site_model = model.load_site(args.live_graph, args.commit)
    with tempfile.TemporaryDirectory() as tmp:
        files = render.render_site(site_model, repo_url="https://github.com/example/graph")
        site = Path(tmp) / "site"
        render.write(files, site)
        handler = functools.partial(Quiet, directory=str(site))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            report: dict[str, object] = {}
            with sync_playwright() as p:
                b = p.chromium.launch()
                for width in (1440, 390):
                    pg = b.new_page(viewport={"width": width, "height": 900})
                    pg.goto(f"{base}/problems/{TARGET}/")
                    pg.wait_for_load_state("networkidle")
                    ids = pg.eval_on_selector_all(
                        ".panel[data-node]", "els => els.map(e => e.dataset.node)"
                    )
                    panels, opened = measure_panels(pg, base, ids, args, width)
                    report[f"panels@{width}"] = summarise(panels)
                    report[f"panels, folds open@{width}"] = summarise(opened)
                    if args.pages:
                        pages: dict[str, object] = {}
                        for nid in ids:
                            pg.goto(f"{base}/nodes/{TARGET}/{nid}/")
                            pg.wait_for_load_state("networkidle")
                            pg.evaluate(OPEN_FOLDS, "main")
                            pg.wait_for_timeout(100)
                            pages[nid] = pg.evaluate(OVERFLOW, "main")
                        report[f"pages, folds open@{width}"] = summarise(pages)
                    pg.close()
                b.close()
            print(json.dumps({args.tag: report}, ensure_ascii=False, indent=1))


def measure_panels(
    pg: Any, base: str, ids: list[str], args: argparse.Namespace, width: int
) -> tuple[dict[str, object], dict[str, object]]:
    """Each node's panel as first shown, then with every fold open; the two panels in SHOTS
    captured as first shown."""
    panels: dict[str, object] = {}
    opened: dict[str, object] = {}
    for nid in ids:
        pg.goto(f"{base}/problems/{TARGET}/#node={nid}")
        pg.wait_for_timeout(150)
        sel = f'.panel[data-node="{nid}"]'
        panels[nid] = pg.evaluate(OVERFLOW, sel)
        if nid in SHOTS:
            panel = pg.locator(sel)
            panel.scroll_into_view_if_needed()
            panel.screenshot(path=str(args.out / f"task-51-{args.tag}-{nid}-{width}.png"))
        pg.evaluate(OPEN_FOLDS, sel)
        pg.wait_for_timeout(100)
        opened[nid] = pg.evaluate(OVERFLOW, sel)
    return panels, opened


def fallback(args: argparse.Namespace) -> None:
    """The test tree's hole whose formula cannot break: its panel at 390, the box scrolled to
    its middle, showing the bar that says there is more."""
    with tempfile.TemporaryDirectory() as tmp:
        root = wrap_tree(Path(tmp) / "graph")
        page_of(root)
        site = Path(tmp) / "site"
        render.write(
            render.render_site(model.load_site(root, fixture.COMMIT), repo_url=wrap.REPO), site
        )
        handler = functools.partial(Quiet, directory=str(site))
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            with sync_playwright() as p:
                # Headless Chromium hides every scrollbar unless told not to.
                b = p.chromium.launch(ignore_default_args=["--hide-scrollbars"])
                pg = b.new_page(viewport={"width": 390, "height": 900})
                pg.goto(f"{base}/problems/{harness.TARGET}/#node={wrap.HOLE_IDS[1]}")
                pg.wait_for_load_state("networkidle")
                panel = pg.locator(f'.panel[data-node="{wrap.HOLE_IDS[1]}"]')
                box = panel.locator(".claim-math .math-break").first
                facts = (
                    "e => [e.className, e.scrollWidth, e.clientWidth,"
                    " e.offsetHeight - e.clientHeight]"
                )
                print(json.dumps(box.evaluate(facts)))
                panel.locator('[data-section="claim"]').screenshot(
                    path=str(args.out / "task-51-fallback-390.png")
                )
                b.close()


def summarise(per: dict[str, object]) -> dict[str, object]:
    formulas = sum(len(v) for v in per.values())  # type: ignore[arg-type]
    over = {k: [f for f in v if f["over"]] for k, v in per.items()}  # type: ignore[union-attr]
    # Wider than its box and not in a marked fallback box: cut off as the reader sees it (a
    # .katex-display box scrolls, but shows no bar on macOS until it is scrolled).
    hidden = sum(1 for v in over.values() for f in v if not f["fallback"])
    marked = sum(1 for v in over.values() for f in v if f["fallback"] and f["scrolls"])
    return {
        "formulas": formulas,
        "overflowing_cut_off": hidden,
        "overflowing_in_marked_scroll_box": marked,
        "where": {
            k: [(f["width"], f["box"], f["fallback"], f["slot"], f["tex"][:60]) for f in v]
            for k, v in over.items()
            if v
        },
    }


if __name__ == "__main__":
    main()
