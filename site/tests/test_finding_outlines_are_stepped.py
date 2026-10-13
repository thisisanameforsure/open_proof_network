"""F04-T45 (Q44): only a stepped annex is an outline.

A mathematician reading erdos-1094--h2's panel found two "outlines": the stepped annex the
skeleton followed (``annex/v2`` with ``steps``, D-31 v3.26) and a literature-and-numerics note
with no steps at all. The graph's tab said 2, the key said "has an outline", and the panel put
both under "Outlines". An annex without steps is a note — an informal argument, still untrusted —
and the page now says so: the tab counts stepped annexes, "Outlines" lists them, and every other
annex sits under "Notes", labelled by its kind, with the same "followed by" line and the same
untrusted marking.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET, copy_graph
from test_annex_steps import outline_annex
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_outline_links import page_of, panel
from test_products import ROOT_NODE, nodes_dir

NOTE = "c" * 64


def stepped_and_note(tmp_path: Path) -> tuple[Path, str]:
    """The root carries one stepped annex (followed by a merged skeleton) and one note."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    digest = outline_annex(root, "hden", "combine")
    merged_partial(root, 7, ["hden"], annex=None)
    partial = nodes_dir(root) / ROOT_NODE / "attempts" / "20260920T000000Z-alice-partial.lean"
    partial.write_text(f"theorem x : True := by\n  -- annex: {digest}\n  sorry\n")
    (nodes_dir(root) / ROOT_NODE / "annex" / f"{NOTE}.md").write_text(
        "# What the literature says\n\nKonyagin 1999.\n", encoding="utf-8"
    )
    return root, digest


def pill(page: str, node_id: str) -> str:
    m = re.search(rf'<g class="node[^"]*" data-node="{node_id}".*?</g></a>', page, re.S)
    assert m is not None, node_id
    return m.group(0)


def test_the_tab_counts_only_stepped_annexes(tmp_path: Path) -> None:
    root, _ = stepped_and_note(tmp_path)
    mark = re.search(
        r'<g class="outline-mark"[^>]*>.*?<text[^>]*>(\d+)</text>',
        pill(page_of(root), ROOT_NODE),
        re.S,
    )
    assert mark is not None and mark.group(1) == "1"


def test_a_note_is_not_listed_under_outlines(tmp_path: Path) -> None:
    root, digest = stepped_and_note(tmp_path)
    body = panel(page_of(root), ROOT_NODE)
    outlines = re.search(r'<ul class="outlines">(.*?)</ul>', body, re.S)
    assert outlines is not None
    assert f'data-annex="{digest}"' in outlines.group(1)
    assert f'data-annex="{NOTE}"' not in outlines.group(1)


def test_a_note_is_listed_under_notes_labelled_untrusted_and_by_kind(tmp_path: Path) -> None:
    root, _ = stepped_and_note(tmp_path)
    body = panel(page_of(root), ROOT_NODE)
    notes = re.search(
        r'<div class="panel-outlines panel-notes"><span class="kicker">Notes</span>(.*?)</div>',
        body,
        re.S,
    )
    assert notes is not None
    item = re.search(
        rf'<li class="outline note" data-annex="{NOTE}">(.*?)</li>', notes.group(1), re.S
    )
    assert item is not None
    assert "What the literature says" in item.group(1)
    assert '<span class="note-kind">' in item.group(1)
    assert "untrusted" in notes.group(1).lower()
    assert "record page" in notes.group(1)
    assert f'href="/nodes/{TARGET}/{ROOT_NODE}/#annex-{NOTE[:12]}"' in item.group(1)
    node_page = page_of(root, f"nodes/{TARGET}/{ROOT_NODE}/index.html")
    assert f'id="annex-{NOTE[:12]}"' in node_page


def test_a_node_with_only_notes_has_no_tab_and_no_outline_key(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    (nodes_dir(root) / ROOT_NODE / "annex" / f"{NOTE}.md").write_text("a note\n", encoding="utf-8")
    page = page_of(root)
    assert "outline-mark" not in pill(page, ROOT_NODE)
    key = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert key is not None and "has an outline" not in key.group(1)
    body = panel(page, ROOT_NODE)
    assert '<span class="kicker">Outlines</span>' not in body
    assert '<span class="kicker">Notes</span>' in body
