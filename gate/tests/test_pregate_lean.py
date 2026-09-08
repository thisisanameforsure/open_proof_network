"""F00-T6: pregate.sh against the real toolchain (R11; AC21-AC24). make verify-lean."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from harness import GRAPH, TUTORIAL

from opn_gate import attestation, schemas
from opn_gate.signer import SshKeygenSigner

pytestmark = pytest.mark.lean

ROOT = Path(__file__).resolve().parents[2]
PREGATE = ROOT / "gate" / "pregate.sh"
NODE = f"targets/propositional/nodes/{TUTORIAL}"


def git_graph(tmp_path: Path) -> Path:
    """A committed copy of the fixture graph, so pregate can diff the working tree."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env)
    return root


def run_pregate(graph: Path, out: Path, *extra: str) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(
        [str(PREGATE), "--graph", str(graph), "--node", TUTORIAL, "--out", str(out), *extra],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert proc.stdout.strip().startswith("{"), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_tutorial_node_passes(tmp_path: Path) -> None:
    """AC21."""
    graph = git_graph(tmp_path)
    code, summary = run_pregate(graph, tmp_path / "out")
    assert code == 0, summary
    assert summary["verdict"] == "pass"
    assert [(s["step"], s["result"]) for s in summary["steps"]] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    doc = json.loads((tmp_path / "out" / "attestation.json").read_text())
    assert schemas.violations(doc) == []
    assert doc["runner"] == "local"
    assert doc["signature"]["kind"] == "none"
    assert doc["toolchain_hash"] and doc["lean_toolchain"] == "leanprover/lean4:v4.33.1"
    assert doc["graph_commit"] is not None  # clean committed tree
    assert doc["artifact_hash"] == schemas.content_hash((graph / NODE / "Proof.lean").read_bytes())


def test_sorry_fails_step5(tmp_path: Path) -> None:
    """AC22."""
    graph = git_graph(tmp_path)
    proof = graph / NODE / "Proof.lean"
    proof.write_text(proof.read_text().replace("  intro p q h\n  exact ⟨h.2, h.1⟩\n", "  sorry\n"))
    code, summary = run_pregate(graph, tmp_path / "out")
    assert code == 1
    assert summary["verdict"] == "fail"
    assert summary["first_failing_step"] == 5
    assert summary["diagnostic"]["code"] == "axiom-not-allowed"
    assert summary["diagnostic"]["details"]["axioms"] == ["sorryAx"]
    doc = json.loads((tmp_path / "out" / "attestation.json").read_text())
    assert doc["graph_commit"] is None  # dirty tree


def test_extra_axiom_fails_step5(tmp_path: Path) -> None:
    """AC23: elaborates, but rests on an axiom outside the allowlist."""
    graph = git_graph(tmp_path)
    proof = graph / NODE / "Proof.lean"
    proof.write_text(
        proof.read_text().replace(
            "  intro p q h\n  exact ⟨h.2, h.1⟩\n",
            "  exact OpnEvil.oracle _\nwhere\n  OpnEvil.oracle : ∀ p : Prop, p := sorry\n",
        )
    )
    code, summary = run_pregate(graph, tmp_path / "out")
    assert code == 1 and summary["first_failing_step"] in (4, 5), summary


def test_extra_axiom_declared_fails_step5(tmp_path: Path) -> None:
    """AC23, the direct form: an `axiom` declaration in the proof body's file."""
    graph = git_graph(tmp_path)
    proof = graph / NODE / "Proof.lean"
    proof.write_text(
        proof.read_text().replace(
            "  intro p q h\n  exact ⟨h.2, h.1⟩\n",
            "  exact opn_oracle _\n\naxiom opn_oracle : ∀ p : Prop, p\n",
        )
    )
    code, summary = run_pregate(graph, tmp_path / "out")
    # The axiom is declared after its use, so this is an elaboration failure at step 4; a
    # forward-declared axiom cannot precede the theorem under R19. Either way it never passes.
    assert code == 1 and summary["first_failing_step"] in (4, 5), summary


def test_ssh_signature_verifies(tmp_path: Path) -> None:
    """AC24."""
    graph = git_graph(tmp_path)
    key = tmp_path / "id_test"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    code, _summary = run_pregate(graph, tmp_path / "out", "--sign", str(key))
    assert code == 0
    doc = json.loads((tmp_path / "out" / "attestation.json").read_text())
    assert doc["signature"]["kind"] == "contributor"
    assert doc["signature"]["key_id"].startswith("SHA256:")
    pub = (tmp_path / "id_test.pub").read_text()
    s = SshKeygenSigner()
    assert s.verify(attestation.signed_bytes(doc), doc["signature"]["value"], pub)
    assert doc["signature"]["key_id"] == s.fingerprint(pub)


# --- F01-T4: steps 7 and 8 with the real toolchain --------------------------------------------

ADVERSARIAL = Path(__file__).resolve().parent / "fixtures" / "graphs" / "adversarial"


def git_adversarial(tmp_path: Path) -> Path:
    root = tmp_path / "graph"
    shutil.copytree(ADVERSARIAL, root)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env)
    return root


def run_pregate_node(graph: Path, node: str, out: Path) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(
        [str(PREGATE), "--graph", str(graph), "--node", node, "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    assert proc.stdout.strip().startswith("{"), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_root_with_deps_passes_all_steps(tmp_path: Path) -> None:
    """F01-Q4: the root's proof compiles against the deps' merged proofs; 1, 2, 4, 5, 7, 8 pass."""
    graph = git_graph(tmp_path)
    code, summary = run_pregate_node(graph, "and-swap-reassoc", tmp_path / "out")
    assert code == 0, summary
    assert [(s["step"], s["result"]) for s in summary["steps"]] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]


def test_undeclared_dep_fails_step8(tmp_path: Path) -> None:
    """AC13."""
    graph = git_adversarial(tmp_path)
    code, summary = run_pregate_node(graph, "undeclared-dep", tmp_path / "out")
    assert code == 1
    assert summary["first_failing_step"] == 8, summary
    d = summary["diagnostic"]
    assert d["code"] == "undeclared-dependency"
    assert {o["node"] for o in d["details"]["offences"]} == {"and-reassoc", "tutorial-and-swap"}


def test_wrong_witness_fails_step7(tmp_path: Path) -> None:
    """AC14."""
    graph = git_adversarial(tmp_path)
    code, summary = run_pregate_node(graph, "wrong-witness", tmp_path / "out")
    assert code == 1
    assert summary["first_failing_step"] == 7, summary
    d = summary["diagnostic"]
    assert d["code"] == "witness-type-mismatch"
    assert d["details"] == {"expected": "∃ p q, p ∧ q", "witness": "∃ p, p"}


def test_unused_dep_warns_and_context_mismatch_fails(tmp_path: Path) -> None:
    graph = git_adversarial(tmp_path)
    code, summary = run_pregate_node(graph, "unused-dep", tmp_path / "out1")
    assert code == 0, summary
    code, summary = run_pregate_node(graph, "context-mismatch", tmp_path / "out2")
    assert code == 1 and summary["first_failing_step"] == 8
    assert summary["diagnostic"]["code"] == "context-signature-mismatch"
