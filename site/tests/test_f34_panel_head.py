"""F34-T34 (REMINDERS-erdos-257 item 13; mockup ``New-Select-Side``): the selected statement's
panel opens with a dark header that names the selection by its path: "Selected in Figure 1",
then the path from the problem to it with its last step bold, in place of the light "Selected
statement" label.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET
from test_routes_view import render_tree, two_routes

PAGE = f"problems/{TARGET}/index.html"


def panels(page: str) -> list[str]:
    return re.findall(r'<div class="card panel" data-node="[^"]+"[^>]*>(.*?)</div>\n', page, re.S)


def test_each_panel_opens_with_a_dark_header_naming_its_path(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    assert '<span class="kicker">Selected statement</span>' not in page
    heads = re.findall(
        r'<div class="panel-head"><span class="panel-head-k">Selected in Figure 1</span>'
        r'<p class="panel-path cue" data-path="([^"]+)">(.*?)</p></div>',
        page,
        re.S,
    )
    assert heads and len(heads) == page.count('<div class="card panel" data-node=')
    for ids, words in heads:
        last = words.rsplit(" &rsaquo; ", 1)[-1]
        assert last.startswith("<strong>") and last.endswith("</strong>"), words
        assert words.count("&rsaquo;") == len(ids.split()) - 1, (ids, words)


def test_the_header_is_dark() -> None:
    css = (Path(__file__).resolve().parents[1] / "opn_site/static/site.css").read_text()
    rule = re.search(r"^\.panel-head \{([^}]*)\}", css, re.M)
    assert rule is not None
    assert "background: var(--ink)" in rule.group(1) and "color: var(--surface)" in rule.group(1)
