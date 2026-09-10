"""F01-Q4: staging the dependency closure — every way it fails before a single build (F00-R7)."""

from __future__ import annotations

import re
from pathlib import Path

from harness import make_context, node_dir

from opn_gate import layout, pipeline
from opn_gate.steps import stage as staging

ROOT = "and-swap-reassoc"
A, B = "tutorial-and-swap", "and-reassoc"


def set_deps(nodes: Path, node_id: str, deps: list[str]) -> None:
    meta = nodes / node_id / "META.yaml"
    text = meta.read_text()
    meta.write_text(re.sub(r"^deps: .*$", "deps: [" + ", ".join(deps) + "]", text, flags=re.M))


def test_dependency_cycle_fails_step4(tmp_path: Path) -> None:
    """A cycle through the declared deps is named with its path, and nothing is compiled."""
    ctx = make_context(tmp_path, node_id=A)
    nodes = node_dir(ctx).parent
    set_deps(nodes, A, [B])
    set_deps(nodes, B, [A])
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict
    d = verdict.diagnostic
    assert d is not None and d.code == "dep-cycle"
    assert f"{A} -> {B} -> {A}" in d.message
    assert not any(c.startswith("elaborate:") for c in ctx.toolchain.calls)  # type: ignore[attr-defined]


def test_transitive_dep_missing_fails_step4(tmp_path: Path) -> None:
    """Step 2 checks the node's own deps exist; a dep's dep that does not is caught when the
    closure is staged, naming it."""
    ctx = make_context(tmp_path, node_id=ROOT)
    set_deps(node_dir(ctx).parent, B, ["ghost"])
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    d = verdict.diagnostic
    assert d is not None and d.code == "dep-missing"
    assert "'ghost'" in d.message


def test_dep_with_invalid_meta_fails_step4(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id=ROOT)
    (node_dir(ctx).parent / B / "META.yaml").write_text("schema: meta/v9\nid: and-reassoc\n")
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    d = verdict.diagnostic
    assert d is not None and d.code == "dep-meta"
    assert B in d.message and "unknown schema" in d.message


def test_stage_reports_every_problem_and_a_shared_dep_once(tmp_path: Path) -> None:
    """Problems accumulate (all named, first one fails the step); a dep reached twice is staged
    once, so the build order has no duplicates."""
    ctx = make_context(tmp_path, node_id=ROOT)
    nodes = node_dir(ctx).parent
    set_deps(nodes, B, [A])  # both the root and B depend on A
    (nodes / A / "Proof.lean").unlink()
    (nodes / B / "Proof.lean").unlink()
    node = layout.load_node(nodes / ROOT, "propositional")
    assert isinstance(node, layout.Node)
    staged = staging.stage(node, tmp_path / "work")
    assert staged.order == (A, B, ROOT)
    assert [(p.code, p.details.get("dep")) for p in staged.problems] == [
        ("dep-unproved", A),
        ("dep-unproved", B),
    ]
    # The generated Context imports each declared dep's merged Proof and nothing else.
    text = (staged.node_dir(B) / "Context.lean").read_text()
    assert text.count("import ") == 1 and layout.node_module(A, "Proof") in text
    assert staging.generated_context([]).count("import ") == 0
