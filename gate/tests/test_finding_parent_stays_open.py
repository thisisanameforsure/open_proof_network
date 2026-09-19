"""F07-T21 (R22, AC43, Q29; D-12 v3.19): a decomposition never blocks the node it decomposes.

The finding (Mike, 2026-09-19): the first merged partial or reduction appended its holes to the
parent's ``deps``, so the parent derived ``blocked``, left the frontier, drew ``409
node-blocked`` from the service and ``dep-unproved`` from the gate's staging step. One
contributor's route locked the node for everyone: no direct proof, no rival decomposition, while
D-6 says competing routes coexist and D-31 calls competing skeletons normal. The rule now: a
hole is a child the parent may draw on once it is proved, never a dependency it waits on. Only a
proof, a counterexample or a vacuity certificate closes the parent.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from harness import TARGET, copy_graph, make_context, node_dir
from test_postmerge import ASSEMBLY, HOLES, PARENT, PSEUDONYM, STAMP, hole
from test_products import ROOT_NODE, attest, node_status_record

from opn_gate import graph, layout, pipeline, postmerge, products
from opn_gate.steps import stage as staging

DEP_A = "tutorial-and-swap"
DEP_B = "and-reassoc"
H1 = f"{PARENT}--h1"
H2 = f"{PARENT}--h2"


def decomposed(tmp_path: Path) -> Path:
    """The fixture graph with the root unproved, its two declared deps proved, and one merged
    partial applied: two hole children on the record and in the root's deps."""
    root = copy_graph(tmp_path, publish=True)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    (parent / "Proof.lean").unlink()
    attest(root, DEP_A, n=1)
    attest(root, DEP_B, n=2)
    postmerge.apply_partial(parent, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP)
    return root


# --- derivation (F03 reads the tree) ---------------------------------------------------------


def test_the_parent_stays_open_after_a_partial_merges(tmp_path: Path) -> None:
    """R22: the holes are in ``deps`` and on the record, and the parent is ``ready`` all the
    same — listed and claimable — while each hole needs its witness."""
    root = decomposed(tmp_path)
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[ROOT_NODE].deps[-2:] == (H1, H2)
    assert tg.nodes[ROOT_NODE].holes == (H1, H2)
    assert tg.statuses[ROOT_NODE] == "ready"
    assert tg.statuses[H1] == "blocked" and tg.statuses[H2] == "blocked"
    causes = graph.derive_causes(tg.nodes, tg.statuses)
    assert causes[H1] == graph.CAUSE_WITNESS_MISSING and causes[ROOT_NODE] is None
    status_of = lambda n: tg.statuses[n]  # noqa: E731
    assert products.in_frontier("ready", tg.nodes[ROOT_NODE], status_of)
    assert products.workable("ready", tg.nodes[ROOT_NODE], status_of)


def test_a_declared_dependency_still_blocks(tmp_path: Path) -> None:
    """The rule is about holes, not deps: take away a declared dep's proof and the parent is
    blocked on it as before, with the holes still set aside."""
    root = decomposed(tmp_path)
    (root / "attestations" / "000002.json").unlink()  # DEP_B no longer proved
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[DEP_B] == "ready"
    assert tg.statuses[ROOT_NODE] == "blocked"
    assert graph.derive_causes(tg.nodes, tg.statuses)[ROOT_NODE] is None


def test_a_dead_hole_is_a_dead_route_not_a_dead_node(tmp_path: Path) -> None:
    """An abandoned hole (a curator's record, D-14) leaves the parent open; only a declared dep
    that was refuted or abandoned would block it."""
    root = decomposed(tmp_path)
    node_status_record(root, H1, "abandoned")
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[H1] == "abandoned"
    assert tg.statuses[ROOT_NODE] == "ready"


def test_only_the_parents_own_holes_are_set_aside(tmp_path: Path) -> None:
    """``is_hole_of`` is the prefix and a hole origin together: a sibling that merely carries
    the prefix with an authored origin is a dependency, and a hole of another node is too."""
    assert graph.is_hole_of(PARENT, H1, "compiler-derived")
    assert graph.is_hole_of(PARENT, f"{H1}-v2", "skeleton-hole")
    assert not graph.is_hole_of(PARENT, H1, "authored")
    assert not graph.is_hole_of(PARENT, "other--h1", "compiler-derived")
    assert not graph.is_hole_of(PARENT, DEP_B, "compiler-derived")
    root = decomposed(tmp_path)
    nodes = root / "targets" / TARGET / "nodes"
    assert graph.is_hole_child(nodes, PARENT, H1)
    assert not graph.is_hole_child(nodes, PARENT, DEP_B)
    assert not graph.is_hole_child(nodes, PARENT, f"{PARENT}--h9")  # not a node


# --- the gate (steps 4 and 8) -----------------------------------------------------------------


def test_staging_leaves_an_unproved_hole_out_and_imports_a_proved_one(tmp_path: Path) -> None:
    """A direct proof of the parent builds while its holes are open: the unproved holes are
    neither staged nor refused (no ``dep-unproved``), and a hole that has been proved is
    imported like a dep, so the assembly route can use it."""
    ctx = make_context(tmp_path, node_id=PARENT)
    nodes = node_dir(ctx).parent
    postmerge.apply_partial(
        node_dir(ctx), HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    node = layout.load_node(nodes / PARENT, TARGET)
    assert isinstance(node, layout.Node)
    staged = staging.stage(node, tmp_path / "work")
    assert staged.problems == ()
    assert staged.order == (DEP_A, DEP_B, PARENT)
    context = (staged.node_dir(PARENT) / "Context.lean").read_text()
    assert context.count("import ") == 2 and H1 not in context
    # The hole proved: staged before the parent and imported.
    (nodes / H1 / "Proof.lean").write_text(
        (nodes / DEP_A / "Proof.lean").read_text(encoding="utf-8"), encoding="utf-8"
    )
    staged = staging.stage(node, tmp_path / "work2")
    assert staged.problems == ()
    assert staged.order == (DEP_A, DEP_B, H1, PARENT)
    context = (staged.node_dir(PARENT) / "Context.lean").read_text()
    assert context.count("import ") == 3 and layout.node_module(H1, "Proof") in context


def test_a_direct_proof_of_a_decomposed_node_passes_the_pipeline(tmp_path: Path) -> None:
    """Over the fake toolchain, the parent's own proof runs every step with two open holes on
    the record; before R22 it failed step 4 with ``dep-unproved`` naming the first hole."""
    ctx = make_context(tmp_path, node_id=PARENT)
    postmerge.apply_partial(
        node_dir(ctx), HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict


# --- the post-merge job (a second route) ------------------------------------------------------


def test_a_later_decomposition_numbers_its_holes_after_the_earlier_ones(tmp_path: Path) -> None:
    """Two routes to one node coexist as two sets of children: the second partial's holes are
    ``--h3`` and ``--h4``, both routes are on the record under attempts/, and the parent's deps
    carry all four holes."""
    root = decomposed(tmp_path)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    nodes = parent.parent
    assert postmerge.next_child_index(nodes, PARENT) == 3
    second = (
        hole("h_left", "∀ (p q r : Prop), (p ∧ q) ∧ r → q", local="q"),
        hole("h_rest", "∀ (p q r : Prop), (p ∧ q) ∧ r → q → r ∧ p", local="r ∧ p"),
    )
    result = postmerge.apply_partial(
        parent, second, partial_text=ASSEMBLY, pseudonym="bob", stamp="20260919T120000Z"
    )
    assert result.children == (f"{PARENT}--h3", f"{PARENT}--h4")
    meta = yaml.safe_load((parent / "META.yaml").read_text())
    assert meta["deps"][-4:] == [H1, H2, f"{PARENT}--h3", f"{PARENT}--h4"]
    assert len(sorted((parent / "attempts").glob("*.lean"))) == 2
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[ROOT_NODE] == "ready"
    assert tg.nodes[ROOT_NODE].holes == (H1, H2, f"{PARENT}--h3", f"{PARENT}--h4")


def test_next_child_index_counts_a_revised_hole_by_its_number(tmp_path: Path) -> None:
    nodes = tmp_path / "nodes"
    for name in (f"{PARENT}--h1", f"{PARENT}--h2-v2", f"{PARENT}--h2", "other--h7", PARENT):
        (nodes / name).mkdir(parents=True)
    assert postmerge.next_child_index(nodes, PARENT) == 3
    assert postmerge.next_child_index(nodes, "other") == 8
    assert postmerge.next_child_index(nodes, "fresh") == 1


def test_a_restated_hole_is_an_edge_and_a_restated_sibling_is_not(tmp_path: Path) -> None:
    """A later route's hole that restates one of the parent's own holes is that hole again (an
    edge already on the record); one that restates any other sibling adds no edge, because an
    edge the parent would wait on is what a decomposition must not add."""
    root = decomposed(tmp_path)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    own = replace(hole("again", HOLES[0].closed_type, local="r"), defeq_sibling=H1)
    other = replace(
        hole("borrowed", "∀ (p q : Prop), p ∧ q → q ∧ p", local="q ∧ p"), defeq_sibling=DEP_A
    )
    fresh = hole("h_new", "∀ (p q r : Prop), (p ∧ q) ∧ r → q", local="q")
    before = yaml.safe_load((parent / "META.yaml").read_text())["deps"]
    assert DEP_A in before  # a declared dep of the fixture's root
    result = postmerge.apply_partial(
        parent,
        (own, other, fresh),
        partial_text=ASSEMBLY,
        pseudonym="carol",
        stamp="20260919T130000Z",
    )
    assert result.children == (f"{PARENT}--h5",)  # indexes 3 and 4 were the reused holes' slots
    placed = {p["name"]: p for p in result.holes}
    assert placed["again"] == {"name": "again", "child": None, "reused_node": H1}
    assert placed["borrowed"] == {"name": "borrowed", "child": None, "reused_node": DEP_A}
    after = yaml.safe_load((parent / "META.yaml").read_text())["deps"]
    assert after == [*before, f"{PARENT}--h5"]  # H1 was already there; DEP_A likewise
    assert not (parent.parent / f"{PARENT}--h3").exists()


@pytest.mark.parametrize("sibling", [DEP_B])
def test_a_restated_sibling_that_was_not_a_dep_stays_off_the_deps(
    tmp_path: Path, sibling: str
) -> None:
    root = copy_graph(tmp_path)
    parent = root / "targets" / TARGET / "nodes" / PARENT
    meta = yaml.safe_load((parent / "META.yaml").read_text())
    meta["deps"] = [d for d in meta["deps"] if d != sibling]
    (parent / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    borrowed = replace(
        hole("borrowed", "∀ (p q r : Prop), (p ∧ q) ∧ r → p ∧ (q ∧ r)", local="x"),
        defeq_sibling=sibling,
    )
    result = postmerge.apply_partial(
        parent, (borrowed,), partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    assert result.children == ()
    after = yaml.safe_load((parent / "META.yaml").read_text())["deps"]
    assert sibling not in after
