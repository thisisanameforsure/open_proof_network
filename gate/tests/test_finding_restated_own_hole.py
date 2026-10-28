"""F07-T78 (R22): a hole that restates one of the parent's own holes is that hole, and the record
says so.

The finding (2026-10-28, erdos-68, graph #1154): a second skeleton on the root restated the first
skeleton's ``h1``. The post-merge job recognised it (``defeq_sibling`` names ``erdos-68--h1``),
wrote no new node — R22: it is that hole again, and the edge is already in ``deps`` — and
recorded the match in its log and nowhere else. The products match a decomposition's holes to
children by the name in each child's header, one hole per child, so the first route kept
``--h1`` and the second route's ``h1`` was published as ``node: null``: ``get_submission`` said
``became: None``, ``list_sufficient_sets`` dropped the route as not live, and the site drew it as
"closes nothing".

The rule now: ``META.yaml`` gains ``restated: [{partial, hole, node}]`` (``meta/v7``),
bot-written and additive, beside ``lemmas`` (which stays the record of nodes under *other*
branches). Keyed by the partial, because two routes may each have an ``h1``. It adds no edge and
changes no standing; it only records which existing hole a route's hole is.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml
from harness import TARGET, copy_graph
from test_decompositions import add_hole, merged_partial
from test_finding_graph_lemmas import graph_rows, revise
from test_finding_parent_stays_open import H1, H2, decomposed
from test_postmerge import ASSEMBLY, PARENT, hole
from test_products import ROOT_NODE, nodes_dir

from opn_gate import graph, layout, postmerge, products, routes, schemas

ROUTE_1 = "attempts/20261028T132200Z-alice-partial.lean"
ROUTE_2 = "attempts/20261028T145000Z-bob-partial.lean"


def meta_of(root: Path, node_id: str) -> dict[str, Any]:
    path = layout.graph_nodes_dir(root, TARGET) / node_id / "META.yaml"
    return dict(yaml.safe_load(path.read_text("utf-8")))


# --- the writer -------------------------------------------------------------------------------


def test_a_second_route_restating_an_own_hole_records_which_hole_it_is(tmp_path: Path) -> None:
    root = decomposed(tmp_path)  # the root with its first route's holes --h1, --h2
    own = replace(hole("h1", "∀ (p q r : Prop), (p ∧ q) ∧ r → r", local="r"), defeq_sibling=H1)
    fresh = hole("h2", "∀ (p q r : Prop), (p ∧ q) ∧ r → q ∧ True", local="q ∧ True")
    result = postmerge.apply_partial(
        layout.graph_nodes_dir(root, TARGET) / PARENT,
        (own, fresh),
        partial_text=ASSEMBLY,
        pseudonym="bob",
        stamp="20261028T145000Z",
    )
    meta = meta_of(root, PARENT)
    assert meta["restated"] == [{"partial": result.attempt_path, "hole": "h1", "node": H1}]
    assert meta["schema"] == "meta/v7"
    assert schemas.violations(meta, "meta/v7") == []
    # No edge and no lemma beyond what R22 already gave: the own hole is a dep once.
    assert meta["deps"].count(H1) == 1 and "lemmas" not in meta
    assert result.restated == (("h1", H1),)
    assert result.as_dict()["restated"] == [{"hole": "h1", "node": H1}]
    assert graph.load_target(root, TARGET).nodes[PARENT].restated == (
        graph.Restated(partial=result.attempt_path, hole="h1", node=H1),
    )


def test_a_route_that_restates_nothing_writes_no_field(tmp_path: Path) -> None:
    root = decomposed(tmp_path)
    before = meta_of(root, PARENT)
    assert "restated" not in before
    postmerge.apply_partial(
        layout.graph_nodes_dir(root, TARGET) / PARENT,
        (hole("h_new", "∀ (p q r : Prop), (p ∧ q) ∧ r → q ∧ True", local="q ∧ True"),),
        partial_text=ASSEMBLY,
        pseudonym="bob",
        stamp="20261028T145000Z",
    )
    after = meta_of(root, PARENT)
    assert "restated" not in after and after["schema"] == before["schema"]


def test_applying_the_same_merge_twice_records_the_restatement_once(tmp_path: Path) -> None:
    root = decomposed(tmp_path)
    own = replace(hole("h1", "∀ (p q r : Prop), (p ∧ q) ∧ r → r", local="r"), defeq_sibling=H2)
    node_dir = layout.graph_nodes_dir(root, TARGET) / PARENT
    first = postmerge.add_restated(node_dir, ROUTE_2, [("h1", H2)])
    again = postmerge.add_restated(node_dir, ROUTE_2, [("h1", H2)])
    assert first == again == [{"partial": ROUTE_2, "hole": "h1", "node": H2}]
    assert own.defeq_sibling == H2


# --- the products -----------------------------------------------------------------------------


def two_routes(tmp_path: Path) -> Path:
    """erdos-68's shape: route 1 made ``--h1`` (``h1``) and ``--h2`` (``h2``); route 2's ``h1``
    restated ``--h1`` and its ``h2`` became ``--h3``."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, f"{ROOT_NODE}--h1", "h1")
    add_hole(root, f"{ROOT_NODE}--h2", "h2")
    add_hole(root, f"{ROOT_NODE}--h3", "h2")
    merged_partial(root, 7, ["h1", "h2"], path=ROUTE_1)
    merged_partial(root, 8, ["h1", "h2"], path=ROUTE_2)
    return root


def write_restated(root: Path, entries: list[dict[str, str]]) -> None:
    path = nodes_dir(root) / ROOT_NODE / "META.yaml"
    doc = yaml.safe_load(path.read_text())
    doc.update(schema="meta/v7", restated=entries)
    assert schemas.violations(doc, "meta/v7") == []
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_without_the_record_the_second_route_s_hole_is_null(tmp_path: Path) -> None:
    """The live defect, kept as the baseline: nothing says which hole route 2's ``h1`` is."""
    rows = graph_rows(two_routes(tmp_path))
    d2 = rows[ROOT_NODE]["decompositions"][1]
    assert d2["holes"][0] == {"name": "h1", "node": None}


def test_the_record_resolves_the_second_route_s_hole(tmp_path: Path) -> None:
    root = two_routes(tmp_path)
    write_restated(root, [{"partial": ROUTE_2, "hole": "h1", "node": f"{ROOT_NODE}--h1"}])
    d1, d2 = graph_rows(root)[ROOT_NODE]["decompositions"]
    assert d1["holes"] == [
        {"name": "h1", "node": f"{ROOT_NODE}--h1"},
        {"name": "h2", "node": f"{ROOT_NODE}--h2"},
    ]
    assert d2["holes"] == [
        {"name": "h1", "node": f"{ROOT_NODE}--h1"},
        {"name": "h2", "node": f"{ROOT_NODE}--h3"},
    ]


def test_a_restatement_keyed_to_another_partial_does_not_apply(tmp_path: Path) -> None:
    """Two routes may each have an ``h1``: the record names the partial it belongs to."""
    root = two_routes(tmp_path)
    write_restated(root, [{"partial": ROUTE_1, "hole": "h1", "node": f"{ROOT_NODE}--h2"}])
    d1, d2 = graph_rows(root)[ROOT_NODE]["decompositions"]
    assert d1["holes"][0] == {"name": "h1", "node": f"{ROOT_NODE}--h2"}
    # Route 1's entry says nothing of route 2's h1, which takes the child left free by name.
    assert d2["holes"][0] == {"name": "h1", "node": f"{ROOT_NODE}--h1"}


def test_a_restated_hole_later_revised_publishes_the_revision(tmp_path: Path) -> None:
    root = two_routes(tmp_path)
    write_restated(root, [{"partial": ROUTE_2, "hole": "h1", "node": f"{ROOT_NODE}--h1"}])
    new = revise(root, f"{ROOT_NODE}--h1")
    d2 = graph_rows(root)[ROOT_NODE]["decompositions"][1]
    assert d2["holes"][0] == {"name": "h1", "node": new}


def test_the_second_route_is_live_in_the_route_view(tmp_path: Path) -> None:
    """``list_sufficient_sets`` dropped erdos-68's route 2 because one hole had no node."""
    root = two_routes(tmp_path)
    write_restated(root, [{"partial": ROUTE_2, "hole": "h1", "node": f"{ROOT_NODE}--h1"}])
    tg = graph.load_target(root, TARGET)
    doc = products.graph_doc(tg, None)
    view = routes.read(doc)
    mine = [r for r in view.routes if r.node == ROOT_NODE]
    assert len(mine) == 2 and all(r.resolved for r in mine), mine
