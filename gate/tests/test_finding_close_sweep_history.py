"""F28-T12: the closure sweep reads the statuses the products publish (B2 of the 2026-11-19 run).

Measured on the live record: every post-merge run of ``opn-gate close --all`` tried to join
``erdos-1050@1`` and failed, though ``erdos-1050`` is proved and its ``graph.json`` says so. The
sweep worked on ``git archive`` of the commit — a tree with no history — and a parent whose hole
was revised carries a ``stale`` record that only commit ancestry lifts (F08-T10). With no history
to ask, the record stays (the conservative answer), so the sweep saw a proved calibration root as
``stale``, called it closable, pulled the Mathlib image and composed a join every run. The fix is
the Palomar export's (F25): the sweep works on a detached worktree of the commit, so it derives
exactly what the products derive, and the worktree is removed afterwards.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_cli_sandboxed import Seam, run
from test_finding_revised_hole_parent import (
    DEP_V2,
    ROOT,
    attest,
    base,
    commit_all,
    git,
    prove,
    revise,
    statuses,
)

from opn_gate import cli, closing


def proved_after_revision(tmp_path: Path) -> Path:
    """The live erdos-1050 shape: a proved root, its hole revised (the root marked ``stale``),
    the revision proved, and the root's proof re-run at a commit that includes the mark."""
    root = base(tmp_path, root_proved=True)
    git(root, "init", "-q", "-b", "main")
    commit_all(root, "base")
    revise(root)
    prove(root, DEP_V2, 9)
    marked = commit_all(root, "the revision, marking the root stale")
    attest(root, ROOT, 12, graph_commit=marked)
    commit_all(root, "the root re-run against the revision")
    assert statuses(root)[ROOT] == "proved", "the checkout, as the products read it"
    return root


def test_the_sweep_sees_a_proved_root_as_the_products_do(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = proved_after_revision(tmp_path / "g")
    seen: list[str] = []

    def closable(doc: Any) -> tuple[closing.Closable, ...]:
        seen.extend(n["status"] for n in doc["nodes"] if n["node_id"] == ROOT)
        return ()

    monkeypatch.setattr(closing, "closable", closable)
    out_dir = tmp_path / "o"
    code, out, _err = run(capsys, "close", "--graph", str(root), "--target", TARGET,
                          "--out", str(out_dir))  # fmt: skip
    assert code == cli.EXIT_PASS and out["results"] == []
    assert seen == ["proved"], "the sweep must derive what graph.json publishes"
    assert seam.made == [], "nothing is ready, so no sandbox is started"
    # The scratch worktree is gone, and the checkout carries no registration of it.
    listed = subprocess.run(
        ["git", "-C", str(root), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    assert listed.count("worktree ") == 1, listed
    assert git(root, "status", "--porcelain") == ""


def test_an_occupied_tree_directory_is_a_named_error_not_a_traceback(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root = proved_after_revision(tmp_path / "g")
    occupied = tmp_path / "o" / "tree"
    occupied.mkdir(parents=True)
    (occupied / "left-over").write_text("x")
    code, _out, err = run(capsys, "close", "--graph", str(root), "--target", TARGET,
                          "--out", str(tmp_path / "o"))  # fmt: skip
    assert code != cli.EXIT_PASS
    assert "could not check out" in err
    assert (occupied / "left-over").read_text() == "x", "nothing of the caller's is removed"
