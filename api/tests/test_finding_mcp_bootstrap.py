"""Findings 1 and 10 (2026-09-13, the live MCP contribution): the MCP path cannot bootstrap an
identity, and its refusal body is not the route's.

The tester was handed the site and the MCP endpoint. ``precheck_submission`` on the tutorial
node answered 401 through the adapter while the same bundle over ``POST /precheck`` passed
(F06-R2 exempts the tutorial node from the bearer); there was no tool for ``POST /tokens``, so
the identity had to be minted over HTTP; and there was no tool for ``POST /proposals/witness``,
so the two holes the merged skeleton spawned could only be witnessed by a curator. Every
unauthenticated write answered the SDK's OAuth body (``invalid_token``) while the route answers
a sentence with the fix.

Mike's decision (2026-09-13, plan Phase 0): ``precheck_submission`` passes an anonymous tutorial
precheck through, mirroring F06-R2; two new tools, ``get_token`` -> ``POST /tokens`` and
``propose_witness`` -> ``POST /proposals/witness``, as a notation addendum to D-28's v0 table
(both are existing endpoints, so the bijection holds). Each test asserts that behaviour and is
held as a strict xfail until F09-T6 lands (conventions §2). The two new tools are looked up in
``tools/list`` inside the test body, never imported: a collection error is not an xfail.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
)
from mcp_client import NODE, TARGET, McpClient

BUNDLE = {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF}
GRAPH_PATH = f"targets/{TARGET}/graph.json"
HOLE = "and-reassoc--h1"
WITNESS = "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"
FINDING_1 = "finding 1 (F09-R2, F06-R2, D-19, D-28): {}; fix: F09-T6 (Mike, 2026-09-13)"
FINDING_10 = "finding 10 (F09-R2, F05-R5, D-28): {}; fix: F09-T6 (Mike, 2026-09-13)"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def tool_names(client: McpClient) -> set[str]:
    return {t.name for t in client.list_tools()}


def add_hole(harness: Harness) -> None:
    """A compiler-derived hole blocked ``witness-missing`` in the committed graph.json — the
    state a merged skeleton leaves behind (F07-R6), as ``test_proposals.py`` seeds it."""
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != HOLE]
    doc["nodes"].append(
        {
            "node_id": HOLE,
            "status": "blocked",
            "cause": "witness-missing",
            "deps": [],
            "origin": "compiler-derived",
            "statement_hash": "1" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.pop(GRAPH_PATH, None)


# --- finding 1: the anonymous tutorial precheck, and the two missing tools ------------------------


@pytest.mark.xfail(
    strict=True,
    reason=FINDING_1.format(
        "precheck_submission refuses every caller without a bearer, so the one anonymous write "
        "F06-R2 allows — the tutorial precheck that mints every identity — is unreachable "
        "through the MCP"
    ),
)
def test_precheck_submission_on_the_tutorial_node_needs_no_bearer(harness: Harness) -> None:
    """F06-R2: the tutorial node is open to an unauthenticated caller and the job carries the
    single-use nonce; through the adapter the same request is the same 202. A non-tutorial node
    without a bearer still gets the endpoint's own 401 passed through (F09-R7)."""
    client = McpClient(harness)
    doc = client.ok("precheck_submission", {"node_id": TUTORIAL_NODE, "bundle": BUNDLE})
    assert doc["status"] == 202, doc
    body = doc["body"]
    assert doc["job_id"] == body["id"]
    assert body["authenticated"] is False
    assert body["nonce"], "an anonymous tutorial job is answered with its nonce (F06-R7)"
    polled = harness.client.get(f"/precheck/{doc['job_id']}")
    assert polled.status_code == 200 and polled.json()["state"] in ("queued", "running")

    refused = client.failed(
        "precheck_submission",
        {"node_id": NODE, "bundle": {f"{PROOF_PREFIX}{NODE}/Proof.lean": TUTORIAL_PROOF}},
    )
    assert refused["status"] == 401, refused
    assert len(harness.githost.dispatches) == 1, "only the tutorial job was dispatched"


@pytest.mark.xfail(
    strict=True,
    reason=FINDING_1.format(
        "there is no get_token tool, so an MCP-only client can never turn a passing tutorial "
        "precheck into a token and is read-only forever"
    ),
)
def test_get_token_is_listed_and_mints_a_token_from_a_tutorial_pass(
    harness: Harness, key: PrecheckKey
) -> None:
    """``get_token`` is ``POST /tokens`` with the body verbatim (``{proof, pseudonym, dco}``),
    anonymous by design: the proof is the passing anonymous job's ``{id, nonce}`` (F06-R7,
    D-19), the DCO version is what ``GET /dco.json`` publishes (F05-R4). The token it returns
    is a real bearer: it authenticates a write."""
    job = harness.tutorial_job(key)  # anonymous, done, passing
    client = McpClient(harness)
    assert "get_token" in tool_names(client), sorted(tool_names(client))
    dco = harness.client.get("/dco.json").json()
    doc = client.ok(
        "get_token",
        {
            "proof": {"kind": "tutorial", "job_id": job["id"], "nonce": job["nonce"]},
            "pseudonym": "agent-4b1f4d",
            "dco": {"version": dco["version"], "accepted": True},
        },
    )
    assert doc["status"] == 201, doc
    token = doc["body"]["token"]
    assert isinstance(token, str) and token
    assert doc["body"]["identity"]["pseudonym"] == "agent-4b1f4d"
    assert doc["body"]["identity"]["proof_kind"] == "tutorial"
    claimed = client.ok("claim_node", {"node_id": NODE}, token=token)
    assert claimed["status"] == 201
    assert claimed["body"]["pseudonym"] == "agent-4b1f4d"


@pytest.mark.xfail(
    strict=True,
    reason=FINDING_1.format(
        "there is no propose_witness tool, so the holes a merged skeleton spawns can only be "
        "witnessed over HTTP or by a curator"
    ),
)
def test_propose_witness_is_listed_and_forwards_to_the_witness_route(harness: Harness) -> None:
    """``propose_witness`` is ``POST /proposals/witness`` (F08-R5): with a bearer, on a hole
    blocked ``witness-missing``, it opens the pull request adding only ``Witness.lean``; without
    a bearer it is refused and nothing is pushed."""
    add_hole(harness)
    token = harness.token_for("code_alice", "alice")
    client = McpClient(harness)
    assert "propose_witness" in tool_names(client), sorted(tool_names(client))

    refused = client.failed("propose_witness", {"node_id": HOLE, "witness": WITNESS})
    assert refused["status"] == 401
    assert harness.githost.pushes == []

    doc = client.ok("propose_witness", {"node_id": HOLE, "witness": WITNESS}, token=token)
    assert doc["status"] == 201, doc
    assert doc["body"]["node_id"] == HOLE
    assert doc["body"]["target_id"] == TARGET
    assert doc["body"]["pr_url"].endswith("/pull/1")
    [push] = harness.githost.pushes
    assert push.files == {f"targets/{TARGET}/nodes/{HOLE}/Witness.lean": WITNESS}
    assert push.author is not None and push.author.name == "alice"


# --- finding 10: the refusal body is the route's --------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=FINDING_10.format(
        "an unauthenticated write answers the SDK's OAuth body {error: invalid_token, "
        "error_description: Authentication required} instead of the route's "
        "{error: unauthenticated, message: ...} naming the fix"
    ),
)
def test_unauthenticated_write_refusal_matches_the_http_route(harness: Harness) -> None:
    """The same refusal on both paths: status 401, ``error`` equal to ``POST /claims``'s own,
    and a ``message`` that names the way out on the MCP path: ``get_token``, and the anonymous
    tutorial ``precheck_submission`` whose pass the token is minted from."""
    client = McpClient(harness)
    over_mcp = client.failed("claim_node", {"node_id": NODE})
    over_http = harness.client.post("/claims", json={"node_id": NODE})
    assert over_http.status_code == 401 and over_http.json()["error"] == "unauthenticated"

    assert over_mcp["status"] == over_http.status_code
    body = over_mcp["body"]
    assert set(body) == {"error", "message"}, body
    assert body["error"] == over_http.json()["error"]
    assert "get_token" in body["message"], body["message"]
    assert "precheck_submission" in body["message"], body["message"]
    assert harness.store.list_claims() == []
    assert harness.githost.pushes == []


def test_pin_the_precheck_route_is_anonymous_for_the_tutorial_node(harness: Harness) -> None:
    """**PIN — the rule the adapter must mirror.** Over HTTP the tutorial node needs no bearer
    (F06-R2) and every other node does, with the route's refusal shape: the finding is about
    the adapter, not the route."""
    open_node = harness.client.post("/precheck", json={"node_id": TUTORIAL_NODE, "bundle": BUNDLE})
    assert open_node.status_code == 202, open_node.text
    assert open_node.json()["authenticated"] is False and open_node.json()["nonce"]
    closed: dict[str, Any] = harness.client.post(
        "/precheck",
        json={"node_id": NODE, "bundle": {f"{PROOF_PREFIX}{NODE}/Proof.lean": TUTORIAL_PROOF}},
    ).json()
    assert closed == {
        "error": "unauthenticated",
        "message": "this route needs `Authorization: Bearer <token>`",
    }
