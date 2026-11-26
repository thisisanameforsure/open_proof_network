"""F34-T28 (handoff §3.4 Review: "a 'Your turn' note for the signed-in intent signer").

The review page is static; ``GET /session`` already names the questions waiting for the signed-in
login as this review's intent signer (``reviews``, F26-T11), so the page carries one empty, hidden
slot and ``session.js`` fills it — "Your turn", how many questions wait, and what an answer does —
only when that list holds a question of this problem. Signed out, signed in as someone else, or
with nothing waiting, the slot stays hidden and empty.

Browser tests run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest site/tests/test_f34_your_turn.py``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_review_legible import SIGNER, FakeService, pages, root, served  # noqa: F401
from test_review_page import PAGE


def test_the_review_page_carries_one_hidden_slot(pages: dict[str, str]) -> None:  # noqa: F811
    page = pages[PAGE]
    slot = re.findall(
        r'<div class="your-turn" role="note" data-your-turn="([^"]+)" hidden></div>', page
    )
    assert slot == [TARGET]
    assert page.index("data-your-turn") < page.index('class="review-progress"')


def _note(
    served: str,  # noqa: F811
    session: dict[str, Any],
    shot: Path | None = None,
) -> tuple[bool, str]:
    sync_api = pytest.importorskip("playwright.sync_api")
    FakeService.session = session
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + f"/problems/{TARGET}/review/")
        page.wait_for_function("() => window.OPN && window.OPN.session")
        page.evaluate("() => window.OPN.session")
        page.wait_for_timeout(200)
        note = page.locator("[data-your-turn]")
        if shot and note.is_visible():
            page.locator("h1").scroll_into_view_if_needed()
            box = page.locator("h1").bounding_box()
            assert box is not None
            page.screenshot(
                path=str(shot),
                clip={"x": 0, "y": max(0, box["y"] - 40), "width": 1440, "height": 420},
            )
        out = (note.is_visible(), note.text_content() or "")
        browser.close()
    return out


def waiting(n: int, target: str = TARGET) -> list[dict[str, str]]:
    return [
        {"target": target, "question": f"q-{i}", "text": "?", "page": f"/problems/{target}/review/"}
        for i in range(1, n + 1)
    ]


def test_the_intent_signer_sees_whose_turn_it_is(served: str) -> None:  # noqa: F811
    shot = (
        Path(__file__).resolve().parents[2] / "engineering/evidence/F34/task-28-your-turn-1440.png"
    )
    shown, text = _note(served, {**SIGNER, "reviews": waiting(3) + waiting(2, "elsewhere")}, shot)
    assert shown
    assert text.startswith("Your turn ")
    assert "3 questions wait for you" in text


def test_one_question_is_singular(served: str) -> None:  # noqa: F811
    shown, text = _note(served, {**SIGNER, "reviews": waiting(1)})
    assert shown and "1 question waits for you" in text


@pytest.mark.parametrize(
    "session",
    [
        {"signed_in": False},
        {**SIGNER, "login": "someone-else", "reviews": []},
        {**SIGNER, "reviews": waiting(4, "elsewhere")},
    ],
    ids=["signed-out", "not-the-signer", "waiting-elsewhere"],
)
def test_anyone_else_sees_nothing(served: str, session: dict[str, Any]) -> None:  # noqa: F811
    shown, text = _note(served, session)
    assert not shown and text == ""
