"""F34-T43 (REMINDERS-erdos-257 item 17; handoff §3.4.4): §2's small trees as the mockup draws them.

* A group drawn as a small tree prints no list under it: the tree is the list, each of its
  statements a box linked to its page (and selectable, T36). Groups with no tree keep their list.
* The boxes are dotted outlines with serif labels — not the drawing's solid boxes.
* A statement with no name of its own shows its id, in mono, as a fallback.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET
from test_crux_band import CRUX, band_tree
from test_routes_view import render_tree

PAGE = f"problems/{TARGET}/index.html"
CSS = (Path(__file__).resolve().parents[1] / "opn_site" / "static" / "site.css").read_text()


def test_a_group_drawn_as_a_tree_prints_no_list(tmp_path: Path) -> None:
    page = render_tree(band_tree(tmp_path / "g"))[PAGE]
    group = re.search(r'<div class="off-group"[^>]*>(.*?)</div><!-- /off-group -->', page, re.S)
    assert group is not None
    assert "<ul>" not in group.group(1), "the tree is the list"
    tree = re.search(r'<svg class="dag mini-tree"[^>]*>(.*?)</svg>', group.group(1), re.S)
    assert tree is not None and f'data-node="{CRUX}"' in tree.group(1)
    assert f'href="/nodes/{TARGET}/{CRUX}/"' in tree.group(1)


def test_the_small_trees_boxes_are_dotted_with_serif_labels() -> None:
    pill = re.search(r"^svg\.mini-tree g\.node rect\.pill \{([^}]*)\}", CSS, re.M)
    text = re.search(r"^svg\.mini-tree g\.node:not\(\.fold\) > text \{([^}]*)\}", CSS, re.M)
    assert pill is not None and "stroke-dasharray" in pill.group(1)
    assert text is not None and "var(--serif)" in text.group(1)
    mono = re.search(r"^svg\.dag text\.is-id \{([^}]*)\}", CSS, re.M)
    assert mono is not None and "var(--mono)" in mono.group(1)


def test_a_statement_with_no_name_shows_its_id_in_mono(tmp_path: Path) -> None:
    """The band fixture's crux has no label of its own, so its box shows its id, marked."""
    page = render_tree(band_tree(tmp_path / "g"))[PAGE]
    tree = re.search(r'<svg class="dag mini-tree"[^>]*>(.*?)</svg>', page, re.S)
    assert tree is not None
    box = re.search(rf'data-node="{CRUX}".*?<text ([^>]*)>([^<]*)</text>', tree.group(1), re.S)
    assert box is not None
    assert 'class="is-id"' in box.group(1), box.group(0)
    assert CRUX.endswith(box.group(2)) or box.group(2) in CRUX, box.group(2)
