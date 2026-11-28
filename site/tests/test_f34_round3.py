"""F34-T54 to T57 (the owner's review of the live pages, 2026-11-28).

* T54 — the panel's opening is one line. A statement other splits restated as a hole printed
  one "Restated as hole … (split by …-partial.lean)" line per split above the tabs (five on
  erdos-1094), pushing the tabs off the screen; those lines are in the Record tab. A hole still
  names the parent whose split made it, in one line.
* T55 — nothing stands between "Proved statements folded" and the drawing. The line per split of
  the route ("Split of …: …") is inside one "Retire this route…" control beside the fold
  control, which only a steward or curator sees; the full-width "Show n more statements" button
  is a quiet link under the drawing to §2, where those statements are listed, and no longer
  swaps the route for a drawing of everything.
* T56 — a phone's outline folds what the drawing folds. It had a rule of its own over every
  route together, so erdos-1094 said "10 proved statements" on a phone and "3 proved statements"
  on a desktop for one route.
* T57 — a row of the drawing that holds only junction dots is a thin row, so two levels of
  statements are not a whole empty level apart.

The browser half runs with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest site/tests/test_f34_round3.py``
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET
from test_decompositions import HOLE_IDS
from test_f34_folds import proved_pair
from test_f34_route_count import layouts_of
from test_one_view import browser, off_route
from test_products import ROOT_NODE, nodes_dir
from test_products import attest as gate_attest
from test_routes_view import REPO, THIRD, render_tree, two_routes
from test_shelving_controls import (  # noqa: F401 — the shelving test's site and fake service
    FakeService,
    pages,
    served,
    site,
    static_pages,
)

from opn_gate import products
from opn_site import dag, model, render

PAGE = f"problems/{TARGET}/index.html"


# -- T54: the panel's opening ---------------------------------------------------------------------


def restated(tmp_path: Path) -> tuple[render.Renderer, model.TargetView, model.NodeView]:
    """``two_routes``, with the second hole's row also splitting into the first hole — so the
    first hole is its parent's own hole and, to the second, a statement restated as a hole."""
    root = two_routes(tmp_path)
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    found = model.load_site(root, fixture.COMMIT)
    tv = found.targets[TARGET]
    other = tv.nodes[HOLE_IDS[1]]
    split = {
        "partial": "attempts/20260925T000000Z-carol-partial.lean",
        "holes": [{"name": "h_again", "node": HOLE_IDS[0]}],
    }
    entry = {**other.graph_entry, "decompositions": [split]}
    nodes = {**tv.nodes, HOLE_IDS[1]: dataclasses.replace(other, graph_entry=entry)}
    tv = dataclasses.replace(tv, nodes=nodes)
    return render.Renderer(found, repo_url=REPO), tv, tv.nodes[HOLE_IDS[0]]


def test_the_panel_opens_with_one_line_and_the_rest_is_in_the_record(tmp_path: Path) -> None:
    r, tv, nv = restated(tmp_path)
    panel = r.statement_panel(tv, nv)
    head, record = panel.split('<details class="record">')
    assert head.count('class="hole-of"') == 1, head
    assert "Restated as hole" not in head
    assert "<code>hden</code>" in head  # its own parent's split, still said first
    assert "Restated as hole <code>h_again</code>" in record
    assert "carol-partial.lean" in record


def test_a_statement_only_restated_opens_with_its_role(tmp_path: Path) -> None:
    """Nothing but restatements name it: the opening line is its role, as for any statement."""
    r, tv, nv = restated(tmp_path)
    entry = {**nv.graph_entry, "origin": "authored"}
    root = tv.nodes[ROOT_NODE]
    nodes = {
        **tv.nodes,
        nv.node_id: dataclasses.replace(nv, graph_entry=entry),
        ROOT_NODE: dataclasses.replace(
            root, graph_entry={**root.graph_entry, "decompositions": []}
        ),
    }
    tv = dataclasses.replace(tv, nodes=nodes)
    panel = r.statement_panel(tv, tv.nodes[nv.node_id])
    head, record = panel.split('<details class="record">')
    assert 'class="hole-of"' not in head and 'class="panel-note"' in head
    assert "Restated as hole <code>h_again</code>" in record


def test_a_hole_two_splits_of_its_parent_share_opens_with_one_line(tmp_path: Path) -> None:
    """Live erdos-257 after the deploy (2026-11-28): a second split of the same parent reused a
    hole, and its panel opened with two lines. The first split says where it came from; the
    second is in the Record tab."""
    r, tv, nv = restated(tmp_path)
    root = tv.nodes[ROOT_NODE]
    first = next(
        d
        for d in root.graph_entry["decompositions"]
        if any(h["node"] == nv.node_id for h in d["holes"])
    )
    again = {**first, "partial": "attempts/20260926T000000Z-dave-partial.lean"}
    splits = [*root.graph_entry["decompositions"], again]
    entry = {**root.graph_entry, "decompositions": splits}
    tv = dataclasses.replace(
        tv, nodes={**tv.nodes, ROOT_NODE: dataclasses.replace(root, graph_entry=entry)}
    )
    head, record = r.statement_panel(tv, nv).split('<details class="record">')
    assert head.count('class="hole-of"') == 1, head
    assert "dave-partial.lean" in record and "dave-partial.lean" not in head


def test_the_statements_own_page_still_says_all_of_it(tmp_path: Path) -> None:
    r, tv, nv = restated(tmp_path)
    said = r.panel_role(tv, nv, page=True)
    assert said.count('class="hole-of"') == 2 and "Restated as hole" in said


# -- T55: nothing between the fold control and the drawing ---------------------------------------


def heading(page: str) -> str:
    """From the figure's heading to its drawing."""
    return page[page.index('<p class="figure-cap">') : page.index('<div class="graph-body">')]


def test_the_splits_are_inside_one_retire_control(pages: dict[str, str]) -> None:  # noqa: F811
    head = heading(pages[PAGE])
    groups = re.findall(
        r'<details class="figure-retire" data-view="[^"]+" hidden>'
        r'<summary class="retire-route">Retire this route…</summary>(.*?)</details>',
        head,
        re.S,
    )
    assert groups
    assert any('class="retire-act"' in g for g in groups)
    outside = re.sub(r"<details class=\"figure-retire\".*?</details>", "", head, flags=re.S)
    assert "Split of" not in outside and "split-words" not in outside
    assert '<div class="figure-retire"' not in pages[PAGE]
    # the fold control and the retire control share one row
    assert re.search(r'<div class="figure-acts">.*class="figure-folds".*</div>', head, re.S)


def test_no_service_no_retire_control(static_pages: dict[str, str]) -> None:  # noqa: F811
    assert "figure-retire" not in static_pages[PAGE]
    assert "Retire this route" not in static_pages[PAGE]


def test_the_statements_on_no_route_are_a_quiet_link_to_section_two(tmp_path: Path) -> None:
    page = render_tree(off_route(tmp_path / "g"))[PAGE]
    assert "view-toggle" not in page
    assert 'class="chip' not in heading(page) and "Show 1 more" not in page
    link = re.search(r'<p class="off-route-line"><a href="#not-on-route">([^<]+)</a></p>', page)
    assert link is not None
    assert link.group(1) == "1 more statement is not on a route ↓"
    # under the drawing, inside the figure's card
    assert page.index('<div class="graph-body">') < link.start() < page.index('class="dag-caption"')


def test_no_link_when_every_statement_is_on_a_route(tmp_path: Path) -> None:
    assert "off-route-line" not in render_tree(two_routes(tmp_path / "g"))[PAGE]


def test_a_reader_sees_nothing_between_the_fold_control_and_the_drawing(tmp_path: Path) -> None:
    with browser(proved_pair(two_routes(tmp_path / "g")), tmp_path / "site") as pg:
        gap = pg.evaluate(
            """() => {
              const cap = document.querySelector('.figure-cap').getBoundingClientRect();
              const body = document.querySelector('.graph-body').getBoundingClientRect();
              const between = [...document.querySelectorAll('.figure-card *')].filter(e => {
                if (!e.checkVisibility() || e.children.length) return false;
                const r = e.getBoundingClientRect();
                return r.height > 0 && r.top >= cap.bottom - 1 && r.bottom <= body.top + 1;
              }).map(e => e.textContent.trim()).filter(Boolean);
              return {between, room: body.top - cap.bottom};
            }"""
        )
    assert all(w in ("unfold", "fold") for w in gap["between"]), gap
    assert gap["room"] <= 70, gap


def test_a_steward_opens_retire_this_route_to_choose_a_split(served: str) -> None:  # noqa: F811
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(served + f"/problems/{TARGET}/")
        control = pg.locator("details.figure-retire:not([hidden]) > summary")
        control.wait_for(state="visible", timeout=10000)
        assert control.inner_text() == "Retire this route…"
        closed = pg.locator("details.figure-retire:not([hidden]) .split-words").first.is_visible()
        same_row = pg.evaluate(
            """() => {
              const a = document.querySelector('.figure-acts').getBoundingClientRect();
              const s = document.querySelector('details.figure-retire:not([hidden]) > summary')
                .getBoundingClientRect();
              return s.top >= a.top - 1 && s.bottom <= a.top + 60;
            }"""
        )
        control.click()
        opened = pg.locator("details.figure-retire:not([hidden]) .retire-act button").first
        opened.wait_for(state="visible")
        words = pg.locator("details.figure-retire:not([hidden]) .split-words").first.inner_text()
        evidence = Path(__file__).resolve().parents[2] / "engineering/evidence/F34"
        pg.locator(".figure-card").screenshot(path=str(evidence / "task-55-steward-1440.png"))
        b.close()
    assert not closed and same_row
    assert words.startswith("Split of ")


def test_a_reader_who_is_no_steward_sees_no_retire_control(tmp_path: Path, site: Any) -> None:  # noqa: F811
    """The control is on the page for the script to fill; unfilled, the stylesheet hides it."""
    css = (Path(render.__file__).resolve().parent / "static" / "site.css").read_text("utf-8")
    assert re.search(
        r"\.figure-retire:not\(:has\(\.retire-act:not\(\[hidden\]\)\)\)\s*\{\s*display:\s*none",
        css,
    )


# -- T56: the outline folds what the drawing folds -----------------------------------------------

OUTLINE = """() => {
  const svg = document.querySelector('svg.dag:not(.band)');
  const drawn = [...svg.querySelectorAll('g.node.fold')]
    .filter(g => !g.classList.contains('off-view'))
    .map(g => parseInt(g.getAttribute('aria-label'), 10)).sort();
  const boxes = [...document.querySelectorAll('.route-outline li.fold')]
    .filter(li => !li.hidden).map(li => parseInt(li.textContent, 10)).sort();
  const rows = [...document.querySelectorAll('.route-outline > li[data-node]')]
    .filter(li => !li.hidden).map(li => li.dataset.node);
  return {view: svg.dataset.view, drawn, boxes, rows};
}"""


def test_the_outline_has_no_fold_rule_of_its_own(tmp_path: Path) -> None:
    page = render_tree(proved_pair(two_routes(tmp_path / "g")))[PAGE]
    outline = re.search(r'<ol class="route-outline".*?</ol>', page, re.S)
    assert outline is not None
    assert "data-in-fold" not in outline.group(0) and 'class="fold' not in outline.group(0)
    assert not hasattr(render, "outline_folds")


def three_proved(root: Path) -> Path:
    """``proved_pair`` with the other split's one hole proved too: two routes, the first with two
    proved statements under the problem and the second with one. Over both routes together the
    three are one run of proved siblings, which is what the outline used to fold and count."""
    root = proved_pair(root)
    d = nodes_dir(root) / THIRD
    (d / "Proof.lean").write_text(
        (d / "Statement.lean").read_text(encoding="utf-8").replace("sorry", "trivial"),
        encoding="utf-8",
    )
    gate_attest(root, THIRD, n=22, footprint={"nodes": []})
    return root


def test_a_phone_folds_what_the_drawing_folds(tmp_path: Path) -> None:
    with browser(three_proved(two_routes(tmp_path / "g")), tmp_path / "site") as pg:
        lays = pg.evaluate("JSON.parse(document.getElementById('graph-layouts').textContent)")
        folded = next(k for k in lays if k.endswith("~open")).removesuffix("~open")
        plain = next(
            k for k in lays if k.startswith("sel/") and "~" not in k and f"{k}~open" not in lays
        )
        seen = {}
        for view in (folded, plain):
            pg.set_viewport_size({"width": 1440, "height": 900})
            pg.locator(f'svg.selector g.kind-leaf[data-view="{view}"]').click()
            pg.wait_for_function(
                "v => document.querySelector('svg.dag').dataset.view === v", arg=view
            )
            pg.wait_for_timeout(900)
            wide = pg.evaluate(OUTLINE)
            pg.set_viewport_size({"width": 390, "height": 844})
            pg.wait_for_timeout(300)
            seen[view] = (wide, pg.evaluate(OUTLINE))
        # the folded route: one box, the drawing's count, its members out of sight
        wide, phone = seen[folded]
        assert wide["drawn"] == [2] and phone["boxes"] == wide["drawn"], seen[folded]
        assert not set(HOLE_IDS) & set(phone["rows"])
        # the other route's one proved statement is a box of its own in the drawing (the fold
        # rule wants two), so it is a row of its own on the phone
        wide, phone = seen[plain]
        assert wide["drawn"] == [] and phone["boxes"] == [], seen[plain]
        assert THIRD in phone["rows"]
        # the box opens in place and closes again
        pg.set_viewport_size({"width": 1440, "height": 900})
        pg.locator(f'svg.selector g.kind-leaf[data-view="{folded}"]').click()
        pg.wait_for_function(
            "v => document.querySelector('svg.dag').dataset.view === v", arg=folded
        )
        pg.set_viewport_size({"width": 390, "height": 844})
        pg.wait_for_timeout(300)
        box = pg.locator(".route-outline li.fold:not([hidden]) .fold-box")
        assert "2 proved statements" in box.inner_text()
        box.click()
        assert set(HOLE_IDS) <= set(pg.evaluate(OUTLINE)["rows"])
        pg.locator(".route-outline li.fold:not([hidden]) .fold-box").click()
        assert not set(HOLE_IDS) & set(pg.evaluate(OUTLINE)["rows"])


# -- T57: a row of junction dots is a thin row ---------------------------------------------------


def test_a_row_of_only_dots_keeps_two_levels_close(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    lays = layouts_of(page)
    checked = 0
    for key, lay in lays.items():
        if not key.startswith("sel/"):
            continue
        tops: dict[float, list[str]] = {}
        for nid, (_x, y, _w) in lay["nodes"].items():
            tops.setdefault(y, []).append(nid)
        levels = sorted(tops)
        for above, here, below in zip(levels, levels[1:], levels[2:], strict=False):
            if all("@" in n for n in tops[here]):
                assert here - above <= dag.NODE_H + dag.DOT_GAP_Y, (key, above, here)
                assert below - here <= dag.NODE_H + dag.DOT_GAP_Y, (key, here, below)
                checked += 1
    assert checked
    assert dag.DOT_GAP_Y < dag.WRAP_GAP_Y < dag.GAP_Y


def test_two_rows_of_statements_keep_their_distance() -> None:
    nodes = [
        {"node_id": "r", "status": "ready", "deps": ["a"]},
        {"node_id": "a", "status": "ready", "deps": []},
    ]
    lay = dag.layout(nodes, root="r")
    ys = sorted(p.y for p in lay.placed)
    assert ys[1] - ys[0] == dag.NODE_H + dag.GAP_Y
