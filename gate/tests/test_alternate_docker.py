"""F07-T10: an alternate proof re-derived in the sandbox (R7; AC27). Docker tier.

The sandbox holds only the node under check and the work directory, and three checks have failed
there alone after passing every laptop tier (log, 2026-09-10 and 2026-09-12). So the alternate
gets its own sandboxed run: a commit that adds one to the proved tutorial node, re-derived by
``reproduce.sh`` exactly as the post-merge job re-derives a merge.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from harness import GRAPH, TUTORIAL
from test_reproduce_docker import REPRODUCE

from opn_gate import schemas

pytestmark = pytest.mark.docker

NODE = f"targets/propositional/nodes/{TUTORIAL}"
NAME = "20260914T120000Z-bob-alternate.lean"


def alternate_commit(tmp_path: Path) -> tuple[Path, str, Path]:
    """The fixture at one commit with the tutorial proved, then a commit adding an alternate."""
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

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "seed, tutorial proved")
    proof = (root / NODE / "Proof.lean").read_text(encoding="utf-8")
    text = proof.replace("  exact ⟨h.2, h.1⟩\n", "  exact And.intro h.2 h.1\n")
    assert text != proof
    alternate = root / NODE / "attempts" / NAME
    alternate.write_text(text, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "alternate: tutorial-and-swap")
    return root, git("rev-parse", "HEAD"), alternate


def test_real_alternate_passes_in_the_sandbox(sandbox_image: str, tmp_path: Path) -> None:
    """AC27, in the sandbox: steps 1-8 pass on the alternate and the attestation names it."""
    graph, commit, alternate = alternate_commit(tmp_path)
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            str(REPRODUCE),
            "--graph",
            str(graph),
            "--commit",
            commit,
            "--node",
            TUTORIAL,
            "--out",
            str(out),
            "--no-build",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    doc = json.loads((out / "attestation.json").read_text())
    assert doc["verdict"] == "pass", doc
    assert [(s["step"], s["result"]) for s in doc["steps"]] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    assert doc["artifact_hash"] == schemas.content_hash(alternate.read_bytes())
    assert sandbox_image
