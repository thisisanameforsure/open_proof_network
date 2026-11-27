"""F34 round 2 evidence: raw statement ids a reader can see on a problem page.

    PYTHONPATH=gate:site:api uv run --frozen --with 'playwright==1.58.0' python \
        engineering/evidence/F34/scan_ids.py <rendered dir> <graph> <problem> [width]

Opens the page as rendered from the live graph, and lists every visible text run that carries a
statement id of the problem's graph.json (or a route id, ``<id>@<n>``), with the section it is
in. Allowed places (ROUND-2 "Done means"): the sidenotes (.margin-notes), the Record section
(§6) and a panel's Record tab; and, by the round's own D1 and the mockup, the breadcrumb and a
List row's "through …" line. A statement with no name of its own shows its id in its name's place
(F34-T43, as the mockup's "no short name yet" boxes do): those are listed and counted apart.
Everything else is a finding.
"""

import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

src, graph, problem = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
width = int(sys.argv[4]) if len(sys.argv) > 4 else 1440
ids = sorted(
    (
        n["node_id"]
        for n in json.loads((graph / "targets" / problem / "graph.json").read_text())["nodes"]
    ),
    key=len,
    reverse=True,
)

SCAN = """(ids) => {
  const allowed = '.margin-notes, .crumbs, .route-through, details.record, #record ~ *, script, style, title';
  // a statement with no name of its own is headed or labelled by its id (F34-T43): counted apart
  const unnamed = '.is-id, a.mono, .panel-title.mono';
  const out = [];
  const walker = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.nodeValue;
    const hit = ids.find(i => text.includes(i) && (i.includes('-') || i.includes('@')));
    if (!hit) continue;
    const el = n.parentElement;
    // a statement's panel is hidden until its statement is selected: its words count as seen
    const panel = el ? el.closest('.panel[data-node]') : null;
    const seen = el && (panel ? !el.closest('[hidden]:not(.panel):not(.panel-sec)') : el.checkVisibility());
    if (!el || !seen || el.closest(allowed) || el.closest('svg title')) continue;
    if (el.closest('title')) continue;
    const where = el.closest('section, aside, nav, .panel');
    out.push({id: hit, text: text.trim().slice(0, 90), unnamed: !!el.closest(unnamed),
              in: (where ? (where.className.baseVal ?? where.className) : '?') + ' > ' + el.tagName.toLowerCase() + '.' + (el.className.baseVal ?? el.className)});
  }
  return out;
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


with socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=src)) as srv:
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": width, "height": 1000})
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/problems/{problem}/")
        pg.wait_for_timeout(1000)
        found = []
        for state in ("as it opens", "List", "harder routes shown"):
            if state == "List" and pg.locator('.route-tabs [aria-controls="sets-list"]').count():
                pg.locator('.route-tabs [aria-controls="sets-list"]').click()
            if state == "harder routes shown" and pg.locator("button.harder-link").count():
                pg.locator("button.harder-link").click()
            pg.wait_for_timeout(300)
            for hit in pg.evaluate(SCAN, ids):
                if hit not in found:
                    found.append(hit)
                    print(json.dumps({"state": state, **hit}))
        named = [h for h in found if not h["unnamed"]]
        print(
            json.dumps(
                {
                    "problem": problem,
                    "width": width,
                    "findings": len(named),
                    "ids_of_statements_with_no_name": len(found) - len(named),
                }
            )
        )
        b.close()
