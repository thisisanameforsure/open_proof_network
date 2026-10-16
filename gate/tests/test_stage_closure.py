"""F28-T8: staging a dependency proved by closure (fast tier).

A node with a closure record and no ``Proof.lean`` is a proved dependency like any other: staging
does not refuse it, stages its merged assembly as its ``Proof.lean``, and marks it so the build
makes its module by the join (``join_module``) instead of compiling an assembly that has holes. A
claim or a variant closure stages the composed proof the record keeps, compiled like any proof.
"""

from __future__ import annotations

import json
from pathlib import Path

from fakes import FAKE_RESOLVED, FakeToolchain
from harness import TARGET, copy_graph

from opn_gate import closure, layout
from opn_gate.steps import stage as staging

ASSEMBLY = (
    "import Nodes.«and-reassoc».Context\n\n"
    "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n"
    "  intro p q r h\n  have hole : p ∧ (q ∧ r) := sorry\n  exact hole\n"
)


def closed_graph(tmp_path: Path, *, text: str | None = None) -> Path:
    """The fixture with ``and-reassoc``'s proof replaced by a closure record over an assembly
    (route) or over a composed proof (``text``, a claim or variant)."""
    root = copy_graph(tmp_path)
    node = layout.graph_nodes_dir(root, TARGET) / "and-reassoc"
    (node / "Proof.lean").unlink()
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / "a-partial.lean").write_text(ASSEMBLY, encoding="utf-8")
    record = closure.build(
        target_id=TARGET, node_id="and-reassoc", statement_hash="a" * 64,
        link=closure.Link("route" if text is None else "variant", "and-reassoc@1",
                          ("tutorial-and-swap",)),
        source_path=None if text is not None else "attempts/a-partial.lean",
        source_text=text, source_hash="b" * 64, axioms=[], graph_commit="c" * 40,
        network_commit=None, lean_toolchain="leanprover/lean4:v4.33.1", mathlib_sha=None,
        timestamp="2026-10-15T12:00:00Z",
    )  # fmt: skip
    closure.write(node, record)
    return root


def stage_dependent(root: Path, tmp_path: Path) -> staging.Staged:
    node = layout.load_node(layout.graph_nodes_dir(root, TARGET) / "and-swap-reassoc", TARGET)
    assert not isinstance(node, list)
    return staging.stage(node, tmp_path / "work")


def test_a_route_closure_is_staged_as_its_assembly_and_marked_to_join(tmp_path: Path) -> None:
    staged = stage_dependent(closed_graph(tmp_path), tmp_path)
    assert staged.problems == ()
    assert "and-reassoc" in staged.order
    assert staged.joined == {
        "and-reassoc": staging.Joined(
            decl="OpnProp.and_reassoc", children=(("tutorial-and-swap", "OpnProp.and_swap"),)
        )
    }
    staged_proof = staged.root / staged.rel("and-reassoc", "Proof")
    assert staged_proof.read_text(encoding="utf-8") == ASSEMBLY


def test_a_link_closure_stages_its_composed_proof_and_compiles_it(tmp_path: Path) -> None:
    text = "theorem OpnProp.and_reassoc : True := trivial\n"
    staged = stage_dependent(closed_graph(tmp_path, text=text), tmp_path)
    assert staged.problems == () and staged.joined == {}
    assert (staged.root / staged.rel("and-reassoc", "Proof")).read_text(encoding="utf-8") == text


def test_without_a_record_the_dependency_is_still_unproved(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    (layout.graph_nodes_dir(root, TARGET) / "and-reassoc" / "Proof.lean").unlink()
    staged = stage_dependent(root, tmp_path)
    assert [p.code for p in staged.problems] == ["dep-unproved"]


def test_the_join_is_asked_for_the_module_the_dependents_import(tmp_path: Path) -> None:
    staged = stage_dependent(closed_graph(tmp_path), tmp_path)
    fake = FakeToolchain()
    staging.join_module(fake, FAKE_RESOLVED, staged, "and-reassoc", timeout_s=60)
    [req] = fake.close_requests
    assert req.module == "Nodes.«and-reassoc».Proof"
    assert req.decl == "OpnProp.and_reassoc"
    assert req.file == staged.root / staged.rel("and-reassoc", "Proof")
    assert req.out_olean.is_relative_to(staged.build) and req.out_olean.name == "Proof.olean"
    assert json.loads(req.children.read_text(encoding="utf-8")) == [
        {"node": "tutorial-and-swap", "decl": "OpnProp.and_swap"}
    ]


def test_no_submission_may_write_a_closure_record() -> None:
    """Only the post-merge job writes ``closure.json`` (signed with the gate key); like
    ``CONTEXT.json`` it has no role, so every mode refuses a pull request that touches it."""
    from opn_gate import paths  # noqa: PLC0415

    assert paths.locate("targets/t/nodes/n/closure.json") is None
