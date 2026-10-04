"""F07-T62: three ways the merge actor could stop with work waiting (audit 2026-10-04).

1. It read the open pull requests as one page of a hundred, and the host lists them newest first:
   with a hundred and one open, the oldest — the one the queue takes first — was never seen.
2. An up-to-date pull request whose gate check never started (no check run at all: a workflow that
   did not trigger, a runner that never picked it up) held its lane forever. HOLD_S was measured
   from the gate's start, and with no start there was nothing to measure from. It now falls back
   to when the host last changed the pull request (``updated_at``), so the hold ends HOLD_S later.
3. A service pull request whose diff is empty was placed in no lane, and a pull request in no lane
   closes every lane when it is first: an empty diff whose gate was running stopped the whole queue.
   An empty diff can change nothing any other lane is gated against, so it is a lane of its own.

The decision program runs here as ``merge.yml`` writes it, end to end against a fake host where the
read matters (the pages, the files), and through ``decide`` where it does not.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_lanes import NOW, green
from test_finding_merge_actor_workflow import (
    GATE_JOB,
    REPO,
    RULES,
    STEP9_JOB,
    check,
    load_doc,
    load_pick,
    pull,
)

MAIN = "f" * 40

#: The host's REST API as the pick step reads it, from one JSON document in GH_HOST.
FAKE_GH = r"""#!/usr/bin/env python3
import json, os, re, sys
args = sys.argv[1:]
host = json.loads(os.environ["GH_HOST"])
with open(os.environ["GH_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\n")
path = args[1]
repo = os.environ["REPO"]
pulls = sorted(host["pulls"], key=lambda p: p["number"])
if "direction=asc" not in path:
    pulls.reverse()  # the host lists newest first unless asked otherwise
def page_of(path):
    found = re.search(r"[?&]page=([0-9]+)", path)
    return int(found.group(1)) if found else 1
def out(doc):
    print(json.dumps(doc)); sys.exit(0)
if path == f"repos/{repo}/rules/branches/main":
    out(host["rules"])
if path.startswith(f"repos/{repo}/pulls?"):
    page = page_of(path)
    out(pulls[(page - 1) * 100 : page * 100])
if path == f"repos/{repo}/git/ref/heads/main":
    out({"object": {"sha": host["main"]}})
found = re.match(rf"repos/{repo}/git/ref/heads/(.+)$", path)
if found:
    ref = found.group(1)
    out({"object": {"sha": next(p["head"]["sha"] for p in pulls if p["head"]["ref"] == ref)}})
found = re.match(rf"repos/{repo}/commits/([0-9a-f]+)/check-runs", path)
if found:
    out({"check_runs": host["checks"].get(found.group(1), [])})
if path.startswith(f"repos/{repo}/compare/"):
    out({"ahead_by": 0, "merge_base_commit": {"sha": host["main"]}})
found = re.match(rf"repos/{repo}/pulls/([0-9]+)/files", path)
if found:
    files = host["files"].get(found.group(1), [])
    page = page_of(path)
    out([{"filename": f} for f in files[(page - 1) * 100 : page * 100]])
found = re.match(rf"repos/{repo}/pulls/([0-9]+)$", path)
if found:
    out({"number": int(found.group(1)), "mergeable": True})
print("unexpected: " + " ".join(args), file=sys.stderr)
sys.exit(1)
"""


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    return load_doc()


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    return load_pick(doc)


def red() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "failure"), check(STEP9_JOB, "skipped", id_=2)]


def gating(minutes_ago: float = 1) -> list[dict[str, Any]]:
    """A gate that started a minute ago by the wall clock: the pick step reads ``now`` itself."""
    stamp = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
    stamp = stamp.replace("+00:00", "Z")
    return [{**check(GATE_JOB, None), "started_at": stamp}, check(STEP9_JOB, None, id_=2)]


def run_pick(
    doc: dict[Any, Any],
    tmp_path: Path,
    pulls: list[dict[str, Any]],
    checks: dict[int, list[dict[str, Any]]],
    files: dict[int, list[str]],
) -> tuple[int, dict[str, str], str]:
    """The pick step as the workflow writes it, with one settle round instead of fifteen minutes
    of them (a hold is decided once; the tests below are about what is decided)."""
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    run = str(step["run"])
    assert "SETTLE_CAP_S = 15 * 60" in run
    run = run.replace("SETTLE_CAP_S = 15 * 60", "SETTLE_CAP_S = 0")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    output = tmp_path / "output"
    output.write_text("", encoding="utf-8")
    host = {
        "rules": RULES,
        "pulls": pulls,
        "main": MAIN,
        "checks": {p["head"]["sha"]: checks[p["number"]] for p in pulls},
        "files": {str(n): paths for n, paths in files.items()},
    }
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GH_HOST": json.dumps(host),
        "GH_LOG": str(tmp_path / "gh.log"),
        "GH_TOKEN": "fake",
        "REPO": REPO,
        "GITHUB_OUTPUT": str(output),
    }
    proc = subprocess.run(
        ["bash", "-c", run], capture_output=True, text=True, check=False, cwd=tmp_path, env=env
    )  # fmt: skip
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    return proc.returncode, outputs, proc.stdout + proc.stderr


@pytest.mark.parametrize("green_one", [1, 101])
def test_every_one_of_a_hundred_and_one_is_seen(
    doc: dict[Any, Any], tmp_path: Path, green_one: int
) -> None:
    """The host lists open pull requests newest first, a hundred to a page: the oldest was on the
    second page, and it is the one the queue takes first. Read oldest first, the newest is on the
    second page instead; every page is read, so either is seen."""
    pulls = [pull(n, f"submit/p{n}") for n in range(1, 102)]
    checks = {n: (green() if n == green_one else red()) for n in range(1, 102)}
    files = {n: [f"targets/t{n}/nodes/n/Proof.lean"] for n in range(1, 102)}
    code, out, said = run_pick(doc, tmp_path, pulls, checks, files)
    assert code == 0, said
    assert (out.get("number"), out.get("action")) == (str(green_one), "merge"), (out, said)


def test_an_empty_diff_holds_its_own_lane_and_no_other(doc: dict[Any, Any], tmp_path: Path) -> None:
    """An empty service pull request first in the queue, its gate running: the green pull requests
    on t1 and t2 behind it merge in the same run."""
    pulls = [pull(1, "append/empty"), pull(2, "submit/a"), pull(3, "submit/b")]
    checks = {1: gating(), 2: green(), 3: green()}
    files = {1: [], 2: ["targets/t1/nodes/n/Proof.lean"], 3: ["targets/t2/nodes/n/Proof.lean"]}
    code, out, said = run_pick(doc, tmp_path, pulls, checks, files)
    assert code == 0, said
    assert (out.get("number"), out.get("action")) == ("2 3", "merge merge"), (out, said)


def test_a_pull_request_in_no_lane_still_closes_every_lane(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    """The rule the empty diff was caught by stands for what it was written for: policy.json."""
    pulls = [pull(1, "propose/policy"), pull(2, "submit/a")]
    checks = {1: gating(), 2: green()}
    files = {1: ["policy.json"], 2: ["targets/t1/nodes/n/Proof.lean"]}
    code, out, said = run_pick(doc, tmp_path, pulls, checks, files)
    assert code == 0, said
    assert out.get("number", "") == "", (out, said)


def with_updated(pr: dict[str, Any], minutes_ago: float) -> dict[str, Any]:
    stamp = (NOW - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")
    return {**pr, "updated_at": stamp}


def test_a_gate_that_never_started_stops_holding_after_hold_s(pick: dict[str, Any]) -> None:
    hold_min = int(pick["HOLD_S"]) / 60
    never = with_updated(pull(1, "submit/a"), hold_min + 5)
    pulls = [never, pull(2, "submit/b")]
    checks: dict[int, list[dict[str, Any]]] = {1: [], 2: green()}
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    decided = pick["decide_lanes"](
        pulls, RULES, lambda s: checks[by_sha[s]], lambda s: 0, lambda n: False,
        now=NOW, lane_of=lambda n: "t1",
    )  # fmt: skip
    assert decided == [(2, pulls[1]["head"]["sha"], "merge")], decided


def test_a_gate_that_has_not_started_yet_still_holds(pick: dict[str, Any]) -> None:
    """The fallback is a bound, not a reason to stop holding: a pull request the host changed a
    minute ago, whose gate has not started yet, holds its lane as T31 says."""
    fresh = with_updated(pull(1, "submit/a"), 1)
    pulls = [fresh, pull(2, "submit/b")]
    checks: dict[int, list[dict[str, Any]]] = {1: [], 2: green()}
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    decided = pick["decide_lanes"](
        pulls, RULES, lambda s: checks[by_sha[s]], lambda s: 0, lambda n: False,
        now=NOW, lane_of=lambda n: "t1",
    )  # fmt: skip
    assert decided == [(1, pulls[0]["head"]["sha"], "hold")], decided


def test_a_batch_is_not_ended_by_a_gate_that_never_started(pick: dict[str, Any]) -> None:
    """The same bound inside a batch of appends (T45): an append whose gate never started and
    that the host last changed over HOLD_S ago does not end the batch."""
    hold_min = int(pick["HOLD_S"]) / 60
    pulls = [
        pull(1, "append/a"),
        with_updated(pull(2, "append/b"), hold_min + 5),
        pull(3, "append/c"),
    ]
    checks: dict[int, list[dict[str, Any]]] = {1: green(), 2: [], 3: green()}
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    decided = pick["decide_lanes"](
        pulls, RULES, lambda s: checks[by_sha[s]], lambda s: 0, lambda n: False,
        now=NOW, lane_of=lambda n: "t1",
    )  # fmt: skip
    assert [n for n, _s, a in decided if a == "merge"] == [1, 3], decided
