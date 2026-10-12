"""F04-T44: a problem with a steward says co-stewards are welcome and how one joins.

Once a target has a steward, D-32 (v3.34) admits a new one by a passed invitation of its panel
and their own acceptance, or by a curator adding them; a self-commitment is refused at the gate
(``steward-invitation-required``, F24-R4). The erdos-1094 page showed its steward and offered a
would-be co-steward nothing, and the steward form page drew the self-commit form anyway, so a
second mathematician's submission would fail after the fact. Now the problem page's steward card
says co-stewards are welcome and how they join, and the form page says it up front and carries
no self-commit form for a problem whose panel has a member.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fixture import COMMIT, STEWARD_LOGIN, STEWARDED_TARGET, STEWARDLESS_TARGET, build_with_stewards

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.invalid"
STEWARD_JS = Path(render.__file__).parent / "static" / "steward.js"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = build_with_stewards(tmp_path_factory.mktemp("co-stewards"))
    site = model.load_site(root, COMMIT)
    assert [s["login"] for s in site.targets[STEWARDED_TARGET].stewards] == [STEWARD_LOGIN]
    return render.render_site(site, repo_url=REPO, api_url=API)


def text(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def steward_card(page: str) -> str:
    start = page.index('<aside class="card steward-card">')
    return page[start : page.index("</aside>", start)]


def test_the_problem_page_welcomes_a_co_steward_and_says_how(pages: dict[str, str]) -> None:
    card = steward_card(pages[f"problems/{STEWARDED_TARGET}/index.html"])
    words = text(card)
    assert "Co-stewards are welcome" in words, words
    assert "invit" in words and "panel" in words and "curator" in words, words
    assert f'href="/steward/{STEWARDED_TARGET}/"' in card
    assert 'href="/rules/"' in card


def test_the_form_page_says_up_front_a_new_steward_comes_by_invitation(
    pages: dict[str, str],
) -> None:
    page = pages[f"steward/{STEWARDED_TARGET}/index.html"]
    head = page[page.index('<section class="page-head steward-head">') :]
    head = head[: head.index("</section>")]
    words = text(head)
    assert "by invitation" in words and "Co-stewards are welcome" in words, words
    assert f'href="/problems/{STEWARDED_TARGET}/#panel"' in head
    slot = re.search(r'<div class="steward-form"([^>]*)></div>', page)
    assert slot is not None, "the slot stays: a current steward steps down through it"
    assert 'data-invitation="required"' in slot.group(1)


def test_a_problem_with_no_steward_keeps_the_self_commit_form(pages: dict[str, str]) -> None:
    page = pages[f"steward/{STEWARDLESS_TARGET}/index.html"]
    slot = re.search(r'<div class="steward-form"([^>]*)></div>', page)
    assert slot is not None and "data-invitation" not in slot.group(1)
    assert "by invitation" not in text(page)


def test_the_script_draws_no_self_commit_form_where_an_invitation_is_required() -> None:
    """The slot's flag reaches steward.js: a signed-in visitor who is not yet a steward of such a
    problem gets no commit form (a current steward still gets Step down)."""
    js = STEWARD_JS.read_text(encoding="utf-8")
    then = js[js.index("O.session.then") :]
    assert (
        then.index("stepDown(s)") < then.index('invitation === "required"') < then.index("form(s)")
    ), then
