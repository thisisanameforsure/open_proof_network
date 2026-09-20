"""F07-T23, lean tier: a hole's statement imports its own Context, and the real gate takes it.

Found live on graph PR #123 (the 2026-09-19 primes run, agent D): both holes of
``variant-2a7919a9`` were proved, the post-merge job had written them into the parent's
``Context.lean``, and the closing proof failed step 4, "Unknown identifier
`variant_2a7919a9__h1`", because the parent's statement never imported that Context and a proof
may not add an import (F00-R19). The service half is F08-T13. This is the gate half: a hole is a
node that may be decomposed in turn, so the statement ``child_statement`` writes carries the
import from birth. The fast tier pins the text; this proves the text elaborates, stages and
passes steps 1 to 8 with the header compared (step 2).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from harness import TARGET
from test_pregate_lean import git_graph, run_pregate_node

from opn_gate import layout, postmerge, scaffold

pytestmark = pytest.mark.lean

CHILD = "and-swap-reassoc--h1"
CLOSED = "∀ (p q r : Prop), (p ∧ q) ∧ r → r"
WITNESS = "theorem witness : ∃ p q r : Prop, (p ∧ q) ∧ r :=\n  ⟨True, True, True, ⟨trivial, trivial⟩, trivial⟩\n"  # noqa: E501


@dataclass(frozen=True)
class Hole:
    name: str
    closed_type: str


def test_a_gate_written_hole_is_provable_under_its_own_context_import(tmp_path: Path) -> None:
    graph = git_graph(tmp_path)
    nodes = layout.graph_nodes_dir(graph, TARGET)
    statement = postmerge.child_statement(CHILD, Hole("right", CLOSED))
    assert f"import {layout.node_module(CHILD, 'Context')}\n" in statement
    scaffold.write(
        nodes,
        scaffold.Proposal(
            node_id=CHILD, target_id=TARGET, statement=statement, witness=WITNESS, author="t"
        ),
    )
    assert layout.check_imports(nodes / CHILD, CHILD) == []
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    # The node is merged history; the submission is its Proof.lean alone (2026-09-12).
    for cmd in (["add", "-A"], ["commit", "-q", "-m", "the hole, as the post-merge job writes it"]):
        subprocess.run(["git", "-C", str(graph), *cmd], check=True, env=env)
    proof = statement.replace("  sorry\n", "  intro p q r h\n  exact h.2\n")
    assert proof != statement
    (nodes / CHILD / "Proof.lean").write_text(proof, encoding="utf-8")
    code, summary = run_pregate_node(graph, CHILD, tmp_path / "out")
    assert code == 0, summary
    assert all(s["result"] == "pass" for s in summary["steps"]), summary["steps"]
