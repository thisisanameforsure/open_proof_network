"""F04-T55 (D-25 v3.46, D-30 v3.46, D-14 v3.26): the refuting side on the problem page.

A route may settle a conjecture either way. The relation edge from a ``refutes`` variant into the
root and the selector branch beneath the top fork's ``refutes`` side wear a second colour
(``--refute``), the key names it ("refutes the problem"), the sets are "ways to settle the
problem" and each says which way ("Set 1 (proves)", "Set 2 (refutes)"), the sets table says
"refutes" on a refuting row, and statements keep their one status colour. A root refuted through
a variant reads "disproved" with "a refuting variant is proved on the record", never "a
counterexample". Read through ``opn_gate.routes`` as F27-T11 built it (``settles``, ``side``) on
the hand fixture of the erdos-257 shape; a graph with a resolving variant only has one side and
no fork.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import fixture
import pytest
import refutes_fixture as rf
from test_routes_view import doc as resolves_doc

from opn_gate import routes
from opn_site import model, one_view, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
STATIC = Path(render.__file__).resolve().parent / "static"
CSS = (STATIC / "site.css").read_text(encoding="utf-8")


def hrefs(g: dict[str, Any]) -> dict[str, str]:
    return {n["node_id"]: f"/nodes/{n['node_id']}/" for n in g["nodes"]}


@pytest.fixture
def two_sides() -> dict[str, Any]:
    """The hand fixture as ``opn_gate.routes`` reads it since F27-T11 (D-25 v3.46): three sets,
    one proving and two refuting, the selector forked by side first (``refutes_fixture`` asserts
    that shape before the test runs)."""
    g = rf.doc()
    rf.tree(rf.result(g))
    return g


def drawn(g: dict[str, Any]) -> one_view.Drawing:
    return one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)


def token(name: str) -> str:
    m = re.search(rf"^\s*{re.escape(name)}:\s*([^;]+);", CSS, re.M)
    assert m is not None, name
    return m.group(1).strip().lower()


# -- 1. the colour and the stylesheet -----------------------------------------------------------


def test_the_refuting_colour_is_its_own_token() -> None:
    refute = token("--refute")
    assert re.fullmatch(r"#[0-9a-f]{6}", refute), refute
    others = {
        k: token(k)
        for k in (
            "--accent",
            "--select",
            "--lit-open",
            "--lit-known",
            "--lit-elementary",
            "--bad",
            "--warn",
        )
    }
    assert refute not in others.values(), others
    assert re.search(r"^\.dag \.edge\.relation\.refutes \{[^}]*var\(--refute\)", CSS, re.M)
    assert re.search(r"^\.dag \.edge\.relation\.resolves \{", CSS, re.M)
    assert re.search(r"\.selector \.sel-edge\.side-refutes[^{]*\{[^}]*var\(--refute\)", CSS)
    assert re.search(r"\.selector \.side-refutes \.dot[^{]*\{[^}]*var\(--refute\)", CSS)
    for key in ("relation-refutes", "relation-resolves"):
        assert f".dot-{key}" in CSS, key
    assert re.search(r"\.dot-relation-refutes \{[^}]*var\(--refute\)", CSS)
    # A statement is not refuting by itself: no pill rule keys on the side.
    assert not re.search(r"\.dag \.node[^{]*side-refutes", CSS)


# -- 2. the relation edge and the key -----------------------------------------------------------


def test_the_refuting_trunk_is_drawn_from_the_variant_into_the_root() -> None:
    """The trunk is drawn, in view, the key names it, and the variant keeps its status class."""
    d = drawn(rf.doc())
    path = re.search(
        rf'<path class="(edge relation refutes[^"]*)" data-from="{rf.VARIANT}" data-to="{rf.ROOT}"',
        d.svg,
    )
    assert path is not None and "off-view" not in path.group(1)
    assert "relation-refutes" in d.marks and "relation-resolves" not in d.marks
    assert re.search(rf'<g class="node status-ready" data-node="{rf.VARIANT}"', d.svg)


def test_the_resolving_trunk_is_drawn_and_keyed_too() -> None:
    d = one_view.drawing(resolves_doc(), [], href=hrefs(resolves_doc()), prefix="t")
    assert re.search(r'<path class="edge relation resolves[^"]*" data-from="v" data-to="t"', d.svg)
    assert "relation-resolves" in d.marks and "relation-refutes" not in d.marks


def test_the_key_names_the_sides_and_the_band_only_when_drawn(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    plain = r.graph_legend(tv, drawn(rf.doc()))
    assert "refutes the problem" in plain and "resolves the problem" not in plain
    # The key's label is the band's word; the old "proposed for" label is gone.
    assert '</span>proposed statement<span class="term-card"' in plain
    assert '</span>proposed for<span class="term-card"' not in plain
    bare = r.graph_legend(tv, drawn(resolves_doc()))
    assert "resolves the problem" in bare and "refutes the problem" not in bare
    assert "proposed statement" not in bare
    for key in ("relation-refutes", "relation-resolves"):
        assert key in render.GLOSSARY_BY_KEY and key in render.ROUTE_MARK_KEYS, key
    assert render.GLOSSARY_BY_KEY["proposed-for"][0] == "proposed statement"


# -- 3. the selector, the sets table and the words ----------------------------------------------


def test_the_selector_forks_by_side_and_colours_the_refuting_branch(
    two_sides: dict[str, Any],
) -> None:
    d = drawn(two_sides)
    assert d.sets == 3
    sel = d.selector
    words = dict(re.findall(r'data-key="([^"]+)" data-words="([^"]*)"', sel))
    assert words["sel/proves"].startswith("Set 1 (proves): 1 open statement of 2")
    assert "proves the problem" in words["sel/proves"]
    assert "refutes the problem" in words["sel/refutes"]
    assert words["sel/refutes/v@1"].startswith("Set 2 (refutes): 1 open statement of 4")
    assert words["sel/refutes/v@2"].startswith("Set 3 (refutes): 1 open statement of 1")
    assert "proving or refuting" in words["sel"]
    # The refuting branch: its node, its leaves and the edges into and under it, in the colour.
    for key in ("sel/refutes", "sel/refutes/v@1", "sel/refutes/v@2"):
        g = re.search(rf'<g class="sel-node ([^"]*)"[^>]*data-key="{re.escape(key)}"', sel)
        assert g is not None and "side-refutes" in g.group(1), key
    for key in ("sel", "sel/proves"):
        g = re.search(rf'<g class="sel-node ([^"]*)"[^>]*data-key="{re.escape(key)}"', sel)
        assert g is not None and "side-refutes" not in g.group(1), key
    edges = re.findall(r'<path class="sel-edge([^"]*)" data-from="([^"]+)" data-to="([^"]+)"', sel)
    sides = {(f, t): c for c, f, t in edges}
    assert "side-refutes" in sides[("sel", "sel/refutes")]
    assert "side-refutes" in sides[("sel/refutes", "sel/refutes/v@1")]
    assert "side-refutes" not in sides[("sel", "sel/proves")]
    # Every view under the side carries it; the top and the proving leaf do not.
    vs = one_view.views(two_sides, routes.read(two_sides, []))
    assert vs["sel/refutes"].side == "refutes" and vs["edge/sel/refutes/v@1"].side == "refutes"
    assert vs["sel/proves"].side == "proves" and vs["sel"].side is None


def test_the_table_says_which_way_each_set_settles(two_sides: dict[str, Any]) -> None:
    d = drawn(two_sides)
    rows = re.findall(r'<tr class="set-row[^"]*"[^>]*>.*?</tr>', d.table, re.S)
    assert len(rows) == 3
    assert 'class="set-row side-proves"' in rows[0] and "refutes" not in rows[0]
    assert (
        'class="set-row side-refutes"' in rows[1]
        and '<span class="set-side">refutes</span>' in rows[1]
    )
    assert "goes through the variant" in rows[1]
    assert "3 ways to settle the problem" in d.table


def test_the_page_says_ways_to_settle_and_that_a_set_proves_or_refutes(tmp_path: Path) -> None:
    from test_routes_view import render_tree, two_routes  # noqa: PLC0415

    page = render_tree(two_routes(tmp_path))[f"problems/{TARGET}/index.html"]
    wrap = page[page.index('<div class="selector-wrap">') : page.index('<svg class="selector"')]
    assert "Ways to settle the problem" in wrap and "Sufficient sets" not in page
    assert "proves" in wrap and "refutes" in wrap
    _label, meaning, proto = render.GLOSSARY_BY_KEY["sufficient-set"]
    assert "refut" in meaning and "v3.46" in proto


# -- 4. a root refuted through a variant --------------------------------------------------------


def refuted_view(tmp_path: Path, *, through_variant: bool) -> tuple[render.Renderer, Any]:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    nodes = dict(tv.nodes)
    rv = nodes[tv.root]
    nodes[tv.root] = dataclasses.replace(rv, graph_entry={**rv.graph_entry, "status": "refuted"})
    graph = dict(tv.graph)
    graph["nodes"] = [
        {**n, "status": "refuted"} if n["node_id"] == tv.root else n for n in graph["nodes"]
    ]
    if through_variant:
        graph["nodes"].append(
            {
                **graph["nodes"][0],
                "node_id": "v",
                "status": "proved",
                "relation": "refutes",
                "origin": "variant",
                "deps": [],
            }
        )
        graph["target_proofs"] = [
            {
                "node_id": "v",
                "relation": "refutes",
                "kind": "proof",
                "closure": ["v"],
                "submitter": "alice",
            }
        ]
    index = {**tv.index_entry, "status": "resolved", "root": tv.root}
    return render.Renderer(site, repo_url=REPO, decisions_doc=None), dataclasses.replace(
        tv, nodes=nodes, graph=graph, index_entry=index
    )


def test_a_root_refuted_through_a_variant_says_disproved_by_a_refuting_variant(
    tmp_path: Path,
) -> None:
    r, tv = refuted_view(tmp_path, through_variant=True)
    assert r.resolution(tv) == "disproved"
    assert r.resolution_record(tv) == "a refuting variant is proved on the record"
    assert "counterexample" not in r.resolution_record(tv)
    assert r.resolution_artifact(tv) == "refuting variant's proof"


def test_the_page_itself_says_disproved_by_a_refuting_variant(tmp_path: Path) -> None:
    """The rendered words, not only the methods: the page's claimable line, the root's panel
    line and the "disproved" tag's card each name the refuting variant's proof, and none of
    them says the root was refuted by a counterexample (a live render of erdos-257 with the
    relation mocked showed all three saying "counterexample")."""
    r, tv = refuted_view(tmp_path, through_variant=True)
    tv = dataclasses.replace(
        tv, index_entry={**tv.index_entry, "claimable": False, "not_claimable": []}
    )
    head = r.target_claimable(tv)
    assert "Disproved: a refuting variant is proved on the record" in head, head
    how = r.how_block(tv, tv.nodes[tv.root])
    assert "a refuting variant is proved on the record" in how, how
    assert "counterexample" not in how, how
    assert "refutes" in render.PROBLEM_STATUS_DEFS["disproved"]
    # The key's "refuted" card is shown beside the root too: it names the variant's way.
    _label, meaning, proto = render.GLOSSARY_BY_KEY["refuted"]
    assert "variant" in meaning and "v3.46" in proto


def test_a_root_refuted_by_its_own_counterexample_still_says_so(tmp_path: Path) -> None:
    r, tv = refuted_view(tmp_path, through_variant=False)
    assert r.resolution(tv) == "disproved"
    assert r.resolution_record(tv) == "a counterexample is on the record"
    assert r.resolution_artifact(tv) == "counterexample"


def test_the_relation_roles_and_the_reading_page_name_refutes() -> None:
    assert render.RELATION_ROLES["refutes"] == "a variant that refutes the problem"
    src = Path(render.__file__).read_text(encoding="utf-8")
    assert 'a variant that resolves "\n' not in src
    assert src.count("a variant that resolves the problem") == 1, "RELATION_ROLES is the one home"


def test_the_states_page_names_a_refuting_variant() -> None:
    html = (Path(render.__file__).resolve().parent / "templates" / "states.html").read_text(
        encoding="utf-8"
    )
    assert "refutes-variant" in html or "refutes variant" in html
    for line in re.findall(r"[^\n]*resolves-variant[^\n]*", html):
        assert "refutes" in line, line
