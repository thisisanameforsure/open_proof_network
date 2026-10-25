"""F31-T11 (R8; AC8): the static half of the shelving controls, and the script in a browser.

A page is static: a statement's page carries one hidden ``.shelve-act`` slot with what a
shelving record needs as data (the target, the node, whether it is shelved and by whom, when,
with what cause), and the problem page one hidden ``.retire-act`` per drawn route with the
route's partial. ``static/shelve.js`` shows Shelve, Unshelve or Retire to a signed-in steward of
the target or a curator once ``GET /session`` answers, posts to ``POST /shelvings`` and shows
the pull request as a receipt. A build with no service address carries no slot and no script.
The cause is a person's words: shown demarcated, and never read back into markup (C9, D-31).

The browser half needs Playwright (``uv run --frozen --with playwright pytest …``); without it
those tests skip, which proves nothing, and the evidence file says so.
"""

from __future__ import annotations

import functools
import http.server
import json
import re
import threading
from collections.abc import Iterator
from html import unescape
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET
from test_decompositions import HOLE_IDS
from test_products import ROOT_NODE
from test_routes_view import two_routes

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.invalid"
CAUSE = "Route 1 is <script>alert(1)</script> & a distraction"
SHELVED, OPEN = HOLE_IDS
NODE_PAGE = f"nodes/{TARGET}/{SHELVED}/index.html"
OPEN_PAGE = f"nodes/{TARGET}/{OPEN}/index.html"
ROOT_PAGE = f"nodes/{TARGET}/{ROOT_NODE}/index.html"
PROBLEM = f"problems/{TARGET}/index.html"
SLOT = re.compile(r'<div class="shelve-act" ([^>]*) hidden></div>')
RETIRE = re.compile(r'<span class="retire-act" ([^>]*) hidden></span>')
ATTR = re.compile(r'([a-z-]+)="([^"]*)"')
JS = (
    (render.STATIC / "shelve.js").read_text(encoding="utf-8")
    if (render.STATIC / "shelve.js").is_file()
    else ""
)


def attrs(raw: str) -> dict[str, str]:
    return {k: unescape(v) for k, v in ATTR.findall(raw)}


def shelved_tree(tmp_path: Path) -> Path:
    """``two_routes`` rendered, then its first hole shelved as the v3.47 gate would leave it."""
    root = two_routes(tmp_path)
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    fixture.publish_shelved(root, {SHELVED: fixture.shelved_fact(CAUSE, via=SHELVED)})
    return root


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> model.Site:
    return model.load_site(shelved_tree(tmp_path_factory.mktemp("shelving")), fixture.COMMIT)


@pytest.fixture(scope="module")
def pages(site: model.Site) -> dict[str, str]:
    return render.render_site(site, repo_url=REPO, api_url=API)


@pytest.fixture(scope="module")
def static_pages(site: model.Site) -> dict[str, str]:
    return render.render_site(site, repo_url=REPO)


def partials_of(site: model.Site) -> set[str]:
    rows = {str(n["node_id"]): n for n in site.targets[TARGET].graph["nodes"]}
    return {str(d["partial"]) for d in rows[ROOT_NODE]["decompositions"]}


# --- the statement's page -------------------------------------------------------------------------


def test_a_shelved_statement_page_carries_the_slot_with_its_data(pages: dict[str, str]) -> None:
    slots = [attrs(m) for m in SLOT.findall(pages[NODE_PAGE])]
    assert len(slots) == 1, slots
    s = slots[0]
    assert s["data-target"] == TARGET and s["data-node"] == SHELVED
    assert s["data-shelved"] == "1"
    assert s["data-cause"] == CAUSE
    assert s["data-by"] == fixture.SHELVED_BY and s["data-date"] == fixture.SHELVED_DATE


def test_an_unshelved_statement_page_carries_an_empty_slot(pages: dict[str, str]) -> None:
    slots = [attrs(m) for m in SLOT.findall(pages[OPEN_PAGE])]
    assert len(slots) == 1, slots
    s = slots[0]
    assert s["data-node"] == OPEN and s["data-shelved"] == "0"
    assert s["data-cause"] == "" and s["data-by"] == "" and s["data-date"] == ""


def test_the_root_has_no_slot(pages: dict[str, str]) -> None:
    """R1, R6: the root is never shelved (``node-root``), so its page offers no control."""
    assert not SLOT.findall(pages[ROOT_PAGE])
    assert "shelve-act" not in pages[ROOT_PAGE]


def test_the_cause_reaches_the_page_as_text(
    pages: dict[str, str], static_pages: dict[str, str]
) -> None:
    """The visible note names the signer, the date and the cause, regardless of sign-in and
    of a service address; the cause is escaped and demarcated as the literature summary is."""
    for page in (pages[NODE_PAGE], static_pages[NODE_PAGE]):
        assert "<script>alert(1)</script>" not in page
        assert render.esc(CAUSE) in page
        note = re.search(r'<div class="shelved-note[^"]*"[^>]*>.*?</div></div>', page, re.S)
        assert note is not None, "no shelving note"
        text = note.group(0)
        assert "Shelved by" in text and fixture.SHELVED_BY in text and fixture.SHELVED_DATE in text
        assert 'data-block="shelving"' in text and "untrusted" in text
        assert render.esc(CAUSE) in text
    assert "shelved-note" not in static_pages[OPEN_PAGE]


# --- the problem page -------------------------------------------------------------------------


def test_the_sets_table_offers_retire_per_route(site: model.Site, pages: dict[str, str]) -> None:
    """F31-Q18 (the owner, 2026-10-25: "incorporated into the sufficient sets table"): each set
    row names the routes it goes through, each with its retire control; no separate list. The
    fixture's route 1 has a shelved unproved hole, so no set rests on it (F31-R4) and it is in
    no row: a retire control belongs to a route a set still goes through."""
    page = pages[PROBLEM]
    assert "routes-list" not in page and "route-row" not in page
    table = re.search(r'<table class="routes-table">.*?</table>', page, re.S)
    assert table is not None
    cells = re.findall(r'<span class="set-route" data-route="([^"]*)"', table.group(0))
    assert sorted(set(cells)) == [f"{ROOT_NODE}@2"], cells
    controls = [attrs(m) for m in RETIRE.findall(table.group(0))]
    assert len(controls) == 1
    assert controls[0]["data-partial"] in partials_of(site)
    assert controls[0]["data-target"] == TARGET and controls[0]["data-node"] == ROOT_NODE
    head = re.search(r"<thead>.*?</thead>", table.group(0), re.S)
    assert head is not None and "Routes" in head.group(0)


# --- the script ---------------------------------------------------------------------------------


def test_the_script_is_present_with_a_service_and_absent_without(
    pages: dict[str, str], static_pages: dict[str, str]
) -> None:
    tag = f'<script src="/shelve.js" data-repo="{REPO}"></script>'
    assert pages[NODE_PAGE].count(tag) == 1 and pages[PROBLEM].count(tag) == 1
    for page in (static_pages[NODE_PAGE], static_pages[PROBLEM], static_pages[OPEN_PAGE]):
        assert "/shelve.js" not in page
        assert "shelve-act" not in page and "retire-act" not in page
    assert "/shelve.js" in render.SCRIPTS
    assert (render.STATIC / "shelve.js").is_file()


def test_the_script_gates_on_the_session_and_posts_the_three_shapes() -> None:
    assert JS, "static/shelve.js is missing"
    assert '"/shelvings"' in JS
    for key in ("node_id", "action", "scope", "route", "cause"):
        assert re.search(rf"\b{key}\s*:", JS), key
    for value in ('"shelved"', '"unshelved"', '"node"', '"route"'):
        assert value in JS, value
    assert "s.curator" in JS and "s.stewards.indexOf" in JS and "signed_in" in JS
    for word in ("Shelve", "Unshelve", "Retire"):
        assert word in JS, word
    assert "pr_number" in JS and "pr_url" in JS


# --- in a browser, against a fake service -------------------------------------------------------


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


POSTED: list[dict[str, Any]] = []


class FakeService(http.server.BaseHTTPRequestHandler):
    """``GET /session`` signed in as a steward of the fixture's target; ``POST /shelvings``
    records the body and answers 201 with a pull request."""

    session: dict[str, Any] = {  # noqa: RUF012 — the tests swap it to drive the gate
        "signed_in": True,
        "login": "alice-steward",
        "pseudonym": "alice-steward",
        "curator": False,
        "stewards": [TARGET],
        "expires": "2026-10-30T12:00:00Z",
        "awaiting": {"votes": [], "invitations": []},
        "reviews": [],
    }

    def log_message(self, *_args: object) -> None:
        return

    def cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-OPN-Web")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")

    def reply(self, status: int, doc: Any) -> None:
        body = json.dumps(doc).encode("utf-8")
        self.send_response(status)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(body.__len__()))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/session":
            self.reply(200, self.session)
        else:
            self.reply(404, {"error": "not-found", "message": "no"})

    def do_POST(self) -> None:
        n = int(self.headers.get("Content-Length") or 0)
        doc = json.loads(self.rfile.read(n) or b"{}")
        POSTED.append({"path": self.path, "body": doc})
        if self.path == "/shelvings":
            self.reply(201, {"pr_number": 7, "pr_url": f"{REPO}/pull/7", "branch": "append/x"})
        else:
            self.reply(404, {"error": "not-found", "message": "no"})


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    api_server, api = serve(FakeService)
    root = shelved_tree(tmp_path_factory.mktemp("shelving-graph"))
    site_dir = tmp_path_factory.mktemp("shelving-site")
    render.write(
        render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO, api_url=api),
        site_dir,
    )

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

    site_server, origin = serve(functools.partial(Quiet, directory=str(site_dir)))
    yield origin
    site_server.shutdown()
    api_server.shutdown()


def test_a_steward_shelves_unshelves_and_retires_from_the_site(served: str) -> None:
    """Needs Playwright; without it this test skips, which proves nothing. Shelve posts
    ``{node_id, action: shelved, scope: node, route: null, cause}``; Unshelve the same with
    ``unshelved``; Retire ``scope: route`` with the partial; each shows the pull request."""
    sync_api = pytest.importorskip("playwright.sync_api")
    POSTED.clear()
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        # Shelve an open statement.
        page.goto(served + f"/nodes/{TARGET}/{OPEN}/")
        page.wait_for_selector(".shelve-act button")
        assert not page.locator(".shelve-act").evaluate("e => e.hidden")
        page.get_by_role("button", name="Shelve").click()
        page.wait_for_selector(".shelve-act textarea")
        page.locator(".shelve-act textarea").fill("Not on the way to the root.")
        page.locator(".shelve-act button.send").click()
        page.wait_for_selector(".shelve-act .receipt a")
        assert page.locator(".shelve-act .receipt a").inner_text() == "#7"
        assert POSTED[-1] == {
            "path": "/shelvings",
            "body": {
                "node_id": OPEN,
                "action": "shelved",
                "scope": "node",
                "route": None,
                "cause": "Not on the way to the root.",
            },
        }
        # Unshelve the shelved one.
        page.goto(served + f"/nodes/{TARGET}/{SHELVED}/")
        page.wait_for_selector(".shelve-act button")
        page.get_by_role("button", name="Unshelve").click()
        page.locator(".shelve-act textarea").fill("It helps after all.")
        page.locator(".shelve-act button.send").click()
        page.wait_for_selector(".shelve-act .receipt a")
        assert POSTED[-1]["body"]["action"] == "unshelved"
        assert POSTED[-1]["body"]["node_id"] == SHELVED
        # Retire a route from the problem page.
        page.goto(served + f"/problems/{TARGET}/")
        page.wait_for_selector(".retire-act button")
        first = page.locator(".retire-act").nth(0)
        partial = first.get_attribute("data-partial")
        first.locator("button").click()
        first.locator("textarea").fill("A distraction.")
        first.locator("button.send").click()
        page.wait_for_selector(".retire-act .receipt a")
        assert POSTED[-1]["body"] == {
            "node_id": ROOT_NODE,
            "action": "shelved",
            "scope": "route",
            "route": partial,
            "cause": "A distraction.",
        }
        # Signed out: nothing is drawn.
        FakeService.session = {**FakeService.session, "signed_in": False}
        try:
            page.goto(served + f"/nodes/{TARGET}/{OPEN}/")
            page.wait_for_timeout(300)
            assert page.locator(".shelve-act").evaluate("e => e.hidden")
            assert page.locator(".shelve-act button").count() == 0
        finally:
            FakeService.session = {**FakeService.session, "signed_in": True}
        browser.close()
