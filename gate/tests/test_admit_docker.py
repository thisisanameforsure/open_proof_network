"""F08-T2: admission inside the step-3 sandbox (R2; C9). make verify-lean (docker tier).

The fast tier proves ``admit --sandbox`` builds the sandboxed toolchain; this proves the sandbox
can actually run every admission check — the statement, the witness, the hazards and the relation
metaprograms — over a proposal, which is what the authoritative gate does on a proposal PR.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from harness import GRAPH, TARGET, copy_graph

from opn_gate import cli

pytestmark = pytest.mark.docker

PROPOSALS = Path(__file__).resolve().parent / "fixtures" / "proposals"


def place(graph: Path, case: str) -> Path:
    dest = graph / "targets" / TARGET / "nodes" / case
    shutil.copytree(PROPOSALS / case, dest)
    return dest


def admit(node_dir: Path, image: str, out: Path, capsys: pytest.CaptureFixture[str]) -> dict:  # type: ignore[type-arg]
    code = cli.main(["admit", str(node_dir), "--sandbox", "--image", image, "--out", str(out)])
    summary = json.loads(capsys.readouterr().out)
    assert (code == 0) is (summary["verdict"] == "pass"), summary
    assert summary["sandboxed"] is True
    return dict(summary)


def test_admission_runs_in_the_sandbox(
    sandbox_image: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R2: a well-formed proposal is admitted inside the container; a variant with its relation
    proof backwards is refused at the relation check, by the container's own Lean."""
    # One graph per case: two un-depended-on proposals would make the root ambiguous (F03-Q5).
    graph = copy_graph(tmp_path / "a", GRAPH)
    good = admit(place(graph, "good"), sandbox_image, tmp_path / "good", capsys)
    assert good["verdict"] == "pass", good
    assert [c["check"] for c in good["checks"]] == [
        "toolchain",
        "layout",
        "declaration",
        "statement",
        "witness",
        "hazards",
        "context",
        "graph",
        "relation",
    ]

    graph = copy_graph(tmp_path / "b", GRAPH)
    backwards = admit(place(graph, "variant-backwards"), sandbox_image, tmp_path / "bw", capsys)
    assert backwards["verdict"] == "fail"
    assert backwards["first_failing_check"] == "relation"
    assert backwards["diagnostic"]["code"] == "relation-direction"
