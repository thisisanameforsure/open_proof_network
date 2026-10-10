"""F07-T77 (D-12 v3.36; F07-R22 revised): a hole that restates a node under another branch of the
target is that node, and the parent gains it as a *lemma*.

The finding (graph #479, 2026-10-09, erdos-1094): a partial on ``--h3`` had one hole that restated
``--h2--h1--h1``, step 4 recognised it (``defeq_sibling``), and the post-merge writer recorded the
restatement in its log and nowhere else — D-12 v3.19 (Q29) had said a restated sibling adds no
edge, because an edge the parent would *wait on* is what a decomposition must not add. So the
merged assembly could never be used: a proof may draw only on what its ``Context.lean`` carries.

The rule now: ``META.yaml`` gains ``lemmas: [{hole, node}]`` (``meta/v6``), bot-written and
additive, with exactly a hole's standing — the parent's ``Context.lean`` carries the lemma's
signature, the parent may draw on it once it is proved, and the parent never waits on it. Not in
``deps``: a declared dependency keeps blocking (D-3), and ``is_hole_child`` knows a hole by prefix
and origin, which a cross-branch node has neither of.

The writer (this file); the standing — derivation, staging, step 8 — is
``test_finding_lemma_standing.py`` (F08-T41).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from harness import TARGET
from test_finding_b_revise_v2 import AUTHOR, DATE, v1_request_doc, write_doc
from test_finding_parent_stays_open import DEP_A, DEP_B, H1, H2, decomposed
from test_postmerge import ASSEMBLY, PARENT, hole

from opn_gate import curator, graph, layout, postmerge, schemas
from opn_gate.steps import artifact as art
from opn_gate.steps import deps as depstep

#: The node under another branch: a hole of ``and-reassoc``, which the fixture's root depends on.
#: It is not the root's hole child (wrong prefix) and not its ancestor (nothing rests on it
#: through the root), so it is exactly what ``offload-restates-ancestor`` lets through.
X = f"{DEP_B}--h1"
X_DECL = "and_reassoc__h1"
X_TYPE = "∀ (p q r : Prop), (p ∧ q) ∧ r → q"
X_SIGNATURE = f"theorem {X_DECL} : {X_TYPE} := by\n  sorry\n"
STAMP_2 = "20261010T100000Z"
STAMP_3 = "20261010T110000Z"


def nodes_dir(root: Path) -> Path:
    return layout.graph_nodes_dir(root, TARGET)


def with_cross_branch_node(tmp_path: Path) -> Path:
    """The decomposed fixture (root unproved with holes ``--h1``, ``--h2``; its two deps proved)
    plus ``X``, a hole written under ``and-reassoc`` by a partial of its own."""
    root = decomposed(tmp_path)
    postmerge.apply_partial(
        nodes_dir(root) / DEP_B,
        (hole("cut_q", X_TYPE, local="q"),),
        partial_text=ASSEMBLY,
        pseudonym="bob",
        stamp=STAMP_2,
    )
    assert (
        (nodes_dir(root) / X / "Statement.lean").read_text(encoding="utf-8").endswith(X_SIGNATURE)
    )
    return root


def borrowed(name: str = "borrowed", sibling: str = X) -> art.Hole:
    return replace(hole(name, X_TYPE, local="q"), defeq_sibling=sibling)


def restate(
    root: Path, *holes: art.Hole, stamp: str = STAMP_3, pseudonym: str = "carol"
) -> postmerge.PartialMerge:
    return postmerge.apply_partial(
        nodes_dir(root) / PARENT,
        tuple(holes),
        partial_text=ASSEMBLY,
        pseudonym=pseudonym,
        stamp=stamp,
    )


def meta_of(root: Path, node_id: str = PARENT) -> dict[str, object]:
    return dict(yaml.safe_load((nodes_dir(root) / node_id / "META.yaml").read_text("utf-8")))


def context_of(root: Path, node_id: str = PARENT) -> str:
    return (nodes_dir(root) / node_id / "Context.lean").read_text(encoding="utf-8")


def loaded(root: Path, node_id: str = PARENT) -> layout.Node:
    node = layout.load_node(nodes_dir(root) / node_id, TARGET)
    assert isinstance(node, layout.Node), node
    return node


# --- the edge ---------------------------------------------------------------------------------


def test_a_restated_cross_branch_node_becomes_a_lemma_of_the_parent(tmp_path: Path) -> None:
    """The hole's name and the node it restated land in ``META.yaml``'s ``lemmas``; ``deps`` is
    exactly what it was; no child directory is written; the placement still names the reuse."""
    root = with_cross_branch_node(tmp_path)
    before = meta_of(root)
    result = restate(root, borrowed())
    assert result.children == ()
    assert result.holes == ({"name": "borrowed", "child": None, "reused_node": X},)
    assert result.lemmas == (("borrowed", X),)
    assert "lemmas" in result.as_dict()
    after = meta_of(root)
    assert after["deps"] == before["deps"] == [DEP_A, DEP_B, H1, H2]
    assert after["lemmas"] == [{"hole": "borrowed", "node": X}]
    assert after["schema"] == "meta/v6"  # bumped from the fixture's v1: the field exists from v6
    schemas.validate(after, "meta/v6")
    assert not (nodes_dir(root) / f"{PARENT}--h3").exists()
    # The graph reads it through the one accessor every consumer builds on.
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[PARENT].lemmas == (graph.Lemma(hole="borrowed", node=X),)
    assert tg.nodes[PARENT].deps == (DEP_A, DEP_B, H1, H2)


def test_the_parents_context_carries_the_lemmas_signature_verbatim(tmp_path: Path) -> None:
    """``Context.lean`` is regenerated with the lemma's statement verbatim beside the deps', so a
    proof of the parent may name it (F00-R19: a proof cannot add an import) and the gate's own
    F01-R6 byte check — the dep's signature hash-equals its ``Statement.lean`` — holds for the
    lemma as it holds for every dep. The layout still accepts the file (its imports are the
    library's and ``Defs.*`` only: the lemma's own ``Context`` import is stripped as a dep's is)."""
    root = with_cross_branch_node(tmp_path)
    restate(root, borrowed())
    context = context_of(root)
    assert X_SIGNATURE in context
    assert f"`{X}`" in context
    for dep in (DEP_A, DEP_B, H1, H2):  # the deps' signatures are still there, in order
        assert f"`{dep}`" in context
    assert context.index(f"`{H2}`") < context.index(f"`{X}`")
    assert "import" not in context
    node = loaded(root)
    assert depstep.required_signatures(node) == [DEP_A, DEP_B, H1, H2, X]
    assert depstep.check_context(node, depstep.required_signatures(node)) is None


def test_a_hand_edited_context_is_still_refused(tmp_path: Path) -> None:
    """The byte check reaches the lemma's signature: a Context whose lemma signature differs from
    the node's ``Statement.lean`` is a graph defect, named as it is for a dep."""
    root = with_cross_branch_node(tmp_path)
    restate(root, borrowed())
    path = nodes_dir(root) / PARENT / "Context.lean"
    path.write_text(path.read_text("utf-8").replace("∧ r → q :=", "∧ r → p :="), "utf-8")
    node = loaded(root)
    problem = depstep.check_context(node, depstep.required_signatures(node))
    assert problem is not None and problem.diagnostic is not None
    assert problem.diagnostic.code == "context-signature-mismatch"
    assert problem.diagnostic.details["dep"] == X
    # The post-merge pass that mends a stale context (F08-T10) mends this one too.
    assert postmerge.refresh_contexts(nodes_dir(root)) == [path]
    assert X_SIGNATURE in path.read_text("utf-8")


def test_the_parents_statement_hash_is_untouched(tmp_path: Path) -> None:
    """Only the two bot-owned files change (F07-Q2): the statement and its hash are what they
    were, so D-3's immutability is intact."""
    root = with_cross_branch_node(tmp_path)
    statement = (nodes_dir(root) / PARENT / "Statement.lean").read_bytes()
    before = meta_of(root)["statement-hash"]
    restate(root, borrowed())
    assert (nodes_dir(root) / PARENT / "Statement.lean").read_bytes() == statement
    assert meta_of(root)["statement-hash"] == before
    assert meta_of(root)["statement-hash"] == schemas.content_hash(statement)


# --- additive, once --------------------------------------------------------------------------


def test_applying_the_same_partial_twice_adds_one_lemma(tmp_path: Path) -> None:
    """A re-run of the job on the same merge (two attempts on the record, as a re-run leaves
    them) adds the edge once."""
    root = with_cross_branch_node(tmp_path)
    restate(root, borrowed(), stamp=STAMP_3)
    restate(root, borrowed(), stamp="20261010T120000Z")
    assert meta_of(root)["lemmas"] == [{"hole": "borrowed", "node": X}]
    assert context_of(root).count(X_SIGNATURE) == 1


def test_two_partials_restating_the_same_node_add_one_lemma(tmp_path: Path) -> None:
    """Two routes that each restate ``X`` under their own hole name record one lemma, under the
    first hole's name: the edge is to the node, and a node is a lemma once."""
    root = with_cross_branch_node(tmp_path)
    restate(root, borrowed("first_route"), stamp=STAMP_3, pseudonym="carol")
    restate(root, borrowed("second_route"), stamp="20261010T120000Z", pseudonym="dave")
    assert meta_of(root)["lemmas"] == [{"hole": "first_route", "node": X}]
    assert len(sorted((nodes_dir(root) / PARENT / "attempts").glob("*.lean"))) == 3


def test_a_restated_own_hole_is_an_edge_and_a_fresh_hole_a_child_beside_a_lemma(
    tmp_path: Path,
) -> None:
    """One partial, three holes: one restates the parent's own ``--h1`` (an edge already on the
    record, no lemma), one restates ``X`` (a lemma), one is new (a child). The three placements
    keep today's shape and the child takes the next free index."""
    root = with_cross_branch_node(tmp_path)
    own = replace(hole("again", "∀ (p q r : Prop), (p ∧ q) ∧ r → r", local="r"), defeq_sibling=H1)
    fresh = hole("h_new", "∀ (p q r : Prop), (p ∧ q) ∧ r → q ∧ True", local="q ∧ True")
    result = restate(root, own, borrowed(), fresh)
    assert result.children == (f"{PARENT}--h5",)
    assert result.lemmas == (("borrowed", X),)
    meta = meta_of(root)
    assert meta["deps"] == [DEP_A, DEP_B, H1, H2, f"{PARENT}--h5"]
    assert meta["lemmas"] == [{"hole": "borrowed", "node": X}]
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[PARENT].holes == (H1, H2, f"{PARENT}--h5")
    assert tg.nodes[PARENT].lemmas == (graph.Lemma("borrowed", X),)


def test_a_reused_name_that_is_not_a_node_is_still_refused(tmp_path: Path) -> None:
    """``reused_node``'s refusal is unchanged: an edge to nothing is written nowhere (C7)."""
    root = with_cross_branch_node(tmp_path)
    before = meta_of(root)
    with pytest.raises(postmerge.GraphWriteError, match="not another node"):
        restate(root, borrowed(sibling="no-such-node"))
    assert meta_of(root) == before
    assert "lemmas" not in meta_of(root)


def test_a_meta_already_at_v6_keeps_its_version_and_a_v5_one_is_bumped(tmp_path: Path) -> None:
    """``add_lemmas`` follows ``scaffold.meta_for``'s precedent: the oldest version that can
    express the record. A v5 META (a hole with ``proved_binders``) becomes v6; a v6 stays."""
    root = with_cross_branch_node(tmp_path)
    path = nodes_dir(root) / PARENT / "META.yaml"
    meta = meta_of(root)
    meta["schema"] = "meta/v5"
    path.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), "utf-8")
    assert postmerge.add_lemmas(nodes_dir(root) / PARENT, [("borrowed", X)]) == [
        {"hole": "borrowed", "node": X}
    ]
    assert meta_of(root)["schema"] == "meta/v6"
    assert postmerge.add_lemmas(nodes_dir(root) / PARENT, [("other", X)]) == [
        {"hole": "borrowed", "node": X}
    ]
    assert meta_of(root)["schema"] == "meta/v6"
    assert postmerge.add_lemmas(nodes_dir(root) / PARENT, []) == [{"hole": "borrowed", "node": X}]


# --- through a revision (D-8) -----------------------------------------------------------------


def test_a_lemma_of_a_node_later_revised_reads_through_the_revision(tmp_path: Path) -> None:
    """A D-8 revision of ``X`` supersedes it with ``X-v2``; the record still says ``X`` (nothing
    rewrites it, F08-T10) and the graph reads the lemma as ``X-v2`` — and the post-merge pass
    regenerates the parent's Context to carry the revision's signature."""
    root = with_cross_branch_node(tmp_path)
    restate(root, borrowed())
    revised = X_SIGNATURE.replace("→ q :=", "→ q ∧ True :=")
    statement = f"import {layout.node_module(X + '-v2', 'Context')}\n\n{revised}"
    request = write_doc(root, X, v1_request_doc(X))
    # The hole's witness slot imports the superseded node's own Context, which the revision may
    # not carry (2026-09-17: a revision of an unwitnessed hole is held to a witness of its own).
    witness = (
        "theorem witness : ∃ p q r : Prop, (p ∧ q) ∧ r := "
        "⟨True, True, True, ⟨trivial, trivial⟩, trivial⟩\n"
    )
    curator.revise(root, TARGET, X, statement, request, author=AUTHOR, date=DATE, witness=witness)
    assert meta_of(root)["lemmas"] == [{"hole": "borrowed", "node": X}]  # the record stays
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[PARENT].lemmas == (graph.Lemma("borrowed", X + "-v2"),)
    node = loaded(root)
    assert depstep.required_signatures(node)[-1] == X + "-v2"
    stale = depstep.check_context(node, depstep.required_signatures(node))
    assert stale is not None and stale.diagnostic is not None
    assert stale.diagnostic.code == "context-signature-mismatch", "guard: the old signature"
    # Two contexts carried the old signature: the lemma's parent-through-deps (``and-reassoc``,
    # F08-T10's case) and the lemma's parent-through-lemmas (the root, this case).
    assert postmerge.refresh_contexts(nodes_dir(root)) == [
        nodes_dir(root) / DEP_B / "Context.lean",
        nodes_dir(root) / PARENT / "Context.lean",
    ]
    assert revised in context_of(root) and X_SIGNATURE not in context_of(root)
    assert depstep.check_context(loaded(root), depstep.required_signatures(loaded(root))) is None
