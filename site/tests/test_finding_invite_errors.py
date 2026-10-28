"""F04-T59: the Invite form says when a sign-in has ended, and takes a pasted GitHub address.

The owner pressed Invite on erdos-257 at 06:17:28Z on 2026-10-28 from a page loaded at 22:18Z
the night before. Their web session, opened at 22:17:17Z, had ended eleven seconds earlier (the
eight-hour ``web_session_ttl_s``), so the service answered 401 with a message written for a bearer
client: "this route needs `Authorization: Bearer <token>`, or a web session from the site". They had
also typed the invitee as ``https://github.com/riversupport``, a profile address, where the form
wants the login. Now:

* a 401 on a web call reads "Your sign-in has ended." with a link to sign in again, in every script
  that sets the service's refusal as text, and the panel's refusal line carries the link itself;
* the login field takes ``https://github.com/<login>``, ``github.com/<login>/`` or ``@<login>`` and
  sends ``<login>``; anything that is still not a GitHub login is refused before anything is sent.
"""

from __future__ import annotations

import functools
import http.server
import json
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fixture import COMMIT, STEWARD_LOGIN, STEWARDED_TARGET, build_with_stewards

from opn_site import model, render

REPO = "https://github.com/example/graph"
STATIC = Path(render.__file__).parent / "static"
SESSION_JS = (STATIC / "session.js").read_text(encoding="utf-8")
PANEL_JS = (STATIC / "panel.js").read_text(encoding="utf-8")
EVIDENCE = Path(__file__).resolve().parents[2] / "engineering" / "evidence" / "F04"

#: The service's own refusal, word for word (opn_api.auth.authenticate_web).
BEARER_401 = {
    "error": "unauthenticated",
    "message": "this route needs `Authorization: Bearer <token>`, or a web session from the site",
}

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


# --- the static scripts --------------------------------------------------------------------------


def test_session_js_reads_a_401_as_an_ended_sign_in() -> None:
    body = SESSION_JS[SESSION_JS.index("var ENDED") :]
    body = body[: body.index("function here")]
    assert "401" in body and "Your sign-in has ended" in body, body


def test_panel_js_normalises_the_login_before_posting() -> None:
    form = PANEL_JS[PANEL_JS.index("function inviteForm") :]
    form = form[: form.index("function acceptForm")]
    assert "githubLogin(" in form, form


# --- in a browser, against a fake service -------------------------------------------------------


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class FakeService(http.server.BaseHTTPRequestHandler):
    session: dict[str, Any] = dict(MEMBER)  # noqa: RUF012 — the tests swap it
    motion_status: int = 401
    posted: list[dict[str, Any]] = []  # noqa: RUF012 — what the page sent, read by the tests

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

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        FakeService.posted.append({"path": self.path, "body": body})
        if self.path == "/motions" and FakeService.motion_status == 401:
            self.reply(401, BEARER_401)
        elif self.path == "/motions":
            self.reply(201, {"pr_number": 7, "pr_url": "https://github.com/example/graph/pull/7"})
        else:
            self.reply(404, {"error": "not-found", "message": "no"})


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    root = build_with_stewards(tmp_path_factory.mktemp("invite-errors"))
    api_server, api = serve(FakeService)
    site_dir = tmp_path_factory.mktemp("invite-errors-site")
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


def open_form(p: Any, served: str, width: int = 1440) -> tuple[Any, Any]:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": width, "height": 900})
    page.goto(served + f"/problems/{STEWARDED_TARGET}/")
    page.wait_for_selector("#invite-login")
    return browser, page


def test_an_ended_sign_in_says_so_and_offers_sign_in_again(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FakeService.session, FakeService.motion_status, FakeService.posted = dict(MEMBER), 401, []
    with sync_api.sync_playwright() as p:
        browser, page = open_form(p, served)
        page.fill("#invite-login", "riversupport")
        page.locator(".invite-ctl button.btn-primary").click()
        out = page.locator(".invite-ctl .form-error")
        out.locator("a").wait_for()
        words = out.inner_text()
        assert "Your sign-in has ended" in words, words
        assert "Bearer" not in words, words
        link = out.locator("a")
        assert "/auth/github/start?return=" in (link.get_attribute("href") or "")
        assert "Sign in again" in link.inner_text()
        # The button is usable again, so the invite can be sent after signing in.
        assert page.locator(".invite-ctl button.btn-primary").is_enabled()
        page.locator(".invite-ctl").screenshot(path=str(EVIDENCE / "task-59-ended-session.png"))
        browser.close()


@pytest.mark.parametrize(
    "typed",
    [
        "https://github.com/riversupport",
        "https://github.com/riversupport/",
        "http://www.github.com/riversupport?tab=repositories",
        "github.com/riversupport",
        "@riversupport",
        "  riversupport  ",
    ],
)
def test_a_pasted_github_address_sends_the_login(served: str, typed: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    FakeService.session, FakeService.motion_status, FakeService.posted = dict(MEMBER), 201, []
    with sync_api.sync_playwright() as p:
        browser, page = open_form(p, served)
        page.fill("#invite-login", typed)
        page.locator(".invite-ctl button.btn-primary").click()
        page.wait_for_selector(".receipt")
        motions = [x for x in FakeService.posted if x["path"] == "/motions"]
        assert len(motions) == 1, FakeService.posted
        assert motions[0]["body"]["subject"]["login"] == "riversupport", motions[0]
        assert "riversupport" in page.locator(".receipt").inner_text()
        browser.close()


@pytest.mark.parametrize(
    "typed", ["carl011226@gmail.com", "https://github.com/", "not a login", "-bad", "a--b"]
)
def test_what_is_not_a_login_is_refused_before_anything_is_sent(served: str, typed: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    FakeService.session, FakeService.motion_status, FakeService.posted = dict(MEMBER), 201, []
    with sync_api.sync_playwright() as p:
        browser, page = open_form(p, served)
        page.fill("#invite-login", typed)
        page.locator(".invite-ctl button.btn-primary").click()
        page.wait_for_timeout(300)
        words = page.locator(".invite-ctl .form-error").inner_text()
        assert "GitHub login" in words, words
        assert not [x for x in FakeService.posted if x["path"] == "/motions"]
        if typed.endswith("gmail.com"):
            assert "email" in words, words
            page.locator(".invite-ctl").screenshot(path=str(EVIDENCE / "task-59-email.png"))
        browser.close()
