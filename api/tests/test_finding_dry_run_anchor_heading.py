"""F22-T30 (2026-11-19 run, B17c): a dry run's ``preview_html`` shows an explainer the way the site
shows it.

``preview_html`` rendered the whole text as one prose document, so a heading's step anchor
(``## The bound {steps: s1}``) appeared literally in the heading. The site shows an explainer
section by section, each heading with its steps named after it as ``(s1)`` and no braces
(``Renderer.version_words``). The preview is now that rendering: a gloss is unchanged.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import Harness
from test_explainer_schema import step
from test_glosses_route import (
    explainer_body,
    make_h,
    make_keys,
    make_tree,
    post,
    proof_hash,
    serve,
    statement_gloss,
    write_outline,
)

from opn_gate import explainers
from opn_site import prose
from opn_site.model import VersionView
from opn_site.render import Renderer

ANCHORED = (
    "## The idea\nRegroup, *then* read.\n\n"
    "## The bound $p$ {steps: s1 s2}\nBy `Nat.Prime.two_le`, $2 \\le p$.\n"
)


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def site_words(text: str) -> str:
    """What the site's node page prints for these words as one explainer version."""
    view = VersionView(
        hash="0" * 64,
        path="x.md",
        schema="explainer/v2",
        supersedes=None,
        author="bob",
        drafter=None,
        date="2026-11-19",
        withdrawn=False,
        describes_current=None,
        signers=(),
        body=text,
        sections=tuple(explainers.sections(text)),
    )
    return Renderer.version_words(view)


def test_the_anchor_is_not_printed_in_the_heading(h: Harness, tree: Path) -> None:
    write_outline(tree, [step("s1"), step("s2")])
    serve(h, tree)
    body = explainer_body(proof_hash(tree), ANCHORED) | {"dry_run": True}
    r = post(h, h.token_for("code_bob", "bob"), body)
    assert r.status_code == 200, r.text
    html = r.json()["preview_html"]
    assert "{steps" not in html
    assert '<span class="po-id">(s1 s2)</span>' in html
    assert html == site_words(ANCHORED)


def test_a_gloss_preview_is_unchanged(h: Harness) -> None:
    gloss = statement_gloss()
    r = post(h, h.token_for("code_bob", "bob"), gloss | {"dry_run": True})
    assert r.status_code == 200, r.text
    assert r.json()["preview_html"] == prose.render(gloss["text"], math=True)
