"""Round four of failing-case coverage for the site: the last unexercised lines, one case each
(session note 2026-09-10-test-coverage-review.md for rounds one to three).

``cli.py:40`` is the ``__main__`` guard and is not tested.
"""

from __future__ import annotations

from pathlib import Path

import fixture

from opn_site import links, model, render

REPO = "https://github.com/example/graph"


def test_a_stray_close_of_a_void_tag_is_ignored_not_reported_as_unbalanced() -> None:
    """``</br>`` closes nothing because ``<br>`` opened nothing; the balance check skips void
    tags on both ends rather than reporting a close that has no open."""
    files = {"index.html": "<p>x<br></br><img src='/a.png'></img></p>", "a.png": ""}
    assert links.check(files, repo_url=REPO) == []


def test_a_node_without_a_prose_directory_has_no_prose(tmp_path: Path) -> None:
    """A missing ``explainer/`` or ``annex/`` directory is no prose, not an error — the gate's
    layout check already guarantees the directories exist on any node the site loads (so
    ``load_site`` never reaches this arm), and the guard is driven directly."""
    assert model._prose_files(tmp_path / "explainer", tmp_path) == ()


def test_docs_page_without_the_decisions_document_says_so_and_copies_nothing(
    tmp_path: Path,
) -> None:
    """R9, Q4: a build with no decisions document to copy renders the docs page with a plain
    notice and adds no ``docs/architecture-decisions.html`` or stylesheet."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    for decisions_doc in (None, tmp_path / "missing.html"):
        page, extra = render.Renderer(site, repo_url=REPO, decisions_doc=decisions_doc).docs()
        assert "not available in this build" in page
        assert "/docs/architecture-decisions.html" not in page
        # F10-T5: the human-funnel pages are still rendered; the copied doc and its css are not.
        assert extra and all(k.startswith("docs/") and k.endswith(".html") for k in extra)
        assert "docs/architecture-decisions.html" not in extra and "docs/decisions.css" not in extra
