"""F29-T1 (R6; D-25 v3.44): the selector tree over a target's sufficient sets.

Built from the enumerated sets alone: the list is split, in record order, on the first route
choice on which its members differ, and the split recurses. Each leaf is exactly one published
set; each interior node is the family of sets that share the choices above it. It is never built
from the graph, because a hole shared between branches (a lemma) makes the unrolled OR tree
over-count; on a tree-shaped target the two agree (AC3), and on a shared one only this is right
(AC4).
"""

from __future__ import annotations

from typing import Any

from test_target_routes import doc, hole, live, node

from opn_gate import routes


def tree(graph: dict[str, Any], cut: str = "finest") -> routes.Selector:
    return routes.selector_tree(routes.read(graph, (), cut=cut))


def leaves(t: routes.Selector) -> list[str]:
    if t.set is not None:
        return [t.set]
    return [s for c in t.children for s in leaves(c)]


def test_a_target_with_one_route_choice_is_one_split_with_one_leaf_per_set() -> None:
    g = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]], deps=["t--h1", "t--h2"]),
        hole("t--h1"),
        hole("t--h2"),
    )
    result = routes.read(g, ())
    t = routes.selector_tree(result)
    assert t.node == "t" and t.set is None
    assert [c.route for c in t.children] == ["t@1", "t@2"]
    assert leaves(t) == [s.id for s in result.sets]
    assert all(c.set is not None and c.children == () for c in t.children)
    assert [c.sets for c in t.children] == [1, 1] and t.sets == 2


def test_a_forced_choice_never_splits() -> None:
    # One route at the root, two at the hole: the only split is at the hole, and the leaf
    # order is the record's (the sets' order).
    g = doc(
        node("t", decompositions=[["t--h1"]], deps=["t--h1"]),
        hole(
            "t--h1", decompositions=[["t--h1--h1"], ["t--h1--h2"]], deps=["t--h1--h1", "t--h1--h2"]
        ),
        hole("t--h1--h1"),
        hole("t--h1--h2"),
    )
    result = routes.read(g, ())
    t = routes.selector_tree(result)
    assert t.node == "t--h1"
    assert [c.route for c in t.children] == ["t--h1@1", "t--h1@2"]
    assert leaves(t) == [s.id for s in result.sets]


def test_a_tree_shaped_target_matches_the_product_of_its_choices() -> None:
    # AC3: two independent OR points, 2 x 2 = 4 sets, and the tree nests the second choice
    # under each branch of the first.
    g = doc(
        node("t", decompositions=[["t--h1", "t--h2"]], deps=["t--h1", "t--h2"]),
        hole(
            "t--h1", decompositions=[["t--h1--h1"], ["t--h1--h2"]], deps=["t--h1--h1", "t--h1--h2"]
        ),
        hole("t--h1--h1"),
        hole("t--h1--h2"),
        hole(
            "t--h2", decompositions=[["t--h2--h1"], ["t--h2--h2"]], deps=["t--h2--h1", "t--h2--h2"]
        ),
        hole("t--h2--h1"),
        hole("t--h2--h2"),
    )
    result = routes.read(g, ())
    assert len(result.sets) == 4
    t = routes.selector_tree(result)
    assert t.node == "t--h1" and [c.route for c in t.children] == ["t--h1@1", "t--h1@2"]
    for branch in t.children:
        assert branch.node == "t--h2"
        assert [c.route for c in branch.children] == ["t--h2@1", "t--h2@2"]
        assert branch.sets == 2
    assert leaves(t) == [s.id for s in result.sets]


def test_a_shared_hole_is_read_from_the_sets_not_the_graph() -> None:
    # AC4: t--h2's second route restates t--h1's hole (a lemma), so under t--h2@2 nothing but
    # the shared statement is needed. The sets are still one per choice (F27-T7), but the tree
    # must say so from the sets: here every leaf is a set and every set a leaf, whatever the
    # graph's sharing, and the selector reports how many sets each family holds.
    g = doc(
        node("t", decompositions=[["t--h1", "t--h2"]], deps=["t--h1", "t--h2"]),
        hole("t--h1", decompositions=[["t--h1--h1"]], deps=["t--h1--h1"]),
        hole("t--h1--h1"),
        hole("t--h2", decompositions=[["t--h2--h1"], ["t--h1--h1"]], deps=["t--h2--h1"]),
        hole("t--h2--h1"),
    )
    result = routes.read(g, ())
    t = routes.selector_tree(result)
    assert sorted(leaves(t)) == sorted(s.id for s in result.sets)
    assert len(leaves(t)) == len(result.sets) == t.sets
    assert len(set(leaves(t))) == len(leaves(t)), "a set appears once"


def test_a_target_with_one_set_is_a_single_leaf() -> None:
    g = doc(node("t", decompositions=[["t--h1"]], deps=["t--h1"]), hole("t--h1"))
    result = routes.read(g, ())
    t = routes.selector_tree(result)
    assert t.set == result.sets[0].id and t.children == () and t.sets == 1


def test_no_sets_is_an_empty_selector() -> None:
    g = doc(node("t", "abandoned"))  # a dead root closes nothing (F27-R5)
    t = routes.selector_tree(routes.read(g, ()))
    assert t.set is None and t.children == () and t.sets == 0


def test_as_dict_carries_route_node_set_and_count_at_every_level() -> None:
    g = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]], deps=["t--h1", "t--h2"]),
        hole("t--h1"),
        hole("t--h2"),
    )
    d = routes.selector_tree(routes.read(g, ())).as_dict()
    assert set(d) == {"route", "node", "set", "sets", "side", "children"}  # side: F27-T11
    assert d["route"] is None and d["node"] == "t" and d["set"] is None and d["sets"] == 2
    assert d["side"] is None
    assert d["children"][0]["route"] == "t@1" and d["children"][0]["set"] is not None
    assert d["children"][0]["children"] == []


def test_live_erdos_1094_every_leaf_is_a_set_and_the_first_split_is_the_records() -> None:
    graph, frontier = live("erdos-1094")
    result = routes.read(graph, frontier)
    t = routes.selector_tree(result)
    assert leaves(t) == [s.id for s in result.sets]
    assert t.sets == len(result.sets) >= 2

    # Every interior node splits on a statement with two or more routes used across its family.
    def walk(n: routes.Selector) -> None:
        if n.set is not None:
            return
        chosen = [c.route for c in n.children]
        assert len(chosen) >= 2
        assert n.node is not None
        assert all(r is None or r.startswith(n.node + "@") for r in chosen)
        for c in n.children:
            walk(c)

    walk(t)


# --- D-25 v3.46 (F27-T11): the fork on the side -----------------------------------------------


def refuting(*holes: str) -> dict[str, Any]:
    return node(
        "v", origin="variant", relation="refutes", deps=list(holes), decompositions=[list(holes)]
    )


def test_both_sides_fork_at_the_top_proving_first() -> None:
    """With sets of both sides the tree opens on a fork: a top node that splits on nothing
    (route, node and set all None), two children in this order — the proving family then the
    refuting one — each carrying ``side`` and being what the split of its own sets gives; the
    leaves are still the sets, in their order."""
    g = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]], deps=["t--h1", "t--h2"]),
        hole("t--h1"),
        hole("t--h2"),
        refuting("v--h1"),
        hole("v--h1"),
    )
    result = routes.read(g, ())
    t = routes.selector_tree(result)
    assert (t.route, t.node, t.set, t.side, t.sets) == (None, None, None, None, 3)
    proving, refuting_side = t.children
    assert (proving.side, refuting_side.side) == ("proves", "refutes")
    # the proving family is today's split of the proving sets alone
    assert (proving.route, proving.node, proving.sets) == (None, "t", 2)
    assert [c.route for c in proving.children] == ["t@1", "t@2"]
    assert all(c.side is None for c in proving.children)
    # one refuting set: its family is a leaf, carrying the side
    assert (refuting_side.set, refuting_side.sets, refuting_side.children) == (
        result.sets[2].id,
        1,
        (),
    )
    assert leaves(t) == [s.id for s in result.sets]
    proving_only = routes.selector_tree(routes.read(doc(*g["nodes"][:3]), ()))
    assert proving_only.side is None and proving_only.node == "t"


def test_one_side_only_has_no_fork_and_no_side() -> None:
    """One side only forks on nothing: as today, ``side`` None at every level; and a proved
    root has nothing to refute, so a refutes variant beside it gives no second side."""
    g = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]], deps=["t--h1", "t--h2"]),
        hole("t--h1"),
        hole("t--h2"),
    )
    t = tree(g)
    assert t.side is None and all(c.side is None for c in t.children)
    assert t.node == "t"
    settled = routes.read(doc(node("t", "proved"), refuting("v--h1"), hole("v--h1")), ())
    assert [s.settles for s in settled.sets] == ["proves"]
    assert routes.selector_tree(settled).side is None


def test_as_dict_carries_side_at_every_level() -> None:
    g = doc(
        node("t", decompositions=[["t--h1"]], deps=["t--h1"]),
        hole("t--h1"),
        refuting("v--h1"),
        hole("v--h1"),
    )
    d = routes.selector_tree(routes.read(g, ())).as_dict()
    assert set(d) == {"route", "node", "set", "sets", "side", "children"}
    assert d["side"] is None and d["node"] is None and d["sets"] == 2
    assert [c["side"] for c in d["children"]] == ["proves", "refutes"]
    assert all(c["set"] is not None for c in d["children"])


def test_the_erdos_257_shape_forks_into_two_leaves() -> None:
    graph, frontier = live("erdos-257-shape")
    result = routes.read(graph, frontier)
    t = routes.selector_tree(result)
    assert t.node is None and t.sets == 2
    assert [(c.side, c.set) for c in t.children] == [
        ("proves", result.sets[0].id),
        ("refutes", result.sets[1].id),
    ]
