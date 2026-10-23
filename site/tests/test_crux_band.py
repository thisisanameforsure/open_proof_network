"""F30-T11 (D-14 v3.26 as amended by v3.46, D-25 v3.46): proposed cruxes leave the proof tree
for a band of their own, and only the lines the record has measured join them to it, lit.

The owner's reading of erdos-257 (2026-10-21): a proved spec pointed at an unproved root by a
dotted line that meant nothing. Now a crux with a ``proposed_for`` pointer and no checked relation,
with its own holes, is drawn in a second region under the main drawing ("Proposed statements");
no line joins it to the tree at rest; hovering or clicking its pill lights the measured lines from
it (a use, a lemma, a dependency) across the gap, and the band's own lines through its junctions,
as F30-T6's hover does. Clicking keeps them lit (``band=<id>`` in the hash). Nothing moves. A
crux a merged proof *uses* stays in the band (the owner: "keep the specs on the band"); a crux
some statement declares as a *dependency* stays in the tree, where its solid line already says
more (erdos-402's ``spec-fa8046e4``). A crux with a checked relation is a variant and is drawn in
the tree as one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fixture
import pytest
import refutes_fixture as rf
import samples
import yaml
from harness import TARGET
from test_finding_dag_layout import SHAPES
from test_one_view import LEAF, SNAPSHOT, boxes, browser, layouts_in, lit_edges, lit_nodes
from test_products import ROOT_NODE, nodes_dir
from test_products import attest as gate_attest
from test_routes_view import THIRD, node, two_routes

from opn_gate import layout as gate_layout
from opn_gate import scaffold
from opn_site import dag, one_view

CRUX = "spec-crux1"
PAGE = f"problems/{TARGET}/index.html"


def hand(*, dep: bool = False, relation: str | None = None) -> list[dict[str, Any]]:
    """``n`` (open) and the proved crux ``c`` proposed for it; with ``dep`` ``n`` declares ``c``;
    with ``relation`` ``c`` is a variant that carries one."""
    return [
        {"node_id": "n", "status": "ready", "deps": ["c"] if dep else [], "proposed_for": None},
        {
            "node_id": "c",
            "status": "proved",
            "deps": [],
            "proposed_for": "n",
            "relation": relation,
            "origin": "variant" if relation else "authored",
        },
    ]


# -- 1. membership and the layout (dag) ------------------------------------------------------------


def test_a_proposed_crux_leaves_the_tree_for_the_band() -> None:
    nodes = hand()
    assert dag.proposed(nodes) == ["c"]
    assert dag.band_of(nodes) == ("c",)
    assert dag.lines(nodes) == [], "no pointer line is drawn any more"
    assert dag.layers(nodes) == {"c": 0, "n": 0}, "the crux is not layered under the node"
    lay = dag.layout(nodes, root="n")
    assert lay.band == ("c",) and lay.loose == () and lay.links == ()
    at = {p.node_id: p for p in lay.placed}
    assert at["c"].y > at["n"].y + dag.NODE_H, "the band lies under the tree"
    assert at["n"].y < lay.band_y < at["c"].y, "the band's label sits between"


def test_a_used_crux_stays_in_the_band_and_the_use_is_a_lit_only_link() -> None:
    nodes = hand()
    nodes[0]["uses"] = ["c"]
    lay = dag.layout(nodes, root="n")
    assert lay.band == ("c",)
    assert [(e.src, e.dst, e.kind) for e in lay.links] == [("c", "n", "edge use")]
    assert lay.edges == [], "the use crosses the regions, so it is a link, not a tree line"
    svg = dag.svg(nodes, href={"n": "/n", "c": "/c"})
    assert re.search(r'<path class="edge use band-link" data-from="c" data-to="n"', svg)
    assert "edge proposed" not in svg
    assert dag.BAND_LABEL in svg


def test_a_crux_declared_as_a_dependency_stays_in_the_tree() -> None:
    nodes = hand(dep=True)
    # F30-T16: it is the tree's because the root reaches it by that dependency
    assert dag.band_of(nodes, dag.connected_to(nodes, "n")) == () and dag.proposed(nodes) == []
    lay = dag.layout(nodes, root="n")
    assert lay.band == () and [(e.src, e.dst, e.kind) for e in lay.edges] == [("c", "n", "edge")]


def test_a_crux_with_a_checked_relation_is_a_variant_not_a_band_statement() -> None:
    assert dag.band_of(hand(relation="refutes")) == ()


def test_a_superseded_crux_leaves_the_band_and_its_holes_follow_its_revision() -> None:
    """F30-T12 (found live on erdos-257, 2026-10-21): ``spec-a70fcca4`` was revised as a
    ``refutes`` variant (graph #801) whose route is the old node's, read through ``supersedes``.
    The old crux kept its proposed-for pointer and no relation, so the band still took it and,
    by id prefix, its four holes, while the revision's junction in the tree hung with nothing
    beneath it. A superseded crux leaves the band as every superseded statement does, and the
    holes go with the live route that holds them. F30-T15 (the owner, 2026-10-22: "everything that
    is a spec"): that route is the revision's, and a spec revised into a variant is in the
    column, so the holes are there with it."""
    rows: list[dict[str, Any]] = [
        {"node_id": "root", "status": "ready", "deps": [], "proposed_for": None},
        {
            "node_id": "spec-x",
            "status": "superseded",
            "deps": ["spec-x--h1", "spec-x--h2"],
            "proposed_for": "root",
            "relation": None,
            "origin": "authored",
        },
        {
            "node_id": "spec-x-v2",
            "status": "ready",
            "deps": ["spec-x--h1", "spec-x--h2"],
            "proposed_for": None,
            "relation": "refutes",
            "origin": "variant",
        },
        {"node_id": "spec-x--h1", "status": "proved", "deps": [], "origin": "compiler-derived"},
        {"node_id": "spec-x--h2", "status": "ready", "deps": [], "origin": "compiler-derived"},
    ]
    assert dag.band_of(rows) == ("spec-x--h1", "spec-x--h2", "spec-x-v2")


def test_the_band_holds_a_crux_its_holes_and_the_crux_it_uses() -> None:
    rows = rf.doc()["nodes"]
    assert dag.proposed(rows) == [rf.GAP, rf.UNIQUE]
    assert dag.band_of(rows) == (rf.GAP, rf.UNIQUE, f"{rf.UNIQUE}--h1", f"{rf.UNIQUE}--h2")


@pytest.mark.parametrize("target", sorted(SHAPES))
def test_every_pointer_crux_of_the_live_shapes_is_in_the_band_or_a_dependency(
    target: str,
) -> None:
    shape = SHAPES[target]
    rows = shape["nodes"]
    # F30-T16: a crux is the tree's when the root reaches it, else the column's
    reached = dag.connected_to(rows, shape["root"])
    cruxes = {n["node_id"] for n in rows if n.get("proposed_for") and not n.get("relation")}
    band = set(dag.band_of(rows, reached))
    assert band >= cruxes - reached
    assert not band & reached
    lay = dag.layout(rows, root=shape["root"], prefix=target)
    assert set(lay.band) == band
    assert not set(lay.loose) & cruxes, "no crux is in the group no line joins"
    assert not any(e.kind == "edge proposed" for e in lay.edges)


# -- 2. the views and the drawing (one_view) ----------------------------------------------------


def hrefs(g: dict[str, Any]) -> dict[str, str]:
    return {n["node_id"]: f"/nodes/{n['node_id']}/" for n in g["nodes"]}


def test_the_views_exclude_the_band_and_the_band_view_has_its_own_junction() -> None:
    g = rf.doc()
    from opn_gate import routes  # noqa: PLC0415

    vs = one_view.views(g, routes.read(g, []))
    band = set(dag.band_of(g["nodes"]))
    for key, v in vs.items():
        if key == one_view.BAND:
            continue
        assert not band & set(v.nodes), key
        assert not any(k == "edge proposed" for _s, _d, k in v.lines), key
    assert set(vs[one_view.BAND].nodes) == band | {f"{rf.UNIQUE}@1"}
    assert (rf.GAP, rf.UNIQUE, "edge use") in vs[one_view.BAND].lines
    assert (f"{rf.UNIQUE}@1", rf.UNIQUE, "edge") in vs[one_view.BAND].lines


def test_the_drawing_puts_the_band_beside_the_tree_with_lit_only_links() -> None:
    g = rf.doc()
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    assert '<svg class="dag band"' in d.band
    assert "Speculative statements" in d.band and "measured" in d.band
    band_svg = d.band[d.band.index('<svg class="dag band"') :]
    band_svg = band_svg[: band_svg.index("</svg>")]
    for nid in (rf.GAP, rf.UNIQUE, f"{rf.UNIQUE}--h1", f"{rf.UNIQUE}--h2"):
        assert f'data-node="{nid}"' in band_svg and f'data-node="{nid}"' not in d.svg, nid
        pill = re.search(rf'<g class="[^"]*" data-node="{nid}"', band_svg)
        assert pill is not None and "off-view" not in pill.group(0)
    # F30-T13 (the owner, 2026-10-21): the column draws no line and no junction at rest; every
    # line from a band statement, the band's own use line and its holes' lines included, is a
    # link with no d, drawn only while lit.
    assert "<path" not in band_svg and "data-route=" not in band_svg
    links = re.findall(r'<path class="band-link[^"]*"[^>]*>', d.band)
    ends = {tuple(re.findall(r'data-(?:from|to)="([^"]+)"', ln)) for ln in links}
    assert ends == {
        (rf.GAP, f"{rf.ROOT}--h1"),
        (rf.GAP, rf.UNIQUE),
        (f"{rf.UNIQUE}--h1", rf.UNIQUE),
        (f"{rf.UNIQUE}--h2", rf.UNIQUE),
    }
    assert all(" d=" not in ln for ln in links)
    assert "edge proposed" not in d.svg and "edge proposed" not in d.band
    # The pill's words say what the pointer says, since no line does.
    assert f"proposed for: {rf.ROOT_LABEL}" in band_svg
    # The toggle counts no band statement: here every other statement is on a route.
    assert d.hidden == 0 and d.toggle == ""


def test_the_toggle_counts_off_route_statements_but_not_the_band() -> None:
    g = rf.doc()
    g["nodes"].append(
        # F30-T16: an authored statement nothing joins (a related variant is in the column)
        {**node("u", origin="authored"), "uses": [], "proposed_for": None}
    )
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    assert d.hidden == 1 and "Show 1 more statement" in d.toggle


def test_the_layouts_json_has_no_crux_ids() -> None:
    g = rf.doc()
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    doc = json.loads(re.search(r">(\{.*\})</script>", d.layouts_json, re.S).group(1))  # type: ignore[union-attr]
    assert one_view.BAND not in doc
    band = set(dag.band_of(g["nodes"]))
    for key, lay in doc.items():
        assert not band & set(lay["nodes"]), key
        assert not any(k == "edge proposed" for _s, _d, k, _p in lay["lines"]), key


def test_a_graph_without_a_crux_has_no_band() -> None:
    from test_routes_view import nested_doc  # noqa: PLC0415

    g = nested_doc()
    d = one_view.drawing(g, [], href=hrefs(g), prefix="t")
    assert d.band == ""


# -- 3. in a browser ----------------------------------------------------------------------------


def band_tree(tmp_path: Path) -> Path:
    """``two_routes`` plus a proved crux proposed for the root, which the third hole's merged
    proof uses (a use line after its header, F08-R19): on the record the crux has a pointer and
    a use, and nothing declares it as a dependency."""
    root = two_routes(tmp_path)
    proposal = scaffold.Proposal(
        node_id=CRUX,
        target_id=TARGET,
        statement="theorem OpnProp.crux1 : ∀ p : Prop, p → p := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="authored",
        proposed_for=ROOT_NODE,
        date="2026-10-02T00:00:00Z",
    )
    scaffold.validate(proposal)
    scaffold.write(fixture.nodes_dir(root), proposal)
    crux = nodes_dir(root) / CRUX
    statement = (crux / "Statement.lean").read_text(encoding="utf-8")
    (crux / "Proof.lean").write_text(
        statement.replace("sorry", "exact fun _ h => h"), encoding="utf-8"
    )
    gate_attest(root, CRUX, n=13, footprint={"nodes": []})
    hole = nodes_dir(root) / THIRD
    text = (hole / "Statement.lean").read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    last_import = max(i for i, ln in enumerate(lines) if ln.startswith("import "))
    lines.insert(last_import + 1, f"import {gate_layout.node_module(CRUX, 'Proof')}\n")
    (hole / "Proof.lean").write_text(
        "".join(lines).replace("sorry", "exact trivial"), encoding="utf-8"
    )
    gate_attest(root, THIRD, n=12, footprint={"nodes": [CRUX]})
    assert gate_layout.merged_uses(hole) == (CRUX,), "the fixture's use line is not read"
    # A crux has no dependents, so the root is declared (F08-Q19).
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / "2026-10-02-curator.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE)), encoding="utf-8"
    )
    return root


BAND_STATE = """() => {
  const main = document.querySelector('svg.dag:not(.band)');
  const band = document.querySelector('svg.band');
  const vis = el => getComputedStyle(el).display !== 'none';
  const at = g => g.getAttribute('transform');
  const links = [...document.querySelectorAll('path.band-link')].map(p => {
    const b = p.getBBox();
    return {key: p.getAttribute('data-key'), shown: vis(p), lit: p.classList.contains('lit'),
            d: p.getAttribute('d') || '', box: [b.width, b.height]};
  });
  return {
    links,
    band: band ? [...band.querySelectorAll('[data-node]')]
      .map(g => [g.getAttribute('data-node'), at(g), g.classList.contains('lit')]) : null,
    bandHovering: band ? band.classList.contains('hovering') : null,
    mainHovering: main.classList.contains('hovering'),
    mainLit: [...main.querySelectorAll('[data-node].lit')].map(g => g.getAttribute('data-node')),
    mainLitEdges: [...main.querySelectorAll('path.edge.lit')].map(e => e.getAttribute('data-key')),
    hash: location.hash,
    panel: [...document.querySelectorAll('.panel[data-node]')].filter(p => !p.hidden)
      .map(p => p.getAttribute('data-node')),
  };
}"""


#: Each lit band link's two ends on screen against the pills it joins: the band pill's left
#: middle and the tree pill's right middle (F30-T13: the column is at the card's right, so a
#: line leaves the column sideways), as distances in CSS pixels.
LINK_ENDS = """() => [...document.querySelectorAll('path.band-link.lit')].map(p => {
  const m = p.getScreenCTM(), n = p.getTotalLength();
  const at = l => { const q = p.getPointAtLength(l); return [q.x * m.a + m.e, q.y * m.d + m.f]; };
  const box = id => document.querySelector(
    `svg.band [data-node="${id}"], svg.dag:not(.band) [data-node="${id}"]`).getBoundingClientRect();
  const a = box(p.getAttribute('data-from')), b = box(p.getAttribute('data-to'));
  const [s, e] = [at(0), at(n)];
  return [Math.hypot(s[0] - a.left, s[1] - (a.top + a.height / 2)),
          Math.hypot(e[0] - b.right, e[1] - (b.top + b.height / 2))];
})"""


def test_a_lit_band_link_meets_the_two_pills_it_joins(tmp_path: Path) -> None:
    """The lit line is drawn where its pills are: it starts at the band pill's left side and
    ends at the tree pill's right side (F30-T13), within a pixel, on screen (the overlay's own
    coordinates, not the card's — an offset the d-attribute alone cannot show)."""
    with browser(band_tree(tmp_path / "g"), tmp_path / "site") as pg:
        pg.locator(f'svg.band g.node[data-node="{CRUX}"]').hover()
        ends = pg.evaluate(LINK_ENDS)
    assert len(ends) == 1, ends
    assert all(d <= 1.0 for d in ends[0]), ends


def test_hovering_and_clicking_a_band_pill_lights_its_measured_lines_only(tmp_path: Path) -> None:
    """Hover: the use line from the crux into the tree is drawn and lit, the third hole lit,
    nothing else; the drawing's boxes unchanged. Leave: hidden again. Click: the panel and the
    hash (``band=``), lit after the pointer leaves; click again: unlit."""
    with browser(band_tree(tmp_path / "g"), tmp_path / "site") as pg:
        lays = layouts_in(pg)
        rest = pg.evaluate(BAND_STATE)
        before = pg.evaluate(SNAPSHOT)
        pill = pg.locator(f'svg.band g.node[data-node="{CRUX}"]')
        pill.hover()
        hovered = pg.evaluate(BAND_STATE)
        hovered_main = pg.evaluate(SNAPSHOT)
        pg.mouse.move(5, 5)
        left = pg.evaluate(BAND_STATE)
        pill.click()
        pg.mouse.move(5, 5)
        clicked = pg.evaluate(BAND_STATE)
        pill.click()
        pg.mouse.move(5, 5)
        again = pg.evaluate(BAND_STATE)
    assert CRUX not in lays["all"]["nodes"] and "band" not in lays
    assert rest["band"] is not None and [b[0] for b in rest["band"]] == [CRUX]
    # At rest no band line is visible: not displayed, no path, a zero box (getBBox).
    assert [(ln["key"], ln["shown"], ln["d"], ln["box"]) for ln in rest["links"]] == [
        (f"{CRUX}>{THIRD}", False, "", [0, 0])
    ]
    (link,) = hovered["links"]
    assert link["shown"] and link["lit"] and link["d"].startswith("M") and link["box"][1] > 0
    assert (
        hovered["mainHovering"] and hovered["mainLit"] == [THIRD] and hovered["mainLitEdges"] == []
    )
    assert lit_nodes(hovered_main) == {THIRD} and lit_edges(hovered_main) == set()
    assert hovered["band"] == [[CRUX, rest["band"][0][1], True]], "lit, and not moved"
    assert boxes(hovered_main) == boxes(before)
    assert not left["links"][0]["shown"] and not left["mainHovering"] and left["mainLit"] == []
    assert clicked["panel"] == [CRUX] and f"band={CRUX}" in clicked["hash"]
    assert clicked["links"][0]["lit"] and clicked["links"][0]["shown"], "a click keeps it lit"
    assert clicked["mainLit"] == [THIRD]
    assert not again["links"][0]["shown"] and "band=" not in again["hash"]


def test_the_band_never_moves_on_a_selection(tmp_path: Path) -> None:
    with browser(band_tree(tmp_path / "g"), tmp_path / "site") as pg:
        rest = pg.evaluate(BAND_STATE)
        pg.locator(f'svg.band g.node[data-node="{CRUX}"]').click()
        pg.mouse.move(5, 5)
        pinned = pg.evaluate(BAND_STATE)
        pg.locator(LEAF).nth(1).click()
        pg.mouse.move(5, 5)
        on_leaf = pg.evaluate(BAND_STATE)
        main = pg.evaluate(SNAPSHOT)
        pg.keyboard.press("Escape")
        pg.mouse.move(5, 5)
        back = pg.evaluate(BAND_STATE)
    assert main["view"] != "routes" and THIRD in main["nodes"] and main["nodes"][THIRD]["shown"]
    assert on_leaf["band"] == pinned["band"] == [[CRUX, rest["band"][0][1], True]]
    assert on_leaf["links"][0]["lit"], "the pinned line follows the tree node to its new place"
    assert back["band"][0][1] == rest["band"][0][1]
