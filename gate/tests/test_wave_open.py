"""F14-T24: the admitted drafts are opened as intake pull requests, one per target, on `intake/`
branches the merge actor takes (T22).

``gate/tools/wave_open.py`` reads the merged admission report (T20's ``summary.json`` beside the
drafts), and for each admitted target imports the draft into a graph clone on a fresh
``intake/<id>`` branch from ``origin/main`` (no toolchain: the gate judges the pull request), pushes
the branch and opens the pull request; what it did is written down per target, so a run that stops
can resume and never opens a target twice.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from test_wave import PIN, run_wave

TOOL = Path(__file__).resolve().parents[1] / "tools" / "wave_open.py"


def load_tool() -> Any:
    spec = importlib.util.spec_from_file_location("wave_open", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def admitted(tmp_path: Path) -> tuple[Path, Path]:
    """Drafts, and a merged report admitting three of them."""
    out, _result, _doc = run_wave(tmp_path)
    report = tmp_path / "merged"
    report.mkdir()
    (report / "summary.json").write_text(
        json.dumps(
            {
                "schema": "wave-admit/v1",
                "admitted": ["erdos-7001", "erdos-7003", "erdos-7006"],
                "refused": [{"target": "erdos-7002", "check": "statement", "message": "x"}],
            }
        ),
        encoding="utf-8",
    )
    return out, report


def test_each_admitted_target_is_one_branch_one_pull_request(
    admitted: tuple[Path, Path], tmp_path: Path
) -> None:
    out, report = admitted
    tool = load_tool()
    calls: list[list[str]] = []

    def runner(argv: list[str], cwd: Path) -> tuple[int, str]:
        calls.append(argv)
        if argv[:2] == ["gh", "pr"]:
            return 0, "https://github.com/o/g/pull/1700\n"
        return 0, '{"ok": true}\n'

    done = tool.open_all(
        report,
        out,
        graph=tmp_path / "graph",
        repo="o/g",
        pin=PIN,
        network="1" * 40,
        catalog=Path("c.json"),
        author="curator",
        runner=runner,
        limit=None,
    )
    assert [d["target"] for d in done] == ["erdos-7001", "erdos-7003", "erdos-7006"]
    assert all(d["pull_request"] == "https://github.com/o/g/pull/1700" for d in done)
    joined = [" ".join(c) for c in calls]
    # Per target: a fresh detached checkout of origin/main, the import on its intake/ branch with
    # no toolchain (the gate judges the pull request), the push, the pull request.
    for target in ("erdos-7001", "erdos-7003", "erdos-7006"):
        assert any(c.startswith("git ") and "checkout" in c and "origin/main" in c for c in joined)
        imp = next(c for c in joined if f"--target {target} " in c)
        assert f"--branch intake/{target}" in imp and "--no-toolchain" in imp
        assert ("--defs" in imp) is (target == "erdos-7003")
        assert any(c.startswith("git ") and "push" in c and f"intake/{target}" in c for c in joined)
        pr = next(c for c in joined if c.startswith("gh pr create") and f"intake/{target}" in c)
        assert "--repo o/g" in pr and "--base main" in pr
    # The record: one line per target, resumable.
    log = json.loads((report / "opened.json").read_text(encoding="utf-8"))
    assert [e["target"] for e in log] == ["erdos-7001", "erdos-7003", "erdos-7006"]
    # A second run opens nothing again.
    calls.clear()
    again = tool.open_all(
        report,
        out,
        graph=tmp_path / "graph",
        repo="o/g",
        pin=PIN,
        network="1" * 40,
        catalog=Path("c.json"),
        author="curator",
        runner=runner,
        limit=None,
    )
    assert again == [] and calls == []


def test_a_limit_opens_the_first_few_and_a_failure_stops_the_run(
    admitted: tuple[Path, Path], tmp_path: Path
) -> None:
    out, report = admitted
    tool = load_tool()

    def runner(argv: list[str], cwd: Path) -> tuple[int, str]:
        if argv[:2] == ["gh", "pr"]:
            return 0, "https://github.com/o/g/pull/1\n"
        if "--target erdos-7003" in " ".join(argv):
            return 1, '{"ok": false, "refused": {"check": "layout", "message": "no"}}\n'
        return 0, '{"ok": true}\n'

    done = tool.open_all(
        report,
        out,
        graph=tmp_path / "graph",
        repo="o/g",
        pin=PIN,
        network="1" * 40,
        catalog=Path("c.json"),
        author="curator",
        runner=runner,
        limit=1,
    )
    assert [d["target"] for d in done] == ["erdos-7001"]
    with pytest.raises(tool.OpenError, match="erdos-7003"):
        tool.open_all(
            report,
            out,
            graph=tmp_path / "graph",
            repo="o/g",
            pin=PIN,
            network="1" * 40,
            catalog=Path("c.json"),
            author="curator",
            runner=runner,
            limit=None,
        )
    log = json.loads((report / "opened.json").read_text(encoding="utf-8"))
    assert [e["target"] for e in log] == ["erdos-7001"]  # the failed one is not recorded as opened
