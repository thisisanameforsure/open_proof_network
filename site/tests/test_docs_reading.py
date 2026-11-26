"""F19-T9, F20-T12: the Docs page tells a reader how to read a proof page, and the site's "improve
these words" links land on the guide's section about glosses, explainers and outlines.

The page is documentation of the renderer, so the tests hold it to the renderer's own words: every
provenance label a block can open with has a row in the Docs page's table (a label added to
``PROVENANCE`` turns this red until the page says what it means), and ``GLOSS_GUIDE_HREF``'s
fragment is an id the rendered guide carries, read from the tested guide itself.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import fixture
import pytest

from opn_site import model, prose, render

REPO = "https://github.com/example/graph"
GUIDE = Path(__file__).resolve().parents[2] / "gate" / "agents" / "AGENTS.md"


@pytest.fixture(scope="module")
def docs(tmp_path_factory: pytest.TempPathFactory) -> str:
    """The Docs page of the fixture graph carrying the tested guide, as the live graph does."""
    root = fixture.build(tmp_path_factory.mktemp("graph"))
    shutil.copyfile(GUIDE, root / "AGENTS.md")
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)[
        "docs/reading/index.html"  # F34-T6: the reading guide and the state map have a page
    ]


def reading(docs: str) -> str:
    start = docs.index('<article class="docs-main">')
    return docs[start : docs.index('<h2 id="states">')]


def test_the_reading_section_sits_before_the_state_map_and_is_linked(docs: str) -> None:
    assert "<h1>Read a proof page</h1>" in docs  # F34-T6: its own page, the state map after it
    assert docs.index("<h1>Read a proof page</h1>") < docs.index('<h2 id="states">')
    section = reading(docs)
    for words in ("routine", "hole", "read back", "machine-drafted by", "read against"):
        assert words in section, words
    # F21-T8 (R14, D-3 v3.31): the section states and pending edits, in the renderer's own words.
    for words in (
        "drafted with",
        "written by",
        "read against the Lean by",
        "awaiting review",
        "a diff",
    ):
        assert words in section, words
    assert "<script" not in section and 'href="http' not in section


def test_every_provenance_label_has_a_row(docs: str) -> None:
    """F19-R11's labels, each with its meaning: the table is the renderer's dictionary."""
    keys = [key for key, _ in render.READING_LABELS]
    assert len(keys) == len(set(keys)) and set(keys) == set(render.PROVENANCE)
    table = reading(docs).split('<table class="reading-labels">', 1)[1].split("</table>", 1)[0]
    labels = re.findall(r"<tr><td>([^<]+)</td>", table)
    assert labels == [render.esc(render.PROVENANCE[key]) for key, _ in render.READING_LABELS]


def test_the_gloss_guide_link_lands_on_the_guides_section(docs: str) -> None:
    """F20-Q16(a), as F34-T6 carries it: the guide's section on the words is a heading the
    tested guide has, and the site's link for writing words lands on the short page that sends a
    reader to it in AGENTS.md, which is served whole and no longer copied into Docs."""
    headings = re.findall(r"^## (.+)$", GUIDE.read_text(encoding="utf-8"), re.M)
    assert any(h.split(" (", 1)[0] == render.GLOSS_GUIDE_SECTION for h in headings), headings
    assert render.GLOSS_GUIDE_HREF == "/docs/words/"
    assert f'<a href="{render.GLOSS_GUIDE_HREF}">' in reading(docs)
    assert render.GLOSS_GUIDE_SECTION in render._template("docs-words.html").template
    assert "## Glosses" not in docs and 'id="guide-' not in docs  # nothing of the guide copied
    ids = re.findall(r'id="([^"]+)"', docs)
    assert len(ids) == len(set(ids)), sorted(i for i in ids if ids.count(i) > 1)


def test_the_actions_table_names_the_word_actions(docs: str) -> None:
    table = docs.split('<table class="actions">', 1)[1].split("</table>", 1)[0]
    for needle in (
        "Say a file in words",
        "<code>POST /glosses</code>",
        "Revise a gloss or an explainer",
        "<code>opn-gate gloss revise</code>",
        "Withdraw a version",
        "<code>POST /glosses/withdrawals</code>",
        # F21-T8: write, revise, approve as F21 has them (D-3 v3.31)
        "<code>list_words_needed</code>",
        "one writer per file",
        "Approve words",
        "<code>opn-gate gloss sign --sections</code>",
        "awaiting review",
    ):
        assert needle in table, needle
    assert "a signed version only a steward or curator" not in table  # F20-R6, withdrawn (R13)


def test_heading_anchors_are_opt_in_slugged_and_unique() -> None:
    text = (
        "# Title\n## Glosses, explainers and outlines (D-3 v3.30)\n## Again!\n## Again?\n### Sub\n"
    )
    assert 'id="' not in prose.render_document(text)
    html = prose.render_document(text, anchors="guide-")
    assert '<h2 id="guide-glosses-explainers-and-outlines">' in html
    assert html.count('id="guide-again"') == 1  # the first of two that would share an id
    assert "<h2>Again?</h2>" in html
    assert "<h1>Title</h1>" in html and "<h3>Sub</h3>" in html  # sections only
    assert prose.heading_slug("Precheck and submit") == "precheck-and-submit"
    assert prose.heading_slug("<script> (x)") == "script"
