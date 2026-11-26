"""F27-T13 (R14; D-25 v3.52): a claim on a statement only strictly harder routes reach is refused
with ``node-dominated``, and nothing else about it changes.

The products leave a dominated statement off the frontier, and a claim is the frontier's act, so
without this the claimant would read only "ready and not on the frontier". The refusal names the
rule and the sets still offered. Work is not refused (the owner, 2026-11-25): a precheck of the
same node runs as before.

The rows are fabricated as the gate would render them: the root gets two routes, ``[SIBLING]``
and ``[SIBLING, NODE]``, so ``NODE`` is needed only by the second, which needs strictly more.
"""

from __future__ import annotations

import json
from typing import Any

from api_fakes import Harness
from mcp_client import TARGET
from test_finding_precheck_blocked import bundle

GRAPH_PATH = f"targets/{TARGET}/graph.json"
ROOT = "and-swap-reassoc"
NODE = "and-reassoc"
SIBLING = "tutorial-and-swap"


def dominate(harness: Harness) -> None:
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    if not any(n["node_id"] == ROOT for n in doc["nodes"]):  # the harness's golden lists no root
        doc["nodes"].append({"node_id": ROOT, "origin": "authored", "relation": None})
    for node in doc["nodes"]:
        if node["node_id"] == ROOT:
            node["status"] = "ready"
            node["deps"] = [SIBLING, NODE]
            node["decompositions"] = [
                {
                    "partial": f"attempts/2026112{k}T000000Z-a-partial.lean",
                    "annex": None,
                    "holes": [{"name": f"h{i + 1}", "node": h} for i, h in enumerate(holes)],
                }
                for k, holes in enumerate([[SIBLING], [SIBLING, NODE]])
            ]
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    frontier = json.loads(harness.githost.files["frontier.json"])
    frontier["entries"] = [e for e in frontier["entries"] if e["node_id"] != NODE]
    harness.githost.files["frontier.json"] = json.dumps(frontier).encode()
    harness.context.files.clear()


def token(harness: Harness) -> dict[str, str]:
    return harness.auth(harness.token_for("code_alice", "alice-p"))


def test_a_claim_on_a_dominated_statement_is_refused_and_says_why(harness: Harness) -> None:
    dominate(harness)
    r = harness.client.post("/claims", json={"node_id": NODE}, headers=token(harness))
    body: dict[str, Any] = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-dominated"), body
    assert "strictly harder" in body["message"] and "D-25 v3.52" in body["message"]
    assert body["details"]["node_id"] == NODE
    assert body["details"]["routes"] == [f"{ROOT}@2"]
    assert harness.store.list_claims() == []


def test_the_sibling_on_the_offered_route_is_claimed_as_before(harness: Harness) -> None:
    dominate(harness)
    r = harness.client.post("/claims", json={"node_id": SIBLING}, headers=token(harness))
    assert r.status_code == 201, r.text


def test_work_on_a_dominated_statement_is_not_refused(harness: Harness) -> None:
    """Not offered, never refused: a precheck of the node is accepted as before."""
    dominate(harness)
    r = harness.client.post(
        "/precheck", json={"node_id": NODE, "bundle": bundle(NODE)}, headers=token(harness)
    )
    assert r.status_code == 202, r.text
