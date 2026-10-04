"""F20-T8 (R14; AC12): explainer versions on the node page.

The tutorial's proof carries one explainer chain: a machine draft, a person's revision of it
(signed by a curator), and a third version that was withdrawn, so the revision is the current
version again (D-3 v3.30). The page shows the current version under D-36's fixed label with its
provenance line; each section that names outline steps sits beside those steps, linked to them in
the outline above; the history lists every version — the withdrawn one labelled withdrawn, never
hidden — each with a diff to its predecessor; and the page carries no form or input (D-36).
"""

from __future__ import annotations

import re
from html import escape

import gloss_fixture as gf
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
D36_LABEL = "unverified prose about a kernel-checked proof"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = gf.glossed_tree(tmp_path_factory.mktemp("explainers"))
    return render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO)


def explainer_section(page: str) -> str:
    start = page.index("<h2>Explainer</h2>")
    return page[start : page.index("<h2>Annex</h2>", start)]


def test_the_current_version_its_sections_history_and_no_form(pages: dict[str, str]) -> None:
    page = pages[f"nodes/{TARGET}/{gf.TUTORIAL}/index.html"]
    section = explainer_section(page)
    assert '<details class="history"' in section, "the explainer chain has no history"
    cut = section.index('<details class="history"')
    current, history = section[:cut], section[cut:]

    # The person's revision is current, under D-36's label, with its provenance and signature.
    assert "reorders them" in current
    assert "Split the hypothesis" not in current and "misread the hypothesis" not in current
    assert D36_LABEL in current and "written by alice" in current
    assert f"Explained and vouched for by <strong>{gf.CURATOR}</strong>" in current

    # Each anchored section sits beside the steps it names, linked into the outline above.
    sections = re.findall(
        r'<section class="ex-section" data-steps="([^"]*)">(.*?)</section>', current, re.S
    )
    assert [s for s, _ in sections] == ["", "hq", "hp s3"]
    for steps, body in sections[1:]:
        for sid in steps.split():
            link = re.search(rf'href="#(po-[0-9a-f]{{12}}-{re.escape(sid)})"', body)
            assert link is not None, sid
            assert f'id="{link.group(1)}"' in page  # the step it links is on this page
    assert "Getting q" in sections[1][1] and escape("`h.2`") not in sections[1][1]

    # History: all three versions in chain order, the draft machine-drafted, the revision signed,
    # the third labelled withdrawn; each after the first with a diff to its predecessor.
    items = re.findall(r'<li class="version"[^>]*>(.*?)</li>\s*(?=<li class="version"|</ol>)',
                       history, re.S)  # fmt: skip
    assert len(items) == 3
    assert f"machine-drafted by {gf.DRAFTER['model']}" in items[0]
    assert "written by alice" in items[1] and f"signed by {gf.CURATOR}" in items[1]
    assert "withdrawn" in items[2] and "written by " + gf.CURATOR in items[2]
    for item in items[1:]:
        anchor = re.search(r'href="#(diff-[0-9a-f]{12})"', item)
        assert anchor is not None
        diff = re.search(
            rf'<details class="diff" id="{anchor.group(1)}">.*?<pre class="diff">(.*?)</pre>',
            history,
            re.S,
        )
        assert diff is not None
        assert 'class="diff-del"' in diff.group(1) and 'class="diff-add"' in diff.group(1)
    assert "Split the hypothesis" in history and "misread the hypothesis" in history

    # The way to improve the words, and nothing that accepts input (D-36). The frame's one
    # checkbox is the phone menu's CSS toggle, outside <main>; the page's own content has none.
    assert "Improve these words" in section
    for p in (page, *(v for k, v in pages.items() if "/proofs/" in k)):
        main = p[p.index("<main>") : p.index("</main>")]
        assert not re.search(r"<(form|input|textarea|select|button)\b", main)
        assert "<form" not in p
