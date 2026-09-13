"""F12-T8 in the step-3 image (docker tier): ``opn-gate qa-rerun --sandbox`` on a typed QA record.

The fast tier proves the comparison and the sandbox seam through fakes; the lean tier proves the
re-run is real Lean on the host's toolchain. This proves what the drafted ``gate.yml`` step runs:
the command itself, inside the image ``gate/Dockerfile`` builds, over a git checkout whose head
commit adds one record — the propositional root is a tautology, so the statement screen proves
it, and a record typing ``screen-statement: pass`` is refused naming that row, while the compile
and the other screens agree. F12-Q19 owed this test before the graph is re-pinned to the gate
that carries the step.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from harness import GRAPH, TARGET, copy_graph

from opn_gate import cli, qa, qa_rerun

WHEN = "2026-09-13T12:00:00Z"


@pytest.mark.docker
def test_qa_rerun_in_the_sandbox_refutes_a_typed_pass_on_a_tautology(
    tmp_path: Path, sandbox_image: str, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_graph(tmp_path, GRAPH)
    env = {
        "GIT_AUTHOR_NAME": "curator",
        "GIT_AUTHOR_EMAIL": "c@x",
        "GIT_COMMITTER_NAME": "curator",
        "GIT_COMMITTER_EMAIL": "c@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
    }

    def git(*args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], check=True, env=env, capture_output=True, text=True
        )
        return proc.stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    rows = [
        qa.row(check, "pass", tool="hand", tool_version="hand", timestamp=WHEN)
        for check in ("compile", *qa.SCREENS)
    ]
    qa.write(root / "targets" / TARGET, "root", rows, date=WHEN, produced_by="hand")
    git("add", "-A")
    git("commit", "-q", "-m", "qa: typed by hand")

    code = cli.main(
        [
            "qa-rerun",
            "--graph",
            str(root),
            "--base",
            "HEAD~1",
            "--sandbox",
            "--image",
            sandbox_image,
            "--date",
            WHEN,
            "--out",
            str(tmp_path / "rerun"),
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_FAIL, f"the sandboxed re-run accepted a pass it refutes: {out}"
    assert [(p["code"], p["details"]["check"]) for p in out["problems"]] == [
        (qa_rerun.CODE_DISAGREES, "screen-statement")
    ]
    assert git("status", "--porcelain") == "", "the sandboxed re-run wrote into the checkout"
