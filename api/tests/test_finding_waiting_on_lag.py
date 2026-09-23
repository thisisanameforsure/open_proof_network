"""F07-T32, the service's half (testers 2026-09-23): ``waiting_on`` read the run's own status,
which the host reports late, and had no word for a conflict.

* #148 at 15:08:31: ``GET /submissions`` and the host disagreed about its gate for as long as the
  run's status lagged its jobs (#147's post-merge run: eight minutes). The merge actor now asks the
  jobs (``postmerge_running_from``); so does this.
* #150 conflicted with ``main`` after #146 merged the same witness, and read ``waiting_on:
  merge`` until it was closed: a contributor told to wait for a merge that can never come.
"""

from __future__ import annotations

from typing import Any

import pytest
from test_finding_submission_waiting_on import GATE_JOB, STEP9_JOB, gate_run, job, state
from test_githost_seam import (  # the seam's fixtures, reused as they stand
    ACTION_RUNS,
    HEAD_SHA,
    PULL,
    REPO,
    REVIEWS,
    Script,
    host,
    install_app,
    pem,
    rsa_key,
    script,
)

from opn_api import githost
from opn_api.githost import HttpxGitHost
from opn_api.mcp import results

JOBS = f"/repos/{REPO}/actions/runs/9/jobs"
__all__ = ["host", "pem", "rsa_key", "script"]  # fixtures, imported for pytest to find


def lagging(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """A gate run the host still calls in progress, with the jobs it has already finished."""
    return {**gate_run(None), "jobs": jobs}


@pytest.mark.parametrize(
    ("pull", "expected"),
    [
        # the run's status lags; its jobs have finished green
        (
            state(
                runs=(lagging([job(GATE_JOB, "success"), job(STEP9_JOB, "skipped")]),),
                mergeable_state="clean",
            ),
            "merge",
        ),
        (
            state(
                runs=(lagging([job(GATE_JOB, "success"), job(STEP9_JOB, "skipped")]),),
                mergeable_state="behind",
            ),
            "branch-update",
        ),
        # finished red, the run still says in progress
        (
            state(runs=(lagging([job(GATE_JOB, "failure"), job(STEP9_JOB, "skipped")]),)),
            "gate-failed",
        ),
        (
            state(runs=(lagging([job(GATE_JOB, "success"), job(STEP9_JOB, "failure")]),)),
            "step9-review",
        ),
        # a job still running is the gate still running
        (
            state(runs=(lagging([job(GATE_JOB, None, status="in_progress")]),)),
            "gate",
        ),
        (state(runs=(lagging([]),)), "gate"),  # no job started yet
        # a conflict is its own answer, whatever the gate said
        (state(runs=(gate_run("success"),), mergeable_state="dirty"), "conflict"),
        (
            state(
                runs=(lagging([job(GATE_JOB, "success"), job(STEP9_JOB, "skipped")]),),
                mergeable_state="dirty",
            ),
            "conflict",
        ),
    ],
)
def test_waiting_on_reads_the_jobs_and_names_a_conflict(
    pull: githost.PullRequestState, expected: str
) -> None:
    assert pull.waiting_on == expected


def test_the_schema_admits_conflict() -> None:
    schema = results.load("get_submission")["$defs"]["pull_request"]["properties"]["waiting_on"]
    assert "conflict" in str(schema), schema


def test_an_unfinished_gate_run_on_an_open_pull_request_carries_its_jobs(
    script: Script, host: HttpxGitHost
) -> None:
    """The seam reads the jobs of a gate run the host has not called complete, as it already did
    for a failed one."""
    install_app(script).on(
        "GET",
        PULL,
        json={
            "number": 33,
            "html_url": "u",
            "state": "open",
            "merged": False,
            "mergeable_state": "clean",
            "head": {"sha": HEAD_SHA},
        },
    ).on("GET", REVIEWS, json=[]).on(
        "GET",
        ACTION_RUNS,
        json={"workflow_runs": [{"id": 9, "name": "gate", "status": "in_progress"}]},
    ).on(
        "GET",
        JOBS,
        json={
            "jobs": [
                {"name": GATE_JOB, "status": "completed", "conclusion": "success"},
                {"name": STEP9_JOB, "status": "completed", "conclusion": "skipped"},
            ]
        },
    )
    pull = host.get_pull_request(REPO, 33)
    assert pull is not None and pull.waiting_on == "merge", pull
