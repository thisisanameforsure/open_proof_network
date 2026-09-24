"""F07-T42 (testers 2026-09-24): ``pull_request.runs[].jobs`` had two shapes.

The story. The erdos-69 HTTP agent (``engineering/evidence/testers-2026-09-24/erdos-69-http.md``,
12:37Z, reproduced on #175 and a second pull request) read ``GET /submissions/<id>`` while its pull
request was open and found ``runs[].jobs``; once it merged the key was gone, and a client that read
``r["jobs"]`` crashed on the merged submission. Expected: the same shape in both states, an empty
list when nothing was read.

The mechanism. ``HttpxGitHost.get_pull_request`` reads a run's jobs only where the run's colour is
ambiguous (F07-T22, T32): a gate run that failed or has not finished, on an open pull request. It
added the key only to those runs, so a merged pull request, a closed one, and every green or
non-gate run on an open one carried no ``jobs`` at all. The record then closed with that shape in
``final_state``, so every merged submission read back without the key for good.

The rule. Every run carries ``jobs``: the latest attempt's jobs where they were read, ``[]`` where
they were not. A record closed before the change is read back in the same shape, so old merged
submissions agree with new ones.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, make_harness
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
from test_store_seam import dynamo

from opn_api.githost import HttpxGitHost
from opn_api.mcp import results
from opn_api.store import MemoryStore, Store, Submission

__all__ = ["host", "pem", "rsa_key", "script"]  # fixtures, imported for pytest to find

JOBS = f"/repos/{REPO}/actions/runs/9/jobs"
GATE_JOB = "gate (steps 1, 2 and 4-8 in the sandbox)"
STEP9_JOB = "step 9 (a non-author approving review)"


def pull_body(state: str, *, merged: bool) -> dict[str, Any]:
    return {
        "number": 33,
        "html_url": "https://github.com/owner/scratch/pull/33",
        "state": state,
        "merged": merged,
        "mergeable_state": "unknown",
        "head": {"sha": HEAD_SHA},
        "merge_commit_sha": "d" * 40 if merged else None,
    }


RUNS = {
    "workflow_runs": [
        {"id": 9, "name": "gate", "status": "completed", "conclusion": "success"},
        {"id": 10, "name": "step9-refresh", "status": "completed", "conclusion": "skipped"},
    ]
}


def test_a_merged_pull_request_carries_jobs_on_every_run(
    script: Script, host: HttpxGitHost
) -> None:
    """The seam: a merged pull request's runs each carry ``jobs``, and none was read for it (the
    merged case costs no extra call, as before)."""
    install_app(script).on("GET", PULL, json=pull_body("closed", merged=True)).on(
        "GET", REVIEWS, json=[]
    ).on("GET", ACTION_RUNS, json=RUNS)
    pull = host.get_pull_request(REPO, 33)
    assert pull is not None
    assert [r.get("jobs") for r in pull.runs] == [[], []], pull.runs
    assert [r.get("jobs") for r in pull.as_dict()["runs"]] == [[], []]
    assert script.to("GET", JOBS) == []


def test_a_green_run_on_an_open_pull_request_carries_jobs_too(
    script: Script, host: HttpxGitHost
) -> None:
    """Open, green, not ambiguous: no jobs read, and the key is still there."""
    install_app(script).on("GET", PULL, json=pull_body("open", merged=False)).on(
        "GET", REVIEWS, json=[]
    ).on("GET", ACTION_RUNS, json=RUNS)
    pull = host.get_pull_request(REPO, 33)
    assert pull is not None
    assert all(r.get("jobs") == [] for r in pull.runs), pull.runs
    assert pull.waiting_on == "merge"


def test_an_open_failed_gate_run_keeps_its_fetched_jobs(script: Script, host: HttpxGitHost) -> None:
    """Guard: where the jobs were read they are the answer, and the other run gets ``[]``."""
    install_app(script).on("GET", PULL, json=pull_body("open", merged=False)).on(
        "GET", REVIEWS, json=[]
    ).on(
        "GET",
        ACTION_RUNS,
        json={
            "workflow_runs": [
                {"id": 9, "name": "gate", "status": "completed", "conclusion": "failure"},
                {"id": 10, "name": "step9-refresh", "status": "completed", "conclusion": "success"},
            ]
        },
    ).on(
        "GET",
        JOBS,
        json={
            "jobs": [
                {"name": GATE_JOB, "status": "completed", "conclusion": "success"},
                {"name": STEP9_JOB, "status": "completed", "conclusion": "failure"},
            ]
        },
    )
    pull = host.get_pull_request(REPO, 33)
    assert pull is not None
    assert pull.runs[0]["jobs"] == [
        {"name": GATE_JOB, "status": "completed", "conclusion": "success"},
        {"name": STEP9_JOB, "status": "completed", "conclusion": "failure"},
    ]
    assert pull.runs[1].get("jobs") == []
    assert pull.waiting_on == "step9-review"


# --- a record closed before the change --------------------------------------------------------

#: The shape ``final_state`` was stored in before F07-T42: ``as_dict()`` of a merged pull request
#: whose runs carry no ``jobs`` key (#175's, as the tester read it back).
LEGACY_FINAL_STATE: dict[str, Any] = {
    "waiting_on": None,
    "number": 7,
    "url": "https://github.com/o/r/pull/7",
    "state": "closed",
    "merged": True,
    "mergeable_state": "unknown",
    "head_sha": "7" * 40,
    "merge_commit_sha": "8" * 40,
    "runs": [
        {"name": "gate", "status": "completed", "conclusion": "success", "url": "u"},
        {"name": "step9-refresh", "status": "completed", "conclusion": "skipped", "url": "v"},
    ],
    "reviews": [],
}


@pytest.fixture(params=["memory", "dynamodb"])
def store(request: pytest.FixtureRequest) -> Store:
    return MemoryStore() if request.param == "memory" else dynamo()


def test_a_record_closed_before_the_change_reads_with_jobs(store: Store) -> None:
    """A merged postmortem closed with the old shape: the route answers every run with ``jobs``
    and costs no host call (a closed record is never looked up again), and the answer validates
    against the MCP adapter's schema, which now requires the key."""
    h = make_harness(store=store)
    with h.client:
        record = Submission(
            id="01M00000000000000000000007",
            kind="postmortem",
            node_id=TUTORIAL_NODE,
            target_id="propositional",
            pr_number=7,
            pr_url="https://github.com/o/r/pull/7",
            pseudonym="alice",
            precheck_job_id=None,
            created="2026-09-24T12:00:00Z",
        )
        store.put_submission(record)
        store.close_submission(
            record.id, closed="2026-09-24T12:30:00Z", final_state=LEGACY_FINAL_STATE
        )
        r = h.client.get("/submissions/7")
        assert r.status_code == 200, r.text
        doc = r.json()
        assert [run.get("jobs") for run in doc["pull_request"]["runs"]] == [[], []], doc
        assert h.githost.pull_lookups == []
        assert results.violations("get_submission", doc) == []


def test_the_mcp_schema_requires_jobs_on_every_run() -> None:
    """The adapter's result schema says what the route now guarantees: a run without ``jobs``
    is a violation, so the shape cannot quietly regress (F09-Q5: reshaped in place)."""
    run = {"name": "gate", "status": "completed", "conclusion": "success", "url": "u"}
    doc = {
        "submission": None,
        "pull_request": {**LEGACY_FINAL_STATE, "runs": [run]},
        "pull_request_error": None,
        "attestation_path": None,
        "attestation": None,
        "attestation_note": None,
    }
    assert results.violations("get_submission", doc) != []
    fixed = {**doc, "pull_request": {**LEGACY_FINAL_STATE, "runs": [{**run, "jobs": []}]}}
    assert results.violations("get_submission", fixed) == []


def test_the_fake_host_answers_in_the_seams_shape() -> None:
    """The route tests' host keeps the seam's shape, so a route test cannot pass on a run the
    real host would never produce."""
    h = make_harness()
    h.githost.set_pull_request_state(
        7, state="closed", merged=True, runs=[{"name": "gate", "status": "completed"}]
    )
    pull = h.githost.get_pull_request("o/r", 7)
    assert pull is not None
    assert [r.get("jobs") for r in pull.runs] == [[]]
