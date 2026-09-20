"""Finding submission-waiting-on (the 2026-09-19 primes run, all four agents): ``GET
/submissions/<id>`` reported ``runs: [{"name": "gate", "conclusion": "failure"}]`` for a proof the
sandbox had passed, because step 9 is a job of the same workflow run and stays red until a
non-author approves (F07-T8). The guide promised the call tells a contributor "whether it is
waiting on the gate, on a step 9 review or on a branch update"; it could not, and an agent reading
it concluded its proof had failed.

F07-T22: a failed gate run on an open pull request carries its jobs, and the state says what the
pull request is ``waiting_on``. The seam half is in ``test_githost_seam.py``.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import make_harness

from opn_api import githost
from opn_api.mcp import results

GATE_JOB = "gate (steps 1, 2 and 4-8 in the sandbox)"
STEP9_JOB = "step 9 (a non-author approving review)"
POSTMERGE_JOB = "postmerge (step 9 record, gate signature, attestation commit)"
HEAD_SHA = "e" * 40


def job(name: str, conclusion: str | None, status: str = "completed") -> dict[str, Any]:
    return {"name": name, "status": status, "conclusion": conclusion}


def state(
    *,
    runs: tuple[dict[str, Any], ...] = (),
    mergeable_state: str = "blocked",
    open_: bool = True,
) -> githost.PullRequestState:
    return githost.PullRequestState(
        number=33,
        url="u",
        state="open" if open_ else "closed",
        merged=not open_,
        mergeable_state=mergeable_state,
        head_sha=HEAD_SHA,
        merge_commit_sha=None,
        runs=runs,
    )


def gate_run(conclusion: str | None, jobs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    run: dict[str, Any] = {
        "name": "gate",
        "status": "completed" if conclusion else "in_progress",
        "conclusion": conclusion,
        "url": "r",
    }
    if jobs is not None:
        run["jobs"] = jobs
    return run


@pytest.mark.parametrize(
    ("pull", "expected"),
    [
        (state(), "gate"),  # no run yet
        (state(runs=(gate_run(None),)), "gate"),
        (
            state(
                runs=(
                    gate_run(
                        "failure",
                        [
                            job(GATE_JOB, "success"),
                            job(STEP9_JOB, "failure"),
                            job(POSTMERGE_JOB, "skipped"),
                        ],
                    ),
                )
            ),
            "step9-review",
        ),
        (
            state(
                runs=(gate_run("failure", [job(GATE_JOB, "failure"), job(STEP9_JOB, "skipped")]),)
            ),
            "gate-failed",
        ),
        (state(runs=(gate_run("failure"),)), "gate-failed"),  # jobs unread: say the run's word
        (state(runs=(gate_run("success"),), mergeable_state="behind"), "branch-update"),
        (state(runs=(gate_run("success"),), mergeable_state="clean"), "merge"),
        (state(runs=(gate_run("success"),), mergeable_state="unknown"), "merge"),
        (state(runs=(gate_run("failure"),), open_=False), None),  # finished: nothing waits
        # a step9-refresh run on the same head is not the gate's word
        (
            state(
                runs=(
                    {"name": "step9-refresh", "status": "completed", "conclusion": "success"},
                    gate_run(None),
                )
            ),
            "gate",
        ),
    ],
)
def test_waiting_on_names_the_one_thing_the_pull_request_waits_for(
    pull: githost.PullRequestState, expected: str | None
) -> None:
    assert pull.waiting_on == expected
    assert pull.as_dict()["waiting_on"] == expected


def test_the_mcp_result_schema_carries_the_new_fields() -> None:
    doc = state(
        runs=(gate_run("failure", [job(GATE_JOB, "success"), job(STEP9_JOB, "failure")]),)
    ).as_dict()
    schema = results.load("get_submission")["$defs"]["pull_request"]
    assert "waiting_on" in schema["properties"]
    assert "jobs" in schema["properties"]["runs"]["items"]["properties"]
    assert set(doc) <= set(schema["properties"])


def test_the_fake_host_keeps_jobs_so_route_tests_can_say_what_waits() -> None:
    h = make_harness()
    h.githost.set_pull_request_state(
        7, runs=[gate_run("failure", [job(GATE_JOB, "success"), job(STEP9_JOB, "failure")])]
    )
    pull = h.githost.get_pull_request("o/r", 7)
    assert pull is not None and pull.waiting_on == "step9-review"
