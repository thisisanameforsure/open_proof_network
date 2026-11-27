"""F31-T17 (Q19): a filed shelving is followed on the page until it is drawn.

The owner retired a route on erdos-257 and "the display did not change … right now it just
feels broken": the page said "Retirement filed: #2078" until the next reload, then offered the
same Retire button again, and the drawing stayed as it was for the quarter of an hour the
products take to land. Three things answer it, all in ``static/shelve.js``:

1. the filing is remembered in the browser and survives a reload: the control is replaced by the
   record's progress until the page is drawn with it;
2. the progress says where the record is — filed, checked, merged, on this page — and what
   happens next, read from ``GET /submissions/{n}`` (F31-T16), and ends with "Reload to see it"
   once a fresh copy of this very page shows the change;
3. the drawing marks what the record will change (the route's junction and holes, or the
   statement's pill) as pending. It is never drawn as done before the page is rendered with it:
   the check may still refuse the record.

A viewer who did not file it sees "a shelving record is pending: #N by X" from
``GET /submissions.json`` (``open`` and ``awaiting_render``).

The browser tests need Playwright (``uv run --with 'playwright==1.58.0' python -m pytest …``);
without it they skip, which proves nothing, and the evidence file says so.
"""

from __future__ import annotations

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
from test_products import ROOT_NODE
from test_routes_view import THIRD, two_routes

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
LATER = "attempts/20260924T000000Z-bob-partial.lean"  # two_routes' second split: [h3]
PROBLEM = f"problems/{TARGET}/index.html"
RETIRE = re.compile(r'<span class="retire-act" ([^>]*) hidden></span>')
ATTR = re.compile(r'([a-z-]+)="([^"]*)"')
JS = (render.STATIC / "shelve.js").read_text(encoding="utf-8")
PR = 7


def attrs(raw: str) -> dict[str, str]:
    return {k: unescape(v) for k, v in ATTR.findall(raw)}


def tree(tmp_path: Path, *, retired: bool) -> Path:
    """``two_routes`` rendered; with ``retired``, as the gate leaves it once the second split
    is retired: its one hole shelved through the root's record."""
    root = two_routes(tmp_path)
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    if retired:
        fact = fixture.shelved_fact("A distraction.", via=ROOT_NODE, scope="route")
        fixture.publish_shelved(root, {THIRD: fact})
    return root


def rendered(root: Path, api: str) -> dict[str, str]:
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO, api_url=api)


# --- the static half --------------------------------------------------------------------------


def test_a_retire_slot_names_its_route_and_its_holes(tmp_path: Path) -> None:
    """What the script needs to mark the drawing: the junction's id and the holes beneath it."""
    page = rendered(tree(tmp_path, retired=False), "https://api.example.invalid")[PROBLEM]
    slots = [attrs(m) for m in RETIRE.findall(page)]
    later = [s for s in slots if s["data-partial"] == LATER]
    assert later, slots
    for s in later:
        assert s["data-holes"] == THIRD
        assert f'data-route="{s["data-route"]}"' in page.split("<svg", 1)[1]  # a drawn junction
    other = next(s for s in slots if s["data-partial"] != LATER)
    assert len(other["data-holes"].split(" ")) == 2


def test_the_script_never_draws_a_pending_record_as_done() -> None:
    """A pending mark is its own class; ``shelved`` is the render's word alone."""
    assert "act-pending" in JS
    assert not re.search(r"classList\.(add|toggle)\(\s*[\"']shelved[\"']", JS)


# --- in a browser, against a fake service -----------------------------------------------------


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def pull(**over: Any) -> dict[str, Any]:
    return {
        "number": PR,
        "state": "open",
        "merged": False,
        "waiting_on": "gate",
        "url": f"{REPO}/pull/{PR}",
        **over,
    }


class Service(http.server.BaseHTTPRequestHandler):
    """``GET /session`` signed in as a steward; ``POST /shelvings`` answers 201 with #7;
    ``GET /submissions/7`` answers ``pull`` and ``GET /submissions.json`` ``listing``, both of
    which a test swaps to move the record along."""

    pull: dict[str, Any] | None = pull()  # swapped by the tests
    listing: dict[str, Any] = {"open": [], "awaiting_render": []}  # noqa: RUF012
    seen: list[str] = []  # noqa: RUF012

    def log_message(self, *_args: object) -> None:
        return

    def reply(self, status: int, doc: Any) -> None:
        body = json.dumps(doc).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        if "X-OPN-Web" in self.headers:
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-OPN-Web")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.end_headers()

    def do_GET(self) -> None:
        Service.seen.append(self.path)
        if self.path == "/session":
            self.reply(
                200,
                {
                    "signed_in": True,
                    "login": "alice-steward",
                    "pseudonym": "alice-steward",
                    "curator": False,
                    "stewards": [TARGET],
                    "expires": "2026-12-30T12:00:00Z",
                    "awaiting": {"votes": [], "invitations": []},
                    "reviews": [],
                },
            )
        elif self.path == f"/submissions/{PR}":
            if Service.pull is None:
                self.reply(502, {"error": "host", "message": "no"})
            else:
                self.reply(200, {"state": "open", "pull_request": Service.pull})
        elif self.path.startswith("/submissions.json"):
            self.reply(200, Service.listing)
        else:
            self.reply(404, {"error": "not-found", "message": "no"})

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.reply(201, {"pr_number": PR, "pr_url": f"{REPO}/pull/{PR}", "branch": "append/x"})


class Pages(http.server.SimpleHTTPRequestHandler):
    """The site, from whichever directory ``root`` names now: a test swaps it for the render
    that carries the retirement, as a deploy does."""

    root: str = ""

    def log_message(self, *_args: object) -> None:
        return

    def translate_path(self, path: str) -> str:
        self.directory = Pages.root
        return super().translate_path(path)


class Served:
    def __init__(self, origin: str, before: str, after: str) -> None:
        self.origin, self.before, self.after = origin, before, after

    def deploy(self, *, retired: bool) -> None:
        Pages.root = self.after if retired else self.before


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Served]:
    api_server, api = serve(Service)
    dirs = []
    for retired in (False, True):
        root = tree(tmp_path_factory.mktemp("progress-graph"), retired=retired)
        out = tmp_path_factory.mktemp("progress-site")
        render.write(rendered(root, api), out)
        dirs.append(str(out))
    site_server, origin = serve(Pages)
    yield Served(origin, dirs[0], dirs[1])
    site_server.shutdown()
    api_server.shutdown()


@pytest.fixture
def fresh(served: Served) -> Served:
    served.deploy(retired=False)
    Service.pull = pull()
    Service.listing = {"open": [], "awaiting_render": []}
    Service.seen.clear()
    return served


SLOT = f'li.route-row .retire-act[data-partial="{LATER}"]'
OTHER = f'li.route-row .retire-act:not([data-partial="{LATER}"])'
PENDING_PILL = f'svg g.node.act-pending[data-node="{THIRD}"]'


def open_problem(page: Any, origin: str) -> None:
    page.goto(origin + f"/problems/{TARGET}/")
    page.locator('.route-tabs [aria-controls="sets-list"]').click()


def file_retirement(page: Any, origin: str) -> None:
    open_problem(page, origin)
    row = page.locator("li.route-row", has=page.locator(f'.retire-act[data-partial="{LATER}"]'))
    row.locator(".route-retire summary").click()
    page.wait_for_selector(SLOT + " button")
    page.locator(SLOT + " button").click()
    page.locator(SLOT + " textarea").fill("A distraction.")
    page.locator(SLOT + " button.send").click()
    page.wait_for_selector(SLOT + " .act-progress")


def steps(page: Any) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"done": [], "now": [], "todo": []}
    for li in page.locator(SLOT + " .act-steps li").all():
        cls = li.get_attribute("class") or ""
        key = "done" if "done" in cls else "now" if "now" in cls else "todo"
        out[key].append(li.inner_text())
    return out


def again(page: Any) -> None:
    """The script asks again when the tab is looked at, as well as on its own clock."""
    page.evaluate("window.dispatchEvent(new Event('focus'))")


def test_a_filed_retirement_is_followed_until_it_is_drawn(fresh: Served) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        file_retirement(page, fresh.origin)

        # 2: filed, being checked; the pull request is linked; the control is gone
        assert page.locator(SLOT + " .act-progress a").first.inner_text() == f"#{PR}"
        assert steps(page) == {
            "done": ["Filed"],
            "now": ["Checked"],
            "todo": ["Merged", "On this page"],
        }
        assert page.locator(SLOT + " button").count() == 0
        # 3: the drawing marks what the record will change, and draws none of it as done
        page.wait_for_selector(PENDING_PILL, state="attached")
        assert page.locator("svg g.junction.act-pending").count() >= 1
        assert page.locator(f'svg g.node.shelved[data-node="{THIRD}"]').count() == 0
        assert page.locator(f'svg g.node.act-pending[data-node="{ROOT_NODE}"]').count() == 0

        # 1: a reload keeps it — no second Retire for this route, the other route untouched
        open_problem(page, fresh.origin)
        page.wait_for_selector(SLOT + " .act-progress")
        assert page.locator(SLOT).evaluate("e => e.closest('details').open")
        assert page.locator(SLOT + " button").count() == 0
        page.wait_for_selector(OTHER + " button", state="attached")
        page.wait_for_selector(PENDING_PILL, state="attached")

        # checked, waiting to merge
        Service.pull = pull(waiting_on="merge")
        again(page)
        page.wait_for_function(
            "s => document.querySelector(s).dataset.state === 'merging'",
            arg=SLOT + " .act-progress",
        )
        assert steps(page)["now"] == ["Merged"]

        # merged; the products are not rendered from it yet
        Service.pull = pull(state="closed", merged=True, waiting_on="products")
        again(page)
        page.wait_for_function(
            "s => document.querySelector(s).dataset.state === 'rendering'",
            arg=SLOT + " .act-progress",
        )
        assert steps(page) == {
            "done": ["Filed", "Checked", "Merged"],
            "now": ["On this page"],
            "todo": [],
        }
        words = page.locator(SLOT + " .act-words").inner_text()
        assert "quarter of an hour" in words
        assert page.locator(SLOT + " .act-reload").count() == 0

        # rendered, and the site still serves the old page: not drawn yet
        Service.pull = pull(state="closed", merged=True, waiting_on=None)
        again(page)
        page.wait_for_function(
            "s => document.querySelector(s).dataset.state === 'publishing'",
            arg=SLOT + " .act-progress",
        )
        assert page.locator(SLOT + " .act-reload").count() == 0

        # the site deploys the page that carries it: say so, and offer the reload
        fresh.deploy(retired=True)
        again(page)
        page.wait_for_selector(SLOT + " .act-reload")
        assert steps(page)["done"] == ["Filed", "Checked", "Merged", "On this page"]
        assert page.locator(SLOT + " .act-progress").get_attribute("data-state") == "drawn"
        page.locator(SLOT + " .act-reload").click()
        page.wait_for_load_state("load")
        page.wait_for_selector("svg g.node", state="attached")
        # the fresh page shows the retirement itself; the note and the mark are gone for good
        page.wait_for_timeout(300)
        assert page.locator(".act-progress").count() == 0
        assert page.locator("svg .act-pending").count() == 0
        assert page.evaluate("JSON.parse(localStorage.getItem('opn.shelvings') || '[]')") == []
        browser.close()


def test_a_record_closed_without_merging_says_so_and_gives_the_control_back(
    fresh: Served,
) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        file_retirement(page, fresh.origin)
        # the check refuses it: still open, and said plainly
        Service.pull = pull(waiting_on="gate-failed")
        again(page)
        page.wait_for_function(
            "s => document.querySelector(s).dataset.state === 'failed'",
            arg=SLOT + " .act-progress",
        )
        assert "Nothing has changed" in page.locator(SLOT + " .act-words").inner_text()
        # closed, not merged
        Service.pull = pull(state="closed", merged=False, waiting_on=None)
        again(page)
        page.wait_for_function(
            "s => document.querySelector(s).dataset.state === 'refused'",
            arg=SLOT + " .act-progress",
        )
        assert "without merging" in page.locator(SLOT + " .act-words").inner_text()
        assert page.locator("svg .act-pending").count() == 0
        page.locator(SLOT + " .act-dismiss").click()
        page.wait_for_selector(SLOT + " button:not(.act-dismiss)")
        assert page.locator(SLOT + " .act-progress").count() == 0
        assert page.locator(SLOT + " button").inner_text() == "Retire this route"
        assert page.evaluate("JSON.parse(localStorage.getItem('opn.shelvings') || '[]')") == []
        browser.close()


def test_a_service_that_does_not_answer_changes_nothing_shown(fresh: Served) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        file_retirement(page, fresh.origin)
        Service.pull = None
        Service.seen.clear()
        again(page)
        page.wait_for_function("() => true")
        page.wait_for_timeout(400)
        assert f"/submissions/{PR}" in Service.seen
        assert steps(page)["now"] == ["Checked"]
        assert page.locator(SLOT + " .act-progress").get_attribute("data-state") == "checking"
        browser.close()


def test_another_viewer_sees_that_a_record_is_pending(fresh: Served) -> None:
    """No filing in this browser: the listing says a shelving record on the root is merged and
    not drawn yet. Its scope is not in the listing, so the statement is marked, the control
    stays, and nothing claims to know which route."""
    sync_api = pytest.importorskip("playwright.sync_api")
    Service.listing = {
        "open": [],
        "awaiting_render": [
            {
                "kind": "shelving",
                "node_id": ROOT_NODE,
                "target_id": TARGET,
                "pr_number": 9,
                "pr_url": f"{REPO}/pull/9",
                "pseudonym": "bob<b>",
            },
            {  # another repository's link is never made a link
                "kind": "shelving",
                "node_id": ROOT_NODE,
                "target_id": TARGET,
                "pr_number": 10,
                "pr_url": "https://evil.example/pull/10",
                "pseudonym": "eve",
            },
        ],
    }
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        open_problem(page, fresh.origin)
        page.wait_for_selector(SLOT + " .act-others", state="attached")
        note = page.locator(SLOT + " .act-others").first
        text = note.text_content()  # behind "Retire…", as the control is
        assert "#9" in text and "bob<b>" in text and "merged" in text
        assert note.locator("b").count() == 0  # a name is text, never markup
        links = page.locator(SLOT + " .act-others a").all()
        assert [a.get_attribute("href") for a in links] == [f"{REPO}/pull/9"]
        page.wait_for_selector(f'svg g.node.act-pending[data-node="{ROOT_NODE}"]', state="attached")
        page.wait_for_selector(SLOT + " button", state="attached")  # the control is still offered
        assert any(
            s.startswith(f"/submissions.json?target={TARGET}&kind=shelving") for s in Service.seen
        )
        browser.close()
