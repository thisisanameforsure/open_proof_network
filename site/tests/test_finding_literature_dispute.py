"""F04-T63 (D-25 v3.45), part 2: a disputed proposal is shown, and a signed-in steward of the
target or a curator can confirm or dispute an awaiting proposal from the node's own page.

v3.45 lets a steward's or curator's signed literature record name in ``disputes`` the proposal
it rejects, carrying the signer's own reading; the products publish that reading as the node's
``literature`` with the rejected proposal beside it (``graph/v13`` ``literature.disputes``).
The site says "<signer> disputed <contributor>'s proposal (<its words>) and reads the statement
as <the signer's words>", links the rejected record as records are linked, and demarcates the
signer's own summary as untrusted text as before. On the node page the awaiting proposal gets
Confirm and Dispute for a signed-in steward of the target or a curator (today only ``/me/``
has Confirm); a signed-out reader sees no control; one script serves both pages.
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import re
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET
from test_finding_literature_marks import DEP, NONE, ROOT, with_literature
from test_finding_literature_status import literature_dir_allowed  # noqa: F401 — the layout rule

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.test"
STATIC = Path(render.__file__).resolve().parent / "static"
JS = (
    (STATIC / "literature.js").read_text(encoding="utf-8")
    if (STATIC / "literature.js").is_file()
    else ""
)
ME_JS = (STATIC / "me.js").read_text(encoding="utf-8")
NODE_DIR = f"targets/{TARGET}/nodes/{ROOT}"
DISPUTED = f"{NODE_DIR}/literature/20261009T125137Z-t1009-b.yaml"
READING = f"{NODE_DIR}/literature/20261019T090000Z-mike.yaml"
DEP_PROPOSAL = f"targets/{TARGET}/nodes/{DEP}/literature/20261009T144817Z-t1009-c.yaml"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = with_literature(tmp_path_factory.mktemp("dispute"))
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO, api_url=API)


def block(page: str) -> str:
    start = page.index('<div class="literature" data-block="literature">')
    depth = 0
    for m in re.finditer(r"<div\b|</div>", page[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return page[start : start + m.end()]
    raise AssertionError("unbalanced literature block")


# --- (a) the dispute on the page ----------------------------------------------------------------


def test_the_model_reads_the_disputed_proposal(built: tuple[model.Site, dict[str, str]]) -> None:
    site, _ = built
    nodes = site.targets[TARGET].nodes
    lit = nodes[ROOT].literature
    assert lit is not None and lit.confirmed and lit.status == "known"
    assert lit.disputes == model.DisputedProposal(
        status="open", record=DISPUTED, contributor="t1009-b"
    )
    assert nodes[ROOT].literature_proposed is None, "a rejected proposal is covered (v3.45)"
    dep = nodes[DEP].literature_proposed
    assert dep is not None and dep.disputes is None
    assert nodes[NONE].literature is None


def test_a_confirmation_without_a_dispute_reads_none(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    rel = fixture.write_literature(
        root, ROOT, status="known", contributor="mike", date="2026-10-19T09:00:00Z", signed=True
    )
    fixture.publish_v335(
        root,
        literature={
            ROOT: {
                "status": "known",
                "record": rel,
                "contributor": "mike",
                "confirmed_by": "mike",
                "confirmation": rel,
                "disputes": None,
            }
        },
    )
    lit = model.load_site(root, fixture.COMMIT).targets[TARGET].nodes[ROOT].literature
    assert lit is not None and lit.disputes is None
    page = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)[
        f"nodes/{TARGET}/{ROOT}/index.html"
    ]
    assert "disputed" not in block(page)


def test_the_block_says_who_disputed_whose_proposal_and_links_the_rejected_record(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _, pages = built
    page = pages[f"nodes/{TARGET}/{ROOT}/index.html"]
    b = block(page)
    sentence = re.search(r'<p class="literature-dispute">(.*?)</p>', b, re.S)
    assert sentence is not None, b
    s = sentence.group(1)
    assert s.startswith("<code>mike</code> disputed <code>t1009-b</code>&rsquo;s proposal (")
    assert "Open problem: no proof is known" in s
    assert f'<a class="file" href="{REPO}/blob/{fixture.COMMIT}/{DISPUTED}">record</a>' in s
    assert "and reads the statement as <strong>Known: a proof is published and not formalised" in s
    # The fact line is the signer's reading, confirmed by the signer; the summary is the
    # signer's own record, demarcated as untrusted text as before.
    fact = "<strong>Known: a proof is published and not formalised</strong> &middot; confirmed by "
    assert fact + "<code>mike</code>" in b
    assert 'data-block="literature-summary"' in b and "Konyagin proved it in 1999." in b
    assert "Untrusted: summary by mike" in b
    # The dispute sentence follows the fact line, before the signer's references and summary.
    assert b.index('class="literature-dispute"') < b.index('class="literature-refs"')
    # The rejected record is among the files the page renders (R2), as records are.
    assert page.count(f"/blob/{fixture.COMMIT}/{DISPUTED}") >= 2
    assert "awaits confirmation" not in b and "Proposed by" not in b


def test_the_dispute_escapes_the_contributors_name(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    rel = fixture.write_literature(
        root, ROOT, status="known", contributor="mike", date="2026-10-19T09:00:00Z", signed=True
    )
    fixture.publish_v335(
        root,
        literature={
            ROOT: {
                "status": "known",
                "record": rel,
                "contributor": "mike",
                "confirmed_by": "mike",
                "confirmation": rel,
                "disputes": {
                    "status": "open",
                    "record": "literature/20261009T125137Z-x.yaml",
                    "contributor": "<b>x</b>",
                },
            }
        },
    )
    site = model.load_site(root, fixture.COMMIT)
    b = block(render.render_site(site, repo_url=REPO)[f"nodes/{TARGET}/{ROOT}/index.html"])
    assert "<b>x</b>" not in b and "&lt;b&gt;x&lt;/b&gt;" in b


def test_the_panel_on_the_problem_page_carries_the_same_sentence(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _, pages = built
    page = pages[f"problems/{TARGET}/index.html"]
    panel = re.search(
        rf'<div class="card panel" data-node="{ROOT}"(.*?)(?=<div class="card panel"|$)', page, re.S
    )
    assert panel is not None
    assert "<code>mike</code> disputed <code>t1009-b</code>" in panel.group(1)


# --- (b) Confirm and Dispute on the node page ---------------------------------------------------


def act_slot(page: str) -> str | None:
    m = re.search(r'<div class="lit-act"([^>]*) hidden>(.*?)</div>', page, re.S)
    return m.group(0) if m else None


def test_the_node_page_carries_the_awaiting_proposal_as_a_hidden_row_with_its_data(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _, pages = built
    page = pages[f"nodes/{TARGET}/{DEP}/index.html"]
    slot = act_slot(page)
    assert slot is not None, "no slot for the awaiting proposal"
    assert f'data-target="{TARGET}"' in slot and f'data-node="{DEP}"' in slot
    row = re.search(r'<li class="lit-row"([^>]*)>', slot)
    assert row is not None
    attrs = row.group(1)
    assert f'data-node="{DEP}"' in attrs
    assert 'data-record="literature/20261009T144817Z-t1009-c.yaml"' in attrs
    assert 'data-status="open"' in attrs
    assert "data-references=" in attrs and "data-summary=" in attrs
    assert "t1009-c" in slot and "Open problem: no proof is known" in slot
    # No control in the static page (F23-R15): the script adds them after GET /session.
    main = page.split("<main>", 1)[1]
    assert not re.search(r"<(form|input|textarea|select|button)\b", main)
    assert '<script src="/literature.js"' in page
    assert "/literature.js" in render.SCRIPTS


def test_a_node_with_a_confirmed_status_or_no_record_carries_no_slot(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _, pages = built
    for nid in (ROOT, NONE):
        page = pages[f"nodes/{TARGET}/{nid}/index.html"]
        assert act_slot(page) is None, nid
        assert "/literature.js" not in page, nid


def test_without_a_service_address_the_page_carries_no_slot_or_script(tmp_path: Path) -> None:
    root = with_literature(tmp_path)
    pages = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    page = pages[f"nodes/{TARGET}/{DEP}/index.html"]
    assert act_slot(page) is None and "/literature.js" not in page


def test_the_me_page_rows_and_the_node_pages_row_are_one_function(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _, pages = built
    me = pages["me/index.html"]
    me_row = re.search(r'<li class="lit-row"[^>]*data-node="' + DEP + '"[^>]*>', me)
    node_row = re.search(
        r'<li class="lit-row"[^>]*data-node="' + DEP + '"[^>]*>',
        pages[f"nodes/{TARGET}/{DEP}/index.html"],
    )
    assert me_row is not None and node_row is not None
    assert me_row.group(0) == node_row.group(0)
    assert '<script src="/literature.js"' in me and me.index("/literature.js") < me.index("/me.js")


def test_the_script_gates_on_the_session_and_posts_the_two_shapes() -> None:
    """Confirm posts what ``/me/`` posts today; Dispute posts ``{node_id, disputes, status,
    references, summary}`` from an inline form; both only for a steward of the target or a
    curator, drawn after ``GET /session``; ``me.js`` reuses the same Confirm."""
    assert JS, "static/literature.js is missing"
    assert '"/literature/confirm"' in JS
    for key in ("node_id", "record", "disputes", "status", "references", "summary"):
        assert re.search(rf"\b{key}\s*:", JS), key
    assert "s.curator" in JS and "s.stewards.indexOf" in JS
    assert "signed_in" in JS
    assert "Confirm" in JS and "Dispute" in JS
    for status in render.LITERATURE_WORDS:
        assert f'"{status}"' in JS, status
    assert "O.literature" in JS or "window.OPN.literature" in JS
    assert "O.literature.confirmButton" in ME_JS
    assert '"/literature/confirm"' not in ME_JS, "one function, in literature.js"


# --- in a browser, against a fake service -------------------------------------------------------


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


POSTED: list[dict[str, Any]] = []


class FakeService(http.server.BaseHTTPRequestHandler):
    """``GET /session`` signed in as a steward of the fixture's target (or, with
    ``?curator``-free paths, exactly that); ``POST /literature/confirm`` records the body and
    answers 201 with a pull request."""

    session: dict[str, Any] = {  # noqa: RUF012 — the tests swap it to drive the gate
        "signed_in": True,
        "login": "alice-steward",
        "pseudonym": "alice-steward",
        "curator": False,
        "stewards": [TARGET],
        "expires": "2026-10-20T12:00:00Z",
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
        n = int(self.headers.get("Content-Length") or 0)
        doc = json.loads(self.rfile.read(n) or b"{}")
        POSTED.append({"path": self.path, "body": doc})
        if self.path == "/literature/confirm":
            self.reply(201, {"pr_number": 7, "pr_url": f"{REPO}/pull/7", "branch": "append/x"})
        else:
            self.reply(404, {"error": "not-found", "message": "no"})


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    api_server, api = serve(FakeService)
    root = with_literature(tmp_path_factory.mktemp("lit-graph"))
    site_dir = tmp_path_factory.mktemp("lit-site")
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


def test_a_steward_sees_confirm_and_dispute_and_a_dispute_posts_the_signers_reading(
    served: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Needs Playwright (``uv run --frozen --with playwright pytest …``); without it this test
    skips, which proves nothing. Screenshots go to ``$OPN_F04_T63_SHOTS`` when set."""
    sync_api = pytest.importorskip("playwright.sync_api")
    shots = Path(os.environ.get("OPN_F04_T63_SHOTS") or tmp_path_factory.mktemp("shots"))
    shots.mkdir(parents=True, exist_ok=True)
    POSTED.clear()
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + f"/nodes/{TARGET}/{DEP}/")
        page.wait_for_selector(".lit-act button")
        slot = page.locator(".lit-act")
        assert not slot.evaluate("e => e.hidden")
        buttons = slot.locator("button")
        assert [buttons.nth(i).inner_text() for i in range(buttons.count())] == [
            "Confirm",
            "Dispute",
        ]
        slot.scroll_into_view_if_needed()
        slot.screenshot(path=str(shots / "task-63-node-act-steward-1440.png"))
        page.get_by_role("button", name="Dispute").click()
        page.wait_for_selector(".lit-dispute textarea")
        page.locator(".lit-dispute select").select_option("known")
        page.locator(".lit-dispute textarea").fill("Konyagin proved it in 1999.")
        page.locator(".lit-dispute input[name=title]").fill("S. V. Konyagin, 1999")
        page.locator(".lit-dispute input[name=url]").fill("https://example.org/konyagin")
        slot.screenshot(path=str(shots / "task-63-node-act-dispute-form-1440.png"))
        page.get_by_role("button", name="File the dispute").click()
        page.wait_for_selector(".lit-act .receipt")
        receipt = page.locator(".lit-act .receipt").inner_text()
        assert "Dispute filed" in receipt and "#7" in receipt
        slot.screenshot(path=str(shots / "task-63-node-act-dispute-filed-1440.png"))
        assert POSTED == [
            {
                "path": "/literature/confirm",
                "body": {
                    "node_id": DEP,
                    "disputes": "literature/20261009T144817Z-t1009-c.yaml",
                    "status": "known",
                    "references": [
                        {
                            "title": "S. V. Konyagin, 1999",
                            "url": "https://example.org/konyagin",
                            "note": None,
                        }
                    ],
                    "summary": "Konyagin proved it in 1999.",
                },
            }
        ]
        # Confirm, on a fresh page, posts exactly what /me/ posts today.
        POSTED.clear()
        page.goto(served + f"/nodes/{TARGET}/{DEP}/")
        page.wait_for_selector(".lit-act button")
        page.get_by_role("button", name="Confirm").click()
        page.wait_for_selector(".lit-act .receipt")
        assert "Confirmation filed" in page.locator(".lit-act .receipt").inner_text()
        assert POSTED[0]["body"] == {
            "node_id": DEP,
            "record": "literature/20261009T144817Z-t1009-c.yaml",
            "status": "open",
            "references": [{"title": "Where the problem is listed", "url": None, "note": None}],
            "summary": "What the literature says, in the contributor's words.",
        }
        # At 390 the slot does not widen the page.
        page.set_viewport_size({"width": 390, "height": 900})
        page.wait_for_timeout(100)
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        page.locator(".lit-act").screenshot(path=str(shots / "task-63-node-act-steward-390.png"))
        browser.close()


def test_a_reader_who_is_not_a_steward_of_the_target_sees_no_control(
    served: str,
) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for session in (
            {"signed_in": False},
            {**FakeService.session, "stewards": ["another-problem"], "curator": False},
        ):
            FakeService.session = session
            page.goto(served + f"/nodes/{TARGET}/{DEP}/")
            page.wait_for_timeout(400)
            assert page.locator(".lit-act").evaluate("e => e.hidden")
            assert page.locator(".lit-act button").count() == 0
        FakeService.session = {**FakeService.session, "stewards": [], "curator": True}
        page.goto(served + f"/nodes/{TARGET}/{DEP}/")
        page.wait_for_selector(".lit-act button")
        assert page.locator(".lit-act button").count() == 2
        browser.close()
