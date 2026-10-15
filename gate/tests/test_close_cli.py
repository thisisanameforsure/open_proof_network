"""F28-T9: ``opn-gate close`` — the sweep the post-merge job runs (fast tier).

It exports the commit, asks each target (one, or ``--all``) what is ready to close, starts a
sandbox only for a target that has something, sweeps it (``close.sweep``, faked here), and copies
each record it wrote into the checkout beside its node, for the post-merge job to sign and commit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, TUTORIAL
from test_cli_sandboxed import Seam, git_repo, run

from opn_gate import cli, close, closing, closure

FACTS_KEYS = {"graph_commit", "network_commit", "lean_toolchain", "mathlib_sha", "timestamp"}


def record(node: str) -> dict[str, Any]:
    return closure.build(
        target_id=TARGET, node_id=node, statement_hash="a" * 64,
        link=closure.Link("route", f"{node}@1", ("x",)), source_path="attempts/a.lean",
        source_text=None, source_hash="b" * 64, axioms=[], graph_commit="c" * 40,
        network_commit=None, lean_toolchain="leanprover/lean4:v4.33.1", mathlib_sha=None,
        timestamp="2026-10-15T12:00:00Z",
    )  # fmt: skip


def test_a_target_with_nothing_ready_starts_no_sandbox(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _git, _base = git_repo(tmp_path)
    monkeypatch.setattr(closing, "closable", lambda doc: ())
    code, out, _err = run(capsys, "close", "--graph", str(root), "--target", TARGET,
                          "--out", str(tmp_path / "o"))  # fmt: skip
    assert code == cli.EXIT_PASS and out["results"] == []
    assert seam.made == [] and seam.docker_log() == []


def test_records_the_sweep_wrote_land_beside_their_nodes_in_the_checkout(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _git, _base = git_repo(tmp_path)
    monkeypatch.setattr(
        closing, "closable",
        lambda doc: (closing.Closable(TUTORIAL, closing.Link("route", "x@1", ("x",)), True),),
    )  # fmt: skip
    seen: dict[str, Any] = {}

    def sweep(seam_: Any, tc: Any, tree: Path, target: str, work: Path, *, facts: Any,
              timeout_s: float) -> list[close.Result]:  # fmt: skip
        seen.update(target=target, facts=facts)
        link = closing.Link("route", f"{TUTORIAL}@1", ("x",))
        return [
            close.Result(target, TUTORIAL, link, record=record(TUTORIAL)),
            close.Result(target, "other", link, reason=close.JOIN_FAILED, detail="no"),
        ]

    monkeypatch.setattr(close, "sweep", sweep)
    code, out, _err = run(capsys, "close", "--graph", str(root), "--target", TARGET,
                          "--out", str(tmp_path / "o"))  # fmt: skip
    assert code == cli.EXIT_FAIL  # one join failed; it is named and changes nothing
    written = root / "targets" / TARGET / "nodes" / TUTORIAL / "closure.json"
    assert closure.load(written.parent) is not None
    assert [(r["node"], r["ok"], r.get("written")) for r in out["results"]] == [
        (TUTORIAL, True, written.relative_to(root).as_posix()),
        ("other", False, None),
    ]
    assert seen["target"] == TARGET and set(vars(seen["facts"])) == FACTS_KEYS
    assert len(seen["facts"].graph_commit) == 40
