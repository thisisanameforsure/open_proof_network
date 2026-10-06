"""F21-T12 (R14; AC11, the site half): words by section, and edits awaiting review.

The tutorial's explainer is ``gloss_fixture.sectioned_tree``'s: Dana's agent drafted three
sections; Alice rewrote the one on step ``hq`` (written); a curator signed the one on ``hp s3``
in Alice's version (verified); Bob then edited that verified section, which is pending. Its
statement's gloss is Alice's, signed by the curator, with Bob's edit of it pending.

Before review the page shows each section's words with a text label for its state — "drafted"
(the model named once above, F22-T17), "written by <author>", "read against the Lean by
<signer>" — each still beside the outline steps it names; beneath the verified section, Bob's
edit with its author, "awaiting review" and a diff against the words shown. Bob's words are
never shown as the section's. Once the curator signs that section of Bob's version, his words are
shown, labelled verified, and nothing awaits review.
"""

from __future__ import annotations

import re
from html import escape

import gloss_fixture as gf
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
NODE_PAGE = f"nodes/{TARGET}/{gf.TUTORIAL}/index.html"
STATEMENT = f"{TARGET}/nodes/{gf.TUTORIAL}/Statement.lean"
SHOWN_P = "The left half is h.1; pair them the other way."
EDIT_P = "read off the hypothesis"
SECTION = re.compile(
    r'<section class="ex-section" data-key="([^"]+)" data-steps="([^"]*)">(.*?)</section>', re.S
)
PENDING = re.compile(r'<div class="pending-edit" data-pending="([^"]+)"[^>]*>(.*?)</div>', re.S)


def build(tmp_path_factory: pytest.TempPathFactory, *, approve_edit: bool) -> dict[str, str]:
    root, _ = gf.sectioned_tree(tmp_path_factory.mktemp("pending"), approve_edit=approve_edit)
    return render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO)


@pytest.fixture(scope="module")
def before(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return build(tmp_path_factory, approve_edit=False)


@pytest.fixture(scope="module")
def after(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return build(tmp_path_factory, approve_edit=True)


def explainer_part(page: str) -> tuple[str, str]:
    """The node page's explainer section, split into what it shows and its history."""
    start = page.index('<h2 id="explainer">Explainer</h2>')
    section = page[start : page.index("<h2>Annex</h2>", start)]
    cut = section.index('<details class="history"')
    return section[:cut], section[cut:]


def state_of(html: str) -> tuple[str, str]:
    m = re.search(r'<p class="words-state" data-state="([a-z]+)">(.*?)</p>', html, re.S)
    assert m is not None, html[:300]
    return m.group(1), re.sub(r"<[^>]+>", "", m.group(2))


def slot_now(page: str) -> str:
    m = re.search(rf'<div class="gloss-slot" data-gloss-slot="{re.escape(STATEMENT)}">', page)
    assert m is not None
    rest = page[m.start() :]
    return rest[: rest.find('<details class="history"')]


def test_each_section_shows_its_words_and_state_and_the_edit_awaits_review(
    before: dict[str, str],
) -> None:
    page = before[NODE_PAGE]
    shown, history = explainer_part(page)
    sections = {key: (steps, body) for key, steps, body in SECTION.findall(shown)}
    assert list(sections) == [gf.KEY_OVERVIEW, gf.KEY_Q, gf.KEY_P]

    # Each section's words, with its state in text.
    # F22-T17 (14): the chip says the state; the model is named once, on the provenance line
    # above (contributor text, escaped, C9).
    assert state_of(sections[gf.KEY_OVERVIEW][1]) == (
        "drafted",
        "drafted, by the model named above",
    )
    assert f"drafted with {escape(gf.DRAFTED_WITH)}" in shown
    assert state_of(sections[gf.KEY_Q][1]) == ("written", "written by alice")
    assert "keep its right half" in sections[gf.KEY_Q][1]
    assert state_of(sections[gf.KEY_P][1]) == ("verified", f"read against the Lean by {gf.CURATOR}")
    assert SHOWN_P in sections[gf.KEY_P][1]

    # Still beside the outline steps they name, linked into the outline on the page.
    assert sections[gf.KEY_P][0] == "hp s3"
    for sid in ("hp", "s3"):
        link = re.search(rf'href="#(po-[0-9a-f]{{12}}-{sid})"', sections[gf.KEY_P][1])
        assert link is not None and f'id="{link.group(1)}"' in page

    # An unapproved edit is never the section's words.
    for _key, (_steps, body) in sections.items():
        prose = body[body.index('<div class="ex-prose">') :]
        prose = (
            prose[: prose.find('<div class="pending-edit"')] if "pending-edit" in prose else prose
        )
        assert EDIT_P not in prose

    # Beneath the verified section: Bob's edit, awaiting review, with its diff.
    pending = PENDING.findall(shown)
    assert [key for key, _ in pending] == [gf.KEY_P]
    edit = pending[0][1]
    assert "awaiting review" in edit.lower() and "written by bob" in edit
    diff = re.search(r'<pre class="diff">(.*?)</pre>', edit, re.S)
    assert diff is not None
    dels = "".join(re.findall(r'<span class="diff-del">(.*?)</span>', diff.group(1)))
    adds = "".join(re.findall(r'<span class="diff-add">(.*?)</span>', diff.group(1)))
    assert SHOWN_P in dels and EDIT_P in adds
    assert shown.index(edit) > shown.index(SHOWN_P)

    # The history still lists every version.
    assert history.count('<li class="version"') == 3

    # The statement's gloss: Alice's verified words, Bob's edit beneath them, awaiting review.
    now = slot_now(page)
    assert escape(gf.GLOSS_VERIFIED) in now
    assert state_of(now) == ("verified", f"read against the Lean by {gf.CURATOR}")
    gloss_words = now[: now.find('<div class="pending-edit"')]
    assert escape(gf.GLOSS_EDIT) not in gloss_words
    gp = PENDING.findall(now)
    assert [key for key, _ in gp] == ["whole"]
    assert "awaiting review" in gp[0][1].lower() and "written by bob" in gp[0][1]
    assert escape(gf.GLOSS_EDIT) in "".join(re.findall(r'class="diff-add">(.*?)</span>', gp[0][1]))

    # Nothing on the page accepts input (D-36).
    main = page[page.index("<main>") : page.index("</main>")]
    assert not re.search(r"<(form|input|textarea|select|button)\b", main)


def test_a_signed_edit_is_shown_and_verified(after: dict[str, str]) -> None:
    page = after[NODE_PAGE]
    shown, history = explainer_part(page)
    sections = {key: body for key, _steps, body in SECTION.findall(shown)}
    assert list(sections) == [gf.KEY_OVERVIEW, gf.KEY_Q, gf.KEY_P]
    assert state_of(sections[gf.KEY_P]) == ("verified", f"read against the Lean by {gf.CURATOR}")
    assert EDIT_P in sections[gf.KEY_P] and SHOWN_P not in sections[gf.KEY_P]
    assert state_of(sections[gf.KEY_Q]) == ("written", "written by alice")
    assert not PENDING.findall(shown)
    assert "awaiting review" not in shown.lower()
    assert history.count('<li class="version"') == 3

    now = slot_now(page)
    assert escape(gf.GLOSS_EDIT) in now and escape(gf.GLOSS_VERIFIED) not in now
    assert state_of(now) == ("verified", f"read against the Lean by {gf.CURATOR}")
    assert not PENDING.findall(now)
