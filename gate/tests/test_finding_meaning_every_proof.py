"""F08-T28: step 4's meaning guard reads every artifact that claims the statement (F08-Q36, Q40).

Until T28 the guard asked its question only when a use line stood in the artifact or in a merged
proof beneath it (T23, T25). That left the oldest road open: a dependency's merged ``Proof.lean``
may carry a further command after its body (step 2 checks the text's prefix and suffix only), the
build stages that proof as the dependency's module, and so an instance, a notation or a macro it
declares is in the environment of every proof built on it. A dependent with no use line anywhere
was never compared with its statement, and for a plain proof ``artifact.judge`` checks no type at
all: the verdict that the artifact proves the statement rested on the statement's *text* being
repeated, not on what the text elaborated to.

So the comparison now runs for every artifact that declares the statement's own theorem: a
proof, an alternate (D-25) and a partial's assembly (D-12 #5). A counterexample or a vacuity
certificate declares another theorem, which ``opn-artifact-type`` checks; with no use in its
closure it is not asked, exactly as before (proposed follow-up in the evidence file).

The toolchain is faked here; ``test_uses_defs_lean.py`` shows the road and its refusal on the
real one (``test_a_dependencys_proof_module_cannot_change_the_statement_of_any_artifact`` and the
notation case beside it).
"""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, meaning_result
from harness import make_context, node_dir

from opn_gate import layout, pipeline, uses
from opn_gate.steps import meaning

NODE = "and-swap-reassoc"  # two proved dependencies, no use line anywhere in the fixture
QUESTION = f"statement_meaning:{layout.node_module(NODE, 'Proof')}:OpnProp.and_swap_reassoc"


def test_a_plain_proof_with_no_uses_is_held_to_its_statements_meaning(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert uses.USES_KEY not in verdict.data
    # the statement is built from the node's own files, and the question is asked before replay
    assert f"elaborate:{layout.node_module(NODE, 'Statement')}" in fake.calls
    assert QUESTION in fake.calls
    assert fake.calls.index(QUESTION) < next(
        i for i, c in enumerate(fake.calls) if c.startswith("kernel_replay")
    )
    assert verdict.data[meaning.MEANING_KEY] == {"identical": True, "matches": True}


def test_a_changed_meaning_with_no_use_anywhere_fails_step_4(tmp_path: Path) -> None:
    """The road Q36 left open: nothing declares a use, and the statement's text still reads as
    another proposition in the artifact's environment (here, one a dependency's proof carried)."""
    fake = FakeToolchain(
        meaning=meaning_result(
            expected="∀ (p q r : Prop), p ∧ q ∧ r → r ∧ q ∧ p",
            declared="∀ (p q r : Prop), p ∧ q ∧ r → False",
        )
    )
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed"
    assert verdict.diagnostic.details["uses"] == []
    assert verdict.diagnostic.details["carried"] == {}
    assert not any(c.startswith("kernel_replay") for c in fake.calls)


def test_a_counterexample_with_nothing_carried_is_not_asked(tmp_path: Path) -> None:
    """A counterexample declares ``<decl>_refuted : ¬ S``; the statement's theorem is not in its
    module, and its type is ``opn-artifact-type``'s check. Unchanged by T28."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    proof = node_dir(ctx) / "Proof.lean"
    proof.write_text(
        f"import {layout.node_module(NODE, 'Context')}\n\n"
        "theorem OpnProp.and_swap_reassoc_refuted : ¬ True := by\n  sorry\n",
        encoding="utf-8",
    )
    pipeline.run_steps(ctx)
    assert not any(c.startswith("statement_meaning") for c in fake.calls)
    assert meaning.MEANING_KEY not in ctx.data
