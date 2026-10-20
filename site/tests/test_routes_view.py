"""F27-T3 (R11; AC10, AC11), restated by F30-T2: the routes' marks and the sets table.

The routes drawing and its selector box were folded into the problem page's one statement graph
(F30, ``opn_site.one_view``; F27-R10 and F29-R10 superseded, F30-Q1). What this file keeps: the
hand-made graph documents every shape has a mark for, the ``two_routes`` fixture tree, and the
tests of the marks and the table as the merged drawing now carries them: a junction per route
(AND), a diamond on a statement two or more routes could close (OR), a dead route drawn dead,
closable marked and never proved, one table row per set with its counts, ids escaped. The
browser behaviour is F30-T3's (``test_one_view.py``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fixture
from harness import TARGET, copy_graph
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_products import ROOT_NODE, nodes_dir

from opn_gate import products
from opn_site import model, one_view, render

REPO = "https://github.com/example/graph"
THIRD = f"{ROOT_NODE}--h3"


# -- a graph document by hand: every shape the drawing has a mark for ---------------------------


def node(
    node_id: str,
    status: str = "ready",
    *,
    origin: str = "skeleton-hole",
    relation: str | None = None,
    routes: list[list[str]] | None = None,
    deps: list[str] | None = None,
    circular: bool = False,
    approaches: list[str | None] | None = None,
) -> dict[str, Any]:
    """``circular`` gives the row an older snapshot's ``graph/v9`` label (F04-T53: ignored);
    ``approaches`` (F29-R4) the routes' declared approaches, ``None`` where a partial declared
    none (an older pin)."""
    holes = [h for r in routes or [] for h in r]
    approaches = approaches or [None] * len(routes or [])
    return {
        "node_id": node_id,
        "status": status,
        "deps": list(dict.fromkeys([*(deps or []), *holes])),
        "origin": origin,
        "relation": relation,
        "decompositions": [
            {
                "partial": f"attempts/2026101{k}T000000Z-a-partial.lean",
                "annex": None,
                "holes": [{"name": f"h{i + 1}", "node": h} for i, h in enumerate(r)],
                "approach": approaches[k],
            }
            for k, r in enumerate(routes or [])
        ],
        "circular": [{"claim": "x"}] if circular else [],
    }


def doc() -> dict[str, Any]:
    """Root ``t`` with three routes: ``[a, b]``, ``[b, c]`` (``b`` proved, ``c`` decomposed into
    ``c--h1``) and ``[d]`` with ``d`` refuted (dead); and a ``resolves`` variant ``v``. The sets
    are ``{a, b}``, ``{b, c--h1}`` (assembly ``c``) and ``{v}``. ``c--h1`` carries an older
    snapshot's circularity label, which the section ignores (F04-T53, D-12 v3.43)."""
    return {
        "schema": "graph/v9",
        "target_id": "t",
        "root": "t",
        "nodes": [
            node("t", origin="authored", routes=[["t--a", "t--b"], ["t--b", "t--c"], ["t--d"]]),
            node("t--a"),
            node("t--b", "proved"),
            node("t--c", routes=[["t--c--h1"]]),
            node("t--c--h1", circular=True),
            node("t--d", "refuted"),
            node("v", origin="authored", relation="resolves"),
            node("u", origin="authored", relation="related"),
        ],
    }


SPLIT = "Split at the conjunction and bound each half"
THROUGH_C = "Go through c instead"
DENSITY = "Bound the density of the set"


def nested_doc() -> dict[str, Any]:
    """F29-T6: root ``t`` with two routes, ``[a, b]`` and ``[c]``, and ``a`` itself split two
    ways, ``[a--h1]`` and ``[a--h2]``; the second route of ``a`` declares no approach (an older
    partial). The finest sets are ``{a--h1, b}``, ``{a--h2, b}`` and ``{c}``, so the selector
    tree splits on ``t`` into a branch (``t@1``, split again on ``a`` into two leaves) and a
    leaf (``t@2``)."""
    return {
        "schema": "graph/v12",
        "target_id": "t",
        "root": "t",
        "nodes": [
            node(
                "t",
                origin="authored",
                routes=[["t--a", "t--b"], ["t--c"]],
                approaches=[SPLIT, THROUGH_C],
            ),
            node("t--a", routes=[["t--a--h1"], ["t--a--h2"]], approaches=[DENSITY, None]),
            node("t--a--h1"),
            node("t--a--h2"),
            node("t--b"),
            node("t--c"),
        ],
    }


def g_of(html: str, node_id: str) -> str:
    m = re.search(rf'<g class="[^"]*" data-node="{re.escape(node_id)}".*?</g>(?:</a>)?', html, re.S)
    assert m is not None, node_id
    return m.group(0)


def drawn(d: dict[str, Any]) -> one_view.Drawing:
    return one_view.drawing(d, [], href={n["node_id"]: "#" for n in d["nodes"]}, prefix="t")


def test_routes_marks_and_table_structure() -> None:
    """AC10, as the merged drawing carries it (F30-R1)."""
    picture = drawn(doc())
    drawing, table = picture.svg, picture.table
    assert picture.sets == 3
    # AND: one live junction per live route (t@1, t@2, t--c@1); the dead route is drawn dead.
    assert drawing.count('class="and-mark"') == 3
    assert drawing.count('<g class="junction live"') == 3
    assert drawing.count('<g class="junction dead"') == 1
    assert 'data-route="t@3"' in drawing and 'class="dead-mark"' in drawing
    # OR: only the root has two or more alternatives (three routes and a variant).
    assert drawing.count('class="or-mark"') == 1
    assert 'class="or-mark"' in g_of(drawing, "t")
    # Drawn and shown: every statement on a way to the root, live or dead, and the resolves
    # variant; the related variant is in the markup but off the opening view (F30-R4).
    for v in ("t", "t--a", "t--b", "t--c", "t--c--h1", "t--d", "v"):
        assert f'data-node="{v}"' in drawing and "off-view" not in g_of(drawing, v), v
    assert "off-view" in g_of(drawing, "u")
    # Proved is the filled pill; open and dead keep their status classes; no set colours.
    assert 'class="node status-proved proved"' in g_of(drawing, "t--b")
    assert 'class="node status-ready"' in g_of(drawing, "t--a")
    assert 'class="node status-refuted"' in g_of(drawing, "t--d")
    assert 'class="wedge' not in drawing and "data-sets" not in drawing
    assert 'class="asm"' not in drawing
    # Every line names its two ends and its key.
    for m in re.finditer(r"<path class=\"edge[^\"]*\"([^>]*)>", drawing):
        assert 'data-from="' in m.group(1) and 'data-to="' in m.group(1), m.group(0)
        assert 'data-key="' in m.group(1)
    # The table: one row per set, in the record's order, with its counts and its leaf view.
    rows = re.findall(r'<tr class="set-row".*?</tr>', table, re.S)
    assert len(rows) == 3

    def counts(row: str) -> list[int]:
        return [int(x) for x in re.findall(r'<td class="num" data-sort="(\d+)"', row)]

    # total, proved, open, shared, assemblies
    assert counts(rows[0]) == [2, 1, 1, 1, 1]
    assert counts(rows[1]) == [2, 1, 1, 1, 2]
    assert counts(rows[2]) == [1, 0, 1, 0, 0]
    assert all('data-view="sel' in r for r in rows)
    assert "circular" not in rows[1]  # F04-T53 (D-12 v3.43): no label, no note
    assert "goes through the variant" in rows[2]
    # The key terms the drawing asks for (F30-R2).
    assert picture.marks == frozenset({"route-and", "route-or", "route-dead"})
    # The controls that need the script are rendered hidden.
    assert re.search(r'<button[^>]*class="routes-fewest"[^>]*hidden', table)
    assert "Fewest open first" in table
    for word in ("closest", "easiest", "best"):
        assert word not in table.lower(), word


def test_ids_are_escaped() -> None:
    d = doc()
    d["nodes"][1]["node_id"] = 't--a"<x>'
    d["nodes"][0]["decompositions"][0]["holes"][0]["node"] = 't--a"<x>'
    d["nodes"][0]["deps"][0] = 't--a"<x>'
    picture = drawn(d)
    html = picture.svg + picture.selector + picture.table
    assert "<x>" not in html and '"<x' not in html
    assert "t--a&quot;&lt;x&gt;" in html


def test_more_than_eight_sets_are_listed_in_the_table() -> None:
    holes = [f"t--h{i}" for i in range(10)]
    d = {
        "schema": "graph/v9",
        "target_id": "t",
        "root": "t",
        "nodes": [
            node("t", origin="authored", routes=[[h] for h in holes]),
            *(node(h) for h in holes),
        ],
    }
    picture = drawn(d)
    assert picture.table.count('<tr class="set-row"') == 10
    assert 'class="set-swatch set-8"' in picture.table
    assert 'class="set-swatch set-more"' in picture.table
    assert picture.selector.count('class="sel-node kind-leaf"') == 10


def test_a_target_with_no_route_has_no_selector_and_no_table() -> None:
    d = doc()
    for n in d["nodes"]:
        n["decompositions"] = []
    picture = drawn(d)
    assert picture.selector == "" and picture.table == "" and picture.sets == 0
    assert picture.marks == frozenset()
    assert 'class="junction' not in picture.svg


def test_a_closable_statement_is_marked_never_as_proved() -> None:
    """F28-T4 (R12; v3.41): with ``t--c--h1`` proved, ``t--c`` is closable now and the root once
    ``t--c``'s closing proof merges. Each is marked closable, says what its closing proof waits
    on, keeps the open look (never the proved one); the key names the mark. A statement that is
    not closable carries no mark."""
    d = doc()
    for n in d["nodes"]:
        if n["node_id"] == "t--c--h1":
            n["status"] = "proved"
    picture = drawn(d)
    html = picture.svg
    c = g_of(html, "t--c")
    assert "closable" in c.split('"')[1] and "status-ready" in c.split('"')[1]
    assert "proved" not in c.split('"')[1]
    assert "closable: its closing proof is pending" in c
    root = g_of(html, "t")
    assert "closable" in root.split('"')[1]
    assert "closable once the closing proof of t--c merges" in root
    for other in ("t--a", "t--b", "t--c--h1", "t--d"):
        assert "closable" not in g_of(html, other).split('"')[1], other
    assert "closable" in picture.marks


def test_nothing_closable_means_no_mark() -> None:
    picture = drawn(doc())
    assert "closable" not in picture.marks
    assert not re.search(r'<g class="node[^"]*closable', picture.svg)


# -- the page -----------------------------------------------------------------------------------


def two_routes(tmp_path: Path) -> Path:
    """The fixture root, its proof taken out so it is open, split twice: ``[h1, h2]`` then
    ``[h3]``; two sets. (A hole shared by two partials is a lemma, F04-T39, which the hand-made
    document above covers; here each partial makes its own holes.)"""
    root = copy_graph(tmp_path, publish=True)
    (nodes_dir(root) / ROOT_NODE / "Proof.lean").unlink()
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    add_hole(root, THIRD, "hthree")
    merged_partial(root, 7, ["hden", "hrem"], annex=None)
    later = "attempts/20260924T000000Z-bob-partial.lean"
    merged_partial(root, 9, ["hthree"], path=later, annex=None)
    return root


def render_tree(root: Path) -> dict[str, str]:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_a_problem_page_without_routes_has_no_sets_block(tmp_path: Path) -> None:
    page = render_tree(copy_graph(tmp_path, publish=True))[f"problems/{TARGET}/index.html"]
    assert "sets-grid" not in page and "/routes.js" not in page
    assert 'id="graph-layouts"' in page  # the layouts are embedded for every target
