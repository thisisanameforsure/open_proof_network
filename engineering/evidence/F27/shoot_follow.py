"""F27-T10 (R13, AC14): captures of the "Stop at proved statements" toggle on a full render of the
live graph.

Usage: ``uv run --frozen --with playwright python engineering/evidence/F27/shoot_follow.py
<site dir> <target> [--out DIR]``. Serves the rendered site locally and captures, at 1440: the
selector panel with the toggle as the page opens; the first set selected with the toggle ticked
(the set stops at its proved statements); the same set with the toggle unticked (the proved
structure beneath them shown); and the sets table under both readings. It writes
``measure-follow-<target>.json``: the selector's node positions under both readings (they must
be equal), the drawing's shown nodes under each, the table's first row under each, the embedded
layouts JSON size and the number of ``follow/`` views.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import socketserver
import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


SELECTOR_AT = """() => {
  const out = {};
  document.querySelectorAll('svg.selector g.sel-node').forEach(g => {
    out[g.getAttribute('data-key')] = g.getAttribute('transform');
  });
  return out;
}"""

SHOWN = """() => {
  const out = [];
  document.querySelectorAll('svg.dag [data-node]').forEach(g => {
    if (getComputedStyle(g).display !== 'none') out.push(g.getAttribute('data-node'));
  });
  return out.sort();
}"""

FIRST_ROW = """() => {
  const r = [...document.querySelectorAll('tr.set-row')].find(r => !r.hidden);
  if (!r) return null;
  return [...r.cells].map(c => c.innerText.trim().split('\\n')[0]);
}"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=Path)
    ap.add_argument("target")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    page_html = (args.site / "problems" / args.target / "index.html").read_text("utf-8")
    m = re.search(r'id="graph-layouts">(.*?)</script>', page_html, re.S)
    assert m is not None
    layouts = json.loads(m.group(1))
    measure: dict[str, Any] = {
        "layouts_json_bytes": len(m.group(1)),
        "views": len(layouts),
        "follow_views": sum(1 for k in layouts if k.startswith("follow/")),
    }
    handler = functools.partial(Quiet, directory=str(args.site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/problems/{args.target}/"
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 1000})
            pg.emulate_media(reduced_motion="reduce")
            pg.goto(url)
            pg.wait_for_load_state("networkidle")
            tag = f"{args.target}-1440"
            section = pg.locator("section.statements-section")
            section.scroll_into_view_if_needed()
            panel = pg.locator(".selector-wrap")
            panel.screenshot(path=str(out / f"{tag}-follow-panel.png"))
            box = pg.locator("input.follow-proved")
            measure["toggle_visible_on_load"] = box.is_visible()
            measure["toggle_checked_on_load"] = box.is_checked()
            leaves = pg.locator("svg.selector .sel-node.kind-leaf")
            if leaves.count():
                leaves.nth(0).click()
                time.sleep(0.4)
                pg.mouse.move(5, 5)
                measure["selector_at_stop"] = pg.evaluate(SELECTOR_AT)
                measure["shown_at_stop"] = pg.evaluate(SHOWN)
                measure["view_at_stop"] = pg.evaluate(
                    "() => document.querySelector('svg.dag').getAttribute('data-view')"
                )
                measure["first_row_at_stop"] = pg.evaluate(FIRST_ROW)
                pg.locator(".dag-wrap").screenshot(path=str(out / f"{tag}-set1-stop.png"))
                pg.locator(".sets-grid").screenshot(path=str(out / f"{tag}-table-stop.png"))
                box.uncheck()
                time.sleep(0.6)
                pg.mouse.move(5, 5)
                measure["selector_at_follow"] = pg.evaluate(SELECTOR_AT)
                measure["shown_at_follow"] = pg.evaluate(SHOWN)
                measure["view_at_follow"] = pg.evaluate(
                    "() => document.querySelector('svg.dag').getAttribute('data-view')"
                )
                measure["first_row_at_follow"] = pg.evaluate(FIRST_ROW)
                measure["hash_at_follow"] = pg.evaluate("() => location.hash")
                pg.locator(".dag-wrap").screenshot(path=str(out / f"{tag}-set1-follow.png"))
                pg.locator(".sets-grid").screenshot(path=str(out / f"{tag}-table-follow.png"))
                measure["selector_still"] = (
                    measure["selector_at_stop"] == measure["selector_at_follow"]
                )
                measure["added_when_followed"] = sorted(
                    set(measure["shown_at_follow"]) - set(measure["shown_at_stop"])
                )
                box.check()
                time.sleep(0.6)
                measure["view_after_retick"] = pg.evaluate(
                    "() => document.querySelector('svg.dag').getAttribute('data-view')"
                )
                measure["shown_after_retick_equals_stop"] = (
                    pg.evaluate(SHOWN) == measure["shown_at_stop"]
                )
            pg.close()
            b.close()
    (out / f"measure-follow-{args.target}.json").write_text(json.dumps(measure, indent=1))
    print(
        json.dumps(
            {k: v for k, v in measure.items() if not k.startswith(("selector_at", "shown_at"))},
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
