"""F04-T33 (Q34): the statement graph is drawn so that lines do not cross or run behind pills.

The finding (Mike, 2026-10-04): on the live erdos-69 page sixteen pairs of lines crossed and
forty-three times a line ran behind a statement it does not join, so a reader could not tell
which statement a line belonged to. F04-Q3 had chosen lexical order and straight lines. The
four live shapes that crossed are in ``dag_live_shapes.json`` (trimmed ``graph.json``, the
commit named in the file); every one can be drawn with no crossing at all.

The same sitting's other changes to the drawing, each owned by a test below: statements joined
to nothing are drawn apart from the tree; a pill drops the problem's own name from its label;
superseded statements are faded and can be hidden; hovering a statement lights its lines; and
the key names every kind of line the drawing shows.
"""

from __future__ import annotations

import dataclasses
import json
import re
from itertools import pairwise
from pathlib import Path
from typing import Any

import fixture
import pytest

from opn_site import dag, model, render

HERE = Path(__file__).resolve().parent
STATIC = Path(render.__file__).resolve().parent / "static"
SHAPES: dict[str, dict[str, Any]] = json.loads(
    (HERE / "dag_live_shapes.json").read_text(encoding="utf-8")
)["targets"]
LIVE = sorted(SHAPES)

Point = tuple[float, float]


def drawn(target: str) -> dag.Layout:
    shape = SHAPES[target]
    return dag.layout(shape["nodes"], root=shape["root"], prefix=target)


def segments(edge: dag.Edge) -> list[tuple[Point, Point]]:
    pts = dag.curve_points(edge)
    return list(pairwise(pts))


def _ccw(a: Point, b: Point, c: Point) -> float:
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def _cross(s: tuple[Point, Point], t: tuple[Point, Point]) -> bool:
    (a, b), (c, d) = s, t
    d1, d2, d3, d4 = _ccw(c, d, a), _ccw(c, d, b), _ccw(a, b, c), _ccw(a, b, d)
    return d1 * d2 < 0 and d3 * d4 < 0


def crossings(lay: dag.Layout) -> list[tuple[str, str, str, str]]:
    out = []
    for i, e in enumerate(lay.edges):
        for f in lay.edges[i + 1 :]:
            if {e.src, e.dst} & {f.src, f.dst}:
                continue  # lines that share a statement meet there by design
            if any(_cross(s, t) for s in segments(e) for t in segments(f)):
                out.append((e.src, e.dst, f.src, f.dst))
    return out


def behind_pills(lay: dag.Layout) -> list[tuple[str, str, str]]:
    """Every (line, pill) where the drawn line enters a pill it does not join."""
    out = []
    for e in lay.edges:
        pts: list[Point] = []
        for (x1, y1), (x2, y2) in segments(e):
            pts.extend((x1 + (x2 - x1) * k / 8, y1 + (y2 - y1) * k / 8) for k in range(9))
        for p in lay.placed:
            if p.node_id in (e.src, e.dst):
                continue
            if any(
                p.x + 1 < x < p.x + p.w - 1 and p.y + 1 < y < p.y + dag.NODE_H - 1 for x, y in pts
            ):
                out.append((e.src, e.dst, p.node_id))
    return out


# --- 1. crossings and lines behind pills ---------------------------------------------------------


@pytest.mark.parametrize("target", LIVE)
def test_no_two_lines_cross_on_the_live_shapes(target: str) -> None:
    assert crossings(drawn(target)) == []


@pytest.mark.parametrize("target", LIVE)
def test_no_line_runs_behind_a_statement_it_does_not_join(target: str) -> None:
    assert behind_pills(drawn(target)) == []


@pytest.mark.parametrize("target", LIVE)
def test_every_dependency_is_still_drawn_once(target: str) -> None:
    """The routing changes the lines' shape, never which lines exist."""
    nodes = SHAPES[target]["nodes"]
    ids = {n["node_id"] for n in nodes}
    pointed = dag.pointers(nodes)
    want = set()
    for n in nodes:
        for d in dag.below(n):
            if d in ids:
                want.add((d, n["node_id"]))
        for c in pointed.get(n["node_id"], []):
            want.add((c, n["node_id"]))
    got = [(e.src, e.dst) for e in drawn(target).edges]
    assert sorted(got) == sorted(want)


@pytest.mark.parametrize("target", LIVE)
def test_every_line_runs_upward_from_the_lower_statement(target: str) -> None:
    lay = drawn(target)
    at = {p.node_id: p for p in lay.placed}
    for e in lay.edges:
        ys = [y for _x, y in e.points]
        assert ys == sorted(ys, reverse=True), e
        assert ys[0] == at[e.src].y and ys[-1] == at[e.dst].y + dag.NODE_H, e


# --- 2. placement --------------------------------------------------------------------------------


@pytest.mark.parametrize("target", LIVE)
def test_pills_stay_inside_the_drawing_and_never_overlap(target: str) -> None:
    lay = drawn(target)
    for p in lay.placed:
        assert p.x >= 0 and p.x + p.w <= lay.width and p.y + dag.NODE_H <= lay.height, p
    for a in lay.placed:
        for b in lay.placed:
            if a is not b and a.y == b.y:
                assert a.x + a.w <= b.x or b.x + b.w <= a.x, (a, b)


@pytest.mark.parametrize("target", LIVE)
def test_a_statement_sits_just_below_the_lowest_statement_that_rests_on_it(target: str) -> None:
    """A hole under its parent and a crux under the statement it was proposed for, not at the
    bottom of the drawing: on erdos-69 every crux sat in the bottom row and its pointer ran the
    whole height of the page, behind the statements between."""
    lay = drawn(target)
    layer = {p.node_id: p.layer for p in lay.placed}
    above: dict[str, list[str]] = {}
    for e in lay.edges:
        above.setdefault(e.src, []).append(e.dst)
    for src, dsts in above.items():
        assert min(layer[d] for d in dsts) == layer[src] + 1, (src, dsts)


def test_a_chain_of_single_steps_stands_upright() -> None:
    """``a`` rests on ``a1`` alone and nothing else rests on ``a1``: one column, even though
    ``a`` shares its row with ``b`` and ``a1`` is alone in its own."""
    nodes: list[dict[str, Any]] = [
        {"node_id": "r", "status": "ready", "deps": ["a", "b"]},
        {"node_id": "a", "status": "ready", "deps": ["a1"]},
        {"node_id": "a1", "status": "proved", "deps": []},
        {"node_id": "b", "status": "proved", "deps": []},
    ]
    at = {p.node_id: p for p in dag.layout(nodes, root="r").placed}
    assert abs((at["a"].x + at["a"].w / 2) - (at["a1"].x + at["a1"].w / 2)) <= 1


@pytest.mark.parametrize("target", LIVE)
def test_the_layout_does_not_depend_on_input_order(target: str) -> None:
    shape = SHAPES[target]
    href = {n["node_id"]: "/x/" for n in shape["nodes"]}
    a = dag.svg(shape["nodes"], href=href, root=shape["root"], prefix=target)
    b = dag.svg(list(reversed(shape["nodes"])), href=href, root=shape["root"], prefix=target)
    assert a == b


# --- 3. statements joined to nothing --------------------------------------------------------------


def test_statements_joined_to_nothing_are_drawn_apart_below_the_tree() -> None:
    lay = drawn("erdos-402")
    joined = {x for e in lay.edges for x in (e.src, e.dst)}
    alone = {p.node_id for p in lay.placed if p.node_id not in joined}
    assert alone and set(lay.loose) == alone
    tree_bottom = max(p.y for p in lay.placed if p.node_id in joined)
    assert all(p.y > tree_bottom + dag.NODE_H for p in lay.placed if p.node_id in lay.loose)


def test_superseded_statements_come_last_in_the_apart_group() -> None:
    """Hiding them then shortens the last row instead of leaving holes in the grid."""
    loose = drawn("erdos-69").loose
    status = {n["node_id"]: n["status"] for n in SHAPES["erdos-69"]["nodes"]}
    kinds = [status[v] == "superseded" for v in loose]
    assert kinds == sorted(kinds) and any(kinds) and not all(kinds)


def test_the_root_stays_in_the_tree_even_when_nothing_joins_it() -> None:
    nodes: list[dict[str, Any]] = [
        {"node_id": "r", "status": "ready", "deps": []},
        {"node_id": "a", "status": "proved", "deps": []},
        {"node_id": "b", "status": "ready", "deps": ["a"]},
    ]
    assert dag.layout(nodes, root="r").loose == ()


def test_a_graph_with_no_lines_is_drawn_as_one_group() -> None:
    nodes: list[dict[str, Any]] = [
        {"node_id": n, "status": "ready", "deps": []} for n in ("r", "v1", "v2")
    ]
    lay = dag.layout(nodes, root="r")
    assert lay.loose == ()
    out = dag.svg(nodes, href={n["node_id"]: "/x/" for n in nodes}, root="r")
    assert "dag-group" not in out


def test_the_apart_group_is_labelled_in_the_drawing() -> None:
    shape = SHAPES["erdos-402"]
    out = dag.svg(
        shape["nodes"],
        href={n["node_id"]: "/x/" for n in shape["nodes"]},
        root=shape["root"],
        prefix="erdos-402",
    )
    assert re.search(r'<text class="dag-group"[^>]*>[^<]*no line[^<]*</text>', out)


# --- 4. labels -----------------------------------------------------------------------------------


def test_a_label_drops_the_problems_own_name() -> None:
    nodes: list[dict[str, Any]] = [
        {"node_id": "erdos-69", "status": "ready", "deps": ["erdos-69--h2-v2"]},
        {"node_id": "erdos-69--h2-v2", "status": "ready", "deps": []},
        {"node_id": "spec-2e765953", "status": "proved", "deps": ["erdos-69"]},
    ]
    out = dag.svg(
        nodes, href={n["node_id"]: "/x/" for n in nodes}, root="erdos-69", prefix="erdos-69"
    )
    labels = set(re.findall(r'<text x="28"[^>]*>([^<]+)</text>', out))
    assert labels == {"erdos-69", "h2-v2", "spec-2e765953"}
    assert "<title>erdos-69--h2-v2: ready</title>" in out
    assert dag.node_width("erdos-69--h2-v2", prefix="erdos-69") == dag.node_width("h2-v2")


def test_a_label_drops_the_roots_own_name_too() -> None:
    """euclid-primes: the root is ``infinitude-of-primes`` and its holes are named after it."""
    shape = SHAPES["euclid-primes"]
    out = dag.svg(
        shape["nodes"],
        href={n["node_id"]: "/x/" for n in shape["nodes"]},
        root=shape["root"],
        prefix="euclid-primes",
    )
    labels = set(re.findall(r'<text x="28"[^>]*>([^<]+)</text>', out))
    assert {"infinitude-of-primes", "h1", "h4", "variant-2a7919a9--h1"} <= labels
    assert "infinitude-of-primes--h1" not in labels


def test_without_a_prefix_a_label_is_the_id_as_before() -> None:
    nodes = [{"node_id": "erdos-69--h2-v2", "status": "ready", "deps": []}]
    out = dag.svg(nodes, href={"erdos-69--h2-v2": "/x/"})
    assert ">erdos-69--h2-v2</text>" in out


def test_the_problem_page_draws_short_labels(tmp_path: Path) -> None:
    html = page(tmp_path)
    assert "drop the problem" in html  # the caption says so


# --- 5. superseded statements ---------------------------------------------------------------------


def test_lines_to_a_superseded_statement_say_so() -> None:
    nodes: list[dict[str, Any]] = [
        {"node_id": "r", "status": "ready", "deps": ["h1", "h1-v2"]},
        {"node_id": "h1", "status": "superseded", "deps": []},
        {"node_id": "h1-v2", "status": "ready", "deps": []},
    ]
    out = dag.svg(nodes, href={n["node_id"]: "/x/" for n in nodes}, root="r")
    edges = dict(
        ((f, t), c)
        for c, f, t in re.findall(
            r'<path class="([^"]+)" data-from="([^"]+)" data-to="([^"]+)"', out
        )
    )
    assert "touches-superseded" in edges[("h1", "r")]
    assert "touches-superseded" not in edges[("h1-v2", "r")]


def page(tmp_path: Path, statuses: dict[str, str] | None = None, **graph: Any) -> str:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets["propositional"]
    nodes = dict(tv.nodes)
    for node_id, status in (statuses or {}).items():
        nv = nodes[node_id]
        nodes[node_id] = dataclasses.replace(nv, graph_entry={**nv.graph_entry, "status": status})
    g = {**tv.graph, **graph}
    if statuses:
        g["nodes"] = [{**n, "status": statuses.get(n["node_id"], n["status"])} for n in g["nodes"]]
    r = render.Renderer(site, repo_url="https://github.com/example/graph", decisions_doc=None)
    return r.target(dataclasses.replace(tv, nodes=nodes, graph=g))


def test_the_page_offers_to_hide_superseded_statements_when_it_has_any(tmp_path: Path) -> None:
    html = page(tmp_path / "a", {"and-reassoc": "superseded"})
    assert re.search(r'<button type="button" class="chip dag-toggle" data-hide="superseded"', html)
    assert 'data-hide="superseded"' not in page(tmp_path / "b")


def test_superseded_statements_are_faded_and_the_toggle_hides_them() -> None:
    css = (STATIC / "site.css").read_text(encoding="utf-8")
    assert re.search(r"\.dag \.node\.status-superseded \{[^}]*opacity", css)
    assert re.search(r"\.dag\.hide-superseded \.status-superseded[^{]*\{[^}]*display: none", css)
    assert re.search(r"\.dag\.hide-superseded \.touches-superseded[^{]*\{[^}]*display: none", css)
    js = (STATIC / "problem.js").read_text(encoding="utf-8")
    assert "hide-superseded" in js and "data-hide" in js


# --- 6. hover ------------------------------------------------------------------------------------


def test_hovering_a_statement_lights_its_lines() -> None:
    js = (STATIC / "problem.js").read_text(encoding="utf-8")
    assert "mouseenter" in js and "focusin" in js and "hovering" in js
    css = (STATIC / "site.css").read_text(encoding="utf-8")
    assert re.search(r"\.dag\.hovering \.edge:not\(\.lit\)[^{]*\{[^}]*opacity", css)
    assert re.search(r"\.dag\.hovering \.node:not\(\.lit\)[^{]*\{[^}]*opacity", css)


# --- 7. the key names every kind of line ----------------------------------------------------------


def legend(html: str) -> str:
    m = re.search(r'<div class="dag-legend">(.*?)</div>', html, re.S)
    assert m is not None
    return m.group(1)


def test_the_key_names_the_solid_line(tmp_path: Path) -> None:
    word = render.GLOSSARY_BY_KEY["depends-on"][0]
    assert f'<span class="dot dot-depends-on"></span>{word}' in legend(page(tmp_path))


def test_the_key_names_a_used_lemma_even_before_a_proof_is_selected(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets["propositional"]
    nodes: list[dict[str, Any]] = [
        {**n, "uses": ["and-reassoc"]} if n["node_id"] == "tutorial-and-swap" else n
        for n in tv.graph["nodes"]
    ]
    tv = dataclasses.replace(tv, graph={**tv.graph, "nodes": nodes, "target_proofs": []})
    assert "use" in render.Renderer.proof_legend(tv)


def test_a_line_off_the_selected_proof_is_dimmed_not_dashed() -> None:
    """Dashes mean a used lemma; a line the selected proof does not need is only dimmed."""
    css = (STATIC / "site.css").read_text(encoding="utf-8")
    rule = re.search(r"^\.dag \.edge\.off-proof \{[^}]*\}", css, re.M)
    assert rule is None or "dasharray" not in rule.group(0)
    assert re.search(r"^\.dag \.edge \{[^}]*fill: none", css, re.M)
