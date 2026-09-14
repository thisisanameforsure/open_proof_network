"""F09-T6: the edges of the MCP bootstrap — the anonymous writes pass the endpoint's refusals
through unchanged, and the adapter's gate never stands in for the endpoint's own rule.

The happy paths are ``test_finding_mcp_bootstrap.py`` (findings 1 and 10). Here: ``get_token``
with a wrong and a used nonce, ``precheck_submission`` without a token on a node that is not the
tutorial one, an anonymous tutorial precheck compared with ``POST /precheck`` on a twin harness,
and ``propose_witness`` on nodes that are not witness-missing holes.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_harness,
    make_precheck_key,
)
from mcp_client import NODE, McpClient
from test_finding_mcp_bootstrap import HOLE, WITNESS, add_hole

BUNDLE = {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF}
ULID_RE = re.compile(r"[0-9A-Z]{26}")


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def envelope(r: Any) -> dict[str, Any]:
    return {"status": r.status_code, "body": r.json()}


def dco(h: Harness) -> dict[str, Any]:
    return {"version": h.client.get("/dco.json").json()["version"], "accepted": True}


def token_args(h: Harness, job: dict[str, Any], nonce: str, pseudonym: str) -> dict[str, Any]:
    return {
        "proof": {"kind": "tutorial", "job_id": job["id"], "nonce": nonce},
        "pseudonym": pseudonym,
        "dco": dco(h),
    }


def test_get_token_wrong_nonce_is_the_routes_refusal(harness: Harness, key: PrecheckKey) -> None:
    """A passing anonymous job with the wrong nonce: the route's 400, unchanged, and no
    identity; the right nonce still works afterwards (the refusal consumed nothing)."""
    job = harness.tutorial_job(key)
    client = McpClient(harness)
    args = token_args(harness, job, "not-the-nonce", "agent-wrong")
    over_mcp = client.failed("get_token", args)
    over_http = envelope(harness.client.post("/tokens", json=args))
    assert over_mcp == over_http
    assert over_mcp["status"] == 400 and over_mcp["body"]["error"] == "proof-invalid"
    assert (
        client.ok("get_token", token_args(harness, job, job["nonce"], "agent-right"))["status"]
        == 201
    )


def test_get_token_used_nonce_is_the_routes_refusal(harness: Harness, key: PrecheckKey) -> None:
    """A nonce mints one identity: the second get_token on it is the route's refusal, the same
    body the HTTP path gets for a third try."""
    job = harness.tutorial_job(key)
    client = McpClient(harness)
    first = client.ok("get_token", token_args(harness, job, job["nonce"], "agent-once"))
    assert first["status"] == 201 and first["body"]["token"]
    again = client.failed("get_token", token_args(harness, job, job["nonce"], "agent-twice"))
    third = harness.client.post(
        "/tokens", json=token_args(harness, job, job["nonce"], "agent-thrice")
    )
    assert again == envelope(third)
    assert again["status"] == 400 and again["body"]["error"] == "proof-invalid"


def test_get_token_carries_no_bearer(harness: Harness, key: PrecheckKey) -> None:
    """A caller who already holds a token still mints a new, separate identity: get_token
    forwards no bearer, so the token it returns resolves to the new pseudonym."""
    held = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key)
    client = McpClient(harness)
    doc = client.ok("get_token", token_args(harness, job, job["nonce"], "agent-new"), token=held)
    assert doc["status"] == 201
    claimed = client.ok("claim_node", {"node_id": NODE}, token=doc["body"]["token"])
    assert claimed["body"]["pseudonym"] == "agent-new"


def test_anonymous_precheck_on_another_node_is_the_routes_401(harness: Harness) -> None:
    """No token on a node that is not the tutorial one: POST /precheck's own 401 body (not the
    adapter's), nothing dispatched — the route's rule decides, the adapter does not guess it."""
    args = {"node_id": NODE, "bundle": {f"{PROOF_PREFIX}{NODE}/Proof.lean": TUTORIAL_PROOF}}
    over_mcp = McpClient(harness).failed("precheck_submission", args)
    assert harness.githost.dispatches == []
    over_http = envelope(harness.client.post("/precheck", json=args))
    assert over_mcp == over_http
    assert over_mcp["body"] == {
        "error": "unauthenticated",
        "message": "this route needs `Authorization: Bearer <token>`",
    }
    assert harness.githost.dispatches == []


def test_anonymous_tutorial_precheck_equals_the_route() -> None:
    """On two fresh harnesses, the anonymous tutorial precheck through the adapter and over HTTP
    answer the same 202 body, the job id and nonce aside; each dispatched one job."""
    a, b = make_harness(), make_harness()
    doc = McpClient(a).ok("precheck_submission", {"node_id": TUTORIAL_NODE, "bundle": BUNDLE})
    direct = b.client.post("/precheck", json={"node_id": TUTORIAL_NODE, "bundle": BUNDLE})

    def masked(value: dict[str, Any]) -> Any:
        body = {**value["body"], "nonce": "<nonce>" if value["body"].get("nonce") else None}
        text = json.dumps({"status": value["status"], "body": body}, sort_keys=True)
        return json.loads(ULID_RE.sub("<ulid>", text))

    assert masked(doc) == masked(envelope(direct))
    assert doc["status"] == 202 and doc["body"]["nonce"] and doc["job_id"] == doc["body"]["id"]
    assert len(a.githost.dispatches) == len(b.githost.dispatches) == 1


@pytest.mark.parametrize(
    ("node_id", "status", "error"),
    [(NODE, 400, "witness-not-missing"), ("no-such-node", 404, "node-unknown")],
)
def test_propose_witness_on_a_node_that_is_no_hole(
    harness: Harness, node_id: str, status: int, error: str
) -> None:
    """A ready node, or no node at all: the route's refusal passed through, nothing pushed."""
    add_hole(harness)  # a real hole exists; the call names a different node
    token = harness.token_for("code_alice", "alice")
    args = {"node_id": node_id, "witness": WITNESS}
    over_mcp = McpClient(harness).failed("propose_witness", args, token=token)
    over_http = envelope(
        harness.client.post("/proposals/witness", json=args, headers=harness.auth(token))
    )
    assert over_mcp == over_http
    assert (over_mcp["status"], over_mcp["body"]["error"]) == (status, error)
    assert harness.githost.pushes == []
    assert node_id != HOLE
