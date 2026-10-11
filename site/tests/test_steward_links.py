"""F23-T8 / AC10: the header's sign-in slot, the steward pages and the calls to action that lead
to them (R1, R5, R6, R7, R15; D-36 v3.33).

The static files take no input: the header carries an empty slot that ``session.js`` fills only
once the service answers ``GET /session``, the steward form is an empty slot ``steward.js`` draws
into, and no page carries an Edit, Approve, Withdraw, Become steward or Sign out control of its
own. Every call to become a known problem's steward goes to ``/steward/<target>/``, never to the
Docs page.
"""

from __future__ import annotations

import re
from html import escape

import pytest
from fixture import (
    CALIBRATION_TARGET,
    COMMIT,
    RESOLVED_TARGET,
    STEWARDED_TARGET,
    STEWARDLESS_TARGET,
    build_with_stewards,
)

from opn_gate import steward
from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.invalid"
SLOT = '<span class="session-slot" data-session hidden></span>'
SESSION_SCRIPT = f'<script src="/session.js" data-api="{API}"></script>'
#: The words of a control that needs a session (R12, R13, R7, R1): none is in any static page.
CONTROL_WORDS = re.compile(
    r">\s*(Edit|Approve|Withdraw|Become steward|Step down|Sign out|Steward this target)\s*<"
)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = build_with_stewards(tmp_path_factory.mktemp("steward-links"))
    site = model.load_site(root, COMMIT)
    return site, render.render_site(site, repo_url=REPO, api_url=API)


@pytest.fixture(scope="module")
def pages(built: tuple[model.Site, dict[str, str]]) -> dict[str, str]:
    return built[1]


def html_pages(pages: dict[str, str]) -> dict[str, str]:
    """The site's own pages: every one rendered through the frame. The decisions document and
    the other copied documents are foreign files served beside them (links.check's ``foreign``)."""
    return {
        rel: text
        for rel, text in pages.items()
        if rel.endswith(".html") and '<footer class="provenance">' in text
    }


def header(page: str) -> str:
    return page[page.index('<header class="masthead">') : page.index("</header>")]


def test_every_page_has_the_session_slot_and_script(pages: dict[str, str]) -> None:
    """R1, R15: an empty, hidden slot in every header, and the script that fills it, pointed at
    the configured service; the slot holds nothing until the service answers."""
    found = html_pages(pages)
    assert len(found) > 20  # guard: the walk sees the whole site
    for rel, page in found.items():
        assert SLOT in header(page), rel
        assert SESSION_SCRIPT in page, rel
        assert page.index(SESSION_SCRIPT) < page.index("</body>"), rel


def test_without_a_service_the_slot_stays_and_no_script_loads(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """C7: a build with no service address draws the read-only page: the slot, no script."""
    root = build_with_stewards(tmp_path_factory.mktemp("steward-links-off"))
    files = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)
    for rel, page in html_pages(files).items():
        assert SLOT in header(page), rel
        assert "/session.js" not in page and "/steward.js" not in page, rel


def needs_steward_link(page: str) -> re.Match[str] | None:
    return re.search(
        r'<a class="[^"]*needs-steward[^"]*" href="/steward/">Needs a steward '
        r'<span class="n">(\d+)</span>',
        page,
    )


def test_home_and_problems_link_needs_a_steward_with_its_count(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """R5: "Needs a steward" is a link with its count to /steward/ on both pages; the count is
    the number of lines /steward/ lists; the Problems filter stays."""
    _site, pages = built
    listed = re.findall(r'<li class="steward-row"', pages["steward/index.html"])
    for rel in ("index.html", "problems/index.html"):
        m = needs_steward_link(pages[rel])
        assert m is not None, rel
        assert int(m.group(1)) == len(listed), rel
    problems = pages["problems/index.html"]
    assert 'data-filter="unstewarded"' in problems  # the filter stays


def test_the_steward_index_lists_the_problems_without_one(pages: dict[str, str]) -> None:
    """R5: one line per target with no active steward that can have one, each with Steward this
    to its own page; a stewarded, a calibration and an on-ramp target are not listed."""
    page = pages["steward/index.html"]
    rows = re.findall(r'<li class="steward-row" data-target="([^"]+)">(.*?)</li>', page, re.S)
    ids = [tid for tid, _ in rows]
    assert STEWARDLESS_TARGET in ids and RESOLVED_TARGET in ids
    assert STEWARDED_TARGET not in ids and CALIBRATION_TARGET not in ids
    for tid, row in rows:
        assert f'href="/steward/{tid}/">Steward this</a>' in row
        assert f'href="/problems/{tid}/"' in row
    assert "<button" not in page


def test_every_target_has_a_steward_page(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, pages = built
    for tid in site.targets:
        assert f"steward/{tid}/index.html" in pages, tid


def test_the_steward_page_carries_what_the_form_needs_and_no_control(
    pages: dict[str, str],
) -> None:
    """R7: the statement in prose, what the role asks in three lines, Read more to the Docs
    anchor, and an empty form slot carrying the commitment sentence as data — verbatim, from
    opn_gate.steward — for the script to draw; the page itself has no input and no button."""
    page = pages[f"steward/{STEWARDLESS_TARGET}/index.html"]
    assert 'class="informal' in page
    asks = re.findall(r'<li class="asks">', page)
    assert len(asks) == 3
    assert '<a href="/docs/#stewards">Read more' in page
    slot = re.search(r'<div class="steward-form"([^>]*)></div>', page)
    assert slot is not None
    attrs = slot.group(1)
    assert f'data-target="{STEWARDLESS_TARGET}"' in attrs
    assert f'data-commitment="{escape(steward.COMMITMENT)}"' in attrs
    assert f'<script src="/steward.js" data-api="{API}"></script>' in page
    for tag in ("<button", "<form", "<textarea", "<select"):
        assert tag not in page.split("<main>")[1], tag


def test_a_problem_that_takes_no_steward_says_so_and_draws_no_form(
    pages: dict[str, str],
) -> None:
    page = pages[f"steward/{CALIBRATION_TARGET}/index.html"]
    assert 'class="steward-form"' not in page and "/steward.js" not in page
    assert "no steward" in page.lower()


def test_steward_calls_to_action_go_to_the_form_never_the_docs(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """R6: the problem page's card and stewards section, the problem cards and rows, About and
    Home: a known target's call goes to /steward/<target>/, a general one to /steward/; the
    Docs anchor is linked only by the steward pages' Read more and the Docs page itself."""
    site, pages = built
    page = pages[f"problems/{STEWARDLESS_TARGET}/index.html"]
    assert f'href="/steward/{STEWARDLESS_TARGET}/">Become its steward</a>' in page
    resolved = pages[f"problems/{RESOLVED_TARGET}/index.html"]
    assert f'href="/steward/{RESOLVED_TARGET}/">Become its steward</a>' in resolved
    assert 'href="/steward/">How stewardship works' in pages["index.html"]
    assert 'href="/steward/">Steward a problem' in pages["about/index.html"]
    for rel, text in html_pages(pages).items():
        if rel.startswith(("steward/", "docs/")):
            continue
        assert "/docs/#stewards" not in text, rel
    # The proposal form stays the way to propose a new problem.
    assert "issues/new?template=" in pages["index.html"]
    assert "issues/new?template=" in pages["about/index.html"]
    assert len(site.targets) >= 4


def test_no_static_page_has_a_session_control(pages: dict[str, str]) -> None:
    """R15, R12: no Edit, Approve, Withdraw, Become steward, Step down or Sign out control is in
    any static page, and no record page, steward page or /me/ carries a button, a form or a text
    box; every one of them is drawn by script after the service answers."""
    for rel, page in html_pages(pages).items():
        main = page.split("<main>", 1)[1]
        assert not CONTROL_WORDS.search(main), (rel, CONTROL_WORDS.search(main))
        assert "<form" not in page and "<textarea" not in page, rel
        if rel.startswith(("nodes/", "steward/", "me/")) or "/proofs/" in rel:
            assert "<button" not in main, rel
