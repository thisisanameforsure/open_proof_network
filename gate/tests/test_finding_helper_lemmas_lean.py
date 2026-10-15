"""F00-T11 and F02-T15, lean tier: the real gate takes a proof with private helpers, and every
``lean`` call it makes runs at the 1000000-heartbeat cap.

The fast tier pins the step-2 rule and the command line (``test_finding_helper_lemmas.py``). This
proves the rest with the real toolchain: Lean reads the option off the command line (the core
limit a declaration elaborates under is the cap, in Lean's internal thousands), and a proof
whose theorem uses a private helper passes steps 1 to 8 — the kernel replay, the axiom probe,
the meaning check and the dependency check all see the helper and accept it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from test_pregate_lean import git_graph, run_pregate_node

from opn_gate import config, layout
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

#: Fails to elaborate unless the declaration-level limit is the gate's cap.
PROBE = (
    "import Lean\n"
    "open Lean in\n"
    "run_meta do\n"
    "  let got := (← readThe Core.Context).maxHeartbeats\n"
    f"  unless got == {config.MAX_HEARTBEATS} * 1000 do\n"
    '    throwError "maxHeartbeats is {got / 1000}"\n'
)


def test_lean_runs_at_the_gate_s_cap(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain
) -> None:
    src = tmp_path / "src" / "Probe.lean"
    src.parent.mkdir(parents=True)
    src.write_text(PROBE, encoding="utf-8")
    result = real_toolchain.elaborate(pinned, src, "Probe", tmp_path / "build", root=src.parent)
    assert result.ok, [m.as_dict() for m in result.messages]


HELPED = (
    "/-! The tutorial node (D-27): permanently open, off-ledger. Lean core only. -/\n"
    "\n"
    "/-- A helper the proof uses. -/\n"
    "private theorem swap_one {p q : Prop} (h : p ∧ q) : q ∧ p := ⟨h.2, h.1⟩\n"
    "\n"
    "private def unused : Nat := 2\n"
    "\n"
    "theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by\n"
    "  intro p q h\n"
    "  exact swap_one h\n"
)


def test_the_gate_takes_a_proof_with_private_helpers(tmp_path: Path) -> None:
    graph = git_graph(tmp_path)
    here = layout.graph_nodes_dir(graph, "propositional") / "tutorial-and-swap"
    assert (
        (here / "Statement.lean")
        .read_text(encoding="utf-8")
        .startswith(HELPED.split("\n", maxsplit=1)[0])
    )
    # The merged proof is history; the submission is the new Proof.lean alone (2026-09-12).
    (here / "Proof.lean").unlink()
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    for cmd in (["add", "-A"], ["commit", "-q", "-m", "an open tutorial"]):
        subprocess.run(["git", "-C", str(graph), *cmd], check=True, env=env)
    (here / "Proof.lean").write_text(HELPED, encoding="utf-8")
    code, summary = run_pregate_node(graph, "tutorial-and-swap", tmp_path / "out")
    assert code == 0, summary
    assert all(s["result"] == "pass" for s in summary["steps"]), summary["steps"]
