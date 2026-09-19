"""F08-T10, lean tier: a parent is finalized over its *revised* child, by the real gate.

The fast tier (``test_finding_revised_hole_parent.py``) proves the derivation; this proves the
thing the contributor could not do. The tree is the live shape: the original child never had a
proof (a mis-generated hole cannot be proved as written), a curator revised it, and the revision
was proved. Before F08-T10 the parent's proof failed step 4 with ``dep-unproved``, because
staging walked ``META.yaml``'s deps to the dead child; now staging builds the parent against the
revision's proof, and steps 1 to 8 pass with ``META.yaml`` untouched.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from harness import TARGET
from test_finding_b_revise_v2 import AUTHOR, DATE, NEW_STATEMENT, v1_request_doc, write_doc
from test_pregate_lean import git_graph, run_pregate_node

from opn_gate import curator, layout, postmerge

pytestmark = pytest.mark.lean

ROOT = "and-swap-reassoc"
DEP = "and-reassoc"
PROOF_BODY = "  intro p q r h\n  exact ⟨h.1.1, h.1.2, h.2⟩\n"


def revised_tree(tmp_path: Path) -> tuple[Path, str, bytes]:
    """A graph in the live shape, in two commits, as it would happen: first the merged history
    (the original child unproved and superseded, its revision proved, contexts current, the
    parent not yet proved), then the submission, which is the parent's ``Proof.lean`` alone.
    Returns the graph, the submission's commit and the parent's ``META.yaml`` as it was before
    any of it."""
    graph = git_graph(tmp_path)
    nodes = layout.graph_nodes_dir(graph, TARGET)
    (nodes / DEP / "Proof.lean").unlink()  # the live shape: the original was never proved
    meta_before = (nodes / ROOT / "META.yaml").read_bytes()

    request = write_doc(graph, DEP, v1_request_doc(DEP))
    revision = curator.revise(graph, TARGET, DEP, NEW_STATEMENT, request, author=AUTHOR, date=DATE)
    proof = NEW_STATEMENT.replace("  sorry\n", PROOF_BODY)
    assert proof != NEW_STATEMENT
    (nodes / revision.new_id / "Proof.lean").write_text(proof, encoding="utf-8")
    postmerge.refresh_contexts(nodes)
    parent_proof = (nodes / ROOT / "Proof.lean").read_text(encoding="utf-8")
    (nodes / ROOT / "Proof.lean").unlink()
    # The tree's preconditions go in a commit of their own: pregate reads uncommitted changes as
    # the submission and reproduce reads a commit's diff as one (2026-09-12), and a curator's
    # revision is merged history, not part of anyone's submission.
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    for cmd in (["add", "-A"], ["commit", "-q", "-m", "the revision, proved, contexts current"]):
        subprocess.run(["git", "-C", str(graph), *cmd], check=True, env=env)
    (nodes / ROOT / "Proof.lean").write_text(parent_proof, encoding="utf-8")
    for cmd in (["add", "-A"], ["commit", "-q", "-m", "proof: the parent, over its revised child"]):
        subprocess.run(["git", "-C", str(graph), *cmd], check=True, env=env)
    head = subprocess.run(
        ["git", "-C", str(graph), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()
    return graph, head, meta_before


ALL_STEPS_PASS = [
    (1, "pass"),
    (2, "pass"),
    (4, "pass"),
    (5, "pass"),
    (6, "pass"),
    (7, "pass"),
    (8, "pass"),
]


def test_the_parent_passes_every_step_against_the_revision(tmp_path: Path) -> None:
    graph, _commit, meta_before = revised_tree(tmp_path)
    code, summary = run_pregate_node(graph, ROOT, tmp_path / "out")
    assert code == 0, summary
    assert [(s["step"], s["result"]) for s in summary["steps"]] == ALL_STEPS_PASS
    nodes = layout.graph_nodes_dir(graph, TARGET)
    assert (nodes / ROOT / "META.yaml").read_bytes() == meta_before
