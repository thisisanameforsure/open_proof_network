"""Finding "a hole may restate an ancestor", lean tier: a real three-level chain through the real
extractor (F07-T34).

The chain is the fixture's root ``and-swap-reassoc`` → ``and-reassoc`` → a new leaf
``and-left-of-and`` (``∀ p q : Prop, p ∧ q → p``), and a partial on the leaf hands a node above it
back down as a hole. The fast tier (``test_finding_hole_restates_ancestor.py``) proves what the
gate does with a ``defeq_ancestor`` the fake reports; only this tier proves the extractor reports
it, because definitional equality is a question for Lean, and the ancestor probes are staged into
the work directory and read there, which a fake never does (one lean-tier test per new
Lean-facing seam).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, make_context
from test_finding_hole_restates_ancestor import (
    LEAF,
    LEAF_STATEMENT,
    PARENT,
    ROOT,
    add_node,
    set_deps,
)

from opn_gate import layout, pipeline
from opn_gate.paths import Change
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

STAMP = "20260923T120000Z-tester-partial.lean"
ROOT_SOURCE = "∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)"
PARENT_SOURCE = "∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r)"
#: A hole nobody above the leaf states: the leaf's hypotheses over a weaker conclusion.
FRESH = "  have fresh : ∀ p q : Prop, p ∧ q → p ∧ True := sorry\n"
ASSEMBLE = "  intro p q h\n  exact (fresh p q h).1\n"


def leaf_partial(tmp_path: Path, toolchain: LocalToolchain | None, body: str) -> RunContext:
    """The three-level chain, and ``body`` as the leaf's one partial under ``attempts/``; with no
    toolchain the harness's fake, for a caller that puts its own seam on the context after."""
    ctx = make_context(
        tmp_path,
        node_id=LEAF,
        toolchain=toolchain,
        changes=[Change("A", f"targets/{TARGET}/nodes/{LEAF}/attempts/{STAMP}")],
    )
    nodes = layout.graph_nodes_dir(ctx.graph_root, TARGET)
    leaf = add_node(nodes, LEAF, LEAF_STATEMENT, deps=[])
    set_deps(nodes, PARENT, [LEAF])
    head, _, _ = LEAF_STATEMENT.partition(":= by\n  sorry")
    (leaf / "attempts" / STAMP).write_text(head + ":= by\n" + body, encoding="utf-8")
    return ctx


@pytest.mark.parametrize(
    ("body", "ancestor"),
    [
        # The grandchild's hole is the root's statement, stated before any binder.
        (f"  have up : {ROOT_SOURCE} := sorry\n" + FRESH + ASSEMBLE, ROOT),
        # The same, one level up: the parent is an ancestor too, not only the root.
        (f"  have up : {PARENT_SOURCE} := sorry\n" + FRESH + ASSEMBLE, PARENT),
        # Written under the leaf's own binders: the closed form carries them and is not the
        # root's statement, but the type where it sits is — and is still the root restated.
        (
            FRESH + f"  intro p q h\n  have up : {ROOT_SOURCE} := sorry\n  exact (fresh p q h).1\n",
            ROOT,
        ),
    ],
    ids=["root-before-binders", "parent", "root-under-binders"],
)
def test_the_extractor_names_the_ancestor_a_hole_restates(
    tmp_path: Path,
    *,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
    body: str,
    ancestor: str,
) -> None:
    del pinned, lean_pkg  # resolved and built by the fixtures; the seam finds both itself
    ctx = leaf_partial(tmp_path, real_toolchain, body)
    verdict = pipeline.run_submission(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "offload-restates-ancestor", verdict.as_dict()
    assert verdict.diagnostic.details["restated"] == [{"hole": "up", "ancestor": ancestor}]
    holes = {h["name"]: h for h in verdict.data["artifact"]["holes"]}
    assert holes["up"]["defeq_ancestor"] == ancestor
    assert holes["fresh"]["defeq_ancestor"] is None
    # Neither is the leaf's own goal, and the ancestor is no sibling: only the new rule sees it.
    assert not any(h["defeq_goal"] for h in holes.values())
    assert all(h["defeq_sibling"] is None for h in holes.values())


def test_a_genuinely_new_hole_passes(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """The negative: the same chain, the ancestors staged and asked, and a hole that is new work."""
    del pinned, lean_pkg
    ctx = leaf_partial(tmp_path, real_toolchain, FRESH + ASSEMBLE)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    [hole] = verdict.data["artifact"]["holes"]
    assert hole["name"] == "fresh"
    assert hole["closed_type"] == "∀ (p q : Prop), p ∧ q → p ∧ True"
    assert hole["defeq_ancestor"] is None and hole["defeq_goal"] is False
    # The question was asked: both ancestors were staged for the extractor to read.
    assert sorted(p.name for p in ctx.workdir.rglob("Ancestor*.lean")) == [
        "Ancestor0.lean",
        "Ancestor1.lean",
    ]
