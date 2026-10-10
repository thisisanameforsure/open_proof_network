"""F08-T41 (D-12 v3.36), lean tier: a real proof of the parent uses the staged lemma.

What only the real toolchain can show: the parent's regenerated ``Context.lean`` elaborates with
the lemma's signature in it; with the lemma proved, step 4 builds the lemma's ``Proof`` module
before the parent's and the parent's proof closes its goal through the lemma's constant, which
step 8 then reads from the kernel term and accepts as a proved lemma's; with the lemma unproved,
nothing of it is staged, so the same proof fails at step 4 on an unknown identifier — never on
``dep-unproved``, because the parent does not wait on a lemma.

Lean core only, like the rest of the propositional fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import make_context, node_dir
from test_finding_lemma_edge import X_DECL, X_TYPE, X, borrowed
from test_finding_parent_stays_open import DEP_A, DEP_B
from test_postmerge import ASSEMBLY, PARENT, hole

from opn_gate import layout, pipeline, postmerge
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain

pytestmark = [pytest.mark.lean, pytest.mark.usefixtures("pinned", "lean_pkg")]

#: The root's statement is ``∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)``; ``X`` gives ``q``.
PROOF = (
    f"import {layout.node_module(PARENT, 'Context')}\n\n"
    "theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by\n"
    "  intro p q r h\n"
    f"  exact ⟨h.2, {X_DECL} p q r h, h.1.1⟩\n"
)


def submission(tmp_path: Path, tc: LocalToolchain, *, lemma_proved: bool) -> RunContext:
    """The fixture's root, with ``X`` under ``and-reassoc`` restated as the root's lemma, and
    the root's ``Proof.lean`` drawing on it."""
    ctx = make_context(tmp_path, node_id=PARENT, toolchain=tc)
    nodes = node_dir(ctx).parent
    postmerge.apply_partial(
        nodes / DEP_B,
        (hole("cut_q", X_TYPE, local="q"),),
        partial_text=ASSEMBLY,
        pseudonym="bob",
        stamp="20261010T100000Z",
    )
    postmerge.apply_partial(
        nodes / PARENT,
        (borrowed(),),
        partial_text=ASSEMBLY,
        pseudonym="carol",
        stamp="20261010T110000Z",
    )
    if lemma_proved:
        statement = (nodes / X / "Statement.lean").read_text(encoding="utf-8")
        (nodes / X / "Proof.lean").write_text(
            statement.replace("  sorry\n", "  intro p q r h\n  exact h.1.2\n"), encoding="utf-8"
        )
    (nodes / PARENT / "Proof.lean").write_text(PROOF, encoding="utf-8")
    return ctx


def test_a_real_proof_of_the_parent_uses_the_staged_lemma(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    ctx = submission(tmp_path / "proved", real_toolchain, lemma_proved=True)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert verdict.data["deps"]["used"] == [X]  # the term rests on the lemma alone
    assert verdict.data["deps"]["unused"] == [DEP_A, DEP_B]  # R7: a warning, never a failure
    assert verdict.data["deps"]["lemmas"] == [X]
    assert verdict.data["deps"]["declared"] == [DEP_A, DEP_B]
    staged = ctx.workdir / "src" / "Nodes" / PARENT / "Context.lean"
    assert f"import {layout.node_module(X, 'Proof')}" in staged.read_text(encoding="utf-8")


def test_the_same_proof_with_the_lemma_unproved_fails_to_elaborate_not_on_a_dependency(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    ctx = submission(tmp_path / "open", real_toolchain, lemma_proved=False)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail"
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code != "dep-unproved"
    assert "dep-unproved" not in str(verdict.as_dict())
    assert X_DECL in str(verdict.as_dict())  # the unknown identifier is the lemma's constant
