"""F00-T10, lean tier: the real gate closes a parent of the live shape through its dependencies.

The fast tier pins the header rule (``test_finding_proof_own_context_import.py``). This proves
the rest with the real toolchain: a statement with no own-Context import, a proof that adds the
line and names two dependencies' theorems, and steps 1 to 8 all pass, step 2 having compared the
header and step 4 having built the proof against the staged, proved dependencies.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from harness import TARGET
from test_finding_proof_own_context_import import NODE, OLD_STATEMENT, proof
from test_pregate_lean import git_graph, run_pregate_node

from opn_gate import layout, schemas

pytestmark = pytest.mark.lean


def test_the_gate_takes_an_old_statements_assembly(tmp_path: Path) -> None:
    graph = git_graph(tmp_path)
    here = layout.graph_nodes_dir(graph, TARGET) / NODE
    old_hash = schemas.content_hash((here / "Statement.lean").read_bytes())
    (here / "Statement.lean").write_text(OLD_STATEMENT, encoding="utf-8")
    meta = (here / "META.yaml").read_text(encoding="utf-8")
    assert old_hash in meta
    new_hash = schemas.content_hash(OLD_STATEMENT.encode())
    (here / "META.yaml").write_text(meta.replace(old_hash, new_hash), encoding="utf-8")
    (here / "Proof.lean").unlink()
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    # The old-shape node is merged history; the submission is its Proof.lean alone (2026-09-12).
    for cmd in (["add", "-A"], ["commit", "-q", "-m", "a statement from before 2026-09-20"]):
        subprocess.run(["git", "-C", str(graph), *cmd], check=True, env=env)
    (here / "Proof.lean").write_text(proof(), encoding="utf-8")
    code, summary = run_pregate_node(graph, NODE, tmp_path / "out")
    assert code == 0, summary
    assert all(s["result"] == "pass" for s in summary["steps"]), summary["steps"]
