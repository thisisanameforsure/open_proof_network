"""F22-T15 (ruling 2): contributor words render their Markdown, and math renders inside it.

Seen by the 2026-10-06 testers (bugs.md P2-2) on erdos-1050: a gloss's ``- item`` lines came out as
one ``<p>- … - …</p>`` and ``**`` stood on the page 102 times, so writers re-filed versions to work
around the renderer. A record's informal statement had the opposite half of the defect: its
``**$x$ is prime**`` could not pair, because math was set aside before emphasis was read.

One inline renderer serves all three callers now (``prose.render`` with math for glosses,
explainers and annexes; ``prose.render_document`` for the docs, which gain math;
``prose.inline_statement``). Code spans are held first, then math, then emphasis is read over the
rest, so an emphasis pair may span a math segment and nothing inside code or math is ever read as
emphasis. Every character is escaped before any tag is written (F04-R3); links stay text (F04-R13).
"""

from __future__ import annotations

import re

from opn_site import prose, render


def words(text: str) -> str:
    return prose.render(text, math=True)


def math_spans(html: str) -> list[str]:
    return re.findall(r'<span class="math">(.*?)</span>', html, re.S)


# --- lists ------------------------------------------------------------------------------------


def test_a_bullet_list_is_a_list() -> None:
    html = words("The terms:\n- $W(n)$ first;\n- then $A_k$.\n\nAfter.")
    assert html == (
        "<p>The terms:</p>\n"
        '<ul><li><span class="math">$W(n)$</span> first;</li>'
        '<li>then <span class="math">$A_k$</span>.</li></ul>\n'
        "<p>After.</p>"
    )


def test_star_and_numbered_lists() -> None:
    assert words("* a\n* b") == "<ul><li>a</li><li>b</li></ul>"
    assert words("1. one\n2. two") == "<ol><li>one</li><li>two</li></ol>"


def test_lists_nest_by_indentation() -> None:
    html = words("1. outer\n   - inner one\n   - inner two\n2. next")
    assert html == (
        "<ol><li>outer<ul><li>inner one</li><li>inner two</li></ul></li><li>next</li></ol>"
    )


def test_an_indented_line_continues_an_item_and_an_unindented_one_ends_the_list() -> None:
    assert words("- one\n  more\n- two\nafter") == (
        "<ul><li>one more</li><li>two</li></ul>\n<p>after</p>"
    )


def test_a_blank_line_between_items_keeps_one_list() -> None:
    assert words("- a\n\n- b") == "<ul><li>a</li><li>b</li></ul>"


def test_a_dash_inside_math_is_not_a_list() -> None:
    html = words("The sum $$\n- \\sum_k a_k\n$$ is negative.")
    assert "<ul>" not in html and "<li>" not in html
    assert math_spans(html) == ["$$ - \\sum_k a_k $$"]


def test_display_math_on_its_own_lines_inside_a_list_item() -> None:
    html = words("- the bound\n  $$\n  - x \\le y\n  $$\n- next")
    assert html == (
        '<ul><li>the bound <span class="math">$$ - x \\le y $$</span></li><li>next</li></ul>'
    )


# --- emphasis, code and math together ---------------------------------------------------------


def test_bold_italic_and_code() -> None:
    assert words("**Base case.** Use *induction* on `n`.") == (
        "<p><strong>Base case.</strong> Use <em>induction</em> on <code>n</code>.</p>"
    )


def test_math_inside_a_list_item_and_inside_bold() -> None:
    html = words("1. **Integrality of $d_n Q$.** It holds.\n2. *for $n \\ge 1$* too")
    assert html == (
        '<ol><li><strong>Integrality of <span class="math">$d_n Q$</span>.</strong> It holds.</li>'
        '<li><em>for <span class="math">$n \\ge 1$</span></em> too</li></ol>'
    )


def test_stars_inside_math_or_code_are_never_emphasis() -> None:
    html = words("Here $a*b*c$ and `x * y * z` and **real**.")
    assert html == (
        '<p>Here <span class="math">$a*b*c$</span> and <code>x * y * z</code> and '
        "<strong>real</strong>.</p>"
    )


def test_a_link_is_its_text_and_its_url_as_text() -> None:
    html = words("See [the paper](https://example.org/p?a=1&b=2).")
    assert html == "<p>See the paper (https://example.org/p?a=1&amp;b=2).</p>"
    assert "<a " not in html


def test_headings_in_words_sit_below_the_page_headings() -> None:
    html = words("# hden\n\n## Candidate d for h3\n\nText.")
    assert html == "<h4>hden</h4>\n<h5>Candidate d for h3</h5>\n<p>Text.</p>"


# --- escaping, before every tag ---------------------------------------------------------------


def test_hostile_markup_in_every_form_stays_text() -> None:
    hostile = (
        "- **<script>alert(1)</script>**\n"
        "- *<img src=x onerror=alert(1)>*\n"
        "  - `<b>` and $<i>$\n"
        '- [<a href="javascript:x">y</a>](https://e.x/"onmouseover="z)\n'
        "# <h1>t</h1>\n"
    )
    html = words(hostile)
    for tag in ("<script", "<img", "<b>", "<i>", "<a ", "<h1>"):
        assert tag not in html, tag
    assert "&lt;script&gt;" in html and "&quot;onmouseover=&quot;" in html


def test_a_nul_in_the_words_cannot_forge_a_placeholder() -> None:
    html = words("`<b>` then \x000\x00 and **x**")
    assert "<b>" not in html and "\x00" not in html


# --- the other two callers ----------------------------------------------------------------------


def test_emphasis_spans_math_in_an_informal_statement() -> None:
    html = prose.inline_statement("**$p$ is prime** and *$q$ odd*", allowed_urls=frozenset())
    assert html == "<strong>$p$ is prime</strong> and <em>$q$ odd</em>"


def test_the_docs_carry_math_and_nested_lists() -> None:
    html = prose.render_document("For $n \\ge 1$:\n\n- a\n  - b `$HOME`\n")
    assert math_spans(html) == ["$n \\ge 1$"]
    assert "<ul><li>a<ul><li>b <code>$HOME</code></li></ul></li></ul>" in html


def test_every_math_span_is_one_math_js_processes() -> None:
    """math.js renders inside every ``.math`` element; the renderer marks math with that class
    and no other, so a span it emits is one the script reaches."""
    script = (render.STATIC / "math.js").read_text(encoding="utf-8")
    assert 'querySelectorAll(".math")' in script
    html = words("- $a$\n\n**$b$**\n\n# $c$")
    assert len(math_spans(html)) == 3
    assert "math" not in re.sub(r'<span class="math">', "", html).replace("$", "")
