"""Submission refusals not yet named by a test (F07-R1, R2, R14; C7, C8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, TUTORIAL_PROOF, Harness, PrecheckKey, make_precheck_key

from opn_api import precheck

PREFIX = "targets/propositional/nodes/"
PROOF_PATH = f"{PREFIX}{TUTORIAL_NODE}/Proof.lean"


@pytest.fixture
def key(tmp_path: Path) -> PrecheckKey:
    return make_precheck_key(tmp_path)


def submit(h: Harness, token: str, **overrides: Any) -> Any:
    body: dict[str, Any] = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "proof",
        "bundle": {PROOF_PATH: TUTORIAL_PROOF},
    }
    body.update(overrides)
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def test_precheck_still_running_is_refused(harness: Harness, key: PrecheckKey) -> None:
    """R1: ``done`` means done; a job whose run is in flight is 400 naming its state."""
    token = harness.token_for("code_alice", "alice")
    harness.commit_precheck_key(key.public)
    created = harness.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": {PROOF_PATH: TUTORIAL_PROOF}},
        headers=harness.auth(token),
    ).json()
    harness.githost.start_run(f"job/{created['id']}")
    r = submit(harness, token, precheck_job_id=created["id"])
    assert r.status_code == 400
    assert r.json()["error"] == "precheck-not-done"
    assert "running" in r.json()["message"]
    assert harness.githost.pulls == []


def test_precheck_past_retention_is_refused(harness: Harness, key: PrecheckKey) -> None:
    """R1 with F06-R5: a result the service no longer serves cannot be submitted on."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    assert harness.client.get(f"/precheck/{job['id']}").json()["state"] == "done"
    harness.clock.advance(days=precheck.RESULT_RETENTION_DAYS)
    r = submit(harness, token, precheck_job_id=job["id"])
    assert r.status_code == 400
    assert r.json()["error"] == "precheck-expired"
    assert harness.githost.pulls == []


def test_errored_precheck_is_refused(harness: Harness, key: PrecheckKey) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.commit_precheck_key(key.public)
    created = harness.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": {PROOF_PATH: TUTORIAL_PROOF}},
        headers=harness.auth(token),
    ).json()
    harness.githost.finish_run(f"job/{created['id']}", conclusion="failure")
    r = submit(harness, token, precheck_job_id=created["id"])
    assert r.status_code == 400
    assert r.json()["error"] == "precheck-not-done"
    assert "error" in r.json()["message"]


def test_precheck_job_id_of_the_wrong_type_is_required_not_unknown(
    harness: Harness,
) -> None:
    token = harness.token_for("code_alice", "alice")
    for bad in (7, "", None, ["01X"]):
        r = submit(harness, token, precheck_job_id=bad)
        assert r.status_code == 400, bad
        assert r.json()["error"] == "precheck-required", bad


def test_tooling_shapes_are_refused_before_the_precheck_is_read(
    harness: Harness, key: PrecheckKey
) -> None:
    """R14: the declaration is validated for shape, never trusted, and refused first."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    shapes: tuple[Any, ...] = (
        "claude",
        7,
        ["claude"],
        {"model": 7},
        {"model": ["x"]},
        {"harness": {}},
    )
    for tooling in shapes:
        r = submit(harness, token, tooling=tooling, precheck_job_id=job["id"])
        assert r.status_code == 400, tooling
        assert r.json()["error"] == "tooling-invalid", tooling
    assert harness.githost.pulls == []
    # Unknown keys are ignored rather than refused; only the three declared fields land.
    r = submit(harness, token, tooling={"model": "m", "extra": "x"}, precheck_job_id=job["id"])
    assert r.status_code == 201, r.text
    assert '"extra"' not in harness.githost.pulls[-1].body


def test_missing_node_id_is_400(harness: Harness, key: PrecheckKey) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    for node_id in (None, "", 7):
        r = submit(harness, token, node_id=node_id, precheck_job_id=job["id"])
        assert r.status_code == 400, node_id
        assert r.json()["error"] == "node-id-missing", node_id


def test_push_failure_is_502_and_opens_nothing(harness: Harness, key: PrecheckKey) -> None:
    """C7: when the branch itself cannot be pushed, no pull request is attempted and the caller
    is told; the same submission opens once the host answers."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    assert harness.client.get(f"/precheck/{job['id']}").json()["state"] == "done"
    harness.githost.app_failure = "POST /repos/g/git/trees returned 502"
    r = submit(harness, token, precheck_job_id=job["id"])
    assert r.status_code == 502, r.text
    assert r.json()["error"] == "pull-request-failed"
    assert harness.githost.pulls == []
    pushes_before = len(harness.githost.pushes)

    harness.githost.app_failure = None
    assert submit(harness, token, precheck_job_id=job["id"]).status_code == 201
    assert len(harness.githost.pushes) == pushes_before + 1


def test_pr_failure_after_a_push_leaves_no_pull_request(harness: Harness, key: PrecheckKey) -> None:
    """C7: the branch may survive, the pull request does not exist, and the caller knows."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    harness.githost.pr_failure = "POST /repos/g/pulls returned 422: A pull request already exists"
    r = submit(harness, token, precheck_job_id=job["id"])
    assert r.status_code == 502
    assert harness.githost.pulls == []
    assert "submission_id" not in r.json()


def test_the_token_reaches_neither_the_commit_nor_the_pull_request(
    harness: Harness, key: PrecheckKey
) -> None:
    """C8: what lands on the public graph carries the pseudonym, never the credential."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    assert submit(harness, token, precheck_job_id=job["id"]).status_code == 201
    push = harness.githost.pushes[-1]
    pr = harness.githost.pulls[-1]
    for text in (push.message, pr.body, pr.title, *push.files.values()):
        assert token not in text
        assert "token-secret-for-tests" not in text
    identity_id = next(iter(harness.store.identities))
    assert identity_id not in pr.body, "the ledger name is the pseudonym, not the ULID"


def test_a_bundle_for_another_node_is_refused_on_paths_first(
    harness: Harness, key: PrecheckKey
) -> None:
    """R1 through F06-R1: the bundle's paths are judged against the node it names, so a proof
    of one node submitted as another is a path rejection before any precheck is consulted."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    r = submit(harness, token, node_id="and-reassoc", precheck_job_id=job["id"])
    assert r.status_code == 400
    assert r.json()["error"] == "path-forbidden"
    assert harness.githost.pulls == []
