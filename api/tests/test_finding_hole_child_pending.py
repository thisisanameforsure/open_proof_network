"""Testers 2026-10-09b (C6): a hole's child, written by the post-merge job of a merged partial,
answered ``404 node-unknown`` until the products were rendered, where a proposed node in the same
state answers ``409 products-pending`` naming its pull request. ``unknown_node`` could tell the
cases apart only for a node a submission *proposed*; a hole child is proposed by nobody.

The precheck job already names the node each hole is expected to become (F06-T15). The
submission's record now keeps those ids, both stores index them, and ``unknown_node`` answers
for a hole child as it answers for a proposal: ``409 node-pending`` while the partial's pull
request is open, ``409 products-pending`` once it merged, ``404`` once it closed unmerged — in
each case naming the pull request and the hole.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, TUTORIAL_PROOF, Harness, PrecheckKey, make_precheck_key
from mcp_client import McpClient
from test_finding_partial_witnesses import PARTIAL_PATH, hole, passing_job, submit
from test_store_seam import both  # noqa: F401 — the fixture, by name

from opn_api.store import Store, Submission

BUNDLE = {PARTIAL_PATH: TUTORIAL_PROOF}
CHILD = f"{TUTORIAL_NODE}--h3"
EXISTING = "already-proved"  # a node of the fixture graph a hole may restate


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def submitted_partial(harness: Harness, key: PrecheckKey) -> dict[str, Any]:
    token = harness.token_for("code_alice", "alice")
    holes = [
        {**hole("left"), "expected_node_id": CHILD, "expected_new": True},
        {**hole("right"), "expected_node_id": EXISTING, "expected_new": False},
    ]
    job = passing_job(harness, key, token, BUNDLE, holes)
    r = submit(harness, token, BUNDLE, job)
    assert r.status_code == 201, r.text
    doc: dict[str, Any] = r.json()
    return doc


def claim(harness: Harness, node_id: str) -> Any:
    token = harness.token_for("code_bob", "bob")
    return harness.client.post("/claims", json={"node_id": node_id}, headers=harness.auth(token))


def test_a_hole_child_is_pending_while_its_partial_is_open(
    harness: Harness, key: PrecheckKey
) -> None:
    receipt = submitted_partial(harness, key)
    r = claim(harness, CHILD)
    assert (r.status_code, r.json()["error"]) == (409, "node-pending"), r.text
    body = r.json()
    assert body["details"]["pr_number"] == receipt["pr_number"]
    assert "left" in body["message"] and str(receipt["pr_number"]) in body["message"]


def test_a_hole_child_is_products_pending_once_its_partial_merged(
    harness: Harness, key: PrecheckKey
) -> None:
    receipt = submitted_partial(harness, key)
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=True)
    r = claim(harness, CHILD)
    assert (r.status_code, r.json()["error"]) == (409, "products-pending"), r.text
    assert r.headers.get("Retry-After")
    assert r.json()["details"]["pr_number"] == receipt["pr_number"]
    # the same answer through the MCP's get_node
    refused = McpClient(harness).failed("get_node", {"node_id": CHILD, "include": []})
    assert refused["error"] == "products-pending", refused


def test_a_restated_node_is_not_claimed_by_the_partial(harness: Harness, key: PrecheckKey) -> None:
    """A hole that restates an existing node creates nothing: the existing node answers for
    itself, and the partial's record never stands in for it."""
    submitted_partial(harness, key)
    r = claim(harness, EXISTING)
    assert r.json().get("error") not in ("node-pending", "products-pending"), r.text


def test_a_hole_child_of_a_closed_partial_is_unknown(harness: Harness, key: PrecheckKey) -> None:
    receipt = submitted_partial(harness, key)
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=False)
    r = claim(harness, CHILD)
    assert (r.status_code, r.json()["error"]) == (404, "node-unknown"), r.text


def test_both_stores_index_a_submissions_expected_nodes(both: Store) -> None:  # noqa: F811
    record = Submission(
        id="01J0000000000000000000000A",
        kind="partial",
        node_id=TUTORIAL_NODE,
        target_id="tutorial",
        pr_number=7,
        pr_url="u",
        pseudonym="alice",
        precheck_job_id="j",
        created="2026-10-09T15:00:00Z",
        expected_nodes=(CHILD,),
    )
    both.put_submission(record)
    assert both.get_submission_expecting(CHILD) == record
    assert both.get_submission_expecting(EXISTING) is None
    # the newest partial expecting the node wins, as the by-node index does
    newer = Submission(**{**record.__dict__, "id": "01J0000000000000000000000B", "pr_number": 8})
    both.put_submission(newer)
    assert both.get_submission_expecting(CHILD) == newer
