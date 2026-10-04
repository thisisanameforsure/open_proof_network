"""F19-T6 (R12; AC9): TeX in explainer and annex prose.

An explainer is prose about mathematics, and until now the site printed its TeX as dollar signs.
``prose.render`` gains an escaped math path: everything is escaped first, then text between
``$…$`` or ``$$…$$`` — outside code spans and fences only — is wrapped in the one element class
the vendored KaTeX renderer may touch (``.math``, F04-T13), with trust off. A fence, an inline code
span, Lean and file names are never wrapped, so a dollar sign in them stays text.

MathML is produced in the browser by KaTeX, not by the generator, so the generator's half is the
renderer's configuration asking for it (``output: "htmlAndMathml"``); the rendered ``<math>``
element is measured in the browser by ``engineering/evidence/F19/shoot.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import fixture
import pytest
from harness import TARGET

from opn_gate import products
from opn_site import model, prose, render

REPO = "https://github.com/example/graph"
PROSE = (
    "The ratio $\\frac{a}{b}$ is what the lemma bounds.\n\n"
    "```\nexample : $x$ = 1 := rfl\n```\n\n"
    "Run `echo $HOME` first, then <script>alert(1)</script>.\n"
)


def math_spans(html: str) -> list[str]:
    return re.findall(r'<span class="math">(.*?)</span>', html, re.S)


def test_only_the_math_outside_code_is_marked() -> None:
    html = prose.render(PROSE, math=True)
    assert math_spans(html) == ["$\\frac{a}{b}$"]
    # The fence keeps its dollars as escaped text, outside any .math element.
    assert "<pre><code>example : $x$ = 1 := rfl</code></pre>" in html
    # The inline code span keeps its dollar as text, outside any .math element.
    assert "<code>echo $HOME</code>" in html
    assert "<script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_display_math_is_marked_whole() -> None:
    html = prose.render("So $$\\sum_{i<n} i = \\binom{n}{2}$$ holds.", math=True)
    assert math_spans(html) == ["$$\\sum_{i&lt;n} i = \\binom{n}{2}$$"]


def test_currency_is_not_math() -> None:
    """Pandoc's rule: a closing dollar has a non-space before it and no digit after it."""
    html = prose.render("Costs $5 and $6, or ${more}; but $n$ is.", math=True)
    assert math_spans(html) == ["$n$"]


def test_markup_inside_math_is_escaped_before_it_is_marked() -> None:
    html = prose.render('$<img src=x onerror="alert(1)">$', math=True)
    assert math_spans(html) == ["$&lt;img src=x onerror=&quot;alert(1)&quot;&gt;$"]
    assert "<img" not in html


def test_without_the_math_path_prose_renders_as_before() -> None:
    """Every other caller of ``prose.render`` (acknowledgments, notes) is unchanged."""
    html = prose.render(PROSE)
    assert 'class="math"' not in html and "$\\frac{a}{b}$" in html


def test_the_renderer_asks_katex_for_mathml_with_trust_off() -> None:
    script = (render.STATIC / "math.js").read_text(encoding="utf-8")
    assert 'output: "htmlAndMathml"' in script
    assert "trust: false" in script
    assert 'querySelectorAll(".math")' in script


# --- on the page: the explainer and the annex -----------------------------------------------


@pytest.fixture(scope="module")
def node_page(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = fixture.curated(tmp_path_factory.mktemp("prose-math"))
    nodes = root / "targets" / TARGET / "nodes"
    (nodes / "tutorial-and-swap" / "explainer" / "why.md").write_text(
        "---\nauthor: alice\n---\n" + PROSE, encoding="utf-8"
    )
    (nodes / "tutorial-and-swap" / "annex" / "sketch.md").write_text(
        "An annex with $p \\land q$ in it.\n", encoding="utf-8"
    )
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    pages = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    return pages[f"nodes/{TARGET}/tutorial-and-swap/index.html"]


def block(page: str, label: str) -> str:
    m = re.search(rf'<div class="prose-block {label}"[^>]*>.*?</div></div>', page, re.S)
    assert m is not None, label
    return m.group(0)


def test_explainer_and_annex_prose_carry_math_and_load_katex(node_page: str) -> None:
    assert math_spans(block(node_page, "unverified")) == ["$\\frac{a}{b}$"]
    assert math_spans(block(node_page, "untrusted")) == ["$p \\land q$"]
    assert render.MATH_HEAD in node_page and render.MATH_SCRIPTS in node_page


def test_lean_and_file_names_are_never_marked(node_page: str) -> None:
    for pre in re.findall(r'<pre class="lean[^"]*">.*?</pre>', node_page, re.S):
        assert 'class="math"' not in pre
    for link in re.findall(r'<a class="file"[^>]*>.*?</a>', node_page, re.S):
        assert 'class="math"' not in link


def test_a_page_with_no_math_loads_no_katex(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    pages = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    page = pages[f"nodes/{TARGET}/and-reassoc/index.html"]
    assert "katex" not in page
