"""F07-T30, lean tier: a hole that binds under ``∃`` keeps its binder types (testers 2026-09-21).

The erdos-69 agent's crux bound two naturals and an integer under ``∃`` and used the integer
only through a cast to the reals. The extractor printed it
``∃ N k m, …``: the binder types were gone, ``m`` could be recovered only through its coercion, and
the text read back as a different type, so precheck refused the skeleton ``hole-not-roundtrip``.
The refusal was right; the printer was the defect. Probed at Lean 4.33.1 before any code
(``engineering/evidence/F07/task-30-probe.lean``): under ``pp.coercions.types`` and
``pp.numericTypes`` alone the shape below reads back as a DIFFERENT TYPE; with
``pp.funBinderTypes`` it round-trips.

Lean core only, like the rest of the propositional fixture (``Nat`` and ``Int``, no Mathlib).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, make_context
from test_finding_hole_roundtrip_lean import ROOT, SKELETON

from opn_gate import layout, pipeline
from opn_gate.paths import Change
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

#: The agent's shape in core Lean: three binders under ``∃``, one of them visible in the body only
#: through a coercion, behind a hypothesis so the expected witness type binds them too.
BODY = (
    "  intro p q r h\n"
    "  have crux : ∀ b : Nat, 0 < b → ∃ N k : Nat, ∃ m : Nat, "
    "((m : Int)) * 2 ≤ (N : Int) + k := sorry\n"
    "  exact ⟨h.2, ⟨h.1.2, h.1.1⟩⟩\n"
)


def write_skeleton(root: Path) -> None:
    node = layout.graph_nodes_dir(root, TARGET) / ROOT
    (node / "Proof.lean").unlink(missing_ok=True)
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / SKELETON).write_text(head + ":= by\n" + BODY, encoding="utf-8")


def test_an_exists_binder_keeps_its_type(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain
) -> None:
    del pinned
    ctx = make_context(
        tmp_path,
        node_id=ROOT,
        toolchain=real_toolchain,
        changes=[Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{SKELETON}")],
    )
    write_skeleton(ctx.graph_root)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    (hole,) = verdict.data["artifact"]["holes"]
    assert hole["closed_roundtrip"] is True, hole["closed_type"]
    assert "(m : Nat)" in hole["closed_type"], hole["closed_type"]
    # The witness slot is written from the expected witness type, which binds the statement's
    # variables and the hole's own (``b``; ``N``, ``k`` and ``m`` sit in the conclusion). Each
    # binder carries its type, so a slot with a binder its body never uses still elaborates (the
    # live slot read ``∃ N k, <identity>``, which has no type to infer).
    assert hole["expected_witness"] is not None
    assert "(b : Nat)" in hole["expected_witness"], hole["expected_witness"]
    assert "∃ p" not in hole["expected_witness"], hole["expected_witness"]
