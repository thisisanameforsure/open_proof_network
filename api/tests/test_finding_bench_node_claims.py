"""Owner decision 2026-09-14: MCP get_node returns the latest node, so the context bundle's
``claims`` carries the live overlay and never disagrees with the top-level ``claims``."""

from __future__ import annotations

from api_fakes import make_harness
from mcp_client import NODE, McpClient, seed_node


def test_get_node_context_claims_follow_live_claims() -> None:
    harness = make_harness()
    seed_node(harness)
    harness.context.files.clear()
    client = McpClient(harness)
    token = harness.token_for("code_alice", "alice-p")

    claimed = harness.client.post("/claims", json={"node_id": NODE}, headers=harness.auth(token))
    assert claimed.status_code == 201, claimed.text
    node = client.ok("get_node", {"node_id": NODE})
    assert [a["pseudonym"] for a in node["context"]["claims"]["active"]] == ["alice-p"]
    assert node["context"]["claims"] == node["claims"]

    released = harness.client.delete(f"/claims/{claimed.json()['id']}", headers=harness.auth(token))
    assert released.status_code < 400, released.text
    node = client.ok("get_node", {"node_id": NODE})
    assert node["context"]["claims"]["active"] == [] == node["claims"]["active"]
    assert node["context"]["claims"] == node["claims"]
