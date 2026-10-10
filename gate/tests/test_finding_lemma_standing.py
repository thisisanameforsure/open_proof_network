"""F08-T41 (D-12 v3.36): a lemma has exactly a hole's standing.

F07-T77 writes the edge (``test_finding_lemma_edge.py``); this file is what the gate makes of it.
The derivation sets lemmas aside as it sets the node's own holes aside (an unproved lemma does not
block; a refuted lemma is a dead route, not a dead node); staging imports a proved lemma before
the parent and leaves an unproved one out, refusing nothing; step 8 accepts a proved lemma's
constants and still refuses an unproved lemma's, because nothing of it was staged.

Over the fake toolchain, which answers step 8 with whatever constants it is told the proof used;
``test_finding_lemma_standing_lean.py`` drives a real proof through the real one.
"""

from __future__ import annotations

import json
from pathlib import Path

from fakes import LIBRARY_CONSTANTS, FakeToolchain, used_constants_result
from harness import TARGET, make_context, node_dir
from test_finding_lemma_edge import X_DECL, X_TYPE, X, borrowed, meta_of, with_cross_branch_node
from test_finding_parent_stays_open import DEP_A, DEP_B
from test_postmerge import ASSEMBLY, PARENT, hole
from test_products import ROOT_NODE, attest

from opn_gate import graph, layout, pipeline, postmerge, products
from opn_gate.steps import stage as staging
from opn_gate.steps.base import RunContext

X_MODULE = layout.node_module(X, "Proof")
A_MODULE, B_MODULE = layout.node_module(DEP_A, "Proof"), layout.node_module(DEP_B, "Proof")
STAMP_B = "20261010T100000Z"
STAMP_ROOT = "20261010T110000Z"


def nodes_dir(root: Path) -> Path:
    return layout.graph_nodes_dir(root, TARGET)


def prove_lemma(root: Path, *, n: int = 3) -> None:
    """A merged proof of ``X``: the statement with its body filled, and its attestation."""
    node = nodes_dir(root) / X
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    (node / "Proof.lean").write_text(
        statement.replace("  sorry\n", "  intro p q r h\n  exact h.1.2\n"), encoding="utf-8"
    )
    attest(root, X, n=n)


def refute_lemma(root: Path, *, n: int = 3) -> None:
    """A merged counterexample on ``X`` (D-12 #2): the artifact declares ``<decl>_refuted``."""
    node = nodes_dir(root) / X
    (node / "Proof.lean").write_text(
        f"import {layout.node_module(X, 'Context')}\n\n"
        f"theorem {X_DECL}_refuted : ¬ ({X_TYPE}) := by\n  sorry\n",
        encoding="utf-8",
    )
    attest(root, X, n=n)


def with_lemma(tmp_path: Path) -> Path:
    """The decomposed fixture with ``X`` under ``and-reassoc`` and the root restating it."""
    root = with_cross_branch_node(tmp_path)
    postmerge.apply_partial(
        nodes_dir(root) / PARENT,
        (borrowed(),),
        partial_text=ASSEMBLY,
        pseudonym="carol",
        stamp=STAMP_ROOT,
    )
    assert meta_of(root)["lemmas"] == [{"hole": "borrowed", "node": X}], "guard: the edge"
    return root


# --- the derivation (F03 reads the tree) ------------------------------------------------------


def test_the_parent_with_an_unproved_lemma_is_ready_listed_and_claimable(tmp_path: Path) -> None:
    """The root's deps are proved and its lemma is not: the root is ``ready``, in the frontier
    and claimable, with no cause — a lemma is never waited on. (Green before F08-T41 too: a
    lemma is not a dep, so ``blocked_because`` never saw it; kept as the guard that it never
    will.)"""
    root = with_lemma(tmp_path)
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[ROOT_NODE].lemmas == (graph.Lemma("borrowed", X),)
    assert tg.statuses[X] == "blocked"  # its own witness slot
    assert tg.statuses[ROOT_NODE] == "ready"
    assert graph.derive_causes(tg.nodes, tg.statuses)[ROOT_NODE] is None
    status_of = lambda n: tg.statuses[n]  # noqa: E731
    assert products.in_frontier("ready", tg.nodes[ROOT_NODE], status_of)
    assert products.workable("ready", tg.nodes[ROOT_NODE], status_of)
    assert products.needs_of("ready", tg.nodes[ROOT_NODE], status_of) == products.NEEDS_PROOF
    built = products.generate(root, rendered_from=None, commit_time="2026-10-10T12:00:00Z")
    doc = json.loads(built.files[Path("frontier.json")].decode("utf-8"))
    [entry] = [e for e in doc["entries"] if e["node_id"] == ROOT_NODE]
    # ``claimable`` on an entry is also the *target's* (the fixture declares none); the node's
    # own answer is ``needs``: a proof, which is what a claim reserves (F03-T16).
    assert entry["status"] == "ready" and entry["needs"] == "proof" and entry["cause"] is None
    assert X in {e["node_id"] for e in doc["entries"]}  # the lemma is work too: its witness


def test_a_refuted_lemma_is_a_dead_route_not_a_dead_node(tmp_path: Path) -> None:
    """A counterexample merged on the lemma refutes *it*; the root stays ``ready`` with no
    ``dep-refuted``, exactly as a refuted hole leaves its parent (D-12 v3.19)."""
    root = with_lemma(tmp_path)
    refute_lemma(root)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[X] == "refuted"
    assert tg.statuses[ROOT_NODE] == "ready"
    assert graph.derive_causes(tg.nodes, tg.statuses)[ROOT_NODE] is None
    assert not graph.blocked_because(tg.nodes[ROOT_NODE], lambda n: tg.statuses[n])[0]


# --- staging (step 4) -------------------------------------------------------------------------


def test_staging_imports_a_proved_lemma_and_leaves_an_unproved_one_out(tmp_path: Path) -> None:
    """A direct proof of the root builds while its lemma is open: the lemma is neither staged
    nor refused (no ``dep-unproved``); once proved, it is staged before the root and imported
    in the generated Context like a dep, so the proof can use it."""
    root = with_lemma(tmp_path)
    node = layout.load_node(nodes_dir(root) / PARENT, TARGET)
    assert isinstance(node, layout.Node)
    staged = staging.stage(node, tmp_path / "work")
    assert staged.problems == ()
    assert X not in staged.order and staged.order[-1] == PARENT
    context = (staged.node_dir(PARENT) / "Context.lean").read_text(encoding="utf-8")
    assert X_MODULE not in context and context.count("import ") == 2  # the two proved deps
    prove_lemma(root)
    staged = staging.stage(node, tmp_path / "work2")
    assert staged.problems == ()
    assert X in staged.order and staged.order.index(X) < staged.order.index(PARENT)
    assert staged.order[-1] == PARENT
    context = (staged.node_dir(PARENT) / "Context.lean").read_text(encoding="utf-8")
    assert f"import {X_MODULE}" in context and context.count("import ") == 3
    assert (staged.node_dir(X) / "Proof.lean").is_file()
    # The lemma's own deps come with it, as a dep's do: none here, and ``and-reassoc``'s
    # record is not touched (X is its hole, not its dep).
    assert graph.load_target(root, TARGET).nodes[DEP_B].holes == (X,)


# --- the pipeline over the fake toolchain (steps 1 to 8) ---------------------------------------


def context_with_lemma(tmp_path: Path, *, used: list[tuple[str, str | None]]) -> RunContext:
    """The fixture's root claimed by a proof submission, with ``X`` restated as its lemma and
    the fake answering step 8 with ``used`` beside the library's constants."""
    fake = FakeToolchain(constants=used_constants_result([*LIBRARY_CONSTANTS, *used]))
    ctx = make_context(tmp_path, node_id=PARENT, toolchain=fake)
    nodes = node_dir(ctx).parent
    postmerge.apply_partial(
        nodes / DEP_B, (hole("cut_q", X_TYPE, local="q"),), partial_text=ASSEMBLY,
        pseudonym="bob", stamp=STAMP_B,
    )  # fmt: skip
    postmerge.apply_partial(
        nodes / PARENT, (borrowed(),), partial_text=ASSEMBLY, pseudonym="carol", stamp=STAMP_ROOT
    )
    return ctx


USES_DEPS_AND_LEMMA: list[tuple[str, str | None]] = [
    ("OpnProp.and_swap", A_MODULE),
    ("OpnProp.and_reassoc", B_MODULE),
    (X_DECL, X_MODULE),
]


def test_a_direct_proof_naming_a_proved_lemma_passes_the_pipeline(tmp_path: Path) -> None:
    """With the lemma proved, the root's own proof draws on its constant and every step passes:
    step 8 reads a proved lemma as declared. Before F08-T41 it failed ``undeclared-dependency``
    naming the lemma's module."""
    ctx = context_with_lemma(tmp_path, used=USES_DEPS_AND_LEMMA)
    nodes = node_dir(ctx).parent
    statement = (nodes / X / "Statement.lean").read_text(encoding="utf-8")
    (nodes / X / "Proof.lean").write_text(
        statement.replace("  sorry\n", "  intro p q r h\n  exact h.1.2\n"), encoding="utf-8"
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()
    assert verdict.data["deps"]["used"] == sorted([DEP_A, DEP_B, X])
    assert verdict.data["deps"]["lemmas"] == [X]
    assert verdict.data["deps"]["declared"] == [DEP_A, DEP_B]  # a lemma is not a dep


def test_a_proof_naming_an_unproved_lemma_is_refused_by_name_and_never_dep_unproved(
    tmp_path: Path,
) -> None:
    """With the lemma unproved nothing of it is staged, so its constant is one the proof cannot
    have: step 8 refuses ``undeclared-dependency`` naming the lemma; staging (step 4) refused
    nothing — in particular never ``dep-unproved``, which would say the root waits on it."""
    ctx = context_with_lemma(tmp_path, used=USES_DEPS_AND_LEMMA)
    verdict = pipeline.run_steps(ctx)
    assert not verdict.ok
    assert verdict.first_failing_step == 8, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "undeclared-dependency"
    assert verdict.diagnostic.details["offences"][0]["node"] == X
    assert "dep-unproved" not in str(verdict.as_dict())
    assert [s.result for s in verdict.steps if s.step == 4] == ["pass"]


def test_a_direct_proof_that_ignores_its_lemma_passes_with_no_warning_about_it(
    tmp_path: Path,
) -> None:
    """A lemma the proof never touches is not a declared dep that went unused (R7's warning is
    about deps); the root is provable directly, lemma or no lemma."""
    ctx = context_with_lemma(tmp_path, used=USES_DEPS_AND_LEMMA[:2])
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()
    assert verdict.data["deps"]["unused"] == []
    assert verdict.data["deps"]["lemmas"] == []  # unproved: not staged, not declared
    assert not any(X in w for w in verdict.data["deps"]["warnings"])
