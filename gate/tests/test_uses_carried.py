"""F08-T25: a use reaches the proofs built on it, so the meaning guard does too (R22, Q40).

T23 and T24 run step 4's meaning guard for an artifact that *declares* uses, on the reading that
only such an artifact is elaborated in a larger environment than its statement. A second reader
found the case that reading leaves out. A merged proof's use lines are imports of its ``Proof``
module, and the build stages a node's dependencies as their ``Proof`` modules (F01-Q4). So once a
dependency's proof declares ``import Defs.X`` (or uses a node whose proof does), every proof built
on that dependency is elaborated with ``Defs.X`` in its environment, whether or not it declares
anything itself, and its statement's own header never named the module. That artifact was not
guarded: its statement's text could elaborate to another proposition and nothing compared the two.
(Since F08-T28 every proof is guarded; what this file still pins is the ``carried`` record.)

It is uses that open this road, not an older defect: before T23 a ``Proof`` module's imports were
its statement's, which the dependent's own ``Context.lean`` of signatures already carries.

So the guard's question is asked whenever a use line stands anywhere in the staged closure: in
the artifact, or in the merged proof of any node staged beneath it. A tree with no use lines is
checked exactly as before (no statement build, no question, no record), which is every graph
today.

The toolchain is faked here; ``test_uses_carried_lean.py`` shows the trap and the refusal on the
real one. Seen red first (``engineering/evidence/F08/task-25-red.txt``).
"""

from __future__ import annotations

from pathlib import Path

from fakes import LIBRARY_CONSTANTS, FakeToolchain, meaning_result, used_constants_result
from harness import make_context, node_dir
from test_uses_defs import EXTRA, NODE, USE, defs_dir
from test_uses_nodes import INTERIOR, TUTORIAL, add_node, nodes, prove, swap_constant, with_uses

from opn_gate import layout, pipeline, uses
from opn_gate.steps import RunContext, meaning

QUESTION = f"statement_meaning:{layout.node_module(NODE, 'Proof')}:OpnProp.and_swap_reassoc"


def dependency_declares(ctx: RunContext, dep: str = INTERIOR) -> None:
    """``dep``'s merged proof gains a use line for an admitted definition. ``and-reassoc`` has no
    imports, so the line leads its file."""
    (defs_dir(ctx) / "Extra.lean").write_text(EXTRA, encoding="utf-8")
    proof = node_dir(ctx).parent / dep / "Proof.lean"
    proof.write_text(f"{USE}\n" + proof.read_text(encoding="utf-8"), encoding="utf-8")
    assert layout.validate_node(proof.parent) == []


def test_a_dependencys_use_line_brings_the_guard_to_a_proof_that_declares_none(
    tmp_path: Path,
) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    dependency_declares(ctx)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    # the artifact declares nothing, and is still held to its statement's own meaning
    assert uses.USES_KEY not in verdict.data
    assert QUESTION in fake.calls
    assert fake.calls.index(QUESTION) < next(
        i for i, c in enumerate(fake.calls) if c.startswith("kernel_replay")
    )
    assert verdict.data[meaning.MEANING_KEY] == {
        "identical": True,
        "matches": True,
        "carried": {INTERIOR: ["Defs.Extra"]},
    }
    # step 8 has no declaration to hold to the term, and writes no record of one
    assert "uses" not in verdict.data["deps"]


def test_a_meaning_changed_by_a_dependencys_use_fails_step_4_and_names_the_carrier(
    tmp_path: Path,
) -> None:
    fake = FakeToolchain(
        meaning=meaning_result(
            expected="∀ (n : Nat), @Size.size Nat instBase n = 0",
            declared="∀ (n : Nat), @Size.size Nat instTrap n = 0",
        )
    )
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    dependency_declares(ctx)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed"
    assert verdict.diagnostic.details["uses"] == []
    assert verdict.diagnostic.details["carried"] == {INTERIOR: ["Defs.Extra"]}
    assert INTERIOR in verdict.diagnostic.message
    assert not any(c.startswith("kernel_replay") for c in fake.calls)


def test_a_use_two_proofs_down_is_carried_as_well(tmp_path: Path) -> None:
    """The closure, not the first layer: the root depends on ``and-reassoc``, whose merged proof
    uses the node ``lemma``, whose merged proof declares the definition."""
    fake = FakeToolchain(
        constants=used_constants_result(
            [*LIBRARY_CONSTANTS, swap_constant(TUTORIAL), swap_constant(INTERIOR)]
        )
    )
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    (defs_dir(ctx) / "Extra.lean").write_text(EXTRA, encoding="utf-8")
    add_node(ctx, "lemma")
    lemma = prove(ctx, "lemma")
    text = lemma.read_text(encoding="utf-8")
    own = f"import {layout.node_module('lemma', 'Context')}\n"
    assert text.count(own) == 1
    lemma.write_text(text.replace(own, f"{own}{USE}\n"), encoding="utf-8")
    with_uses(ctx, "lemma", node_id=INTERIOR)
    assert layout.validate_node(nodes(ctx) / "lemma") == []
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert QUESTION in fake.calls
    assert verdict.data[meaning.MEANING_KEY].get("carried") == {
        INTERIOR: [layout.node_module("lemma", "Proof")],
        "lemma": ["Defs.Extra"],
    }


def test_a_declared_use_and_a_carried_one_are_both_recorded(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    dependency_declares(ctx)
    (defs_dir(ctx) / "Other.lean").write_text("def Opn.other : Nat := 1\n", encoding="utf-8")
    proof = node_dir(ctx) / "Proof.lean"
    own = f"import {layout.node_module(NODE, 'Context')}\n"
    text = proof.read_text(encoding="utf-8")
    assert text.count(own) == 1
    proof.write_text(text.replace(own, f"{own}import Defs.Other\n"), encoding="utf-8")
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Other"]
    assert verdict.data[meaning.MEANING_KEY].get("carried") == {INTERIOR: ["Defs.Extra"]}


def test_a_closure_with_no_use_line_anywhere_is_still_asked_and_carries_nothing(
    tmp_path: Path,
) -> None:
    """Restated by F08-T28 (Q36): this test said a tree with no use line was checked exactly as
    before, with no statement build and no question. That was the road T28 closes, since a
    dependency's merged proof may carry an instance after its body with no use line anywhere. The
    question is now asked of every proof; what stays true is that nothing is *carried*."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[meaning.MEANING_KEY] == {"identical": True, "matches": True}
    assert QUESTION in fake.calls
    assert f"elaborate:{layout.node_module(NODE, 'Statement')}" in fake.calls


def test_a_use_in_a_node_outside_the_closure_carries_nothing(tmp_path: Path) -> None:
    """Only what is staged beneath the artifact is in its environment: a use line in the proof
    of a node this one does not rest on is no concern of this check."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=INTERIOR, toolchain=fake)
    (defs_dir(ctx) / "Extra.lean").write_text(EXTRA, encoding="utf-8")
    add_node(ctx, "lemma")
    lemma = prove(ctx, "lemma")
    text = lemma.read_text(encoding="utf-8")
    own = f"import {layout.node_module('lemma', 'Context')}\n"
    lemma.write_text(text.replace(own, f"{own}{USE}\n"), encoding="utf-8")
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    # T28: the proof is still held to its statement's meaning, but nothing is carried into it
    assert "carried" not in verdict.data[meaning.MEANING_KEY]
