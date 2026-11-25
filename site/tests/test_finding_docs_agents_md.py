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


def test_agents_md_is_served_whole_and_copied_into_no_page(tmp_path: Path) -> None:
    """F34-T6 (F34-Q6): F04-T10 rendered the guide as a document inside Docs; the handoff serves it
    whole instead (73,700px of page). The tested guide reaches /AGENTS.md byte for byte, linked
    from Docs, and none of its sections is on any page. The renderer's document tests below still
    hold: the human-funnel documents use it."""
    root = fixture.build(tmp_path)
    shutil.copyfile(GUIDE, root / "AGENTS.md")
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    assert files["AGENTS.md"] == GUIDE.read_text(encoding="utf-8")
    assert 'href="/AGENTS.md"' in files["docs/index.html"]
    for rel, html in files.items():
        if rel.endswith(".html"):
            assert not re.search(r"<h2[^>]*>Claiming a node \(D-25\)</h2>", html), rel
            assert "Untrusted: AGENTS.md" not in html, rel


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
