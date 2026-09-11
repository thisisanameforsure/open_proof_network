"""F09-T1, T3 / AC5, AC10: bearer gating of writes, and pass-through of the endpoint's answer."""

from __future__ import annotations

from typing import Any

from api_fakes import PROOF_PREFIX, TUTORIAL_NODE, TUTORIAL_PROOF, Harness, make_harness
from mcp_client import NODE, McpClient

from opn_api.mcp import auth
from opn_api.mcp.server import TOOLS

MINIMAL: dict[str, dict[str, Any]] = {
    "claim_node": {"node_id": NODE},
    "release_claim": {"claim_id": "0" * 26},
    "precheck_submission": {"node_id": TUTORIAL_NODE, "bundle": {}},
    "submit_proof": {"node_id": NODE, "artifact_type": "proof", "bundle": {}, "attestation": {}},
    "submit_postmortem": {"node_id": NODE, "yaml": {}},
    "submit_informal_annex": {"node_id": NODE, "text": "t"},
    "submit_approach_record": {"target_id": "propositional", "record": {}},
    "file_defect_claim": {"stmt_ref": NODE, "class": "vacuity", "line": 1, "exhibit": "x"},
    "file_revision_request": {
        "node_id": NODE,
        "defect_class": "vacuity",
        "evidence": {"text": "t"},
    },
    "propose_speculative_node": {"target_id": "propositional", "stmt": "s", "witness": "w"},
    "propose_variant": {"target_id": "propositional", "stmt": "s", "witness": "w"},
}


def test_token_required_for_writes_only(harness: Harness) -> None:
    """AC5: every write tool without a token is the SDK's unauthorized result and reaches no
    endpoint; every read tool without a token succeeds."""
    client = McpClient(harness)
    for tool in TOOLS:
        if not tool.write:
            continue
        doc = client.failed(tool.name, MINIMAL[tool.name])
        assert doc == {"status": auth.UNAUTHORIZED_STATUS, "body": auth.UNAUTHORIZED}, tool.name
    assert harness.store.list_claims() == []
    assert harness.githost.pushes == []
    for name in ("server_info", "list_targets", "list_frontier"):
        client.ok(name)
    # An unknown or revoked token is anonymous too: the same result, never a 500 or a leak.
    doc = client.failed("claim_node", {"node_id": NODE}, token="not-a-token")  # noqa: S106 — a sentinel
    assert doc["status"] == auth.UNAUTHORIZED_STATUS


def test_token_reaches_the_endpoint(harness: Harness) -> None:
    """R7: with a token, the receipt is the endpoint's own 201 body, and the claim is stored
    under the identity the token resolves to."""
    token = harness.token_for("code_alice", "alice-p")
    doc = McpClient(harness).ok("claim_node", {"node_id": NODE, "ttl": 5}, token=token)
    assert doc["status"] == 201
    assert doc["body"]["node_id"] == NODE
    assert doc["body"]["pseudonym"] == "alice-p"
    assert doc["body"]["expires"] == "2026-09-09T17:00:00Z"  # the fake clock plus ttl hours
    assert "retry_after" not in doc
    [claim] = harness.store.list_claims()
    assert claim.id == doc["body"]["id"]


def test_endpoint_refusal_passes_through(harness: Harness) -> None:
    """R7: a refusal from the endpoint is the tool's error result, status and body unchanged."""
    token = harness.token_for("code_alice", "alice")
    client = McpClient(harness)
    doc = client.failed("claim_node", {"node_id": "listed-only"}, token=token)
    direct = harness.client.post(
        "/claims", json={"node_id": "listed-only"}, headers=harness.auth(token)
    )
    assert doc == {"status": direct.status_code, "body": direct.json()}
    assert doc["status"] == 409
    assert doc["body"]["error"] == direct.json()["error"] == "node-not-claimable"


def test_rate_limit_passthrough() -> None:
    """AC10: the identity layer's 429 arrives as-is, Retry-After beside it (R8)."""
    h = make_harness({"OPN_API_WRITES_PER_HOUR": "1"})
    token = h.token_for("code_alice", "alice")
    client = McpClient(h)
    assert client.ok("claim_node", {"node_id": NODE}, token=token)["status"] == 201
    doc = client.failed("claim_node", {"node_id": "tutorial-and-swap"}, token=token)
    assert doc["status"] == 429
    assert doc["body"]["error"] == "rate-limited"
    assert doc["retry_after"] == "3600"  # the fake clock sits on the hour
    direct = h.client.post("/claims", json={"node_id": NODE}, headers=h.auth(token))
    assert direct.status_code == 429
    assert direct.headers["Retry-After"] == doc["retry_after"]


def test_precheck_submission_returns_job_and_poll(harness: Harness) -> None:
    """R7: the job id and the polling instruction, and get_precheck is GET /precheck/<id>."""
    token = harness.token_for("code_alice", "alice")
    client = McpClient(harness)
    proof = f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean"
    doc = client.ok(
        "precheck_submission",
        {"node_id": TUTORIAL_NODE, "bundle": {proof: TUTORIAL_PROOF}},
        token=token,
    )
    assert doc["status"] == 202
    assert doc["job_id"] == doc["body"]["id"]
    assert "get_precheck" in doc["poll"]
    polled = client.ok("get_precheck", {"job_id": doc["job_id"]})
    assert polled == harness.client.get(f"/precheck/{doc['job_id']}").json()
    assert polled["state"] in ("queued", "running")
