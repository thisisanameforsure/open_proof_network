"""F00-T7: reproduce.sh and the D-5 identical-run property (R15; AC27). Docker tier."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from harness import TUTORIAL

from opn_gate import attestation, schemas

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
REPRODUCE = ROOT / "gate" / "reproduce.sh"


def run_reproduce(graph: Path, commit: str, out: Path, *extra: str) -> tuple[int, dict[str, Any]]:
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
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    assert proc.stdout.strip().startswith("{"), proc.stderr
    return proc.returncode, json.loads((out / "attestation.json").read_text())


def test_two_runs_identical(
    fixture_graph_repo: tuple[Path, str], sandbox_image: str, tmp_path: Path
) -> None:
    """AC27; F01-T5: the replay covers steps 7 and 8 with the image's metaprograms (R10)."""
    graph, commit = fixture_graph_repo
    code_a, a = run_reproduce(graph, commit, tmp_path / "a")
    code_b, b = run_reproduce(graph, commit, tmp_path / "b")
    assert code_a == 0 and code_b == 0, (a, b)
    assert a["verdict"] == "pass" and b["verdict"] == "pass"
    assert [(s["step"], s["result"]) for s in a["steps"]] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    assert a["graph_commit"] == commit
    assert schemas.violations(a) == [] and schemas.violations(b) == []
    assert attestation.compare(a, b) == []
    assert schemas.canonical_json(attestation.masked(a)) == schemas.canonical_json(
        attestation.masked(b)
    )
    assert sandbox_image


def test_compare_against_committed_attestation(
    fixture_graph_repo: tuple[Path, str], tmp_path: Path
) -> None:
    graph, commit = fixture_graph_repo
    code, doc = run_reproduce(graph, commit, tmp_path / "first")
    assert code == 0
    committed = tmp_path / "0001.json"
    doc["runner"] = "hosted"
    doc["merge_commit"] = commit
    committed.write_bytes(schemas.canonical_json(doc))
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
            str(tmp_path / "second"),
            "--no-build",
            "--compare",
            str(committed),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '"identical": true' in proc.stdout.splitlines()[-1]

    doc["artifact_hash"] = "0" * 64
    committed.write_bytes(schemas.canonical_json(doc))
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
            str(tmp_path / "third"),
            "--no-build",
            "--compare",
            str(committed),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    assert proc.returncode == 1
    assert "artifact_hash" in proc.stdout.splitlines()[-1]
