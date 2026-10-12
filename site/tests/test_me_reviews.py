"""F26-T11 / AC14: ``/me/`` lists the review questions waiting for the signed-in intent signer.

``me.js`` draws them from ``GET /session``'s ``reviews`` (the service's
``review_notice.waiting_for``), one row per question linking the review page. The first test reads
the script; the second drives the rendered ``/me/`` page in Chromium against a fake service that
answers ``GET /session`` with two questions, and takes the screenshots at 1440 and 390 (to
``$OPN_F26_SHOTS`` when set). It needs Playwright: ``uv run --frozen --with playwright pytest
site/tests/test_me_reviews.py``; without it that one test skips, which proves nothing.
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fixture import COMMIT, build

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "erdos-1094"
REVIEWS = [
    {
        "target": TARGET,
        "question": "q-1",
        "text": "Suppose 5 were the only prime. Would the conjecture hold at n = 2?",
        "page": f"/problems/{TARGET}/review/",
    },
    {
        "target": TARGET,
        "question": "q-2",
        "text": "Is k meant to range over k ≥ 2 only?",
        "page": f"/problems/{TARGET}/review/",
    },
]


def test_me_script_draws_the_session_s_reviews_linking_the_review_page() -> None:
    js = (Path(render.__file__).parent / "static" / "me.js").read_text(encoding="utf-8")
    assert "s.reviews" in js and "Questions waiting for your answer" in js
    assert '"/review/"' in js and "me-reviews" in js


# --- in a browser ---------------------------------------------------------------------------------


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class FakeService(http.server.BaseHTTPRequestHandler):
    """``GET /session`` signed in as the intent signer with two questions waiting, and an empty
    open listing; CORS names the requesting origin with credentials, as the service's does."""

    def log_message(self, *_args: object) -> None:
        return

    def cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-OPN-Web")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/session":
            doc: Any = {
                "signed_in": True,
                "login": "carol",
                "pseudonym": "carol",
                "curator": False,
                "stewards": [],
                "expires": "2026-10-13T12:00:00Z",
                "awaiting": {"votes": [], "invitations": []},
                "reviews": REVIEWS,
            }
        elif self.path == "/submissions.json":
            doc = {"open": [], "recent": []}
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(doc).encode("utf-8")
        self.send_response(200)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    api_server, api = serve(FakeService)
    root = build(tmp_path_factory.mktemp("me-reviews-graph"))
    site_dir = tmp_path_factory.mktemp("me-reviews-site")
    render.write(
        render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=api), site_dir
    )

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

    site_server, origin = serve(functools.partial(Quiet, directory=str(site_dir)))
    yield origin
    site_server.shutdown()
    api_server.shutdown()


def test_me_lists_each_waiting_question_with_its_review_page(
    site: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    shots = Path(os.environ.get("OPN_F26_SHOTS") or tmp_path_factory.mktemp("shots"))
    shots.mkdir(parents=True, exist_ok=True)
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(site + "/me/")
        page.wait_for_selector(".me-reviews li")
        rows = page.locator(".me-reviews li")
        assert rows.count() == 2
        assert rows.nth(0).inner_text() == f"{TARGET} · q-1: {REVIEWS[0]['text']}"
        assert rows.nth(1).locator("a").get_attribute("href") == f"/problems/{TARGET}/review/"
        heading = page.locator(".me-section h2", has_text="Questions waiting for your answer")
        assert heading.count() == 1
        for label, width in (("desktop", 1440), ("phone", 390)):
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_timeout(100)
            assert page.evaluate("document.documentElement.scrollWidth") <= width, label
            page.screenshot(path=str(shots / f"me-reviews-{label}.png"), full_page=True)
        browser.close()
