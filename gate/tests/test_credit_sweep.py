"""F07-T59: the sweep for merges on a graph's main that no ``gate:`` commit credits.

The 2026-10-04 audit found four merges on the live graph's first-parent line (#2, #8, #72, #73)
with no gate commit naming them, by hand: nothing on a schedule looks. ``gate/tools/uncredited.py``
is that look. These tests drive it over a real git history built here: #2 credited by its own gate
commit, #3 touching a target with no credit (owed), #4 touching only a workflow (maintenance, owes
nothing), #5 credited only by a replay, and a ``gate: #23`` commit that must credit neither 2 nor 3.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import GRAPH_CHECKOUT

from opn_gate import config

TOOL = Path(__file__).resolve().parents[1] / "tools" / "uncredited.py"
GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"}  # fmt: skip


def load_tool() -> Any:
    spec = importlib.util.spec_from_file_location("uncredited", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # the dataclass resolves its module's namespace
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, env=GIT, capture_output=True, text=True
    )
    return done.stdout


def _merge(repo: Path, number: int, path: str) -> None:
    """A pull request's branch adding ``path``, merged into main the way the host merges it."""
    branch = f"pr{number}"
    _git(repo, "checkout", "-q", "-b", branch, "main")
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(f"{number}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"work for #{number}")
    _git(repo, "checkout", "-q", "main")
    message = f"Merge pull request #{number} from owner/{branch}"
    _git(repo, "merge", "-q", "--no-ff", "-m", message, branch)


def _gate(repo: Path, subject: str) -> None:
    _git(repo, "commit", "-q", "--allow-empty", "-m", subject)


@pytest.fixture
def history(tmp_path: Path) -> Path:
    repo = tmp_path / "graph"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("graph\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _merge(repo, 2, "targets/alpha/nodes/a/Proof.lean")
    _gate(repo, "gate: #2 pass")
    _merge(repo, 3, "targets/beta/nodes/b/Proof.lean")
    _merge(repo, 4, ".github/workflows/gate.yml")
    _gate(repo, "gate: #23 pass")  # names neither #2 nor #3
    _merge(repo, 5, "targets/alpha/nodes/c/Proof.lean")
    _gate(repo, "gate: #5 pass (replayed)")
    return repo


def test_sweep_finds_the_owed_merge_and_sets_maintenance_apart(history: Path) -> None:
    tool = load_tool()
    log = tool.parse_log(_git(history, "log", "--first-parent", "--format=%H%x09%P%x09%s", "main"))
    owed, no_target = tool.sweep(log, tool.targets_in(history))
    assert [m.number for m in owed] == [3]
    assert owed[0].targets == ("beta",)
    assert owed[0].branch == "pr3"
    assert [m.number for m in no_target] == [4]


def test_an_owed_merge_not_acknowledged_fails_the_run(
    history: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tool = load_tool()
    assert tool.main(["--graph", str(history)]) == 1
    out = capsys.readouterr().out
    assert "OWED: #3 " in out
    assert "#4" in out and "maintenance" in out


def test_an_acknowledged_merge_reports_but_passes(
    history: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tool = load_tool()
    monkeypatch.setattr(tool, "ACKNOWLEDGED", {3: "known"})
    assert tool.main(["--graph", str(history)]) == 0
    assert "acknowledged: #3 " in capsys.readouterr().out


def test_the_live_audit_findings_stay_pending_the_owner() -> None:
    """The four merges the audit found are acknowledged only so the sweep can go green on the
    rest; each reason says the decision is the owner's until he makes it."""
    tool = load_tool()
    assert set(tool.ACKNOWLEDGED) == {2, 8, 72, 73}
    assert all("owner" in reason for reason in tool.ACKNOWLEDGED.values())


def test_credits_grammar_matches_the_graph_post_merge_helper() -> None:
    """The subject grammars are copies of the graph workflow's; a change there must reach here."""
    if not GRAPH_CHECKOUT.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
    text = subprocess.run(
        ["git", "-C", str(GRAPH_CHECKOUT), "show", "origin/main:.github/workflows/gate.yml"],
        check=True, capture_output=True, text=True, env=env,
    ).stdout  # fmt: skip
    tool = load_tool()
    for name in ("MERGE_RE", "CREDIT_RE"):
        found = re.search(rf'^\s*{name} = re\.compile\(r"(.*)"\)$', text, re.MULTILINE)
        assert found, name
        assert getattr(tool, name).pattern == found.group(1), name
    assert tool.credits("gate: #2 #3 pass") == [2, 3]
    assert tool.credits("gate: #23 pass") == [23]
    assert tool.credits("gate: nothing") == []


def test_the_sweep_workflow_is_scheduled_and_read_only() -> None:
    """The sweep runs daily and on demand, holds no write permission and no graph credential."""
    path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "credit-sweep.yml"
    flow = yaml.safe_load(path.read_text())
    triggers = flow[True]  # YAML 1.1 reads the key `on` as a boolean
    assert "schedule" in triggers and "workflow_dispatch" in triggers
    assert flow["permissions"] == {"contents": "read"}
    steps = flow["jobs"]["sweep"]["steps"]
    graph = next(s for s in steps if s.get("with", {}).get("path") == "graph")
    assert graph["with"]["persist-credentials"] is False
    assert graph["with"]["fetch-depth"] == 0
    assert any("gate/tools/uncredited.py" in s.get("run", "") for s in steps)
