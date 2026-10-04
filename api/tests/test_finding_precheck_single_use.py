"""F06-T11 (audit 2026-10-04): a precheck job opens one pull request.

``submissions.bound_job`` checked that a job was done, passing, the caller's and over the same
bundle, and never marked it used: one passing precheck could be submitted again and again for as
long as its result was retained, each time a new pull request and a full gate run that no new
precheck had paid for (F06-R8's precheck limit bounded nothing). On the tutorial node, which
D-27 keeps open to rehearsal and the duplicate rule therefore skips, nothing else stopped it.

Now the job is taken atomically around the opening (``precheckused#<job>`` in the tokens table,
a key prefix as every new item there is, with the job's retention as its TTL): a second
submission on the same job is 409 ``precheck-used``, and a pull request that failed to open gives
the job back, so the caller can send the same request again at once (C7).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, Harness, PrecheckKey, make_harness, make_precheck_key
from test_store_seam import dynamo
from test_submissions import submit

from opn_api.store import MemoryStore


@pytest.fixture(params=["memory", "dynamodb"])
def harness(request: pytest.FixtureRequest) -> Any:
    store = MemoryStore() if request.param == "memory" else dynamo()
    h = make_harness(store=store)
    with h.client:
        yield h


@pytest.fixture
def key(tmp_path: Path) -> PrecheckKey:
    return make_precheck_key(tmp_path)


def test_a_precheck_job_opens_one_pull_request(harness: Harness, key: PrecheckKey) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    first = submit(harness, token, precheck_job_id=job["id"])
    assert first.status_code == 201, first.text
    second = submit(harness, token, precheck_job_id=job["id"])
    assert second.status_code == 409, second.text
    assert second.json()["error"] == "precheck-used"
    assert job["id"] in second.json()["message"]
    assert len(harness.githost.pulls) == 1
    submitted = [p for p in harness.githost.pushes if p.branch.startswith("submit/")]
    assert len(submitted) == 1  # the other push is the precheck job's own


def test_a_pull_request_that_failed_to_open_gives_the_job_back(
    harness: Harness, key: PrecheckKey
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    harness.githost.pr_failure = "POST /repos/.../pulls returned 502"
    failed = submit(harness, token, precheck_job_id=job["id"])
    assert failed.status_code == 502, failed.text
    harness.githost.pr_failure = None
    again = submit(harness, token, precheck_job_id=job["id"])
    assert again.status_code == 201, again.text
    assert again.json()["node_id"] == TUTORIAL_NODE
    third = submit(harness, token, precheck_job_id=job["id"])
    assert third.status_code == 409, third.text


def test_a_refusal_before_the_opening_does_not_spend_the_job(
    harness: Harness, key: PrecheckKey
) -> None:
    """Only an opened pull request uses the job: a request refused for another reason (here the
    wrong artifact type for the path) leaves it whole."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    refused = submit(harness, token, precheck_job_id=job["id"], artifact_type="partial")
    assert refused.status_code == 400, refused.text
    assert submit(harness, token, precheck_job_id=job["id"]).status_code == 201
