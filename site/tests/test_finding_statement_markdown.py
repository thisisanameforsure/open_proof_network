"""F04-T19: the inline Markdown a record's informal statement carries is rendered (Q21).

Seen by an outside contributor on Home and Problems, 2026-09-18: ``**Erdős Problem 1050.**``,
backticked Lean names, ``*Richard K. Guy*`` and ``[Unsolved Problems…](https://doi…)`` shown as
typed. T13 rendered the TeX in the same text and left the Markdown as "the record's text and a
separate call" (Q15). Four live records carry it, copied from the registry's docstrings.

The renderer is ``prose.inline_statement``: escape first, then four inline forms and nothing
else. Math between dollar signs is set aside before any of it, so an asterisk or underscore in a
formula is never emphasis; a link is a link only when a validated record already cites its url
(the link checker's own allowlist, R13), and is its text otherwise.
"""

from __future__ import annotations

import dataclasses

import fixture
import pytest

from opn_site import model, prose, render

REPO = "https://github.com/example/graph"
CITED = frozenset({"https://doi.org/10.1007/978-0-387-26677-0"})


def out(text: str, allowed: frozenset[str] = CITED) -> str:
    return prose.inline_statement(text, allowed_urls=allowed)


def test_strong_code_and_emphasis() -> None:
    assert out("**Erdős Problem 1050.** The series") == (
        "<strong>Erdős Problem 1050.</strong> The series"
    )
    assert out("as a `tsum` over `Nat`") == "as a <code>tsum</code> over <code>Nat</code>"
    assert out("by *Richard K. Guy*.") == "by <em>Richard K. Guy</em>."


def test_a_cited_link_is_a_link_and_any_other_is_its_text() -> None:
    cited = "[Unsolved Problems](https://doi.org/10.1007/978-0-387-26677-0)"
    assert out(cited) == (
        '<a href="https://doi.org/10.1007/978-0-387-26677-0">Unsolved Problems</a>'
    )
    assert out("[Clay](https://www.claymath.org/riemann.pdf)") == "Clay"
    assert out("[x](javascript:alert(1))") == "[x](javascript:alert(1))"  # not a link form at all


@pytest.mark.parametrize(
    "formula",
    [
        "$a*b*c$",
        "$\\sum_{n=1}^\\infty \\frac{1}{2^n - 3}$",
        "$$\\prod_{1\\leq i\\leq k_1} (n_1 + i)\\ \\text{and}\\ \\prod_{j} (n_2 *j*)$$",
        "$x_1$ and $x_2$",
    ],
)
def test_math_is_never_markup(formula: str) -> None:
    assert out(f"Is {formula} true?") == f"Is {render.esc(formula)} true?"


def test_code_is_never_markup_or_math() -> None:
    lean = "`∀ (s : Complex), a * b * c = 0 → s.re = 1 / 2`"
    assert out(lean) == "<code>∀ (s : Complex), a * b * c = 0 → s.re = 1 / 2</code>"
    assert out("`cost $5 and $6`") == "<code>cost $5 and $6</code>"


def test_everything_is_escaped_first() -> None:
    hostile = "**<script>alert(1)</script>** `<img src=x>` *<b>x</b>* [<i>t</i>](https://e.x/)"
    html = out(hostile, frozenset({"https://e.x/"}))
    assert "<script>" not in html and "<img" not in html and "<b>" not in html and "<i>" not in html
    assert html.count("&lt;") == 7  # script and b and i open and close, img once
    assert out('[t](https://e.x/"onmouseover="x)', frozenset({'https://e.x/"onmouseover="x'})) == (
        '<a href="https://e.x/&quot;onmouseover=&quot;x">t</a>'
    )


def test_a_lone_asterisk_or_dollar_is_text() -> None:
    assert out("2 * 3 = 6, and n* is fine") == "2 * 3 = 6, and n* is fine"
    assert out("costs $5") == "costs $5"
    assert out("a ** b") == "a ** b"


def test_plain_text_is_exactly_the_escaped_text() -> None:
    """The T13 contract the vendor test pins: no Markdown, no difference."""
    assert out(fixture.PARAPHRASE) == render.esc(fixture.PARAPHRASE)


def test_the_pages_render_a_records_markdown(tmp_path_factory: pytest.TempPathFactory) -> None:
    root = fixture.build_with_listed_target(tmp_path_factory.mktemp("md"))
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[fixture.LISTED_TARGET]
    assert tv.record is not None
    url = str(tv.record["sources"][0]["url"])
    text = f"**Problem.** Is `tsum` of $a*b$ bounded? See [the source]({url}) and [other](https://no.example/)."
    marked = dataclasses.replace(tv, record={**tv.record, "informal": text})
    r = render.Renderer(site, repo_url=REPO)
    for html in (r.informal_words(marked), r.informal_line(marked)):
        assert html.startswith('<span class="math">') and html.count('class="math"') == 1
        assert "<strong>Problem.</strong>" in html and "<code>tsum</code>" in html
        assert "$a*b$" in html
        assert f'<a href="{render.esc(url)}">the source</a>' in html
        assert "no.example" not in html and "other" in html
