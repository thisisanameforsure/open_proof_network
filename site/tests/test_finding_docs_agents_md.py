"""Finding site-docs-agents-md (2026-09-13, the Euclid tester): the docs page shows AGENTS.md
as a wall of text.

The graph's ``AGENTS.md`` is the contributor guide, written in headings, fenced ``sh`` and
``output`` blocks, and pipe tables. The docs page renders it through ``prose.render`` — the
paragraphs-and-fences renderer meant for contributor prose — so every ``##`` heading is a
paragraph, the MCP appendix table is a run of pipes, and the ``output`` fences show no label
saying their lines are fragments to look for rather than a transcript.

Mike's decision (2026-09-14, plan F04-T10): ``docs()`` renders AGENTS.md through
``prose.render_document``, which gains fence info strings (``output`` labelled "expected output
(fragments)") and pipe tables. Strict xfail until F04-T10 lands (conventions §2).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import fixture

from opn_site import model, prose, render

REPO = "https://github.com/example/graph"
GUIDE = Path(__file__).resolve().parents[2] / "gate" / "agents" / "AGENTS.md"


def test_agents_md_renders_as_a_document(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    shutil.copyfile(GUIDE, root / "AGENTS.md")
    docs = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)[
        "docs/index.html"
    ]
    assert "Claiming a node (D-25)" in docs, "guard: the guide is on the page"

    assert re.search(r"<h2[^>]*>Claiming a node \(D-25\)</h2>", docs), "no <h2> for the section"
    assert "expected output (fragments)" in docs, "output fences carry no label"
    tables = re.findall(r"<table[^>]*>.*?</table>", docs, re.S)
    assert any("server_info" in t for t in tables), "the MCP appendix is not a table"
    assert "```" not in docs, "a literal fence reached the page"
    assert '<pre class="fence-sh"><code>' in docs, "sh fences carry no class"
    assert "Untrusted: AGENTS.md" in docs, "the guide left its labelled block (F04-R4)"


# --- the document renderer's new shapes, edge cases first (F04-T10 part 2) ----------------------


def test_output_fence_is_labelled_exactly_and_sh_fence_gets_a_class() -> None:
    html = prose.render_document("```sh manual\nls <x>\n```\n\n```output\nok\n```\n")
    assert html == (
        '<pre class="fence-sh"><code>ls &lt;x&gt;</code></pre>\n'
        '<p class="fence-label">expected output (fragments)</p>'
        '<pre class="fence-output"><code>ok</code></pre>'
    )


def test_an_info_string_that_is_not_a_plain_word_gives_no_class() -> None:
    html = prose.render_document('```"><script>\ncode\n```\n')
    assert html == "<pre><code>code</code></pre>"


def test_a_pipe_inside_backticks_stays_in_its_cell() -> None:
    html = prose.render_document("| Flag | Means |\n|---|---|\n| `a|b` | either \\| or |\n")
    assert "<th>Flag</th><th>Means</th>" in html
    assert "<td><code>a|b</code></td><td>either | or</td>" in html
    assert html.count("<td>") == 2


def test_a_short_row_is_padded_and_a_pipe_line_without_a_rule_is_a_paragraph() -> None:
    html = prose.render_document("| a | b |\n|---|---|\n| only |\n\n| not | a table |\n")
    assert "<tr><td>only</td><td></td></tr>" in html
    assert "<p>| not | a table |</p>" in html


def test_an_unclosed_fence_keeps_its_info_and_its_text() -> None:
    html = prose.render_document("intro\n\n```output\n## not a heading\n| a | b |\n|---|---|\n")
    assert html == (
        "<p>intro</p>\n"
        '<p class="fence-label">expected output (fragments)</p>'
        '<pre class="fence-output"><code>## not a heading\n| a | b |\n|---|---|</code></pre>'
    )


def test_a_heading_inside_a_fence_is_not_a_heading() -> None:
    html = prose.render_document("```sh\n## Claiming a node (D-25)\necho '```json'\n```\n## Real\n")
    assert "<h2>Claiming a node (D-25)</h2>" not in html
    assert "## Claiming a node (D-25)" in html
    assert "echo &#x27;&#96;&#96;&#96;json&#x27;" in html  # a quoted fence is text, not a fence
    assert html.endswith("<h2>Real</h2>")
