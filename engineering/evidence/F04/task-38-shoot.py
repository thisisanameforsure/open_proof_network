"""F04-T38 screenshots and measurements: the literature status on a local render of the live
graph whose products were rewritten as the v3.35 gate writes them, with a hand-made literature
pair on erdos-1094: ``--h2`` a proposed `open` (awaiting), ``--h3`` a confirmed `known`
(Konyagin 1999) with a later proposal.

Serves the rendered site and shoots, at 1440 and 390: the two node pages' literature blocks,
erdos-1094's statement card, and /me/ — for which the service is stubbed at the browser
(Playwright routes GET /session to a signed-in curator, GET /submissions.json to an empty list,
and POST /literature/confirm to a 201), so the page's own script draws the lists and the Confirm
control, one Confirm is clicked, and the body the script sent is printed as the evidence of the
request shape assumed. Measures scrollWidth at 390 and the bounding box of every reference
link against its list item. Prints a JSON report.

    uv run --with playwright python engineering/evidence/F04/task-38-shoot.py \
        --site <rendered site> --out engineering/evidence/F04 --api https://api.openproofnetwork.org
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

H2 = "/nodes/erdos-1094/erdos-1094--h2/"
H3 = "/nodes/erdos-1094/erdos-1094--h3/"
PROBLEM = "/problems/erdos-1094/"
SESSION = {
    "signed_in": True,
    "login": "thisisanameforsure",
    "pseudonym": "thisisanameforsure",
    "curator": True,
    "stewards": ["erdos-1094"],
}
MEASURE_REFS = """
() => Array.from(document.querySelectorAll('.literature-refs li')).map(li => {
  const r = li.getBoundingClientRect(); const a = li.querySelector('a');
  const b = a ? a.getBoundingClientRect() : null;
  return {text: li.textContent.slice(0, 60), link: Boolean(a),
          inside: !a || (b.left >= r.left - 1 && b.right <= r.right + 1)};
})
"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None  # type: ignore[attr-defined]
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def shot(page: Any, selector: str, path: Path) -> str:
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    el.screenshot(path=str(path))
    return " ".join(el.inner_text().split())


def stub_service(context: Any, api: str, sent: list[dict[str, Any]]) -> None:
    def session(route: Any) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(SESSION))

    def submissions(route: Any) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"open": []}))

    def confirm(route: Any) -> None:
        sent.append(json.loads(route.request.post_data or "null"))
        body = {"pr_number": 999, "pr_url": "https://github.com/thisisanameforsure/open_proof_network_graph/pull/999"}
        route.fulfill(status=201, content_type="application/json", body=json.dumps(body))

    context.route(api + "/session", session)
    context.route(api + "/submissions.json", submissions)
    context.route(api + "/literature/confirm", confirm)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--api", required=True)
    args = ap.parse_args()
    server, port = serve(args.site)
    base = f"http://127.0.0.1:{port}"
    report: dict[str, Any] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (1440, 390):
            sent: list[dict[str, Any]] = []
            context = browser.new_context(viewport={"width": width, "height": 900})
            stub_service(context, args.api.rstrip("/"), sent)
            page = context.new_page()
            for name, path in (("h3-known", H3), ("h2-proposed", H2)):
                page.goto(base + path, wait_until="networkidle")
                report[f"{name}@{width}"] = {
                    "block": shot(page, 'div[data-block="literature"]', args.out / f"task-38-{name}-{width}.png"),
                    "refs": page.evaluate(MEASURE_REFS),
                    "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
                }
            page.goto(base + PROBLEM + "#node=erdos-1094--h3", wait_until="networkidle")
            page.wait_for_timeout(300)
            report[f"panel@{width}"] = {
                "block": shot(page, '.panel[data-node="erdos-1094--h3"] div[data-block="literature"]', args.out / f"task-38-panel-h3-{width}.png"),
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
            }
            page.goto(base + "/me/", wait_until="networkidle")
            page.wait_for_selector(".literature-waiting:not([hidden]) .lit-row button")
            lists = page.locator(".literature-waiting:not([hidden])")
            rows = page.locator(".literature-waiting:not([hidden]) .lit-row")
            buttons = page.locator(".lit-row button")
            section = page.locator("section.me-section", has_text="Literature statuses").first
            section.scroll_into_view_if_needed()
            section.screenshot(path=str(args.out / f"task-38-me-{width}.png"))
            report[f"me@{width}"] = {
                "static_buttons_in_html": page.evaluate("document.documentElement.outerHTML").count("<button") - buttons.count() - page.locator(".me-step-down button").count(),
                "lists_shown": lists.count(),
                "targets": [lists.nth(i).get_attribute("data-target") for i in range(lists.count())],
                "rows": [" ".join(rows.nth(i).inner_text().split()) for i in range(rows.count())],
                "scrollWidth": page.evaluate("document.documentElement.scrollWidth"),
            }
            # Click the first Confirm: the stub answers 201, the row shows the receipt.
            buttons.first.click()
            page.wait_for_selector(".lit-row .receipt")
            section.screenshot(path=str(args.out / f"task-38-me-confirmed-{width}.png"))
            report[f"me@{width}"]["confirm_request_body"] = sent
            report[f"me@{width}"]["receipt"] = " ".join(page.locator(".lit-row .receipt").first.inner_text().split())
            context.close()
        browser.close()
    server.shutdown()
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
