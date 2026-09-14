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
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
GUIDE = Path(__file__).resolve().parents[2] / "gate" / "agents" / "AGENTS.md"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "finding site-docs-agents-md (F04-R9, F10-R9, D-27): AGENTS.md is rendered by the prose "
        "renderer, so its headings, output fences and MCP table reach the docs page as "
        "paragraphs of raw markdown; fix: F04-T10 (Mike, 2026-09-14)"
    ),
)
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
