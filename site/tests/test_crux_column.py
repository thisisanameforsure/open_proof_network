"""F30-T13 (the owner, 2026-10-21, on the live erdos-257): the proposed statements are one column
at the top right of the drawing's card, beside "Ways to settle the problem" and flush with the
card's right side, not a drawing under the tree.

"They should be positioned vertically regardless of the specs' relationship between each other.
You can order them so that ones related to each other are more likely to be positioned above or
below each other. The curves between the spec node and the nodes they relate to should not be
drawn unless the spec is hovered or clicked."

So the column stacks every band statement (a crux and its own holes) as plain pills, a crux
followed by its holes and then by the cruxes it is related to; it draws no line at all at rest,
the lines among band statements included; every line from a band statement is a link that is
drawn only while lit.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import refutes_fixture as rf
from test_crux_band import BAND_STATE, CRUX, band_tree, hrefs
from test_one_view import browser
from test_routes_view import THIRD

from opn_site import dag, one_view


def _crux(
    nid: str, *, deps: list[str] | None = None, uses: list[str] | None = None
) -> dict[str, Any]:
    return {
        "node_id": nid,
        "status": "ready",
        "deps": deps or [],
        "uses": uses or [],
        "proposed_for": "root",
        "relation": None,
        "origin": "authored",
    }


def _hole(nid: str) -> dict[str, Any]:
    return {"node_id": nid, "status": "ready", "deps": [], "origin": "compiler-derived"}


def test_the_column_puts_a_crux_its_holes_and_its_relations_together() -> None:
    """Sorted by id the column would read a, a--h1, b, c, separating ``a`` from ``c``, which
    ``a``'s hole uses; related statements are adjacent, unrelated ones after."""
    rows = [
        {"node_id": "root", "status": "ready", "deps": [], "proposed_for": None},
        _crux("spec-a", deps=["spec-a--h1"]),
        _hole("spec-a--h1") | {"uses": ["spec-c"]},
        _crux("spec-b"),
        _crux("spec-c"),
    ]
    assert dag.band_column(rows) == ("spec-a", "spec-a--h1", "spec-c", "spec-b")


def test_the_column_is_a_stack_of_pills_flush_right_with_no_line_at_rest() -> None:
    g = rf.doc()
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    band_svg = d.band[d.band.index('<svg class="dag band"') :]
    band_svg = band_svg[: band_svg.index("</svg>")]
    assert "<path" not in band_svg, "the column draws no line at rest"
    assert "data-route=" not in band_svg, "no junction in the column"
    placed = [
        (m["id"], float(m["x"]), float(m["y"]))
        for m in re.finditer(
            r'data-node="(?P<id>[^"]+)"[^>]*'
            r'transform="translate\((?P<x>[-\d.]+)[ ,](?P<y>[-\d.]+)\)"',
            band_svg,
        )
    ]
    order = dag.band_column(g["nodes"])
    assert [p[0] for p in placed] == list(order)
    ys = [p[2] for p in placed]
    assert ys == sorted(ys) and len(set(ys)) == len(ys), "one pill per row, top to bottom"
    # every line from a band statement, among the band's own included, is a link with no path
    links = re.findall(
        r'<path class="band-link[^"]*" data-from="([^"]+)" data-to="([^"]+)"', d.band
    )
    assert (f"{rf.UNIQUE}--h1", rf.UNIQUE) in links and (f"{rf.UNIQUE}--h2", rf.UNIQUE) in links
    assert (rf.GAP, rf.UNIQUE) in links and (rf.GAP, f"{rf.ROOT}--h1") in links
    assert " d=" not in "".join(re.findall(r'<path class="band-link[^>]*>', d.band))


def test_the_column_sits_beside_the_selector(tmp_path: Path) -> None:
    """In the page: the card's body holds the selector and the drawing on the left and the
    column on the right; on screen the column's top meets the selector's top and its right side
    the card's content edge, and the tree is not under it."""
    with browser(band_tree(tmp_path / "g"), tmp_path / "site") as pg:
        html = pg.content()
        geo = pg.evaluate(
            """() => {
              const r = s => document.querySelector(s).getBoundingClientRect();
              const card = document.querySelector('.dag-wrap');
              const cs = getComputedStyle(card);
              return {sel: r('.selector-wrap'), band: r('.band-wrap'), tree: r('.dag-scroll'),
                      inner: card.getBoundingClientRect().right - parseFloat(cs.paddingRight)
                             - parseFloat(cs.borderRightWidth)};
            }"""
        )
        rest = pg.evaluate(BAND_STATE)
        pg.locator(f'svg.band g.node[data-node="{CRUX}"]').hover()
        hovered = pg.evaluate(BAND_STATE)
    body = html[html.index('class="graph-body"') :]
    assert body.index('class="graph-main"') < body.index('class="selector-wrap"')
    assert body.index('class="dag-scroll"') < body.index('class="band-wrap"')
    assert abs(geo["band"]["top"] - geo["sel"]["top"]) <= 4, geo
    assert abs(geo["band"]["right"] - geo["inner"]) <= 2, geo
    assert (
        geo["band"]["left"] >= geo["sel"]["right"]
        and geo["band"]["left"] >= geo["tree"]["right"] - 1
    )
    assert not any(ln["shown"] for ln in rest["links"])
    lit = [ln["key"] for ln in hovered["links"] if ln["lit"] and ln["shown"]]
    assert lit == [f"{CRUX}>{THIRD}"], lit
