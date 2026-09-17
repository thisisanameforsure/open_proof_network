"""F07-R19, T18, lean tier: the extractor prints a hole's type so that it reads back.

Whether a printed type elaborates to the same obligation is a question for Lean, so the fast tier
cannot ask it (F07-T7's rule: one lean-tier test per new Lean-facing seam). The hole here carries a
coercion, which is the shape that broke live: printed with `ppExpr`'s defaults, an `Int`-valued
cast of a `Nat` numeral loses its types and reads back over `Nat`, so the child node would state a
different proposition. Printed under `pp.coercions.types` and `pp.numericTypes` it carries its
types and reads back.

Lean core only, like the rest of the propositional fixture: no Mathlib checkout is needed. The
types are spelled `Nat` and `Int` for that reason, since the double-struck notations are Mathlib's
and do not resolve in the fixture's environment (`failed to synthesize OfNat`, probed 2026-09-17).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, make_context

from opn_gate import layout, pipeline
from opn_gate.paths import Change
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

ROOT = "and-swap-reassoc"
SKELETON = "20260917T000000Z-tester-partial.lean"
#: The hole is a coercion identity that has nothing to do with the goal, which is the point: it is
#: there to be printed. It is closed over the root's binders, as every hole is.
SKELETON_BODY = (
    "  intro p q r h\n"
    "  have cast_step : ((2 : Nat) : Int) + 0 = ((2 : Nat) : Int) := sorry\n"
    "  exact ⟨h.2, ⟨h.1.2, h.1.1⟩⟩\n"
)


def write_skeleton(root: Path) -> None:
    """The root without its proof, carrying the skeleton as its one attempt."""
    node = layout.graph_nodes_dir(root, TARGET) / ROOT
    (node / "Proof.lean").unlink(missing_ok=True)
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / SKELETON).write_text(head + ":= by\n" + SKELETON_BODY, encoding="utf-8")


def test_a_holes_printed_type_reads_back(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain
) -> None:
    """AC40: the printed closed type carries its coercion's type, and the extractor says it
    elaborates back to the hole's own obligation."""
    del pinned  # resolved by the fixture; the seam finds it itself
    ctx = make_context(
        tmp_path,
        node_id=ROOT,
        toolchain=real_toolchain,
        changes=[Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{SKELETON}")],
    )
    write_skeleton(ctx.graph_root)

    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()

    holes = verdict.data["artifact"]["holes"]
    assert [h["name"] for h in holes] == ["cast_step"]
    printed = holes[0]["closed_type"]
    # Printed under the options R19 requires: the coercion and the numerals name their types, so
    # the text means over `Int` what the hole meant over `Int`.
    assert "Int" in printed, printed
    assert holes[0]["closed_roundtrip"] is True, printed
