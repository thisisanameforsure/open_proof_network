"""F07-T40: a proof submission's receipt says what else is on the node (testers 2026-09-24).

Six agents on the calibration targets, 2026-09-24. On erdos-402 two agents proved the same
variants within a minute of each other: ``tester-402-mcp`` opened #181 on ``variant-3377fd96``
while the other agent's #177 was already open for it, and #182 raced #183 on ``variant-a874fe93``.
On erdos-1050 two agents' partials (#196, #199) decomposed the same node. ``POST /submissions``
answered each with the submission alone — id, pull request, node — so each agent learned of its
rival only by reading ``GET /submissions.json`` later, and #181's author watched it sit at the head
of the queue "with nothing in the status saying the node was already proved".

Racing stays allowed (D-25: a node keeps every different proof; the loser becomes an alternate,
F07-T36), and a copy is still refused (``duplicates.check_proof``). What changes is the receipt:

* ``rivals: [{pr_number, pseudonym}]`` lists the submissions open on the node that can still
  merge, the new one excluded;
* on a node whose proof has merged, ``node_proved: true`` and, for a proof (which there is an
  alternate by placement, F07-T12), ``becomes: "alternate"``;
* when nothing applies, the keys are absent, not empty.

The MCP ``submit_proof`` passes the endpoint's body through its envelope, so it carries the keys.

Red run: ``engineering/evidence/F07/task-40.txt``.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import PROOF_PREFIX, Harness, PrecheckKey, make_precheck_key
from mcp_client import McpClient
from test_finding_duplicate_submissions import GATE_FAILED, OTHER_PROOF, PROOF
from test_submissions_alternate import mark_proved, passing_job, submit

RED = "F07-T40: the 201 body is the submission alone"
ALTERNATE = "attempts/20260924T120000Z-bob-alternate.lean"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def proof_of(node: str, text: str) -> dict[str, str]:
    return {f"{PROOF_PREFIX}{node}/Proof.lean": text}


def submitted(h: Harness, key: PrecheckKey, token: str, node: str, bundle: dict[str, str]) -> Any:
    got = submit(h, token, node, bundle, passing_job(h, key, token, node, bundle))
    assert got.status_code == 201, got.text
    return got.json()


@pytest.mark.xfail(strict=True, reason=RED)
def test_an_open_rival_proof_is_named(harness: Harness, key: PrecheckKey) -> None:
    """#177 open, then #181: the second receipt names the first, and not itself."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    _proved, node = mark_proved(harness)
    first = submitted(harness, key, alice, node, proof_of(node, PROOF))
    second = submitted(harness, key, bob, node, proof_of(node, OTHER_PROOF))
    assert second.get("rivals") == [{"pr_number": first["pr_number"], "pseudonym": "alice"}], second
    assert "node_proved" not in second and "becomes" not in second, second


def test_a_rival_that_can_no_longer_merge_is_not_named(harness: Harness, key: PrecheckKey) -> None:
    """A rival whose gate failed stands in nobody's way (the rule ``duplicates`` uses)."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    _proved, node = mark_proved(harness)
    first = submitted(harness, key, alice, node, proof_of(node, PROOF))
    harness.githost.set_pull_request_state(first["pr_number"], runs=GATE_FAILED)
    second = submitted(harness, key, bob, node, proof_of(node, OTHER_PROOF))
    assert "rivals" not in second, second


@pytest.mark.xfail(strict=True, reason=RED)
def test_a_proved_node_says_the_proof_becomes_an_alternate(
    harness: Harness, key: PrecheckKey
) -> None:
    bob = harness.token_for("code_bob", "bob")
    proved, _node = mark_proved(harness)
    harness.githost.files[f"{PROOF_PREFIX}{proved}/Proof.lean"] = PROOF.encode()
    got = submitted(harness, key, bob, proved, {f"{PROOF_PREFIX}{proved}/{ALTERNATE}": OTHER_PROOF})
    assert (got.get("node_proved"), got.get("becomes")) == (True, "alternate"), got
    assert "rivals" not in got


def test_a_node_with_nothing_open_says_nothing(harness: Harness, key: PrecheckKey) -> None:
    alice = harness.token_for("code_alice", "alice")
    _proved, node = mark_proved(harness)
    got = submitted(harness, key, alice, node, proof_of(node, PROOF))
    assert not {"rivals", "node_proved", "becomes"} & set(got), got


def test_a_copy_is_still_refused(harness: Harness, key: PrecheckKey) -> None:
    """Guard: naming rivals changes no refusal; the copy rule stands in front of it."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    _proved, node = mark_proved(harness)
    submitted(harness, key, alice, node, proof_of(node, PROOF))
    bundle = proof_of(node, PROOF)
    got = submit(harness, bob, node, bundle, passing_job(harness, key, bob, node, bundle))
    assert (got.status_code, got.json()["error"]) == (409, "duplicate-submission"), got.text


@pytest.mark.xfail(strict=True, reason=RED)
def test_mcp_submit_proof_passes_the_keys_through(harness: Harness, key: PrecheckKey) -> None:
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    _proved, node = mark_proved(harness)
    first = submitted(harness, key, alice, node, proof_of(node, PROOF))
    bundle = proof_of(node, OTHER_PROOF)
    job = passing_job(harness, key, bob, node, bundle)
    args = {"node_id": node, "artifact_type": "proof", "bundle": bundle, "precheck_job_id": job}
    got = McpClient(harness).ok("submit_proof", args, token=bob)
    assert got["status"] == 201, got
    assert got["body"].get("rivals") == [{"pr_number": first["pr_number"], "pseudonym": "alice"}]
