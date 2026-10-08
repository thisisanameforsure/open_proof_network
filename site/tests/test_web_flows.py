"""F23-T9 / AC11: the site's signed-in flows, in a real browser, against a fake service.

The fixture sites are rendered with the fake service's address (the site's config, as live), served
from a local port, and driven with Playwright. The fake service is a few lines honouring the service
contract F23 builds against: ``GET /auth/github/start`` sets a session cookie and sends the browser
back to the path it was given; ``GET /session`` answers the cookie's roles; ``POST /stewards``,
``POST /approvals``, ``POST /glosses`` (with ``dry_run``) and ``POST /glosses/withdrawals``
answer as the contract says, refusing any write without ``X-OPN-Web: 1`` from the site's
origin; CORS names the site's origin with credentials. Every
request is recorded, so a test can read what the page sent as well as what it drew.

AC11: sign in, steward a target, see the receipt; open a node page as that steward, see Approve;
as a stranger, see Edit and no Approve; with the service down, the read-only page. Screenshots at
1440 and 390 with no horizontal scroll, written to ``$OPN_F23_SHOTS`` when set (the evidence run)
and to a temporary directory otherwise.

Needs Playwright and its Chromium: ``uv run --frozen --with playwright pytest site/tests/
test_web_flows.py``. Without them the module skips, which proves nothing; the evidence file records
a run with them.
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import gloss_fixture as gf
import panel_fixture as pf
import pytest
from fixture import COMMIT, STEWARDLESS_TARGET, build_with_stewards
from harness import TARGET

from opn_site import model, render

sync_api = pytest.importorskip("playwright.sync_api")

REPO = "https://github.com/example/graph"
NODE = f"/nodes/{TARGET}/{gf.TUTORIAL}/"
COOKIE = "opn_web"
WIDTHS = {"desktop": 1440, "phone": 390}


@dataclass
class Fake:
    """The fake service's state: who each cookie is, their roles, and every request."""

    origins: set[str] = field(default_factory=set)
    next_login: str = "mira"
    curators: set[str] = field(default_factory=set)
    stewards: dict[str, set[str]] = field(default_factory=dict)
    conflict: set[str] = field(default_factory=set)  # logins POST /stewards answers 409 for
    open_prs: list[dict[str, Any]] = field(default_factory=list)
    #: F24-T6: login -> GET /session's ``awaiting``; path -> a refusal the next POST answers.
    awaiting: dict[str, dict[str, Any]] = field(default_factory=dict)
    refuse: dict[str, tuple[int, dict[str, str]]] = field(default_factory=dict)
    log: list[tuple[str, str, dict[str, str], Any]] = field(default_factory=list)
    pr: int = 500

    def posted(self, path: str) -> list[tuple[dict[str, str], Any]]:
        return [(h, b) for m, p, h, b in self.log if m == "POST" and p == path]


class Handler(http.server.BaseHTTPRequestHandler):
    server: Any

    def log_message(self, *_args: object) -> None:  # quiet
        return

    @property
    def fake(self) -> Fake:
        return self.server.fake  # type: ignore[no-any-return]

    def cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin in self.fake.origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")

    def answer(self, status: int, body: Any = None, headers: dict[str, str] | None = None) -> None:
        data = b"" if body is None else json.dumps(body).encode()
        self.send_response(status)
        self.cors()
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def login(self) -> str | None:
        jar: SimpleCookie = SimpleCookie(self.headers.get("Cookie", ""))
        return jar[COOKIE].value if COOKIE in jar else None

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "X-OPN-Web, Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        url = urlparse(self.path)
        self.fake.log.append(("GET", url.path, dict(self.headers), None))
        if url.path == "/auth/github/start":
            back = parse_qs(url.query).get("return", ["/"])[0]
            if not back.startswith("/") or back.startswith("//"):
                self.answer(400, {"error": "return-invalid", "message": "a path on the site"})
                return
            self.send_response(303)
            self.send_header("Set-Cookie", f"{COOKIE}={self.fake.next_login}; Path=/; HttpOnly")
            self.send_header("Location", self.server.home + back)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if url.path == "/session":
            who = self.login()
            if who is None:
                self.answer(200, {"signed_in": False})
                return
            self.answer(
                200,
                {
                    "signed_in": True,
                    "login": who,
                    "pseudonym": who,
                    "curator": who in self.fake.curators,
                    "stewards": sorted(self.fake.stewards.get(who, set())),
                    "expires": "2026-10-07T20:00:00Z",
                    "awaiting": self.fake.awaiting.get(who, {"votes": [], "invitations": []}),
                },
            )
            return
        if url.path == "/submissions.json":
            self.answer(200, {"open": self.fake.open_prs, "recent": []})
            return
        self.answer(404, {"error": "not-found", "message": "no such route"})

    def do_POST(self) -> None:  # noqa: PLR0911, PLR0912 — one branch per route
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body: Any = json.loads(raw) if raw else {}
        self.fake.log.append(("POST", url.path, dict(self.headers), body))
        who = self.login()
        web = self.headers.get("X-OPN-Web") == "1"
        if not web or self.headers.get("Origin") not in self.fake.origins or who is None:
            self.answer(401, {"error": "unauthenticated", "message": "sign in on the site"})
            return
        if url.path in self.fake.refuse:
            status, refusal = self.fake.refuse.pop(url.path)
            self.answer(status, refusal)
            return
        if url.path in ("/motions", "/votes", "/writeups"):  # F24-T6: the panel's routes
            self.answer(201, self.receipt(url.path.strip("/")))
            return
        if url.path == "/session/end":
            self.answer(204, headers={"Set-Cookie": f"{COOKIE}=; Path=/; Max-Age=0"})
            return
        if url.path == "/stewards":
            held = self.fake.stewards.setdefault(who, set())
            target = body["target"]
            if body["action"] == "commit" and (target in held or who in self.fake.conflict):
                self.answer(
                    409, {"error": "steward-already-active", "message": "already a steward"}
                )
                return
            if body["action"] == "commit":
                held.add(target)
            else:
                held.discard(target)
            self.answer(201, self.receipt("stewards"))
            return
        if url.path == "/approvals":
            allowed = who in self.fake.curators or body["target"] in self.fake.stewards.get(
                who, set()
            )
            if not allowed:
                self.answer(
                    403, {"error": "not-steward-or-curator", "message": "not a steward or curator"}
                )
                return
            self.answer(201, self.receipt("approvals"))
            return
        if url.path == "/glosses":
            if body.get("dry_run"):
                # The service renders the words with the site's own escaping renderer.
                from opn_site import prose  # noqa: PLC0415

                self.answer(
                    200, {"ok": True, "dry_run": True, "preview_html": prose.render(body["text"])}
                )
                return
            self.answer(201, self.receipt("glosses"))
            return
        if url.path == "/glosses/withdrawals":
            self.answer(201, self.receipt("withdrawals"))
            return
        self.answer(404, {"error": "not-found", "message": "no such route"})

    def receipt(self, what: str) -> dict[str, Any]:
        self.fake.pr += 1
        n = self.fake.pr
        return {
            "pr_number": n,
            "pr_url": f"{REPO}/pull/{n}",
            "branch": f"append/{what}-{n}",
            "path": f"targets/{what}.yaml",
        }


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def site_server(directory: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

    return serve(functools.partial(Quiet, directory=str(directory)))


@dataclass
class Bench:
    fake: Fake
    api: str
    stewards_site: str
    words_site: str
    down_site: str
    shots: Path
    api_server: Any


@pytest.fixture(scope="module")
def bench(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Bench]:
    fake = Fake()
    api_server, api = serve(Handler)
    api_server.fake = fake  # type: ignore[attr-defined]
    servers = [api_server]

    stewards_root = build_with_stewards(tmp_path_factory.mktemp("flows-stewards"))
    words_root, _ = gf.sectioned_tree(tmp_path_factory.mktemp("flows-words"))
    out: dict[str, str] = {}
    for name, root, commit, api_url in (
        ("stewards", stewards_root, COMMIT, api),
        ("words", words_root, gf.COMMIT, api),
        # The service down: a port nothing listens on (bound, then closed).
        ("down", stewards_root, COMMIT, dead_origin()),
    ):
        site_dir = tmp_path_factory.mktemp(f"site-{name}")
        render.write(
            render.render_site(model.load_site(root, commit), repo_url=REPO, api_url=api_url),
            site_dir,
        )
        server, origin = site_server(site_dir)
        servers.append(server)
        out[name] = origin
        fake.origins.add(origin)
    api_server.home = out["stewards"]  # type: ignore[attr-defined]
    shots = Path(os.environ.get("OPN_F23_SHOTS") or tmp_path_factory.mktemp("shots"))
    shots.mkdir(parents=True, exist_ok=True)
    yield Bench(fake, api, out["stewards"], out["words"], out["down"], shots, api_server)
    for server in servers:
        server.shutdown()


def dead_origin() -> str:
    import socket  # noqa: PLC0415

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def new_page(browser: Any, width: int = 1440) -> Any:
    context = browser.new_context(viewport={"width": width, "height": 900})
    return context.new_page()


def shoot(page: Any, bench: Bench, name: str) -> None:
    """Both widths, each measured: the document is never wider than the viewport."""
    for label, width in WIDTHS.items():
        page.set_viewport_size({"width": width, "height": 900})
        page.wait_for_timeout(100)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        assert scroll <= width, (name, label, scroll)
        page.screenshot(path=str(bench.shots / f"{name}-{label}.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 900})


def _set_home(bench: Bench, origin: str) -> None:
    """Where the fake's sign-in sends the browser back to: the site the test is driving."""
    bench.api_server.home = origin


# --- AC11: sign in, steward a target, see the receipt ------------------------------------------


def test_sign_in_then_steward_a_problem(bench: Bench, browser: Any) -> None:
    page = new_page(browser)
    path = f"/steward/{STEWARDLESS_TARGET}/"
    page.goto(bench.stewards_site + path)
    link = page.wait_for_selector(".steward-form a.btn")
    assert link.inner_text() == "Sign in with GitHub to continue"
    href = link.get_attribute("href")
    assert href == f"{bench.api}/auth/github/start?return=%2Fsteward%2F{STEWARDLESS_TARGET}%2F"
    assert page.inner_text(".session-slot") == "Sign in"
    shoot(page, bench, "steward-signed-out")

    _set_home(bench, bench.stewards_site)
    bench.fake.next_login = "mira"
    link.click()
    page.wait_for_url(bench.stewards_site + path)
    name = page.wait_for_selector("#steward-name")
    assert name.input_value() == "mira"
    assert page.inner_text(".session-slot .session-login") == "mira"
    assert page.get_attribute(".session-slot a[href='/me/']", "href") == "/me/"
    commitment = page.inner_text(".steward-form .commitment")
    from opn_gate import steward  # noqa: PLC0415

    assert commitment == steward.COMMITMENT
    submit = page.locator("button", has_text="Become steward")
    assert submit.is_disabled()  # not until the commitment is ticked
    page.check("#steward-accept")
    shoot(page, bench, "steward-form")
    submit.click()
    receipt = page.wait_for_selector(".steward-form .receipt")
    text = receipt.inner_text()
    assert text.startswith(
        f"You're the steward of {STEWARDLESS_TARGET}; "
        "it shows on the problem page in a few minutes."
    )
    assert page.get_attribute(".steward-form .receipt a", "href") == f"{REPO}/pull/{bench.fake.pr}"
    headers, body = bench.fake.posted("/stewards")[-1]
    assert body == {
        "target": STEWARDLESS_TARGET,
        "action": "commit",
        "name": "mira",
        "link": None,
        "accept": True,
    }
    assert headers.get("X-OPN-Web") == "1" and headers.get("Origin") == bench.stewards_site
    shoot(page, bench, "steward-receipt")

    # Back on the page, the service now lists the target among mira's: Step down, no form.
    page.reload()
    page.wait_for_selector(".steward-form button:has-text('Step down')")
    assert page.query_selector("#steward-name") is None
    page.context.close()


def test_a_second_commit_says_already(bench: Bench, browser: Any) -> None:
    page = new_page(browser)
    bench.fake.conflict.add("twice")
    _set_home(bench, bench.stewards_site)
    bench.fake.next_login = "twice"
    page.goto(bench.stewards_site + f"/steward/{STEWARDLESS_TARGET}/")
    page.click(".steward-form a.btn")
    page.wait_for_selector("#steward-name")
    page.check("#steward-accept")
    page.click("button:has-text('Become steward')")
    page.wait_for_selector(".steward-form .form-error:has-text('already')")
    assert page.inner_text(".steward-form .form-error") == "You're already its steward."
    page.context.close()


# --- AC11: the words controls by role ---------------------------------------------------------


def words_page(bench: Bench, browser: Any, login: str) -> Any:
    page = new_page(browser)
    _set_home(bench, bench.words_site)
    bench.fake.next_login = login
    page.goto(bench.words_site + NODE)
    page.click(".session-slot a.session-in")
    page.wait_for_url(bench.words_site + NODE)
    page.wait_for_selector(".words-ctl .words-actions")
    return page


def labels(page: Any, word: str) -> int:
    return int(page.locator("main button", has_text=word).count())


def test_a_steward_sees_approve_on_each_section_not_final(bench: Bench, browser: Any) -> None:
    bench.fake.stewards["stew"] = {TARGET}
    page = words_page(bench, browser, "stew")
    # drafted, written and two edits awaiting review; never the final sections.
    assert labels(page, "Approve") == 4
    assert labels(page, "Edit") == 2
    assert labels(page, "Withdraw") == 0
    page.locator(".words-approve button", has_text="Approve").first.scroll_into_view_if_needed()
    shoot(page, bench, "words-steward")
    page.locator(".words-approve button", has_text="Approve").first.click()
    page.wait_for_selector(".words-approve .receipt")
    _h, body = bench.fake.posted("/approvals")[-1]
    assert body["target"] == TARGET and body["node"] == gf.TUTORIAL
    assert body["kind"] in ("gloss", "explainer") and len(body["version"]) == 64
    assert isinstance(body["sections"], list) and len(body["sections"]) == 1
    page.context.close()


def test_a_stranger_sees_edit_and_no_approve(bench: Bench, browser: Any) -> None:
    page = words_page(bench, browser, "stranger")
    assert labels(page, "Edit") == 2
    assert labels(page, "Approve") == 0
    assert labels(page, "Withdraw") == 0
    gloss_ctl = page.locator('.words-ctl[data-kind="gloss"]')
    gloss_ctl.locator("button", has_text="Edit").click()
    box = gloss_ctl.locator("textarea")
    assert box.input_value().strip() == gf.GLOSS_VERIFIED
    gloss_ctl.locator("select").select_option("CC-BY-4.0")
    box.fill("Swap them: from <b>p</b> and q, get q and p.")
    # The licence's preview comes first (the old words); the typed words' preview after it.
    page.wait_for_selector('.words-ctl[data-kind="gloss"] .words-preview p:has-text("Swap them")')
    preview = gloss_ctl.locator(".words-preview").inner_html()
    assert "&lt;b&gt;" in preview and "<b>" not in preview  # escaped by the renderer
    dry = [b for _h, b in bench.fake.posted("/glosses") if b.get("dry_run")]
    assert dry and dry[-1]["subject"] == {"kind": "statement", "node_id": gf.TUTORIAL}
    assert dry[-1]["licence"] == "CC-BY-4.0" and len(dry[-1]["supersedes"]) == 64
    gloss_ctl.scroll_into_view_if_needed()
    shoot(page, bench, "words-edit")
    gloss_ctl.locator("button", has_text="Submit").click()
    page.wait_for_selector('.words-ctl[data-kind="gloss"] .receipt')
    final = bench.fake.posted("/glosses")[-1][1]
    assert final["dry_run"] is False and final["text"].startswith("Swap them")
    page.context.close()


def test_a_curator_sees_withdraw(bench: Bench, browser: Any) -> None:
    bench.fake.curators.add("cura")
    page = words_page(bench, browser, "cura")
    assert labels(page, "Withdraw") == 2 and labels(page, "Approve") == 4
    gloss_ctl = page.locator('.words-ctl[data-kind="gloss"]')
    gloss_ctl.locator("button", has_text="Withdraw").click()
    gloss_ctl.locator("input").fill("misreads the hypothesis")
    gloss_ctl.locator("button", has_text="Withdraw this version").click()
    page.wait_for_selector('.words-ctl[data-kind="gloss"] .receipt')
    body = bench.fake.posted("/glosses/withdrawals")[-1][1]
    assert body["record"].startswith(f"targets/{TARGET}/nodes/{gf.TUTORIAL}/gloss/")
    page.context.close()


def test_signed_out_the_node_page_draws_no_control(bench: Bench, browser: Any) -> None:
    page = new_page(browser)
    page.goto(bench.words_site + NODE)
    page.wait_for_selector(".session-slot a.session-in")
    assert labels(page, "Edit") == 0 and labels(page, "Approve") == 0
    assert page.locator(".words-ctl:visible").count() == 0
    page.context.close()


# --- AC11: the service down --------------------------------------------------------------------


def test_with_the_service_down_the_page_is_read_only(bench: Bench, browser: Any) -> None:
    page = new_page(browser)
    page.goto(bench.down_site + f"/steward/{STEWARDLESS_TARGET}/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)
    assert page.locator(".session-slot").is_hidden()
    assert page.locator(".steward-form *").count() == 0
    assert page.locator("main button, main input, main textarea").count() == 0
    assert "what the role asks" in page.inner_text("main").lower()  # the kicker is upper case
    shoot(page, bench, "service-down")
    page.goto(bench.down_site + "/")
    page.wait_for_load_state("networkidle")
    assert page.locator(".session-slot").is_hidden()
    page.context.close()


# --- R13: /me/ ---------------------------------------------------------------------------------


def test_me_shows_roles_waiting_sections_prs_and_step_down(bench: Bench, browser: Any) -> None:
    bench.fake.stewards["mestew"] = {TARGET}
    bench.fake.open_prs = [
        {"kind": "gloss", "target_id": TARGET, "node_id": gf.TUTORIAL, "pr_number": 42,
         "pr_url": f"{REPO}/pull/42", "pseudonym": "mestew"},
        {"kind": "gloss", "target_id": TARGET, "node_id": gf.TUTORIAL, "pr_number": 43,
         "pr_url": f"{REPO}/pull/43", "pseudonym": "someone-else"},
    ]  # fmt: skip
    page = new_page(browser)
    _set_home(bench, bench.words_site)
    bench.fake.next_login = "mestew"
    page.goto(bench.words_site + "/me/")
    page.click(".me a.btn")  # Sign in with GitHub, back to /me/
    page.wait_for_url(bench.words_site + "/me/")
    page.wait_for_selector(".me-roles")
    assert page.inner_text(".me-roles") == f"signed in as mestew · steward of {TARGET}"
    waiting = page.locator(f'.waiting[data-target="{TARGET}"]')
    assert waiting.is_visible() and waiting.locator("li").count() == 4
    page.wait_for_selector(".me-prs li")
    prs = page.locator(".me-prs li")
    assert prs.count() == 1 and prs.first.inner_text().startswith("#42")
    assert page.locator(".me button", has_text="Step down").count() == 1
    shoot(page, bench, "me")
    page.locator(".me button", has_text="Step down").click()
    page.wait_for_selector(".me .receipt")
    body = bench.fake.posted("/stewards")[-1][1]
    assert body["action"] == "step-down" and body["target"] == TARGET
    page.context.close()


# --- F24-T6 / AC10: the panel and write-up controls, by role ------------------------------------

PANEL_PAGE = f"/problems/{pf.STEWARDED_TARGET}/"


@pytest.fixture(scope="module")
def panel_site(bench: Bench, tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    root = pf.build(tmp_path_factory.mktemp("flows-panel"))
    site_dir = tmp_path_factory.mktemp("site-panel")
    render.write(
        render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=bench.api),
        site_dir,
    )
    server, origin = site_server(site_dir)
    bench.fake.origins.add(origin)
    yield origin
    server.shutdown()


def panel_shots() -> Path:
    shots = Path(os.environ.get("OPN_F24_SHOTS") or os.environ.get("OPN_F23_SHOTS") or "")
    if not str(shots) or str(shots) == ".":
        import tempfile  # noqa: PLC0415

        shots = Path(tempfile.mkdtemp(prefix="f24-shots-"))
    shots.mkdir(parents=True, exist_ok=True)
    return shots


def shoot_part(page: Any, selector: str, name: str) -> None:
    """Both widths, each measured for horizontal overflow; the part itself, and the page."""
    shots = panel_shots()
    for label, width in WIDTHS.items():
        page.set_viewport_size({"width": width, "height": 900})
        page.wait_for_timeout(150)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        assert scroll <= width, (name, label, scroll)
        page.locator(selector).first.screenshot(path=str(shots / f"{name}-{label}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


def panel_page(bench: Bench, browser: Any, origin: str, login: str, path: str = PANEL_PAGE) -> Any:
    page = new_page(browser)
    _set_home(bench, origin)
    bench.fake.next_login = login
    page.goto(origin + path)
    page.click(".session-slot a.session-in")
    page.wait_for_url(origin + path)
    page.wait_for_selector(".session-slot .session-login")
    page.wait_for_selector(".writeup-ctl .record-ctl")
    return page


def test_signed_out_the_panel_draws_no_control(bench: Bench, browser: Any, panel_site: str) -> None:
    page = new_page(browser)
    page.goto(panel_site + PANEL_PAGE)
    page.wait_for_selector(".writeup-ctl a.btn")
    assert page.locator(".panel-writeup button, .panel-writeup input").count() == 0
    assert page.inner_text(".writeup-ctl a.btn").startswith("Sign in with GitHub")
    shoot_part(page, ".panel-writeup", "panel-signed-out")
    page.context.close()


def test_a_member_votes_invites_and_acts_on_the_writeups(
    bench: Bench, browser: Any, panel_site: str
) -> None:
    page = panel_page(bench, browser, panel_site, pf.STEWARD_LOGIN)
    # Yes / No on the one open motion; Invite; Sign on the note only (the paper is signed);
    # Ask the panel to verify on the note only (the paper is already past verification).
    assert page.locator('.motions.open li[data-motion="1"] button').all_inner_texts() == [
        "Yes",
        "No",
    ]
    assert page.locator(".invite-ctl").count() == 1
    acts = page.locator('.writeup-acts[data-writeup="2"]')
    assert acts.locator("button", has_text="Sign").count() == 1
    assert acts.locator("button", has_text="Ask the panel to verify").count() == 1
    paper = page.locator('.writeup-acts[data-writeup="1"]')
    assert paper.locator("button", has_text="Ask the panel").count() == 0
    assert paper.locator("button:text-is('Sign')").count() == 0
    assert page.locator('.writeup-acts[data-writeup="3"]').count() == 0  # withdrawn
    shoot_part(page, ".panel-writeup", "panel-member")

    page.locator('.motions.open li[data-motion="1"] button', has_text="Yes").click()
    page.wait_for_selector('.motions.open li[data-motion="1"] .receipt')
    assert bench.fake.posted("/votes")[-1][1] == {
        "target": pf.STEWARDED_TARGET, "motion": 1, "vote": "yes"
    }  # fmt: skip

    page.fill("#invite-login", "expert-e")
    page.fill("#invite-note", "the <b>sieve</b> step")
    page.click(".invite-ctl button")
    page.wait_for_selector(".panel-ctl .receipt")
    assert bench.fake.posted("/motions")[-1][1] == {
        "target": pf.STEWARDED_TARGET, "kind": "invite",
        "subject": {"login": "expert-e", "note": "the <b>sieve</b> step"},
    }  # fmt: skip

    acts.locator("summary").click()
    acts.locator("button", has_text="Ask the panel to verify").click()
    page.wait_for_selector('.writeup-acts[data-writeup="2"] .receipt')
    assert bench.fake.posted("/motions")[-1][1]["subject"] == {"writeup": 2}

    paper.locator("summary").click()
    paper.locator("input[id^='wr-arxiv']").fill("2610.01234")
    paper.locator("button", has_text="Add arXiv id").click()
    page.wait_for_selector('.writeup-acts[data-writeup="1"] .receipt')
    assert bench.fake.posted("/writeups")[-1][1] == {
        "target": pf.STEWARDED_TARGET, "action": "arxiv", "writeup": 1, "arxiv": "2610.01234"
    }  # fmt: skip
    page.context.close()


def test_a_refusal_is_shown_in_the_services_words(
    bench: Bench, browser: Any, panel_site: str
) -> None:
    page = panel_page(bench, browser, panel_site, pf.SECOND_MEMBER)
    message = "The motion's window has closed."
    bench.fake.refuse["/votes"] = (409, {"error": "window-closed", "message": message})
    page.locator('.motions.open li[data-motion="1"] button', has_text="No").click()
    page.wait_for_selector(f'.motions.open .form-error:has-text("{message}")')
    page.context.close()


def test_an_invited_login_accepts(bench: Bench, browser: Any, panel_site: str) -> None:
    bench.fake.awaiting[pf.INVITEE] = {
        "votes": [],
        "invitations": [{"target": pf.STEWARDED_TARGET, "motion": 1, "note": pf.NOTE}],
    }
    page = panel_page(bench, browser, panel_site, pf.INVITEE)
    page.wait_for_selector(".accept-ctl")
    assert page.locator(".invite-ctl").count() == 0  # not a member
    assert page.locator(".motions.open button").count() == 0
    note = page.inner_text(".accept-ctl .invite-note")
    assert pf.NOTE in note  # set as text, so the markup is shown, never run
    accept = page.locator("button", has_text="Accept the invitation")
    assert accept.is_disabled()
    page.check("#accept-commitment")
    page.locator(".accept-ctl").scroll_into_view_if_needed()
    shoot_part(page, ".panel-writeup", "panel-invited")
    accept.click()
    page.wait_for_selector(".panel-ctl .receipt")
    body = bench.fake.posted("/stewards")[-1][1]
    assert body["motion"] == 1 and body["accept"] is True and body["action"] == "commit"
    assert body["target"] == pf.STEWARDED_TARGET and body["name"] == pf.INVITEE
    page.context.close()


def test_anyone_signed_in_records_a_writeup(bench: Bench, browser: Any, panel_site: str) -> None:
    page = panel_page(bench, browser, panel_site, "stranger2")
    assert page.locator(".invite-ctl, .writeup-acts, .motions.open button").count() == 0
    page.click(".record-ctl summary")
    page.select_option("#wr-kind", "note")
    page.fill("#wr-title", "Notes on the lemma")
    page.fill("#wr-url", "https://example.org/notes.pdf")
    page.fill("#wr-authors", "stranger2, alice-steward")
    page.locator(".record-ctl").scroll_into_view_if_needed()
    shoot_part(page, ".panel-writeup", "panel-record")
    page.click(".record-ctl button")
    page.wait_for_selector(".writeup-ctl .receipt")
    assert bench.fake.posted("/writeups")[-1][1] == {
        "target": pf.STEWARDED_TARGET, "action": "record", "kind": "note",
        "title": "Notes on the lemma", "url": "https://example.org/notes.pdf",
        "authors": ["stranger2", "alice-steward"],
    }  # fmt: skip
    page.context.close()


def test_rules_page_fits_both_widths(bench: Bench, browser: Any, panel_site: str) -> None:
    page = new_page(browser)
    page.goto(panel_site + "/rules/")
    page.wait_for_selector('tr[data-setting="steward_admission"]')
    shoot_part(page, "main", "rules")
    page.context.close()


def test_me_lists_votes_and_invitations(bench: Bench, browser: Any, panel_site: str) -> None:
    bench.fake.awaiting["waiter"] = {
        "votes": [{"target": pf.STEWARDED_TARGET, "motion": 1, "kind": "invite",
                   "subject": {"login": pf.INVITEE}, "closes": "2026-10-19"}],
        "invitations": [{"target": pf.STEWARDED_TARGET, "motion": 4, "note": pf.NOTE}],
    }  # fmt: skip
    bench.fake.open_prs = []
    page = new_page(browser)
    _set_home(bench, panel_site)
    bench.fake.next_login = "waiter"
    page.goto(panel_site + "/me/")
    page.click(".me a.btn")
    page.wait_for_url(panel_site + "/me/")
    page.wait_for_selector(".me-votes li")
    assert page.inner_text(".me-votes li") == (
        f"{pf.STEWARDED_TARGET} · motion #1: invite {pf.INVITEE} · closes 2026-10-19"
    )
    assert pf.NOTE in page.inner_text(".me-invitations li")
    href = page.get_attribute(".me-invitations li a", "href")
    assert href == f"/problems/{pf.STEWARDED_TARGET}/#panel"
    page.wait_for_selector(".me-prs, .me-section .cue")
    shoot_part(page, "main", "me")
    page.context.close()
