"""F31-T8 (R5, AC5): the service refuses work on a shelved statement with ``node-shelved`` and
the cause (D-14 v3.47).

A shelving is a steward's or curator's judgment that a statement does not serve the root; the
products derive it onto the node's ``graph.json`` row as ``shelved`` (graph/v15) and leave the
statement off the frontier. The service reads the row, as it reads ``superseded`` (F05-T11), so
a precheck, a submission, a claim, a witness and a proposal naming the node each answer
``409 node-shelved`` carrying the cause, the signer, the date and the record, before any job,
push or pull request; ``POST /check`` warns rather than refuses (checking a statement is how a
defect in it is shown, F13-T15). A sibling that is not shelved is unaffected, and a node whose
row carries ``shelved: null`` is the world before the record.

Modelled on ``test_finding_superseded_refusals.py``: the row is fabricated as the gate would
render it; nothing here derives a shelving.
"""

from __future__ import annotations

import json
from typing import Any

import samples
from api_fakes import AUTOMATION, Harness, make_harness
from mcp_client import TARGET, McpClient, seed_node
from test_checks import PIN
from test_checks import post as post_check
from test_finding_mcp_bootstrap import HOLE, WITNESS, add_hole
from test_finding_precheck_blocked import bundle, nothing_started
from test_proposals_for import STATEMENT as CRUX_STATEMENT
from test_proposals_for import WITNESS as CRUX_WITNESS

from opn_gate import schemas

GRAPH_PATH = f"targets/{TARGET}/graph.json"
NODE = "and-reassoc"  # ready and claimable in the fixture
SIBLING = "tutorial-and-swap"  # ready and claimable in the fixture, left alone
CAUSE = "Route 2 proves fourteen special cases and nothing the root needs."
SHELVED: dict[str, Any] = {
    "cause": CAUSE,
    "by": "alice",
    "date": "2026-10-24",
    "record": "shelving/20261024T090000Z-alice.yaml",
    "scope": "node",
    "via": NODE,
}


def shelve(harness: Harness, node_id: str, **over: Any) -> dict[str, Any]:
    """The row as the products publish it once a shelving reaches the node: ``shelved`` set,
    status unchanged, and the node gone from the frontier (F31-R4)."""
    shelved = {**SHELVED, **over}
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    for node in doc["nodes"]:
        if node["node_id"] == node_id:
            node["shelved"] = shelved
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    frontier = json.loads(harness.githost.files["frontier.json"])
    frontier["entries"] = [e for e in frontier["entries"] if e["node_id"] != node_id]
    harness.githost.files["frontier.json"] = json.dumps(frontier).encode()
    harness.context.files.clear()
    return shelved


def token(harness: Harness) -> dict[str, str]:
    return harness.auth(harness.token_for("code_alice", "alice-p"))


def refused(r: Any) -> dict[str, Any]:
    body: dict[str, Any] = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-shelved"), body
    assert body["details"]["shelved"] == SHELVED, body["details"]
    assert body["details"]["node_id"] == NODE
    assert CAUSE in body["message"] and "alice" in body["message"]
    return body


# --- the five writes -----------------------------------------------------------------------------


def test_a_claim_on_a_shelved_node_is_refused_with_the_cause(harness: Harness) -> None:
    shelve(harness, NODE)
    r = harness.client.post("/claims", json={"node_id": NODE}, headers=token(harness))
    refused(r)
    assert harness.store.list_claims() == []


def test_precheck_refuses_a_shelved_node_before_any_job(harness: Harness) -> None:
    shelve(harness, NODE)
    r = harness.client.post(
        "/precheck", json={"node_id": NODE, "bundle": bundle(NODE)}, headers=token(harness)
    )
    refused(r)
    nothing_started(harness)


def test_a_submission_against_a_shelved_node_is_refused_the_same_way(harness: Harness) -> None:
    shelve(harness, NODE)
    r = harness.client.post(
        "/submissions",
        json={
            "node_id": NODE,
            "artifact_type": "proof",
            "precheck_job_id": "01M2TC4VB0K7D04GWGP4GDMZ9T",
            "automation": AUTOMATION,
        },
        headers=token(harness),
    )
    refused(r)
    assert harness.githost.pushes == []


def test_a_witness_for_a_shelved_hole_is_refused(harness: Harness) -> None:
    """A hole under a retired route reads shelved via its parent (scope route); the witness
    route refuses it before the pre-flight, naming the parent's record."""
    add_hole(harness)
    shelve(harness, HOLE, scope="route", via=NODE)
    r = harness.client.post(
        "/proposals/witness", json={"node_id": HOLE, "witness": WITNESS}, headers=token(harness)
    )
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-shelved"), body
    assert body["details"]["shelved"] == {**SHELVED, "scope": "route", "via": NODE}
    assert body["details"]["node_id"] == HOLE
    assert harness.githost.pushes == [] and harness.githost.dispatches == []


def test_a_proposal_for_a_shelved_node_is_refused(harness: Harness) -> None:
    """``for`` naming a shelved node: a crux proposed for a statement nobody should work on."""
    shelve(harness, NODE)
    r = harness.client.post(
        "/proposals/speculative",
        json={
            "target_id": TARGET,
            "statement": CRUX_STATEMENT,
            "witness": CRUX_WITNESS,
            "for": NODE,
        },
        headers=token(harness),
    )
    refused(r)
    assert harness.githost.pushes == [] and harness.githost.pulls == []


# --- the fast check warns ------------------------------------------------------------------------

CHECK_STATEMENT = "theorem OpnProp.and_reassoc : True := by\n  sorry\n"
CHECK_PROOF = "theorem OpnProp.and_reassoc : True := by\n  trivial\n"


def check_harness() -> Harness:
    h = make_harness(None)
    seed_node(h)
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=PIN)
    )
    files[f"targets/{TARGET}/nodes/{NODE}/Statement.lean"] = CHECK_STATEMENT.encode()
    files[f"targets/{TARGET}/nodes/{SIBLING}/Statement.lean"] = CHECK_STATEMENT.encode()
    h.context.files.clear()
    return h


def lint_of(h: Harness, node_id: str) -> list[dict[str, Any]]:
    r = post_check(h, {"target_id": TARGET, "node_id": node_id, "content": CHECK_PROOF})
    assert r.status_code == 200, r.text
    warnings: list[dict[str, Any]] = r.json()["lint"]
    return warnings


def test_a_check_against_a_shelved_node_warns_with_the_cause() -> None:
    h = check_harness()
    shelve(h, NODE)
    (warning,) = [w for w in lint_of(h, NODE) if w["code"] == "node-shelved"]
    assert warning["shelved"] == SHELVED
    assert CAUSE in str(warning["message"])


def test_a_check_against_the_sibling_is_not_warned() -> None:
    h = check_harness()
    shelve(h, NODE)
    assert [w for w in lint_of(h, SIBLING) if w["code"] == "node-shelved"] == []


# --- what is unaffected --------------------------------------------------------------------------


def test_an_unshelved_sibling_is_claimed_and_prechecked_as_before(harness: Harness) -> None:
    shelve(harness, NODE)
    r = harness.client.post("/claims", json={"node_id": SIBLING}, headers=token(harness))
    assert r.status_code == 201, r.text
    assert [c.node_id for c in harness.store.list_claims()] == [SIBLING]


def test_a_row_with_shelved_null_is_the_world_before(harness: Harness) -> None:
    """graph/v15 writes ``shelved: null`` on every row; nothing reads it as a shelving."""
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    for node in doc["nodes"]:
        node["shelved"] = None
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.clear()
    r = harness.client.post("/claims", json={"node_id": NODE}, headers=token(harness))
    assert r.status_code == 201, r.text


def test_the_refusal_comes_before_the_path_check(harness: Harness) -> None:
    """As for a superseded node (F05-T11): a wrong path on a shelved node says shelved."""
    shelve(harness, NODE)
    wrong = {f"targets/{TARGET}/nodes/{SIBLING}/Proof.lean": "theorem x : True := trivial\n"}
    r = harness.client.post(
        "/precheck", json={"node_id": NODE, "bundle": wrong}, headers=token(harness)
    )
    assert r.json().get("error") == "node-shelved", r.text


# --- F31-T9 (R3): the MCP ------------------------------------------------------------------------


def test_mcp_get_node_carries_the_shelving_through_the_bundle(harness: Harness) -> None:
    """The bundle is derived from the row (context.build through the HostReader), so
    ``get_node`` answers the shelving where an agent reads the node, with the cause."""
    seed_node(harness)
    shelve(harness, NODE)
    served = McpClient(harness).ok("get_node", {"node_id": NODE, "include": []})
    assert served["context"]["schema"] == "context/v11"
    assert served["context"]["shelved"] == SHELVED
    assert served["context_source"] == "derived"


def test_mcp_list_frontier_omits_a_shelved_node(harness: Harness) -> None:
    seed_node(harness)
    shelve(harness, NODE)
    served = McpClient(harness).ok("list_frontier")
    ids = [e["node_id"] for e in served["entries"]]
    assert NODE not in ids and SIBLING in ids


def test_mcp_claim_on_a_shelved_node_is_the_routes_refusal(harness: Harness) -> None:
    shelve(harness, NODE)
    client = McpClient(harness)
    failed = client.failed(
        "claim_node", {"node_id": NODE}, token=harness.token_for("code_alice", "alice-p")
    )
    assert failed["status"] == 409, failed
    assert failed["body"]["error"] == "node-shelved", failed
    assert failed["body"]["details"]["shelved"]["cause"] == CAUSE
