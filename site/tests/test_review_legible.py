# ruff: noqa: RUF001 — the statements and variants are Lean source, with its connectives
"""F26-T22, T23: a review page a signer can act on (Q24).

The owner, signed in as erdos-257's steward and so its intent signer, read its review page
(2026-10-28) and could not use it: eight questions, every one the same sentence about "a variant
of the statement" with no variant anywhere on the page, and no way to sign at all. The service
had ``POST /reviews/<t>/signatures`` since F26-T10; the site drew only the answer boxes. Now:

* a question a mutant raised shows the change, the statement and the variant beside it, the
  variant rebuilt from the candidate's Lean by the gate's own ``mutants`` (so the eight questions
  already on the record read too);
* each answer box sits under its own question, not in a list after all of them;
* the signatures section carries a slot the session script fills: signed out, a sign-in link;
  signed in, a form that posts one decision (accept or split naming a cluster, or send back)
  for the role the login holds.
"""

from __future__ import annotations

import functools
import html
import http.server
import json
import re
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import fixture
import pytest
from fixture import COMMIT, REVIEW_IDS, REVIEW_PROPOSER
from harness import TARGET
from test_review_page import API, PAGE, REPO, section, text_of

from opn_site import model, render

EVIDENCE = Path(__file__).resolve().parents[2] / "engineering" / "evidence" / "F26"
PERSON = REVIEW_IDS["person"]
CLUSTER = sorted((REVIEW_IDS["person"], REVIEW_IDS["model"]))


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return fixture.build_with_review(tmp_path_factory.mktemp("legible"))


@pytest.fixture(scope="module")
def pages(root: Path) -> dict[str, str]:
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=API)


def question_item(page: str, qid: str) -> str:
    m = re.search(rf'<li class="question" data-question="{qid}">.*?</li>', page, re.S)
    assert m is not None, qid
    return m.group(0)


# --- the variant beside the question ----------------------------------------------------------


def test_a_mutant_question_shows_the_change_the_statement_and_the_variant(
    pages: dict[str, str],
) -> None:
    item = question_item(section(pages[PAGE], "questions"), "q-2")
    words = text_of(item)
    assert "∧ → ∨" in words and "connective" in words, words
    assert html.escape("p ∧ q → q ∧ p") in item  # the statement, as the candidate has it
    assert html.escape("p ∧ q → q ∨ p") in item  # the variant the mutant exhibit checked
    assert PERSON in words  # whose claim was changed


def test_a_disagreement_question_carries_no_variant(pages: dict[str, str]) -> None:
    item = question_item(section(pages[PAGE], "questions"), "q-1")
    assert "mutant-variant" not in item


def test_a_mutant_detail_with_no_label_renders_the_question_alone(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    root = fixture.build_with_review(tmp_path_factory.mktemp("unlabelled"))
    path = root / "targets" / TARGET / "review" / "exhibits" / "e-0000ffff.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["detail"] = "a mutant the job described some other way"
    path.write_text(json.dumps(doc), encoding="utf-8")
    page = render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=API)[PAGE]
    item = question_item(section(page, "questions"), "q-2")
    assert "mutant-variant" not in item and "Waiting for the intent signer" in text_of(item)


def test_a_dropped_hypothesis_reads_as_code_and_markup_stays_escaped(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The gate writes a hypothesis label with backticks, and so does its question (F26-Q24);
    the page shows each span as code, never the backticks, and adds nothing else."""
    root = fixture.build_with_review(tmp_path_factory.mktemp("hypothesis"))
    base = root / "targets" / TARGET / "review"
    ex = json.loads((base / "exhibits" / "e-0000ffff.json").read_text(encoding="utf-8"))
    ex["detail"] = "`p ∧ q →` dropped at 0 (hypothesis): every test passes"
    (base / "exhibits" / "e-0000ffff.json").write_text(json.dumps(ex), encoding="utf-8")
    q = (base / "questions" / "q-2.yaml").read_text(encoding="utf-8")
    q = re.sub(r"question: .*", "question: 'Is `<b>x</b>` the same?'", q)
    (base / "questions" / "q-2.yaml").write_text(q, encoding="utf-8")
    page = render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=API)[PAGE]
    item = question_item(section(page, "questions"), "q-2")
    assert f"<code>{html.escape('p ∧ q →')}</code> dropped" in item
    assert '<pre class="lean">q ∧ p</pre>' in item
    assert "`" not in text_of(item)
    assert "<code>&lt;b&gt;x&lt;/b&gt;</code>" in item and "<b>x</b>" not in item


# --- the sign slot ----------------------------------------------------------------------------


def test_the_signatures_section_carries_the_sign_slot(root: Path, pages: dict[str, str]) -> None:
    sec = section(pages[PAGE], "signatures")
    m = re.search(r'<div class="review-sign-ctl" ([^>]*)hidden></div>', sec)
    assert m is not None, sec
    attrs = m.group(1)
    assert "data-review-sign" in attrs and f'data-target="{TARGET}"' in attrs

    def data(name: str) -> Any:
        found = re.search(rf'data-{name}="([^"]*)"', attrs)
        assert found is not None, name
        return json.loads(html.unescape(found.group(1)))

    assert data("clusters") == [CLUSTER]
    assert data("intent") == [REVIEW_PROPOSER]
    assert data("questions") == ["q-1", "q-2"]
    assert data("waiting") == 1
    assert "<form" not in sec and "<button" not in sec  # nothing in the static page posts
    no_api = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)[PAGE]
    assert "review-sign-ctl" not in no_api


# --- in a browser, against a fake service -------------------------------------------------------


POSTED: list[dict[str, Any]] = []
SIGNER: dict[str, Any] = {
    "signed_in": True,
    "login": REVIEW_PROPOSER,
    "pseudonym": REVIEW_PROPOSER,
    "curator": False,
    "stewards": [],
    "expires": "2026-12-01T12:00:00Z",
    "awaiting": {"votes": [], "invitations": []},
    "reviews": [],
}


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class FakeService(http.server.BaseHTTPRequestHandler):
    session: dict[str, Any] = dict(SIGNER)  # noqa: RUF012 — the tests swap it

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
        if self.path == f"/reviews/{TARGET}/signatures" and doc.get("role") == "independent":
            self.reply(
                403,
                {"error": "review-signer-wrote-candidate", "message": "you wrote c-1 (F26-R9)"},
            )
        elif self.path.startswith(f"/reviews/{TARGET}/"):
            self.reply(201, {"pr_number": 9, "pr_url": f"{REPO}/pull/9", "branch": "append/x"})
        else:
            self.reply(404, {"error": "not-found", "message": "no"})


@pytest.fixture(scope="module")
def served(root: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    api_server, api = serve(FakeService)
    site_dir = tmp_path_factory.mktemp("legible-site")
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


def test_the_intent_signer_signs_accept_naming_the_cluster(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FakeService.session = dict(SIGNER)
    POSTED.clear()
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + f"/problems/{TARGET}/review/")
        page.wait_for_selector(".review-sign-ctl .review-sign button")
        form = page.locator(".review-sign-ctl .review-sign")
        words = form.inner_text()
        assert f"Sign as {REVIEW_PROPOSER}" in words, words
        assert "1 question" in words and "waiting" in words, words
        # the role the login holds is chosen; the cluster is named by its representative
        assert page.locator(".review-sign input[name=role][value=intent]").is_checked()
        assert page.locator(".review-sign select.cluster").input_value() == CLUSTER[0]
        # send-back hides the cluster and offers a question instead
        page.locator(".review-sign input[name=decision][value=send-back]").check()
        assert not page.locator(".review-sign select.cluster").is_visible()
        assert page.locator(".review-sign select.question").is_visible()
        page.locator(".review-sign input[name=decision][value=accept]").check()
        assert page.evaluate("document.documentElement.scrollWidth") <= 1440
        page.locator("section:has(#signatures)").screenshot(
            path=str(EVIDENCE / "task-23-sign-form.png")
        )
        form.locator("button").click()
        page.wait_for_selector(".review-sign-ctl .receipt")
        assert POSTED[-1] == {
            "path": f"/reviews/{TARGET}/signatures",
            "body": {
                "role": "intent",
                "decision": "accept",
                "cluster": CLUSTER[0],
                "question": None,
            },
        }
        assert "Pull request #9" in page.locator(".review-sign-ctl .receipt").inner_text()
        browser.close()


def test_a_send_back_names_the_question_and_no_cluster(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    FakeService.session = dict(SIGNER)
    POSTED.clear()
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 900})
        page.goto(served + f"/problems/{TARGET}/review/")
        page.wait_for_selector(".review-sign-ctl .review-sign button")
        page.locator(".review-sign input[name=decision][value=send-back]").check()
        page.locator(".review-sign select.question").select_option("q-2")
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        page.locator("section:has(#signatures)").screenshot(
            path=str(EVIDENCE / "task-23-send-back-390.png")
        )
        page.locator(".review-sign button").click()
        page.wait_for_selector(".review-sign-ctl .receipt")
        assert POSTED[-1]["body"] == {
            "role": "intent",
            "decision": "send-back",
            "cluster": None,
            "question": "q-2",
        }
        browser.close()


def test_anyone_else_is_offered_the_independent_role_and_sees_a_refusal(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    FakeService.session = {**SIGNER, "login": "someone-else", "pseudonym": "someone-else"}
    POSTED.clear()
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + f"/problems/{TARGET}/review/")
        page.wait_for_selector(".review-sign-ctl .review-sign button")
        assert page.locator(".review-sign input[name=role][value=independent]").is_checked()
        page.locator(".review-sign button").click()
        page.wait_for_selector(".review-sign .form-error:not(:empty)")
        assert "F26-R9" in page.locator(".review-sign .form-error").inner_text()
        assert POSTED[-1]["body"]["role"] == "independent"
        browser.close()


def test_signed_out_a_sign_in_link(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    FakeService.session = {"signed_in": False}
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + f"/problems/{TARGET}/review/")
        page.wait_for_selector(".review-sign-ctl a")
        link = page.locator(".review-sign-ctl a")
        assert "Sign in" in link.inner_text()
        assert "/auth/github/start?return=" in (link.get_attribute("href") or "")
        assert page.locator(".review-sign-ctl button").count() == 0
        browser.close()


def test_each_answer_box_sits_under_its_own_question(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    FakeService.session = dict(SIGNER)
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + f"/problems/{TARGET}/review/")
        page.wait_for_selector(".review-answer textarea")
        assert page.locator('li.question[data-question="q-2"] .review-answer textarea').count() == 1
        # an answered question takes no box
        assert page.locator('li.question[data-question="q-1"] .review-answer').count() == 0
        page.locator('li.question[data-question="q-2"]').screenshot(
            path=str(EVIDENCE / "task-22-question-variant.png")
        )
        browser.close()
