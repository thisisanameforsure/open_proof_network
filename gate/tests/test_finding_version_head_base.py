"""F22-T11: the head check reads a version's siblings from the pull request's base commit.

A replay runs ``classify --base <merge>^ --head <merge>`` with ``main``'s tip checked out
(F07-T33), so a version that was the head's legitimate successor when it merged reads, against the
working tree, as superseding a version some *later* merge superseded again, and its replay is
refused ``record-not-head`` for ever (testers 2026-10-06, P1). What the version superseded is a fact
about the base plus the pull request's own files; a true fork, two versions superseding one head
both present at the base and the diff, is still refused.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import test_gloss_chains as chains
from test_gloss_chains import STEWARD, explainer, gloss, withdraw

from opn_gate import cli

#: The versions' author opens each pull request, as the service does for them (F20-T6).
AUTHOR = "carol"

#: The propositional fixture with a steward committed, and the keys it signs with.
keys = chains.keys
root = chains.root


def _git(graph: Path, *args: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(graph.parent),
    }
    proc = subprocess.run(
        ["git", "-C", str(graph), *args], check=True, env=env, capture_output=True, text=True
    )
    return proc.stdout.strip()


def _commit(graph: Path, message: str) -> str:
    _git(graph, "add", "-A")
    _git(graph, "commit", "-q", "-m", message)
    return _git(graph, "rev-parse", "HEAD")


def _classify(
    graph: Path, base: str, head: str, capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, Any]]:
    capsys.readouterr()
    code = cli.main(
        ["classify", "--graph", str(graph), "--base", base, "--head", head, "--author", AUTHOR]
    )
    return code, json.loads(capsys.readouterr().out)


def _make(record: str):  # type: ignore[no-untyped-def]
    return gloss if record == "gloss" else explainer


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_replay_of_a_version_later_superseded_passes(
    root: Path, record: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """v2 superseded v1 and merged; v3 later superseded v2. Replayed on the tip, v2's pull
    request is judged against its own base, where v1 was the head. (A guard: this shape passed
    before T11 too, because the version under check is left out of its own siblings, so v3 hung
    off nothing.)"""
    make = _make(record)
    v1, _ = make(root, "First.")
    _git(root, "init", "-q")
    seed = _commit(root, "seed")
    v2, _ = make(root, "Second.", supersedes=v1)
    merge = _commit(root, "merge v2")
    make(root, "Third.", supersedes=v2)
    _commit(root, "merge v3")  # main's tip, checked out, as on a replay
    code, out = _classify(root, seed, merge, capsys)
    assert [p["code"] for p in out["problems"]] == [], out["problems"]
    assert out["mode"] == "explainer" and code == 0


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_the_first_of_two_rivals_replays_clean(
    root: Path, record: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """The red case, #415's: two versions superseded one head while both were open, and the
    first merged legitimately (its base held the head and nothing after it). Replayed on the tip,
    the second rival is on the working tree, and today the first is refused for it."""
    make = _make(record)
    v1, _ = make(root, "First.")
    _git(root, "init", "-q")
    seed = _commit(root, "seed")
    make(root, "One rival.", supersedes=v1)
    merge = _commit(root, "merge the first rival")
    make(root, "The other rival.", supersedes=v1)
    _commit(root, "merge the second rival")  # main's tip, checked out, as on a replay
    code, out = _classify(root, seed, merge, capsys)
    assert [p["code"] for p in out["problems"]] == [], out["problems"]
    assert code == 0


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_replay_passes_when_the_superseded_version_was_withdrawn_later(
    root: Path, record: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """A withdrawal merged after the version is no fact about its base either."""
    make = _make(record)
    v1, _ = make(root, "First.")
    _git(root, "init", "-q")
    seed = _commit(root, "seed")
    make(root, "Second.", supersedes=v1)
    merge = _commit(root, "merge v2")
    withdraw(root, f"{record}/{v1}.md", STEWARD, n=1)
    _commit(root, "withdraw v1")
    code, out = _classify(root, seed, merge, capsys)
    assert [p["code"] for p in out["problems"]] == [], out["problems"]
    assert code == 0


@pytest.mark.parametrize("record", ["gloss", "explainer"])
def test_a_fork_is_still_refused(
    root: Path, record: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """#415/#417's shape: two versions supersede one head. The second to merge has the first on
    its base, so it is refused, naming the first as the head; replayed on the tip, the same."""
    make = _make(record)
    v1, _ = make(root, "First.")
    _git(root, "init", "-q")
    _commit(root, "seed")
    first, _ = make(root, "One rival.", supersedes=v1)
    base = _commit(root, "merge the first rival")
    make(root, "The other rival.", supersedes=v1)
    merge = _commit(root, "merge the second rival")
    make(root, "A third, later.", supersedes=first)
    _commit(root, "a later version")
    code, out = _classify(root, base, merge, capsys)
    [problem] = out["problems"]
    assert problem["code"] == "record-not-head" and code == 1
    assert problem["details"]["head"] == first
