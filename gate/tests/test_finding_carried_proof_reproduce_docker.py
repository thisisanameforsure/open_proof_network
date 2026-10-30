"""F32-T7 (R6, AC10; D-5 v3.49), docker tier: a born-proved hole's record reproduced in the image.

The merge of AC6 through the real toolchain in the step-3 sandbox: a skeleton on ``doubling``
carrying witnesses for both holes and a proof of ``first`` (the lean tier's
``test_finding_partial_carries_proofs_lean.py``), merged as a commit and attested by the
post-merge job in process. Then ``reproduce.sh --node <hole> --compare`` replays the partial at
the merge commit and holds the hole's own record to the committed one; ``--node <parent>`` does
the same for the partial's. Run from this checkout rather than the fixture's pinned forty zeros,
so (as in ``test_reproduce_docker.py``) the result is never ``identical`` (F07-T65); D-5's
comparison itself is that no field differs. The fast tier asserts identical at the pin
(``test_finding_carried_proof_reproduce.py``).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from harness import GRAPH, TARGET
from test_finding_partial_carries_proofs_lean import (
    BODY,
    CHILD,
    DOUBLE,
    GOOD,
    NODE,
    OTHER,
    SKELETON,
    STATEMENT,
    STEM,
)
from test_reproduce_docker import REPRODUCE

from opn_gate import carried, cli, layout, scaffold, schemas

pytestmark = pytest.mark.docker

ALL_STEPS_PASS = [(n, "pass") for n in (1, 2, 4, 5, 6, 7, 8)]


def witness(name: str) -> str:
    """Both holes ask for ``∃ (n : Nat), True`` (measured at 4.33.1, the lean tier's note)."""
    return (
        f"-- hole: {name}\nimport Defs.Double\n\n"
        "theorem witness : ∃ (n : Nat), True := ⟨0, trivial⟩\n"
    )


def merged_repo(tmp_path: Path) -> tuple[Path, str]:
    """The propositional fixture with ``doubling`` as history, then one commit merging the
    skeleton, both witnesses and the carried proof of ``first``; (graph, merge commit)."""
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    target_dir = layout.gate_spec_path(root, TARGET).parent
    (target_dir / "defs" / "Double.lean").write_text(DOUBLE, encoding="utf-8")
    (target_dir / "defs" / "Other.lean").write_text(OTHER, encoding="utf-8")
    scaffold.write(
        target_dir / "nodes",
        scaffold.Proposal(
            node_id=NODE,
            target_id=TARGET,
            statement=STATEMENT,
            witness="theorem witness : ∃ n : Nat, True := ⟨0, trivial⟩\n",
            author="curator",
            date="2026-10-29T00:00:00Z",
        ),
    )
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
    git("commit", "-q", "-m", "seed: doubling, unproved")
    node = target_dir / "nodes" / NODE
    st = layout.parse_statement((node / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    (node / SKELETON).write_text(st.prefix + BODY, encoding="utf-8")
    (node / f"{STEM}.1{carried.SUFFIX}").write_text(witness("first"), encoding="utf-8")
    (node / f"{STEM}.2{carried.SUFFIX}").write_text(witness("second"), encoding="utf-8")
    (node / f"{STEM}.1{carried.PROOF_SUFFIX}").write_text(GOOD, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "partial: doubling, carrying a proof of first")
    return root, git("rev-parse", "HEAD")


def reproduce(graph: Path, commit: str, node: str, out: Path, compare: Path) -> dict[str, Any]:
    argv = [str(REPRODUCE), "--graph", str(graph), "--commit", commit, "--node", node,
            "--target", TARGET, "--out", str(out), "--no-build",
            "--allow-network-mismatch",  # F07-T65: the fixtures pin forty zeros
            "--compare", str(compare)]  # fmt: skip
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        timeout=1800,
    )
    result: dict[str, Any] = json.loads(proc.stdout.splitlines()[-1])
    assert proc.returncode == 1, proc.stdout + proc.stderr  # never identical off the pin
    return result


def test_the_born_proved_hole_and_its_partial_reproduce_in_the_sandbox(
    sandbox_image: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC10: the post-merge job's two records of the merge, each reproduced at the merge commit
    in the image with no field differing once D-5's three are masked."""
    graph, merge = merged_repo(tmp_path)
    attested = tmp_path / "postmerge"
    argv = ["postmerge", "--graph", str(graph), "--commit", merge, "--pr", "9",
            "--target", TARGET, "--node", NODE, "--review-kind", "pr-approval",
            "--reviewer", "rev", "--out", str(attested), "--apply-partial",
            "--author", "login", "--image", sandbox_image]  # fmt: skip
    code = cli.main(argv)
    captured = capsys.readouterr()
    assert code == cli.EXIT_PASS, captured.out + captured.err
    hole_path = attested / "hole-attestations" / f"{CHILD}.json"
    hole = schemas.load_json(hole_path)
    assert hole["verdict"] == "pass" and hole["carried_by"]["node_id"] == NODE
    assert [(s["step"], s["result"]) for s in hole["steps"]] == ALL_STEPS_PASS

    result = reproduce(graph, merge, CHILD, tmp_path / "hole", hole_path)
    assert result["differing_fields"] == [], result
    assert result["network_mismatch"]["code"] == "network-mismatch"
    reproduced = schemas.load_json(tmp_path / "hole" / "hole-attestations" / f"{CHILD}.json")
    assert reproduced["carried_by"] == hole["carried_by"]

    result = reproduce(graph, merge, NODE, tmp_path / "parent", attested / "attestation.json")
    assert result["differing_fields"] == [], result
