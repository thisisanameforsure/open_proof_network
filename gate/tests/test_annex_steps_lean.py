"""F18-T5 (R6; AC8), lean tier: a stepped annex against the real extractor's hole names.

The fast tier (``test_annex_steps.py``) proves the rule over the fake seam's names. The names a
skeleton's holes carry are the extractor's (``opn-artifact-type``), and the refusal sits at the
end of step 4 because nothing earlier knows them, so this tier proves the names the real
extractor reports for ``have <id> : T := sorry`` are the ids a stepped annex names, and that a
hole no step names is refused there (one lean-tier test per new Lean-facing seam).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harness import TARGET, TUTORIAL, make_context
from test_annex_steps import place_annex

from opn_gate import layout, pipeline, schemas
from opn_gate.paths import Change
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

VARIANT = "and-left-of-and-swap"
VARIANT_STATEMENT = (
    "/-! A related variant of the tutorial node (D-30), as in the duplicate-hole test. -/\n\n"
    "theorem OpnProp.and_left_of_and_swap : ∀ p q : Prop, p ∧ q → p := by\n  sorry\n"
)
SKELETON = "20261003T000000Z-tester-partial.lean"


def annex_text(*ids: str) -> bytes:
    front = {
        "schema": "annex/v2",
        "node": VARIANT,
        "contributor": "tester",
        "licence": "CC-BY-4.0",
        "date": "2026-10-03T00:00:00Z",
        "model_and_tooling": None,
        "steps": [{"id": i, "summary": f"the step {i}"} for i in ids],
    }
    assert schemas.violations(front, "annex/v2") == []  # setup guard
    return f"---\n{yaml.safe_dump(front, sort_keys=True)}---\nTake the left conjunct.\n".encode()


def write_variant(root: Path, annex: bytes) -> None:
    """The variant beside the tutorial node, unproved, with a skeleton citing ``annex``."""
    nodes = layout.graph_nodes_dir(root, TARGET)
    tutorial = nodes / TUTORIAL
    dest = nodes / VARIANT
    dest.mkdir()
    (dest / "Statement.lean").write_text(VARIANT_STATEMENT, encoding="utf-8")
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
    digest = place_annex(dest, annex)
    head, _, _ = VARIANT_STATEMENT.partition(":= by\n  sorry")
    body = (
        f"  -- annex: {digest}\n"
        "  intro p q h\n"
        "  have swapped : q ∧ p := sorry\n"
        "  have kept : p ∧ q := sorry\n"
        "  exact swapped.2\n"
    )
    (dest / "attempts" / SKELETON).write_text(head + ":= by\n" + body, encoding="utf-8")


def run(tmp_path: Path, real_toolchain: LocalToolchain, annex: bytes):  # type: ignore[no-untyped-def]
    ctx = make_context(
        tmp_path,
        node_id=VARIANT,
        toolchain=real_toolchain,
        changes=[Change("A", f"targets/{TARGET}/nodes/{VARIANT}/attempts/{SKELETON}")],
    )
    write_variant(ctx.graph_root, annex)
    return pipeline.run_submission(ctx)


def test_the_real_extractors_hole_names_are_the_annexs_step_ids(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    del pinned, lean_pkg  # resolved and built by the fixtures; the seam finds both itself
    verdict = run(tmp_path, real_toolchain, annex_text("swapped", "combine", "kept"))
    assert verdict.verdict == "pass", verdict.as_dict()
    assert [h["name"] for h in verdict.data["artifact"]["holes"]] == ["swapped", "kept"]


def test_a_real_hole_no_step_names_is_refused_at_step_4(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    del pinned, lean_pkg
    verdict = run(tmp_path, real_toolchain, annex_text("swapped"))
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "annex-step-missing"
    assert verdict.diagnostic.details["missing"] == ["kept"]
    assert verdict.diagnostic.details["steps"] == ["swapped"]
