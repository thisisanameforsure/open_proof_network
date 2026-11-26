"""F34-T2 (R4): a record's informal text never reaches a page as raw TeX or Markdown markers.

The 2026-11-24 review found ``*abc* conjecture`` in abc's heading, erdos-257's sentence under its
statement printing ``$A\\subseteq\\mathbb{N}$``, and singmaster's hole claims printing their TeX. A
scan of the live graph rendered by F34-T1 (``engineering/evidence/F34/task-2.txt``) found the same
in 128 problem pages' provenance lines, the review page's lead, annex titles and statement labels.
Each place now renders the record's inline forms: TeX inside a ``.math`` element for the same-origin
renderer, ``*emphasis*`` as ``<em>``; a drawing's SVG text, which can carry no markup, shows the
words without their markers.
"""

from __future__ import annotations

import re
import shutil
from html.parser import HTMLParser

import fixture
import pytest
import yaml

from opn_gate import products
from opn_site import model, prose, render

REPO = "https://github.com/example/graph"
TARGET = "inline-text"
ROOT = "inline-text-root"
TITLE = "*abc* conjecture: for every $\\varepsilon > 0$, only finitely many triples"

#: Raw TeX or a Markdown emphasis marker in visible text.
RAW = re.compile(r"\$[^$\s][^$]*\$|\\[A-Za-z]+|(?<![\w*])\*[A-Za-z][^*\n]{0,40}\*(?![\w*])")
SKIP = {"code", "pre", "script", "style", "textarea"}


class _Visible(HTMLParser):
    """Text runs a reader sees as text: outside ``.math`` (rendered by KaTeX) and code."""

    VOID = frozenset({"br", "img", "input", "meta", "link", "hr", "wbr", "path", "circle", "rect"})

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[bool] = []
        self.runs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.VOID:
            return
        cls = (dict(attrs).get("class") or "").split()
        self.stack.append("math" in cls or tag in SKIP)

    def handle_endtag(self, tag: str) -> None:
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if not any(self.stack) and data.strip():
            self.runs.append(data)


def raw_runs(html: str) -> list[str]:
    p = _Visible()
    p.feed(html)
    return [r.strip() for r in p.runs if RAW.search(r)]


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    from harness import take_in  # noqa: PLC0415

    tmp = tmp_path_factory.mktemp("f34-inline")
    root = fixture.build(tmp)
    staged = tmp / ROOT
    shutil.copytree(fixture.nodes_dir(root) / "and-reassoc", staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text())
    meta["id"] = ROOT
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (staged / "Proof.lean").unlink(missing_ok=True)
    take_in(
        root,
        target_id=TARGET,
        root_dir=staged,
        title=TITLE,
        track="open",
        informal=None,  # the source states no licence, so the paraphrase stands in (F11-R10)
        paraphrase="For every $\\varepsilon > 0$ there are finitely many triples.",
        sources=[fixture.UNLICENSED],
        qa_summary=fixture.QA_SUMMARY,
        domains=["number-theory"],
    )
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_the_problem_page_shows_no_raw_tex_or_markers(pages: dict[str, str]) -> None:
    page = pages[f"problems/{TARGET}/index.html"]
    assert raw_runs(page) == []
    assert "<em>abc</em> conjecture" in page


def test_the_provenance_sentence_carries_its_tex_to_the_renderer(pages: dict[str, str]) -> None:
    page = pages[f"problems/{TARGET}/index.html"]
    line = page[page.index('class="provenance-line"') :]
    line = line[: line.index("</p>")]
    assert '<span class="math">' in line and "\\varepsilon" in line


def test_a_drawing_label_drops_the_markers(pages: dict[str, str]) -> None:
    """SVG text can carry no markup: the label reads ``abc conjecture``."""
    page = pages[f"problems/{TARGET}/index.html"]
    svg_text = re.findall(r"<text[^>]*>([^<]*)</text>|<title>([^<]*)</title>", page)
    shown = [a or b for a, b in svg_text]
    assert any("abc conjecture" in s for s in shown), shown[:10]
    assert not any("*abc*" in s for s in shown)


def test_every_page_of_the_target_is_clean(pages: dict[str, str]) -> None:
    dirty = {
        rel: raw_runs(html)
        for rel, html in pages.items()
        if rel.endswith(".html") and f"/{TARGET}/" in f"/{rel}" and raw_runs(html)
    }
    assert dirty == {}


def test_a_display_block_that_holds_inline_math_is_read_as_a_line() -> None:
    """Singmaster's hole: the post-merge job wrote ``$$<claim>$$`` around a claim that already
    mixed words and ``$…$``; KaTeX cannot parse the whole, so the line is rendered as words with
    its inline math instead (the record is immutable, F34-Q17)."""
    text = "$$\\{(n,k) : 1 \\le k < n\\}$ is finite for every $t$$"
    html = prose.render(text, math=True)
    assert "$$" not in html
    assert '<span class="math">$\\{(n,k) : 1 \\le k &lt; n\\}$</span>' in html
    assert "is finite for every" in html
    assert '<span class="math">$t$</span>' in html


def test_two_display_blocks_with_inline_math_between_are_unchanged() -> None:
    """The repair reads a whole paragraph only: the ``$$`` closing one block and the ``$$`` opening
    the next never pair up (erdos-1050's reading view, found by the live scan)."""
    text = "So $$a = b$$ holds, and with $x$ fixed, $$c = d$$ too."
    html = prose.render(text, math=True)
    assert '<span class="math">$$a = b$$</span>' in html
    assert '<span class="math">$$c = d$$</span>' in html
    assert '<span class="math">$x$</span>' in html


def test_a_well_formed_display_block_is_unchanged() -> None:
    text = "$$\\forall n,\\ n + 0 = n$$"
    assert (
        prose.render(text, math=True)
        == '<p><span class="math">$$\\forall n,\\ n + 0 = n$$</span></p>'
    )


@pytest.mark.parametrize(
    ("words", "shown"),
    [
        ("Is $\\sum_n p_n/2^n$ irrational?", '<span class="math">'),
        ("Numerical check: no exception with $n\\ge k^3$", '<span class="math">'),
    ],
)
def test_review_words_and_annex_titles_render_their_math(words: str, shown: str) -> None:
    html = render.record_words(words)
    assert shown in html and raw_runs(html) == []
