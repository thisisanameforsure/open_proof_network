"""F31-T3 (R2, R3; AC2, AC3): the shelving derivation and what the products publish of it.

The fixture (``shelving_support``): the root ``and-swap-reassoc`` over ``and-reassoc`` (``A``)
and ``tutorial-and-swap`` (``T``). ``A`` gets a merged decomposition (route 1, holes ``h1`` and
``h2`` as ``A--h1`` and ``A--h2``), ``A--h2`` a decomposition of its own (``A--h2--h1``), and the
tests add a second route of ``A`` sharing ``A--h2``, or a route of ``T`` using ``A--h1`` as a
lemma (the erdos-1094 shape, F31-Q5). Every expectation is the ruled set (F31-Q3, Q5, Q6).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from shelving_support import ALICE, ROOT, A, T, Tree, make_keys
from test_modes import CURATOR

from opn_gate import context, products, shelving

H1 = f"{A}--h1"
H2 = f"{A}--h2"
H3 = f"{A}--h3"
H21 = f"{A}--h2--h1"
ROUTE1 = "attempts/20261020T000000Z-alice-partial.lean"
ROUTE2 = "attempts/20261021T000000Z-bob-partial.lean"
ROUTE21 = "attempts/20261022T000000Z-carol-partial.lean"
ROUTE_T = "attempts/20261023T000000Z-dave-partial.lean"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory.mktemp("shelving-keys"))


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Tree:
    """``A`` decomposed once into ``A--h1`` and ``A--h2``; ``A--h2`` into ``A--h2--h1``."""
    t = Tree(tmp_path, keys)
    t.hole(H1, "h1", parent=A)
    t.hole(H2, "h2", parent=A)
    t.partial(A, ["h1", "h2"], path=ROUTE1)
    t.hole(H21, "k1", parent=H2)
    t.partial(H2, ["k1"], path=ROUTE21)
    return t


ROOT_HOLE = f"{ROOT}--h9"
ROOT_ROUTE = "attempts/20261025T000000Z-root-partial.lean"


def second_route(tree: Tree) -> None:
    """Route 2 of ``A``: a new hole ``A--h3`` and ``A--h2`` again, restated as a lemma."""
    tree.hole(H3, "h3", parent=A)
    tree.lemmas(A, [{"hole": "h2s", "node": H2}])
    tree.partial(A, ["h3", "h2s"], path=ROUTE2)


def shelved(tree: Tree) -> dict[str, dict[str, Any] | None]:
    tg = tree.load()
    return {n: tg.nodes[n].shelved for n in tg.order}


def shelved_ids(tree: Tree) -> set[str]:
    return {n for n, s in shelved(tree).items() if s is not None}


# --- AC2: the ruled set -----------------------------------------------------------------------


def test_nothing_is_shelved_without_a_record(tree: Tree) -> None:
    assert shelved_ids(tree) == set()


def test_a_node_scope_shelving_reaches_the_node_and_every_hole_child_beneath_it(
    tree: Tree,
) -> None:
    """(a): ``A``, ``A--h1``, ``A--h2`` and ``A--h2--h1``; never the root, never ``T``."""
    tree.shelve(ALICE, A)
    assert shelved_ids(tree) == {A, H1, H2, H21}


def test_the_derived_object_names_the_record_and_the_node_it_reached_through(
    tree: Tree,
) -> None:
    change = tree.shelve(ALICE, A, cause="Route 2 does not help the root.")
    name = change.path.rsplit("/", 1)[1]
    expected = {
        "cause": "Route 2 does not help the root.",
        "by": ALICE,
        "date": "2026-10-24",
        "record": f"shelving/{name}",
        "scope": "node",
        "via": A,
    }
    found = shelved(tree)
    assert found[A] == expected
    assert found[H1] == expected and found[H21] == expected, "inherited: the same object, via A"
    assert found[ROOT] is None and found[T] is None


def test_a_statement_a_merged_proof_uses_is_never_reached(tree: Tree) -> None:
    """(a): ``T``'s proof uses ``A--h1``, so the cascade from ``A`` stops short of it."""
    tree.prove(H1)
    tree.prove(T, used=[H1])
    tree.shelve(ALICE, A)
    assert shelved_ids(tree) == {A, H2, H21}


def test_an_own_record_on_a_used_statement_is_void(tree: Tree) -> None:
    """Rule 3 outranks the label: a record that merged before the proof that uses the node says
    nothing once that proof is on the record (F31-Q8); nothing is rewritten."""
    tree.shelve(ALICE, H1)
    assert shelved_ids(tree) == {H1}
    tree.prove(H1)
    tree.prove(T, used=[H1])
    assert shelved_ids(tree) == set()


def test_a_record_on_the_root_that_slipped_in_is_ignored(tree: Tree) -> None:
    tree.shelve(ALICE, ROOT)
    assert shelved_ids(tree) == set()


def test_retiring_a_route_of_the_root_shelves_its_holes_and_not_the_root(tree: Tree) -> None:
    """F31-Q18: the root is never shelved, but its own decompositions are retired like any
    other's — the retirement cuts the arrival into each hole and the root stays."""
    tree.hole(ROOT_HOLE, "hr", parent=ROOT)
    tree.partial(ROOT, ["hr"], path=ROOT_ROUTE)
    tree.shelve(ALICE, ROOT, scope="route", route=ROOT_ROUTE)
    assert shelved_ids(tree) == {ROOT_HOLE}


def test_a_route_retirement_reaches_its_holes_and_theirs_but_not_the_node_or_a_shared_hole(
    tree: Tree,
) -> None:
    """(b): retiring route 1 shelves ``A--h1``; ``A--h2`` is a hole of the live route 2 too, so
    it stays, and so does ``A--h2--h1`` beneath it; ``A`` itself is never shelved by a route."""
    second_route(tree)
    change = tree.shelve(ALICE, A, scope="route", route=ROUTE1)
    assert shelved_ids(tree) == {H1}
    name = change.path.rsplit("/", 1)[1]
    assert shelved(tree)[H1] == {
        "cause": "This branch does not serve the root.",
        "by": ALICE,
        "date": "2026-10-24",
        "record": f"shelving/{name}",
        "scope": "route",
        "via": A,
    }


def test_retiring_every_route_shelves_every_hole_and_what_is_beneath_them(tree: Tree) -> None:
    """(b): both routes retired — ``A--h1``, ``A--h2``, ``A--h3`` and ``A--h2--h1``; not ``A``.
    Two retirements are two keys: the second does not lift the first."""
    second_route(tree)
    tree.shelve(ALICE, A, scope="route", route=ROUTE1, date="2026-10-24T10:00:00Z")
    tree.shelve(ALICE, A, scope="route", route=ROUTE2, date="2026-10-24T11:00:00Z")
    assert shelved_ids(tree) == {H1, H2, H3, H21}


def test_a_hole_shared_with_a_live_route_of_another_unshelved_parent_stays(tree: Tree) -> None:
    """(c), F31-Q5: ``T``'s route uses ``A--h1`` as a lemma; shelving ``A`` must not take it
    off the frontier, while ``A--h2`` (no other arrival) goes."""
    tree.lemmas(T, [{"hole": "l", "node": H1}])
    tree.partial(T, ["l"], path=ROUTE_T)
    tree.shelve(ALICE, A)
    assert shelved_ids(tree) == {A, H2, H21}


def test_the_shared_hole_goes_when_the_other_parent_is_shelved_too(tree: Tree) -> None:
    tree.lemmas(T, [{"hole": "l", "node": H1}])
    tree.partial(T, ["l"], path=ROUTE_T)
    tree.shelve(ALICE, A)
    tree.shelve(ALICE, T)
    assert shelved_ids(tree) == {A, T, H1, H2, H21}


def test_an_own_unshelved_record_on_a_child_exempts_it_and_what_is_beneath_it(
    tree: Tree,
) -> None:
    """(d): the child's own record decides for it before any inherited shelving; a parent that
    is not shelved cuts nothing beneath it."""
    tree.shelve(ALICE, A)
    tree.shelve(ALICE, H2, action="unshelved")
    assert shelved_ids(tree) == {A, H1}


def test_the_latest_own_record_wins_by_date_then_name(tree: Tree) -> None:
    """(e)."""
    tree.shelve(ALICE, A, date="2026-10-24T10:00:00Z")
    tree.shelve(ALICE, A, action="unshelved", date="2026-10-24T11:00:00Z")
    assert shelved_ids(tree) == set()
    tree.shelve(ALICE, A, date="2026-10-24T12:00:00Z")
    assert shelved_ids(tree) == {A, H1, H2, H21}
    # the same second by another signer: the file name (the login) breaks the tie, and
    # ``thisisanameforsure`` sorts after ``alice-steward``
    tree.shelve(CURATOR, A, action="unshelved", date="2026-10-24T12:00:00Z")
    assert shelved_ids(tree) == set()


def test_a_withdrawn_or_excluded_record_is_absent(tree: Tree) -> None:
    """(f): the loader leaves out what a curator's withdrawal names and what the caller excludes
    (the gate's view before a pull request's own files)."""
    change = tree.shelve(ALICE, A)
    name = change.path.rsplit("/", 1)[1]
    assert [r.name for r in shelving.load(tree.node_dir(A))] == [name]
    assert shelving.load(tree.node_dir(A), exclude=frozenset({name})) == []
    tg = tree.load()
    derived = shelving.derive(
        tg.nodes, root=tg.root, used=shelving.used_nodes(tg.nodes), exclude=frozenset({change.path})
    )
    assert all(v is None for v in derived.values())


def test_a_same_statement_revision_inherits_its_predecessors_record(tree: Tree) -> None:
    """F31-Q8: ``A--h2`` shelved, then revised with its statement unchanged — the revision has no
    record of its own and reads the chain's."""
    tree.shelve(ALICE, H2)
    new = tree.revise(H2)
    found = shelved(tree)
    inherited = found[new]
    assert inherited is not None
    assert inherited["via"] == H2, "the record is read where it sits"
    assert found[H21] is not None, "the revision folds the old node's holes onto itself"


def test_a_shelved_proved_statement_keeps_its_status(tree: Tree) -> None:
    """Rule 2 and F31-Q6: shelving is not a status."""
    tree.prove(H1)
    tree.shelve(ALICE, H1)
    tg = tree.load()
    assert tg.statuses[H1] == "proved" and tg.nodes[H1].shelved is not None


# --- AC3: the products ------------------------------------------------------------------------


def test_a_shelved_ready_node_leaves_the_frontier_and_its_row_and_bundle_carry_the_object(
    tree: Tree,
) -> None:
    before = tree.render()
    assert {H1, H21} <= tree.frontier(before)
    tree.shelve(ALICE, A)
    prod = tree.render()
    rows = tree.rows(prod)
    assert rows[H1]["status"] == "ready" and rows[H1]["shelved"]["via"] == A
    assert rows[A]["shelved"] == rows[H1]["shelved"] == rows[H21]["shelved"]
    assert rows[ROOT]["shelved"] is None and rows[T]["shelved"] is None
    assert not ({A, H1, H2, H21} & tree.frontier(prod))
    assert tree.frontier(prod) == tree.frontier(before) - {A, H1, H2, H21}
    bundle = tree.bundle(prod, H1)
    assert bundle["shelved"] == rows[H1]["shelved"] and bundle["status"] == "ready"
    parent = tree.bundle(prod, A)
    deps = {d["node_id"]: d for d in parent["deps"]}
    assert deps[H1]["shelved"] == rows[H1]["shelved"]
    root_bundle = tree.bundle(prod, ROOT)
    root_deps = {d["node_id"]: d for d in root_bundle["deps"]}
    assert root_deps[A]["shelved"] == rows[A]["shelved"] and root_deps[T]["shelved"] is None


def test_the_two_bundle_builders_agree_byte_for_byte(tree: Tree) -> None:
    """The disk builder the products run and ``context.build`` over the published rows (the
    shape the service's host reader takes) produce one document."""
    tree.shelve(ALICE, A)
    prod = tree.render()
    gdoc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
    states = context.graph_states(gdoc)
    reader = context.DiskReader(tree.root)
    for node_id in (A, H1, H21, ROOT):
        built = context.build(
            reader, TARGET, node_id, states=states, rendered_from=gdoc["rendered_from"]
        )
        assert built == tree.bundle(prod, node_id), node_id
    again = tree.render()
    assert again.files == prod.files


def test_in_frontier_is_false_for_a_shelved_node(tree: Tree) -> None:
    tree.shelve(ALICE, H1)
    tg = tree.load()
    node = tg.nodes[H1]
    assert tg.statuses[H1] == "ready"
    assert products.in_frontier("ready", node, lambda n: tg.statuses[n]) is False
    unshelved = replace(node, shelved=None)
    assert products.in_frontier("ready", unshelved, lambda n: tg.statuses[n]) is True
