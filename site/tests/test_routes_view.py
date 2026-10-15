"""F27-T3 (R10, R11; AC10, AC11): the problem page's Routes section.

The structure test reads the markup: a junction per route (AND), a diamond on each statement two
or more routes or variants could close (OR), one wedge per set a statement belongs to, proved
statements marked proved, and one table row per set with its counts. The browser test (Playwright,
``uv run --frozen --with playwright pytest site/tests/test_routes_view.py``; it skips without
Playwright, which proves nothing, so the evidence runs it) selects a row and checks that the set is
lit, the rest dimmed, that nothing moved, and that clearing restores every wedge.
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET, copy_graph
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_products import ROOT_NODE, nodes_dir

from opn_gate import products
from opn_site import model, render, routes_view

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
) -> dict[str, Any]:
    holes = [h for r in routes or [] for h in r]
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
            }
            for k, r in enumerate(routes or [])
        ],
        "circular": [{"claim": "x"}] if circular else [],
    }


def doc() -> dict[str, Any]:
    """Root ``t`` with three routes: ``[a, b]``, ``[b, c]`` (``b`` proved, ``c`` decomposed into
    ``c--h1``) and ``[d]`` with ``d`` refuted (dead); and a ``resolves`` variant ``v``. The sets
    are ``{a, b}``, ``{b, c--h1}`` (assembly ``c``) and ``{v}``."""
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


def g_of(html: str, node_id: str) -> str:
    m = re.search(rf'<g class="[^"]*" data-node="{re.escape(node_id)}".*?</g>(?:</a>)?', html, re.S)
    assert m is not None, node_id
    return m.group(0)


def test_routes_section_structure(tmp_path: Path) -> None:
    """AC10."""
    section = routes_view.section(doc(), [], href={}, prefix="t")
    html = section.html
    assert section.sets == 3
    assert '<section class="routes-section"' in html
    svg = re.search(r'<svg class="routes-svg".*?</svg>', html, re.S)
    assert svg is not None
    drawing = svg.group(0)
    # AND: one live junction per live route (t@1, t@2, t--c@1); the dead route is drawn dead.
    assert drawing.count('class="and-mark"') == 3
    assert drawing.count('<g class="junction live"') == 3
    assert drawing.count('<g class="junction dead"') == 1
    assert 'data-route="t@3"' in drawing and 'class="dead-mark"' in drawing
    # OR: only the root has two or more alternatives (three routes and a variant).
    assert drawing.count('class="or-mark"') == 1
    assert 'class="or-mark"' in g_of(drawing, "t")
    assert 'class="rnode st-open member root"' in g_of(drawing, "t")
    # Drawn: every statement on a way to the root, live or dead, and the resolves variant; not the
    # related variant.
    for v in ("t", "t--a", "t--b", "t--c", "t--c--h1", "t--d", "v"):
        assert f'data-node="{v}"' in drawing, v
    assert 'data-node="u"' not in drawing
    # Wedges: one per set whose plan uses the statement, as a leaf or as an interior node it
    # passes through (F27-T8, the owner: no separate mark for an interior node; whether it is a
    # leaf is read from the drawing). The root is interior to the two route sets, not to {v}.
    wedges = {
        v: len(re.findall(r'class="wedge [^"]*" data-set=', g_of(drawing, v)))
        for v in ("t", "t--a", "t--b", "t--c", "t--c--h1", "t--d", "v")
    }
    assert wedges == {"t": 2, "t--a": 1, "t--b": 2, "t--c": 1, "t--c--h1": 1, "t--d": 0, "v": 1}
    # Proved, open, dead on their own classes; an interior node looks like any other.
    assert 'class="rnode st-proved member"' in g_of(drawing, "t--b")
    assert 'class="rnode st-open member"' in g_of(drawing, "t--a")
    assert 'class="rnode st-dead none"' in g_of(drawing, "t--d")
    assert 'class="rnode st-open member"' in g_of(drawing, "t--c")
    assert 'class="asm"' not in drawing
    # Every line names its two ends.
    for m in re.finditer(r"<path class=\"rline[^\"]*\"([^>]*)>", drawing):
        assert 'data-from="' in m.group(1) and 'data-to="' in m.group(1)
    # The table: one row per set, in the record's order, with its counts.
    rows = re.findall(r'<tr class="set-row".*?</tr>', html, re.S)
    assert len(rows) == 3

    def counts(row: str) -> list[int]:
        return [int(x) for x in re.findall(r'<td class="num" data-sort="(\d+)"', row)]

    # total, proved, open, shared, assemblies
    assert counts(rows[0]) == [2, 1, 1, 1, 1]
    assert counts(rows[1]) == [2, 1, 1, 1, 2]
    assert counts(rows[2]) == [1, 0, 1, 0, 0]
    assert "labelled circular" in rows[1]
    assert "goes through the variant" in rows[2]
    # The legend names every mark the drawing can show, inside the drawing's card.
    legend = html[html.index('class="routes-legend"') : html.index('class="routes-scroll"')]
    assert "assembly" not in legend
    for words in (
        "(AND)",
        "(OR)",
        "closes nothing",
        "proved",
        "open",
        "refuted",
        "no set",
    ):
        assert words in legend, words
    # The controls that need the script are rendered hidden.
    assert re.search(r'<button[^>]*class="routes-fewest"[^>]*hidden', html)
    assert "Fewest open first" in html
    for word in ("closest", "easiest", "best"):
        assert word not in html.lower(), word


def test_ids_are_escaped(tmp_path: Path) -> None:
    d = doc()
    d["nodes"][1]["node_id"] = 't--a"<x>'
    d["nodes"][0]["decompositions"][0]["holes"][0]["node"] = 't--a"<x>'
    d["nodes"][0]["deps"][0] = 't--a"<x>'
    html = routes_view.section(d, [], href={}, prefix="t").html
    assert "<x>" not in html and '"<x' not in html
    assert "t--a&quot;&lt;x&gt;" in html


def test_more_than_eight_sets_are_grey_and_the_section_says_so() -> None:
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
    html = routes_view.section(d, [], href={}, prefix="t").html
    assert html.count('<tr class="set-row"') == 10
    # Sets 9 and 10 are grey on their holes and on the root they pass through (F27-T8).
    assert html.count('class="wedge set-more"') == 4
    assert 'class="set-swatch set-8"' in html and 'class="set-swatch set-more"' in html
    assert "beyond the 8th are drawn grey" in html


def test_a_target_with_no_route_has_no_section() -> None:
    d = doc()
    for n in d["nodes"]:
        n["decompositions"] = []
    assert routes_view.section(d, [], href={}, prefix="t").html == ""


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


def test_the_problem_page_carries_the_section_after_the_statement_graph(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path))[f"problems/{TARGET}/index.html"]
    assert page.index('class="statements-section"') < page.index('class="routes-section"')
    assert '<script src="/routes.js"></script>' in page
    assert page.count('<tr class="set-row"') == 2
    drawing = page[page.index('<svg class="routes-svg"') :]
    drawing = drawing[: drawing.index("</svg>")]
    assert drawing.count('class="and-mark"') == 2 and drawing.count('class="or-mark"') == 1
    for hole in (*HOLE_IDS, THIRD):
        assert len(re.findall(r'class="wedge ', g_of(drawing, hole))) == 1, hole


def test_a_problem_page_without_routes_has_no_section(tmp_path: Path) -> None:
    page = render_tree(copy_graph(tmp_path, publish=True))[f"problems/{TARGET}/index.html"]
    assert "routes-section" not in page and "/routes.js" not in page


# -- the browser --------------------------------------------------------------------------------


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


#: Every node's box, every element's lit and dimmed state, and every wedge's.
SNAPSHOT = """() => {
  const svg = document.querySelector('svg.routes-svg');
  const box = el => { const r = el.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; };
  const out = {boxes: {}, lit: [], dim: [], wedgesOff: 0, wedges: 0};
  svg.querySelectorAll('[data-node]').forEach(g => {
    const id = g.getAttribute('data-node');
    out.boxes[id] = box(g);
    const o = parseFloat(getComputedStyle(g).opacity);
    (o > 0.9 ? out.lit : out.dim).push(id);
  });
  svg.querySelectorAll('.wedge').forEach(w => {
    out.wedges += 1;
    const o = parseFloat(getComputedStyle(w).opacity);
    if (w.classList.contains('off') || o < 0.9) out.wedgesOff += 1;
  });
  return out;
}"""


def test_selection_lights_one_set_and_layout_is_fixed(tmp_path: Path) -> None:  # noqa: PLR0915 — one browser session, each state it passes through
    """AC11, F27-T7: the first set is selected when the page loads, its label highlighted and its
    statements and lines lit; clicking another set's label in the drawing selects that one;
    clicking it again, or Escape, clears; a row still previews and selects; nothing moves."""
    sync_api = pytest.importorskip("playwright.sync_api")
    out = tmp_path / "site"
    render.write(render_tree(two_routes(tmp_path / "g")), out)
    handler = functools.partial(Quiet, directory=str(out))

    def members(pg: Any, set_id: str) -> list[str]:
        found: list[str] = pg.evaluate(
            "id => [...document.querySelectorAll('svg.routes-svg [data-node]')]"
            ".filter(g => (g.getAttribute('data-sets') || '').split(' ').includes(id))"
            ".map(g => g.getAttribute('data-node'))",
            set_id,
        )
        return found

    def pressed(pg: Any) -> list[str]:
        found: list[str] = pg.evaluate(
            "() => [...document.querySelectorAll('svg.routes-svg .set-label.selected')]"
            ".map(g => g.getAttribute('data-set'))"
        )
        return found

    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.emulate_media(reduced_motion="reduce")
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/")
            pg.wait_for_load_state("networkidle")
            pg.locator(".routes-section").scroll_into_view_if_needed()
            labels = pg.locator("svg.routes-svg .set-label")
            first_id = labels.nth(0).get_attribute("data-set")
            second_id = labels.nth(1).get_attribute("data-set")
            assert first_id and second_id
            loaded = pg.evaluate(SNAPSHOT)
            loaded_pressed = pressed(pg)
            first_members = members(pg, first_id)
            lit_lines = pg.evaluate(
                "() => document.querySelectorAll('svg.routes-svg .rline.lit').length"
            )
            row_selected = pg.locator("tr.set-row").nth(0).get_attribute("aria-selected")
            labels.nth(1).click()
            pg.mouse.move(5, 5)
            second = pg.evaluate(SNAPSHOT)
            second_pressed = pressed(pg)
            second_members = members(pg, second_id)
            labels.nth(1).click()
            pg.mouse.move(5, 5)
            cleared = pg.evaluate(SNAPSHOT)
            cleared_pressed = pressed(pg)
            # A row still previews on hover and selects on click; Escape clears.
            rows = pg.locator("tr.set-row")
            rows.nth(0).hover()
            hovered = pg.evaluate(SNAPSHOT)
            rows.nth(0).click()
            pg.mouse.move(5, 5)
            by_row = pressed(pg)
            pg.keyboard.press("Escape")
            escaped = pg.evaluate(SNAPSHOT)
            b.close()
    assert loaded_pressed == [first_id]
    assert row_selected == "true"
    assert sorted(loaded["lit"]) == sorted(first_members)
    assert loaded["dim"], "nothing was dimmed on load"
    assert loaded["wedgesOff"] > 0
    # The first set is [h1, h2] with the root's first route: h3 and the second route are dimmed.
    assert HOLE_IDS[0] in first_members and HOLE_IDS[1] in first_members
    assert THIRD not in first_members
    assert f"{ROOT_NODE}@1" in first_members and f"{ROOT_NODE}@2" not in first_members
    assert lit_lines == 3  # root to junction, junction to h1 and to h2
    assert second_pressed == [second_id]
    assert sorted(second["lit"]) == sorted(second_members)
    assert THIRD in second_members
    assert cleared_pressed == [] and cleared["dim"] == [] and cleared["wedgesOff"] == 0
    assert sorted(hovered["lit"]) == sorted(first_members)
    assert by_row == [first_id]
    assert escaped["dim"] == [] and escaped["wedgesOff"] == 0
    for snap in (second, cleared, hovered, escaped):
        assert snap["boxes"] == loaded["boxes"], "a node moved"


def test_set_labels_are_inside_the_drawing() -> None:
    """F27-T7: one label per set, stacked down the drawing's left edge inside the SVG, in the
    table's order, each naming its set and a button a keyboard can reach; the statements sit to
    the right of the column, so no label covers one."""
    html = routes_view.section(doc(), [], href={}, prefix="t").html
    start = html.index('<svg class="routes-svg"')
    drawing = html[start : html.index("</svg>", start)]
    tags = re.findall(r'<g class="set-label[^"]*"[^>]*>.*?</g>', drawing, re.S)
    rows = re.findall(r'<tr class="set-row[^"]*" data-set="([^"]+)"', html)
    assert len(tags) == len(rows) >= 2
    ys = []
    for k, (tag, sid) in enumerate(zip(tags, rows, strict=True), start=1):
        assert f'data-set="{sid}"' in tag
        assert 'role="button"' in tag and 'tabindex="0"' in tag
        assert f">Set {k}<" in tag
        m = re.search(r'transform="translate\(([\d.]+),([\d.]+)\)"', tag)
        assert m is not None
        assert float(m.group(1)) < routes_view.LABEL_COLUMN
        ys.append(float(m.group(2)))
    assert ys == sorted(ys) and len(set(ys)) == len(ys), "labels are not stacked vertically"
    xs = [
        float(x)
        for x in re.findall(r'<g class="rnode[^"]*"[^>]*transform="translate\(([\d.]+),', drawing)
    ]
    assert xs and min(xs) >= routes_view.LABEL_COLUMN, "a statement sits under the label column"


def test_a_closable_statement_is_marked_never_as_proved() -> None:
    """F28-T4 (R12; v3.41): with ``t--c--h1`` proved, ``t--c`` is closable now and the root once
    ``t--c``'s closing proof merges. Each is marked closable, says what its closing proof waits
    on, keeps the open look (never the proved one), and is named under the drawing; the key
    names the mark. A statement that is not closable carries no mark."""
    d = doc()
    for n in d["nodes"]:
        if n["node_id"] == "t--c--h1":
            n["status"] = "proved"
    html = routes_view.section(d, [], href={}, prefix="t").html
    c = g_of(html, "t--c")
    assert "closable" in c.split('"')[1] and "st-open" in c.split('"')[1]
    assert "closable: its closing proof is pending" in c
    root = g_of(html, "t")
    assert "closable" in root.split('"')[1]
    assert "closable once the closing proof of t--c merges" in root
    for other in ("t--a", "t--b", "t--c--h1", "t--d"):
        assert "closable" not in g_of(html, other).split('"')[1], other
    assert "closable: its proof exists in parts" in html
    listed = re.search(r'<p class="routes-closable">.*?</p>', html, re.S)
    assert listed is not None
    # named with the drawing's own short labels: the root ``t`` and ``c`` for ``t--c``
    assert '>t</a>, <a href="#">c</a>' in listed.group(0)
    assert "nothing is proved until" in listed.group(0)


def test_nothing_closable_means_no_mark_and_no_line() -> None:
    html = routes_view.section(doc(), [], href={}, prefix="t").html
    assert 'class="routes-closable"' not in html
    assert not re.search(r'<g class="rnode[^"]*closable', html)
