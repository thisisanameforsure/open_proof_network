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
        "docs/index.html"
    ]


def reading(docs: str) -> str:
    start = docs.index('<h2 id="reading">')
    return docs[start : docs.index('<h2 id="states">')]


def test_the_reading_section_sits_before_the_state_map_and_is_linked(docs: str) -> None:
    assert '<a href="#reading">' in docs
    assert docs.index('<h2 id="reading">') < docs.index('<h2 id="states">')
    section = reading(docs)
    for words in ("routine", "hole", "read back", "machine-drafted by", "read against"):
        assert words in section, words
    # F21-T8 (R14, D-3 v3.31): the section states and pending edits, in the renderer's own words.
    for words in ("drafted with", "written by", "verified by", "awaiting review", "a diff"):
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
    """F20-Q16(a): the constant names a heading the tested guide has, and the rendered guide on
    the Docs page carries that heading's id."""
    headings = re.findall(r"^## (.+)$", GUIDE.read_text(encoding="utf-8"), re.M)
    assert any(h.split(" (", 1)[0] == render.GLOSS_GUIDE_SECTION for h in headings), headings
    path, _, fragment = render.GLOSS_GUIDE_HREF.partition("#")
    assert path == "/docs/"
    assert fragment == "guide-glosses-explainers-and-outlines"
    assert re.search(rf'<h2 id="{fragment}">Glosses, explainers and outlines', docs)
    assert f'<a href="{render.GLOSS_GUIDE_HREF}">' in reading(docs)
    # Every section of the guide is linkable, under a prefix that keeps its ids apart from the
    # page's own (#agents, #states, #glossary, ...); an id appears once on the page.
    guide = docs[docs.index('<h2 id="agents">') + 1 : docs.index("<h2>For people</h2>")]
    sections = re.findall(r"<h2([^>]*)>", guide)
    assert len(sections) >= 10
    assert all(s.startswith(f' id="{render.GUIDE_ANCHOR_PREFIX}') for s in sections), sections
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
