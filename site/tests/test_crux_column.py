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
from itertools import pairwise
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


# -- F30-T14 (the owner, 2026-10-22): half the width, labels wrapped, a clear way to deselect -----


def _column(band: str) -> str:
    svg = band[band.index('<svg class="dag band"') :]
    return svg[: svg.index("</svg>")]


def test_the_column_is_half_its_natural_width_and_its_labels_wrap() -> None:
    """ "The RHS takes up too much space. Make it take up half the width by default and have
    word wrap in the nodes": the column is half the width its widest one-line pill would need
    (never below a floor), every pill is that wide, a label too long for it breaks into lines,
    and the pill grows to hold them, so no two rows overlap."""
    g = rf.doc()
    # the live erdos-257 labels of uniqueness's two holes (graph/v12 `label`, from their glosses)
    for n in g["nodes"]:
        if n["node_id"] == f"{rf.UNIQUE}--h1":
            n["label"], n["label_source"] = "Mersenne reciprocals are summable", "gloss"
        if n["node_id"] == f"{rf.UNIQUE}--h2":
            n["label"], n["label_source"] = "lexicographic comparison of subset sums", "gloss"
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    col = _column(d.band)
    labels = dag.labels_of(g["nodes"])
    natural = max(dag.node_width(n, rf.ROOT, None, labels) for n in dag.band_column(g["nodes"]))
    found = re.search(r'<svg class="dag band" viewBox="0 0 (\d+) ', col)
    assert found is not None
    width = int(found.group(1))
    assert width == max(one_view.BAND_MIN_W, natural // 2), (width, natural)
    pills = re.findall(
        r'transform="translate\((-?\d+),(-?\d+)\)">.*?<rect class="pill" width="(\d+)" '
        r'height="(\d+)".*?<text[^>]*>(.*?)</text>',
        col,
        re.S,
    )
    assert pills and all(int(w) == width for _x, _y, w, _h, _t in pills)
    tall = [(int(h), t) for _x, _y, _w, h, t in pills if t.count("<tspan") >= 2]
    assert tall, "a long label wraps onto lines of its own"
    assert all(h > dag.NODE_H for h, _t in tall)
    rows = sorted((int(y), int(h)) for _x, y, _w, h, _t in pills)
    assert all(a[0] + a[1] < b[0] for a, b in pairwise(rows)), rows


PINNED = """() => ({
  pinned: [...document.querySelectorAll('svg.band g.node.pinned')].map(g => g.dataset.node),
  shown: [...document.querySelectorAll('path.band-link')]
    .filter(p => getComputedStyle(p).display !== 'none' && p.getAttribute('d')).length,
  hash: location.hash,
  stroke: (g => g ? getComputedStyle(g.querySelector('rect.pill')).stroke : null)(
    document.querySelector('svg.band g.node.pinned')),
  select: getComputedStyle(document.documentElement).getPropertyValue('--select').trim(),
})"""


def test_a_pinned_spec_is_marked_and_clears_on_a_click_elsewhere_or_escape(tmp_path: Path) -> None:
    """ "I don't see how to deselect a node being selected": a click pins a spec, which is drawn
    in the selection's amber; clicking it again, clicking on empty space, or pressing Escape
    clears it, and its lines go. (A click on a selector node keeps it, so its lines follow the
    tree: test_crux_band.test_the_band_never_moves_on_a_selection.)"""
    with browser(band_tree(tmp_path / "g"), tmp_path / "site") as pg:
        pill = pg.locator(f'svg.band g.node[data-node="{CRUX}"]')
        pill.click()
        pg.mouse.move(2, 2)
        pinned = pg.evaluate(PINNED)
        pg.mouse.click(4, 4)
        after_click = pg.evaluate(PINNED)
        pill.click()
        pg.mouse.move(2, 2)
        pg.keyboard.press("Escape")
        after_escape = pg.evaluate(PINNED)
    assert pinned["pinned"] == [CRUX] and pinned["shown"] == 1 and "band=" in pinned["hash"]
    assert pinned["stroke"] is not None and pinned["select"], pinned
    assert pinned["stroke"].replace(" ", "") == _rgb(pinned["select"]), pinned
    assert after_click["pinned"] == [] and after_click["shown"] == 0
    assert "band=" not in after_click["hash"]
    assert after_escape["pinned"] == [] and after_escape["shown"] == 0


def _rgb(hex_colour: str) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgb({r},{g},{b})"


# -- F30-T15 (the owner, 2026-10-22): a spec revised into a variant stays a spec -------------------

OLD, REV = "spec-x", "spec-x-v2"


def revised_spec_doc() -> dict[str, Any]:
    """``refutes_fixture`` with its refuting variant in the live erdos-257 shape: ``spec-x`` was a
    crux proposed for the root and is superseded by ``spec-x-v2`` (D-8 v3.46), which carries the
    relation and reads ``spec-x``'s holes — named after the old id — as its own."""
    import json  # noqa: PLC0415

    text = json.dumps(rf.doc())
    for i in range(1, 6):
        text = text.replace(f'"{rf.VARIANT}--h{i}"', f'"{OLD}--h{i}"')
    text = text.replace(f'"{rf.VARIANT}"', f'"{REV}"')
    g = json.loads(text)
    old = {
        "node_id": OLD,
        "status": "superseded",
        "deps": [f"{OLD}--h{i}" for i in range(1, 6)],
        "origin": "authored",
        "relation": None,
        "decompositions": [],
        "proposed_for": rf.ROOT,
        "uses": [],
        "label": OLD,
        "label_source": "id",
    }
    g["nodes"].append(old)
    out: dict[str, Any] = g
    return out


def test_a_spec_revised_into_a_variant_lives_in_the_column_with_its_holes() -> None:
    """ "spec-a70... still appears in the main view. It should appear on the RHS" — and the
    owner's rule: everything that is a spec, cruxes and any spec revised into a variant, while a
    statement proposed as a variant stays in the tree (refutes_fixture's own ``v``)."""
    g = revised_spec_doc()
    band = set(dag.band_of(g["nodes"]))
    assert REV in band and OLD not in band
    assert {f"{OLD}--h{i}" for i in range(1, 6)} <= band
    assert rf.VARIANT not in set(dag.band_of(rf.doc()["nodes"])), "a variant proposed as one"


def test_the_column_spec_leaves_the_resting_views_but_its_set_still_draws_it() -> None:
    """At rest the tree holds the problem's own routes only; selecting the refuting set draws
    that set (the revised spec, its route and its holes) in the main view as before."""
    from opn_gate import routes  # noqa: PLC0415

    g = revised_spec_doc()
    res = routes.read(g, [])
    vs = one_view.views(g, res)
    for key in (one_view.ROUTES, one_view.ALL):
        assert REV not in vs[key].nodes, key
    assert any(s.settles == routes.REFUTES for s in res.sets)
    view = vs[f"sel/refutes/{REV}@1"]  # the refuting set through the revision's first route
    assert REV in view.nodes and f"{OLD}--h4" in view.nodes
    assert f"{REV}@1" in view.nodes, "with its route's junction"
    assert vs["sel/proves"].nodes and REV not in vs["sel/proves"].nodes
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    assert f'data-node="{REV}"' in _column(d.band)
