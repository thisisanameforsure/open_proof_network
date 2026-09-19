"""Finding "record: duplicate hole" (the 2026-09-13 live contribution, seen from the record side):
a skeleton's first hole was the tutorial's own proved theorem, and the post-merge job created a
blocked node for it (`variant-93e79cb5--h1`, byte for byte the statement of `tutorial-and-swap`).

Mike's decision (2026-09-13): a hole whose closed type is definitionally the statement of an
existing node in the target becomes a dependency edge to that node, and no ``--h<n>`` node. The
test is the one the offload rule already applies to the parent's goal (``defeq_goal``,
``steps/artifact.py``), generalised to any sibling statement: the extractor reports it per hole
as ``defeq_sibling: <node-id> | null``, computed in the sandbox over the sibling statements staged
into the work directory. Near-duplicates stay curator ``consolidate`` (D-12, D-29).

Fast tier: ``FakeToolchain`` reports the new field; these tests prove the plumbing from the
metaprogram's answer to what the merge leaves in the checkout. The lean tier
(``test_finding_duplicate_hole_lean.py``) proves the extractor answers it for the real tutorial
pair. Held as strict xfails until F07-T7 landed (2026-09-14); the consolidate guard passed before
and must keep passing, because the fix must not widen D-29's same-statement rule. The edges at
the end are F07-T7's own: which siblings are asked about, where their probes are staged, and what
the job refuses before it writes anything.

Revised 2026-09-19 (F07-T21, D-12 v3.19): a decomposition never blocks the node it decomposes,
so a restated sibling that is not one of the parent's own holes is still no child — but it is no
edge either, because an edge the parent would wait on is exactly what a route must not add. The
reuse is on the record in the job's ``holes`` block; the parent's deps and Context carry only
its declared deps and its own holes.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from fakes import FakeToolchain, artifact_result
from harness import TARGET, TUTORIAL, copy_graph
from test_cli_sandboxed import NODES, Seam, git_repo, run
from test_postmerge_apply import BODY, HOLES, ROOT, STAMP_FILE, WITNESS, argv

from opn_gate import cli, curator, layout, postmerge, schemas
from opn_gate import graph as graphmod
from opn_gate.steps import artifact as art
from opn_gate.toolchain import ArtifactRequest

#: The sibling whose statement is the first hole's closed type (``right`` in ``HOLES``).
SIBLING = "reassoc-right"
SIBLING_STATEMENT = (
    "/-! The right conjunct of a reassociation, stated on its own. -/\n\n"
    f"theorem OpnProp.reassoc_right : {HOLES[0][1]} := by\n  sorry\n"
)
CHILD_1 = f"{ROOT}--h1"
CHILD_2 = f"{ROOT}--h2"
AUTHOR = "curator"
DATE = "2026-09-13T00:00:00Z"


def clone_node(root: Path, source: str, new_id: str, *, statement: str) -> Path:
    """A node beside ``source`` with ``statement`` as its ``Statement.lean`` and the rest copied —
    the shape ``test_curator_lean.clone_node`` uses, kept local so no test file edits another."""
    nodes = layout.graph_nodes_dir(root, TARGET)
    dest = nodes / new_id
    dest.mkdir()
    for name in ("Witness.lean", "Context.lean"):
        (dest / name).write_text(
            (nodes / source / name).read_text().replace(f"«{source}»", f"«{new_id}»")
        )
    (dest / "Statement.lean").write_text(statement)
    meta = yaml.safe_load((nodes / source / "META.yaml").read_text())
    meta["id"] = new_id
    parsed = layout.parse_statement(statement)
    assert isinstance(parsed, layout.Statement)
    meta["statement-hash"] = parsed.statement_hash
    (dest / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    for d in layout.REQUIRED_DIRS:
        (dest / d).mkdir()
        (dest / d / layout.KEEP_FILE).write_text("")
    return dest


def declare_root(root: Path) -> None:
    """A ``target-status/v2`` record naming the root, the way a curator declares one (F11-R14)."""
    doc = {
        "schema": "target-status/v2",
        "status": "active",
        "root": ROOT,
        "cause": "the root, declared beside a sibling nothing depends on yet (F08-Q19)",
        "author": AUTHOR,
        "date": DATE[:10],
    }
    assert schemas.violations(doc, "target-status/v2") == []
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / f"{DATE[:10]}-{AUTHOR}.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )


def merged_partial_beside_sibling(tmp_path: Path) -> Path:
    """A repo whose HEAD merges the assembly of ``test_postmerge_apply`` onto the unproved root,
    with a sibling node whose statement is the first hole's closed type already in the tree."""
    root, git, _base = git_repo(tmp_path)
    node = root / NODES / ROOT
    (node / "Proof.lean").unlink(missing_ok=True)
    # ``and-reassoc`` carries no import line, so the clone needs no module rename.
    clone_node(root, "and-reassoc", SIBLING, statement=SIBLING_STATEMENT)
    # A sibling nothing depends on yet is a second sink, so the root is declared (F08-Q19).
    declare_root(root)
    git("add", "-A")
    git("commit", "-q", "-m", "the root, unproved, beside the statement its first hole restates")
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / STAMP_FILE).write_text(head + ":= by\n" + BODY, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", f"partial: {ROOT}")
    return root


def sibling_reported(seam: Seam) -> None:
    """The extractor's answer once F07-T7 lands: the first hole is ``SIBLING``'s statement, the
    second is nobody's. Injected into the doc rather than through ``artifact_result``'s
    signature, which does not know the field yet."""
    report = artifact_result(holes=HOLES)
    report.doc["holes"][0]["defeq_sibling"] = SIBLING
    report.doc["holes"][1]["defeq_sibling"] = None
    seam.fake = FakeToolchain(witness=WITNESS, artifact=report)


def test_a_hole_that_restates_a_sibling_becomes_a_dep_not_a_child(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """No ``--h1`` directory and, since T21, no edge to the sibling either; the other hole still
    becomes ``--h2``; the postmerge JSON's ``partial`` block names the reuse per hole
    (``holes[i]`` with ``child`` and ``reused_node``, one of them null)."""
    root = merged_partial_beside_sibling(tmp_path)
    sibling_reported(seam)
    code, out, err = run(capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", AUTHOR))
    assert code == cli.EXIT_PASS, err
    nodes = root / NODES
    assert not (nodes / CHILD_1).exists(), "the restated hole must not become a node"
    assert (nodes / CHILD_2 / "Statement.lean").is_file()
    assert HOLES[1][1] in (nodes / CHILD_2 / "Statement.lean").read_text(encoding="utf-8")
    parent = yaml.safe_load((nodes / ROOT / "META.yaml").read_text())
    assert parent["deps"] == ["tutorial-and-swap", "and-reassoc", CHILD_2]
    # The regenerated Context carries the surviving hole's signature and no twin of the sibling.
    context = (nodes / ROOT / "Context.lean").read_text(encoding="utf-8")
    assert f"`{SIBLING}`" not in context and "theorem OpnProp.reassoc_right" not in context
    assert CHILD_1 not in context and f"`{CHILD_2}`" in context
    assert out["partial"]["children"] == [CHILD_2]
    assert out["partial"]["holes"] == [
        {"name": "right", "child": None, "reused_node": SIBLING},
        {"name": "left", "child": CHILD_2, "reused_node": None},
    ]


def test_the_state_a_reused_hole_leaves_behind(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The products still load the target; the sibling's own status is untouched by the merge;
    the surviving hole is blocked on its witness as any hole is; and the parent waits on
    neither (T21): with its declared deps proved it is ready while the sibling and the hole are
    still open, with no phantom ``--h1`` anywhere."""
    root = merged_partial_beside_sibling(tmp_path)
    sibling_reported(seam)
    code, _out, err = run(
        capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", AUTHOR)
    )
    assert code == cli.EXIT_PASS, err
    target = graphmod.load_target(root, TARGET)
    assert CHILD_1 not in target.nodes
    assert target.nodes[ROOT].deps == ("tutorial-and-swap", "and-reassoc", CHILD_2)
    assert target.nodes[ROOT].holes == (CHILD_2,)
    assert target.statuses[SIBLING] == "ready"  # unproved, as before: the merge left it alone
    assert target.statuses[CHILD_2] == "blocked"
    causes = graphmod.derive_causes(target.nodes, target.statuses)
    assert causes[CHILD_2] == graphmod.CAUSE_WITNESS_MISSING
    # The parent waits on its declared deps only: with those two proved it is ready while its
    # hole and the restated sibling are both still open (D-12 v3.19).
    proved = graphmod.Proof(merge_commit="0" * 40, trust_base=graphmod.TRUST_KERNEL, attestation="")
    facts = {
        node_id: replace(node, proof=proved, artifact="proof", witness_stub=False)
        if node_id in ("tutorial-and-swap", "and-reassoc")
        else node
        for node_id, node in target.nodes.items()
    }
    statuses = graphmod.derive_statuses(facts)
    assert statuses[ROOT] == "ready" and statuses[CHILD_2] == "blocked"


def test_consolidate_still_takes_two_identical_statements(tmp_path: Path) -> None:
    """Guard (passes today, must keep passing): the fix lives in the post-merge job, and D-29's
    curator consolidation of two byte-identical statements is untouched by it."""
    root = copy_graph(tmp_path)
    nodes = layout.graph_nodes_dir(root, TARGET)
    original = (nodes / "and-reassoc" / "Statement.lean").read_text(encoding="utf-8")
    clone_node(root, "and-reassoc", "and-reassoc-again", statement=original)
    record = curator.consolidate(
        root, TARGET, "and-reassoc", "and-reassoc-again", author=AUTHOR, date=DATE
    )
    doc = yaml.safe_load(record.read_text(encoding="utf-8"))
    assert doc["status"] == "superseded" and doc["reference"] == "and-reassoc"
    assert "identical statement" in doc["cause"]
    assert record.parent == nodes / "and-reassoc-again" / "status"


# --- F07-T7 edges -----------------------------------------------------------------------------


def test_siblings_leave_out_the_node_its_dependents_and_the_superseded(tmp_path: Path) -> None:
    """An edge from a parent to a node that depends on it, however indirectly, would close a
    cycle; a superseded node's statement lives on in its successor (D-29). Neither is asked."""
    root = copy_graph(tmp_path)
    nodes = layout.graph_nodes_dir(root, TARGET)
    tutorial = (nodes / TUTORIAL / "Statement.lean").read_text(encoding="utf-8")
    clone_node(root, "and-reassoc", "tutorial-again", statement=tutorial)
    curator.consolidate(root, TARGET, TUTORIAL, "tutorial-again", author=AUTHOR, date=DATE)
    # A node two edges above and-reassoc: reassoc-top -> and-swap-reassoc -> and-reassoc.
    clone_node(root, "and-reassoc", "reassoc-top", statement=SIBLING_STATEMENT)
    meta_path = nodes / "reassoc-top" / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = [ROOT]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False))

    assert art.sibling_candidates(nodes, "and-reassoc") == [TUTORIAL]
    assert art.sibling_candidates(nodes, ROOT) == ["and-reassoc", TUTORIAL]
    assert art.sibling_candidates(nodes, "reassoc-top") == ["and-reassoc", ROOT, TUTORIAL]


def test_a_sibling_probe_has_no_imports_and_a_name_of_its_own(tmp_path: Path) -> None:
    """Elaborated on the parent's imports, a probe under its own name could redeclare a dep's
    statement the parent's Context imports; so it carries no import and the probe's name."""
    root = copy_graph(tmp_path)
    text = (layout.graph_nodes_dir(root, TARGET) / ROOT / "Statement.lean").read_text("utf-8")
    assert layout.imports_of(text) == [f"Nodes.«{ROOT}».Context"]
    probe = art.sibling_probe(text)
    assert layout.imports_of(probe) == []
    assert layout.parse_declaration(probe) == art.SIBLING_PROBE_NAME
    assert "OpnProp.and_swap_reassoc" not in probe
    assert f"theorem {art.SIBLING_PROBE_NAME} : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)" in probe
    namespaced = "namespace Opn\n\ntheorem thing : True := by\n  sorry\n\nend Opn\n"
    assert layout.parse_declaration(art.sibling_probe(namespaced)) == "Opn.OpnSibling.probe"


def test_a_partial_run_stages_each_sibling_in_the_work_directory(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The sandbox reads the work directory and the node under check, nothing else, so the probes
    and their manifest are written there; the parent is never among them."""
    root = merged_partial_beside_sibling(tmp_path)
    sibling_reported(seam)
    code, _out, err = run(
        capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", AUTHOR)
    )
    assert code == cli.EXIT_PASS, err
    [manifest] = list((tmp_path / "o").rglob(art.SIBLINGS_MANIFEST))
    assert manifest.parent.name == art.SIBLINGS_DIR
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    assert [e["node"] for e in entries] == ["and-reassoc", SIBLING, TUTORIAL]
    for entry in entries:
        probe = (manifest.parent / entry["file"]).read_text(encoding="utf-8")
        assert layout.imports_of(probe) == [] and entry["decl"] == art.SIBLING_PROBE_NAME


def test_the_extractor_is_asked_about_siblings_only_when_they_are_staged(tmp_path: Path) -> None:
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
    assert "--siblings" not in base.args()
    staged = replace(base, siblings=tmp_path / "siblings.json")
    assert staged.args() == [
        *base.args(),
        "--siblings",
        str((tmp_path / "siblings.json").resolve()),
    ]


@pytest.mark.parametrize("named", ["no-such-node", ROOT])
def test_a_hole_restating_no_other_node_is_refused_before_anything_is_written(
    tmp_path: Path, named: str
) -> None:
    """An edge to nothing, or from the parent to itself, would corrupt the DAG; the refusal comes
    before the first hole's child is written, so the checkout is as the merge left it (C7)."""
    root = copy_graph(tmp_path)
    node_dir = layout.graph_nodes_dir(root, TARGET) / ROOT
    before = {n: (node_dir / n).read_text(encoding="utf-8") for n in ("META.yaml", "Context.lean")}
    holes = [
        art.Hole(name="right", type="r", closed_type=HOLES[0][1], defeq_goal=False),
        art.Hole(
            name="left",
            type="q ∧ p",
            closed_type=HOLES[1][1],
            defeq_goal=False,
            defeq_sibling=named,
        ),
    ]
    with pytest.raises(postmerge.GraphWriteError, match="not another node"):
        postmerge.apply_partial(
            node_dir,
            holes,
            partial_text="theorem OpnProp.and_swap_reassoc : True := by\n  sorry\n",
            pseudonym="someone",
            stamp="20260914T000000Z",
            assembly_path=f"attempts/{STAMP_FILE}",
        )
    assert not (node_dir.parent / CHILD_1).exists()
    assert {n: (node_dir / n).read_text(encoding="utf-8") for n in before} == before
