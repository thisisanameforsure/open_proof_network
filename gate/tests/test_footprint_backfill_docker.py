"""F08-T27, F18-T7: ``opn-gate footprints`` in the step-3 sandbox. Docker tier.

Every check that reads the image's filesystem has failed once only in the sandbox (2026-09-12),
so the command is run end to end the way the backfill workflow runs it: a committed graph whose
attestations predate v6, the pinned image, the cache written to ``--out`` and nothing to the
graph.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from harness import TARGET, copy_graph
from test_footprint_backfill import v5_attest
from test_node_proofs import proof_hash

from opn_gate import graph

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
A, B, NODE = "tutorial-and-swap", "and-reassoc", "and-swap-reassoc"
ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@x",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@x",
    "PATH": "/usr/bin:/bin",
}


def committed_graph(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path / "g", publish=True)
    for n, node in enumerate((A, B, NODE), start=1):
        v5_attest(root, node, n, proof_hash(root, node))
    env = {**ENV, "HOME": str(tmp_path)}
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env)
    return root


def test_the_backfill_measures_every_old_merge_in_the_sandbox(
    tmp_path: Path, sandbox_image: str
) -> None:
    root = committed_graph(tmp_path)
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "opn_gate.cli",
            "footprints",
            "--graph",
            str(root),
            "--target",
            TARGET,
            "--image",
            sandbox_image,
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=1800,
        env={**os.environ, "PYTHONPATH": str(ROOT / "gate")},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["measured"] == 3 and summary["failed"] == []
    cache = json.loads((out / graph.FOOTPRINT_CACHE).read_text())
    assert cache == {
        proof_hash(root, A): [],
        proof_hash(root, B): [],
        proof_hash(root, NODE): sorted([A, B]),
    }
    # Nothing was written to the graph.
    assert not (root / "targets" / TARGET / graph.FOOTPRINT_CACHE).exists()
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert status.stdout == ""
