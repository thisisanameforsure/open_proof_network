"""F28-T5 (R7, R8; draft decisions v3.41): the gate side of the automatic closing proof.

The closer (the graph's ``close.yml``) asks the pinned gate for every node of a target that is
ready to close, less those it already has a pull request for, and composes each (``opn-gate close
--target``). A closing proof is a join, authored ``opn-gate`` (a reserved name no contributor can
hold): it earns no ledger line, the work it joins having earned its own. It is prechecked like any
plain-git submission (D-4's unsigned kind) in the workflow, not here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_cli_sandboxed import NODES, Seam, git_repo, run
from test_finding_ledger_update_branch_credit import merge_no_ff

from opn_gate import cli, close

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def test_a_closing_proof_earns_no_ledger_line(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The submission commit is authored ``opn-gate`` (the closing workflow's identity, a reserved
    name no contributor can hold): the merge earns nothing and no ``ledger/opn-gate.json``."""
    root, git, _base = git_repo(tmp_path)
    node = "and-reassoc"
    proof = root / NODES / node / "Proof.lean"
    text = proof.read_text(encoding="utf-8")
    proof.unlink()
    git("add", "--", f"{NODES}/{node}")
    git("commit", "-q", "-m", f"{node}, unproved")
    main = git("rev-parse", "--abbrev-ref", "HEAD")
    git("checkout", "-q", "-b", f"close/{node}")
    proof.write_text(text, encoding="utf-8")
    git("add", "--", f"{NODES}/{node}/Proof.lean")
    author = close.CLOSING_AUTHOR
    git("commit", "-q", "--author", f"{author} <{author}@x>", "-m", f"close {node}")
    git("checkout", "-q", main)
    head = merge_no_ff(git, f"close/{node}", who="thisisanameforsure")

    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", head)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is False
    assert "closing proof" in out["reason"]
    assert not (root / "ledger" / f"{author}.json").exists()


# --- the sweep the closing workflow runs -------------------------------------------------------


def test_the_sweep_composes_every_ready_node_but_the_skipped(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """``opn-gate close --target`` with no ``--node``: each node ready to close, less those the
    workflow already has a pull request for, composed in its own work directory and written to
    ``<dest>/<target>/<node>.lean``; a node whose proof failed is reported and written nowhere."""
    root, _git, _base = git_repo(tmp_path)
    monkeypatch.setattr(close, "graph_doc", lambda tree, target: {})
    monkeypatch.setattr(close, "ready_nodes", lambda graph: ["a", "b", "c"])
    composed: list[tuple[str, Path]] = []

    def compose(*args: Any, timeout_s: float) -> close.Result:
        node, work = args[4], args[5]
        composed.append((node, work))
        if node == "c":
            return close.Result(TARGET, node, None, reason=close.COMPOSE_FAILED, detail="no")
        return close.Result(TARGET, node, None, proof=f"proof of {node}\n")

    monkeypatch.setattr(close, "compose", compose)
    dest = tmp_path / "dest"
    code, out, _err = run(
        capsys, "close", "--graph", str(root), "--target", TARGET, "--skip", "b",
        "--dest", str(dest), "--out", str(tmp_path / "o"),
    )  # fmt: skip
    assert code == cli.EXIT_FAIL  # one asked for got no proof
    assert [n for n, _ in composed] == ["a", "c"]
    assert len({w for _, w in composed}) == 2
    assert out["skipped"] == ["b"]
    assert [(r["node"], r["ok"]) for r in out["results"]] == [("a", True), ("c", False)]
    assert (dest / TARGET / "a.lean").read_text(encoding="utf-8") == "proof of a\n"
    assert not (dest / TARGET / "c.lean").exists()


def test_the_sweep_starts_no_sandbox_when_nothing_is_ready(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _git, _base = git_repo(tmp_path)
    monkeypatch.setattr(close, "graph_doc", lambda tree, target: {})
    monkeypatch.setattr(close, "ready_nodes", lambda graph: ["a"])
    code, out, _err = run(
        capsys, "close", "--graph", str(root), "--target", TARGET, "--skip", "a",
        "--out", str(tmp_path / "o"),
    )  # fmt: skip
    assert code == cli.EXIT_PASS and out["results"] == []
    assert seam.made == [] and seam.docker_log() == []
