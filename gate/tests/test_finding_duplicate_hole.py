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
pair. Held as strict xfails until F07-T7 lands; the consolidate guard passes today and must keep
passing, because the fix must not widen D-29's same-statement rule.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from fakes import FakeToolchain, artifact_result
from harness import TARGET, copy_graph
from test_cli_sandboxed import NODES, Seam, git_repo, run
from test_postmerge_apply import BODY, HOLES, ROOT, STAMP_FILE, WITNESS, argv

from opn_gate import cli, curator, layout, schemas
from opn_gate import graph as graphmod

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

REASON = (
    "finding record-duplicate-hole (F07-R6, D-12 #5, D-29): a hole whose closed type is an "
    "existing sibling's statement becomes a new --h<n> node instead of a dependency edge to that "
    "sibling; fix: F07-T7 (Mike, 2026-09-13)"
)


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


@pytest.mark.xfail(strict=True, reason=REASON)
def test_a_hole_that_restates_a_sibling_becomes_a_dep_not_a_child(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """No ``--h1`` directory; the parent depends on the sibling instead; the other hole still
    becomes ``--h2``; the postmerge JSON's ``partial`` block names the reuse per hole (the
    proposed shape: ``holes[i]`` with ``child`` and ``reused_node``, one of them null)."""
    root = merged_partial_beside_sibling(tmp_path)
    sibling_reported(seam)
    code, out, err = run(capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", AUTHOR))
    assert code == cli.EXIT_PASS, err
    nodes = root / NODES
    assert not (nodes / CHILD_1).exists(), "the restated hole must not become a node"
    assert (nodes / CHILD_2 / "Statement.lean").is_file()
    assert HOLES[1][1] in (nodes / CHILD_2 / "Statement.lean").read_text(encoding="utf-8")
    parent = yaml.safe_load((nodes / ROOT / "META.yaml").read_text())
    assert parent["deps"] == ["tutorial-and-swap", "and-reassoc", SIBLING, CHILD_2]
    # The regenerated Context carries the sibling's signature, verbatim (F01-R6), not a twin's.
    context = (nodes / ROOT / "Context.lean").read_text(encoding="utf-8")
    assert f"`{SIBLING}`" in context and "theorem OpnProp.reassoc_right" in context
    assert CHILD_1 not in context and f"`{CHILD_2}`" in context
    assert out["partial"]["children"] == [CHILD_2]
    assert out["partial"]["holes"] == [
        {"name": "right", "child": None, "reused_node": SIBLING},
        {"name": "left", "child": CHILD_2, "reused_node": None},
    ]


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_state_a_reused_hole_leaves_behind(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The products still load the target (the edge names a real node, no cycle); the sibling's
    own status is untouched by the merge; the surviving hole is blocked on its witness as any
    hole is; and the parent's status is derived from the sibling like any other dep — once every
    dep is proved the parent is ready, with no phantom ``--h1`` left to block it."""
    root = merged_partial_beside_sibling(tmp_path)
    sibling_reported(seam)
    code, _out, err = run(
        capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", AUTHOR)
    )
    assert code == cli.EXIT_PASS, err
    target = graphmod.load_target(root, TARGET)
    assert CHILD_1 not in target.nodes
    assert target.nodes[ROOT].deps == ("tutorial-and-swap", "and-reassoc", SIBLING, CHILD_2)
    assert target.statuses[SIBLING] == "ready"  # unproved, as before: the merge left it alone
    assert target.statuses[CHILD_2] == "blocked"
    causes = graphmod.derive_causes(target.nodes, target.statuses)
    assert causes[CHILD_2] == graphmod.CAUSE_WITNESS_MISSING
    assert target.statuses[ROOT] == "blocked"
    # A proved sibling does not block the parent: with every dep proved, the parent is ready.
    proved = graphmod.Proof(merge_commit="0" * 40, trust_base=graphmod.TRUST_KERNEL, attestation="")
    facts = {
        node_id: node
        if node_id == ROOT
        else replace(node, proof=proved, artifact="proof", witness_stub=False)
        for node_id, node in target.nodes.items()
    }
    assert graphmod.derive_statuses(facts)[ROOT] == "ready"


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
