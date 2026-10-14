"""F04-T50: one tree carrying everything a statement's page can show, for the page redesign.

F04-T48's summary tree (a proved root split by a merged partial into two open holes, a plan and a
note on the root, an approach record, a math-first gloss and a proposed literature status on the
first hole) plus an explainer of the root's proof in three sections, so the page has an overview
to lead with and steps to fold.
"""

from __future__ import annotations

from pathlib import Path

import gloss_fixture as gf
import summary_fixture as sf
from harness import TARGET

ROOT, H1, H2 = sf.ROOT, sf.H1, sf.H2
#: The fixture graph's other nodes: the interior node and the tutorial node, both open here.
MIDDLE, TUTORIAL = "and-reassoc", "tutorial-and-swap"
NODES = (ROOT, H1, H2, MIDDLE, TUTORIAL)
OVERVIEW = "Swap the conjunction, then reassociate; each move is one rule."
EXPLAINER = (
    f"## Overview\n{OVERVIEW}\n\n"
    "## The swap {steps: h1}\nTake the hypothesis apart into its two halves and pair them the "
    "other way.\n\n"
    "## The reassociation {steps: h2}\nRegroup the three conjuncts; nothing new is assumed.\n"
)


def node_page_tree(tmp_path: Path) -> Path:
    root = sf.summary_tree(tmp_path)
    gf.explainer(root, ROOT, EXPLAINER, author="alice", date="2026-10-12")
    return root


def pages(tmp_path: Path) -> dict[str, str]:
    return sf.pages(node_page_tree(tmp_path))


def node_page(files: dict[str, str], node_id: str) -> str:
    return files[f"nodes/{TARGET}/{node_id}/index.html"]


def main_of(page: str) -> str:
    """The page's own content: what sits between the frame's ``<main>`` tags."""
    start = page.index("<main")
    return page[page.index(">", start) + 1 : page.rindex("</main>")]
