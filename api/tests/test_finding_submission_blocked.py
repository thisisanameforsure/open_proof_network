"""Finding precheck-blocked, the submission half (2026-09-13, the Euclid tester; plan F06-T6).

``POST /precheck`` refuses a blocked node (``test_finding_precheck_blocked.py``). A precheck job
outlives the state it was minted in: a job that passed while the node was ready still binds a
submission once a merge has turned the node ``blocked``, and ``POST /submissions`` then opened a
pull request the gate can only refuse at the dependency check — a hosted run spent, and a red
check on the graph, for a node the service already knew could not pass.

The fix (plan F06-T6, "after their commit: the same call at submissions.py"): ``post_submissions``
calls ``precheck.check_open`` right after ``node_facts``, before the bundle is placed or any
precheck job is bound, so the refusal is the shared ``409 node-blocked`` (F05-T9), nothing is
pushed, and nothing is recorded (F07-T16).
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness, PrecheckKey, make_precheck_key
from mcp_client import NODE
from test_finding_mcp_bootstrap import HOLE, add_hole
from test_finding_precheck_blocked import UNPROVED_DEP, block_node, bundle


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def submit(h: Harness, token: str, node_id: str, job_id: str | None) -> Any:
    body: dict[str, Any] = {"node_id": node_id, "artifact_type": "proof", "bundle": bundle(node_id)}
    if job_id is not None:
        body["precheck_job_id"] = job_id
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def nothing_opened(h: Harness, pushes_before: int) -> None:
    assert len(h.githost.pushes) == pushes_before, "a branch was pushed for a blocked node"
    assert h.githost.pulls == [], "a pull request was opened for a blocked node"
    assert h.store.list_open_submissions() == [], "a submission was recorded for a blocked node"


def test_a_job_minted_before_the_node_turned_blocked_opens_nothing(
    harness: Harness, key: PrecheckKey
) -> None:
    """The edge the precheck refusal cannot see: the job passed while ``and-reassoc`` was ready,
    then the node turned blocked on an unproved dependency. The submission bound to that job is
    ``409 node-blocked`` naming the dependency, with the details F05-T9 gives."""
    token = harness.token_for("code_alice", "alice-p")
    job = harness.tutorial_job(key, node=NODE, token=token)  # minted while the node was ready
    block_node(harness)
    pushes = len(harness.githost.pushes)  # the precheck's own job branch (F06-R3)

    r = submit(harness, token, NODE, job["id"])
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-blocked"), body
    assert UNPROVED_DEP in body["message"], body["message"]
    assert body["details"] == {"status": "blocked", "cause": None, "unproved_deps": [UNPROVED_DEP]}
    nothing_opened(harness, pushes)


def test_a_blocked_node_is_refused_before_the_precheck_binding(harness: Harness) -> None:
    """The refusal is about the node, so it comes before the request's precheck is looked at: a
    witness-missing hole with no ``precheck_job_id`` at all is ``node-blocked`` naming the
    witness route, not ``precheck-required``."""
    add_hole(harness)
    token = harness.token_for("code_alice", "alice-p")
    r = submit(harness, token, HOLE, None)
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-blocked"), body
    assert "/proposals/witness" in body["message"], body["message"]
    nothing_opened(harness, 0)


def test_pin_a_ready_node_still_submits(harness: Harness, key: PrecheckKey) -> None:
    """**PIN.** The same job and bundle on the node while it is still ready opens the pull
    request, so the refusal above is about the node's status and nothing else."""
    token = harness.token_for("code_alice", "alice-p")
    job = harness.tutorial_job(key, node=NODE, token=token)
    r = submit(harness, token, NODE, job["id"])
    assert r.status_code == 201, r.text
