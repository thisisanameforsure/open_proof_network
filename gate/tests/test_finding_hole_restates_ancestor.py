"""Finding "a hole may restate an ancestor" (the nine testers, 2026-09-23): D-12's offload rule
compared each hole with the node's *own* goal only, so a partial could hand back any statement
above it as a hole and the statement graph would grow a cycle — the root waiting on a grandchild
that waits on the root. On the live graph ``erdos-1050``'s chain root → ``erdos-1050--h1-v2`` →
hole ``erdos-1050--h1-v2--h1`` came back to the root (up to a proved reindexing), and
``erdos-69``'s ``h4`` was the target by a real argument. Neither is definitional equality, and
that part is a separate task (a gate-checked circularity claim). This file is the mechanical
part (F07-T34): a hole definitionally equal — the same transparency ladder as ``defeq_goal`` — to
the statement of *any* ancestor of the node it decomposes is refused at step 4 with
``offload-restates-ancestor``, naming the hole and the ancestor.

Ancestors are the node's transitive dependents over ``META.yaml``'s ``deps``, each read through
its revision chain (``graph.effective_deps``); a superseded ancestor is asked about in its
successor's statement, the one the graph means now. They are staged into the work directory as
probes with a manifest the way F07-T7's siblings are (the sandbox sees the node under check and
the work directory, nothing else), and the extractor answers ``defeq_ancestor`` per hole on its
stdout. ``sibling_candidates`` already left every ancestor out ("an edge from the parent to it
would close a cycle"), which is why a hole restating one was reported as nobody's and passed.

Fast tier: the fake reports the field and these tests prove the plumbing — what is staged, what
the request asks, what step 4 decides. ``test_finding_hole_restates_ancestor_lean.py`` proves the
extractor answers it for a real three-level chain.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from fakes import FakeToolchain, artifact_result, witness_result
from harness import TARGET, TUTORIAL, make_context

from opn_gate import curator, layout, pipeline
from opn_gate.paths import Change
from opn_gate.steps import artifact as art
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ArtifactRequest

ROOT = "and-swap-reassoc"  # the fixture's root; deps [tutorial-and-swap, and-reassoc]
PARENT = "and-reassoc"
#: A node beneath ``and-reassoc``, so the chain is ROOT → PARENT → LEAF: three levels.
LEAF = "and-left-of-and"
LEAF_STATEMENT = (
    "/-! A leaf beneath and-reassoc: the chain root → and-reassoc → this node. -/\n\n"
    "theorem OpnProp.and_left_of_and : ∀ p q : Prop, p ∧ q → p := by\n  sorry\n"
)
ROOT_TYPE = "∀ (p q r : Prop), (p ∧ q) ∧ r → r ∧ q ∧ p"
STAMP = "20260923T120000Z-someone-partial.lean"
WITNESS = witness_result(expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q")
#: ``up`` restates the root; ``fresh`` is nobody's.
HOLES = [("up", ROOT_TYPE, False), ("fresh", "∀ (p q : Prop), p ∧ q → p ∧ True", False)]
AUTHOR = "curator"
DATE = "2026-09-23"


def add_node(nodes: Path, node_id: str, statement: str, *, deps: list[str]) -> Path:
    """A node with ``statement``, the tutorial's witness and an empty Context — the tutorial's
    hypotheses are ``p ∧ q``, and so are every statement's here."""
    tutorial = nodes / TUTORIAL
    dest = nodes / node_id
    dest.mkdir()
    (dest / "Statement.lean").write_text(statement, encoding="utf-8")
    for name in ("Witness.lean", "Context.lean"):
        (dest / name).write_text((tutorial / name).read_text(encoding="utf-8"), encoding="utf-8")
    meta = yaml.safe_load((tutorial / "META.yaml").read_text(encoding="utf-8"))
    parsed = layout.parse_statement(statement)
    assert isinstance(parsed, layout.Statement)
    meta.update(
        {"id": node_id, "statement-hash": parsed.statement_hash, "tutorial": False, "deps": deps}
    )
    (dest / "META.yaml").write_text(
        yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    for d in layout.REQUIRED_DIRS:
        (dest / d).mkdir(exist_ok=True)
        (dest / d / layout.KEEP_FILE).write_text("")
    return dest


def set_deps(nodes: Path, node_id: str, deps: list[str]) -> None:
    path = nodes / node_id / "META.yaml"
    meta = yaml.safe_load(path.read_text(encoding="utf-8"))
    meta["deps"] = deps
    path.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8")


def supersede(nodes: Path, old: str, new: str) -> None:
    """``old`` superseded by ``new``, the record ``revise`` writes (D-8)."""
    path = curator.record_path(nodes / old, author=AUTHOR, date=DATE)
    doc = curator.node_status_doc(
        "superseded", f"superseded by {new} (D-8)", author=AUTHOR, date=DATE, reference=new
    )
    path.parent.mkdir(exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def leaf_partial(tmp_path: Path, fake: FakeToolchain) -> RunContext:
    """The chain ROOT → PARENT → LEAF, and one partial on LEAF under ``attempts/``."""
    changes = [Change("A", f"targets/{TARGET}/nodes/{LEAF}/attempts/{STAMP}")]
    ctx = make_context(tmp_path, node_id=LEAF, toolchain=fake, changes=changes)
    nodes = layout.graph_nodes_dir(ctx.graph_root, TARGET)
    leaf = add_node(nodes, LEAF, LEAF_STATEMENT, deps=[])
    set_deps(nodes, PARENT, [LEAF])
    head, _, _ = LEAF_STATEMENT.partition(":= by\n  sorry")
    body = (
        f"  have up : {ROOT_TYPE} := sorry\n"
        "  have fresh : ∀ p q : Prop, p ∧ q → p ∧ True := sorry\n"
        "  intro p q h\n  exact (fresh p q h).1\n"
    )
    (leaf / "attempts" / STAMP).write_text(head + ":= by\n" + body, encoding="utf-8")
    return ctx


def reporting(ancestor: str | None, *, hole: int = 0) -> FakeToolchain:
    """The extractor's answer: hole ``hole`` restates ``ancestor``, the rest nobody."""
    report = artifact_result(decl="OpnProp.and_left_of_and", holes=HOLES)
    for h in report.doc["holes"]:
        h["defeq_ancestor"] = None
    report.doc["holes"][hole]["defeq_ancestor"] = ancestor
    return FakeToolchain(witness=WITNESS, artifact=report)


# --- the defect -------------------------------------------------------------------------------


@pytest.mark.parametrize("ancestor", [ROOT, PARENT])
def test_a_hole_restating_an_ancestor_is_refused_at_step_4(tmp_path: Path, ancestor: str) -> None:
    """The grandchild's hole is the root's statement (or the parent's): a cycle, refused by name.
    Before F07-T34 the verdict was a pass, because the goal check sees only the leaf's own goal."""
    ctx = leaf_partial(tmp_path, reporting(ancestor))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "offload-restates-ancestor"
    assert verdict.diagnostic.details["holes"] == ["up"]
    assert verdict.diagnostic.details["restated"] == [{"hole": "up", "ancestor": ancestor}]
    assert "up" in verdict.diagnostic.message and ancestor in verdict.diagnostic.message
    assert {s.result for s in verdict.steps if s.step > 4} == {"skipped"}
    # The record the verdict carries keeps every hole with its answer.
    holes = ctx.data[art.ARTIFACT_KEY]["holes"]
    assert [h["defeq_ancestor"] for h in holes] == [ancestor, None]


def test_a_partial_run_stages_every_ancestor_in_the_work_directory(tmp_path: Path) -> None:
    """The sandbox reads the work directory and the node under check, nothing else, so each
    ancestor's statement is staged there as a probe, nearest first, with a manifest the extractor
    is pointed at. The unrelated tutorial node is a sibling, not an ancestor."""
    ctx = leaf_partial(tmp_path, reporting(None))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    manifests = list(ctx.workdir.rglob(art.ANCESTORS_MANIFEST))
    assert len(manifests) == 1, manifests
    manifest = manifests[0]
    assert manifest.parent.name == art.ANCESTORS_DIR
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    assert [e["node"] for e in entries] == [PARENT, ROOT]
    for entry in entries:
        probe = (manifest.parent / entry["file"]).read_text(encoding="utf-8")
        assert layout.imports_of(probe) == [] and entry["decl"] == art.SIBLING_PROBE_NAME
    root_probe = (manifest.parent / entries[1]["file"]).read_text(encoding="utf-8")
    assert "(p ∧ q) ∧ r → r ∧ (q ∧ p)" in root_probe
    siblings = json.loads(next(ctx.workdir.rglob(art.SIBLINGS_MANIFEST)).read_text("utf-8"))
    assert [e["node"] for e in siblings] == [TUTORIAL]


def test_a_superseded_ancestor_is_asked_about_in_its_successor(tmp_path: Path) -> None:
    """D-8: once the parent is revised, the root's dep reads through to the revision, and the
    revision's statement is the one a hole must not restate. The superseded node is not staged:
    its statement is no longer what the graph means."""
    ctx = leaf_partial(tmp_path, reporting(None))
    nodes = layout.graph_nodes_dir(ctx.graph_root, TARGET)
    revised = "and-reassoc-v2"
    add_node(
        nodes,
        revised,
        "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → (p ∧ q) ∧ r := by\n  sorry\n",
        deps=[LEAF],
    )
    supersede(nodes, PARENT, revised)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    manifest = next(ctx.workdir.rglob(art.ANCESTORS_MANIFEST))
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    assert [e["node"] for e in entries] == [revised, ROOT]
    probe = (manifest.parent / entries[0]["file"]).read_text(encoding="utf-8")
    assert "(p ∧ q) ∧ r → (p ∧ q) ∧ r" in probe


# --- what the fix must not change ---------------------------------------------------------------


def test_a_hole_restating_a_sibling_that_is_no_ancestor_still_passes(tmp_path: Path) -> None:
    """Guard: F07-T7's reuse of a sibling statement is an edge to a node beside the parent, no
    cycle, and stays a pass (the post-merge job wires it)."""
    fake = reporting(None)
    fake.artifact.doc["holes"][1]["defeq_sibling"] = TUTORIAL
    ctx = leaf_partial(tmp_path, fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()


def test_a_report_without_the_field_passes_as_before(tmp_path: Path) -> None:
    """D-35: an extractor pinned before the check reports no field; its holes restate nobody."""
    report = artifact_result(decl="OpnProp.and_left_of_and", holes=HOLES)
    ctx = leaf_partial(tmp_path, FakeToolchain(witness=WITNESS, artifact=report))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert all(h["defeq_ancestor"] is None for h in ctx.data[art.ARTIFACT_KEY]["holes"])


def test_a_node_with_no_dependents_stages_no_ancestors(tmp_path: Path) -> None:
    """The root has nothing above it: no manifest, and the request carries no flag."""
    nodes = layout.graph_nodes_dir(make_context(tmp_path).graph_root, TARGET)
    assert art.ancestor_candidates(nodes, ROOT) == []
    assert art.ancestor_candidates(nodes, PARENT) == [ROOT]
    assert art.ancestor_candidates(nodes, TUTORIAL) == [ROOT]


def test_ancestors_climb_every_path_once_and_survive_a_cycle(tmp_path: Path) -> None:
    """A diamond reaches the root by two paths and names it once; a cycle already in the record
    (the defect this rule exists to stop) does not loop the walk, and the node is never its own
    ancestor — its own goal is ``defeq_goal``'s question."""
    nodes = layout.graph_nodes_dir(make_context(tmp_path).graph_root, TARGET)
    add_node(nodes, LEAF, LEAF_STATEMENT, deps=[])
    set_deps(nodes, PARENT, [LEAF])
    set_deps(nodes, TUTORIAL, [LEAF])
    assert art.ancestor_candidates(nodes, LEAF) == [PARENT, TUTORIAL, ROOT]
    set_deps(nodes, LEAF, [ROOT])
    assert art.ancestor_candidates(nodes, LEAF) == [PARENT, TUTORIAL, ROOT]


def test_the_extractor_is_asked_about_ancestors_only_when_they_are_staged(tmp_path: Path) -> None:
    """No manifest, no flag: the request an older caller builds is byte for byte what it was."""
    base = ArtifactRequest(
        statement=tmp_path / "Statement.lean",
        statement_module="S",
        decl="d",
        artifact=tmp_path / "Proof.lean",
        artifact_module="P",
        artifact_decl="d",
        kind="partial",
    )
    assert "--ancestors" not in base.args()
    staged = replace(base, ancestors=tmp_path / "ancestors.json")
    assert staged.args() == [
        *base.args(),
        "--ancestors",
        str((tmp_path / "ancestors.json").resolve()),
    ]
