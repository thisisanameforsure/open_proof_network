"""F04-T3: escaping (R3, R4; AC2, AC3) and the prose renderer (Q2)."""

from __future__ import annotations

import re
from pathlib import Path

import fixture
import pytest
import yaml

from opn_gate import products, schemas
from opn_site import model, prose, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("esc"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_prose_is_escaped(rendered: dict[str, str]) -> None:
    """AC2: the explainer's <script> and the annex's <img onerror> survive only as text."""
    explainer_page = rendered["nodes/propositional/tutorial-and-swap/index.html"]
    annex_page = rendered["nodes/propositional/and-swap-reassoc/index.html"]
    for page in (explainer_page, annex_page):
        assert "<script>" not in page and "<img" not in page
        assert re.search(r"<script\b(?! src=\"/frontier\.js\")", page) is None
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in explainer_page
    assert "&lt;img src=x onerror=alert(1)&gt;" in annex_page
    assert "&lt;b&gt;tags&lt;/b&gt;" in annex_page and " &amp; " in annex_page
    # ...and inside the labelled block, below the file link, with author and model.
    block = explainer_page[explainer_page.index('<div class="prose-block unverified">') :]
    assert block.index("Rendered from") < block.index("&lt;script&gt;")
    assert 'class="prose-block untrusted"' in annex_page
    assert "Untrusted: annex (D-31), author not recorded" in annex_page


def test_lean_is_escaped(tmp_path: Path) -> None:
    """AC3: a statement with < and & renders escaped and intact."""
    root = fixture.build(tmp_path)
    node = root / "targets" / "propositional" / "nodes" / "and-reassoc"
    statement = (
        "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n  sorry\n"
    )
    statement = statement.replace("(p ∧ q) ∧ r", "(p ∧ q) ∧ r -- a < b && c")
    (node / "Statement.lean").write_text(statement, encoding="utf-8")
    (node / "Proof.lean").unlink()
    meta = yaml.safe_load((node / "META.yaml").read_text())
    meta["statement-hash"] = schemas.content_hash(statement.encode("utf-8"))
    (node / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    page = files["nodes/propositional/and-reassoc/index.html"]
    assert "-- a &lt; b &amp;&amp; c" in page
    assert "a < b && c" not in page
    assert "∀ p q r : Prop" in page  # unicode is left alone


def test_prose_renderer() -> None:
    """Q2: paragraphs and fences only; everything else is literal, escaped text."""
    text = "First line\nsame paragraph.\n\nSecond <b>para</b>\n\n"
    text += "```\nx < 1 & y\n```\n# not a heading\n"
    out = prose.render(text)
    assert out == (
        "<p>First line same paragraph.</p>\n"
        "<p>Second &lt;b&gt;para&lt;/b&gt;</p>\n"
        "<pre><code>x &lt; 1 &amp; y</code></pre>\n"
        "<p># not a heading</p>"
    )
    assert prose.render("") == ""
    assert prose.render("```\nunclosed") == "<pre><code>unclosed</code></pre>"


def test_every_graph_string_passes_through_esc() -> None:
    """R3: the escaping function quotes everything HTML could interpret."""
    assert render.esc('<a href="x">&\'') == "&lt;a href=&quot;x&quot;&gt;&amp;&#x27;"
