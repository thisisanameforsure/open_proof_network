"""Finding "record: duplicate hole", lean tier: the real tutorial pair through the real extractor.

The live skeleton (graph PR #33, 2026-09-13) sat on `variant-93e79cb5`, ``∀ p q : Prop, p ∧ q → p``,
and its first hole was ``have h₁ : q ∧ p := sorry`` — closed over the binders,
``∀ (p q : Prop), p ∧ q → q ∧ p``, which is the statement of ``tutorial-and-swap`` (the fixture's
``Statement.lean`` is byte-identical to the live one). The fast tier proves what the post-merge
job does with a ``defeq_sibling`` the fake reports; only this tier proves the extractor reports
it, because definitional equality is a question for Lean (F07-T7: one lean-tier test per new
Lean-facing seam). A strict xfail until F07-T7 gave the extractor the field (2026-09-14).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harness import TARGET, TUTORIAL, make_context

from opn_gate import layout, pipeline
from opn_gate.paths import Change
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

VARIANT = "and-left-of-and-swap"
VARIANT_STATEMENT = (
    "/-! A related variant of the tutorial node (D-30), in the live variant's shape. -/\n\n"
    "theorem OpnProp.and_left_of_and_swap : ∀ p q : Prop, p ∧ q → p := by\n  sorry\n"
)
TUTORIAL_LINE = "theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by"
SKELETON = "20260913T000000Z-tester-partial.lean"
#: h₁ is the tutorial's statement under the variant's binders; h₂ is nobody's.
SKELETON_BODY = (
    "  intro p q h\n  have h₁ : q ∧ p := sorry\n  have h₂ : p ∧ q := sorry\n  exact h₁.2\n"
)


def write_variant_with_skeleton(root: Path) -> None:
    """The variant beside the tutorial node, unproved, with the skeleton as its one attempt."""
    nodes = layout.graph_nodes_dir(root, TARGET)
    tutorial = nodes / TUTORIAL
    assert TUTORIAL_LINE in tutorial.joinpath("Statement.lean").read_text(encoding="utf-8")
    dest = nodes / VARIANT
    dest.mkdir()
    (dest / "Statement.lean").write_text(VARIANT_STATEMENT, encoding="utf-8")
    # The same hypotheses as the tutorial's, so its witness is this node's witness too.
    for name in ("Witness.lean", "Context.lean"):
        (dest / name).write_text((tutorial / name).read_text(encoding="utf-8"), encoding="utf-8")
    meta = yaml.safe_load((tutorial / "META.yaml").read_text())
    parsed = layout.parse_statement(VARIANT_STATEMENT)
    assert isinstance(parsed, layout.Statement)
    meta.update({"id": VARIANT, "statement-hash": parsed.statement_hash, "tutorial": False})
    (dest / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
    for d in layout.REQUIRED_DIRS:
        (dest / d).mkdir(exist_ok=True)
        (dest / d / layout.KEEP_FILE).write_text("")
    head, _, _ = VARIANT_STATEMENT.partition(":= by\n  sorry")
    (dest / "attempts" / SKELETON).write_text(head + ":= by\n" + SKELETON_BODY, encoding="utf-8")


def test_the_extractor_names_the_sibling_a_hole_restates(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    del pinned, lean_pkg  # resolved and built by the fixtures; the seam finds both itself
    ctx = make_context(
        tmp_path,
        node_id=VARIANT,
        toolchain=real_toolchain,
        changes=[Change("A", f"targets/{TARGET}/nodes/{VARIANT}/attempts/{SKELETON}")],
    )
    write_variant_with_skeleton(ctx.graph_root)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    holes = verdict.data["artifact"]["holes"]
    assert [h["name"] for h in holes] == ["h₁", "h₂"]
    assert holes[0]["closed_type"] == "∀ (p q : Prop), p ∧ q → q ∧ p"
    assert not any(h["defeq_goal"] for h in holes)  # neither is the variant's own goal
    assert holes[0].get("defeq_sibling") == TUTORIAL
    assert holes[1].get("defeq_sibling") is None
