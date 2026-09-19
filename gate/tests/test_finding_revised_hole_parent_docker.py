"""F08-T10, docker tier: the parent of a revised child passes in the step-3 sandbox.

Three checks have passed every laptop tier and failed on their first sandboxed run, each because
it read a sibling node the sandbox did not hold (F06-Q6, F08-Q13, 2026-09-12). Staging now reads
a dependency through its revision, which is exactly a sibling read, so the revised-parent tree
of the lean tier is gated here the way CI gates it: ``reproduce.sh`` at a commit, in the image.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from test_finding_revised_hole_parent_lean import ALL_STEPS_PASS, ROOT, revised_tree
from test_reproduce_docker import REPRODUCE

pytestmark = pytest.mark.docker


def test_the_parent_passes_in_the_sandbox_against_the_revision(
    sandbox_image: str, tmp_path: Path
) -> None:
    graph, commit, _meta = revised_tree(tmp_path)
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            str(REPRODUCE),
            "--graph",
            str(graph),
            "--commit",
            commit,
            "--node",
            ROOT,
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
    assert [(s["step"], s["result"]) for s in doc["steps"]] == ALL_STEPS_PASS
    assert sandbox_image
