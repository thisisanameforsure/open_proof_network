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
    # F13-T6: verify without a node is the endpoint's own 400, reached without a token.
    "check_lean": {"target_id": "propositional", "content": "x", "mode": "verify"},
    "get_token": {
        "proof": {"kind": "tutorial", "job_id": "0" * 26, "nonce": "n"},
        "pseudonym": "anon",
        "dco": {"version": "v", "accepted": True},
    },
    "propose_witness": {"node_id": NODE, "witness": "w"},
    "withdraw_submission": {"submission_id": "1"},
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


#: The writes anonymous by design (F09-T6, Mike 2026-09-13): get_token mints the identity, so it
#: can carry none; precheck_submission lets POST /precheck decide, which opens the tutorial node
#: (F06-R2). A new write is refused without a bearer unless it is added here, deliberately.
#: F13-T6 (Mike, 2026-09-14, F13-Q2): check_lean lets POST /check decide, which charges an
#: anonymous caller by address.
ANONYMOUS_WRITES = {
    "get_token": "anyone",
    "precheck_submission": "endpoint",
    "check_lean": "endpoint",
}


def test_token_required_for_writes_only(harness: Harness) -> None:
    """AC5, amended by F09-T6: every write tool without a token is the unauthorized result (the
    route's shape) and reaches no endpoint — except the two anonymous by design, listed above,
    which reach their endpoint and return its own answer; every read tool without a token
    succeeds."""
    assert {t.name: t.access for t in TOOLS if t.write and not t.needs_bearer} == ANONYMOUS_WRITES
    client = McpClient(harness)
    for tool in TOOLS:
        if not tool.write or tool.name in ANONYMOUS_WRITES:
            continue
        doc = client.failed(tool.name, MINIMAL[tool.name])
        assert doc == {"status": auth.UNAUTHORIZED_STATUS, "body": auth.UNAUTHORIZED}, tool.name
    assert harness.store.list_claims() == []
    assert harness.githost.pushes == []
    assert harness.githost.dispatches == []
    for name in sorted(ANONYMOUS_WRITES):
        # The minimal arguments are refused, but by the endpoint (a 400 naming the field), not
        # by the adapter's gate.
        doc = client.failed(name, MINIMAL[name])
        assert doc["status"] == 400, (name, doc)
        assert doc["body"]["error"] != auth.UNAUTHORIZED["error"], (name, doc)
    assert harness.githost.dispatches == []
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
