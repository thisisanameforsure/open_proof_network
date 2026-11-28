"""F07-T90: a merge is replayed once, however many runs find it owed (Q95).

Read from the record: from 2026-11-23T15:34Z to 2026-11-24T02:11Z the graph's post-merge runs
dispatched 177 replays of PR #1681 (``gate: replay of #1681``), from runs on 175 distinct heads of
main. Every run's plan found #1681 uncredited, its own push run finished, and so dispatched a
replay. Nothing asked whether a replay of #1681 was already queued, and each replay waited behind
the others: the account runs twenty jobs at once, so the replays filled it, every pull request's
gate queued behind them, and #1681 stayed uncredited longer, which made the next run dispatch
another. When one of them did run, it checked the credit against the commit it was dispatched at,
hours old by then, not against main. 113 were still queued when they were cancelled by hand.

So the three places that dispatch a replay (the find step, the commit step and the publish
program) go through one command, ``dispatch-replay``, which skips a merge main already credits and
a merge whose replay is already queued or running. A replay reads the credit from main as the host
has it when the replay starts, and yields to an older replay of the same merge that has not ended.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc
from test_finding_postmerge_batch import (
    FAKE,
    REPO,
    Graph,
    git_env,
    helper_source,
    step_run,
)

#: The host, with state: dispatched replays are runs it lists afterwards, as GitHub's does. A run
#: is ``{"id", "display_title", "status"}``, the fields the actions runs listing carries.
STATEFUL_GH = r"""#!/usr/bin/env python3
import json, os, re, sys
args = sys.argv[1:]
state_path = os.environ["GH_STATE"]
state = json.load(open(state_path))
with open(os.environ["GH_LOG"], "a") as log:
    log.write(" ".join(args) + "\n")
if args[:2] == ["workflow", "run"]:
    number = next(a.split("=", 1)[1] for a in args if a.startswith("replay_pr="))
    state["runs"].append({"id": state["next_id"], "display_title": f"gate: replay of #{number}",
                          "status": "queued", "event": "workflow_dispatch"})
    state["next_id"] += 1
    json.dump(state, open(state_path, "w"))
    sys.exit(0)
path = next((a for a in args if a.startswith("repos/")), "")
if re.match(r"repos/[^/]+/[^/]+/actions/(workflows/gate\.yml/)?runs", path):
    if os.environ.get("GH_RUNS_DOWN"):
        sys.exit(1)
    event = re.search(r"event=([a-z_]+)", path)
    runs = [r for r in state["runs"] if not event or r.get("event") == event.group(1)]
    print(json.dumps({"total_count": len(runs), "workflow_runs": runs}))
    sys.exit(0)
found = re.match(r"repos/[^/]+/[^/]+/pulls/([0-9]+)$", path)
if found:
    pr = state["pulls"][found.group(1)]
    print(pr["user"]["login"] if "--jq" in args else json.dumps(pr))
    sys.exit(0)
sys.exit(0)
"""


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


class Host:
    """The fake ``gh`` on a PATH of its own, and the state it keeps."""

    def __init__(self, root: Path, *, runs: list[dict[str, Any]] | None = None) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.bin = root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(STATEFUL_GH, encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.state = root / "state.json"
        self.log = root / "gh.log"
        self.save({"runs": runs or [], "next_id": 1000, "pulls": {}})

    def save(self, doc: dict[str, Any]) -> None:
        self.state.write_text(json.dumps(doc), encoding="utf-8")

    def load(self) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.state.read_text(encoding="utf-8"))
        return loaded

    def pull(self, number: int, merge: str) -> None:
        doc = self.load()
        doc["pulls"][str(number)] = {
            "number": number, "merged_at": "x", "merge_commit_sha": merge,
            "user": {"login": "bot"},
        }  # fmt: skip
        self.save(doc)

    def env(self, **extra: str) -> dict[str, str]:
        env = git_env()
        env.update(
            PATH=f"{self.bin}{os.pathsep}{env['PATH']}", GH_STATE=str(self.state),
            GH_LOG=str(self.log), GH_TOKEN=FAKE, GITHUB_REPOSITORY=REPO, OPN_GH_RETRY_SLEEP="0",
        )  # fmt: skip
        env.update(extra)
        return env

    def dispatches(self) -> list[str]:
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return [c for c in calls if c.startswith("workflow run gate.yml")]


@pytest.fixture
def helper_file(gate_doc: dict[Any, Any], tmp_path: Path) -> Path:
    path = tmp_path / "postmerge_batch.py"
    path.write_text(helper_source(gate_doc), encoding="utf-8")
    return path


def building(graph: Graph, number: int) -> str:
    """A building merge: a proof on t1, the kind no later run records for it (F07-T55)."""
    return graph.merge(
        number, f"submit/s{number}", {f"targets/t1/nodes/n{number}/Proof.lean": "proof\n"}
    )


# --- the dispatch -----------------------------------------------------------------------------


def dispatch(helper_file: Path, graph: Graph, host: Host, *numbers: int) -> str:
    proc = subprocess.run(
        [sys.executable, str(helper_file), "dispatch-replay", "HEAD", *map(str, numbers)],
        capture_output=True, text=True, check=False, cwd=graph.root, env=host.env(),
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout + proc.stderr


def test_the_night_of_1681_dispatches_one_replay(helper_file: Path, tmp_path: Path) -> None:
    """The record: one owed building merge and a run after every later merge. Each run asks for
    the replay; the host dispatches it once, and every later run is told it is already queued."""
    graph = Graph(tmp_path / "g")
    building(graph, 2)
    host = Host(tmp_path / "host")
    said = []
    for n in range(3, 13):  # ten later merges, each with a post-merge run of its own
        graph.append(n)
        said.append(dispatch(helper_file, graph, host, 2))
    assert len(host.dispatches()) == 1, host.dispatches()
    assert "replay_pr=2" in host.dispatches()[0]
    assert all("already queued or running" in s for s in said[1:]), said


def test_a_replay_that_has_ended_without_crediting_is_dispatched_again(
    helper_file: Path, tmp_path: Path
) -> None:
    """Only a replay that has not ended holds the dispatch: one that failed is not a record."""
    graph = Graph(tmp_path / "g")
    building(graph, 2)
    host = Host(
        tmp_path / "host",
        runs=[{"id": 7, "display_title": "gate: replay of #2", "status": "completed",
               "event": "workflow_dispatch"}],
    )  # fmt: skip
    dispatch(helper_file, graph, host, 2)
    assert len(host.dispatches()) == 1


def test_a_replay_of_another_merge_does_not_hold_this_one(
    helper_file: Path, tmp_path: Path
) -> None:
    """The match is the whole number: a queued replay of #21 is not one of #2."""
    graph = Graph(tmp_path / "g")
    building(graph, 2)
    host = Host(
        tmp_path / "host",
        runs=[{"id": 7, "display_title": "gate: replay of #21", "status": "queued",
               "event": "workflow_dispatch"}],
    )  # fmt: skip
    dispatch(helper_file, graph, host, 2)
    assert len(host.dispatches()) == 1


def test_a_credited_merge_is_never_dispatched(helper_file: Path, tmp_path: Path) -> None:
    graph = Graph(tmp_path / "g")
    building(graph, 2)
    graph.bot(2)
    host = Host(tmp_path / "host")
    dispatch(helper_file, graph, host, 2)
    assert host.dispatches() == []


def test_a_host_that_cannot_list_runs_still_dispatches(helper_file: Path, tmp_path: Path) -> None:
    """C7: a record is never lost to a host that does not answer. A replay then costs a run, and
    the replay's own check keeps it from crediting anything twice."""
    graph = Graph(tmp_path / "g")
    building(graph, 2)
    host = Host(tmp_path / "host")
    proc = subprocess.run(
        [sys.executable, str(helper_file), "dispatch-replay", "HEAD", "2"],
        capture_output=True, text=True, check=False, cwd=graph.root,
        env=host.env(GH_RUNS_DOWN="1"),
    )  # fmt: skip
    assert proc.returncode == 0, proc.stderr
    assert len(host.dispatches()) == 1


def test_every_dispatch_of_a_replay_goes_through_the_one_command(gate_doc: dict[Any, Any]) -> None:
    """The three dispatch sites of 2026-11-24 (the find step's ``dispatch_replays``, the commit
    step's ``replay_owed`` and the publish program's ``replay``) each called ``gh workflow run``
    on their own; none asked the host what was queued."""
    steps = gate_doc["jobs"]["postmerge"]["steps"]
    for step in steps:
        run = str(step.get("run", ""))
        shell = run.split("<<'PY'", 1)[0] + (run.split("\nPY\n", 1)[1] if "\nPY\n" in run else "")
        assert not re.search(r"gh workflow run gate\.yml", shell), step.get("name")
    source = helper_source(gate_doc)
    calls = [m.start() for m in re.finditer(r'"workflow", "run", "gate\.yml"', source)]
    assert len(calls) == 1, "one place dispatches a replay"
    publish = source[source.index("def run_publish") :]
    body = publish[publish.index("def replay(") : publish.index("def follow(")]
    assert "dispatch_replay(" in body, body


# --- the replay itself --------------------------------------------------------------------------


def run_replay(
    gate_doc: dict[Any, Any],
    graph: Graph,
    host: Host,
    tmp_path: Path,
    *,
    at: str,
    number: int,
    run_id: int,
) -> tuple[int, dict[str, str], str]:
    """The ``pr`` step on a dispatch: a clone of ``graph`` checked out at ``at`` (main's head when
    the replay was dispatched), with ``origin`` the graph as it is now."""
    clone = tmp_path / f"clone-{run_id}"
    subprocess.run(["git", "clone", "-q", str(graph.root), str(clone)], check=True, env=git_env())
    subprocess.run(["git", "-C", str(clone), "checkout", "-q", at], check=True, env=git_env())
    runner_temp = tmp_path / f"temp-{run_id}"
    runner_temp.mkdir()
    output = runner_temp / "output"
    output.write_text("", encoding="utf-8")
    env = host.env(
        GITHUB_EVENT_NAME="workflow_dispatch", GITHUB_SHA=at, GITHUB_OUTPUT=str(output),
        RUNNER_TEMP=str(runner_temp), REPLAY_PR=str(number), GITHUB_RUN_ID=str(run_id),
        PUSH_BEFORE="",
    )  # fmt: skip
    proc = subprocess.run(
        ["bash", "-c", step_run(gate_doc, id_="pr")],
        capture_output=True, text=True, check=False, cwd=clone, env=env,
    )  # fmt: skip
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    return proc.returncode, outputs, proc.stdout + proc.stderr


def test_a_replay_reads_the_credit_from_main_as_it_is_not_as_dispatched(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """#1681's replays queued for hours: by the time one ran, main credited #1681 (13e28997e4),
    while the commit it had been dispatched at did not."""
    graph = Graph(tmp_path / "g")
    two = building(graph, 2)
    dispatched_at = graph.append(3)
    graph.bot(2, 3)  # another run credited #2 while the replay waited
    host = Host(tmp_path / "host")
    host.pull(2, two)
    code, out, said = run_replay(
        gate_doc, graph, host, tmp_path, at=dispatched_at, number=2, run_id=500
    )
    assert code == 0, said
    assert out.get("run") == "false", (out, said)
    assert "already has its gate commit" in said, said


def test_a_replay_yields_to_an_older_replay_of_the_same_merge(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """Two runs that dispatch at the same moment can each find nothing queued. The newer replay
    yields to the older; the older, finding only a newer one, goes on, so the merge is replayed
    exactly once and never dropped."""
    graph = Graph(tmp_path / "g")
    two = building(graph, 2)
    runs = [
        {"id": 400, "display_title": "gate: replay of #2", "status": "in_progress",
         "event": "workflow_dispatch"},
        {"id": 500, "display_title": "gate: replay of #2", "status": "in_progress",
         "event": "workflow_dispatch"},
    ]  # fmt: skip
    host = Host(tmp_path / "host", runs=runs)
    host.pull(2, two)
    code, out, said = run_replay(gate_doc, graph, host, tmp_path, at=two, number=2, run_id=500)
    assert code == 0, said
    assert out.get("run") == "false", (out, said)
    assert "an older replay of #2" in said, said
    code, out, said = run_replay(gate_doc, graph, host, tmp_path, at=two, number=2, run_id=400)
    assert code == 0, said
    assert out.get("run") == "true" and out.get("number") == "2", (out, said)
