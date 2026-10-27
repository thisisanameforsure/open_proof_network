"""F04-T58: a steward can find how to invite a co-steward.

The owner, the only steward of erdos-257, could not see how to invite a second (2026-10-26). The
Invite form existed (F24-T6) but only in the Panel section at the foot of the problem page, drawn
after sign-in; the steward card's "How to join" went to the steward form page, which speaks to
the invitee and never tells a member where the form is; and nothing said an invitation names a
GitHub login, not an email address. Now:

* the steward card carries a slot that panel.js fills: signed out, a "Sign in with GitHub to
  invite a co-steward" link; signed in as a panel member or a curator, an "Invite a co-steward"
  button that goes to the Panel section and puts the cursor in the login field; anyone else,
  nothing (the sentence of F04-T44 stays for them);
* the Invite form says invitations go to a GitHub login, not an email, and when the motion passes
  (at once for a sole member or a curator, otherwise by the panel's vote within its window);
* the steward form page tells a current member where to invite from.
"""

from __future__ import annotations

import functools
import http.server
import json
import re
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fixture import COMMIT, STEWARD_LOGIN, STEWARDED_TARGET, STEWARDLESS_TARGET, build_with_stewards

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.invalid"
PANEL_JS = (Path(render.__file__).parent / "static" / "panel.js").read_text(encoding="utf-8")
EVIDENCE = Path(__file__).resolve().parents[2] / "engineering" / "evidence" / "F04"


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_with_stewards(tmp_path_factory.mktemp("invite-path"))


@pytest.fixture(scope="module")
def pages(root: Path) -> dict[str, str]:
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=API)


def text(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def steward_card(page: str) -> str:
    start = page.index('<aside class="card steward-card">')
    return page[start : page.index("</aside>", start)]


# --- the static page -----------------------------------------------------------------------------


def test_the_steward_card_carries_the_invite_slot_for_the_script(pages: dict[str, str]) -> None:
    card = steward_card(pages[f"problems/{STEWARDED_TARGET}/index.html"])
    assert '<div class="invite-cue"' in card, card
    # F23-R15: the static page carries no control; the script draws one after GET /session.
    assert "Invite a co-steward" not in card and "<button" not in card


def test_without_a_service_or_a_steward_there_is_no_slot(root: Path, pages: dict[str, str]) -> None:
    no_api = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)
    assert "invite-cue" not in steward_card(no_api[f"problems/{STEWARDED_TARGET}/index.html"])
    assert "invite-cue" not in steward_card(pages[f"problems/{STEWARDLESS_TARGET}/index.html"])


def test_the_panel_slot_carries_the_vote_window(pages: dict[str, str]) -> None:
    page = pages[f"problems/{STEWARDED_TARGET}/index.html"]
    slot = re.search(r'<div class="panel-ctl"([^>]*)></div>', page)
    assert slot is not None
    m = re.search(r'data-window-days="(\d+)"', slot.group(1))
    assert m is not None, slot.group(1)
    assert int(m.group(1)) >= 1


def test_the_form_page_tells_a_member_where_to_invite_from(pages: dict[str, str]) -> None:
    page = pages[f"steward/{STEWARDED_TARGET}/index.html"]
    head = page[page.index('<section class="page-head steward-head">') :]
    head = head[: head.index("</section>")]
    cue = re.search(r'<p class="cue member-invites">(.*?)</p>', head, re.S)
    assert cue is not None, text(head)
    words = text(cue.group(1))
    assert "Already a steward" in words and "Invite" in words and "GitHub login" in words, words
    assert f'href="/problems/{STEWARDED_TARGET}/#panel"' in cue.group(1)
    # A problem with no steward takes a self-commitment: no member line there.
    assert "member-invites" not in pages[f"steward/{STEWARDLESS_TARGET}/index.html"]


def test_the_script_says_login_not_email_and_when_an_invitation_passes() -> None:
    form = PANEL_JS[PANEL_JS.index("function inviteForm") :]
    form = form[: form.index("function acceptForm")]
    assert "GitHub login, not an email" in form, form
    assert "at once" in form and "windowDays" in form, form


# --- in a browser, against a fake service -------------------------------------------------------


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


MEMBER: dict[str, Any] = {
    "signed_in": True,
    "login": STEWARD_LOGIN,
    "pseudonym": STEWARD_LOGIN,
    "curator": False,
    "stewards": [STEWARDED_TARGET],
    "expires": "2026-12-01T12:00:00Z",
    "awaiting": {"votes": [], "invitations": []},
    "reviews": [],
}


class FakeService(http.server.BaseHTTPRequestHandler):
    session: dict[str, Any] = dict(MEMBER)  # noqa: RUF012 — the tests swap it to drive the gate

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
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/session":
            self.reply(200, self.session)
        elif self.path == "/submissions.json":
            self.reply(200, {"open": [], "recent": []})
        else:
            self.reply(404, {"error": "not-found", "message": "no"})


@pytest.fixture(scope="module")
def served(root: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    api_server, api = serve(FakeService)
    site_dir = tmp_path_factory.mktemp("invite-site")
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


def test_a_member_gets_a_button_that_lands_on_the_invite_form(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FakeService.session = dict(MEMBER)
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + f"/problems/{STEWARDED_TARGET}/")
        page.wait_for_selector(".steward-card .invite-cue a.btn")
        button = page.locator(".steward-card .invite-cue a.btn")
        assert button.inner_text().strip() == "Invite a co-steward"
        assert button.get_attribute("href") == "#panel"
        page.locator(".steward-card").screenshot(path=str(EVIDENCE / "task-58-card-member.png"))
        button.click()
        page.wait_for_timeout(200)
        assert page.evaluate("location.hash") == "#panel"
        assert page.evaluate("document.activeElement && document.activeElement.id") == (
            "invite-login"
        )
        # The form says what an invitation takes and when it passes.
        note = page.locator(".invite-ctl .cue").inner_text()
        assert "GitHub login, not an email" in note and "at once" in note, note
        assert re.search(r"\d+ days", note), note
        page.locator(".invite-ctl").screenshot(path=str(EVIDENCE / "task-58-invite-form.png"))
        # A curator who is not a member gets the same button.
        FakeService.session = {**MEMBER, "login": "a-curator", "stewards": [], "curator": True}
        page.goto(served + f"/problems/{STEWARDED_TARGET}/")
        page.wait_for_selector(".steward-card .invite-cue a.btn")
        browser.close()


def test_signed_out_a_sign_in_link_and_a_bystander_nothing(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 900})
        FakeService.session = {"signed_in": False}
        page.goto(served + f"/problems/{STEWARDED_TARGET}/")
        page.wait_for_selector(".steward-card .invite-cue a")
        link = page.locator(".steward-card .invite-cue a")
        assert "Sign in with GitHub to invite a co-steward" in link.inner_text()
        assert "/auth/github/start?return=" in (link.get_attribute("href") or "")
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        page.locator(".steward-card").screenshot(path=str(EVIDENCE / "task-58-card-out-390.png"))
        FakeService.session = {**MEMBER, "login": "someone-else", "stewards": []}
        page.goto(served + f"/problems/{STEWARDED_TARGET}/")
        page.wait_for_timeout(400)
        assert page.locator(".steward-card .invite-cue a").count() == 0
        assert "Co-stewards are welcome" in page.locator(".steward-card").inner_text()
        browser.close()
